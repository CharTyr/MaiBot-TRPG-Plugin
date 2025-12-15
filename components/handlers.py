"""
TRPG DM 插件事件处理器
"""

from typing import Tuple, Optional, TYPE_CHECKING
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
    
    拦截来自已启用跑团群组的消息，交给 DM 引擎处理
    """
    
    event_type = EventType.ON_MESSAGE
    handler_name = "trpg_message_handler"
    handler_description = "处理跑团相关的玩家消息"
    weight = 100  # 高权重，优先处理
    intercept_message = False  # 默认不拦截，让其他处理器也能处理

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
        
        # 忽略命令消息（以 / 开头）
        if plain_text.startswith("/"):
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
        
        # 检查是否是角色扮演消息（可以通过特定格式识别）
        is_roleplay = self._is_roleplay_message(plain_text)
        
        if is_roleplay or (player and self._should_dm_respond(plain_text, session)):
            # 记录玩家行动
            character_name = player.character_name if player else "旁观者"
            session.add_history(
                "player",
                plain_text,
                user_id=user_id,
                character_name=character_name,
            )
            
            # 如果启用了自动叙述，生成 DM 响应
            if _plugin_config.get("dm", {}).get("auto_narrative", True):
                try:
                    # 解析玩家意图
                    intent = await _dm_engine.interpret_player_intent(plain_text, session, player)
                    
                    # 生成 DM 响应
                    response = await _dm_engine.generate_narrative(
                        session=session,
                        player_action=plain_text,
                        player=player,
                        context=f"玩家意图: {intent.get('intent', 'unknown')}",
                    )
                    
                    # 记录 DM 响应
                    session.add_history("dm", response)
                    await _storage.save_session(session)
                    
                    # 发送响应
                    await self.send_text(stream_id, f"🎲 {response}")
                    
                except Exception as e:
                    logger.error(f"[TRPGHandler] 生成 DM 响应失败: {e}")
            else:
                # 仅保存历史
                await _storage.save_session(session)
        
        # 继续让其他处理器处理
        return True, True, None, None, None

    def _is_roleplay_message(self, text: str) -> bool:
        """
        判断是否是角色扮演消息
        
        常见的角色扮演格式:
        - *动作描述*
        - （动作描述）
        - 【角色名】对话
        - "对话内容"
        """
        # 检查动作描述格式
        if text.startswith("*") and text.endswith("*"):
            return True
        if text.startswith("（") and text.endswith("）"):
            return True
        if text.startswith("(") and text.endswith(")"):
            return True
        
        # 检查角色对话格式
        if text.startswith("【") and "】" in text:
            return True
        
        # 检查引号对话
        if text.startswith('"') and text.endswith('"'):
            return True
        if text.startswith('"') and text.endswith('"'):
            return True
        
        return False

    def _should_dm_respond(self, text: str, session) -> bool:
        """
        判断 DM 是否应该响应这条消息
        
        基于消息内容和上下文判断
        """
        # 检查是否包含行动关键词
        action_keywords = [
            "我要", "我想", "我尝试", "我试着",
            "攻击", "使用", "查看", "检查", "调查",
            "走向", "前往", "进入", "离开",
            "说", "问", "告诉", "询问",
            "拿", "捡", "打开", "关闭",
        ]
        
        text_lower = text.lower()
        for keyword in action_keywords:
            if keyword in text_lower:
                return True
        
        # 检查是否是对 NPC 说话
        for npc_name in session.npcs.keys():
            if npc_name in text:
                return True
        
        return False


class TRPGStartupHandler(BaseEventHandler):
    """
    跑团启动处理器
    
    在插件启动时初始化数据
    """
    
    event_type = EventType.ON_START
    handler_name = "trpg_startup_handler"
    handler_description = "跑团插件启动初始化"
    weight = 0

    async def execute(
        self, message: MaiMessages | None
    ) -> Tuple[bool, bool, Optional[str], Optional[CustomEventHandlerResult], Optional[MaiMessages]]:
        """启动时初始化"""
        logger.info("[TRPGHandler] 跑团插件启动初始化")
        
        if _storage:
            await _storage.initialize()
            active_sessions = await _storage.get_active_sessions()
            logger.info(f"[TRPGHandler] 已加载 {len(active_sessions)} 个活跃会话")
        
        return True, True, None, None, None


class TRPGShutdownHandler(BaseEventHandler):
    """
    跑团关闭处理器
    
    在插件关闭时保存数据
    """
    
    event_type = EventType.ON_STOP
    handler_name = "trpg_shutdown_handler"
    handler_description = "跑团插件关闭保存"
    weight = 0

    async def execute(
        self, message: MaiMessages | None
    ) -> Tuple[bool, bool, Optional[str], Optional[CustomEventHandlerResult], Optional[MaiMessages]]:
        """关闭时保存数据"""
        logger.info("[TRPGHandler] 跑团插件关闭，保存数据...")
        
        if _storage:
            await _storage.save_all()
            logger.info("[TRPGHandler] 数据保存完成")
        
        return True, True, None, None, None
