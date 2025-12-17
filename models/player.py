"""
玩家角色数据模型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
import time


@dataclass
class InventoryItem:
    """背包物品"""
    name: str
    quantity: int = 1
    description: str = ""
    item_type: str = "misc"  # weapon, armor, consumable, misc
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "description": self.description,
            "item_type": self.item_type,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InventoryItem":
        return cls(**data)


@dataclass
class PlayerAttributes:
    """玩家属性"""
    strength: int = 10      # 力量 STR
    dexterity: int = 10     # 敏捷 DEX
    constitution: int = 10  # 体质 CON
    intelligence: int = 10  # 智力 INT
    wisdom: int = 10        # 感知 WIS
    charisma: int = 10      # 魅力 CHA

    # 简写映射
    ATTR_ALIASES = {
        "str": "strength", "力量": "strength",
        "dex": "dexterity", "敏捷": "dexterity",
        "con": "constitution", "体质": "constitution",
        "int": "intelligence", "智力": "intelligence",
        "wis": "wisdom", "感知": "wisdom",
        "cha": "charisma", "魅力": "charisma",
    }

    def to_dict(self) -> Dict[str, int]:
        return {
            "strength": self.strength,
            "dexterity": self.dexterity,
            "constitution": self.constitution,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "charisma": self.charisma,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "PlayerAttributes":
        return cls(**data)

    def get_modifier(self, attr_name: str) -> int:
        """获取属性调整值 (D&D 风格)"""
        value = self.get_attribute(attr_name)
        return (value - 10) // 2

    def get_attribute(self, attr_name: str) -> int:
        """获取属性值，支持简写"""
        attr_name = attr_name.lower()
        if attr_name in self.ATTR_ALIASES:
            attr_name = self.ATTR_ALIASES[attr_name]
        return getattr(self, attr_name, 10)

    def set_attribute(self, attr_name: str, value: int) -> bool:
        """设置属性值，支持简写"""
        attr_name = attr_name.lower()
        if attr_name in self.ATTR_ALIASES:
            attr_name = self.ATTR_ALIASES[attr_name]
        if hasattr(self, attr_name):
            setattr(self, attr_name, value)
            return True
        return False

    def get_display(self) -> str:
        """获取属性显示文本"""
        return (
            f"力量(STR): {self.strength} ({self.get_modifier('str'):+d})\n"
            f"敏捷(DEX): {self.dexterity} ({self.get_modifier('dex'):+d})\n"
            f"体质(CON): {self.constitution} ({self.get_modifier('con'):+d})\n"
            f"智力(INT): {self.intelligence} ({self.get_modifier('int'):+d})\n"
            f"感知(WIS): {self.wisdom} ({self.get_modifier('wis'):+d})\n"
            f"魅力(CHA): {self.charisma} ({self.get_modifier('cha'):+d})"
        )


# 默认配置
DEFAULT_FREE_POINTS = 30  # 初始自由加点点数
DEFAULT_BASE_ATTRIBUTE = 8  # 基础属性值（加点前）
DEFAULT_MAX_ATTRIBUTE = 18  # 单项属性最大值
DEFAULT_MIN_ATTRIBUTE = 3   # 单项属性最小值


@dataclass
class Player:
    """玩家角色"""
    user_id: str
    stream_id: str
    character_name: str = "无名冒险者"
    attributes: PlayerAttributes = field(default_factory=PlayerAttributes)
    hp_current: int = 20
    hp_max: int = 20
    mp_current: int = 10
    mp_max: int = 10
    level: int = 1
    experience: int = 0
    inventory: List[InventoryItem] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    # 加点系统
    free_points: int = DEFAULT_FREE_POINTS  # 剩余自由加点点数
    points_allocated: Dict[str, int] = field(default_factory=dict)  # 已分配的点数 {attr: points}
    character_locked: bool = False  # 角色是否已锁定（锁定后不能再加点）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "stream_id": self.stream_id,
            "character_name": self.character_name,
            "attributes": self.attributes.to_dict(),
            "hp_current": self.hp_current,
            "hp_max": self.hp_max,
            "mp_current": self.mp_current,
            "mp_max": self.mp_max,
            "level": self.level,
            "experience": self.experience,
            "inventory": [item.to_dict() for item in self.inventory],
            "skills": self.skills,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "custom_data": self.custom_data,
            "free_points": self.free_points,
            "points_allocated": self.points_allocated,
            "character_locked": self.character_locked,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Player":
        attributes = PlayerAttributes.from_dict(data.get("attributes", {}))
        inventory = [InventoryItem.from_dict(item) for item in data.get("inventory", [])]
        
        return cls(
            user_id=data["user_id"],
            stream_id=data["stream_id"],
            character_name=data.get("character_name", "无名冒险者"),
            attributes=attributes,
            hp_current=data.get("hp_current", 20),
            hp_max=data.get("hp_max", 20),
            mp_current=data.get("mp_current", 10),
            mp_max=data.get("mp_max", 10),
            level=data.get("level", 1),
            experience=data.get("experience", 0),
            inventory=inventory,
            skills=data.get("skills", []),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            custom_data=data.get("custom_data", {}),
            free_points=data.get("free_points", DEFAULT_FREE_POINTS),
            points_allocated=data.get("points_allocated", {}),
            character_locked=data.get("character_locked", False),
        )

    def modify_hp(self, amount: int) -> tuple[int, int]:
        """修改生命值，返回 (修改前, 修改后)"""
        old_hp = self.hp_current
        self.hp_current = max(0, min(self.hp_max, self.hp_current + amount))
        self.updated_at = time.time()
        return old_hp, self.hp_current

    def modify_mp(self, amount: int) -> tuple[int, int]:
        """修改魔力值，返回 (修改前, 修改后)"""
        old_mp = self.mp_current
        self.mp_current = max(0, min(self.mp_max, self.mp_current + amount))
        self.updated_at = time.time()
        return old_mp, self.mp_current

    def add_item(self, name: str, quantity: int = 1, **kwargs) -> InventoryItem:
        """添加物品到背包"""
        # 检查是否已有同名物品
        for item in self.inventory:
            if item.name == name:
                item.quantity += quantity
                self.updated_at = time.time()
                return item
        
        # 创建新物品
        new_item = InventoryItem(name=name, quantity=quantity, **kwargs)
        self.inventory.append(new_item)
        self.updated_at = time.time()
        return new_item

    def remove_item(self, name: str, quantity: int = 1) -> Optional[InventoryItem]:
        """从背包移除物品"""
        for item in self.inventory:
            if item.name == name:
                if item.quantity <= quantity:
                    self.inventory.remove(item)
                    self.updated_at = time.time()
                    return item
                else:
                    item.quantity -= quantity
                    self.updated_at = time.time()
                    return item
        return None

    def get_item(self, name: str) -> Optional[InventoryItem]:
        """获取背包中的物品"""
        for item in self.inventory:
            if item.name == name:
                return item
        return None

    def get_character_sheet(self) -> str:
        """获取角色卡显示"""
        hp_bar = self._get_bar(self.hp_current, self.hp_max, "❤️")
        mp_bar = self._get_bar(self.mp_current, self.mp_max, "💙")
        
        # 状态标记
        lock_status = "🔒" if self.character_locked else "📝"
        
        sheet = f"""
╔══════════════════════════════╗
║  📜 {self.character_name} 的角色卡 {lock_status}
╠══════════════════════════════╣
║  等级: Lv.{self.level}  经验: {self.experience}
║  
║  ❤️ HP: {self.hp_current}/{self.hp_max} {hp_bar}
║  💙 MP: {self.mp_current}/{self.mp_max} {mp_bar}
║  
║  📊 属性:
║  {self.attributes.get_display().replace(chr(10), chr(10) + '║  ')}
║  
║  🎒 背包: {len(self.inventory)} 件物品
║  ⚔️ 技能: {', '.join(self.skills) if self.skills else '无'}
╚══════════════════════════════╝
"""
        return sheet.strip()

    def _get_bar(self, current: int, maximum: int, emoji: str) -> str:
        """生成进度条"""
        if maximum <= 0:
            return ""
        ratio = current / maximum
        filled = int(ratio * 10)
        return "█" * filled + "░" * (10 - filled)

    def get_inventory_display(self) -> str:
        """获取背包显示"""
        if not self.inventory:
            return "🎒 背包空空如也"
        
        lines = ["🎒 背包物品:"]
        for i, item in enumerate(self.inventory, 1):
            lines.append(f"  {i}. {item.name} x{item.quantity}")
            if item.description:
                lines.append(f"     └─ {item.description}")
        return "\n".join(lines)

    def is_alive(self) -> bool:
        """检查角色是否存活"""
        return self.hp_current > 0

    # ==================== 加点系统 ====================

    def allocate_point(self, attr_name: str, points: int = 1) -> Tuple[bool, str]:
        """
        分配属性点
        
        Args:
            attr_name: 属性名（支持简写）
            points: 要分配的点数（正数加点，负数减点）
            
        Returns:
            (成功, 消息)
        """
        if self.character_locked:
            return False, "角色已锁定，无法修改属性"
        
        # 标准化属性名
        attr_name_lower = attr_name.lower()
        if attr_name_lower in PlayerAttributes.ATTR_ALIASES:
            std_attr = PlayerAttributes.ATTR_ALIASES[attr_name_lower]
        elif hasattr(self.attributes, attr_name_lower):
            std_attr = attr_name_lower
        else:
            return False, f"未知属性: {attr_name}"
        
        # 检查点数是否足够
        if points > 0 and points > self.free_points:
            return False, f"点数不足！剩余 {self.free_points} 点，需要 {points} 点"
        
        # 计算新属性值
        current_value = self.attributes.get_attribute(std_attr)
        new_value = current_value + points
        
        # 检查属性范围
        if new_value > DEFAULT_MAX_ATTRIBUTE:
            return False, f"属性不能超过 {DEFAULT_MAX_ATTRIBUTE}！当前 {current_value}"
        if new_value < DEFAULT_MIN_ATTRIBUTE:
            return False, f"属性不能低于 {DEFAULT_MIN_ATTRIBUTE}！当前 {current_value}"
        
        # 减点时检查是否有足够的已分配点数
        if points < 0:
            allocated = self.points_allocated.get(std_attr, 0)
            if allocated + points < 0:
                return False, f"无法减点！该属性只分配了 {allocated} 点"
        
        # 应用变化
        self.attributes.set_attribute(std_attr, new_value)
        self.free_points -= points
        
        # 记录分配
        if std_attr not in self.points_allocated:
            self.points_allocated[std_attr] = 0
        self.points_allocated[std_attr] += points
        
        self.updated_at = time.time()
        
        change = f"+{points}" if points > 0 else str(points)
        return True, f"{attr_name} {current_value} → {new_value} ({change})，剩余 {self.free_points} 点"

    def lock_character(self) -> Tuple[bool, str]:
        """锁定角色，不再允许加点"""
        if self.character_locked:
            return False, "角色已经锁定"
        
        self.character_locked = True
        self.updated_at = time.time()
        return True, "角色已锁定，属性分配完成"

    def unlock_character(self) -> Tuple[bool, str]:
        """解锁角色（管理员功能）"""
        if not self.character_locked:
            return False, "角色未锁定"
        
        self.character_locked = False
        self.updated_at = time.time()
        return True, "角色已解锁"

    def reset_points(self) -> Tuple[bool, str]:
        """重置所有加点"""
        if self.character_locked:
            return False, "角色已锁定，无法重置"
        
        # 恢复所有属性到基础值
        total_refund = 0
        for attr, points in self.points_allocated.items():
            current = self.attributes.get_attribute(attr)
            self.attributes.set_attribute(attr, current - points)
            total_refund += points
        
        self.free_points += total_refund
        self.points_allocated = {}
        self.updated_at = time.time()
        
        return True, f"已重置所有加点，返还 {total_refund} 点，当前剩余 {self.free_points} 点"

    def get_points_display(self) -> str:
        """获取加点状态显示"""
        status = "🔒 已锁定" if self.character_locked else f"🎯 剩余 {self.free_points} 点"
        
        if self.points_allocated:
            allocated_str = ", ".join([
                f"{attr[:3].upper()}+{pts}" for attr, pts in self.points_allocated.items() if pts > 0
            ])
            if allocated_str:
                status += f"\n📊 已分配: {allocated_str}"
        
        return status
