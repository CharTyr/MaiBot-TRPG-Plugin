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

# 导入服务
from .services.dice import DiceService
from .services.dm_engine import DMEngine

# 导入组件
from .components.commands import (
    TRPGCommand,
    DiceShortcut,
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
        "save_slots": "存档插槽设置",
        "dice": "骰子系统设置",
        "player": "玩家角色设置",
        "world": "世界状态设置",
        "dm": "DM 引擎设置",
        "permissions": "权限设置",
        "integration": "MaiBot 融合设置",
        "multiplayer": "多人行动设置",
        "module": "模组系统设置",
        "image": "场景图片设置",
        "llm_models": "模型组选择",
    }

    # 配置 Schema 定义
    config_schema: dict = {
        "plugin": {
            "config_version": ConfigField(type=str, default="1.2.0", description="配置文件版本"),
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
            "allowed_groups": ConfigField(type=list, default=[], description="允许启用跑团的群组ID列表（空列表表示全部允许）"),
        },
        "session": {
            "auto_save_interval": ConfigField(type=int, default=300, description="自动保存间隔（秒）"),
            "max_history_length": ConfigField(type=int, default=100, description="历史记录最大条数"),
            "verbose_mode": ConfigField(type=bool, default=False, description="是否显示详细日志"),
            "allow_mid_join": ConfigField(type=bool, default=True, description="是否允许中途加入"),
            "mid_join_require_confirm": ConfigField(type=bool, default=False, description="中途加入是否需要管理员确认"),
        },
        "save_slots": {
            "max_slots": ConfigField(type=int, default=3, description="存档插槽数量（每个群组独立）"),
            "allow_overwrite": ConfigField(type=bool, default=True, description="是否允许覆盖已有存档"),
        },
        "dice": {
            "default_dice_sides": ConfigField(type=int, default=20, description="默认骰子面数"),
            "max_dice_count": ConfigField(type=int, default=100, description="单次最大骰子数量"),
            "max_dice_sides": ConfigField(type=int, default=1000, description="单个骰子最大面数"),
            "show_individual_rolls": ConfigField(type=bool, default=True, description="是否显示每个骰子的结果"),
        },
        "player": {
            "free_points": ConfigField(type=int, default=30, description="初始自由加点点数"),
            "base_attribute": ConfigField(type=int, default=8, description="基础属性值（加点前）"),
            "max_attribute": ConfigField(type=int, default=18, description="单项属性最大值"),
            "min_attribute": ConfigField(type=int, default=3, description="单项属性最小值"),
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
            "use_maibot_replyer": ConfigField(type=bool, default=True, description="是否优先使用 replyer 模型"),
            "llm_temperature": ConfigField(type=float, default=0.8, description="DM响应的温度参数"),
            "llm_max_tokens": ConfigField(type=int, default=800, description="DM响应的最大token数"),
            "auto_narrative": ConfigField(type=bool, default=True, description="是否启用自动剧情生成"),
            "npc_style": ConfigField(type=str, default="immersive", description="NPC对话风格"),
            "dm_personality": ConfigField(type=str, default="", description="DM 人格提示词（简短为佳）"),
            "include_action_hints": ConfigField(type=bool, default=True, description="是否在回复中包含行动建议"),
            "show_action_feedback": ConfigField(type=bool, default=True, description="玩家行动时是否立即反馈已接收"),
            "max_retries": ConfigField(type=int, default=3, description="DM 响应失败最大重试次数"),
            "retry_delay": ConfigField(type=float, default=1.0, description="重试间隔基础时间（秒）"),
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
        "multiplayer": {
            "batch_actions": ConfigField(type=bool, default=True, description="多人模式下是否批量处理行动"),
            "action_collect_window": ConfigField(type=float, default=60.0, description="等待所有玩家行动的最大时间（秒）"),
            "reminder_interval": ConfigField(type=float, default=20.0, description="提醒未行动玩家的间隔（秒）"),
            "process_when_all_ready": ConfigField(type=bool, default=True, description="所有玩家行动后是否立即处理"),
        },
        "module": {
            "custom_module_dir": ConfigField(type=str, default="data/modules", description="自定义模组目录"),
            "markdown_module_dir": ConfigField(type=str, default="custom_modules", description="Markdown 模组目录"),
            "auto_scan_markdown": ConfigField(type=bool, default=True, description="是否自动扫描 Markdown 模组"),
            "allow_pdf_import": ConfigField(type=bool, default=True, description="是否允许导入PDF模组"),
            "pdf_parse_model": ConfigField(type=str, default="utils", description="PDF解析使用的模型"),
        },
        "image": {
            "enabled": ConfigField(type=bool, default=False, description="是否启用场景图片生成"),
            "api_type": ConfigField(type=str, default="sd_api", description="生图 API 类型: openai/sd_api/gradio/novelai"),
            "base_url": ConfigField(type=str, default="", description="生图 API 地址"),
            "api_key": ConfigField(type=str, default="", description="生图 API 密钥（建议通过环境变量注入）"),
            "model_name": ConfigField(type=str, default="", description="模型名称（OpenAI兼容需要）"),
            "default_size_preset": ConfigField(type=str, default="landscape", description="默认尺寸预设"),
            "custom_width": ConfigField(type=int, default=0, description="自定义宽度（0表示使用预设）"),
            "custom_height": ConfigField(type=int, default=0, description="自定义高度（0表示使用预设）"),
            "auto_generate": ConfigField(type=bool, default=False, description="是否自动生成场景图片"),
            "auto_generate_interval": ConfigField(type=int, default=10, description="自动生成触发间隔（条消息）"),
            "climax_auto_image": ConfigField(type=bool, default=True, description="高潮时是否自动生成图片"),
            "climax_min_interval": ConfigField(type=int, default=5, description="高潮画图最小间隔（历史条数）"),
        },
        "llm_models": {
            "dm_response_model": ConfigField(type=str, default="replyer", description="DM 响应使用的模型组"),
            "image_prompt_model": ConfigField(type=str, default="planner", description="图片提示词生成使用的模型组"),
            "pdf_parse_model": ConfigField(type=str, default="utils", description="PDF 解析使用的模型组"),
            "intent_model": ConfigField(type=str, default="planner", description="意图理解使用的模型组"),
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
        
        # 获取配置 (BasePlugin 使用 self.config)
        config = getattr(self, 'config', {}) or {}
        
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
        
        # 初始化模组加载器（支持配置自定义目录）
        module_config = config.get("module", {})
        custom_module_dir = module_config.get("custom_module_dir", "data/modules")
        plugin_dir = Path(__file__).parent
        self._module_loader = ModuleLoader(plugin_dir / custom_module_dir, config=config)
        
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
            # 统一命令
            (TRPGCommand.get_command_info(), TRPGCommand),
            # 骰子快捷命令
            (DiceShortcut.get_command_info(), DiceShortcut),
            
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
