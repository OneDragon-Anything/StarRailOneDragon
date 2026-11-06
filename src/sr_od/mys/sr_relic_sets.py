"""米游社遗器套装快照常量与套装效果助手。

设计出处：changes/mys-relic-sets/design.md §1（数据层，用户裁定禁 JSON 数据
文件、数据写代码）。映射内容的权威快照：官方 wiki 遗器频道 2026-11-04 抓取
（版本 3.7；62 套 = 隧洞 34 + 位面饰品 28、件名 192 唯一、2 件效果 62/62、
4 件效果 34/34 齐备、planner 实测件名覆盖 100%）——本模块固化其内容，
禁自行增删改；固化后本模块即唯一权威载体（快照 JSON 为易失本地件）。

set_id 与单件 desc（2026-11-05 增量固化）：
- ``set_id`` = 游戏内部套装 ID，双源锚定：①米游社 avatar/info 遗器件 id
  实证（tid 公式 60000/50000+set_id*10+pos，43 套零冲突）；②归档图标
  ``iconrelic_<set_id>_<pos>.webp`` 文件名 ↔ wiki 单件图逐套对照仲裁
  （其余 19 套 + 顺序律全量吻合：set_id 按实装顺序连续分配，隧洞 101 起、
  位面 301 起，本模块排列序 = 实装序）。
- ``desc`` = 单件描述（官方 wiki 原文透传）；``obtain`` = 套装获取途径。
  wiki 词条偶有错字/缺段（实测 8 套 effects/件名与已固化常量不一致）——
  effects 与件名一律以本模块原有常量为准，wiki 只作新增字段来源。

图标归档：``assets/game_data/relic_icons/iconrelic_<set_id>_<pos>.webp``
（192 件全量，官方图标转档归档；寻址公式见 ``icon_webp_path``）。

版本刷新工序：游戏新版本后重跑 wiki 抓取生成新快照 → 与下方 RELIC_SETS
逐条 diff → 人工审阅后更新常量；新套装 set_id 按顺序律续排（隧洞/位面各
自分段连续），图标按归档命名增量入库；新版本套装未及固化时由
``resolve_set_name`` 兜底（warning 不抛异常），勿临时塞未经抓取核验的数据。

模块纪律：零外部 IO、零状态——纯常量 + 纯函数（同 sr_codes 模块纪律）。
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from one_dragon.utils.log_utils import log


@dataclass(frozen=True)
class SrRelicPieceDef:
    """套装单件定义（快照 pieces[].{name, pos} 固化 + desc 增量）。

    pos 坐标系：game_record 件 id 公式 60000+set_id*10+pos 的 pos 位——
    隧洞 1=头部 2=手部 3=躯干 4=脚部、位面 5=位面球 6=连结绳（与
    sr_codes.RELIC_POS_CN 同源）；取值时机 = 生成期快照（固化于常量，恒稳）。
    """

    name: str
    pos: int
    desc: str = ''
    """单件描述（官方 wiki 原文透传，纯展示文本；识别不依赖）。"""


@dataclass(frozen=True)
class RelicSetDef:
    """套装定义（快照 sets[] 固化 + set_id/obtain 增量）。

    Attributes:
        set_name: 官方套装全名（社区简称不入表；基准：「骇域漫游的信使」/
            「生命的翁瓦克」）。
        kind: ``'cavern'``=隧洞遗器（4 件套，2/4 件效果）、``'ornament'``=
            位面饰品（2 件套，仅 2 件效果，effects 无 ``'4'`` 键）。
        pieces: 全部件定义（隧洞 4 件 / 饰品 2 件，pos 见 SrRelicPieceDef）。
        effects: 套装效果文案，键 ``'2'``/``'4'``（官方 wiki 原文透传，
            不清洗富文本）。
        set_id: 游戏内部套装 ID（tid 公式 60000/50000+set_id*10+pos 的
            set_id 位；归档图标文件名同源——双源实证见模块 docstring；
            生成期快照，恒稳）。
        obtain: 套装获取途径（官方 wiki 原文透传，如副本名；纯展示）。
    """

    set_name: str
    kind: Literal['cavern', 'ornament']
    pieces: tuple[SrRelicPieceDef, ...]
    effects: Mapping[str, str]
    set_id: int = 0
    obtain: str = ''


RELIC_SETS: tuple[RelicSetDef, ...] = (
    # ---- 隧洞遗器（cavern，34 套，按 set_id 升序）----
    RelicSetDef(
        set_name='云无留迹的过客',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='过客的逢春木簪', pos=1, desc='枯木曾作发簪，枝梢有花苞初绽。而今往事已矣，花苞鎏金嵌入簪中，用以纪念新生的开始。'),
            SrRelicPieceDef(name='过客的游龙臂鞲', pos=2, desc='如水的珊瑚金与未知的兽革制成的腕甲，唯有龙脉一族的巧匠才能打造出这等非凡工艺。'),
            SrRelicPieceDef(name='过客的残绣风衣', pos=3, desc='长摆残破的古旧风衣，绣纹被剑痕撕碎。肉体会快速愈合，但外衣却不能，正如人的痛苦。'),
            SrRelicPieceDef(name='过客的冥途游履', pos=4, desc='—双经久耐用的短靴，曾踏遍诸多世界，出入死生。'),
        ),
        effects={
            '2': '治疗量提高10%。',
            '4': '在战斗开始时，立即为我方恢复1个战技点。',
        },
        set_id=101,
        obtain='漂泊之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='野穗伴行的快枪手',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='快枪手的野穗毡帽', pos=1, desc='—顶绑着野生麦穗的牛仔毡帽，传奇枪手奥克莱的标志。'),
            SrRelicPieceDef(name='快枪手的粗革手套', pos=2, desc='表面已经部分开裂的皮革手套，握枪处磨损尤其严重。'),
            SrRelicPieceDef(name='快枪手的猎风披肩', pos=3, desc='看上去是有民族风格的编制披肩，内衬部分编织了能够防弹的纤维。'),
            SrRelicPieceDef(name='快枪手的铆钉马靴', pos=4, desc='马靴有着V形剪裁的开口，看上去随性松弛，穿起来非常舒适。'),
        ),
        effects={
            '2': '攻击力提高12%。',
            '4': '使装备者的速度提高6%，普攻造成的伤害提高10%。',
        },
        set_id=102,
        obtain='漂泊之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='净庭教宗的圣骑士',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='圣骑的宽恕盔面', pos=1, desc='如同宗教石雕宽恕女神的面具头盔，用以隐藏自己的相貌。'),
            SrRelicPieceDef(name='圣骑的沉默誓环', pos=2, desc='装饰着教会纹样的银戒，镶嵌着看上去些许浑浊的宝石。'),
            SrRelicPieceDef(name='圣骑的肃穆胸甲', pos=3, desc='厚重的胸甲装饰着净庭教会鲜明的符号，关节处也都密不透风。'),
            SrRelicPieceDef(name='圣骑的秩序铁靴', pos=4, desc='净庭教会骑士的标准骑士长靴，脚后跟上刻印着简短的单词：「秩序」。'),
        ),
        effects={
            '2': '防御力提高15%。',
            '4': '使装备者提供的护盾量提高20%。',
        },
        set_id=103,
        obtain='圣颂之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='密林卧雪的猎人',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='雪猎的荒神兜帽', pos=1, desc='巨大的雪原熊头部毛皮做成的兜帽。毛皮似乎寄宿鬼神，刀枪不入。'),
            SrRelicPieceDef(name='雪猎的巨蜥手套', pos=2, desc='雪岩巨蜥的鳞爪与战术手套紧密缝合起来，可以在任何墙面上自由地攀爬悬挂。'),
            SrRelicPieceDef(name='雪猎的冰龙披风', pos=3, desc='由冰龙细鳞制作的披风，在奇妙光学折射下，近乎隐形。'),
            SrRelicPieceDef(name='雪猎的鹿皮软靴', pos=4, desc='麋鹿柔软的毛皮包裹着增强动力靴，在雪原，猎户的鞋底只会留下浅浅的印记。'),
        ),
        effects={
            '2': '冰属性伤害提高10%。',
            '4': '当装备者施放终结技时，暴击伤害提高25%，持续2回合。',
        },
        set_id=104,
        obtain='霜风之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='街头出身的拳王',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='拳王的冠军护头', pos=1, desc='防护效果极佳的拳击护头，与物件主人的脸型完美贴合。'),
            SrRelicPieceDef(name='拳王的重炮拳套', pos=2, desc='保养得极好的拳击手套，细微的破损并不影响实际的使用。'),
            SrRelicPieceDef(name='拳王的贴身护胸', pos=3, desc='拳击手的专业护胸，外罩和内衬垫相互组合，既保障了安全又不影响技术发挥。'),
            SrRelicPieceDef(name='拳王的弧步战靴', pos=4, desc='巧妙地将皮革和网结合，采用了厚鞋垫、薄鞋底的设计，保证了脚步灵活。'),
        ),
        effects={
            '2': '物理属性伤害提高10%。',
            '4': '当装备者施放攻击或受到攻击后，其在本场战斗中攻击力提高5%，最多叠加5层。',
        },
        set_id=105,
        obtain='迅拳之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='戍卫风雪的铁卫',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='铁卫的铸铁面盔', pos=1, desc='经过统一改造过的覆面头盔，通过内部的填充物使头部保持温暖。'),
            SrRelicPieceDef(name='铁卫的银鳞手甲', pos=2, desc='闪耀着银光的金属手甲，复合的机械结构深藏其中。'),
            SrRelicPieceDef(name='铁卫的旧制军服', pos=3, desc='熨烫妥帖的银鬃铁卫旧制军服，结实的排扣将布料压出褶痕。'),
            SrRelicPieceDef(name='铁卫的白银护胫', pos=4, desc='坚硬的白银色金属护胫，注重防护的同时，足够轻巧又保暖。'),
        ),
        effects={
            '2': '受到伤害降低8%。',
            '4': '回合开始时，如果装备者当前生命值百分比小于等于50%，则回复等同于自身生命上限8%的生命值，并恢复5点能量。',
        },
        set_id=106,
        obtain='睿治之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='熔岩锻铸的火匠',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='火匠的黑曜目镜', pos=1, desc='以漆黑焰晶打造的防护目镜，在镜片之下，激烈的火星迸裂也只不过是斑驳残影。'),
            SrRelicPieceDef(name='火匠的御火戒指', pos=2, desc='有着火焰标志的戒指，是火匠一族中最高荣誉的象征。'),
            SrRelicPieceDef(name='火匠的阻燃围裙', pos=3, desc='铁匠围裙没有多余的装饰，只有皮革纹理与家族标识清晰可见。'),
            SrRelicPieceDef(name='火匠的合金义肢', pos=4, desc='金属材质的义肢，表面上缠绕着火焰的立体花纹。'),
        ),
        effects={
            '2': '火属性伤害提高10%。',
            '4': '使装备者战技造成的伤害提高12%，并使施放终结技后的下一次攻击造成的火属性伤害提高12%。',
        },
        set_id=107,
        obtain='野焰之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='繁星璀璨的天才',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='天才的超距遥感', pos=1, desc='基于超距遥感技术制造出的通讯目镜，打破了传播介质与距离的束缚。'),
            SrRelicPieceDef(name='天才的频变捕手', pos=2, desc='装有精密的频变捕捉器的手套，能够对客观的声光振动进行直观地操作。'),
            SrRelicPieceDef(name='天才的元域深潜', pos=3, desc='启动后形似包裹全身的潜水服，将全身的神经信号实时传输至元域空间。'),
            SrRelicPieceDef(name='天才的引力漫步', pos=4, desc='穿戴式引力捕获装置，形似冰鞋，能在快速滑行时倒映出群星的光芒。'),
        ),
        effects={
            '2': '量子属性伤害提高10%。',
            '4': '当装备者对敌方目标造成伤害时，无视其10%的防御力。若目标拥有量子属性弱点，额外无视其10%的防御力。',
        },
        set_id=108,
        obtain='睿治之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='激奏雷电的乐队',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='乐队的偏光墨镜', pos=1, desc='主唱之一的詹尼斯所戴的经典款墨镜，镀铬镜片反射着蓝色的光芒。'),
            SrRelicPieceDef(name='乐队的巡演手绳', pos=2, desc='贝斯手席德的手绳，由巡演时的丝带手环编织而成，上面写着几句歌词。'),
            SrRelicPieceDef(name='乐队的钉刺皮衣', pos=3, desc='主唱之一的大卫在皮衣背面画上了白色的星星，它成为了乐队最后一张专辑的封面。'),
            SrRelicPieceDef(name='乐队的铆钉短靴', pos=4, desc='鼓手博纳姆的短靴，折射着舞台灯光的漆面上粘着铆钉尖刺。'),
        ),
        effects={
            '2': '雷属性伤害提高10%。',
            '4': '当装备者施放战技时，使装备者的攻击力提高20%，持续1回合。',
        },
        set_id=109,
        obtain='圣颂之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='晨昏交界的翔鹰',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='翔鹰的长喙头盔', pos=1, desc='高速飞行中使用的流体头盔，行似空渔鹰的鸟喙。'),
            SrRelicPieceDef(name='翔鹰的鹰击指环', pos=2, desc='卓越空渔人大师所佩戴的指环，空渔鹰双翅纹样紧抱手指。'),
            SrRelicPieceDef(name='翔鹰的翼装束带', pos=3, desc='连接扑翼装的腰带，金属支撑藏在粗麻束带中，柔软贴身。'),
            SrRelicPieceDef(name='翔鹰的绒羽绑带', pos=4, desc='飞行中确保腿部保暖的绑带，装饰着空渔鹰的翎羽。'),
        ),
        effects={
            '2': '风属性伤害提高10%。',
            '4': '当装备者施放终结技后，使其行动提前25%。',
        },
        set_id=110,
        obtain='霜风之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='流星追迹的怪盗',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='怪盗的千人假面', pos=1, desc='用以改变面貌的面具，结合精湛的演技便能以假乱真。'),
            SrRelicPieceDef(name='怪盗的绘纹手套', pos=2, desc='编入纳米材料的特殊手套，可即时编写手套表面纹样。'),
            SrRelicPieceDef(name='怪盗的纤钢爪钩', pos=3, desc='伪装成编织腰带的钢索，腰带卡扣里隐藏着挂钩和滑轮。'),
            SrRelicPieceDef(name='怪盗的流星快靴', pos=4, desc='一双辅助增强人体机能的靴子，帮助怪盗在楼宇之间大步流星。'),
        ),
        effects={
            '2': '击破特攻提高16%。',
            '4': '使装备者的击破特攻提高16%。当装备者击破敌方目标弱点后，恢复3点能量。',
        },
        set_id=111,
        obtain='迅拳之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='盗匪荒漠的废土客',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='废土客的呼吸面罩', pos=1, desc='能够过滤沙尘与辐射的面罩，像是由废弃呼吸器改造而来。'),
            SrRelicPieceDef(name='废土客的荒漠终端', pos=2, desc='能检测电离辐射气体的多功能垃圾，会讲垃圾话。'),
            SrRelicPieceDef(name='废土客的修士长袍', pos=3, desc='宽松的长袍，由传教士的款式改造而来。'),
            SrRelicPieceDef(name='废土客的动力腿甲', pos=4, desc='动力甲的腿部，废铁和旧电线制作的外骨骼。'),
        ),
        effects={
            '2': '虚数属性伤害提高10%。',
            '4': '装备者对陷入负面效果的敌方目标造成伤害时暴击率提高10%，对陷入禁锢状态的敌方目标造成伤害时暴击伤害提高20%。',
        },
        set_id=112,
        obtain='野焰之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='宝命长存的莳者',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='莳者的复明义眼', pos=1, desc='曾属于某人的机巧义眼，如今它被逐出主人的身体，百无一用。'),
            SrRelicPieceDef(name='莳者的机巧木手', pos=2, desc='专为长生种制造的机巧义肢，使用时无需侵入肉体。'),
            SrRelicPieceDef(name='莳者的承露羽衣', pos=3, desc='据古籍记载纺织的羽衣，它属于万古的妖人，亦或万人的救主。'),
            SrRelicPieceDef(name='莳者的天人丝履', pos=4, desc='一双鞋底薄如蝉翼的丝履，它的主人一定长久不曾用双脚行走了。'),
        ),
        effects={
            '2': '生命上限提高12%。',
            '4': '当装备者受到攻击或被我方目标消耗生命值后，暴击率提高8%，持续2回合，该效果最多叠加2层。',
        },
        set_id=113,
        obtain='药使之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='骇域漫游的信使',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='信使的全息目镜', pos=1, desc='外形酷似滑雪目镜，不仅能防眩光，还能看虚拟人直播。'),
            SrRelicPieceDef(name='信使的百变义手', pos=2, desc='可随便拆卸的机械义手，能够将指节像子弹一样发射出去。'),
            SrRelicPieceDef(name='信使的密信挎包', pos=3, desc='时尚的信使邮差包，添加了各种挂件，看上去有些可爱。'),
            SrRelicPieceDef(name='信使的酷跑板鞋', pos=4, desc='支持自由跑酷的滑板鞋，穿上去很舒服，仅此而已。'),
        ),
        effects={
            '2': '速度提高6%。',
            '4': '当装备者对我方目标施放终结技时，我方全体速度提高12%，持续1回合，该效果无法叠加。',
        },
        set_id=114,
        obtain='药使之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='毁烬焚骨的大公',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='大公的冥焰冠冕', pos=1, desc='不停燃烧的火焰冠冕，熊熊野心是它的不尽燃料。'),
            SrRelicPieceDef(name='大公的绒火指套', pos=2, desc='以火焰为绒毛的洁白手套，将暴戾藏于缎面之下。'),
            SrRelicPieceDef(name='大公的蒙恩长袍', pos=3, desc='一袭华美的袍，彰显长袍主人的端庄风雅。'),
            SrRelicPieceDef(name='大公的绅雅礼靴', pos=4, desc='经典而舒适的靴子，保养完好，造型挺括，修饰脚型。'),
        ),
        effects={
            '2': '追加攻击造成的伤害提高20%。',
            '4': '装备者施放追加攻击时，根据追加攻击造成伤害的次数，每次造成伤害时使装备者的攻击力提高6%，最多叠加8次，持续3回合。该效果在装备者下次施放追加攻击时移除。',
        },
        set_id=115,
        obtain='幽冥之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='幽锁深牢的系囚',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='系囚的合啮拘笼', pos=1, desc='紧扣兽面囚徒面部的犬嘴笼，严防末路恶逆露出獠牙伤人。'),
            SrRelicPieceDef(name='系囚的铅石梏铐', pos=2, desc='紧缚魔手的沉重镣铐，钢针钉腕，钳制凶爪恶逆再造杀孽。'),
            SrRelicPieceDef(name='系囚的幽闭缚束', pos=3, desc='捆缚危险重犯的拘束囚服，反扣关节，限制囚徒身体的变化能力。'),
            SrRelicPieceDef(name='系囚的绝足锁桎', pos=4, desc='桎缚兽足的金属脚镣，禁铜末路恶逆，以防脱逃酿祸。'),
        ),
        effects={
            '2': '攻击力提高12%。',
            '4': '敌方目标每承受1个持续伤害效果，装备者对其造成伤害时就无视其6%的防御力，最多计入3个持续伤害效果。',
        },
        set_id=116,
        obtain='幽冥之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='死水深潜的先驱',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='先驱的绝热围壳', pos=1, desc='俄尔刻龙常见款式的潜水重盔。透过小小的舷窗只能看到令人难以忍受的无边黑暗。'),
            SrRelicPieceDef(name='先驱的虚极罗盘', pos=2, desc='一块腕表式指南针，磁针已被拆去，不再能指示任何方向。'),
            SrRelicPieceDef(name='先驱的密合铅衣', pos=3, desc='废铁打造的重型潜水服，密不透风，使用者也常常调侃它更像是一具深水棺材。'),
            SrRelicPieceDef(name='先驱的泊星桩锚', pos=4, desc='重靴形似船锚，它的主人已经做好了永不返回水面的打算。'),
        ),
        effects={
            '2': '对受负面状态影响的敌人造成的伤害提高12%。',
            '4': '暴击率提高4%，装备者对陷入不少于2/3个负面效果的敌方目标造成的暴击伤害提高8%/12%。装备者对敌方目标施加负面效果后，上述效果提高100%，持续1回合。',
        },
        set_id=117,
        obtain='梦潜之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='机心戏梦的钟表匠',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='钟表匠的极目透镜', pos=1, desc='一枚金雕目镜，镜片映照远方的纷繁奇象，助它的主人望穿迷梦。'),
            SrRelicPieceDef(name='钟表匠的交运腕表', pos=2, desc='一块做工精美的手表，有着奇特的子盘与时针，据说是梦境中好运的象征。'),
            SrRelicPieceDef(name='钟表匠的空幻礼服', pos=3, desc='一身富丽堂皇的皮领礼服，华美典雅，通常用于宴会等正式场合。'),
            SrRelicPieceDef(name='钟表匠的隐梦革履', pos=4, desc='一双款式优雅的皮靴，穿戴者曾以神秘的姿态踏梦潜行。'),
        ),
        effects={
            '2': '击破特攻提高16%。',
            '4': '当装备者对我方目标施放终结技时，我方全体击破特攻提高30%，持续2回合，该效果无法叠加。',
        },
        set_id=118,
        obtain='梦潜之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='荡除蠹灾的铁骑',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='铁骑的索敌战盔', pos=1, desc='深度强化感官信号的钢铁战盔，将格拉默铁骑的意识与装甲融为一体。'),
            SrRelicPieceDef(name='铁骑的摧坚铁腕', pos=2, desc='粉碎虫裔的强劲铁腕，尖锐而轻盈，坚硬又稳固。'),
            SrRelicPieceDef(name='铁骑的银影装甲', pos=3, desc='迸发烈焰的推进装甲，给予格拉默铁骑足以点燃战场的烈焰。'),
            SrRelicPieceDef(name='铁骑的行空护胫', pos=4, desc='兼具破坏力与速度的机骑护胫，格拉默铁骑会高高跃起，将力量集中于一处踢向敌人。'),
        ),
        effects={
            '2': '击破特攻提高16%。',
            '4': '当装备者的击破特攻大于等于150%时，对敌方目标造成的击破伤害无视其10%的防御力。当装备者的击破特攻大于等于250%时，对敌方目标造成的超击破伤害额外无视其15%的防御力。',
        },
        set_id=119,
        obtain='勇骑之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='风举云飞的勇烈',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='勇烈的玄枵面甲', pos=1, desc='以凶鸟「大风」为原型的面甲，两对辅眼曾目睹过神迹示现。'),
            SrRelicPieceDef(name='勇烈的钩爪腕甲', pos=2, desc='嵌合肌体的仿生手甲。若想狩猎猛兽，就要有比猛兽更锐利的爪牙。'),
            SrRelicPieceDef(name='勇烈的飞翎瓷甲', pos=3, desc='身如凛风，翱翔群狼仰首处，猎物与猎人终将易位而处。'),
            SrRelicPieceDef(name='勇烈的逐猎腿甲', pos=4, desc='禽爪制式的战靴，着装之人迅疾如风地奔袭战场，轻易踏行于荆棘坎坷。'),
        ),
        effects={
            '2': '攻击力提高12%。',
            '4': '使装备者的暴击率提高6%，装备者施放追加攻击时，使终结技造成的伤害提高36%，持续1回合。',
        },
        set_id=120,
        obtain='勇骑之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='重循苦旅的司铎',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='司铎的律音耳坠', pos=1, desc='他常常坐在告解室内侧耳倾听。耳坠不断提醒着他，即便是最微末的细语也是有重量的。'),
            SrRelicPieceDef(name='司铎的授邀手套', pos=2, desc='他常常站在公馆内接待访客，无数遍发出邀请的动作。洁净的手套提醒着他切记谦卑与礼数。'),
            SrRelicPieceDef(name='司铎的圣职礼服', pos=3, desc='他常常站在试衣镜前，确认仪容衣装。在出门前就确保一切井然有序，绝不偏移。'),
            SrRelicPieceDef(name='司铎的苦旅短靴', pos=4, desc='他常常在旅行开始之前，挑选一双适脚的靴子。他摔倒过很多次，但他站起过同样多次。'),
        ),
        effects={
            '2': '速度提高6%。',
            '4': '对我方单体目标施放战技或终结技时，使技能目标的暴击伤害提高18%，持续2回合，该效果最多叠加2次。',
        },
        set_id=121,
        obtain='迷识之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='识海迷坠的学者',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='学者的银边视镜', pos=1, desc='一枚映照着巨厦的单片晶石眼镜，与手杖、表链、胸针一起衬托出主人的时髦与学识。'),
            SrRelicPieceDef(name='学者的辅助指节', pos=2, desc='以合金制成、辅助手指活动的外骨骼，需要配合使用者手型订制，价值不菲。'),
            SrRelicPieceDef(name='学者的粗纺外套', pos=3, desc='粗花呢外套和针织衫是学院中常见的搭配，耐用不易皱的面料对访问学者来说正合适。'),
            SrRelicPieceDef(name='学者的绒皮雪靴', pos=4, desc='松软舒适的女式短靴，搭配合适的小腿裤会有恰到好处的时尚感，已陪伴主人极地科考多年。'),
        ),
        effects={
            '2': '暴击率提高8%。',
            '4': '战技和终结技造成的伤害提高20%，施放终结技后，下一次施放战技时造成的伤害额外提高25%。',
        },
        set_id=122,
        obtain='迷识之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='凯歌祝捷的英豪',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='英豪的冠军桂冠', pos=1, desc='竞技场冠军所得的桂冠。每一片金色的桂叶都闪烁着勇气与荣耀。'),
            SrRelicPieceDef(name='英豪的鉴金腕铠', pos=2, desc='一对精致的督战勇士护腕。紧贴着勇士的手腕，稳稳地支撑着胜利号角。'),
            SrRelicPieceDef(name='英豪的骁战金甲', pos=3, desc='宛如天神的铠甲，完美贴合着雄健的身躯。'),
            SrRelicPieceDef(name='英豪的赴火护胫', pos=4, desc='紧密贴合战士腿部的护胫，曲线优雅而坚固，蕴藏着决不退缩的信念。'),
        ),
        effects={
            '2': '攻击力提高12%。',
            '4': '装备者的忆灵在场时，装备者的速度提高6%，装备者的忆灵攻击时，装备者和忆灵的暴击伤害提高30%，持续2回合。',
        },
        set_id=123,
        obtain='弦歌之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='哀歌覆国的诗人',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='诗人的莳萝花冠', pos=1, desc='春日黄昏神庙前，最出色的吟游诗人将得到墨涅塔赐福的莳萝花冠。'),
            SrRelicPieceDef(name='诗人的贵金手镯', pos=2, desc='被人喜爱的金属打造的手镯，故事中的恶龙，也曾背负这样金属打造的枷锁。'),
            SrRelicPieceDef(name='诗人的缀星裙摆', pos=3, desc='黎明是最温柔的时辰，她的裙摆也恰如黎明前的最后一缕晚星，那般颜色。'),
            SrRelicPieceDef(name='诗人的钉银之履', pos=4, desc='织履镶着银钉，行在沙地上印出字样的纹路，为了采撷旧日的诗篇她始终步履不停。'),
        ),
        effects={
            '2': '量子属性伤害提高10%。',
            '4': '使装备者的速度降低8%。进入战斗前，若装备者的速度小于110/95，使装备者的暴击率提高20%/32%。该效果同时对装备者的忆灵生效。',
        },
        set_id=124,
        obtain='弦歌之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='烈阳惊雷的女武神',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='女武神的翱翔翼盔', pos=1, desc='这顶翼盔曾见证了阳雷骑士挑落天神，它也见证了天空阖眼。'),
            SrRelicPieceDef(name='女武神的骑枪手铠', pos=2, desc='这对护手陪伴骑士赢下了所有的战斗。它能够让人紧握最致命的武器，忍受最痛苦的背叛。'),
            SrRelicPieceDef(name='女武神的启程披风', pos=3, desc='这袭披风为阳雷骑士遮雨避尘，陪伴她经历所有的冒险——留下那天空中最醒目的背影。'),
            SrRelicPieceDef(name='女武神的勋礼马刺', pos=4, desc='这对马刺来自阳雷骑士两只翼兽伙伴的馈赠——走在追求真实的道路之上，这是必要的疼痛。'),
        ),
        effects={
            '2': '速度提高6%。',
            '4': '当装备者及其忆灵为装备者及其忆灵以外的我方目标提供治疗后，使装备者获得【甘霖】，每回合最多触发1次，持续2回合。装备者持有【甘霖】时，速度提高6%，我方全体暴击伤害提高15%，该效果无法叠加。',
        },
        set_id=125,
        obtain='雳涌之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='恶海逐波的船长',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='船长的领航笠帽', pos=1, desc='泛着珍珠光泽的宽边太阳帽。海上驰骋的船员们，借此抵挡艾格勒的烈日。'),
            SrRelicPieceDef(name='船长的捕光星盘', pos=2, desc='捕获星光指引方向的航海罗盘。即使身处昏黑无边的大海中，也会有星光指出前进方向。'),
            SrRelicPieceDef(name='船长的驭风斗篷', pos=3, desc='航海斗篷如同巨帆般飞舞。若长风不助我，我便化为长风。'),
            SrRelicPieceDef(name='船长的踏浪游靴', pos=4, desc='破碎的浪花在船长靴下绽放。即便他一去不返，海潮也会带回他的祝福。'),
        ),
        effects={
            '2': '暴击伤害提高16%。',
            '4': '装备者成为其他我方目标的技能目标时，获得1层【助力】，最多叠加2层。施放终结技时，若持有2层【助力】，消耗所有【助力】，使装备者攻击力提高48%，持续1回合。',
        },
        set_id=126,
        obtain='雳涌之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='再创天地的救世主',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='救世主的登程风帽', pos=1, desc='传说中救世主遮风避雨时会使用的风帽，实际穿着可能与吟游诗人的描述不同。'),
            SrRelicPieceDef(name='救世主的执剑护手', pos=2, desc='传说中救世主披荆斩棘时会穿戴的护手，实际穿着可能与吟游诗人的描述不同。'),
            SrRelicPieceDef(name='救世主的传承战袍', pos=3, desc='传说中救世主兵刃相接时会披戴的战袍，实际穿着可能与吟游诗人的描述不同。'),
            SrRelicPieceDef(name='救世主的拓荒长靴', pos=4, desc='传说中救世主跋山涉水时会穿戴的长靴，实际穿着可能与吟游诗人的描述不同。'),
        ),
        effects={
            '2': '暴击率提高8%。',
            '4': '装备者施放普攻或战技后，若装备者的忆灵在场，使装备者及其忆灵生命上限提高24%，我方全体造成的伤害提高15%，持续至装备者下次施放普攻或战技后。',
        },
        set_id=127,
        obtain='隐救之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='自匿星芒的隐士',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='隐士的宽檐呢帽', pos=1, desc='一顶经典的、宽檐可卷起的软呢帽。在知识分子、艺术家、专业人士中非常流行。'),
            SrRelicPieceDef(name='隐士的简雅腕表', pos=2, desc='漂亮的金属编织链带，以及简约的圆形表盘。冷静、精密、工业化；低调、实用、不张扬。'),
            SrRelicPieceDef(name='隐士的驼色夹克', pos=3, desc='一件棕色灯芯绒夹克。他常将这件夹克敞开穿，来打破一丝不苟的框架。'),
            SrRelicPieceDef(name='隐士的麂皮软鞋', pos=4, desc='出现在不太正式的场合里，更加结实耐磨的皮质高帮系带软鞋。依然可见其优雅的一面。'),
        ),
        effects={
            '2': '提供的护盾量提高10%。',
            '4': '使装备者提供的护盾量提高12%，我方目标持有装备者提供的护盾时，暴击伤害提高15%。',
        },
        set_id=128,
        obtain='隐救之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='闪耀功勋的魔法少女',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='魔法少女的闪耀勋章', pos=1, desc='魔法少女糖果色的蝴蝶结发卡，犹如一枚闪闪发光的勋章。'),
            SrRelicPieceDef(name='魔法少女的守护手套', pos=2, desc='魔法少女的多功能手套，集娱乐和战斗功能于一体。纯白的双手，呵护着众人的愿。'),
            SrRelicPieceDef(name='魔法少女的永舞战裙', pos=3, desc='定制的多用型作战服，也是能用作打歌服的偶像短裙。舒适、轻便，且不易污浊。'),
            SrRelicPieceDef(name='魔法少女的缔约长靴', pos=4, desc='抗磨损一流的长靴，真正的约定超越言语，需在行迹中践履。'),
        ),
        effects={
            '2': '暴击伤害提高16%。',
            '4': '装备者及其忆灵造成的欢愉伤害无视目标10%的防御力，我方每累计获得5点笑点，造成的欢愉伤害额外无视目标1%的防御力，最多叠加10层。',
        },
        set_id=129,
        obtain='魔占之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='应天涉远的卜者',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='卜者的演算玉兆', pos=1, desc='竟天佩戴的外置玉兆。深感人力难穷天命，他以此不休地占望未来。'),
            SrRelicPieceDef(name='卜者的机巧义手', pos=2, desc='于塔拉萨的战场失去一条手臂后，竟天为自己打造的义手——冰冷、精确，一如他的卜算。'),
            SrRelicPieceDef(name='卜者的观天星袍', pos=3, desc='玉阙太卜司的制式道袍，一般适用于隆重的场合。因很少穿着，看起来依然如同全新的一般。'),
            SrRelicPieceDef(name='卜者的飞腾云履', pos=4, desc='竟天制作的云靴，能助他飞临战场，搜集信息。如今陈列玉阙太卜司中，以示后人。'),
        ),
        effects={
            '2': '速度提高6%。',
            '4': '进入战斗前，若装备者的速度大于等于120/160，使装备者的暴击率提高10%/18%。装备者每场战斗首次施放欢愉技时，使我方全体欢愉度提高10%，该效果无法叠加。',
        },
        set_id=130,
        obtain='魔占之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='星如我见的领航员',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='领航员的深空之镜', pos=1, desc='领航员精心打造的望远镜，他见证过生命诞生于荒芜的星尘，也目睹了毁灭自彼方升起。'),
            SrRelicPieceDef(name='领航员的游戏之骰', pos=2, desc='领航员的骰子戒指，每一次转动都会给出有趣的谜题。他似乎和很多人玩过游戏，有些人赢了，有些人则就此不知所踪。'),
            SrRelicPieceDef(name='领航员的星图制服', pos=3, desc='领航员制服的暗纹里，细密地绣着星穹列车曾驶过的浩瀚星图。每一条金线的延伸，都代表着一段航程。'),
            SrRelicPieceDef(name='领航员的永行魔靴', pos=4, desc='领航员的特制皮靴，据传拥有特殊的魔力，会把人带往所有不欢迎他的地方。'),
        ),
        effects={
            '2': '攻击力提高12%。',
            '4': '装备者进入战斗时/施放战技时，造成的战技与终结技伤害提高18%，最多叠加3层，装备者回合开始时/施放终结技后，移除1层该效果。',
        },
        set_id=131,
        obtain='观火之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='叩问天工的名冶',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='名冶的火兽面罩', pos=1, desc='朱明匠人锻器的面罩，以火兽的形象设计而成。额处嵌有火晶，可保护工匠免受炽气和幻象侵灼。'),
            SrRelicPieceDef(name='名冶的镔铁护手', pos=2, desc='朱明匠人的多功能护手，可在锻打时辅助发力。冷铁与焰纹相融，既取刚坚不摧之质，亦含驯火成锋之意。'),
            SrRelicPieceDef(name='名冶的辟火匠衫', pos=3, desc='以火浣锦织就的匠衫，穿着者即使伫立洪炉畔，周身犹可存寸尺清凉。'),
            SrRelicPieceDef(name='名冶的无拘重靴', pos=4, desc='对抗朱明核心的超大重力场，匠人们打造出带有反冲悬浮装置的重靴，藉此自如行动。'),
        ),
        effects={
            '2': '生命上限提高12%。',
            '4': '装备者对防御力降低状态的敌方目标造成的暴击伤害提高28%。装备者对敌方目标施加防御力降低状态后，使我方全体获得【助燃】，持续2回合，该效果无法叠加，持有【助燃】的我方目标造成的伤害提高15%。该效果在装备者施放攻击后可再次触发。',
        },
        set_id=132,
        obtain='观火之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='戏梦点星的伶人',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='伶人的悲泣假面', pos=1, desc='伶人们表演时佩戴的面具，掩住了颤抖的哀容，却留下那双哭泣的眼睛。'),
            SrRelicPieceDef(name='伶人的斑斓折扇', pos=2, desc='伶人们随身携带的折扇，在舞台上可变幻成诸多道具。'),
            SrRelicPieceDef(name='伶人的滑稽戏服', pos=3, desc='装点着华贵装饰的束腰戏服。伶人演出种种剧目，观众的眼泪是最好的报答。'),
            SrRelicPieceDef(name='伶人的弯月舞靴', pos=4, desc='造型奇异的戏靴。有人说它的形象来自某处的月亮，有人说那其实是阿哈弯起的嘴角。'),
        ),
        effects={
            '2': '速度提高6%。',
            '4': '当装备者对我方其他单体目标施放战技或终结技时，使技能目标的欢愉度提高16%，持续3回合，若装备者持有的好活当赏大于等于10点，则额外使我方全体目标的暴击伤害提高12%，持续3回合。',
        },
        set_id=133,
        obtain='密伶之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='贪噬禁果的异端',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='异端的颅脑仪器', pos=1, desc='研究员对大脑进行手术的仪器，历经灼烧与重塑，她的神经足以承载最黑暗的秘密。'),
            SrRelicPieceDef(name='异端的注射手套', pos=2, desc='研究员配备注射器的实验手套，远古的嘶吼自那腥甜的液体中升起。'),
            SrRelicPieceDef(name='异端的理性束衣', pos=3, desc='研究员的工作服布满拘束，可她深知：无形的生命又怎会被拘束于有形的骸体。'),
            SrRelicPieceDef(name='异端的饥饿短靴', pos=4, desc='研究员的皮靴在意外中生出了唇齿，拥有了永不满足的欲望，也意味着饱受折磨的饥饿。'),
        ),
        effects={
            '2': '暴击伤害提高16%。',
            '4': '使装备者普攻造成的伤害提高36%。当装备者施放普攻时，使装备者的攻击力提高20%，持续2回合。',
        },
        set_id=134,
        obtain='密伶之径·侵蚀隧洞',
    ),
    RelicSetDef(
        set_name='太空封印站',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='「黑塔」的空间站点', pos=5, desc='位面封装的是「黑塔」空间站，它停靠在湛蓝星上空，沿着既定轨道缓缓漂流，寂静的银河像是本书卷等待翻阅。'),
            SrRelicPieceDef(name='「黑塔」的漫历轨迹', pos=6, desc='「黑塔」空间站建立起那一刻，黑塔女士便失去了兴致。它在湛蓝星上空保持着第一宇宙速度，在卫星轨道上留下环绕的轨迹。'),
        ),
        effects={
            '2': '使装备者的攻击力提高12%。当装备者的速度大于等于120时，攻击力额外提高12%。',
        },
        set_id=301,
        obtain='第三世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='不老者的仙舟',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='罗浮仙舟的天外楼船', pos=5, desc='泛于星海的罗浮仙舟被收拢于球中，玉界门上浮槎去来，若星月之出入。无数人曾来此寻求长生之秘，却又失望而归。'),
            SrRelicPieceDef(name='罗浮仙舟的建木枝蔓', pos=6, desc='曾经罗浮仙舟因建木生发，成为仙舟舰队之尊；后来罗浮仙舟因建木成祸，自食长寿恶果…建木枝蔓已经牢牢缠住罗浮命运，难以分离。'),
        ),
        effects={
            '2': '使装备者的生命上限提高12%。当装备者的速度大于等于120时，我方全体攻击力提高8%。',
        },
        set_id=302,
        obtain='第三世界·模拟宇宙；坚城不倒·差分宇宙',
    ),
    RelicSetDef(
        set_name='泛银河商业公司',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='公司的巨构总部', pos=5, desc='位于庇尔波因特的公司总部被封存在位面球中。在星际和平公司的商业宏图之中，没有一颗星球可以置身事外，他们前往深空，是为了将全宇宙的力量集合起来。'),
            SrRelicPieceDef(name='公司的贸易航道', pos=6, desc='借助「信用点体系」的便利，跨越星际的商贸得以成立。星际和平公司用经济活动连缀繁星，拓展了贸易边界。'),
        ),
        effects={
            '2': '使装备者的效果命中提高10%。同时提高装备者等同于当前效果命中25%的攻击力，最多提高25%。',
        },
        set_id=303,
        obtain='第五世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='筑城者的贝洛伯格',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='贝洛伯格的存护堡垒', pos=5, desc='位面封装的是贝洛伯格行政区最常见的风景：永冬铭碑。人们从这里路过，感受到来自遥远而温暖的目光守护着他们。'),
            SrRelicPieceDef(name='贝洛伯格的铁卫防线', pos=6, desc='贝洛伯格的银鬃铁卫矗立在风雪之中，他们排成一线，等待着前来进犯的天外入侵者。铁卫的意志坚不可摧，铁卫的阵线也绝不后退。'),
        ),
        effects={
            '2': '使装备者的防御力提高15%。当装备者的效果命中大于等于50%时，防御力额外提高15%。',
        },
        set_id=304,
        obtain='第六世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='星体差分机',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='螺丝星的机械烈阳', pos=5, desc='位面封装的是螺丝星的核心——行星被囚于由无数杠杆、活塞与齿轮构成的囚笼中，螺丝星的住民美其名曰「钢铁太阳」。'),
            SrRelicPieceDef(name='螺丝星的环星孔带', pos=6, desc='行星环承载着螺丝星的一切——有多少人曾意识到密布的矩形孔隙阵列书写了行星系统的真相？'),
        ),
        effects={
            '2': '使装备者的暴击伤害提高16%。当装备者的暴击伤害大于等于120%时，进入战斗后装备者的暴击率提高60%，持续到施放首次攻击后结束。',
        },
        set_id=305,
        obtain='第五世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='停转的萨尔索图',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='萨尔索图的移动城市', pos=5, desc='位面封装的是萨尔索图星上仅剩的移动城市之一：风滚草。这座城市从未停下，才勉强做到不被黑夜或者极昼吞没。'),
            SrRelicPieceDef(name='萨尔索图的晨昏界线', pos=6, desc='停止自转的萨尔索图星的日夜周期漫长无比，人们只有追逐着「晨昏交界线」不断迁徙，才能勉强维持住仅剩的生存空间。'),
        ),
        effects={
            '2': '使装备者的暴击率提高8%。当装备者当前暴击率大于等于50%时，终结技和追加攻击造成的伤害提高15%。',
        },
        set_id=306,
        obtain='第六世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='盗贼公国塔利亚',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='塔利亚的钉壳小镇', pos=5, desc='位面封装的是塔利亚上无依无靠的破落小镇：「钉壳」。盗贼们在这个水源地建立破布、钢筋和木板的小镇，为了暂时的和平。'),
            SrRelicPieceDef(name='塔利亚的裸皮电线', pos=6, desc='这是废料场中收捡来电线，它的绝缘层部分脱落，部分残留，但仍然没有退役。在塔利亚的盗匪小镇上，从来就没有真正的废物。'),
        ),
        effects={
            '2': '使装备者的击破特攻提高16%。当装备者的速度大于等于145时，击破特攻额外提高20%。',
        },
        set_id=307,
        obtain='第四世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='生命的翁瓦克',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='翁瓦克的诞生之岛', pos=5, desc='位面封装的翁瓦克星球上最著名的岛屿——瓦克岛。整座岛屿郁郁葱葱，在名为「西斯腾」的大树上，结满了各式动物的果实。'),
            SrRelicPieceDef(name='翁瓦克的环岛海岸', pos=6, desc='瓦克岛的海岸线上，海面时高时低，浪潮时涨时落…千年不变的风景，见证了如同潮汐一般的兴衰。'),
        ),
        effects={
            '2': '使装备者的能量恢复效率提高5%。当装备者的速度大于等于120时，进入战斗时立刻使行动提前40%。',
        },
        set_id=308,
        obtain='第四世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='繁星竞技场',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='泰科铵的镭射球场', pos=5, desc='位面封装的泰科铵星规格最高的竞技场——泰科铵大球馆。球馆内外人声鼎沸，彩旗展动...激动人心的机动球竞技比赛将在万众瞩目中盛大开幕。'),
            SrRelicPieceDef(name='泰科铵的弧光赛道', pos=6, desc='泰科铵大球馆的标准赛道通常为金属结构外覆光滑混凝土与原木地板。为了让场内观众清晰观赛，大量透明聚碳酸酯材料被投入球馆，战况一览无余。'),
        ),
        effects={
            '2': '使装备者的暴击率提高8%。当装备者当前暴击率大于等于70%时，普攻和战技造成的伤害提高20%。',
        },
        set_id=309,
        obtain='第七世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='折断的龙骨',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='伊须磨洲的残船鲸落', pos=5, desc='位面封装的是塔拉萨的伊须磨洲自治区。仙舟「岱舆」断舰坠毁于此，启迪了伊须磨洲文明。'),
            SrRelicPieceDef(name='伊须磨洲的坼裂缆索', pos=6, desc='坠落的仙舟「岱舆」断舰永远地碇泊在异乡，也许是时候解开缆索，让它返航了。'),
        ),
        effects={
            '2': '使装备者的效果抵抗提高10%。当装备者的效果抵抗大于等于30%时，我方全体暴击伤害提高10%。',
        },
        set_id=310,
        obtain='第七世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='苍穹战线格拉默',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='格拉默的铁骑兵团', pos=5, desc='位面球中封装的是格拉默帝国盛名在外的铁骑变形鞘。无数白银机甲被装载进舰船，驶向星系外缘，抵御自深空而来的虫群恶蠹。'),
            SrRelicPieceDef(name='格拉默的寂静坟碑', pos=6, desc='鼎盛的「帝国」格拉默化为了尘埃。没有任何东西能证明它往日的辉煌，唯有星尘、机甲、舰船与虫群的残骸飘荡在真空中绵延成河，维持着惨烈战线的原状，也成了它陨落的纪念碑。'),
        ),
        effects={
            '2': '使装备者的攻击力提高12%。当装备者的速度大于等于135/160时，使装备者造成的伤害提高12%/18%。',
        },
        set_id=311,
        obtain='第八世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='梦想之地匹诺康尼',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='匹诺康尼的堂皇酒店', pos=5, desc='位面封装的是匹诺康尼的主体——「白日梦」酒店。在此下榻的宾客将去往美梦的世界，在无所不可的大都会中，享受纸醉金迷的盛宴。'),
            SrRelicPieceDef(name='匹诺康尼的逐梦轨道', pos=6, desc='匹诺康尼的梦境都市里，复杂的轨道盘绕于楼宇之间，托起游客搭乘的球笼，将五色缤纷的梦连为一体。'),
        ),
        effects={
            '2': '使装备者的能量恢复效率提高5%。使队伍中与装备者属性相同的我方其他角色造成的伤害提高10%。',
        },
        set_id=312,
        obtain='第八世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='无主荒星茨冈尼亚',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='茨冈尼亚的母神卧榻', pos=5, desc='位面封装的是茨冈尼亚-Ⅳ最宜居的地带——死寂荒漠「母神卧榻」。三重眼的地母神沉默而朴素，以其厚重的身躯无言地包罗茨冈尼亚的一切生者和死者。'),
            SrRelicPieceDef(name='茨冈尼亚的轮回纽结', pos=6, desc='绿松陨石被埃维金人细细磋磨，又以金线翠缎穿之。他们说护身的纽结绝不应被黄沙埋没，而要璀璨得如同「卡卡瓦」之夜里自死亡中脱胎的神体。'),
        ),
        effects={
            '2': '使装备者的暴击率提高4%。当敌方目标被消灭时，装备者暴击伤害提高4%，最多叠加10层。',
        },
        set_id=313,
        obtain='第九世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='出云显世与高天神国',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='出云的祸津众神', pos=5, desc='位面封装的是被一刀斩开过去未来的出云。出云曾遍历不堪言状的生存战争，也曾有过饫甘餍肥的辉煌岁月...如今荒土业已无处可寻，唯余下埋葬往昔的剑冢。'),
            SrRelicPieceDef(name='出云的终始一刀', pos=6, desc='出云人借由刀穗将利刃系于腰间。他们行走世间，以刀狩神，又以神骸锻刀...如此循环往复，出云走向繁荣、走向幻灭、走向空无。'),
        ),
        effects={
            '2': '使装备者的攻击力提高12%。进入战斗时，若至少存在一名与装备者命途相同的队友，装备者的暴击率提高12%。',
        },
        set_id=314,
        obtain='第九世界·模拟宇宙',
    ),
    RelicSetDef(
        set_name='奔狼的都蓝王朝',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='都蓝的穹窿金帐', pos=5, desc='位面封装的是青丘步离的穹窿金帐。与步离人留在银河中的蛮野名声不同，他们拥有非凡的生物技术。狼子们汇聚在伟大的巢父都蓝之侧，将天上众星视为牧畜，逐驰其间。'),
            SrRelicPieceDef(name='都蓝的器兽缰辔', pos=6, desc='是缰绳、是锁镣，亦是皮鞭。高过战兽腿的步离青年被教会的第一个道理就是：永远要把缰绳要握紧在手里，否则自己将成为被奴役的牲畜，甚至饲料。'),
        ),
        effects={
            '2': '我方角色施放追加攻击时，装备者获得一层【功勋】，最多叠加5层，每层【功勋】使装备者追加攻击造成的伤害提高5%，叠满5层时，额外使装备者的暴击伤害提高25%。',
        },
        set_id=315,
        obtain='永恒笑剧·差分宇宙',
    ),
    RelicSetDef(
        set_name='劫火莲灯铸炼宫',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='铸炼宫的莲华灯芯', pos=5, desc='位面封装的是朱明仙舟的工造司所在地——焰轮铸炼宫，朱明仙舟围绕着岁阳之祖「燧皇」构建的天体级球形结构。天才匠人们自其中汲取能量，将奇思异想打造成型。'),
            SrRelicPieceDef(name='铸炼宫的焰轮天绸', pos=6, desc='伟如恒星般的岁阳始祖沉陷在无边梦境之中。在它的酣眠之中，周身的原子与分子碰撞激发，不断从焰轮铸炼的外壳结构中逸散出来，最终呈现为色彩纷呈的天绸光带。'),
        ),
        effects={
            '2': '使装备者的速度提高6%。当装备者击中拥有火属性弱点的敌方目标时，击破特攻提高40%，持续1回合。',
        },
        set_id=316,
        obtain='永恒笑剧·差分宇宙',
    ),
    RelicSetDef(
        set_name='沉陆海域露莎卡',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='露莎卡的水朽苍都', pos=5, desc='位面封装的是海洋世界露莎卡一处被淹没的城市。海平线不断上升直到城市也被淹没，只有巨大的「船邦」载着船员们在海上前进，找寻下次远航的方向。'),
            SrRelicPieceDef(name='露莎卡的双生航道', pos=6, desc='无垠的水平线内，即使只存浅痕，也足以打破这份沉寂。航线承载着船员的历史，水灵于水道追寻着希望。'),
        ),
        effects={
            '2': '使装备者的能量恢复效率提高5%，如果装备者不是编队中的第一位角色，使编队中的第一位角色攻击力提高12%。',
        },
        set_id=317,
        obtain='蠹役饥肠·差分宇宙',
    ),
    RelicSetDef(
        set_name='奇想蕉乐园',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='蕉乐园的蕉芯广场', pos=5, desc='位面球封装的是某个科研团体下设实验室之一，因为模因污染，信息的真实与虚假已经彻底混合，难以分清，现已被认知重塑为「蕉乐园」。'),
            SrRelicPieceDef(name='蕉乐园的模因线缆', pos=6, desc='实验室中随处可见的光信号缆线，它被用于采集实验数据，以达成不可告人的秘密。对「香蕉们」而言，认知世界的方法就藏在其中。'),
        ),
        effects={
            '2': '使装备者的暴击伤害提高16%，当存在装备者召唤的目标时，暴击伤害额外提高32%。',
        },
        set_id=318,
        obtain='蠹役饥肠·差分宇宙',
    ),
    RelicSetDef(
        set_name='谧宁拾骨地',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='哀地里亚的殁名祭碑', pos=5, desc='位面球中封存着翁法罗斯的哀地里亚，信仰塞纳托斯的民众们在雪原上修筑起巨碑，敬奉为他们带来死亡祝福的圣女。'),
            SrRelicPieceDef(name='哀地里亚的入溟骨链', pos=6, desc='兽骨、箭镞与铁蒺藜，将哀地里亚人与那亡者的世界相连。荒原上的苦行者只愿自己的灵魂能够渡过寒溟，不因其贫瘠与软弱而彷徨失落于面见尊神的路上。'),
        ),
        effects={
            '2': '使装备者的生命上限提高12%。当装备者的生命上限大于等于5000点时，使装备者及其忆灵的暴击伤害提高28%。',
        },
        set_id=319,
        obtain='纷争不休·差分宇宙',
    ),
    RelicSetDef(
        set_name='渊思寂虑的巨树',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='神悟树庭的沉思巨桹', pos=5, desc='位面球封装的是翁法罗斯的神悟树庭，「裂分之枝」瑟希斯的神躯在此沉思。「最初的学者」带领众人在林间建立起花园与庭院，分享学识，树庭由此初诞。'),
            SrRelicPieceDef(name='神悟树庭的联识叶路', pos=6, desc='金丝与藤蔓串联起树庭识网，成为学派间共享成果的生命线。信息由根系传入，沿脉络游览、析构。直至化作一滴露珠，溶入友爱之馆的池中。'),
        ),
        effects={
            '2': '使装备者的速度提高6%。当装备者的速度大于等于135/180时，使装备者及其忆灵的治疗量提高12%/20%。',
        },
        set_id=320,
        obtain='纷争不休·差分宇宙',
    ),
    RelicSetDef(
        set_name='妖精织梦的乐园',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='迷路迷境的恬梦树屋', pos=5, desc='位面球中封装着哀丽秘榭的「迷路迷境」，拨开金色的麦草，掉进一片深深、深深的树洞，咦？好多小妖精，「一二三四五六七？」，错啦！是「哆徕咪发嗦啦嘻！」'),
            SrRelicPieceDef(name='迷路迷境的祈愿笛哨', pos=6, desc='陶土捏制的笛哨，代表着小妖精们和两个小孩子的约定。当小男孩和小女孩吹起笛哨的时候，「迷？」的一声，妖精们就会打开通往迷境的树洞，欢迎他们来做客！'),
        ),
        effects={
            '2': '队伍中当前在场的我方目标数量不等于4时，每多/少1名我方目标，使装备者及其忆灵造成的伤害提高9%/12%，最多叠加4/3层。',
        },
        set_id=321,
        obtain='&nbsp;月下朱殷·差分宇宙',
    ),
    RelicSetDef(
        set_name='沉欢醉饮的海隅',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='酣歌海垠的礁屿灯塔', pos=5, desc='位面球中封装着沉浸在永世欢乐中的斯缇科西亚。长明的灯塔矗立海滨，演奏着不息的乐曲。循着欢歌的航船越过迷雾而来，旋即触礁沉没，空留残骸被浪涛吞吃。'),
            SrRelicPieceDef(name='酣歌海垠的歌咏步道', pos=6, desc='斯缇科西亚人深信海妖如传说中一样以血肉守护此处安乐，而她们终有一日将循着灯塔不竭的歌咏赴约而来，得到永不止息的宴会作为犒赏。'),
        ),
        effects={
            '2': '使装备者的攻击力提高12%。当装备者的攻击力大于等于2400/3600时，使造成的持续伤害额外提高12%/24%。',
        },
        set_id=322,
        obtain='&nbsp;月下朱殷·差分宇宙',
    ),
    RelicSetDef(
        set_name='永恒之地翁法罗斯',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='翁法罗斯的西风尽途', pos=5, desc='位面球中封装着「如我所书」中的一个章节：「一页永恒」。它被赋予了鲜花的芬芳，西风的温暖…以及一个开放的结局。'),
            SrRelicPieceDef(name='翁法罗斯的永恒诗篇', pos=6, desc='在故事的尾声，三千万世的数据化作完整的诗篇，执笔者写下的岁月，将留在银河的回忆之中，永不褪色。'),
        ),
        effects={
            '2': '使装备者的暴击率提高8%。装备者的忆灵在场时，我方全体速度提高8%，该效果无法叠加。',
        },
        set_id=323,
        obtain='西风丛中·差分宇宙',
    ),
    RelicSetDef(
        set_name='天国@直播间',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='直播间的千窗万面', pos=5, desc='位面球中封装着无数直播窗口的数字空间。它是与现实深度交织的虚拟社会，它是梦幻且疏离的假想都市，它是人人可以窥探并参与其中的另一种生活。'),
            SrRelicPieceDef(name='直播间的畅聊语流', pos=6, desc='天国@直播间或许不是天国。无数次的聊天框流淌，既能构建辉煌，也能带来崩溃——它从来都不是现实的隔绝，而是现实的延伸。'),
        ),
        effects={
            '2': '使装备者的暴击伤害提高16%，若在同一回合内消耗大于等于3点战技点，额外使装备者暴击伤害提高32%，持续3回合。',
        },
        set_id=324,
        obtain='西风丛中·差分宇宙',
    ),
    RelicSetDef(
        set_name='零号关卡朋克洛德',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='朋克洛德的虹霓都市', pos=5, desc='位面球中封装着朋克洛德的虹霓都市。昼与夜没有分别，虚幻和现实没有边界，生命有如一段闪烁的字节。'),
            SrRelicPieceDef(name='朋克洛德的数据洪流', pos=6, desc='信息川流的网络，将骇客们的卡带彼此相连。奔腾的不只有数据，还有骇客的生命。'),
        ),
        effects={
            '2': '使装备者的欢愉度提高8%。战斗中欢愉度首次达到40%/80%时，使装备者暴击伤害提高20%/32%。',
        },
        set_id=325,
        obtain='鎏金追忆·差分宇宙',
    ),
    RelicSetDef(
        set_name='千星荟萃之城',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='千星城的传媒总部', pos=5, desc='位面球中封装着「星际和平娱乐」的巨构总部——千星城。这座打造过无数巨星的传媒之都，以极高的工业化水准向寰宇放送各类娱乐产品。'),
            SrRelicPieceDef(name='千星城的雇员凭证', pos=6, desc='千星城员工的凭证，标有职级与人员信息。云顶之上与云顶之下，这或许为数不多共享的事物。'),
        ),
        effects={
            '2': '装备者施放追加攻击时，攻击力提高24%，持续2回合。当敌方目标被消灭时，我方全体在本场战斗中暴击伤害提高12%，该效果无法叠加。',
        },
        set_id=326,
        obtain='鎏金追忆·差分宇宙',
    ),
    RelicSetDef(
        set_name='坠星启航地',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='启航地的搁浅列车', pos=5, desc='位面球中封装着曾坠落在此的星穹列车。沉默的星空，冷寂的引擎，一段战火交织的开拓之旅。'),
            SrRelicPieceDef(name='启航地的梦想银轨', pos=6, desc='少女仰望星空，绘出梦想中的银河星轨，希冀有朝一日自己也能去往无垠的未来。'),
        ),
        effects={
            '2': '使装备者的暴击率提高8%。进入战斗时，若装备者与另一名队友均为开拓同行角色，使装备者的暴击伤害提高32%。',
        },
        set_id=327,
        obtain='虫虫来袭·差分宇宙',
    ),
    RelicSetDef(
        set_name='寰宇生研院',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='生研院的中心突触', pos=5, desc='位面球中封装着生命科学研究院的核心区域，研究员如同神经网络中的节点，不断在工业化流程中产出灵感与回馈。'),
            SrRelicPieceDef(name='生研院的外周管线', pos=6, desc='批量生产人造生命的管线，流水线履带轻轻摇晃，总有造物将它误认作母亲与摇篮。'),
        ),
        effects={
            '2': '进入战斗时，若装备者能量上限大于等于200点，每超过1点使装备者造成的伤害提高0.2%，最多提高32%。',
        },
        set_id=328,
        obtain='虫虫来袭·差分宇宙',
    ),
)

# 件名反查索引：模块加载时构建一次（进程内缓存）；192 件名唯一由单测锁定。
PIECE_TO_SET: dict[str, RelicSetDef] = {
    piece.name: relic_set
    for relic_set in RELIC_SETS
    for piece in relic_set.pieces
}

# 套装名 → 定义索引（内部件）：build_set_effects 按 set_name 分组后回查定义用，
# 与 PIECE_TO_SET 同源同载入（件名键 ≠ 套装名键，两索引不可互查）。
_SET_BY_NAME: dict[str, RelicSetDef] = {
    relic_set.set_name: relic_set for relic_set in RELIC_SETS
}

# set_id → 套装定义索引：tid 反查（mys 遗器件 id → 套装）与图标寻址用。
_SET_BY_ID: dict[int, RelicSetDef] = {
    relic_set.set_id: relic_set for relic_set in RELIC_SETS if relic_set.set_id
}

#: 单件图标归档相对路径公式（项目 assets 根起）；192 件全量，见模块 docstring。
_RELIC_ICON_REL_TEMPLATE = 'assets/game_data/relic_icons/iconrelic_{set_id}_{pos}.webp'


def icon_webp_rel_path(set_id: int, pos: int) -> str:
    """套装 set_id + 部位 pos → 单件图标 webp 的项目相对路径。

    纯公式寻址不查存在性（零 IO 纪律）；文件归档见模块 docstring。
    """
    return _RELIC_ICON_REL_TEMPLATE.format(set_id=set_id, pos=pos)


def resolve_set_by_tid(tid: int) -> RelicSetDef | None:
    """mys 遗器件 id（tid）→ 套装定义（miss 返回 None）。

    tid 公式：隧洞 60000+set_id*10+pos、位面饰品 50000+set_id*10+pos
    （2026-11-05 avatar/info 实证；pos 见 SrRelicPieceDef 坐标系）。
    新版本套装未入常量时 miss 返回 None（调用方自行兜底），不抛异常。
    """
    base = 60000 if tid >= 60000 else 50000
    rest = tid - base
    if rest < 0:
        return None
    return _SET_BY_ID.get(rest // 10)


def resolve_set_name(piece_name: str) -> str | None:
    """件名 → 套装名（miss 兜底不抛异常）。

    新版本套装未入常量时 miss 返回 None 并 warning（由映射层落「未知套装」），
    不抛异常；warning 前缀 ``sr_relic_sets:`` 便于日志定位来源。

    Args:
        piece_name: 遗器/饰品件名（game_record 的 name 字段）。

    Returns:
        命中时返回官方套装全名；miss 返回 None。
    """
    relic_set = PIECE_TO_SET.get(piece_name)
    if relic_set is None:
        log.warning(f'sr_relic_sets: 件名「{piece_name}」查无套装（新版本套装未入常量），按未知套装兜底')
        return None
    return relic_set.set_name


def build_set_effects(
    relic_piece_names: list[str],
    ornament_piece_names: list[str],
) -> list[dict]:
    """按套装分组统计佩戴件，产出已激活的套装效果条目列表。

    入参是件名字符串列表（非 SrRelic 对象），避免 mys 数据层与本常量模块的
    循环导入。两个入参的分桶由调用方按部位负责（pos 1-4 遗器 / 5-6 饰品），
    本函数信任分桶不再校验 pos。

    每个套装产出一条::

        {'set_name', 'kind', 'piece_count', 'pieces': [实际佩戴件名],
          'activated': [{'count': 2, 'desc': ...}, {'count': 4, 'desc': ...}]}

    只列已激活档：count=2 需 piece_count≥2；count=4 需 piece_count≥4（且该
    套 effects 带 ``'4'`` 键，即隧洞套——饰品套常量层面无 ``'4'`` 键）。均未
    激活（如饰品只戴 1 件）不产出条目。快照 miss 的件名跳过不产出条目、
    不落 warning——告警责任在 ``resolve_set_name``（映射层逐件调用时触发），
    本函数保持纯函数零日志。

    排序：piece_count 降序、同级按 set_name 升序（中文按码点序，仅供稳定
    输出，无展示语义）。

    Returns:
        套装效果条目列表；无任何激活档时返回空列表。
    """
    worn: dict[str, list[str]] = {}  # set_name → 实际佩戴件名（入参出现顺序）
    for piece_name in (*relic_piece_names, *ornament_piece_names):
        relic_set = PIECE_TO_SET.get(piece_name)
        if relic_set is None:
            continue  # miss 告警由 resolve_set_name 负责，此处静默跳过
        worn.setdefault(relic_set.set_name, []).append(piece_name)

    entries: list[dict] = []
    for set_name, piece_names in worn.items():
        relic_set = _SET_BY_NAME[set_name]
        piece_count = len(piece_names)
        activated: list[dict] = []
        desc_2 = relic_set.effects.get('2')
        if desc_2 is not None and piece_count >= 2:
            activated.append({'count': 2, 'desc': desc_2})
        desc_4 = relic_set.effects.get('4')
        if desc_4 is not None and piece_count >= 4:
            activated.append({'count': 4, 'desc': desc_4})
        if not activated:
            continue  # 一档都没激活（如饰品 1 件）不产出条目
        entries.append({
            'set_name': set_name,
            'kind': relic_set.kind,
            'piece_count': piece_count,
            'pieces': piece_names,
            'activated': activated,
        })
    entries.sort(key=lambda entry: (-entry['piece_count'], entry['set_name']))
    return entries
