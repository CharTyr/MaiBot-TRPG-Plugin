# MaiBot_TRPG_DM 测试指南

## 快速测试流程

### 1. 基础功能测试

```
# 查看可用模组
/trpg start

# 开始单人测试模组（推荐）
/trpg start solo_mystery

# 加入跑团
/join 李明

# 查看角色卡
/pc show

# 掷骰子测试
/r d20
/r 2d6+3
/r 3d8-2
/r 1d20+1d4+5

# 查看背包
/inv

# 添加物品
/inv add 治疗药水 3
/inv add 古老钥匙

# 使用物品
/inv use 治疗药水

# 修改HP/MP
/hp -5
/hp +10
/mp -3

# 查看状态
/trpg status

# 结束跑团
/trpg end
```

### 2. 存档功能测试

```
# 开始新跑团
/trpg start dragon_cave
/join 勇者

# 保存到插槽1
/slot save 1

# 查看存档列表
/slot list

# 结束当前跑团
/trpg end

# 从插槽加载
/slot load 1

# 验证恢复
/trpg status
/pc show
```

### 3. DM命令测试（需管理员权限）

```
# 开始跑团
/trpg start 测试世界

# 设置环境
/dm time night
/dm weather rainy
/dm location 神秘森林

# 描述环境
/dm describe

# 添加NPC
/dm npc 老村长 向冒险者打招呼

# 触发事件
/dm event 远处传来狼嚎声
```

### 4. 角色扮演测试

开始跑团后，发送以下格式的消息测试DM响应：

```
*小心翼翼地推开门*
（检查房间里有什么）
"你好，请问这里是哪里？"
【李明】我要调查这个神秘的箱子
我想查看周围的环境
攻击面前的怪物
```

### 5. 模组功能测试

```
# 列出所有模组
/module list

# 查看模组详情
/module info solo_mystery
/module info dragon_cave
/module info haunted_mansion
/module info cyberpunk_heist

# 查看导入说明
/module import
```

### 6. 世界观设定测试

```
/trpg start 自定义世界

# 添加设定
/lore add 这是一个魔法与科技并存的世界
/lore add 精灵族居住在北方森林

# 搜索设定
/lore search 精灵

# 查看所有设定
/lore
```

---

## 预期结果

### 骰子系统
- `d20` → 1-20 的随机数
- `2d6+3` → 两个d6的和加3
- 大成功(20)/大失败(1) 应有特殊提示

### 角色系统
- 默认属性值: 10
- 默认HP: 20, MP: 10
- 背包最大容量: 50

### 存档系统
- 默认3个插槽
- 保存/加载应保留所有玩家数据

### DM响应
- 角色扮演消息应触发AI响应
- 响应应包含场景描述和行动结果

---

## 常见问题排查

### 插件未加载
检查 `config.toml` 中 `enabled = true`

### DM不响应
1. 检查 `[dm]` 配置中 `auto_narrative = true`
2. 检查 MaiBot 的 LLM 模型是否正常

### 权限问题
在 `config.toml` 的 `[permissions]` 中添加管理员ID：
```toml
admin_users = ["你的用户ID"]
```

### 图片生成失败
需要在 `[image]` 中配置API：
```toml
[image]
enabled = true
api_type = "openai"  # 或 gradio, sd_api
base_url = "你的API地址"
api_key = "你的API密钥"
```

---

## 测试检查清单

- [ ] `/trpg start` 显示模组列表
- [ ] `/trpg start solo_mystery` 成功加载模组
- [ ] `/join` 成功创建角色
- [ ] `/r d20` 正确掷骰
- [ ] `/pc show` 显示角色卡
- [ ] `/inv add/remove/use` 背包操作正常
- [ ] `/hp` `/mp` 修改生效
- [ ] `/slot save/load` 存档功能正常
- [ ] 角色扮演消息触发DM响应
- [ ] `/trpg end` 正确结束会话

---

*测试指南版本: 1.0*
*对应插件版本: 1.2.0*
