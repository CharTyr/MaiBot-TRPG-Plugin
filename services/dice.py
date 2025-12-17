"""
骰子服务 - 处理所有骰子相关的逻辑
"""

import re
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class DiceResult:
    """骰子结果"""
    expression: str           # 原始表达式
    total: int               # 总结果
    rolls: List[int]         # 每个骰子的结果
    modifier: int = 0        # 修正值
    dice_count: int = 1      # 骰子数量
    dice_sides: int = 20     # 骰子面数
    is_critical: bool = False    # 是否大成功
    is_fumble: bool = False      # 是否大失败
    description: str = ""    # 结果描述

    def get_display(self) -> str:
        """获取显示文本"""
        rolls_str = ", ".join(str(r) for r in self.rolls)
        
        result_text = f"🎲 {self.expression}\n"
        result_text += f"骰子: [{rolls_str}]"
        
        if self.modifier != 0:
            sign = "+" if self.modifier > 0 else ""
            result_text += f" {sign}{self.modifier}"
        
        result_text += f"\n结果: {self.total}"
        
        if self.is_critical:
            result_text += " 🌟 大成功！"
        elif self.is_fumble:
            result_text += " 💀 大失败！"
        
        if self.description:
            result_text += f"\n{self.description}"
        
        return result_text


class DiceService:
    """骰子服务"""

    # 骰子表达式正则: XdY+Z 或 XdY-Z 或 dY 或 XdY
    DICE_PATTERN = re.compile(
        r'^(\d*)d(\d+)([+-]\d+)?$',
        re.IGNORECASE
    )
    
    # 复杂表达式: 支持多个骰子组合，如 2d6+1d4+3
    COMPLEX_PATTERN = re.compile(
        r'(\d*)d(\d+)|([+-]?\d+)',
        re.IGNORECASE
    )

    def __init__(self, max_dice_count: int = 100, max_dice_sides: int = 1000):
        self.max_dice_count = max_dice_count
        self.max_dice_sides = max_dice_sides

    def roll(self, expression: str) -> DiceResult:
        """
        掷骰子
        
        支持的格式:
        - d20: 掷一个20面骰
        - 2d6: 掷两个6面骰
        - 3d6+5: 掷三个6面骰加5
        - 2d10-2: 掷两个10面骰减2
        - 2d6+1d4+3: 复杂表达式
        """
        expression = (expression or "").strip().lower().replace(" ", "")
        if not expression:
            expression = "d20"
        
        # 尝试简单表达式
        simple_match = self.DICE_PATTERN.match(expression)
        if simple_match:
            return self._roll_simple(expression, simple_match)
        
        # 尝试复杂表达式
        return self._roll_complex(expression)

    def _roll_simple(self, expression: str, match: re.Match) -> DiceResult:
        """处理简单骰子表达式"""
        count_str, sides_str, modifier_str = match.groups()
        
        count = int(count_str) if count_str else 1
        sides = int(sides_str)
        modifier = int(modifier_str) if modifier_str else 0
        
        # 基础校验
        if count < 1:
            raise ValueError("骰子数量必须 >= 1")
        if sides < 1:
            raise ValueError("骰子面数必须 >= 1")

        # 验证限制
        if count > self.max_dice_count:
            raise ValueError(f"单次最大骰子数量为 {self.max_dice_count}")
        if sides > self.max_dice_sides:
            raise ValueError(f"单个骰子最大面数为 {self.max_dice_sides}")
        
        # 掷骰子
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier
        
        # 检查大成功/大失败 (仅对单个d20)
        is_critical = count == 1 and sides == 20 and rolls[0] == 20
        is_fumble = count == 1 and sides == 20 and rolls[0] == 1
        
        return DiceResult(
            expression=expression,
            total=total,
            rolls=rolls,
            modifier=modifier,
            dice_count=count,
            dice_sides=sides,
            is_critical=is_critical,
            is_fumble=is_fumble,
        )

    def _roll_complex(self, expression: str) -> DiceResult:
        """处理复杂骰子表达式"""
        all_rolls = []
        total = 0
        modifier = 0
        
        # 处理表达式开头可能没有符号的情况
        if expression and expression[0] not in '+-':
            expression = '+' + expression
        
        token_re = re.compile(r'([+-])(\d*d\d+|\d+)', re.IGNORECASE)
        pos = 0
        for m in token_re.finditer(expression):
            if m.start() != pos:
                raise ValueError(f"骰子表达式无效: {expression}")
            pos = m.end()

            sign = 1 if m.group(1) == "+" else -1
            term = m.group(2)

            if "d" in term:
                count_str, sides_str = term.split("d", 1)
                count = int(count_str) if count_str else 1
                sides = int(sides_str)

                if count < 1:
                    raise ValueError("骰子数量必须 >= 1")
                if sides < 1:
                    raise ValueError("骰子面数必须 >= 1")
                if count > self.max_dice_count:
                    raise ValueError(f"单次最大骰子数量为 {self.max_dice_count}")
                if sides > self.max_dice_sides:
                    raise ValueError(f"单个骰子最大面数为 {self.max_dice_sides}")

                rolls = [random.randint(1, sides) for _ in range(count)]
                all_rolls.extend([r * sign for r in rolls])
                total += sum(rolls) * sign
            else:
                num = int(term)
                modifier += num * sign
                total += num * sign

        if pos != len(expression):
            raise ValueError(f"骰子表达式无效: {expression}")
        
        return DiceResult(
            expression=expression.lstrip('+'),
            total=total,
            rolls=[abs(r) for r in all_rolls],  # 显示绝对值
            modifier=modifier,
            dice_count=len(all_rolls),
            dice_sides=0,  # 复杂表达式不记录单一面数
        )

    def roll_check(self, attribute_value: int, difficulty: int = 10, 
                   modifier: int = 0) -> Tuple[DiceResult, bool, str]:
        """
        属性检定
        
        Args:
            attribute_value: 属性值
            difficulty: 难度等级 (DC)
            modifier: 额外修正值
        
        Returns:
            (骰子结果, 是否成功, 描述)
        """
        # 计算属性调整值 (D&D 风格)
        attr_modifier = (attribute_value - 10) // 2
        total_modifier = attr_modifier + modifier
        
        # 掷d20
        result = self.roll(f"d20{total_modifier:+d}" if total_modifier else "d20")
        
        # 判定成功
        success = result.total >= difficulty
        
        # 生成描述
        if result.is_critical:
            description = "大成功！无论如何都成功了！"
            success = True
        elif result.is_fumble:
            description = "大失败！无论如何都失败了！"
            success = False
        elif success:
            margin = result.total - difficulty
            description = f"成功！(超过DC {margin}点)"
        else:
            margin = difficulty - result.total
            description = f"失败！(差 {margin}点)"
        
        result.description = description
        return result, success, description

    def roll_opposed(self, attr1: int, attr2: int, 
                     mod1: int = 0, mod2: int = 0) -> Tuple[DiceResult, DiceResult, int, str]:
        """
        对抗检定
        
        Args:
            attr1: 发起方属性值
            attr2: 对抗方属性值
            mod1: 发起方额外修正
            mod2: 对抗方额外修正
        
        Returns:
            (发起方结果, 对抗方结果, 胜者(1/-1/0), 描述)
        """
        mod1_total = (attr1 - 10) // 2 + mod1
        mod2_total = (attr2 - 10) // 2 + mod2
        
        result1 = self.roll(f"d20{mod1_total:+d}" if mod1_total else "d20")
        result2 = self.roll(f"d20{mod2_total:+d}" if mod2_total else "d20")
        
        if result1.total > result2.total:
            winner = 1
            description = f"发起方胜出！({result1.total} vs {result2.total})"
        elif result2.total > result1.total:
            winner = -1
            description = f"对抗方胜出！({result1.total} vs {result2.total})"
        else:
            winner = 0
            description = f"平局！({result1.total} vs {result2.total})"
        
        return result1, result2, winner, description

    @staticmethod
    def quick_roll(sides: int = 20, count: int = 1) -> List[int]:
        """快速掷骰子，返回结果列表"""
        return [random.randint(1, sides) for _ in range(count)]

    @staticmethod
    def roll_with_advantage(sides: int = 20) -> Tuple[int, int, int]:
        """优势骰 - 掷两次取高"""
        roll1 = random.randint(1, sides)
        roll2 = random.randint(1, sides)
        return max(roll1, roll2), roll1, roll2

    @staticmethod
    def roll_with_disadvantage(sides: int = 20) -> Tuple[int, int, int]:
        """劣势骰 - 掷两次取低"""
        roll1 = random.randint(1, sides)
        roll2 = random.randint(1, sides)
        return min(roll1, roll2), roll1, roll2
