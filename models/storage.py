"""
数据存储管理器
"""

import json
import os
import asyncio
from pathlib import Path
from typing import Dict, Optional, List, Any
from .session import TRPGSession
from .player import Player


class StorageManager:
    """数据存储管理器 - 负责所有数据的持久化"""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.sessions_dir = self.data_dir / "sessions"
        self.players_dir = self.data_dir / "players"
        self.lore_dir = self.data_dir / "lore"
        self.config_dir = self.data_dir / "config"
        
        # 内存缓存
        self._sessions: Dict[str, TRPGSession] = {}
        self._players: Dict[str, Dict[str, Player]] = {}  # {stream_id: {user_id: Player}}
        self._enabled_groups: List[str] = []
        
        # 确保目录存在
        self._ensure_directories()
        
        # 文件锁
        self._lock = asyncio.Lock()

    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        for directory in [self.sessions_dir, self.players_dir, self.lore_dir, self.config_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """初始化存储管理器，加载所有数据"""
        async with self._lock:
            await self._load_enabled_groups()
            await self._load_all_sessions()
            await self._load_all_players()

    async def _load_enabled_groups(self):
        """加载启用的群组列表"""
        config_file = self.config_dir / "enabled_groups.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    self._enabled_groups = json.load(f)
            except Exception:
                self._enabled_groups = []

    async def _save_enabled_groups(self):
        """保存启用的群组列表"""
        config_file = self.config_dir / "enabled_groups.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(self._enabled_groups, f, ensure_ascii=False, indent=2)

    async def _load_all_sessions(self):
        """加载所有会话"""
        if not self.sessions_dir.exists():
            return
        
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                session = TRPGSession.from_dict(data)
                if session.status != "ended":  # 只加载未结束的会话
                    self._sessions[session.stream_id] = session
            except Exception as e:
                print(f"加载会话文件失败 {session_file}: {e}")

    async def _load_all_players(self):
        """加载所有玩家数据"""
        if not self.players_dir.exists():
            return
        
        for stream_dir in self.players_dir.iterdir():
            if stream_dir.is_dir():
                stream_id = stream_dir.name
                self._players[stream_id] = {}
                
                for player_file in stream_dir.glob("*.json"):
                    try:
                        with open(player_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        player = Player.from_dict(data)
                        self._players[stream_id][player.user_id] = player
                    except Exception as e:
                        print(f"加载玩家文件失败 {player_file}: {e}")

    # ==================== 会话操作 ====================

    async def get_session(self, stream_id: str) -> Optional[TRPGSession]:
        """获取会话"""
        return self._sessions.get(stream_id)

    async def create_session(self, stream_id: str, world_name: str = "通用奇幻世界") -> TRPGSession:
        """创建新会话"""
        session = TRPGSession(stream_id=stream_id, world_name=world_name)
        self._sessions[stream_id] = session
        await self.save_session(session)
        
        # 自动启用该群组
        if stream_id not in self._enabled_groups:
            self._enabled_groups.append(stream_id)
            await self._save_enabled_groups()
        
        return session

    async def save_session(self, session: TRPGSession):
        """保存会话"""
        async with self._lock:
            session_file = self.sessions_dir / f"{session.stream_id}.json"
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

    async def end_session(self, stream_id: str) -> bool:
        """结束会话"""
        session = self._sessions.get(stream_id)
        if session:
            session.status = "ended"
            await self.save_session(session)
            del self._sessions[stream_id]
            return True
        return False

    async def get_active_sessions(self) -> List[TRPGSession]:
        """获取所有活跃会话"""
        return [s for s in self._sessions.values() if s.is_active()]

    # ==================== 玩家操作 ====================

    async def get_player(self, stream_id: str, user_id: str) -> Optional[Player]:
        """获取玩家"""
        if stream_id in self._players:
            return self._players[stream_id].get(user_id)
        return None

    async def create_player(self, stream_id: str, user_id: str, character_name: str = "无名冒险者") -> Player:
        """创建新玩家"""
        if stream_id not in self._players:
            self._players[stream_id] = {}
            # 确保玩家目录存在
            (self.players_dir / stream_id).mkdir(parents=True, exist_ok=True)
        
        player = Player(user_id=user_id, stream_id=stream_id, character_name=character_name)
        self._players[stream_id][user_id] = player
        await self.save_player(player)
        
        # 将玩家添加到会话
        session = await self.get_session(stream_id)
        if session:
            session.add_player(user_id)
            await self.save_session(session)
        
        return player

    async def save_player(self, player: Player):
        """保存玩家数据"""
        async with self._lock:
            player_dir = self.players_dir / player.stream_id
            player_dir.mkdir(parents=True, exist_ok=True)
            player_file = player_dir / f"{player.user_id}.json"
            with open(player_file, "w", encoding="utf-8") as f:
                json.dump(player.to_dict(), f, ensure_ascii=False, indent=2)

    async def delete_player(self, stream_id: str, user_id: str) -> bool:
        """删除玩家"""
        if stream_id in self._players and user_id in self._players[stream_id]:
            del self._players[stream_id][user_id]
            
            # 删除文件
            player_file = self.players_dir / stream_id / f"{user_id}.json"
            if player_file.exists():
                player_file.unlink()
            
            # 从会话中移除
            session = await self.get_session(stream_id)
            if session:
                session.remove_player(user_id)
                await self.save_session(session)
            
            return True
        return False

    async def get_players_in_session(self, stream_id: str) -> List[Player]:
        """获取会话中的所有玩家"""
        if stream_id in self._players:
            return list(self._players[stream_id].values())
        return []

    # ==================== 群组管理 ====================

    def is_group_enabled(self, stream_id: str) -> bool:
        """检查群组是否启用跑团"""
        return stream_id in self._enabled_groups

    async def enable_group(self, stream_id: str):
        """启用群组"""
        if stream_id not in self._enabled_groups:
            self._enabled_groups.append(stream_id)
            await self._save_enabled_groups()

    async def disable_group(self, stream_id: str):
        """禁用群组"""
        if stream_id in self._enabled_groups:
            self._enabled_groups.remove(stream_id)
            await self._save_enabled_groups()

    def get_enabled_groups(self) -> List[str]:
        """获取所有启用的群组"""
        return self._enabled_groups.copy()

    # ==================== 世界观设定 ====================

    async def get_lore(self, stream_id: str) -> List[str]:
        """获取世界观设定"""
        session = await self.get_session(stream_id)
        return session.lore if session else []

    async def add_lore(self, stream_id: str, lore_entry: str) -> bool:
        """添加世界观设定"""
        session = await self.get_session(stream_id)
        if session:
            session.lore.append(lore_entry)
            await self.save_session(session)
            return True
        return False

    async def search_lore(self, stream_id: str, keyword: str) -> List[str]:
        """搜索世界观设定"""
        lore = await self.get_lore(stream_id)
        return [entry for entry in lore if keyword.lower() in entry.lower()]

    # ==================== 工具方法 ====================

    async def save_all(self):
        """保存所有数据"""
        for session in self._sessions.values():
            await self.save_session(session)
        
        for stream_players in self._players.values():
            for player in stream_players.values():
                await self.save_player(player)
        
        await self._save_enabled_groups()

    def has_active_session(self, stream_id: str) -> bool:
        """检查是否有活跃会话"""
        session = self._sessions.get(stream_id)
        return session is not None and session.is_active()
