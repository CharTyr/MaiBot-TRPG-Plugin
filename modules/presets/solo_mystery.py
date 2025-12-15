"""
预设模组：独行侦探
一个专为单人设计的推理解谜模组，适合测试和单人游玩
"""

from ..base import ModuleBase, ModuleInfo, NPCTemplate, LocationTemplate, EventTemplate


def create_module() -> ModuleBase:
    """创建独行侦探模组"""
    
    info = ModuleInfo(
        id="solo_mystery",
        name="独行侦探",
        description="一个人也能玩的推理解谜模组。你是一名私家侦探，接到了一个神秘的委托...",
        author="MaiBot TRPG Team",
        version="1.0.0",
        genre="modern",
        difficulty="easy",
        player_count="1",
        duration="30-60分钟",
        tags=["单人", "推理", "解谜", "现代", "新手友好", "测试"],
    )
    
    module = ModuleBase(
        info=info,
        world_name="独行侦探",
        world_background="""
现代都市，一个普通的雨夜。

你是李明，一名经验丰富的私家侦探。
你的事务所位于城市老区的一栋旧楼里，生意不算好，但也能糊口。

今晚，一封神秘的信被塞进了你的门缝。
信上只有一个地址和一句话："午夜，旧图书馆，真相在等待。"

没有署名，没有报酬承诺，只有这个诡异的邀请。

作为一个侦探，你的好奇心被勾起了。
旧图书馆已经废弃多年，为什么有人要约你去那里？

时钟指向11点，你决定...
""",
        lore=[
            "旧图书馆建于1950年代，十年前因资金问题关闭",
            "据说图书馆的创始人王老先生在这里藏了一个秘密",
            "图书馆关闭后，偶尔有人看到里面有灯光",
            "你曾经帮王老先生的孙女找过一只走失的猫",
        ],
        intro_text="""
📖 独行侦探

🌧️ 雨夜，你的侦探事务所。

窗外的雨淅淅沥沥地下着，霓虹灯的光芒在雨幕中模糊成一片。
你正准备收拾东西回家，却发现门缝下多了一封信。

信封是普通的白色信封，没有邮戳，显然是有人亲手送来的。
你打开信封，里面只有一张纸条：

「午夜，旧图书馆，真相在等待。」

你看了看墙上的时钟——11:00。
还有一个小时。

旧图书馆...那个废弃了十年的地方？
是谁在那里等你？又是什么"真相"？

🎯 你的目标：前往旧图书馆，揭开这个神秘邀请背后的真相。

💡 提示：
- 输入你想做的事情，比如"检查信封"、"前往图书馆"
- 使用 /r d20 进行检定
- 使用 /pc show 查看你的状态
- 仔细观察环境，寻找线索

准备好了吗？冒险开始！
""",
        starting_location="侦探事务所",
        starting_time="night",
        starting_weather="rainy",
        
        npcs={
            "神秘女子": NPCTemplate(
                name="神秘女子",
                description="一位穿着黑色风衣的年轻女子，面容清秀但神情忧郁",
                location="图书馆大厅",
                attitude="neutral",
                dialogue_style="说话轻声细语，似乎在隐藏什么，但对侦探抱有期待",
                secrets=[
                    "她是王老先生的孙女王小雨",
                    "她发现了爷爷留下的遗嘱线索",
                    "她不信任警察，所以找了私家侦探",
                ],
            ),
            "老守卫": NPCTemplate(
                name="老守卫",
                description="一位年迈的守卫，在图书馆工作了三十年，即使关闭后也住在附近",
                location="图书馆门口",
                attitude="friendly",
                dialogue_style="说话啰嗦，喜欢回忆过去，对图书馆有深厚感情",
                secrets=[
                    "他知道图书馆的秘密通道",
                    "他见过有人深夜进入图书馆",
                ],
                inventory=["旧钥匙", "手电筒"],
            ),
        },
        
        locations={
            "侦探事务所": LocationTemplate(
                name="侦探事务所",
                description="你的小事务所，堆满了文件和旧报纸，墙上挂着你的侦探执照",
                connections=["街道"],
                items=["神秘信件", "手电筒", "笔记本", "放大镜"],
                hidden_info="信封上有淡淡的香水味，是一种昂贵的品牌",
            ),
            "街道": LocationTemplate(
                name="街道",
                description="雨夜的街道，路灯昏暗，行人稀少",
                connections=["侦探事务所", "图书馆门口"],
            ),
            "图书馆门口": LocationTemplate(
                name="图书馆门口",
                description="旧图书馆的正门，铁门生锈，但似乎最近被人打开过",
                connections=["街道", "图书馆大厅"],
                npcs=["老守卫"],
                hidden_info="门锁上有新的划痕，说明最近有人用工具开过锁",
            ),
            "图书馆大厅": LocationTemplate(
                name="图书馆大厅",
                description="宽敞但布满灰尘的大厅，月光从破碎的天窗洒入，照亮了中央的服务台",
                connections=["图书馆门口", "阅览室", "档案室", "楼梯"],
                npcs=["神秘女子"],
                items=["旧报纸", "灰尘中的脚印"],
                events=["听到楼上有声音"],
            ),
            "阅览室": LocationTemplate(
                name="阅览室",
                description="曾经的阅览室，书架东倒西歪，书籍散落一地",
                connections=["图书馆大厅"],
                items=["一本被翻开的书", "书签"],
                hidden_info="被翻开的书是《密码学入门》，书签上写着一串数字",
            ),
            "档案室": LocationTemplate(
                name="档案室",
                description="存放旧档案的房间，铁柜整齐排列，但有一个柜子被撬开了",
                connections=["图书馆大厅"],
                items=["被撬开的档案柜", "散落的文件"],
                hidden_info="档案柜里少了一份文件，标签显示是'王氏捐赠记录'",
            ),
            "楼梯": LocationTemplate(
                name="楼梯",
                description="通往二楼的楼梯，木质台阶吱呀作响",
                connections=["图书馆大厅", "馆长办公室"],
            ),
            "馆长办公室": LocationTemplate(
                name="馆长办公室",
                description="二楼的办公室，桌上有一盏还亮着的台灯，说明有人在这里",
                connections=["楼梯", "密室"],
                items=["台灯", "日记本", "保险箱"],
                hidden_info="日记本记录了王老先生临终前的话：'真相在书中，钥匙在心中'",
            ),
            "密室": LocationTemplate(
                name="密室",
                description="隐藏在书架后的小房间，这里存放着王老先生真正的遗产",
                connections=["馆长办公室"],
                items=["遗嘱", "老照片", "一箱珍贵的古籍"],
                hidden_info="遗嘱表明王老先生将图书馆和古籍捐给了城市，但被人隐瞒了",
            ),
        },
        
        events=[
            EventTemplate(
                name="遇见神秘女子",
                description="当你进入图书馆大厅时，一个身影从阴影中走出",
                trigger="进入图书馆大厅",
            ),
            EventTemplate(
                name="发现线索",
                description="在阅览室发现了重要的密码线索",
                trigger="仔细检查阅览室",
            ),
            EventTemplate(
                name="真相大白",
                description="找到密室，揭开了整个事件的真相",
                trigger="找到并进入密室",
            ),
        ],
        
        key_items=[
            {"name": "神秘信件", "description": "邀请你来图书馆的信", "location": "侦探事务所"},
            {"name": "书签密码", "description": "写着数字的书签，是保险箱密码", "location": "阅览室"},
            {"name": "日记本", "description": "记录了关键信息的日记", "location": "馆长办公室"},
            {"name": "遗嘱", "description": "王老先生的真正遗嘱", "location": "密室"},
        ],
        
        endings=[
            {
                "name": "真相大白",
                "condition": "找到遗嘱，揭露真相",
                "description": "你成功找到了王老先生的遗嘱，揭露了有人试图侵吞图书馆遗产的阴谋。神秘女子——王小雨感激地握住你的手。这座图书馆将重新开放，而你，又完成了一个案件。",
            },
            {
                "name": "部分真相",
                "condition": "找到部分线索但未找到遗嘱",
                "description": "虽然没有找到决定性的证据，但你收集的线索足以让警方介入调查。案件还没有完全解决，但至少迈出了第一步。",
            },
            {
                "name": "空手而归",
                "condition": "没有找到重要线索就离开",
                "description": "这个夜晚充满了谜团，但你没能解开它们。也许下次会有更好的机会...",
            },
        ],
        
        dm_notes="""
DM 提示（单人模组特别说明）：

1. 节奏控制：
   - 这是单人模组，节奏可以更快
   - 多给予正面反馈，保持玩家兴趣
   - 如果玩家卡住，可以通过NPC给予提示

2. 检定建议：
   - 检查信封：感知检定 DC10
   - 发现脚印：感知检定 DC12
   - 找到书签密码：智力检定 DC10
   - 打开保险箱：智力检定 DC12（有密码则自动成功）
   - 发现密室入口：感知检定 DC15

3. 关键流程：
   侦探事务所 → 图书馆门口（遇老守卫）→ 大厅（遇神秘女子）
   → 阅览室（找密码）→ 馆长办公室（找日记）→ 密室（找遗嘱）

4. NPC 互动：
   - 老守卫：可以提供图书馆历史和秘密通道信息
   - 神秘女子：会在关键时刻提供帮助，但不会直接告诉答案

5. 单人游戏特别提示：
   - 可以让玩家的角色"自言自语"来推理
   - 适时给予环境描写来营造氛围
   - 如果玩家长时间没有进展，可以触发新事件推动剧情
""",
        
        plot_hooks=[
            "信封上的香水味可以作为线索",
            "老守卫会主动搭话，提供背景信息",
            "神秘女子会在玩家迷茫时给予暗示",
            "书签上的数字是保险箱密码",
            "日记本暗示了密室的存在",
        ],
    )
    
    return module
