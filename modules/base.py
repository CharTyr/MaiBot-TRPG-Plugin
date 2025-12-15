"""
模组基类定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class NPCTemplate:
    """NPC 模板"""
    name: str
    description: str
    location: str = ""
    attitude: str = "neutral"  # friendly, neutral, hostile
    dialogue_style: str = ""   # NPC 说话风格提示
    secrets: List[str] = field(default_factory=list)  # NPC 知道的秘密
    inventory: List[str] = field(default_factory=list)  # NPC 携带的物品


@dataclass
class LocationTemplate:
    """地点模板"""
    name: str
    description: str
    connections: List[str] = field(default_factory=list)  # 连接的其他地点
    items: List[str] = field(default_factory=list)  # 地点中的物品
    npcs: List[str] = field(default_factory=list)  # 地点中的 NPC
    events: List[str] = field(default_factory=list)  # 可能触发的事件
    hidden_info: str = ""  # 隐藏信息（需要调查才能发现）


@dataclass
class EventTemplate:
    """事件模板"""
    name: str
    description: str
    trigger: str = ""  # 触发条件
    consequences: List[str] = field(default_factory=list)  # 后果


@dataclass
class ModuleInfo:
    """模组信息"""
    id: str                    # 模组唯一标识
    name: str                  # 模组名称
    description: str           # 模组简介
    author: str = "Anonymous"  # 作者
    version: str = "1.0.0"     # 版本
    genre: str = "fantasy"     # 类型: fantasy, horror, scifi, modern
    difficulty: str = "normal" # 难度: easy, normal, hard
    player_count: str = "2-5"  # 建议玩家数
    duration: str = "2-4小时"  # 预计时长
    tags: List[str] = field(default_factory=list)


@dataclass
class ModuleBase:
    """模组基类"""
    info: ModuleInfo
    
    # 世界观设定
    world_name: str = ""
    world_background: str = ""  # 世界背景故事
    lore: List[str] = field(default_factory=list)  # 世界观设定条目
    
    # 开场
    intro_text: str = ""  # 开场白
    starting_location: str = ""  # 起始地点
    starting_time: str = "day"  # 起始时间
    starting_weather: str = "sunny"  # 起始天气
    
    # 内容
    npcs: Dict[str, NPCTemplate] = field(default_factory=dict)
    locations: Dict[str, LocationTemplate] = field(default_factory=dict)
    events: List[EventTemplate] = field(default_factory=list)
    
    # 物品
    key_items: List[Dict[str, str]] = field(default_factory=list)  # 关键道具
    
    # 结局
    endings: List[Dict[str, str]] = field(default_factory=list)  # 可能的结局
    
    # DM 提示
    dm_notes: str = ""  # 给 DM 的提示
    plot_hooks: List[str] = field(default_factory=list)  # 剧情钩子

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "info": {
                "id": self.info.id,
                "name": self.info.name,
                "description": self.info.description,
                "author": self.info.author,
                "version": self.info.version,
                "genre": self.info.genre,
                "difficulty": self.info.difficulty,
                "player_count": self.info.player_count,
                "duration": self.info.duration,
                "tags": self.info.tags,
            },
            "world_name": self.world_name,
            "world_background": self.world_background,
            "lore": self.lore,
            "intro_text": self.intro_text,
            "starting_location": self.starting_location,
            "starting_time": self.starting_time,
            "starting_weather": self.starting_weather,
            "npcs": {k: vars(v) for k, v in self.npcs.items()},
            "locations": {k: vars(v) for k, v in self.locations.items()},
            "events": [vars(e) for e in self.events],
            "key_items": self.key_items,
            "endings": self.endings,
            "dm_notes": self.dm_notes,
            "plot_hooks": self.plot_hooks,
        }
