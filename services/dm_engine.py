"""
DM 引擎 - 负责剧情生成、NPC 扮演、环境描述等核心 DM 功能
深度融合 MaiBot 的 replyer 系统
"""

import re
import json
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from src.plugin_system.apis import llm_api
from src.common.logger import get_logger

if TYPE_CHECKING:
    from ..models.session import TRPGSession, HistoryEntry
    from ..models.player import Player

logger = get_logger("trpg_dm_engine")


class GameStateChange:
    """游戏状态变化记录"""
    
    def __init__(self):
        self.hp_changes: Dict[str, int] = {}  # user_id -> delta
        self.mp_changes: Dict[str, int] = {}  # user_id -> delta
        self.attr_changes: Dict[str, Dict[str, int]] = {}  # user_id -> {attr: delta}
        self.item_gains: Dict[str, List[Tuple[str, int]]] = {}  # user_id -> [(item, qty)]
        self.item_losses: Dict[str, List[Tuple[str, int]]] = {}  # user_id -> [(item, qty)]
        self.world_changes: Dict[str, Any] = {}  # location, time, weather, etc.
        self.npc_changes: Dict[str, Dict[str, Any]] = {}  # npc_name -> changes
    
    def has_changes(self) -> bool:
        return bool(
            self.hp_changes or self.mp_changes or self.attr_changes or
            self.item_gains or self.item_losses or self.world_changes or
            self.npc_changes
        )
    
    def get_summary(self) -> str:
        """获取变化摘要"""
        lines = []
        
        for user_id, delta in self.hp_changes.items():
            sign = "+" if delta > 0 else ""
            lines.append(f"❤️ HP {sign}{delta}")
        
        for user_id, delta in self.mp_changes.items():
            sign = "+" if delta > 0 else ""
            lines.append(f"💙 MP {sign}{delta}")
        
        for user_id, attrs in self.attr_changes.items():
            for attr, delta in attrs.items():
                sign = "+" if delta > 0 else ""
                lines.append(f"📊 {attr} {sign}{delta}")
        
        for user_id, items in self.item_gains.items():
            for item, qty in items:
                lines.append(f"🎒 获得 {item} x{qty}")
        
        for user_id, items in self.item_losses.items():
            for item, qty in items:
                lines.append(f"🎒 失去 {item} x{qty}")
        
        if self.world_changes.get("location"):
            lines.append(f"📍 移动到: {self.world_changes['location']}")
        
        return "\n".join(lines) if lines else ""


class DMEngine:
    """DM 引擎 - 跑团的核心大脑，融合 MaiBot 人格"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.dm_config = config.get("dm", {})
        self.temperature = self.dm_config.get("llm_temperature", 0.8)
        self.max_tokens = self.dm_config.get("llm_max_tokens", 800)
        self.auto_narrative = self.dm_config.get("auto_narrative", True)
        self.npc_style = self.dm_config.get("npc_style", "immersive")
        self.dm_personality = self.dm_config.get("dm_personality", "")
        self.include_hints = self.dm_config.get("include_action_hints", True)
        
        # 融合配置
        self.integration_config = config.get("integration", {})
        self.use_maibot_replyer = self.dm_config.get("use_maibot_replyer", True)
        self.merge_personality = self.integration_config.get("merge_bot_personality", True)
        
        # 图片配置
        self.image_config = config.get("image", {})
        self.auto_image_enabled = self.image_config.get("auto_generate", False)
        self.auto_image_interval = self.image_config.get("auto_generate_interval", 10)
        self.climax_image_enabled = self.image_config.get("climax_auto_image", True)
        
        # 状态变化解析模式
        self.state_change_patterns = {
            # HP 变化: [HP -5] [HP +10] [生命值 -3]
            "hp": re.compile(r'\[(?:HP|生命值?|hp)\s*([+-]?\d+)\]', re.IGNORECASE),
            # MP 变化: [MP -5] [MP +10] [魔力值 -3]
            "mp": re.compile(r'\[(?:MP|魔力值?|mp)\s*([+-]?\d+)\]', re.IGNORECASE),
            # 获得物品: [获得 钥匙] [获得 金币 x10]
            "item_gain": re.compile(r'\[获得\s+([^\]]+?)(?:\s*[xX×]\s*(\d+))?\]'),
            # 失去物品: [失去 钥匙] [消耗 药水 x2]
            "item_loss": re.compile(r'\[(?:失去|消耗|使用)\s+([^\]]+?)(?:\s*[xX×]\s*(\d+))?\]'),
            # 属性变化: [力量 +2] [敏捷 -1]
            "attr": re.compile(r'\[(?:力量|敏捷|体质|智力|感知|魅力|STR|DEX|CON|INT|WIS|CHA)\s*([+-]?\d+)\]', re.IGNORECASE),
            # 位置变化: [移动到 图书馆] [进入 地下室]
            "location": re.compile(r'\[(?:移动到|进入|来到|到达)\s+([^\]]+)\]'),
            # 时间变化: [时间 夜晚] [时间流逝 2小时]
            "time": re.compile(r'\[时间\s+([^\]]+)\]'),
        }
        
        # 高潮关键词（用于检测剧情高潮）
        self.climax_keywords = [
            # 战斗高潮
            "致命一击", "最后一击", "倒下", "死亡", "击败", "胜利", "战斗结束",
            # 剧情高潮
            "真相", "揭露", "发现", "震惊", "原来", "终于", "秘密",
            # 转折
            "突然", "意外", "惊讶", "不可思议", "转折",
            # 情感高潮
            "感动", "泪水", "拥抱", "告别", "重逢",
            # 危机
            "危险", "紧急", "爆炸", "崩塌", "逃跑",
        ]

    def parse_state_changes(
        self, 
        dm_response: str, 
        player: Optional["Player"] = None
    ) -> GameStateChange:
        """
        从 DM 响应中解析状态变化
        
        支持的格式:
        - [HP -5] [HP +10] - HP 变化
        - [MP -3] [MP +5] - MP 变化
        - [获得 钥匙] [获得 金币 x10] - 获得物品
        - [失去 钥匙] [消耗 药水 x2] - 失去物品
        - [力量 +2] [敏捷 -1] - 属性变化
        - [移动到 图书馆] - 位置变化
        """
        changes = GameStateChange()
        user_id = player.user_id if player else "unknown"
        
        # 解析 HP 变化
        hp_matches = self.state_change_patterns["hp"].findall(dm_response)
        for match in hp_matches:
            delta = int(match)
            changes.hp_changes[user_id] = changes.hp_changes.get(user_id, 0) + delta
        
        # 解析 MP 变化
        mp_matches = self.state_change_patterns["mp"].findall(dm_response)
        for match in mp_matches:
            delta = int(match)
            changes.mp_changes[user_id] = changes.mp_changes.get(user_id, 0) + delta
        
        # 解析获得物品
        item_gain_matches = self.state_change_patterns["item_gain"].findall(dm_response)
        for match in item_gain_matches:
            item_name = match[0].strip()
            qty = int(match[1]) if match[1] else 1
            if user_id not in changes.item_gains:
                changes.item_gains[user_id] = []
            changes.item_gains[user_id].append((item_name, qty))
        
        # 解析失去物品
        item_loss_matches = self.state_change_patterns["item_loss"].findall(dm_response)
        for match in item_loss_matches:
            item_name = match[0].strip()
            qty = int(match[1]) if match[1] else 1
            if user_id not in changes.item_losses:
                changes.item_losses[user_id] = []
            changes.item_losses[user_id].append((item_name, qty))
        
        # 解析属性变化
        attr_pattern = re.compile(
            r'\[(力量|敏捷|体质|智力|感知|魅力|STR|DEX|CON|INT|WIS|CHA)\s*([+-]?\d+)\]', 
            re.IGNORECASE
        )
        attr_matches = attr_pattern.findall(dm_response)
        for attr_name, delta_str in attr_matches:
            delta = int(delta_str)
            if user_id not in changes.attr_changes:
                changes.attr_changes[user_id] = {}
            # 标准化属性名
            attr_map = {
                "力量": "strength", "str": "strength",
                "敏捷": "dexterity", "dex": "dexterity",
                "体质": "constitution", "con": "constitution",
                "智力": "intelligence", "int": "intelligence",
                "感知": "wisdom", "wis": "wisdom",
                "魅力": "charisma", "cha": "charisma",
            }
            std_attr = attr_map.get(attr_name.lower(), attr_name.lower())
            changes.attr_changes[user_id][std_attr] = delta
        
        # 解析位置变化
        location_matches = self.state_change_patterns["location"].findall(dm_response)
        if location_matches:
            changes.world_changes["location"] = location_matches[-1].strip()
        
        # 解析时间变化
        time_matches = self.state_change_patterns["time"].findall(dm_response)
        if time_matches:
            changes.world_changes["time"] = time_matches[-1].strip()
        
        return changes

    async def apply_state_changes(
        self,
        changes: GameStateChange,
        session: "TRPGSession",
        storage: Any,  # StorageManager
    ) -> str:
        """
        应用状态变化到玩家和会话
        
        Returns:
            变化摘要文本
        """
        applied_changes = []
        
        # 应用 HP 变化
        for user_id, delta in changes.hp_changes.items():
            player = await storage.get_player(session.stream_id, user_id)
            if player:
                old_hp, new_hp = player.modify_hp(delta)
                await storage.save_player(player)
                sign = "+" if delta > 0 else ""
                applied_changes.append(
                    f"❤️ {player.character_name} HP: {old_hp} → {new_hp} ({sign}{delta})"
                )
                logger.info(f"[DMEngine] 应用 HP 变化: {player.character_name} {sign}{delta}")
        
        # 应用 MP 变化
        for user_id, delta in changes.mp_changes.items():
            player = await storage.get_player(session.stream_id, user_id)
            if player:
                old_mp, new_mp = player.modify_mp(delta)
                await storage.save_player(player)
                sign = "+" if delta > 0 else ""
                applied_changes.append(
                    f"💙 {player.character_name} MP: {old_mp} → {new_mp} ({sign}{delta})"
                )
                logger.info(f"[DMEngine] 应用 MP 变化: {player.character_name} {sign}{delta}")
        
        # 应用属性变化
        for user_id, attrs in changes.attr_changes.items():
            player = await storage.get_player(session.stream_id, user_id)
            if player:
                for attr_name, delta in attrs.items():
                    old_val = player.attributes.get_attribute(attr_name)
                    new_val = old_val + delta
                    player.attributes.set_attribute(attr_name, new_val)
                    sign = "+" if delta > 0 else ""
                    applied_changes.append(
                        f"📊 {player.character_name} {attr_name}: {old_val} → {new_val} ({sign}{delta})"
                    )
                    logger.info(f"[DMEngine] 应用属性变化: {player.character_name} {attr_name} {sign}{delta}")
                await storage.save_player(player)
        
        # 应用物品获得
        for user_id, items in changes.item_gains.items():
            player = await storage.get_player(session.stream_id, user_id)
            if player:
                for item_name, qty in items:
                    player.add_item(item_name, qty)
                    applied_changes.append(
                        f"🎒 {player.character_name} 获得: {item_name} x{qty}"
                    )
                    logger.info(f"[DMEngine] 物品获得: {player.character_name} +{item_name} x{qty}")
                await storage.save_player(player)
        
        # 应用物品失去
        for user_id, items in changes.item_losses.items():
            player = await storage.get_player(session.stream_id, user_id)
            if player:
                for item_name, qty in items:
                    removed = player.remove_item(item_name, qty)
                    if removed:
                        applied_changes.append(
                            f"🎒 {player.character_name} 失去: {item_name} x{qty}"
                        )
                        logger.info(f"[DMEngine] 物品失去: {player.character_name} -{item_name} x{qty}")
                await storage.save_player(player)
        
        # 应用世界状态变化
        if changes.world_changes.get("location"):
            old_location = session.world_state.location
            session.world_state.location = changes.world_changes["location"]
            applied_changes.append(
                f"📍 位置变化: {old_location} → {session.world_state.location}"
            )
            logger.info(f"[DMEngine] 位置变化: {session.world_state.location}")
        
        if changes.world_changes.get("time"):
            session.world_state.time_of_day = changes.world_changes["time"]
            applied_changes.append(f"🕐 时间变化: {session.world_state.time_of_day}")
        
        # 保存会话
        if changes.world_changes:
            await storage.save_session(session)
        
        return "\n".join(applied_changes) if applied_changes else ""

    def clean_state_tags(self, response: str) -> str:
        """从响应中移除状态变化标签，保留纯叙述文本"""
        # 移除所有 [...] 格式的状态标签
        patterns = [
            r'\[(?:HP|生命值?|hp)\s*[+-]?\d+\]',
            r'\[(?:MP|魔力值?|mp)\s*[+-]?\d+\]',
            r'\[获得\s+[^\]]+\]',
            r'\[(?:失去|消耗|使用)\s+[^\]]+\]',
            r'\[(?:力量|敏捷|体质|智力|感知|魅力|STR|DEX|CON|INT|WIS|CHA)\s*[+-]?\d+\]',
            r'\[(?:移动到|进入|来到|到达)\s+[^\]]+\]',
            r'\[时间\s+[^\]]+\]',
        ]
        
        cleaned = response
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # 清理多余的空格和换行
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        cleaned = re.sub(r'  +', ' ', cleaned)
        
        return cleaned.strip()

    def detect_climax(self, dm_response: str, session: "TRPGSession") -> bool:
        """
        检测 DM 响应是否包含剧情高潮
        
        Returns:
            True 如果检测到高潮场景
        """
        if not self.climax_image_enabled:
            return False
        
        # 检查关键词
        response_lower = dm_response.lower()
        keyword_count = sum(1 for kw in self.climax_keywords if kw in response_lower)
        
        # 检查张力等级
        tension = session.story_context.tension_level
        
        # 检查距离上次生成图片的历史条数
        history_since_last_image = len(session.history) - session.story_context.last_image_history_index
        
        # 高潮判定条件：
        # 1. 关键词数量 >= 2
        # 2. 或者张力等级 >= 7 且有至少1个关键词
        # 3. 且距离上次图片至少5条历史
        if history_since_last_image < 5:
            return False
        
        if keyword_count >= 2:
            logger.info(f"[DMEngine] 检测到剧情高潮（关键词: {keyword_count}）")
            return True
        
        if tension >= 7 and keyword_count >= 1:
            logger.info(f"[DMEngine] 检测到剧情高潮（张力: {tension}, 关键词: {keyword_count}）")
            return True
        
        return False

    def update_tension_level(self, dm_response: str, session: "TRPGSession"):
        """根据 DM 响应更新剧情张力等级"""
        response_lower = dm_response.lower()
        
        # 增加张力的关键词
        tension_up_keywords = ["危险", "紧张", "战斗", "敌人", "威胁", "追逐", "陷阱", "黑暗"]
        # 降低张力的关键词
        tension_down_keywords = ["安全", "休息", "平静", "解决", "离开", "结束", "放松"]
        
        up_count = sum(1 for kw in tension_up_keywords if kw in response_lower)
        down_count = sum(1 for kw in tension_down_keywords if kw in response_lower)
        
        # 调整张力
        delta = up_count - down_count
        new_tension = max(0, min(10, session.story_context.tension_level + delta))
        session.story_context.tension_level = new_tension

    async def should_update_summary(self, session: "TRPGSession") -> bool:
        """检查是否需要更新剧情摘要"""
        history_since_last = len(session.history) - session.story_context.last_summary_history_index
        # 每10条历史更新一次摘要
        return history_since_last >= 10

    async def update_story_summary(self, session: "TRPGSession"):
        """更新剧情摘要"""
        recent_history = session.get_recent_history(15)
        if not recent_history:
            return
        
        history_text = "\n".join([
            f"[{h.entry_type}] {h.content[:100]}" for h in recent_history
        ])
        
        prompt = f"""请根据以下跑团历史记录，生成一段简洁的剧情摘要（100字以内）：

世界观: {session.world_name}
当前位置: {session.world_state.location}

历史记录:
{history_text}

要求：
1. 概括主要事件和进展
2. 突出关键转折点
3. 保持客观叙述

只输出摘要，不要其他内容。"""

        try:
            models = llm_api.get_available_models()
            if models:
                model_config = models.get("utils") or models.get("normal_chat") or next(iter(models.values()))
                success, response, _, _ = await llm_api.generate_with_model(
                    prompt=prompt,
                    model_config=model_config,
                    request_type="trpg.summary",
                    temperature=0.5,
                    max_tokens=200,
                )
                if success and response:
                    session.story_context.story_summary = response.strip()
                    session.story_context.last_summary_history_index = len(session.history)
                    logger.info("[DMEngine] 剧情摘要已更新")
        except Exception as e:
            logger.warning(f"[DMEngine] 更新剧情摘要失败: {e}")

    def get_full_context(self, session: "TRPGSession") -> str:
        """获取完整的剧情上下文供 LLM 使用"""
        ctx = session.story_context
        
        parts = []
        
        # 剧情摘要
        if ctx.story_summary:
            parts.append(f"【剧情摘要】\n{ctx.story_summary}")
        
        # 关键事件
        if ctx.key_events:
            recent_events = ctx.key_events[-5:]
            parts.append(f"【近期关键事件】\n" + "\n".join(f"• {e}" for e in recent_events))
        
        # 未解决的谜题
        if ctx.open_threads:
            parts.append(f"【未解之谜】\n" + "\n".join(f"• {t}" for t in ctx.open_threads[:3]))
        
        # 已发现线索
        if ctx.discovered_clues:
            parts.append(f"【已发现线索】\n" + "\n".join(f"• {c}" for c in ctx.discovered_clues[-5:]))
        
        # 当前场景
        if ctx.current_scene:
            parts.append(f"【当前场景】{ctx.current_scene}")
        
        return "\n\n".join(parts) if parts else ""

    async def generate_dm_response(
        self,
        session: "TRPGSession",
        player_message: str,
        player: Optional["Player"] = None,
        config: Optional[Dict] = None,
    ) -> str:
        """
        生成 DM 响应 - 核心方法
        
        融合 MaiBot 的人格设定，生成沉浸式的 DM 回复
        """
        # 构建提示词
        prompt = self._build_dm_prompt(session, player_message, player)
        
        try:
            # 获取模型配置
            models = llm_api.get_available_models()
            if not models:
                logger.error("[DMEngine] 没有可用的 LLM 模型")
                return self._get_fallback_response(player_message)
            
            # 优先使用 replyer 模型（与 MaiBot 主程序一致）
            if self.use_maibot_replyer:
                model_config = models.get("replyer") or models.get("normal_chat") or next(iter(models.values()))
            else:
                model_config = models.get("normal_chat") or models.get("utils") or next(iter(models.values()))
            
            success, response, reasoning, model_name = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.dm_response",
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            if success and response:
                logger.debug(f"[DMEngine] DM 响应生成成功，使用模型: {model_name}")
                return self._format_response(response.strip(), session)
            else:
                logger.warning(f"[DMEngine] DM 响应生成失败: {response}")
                return self._get_fallback_response(player_message)
                
        except Exception as e:
            logger.error(f"[DMEngine] 生成 DM 响应时出错: {e}")
            return self._get_fallback_response(player_message)

    async def generate_batch_dm_response(
        self,
        session: "TRPGSession",
        actions: List[Dict[str, Any]],
        config: Optional[Dict] = None,
    ) -> str:
        """
        生成多人行动的批量 DM 响应
        
        Args:
            session: 跑团会话
            actions: 行动列表 [{user_id, character_name, action, timestamp}]
            config: 配置
            
        Returns:
            统一的 DM 响应
        """
        # 构建多人行动提示词
        prompt = self._build_batch_dm_prompt(session, actions)
        
        try:
            models = llm_api.get_available_models()
            if not models:
                logger.error("[DMEngine] 没有可用的 LLM 模型")
                return self._get_batch_fallback_response(actions)
            
            if self.use_maibot_replyer:
                model_config = models.get("replyer") or models.get("normal_chat") or next(iter(models.values()))
            else:
                model_config = models.get("normal_chat") or next(iter(models.values()))
            
            # 多人响应需要更多 token
            batch_max_tokens = min(self.max_tokens * 2, 1500)
            
            success, response, reasoning, model_name = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.batch_dm_response",
                temperature=self.temperature,
                max_tokens=batch_max_tokens,
            )
            
            if success and response:
                logger.debug(f"[DMEngine] 批量 DM 响应生成成功，使用模型: {model_name}")
                return self._format_batch_response(response.strip(), session, actions)
            else:
                logger.warning(f"[DMEngine] 批量 DM 响应生成失败: {response}")
                return self._get_batch_fallback_response(actions)
                
        except Exception as e:
            logger.error(f"[DMEngine] 生成批量 DM 响应时出错: {e}")
            return self._get_batch_fallback_response(actions)

    def _build_batch_dm_prompt(
        self,
        session: "TRPGSession",
        actions: List[Dict[str, Any]],
    ) -> str:
        """构建多人行动的 DM 提示词"""
        # 获取最近的历史记录
        max_history = self.config.get("session", {}).get("max_history_length", 50)
        recent_history = session.get_recent_history(min(8, max_history))
        
        history_text = ""
        if recent_history:
            history_lines = []
            for h in recent_history[-6:]:
                if h.entry_type == "dm":
                    history_lines.append(f"[DM]: {h.content[:80]}...")
                elif h.entry_type == "player":
                    name = h.character_name or "玩家"
                    history_lines.append(f"[{name}]: {h.content[:50]}")
            history_text = "\n".join(history_lines)
        
        # 构建行动列表
        action_lines = []
        for act in actions:
            action_lines.append(f"• {act['character_name']}: {act['action']}")
        actions_text = "\n".join(action_lines)
        
        # 世界状态
        world = session.world_state
        world_info = f"位置: {world.location} | 时间: {world.time_of_day} | 天气: {world.weather}"
        
        # NPC 信息
        npc_info = ""
        if session.npcs:
            npc_list = [f"{name}({npc.attitude})" for name, npc in list(session.npcs.items())[:5]]
            npc_info = f"场景NPC: {', '.join(npc_list)}"
        
        # DM 人格
        personality = self.dm_personality or "你是一个专业的跑团主持人。"
        
        prompt = f"""【跑团DM系统提示 - 多人回合】
{personality}

当前正在主持: {session.world_name}
{world_info}
{npc_info}

最近的游戏记录:
{history_text if history_text else "(游戏刚开始)"}

---
本轮多位玩家同时行动:
{actions_text}
---

请作为DM统一回应所有玩家的行动。要求:
1. 按顺序描述每位玩家行动的结果（每人30-50字）
2. 描述行动之间的互动和影响
3. 如果行动有冲突或配合，要体现出来
4. 保持叙事连贯，像在讲述一个场景
5. 最后简短描述场景的整体变化
6. 如需检定，指出哪位玩家需要什么检定

格式示例:
【角色A】行动结果描述...
【角色B】行动结果描述...
📍 场景变化: ..."""

        return prompt

    def _format_batch_response(
        self, response: str, session: "TRPGSession", actions: List[Dict]
    ) -> str:
        """格式化批量响应"""
        # 添加回合标记
        player_names = [act["character_name"] for act in actions]
        header = f"🎭 本轮行动结果 ({', '.join(player_names)})\n\n"
        return header + response

    def _get_batch_fallback_response(self, actions: List[Dict]) -> str:
        """获取批量响应的备用响应"""
        lines = ["🎲 本轮行动处理中...\n"]
        for act in actions:
            lines.append(f"• {act['character_name']} 尝试 {act['action'][:20]}...")
        lines.append("\n请稍等，DM正在思考结果。")
        return "\n".join(lines)

    def _build_dm_prompt(
        self,
        session: "TRPGSession",
        player_message: str,
        player: Optional["Player"],
    ) -> str:
        """构建 DM 提示词"""
        # 获取最近的历史记录
        max_history = self.config.get("session", {}).get("max_history_length", 50)
        recent_history = session.get_recent_history(min(10, max_history))
        
        history_text = ""
        if recent_history:
            history_lines = []
            for h in recent_history[-8:]:  # 只取最近8条
                if h.entry_type == "dm":
                    history_lines.append(f"[DM]: {h.content[:100]}...")
                elif h.entry_type == "player":
                    name = h.character_name or "玩家"
                    history_lines.append(f"[{name}]: {h.content}")
                elif h.entry_type == "dice":
                    history_lines.append(f"[骰子]: {h.content}")
            history_text = "\n".join(history_lines)
        
        # 玩家信息
        player_info = ""
        if player:
            player_info = f"""
当前玩家: {player.character_name}
HP: {player.hp_current}/{player.hp_max} | MP: {player.mp_current}/{player.mp_max}
"""
        
        # 世界状态
        world = session.world_state
        world_info = f"位置: {world.location} | 时间: {world.time_of_day} | 天气: {world.weather}"
        
        # NPC 信息
        npc_info = ""
        if session.npcs:
            npc_list = [f"{name}({npc.attitude})" for name, npc in list(session.npcs.items())[:5]]
            npc_info = f"场景NPC: {', '.join(npc_list)}"
        
        # 世界观设定（简化）
        lore_text = ""
        if session.lore:
            lore_text = "世界观要点: " + "; ".join(session.lore[:3])
        
        # 剧情上下文（增强连贯性）
        story_context = self.get_full_context(session)
        
        # DM 人格
        personality = self.dm_personality or "你是一个专业的跑团主持人。"
        
        # 分析玩家行动，判断是否需要检定
        check_hint = self._analyze_action_for_check(player_message)
        
        # 张力等级提示
        tension = session.story_context.tension_level
        tension_hint = ""
        if tension >= 7:
            tension_hint = "\n⚡ 当前剧情张力很高，注意营造紧张氛围！"
        elif tension <= 2:
            tension_hint = "\n🌿 当前氛围平静，可以适当推进剧情或埋下伏笔。"
        
        prompt = f"""【跑团DM系统提示】
{personality}

当前正在主持: {session.world_name}
{world_info}
{player_info}
{npc_info}
{lore_text}
{tension_hint}

{story_context if story_context else ""}

最近的游戏记录:
{history_text if history_text else "(游戏刚开始)"}

---
玩家行动: {player_message}
---

【骰子检定规则】
以下情况必须要求玩家进行骰子检定：
- 🔍 调查/搜索/观察 → 感知检定 `/r d20` (DC 10-15)
- ⚔️ 攻击/战斗 → 攻击检定 `/r d20` + 伤害骰
- 🗣️ 说服/欺骗/威胁 → 魅力检定 `/r d20` (DC 12-18)
- 🤸 跳跃/攀爬/躲避 → 敏捷检定 `/r d20` (DC 10-15)
- 💪 推/拉/破坏 → 力量检定 `/r d20` (DC 12-18)
- 🧠 回忆/分析/识破 → 智力检定 `/r d20` (DC 10-15)
- 🎭 隐藏/潜行 → 隐匿检定 `/r d20` (DC 12-15)
- 🔧 开锁/拆卸/修理 → 巧手检定 `/r d20` (DC 12-18)
{check_hint}

请作为DM回应玩家。要求:
1. 先简短描述玩家开始行动的场景（1-2句）
2. 如果行动有不确定性，必须要求骰子检定，格式：「🎲 请进行XX检定 `/r d20`，DC XX」
3. 如果玩家刚刚进行了检定（历史记录中有骰子结果），根据结果描述成功或失败
4. 保持沉浸感，使用第三人称
5. 不要过度描述，保持简洁（50-100字）

【状态变化标记】
当玩家的状态发生变化时，必须在叙述中使用以下标签（系统会自动解析并应用）：
- HP变化: [HP -5] 或 [HP +10]
- MP变化: [MP -3] 或 [MP +5]
- 获得物品: [获得 物品名] 或 [获得 物品名 x数量]
- 失去物品: [失去 物品名] 或 [消耗 物品名 x数量]
- 属性变化: [力量 +2] 或 [敏捷 -1]
- 位置变化: [移动到 新位置名]

示例: "你被陷阱击中 [HP -5]，但成功找到了一把钥匙 [获得 铜钥匙]。"
注意: 只有在确实发生变化时才添加标签，不要随意添加。"""

        return prompt

    def _analyze_action_for_check(self, message: str) -> str:
        """分析玩家行动，返回建议的检定类型"""
        message_lower = message.lower()
        
        # 检定类型映射
        check_mappings = [
            (["搜索", "调查", "检查", "查看", "观察", "寻找", "翻找"], "→ 建议: 感知检定"),
            (["攻击", "打", "砍", "刺", "射", "战斗", "挥"], "→ 建议: 攻击检定"),
            (["说服", "劝说", "欺骗", "撒谎", "威胁", "恐吓", "谈判"], "→ 建议: 魅力检定"),
            (["跳", "爬", "翻", "躲", "闪", "滚"], "→ 建议: 敏捷检定"),
            (["推", "拉", "举", "砸", "破门", "撞"], "→ 建议: 力量检定"),
            (["回忆", "分析", "推理", "识破", "辨认"], "→ 建议: 智力检定"),
            (["潜行", "隐藏", "躲藏", "偷偷", "悄悄"], "→ 建议: 隐匿检定"),
            (["开锁", "撬", "拆", "修理", "解除"], "→ 建议: 巧手检定"),
        ]
        
        for keywords, suggestion in check_mappings:
            if any(kw in message_lower for kw in keywords):
                return f"\n⚠️ 玩家行动分析 {suggestion}"
        
        return ""

    async def generate_npc_dialogue(
        self,
        session: "TRPGSession",
        npc_name: str,
        player_message: str,
        player: Optional["Player"] = None,
    ) -> str:
        """生成 NPC 对话"""
        npc = session.npcs.get(npc_name)
        
        npc_desc = ""
        if npc:
            npc_desc = f"NPC描述: {npc.description}\n态度: {npc.attitude}"
        
        player_name = player.character_name if player else "冒险者"
        
        prompt = f"""你现在扮演NPC「{npc_name}」。

世界观: {session.world_name}
场景: {session.world_state.location}
{npc_desc}

{player_name}对你说: "{player_message}"

请以{npc_name}的身份回复（30-50字，只输出对话内容）:"""

        try:
            models = llm_api.get_available_models()
            if not models:
                return f"【{npc_name}】..."
            model_config = models.get("replyer") or models.get("normal_chat") or next(iter(models.values()))
            
            success, response, _, _ = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.npc_dialogue",
                temperature=self.temperature,
                max_tokens=200,
            )
            
            if success and response:
                return f"【{npc_name}】{response.strip()}"
            return f"【{npc_name}】..."
                
        except Exception as e:
            logger.error(f"[DMEngine] 生成NPC对话时出错: {e}")
            return f"【{npc_name}】..."

    async def describe_environment(self, session: "TRPGSession") -> str:
        """描述当前环境"""
        world = session.world_state
        
        prompt = f"""请用2-3句话描述以下场景（有画面感，第三人称）:

世界观: {session.world_name}
位置: {world.location}
时间: {world.time_of_day}
天气: {world.weather}
{f"场景描述: {world.location_description}" if world.location_description else ""}"""

        try:
            models = llm_api.get_available_models()
            if not models:
                return f"🌍 {world.get_description()}"
            model_config = models.get("normal_chat") or next(iter(models.values()))
            
            success, response, _, _ = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.environment",
                temperature=0.7,
                max_tokens=200,
            )
            
            if success and response:
                return f"🌍 {response.strip()}"
            return f"🌍 {world.get_description()}"
                
        except Exception as e:
            logger.error(f"[DMEngine] 生成环境描述时出错: {e}")
            return f"🌍 {world.get_description()}"

    async def generate_session_intro(self, session: "TRPGSession") -> str:
        """生成会话开场白"""
        prompt = f"""你是跑团DM。请为以下设定生成一段开场白（80-120字，营造氛围）:

世界观: {session.world_name}
起始位置: {session.world_state.location}
时间: {session.world_state.time_of_day}
天气: {session.world_state.weather}

世界观设定:
{chr(10).join(session.lore[:3]) if session.lore else "奇幻冒险世界"}"""

        try:
            models = llm_api.get_available_models()
            if not models:
                return f"欢迎来到{session.world_name}！冒险即将开始..."
            model_config = models.get("normal_chat") or next(iter(models.values()))
            
            success, response, _, _ = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.intro",
                temperature=0.9,
                max_tokens=250,
            )
            
            if success and response:
                return response.strip()
            
        except Exception as e:
            logger.error(f"[DMEngine] 生成开场白时出错: {e}")
        
        # 备用开场白
        return f"欢迎来到{session.world_name}！冒险即将开始..."

    def _format_response(self, response: str, session: "TRPGSession") -> str:
        """格式化响应"""
        # 添加行动提示
        if self.include_hints and len(response) < 200:
            hints = self._get_action_hints(session)
            if hints:
                response += f"\n\n💡 {hints}"
        return response

    def _get_action_hints(self, session: "TRPGSession") -> str:
        """获取行动提示"""
        hints = []
        
        # 根据场景给出提示
        if session.npcs:
            npc_names = list(session.npcs.keys())[:2]
            hints.append(f"可以与{'/'.join(npc_names)}交谈")
        
        return hints[0] if hints else ""

    def _get_fallback_response(self, player_message: str) -> str:
        """获取备用响应"""
        return f"你尝试{player_message[:20]}...请稍等，DM正在思考结果。"

    async def interpret_player_intent(
        self,
        message: str,
        session: "TRPGSession",
        player: Optional["Player"] = None,
    ) -> Dict[str, Any]:
        """解析玩家意图"""
        message_lower = message.lower()
        
        # 战斗意图
        if any(word in message_lower for word in ["攻击", "打", "砍", "刺", "射", "战斗"]):
            return {"intent": "combat", "action": "attack"}
        
        # 对话意图
        if any(word in message_lower for word in ["说", "问", "告诉", "询问"]):
            return {"intent": "dialogue"}
        
        # 移动意图
        if any(word in message_lower for word in ["走", "去", "前往", "移动", "进入", "离开"]):
            return {"intent": "movement"}
        
        # 调查意图
        if any(word in message_lower for word in ["检查", "查看", "观察", "搜索", "调查"]):
            return {"intent": "investigate"}
        
        # 使用物品
        if any(word in message_lower for word in ["使用", "用", "拿出"]):
            return {"intent": "use_item"}
        
        return {"intent": "roleplay", "action": message}

    async def generate_recap(
        self,
        session: "TRPGSession",
        max_history: int = 10,
    ) -> str:
        """
        生成存档加载后的前情回顾
        
        Args:
            session: 跑团会话
            max_history: 用于生成回顾的最大历史条数
            
        Returns:
            前情回顾文本
        """
        # 获取最近的历史记录
        recent_history = session.get_recent_history(max_history)
        
        if not recent_history:
            # 没有历史记录，返回简单的状态描述
            world = session.world_state
            return f"""📖 前情回顾

🌍 世界观: {session.world_name}
📍 当前位置: {world.location}
🕐 时间: {world.time_of_day}
🌤️ 天气: {world.weather}

冒险刚刚开始，一切等待着你去探索..."""
        
        # 构建历史摘要
        history_lines = []
        for h in recent_history:
            if h.entry_type == "dm":
                # DM 叙述，截取关键部分
                content = h.content[:80] + ("..." if len(h.content) > 80 else "")
                history_lines.append(f"📜 {content}")
            elif h.entry_type == "player":
                name = h.character_name or "玩家"
                content = h.content[:50] + ("..." if len(h.content) > 50 else "")
                history_lines.append(f"🎭 {name}: {content}")
            elif h.entry_type == "system":
                history_lines.append(f"⚙️ {h.content}")
        
        history_text = "\n".join(history_lines[-8:])  # 最多显示8条
        
        # 尝试使用 LLM 生成更好的回顾
        try:
            models = llm_api.get_available_models()
            if models:
                model_config = models.get("normal_chat") or next(iter(models.values()))
                
                prompt = f"""请根据以下跑团历史记录，生成一段简洁的前情回顾（50-80字）:

世界观: {session.world_name}
当前位置: {session.world_state.location}

最近发生的事:
{history_text}

要求:
1. 用第三人称叙述
2. 突出关键剧情点
3. 营造氛围感
4. 不要列举，用流畅的叙述"""

                success, response, _, _ = await llm_api.generate_with_model(
                    prompt=prompt,
                    model_config=model_config,
                    request_type="trpg.recap",
                    temperature=0.7,
                    max_tokens=200,
                )
                
                if success and response:
                    world = session.world_state
                    return f"""📖 前情回顾

{response.strip()}

━━━ 当前状态 ━━━
📍 位置: {world.location}
🕐 时间: {world.time_of_day}
🌤️ 天气: {world.weather}"""
        
        except Exception as e:
            logger.warning(f"[DMEngine] 生成前情回顾失败，使用简单回顾: {e}")
        
        # 备用：简单的历史列表
        world = session.world_state
        return f"""📖 前情回顾

🌍 {session.world_name}

最近发生的事:
{history_text}

━━━ 当前状态 ━━━
📍 位置: {world.location}
🕐 时间: {world.time_of_day}
🌤️ 天气: {world.weather}"""
