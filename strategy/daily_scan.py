#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日盘后扫描 - 川润股份 & 爱乐达 & 高澜股份
每天北京时间19:00运行，用Tushare完整数据确认信号，
并对比盘中预警（14:45实时扫描结果），跟踪历史信号8天后收益
"""
import tushare as ts
import pandas as pd
import json
import os
import glob
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


def calculate_return(df, signal_date, buy_price):
    """从df中计算signal_date后第8个交易日的收益"""
    df = df.copy()
    df['trade_date_str'] = df['trade_date'].astype(str)
    mask = df['trade_date_str'] == signal_date.replace('-', '')
    if not mask.any():
        return None
    idx = df[mask].index[0]
    sell_idx = idx + 8
    if sell_idx >= len(df):
        return None  # 8天后数据还没到
    sell_row = df.iloc[sell_idx]
    sell_price = float(sell_row['close'])
    return_pct = (sell_price - buy_price) / buy_price * 100
    return {
        'sell_date': str(sell_row['trade_date']),
        'sell_price': round(sell_price, 2),
        'return_pct': round(return_pct, 2)
    }


def update_signal_returns(name, code, df):
    """更新该股票所有历史信号的8天后收益"""
    files = sorted(glob.glob('reports/signal_*.json'))
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            modified = False
            for stock in data['signals']:
                if stock['name'] != name or not stock.get('has_signal'):
                    continue
                # 确保有 buy_price
                if 'buy_price' not in stock:
                    stock['buy_price'] = stock['latest_close']
                    modified = True
                # 计算8天后收益（如果还没算过）
                if 'sell_price' not in stock:
                    signal_date = data['date']
                    result = calculate_return(df, signal_date, stock['buy_price'])
                    if result:
                        stock.update(result)
                        modified = True
                        print(f"  [收益] {name} {signal_date} 买入¥{stock['buy_price']:.2f} -> {result['sell_date']} 卖出¥{result['sell_price']:.2f} ({result['return_pct']:+.2f}%)")
            if modified:
                with open(f, 'w', encoding='utf-8') as fp:
                    json.dump(data, fp, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [警告] 更新{f}失败: {e}")
            continue


def load_realtime_data(date_str):
    """加载当天的盘中预警数据"""
    rt_path = f"reports/realtime_{date_str}.json"
    if not os.path.exists(rt_path):
        return None
    try:
        with open(rt_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  [警告] 读取盘中预警失败: {e}")
        return None


def compare_with_realtime(stock_result, realtime_data):
    """对比盘中预警和盘后确认"""
    if not realtime_data:
        return None
    
    # 找到对应股票的盘中预警
    rt_stock = None
    for s in realtime_data.get('signals', []):
        if s['name'] == stock_result['name']:
            rt_stock = s
            break
    
    if not rt_stock:
        return None
    
    daily_has = stock_result['has_signal']
    realtime_has = rt_stock.get('has_signal', False)
    
    if daily_has and realtime_has:
        match = "match"  # ✅ 盘中预警正确
        note = "盘中预警与盘后确认一致"
    elif daily_has and not realtime_has:
        match = "missed"  # ⚠️ 盘中漏报
        note = "盘中未预警，盘后确认有信号（尾盘异动）"
    elif not daily_has and realtime_has:
        match = "false_alarm"  # ⚠️ 盘中误报
        note = "盘中有预警，盘后确认无信号（尾盘回落）"
    else:
        match = "match"  # ✅ 都观望
        note = "盘中盘后均无信号"
    
    return {
        'match': match,
        'note': note,
        'realtime_has_signal': realtime_has,
        'realtime_time': realtime_data.get('scan_time', ''),
        'realtime_signals': rt_stock.get('signals', []),
        'realtime_indicators': rt_stock.get('indicators', {}),
    }


def main():
    stocks = {
        '川润股份': '002272.SZ',
        '爱乐达': '300696.SZ',
        '高澜股份': '300499.SZ'
    }
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    results = {
        'type': 'daily',
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'date': today_str,
        'data_source': 'tushare',
        'signals': []
    }
    
    # 加载盘中预警数据
    realtime_data = load_realtime_data(today_str)
    if realtime_data:
        print(f"===== 每日策略扫描 {results['scan_time']} =====")
        print(f"盘中预警时间: {realtime_data.get('scan_time', '未知')}\n")
    else:
        print(f"===== 每日策略扫描 {results['scan_time']} =====")
        print("(未找到盘中预警数据)\n")
    
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
        
        # 如果触发信号，记录买入价
        if signals:
            stock_result['buy_price'] = float(latest['close'])
            print(f"  [!] 触发信号: {len(signals)}个")
            for s in signals:
                tag = "[主]" if s['type'] == 'primary' else "[极]" if s['type'] == 'high_confidence' else "[辅]"
                print(f"    {tag} [{s['strategy']}] 置信度:{s['confidence']} - {s['description']}")
        else:
            print(f"  [OK] 无信号")
        
        # 对比盘中预警
        comparison = compare_with_realtime(stock_result, realtime_data)
        if comparison:
            stock_result['realtime_comparison'] = comparison
            emoji = {"match": "✅", "missed": "⚠️", "false_alarm": "⚠️"}.get(comparison['match'], "")
            print(f"  {emoji} 盘中对比: {comparison['note']}")
        
        results['signals'].append(stock_result)
        
        # 更新该股票所有历史信号的8天后收益
        print(f"  更新历史信号收益...")
        update_signal_returns(name, code, df)
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
