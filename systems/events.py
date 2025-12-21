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

数值约束：
1. 奖励或惩罚的绝对值不应超过 {max_val} 点。
2. 如果奖励是特质(trait)或技能(skill)，请确保数值平衡且有趣。
3. 如果是物品，请提供 `stats` 字典 (如 {{"attack": 5, "defense": 0}})。
4. 确保 "value" 字段的数据类型正确（数字/字典）。

示例输出：
{{
    "title": "神秘泉水",
    "description": "路边的一口泉水散发着微光。",
    "choices": [
        {{"text": "饮用", "effect": "hp", "value": 50}},
        {{"text": "寻找宝物", "effect": "item", "value": {{"name": "古老指环", "type": "饰品", "stats": {{"luck": 5}}}}}}
    ]
}}
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
                # 1. 存入 custom_traits
                if 'custom_traits' not in player.save_data:
                    player.save_data['custom_traits'] = {}
                player.save_data['custom_traits'][t_name] = trait_data
                
                # 2. 只有在此刻获得，但基因里可能没有？
                # 我们可以强行把这个特质加到基因组里吗？或者加到额外的 "acquired_traits" 列表？
                # 简单起见，我们假设这是 "后天特质"，不进基因，但进生效列表
                # 为了兼容，我们把它加到 genome 的 "custom_genes" 字段? 
                # 或者：直接修改 get_traits 逻辑读取 acquired_traits
                if 'acquired_traits' not in player.save_data:
                    player.save_data['acquired_traits'] = []
                player.save_data['acquired_traits'].append(t_name)
                
                print_success(f"🧬 获得了新特质: [{t_name}] {trait_data.get('desc', '')}")
                print_info(f"   效果: {trait_data.get('modifiers')}")
                
        elif effect == 'item':
            item_data = selected.get('value')
            if isinstance(item_data, dict):
                player.inventory.append(item_data)
                print_success(f"🎁 获得了物品: {item_data.get('name', '未知物品')}")
                if 'stats' in item_data:
                     print_info(f"   属性: {item_data['stats']}")
            
        return True
