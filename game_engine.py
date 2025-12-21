import time
import random
import sys
import json
import msvcrt
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel

from core.config import Config
from core.ai import AIBrain
from core.utils import console, print_header, print_info, print_success, print_warning, print_error, print_event, print_character, format_loot
from models.world import GameWorld
from models.character import Character
from systems.race import RaceSystem
from systems.genetics import GeneticSystem
from systems.merchant import MerchantSystem
from systems.combat import CombatSystem, Skill
from systems.events import DynamicEventSystem
from systems.relationships import RelationshipSystem
import uuid

class GameEngine:
    def __init__(self, config=None, reset_save=False, save_file=None):
        self.config = config if config else Config()
        
        # 根据存档自动切换世界
        if save_file and not reset_save:
            try:
                with open(save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                world_id = data.get('world_id')
                if world_id:
                    # 查找对应的世界索引
                    for i, w in enumerate(self.config.worlds):
                        if w['id'] == world_id:
                            self.config.active_world_idx = i
                            print_info(f"🌍 根据存档自动切换世界至: {w['name']}")
                            break
            except Exception as e:
                print_warning(f"读取存档世界信息失败: {e}")

        self.ai = AIBrain(self.config)
        self.world = GameWorld(self.config)
        self.player = Character(self.config, reset_save=reset_save, save_file=save_file)
        self.paused = False
        self.game_over = False
        
        # Session stats
        self.session_stats = {
            "回合数": 0, "战斗次数": 0, "击杀数": 0,
            "探索次数": 0, "休息次数": 0, "NPC互动": 0,
            "总经验": 0, "升级次数": 0, "受伤次数": 0,
            "死亡次数": 0,
            "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0
        }
        self.start_time = time.time()
        self.turns_since_save = 0

    def handle_combat(self, enemy):
        print_event("战斗", f"遭遇了 {enemy['名称']} (Lv{enemy.get('等级', 1)})!")
        self.session_stats['战斗次数'] += 1
        
        player = self.player
        p_stats = player.game_stats
        
        # 战斗循环
        rounds = 0
        while p_stats['HP'] > 0:
            rounds += 1
            print_info(f"\n--- 第 {rounds} 回合 ---")
            
            # 玩家回合
            dmg, crit = CombatSystem.execute_turn(player, enemy, console)
            
            # 怪物死亡判定
            if 'HP' not in enemy:
                enemy['HP'] = enemy.get('等级', 1) * 20
            
            enemy['HP'] -= dmg
            print_info(f"⚔️  造成伤害: {dmg} (敌方剩余HP: {enemy['HP']})")
            
            if enemy['HP'] <= 0:
                print_success(f"💥 你击败了 {enemy['名称']}!")
                self.session_stats['击杀数'] += 1
                
                # 掉落结算
                exp = enemy.get('经验', 10)
                gold = enemy.get('金币', random.randint(1, 5))
                loot = enemy.get('掉落', [])
                
                player.gain_exp(exp)
                p_stats['金币'] += gold
                self.session_stats['总经验'] += exp
                
                if loot and random.random() < 0.3:
                    item = random.choice(loot)
                    # 尝试自动装备
                    if item.get('type') in ["武器", "防具", "饰品"]:
                        # 简单逻辑：如果当前没有装备，就装备上
                        slot_map = {"武器": "weapon", "防具": "armor", "饰品": "accessory"}
                        slot = slot_map.get(item.get('type'))
                        current_equip = player.save_data.get('equipment', {}).get(slot)
                        if not current_equip:
                            player.equip_item(item)
                            print_success(f"🛡️  获得并装备了: {item['name']}")
                        else:
                            player.inventory.append(item)
                            print_success(f"📦 获得战利品: {item['name']}")
                    else:
                        player.inventory.append(item)
                        print_success(f"📦 获得战利品: {item.get('name', '未知物品')}")
                
                print_info(f"💰 获得 {gold} 金币")
                
                # 不打不相识逻辑 (仅限NPC战斗)
                if enemy.get('is_npc_battle'):
                    if random.random() < 0.5:
                        print_info(f"🤝 {enemy['名称']} 对你的实力表示认可，结为好友！")
                        # 初始化关系
                        npc_id, _ = RelationshipSystem.initialize_npc_relationship(player, enemy, "战斗相识")
                        # 增加好感
                        rel_data = player.save_data['relationships'][npc_id]
                        rel_data['game_stats'] = enemy # 保存实力快照
                        rel_data['affection'] += 20
                return True

            # 怪物反击
            # 闪避判定
            dodge_rate = player.get_dodge_bonus() / 100.0 + (p_stats['等级'] - enemy.get('等级',1)) * 0.02
            if random.random() < max(0.05, dodge_rate):
                print_info(f"💨 你闪避了 {enemy['名称']} 的攻击")
                continue
            
            # 使用战斗系统执行怪物回合 (怪物可能会放技能！)
            e_dmg, e_crit = CombatSystem.execute_turn(enemy, player, console)
            
            player.take_damage(e_dmg)
            self.session_stats['受伤次数'] += 1
            
            crit_msg = " [bold red](暴击!)[/bold red]" if e_crit else ""
            print_warning(f"🛡️  {enemy['名称']} 反击造成 {e_dmg} 点伤害{crit_msg} (剩余HP: {p_stats['HP']}/{p_stats['MaxHP']})")
            
            if p_stats['HP'] <= 0:
                # 濒死判定
                if player.check_survival(enemy.get('等级', 1)):
                    # 生还后逃离战斗，不再继续送死
                    print_success(f"🏃 趁着最后一丝力气，你拼命逃离了战场！")
                    return True  # 视为战斗结束（逃脱）
                else:
                    self.handle_death(f"被 {enemy['名称']} 击杀", f"被{enemy['名称']}击杀")
                    return False
            
            # 回合结束MP恢复一丢丢
            player.heal(mp=2)
            
            time.sleep(self.config.speed * 0.05) # 战斗节奏
            
        return False

    def handle_death(self, death_summary, detailed_cause):
        """统一处理死亡逻辑（战斗/老死等）"""
        print_error(f"☠️  {death_summary}")
        self.player.die(detailed_cause, self.session_stats['回合数'])
        self.session_stats['死亡次数'] += 1
        
        # 检查是否有继承人
        heir_id, heir = self.player.get_eldest_child()
        if heir_id:
            print_info(f"👶 继承人: {heir.get('name')} 将继续冒险...")
            if self.player.switch_to_heir(heir_id):
                with console.status("[bold green]正在完成家族权力交接... (5s)[/bold green]"):
                    time.sleep(5)
                return True # 继承成功
        
        print_error("💔 没有继承人，家族血脉断绝...")
        self.game_over = True
        return False # 游戏结束

    def construct_prompt(self, event_type, event_data, extra_context=""):
        p = self.player
        stats = p.game_stats
        
        # 1. 核心属性摘要 (只列出突出的)
        core_stats = []
        for k in ['STR', 'AGI', 'INT', 'CON', 'CHA', 'LUK']:
            val = stats.get(k, 10)
            if val >= 20: core_stats.append(f"{k}高({val})")
            elif val <= 5: core_stats.append(f"{k}低({val})")
        
        attr_desc = ", ".join(core_stats) if core_stats else "属性均衡"
        
        # 2. 精神状态
        san = stats.get('SAN', 50)
        max_san = stats.get('MaxSAN', 99)
        san_status = "精神正常"
        if san < 20: san_status = "精神崩溃/疯狂"
        elif san < 40: san_status = "精神恍惚/恐惧"
        
        # 3. 提取角色人设核心信息
        char_desc = p.profile.get('角色描述', '一名冒险者')[:150]  # 限制长度
        
        # 心理特征摘要
        psych = p.profile.get('心理特征', {})
        psych_summary = ""
        if isinstance(psych, dict):
            # 提取关键词
            keywords = []
            for section, data in psych.items():
                if isinstance(data, dict) and '关键词' in data:
                    keywords.extend(data['关键词'][:2])  # 每个部分取前2个关键词
            if keywords:
                psych_summary = "、".join(keywords[:6])  # 最多6个关键词
        elif isinstance(psych, str):
            psych_summary = psych[:50]
        
        # 语言特征摘要
        lang = p.profile.get('语言特征', {})
        lang_summary = ""
        if isinstance(lang, dict):
            keywords = []
            for section, data in lang.items():
                if isinstance(data, dict) and '关键词' in data:
                    keywords.extend(data['关键词'][:2])
            if keywords:
                lang_summary = "、".join(keywords[:6])
            # 尝试获取示例
            examples = []
            for section, data in lang.items():
                if isinstance(data, dict) and '示例' in data:
                    examples.extend(data['示例'][:1])  # 每部分取1个示例
            if examples:
                lang_summary += f" | 示例: \"{examples[0][:30]}...\""
        elif isinstance(lang, str):
            lang_summary = lang[:50]
        
        prompt = f"""【角色扮演指令】
你现在必须完全扮演角色：{p.name}

【角色设定】
{char_desc}

【性格特点】{psych_summary if psych_summary else '无特殊设定'}
【说话风格】{lang_summary if lang_summary else '正常说话'}
【当前状态】Lv{stats['等级']} {p.save_data.get('race', '人类')} | HP:{stats['HP']}/{stats['MaxHP']} | {san_status}
【特质】{','.join(p.get_traits()) if p.get_traits() else '无'}

【当前事件】
[{event_type}] {event_data}
{extra_context}

【任务】
以{p.name}的第一人称写一句简短反应（30字以内）。

【重要要求】
1. 必须使用角色的说话风格和口癖！例如chi酱应该用"咱"自称，带颜文字和表情。
2. 即使在异世界，角色的语言习惯和人设也不会改变。
3. 不要使用与角色人设不符的术语。技术宅不会说"运转周天"，会说"这buff真强"。
"""
        return prompt

    def ai_generate_child_personality(self, p1_name, p1_personality, p1_style, 
                                       p2_name, p2_personality, p2_style, child_gender):
        """使用AI融合父母性格生成子嗣性格 (引入骰子判定天赋)"""
        
        from systems.dice import DiceSystem
        
        # 1. 投掷骰子决定先天运势
        # 使用默认50或父母平均幸运值
        luck_check, level, success = DiceSystem.check("投胎运势", 50)
        
        fortune_desc = "普通孩子"
        if level == "critical": fortune_desc = "天选之子(大成功)"
        elif level == "fumble": fortune_desc = "被诅咒的孩子(大失败)"
        elif level == "hard": fortune_desc = "聪慧过人"
        
        prompt = f"""请根据父母特点及【先天运势】生成孩子性格和名字。
父/母1: {p1_name} (性格:{p1_personality})
父/母2: {p2_name}
孩子性别: {child_gender}
先天运势判定: {fortune_desc} (请务必在性格中体现这一点)

请直接输出JSON（不要其他文字）：
{{"name":"孩子名字(需符合父母文化风格)","personality":"性格描述(30字)","language_style":"口癖(15字)"}}"""
        
        try:
            response, _ = self.ai.think_and_act(prompt)
            if response:
                import re
                match = re.search(r'\{.*\}', response.replace('\n', ' '), re.DOTALL)
                if match:
                    result = json.loads(match.group())
                    return (result.get('personality', ''), result.get('language_style', ''), result.get('name'))
        except Exception as e:
            print_warning(f"AI生成失败，使用默认融合: {e}")
        
        # 备用：简单融合
        if random.random() < 0.5:
            personality = f"继承了{p1_name}的部分性格，又有点{p2_name}的影子"
            style = p1_style[:40] if p1_style else p2_style[:40]
        else:
            personality = f"性格像{p2_name}，但也有{p1_name}的一面"
            style = p2_style[:40] if p2_style else p1_style[:40]
            
        return personality, style, None


    def process_ai_response(self, response, usage):
        if response:
            # 处理可能的骰子申请 [CHECK: 技能]
            from systems.dice import DiceSystem
            processed_response = DiceSystem.parse_and_roll(response, self.player)
            
            print_character(self.player.name, processed_response)
            self.player.add_event_to_history("AI日志", processed_response, "")
        
        if usage:
            self.session_stats['prompt_tokens'] += usage.get('prompt_tokens', 0)
            self.session_stats['completion_tokens'] += usage.get('completion_tokens', 0)
            self.session_stats['total_tokens'] += usage.get('total_tokens', 0)

            self.session_stats['total_tokens'] += usage.get('total_tokens', 0)

    def process_life_events(self):
        """处理生命事件：结婚、生子"""
        p = self.player
        age = p.save_data.get('age', 18)
        char_id = p.save_data.get('current_character_id')
        member = p.save_data.get('family_tree', {}).get('members', {}).get(char_id)
        
        if not member: return
        
        # 1. 结婚判定 (适婚年龄 18-50, 单身)
        if 18 <= age <= 50 and not member.get('spouse_id'):
            # 每回合 1% 概率结婚
            if random.random() < 0.01:
                spouse_npc = self.world.get_random_npc(npc_type="伴侣")
                if not spouse_npc:
                     # Fallback check
                     available = []
                     if isinstance(self.world.npcs, dict):
                         # Filter manually if get_random_npc logic is strict
                         for n, d in self.world.npcs.items():
                             if isinstance(d, dict) and d.get('类型') == '可结伴':
                                 available.append((n, d))
                     if available:
                         name, data = random.choice(available)
                         spouse_npc = data.copy()
                         spouse_npc['名称'] = name
                
                # print(f"DEBUG: spouse_npc type: {type(spouse_npc)}, value: {spouse_npc}")
                spouse_name = spouse_npc.get('名称', '神秘伴侣') if spouse_npc else "神秘伴侣"
                spouse_id = str(uuid.uuid4())[:8]
                member['spouse_id'] = spouse_id
                
                # 记录配偶 (简化，只存ID和名字)
                # 实际可以加到family_tree里，但作为NPC可能不需要完整数据
                print_success(f"💍 喜结良缘！你与 {spouse_name} 结婚了。")
                p.add_event_to_history("结婚", f"与 {spouse_name} 结婚", "家族诞生")
                with console.status("[bold green]💍 婚礼现场... (庆祝 5s)[/bold green]"):
                    time.sleep(5)

    def handle_birth(self, parent_data, spouse_id, spouse_name="配偶"):
        """处理生子逻辑"""
        p = self.player
        char_id = p.save_data.get('current_character_id')
        member = parent_data # self.player.save_data['family_tree']['members'][char_id]
        
        child_id = str(uuid.uuid4())[:8]
        child_gender = random.choice(['男', '女'])
        child_name = f"{p.name}的{'儿子' if child_gender=='男' else '女儿'}" 
        
        # 基因遗传 logic
        parent_genome = p.save_data.get('player_genome', {})
        spouse_genome = GeneticSystem.generate_random_genome() # 简化：每次随机生成配偶基因
        
        child_genome = GeneticSystem.crossover(parent_genome, spouse_genome)
        child_genome, mutations = GeneticSystem.mutate(child_genome, mutation_rate=0.05)
        if mutations:
            print_info(f"🧬 基因突变: {', '.join(mutations)}")
        
        # 创建子女记录
        child_data = {
            "name": child_name,
            "id": child_id,
            "gender": child_gender,
            "generation": member.get('generation', 1) + 1,
            "parent_ids": [char_id, spouse_id],
            "birth_turn": self.session_stats['回合数'], 
            "genome": child_genome,
            "gene_score": GeneticSystem.calculate_gene_score(child_genome),
            "gene_score": GeneticSystem.calculate_gene_score(child_genome),
            "personality": "未知",
            "language_style": "未知",
            "children_ids": []
        }
        
        # 尝试生成性格
        try:
            p1 = p.psychology[:100]
            p1_style = p.language_style[:100]
            # 配偶信息缺失，用通用描述替代
            p2 = "未知"
            p2_style = "未知"
            
            c_personality, c_style, c_name = self.ai_generate_child_personality(
                p.name, p1, p1_style,
                spouse_name, p2, p2_style,
                child_gender
            )
            child_data['personality'] = c_personality
            child_data['language_style'] = c_style
            
            if c_name:
                child_data['name'] = c_name
                child_name = c_name
                print_info(f"✨ AI为孩子起名: {c_name}")
        except Exception as e:
            # print_error(f"性格生成错误: {e}")
            pass
        
        p.save_data['family_tree']['members'][child_id] = child_data
        member['children_ids'].append(child_id)
        p.save()
        
        print_success(f"👶 喜得贵子！{child_name} 出生了。(基因评分: {child_data['gene_score']})")
        p.add_event_to_history("生子", f"{child_name} 出生", "家族延续")
        with console.status("[bold green]👶 庆祝新生... (庆祝 5s)[/bold green]"):
            time.sleep(5)

    def process_life_events(self):
        """处理生命事件：结婚、亲密、生子"""
        p = self.player
        age = p.save_data.get('age', 18)
        char_id = p.save_data.get('current_character_id')
        member = p.save_data.get('family_tree', {}).get('members', {}).get(char_id)
        
        if not member: return
        
        # 1. 结婚判定 (适婚年龄 18-50, 单身)
        if 18 <= age <= 50 and not member.get('spouse_id'):
            # 每回合 1% 概率结婚
            if random.random() < 0.01:
                spouse_npc = self.world.get_random_npc(npc_type="伴侣")
                if not spouse_npc:
                     # Fallback check
                     available = []
                     if isinstance(self.world.npcs, dict):
                         # Filter manually if get_random_npc logic is strict
                         for n, d in self.world.npcs.items():
                             if isinstance(d, dict) and d.get('类型') == '可结伴':
                                 available.append((n, d))
                     if available:
                         name, data = random.choice(available)
                         spouse_npc = data.copy()
                         spouse_npc['名称'] = name
                
                spouse_name = spouse_npc.get('名称', '神秘伴侣') if spouse_npc else "神秘伴侣"
                spouse_id = str(uuid.uuid4())[:8]
                member['spouse_id'] = spouse_id
                member['spouse_name'] = spouse_name # 记录名字方便后续可以重构NPC对象
                
                print_success(f"💍 喜结良缘！你与 {spouse_name} 结婚了。")
                p.add_event_to_history("结婚", f"与 {spouse_name} 结婚", "家族诞生")

        # 2. 婚后生活 (已婚) - 替代原本简单的生子判定
        spouse_id = member.get('spouse_id')
        if spouse_id:
            # 随机构造一个伴侣对象用于互动
            spouse_name = member.get('spouse_name', '配偶')
            spouse_npc = {
                "名称": spouse_name,
                "类型": "伴侣",
                "id": spouse_id
            }
            
            # 尝试亲密
            # 夫妻默认好感度高 -> 概率 DO
            # 但也不能每回合都判，稍微控制下频率，比如每回合 20% 概率尝试亲密
            if random.random() < 0.2:
                _, is_pregnant = RelationshipSystem.attempt_intimacy(p, spouse_npc)
                if is_pregnant:
                    self.handle_birth(member, spouse_id, spouse_name)
                    
            # 伴侣传授技能 (2% 概率)
            if random.random() < 0.02:
                 CombatSystem.ai_teach_skill(p, spouse_name, "伴侣", self.ai)

        # 3. 致命诱惑/艳遇判定
        # 必须确认已婚才触发出轨逻辑
        spouse_id_check = member.get('spouse_id')
        if spouse_id_check and member.get('spouse_name') and random.random() < 0.05:
            self.process_temptation(p, member)

    def process_child_growth(self):
        """处理子嗣成长随机事件"""
        current_turn = self.session_stats['回合数']
        
        char_id = self.player.save_data.get('current_character_id')
        members = self.player.save_data['family_tree']['members']
        current_char = members.get(char_id)
        if not current_char: return
        
        child_ids = current_char.get('children_ids', [])
        valid_kids = []
        
        for cid in child_ids:
            child = members.get(cid)
            if not child or child.get('death_turn'): continue
            birth = child.get('birth_turn', 0)
            age = (current_turn - birth) // RaceSystem.TURNS_PER_YEAR
            if 3 <= age < 16: # 3-16岁成长事件
                valid_kids.append((cid, child, age))
        
        if not valid_kids: return
        
        cid, child, age = random.choice(valid_kids)
        name = child['name']
        
        events = [
            (f"{name}在后院练习挥剑", "STR", 1),
            (f"{name}沉迷于阅读古籍", "INT", 1),
            (f"{name}帮助邻居照顾宠物", "CHA", 1),
            (f"{name}即使跌倒也没哭", "CON", 1),
            (f"{name}爬树掏到了鸟蛋", "LUK", 1),
            (f"{name}在集市上灵活地穿梭", "AGI", 1)
        ]
        ev_desc, stat, val = random.choice(events)
        
        print_info(f"📚 [家事] {ev_desc} ({stat} +{val})")
        
        if 'growth_bonus' not in child: child['growth_bonus'] = {}
        child['growth_bonus'][stat] = child['growth_bonus'].get(stat, 0) + val
        self.player.save()

    def process_temptation(self, player, member):
        """处理诱惑事件: AI决策版 (仅已婚角色)"""
        # 安全检查：必须已婚
        if not member.get('spouse_id') or not member.get('spouse_name'):
            return
        
        # 1. 生成诱惑对象
        lover_npc = self.world.get_random_npc(npc_type="可结伴")
        if not lover_npc: return
        
        lover_name = lover_npc.get('名称', '神秘人')
        lover_desc = lover_npc.get('描述', '充满魅力')
        
        # 2. 构建AI Prompt (Enhanced Roleplay)
        traits = player.get_traits()
        spouse_name = member.get('spouse_name', '配偶')
        children_ids = member.get('children_ids', [])
        num_children = len(children_ids)
        
        # 获取人设详细信息
        char_desc = player.profile.get('角色描述', '一名普通的冒险者')[:150]
        
        # 提取语言特征关键词（与construct_prompt一致）
        lang = player.profile.get('语言特征', {})
        lang_summary = ""
        if isinstance(lang, dict):
            keywords = []
            examples = []
            for section, data in lang.items():
                if isinstance(data, dict):
                    if '关键词' in data:
                        keywords.extend(data['关键词'][:2])
                    if '示例' in data:
                        examples.extend(data['示例'][:1])
            if keywords:
                lang_summary = "、".join(keywords[:6])
            if examples:
                lang_summary += f" | 例: \"{examples[0][:25]}...\""
        elif isinstance(lang, str):
            lang_summary = lang[:50]
        else:
            lang_summary = "正常说话"

        # 准确描述家庭状况
        if num_children == 0:
            family_desc = f"已婚，配偶是 {spouse_name}，暂时没有孩子"
        else:
            family_desc = f"已婚，配偶是 {spouse_name}，有 {num_children} 个孩子"
        
        prompt = f"""【角色扮演指令】
你现在必须完全沉浸在角色：{player.name} 中。
你的设定：{char_desc}
你的口癖/说话风格：{lang_summary}
你的性格标签：[{', '.join(traits)}]
你的现状：{family_desc}

【触发事件】：
你在外面偶遇了 {lover_name} ({lover_desc})。对方对你释放了强烈的费洛蒙，试图诱惑你出轨，气氛变得燥热暧昧。

【任务】：
请以 {player.name} 的第一人称视角，用**极度符合你人设和口癖**的语气描写你的内心弹幕和最终决定。
- 严禁使用“虽然...但是...责任感”这种AI味的说教！
- 如果你是傲娇，就骂骂咧咧地拒绝；如果是魅魔，可能欲拒还迎；如果是老实人，就惊慌失措。
- 必须生动、口语化。

格式要求：
一段内心独白(50字以内)
[DECISION: ACCEPT] 或 [DECISION: REJECT]
"""
        # 3. 调用AI
        print_info(f"🤔 {player.name} 正在面对诱惑进行内心挣扎...")
        content, usage = self.ai.think_and_act(prompt)
        self.process_ai_response(content, usage)
        
        # 4. 解析结果
        if content and "[DECISION: ACCEPT]" in content:
            print_warning(f"💓 [AI决定] 你未能抵挡诱惑...")
            # 执行亲密
            success, is_pregnant = RelationshipSystem.attempt_intimacy(player, lover_npc)
            if success:
                player.add_event_to_history("出轨", f"未能抵挡诱惑，与 {lover_name} 发生了关系 (AI决策)", "情感波折")
        else:
            print_success(f"🛡️ [AI决定] 你拒绝了诱惑，守住了底线。")

    def run_turn(self):
        self.session_stats['回合数'] += 1
        current_region_id = self.player.current_location
        
        # 0. 自动换地图逻辑 (Auto-Travel)
        # 每10回合检查一次，避免过于频繁
        if self.session_stats['回合数'] % 10 == 0:
            current_region = self.world.get_region(current_region_id)
            player_level = self.player.game_stats['等级']
            
            # 1. 检查是否等级过高，应该去更高级地图
            if current_region and player_level > current_region.get('max_level', 100) + 2:
                # 寻找更高级的地图
                for region in self.world.data['地区']:
                    r_min = region.get('min_level', 0)
                    r_max = region.get('max_level', 100)
                    if r_min > current_region.get('min_level', 0) and r_min <= player_level <= r_max:
                        # 找到了合适的下一站
                        self.player.current_location = region['id']
                        print_success(f"🚀 [自动探索] 你感觉 {current_region.get('名称')} 已经没有挑战了，前往了新的地区：{region['名称']} (Lv.{r_min}-{r_max})")
                        current_region_id = region['id'] # 更新当前引用
                        break
            
            # 2. 检查是否等级过低(比如通过修改或其他方式误入)，应该撤退
            elif current_region and player_level < current_region.get('min_level', 0) - 1:
                 # 寻找适合的低级地图
                 for region in self.world.data['地区']:
                    r_min = region.get('min_level', 0)
                    r_max = region.get('max_level', 100)
                    if r_min <= player_level <= r_max:
                        self.player.current_location = region['id']
                        print_warning(f"🏳️ [自动撤退] {current_region.get('名称')} 太危险了，你撤退到了安全区域：{region['名称']}")
                        current_region_id = region['id']
                        break
        
        # 1. 尝试触发随机事件（子嗣成长、商人等）
        if random.random() < 0.05:
            # 商人事件
            usage = MerchantSystem.interact(self.player, self.ai, console)
            # 记录商人AI消耗
            if usage:
                self.session_stats['prompt_tokens'] += usage.get('prompt_tokens', 0)
                self.session_stats['completion_tokens'] += usage.get('completion_tokens', 0)
                self.session_stats['total_tokens'] += usage.get('total_tokens', 0)
                
                self.session_stats['completion_tokens'] += usage.get('completion_tokens', 0)
                self.session_stats['total_tokens'] += usage.get('total_tokens', 0)
        
        # 1.2 顿悟事件 (领悟新技能)
        if random.random() < 0.02 and self.player.game_stats['等级'] >= 5:
             CombatSystem.ai_learn_skill(self.player, self.ai)

        # 1.5 处理生命事件 (结婚生子)
        self.process_life_events()
        
        # 1.6 子嗣成长 (5%概率)
        if random.random() < 0.05:
            self.process_child_growth()

        # 2. 更新年龄/自然死亡检查
        death_cause = self.player.update_age(self.session_stats['回合数'])
        if death_cause == "old_age":
            self.handle_death(f"{self.player.name} 寿终正寝了...", "寿终正寝")
            if self.game_over: return
            
        # 3. 地区主要事件
        event_type = self.world.get_random_event_type(current_region_id)
        
        ai_input_data = ""
        
        if event_type == "战斗":
            enemy = self.world.get_encounter(current_region_id, self.player.game_stats['等级'])
            ai_input_data = f"遭遇怪物：{enemy['名称']}"
            if not self.handle_combat(enemy):
                if self.game_over: return
        
        elif event_type == "探索":
            self.session_stats['探索次数'] += 1
            region_name = self.world.get_region(current_region_id).get('名称', current_region_id)
            world_name = self.world.data.get('世界名称', '异世界')
            
            # 引入骰子系统
            from systems.dice import DiceSystem

            explore_desc = ""
            # 根据配置概率 AI 生成独特文案
            # 引入骰子系统
            from systems.dice import DiceSystem
            import json
            import re
            
            # 预先进行幸运判定，给 AI 参考，但最终由 AI 制定的结果为准
            luck_val = self.player.game_stats.get('幸运', 50)
            luck_roll, level, success = DiceSystem.check("探索运势", luck_val)
            luck_context = f"运势：{level} ({luck_roll})"

            explore_json = None
            found_item = None
            
            if random.random() < self.config.ai_event_rate:
                # 请求 AI 直接返回结构化数据
                prompt = (f"角色在{world_name}的{region_name}探索。{luck_context}。\n"
                          f"请生成探索结果，包含：简短经历描述、发现的物品(可选)、理智值扣除(如有恐怖)。\n"
                          f"直接输出JSON：\n"
                          f'{{"desc": "经历描述(30字)", "item": "物品名或null", "san_cost": 0}}')
                try:
                    content, usage = self.ai.think_and_act(prompt)
                    if content:
                        match = re.search(r'\{.*\}', content.replace('\n', ' '), re.DOTALL)
                        if match:
                            explore_json = json.loads(match.group())
                            self.process_ai_response(None, usage)
                except Exception as e:
                    # print_warning(f"AI 生成解析失败: {e}")
                    pass

            explore_desc = ""
            is_critical = False
            DiceSystem.last_result = None # 重置状态
            
            # A. 使用 AI 生成的结果
            if explore_json:
                explore_desc = explore_json.get('desc', '你四处看了看。')
                
                # 在处理物品前，先解析描述中的骰子判定
                explore_desc = DiceSystem.parse_and_roll(explore_desc, self.player)
                if DiceSystem.last_result == 'critical': is_critical = True
                
                # 处理物品
                item_name = explore_json.get('item')
                if item_name and str(item_name).lower() != 'null' and str(item_name).lower() != 'none':
                     # 尝试在数据库找，找不到就创建临时物品
                     found_item = None
                     # 简单的查找逻辑
                     base_item = self.world.get_random_item() or {"type": "杂物", "stats": {}}
                     base_item = base_item.copy()
                     base_item['name'] = item_name
                     base_item['desc'] = f"在{region_name}发现的{item_name}"
                     
                     self.player.inventory.append(base_item)
                     explore_desc += f" (获得: {item_name})"
                
                # 处理 Sanity 扣除
                cost = explore_json.get('san_cost', 0)
                if cost > 0:
                    current_san = self.player.game_stats.get('SAN', 50)
                    self.player.game_stats['SAN'] = max(0, current_san - cost)
                    explore_desc += f" [理智 -{cost}]"
                    if self.player.game_stats['SAN'] < 20: 
                        explore_desc += " (精神崩溃...)"

            # B. Fallback 到传统逻辑
            else:
                explore_desc = self.world.get_random_exploration_text()
                # ... (保留原有的 {item} 替换逻辑作为保底，此处简化)
                if "{item}" in explore_desc:
                     found_item = self.world.get_random_item() or {"name": "神秘碎片"}
                     item_name = found_item.get('name', '未知物品')
                     explore_desc = explore_desc.replace("{item}", item_name)
                     self.player.inventory.append(found_item)
                     
                # 也要检查传统文本里是否有骰子判定
                explore_desc = DiceSystem.parse_and_roll(explore_desc, self.player)
                if DiceSystem.last_result == 'critical': is_critical = True

            # 随机奖励逻辑 (基础经验)
            exp = 5 + random.randint(0, self.player.game_stats['等级'])
            gold = 0
            
            # 如果没找到物品，才给金币
            if not found_item and random.random() < 0.2:
                gold = random.randint(1, 10)
            
            # 大成功奖励翻倍
            if is_critical:
                exp *= 5
                gold = max(5, gold * 5) # 确保大成功至少有5金币(即使原本是0)
                print_success("✨ 吉星高照！大成功获得 5倍 奖励！")

            self.player.gain_exp(exp)
            self.player.game_stats['金币'] += gold
            self.session_stats['总经验'] += exp
            
            # 发放物品
            if found_item:
                self.player.inventory.append(found_item)
            
            # 显示更沉浸的文本
            reward_text = f" (经验+{exp}" 
            if gold > 0: reward_text += f", 金币+{gold}"
            if found_item: reward_text += f", 获得: {item_name}"
            reward_text += ")"
            
            print_event("探索", f"[{region_name}] {explore_desc}{reward_text}")
            ai_input_data = f"在{region_name}探索: {explore_desc}"
            
        elif event_type == "休息":
            self.session_stats['休息次数'] += 1
            heal_hp = int(self.player.game_stats['MaxHP'] * 0.2)
            heal_mp = int(self.player.game_stats['MaxMP'] * 0.2)
            self.player.heal(heal_hp, heal_mp)
            print_event("休息", f"你找了个安全的地方休息，恢复了 {heal_hp} HP。")
            ai_input_data = "休息调整状态。"

        elif event_type == "NPC":
            self.session_stats['NPC互动'] += 1
            npc = self.world.get_random_npc()
            if npc:
                print_event("NPC", f"你遇到了 {npc['名称']} ({npc['职业']})。")
                ai_input_data = f"偶遇了{npc['名称']}，{npc['描述']}"
                
                # 简单交互逻辑
                action = random.choice(["chat", "gift", "romance"])
                
                # 获取或初始化关系
                rel_id, rel_data = RelationshipSystem.initialize_npc_relationship(self.player, npc, "偶遇")
                affinity = rel_data['affection']
                
                if action == "chat":
                    greetings = [
                        f"{npc['名称']} 微笑着向你打招呼。",
                        f"{npc['名称']} 似乎在忙着什么，只是匆匆点了点头。",
                        f"{npc['名称']} 跟你聊了聊最近的天气。",
                        f"你和 {npc['名称']} 交换了一些冒险情报。"
                    ]
                    print_info(random.choice(greetings))
                    # 聊天增加好感
                    val = random.randint(3, 6)
                    rel_data['affection'] += val
                    print_info(f"  (好感度 +{val} -> {rel_data['affection']})")
                    
                elif action == "gift":
                    gift_coin = random.randint(1, 10)
                    self.player.game_stats['金币'] += gift_coin
                    print_success(f"🎁 {npc['名称']} 送给你 {gift_coin} 金币作为见面礼！")
                    val = random.randint(5, 12)
                    rel_data['affection'] += val
                    print_info(f"  (好感度 +{val} -> {rel_data['affection']})")
                    
                elif action == "romance":
                    # 尝试发展关系
                    if affinity >= 80 and rel_data['status'] != "恋人":
                        if random.random() < 0.5:
                            rel_data['status'] = "恋人"
                            print_success(f"💖 你与 {npc['名称']} 的关系升温了，成为了恋人！")
                            self.player.add_event_to_history("恋爱", f"与 {npc['名称']} 确认了恋人关系", "情感")
                    elif affinity >= 50 and rel_data['status'] == "陌生人":
                         rel_data['status'] = "朋友"
                         print_success(f"🤝 你与 {npc['名称']} 一见如故，成为了朋友。")
                    elif affinity >= 20 and rel_data['status'] == "陌生人":
                         # 增加一个小状态提示
                         print_info(f"😊 你和 {npc['名称']} 算是熟人了。")
                
                # 状态更新提示
                new_status = RelationshipSystem.get_relation_level(rel_data['affection'])
                if new_status != rel_data.get('status_label', ''):
                     rel_data['status_label'] = new_status
                
                # 检查表白事件
                RelationshipSystem.check_romance_events(self.player, rel_id, console)
        
        elif event_type == "奇遇":
            # 尝试生成动态事件
            usage = None
            if random.random() < 0.5: # 50%概率触发AI生成
                 event_data, usage = DynamicEventSystem.generate_random_event(
                    self.ai, self.player, self.world.get_region(current_region_id)
                 )
                 if event_data:
                     DynamicEventSystem.handle_event(self.player, event_data, console)
                     ai_input_data = f"触发奇遇：{event_data['title']}"
                     # 统计token
                     self.process_ai_response(None, usage)
            
            # 失败或未触发AI生成，回退到静态奇遇
            if not usage:
                adv = self.world.get_random_adventure()
                if adv:
                    print_event("奇遇", f"{adv['名称']}: {adv['描述']}")
                    # 结算奇遇效果
                    self.apply_game_effect(adv.get('效果', {}))
                    ai_input_data = f"触发奇遇：{adv['名称']}"



        
        # 4. 生成角色主观反应 (根据配置概率)
        # 恢复丢失的逻辑
        if ai_input_data and random.random() < self.config.ai_event_rate:
             try:
                 prompt = self.construct_prompt(event_type, ai_input_data)
                 # 加上简单的防破防指令
                 prompt += "\n(请以第一人称简短吐槽或感慨，不要重复事件描述，30字以内)"
                 
                 reaction, usage = self.ai.think_and_act(prompt)
                 if reaction:
                     # 清理可能的多余符号
                     reaction = reaction.strip('"').strip()
                     print_character(self.player.name, reaction)
                     self.process_ai_response(None, usage)
             except Exception as e:
                 # print_error(f"AI反应生成错误: {e}")
                 pass

        # 0.5 历史记录压缩逻辑
        if self.config.history_limit > 0:
             hist_len = len(self.player.save_data.get('event_history', []))
             threshold = self.config.history_compress_threshold
             retention = self.config.history_retention_count
             
             if hist_len >= threshold: 
                 print_info(f"🧠 历史记录达到{threshold}条，正在进行压缩...")
                 
                 # 只总结要被移除的那部分(前N条)，保留后retention条作为新鲜记忆
                 keep_count = retention
                 history = self.player.save_data.get('event_history', [])
                 to_summarize = history[:-keep_count]
                 
                 text = ""
                 for h in to_summarize:
                     text += f"{h['描述']}; "
                     
                 prompt = f"用30字概括以下经历：{text[:500]}"
                 summary, _ = self.ai.think_and_act(prompt)
                 
                 if summary:
                     self.player.compress_history(self.ai, summary, keep_count)
        
        # 自动保存
        self.turns_since_save += 1
        if self.turns_since_save >= self.config.autosave_interval:
            self.player.save()
            self.turns_since_save = 0
            
        time.sleep(self.config.speed * 0.1)

    def main_loop(self):
        print_header("✨ 游戏开始 ✨")
        print_info(f"当前角色: {self.player.name} | 'F'暂停 | 'S'查看摘要 | 'Q'退出")
        
        last_time = 0
        
        try:
            while not self.game_over:
                # 输入检测
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key.lower() == b'f':
                        self.paused = not self.paused
                        status = "暂停" if self.paused else "继续"
                        print_warning(f"\n⏸️  游戏{status}")
                    elif key.lower() == b'q':
                        print_warning("\n💾 正在保存并退出...")
                        self.player.save()
                        self.game_over = True
                        break
                    elif key.lower() == b's':
                        # 查看摘要和状态
                        console.clear()
                        print_header(f"📜 {self.player.name} 的人生小结")
                        
                        summary = self.player.save_data.get('summary', '暂无摘要')
                        print_info(f"\n[长期记忆]\n{summary}")
                        
                        history = self.player.save_data.get('event_history', [])
                        print_info(f"\n[短期记忆 ({len(history)}条)]")
                        for h in history[-5:]:
                            print(f"  - [{h['时间']}] {h['描述']}")
                            
                        console.input("\n按回车键返回游戏...")
                        console.clear()
                        # 重绘界面提示
                        print_header("✨ 游戏继续 ✨")
                        print_info(f"当前角色: {self.player.name} | 'F'暂停 | 'S'查看摘要 | 'Q'退出")

                if not self.paused:
                    current_time = time.time()
                    if current_time - last_time >= self.config.speed:
                        self.run_turn()
                        last_time = time.time()
                        # 显示倒计时提示，不用每次都刷屏，只在回合结束提示一下
                        # print_info(f"⏳ 等待 {self.config.speed}s ...")
                
                time.sleep(self.config.ui_refresh_rate)

        except KeyboardInterrupt:
            print_warning("\n\n⚠️  检测到强制退出信号...")
            self.player.save()
            self.game_over = True
        except Exception as e:
            print_error(f"❌ 游戏发生致命错误: {e}")
            import traceback
            traceback.print_exc()
            self.player.save() # 尝试保存
            console.input("⚠️ 按回车键退出...")

        # 结算
        end_time = time.time()
        duration = int(end_time - self.start_time)
        print_header("\n=== 游戏结束 ===")
        print_info(f"本次存活时间: {duration}秒")
        
        # 打印本次会话总结
        self.print_session_summary()
        
        
        self.player.update_lifetime_stats(self.session_stats, duration)
        
        console.input("\n请按回车键结束游戏...")

    def apply_game_effect(self, effect):
        """应用游戏效果 (解析JSON)"""
        if not effect: return
        
        p = self.player
        
        # 递归处理 '随机'
        if '随机' in effect:
            chosen = random.choice(effect['随机'])
            if isinstance(chosen, str):
                self.resolve_effect_string(chosen)
            elif isinstance(chosen, dict):
                self.apply_game_effect(chosen)
            return

        # 治疗
        if '治疗' in effect:
            if effect['治疗'] == '全满':
                p.heal(p.game_stats['MaxHP'], p.game_stats['MaxMP'])
                print_success("💖 状态完全恢复！")
            elif isinstance(effect['治疗'], int):
                p.heal(effect['治疗'])
                print_success(f"💚 恢复了 {effect['治疗']} 点生命")
        
        # 经验
        if '经验' in effect:
            p.gain_exp(effect['经验'])
            
        # 金币 (兼容 '金币' 和 '获得金币')
        gold = effect.get('金币', effect.get('获得金币', 0))
        if gold > 0:
            p.game_stats['金币'] += gold
            print_success(f"💰 获得了 {gold} 金币")

        # 获得物品
        if '获得物品' in effect:
            item_name = effect['获得物品']
            item = self.world.get_item_by_name(item_name)
            if item:
                p.inventory.append(item)
                print_success(f"📦 获得了物品: {item_name}")
            else:
                sim_item = {"name": item_name, "type": "特殊", "desc": "奇遇获得的物品"}
                p.inventory.append(sim_item)
                print_success(f"📦 获得了物品: {item_name}")

        # 永久加成
        if '永久加成' in effect:
            for stat, val in effect['永久加成'].items():
                if stat in p.game_stats:
                    p.game_stats[stat] += val
                    print_success(f"💪 {stat} 永久增加了 {val}点！")
                    
        # 触发NPC交友
        if effect.get('触发NPC交友'):
             npc = self.world.get_random_npc('可结伴')
             if npc:
                 print_success(f"🤝 你与 {npc['名称']} 成为了朋友！")
                 # Future: Add to relationships

    def resolve_effect_string(self, text):
        """解析简化的效果描述"""
        p = self.player
        if "大量金币" in text:
            amount = random.randint(100, 500)
            p.game_stats['金币'] += amount
            print_success(f"💰 意外横财！获得了 {amount} 金币")
        elif "诅咒" in text:
            p.game_stats['攻击'] = max(1, p.game_stats['攻击'] - 2)
            print_warning("💀 遭受诅咒，攻击力下降了 2 点...")
        elif "稀有武器" in text:
            # Mock
            w = {"name": "远古之剑", "type": "武器", "stats": {"attack": 15}, "rarity": 4}
            p.inventory.append(w)
            print_success(f"⚔️  发现了一把 {w['name']}!")
        else:
            print_info(f"✨ 发生了一些事: {text}")

    def print_session_summary(self):
        """打印本次会话的统计信息"""
        stats = self.session_stats
        life = self.player.save_data.get('lifetime_stats', {})
        
        # 计算累计值 (当前存档累积 + 本次)
        total_turns = life.get('总回合数', 0) + stats['回合数']
        total_tokens = life.get('总total_tokens', 0) + stats['total_tokens']
        total_exp = life.get('总获得经验', 0) + stats['总经验']
        
        # 1. 基础统计
        summary_text = f"""
[bold green]--- 📊 数据结算 ---[/bold green]

[cyan]本次会话:[/cyan]
⏱️  回合数: {stats['回合数']}
⚔️  战斗/击杀: {stats['战斗次数']} / {stats['击杀数']}
🗺️  探索/互动: {stats['探索次数']} / {stats['NPC互动']}
✨ 获得经验: {stats['总经验']}
🪙 [bold yellow]消耗Token: {stats['total_tokens']}[/bold yellow]

[magenta]历史累计 (含本次):[/magenta]
⏱️  总回合数: {total_turns}
✨ 总经验: {total_exp}
💰 [bold yellow]总消耗Token: {total_tokens}[/bold yellow]
"""
        console.print(Panel(summary_text, title="📊 冒险结算", border_style="blue"))
        
        # 2. AI生成剧情总结
        print_info("🧠 正在生成本次冒险的剧情回顾...")
        try:
            # 获取本次会话期间的历史记录
            # 简单策略：取最近的N条记录，或者根据时间筛选(如果历史记录有时间戳)
            # 这里取最近20条，假设一局游戏也就这么多有效记录
            history = self.player.save_data.get('event_history', [])
            recent_events = history[-30:] if len(history) > 30 else history
            
            if not recent_events:
                print_warning("暂无足够事件生成总结。")
                return

            text = ""
            for h in recent_events:
                text += f"[{h['时间']}] {h['描述']} -> {h['结果']}\n"
                
            prompt = f"""
请根据以下冒险日志，用一段通俗幽默的话总结 {self.player.name} 这次的游戏经历（100字左右）：
重点关注：发生了什么趣事、获得了什么成就、以及最后的结局（是主动退出还是意外死亡）。
请用第三人称叙述，像在讲故事一样。

日志：
{text}
"""
            content, usage = self.ai.think_and_act(prompt)
            if content:
                console.print(Panel(content, title="📜 冒险回顾 (AI生成)", border_style="green"))
                # 累加Token消耗
                if usage:
                     print_info(f"(本次总结消耗: {usage.get('total_tokens', 0)} tokens)")
                     
        except Exception as e:
            print_error(f"生成总结失败: {e}")
