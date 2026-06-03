#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印详细交易明细
"""
import pandas as pd
import numpy as np
from deep_analysis import load_data, calc_indicators, backtest
from deep_analysis import s_vol_breakout, s_morning_star, s_engulfing, s_gap_up
from deep_analysis import s_consolidation_break, s_combo1, s_break_ma20

# ========== 川润股份 ==========
print("=" * 90)
print("川润股份 (002272) 详细交易明细")
print("=" * 90)

df_cr = load_data('002272_SZ_daily.csv')
df_cr = calc_indicators(df_cr)

strategies_cr = [
    ("策略1: 放量突破 (vol_mult=1.5, min_amp=2.5)", s_vol_breakout, {'vol_mult': 1.5, 'min_amp': 2.5}),
    ("策略2: 放量突破 (vol_mult=1.2, min_amp=2.0)", s_vol_breakout, {'vol_mult': 1.2, 'min_amp': 2.0}),
    ("策略3: 晨星形态", s_morning_star, {}),
    ("策略4: 阳线吞没", s_engulfing, {}),
    ("策略5: 盘整突破 (days=5, max_range=6)", s_consolidation_break, {'days': 5, 'max_range': 6}),
    ("策略6: 突破MA20", s_break_ma20, {}),
]

def combo_cr(df, i):
    return s_vol_breakout(df, i, vol_mult=1.5, min_amp=2.5) or s_morning_star(df, i) or s_engulfing(df, i)

strategies_cr.append(("组合A: 突破+晨星+吞没", combo_cr, {}))

for name, func, params in strategies_cr:
    res = backtest(df_cr, func, max_hold=8, **params)
    print(f"\n{name}")
    print(f"  总交易: {res['count']}次 | 胜率: {res['win_rate']:.1f}% | 总收益: {res['total_pnl']:.2f}% | 盈亏比: {res['profit_factor']:.2f}")
    if res['count'] > 0:
        print(f"  {'序号':>4} {'买入日期':<12} {'买入价':>8} {'卖出日期':<12} {'卖出价':>8} {'天数':>4} {'盈亏%':>9} {'原因':<12}")
        print("  " + "-" * 85)
        cum = 1
        for i, t in enumerate(res['trades'], 1):
            cum *= (1 + t['pnl'] / 100)
            print(f"  {i:>4} {str(t['entry_date'])[:10]:<12} {t['entry_price']:>8.2f} {str(t['exit_date'])[:10]:<12} {t['exit_price']:>8.2f} {t['hold_days']:>4} {t['pnl']:>+9.2f} {t['reason']:<12}  累计: {(cum-1)*100:.2f}%")

# 带止损止盈的版本
print(f"\n{'=' * 90}")
print("川润股份 组合A + 动态止损止盈")
print(f"{'=' * 90}")
for sl, tp in [(3, 8), (4, 10), (5, 12), (6, 15)]:
    res = backtest(df_cr, combo_cr, max_hold=8, stop_loss=sl, take_profit=tp)
    print(f"\n止损{sl}% + 止盈{tp}%:")
    print(f"  总交易: {res['count']}次 | 胜率: {res['win_rate']:.1f}% | 总收益: {res['total_pnl']:.2f}% | 平均持仓: {res['avg_hold']:.1f}天")
    if res['count'] > 0:
        print(f"  {'序号':>4} {'买入日期':<12} {'买入价':>8} {'卖出日期':<12} {'卖出价':>8} {'天数':>4} {'盈亏%':>9} {'原因':<12}")
        print("  " + "-" * 85)
        for i, t in enumerate(res['trades'], 1):
            print(f"  {i:>4} {str(t['entry_date'])[:10]:<12} {t['entry_price']:>8.2f} {str(t['exit_date'])[:10]:<12} {t['exit_price']:>8.2f} {t['hold_days']:>4} {t['pnl']:>+9.2f} {t['reason']:<12}")


# ========== 爱乐达 ==========
print(f"\n{'=' * 90}")
print("爱乐达 (300696) 详细交易明细")
print(f"{'=' * 90}")

df_ald = load_data('300696_SZ_daily.csv')
df_ald = calc_indicators(df_ald)

# 爱乐达专属策略
from optimize_ald import s_first_red_after_blues, s_volume_climax, s_ma_convergence_break
from optimize_ald import s_range_trap, s_power_gap, s_oversold_bounce

def combo_ald(df, i):
    return s_first_red_after_blues(df, i) or s_volume_climax(df, i) or s_ma_convergence_break(df, i)

strategies_ald = [
    ("策略1: 连阴首阳", s_first_red_after_blues, {}),
    ("策略2: 放量见底", s_volume_climax, {}),
    ("策略3: 均线粘合突破", s_ma_convergence_break, {}),
    ("策略4: 假跌破真反弹", s_range_trap, {}),
    ("策略5: 宽松跳空", s_power_gap, {}),
    ("策略6: 放量突破(v1.5)", s_vol_breakout, {'vol_mult': 1.5, 'min_amp': 2.5}),
    ("策略7: 突破MA20", s_break_ma20, {}),
    ("策略8: 组合(首阳+放量+粘合)", combo_ald, {}),
]

for name, func, params in strategies_ald:
    res = backtest(df_ald, func, max_hold=8, **params)
    print(f"\n{name}")
    print(f"  总交易: {res['count']}次 | 胜率: {res['win_rate']:.1f}% | 总收益: {res['total_pnl']:.2f}% | 盈亏比: {res['profit_factor']:.2f}")
    if res['count'] > 0:
        print(f"  {'序号':>4} {'买入日期':<12} {'买入价':>8} {'卖出日期':<12} {'卖出价':>8} {'天数':>4} {'盈亏%':>9} {'原因':<12}")
        print("  " + "-" * 85)
        cum = 1
        for i, t in enumerate(res['trades'], 1):
            cum *= (1 + t['pnl'] / 100)
            print(f"  {i:>4} {str(t['entry_date'])[:10]:<12} {t['entry_price']:>8.2f} {str(t['exit_date'])[:10]:<12} {t['exit_price']:>8.2f} {t['hold_days']:>4} {t['pnl']:>+9.2f} {t['reason']:<12}  累计: {(cum-1)*100:.2f}%")

# 带止损止盈的版本
print(f"\n{'=' * 90}")
print("爱乐达 连阴首阳 + 动态止损止盈")
print(f"{'=' * 90}")
for sl, tp in [(3, 8), (4, 10), (5, 12)]:
    res = backtest(df_ald, s_first_red_after_blues, max_hold=8, stop_loss=sl, take_profit=tp)
    print(f"\n止损{sl}% + 止盈{tp}%:")
    print(f"  总交易: {res['count']}次 | 胜率: {res['win_rate']:.1f}% | 总收益: {res['total_pnl']:.2f}% | 平均持仓: {res['avg_hold']:.1f}天")
    if res['count'] > 0:
        print(f"  {'序号':>4} {'买入日期':<12} {'买入价':>8} {'卖出日期':<12} {'卖出价':>8} {'天数':>4} {'盈亏%':>9} {'原因':<12}")
        print("  " + "-" * 85)
        for i, t in enumerate(res['trades'], 1):
            print(f"  {i:>4} {str(t['entry_date'])[:10]:<12} {t['entry_price']:>8.2f} {str(t['exit_date'])[:10]:<12} {t['exit_price']:>8.2f} {t['hold_days']:>4} {t['pnl']:>+9.2f} {t['reason']:<12}")

print(f"\n{'=' * 90}")
print("报告完成")
print(f"{'=' * 90}")
