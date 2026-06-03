#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略信号定义 - 川润股份 & 爱乐达 & 高澜股份 专用策略
"""
import pandas as pd
import numpy as np

def calc_indicators(df):
    """计算技术指标"""
    df = df.copy()
    df = df.sort_values('trade_date').reset_index(drop=True)
    
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
    
    # 振幅和实体
    df['amplitude'] = (df['high'] - df['low']) / df['low'] * 100
    df['body'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['upper_shadow'] = (df['high'] - df[['close', 'open']].max(axis=1)) / df['open'] * 100
    df['lower_shadow'] = (df[['close', 'open']].min(axis=1) - df['low']) / df['open'] * 100
    
    # 涨跌幅
    df['change_pct'] = df['close'].pct_change() * 100
    df['pct_chg'] = (df['close'] - df['pre_close']) / df['pre_close'] * 100
    
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
    
    return df

# ================== 川润股份策略 ==================

def chuanrun_volume_breakout(df, i, vol_mult=1.5, min_amp=2.5):
    """川润股份: 放量突破策略"""
    if i < 10: return False
    row = df.iloc[i]
    
    return (row['vol_ratio'] > vol_mult and 
            row['amplitude'] > min_amp and
            row['close'] > row['open'] and
            row['close'] > df.iloc[i-1]['high'])

def chuanrun_morning_star(df, i):
    """川润股份: 晨星形态"""
    if i < 5: return False
    d1, d2, d3 = df.iloc[i-2], df.iloc[i-1], df.iloc[i]
    return (d1['close'] < d1['open'] and
            abs(d2['close'] - d2['open']) / d2['open'] * 100 < 1.5 and
            d3['close'] > d3['open'] and
            d3['close'] > (d1['open'] + d1['close']) / 2 and
            d3['vol_ratio'] > 1.0)

def chuanrun_engulfing(df, i):
    """川润股份: 阳线吞没"""
    if i < 5: return False
    prev = df.iloc[i-1]
    curr = df.iloc[i]
    return (prev['close'] < prev['open'] and
            curr['close'] > curr['open'] and
            curr['open'] <= prev['close'] and
            curr['close'] >= prev['open'] and
            curr['vol_ratio'] > 1.2)

def chuanrun_combo_a(df, i):
    """川润股份: 组合A (放量突破 + 晨星 + 阳线吞没)"""
    return (chuanrun_volume_breakout(df, i) or 
            chuanrun_morning_star(df, i) or 
            chuanrun_engulfing(df, i))

# ================== 爱乐达策略 ==================

def aileda_first_red_after_blues(df, i):
    """爱乐达: 连阴首阳策略"""
    if i < 5: return False
    blues = sum(1 for j in range(1, 4) if df.iloc[i-j]['close'] < df.iloc[i-j]['open'])
    return (blues >= 2 and
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['close'] > df.iloc[i-1]['close'] and
            df.iloc[i]['rsi14'] < 60)

def aileda_volume_climax(df, i):
    """爱乐达: 放量见底"""
    if i < 10: return False
    high_vol = df.iloc[i]['vol'] == df.iloc[i-10:i+1]['vol'].max()
    price_ok = df.iloc[i]['close'] >= df.iloc[i]['open'] * 0.99
    prior_drop = df.iloc[i-5:i]['change_pct'].sum() < -5
    return high_vol and price_ok and prior_drop

def aileda_ma_convergence_break(df, i):
    """爱乐达: 均线粘合突破"""
    if i < 25: return False
    ma5, ma10, ma20 = df.iloc[i]['ma5'], df.iloc[i]['ma10'], df.iloc[i]['ma20']
    convergence = max(ma5, ma10, ma20) / min(ma5, ma10, ma20) < 1.03
    break_up = df.iloc[i]['close'] > max(ma5, ma10, ma20) and df.iloc[i]['close'] > df.iloc[i]['open']
    vol_ok = df.iloc[i]['vol_ratio'] > 1.3
    return convergence and break_up and vol_ok

def aileda_combo(df, i):
    """爱乐达: 综合组合策略"""
    return (aileda_first_red_after_blues(df, i) or 
            aileda_volume_climax(df, i) or 
            aileda_ma_convergence_break(df, i))

# ================== 高澜股份策略 ==================

def gaolan_gap_up(df, i, min_gap=0.8, max_gap=5.0):
    """高澜股份: 跳空高开策略"""
    if i < 5: return False
    gap = (df.iloc[i]['open'] - df.iloc[i-1]['close']) / df.iloc[i-1]['close'] * 100
    return (min_gap < gap < max_gap and 
            df.iloc[i]['close'] > df.iloc[i]['open'] and
            df.iloc[i]['vol_ratio'] > 1.2)

# ================== 信号扫描入口 ==================

def scan_signals(df, stock_name):
    """扫描今日是否触发买入信号"""
    df = calc_indicators(df)
    i = len(df) - 1  # 最新一日
    
    signals = []
    if stock_name == '川润股份':
        if chuanrun_volume_breakout(df, i):
            signals.append({
                'strategy': '放量突破',
                'type': 'primary',
                'confidence': '高',
                'description': '成交量放大1.5倍以上，价格突破前高，收阳线'
            })
        if chuanrun_morning_star(df, i):
            signals.append({
                'strategy': '晨星形态',
                'type': 'secondary',
                'confidence': '中',
                'description': '下跌末端出现晨星反转K线组合'
            })
        if chuanrun_engulfing(df, i):
            signals.append({
                'strategy': '阳线吞没',
                'type': 'secondary',
                'confidence': '中',
                'description': '阳线实体完全覆盖前日阴线实体'
            })
    
    elif stock_name == '爱乐达':
        if aileda_first_red_after_blues(df, i):
            signals.append({
                'strategy': '连阴首阳',
                'type': 'primary',
                'confidence': '高',
                'description': '连续阴线后出现首根阳线，RSI<60'
            })
        if aileda_volume_climax(df, i):
            signals.append({
                'strategy': '放量见底',
                'type': 'high_confidence',
                'confidence': '极高',
                'description': '成交量创10日新高，价格止跌，前期跌幅>5%'
            })
        if aileda_ma_convergence_break(df, i):
            signals.append({
                'strategy': '均线粘合突破',
                'type': 'secondary',
                'confidence': '中',
                'description': 'MA5/MA10/MA20粘合后向上突破'
            })
    
    elif stock_name == '高澜股份':
        if gaolan_gap_up(df, i):
            signals.append({
                'strategy': '跳空高开',
                'type': 'primary',
                'confidence': '高',
                'description': '跳空高开0.8%~5.0%，收阳线，放量(vol_ratio>1.2)'
            })
    
    return signals, df.iloc[i]
