# -*- coding: utf-8 -*-
"""
舆情分析模块
支持雪球财经社区、新闻情感分析
"""

import requests
import pandas as pd
import re
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import numpy as np


class SentimentAnalyzer:
    """舆情分析器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://xueqiu.com/'
        }
        
        # 情感词典
        self.positive_words = {
            '上涨': 0.6, '看好': 0.8, '增持': 0.7, '买入': 0.7, '推荐': 0.6,
            '优质': 0.7, '低估': 0.6, '价值': 0.5, '机会': 0.5, '抄底': 0.7,
            '加仓': 0.6, '重仓': 0.6, '利好': 0.7, '突破': 0.5, '强势': 0.6,
            '分红': 0.5, '业绩增长': 0.7, '前景好': 0.7, '稳': 0.4, '牛': 0.7,
            '大赚': 0.8, '盈利': 0.6, '收益高': 0.7, '创新高': 0.7
        }
        
        self.negative_words = {
            '下跌': -0.6, '看空': -0.8, '减持': -0.7, '卖出': -0.7, '风险': -0.6,
            '亏损': -0.8, '踩雷': -0.9, '暴跌': -0.9, '利空': -0.7, '破位': -0.6,
            '减仓': -0.5, '轻仓': -0.4, '观望': -0.3, '回调': -0.4, '弱势': -0.6,
            '业绩下滑': -0.7, '不确定': -0.4, '谨慎': -0.4, '跌': -0.6, '危险': -0.7,
            '大亏': -0.8, '亏钱': -0.7, '被套': -0.6, '割肉': -0.7
        }
        
        # 模拟数据开关
        self.use_mock = True
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        分析单条文本情感
        
        Returns:
            {
                'sentiment': 'positive' | 'neutral' | 'negative',
                'score': -1.0 ~ 1.0,
                'keywords': []
            }
        """
        if not text:
            return {'sentiment': 'neutral', 'score': 0, 'keywords': []}
        
        text = text.lower()
        score = 0
        keywords = []
        
        # 计算正面词得分
        for word, weight in self.positive_words.items():
            if word in text:
                score += weight
                keywords.append(word)
        
        # 计算负面词得分
        for word, weight in self.negative_words.items():
            if word in text:
                score += weight
                keywords.append(word)
        
        # 归一化
        score = max(-1.0, min(1.0, score))
        
        if score > 0.2:
            sentiment = 'positive'
        elif score < -0.2:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'sentiment': sentiment,
            'score': round(score, 3),
            'keywords': list(set(keywords))[:5]
        }
    
    def get_xueqiu_comments(self, fund_code: str, limit: int = 20) -> List[Dict]:
        """
        获取雪球基金评论
        
        Args:
            fund_code: 基金代码
            limit: 返回数量
        """
        if self.use_mock:
            return self._get_mock_comments(fund_code, limit)
        
        # 真实API调用
        try:
            url = f"https://xueqiu.com/fund/{fund_code}/comment"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                comments = []
                
                for item in data.get('list', [])[:limit]:
                    text = item.get('text', '')
                    sentiment = self.analyze_sentiment(text)
                    
                    comments.append({
                        'id': item.get('id'),
                        'user': item.get('user', {}).get('nickname', ''),
                        'text': text[:200],
                        'created_at': item.get('created_at'),
                        'sentiment': sentiment['sentiment'],
                        'sentiment_score': sentiment['score']
                    })
                
                return comments
        except Exception as e:
            print(f"获取雪球评论失败: {e}")
        
        return self._get_mock_comments(fund_code, limit)
    
    def _get_mock_comments(self, fund_code: str, limit: int) -> List[Dict]:
        """生成模拟评论数据"""
        mock_comments = [
            {"user": "基民小李", "text": "这只基金最近走势很强，看好后续行情，准备加仓！", "sentiment": "positive"},
            {"user": "理财达人", "text": "经理能力强，业绩稳定增长，值得持有。", "sentiment": "positive"},
            {"user": "股市老王", "text": "回调是机会，准备抄底买入。", "sentiment": "positive"},
            {"user": "新手小白", "text": "今天跌了一点，要不要卖出啊？", "sentiment": "negative"},
            {"user": "价值投资者", "text": "估值偏低，长期持有应该不错。", "sentiment": "positive"},
            {"user": "技术派", "text": "K线形态不太好，可能要回调。", "sentiment": "negative"},
            {"user": "养基专业户", "text": "分红了三次，收益还算稳定。", "sentiment": "positive"},
            {"user": "观望者", "text": "等跌到位再考虑买入。", "sentiment": "neutral"},
            {"user": "趋势交易", "text": "突破关键点位，可能开启新一轮上涨。", "sentiment": "positive"},
            {"user": "风险提示", "text": "市场行情不好，建议谨慎操作。", "sentiment": "negative"},
        ]
        
        import random
        selected = random.sample(mock_comments, min(limit, len(mock_comments)))
        
        comments = []
        for i, c in enumerate(selected):
            sentiment = self.analyze_sentiment(c['text'])
            comments.append({
                'id': 1000 + i,
                'user': c['user'],
                'text': c['text'],
                'created_at': (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat(),
                'sentiment': sentiment['sentiment'],
                'sentiment_score': sentiment['score']
            })
        
        return comments
    
    def get_fund_sentiment_summary(self, fund_code: str) -> Dict:
        """
        获取基金舆情摘要
        
        Returns:
            {
                'fund_code': str,
                'total_comments': int,
                'positive_count': int,
                'negative_count': int,
                'neutral_count': int,
                'overall_sentiment': 'positive' | 'neutral' | 'negative',
                'sentiment_score': float,  # -1 ~ 1
                'hot_keywords': List[str],
                'last_updated': str
            }
        """
        comments = self.get_xueqiu_comments(fund_code, 20)
        
        if not comments:
            return {
                'fund_code': fund_code,
                'error': '无法获取舆情数据'
            }
        
        # 统计情感
        positive = sum(1 for c in comments if c['sentiment'] == 'positive')
        negative = sum(1 for c in comments if c['sentiment'] == 'negative')
        neutral = len(comments) - positive - negative
        
        # 计算平均得分
        avg_score = sum(c['sentiment_score'] for c in comments) / len(comments)
        
        # 提取关键词
        all_keywords = []
        for c in comments:
            sentiment = self.analyze_sentiment(c['text'])
            all_keywords.extend(sentiment.get('keywords', []))
        
        from collections import Counter
        keyword_counts = Counter(all_keywords)
        hot_keywords = [k for k, v in keyword_counts.most_common(5)]
        
        # 综合情感
        if avg_score > 0.2:
            overall = 'positive'
        elif avg_score < -0.2:
            overall = 'negative'
        else:
            overall = 'neutral'
        
        return {
            'fund_code': fund_code,
            'total_comments': len(comments),
            'positive_count': positive,
            'negative_count': negative,
            'neutral_count': neutral,
            'overall_sentiment': overall,
            'sentiment_score': round(avg_score, 3),
            'hot_keywords': hot_keywords,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'comments': comments[:10]  # 返回前10条
        }
    
    def get_market_sentiment(self) -> Dict:
        """
        获取市场整体情绪
        """
        if self.use_mock:
            return self._get_mock_market_sentiment()
        
        # 这里可以接入真实的市场情绪数据
        return self._get_mock_market_sentiment()
    
    def _get_mock_market_sentiment(self) -> Dict:
        """模拟市场情绪"""
        import random
        
        scores = {
            '极好': 0.9,
            '乐观': 0.6,
            '中性': 0.0,
            '谨慎': -0.4,
            '恐慌': -0.8
        }
        
        levels = list(scores.keys())
        level = random.choice(levels)
        
        return {
            'market_sentiment': level,
            'score': scores[level],
            'fear_greed_index': random.randint(20, 80),
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'description': self._get_sentiment_description(level)
        }
    
    def _get_sentiment_description(self, level: str) -> str:
        descriptions = {
            '极好': '市场情绪高涨，投资者信心充足，风险偏好上升',
            '乐观': '市场整体偏多，赚钱效应明显，适量参与',
            '中性': '市场观望情绪浓厚，建议谨慎操作',
            '谨慎': '市场风险较大，建议控制仓位观望',
            '恐慌': '市场恐慌情绪蔓延，建议规避风险'
        }
        return descriptions.get(level, '')


def analyze_fund_sentiment(fund_code: str) -> Dict:
    """快速分析基金舆情"""
    analyzer = SentimentAnalyzer()
    return analyzer.get_fund_sentiment_summary(fund_code)


if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    
    print("=== 基金舆情分析 ===")
    result = analyzer.get_fund_sentiment_summary('161039')
    print(f"总体情感: {result['overall_sentiment']}")
    print(f"情感得分: {result['sentiment_score']}")
    print(f"热门关键词: {result['hot_keywords']}")
    print(f"正面评论: {result['positive_count']}, 负面评论: {result['negative_count']}")
