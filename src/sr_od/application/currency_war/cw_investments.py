"""货币战争 投资策略 + 投资环境领域模型(meta 层,V4.4)。

**两层架构(ADR-0150)**:
- **base 事实层** = ``cw_invest_data.py``(``tools/cw/gen_plaza_invest.py`` 从米游社攻略广场
  官方 API 生成,勿手编):名字/品质/效果全文,数字 id 稳定主键,投资策略 334 + 投资环境 83
  官方全量(游戏内数据银行同口径,米游社百科 doc 的 19 条版本漂移缺口就此补齐)。
- **建模增量层** = 本文件手维护(API 给不了的人工建模):
  - ``STRATEGY_ECONOMY``(ADR-0131 可数值化经济效果);
  - ``ENV_CATEGORY``/``ENV_FACTION``(环境 7 类分类 + 阵营绑定,ENV_FACTION_MAP 派生源);
  - ``_MANUAL_EXTRAS``(plaza 不收的补遗条目);
  - ``PICK_VALUE``/``ENV_PICK_VALUE``/``SURVIVAL_PICKS``(ADR-0143/0144 选卡评估分)。
- **合并层**:base × overlay → 注册表,构建时做孤儿校验(overlay 引用了 base 没有的键 →
  import 即炸,防版本更新后静默失联)。

**版本更新工作流**:重跑 ``uv run python tools/cw/gen_plaza_invest.py`` → 看 diff 报告
(新增/移除/改名/品质变)→ 修 overlay 孤儿键 → 完成。

**用途**:
- ``InvestmentEnv``(概念股/邀请/契约/时代/经济/规则/专家):**带 faction 字段** —— 概念股/
  邀请/命运圣杯契约对应哪个阵营是派生 ENV_FACTION_MAP 的单一真相源。
- ``InvestmentStrategy``(局内 3 选 1):pick_value 评估与用户转向轴(config strategy/env priority/forbid)的规范名来源。
- 键约定:canon 归一名(半角冒号/逗号、`·`、拉丁数字),与 OCR 精确匹配层一致;
  OCR 形变(全角标点/剎刹)走 pick_value_of 的 LCS 兜底。

**为什么建模**(用户 2026-08-03):核心实体建正规 model 类 + 注册表(可查询/校验/派生),非散 dict。

⚠️ env_fit 策略影响目前只用「阵营亲和」一维(概念股/邀请/命运圣杯),其余类别(契约/时代/
经济/规则/专家)效果异质,待分类建模(阶段 3a)。版本依赖:赛季扩充会新增/调整。
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from sr_od.application.currency_war.cw_invest_data import (
    PLAZA_AUGMENTS,
    PLAZA_PORTALS,
)


@dataclass(frozen=True)
class InvestmentEnv:
    """投资环境(开局/固定节点整局增益)。"""
    name: str           # 规范名(如"昼之半神概念股")
    category: str       # "概念股"/"邀请"/"契约"/"时代"/"经济"/"规则"/"专家"
    effect: str         # 效果原文(官方 API 全文)
    faction: str = ""   # 对应阵营(概念股/邀请 boosts 的羁绊;ENV_FACTION_MAP 派生用;无则 "")
    source: str = ""    # 溯源(plaza:<id> 或 content_id)
    pick_value: int = 0  # 选卡价值基准分 0-100(ADR-0144;0=未评估)


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
    - gold_per_boss_node: 进首领节点给金(特战资金系;boss 占节点 ~1/9,消费侧折算)
    - gold_next_nodes_amount/count: 「现在及接下来 count 次进节点每次 amount 金」(长期主义系;分期金)
    - gold_per_level_up: 每次升级给金(节节高升;P1 约 7 次升级,P2 再 2 次)
    - gold_per_20hp_lost: 每损 20HP 给金(保险;**故意不进经济分** —— 损血换钱是反向激励,仅建档)
    (ADR-0142:9 条曾错装一次性 instant_gold 的重复性效果,按效果原文归位)
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
    gold_per_boss_node: int = 0
    gold_next_nodes_amount: int = 0
    gold_next_nodes_count: int = 0
    gold_per_level_up: int = 0
    gold_per_20hp_lost: int = 0
    # —— v2 扩展(ADR-0205 全量调研;仅 API 文本明说的数值)——
    difficulty_delta: int = 0             # 静态难度 Δ(简单模式 −3 等;36 号账本消费)
    difficulty_per_streak: int = 0        # 动态难度(伟大征服:难度+连胜数)
    difficulty_node_types: tuple[str, ...] = ()   # Δ 限定节点型(难度修改器:遭遇+首领)
    future_quality_upgrade: str = ''      # 远见:后续策略节点品质改写('prism';期权侧消费)
    difficulty_inflation_exempt: bool = False    # 远见:不增加敌人难度
    gold_at_level: int = 0                # 成长基金:到达该级给金(级数配对字段)
    gold_at_level_target: int = 0         # 触发等级(9)
    xp_click_discount_from_level: int = 0  # 成长的快乐:该级起单击减金(配对字段 below)
    xp_click_discount_from_level_at: int = 0   # 触发等级(8)
    gold_at_node: int = 0                 # 时点大额(超发货币 +70;负债部分由消费端按持有金算)
    gold_at_node_offset: int = 0          # 何时(t+5)
    interest_flat_per_node: int = 0       # 狸财经狸:每节点固定息(与 interest_cap 无关)
    hp_gold_swap: bool = False            # 不等价交换:交换 hp/gold(33 号 λ_hp 消费)
    gold_per_hp_lost_now: bool = False    # 星际和平保险:选卡时=已损血数金
    xp_instant: int = 0                   # 即时经验(伟大征服 12/气氛组+ 8/成长的快乐 4)
    # —— 合成/出售触发族(ADR-0211 裁定;均为「正常成型路上
    #     白得」的被动经济,选卡正常评估,不围绕改打法)——
    gold_per_2star2cost_merge: int = 0    # 砂里淘金:合 2星2费 得砂金(可卖 ≈ 现金)
    gold_per_3star_merge: int = 0         # 星星相印:每合 3 星 +金
    refresh_per_compose: int = 0          # 武力刷新:合成装备时得免费刷
    sell_price_mult: float = 1.0          # 大裁员/降本增效:卖价 ×2(配合全场出售动作)


@dataclass(frozen=True)
class InvestmentStrategy:
    """投资策略(局内 3 选 1,可刷新)。"""
    name: str           # 规范名(canon 归一)
    rarity: str         # "棱彩"/"金"/"银"(官方 quality)
    effect: str         # 官方效果全文(plaza API)
    source: str = ""    # 溯源(plaza:<id> / content_id / codex_20260815)
    economy: EconomyEffect | None = None   # 可数值化经济效果(ADR-0131);战力类 None
    pick_value: int = 0    # 选卡价值基准分 0-100(ADR-0143;0=未评估回落品质先验)


def _strat(name: str, rarity: str, effect: str, source: str = "",
           economy: EconomyEffect | None = None) -> InvestmentStrategy:
    return InvestmentStrategy(name=name, rarity=rarity, effect=effect, source=source, economy=economy)


# ===== curated overlay:可数值化经济效果(ADR-0131;手维护,键=注册表规范名)=====
# base(API)给不了的效果结构化;战力类不在此(走战力评估)。孤儿键 → 构建层报错。
STRATEGY_ECONOMY: dict[str, EconomyEffect] = {
    '高效决策': EconomyEffect(free_refresh_burst=9999),
    '采购专员·彩': EconomyEffect(refresh_surprise_every=5),
    '本金充裕': EconomyEffect(instant_gold=26),
    '开源节流': EconomyEffect(instant_gold=10, interest_cap_override=9),
    '利息上调': EconomyEffect(instant_gold=25, interest_cap_override=10),
    '买断制': EconomyEffect(instant_gold=15, interest_cap_override=0, xp_per_node=4),
    '淘金客': EconomyEffect(xp_per_refresh=2),
    '伟大征服': EconomyEffect(win_reward_mult=3.0, difficulty_per_streak=1, xp_instant=12),
    # ↑ 纠错(ADR-0205):注册表曾只建 ×3,漏「敌人难度+N(N=连胜)」与 +12XP(API 原文)
    '商业间谍': EconomyEffect(xp_buy_cost_discount=1),
    '返利+': EconomyEffect(instant_gold=6, gold_per_three_5cost=3),
    '采购专员·金': EconomyEffect(refresh_surprise_every=7),
    '定期福利': EconomyEffect(instant_gold=4, gold_per_node=2),
    '加油站': EconomyEffect(instant_gold=8, free_refresh_per_node=1),
    '乱成一锅粥+': EconomyEffect(instant_gold=14, free_refresh_burst=7),
    '乱成一锅粥': EconomyEffect(instant_gold=10, free_refresh_burst=5),
    '着眼当下': EconomyEffect(instant_gold=5),
    '搜打撤': EconomyEffect(free_refresh_per_node=1),
    '远见': EconomyEffect(instant_gold=15, future_quality_upgrade='prism',
                          difficulty_inflation_exempt=True),
    # ↑ 纠错(ADR-0205):曾只建 +15 金,漏「后续策略节点→随机棱彩(不可刷)」
    # +「不增加敌人难度」两大效果(API 原文;期权/难度侧由 33/36 号消费)
    '贸易专家:停云': EconomyEffect(instant_gold=10),
    '佩佩驾到': EconomyEffect(instant_gold=8),
    '控制规模': EconomyEffect(instant_gold=40),
    '藏一手': EconomyEffect(instant_gold=80),
    '及时雨': EconomyEffect(free_refresh_burst=4),
    '决议:娱乐星球': EconomyEffect(instant_gold=50),
    '公司严选': EconomyEffect(instant_gold=3),
    '节节高升': EconomyEffect(gold_per_level_up=1),
    '本金充裕+': EconomyEffect(instant_gold=45),
    '黄金垃圾': EconomyEffect(instant_gold=15),
    '退化': EconomyEffect(instant_gold=8, difficulty_delta=-5),
    '停云顾问': EconomyEffect(instant_gold=4),
    '加拉赫顾问': EconomyEffect(instant_gold=4),
    '摸个鱼吧II': EconomyEffect(instant_gold=6),
    '摸个鱼吧I': EconomyEffect(instant_gold=6),
    '按劳分配': EconomyEffect(gold_per_node=1),
    '专家招募+': EconomyEffect(instant_gold=12),
    '专家招募': EconomyEffect(instant_gold=4),
    '大扩招': EconomyEffect(instant_gold=16),
    '五百强': EconomyEffect(instant_gold=30),
    '成本控制': EconomyEffect(instant_gold=8),
    '剩余价值': EconomyEffect(gold_per_node=1),
    '四费晋升': EconomyEffect(instant_gold=12),
    '小复制+': EconomyEffect(instant_gold=13),
    '小复制': EconomyEffect(instant_gold=7),
    '长期主义+': EconomyEffect(gold_next_nodes_amount=9, gold_next_nodes_count=3),
    '长期主义': EconomyEffect(gold_next_nodes_amount=7, gold_next_nodes_count=3),
    '大裁员': EconomyEffect(free_refresh_burst=5, sell_price_mult=2.0),
    # ↑ 刷(旧)+ 卖价×2(合成/出售族轮并入)
    '嘴硬': EconomyEffect(instant_gold=6),
    '秘密典籍+': EconomyEffect(instant_gold=12),
    '秘密典籍': EconomyEffect(instant_gold=8),
    '经验就是财富': EconomyEffect(instant_gold=4),
    '二极管': EconomyEffect(instant_gold=6),
    '免费升舱': EconomyEffect(instant_gold=4),
    '无害垃圾': EconomyEffect(instant_gold=8),
    '胜利,还是胜利': EconomyEffect(instant_gold=4),
    '打捞人才库+': EconomyEffect(instant_gold=4),
    '尾款交付': EconomyEffect(instant_gold=30),
    '免费午餐': EconomyEffect(free_refresh_burst=11),
    '特战资金+': EconomyEffect(gold_per_boss_node=11),
    '特战资金': EconomyEffect(gold_per_boss_node=7),
    '返利': EconomyEffect(gold_per_three_5cost=3),
    '军火贸易': EconomyEffect(instant_gold=4),
    '军火贸易+': EconomyEffect(instant_gold=8),
    '以战养战': EconomyEffect(instant_gold=6),
    '躺平': EconomyEffect(instant_gold=20),
    '公司人才流动': EconomyEffect(instant_gold=2),
    '武装支援+': EconomyEffect(instant_gold=6),
    '合并同类项': EconomyEffect(instant_gold=1, free_refresh_burst=4),
    '无伤通关': EconomyEffect(instant_gold=1),
    '招聘资金': EconomyEffect(instant_gold=4),
    '招聘资金+': EconomyEffect(instant_gold=5),
    '溜佩佩': EconomyEffect(instant_gold=9),
    '溜佩佩+': EconomyEffect(instant_gold=15),
    '保险': EconomyEffect(gold_per_20hp_lost=5),
    # —— v2 新建(ADR-0205 调研落地;API 文本明说的数值)——
    # 批 1:等级触发
    '成长基金': EconomyEffect(gold_at_level=40, gold_at_level_target=9),
    '成长的快乐': EconomyEffect(xp_instant=4,
                                xp_click_discount_from_level=1, xp_click_discount_from_level_at=8),
    # 批 2:时点日程
    '超发货币': EconomyEffect(gold_at_node=70, gold_at_node_offset=5),
    # ↑ 负债部分(失去现有全部金)由消费端按持有金处理,数值侧只记回流 +70
    '固定理财': EconomyEffect(xp_per_node=0, free_refresh_burst=2),   # 位面开始部分(见下)
    '固定理财+': EconomyEffect(free_refresh_burst=3),
    # ↑ 「现在+每位置面开始 4/6XP+2/3 刷」——v0 只建即时刷;位面日程挂台账批次
    '经验到账': EconomyEffect(xp_instant=10),
    '孪生素数': EconomyEffect(xp_instant=0),   # 首购计数器(2/3/5/7/11)——行为条件流,消费端计数
    # 批 3:动态/血金互兑
    '狸财经狸': EconomyEffect(interest_flat_per_node=2),
    # ↑ API 全文:30 本金进不了字段(非给玩家);息+2/节点;金<20 取 10(流动性保险,
    #   行为条件流);P3 首领取全部存款(存款累计值消费端推)。数值侧先建固定息。
    '不等价交换': EconomyEffect(hp_gold_swap=True),
    '星际和平保险': EconomyEffect(gold_per_hp_lost_now=True),
    # C 类:难度交互(显数值;36 号账本消费)
    '简单模式': EconomyEffect(difficulty_delta=-3),
    '难度修改器': EconomyEffect(difficulty_delta=-4, difficulty_node_types=('遭遇', '首领')),
    # 合成/出售触发族(ADR-0211:选卡照常评估)
    '砂里淘金': EconomyEffect(gold_per_2star2cost_merge=2),
    # ↑ 合 2星2费 白得砂金(2费可卖 ≈2 金/张;阵容用得上则价值更高,经济侧按下界)
    '星星相印': EconomyEffect(gold_per_3star_merge=5),
    '武力刷新': EconomyEffect(refresh_per_compose=2),
    '降本增效': EconomyEffect(sell_price_mult=2.0),
}


# ===== curated overlay:环境分类 + 阵营绑定(手维护)=====
ENV_CATEGORY: dict[str, str] = {
    '追击概念股': '概念股', '击破概念股': '概念股', '群攻概念股': '概念股',
    '能量概念股': '概念股', '燃血概念股': '概念股', '减益概念股': '概念股',
    '战技点概念股': '概念股', '仙舟概念股': '概念股', '贝洛伯格概念股': '概念股',
    '狼狩概念股': '概念股', '星间旅人概念股': '概念股', '银河学者概念股': '概念股',
    '列车同行概念股': '概念股', '昼之半神概念股': '概念股', '夜之半神概念股': '概念股',
    '仙舟邀请': '邀请', '贝洛伯格邀请': '邀请', '狼狩邀请': '邀请', '盛会之星邀请': '邀请',
    '星间旅人邀请': '邀请', '银河学者邀请': '邀请', '列车同行邀请': '邀请',
    '昼之半神邀请': '邀请', '夜之半神邀请': '邀请', '追击邀请': '邀请', '击破邀请': '邀请',
    '群攻邀请': '邀请', '能量邀请': '邀请', '燃血邀请': '邀请', '减益邀请': '邀请',
    '持续伤害邀请': '邀请', '量子同频邀请': '邀请', '战技点邀请': '邀请', '欢愉邀请': '邀请',
    '命运圣杯邀请': '邀请',
    '星核猎手契约': '契约', '战技点契约': '契约', '公司契约': '契约', '持续伤害契约': '契约',
    '量子同频契约': '契约', '欢愉契约': '契约', '命运圣杯契约': '契约',
    '黄金时代': '时代', '白银时代': '时代', '彩虹时代': '时代',
    '头彩': '时代', '尾彩': '时代', '银·金·彩': '时代',
    '经济过热': '经济', '经济严重过热': '经济', '增发货币': '经济', '过剩经费': '经济',
    '人身意外险': '经济', '长线利好': '经济', '二手市场': '经济', '蓝海': '经济',
    '深井角斗场': '经济', '火药味': '经济', '特权阶级': '经济', '人才引进': '经济',
    '成功经验': '经济', '红钻贵族': '经济', '蓝钻贵族': '经济',
    '人才下沉': '规则', '联席决策': '规则', '轮岗': '规则', '劳务派遣合同': '规则',
    '战争边疆': '规则', '粗星佩佩': '规则', '三星佩佩': '规则', '敌后破坏': '规则',
    '进化算法': '规则', '策略大师': '规则',
    '人才储备': '专家', '战力飙升': '专家', '战力提升': '专家', '专家研讨会': '专家',
    '特邀专家:银狼': '专家', '特邀专家:加拉赫': '专家', '特邀专家:停云': '专家',
    '特邀专家:桑博': '专家', '命运礼物': '专家', '英雄登场': '专家',
}

ENV_FACTION: dict[str, str] = {
    '追击概念股': '追击', '击破概念股': '击破', '群攻概念股': '群攻', '能量概念股': '能量',
    '燃血概念股': '燃血', '减益概念股': '减益', '战技点概念股': '战技点', '仙舟概念股': '仙舟',
    '贝洛伯格概念股': '贝洛伯格', '狼狩概念股': '狼狩', '星间旅人概念股': '星间旅人',
    '银河学者概念股': '银河学者', '列车同行概念股': '列车同行', '昼之半神概念股': '昼之半神',
    '夜之半神概念股': '夜之半神',
    '仙舟邀请': '仙舟', '贝洛伯格邀请': '贝洛伯格', '狼狩邀请': '狼狩', '盛会之星邀请': '盛会之星',
    '星间旅人邀请': '星间旅人', '银河学者邀请': '银河学者', '列车同行邀请': '列车同行',
    '昼之半神邀请': '昼之半神', '夜之半神邀请': '夜之半神', '追击邀请': '追击', '击破邀请': '击破',
    '群攻邀请': '群攻', '能量邀请': '能量', '燃血邀请': '燃血', '减益邀请': '减益',
    '持续伤害邀请': '持续伤害', '量子同频邀请': '量子同频', '战技点邀请': '战技点',
    '欢愉邀请': '欢愉', '命运圣杯邀请': '命运圣杯',
    '命运圣杯契约': '命运圣杯',
    # —— 契约类阵营绑定(ADR-0151 补:效果=获赠该阵营角色,原 overlay 漏)——
    '量子同频契约': '量子同频',   # 花火/缇宝升星→符玄/希儿
    '公司契约': '公司',           # 翡翠/砂金/托帕
    '持续伤害契约': '持续伤害',   # 椒丘/卡芙卡/黑天鹅
    '战技点契约': '战技点',       # 丹恒·饮月/花火/火花
    '星核猎手契约': '星核猎手',   # 卡芙卡/刃/银狼/流萤
    '欢愉契约': '欢愉',           # 银狼LV.999/火花/开拓者·欢愉
    '特邀专家:加拉赫': '击破',   # 加拉赫=击破角色(plaza traits 盛会之星/击破/治疗)+击破档位给钻头(用户确认)
}


# ===== 补遗:plaza 不收的条目(手维护)=====
_MANUAL_EXTRAS: list[InvestmentStrategy] = [
    # 与「追击星徽套组」(id 352201 系)同效果,plaza 只收一张;米游社图鉴收两张(content 6302)
    _strat("追击星徽套组(二)", "棱彩", "获得1个【追击星徽】,和1个【飞霄】,以及1个【永动机】。(与追击星徽套组同效果)", "6302"),
]


# ===== 合并层:base(plaza API)× overlay → 注册表(ADR-0150)=====
def _build_strategies() -> dict[str, InvestmentStrategy]:
    """base 334 条 + 补遗 → 注册表;economy 从 overlay 挂;孤儿键报错。"""
    out: dict[str, InvestmentStrategy] = {}
    for a in PLAZA_AUGMENTS:
        out[a.name] = InvestmentStrategy(
            name=a.name, rarity=a.rarity, effect=a.effect,
            source=f"plaza:{a.id}",
            economy=STRATEGY_ECONOMY.get(a.name),
        )
    for s in _MANUAL_EXTRAS:
        out.setdefault(s.name, s)
    orphans = set(STRATEGY_ECONOMY) - set(out)
    if orphans:
        raise ValueError(f"STRATEGY_ECONOMY 孤儿键(base 无此卡,版本更新改名/移除?):{sorted(orphans)}")
    return out


def _build_envs() -> dict[str, InvestmentEnv]:
    """base 83 条 → 注册表;category/faction 从 overlay 挂;孤儿键报错。"""
    out: dict[str, InvestmentEnv] = {}
    for p in PLAZA_PORTALS:
        out[p.name] = InvestmentEnv(
            name=p.name,
            category=ENV_CATEGORY.get(p.name, "未分类"),
            effect=p.effect,
            faction=ENV_FACTION.get(p.name, ""),
            source=f"plaza:{p.id}",
        )
    orphans = (set(ENV_CATEGORY) | set(ENV_FACTION)) - set(out)
    if orphans:
        raise ValueError(f"ENV_CATEGORY/ENV_FACTION 孤儿键(base 无此环境?):{sorted(orphans)}")
    return out


INVESTMENT_STRATEGIES: dict[str, InvestmentStrategy] = _build_strategies()
INVESTMENT_ENVS: dict[str, InvestmentEnv] = _build_envs()


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
            gold_per_boss_node=eff.gold_per_boss_node + e.gold_per_boss_node,
            gold_next_nodes_amount=eff.gold_next_nodes_amount + e.gold_next_nodes_amount,
            gold_next_nodes_count=max(eff.gold_next_nodes_count, e.gold_next_nodes_count),
            gold_per_level_up=eff.gold_per_level_up + e.gold_per_level_up,
            gold_per_20hp_lost=eff.gold_per_20hp_lost + e.gold_per_20hp_lost,
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


# ===== curated overlay:策略语义绑定(ADR-0151,逐卡按效果含义手建模;↺ ADR-0134 文本扫描派生)=====
# 判据:**效果引用 comp 专属机制/召唤物/星徽/赠 key 角色 → 绑定;泛用数值(全队强度/给金/装备)→ 不绑**。
# 文本扫描的两类噪声就此清除:战术义眼(泛用回能,误绑"能量")/生命之花祝福(泛用治疗强度,误绑"治疗")。
# 消费:decide_event comp 匹配分 + cw_comps.held_strategy_fit(持卡影响 pivot)。
# 维护:版本更新重跑 gen_plaza_invest.py → diff 报告对「效果变」条目提示 → 回本表重审对应键。
STRATEGY_BINDINGS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    # —— 星徽套组(棱彩):阵营星徽 + 阵营 key 角色 ——
    '列车同行星徽套组': (frozenset({'列车同行'}), frozenset({'丹恒·饮月'})),
    '银河学者星徽套组': (frozenset({'银河学者'}), frozenset({'艾丝妲'})),
    '贝洛伯格星徽套组': (frozenset({'贝洛伯格'}), frozenset({'希儿'})),
    '星间旅人星徽套组': (frozenset({'星间旅人'}), frozenset({'银枝'})),
    '仙舟星徽套组': (frozenset({'仙舟'}), frozenset({'藿藿'})),
    '狼狩星徽套组': (frozenset({'狼狩'}), frozenset({'椒丘'})),
    '盛会之星星徽套组': (frozenset({'盛会之星'}), frozenset({'花火'})),
    '昼之半神星徽套组': (frozenset({'昼之半神'}), frozenset({'风堇'})),
    '夜之半神星徽套组': (frozenset({'夜之半神'}), frozenset({'万敌'})),
    '追击星徽套组': (frozenset({'追击'}), frozenset({'飞霄'})),
    '追击星徽套组(二)': (frozenset({'追击'}), frozenset({'飞霄'})),
    '击破星徽套组': (frozenset({'击破'}), frozenset({'阮·梅'})),
    '群攻星徽套组': (frozenset({'群攻'}), frozenset({'翡翠'})),
    '能量星徽套组': (frozenset({'能量'}), frozenset({'星期日'})),
    '治疗星徽套组': (frozenset({'治疗'}), frozenset({'风堇'})),
    '燃血星徽套组': (frozenset({'燃血'}), frozenset({'万敌'})),
    '减益星徽套组': (frozenset({'减益'}), frozenset({'黄泉'})),
    '持续伤害星徽套组': (frozenset({'持续伤害'}), frozenset({'卡芙卡'})),
    '量子同频星徽套组': (frozenset({'量子同频'}), frozenset({'希儿'})),
    '护盾星徽套组': (frozenset({'护盾'}), frozenset({'砂金'})),
    '战技点星徽套组': (frozenset({'战技点'}), frozenset({'丹恒·饮月'})),
    # —— 星徽单件(金):阵营星徽 + 阵营 key 角色 ——
    '列车同行星徽': (frozenset({'列车同行'}), frozenset({'丹恒·饮月'})),
    '银河学者星徽': (frozenset({'银河学者'}), frozenset({'艾丝妲'})),
    '贝洛伯格星徽': (frozenset({'贝洛伯格'}), frozenset({'希儿'})),
    '星间旅人星徽': (frozenset({'星间旅人'}), frozenset({'银枝'})),
    '仙舟星徽': (frozenset({'仙舟'}), frozenset({'藿藿'})),
    '狼狩星徽': (frozenset({'狼狩'}), frozenset({'椒丘'})),
    '盛会之星星徽': (frozenset({'盛会之星'}), frozenset({'花火'})),
    '昼之半神星徽': (frozenset({'昼之半神'}), frozenset({'风堇'})),
    '夜之半神星徽': (frozenset({'夜之半神'}), frozenset({'万敌'})),
    '命运圣杯星徽': (frozenset({'命运圣杯'}), frozenset({'远坂凛'})),
    '追击星徽': (frozenset({'追击'}), frozenset({'飞霄'})),
    '击破星徽': (frozenset({'击破'}), frozenset({'阮·梅'})),
    '群攻星徽': (frozenset({'群攻'}), frozenset({'翡翠'})),
    '能量星徽': (frozenset({'能量'}), frozenset({'星期日'})),
    '治疗星徽': (frozenset({'治疗'}), frozenset({'风堇'})),
    '燃血星徽': (frozenset({'燃血'}), frozenset({'万敌'})),
    '减益星徽': (frozenset({'减益'}), frozenset({'黄泉'})),
    '持续伤害星徽': (frozenset({'持续伤害'}), frozenset({'卡芙卡'})),
    '量子同频星徽': (frozenset({'量子同频'}), frozenset({'希儿'})),
    '护盾星徽': (frozenset({'护盾'}), frozenset({'砂金'})),
    '战技点星徽': (frozenset({'战技点'}), frozenset({'丹恒·饮月'})),
    '欢愉星徽': (frozenset({'欢愉'}), frozenset({'绯英'})),
    # —— comp 专属机制强化(金):效果点名声援某阵营机制 ——
    '双人舞': (frozenset({'星核猎手'}), frozenset({'千冶·刃', '卡芙卡'})),
    '读博深造': (frozenset({'银河学者'}), frozenset({'艾丝妲', '阮·梅'})),
    '钢铁美学': (frozenset({'贝洛伯格'}), frozenset({'希儿'})),
    '人在旅途': (frozenset({'星间旅人'}), frozenset({'绯英', '银枝'})),
    '装备党': (frozenset({'狼狩'}), frozenset({'椒丘', '飞霄'})),
    '梦境大舞台': (frozenset({'盛会之星'}), frozenset({'花火'})),
    '赞美太阳': (frozenset({'昼之半神'}), frozenset({'那刻夏'})),
    '月光宝盒': (frozenset({'夜之半神'}), frozenset({'赛飞儿', '万敌'})),
    '借力打力': (frozenset({'群攻'}), frozenset({'黑塔', '缇宝'})),
    '超充站': (frozenset({'能量'}), frozenset({'阿格莱雅', '藿藿'})),
    '燃起来了': (frozenset({'燃血'}), frozenset({'万敌', '千冶·刃'})),
    '量子力学': (frozenset({'量子同频'}), frozenset({'希儿'})),
    '如有神助': (frozenset({'仙舟'}), frozenset()),       # 神君伤害(仙舟召唤)
    '迷之旅人': (frozenset({'巡海游侠'}), frozenset({'黄泉', '波提欧'})),
    '阿哈大悦': (frozenset({'欢愉'}), frozenset()),       # 欢愉羁绊激活时强化阿哈
    '不虚此行': (frozenset({'列车同行'}), frozenset()),   # 星穹列车/光轨
    '离火燎原': (frozenset({'减益'}), frozenset()),       # 离火真伤
    '按劳分配': (frozenset({'战技点'}), frozenset()),     # 金币上限随战技点羁绊档位(用户确认)
    '步狸村之谜': (frozenset({'狼狩'}), frozenset()),     # 狸狸穿戴狼狩星徽(用户确认,同 星徽→绑定 判据)
    # —— comp 专属机制强化(棱彩)——
    '盗用身份': (frozenset({'列车同行'}), frozenset({'火花'})),  # 所赠列车同行星徽(用户确认;{NICKNAME}=开拓者卡已归一)
    '飞光·传剑': (frozenset({'仙舟'}), frozenset({'彦卿', '景元'})),  # 神君引用+双仙舟角色(用户确认)
    '都是这家伙的错！': (frozenset({'命运圣杯'}), frozenset()),
    # —— 赠 key 角色 / 双子互升 / 专家顾问(角色绑定,无阵营)——
    '飞光·映月': (frozenset(), frozenset({'镜流', '景元'})),
    '本姑娘就是罗刹': (frozenset(), frozenset({'三月七', '罗刹'})),
    '黑塔纪元': (frozenset(), frozenset({'大黑塔', '黑塔'})),
    '轮回不止': (frozenset(), frozenset({'白厄'})),
    '白衣伙伴': (frozenset(), frozenset({'白厄', '星期日'})),
    '双龙会': (frozenset(), frozenset({'丹恒·饮月', '丹恒·腾荒'})),
    '偶像经济': (frozenset({'星间旅人'}), frozenset({'火花'})),  # 火花=星间旅人 4费核心(plaza traits 确认;用户授权查角色数据定)
    '愚者恶作剧': (frozenset(), frozenset({'花火', '火花'})),
    '砂里淘金': (frozenset(), frozenset({'砂金'})),
    '琼玉专家:青雀': (frozenset(), frozenset({'青雀'})),
    '贸易专家:停云': (frozenset(), frozenset({'停云'})),
    '调饮专家:加拉赫': (frozenset(), frozenset({'加拉赫'})),
    '锻冶专家:刃': (frozenset(), frozenset({'刃'})),
    '骇客专家:银狼': (frozenset(), frozenset({'银狼'})),
    '潜行专家:貊泽': (frozenset(), frozenset({'貊泽'})),
    '战术专家:佩拉': (frozenset(), frozenset({'佩拉'})),
    '领航专家:姬子': (frozenset(), frozenset({'姬子'})),
    '加拉赫顾问': (frozenset(), frozenset({'加拉赫'})),
    '停云顾问': (frozenset(), frozenset({'停云'})),
    '摸个鱼吧I': (frozenset(), frozenset({'青雀'})),
    '摸个鱼吧II': (frozenset(), frozenset({'青雀'})),
    '摸个鱼吧III': (frozenset(), frozenset({'青雀'})),
}
_BINDINGS_ORPHANS: list[str] = [n for n in STRATEGY_BINDINGS if n not in INVESTMENT_STRATEGIES]
if _BINDINGS_ORPHANS:
    raise ValueError(f"STRATEGY_BINDINGS 孤儿键(注册表无此卡,版本更新?):{_BINDINGS_ORPHANS}")


def strategy_bindings(strategy: InvestmentStrategy) -> tuple[frozenset[str], frozenset[str]]:
    """策略的(阵营绑定, 角色绑定)—— 查 STRATEGY_BINDINGS 语义表(ADR-0151 逐卡手建模;
    ↺ ADR-0134 的文本扫描派生已撤 —— 扫描有两类噪声:泛用效果顺带提及阵营误绑
    (战术义眼"恢复能量"≠能量队卡)/不可审不可纠;语义表可 dump 可逐条纠)。

    用于 decide_event 的 comp 匹配分 + cw_comps.held_strategy_fit(持卡影响 pivot)。
    未建模卡 → 空绑定(匹配分 0,回落评估分/品质先验;新 API 卡待 diff 提示后建模)。
    """
    return STRATEGY_BINDINGS.get(strategy.name, (frozenset(), frozenset()))


def get_strategy(name: str) -> InvestmentStrategy | None:
    """按规范名取 InvestmentStrategy;无则 None(注册表已全量 335,miss = OCR 形变,走 pick_value_of 的 LCS)。"""
    return INVESTMENT_STRATEGIES.get(name)

# ===== ADR-0143 选卡价值基准分(全量评估表派生;.debug/temp/currency_war/strategy_eval_full.tsv)=====
# 评估口径:value_class 七分类 + quantizable 三档 + pick_priority 0-100(读 effect 原文逐条判定;
# 无上下文基准分,comp 匹配/HP 分档在 decide_event 消费侧调)。表与注册表对拍:315/315 命中
# (curated+ingested;ADR-0150 后注册表 = plaza base 335,键经 canon 归一对齐)。
PICK_VALUE: dict[str, int] = {
    "鲜血阶梯": 75,
    "打通上下游·彩": 72,
    "远见": 70,
    "利息上调": 68,
    "高效决策": 65,
    "开源节流": 65,
    "藏一手": 65,
    "价值投资·彩": 62,
    "及时雨": 62,
    "全都要·彩": 60,
    "榜样的力量·彩": 60,
    "采购专员·彩": 58,
    "加油站": 58,
    "野蛮成长": 58,
    "后勤超响应": 58,
    "本金充裕+": 58,
    "钻石恒永久": 58,
    "三五成群": 56,
    "本金充裕": 55,
    "商业间谍": 55,
    "搜打撤": 55,
    "本姑娘就是罗刹": 55,
    "万箭齐发": 55,
    "战术义眼++": 55,
    "金币大使叽米": 55,
    "概率事件": 55,
    "爆仓": 55,
    "全都要·金": 55,
    "超发货币": 55,
    "买断制": 52,
    "采购专员·金": 52,
    "幸运闪避EX": 52,
    "战术义眼+": 52,
    "财富就是力量": 52,
    "幸运之子": 52,
    "团队力量·金": 52,
    "打通上下游·金": 52,
    "淘金客": 50,
    "分解万物": 50,
    "保守派": 50,
    "更快,更幸运": 50,
    "星徽大使叽米": 50,
    "战术义眼": 50,
    "和平手枪祝福": 50,
    "折叠小刀祝福": 50,
    "OOTD·金": 50,
    "中产阶级": 50,
    "免战牌": 50,
    "免费午餐": 50,
    "定期福利": 48,
    "摸个鱼吧III": 48,
    "黄金投资": 48,
    "爆晶矿·彩": 48,
    "黄金垃圾": 48,
    "量产型装甲祝福": 48,
    "成本控制": 48,
    "打人就打脸·金": 48,
    "长期主义+": 48,
    "彩虹期货+": 48,
    "全都要·银": 48,
    "生命之花祝福": 46,
    "伟大征服": 45,
    "基本保障": 45,
    "乱成一锅粥+": 45,
    "调饮专家:加拉赫": 45,
    "军备供应链": 45,
    "复印件": 45,
    "武装突入": 45,
    "奋斗协议": 45,
    "节节高升": 45,
    "装备方案A": 45,
    "终身学习": 45,
    "节假日礼盒": 45,
    "被动收入": 45,
    "装备方案B": 45,
    "手枪发烧友": 45,
    "入职礼包": 45,
    "独家代言": 45,
    "超光速提拔": 45,
    "偶像经济": 45,
    "广聚天下英才": 45,
    "幸运星祝福": 45,
    "四费晋升": 45,
    "星级压制": 45,
    "长期主义": 45,
    "彩虹期货": 45,
    "价值投资·金": 45,
    "榜样的力量·金": 45,
    "三三三": 45,
    "前段发力": 45,
    "固定理财+": 45,
    "人海战术": 45,
    "特战资金+": 45,
    "全员晋升": 45,
    "乱成一锅粥": 42,
    "着眼当下": 42,
    "琼玉专家:青雀": 42,
    "佩佩驾到": 42,
    "公司严选": 42,
    "愚者恶作剧": 42,
    "摸个鱼吧II": 42,
    "专家招募+": 42,
    "星魂升华": 42,
    "延迟收益": 42,
    "爆晶矿·金": 42,
    "固定理财": 42,
    "四费援军": 42,
    "难度修改器": 42,
    "完美进化": 40,
    "快请专家·彩": 40,
    "贸易专家:停云": 40,
    "优势火力论": 40,
    "星际和平保险": 40,
    "控制规模": 40,
    "彩虹矿+": 40,
    "佩佩客串": 40,
    "好运令牌·彩": 40,
    "潜行专家:貊泽": 40,
    "退化": 40,
    "摸个鱼吧I": 40,
    "五百强": 40,
    "小复制+": 40,
    "孪生素数": 40,
    "绕口令": 40,
    "嘴硬": 40,
    "这么大的钻石": 40,
    "秘密典籍+": 40,
    "成长的快乐": 40,
    "胜利,还是胜利": 40,
    "打捞人才库+": 40,
    "存款回报": 40,
    "特战资金": 40,
    "团队力量·银": 40,
    "当头一棒": 40,
    "简单模式": 40,
    "脱颖而出": 38,
    "公司军火更新·彩": 38,
    "精密拆装·彩": 38,
    "大扩招": 38,
    "幸运中的幸运": 38,
    "大裁员": 38,
    "幸运喷雾": 38,
    "市场干预": 38,
    "爆晶矿·银": 38,
    "完美开局": 38,
    "返利+": 35,
    "数值碾压": 35,
    "攻防一体": 35,
    "融合召唤": 35,
    "轮回不止": 35,
    "武器批发商": 35,
    "客制化服务": 35,
    "天降救兵": 35,
    "晋升名额": 35,
    "彩虹矿": 35,
    "停云顾问": 35,
    "加拉赫顾问": 35,
    "骇客专家:银狼": 35,
    "按劳分配": 35,
    "专家招募": 35,
    "人才济济": 35,
    "降本增效": 35,
    "不要小看我们的羁绊": 35,
    "市场活力": 35,
    "小复制": 35,
    "星变": 35,
    "独狼": 35,
    "秘密典籍": 35,
    "升级锅炉": 35,
    "经验就是财富": 35,
    "二极管": 35,
    "打捞人才库": 35,
    "三费援军": 35,
    "经验到账": 35,
    "返利": 35,
    "成长基金": 35,
    "合并同类项": 35,
    "健康充值": 35,
    "正能量": 35,
    "基层贡献": 35,
    "燃起来了": 33,
    "超充站": 33,
    "月光宝盒": 33,
    "赞美太阳": 33,
    "梦境大舞台": 33,
    "装备党": 33,
    "人在旅途": 33,
    "读博深造": 33,
    "快请专家·金": 32,
    "如有神助": 32,
    "阿哈大悦": 32,
    "人才空洞": 32,
    "量子力学": 32,
    "双人舞": 32,
    "全武行": 32,
    "免费升舱": 32,
    "黄金期货+": 32,
    "以战养战": 32,
    "武力刷新": 32,
    "武装支援+": 32,
    "招聘资金+": 32,
    "溜佩佩+": 32,
    "保险": 32,
    "应援团": 32,
    "榜样的力量·银": 32,
    "定点爆破": 30,
    "羁绊的力量": 30,
    "双龙会": 30,
    "白衣伙伴": 30,
    "临时工合约": 30,
    "贝洛伯格星徽套组": 30,
    "银河学者星徽套组": 30,
    "列车同行星徽套组": 30,
    "盛会之星星徽套组": 30,
    "昼之半神星徽套组": 30,
    "夜之半神星徽套组": 30,
    "追击星徽套组": 30,
    "狼狩星徽套组": 30,
    "仙舟星徽套组": 30,
    "星间旅人星徽套组": 30,
    "追击星徽套组(二)": 30,
    "击破星徽套组": 30,
    "群攻星徽套组": 30,
    "能量星徽套组": 30,
    "治疗星徽套组": 30,
    "燃血星徽套组": 30,
    "减益星徽套组": 30,
    "持续伤害星徽套组": 30,
    "量子同频星徽套组": 30,
    "护盾星徽套组": 30,
    "战技点星徽套组": 30,
    "迷之旅人": 30,
    "好运来": 30,
    "白银投资": 30,
    "剩余价值": 30,
    "空仓+": 30,
    "钢铁美学": 30,
    "枪在手+": 30,
    "市场混乱": 30,
    "现金为王": 30,
    "精密拆装·金": 30,
    "蓝钻闪耀": 30,
    "红钻闪耀": 30,
    "回收计划+": 30,
    "公司军火更新·金": 30,
    "借力打力": 30,
    "黄金期货": 30,
    "全队的希望": 30,
    "尾款交付": 30,
    "军火贸易+": 30,
    "人力重组": 30,
    "溜佩佩": 30,
    "招财狗": 30,
    "自由市场": 30,
    "效率员工奖": 30,
    "盗用身份": 28,
    "创伤小组": 28,
    "回收计划": 28,
    "银河学者星徽": 28,
    "仙舟星徽": 28,
    "列车同行星徽": 28,
    "夜之半神星徽": 28,
    "昼之半神星徽": 28,
    "盛会之星星徽": 28,
    "击破星徽": 28,
    "能量星徽": 28,
    "治疗星徽": 28,
    "燃血星徽": 28,
    "群攻星徽": 28,
    "追击星徽": 28,
    "狼狩星徽": 28,
    "星间旅人星徽": 28,
    "贝洛伯格星徽": 28,
    "减益星徽": 28,
    "持续伤害星徽": 28,
    "量子同频星徽": 28,
    "护盾星徽": 28,
    "战技点星徽": 28,
    "欢愉星徽": 28,
    "是钻石总会发光": 28,
    "二费援军": 28,
    "人才激励+": 28,
    "招聘资金": 28,
    "买彩票+": 28,
    "军火贸易": 26,
    "决议:娱乐星球": 25,
    "黄晶矿工": 25,
    "孪生姵姵": 25,
    "空仓": 25,
    "砂里淘金": 25,
    "枪在手": 25,
    "风暴骑士": 25,
    "好运令牌·金": 25,
    "无害垃圾": 25,
    "规模效应": 25,
    "人才激励": 25,
    "公司人才流动": 25,
    "扩充团队": 25,
    "武装支援": 25,
    "气氛组+": 25,
    "买彩票": 25,
    "公司军火更新·银": 25,
    "许诺特权": 25,
    "钻石商人": 25,
    "好运令牌·银": 25,
    "多元化团队": 22,
    "躺平": 22,
    "无伤通关": 22,
    "精密拆装·银": 22,
    "不等价交换": 20,
    "节省工位": 20,
    "气氛组": 20,
    "赌神·银": 20,
    "先亏后盈": 18,
    "恢复生机": 12,
}
_PICK_ORPHANS: list[str] = [n for n in PICK_VALUE if n not in INVESTMENT_STRATEGIES]
if _PICK_ORPHANS:
    raise ValueError(f"PICK_VALUE 孤儿键(注册表无此卡,版本更新?):{_PICK_ORPHANS}")
for _n, _v in PICK_VALUE.items():
    INVESTMENT_STRATEGIES[_n] = replace(INVESTMENT_STRATEGIES[_n], pick_value=_v)

# HP<40 生存类(评估表 notes 钩子:恢复/免战/降难度;decide_event 低血 +15)
SURVIVAL_PICKS: frozenset[str] = frozenset({
    '健康充值', '成本控制', '星际和平保险', '藏一手', '免战牌', '保险',
    '奋斗协议', '退化', '简单模式', '难度修改器',
})

# r255(P2 断崖装备缺失,11 局实锤):装备流策略——P2r1 的
# 掉血(-14~-41)与板面弱相关,五局 P2 板面 equips 全空
# (裸件打仗);军火类策略(每节点刷装备)是 P2 生存的
# 关键补强通道。decide_event 在 P2 给这类 +25。
EQUIP_FLOW_PICKS: frozenset[str] = frozenset({
    '公司军火更新·彩', '公司军火更新·金', '公司军火更新·银',
    '军火贸易', '军火贸易+', '轮回不止', '装备方案A',
    '军备供应链', '武器批发商', '采购专员·彩', '采购专员·金',
})


def pick_value_of(name: str) -> int | None:
    """选卡价值基准分(ADR-0143)。精确名优先;OCR 形变走 LCS(0.6 + 长度差守卫,评审建议6:
    |Δlen|≤3 —— 防未来新增短名/长名与现有卡高 LCS 借分;env 名的跨表污染由 cw_events 守卫
    另行拦截,此处只管策略表内部);未评估(codex 新条目/完全未知)→ None(回落品质先验)。"""
    s = INVESTMENT_STRATEGIES.get(name)
    if s is not None and s.pick_value > 0:
        return s.pick_value
    from one_dragon.utils.str_utils import find_best_match_by_lcs
    names = list(INVESTMENT_STRATEGIES)
    idx = find_best_match_by_lcs(name, names, lcs_percent_threshold=0.6)
    if idx is not None and abs(len(names[idx]) - len(name)) <= 3:
        v = INVESTMENT_STRATEGIES[names[idx]].pick_value
        return v if v > 0 else None
    return None


# ===== ADR-0144 环境选卡价值基准分(83 条全量评估表派生;.debug/temp/currency_war/env_eval_full.tsv)=====
# 环境与策略结构倒挂(评估实证):synergy 主导 47/83(阵营定向),economy 16;无品质分级(全 '-')。
# 量化断层:yes-direct 仅 1 条(蓝海)—— 环境效果全是整局规则(费率覆写/分期/重复触发),EconomyEffect
# 现有字段结构性装不下(EnvEconomyEffect 扩字段待后续);接线防一次性错装点名 6 条见 TSV notes。
ENV_PICK_VALUE: dict[str, int] = {
    "追击概念股": 52,
    "击破概念股": 50,
    "群攻概念股": 44,
    "能量概念股": 44,
    "燃血概念股": 50,
    "减益概念股": 48,
    "战技点概念股": 46,
    "仙舟概念股": 48,
    "贝洛伯格概念股": 38,
    "狼狩概念股": 40,
    "星间旅人概念股": 40,
    "银河学者概念股": 44,
    "列车同行概念股": 44,
    "昼之半神概念股": 44,
    "夜之半神概念股": 48,
    "仙舟邀请": 30,
    "贝洛伯格邀请": 30,
    "狼狩邀请": 30,
    "盛会之星邀请": 30,
    "星间旅人邀请": 30,
    "银河学者邀请": 30,
    "列车同行邀请": 30,
    "昼之半神邀请": 30,
    "夜之半神邀请": 30,
    "追击邀请": 30,
    "击破邀请": 30,
    "群攻邀请": 30,
    "能量邀请": 30,
    "燃血邀请": 30,
    "减益邀请": 30,
    "持续伤害邀请": 30,
    "量子同频邀请": 30,
    "战技点邀请": 30,
    "欢愉邀请": 30,
    "命运圣杯邀请": 32,
    "星核猎手契约": 52,
    "战技点契约": 58,
    "公司契约": 48,
    "持续伤害契约": 48,
    "量子同频契约": 45,
    "欢愉契约": 42,
    "命运圣杯契约": 52,
    "黄金时代": 55,
    "白银时代": 35,
    "彩虹时代": 72,
    "头彩": 55,
    "尾彩": 52,
    "银·金·彩": 62,
    "经济过热": 55,
    "经济严重过热": 58,
    "增发货币": 48,
    "过剩经费": 52,
    "人身意外险": 48,
    "长线利好": 65,
    "二手市场": 45,
    "蓝海": 38,
    "深井角斗场": 42,
    "火药味": 28,
    "特权阶级": 38,
    "人才引进": 36,
    "成功经验": 36,
    "红钻贵族": 38,
    "蓝钻贵族": 38,
    "人才下沉": 48,
    "联席决策": 50,
    "轮岗": 42,
    "劳务派遣合同": 52,
    "战争边疆": 35,
    "粗星佩佩": 45,
    "三星佩佩": 42,
    "敌后破坏": 46,
    "进化算法": 70,
    "策略大师": 64,
    "人才储备": 48,
    "战力飙升": 42,
    "战力提升": 38,
    "专家研讨会": 34,
    "特邀专家:银狼": 30,
    "特邀专家:加拉赫": 42,
    "特邀专家:停云": 38,
    "特邀专家:桑博": 35,
    "命运礼物": 40,
    "英雄登场": 32,
}
_ENV_PICK_ORPHANS: list[str] = [n for n in ENV_PICK_VALUE if n not in INVESTMENT_ENVS]
if _ENV_PICK_ORPHANS:
    raise ValueError(f"ENV_PICK_VALUE 孤儿键(注册表无此环境?):{_ENV_PICK_ORPHANS}")
for _n, _v in ENV_PICK_VALUE.items():
    INVESTMENT_ENVS[_n] = replace(INVESTMENT_ENVS[_n], pick_value=_v)

# 阵营定向类 comp 匹配条件分下限(评估表条件白名单:概念股→78 / 邀请→70 / 契约 66-78 取 72;
# faction ∩ target_comp.factions 时 score 提到下限,未匹配吃裸基准分)
ENV_FACTION_MATCH_FLOOR: dict[str, float] = {'概念股': 78.0, '邀请': 70.0, '契约': 72.0}
# HP<40 钩子(评估表 notes:白银时代/敌后破坏 +15 降难度求稳;人身意外险 +10 补给补强)
ENV_SURVIVAL_BONUS: dict[str, float] = {'白银时代': 15.0, '敌后破坏': 15.0, '人身意外险': 10.0}
