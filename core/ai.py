import requests
import json
import time
from core.utils import print_warning, print_error, console

class AIBrain:
    def __init__(self, config):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }

    def think_and_act(self, prompt):
        """返回 (内容, token统计) 或 (None, None)"""
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        max_retries = self.config.api_retry_count
        retry_delay = self.config.api_retry_delay
        
        for attempt in range(max_retries):
            try:
                with console.status(f"[bold green]🧠 AI ({self.config.provider_name}) 正在思考... (尝试 {attempt+1}/{max_retries})[/bold green]", spinner="clock", refresh_per_second=2):
                    response = requests.post(
                        f"{self.config.base_url}/chat/completions", 
                        headers=self.headers, 
                        json=payload, 
                        timeout=60
                    )
                
                # 如果是4xx错误(如Key无效)，通常重试没用，但为了满足要求还是走统一逻辑
                # 不过 raise_for_status 会抛出 HTTPError
                response.raise_for_status()
                data = response.json()
                
                # 安全检查 API 响应
                if 'choices' not in data or not data['choices']:
                    # 尝试解析不同厂商的错误格式
                    error_msg = '未知API错误'
                    if isinstance(data.get('error'), dict):
                        error_msg = data['error'].get('message', str(data['error']))
                    elif isinstance(data.get('error'), str):
                        error_msg = data['error']
                    elif 'msg' in data:
                        error_msg = data['msg']
                    elif 'message' in data:
                        error_msg = data['message']
                    
                    print_error(f"🧠 API响应异常: {error_msg}")
                    print_warning(f"🔍 调试信息: {json.dumps(data, ensure_ascii=False)}")
                    
                    if attempt < max_retries - 1:
                        print_warning(f"⏳ {retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        console.input("[bold yellow]⏸️ 发生API错误(重试用尽)，按回车键继续...[/bold yellow]")
                        return None, None
                    
                content = data['choices'][0]['message']['content']
                usage = data.get('usage', {})
                return content, usage
                
            except Exception as e:
                # 包含 Timeout, ConnectionError, HTTPError (raise_for_status) 等
                print_error(f"🧠 AI思考出错: {e}")
                
                if attempt < max_retries - 1:
                    print_warning(f"⏳ {retry_delay}秒后重试 ({attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                else:
                    console.input("[bold yellow]⏸️ 连接失败(重试用尽)，按回车键继续...[/bold yellow]")
                    return None, None
        
        return None, None
