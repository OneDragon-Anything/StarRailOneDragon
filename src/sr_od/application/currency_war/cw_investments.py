# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 投资策略 + 投资环境领域模型(meta 层,V4.4)。

**来源**:米游社百科「货币战争图鉴」投资策略 `channel/map/209/212`(216)、投资环境 `/213`,
+ 游戏内「数据银行」投资环境图鉴核对(2026-08-06,;游戏内总 83 / 解锁 68)。
投资环境全量在本注册表(``INVESTMENT_ENVS``,代码单一源 —— 原 ``investment_envs.md`` doc 已删,
用户原则:代码已建模的游戏数据不存 doc);投资策略全量 216 在 ``investment_strategies.md``(本表只收 T0)。

**用途**:
- ``InvestmentEnv``(概念股/邀请/契约/时代/经济/规则/专家):**带 faction 字段** —— 概念股/邀请/命运圣杯
  对应哪个阵营是派生 ENV_FACTION_MAP 的单一真相源(改注册表自动传导,取代 cw_comps 硬编码)。
  起 INVESTMENT_ENVS 收全部「有名」环境(投资环境屏 OCR 名 → effect/category 查表,识别全集)。
- ``InvestmentStrategy``(局内 3 选 1):event_whitelist 的规范名来源。

**为什么建模**(用户 2026-08-03):核心实体建正规 model 类 + 注册表(可查询/校验/派生),非散 dict。

⚠️ INVESTMENT_ENVS 已全量(7 类有名环境);INVESTMENT_STRATEGIES 仍只收 T0(event_whitelist 用),
全量 216 在 doc,随事件/补给决策(阶段 3a)接线补全。env_fit 策略影响目前只用「阵营亲和」一维
(概念股/邀请/命运圣杯),其余类别(契约/时代/经济/规则/专家)效果异质,待分类建模(阶段 3a)。
版本依赖:赛季扩充会新增/调整(如命运圣杯 = Fate 联动阵营,新增)。
"""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class InvestmentEnv:
    """投资环境(开局/固定节点整局增益)。"""
    name: str           # 规范名(如"昼之半神概念股")
    category: str       # "概念股"/"邀请"/"契约"/"时代"/"经济"/"规则"/"专家"
    effect: str         # 效果原文
    faction: str = ""   # 对应阵营(概念股/邀请 boosts 的羁绊;ENV_FACTION_MAP 派生用;无则 "")
    source: str = ""    # content_id


@dataclass(frozen=True)
class EconomyEffect:
    """投资策略/环境的**可数值化经济效果**(ADR-0131;用户 2026-08-15:效果要直接转经济模型)。

    只收能进策略层算账的效果(给金/免费刷新/利息/经验/连胜倍率);战力类(数值碾压/攻防一体等)
    不在此(走战力评估,不进经济)。全 0/None = 无经济效果。字段语义:
    - instant_gold: 选牌当场给金(一次性)
    - gold_per_node: 每次进入新节点给金
    - free_refresh_per_node: 每节点免费刷新次数(成本 0 的刷新)
    - free_refresh_burst: 一次性海量免费刷新(如高效决策 9999 次);限时窗口策略层不编排时机(执行层待办)
    - refresh_surprise_every: 每 N 次刷新刷出 5 张同费卡(采购专员;稳定器,提高刷新期望)
    - gold_per_three_5cost: 每购买 3 个 5 费角色给金
    - interest_cap_override: 利息档上限覆写(开源节流 9 档/利息上调 10 档/买断制 0)
    - xp_per_refresh: 每次刷新 +经验
    - xp_per_node: 每节点 +经验
    - xp_buy_cost_discount: 每击「购买经验」减金
    - win_reward_mult: 连胜奖励倍率(伟大征服 3)
    """
    instant_gold: int = 0
    gold_per_node: int = 0
    free_refresh_per_node: int = 0
    free_refresh_burst: int = 0
    refresh_surprise_every: int = 0
    gold_per_three_5cost: int = 0
    interest_cap_override: int | None = None
    xp_per_refresh: int = 0
    xp_per_node: int = 0
    xp_buy_cost_discount: int = 0
    win_reward_mult: float = 1.0


@dataclass(frozen=True)
class InvestmentStrategy:
    """投资策略(局内 3 选 1,可刷新)。"""
    name: str           # 规范名
    rarity: str         # "棱彩"/"金"/"银"
    effect: str
    source: str = ""
    economy: EconomyEffect | None = None   # 可数值化经济效果(ADR-0131);战力类 None


def _env(name: str, category: str, effect: str, faction: str = "", source: str = "") -> InvestmentEnv:
    return InvestmentEnv(name=name, category=category, effect=effect, faction=faction, source=source)


def _strat(name: str, rarity: str, effect: str, source: str = "",
          economy: EconomyEffect | None = None) -> InvestmentStrategy:
    return InvestmentStrategy(name=name, rarity=rarity, effect=effect, source=source, economy=economy)


# ===== INVESTMENT_ENVS 注册表(全量;🟢 米游社原文 + 数据银行补;带 faction)=====
# faction 仅概念股/邀请/命运圣杯契约有(加成对应阵营);其余类别效果异质,策略影响待分类建模(阶段 3a)。
# (只剩持续伤害/量子同频的「邀请」「契约」形态)。新增:战技点概念股(实存)、红钻/蓝钻贵族、
# 命运圣杯邀请/契约(Fate 联动阵营)。
INVESTMENT_ENVS: dict[str, InvestmentEnv] = {e.name: e for e in [
    # —— 概念股(开局送阵营角色+装备+刷新率)—— faction = 该阵营
    _env("追击概念股", "概念股", "开局获得【追击】角色+简易装备,【追击】刷新率提高", "追击", "6107"),
    _env("击破概念股", "概念股", "开局获得【击破】角色+简易装备,【击破】刷新率提高", "击破", "6139"),
    _env("群攻概念股", "概念股", "开局获得【群攻】角色+简易装备,【群攻】刷新率提高", "群攻", "6138"),
    _env("能量概念股", "概念股", "开局获得【能量】角色+简易装备,【能量】刷新率提高", "能量", "6109"),
    _env("燃血概念股", "概念股", "开局获得【燃血】角色+简易装备,【燃血】刷新率提高", "燃血", "6108"),
    _env("减益概念股", "概念股", "开局获得【减益】角色+简易装备,【减益】刷新率提高", "减益", "6124"),
    _env("战技点概念股", "概念股", "开局时获得【战技点】角色和初始简易装备,【战技点】角色的刷新概率提高", "战技点"),
    _env("仙舟概念股", "概念股", "开局获得【仙舟】角色+简易装备,【仙舟】刷新率提高", "仙舟", "6142"),
    _env("贝洛伯格概念股", "概念股", "开局获得【贝洛伯格】角色+简易装备,【贝洛伯格】刷新率提高", "贝洛伯格", "6144"),
    _env("狼狩概念股", "概念股", "开局获得【狼狩】角色+简易装备,【狼狩】刷新率提高", "狼狩", "6141"),
    _env("星间旅人概念股", "概念股", "开局获得【星间旅人】角色+简易装备,刷新率提高", "星间旅人", "6143"),
    _env("银河学者概念股", "概念股", "开局获得【银河学者】角色+简易装备,刷新率提高", "银河学者", "6111"),
    _env("列车同行概念股", "概念股", "开局获得【列车同行】角色+简易装备,刷新率提高", "列车同行", "6110"),
    _env("昼之半神概念股", "概念股", "开局获得【昼之半神】角色+简易装备,刷新率提高", "昼之半神", "6140"),
    _env("夜之半神概念股", "概念股", "开局获得【夜之半神】角色+简易装备,刷新率提高", "夜之半神", "6122"),
    # —— 邀请(获得阵营星徽)—— faction = 该阵营
    _env("仙舟邀请", "邀请", "获得一个【仙舟星徽】", "仙舟", "6128"),
    _env("贝洛伯格邀请", "邀请", "获得一个【贝洛伯格星徽】", "贝洛伯格", "6127"),
    _env("狼狩邀请", "邀请", "获得一个【狼狩星徽】", "狼狩", "6129"),
    _env("盛会之星邀请", "邀请", "获得一个【盛会之星星徽】", "盛会之星", "6130"),
    _env("星间旅人邀请", "邀请", "获得一个【星间旅人星徽】", "星间旅人", "6126"),
    _env("银河学者邀请", "邀请", "获得一个【银河学者星徽】", "银河学者", "6125"),
    _env("列车同行邀请", "邀请", "获得一个【列车同行星徽】", "列车同行", "6123"),
    _env("昼之半神邀请", "邀请", "获得一个【昼之半神星徽】", "昼之半神", "6131"),
    _env("夜之半神邀请", "邀请", "获得一个【夜之半神星徽】", "夜之半神", "6112"),
    _env("追击邀请", "邀请", "获得一个【追击星徽】", "追击", "6113"),
    _env("击破邀请", "邀请", "获得一个【击破星徽】", "击破", "6114"),
    _env("群攻邀请", "邀请", "获得一个【群攻星徽】", "群攻", "6115"),
    _env("能量邀请", "邀请", "获得一个【能量星徽】", "能量", "6116"),
    _env("燃血邀请", "邀请", "获得一个【燃血星徽】", "燃血", "6117"),
    _env("减益邀请", "邀请", "获得一个【减益星徽】", "减益", "6119"),
    _env("持续伤害邀请", "邀请", "获得一个【持续伤害星徽】", "持续伤害", "6118"),
    _env("量子同频邀请", "邀请", "获得一个【量子同频星徽】", "量子同频", "6120"),
    _env("战技点邀请", "邀请", "获得一个【战技点星徽】", "战技点", "6121"),
    _env("欢愉邀请", "邀请", "获得一个【欢愉星徽】", "欢愉", "7451"),
    _env("命运圣杯邀请", "邀请", "获得1个【命运圣杯星徽】", "命运圣杯"),
    # —— 契约(送特定角色+条件解锁更多)——
    _env("星核猎手契约", "契约", "获得【卡芙卡】。当【刃】【卡芙卡】【银狼LV.999】或【银狼】一起参与一次战斗后,获得【流萤】,在2个节点后才能将其上场。", source="6105"),
    _env("战技点契约", "契约", "获得【丹恒·饮月】和【花火】。打开20个晶矿后,获得【火花】和1个随机战技点羁绊角色;之后每打开10个晶矿,都可重复获得一次角色奖励。", source="6104"),
    _env("公司契约", "契约", "获得【翡翠】和【砂金】,累计获得40利息后,获得【托帕&账账】。", source="6103"),
    _env("持续伤害契约", "契约", "获得【桑博】和【卡芙卡】。敌人被消灭时,每陷入一个不同的持续伤害状态,获得1点计数。计数达到180时,获得【黑天鹅】。", source="6102"),
    _env("量子同频契约", "契约", "花火和缇宝升星时,随机获得【符玄】或【希儿】。", source="6101"),
    _env("欢愉契约", "契约", "获得【银狼LV.999】,她每次触发独立羁绊【头号玩家】选项时,获得【火花】或【开拓者·欢愉】。", source="7450"),
    _env("命运圣杯契约", "契约", "获得【远坂凛】、【吉尔伽美什】,完成两次圣杯试炼后,获得【Archer】。", "命运圣杯"),
    # —— 时代(锁定本局投资策略品质)——
    _env("黄金时代", "时代", "这局的投资策略均为黄金品质。", source="6077"),
    _env("白银时代", "时代", "这局的投资策略均为白银品质,因此敌人难度不会由于选择高品质投资策略而提高。", source="6083"),
    _env("彩虹时代", "时代", "这局的投资策略均为棱彩品质。", source="6080"),
    _env("头彩", "时代", "第一个投资策略是棱彩品质。", source="6099"),
    _env("尾彩", "时代", "第三个投资策略是棱彩品质。", source="6100"),
    _env("银·金·彩", "时代", "本局固定节点投资策略选择时,左/中/右分别为银/金/彩品质,且刷新次数+2。", source="7462"),
    # —— 经济/刷新/补给 ——
    _env("经济过热", "经济", "本局全部奖励节点替换为次元扑满主题,次元扑满会掉落更多战利品。", source="6082"),
    _env("经济严重过热", "经济", "本局全部奖励节点替换为超级次元扑满主题!超级次元扑满掉落超多战利品!但它们跑得超快!", source="6087"),
    _env("增发货币", "经济", "第一/二/三阶段开始时,获得一个6/8/10金币的晶矿。", source="6094"),
    _env("过剩经费", "经济", "补给阶段中,角色会携带两件装备。", source="6079"),
    _env("人身意外险", "经济", "所有首领节点前都加入一个额外补给阶段。", source="6081"),
    _env("长线利好", "经济", "花费金币进行30次刷新后,获得20金币,之后本局只需1金币就能刷新。", source="6086"),
    _env("二手市场", "经济", "商店刷新20次后,获得30金币和【员工投影仪】。", source="6092"),
    _env("蓝海", "经济", "进入到一个随机投资环境中,开局额外获得6金币。", source="6091"),
    _env("深井角斗场", "经济", "本局首次达成5连胜时,获得【财富宝钻】。", source="6093"),
    _env("火药味", "经济", "开局时获得2个简易武装箱。", source="6096"),
    _env("特权阶级", "经济", "第二位面开始时,获得1个特权武装箱。", source="6095"),
    _env("人才引进", "经济", "开局拥有1个随机4费角色。", source="6078"),
    _env("成功经验", "经济", "在你升到8级后,进入接下来3个节点时,获得12经验。", source="7566"),
    _env("红钻贵族", "经济", "开局时拥有【红钻】和一个【简易武装箱】。"),
    _env("蓝钻贵族", "经济", "开局时拥有【蓝钻】和一个【简易武装箱】。"),
    # —— 规则/玩法变体 ——
    _env("人才下沉", "规则", "商店中有概率出现2星角色。", source="6097"),
    _env("联席决策", "规则", "在2-6节点进行一次额外的投资策略三选一。", source="6098"),
    _env("轮岗", "规则", "备战阶段开始时,使一个随机费用的刷新概率翻倍,每个备战阶段重新随机。", source="6090"),
    _env("劳务派遣合同", "规则", "获得随机星徽,每次进入首领节点时,获得对应羁绊的随机角色。", source="6088"),
    _env("战争边疆", "规则", "第三位面的所有战斗节点都替换为遭遇节点。", source="6089"),
    _env("粗星佩佩", "规则", "获得一个穿戴三个随机星徽的佩佩,粗心的佩佩有时候会把星徽落在你的物品栏。", source="6084"),
    _env("三星佩佩", "规则", "获得一个穿戴三个随机星徽的佩佩。", source="6085"),
    _env("敌后破坏", "规则", "开局时,使一个已生成的敌人词缀失效。", source="7453"),
    _env("进化算法", "规则", "进入新节点时,所有场上角色获得4%前后台强度和2%伤害减免,可叠加。", source="7454"),
    _env("策略大师", "规则", "获取投资策略时,获得(2×已拥有投资策略数)的金币。在3-5节点额外获得一个投资策略。", source="7452"),
    # —— 专家/佩佩/角色强化 ——
    _env("人才储备", "专家", "开局补给替换为3个随机3费角色。3费角色升至2/3星时,获得11%/33%速度增幅、22%/66%伤害增幅。", source="7455"),
    _env("战力飙升", "专家", "获得1个随机2星2费角色,进入新节点时,这位角色永久获得随机属性加成。", source="7457"),
    _env("战力提升", "专家", "获得1个随机2星1费的输出角色,进入新节点时,这位角色永久获得随机属性加成。", source="7461"),
    _env("专家研讨会", "专家", "获得1个【专家邀请函】和1个【简易武装箱】。", source="7459"),
    _env("特邀专家:银狼", "专家", "当你首次获得【银狼LV.999】时,获得专家顾问【银狼】,并使其在本局游戏中加入商店。", source="7456"),
    _env("特邀专家:加拉赫", "专家", "获得专家顾问【加拉赫】,并使其加入商店。激活2/4/6/8击破羁绊时,获得1件【以太钻头】。", source="7458"),
    _env("特邀专家:停云", "专家", "获得专家顾问【停云】,并使其加入商店。停云施放终结技时,使目标队员获得等同于停云60%后台强度的前台强度(仅对最新目标生效)。", source="7460"),
    _env("命运礼物", "专家", "立刻获得一个【惊喜盒】,倒计时12个节点后礼盒打开,战斗完胜后,倒计时额外减少1点。", source="7463"),
    _env("英雄登场", "专家", "获得1个2星5费角色,19个节点后才能将其上场。战斗完胜后,上场节点额外提前1点。", source="7464"),
]}

# ===== INVESTMENT_STRATEGIES 注册表(T0 投资策略,event_whitelist 规范名来源;全量 216 在 doc)=====
# 效果原文对齐米游社 315 全量 doc(ADR-0131 修正:旧 8 条描述错 —— 高效决策非"减半"而是 45 秒免费刷爆发;
# 采购专员非"返现"而是变同费 5 张卡;价值投资·彩非"生息"而是送角色滚雪球;基本保障非"经济"而是战力)。
INVESTMENT_STRATEGIES: dict[str, InvestmentStrategy] = {s.name: s for s in [
    _strat("高效决策", "棱彩", "获得9999次免费刷新,但只持续45秒。结束时移除所有免费刷新。",
           economy=EconomyEffect(free_refresh_burst=9999)),
    _strat("价值投资·彩", "棱彩", "获得1个随机2星2费角色。每次进入新节点获得1星该角色,补给后额外2个,持续至本局结束。"),
    _strat("采购专员·彩", "棱彩", "每5次刷新,商店刷出5张费用相同的角色(费用=备战席最左侧角色费用)。",
           economy=EconomyEffect(refresh_surprise_every=5)),
    _strat("本金充裕", "棱彩", "获得26金币。每次进入新节点,若拥有超过50金币,每额外10金币获1次免费刷新(最多3次)。",
           economy=EconomyEffect(instant_gold=26)),
    _strat("开源节流", "棱彩", "获得10金币,利息上限提升至9。进入新节点若上节点未花金币,则获最大利息金币。",
           economy=EconomyEffect(instant_gold=10, interest_cap_override=9)),
    _strat("利息上调", "棱彩", "获得25金币。最大利息提升至10金币。",
           economy=EconomyEffect(instant_gold=25, interest_cap_override=10)),
    _strat("买断制", "棱彩", "你不再获得利息。即刻获得15金币。每次进入新节点获得4经验。",
           economy=EconomyEffect(instant_gold=15, interest_cap_override=0, xp_per_node=4)),
    _strat("淘金客", "棱彩", "你每次消耗金币刷新商店,获得2经验值。",
           economy=EconomyEffect(xp_per_refresh=2)),
    _strat("伟大征服", "棱彩", "连胜奖励变为3倍,敌人难度+N(N=当前连胜数)。获12经验。",
           economy=EconomyEffect(win_reward_mult=3.0)),
    _strat("商业间谍", "棱彩", "购买经验花费减1,升级时刷新商店,并偷取其中最贵的3个角色。",
           economy=EconomyEffect(xp_buy_cost_discount=1)),
    _strat("返利+", "金", "每购买3个5费角色获得3金币。立刻获6金币。",
           economy=EconomyEffect(instant_gold=6, gold_per_three_5cost=3)),
    _strat("采购专员·金", "金", "每7次刷新,商店刷出5张费用相同的角色(费用=备战席最左侧角色费用)。",
           economy=EconomyEffect(refresh_surprise_every=7)),
    _strat("定期福利", "金", "立刻获得4金币,且每次进入新节点获2金币。",
           economy=EconomyEffect(instant_gold=4, gold_per_node=2)),
    _strat("加油站", "金", "现在及每次进入新节点获1次免费刷新,立刻获8金币。",
           economy=EconomyEffect(instant_gold=8, free_refresh_per_node=1)),
    _strat("定点爆破", "金", "爆发伤害"),
    _strat("数值碾压", "金", "强度增益"),
    _strat("攻防一体", "金", "攻防增益"),
    _strat("羁绊的力量", "金", "羁绊增益"),
    _strat("基本保障", "金", "至少携带1件装备的角色获得20%生命增幅和16%伤害增幅。"),
    # 注:砂里淘金(电表倒转核心)是已知场景但难操作+耗时,非推荐 bot 玩法,不入白名单(economy_research §3)
]}


# ===== 派生:ENV_FACTION_MAP(投资环境 → 加成阵营;从 INVESTMENT_ENVS 派生,单一真相源)=====
def env_faction(env_name: str) -> str:
    """投资环境加成的阵营(概念股/邀请的 faction;无则 "")。"""
    e = INVESTMENT_ENVS.get(env_name)
    return e.faction if e is not None else ""


def envs_boosting_faction(faction: str) -> list[str]:
    """加成某阵营的全部投资环境名(概念股 + 邀请)。"""
    return [name for name, e in INVESTMENT_ENVS.items() if e.faction == faction]


def get_env(name: str) -> InvestmentEnv | None:
    """按规范名取 InvestmentEnv;无则 None。"""
    return INVESTMENT_ENVS.get(name)


def is_known_env(name: str) -> bool:
    """投资环境名是否在注册表内(识别完整性信号;OCR 命中注册表外的名字 → 数据缺口,应 log warn)。

    用于 handle_invest_env 把「未建模环境」从静默中性 fallback 变成可见信号(防假绿,
    见 od-dev-gameplay-automation 完成判据反馈)。注册表外的名字可能是:① 赛季新增未收录;
    ② OCR 误识;③ 锁定未命名环境(数据银行 ??? 无法收录)。
    """
    return name in INVESTMENT_ENVS


def economy_effect_of(name: str) -> EconomyEffect:
    """单策略经济效果(无/未注册 → 全 0 EconomyEffect;ADR-0131)。"""
    s = INVESTMENT_STRATEGIES.get(name)
    return s.economy if (s is not None and s.economy is not None) else EconomyEffect()


def aggregate_economy(strategy_names: list[str]) -> EconomyEffect:
    """聚合多策略经济效果(ADR-0131):加法字段求和;interest_cap_override 取**最大**(更宽上限赢,
    买断制 0 单独持有时生效 —— 与其它利息策略并持时游戏取宽值,保守建模取 max 非 min);
    win_reward_mult 取**最大**(不叠乘)。"""
    eff = EconomyEffect()
    caps: list[int] = []
    mults: list[float] = []
    for n in strategy_names:
        e = economy_effect_of(n)
        eff = EconomyEffect(
            instant_gold=eff.instant_gold + e.instant_gold,
            gold_per_node=eff.gold_per_node + e.gold_per_node,
            free_refresh_per_node=eff.free_refresh_per_node + e.free_refresh_per_node,
            free_refresh_burst=eff.free_refresh_burst + e.free_refresh_burst,
            refresh_surprise_every=(min(eff.refresh_surprise_every, e.refresh_surprise_every)
                                    if (eff.refresh_surprise_every and e.refresh_surprise_every)
                                    else (eff.refresh_surprise_every or e.refresh_surprise_every)),
            gold_per_three_5cost=eff.gold_per_three_5cost + e.gold_per_three_5cost,
            interest_cap_override=eff.interest_cap_override,
            xp_per_refresh=eff.xp_per_refresh + e.xp_per_refresh,
            xp_per_node=eff.xp_per_node + e.xp_per_node,
            xp_buy_cost_discount=eff.xp_buy_cost_discount + e.xp_buy_cost_discount,
            win_reward_mult=eff.win_reward_mult,
        )
        if e.interest_cap_override is not None:
            caps.append(e.interest_cap_override)
        if e.win_reward_mult != 1.0:
            mults.append(e.win_reward_mult)
    if caps:
        eff = replace(eff, interest_cap_override=max(caps))
    if mults:
        eff = replace(eff, win_reward_mult=max(mults))
    return eff


def get_strategy(name: str) -> InvestmentStrategy | None:
    """按规范名取 InvestmentStrategy;无则 None(全量未收的查 investment_strategies.md)。"""
    return INVESTMENT_STRATEGIES.get(name)
