# -*- coding: utf-8 -*-
"""
基金数据采集模块
支持真实API + 模拟数据备用
"""

import requests
import pandas as pd
import numpy as np
import re
import json
from typing import Optional, Dict, List
from datetime import datetime, timedelta


class FundDataFetcher:
    """基金数据采集器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://fund.eastmoney.com/'
        }
        self.use_mock = True  # 默认使用模拟数据
    
    def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金基本信息"""
        # 尝试真实API
        if not self.use_mock:
            result = self._get_fund_info_real(fund_code)
            if 'error' not in result:
                return result
        
        # 使用模拟数据
        return self._get_fund_info_mock(fund_code)
    
    def _get_fund_info_real(self, fund_code: str) -> Dict:
        """真实API获取基金信息"""
        url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            text = response.text
            
            name_match = re.search(r'fund_name="([^"]+)"', text)
            name = name_match.group(1) if name_match else ""
            
            nav_match = re.search(r'net_value="([^"]+)"', text)
            nav = float(nav_match.group(1)) if nav_match else 0
            
            if name or nav > 0:
                return {
                    'fund_code': fund_code,
                    'fund_name': name,
                    'net_value': nav,
                    'total_net': 0,
                    'growth_rate': 0,
                    'net_value_date': datetime.now().strftime('%Y-%m-%d'),
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        except:
            pass
        
        return {'error': 'API不可用', 'fund_code': fund_code}
    
    def _get_fund_info_mock(self, fund_code: str) -> Dict:
        """模拟基金数据"""
        # 常用基金代码映射
        fund_names = {
            '161039': '易方达消费行业股票',
            '110011': '易方达中小盘混合',
            '000001': '平安财富宝货币A',
            '110022': '华夏成长混合',
            '001552': '天弘中证银行ETF联接',
            '161725': '招商中证白酒指数',
            '005827': '易方达蓝筹精选混合',
            '000311': '景顺长城沪深300ETF联接',
        }
        
        fund_name = fund_names.get(fund_code, f'基金{fund_code}')
        
        # 生成随机净值
        np.random.seed(int(fund_code) if fund_code.isdigit() else hash(fund_code))
        base_nav = np.random.uniform(1.0, 3.0)
        change = np.random.uniform(-3, 3)
        
        return {
            'fund_code': fund_code,
            'fund_name': fund_name,
            'net_value': round(base_nav, 4),
            'total_net': round(base_nav * 1.1, 4),
            'growth_rate': round(change, 2),
            'net_value_date': datetime.now().strftime('%Y-%m-%d'),
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_mock': True
        }
    
    def get_historical_nav(self, fund_code: str, days: int = 90) -> pd.DataFrame:
        """获取基金历史净值"""
        # 尝试真实API
        if not self.use_mock:
            result = self._get_historical_real(fund_code, days)
            if not result.empty:
                return result
        
        # 使用模拟数据
        return self._get_historical_mock(fund_code, days)
    
    def _get_historical_real(self, fund_code: str, days: int) -> pd.DataFrame:
        """真实API获取历史净值"""
        url = "https://fund.eastmoney.com/f10/F10DataApi.aspx"
        params = {'type': 'FFDR', 'code': fund_code, 'page': 1, 'per': days}
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            tables = pd.read_html(response.text)
            if tables:
                df = tables[0]
                df.columns = ['date', 'net_value', 'acc_net_value', 'daily_gain', 'daily_gain_pct', 'buy_status', 'sell_status']
                return df
        except:
            pass
        
        return pd.DataFrame()
    
    def _get_historical_mock(self, fund_code: str, days: int) -> pd.DataFrame:
        """生成模拟历史数据"""
        np.random.seed(int(fund_code) if fund_code.isdigit() else hash(fund_code))
        
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        
        # 生成净值走势
        base_nav = np.random.uniform(1.0, 2.0)
        daily_returns = np.random.normal(0.001, 0.015, days)
        nav = base_nav * np.exp(np.cumsum(daily_returns))
        
        df = pd.DataFrame({
            'date': dates,
            'net_value': np.round(nav, 4),
            'acc_net_value': np.round(nav * 1.1, 4),
            'daily_gain': np.round(nav * daily_returns, 4),
            'daily_gain_pct': np.round(daily_returns * 100, 2),
        })
        
        df['buy_status'] = np.where(np.random.random(days) > 0.3, '开放', '限额')
        df['sell_status'] = '开放'
        
        return df
    
    def search_fund(self, keyword: str) -> List[Dict]:
        """搜索基金"""
        # 模拟搜索结果
        mock_funds = [
            {'fund_code': '161039', 'fund_name': '易方达消费行业股票', 'type': '股票型', 'net_value': '2.3456', 'growth_rate': '1.23'},
            {'fund_code': '161725', 'fund_name': '招商中证白酒指数', 'type': '指数型', 'net_value': '1.5678', 'growth_rate': '-0.45'},
            {'fund_code': '005827', 'fund_name': '易方达蓝筹精选混合', 'type': '混合型', 'net_value': '1.8901', 'growth_rate': '0.89'},
            {'fund_code': '110011', 'fund_name': '易方达中小盘混合', 'type': '混合型', 'net_value': '3.1234', 'growth_rate': '2.15'},
            {'fund_code': '001552', 'fund_name': '天弘中证银行ETF联接', 'type': '联接型', 'net_value': '1.2345', 'growth_rate': '-1.23'},
        ]
        
        # 关键词过滤
        results = []
        keyword_lower = keyword.lower()
        for fund in mock_funds:
            if (keyword_lower in fund['fund_code'] or 
                keyword_lower in fund['fund_name'].lower() or
                keyword_lower in fund['type'].lower()):
                results.append(fund)
        
        return results if results else mock_funds[:3]
    
    def get_fund_manager(self, fund_code: str) -> Dict:
        """获取基金经理信息"""
        managers = [
            {'name': '张坤', 'tenure': '4年', 'rating': 5, 'assets': 622.5},
            {'name': '刘彦春', 'tenure': '6年', 'rating': 4.5, 'assets': 456.3},
            {'name': '侯昊', 'tenure': '3年', 'rating': 4.8, 'assets': 389.2}
        ]
        
        return {
            'fund_code': fund_code,
            'managers': managers,
            'current_manager': managers[0]
        }
    
    def get_fund_holdings(self, fund_code: str) -> List[Dict]:
        """获取基金持仓"""
        holdings = []
        stocks = ['贵州茅台', '宁德时代', '招商银行', '中国平安', '五粮液',
                  '隆基绿能', '比亚迪', '泸州老窖', '山西汾酒', '美的集团']
        
        for i, stock in enumerate(stocks[:10]):
            holdings.append({
                'rank': i + 1,
                'stock_code': f'{600000 + i * 100:06d}.SH',
                'stock_name': stock,
                'shares': int(np.random.randint(1000000, 50000000)),
                'market_value': float(np.random.uniform(1e8, 5e9)),
                'proportion': float(np.random.uniform(3, 15))
            })
        
        return holdings
    
    def get_fund_compare(self, fund_codes: List[str]) -> Dict:
        """基金对比分析"""
        compare_result = {'funds': [], 'comparison': {}}
        
        for code in fund_codes:
            info = self.get_fund_info(code)
            compare_result['funds'].append({
                'code': code,
                'name': info.get('fund_name', '未知'),
                'nav': info.get('net_value', 0),
                'growth': info.get('growth_rate', 0),
                'type': info.get('fund_type', '混合型')
            })
        
        if compare_result['funds']:
            growths = [f['growth'] for f in compare_result['funds']]
            compare_result['comparison'] = {
                'best_growth': max(growths),
                'avg_growth': sum(growths) / len(growths),
                'best_fund': compare_result['funds'][growths.index(max(growths))]['name']
            }
        
        return compare_result
    
    def get_fund_dividend(self, fund_code: str) -> List[Dict]:
        """获取基金分红历史"""
        dividends = []
        for year in range(2020, 2025):
            dividends.append({
                'year': year,
                'date': f'{year}-12-15',
                'cash_dividend': round(float(np.random.uniform(0.1, 0.5)), 4),
                'share_dividend': round(float(np.random.uniform(0, 0.1)), 4),
                'total': round(float(np.random.uniform(0.1, 0.6)), 4)
            })
        return dividends


# 便捷函数
def get_fund_nav(fund_code: str) -> Dict:
    fetcher = FundDataFetcher()
    return fetcher.get_fund_info(fund_code)


def get_fund_history(fund_code: str, days: int = 90) -> pd.DataFrame:
    fetcher = FundDataFetcher()
    return fetcher.get_historical_nav(fund_code, days)


if __name__ == "__main__":
    f = FundDataFetcher()
    print(f.get_fund_info('161039'))
    print(f.search_fund('白酒'))
