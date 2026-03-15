# Finance Service - 基金分析平台

基于 FastAPI + Vue3 的专业基金分析服务

## 功能特性

- 📊 **基金信息查询** - 实时净值、历史走势、基金档案
- 📈 **技术指标分析** - RSI、MACD、KDJ、BOLL、均线等
- 🎯 **买卖信号推荐** - 多指标综合分析给出建议
- 📰 **舆情分析** - 基金相关新闻情感分析
- 💼 **组合管理** - 创建投资组合、添加基金、收益跟踪
- 🔄 **收益回测** - 买入持有策略历史回测
- 🔌 **WebSocket实时推送** - 实时价格更新

## 快速开始

```bash
# 安装依赖
cd financeService-main
pip install fastapi uvicorn pandas numpy

# 启动服务
python -m uvicorn src.main:app --host 0.0.0.0 --port 9000
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页 |
| `/fund/info/{code}` | GET | 基金基本信息 |
| `/fund/analyze/{code}` | GET | 综合分析报告 |
| `/fund/holdings/{code}` | GET | 基金持仓明细 |
| `/sentiment/fund/{code}` | GET | 舆情分析 |
| `/portfolio/{user_id}` | GET/POST | 组合管理 |
| `/backtest` | GET | 收益回测 |
| `/ws` | WebSocket | 实时推送 |

## 前端界面

访问 `finance-web/index.html` 即可使用可视化界面

## 技术栈

- **后端**: FastAPI + Python
- **前端**: HTML5 + Bootstrap5 + Vue3
- **数据**: 东方财富API (模拟数据fallback)

## License

MIT
