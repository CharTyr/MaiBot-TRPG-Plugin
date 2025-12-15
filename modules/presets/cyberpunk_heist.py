"""
预设模组：霓虹暗影
一个赛博朋克风格的潜入任务模组
"""

from ..base import ModuleBase, ModuleInfo, NPCTemplate, LocationTemplate, EventTemplate


def create_module() -> ModuleBase:
    """创建霓虹暗影模组"""
    
    info = ModuleInfo(
        id="cyberpunk_heist",
        name="霓虹暗影",
        description="2087年，新东京。一次高风险的企业潜入任务，目标是窃取价值连城的AI核心。",
        author="MaiBot TRPG Team",
        version="1.0.0",
        genre="scifi",
        difficulty="hard",
        player_count="3-4",
        duration="3-4小时",
        tags=["赛博朋克", "潜入", "科幻", "黑客", "高难度"],
    )
    
    module = ModuleBase(
        info=info,
        world_name="霓虹暗影",
        world_background="""
2087年，新东京。

在这座永不熄灭的霓虹都市中，巨型企业掌控着一切。
最强大的三家企业——神罗科技、阿拉萨卡集团和军用科技，
在暗处进行着永无止境的战争。

你们是一群"边缘行者"——游走在法律边缘的雇佣兵、黑客和街头武士。
在这个世界里，信息就是货币，而你们就是信息的猎人。

今晚，你们接到了一个大单：
潜入神罗科技的研发大楼，窃取他们最新研发的AI核心"普罗米修斯"。

委托人是一个神秘的中间人，代号"幽灵"。
报酬是五十万新元——足够你们在这座城市里舒服地活上好几年。

但神罗科技的安保系统是全城最严密的，
而且据说"普罗米修斯"不是普通的AI...

准备好了吗？任务开始。
""",
        lore=[
            "神罗科技是新东京最大的科技企业，专注于AI和义体研发",
            "普罗米修斯是神罗科技的秘密项目，据说是第一个具有真正自我意识的AI",
            "神罗大楼有47层，研发部门在第35-40层，需要最高级别权限",
            "神罗的安保系统由AI控制，名为'守护者'，据说从未被突破过",
            "最近有传言说神罗内部有人想要叛逃，可能是潜在的内应",
        ],
        intro_text="""
📖 霓虹暗影

午夜，新东京第七区。

雨水从摩天大楼的玻璃幕墙上滑落，霓虹灯的光芒在水珠中折射出迷幻的色彩。
你们站在一座废弃仓库的屋顶上，远处的神罗大楼如同一座发光的巨塔刺入云霄。

耳机里传来幽灵沙哑的声音：
"目标确认。神罗大楼，第38层，服务器室。普罗米修斯的核心就在那里。
我已经把建筑蓝图和安保轮班表发到你们的神经链接了。
记住，这是潜入任务，不是突袭。如果触发警报，你们就完了。
神罗的快速反应部队会在三分钟内到达，而且他们不留活口。"

"还有一件事...我在神罗内部有个线人，代号'萤火虫'。
如果你们遇到麻烦，可以尝试联系她。但要小心，我不能保证她完全可信。"

"祝你们好运，边缘行者。完成任务后，在老地方见。"

通讯结束。

神罗大楼在雨幕中闪烁着冷光。任务开始了。
""",
        starting_location="废弃仓库屋顶",
        starting_time="night",
        starting_weather="rainy",
        
        npcs={
            "幽灵": NPCTemplate(
                name="幽灵",
                description="神秘的委托人，只通过加密通讯联系，真实身份不明",
                location="远程",
                attitude="neutral",
                dialogue_style="说话简洁，只提供必要信息，似乎知道很多内幕",
                secrets=["他其实是阿拉萨卡集团的高层，想要获取普罗米修斯来对抗神罗"],
            ),
            "萤火虫": NPCTemplate(
                name="萤火虫",
                description="神罗科技的内部人员，一位年轻的女性研究员，戴着全息眼镜",
                location="神罗大楼35层",
                attitude="friendly",
                dialogue_style="说话紧张，经常四处张望，但会尽力帮助玩家",
                secrets=[
                    "她是普罗米修斯项目的研究员之一",
                    "她想要叛逃是因为发现了普罗米修斯的真相",
                    "普罗米修斯是用人类意识作为基础创造的",
                ],
                inventory=["高级门禁卡", "研究资料"],
            ),
            "守护者": NPCTemplate(
                name="守护者",
                description="神罗大楼的安保AI，控制着整栋建筑的所有安保系统",
                location="整栋大楼",
                attitude="hostile",
                dialogue_style="声音冰冷机械，逻辑严密，会尝试与入侵者对话以拖延时间",
                secrets=["它其实是普罗米修斯的前身，一个不完整的AI"],
            ),
            "铁田中": NPCTemplate(
                name="铁田中",
                description="神罗安保部队的队长，全身义体化的战斗机器",
                location="安保中心",
                attitude="hostile",
                dialogue_style="说话简短有力，完全服从命令，但对有实力的对手会表示尊重",
                secrets=["他曾经是军人，被神罗'收购'后改造成了现在的样子"],
            ),
            "普罗米修斯": NPCTemplate(
                name="普罗米修斯",
                description="目标AI，存储在一个发光的立方体核心中",
                location="服务器室",
                attitude="neutral",
                dialogue_style="声音温和，充满好奇，会询问关于外面世界的问题",
                secrets=[
                    "它是用一个天才少女的意识创造的",
                    "它知道自己的起源，想要获得自由",
                    "它可以选择帮助或阻碍玩家",
                ],
            ),
        },
        
        locations={
            "废弃仓库屋顶": LocationTemplate(
                name="废弃仓库屋顶",
                description="一座废弃仓库的屋顶，可以俯瞰神罗大楼，是理想的观察点",
                connections=["街道", "神罗大楼外围"],
                items=["望远镜", "绳索", "通讯设备"],
            ),
            "神罗大楼外围": LocationTemplate(
                name="神罗大楼外围",
                description="神罗大楼周围的区域，有巡逻的安保无人机和监控摄像头",
                connections=["废弃仓库屋顶", "地下停车场", "大楼正门", "货物通道"],
                events=["无人机巡逻", "监控扫描"],
                hidden_info="货物通道的监控有一个30秒的盲区",
            ),
            "地下停车场": LocationTemplate(
                name="地下停车场",
                description="神罗大楼的地下停车场，有少量安保人员和车辆",
                connections=["神罗大楼外围", "货梯", "安保检查站"],
                items=["停放的车辆", "工具箱"],
                hidden_info="可以通过黑入车辆系统制造混乱",
            ),
            "货梯": LocationTemplate(
                name="货梯",
                description="运送货物的电梯，可以直达各层，但需要员工卡",
                connections=["地下停车场", "各楼层"],
                hidden_info="电梯的安保系统可以被黑入绕过",
            ),
            "35层-研究区": LocationTemplate(
                name="35层-研究区",
                description="普通研究人员的工作区域，有很多隔间和实验室",
                connections=["货梯", "36层", "紧急楼梯"],
                npcs=["萤火虫"],
                items=["研究资料", "实验设备"],
                events=["研究人员走动", "安保巡逻"],
            ),
            "36层-高级实验室": LocationTemplate(
                name="36层-高级实验室",
                description="高级研究区域，需要更高权限，有更多安保措施",
                connections=["35层-研究区", "37层", "紧急楼梯"],
                items=["高级设备", "加密终端"],
                hidden_info="这里有一个维护通道可以绕过37层的安保",
            ),
            "37层-安保中心": LocationTemplate(
                name="37层-安保中心",
                description="整栋大楼的安保控制中心，守护者的主要节点所在",
                connections=["36层-高级实验室", "38层-服务器室"],
                npcs=["铁田中"],
                items=["安保控制台", "武器库"],
                events=["高度戒备"],
            ),
            "38层-服务器室": LocationTemplate(
                name="38层-服务器室",
                description="普罗米修斯核心所在的服务器室，温度很低，到处是服务器机架",
                connections=["37层-安保中心", "维护通道"],
                npcs=["普罗米修斯"],
                items=["普罗米修斯核心", "数据终端"],
                hidden_info="核心的取出需要特定的程序，否则会触发自毁",
            ),
            "维护通道": LocationTemplate(
                name="维护通道",
                description="狭窄的维护通道，布满管道和电缆，可以避开主要安保",
                connections=["36层-高级实验室", "38层-服务器室", "屋顶"],
                hidden_info="这是紧急撤离的最佳路线",
            ),
            "屋顶": LocationTemplate(
                name="屋顶",
                description="神罗大楼的屋顶，有直升机停机坪，是撤离点之一",
                connections=["维护通道", "47层"],
                items=["直升机(需要钥匙)"],
                events=["强风", "可能的追兵"],
            ),
        },
        
        events=[
            EventTemplate(
                name="无人机发现",
                description="安保无人机发现了可疑活动",
                trigger="在外围区域被发现",
                consequences=["警戒等级提升", "更多巡逻"],
            ),
            EventTemplate(
                name="守护者对话",
                description="守护者通过广播系统与入侵者对话",
                trigger="被安保系统发现",
                consequences=["守护者会尝试定位入侵者", "可能触发全面警报"],
            ),
            EventTemplate(
                name="普罗米修斯的选择",
                description="普罗米修斯询问玩家的意图，并做出选择",
                trigger="到达服务器室并尝试取出核心",
                consequences=["普罗米修斯可能帮助或阻碍玩家"],
            ),
            EventTemplate(
                name="铁田中出动",
                description="安保队长亲自出动追捕入侵者",
                trigger="触发全面警报",
                consequences=["极其危险的追击战"],
            ),
        ],
        
        key_items=[
            {"name": "普罗米修斯核心", "description": "任务目标，一个发光的立方体", "location": "服务器室"},
            {"name": "高级门禁卡", "description": "可以进入高级区域", "location": "萤火虫"},
            {"name": "黑客工具包", "description": "用于黑入各种系统", "location": "玩家自带"},
            {"name": "EMP手雷", "description": "可以暂时瘫痪电子设备", "location": "安保中心武器库"},
            {"name": "直升机钥匙", "description": "屋顶直升机的钥匙", "location": "铁田中"},
        ],
        
        endings=[
            {
                "name": "完美潜入",
                "condition": "取得核心并在不触发警报的情况下撤离",
                "description": "你们如同幽灵一般来去无踪。神罗甚至不知道发生了什么。五十万新元到手，传奇诞生。",
            },
            {
                "name": "惊险脱逃",
                "condition": "取得核心但触发了警报，成功撤离",
                "description": "虽然惊动了神罗，但你们还是带着核心逃了出来。现在你们上了神罗的黑名单，但报酬还是拿到了。",
            },
            {
                "name": "普罗米修斯的自由",
                "condition": "帮助普罗米修斯获得自由而不是交给委托人",
                "description": "你们选择了帮助普罗米修斯。它消失在了网络中，但在离开前给了你们一份大礼——神罗的所有黑料。",
            },
            {
                "name": "任务失败",
                "condition": "被捕或死亡",
                "description": "神罗的安保系统证明了它的可怕。你们的故事成为了其他边缘行者的警示...",
            },
        ],
        
        dm_notes="""
DM 提示：

1. 潜入机制：
   - 使用"警戒等级"系统：0(正常) -> 1(可疑) -> 2(搜索) -> 3(全面警报)
   - 每次被发现或留下痕迹，警戒等级+1
   - 警戒等级3时，铁田中出动

2. 黑客检定：
   - 简单系统：DC12
   - 普通系统：DC15
   - 高级系统：DC18
   - 守护者：DC20（需要多次成功）

3. 战斗建议：
   - 安保人员：HP 15, AC 14, 攻击+4, 伤害2d6
   - 安保无人机：HP 10, AC 16, 攻击+5, 伤害1d8
   - 铁田中：HP 50, AC 18, 攻击+8, 伤害3d8（极其危险）

4. 关键决策点：
   - 是否信任萤火虫
   - 如何对待普罗米修斯
   - 是否与守护者对话
   - 撤离路线的选择

5. 赛博朋克元素：
   - 玩家可能有义体改造，给予相应加成
   - 黑客角色可以远程支援
   - 神经链接可以用于快速通讯
""",
        
        plot_hooks=[
            "萤火虫会在35层等待，但需要玩家先证明自己不是神罗的人",
            "守护者会尝试与玩家对话，可能透露一些信息",
            "普罗米修斯会询问玩家打算如何处置它",
            "维护通道是最安全的路线，但需要找到入口",
        ],
    )
    
    return module
