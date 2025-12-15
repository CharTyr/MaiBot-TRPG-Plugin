"""
预设模组集合
"""

from . import haunted_mansion
from . import dragon_cave
from . import cyberpunk_heist
from . import solo_mystery

# 所有可用的预设模组
PRESET_MODULES = {
    "solo_mystery": {
        "name": "独行侦探",
        "genre": "modern",
        "difficulty": "easy",
        "player_count": "1",
        "create": solo_mystery.create_module,
    },
    "dragon_cave": {
        "name": "龙穴探险",
        "genre": "fantasy",
        "difficulty": "easy",
        "player_count": "3-5",
        "create": dragon_cave.create_module,
    },
    "haunted_mansion": {
        "name": "幽灵庄园",
        "genre": "horror",
        "difficulty": "normal",
        "player_count": "2-4",
        "create": haunted_mansion.create_module,
    },
    "cyberpunk_heist": {
        "name": "霓虹暗影",
        "genre": "scifi",
        "difficulty": "hard",
        "player_count": "3-4",
        "create": cyberpunk_heist.create_module,
    },
}


def get_module_list():
    """获取所有可用模组列表"""
    return [
        {
            "id": module_id,
            "name": info["name"],
            "genre": info["genre"],
            "difficulty": info["difficulty"],
            "player_count": info["player_count"],
        }
        for module_id, info in PRESET_MODULES.items()
    ]


def create_module(module_id: str):
    """根据ID创建模组实例"""
    if module_id in PRESET_MODULES:
        return PRESET_MODULES[module_id]["create"]()
    return None
