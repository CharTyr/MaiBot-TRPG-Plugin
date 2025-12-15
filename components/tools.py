"""
TRPG DM 插件 LLM 工具
"""

from typing import Any, Dict, Optional, TYPE_CHECKING
from src.plugin_system import BaseTool, ToolParamType
from src.common.logger import get_logger

if TYPE_CHECKING:
    from ..models.storage import StorageManager
    from ..services.dice import DiceService

logger = get_logger("trpg_tools")

# 全局引用
_storage: Optional["StorageManager"] = None
_dice_service: Optional["DiceService"] = None


def set_tool_services(storage: "StorageManager", dice: "DiceService"):
    """设置服务引用"""
    global _storage, _dice_service
    _storage = storage
    _dice_service = dice


class RollDiceTool(BaseTool):
    """骰子工具 - 供 LLM 使用"""
    
    name = "roll_dice"
    description = "掷骰子，支持标准骰子表达式如 2d6+3, d20, 3d8-2 等"
    parameters = [
        ("expression", ToolParamType.STRING, "骰子表达式，如 2d6+3, d20, 1d100", True, None),
        ("reason", ToolParamType.STRING, "掷骰原因说明", False, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行掷骰子"""
        if not _dice_service:
            return {"name": self.name, "content": "骰子服务未初始化"}
        
        expression = function_args.get("expression", "d20")
        reason = function_args.get("reason", "")
        
        try:
            result = _dice_service.roll(expression)
            
            content = f"🎲 掷骰: {expression}\n"
            content += f"结果: [{', '.join(str(r) for r in result.rolls)}]"
            if result.modifier:
                content += f" {result.modifier:+d}"
            content += f" = {result.total}"
            
            if result.is_critical:
                content += " (大成功!)"
            elif result.is_fumble:
                content += " (大失败!)"
            
            if reason:
                content = f"[{reason}] {content}"
            
            return {
                "name": self.name,
                "content": content,
                "data": {
                    "total": result.total,
                    "rolls": result.rolls,
                    "is_critical": result.is_critical,
                    "is_fumble": result.is_fumble,
                }
            }
            
        except Exception as e:
            return {"name": self.name, "content": f"掷骰失败: {str(e)}"}


class CheckPlayerStatusTool(BaseTool):
    """查询玩家状态工具"""
    
    name = "check_player_status"
    description = "查询指定玩家的角色状态，包括HP、MP、属性等"
    parameters = [
        ("stream_id", ToolParamType.STRING, "群组/会话ID", True, None),
        ("user_id", ToolParamType.STRING, "玩家用户ID", True, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """查询玩家状态"""
        if not _storage:
            return {"name": self.name, "content": "存储服务未初始化"}
        
        stream_id = function_args.get("stream_id", "")
        user_id = function_args.get("user_id", "")
        
        if not stream_id or not user_id:
            return {"name": self.name, "content": "缺少必要参数"}
        
        player = await _storage.get_player(stream_id, user_id)
        if not player:
            return {"name": self.name, "content": f"未找到玩家 {user_id}"}
        
        return {
            "name": self.name,
            "content": f"玩家 {player.character_name} 的状态:\n"
                      f"HP: {player.hp_current}/{player.hp_max}\n"
                      f"MP: {player.mp_current}/{player.mp_max}\n"
                      f"等级: {player.level}",
            "data": player.to_dict(),
        }


class GetWorldStateTool(BaseTool):
    """获取世界状态工具"""
    
    name = "get_world_state"
    description = "获取当前跑团会话的世界状态，包括时间、天气、位置等"
    parameters = [
        ("stream_id", ToolParamType.STRING, "群组/会话ID", True, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """获取世界状态"""
        if not _storage:
            return {"name": self.name, "content": "存储服务未初始化"}
        
        stream_id = function_args.get("stream_id", "")
        if not stream_id:
            return {"name": self.name, "content": "缺少会话ID"}
        
        session = await _storage.get_session(stream_id)
        if not session:
            return {"name": self.name, "content": "未找到会话"}
        
        world_state = session.world_state
        return {
            "name": self.name,
            "content": f"世界状态:\n"
                      f"位置: {world_state.location}\n"
                      f"时间: {world_state.time_of_day}\n"
                      f"天气: {world_state.weather}\n"
                      f"描述: {world_state.location_description or '无'}",
            "data": world_state.to_dict(),
        }


class ModifyPlayerStatusTool(BaseTool):
    """修改玩家状态工具"""
    
    name = "modify_player_status"
    description = "修改玩家的HP或MP值"
    parameters = [
        ("stream_id", ToolParamType.STRING, "群组/会话ID", True, None),
        ("user_id", ToolParamType.STRING, "玩家用户ID", True, None),
        ("hp_change", ToolParamType.INTEGER, "HP变化量（正数增加，负数减少）", False, None),
        ("mp_change", ToolParamType.INTEGER, "MP变化量（正数增加，负数减少）", False, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """修改玩家状态"""
        if not _storage:
            return {"name": self.name, "content": "存储服务未初始化"}
        
        stream_id = function_args.get("stream_id", "")
        user_id = function_args.get("user_id", "")
        hp_change = function_args.get("hp_change", 0)
        mp_change = function_args.get("mp_change", 0)
        
        if not stream_id or not user_id:
            return {"name": self.name, "content": "缺少必要参数"}
        
        player = await _storage.get_player(stream_id, user_id)
        if not player:
            return {"name": self.name, "content": f"未找到玩家 {user_id}"}
        
        changes = []
        
        if hp_change:
            old_hp, new_hp = player.modify_hp(hp_change)
            changes.append(f"HP: {old_hp} → {new_hp}")
        
        if mp_change:
            old_mp, new_mp = player.modify_mp(mp_change)
            changes.append(f"MP: {old_mp} → {new_mp}")
        
        if changes:
            await _storage.save_player(player)
            return {
                "name": self.name,
                "content": f"已修改 {player.character_name} 的状态:\n" + "\n".join(changes),
            }
        
        return {"name": self.name, "content": "未进行任何修改"}


class SearchLoreTool(BaseTool):
    """搜索世界观设定工具"""
    
    name = "search_lore"
    description = "搜索当前跑团会话的世界观设定"
    parameters = [
        ("stream_id", ToolParamType.STRING, "群组/会话ID", True, None),
        ("keyword", ToolParamType.STRING, "搜索关键词", True, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """搜索世界观设定"""
        if not _storage:
            return {"name": self.name, "content": "存储服务未初始化"}
        
        stream_id = function_args.get("stream_id", "")
        keyword = function_args.get("keyword", "")
        
        if not stream_id or not keyword:
            return {"name": self.name, "content": "缺少必要参数"}
        
        results = await _storage.search_lore(stream_id, keyword)
        
        if results:
            return {
                "name": self.name,
                "content": f"找到 {len(results)} 条相关设定:\n" + "\n".join([f"• {r}" for r in results[:5]]),
                "data": {"results": results},
            }
        
        return {"name": self.name, "content": f"未找到与 '{keyword}' 相关的设定"}
