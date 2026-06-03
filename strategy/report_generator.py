#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML报告生成器 - 生成每日策略扫描报告网页
手机端优化版 - 一眼看全
"""
import json
import os
import glob
from datetime import datetime

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>短线策略日报 - {{date}}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #0a0a1a;
            color: #e0e0e0;
            min-height: 100vh;
            padding-bottom: 20px;
        }
        
        /* 顶部总览 */
        .topbar {
            background: linear-gradient(135deg, #1a1a3e 0%, #0f0f2e 100%);
            padding: 16px 16px 12px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(20px);
        }
        .topbar-title {
            font-size: 1.1em;
            font-weight: 700;
            color: #00d4aa;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .topbar-date {
            font-size: 0.75em;
            color: #666;
            margin-top: 4px;
        }
        
        /* 信号总览条 */
        .overview {
            display: flex;
            gap: 8px;
            padding: 12px 16px;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
        }
        .overview::-webkit-scrollbar { display: none; }
        
        .overview-chip {
            flex: 0 0 auto;
            min-width: 110px;
            padding: 12px 14px;
            border-radius: 14px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .overview-chip.buy {
            background: linear-gradient(135deg, rgba(0,212,170,0.15) 0%, rgba(0,150,100,0.1) 100%);
            border: 1.5px solid rgba(0,212,170,0.4);
        }
        .overview-chip.wait {
            background: rgba(255,255,255,0.03);
            border: 1.5px solid rgba(255,255,255,0.08);
        }
        .overview-chip .chip-stock {
            font-size: 0.85em;
            font-weight: 700;
            color: #fff;
        }
        .overview-chip .chip-status {
            font-size: 0.7em;
            margin-top: 4px;
            font-weight: 600;
        }
        .overview-chip.buy .chip-status { color: #00d4aa; }
        .overview-chip.wait .chip-status { color: #666; }
        .overview-chip .chip-price {
            font-size: 0.65em;
            color: #888;
            margin-top: 2px;
        }
        .overview-chip .dot {
            position: absolute;
            top: 8px;
            right: 8px;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        .overview-chip.buy .dot { background: #00d4aa; box-shadow: 0 0 8px #00d4aa; }
        .overview-chip.wait .dot { background: #444; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        
        /* 汇总卡片 */
        .summary-card {
            margin: 12px 16px;
            padding: 14px 16px;
            border-radius: 14px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.06);
        }
        .summary-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .summary-label { font-size: 0.8em; color: #888; }
        .summary-value {
            font-size: 1.3em;
            font-weight: 700;
        }
        .summary-value.buy { color: #00d4aa; }
        .summary-value.wait { color: #666; }
        .summary-detail {
            font-size: 0.75em;
            color: #666;
            margin-top: 6px;
            line-height: 1.5;
        }
        
        /* 股票详细卡片 */
        .stock-section {
            margin: 16px;
            border-radius: 16px;
            overflow: hidden;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.06);
        }
        .stock-section.buy-active {
            border-color: rgba(0,212,170,0.3);
            box-shadow: 0 0 20px rgba(0,212,170,0.05);
        }
        .stock-header {
            padding: 14px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.04);
        }
        .stock-header-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .stock-emoji { font-size: 1.4em; }
        .stock-title { font-weight: 700; font-size: 1.05em; }
        .stock-code-badge {
            font-size: 0.65em;
            color: #888;
            background: rgba(255,255,255,0.06);
            padding: 2px 8px;
            border-radius: 8px;
        }
        .stock-price {
            text-align: right;
        }
        .stock-price-value {
            font-size: 1.2em;
            font-weight: 700;
        }
        .stock-price-change {
            font-size: 0.75em;
            margin-top: 2px;
        }
        .stock-price-change.up { color: #00d4aa; }
        .stock-price-change.down { color: #ff5050; }
        
        .stock-body { padding: 14px 16px; }
        
        /* 信号区域 */
        .signal-area {
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 12px;
        }
        .signal-area.buy {
            background: linear-gradient(135deg, rgba(0,212,170,0.1) 0%, rgba(0,100,80,0.08) 100%);
            border: 1px solid rgba(0,212,170,0.2);
        }
        .signal-area.wait {
            background: rgba(255,255,255,0.02);
            border: 1px dashed rgba(255,255,255,0.08);
            text-align: center;
            color: #666;
            padding: 20px;
        }
        .signal-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 0.9em;
            font-weight: 700;
            color: #00d4aa;
            margin-bottom: 6px;
        }
        .signal-desc {
            font-size: 0.85em;
            color: #bbb;
            line-height: 1.5;
        }
        .signal-confidence {
            display: inline-block;
            font-size: 0.65em;
            padding: 2px 8px;
            border-radius: 6px;
            background: rgba(0,212,170,0.15);
            color: #00d4aa;
            margin-left: 8px;
            font-weight: 600;
        }
        
        /* 指标横排 */
        .indicators-row {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
            padding-bottom: 4px;
        }
        .indicators-row::-webkit-scrollbar { display: none; }
        .indicators-row .indicator {
            flex: 0 0 auto;
            min-width: 80px;
            text-align: center;
            padding: 10px 12px;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
        }
        .indicators-row .indicator-label {
            font-size: 0.65em;
            color: #888;
            margin-bottom: 4px;
        }
        .indicators-row .indicator-value {
            font-size: 1em;
            font-weight: 700;
        }
        .indicators-row .indicator-value.green { color: #00d4aa; }
        .indicators-row .indicator-value.red { color: #ff5050; }
        .indicators-row .indicator-value.yellow { color: #ffaa00; }
        
        /* 操作提示 */
        .action-tip {
            margin-top: 12px;
            padding: 10px 14px;
            background: rgba(0,212,170,0.06);
            border-radius: 10px;
            border-left: 3px solid #00d4aa;
            font-size: 0.8em;
            color: #ccc;
            line-height: 1.6;
        }
        
        /* 历史记录 */
        .history-section {
            margin: 16px;
        }
        .history-title {
            font-size: 0.85em;
            color: #888;
            margin-bottom: 10px;
            font-weight: 600;
        }
        .history-table {
            width: 100%;
            font-size: 0.8em;
            border-collapse: collapse;
        }
        .history-table th {
            text-align: left;
            padding: 8px 10px;
            color: #888;
            font-weight: 500;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .history-table td {
            padding: 8px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.04);
        }
        .history-table .sig-yes { color: #00d4aa; font-weight: 600; }
        .history-table .sig-no { color: #555; }
        
        .footer {
            text-align: center;
            padding: 24px 16px;
            color: #555;
            font-size: 0.75em;
            line-height: 1.8;
        }
        .footer a { color: #4a90d9; text-decoration: none; }
    </style>
</head>
<body>
    <!-- 顶部栏 -->
    <div class="topbar">
        <div class="topbar-title">📊 短线策略日报</div>
        <div class="topbar-date">{{date}} {{scan_time}} | 持股8天策略</div>
    </div>
    
    <!-- 横向总览 -->
    <div class="overview">
        {{overview_chips}}
    </div>
    
    <!-- 汇总 -->
    {{summary_card}}
    
    <!-- 股票详细 -->
    {{stock_sections}}
    
    <!-- 历史 -->
    <div class="history-section">
        <div class="history-title">📈 近30天信号记录</div>
        <table class="history-table">
            <tr><th>日期</th><th>川润</th><th>爱乐达</th><th>高澜</th></tr>
            {{history_rows}}
        </table>
    </div>
    
    <div class="footer">
        <p><a href="docs/strategy.html">📖 策略详细说明</a> | <a href="https://github.com/wateralways/aileda_chuanrun">📁 GitHub</a></p>
        <p style="margin-top:6px; color:#444;">⚠️ 本报告仅供学习研究，不构成投资建议</p>
    </div>
</body>
</html>
'''

def generate_report(json_path=None):
    """生成HTML报告"""
    if json_path is None:
        files = sorted(glob.glob('reports/signal_*.json'), reverse=True)
        if not files:
            print("没有找到信号文件")
            return
        json_path = files[0]
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    date = data['date']
    scan_time = data['scan_time']
    
    # === 生成顶部总览芯片 ===
    overview_chips = []
    stock_emojis = {'川润股份': '🔷', '爱乐达': '🔶', '高澜股份': '🔹'}
    
    buy_count = 0
    for stock in data['signals']:
        is_buy = stock['has_signal']
        if is_buy:
            buy_count += 1
            chip_class = 'buy'
            status_text = '🔥 买入信号'
        else:
            chip_class = 'wait'
            status_text = '⏳ 观望'
        
        chip = f'''
        <div class="overview-chip {chip_class}">
            <div class="dot"></div>
            <div class="chip-stock">{stock_emojis.get(stock['name'], '')} {stock['name']}</div>
            <div class="chip-status">{status_text}</div>
            <div class="chip-price">¥{stock['latest_close']:.2f} ({stock['latest_pct_chg']:+.2f}%)</div>
        </div>
        '''
        overview_chips.append(chip)
    
    # === 生成汇总卡片 ===
    if buy_count > 0:
        summary_html = f'''
        <div class="summary-card">
            <div class="summary-row">
                <span class="summary-label">今日可买入</span>
                <span class="summary-value buy">{buy_count} 只</span>
            </div>
            <div class="summary-detail">
                {{buy_list}}
            </div>
        </div>
        '''
        buy_names = [s['name'] for s in data['signals'] if s['has_signal']]
        buy_list = '、'.join([f'<b style="color:#00d4aa">{n}</b>' for n in buy_names])
        summary_html = summary_html.replace('{{buy_list}}', f'建议关注：{buy_list}，收盘前确认信号后择机买入')
    else:
        summary_html = f'''
        <div class="summary-card">
            <div class="summary-row">
                <span class="summary-label">今日可买入</span>
                <span class="summary-value wait">0 只</span>
            </div>
            <div class="summary-detail">今日3只股票均无买入信号，继续观望，等待机会。</div>
        </div>
        '''
    
    # === 生成股票详细区域 ===
    stock_sections = []
    for stock in data['signals']:
        ind = stock['indicators']
        is_buy = stock['has_signal']
        section_class = 'buy-active' if is_buy else ''
        
        # 价格颜色
        price_change_class = 'up' if stock['latest_pct_chg'] >= 0 else 'down'
        
        # 信号区域
        if is_buy:
            signals_html = ""
            for sig in stock['signals']:
                conf_tag = f'<span class="signal-confidence">{sig["confidence"]}置信</span>'
                signals_html += f'''
                <div class="signal-area buy">
                    <div class="signal-tag">🔥 {sig['strategy']} {conf_tag}</div>
                    <div class="signal-desc">{sig['description']}</div>
                </div>
                '''
            action_tip = '''
            <div class="action-tip">
                <b>🎯 操作建议：</b>今日收盘前确认信号，可择机买入。买入后严格持有8个交易日。
            </div>
            '''
        else:
            signals_html = '''
            <div class="signal-area wait">
                <div style="font-size:1.1em; margin-bottom:4px;">⏳ 暂无买入信号</div>
                <div>今日未触发策略条件</div>
            </div>
            '''
            action_tip = ''
        
        # 指标横排
        def val_color(val, thresholds):
            if val is None: return ''
            if val > thresholds[1]: return 'red'
            if val < thresholds[0]: return 'green'
            return 'yellow'
        
        vol_color = val_color(ind.get('vol_ratio'), (0.8, 1.5))
        rsi_color = val_color(ind.get('rsi14'), (30, 70))
        
        section = f'''
        <div class="stock-section {section_class}">
            <div class="stock-header">
                <div class="stock-header-left">
                    <span class="stock-emoji">{stock_emojis.get(stock['name'], '📌')}</span>
                    <div>
                        <div class="stock-title">{stock['name']}</div>
                        <span class="stock-code-badge">{stock['code']}</span>
                    </div>
                </div>
                <div class="stock-price">
                    <div class="stock-price-value">¥{stock['latest_close']:.2f}</div>
                    <div class="stock-price-change {price_change_class}">{stock['latest_pct_chg']:+.2f}%</div>
                </div>
            </div>
            <div class="stock-body">
                {signals_html}
                <div class="indicators-row">
                    <div class="indicator">
                        <div class="indicator-label">量比</div>
                        <div class="indicator-value {vol_color}">{ind.get('vol_ratio', '-'):.2f}</div>
                    </div>
                    <div class="indicator">
                        <div class="indicator-label">RSI(14)</div>
                        <div class="indicator-value {rsi_color}">{ind.get('rsi14', '-'):.1f}</div>
                    </div>
                    <div class="indicator">
                        <div class="indicator-label">MACD</div>
                        <div class="indicator-value">{ind.get('macd', '-'):.2f}</div>
                    </div>
                    <div class="indicator">
                        <div class="indicator-label">振幅</div>
                        <div class="indicator-value">{ind.get('amplitude', '-'):.1f}%</div>
                    </div>
                    <div class="indicator">
                        <div class="indicator-label">连涨/跌</div>
                        <div class="indicator-value">{ind.get('up_days', 0)}/{ind.get('down_days', 0)}</div>
                    </div>
                </div>
                {action_tip}
            </div>
        </div>
        '''
        stock_sections.append(section)
    
    # === 历史记录 ===
    history_rows = ""
    files = sorted(glob.glob('reports/signal_*.json'), reverse=True)[:30]
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                d = json.load(fp)
            row_date = d['date']
            cells = []
            for s in d['signals']:
                if s.get('has_signal'):
                    names = [sig['strategy'] for sig in s['signals']]
                    cells.append(f"<span class='sig-yes'>{names[0]}</span>")
                else:
                    cells.append("<span class='sig-no'>-</span>")
            # 补齐3列
            while len(cells) < 3:
                cells.append("<span class='sig-no'>-</span>")
            history_rows += f"<tr><td>{row_date}</td><td>{cells[0]}</td><td>{cells[1]}</td><td>{cells[2]}</td></tr>\n"
        except Exception:
            continue
    
    # === 组装 ===
    html = HTML_TEMPLATE
    html = html.replace('{{date}}', date)
    # 转北京时间
    def to_bjt(st):
        try:
            dt = datetime.strptime(st, '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(hour=(dt.hour+8)%24)
            if dt.hour < 8:  # 跨天了
                dt = dt.replace(day=dt.day+1)
            return dt.strftime('%H:%M:%S')
        except Exception:
            return st
    bjt_time = to_bjt(scan_time)
    html = html.replace('{{scan_time}}', bjt_time)
    html = html.replace('{{overview_chips}}', '\n'.join(overview_chips))
    html = html.replace('{{summary_card}}', summary_html)
    html = html.replace('{{stock_sections}}', '\n'.join(stock_sections))
    html = html.replace('{{history_rows}}', history_rows)
    
    output_path = f"reports/report_{date}.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    with open('reports/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"报告已生成: {output_path}")
    print(f"最新报告: reports/index.html")
    return output_path

if __name__ == '__main__':
    import sys
    json_path = sys.argv[1] if len(sys.argv) > 1 else None
    generate_report(json_path)
