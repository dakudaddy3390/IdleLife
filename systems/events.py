import random
import json
from core.utils import print_info, print_warning, print_error, print_success
from core.templates import TRAIT_TEMPLATE, SKILL_TEMPLATE, EVENT_TEMPLATE

class DynamicEventSystem:
    """
    动态事件系统：利用AI生成无限的随机事件
    """
    
    @staticmethod
    def generate_random_event(ai, player, region):
        """生成一个随机事件"""
        # region is a dict passed from GameWorld.get_region
        region_name = region.get('name', '未知区域')
        region_desc = region.get('desc', '神秘的地方')
        
        # 数值约束
        max_val = player.game_stats['等级'] * 20
        
        prompt = f"""
请为一款文字放置游戏生成一个随机事件。
背景：{region_name} (描述: {region_desc})
玩家：{player.name} (种族:{player.save_data.get('race')}, Lv{player.game_stats['等级']})

请生成一个JSON对象，严格遵守以下格式：
{EVENT_TEMPLATE}

【重要约束】：
1. 数值奖励/惩罚不应超过 {max_val} 点。
2. 如果奖励是特质(trait)，**必须**包含modifiers字段，指定具体的属性加成！
3. 如果是物品，**必须**包含stats字段。
4. 不要输出null或None，必须是有效的数值。

【示例1 - HP恢复】：
{{"title": "神秘泉水", "description": "路边的一口泉水散发着微光。",
  "choices": [{{"text": "饮用", "effect": "hp", "value": 50}}]}}

【示例2 - 获得物品】：
{{"title": "宝箱", "description": "发现一个古老的宝箱。",
  "choices": [{{"text": "打开", "effect": "item", "value": {{"name": "古老指环", "type": "饰品", "stats": {{"LUK": 5}}}}}}]}}

【示例3 - 获得特质（注意modifiers必填！）】：
{{"title": "神秘祝福", "description": "神殿中的神像闪烁微光。",
  "choices": [{{"text": "祈祷", "effect": "trait", "value": {{"name": "神眷者", "desc": "受到神明的庇护", "modifiers": {{"LUK": 2, "MaxHP": 10}}}}}}]}}
"""
        try:
            content, usage = ai.think_and_act(prompt)
            if content:
                # 提取JSON
                import re
                json_match = re.search(r'\{.*\}', content.replace('\n', ' '), re.DOTALL)
                if json_match:
                    event_data = json.loads(json_match.group())
                    return event_data, usage
        except Exception as e:
            print_error(f"事件生成失败: {e}")
            
        return None, None

    @staticmethod
    def handle_event(player, event_data, console):
        """处理动态事件交互"""
        from rich.panel import Panel
        
        console.print(Panel(f"[bold]{event_data['title']}[/bold]\n\n{event_data['description']}", title="🔮 奇遇", border_style="magenta"))
        
        choices = event_data.get('choices', [])
        if not choices:
            return 
            
        for i, choice in enumerate(choices, 1):
            console.print(f"[{i}] {choice['text']}")
            
        # 放置游戏通常自动选择，或者随机选择
        # 为了增加随机性，我们随机选一个
        import time
        time.sleep(1)
        
        choice_idx = random.randint(0, len(choices)-1)
        selected = choices[choice_idx]
        
        print_info(f"\n👉 你选择了: {selected['text']}")
        
        # 结算效果
        effect = selected.get('effect')
        val = selected.get('value', 0)
        
        if effect == 'gold':
            player.game_stats['金币'] += val
            change = "获得" if val > 0 else "失去"
            print_info(f"💰 {change}了 {abs(val)} 金币")
        elif effect == 'exp':
            if val > 0: player.gain_exp(val)
        elif effect == 'hp':
            if val > 0: player.heal(hp=val)
            else: player.take_damage(abs(val))
        elif effect == 'mp':
            if val > 0: player.heal(mp=val)
            else: player.game_stats['MP'] = max(0, player.game_stats['MP'] + val)
            
        elif effect == 'trait':
            # 获得新特质
            trait_data = selected.get('value')
            if isinstance(trait_data, dict):
                t_name = trait_data.get('name', '未知特质')
                
                # 确保特质有有效的modifiers
                modifiers = trait_data.get('modifiers')
                if not modifiers or modifiers == 'None' or modifiers == 'null':
                    # 根据特质名猜测一个合理的默认效果
                    stat_options = ['STR', 'AGI', 'INT', 'CON', 'CHA', 'LUK']
                    random_stat = random.choice(stat_options)
                    default_bonus = random.randint(1, 3)
                    modifiers = {random_stat: default_bonus}
                    trait_data['modifiers'] = modifiers
                
                # 1. 存入 custom_traits
                if 'custom_traits' not in player.save_data:
                    player.save_data['custom_traits'] = {}
                player.save_data['custom_traits'][t_name] = trait_data
                
                # 2. 加入后天特质列表
                if 'acquired_traits' not in player.save_data:
                    player.save_data['acquired_traits'] = []
                player.save_data['acquired_traits'].append(t_name)
                
                # 格式化效果显示
                effect_str = ", ".join([f"{k}+{v}" for k, v in modifiers.items()]) if modifiers else "神秘效果"
                
                print_success(f"🧬 获得了新特质: [{t_name}] {trait_data.get('desc', '')}")
                print_info(f"   效果: {effect_str}")
                
        elif effect == 'item':
            item_data = selected.get('value')
            if isinstance(item_data, dict):
                player.inventory.append(item_data)
                print_success(f"🎁 获得了物品: {item_data.get('name', '未知物品')}")
                if 'stats' in item_data:
                     print_info(f"   属性: {item_data['stats']}")
            
        return True
