#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日尾盘扫描 - 川润股份 & 爱乐达
每天14:45运行，检查是否触发买入信号
"""
import tushare as ts
import pandas as pd
import json
import os
import sys
from datetime import datetime
from signals import scan_signals

# Tushare Token（优先从环境变量读取）
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '701a94c30c5d1c7af41602c8ebd47b1ca7a2c49bfdd5419379f40c8d')

def get_daily_data(ts_code, start_date='20260101', end_date=None):
    """获取日线数据"""
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df is None or df.empty:
        return None
    df = df.sort_values('trade_date').reset_index(drop=True)
    return df

def main():
    stocks = {
        '川润股份': '002272.SZ',
        '爱乐达': '300696.SZ',
        '高澜股份': '300499.SZ'
    }
    
    results = {
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'signals': []
    }
    
    print(f"===== 每日策略扫描 {results['scan_time']} =====\n")
    
    for name, code in stocks.items():
        print(f"扫描 {name} ({code})...")
        df = get_daily_data(code)
        if df is None:
            print(f"  获取数据失败")
            continue
        
        latest = df.iloc[-1]
        print(f"  最新日期: {latest['trade_date']}, 收盘: {latest['close']:.2f}, 涨跌幅: {latest['pct_chg']:.2f}%")
        
        signals, latest_row = scan_signals(df, name)
        
        stock_result = {
            'name': name,
            'code': code,
            'latest_date': str(latest['trade_date']),
            'latest_close': float(latest['close']),
            'latest_pct_chg': float(latest['pct_chg']),
            'signals': signals,
            'has_signal': len(signals) > 0,
            'indicators': {
                'vol_ratio': round(float(latest_row['vol_ratio']), 2) if not pd.isna(latest_row['vol_ratio']) else None,
                'rsi14': round(float(latest_row['rsi14']), 2) if not pd.isna(latest_row['rsi14']) else None,
                'rsi6': round(float(latest_row['rsi6']), 2) if not pd.isna(latest_row['rsi6']) else None,
                'macd': round(float(latest_row['macd']), 3) if not pd.isna(latest_row['macd']) else None,
                'amplitude': round(float(latest_row['amplitude']), 2) if not pd.isna(latest_row['amplitude']) else None,
                'bb_pct': round(float(latest_row['bb_pct']), 3) if not pd.isna(latest_row['bb_pct']) else None,
                'price_position': round(float(latest_row['price_position']), 3) if not pd.isna(latest_row['price_position']) else None,
                'up_days': int(latest_row['up_days']),
                'down_days': int(latest_row['down_days']),
            }
        }
        
        results['signals'].append(stock_result)
        
        if signals:
            print(f"  [!] 触发信号: {len(signals)}个")
            for s in signals:
                tag = "[主]" if s['type'] == 'primary' else "[极]" if s['type'] == 'high_confidence' else "[辅]"
                print(f"    {tag} [{s['strategy']}] 置信度:{s['confidence']} - {s['description']}")
        else:
            print(f"  [OK] 无信号")
        print()
    
    # 保存JSON结果
    os.makedirs('reports', exist_ok=True)
    json_path = f"reports/signal_{results['date']}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"结果已保存: {json_path}")
    
    return results

if __name__ == '__main__':
    main()
