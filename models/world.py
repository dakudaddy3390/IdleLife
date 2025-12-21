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
        return "starter_village"

    def get_region(self, region_id):
        return self.regions.get(region_id, self.regions['starter_village'])

    def get_random_event_type(self, region_id):
        region = self.get_region(region_id)
        weights = region['事件权重']
        
        # 小概率奇遇事件
        if random.random() < 0.05:
            return "奇遇"
        
        # 简单的加权随机
        choices = []
        for k, v in weights.items():
            choices.extend([k] * v)
        return random.choice(choices)

    def get_monster(self, region_id, player_level=1):
        region = self.get_region(region_id)
        monster_name = random.choice(region['怪物'])
        monster_data = self.monsters.get(monster_name).copy()
        monster_data['名称'] = monster_name
        
        # 动态属性平衡: 根据玩家等级调整怪物强度
        # 假设怪物模板是 Lv1 标准
        # 每级 +10% 属性
        scale = 1.0 + (player_level - 1) * 0.1
        monster_data['攻击'] = int(monster_data.get('攻击', 5) * scale)
        monster_data['防御'] = int(monster_data.get('防御', 0) * scale)
        monster_data['HP'] = int(monster_data.get('HP', 20) * scale)
        monster_data['经验'] = int(monster_data.get('经验', 10) * scale) # 经验也随等级增加
        monster_data['等级'] = player_level # 怪物等级跟随玩家
        
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
        npc['名称'] = name
        npc['职业'] = npc.get('职业', '居民')
        npc['描述'] = npc.get('描述', '一个普通的居民')
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
    
    def get_item_by_name(self, name):
        """根据名称查找物品"""
        for item in self.items:
            if item.get('名称') == name or item.get('name') == name:
                return item.copy()
        return None
