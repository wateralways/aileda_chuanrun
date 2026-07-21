#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工行跷跷板过滤器 - ICBC Seesaw Filter

基于工商银行(601398.SH)的走势判断当前市场环境：
- 工行上行期(5日涨幅>2%) → 逃科技模式：减少/谨慎科技股买入
- 工行下行期(5日跌幅>2%) → 抄科技模式：增加科技股买入信心
- 震荡期(涨跌幅在±2%内) → 正常模式：不调整

使用方法：
    from icbc_filter import get_icbc_filter, ICBC_FILTER_UP, ICBC_FILTER_DOWN, ICBC_FILTER_NEUTRAL
    
    filter_result = get_icbc_filter()
    if filter_result['status'] == ICBC_FILTER_UP:
        print("工行上行，逃科技模式")
    elif filter_result['status'] == ICBC_FILTER_DOWN:
        print("工行下行，抄科技模式")
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# 常量
ICBC_FILTER_UP = 'up'        # 工行上行 → 逃科技
ICBC_FILTER_DOWN = 'down'    # 工行下行 → 抄科技
ICBC_FILTER_NEUTRAL = 'neutral'  # 震荡 → 正常

# 阈值
ROC_THRESHOLD = 2.0  # 5日涨跌幅阈值(%)

# ICBC Tushare代码
ICBC_TS_CODE = '601398.SH'

# 默认Tushare Token（从环境变量读取）
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '701a94c30c5d1c7af41602c8ebd47b1ca7a2c49bfdd5419379f40c8d')


def get_icbc_data(days=30):
    """获取工商银行最近日线数据
    
    Args:
        days: 需要获取的天数（至少22个交易日才能计算完整指标）
    
    Returns:
        DataFrame with columns: trade_date, close, pct_chg, ...
        失败返回 None
    """
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        end_date = datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d')
        # 多取一些确保有足够数据
        start_date = '20260101'
        
        df = pro.daily(ts_code=ICBC_TS_CODE, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            print("  [ICBC] Tushare数据为空")
            return None
        
        df = df.sort_values('trade_date').reset_index(drop=True)
        return df
        
    except Exception as e:
        print(f"  [ICBC] Tushare获取数据失败: {e}")
        return None


def get_icbc_filter(df=None, threshold=ROC_THRESHOLD):
    """计算工行跷跷板过滤器状态
    
    使用5日涨跌幅判断工行当前所处阶段：
    - 5日涨幅 > +threshold% → up (逃科技)
    - 5日跌幅 > -threshold% → down (抄科技)
    - 否则 → neutral (正常)
    
    Args:
        df: 工行日线数据（若为None则自动获取）
        threshold: 阈值百分比，默认2.0
    
    Returns:
        dict: {
            'status': 'up' | 'down' | 'neutral',
            'roc_5d': float,       # 5日涨跌幅(%)
            'close': float,        # 最新收盘价
            'date': str,           # 最新日期
            'roc_3d': float,       # 3日涨跌幅(%)
            'ma5': float,          # 5日均线
            'ma22': float,         # 22日均线
            'trend': str,          # 短期趋势描述
            'recommendation': str, # 操作建议
            'data_available': bool # 数据是否可用
        }
    """
    if df is None:
        df = get_icbc_data()
    
    if df is None or len(df) < 6:
        return {
            'status': ICBC_FILTER_NEUTRAL,
            'roc_5d': 0.0,
            'close': 0.0,
            'date': '',
            'roc_3d': 0.0,
            'ma5': 0.0,
            'ma22': 0.0,
            'trend': '数据不足',
            'recommendation': '正常操作（数据不足）',
            'data_available': False
        }
    
    try:
        latest = df.iloc[-1]
        close = float(latest['close'])
        date = str(latest['trade_date'])
        
        # 5日涨跌幅
        if len(df) >= 6:
            roc_5d = (close / float(df.iloc[-6]['close']) - 1) * 100
        else:
            roc_5d = 0.0
        
        # 3日涨跌幅
        if len(df) >= 4:
            roc_3d = (close / float(df.iloc[-4]['close']) - 1) * 100
        else:
            roc_3d = 0.0
        
        # 移动平均线
        closes = df['close'].values.astype(float)
        ma5 = np.mean(closes[-5:]) if len(closes) >= 5 else close
        ma22 = np.mean(closes[-22:]) if len(closes) >= 22 else close
        
        # 判断状态
        if roc_5d > threshold:
            status = ICBC_FILTER_UP
            trend = '工行上行期'
            recommendation = '⚠️ 逃科技模式：工行大涨，谨慎开新仓，已有仓位考虑减仓'
        elif roc_5d < -threshold:
            status = ICBC_FILTER_DOWN
            trend = '工行下行期'
            recommendation = '✅ 抄科技模式：工行大跌，可积极寻找买入机会'
        else:
            status = ICBC_FILTER_NEUTRAL
            trend = '工行震荡期'
            recommendation = '➖ 正常模式：工行波动不大，按原策略操作'
        
        return {
            'status': status,
            'roc_5d': round(roc_5d, 2),
            'close': round(close, 2),
            'date': date,
            'roc_3d': round(roc_3d, 2),
            'ma5': round(ma5, 2),
            'ma22': round(ma22, 2),
            'trend': trend,
            'recommendation': recommendation,
            'data_available': True,
            'threshold': threshold
        }
        
    except Exception as e:
        print(f"  [ICBC] 计算过滤器失败: {e}")
        return {
            'status': ICBC_FILTER_NEUTRAL,
            'roc_5d': 0.0,
            'close': 0.0,
            'date': '',
            'trend': '计算错误',
            'recommendation': '正常操作（计算异常）',
            'data_available': False
        }


def adjust_signal_confidence(filter_result, signal):
    """根据工行过滤器调整信号置信度
    
    在工行上行期(逃科技模式)：
    - 高置信度 → 降为中
    - 中置信度 → 降为低
    - 低置信度 → 忽略（不推荐）
    
    在工行下行期(抄科技模式)：
    - 中置信度 → 升为高
    - 低置信度 → 升为中
    
    Args:
        filter_result: get_icbc_filter()的返回值
        signal: 信号dict，包含 'confidence' 字段
    
    Returns:
        dict: 更新后的信号（含调整说明）
    """
    if not filter_result.get('data_available'):
        return signal
    
    status = filter_result['status']
    original_confidence = signal.get('confidence', '中')
    
    # 置信度映射
    confidence_level = {'极高': 4, '高': 3, '中': 2, '低': 1}
    level_to_text = {4: '极高', 3: '高', 2: '中', 1: '低'}
    
    orig_level = confidence_level.get(original_confidence, 2)
    new_level = orig_level
    
    adjust_reason = ''
    
    if status == ICBC_FILTER_UP:
        # 逃科技模式：降低信心
        new_level = max(1, orig_level - 1)
        if orig_level >= 3:
            adjust_reason = f'工行大涨{filter_result["roc_5d"]:+.1f}%，处于逃科技模式，信号置信度下调'
        else:
            adjust_reason = f'工行大涨{filter_result["roc_5d"]:+.1f}%，逃科技模式，建议观望'
            # 低置信度的直接标记为不推荐
            if orig_level <= 2:
                new_level = 1
    
    elif status == ICBC_FILTER_DOWN:
        # 抄科技模式：提升信心
        new_level = min(4, orig_level + 1)
        adjust_reason = f'工行下跌{filter_result["roc_5d"]:+.1f}%，处于抄科技模式，信号置信度上调'
    
    else:
        # 正常模式
        adjust_reason = f'工行震荡({filter_result["roc_5d"]:+.1f}%)，按原策略操作'
    
    new_confidence = level_to_text.get(new_level, original_confidence)
    
    updated_signal = dict(signal)
    updated_signal['confidence'] = new_confidence
    updated_signal['icbc_adjusted'] = True
    updated_signal['original_confidence'] = original_confidence
    updated_signal['icbc_adjust_reason'] = adjust_reason
    
    return updated_signal


# ===== 便捷函数 =====

def is_icbc_up(filter_result):
    """工行是否处于上行期（逃科技模式）"""
    return filter_result.get('status') == ICBC_FILTER_UP

def is_icbc_down(filter_result):
    """工行是否处于下行期（抄科技模式）"""
    return filter_result.get('status') == ICBC_FILTER_DOWN

def is_icbc_neutral(filter_result):
    """工行是否处于震荡期（正常模式）"""
    return filter_result.get('status') == ICBC_FILTER_NEUTRAL


# ===== 命令行测试 =====
if __name__ == '__main__':
    result = get_icbc_filter()
    print(f"\n{'='*50}")
    print(f"工行跷跷板过滤器")
    print(f"{'='*50}")
    if result['data_available']:
        print(f"  日期: {result['date']}")
        print(f"  收盘价: {result['close']}")
        print(f"  5日涨跌幅: {result['roc_5d']:+.2f}%")
        print(f"  3日涨跌幅: {result['roc_3d']:+.2f}%")
        print(f"  MA5: {result['ma5']}  MA22: {result['ma22']}")
        print(f"  状态: {result['trend']}")
        print(f"  建议: {result['recommendation']}")
    else:
        print(f"  数据不可用")
    print()
