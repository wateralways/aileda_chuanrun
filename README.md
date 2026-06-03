# 📊 川润股份 & 爱乐达 短线策略系统

> 基于2026年历史数据回测的高胜率短线交易策略 | 持股8天 | 每日自动扫描

[![Daily Scan](https://github.com/wateralways/aileda_chuanrun/actions/workflows/daily.yml/badge.svg)](https://github.com/wateralways/aileda_chuanrun/actions/workflows/daily.yml)
[![Report](https://img.shields.io/badge/最新报告-点击查看-blue)](https://wateralways.github.io/aileda_chuanrun/reports/)

---

## 🎯 策略概览

| 股票 | 策略类型 | 核心策略 | 胜率 | 总收益 | 持股天数 |
|-----|---------|---------|:---:|---:|:---:|
| **川润股份** (002272) | 趋势突破 | 放量突破 | 100% | +60.30% | 8天 |
| **爱乐达** (300696) | 回调反弹 | 连阴首阳 | 62.5% | +24.81% | 8天 |

📖 [策略详细说明文档](https://wateralways.github.io/aileda_chuanrun/docs/strategy.html)

---

## ⚡ 每日自动扫描

- **运行时间**：每个交易日 14:45 (北京时间)
- **数据来源**：Tushare Pro
- **扫描内容**：
  - 川润股份：放量突破 / 晨星形态 / 阳线吞没
  - 爱乐达：连阴首阳 / 放量见底 / 均线粘合突破
- **报告输出**：HTML网页报告，包含实时指标和操作建议

📊 [查看最新扫描报告](https://wateralways.github.io/aileda_chuanrun/reports/)

---

## 📁 项目结构

```
.
├── .github/workflows/       # GitHub Actions 工作流
│   └── daily.yml            # 每日14:45自动扫描
├── strategy/                # 策略核心代码
│   ├── signals.py           # 策略信号定义
│   ├── daily_scan.py        # 每日扫描入口
│   └── report_generator.py  # HTML报告生成
├── docs/                    # 文档和说明
│   └── strategy.html        # 策略详细说明页
├── reports/                 # 生成的报告
│   └── index.html           # 最新报告
├── requirements.txt         # Python依赖
└── README.md                # 本文件
```

---

## 🛠️ 本地运行

```bash
# 克隆仓库
git clone https://github.com/wateralways/aileda_chuanrun.git
cd aileda_chuanrun

# 安装依赖
pip install -r requirements.txt

# 设置Tushare Token (可选，默认已配置)
export TUSHARE_TOKEN=your_token_here

# 运行扫描
cd strategy
python daily_scan.py

# 生成报告
python report_generator.py
```

---

## 📈 回测详情

### 川润股份 - 放量突破策略

| 买入日期 | 买入价 | 卖出日期 | 卖出价 | 盈亏 |
|---------|------:|---------|------:|-----:|
| 2026-02-06 | 15.39 | 2026-02-26 | 19.21 | +24.82% |
| 2026-02-27 | 19.47 | 2026-03-11 | 20.69 | +6.27% |
| 2026-03-30 | 18.06 | 2026-04-10 | 19.12 | +5.87% |
| 2026-05-07 | 19.86 | 2026-05-19 | 22.67 | +14.15% |

### 爱乐达 - 连阴首阳策略

| 买入日期 | 买入价 | 卖出日期 | 卖出价 | 盈亏 |
|---------|------:|---------|------:|-----:|
| 2026-01-19 | 31.10 | 2026-01-29 | 33.80 | +8.68% |
| 2026-04-14 | 31.99 | 2026-04-24 | 37.64 | +17.66% |
| 2026-04-27 | 38.61 | 2026-05-12 | 43.11 | +11.66% |

---

## ⚠️ 风险提示

1. **样本量有限**：回测基于2026年1-6月共98个交易日，部分策略交易次数较少
2. **过拟合风险**：策略参数基于历史数据优化，未来表现可能不同
3. **市场环境变化**：当前市场环境可能与后续不同
4. **单一股票风险**：建议严格控制单票仓位
5. **交易成本**：实际交易需考虑佣金、印花税、滑点等

> **免责声明**：本策略仅供学习研究，不构成投资建议。股市有风险，投资需谨慎。

---

## 🔗 链接

- 📊 [最新扫描报告](https://wateralways.github.io/aileda_chuanrun/reports/)
- 📖 [策略详细说明](https://wateralways.github.io/aileda_chuanrun/docs/strategy.html)
- 🔄 [Actions运行记录](https://github.com/wateralways/aileda_chuanrun/actions)
