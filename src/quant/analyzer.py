# -*- coding: utf-8 -*-
"""
Quantitative Analysis Engine for FinanceService
专业量化分析引擎
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class TechnicalIndicator:
    name: str
    value: float
    signal: SignalType
    confidence: float

@dataclass
class AnalysisResult:
    symbol: str
    timestamp: pd.Timestamp
    indicators: List[TechnicalIndicator]
    overall_signal: SignalType
    confidence_score: float
    price_target: Optional[float] = None
    risk_level: str = "MEDIUM"

class QuantitativeAnalyzer:
    """
    高级量化分析引擎
    支持多因子模型、机器学习预测、技术指标分析
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        
    def analyze_stock(self, 
                     symbol: str,
                     data: pd.DataFrame,
                     indicators: List[str] = None) -> AnalysisResult:
        """
        综合股票分析
        
        Args:
            symbol: 股票代码
            data: 历史价格数据 (OHLCV格式)
            indicators: 要计算的技术指标列表
            
        Returns:
            AnalysisResult: 分析结果
        """
        if indicators is None:
            indicators = ['RSI', 'MA', 'VOL']
            
        # 数据预处理
        df = self._preprocess_data(data)
        
        # 计算技术指标
        technical_indicators = self._calculate_technical_indicators(df, indicators)
        
        # 综合信号生成
        overall_signal, confidence = self._generate_combined_signal(technical_indicators)
        
        # 价格目标预测
        price_target = self._predict_price_target(df, technical_indicators)
        
        # 风险评估
        risk_level = self._assess_risk(df, technical_indicators)
        
        return AnalysisResult(
            symbol=symbol,
            timestamp=df.index[-1],
            indicators=technical_indicators,
            overall_signal=overall_signal,
            confidence_score=confidence,
            price_target=price_target,
            risk_level=risk_level
        )
    
    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """数据预处理"""
        df = data.copy()
        
        # 确保必要的列存在
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # 处理缺失值
        df = df.ffill()
        
        # 计算对数收益率
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        # 计算波动率
        df['volatility'] = df['log_return'].rolling(window=20).std() * np.sqrt(252)
        
        return df
    
    def _calculate_technical_indicators(self, 
                                      df: pd.DataFrame, 
                                      indicators: List[str]) -> List[TechnicalIndicator]:
        """计算技术指标"""
        results = []
        
        for indicator in indicators:
            try:
                if indicator == 'RSI':
                    result = self._calc_rsi(df)
                    if result:
                        results.append(result)
                        
                elif indicator == 'MA':
                    result = self._calc_ma(df)
                    if result:
                        results.append(result)
                        
                elif indicator == 'VOL':
                    result = self._calc_vol(df)
                    if result:
                        results.append(result)
                
                elif indicator == 'MACD':
                    result = self._calc_macd(df)
                    if result:
                        results.append(result)
                
                elif indicator == 'KDJ':
                    result = self._calc_kdj(df)
                    if result:
                        results.append(result)
                
                elif indicator == 'BOLL':
                    result = self._calc_boll(df)
                    if result:
                        results.append(result)
                        
            except Exception as e:
                print(f"Error calculating {indicator}: {e}")
                continue
                
        return results
    
    def _calc_rsi(self, df: pd.DataFrame) -> Optional[TechnicalIndicator]:
        """计算RSI指标"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        latest_rsi = rsi.iloc[-1]
        
        if latest_rsi < 30:
            signal = SignalType.BUY
            confidence = (30 - latest_rsi) / 30
        elif latest_rsi > 70:
            signal = SignalType.SELL
            confidence = (latest_rsi - 70) / 30
        else:
            signal = SignalType.HOLD
            confidence = 0.5
            
        return TechnicalIndicator(
            name='RSI(14)', 
            value=latest_rsi,
            signal=signal,
            confidence=min(confidence, 1.0)
        )
    
    def _calc_ma(self, df: pd.DataFrame) -> Optional[TechnicalIndicator]:
        """计算移动平均线"""
        ma5 = df['close'].rolling(window=5).mean()
        ma20 = df['close'].rolling(window=20).mean()
        
        if ma5.iloc[-1] > ma20.iloc[-1] and ma5.iloc[-2] <= ma20.iloc[-2]:
            signal = SignalType.BUY
            confidence = 0.7
        elif ma5.iloc[-1] < ma20.iloc[-1] and ma5.iloc[-2] >= ma20.iloc[-2]:
            signal = SignalType.SELL
            confidence = 0.7
        else:
            signal = SignalType.HOLD
            confidence = 0.5
            
        return TechnicalIndicator(
            name='MA(5,20)',
            value=ma5.iloc[-1] - ma20.iloc[-1],
            signal=signal,
            confidence=confidence
        )
    
    def _calc_vol(self, df: pd.DataFrame) -> Optional[TechnicalIndicator]:
        """成交量分析"""
        vol_ma = df['volume'].rolling(window=20).mean()
        current_vol = df['volume'].iloc[-1]
        vol_ratio = current_vol / vol_ma.iloc[-1]
        
        if vol_ratio > 1.5:
            signal = SignalType.BUY
            confidence = min(vol_ratio / 3, 1.0)
        elif vol_ratio < 0.5:
            signal = SignalType.SELL
            confidence = min((1 - vol_ratio) / 2, 1.0)
        else:
            signal = SignalType.HOLD
            confidence = 0.5
            
        return TechnicalIndicator(
            name='VOL',
            value=vol_ratio,
            signal=signal,
            confidence=confidence
        )
    
    def _calc_macd(self, df: pd.DataFrame) -> Optional[TechnicalIndicator]:
        """计算MACD指标"""
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line
        
        # 最新值
        macd_val = macd_line.iloc[-1]
        signal_val = signal_line.iloc[-1]
        hist_val = macd_hist.iloc[-1]
        
        # 前一个值
        macd_prev = macd_line.iloc[-2]
        signal_prev = signal_line.iloc[-2]
        
        # 金叉/死叉判断
        if macd_val > signal_val and macd_prev <= signal_prev:
            signal = SignalType.BUY
            confidence = 0.75
        elif macd_val < signal_val and macd_prev >= signal_prev:
            signal = SignalType.SELL
            confidence = 0.75
        elif hist_val > 0:
            signal = SignalType.BUY
            confidence = 0.5
        else:
            signal = SignalType.SELL
            confidence = 0.5
            
        return TechnicalIndicator(
            name='MACD(12,26,9)',
            value=hist_val,
            signal=signal,
            confidence=confidence
        )
    
    def _calc_kdj(self, df: pd.DataFrame) -> Optional[TechnicalIndicator]:
        """计算KDJ指标"""
        low_n = df['low'].rolling(window=9).min()
        high_n = df['high'].rolling(window=9).max()
        
        k = 100 * (df['close'] - low_n) / (high_n - low_n)
        k = k.fillna(50)
        d = k.rolling(window=3).mean()
        j = 3 * k - 2 * d
        
        k_val = k.iloc[-1]
        d_val = d.iloc[-1]
        j_val = j.iloc[-1]
        
        # 超买超卖判断
        if k_val < 20 or d_val < 20:
            signal = SignalType.BUY
            confidence = (20 - min(k_val, d_val)) / 20
        elif k_val > 80 or d_val > 80:
            signal = SignalType.SELL
            confidence = (max(k_val, d_val) - 80) / 20
        else:
            signal = SignalType.HOLD
            confidence = 0.5
            
        return TechnicalIndicator(
            name='KDJ(9,3,3)',
            value=j_val,
            signal=signal,
            confidence=min(confidence, 1.0)
        )
    
    def _calc_boll(self, df: pd.DataFrame) -> Optional[TechnicalIndicator]:
        """计算布林带指标"""
        ma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        
        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20
        
        current_price = df['close'].iloc[-1]
        bb_position = (current_price - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
        
        if bb_position < 0.2:
            signal = SignalType.BUY
            confidence = (0.2 - bb_position) / 0.2
        elif bb_position > 0.8:
            signal = SignalType.SELL
            confidence = (bb_position - 0.8) / 0.2
        else:
            signal = SignalType.HOLD
            confidence = 0.5
            
        return TechnicalIndicator(
            name='BOLL(20,2)',
            value=bb_position,
            signal=signal,
            confidence=min(confidence, 1.0)
        )
    
    def _generate_combined_signal(self, 
                                technical_indicators: List[TechnicalIndicator]) -> Tuple[SignalType, float]:
        """生成综合交易信号"""
        # 技术指标投票
        buy_votes = sum(1 for ind in technical_indicators if ind.signal == SignalType.BUY)
        sell_votes = sum(1 for ind in technical_indicators if ind.signal == SignalType.SELL)
        hold_votes = sum(1 for ind in technical_indicators if ind.signal == SignalType.HOLD)
        
        # 选择最高票数的信号
        if buy_votes > sell_votes and buy_votes > hold_votes:
            final_signal = SignalType.BUY
            confidence = sum(ind.confidence for ind in technical_indicators if ind.signal == SignalType.BUY) / buy_votes
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            final_signal = SignalType.SELL
            confidence = sum(ind.confidence for ind in technical_indicators if ind.signal == SignalType.SELL) / sell_votes
        else:
            final_signal = SignalType.HOLD
            confidence = 0.5
        
        return final_signal, min(confidence, 1.0)
    
    def _predict_price_target(self, 
                            df: pd.DataFrame, 
                            indicators: List[TechnicalIndicator]) -> Optional[float]:
        """预测价格目标"""
        current_price = df['close'].iloc[-1]
        
        # 基于ATR的波动性调整
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        
        buy_signals = sum(1 for ind in indicators if ind.signal == SignalType.BUY)
        sell_signals = sum(1 for ind in indicators if ind.signal == SignalType.SELL)
        
        if buy_signals > sell_signals:
            # 看涨目标：当前价格 + 2倍ATR
            return current_price + 2 * atr
        elif sell_signals > buy_signals:
            # 看跌目标：当前价格 - 2倍ATR
            return current_price - 2 * atr
        else:
            # 中性：当前价格 ± 1倍ATR
            return current_price + atr
    
    def _assess_risk(self, 
                    df: pd.DataFrame, 
                    indicators: List[TechnicalIndicator]) -> str:
        """风险评估"""
        # 波动率风险
        volatility = df['volatility'].iloc[-1]
        
        # 技术指标分歧度
        signal_variance = np.var([ind.confidence for ind in indicators])
        
        # 综合风险评分
        risk_score = volatility * 0.7 + signal_variance * 0.3
        
        if risk_score < 0.1:
            return "LOW"
        elif risk_score < 0.3:
            return "MEDIUM"
        else:
            return "HIGH"

# 使用示例
if __name__ == "__main__":
    # 创建分析器实例
    analyzer = QuantitativeAnalyzer()
    
    # 模拟数据
    dates = pd.date_range('2023-01-01', '2026-03-09', freq='D')
    np.random.seed(42)
    prices = 100 * (1 + np.random.randn(len(dates)).cumsum() * 0.02)
    
    data = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, len(dates))
    }, index=dates)
    
    # 分析股票
    result = analyzer.analyze_stock('AAPL', data)
    
    print(f"分析结果: {result.symbol}")
    print(f"时间: {result.timestamp}")
    print(f"综合信号: {result.overall_signal.value}")
    print(f"置信度: {result.confidence_score:.2f}")
    print(f"价格目标: {result.price_target:.2f}")
    print(f"风险等级: {result.risk_level}")
    
    print("\n技术指标:")
    for indicator in result.indicators:
        print(f"  {indicator.name}: {indicator.value:.2f} ({indicator.signal.value}, 置信度: {indicator.confidence:.2f})")
