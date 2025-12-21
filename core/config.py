import json5
import sys
import os
from core.utils import print_error, print_warning, print_info

class Config:
    def __init__(self):
        try:
            # 优先尝试加载 config.json5 (支持注释)
            config_file = 'config.json5'
            if not os.path.exists(config_file):
                # 回退兼容 config.json
                config_file = 'config.json'
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self.data = json5.load(f)
                
            # 支持多API配置
            providers = self.data.get('api_providers', [])
            active_idx = self.data.get('active_provider', 0)
            
            if not providers:
                print_error(f"❌ {config_file} 中没有找到api_providers配置！")
                sys.exit(1)
            
            if active_idx >= len(providers):
                print_warning(f"⚠️  active_provider索引{active_idx}超出范围，使用第一个API")
                active_idx = 0
            
            self.provider = providers[active_idx]
            self.settings = self.data.get('game_settings', {})
            
            # 角色和世界观配置
            self.characters = self.data.get('characters', [])
            self.active_char_idx = self.data.get('active_character', 0)
            self.worlds = self.data.get('worlds', [])
            self.active_world_idx = self.data.get('active_world', 0)
            
            print_info(f"🎮 使用配置: {config_file}")
            print_info(f"🎮 使用API: {self.provider.get('name', '未命名')}")
            
        except Exception as e:
            print_error(f"加载配置文件失败: {e}")
            # 打印更详细的错误堆栈以便排查
            import traceback
            traceback.print_exc()
            sys.exit(1)
            
    @property
    def api_key(self): return self.provider.get('api_key')
    @property
    def provider_name(self): return self.provider.get('name', 'Unknown')
    @property
    def base_url(self): return self.provider.get('base_url')
    @property
    def model(self): return self.provider.get('model')
    @property
    def speed(self): return self.settings.get('game_speed', 10)
    @property
    def max_tokens(self): return self.settings.get('max_tokens', 500)
    @property
    def temperature(self): return self.settings.get('temperature', 0.8)
    @property
    def history_limit(self): return self.settings.get('history_limit', 100)
    @property
    def autosave_interval(self): return self.settings.get('autosave_interval', 1)
    @property
    def ui_refresh_rate(self): return self.settings.get('ui_refresh_rate', 0.1)
    @property
    def api_retry_count(self): return self.settings.get('api_retry_count', 3)
    @property
    def api_retry_delay(self): return self.settings.get('api_retry_delay', 2)
    @property
    def ai_event_rate(self):
        """AI生成动态事件的概率"""
        return self.settings.get('ai_event_rate', 0.7)
        
    @property
    def history_compress_threshold(self): return self.settings.get('history_compress_threshold', 20)
    @property
    def history_retention_count(self): return self.settings.get('history_retention_count', 10)
    @property
    def streaming(self): return self.settings.get('streaming', False)
    
    def toggle_streaming(self):
        """切换流式传输开关"""
        current = self.settings.get('streaming', False)
        self.settings['streaming'] = not current
        return self.settings['streaming']
    
    def get_character_file(self):
        if self.characters and self.active_char_idx < len(self.characters):
            char = self.characters[self.active_char_idx]
            print_info(f"👤 角色: {char.get('name', '未知')}")
            return char.get('file', 'characters/chi.json')
        return 'characters/chi.json'
    
    def get_world_file(self):
        if self.worlds and self.active_world_idx < len(self.worlds):
            world = self.worlds[self.active_world_idx]
            print_info(f"🌍 世界: {world.get('name', '未知')}")
            return world.get('file', 'worlds/eldoria.json')
        return 'worlds/eldoria.json'
    
    @property
    def api_providers(self):
        """获取所有可用的 API 渠道列表"""
        return self.data.get('api_providers', [])
    
    @property
    def active_provider_idx(self):
        """获取当前激活的 API 渠道索引"""
        return self.data.get('active_provider', 0)
    
    def set_active_provider(self, idx):
        """切换当前激活的 API 渠道"""
        providers = self.api_providers
        if 0 <= idx < len(providers):
            self.data['active_provider'] = idx
            self.provider = providers[idx]
            print_info(f"🔄 已切换到 API 渠道: {self.provider.get('name', '未命名')}")
            return True
        return False

