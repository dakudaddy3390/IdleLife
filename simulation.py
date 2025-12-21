
import sys
import os
import time
import random
import traceback

# 添加当前目录到 sys.path
sys.path.append(os.getcwd())

from game_engine import GameEngine
from core.config import Config

def run_simulation():
    print("🚀 开始全流程模拟测试...")
    
    # 1. 初始化游戏
    config = Config()
    engine = GameEngine(config, reset_save=True) # 重置存档以开始新游戏
    player = engine.player
    
    print(f"1️⃣  初始角色: {player.name} (ID: {player.save_data['current_character_id']})")
    print(f"    初始属性: Lv{player.game_stats['等级']} HP={player.game_stats['HP']} 金币={player.game_stats['金币']}")
    
    # 2. 模拟积累财富
    print("\n2️⃣  模拟冒险与积累...")
    player.game_stats['金币'] = 5000
    player.game_stats['等级'] = 10
    sword = {"name": "传家宝大剑", "type": "武器", "stats": {"attack": 50}, "price": 1000, "desc": "测试用神剑"}
    player.inventory.append(sword)
    player.equip_item(sword) # 装备上
    
    print(f"    当前状态: Lv10, 金币=5000, 装备={player.save_data['equipment']['weapon']['name']}")
    
    # 3. 模拟结婚生子 (强制触发)
    print("\n3️⃣  模拟结婚生子...")
    # 强制调整年龄
    player.save_data['age'] = 25
    
    # Mock random to force events
    original_random = random.random
    # Force < 0.01 for marriage
    # Force < prob for birth
    
    # We monkeypatch random to return 0.001
    random.random = lambda: 0.001 
    
    # 触发结婚
    engine.process_life_events() 
    char_id = player.save_data['current_character_id']
    member = player.save_data['family_tree']['members'][char_id]
    
    if member.get('spouse_id'):
        print("    ✅ 结婚成功！")
    else:
        print("    ❌ 结婚失败")
        
    # 触发生子
    # process_life_events logic: if spouse_id... birth check.
    # We call it again.
    engine.process_life_events()
    children = player.get_children()
    if children:
        child_name = children[0][1]['name']
        print(f"    ✅ 生子成功！孩子: {child_name}")
    else:
        print("    ❌ 生子失败")
        
    # 恢复 random
    random.random = original_random
    
    # 4. 模拟老去与死亡
    print("\n4️⃣  模拟岁月流逝与死亡...")
    player.save_data['age'] = 100
    player.save_data['max_age'] = 60
    
    print("    💀 触发死亡...")
    inheritance_success = engine.handle_death("模拟寿命耗尽", "老死")
    
    if inheritance_success:
        print("\n5️⃣  继承成功！")
        new_player = engine.player
        print(f"    新角色: {new_player.name}")
        
        # 验证
        gold = new_player.game_stats['金币']
        if gold == 5000:
            print("    ✅ 金币继承正确")
        else:
            print(f"    ❌ 金币继承错误: {gold}")
            
        with open("sim_result.txt", "w") as f:
            f.write("SUCCESS")
    else:
        print("\n❌ 继承失败 (游戏结束)")

if __name__ == "__main__":
    try:
        run_simulation()
    except Exception as e:
        traceback.print_exc()
        with open("error.log", "w") as f:
            f.write(traceback.format_exc())
