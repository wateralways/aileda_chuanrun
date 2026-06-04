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
        <p><a href="/aileda_chuanrun/docs/strategy.html">📖 策略详细说明</a> | <a href="https://github.com/wateralways/aileda_chuanrun">📁 GitHub</a></p>
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
    
    # === 加载盘中预警数据 ===
    rt_data = None
    rt_path = f"reports/realtime_{date}.json"
    if os.path.exists(rt_path):
        try:
            with open(rt_path, 'r', encoding='utf-8') as f:
                rt_data = json.load(f)
        except Exception:
            pass
    
    # === 生成顶部总览芯片 ===
    overview_chips = []
    stock_emojis = {'川润股份': '🔷', '爱乐达': '🔶', '高澜股份': '🔹'}
    
    buy_count = 0
    rt_match_count = 0
    for stock in data['signals']:
        is_buy = stock['has_signal']
        if is_buy:
            buy_count += 1
            chip_class = 'buy'
            status_text = '🔥 买入信号'
        else:
            chip_class = 'wait'
            status_text = '⏳ 观望'
        
        # 盘中预警对比标记
        rt_badge = ''
        if rt_data:
            rt_stock = next((s for s in rt_data.get('signals', []) if s['name'] == stock['name']), None)
            if rt_stock:
                rt_has = rt_stock.get('has_signal', False)
                if is_buy and rt_has:
                    rt_badge = '<div style="font-size:0.6em;color:#00d4aa;margin-top:2px;">✅ 盘中一致</div>'
                    rt_match_count += 1
                elif is_buy and not rt_has:
                    rt_badge = '<div style="font-size:0.6em;color:#ffaa00;margin-top:2px;">⚠️ 尾盘异动</div>'
                elif not is_buy and rt_has:
                    rt_badge = '<div style="font-size:0.6em;color:#ffaa00;margin-top:2px;">⚠️ 尾盘回落</div>'
                else:
                    rt_match_count += 1
        
        chip = f'''
        <div class="overview-chip {chip_class}">
            <div class="dot"></div>
            <div class="chip-stock">{stock_emojis.get(stock['name'], '')} {stock['name']}</div>
            <div class="chip-status">{status_text}</div>
            {rt_badge}
            <div class="chip-price">¥{stock['latest_close']:.2f} ({stock['latest_pct_chg']:+.2f}%)</div>
        </div>
        '''
        overview_chips.append(chip)
    
    # === 生成汇总卡片 ===
    rt_summary = ''
    if rt_data:
        rt_time = rt_data.get('scan_time', '').split()[1] if ' ' in rt_data.get('scan_time', '') else rt_data.get('scan_time', '')
        try:
            from datetime import datetime as _dt
            rt_dt = _dt.strptime(rt_data.get('scan_time', ''), '%Y-%m-%d %H:%M:%S')
            rt_dt = rt_dt.replace(hour=(rt_dt.hour+8)%24)
            if rt_dt.hour < 8:
                rt_dt = rt_dt.replace(day=rt_dt.day+1)
            rt_time = rt_dt.strftime('%H:%M:%S')
        except Exception:
            pass
        rt_summary = f'<div class="summary-detail" style="margin-top:8px;font-size:0.75em;color:#888;">⚡ 盘中预警 {rt_time} | {rt_match_count}/3 只状态一致</div>'
    
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
            {rt_summary}
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
            {rt_summary}
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
        
        # 盘中预警对比
        rt_compare_html = ''
        if 'realtime_comparison' in stock:
            comp = stock['realtime_comparison']
            match = comp.get('match', '')
            note = comp.get('note', '')
            if match == 'match':
                rt_compare_html = f'<div style="font-size:0.75em;color:#00d4aa;margin:4px 0;">✅ {note}</div>'
            else:
                rt_compare_html = f'<div style="font-size:0.75em;color:#ffaa00;margin:4px 0;">⚠️ {note}</div>'
        
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
            action_tip = f'''
            <div class="action-tip">
                <b>🎯 操作建议：</b>今日收盘前确认信号，可择机买入。买入后严格持有8个交易日。
                {rt_compare_html}
            </div>
            '''
        else:
            signals_html = f'''
            <div class="signal-area wait">
                <div style="font-size:1.1em; margin-bottom:4px;">⏳ 暂无买入信号</div>
                <div>今日未触发策略条件</div>
                {rt_compare_html}
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
    
    # === 生成动态统计和策略说明页 ===
    generate_stats_and_strategy_page()
    
    return output_path


def generate_stats_and_strategy_page():
    """生成 stats.json 和动态 strategy.html"""
    # 读取所有历史信号
    stock_stats = {}
    files = sorted(glob.glob('reports/signal_*.json'))
    
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            for stock in data['signals']:
                if not stock.get('has_signal') or 'buy_price' not in stock:
                    continue
                name = stock['name']
                if name not in stock_stats:
                    stock_stats[name] = {
                        'trades': [], 'total_return': 0, 'win_count': 0,
                        'max_profit': float('-inf'), 'max_loss': float('inf')
                    }
                trade = {
                    'date': data['date'],
                    'buy_price': stock['buy_price'],
                }
                if 'return_pct' in stock:
                    trade['sell_date'] = stock.get('sell_date', '')
                    trade['sell_price'] = stock.get('sell_price', 0)
                    trade['return_pct'] = stock['return_pct']
                    stock_stats[name]['total_return'] += trade['return_pct']
                    if trade['return_pct'] > 0:
                        stock_stats[name]['win_count'] += 1
                    stock_stats[name]['max_profit'] = max(stock_stats[name]['max_profit'], trade['return_pct'])
                    stock_stats[name]['max_loss'] = min(stock_stats[name]['max_loss'], trade['return_pct'])
                stock_stats[name]['trades'].append(trade)
        except Exception:
            continue
    
    # 汇总统计
    stats = {'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'stocks': {}}
    for name, s in stock_stats.items():
        total = len(s['trades'])
        completed = sum(1 for t in s['trades'] if 'return_pct' in t)
        stats['stocks'][name] = {
            'total_trades': total,
            'completed_trades': completed,
            'win_trades': s['win_count'],
            'win_rate': round(s['win_count'] / completed * 100, 1) if completed > 0 else None,
            'total_return': round(s['total_return'], 2),
            'avg_return': round(s['total_return'] / completed, 2) if completed > 0 else None,
            'max_profit': round(s['max_profit'], 2) if s['max_profit'] != float('-inf') else None,
            'max_loss': round(s['max_loss'], 2) if s['max_loss'] != float('inf') else None,
        }
    
    # 保存 stats.json
    with open('reports/stats.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"统计已更新: reports/stats.json")
    
    # 生成 strategy.html
    generate_strategy_html(stats)


def generate_strategy_html(stats):
    """生成动态策略说明页"""
    # 检测是否在 strategy/ 子目录中运行
    docs_dir = '../docs' if os.path.basename(os.getcwd()) == 'strategy' else 'docs'
    os.makedirs(docs_dir, exist_ok=True)
    
    # 构建动态统计HTML（JS会覆盖这部分，但作为fallback）
    def stat_cell(name, key):
        if name in stats['stocks']:
            s = stats['stocks'][name]
            if key == 'win_rate' and s['win_rate'] is not None:
                return f'<span data-stat="{name}-{key}">{s["win_rate"]:.1f}%</span>'
            elif key == 'total_return':
                return f'<span data-stat="{name}-{key}">{s["total_return"]:+.2f}%</span>'
            elif key == 'avg_return' and s['avg_return'] is not None:
                return f'<span data-stat="{name}-{key}">{s["avg_return"]:+.2f}%</span>'
            elif key == 'total_trades':
                return f'<span data-stat="{name}-{key}">{s["total_trades"]}</span>'
        return f'<span data-stat="{name}-{key}">-</span>'
    
    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>策略详细说明 - 川润股份 & 爱乐达 & 高澜股份</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: #0f0f23;
            color: #e0e0e0;
            line-height: 1.8;
        }
        .container { max-width: 900px; margin: 0 auto; padding: 40px 20px; }
        h1 { color: #00d4aa; font-size: 2.2em; margin-bottom: 10px; text-align: center; }
        h2 { color: #4a90d9; font-size: 1.5em; margin: 40px 0 20px; border-bottom: 2px solid rgba(74,144,217,0.3); padding-bottom: 10px; }
        h3 { color: #ffaa00; font-size: 1.2em; margin: 30px 0 15px; }
        .subtitle { text-align: center; color: #888; margin-bottom: 40px; }
        
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 28px;
            margin: 24px 0;
            border: 1px solid rgba(255,255,255,0.08);
        }
        
        table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.95em; }
        th { text-align: left; padding: 12px; background: rgba(0,212,170,0.1); color: #00d4aa; font-weight: 600; }
        td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.06); }
        tr:hover { background: rgba(255,255,255,0.03); }
        
        .highlight { color: #00d4aa; font-weight: 600; }
        .warning { color: #ffaa00; }
        .danger { color: #ff5050; }
        .badge {
            display: inline-block;
            padding: 3px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge.green { background: rgba(0,212,170,0.15); color: #00d4aa; }
        .badge.orange { background: rgba(255,170,0,0.15); color: #ffaa00; }
        .badge.red { background: rgba(255,80,80,0.15); color: #ff5050; }
        .badge.blue { background: rgba(74,144,217,0.15); color: #4a90d9; }
        
        .rule-box {
            background: rgba(0,212,170,0.05);
            border-left: 4px solid #00d4aa;
            padding: 16px 20px;
            margin: 16px 0;
            border-radius: 0 12px 12px 0;
        }
        .rule-box.danger { background: rgba(255,80,80,0.05); border-left-color: #ff5050; }
        
        code {
            background: rgba(255,255,255,0.1);
            padding: 2px 8px;
            border-radius: 4px;
            font-family: "Fira Code", monospace;
            font-size: 0.9em;
        }
        
        .nav { text-align: center; margin-bottom: 40px; }
        .nav a { color: #4a90d9; text-decoration: none; margin: 0 15px; }
        .nav a:hover { text-decoration: underline; }
        
        .footer { text-align: center; margin-top: 60px; padding-top: 30px; border-top: 1px solid rgba(255,255,255,0.1); color: #666; font-size: 0.9em; }
        
        .live-track {
            background: linear-gradient(135deg, rgba(0,212,170,0.08) 0%, rgba(74,144,217,0.05) 100%);
            border: 1px solid rgba(0,212,170,0.15);
        }
        .live-tag {
            display: inline-block;
            font-size: 0.7em;
            padding: 2px 10px;
            border-radius: 10px;
            background: #00d4aa;
            color: #0f0f23;
            font-weight: 700;
            margin-left: 10px;
            vertical-align: middle;
        }
        .live-tag::before { content: "● "; animation: blink 2s infinite; }
        @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
        .stat-note { font-size: 0.8em; color: #888; margin-top: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/aileda_chuanrun/">📊 返回日报</a>
            <a href="https://github.com/wateralways/aileda_chuanrun">📁 GitHub仓库</a>
        </div>
        
        <h1>📖 策略详细说明</h1>
        <p class="subtitle">川润股份(002272) & 爱乐达(300696) & 高澜股份(300499) | 短线8天策略</p>
        
        <h2>一、策略总览</h2>
        <div class="card">
            <table>
                <tr><th>维度</th><th>川润股份</th><th>爱乐达</th><th>高澜股份</th></tr>
                <tr><td>策略类型</td><td><span class="badge green">趋势突破（追涨）</span></td><td><span class="badge orange">回调反弹（低吸）</span></td><td><span class="badge blue">跳空高开（追涨）</span></td></tr>
                <tr><td>核心策略</td><td class="highlight">放量突破</td><td class="highlight">连阴首阳</td><td class="highlight">跳空高开</td></tr>
                <tr><td>最佳持股</td><td class="highlight">8天（越久越好）</td><td class="highlight">严格8天</td><td class="highlight">8天</td></tr>
                <tr><td>历史回测胜率</td><td>80~100%</td><td>50~62.5%</td><td>77.8%</td></tr>
                <tr><td>历史回测收益</td><td class="highlight">+57~60%</td><td class="highlight">+24~25%</td><td class="highlight">+102.68%</td></tr>
                <tr><td>止损设置</td><td class="danger">❌ 不设置止损</td><td>✅ 可设4%止损</td><td>✅ 可设6%止损</td></tr>
            </table>
        </div>
        
        <h2>二、实盘跟踪 <span class="live-tag">LIVE</span></h2>
        <p class="stat-note">以下数据基于策略实际触发后的真实表现，随每日扫描自动更新。部分信号尚未到8天卖出日，收益待结算。</p>
        <div class="card live-track">
            <table>
                <tr><th>股票</th><th>触发次数</th><th>已完成</th><th>胜率</th><th>总收益</th><th>平均收益</th><th>最大盈利</th><th>最大亏损</th></tr>
                <tr>
                    <td><b>川润股份</b></td>
                    <td>''' + stat_cell('川润股份', 'total_trades') + '''</td>
                    <td>''' + stat_cell('川润股份', 'completed_trades') + '''</td>
                    <td class="highlight">''' + stat_cell('川润股份', 'win_rate') + '''</td>
                    <td class="highlight">''' + stat_cell('川润股份', 'total_return') + '''</td>
                    <td>''' + stat_cell('川润股份', 'avg_return') + '''</td>
                    <td class="highlight">''' + stat_cell('川润股份', 'max_profit') + '''</td>
                    <td class="danger">''' + stat_cell('川润股份', 'max_loss') + '''</td>
                </tr>
                <tr>
                    <td><b>爱乐达</b></td>
                    <td>''' + stat_cell('爱乐达', 'total_trades') + '''</td>
                    <td>''' + stat_cell('爱乐达', 'completed_trades') + '''</td>
                    <td class="highlight">''' + stat_cell('爱乐达', 'win_rate') + '''</td>
                    <td class="highlight">''' + stat_cell('爱乐达', 'total_return') + '''</td>
                    <td>''' + stat_cell('爱乐达', 'avg_return') + '''</td>
                    <td class="highlight">''' + stat_cell('爱乐达', 'max_profit') + '''</td>
                    <td class="danger">''' + stat_cell('爱乐达', 'max_loss') + '''</td>
                </tr>
                <tr>
                    <td><b>高澜股份</b></td>
                    <td>''' + stat_cell('高澜股份', 'total_trades') + '''</td>
                    <td>''' + stat_cell('高澜股份', 'completed_trades') + '''</td>
                    <td class="highlight">''' + stat_cell('高澜股份', 'win_rate') + '''</td>
                    <td class="highlight">''' + stat_cell('高澜股份', 'total_return') + '''</td>
                    <td>''' + stat_cell('高澜股份', 'avg_return') + '''</td>
                    <td class="highlight">''' + stat_cell('高澜股份', 'max_profit') + '''</td>
                    <td class="danger">''' + stat_cell('高澜股份', 'max_loss') + '''</td>
                </tr>
            </table>
            <p class="stat-note">更新于 <span id="stats-update-time">''' + stats.get('update_time', '-') + '''</span></p>
        </div>
        
        <h2>三、川润股份策略详解</h2>
        
        <h3>3.1 首选策略：放量突破</h3>
        <div class="card">
            <p>回测表现：<span class="highlight">4次交易，胜率100%，总收益+60.30%</span></p>
            
            <div class="rule-box">
                <strong>买入条件（四重过滤，缺一不可）：</strong><br>
                ① <code>成交量 > 5日均量 × 1.5倍</code><br>
                ② <code>当日振幅 > 2.5%</code><br>
                ③ <code>收盘价突破前1日最高价</code><br>
                ④ <code>收盘价 > 开盘价（收阳线）</code>
            </div>
            
            <div class="rule-box danger">
                <strong>卖出规则：</strong><br>
                买入后<strong>严格持有8天</strong>，第8天收盘卖出。<br>
                <span class="danger">严禁设置止损！</span> 回测证明3%止损会让胜率从100%暴跌至33%，总收益从+60%降至+3%。
            </div>
            
            <p><strong>逐笔交易明细：</strong></p>
            <table>
                <tr><th>买入日期</th><th>买入价</th><th>卖出日期</th><th>卖出价</th><th>盈亏</th></tr>
                <tr><td>2026-02-06</td><td>15.39</td><td>2026-02-26</td><td>19.21</td><td class="highlight">+24.82%</td></tr>
                <tr><td>2026-02-27</td><td>19.47</td><td>2026-03-11</td><td>20.69</td><td>+6.27%</td></tr>
                <tr><td>2026-03-30</td><td>18.06</td><td>2026-04-10</td><td>19.12</td><td>+5.87%</td></tr>
                <tr><td>2026-05-07</td><td>19.86</td><td>2026-05-19</td><td>22.67</td><td class="highlight">+14.15%</td></tr>
            </table>
        </div>
        
        <h3>3.2 备选策略：组合A</h3>
        <div class="card">
            <p>回测表现：<span class="highlight">5次交易，胜率80%，总收益+57.69%</span></p>
            <p>在放量突破的基础上，增加两种底部反转形态作为补充信号：</p>
            <ul>
                <li><strong>晨星形态：</strong>下跌末端出现晨星K线组合（阴线+小实体+阳线）</li>
                <li><strong>阳线吞没：</strong>阳线实体完全覆盖前日阴线实体</li>
            </ul>
            <p>适合希望交易频率更高的场景，但会多1次小额亏损（-1.63%）。</p>
        </div>
        
        <h3>3.3 持股天数敏感性</h3>
        <div class="card">
            <table>
                <tr><th>持股天数</th><th>交易次数</th><th>胜率</th><th>总收益</th></tr>
                <tr><td>3天</td><td>4</td><td>50%</td><td>+7.25%</td></tr>
                <tr><td>5天</td><td>4</td><td>75%</td><td>+14.96%</td></tr>
                <tr><td class="highlight">8天</td><td class="highlight">4</td><td class="highlight">100%</td><td class="highlight">+60.30%</td></tr>
                <tr><td>12天</td><td>3</td><td>100%</td><td>+80.12%</td></tr>
            </table>
            <p class="warning">核心发现：持股7天后胜率跃升至100%，川润的趋势延续性极强。但超过8天交易次数减少，8天是最佳平衡点。</p>
        </div>
        
        <h2>四、爱乐达策略详解</h2>
        
        <h3>4.1 首选策略：连阴首阳</h3>
        <div class="card">
            <p>回测表现：<span class="highlight">8次交易，胜率62.5%，总收益+24.81%</span></p>
            
            <div class="rule-box">
                <strong>买入条件：</strong><br>
                ① <code>前2~3个交易日，至少2天收阴线</code><br>
                ② <code>当日收阳线，且收盘 > 前日收盘</code><br>
                ③ <code>RSI14 < 60（非高位区域）</code>
            </div>
            
            <div class="rule-box">
                <strong>卖出规则：</strong><br>
                买入后<strong>严格持有8天</strong>卖出。<br>
                风险偏好低者可设 <code>4%止损 + 12%止盈</code>。
            </div>
            
            <p><strong>逐笔交易明细：</strong></p>
            <table>
                <tr><th>买入日期</th><th>买入价</th><th>卖出日期</th><th>卖出价</th><th>盈亏</th></tr>
                <tr><td>2026-01-19</td><td>31.10</td><td>2026-01-29</td><td>33.80</td><td>+8.68%</td></tr>
                <tr><td>2026-02-03</td><td>32.00</td><td>2026-02-13</td><td>32.80</td><td>+2.50%</td></tr>
                <tr><td>2026-02-27</td><td>32.83</td><td>2026-03-11</td><td>30.24</td><td class="danger">-7.89%</td></tr>
                <tr><td>2026-03-13</td><td>29.18</td><td>2026-03-25</td><td>27.64</td><td class="danger">-5.28%</td></tr>
                <tr><td>2026-03-27</td><td>27.80</td><td>2026-04-09</td><td>30.07</td><td>+8.17%</td></tr>
                <tr><td>2026-04-14</td><td>31.99</td><td>2026-04-24</td><td>37.64</td><td class="highlight">+17.66%</td></tr>
                <tr><td>2026-04-27</td><td>38.61</td><td>2026-05-12</td><td>43.11</td><td class="highlight">+11.66%</td></tr>
                <tr><td>2026-05-28</td><td>32.91</td><td>2026-06-03</td><td>29.74</td><td class="danger">-9.63%</td></tr>
            </table>
        </div>
        
        <h3>4.2 辅助策略：放量见底</h3>
        <div class="card">
            <p>回测表现：<span class="highlight">1次交易，胜率100%，收益+28.37%</span></p>
            <p>信号极其稀少但精准——成交量创10日新高、价格不再跌、前期跌幅>5%。</p>
            <p>不要单独等这个信号，但当它出现时，<strong>可加大仓位</strong>。</p>
        </div>
        
        <h3>4.3 持股天数敏感性</h3>
        <div class="card">
            <table>
                <tr><th>持股天数</th><th>交易次数</th><th>胜率</th><th>总收益</th></tr>
                <tr><td>1天</td><td>19</td><td>36.8%</td><td class="danger">-4.10%</td></tr>
                <tr><td>3天</td><td>14</td><td>57.1%</td><td>+9.23%</td></tr>
                <tr><td>5天</td><td>12</td><td>41.7%</td><td>+2.87%</td></tr>
                <tr><td class="highlight">8天</td><td class="highlight">8</td><td class="highlight">62.5%</td><td class="highlight">+24.81%</td></tr>
                <tr><td>12天</td><td>6</td><td>33.3%</td><td>+8.82%</td></tr>
                <tr><td>15天</td><td>6</td><td>16.7%</td><td class="danger">-12.84%</td></tr>
            </table>
            <p class="warning">核心发现：持股1天巨亏-4.10%，说明爱乐达反弹次日极少立刻大涨。6天是死亡陷阱（-15.52%），8天是最佳甜蜜点。超过10天胜率暴跌。</p>
        </div>
        
        <h2>五、高澜股份策略详解</h2>
        
        <h3>5.1 首选策略：跳空高开</h3>
        <div class="card">
            <p>回测表现：<span class="highlight">9次交易，胜率77.8%，总收益+102.68%，盈亏比10.64，最大回撤仅6.10%</span></p>
            
            <div class="rule-box">
                <strong>买入条件（三重过滤）：</strong><br>
                ① <code>跳空高开 0.8% ~ 5.0%</code><br>
                ② <code>当日收阳线（收盘 > 开盘）</code><br>
                ③ <code>放量（成交量 > 5日均量 × 1.2倍）</code>
            </div>
            
            <div class="rule-box">
                <strong>卖出规则：</strong><br>
                买入后<strong>严格持有8天</strong>，第8天收盘卖出。<br>
                可设置动态止盈止损：<code>6%止损 + 15%止盈</code>，胜率63.6%，收益+77.49%
            </div>
            
            <p><strong>逐笔交易明细：</strong></p>
            <table>
                <tr><th>买入日期</th><th>买入价</th><th>卖出日期</th><th>卖出价</th><th>盈亏</th></tr>
                <tr><td>2025-07-31</td><td>20.13</td><td>2025-08-12</td><td>22.83</td><td class="highlight">+13.41%</td></tr>
                <tr><td>2025-09-10</td><td>29.38</td><td>2025-09-22</td><td>33.16</td><td class="highlight">+12.87%</td></tr>
                <tr><td>2025-11-20</td><td>26.68</td><td>2025-12-02</td><td>26.18</td><td>-1.87%</td></tr>
                <tr><td>2025-12-08</td><td>27.04</td><td>2025-12-18</td><td>28.80</td><td>+6.51%</td></tr>
                <tr><td>2025-12-24</td><td>31.40</td><td>2026-01-07</td><td>31.92</td><td>+1.66%</td></tr>
                <tr><td>2026-02-12</td><td>30.75</td><td>2026-03-04</td><td>37.36</td><td class="highlight">+21.50%</td></tr>
                <tr><td>2026-03-10</td><td>41.79</td><td>2026-03-20</td><td>39.24</td><td>-6.10%</td></tr>
                <tr><td>2026-04-08</td><td>37.40</td><td>2026-04-20</td><td>44.97</td><td class="highlight">+20.24%</td></tr>
                <tr><td>2026-05-06</td><td>40.48</td><td>2026-05-18</td><td>43.98</td><td>+8.65%</td></tr>
            </table>
            
            <p class="warning">核心发现：7盈2亏，胜率77.8%。最大盈利+21.50%，最大亏损仅-6.10%。这是三只股票中<span class="highlight">风险收益比最佳</span>的策略。</p>
        </div>
        
        <h3>5.2 持股天数敏感性</h3>
        <div class="card">
            <table>
                <tr><th>持股天数</th><th>交易次数</th><th>胜率</th><th>总收益</th></tr>
                <tr><td>3天</td><td>14</td><td>57.1%</td><td>+9.23%</td></tr>
                <tr><td>5天</td><td>12</td><td>58.3%</td><td>+21.35%</td></tr>
                <tr><td class="highlight">8天</td><td class="highlight">9</td><td class="highlight">77.8%</td><td class="highlight">+102.68%</td></tr>
                <tr><td>10天</td><td>8</td><td>75.0%</td><td>+63.20%</td></tr>
                <tr><td>12天</td><td>7</td><td>71.4%</td><td>+45.42%</td></tr>
            </table>
            <p class="warning">8天是最佳甜蜜点，超过后收益递减。</p>
        </div>
        
        <h3>5.3 高澜股份 vs 川润股份</h3>
        <div class="card">
            <table>
                <tr><th>维度</th><th>川润股份</th><th>高澜股份</th></tr>
                <tr><td>最佳策略</td><td>放量突破</td><td>跳空高开</td></tr>
                <tr><td>胜率</td><td>100%</td><td>77.8%</td></tr>
                <tr><td>总收益</td><td>+60.30%</td><td>+102.68%</td></tr>
                <tr><td>最大回撤</td><td>0%</td><td>6.10%</td></tr>
                <tr><td>盈亏比</td><td>∞</td><td>10.64</td></tr>
                <tr><td>交易次数</td><td>4次</td><td>9次</td></tr>
            </table>
            <p>高澜股份虽然胜率略低，但<span class="highlight">交易次数更多、收益更高、回撤可控</span>，实盘可操作性更强。</p>
        </div>
        
        <h2>六、关键禁忌</h2>
        <div class="card">
            <div class="rule-box danger">
                <strong>❌ 川润股份绝对不能做的事：</strong><br>
                1. 设置3-5%的止损 → 会让胜率从100%暴跌到33%，收益从+60%降到+3%<br>
                2. 持股少于5天就卖 → 前3-5天可能浮亏或微利，第7天后才开始发力<br>
                3. 突破当天没买，次日追高 → 策略要求收盘前确认信号后买入
            </div>
            <div class="rule-box danger">
                <strong>❌ 爱乐达绝对不能做的事：</strong><br>
                1. 追涨突破 → 放量突破策略在爱乐达上亏损-2%，5月11日追高亏18.77%<br>
                2. 持股1-2天就卖 → 次日极少立刻大涨，必须拿满8天<br>
                3. 在RSI>70时买入 → 高位反弹陷阱
            </div>
            <div class="rule-box danger">
                <strong>❌ 高澜股份绝对不能做的事：</strong><br>
                1. 跳空>5%时追高 → 高开过多易回落，严格控制在0.8%~5%区间<br>
                2. 缩量跳空买入 → 必须放量确认，否则假突破概率大增<br>
                3. 持股少于5天 → 跳空高开后常有小回调，5天内卖出易亏损
            </div>
        </div>
        
        <h2>七、实盘操作SOP</h2>
        <div class="card">
            <h3>川润股份 SOP</h3>
            <div class="rule-box">
                1. 每天14:30开始观察<br>
                2. 检查当日是否满足放量突破四条件<br>
                3. 14:45确认信号后，收盘前买入<br>
                4. 买入后设日历提醒，8个交易日后卖出<br>
                5. 期间不盯盘，不止损，让利润奔跑
            </div>
            
            <h3>爱乐达 SOP</h3>
            <div class="rule-box">
                1. 每天14:30开始观察<br>
                2. 检查是否连阴后出现首根阳线<br>
                3. 确认RSI14 < 60<br>
                4. 14:45确认信号后，收盘前买入<br>
                5. 买入后设日历提醒，8个交易日后卖出<br>
                6. 如浮亏超4%，次日开盘考虑止损
            </div>
            
            <h3>高澜股份 SOP</h3>
            <div class="rule-box">
                1. 每天14:30开始观察<br>
                2. 检查是否跳空高开0.8%~5%<br>
                3. 确认收阳且放量（量比>1.2）<br>
                4. 14:45确认信号后，收盘前买入<br>
                5. 买入后设日历提醒，8个交易日后卖出<br>
                6. 可设6%止损+15%止盈，降低回撤
            </div>
        </div>
        
        <h2>八、技术实现</h2>
        <div class="card">
            <p><strong>自动扫描：</strong>GitHub Actions 每天北京时间14:45自动运行</p>
            <p><strong>数据来源：</strong>Tushare Pro API</p>
            <p><strong>报告发布：</strong>自动部署到 GitHub Pages</p>
            <p><strong>策略代码：</strong><code>strategy/signals.py</code></p>
            <p><strong>扫描脚本：</strong><code>strategy/daily_scan.py</code></p>
            <p><strong>报告生成：</strong><code>strategy/report_generator.py</code></p>
            <p><strong>信号跟踪：</strong>每次扫描自动计算8天后收益率，胜率实时更新</p>
        </div>
        
        <div class="footer">
            <p>策略基于2025-2026年历史数据回测 | 实盘跟踪数据随每日扫描自动更新</p>
            <p style="margin-top:10px; color:#ff5050;">⚠️ 本策略仅供学习研究，不构成投资建议。股市有风险，投资需谨慎。</p>
        </div>
    </div>
    
    <script>
    // 动态加载最新统计（支持GitHub Pages跨域，通过fetch stats.json）
    (function() {
        // 尝试从相对路径加载 stats.json
        fetch('../reports/stats.json')
            .then(r => r.json())
            .then(data => {
                document.getElementById('stats-update-time').textContent = data.update_time || '-';
                const stocks = data.stocks || {};
                const fmt = (v, suffix) => v != null ? (v > 0 && suffix === '%' ? '+' : '') + v + suffix : '-';
                
                Object.keys(stocks).forEach(name => {
                    const s = stocks[name];
                    const prefix = name + '-';
                    const map = {
                        [prefix + 'total_trades']: s.total_trades,
                        [prefix + 'completed_trades']: s.completed_trades,
                        [prefix + 'win_rate']: fmt(s.win_rate, '%'),
                        [prefix + 'total_return']: fmt(s.total_return, '%'),
                        [prefix + 'avg_return']: fmt(s.avg_return, '%'),
                        [prefix + 'max_profit']: fmt(s.max_profit, '%'),
                        [prefix + 'max_loss']: fmt(s.max_loss, '%'),
                    };
                    Object.keys(map).forEach(key => {
                        const el = document.querySelector('[data-stat="' + key + '"]');
                        if (el) el.textContent = map[key];
                    });
                });
            })
            .catch(e => console.log('stats.json 加载失败（可能首次运行或无数据）:', e));
    })();
    </script>
</body>
</html>'''
    
    strategy_path = f'{docs_dir}/strategy.html'
    with open(strategy_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"策略说明页已更新: {strategy_path}")


if __name__ == '__main__':
    import sys
    json_path = sys.argv[1] if len(sys.argv) > 1 else None
    generate_report(json_path)
