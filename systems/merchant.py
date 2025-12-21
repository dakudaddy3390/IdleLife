import random
import json
from rich.table import Table
from rich import print as rprint
from rich.panel import Panel
from core.utils import print_header, print_info, print_success, print_warning, print_error

class MerchantSystem:
    """NPC商人系统：动态生成商品"""
    
    NAMES = {
        "human": ["艾里克", "贝尔", "卡洛斯", "大卫", "爱德华", "弗兰克", "乔治", "亨利", "伊萨克", "杰克"],
        "elf": ["艾兰", "贝奥", "卡ael", "大eon", "爱el", "弗ean", "乔ar", "亨il", "伊sa", "杰en"], # 简化的精灵风
        "dwarf": ["昂", "霸", "卡", "大", "爱", "弗", "乔", "亨", "伊", "杰"], # 简化的矮人风 (这其实不太像，还是用通用英文音译吧)
        "general": ["托马斯", "安娜", "罗伯特", "玛丽", "威廉", "伊丽莎白", "理查德", "萨拉", "约瑟夫", "苏珊", 
                   "老杰克", "神秘客", "流浪者", "幽灵", "影子", "风行者", "铁胡子", "金牙"]
    }

    @staticmethod
    def generate_merchant_persona(race, level):
        """生成商人人设"""
        personas = [
            {"type": "旅行商", "desc": "走南闯北的精明商人", "bias": "general"},
            {"type": "黑市贩子", "desc": "眼神闪烁，兜售违禁品", "bias": "rare"},
            {"type": "炼金术士", "desc": "散发着药水气味", "bias": "magic"},
            {"type": "铁匠", "desc": "肌肉虬结的锻造师", "bias": "weapon"},
        ]
        
        # 根据种族调整
        if race == "精灵":
            personas.append({"type": "森林行商", "desc": "贩卖自然奇珍", "bias": "nature"})
        elif race == "矮人":
            personas.append({"type": "符文工匠", "desc": "贩卖强力装备", "bias": "weapon"})
            
        persona = random.choice(personas)
        
        # 简单分配名字
        name_pool = MerchantSystem.NAMES['general']
        if race == "精灵": name_pool = ["Legolas", "Thranduil", "Arwen", "Galadriel", "Elrond", "Tauriel"]
        if race == "矮人": name_pool = ["Gimli", "Thorin", "Balin", "Dwalin", "Gloin", "Oin"]
        
        persona['name'] = random.choice(name_pool)
        return persona

    @staticmethod
    def ai_generate_goods(ai, merchant_type, player_level, player_race):
        """使用AI生成动态商品列表"""
        # 数值平衡约束
        try:
            player_level = int(player_level)
        except:
            player_level = 1
            
        base_price = player_level * 50
        max_stat = max(2, int(player_level * 1.5))
        
        prompt = f"""作为一名{merchant_type}，请为一位Lv{player_level}的{player_race}冒险者生成3件待售商品。
要求：
1. 包含一件普通消耗品，一件适合该种族的特色物品，一件稀有的强力装备。
2. 价格要符合等级，参考基准金币：{base_price}。
3. 物品属性（攻击/防御）不应超过 {max_stat} 点太多，以免破坏平衡。
4. 物品名称要有奇幻感。
5. 请给商人起一个符合其种族和职业风格的名字（如东方修仙者叫‘云游道人’、‘李掌柜’，西方叫‘Old Tom’、‘Merchant Jack’等）。

请直接输出严谨的JSON格式（不要Markdown代码块）：
{{
  "merchant_name": "风格化名字",
  "goods": [
      {{
        "name": "物品名", 
        "type": "消耗品/武器/防具/饰品", 
        "stats": {{ "attack": 0, "defense": 0, "hp": 0, "mp": 0 }},
        "effect_desc": "简短的功能描述",
        "price": 100, 
        "desc": "描述"
      }},
      ...
  ]
}}
注意：stats字段数值为整数。
"""
        try:
            content, usage = ai.think_and_act(prompt)
            if content:
                import re
                json_match = re.search(r'\{.*\}', content.replace('\n', ' '), re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    items = data.get('goods', [])
                    name = data.get('merchant_name')
                    
                    for item in items:
                        if 'stats' not in item: item['stats'] = {}
                        if 'price' not in item: item['price'] = 10
                    return items, name, usage
        except Exception as e:
            print_error(f"商人进货失败: {e}")
            
        # 备用商品
        fallback_goods = [
            {"name": "急救包", "type": "消耗品", "stats": {"hp": 50}, "effect_desc": "恢复50点生命值", "price": 50, "desc": "基础的急救用品"},
            {"name": "铁剑", "type": "武器", "stats": {"attack": 5}, "effect_desc": "攻击力+5", "price": 200, "desc": "普通的铁剑"},
            {"name": "皮甲", "type": "防具", "stats": {"defense": 3}, "effect_desc": "防御力+3", "price": 150, "desc": "普通的皮甲"}
        ]
        return fallback_goods, None, {}

    @staticmethod
    def interact(player, ai, console):
        """商人交互主流程"""
        race = player.save_data.get('race', '人类')
        level = player.game_stats['等级']
        
        persona = MerchantSystem.generate_merchant_persona(race, level)
        
        # 1. 先调用 AI 生成名字和商品
        items, ai_name, usage = MerchantSystem.ai_generate_goods(ai, persona['type'], level, race)
        
        # 优先使用 AI 生成的名字
        final_name = ai_name if ai_name else persona.get('name', '神秘商人')
        full_name = f"{final_name} ({persona['type']})"
        
        print_header(f"💰 偶遇 {full_name}")
        print_info(f"{persona['desc']}")
        
        # 引入骰子系统进行砍价
        from systems.dice import DiceSystem
        
        # 使用社交技能(如有)或魅力属性进行砍价
        negotiate_skill = player.game_stats.get('技能_心理学', player.game_stats.get('CHA', 50))
        roll, level, success = DiceSystem.check("交涉", negotiate_skill)
        
        discount_msg = ""
        multiplier = 1.0
        
        if level == "critical":
            multiplier = 0.5
            discount_msg = "[bold gold1]大成功！[/bold gold1] 商人被你的魅力折服 (5折)"
        elif level == "hard" or level == "extreme":
            multiplier = 0.7
            discount_msg = "[green]卓越口才！[/green] (7折)"
        elif success:
            multiplier = 0.8
            discount_msg = "[green]讨价还价成功[/green] (8折)"
        elif level == "fumble":
            multiplier = 1.5
            discount_msg = "[bold red]大失败...[/bold red] 你不小心冒犯了商人 (1.5倍价格)"
        else:
            discount_msg = "交涉失败 (原价)"
            
        print_info(f"💬 正在讨价还价... {discount_msg}")
        print_info("正在整理货物...")
        
        # 商品已经生成好了 (items)，不需要再次调用 ai_generate_goods
        # 只需要应用折扣
        
        # 应用折扣
        for item in items:
            original_price = item.get('price', 100)
            item['price'] = int(original_price * multiplier)
        
        # 显示商品表格
        table = Table(title=f"{full_name}的商店 (你的金币: {player.game_stats['金币']})")
        table.add_column("序号", justify="right", style="cyan")
        table.add_column("商品", style="bold white")
        table.add_column("类型", style="green")
        table.add_column("功能/效果", style="magenta")
        table.add_column("价格", style="yellow")
        
        for i, item in enumerate(items, 1):
            # 优先使用 AI 生成的 effect_desc，没有则回退到 stats 拼接
            effect_text = item.get('effect_desc')
            if not effect_text:
                effect_text = ", ".join([f"{k}:{v}" for k,v in item.get('stats', {}).items() if v])
            
            table.add_row(str(i), item['name'], item['type'], effect_text, str(item['price']))
            
        console.print(table)
        
        # 购买逻辑
        bought = False
        for item in items:
            cost = item['price']
            if player.game_stats['金币'] >= cost:
                # 决定是否购买
                should_buy = False
                if item['type'] == "消耗品" and player.game_stats['HP'] < player.game_stats['MaxHP'] * 0.8:
                    should_buy = True
                elif item['type'] in ["武器", "防具", "饰品"]:
                    should_buy = True
                
                if should_buy:
                    player.game_stats['金币'] -= cost
                    player.inventory.append(item)
                    print_success(f"🛒 购买了 {item['name']} (-{cost}金币)")
                    bought = True
        
        if not bought:
            print_info("囊中羞涩，什么都没买...")
            
        return usage
