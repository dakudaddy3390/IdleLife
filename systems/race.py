class RaceSystem:
    """种族系统：定义寿命和衰老特性"""
    TURNS_PER_YEAR = 50  # 50回合=1年
    
    RACES = {
        "人类": {"base_lifespan": 80, "aging_threshold": 0.8, "level_bonus": 2},
        "精灵": {"base_lifespan": 300, "aging_threshold": 0.9, "level_bonus": 5},
        "矮人": {"base_lifespan": 150, "aging_threshold": 0.85, "level_bonus": 3},
        "兽人": {"base_lifespan": 60, "aging_threshold": 0.7, "level_bonus": 1.5},
        "半精灵": {"base_lifespan": 150, "aging_threshold": 0.85, "level_bonus": 3}
    }
    
    @staticmethod
    def infer_race(profile_data, genome_desc=""):
        """根据简介和基因推断种族"""
        desc = str(profile_data).lower()
        if "猫娘" in desc or "兽耳" in desc or "尾巴" in desc:
            return "兽人"
        if "精灵" in desc:
            return "精灵"
        if "矮人" in desc:
            return "矮人"
        return "人类"  # 默认

    @staticmethod
    def calculate_max_age(race, level, custom_races=None):
        """计算最大寿命"""
        races = custom_races if custom_races else RaceSystem.RACES
        data = races.get(race, races.get("人类", {"base_lifespan":80, "level_bonus":2}))
        return int(data.get("base_lifespan", 80) + level * data.get("level_bonus", 2))

    @staticmethod
    def check_aging_debuff(race, current_age, max_age, custom_races=None):
        """检查衰老惩罚"""
        races = custom_races if custom_races else RaceSystem.RACES
        data = races.get(race, races.get("人类", {"aging_threshold": 0.8}))
        threshold = data.get("aging_threshold", 0.8)
        
        if current_age >= max_age * threshold:
            # 超过阈值，属性衰减
            # 衰减比例：超过部分的百分比 * 2 (例如超10% -> 减20%属性)
            over_ratio = (current_age / max_age - threshold) / (1 - threshold)
            debuff_pct = min(0.5, over_ratio * 0.5)  # 最多衰减50%
            return debuff_pct
        return 0.0
