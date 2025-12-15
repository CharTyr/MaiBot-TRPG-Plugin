"""
预设模组：幽灵庄园
一个经典的克苏鲁/哥特恐怖风格短篇模组
"""

from ..base import ModuleBase, ModuleInfo, NPCTemplate, LocationTemplate, EventTemplate


def create_module() -> ModuleBase:
    """创建幽灵庄园模组"""
    
    info = ModuleInfo(
        id="haunted_mansion",
        name="幽灵庄园",
        description="一座废弃多年的维多利亚式庄园，据说藏着不为人知的秘密。当地人都说，那里闹鬼...",
        author="MaiBot TRPG Team",
        version="1.0.0",
        genre="horror",
        difficulty="normal",
        player_count="2-4",
        duration="2-3小时",
        tags=["恐怖", "调查", "克苏鲁", "短篇"],
    )
    
    module = ModuleBase(
        info=info,
        world_name="幽灵庄园",
        world_background="""
1923年，美国新英格兰地区。

布莱克伍德庄园坐落在阿卡姆镇郊外的山丘上，这座维多利亚式的宏伟建筑已经废弃了整整二十年。
1903年的那个雨夜，庄园的主人埃德加·布莱克伍德和他的妻子伊莎贝拉在一场神秘的火灾中丧生，
他们的女儿艾米莉亚则从此下落不明。

当地人都说庄园闹鬼，夜晚能看到窗户里有幽灵般的光芒闪烁。
最近，一位古董商在拍卖会上购得了这座庄园，并雇佣了你们前去调查和清点庄园内的物品。

但你们很快就会发现，这座庄园隐藏的秘密远比想象中更加黑暗...
""",
        lore=[
            "布莱克伍德家族是当地的名门望族，据说他们的财富来源于与某种'古老存在'的交易",
            "埃德加·布莱克伍德是一位狂热的神秘学研究者，收藏了大量禁忌书籍",
            "1903年的火灾只烧毁了庄园的东翼，但整座庄园都被封锁了",
            "当地人说，每逢满月之夜，能听到庄园里传来女孩的哭声",
            "庄园的地下室据说通往一个古老的洞穴系统",
        ],
        intro_text="""
📖 幽灵庄园

雨夜，你们的汽车在泥泞的山路上艰难前行。

透过雨幕，布莱克伍德庄园的轮廓逐渐显现——一座哥特式的三层建筑，
尖塔刺破阴沉的天空，破碎的窗户像是空洞的眼眶凝视着来访者。

庄园的铁门锈迹斑斑，却诡异地半开着，仿佛在邀请你们进入。

当你们走近大门时，一道闪电划破夜空，照亮了庄园的正面——
你们似乎看到三楼的窗户后有一个苍白的人影一闪而过...

冒险开始了。你们要进入庄园吗？
""",
        starting_location="庄园大门",
        starting_time="night",
        starting_weather="stormy",
        
        npcs={
            "艾米莉亚的幽灵": NPCTemplate(
                name="艾米莉亚的幽灵",
                description="一个穿着白色睡裙的小女孩幽灵，约8岁的样子，面容苍白但并不可怕",
                location="三楼走廊",
                attitude="neutral",
                dialogue_style="说话轻柔，经常说一些谜语般的话，似乎在试图传达什么信息",
                secrets=[
                    "她知道父亲在地下室进行的仪式",
                    "她知道真正的凶手是谁",
                    "她被困在庄园里，需要有人帮她完成未竟之事",
                ],
            ),
            "管家詹姆斯": NPCTemplate(
                name="管家詹姆斯",
                description="一个年迈的幽灵，穿着褪色的燕尾服，举止依然保持着仆人的恭敬",
                location="大厅",
                attitude="friendly",
                dialogue_style="说话正式有礼，会提供一些关于庄园的信息，但对某些话题讳莫如深",
                secrets=[
                    "他目睹了那晚发生的一切",
                    "他知道密室的位置",
                ],
                inventory=["生锈的钥匙"],
            ),
            "埃德加的怨灵": NPCTemplate(
                name="埃德加的怨灵",
                description="一个被黑暗力量扭曲的恐怖存在，曾经是庄园的主人",
                location="地下室",
                attitude="hostile",
                dialogue_style="声音扭曲，混杂着多种语言，充满疯狂",
                secrets=[
                    "他召唤了某种古老的存在",
                    "他为了永生献祭了自己的家人",
                ],
            ),
        },
        
        locations={
            "庄园大门": LocationTemplate(
                name="庄园大门",
                description="锈迹斑斑的铁艺大门，两侧是长满青苔的石柱，上面雕刻着奇怪的符文",
                connections=["前院", "外部道路"],
                items=["褪色的家族徽章"],
                hidden_info="石柱上的符文是某种古老的封印，似乎在阻止什么东西离开庄园",
            ),
            "前院": LocationTemplate(
                name="前院",
                description="杂草丛生的花园，中央有一座干涸的喷泉，雕像是一个哭泣的天使",
                connections=["庄园大门", "正门大厅", "东翼废墟", "西翼入口"],
                items=["枯萎的玫瑰", "破碎的园艺工具"],
                hidden_info="喷泉底部有一个暗格，里面藏着一本日记",
            ),
            "正门大厅": LocationTemplate(
                name="正门大厅",
                description="宏伟但破败的大厅，双层挑高，墙上挂着蒙尘的肖像画，一盏巨大的水晶吊灯摇摇欲坠",
                connections=["前院", "餐厅", "图书室", "二楼走廊"],
                npcs=["管家詹姆斯"],
                items=["蒙尘的烛台", "破碎的花瓶"],
                events=["吊灯摇晃", "肖像画的眼睛似乎在动"],
            ),
            "图书室": LocationTemplate(
                name="图书室",
                description="四面墙都是书架，大部分书籍已经腐烂，但有一个上锁的玻璃柜里保存着几本看起来很古老的书",
                connections=["正门大厅"],
                items=["腐烂的书籍", "放大镜", "神秘的笔记"],
                hidden_info="玻璃柜里有一本《死灵之书》的抄本，书架后面有一个通往密室的暗门",
            ),
            "密室": LocationTemplate(
                name="密室",
                description="一个狭小的房间，墙上画满了奇怪的符号，中央有一个石制祭坛",
                connections=["图书室"],
                items=["仪式匕首", "黑色蜡烛", "神秘卷轴"],
                hidden_info="这里是埃德加进行召唤仪式的地方，祭坛上有干涸的血迹",
            ),
            "二楼走廊": LocationTemplate(
                name="二楼走廊",
                description="昏暗的走廊，地毯已经腐烂，墙纸剥落，两侧是紧闭的房门",
                connections=["正门大厅", "主卧室", "艾米莉亚的房间", "三楼走廊"],
                events=["脚步声", "门自己打开"],
            ),
            "艾米莉亚的房间": LocationTemplate(
                name="艾米莉亚的房间",
                description="一个小女孩的房间，布满灰尘但保存相对完好，床上放着一个破旧的布娃娃",
                connections=["二楼走廊"],
                items=["布娃娃", "儿童画", "日记本"],
                hidden_info="日记本记录了艾米莉亚在火灾前几天看到的奇怪事情",
            ),
            "三楼走廊": LocationTemplate(
                name="三楼走廊",
                description="最高层的走廊，窗户破碎，冷风呼啸，尽头是一扇紧锁的门",
                connections=["二楼走廊", "阁楼"],
                npcs=["艾米莉亚的幽灵"],
            ),
            "地下室": LocationTemplate(
                name="地下室",
                description="阴暗潮湿的地下室，空气中弥漫着腐败的气息，墙上有火把的痕迹",
                connections=["正门大厅", "古老洞穴"],
                npcs=["埃德加的怨灵"],
                items=["生锈的链条", "破碎的仪式器具"],
                events=["低语声", "温度骤降"],
            ),
            "古老洞穴": LocationTemplate(
                name="古老洞穴",
                description="一个天然形成的洞穴，墙壁上有史前的壁画，中央是一个深不见底的黑暗深渊",
                connections=["地下室"],
                hidden_info="这里是'古老存在'沉睡的地方，深渊中传来令人发狂的低语",
            ),
        },
        
        events=[
            EventTemplate(
                name="初遇幽灵",
                description="当玩家首次进入大厅时，会看到管家詹姆斯的幽灵",
                trigger="进入正门大厅",
            ),
            EventTemplate(
                name="艾米莉亚的求助",
                description="艾米莉亚的幽灵出现，用谜语暗示玩家去寻找真相",
                trigger="进入三楼走廊",
            ),
            EventTemplate(
                name="埃德加苏醒",
                description="当玩家找到关键证据后，埃德加的怨灵会苏醒并追杀玩家",
                trigger="发现密室或阅读禁忌书籍",
            ),
        ],
        
        key_items=[
            {"name": "艾米莉亚的日记", "description": "记录了火灾前几天的异常事件", "location": "艾米莉亚的房间"},
            {"name": "生锈的钥匙", "description": "可以打开密室的门", "location": "管家詹姆斯"},
            {"name": "神秘卷轴", "description": "记载了封印仪式的方法", "location": "密室"},
            {"name": "家族徽章", "description": "布莱克伍德家族的徽章，可能有特殊用途", "location": "庄园大门"},
        ],
        
        endings=[
            {
                "name": "真相大白",
                "condition": "找到所有证据，了解真相，帮助艾米莉亚安息",
                "description": "玩家揭露了埃德加的罪行，完成封印仪式，让所有幽灵得到安息。庄园恢复平静。",
            },
            {
                "name": "仓皇逃离",
                "condition": "在没有完成调查的情况下逃离庄园",
                "description": "玩家逃出了庄园，但真相永远被埋葬。据说之后庄园的闹鬼事件更加频繁了...",
            },
            {
                "name": "永远留下",
                "condition": "被埃德加的怨灵杀死或陷入疯狂",
                "description": "玩家成为了庄园新的幽灵，永远徘徊在这座被诅咒的建筑中...",
            },
        ],
        
        dm_notes="""
DM 提示：

1. 氛围营造：
   - 多使用感官描写（声音、气味、温度变化）
   - 让玩家时刻感到被注视
   - 适时使用跳吓但不要过度

2. 节奏控制：
   - 前期以探索和收集信息为主
   - 中期揭示部分真相，增加紧张感
   - 后期是与埃德加的对抗

3. 关键检定：
   - 图书室调查：智力检定 DC12
   - 发现暗门：感知检定 DC15
   - 抵抗恐惧：意志检定 DC13
   - 封印仪式：需要找到所有关键道具

4. 战斗建议：
   - 埃德加的怨灵不能被物理攻击伤害
   - 只有完成封印仪式才能消灭他
   - 如果玩家选择战斗，让他们意识到需要另寻他法
""",
        
        plot_hooks=[
            "管家詹姆斯会暗示图书室有秘密",
            "艾米莉亚的幽灵会引导玩家找到她的日记",
            "日记中提到父亲经常去地下室",
            "密室中的卷轴记载了封印方法",
        ],
    )
    
    return module
