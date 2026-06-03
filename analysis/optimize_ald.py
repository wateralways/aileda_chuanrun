#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爱乐达针对性策略优化
"""
import pandas as pd
import numpy as np
from deep_analysis import load_data, calc_indicators, backtest

def s_oversold_bounce(df, i, rsi_thresh=30, need_hammer=True):
    """深度超跌反弹"""
    if i < 15: return False
    # 连续大跌或RSI极低
    severe_drop = df.iloc[i]['down_days'] >= 3 or df.iloc[i]['rsi14'] < rsi_thresh
    # 今日止跌回升
    bounce = df.iloc[i]['close'] > df.iloc[i]['open'] and df.iloc[i]['close'] > df.iloc[i-1]['close']
    # 缩量
    vol_shrink = df.iloc[i]['vol_ratio'] < 1.0
    if need_hammer:
        bounce = bounce and df.iloc[i]['lower_shadow'] > df.iloc[i]['body']
    return severe_drop and bounce and vol_shrink

def s_double_bottom(df, i):
    """双底形态"""
    if i < 15: return False
    # 寻找近期低点
    recent = df.iloc[i-15:i]
    lows = recent['low'].values
    # 找到两个相近的低点
    for j in range(5, len(lows)-5):
        if abs(lows[j] - lows[-1]) / lows[j] < 0.03:  # 低点接近
            # 中间有反弹
            if max(lows[j:j+5]) > lows[j] * 1.03:
                return df.iloc[i]['close'] > df.iloc[i]['open'] and df.iloc[i]['vol_ratio'] > 1.0
    return False

def s_volume_climax(df, i):
    """放量见底（成交量极大但价格不再跌）"""
    if i < 10: return False
    # 成交量是近期最高
    high_vol = df.iloc[i]['vol'] == df.iloc[i-10:i+1]['vol'].max()
    # 但价格跌幅不大或收红
    price_ok = df.iloc[i]['close'] >= df.iloc[i]['open'] * 0.99
    # 前期有下跌
    prior_drop = df.iloc[i-5:i]['change_pct'].sum() < -5
    return high_vol and price_ok and prior_drop

def s_ma_convergence_break(df, i):
    """均线粘合突破"""
    if i < 25: return False
    # MA5, MA10, MA20接近
    ma5, ma10, ma20 = df.iloc[i]['ma5'], df.iloc[i]['ma10'], df.iloc[i]['ma20']
    convergence = max(ma5, ma10, ma20) / min(ma5, ma10, ma20) < 1.03
    # 突破向上
    break_up = df.iloc[i]['close'] > max(ma5, ma10, ma20) and df.iloc[i]['close'] > df.iloc[i]['open']
    # 放量
    vol_ok = df.iloc[i]['vol_ratio'] > 1.3
    return convergence and break_up and vol_ok

def s_atr_compression_break(df, i):
    """ATR压缩后突破"""
    if i < 20: return False
    # ATR处于近期低位（波动压缩）
    atr_low = df.iloc[i]['atr_pct'] < df.iloc[i-10:i]['atr_pct'].quantile(0.3)
    # 今日突破
    break_today = df.iloc[i]['amplitude'] > df.iloc[i-5:i]['amplitude'].mean() * 1.5
    break_today = break_today and df.iloc[i]['close'] > df.iloc[i]['open']
    # 放量
    vol_ok = df.iloc[i]['vol_ratio'] > 1.3
    return atr_low and break_today and vol_ok

def s_vwap_bounce(df, i):
    """VWAP/均价支撑反弹"""
    if i < 5: return False
    # 日内VWAP附近获得支撑
    vwap = (df.iloc[i]['amount'] / df.iloc[i]['vol']) if df.iloc[i]['vol'] > 0 else df.iloc[i]['close']
    # 简单用开盘价+收盘价/2代替
    approx_vwap = (df.iloc[i]['open'] + df.iloc[i]['close']) / 2
    # 收盘价在VWAP上方，且下影线长
    support = df.iloc[i]['close'] > approx_vwap and df.iloc[i]['lower_shadow'] > 1.0
    # 前期下跌
    prior_drop = df.iloc[i-3:i]['change_pct'].sum() < -3
    return support and prior_drop and df.iloc[i]['close'] > df.iloc[i]['open']

def s_fib_bounce(df, i):
    """斐波那契回撤反弹"""
    if i < 20: return False
    recent_high = df.iloc[i-20:i]['high'].max()
    recent_low = df.iloc[i-20:i]['low'].min()
    if recent_high <= recent_low:
        return False
    # 当前价格接近0.382或0.5回撤位
    fib382 = recent_high - (recent_high - recent_low) * 0.382
    fib50 = recent_high - (recent_high - recent_low) * 0.5
    near_fib = abs(df.iloc[i]['close'] - fib382) / fib382 < 0.02 or abs(df.iloc[i]['close'] - fib50) / fib50 < 0.02
    return near_fib and df.iloc[i]['close'] > df.iloc[i]['open'] and df.iloc[i]['vol_ratio'] < 1.2

def s_range_trap(df, i):
    """区间陷阱/假跌破真反弹"""
    if i < 10: return False
    # 昨日跌破近期低点但今日收回
    if i >= 2:
        prev_low_break = df.iloc[i-1]['close'] < df.iloc[i-5:i-1]['low'].min()
        today_recover = df.iloc[i]['close'] > df.iloc[i-5:i-1]['low'].min() and df.iloc[i]['close'] > df.iloc[i]['open']
        return prev_low_break and today_recover and df.iloc[i]['vol_ratio'] > 1.0
    return False

def s_power_gap(df, i):
    """强势股跳空（更宽松）"""
    if i < 5: return False
    gap = df.iloc[i]['gap']
    # 更小的跳空也接受
    return 0.5 < gap < 5.0 and df.iloc[i]['close'] > df.iloc[i]['open']

def s_first_red_after_blues(df, i):
    """连阴后首阳"""
    if i < 5: return False
    # 前3-5天连续下跌或收阴
    blues = sum(1 for j in range(1, 4) if df.iloc[i-j]['close'] < df.iloc[i-j]['open'])
    return blues >= 2 and df.iloc[i]['close'] > df.iloc[i]['open'] and df.iloc[i]['close'] > df.iloc[i-1]['close']

if __name__ == '__main__':
    df = load_data('300696_SZ_daily.csv')
    df = calc_indicators(df)
    
    print(f"爱乐达针对性策略优化")
    print(f"数据: {len(df)}条, {df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}")
    
    strategies = [
        ('深度超跌反弹', s_oversold_bounce, [{'rsi_thresh': 25}, {'rsi_thresh': 30}, {'rsi_thresh': 35}]),
        ('放量见底', s_volume_climax, [{}]),
        ('均线粘合突破', s_ma_convergence_break, [{}]),
        ('ATR压缩突破', s_atr_compression_break, [{}]),
        ('支撑位反弹', s_vwap_bounce, [{}]),
        ('斐波那契回撤', s_fib_bounce, [{}]),
        ('假跌破真反弹', s_range_trap, [{}]),
        ('宽松跳空', s_power_gap, [{}]),
        ('连阴首阳', s_first_red_after_blues, [{}]),
    ]
    
    all_results = []
    for name, func, param_list in strategies:
        for params in param_list:
            res = backtest(df, func, max_hold=8, **params)
            display_name = name + (f"({params})" if params else "")
            print(f"\n{display_name}:")
            print(f"  交易: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%, 盈亏比: {res['profit_factor']:.2f}")
            if res['trades']:
                for t in res['trades']:
                    print(f"    {str(t['entry_date'])[:10]} {t['entry_price']:.2f} -> {str(t['exit_date'])[:10]} {t['exit_price']:.2f} ({t['pnl']:+.2f}%) [{t['reason']}]")
            all_results.append({'name': display_name, **res})
    
    # 组合策略
    print(f"\n{'='*60}")
    print("组合策略测试")
    print(f"{'='*60}")
    
    def combo_ald_a(df, i):
        return s_oversold_bounce(df, i, rsi_thresh=30) or s_volume_climax(df, i) or s_range_trap(df, i)
    
    def combo_ald_b(df, i):
        return s_power_gap(df, i) or s_ma_convergence_break(df, i) or s_atr_compression_break(df, i)
    
    def combo_ald_c(df, i):
        return (s_oversold_bounce(df, i, rsi_thresh=35) or 
                s_first_red_after_blues(df, i) or 
                s_fib_bounce(df, i) or
                s_vwap_bounce(df, i))
    
    for name, func in [('组合A(超跌)', combo_ald_a), ('组合B(突破)', combo_ald_b), ('组合C(综合)', combo_ald_c)]:
        for stop_cfg in [{}, {'stop_loss': 3, 'take_profit': 8}, {'stop_loss': 4, 'take_profit': 10}, {'stop_loss': 5, 'take_profit': 12}]:
            res = backtest(df, func, max_hold=8, **stop_cfg)
            suffix = f"[SL{stop_cfg['stop_loss']}TP{stop_cfg['take_profit']}]" if stop_cfg else ""
            print(f"\n{name}{suffix}:")
            print(f"  交易: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%, 盈亏比: {res['profit_factor']:.2f}")
            if res['trades']:
                for t in res['trades']:
                    print(f"    {str(t['entry_date'])[:10]} {t['entry_price']:.2f} -> {str(t['exit_date'])[:10]} {t['exit_price']:.2f} ({t['pnl']:+.2f}%) [{t['reason']}]")
