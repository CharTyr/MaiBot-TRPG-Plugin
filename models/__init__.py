"""
TRPG DM 插件数据模型
"""

from .session import TRPGSession, WorldState, NPCState, HistoryEntry
from .player import Player, PlayerAttributes, InventoryItem
from .storage import StorageManager

__all__ = [
    "TRPGSession",
    "WorldState", 
    "NPCState",
    "HistoryEntry",
    "Player",
    "PlayerAttributes",
    "InventoryItem",
    "StorageManager",
]
