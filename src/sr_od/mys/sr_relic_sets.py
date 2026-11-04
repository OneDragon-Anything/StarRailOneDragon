"""米游社遗器套装快照常量与套装效果助手。

设计出处：changes/mys-relic-sets/design.md §1（数据层，用户裁定禁 JSON 数据
文件、数据写代码）。映射内容的权威快照：官方 wiki 遗器频道 2026-11-04 抓取
（版本 3.7；62 套 = 隧洞 34 + 位面饰品 28、件名 192 唯一、2 件效果 62/62、
4 件效果 34/34 齐备、planner 实测件名覆盖 100%）——本模块固化其内容，
禁自行增删改；固化后本模块即唯一权威载体（快照 JSON 为易失本地件）。

版本刷新工序：游戏新版本后重跑 wiki 抓取生成新快照 → 与下方 RELIC_SETS
逐条 diff → 人工审阅后更新常量；新版本套装未及固化时由 ``resolve_set_name``
兜底（warning 不抛异常），勿临时塞未经抓取核验的数据。

模块纪律：零外部 IO、零状态——纯常量 + 纯函数（同 sr_codes 模块纪律）。
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from one_dragon.utils.log_utils import log


@dataclass(frozen=True)
class SrRelicPieceDef:
    """套装单件定义（快照 pieces[].{name, pos} 固化）。

    pos 坐标系：game_record 件 id 公式 60000+set_id*10+pos 的 pos 位——
    隧洞 1=头部 2=手部 3=躯干 4=脚部、位面 5=位面球 6=连结绳（与
    sr_codes.RELIC_POS_CN 同源）；取值时机 = 生成期快照（固化于常量，恒稳）。
    """

    name: str
    pos: int


@dataclass(frozen=True)
class RelicSetDef:
    """套装定义（快照 sets[] 固化）。

    Attributes:
        set_name: 官方套装全名（社区简称不入表；锚点：「骇域漫游的信使」/
            「生命的翁瓦克」）。
        kind: ``'cavern'``=隧洞遗器（4 件套，2/4 件效果）、``'ornament'``=
            位面饰品（2 件套，仅 2 件效果，effects 无 ``'4'`` 键）。
        pieces: 全部件定义（隧洞 4 件 / 饰品 2 件，pos 见 SrRelicPieceDef）。
        effects: 套装效果文案，键 ``'2'``/``'4'``（官方 wiki 原文透传，
            不清洗富文本）。
    """

    set_name: str
    kind: Literal['cavern', 'ornament']
    pieces: tuple[SrRelicPieceDef, ...]
    effects: Mapping[str, str]


RELIC_SETS: tuple[RelicSetDef, ...] = (
    # ---- 隧洞遗器（cavern，34 套，按 set_id 升序）----
    RelicSetDef(
        set_name='云无留迹的过客',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='过客的逢春木簪', pos=1),
            SrRelicPieceDef(name='过客的游龙臂鞲', pos=2),
            SrRelicPieceDef(name='过客的残绣风衣', pos=3),
            SrRelicPieceDef(name='过客的冥途游履', pos=4),
        ),
        effects={
            '2': '治疗量提高10%。',
            '4': '在战斗开始时，立即为我方恢复1个战技点。',
        },
    ),
    RelicSetDef(
        set_name='野穗伴行的快枪手',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='快枪手的野穗毡帽', pos=1),
            SrRelicPieceDef(name='快枪手的粗革手套', pos=2),
            SrRelicPieceDef(name='快枪手的猎风披肩', pos=3),
            SrRelicPieceDef(name='快枪手的铆钉马靴', pos=4),
        ),
        effects={
            '2': '攻击力提高12%。',
            '4': '使装备者的速度提高6%，普攻造成的伤害提高10%。',
        },
    ),
    RelicSetDef(
        set_name='净庭教宗的圣骑士',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='圣骑的宽恕盔面', pos=1),
            SrRelicPieceDef(name='圣骑的沉默誓环', pos=2),
            SrRelicPieceDef(name='圣骑的肃穆胸甲', pos=3),
            SrRelicPieceDef(name='圣骑的秩序铁靴', pos=4),
        ),
        effects={
            '2': '防御力提高15%。',
            '4': '使装备者提供的护盾量提高20%。',
        },
    ),
    RelicSetDef(
        set_name='密林卧雪的猎人',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='雪猎的荒神兜帽', pos=1),
            SrRelicPieceDef(name='雪猎的巨蜥手套', pos=2),
            SrRelicPieceDef(name='雪猎的冰龙披风', pos=3),
            SrRelicPieceDef(name='雪猎的鹿皮软靴', pos=4),
        ),
        effects={
            '2': '冰属性伤害提高10%。',
            '4': '当装备者施放终结技时，暴击伤害提高25%，持续2回合。',
        },
    ),
    RelicSetDef(
        set_name='街头出身的拳王',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='拳王的冠军护头', pos=1),
            SrRelicPieceDef(name='拳王的重炮拳套', pos=2),
            SrRelicPieceDef(name='拳王的贴身护胸', pos=3),
            SrRelicPieceDef(name='拳王的弧步战靴', pos=4),
        ),
        effects={
            '2': '物理属性伤害提高10%。',
            '4': '当装备者施放攻击或受到攻击后，其在本场战斗中攻击力提高5%，最多叠加5层。',
        },
    ),
    RelicSetDef(
        set_name='戍卫风雪的铁卫',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='铁卫的铸铁面盔', pos=1),
            SrRelicPieceDef(name='铁卫的银鳞手甲', pos=2),
            SrRelicPieceDef(name='铁卫的旧制军服', pos=3),
            SrRelicPieceDef(name='铁卫的白银护胫', pos=4),
        ),
        effects={
            '2': '受到伤害降低8%。',
            '4': '回合开始时，如果装备者当前生命值百分比小于等于50%，则回复等同于自身生命上限8%的生命值，并恢复5点能量。',
        },
    ),
    RelicSetDef(
        set_name='熔岩锻铸的火匠',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='火匠的黑曜目镜', pos=1),
            SrRelicPieceDef(name='火匠的御火戒指', pos=2),
            SrRelicPieceDef(name='火匠的阻燃围裙', pos=3),
            SrRelicPieceDef(name='火匠的合金义肢', pos=4),
        ),
        effects={
            '2': '火属性伤害提高10%。',
            '4': '使装备者战技造成的伤害提高12%，并使施放终结技后的下一次攻击造成的火属性伤害提高12%。',
        },
    ),
    RelicSetDef(
        set_name='繁星璀璨的天才',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='天才的超距遥感', pos=1),
            SrRelicPieceDef(name='天才的频变捕手', pos=2),
            SrRelicPieceDef(name='天才的元域深潜', pos=3),
            SrRelicPieceDef(name='天才的引力漫步', pos=4),
        ),
        effects={
            '2': '量子属性伤害提高10%。',
            '4': '当装备者对敌方目标造成伤害时，无视其10%的防御力。若目标拥有量子属性弱点，额外无视其10%的防御力。',
        },
    ),
    RelicSetDef(
        set_name='激奏雷电的乐队',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='乐队的偏光墨镜', pos=1),
            SrRelicPieceDef(name='乐队的巡演手绳', pos=2),
            SrRelicPieceDef(name='乐队的钉刺皮衣', pos=3),
            SrRelicPieceDef(name='乐队的铆钉短靴', pos=4),
        ),
        effects={
            '2': '雷属性伤害提高10%。',
            '4': '当装备者施放战技时，使装备者的攻击力提高20%，持续1回合。',
        },
    ),
    RelicSetDef(
        set_name='晨昏交界的翔鹰',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='翔鹰的长喙头盔', pos=1),
            SrRelicPieceDef(name='翔鹰的鹰击指环', pos=2),
            SrRelicPieceDef(name='翔鹰的翼装束带', pos=3),
            SrRelicPieceDef(name='翔鹰的绒羽绑带', pos=4),
        ),
        effects={
            '2': '风属性伤害提高10%。',
            '4': '当装备者施放终结技后，使其行动提前25%。',
        },
    ),
    RelicSetDef(
        set_name='流星追迹的怪盗',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='怪盗的千人假面', pos=1),
            SrRelicPieceDef(name='怪盗的绘纹手套', pos=2),
            SrRelicPieceDef(name='怪盗的纤钢爪钩', pos=3),
            SrRelicPieceDef(name='怪盗的流星快靴', pos=4),
        ),
        effects={
            '2': '击破特攻提高16%。',
            '4': '使装备者的击破特攻提高16%。当装备者击破敌方目标弱点后，恢复3点能量。',
        },
    ),
    RelicSetDef(
        set_name='盗匪荒漠的废土客',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='废土客的呼吸面罩', pos=1),
            SrRelicPieceDef(name='废土客的荒漠终端', pos=2),
            SrRelicPieceDef(name='废土客的修士长袍', pos=3),
            SrRelicPieceDef(name='废土客的动力腿甲', pos=4),
        ),
        effects={
            '2': '虚数属性伤害提高10%。',
            '4': '装备者对陷入负面效果的敌方目标造成伤害时暴击率提高10%，对陷入禁锢状态的敌方目标造成伤害时暴击伤害提高20%。',
        },
    ),
    RelicSetDef(
        set_name='宝命长存的莳者',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='莳者的复明义眼', pos=1),
            SrRelicPieceDef(name='莳者的机巧木手', pos=2),
            SrRelicPieceDef(name='莳者的承露羽衣', pos=3),
            SrRelicPieceDef(name='莳者的天人丝履', pos=4),
        ),
        effects={
            '2': '生命上限提高12%。',
            '4': '当装备者受到攻击或被我方目标消耗生命值后，暴击率提高8%，持续2回合，该效果最多叠加2层。',
        },
    ),
    RelicSetDef(
        set_name='骇域漫游的信使',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='信使的全息目镜', pos=1),
            SrRelicPieceDef(name='信使的百变义手', pos=2),
            SrRelicPieceDef(name='信使的密信挎包', pos=3),
            SrRelicPieceDef(name='信使的酷跑板鞋', pos=4),
        ),
        effects={
            '2': '速度提高6%。',
            '4': '当装备者对我方目标施放终结技时，我方全体速度提高12%，持续1回合，该效果无法叠加。',
        },
    ),
    RelicSetDef(
        set_name='毁烬焚骨的大公',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='大公的冥焰冠冕', pos=1),
            SrRelicPieceDef(name='大公的绒火指套', pos=2),
            SrRelicPieceDef(name='大公的蒙恩长袍', pos=3),
            SrRelicPieceDef(name='大公的绅雅礼靴', pos=4),
        ),
        effects={
            '2': '追加攻击造成的伤害提高20%。',
            '4': '装备者施放追加攻击时，根据追加攻击造成伤害的次数，每次造成伤害时使装备者的攻击力提高6%，最多叠加8次，持续3回合。该效果在装备者下次施放追加攻击时移除。',
        },
    ),
    RelicSetDef(
        set_name='幽锁深牢的系囚',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='系囚的合啮拘笼', pos=1),
            SrRelicPieceDef(name='系囚的铅石梏铐', pos=2),
            SrRelicPieceDef(name='系囚的幽闭缚束', pos=3),
            SrRelicPieceDef(name='系囚的绝足锁桎', pos=4),
        ),
        effects={
            '2': '攻击力提高12%。',
            '4': '敌方目标每承受1个持续伤害效果，装备者对其造成伤害时就无视其6%的防御力，最多计入3个持续伤害效果。',
        },
    ),
    RelicSetDef(
        set_name='死水深潜的先驱',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='先驱的绝热围壳', pos=1),
            SrRelicPieceDef(name='先驱的虚极罗盘', pos=2),
            SrRelicPieceDef(name='先驱的密合铅衣', pos=3),
            SrRelicPieceDef(name='先驱的泊星桩锚', pos=4),
        ),
        effects={
            '2': '对受负面状态影响的敌人造成的伤害提高12%。',
            '4': '暴击率提高4%，装备者对陷入不少于2/3个负面效果的敌方目标造成的暴击伤害提高8%/12%。装备者对敌方目标施加负面效果后，上述效果提高100%，持续1回合。',
        },
    ),
    RelicSetDef(
        set_name='机心戏梦的钟表匠',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='钟表匠的极目透镜', pos=1),
            SrRelicPieceDef(name='钟表匠的交运腕表', pos=2),
            SrRelicPieceDef(name='钟表匠的空幻礼服', pos=3),
            SrRelicPieceDef(name='钟表匠的隐梦革履', pos=4),
        ),
        effects={
            '2': '击破特攻提高16%。',
            '4': '当装备者对我方目标施放终结技时，我方全体击破特攻提高30%，持续2回合，该效果无法叠加。',
        },
    ),
    RelicSetDef(
        set_name='荡除蠹灾的铁骑',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='铁骑的索敌战盔', pos=1),
            SrRelicPieceDef(name='铁骑的摧坚铁腕', pos=2),
            SrRelicPieceDef(name='铁骑的银影装甲', pos=3),
            SrRelicPieceDef(name='铁骑的行空护胫', pos=4),
        ),
        effects={
            '2': '击破特攻提高16%。',
            '4': '当装备者的击破特攻大于等于150%时，对敌方目标造成的击破伤害无视其10%的防御力。当装备者的击破特攻大于等于250%时，对敌方目标造成的超击破伤害额外无视其15%的防御力。',
        },
    ),
    RelicSetDef(
        set_name='风举云飞的勇烈',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='勇烈的玄枵面甲', pos=1),
            SrRelicPieceDef(name='勇烈的钩爪腕甲', pos=2),
            SrRelicPieceDef(name='勇烈的飞翎瓷甲', pos=3),
            SrRelicPieceDef(name='勇烈的逐猎腿甲', pos=4),
        ),
        effects={
            '2': '攻击力提高12%。',
            '4': '使装备者的暴击率提高6%，装备者施放追加攻击时，使终结技造成的伤害提高36%，持续1回合。',
        },
    ),
    RelicSetDef(
        set_name='重循苦旅的司铎',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='司铎的律音耳坠', pos=1),
            SrRelicPieceDef(name='司铎的授邀手套', pos=2),
            SrRelicPieceDef(name='司铎的圣职礼服', pos=3),
            SrRelicPieceDef(name='司铎的苦旅短靴', pos=4),
        ),
        effects={
            '2': '速度提高6%。',
            '4': '对我方单体目标施放战技或终结技时，使技能目标的暴击伤害提高18%，持续2回合，该效果最多叠加2次。',
        },
    ),
    RelicSetDef(
        set_name='识海迷坠的学者',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='学者的银边视镜', pos=1),
            SrRelicPieceDef(name='学者的辅助指节', pos=2),
            SrRelicPieceDef(name='学者的粗纺外套', pos=3),
            SrRelicPieceDef(name='学者的绒皮雪靴', pos=4),
        ),
        effects={
            '2': '暴击率提高8%。',
            '4': '战技和终结技造成的伤害提高20%，施放终结技后，下一次施放战技时造成的伤害额外提高25%。',
        },
    ),
    RelicSetDef(
        set_name='凯歌祝捷的英豪',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='英豪的冠军桂冠', pos=1),
            SrRelicPieceDef(name='英豪的鉴金腕铠', pos=2),
            SrRelicPieceDef(name='英豪的骁战金甲', pos=3),
            SrRelicPieceDef(name='英豪的赴火护胫', pos=4),
        ),
        effects={
            '2': '攻击力提高12%。',
            '4': '装备者的忆灵在场时，装备者的速度提高6%，装备者的忆灵攻击时，装备者和忆灵的暴击伤害提高30%，持续2回合。',
        },
    ),
    RelicSetDef(
        set_name='哀歌覆国的诗人',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='诗人的莳萝花冠', pos=1),
            SrRelicPieceDef(name='诗人的贵金手镯', pos=2),
            SrRelicPieceDef(name='诗人的缀星裙摆', pos=3),
            SrRelicPieceDef(name='诗人的钉银之履', pos=4),
        ),
        effects={
            '2': '量子属性伤害提高10%。',
            '4': '使装备者的速度降低8%。进入战斗前，若装备者的速度小于110/95，使装备者的暴击率提高20%/32%。该效果同时对装备者的忆灵生效。',
        },
    ),
    RelicSetDef(
        set_name='烈阳惊雷的女武神',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='女武神的翱翔翼盔', pos=1),
            SrRelicPieceDef(name='女武神的骑枪手铠', pos=2),
            SrRelicPieceDef(name='女武神的启程披风', pos=3),
            SrRelicPieceDef(name='女武神的勋礼马刺', pos=4),
        ),
        effects={
            '2': '速度提高6%。',
            '4': '当装备者及其忆灵为装备者及其忆灵以外的我方目标提供治疗后，使装备者获得【甘霖】，每回合最多触发1次，持续2回合。装备者持有【甘霖】时，速度提高6%，我方全体暴击伤害提高15%，该效果无法叠加。',
        },
    ),
    RelicSetDef(
        set_name='恶海逐波的船长',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='船长的领航笠帽', pos=1),
            SrRelicPieceDef(name='船长的捕光星盘', pos=2),
            SrRelicPieceDef(name='船长的驭风斗篷', pos=3),
            SrRelicPieceDef(name='船长的踏浪游靴', pos=4),
        ),
        effects={
            '2': '暴击伤害提高16%。',
            '4': '装备者成为其他我方目标的技能目标时，获得1层【助力】，最多叠加2层。施放终结技时，若持有2层【助力】，消耗所有【助力】，使装备者攻击力提高48%，持续1回合。',
        },
    ),
    RelicSetDef(
        set_name='再创天地的救世主',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='救世主的登程风帽', pos=1),
            SrRelicPieceDef(name='救世主的执剑护手', pos=2),
            SrRelicPieceDef(name='救世主的传承战袍', pos=3),
            SrRelicPieceDef(name='救世主的拓荒长靴', pos=4),
        ),
        effects={
            '2': '暴击率提高8%。',
            '4': '装备者施放普攻或战技后，若装备者的忆灵在场，使装备者及其忆灵生命上限提高24%，我方全体造成的伤害提高15%，持续至装备者下次施放普攻或战技后。',
        },
    ),
    RelicSetDef(
        set_name='自匿星芒的隐士',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='隐士的宽檐呢帽', pos=1),
            SrRelicPieceDef(name='隐士的简雅腕表', pos=2),
            SrRelicPieceDef(name='隐士的驼色夹克', pos=3),
            SrRelicPieceDef(name='隐士的麂皮软鞋', pos=4),
        ),
        effects={
            '2': '提供的护盾量提高10%。',
            '4': '使装备者提供的护盾量提高12%，我方目标持有装备者提供的护盾时，暴击伤害提高15%。',
        },
    ),
    RelicSetDef(
        set_name='闪耀功勋的魔法少女',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='魔法少女的闪耀勋章', pos=1),
            SrRelicPieceDef(name='魔法少女的守护手套', pos=2),
            SrRelicPieceDef(name='魔法少女的永舞战裙', pos=3),
            SrRelicPieceDef(name='魔法少女的缔约长靴', pos=4),
        ),
        effects={
            '2': '暴击伤害提高16%。',
            '4': '装备者及其忆灵造成的欢愉伤害无视目标10%的防御力，我方每累计获得5点笑点，造成的欢愉伤害额外无视目标1%的防御力，最多叠加10层。',
        },
    ),
    RelicSetDef(
        set_name='应天涉远的卜者',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='卜者的演算玉兆', pos=1),
            SrRelicPieceDef(name='卜者的机巧义手', pos=2),
            SrRelicPieceDef(name='卜者的观天星袍', pos=3),
            SrRelicPieceDef(name='卜者的飞腾云履', pos=4),
        ),
        effects={
            '2': '速度提高6%。',
            '4': '进入战斗前，若装备者的速度大于等于120/160，使装备者的暴击率提高10%/18%。装备者每场战斗首次施放欢愉技时，使我方全体欢愉度提高10%，该效果无法叠加。',
        },
    ),
    RelicSetDef(
        set_name='星如我见的领航员',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='领航员的深空之镜', pos=1),
            SrRelicPieceDef(name='领航员的游戏之骰', pos=2),
            SrRelicPieceDef(name='领航员的星图制服', pos=3),
            SrRelicPieceDef(name='领航员的永行魔靴', pos=4),
        ),
        effects={
            '2': '攻击力提高12%。',
            '4': '装备者进入战斗时/施放战技时，造成的战技与终结技伤害提高18%，最多叠加3层，装备者回合开始时/施放终结技后，移除1层该效果。',
        },
    ),
    RelicSetDef(
        set_name='叩问天工的名冶',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='名冶的火兽面罩', pos=1),
            SrRelicPieceDef(name='名冶的镔铁护手', pos=2),
            SrRelicPieceDef(name='名冶的辟火匠衫', pos=3),
            SrRelicPieceDef(name='名冶的无拘重靴', pos=4),
        ),
        effects={
            '2': '生命上限提高12%。',
            '4': '装备者对防御力降低状态的敌方目标造成的暴击伤害提高28%。装备者对敌方目标施加防御力降低状态后，使我方全体获得【助燃】，持续2回合，该效果无法叠加，持有【助燃】的我方目标造成的伤害提高15%。该效果在装备者施放攻击后可再次触发。',
        },
    ),
    RelicSetDef(
        set_name='戏梦点星的伶人',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='伶人的悲泣假面', pos=1),
            SrRelicPieceDef(name='伶人的斑斓折扇', pos=2),
            SrRelicPieceDef(name='伶人的滑稽戏服', pos=3),
            SrRelicPieceDef(name='伶人的弯月舞靴', pos=4),
        ),
        effects={
            '2': '速度提高6%。',
            '4': '当装备者对我方其他单体目标施放战技或终结技时，使技能目标的欢愉度提高16%，持续3回合，若装备者持有的好活当赏大于等于10点，则额外使我方全体目标的暴击伤害提高12%，持续3回合。',
        },
    ),
    RelicSetDef(
        set_name='贪噬禁果的异端',
        kind='cavern',
        pieces=(
            SrRelicPieceDef(name='异端的颅脑仪器', pos=1),
            SrRelicPieceDef(name='异端的注射手套', pos=2),
            SrRelicPieceDef(name='异端的理性束衣', pos=3),
            SrRelicPieceDef(name='异端的饥饿短靴', pos=4),
        ),
        effects={
            '2': '暴击伤害提高16%。',
            '4': '使装备者普攻造成的伤害提高36%。当装备者施放普攻时，使装备者的攻击力提高20%，持续2回合。',
        },
    ),
    # ---- 位面饰品（ornament，28 套，按 set_id 升序）----
    RelicSetDef(
        set_name='太空封印站',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='「黑塔」的空间站点', pos=5),
            SrRelicPieceDef(name='「黑塔」的漫历轨迹', pos=6),
        ),
        effects={
            '2': '使装备者的攻击力提高12%。当装备者的速度大于等于120时，攻击力额外提高12%。',
        },
    ),
    RelicSetDef(
        set_name='不老者的仙舟',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='罗浮仙舟的天外楼船', pos=5),
            SrRelicPieceDef(name='罗浮仙舟的建木枝蔓', pos=6),
        ),
        effects={
            '2': '使装备者的生命上限提高12%。当装备者的速度大于等于120时，我方全体攻击力提高8%。',
        },
    ),
    RelicSetDef(
        set_name='泛银河商业公司',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='公司的巨构总部', pos=5),
            SrRelicPieceDef(name='公司的贸易航道', pos=6),
        ),
        effects={
            '2': '使装备者的效果命中提高10%。同时提高装备者等同于当前效果命中25%的攻击力，最多提高25%。',
        },
    ),
    RelicSetDef(
        set_name='筑城者的贝洛伯格',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='贝洛伯格的存护堡垒', pos=5),
            SrRelicPieceDef(name='贝洛伯格的铁卫防线', pos=6),
        ),
        effects={
            '2': '使装备者的防御力提高15%。当装备者的效果命中大于等于50%时，防御力额外提高15%。',
        },
    ),
    RelicSetDef(
        set_name='星体差分机',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='螺丝星的机械烈阳', pos=5),
            SrRelicPieceDef(name='螺丝星的环星孔带', pos=6),
        ),
        effects={
            '2': '使装备者的暴击伤害提高16%。当装备者的暴击伤害大于等于120%时，进入战斗后装备者的暴击率提高60%，持续到施放首次攻击后结束。',
        },
    ),
    RelicSetDef(
        set_name='停转的萨尔索图',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='萨尔索图的移动城市', pos=5),
            SrRelicPieceDef(name='萨尔索图的晨昏界线', pos=6),
        ),
        effects={
            '2': '使装备者的暴击率提高8%。当装备者当前暴击率大于等于50%时，终结技和追加攻击造成的伤害提高15%。',
        },
    ),
    RelicSetDef(
        set_name='盗贼公国塔利亚',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='塔利亚的钉壳小镇', pos=5),
            SrRelicPieceDef(name='塔利亚的裸皮电线', pos=6),
        ),
        effects={
            '2': '使装备者的击破特攻提高16%。当装备者的速度大于等于145时，击破特攻额外提高20%。',
        },
    ),
    RelicSetDef(
        set_name='生命的翁瓦克',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='翁瓦克的诞生之岛', pos=5),
            SrRelicPieceDef(name='翁瓦克的环岛海岸', pos=6),
        ),
        effects={
            '2': '使装备者的能量恢复效率提高5%。当装备者的速度大于等于120时，进入战斗时立刻使行动提前40%。',
        },
    ),
    RelicSetDef(
        set_name='繁星竞技场',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='泰科铵的镭射球场', pos=5),
            SrRelicPieceDef(name='泰科铵的弧光赛道', pos=6),
        ),
        effects={
            '2': '使装备者的暴击率提高8%。当装备者当前暴击率大于等于70%时，普攻和战技造成的伤害提高20%。',
        },
    ),
    RelicSetDef(
        set_name='折断的龙骨',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='伊须磨洲的残船鲸落', pos=5),
            SrRelicPieceDef(name='伊须磨洲的坼裂缆索', pos=6),
        ),
        effects={
            '2': '使装备者的效果抵抗提高10%。当装备者的效果抵抗大于等于30%时，我方全体暴击伤害提高10%。',
        },
    ),
    RelicSetDef(
        set_name='苍穹战线格拉默',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='格拉默的铁骑兵团', pos=5),
            SrRelicPieceDef(name='格拉默的寂静坟碑', pos=6),
        ),
        effects={
            '2': '使装备者的攻击力提高12%。当装备者的速度大于等于135/160时，使装备者造成的伤害提高12%/18%。',
        },
    ),
    RelicSetDef(
        set_name='梦想之地匹诺康尼',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='匹诺康尼的堂皇酒店', pos=5),
            SrRelicPieceDef(name='匹诺康尼的逐梦轨道', pos=6),
        ),
        effects={
            '2': '使装备者的能量恢复效率提高5%。使队伍中与装备者属性相同的我方其他角色造成的伤害提高10%。',
        },
    ),
    RelicSetDef(
        set_name='无主荒星茨冈尼亚',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='茨冈尼亚的母神卧榻', pos=5),
            SrRelicPieceDef(name='茨冈尼亚的轮回纽结', pos=6),
        ),
        effects={
            '2': '使装备者的暴击率提高4%。当敌方目标被消灭时，装备者暴击伤害提高4%，最多叠加10层。',
        },
    ),
    RelicSetDef(
        set_name='出云显世与高天神国',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='出云的祸津众神', pos=5),
            SrRelicPieceDef(name='出云的终始一刀', pos=6),
        ),
        effects={
            '2': '使装备者的攻击力提高12%。进入战斗时，若至少存在一名与装备者命途相同的队友，装备者的暴击率提高12%。',
        },
    ),
    RelicSetDef(
        set_name='奔狼的都蓝王朝',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='都蓝的穹窿金帐', pos=5),
            SrRelicPieceDef(name='都蓝的器兽缰辔', pos=6),
        ),
        effects={
            '2': '我方角色施放追加攻击时，装备者获得一层【功勋】，最多叠加5层，每层【功勋】使装备者追加攻击造成的伤害提高5%，叠满5层时，额外使装备者的暴击伤害提高25%。',
        },
    ),
    RelicSetDef(
        set_name='劫火莲灯铸炼宫',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='铸炼宫的莲华灯芯', pos=5),
            SrRelicPieceDef(name='铸炼宫的焰轮天绸', pos=6),
        ),
        effects={
            '2': '使装备者的速度提高6%。当装备者击中拥有火属性弱点的敌方目标时，击破特攻提高40%，持续1回合。',
        },
    ),
    RelicSetDef(
        set_name='沉陆海域露莎卡',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='露莎卡的水朽苍都', pos=5),
            SrRelicPieceDef(name='露莎卡的双生航道', pos=6),
        ),
        effects={
            '2': '使装备者的能量恢复效率提高5%，如果装备者不是编队中的第一位角色，使编队中的第一位角色攻击力提高12%。',
        },
    ),
    RelicSetDef(
        set_name='奇想蕉乐园',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='蕉乐园的蕉芯广场', pos=5),
            SrRelicPieceDef(name='蕉乐园的模因线缆', pos=6),
        ),
        effects={
            '2': '使装备者的暴击伤害提高16%，当存在装备者召唤的目标时，暴击伤害额外提高32%。',
        },
    ),
    RelicSetDef(
        set_name='谧宁拾骨地',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='哀地里亚的殁名祭碑', pos=5),
            SrRelicPieceDef(name='哀地里亚的入溟骨链', pos=6),
        ),
        effects={
            '2': '使装备者的生命上限提高12%。当装备者的生命上限大于等于5000点时，使装备者及其忆灵的暴击伤害提高28%。',
        },
    ),
    RelicSetDef(
        set_name='渊思寂虑的巨树',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='神悟树庭的沉思巨桹', pos=5),
            SrRelicPieceDef(name='神悟树庭的联识叶路', pos=6),
        ),
        effects={
            '2': '使装备者的速度提高6%。当装备者的速度大于等于135/180时，使装备者及其忆灵的治疗量提高12%/20%。',
        },
    ),
    RelicSetDef(
        set_name='妖精织梦的乐园',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='迷路迷境的恬梦树屋', pos=5),
            SrRelicPieceDef(name='迷路迷境的祈愿笛哨', pos=6),
        ),
        effects={
            '2': '队伍中当前在场的我方目标数量不等于4时，每多/少1名我方目标，使装备者及其忆灵造成的伤害提高9%/12%，最多叠加4/3层。',
        },
    ),
    RelicSetDef(
        set_name='沉欢醉饮的海隅',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='酣歌海垠的礁屿灯塔', pos=5),
            SrRelicPieceDef(name='酣歌海垠的歌咏步道', pos=6),
        ),
        effects={
            '2': '使装备者的攻击力提高12%。当装备者的攻击力大于等于2400/3600时，使造成的持续伤害额外提高12%/24%。',
        },
    ),
    RelicSetDef(
        set_name='永恒之地翁法罗斯',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='翁法罗斯的西风尽途', pos=5),
            SrRelicPieceDef(name='翁法罗斯的永恒诗篇', pos=6),
        ),
        effects={
            '2': '使装备者的暴击率提高8%。装备者的忆灵在场时，我方全体速度提高8%，该效果无法叠加。',
        },
    ),
    RelicSetDef(
        set_name='天国@直播间',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='直播间的千窗万面', pos=5),
            SrRelicPieceDef(name='直播间的畅聊语流', pos=6),
        ),
        effects={
            '2': '使装备者的暴击伤害提高16%，若在同一回合内消耗大于等于3点战技点，额外使装备者暴击伤害提高32%，持续3回合。',
        },
    ),
    RelicSetDef(
        set_name='零号关卡朋克洛德',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='朋克洛德的虹霓都市', pos=5),
            SrRelicPieceDef(name='朋克洛德的数据洪流', pos=6),
        ),
        effects={
            '2': '使装备者的欢愉度提高8%。战斗中欢愉度首次达到40%/80%时，使装备者暴击伤害提高20%/32%。',
        },
    ),
    RelicSetDef(
        set_name='千星荟萃之城',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='千星城的传媒总部', pos=5),
            SrRelicPieceDef(name='千星城的雇员凭证', pos=6),
        ),
        effects={
            '2': '装备者施放追加攻击时，攻击力提高24%，持续2回合。当敌方目标被消灭时，我方全体在本场战斗中暴击伤害提高12%，该效果无法叠加。',
        },
    ),
    RelicSetDef(
        set_name='坠星启航地',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='启航地的搁浅列车', pos=5),
            SrRelicPieceDef(name='启航地的梦想银轨', pos=6),
        ),
        effects={
            '2': '使装备者的暴击率提高8%。进入战斗时，若装备者与另一名队友均为开拓同行角色，使装备者的暴击伤害提高32%。',
        },
    ),
    RelicSetDef(
        set_name='寰宇生研院',
        kind='ornament',
        pieces=(
            SrRelicPieceDef(name='生研院的中心突触', pos=5),
            SrRelicPieceDef(name='生研院的外周管线', pos=6),
        ),
        effects={
            '2': '进入战斗时，若装备者能量上限大于等于200点，每超过1点使装备者造成的伤害提高0.2%，最多提高32%。',
        },
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
