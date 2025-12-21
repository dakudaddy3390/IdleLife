# 贡献指南

感谢你对本项目的兴趣！欢迎任何形式的贡献。

## 🐛 报告问题

1. 请先搜索已有的 Issue，避免重复
2. 使用清晰的标题描述问题
3. 提供以下信息：
   - Python 版本
   - 操作系统
   - 错误信息（如有）
   - 复现步骤

## 💡 功能建议

欢迎提出新功能建议！请在 Issue 中描述：
- 功能用途
- 使用场景
- 可能的实现方式（可选）

## 🔧 提交代码

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install requests rich pyjson5
```

### 代码规范

- 使用中文注释
- 函数和类添加 docstring
- 保持代码简洁，遵循 KISS 原则

### 提交 PR

1. Fork 本仓库
2. 创建新分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "feat: 添加某功能"`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 Pull Request

### Commit 规范

使用语义化提交信息：

- `feat:` 新功能
- `fix:` 修复问题
- `docs:` 文档更新
- `refactor:` 代码重构
- `style:` 代码格式调整
- `chore:` 其他杂项

## 📂 项目结构说明

| 目录/文件 | 说明 |
|-----------|------|
| `core/` | 核心模块（配置、AI、工具） |
| `models/` | 数据模型（角色、世界） |
| `systems/` | 游戏系统（战斗、遗传、骰子等） |
| `characters/` | 角色配置文件 |
| `worlds/` | 世界观配置文件 |
| `saves/` | 存档目录（自动生成） |
| `tests/` | 测试目录 |
| `game.py` | 游戏入口 |
| `game_engine.py` | 游戏主循环 |
| `simulation.py` | 模拟运行模块 |

## 🎯 待办功能

欢迎认领以下功能：

- [ ] 多语言支持
- [ ] Web 界面
- [ ] 更多世界观
- [ ] 成就系统扩展
- [ ] 存档云同步

---

再次感谢你的贡献！🎉
