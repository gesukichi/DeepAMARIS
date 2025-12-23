"""
web.routers package - HTTPルーター集約

外部委託対応: シンプルで明確なAPI構造
"""

from .history_router import history_bp, init_history_router

__all__ = ['history_bp', 'init_history_router']
