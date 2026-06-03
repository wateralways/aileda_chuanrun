#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML报告生成器 - 生成每日策略扫描报告网页
"""
import json
import os
import glob
from datetime import datetime

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>短线策略日报 - {{date}}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 960px; margin: 0 auto; }
        .header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }
        .header h1 { font-size: 2em; color: #00d4aa; margin-bottom: 10px; }
        .header .subtitle { color: #888; font-size: 0.95em; }
        .header .scan-time { color: #666; font-size: 0.85em; margin-top: 8px; }
        
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid rgba(255,255,255,0.08);
            backdrop-filter: blur(10px);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .stock-name { font-size: 1.4em; font-weight: 600; }
        .stock-code { color: #888; font-size: 0.9em; margin-left: 8px; }
        .price-tag {
            background: rgba(0,212,170,0.15);
            color: #00d4aa;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: 600;
        }
        .price-tag.down { background: rgba(255,80,80,0.15); color: #ff5050; }
        
        .signal-box {
            border-radius: 12px;
            padding: 16px;
            margin: 12px 0;
        }
        .signal-box.buy {
            background: linear-gradient(135deg, rgba(0,212,170,0.1) 0%, rgba(0,150,100,0.1) 100%);
            border: 1px solid rgba(0,212,170,0.3);
        }
        .signal-box.wait {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            text-align: center;
            color: #888;
        }
        .signal-title {
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .signal-title .badge {
            font-size: 0.7em;
            padding: 2px 10px;
            border-radius: 10px;
            font-weight: 500;
        }
        .badge.high { background: #ff6b35; color: white; }
        .badge.primary { background: #00d4aa; color: #1a1a2e; }
        .badge.medium { background: #4a90d9; color: white; }
        .signal-desc { color: #bbb; font-size: 0.95em; line-height: 1.6; }
        
        .indicators {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
            margin-top: 16px;
        }
        .indicator-item {
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            padding: 12px;
            text-align: center;
        }
        .indicator-label { font-size: 0.8em; color: #888; margin-bottom: 4px; }
        .indicator-value { font-size: 1.2em; font-weight: 600; color: #00d4aa; }
        .indicator-value.warning { color: #ffaa00; }
        .indicator-value.danger { color: #ff5050; }
        
        .footer {
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.85em;
            border-top: 1px solid rgba(255,255,255,0.08);
            margin-top: 20px;
        }
        .footer a { color: #4a90d9; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }
        
        .history-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            font-size: 0.9em;
        }
        .history-table th {
            text-align: left;
            padding: 10px 12px;
            color: #888;
            font-weight: 500;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .history-table td {
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .history-table tr:hover { background: rgba(255,255,255,0.03); }
        .history-table .signal-yes { color: #00d4aa; font-weight: 600; }
        .history-table .signal-no { color: #666; }
        
        .action-box {
            background: linear-gradient(135deg, rgba(0,212,170,0.08) 0%, rgba(0,100,80,0.08) 100%);
            border: 1px solid rgba(0,212,170,0.2);
            border-radius: 12px;
            padding: 20px;
            margin-top: 16px;
        }
        .action-title { color: #00d4aa; font-weight: 600; margin-bottom: 12px; }
        .action-item { display: flex; align-items: center; gap: 10px; margin: 8px 0; color: #ccc; }
        .action-item::before { content: "▸"; color: #00d4aa; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 短线策略日报</h1>
            <div class="subtitle">川润股份 & 爱乐达 | 持股周期8天策略</div>
            <div class="scan-time">扫描时间: {{scan_time}} | 数据日期: {{date}}</div>
        </div>
        
        {{stock_cards}}
        
        <div class="card">
            <div class="card-header">
                <span class="stock-name">📈 历史信号记录</span>
            </div>
            <table class="history-table">
                <tr><th>日期</th><th>川润股份</th><th>爱乐达</th></tr>
                {{history_rows}}
            </table>
        </div>
        
        <div class="footer">
            <p>策略详细说明请查看 <a href="docs/strategy.html">📖 策略文档</a></p>
            <p>本报告由 GitHub Actions 自动生成 | 数据来源于 Tushare</p>
            <p style="margin-top:8px; color:#444;">⚠️ 风险提示：本策略基于历史数据回测，不构成投资建议。股市有风险，投资需谨慎。</p>
        </div>
    </div>
</body>
</html>
'''

STOCK_CARD_TEMPLATE = '''
<div class="card">
    <div class="card-header">
        <div>
            <span class="stock-name">{{stock_emoji}} {{name}}</span>
            <span class="stock-code">{{code}}</span>
        </div>
        <div class="price-tag {{price_class}}">
            ¥{{close}} ({{pct_chg:+.2f}}%)
        </div>
    </div>
    
    {{signals_html}}
    
    <div class="indicators">
        <div class="indicator-item">
            <div class="indicator-label">量比</div>
            <div class="indicator-value {{vol_class}}">{{vol_ratio}}</div>
        </div>
        <div class="indicator-item">
            <div class="indicator-label">RSI(14)</div>
            <div class="indicator-value {{rsi_class}}">{{rsi14}}</div>
        </div>
        <div class="indicator-item">
            <div class="indicator-label">MACD</div>
            <div class="indicator-value {{macd_class}}">{{macd}}</div>
        </div>
        <div class="indicator-item">
            <div class="indicator-label">振幅</div>
            <div class="indicator-value">{{amplitude}}%</div>
        </div>
        <div class="indicator-item">
            <div class="indicator-label">布林带位置</div>
            <div class="indicator-value {{bb_class}}">{{bb_pct}}</div>
        </div>
        <div class="indicator-item">
            <div class="indicator-label">连涨/连跌</div>
            <div class="indicator-value">{{up_days}}/{{down_days}}</div>
        </div>
    </div>
</div>
'''

def get_indicator_class(value, thresholds):
    """根据阈值返回CSS类名"""
    if value is None:
        return ""
    if thresholds[0] <= value <= thresholds[1]:
        return ""
    elif thresholds[0] <= value <= thresholds[2]:
        return "warning"
    else:
        return "danger"

def generate_report(json_path=None):
    """生成HTML报告"""
    if json_path is None:
        # 找到最新的报告
        files = sorted(glob.glob('reports/signal_*.json'), reverse=True)
        if not files:
            print("没有找到信号文件")
            return
        json_path = files[0]
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    date = data['date']
    scan_time = data['scan_time']
    
    # 生成股票卡片
    stock_cards = []
    stock_emojis = {'川润股份': '🔷', '爱乐达': '🔶'}
    
    for stock in data['signals']:
        ind = stock['indicators']
        
        # 信号HTML
        if stock['has_signal']:
            signals_html = ""
            for sig in stock['signals']:
                emoji = "🔥" if sig['type'] == 'primary' else "⭐" if sig['type'] == 'high_confidence' else "📌"
                badge_class = "high" if sig['type'] == 'high_confidence' else "primary" if sig['type'] == 'primary' else "medium"
                signals_html += f'''
                <div class="signal-box buy">
                    <div class="signal-title">{emoji} {sig['strategy']} <span class="badge {badge_class}">{sig['confidence']}置信</span></div>
                    <div class="signal-desc">{sig['description']}</div>
                </div>
                '''
            signals_html += f'''
                <div class="action-box">
                    <div class="action-title">🎯 操作建议</div>
                    <div class="action-item">今日收盘前确认信号，可择机买入</div>
                    <div class="action-item">买入后严格持有8个交易日</div>
                    <div class="action-item">川润不设置止损，爱乐达可设4%止损</div>
                </div>
            '''
        else:
            signals_html = '''
                <div class="signal-box wait">
                    <div style="font-size: 1.2em; margin-bottom: 8px;">⏳ 暂无买入信号</div>
                    <div>今日未触发策略条件，继续观望</div>
                </div>
            '''
        
        # 价格颜色
        price_class = "down" if stock['latest_pct_chg'] < 0 else ""
        
        # 指标颜色
        vol_class = get_indicator_class(ind.get('vol_ratio'), (0.8, 1.5, 2.5))
        rsi_class = get_indicator_class(ind.get('rsi14'), (30, 50, 70))
        macd_class = "danger" if ind.get('macd') is not None and ind['macd'] < 0 else ""
        bb_class = get_indicator_class(ind.get('bb_pct'), (0.2, 0.5, 0.8))
        
        card = STOCK_CARD_TEMPLATE
        card = card.replace('{{stock_emoji}}', stock_emojis.get(stock['name'], '📌'))
        card = card.replace('{{name}}', stock['name'])
        card = card.replace('{{code}}', stock['code'])
        card = card.replace('{{close}}', f"{stock['latest_close']:.2f}")
        card = card.replace('{{pct_chg:+.2f}}', f"{stock['latest_pct_chg']:+.2f}")
        card = card.replace('{{price_class}}', price_class)
        card = card.replace('{{signals_html}}', signals_html)
        card = card.replace('{{vol_ratio}}', str(ind.get('vol_ratio', '-')))
        card = card.replace('{{vol_class}}', vol_class)
        card = card.replace('{{rsi14}}', str(ind.get('rsi14', '-')))
        card = card.replace('{{rsi_class}}', rsi_class)
        card = card.replace('{{macd}}', str(ind.get('macd', '-')))
        card = card.replace('{{macd_class}}', macd_class)
        card = card.replace('{{amplitude}}', str(ind.get('amplitude', '-')))
        card = card.replace('{{bb_pct}}', str(ind.get('bb_pct', '-')))
        card = card.replace('{{bb_class}}', bb_class)
        card = card.replace('{{up_days}}', str(ind.get('up_days', 0)))
        card = card.replace('{{down_days}}', str(ind.get('down_days', 0)))
        
        stock_cards.append(card)
    
    # 历史记录行
    history_rows = ""
    files = sorted(glob.glob('reports/signal_*.json'), reverse=True)[:7]
    for f in files:
        with open(f, 'r', encoding='utf-8') as fp:
            d = json.load(fp)
        row_date = d['date']
        cr_signal = ""
        ald_signal = ""
        for s in d['signals']:
            if s['has_signal']:
                names = [sig['strategy'] for sig in s['signals']]
                tag = f"<span class='signal-yes'>{', '.join(names)}</span>"
            else:
                tag = "<span class='signal-no'>-</span>"
            if s['name'] == '川润股份':
                cr_signal = tag
            else:
                ald_signal = tag
        history_rows += f"<tr><td>{row_date}</td><td>{cr_signal}</td><td>{ald_signal}</td></tr>\n"
    
    # 组装HTML
    html = HTML_TEMPLATE
    html = html.replace('{{date}}', date)
    html = html.replace('{{scan_time}}', scan_time)
    html = html.replace('{{stock_cards}}', '\n'.join(stock_cards))
    html = html.replace('{{history_rows}}', history_rows)
    
    output_path = f"reports/report_{date}.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # 同时更新最新报告
    with open('reports/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"报告已生成: {output_path}")
    print(f"最新报告: reports/index.html")
    return output_path

if __name__ == '__main__':
    import sys
    json_path = sys.argv[1] if len(sys.argv) > 1 else None
    generate_report(json_path)
