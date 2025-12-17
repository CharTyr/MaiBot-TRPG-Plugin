"""
数据存储管理器
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
from src.common.logger import get_logger
from .session import TRPGSession
from .player import Player

logger = get_logger("trpg_storage")


class StorageManager:
    """数据存储管理器 - 负责所有数据的持久化"""

    def __init__(self, data_dir: str, config: Dict[str, Any] = None):
        self.data_dir = Path(data_dir)
        self.sessions_dir = self.data_dir / "sessions"
        self.players_dir = self.data_dir / "players"
        self.lore_dir = self.data_dir / "lore"
        self.config_dir = self.data_dir / "config"
        self.slots_dir = self.data_dir / "save_slots"
        
        # 配置
        self._config = config or {}
        self._max_slots = self._config.get("save_slots", {}).get("max_slots", 3)
        self._allowed_groups = self._config.get("plugin", {}).get("allowed_groups", [])
        
        # 内存缓存
        self._sessions: Dict[str, TRPGSession] = {}
        self._players: Dict[str, Dict[str, Player]] = {}
        self._enabled_groups: List[str] = []
        self._pending_joins: Dict[str, Dict[str, str]] = {}  # {stream_id: {user_id: character_name}}
        
        # 确保目录存在
        self._ensure_directories()
        
        # 文件锁
        self._lock = asyncio.Lock()

    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        for directory in [self.sessions_dir, self.players_dir, self.lore_dir, 
                          self.config_dir, self.slots_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self._config = config
        self._max_slots = config.get("save_slots", {}).get("max_slots", 3)
        self._allowed_groups = config.get("plugin", {}).get("allowed_groups", [])

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
                if session.status != "ended":
                    self._sessions[session.stream_id] = session
            except Exception as e:
                logger.warning(f"[Storage] 加载会话文件失败 {session_file}: {e}")

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
                        logger.warning(f"[Storage] 加载玩家文件失败 {player_file}: {e}")

    # ==================== 群组权限检查 ====================

    def is_group_allowed(self, stream_id: str) -> bool:
        """检查群组是否在允许列表中"""
        if not self._allowed_groups:
            return True  # 空列表表示允许所有群组
        return stream_id in self._allowed_groups

    def is_group_enabled(self, stream_id: str) -> bool:
        """检查群组是否启用跑团"""
        return stream_id in self._enabled_groups

    async def enable_group(self, stream_id: str) -> bool:
        """启用群组"""
        if not self.is_group_allowed(stream_id):
            return False
        if stream_id not in self._enabled_groups:
            self._enabled_groups.append(stream_id)
            await self._save_enabled_groups()
        return True

    async def disable_group(self, stream_id: str):
        """禁用群组"""
        if stream_id in self._enabled_groups:
            self._enabled_groups.remove(stream_id)
            await self._save_enabled_groups()

    def get_enabled_groups(self) -> List[str]:
        """获取所有启用的群组"""
        return self._enabled_groups.copy()

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
        await self.enable_group(stream_id)
        
        return session

    async def save_session(self, session: TRPGSession):
        """保存会话"""
        async with self._lock:
            max_history = self._config.get("session", {}).get("max_history_length", 0)
            if isinstance(max_history, int) and max_history > 0:
                session.trim_history(max_history)
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

    def has_active_session(self, stream_id: str) -> bool:
        """检查是否有活跃会话"""
        session = self._sessions.get(stream_id)
        return session is not None and session.is_active()

    # ==================== 存档插槽操作 ====================

    def _get_slot_dir(self, stream_id: str) -> Path:
        """获取群组的存档目录"""
        # 将 stream_id 中的特殊字符替换为下划线
        safe_id = stream_id.replace(":", "_").replace("/", "_")
        slot_dir = self.slots_dir / safe_id
        slot_dir.mkdir(parents=True, exist_ok=True)
        return slot_dir

    async def list_save_slots(self, stream_id: str) -> List[Dict[str, Any]]:
        """列出群组的所有存档插槽"""
        slot_dir = self._get_slot_dir(stream_id)
        slots = []
        
        for i in range(1, self._max_slots + 1):
            slot_file = slot_dir / f"slot_{i}.json"
            if slot_file.exists():
                try:
                    with open(slot_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    slots.append({
                        "slot": i,
                        "world_name": data.get("session", {}).get("world_name", "未知"),
                        "created_at": data.get("saved_at", "未知"),
                        "player_count": len(data.get("players", [])),
                        "exists": True,
                    })
                except Exception:
                    slots.append({"slot": i, "exists": False, "error": True})
            else:
                slots.append({"slot": i, "exists": False})
        
        return slots

    async def save_to_slot(self, stream_id: str, slot_number: int) -> Tuple[bool, str]:
        """保存当前会话到指定插槽"""
        if slot_number < 1 or slot_number > self._max_slots:
            return False, f"插槽号必须在 1-{self._max_slots} 之间"
        
        session = await self.get_session(stream_id)
        if not session:
            return False, "当前没有进行中的跑团会话"
        
        slot_dir = self._get_slot_dir(stream_id)
        slot_file = slot_dir / f"slot_{slot_number}.json"
        
        # 检查是否允许覆盖
        allow_overwrite = self._config.get("save_slots", {}).get("allow_overwrite", True)
        if slot_file.exists() and not allow_overwrite:
            return False, f"插槽 {slot_number} 已有存档，不允许覆盖"
        
        # 收集玩家数据
        players_data = []
        if stream_id in self._players:
            for player in self._players[stream_id].values():
                players_data.append(player.to_dict())
        
        # 保存数据
        import time
        save_data = {
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "session": session.to_dict(),
            "players": players_data,
        }
        
        async with self._lock:
            with open(slot_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        return True, f"已保存到插槽 {slot_number}"

    async def load_from_slot(self, stream_id: str, slot_number: int) -> Tuple[bool, str]:
        """从指定插槽加载存档"""
        if slot_number < 1 or slot_number > self._max_slots:
            return False, f"插槽号必须在 1-{self._max_slots} 之间"
        
        # 检查是否有活跃会话
        if self.has_active_session(stream_id):
            return False, "当前已有进行中的跑团会话，请先结束或保存"
        
        slot_dir = self._get_slot_dir(stream_id)
        slot_file = slot_dir / f"slot_{slot_number}.json"
        
        if not slot_file.exists():
            return False, f"插槽 {slot_number} 没有存档"
        
        try:
            with open(slot_file, "r", encoding="utf-8") as f:
                save_data = json.load(f)
            
            # 恢复会话
            session_data = save_data.get("session", {})
            session_data["stream_id"] = stream_id  # 确保使用当前群组ID
            session_data["status"] = "active"  # 恢复为活跃状态
            session = TRPGSession.from_dict(session_data)
            self._sessions[stream_id] = session
            await self.save_session(session)
            
            # 恢复玩家
            self._players[stream_id] = {}
            for player_data in save_data.get("players", []):
                player_data["stream_id"] = stream_id
                player = Player.from_dict(player_data)
                self._players[stream_id][player.user_id] = player
                await self.save_player(player)
            
            # 启用群组
            await self.enable_group(stream_id)
            
            return True, f"已从插槽 {slot_number} 加载存档: {session.world_name}"
            
        except Exception as e:
            return False, f"加载存档失败: {e}"

    async def delete_slot(self, stream_id: str, slot_number: int) -> Tuple[bool, str]:
        """删除指定插槽的存档"""
        if slot_number < 1 or slot_number > self._max_slots:
            return False, f"插槽号必须在 1-{self._max_slots} 之间"
        
        slot_dir = self._get_slot_dir(stream_id)
        slot_file = slot_dir / f"slot_{slot_number}.json"
        
        if not slot_file.exists():
            return False, f"插槽 {slot_number} 没有存档"
        
        try:
            slot_file.unlink()
            return True, f"已删除插槽 {slot_number} 的存档"
        except Exception as e:
            return False, f"删除失败: {e}"

    # ==================== 中途加入确认 ====================

    def add_pending_join(self, stream_id: str, user_id: str, character_name: str):
        """添加待确认的加入请求"""
        if stream_id not in self._pending_joins:
            self._pending_joins[stream_id] = {}
        self._pending_joins[stream_id][user_id] = character_name

    def get_pending_join(self, stream_id: str, user_id: str) -> Optional[str]:
        """获取待确认的加入请求"""
        if stream_id in self._pending_joins:
            return self._pending_joins[stream_id].get(user_id)
        return None

    def remove_pending_join(self, stream_id: str, user_id: str) -> Optional[str]:
        """移除并返回待确认的加入请求"""
        if stream_id in self._pending_joins:
            return self._pending_joins[stream_id].pop(user_id, None)
        return None

    def get_all_pending_joins(self, stream_id: str) -> Dict[str, str]:
        """获取群组所有待确认的加入请求"""
        return self._pending_joins.get(stream_id, {}).copy()

    # ==================== 玩家操作 ====================

    async def get_player(self, stream_id: str, user_id: str) -> Optional[Player]:
        """获取玩家"""
        if stream_id in self._players:
            return self._players[stream_id].get(user_id)
        return None

    async def create_player(
        self, 
        stream_id: str, 
        user_id: str, 
        character_name: str = "无名冒险者",
        free_points: int = None,
    ) -> Player:
        """
        创建新玩家
        
        Args:
            stream_id: 会话ID
            user_id: 用户ID
            character_name: 角色名
            free_points: 自由加点点数（None则使用配置默认值）
        """
        if stream_id not in self._players:
            self._players[stream_id] = {}
            (self.players_dir / stream_id).mkdir(parents=True, exist_ok=True)
        
        # 获取配置的加点点数
        player_config = self._config.get("player", {})
        default_free_points = player_config.get("free_points", 30)
        base_attr = player_config.get("base_attribute", 8)
        default_max_hp = player_config.get("default_max_hp", 20)
        default_max_mp = player_config.get("default_max_mp", 10)
        
        # 创建基础属性（所有属性从基础值开始）
        from .player import PlayerAttributes
        base_attributes = PlayerAttributes(
            strength=base_attr,
            dexterity=base_attr,
            constitution=base_attr,
            intelligence=base_attr,
            wisdom=base_attr,
            charisma=base_attr,
        )
        
        player = Player(
            user_id=user_id, 
            stream_id=stream_id, 
            character_name=character_name,
            attributes=base_attributes,
            hp_current=default_max_hp,
            hp_max=default_max_hp,
            mp_current=default_max_mp,
            mp_max=default_max_mp,
            free_points=free_points if free_points is not None else default_free_points,
            points_allocated={},
            character_locked=False,
        )
        self._players[stream_id][user_id] = player
        await self.save_player(player)
        
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
            
            player_file = self.players_dir / stream_id / f"{user_id}.json"
            if player_file.exists():
                player_file.unlink()
            
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
