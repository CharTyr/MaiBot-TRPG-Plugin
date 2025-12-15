"""
预设模组集合
"""

from . import haunted_mansion
from . import dragon_cave
from . import cyberpunk_heist

# 所有可用的预设模组
PRESET_MODULES = {
    "haunted_mansion": {
        "name": "幽灵庄园",
        "genre": "horror",
        "difficulty": "normal",
        "create": haunted_mansion.create_module,
    },
    "dragon_cave": {
        "name": "龙穴探险",
        "genre": "fantasy",
        "difficulty": "easy",
        "create": dragon_cave.create_module,
    },
    "cyberpunk_heist": {
        "name": "霓虹暗影",
        "genre": "scifi",
        "difficulty": "hard",
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
        }
        for module_id, info in PRESET_MODULES.items()
    ]


def create_module(module_id: str):
    """根据ID创建模组实例"""
    if module_id in PRESET_MODULES:
        return PRESET_MODULES[module_id]["create"]()
    return None
