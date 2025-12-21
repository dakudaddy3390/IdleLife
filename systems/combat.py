import random
import json
from core.utils import print_info, print_success, print_warning, print_error

class Skill:
    def __init__(self, name, type_, cost, power, desc, effect=None):
        self.name = name
        self.type = type_ # 'physical', 'magic', 'heal', 'buff'
        self.cost = cost # MP cost
        self.power = power # Modifier for damage/heal
        self.desc = desc
        self.effect = effect # Special effect function

class CombatSystem:
    """
    战斗系统 2.0
    - 技能系统：基于基因和属性解锁
    - 回合制策略：AI或自动选择最佳技能
    """
    
    SKILLS = {
        "重击": Skill("重击", "physical", 5, 1.5, "用力挥舞武器，造成1.5倍伤害"),
        "二连击": Skill("二连击", "physical", 10, 0.9, "快速攻击两次", effect="multi_hit_2"),
        "火球术": Skill("火球术", "magic", 15, 2.0, "发射火球，造成大量魔法伤害"),
        "治疗术": Skill("治疗术", "heal", 20, 3.0, "恢复大量生命值"),
        "吸血": Skill("吸血", "magic", 15, 1.0, "造成伤害并恢复等量生命", effect="drain"),
        "弱点看破": Skill("弱点看破", "buff", 10, 0, "下一次攻击必定暴击", effect="crit_buff"),
    }

    @staticmethod
    def get_skill(name):
        """安全获取技能，如果不存在则返回基础攻击"""
        skill = CombatSystem.SKILLS.get(name)
        if not skill:
            return Skill(name, "physical", 0, 1.0, "普通的一击")
        return skill
    
    @staticmethod
    def get_available_skills(character):
        """根据角色基因和属性解锁技能"""
        # 兼容怪物字典
        if isinstance(character, dict):
             return [CombatSystem.get_skill(name) for name in character.get('skills', [])]
             
        skills = []
        stats = character.game_stats
        traits = character.get_traits()
        
        # 基础技能
        skills.append(CombatSystem.SKILLS["重击"])
        
        # 属性解锁
        # 属性解锁 (新数值体系: 40=弱, 60=强, 80=顶尖)
        if stats.get('INT', 0) >= 60 or stats.get('MaxMP', 0) >= 200:
            skills.append(CombatSystem.SKILLS["火球术"])
        if stats.get('AGI', 0) >= 65:
            skills.append(CombatSystem.SKILLS["二连击"])
        if stats.get('INT', 0) >= 50 and stats.get('CHA', 0) >= 50:
            skills.append(CombatSystem.SKILLS["治疗术"])
            
        # 基因/特质解锁
        if "天生神力" in traits: # STR
             # 强化版重击? 暂时用普通技能代替
             pass
        if "吸血鬼" in traits: # 假设有这个Trait
            skills.append(CombatSystem.SKILLS["吸血"])
        if "风之子" in traits:
            skills.append(CombatSystem.SKILLS["二连击"])
            
        # 加载 AI 领悟的自定义技能
        custom_data = character.save_data.get('custom_skills', [])
        for s_data in custom_data:
            # 动态重建 Skill 对象
            new_skill = Skill(
                s_data.get('name', '未知技能'),
                s_data.get('type', 'physical'),
                s_data.get('cost', 10),
                s_data.get('power', 1.0),
                s_data.get('desc', '...'),
                s_data.get('effect')
            )
            skills.append(new_skill)
            
        return skills

    @staticmethod
    def ai_learn_skill(character, ai):
        """AI 领悟新技能"""
        p = character
        stats = p.game_stats
        
        # 找出最高属性
        best_stat = max(stats, key=lambda k: stats[k] if isinstance(stats[k], int) else 0)
        
        prompt = f"""角色: {p.name} (种族:{p.save_data.get('race')})
特质: {','.join(p.get_traits())}
最高属性: {best_stat} ({stats.get(best_stat)})
已会技能: {[s.name for s in CombatSystem.get_available_skills(p)]}

请根据角色特点，创造一个全新的战斗技能。
要求：
1. 技能名要帅气/中二。
2. 类型从 [physical, magic, heal, buff] 中选。
3. 消耗(cost) 10-100 MP。
4. 威力(power) 1.5-4.0 (倍率)。
5. 特效(effect) 可选 [multi_hit_2, drain, crit_buff] 或 null。

直接输出JSON：
{{
  "name": "技能名",
  "type": "类型",
  "cost": 30,
  "power": 2.5,
  "desc": "技能描述",
  "effect": null
}}"""
        try:
            content, usage = ai.think_and_act(prompt)
            if content:
                import re
                match = re.search(r'\{.*\}', content.replace('\n', ' '), re.DOTALL)
                if match:
                    skill_data = json.loads(match.group())
                    
                    # 验证必要字段
                    if 'name' in skill_data:
                        # 保存
                        if 'custom_skills' not in p.save_data:
                             p.save_data['custom_skills'] = []
                        p.save_data['custom_skills'].append(skill_data)
                        p.save()
                        print_success(f"💡 [顿悟] {p.name} 领悟了新技能: [bold cyan]{skill_data['name']}[/bold cyan]!")
                        print_info(f"   {skill_data['desc']} (威力: {skill_data.get('power')})")
                        return True
        except Exception as e:
            print_error(f"领悟技能失败: {e}")
        return False

    @staticmethod
    def ai_teach_skill(character, teacher_name, relation, ai):
        """NPC (伴侣/导师) 传授技能"""
        p = character
        
        prompt = f"""角色: {p.name}
导师: {teacher_name} (关系: {relation})
已会技能: {[s.name for s in CombatSystem.get_available_skills(p)]}

请设计一个由 {teacher_name} 传授给 {p.name} 的特殊技能。
要求：
1. 技能名要体现导师的风格（如伴侣传授的守护/爱意，导师传授的秘术）。
2. 类型从 [physical, magic, heal, buff] 中选。
3. 消耗(cost) 10-80 MP。
4. 威力(power) 2.0-3.5 (倍率)。
5. 特效(effect) 可选 [multi_hit_2, drain, crit_buff] 或 null。
6. 描述要写出传授时的情景（如“手把手教导”、“深情地传授”）。

直接输出JSON：
{{
  "name": "技能名",
  "type": "类型",
  "cost": 30,
  "power": 2.5,
  "desc": "技能描述(含传授情景)",
  "effect": null
}}"""
        try:
            content, usage = ai.think_and_act(prompt)
            if content:
                import re
                match = re.search(r'\{.*\}', content.replace('\n', ' '), re.DOTALL)
                if match:
                    skill_data = json.loads(match.group())
                    
                    if 'name' in skill_data:
                        if 'custom_skills' not in p.save_data:
                             p.save_data['custom_skills'] = []
                        p.save_data['custom_skills'].append(skill_data)
                        p.save()
                        print_success(f"🎓 [传授] {teacher_name} 教会了你新技能: [bold cyan]{skill_data['name']}[/bold cyan]!")
                        print_info(f"   {skill_data['desc']}")
                        return True
        except Exception as e:
            print_error(f"传授技能失败: {e}")
        return False

    @staticmethod
    def choose_skill(attacker, defender, skills):
        """智能战斗决策 AI"""
        stats = attacker if isinstance(attacker, dict) else attacker.game_stats
        target_stats = defender if isinstance(defender, dict) else defender.game_stats
        
        current_mp = stats.get('MP', 0)
        
        # 0. 整理可用技能
        attack_skills = [s for s in skills if s.type in ['physical', 'magic']]
        heal_skills = [s for s in skills if s.type == 'heal']
        
        # 1. 斩杀判定 (Kill Shot) - 优先级最高
        # 如果能直接打死对面，就别加血了
        kill_options = []
        target_hp = target_stats.get('HP', 0)
        
        for s in attack_skills:
            if current_mp >= s.cost:
                # 预估伤害 (取一次随机结果作为预判，模拟直觉)
                dmg, _, _ = CombatSystem.calculate_damage(attacker, defender, s)
                if dmg >= target_hp:
                    kill_options.append(s)
        
        if kill_options:
            # 选择消耗最低的斩杀技能
            kill_options.sort(key=lambda x: x.cost)
            return kill_options[0]

        # 2. 紧急治疗判定 (Survival)
        if stats.get('HP', 0) < stats.get('MaxHP', 100) * 0.3:
            # 找效果最好的治疗
            best_heal = None
            max_power = -1
            for s in heal_skills:
                if current_mp >= s.cost:
                    if s.power > max_power:
                        max_power = s.power
                        best_heal = s
            
            if best_heal:
                return best_heal
        
        # 3. 常规输出 (Normal)
        # 随机选择一个蓝够的技能，或者普攻
        valid_skills = [s for s in skills if current_mp >= s.cost]
        if not valid_skills:
            return None # 普通攻击
        
        # 稍微倾向于使用强力技能 (Power高的权重更大?) 
        # 暂时保持随机，避免过于单调
        return random.choice(valid_skills)

    @staticmethod
    def calculate_damage(attacker, defender, skill=None):
        """计算伤害"""
        stats = attacker if isinstance(attacker, dict) else attacker.game_stats
        target_stats = defender if isinstance(defender, dict) else defender.game_stats
        
        # 基础属性
        # 兼容 attacker.get_attack()
        if hasattr(attacker, 'get_attack'):
             atk = attacker.get_attack()
        else:
             atk = stats.get('攻击', 0)
             
        if hasattr(defender, 'get_defense'):
             defn = defender.get_defense()
        else:
             defn = target_stats.get('防御', 0)
        
        # 技能修正
        multiplier = 1.0
        bonus_dmg = 0
        
        is_magic = False
        if skill:
            multiplier = skill.power
            if skill.type == 'magic':
                is_magic = True
                # 魔法伤害受智力加成
                int_stat = stats.get('INT', 10) 
                # 平衡调整: INT*0.5 + 等级*2 (避免前期伤害过高)
                magic_atk = int_stat * 0.5 + stats.get('等级', 1) * 2
                atk = magic_atk
                # 魔法无视部分防御
                defn = defn // 2
        
        base_dmg = max(1, atk - defn)
        final_dmg = int(base_dmg * multiplier + bonus_dmg)
        
        # 浮动
        variation = random.randint(-int(final_dmg*0.1), int(final_dmg*0.1))
        final_dmg = max(1, final_dmg + variation)
        
        # 暴击
        crit_rate = 0.05
        if hasattr(attacker, 'get_crit_bonus'):
            crit_rate += attacker.get_crit_bonus()
            
        if skill and skill.effect == 'crit_buff':
            crit_rate += 1.0
            
        is_crit = random.random() < crit_rate
        if is_crit:
            final_dmg = int(final_dmg * 1.5)
            
        return final_dmg, is_crit, is_magic

    @staticmethod
    def execute_turn(attacker, defender, console):
        """执行一个回合"""
        stats = attacker if isinstance(attacker, dict) else attacker.game_stats
        name = attacker.get('名称', '怪物') if isinstance(attacker, dict) else attacker.name
        
        skills = CombatSystem.get_available_skills(attacker)
        skill = CombatSystem.choose_skill(attacker, defender, skills)
        
        # 扣除MP
        if skill:
            stats['MP'] = stats.get('MP', 0) - skill.cost
            print_info(f"✨ {name} 使用了 [bold cyan]{skill.name}[/bold cyan]!")
            
            if skill.type == 'heal':
                heal_amt = int(skill.power * 10) # 简化：系数*10
                
                if hasattr(attacker, 'heal'):
                    attacker.heal(hp=heal_amt)
                else:
                    stats['HP'] = min(stats.get('MaxHP', 100), stats.get('HP', 0) + heal_amt)
                    
                print_success(f"💚 恢复了 {heal_amt} 点生命")
                return 0, False # 无伤害
                
        # 计算伤害
        dmg, is_crit, is_magic = CombatSystem.calculate_damage(attacker, defender, skill)
        
        # 特殊效果处理
        if skill and skill.effect == 'multi_hit_2':
            dmg2, _, _ = CombatSystem.calculate_damage(attacker, defender, skill)
            dmg += dmg2
            print_info(f"💨 连续攻击!")
            
        if skill and skill.effect == 'drain':
            drain = int(dmg * 0.5)
            if hasattr(attacker, 'heal'):
                attacker.heal(hp=drain)
            else:
                stats['HP'] = min(stats.get('MaxHP', 100), stats.get('HP', 0) + drain)
            print_success(f"🩸 吸取了 {drain} 点生命")
            
        return dmg, is_crit
