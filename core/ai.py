import requests
import json
import time
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
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
        if self.config.streaming:
            return self._streaming_request(prompt)
        else:
            return self._normal_request(prompt)
    
    def _normal_request(self, prompt):
        """普通请求（非流式）"""
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False
        }
        
        max_retries = self.config.api_retry_count
        retry_delay = self.config.api_retry_delay
        
        for attempt in range(max_retries):
            try:
                with console.status(f"[bold green]🧠 AI ({self.config.provider_name}) 思考中...[/bold green]", spinner="dots", refresh_per_second=8):
                    response = requests.post(
                        f"{self.config.base_url}/chat/completions", 
                        headers=self.headers, 
                        json=payload, 
                        timeout=60
                    )
                
                response.raise_for_status()
                data = response.json()
                
                if 'choices' not in data or not data['choices']:
                    error_msg = self._parse_error(data)
                    print_error(f"🧠 API响应异常: {error_msg}")
                    
                    if attempt < max_retries - 1:
                        print_warning(f"⏳ {retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        console.input("[bold yellow]⏸️ API错误，按回车继续...[/bold yellow]")
                        return None, None
                    
                content = data['choices'][0]['message']['content']
                usage = data.get('usage', {})
                return content, usage
                
            except Exception as e:
                print_error(f"🧠 AI思考出错: {e}")
                
                if attempt < max_retries - 1:
                    print_warning(f"⏳ {retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                else:
                    console.input("[bold yellow]⏸️ 连接失败，按回车继续...[/bold yellow]")
                    return None, None
        
        return None, None
    
    def _streaming_request(self, prompt):
        """流式请求 - 使用 Rich Live 实现美观的实时输出"""
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True
        }
        
        max_retries = self.config.api_retry_count
        retry_delay = self.config.api_retry_delay
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.config.base_url}/chat/completions", 
                    headers=self.headers, 
                    json=payload, 
                    timeout=120,
                    stream=True
                )
                
                response.raise_for_status()
                
                full_content = ""
                usage = {}
                
                # 使用 Rich Live 实现美观的实时更新
                with Live(
                    Panel("[dim]等待AI响应...[/dim]", title=f"🧠 {self.config.provider_name}", border_style="cyan", padding=(0, 1)),
                    console=console,
                    refresh_per_second=15,
                    transient=True  # 完成后替换
                ) as live:
                    for line in response.iter_lines():
                        if line:
                            line_text = line.decode('utf-8')
                            if line_text.startswith('data: '):
                                data_str = line_text[6:]
                                
                                if data_str.strip() == '[DONE]':
                                    break
                                
                                try:
                                    chunk = json.loads(data_str)
                                    
                                    if 'choices' in chunk and chunk['choices']:
                                        delta = chunk['choices'][0].get('delta', {})
                                        content_piece = delta.get('content', '')
                                        if content_piece:
                                            full_content += content_piece
                                            # 实时更新 Panel 内容
                                            display_text = Text(full_content)
                                            live.update(
                                                Panel(
                                                    display_text,
                                                    title=f"🧠 {self.config.provider_name}",
                                                    subtitle="[dim]流式输出中...[/dim]",
                                                    border_style="cyan",
                                                    padding=(0, 1)
                                                )
                                            )
                                    
                                    if 'usage' in chunk:
                                        usage = chunk['usage']
                                        
                                except json.JSONDecodeError:
                                    pass
                
                # 输出完成后显示最终结果（非 transient）
                if full_content:
                    console.print(Panel(
                        Text(full_content, style="white"),
                        title=f"🧠 {self.config.provider_name}",
                        subtitle="[green]✓ 完成[/green]",
                        border_style="green",
                        padding=(0, 1)
                    ))
                    return full_content, usage
                else:
                    print_error("🧠 流式响应为空")
                    if attempt < max_retries - 1:
                        print_warning(f"⏳ {retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                        continue
                    return None, None
                
            except Exception as e:
                print_error(f"🧠 流式请求出错: {e}")
                
                if attempt < max_retries - 1:
                    print_warning(f"⏳ {retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                else:
                    console.input("[bold yellow]⏸️ 流式连接失败，按回车继续...[/bold yellow]")
                    return None, None
        
        return None, None
    
    def _parse_error(self, data):
        """解析 API 错误信息"""
        if isinstance(data.get('error'), dict):
            return data['error'].get('message', str(data['error']))
        elif isinstance(data.get('error'), str):
            return data['error']
        elif 'msg' in data:
            return data['msg']
        elif 'message' in data:
            return data['message']
        return '未知API错误'


