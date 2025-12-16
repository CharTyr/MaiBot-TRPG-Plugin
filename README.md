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
/trpg join 李明
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
/trpg slot save 1    # 保存到插槽1
/trpg slot list      # 查看所有存档
/trpg slot load 1    # 加载插槽1
```

### 第六步：结束跑团
```
/trpg end
```

---

## 📋 命令参考

> 所有命令统一使用 `/trpg` 前缀，骰子命令保留 `/r` 快捷方式

### 会话管理
| 命令 | 说明 |
|------|------|
| `/trpg help` | 显示帮助信息 |
| `/trpg start` | 显示可用模组列表 |
| `/trpg start [模组ID]` | 使用预设模组开始 |
| `/trpg start [世界观]` | 自由模式开始 |
| `/trpg end` | 结束当前跑团 |
| `/trpg status` 或 `/trpg s` | 查看会话状态 |
| `/trpg save` | 手动保存 |
| `/trpg pause` | 暂停跑团 |
| `/trpg resume` | 继续跑团 |

### 存档插槽
| 命令 | 说明 |
|------|------|
| `/trpg slot list` | 查看所有存档插槽 |
| `/trpg slot save [1-3]` | 保存到指定插槽 |
| `/trpg slot load [1-3]` | 从插槽加载存档（自动显示前情回顾） |
| `/trpg slot delete [1-3]` | 删除插槽存档（管理员） |

### 玩家操作
| 命令 | 说明 |
|------|------|
| `/trpg join [角色名]` 或 `/trpg j` | 加入跑团 |
| `/trpg pc show` | 查看角色卡 |
| `/trpg pc set [属性] [值]` | 设置属性 |
| `/trpg pc leave` | 离开跑团 |
| `/trpg hp [+/-数值]` | 修改HP |
| `/trpg mp [+/-数值]` | 修改MP |

### 背包系统
| 命令 | 说明 |
|------|------|
| `/trpg inv` 或 `/trpg i` | 查看背包 |
| `/trpg inv add [物品] [数量]` | 添加物品 |
| `/trpg inv rm [物品] [数量]` | 移除物品 |
| `/trpg inv use [物品]` | 使用物品 |

### 骰子命令
| 命令 | 示例 |
|------|------|
| `/trpg r XdY` 或 `/r XdY` | `/r d20` `/r 2d6` |
| `/trpg r XdY+Z` | `/trpg r 1d20+5` |
| `/r XdY-Z` | `/r 3d8-2` |

### DM 命令（管理员）
| 命令 | 说明 |
|------|------|
| `/trpg dm time [时间]` | 设置时间 |
| `/trpg dm weather [天气]` | 设置天气 |
| `/trpg dm location [位置]` | 设置位置 |
| `/trpg dm npc [名称] [动作]` | 控制NPC |
| `/trpg dm event [描述]` | 触发事件 |
| `/trpg dm describe` | 描述环境 |

### 模组管理
| 命令 | 说明 |
|------|------|
| `/trpg mod list` | 列出可用模组 |
| `/trpg mod info [ID]` | 查看模组详情 |

### 场景图片（需配置）
| 命令 | 说明 |
|------|------|
| `/trpg scene` | 生成当前场景图片 |
| `/trpg scene [描述]` | 根据描述生成图片 |

### 管理员命令
| 命令 | 说明 |
|------|------|
| `/trpg confirm` | 查看待确认的加入请求 |
| `/trpg confirm accept [用户ID]` | 确认加入 |
| `/trpg confirm reject [用户ID]` | 拒绝加入 |

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
show_action_feedback = true  # 玩家行动时立即反馈
max_retries = 3              # DM 响应失败重试次数
retry_delay = 1.0            # 重试间隔（秒，指数退避）

[multiplayer]
batch_actions = true         # 启用多人行动批量处理
action_collect_window = 5.0  # 行动收集窗口（秒）
extra_wait_time = 2.0        # 额外等待时间

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
api_type = "sd_api"          # API 类型: openai, sd_api, gradio, novelai
base_url = ""                # API 地址
api_key = ""                 # API 密钥
model_name = ""              # 模型名称（OpenAI 格式需要）
default_size_preset = "landscape"  # 默认尺寸
auto_generate = false        # 自动生成
climax_auto_image = true     # 高潮自动画图
climax_min_interval = 5      # 高潮画图最小间隔
```

图片尺寸预设：
- `portrait`: 768x1024 (竖版，适合角色)
- `landscape`: 1024x768 (横版，适合场景)
- `wide`: 1024x512 (宽幅，适合全景)
- `square`: 1024x1024 (正方形)

#### SD API 配置
```toml
[image.sd_api]
# 负面提示词 (string, 默认"")
negative_prompt = "lowres, bad quality, watermark"
# 图像宽度 (integer, 64-2048, 默认512)，设为0则使用 default_size_preset
width = 0
# 图像高度 (integer, 64-2048, 默认512)，设为0则使用 default_size_preset
height = 0
# 生成步数 (integer, 1-50, 默认20)
steps = 28
# CFG 引导强度 (float, 1-10, 默认7.0)
cfg = 7.0
# 模型索引 (integer, 默认0)
model_index = 0
# 随机种子 (integer, 默认-1)，-1为随机
seed = -1
# 请求超时时间（秒）
timeout = 120
```

#### Gradio API 配置
```toml
[image.gradio]
resolution = "1024x1024 ( 1:1 )"  # 分辨率
steps = 8                         # 推理步数
shift = 3                         # 时间偏移
timeout = 120                     # 超时时间
```

#### NovelAI API 配置
```toml
[image.novelai]
model = "nai-diffusion-4-5-full"  # 模型名称
width = 832                       # 图像宽度
height = 1216                     # 图像高度
steps = 28                        # 生成步数
scale = 5.0                       # 引导强度
sampler = "k_euler"               # 采样器
negative_prompt = ""              # 负面提示词
seed = -1                         # 随机种子
timeout = 120                     # 超时时间
```

---

## 👥 多人模式

当模组有 2 人以上参与时，插件会自动启用**行动收集模式**：

1. 玩家 A 发送行动 → 立即收到确认反馈
2. 系统开始 5 秒收集窗口
3. 玩家 B、C 在窗口内发送行动 → 各自收到确认
4. 窗口结束后，DM 统一处理所有行动
5. 生成一个连贯的场景描述，体现行动间的互动

**优势**：
- 避免响应混乱，剧情更连贯
- 减少 API 调用，节省资源
- 体现玩家间的配合或冲突

**配置**：
```toml
[multiplayer]
batch_actions = true         # 启用批量处理（默认开启）
action_collect_window = 5.0  # 收集窗口时长（秒）
```

---

## 📖 剧情上下文系统

插件会自动追踪和维护剧情上下文，确保叙事连贯：

**自动追踪的内容**：
- 📝 剧情摘要（每10条历史自动更新）
- ⚡ 关键事件列表
- 🔍 已发现的线索
- ❓ 未解决的谜题
- 📊 剧情张力等级（0-10）

**张力等级影响**：
- 高张力（≥7）：DM 会营造紧张氛围，更容易触发高潮画图
- 低张力（≤2）：DM 会适当推进剧情或埋下伏笔

---

## 🎨 高潮场景自动画图

当检测到剧情高潮时，插件会自动生成场景图片：

**触发条件**（满足任一）：
- 响应中包含 ≥2 个高潮关键词（如"真相"、"胜利"、"死亡"等）
- 张力等级 ≥7 且有 ≥1 个关键词
- 距离上次生成图片至少 5 条历史

**Planner 智能选择尺寸**：
- `portrait` (768x1024) - 角色特写、NPC对话
- `landscape` (1024x768) - 场景描述、战斗场面
- `wide` (1024x512) - 全景、大场面

**配置**：
```toml
[image]
enabled = true              # 启用图片生成
climax_auto_image = true    # 启用高潮自动画图
climax_min_interval = 5     # 最小间隔（历史条数）
```

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

支持互联网主流 TRPG 模组规范（COC/DND 等）。

#### 模组结构规范

符合主流 TRPG 模组的四大部分：

| 部分 | 章节 | 说明 |
|------|------|------|
| 公开信息 | 简介、背景介绍、故事前提 | 可展示给玩家 |
| 主持人信息 | 真相揭秘、故事龙骨 | 仅供 KP/DM |
| 模组正文 | 场景、NPC、地点、事件、物品、线索 | 游戏核心内容 |
| 辅助资料 | DM提示、附录、结局 | 帮助主持 |

#### 快速示例

```markdown
---
id: haunted_mansion
name: 幽灵庄园
genre: horror
difficulty: normal
player_count: 2-4
era: 现代
system: coc
---

# 幽灵庄园

## 背景介绍
一座废弃多年的维多利亚式庄园，据说藏着不为人知的秘密...

## 真相揭秘
庄园主人是邪教徒，管家是真正的幕后黑手...

## 开场白
雨夜，你们的车在泥泞的山路上艰难前行...

## 场景
### 场景一：庄园大厅
布景：宏伟但破败的大厅
承接：开场 → 餐厅/图书室
NPC：管家詹姆斯
检定：侦查 DC12

## NPC
### 管家詹姆斯
态度：表面友好，实际敌对
位置：大厅
说话风格：正式有礼但讳莫如深
秘密：
- 他是邪教核心成员
- 他知道密室位置

## 地点
### 图书室
连接：大厅、密室（暗门）
物品：古老书籍、神秘笔记
隐藏信息：书架后有暗门

## 线索
### 神秘日记
位置：喷泉暗格
指向：二十年前的事件

## 结局
### 光明结局
条件：成功阻止仪式
类型：good
```

#### 支持的章节类型

| 章节关键词 | 说明 |
|-----------|------|
| 简介/背景/世界观 | 背景设定 |
| 故事前提/前提 | 故事起因 |
| 真相/揭秘 | KP 专用真相 |
| 龙骨/大纲/流程 | 故事主线 |
| 开场/序幕/导入 | 开场白 |
| 场景/scene | 场景序列 |
| NPC/角色/人物 | NPC 图鉴 |
| 地点/场景/地图 | 地点设计 |
| 事件/event | 触发事件 |
| 物品/道具 | 关键道具 |
| 线索/clue | 线索列表 |
| 结局/ending | 可能结局 |
| DM/KP/提示 | 主持提示 |

#### NPC 详细格式

```markdown
### NPC名称
描述文本...

态度：友好/中立/敌对
位置：所在地点
说话风格：对话特点
职业：职业设定
动机：行动目的
关系：与其他角色关系
物品：携带物品1、物品2

秘密：
- 秘密1
- 秘密2
```

#### 场景详细格式

```markdown
### 场景名称
布景：环境描述
设定：时间、地点等基础设定
承接：前置场景 → 后续场景
NPC：出场NPC
物品：可发现物品
检定：需要的检定

> 引用块作为 CG 描述文本
```

#### 模板文件

参考 `custom_modules/_template.md` 获取完整模板，包含所有支持的字段和格式示例。

### JSON 格式

将 JSON 文件放入 `modules/custom/` 目录。

### PDF 导入（实验性）

1. 安装解析库：`pip install PyMuPDF`
2. 将 PDF 放入 `data/pdf_import/`
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
| 世界观/背景/设定 | 世界观设定（列表项会提取为 lore） |
| 开场/序幕/引子 | 开场白文本 |
| NPC/角色/人物 | NPC 列表（用 ### 分隔每个 NPC） |
| 地点/场景/location | 地点列表（用 ### 分隔每个地点） |
| 事件/event | 事件列表（用 ### 分隔每个事件） |
| 物品/道具/item | 关键物品 |
| 结局/ending | 可能的结局（用 ### 分隔每个结局） |
| DM/主持/提示 | DM 私密提示 |
| 剧情/钩子/hook | 剧情触发点 |

#### NPC 详细格式

```markdown
### NPC名称
描述文本...

态度：友好/中立/敌对
位置：所在地点
说话风格：NPC 的对话特点
物品：物品1、物品2

秘密：
- 秘密1
- 秘密2
```

#### 地点详细格式

```markdown
### 地点名称
描述文本...

连接：地点1、地点2
物品：物品1、物品2
NPC：NPC1、NPC2
事件：事件1、事件2
隐藏信息：需要调查才能发现的信息
```

#### 结局详细格式

```markdown
### 结局名称
条件：达成此结局的条件

结局描述文本...
```

#### 模板文件

参考 `custom_modules/_template.md` 获取完整模板，包含所有支持的字段和格式示例。

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
