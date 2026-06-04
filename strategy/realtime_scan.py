#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盘中实时扫描 - 基于新浪财经实时行情 + Tushare历史数据
每天北京时间 14:45 运行，生成盘中预警信号

策略逻辑：
- 用 Tushare 获取历史日线数据（用于计算技术指标）
- 用新浪财经获取当天盘中实时价格
- 将实时数据合并到历史数据中，重新计算指标
- 成交量按已过交易时间比例修正，估算全天成交量
- 调用 signals.py 判断信号
- 生成盘中预警报告（JSON + HTML）

注意：盘中数据不完整，量比、振幅等指标为估算值。
      盘中预警仅作参考，以盘后完整数据确认为准。
"""
import requests
import pandas as pd
import json
import os
import tushare as ts
from datetime import datetime, timezone
from signals import scan_signals, calc_indicators

TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '701a94c30c5d1c7af41602c8ebd47b1ca7a2c49bfdd5419379f40c8d')

# 股票配置
STOCKS = {
    '川润股份': '002272.SZ',
    '爱乐达': '300696.SZ',
    '高澜股份': '300499.SZ'
}


def tushare_to_sina_code(ts_code):
    """002272.SZ -> sz002272"""
    code, market = ts_code.split('.')
    prefix = 'sz' if market == 'SZ' else 'sh'
    return f"{prefix}{code}"


def get_sina_realtime(codes):
    """获取新浪财经实时行情
    
    返回格式示例：
    var hq_str_sz002272="川润股份,19.83,19.92,19.64,20.99,19.42,...,2026-06-03,15:00:00,00,";
    
    字段索引：
    0: 名称, 1: 开盘价, 2: 昨日收盘价, 3: 当前价, 4: 最高价, 5: 最低价
    6: 买一价, 7: 卖一价, 8: 成交量(股), 9: 成交金额
    30: 日期, 31: 时间
    """
    url = f"https://hq.sinajs.cn/list={','.join(codes)}"
    headers = {'Referer': 'https://finance.sina.com.cn'}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
    except Exception as e:
        print(f"新浪财经接口请求失败: {e}")
        return {}
    
    result = {}
    for line in resp.text.strip().split(';'):
        line = line.strip()
        if not line or 'var hq_str_' not in line:
            continue
        
        try:
            code_key = line.split('=')[0].replace('var hq_str_', '')
            data_part = line.split('="')[1].rstrip('"')
            parts = data_part.split(',')
            
            if len(parts) < 32:
                continue
            
            result[code_key] = {
                'name': parts[0],
                'open': float(parts[1]),
                'prev_close': float(parts[2]),
                'current': float(parts[3]),
                'high': float(parts[4]),
                'low': float(parts[5]),
                'volume': int(parts[8]),      # 股数
                'amount': float(parts[9]),    # 成交金额
                'date': parts[30],
                'time': parts[31],
            }
        except (IndexError, ValueError) as e:
            print(f"解析 {line[:50]}... 失败: {e}")
            continue
    
    return result


def trading_minutes_elapsed(hour, minute):
    """计算当天已过的交易分钟数
    
    A股交易时间：
    - 上午 9:30-11:30 = 120分钟
    - 下午 13:00-15:00 = 120分钟
    - 全天 240分钟
    """
    if hour < 9 or (hour == 9 and minute < 30):
        return 0
    if hour < 11 or (hour == 11 and minute <= 30):
        return (hour - 9) * 60 + minute - 30
    if hour < 13:
        return 120  # 午休期间
    if hour < 15 or (hour == 15 and minute == 0):
        return 120 + (hour - 13) * 60 + minute
    return 240


def estimate_full_day_volume(current_volume, time_str):
    """根据已过交易时间，估算全天成交量"""
    try:
        h, m, _ = map(int, time_str.split(':'))
    except ValueError:
        return current_volume
    
    elapsed = trading_minutes_elapsed(h, m)
    if elapsed <= 0:
        return current_volume
    
    # 线性外推：全天成交量 ≈ 当前成交量 / (已过分钟 / 240)
    # 但实际尾盘成交量通常更大，所以用 sqrt 衰减修正
    base_ratio = elapsed / 240.0
    adjusted_ratio = base_ratio ** 0.85  # 0.85 衰减因子，尾盘成交量更大
    
    estimated = int(current_volume / adjusted_ratio)
    return estimated


def get_tushare_history(ts_code, today_str):
    """获取Tushare历史日线数据（不含今天）"""
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    
    df = pro.daily(ts_code=ts_code, start_date='20260101', end_date=today_str)
    if df is None or df.empty:
        return None
    
    df = df.sort_values('trade_date').reset_index(drop=True)
    
    # 如果最后一天是今天，去掉（因为盘中时Tushare今天数据通常还没更新）
    if str(df.iloc[-1]['trade_date']) == today_str:
        df = df.iloc[:-1].reset_index(drop=True)
    
    return df


def merge_realtime_data(df_history, rt):
    """将新浪财经实时数据合并到Tushare历史数据中"""
    today_date = rt['date'].replace('-', '')
    
    # 估算全天成交量
    estimated_vol = estimate_full_day_volume(rt['volume'], rt['time'])
    
    today_row = {
        'ts_code': None,
        'trade_date': today_date,
        'open': rt['open'],
        'high': rt['high'],
        'low': rt['low'],
        'close': rt['current'],
        'pre_close': rt['prev_close'],
        'change': rt['current'] - rt['prev_close'],
        'pct_chg': (rt['current'] - rt['prev_close']) / rt['prev_close'] * 100,
        'vol': estimated_vol,
        'amount': rt['amount'],
    }
    
    # 追加到历史数据
    new_df = pd.concat([df_history, pd.DataFrame([today_row])], ignore_index=True)
    return new_df


def generate_realtime_html(data):
    """生成盘中实时报告 HTML（简化版，部署到 Pages 首页）"""
    date = data['date']
    scan_time = data['scan_time']
    stocks = data['signals']
    
    # 转换时间为北京时间显示
    def bjt_time(utc_str):
        try:
            from datetime import datetime, timedelta
            dt = datetime.strptime(utc_str, '%Y-%m-%d %H:%M:%S')
            dt = dt + timedelta(hours=8)
            return dt.strftime('%H:%M:%S')
        except:
            return utc_str
    
    # 构建芯片
    chips = []
    stock_emojis = {'川润股份': '🔷', '爱乐达': '🔶', '高澜股份': '🔹'}
    buy_count = 0
    for s in stocks:
        is_buy = s['has_signal']
        if is_buy:
            buy_count += 1
            chip_class = 'buy'
            status = '🔥 买入信号'
        else:
            chip_class = 'wait'
            status = '⏳ 观望'
        rt = s['realtime']
        pct = rt['pct_chg']
        color = '#00d4aa' if pct >= 0 else '#ff5050'
        chips.append(f'''
        <div class="chip {chip_class}">
            <div class="dot"></div>
            <div class="name">{stock_emojis.get(s['name'],'')} {s['name']}</div>
            <div class="status">{status}</div>
            <div class="price" style="color:{color}">¥{rt['current']:.2f} ({pct:+.2f}%)</div>
            <div class="time">{rt['time']}</div>
        </div>''')
    
    # 构建股票详情
    sections = []
    for s in stocks:
        rt = s['realtime']
        ind = s['indicators']
        is_buy = s['has_signal']
        section_class = 'buy-active' if is_buy else ''
        pct = rt['pct_chg']
        price_color = 'up' if pct >= 0 else 'down'
        
        if is_buy:
            sig_html = ""
            for sig in s['signals']:
                sig_html += f'''<div class="sig-box buy"><b>🔥 {sig['strategy']}</b> {sig['description']}</div>'''
        else:
            sig_html = '<div class="sig-box wait">⏳ 暂无买入信号</div>'
        
        sections.append(f'''
        <div class="section {section_class}">
            <div class="sec-header">
                <div><b>{s['name']}</b> <span class="code">{s['code']}</span></div>
                <div class="rt-price {price_color}">¥{rt['current']:.2f} <span class="pct">{pct:+.2f}%</span></div>
            </div>
            <div class="sec-body">
                {sig_html}
                <div class="ind-row">
                    <div class="ind"><div class="label">开盘</div><div class="val">{rt['open']:.2f}</div></div>
                    <div class="ind"><div class="label">最高</div><div class="val">{rt['high']:.2f}</div></div>
                    <div class="ind"><div class="label">最低</div><div class="val">{rt['low']:.2f}</div></div>
                    <div class="ind"><div class="label">量比(估)</div><div class="val">{ind.get('vol_ratio','-'):.2f}</div></div>
                    <div class="ind"><div class="label">RSI14</div><div class="val">{ind.get('rsi14','-'):.1f}</div></div>
                </div>
            </div>
        </div>''')
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>⚡ 盘中实时预警 - {date}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; background:#0a0a1a; color:#e0e0e0; min-height:100vh; padding-bottom:20px; }}
.topbar {{ background:linear-gradient(135deg,#1a1a3e,#0f0f2e); padding:14px 16px 10px; border-bottom:1px solid rgba(255,255,255,0.06); }}
.topbar-title {{ font-size:1.05em; font-weight:700; color:#ffaa00; display:flex; align-items:center; gap:6px; }}
.topbar-title::before {{ content:"●"; color:#ff5050; animation:blink 1.5s infinite; }}
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.3}} }}
.topbar-date {{ font-size:0.7em; color:#666; margin-top:3px; }}

.chips {{ display:flex; gap:8px; padding:10px 14px; overflow-x:auto; scrollbar-width:none; }}
.chips::-webkit-scrollbar {{ display:none; }}
.chip {{ flex:0 0 auto; min-width:110px; padding:12px 14px; border-radius:14px; text-align:center; position:relative; overflow:hidden; }}
.chip.buy {{ background:linear-gradient(135deg,rgba(0,212,170,0.15),rgba(0,150,100,0.1)); border:1.5px solid rgba(0,212,170,0.4); }}
.chip.wait {{ background:rgba(255,255,255,0.03); border:1.5px solid rgba(255,255,255,0.08); }}
.chip .dot {{ position:absolute; top:7px; right:7px; width:7px; height:7px; border-radius:50%; }}
.chip.buy .dot {{ background:#00d4aa; box-shadow:0 0 6px #00d4aa; animation:blink 2s infinite; }}
.chip.wait .dot {{ background:#444; }}
.chip .name {{ font-size:0.82em; font-weight:700; color:#fff; }}
.chip .status {{ font-size:0.68em; margin-top:3px; font-weight:600; }}
.chip.buy .status {{ color:#00d4aa; }}
.chip.wait .status {{ color:#666; }}
.chip .price {{ font-size:0.7em; margin-top:2px; }}
.chip .time {{ font-size:0.6em; color:#555; margin-top:2px; }}

.summary {{ margin:10px 14px; padding:12px 14px; border-radius:12px; background:rgba(255,170,0,0.06); border:1px solid rgba(255,170,0,0.15); }}
.summary-row {{ display:flex; justify-content:space-between; align-items:center; }}
.summary-label {{ font-size:0.78em; color:#888; }}
.summary-val {{ font-size:1.2em; font-weight:700; color:#ffaa00; }}
.summary-note {{ font-size:0.7em; color:#666; margin-top:6px; line-height:1.5; }}

.section {{ margin:12px 14px; border-radius:14px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.06); overflow:hidden; }}
.section.buy-active {{ border-color:rgba(0,212,170,0.25); box-shadow:0 0 15px rgba(0,212,170,0.04); }}
.sec-header {{ padding:12px 14px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.04); }}
.sec-header .code {{ font-size:0.65em; color:#888; background:rgba(255,255,255,0.06); padding:1px 6px; border-radius:6px; margin-left:4px; }}
.rt-price {{ font-size:1.1em; font-weight:700; text-align:right; }}
.rt-price.up {{ color:#00d4aa; }}
.rt-price.down {{ color:#ff5050; }}
.rt-price .pct {{ font-size:0.75em; display:block; margin-top:1px; }}
.sec-body {{ padding:12px 14px; }}
.sig-box {{ padding:10px 12px; border-radius:10px; margin-bottom:10px; font-size:0.85em; }}
.sig-box.buy {{ background:linear-gradient(135deg,rgba(0,212,170,0.1),rgba(0,100,80,0.08)); border:1px solid rgba(0,212,170,0.2); color:#00d4aa; }}
.sig-box.wait {{ background:rgba(255,255,255,0.02); border:1px dashed rgba(255,255,255,0.08); text-align:center; color:#666; padding:16px; }}
.ind-row {{ display:flex; gap:6px; overflow-x:auto; scrollbar-width:none; padding-bottom:2px; }}
.ind-row::-webkit-scrollbar {{ display:none; }}
.ind {{ flex:0 0 auto; min-width:70px; text-align:center; padding:8px 10px; background:rgba(0,0,0,0.2); border-radius:8px; }}
.ind .label {{ font-size:0.6em; color:#888; margin-bottom:2px; }}
.ind .val {{ font-size:0.9em; font-weight:700; }}

.footer {{ text-align:center; padding:20px 14px; color:#555; font-size:0.7em; line-height:1.8; }}
.footer a {{ color:#4a90d9; text-decoration:none; }}
</style>
</head>
<body>
<div class="topbar">
    <div class="topbar-title">⚡ 盘中实时预警</div>
    <div class="topbar-date">{date} {bjt_time(scan_time)} | 数据来自新浪财经 | 实时刷新中</div>
</div>
<div class="chips">
    {''.join(chips)}
</div>
<div class="summary">
    <div class="summary-row">
        <span class="summary-label">盘中可买入</span>
        <span class="summary-val">{buy_count} 只</span>
    </div>
    <div class="summary-note">
        ⚠️ 盘中数据不完整，量比/振幅为估算值。<br>
        成交量按交易时间比例修正（当前 {bjt_time(scan_time)}）。<br>
        <b>正式信号以 19:00 盘后确认为准。</b>
    </div>
</div>
{''.join(sections)}
<div class="footer">
    <p><a href="/aileda_chuanrun/docs/strategy.html">📖 策略说明</a> | <a href="https://github.com/wateralways/aileda_chuanrun">📁 GitHub</a></p>
    <p style="margin-top:4px; color:#444;">⚠️ 本报告仅供学习研究，不构成投资建议</p>
</div>
</body>
</html>'''
    
    # 保存盘中报告
    with open('reports/realtime_index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"盘中实时报告已生成: reports/realtime_index.html")



def main():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today_str = now.strftime('%Y%m%d')
    
    results = {
        'type': 'realtime',
        'date': now.strftime('%Y-%m-%d'),
        'scan_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'data_source': 'sina_realtime + tushare_history',
        'note': '盘中数据不完整，量比/振幅为估算值，仅供参考',
        'signals': []
    }
    
    print(f"===== 盘中实时扫描 {results['scan_time']} =====\n")
    
    # 获取新浪财经实时数据
    sina_codes = [tushare_to_sina_code(c) for c in STOCKS.values()]
    realtime_data = get_sina_realtime(sina_codes)
    
    if not realtime_data:
        print("实时数据获取失败，终止扫描")
        return
    
    for name, ts_code in STOCKS.items():
        sina_code = tushare_to_sina_code(ts_code)
        
        if sina_code not in realtime_data:
            print(f"{name}: 实时数据缺失")
            continue
        
        rt = realtime_data[sina_code]
        print(f"\n{name} ({ts_code})")
        print(f"  时间: {rt['date']} {rt['time']}")
        print(f"  开盘: {rt['open']:.2f}  最高: {rt['high']:.2f}  最低: {rt['low']:.2f}")
        print(f"  现价: {rt['current']:.2f}  昨收: {rt['prev_close']:.2f}  涨跌: {(rt['current']-rt['prev_close'])/rt['prev_close']*100:+.2f}%")
        
        # 获取历史数据
        df = get_tushare_history(ts_code, today_str)
        if df is None:
            print(f"  历史数据获取失败")
            continue
        
        # 合并实时数据
        df_merged = merge_realtime_data(df, rt)
        
        # 计算指标
        df_merged = calc_indicators(df_merged)
        
        # 扫描信号
        signals, latest_row = scan_signals(df_merged, name)
        
        stock_result = {
            'name': name,
            'code': ts_code,
            'realtime': {
                'open': rt['open'],
                'high': rt['high'],
                'low': rt['low'],
                'current': rt['current'],
                'volume': rt['volume'],
                'estimated_volume': int(df_merged.iloc[-1]['vol']),
                'pct_chg': round((rt['current'] - rt['prev_close']) / rt['prev_close'] * 100, 2),
                'date': rt['date'],
                'time': rt['time'],
            },
            'has_signal': len(signals) > 0,
            'signals': signals,
            'indicators': {
                'vol_ratio': round(float(latest_row['vol_ratio']), 2) if not pd.isna(latest_row['vol_ratio']) else None,
                'rsi14': round(float(latest_row['rsi14']), 2) if not pd.isna(latest_row['rsi14']) else None,
                'rsi6': round(float(latest_row['rsi6']), 2) if not pd.isna(latest_row['rsi6']) else None,
                'macd': round(float(latest_row['macd']), 3) if not pd.isna(latest_row['macd']) else None,
                'amplitude': round(float(latest_row['amplitude']), 2) if not pd.isna(latest_row['amplitude']) else None,
                'bb_pct': round(float(latest_row['bb_pct']), 3) if not pd.isna(latest_row['bb_pct']) else None,
                'up_days': int(latest_row['up_days']),
                'down_days': int(latest_row['down_days']),
            }
        }
        
        results['signals'].append(stock_result)
        
        if signals:
            print(f"  [!] 盘中预警: {len(signals)}个")
            for s in signals:
                tag = "[主]" if s['type'] == 'primary' else "[极]" if s['type'] == 'high_confidence' else "[辅]"
                print(f"    {tag} [{s['strategy']}] 置信度:{s['confidence']} - {s['description']}")
        else:
            print(f"  [OK] 无信号")
    
    # 保存JSON
    os.makedirs('reports', exist_ok=True)
    json_path = f"reports/realtime_{results['date']}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n盘中预警已保存: {json_path}")
    
    # 生成盘中实时报告 HTML
    generate_realtime_html(results)
    
    return results

if __name__ == '__main__':
    main()
