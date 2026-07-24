#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工行 vs 科创50 跷跷板策略（概率版）
===================================
不是硬性买卖信号，而是给出工行见顶概率（0~100分）
让你自己根据概率做决策。

核心逻辑：
  评分 > 70 → 高概率见顶，可买入科创50
  评分 50~70 → 可能见顶，准备
  评分 30~50 → 仍在上升，观望
  评分 < 30 → 强势上行，不动

评分维度（7个）：
  ① 月超额（20分）— 工行跑赢大盘越多越危险
  ② 波段涨幅（15分）— 从低点上来涨越多越危险
  ③ 距MA5（15分）— 跌破MA5或接近MA5
  ④ 成交额异常（15分）— 放量冲顶是见顶信号
  ⑤ 上影线（15分）— 长上影是见顶信号
  ⑥ 大盘环境（10分）— 大盘越弱，工行独涨越难持续
  ⑦ 历史位置（10分）— 在60日高位=接近见顶
"""

import json, urllib.request, ssl, pandas as pd, sys
from datetime import datetime

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def fetch_icbc(days=200):
    url = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh601398&datalen=%d&scale=240&ma=no" % days
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, context=CTX, timeout=10)
    d = json.loads(resp.read().decode('utf-8'))
    df = pd.DataFrame(d)
    df['day'] = pd.to_datetime(df['day'])
    for c in ['open','high','low','close','volume']:
        df[c] = df[c].astype(float)
    return df.sort_values('day').reset_index(drop=True)

def fetch_sh(days=200):
    url = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&datalen=%d&scale=240&ma=no" % days
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, context=CTX, timeout=10)
    d = json.loads(resp.read().decode('utf-8'))
    df = pd.DataFrame(d)
    df['day'] = pd.to_datetime(df['day'])
    for c in ['open','high','low','close','volume']:
        df[c] = df[c].astype(float)
    return df.sort_values('day').reset_index(drop=True)


def calc_score(icbc_df=None, sh_df=None):
    """计算工行见顶概率评分
    
    Returns:
        dict: { 'score': 总分, 'detail': 各维度得分, 'data': 原始数据, 'signal': 建议 }
    """
    if icbc_df is None:
        icbc_df = fetch_icbc()
    if sh_df is None:
        sh_df = fetch_sh()
    
    df = icbc_df.copy()
    for w in [5, 10, 20, 60]:
        df['ma%d'%w] = df['close'].rolling(w).mean()
    df['vol_ma20'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma20']
    df['upper_shadow'] = (df['high'] - df[['close','open']].max(axis=1)) / df['open'] * 100
    df['month'] = df['day'].dt.month
    
    r = df.iloc[-1]
    price = r['close']
    today = r['day']
    
    # ── 月超额 ──
    this_m = df[df['month'] == r['month']]
    if len(this_m) >= 5:
        m_ret = (price / this_m['close'].iloc[0] - 1) * 100
    else:
        m_ret = 0
    
    # ── 波段涨幅 ──
    trough = df.tail(60)['low'].min()
    gain_from_trough = (price / trough - 1) * 100
    
    # ── 大盘月涨跌 ──
    sh_m = sh_df[sh_df['day'] >= str(today.date())[:7]]
    if len(sh_m) >= 5:
        sh_m_ret = (sh_m['close'].iloc[-1] / sh_m['close'].iloc[0] - 1) * 100
    else:
        sh_m_ret = 0
    
    # ── 7维度打分 ──
    detail = {}
    
    # 1. 月超额 (20分)
    excess_score = min(max(m_ret / 15 * 20, 0), 20)
    detail['月超额'] = round(excess_score, 1)
    
    # 2. 波段涨幅 (15分)
    gain_score = min(max(gain_from_trough / 12 * 15, 0), 15)
    detail['波段涨幅'] = round(gain_score, 1)
    
    # 3. 距MA5 (15分)
    dist_ma5 = (price - r['ma5']) / r['ma5'] * 100
    if dist_ma5 < 0:
        ma5_score = 15
    else:
        ma5_score = max(15 - dist_ma5 / 0.5 * 15, 0)
    detail['距MA5'] = round(ma5_score, 1)
    
    # 4. 成交额 (15分)
    vol = r['vol_ratio']
    if vol > 1.3:
        vol_score = 15
    elif vol > 1.1:
        vol_score = 10
    elif vol > 0.9:
        vol_score = 5
    else:
        vol_score = 0
    detail['成交额'] = round(vol_score, 1)
    
    # 5. 上影线 (15分)
    shadow = r['upper_shadow']
    shadow_score = min(shadow / 3 * 15, 15)
    detail['上影线'] = round(shadow_score, 1)
    
    # 6. 大盘环境 (10分)
    if sh_m_ret < -5:
        mkt_score = 10
    elif sh_m_ret < -3:
        mkt_score = 8
    elif sh_m_ret < 0:
        mkt_score = 5
    else:
        mkt_score = 0
    detail['大盘环境'] = round(mkt_score, 1)
    
    # 7. 历史位置 (10分)
    pos_60 = (price - df.tail(60)['low'].min()) / (df.tail(60)['high'].max() - df.tail(60)['low'].min()) * 100
    pos_score = min(pos_60 / 100 * 10, 10)
    detail['历史位置'] = round(pos_score, 1)
    
    total = sum(detail.values())
    
    # ── 信号判定 ──
    if total >= 70:
        signal = '买入'
        signal_detail = '高概率见顶，可买入科创50ETF'
    elif total >= 50:
        signal = '准备'
        signal_detail = '可能见顶，准备买入'
    elif total >= 30:
        signal = '观望'
        signal_detail = '仍在上升，等待更好时机'
    else:
        signal = '不动'
        signal_detail = '强势上行，不操作'
    
    return {
        'score': round(total, 1),
        'detail': detail,
        'signal': signal,
        'signal_detail': signal_detail,
        'data': {
            'price': round(price, 2),
            'date': str(today.date()),
            'm_ret': round(m_ret, 2),
            'gain_from_trough': round(gain_from_trough, 2),
            'dist_ma5': round(dist_ma5, 2),
            'vol_ratio': round(vol, 2),
            'upper_shadow': round(shadow, 2),
            'sh_m_ret': round(sh_m_ret, 2),
            'ma5': round(r['ma5'], 2),
            'ma10': round(r['ma10'], 2),
            'ma20': round(r['ma20'], 2),
            'trough': round(trough, 2),
        }
    }


def print_score(result):
    """打印评分结果"""
    d = result['data']
    print("="*55)
    print("  工行见顶概率评分  %s" % d['date'])
    print("="*55)
    print()
    print("  综合评分: %.1f / 100" % result['score'])
    print("  信号: 【%s】 - %s" % (result['signal'], result['signal_detail']))
    print()
    print("  各维度:")
    for k, v in sorted(result['detail'].items(), key=lambda x: -x[1]):
        bar = "█" * int(v / 2)
        print("    %-10s %5.1f  %s" % (k, v, bar))
    print()
    print("  当前数据:")
    print("    工行: %.2f | MA5: %.2f | MA10: %.2f | MA20: %.2f" % (d['price'], d['ma5'], d['ma10'], d['ma20']))
    print("    月超额: %+.2f%% | 波段涨: %+.2f%% | 距前低: %.2f" % (d['m_ret'], d['gain_from_trough'], d['trough']))
    print("    量比: %.2f | 上影线: %.2f%% | 大盘月: %+.2f%%" % (d['vol_ratio'], d['upper_shadow'], d['sh_m_ret']))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    result = calc_score()
    print_score(result)
