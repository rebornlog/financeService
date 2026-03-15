# -*- coding: utf-8 -*-
"""
Finance Service API - 基金分析服务API
支持真实基金数据获取和技术分析、实时推送、组合管理
"""

from fastapi import FastAPI, HTTPException, Query, Body, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 静态文件目录 - 指向正确的Claw目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # financeService-main
CLAW_DIR = os.path.dirname(BASE_DIR)  # Claw
STATIC_DIR = os.path.join(CLAW_DIR, 'finance-web')

# 导入数据采集
from src.data.fund_fetcher import FundDataFetcher
from src.data.sentiment import SentimentAnalyzer
from src.quant.analyzer import QuantitativeAnalyzer, SignalType
from src.websocket_manager import manager, portfolio_manager, start_fund_price_stream, start_market_summary_stream

app = FastAPI(
    title="Finance Service API",
    description="基金分析服务 - 实时净值、技术指标、舆情分析、买卖建议、组合管理",
    version="1.4.0"
)

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
fund_fetcher = FundDataFetcher()
analyzer = QuantitativeAnalyzer()
sentiment_analyzer = SentimentAnalyzer()

# 请求模型
class AnalysisRequest(BaseModel):
    symbol: str
    indicators: Optional[List[str]] = None


class AnalysisResponse(BaseModel):
    symbol: str
    fund_name: str
    timestamp: str
    net_value: float
    growth_rate: float
    indicators: List[Dict]
    overall_signal: str
    confidence_score: float
    price_target: Optional[float] = None
    risk_level: str
    recommendation: str


@app.on_event("startup")
async def startup_event():
    """启动后台任务"""
    asyncio.create_task(start_fund_price_stream(manager))
    asyncio.create_task(start_market_summary_stream(manager))


@app.get("/")
def root():
    """根路径"""
    return {
        "message": "Finance Service API - 基金分析平台",
        "version": "1.4.0",
        "endpoints": [
            "/",
            "/health",
            "/ws - WebSocket实时推送",
            "/portfolio - 组合管理",
            "/backtest - 收益回测",
            "/fund/info/{fund_code} - 基金基本信息",
            "/fund/analyze/{fund_code} - 综合分析",
            "/sentiment/fund/{fund_code} - 舆情分析",
            "/docs - API文档"
        ]
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ==================== WebSocket接口 ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket实时推送"""
    client_id = websocket.query_params.get("client_id", "unknown")
    await manager.connect(websocket, client_id)
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            'type': 'connected',
            'client_id': client_id,
            'message': '连接成功, 可以订阅基金'
        })
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            
            action = data.get('action')
            
            if action == 'subscribe':
                funds = data.get('funds', [])
                manager.subscribe(websocket, funds)
                await websocket.send_json({
                    'type': 'subscribed',
                    'funds': funds
                })
                
            elif action == 'unsubscribe':
                funds = data.get('funds', [])
                manager.unsubscribe(websocket, funds)
                await websocket.send_json({
                    'type': 'unsubscribed',
                    'funds': funds
                })
                
            elif action == 'ping':
                await websocket.send_json({'type': 'pong'})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception as e:
        print(f"WebSocket错误: {e}")
        manager.disconnect(websocket, client_id)


# ==================== 组合管理接口 ====================

@app.post("/portfolio/{user_id}")
def create_portfolio(user_id: str, name: str = "我的组合"):
    """创建基金组合"""
    portfolio = portfolio_manager.create_portfolio(user_id, name)
    return {
        'success': True,
        'portfolio': portfolio
    }


@app.get("/portfolio/{user_id}")
def get_portfolios(user_id: str):
    """获取用户所有组合"""
    portfolios = portfolio_manager.get_portfolio(user_id)
    if portfolios is None:
        return {'portfolios': [], 'message': '暂无组合'}
    return {'portfolios': portfolios}


@app.get("/portfolio/{user_id}/{portfolio_id}")
def get_portfolio_detail(user_id: str, portfolio_id: int):
    """获取组合详情"""
    portfolio = portfolio_manager.get_portfolio(user_id, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="组合不存在")
    return portfolio


@app.post("/portfolio/{user_id}/{portfolio_id}/add")
def add_fund_to_portfolio(
    user_id: str, 
    portfolio_id: int,
    fund_code: str = Body(...),
    shares: float = Body(...),
    cost: float = Body(...)
):
    """添加基金到组合"""
    result = portfolio_manager.add_fund(user_id, portfolio_id, fund_code, shares, cost)
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])
    return {'success': True, 'holding': result}


@app.delete("/portfolio/{user_id}/{portfolio_id}/remove/{fund_code}")
def remove_fund_from_portfolio(user_id: str, portfolio_id: int, fund_code: str):
    """从组合移除基金"""
    success = portfolio_manager.remove_fund(user_id, portfolio_id, fund_code)
    if not success:
        raise HTTPException(status_code=404, detail="移除失败")
    return {'success': True, 'message': f'已移除 {fund_code}'}


# ==================== 回测接口 ====================

@app.get("/backtest")
def backtest(
    fund_code: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    initial_money: float = Query(100000)
):
    """
    基金收益回测
    
    Args:
        fund_code: 基金代码
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        initial_money: 初始资金
    """
    # 获取历史数据
    days = (datetime.strptime(end_date, '%Y-%m-%d') - 
            datetime.strptime(start_date, '%Y-%m-%d')).days
    
    df = fund_fetcher.get_historical_nav(fund_code, days)
    
    if df.empty:
        raise HTTPException(status_code=404, detail="获取历史数据失败")
    
    # 简单回测: 买入持有策略
    df = df.tail(min(days, 365))  # 最多一年
    
    initial_nav = df['net_value'].iloc[0]
    final_nav = df['net_value'].iloc[-1]
    
    # 计算收益
    shares = initial_money / initial_nav
    final_value = shares * final_nav
    total_return = final_value - initial_money
    return_pct = (total_return / initial_money) * 100
    
    # 计算年化收益
    years = len(df) / 252
    annual_return = ((final_nav / initial_nav) ** (1/years) - 1) * 100 if years > 0 else 0
    
    # 计算最大回撤
    df['cummax'] = df['net_value'].cummax()
    df['drawdown'] = (df['net_value'] - df['cummax']) / df['cummax']
    max_drawdown = df['drawdown'].min() * 100
    
    # 每月收益
    df['month'] = df['date'].dt.to_period('M')
    monthly_returns = df.groupby('month')['daily_gain_pct'].sum()
    
    return {
        'fund_code': fund_code,
        'period': {
            'start': start_date,
            'end': end_date,
            'days': len(df)
        },
        'results': {
            'initial_money': initial_money,
            'final_value': round(final_value, 2),
            'total_return': round(total_return, 2),
            'return_pct': round(return_pct, 2),
            'annual_return': round(annual_return, 2),
            'max_drawdown': round(max_drawdown, 2)
        },
        'monthly_best': round(monthly_returns.max(), 2) if len(monthly_returns) > 0 else 0,
        'monthly_worst': round(monthly_returns.min(), 2) if len(monthly_returns) > 0 else 0,
        'win_rate': round((monthly_returns > 0).sum() / len(monthly_returns) * 100, 2) if len(monthly_returns) > 0 else 0
    }


# ==================== 基金数据接口 ====================

@app.get("/fund/info/{fund_code}")
def get_fund_info(fund_code: str):
    """获取基金基本信息"""
    info = fund_fetcher.get_fund_info(fund_code)
    if 'error' in info:
        raise HTTPException(status_code=404, detail=info['error'])
    return info


@app.get("/fund/history/{fund_code}")
def get_fund_history(fund_code: str, days: int = Query(90, ge=1, le=365)):
    """获取基金历史净值"""
    df = fund_fetcher.get_historical_nav(fund_code, days)
    if df.empty:
        raise HTTPException(status_code=404, detail="未获取到历史数据")
    return {
        'fund_code': fund_code,
        'days': days,
        'count': len(df),
        'data': df.to_dict(orient='records')
    }


@app.get("/fund/search")
def search_fund(q: str = Query(..., min_length=1)):
    """搜索基金"""
    results = fund_fetcher.search_fund(q)
    return {'keyword': q, 'count': len(results), 'results': results}


@app.get("/fund/manager/{fund_code}")
def get_fund_manager_info(fund_code: str):
    """获取基金经理信息"""
    return fund_fetcher.get_fund_manager(fund_code)


@app.get("/fund/holdings/{fund_code}")
def get_fund_holdings(fund_code: str):
    """获取基金持仓"""
    holdings = fund_fetcher.get_fund_holdings(fund_code)
    return {'fund_code': fund_code, 'holdings': holdings}


@app.get("/fund/dividend/{fund_code}")
def get_fund_dividend_info(fund_code: str):
    """获取基金分红历史"""
    return {'fund_code': fund_code, 'dividends': fund_fetcher.get_fund_dividend(fund_code)}


@app.post("/fund/compare")
def compare_funds(fund_codes: List[str] = Body(...)):
    """基金对比分析"""
    return fund_fetcher.get_fund_compare(fund_codes)


# ==================== 舆情分析接口 ====================

@app.get("/sentiment/fund/{fund_code}")
def get_fund_sentiment(fund_code: str):
    """获取基金舆情分析"""
    return sentiment_analyzer.get_fund_sentiment_summary(fund_code)


@app.get("/sentiment/market")
def get_market_sentiment():
    """获取市场整体情绪"""
    return sentiment_analyzer.get_market_sentiment()


# ==================== 分析接口 ====================

@app.get("/fund/analyze/{fund_code}")
def analyze_fund(fund_code: str, days: int = Query(90, ge=30, le=365)):
    """综合基金分析"""
    fund_info = fund_fetcher.get_fund_info(fund_code)
    if 'error' in fund_info:
        raise HTTPException(status_code=404, detail=fund_info['error'])
    
    hist_df = fund_fetcher.get_historical_nav(fund_code, days)
    if hist_df.empty:
        raise HTTPException(status_code=404, detail="获取历史数据失败")
    
    data = pd.DataFrame({
        'date': hist_df['date'],
        'open': hist_df['net_value'],
        'high': hist_df['net_value'] * 1.02,
        'low': hist_df['net_value'] * 0.98,
        'close': hist_df['net_value'],
        'volume': hist_df['acc_net_value'] * 1000000
    })
    data.set_index('date', inplace=True)
    
    try:
        result = analyzer.analyze_stock(
            symbol=fund_code,
            data=data,
            indicators=['RSI', 'MA', 'VOL', 'MACD', 'KDJ', 'BOLL']
        )
        
        return {
            'symbol': fund_code,
            'fund_name': fund_info.get('fund_name', ''),
            'timestamp': str(result.timestamp),
            'net_value': fund_info.get('net_value', 0),
            'growth_rate': fund_info.get('growth_rate', 0),
            'indicators': [
                {'name': ind.name, 'value': float(ind.value), 
                 'signal': ind.signal.value, 'confidence': float(ind.confidence)}
                for ind in result.indicators
            ],
            'overall_signal': result.overall_signal.value,
            'confidence_score': float(result.confidence_score),
            'price_target': float(result.price_target) if result.price_target else None,
            'risk_level': result.risk_level,
            'recommendation': get_recommendation(result),
            'analysis_days': days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


def get_recommendation(result) -> str:
    """根据分析结果给出建议"""
    signal = result.overall_signal.value
    confidence = result.confidence_score
    
    if signal == "BUY" and confidence > 0.7:
        return "强烈建议买入"
    elif signal == "BUY":
        return "可以考虑买入"
    elif signal == "SELL" and confidence > 0.7:
        return "建议卖出"
    elif signal == "SELL":
        return "可以考虑卖出"
    else:
        return "建议持有"


@app.get("/mock/analyze/{symbol}")
def mock_analyze(symbol: str):
    """模拟分析接口"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    base_price = 1.5
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * np.exp(np.cumsum(returns))
    
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
        'high': prices * (1 + np.random.uniform(0.01, 0.03, 100)),
        'low': prices * (1 + np.random.uniform(-0.03, -0.01, 100)),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, 100)
    })
    data.set_index('date', inplace=True)
    
    result = analyzer.analyze_stock(symbol=symbol, data=data, indicators=['RSI', 'MA', 'VOL'])
    
    return {
        "symbol": symbol,
        "type": "模拟数据",
        "timestamp": str(result.timestamp),
        "indicators": [
            {"name": ind.name, "value": float(ind.value), 
             "signal": ind.signal.value, "confidence": float(ind.confidence)}
            for ind in result.indicators
        ],
        "overall_signal": result.overall_signal.value,
        "confidence_score": float(result.confidence_score),
        "risk_level": result.risk_level,
        "recommendation": get_recommendation(result)
    }


# ==================== 静态文件服务 ====================
@app.get("/")
def root():
    """首页 - 重定向到前端页面"""
    index_path = os.path.join(STATIC_DIR, 'index.html')
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Finance Service API", "version": "1.4.0", "docs": "/docs"}

@app.get("/finance-web/{file_path:path}")
def serve_static(file_path: str):
    """静态文件服务"""
    file_path_full = os.path.join(STATIC_DIR, file_path)
    if os.path.exists(file_path_full):
        return FileResponse(file_path_full)
    raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
