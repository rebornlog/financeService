# -*- coding: utf-8 -*-
"""
Finance Service API - 基金分析服务API
支持真实基金数据获取和技术分析
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入数据采集
from src.data.fund_fetcher import FundDataFetcher
from src.quant.analyzer import QuantitativeAnalyzer, SignalType

app = FastAPI(
    title="Finance Service API",
    description="基金分析服务 - 实时净值、技术指标、舆情分析、买卖建议",
    version="1.1.0"
)

# 初始化组件
fund_fetcher = FundDataFetcher()
analyzer = QuantitativeAnalyzer()

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


@app.get("/")
def root():
    """根路径"""
    return {
        "message": "Finance Service API - 基金分析平台",
        "version": "1.1.0",
        "endpoints": [
            "/",
            "/health",
            "/fund/info/{fund_code} - 基金基本信息",
            "/fund/history/{fund_code} - 历史净值",
            "/fund/search - 搜索基金",
            "/fund/analyze/{fund_code} - 综合分析",
            "/mock/analyze/{symbol} - 模拟分析",
            "/docs - API文档"
        ]
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ==================== 基金数据接口 ====================

@app.get("/fund/info/{fund_code}")
def get_fund_info(fund_code: str):
    """
    获取基金基本信息
    
    Args:
        fund_code: 基金代码 (如 161039, 000001)
    """
    info = fund_fetcher.get_fund_info(fund_code)
    
    if 'error' in info:
        raise HTTPException(status_code=404, detail=info['error'])
    
    return info


@app.get("/fund/history/{fund_code}")
def get_fund_history(
    fund_code: str, 
    days: int = Query(90, ge=1, le=365)
):
    """
    获取基金历史净值
    
    Args:
        fund_code: 基金代码
        days: 获取天数 (默认90天)
    """
    df = fund_fetcher.get_historical_nav(fund_code, days)
    
    if df.empty:
        raise HTTPException(status_code=404, detail="未获取到历史数据")
    
    # 转换为JSON格式
    return {
        'fund_code': fund_code,
        'days': days,
        'count': len(df),
        'data': df.to_dict(orient='records')
    }


@app.get("/fund/search")
def search_fund(q: str = Query(..., min_length=1)):
    """
    搜索基金
    
    Args:
        q: 搜索关键词 (基金代码或名称)
    """
    results = fund_fetcher.search_fund(q)
    return {
        'keyword': q,
        'count': len(results),
        'results': results
    }


@app.get("/fund/manager/{fund_code}")
def get_fund_manager(fund_code: str):
    """获取基金经理信息"""
    managers = fund_fetcher.get_fund_manager(fund_code)
    return {
        'fund_code': fund_code,
        'managers': managers
    }


@app.get("/fund/holdings/{fund_code}")
def get_fund_holdings(fund_code: str):
    """获取基金持仓"""
    holdings = fund_fetcher.get_fund_holdings(fund_code)
    return {
        'fund_code': fund_code,
        'holdings': holdings
    }


# ==================== 分析接口 ====================

@app.get("/fund/analyze/{fund_code}")
def analyze_fund(
    fund_code: str,
    days: int = Query(90, ge=30, le=365)
):
    """
    综合基金分析
    
    Args:
        fund_code: 基金代码
        days: 分析天数
    
    Returns:
        包含技术指标、信号、建议的完整分析
    """
    # 1. 获取基金基本信息
    fund_info = fund_fetcher.get_fund_info(fund_code)
    if 'error' in fund_info:
        raise HTTPException(status_code=404, detail=fund_info['error'])
    
    # 2. 获取历史数据
    hist_df = fund_fetcher.get_historical_nav(fund_code, days)
    if hist_df.empty:
        raise HTTPException(status_code=404, detail="获取历史数据失败")
    
    # 3. 转换为OHLCV格式
    data = pd.DataFrame({
        'date': hist_df['date'],
        'open': hist_df['net_value'],
        'high': hist_df['net_value'] * 1.02,  # 估算
        'low': hist_df['net_value'] * 0.98,   # 估算
        'close': hist_df['net_value'],
        'volume': hist_df['acc_net_value'] * 1000000  # 估算
    })
    data.set_index('date', inplace=True)
    
    # 4. 执行技术分析
    try:
        result = analyzer.analyze_stock(
            symbol=fund_code,
            data=data,
            indicators=['RSI', 'MA', 'VOL', 'MACD', 'KDJ', 'BOLL']
        )
        
        # 5. 构建响应
        return {
            'symbol': fund_code,
            'fund_name': fund_info.get('fund_name', ''),
            'timestamp': str(result.timestamp),
            'net_value': fund_info.get('net_value', 0),
            'growth_rate': fund_info.get('growth_rate', 0),
            'indicators': [
                {
                    'name': ind.name,
                    'value': float(ind.value),
                    'signal': ind.signal.value,
                    'confidence': float(ind.confidence)
                }
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
        return "强烈建议买入 ✅"
    elif signal == "BUY":
        return "可以考虑买入 📈"
    elif signal == "SELL" and confidence > 0.7:
        return "建议卖出 ⚠️"
    elif signal == "SELL":
        return "可以考虑卖出 📉"
    else:
        return "建议持有 ⏸️"


# ==================== 模拟数据接口 (保留) ====================

@app.get("/mock/analyze/{symbol}")
def mock_analyze(symbol: str):
    """模拟分析接口（用于测试）"""
    # 生成模拟数据
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
    
    result = analyzer.analyze_stock(
        symbol=symbol,
        data=data,
        indicators=['RSI', 'MA', 'VOL']
    )
    
    return {
        "symbol": symbol,
        "type": "模拟数据",
        "timestamp": str(result.timestamp),
        "indicators": [
            {
                "name": ind.name,
                "value": float(ind.value),
                "signal": ind.signal.value,
                "confidence": float(ind.confidence)
            }
            for ind in result.indicators
        ],
        "overall_signal": result.overall_signal.value,
        "confidence_score": float(result.confidence_score),
        "risk_level": result.risk_level,
        "recommendation": get_recommendation(result)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
