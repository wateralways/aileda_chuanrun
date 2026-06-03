#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度分析 - 川润股份 & 爱乐达
"""
import pandas as pd
import numpy as np
from datetime import datetime
import json

# 读取数据
def load_data(file_name):
    df = pd.read_csv(f'D:/Projects/earn_money/wateralways/chuanrun/analysis/{file_name}')
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    return df

# 计算更多指标
def calc_indicators(df):
    df = df.copy()
    
    # 移动平均线
    for window in [3, 5, 10, 20]:
        df[f'ma{window}'] = df['close'].rolling(window=window).mean()
    
    # 成交量均线
    df['vol_ma5'] = df['vol'].rolling(window=5).mean()
    df['vol_ma10'] = df['vol'].rolling(window=10).mean()
    df['vol_ratio'] = df['vol'] / df['vol_ma5']
    
    # RSI
    delta = df['close'].diff()
    for window in [6, 14]:
        gain = delta.where(delta > 0, 0).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        df[f'rsi{window}'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
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
    
    # ATR
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift(1))
    tr3 = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100
    
    # 振幅和实体
    df['amplitude'] = (df['high'] - df['low']) / df['low'] * 100
    df['body'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['upper_shadow'] = (df['high'] - df[['close', 'open']].max(axis=1)) / df['open'] * 100
    df['lower_shadow'] = (df[['close', 'open']].min(axis=1) - df['low']) / df['open'] * 100
    
    # 涨跌幅
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
    
    # 日内强弱
    df['intraday_strength'] = (df['close'] - df['open']) / (df['high'] - df['low']) * 100
    
    # 偏离度
    df['deviation_ma5'] = (df['close'] - df['ma5']) / df['ma5'] * 100
    df['deviation_ma10'] = (df['close'] - df['ma10']) / df['ma10'] * 100
    
    return df

# 回测函数
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
                    trades.append({
                        'entry_date': entry_date, 'entry_price': entry_price,
                        'exit_date': df.iloc[j]['trade_date'], 'exit_price': entry_price * (1 - stop_loss/100),
                        'hold_days': j - i, 'pnl': pnl, 'reason': 'stop_loss'
                    })
                    i = j + 1
                    break
                elif take_profit and high_pct > take_profit:
                    pnl = take_profit
                    trades.append({
                        'entry_date': entry_date, 'entry_price': entry_price,
                        'exit_date': df.iloc[j]['trade_date'], 'exit_price': entry_price * (1 + take_profit/100),
                        'hold_days': j - i, 'pnl': pnl, 'reason': 'take_profit'
                    })
                    i = j + 1
                    break
            else:
                exit_price = df.iloc[exit_idx]['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'entry_date': entry_date, 'entry_price': entry_price,
                    'exit_date': df.iloc[exit_idx]['trade_date'], 'exit_price': exit_price,
                    'hold_days': exit_idx - i, 'pnl': pnl, 'reason': 'time_exit'
                })
                i = exit_idx + 1
        else:
            i += 1
    
    if not trades:
        return {'trades': [], 'count': 0, 'win_rate': 0, 'avg_pnl': 0, 'total_pnl': 0, 'profit_factor': 0, 'max_dd': 0}
    
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
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['lower_shadow'] > df.iloc[i]['body'])

def s_gap_up(df, i, min_gap=1.0, max_gap=5.0):
    if i < 5: return False
    gap = df.iloc[i]['gap']
    return (min_gap < gap < max_gap and 
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['vol_ratio'] > 1.2)

def s_macd_cross(df, i):
    if i < 30: return False
    return (df.iloc[i-1]['macd'] < df.iloc[i-1]['macd_signal'] and 
            df.iloc[i]['macd'] > df.iloc[i]['macd_signal'] and
            df.iloc[i]['macd'] > -0.5 and
            df.iloc[i]['vol_ratio'] > 1.0)

def s_kdj_low(df, i, j_max=20):
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

def s_limit_up(df, i):
    if i < 5: return False
    return (df.iloc[i-1]['pct_chg'] > 9.5 and
            df.iloc[i]['open'] > df.iloc[i-1]['close'] * 1.02 and
            df.iloc[i]['amplitude'] > 5 and
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['vol_ratio'] > 2.0)

def s_combo1(df, i):
    if i < 20: return False
    return (df.iloc[i]['vol_ratio'] > 1.8 and
            df.iloc[i]['close'] > df.iloc[i-3:i]['high'].max() and
            df.iloc[i]['macd'] > df.iloc[i]['macd_signal'] and
            35 < df.iloc[i]['rsi6'] < 70 and
            df.iloc[i]['amplitude'] > 2.5)

def s_combo2(df, i):
    if i < 20: return False
    return ((df.iloc[i]['down_days'] >= 2 or df.iloc[i-3:i]['change_pct'].sum() < -5) and
            df.iloc[i]['rsi6'] < 40 and df.iloc[i]['rsi6'] > df.iloc[i-1]['rsi6'] and
            df.iloc[i]['j'] < 30 and
            df.iloc[i]['bb_pct'] < 0.2 and
            df.iloc[i]['lower_shadow'] > df.iloc[i]['body'] and
            df.iloc[i]['vol_ratio'] < 0.9)

def s_combo3(df, i):
    if i < 20: return False
    return (df.iloc[i]['ma10'] > df.iloc[i-5]['ma10'] and
            df.iloc[i]['close'] < df.iloc[i]['ma5'] and df.iloc[i]['close'] > df.iloc[i]['ma10'] and
            df.iloc[i]['vol_ratio'] < 1.0 and
            df.iloc[i]['rsi14'] < 60 and
            df.iloc[i]['lower_shadow'] > 0.8)

def s_high_vol_low_price(df, i):
    """低位放量策略"""
    if i < 20: return False
    return (df.iloc[i]['price_position'] < 0.3 and
            df.iloc[i]['vol_ratio'] > 2.0 and
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['rsi6'] < 50)

def s_engulfing(df, i):
    """阳线吞没策略"""
    if i < 5: return False
    prev = df.iloc[i-1]
    curr = df.iloc[i]
    return (prev['close'] < prev['open'] and  # 昨日阴线
            curr['close'] > curr['open'] and   # 今日阳线
            curr['open'] <= prev['close'] and  # 开盘低于昨收
            curr['close'] >= prev['open'] and  # 收盘高于昨开
            curr['vol_ratio'] > 1.2)

def s_morning_star(df, i):
    """晨星形态策略"""
    if i < 5: return False
    d1, d2, d3 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
    return (d1['close'] < d1['open'] and                    # 第一日阴线
            abs(d2['close'] - d2['open']) / d2['open'] * 100 < 1.5 and  # 第二日小实体
            d3['close'] > d3['open'] and                     # 第三日阳线
            d3['close'] > (d1['open'] + d1['close']) / 2 and
            d3['vol_ratio'] > 1.0)

def s_volume_price_divergence(df, i):
    """量价底背离"""
    if i < 10: return False
    # 价格创新低但成交量缩小，且RSI未创新低
    price_lower = df.iloc[i]['close'] < df.iloc[i-5:i]['close'].min()
    vol_lower = df.iloc[i]['vol'] < df.iloc[i-5:i]['vol'].mean() * 0.8
    rsi_not_low = df.iloc[i]['rsi6'] > df.iloc[i-5:i]['rsi6'].min()
    return price_lower and vol_lower and rsi_not_low and df.iloc[i]['close'] > df.iloc[i]['open']

def s_break_ma20(df, i):
    """突破20日均线"""
    if i < 25: return False
    return (df.iloc[i-1]['close'] < df.iloc[i-1]['ma20'] and
            df.iloc[i]['close'] > df.iloc[i]['ma20'] and
            df.iloc[i]['vol_ratio'] > 1.3 and
            df.iloc[i]['close'] > df.iloc[i]['open'])

def s_support_bounce(df, i):
    """支撑位反弹（多次触及同一低点）"""
    if i < 10: return False
    recent_lows = df.iloc[i-10:i]['low']
    # 找到近期低点区域
    low_range = recent_lows.min() * 1.02
    touches = (recent_lows <= low_range).sum()
    return (touches >= 2 and
            df.iloc[i]['low'] <= low_range and
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['lower_shadow'] > 1.0)

# ===================== 主程序 =====================

if __name__ == '__main__':
    strategy_defs = [
        ('放量突破', s_vol_breakout, [{'vol_mult': 1.5, 'min_amp': 2.5}, {'vol_mult': 2.0, 'min_amp': 3.0}, {'vol_mult': 1.2, 'min_amp': 2.0}]),
        ('RSI超跌反弹', s_rsi_bounce, [{'rsi_thresh': 30}, {'rsi_thresh': 35}, {'rsi_thresh': 40}]),
        ('跳空高开', s_gap_up, [{'min_gap': 0.8, 'max_gap': 3.0}, {'min_gap': 1.5, 'max_gap': 5.0}]),
        ('MACD金叉', s_macd_cross, [{}]),
        ('KDJ金叉低位', s_kdj_low, [{'j_max': 15}, {'j_max': 20}, {'j_max': 30}]),
        ('布林带反弹', s_bb_bounce, [{}]),
        ('盘整突破', s_consolidation_break, [{'days': 3, 'max_range': 5}, {'days': 5, 'max_range': 6}, {'days': 5, 'max_range': 8}]),
        ('强势股回调', s_pullback, [{}]),
        ('涨停回封', s_limit_up, [{}]),
        ('组合量价MACD', s_combo1, [{}]),
        ('组合超跌共振', s_combo2, [{}]),
        ('组合趋势回调', s_combo3, [{}]),
        ('低位放量', s_high_vol_low_price, [{}]),
        ('阳线吞没', s_engulfing, [{}]),
        ('晨星形态', s_morning_star, [{}]),
        ('量价底背离', s_volume_price_divergence, [{}]),
        ('突破MA20', s_break_ma20, [{}]),
        ('支撑位反弹', s_support_bounce, [{}]),
    ]
    
    stop_configs = [
        {},
        {'stop_loss': 3, 'take_profit': 8},
        {'stop_loss': 4, 'take_profit': 10},
        {'stop_loss': 5, 'take_profit': 12},
        {'stop_loss': 6, 'take_profit': 15},
    ]
    
    all_results = {}
    
    for stock_name, file_name in [('川润股份', '002272_SZ_daily.csv'), ('爱乐达', '300696_SZ_daily.csv')]:
        print(f"\n{'='*80}")
        print(f"分析: {stock_name}")
        print(f"{'='*80}")
        
        df = load_data(file_name)
        df = calc_indicators(df)
        
        print(f"数据: {len(df)}条, 日期: {df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}")
        print(f"价格: {df['low'].min():.2f} ~ {df['high'].max():.2f}, 平均振幅: {df['amplitude'].mean():.2f}%")
        print(f"涨停: {(df['pct_chg'] > 9.5).sum()}次, 跌停: {(df['pct_chg'] < -9.5).sum()}次")
        
        results = []
        for strat_name, strat_func, param_list in strategy_defs:
            for params in param_list:
                for stop_cfg in stop_configs:
                    cfg_name = strat_name
                    if params:
                        cfg_name += f"({str(params).replace(' ', '')})"
                    if stop_cfg:
                        cfg_name += f"[SL{stop_cfg['stop_loss']}TP{stop_cfg['take_profit']}]"
                    
                    try:
                        res = backtest(df, strat_func, max_hold=8, **stop_cfg, **params)
                        results.append({
                            'name': cfg_name,
                            'strategy': strat_name,
                            'params': params,
                            'stop': stop_cfg,
                            **res
                        })
                    except Exception as e:
                        print(f"Error: {cfg_name}: {e}")
        
        # 排序并显示
        results.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        print(f"\n{'='*80}")
        print("TOP 策略（按总收益排序）")
        print(f"{'='*80}")
        print(f"{'策略':<40} {'次数':>6} {'胜率%':>8} {'总收益%':>10} {'盈亏比':>8} {'回撤%':>8} {'持仓':>6}")
        print("-" * 100)
        for r in results[:25]:
            print(f"{r['name']:<40} {r['count']:>6} {r['win_rate']:>8.1f} {r['total_pnl']:>10.2f} {r['profit_factor']:>8.2f} {r['max_dd']:>8.2f} {r['avg_hold']:>6.1f}")
        
        # 按胜率+交易次数过滤
        print(f"\n{'='*80}")
        print("高胜率策略（交易>=3次, 胜率>=60%）")
        print(f"{'='*80}")
        good = [r for r in results if r['count'] >= 3 and r['win_rate'] >= 60 and r['total_pnl'] > 0]
        good.sort(key=lambda x: x['total_pnl'], reverse=True)
        print(f"{'策略':<40} {'次数':>6} {'胜率%':>8} {'总收益%':>10} {'盈亏比':>8} {'回撤%':>8}")
        for r in good[:15]:
            print(f"{r['name']:<40} {r['count']:>6} {r['win_rate']:>8.1f} {r['total_pnl']:>10.2f} {r['profit_factor']:>8.2f} {r['max_dd']:>8.2f}")
        
        all_results[stock_name] = results
        
        # 保存结果
        save_data = []
        for r in results:
            d = {k: v for k, v in r.items() if k != 'trades'}
            save_data.append(d)
        with open(f'D:/Projects/earn_money/wateralways/chuanrun/analysis/{stock_name}_deep_results.json', 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    # 打印推荐策略
    print(f"\n{'='*80}")
    print("最终推荐策略")
    print(f"{'='*80}")
    
    for stock_name in ['川润股份', '爱乐达']:
        print(f"\n【{stock_name}】")
        results = all_results[stock_name]
        
        # 综合评分 = 总收益 * 胜率 / 100 / (最大回撤 + 1)
        for r in results:
            if r['count'] >= 2:
                r['score'] = r['total_pnl'] * (r['win_rate'] / 100) / (r['max_dd'] + 1)
            else:
                r['score'] = -999
        
        best = sorted(results, key=lambda x: x['score'], reverse=True)[:5]
        for i, r in enumerate(best, 1):
            print(f"  {i}. {r['name']}")
            print(f"     交易次数: {r['count']}, 胜率: {r['win_rate']:.1f}%, 总收益: {r['total_pnl']:.2f}%, 盈亏比: {r['profit_factor']:.2f}, 最大回撤: {r['max_dd']:.2f}%")
