import random

class GeneticSystem:
    """
    模拟真实世界的基因遗传系统
    - 6个基因位点：力量(STR)、敏捷(AGI)、智力(INT)、魅力(CHA)、体质(CON)、幸运(LUK)
    - 每个位点有两个等位基因（来自父母）
    - 大写=显性(+3)，小写=隐性(+1)，表型由显性决定
    - 支持基因重组（交叉互换）和突变
    """
    
    GENE_LOCI = ['STR', 'AGI', 'INT', 'CHA', 'CON', 'LUK']
    GENE_NAMES = {
        'STR': '力量', 'AGI': '敏捷', 'INT': '智力',
        'CHA': '魅力', 'CON': '体质', 'LUK': '幸运'
    }
    
    TRAITS = {
        "天生神力": {"req": {"STR": "AA"}, "modifiers": {"攻击": 5}, "desc": "STR显性纯合子"},
        "风之子": {"req": {"AGI": "AA"}, "modifiers": {"闪避": 5}, "desc": "AGI显性纯合子"}, # 5 represents 5%
        "过目不忘": {"req": {"INT": "AA"}, "modifiers": {"经验获取": 10}, "desc": "INT显性纯合子"},
        "倾国倾城": {"req": {"CHA": "AA"}, "modifiers": {"好感度获取": 20}, "desc": "CHA显性纯合子"},
        "钢铁之躯": {"req": {"CON": "AA"}, "modifiers": {"防御": 3}, "desc": "CON显性纯合子"},
        "天选之人": {"req": {"LUK": "AA"}, "modifiers": {"暴击": 5}, "desc": "LUK显性纯合子"},
        "血友病": {"req": {"CON": "aa"}, "modifiers": {"恢复效率": -50}, "desc": "CON隐性纯合子"},
        "迟钝": {"req": {"AGI": "aa"}, "modifiers": {"闪避": -5}, "desc": "AGI隐性纯合子"},
        
        # 社交/性格特质 (Relationship System Compatible)
        "魅力四射": {"req": {"CHA": "AA"}, "modifiers": {"亲密成功率": 20}, "desc": "CHA显性纯合子"},
        "好色": {"req": {"INT": "aa", "CON": "A"}, "modifiers": {"亲密成功率": 10, "诱惑_欲望": 30}, "desc": "低智力+高体质"},
        "忠诚": {"req": {"LUK": "A", "INT": "A"}, "modifiers": {"诱惑_抵抗": 40}, "desc": "高幸运+高智力"},
        "禁欲": {"req": {"CON": "aa", "INT": "AA"}, "modifiers": {"诱惑_抵抗": 50}, "desc": "低体质+高智力"},
        "热情": {"req": {"CHA": "A", "AGI": "A"}, "modifiers": {"亲密成功率": 10, "诱惑_欲望": 10}, "desc": "高魅力+高敏捷"},
        "保守": {"req": {"INT": "A", "CHA": "aa"}, "modifiers": {"亲密成功率": -20, "诱惑_抵抗": 30}, "desc": "高智力+低魅力"},
        "魅魔体质": {"req": {"CHA": "AA", "CON": "AA"}, "modifiers": {"亲密成功率": 100, "诱惑_欲望": 50}, "desc": "突变:魅力+体质双显性纯合"},
    }

    @staticmethod
    def is_match(genome, locus, req_type):
        """检查基因位点是否符合要求"""
        alleles = genome.get(locus, 'Aa')
        if req_type == "AA": # 显性纯合
            return alleles[0].isupper() and alleles[1].isupper()
        elif req_type == "aa": # 隐性纯合
            return alleles[0].islower() and alleles[1].islower()
        elif req_type == "A": # 显性（只要有一个大写）
            return alleles[0].isupper() or alleles[1].isupper()
        return False

    @staticmethod
    def get_traits(genome, custom_traits=None):
        """获取基因特质列表，支持自定义特质"""
        traits = []
        source = custom_traits if custom_traits else GeneticSystem.TRAITS
        
        for name, data in source.items():
            reqs = data.get('req', {})
            match = True
            for locus, req_type in reqs.items():
                if not GeneticSystem.is_match(genome, locus, req_type):
                    match = False
                    break
            if match:
                traits.append(name)
        return traits
    
    @staticmethod
    def generate_random_genome():
        """生成随机基因组（初始角色用）"""
        genome = {}
        for locus in GeneticSystem.GENE_LOCI:
            # 每个位点两个等位基因，各有50%几率是显性(大写)或隐性(小写)
            allele1 = locus[0].upper() if random.random() > 0.5 else locus[0].lower()
            allele2 = locus[0].upper() if random.random() > 0.5 else locus[0].lower()
            genome[locus] = allele1 + allele2
        return genome
    
    @staticmethod
    def generate_npc_genome(strength_bias=0):
        """生成NPC基因组，战斗遇见的有力量偏向"""
        genome = {}
        for locus in GeneticSystem.GENE_LOCI:
            # 战斗型NPC在STR/CON上有更高概率是显性
            if locus in ['STR', 'CON'] and strength_bias > 0:
                prob = 0.5 + strength_bias * 0.2  # 战斗型最高0.9
            elif locus in ['CHA', 'INT'] and strength_bias < 0:
                prob = 0.5 + abs(strength_bias) * 0.2  # 社交型
            else:
                prob = 0.5
            
            allele1 = locus[0].upper() if random.random() < prob else locus[0].lower()
            allele2 = locus[0].upper() if random.random() < prob else locus[0].lower()
            genome[locus] = allele1 + allele2
        return genome
    
    @staticmethod
    def crossover(parent1_genome, parent2_genome):
        """基因重组：模拟减数分裂时的交叉互换"""
        child_genome = {}
        
        for locus in GeneticSystem.GENE_LOCI:
            p1_alleles = parent1_genome.get(locus, 'Aa')
            p2_alleles = parent2_genome.get(locus, 'Aa')
            
            # 各取一个等位基因（随机选择）
            child_allele1 = random.choice(list(p1_alleles))
            child_allele2 = random.choice(list(p2_alleles))
            
            child_genome[locus] = child_allele1 + child_allele2
        
        return child_genome
    
    @staticmethod
    def mutate(genome, mutation_rate=0.05):
        """基因突变"""
        mutated = genome.copy()
        mutations = []
        
        for locus in GeneticSystem.GENE_LOCI:
            alleles = list(mutated[locus])
            for i in range(2):
                if random.random() < mutation_rate:
                    # 突变：翻转显隐性
                    old = alleles[i]
                    alleles[i] = alleles[i].swapcase()
                    mutations.append(f"{GeneticSystem.GENE_NAMES[locus]}: {old}→{alleles[i]}")
            mutated[locus] = ''.join(alleles)
        
        return mutated, mutations
    
    @staticmethod
    def express_phenotype(genome):
        """基因表型表达：计算实际属性加成"""
        phenotype = {}
        for locus in GeneticSystem.GENE_LOCI:
            alleles = genome.get(locus, 'aa')
            # 显性(大写)=+3，隐性(小写)=+1
            value = 0
            for a in alleles:
                value += 3 if a.isupper() else 1
            phenotype[locus] = value  # 范围: 2(aa) ~ 6(AA)
        return phenotype
    
    @staticmethod
    def calculate_gene_score(genome):
        """计算总基因分（用于评估基因优劣）"""
        phenotype = GeneticSystem.express_phenotype(genome)
        return sum(phenotype.values())  # 范围: 12 ~ 36
    
    @staticmethod
    def genome_to_stats_bonus(genome):
        """将基因组转换为游戏属性加成"""
        phenotype = GeneticSystem.express_phenotype(genome)
        return {
            '攻击': phenotype['STR'] - 2,      # 0~4
            '防御': phenotype['CON'] - 2,      # 0~4
            'MaxHP': (phenotype['CON'] - 2) * 10,  # 0~40
            'MaxMP': (phenotype['INT'] - 2) * 5,   # 0~20
            '幸运': phenotype['LUK'] - 2,      # 0~4
            '魅力': phenotype['CHA'] - 2       # 用于社交
        }
    
    @staticmethod
    def describe_genome(genome):
        """人类可读的基因描述"""
        phenotype = GeneticSystem.express_phenotype(genome)
        score = GeneticSystem.calculate_gene_score(genome)
        
        # 找出优势和劣势
        sorted_traits = sorted(phenotype.items(), key=lambda x: x[1], reverse=True)
        strengths = [GeneticSystem.GENE_NAMES[k] for k, v in sorted_traits[:2] if v >= 5]
        weaknesses = [GeneticSystem.GENE_NAMES[k] for k, v in sorted_traits[-2:] if v <= 3]
        
        desc = f"基因分:{score}"
        if strengths:
            desc += f" 优势:{'/'.join(strengths)}"
        if weaknesses:
            desc += f" 劣势:{'/'.join(weaknesses)}"
        return desc
