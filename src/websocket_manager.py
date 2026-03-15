# -*- coding: utf-8 -*-
"""
WebSocket管理器 - 实时推送基金数据
"""
import asyncio
import json
from typing import Dict, List, Set
from datetime import datetime
from fastapi import WebSocket
import random


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃的WebSocket连接
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # 基金订阅列表
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """客户端连接"""
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
        self.subscriptions[websocket] = set()
        print(f"客户端 {client_id} 连接, 当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, client_id: str):
        """客户端断开"""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        print(f"客户端 {client_id} 断开, 当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"发送消息失败: {e}")
    
    async def broadcast(self, message: dict, fund_codes: List[str] = None):
        """广播消息"""
        if fund_codes is None:
            # 广播给所有连接
            for client_id, connections in self.active_connections.items():
                for connection in connections:
                    await self.send_personal_message(message, connection)
        else:
            # 只广播给订阅了指定基金的连接
            for websocket, codes in self.subscriptions.items():
                if any(code in fund_codes for code in codes):
                    await self.send_personal_message(message, websocket)
    
    def subscribe(self, websocket: WebSocket, fund_codes: List[str]):
        """订阅基金"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].update(fund_codes)
    
    def unsubscribe(self, websocket: WebSocket, fund_codes: List[str]):
        """取消订阅"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].difference_update(fund_codes)


# 全局连接管理器
manager = ConnectionManager()


async def start_fund_price_stream(manager: ConnectionManager):
    """定时推送基金价格更新"""
    while True:
        await asyncio.sleep(5)  # 每5秒推送一次
        
        # 模拟基金价格更新
        funds = ['161039', '161725', '005827', '110011', '000001']
        
        for fund_code in funds:
            # 模拟价格变动
            change = random.uniform(-0.5, 0.5)
            message = {
                'type': 'price_update',
                'fund_code': fund_code,
                'price': round(1.5 + change, 4),
                'change': round(change, 4),
                'change_pct': round(change / 1.5 * 100, 2),
                'timestamp': datetime.now().isoformat()
            }
            
            # 广播给订阅了该基金的客户端
            await manager.broadcast(message, [fund_code])


async def start_market_summary_stream(manager: ConnectionManager):
    """定时推送市场摘要"""
    while True:
        await asyncio.sleep(30)  # 每30秒推送一次
        
        # 模拟市场数据
        message = {
            'type': 'market_summary',
            'data': {
                'shanghai_index': round(3400 + random.uniform(-20, 20), 2),
                'shenzhen_index': round(11000 + random.uniform(-50, 50), 2),
                'turnover': round(random.uniform(8000, 12000), 2),
                'sentiment': random.choice(['乐观', '谨慎', '观望']),
                'fear_greed_index': random.randint(30, 70)
            },
            'timestamp': datetime.now().isoformat()
        }
        
        await manager.broadcast(message)


class PortfolioManager:
    """基金组合管理器"""
    
    def __init__(self):
        # 内存存储组合 (生产环境应使用数据库)
        self.portfolios: Dict[str, List[dict]] = {}
    
    def create_portfolio(self, user_id: str, name: str) -> dict:
        """创建组合"""
        if user_id not in self.portfolios:
            self.portfolios[user_id] = []
        
        portfolio = {
            'id': len(self.portfolios[user_id]) + 1,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'holdings': [],
            'total_value': 0,
            'total_cost': 0,
            'total_gain': 0,
            'total_gain_pct': 0
        }
        
        self.portfolios[user_id].append(portfolio)
        return portfolio
    
    def add_fund(self, user_id: str, portfolio_id: int, fund_code: str, 
                 shares: float, cost: float) -> dict:
        """添加基金到组合"""
        if user_id not in self.portfolios:
            return {'error': '组合不存在'}
        
        portfolio = next((p for p in self.portfolios[user_id] if p['id'] == portfolio_id), None)
        if not portfolio:
            return {'error': '组合不存在'}
        
        # 添加持仓
        holding = {
            'fund_code': fund_code,
            'shares': shares,
            'cost': cost,
            'avg_cost': cost / shares if shares > 0 else 0,
            'added_at': datetime.now().isoformat()
        }
        
        portfolio['holdings'].append(holding)
        self._recalculate_portfolio(user_id, portfolio_id)
        
        return holding
    
    def remove_fund(self, user_id: str, portfolio_id: int, fund_code: str) -> bool:
        """从组合移除基金"""
        if user_id not in self.portfolios:
            return False
        
        portfolio = next((p for p in self.portfolios[user_id] if p['id'] == portfolio_id), None)
        if not portfolio:
            return False
        
        portfolio['holdings'] = [h for h in portfolio['holdings'] if h['fund_code'] != fund_code]
        self._recalculate_portfolio(user_id, portfolio_id)
        
        return True
    
    def get_portfolio(self, user_id: str, portfolio_id: int = None) -> dict:
        """获取组合"""
        if user_id not in self.portfolios:
            return None
        
        if portfolio_id is None:
            return self.portfolios[user_id]
        
        return next((p for p in self.portfolios[user_id] if p['id'] == portfolio_id), None)
    
    def _recalculate_portfolio(self, user_id: str, portfolio_id: int):
        """重新计算组合价值"""
        from src.data.fund_fetcher import FundDataFetcher
        
        fetcher = FundDataFetcher()
        portfolio = next((p for p in self.portfolios[user_id] if p['id'] == portfolio_id), None)
        
        if not portfolio:
            return
        
        total_value = 0
        total_cost = 0
        
        for holding in portfolio['holdings']:
            # 获取当前净值
            info = fetcher.get_fund_info(holding['fund_code'])
            current_nav = info.get('net_value', 1)
            
            # 更新持仓信息
            holding['current_nav'] = current_nav
            holding['current_value'] = current_nav * holding['shares']
            holding['gain'] = holding['current_value'] - holding['cost']
            holding['gain_pct'] = (holding['gain'] / holding['cost'] * 100) if holding['cost'] > 0 else 0
            
            total_value += holding['current_value']
            total_cost += holding['cost']
        
        portfolio['total_value'] = total_value
        portfolio['total_cost'] = total_cost
        portfolio['total_gain'] = total_value - total_cost
        portfolio['total_gain_pct'] = (portfolio['total_gain'] / total_cost * 100) if total_cost > 0 else 0


# 全局组合管理器
portfolio_manager = PortfolioManager()
