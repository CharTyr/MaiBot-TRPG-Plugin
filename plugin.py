"""
MaiBot TRPG DM 跑团插件

将 MaiBot 变成专业的 TRPG 跑团 DM，支持：
- 骰子系统
- 玩家角色管理
- 背包物品系统
- 世界状态管理
- 剧情生成
- NPC 扮演
- 数据持久化
- 群组隔离
- 存档系统
"""

import os
from typing import List, Tuple, Type
from pathlib import Path

from src.plugin_system import (
    BasePlugin,
    register_plugin,
    ConfigField,
    ComponentInfo,
)
from src.common.logger import get_logger

# 导入模型
from .models.storage import StorageManager
from .models.session import TRPGSession
from .models.player import Player

# 导入服务
from .services.dice import DiceService
from .services.dm_engine import DMEngine

# 导入组件
from .components.commands import (
    TRPGSessionCommand,
    DiceRollCommand,
    PlayerJoinCommand,
    PlayerStatusCommand,
    InventoryCommand,
    HPCommand,
    MPCommand,
    DMCommand,
    LoreCommand,
    ModuleCommand,
    SaveSlotCommand,
    ImageCommand,
    AdminJoinConfirmCommand,
    set_services as set_command_services,
    set_config as set_command_config,
)
from .components.handlers import (
    TRPGMessageHandler,
    TRPGStartupHandler,
    TRPGShutdownHandler,
    set_handler_services,
)
from .components.tools import (
    RollDiceTool,
    CheckPlayerStatusTool,
    GetWorldStateTool,
    ModifyPlayerStatusTool,
    SearchLoreTool,
    set_tool_services,
)

# 导入模组系统
from .modules.loader import ModuleLoader

logger = get_logger("trpg_dm_plugin")


@register_plugin
class TRPGDMPlugin(BasePlugin):
    """MaiBot TRPG DM 跑团插件"""

    # 插件基本信息
    plugin_name: str = "MaiBot_TRPG_DM"
    enable_plugin: bool = True
    dependencies: List[str] = []
    python_dependencies: List[str] = []
    config_file_name: str = "config.toml"

    # 配置节描述
    config_section_descriptions = {
        "plugin": "插件基本设置",
        "session": "会话管理设置",
        "dice": "骰子系统设置",
        "player": "玩家角色设置",
        "world": "世界状态设置",
        "dm": "DM 引擎设置",
        "permissions": "权限设置",
        "integration": "MaiBot 融合设置",
        "module": "模组系统设置",
    }

    # 配置 Schema 定义
    config_schema: dict = {
        "plugin": {
            "config_version": ConfigField(type=str, default="1.2.0", description="配置文件版本"),
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
        },
        "session": {
            "enabled_groups": ConfigField(type=list, default=[], description="允许启用跑团的群组ID列表"),
            "auto_save_interval": ConfigField(type=int, default=300, description="自动保存间隔（秒）"),
            "max_history_length": ConfigField(type=int, default=100, description="历史记录最大条数"),
            "verbose_mode": ConfigField(type=bool, default=False, description="是否显示详细日志"),
        },
        "dice": {
            "default_dice_sides": ConfigField(type=int, default=20, description="默认骰子面数"),
            "max_dice_count": ConfigField(type=int, default=100, description="单次最大骰子数量"),
            "max_dice_sides": ConfigField(type=int, default=1000, description="单个骰子最大面数"),
            "show_individual_rolls": ConfigField(type=bool, default=True, description="是否显示每个骰子的结果"),
        },
        "player": {
            "default_attribute_value": ConfigField(type=int, default=10, description="默认属性值"),
            "default_max_hp": ConfigField(type=int, default=20, description="默认最大生命值"),
            "default_max_mp": ConfigField(type=int, default=10, description="默认最大魔力值"),
            "max_inventory_size": ConfigField(type=int, default=50, description="背包最大容量"),
        },
        "world": {
            "default_world_name": ConfigField(type=str, default="通用奇幻世界", description="默认世界观名称"),
            "default_time": ConfigField(type=str, default="day", description="默认时间状态"),
            "default_weather": ConfigField(type=str, default="sunny", description="默认天气"),
        },
        "dm": {
            "llm_temperature": ConfigField(type=float, default=0.8, description="DM响应的温度参数"),
            "llm_max_tokens": ConfigField(type=int, default=1000, description="DM响应的最大token数"),
            "auto_narrative": ConfigField(type=bool, default=True, description="是否启用自动剧情生成"),
            "npc_style": ConfigField(type=str, default="immersive", description="NPC对话风格"),
        },
        "permissions": {
            "admin_users": ConfigField(type=list, default=[], description="管理员用户ID列表"),
            "allow_player_edit_attributes": ConfigField(type=bool, default=False, description="是否允许玩家自行修改属性"),
            "allow_view_others": ConfigField(type=bool, default=True, description="是否允许玩家查看其他玩家状态"),
            "allow_player_end_session": ConfigField(type=bool, default=False, description="是否允许非管理员结束跑团"),
        },
        "integration": {
            "takeover_message": ConfigField(type=bool, default=True, description="跑团模式下是否完全接管消息处理"),
            "block_other_plugins": ConfigField(type=bool, default=True, description="接管时是否阻止其他插件处理消息"),
            "merge_bot_personality": ConfigField(type=bool, default=True, description="是否使用MaiBot的人格设定融合DM角色"),
        },
        "module": {
            "custom_module_dir": ConfigField(type=str, default="data/modules", description="自定义模组目录"),
            "allow_pdf_import": ConfigField(type=bool, default=True, description="是否允许导入PDF模组"),
            "pdf_parse_model": ConfigField(type=str, default="utils", description="PDF解析使用的模型"),
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 获取插件数据目录
        plugin_dir = Path(__file__).parent
        self.data_dir = plugin_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化服务
        self._storage: StorageManager = None
        self._dice_service: DiceService = None
        self._dm_engine: DMEngine = None
        self._module_loader: ModuleLoader = None

    def _initialize_services(self):
        """初始化所有服务"""
        if self._storage is not None:
            return  # 已初始化
        
        logger.info(f"[{self.plugin_name}] 初始化服务...")
        
        # 获取配置
        config = self.plugin_config or {}
        
        # 初始化存储管理器（传入配置）
        self._storage = StorageManager(str(self.data_dir), config)
        
        # 初始化骰子服务
        dice_config = config.get("dice", {})
        self._dice_service = DiceService(
            max_dice_count=dice_config.get("max_dice_count", 100),
            max_dice_sides=dice_config.get("max_dice_sides", 1000),
        )
        
        # 初始化 DM 引擎
        self._dm_engine = DMEngine(config)
        
        # 初始化模组加载器
        self._module_loader = ModuleLoader(self.data_dir / "modules")
        
        # 注入服务和配置到组件
        set_command_services(self._storage, self._dice_service, self._dm_engine, self._module_loader)
        set_command_config(config)
        set_handler_services(self._storage, self._dm_engine, config)
        set_tool_services(self._storage, self._dice_service)
        
        logger.info(f"[{self.plugin_name}] 服务初始化完成")

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """获取插件包含的组件列表"""
        # 确保服务已初始化
        self._initialize_services()
        
        return [
            # 命令组件
            (TRPGSessionCommand.get_command_info(), TRPGSessionCommand),
            (DiceRollCommand.get_command_info(), DiceRollCommand),
            (PlayerJoinCommand.get_command_info(), PlayerJoinCommand),
            (PlayerStatusCommand.get_command_info(), PlayerStatusCommand),
            (InventoryCommand.get_command_info(), InventoryCommand),
            (HPCommand.get_command_info(), HPCommand),
            (MPCommand.get_command_info(), MPCommand),
            (DMCommand.get_command_info(), DMCommand),
            (LoreCommand.get_command_info(), LoreCommand),
            (ModuleCommand.get_command_info(), ModuleCommand),
            (SaveSlotCommand.get_command_info(), SaveSlotCommand),
            (ImageCommand.get_command_info(), ImageCommand),
            (AdminJoinConfirmCommand.get_command_info(), AdminJoinConfirmCommand),
            
            # 事件处理器
            (TRPGMessageHandler.get_handler_info(), TRPGMessageHandler),
            (TRPGStartupHandler.get_handler_info(), TRPGStartupHandler),
            (TRPGShutdownHandler.get_handler_info(), TRPGShutdownHandler),
            
            # LLM 工具
            (RollDiceTool.get_tool_info(), RollDiceTool),
            (CheckPlayerStatusTool.get_tool_info(), CheckPlayerStatusTool),
            (GetWorldStateTool.get_tool_info(), GetWorldStateTool),
            (ModifyPlayerStatusTool.get_tool_info(), ModifyPlayerStatusTool),
            (SearchLoreTool.get_tool_info(), SearchLoreTool),
        ]
