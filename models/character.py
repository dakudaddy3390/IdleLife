import json
import time
import os
import sys
import uuid
import random
from datetime import datetime
from rich import print as rprint
from core.utils import print_info, print_success, print_warning, print_error
from systems.genetics import GeneticSystem
from systems.race import RaceSystem

class Character:
    """角色类：管理角色状态、存档和属性"""
    
    def __init__(self, config, reset_save=False, save_file=None):
        self.profile_path = config.get_character_file()
        self.config = config
        # 根据角色ID创建不同的存档
        char_id = config.characters[config.active_char_idx].get('id', 'default') if config.characters else 'default'
        
        # 确保存档目录存在
        if not os.path.exists('saves'):
            os.makedirs('saves')
            
        if reset_save:
            # 新建存档：save_{char_id}_{YYMMDD_HHMM}.json
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_path = os.path.join('saves', f'save_{char_id}_{now}.json')
            self.load(force_init=True)
        elif save_file:
            # 显式指定存档文件
            self.save_path = save_file
            self.load()
        else:
            # 兼容旧逻辑: 优先找最新的 save_{char_id}_*.json，没有则用 save_{char_id}.json
            self.save_path = self._find_latest_save(char_id)
            self.load()
            
    def _find_latest_save(self, char_id):
        """寻找最新的存档"""
        try:
            files = [f for f in os.listdir('saves') if f.startswith(f'save_{char_id}_') and f.endswith('.json')]
            if files:
                # 按文件名(包含时间戳)排序，取最后的
                files.sort(reverse=True)
                return os.path.join('saves', files[0])
        except: pass
        
        # Fallback to root or old style
        old_path = f'save_{char_id}.json'
        if os.path.exists(old_path): return old_path
        
        # 默认新路径
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join('saves', f'save_{char_id}_{now}.json')

    def load(self, force_init=False):
        # 加载只读的角色资料
        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                self.profile = json.load(f)
        except Exception as e:
            print_error(f"加载角色资料失败: {e}")
            sys.exit(1)

        # 加载或初始化游戏存档
        if force_init or not os.path.exists(self.save_path):
            self.init_save()
            return
        
        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                self.save_data = json.load(f)
            # 兼容性检查：确保新字段存在
            if 'equipment' not in self.save_data:
                self.save_data['equipment'] = {"weapon": None, "armor": None, "accessory": None}
            if 'event_history' not in self.save_data:
                self.save_data['event_history'] = []
            if 'summary' not in self.save_data:
                self.save_data['summary'] = ""
            print_success(f"成功加载存档: {self.save_path}")
        except Exception as e:
            print_warning(f"加载存档失败或存档损坏: {self.save_path}. 错误: {e}. 正在初始化新存档...")
            self.init_save()

        self.game_stats = self.save_data.get('base_stats', {})
        self.inventory = self.save_data.get('inventory', [])

        # 兼容性修复：确保核心六维属性存在
        required_stats = ['力量', '敏捷', '智力', '体质', '魅力', '幸运']
        if any(k not in self.game_stats for k in required_stats):
            print_warning("检测到旧存档缺少核心属性，正在基于基因组重建...")
            genome = self.save_data.get('player_genome', {})
            if not genome: # 极老存档可能连genome都没有
                 genome = GeneticSystem.generate_random_genome()
                 self.save_data['player_genome'] = genome
            
            phenotype = GeneticSystem.express_phenotype(genome)
            mapping = {
                '力量': 'STR', '敏捷': 'AGI', '智力': 'INT',
                '体质': 'CON', '魅力': 'CHA', '幸运': 'LUK'
            }
            for stat_k, gene_k in mapping.items():
                if stat_k not in self.game_stats:
                    self.game_stats[stat_k] = phenotype.get(gene_k, 2) # 默认值2 (aa)
            
            self.save() # 保存修复后的数据
    
    def init_save(self):
        # 生成角色唯一ID
        char_id = str(uuid.uuid4())[:8]
        
        # 生成初始角色的随机基因组
        genome = GeneticSystem.generate_random_genome()
        gene_score = GeneticSystem.calculate_gene_score(genome)
        gene_desc = GeneticSystem.describe_genome(genome)
        
        print_info(f"🧬 角色基因生成: {gene_desc}")
        
        # 初始化种族和年龄
        race = RaceSystem.infer_race(self.profile)
        age = 18  # 初始年龄
        max_age = RaceSystem.calculate_max_age(race, 1)
        
        # 获取表型属性 (2-6)
        phenotype = GeneticSystem.express_phenotype(genome)
        
        print_info(f"👤 种族: {race} | 初始年龄: {age}岁 | 预期寿命: {max_age}岁")
        
        # 初始化存档数据
        self.save_data = {
            "current_character_id": char_id,
            "player_genome": genome,  # 保存基因组
            "player_gene_score": gene_score,
            "race": race,
            "age": age,
            "max_age": max_age,
            "world_id": self.config.worlds[self.config.active_world_idx]['id'] if hasattr(self.config, 'worlds') else 'eldoria',
            "custom_skills": [], # AI领悟的技能
            
            # 保存自定义数据
            "custom_races": RaceSystem.RACES.copy(),
            "custom_traits": GeneticSystem.TRAITS.copy(),
            
            "base_stats": {
                # 核心六维属性 (STR, AGI, INT, CON, CHA, LUK)
                # 平衡调整: (表型值+2) * 10
                # aa(2)->40(弱), Aa(4)->60(强), AA(6)->80(顶尖)
                "STR": (phenotype['STR'] + 2) * 10,
                "AGI": (phenotype['AGI'] + 2) * 10,
                "INT": (phenotype['INT'] + 2) * 10,
                "CHA": (phenotype['CHA'] + 2) * 10,
                "CON": (phenotype['CON'] + 2) * 10,
                "LUK": (phenotype['LUK'] + 2) * 10,
                
                # CoC 衍生属性
                # 初始 Sanity = POW
                "SAN": (phenotype['LUK'] + 2) * 10, 
                "MaxSAN": 99,
                "灵感": (phenotype['INT'] + 2) * 10, # Idea
                "幸运": (phenotype['LUK'] + 2) * 10, # Luck
                
                # 基础技能 (CoC标准: 50=职业水准)
                # 属性值现在是 40-80
                "技能_侦查": 25 + int((phenotype['INT'] + 2) * 5),  # 25 + 20~40 = 45~65
                "技能_聆听": 20 + int((phenotype['INT'] + 2) * 4),  # 20 + 16~32 = 36~52
                "技能_潜行": 20 + int((phenotype['AGI'] + 2) * 5),  # 20 + 20~40 = 40~60
                "技能_心理学": 5 + int((phenotype['CHA'] + 2) * 5), # 5 + 20~40 = 25~45
                "技能_克苏鲁神话": 0,
                
                # 衍生属性 (初始化为0，稍后计算)
                "HP": 0, "MaxHP": 0, 
                "MP": 0, "MaxMP": 0,
                "攻击": 0, "防御": 0,
                
                # 资源
                "金币": 0,
                "等级": 1, 
                "经验": 0, 
                "下一级经验": 100
            },
            
            "inventory": [],
            "equipment": {
                "weapon": None,
                "armor": None,
                "accessory": None
            },
            "skills": [],
            "achievements": [],
            "heirlooms": [], # 家族传家宝库
            
            # 家族树
            "family_tree": {
                "members": {
                    char_id: {
                        "name": self.profile.get('角色名称', 'Chi'),
                        "spouse": None,
                        "children_ids": [],
                        "genome": genome,
                        "birth_turn": 0,
                        "generation": 1
                    }
                },
                "head_id": char_id
            },
            "family_prestige": 0, # 家族声望
            
            # 关系系统
            "relationships": {},
            
            # 累计统计
            "lifetime_stats": {
                "总游戏时长": 0, "总回合数": 0, "总战斗次数": 0,
                "总击杀数": 0, "总探索次数": 0, "总休息次数": 0,
                "总NPC互动": 0, "总获得经验": 0, "总升级次数": 0,
                "总受伤次数": 0, "总死亡次数": 0, "游戏次数": 0,
                "总prompt_tokens": 0, "总completion_tokens": 0, "总total_tokens": 0
            },
            "event_history": []
        }
        
        # 绑定引用
        self.game_stats = self.save_data['base_stats']
        self.inventory = self.save_data['inventory']
        
        # 首次计算衍生属性
        self.recalculate_stats()
        # 这一步很重要：将HP/MP回满
        self.game_stats['HP'] = self.game_stats['MaxHP']
        self.game_stats['MP'] = self.game_stats['MaxMP']
        
        self.save()
    def recalculate_stats(self):
        """根据核心属性计算衍生属性 (STR, INT, etc -> HP, Atk)"""
        stats = self.game_stats
        level = stats.get('等级', 1)
        
        # 1. 核心属性 (默认为10，防止旧存档报错)
        STR = stats.get('STR', 10)
        AGI = stats.get('AGI', 10)
        INT = stats.get('INT', 10)
        CON = stats.get('CON', 10)
        CHA = stats.get('CHA', 10)
        LUK = stats.get('LUK', 10)
        
        # 2. 装备加成 (临时计算)
        equipment = self.save_data.get('equipment', {})
        bonus_stats = {'attack':0, 'defense':0}
        
        for slot, item in equipment.items():
            if item:
                stats_bonus = item.get('stats', {})
                bonus_stats['attack'] += stats_bonus.get('attack', 0)
                bonus_stats['defense'] += stats_bonus.get('defense', 0)
                # Future: equipment could also add STR/INT
        
        # 3. 衍生公式 (数值平衡优化 v2.0)
        # 设计原则：压缩初期面板，拉开成长空间，增强等级和装备的价值感
        
        # MaxHP: 体质*3 + 等级*15 + 基础50
        # CON=40(aa)Lv1 -> 170HP, CON=80(AA)Lv1 -> 305HP
        # CON=60Lv10 -> 380HP, CON=60Lv20 -> 530HP
        stats['MaxHP'] = int(CON * 3 + level * 15 + 50)
        
        # MaxMP: 智力*1.5 + 等级*8 + 基础20
        # INT=40Lv1 -> 88MP, INT=80Lv1 -> 148MP
        stats['MaxMP'] = int(INT * 1.5 + level * 8 + 20)
        
        # 攻击: 力量*0.4 + 敏捷*0.15 + 等级*1.5 + 装备
        # STR=50AGI=50Lv1 -> ~29攻击, Lv10 -> ~43攻击
        base_atk = int(STR * 0.4 + AGI * 0.15 + level * 1.5)
        stats['攻击'] = base_atk + bonus_stats['attack']
        
        # 防御: 体质*0.2 + 敏捷*0.1 + 等级*0.8 + 装备
        # CON=50AGI=50Lv1 -> ~16防御, Lv10 -> ~23防御
        base_def = int(CON * 0.2 + AGI * 0.1 + level * 0.8)
        stats['防御'] = base_def + bonus_stats['defense']
        
        # 确保当前HP/MP不超标
        if stats['HP'] > stats['MaxHP']: stats['HP'] = stats['MaxHP']
        if stats['MP'] > stats['MaxMP']: stats['MP'] = stats['MaxMP']


    def save(self):
        self.save_data['base_stats'] = self.game_stats
        self.save_data['inventory'] = self.inventory
        
        with open(self.save_path, 'w', encoding='utf-8') as f:
            json.dump(self.save_data, f, ensure_ascii=False, indent=4)
    
    def update_lifetime_stats(self, session_stats, duration_seconds):
        """更新累计统计"""
        if 'lifetime_stats' not in self.save_data:
            self.save_data['lifetime_stats'] = {
                "总游戏时长": 0, "总回合数": 0, "总战斗次数": 0,
                "总击杀数": 0, "总探索次数": 0, "总休息次数": 0,
                "总NPC互动": 0, "总获得经验": 0, "总升级次数": 0,
                "总受伤次数": 0, "总死亡次数": 0, "游戏次数": 0,
                "总prompt_tokens": 0, "总completion_tokens": 0, "总total_tokens": 0
            }
        
        lifetime = self.save_data['lifetime_stats']
        lifetime['总游戏时长'] += duration_seconds
        lifetime['总回合数'] += session_stats['回合数']
        lifetime['总战斗次数'] += session_stats['战斗次数']
        lifetime['总击杀数'] += session_stats['击杀数']
        lifetime['总探索次数'] += session_stats['探索次数']
        lifetime['总休息次数'] += session_stats['休息次数']
        lifetime['总NPC互动'] += session_stats['NPC互动']
        lifetime['总获得经验'] += session_stats['总经验']
        lifetime['总升级次数'] += session_stats['升级次数']
        lifetime['总受伤次数'] += session_stats['受伤次数']
        lifetime['总死亡次数'] += session_stats['死亡次数']
        lifetime['游戏次数'] += 1
        # Token累计
        lifetime['总prompt_tokens'] = lifetime.get('总prompt_tokens', 0) + session_stats.get('prompt_tokens', 0)
        lifetime['总completion_tokens'] = lifetime.get('总completion_tokens', 0) + session_stats.get('completion_tokens', 0)
        lifetime['总total_tokens'] = lifetime.get('总total_tokens', 0) + session_stats.get('total_tokens', 0)
        
        self.check_achievements()
        self.save()
    
    def check_achievements(self):
        """检查成就"""
        achievements = self.save_data.get('achievements', [])
        lifetime = self.save_data.get('lifetime_stats', {})
        age = self.save_data.get('age', 18)
        
        new_unlocks = []
        
        # 定义成就条件
        targets = [
            ("长寿者", age >= 60, "活到了60岁"),
            ("百人斩", lifetime.get('总击杀数', 0) >= 100, "击败了100个敌人"),
            ("探险家", lifetime.get('总探索次数', 0) >= 200, "进行了200次探索"),
            ("多子多福", len(self.get_children()) >= 5, "拥有5个子嗣"),
            ("传奇家族", self.save_data.get('family_tree', {}).get('members', {}).get(self.save_data.get('current_character_id'), {}).get('generation', 1) >= 5, "延续了5代人")
        ]
        
        for title, condition, desc in targets:
            if condition and title not in achievements:
                achievements.append(title)
                new_unlocks.append(f"{title} ({desc})")
        
        if new_unlocks:
            self.save_data['achievements'] = achievements
            print_success(f"\n🏆 解锁成就: {', '.join(new_unlocks)}! \n")

    def add_event_to_history(self, event_type, description, result):
        """添加事件到历史记录"""
        if 'event_history' not in self.save_data:
            self.save_data['event_history'] = []
        
        event = {
            "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "类型": event_type,
            "描述": description[:100],  # 限制长度
            "结果": result[:200] if result else ""
        }
        
        # 只保留最近100条
        self.save_data['event_history'].append(event)
        # 只保留最近100条
        self.save_data['event_history'].append(event)
        
        # 触发摘要阈值 (比如20条)
        if len(self.save_data['event_history']) > 20:
             # 在GameEngine里调用summarize，或者这里只标记需要summary
             pass

    def get_recent_history_text(self, limit=10):
        """获取最近的历史文本"""
        history = self.save_data.get('event_history', [])
        recent = history[-limit:]
        text = ""
        for h in recent:
            text += f"[{h['时间']}] {h['描述']} -> {h['结果']}\n"
        return text

    def compress_history(self, ai, summary, keep_count=10):
        """将旧历史压缩为摘要"""
        # 保存摘要
        if 'summary' not in self.save_data:
            self.save_data['summary'] = "角色刚刚开始冒险。"
        
        self.save_data['summary'] += f"\n[近期回忆] {summary}"
        
        # 清理旧历史，只保留最近keep_count条作为上下文
        if len(self.save_data['event_history']) > keep_count:
            self.save_data['event_history'] = self.save_data['event_history'][-keep_count:]
        
        self.save()
        print_success(f"📜 记忆已提炼: {summary}")
        # print_success("📜 记忆已从繁杂的细节中提炼为宝贵的经验。")

    @property
    def name(self): return self.profile['角色名称']
    @property
    def description(self): return self.profile['角色描述']
    @property
    def psychology(self): return json.dumps(self.profile['心理特征'], ensure_ascii=False)
    @property
    def language_style(self): return json.dumps(self.profile['语言特征'], ensure_ascii=False)
    
    @property
    def current_location(self): 
        # 防止 None
        loc = self.save_data.get('location')
        if not loc:
             return "ruins_city" # 默认 fallback
        return loc
    
    def update_location(self, loc_id):
        self.save_data['location'] = loc_id
        self.save()
    
    def check_survival(self, attacker_level=1):
        """濒死判定：基于等级差距和运气的存活率"""
        player_level = self.game_stats['等级']
        level_diff = player_level - attacker_level
        luk = self.game_stats.get('LUK', 10)
        
        # 1. 基础存活率
        base_rate = 0.2
        protected_msg = ""
        
        # 2. 新手保护期 (5级以下)
        if player_level <= 5:
            base_rate = 0.8
            protected_msg = " [新手保护生效]"
        
        # 3. 等级压制修正 (每级差5%)
        level_mod = level_diff * 0.05
        
        # 4. 幸运加成 (每点幸运+1%)
        luck_mod = (luk - 10) * 0.01
        
        # 计算最终概率
        final_rate = max(0.05, min(0.95, base_rate + level_mod + luck_mod))
        
        # 判定
        roll = random.random()
        survived = roll < final_rate
        
        # 详细日志 (方便用户理解死因)
        if survived:
            print_warning(f"🍀 奇迹生还！(概率: {final_rate*100:.0f}% - LUK:{luk}{protected_msg})")
            # 恢复少量生命
            self.game_stats['HP'] = max(1, int(self.game_stats['MaxHP'] * 0.1))
        else:
            # 即使判定失败，如果是幸运儿，还有一次骰子豁免机会
            if luk >= 15 and random.random() < 0.2:
                 print_warning(f"🎲 命运女神的垂青！(强制豁免)")
                 self.game_stats['HP'] = 1
                 survived = True
            else:
                 print_warning(f"💀 逃生失败 (概率: {final_rate*100:.0f}% - 运势不足)")
                 
        return survived
    
    def die(self, death_cause, total_turns):
        """处理角色死亡"""
        self.save_data['is_alive'] = False
        char_id = self.save_data.get('current_character_id')
        
        if char_id and 'family_tree' in self.save_data:
            member = self.save_data['family_tree']['members'].get(char_id)
            if member:
                member['death_turn'] = total_turns
                member['death_cause'] = death_cause
                member['final_stats'] = dict(self.game_stats)
        
        self.save()
    
    def get_children(self):
        """获取当前角色的子女列表"""
        char_id = self.save_data.get('current_character_id')
        if not char_id or 'family_tree' not in self.save_data:
            return []
        
        member = self.save_data['family_tree']['members'].get(char_id)
        if not member:
            return []
        
        children = []
        for child_id in member.get('children_ids', []):
            child = self.save_data['family_tree']['members'].get(child_id)
            if child:
                children.append((child_id, child))
        return children
    
    def get_eldest_child(self):
        """获取最大的孩子（按出生回合排序）"""
        children = self.get_children()
        if not children:
            return None, None
        # 按出生回合排序，取最早的
        children.sort(key=lambda x: x[1].get('birth_turn', 0))
        return children[0]
    
    def switch_to_heir(self, heir_id):
        """切换视角到继承人 (深度家族系统)"""
        if heir_id not in self.save_data['family_tree']['members']:
            return False
        
        # 1. 结算本代家族声望
        stats = self.game_stats
        life_stats = self.save_data.get('lifetime_stats', {})
        
        # 声望公式：等级*10 + 资产/100 + 击杀数 + 成就数*50
        prestige_gain = (stats['等级'] * 10) + (stats['金币'] // 100) + \
                        life_stats.get('总击杀数', 0) + (len(self.save_data.get('achievements', [])) * 50)
        
        current_prestige = self.save_data.get('family_prestige', 0)
        total_prestige = current_prestige + prestige_gain
        self.save_data['family_prestige'] = total_prestige
        
        print_success(f"🏛️ 家族声望结算: 本代贡献 +{prestige_gain} (总声望: {total_prestige})")

        # 2. 打造传家宝
        equipment = self.save_data.get('equipment', {})
        inventory = self.inventory
        
        # 寻找最好的武器或防具进行注灵
        best_gear = None
        best_score = -1
        
        # 检查已装备
        for slot, item in equipment.items():
            if not item: continue
            score = item.get('stats', {}).get('attack', 0) + item.get('stats', {}).get('defense', 0)
            if score > best_score:
                best_score = score
                best_gear = item
        
        # 如果没装备，检查背包
        if not best_gear:
            for item in inventory:
                if item.get('type') in ['武器', '防具']:
                    score = item.get('stats', {}).get('attack', 0) + item.get('stats', {}).get('defense', 0)
                    if score > best_score:
                        best_score = score
                        best_gear = item
        
        heirloom_msg = ""
        if best_gear:
            # 强化传家宝
            # 每代增强 10% 或至少 +2 攻防
            enhancement = 0.1
            stats = best_gear.get('stats', {})
            for k in stats:
                boost = max(1, int(stats[k] * enhancement))
                stats[k] += boost
            
            # 重命名 (如果不包含家族前缀)
            if "传家宝" not in best_gear['name']:
                best_gear['name'] = f"传家宝·{best_gear['name']}"
                best_gear['desc'] = f"家族代代相传的宝物，积蓄了先祖的力量。\n{best_gear.get('desc', '')}"
            else:
                # 已经是传家宝，增加世代标记
                if "+" not in best_gear['name']:
                    best_gear['name'] += " +1"
                else:
                    # 解析并增加代数 (简化处理，直接加后缀)
                    best_gear['name'] += "+"

            heirloom_msg = f"⚔️ 传家宝 [{best_gear['name']}] 已强化并传承！"
            
            # 确保传家宝在背包里
            if best_gear not in inventory:
                inventory.append(best_gear)

        stats = self.game_stats # 旧stats引用
        
        # 3. 切换身份
        heir = self.save_data['family_tree']['members'][heir_id]
        self.save_data['current_character_id'] = heir_id
        self.save_data['is_alive'] = True
        
        # 获取继承人的基因组
        child_genome = heir.get('genome', GeneticSystem.generate_random_genome())
        gene_score = heir.get('gene_score', GeneticSystem.calculate_gene_score(child_genome))
        
        # 4. 基于基因 + 家族声望 初始化核心属性
        # 必须初始化 STR/AGI 等，否则 recalculate_stats 会回退到默认值 10
        phenotype = GeneticSystem.express_phenotype(child_genome)
        
        # 声望加成：每100声望 +1 全属性 (大幅增强家族传承感)
        prestige_bonus = total_prestige // 100
        
        # 继承资产
        inherited_gold = stats.get('金币', 0)
        inherited_inventory = inventory[:]
        inherited_equipment = self.save_data.get('equipment', {}).copy()
        
        # 构建新的 base_stats (完全重置状态)
        self.save_data['base_stats'] = {
            "STR": (phenotype['STR'] + 2) * 10 + prestige_bonus,
            "AGI": (phenotype['AGI'] + 2) * 10 + prestige_bonus,
            "INT": (phenotype['INT'] + 2) * 10 + prestige_bonus,
            "CON": (phenotype['CON'] + 2) * 10 + prestige_bonus,
            "CHA": (phenotype['CHA'] + 2) * 10 + prestige_bonus,
            "LUK": (phenotype['LUK'] + 2) * 10 + prestige_bonus,
            
            "SAN": (phenotype['LUK'] + 2) * 10,
            "MaxSAN": 99,
            "灵感": (phenotype['INT'] + 2) * 10,
            "幸运": (phenotype['LUK'] + 2) * 10,
            
            # CoC 基础技能继承 (稍微给点加成代表家学渊源?)
            "技能_侦查": 25 + int((phenotype['INT'] + 2) * 5) + prestige_bonus,
            "技能_聆听": 20 + int((phenotype['INT'] + 2) * 4) + prestige_bonus,
            "技能_潜行": 20 + int((phenotype['AGI'] + 2) * 5) + prestige_bonus,
            "技能_心理学": 5 + int((phenotype['CHA'] + 2) * 5) + prestige_bonus,
            "技能_克苏鲁神话": 0,
            
            # 衍生属性 (由 recalculate_stats 计算)
            "HP": 0, "MaxHP": 0, "MP": 0, "MaxMP": 0,
            "攻击": 0, "防御": 0,
            
            "等级": 1, "经验": 0, "下一级经验": 100,
            "金币": inherited_gold
        }
        
        # 应用
        self.game_stats = self.save_data['base_stats']
        self.inventory = inherited_inventory
        self.save_data['inventory'] = self.inventory
        self.save_data['equipment'] = inherited_equipment
        
        # 重新计算面板
        self.recalculate_stats()
        # 回满状态
        self.game_stats['HP'] = self.game_stats['MaxHP']
        self.game_stats['MP'] = self.game_stats['MaxMP']
        
        # 保存基因组
        self.save_data['player_genome'] = child_genome
        self.save_data['player_gene_score'] = gene_score
        
        print_success(f"👑 家族传承完成！第 {heir.get('generation', 2)} 代继承人 {heir.get('name')} 继承了家业。")
        
        # 家族秘术/技能继承
        # 简单处理：保留一部分技能
        old_skills = self.save_data.get('custom_skills', [])
        if old_skills:
            # 随机丢失 20% 技能，或者保留全部
            self.save_data['custom_skills'] = old_skills # 完整传承
            print_info(f"📚 继承了 {len(old_skills)} 个家族秘术。")
            
        if heirloom_msg:
            print_info(heirloom_msg)
        print_success(f"🌟 家族底蕴加成: 全属性+{prestige_bonus}")
        
        # 更新profile信息
        self.profile['角色名称'] = heir.get('name', '继承者')
        self.profile['心理特征'] = heir.get('personality', {})
        self.profile['语言特征'] = heir.get('language_style', {})
        
        self.save()
        return True

    def heal(self, hp=0, mp=0, san=0):
        self.game_stats['HP'] = min(self.game_stats['MaxHP'], self.game_stats['HP'] + hp)
        self.game_stats['MP'] = min(self.game_stats['MaxMP'], self.game_stats['MP'] + mp)
        if san > 0:
            max_san = self.game_stats.get('MaxSAN', 99)
            self.game_stats['SAN'] = min(max_san, self.game_stats.get('SAN', 0) + san)

    def take_damage(self, dmg):
        self.game_stats['HP'] = max(0, self.game_stats['HP'] - dmg)

    def gain_exp(self, amount):
        print_success(f"✨ 获得经验: {amount}")
        self.game_stats['经验'] += amount
        # 循环升级，支持一次过多级
        while self.game_stats['经验'] >= self.game_stats['下一级经验']:
            self.level_up()

    def get_next_level_exp(self, level):
        # 宝可梦风格的中速曲线：1.2 * N^3
        # Lv1 -> Lv2: ~10 exp
        # Lv10 -> Lv11: ~1300 exp
        # Lv50 -> Lv51: ~150,000 exp
        return int(1.2 * (level + 1) ** 3)

    def level_up(self):
        old_level = self.game_stats['等级']
        self.game_stats['等级'] += 1
        self.game_stats['经验'] -= self.game_stats['下一级经验']
        
        # 更新下一级所需经验
        self.game_stats['下一级经验'] = self.get_next_level_exp(self.game_stats['等级'])
        
        # 获取基因表型（用于计算成长率）
        genome = self.save_data.get('player_genome', {})
        phenotype = GeneticSystem.express_phenotype(genome)
        
        # 核心属性成长公式 v2.0：大幅增强升级收益感
        # 基础成长 = 表型分(2-6) * 0.3 + 随机(0.3-1.2)
        # aa(2): 0.9~1.8/级, Aa(4): 1.5~2.4/级, AA(6): 2.1~3.0/级
        growth = {}
        for stat in ['STR', 'AGI', 'INT', 'CON', 'CHA', 'LUK']:
            base_growth = phenotype.get(stat, 2) * 0.3
            rand_growth = random.uniform(0.3, 1.2)
            total_gain = base_growth + rand_growth
            
            # 累加到属性上
            old_val = self.game_stats.get(stat, 10)
            self.game_stats[stat] = old_val + total_gain
            growth[stat] = total_gain
        
        # 记录旧的衍生属性以便对比
        old_hp = self.game_stats.get('MaxHP', 100)
        old_atk = self.game_stats.get('攻击', 10)
        
        # 重新计算衍生属性 (HP, Atk...)
        self.recalculate_stats()
        
        # 升级回满
        self.game_stats['HP'] = self.game_stats['MaxHP']
        self.game_stats['MP'] = self.game_stats['MaxMP']
        
        # 计算衍生属性的变化量
        hp_gain = self.game_stats['MaxHP'] - old_hp
        atk_gain = self.game_stats['攻击'] - old_atk
        
        # self.session_stats['升级次数'] += 1 # 移除了，Character无法访问session_stats
        print_success(f"🆙 升级了! (Lv.{old_level} -> Lv.{self.game_stats['等级']})")
        
        # 格式化成长日志
        growth_msg = []
        for s, g in growth.items():
            if g > 0.4: growth_msg.append(f"[bold green]{s}+{g:.1f}[/bold green]")
            else: growth_msg.append(f"{s}+{g:.1f}")
            
        print_info(f"   核心成长: {' | '.join(growth_msg)}")
        print_info(f"   面板提升: MaxHP+{hp_gain}, 攻击+{atk_gain}")
        
        # 增加寿命
        race = self.save_data.get('race', '人类')
        races = self.save_data.get('custom_races', RaceSystem.RACES)
        race_data = races.get(race, races.get('人类'))
        bonus = race_data.get('level_bonus', 2)
        
        self.save_data['max_age'] = int(self.save_data.get('max_age', 80) + bonus)
        
        print_info(f"\n[bold yellow]★ 升级了！当前等级: {self.game_stats['等级']} (寿命上限+{bonus}) ★[/bold yellow]\n")

    def update_age(self, turn_count):
        """更新年龄和检查状态"""
        # 每50回合一岁
        birth_turn = self.save_data['family_tree']['members'][self.save_data['current_character_id']].get('birth_turn', 0)
        current_age = 18 + (turn_count - birth_turn) // RaceSystem.TURNS_PER_YEAR
        
        if current_age > self.save_data.get('age', 18):
            # 生日/过年
            self.save_data['age'] = current_age
            print_info(f"🎂 又长大了一岁！当前年龄: {current_age}")
            
            # 检查自然死亡
            max_age = self.save_data.get('max_age', 80)
            if current_age >= max_age:
                # 寿命耗尽，每回合都有概率死亡 (降低概率，避免瞬间暴毙)
                death_chance = (current_age - max_age) * 0.05 + 0.01
                if random.random() < death_chance:
                    return "old_age"
            
            # 检查衰老惩罚
            self.apply_aging_effects()
            
        return None

    def apply_aging_effects(self):
        """应用衰老带来的属性衰减"""
        race = self.save_data.get('race', '人类')
        age = self.save_data.get('age', 18)
        max_age = self.save_data.get('max_age', 80)
        custom_races = self.save_data.get('custom_races')
        
        new_penalty = RaceSystem.check_aging_debuff(race, age, max_age, custom_races)
        current_penalty = self.save_data.get('aging_penalty', 0.0)
        
        # 如果惩罚加深
        if new_penalty > current_penalty + 0.001:
            diff = new_penalty - current_penalty
            self.save_data['aging_penalty'] = new_penalty
            
            # 扣除属性
            stats = ['攻击', '防御', 'MaxHP', 'MaxMP']
            reduced = []
            for s in stats:
                loss = int(self.game_stats[s] * diff)
                if loss > 0:
                    self.game_stats[s] -= loss
                    reduced.append(f"{s}-{loss}")
            
            if reduced:
                print_warning(f"👴 岁月流逝，身体机能下降: {', '.join(reduced)}")
                # 确保HP不超过MaxHP
                self.game_stats['HP'] = min(self.game_stats['HP'], self.game_stats['MaxHP'])

    def get_traits(self):
        """获取当前激活的基因特质 (包含基因 + AI性格解析)"""
        # 1. 基因特质
        genome = self.save_data.get('player_genome', {})
        custom_traits = self.save_data.get('custom_traits')
        traits = GeneticSystem.get_traits(genome, custom_traits)
        
        # 1.5 后天特质 (Events)
        acquired = self.save_data.get('acquired_traits', [])
        for t in acquired:
            if t not in traits:
                traits.append(t)
        
        # 2. AI性格解析 (兼容 AI 生成的设定)
        # 如果心理特征里包含特质关键词，也算作拥有该特质
        psychology = self.profile.get('心理特征', '')
        if isinstance(psychology, dict):
            psychology = str(psychology)
            
        # 关键词映射
        keywords = ["好色", "忠诚", "热情", "保守", "禁欲", "多疑", "宽容", "嫉妒", "魅魔"]
        for kw in keywords:
            if kw in psychology and kw not in traits:
                # 特殊映射
                trait_name = kw
                if kw == "魅魔": trait_name = "魅魔体质"
                traits.append(trait_name)
                
        return traits
    
    def _parse_trait_bonus(self, trait_name, keyword):
        """解析特质加成数值 (结构化读取)"""
        custom_traits = self.save_data.get('custom_traits', GeneticSystem.TRAITS)
        t_data = custom_traits.get(trait_name)
        if not t_data: return 0
        
        # 新逻辑：直接读取 modifiers 字典
        modifiers = t_data.get('modifiers', {})
        if keyword in modifiers:
            return modifiers[keyword]
            
        # 兼容旧逻辑 (regex)
        effect = t_data.get('effect', '')
        if keyword in effect:
            try:
                import re
                match = re.search(rf'{keyword}.*?([+-]?\d+)', effect)
                if match:
                    return int(match.group(1))
            except: pass
        return 0

    def get_attack(self):
        atk = self.game_stats['攻击']
        # 基因加成
        for t in self.get_traits():
            atk += self._parse_trait_bonus(t, "攻击")
        # 装备加成
        equip = self.save_data.get('equipment', {})
        if equip.get('weapon'):
            atk += self._parse_item_bonus(equip['weapon'], 'attack') # 假设解析函数
        if equip.get('accessory'):
            atk += self._parse_item_bonus(equip['accessory'], 'attack')
        return atk

    def get_defense(self):
        defn = self.game_stats['防御']
        for t in self.get_traits():
            defn += self._parse_trait_bonus(t, "防御")
        # 装备加成
        equip = self.save_data.get('equipment', {})
        if equip.get('armor'):
            defn += self._parse_item_bonus(equip['armor'], 'defense')
        if equip.get('accessory'):
            defn += self._parse_item_bonus(equip['accessory'], 'defense')
        return defn
    
    def _parse_item_bonus(self, item, stat_type):
        """解析物品属性加成"""
        # 优先使用结构化的 stats
        stats = item.get('stats', {})
        if stats:
            if stat_type == 'attack': return stats.get('attack', 0)
            if stat_type == 'defense': return stats.get('defense', 0)
        
        # 兼容旧版本：尝试解析 effect 字符串
        effect = item.get('effect', '')
        import re
        if stat_type == 'attack' and '攻击' in effect:
            m = re.search(r'攻击\+(\d+)', effect)
            if m: return int(m.group(1))
        if stat_type == 'defense' and '防御' in effect:
            m = re.search(r'防御\+(\d+)', effect)
            if m: return int(m.group(1))
        return 0

    def equip_item(self, item):
        """装备物品"""
        type_ = item.get('type') # 武器/防具/饰品
        slot_map = {"武器": "weapon", "防具": "armor", "饰品": "accessory"}
        slot = slot_map.get(type_)
        
        if not slot: return False
        
        # 卸下当前
        current = self.save_data.get('equipment', {}).get(slot)
        if current:
            self.inventory.append(current)
            
        # 装备新
        if 'equipment' not in self.save_data: self.save_data['equipment'] = {}
        self.save_data['equipment'][slot] = item
        
        # 从背包移除 (需要比较引用或ID，这里简单假设item对象就是背包里的)
        if item in self.inventory:
            self.inventory.remove(item)
            
        return True

    def get_dodge_bonus(self):
        bonus = 0
        for t in self.get_traits():
            val = self._parse_trait_bonus(t, "闪避")
            bonus += val / 100.0 # 假设特质写的是 +5% -> 5
        return bonus
    
    def get_crit_bonus(self):
        bonus = 0
        for t in self.get_traits():
            val = self._parse_trait_bonus(t, "暴击")
            bonus += val / 100.0
        return bonus
