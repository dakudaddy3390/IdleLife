# 🎮 Idle Life (挂机人生)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/AI-LLM%20Powered-purple.svg" alt="AI Powered">
</p>

> 一款由 AI 驱动的文字放置挂机游戏，融合了遗传系统、家族传承、动态叙事等深度玩法。

## ✨ 特色功能

- 🤖 **AI 动态叙事** - 使用大语言模型生成沉浸式事件描述和角色对话
- 🧬 **遗传系统** - 角色拥有独特基因组，影响属性和特质
- 👨‍👩‍👧 **家族传承** - 角色死亡后可由后代继承，延续冒险
- 🌍 **多世界观** - 支持奇幻异世界、末日废土等多种设定
- 💕 **关系系统** - 与 NPC 互动、结婚、生子
- ⚔️ **完整 RPG 系统** - 战斗、装备、升级、技能
- 🎨 **精美终端 UI** - 使用 Rich 库打造现代化界面

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install requests rich json5
```

### 2. 配置 API

复制配置模板并填写你的 API 密钥：

```bash
cp config.sample.json5 config.json5
```

编辑 `config.json5`，配置你的 LLM API：

```json5
{
    "api_providers": [
        {
            "name": "DeepSeek Official",
            "api_key": "YOUR_API_KEY_HERE",  // 替换为你的密钥
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat"
        }
    ],
    "active_provider": 0,
    // ...
}
```

### 3. 运行游戏

```bash
python game.py
```

## 🎮 游戏控制

| 按键 | 功能 |
|------|------|
| `F` | 暂停/继续游戏 |
| `Ctrl+C` | 退出游戏 |

## 📁 项目结构

```
神奇的放置自己/
├── 📂 characters/           # 角色配置目录
│   └── chi.json            # 示例角色（技术宅猫娘）
├── 📂 worlds/              # 世界观配置目录
│   ├── eldoria.json        # 艾尔德利亚大陆（剑与魔法）
│   └── wasteland.json      # 末日废土（后启示录）
├── 📂 core/                # 核心模块
│   ├── ai.py               # AI 接口封装
│   ├── config.py           # 配置管理
│   ├── templates.py        # 提示词模板
│   └── utils.py            # 工具函数
├── 📂 models/              # 数据模型
│   ├── character.py        # 角色类
│   └── world.py            # 世界类
├── 📂 systems/             # 游戏系统
│   ├── combat.py           # 战斗系统
│   ├── events.py           # 事件系统
│   ├── genetics.py         # 遗传系统
│   ├── merchant.py         # 商人系统
│   ├── race.py             # 种族系统
│   └── relationships.py    # 关系系统
├── 📂 saves/               # 存档目录（自动生成）
├── config.sample.json5     # 配置模板
├── config.json5            # 用户配置（需自行创建）
├── game.py                 # 游戏入口
├── game_engine.py          # 游戏引擎
└── README.md
```

## ⚙️ 配置说明

### 切换 API 提供商

修改 `config.json5` 中的 `active_provider` 索引：

```json5
"active_provider": 0  // 使用第一个配置的 API
```

### 切换世界观

```json5
"active_world": 0  // 0=异世界奇幻, 1=末日废土
```

### 调整游戏速度

```json5
"game_settings": {
    "game_speed": 1,        // 每回合等待秒数
    "max_tokens": 1024,     // AI 回复最大长度
    "temperature": 1,       // AI 创造性 (0.0-1.0)
    "history_limit": 10,    // 历史记录保留条数
    "autosave_interval": 1  // 自动保存间隔（回合）
}
```

## 🎯 游戏机制

### 🧬 遗传系统

每个角色拥有独特的基因组，决定：
- **六维属性**：力量、敏捷、智力、体质、魅力、幸运
- **特质**：如"好色"、"忠诚"、"魅魔体质"等
- **天赋加成**：攻击、防御、闪避、暴击等

子代会继承并随机组合父母的基因，产生新的属性组合。

### 👨‍👩‍👧 家族传承

- 角色可以结婚、生子
- 角色死亡后，由长子/长女继承
- 继承人获得父母的财产和装备
- 家族树记录所有成员的生平

### ⚔️ 战斗系统

- 回合制自动战斗
- 濒死时有概率奇迹生还
- 击败敌人获得经验和战利品
- 装备系统影响战斗属性

### 🎭 事件类型

| 类型 | 说明 |
|------|------|
| 战斗 | 遭遇怪物，进行战斗 |
| 探索 | 发现宝箱、物品、秘密 |
| 休息 | 恢复 HP/MP |
| NPC | 遇到商人、冒险者、特殊角色 |

### 👴 衰老系统

- 每 50 回合增长 1 岁
- 升级可延长寿命
- 接近寿命上限时属性衰减
- 种族影响基础寿命

## ➕ 扩展指南

### 添加新角色

1. 在 `characters/` 目录创建新的 JSON 文件
2. 参考 `chi.json` 的格式定义角色属性
3. 在 `config.json5` 的 `characters` 数组中注册

```json5
{
    "id": "alice",
    "name": "爱丽丝",
    "file": "characters/alice.json",
    "description": "勇敢的冒险者"
}
```

### 添加新世界观

1. 在 `worlds/` 目录创建新的 JSON 文件
2. 必须包含以下字段：
   - `世界名称` / `世界描述`
   - `地区` (数组)
   - `怪物模板` / `事件模板`
   - `物品列表` / `NPC模板`
3. 在 `config.json5` 的 `worlds` 数组中注册

## 🐛 故障排除

### ModuleNotFoundError

```bash
pip install requests rich pyjson5
```

### API 调用失败

- 检查 `config.json5` 中的 API 密钥是否有效
- 确认网络连接正常
- 尝试切换到其他 `active_provider`

### 中文显示乱码 (Windows)

游戏已内置 Windows 终端编码修复，如仍有问题：
```powershell
chcp 65001
python game.py
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📜 许可证

本项目采用 [MIT 许可证](LICENSE)。

---

**Enjoy your adventure! 🚀**
