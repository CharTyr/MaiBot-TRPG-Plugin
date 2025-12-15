# MaiBot TRPG DM 插件开发文档

本文档面向后续开发者，帮助快速理解插件架构并接手开发。

---

## 📋 项目概述

### 目的
将 MaiBot 变成 TRPG（桌面角色扮演游戏）的 DM（游戏主持人），在群聊中主持跑团游戏。

### 核心功能
1. **骰子系统** - 支持标准骰子表达式 (XdY+Z)
2. **玩家管理** - 角色创建、属性、HP/MP、背包
3. **会话管理** - 开始/暂停/结束跑团，自动存档
4. **DM 引擎** - 使用 LLM 生成剧情、NPC 对话、环境描述
5. **模组系统** - 预设模组 + 自定义模组 + PDF 导入
6. **群组隔离** - 每个群独立的会话和数据

### 设计原则
- **完全接管**：跑团期间插件接管群消息处理，阻止其他插件干扰
- **融合人格**：使用 MaiBot 的 replyer 模型，融合 bot 人格扮演 DM
- **数据持久化**：所有数据 JSON 存储，重启后自动恢复
- **开箱即用**：内置 4 个预设模组，无需配置即可开始

---

## 🏗️ 架构总览

```
MaiBot_TRPG_DM/
├── plugin.py              # 插件入口，注册组件
├── config.toml            # 配置文件
├── _manifest.json         # 插件清单
│
├── components/            # MaiBot 组件（命令、事件处理器、工具）
│   ├── commands.py        # 所有斜杠命令 (/trpg, /r, /join, etc.)
│   ├── handlers.py        # 消息事件处理器（核心拦截逻辑）
│   └── tools.py           # LLM 工具（供 AI 调用）
│
├── services/              # 业务逻辑服务
│   ├── dice.py            # 骰子服务
│   ├── dm_engine.py       # DM 引擎（LLM 调用）
│   ├── pdf_parser.py      # PDF 模组解析
│   └── image_generator.py # 场景图片生成（可选）
│
├── models/                # 数据模型
│   ├── session.py         # 会话、世界状态、NPC、历史记录
│   ├── player.py          # 玩家、属性、背包
│   └── storage.py         # 存储管理器（JSON 持久化）
│
├── modules/               # 模组系统
│   ├── base.py            # 模组基类定义
│   ├── loader.py          # 模组加载器
│   └── presets/           # 预设模组
│       ├── solo_mystery.py      # 独行侦探（单人测试）
│       ├── dragon_cave.py       # 龙穴探险（奇幻）
│       ├── haunted_mansion.py   # 幽灵庄园（恐怖）
│       └── cyberpunk_heist.py   # 霓虹暗影（赛博朋克）
│
└── data/                  # 运行时数据（git 忽略）
    ├── sessions/          # 会话存档
    ├── players/           # 玩家数据
    └── modules/           # 自定义模组
```

---

## 🔌 与 MaiBot 的集成

### 插件系统 API

插件基于 MaiBot 的 `src/plugin_system/` 构建，使用以下基类：

```python
from src.plugin_system import (
    BasePlugin,      # 插件基类
    BaseCommand,     # 命令基类
    BaseEventHandler,# 事件处理器基类
    BaseTool,        # LLM 工具基类
    register_plugin, # 插件注册装饰器
    ConfigField,     # 配置字段定义
)

from src.plugin_system.apis import (
    llm_api,         # LLM 调用 API
    send_api,        # 消息发送 API
    database_api,    # 数据库 API（未使用）
)
```

### 组件注册流程

```python
# plugin.py
@register_plugin
class TRPGDMPlugin(BasePlugin):
    def get_plugin_components(self):
        # 初始化服务
        self._initialize_services()
        
        # 返回组件列表 [(ComponentInfo, ComponentClass), ...]
        return [
            (TRPGSessionCommand.get_command_info(), TRPGSessionCommand),
            (TRPGMessageHandler.get_handler_info(), TRPGMessageHandler),
            (RollDiceTool.get_tool_info(), RollDiceTool),
            # ...
        ]
```

### 服务依赖注入

由于 MaiBot 组件是独立实例化的，使用全局变量注入服务：

```python
# components/commands.py
_storage: Optional["StorageManager"] = None
_dice_service: Optional["DiceService"] = None
_dm_engine: Optional["DMEngine"] = None
_module_loader: Optional["ModuleLoader"] = None

def set_services(storage, dice, dm, loader):
    global _storage, _dice_service, _dm_engine, _module_loader
    _storage = storage
    # ...
```

---

## 🎯 核心流程

### 1. 消息处理流程（与 MaiBot 的集成）

```
用户消息 → bot.py
    │
    ├─ handle_mai_events(ON_MESSAGE_PRE_PROCESS)
    ├─ _process_commands() → 处理斜杠命令
    │
    ├─ handle_mai_events(ON_MESSAGE)
    │   │
    │   └─ TRPGMessageHandler.execute() [weight=1000, intercept_message=True]
    │       │
    │       ├─ 非跑团群组/无活跃会话 → return (True, True) → 放行给 MaiBot
    │       │
    │       └─ 跑团群组 + 活跃会话：
    │           ├─ 跑团命令 (/trpg, /r, /join...) → return (True, False) → 阻止 MaiBot
    │           ├─ 非跑团命令 + takeover=true → return (True, False) → 阻止 MaiBot
    │           ├─ 角色扮演消息 → 生成 DM 响应 → return (True, False)
    │           └─ 普通消息 + takeover=true → return (True, False) → 阻止 MaiBot
    │
    ├─ if not continue_flag: return  ← 插件返回 False 时，这里直接返回！
    │
    └─ heartflow_message_receiver.process_message() ← MaiBot 原本的回复流程（被阻止）
```

**关键点**：
- `weight = 1000`：确保我们的处理器最先执行
- `intercept_message = True`：阻塞执行，等待返回结果
- 返回值第二个参数 `continue_processing`：`False` 阻止后续处理，`True` 放行

### 2. 消息拦截配置

```toml
# config.toml
[integration]
takeover_message = true      # 完全接管消息处理
block_other_plugins = true   # 阻止其他插件
```

| 场景 | takeover_message | 结果 |
|------|------------------|------|
| 跑团群组 + 活跃会话 | true | 所有消息被拦截，MaiBot 不回复 |
| 跑团群组 + 活跃会话 | false | 仅角色扮演消息触发 DM，其他消息 MaiBot 可能回复 |
| 非跑团群组 | - | 放行，MaiBot 正常回复 |
| 无活跃会话 | - | 放行，MaiBot 正常回复 |

### 3. TRPGMessageHandler 详细流程

```
TRPGMessageHandler.execute(message)
    │
    ├─ 前置检查（任一失败则放行）：
    │   ├─ message 存在？
    │   ├─ _storage 和 _dm_engine 已初始化？
    │   ├─ stream_id 存在？
    │   ├─ 群组已启用跑团？ (_storage.is_group_enabled)
    │   └─ 有活跃会话？ (session.is_active)
    │
    ├─ 命令处理（/开头）：
    │   ├─ 跑团命令 → return (True, not block_others)
    │   └─ 非跑团命令 + takeover → return (True, False)
    │
    ├─ 角色扮演检测：
    │   ├─ *动作* / （动作）/ "对话" 格式
    │   └─ 行动关键词（我要、攻击、查看...）
    │
    ├─ DM 响应生成（如果需要）：
    │   ├─ 记录玩家行动到历史
    │   ├─ 调用 DMEngine.generate_dm_response()
    │   ├─ 记录 DM 响应到历史
    │   └─ 发送响应
    │
    └─ 最终返回：
        └─ takeover=true → return (True, False) → 阻止 MaiBot
```

### 4. DM 响应生成流程

```python
# services/dm_engine.py
async def generate_dm_response(self, session, player_message, player, config):
    # 1. 构建提示词
    prompt = self._build_dm_prompt(session, player_message, player)
    
    # 2. 获取 replyer 模型
    models = llm_api.get_available_models()
    model_config = models.get("replyer")
    
    # 3. 调用 LLM
    success, response, _, _ = await llm_api.generate_with_model(
        prompt=prompt,
        model_config=model_config,
        request_type="trpg.dm_response",
        temperature=0.8,
        max_tokens=800,
    )
    
    return response
```

### 5. 数据持久化流程

```
StorageManager
    │
    ├─ _sessions: Dict[stream_id, TRPGSession]  # 内存缓存
    ├─ _players: Dict[stream_id, Dict[user_id, Player]]
    │
    ├─ save_session() → data/sessions/{stream_id}.json
    ├─ save_player() → data/players/{stream_id}/{user_id}.json
    │
    └─ 启动时自动加载所有未结束的会话
```

---

## 📝 关键数据结构

### TRPGSession（会话）

```python
@dataclass
class TRPGSession:
    stream_id: str           # 群组 ID
    status: str              # active, paused, ended
    world_name: str          # 世界观名称
    world_state: WorldState  # 时间、天气、位置
    history: List[HistoryEntry]  # 历史记录
    npcs: Dict[str, NPCState]    # NPC 状态
    lore: List[str]          # 世界观设定
    player_ids: List[str]    # 玩家 ID 列表
```

### Player（玩家）

```python
@dataclass
class Player:
    user_id: str
    stream_id: str
    character_name: str
    hp_current: int
    hp_max: int
    mp_current: int
    mp_max: int
    attributes: PlayerAttributes  # 力量、敏捷等
    inventory: List[InventoryItem]
    status_effects: List[str]
```

### ModuleBase（模组）

```python
@dataclass
class ModuleBase:
    info: ModuleInfo         # 名称、作者、难度等
    world_name: str
    world_background: str
    lore: List[str]
    intro_text: str          # 开场白
    npcs: Dict[str, NPCTemplate]
    locations: Dict[str, LocationTemplate]
    events: List[EventTemplate]
    endings: List[Dict]
```

---

## 🛠️ 开发指南

### 添加新命令

```python
# components/commands.py
class MyNewCommand(BaseCommand):
    command_name = "my_command"
    command_description = "命令描述"
    command_pattern = r"^/mycommand(?:\s+(.+))?$"
    
    async def execute(self) -> Tuple[bool, Optional[str], int]:
        # self.message - 消息对象
        # self.matched_groups - 正则匹配组
        
        await self.send_text("响应内容")
        return True, None, 2  # (成功, 错误信息, 优先级)
```

然后在 `plugin.py` 的 `get_plugin_components()` 中注册。

### 添加新预设模组

1. 在 `modules/presets/` 创建新文件
2. 实现 `create_module() -> ModuleBase` 函数
3. 在 `modules/presets/__init__.py` 的 `PRESET_MODULES` 中注册

```python
# modules/presets/my_module.py
def create_module() -> ModuleBase:
    info = ModuleInfo(
        id="my_module",
        name="我的模组",
        # ...
    )
    return ModuleBase(info=info, ...)

# modules/presets/__init__.py
PRESET_MODULES = {
    "my_module": {
        "name": "我的模组",
        "genre": "fantasy",
        "difficulty": "normal",
        "player_count": "2-4",
        "create": my_module.create_module,
    },
    # ...
}
```

### 修改 DM 行为

DM 的核心逻辑在 `services/dm_engine.py`：

- `_build_dm_prompt()` - 构建提示词
- `generate_dm_response()` - 生成响应
- `generate_npc_dialogue()` - NPC 对话
- `describe_environment()` - 环境描述

### 配置项

所有配置在 `config.toml`，对应 `plugin.py` 中的 `config_schema`。

添加新配置：
1. 在 `config.toml` 添加配置项
2. 在 `plugin.py` 的 `config_schema` 添加 `ConfigField`
3. 在代码中通过 `self.plugin_config` 或注入的 `config` 访问

---

## ⚠️ 待完善功能

### 高优先级

1. **权限系统** - `commands.py` 中 DM 命令的权限检查（标记为 TODO）
2. **存档插槽命令** - `storage.py` 有 `save_to_slot/load_from_slot`，但没有命令入口
3. **中途加入确认** - `allow_mid_join` 配置存在，但确认逻辑未实现

### 中优先级

4. **图片生成集成** - `image_generator.py` 已实现，但未集成到 DM 流程
5. **WebUI 适配** - 需要了解 MaiBot WebUI 系统后实现

### 低优先级

6. **更多预设模组**
7. **战斗系统增强**
8. **多语言支持**

---

## 🧪 测试方法

### 单人测试

使用 `solo_mystery` 模组进行单人测试：

```
/trpg start solo_mystery
/join 李明
*检查信封*
/r d20
/trpg end
```

### 关键测试点

1. 会话创建/结束
2. 玩家加入/离开
3. 骰子表达式解析
4. DM 响应生成
5. 数据持久化（重启后恢复）
6. 群组隔离

---

## 📚 相关文件

- `README.md` - 用户文档
- `CODE_REVIEW.md` - 代码审查报告
- `config.toml` - 配置文件（有详细注释）
- `_manifest.json` - 插件清单

---

## 🔗 MaiBot 插件系统参考

- 基类定义：`src/plugin_system/base/`
- API 接口：`src/plugin_system/apis/`
- 参考插件：`plugins/hello_world_plugin/`

---

## 🔒 消息拦截机制详解

### MaiBot 事件系统

MaiBot 使用 `EventsManager` 管理事件处理器：

```python
# src/plugin_system/core/events_manager.py
class EventsManager:
    async def handle_mai_events(self, event_type, message, ...):
        handlers = self._events_subscribers.get(event_type, [])
        # 按 weight 降序排列
        for handler in handlers:
            if handler.intercept_message:
                should_continue, modified_message = await handler.execute(message)
                continue_flag = continue_flag and should_continue
            else:
                asyncio.create_task(handler.execute(message))  # 异步执行
        return continue_flag, modified_message
```

### 关键属性

| 属性 | 说明 | 我们的设置 |
|------|------|-----------|
| `event_type` | 监听的事件类型 | `EventType.ON_MESSAGE` |
| `weight` | 执行优先级（越高越先） | `1000`（最高） |
| `intercept_message` | 是否阻塞执行 | `True` |

### 返回值格式

```python
async def execute(self, message) -> Tuple[bool, bool, str, CustomEventHandlerResult, MaiMessages]:
    # 返回值：
    # [0] success: 是否执行成功
    # [1] continue_processing: 是否继续处理后续处理器和 MaiBot 主流程
    # [2] return_message: 返回消息（日志用）
    # [3] custom_result: 自定义结果
    # [4] modified_message: 修改后的消息
    
    return True, False, None, None, None  # 阻止后续处理
    return True, True, None, None, None   # 放行
```

### 为什么不会出现双重回复

1. **我们的处理器 weight=1000**，最先执行
2. **返回 `continue_processing=False`** 时，`continue_flag` 变为 `False`
3. **bot.py 检查 `if not continue_flag: return`**，直接返回
4. **MaiBot 的 `heartflow_message_receiver.process_message()` 不会执行**

---

*最后更新：2025-12-15*
