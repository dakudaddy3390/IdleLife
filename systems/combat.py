import random
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
    def get_available_skills(character):
        """根据角色基因和属性解锁技能"""
        skills = []
        stats = character.game_stats
        traits = character.get_traits()
        
        # 基础技能
        skills.append(CombatSystem.SKILLS["重击"])
        
        # 属性解锁
        if stats['智力'] >= 15 or stats['MaxMP'] >= 60:
            skills.append(CombatSystem.SKILLS["火球术"])
        if stats['敏捷'] >= 15:
            skills.append(CombatSystem.SKILLS["二连击"])
        if stats['智力'] >= 10 and stats['魅力'] >= 10:
            skills.append(CombatSystem.SKILLS["治疗术"])
            
        # 基因/特质解锁
        if "天生神力" in traits: # STR
             # 强化版重击? 暂时用普通技能代替
             pass
        if "吸血鬼" in traits: # 假设有这个Trait
            skills.append(CombatSystem.SKILLS["吸血"])
        if "风之子" in traits:
            skills.append(CombatSystem.SKILLS["二连击"])
            
        return skills

    @staticmethod
    def choose_skill(attacker, defender, skills):
        """简单的AI决策技能"""
        # 优先治疗
        if attacker.game_stats['HP'] < attacker.game_stats['MaxHP'] * 0.3:
            heal = CombatSystem.SKILLS.get("治疗术")
            if heal and heal in skills and attacker.game_stats['MP'] >= heal.cost:
                return heal
        
        # 魔法够就用强力技能
        valid_skills = [s for s in skills if attacker.game_stats['MP'] >= s.cost]
        if not valid_skills:
            return None # 普通攻击
        
        # 随机选择一个能用的
        return random.choice(valid_skills)

    @staticmethod
    def calculate_damage(attacker, defender, skill=None):
        """计算伤害"""
        stats = attacker.game_stats
        target_stats = defender if isinstance(defender, dict) else defender.game_stats
        
        # 基础属性
        atk = attacker.get_attack()
        defn = defender.get('防御', 0) if isinstance(defender, dict) else defender.get_defense()
        
        # 技能修正
        multiplier = 1.0
        bonus_dmg = 0
        
        is_magic = False
        if skill:
            multiplier = skill.power
            if skill.type == 'magic':
                is_magic = True
                # 魔法伤害受智力加成
                int_stat = stats.get('智力', 10) # 假设默认10
                # 需要在Character里把INT也放到game_stats? 或者每次从express_genotype算?
                # 简化：用 MaxMP // 5 近似智力
                magic_atk = int_stat * 2
                atk = magic_atk
                # 魔法无视部分防御
                defn = defn // 2
        
        base_dmg = max(1, atk - defn)
        final_dmg = int(base_dmg * multiplier + bonus_dmg)
        
        # 浮动
        variation = random.randint(-int(final_dmg*0.1), int(final_dmg*0.1))
        final_dmg = max(1, final_dmg + variation)
        
        # 暴击
        crit_rate = attacker.get_crit_bonus()
        if skill and skill.effect == 'crit_buff':
            crit_rate += 1.0
            
        is_crit = random.random() < (0.05 + crit_rate)
        if is_crit:
            final_dmg = int(final_dmg * 1.5)
            
        return final_dmg, is_crit, is_magic

    @staticmethod
    def execute_turn(attacker, defender, console):
        """执行一个回合"""
        skills = CombatSystem.get_available_skills(attacker)
        skill = CombatSystem.choose_skill(attacker, defender, skills)
        
        # 扣除MP
        if skill:
            attacker.game_stats['MP'] -= skill.cost
            print_info(f"✨ {attacker.name} 使用了 [bold cyan]{skill.name}[/bold cyan]!")
            
            if skill.type == 'heal':
                heal_amt = int(skill.power * 10) # 简化：系数*10
                attacker.heal(hp=heal_amt)
                print_success(f"💚 恢复了 {heal_amt} 点生命")
                return 0 # 无伤害
                
        # 计算伤害
        dmg, is_crit, is_magic = CombatSystem.calculate_damage(attacker, defender, skill)
        
        # 特殊效果处理
        if skill and skill.effect == 'multi_hit_2':
            dmg2, _, _ = CombatSystem.calculate_damage(attacker, defender, skill)
            dmg += dmg2
            print_info(f"💨 连续攻击!")
            
        if skill and skill.effect == 'drain':
            drain = int(dmg * 0.5)
            attacker.heal(hp=drain)
            print_success(f"🩸 吸取了 {drain} 点生命")
            
        return dmg, is_crit
