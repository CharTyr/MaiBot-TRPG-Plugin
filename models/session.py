"""
跑团会话数据模型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class SessionStatus(Enum):
    """会话状态枚举"""
    ACTIVE = "active"      # 进行中
    PAUSED = "paused"      # 暂停
    ENDED = "ended"        # 已结束


class TimeOfDay(Enum):
    """时间状态枚举"""
    DAWN = "dawn"          # 黎明
    DAY = "day"            # 白天
    DUSK = "dusk"          # 黄昏
    NIGHT = "night"        # 夜晚


class Weather(Enum):
    """天气枚举"""
    SUNNY = "sunny"        # 晴朗
    CLOUDY = "cloudy"      # 多云
    RAINY = "rainy"        # 下雨
    STORMY = "stormy"      # 暴风雨
    SNOWY = "snowy"        # 下雪
    FOGGY = "foggy"        # 大雾


@dataclass
class NPCState:
    """NPC 状态"""
    name: str
    status: str = "normal"
    location: str = ""
    attitude: str = "neutral"  # friendly, neutral, hostile
    description: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "location": self.location,
            "attitude": self.attitude,
            "description": self.description,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NPCState":
        return cls(**data)


@dataclass
class HistoryEntry:
    """历史记录条目"""
    entry_type: str  # "dm", "player", "system", "dice"
    content: str
    timestamp: float = field(default_factory=time.time)
    user_id: Optional[str] = None
    character_name: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_type": self.entry_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "character_name": self.character_name,
            "extra_data": self.extra_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        return cls(**data)


@dataclass
class WorldState:
    """世界状态"""
    time_of_day: str = "day"
    weather: str = "sunny"
    location: str = "未知地点"
    location_description: str = ""
    custom_states: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_of_day": self.time_of_day,
            "weather": self.weather,
            "location": self.location,
            "location_description": self.location_description,
            "custom_states": self.custom_states,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldState":
        return cls(**data)

    def get_description(self) -> str:
        """获取世界状态的文字描述"""
        time_desc = {
            "dawn": "黎明时分，天边泛起鱼肚白",
            "day": "阳光明媚的白天",
            "dusk": "黄昏降临，夕阳西下",
            "night": "夜幕降临，星光点点",
        }.get(self.time_of_day, "")
        
        weather_desc = {
            "sunny": "天气晴朗",
            "cloudy": "乌云密布",
            "rainy": "细雨绵绵",
            "stormy": "狂风暴雨",
            "snowy": "大雪纷飞",
            "foggy": "浓雾弥漫",
        }.get(self.weather, "")
        
        return f"{time_desc}，{weather_desc}。当前位置：{self.location}"


@dataclass
class StoryContext:
    """剧情上下文 - 用于保持叙事连贯性"""
    # 当前章节/场景
    current_chapter: str = ""
    current_scene: str = ""
    # 剧情摘要（定期更新）
    story_summary: str = ""
    # 关键事件列表
    key_events: List[str] = field(default_factory=list)
    # 未解决的谜题/线索
    open_threads: List[str] = field(default_factory=list)
    # 已发现的线索
    discovered_clues: List[str] = field(default_factory=list)
    # 剧情张力等级 (0-10)
    tension_level: int = 3
    # 上次生成图片的历史索引
    last_image_history_index: int = 0
    # 上次摘要更新的历史索引
    last_summary_history_index: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_chapter": self.current_chapter,
            "current_scene": self.current_scene,
            "story_summary": self.story_summary,
            "key_events": self.key_events,
            "open_threads": self.open_threads,
            "discovered_clues": self.discovered_clues,
            "tension_level": self.tension_level,
            "last_image_history_index": self.last_image_history_index,
            "last_summary_history_index": self.last_summary_history_index,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoryContext":
        return cls(
            current_chapter=data.get("current_chapter", ""),
            current_scene=data.get("current_scene", ""),
            story_summary=data.get("story_summary", ""),
            key_events=data.get("key_events", []),
            open_threads=data.get("open_threads", []),
            discovered_clues=data.get("discovered_clues", []),
            tension_level=data.get("tension_level", 3),
            last_image_history_index=data.get("last_image_history_index", 0),
            last_summary_history_index=data.get("last_summary_history_index", 0),
        )
    
    def add_key_event(self, event: str):
        """添加关键事件"""
        self.key_events.append(event)
        # 保留最近20个关键事件
        if len(self.key_events) > 20:
            self.key_events = self.key_events[-20:]
    
    def add_clue(self, clue: str):
        """添加发现的线索"""
        if clue not in self.discovered_clues:
            self.discovered_clues.append(clue)
    
    def add_open_thread(self, thread: str):
        """添加未解决的谜题"""
        if thread not in self.open_threads:
            self.open_threads.append(thread)
    
    def resolve_thread(self, thread: str):
        """解决谜题"""
        if thread in self.open_threads:
            self.open_threads.remove(thread)


@dataclass
class TRPGSession:
    """跑团会话"""
    stream_id: str
    status: str = "active"
    world_name: str = "通用奇幻世界"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    world_state: WorldState = field(default_factory=WorldState)
    history: List[HistoryEntry] = field(default_factory=list)
    npcs: Dict[str, NPCState] = field(default_factory=dict)
    lore: List[str] = field(default_factory=list)
    player_ids: List[str] = field(default_factory=list)
    # 新增：剧情上下文
    story_context: StoryContext = field(default_factory=StoryContext)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stream_id": self.stream_id,
            "status": self.status,
            "world_name": self.world_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "world_state": self.world_state.to_dict(),
            "history": [h.to_dict() for h in self.history],
            "npcs": {k: v.to_dict() for k, v in self.npcs.items()},
            "lore": self.lore,
            "player_ids": self.player_ids,
            "story_context": self.story_context.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TRPGSession":
        world_state = WorldState.from_dict(data.get("world_state", {}))
        history = [HistoryEntry.from_dict(h) for h in data.get("history", [])]
        npcs = {k: NPCState.from_dict(v) for k, v in data.get("npcs", {}).items()}
        story_context = StoryContext.from_dict(data.get("story_context", {}))
        
        return cls(
            stream_id=data["stream_id"],
            status=data.get("status", "active"),
            world_name=data.get("world_name", "通用奇幻世界"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            world_state=world_state,
            history=history,
            npcs=npcs,
            lore=data.get("lore", []),
            player_ids=data.get("player_ids", []),
            story_context=story_context,
        )

    def add_history(self, entry_type: str, content: str, user_id: str = None, 
                    character_name: str = None, extra_data: Dict = None):
        """添加历史记录"""
        entry = HistoryEntry(
            entry_type=entry_type,
            content=content,
            user_id=user_id,
            character_name=character_name,
            extra_data=extra_data or {},
        )
        self.history.append(entry)
        self.updated_at = time.time()

    def get_recent_history(self, count: int = 10) -> List[HistoryEntry]:
        """获取最近的历史记录"""
        return self.history[-count:] if self.history else []

    def add_npc(self, name: str, **kwargs) -> NPCState:
        """添加 NPC"""
        npc = NPCState(name=name, **kwargs)
        self.npcs[name] = npc
        self.updated_at = time.time()
        return npc

    def add_player(self, user_id: str):
        """添加玩家到会话"""
        if user_id not in self.player_ids:
            self.player_ids.append(user_id)
            self.updated_at = time.time()

    def remove_player(self, user_id: str):
        """从会话移除玩家"""
        if user_id in self.player_ids:
            self.player_ids.remove(user_id)
            self.updated_at = time.time()

    def is_active(self) -> bool:
        """检查会话是否活跃"""
        return self.status == "active"

    def trim_history(self, max_length: int) -> int:
        """
        修剪历史记录，避免存档无限增长。

        Returns:
            实际删除的条目数
        """
        if max_length <= 0:
            return 0
        if len(self.history) <= max_length:
            return 0

        removed = len(self.history) - max_length
        self.history = self.history[-max_length:]

        # 同步修正索引类字段，避免修剪后逻辑异常
        ctx = self.story_context
        ctx.last_image_history_index = max(0, ctx.last_image_history_index - removed)
        ctx.last_summary_history_index = max(0, ctx.last_summary_history_index - removed)

        self.updated_at = time.time()
        return removed
