# MaiBot TRPG DM 跑团插件

将 MaiBot 变成专业的 TRPG 跑团 DM（游戏主持人），支持完整的跑团功能。

## ⚠️ 重要提示

### 模型配置建议
本插件充分利用 MaiBot 的多模型组能力：

| 功能 | 推荐模型组 | 说明 |
|------|-----------|------|
| DM 响应 | replyer | 生成剧情叙述、NPC对话 |
| 图片提示词 | planner | 分析场景生成绘图提示词 |
| PDF 解析 | utils | 解析长文本模组 |
| 意图理解 | planner | 理解玩家行动意图 |

为获得最佳体验：
1. **使用强大的 replyer 模型**：推荐 GPT-4、Claude-3、Qwen-Max
2. **简化人格提示词**：建议 50 字以内，避免过长占用上下文
3. **调整温度参数**：`llm_temperature = 0.8` 获得更有创意的响应

### 群组配置
在 `config.toml` 中配置允许使用的群组：
```toml
[plugin]
# 格式：["qq:123456:group", "qq:654321:group"]
# 留空表示所有群组都可以使用
allowed_groups = []
```

---

## 🎮 完整游玩流程示例

### 第一步：开始跑团
```
/trpg start solo_mystery
```

### 第二步：玩家加入
```
/join 李明
```

### 第三步：角色扮演
```
*拿起信封，仔细检查*
```

### 第四步：进行检定
```
/r d20
```

### 第五步：存档管理
```
/slot save 1    # 保存到插槽1
/slot list      # 查看所有存档
/slot load 1    # 加载插槽1
```

### 第六步：结束跑团
```
/trpg end
```

---

## 📋 命令参考

### 会话管理
| 命令 | 说明 |
|------|------|
| `/trpg start` | 显示可用模组列表 |
| `/trpg start [模组ID]` | 使用预设模组开始 |
| `/trpg start [世界观]` | 自由模式开始 |
| `/trpg end` | 结束当前跑团 |
| `/trpg status` | 查看会话状态 |
| `/trpg save` | 手动保存 |
| `/trpg pause` | 暂停跑团 |
| `/trpg resume` | 继续跑团 |

### 存档插槽
| 命令 | 说明 |
|------|------|
| `/slot list` | 查看所有存档插槽 |
| `/slot save [1-3]` | 保存到指定插槽 |
| `/slot load [1-3]` | 从插槽加载存档 |
| `/slot delete [1-3]` | 删除插槽存档（管理员） |

### 玩家操作
| 命令 | 说明 |
|------|------|
| `/join [角色名]` | 加入跑团 |
| `/pc show` | 查看角色卡 |
| `/pc set [属性] [值]` | 设置属性 |
| `/pc leave` | 离开跑团 |
| `/hp [+/-数值]` | 修改HP |
| `/mp [+/-数值]` | 修改MP |

### 背包系统
| 命令 | 说明 |
|------|------|
| `/inv` | 查看背包 |
| `/inv add [物品] [数量]` | 添加物品 |
| `/inv remove [物品] [数量]` | 移除物品 |
| `/inv use [物品]` | 使用物品 |

### 骰子命令
| 命令 | 示例 |
|------|------|
| `/r XdY` | `/r d20` `/r 2d6` |
| `/r XdY+Z` | `/r 1d20+5` |
| `/r XdY-Z` | `/r 3d8-2` |

### DM 命令（管理员）
| 命令 | 说明 |
|------|------|
| `/dm time [时间]` | 设置时间 |
| `/dm weather [天气]` | 设置天气 |
| `/dm location [位置]` | 设置位置 |
| `/dm npc [名称] [动作]` | 控制NPC |
| `/dm event [描述]` | 触发事件 |
| `/dm describe` | 描述环境 |

### 场景图片（需配置）
| 命令 | 说明 |
|------|------|
| `/scene image` | 生成当前场景图片 |
| `/scene image [描述]` | 根据描述生成图片 |

### 管理员命令
| 命令 | 说明 |
|------|------|
| `/confirm` | 查看待确认的加入请求 |
| `/confirm accept [用户ID]` | 确认加入 |
| `/confirm reject [用户ID]` | 拒绝加入 |

---

## 📚 预设模组

| 模组 | 类型 | 难度 | 人数 | 时长 |
|------|------|------|------|------|
| 🏙️ 独行侦探 (solo_mystery) | 现代推理 | 🟢简单 | 1人 | 30-60分钟 |
| 🗡️ 龙穴探险 (dragon_cave) | 奇幻冒险 | 🟢简单 | 3-5人 | 2-4小时 |
| 👻 幽灵庄园 (haunted_mansion) | 恐怖调查 | 🟡普通 | 2-4人 | 2-3小时 |
| 🚀 霓虹暗影 (cyberpunk_heist) | 赛博朋克 | 🔴困难 | 3-4人 | 3-4小时 |

---

## ⚙️ 配置说明

### 基本配置
```toml
[plugin]
enabled = true
# 允许的群组，留空表示所有群组
allowed_groups = []

[save_slots]
max_slots = 3           # 存档插槽数量
allow_overwrite = true  # 允许覆盖存档

[permissions]
# 管理员用户ID
admin_users = ["123456", "654321"]
```

### DM 配置
```toml
[dm]
use_maibot_replyer = true  # 使用 replyer 模型
llm_temperature = 0.8      # AI 创意程度
llm_max_tokens = 800       # 最大响应长度
auto_narrative = true      # 自动生成剧情
dm_personality = "你是一个经验丰富的跑团主持人。"

[llm_models]
dm_response_model = "replyer"    # DM 响应
image_prompt_model = "planner"   # 图片提示词
pdf_parse_model = "utils"        # PDF 解析
intent_model = "planner"         # 意图理解
```

### 图片生成配置
```toml
[image]
enabled = false              # 是否启用
api_type = "openai"          # API 类型
base_url = ""                # API 地址
api_key = ""                 # API 密钥
model_name = ""              # 模型名称
default_size_preset = "landscape"  # 默认尺寸
auto_generate = false        # 自动生成
```

图片尺寸预设：
- `portrait`: 768x1024 (竖版，适合角色)
- `landscape`: 1024x768 (横版，适合场景)
- `wide`: 1024x512 (宽幅，适合全景)
- `square`: 1024x1024 (正方形)

---

## 🎭 角色扮演格式

以下格式会触发 DM 响应：
```
*动作描述*          → *拔出长剑*
（动作描述）        → （小心翼翼地推开门）
"对话内容"          → "你好，请问这里是哪里？"
【角色】对话        → 【李明】我来调查这个案件
```

行动关键词：我要、我想、攻击、使用、查看、前往...

---

## 📥 导入自定义模组

### ✨ 推荐方式：Markdown 格式

将 `.md` 文件放入 `custom_modules/` 目录，插件会自动扫描并导入！

#### Markdown 模组格式

```markdown
---
id: my_adventure
name: 我的冒险
genre: fantasy
difficulty: normal
player_count: 2-4
author: 你的名字
tags: [冒险, 探索]
---

# 我的冒险模组

## 简介
这是一个奇幻冒险模组，玩家将探索神秘的古堡...

## 世界观背景
在艾尔兰大陆上，魔法与剑术并存...

- 三大王国争霸
- 魔法师公会控制魔法知识
- 最近出现了神秘的黑暗力量

## 开场白
夜幕降临，你们来到了边境小镇「晨曦镇」...

## NPC
### 老村长
一位和蔼的老人，知道很多秘密。
态度：友好

### 神秘商人
来历不明的旅行商人。
态度：中立

## 地点
### 晨曦镇
边境小镇，最近发生了奇怪的事件。

### 神秘森林
镇外的森林，据说有怪物出没。

## 物品
- 古老钥匙：打开地下室的钥匙
- 治疗药水：恢复 10 点 HP
- 魔法卷轴：施放火球术

## 剧情钩子
- 调查镇上失踪事件
- 寻找神殿中的古老神器

## 结局
### 光明结局
成功击败黑暗力量，拯救了小镇。

### 黑暗结局
黑暗力量蔓延，小镇陷入永恒的黑夜。

## DM 提示
- 神秘商人其实是关键 NPC
- 地下有密道通往神殿
```

#### 支持的章节

| 章节标题 | 说明 |
|---------|------|
| 简介/介绍/概述 | 模组简短描述 |
| 世界观/背景/设定 | 世界观设定 |
| 开场/序幕/引子 | 开场白文本 |
| NPC/角色/人物 | NPC 列表 |
| 地点/场景/location | 地点列表 |
| 物品/道具/item | 关键物品 |
| 结局/ending | 可能的结局 |
| DM/主持/提示 | DM 私密提示 |
| 剧情/钩子/hook | 剧情触发点 |

#### 模板文件

参考 `custom_modules/_template.md` 获取完整模板。

### JSON 格式

将 JSON 文件放入 `modules/custom/` 目录。

```json
{
  "info": {
    "id": "my_module",
    "name": "我的模组",
    "genre": "fantasy",
    "difficulty": "normal",
    "player_count": "2-4"
  },
  "world_name": "世界名称",
  "world_background": "世界观背景...",
  "intro_text": "开场白...",
  "lore": ["设定1", "设定2"],
  "npcs": {},
  "locations": {},
  "key_items": [],
  "endings": []
}
```

### PDF 导入（实验性）

1. 安装解析库：`pip install PyMuPDF`
2. 将 PDF 放入 `data/pdf_import/`
3. 使用 LLM 自动解析

---

## 📁 数据存储

```
data/
├── sessions/      # 会话存档
├── players/       # 玩家数据
├── lore/          # 世界观设定
├── modules/       # 自定义模组
├── save_slots/    # 存档插槽
└── config/        # 运行时配置
```

---

## 📄 许可证

GPL-3.0-or-later
