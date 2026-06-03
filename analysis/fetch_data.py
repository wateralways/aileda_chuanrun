#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取川润股份(002272)和爱乐达(300696)的日线数据
"""
import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 设置token
ts.set_token('701a94c30c5d1c7af41602c8ebd47b1ca7a2c49bfdd5419379f40c8d')
pro = ts.pro_api()

# 股票代码
STOCKS = {
    '川润股份': '002272.SZ',
    '爱乐达': '300696.SZ'
}

def get_daily_data(ts_code, start_date='20260101', end_date=None):
    """获取日线数据并计算基础指标"""
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df is None or df.empty:
        return None
    
    df = df.sort_values('trade_date').reset_index(drop=True)
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    
    # 基础技术指标
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma10'] = df['close'].rolling(window=10).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['vol_ma5'] = df['vol'].rolling(window=5).mean()
    df['vol_ma10'] = df['vol'].rolling(window=10).mean()
    
    # 振幅
    df['amplitude'] = (df['high'] - df['low']) / df['low'] * 100
    # 涨跌幅
    df['change_pct'] = df['close'].pct_change() * 100
    # 实体大小
    df['body'] = abs(df['close'] - df['open']) / df['open'] * 100
    # 上影线
    df['upper_shadow'] = (df['high'] - df[['close', 'open']].max(axis=1)) / df['open'] * 100
    # 下影线
    df['lower_shadow'] = (df[['close', 'open']].min(axis=1) - df['low']) / df['open'] * 100
    
    return df

if __name__ == '__main__':
    for name, code in STOCKS.items():
        print(f"\n{'='*60}")
        print(f"获取 {name} ({code}) 数据...")
        df = get_daily_data(code)
        if df is not None:
            print(f"获取到 {len(df)} 条数据")
            print(f"日期范围: {df['trade_date'].min()} 至 {df['trade_date'].max()}")
            df.to_csv(f'D:/Projects/earn_money/wateralways/chuanrun/analysis/{code.replace(".", "_")}_daily.csv', index=False)
            print(f"数据已保存")
        time.sleep(0.5)
