
import random
import uuid
from core.utils import print_info, print_success, print_warning, print_error, print_event

class RelationshipSystem:
    """
    深度社交系统：管理好感度、亲密行为、出轨与怀孕
    """
    
    # 好感度阈值
    LEVELS = {
        "陌生人": 0,
        "相识": 20,
        "朋友": 50,
        "恋人": 80, # 可以啪啪啪
        "挚爱": 100
    }
    
    @staticmethod
    def get_relation_level(affection):
        for status, limit in reversed(RelationshipSystem.LEVELS.items()):
            if affection >= limit:
                return status
        return "陌生人"
    
    @staticmethod
    def initialize_npc_relationship(player, npc_data, encounter_type="偶遇"):
        """初始化NPC关系（生成基因、性格等）"""
        npc_name = npc_data.get('名称', '未知')
        npc_id = npc_name.replace(' ', '_').lower() # 简单ID生成
        
        relationships = player.save_data.get('relationships', {})
        
        if npc_id in relationships:
            return npc_id, relationships[npc_id]
            
        # 导入基因系统
        from systems.genetics import GeneticSystem
        
        # 生成NPC的基因组
        if encounter_type == '战斗相识':
            npc_genome = GeneticSystem.generate_npc_genome(strength_bias=2)  # 战斗型偏向
        else:
            npc_genome = GeneticSystem.generate_npc_genome(strength_bias=-1)  # 社交型偏向
        
        npc_gene_score = GeneticSystem.calculate_gene_score(npc_genome)
        gene_desc = GeneticSystem.describe_genome(npc_genome)
        
        relationships[npc_id] = {
            "id": npc_id,
            "名称": npc_name,
            "性别": npc_data.get('性别', '未知'),
            "性格": npc_data.get('性格', '未知'),
            "口癖": npc_data.get('口癖', ''),
            "affection": npc_data.get('好感初始', 30), # 统一用 affection
            "status": "相识",
            "相识回合": player.save_data.get('lifetime_stats', {}).get('总回合数', 0),
            "是伴侣": False,
            "遭遇方式": encounter_type,
            "genome": npc_genome,
            "gene_score": npc_gene_score,
            "攻击": npc_data.get('攻击', 10),
            "防御": npc_data.get('防御', 5)
        }
        
        player.save_data['relationships'] = relationships
        
        print_info(f"🧬 {npc_name}基因: {gene_desc}")
        print_success(f"📝 {npc_name}已加入关系列表 ({encounter_type})")
        
        return npc_id, relationships[npc_id]

    @staticmethod
    def check_romance_events(player, npc_id, console):
        """检查表白事件"""
        relationships = player.save_data.get('relationships', {})
        if npc_id not in relationships: return
        
        npc_data = relationships[npc_id]
        affection = npc_data.get('affection', 0)
        is_spouse = npc_data.get('是伴侣', False)
        status = npc_data.get('status', '陌生人')
        
        # 好感度达到70且还不是伴侣/恋人时，有几率表白
        if affection >= 70 and not is_spouse and status != "恋人":
            # 根据玩家性格判断谁主动
            player_personality = player.psychology
            npc_personality = npc_data.get('性格', '')
            
            # 判断主动方
            player_active = any(kw in player_personality for kw in ['活泼', '主动', '热情', '大胆', '开朗'])
            npc_active = any(kw in npc_personality for kw in ['活泼', '主动', '热情', '大胆', '开朗'])
            
            initiator = player.name
            target = npc_data['名称']
            
            if not player_active and (npc_active or random.random() < 0.5):
                initiator = npc_data['名称']
                target = player.name
            
            if random.random() < 0.3:  # 30%概率触发表白
                print_event("感情", f"💕 {initiator}向{target}表白了...")
                
                # 几乎必成，除非特殊情况
                success_chance = 0.8 + (affection - 70) * 0.02
                if random.random() < success_chance:
                    print_success(f"💍 恭喜！{player.name}和{npc_data['名称']}确定了恋人关系！")
                    npc_data['status'] = "恋人"
                    player.add_event_to_history("表白", f"与 {npc_data['名称']} 成为恋人", "情感里程碑")
                else:
                    print_warning(f"💔 {target}犹豫了...暂时没有答应。")

    @staticmethod
    def process_turn(player, world):
        """每回合处理社交与家庭事件"""
        # 1. 现有关系互动（维持、降温等）
        # TODO: 以后实现，现在主要处理主动事件
        pass

    @staticmethod
    def attempt_intimacy(player, partner_npc):
        """尝试进行亲密行为 (Do iT)"""
        p_data = player.save_data
        rel_id = f"npc_{partner_npc['名称']}" # 简化ID
        rel_data = p_data.get('relationships', {}).get(rel_id, {"affection": 0, "status": "陌生人"})
        
        affection = rel_data.get('affection', 0)
        
        # 门槛判定 (好感度 > 50 且 对方不讨厌你)
        # 如果是 "恋人" 或 "夫妻" 则极高概率同意
        success_prob = 0.0
        
        # 1. 基础概率基于好感度
        if affection >= 80: success_prob = 0.9
        elif affection >= 50: success_prob = 0.3 
        else: success_prob = 0.01 
        
        # 2. 玩家魅力加成 (每10点魅力+5%)
        charm = player.game_stats.get('魅力', 10)
        success_prob += (charm - 10) * 0.005
        
        # 3. 性格/特质修正 (数据驱动)
        traits = player.get_traits()
        
        # 遍历所有特质，累加 "亲密成功率" 加成
        bonus_pct = 0
        for t in traits:
            # 尝试获取 "亲密成功率" (Range: 0-100)
            bonus_pct += player._parse_trait_bonus(t, "亲密成功率")
            
        success_prob += bonus_pct / 100.0
        
        # NPC性格 (如果有)
        npc_personality = partner_npc.get('性格', "")
        if "保守" in npc_personality: success_prob -= 0.3
        elif "开放" in npc_personality or "热情" in npc_personality: success_prob += 0.2
        
        # 特殊：如果是配偶，概率几乎100% (除非刚炒完架? 以后做)
        char_id = p_data.get('current_character_id')
        member = p_data['family_tree']['members'].get(char_id)
        is_spouse = False
        if member and member.get('spouse_id') and partner_npc.get('id') == member.get('spouse_id'):
             is_spouse = True
             success_prob = 0.99

        # 最终判定
        success_prob = max(0.01, min(0.99, success_prob))
        
        if random.random() > success_prob:
            print_info(f"💔 {partner_npc['名称']}({npc_personality}) 拒绝了你的请求。")
            return False, False

        # 成功 DO
        print_event("亲密", f"你与 {partner_npc['名称']} 度过了一个火热的夜晚...")
        
        # 出轨判定
        if member.get('spouse_id') and not is_spouse:
            RelationshipSystem.handle_affair(player, player.save_data, partner_npc)
            
        # 怀孕判定 (加入特质影响)
        is_pregnant = RelationshipSystem.check_pregnancy(player, member, partner_npc, is_spouse)
        return True, is_pregnant


        
    @staticmethod
    def handle_affair(player, p_data, lover):
        """处理出轨逻辑"""
        char_id = p_data.get('current_character_id')
        member = p_data['family_tree']['members'].get(char_id)
        spouse_id = member.get('spouse_id')
        
        # 尝试获取配偶性格 (如果在 family_tree 里没有存，就 Mock 一个)
        # 目前 game_engine.py 里结婚时只存了 id 和 name. 
        # 应该去 fetch 配偶数据，或者默认 "多疑"
        spouse_personality = member.get('spouse_personality', '多疑') # 默认多疑
        
        # 1. 发现概率计算
        risk = 0.3 # 基础
        
        if "多疑" in spouse_personality: risk += 0.3
        elif "迟钝" in spouse_personality or "信任" in spouse_personality: risk -= 0.15
        
        # 玩家属性修正
        luck = player.game_stats.get('幸运', 10)
        risk -= (luck - 10) * 0.02
        
        risk = max(0.05, min(0.95, risk))
        
        if random.random() < risk:
            print_warning(f"⚠️  警告：你的出轨行为被配偶察觉了！(配偶性格: {spouse_personality})")
            
            # 后果判定
            if "宽容" in spouse_personality:
                print_info(f"  {member.get('spouse_name')} 选择原谅了你，但好感度大幅下降。")
            elif "嫉妒" in spouse_personality or "暴躁" in spouse_personality:
                print_error(f"  {member.get('spouse_name')} 勃然大怒！家庭关系破裂！")
                # 触发离婚逻辑? (暂略，需要 GameEngine 支持)
                # 比如: member['status'] = 'divorced'
            else:
                print_warning(f"  你们爆发了激烈的争吵。")
                
    @staticmethod
    def check_pregnancy(player, member, partner, is_spouse):
        """怀孕判定"""
        # 年龄因子
        age = player.save_data.get('age', 18)
        fertility = 0.0
        if 20 <= age <= 35: fertility = 0.25
        elif 35 < age <= 45: fertility = 0.1
        elif 18 <= age < 20: fertility = 0.15
        else: fertility = 0.01
        
        # 特质修正
        traits = player.get_traits()
        if "多产" in traits or "母性" in traits: fertility += 0.15
        if "不孕" in traits: fertility = 0.0
        
        # 如果已经一堆孩子，降低概率
        current_kids = len(member.get('children_ids', []))
        fertility /= (current_kids + 1)
        
        if random.random() < fertility:
            return True
        return False
