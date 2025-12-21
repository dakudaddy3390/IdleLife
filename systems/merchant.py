import random
import json
from rich.table import Table
from rich import print as rprint
from rich.panel import Panel
from core.utils import print_header, print_info, print_success, print_warning, print_error

class MerchantSystem:
    """NPC商人系统：动态生成商品"""
    
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
        if race == "矮人":
            personas.append({"type": "符文工匠", "desc": "贩卖强力装备", "bias": "weapon"})
            
        return random.choice(personas)

    @staticmethod
    def ai_generate_goods(ai, merchant_type, player_level, player_race):
        """使用AI生成动态商品列表"""
        # 数值平衡约束
        base_price = player_level * 50
        max_stat = max(2, int(player_level * 1.5))
        
        prompt = f"""作为一名{merchant_type}，请为一位Lv{player_level}的{player_race}冒险者生成3件待售商品。
要求：
1. 包含一件普通消耗品，一件适合该种族的特色物品，一件稀有的强力装备。
2. 价格要符合等级，参考基准金币：{base_price}。
3. 物品属性（攻击/防御）不应超过 {max_stat} 点太多，以免破坏平衡。
4. 物品名称要有奇幻感。

请直接输出严谨的JSON列表格式（不要Markdown代码块）：
[
  {{
    "name": "物品名", 
    "type": "消耗品/武器/防具/饰品", 
    "stats": {{ "attack": 0, "defense": 0, "hp": 0, "mp": 0 }},
    "price": 100, 
    "desc": "描述"
  }},
  ...
]
注意：stats字段必须存在，数值为整数。效果描述写在desc里。
"""
        try:
            content, usage = ai.think_and_act(prompt)
            if content:
                # 尝试解析JSON
                import re
                json_match = re.search(r'\[.*\]', content.replace('\n', ' '), re.DOTALL)
                if json_match:
                    items = json.loads(json_match.group())
                    # 简单验证结构
                    for item in items:
                        if 'stats' not in item: item['stats'] = {}
                        if 'price' not in item: item['price'] = 10
                    return items, usage
        except Exception as e:
            print_error(f"商人进货失败: {e}")
            
        # 备用商品
        return [
            {"name": "急救包", "type": "消耗品", "stats": {"hp": 50}, "price": 50, "desc": "基础的急救用品"},
            {"name": "铁剑", "type": "武器", "stats": {"attack": 5}, "price": 200, "desc": "普通的铁剑"},
            {"name": "皮甲", "type": "防具", "stats": {"defense": 3}, "price": 150, "desc": "普通的皮甲"}
        ], {}

    @staticmethod
    def interact(player, ai, console):
        """商人交互主流程"""
        race = player.save_data.get('race', '人类')
        level = player.game_stats['等级']
        
        persona = MerchantSystem.generate_merchant_persona(race, level)
        name = persona['type']
        
        print_header(f"💰 偶遇 {name}")
        print_info(f"{persona['desc']}")
        print_info("正在整理货物...")
        
        items, usage = MerchantSystem.ai_generate_goods(ai, name, level, race)
        
        # 显示商品表格
        table = Table(title=f"{name}的商店 (你的金币: {player.game_stats['金币']})")
        table.add_column("序号", justify="right", style="cyan")
        table.add_column("商品", style="bold white")
        table.add_column("类型", style="green")
        table.add_column("效果", style="magenta")
        table.add_column("价格", style="yellow")
        
        for i, item in enumerate(items, 1):
            stats_str = ", ".join([f"{k}:{v}" for k,v in item.get('stats', {}).items() if v])
            table.add_row(str(i), item['name'], item['type'], stats_str, str(item['price']))
            
        console.print(table)
        
        # 购买逻辑（目前自动购买最强或随机，或者增加交互？）
        # 用户要求"爽点"，可以让AI决策或暂停等待用户输入
        # 这里为了保持放置游戏的流畅性，我们设定：如果金币足够且物品比当前好（或者消耗品），则购买
        
        bought = False
        for item in items:
            cost = item['price']
            if player.game_stats['金币'] >= cost:
                # 决定是否购买
                should_buy = False
                if item['type'] == "消耗品" and player.game_stats['HP'] < player.game_stats['MaxHP'] * 0.8:
                    should_buy = True
                elif item['type'] in ["武器", "防具", "饰品"]:
                    # 简单逻辑：有钱就买装备，假定新装备无论是啥都值得收藏/装备
                    should_buy = True
                
                if should_buy:
                    player.game_stats['金币'] -= cost
                    player.inventory.append(item)
                    print_success(f"🛒 购买了 {item['name']} (-{cost}金币)")
                    bought = True
        
        if not bought:
            print_info("囊中羞涩，什么都没买...")
            
        return usage
