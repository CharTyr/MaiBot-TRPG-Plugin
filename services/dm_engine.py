"""
DM 引擎 - 负责剧情生成、NPC 扮演、环境描述等核心 DM 功能
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from src.plugin_system.apis import llm_api
from src.common.logger import get_logger

if TYPE_CHECKING:
    from ..models.session import TRPGSession, HistoryEntry
    from ..models.player import Player

logger = get_logger("trpg_dm_engine")


class DMEngine:
    """DM 引擎 - 跑团的核心大脑"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temperature = config.get("dm", {}).get("llm_temperature", 0.8)
        self.max_tokens = config.get("dm", {}).get("llm_max_tokens", 1000)
        self.auto_narrative = config.get("dm", {}).get("auto_narrative", True)
        self.npc_style = config.get("dm", {}).get("npc_style", "immersive")

    async def generate_narrative(
        self,
        session: "TRPGSession",
        player_action: str,
        player: Optional["Player"] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        生成剧情叙述
        
        Args:
            session: 当前会话
            player_action: 玩家的行动描述
            player: 执行行动的玩家
            context: 额外上下文
        
        Returns:
            DM 的叙述响应
        """
        # 构建提示词
        prompt = self._build_narrative_prompt(session, player_action, player, context)
        
        try:
            # 获取可用模型
            models = llm_api.get_available_models()
            model_config = models.get("normal_chat") or models.get("default") or list(models.values())[0]
            
            success, response, reasoning, model_name = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.narrative",
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            if success and response:
                logger.debug(f"[DMEngine] 生成叙述成功，使用模型: {model_name}")
                return response.strip()
            else:
                logger.warning(f"[DMEngine] 生成叙述失败: {response}")
                return self._get_fallback_narrative(player_action)
                
        except Exception as e:
            logger.error(f"[DMEngine] 生成叙述时出错: {e}")
            return self._get_fallback_narrative(player_action)

    async def generate_npc_dialogue(
        self,
        session: "TRPGSession",
        npc_name: str,
        player_message: str,
        player: Optional["Player"] = None,
    ) -> str:
        """
        生成 NPC 对话
        
        Args:
            session: 当前会话
            npc_name: NPC 名称
            player_message: 玩家对 NPC 说的话
            player: 说话的玩家
        
        Returns:
            NPC 的回复
        """
        npc = session.npcs.get(npc_name)
        prompt = self._build_npc_prompt(session, npc_name, npc, player_message, player)
        
        try:
            models = llm_api.get_available_models()
            model_config = models.get("normal_chat") or list(models.values())[0]
            
            success, response, _, _ = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.npc_dialogue",
                temperature=self.temperature,
                max_tokens=500,
            )
            
            if success and response:
                return f"【{npc_name}】: {response.strip()}"
            else:
                return f"【{npc_name}】沉默不语..."
                
        except Exception as e:
            logger.error(f"[DMEngine] 生成NPC对话时出错: {e}")
            return f"【{npc_name}】似乎没有听清你说的话..."

    async def describe_environment(self, session: "TRPGSession") -> str:
        """
        描述当前环境
        
        Args:
            session: 当前会话
        
        Returns:
            环境描述
        """
        world_state = session.world_state
        
        prompt = f"""你是一个专业的 TRPG 游戏主持人(DM)。请根据以下信息，生成一段生动的环境描述。

世界观: {session.world_name}
当前位置: {world_state.location}
时间: {world_state.time_of_day}
天气: {world_state.weather}
位置描述: {world_state.location_description or "未知"}

世界观设定:
{chr(10).join(session.lore[:5]) if session.lore else "暂无特殊设定"}

请用2-3句话描述当前的环境氛围，要有画面感和沉浸感。不要使用第一人称，使用第三人称叙述。"""

        try:
            models = llm_api.get_available_models()
            model_config = models.get("normal_chat") or list(models.values())[0]
            
            success, response, _, _ = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.environment",
                temperature=0.7,
                max_tokens=300,
            )
            
            if success and response:
                return f"🌍 {response.strip()}"
            else:
                return f"🌍 {world_state.get_description()}"
                
        except Exception as e:
            logger.error(f"[DMEngine] 生成环境描述时出错: {e}")
            return f"🌍 {world_state.get_description()}"

    async def interpret_player_intent(
        self,
        message: str,
        session: "TRPGSession",
        player: Optional["Player"] = None,
    ) -> Dict[str, Any]:
        """
        解析玩家意图
        
        Args:
            message: 玩家消息
            session: 当前会话
            player: 玩家信息
        
        Returns:
            解析结果，包含意图类型和相关信息
        """
        # 简单的意图识别（可以后续用 LLM 增强）
        message_lower = message.lower()
        
        # 检测常见意图
        if any(word in message_lower for word in ["攻击", "打", "砍", "刺", "射"]):
            return {"intent": "combat", "action": "attack", "target": self._extract_target(message)}
        
        if any(word in message_lower for word in ["说", "问", "告诉", "询问"]):
            return {"intent": "dialogue", "target": self._extract_target(message)}
        
        if any(word in message_lower for word in ["走", "去", "前往", "移动", "进入"]):
            return {"intent": "movement", "destination": self._extract_location(message)}
        
        if any(word in message_lower for word in ["检查", "查看", "观察", "搜索", "调查"]):
            return {"intent": "investigate", "target": self._extract_target(message)}
        
        if any(word in message_lower for word in ["使用", "用", "拿出"]):
            return {"intent": "use_item", "item": self._extract_item(message)}
        
        # 默认为角色扮演行动
        return {"intent": "roleplay", "action": message}

    def _build_narrative_prompt(
        self,
        session: "TRPGSession",
        player_action: str,
        player: Optional["Player"],
        context: Optional[str],
    ) -> str:
        """构建叙述生成的提示词"""
        # 获取最近的历史记录
        recent_history = session.get_recent_history(5)
        history_text = "\n".join([
            f"[{h.entry_type}] {h.character_name or '系统'}: {h.content}"
            for h in recent_history
        ])
        
        player_info = ""
        if player:
            player_info = f"""
玩家角色: {player.character_name}
HP: {player.hp_current}/{player.hp_max}
"""
        
        prompt = f"""你是一个专业的 TRPG 游戏主持人(DM)，正在主持一场 {session.world_name} 世界观的跑团游戏。

当前场景:
- 位置: {session.world_state.location}
- 时间: {session.world_state.time_of_day}
- 天气: {session.world_state.weather}
{player_info}

最近的游戏记录:
{history_text if history_text else "游戏刚刚开始"}

世界观设定:
{chr(10).join(session.lore[:3]) if session.lore else "通用奇幻世界设定"}

{f"额外上下文: {context}" if context else ""}

玩家行动: {player_action}

请作为 DM 回应玩家的行动。要求:
1. 描述行动的结果和场景变化
2. 如果涉及 NPC，描述 NPC 的反应
3. 保持叙述的沉浸感和戏剧性
4. 如果需要掷骰子判定，说明需要什么检定
5. 回复控制在100字以内
6. 使用第三人称叙述"""

        return prompt

    def _build_npc_prompt(
        self,
        session: "TRPGSession",
        npc_name: str,
        npc: Optional[Any],
        player_message: str,
        player: Optional["Player"],
    ) -> str:
        """构建 NPC 对话的提示词"""
        npc_info = ""
        if npc:
            npc_info = f"""
NPC 状态: {npc.status}
NPC 态度: {npc.attitude}
NPC 描述: {npc.description}
"""
        
        player_name = player.character_name if player else "冒险者"
        
        prompt = f"""你现在扮演一个名叫 {npc_name} 的 NPC 角色。

世界观: {session.world_name}
当前场景: {session.world_state.location}
{npc_info}

{player_name} 对你说: "{player_message}"

请以 {npc_name} 的身份回复。要求:
1. 保持角色性格一致
2. 回复要符合世界观设定
3. 回复控制在50字以内
4. 只输出对话内容，不要加引号或角色名前缀"""

        return prompt

    def _get_fallback_narrative(self, player_action: str) -> str:
        """获取备用叙述（当 LLM 不可用时）"""
        return f"你尝试{player_action}...结果如何，需要 DM 来判定。"

    def _extract_target(self, message: str) -> Optional[str]:
        """从消息中提取目标"""
        # 简单实现，可以后续增强
        return None

    def _extract_location(self, message: str) -> Optional[str]:
        """从消息中提取位置"""
        return None

    def _extract_item(self, message: str) -> Optional[str]:
        """从消息中提取物品"""
        return None

    async def generate_session_intro(self, session: "TRPGSession") -> str:
        """生成会话开场白"""
        prompt = f"""你是一个专业的 TRPG 游戏主持人(DM)。一场新的冒险即将开始。

世界观: {session.world_name}
起始位置: {session.world_state.location}
时间: {session.world_state.time_of_day}
天气: {session.world_state.weather}

世界观设定:
{chr(10).join(session.lore[:3]) if session.lore else "这是一个充满魔法与冒险的奇幻世界"}

请生成一段引人入胜的开场白，介绍这个世界和冒险的开始。要求:
1. 营造氛围感
2. 暗示可能的冒险方向
3. 控制在150字以内"""

        try:
            models = llm_api.get_available_models()
            model_config = models.get("normal_chat") or list(models.values())[0]
            
            success, response, _, _ = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_config,
                request_type="trpg.intro",
                temperature=0.9,
                max_tokens=300,
            )
            
            if success and response:
                return f"📖 {response.strip()}"
            
        except Exception as e:
            logger.error(f"[DMEngine] 生成开场白时出错: {e}")
        
        # 备用开场白
        return f"""📖 欢迎来到 {session.world_name}！

{session.world_state.get_description()}

冒险即将开始，勇敢的冒险者们，准备好了吗？

输入 /join [角色名] 加入冒险！"""
