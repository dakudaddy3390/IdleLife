import json
import time
import os
import sys
import glob
from rich.console import Console
from rich.table import Table
from rich import box

# 修复Windows下可能出现的中文乱码 - 使用更稳健的方法
if sys.platform == 'win32':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11) # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        mode.value |= 4  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(handle, mode)
        # 设置控制台输出代码页为UTF-8 (65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

# 强制重配置这些流为utf-8
sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys, 'stderr'):
    sys.stderr.reconfigure(encoding='utf-8')

# ================= 模块导入 =================
from core.config import Config
from core.utils import console, print_header, print_info, print_warning, print_error
from game_engine import GameEngine

# ================= 菜单逻辑 =================

def show_save_menu():
    """显示存档选择菜单"""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print("\n[bold cyan]=========== [游戏] 神奇的放置自己 V2.1 (Refactored) ===========[/bold cyan]\n")
    
    # 扫描现有存档
    # 优先扫描 saves/ 目录下的新存档
    saves = []
    
    # 1. 扫描 saves/ 目录
    if os.path.exists('saves'):
        saves_in_dir = glob.glob(os.path.join('saves', 'save_*.json'))
        saves.extend(saves_in_dir)
        
    # 2. 扫描根目录下的旧存档 (为了兼容)
    root_saves = glob.glob('save_*.json')
    saves.extend(root_saves)
    
    # 去重
    saves = list(set(saves))
    # 按修改时间倒序排序 (确保最新的在最前)
    saves.sort(key=os.path.getmtime, reverse=True)

    if saves:
        table = Table(title="[存档列表]", box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("序号", style="green", justify="right")
        table.add_column("存档文件", style="dim")
        table.add_column("角色", style="bold white")
        table.add_column("种族", style="yellow")
        table.add_column("状态", style="yellow")
        table.add_column("等级", style="magenta")
        table.add_column("家族信息", style="blue")

        for i, save in enumerate(saves, 1):
            try:
                with open(save, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 兼容不同层级的数据结构
                char_name = "未知"
                char_id = data.get('current_character_id')
                if char_id and 'family_tree' in data:
                    member = data['family_tree']['members'].get(char_id)
                    if member:
                        char_name = member.get('name', '未知')
                
                level = data.get('base_stats', {}).get('等级', 1)
                gene_score = data.get('player_gene_score', '?')
                
                generation = 1
                if char_id and 'family_tree' in data:
                    member = data['family_tree']['members'].get(char_id)
                    if member:
                        generation = member.get('generation', 1)
                
                race = data.get('race', '未知')
                age = data.get('age', 18)
                max_age = data.get('max_age', 80)
                
                table.add_row(
                    str(i), 
                    os.path.basename(save), # 只显示文件名
                    char_name, 
                    str(race),
                    f"{age}/{max_age}岁", 
                    f"Lv.{level}", 
                    f"第{generation}代 (基因{gene_score})"
                )
            except:
                table.add_row(str(i), save, "[读取错误]", "", "", "", "")
        
        console.print(table)
        console.print()
    
    console.print(f"  [yellow]0.[/yellow] [新建] 新建存档")
    console.print(f"  [cyan]S.[/cyan] [设置] 切换 API 渠道")
    console.print(f"  [red]Q.[/red] [退出] 退出游戏\n")
    
    return saves

def select_from_list(items, prompt, name_key=None):
    """通用列表选择"""
    console.print(f"\n[bold cyan]{prompt}[/bold cyan]")
    for i, item in enumerate(items, 1):
        if name_key:
            display = item.get(name_key, str(item))
        else:
            display = str(item)
        console.print(f"  [green]{i}.[/green] {display}")
    
    while True:
        try:
            choice = console.input("\n请选择 (输入数字, 0/Q返回): ").strip().lower()
            if choice in ['0', 'q']:
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return idx
        except:
            pass
        console.print("[red]无效选择，请重试[/red]")

def create_new_save(config):
    """创建新存档：选择角色和世界观"""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print("\n[bold cyan]=========== [新建] 新建存档 ===========[/bold cyan]\n")
    
    # 选择角色
    if config.characters:
        console.print("[bold yellow][角色] 选择角色:[/bold yellow]")
        char_idx = select_from_list(config.characters, "", name_key='name')
        if char_idx is None: return False
        config.active_char_idx = char_idx
    
    # 选择世界观
    if config.worlds:
        console.print("\n[bold yellow][世界] 选择世界观:[/bold yellow]")
        world_idx = select_from_list(config.worlds, "", name_key='name')
        if world_idx is None: return False
        config.active_world_idx = world_idx
    
    console.print(f"\n[green]✅ 已选择: {config.characters[config.active_char_idx]['name']} "
                 f"@ {config.worlds[config.active_world_idx]['name']}[/green]")
    time.sleep(1)
    
    return True

def show_settings_menu(config):
    """显示设置菜单：选择 API 渠道和配置选项"""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print("\n[bold cyan]=========== [设置] API 渠道选择 ===========[/bold cyan]\n")
        
        providers = config.api_providers
        current_idx = config.active_provider_idx
        
        if not providers:
            console.print("[red]❗ 没有配置任何 API 渠道，请检查 config.json5[/red]")
            console.input("\n按回车返回...")
            return
        
        # 显示渠道列表
        table = Table(title="[可用渠道]", box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("序号", style="green", justify="right", width=4)
        table.add_column("状态", style="yellow", width=6)
        table.add_column("渠道名称", style="bold white")
        table.add_column("模型", style="dim")
        table.add_column("Base URL", style="dim", max_width=40)
        
        for i, p in enumerate(providers):
            status = "[✔ 当前]" if i == current_idx else ""
            name = p.get('name', '未命名')
            model = p.get('model', '-')
            base_url = p.get('base_url', '-')
            # 截断过长的 URL
            if len(base_url) > 35:
                base_url = base_url[:32] + "..."
            
            row_style = "bold green" if i == current_idx else None
            table.add_row(str(i + 1), status, name, model, base_url, style=row_style)
        
        console.print(table)
        console.print(f"\n  [dim]当前使用: {config.provider_name}[/dim]")
        
        # 显示流式传输状态
        streaming_status = "[green]开启[/green]" if config.streaming else "[red]关闭[/red]"
        console.print(f"\n  [cyan]T.[/cyan] 流式传输: {streaming_status}")
        console.print(f"  [red]0.[/red] 返回主菜单\n")
        
        choice = console.input("请选择 (数字选渠道 / T切换流式): ").strip().lower()
        
        if choice in ['0', 'q', '']:
            return
        
        if choice == 't':
            new_state = config.toggle_streaming()
            status_text = "开启" if new_state else "关闭"
            console.print(f"[green]✅ 流式传输已{status_text}[/green]")
            time.sleep(0.8)
            continue
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(providers):
                if idx == current_idx:
                    console.print(f"[yellow]‼️ 已经是当前渠道[/yellow]")
                else:
                    config.set_active_provider(idx)
                    console.print(f"[green]✅ 已切换到: {providers[idx].get('name', '未命名')}[/green]")
                time.sleep(1)
            else:
                console.print("[red]无效选择[/red]")
                time.sleep(0.5)
        except ValueError:
            console.print("[red]请输入有效的数字[/red]")
            time.sleep(0.5)


def main():
    """主入口"""
    try:
        config = Config()
    except Exception as e:
        print_error(f"初始化配置失败: {e}")
        return

    while True:
        saves = show_save_menu()
        
        prompt = "请选择 (输入数字·0新建·Q退出): "
        if saves:
            prompt = "请选择 (回车继续·数字加载·0新建·Q退出): "
            
        choice = console.input(prompt).strip().lower()
        
        if choice == '':
            if saves:
                choice = '1' # 默认加载第一个(最新)
            else:
                choice = '0' # 无存档则新建
        
        if choice == 'q':
            console.print("\n[yellow]👋 再见！[/yellow]\n")
            return
        
        if choice == 's':
            show_settings_menu(config)
            continue
        
        try:
            idx = int(choice)
            
            if idx == 0:
                # 新建存档
                if create_new_save(config):
                    # 启动游戏引擎
                    try:
                        game = GameEngine(config, reset_save=True)
                        game.main_loop() # 进入游戏循环
                    except Exception as e:
                        print_error(f"游戏运行时发生错误: {e}")
                        import traceback
                        traceback.print_exc()
                        console.input("按回车键返回菜单...")
            
            elif 1 <= idx <= len(saves):
                # 加载现有存档
                save_file = saves[idx - 1]
                
                # 尝试推断角色ID以更新Config (虽然GameEngine本身主要靠save_file加载)
                # ...这里逻辑其实GameEngine内部已经自洽，Config主要用于APIKey等全局配置
                
                try:
                    game = GameEngine(config, save_file=save_file)
                    game.main_loop()
                except Exception as e:
                    print_error(f"游戏运行时发生错误: {e}")
                    import traceback
                    traceback.print_exc()
                    console.input("按回车键返回菜单...")
            else:
                console.print("[red]无效选择[/red]")
        except ValueError:
            console.print("[red]请输入有效的数字[/red]")

if __name__ == "__main__":
    main()
