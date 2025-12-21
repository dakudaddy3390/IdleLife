import json
import random

class GameWorld:
    def __init__(self, config):
        world_file = config.get_world_file()
        with open(world_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.regions = {r['id']: r for r in self.data['地区']}
        self.monsters = self.data.get('怪物模板', {})
        self.events = self.data.get('事件模板', {})
        self.items = self.data.get('物品列表', [])
        # 兼容两种命名
        self.npcs = self.data.get('NPC模板', self.data.get('NPC', {}))
        self.bosses = self.data.get('Boss模板', {})
        self.adventures = self.data.get('奇遇事件', [])

    def get_starting_location(self):
        """获取初始地点ID"""
        if self.data.get('地区'):
            return self.data['地区'][0]['id']
        # 万一没有任何地区配置，才返回硬编码，但通常不会发生
        return "starter_village"

    def get_region(self, region_id):
        if not self.regions: return None
        # 如果找不到指定ID，就返回第一个地区作为默认，而不是硬编码 starter_village
        return self.regions.get(region_id, list(self.regions.values())[0])

    def get_random_event_type(self, region_id):
        region = self.get_region(region_id)
        if not region: return "探索" # Fallback
        
        weights = region.get('事件权重', {'探索': 100}).copy()
        
        # 动态平衡：确保探索权重不低于战斗，防止战斗过于频繁
        combat_w = weights.get('战斗', 0)
        explore_w = weights.get('探索', 0)
        if combat_w > explore_w:
            weights['探索'] = combat_w + 20 # 强制让探索比战斗多一点
            
        # 小概率奇遇事件
        if random.random() < 0.05:
            return "奇遇"
        
        # 简单的加权随机
        choices = []
        for k, v in weights.items():
            choices.extend([k] * v)
        if not choices: return "探索"
        return random.choice(choices)

    def get_random_exploration_text(self):
        """获取随机探索描述"""
        if self.events and '探索' in self.events:
            return random.choice(self.events['探索'])
        return "你在周围探索了一番，没有发现什么特别的东西。"

    def get_monster(self, region_id, player_level=1):
        region = self.get_region(region_id)
        if not region or not region.get('怪物'):
            # Fallback if no monsters in region
            return {"名称": "未知的影子", "攻击": 5, "防御": 0, "HP": 10, "经验": 5, "等级": 1}
            
        monster_name = random.choice(region['怪物'])
        raw_data = self.monsters.get(monster_name)
        
        if not raw_data:
            # 防御性编程：如果模板里没这个怪，生成一个通用的
            monster_data = {
                "名称": monster_name,
                "攻击": 5 + player_level, 
                "防御": 0, 
                "HP": 20 + player_level * 5, 
                "经验": 10,
                "描述": "一只神秘的生物"
            }
        else:
            monster_data = raw_data.copy()
            monster_data['名称'] = monster_name
        
        # 动态属性平衡 v2.0: 基于怪物预设等级进行微调
        # 怪物模板中已有合理的等级和数值，此处只做轻微动态调整
        monster_level = monster_data.get('等级', 1)
        
        # 计算等级差: 玩家等级 vs 怪物等级
        # 如果玩家等级高于怪物，怪物略微增强；反之略微减弱
        level_diff = player_level - monster_level
        # 每级差距 ±3% 调整，最大 ±30%
        scale = 1.0 + max(-0.3, min(0.3, level_diff * 0.03))
        
        # 只对基础属性做微调，不再暴力翻倍
        monster_data['攻击'] = int(monster_data.get('攻击', 5) * scale)
        monster_data['防御'] = int(monster_data.get('防御', 0) * scale)
        monster_data['HP'] = int(monster_data.get('hp', monster_data.get('HP', 20)) * scale)
        monster_data['经验'] = int(monster_data.get('经验', 10) * max(1.0, scale))
        
        # 使用怪物模板中预设的等级，不强制跟随玩家
        # monster_data['等级'] 保持模板值
        
        # 补充属性以便使用技能 (基于怪物等级)
        monster_data['INT'] = monster_level * 5 + 10
        monster_data['AGI'] = monster_level * 5 + 10
        monster_data['STR'] = monster_level * 5 + 10
        monster_data['MaxMP'] = monster_level * 20 + 50
        monster_data['MP'] = monster_data['MaxMP']
        
        # 使用怪物模板中预设的技能（已在JSON中配置）
        # 如果模板没有技能，则不额外添加
        if 'skills' not in monster_data:
            monster_data['skills'] = []
        
        return monster_data
    
    def get_random_npc(self, npc_type=None):
        """获取随机NPC，可指定类型"""
        available = []
        if isinstance(self.npcs, dict):
            for name, data in self.npcs.items():
                if not isinstance(data, dict): continue
                if npc_type is None or data.get('类型') == npc_type:
                    available.append((name, data))
                    
        if not available:
            return None
        name, data = random.choice(available)
        npc = data.copy()
        
        # 为NPC生成随机名字
        western_names = ["艾里克", "卡洛斯", "爱德华", "乔治", "亨利", "杰克", "托马斯", "安娜", "玛丽", "萨拉", "苏珊", "莉莉", "露娜", "凯温"]
        eastern_names = ["云舒", "子轩", "无忌", "灵儿", "青璇", "少云", "语嫣", "天放", "婉儿", "长风", "若曦", "惊鸿", "慕白", "清扬"]
        cyberpunk_names = ["V", "Johnny", "Evelyn", "Panam", "Rogue", "Judy", "River", "Jackie", "Kerry", "Alt"]
        
        # 根据世界背景判断风格
        world_name = self.data.get('世界名称', '')
        world_style = self.data.get('世界风格', '')
        
        is_eastern_world = any(k in world_name + world_style for k in ['仙', '武', '古', '玄', '修', '道', '侠', '唐', '宋', '明'])
        is_cyberpunk_world = any(k in world_name + world_style for k in ['赛博', '朋克', '科幻', '未来', '霓虹', 'cyber', 'punk'])
        
        # 再根据NPC原有名称/类型判断 (覆盖世界默认)
        is_eastern_npc = any(k in name for k in ['师', '侠', '道', '仙', '僧', '儒', '妖', '魔', '宗', '门', '古', '龙', '剑', '琴'])
        
        if is_eastern_npc or is_eastern_world:
             random_name = random.choice(eastern_names)
        elif is_cyberpunk_world:
             random_name = random.choice(cyberpunk_names)
        else:
             random_name = random.choice(western_names)
        
        if len(name) < 6: 
             npc['名称'] = f"{random_name} ({name})"
        else:
             npc['名称'] = name
             
        npc['职业'] = npc.get('职业', '居民')
        
        # 补全描述
        if '描述' not in npc:
            npc['描述'] = f"一位看起来很普通的{npc['职业']}。"
            
        return npc
    
    def get_boss(self, region_id):
        """获取指定地区的Boss"""
        for name, boss in self.bosses.items():
            if region_id in boss.get('出现地区', []):
                boss_data = boss.copy()
                boss_data['名称'] = name
                boss_data['is_boss'] = True
                return boss_data
        return None
    
    def get_random_adventure(self):
        """根据概率获取奇遇事件"""
        for adv in self.adventures:
            if random.random() < adv.get('概率', 0.01):
                return adv
        return random.choice(self.adventures) if self.adventures else None
    
    def get_encounter(self, region_id, player_level):
        """获取遭遇（可能是怪物、NPC战斗、或Boss）"""
        # 小概率Boss（等级足够时）
        region = self.get_region(region_id)
        min_level = region.get('等级范围', [1, 5])[0]
        
        if player_level >= min_level + 5 and random.random() < 0.05:
            boss = self.get_boss(region_id)
            if boss:
                return boss
        
        # 小概率NPC战斗（不打不相识）
        if random.random() < 0.15:
            npc = self.get_random_npc('可结伴')
            if npc:
                npc['is_npc_battle'] = True
                return npc
        
        # 普通怪物
        return self.get_monster(region_id, player_level)
    
    def get_random_item(self):
        """随机获取一个物品"""
        if self.items:
            return random.choice(self.items).copy()
        return None

    def get_item_by_name(self, name):
        """根据名称查找物品"""
        for item in self.items:
            if item.get('名称') == name or item.get('name') == name:
                return item.copy()
        return None
