import random
from core.utils import print_info, print_success, print_warning, print_error

class DiceSystem:
    """
    CoC (Call of Cthulhu) 风格的 D100 骰子系统
    """
    
    last_result = None

    @staticmethod
    def roll(expression="1d100"):
        """
        解析并投掷骰子表达式
        支持: "1d100", "2d6+3", "1d10-1"
        """
        import re
        match = re.match(r'(\d+)d(\d+)(?:([+-])(\d+))?', expression)
        if match:
            count = int(match.group(1))
            sides = int(match.group(2))
            operator = match.group(3)
            bonus = int(match.group(4) if match.group(4) else 0)
            
            rolls = [random.randint(1, sides) for _ in range(count)]
            total = sum(rolls)
            
            if operator == '+':
                total += bonus
            elif operator == '-':
                total -= bonus
                
            return max(1, total) # 最小为1
        return random.randint(1, 100)

    @staticmethod
    def parse_and_roll(text, character):
        """
        解析文本中的骰子请求并执行
        支持格式: [CHECK: 侦查] 或 {CHECK: 力量}
        """
        import re
        
        # 正则匹配 [CHECK: 技能名]
        pattern = re.compile(r'[\[\{]CHECK: ?(.+?)[\]\}]', re.IGNORECASE)
        
        def replace_func(match):
            check_name = match.group(1).strip()
            # 尝试在角色属性中查找对应技能或属性
            # 1. 精确匹配
            target_val = character.game_stats.get(check_name)
            
            # 2. 尝试加"技能_"前缀匹配 (如果AI只写了"侦查")
            if target_val is None:
                target_val = character.game_stats.get(f"技能_{check_name}")
                
            # 3. 尝试模糊匹配 (比如"Force" -> "STR")
            if target_val is None:
                map_dict = {"Force": "STR", "Strength": "STR", "Agility": "AGI", "Luck": "LUK", "Sanity": "SAN"}
                target_val = character.game_stats.get(map_dict.get(check_name, ""))
                
            # 4. 默认值
            if target_val is None:
                target_val = 50 # 默认 50
            
            roll_val, level, success = DiceSystem.check(check_name, target_val)
            
            # 构建结果字符串
            color = "green" if success else "red"
            outcome = "成功" if success else "失败"
            if level == "critical": outcome = "大成功!"
            if level == "fumble": outcome = "大失败!"
            
            return f"[[bold cyan]🎲 {check_name}判定[/bold cyan]: {roll_val}/{int(target_val)} -> [bold {color}]{outcome}[/bold {color}]]"
            
        return pattern.sub(replace_func, text)

    @staticmethod
    def check(check_name, target_value, silent=False):
        """
        进行一次 D100 检定 (通用 RPG 风格)
        :param check_name: 检定名称 (如 "敏捷", "幸运")
        :param target_value: 目标值 (属性值/技能值)
        :param silent: 是否静默 (不打印日志)
        :return: (roll_value, result_string, is_success)
        """
        roll_val = random.randint(1, 100)
        
        result_str = "失败"
        is_success = False
        level = "normal"
        
        # 1-5 大成功 (调整了范围，不那么苛刻)
        if roll_val <= 5: 
            result_str = "[bold gold1]大成功![/bold gold1] (Critical)"
            is_success = True
            level = "critical"
        # 96-100 大失败
        elif roll_val >= 96:
            result_str = "[bold red1]大失败![/bold red1] (Fumble)"
            is_success = False
            level = "fumble"
        # 困难成功 (1/2) - 即使属性低也有机会
        elif roll_val <= target_value // 2:
            result_str = "[green]卓越成功[/green] (Great Success)"
            is_success = True
            level = "hard"
        # 普通成功
        elif roll_val <= target_value:
            result_str = "成功"
            is_success = True
            level = "success"
        else:
            result_str = "失败"
            is_success = False
            level = "failure"
            
        if not silent:
            print_info(f"🎲 {check_name}检定({int(target_value)}): [cyan]{roll_val}[/cyan] -> {result_str}")
        DiceSystem.last_result = level
        return roll_val, level, is_success
