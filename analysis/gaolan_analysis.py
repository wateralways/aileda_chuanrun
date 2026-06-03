#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高澜股份(300499) 深度策略分析 - 含主力资金流向
数据区间: 2025-06-03 ~ 2026-06-03 (244个交易日)
"""
import pandas as pd
import numpy as np
import json
import os

def load_data():
    """加载日线+资金流向数据"""
    df = pd.read_csv('gaolan_daily.csv')
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    df = df.sort_values('trade_date').reset_index(drop=True)
    
    has_mf = False
    if os.path.exists('gaolan_moneyflow.csv'):
        mf = pd.read_csv('gaolan_moneyflow.csv')
        df = df.merge(mf, on=['ts_code','trade_date'], how='left')
        has_mf = True
    return df, has_mf

def calc_indicators(df, has_mf=True):
    """计算技术指标+资金流向指标"""
    df = df.copy()
    
    # === 基础价格指标 ===
    for w in [3, 5, 10, 20]:
        df[f'ma{w}'] = df['close'].rolling(window=w).mean()
    df['vol_ma5'] = df['vol'].rolling(window=5).mean()
    df['vol_ma10'] = df['vol'].rolling(window=10).mean()
    df['vol_ratio'] = df['vol'] / df['vol_ma5']
    
    # RSI
    delta = df['close'].diff()
    for w in [6, 14]:
        gain = delta.where(delta > 0, 0).rolling(window=w).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=w).mean()
        df[f'rsi{w}'] = 100 - (100 / (1 + gain / loss))
    
    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # KDJ
    low_min = df['low'].rolling(window=9).min()
    high_max = df['high'].rolling(window=9).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    df['k'] = rsv.ewm(com=2, adjust=False).mean()
    df['d'] = df['k'].ewm(com=2, adjust=False).mean()
    df['j'] = 3 * df['k'] - 2 * df['d']
    
    # 布林带
    df['bb_mid'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * bb_std
    df['bb_lower'] = df['bb_mid'] - 2 * bb_std
    df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # 振幅和实体
    df['amplitude'] = (df['high'] - df['low']) / df['low'] * 100
    df['body'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['upper_shadow'] = (df['high'] - df[['close', 'open']].max(axis=1)) / df['open'] * 100
    df['lower_shadow'] = (df[['close', 'open']].min(axis=1) - df['low']) / df['open'] * 100
    df['change_pct'] = df['close'].pct_change() * 100
    
    # 价格位置
    df['price_position'] = (df['close'] - df['low'].rolling(20).min()) / (df['high'].rolling(20).max() - df['low'].rolling(20).min())
    
    # 连涨连跌
    df['up_days'] = 0
    df['down_days'] = 0
    for i in range(1, len(df)):
        if df.iloc[i]['close'] > df.iloc[i-1]['close']:
            df.iloc[i, df.columns.get_loc('up_days')] = df.iloc[i-1]['up_days'] + 1
        elif df.iloc[i]['close'] < df.iloc[i-1]['close']:
            df.iloc[i, df.columns.get_loc('down_days')] = df.iloc[i-1]['down_days'] + 1
    
    # 跳空
    df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1) * 100
    
    # === 主力资金流向指标 ===
    if has_mf and 'buy_elg_amount' in df.columns:
        df['elg_net_amount'] = df['buy_elg_amount'] - df['sell_elg_amount']
        df['lg_net_amount'] = df['buy_lg_amount'] - df['sell_lg_amount']
        df['main_net_amount'] = df['elg_net_amount'] + df['lg_net_amount']
        df['main_net_ratio'] = df['main_net_amount'] / df['amount'] * 100
        df['elg_net_ratio'] = df['elg_net_amount'] / df['amount'] * 100
        df['main_net_5d'] = df['main_net_amount'].rolling(window=5).sum()
        df['main_net_ratio_5d'] = df['main_net_ratio'].rolling(window=5).mean()
        df['main_strong_inflow'] = df['main_net_ratio'] > 5
        df['sm_net_amount'] = (df['buy_sm_amount'] - df['sell_sm_amount']) + (df['buy_md_amount'] - df['sell_md_amount'])
        df['sm_net_ratio'] = df['sm_net_amount'] / df['amount'] * 100
    
    return df

# ===================== 策略定义 =====================

def s_vol_breakout(df, i, vol_mult=1.5, min_amp=2.5):
    if i < 10: return False
    return (df.iloc[i]['vol_ratio'] > vol_mult and 
            df.iloc[i]['amplitude'] > min_amp and
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['close'] > df.iloc[i-1]['high'])

def s_rsi_bounce(df, i, rsi_thresh=35):
    if i < 15: return False
    return (df.iloc[i-1]['rsi6'] < rsi_thresh and 
            df.iloc[i]['rsi6'] > df.iloc[i-1]['rsi6'] and
            df.iloc[i]['close'] > df.iloc[i]['open'])

def s_gap_up(df, i, min_gap=0.8, max_gap=5.0):
    if i < 5: return False
    gap = df.iloc[i]['gap']
    return (min_gap < gap < max_gap and 
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['vol_ratio'] > 1.2)

def s_macd_cross(df, i):
    if i < 30: return False
    return (df.iloc[i-1]['macd'] < df.iloc[i-1]['macd_signal'] and 
            df.iloc[i]['macd'] > df.iloc[i]['macd_signal'] and
            df.iloc[i]['macd'] > -0.5)

def s_kdj_golden(df, i, j_max=20):
    if i < 20: return False
    return (df.iloc[i-1]['k'] < df.iloc[i-1]['d'] and 
            df.iloc[i]['k'] > df.iloc[i]['d'] and
            df.iloc[i]['j'] < j_max and
            df.iloc[i]['close'] > df.iloc[i]['open'])

def s_bb_bounce(df, i):
    if i < 20: return False
    return ((df.iloc[i-1]['low'] <= df.iloc[i-1]['bb_lower'] or df.iloc[i-1]['bb_pct'] < 0.1) and
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['close'] > df.iloc[i-1]['close'])

def s_consolidation_break(df, i, days=5, max_range=6):
    if i < days + 5: return False
    recent = df.iloc[i-days:i]
    consolidate = (recent['high'].max() - recent['low'].min()) / recent['low'].min() * 100 < max_range
    return (consolidate and 
            df.iloc[i]['close'] > recent['high'].max() and
            df.iloc[i]['vol_ratio'] > 1.5 and
            df.iloc[i]['close'] > df.iloc[i]['open'])

def s_pullback(df, i):
    if i < 10: return False
    recent = df.iloc[i-5:i]
    strong = (recent['high'].max() - recent['low'].min()) / recent['low'].min() * 100 > 8
    return (strong and 
            df.iloc[i]['close'] < df.iloc[i-1]['close'] and
            df.iloc[i]['low'] > df.iloc[i]['ma5'] * 0.98 and
            df.iloc[i]['vol_ratio'] < 0.9 and
            df.iloc[i]['lower_shadow'] > df.iloc[i]['upper_shadow'])

def s_engulfing(df, i):
    if i < 5: return False
    prev = df.iloc[i-1]
    curr = df.iloc[i]
    return (prev['close'] < prev['open'] and
            curr['close'] > curr['open'] and
            curr['open'] <= prev['close'] and
            curr['close'] >= prev['open'] and
            curr['vol_ratio'] > 1.2)

def s_morning_star(df, i):
    if i < 5: return False
    d1, d2, d3 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
    return (d1['close'] < d1['open'] and
            abs(d2['close'] - d2['open']) / d2['open'] * 100 < 1.5 and
            d3['close'] > d3['open'] and
            d3['close'] > (d1['open'] + d1['close']) / 2 and
            d3['vol_ratio'] > 1.0)

def s_limit_up_open(df, i):
    if i < 5: return False
    return (df.iloc[i-1]['pct_chg'] > 9.5 and
            df.iloc[i]['open'] > df.iloc[i-1]['close'] * 1.02 and
            df.iloc[i]['amplitude'] > 5 and
            df.iloc[i]['close'] > df.iloc[i]['open'])

def s_first_red_after_blues(df, i):
    if i < 5: return False
    blues = sum(1 for j in range(1, 4) if df.iloc[i-j]['close'] < df.iloc[i-j]['open'])
    return (blues >= 2 and
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['close'] > df.iloc[i-1]['close'])

def s_break_ma20(df, i):
    if i < 25: return False
    return (df.iloc[i-1]['close'] < df.iloc[i-1]['ma20'] and
            df.iloc[i]['close'] > df.iloc[i]['ma20'] and
            df.iloc[i]['vol_ratio'] > 1.3 and
            df.iloc[i]['close'] > df.iloc[i]['open'])

# === 资金流向策略 ===

def s_main_inflow_break(df, i):
    if i < 10: return False
    if 'main_net_ratio' not in df.columns: return False
    row = df.iloc[i]
    return (row['main_net_ratio'] > 3 and
            row['elg_net_amount'] > 0 and
            row['close'] > row['open'] and
            row['vol_ratio'] > 1.2 and
            row['close'] > row['ma5'])

def s_main_follow(df, i):
    if i < 10: return False
    if 'main_net_ratio' not in df.columns: return False
    prev = df.iloc[i-1]
    curr = df.iloc[i]
    return (prev['main_net_ratio'] > 5 and
            curr['close'] > curr['open'] and curr['close'] > prev['close'] and
            curr['main_net_ratio'] > 0 and
            curr['vol_ratio'] > 1.0)

def s_main_first_red(df, i):
    if i < 5: return False
    if 'main_net_ratio' not in df.columns: return False
    blues = sum(1 for j in range(1, 4) if df.iloc[i-j]['close'] < df.iloc[i-j]['open'])
    return (blues >= 2 and
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['main_net_ratio'] > 3 and
            df.iloc[i]['rsi14'] < 60)

def s_main_divergence(df, i):
    if i < 10: return False
    if 'main_net_ratio' not in df.columns: return False
    row = df.iloc[i]
    prev = df.iloc[i-1]
    price_down = row['close'] < prev['close']
    main_in = row['main_net_ratio'] > 3
    lower_shadow = (min(row['close'], row['open']) - row['low']) / row['low'] * 100 > 1
    return price_down and main_in and lower_shadow

def s_main_continuous(df, i):
    if i < 10: return False
    if 'main_net_ratio' not in df.columns: return False
    recent = df.iloc[i-2:i+1]
    all_in = all(r['main_net_amount'] > 0 for _, r in recent.iterrows())
    total_ratio = recent['main_net_ratio'].sum()
    return all_in and total_ratio > 8 and df.iloc[i]['close'] >= df.iloc[i]['ma10']

def s_macd_main_combo(df, i):
    if i < 30: return False
    if 'main_net_ratio' not in df.columns: return False
    return (df.iloc[i-1]['macd'] < df.iloc[i-1]['macd_signal'] and 
            df.iloc[i]['macd'] > df.iloc[i]['macd_signal'] and
            df.iloc[i]['main_net_ratio'] > 2 and
            df.iloc[i]['vol_ratio'] > 1.0)

# ===================== 回测框架 =====================

def backtest(df, signal_func, max_hold=8, stop_loss=None, take_profit=None, **kwargs):
    trades = []
    i = 0
    while i < len(df):
        if signal_func(df, i, **kwargs):
            entry_price = df.iloc[i]['close']
            entry_date = df.iloc[i]['trade_date']
            exit_idx = min(i + max_hold, len(df) - 1)
            
            for j in range(i + 1, exit_idx + 1):
                high_pct = (df.iloc[j]['high'] - entry_price) / entry_price * 100
                low_pct = (df.iloc[j]['low'] - entry_price) / entry_price * 100
                
                if stop_loss and low_pct < -stop_loss:
                    pnl = -stop_loss
                    trades.append({'entry_date': entry_date, 'entry_price': entry_price,
                        'exit_date': df.iloc[j]['trade_date'], 'exit_price': entry_price * (1 - stop_loss/100),
                        'hold_days': j - i, 'pnl': pnl, 'reason': 'stop_loss'})
                    i = j + 1
                    break
                elif take_profit and high_pct > take_profit:
                    pnl = take_profit
                    trades.append({'entry_date': entry_date, 'entry_price': entry_price,
                        'exit_date': df.iloc[j]['trade_date'], 'exit_price': entry_price * (1 + take_profit/100),
                        'hold_days': j - i, 'pnl': pnl, 'reason': 'take_profit'})
                    i = j + 1
                    break
            else:
                exit_price = df.iloc[exit_idx]['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({'entry_date': entry_date, 'entry_price': entry_price,
                    'exit_date': df.iloc[exit_idx]['trade_date'], 'exit_price': exit_price,
                    'hold_days': exit_idx - i, 'pnl': pnl, 'reason': 'time_exit'})
                i = exit_idx + 1
        else:
            i += 1
    
    if not trades:
        return {'trades': [], 'count': 0, 'win_rate': 0, 'avg_pnl': 0, 'avg_win': 0, 'avg_loss': 0,
                'total_pnl': 0, 'profit_factor': 0, 'max_dd': 0, 'avg_hold': 0}
    
    wins = [t['pnl'] for t in trades if t['pnl'] > 0]
    losses = [t['pnl'] for t in trades if t['pnl'] <= 0]
    
    total_pnl = 1
    for t in trades:
        total_pnl *= (1 + t['pnl'] / 100)
    total_pnl = (total_pnl - 1) * 100
    
    equity = [1]
    for t in trades:
        equity.append(equity[-1] * (1 + t['pnl'] / 100))
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / peak * 100
    
    return {
        'trades': trades, 'count': len(trades), 'win_rate': len(wins) / len(trades) * 100,
        'avg_pnl': np.mean([t['pnl'] for t in trades]),
        'avg_win': np.mean(wins) if wins else 0, 'avg_loss': np.mean(losses) if losses else 0,
        'profit_factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf'),
        'total_pnl': total_pnl, 'max_dd': max(dd), 'avg_hold': np.mean([t['hold_days'] for t in trades])
    }

# ===================== 主程序 =====================

if __name__ == '__main__':
    print("=" * 110)
    print("高澜股份 (300499) 深度策略分析")
    print("=" * 110)
    
    df, has_mf = load_data()
    df = calc_indicators(df, has_mf)
    
    print(f"\n【基础统计】")
    print(f"  数据期间: {df['trade_date'].min().date()} ~ {df['trade_date'].max().date()} ({len(df)}个交易日)")
    print(f"  价格区间: {df['low'].min():.2f} ~ {df['high'].max():.2f}")
    print(f"  期间涨跌幅: {(df.iloc[-1]['close'] / df.iloc[0]['close'] - 1) * 100:.2f}%")
    print(f"  平均振幅: {df['amplitude'].mean():.2f}%")
    print(f"  涨停次数(>9.5%): {(df['pct_chg'] > 9.5).sum()}")
    print(f"  大跌次数(<-5%): {(df['pct_chg'] < -5).sum()}")
    print(f"  波动率(20日): {df['close'].rolling(20).std().mean() / df['close'].mean() * 100:.2f}%")
    
    # 月度表现
    df['month'] = df['trade_date'].dt.to_period('M')
    monthly = df.groupby('month').agg({'close': ['first', 'last'], 'amplitude': 'mean'})
    monthly.columns = ['open', 'close', 'avg_amp']
    monthly['return'] = (monthly['close'] / monthly['open'] - 1) * 100
    print(f"\n【月度表现】")
    for m, row in monthly.iterrows():
        print(f"  {m}: 收益 {row['return']:>+7.2f}%, 振幅 {row['avg_amp']:.2f}%")
    
    if has_mf:
        print(f"\n【资金流向统计】")
        print(f"  主力净流入天数: {(df['main_net_amount'] > 0).sum()} / {len(df)}")
        print(f"  主力强流入天数(>5%): {(df['main_net_ratio'] > 5).sum()}")
        print(f"  平均主力净流入占比: {df['main_net_ratio'].mean():.2f}%")
        main_up = df[df['main_net_amount'] > 0]['change_pct'].mean()
        main_down = df[df['main_net_amount'] < 0]['change_pct'].mean()
        print(f"  主力流入日平均涨幅: {main_up:.2f}%")
        print(f"  主力流出日平均涨幅: {main_down:.2f}%")
    
    # 策略列表
    strategies = [
        ('放量突破(v1.5)', s_vol_breakout, {'vol_mult': 1.5, 'min_amp': 2.5}),
        ('放量突破(v1.2)', s_vol_breakout, {'vol_mult': 1.2, 'min_amp': 2.0}),
        ('放量突破(v2.0)', s_vol_breakout, {'vol_mult': 2.0, 'min_amp': 3.0}),
        ('RSI超跌反弹(35)', s_rsi_bounce, {'rsi_thresh': 35}),
        ('RSI超跌反弹(40)', s_rsi_bounce, {'rsi_thresh': 40}),
        ('跳空高开', s_gap_up, {'min_gap': 0.8, 'max_gap': 5.0}),
        ('MACD金叉', s_macd_cross, {}),
        ('KDJ金叉', s_kdj_golden, {'j_max': 20}),
        ('布林带反弹', s_bb_bounce, {}),
        ('盘整突破', s_consolidation_break, {'days': 5}),
        ('强势股回调', s_pullback, {}),
        ('阳线吞没', s_engulfing, {}),
        ('晨星形态', s_morning_star, {}),
        ('涨停回封', s_limit_up_open, {}),
        ('连阴首阳', s_first_red_after_blues, {}),
        ('突破MA20', s_break_ma20, {}),
    ]
    
    if has_mf:
        strategies.extend([
            ('主力净流入突破', s_main_inflow_break, {}),
            ('跟庄确认', s_main_follow, {}),
            ('连阴首阳+主力', s_main_first_red, {}),
            ('价跌主力吸货', s_main_divergence, {}),
            ('主力连续流入', s_main_continuous, {}),
            ('MACD金叉+主力', s_macd_main_combo, {}),
        ])
    
    # 止盈止损配置
    stop_configs = [
        {},
        {'stop_loss': 5, 'take_profit': 12},
        {'stop_loss': 6, 'take_profit': 15},
    ]
    
    results = []
    for name, func, params in strategies:
        for stop_cfg in stop_configs:
            suffix = ''
            if stop_cfg:
                suffix = f"[SL{stop_cfg['stop_loss']}TP{stop_cfg['take_profit']}]"
            try:
                res = backtest(df, func, max_hold=8, **stop_cfg, **params)
                results.append({'name': name + suffix, **res})
            except Exception as e:
                print(f"Error in {name}{suffix}: {e}")
    
    # 组合策略
    def combo_tech(df, i):
        return (s_vol_breakout(df, i, vol_mult=1.5, min_amp=2.5) or 
                s_engulfing(df, i) or
                s_consolidation_break(df, i, days=5) or
                s_gap_up(df, i))
    
    def combo_all(df, i):
        signals = [combo_tech(df, i)]
        if has_mf:
            signals.extend([s_main_inflow_break(df, i), s_main_follow(df, i)])
        return any(signals)
    
    for stop_cfg in [{}, {'stop_loss': 5, 'take_profit': 12}]:
        suffix = '' if not stop_cfg else f"[SL{stop_cfg['stop_loss']}TP{stop_cfg['take_profit']}]"
        results.append({'name': '组合(纯技术)' + suffix, **backtest(df, combo_tech, max_hold=8, **stop_cfg)})
        results.append({'name': '组合(全部)' + suffix, **backtest(df, combo_all, max_hold=8, **stop_cfg)})
    
    # 排序显示
    results.sort(key=lambda x: x['total_pnl'], reverse=True)
    
    print(f"\n{'='*110}")
    print("策略回测结果（按总收益排序）")
    print(f"{'='*110}")
    print(f"{'策略名称':<42} {'次数':>5} {'胜率%':>7} {'总收益%':>9} {'盈亏比':>7} {'回撤%':>8} {'持仓':>5}")
    print("-" * 110)
    for r in results[:30]:
        print(f"{r['name']:<42} {r['count']:>5} {r['win_rate']:>7.1f} {r['total_pnl']:>9.2f} {r['profit_factor']:>7.2f} {r['max_dd']:>8.2f} {r['avg_hold']:>5.1f}")
    
    # 高胜率策略
    print(f"\n{'='*110}")
    print("高胜率策略（交易>=5次, 胜率>=60%, 总收益>0）")
    print(f"{'='*110}")
    good = [r for r in results if r['count'] >= 5 and r['win_rate'] >= 60 and r['total_pnl'] > 0]
    good.sort(key=lambda x: x['total_pnl'], reverse=True)
    if good:
        print(f"{'策略名称':<42} {'次数':>5} {'胜率%':>7} {'总收益%':>9} {'盈亏比':>7} {'回撤%':>8}")
        for r in good[:15]:
            print(f"{r['name']:<42} {r['count']:>5} {r['win_rate']:>7.1f} {r['total_pnl']:>9.2f} {r['profit_factor']:>7.2f} {r['max_dd']:>8.2f}")
    else:
        print("  无满足条件的策略")
    
    # TOP策略逐笔
    print(f"\n{'='*110}")
    print("TOP 8 策略逐笔交易详情")
    print(f"{'='*110}")
    for r in results[:8]:
        if r['count'] == 0:
            continue
        print(f"\n【{r['name']}】交易{r['count']}次, 胜率{r['win_rate']:.1f}%, 总收益{r['total_pnl']:.2f}%")
        print(f"{'买入日期':<12} {'买入价':>8} {'卖出日期':<12} {'卖出价':>8} {'天数':>4} {'盈亏%':>8} {'原因':<12}")
        for t in r['trades']:
            reason = t.get('reason', 'time_exit')
            print(f"{str(t['entry_date'])[:10]:<12} {t['entry_price']:>8.2f} {str(t['exit_date'])[:10]:<12} {t['exit_price']:>8.2f} {t['hold_days']:>4} {t['pnl']:>+8.2f} {reason:<12}")
    
    # 保存
    save_data = [{k: v for k, v in r.items() if k != 'trades'} for r in results]
    with open('gaolan_results.json', 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到 gaolan_results.json")
