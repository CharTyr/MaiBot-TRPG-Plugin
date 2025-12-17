"""
TRPG DM 插件命令组件 - 统一命令系统
所有命令统一使用 /trpg 前缀
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
_plugin_config: dict = {}


def set_services(storage: "StorageManager", dice: "DiceService", dm: "DMEngine", loader: "ModuleLoader" = None):
    """设置服务引用"""
    global _storage, _dice_service, _dm_engine, _module_loader
    _storage = storage
    _dice_service = dice
    _dm_engine = dm
    _module_loader = loader


def set_config(config: dict):
    """设置配置引用"""
    global _plugin_config
    _plugin_config = config


def _is_admin(user_id: str) -> bool:
    """检查用户是否是管理员"""
    admin_users = _plugin_config.get("permissions", {}).get("admin_users", [])
    return str(user_id) in [str(a) for a in admin_users]


# ============================================================
# 统一 TRPG 命令 - 所有功能通过 /trpg 访问
# ============================================================

class TRPGCommand(BaseCommand):
    """
    统一的 TRPG 命令处理器
    
    命令格式: /trpg <子命令> [参数]
    
    子命令列表:
    - help: 显示帮助
    - start [模组]: 开始跑团
    - end: 结束跑团
    - status: 查看状态
    - join [角色名]: 加入游戏
    - pc [show|set|leave]: 角色管理
    - r/roll [表达式]: 掷骰子
    - inv [add|rm|use]: 背包管理
    - hp/mp [+/-n]: 修改属性
    - dm [子命令]: DM控制
    - slot [list|save|load]: 存档管理
    - module [list|info]: 模组管理
    """
    
    command_name = "trpg_unified"
    command_description = "TRPG 跑团统一命令"
    # 匹配 /trpg 后跟可选的子命令和参数
    command_pattern = r"^/trpg(?:\s+(?P<subcmd>\S+))?(?:\s+(?P<args>.*))?$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _storage:
            return False, "插件未正确初始化", 0
        
        subcmd = (self.matched_groups.get("subcmd") or "help").lower()
        args = (self.matched_groups.get("args") or "").strip()
        
        # 路由到对应的处理方法
        handlers = {
            "help": self._help,
            "h": self._help,
            "start": self._start,
            "end": self._end,
            "status": self._status,
            "s": self._status,
            "join": self._join,
            "j": self._join,
            "pc": self._pc,
            "r": self._roll,
            "roll": self._roll,
            "inv": self._inventory,
            "i": self._inventory,
            "hp": self._hp,
            "mp": self._mp,
            "dm": self._dm,
            "slot": self._slot,
            "save": self._save,
            "module": self._module,
            "mod": self._module,
            "lore": self._lore,
            "scene": self._scene,
            "confirm": self._confirm,
            "pause": self._pause,
            "resume": self._resume,
        }
        
        handler = handlers.get(subcmd)
        if handler:
            return await handler(args)
        
        # 未知子命令，显示帮助
        await self.send_text(f"⚠️ 未知命令: /trpg {subcmd}\n使用 /trpg help 查看帮助")
        return False, "未知命令", 0


    # ==================== 帮助 ====================
    async def _help(self, args: str) -> Tuple[bool, Optional[str], int]:
        """显示帮助信息"""
        help_text = """🎲 MaiBot TRPG DM 跑团插件

━━━ 📋 会话管理 ━━━
/trpg start [模组]  开始跑团
/trpg end           结束跑团
/trpg status        查看状态
/trpg save          手动保存
/trpg pause/resume  暂停/继续

━━━ 🎭 玩家操作 ━━━
/trpg join [角色名] 加入跑团
/trpg pc show       查看角色卡
/trpg pc set 属性 值 设置属性
/trpg pc leave      离开跑团
/trpg hp +/-数值    修改HP
/trpg mp +/-数值    修改MP

━━━ 🎒 背包系统 ━━━
/trpg inv           查看背包
/trpg inv add 物品 数量
/trpg inv rm 物品 数量
/trpg inv use 物品

━━━ 🎲 骰子命令 ━━━
/trpg r d20         掷一个20面骰
/trpg r 2d6+3       掷两个6面骰加3

━━━ 💾 存档系统 ━━━
/trpg slot list     查看存档
/trpg slot save 1-3 保存存档
/trpg slot load 1-3 加载存档

━━━ 📚 模组管理 ━━━
/trpg mod list      列出模组
/trpg mod info ID   模组详情

━━━ 🎮 DM命令 ━━━
/trpg dm time 时间
/trpg dm weather 天气
/trpg dm location 位置
/trpg dm npc 名称 动作
/trpg dm event 描述
/trpg dm describe

━━━ 💡 角色扮演格式 ━━━
*动作描述*  （动作）  "对话"

🌟 快速开始: /trpg start solo_mystery"""
        
        await self.send_text(help_text)
        return True, None, 2


    # ==================== 会话管理 ====================
    async def _start(self, args: str) -> Tuple[bool, Optional[str], int]:
        """开始跑团会话"""
        stream_id = self.message.chat_stream.stream_id
        
        existing = await _storage.get_session(stream_id)
        if existing and existing.is_active():
            return False, "⚠️ 已有进行中的跑团！使用 /trpg end 结束", 2

        if not _storage.is_group_allowed(stream_id):
            await self.send_text("⚠️ 本群未被允许启用跑团（请在 `config.toml` 的 `[plugin].allowed_groups` 中配置）")
            return False, "群组不允许", 0
        
        if not args:
            return await self._show_module_list()
        
        # 检查是否是预设模组
        if _module_loader:
            module = _module_loader.load_module(args)
            if module:
                session = await _storage.create_session(stream_id, module.world_name)
                await _module_loader.apply_module_to_session(module, session, _storage)
                
                await self.send_text(f"""🎲 跑团开始！

📚 模组: {module.info.name}
🎭 {module.info.genre} | 难度: {module.info.difficulty}
👥 建议: {module.info.player_count} | ⏱️ {module.info.duration}

{module.intro_text}

📋 使用 /trpg join [角色名] 加入冒险""")
                return True, f"模组 {module.info.name} 已加载", 2
        
        # 自由模式
        session = await _storage.create_session(stream_id, args)
        intro = await _dm_engine.generate_session_intro(session)
        session.add_history("system", f"跑团开始: {args}")
        await _storage.save_session(session)
        
        await self.send_text(f"""🎲 跑团开始！

世界观: {args}
{intro}

📋 使用 /trpg join [角色名] 加入冒险""")
        return True, "跑团会话已开始", 2

    async def _show_module_list(self) -> Tuple[bool, Optional[str], int]:
        """显示模组选择列表"""
        if not _module_loader:
            await self.send_text("⚠️ 模组系统未初始化")
            return False, "模组系统未初始化", 0
        
        modules = _module_loader.list_available_modules()
        genre_names = {"fantasy": "🗡️奇幻", "horror": "👻恐怖", "scifi": "🚀科幻", "modern": "🏙️现代"}
        diff_icons = {"easy": "🟢", "normal": "🟡", "hard": "🔴"}
        
        by_genre = {}
        for m in modules:
            genre = m.get("genre", "其他")
            by_genre.setdefault(genre, []).append(m)
        
        text = "🎲 请选择模组:\n"
        for genre, mods in by_genre.items():
            text += f"\n{genre_names.get(genre, genre)}:\n"
            for m in mods:
                text += f"  {diff_icons.get(m.get('difficulty'), '⚪')} {m['name']} ({m['id']})\n"
        
        text += "\n📝 /trpg start [模组ID] 或 /trpg start [自定义世界观]"
        await self.send_text(text)
        return True, None, 2


    async def _end(self, args: str) -> Tuple[bool, Optional[str], int]:
        """结束跑团会话"""
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        session = await _storage.get_session(stream_id)
        
        if not session:
            return False, "⚠️ 当前没有进行中的跑团", 2

        allow_player_end = _plugin_config.get("permissions", {}).get("allow_player_end_session", False)
        if not allow_player_end and not _is_admin(user_id):
            await self.send_text("⚠️ 只有管理员可以结束跑团")
            return False, "权限不足", 0
        
        session.add_history("system", "跑团结束")
        await _storage.save_session(session)
        await _storage.end_session(stream_id)
        
        await self.send_text("🎲 跑团结束！感谢各位冒险者的参与！")
        return True, "跑团已结束", 2

    async def _status(self, args: str) -> Tuple[bool, Optional[str], int]:
        """显示会话状态"""
        stream_id = self.message.chat_stream.stream_id
        session = await _storage.get_session(stream_id)
        
        if not session:
            await self.send_text("📋 当前没有跑团会话\n使用 /trpg start 开始")
            return True, None, 2
        
        players = await _storage.get_players_in_session(stream_id)
        player_list = "\n".join([f"  • {p.character_name}" for p in players]) or "  暂无"
        
        await self.send_text(f"""📋 跑团状态

🌍 世界观: {session.world_name}
📍 位置: {session.world_state.location}
🕐 时间: {session.world_state.time_of_day}
🌤️ 天气: {session.world_state.weather}
📊 状态: {session.status}

👥 玩家:
{player_list}""")
        return True, None, 2

    async def _save(self, args: str) -> Tuple[bool, Optional[str], int]:
        """手动保存"""
        stream_id = self.message.chat_stream.stream_id
        session = await _storage.get_session(stream_id)
        
        if not session:
            return False, "⚠️ 当前没有跑团会话", 2
        
        await _storage.save_session(session)
        await self.send_text("💾 存档已保存！")
        return True, "已保存", 2

    async def _pause(self, args: str) -> Tuple[bool, Optional[str], int]:
        """暂停会话"""
        stream_id = self.message.chat_stream.stream_id
        session = await _storage.get_session(stream_id)
        
        if not session:
            return False, "⚠️ 当前没有跑团会话", 2
        
        session.status = "paused"
        session.add_history("system", "跑团暂停")
        await _storage.save_session(session)
        await self.send_text("⏸️ 跑团已暂停，使用 /trpg resume 继续")
        return True, "已暂停", 2

    async def _resume(self, args: str) -> Tuple[bool, Optional[str], int]:
        """恢复会话"""
        stream_id = self.message.chat_stream.stream_id
        session = await _storage.get_session(stream_id)
        
        if not session:
            return False, "⚠️ 当前没有跑团会话", 2
        
        if session.status != "paused":
            return False, "⚠️ 会话未处于暂停状态", 2
        
        session.status = "active"
        session.add_history("system", "跑团继续")
        await _storage.save_session(session)
        await self.send_text("▶️ 跑团继续！")
        return True, "已继续", 2


    # ==================== 玩家操作 ====================
    async def _join(self, args: str) -> Tuple[bool, Optional[str], int]:
        """加入跑团"""
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        character_name = args.strip() or "无名冒险者"
        
        session = await _storage.get_session(stream_id)
        if not session:
            await self.send_text("⚠️ 当前没有跑团会话，无法加入")
            return False, "无会话", 0
        
        if not session.is_active():
            await self.send_text("⚠️ 跑团会话未开启或已暂停，无法加入")
            return False, "会话未激活", 0
        
        existing = await _storage.get_player(stream_id, user_id)
        if existing:
            await self.send_text(f"⚠️ 你已经以 {existing.character_name} 的身份加入了！")
            return False, "已加入", 0

        # 中途加入控制（对已有人加入的会话生效）
        session_config = _plugin_config.get("session", {})
        allow_mid_join = session_config.get("allow_mid_join", True)
        if not allow_mid_join and session.player_ids:
            await self.send_text("⚠️ 本跑团不允许中途加入")
            return False, "不允许中途加入", 0

        # 中途加入确认（管理员）
        mid_join_require_confirm = session_config.get("mid_join_require_confirm", False)
        if mid_join_require_confirm and not _is_admin(user_id):
            pending = _storage.get_pending_join(stream_id, user_id)
            if pending:
                await self.send_text("📝 你已有待确认的加入请求，请等待管理员处理")
                return True, "待确认", 2

            _storage.add_pending_join(stream_id, user_id, character_name)
            await self.send_text(
                "📝 已提交加入申请，等待管理员确认。\n"
                "管理员可使用 `/trpg confirm` 查看并处理。"
            )
            return True, "待确认", 2
        
        player = await _storage.create_player(stream_id, user_id, character_name)
        session.add_history("system", f"{character_name} 加入了冒险", user_id=user_id)
        await _storage.save_session(session)
        
        await self.send_text(f"""🎭 欢迎 {character_name} 加入冒险！

{player.get_character_sheet()}

{player.get_points_display()}

━━━ 加点说明 ━━━
/trpg pc add 属性 点数  分配属性点
/trpg pc reset         重置所有加点
/trpg pc lock          锁定角色（完成加点）

属性: 力量/str 敏捷/dex 体质/con 智力/int 感知/wis 魅力/cha""")
        return True, f"{character_name} 加入", 2

    async def _pc(self, args: str) -> Tuple[bool, Optional[str], int]:
        """角色管理"""
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        
        player = await _storage.get_player(stream_id, user_id)
        if not player:
            await self.send_text("⚠️ 你还没有加入跑团！使用 /trpg join [角色名]")
            return False, "未加入", 0
        
        parts = args.split(maxsplit=2)
        action = parts[0].lower() if parts else "show"
        
        if action == "show" or not action:
            sheet = player.get_character_sheet()
            points_info = player.get_points_display()
            await self.send_text(f"{sheet}\n\n{points_info}")
            return True, None, 2
        
        elif action == "add" and len(parts) >= 2:
            # 加点: /trpg pc add 力量 3
            attr_name = parts[1]
            try:
                points = int(parts[2]) if len(parts) >= 3 else 1
            except ValueError:
                await self.send_text("⚠️ 点数必须是整数")
                return False, "无效数值", 0
            if points <= 0:
                await self.send_text("⚠️ 点数必须为正数")
                return False, "无效数值", 0

            player_cfg = _plugin_config.get("player", {})
            min_attr = int(player_cfg.get("min_attribute", 3))
            max_attr = int(player_cfg.get("max_attribute", 18))
            
            success, msg = player.allocate_point(attr_name, points, min_attribute=min_attr, max_attribute=max_attr)
            if success:
                await _storage.save_player(player)
                await self.send_text(f"✅ {msg}")
            else:
                await self.send_text(f"⚠️ {msg}")
            return success, msg if not success else None, 2
        
        elif action == "sub" and len(parts) >= 2:
            # 减点: /trpg pc sub 力量 2
            attr_name = parts[1]
            try:
                points = int(parts[2]) if len(parts) >= 3 else 1
            except ValueError:
                await self.send_text("⚠️ 点数必须是整数")
                return False, "无效数值", 0
            if points <= 0:
                await self.send_text("⚠️ 点数必须为正数")
                return False, "无效数值", 0

            player_cfg = _plugin_config.get("player", {})
            min_attr = int(player_cfg.get("min_attribute", 3))
            max_attr = int(player_cfg.get("max_attribute", 18))
            
            success, msg = player.allocate_point(attr_name, -points, min_attribute=min_attr, max_attribute=max_attr)
            if success:
                await _storage.save_player(player)
                await self.send_text(f"✅ {msg}")
            else:
                await self.send_text(f"⚠️ {msg}")
            return success, msg if not success else None, 2
        
        elif action == "reset":
            # 重置加点
            success, msg = player.reset_points()
            if success:
                await _storage.save_player(player)
                await self.send_text(f"✅ {msg}")
            else:
                await self.send_text(f"⚠️ {msg}")
            return success, msg if not success else None, 2
        
        elif action == "lock":
            # 锁定角色
            success, msg = player.lock_character()
            if success:
                await _storage.save_player(player)
                await self.send_text(f"🔒 {msg}\n\n{player.get_character_sheet()}")
            else:
                await self.send_text(f"⚠️ {msg}")
            return success, msg if not success else None, 2
        
        elif action == "unlock":
            # 解锁角色（管理员）
            if not _is_admin(user_id):
                await self.send_text("⚠️ 只有管理员可以解锁角色")
                return False, "权限不足", 0
            
            success, msg = player.unlock_character()
            if success:
                await _storage.save_player(player)
                await self.send_text(f"🔓 {msg}")
            else:
                await self.send_text(f"⚠️ {msg}")
            return success, msg if not success else None, 2
        
        elif action == "set" and len(parts) >= 3:
            # 直接设置属性（管理员功能）
            if not _is_admin(user_id):
                await self.send_text("⚠️ 直接设置属性需要管理员权限\n普通玩家请使用 /trpg pc add 属性 点数")
                return False, "权限不足", 0
            
            attr_name, attr_value = parts[1], parts[2]
            try:
                value = int(attr_value)
                if player.attributes.set_attribute(attr_name, value):
                    await _storage.save_player(player)
                    await self.send_text(f"✅ [管理员] 已将 {attr_name} 设置为 {value}")
                    return True, None, 2
                await self.send_text(f"⚠️ 未知属性: {attr_name}")
            except ValueError:
                await self.send_text(f"⚠️ 无效数值: {attr_value}")
            return False, "设置失败", 0
        
        elif action == "leave":
            name = player.character_name
            await _storage.delete_player(stream_id, user_id)
            await self.send_text(f"👋 {name} 离开了冒险...")
            return True, "离开", 2
        
        await self.send_text("""📋 角色管理命令:
/trpg pc show        查看角色卡
/trpg pc add 属性 点数  分配属性点
/trpg pc sub 属性 点数  减少属性点
/trpg pc reset       重置所有加点
/trpg pc lock        锁定角色
/trpg pc leave       离开跑团

属性: 力量/str 敏捷/dex 体质/con 智力/int 感知/wis 魅力/cha""")
        return False, "格式错误", 0

    async def _hp(self, args: str) -> Tuple[bool, Optional[str], int]:
        """修改HP"""
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        
        player = await _storage.get_player(stream_id, user_id)
        if not player:
            await self.send_text("⚠️ 你还没有加入跑团！")
            return False, "未加入", 0
        
        try:
            amount = int(args) if args else 0
        except ValueError:
            await self.send_text("⚠️ 请输入有效数值，如 /trpg hp +5 或 /trpg hp -3")
            return False, "无效数值", 0
        
        old_hp, new_hp = player.modify_hp(amount)
        await _storage.save_player(player)
        
        change = f"+{amount}" if amount > 0 else str(amount)
        status = " 💀 倒下了！" if new_hp <= 0 else ""
        await self.send_text(f"❤️ HP: {old_hp} → {new_hp}/{player.hp_max} ({change}){status}")
        return True, None, 2

    async def _mp(self, args: str) -> Tuple[bool, Optional[str], int]:
        """修改MP"""
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        
        player = await _storage.get_player(stream_id, user_id)
        if not player:
            await self.send_text("⚠️ 你还没有加入跑团！")
            return False, "未加入", 0
        
        try:
            amount = int(args) if args else 0
        except ValueError:
            await self.send_text("⚠️ 请输入有效数值")
            return False, "无效数值", 0
        
        old_mp, new_mp = player.modify_mp(amount)
        await _storage.save_player(player)
        
        change = f"+{amount}" if amount > 0 else str(amount)
        await self.send_text(f"💙 MP: {old_mp} → {new_mp}/{player.mp_max} ({change})")
        return True, None, 2


    # ==================== 背包系统 ====================
    async def _inventory(self, args: str) -> Tuple[bool, Optional[str], int]:
        """背包管理"""
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        
        player = await _storage.get_player(stream_id, user_id)
        if not player:
            await self.send_text("⚠️ 你还没有加入跑团！")
            return False, "未加入", 0
        
        if not args:
            await self.send_text(player.get_inventory_display())
            return True, None, 2
        
        parts = args.split(maxsplit=2)
        action = parts[0].lower()
        
        # 解析物品名和数量
        item_args = " ".join(parts[1:]) if len(parts) > 1 else ""
        item_name = item_args
        quantity = 1
        
        if item_args:
            item_parts = item_args.rsplit(None, 1)
            if len(item_parts) == 2 and item_parts[1].isdigit():
                item_name = item_parts[0]
                quantity = int(item_parts[1])
        
        if action == "add" and item_name:
            player.add_item(item_name, quantity)
            await _storage.save_player(player)
            await self.send_text(f"✅ 获得了 {item_name} x{quantity}")
            return True, None, 2
        
        elif action in ("rm", "remove") and item_name:
            if player.remove_item(item_name, quantity):
                await _storage.save_player(player)
                await self.send_text(f"✅ 移除了 {item_name} x{quantity}")
                return True, None, 2
            await self.send_text(f"⚠️ 背包中没有 {item_name}")
            return False, "物品不存在", 0
        
        elif action == "use" and item_name:
            if player.get_item(item_name):
                player.remove_item(item_name, 1)
                await _storage.save_player(player)
                await self.send_text(f"✨ 使用了 {item_name}！")
                return True, None, 2
            await self.send_text(f"⚠️ 背包中没有 {item_name}")
            return False, "物品不存在", 0
        
        await self.send_text("用法: /trpg inv [add|rm|use] [物品] [数量]")
        return False, "格式错误", 0

    # ==================== 骰子系统 ====================
    async def _roll(self, args: str) -> Tuple[bool, Optional[str], int]:
        """掷骰子"""
        if not _dice_service:
            return False, "骰子服务未初始化", 0
        
        expression = args.strip() or "d20"
        
        try:
            result = _dice_service.roll(expression)
            await self.send_text(result.get_display())
            
            # 记录到历史
            stream_id = self.message.chat_stream.stream_id
            session = await _storage.get_session(stream_id)
            if session and session.is_active():
                user_id = str(self.message.message_info.user_info.user_id)
                player = await _storage.get_player(stream_id, user_id)
                session.add_history(
                    "dice", f"{expression} = {result.total}",
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


    # ==================== DM 控制 ====================
    async def _dm(self, args: str) -> Tuple[bool, Optional[str], int]:
        """DM 控制命令"""
        if not _dm_engine:
            return False, "DM引擎未初始化", 0

        user_id = str(self.message.message_info.user_info.user_id)
        if not _is_admin(user_id):
            await self.send_text("⚠️ 只有管理员可以使用 DM 命令")
            return False, "权限不足", 0
        
        stream_id = self.message.chat_stream.stream_id
        session = await _storage.get_session(stream_id)
        
        if not session:
            await self.send_text("⚠️ 当前没有跑团会话")
            return False, "无会话", 0
        
        parts = args.split(maxsplit=1)
        action = parts[0].lower() if parts else ""
        value = parts[1] if len(parts) > 1 else ""
        
        if action == "time" and value:
            session.world_state.time_of_day = value
            session.add_history("system", f"时间变为: {value}")
            await _storage.save_session(session)
            await self.send_text(f"🕐 时间: {value}")
            return True, None, 2
        
        elif action == "weather" and value:
            session.world_state.weather = value
            session.add_history("system", f"天气变为: {value}")
            await _storage.save_session(session)
            await self.send_text(f"🌤️ 天气: {value}")
            return True, None, 2
        
        elif action == "location" and value:
            session.world_state.location = value
            session.add_history("system", f"场景转换: {value}")
            await _storage.save_session(session)
            await self.send_text(f"📍 位置: {value}")
            return True, None, 2
        
        elif action == "npc" and value:
            npc_parts = value.split(maxsplit=1)
            npc_name = npc_parts[0]
            npc_action = npc_parts[1] if len(npc_parts) > 1 else ""
            
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
        
        elif action == "event" and value:
            session.add_history("dm", f"[事件] {value}")
            await _storage.save_session(session)
            await self.send_text(f"⚡ 事件: {value}")
            return True, None, 2
        
        elif action == "describe":
            description = await _dm_engine.describe_environment(session)
            session.add_history("dm", description)
            await _storage.save_session(session)
            await self.send_text(description)
            return True, None, 2
        
        await self.send_text("""🎮 DM命令:
/trpg dm time [时间]
/trpg dm weather [天气]
/trpg dm location [位置]
/trpg dm npc [名称] [动作]
/trpg dm event [描述]
/trpg dm describe""")
        return True, None, 2

    # ==================== 存档系统 ====================
    async def _slot(self, args: str) -> Tuple[bool, Optional[str], int]:
        """存档插槽管理"""
        stream_id = self.message.chat_stream.stream_id
        
        parts = args.split()
        action = parts[0].lower() if parts else "list"
        slot_num = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        
        if action == "list":
            slots = await _storage.list_save_slots(stream_id)
            text = "💾 存档插槽:\n"
            for slot in slots:
                sn = slot["slot"]
                if slot.get("exists"):
                    text += f"\n📁 插槽 {sn}: {slot.get('world_name', '?')} 👥{slot.get('player_count', 0)}\n"
                else:
                    text += f"\n📁 插槽 {sn}: (空)\n"
            await self.send_text(text)
            return True, None, 2
        
        elif action == "save" and slot_num:
            success, msg = await _storage.save_to_slot(stream_id, slot_num)
            await self.send_text(f"{'💾' if success else '⚠️'} {msg}")
            return success, msg, 2
        
        elif action == "load" and slot_num:
            success, msg = await _storage.load_from_slot(stream_id, slot_num)
            await self.send_text(f"{'💾' if success else '⚠️'} {msg}")
            
            # 加载成功后生成前情回顾
            if success and _dm_engine:
                session = await _storage.get_session(stream_id)
                if session:
                    try:
                        recap = await _dm_engine.generate_recap(session)
                        await self.send_text(recap)
                    except Exception as e:
                        logger.warning(f"生成前情回顾失败: {e}")
            
            return success, msg, 2
        
        elif action == "delete" and slot_num:
            user_id = str(self.message.message_info.user_info.user_id)
            if not _is_admin(user_id):
                await self.send_text("⚠️ 只有管理员可以删除存档")
                return False, "权限不足", 0
            success, msg = await _storage.delete_slot(stream_id, slot_num)
            await self.send_text(f"{'🗑️' if success else '⚠️'} {msg}")
            return success, msg, 2
        
        await self.send_text("用法: /trpg slot [list|save|load|delete] [插槽号]")
        return False, "格式错误", 0


    # ==================== 模组管理 ====================
    async def _module(self, args: str) -> Tuple[bool, Optional[str], int]:
        """模组管理"""
        if not _module_loader:
            await self.send_text("⚠️ 模组系统未初始化")
            return False, "未初始化", 0
        
        parts = args.split(maxsplit=1)
        action = parts[0].lower() if parts else "list"
        module_id = parts[1] if len(parts) > 1 else ""
        
        if action == "list":
            modules = _module_loader.list_available_modules()
            if not modules:
                await self.send_text("📚 暂无可用模组")
                return True, None, 2
            
            genre_names = {"fantasy": "🗡️奇幻", "horror": "👻恐怖", "scifi": "🚀科幻", "modern": "🏙️现代"}
            diff_icons = {"easy": "🟢", "normal": "🟡", "hard": "🔴"}
            
            by_genre = {}
            for m in modules:
                by_genre.setdefault(m.get("genre", "其他"), []).append(m)
            
            text = "📚 可用模组:\n"
            for genre, mods in by_genre.items():
                text += f"\n{genre_names.get(genre, genre)}:\n"
                for m in mods:
                    text += f"  {diff_icons.get(m.get('difficulty'), '⚪')} {m['name']} ({m['id']})\n"
            
            text += "\n使用 /trpg mod info [ID] 查看详情"
            await self.send_text(text)
            return True, None, 2
        
        elif action == "info" and module_id:
            info = _module_loader.get_module_info(module_id)
            if not info:
                await self.send_text(f"⚠️ 未找到模组: {module_id}")
                return False, "模组不存在", 0
            
            mi = info["info"]
            diff_text = {"easy": "简单🟢", "normal": "普通🟡", "hard": "困难🔴"}.get(mi["difficulty"], mi["difficulty"])
            
            await self.send_text(f"""📚 {mi['name']}

📝 {mi['description']}

📊 作者: {mi['author']} | 类型: {mi['genre']}
🎯 难度: {diff_text} | 👥 {mi['player_count']} | ⏱️ {mi['duration']}
🏷️ {', '.join(mi['tags'])}

🌍 世界观: {info['world_name']}
👥 NPC: {info['npc_count']} | 📍 地点: {info['location_count']}

使用 /trpg start {module_id} 开始""")
            return True, None, 2
        
        await self.send_text("用法: /trpg mod [list|info ID]")
        return False, "格式错误", 0

    # ==================== 世界观设定 ====================
    async def _lore(self, args: str) -> Tuple[bool, Optional[str], int]:
        """世界观设定管理"""
        stream_id = self.message.chat_stream.stream_id
        session = await _storage.get_session(stream_id)
        
        if not session:
            await self.send_text("⚠️ 当前没有跑团会话")
            return False, "无会话", 0
        
        parts = args.split(maxsplit=1)
        action = parts[0].lower() if parts else ""
        content = parts[1] if len(parts) > 1 else ""
        
        if action == "add" and content:
            await _storage.add_lore(stream_id, content)
            await self.send_text(f"📚 已添加设定:\n{content}")
            return True, None, 2
        
        elif action == "search" and content:
            results = await _storage.search_lore(stream_id, content)
            if results:
                text = "📚 搜索结果:\n" + "\n".join([f"• {r}" for r in results[:5]])
            else:
                text = f"📚 未找到与 '{content}' 相关的设定"
            await self.send_text(text)
            return True, None, 2
        
        # 显示所有设定
        lore = await _storage.get_lore(stream_id)
        if lore:
            text = "📚 世界观设定:\n" + "\n".join([f"• {l}" for l in lore[:10]])
            if len(lore) > 10:
                text += f"\n... 还有 {len(lore) - 10} 条"
        else:
            text = "📚 暂无设定\n使用 /trpg lore add [内容] 添加"
        await self.send_text(text)
        return True, None, 2


    # ==================== 场景图片 ====================
    async def _scene(self, args: str) -> Tuple[bool, Optional[str], int]:
        """生成场景图片"""
        stream_id = self.message.chat_stream.stream_id
        session = await _storage.get_session(stream_id)
        
        if not session or not session.is_active():
            await self.send_text("⚠️ 当前没有跑团会话")
            return False, "无会话", 0
        
        image_config = _plugin_config.get("image", {})
        if not image_config.get("enabled", False):
            await self.send_text("⚠️ 场景图片功能未启用")
            return False, "功能未启用", 0
        
        await self.send_text("🎨 正在生成场景图片...")
        
        try:
            from ..services.image_generator import ImageGenerator
            generator = ImageGenerator(_plugin_config)
            success, result = await generator.generate_scene_image(session, args)
            
            if success:
                await self.send_image_base64(result)
                session.add_history("system", "生成了场景图片")
                await _storage.save_session(session)
                return True, "图片生成成功", 2
            
            await self.send_text(f"⚠️ 生成失败: {result}")
            return False, result, 0
        except Exception as e:
            logger.error(f"生成场景图片失败: {e}")
            await self.send_text(f"⚠️ 生成失败: {e}")
            return False, str(e), 0

    # ==================== 管理员确认 ====================
    async def _confirm(self, args: str) -> Tuple[bool, Optional[str], int]:
        """确认/拒绝玩家加入请求"""
        stream_id = self.message.chat_stream.stream_id
        user_id = str(self.message.message_info.user_info.user_id)
        
        if not _is_admin(user_id):
            await self.send_text("⚠️ 只有管理员可以确认加入请求")
            return False, "权限不足", 0
        
        parts = args.split()
        action = parts[0].lower() if parts else ""
        target_user = parts[1] if len(parts) > 1 else ""
        
        if not action:
            pending = _storage.get_all_pending_joins(stream_id)
            if not pending:
                await self.send_text("📋 没有待确认的加入请求")
                return True, None, 2
            
            text = "📋 待确认请求:\n"
            for uid, char_name in pending.items():
                text += f"• {char_name} (ID: {uid})\n"
            text += "\n/trpg confirm accept [ID] 确认\n/trpg confirm reject [ID] 拒绝"
            await self.send_text(text)
            return True, None, 2
        
        if not target_user:
            await self.send_text("⚠️ 请指定用户ID")
            return False, "缺少参数", 0
        
        character_name = _storage.remove_pending_join(stream_id, target_user)
        if not character_name:
            await self.send_text(f"⚠️ 未找到用户 {target_user} 的请求")
            return False, "请求不存在", 0
        
        if action == "accept":
            player = await _storage.create_player(stream_id, target_user, character_name)
            session = await _storage.get_session(stream_id)
            if session:
                session.add_history("system", f"{character_name} 加入了冒险（管理员确认）")
                await _storage.save_session(session)
            await self.send_text(f"✅ 已确认 {character_name} 加入！")
            return True, "已确认", 2
        
        elif action == "reject":
            await self.send_text(f"❌ 已拒绝 {character_name} 的请求")
            return True, "已拒绝", 2
        
        return False, "未知操作", 0


# ============================================================
# 快捷命令 - 保留常用的短命令作为别名
# ============================================================

class DiceShortcut(BaseCommand):
    """骰子快捷命令 /r"""
    command_name = "dice_shortcut"
    command_description = "掷骰子快捷命令"
    command_pattern = r"^/r(?:oll)?(?:\s+(?P<expr>.+))?$"

    async def execute(self) -> Tuple[bool, Optional[str], int]:
        if not _dice_service:
            return False, "骰子服务未初始化", 0
        
        expr = self.matched_groups.get("expr") or "d20"
        try:
            result = _dice_service.roll(expr)
            await self.send_text(result.get_display())
            return True, None, 2
        except Exception as e:
            await self.send_text(f"⚠️ 骰子表达式无效: {expr}")
            return False, str(e), 0
