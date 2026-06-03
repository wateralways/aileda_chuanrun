#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持股天数敏感性分析 - 川润股份 & 爱乐达
测试持股1~15天的差异
"""
import pandas as pd
import numpy as np
from deep_analysis import load_data, calc_indicators, backtest
from deep_analysis import s_vol_breakout, s_morning_star, s_engulfing, s_break_ma20
from optimize_ald import s_first_red_after_blues, s_volume_climax, s_ma_convergence_break

def combo_cr(df, i):
    return s_vol_breakout(df, i, vol_mult=1.5, min_amp=2.5) or s_morning_star(df, i) or s_engulfing(df, i)

def combo_ald(df, i):
    return s_first_red_after_blues(df, i) or s_volume_climax(df, i) or s_ma_convergence_break(df, i)

print("=" * 110)
print("持股天数敏感性分析")
print("=" * 110)

df_cr = calc_indicators(load_data('002272_SZ_daily.csv'))
df_ald = calc_indicators(load_data('300696_SZ_daily.csv'))

# ==================== 川润股份 ====================
print("\n")
print("=" * 110)
print("川润股份 (002272) - 放量突破策略 (vol_mult=1.5, min_amp=2.5)")
print("=" * 110)
print(f"{'持股天数':>8} {'交易次数':>8} {'胜率%':>8} {'总收益%':>10} {'平均盈亏%':>10} {'盈亏比':>8} {'最大回撤%':>10} {'单笔最大盈%':>10} {'单笔最大亏%':>10}")
print("-" * 110)
for days in range(1, 16):
    res = backtest(df_cr, s_vol_breakout, max_hold=days, vol_mult=1.5, min_amp=2.5)
    wins = [t['pnl'] for t in res['trades'] if t['pnl'] > 0]
    losses = [t['pnl'] for t in res['trades'] if t['pnl'] <= 0]
    max_win = max(wins) if wins else 0
    max_loss = min(losses) if losses else 0
    print(f"{days:>8} {res['count']:>8} {res['win_rate']:>8.1f} {res['total_pnl']:>10.2f} {res['avg_pnl']:>10.2f} {res['profit_factor']:>8.2f} {res['max_dd']:>10.2f} {max_win:>10.2f} {max_loss:>10.2f}")

print("\n")
print("=" * 110)
print("川润股份 (002272) - 组合A策略 (放量突破 + 晨星 + 阳线吞没)")
print("=" * 110)
print(f"{'持股天数':>8} {'交易次数':>8} {'胜率%':>8} {'总收益%':>10} {'平均盈亏%':>10} {'盈亏比':>8} {'最大回撤%':>10} {'单笔最大盈%':>10} {'单笔最大亏%':>10}")
print("-" * 110)
for days in range(1, 16):
    res = backtest(df_cr, combo_cr, max_hold=days)
    wins = [t['pnl'] for t in res['trades'] if t['pnl'] > 0]
    losses = [t['pnl'] for t in res['trades'] if t['pnl'] <= 0]
    max_win = max(wins) if wins else 0
    max_loss = min(losses) if losses else 0
    print(f"{days:>8} {res['count']:>8} {res['win_rate']:>8.1f} {res['total_pnl']:>10.2f} {res['avg_pnl']:>10.2f} {res['profit_factor']:>8.2f} {res['max_dd']:>10.2f} {max_win:>10.2f} {max_loss:>10.2f}")

# ==================== 爱乐达 ====================
print("\n")
print("=" * 110)
print("爱乐达 (300696) - 连阴首阳策略")
print("=" * 110)
print(f"{'持股天数':>8} {'交易次数':>8} {'胜率%':>8} {'总收益%':>10} {'平均盈亏%':>10} {'盈亏比':>8} {'最大回撤%':>10} {'单笔最大盈%':>10} {'单笔最大亏%':>10}")
print("-" * 110)
for days in range(1, 16):
    res = backtest(df_ald, s_first_red_after_blues, max_hold=days)
    wins = [t['pnl'] for t in res['trades'] if t['pnl'] > 0]
    losses = [t['pnl'] for t in res['trades'] if t['pnl'] <= 0]
    max_win = max(wins) if wins else 0
    max_loss = min(losses) if losses else 0
    print(f"{days:>8} {res['count']:>8} {res['win_rate']:>8.1f} {res['total_pnl']:>10.2f} {res['avg_pnl']:>10.2f} {res['profit_factor']:>8.2f} {res['max_dd']:>10.2f} {max_win:>10.2f} {max_loss:>10.2f}")

print("\n")
print("=" * 110)
print("爱乐达 (300696) - 放量见底策略")
print("=" * 110)
print(f"{'持股天数':>8} {'交易次数':>8} {'胜率%':>8} {'总收益%':>10} {'平均盈亏%':>10} {'盈亏比':>8} {'最大回撤%':>10} {'单笔最大盈%':>10} {'单笔最大亏%':>10}")
print("-" * 110)
for days in range(1, 16):
    res = backtest(df_ald, s_volume_climax, max_hold=days)
    wins = [t['pnl'] for t in res['trades'] if t['pnl'] > 0]
    losses = [t['pnl'] for t in res['trades'] if t['pnl'] <= 0]
    max_win = max(wins) if wins else 0
    max_loss = min(losses) if losses else 0
    print(f"{days:>8} {res['count']:>8} {res['win_rate']:>8.1f} {res['total_pnl']:>10.2f} {res['avg_pnl']:>10.2f} {res['profit_factor']:>8.2f} {res['max_dd']:>10.2f} {max_win:>10.2f} {max_loss:>10.2f}")

print("\n")
print("=" * 110)
print("爱乐达 (300696) - 均线粘合突破策略")
print("=" * 110)
print(f"{'持股天数':>8} {'交易次数':>8} {'胜率%':>8} {'总收益%':>10} {'平均盈亏%':>10} {'盈亏比':>8} {'最大回撤%':>10} {'单笔最大盈%':>10} {'单笔最大亏%':>10}")
print("-" * 110)
for days in range(1, 16):
    res = backtest(df_ald, s_ma_convergence_break, max_hold=days)
    wins = [t['pnl'] for t in res['trades'] if t['pnl'] > 0]
    losses = [t['pnl'] for t in res['trades'] if t['pnl'] <= 0]
    max_win = max(wins) if wins else 0
    max_loss = min(losses) if losses else 0
    print(f"{days:>8} {res['count']:>8} {res['win_rate']:>8.1f} {res['total_pnl']:>10.2f} {res['avg_pnl']:>10.2f} {res['profit_factor']:>8.2f} {res['max_dd']:>10.2f} {max_win:>10.2f} {max_loss:>10.2f}")

# 打印逐笔详情（关键天数）
print("\n\n")
print("=" * 110)
print("川润股份 - 放量突破 - 持股3天 vs 5天 vs 8天 vs 12天 逐笔对比")
print("=" * 110)
for days in [3, 5, 8, 12]:
    res = backtest(df_cr, s_vol_breakout, max_hold=days, vol_mult=1.5, min_amp=2.5)
    print(f"\n持股 {days} 天: 交易{res['count']}次, 胜率{res['win_rate']:.1f}%, 总收益{res['total_pnl']:.2f}%")
    if res['count'] > 0:
        for i, t in enumerate(res['trades'], 1):
            print(f"  {i}. {str(t['entry_date'])[:10]} {t['entry_price']:.2f} -> {str(t['exit_date'])[:10]} {t['exit_price']:.2f} ({t['pnl']:+.2f}%) [{t['reason']}]")

print("\n\n")
print("=" * 110)
print("爱乐达 - 连阴首阳 - 持股3天 vs 5天 vs 8天 vs 12天 逐笔对比")
print("=" * 110)
for days in [3, 5, 8, 12]:
    res = backtest(df_ald, s_first_red_after_blues, max_hold=days)
    print(f"\n持股 {days} 天: 交易{res['count']}次, 胜率{res['win_rate']:.1f}%, 总收益{res['total_pnl']:.2f}%")
    if res['count'] > 0:
        for i, t in enumerate(res['trades'], 1):
            print(f"  {i}. {str(t['entry_date'])[:10]} {t['entry_price']:.2f} -> {str(t['exit_date'])[:10]} {t['exit_price']:.2f} ({t['pnl']:+.2f}%) [{t['reason']}]")

print("\n\n分析完成！")
