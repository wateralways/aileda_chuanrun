#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终策略分析报告
"""
import pandas as pd
import numpy as np
import json
from deep_analysis import load_data, calc_indicators, backtest
from deep_analysis import s_vol_breakout, s_rsi_bounce, s_gap_up, s_macd_cross
from deep_analysis import s_kdj_low, s_bb_bounce, s_consolidation_break, s_pullback
from deep_analysis import s_limit_up, s_combo1, s_combo2, s_combo3
from deep_analysis import s_high_vol_low_price, s_engulfing, s_morning_star
from deep_analysis import s_volume_price_divergence, s_break_ma20, s_support_bounce

def print_trade_details(trades, stock_name):
    print(f"\n【{stock_name}】逐笔交易详情:")
    print(f"{'买入日期':<12} {'买入价':>8} {'卖出日期':<12} {'卖出价':>8} {'持有':>4} {'盈亏%':>8} {'原因':<12}")
    for t in trades:
        print(f"{str(t['entry_date'])[:10]:<12} {t['entry_price']:>8.2f} {str(t['exit_date'])[:10]:<12} {t['exit_price']:>8.2f} {t['hold_days']:>4} {t['pnl']:>8.2f} {t['reason']:<12}")

def analyze_stock(stock_name, file_name):
    df = load_data(file_name)
    df = calc_indicators(df)
    
    print(f"\n{'='*80}")
    print(f"深度分析: {stock_name}")
    print(f"{'='*80}")
    
    # 基础统计
    print(f"\n【基础统计】")
    print(f"  数据期间: {df['trade_date'].min().date()} ~ {df['trade_date'].max().date()} ({len(df)}个交易日)")
    print(f"  价格区间: {df['low'].min():.2f} ~ {df['high'].max():.2f}")
    print(f"  期末涨跌幅: {(df.iloc[-1]['close'] / df.iloc[0]['close'] - 1) * 100:.2f}%")
    print(f"  平均振幅: {df['amplitude'].mean():.2f}%")
    print(f"  平均换手率(估算): {df['vol'].mean() / df['vol'].mean() * 100:.2f}%")
    print(f"  涨停次数(>9.5%): {(df['pct_chg'] > 9.5).sum()}")
    print(f"  大跌次数(<-5%): {(df['pct_chg'] < -5).sum()}")
    print(f"  波动率(20日): {df['close'].rolling(20).std().mean() / df['close'].mean() * 100:.2f}%")
    
    # 月度表现
    df['month'] = df['trade_date'].dt.to_period('M')
    monthly = df.groupby('month').agg({
        'close': ['first', 'last', 'min', 'max'],
        'amplitude': 'mean',
        'vol': 'mean'
    })
    monthly.columns = ['open', 'close', 'low', 'high', 'avg_amp', 'avg_vol']
    monthly['return'] = (monthly['close'] / monthly['open'] - 1) * 100
    print(f"\n【月度表现】")
    for m, row in monthly.iterrows():
        print(f"  {m}: 收益 {row['return']:>7.2f}%, 振幅 {row['avg_amp']:.2f}%, 区间 {row['low']:.2f}~{row['high']:.2f}")
    
    results = {}
    
    # === 测试核心策略 ===
    
    # 1. 放量突破策略
    print(f"\n{'='*80}")
    print("策略1: 放量突破")
    print(f"{'='*80}")
    for params in [{'vol_mult': 1.5, 'min_amp': 2.5}, {'vol_mult': 1.2, 'min_amp': 2.0}]:
        res = backtest(df, s_vol_breakout, max_hold=8, **params)
        key = f"vol_break_{params['vol_mult']}_{params['min_amp']}"
        results[key] = res
        print(f"\n参数 vol_mult={params['vol_mult']}, min_amp={params['min_amp']}:")
        print(f"  交易次数: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%")
        print(f"  平均盈利: {res['avg_win']:.2f}%, 平均亏损: {res['avg_loss']:.2f}%, 盈亏比: {res['profit_factor']:.2f}")
        if res['trades']:
            print_trade_details(res['trades'], stock_name)
    
    # 2. 晨星形态
    print(f"\n{'='*80}")
    print("策略2: 晨星形态")
    print(f"{'='*80}")
    res = backtest(df, s_morning_star, max_hold=8)
    results['morning_star'] = res
    print(f"交易次数: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%")
    if res['trades']:
        print_trade_details(res['trades'], stock_name)
    
    # 3. 阳线吞没
    print(f"\n{'='*80}")
    print("策略3: 阳线吞没")
    print(f"{'='*80}")
    res = backtest(df, s_engulfing, max_hold=8)
    results['engulfing'] = res
    print(f"交易次数: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%")
    if res['trades']:
        print_trade_details(res['trades'], stock_name)
    
    # 4. 跳空高开
    print(f"\n{'='*80}")
    print("策略4: 跳空高开")
    print(f"{'='*80}")
    for params in [{'min_gap': 0.8, 'max_gap': 3.0}, {'min_gap': 1.5, 'max_gap': 5.0}]:
        res = backtest(df, s_gap_up, max_hold=8, **params)
        key = f"gap_{params['min_gap']}_{params['max_gap']}"
        results[key] = res
        print(f"\n参数 min_gap={params['min_gap']}, max_gap={params['max_gap']}:")
        print(f"  交易次数: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%")
        if res['trades']:
            print_trade_details(res['trades'], stock_name)
    
    # 5. 盘整突破
    print(f"\n{'='*80}")
    print("策略5: 盘整突破")
    print(f"{'='*80}")
    for params in [{'days': 3, 'max_range': 5}, {'days': 5, 'max_range': 6}, {'days': 5, 'max_range': 8}]:
        res = backtest(df, s_consolidation_break, max_hold=8, **params)
        key = f"consol_{params['days']}_{params['max_range']}"
        results[key] = res
        print(f"\n参数 days={params['days']}, max_range={params['max_range']}:")
        print(f"  交易次数: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%")
        if res['trades']:
            print_trade_details(res['trades'], stock_name)
    
    # 6. 组合策略
    print(f"\n{'='*80}")
    print("策略6: 组合量价MACD")
    print(f"{'='*80}")
    res = backtest(df, s_combo1, max_hold=8)
    results['combo1'] = res
    print(f"交易次数: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%")
    if res['trades']:
        print_trade_details(res['trades'], stock_name)
    
    # 7. 低位放量
    print(f"\n{'='*80}")
    print("策略7: 低位放量")
    print(f"{'='*80}")
    res = backtest(df, s_high_vol_low_price, max_hold=8)
    results['high_vol_low'] = res
    print(f"交易次数: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%")
    if res['trades']:
        print_trade_details(res['trades'], stock_name)
    
    # 8. 突破MA20
    print(f"\n{'='*80}")
    print("策略8: 突破MA20")
    print(f"{'='*80}")
    res = backtest(df, s_break_ma20, max_hold=8)
    results['break_ma20'] = res
    print(f"交易次数: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%")
    if res['trades']:
        print_trade_details(res['trades'], stock_name)
    
    # === 策略组合测试 ===
    print(f"\n{'='*80}")
    print("策略组合测试")
    print(f"{'='*80}")
    
    def combo_strategy_a(df, i):
        """组合A：放量突破 或 晨星 或 阳线吞没"""
        return s_vol_breakout(df, i, vol_mult=1.5, min_amp=2.5) or s_morning_star(df, i) or s_engulfing(df, i)
    
    def combo_strategy_b(df, i):
        """组合B：放量突破(宽松) 或 跳空高开 或 突破MA20"""
        return s_vol_breakout(df, i, vol_mult=1.2, min_amp=2.0) or s_gap_up(df, i, min_gap=0.8, max_gap=3.0) or s_break_ma20(df, i)
    
    def combo_strategy_c(df, i):
        """组合C：所有强势信号"""
        return (s_vol_breakout(df, i, vol_mult=1.5, min_amp=2.5) or 
                s_morning_star(df, i) or 
                s_engulfing(df, i) or
                s_consolidation_break(df, i, days=5, max_range=6) or
                s_combo1(df, i))
    
    for name, func in [('组合A(突破+晨星+吞没)', combo_strategy_a), 
                       ('组合B(宽松突破+跳空+MA20)', combo_strategy_b),
                       ('组合C(所有强势)', combo_strategy_c)]:
        res = backtest(df, func, max_hold=8)
        print(f"\n{name}:")
        print(f"  交易次数: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%")
        print(f"  平均盈亏: {res['avg_pnl']:.2f}%, 盈亏比: {res['profit_factor']:.2f}, 最大回撤: {res['max_dd']:.2f}%")
        if res['trades']:
            print_trade_details(res['trades'], stock_name)
        results[name] = res
    
    # 带止盈止损的组合
    print(f"\n{'='*80}")
    print("组合策略 + 止盈止损优化")
    print(f"{'='*80}")
    
    for sl, tp in [(3, 8), (4, 10), (5, 12), (6, 15)]:
        res = backtest(df, combo_strategy_c, max_hold=8, stop_loss=sl, take_profit=tp)
        print(f"\n止损{sl}%止盈{tp}%:")
        print(f"  交易次数: {res['count']}, 胜率: {res['win_rate']:.1f}%, 总收益: {res['total_pnl']:.2f}%")
        print(f"  平均持仓: {res['avg_hold']:.1f}天, 最大回撤: {res['max_dd']:.2f}%")
        if res['trades']:
            print_trade_details(res['trades'], stock_name)
    
    return df, results

if __name__ == '__main__':
    cr_df, cr_results = analyze_stock('川润股份', '002272_SZ_daily.csv')
    ald_df, ald_results = analyze_stock('爱乐达', '300696_SZ_daily.csv')
