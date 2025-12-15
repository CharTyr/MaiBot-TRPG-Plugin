"""
TRPG DM 插件命令组件
"""

import re
from typing import Tuple, Optional, TYPE_CHECKING
from src.plugin_system import BaseCommand
from src.common.logger import get_logger

if TYPE_CHECKING:
    from ..models.storage import StorageManager
    from ..services.dice import DiceService
    from ..services.dm_engine import DMEngine
    from ..modules.loader import ModuleLoader

logger = get_logger("trpg_commands")

# 全局引用，由插件主类注入
_storage: Optional["StorageManager"] = None
_dice_service: Optional["DiceService"] = None
_dm_engine: Optional["DMEngine"] = None
_module_loader: Optional["ModuleLoader"] = None


def set_services(storage: "StorageManager", dice: "DiceService", dm: "DMEngine", loader: "ModuleLoader" = None):
    """设置服务引用"""
    global _storage, _dice_service, _dm_engine, _module_loader
    _storage = storage
    _dice_service = dice
    _dm_engine = dm
    _module_loader = loader


class TRPGSessionCommand(BaseCommand):
    """跑团会话管理命令"""
    
    command_name = "trpg_session"
    command_description = "跑团会话管理 - 开始/结束/状态"
    command_pattern = r"^/trpg\s*(start|end|status|save|pause|resume)?(?:\s+(.+))?$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _storage:
            return False, "插件未正确初始化", 0
        
        stream_id = self.message.chat_stream.stream_id
        action = self.matched_groups.get("1", "status") or "status"
        args = self.matched_groups.get("2", "")
        
        if action == "start":
            return await self._start_session(stream_id, args)
        elif action == "end":
            return await self._end_session(stream_id)
        elif action == "status":
            return await self._show_status(stream_id)
        elif action == "save":
            return await self._save_session(stream_id)
        elif action == "pause":
            return await self._pause_session(stream_id)
        elif action == "resume":
            return await self._resume_session(stream_id)
        
        return False, "未知的命令", 0

    async def _start_session(self, stream_id: str, world_name: str) -> Tuple[bool, str, int]:
        """开始新会话"""
        existing = await _storage.get_session(stream_id)
        if existing and existing.is_active():
            return False, "⚠️ 当前群组已有进行中的跑团会话！使用 /trpg end 结束后再开始新的。", 2
        
        world_name = world_name.strip() if world_name else "通用奇幻世界"
        
        # 检查是否是预设模组
        if _module_loader:
            module = _module_loader.load_module(world_name)
            if module:
                # 使用预设模组
                session = await _storage.create_session(stream_id, module.world_name)
                await _module_loader.apply_module_to_session(module, session, _storage)
                
                await self.send_text(f"""🎲 跑团开始！

📚 模组: {module.info.name}
🎭 类型: {module.info.genre} | 难度: {module.info.difficulty}
👥 建议人数: {module.info.player_count} | ⏱️ 预计时长: {module.info.duration}

{module.intro_text}

📋 常用命令:
• /join [角色名] - 加入冒险
• /r [骰子] - 掷骰子 (如 /r 2d6+3)
• /pc show - 查看角色卡
• /module info - 查看模组信息
• /trpg end - 结束跑团""")
                
                return True, f"模组 {module.info.name} 已加载", 2
        
        # 普通会话
        session = await _storage.create_session(stream_id, world_name)
        
        # 生成开场白
        intro = await _dm_engine.generate_session_intro(session)
        session.add_history("system", f"跑团开始: {world_name}")
        await _storage.save_session(session)
        
        await self.send_text(f"""🎲 跑团开始！

世界观: {world_name}
{intro}

📋 常用命令:
• /join [角色名] - 加入冒险
• /r [骰子] - 掷骰子 (如 /r 2d6+3)
• /pc show - 查看角色卡
• /inv - 查看背包
• /module list - 查看可用模组
• /trpg end - 结束跑团""")
        
        return True, "跑团会话已开始", 2

    async def _end_session(self, stream_id: str) -> Tuple[bool, str, int]:
        """结束会话"""
        session = await _storage.get_session(stream_id)
        if not session:
            return False, "⚠️ 当前没有进行中的跑团会话", 2
        
        # 保存最终状态
        session.add_history("system", "跑团结束")
        await _storage.save_session(session)
        await _storage.end_session(stream_id)
        
        await self.send_text("🎲 跑团结束！感谢各位冒险者的参与！\n存档已保存，下次可以继续冒险。")
        return True, "跑团会话已结束", 2

    async def _show_status(self, stream_id: str) -> Tuple[bool, str, int]:
        """显示会话状态"""
        session = await _storage.get_session(stream_id)
        if not session:
            await self.send_text("📋 当前没有进行中的跑团会话\n使用 /trpg start [世界观] 开始新的冒险！")
            return True, None, 2
        
        players = await _storage.get_players_in_session(stream_id)
        player_list = "\n".join([f"  • {p.character_name}" for p in players]) or "  暂无玩家"
        
        status_text = f"""📋 跑团状态

🌍 世界观: {session.world_name}
📍 位置: {session.world_state.location}
🕐 时间: {session.world_state.time_of_day}
🌤️ 天气: {session.world_state.weather}
📊 状态: {session.status}

👥 玩家列表:
{player_list}

📜 历史记录: {len(session.history)} 条"""
        
        await self.send_text(status_text)
        return True, None, 2

    async def _save_session(self, stream_id: str) -> Tuple[bool, str, int]:
        """手动保存"""
        session = await _storage.get_session(stream_id)
        if not session:
            return False, "⚠️ 当前没有进行中的跑团会话", 2
        
        await _storage.save_session(session)
        await self.send_text("💾 存档已保存！")
        return True, "存档已保存", 2

    async def _pause_session(self, stream_id: str) -> Tuple[bool, str, int]:
        """暂停会话"""
        session = await _storage.get_session(stream_id)
        if not session:
            return False, "⚠️ 当前没有进行中的跑团会话", 2
        
        session.status = "paused"
        session.add_history("system", "跑团暂停")
        await _storage.save_session(session)
        
        await self.send_text("⏸️ 跑团已暂停，使用 /trpg resume 继续")
        return True, "跑团已暂停", 2

    async def _resume_session(self, stream_id: str) -> Tuple[bool, str, int]:
        """恢复会话"""
        session = await _storage.get_session(stream_id)
        if not session:
            return False, "⚠️ 当前没有跑团会话", 2
        
        if session.status != "paused":
            return False, "⚠️ 会话未处于暂停状态", 2
        
        session.status = "active"
        session.add_history("system", "跑团继续")
        await _storage.save_session(session)
        
        await self.send_text("▶️ 跑团继续！冒险者们，准备好了吗？")
        return True, "跑团已继续", 2


class DiceRollCommand(BaseCommand):
    """骰子投掷命令"""
    
    command_name = "dice_roll"
    command_description = "掷骰子"
    command_pattern = r"^/r(?:oll)?\s+(.+)$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _dice_service:
            return False, "插件未正确初始化", 0
        
        expression = self.matched_groups.get("1", "d20")
        
        try:
            result = _dice_service.roll(expression)
            await self.send_text(result.get_display())
            
            # 记录到历史
            stream_id = self.message.chat_stream.stream_id
            session = await _storage.get_session(stream_id) if _storage else None
            if session and session.is_active():
                user_id = str(self.message.message_info.user_info.user_id)
                player = await _storage.get_player(stream_id, user_id)
                session.add_history(
                    "dice",
                    f"{expression} = {result.total}",
                    user_id=user_id,
                    character_name=player.character_name if player else None,
                    extra_data={"rolls": result.rolls, "total": result.total}
                )
                await _storage.save_session(session)
            
            return True, None, 2
            
        except Exception as e:
            logger.error(f"掷骰子失败: {e}")
            await self.send_text(f"⚠️ 骰子表达式无效: {expression}")
            return False, str(e), 0


class PlayerJoinCommand(BaseCommand):
    """玩家加入命令"""
    
    command_name = "player_join"
    command_description = "加入跑团"
    command_pattern = r"^/join(?:\s+(.+))?$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _storage:
            return False, "插件未正确初始化", 0
        
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        character_name = self.matched_groups.get("1", "").strip() or "无名冒险者"
        
        session = await _storage.get_session(stream_id)
        if not session or not session.is_active():
            await self.send_text("⚠️ 当前没有进行中的跑团会话")
            return False, "没有活跃会话", 0
        
        # 检查是否已加入
        existing = await _storage.get_player(stream_id, user_id)
        if existing:
            await self.send_text(f"⚠️ 你已经以 {existing.character_name} 的身份加入了冒险！")
            return False, "已加入", 0
        
        # 创建玩家
        player = await _storage.create_player(stream_id, user_id, character_name)
        
        session.add_history("system", f"{character_name} 加入了冒险", user_id=user_id)
        await _storage.save_session(session)
        
        await self.send_text(f"""🎭 欢迎 {character_name} 加入冒险！

{player.get_character_sheet()}

使用 /pc [属性] [值] 来自定义你的角色属性
使用 /pc show 查看完整角色卡""")
        
        return True, f"{character_name} 加入", 2


class PlayerStatusCommand(BaseCommand):
    """玩家状态命令"""
    
    command_name = "player_status"
    command_description = "查看/修改角色状态"
    command_pattern = r"^/pc(?:\s+(show|set|leave))?(?:\s+(\w+))?(?:\s+(\d+))?$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _storage:
            return False, "插件未正确初始化", 0
        
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        
        action = self.matched_groups.get("1", "show") or "show"
        attr_name = self.matched_groups.get("2", "")
        attr_value = self.matched_groups.get("3", "")
        
        player = await _storage.get_player(stream_id, user_id)
        if not player:
            await self.send_text("⚠️ 你还没有加入跑团！使用 /join [角色名] 加入")
            return False, "未加入", 0
        
        if action == "show":
            await self.send_text(player.get_character_sheet())
            return True, None, 2
        
        elif action == "set" and attr_name and attr_value:
            if player.attributes.set_attribute(attr_name, int(attr_value)):
                await _storage.save_player(player)
                await self.send_text(f"✅ 已将 {attr_name} 设置为 {attr_value}")
                return True, None, 2
            else:
                await self.send_text(f"⚠️ 未知属性: {attr_name}")
                return False, "未知属性", 0
        
        elif action == "leave":
            await _storage.delete_player(stream_id, user_id)
            await self.send_text(f"👋 {player.character_name} 离开了冒险...")
            return True, "离开", 2
        
        await self.send_text("⚠️ 命令格式错误\n用法: /pc show | /pc set [属性] [值] | /pc leave")
        return False, "格式错误", 0


class InventoryCommand(BaseCommand):
    """背包管理命令"""
    
    command_name = "inventory"
    command_description = "背包管理"
    command_pattern = r"^/inv(?:\s+(add|remove|use))?(?:\s+(.+?))?(?:\s+(\d+))?$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _storage:
            return False, "插件未正确初始化", 0
        
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        
        action = self.matched_groups.get("1", "")
        item_name = self.matched_groups.get("2", "").strip()
        quantity = int(self.matched_groups.get("3", "1") or "1")
        
        player = await _storage.get_player(stream_id, user_id)
        if not player:
            await self.send_text("⚠️ 你还没有加入跑团！")
            return False, "未加入", 0
        
        if not action:
            # 显示背包
            await self.send_text(player.get_inventory_display())
            return True, None, 2
        
        if action == "add" and item_name:
            player.add_item(item_name, quantity)
            await _storage.save_player(player)
            await self.send_text(f"✅ 获得了 {item_name} x{quantity}")
            return True, None, 2
        
        elif action == "remove" and item_name:
            removed = player.remove_item(item_name, quantity)
            if removed:
                await _storage.save_player(player)
                await self.send_text(f"✅ 移除了 {item_name} x{quantity}")
                return True, None, 2
            else:
                await self.send_text(f"⚠️ 背包中没有 {item_name}")
                return False, "物品不存在", 0
        
        elif action == "use" and item_name:
            item = player.get_item(item_name)
            if item:
                player.remove_item(item_name, 1)
                await _storage.save_player(player)
                await self.send_text(f"✨ 使用了 {item_name}！")
                return True, None, 2
            else:
                await self.send_text(f"⚠️ 背包中没有 {item_name}")
                return False, "物品不存在", 0
        
        await self.send_text("⚠️ 命令格式错误\n用法: /inv | /inv add [物品] [数量] | /inv remove [物品] [数量] | /inv use [物品]")
        return False, "格式错误", 0


class HPCommand(BaseCommand):
    """生命值修改命令"""
    
    command_name = "hp_modify"
    command_description = "修改生命值"
    command_pattern = r"^/hp\s*([+-]?\d+)$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _storage:
            return False, "插件未正确初始化", 0
        
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        amount = int(self.matched_groups.get("1", "0"))
        
        player = await _storage.get_player(stream_id, user_id)
        if not player:
            await self.send_text("⚠️ 你还没有加入跑团！")
            return False, "未加入", 0
        
        old_hp, new_hp = player.modify_hp(amount)
        await _storage.save_player(player)
        
        change_text = f"+{amount}" if amount > 0 else str(amount)
        status = "💀 倒下了！" if new_hp <= 0 else ""
        
        await self.send_text(f"❤️ HP: {old_hp} → {new_hp}/{player.hp_max} ({change_text}) {status}")
        return True, None, 2


class MPCommand(BaseCommand):
    """魔力值修改命令"""
    
    command_name = "mp_modify"
    command_description = "修改魔力值"
    command_pattern = r"^/mp\s*([+-]?\d+)$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _storage:
            return False, "插件未正确初始化", 0
        
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        amount = int(self.matched_groups.get("1", "0"))
        
        player = await _storage.get_player(stream_id, user_id)
        if not player:
            await self.send_text("⚠️ 你还没有加入跑团！")
            return False, "未加入", 0
        
        old_mp, new_mp = player.modify_mp(amount)
        await _storage.save_player(player)
        
        change_text = f"+{amount}" if amount > 0 else str(amount)
        
        await self.send_text(f"💙 MP: {old_mp} → {new_mp}/{player.mp_max} ({change_text})")
        return True, None, 2


class DMCommand(BaseCommand):
    """DM 专用命令"""
    
    command_name = "dm_control"
    command_description = "DM 控制命令"
    command_pattern = r"^/dm\s+(time|weather|location|npc|event|describe)(?:\s+(.+))?$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _storage or not _dm_engine:
            return False, "插件未正确初始化", 0
        
        stream_id = self.message.chat_stream.stream_id
        action = self.matched_groups.get("1", "")
        args = self.matched_groups.get("2", "").strip()
        
        session = await _storage.get_session(stream_id)
        if not session:
            await self.send_text("⚠️ 当前没有进行中的跑团会话")
            return False, "无会话", 0
        
        # TODO: 添加权限检查
        
        if action == "time" and args:
            session.world_state.time_of_day = args
            session.add_history("system", f"时间变为: {args}")
            await _storage.save_session(session)
            await self.send_text(f"🕐 时间已设置为: {args}")
            return True, None, 2
        
        elif action == "weather" and args:
            session.world_state.weather = args
            session.add_history("system", f"天气变为: {args}")
            await _storage.save_session(session)
            await self.send_text(f"🌤️ 天气已设置为: {args}")
            return True, None, 2
        
        elif action == "location" and args:
            session.world_state.location = args
            session.add_history("system", f"场景转换: {args}")
            await _storage.save_session(session)
            await self.send_text(f"📍 位置已设置为: {args}")
            return True, None, 2
        
        elif action == "npc" and args:
            parts = args.split(maxsplit=1)
            npc_name = parts[0]
            npc_action = parts[1] if len(parts) > 1 else ""
            
            if npc_name not in session.npcs:
                session.add_npc(npc_name)
            
            if npc_action:
                response = await _dm_engine.generate_npc_dialogue(session, npc_name, npc_action)
                session.add_history("dm", response)
                await _storage.save_session(session)
                await self.send_text(response)
            else:
                await self.send_text(f"✅ NPC {npc_name} 已添加")
            return True, None, 2
        
        elif action == "event" and args:
            session.add_history("dm", f"[事件] {args}")
            await _storage.save_session(session)
            await self.send_text(f"⚡ 事件发生: {args}")
            return True, None, 2
        
        elif action == "describe":
            description = await _dm_engine.describe_environment(session)
            session.add_history("dm", description)
            await _storage.save_session(session)
            await self.send_text(description)
            return True, None, 2
        
        await self.send_text("⚠️ DM 命令格式错误")
        return False, "格式错误", 0


class LoreCommand(BaseCommand):
    """世界观设定命令"""
    
    command_name = "lore"
    command_description = "世界观设定管理"
    command_pattern = r"^/lore(?:\s+(add|search))?(?:\s+(.+))?$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _storage:
            return False, "插件未正确初始化", 0
        
        stream_id = self.message.chat_stream.stream_id
        action = self.matched_groups.get("1", "")
        content = self.matched_groups.get("2", "").strip()
        
        session = await _storage.get_session(stream_id)
        if not session:
            await self.send_text("⚠️ 当前没有进行中的跑团会话")
            return False, "无会话", 0
        
        if action == "add" and content:
            await _storage.add_lore(stream_id, content)
            await self.send_text(f"📚 已添加世界观设定:\n{content}")
            return True, None, 2
        
        elif action == "search" and content:
            results = await _storage.search_lore(stream_id, content)
            if results:
                text = "📚 搜索结果:\n" + "\n".join([f"• {r}" for r in results[:5]])
                await self.send_text(text)
            else:
                await self.send_text(f"📚 未找到与 '{content}' 相关的设定")
            return True, None, 2
        
        else:
            # 显示所有设定
            lore = await _storage.get_lore(stream_id)
            if lore:
                text = "📚 世界观设定:\n" + "\n".join([f"• {l}" for l in lore[:10]])
                if len(lore) > 10:
                    text += f"\n... 还有 {len(lore) - 10} 条设定"
                await self.send_text(text)
            else:
                await self.send_text("📚 暂无世界观设定\n使用 /lore add [设定内容] 添加")
            return True, None, 2


class ModuleCommand(BaseCommand):
    """模组管理命令"""
    
    command_name = "module"
    command_description = "模组管理"
    command_pattern = r"^/module(?:\s+(list|info|load))?(?:\s+(.+))?$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _module_loader:
            await self.send_text("⚠️ 模组系统未初始化")
            return False, "模组系统未初始化", 0
        
        action = self.matched_groups.get("1", "list") or "list"
        args = self.matched_groups.get("2", "").strip()
        
        if action == "list":
            return await self._list_modules()
        elif action == "info" and args:
            return await self._show_module_info(args)
        elif action == "load" and args:
            return await self._load_module(args)
        
        await self.send_text("""📚 模组命令用法:
• /module list - 列出所有可用模组
• /module info [模组ID] - 查看模组详情
• /module load [模组ID] - 加载模组开始跑团

💡 也可以直接使用 /trpg start [模组ID] 开始""")
        return True, None, 2

    async def _list_modules(self) -> Tuple[bool, str, int]:
        """列出所有可用模组"""
        modules = _module_loader.list_available_modules()
        
        if not modules:
            await self.send_text("📚 暂无可用模组")
            return True, None, 2
        
        # 按类型分组
        by_genre = {}
        for m in modules:
            genre = m.get("genre", "其他")
            if genre not in by_genre:
                by_genre[genre] = []
            by_genre[genre].append(m)
        
        genre_names = {
            "fantasy": "🗡️ 奇幻",
            "horror": "👻 恐怖",
            "scifi": "🚀 科幻",
            "modern": "🏙️ 现代",
        }
        
        text = "📚 可用模组列表:\n"
        for genre, mods in by_genre.items():
            genre_display = genre_names.get(genre, f"📁 {genre}")
            text += f"\n{genre_display}:\n"
            for m in mods:
                difficulty_icon = {"easy": "🟢", "normal": "🟡", "hard": "🔴"}.get(m.get("difficulty"), "⚪")
                text += f"  {difficulty_icon} {m['name']} ({m['id']})\n"
        
        text += "\n使用 /module info [模组ID] 查看详情"
        await self.send_text(text)
        return True, None, 2

    async def _show_module_info(self, module_id: str) -> Tuple[bool, str, int]:
        """显示模组详情"""
        info = _module_loader.get_module_info(module_id)
        
        if not info:
            await self.send_text(f"⚠️ 未找到模组: {module_id}")
            return False, "模组不存在", 0
        
        module_info = info["info"]
        difficulty_text = {"easy": "简单 🟢", "normal": "普通 🟡", "hard": "困难 🔴"}.get(
            module_info["difficulty"], module_info["difficulty"]
        )
        
        text = f"""📚 模组详情: {module_info['name']}

📝 简介: {module_info['description']}

📊 信息:
• 作者: {module_info['author']}
• 类型: {module_info['genre']}
• 难度: {difficulty_text}
• 建议人数: {module_info['player_count']}
• 预计时长: {module_info['duration']}
• 标签: {', '.join(module_info['tags'])}

🌍 世界观: {info['world_name']}
👥 NPC数量: {info['npc_count']}
📍 地点数量: {info['location_count']}
🎭 结局数量: {info['ending_count']}

使用 /trpg start {module_id} 开始此模组"""
        
        await self.send_text(text)
        return True, None, 2

    async def _load_module(self, module_id: str) -> Tuple[bool, str, int]:
        """加载模组"""
        stream_id = self.message.chat_stream.stream_id
        
        # 检查是否已有会话
        existing = await _storage.get_session(stream_id)
        if existing and existing.is_active():
            await self.send_text("⚠️ 当前已有进行中的跑团会话！\n使用 /trpg end 结束后再加载新模组")
            return False, "已有会话", 0
        
        # 加载模组
        module = _module_loader.load_module(module_id)
        if not module:
            await self.send_text(f"⚠️ 未找到模组: {module_id}")
            return False, "模组不存在", 0
        
        # 创建会话并应用模组
        session = await _storage.create_session(stream_id, module.world_name)
        await _module_loader.apply_module_to_session(module, session, _storage)
        
        await self.send_text(f"""🎲 模组加载成功！

📚 {module.info.name}
🎭 {module.info.genre} | 难度: {module.info.difficulty}

{module.intro_text}

📋 使用 /join [角色名] 加入冒险！""")
        
        return True, f"模组 {module.info.name} 已加载", 2
