"""
预设模组：龙穴探险
一个经典的奇幻冒险模组，适合新手
"""

from ..base import ModuleBase, ModuleInfo, NPCTemplate, LocationTemplate, EventTemplate


def create_module() -> ModuleBase:
    """创建龙穴探险模组"""
    
    info = ModuleInfo(
        id="dragon_cave",
        name="龙穴探险",
        description="传说中的巨龙斯莫格已经沉睡百年，它的巢穴中藏着无尽的宝藏。你们能成功取得宝藏并活着离开吗？",
        author="MaiBot TRPG Team",
        version="1.0.0",
        genre="fantasy",
        difficulty="easy",
        player_count="3-5",
        duration="2-4小时",
        tags=["奇幻", "冒险", "战斗", "宝藏", "新手友好"],
    )
    
    module = ModuleBase(
        info=info,
        world_name="龙穴探险",
        world_background="""
在艾尔德兰大陆的东方，矗立着一座被称为"孤峰"的巨山。

传说一百年前，一头名为斯莫格的红龙袭击了繁华的河谷镇，
将整座城镇化为灰烬，并将所有财宝掠夺一空，带回了它在孤峰的巢穴。

从那以后，再也没有人敢接近孤峰。

但最近，一位老矮人带来了消息：斯莫格已经陷入了龙族特有的百年沉睡。
这是取回宝藏的绝佳机会！

河谷镇的幸存者后裔们凑齐了一笔赏金，悬赏勇敢的冒险者前往龙穴，
取回他们祖先的传家宝——月光宝石项链。

当然，如果你们能顺便带回一些其他宝藏，那也是你们应得的报酬...
""",
        lore=[
            "斯莫格是一头古老的红龙，据说已经活了超过五百年",
            "龙穴的入口被斯莫格用魔法封印，但沉睡时封印会减弱",
            "传说龙穴中不只有宝藏，还有斯莫格收集的魔法物品",
            "孤峰山中还住着一群哥布林，它们崇拜斯莫格为神",
            "月光宝石项链是精灵女王赠予河谷镇领主的礼物，具有魔法力量",
        ],
        intro_text="""
📖 龙穴探险

清晨的阳光照耀着你们的营地，孤峰的轮廓在晨雾中若隐若现。

经过三天的跋涉，你们终于来到了传说中的龙穴入口——
一个巨大的洞口，足以让一头成年巨龙自由进出。

洞口周围散落着巨大的骨骸，有些看起来像是牛羊，
但也有一些...明显是人类的。

一股温热的气流从洞穴深处涌出，带着硫磺的气味。

老矮人巴林站在你们身旁，捋着他的白胡子说道：
"就是这里了，年轻人们。记住，龙在沉睡，但它的仆从可能还醒着。
小心那些哥布林，还有...如果你们听到龙的鼾声变了，就赶紧跑。"

他递给你们一张泛黄的地图："这是我年轻时画的，希望还能用。祝你们好运！"

冒险开始了。你们准备好进入龙穴了吗？
""",
        starting_location="龙穴入口",
        starting_time="day",
        starting_weather="sunny",
        
        npcs={
            "巴林": NPCTemplate(
                name="巴林",
                description="一位年迈的矮人，白发白须，曾经是著名的冒险者，现在是河谷镇的顾问",
                location="龙穴入口",
                attitude="friendly",
                dialogue_style="说话慢条斯理，喜欢讲述过去的冒险故事，会给予有用的建议",
                secrets=["他年轻时曾进入过龙穴，但被斯莫格发现后仓皇逃离"],
                inventory=["旧地图", "治疗药水x2"],
            ),
            "哥布林首领格里克": NPCTemplate(
                name="哥布林首领格里克",
                description="一只比普通哥布林高大的哥布林，戴着用龙鳞制成的头盔",
                location="哥布林营地",
                attitude="hostile",
                dialogue_style="说话尖锐刺耳，自大且残忍，但也贪婪，可以被贿赂",
                secrets=["他知道一条通往宝藏室的秘密通道"],
                inventory=["龙鳞头盔", "生锈的弯刀", "钥匙"],
            ),
            "被囚禁的精灵": NPCTemplate(
                name="艾拉",
                description="一位年轻的精灵女性，被哥布林囚禁，衣衫褴褛但眼神坚定",
                location="哥布林营地",
                attitude="friendly",
                dialogue_style="说话优雅，对帮助她的人心存感激，了解一些关于龙穴的知识",
                secrets=["她是来寻找月光宝石项链的，那是她祖先的遗物"],
            ),
            "沉睡的斯莫格": NPCTemplate(
                name="斯莫格",
                description="一头巨大的红龙，鳞片如烈焰般赤红，即使沉睡也散发着可怕的威压",
                location="宝藏大厅",
                attitude="hostile",
                dialogue_style="如果被吵醒，声音如雷鸣般震耳，傲慢且残忍",
                secrets=["它的左胸有一块鳞片缺失，那是它唯一的弱点"],
            ),
        },
        
        locations={
            "龙穴入口": LocationTemplate(
                name="龙穴入口",
                description="一个巨大的洞口，周围散落着骨骸，温热的气流从深处涌出",
                connections=["外部山路", "前厅"],
                npcs=["巴林"],
                items=["散落的骨骸", "破旧的武器"],
            ),
            "前厅": LocationTemplate(
                name="前厅",
                description="一个宽阔的洞穴，地面被无数爪痕划过，墙壁上有火焰灼烧的痕迹",
                connections=["龙穴入口", "左侧通道", "右侧通道", "主通道"],
                items=["烧焦的盾牌", "金币(3枚)"],
                events=["远处传来哥布林的说话声"],
            ),
            "左侧通道": LocationTemplate(
                name="左侧通道",
                description="一条狭窄的通道，墙壁潮湿，有水滴声",
                connections=["前厅", "地下河"],
                hidden_info="通道中有一个陷阱，需要敏捷检定DC12来避开",
            ),
            "地下河": LocationTemplate(
                name="地下河",
                description="一条地下河流经此处，河水冰冷刺骨，对岸似乎有什么东西在闪光",
                connections=["左侧通道"],
                items=["魔法戒指(对岸)"],
                hidden_info="河水中有盲眼鱼，无害但会惊扰到涉水者",
            ),
            "右侧通道": LocationTemplate(
                name="右侧通道",
                description="一条较宽的通道，地上有很多脚印，似乎经常有生物经过",
                connections=["前厅", "哥布林营地"],
            ),
            "哥布林营地": LocationTemplate(
                name="哥布林营地",
                description="一个被哥布林占据的洞穴，到处是垃圾和骨头，中央燃烧着篝火",
                connections=["右侧通道", "秘密通道"],
                npcs=["哥布林首领格里克", "艾拉"],
                items=["哥布林的战利品", "钥匙", "食物"],
                events=["哥布林巡逻"],
                hidden_info="营地后方有一条秘密通道通往宝藏大厅",
            ),
            "主通道": LocationTemplate(
                name="主通道",
                description="通往龙穴深处的主要通道，宽阔到可以让巨龙通过，地面有深深的爪痕",
                connections=["前厅", "守卫室", "宝藏大厅"],
                events=["能听到远处传来的沉重呼吸声"],
            ),
            "守卫室": LocationTemplate(
                name="守卫室",
                description="曾经是守卫休息的地方，现在只剩下破旧的家具和骷髅",
                connections=["主通道"],
                items=["旧武器架", "生锈的剑", "治疗药水"],
                hidden_info="骷髅手中握着一张纸条，记录了龙的弱点",
            ),
            "宝藏大厅": LocationTemplate(
                name="宝藏大厅",
                description="一个巨大的洞穴，堆满了金币、珠宝和各种珍贵物品，中央是沉睡的巨龙斯莫格",
                connections=["主通道", "秘密通道"],
                npcs=["沉睡的斯莫格"],
                items=["金币(无数)", "珠宝", "魔法物品", "月光宝石项链"],
                events=["龙的鼾声", "宝藏堆移动的声音"],
                hidden_info="月光宝石项链在龙的右爪下",
            ),
            "秘密通道": LocationTemplate(
                name="秘密通道",
                description="一条狭窄的通道，只有人类大小的生物才能通过，龙无法追击",
                connections=["哥布林营地", "宝藏大厅"],
                hidden_info="这是逃离宝藏大厅的最佳路线",
            ),
        },
        
        events=[
            EventTemplate(
                name="哥布林伏击",
                description="一群哥布林从暗处跳出，试图伏击玩家",
                trigger="进入右侧通道",
                consequences=["战斗开始", "可能惊动更多哥布林"],
            ),
            EventTemplate(
                name="龙的翻身",
                description="斯莫格在睡梦中翻了个身，引起宝藏堆的移动",
                trigger="在宝藏大厅待太久或发出太大声响",
                consequences=["需要敏捷检定避开滚落的金币", "龙可能醒来"],
            ),
            EventTemplate(
                name="龙的苏醒",
                description="斯莫格睁开了眼睛！",
                trigger="在宝藏大厅发出巨大声响或触碰龙身",
                consequences=["必须立即逃跑", "龙会喷火追击"],
            ),
        ],
        
        key_items=[
            {"name": "月光宝石项链", "description": "任务目标，一条散发着柔和银光的项链", "location": "宝藏大厅"},
            {"name": "旧地图", "description": "巴林提供的龙穴地图", "location": "巴林"},
            {"name": "龙鳞头盔", "description": "格里克的头盔，提供火焰抗性", "location": "哥布林首领格里克"},
            {"name": "魔法戒指", "description": "隐身戒指，每天可使用一次", "location": "地下河"},
            {"name": "秘密通道钥匙", "description": "打开秘密通道的钥匙", "location": "哥布林首领格里克"},
        ],
        
        endings=[
            {
                "name": "完美成功",
                "condition": "取得月光宝石项链并安全离开，没有惊醒斯莫格",
                "description": "你们成功取得了宝藏并安全离开！河谷镇的人们将你们视为英雄，丰厚的赏金和荣誉属于你们！",
            },
            {
                "name": "惊险逃脱",
                "condition": "取得月光宝石项链但惊醒了斯莫格，成功逃离",
                "description": "虽然惊醒了巨龙，但你们还是成功逃了出来！斯莫格的怒吼在身后回响，但宝藏已经到手！",
            },
            {
                "name": "空手而归",
                "condition": "没有取得月光宝石项链但安全离开",
                "description": "这次冒险没有成功，但至少你们活着回来了。也许下次会有更好的机会...",
            },
            {
                "name": "葬身龙穴",
                "condition": "被斯莫格杀死",
                "description": "巨龙的怒火吞噬了一切。你们的故事将成为警示后人的传说...",
            },
        ],
        
        dm_notes="""
DM 提示：

1. 难度调整：
   - 这是一个新手友好的模组，可以根据玩家水平调整哥布林数量
   - 如果玩家表现出色，可以让他们获得额外奖励
   - 如果玩家陷入困境，可以让艾拉提供帮助

2. 战斗建议：
   - 哥布林：HP 7, AC 12, 攻击+3, 伤害1d6
   - 哥布林首领：HP 21, AC 14, 攻击+4, 伤害1d8+2
   - 斯莫格不应该被直接战斗击败，重点是逃跑

3. 关键检定：
   - 潜行通过哥布林营地：敏捷检定 DC13
   - 在宝藏大厅保持安静：敏捷检定 DC15
   - 说服格里克：魅力检定 DC14（需要贿赂）
   - 渡过地下河：力量检定 DC10

4. 奖励建议：
   - 完成任务：500金币 + 月光宝石项链的感谢
   - 额外宝藏：每人可以带走价值100金币的财宝
   - 魔法物品：隐身戒指、龙鳞头盔
""",
        
        plot_hooks=[
            "巴林会建议先探索侧面通道，避开哥布林",
            "艾拉如果被救出，会告诉玩家秘密通道的存在",
            "守卫室的纸条暗示龙的弱点",
            "格里克可以被贿赂交出钥匙",
        ],
    )
    
    return module
