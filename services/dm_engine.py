"""
DM 引擎 - 负责剧情生成、NPC 扮演、环境描述等核心 DM 功能
深度融合 MaiBot 的 replyer 系统
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from src.plugin_system.apis import llm_api
from src.common.logger import get_logger

if TYPE_CHECKING:
    from ..models.session import TRPGSession, HistoryEntry
    from ..models.player import Player

logger = get_logger("trpg_dm_engine")


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
        
        # DM 人格
        personality = self.dm_personality or "你是一个专业的跑团主持人。"
        
        prompt = f"""【跑团DM系统提示】
{personality}

当前正在主持: {session.world_name}
{world_info}
{player_info}
{npc_info}
{lore_text}

最近的游戏记录:
{history_text if history_text else "(游戏刚开始)"}

---
玩家行动: {player_message}
---

请作为DM回应玩家。要求:
1. 描述行动结果和场景变化（50-100字）
2. 如果涉及NPC，简短描述其反应
3. 保持沉浸感，使用第三人称
4. 如需检定，说明需要什么检定（如"请进行感知检定 /r d20"）
5. 不要过度描述，保持简洁有力"""

        return prompt

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
