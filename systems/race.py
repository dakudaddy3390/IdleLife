class RaceSystem:
    """种族系统：定义寿命和衰老特性"""
    TURNS_PER_YEAR = 50  # 50回合=1年
    
    RACES = {
        # 基础奇幻
        "人类": {"base_lifespan": 80, "aging_threshold": 0.8, "level_bonus": 2},
        "精灵": {"base_lifespan": 300, "aging_threshold": 0.9, "level_bonus": 5},
        "矮人": {"base_lifespan": 150, "aging_threshold": 0.85, "level_bonus": 3},
        "兽人": {"base_lifespan": 60, "aging_threshold": 0.7, "level_bonus": 1.5},
        "半精灵": {"base_lifespan": 150, "aging_threshold": 0.85, "level_bonus": 3},
        
        # 黑暗/怪物
        "吸血鬼": {"base_lifespan": 1000, "aging_threshold": 0.99, "level_bonus": 10},
        "魔族": {"base_lifespan": 500, "aging_threshold": 0.9, "level_bonus": 5},
        
        # 赛博朋克
        "改造人": {"base_lifespan": 100, "aging_threshold": 0.9, "level_bonus": 1}, # 义体老化慢
        "仿生人": {"base_lifespan": 200, "aging_threshold": 0.95, "level_bonus": 0}, # 几乎不老化，但难升级
        
        # 东方玄幻
        "仙族": {"base_lifespan": 500, "aging_threshold": 0.95, "level_bonus": 10},
        "妖族": {"base_lifespan": 300, "aging_threshold": 0.9, "level_bonus": 5},
        "灵族": {"base_lifespan": 999, "aging_threshold": 0.99, "level_bonus": 2}
    }
    
    @staticmethod
    def infer_race(profile_data, genome_desc=""):
        """根据简介和基因推断种族"""
        # 1. 优先读取显式定义的种族
        if isinstance(profile_data, dict):
            explicit_race = profile_data.get('基本信息', {}).get('种族')
            if not explicit_race:
                explicit_race = profile_data.get('种族')
            
            if explicit_race:
                # 简单的映射或直接返回
                for r in RaceSystem.RACES:
                    if r in explicit_race:
                        return r

        # 2. 关键词推断
        # 只在描述性文本中查找，避免匹配到示例对话中的关键词(如"摸摸小猫娘")
        search_text = ""
        
        if isinstance(profile_data, dict):
            # 拼接主要描述字段
            search_text += str(profile_data.get('角色描述', ''))
            search_text += str(profile_data.get('基本信息', {}))
            # 自我认知通常包含种族认同
            search_text += str(profile_data.get('心理特征', {}).get('自我认知', {})) 
            
            # 如果没提取到多少文本(可能是旧格式)，则回退到整体转字符串，但尽量避开示例
            if len(search_text) < 10:
                 search_text = str(profile_data)
        else:
            search_text = str(profile_data)
            
        desc = search_text.lower()
        if "机械" in desc or "义体" in desc or "改造" in desc:
            return "改造人"
        if "仿生人" in desc or "机器人" in desc or "android" in desc:
            return "仿生人"
        if "吸血鬼" in desc or "血族" in desc or "vampire" in desc:
            return "吸血鬼"
        if "修仙" in desc or "仙人" in desc:
            return "仙族"
        if "妖怪" in desc or "妖精" in desc and "东方" in desc: # 区分西式妖精(Fairy/Elf)
            return "妖族"
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
