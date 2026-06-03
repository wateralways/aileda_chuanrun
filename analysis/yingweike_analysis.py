#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
英维克(002837) 深度策略分析 - 含主力资金流向
"""
import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

TUSHARE_TOKEN = '701a94c30c5d1c7af41602c8ebd47b1ca7a2c49bfdd5419379f40c8d'
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()

def get_data(code='002837.SZ'):
    """获取日线+资金流向数据"""
    daily_file = 'yingweike_daily.csv'
    mf_file = 'yingweike_moneyflow.csv'
    
    # 日线数据
    if os.path.exists(daily_file):
        df = pd.read_csv(daily_file)
    else:
        df = pro.daily(ts_code=code, start_date='20260101', end_date='20260603')
        df = df.sort_values('trade_date').reset_index(drop=True)
        df.to_csv(daily_file, index=False)
    
    # 资金流向数据
    if os.path.exists(mf_file):
        mf = pd.read_csv(mf_file)
    else:
        try:
            mf = pro.moneyflow(ts_code=code, start_date='20260101', end_date='20260603')
            mf = mf.sort_values('trade_date').reset_index(drop=True)
            mf.to_csv(mf_file, index=False)
        except Exception as e:
            print(f"[注意] moneyflow接口暂时不可用: {e}")
            print("[注意] 将只使用日线数据进行纯技术面策略分析")
            mf = None
    
    df = df.sort_values('trade_date').reset_index(drop=True)
    if mf is not None:
        df = df.merge(mf, on=['ts_code','trade_date'], how='left')
    return df, mf is not None

def calc_indicators(df, has_moneyflow=True):
    """计算技术指标+资金流向指标"""
    df = df.copy()
    
    # === 基础价格指标 ===
    for w in [5, 10, 20]:
        df[f'ma{w}'] = df['close'].rolling(window=w).mean()
    df['vol_ma5'] = df['vol'].rolling(window=5).mean()
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
    
    # 振幅
    df['amplitude'] = (df['high'] - df['low']) / df['low'] * 100
    df['body'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['change_pct'] = df['close'].pct_change() * 100
    
    # === 主力资金流向指标 ===
    if has_moneyflow and 'buy_elg_amount' in df.columns:
        # 特大单净流入金额
        df['elg_net_amount'] = df['buy_elg_amount'] - df['sell_elg_amount']
        # 大单净流入金额
        df['lg_net_amount'] = df['buy_lg_amount'] - df['sell_lg_amount']
        # 主力资金净流入（特大单+大单）
        df['main_net_amount'] = df['elg_net_amount'] + df['lg_net_amount']
        # 主力资金净流入占比（占成交额）
        df['main_net_ratio'] = df['main_net_amount'] / df['amount'] * 100
        # 特大单净流入占比
        df['elg_net_ratio'] = df['elg_net_amount'] / df['amount'] * 100
        
        # 主力资金5日累计
        df['main_net_5d'] = df['main_net_amount'].rolling(window=5).sum()
        df['main_net_ratio_5d'] = df['main_net_ratio'].rolling(window=5).mean()
        
        # 主力资金流向趋势
        df['main_inflow'] = df['main_net_amount'] > 0
        df['main_strong_inflow'] = df['main_net_ratio'] > 5
        df['main_strong_outflow'] = df['main_net_ratio'] < -5
        
        # 特大单主导程度
        df['elg_dominance'] = df['elg_net_amount'] / (abs(df['elg_net_amount']) + abs(df['lg_net_amount']) + 1) * 100
        
        # 散户反向指标
        df['sm_net_amount'] = (df['buy_sm_amount'] - df['sell_sm_amount']) + (df['buy_md_amount'] - df['sell_md_amount'])
        df['sm_net_ratio'] = df['sm_net_amount'] / df['amount'] * 100
    
    # 连涨连跌
    df['up_days'] = 0
    df['down_days'] = 0
    for i in range(1, len(df)):
        if df.iloc[i]['close'] > df.iloc[i-1]['close']:
            df.iloc[i, df.columns.get_loc('up_days')] = df.iloc[i-1]['up_days'] + 1
        elif df.iloc[i]['close'] < df.iloc[i-1]['close']:
            df.iloc[i, df.columns.get_loc('down_days')] = df.iloc[i-1]['down_days'] + 1
    
    # 价格位置
    df['price_position'] = (df['close'] - df['low'].rolling(20).min()) / (df['high'].rolling(20).max() - df['low'].rolling(20).min())
    
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
    gap = (df.iloc[i]['open'] - df.iloc[i-1]['close']) / df.iloc[i-1]['close'] * 100
    return (min_gap < gap < max_gap and 
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['vol_ratio'] > 1.2)

def s_macd_cross(df, i):
    if i < 30: return False
    return (df.iloc[i-1]['macd'] < df.iloc[i-1]['macd_signal'] and 
            df.iloc[i]['macd'] > df.iloc[i]['macd_signal'] and
            df.iloc[i]['macd'] > -0.5)

def s_kdj_golden(df, i):
    if i < 20: return False
    low_min = df['low'].rolling(window=9).min()
    high_max = df['high'].rolling(window=9).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d
    return (k.iloc[i-1] < d.iloc[i-1] and k.iloc[i] > d.iloc[i] and
            j.iloc[i] < 30 and df.iloc[i]['close'] > df.iloc[i]['open'])

def s_consolidation_break(df, i, days=5):
    if i < days + 5: return False
    recent = df.iloc[i-days:i]
    consolidate = (recent['high'].max() - recent['low'].min()) / recent['low'].min() * 100 < 6
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
            df.iloc[i]['vol_ratio'] < 0.9)

def s_engulfing(df, i):
    if i < 5: return False
    prev = df.iloc[i-1]
    curr = df.iloc[i]
    return (prev['close'] < prev['open'] and
            curr['close'] > curr['open'] and
            curr['open'] <= prev['close'] and
            curr['close'] >= prev['open'])

def s_limit_up_open(df, i):
    if i < 5: return False
    return (df.iloc[i-1]['pct_chg'] > 9.5 and
            df.iloc[i]['open'] > df.iloc[i-1]['close'] * 1.02 and
            df.iloc[i]['amplitude'] > 5 and
            df.iloc[i]['close'] > df.iloc[i]['open'])

# === 资金流向策略 ===

def s_main_inflow_break(df, i):
    """主力净流入 + 价格强势"""
    if i < 10: return False
    if 'main_net_ratio' not in df.columns: return False
    row = df.iloc[i]
    return (row['main_net_ratio'] > 3 and
            row['elg_net_amount'] > 0 and
            row['close'] > row['open'] and
            row['vol_ratio'] > 1.2 and
            row['close'] > row['ma5'])

def s_main_follow(df, i):
    """跟庄：昨日主力流入，今日确认上涨"""
    if i < 10: return False
    if 'main_net_ratio' not in df.columns: return False
    prev = df.iloc[i-1]
    curr = df.iloc[i]
    return (prev['main_net_ratio'] > 5 and
            curr['close'] > curr['open'] and curr['close'] > prev['close'] and
            curr['main_net_ratio'] > 0 and
            curr['vol_ratio'] > 1.0)

def s_main_first_red(df, i):
    """连阴后首阳+主力流入"""
    if i < 5: return False
    if 'main_net_ratio' not in df.columns: return False
    blues = sum(1 for j in range(1, 4) if df.iloc[i-j]['close'] < df.iloc[i-j]['open'])
    return (blues >= 2 and
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['main_net_ratio'] > 3 and
            df.iloc[i]['rsi14'] < 60)

def s_main_divergence(df, i):
    """价跌主力吸货"""
    if i < 10: return False
    if 'main_net_ratio' not in df.columns: return False
    row = df.iloc[i]
    prev = df.iloc[i-1]
    price_down = row['close'] < prev['close']
    main_in = row['main_net_ratio'] > 3
    lower_shadow = (min(row['close'], row['open']) - row['low']) / row['low'] * 100 > 1
    return price_down and main_in and lower_shadow

def s_main_continuous(df, i):
    """主力连续流入"""
    if i < 10: return False
    if 'main_net_ratio' not in df.columns: return False
    recent = df.iloc[i-2:i+1]
    all_in = all(r['main_net_amount'] > 0 for _, r in recent.iterrows())
    total_ratio = recent['main_net_ratio'].sum()
    return all_in and total_ratio > 8 and df.iloc[i]['close'] >= df.iloc[i]['ma10']

# ===================== 回测框架 =====================

def backtest(df, signal_func, max_hold=8, **kwargs):
    trades = []
    i = 0
    while i < len(df):
        if signal_func(df, i, **kwargs):
            entry_price = df.iloc[i]['close']
            entry_date = df.iloc[i]['trade_date']
            exit_idx = min(i + max_hold, len(df) - 1)
            
            exit_price = df.iloc[exit_idx]['close']
            pnl = (exit_price - entry_price) / entry_price * 100
            trades.append({
                'entry_date': entry_date, 'entry_price': entry_price,
                'exit_date': df.iloc[exit_idx]['trade_date'], 'exit_price': exit_price,
                'hold_days': exit_idx - i, 'pnl': pnl
            })
            i = exit_idx + 1
        else:
            i += 1
    
    if not trades:
        return {'trades': [], 'count': 0, 'win_rate': 0, 'avg_pnl': 0, 'avg_win': 0, 'avg_loss': 0, 'total_pnl': 0, 'profit_factor': 0, 'max_dd': 0, 'avg_hold': 0}
    
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
        'trades': trades,
        'count': len(trades),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_pnl': np.mean([t['pnl'] for t in trades]),
        'avg_win': np.mean(wins) if wins else 0,
        'avg_loss': np.mean(losses) if losses else 0,
        'profit_factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf'),
        'total_pnl': total_pnl,
        'max_dd': max(dd),
        'avg_hold': np.mean([t['hold_days'] for t in trades])
    }

# ===================== 主程序 =====================

if __name__ == '__main__':
    print("=" * 100)
    print("英维克 (002837) 深度策略分析 - 含主力资金流向")
    print("=" * 100)
    
    df, has_mf = get_data()
    df = calc_indicators(df, has_mf)
    
    print(f"\n【基础统计】")
    print(f"  数据期间: {df['trade_date'].min()} ~ {df['trade_date'].max()} ({len(df)}个交易日)")
    print(f"  价格区间: {df['low'].min():.2f} ~ {df['high'].max():.2f}")
    print(f"  期末涨跌幅: {(df.iloc[-1]['close'] / df.iloc[0]['close'] - 1) * 100:.2f}%")
    print(f"  平均振幅: {df['amplitude'].mean():.2f}%")
    print(f"  涨停次数(>9.5%): {(df['pct_chg'] > 9.5).sum()}")
    print(f"  大跌次数(<-5%): {(df['pct_chg'] < -5).sum()}")
    
    if has_mf:
        print(f"\n【资金流向统计】")
        print(f"  主力净流入天数: {(df['main_net_amount'] > 0).sum()} / {len(df)}")
        print(f"  主力强流入天数(>5%): {(df['main_net_ratio'] > 5).sum()}")
        print(f"  特大单净流入天数: {(df['elg_net_amount'] > 0).sum()}")
        print(f"  平均主力净流入占比: {df['main_net_ratio'].mean():.2f}%")
        print(f"  平均特大单净流入占比: {df['elg_net_ratio'].mean():.2f}%")
        main_up = df[df['main_net_amount'] > 0]['change_pct'].mean()
        main_down = df[df['main_net_amount'] < 0]['change_pct'].mean()
        print(f"  主力流入日平均涨幅: {main_up:.2f}%")
        print(f"  主力流出日平均涨幅: {main_down:.2f}%")
    
    # 策略列表
    strategies = [
        ('放量突破(v1.5)', s_vol_breakout, {'vol_mult': 1.5, 'min_amp': 2.5}),
        ('放量突破(v1.2)', s_vol_breakout, {'vol_mult': 1.2, 'min_amp': 2.0}),
        ('RSI超跌反弹', s_rsi_bounce, {'rsi_thresh': 35}),
        ('跳空高开', s_gap_up, {'min_gap': 0.8, 'max_gap': 5.0}),
        ('MACD金叉', s_macd_cross, {}),
        ('KDJ金叉', s_kdj_golden, {}),
        ('盘整突破', s_consolidation_break, {'days': 5}),
        ('强势股回调', s_pullback, {}),
        ('阳线吞没', s_engulfing, {}),
        ('涨停回封', s_limit_up_open, {}),
    ]
    
    if has_mf:
        strategies.extend([
            ('主力净流入突破', s_main_inflow_break, {}),
            ('跟庄确认', s_main_follow, {}),
            ('连阴首阳+主力', s_main_first_red, {}),
            ('价跌主力吸货', s_main_divergence, {}),
            ('主力连续流入', s_main_continuous, {}),
        ])
    
    results = []
    for name, func, params in strategies:
        res = backtest(df, func, max_hold=8, **params)
        display_name = name
        results.append({'name': display_name, **res})
    
    # 组合策略
    def combo_tech(df, i):
        return (s_vol_breakout(df, i, vol_mult=1.5, min_amp=2.5) or 
                s_engulfing(df, i) or
                s_consolidation_break(df, i, days=5))
    
    def combo_all(df, i):
        signals = [combo_tech(df, i)]
        if has_mf:
            signals.extend([
                s_main_inflow_break(df, i),
                s_main_follow(df, i),
                s_main_first_red(df, i)
            ])
        return any(signals)
    
    results.append({'name': '组合(纯技术)', **backtest(df, combo_tech, max_hold=8)})
    results.append({'name': '组合(全部)', **backtest(df, combo_all, max_hold=8)})
    
    # 排序显示
    results.sort(key=lambda x: x['total_pnl'], reverse=True)
    
    print(f"\n{'='*100}")
    print("策略回测结果（按总收益排序）")
    print(f"{'='*100}")
    print(f"{'策略名称':<35} {'次数':>5} {'胜率%':>8} {'总收益%':>10} {'盈亏比':>8} {'回撤%':>8} {'持仓':>6}")
    print("-" * 100)
    for r in results:
        print(f"{r['name']:<35} {r['count']:>5} {r['win_rate']:>8.1f} {r['total_pnl']:>10.2f} {r['profit_factor']:>8.2f} {r['max_dd']:>8.2f} {r['avg_hold']:>6.1f}")
    
    # 高胜率策略
    print(f"\n{'='*100}")
    print("高胜率策略（交易>=3次, 胜率>=60%）")
    print(f"{'='*100}")
    good = [r for r in results if r['count'] >= 3 and r['win_rate'] >= 60 and r['total_pnl'] > 0]
    good.sort(key=lambda x: x['total_pnl'], reverse=True)
    if good:
        print(f"{'策略名称':<35} {'次数':>5} {'胜率%':>8} {'总收益%':>10} {'盈亏比':>8} {'回撤%':>8}")
        for r in good:
            print(f"{r['name']:<35} {r['count']:>5} {r['win_rate']:>8.1f} {r['total_pnl']:>10.2f} {r['profit_factor']:>8.2f} {r['max_dd']:>8.2f}")
    else:
        print("  无满足条件的策略")
    
    # TOP策略逐笔
    print(f"\n{'='*100}")
    print("TOP 5 策略逐笔交易详情")
    print(f"{'='*100}")
    for r in results[:5]:
        if r['count'] == 0:
            continue
        print(f"\n【{r['name']}】交易{r['count']}次, 胜率{r['win_rate']:.1f}%, 总收益{r['total_pnl']:.2f}%")
        print(f"{'买入日期':<12} {'买入价':>8} {'卖出日期':<12} {'卖出价':>8} {'天数':>4} {'盈亏%':>8}")
        for t in r['trades']:
            print(f"{t['entry_date']:<12} {t['entry_price']:>8.2f} {t['exit_date']:<12} {t['exit_price']:>8.2f} {t['hold_days']:>4} {t['pnl']:>+8.2f}")
    
    # 保存
    save_data = [{k: v for k, v in r.items() if k != 'trades'} for r in results]
    with open('yingweike_results.json', 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到 yingweike_results.json")
