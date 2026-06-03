#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短线策略回测框架 - 川润股份 & 爱乐达
持股时间不超过8天
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

@dataclass
class Trade:
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    hold_days: int
    pnl_pct: float
    reason: str

class StrategyBacktest:
    def __init__(self, df: pd.DataFrame, name: str):
        self.df = df.copy()
        self.name = name
        self.trades: List[Trade] = []
        self._prepare_indicators()
    
    def _prepare_indicators(self):
        """计算所有技术指标"""
        df = self.df
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=6).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=6).mean()
        rs = gain / loss
        df['rsi6'] = 100 - (100 / (1 + rs))
        
        gain14 = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss14 = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs14 = gain14 / loss14
        df['rsi14'] = 100 - (100 / (1 + rs14))
        
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
        
        # 波动率
        df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean() * 100
        
        # 成交量相关
        df['vol_ratio'] = df['vol'] / df['vol_ma5']
        df['amount_ma5'] = df['amount'].rolling(window=5).mean()
        
        # 价格位置
        df['price_position'] = (df['close'] - df['low'].rolling(20).min()) / (df['high'].rolling(20).max() - df['low'].rolling(20).min())
        
        # 连涨连跌天数
        df['up_days'] = 0
        df['down_days'] = 0
        for i in range(1, len(df)):
            if df.loc[i, 'close'] > df.loc[i-1, 'close']:
                df.loc[i, 'up_days'] = df.loc[i-1, 'up_days'] + 1
                df.loc[i, 'down_days'] = 0
            elif df.loc[i, 'close'] < df.loc[i-1, 'close']:
                df.loc[i, 'down_days'] = df.loc[i-1, 'down_days'] + 1
                df.loc[i, 'up_days'] = 0
            else:
                df.loc[i, 'up_days'] = 0
                df.loc[i, 'down_days'] = 0
        
        # 跳空缺口
        df['gap_up'] = (df['low'] - df['high'].shift(1)) / df['close'].shift(1) * 100
        df['gap_down'] = (df['low'].shift(1) - df['high']) / df['close'].shift(1) * 100
        
        self.df = df
    
    def run_backtest(self, strategy_func, max_holding=8, stop_loss=None, take_profit=None, **kwargs) -> Dict:
        """运行回测"""
        self.trades = []
        
        i = 0
        while i < len(self.df):
            row = self.df.iloc[i]
            
            # 检查是否满足买入条件（只传递策略相关参数）
            if strategy_func(self.df, i, **kwargs):
                entry_price = row['close']
                entry_date = row['trade_date']
                
                # 模拟持有max_holding天
                exit_idx = min(i + max_holding, len(self.df) - 1)
                
                # 检查中间是否有止损或止盈条件
                for j in range(i + 1, exit_idx + 1):
                    future_row = self.df.iloc[j]
                    high_pct = (future_row['high'] - entry_price) / entry_price * 100
                    low_pct = (future_row['low'] - entry_price) / entry_price * 100
                    
                    # 动态止盈止损（可选）
                    if stop_loss is not None and low_pct < -stop_loss:
                        exit_price = entry_price * (1 - stop_loss / 100)
                        exit_date = future_row['trade_date']
                        hold_days = j - i
                        pnl = -stop_loss
                        self.trades.append(Trade(entry_date, entry_price, exit_date, exit_price, hold_days, pnl, 'stop_loss'))
                        i = j + 1
                        break
                    elif take_profit is not None and high_pct > take_profit:
                        exit_price = entry_price * (1 + take_profit / 100)
                        exit_date = future_row['trade_date']
                        hold_days = j - i
                        pnl = take_profit
                        self.trades.append(Trade(entry_date, entry_price, exit_date, exit_price, hold_days, pnl, 'take_profit'))
                        i = j + 1
                        break
                else:
                    # 持有到期
                    future_row = self.df.iloc[exit_idx]
                    exit_price = future_row['close']
                    exit_date = future_row['trade_date']
                    hold_days = exit_idx - i
                    pnl = (exit_price - entry_price) / entry_price * 100
                    self.trades.append(Trade(entry_date, entry_price, exit_date, exit_price, hold_days, pnl, 'time_exit'))
                    i = exit_idx + 1
            else:
                i += 1
        
        return self._calculate_metrics()
    
    def _calculate_metrics(self) -> Dict:
        """计算回测指标"""
        if not self.trades:
            return {
                'total_trades': 0, 'win_rate': 0, 'avg_return': 0,
                'avg_win': 0, 'avg_loss': 0, 'profit_factor': 0,
                'total_return': 0, 'max_drawdown': 0, 'avg_hold_days': 0,
                'trades': []
            }
        
        trades = self.trades
        wins = [t for t in trades if t.pnl_pct > 0]
        losses = [t for t in trades if t.pnl_pct <= 0]
        
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        avg_win = np.mean([t.pnl_pct for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl_pct for t in losses]) if losses else 0
        
        # 盈亏比
        profit_factor = abs(sum(t.pnl_pct for t in wins) / sum(t.pnl_pct for t in losses)) if losses and sum(t.pnl_pct for t in losses) != 0 else float('inf')
        
        # 累计收益（复利）
        cumulative = 1
        for t in trades:
            cumulative *= (1 + t.pnl_pct / 100)
        total_return = (cumulative - 1) * 100
        
        # 最大回撤
        equity_curve = [1]
        for t in trades:
            equity_curve.append(equity_curve[-1] * (1 + t.pnl_pct / 100))
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (peak - equity_curve) / peak * 100
        max_drawdown = max(drawdown) if len(drawdown) > 0 else 0
        
        return {
            'total_trades': len(trades),
            'win_rate': win_rate,
            'avg_return': np.mean([t.pnl_pct for t in trades]),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'avg_hold_days': np.mean([t.hold_days for t in trades]),
            'trades': trades
        }

# ======================== 策略定义 ========================

def strategy_volume_breakout(df, i, vol_threshold=2.0, min_amplitude=3.0):
    """放量突破策略：成交量放大 + 价格突破 + 足够振幅"""
    if i < 20:
        return False
    row = df.iloc[i]
    prev = df.iloc[i-1]
    
    # 放量
    vol_ok = row['vol_ratio'] > vol_threshold
    # 价格突破前高（或接近）
    price_ok = row['close'] > prev['high'] or row['high'] > df.iloc[i-5:i]['high'].max()
    # 振幅足够
    amp_ok = row['amplitude'] > min_amplitude
    # 收盘价在高位
    close_high = row['close'] > row['open']
    
    return vol_ok and price_ok and amp_ok and close_high

def strategy_rsi_bounce(df, i, rsi_low=35, rsi_high=65):
    """RSI超跌反弹策略"""
    if i < 20:
        return False
    row = df.iloc[i]
    prev = df.iloc[i-1]
    
    # RSI从低位回升
    rsi_up = prev['rsi6'] < rsi_low and row['rsi6'] > prev['rsi6']
    # 缩量（抛压减轻）
    vol_shrink = row['vol_ratio'] < 1.0
    # 有下影线（支撑）
    support = row['lower_shadow'] > row['body']
    # 价格不在高位
    not_high = row['price_position'] < 0.5
    
    return rsi_up and support and not_high

def strategy_gap_up(df, i, min_gap=1.5, max_gap=5.0):
    """跳空高开策略"""
    if i < 5:
        return False
    row = df.iloc[i]
    
    gap = row['gap_up']
    gap_ok = min_gap < gap < max_gap
    # 不回补缺口
    no_fill = row['low'] > df.iloc[i-1]['high']
    # 放量
    vol_ok = row['vol_ratio'] > 1.2
    # 趋势向上
    trend_ok = row['close'] > row['ma5'] > row['ma10']
    
    return gap_ok and no_fill and vol_ok and trend_ok

def strategy_macd_turn(df, i):
    """MACD金叉策略"""
    if i < 30:
        return False
    row = df.iloc[i]
    prev = df.iloc[i-1]
    
    # MACD金叉
    macd_cross = prev['macd'] < prev['macd_signal'] and row['macd'] > row['macd_signal']
    # 在零轴附近或上方
    macd_pos = row['macd'] > -0.5
    # 放量确认
    vol_ok = row['vol_ratio'] > 1.0
    # 非超买
    not_overbought = row['rsi14'] < 70
    
    return macd_cross and macd_pos and vol_ok and not_overbought

def strategy_kdj_golden(df, i, j_max=20):
    """KDJ金叉策略，J值在低位"""
    if i < 20:
        return False
    row = df.iloc[i]
    prev = df.iloc[i-1]
    
    # KDJ金叉
    kdj_cross = prev['k'] < prev['d'] and row['k'] > row['d']
    # J值低位
    j_low = row['j'] < j_max
    # 价格相对低位
    price_low = row['price_position'] < 0.4
    # 有支撑
    support = row['lower_shadow'] > 0.5
    
    return kdj_cross and j_low and price_low and support

def strategy_bb_bounce(df, i):
    """布林带下轨反弹策略"""
    if i < 20:
        return False
    row = df.iloc[i]
    prev = df.iloc[i-1]
    
    # 触及或跌破下轨后反弹
    touch_lower = prev['low'] <= prev['bb_lower'] or prev['bb_pct'] < 0.1
    bounce = row['close'] > row['open'] and row['close'] > prev['close']
    # 缩量
    vol_shrink = row['vol_ratio'] < 1.2
    # RSI不过高
    rsi_ok = row['rsi14'] < 50
    
    return touch_lower and bounce and vol_shrink and rsi_ok

def strategy_consolidation_break(df, i, days=5):
    """盘整突破策略"""
    if i < days + 5:
        return False
    row = df.iloc[i]
    
    # 近期盘整（波动小）
    recent = df.iloc[i-days:i]
    consolidation = recent['amplitude'].mean() < 3.5
    range_bound = (recent['high'].max() - recent['low'].min()) / recent['low'].min() * 100 < 6
    
    # 今日突破
    break_out = row['close'] > recent['high'].max() and row['amplitude'] > 3
    # 放量
    vol_ok = row['vol_ratio'] > 1.5
    # 收盘价强势
    strong_close = row['close'] > row['open'] and (row['high'] - row['close']) < (row['close'] - row['open'])
    
    return consolidation and range_bound and break_out and vol_ok and strong_close

def strategy_momentum_pullback(df, i):
    """强势股回调买入策略"""
    if i < 10:
        return False
    row = df.iloc[i]
    
    # 前期强势（5日内有大幅上涨）
    recent_high = df.iloc[i-5:i]['high'].max()
    recent_low = df.iloc[i-5:i]['low'].min()
    strong_before = (recent_high - recent_low) / recent_low * 100 > 8
    
    # 今日回调但不破关键位
    pullback = row['close'] < df.iloc[i-1]['close']
    above_ma5 = row['low'] > row['ma5'] * 0.98
    # 缩量回调
    vol_shrink = row['vol_ratio'] < 0.8
    # 有下影线
    support = row['lower_shadow'] > row['upper_shadow']
    
    return strong_before and pullback and above_ma5 and vol_shrink and support

def strategy_limit_up_open(df, i):
    """涨停开板回封策略（模拟）"""
    if i < 5:
        return False
    row = df.iloc[i]
    prev = df.iloc[i-1]
    
    # 昨日涨停或大涨
    prev_limit = prev['pct_chg'] > 9.5
    # 今日高开
    gap_up = row['open'] > prev['close'] * 1.02
    # 有开板迹象（从高位回落）但尾盘收强
    volatile = row['amplitude'] > 5
    close_strong = row['close'] > row['open'] and row['close'] > (row['high'] + row['low']) / 2
    # 巨量换手
    high_vol = row['vol_ratio'] > 2.0
    
    return prev_limit and gap_up and volatile and close_strong and high_vol

def strategy_combined_1(df, i):
    """组合策略1：量价突破 + MACD确认"""
    if i < 30:
        return False
    row = df.iloc[i]
    prev = df.iloc[i-1]
    
    # 放量
    vol_ok = row['vol_ratio'] > 1.8
    # 突破
    break_ok = row['close'] > df.iloc[i-3:i]['high'].max()
    # MACD向上
    macd_ok = row['macd'] > row['macd_signal'] and row['macd_hist'] > prev['macd_hist']
    # RSI适中
    rsi_ok = 40 < row['rsi6'] < 70
    # 振幅
    amp_ok = row['amplitude'] > 2.5
    
    return vol_ok and break_ok and macd_ok and rsi_ok and amp_ok

def strategy_combined_2(df, i):
    """组合策略2：超跌反弹多指标共振"""
    if i < 20:
        return False
    row = df.iloc[i]
    
    # 连续下跌后
    down_ok = row['down_days'] >= 2 or df.iloc[i-3:i]['change_pct'].sum() < -5
    # RSI低位金叉
    rsi_ok = row['rsi6'] < 40 and row['rsi6'] > df.iloc[i-1]['rsi6']
    # KDJ低位
    kdj_ok = row['j'] < 30
    # 布林带下轨附近
    bb_ok = row['bb_pct'] < 0.2
    # 有下影线支撑
    support = row['lower_shadow'] > row['body']
    # 缩量（抛压枯竭）
    vol_shrink = row['vol_ratio'] < 0.9
    
    return down_ok and rsi_ok and kdj_ok and bb_ok and support and vol_shrink

def strategy_combined_3(df, i):
    """组合策略3：趋势跟随回调买"""
    if i < 20:
        return False
    row = df.iloc[i]
    
    # 中期趋势向上
    trend_up = row['ma10'] > df.iloc[i-5]['ma10']
    # 短期回调
    pullback = row['close'] < row['ma5'] and row['close'] > row['ma10']
    # 缩量
    vol_ok = row['vol_ratio'] < 1.0
    # 未超买
    rsi_ok = row['rsi14'] < 60
    # 有支撑形态
    support = row['lower_shadow'] > 0.8
    
    return trend_up and pullback and vol_ok and rsi_ok and support


# ======================== 运行回测 ========================

def run_all_backtests(df, stock_name):
    """运行所有策略回测"""
    bt = StrategyBacktest(df, stock_name)
    
    strategies = [
        ('放量突破', strategy_volume_breakout, {'vol_threshold': 2.0, 'min_amplitude': 3.0}),
        ('放量突破(v1.5)', strategy_volume_breakout, {'vol_threshold': 1.5, 'min_amplitude': 2.5}),
        ('放量突破(v3_amp2)', strategy_volume_breakout, {'vol_threshold': 3.0, 'min_amplitude': 2.0}),
        ('RSI超跌反弹', strategy_rsi_bounce, {'rsi_low': 35}),
        ('RSI超跌反弹(宽松)', strategy_rsi_bounce, {'rsi_low': 40}),
        ('RSI超跌反弹(严格)', strategy_rsi_bounce, {'rsi_low': 30}),
        ('跳空高开', strategy_gap_up, {'min_gap': 1.5, 'max_gap': 5.0}),
        ('跳空高开(小)', strategy_gap_up, {'min_gap': 0.8, 'max_gap': 3.0}),
        ('MACD金叉', strategy_macd_turn, {}),
        ('KDJ金叉', strategy_kdj_golden, {'j_max': 20}),
        ('KDJ金叉(极低位)', strategy_kdj_golden, {'j_max': 10}),
        ('布林带反弹', strategy_bb_bounce, {}),
        ('盘整突破', strategy_consolidation_break, {'days': 5}),
        ('盘整突破(3日)', strategy_consolidation_break, {'days': 3}),
        ('强势股回调', strategy_momentum_pullback, {}),
        ('涨停回封', strategy_limit_up_open, {}),
        ('组合策略1(量价+MACD)', strategy_combined_1, {}),
        ('组合策略2(超跌共振)', strategy_combined_2, {}),
        ('组合策略3(趋势回调)', strategy_combined_3, {}),
    ]
    
    # 也测试带止盈止损的版本
    stop_configs = [
        {},
        {'stop_loss': 5, 'take_profit': 10},
        {'stop_loss': 3, 'take_profit': 8},
        {'stop_loss': 4, 'take_profit': 12},
        {'stop_loss': 6, 'take_profit': 15},
    ]
    
    results = []
    for strat_name, strat_func, params in strategies:
        for stop_config in stop_configs:
            suffix = ''
            stop_params = {}
            if stop_config:
                suffix = f"(止损{stop_config['stop_loss']}%止盈{stop_config['take_profit']}%)"
                stop_params = stop_config
            
            try:
                metrics = bt.run_backtest(strat_func, max_holding=8, **stop_params, **params)
                results.append({
                    'strategy': f"{strat_name}{suffix}",
                    'params': {**params, **stop_params},
                    **metrics
                })
            except Exception as e:
                print(f"策略 {strat_name}{suffix} 运行失败: {e}")
                continue
    
    return results

if __name__ == '__main__':
    import json
    
    for stock_name, file_name in [('川润股份', '002272_SZ_daily.csv'), ('爱乐达', '300696_SZ_daily.csv')]:
        print(f"\n{'='*80}")
        print(f"分析 {stock_name}")
        print(f"{'='*80}")
        
        df = pd.read_csv(f'D:/Projects/earn_money/wateralways/chuanrun/analysis/{file_name}')
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        results = run_all_backtests(df, stock_name)
        
        # 按总收益排序
        results_sorted = sorted(results, key=lambda x: x['total_return'], reverse=True)
        
        print(f"\n{'='*80}")
        print(f"策略回测结果（按总收益排序）")
        print(f"{'='*80}")
        print(f"{'策略名称':<30} {'交易次数':>8} {'胜率%':>8} {'总收益%':>10} {'盈亏比':>8} {'最大回撤%':>10} {'平均持仓':>8}")
        print("-" * 100)
        
        for r in results_sorted[:20]:
            print(f"{r['strategy']:<30} {r['total_trades']:>8} {r['win_rate']:>8.1f} {r['total_return']:>10.2f} {r['profit_factor']:>8.2f} {r['max_drawdown']:>10.2f} {r['avg_hold_days']:>8.1f}")
        
        # 保存结果
        with open(f'D:/Projects/earn_money/wateralways/chuanrun/analysis/{stock_name}_results.json', 'w', encoding='utf-8') as f:
            # 过滤掉不可序列化的对象
            save_results = []
            for r in results:
                save_r = {k: v for k, v in r.items() if k != 'trades'}
                save_results.append(save_r)
            json.dump(save_results, f, ensure_ascii=False, indent=2)
