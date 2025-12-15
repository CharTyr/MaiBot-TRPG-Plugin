"""
TRPG DM 插件事件处理器
实现与 MaiBot 主程序的深度融合
"""

from typing import Tuple, Optional, Dict, TYPE_CHECKING
from src.plugin_system import (
    BaseEventHandler,
    EventType,
    MaiMessages,
    CustomEventHandlerResult,
)
from src.common.logger import get_logger

if TYPE_CHECKING:
    from ..models.storage import StorageManager
    from ..services.dm_engine import DMEngine

logger = get_logger("trpg_handlers")

# 全局引用，由插件主类注入
_storage: Optional["StorageManager"] = None
_dm_engine: Optional["DMEngine"] = None
_plugin_config: dict = {}


def set_handler_services(storage: "StorageManager", dm: "DMEngine", config: dict):
    """设置服务引用"""
    global _storage, _dm_engine, _plugin_config
    _storage = storage
    _dm_engine = dm
    _plugin_config = config


class TRPGMessageHandler(BaseEventHandler):
    """
    跑团消息处理器
    
    核心功能：
    1. 拦截来自已启用跑团群组的消息
    2. 完全接管消息处理，阻止其他插件干扰
    3. 与 MaiBot 的 replyer 系统深度融合
    """
    
    event_type = EventType.ON_MESSAGE
    handler_name = "trpg_message_handler"
    handler_description = "处理跑团相关的玩家消息，完全接管跑团群组的消息处理"
    weight = 1000  # 最高权重，优先处理
    intercept_message = True  # 拦截消息，阻止后续处理

    async def execute(
        self, message: MaiMessages | None
    ) -> Tuple[bool, bool, Optional[str], Optional[CustomEventHandlerResult], Optional[MaiMessages]]:
        """
        处理消息
        
        Returns:
            (是否执行成功, 是否继续处理, 返回消息, 自定义结果, 修改后的消息)
        """
        if not message or not _storage or not _dm_engine:
            return True, True, None, None, None
        
        stream_id = message.stream_id
        if not stream_id:
            return True, True, None, None, None
        
        # 检查是否是已启用跑团的群组
        if not _storage.is_group_enabled(stream_id):
            return True, True, None, None, None
        
        # 检查是否有活跃会话
        session = await _storage.get_session(stream_id)
        if not session or not session.is_active():
            return True, True, None, None, None
        
        # 获取消息内容
        plain_text = message.plain_text
        if not plain_text:
            return True, True, None, None, None
        
        # 命令消息交给命令处理器处理，但仍然阻止其他插件
        if plain_text.startswith("/"):
            # 检查是否是跑团相关命令
            trpg_commands = ["/trpg", "/r", "/roll", "/join", "/pc", "/inv", "/hp", "/mp", "/dm", "/lore", "/module"]
            is_trpg_command = any(plain_text.startswith(cmd) for cmd in trpg_commands)
            
            if is_trpg_command:
                # 跑团命令，让命令处理器处理，但阻止其他插件
                integration_config = _plugin_config.get("integration", {})
                block_others = integration_config.get("block_other_plugins", True)
                return True, not block_others, None, None, None
            else:
                # 非跑团命令，放行
                return True, True, None, None, None
        
        # 获取用户信息
        user_id = None
        if message.message_base_info:
            user_info = message.message_base_info.get("user_info", {})
            user_id = str(user_info.get("user_id", ""))
        
        if not user_id:
            return True, True, None, None, None
        
        # 获取玩家信息
        player = await _storage.get_player(stream_id, user_id)
        
        # 检查是否允许中途加入
        session_config = _plugin_config.get("session", {})
        allow_mid_join = session_config.get("allow_mid_join", True)
        mid_join_require_confirm = session_config.get("mid_join_require_confirm", False)
        
        if not player and not allow_mid_join:
            # 不允许中途加入，忽略非玩家消息但仍阻止其他插件
            integration_config = _plugin_config.get("integration", {})
            if integration_config.get("takeover_message", True):
                return True, False, None, None, None
            return True, True, None, None, None
        
        # 检查是否有待确认的加入请求
        if not player and mid_join_require_confirm:
            pending = _storage.get_pending_join(stream_id, user_id)
            if pending:
                # 已有待确认请求，忽略消息
                integration_config = _plugin_config.get("integration", {})
                if integration_config.get("takeover_message", True):
                    return True, False, None, None, None
                return True, True, None, None, None
        
        # 检查是否是角色扮演消息或需要 DM 响应的消息
        is_roleplay = self._is_roleplay_message(plain_text)
        should_respond = is_roleplay or (player and self._should_dm_respond(plain_text, session))
        
        if should_respond:
            # 记录玩家行动
            character_name = player.character_name if player else "旁观者"
            session.add_history(
                "player",
                plain_text,
                user_id=user_id,
                character_name=character_name,
            )
            
            # 检查是否启用自动叙述
            dm_config = _plugin_config.get("dm", {})
            if dm_config.get("auto_narrative", True):
                try:
                    # 生成 DM 响应
                    response = await _dm_engine.generate_dm_response(
                        session=session,
                        player_message=plain_text,
                        player=player,
                        config=_plugin_config,
                    )
                    
                    # 记录 DM 响应
                    session.add_history("dm", response)
                    await _storage.save_session(session)
                    
                    # 发送响应
                    await self.send_text(stream_id, response)
                    
                except Exception as e:
                    logger.error(f"[TRPGHandler] 生成 DM 响应失败: {e}")
                    await _storage.save_session(session)
            else:
                # 仅保存历史
                await _storage.save_session(session)
        
        # 根据配置决定是否阻止其他插件处理
        integration_config = _plugin_config.get("integration", {})
        if integration_config.get("takeover_message", True):
            # 完全接管，阻止后续处理
            return True, False, None, None, None
        
        return True, True, None, None, None

    def _is_roleplay_message(self, text: str) -> bool:
        """判断是否是角色扮演消息"""
        # 动作描述格式
        if text.startswith("*") and text.endswith("*"):
            return True
        if text.startswith("（") and text.endswith("）"):
            return True
        if text.startswith("(") and text.endswith(")"):
            return True
        
        # 角色对话格式
        if text.startswith("【") and "】" in text:
            return True
        
        # 引号对话
        if (text.startswith('"') and text.endswith('"')) or (text.startswith('"') and text.endswith('"')):
            return True
        
        return False

    def _should_dm_respond(self, text: str, session) -> bool:
        """判断 DM 是否应该响应这条消息"""
        # 行动关键词
        action_keywords = [
            "我要", "我想", "我尝试", "我试着", "我决定",
            "攻击", "使用", "查看", "检查", "调查", "搜索",
            "走向", "前往", "进入", "离开", "移动",
            "说", "问", "告诉", "询问", "回答",
            "拿", "捡", "打开", "关闭", "推", "拉",
            "躲", "藏", "逃跑", "战斗", "施法",
        ]
        
        text_lower = text.lower()
        for keyword in action_keywords:
            if keyword in text_lower:
                return True
        
        # 检查是否是对 NPC 说话
        for npc_name in session.npcs.keys():
            if npc_name in text:
                return True
        
        # 检查消息长度（较长的消息可能是角色扮演）
        if len(text) > 20:
            return True
        
        return False


class TRPGStartupHandler(BaseEventHandler):
    """跑团启动处理器"""
    
    event_type = EventType.ON_START
    handler_name = "trpg_startup_handler"
    handler_description = "跑团插件启动初始化"
    weight = 0
    intercept_message = False

    async def execute(
        self, message: MaiMessages | None
    ) -> Tuple[bool, bool, Optional[str], Optional[CustomEventHandlerResult], Optional[MaiMessages]]:
        """启动时初始化"""
        logger.info("[TRPGHandler] 跑团插件启动初始化")
        
        if _storage:
            await _storage.initialize()
            active_sessions = await _storage.get_active_sessions()
            logger.info(f"[TRPGHandler] 已加载 {len(active_sessions)} 个活跃会话")
            
            # 输出活跃会话信息
            for session in active_sessions:
                players = await _storage.get_players_in_session(session.stream_id)
                logger.info(f"  - {session.world_name} ({session.stream_id}): {len(players)} 名玩家")
        
        return True, True, None, None, None


class TRPGShutdownHandler(BaseEventHandler):
    """跑团关闭处理器"""
    
    event_type = EventType.ON_STOP
    handler_name = "trpg_shutdown_handler"
    handler_description = "跑团插件关闭保存"
    weight = 0
    intercept_message = True  # 确保能执行

    async def execute(
        self, message: MaiMessages | None
    ) -> Tuple[bool, bool, Optional[str], Optional[CustomEventHandlerResult], Optional[MaiMessages]]:
        """关闭时保存数据"""
        logger.info("[TRPGHandler] 跑团插件关闭，保存数据...")
        
        if _storage:
            await _storage.save_all()
            logger.info("[TRPGHandler] 所有跑团数据已保存")
        
        return True, True, None, None, None
