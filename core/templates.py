
"""
Master Templates and Schemas for AI Generation.
Use these in system prompts to ensure structured output.
"""

TRAIT_TEMPLATE = """
{
    "name": "Trait Name",
    "desc": "Fluff description",
    "modifiers": {
        "param_name": value
    }
}
Supported Modifiers:
- '攻击', '防御', 'MaxHP', 'MaxMP', '闪避', '暴击' (Combat Stats)
- '亲密成功率', '好感度获取' (Social Stats)
- '诱惑_欲望', '诱惑_抵抗' (Affair Logic)
- '经验获取', '恢复效率' (Growth Stats)
"""

SKILL_TEMPLATE = """
{
    "name": "Skill Name",
    "type": "physical/magic/heal/buff", 
    "cost": mp_cost_int,
    "power": damage_multiplier_float,
    "desc": "Description",
    "effect": "optional_tag"
}
Effect Tags:
- 'multi_hit_2': Hits twice
- 'drain': Heals 50% of damage dealt
- 'crit_buff': Next attack critical
- 'stun': Stuns enemy (if implemented)
"""

EVENT_TEMPLATE = """
{
    "title": "Event Title",
    "description": "Narrative description",
    "choices": [
        {
            "text": "Action description",
            "effect": "type_code",
            "value": number
        }
    ]
}
Effect Types:
- 'gold', 'exp', 'hp', 'mp'
- 'item': value is item_dict
- 'trait': value is trait_dict (see Trait Template)
- 'skill': value is skill_dict (see Skill Template)
"""

SYSTEM_PROMPT_SUFFIX = f"""
[DATA SCHEMA ENFORCEMENT]
When generating game content, you MUST strictly adhere to these JSON structures.
Traits:
{TRAIT_TEMPLATE}

Skills:
{SKILL_TEMPLATE}

Events:
{EVENT_TEMPLATE}
"""
