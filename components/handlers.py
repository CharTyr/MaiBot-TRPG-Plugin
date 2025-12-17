"""
TRPG DM 插件事件处理器
实现与 MaiBot 主程序的深度融合
"""

import asyncio
import time
from typing import Tuple, Optional, Dict, List, TYPE_CHECKING
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

# 重试配置
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # 秒

# 多人行动收集配置
DEFAULT_ACTION_COLLECT_WINDOW = 60.0  # 秒，等待所有玩家行动的最大时间
DEFAULT_ACTION_REMINDER_INTERVAL = 20.0  # 秒，提醒未行动玩家的间隔

# 全局引用，由插件主类注入
_storage: Optional["StorageManager"] = None
_dm_engine: Optional["DMEngine"] = None
_plugin_config: dict = {}

# 多人行动收集器（按 stream_id 分组）
_action_collectors: Dict[str, "ActionCollector"] = {}


class ActionCollector:
    """
    多人行动收集器
    
    等待所有已加入的玩家做出行动决定，或超时后处理已收集的行动
    """
    
    def __init__(
        self, 
        stream_id: str, 
        total_players: int,
        player_ids: List[str],
        max_wait_time: float = DEFAULT_ACTION_COLLECT_WINDOW,
        reminder_interval: float = DEFAULT_ACTION_REMINDER_INTERVAL,
    ):
        self.stream_id = stream_id
        self.total_players = total_players  # 需要等待的玩家总数
        self.player_ids = set(player_ids)   # 所有玩家ID
        self.max_wait_time = max_wait_time
        self.reminder_interval = reminder_interval
        
        self.actions: Dict[str, Dict] = {}  # {user_id: {character_name, action, timestamp}}
        self.first_action_time: Optional[float] = None
        self.is_processing: bool = False    # 是否正在处理中
        
        self._lock = asyncio.Lock()
        self._timeout_task: Optional[asyncio.Task] = None
        self._reminder_task: Optional[asyncio.Task] = None
        self._handler_ref = None  # 用于发送消息的 handler 引用
    
    def set_handler(self, handler):
        """设置 handler 引用用于发送消息"""
        self._handler_ref = handler
    
    async def add_action(
        self, 
        user_id: str, 
        character_name: str, 
        action: str
    ) -> Tuple[bool, bool, int, int]:
        """
        添加一个行动
        
        Returns:
            (is_first, all_ready, current_count, total_count)
            - is_first: 是否是第一个行动（需要启动定时器）
            - all_ready: 是否所有玩家都已行动
            - current_count: 当前已行动人数
            - total_count: 总玩家数
        """
        async with self._lock:
            if self.is_processing:
                return False, False, len(self.actions), self.total_players
            
            now = time.time()
            is_first = self.first_action_time is None
            
            # 记录或更新行动
            is_update = user_id in self.actions
            self.actions[user_id] = {
                "user_id": user_id,
                "character_name": character_name,
                "action": action,
                "timestamp": now,
            }
            
            if is_first:
                self.first_action_time = now
            
            current_count = len(self.actions)
            all_ready = current_count >= self.total_players
            
            return is_first and not is_update, all_ready, current_count, self.total_players
    
    def get_missing_players(self) -> List[str]:
        """获取尚未行动的玩家ID列表"""
        return [pid for pid in self.player_ids if pid not in self.actions]
    
    def get_acted_players(self) -> List[str]:
        """获取已行动的玩家ID列表"""
        return list(self.actions.keys())
    
    async def get_and_clear(self) -> List[Dict]:
        """获取所有收集的行动并清空"""
        async with self._lock:
            actions = list(self.actions.values())
            self.actions = {}
            self.first_action_time = None
            self.is_processing = False
            return actions
    
    def get_action_count(self) -> int:
        """获取当前收集的行动数量"""
        return len(self.actions)
    
    def mark_processing(self):
        """标记为正在处理"""
        self.is_processing = True
    
    def start_timeout_task(self, callback):
        """启动超时任务"""
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
        
        async def timeout_handler():
            await asyncio.sleep(self.max_wait_time)
            await callback()
        
        self._timeout_task = asyncio.create_task(timeout_handler())
    
    def start_reminder_task(self, callback):
        """启动提醒任务"""
        if self._reminder_task and not self._reminder_task.done():
            self._reminder_task.cancel()
        
        async def reminder_handler():
            while True:
                await asyncio.sleep(self.reminder_interval)
                if self.is_processing:
                    break
                missing = self.get_missing_players()
                if missing:
                    await callback(missing)
                else:
                    break
        
        self._reminder_task = asyncio.create_task(reminder_handler())
    
    def cancel_all_tasks(self):
        """取消所有待处理任务"""
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
        if self._reminder_task and not self._reminder_task.done():
            self._reminder_task.cancel()


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
        
        # 命令消息处理
        if plain_text.startswith("/"):
            # 检查是否是跑团相关命令 - 统一使用 /trpg 前缀，保留 /r 快捷命令
            trpg_commands = ["/trpg", "/r ", "/roll "]
            is_trpg_command = any(plain_text.startswith(cmd) for cmd in trpg_commands)
            
            integration_config = _plugin_config.get("integration", {})
            takeover = integration_config.get("takeover_message", True)
            
            if is_trpg_command:
                # 跑团命令，让命令处理器处理，但阻止其他插件
                block_others = integration_config.get("block_other_plugins", True)
                return True, not block_others, None, None, None
            else:
                # 非跑团命令：根据 takeover_message 配置决定是否放行
                # 如果完全接管模式，则阻止其他命令；否则放行
                if takeover:
                    # 完全接管模式下，忽略非跑团命令（不处理也不放行给 MaiBot）
                    return True, False, None, None, None
                else:
                    # 非完全接管模式，放行给 MaiBot 处理
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
            character_name = player.character_name if player else "旁观者"
            dm_config = _plugin_config.get("dm", {})
            
            # 记录玩家行动到历史
            session.add_history(
                "player",
                plain_text,
                user_id=user_id,
                character_name=character_name,
            )
            await _storage.save_session(session)
            
            # 立即发送动作确认反馈（如果启用）
            if dm_config.get("show_action_feedback", True):
                action_ack = self._generate_action_acknowledgment(plain_text, character_name)
                if action_ack:
                    await self.send_text(stream_id, action_ack)
            
            # 检查是否启用自动叙述
            if dm_config.get("auto_narrative", True):
                # 检查多人模式配置
                multiplayer_config = _plugin_config.get("multiplayer", {})
                batch_mode = multiplayer_config.get("batch_actions", True)
                player_count = len(session.player_ids)
                
                # 只有多人（>=2）且启用批量模式时才收集行动
                if batch_mode and player_count >= 2:
                    await self._handle_multiplayer_action(
                        stream_id, session, user_id, character_name, plain_text, player
                    )
                else:
                    # 单人模式：立即响应
                    await self._generate_and_send_dm_response(
                        stream_id, session, plain_text, player
                    )
            else:
                # 仅保存历史，发送简单确认
                await self.send_text(stream_id, f"📝 已记录 {character_name} 的行动")
        
        # 根据配置决定是否阻止其他插件处理
        integration_config = _plugin_config.get("integration", {})
        if integration_config.get("takeover_message", True):
            # 完全接管，阻止后续处理
            return True, False, None, None, None
        
        return True, True, None, None, None

    async def _handle_multiplayer_action(
        self, stream_id: str, session, user_id: str, 
        character_name: str, action: str, player
    ):
        """处理多人模式下的行动收集 - 等待所有玩家行动"""
        global _action_collectors
        
        multiplayer_config = _plugin_config.get("multiplayer", {})
        max_wait_time = multiplayer_config.get("action_collect_window", DEFAULT_ACTION_COLLECT_WINDOW)
        reminder_interval = multiplayer_config.get("reminder_interval", DEFAULT_ACTION_REMINDER_INTERVAL)
        
        # 获取所有玩家
        all_players = await _storage.get_players_in_session(stream_id)
        player_ids = [p.user_id for p in all_players]
        total_players = len(player_ids)
        
        # 获取或创建行动收集器
        if stream_id not in _action_collectors or _action_collectors[stream_id].is_processing:
            _action_collectors[stream_id] = ActionCollector(
                stream_id=stream_id,
                total_players=total_players,
                player_ids=player_ids,
                max_wait_time=max_wait_time,
                reminder_interval=reminder_interval,
            )
        
        collector = _action_collectors[stream_id]
        collector.set_handler(self)
        
        # 添加行动
        is_first, all_ready, current_count, total_count = await collector.add_action(
            user_id, character_name, action
        )
        
        if is_first:
            # 第一个行动，启动等待
            logger.info(f"[TRPGHandler] 多人模式：开始收集行动，等待所有 {total_count} 名玩家（最长 {max_wait_time} 秒）")
            
            # 发送等待提示
            await self.send_text(
                stream_id, 
                f"⏳ 等待其他玩家行动... ({current_count}/{total_count})\n"
                f"💡 最长等待 {int(max_wait_time)} 秒，或所有玩家行动后立即处理"
            )
            
            # 启动超时任务
            async def on_timeout():
                await self._process_collected_actions(stream_id, timeout=True)
            
            collector.start_timeout_task(on_timeout)
            
            # 启动提醒任务
            async def on_reminder(missing_ids: List[str]):
                missing_players = []
                for pid in missing_ids:
                    p = await _storage.get_player(stream_id, pid)
                    if p:
                        missing_players.append(p.character_name)
                
                if missing_players:
                    acted_count = collector.get_action_count()
                    await self.send_text(
                        stream_id,
                        f"⏰ 等待中... ({acted_count}/{total_count})\n"
                        f"📢 尚未行动: {', '.join(missing_players)}"
                    )
            
            collector.start_reminder_task(on_reminder)
        
        else:
            # 后续行动
            logger.debug(f"[TRPGHandler] 多人模式：已收集 {current_count}/{total_count} 个行动")
            
            # 发送进度更新
            await self.send_text(
                stream_id,
                f"✅ {character_name} 已行动 ({current_count}/{total_count})"
            )
        
        # 检查是否所有人都已行动
        if all_ready:
            logger.info(f"[TRPGHandler] 多人模式：所有 {total_count} 名玩家已行动，立即处理")
            collector.cancel_all_tasks()
            await self._process_collected_actions(stream_id, timeout=False)

    async def _process_collected_actions(self, stream_id: str, timeout: bool = False):
        """处理收集到的所有行动"""
        global _action_collectors
        
        if stream_id not in _action_collectors:
            return
        
        collector = _action_collectors[stream_id]
        
        # 标记为正在处理，防止新行动加入
        collector.mark_processing()
        collector.cancel_all_tasks()
        
        actions = await collector.get_and_clear()
        
        if not actions:
            return
        
        session = await _storage.get_session(stream_id)
        if not session or not session.is_active():
            return
        
        # 获取未行动的玩家信息
        all_players = await _storage.get_players_in_session(stream_id)
        acted_ids = {act["user_id"] for act in actions}
        missing_players = [p for p in all_players if p.user_id not in acted_ids]
        
        # 发送处理开始提示
        if timeout and missing_players:
            missing_names = [p.character_name for p in missing_players]
            await self.send_text(
                stream_id,
                f"⏱️ 等待超时，开始处理已收集的 {len(actions)} 个行动\n"
                f"⚠️ 未行动: {', '.join(missing_names)}（本轮跳过）"
            )
        else:
            await self.send_text(
                stream_id,
                f"✨ 所有玩家已行动！正在处理 {len(actions)} 个行动..."
            )
        
        logger.info(f"[TRPGHandler] 多人模式：处理 {len(actions)} 个行动 (超时={timeout})")
        
        if len(actions) == 1:
            # 只有一个行动，使用单人模式处理
            act = actions[0]
            player = await _storage.get_player(stream_id, act["user_id"])
            await self._generate_and_send_dm_response(
                stream_id, session, act["action"], player
            )
        else:
            # 多个行动，生成批量响应
            await self._generate_batch_dm_response(stream_id, session, actions)

    async def _generate_and_send_dm_response(
        self, stream_id: str, session, player_message: str, player
    ):
        """生成并发送单人 DM 响应（带重试）"""
        dm_config = _plugin_config.get("dm", {})
        max_retries = dm_config.get("max_retries", DEFAULT_MAX_RETRIES)
        retry_delay = dm_config.get("retry_delay", DEFAULT_RETRY_DELAY)
        
        response = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = await _dm_engine.generate_dm_response(
                    session=session,
                    player_message=player_message,
                    player=player,
                    config=_plugin_config,
                )
                if response:
                    break
            except Exception as e:
                last_error = e
                logger.warning(f"[TRPGHandler] DM 响应生成失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
        
        if response:
            # 解析状态变化
            state_changes = _dm_engine.parse_state_changes(response, player)
            
            # 应用状态变化
            change_summary = ""
            if state_changes.has_changes():
                change_summary = await _dm_engine.apply_state_changes(
                    state_changes, session, _storage
                )
                logger.info(f"[TRPGHandler] 应用状态变化: {change_summary}")
            
            # 清理响应中的状态标签
            clean_response = _dm_engine.clean_state_tags(response)
            
            session.add_history("dm", clean_response)
            
            # 更新张力等级
            _dm_engine.update_tension_level(clean_response, session)
            
            # 检查是否需要更新剧情摘要
            if await _dm_engine.should_update_summary(session):
                await _dm_engine.update_story_summary(session)
            
            await _storage.save_session(session)
            
            # 发送响应（如果有状态变化，附加变化摘要）
            if change_summary:
                await self.send_text(stream_id, f"{clean_response}\n\n━━━ 状态变化 ━━━\n{change_summary}")
            else:
                await self.send_text(stream_id, clean_response)
            
            # 检测高潮场景，自动生成图片
            await self._check_and_generate_climax_image(stream_id, session, clean_response)
        else:
            logger.error(f"[TRPGHandler] DM 响应生成失败，已重试 {max_retries} 次: {last_error}")
            await self.send_text(stream_id, "⚠️ DM 思考中遇到了问题，请稍后再试...")

    async def _check_and_generate_climax_image(
        self, stream_id: str, session, dm_response: str
    ):
        """检测高潮场景并自动生成图片"""
        image_config = _plugin_config.get("image", {})
        
        # 检查是否启用图片生成
        if not image_config.get("enabled", False):
            return
        
        # 检查是否启用高潮自动画图
        if not image_config.get("climax_auto_image", True):
            return
        
        # 检测是否是高潮场景
        if not _dm_engine.detect_climax(dm_response, session):
            return
        
        logger.info("[TRPGHandler] 检测到剧情高潮，自动生成场景图片")
        
        try:
            from ..services.image_generator import ImageGenerator
            generator = ImageGenerator(_plugin_config)
            
            if not generator.is_enabled():
                return
            
            # 发送提示
            await self.send_text(stream_id, "🎨 高潮场景！正在生成场景图片...")
            
            # 生成图片（planner 会自动选择尺寸）
            success, result = await generator.generate_scene_image(session, dm_response[:200])
            
            if success:
                await self.send_image_base64(stream_id, result)
                # 更新上次生成图片的历史索引
                session.story_context.last_image_history_index = len(session.history)
                session.story_context.add_key_event(f"[场景图片] {session.world_state.location}")
                await _storage.save_session(session)
                logger.info("[TRPGHandler] 高潮场景图片生成成功")
            else:
                logger.warning(f"[TRPGHandler] 高潮场景图片生成失败: {result}")
                
        except Exception as e:
            logger.error(f"[TRPGHandler] 自动生成图片失败: {e}")

    async def _generate_batch_dm_response(
        self, stream_id: str, session, actions: List[Dict]
    ):
        """生成多人行动的批量 DM 响应"""
        dm_config = _plugin_config.get("dm", {})
        max_retries = dm_config.get("max_retries", DEFAULT_MAX_RETRIES)
        retry_delay = dm_config.get("retry_delay", DEFAULT_RETRY_DELAY)
        
        # 构建多人行动描述
        action_lines = []
        for act in actions:
            action_lines.append(f"【{act['character_name']}】{act['action']}")
        
        combined_message = "\n".join(action_lines)
        
        # 发送行动汇总
        await self.send_text(stream_id, f"📋 本轮行动汇总：\n{combined_message}\n\n🎲 DM 正在处理...")
        
        response = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = await _dm_engine.generate_batch_dm_response(
                    session=session,
                    actions=actions,
                    config=_plugin_config,
                )
                if response:
                    break
            except Exception as e:
                last_error = e
                logger.warning(f"[TRPGHandler] 批量 DM 响应生成失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
        
        if response:
            # 解析所有玩家的状态变化
            all_change_summaries = []
            for act in actions:
                act_player = await _storage.get_player(stream_id, act["user_id"])
                state_changes = _dm_engine.parse_state_changes(response, act_player)
                if state_changes.has_changes():
                    change_summary = await _dm_engine.apply_state_changes(
                        state_changes, session, _storage
                    )
                    if change_summary:
                        all_change_summaries.append(change_summary)
            
            # 清理响应中的状态标签
            clean_response = _dm_engine.clean_state_tags(response)
            
            session.add_history("dm", f"[多人回合]\n{clean_response}")
            
            # 更新张力等级
            _dm_engine.update_tension_level(clean_response, session)
            
            # 检查是否需要更新剧情摘要
            if await _dm_engine.should_update_summary(session):
                await _dm_engine.update_story_summary(session)
            
            await _storage.save_session(session)
            
            # 发送响应（如果有状态变化，附加变化摘要）
            if all_change_summaries:
                combined_changes = "\n".join(all_change_summaries)
                await self.send_text(stream_id, f"{clean_response}\n\n━━━ 状态变化 ━━━\n{combined_changes}")
            else:
                await self.send_text(stream_id, clean_response)
            
            # 检测高潮场景，自动生成图片
            await self._check_and_generate_climax_image(stream_id, session, clean_response)
        else:
            logger.error(f"[TRPGHandler] 批量 DM 响应生成失败: {last_error}")
            await self.send_text(stream_id, "⚠️ DM 思考中遇到了问题，请稍后再试...")

    def _generate_action_acknowledgment(self, text: str, character_name: str) -> str:
        """生成动作确认反馈，包含检定提示"""
        text_lower = text.lower()
        
        # 检查动作格式（角色扮演格式）
        if text.startswith("*") and text.endswith("*"):
            action = text[1:-1].strip()
            check_hint = self._get_check_hint(action)
            return f"🎭 {character_name}: *{action}*{check_hint}"
        
        if text.startswith("（") and text.endswith("）"):
            action = text[1:-1].strip()
            check_hint = self._get_check_hint(action)
            return f"🎭 {character_name}: （{action}）{check_hint}"
        
        if text.startswith("(") and text.endswith(")"):
            action = text[1:-1].strip()
            check_hint = self._get_check_hint(action)
            return f"🎭 {character_name}: ({action}){check_hint}"
        
        # 需要检定的动作类型（带检定提示）
        check_actions = {
            ("搜索", "调查", "检查", "查看", "观察", "寻找", "翻找"): ("🔍", "感知检定", "d20"),
            ("攻击", "战斗", "打", "砍", "刺"): ("⚔️", "攻击检定", "d20"),
            ("说服", "劝说", "欺骗", "撒谎", "威胁", "恐吓"): ("💬", "魅力检定", "d20"),
            ("跳", "爬", "翻", "躲", "闪", "滚"): ("🤸", "敏捷检定", "d20"),
            ("推", "拉", "举", "砸", "破门", "撞"): ("💪", "力量检定", "d20"),
            ("回忆", "分析", "推理", "识破", "辨认"): ("🧠", "智力检定", "d20"),
            ("潜行", "隐藏", "躲藏", "偷偷", "悄悄"): ("🫥", "隐匿检定", "d20"),
            ("开锁", "撬", "拆", "修理", "解除"): ("🔧", "巧手检定", "d20"),
        }
        
        for keywords, (emoji, check_name, dice) in check_actions.items():
            if any(kw in text_lower for kw in keywords):
                short_action = text[:25] + ("..." if len(text) > 25 else "")
                return f"{emoji} {character_name} 尝试: {short_action}\n🎲 需要{check_name} `/r {dice}`"
        
        # 不需要检定的简单动作
        simple_actions = {
            ("打开", "开门"): "🚪",
            ("拿", "捡", "获取"): "🤲",
            ("走向", "前往", "进入", "离开", "移动"): "🚶",
            ("使用"): "✨",
            ("逃跑", "逃"): "🏃",
            ("施法", "魔法"): "🪄",
            ("说", "问", "告诉", "询问", "回答", "对话"): "💬",
        }
        
        for keywords, emoji in simple_actions.items():
            if any(kw in text_lower for kw in keywords):
                short_action = text[:30] + ("..." if len(text) > 30 else "")
                return f"{emoji} {character_name}: {short_action}"
        
        # 默认反馈
        short_action = text[:30] + ("..." if len(text) > 30 else "")
        return f"🎲 {character_name}: {short_action}"

    def _get_check_hint(self, action: str) -> str:
        """根据动作内容返回检定提示"""
        action_lower = action.lower()
        
        check_mappings = [
            (["搜索", "调查", "检查", "查看", "观察", "寻找"], "感知检定", "d20"),
            (["攻击", "战斗", "打", "砍", "刺"], "攻击检定", "d20"),
            (["说服", "劝说", "欺骗", "威胁"], "魅力检定", "d20"),
            (["跳", "爬", "翻", "躲", "闪"], "敏捷检定", "d20"),
            (["推", "拉", "举", "砸", "破"], "力量检定", "d20"),
            (["回忆", "分析", "推理", "识破"], "智力检定", "d20"),
            (["潜行", "隐藏", "躲藏", "偷偷"], "隐匿检定", "d20"),
            (["开锁", "撬", "拆", "修理"], "巧手检定", "d20"),
        ]
        
        for keywords, check_name, dice in check_mappings:
            if any(kw in action_lower for kw in keywords):
                return f"\n🎲 需要{check_name} `/r {dice}`"
        
        return ""

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
