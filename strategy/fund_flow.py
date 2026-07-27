#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量资金监测系统 — 存量vs增量判断
=================================
数据来源: 新浪财经免费API
输出: fund_flow_report.html（手机卡片）

核心指标（6个维度）：
  ① 成交额趋势 - 20日均线方向
  ② 成交额偏离 - 当日 vs 20日均线
  ③ 大小盘分化 - 沪深300 vs 中证1000
  ④ 跷跷板强度 - 工行 vs 科创50反向程度
  ⑤ 科技成交占比 - 科创+创业板/沪市
  ⑥ 市场广度 - 涨跌家数（通过指数走势推断）
"""

import json, urllib.request, ssl, pandas as pd, sys, os
from datetime import datetime, timezone, timedelta

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(BASE_DIR, "fund_flow_report.html")

# ─── 数据获取 ───────────────────────────────────────
def fetch_kline(symbol, days=120):
    url="https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol=%s&datalen=%d&scale=240&ma=no"%(symbol,days)
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
    resp=urllib.request.urlopen(req,context=CTX,timeout=10)
    d=json.loads(resp.read().decode('utf-8'))
    df=pd.DataFrame(d)
    df['day']=pd.to_datetime(df['day'])
    for c in ['open','high','low','close','volume']:
        if c in df.columns: df[c]=df[c].astype(float)
    return df.sort_values('day').reset_index(drop=True)

def get_realtime(name, code):
    """获取实时数据"""
    url="https://hq.sinajs.cn/list=%s"%code
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"})
    resp=urllib.request.urlopen(req,context=CTX,timeout=10)
    raw=resp.read().decode('gbk')
    if raw and '="' in raw:
        p=raw.split('="')[1].split('"')[0].split(',')
        cur=float(p[3]); pre=float(p[2]); hi=float(p[4]); lo=float(p[5])
        return {"name":name,"cur":cur,"pre":pre,"chg":(cur/pre-1)*100,"hi":hi,"lo":lo}
    return None

# ─── 核心分析 ───────────────────────────────────────
def analyze():
    """分析所有指标"""
    result = {"time": datetime.now(timezone(timedelta(hours=8))).strftime('%m/%d %H:%M')}
    
    # 1. 成交额分析
    sh = fetch_kline("sh000001", 60)
    sz = fetch_kline("sz399001", 60)
    sh['amt'] = sh['volume'] / 1e8
    sz['amt'] = sz['volume'] / 1e8
    m = pd.merge(sh[['day','amt','close']], sz[['day','amt']], on='day', suffixes=('_sh','_sz'))
    m['total'] = m['amt_sh'] + m['amt_sz']
    m['ma20'] = m['total'].rolling(20).mean()
    m['ma60'] = m['total'].rolling(60).mean()
    
    latest = m.iloc[-1]
    amt_today = latest['total']
    amt_ma20 = latest['ma20']
    amt_dev = (amt_today/amt_ma20-1)*100
    
    # MA20方向（近5日MA20的变化方向）
    ma20_5d_ago = m.iloc[-6]['ma20'] if len(m)>6 else amt_ma20
    ma20_dir = (amt_ma20/ma20_5d_ago-1)*100
    
    result['amt'] = {"today": round(amt_today),"ma20": round(amt_ma20),"dev": round(amt_dev,1),"ma20_dir": round(ma20_dir,1)}
    
    # 2. 大小盘分化 (沪深300 / 中证1000)
    hs300 = fetch_kline("sh000300", 20)
    zz1000 = fetch_kline("sh000852", 20)
    hs_ret = (hs300['close'].iloc[-1]/hs300['close'].iloc[0]-1)*100
    zz_ret = (zz1000['close'].iloc[-1]/zz1000['close'].iloc[0]-1)*100
    divergence = hs_ret - zz_ret  # 正=大盘强于小盘
    result['divergence'] = {"hs300_ret": round(hs_ret,1),"zz1000_ret": round(zz_ret,1),"gap": round(divergence,1)}
    
    # 3. 工行vs科创跷跷板
    icbc = fetch_kline("sh601398", 20)
    kc = fetch_kline("sh000688", 20)
    icbc_ret = (icbc['close'].iloc[-1]/icbc['close'].iloc[0]-1)*100
    kc_ret = (kc['close'].iloc[-1]/kc['close'].iloc[0]-1)*100
    seesaw_active = (icbc_ret * kc_ret) < 0
    result['seesaw'] = {"icbc_20d": round(icbc_ret,1),"kc_20d": round(kc_ret,1),"active": seesaw_active}
    
    # 4. 科技成交占比
    kc_line = fetch_kline("sh000688", 20)
    cyb_line = fetch_kline("sz399006", 20)
    kc_amt = kc_line['volume'].mean()/1e8
    cyb_amt = cyb_line['volume'].mean()/1e8
    tech_ratio = (kc_amt+cyb_amt)/sh.tail(20)['amt'].mean()*100
    result['tech_ratio'] = round(tech_ratio,1)
    
    # 5. 综合评分
    score = 0
    signals = []
    
    # 成交额 vs 20日均 (存量特征: 缩量)
    if amt_dev < -10: score += 2; signals.append("成交额低于均值10%+ 存量特征")
    elif amt_dev < -5: score += 1; signals.append("成交额偏低")
    
    # MA20方向 (下行=存量)
    if ma20_dir < -2: score += 2; signals.append("成交额趋势向下 缩量中")
    
    # 大小盘分化 (极端分化=存量博弈)
    if abs(divergence) > 5: score += 1; signals.append("大小盘严重分化")
    
    # 跷跷板活跃 (是存量特征)
    if seesaw_active: score += 1; signals.append("跷跷板活跃 存量博弈典型")
    
    # 成交额绝对水平
    if amt_today < 1300: score += 1; signals.append("成交额低于1300亿")
    if amt_today < 1100: score += 1; signals.append("成交额低于1100亿 极度缩量")
    
    # 评分解读
    # 高分 = 存量博弈特征明显
    # 低分 = 可能有增量
    if score >= 5: result['verdict'] = "存量博弈 🔴"
    elif score >= 3: result['verdict'] = "偏存量 🟡"
    elif score >= 1: result['verdict'] = "过渡期 🟢"
    else: result['verdict'] = "可能有增量 🟢"
    
    result['score'] = score
    result['signals'] = signals
    
    return result

# ─── HTML生成 ───────────────────────────────────────
def generate_html(r):
    bar_color = "#e94560" if r['score'] >= 4 else ("#ffa726" if r['score'] >= 2 else "#00d4aa")
    pct = min(r['score']/7*100, 100)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>资金流向监测</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#0a0a1a;color:#e0e0e0;padding:12px}}
.card{{background:linear-gradient(135deg,#12122a,#1a1a3e);border-radius:14px;padding:16px;margin-bottom:10px}}
.title{{font-size:13px;color:#888;margin-bottom:8px}}
.row{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05)}}
.lbl{{font-size:13px;color:#aaa}}
.val{{font-size:14px;font-weight:600}}
.up{{color:#ff6b6b}} .down{{color:#00d4aa}}
.bar{{height:6px;background:#1a1a3e;border-radius:3px;margin:8px 0;overflow:hidden}}
.fill{{height:100%;border-radius:3px}}
.tag{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}}
.t-red{{background:#e9456022;color:#e94560}} .t-yellow{{background:#ffa72622;color:#ffa726}} .t-green{{background:#00d4aa22;color:#00d4aa}}
.sig{{font-size:11px;color:#666;margin:3px 0}}
.footer{{text-align:center;font-size:11px;color:#444;padding:12px 0}}
</style>
</head>
<body>
<div style="text-align:center;padding:12px 0 4px;font-size:20px;font-weight:700;color:#fff;">资金流向监测</div>
<div style="text-align:center;font-size:12px;color:#666;margin-bottom:4px;">{r['time']}</div>

<div class="card">
  <div class="title">综合判断</div>
  <div style="text-align:center;padding:8px 0;">
    <span style="font-size:36px;font-weight:700;color:{bar_color};">{r['score']}</span>
    <span style="font-size:13px;color:#888;">/7</span>
    <div style="font-size:16px;margin-top:4px;color:{bar_color};font-weight:600;">{r['verdict']}</div>
  </div>
  <div class="bar"><div class="fill" style="width:{pct}%;background:{bar_color};"></div></div>
  <div style="font-size:11px;color:#888;text-align:center;">0=增量  →  7=纯存量</div>
</div>

<div class="card">
  <div class="title">成交额</div>
  <div class="row"><span class="lbl">当日成交</span><span class="val">{r['amt']['today']}亿</span></div>
  <div class="row"><span class="lbl">20日均值</span><span class="val">{r['amt']['ma20']}亿</span></div>
  <div class="row"><span class="lbl">偏离20日均</span><span class="val" style="color:{"#ff6b6b" if r['amt']['dev']<0 else "#00d4aa"}">{r['amt']['dev']:+.1f}%</span></div>
  <div class="row"><span class="lbl">20日均方向</span><span class="val" style="color:{"#ff6b6b" if r['amt']['ma20_dir']<0 else "#00d4aa"}">{r['amt']['ma20_dir']:+.1f}%</span></div>
</div>

<div class="card">
  <div class="title">跷跷板 & 分化</div>
  <div class="row"><span class="lbl">跷跷板状态</span><span class="val" style="color:{"#e94560" if r['seesaw']['active'] else "#00d4aa"}">{"活跃(存量特征)" if r['seesaw']['active'] else "不活跃"}</span></div>
  <div class="row"><span class="lbl">工行20日</span><span class="val">+{r['seesaw']['icbc_20d']}%</span></div>
  <div class="row"><span class="lbl">科创50 20日</span><span class="val" style="color:#00d4aa;">{r['seesaw']['kc_20d']}%</span></div>
  <div class="row"><span class="lbl">大小盘分化</span><span class="val" style="color:{"#e94560" if abs(r['divergence']['gap'])>5 else "#888"}">{r['divergence']['gap']:+.1f}%</span></div>
  <div class="row"><span class="lbl">科技成交占比</span><span class="val">{r['tech_ratio']}%</span></div>
</div>

<div class="card">
  <div class="title">监测信号</div>
  {"".join(['<div class="sig">&#8226; '+s+'</div>' for s in r['signals']]) or '<div class="sig" style="color:#00d4aa;">&#8226; 无异常信号</div>'}
</div>

<div class="footer">数据: 新浪财经 | 系统自动生成</div>
</body>
</html>'''
    
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print("已输出: %s" % OUTPUT)

# ─── 主流程 ────────────────────────────────────────
if __name__ == '__main__':
    if sys.platform == 'win32': sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    print("资金流向监测系统")
    r = analyze()
    print("评分: %d/7 - %s" % (r['score'], r['verdict']))
    for s in r['signals']: print("  • %s" % s)
    generate_html(r)
