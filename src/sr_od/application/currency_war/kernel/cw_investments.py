"""货币战争 投资策略 + 投资环境领域模型(meta 层,V4.4)。

**两层架构(ADR-0150)**:
- **base 事实层** = ``cw_invest_data.py``(``tools/cw/gen_plaza_invest.py`` 从米游社攻略广场
  官方 API 生成,勿手编):名字/品质/效果全文,数字 id 稳定主键,投资策略 334 + 投资环境 83
  官方全量(游戏内数据银行同口径,米游社百科 doc 的 19 条版本漂移缺口就此补齐)。
- **建模增量层** = 本文件手维护(API 给不了的人工建模):
  - ``STRATEGY_ECONOMY``(ADR-0131 可数值化经济效果);
  - ``is_blood_economy``/``blood_xp_mode``(血本位判别与 XP 购买模式解析,
    [40]① 选择回避 / [40]② 血闸共享判据,ADR-0578);
  - ``ENV_CATEGORY``/``ENV_FACTION``(环境 7 类分类 + 阵营绑定,ENV_FACTION_MAP 派生源);
  - ``_MANUAL_EXTRAS``(plaza 不收的补遗条目);
  - ``PICK_VALUE``/``ENV_PICK_VALUE``(ADR-0143/0144 选卡评估分;SURVIVAL_PICKS
    等事件面钩子已退役)。
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

from sr_od.application.currency_war.data.cw_chars import CHARACTER_ROSTER
from sr_od.application.currency_war.data.cw_invest_data import (
    PLAZA_AUGMENTS,
    PLAZA_PORTALS,
)
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    BOARD_REWRITE_SELL_ALL,
    BOARD_REWRITE_UPGRADE_ALL,
    BattlefieldEffect,
    DurationKind,
    DutyFlags,
    EffectKind,
    EffectSpec,
    TriggerKind,
    UnitBuffRef,
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
    economy: EnvEconomyEffect | None = None  # 整局经济通道(白名单制;ENV_ECONOMY 构建期 replace 挂载,表外恒 None)


@dataclass(frozen=True)
class EconomyEffect:
    """投资策略/环境的**可数值化经济效果**(ADR-0131;用户 2026-08-15:效果要直接转经济模型)。

    只收能进策略层算账的效果(给金/免费刷新/利息/经验/连胜倍率);战力类(数值碾压/攻防一体等)
    不在此(走战力评估,不进经济)。全 0/None = 无经济效果。字段语义:
    - instant_gold: 选牌当场给金(一次性)
    - gold_per_node: 每次进入新节点给金
    - free_refresh_per_node: 每节点免费刷新次数(成本 0 的刷新)
    - free_refresh_burst: 一次性海量免费刷新(如高效决策 9999 次);限时窗口策略层不编排时机(执行层待办)
    - free_refresh_cond_gold_above/step/cap: 条件判定族三元组(本金充裕系=50/10/3)——每次进入
      新节点时,金 > above 每额外 step 金 +1 次免费刷新、至多 cap 次;发放经
      grant_effect_node_refresh_balance 桥(节点 tick 采样,金=bs.gold 现值评估)
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
    """
    instant_gold: int = 0
    gold_per_node: int = 0
    free_refresh_per_node: int = 0
    free_refresh_burst: int = 0
    # 条件判定族三元组(本金充裕/+,官方卡文 cw_invest_data.py:251-252 id
    # 301001/301002;GameState 设计 §3.3.6 免费刷新余额判定输入):三字段
    # 齐备(>0)才激活,半配对保守 no-op;不做 aggregate_economy 标量聚合
    # (多条件条目各按现值评估,不可折叠单标量),桥逐条目读。
    free_refresh_cond_gold_above: int = 0   # 触发金阈值(严格大于;本金充裕=50)
    free_refresh_cond_gold_step: int = 0    # 每额外该值金 +1 次免费刷(本金充裕=10)
    free_refresh_cond_cap: int = 0          # 单次触发至多授予次数封顶(本金充裕=3)
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
    # —— 机制修改器审计 F1/F2/F3(数值=效果原文,plaza API)——
    refresh_free_chance: float = 0.0      # 概率事件(棱彩):每次刷新 45% 概率免费
                                          # → 消费侧折算期望刷价 = 基准 2×(1−0.45)=1.1
                                          # (MechanismMutation.refresh_price_mult 通道)
    xp_buy_hp_cost: int = 0               # 奋斗协议(棱彩):购经验每击耗 6 血非金
                                          # (成本币种切换;首领战结束回 50 血=行为段,
                                          # 不入经济账,仅本注释留档)
    refresh_shop_rewrite_every_3cost: int = 0  # 市场干预(银):下一次和每 4 次刷新全 3 费面
                                          # (池构成族突变旗标字段;5 次免费刷走 free_refresh_burst)
    # —— 词缀源效果字段(敌人词缀改写源;结构化注册 =
    #    kernel/cw_affix_effects.AFFIX_EFFECT_SPECS,非策略源——不经
    #    STRATEGY_ECONOMY 键空间、不经 aggregate_economy 聚合通道)——
    xp_click_surcharge_from_level: int = 0        # 成长的烦恼:该级起每次购经验多付金(配对字段 below)
    xp_click_surcharge_from_level_at: int = 0     # 触发等级(8);镜像 xp_click_discount_from_level 对
    hp_max_loss_pct_of_loss: int = 0              # 永久创伤:每损失生命值的同值百分比计入生命上限损耗
                                          # (仅建档,不进经济分——gold_per_20hp_lost 同先例)
    hp_max_loss_cap_pct: int = 0                  # 生命上限损耗上限(原生命上限百分比基准;永久创伤=60)


def is_blood_economy(eff: EconomyEffect | None) -> bool:
    """血本位突变判别([40]①「主动选择=回避」的候选判据;ADR-0578)。

    判据 = 效果把 HP 写进经济循环的字段:购经验币种切换(xp_buy_hp_cost)
    ∨ HP↔金互换(hp_gold_swap)。补偿型字段(gold_per_20hp_lost/
    gold_per_hp_lost_now)不改支付币种,不入族;名字含「血」不可作判据
    (反例:鲜血阶梯 = 击杀增伤卡,effect 无 HP 经济字段)。当前族集 =
    {奋斗协议, 不等价交换}——与 [40] 裁定原文点名完全一致;新血本位卡
    建模 EconomyEffect 对应字段即自动入族(零名单维护)。
    """
    if eff is None:
        return False
    return eff.xp_buy_hp_cost > 0 or eff.hp_gold_swap


@dataclass(frozen=True)
class EnvEconomyEffect:
    """投资环境的**整局经济通道**结构(2026-09-12 invest-env 迭代,design.md §2.2.2)。

    区别于 EconomyEffect 的 per-node/一次性形态:环境效果是整局规则改写
    (位面开局分期/条件触发/费率覆写),字段按通道语义设计,全部带缺省值
    (无通道 = 全缺省)。估值单一入口 = ``cw_env_economy.env_economy_value``
    (A 类精确 + 估算参数 fail-closed;B/C 通道估值公式与参数归数据批)。
    **白名单制**:只收 ENV_ECONOMY 显式登记条目,禁从效果原文自动猜装
    (防错装对账 = _validate_env_economy,ADR-0144 决策 3 六条点名)。
    字段语义(值全部 = cw_invest_data 效果原文直读):
    - gold_per_plane_start: 每位面开局金,元组下标 = 位面−1(增发货币 (6,8,12);
      晶矿→金兑现按自动开启建模——晶矿开启是玩家动作面,自动与否未实采
      (战技点契约「打开20个晶矿后」为存在玩家动作的佐证),design.md §2.2.1
      假设登记;证非自动则 bot 具备开矿动作前该通道 fail-closed)
    - gold_instant: 获得时一次性金(蓝海 6;随机环境期望不计——选卡时未知
      且分布含未入模者,design §2.6 取舍)
    - xp_after_level: (等级, 节点数, 每节点XP)(成功经验 (8,3,12);「升 8
      必然发生」假设显式登记(design §2.2.1,发展优先战略下 lv8 标配),
      证伪改条件概率)
    - gold_per_strategy_coef: 每取一张策略 +coef×取卡前已持有数(策略大师 2;
      3-5 节点额外策略不计——策略域价值非经济通道,design §2.2.1)
    - gold_after_refreshes: (刷新阈值, 返金)(长线利好 (30,20)/二手市场 (20,30);
      B 类,估值公式与参数归数据批)
    - refresh_cost_after: (刷新阈值, 新成本)(长线利好 (30,1);基价 2 为游戏定义)
    - reward_node_bonus: C 类通道在场哨兵(1.0 = 通道在,经济过热/经济严重
      过热;每奖励节点期望增益真值+CI 在估算注册表,按环境变体分键——
      cw_env_economy._REWARD_BONUS_VARIANTS;非零而缺变体映射 = 登记笔误,
      构建校验炸出)
    """
    gold_per_plane_start: tuple[int, ...] = ()
    gold_instant: int = 0
    xp_after_level: tuple[int, int, int] | None = None
    gold_per_strategy_coef: int = 0
    gold_after_refreshes: tuple[int, int] | None = None
    refresh_cost_after: tuple[int, int] | None = None
    reward_node_bonus: float = 0.0


@dataclass(frozen=True)
class GiftGrant:
    """投资环境的**具名发放**结构(送卡型估值;2026-09-12 invest-env 迭代,
    details/env-value-models.md §2.1.3;InvestmentEnv 同区 schema)。

    发放按「取环境当场到手(即时)」与「满足条件后到手(条件)」两分——估值只对
    确定性部分给足档,条件部分降档处理(详设 §2.1.2 规则 3)。送卡的价值判据 =
    **所赠角色是否被候选终局阵容使用**(结构集合级,零数值零战力,开局静态可用;
    宪法 00_framework §1.1 禁战力建模,卖价残值对「送的人有没有人用」零判别力)。
    档位机器 = ``cw_comps.gift_hit_tier``;档位是定序实现常数非金流期望
    (ADR-0524 定序/基数分账:(expected_gold, resolved) 契约装不下 66/60/54 档
    语义),**不经经济入口**,消费位 = cw_events env 分支独立 max() 支(3.5 接线)。
    字段语义(值全部 = cw_invest_data 效果原文直读):
    - chars_immediate: 取环境当场发放的具名角色(效果原文「获得【X】」直读)
    - chars_conditional: (角色, 条件描述原文摘要)二元组——注释性字段,不进判据
      (可读性 + 实采对账用);不可具名的随机发放(如战技点契约「随机战技点
      羁绊角色」)不入本字段,只随条件摘要留档
    - advisor: True=专家顾问入商店语义(特邀专家;创造一个可购买的购买选项,
      需再花店价且占购买预算,价值严格低于同档白得——资产账/可得性账分立,
      详设 §2.1.2 规则 2);False=直接送卡(契约,白得资产)
    - sell_value_note: 卖价残值注记(【注】下界;卖价 ≈ 按费用退金,度量费用
      不度量阵容价值,不进任何分值族,详设 §2.1.2-2)
    """
    chars_immediate: tuple[str, ...] = ()
    chars_conditional: tuple[tuple[str, str], ...] = ()
    advisor: bool = False
    sell_value_note: str = ''


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
    # 本金充裕系:官方「获得26/45金币。每次进入新节点时,若拥有超过50金币,
    # 每额外10金币就会获得1次免费刷新(最多3次)」(cw_invest_data.py:251-252,
    # id 301001/301002)。两卡条件腿卡文逐字同文 → 三元组同值;棱彩加强值
    # 只在 instant_gold(26 vs 45)。条件腿发放经节点桥(§3.3.6)。
    '本金充裕': EconomyEffect(instant_gold=26, free_refresh_cond_gold_above=50,
                              free_refresh_cond_gold_step=10, free_refresh_cond_cap=3),
    '开源节流': EconomyEffect(instant_gold=10, interest_cap_override=9),
    '利息上调': EconomyEffect(instant_gold=25, interest_cap_override=10),
    '买断制': EconomyEffect(instant_gold=15, interest_cap_override=0, xp_per_node=4),
    '淘金客': EconomyEffect(xp_per_refresh=2),
    '伟大征服': EconomyEffect(win_reward_mult=3.0, difficulty_per_streak=1, xp_instant=12),
    # ↑ 按 API 原文全额建模:×3 连胜奖励 + 敌人难度+N(N=连胜)+ +12XP(ADR-0205)
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
    # ↑ 全额建模:「后续策略节点→随机棱彩(不可刷)」+「不增加敌人难度」(API 原文;
    # 期权/难度侧由 33/36 号消费)
    '贸易专家:停云': EconomyEffect(instant_gold=10),
    '佩佩驾到': EconomyEffect(instant_gold=8),
    '控制规模': EconomyEffect(instant_gold=40),
    '藏一手': EconomyEffect(instant_gold=80),
    '及时雨': EconomyEffect(free_refresh_burst=4),
    '决议:娱乐星球': EconomyEffect(instant_gold=50),
    '公司严选': EconomyEffect(instant_gold=3),
    '节节高升': EconomyEffect(gold_per_level_up=1),
    '本金充裕+': EconomyEffect(instant_gold=45, free_refresh_cond_gold_above=50,
                               free_refresh_cond_gold_step=10, free_refresh_cond_cap=3),
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
    # ↑ 免费刷 + 卖价×2。5=已裁漂移,官方卡文=6(base 层 plaza:202101,权威序正本=ADR-0620):
    #   纠偏 5→6 是行为面变更,归建模批走方案审/落地审;改 6 前以 5 为现行行为,读值方禁自行 +1。
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
    # 等级触发族
    '成长基金': EconomyEffect(gold_at_level=40, gold_at_level_target=9),
    '成长的快乐': EconomyEffect(xp_instant=4,
                                xp_click_discount_from_level=1, xp_click_discount_from_level_at=8),
    # 时点日程族
    '超发货币': EconomyEffect(gold_at_node=70, gold_at_node_offset=5),
    # ↑ 负债部分(失去现有全部金)由消费端按持有金处理,数值侧只记回流 +70
    '固定理财': EconomyEffect(xp_per_node=0, free_refresh_burst=2),   # 即时段(位面开始段见下,待建模)
    '固定理财+': EconomyEffect(free_refresh_burst=3),
    # ↑ 「现在+每位置面开始 4/6XP+2/3 刷」——此处只建即时刷;位面开始段待建模
    '经验到账': EconomyEffect(xp_instant=10),
    '孪生素数': EconomyEffect(xp_instant=0),   # 首购计数器(2/3/5/7/11)——行为条件流,消费端计数
    # 动态/血金互兑族
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
    # —— 机制修改器审计 F1/F2/F3(效果原文=cw_invest_data
    #    plaza API 逐字:概率事件 300401/奋斗协议 301801/市场干预 102201)——
    '概率事件': EconomyEffect(refresh_free_chance=0.45),
    # ↑ 「刷新时有45%概率获得一次免费刷新」——期望刷价口径 2×0.55=1.1
    #   (MechanismMutation.refresh_price_mult=0.55)
    '奋斗协议': EconomyEffect(xp_buy_hp_cost=6),
    # ↑ 「购买经验值消耗6点小队生命值而非金币。首领战斗结束时回复50点小队生命值」——
    #   金侧成本置 0(血本位),IMPL §6.2 血本位安全带按 rate=6 直读本字段;回血段=行为流不建模
    '市场干预': EconomyEffect(free_refresh_burst=5, refresh_shop_rewrite_every_3cost=4),
    # ↑ 「下一次和每4次商店刷新都将是全3费角色。获得5次刷新」——池构成族突变旗标
    #   (v_c/a_c 池面改写;消费规范见设计总纲注记,修复项14)
}


# ===== curated overlay:策略效果规格 EffectSpec(效果清单骨架实现;手维护,键=注册表规范名)=====
# 机制 = cw_effect_inventory.py(EffectSpec/ActiveEffectInventory);本 overlay 只放**数据**,
# 与 STRATEGY_ECONOMY 同键空间同孤儿校验(见 _validate_strategy_effects),防两套 overlay 漂移。
# 首批 9 条语义全引 cw_invest_data 官方原文;二义条目 pending=True + notes 保守支,不拍死——
# 定谳后回填 verdict(单一语义以实采为准)。
# 边界:只产策略源;环境('portal')/词缀('affix')双源注册属环境/词缀效果辖域,此处不建其条目。
STRATEGY_EFFECTS: dict[str, EffectSpec] = {
    # 淘金客:官方「你每次消耗金币刷新商店,都会获得2经验值」;免费刷不产 XP(「消耗金币」
    # 文本充分;实采复核挂账)。姿态谓词/LevelUp 抑制属淘金客姿态面辖域,本批不接。
    '淘金客': EffectSpec(
        id='301601', name='淘金客', trigger=TriggerKind.ON_REFRESH,
        duration=DurationKind.WHILE_HELD, category=EffectKind.STATE,
        payload=STRATEGY_ECONOMY['淘金客'], duties=DutyFlags(respond=True),
        notes='每次付费刷新+2XP;查询键 xp_per_refresh'),
    # 固定理财:官方「现在以及每个位面开始时,获得4经验值和2次免费刷新」。
    # 待采:开头「现在」段与「每个位面开始」段是否同一 trigger 双发(overlay STRATEGY_ECONOMY
    # 注释已标注位面开始部分拆分);保守支=按 PLANE_START 单触发建模。
    '固定理财': EffectSpec(
        id='201801', name='固定理财', trigger=TriggerKind.PLANE_START,
        duration=DurationKind.PERMANENT, category=EffectKind.STATE,
        payload=STRATEGY_ECONOMY['固定理财'], duties=DutyFlags(track=True, respond=True),
        pending=True,
        notes='待采:即时段与位面段是否双发;保守支=PLANE_START 单触发'),
    # 经验就是财富:官方「获得经验时,改为获取等量金币(购买经验除外)。获得4金币」。
    # 四歧义(改道是否吞策略给的 XP/转换同事件性/上限/版本变体)见该条目待采挂账;
    # 定谳前保守支=「吞」(组合在场按改道成立处理)。xp 改道算子字段待定谳后补 payload。
    '经验就是财富': EffectSpec(
        id='103601', name='经验就是财富', trigger=TriggerKind.CONDITIONAL,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['经验就是财富'], duties=DutyFlags(respond=True),
        pending=True,
        notes='待采(W610-P1 §1.4.1 四歧义);保守支=改道吞非购买 XP'),
    # 商业间谍:官方「购买经验的花费减1,升级时刷新商店,并偷取其中最贵的3个角色」。
    # 战场段(升级偷牌)入 spec;降价段在 STRATEGY_ECONOMY(xp_buy_cost_discount)。
    '商业间谍': EffectSpec(
        id='300201', name='商业间谍', trigger=TriggerKind.LEVEL_UP,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(steal_on_level_up=3),
        duties=DutyFlags(predict=True, respond=True),
        notes='LevelUp 后商店必刷新+偷最贵 3 张;shop 读牌/买牌对账须预知'),
    # 双手狸开键盘!(游戏内单位名 Gemi狸;注册表官方卡名见 204101):
    # 官方「进入新节点时,它会免费刷新商店2次,自动购买你场上拥有的角色」。
    '双手狸开键盘！': EffectSpec(
        id='204101', name='双手狸开键盘！', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(free_refresh_on_node_enter=2, auto_buy_owned=True),
        duties=DutyFlags(track=True, predict=True),
        notes='代买使「牌自己消失」,商店读牌/买牌对账必须预知(W610-P1 §1.5-6 挂时序实采)'),
    # 采购专员·金/彩:官方「每7/5次刷新,商店会刷出5张费用相同的角色,费用为你备战席
    # 最左侧角色的费用」。刷新计数器走 inventory counters[CounterKey.REFRESH]。
    '采购专员·金': EffectSpec(
        id='201201', name='采购专员·金', trigger=TriggerKind.ON_REFRESH,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(counter_every=7, shop_rewrite=True),
        duties=DutyFlags(track=True, predict=True, respond=True),
        notes='备战席最左语义与被动收入同抢(交互仲裁挂设计,本批不建模)'),
    '采购专员·彩': EffectSpec(
        id='303101', name='采购专员·彩', trigger=TriggerKind.ON_REFRESH,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(counter_every=5, shop_rewrite=True),
        duties=DutyFlags(track=True, predict=True, respond=True),
        notes='同采购专员·金,门槛 5'),
    # 全员晋升(板面重写族代表):官方「场上的所有角色会永久升级成比自身高1费的随机角色
    # (最大5费)。获得2个【拆装扳手】」。
    '全员晋升': EffectSpec(
        id='102701', name='全员晋升', trigger=TriggerKind.INSTANT,
        duration=DurationKind.ONCE, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(board_rewrite=BOARD_REWRITE_UPGRADE_ALL),
        duties=DutyFlags(predict=True),
        notes='board/target 全量失效→方向重估强制重派生是后续批辖域;'
              '写归属=替换面随机零逻辑写(详设 §5 全员晋升行)'),
    # 人力重组:官方「出售场上和备战席的所有角色。获得1个随机的2星3费角色、2个2星2费
    # 角色和2个2星1费角色」。⚠️ 注册表 STRATEGY_ECONOMY 无此条(经济面未建模,发牌资产
    # 走战力评估)——语义实为全场出售的板面重写,按 BATTLEFIELD 建模(效果规格判读
    # 归类同族:全员晋升/人力重组/现金为王=即时全场板面重写/出售)。
    '人力重组': EffectSpec(
        id='102801', name='人力重组', trigger=TriggerKind.INSTANT,
        duration=DurationKind.ONCE, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(board_rewrite=BOARD_REWRITE_SELL_ALL),
        duties=DutyFlags(predict=True),
        notes='全场出售事件;执行时序编排(卖→免费买→狂刷)=W610-P1 M8,本批不接;'
              '写归属=出售面逻辑写/发牌面观察收口(详设 §5 人力重组行)'),
    # 躺平:官方「你无法在商店购买角色和刷新,持续3个节点。在此之后,获得20金币」。
    # inventory 余期追踪首例(remaining_nodes 3→0 移除);冻结姿态属姿态面辖域。
    '躺平': EffectSpec(
        id='102001', name='躺平', trigger=TriggerKind.CONDITIONAL,
        duration=DurationKind.N_NODES, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['躺平'], duties=DutyFlags(track=True, respond=True),
        duration_nodes=3,
        notes='禁买+禁刷 3 节点后 +20 金'),
    # 免战牌:官方「进入战斗节点时,直接跳过战斗并进入下一个节点,可生效2次。
    # 获得30点经验。」(cw_invest_data.py:109,PlazaAugment 151301)。建模批件
    # 落注册表条目(设计 §8.7 批次三件 5):次数类余量首例
    # (duration_uses=2 → remaining_uses,§3.2.19 正本=effect_inventory
    # .remaining_uses,§8.6-3),递减挂点 = 跳过型出战上报(kernel
    # cw_exec_state.apply_op_effect;StartBattleOp 经 runner 包络上报跳过
    # 子态,上报时递减——出战域重设计 T-286),用尽移除。+30 经验 = 选牌当场
    # 即时经验(§4 投资选择通用通道,xp_instant 词表;§5.2 显式豁免——即时
    # 到账不入缺口清单,经观察覆盖收口)。trigger=NODE_ENTER(跳过发生在
    # 进入战斗节点时点);归 STATE 族(发给自己的经验)而跳过机制本体由
    # 次数余量维度承载,不占 BattlefieldEffect 改写载荷。
    '免战牌': EffectSpec(
        id='151301', name='免战牌', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.STATE,
        payload=EconomyEffect(xp_instant=30), duties=DutyFlags(track=True),
        duration_uses=2,
        notes='跳过战斗×2(remaining_uses 正本);+30 经验选牌当场'),
    # 本金充裕/+:官方「获得26/45金币。每次进入新节点时,若拥有超过50金币,
    # 每额外10金币就会获得1次免费刷新(最多3次)」(cw_invest_data.py:251-252,
    # id 301001/301002)。条件判定族(GameState 设计 §3.3.6 免费刷新余额的
    # 条件性来源):触发=节点进入、条件=金>50、梯度=每 10 金 1 次、封顶=3;
    # 发放经 grant_effect_node_refresh_balance 桥自动生效(§3.3.6「结构化后
    # 经同一桥」):桥按 bs.gold 现值逐条目评估,金未读(None)保守零授予。
    # counter 不建(无剩余/门槛累计量,授予量由当拍金现值决定,§3 计数器
    # 模型无动态需求为空);duties 全空(无计数器/无预知/无姿态消费面)。
    # payload 引 STRATEGY_ECONOMY 同一实例(单一源);棱彩加强值口径 =
    # instant_gold 26/45,条件腿两卡逐字同文同值。
    '本金充裕': EffectSpec(
        id='301001', name='本金充裕', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['本金充裕'], duties=DutyFlags(),
        notes='条件免费刷 50/10/3 经节点桥发放;instant_gold=26 选卡当场'),
    '本金充裕+': EffectSpec(
        id='301002', name='本金充裕+', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['本金充裕+'], duties=DutyFlags(),
        notes='条件腿与本金充裕逐字同文(50/10/3);加强值=instant_gold 45'),
}


def _validate_strategy_effects() -> None:
    """STRATEGY_EFFECTS 构建校验(import 即炸,防版本更新静默失联):

    ① 孤儿键:name 必须在 base 注册表;② id 双匹配:spec.id 必须等于 plaza id
    (改名且 id 仍在的漂移也炸);③ payload↔category 一致性。
    """
    for spec in STRATEGY_EFFECTS.values():
        base = INVESTMENT_STRATEGIES.get(spec.name)
        if base is None:
            raise ValueError(f"STRATEGY_EFFECTS 孤儿键(base 无此卡):{spec.name!r}")
        if base.source != f"plaza:{spec.id}":
            raise ValueError(
                f"STRATEGY_EFFECTS id 漂移:{spec.name!r} spec.id={spec.id} base={base.source}")
        if spec.category in (EffectKind.ECONOMY, EffectKind.STATE):
            ok = isinstance(spec.payload, EconomyEffect)
        elif spec.category == EffectKind.BATTLEFIELD:
            ok = isinstance(spec.payload, BattlefieldEffect)
        else:
            ok = isinstance(spec.payload, UnitBuffRef)
        if not ok:
            raise ValueError(
                f"STRATEGY_EFFECTS payload↔category 不一致:{spec.name!r} "
                f"category={spec.category} payload={type(spec.payload).__name__}")
        if spec.pending and not spec.notes:
            raise ValueError(f"STRATEGY_EFFECTS pending 条目必须写保守支 notes:{spec.name!r}")


# ===== curated overlay:环境分类 + 阵营绑定(手维护)=====
# 表值大多可由名字派生:类别 = 名字的类别后缀(概念股/邀请/契约)本身;阵营 = 名字去类别后缀。
# 真正的手维护信息只有例外条与不可派生名单;派生结果在构建期与逐位对拍基准比对
# (派生化零行为变化,决策与逐位对拍记录见 git 历史)。
_ENV_SUFFIX_DERIVED_NAMES: tuple[str, ...] = (
    # 概念股 15
    '追击概念股', '击破概念股', '群攻概念股', '能量概念股', '燃血概念股', '减益概念股',
    '战技点概念股', '仙舟概念股', '贝洛伯格概念股', '狼狩概念股', '星间旅人概念股',
    '银河学者概念股', '列车同行概念股', '昼之半神概念股', '夜之半神概念股',
    # 邀请 20
    '仙舟邀请', '贝洛伯格邀请', '狼狩邀请', '盛会之星邀请', '星间旅人邀请', '银河学者邀请',
    '列车同行邀请', '昼之半神邀请', '夜之半神邀请', '追击邀请', '击破邀请', '群攻邀请',
    '能量邀请', '燃血邀请', '减益邀请', '持续伤害邀请', '量子同频邀请', '战技点邀请',
    '欢愉邀请', '命运圣杯邀请',
    # 契约 7(阵营绑定 = 获赠该阵营角色,ADR-0151 补)
    '星核猎手契约', '战技点契约', '公司契约', '持续伤害契约', '量子同频契约', '欢愉契约',
    '命运圣杯契约',
)

# 不可派生环境的手写例外(带溯源;类别值不属三类后缀)
_ENV_CATEGORY_EXCEPTIONS: dict[str, str] = {
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

# 阵营绑定例外:名字推不出阵营(带用户确认注)
_ENV_FACTION_EXCEPTIONS: dict[str, str] = {
    '特邀专家:加拉赫': '击破',  # 加拉赫=击破角色(plaza traits 盛会之星/击破/治疗)+击破档位给钻头(用户确认)
}


def _derive_env_tables() -> tuple[dict[str, str], dict[str, str]]:
    """由 _ENV_SUFFIX_DERIVED_NAMES + 例外表构建 ENV_CATEGORY/ENV_FACTION。

    名字既不在三类后缀派生范围又无例外条 → KeyError(import 即炸,
    防新增环境登记时静默漏建)。"""
    cat: dict[str, str] = dict(_ENV_CATEGORY_EXCEPTIONS)
    fac: dict[str, str] = dict(_ENV_FACTION_EXCEPTIONS)
    for n in _ENV_SUFFIX_DERIVED_NAMES:
        for suf in ('概念股', '邀请', '契约'):
            if n.endswith(suf) and len(n) > len(suf):
                cat[n] = suf
                fac[n] = n[:-len(suf)]
                break
        else:
            raise KeyError(f'环境名字不可派生且无例外条目:{n!r}')
    return cat, fac


ENV_CATEGORY, ENV_FACTION = _derive_env_tables()


# ===== 补遗:plaza 不收的条目(手维护)=====
_MANUAL_EXTRAS: list[InvestmentStrategy] = [
    # 与「追击星徽套组」(id 320101,PLAZA_AUGMENTS)同效果,plaza 只收一张;米游社图鉴收两张(content 6302)
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
_validate_strategy_effects()


# ===== 派生:ENV_FACTION_MAP(投资环境 → 加成阵营;从 INVESTMENT_ENVS 派生,单一真相源)=====
# ===== OCR 分隔符归一(查找边界单一源;AGENTS.md「OCR 文本匹配与修复」②无歧义形变先规范化)=====
# 实机缺陷链(run_20260826_004527):OCR 把间隔号 `·`(U+00B7)误读为圆点 `•`(U+2022)——
# cw_screen_invest_strategy L216 告警 `'全都要•彩'` 注册表 miss → 原始 OCR 名 append 进
# session.active_strategies → cw_economy 按名聚合经济效果精确查 miss → **策略经济效果被
# 静默丢弃**(真金影响);cw_events 品质查同样先吃 miss。
# 先例:cw_chars_data L5「规范名:• 已统一为·」(数据层手改);本函数是查找层归一
# (注册表数据不动,原采集路径保留原始 OCR 名不改——原始证据不碰;采集行
# 已随 invest_cards 流写入端退役删除,归一口径照旧辖查表面)。
# 无歧义性已量化(2026-08-26):INVESTMENT_STRATEGIES(335)/INVESTMENT_ENVS(83)中
# 含 `·` 的条目 33+1(如 全都要·彩/采购专员·彩/银·金·彩),含 bullet 族字符
# (•/‧/∙/・)的正规名 **0 条** → 归一不会撞任何真名。
_INVEST_SEP_CANON = '·'          # U+00B7 间隔号(注册表规范分隔符)
_INVEST_SEP_VARIANTS = (         # OCR 误读形变族 → 一律归一到 U+00B7
    '•',   # U+2022 bullet(实机日志实锤)
    '‧',   # U+2027 hyphenation point
    '∙',   # U+2219 bullet operator
    '・',  # U+30FB 片假名中点
)


def normalize_invest_name(name: str) -> str:
    """投资策略/环境名 OCR 形变归一(仅无歧义分隔符映射,不碰其它语义符号)。

    所有按名查找注册表的入口(get_strategy/get_env/economy_effect_of/
    pick_value_of/is_known_env/env_faction)在查找前先归一入参——消费点统一受益,
    不逐 call site 改;写入端(采集/telemetry/session 存量名)保持原样。
    """
    for v in _INVEST_SEP_VARIANTS:
        if v in name:
            name = name.replace(v, _INVEST_SEP_CANON)
    return name


def refresh_invest_active(state) -> bool:
    """淘金客族刷新经济投资姿态谓词(单一址;效果规格姿态面)。

    判据:任一持有投资策略的可数值化经济效果带刷新增益通道
    (免费刷新/每刷经验——淘金客/加油站/搜打撤族,与 operations.
    buy_cards 免费刷新采证钩子同族判据)。消费面(ADR-0465 预算收权):
    ① ``economy_cycle.schedule_upgrade``——升级通道退役(sim 注入臂实证:
    LevelUp 退役是刷驱姿态行为的主驱动,预算式仅是语义显式化);
    ② ``ev.levelup_ev_basis``——升级授权链同步关闭(含人口位臂,
    与 sim 注入臂的「LevelUp 全抑制」同口径;等级回落预期带
    见批 3 A/B 验证协议 §4 出口 9)。
    """
    for name in (getattr(state, 'active_strategies', None) or ()):
        eff = STRATEGY_ECONOMY.get(normalize_invest_name(name))
        if eff is not None and (eff.free_refresh_per_node > 0
                                or eff.xp_per_refresh > 0):
            return True
    return False


def env_faction(env_name: str) -> str:
    """投资环境加成的阵营(概念股/邀请的 faction;无则 "")。"""
    e = INVESTMENT_ENVS.get(normalize_invest_name(env_name))
    return e.faction if e is not None else ""


def envs_boosting_faction(faction: str) -> list[str]:
    """加成某阵营的全部投资环境名(概念股 + 邀请)。"""
    return [name for name, e in INVESTMENT_ENVS.items() if e.faction == faction]


def get_env(name: str) -> InvestmentEnv | None:
    """按规范名取 InvestmentEnv;无则 None(入参先经 normalize_invest_name 归一分隔符形变)。"""
    return INVESTMENT_ENVS.get(normalize_invest_name(name))


def is_known_env(name: str) -> bool:
    """投资环境名是否在注册表内(识别完整性信号;OCR 命中注册表外的名字 → 数据缺口,应 log warn)。

    用于 cw_screen_invest_env 把「未建模环境」从静默中性 fallback 变成可见信号(防假绿,
    见 od-dev-gameplay-automation 完成判据反馈)。注册表外的名字可能是:① 赛季新增未收录;
    ② OCR 误识;③ 锁定未命名环境(数据银行 ??? 无法收录)。
    """
    return normalize_invest_name(name) in INVESTMENT_ENVS


def economy_effect_of(name: str) -> EconomyEffect:
    """单策略经济效果(无/未注册 → 全 0 EconomyEffect;ADR-0131)。

    入参先归一(normalize_invest_name)——session.active_strategies 里的存量 OCR 原始名
    (如 `全都要•彩`)也走此入口,归一后经济效果不再静默丢(run_20260826_004527 缺陷链)。
    """
    s = INVESTMENT_STRATEGIES.get(normalize_invest_name(name))
    return s.economy if (s is not None and s.economy is not None) else EconomyEffect()


def aggregate_economy(strategy_names: list[str]) -> EconomyEffect:
    """聚合多策略经济效果(ADR-0131):加法字段求和;interest_cap_override 取**最大**(更宽上限赢,
    买断制 0 单独持有时生效 —— 与其它利息策略并持时游戏取宽值,保守建模取 max 非 min);
    win_reward_mult 取**最大**(不叠乘)。

    五族枚举补全(分型登记形态;原 design_economy §E6 已删档,取回口径=
    ADR-0644;前置缺陷 R83-1/R85-3):
    interest_flat_per_node / gold_at_node 族 / gold_at_level 族 /
    xp_click_discount_from_level 族此前在重建枚举中缺席,经 cw_economy
    聚合消费链静默丢值。分型语义=**数值字段加法求和 + 触发配对字段守卫
    min 并宽**(哨兵 0,最早触发位代表聚合时点)。边界:标量载体对
    「多条目不同触发位」有损(两笔不同等级/时点的触发被折叠到最早位)——
    精确多条目消费暂无独立载体(逐策略消费视图未建),需要时先建再依赖。
    聚合语义机器可读单一源 =
    测试位分型表(test_cw_economy_aggregate_typing,§E6 裁决:代码即载体)。
    """
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
            # 修复项12 新字段:血本币/池改写取并持更宽者(唯一持有时即生效,同 cap 取 max 精神);
            # 免刷概率按补集合成(1−∏(1−ci),多张概率事件叠加口径)
            xp_buy_hp_cost=eff.xp_buy_hp_cost or e.xp_buy_hp_cost,
            refresh_shop_rewrite_every_3cost=(
                min(eff.refresh_shop_rewrite_every_3cost, e.refresh_shop_rewrite_every_3cost)
                if (eff.refresh_shop_rewrite_every_3cost and e.refresh_shop_rewrite_every_3cost)
                else (eff.refresh_shop_rewrite_every_3cost or e.refresh_shop_rewrite_every_3cost)),
            refresh_free_chance=1.0 - (1.0 - eff.refresh_free_chance) * (1.0 - e.refresh_free_chance),
            # —— 五族枚举补全(R83-1/R85-3;分型=数值求和 + 触发位守卫 min 并宽,
            # 哨兵 0;语义与边界见函数 docstring)——
            interest_flat_per_node=eff.interest_flat_per_node + e.interest_flat_per_node,
            gold_at_node=eff.gold_at_node + e.gold_at_node,
            gold_at_node_offset=(
                min(eff.gold_at_node_offset, e.gold_at_node_offset)
                if (eff.gold_at_node_offset and e.gold_at_node_offset)
                else (eff.gold_at_node_offset or e.gold_at_node_offset)),
            gold_at_level=eff.gold_at_level + e.gold_at_level,
            gold_at_level_target=(
                min(eff.gold_at_level_target, e.gold_at_level_target)
                if (eff.gold_at_level_target and e.gold_at_level_target)
                else (eff.gold_at_level_target or e.gold_at_level_target)),
            xp_click_discount_from_level=(
                eff.xp_click_discount_from_level + e.xp_click_discount_from_level),
            xp_click_discount_from_level_at=(
                min(eff.xp_click_discount_from_level_at, e.xp_click_discount_from_level_at)
                if (eff.xp_click_discount_from_level_at and e.xp_click_discount_from_level_at)
                else (eff.xp_click_discount_from_level_at or e.xp_click_discount_from_level_at)),
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
_STRATEGY_BINDINGS_EXPLICIT: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    # —— 星徽单件(金):阵营星徽 + 阵营 key 角色 ——
    # (星徽套组(棱彩)条目已派生化:由本段单件 + 名字规则派生,见 _derive_megastar_set_bindings)
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


def _derive_megastar_set_bindings(explicit: dict[str, tuple[frozenset[str], frozenset[str]]]
                                  ) -> dict[str, tuple[frozenset[str], frozenset[str]]]:
    """星徽套组条目由星徽单件条目 + 名字规则派生(构建期,零手维护):
    'X星徽套组'/'X星徽套组(二)' → explicit['X星徽'](逐位共享同一绑定元组)。

    套组卡名单取自注册表(键以'星徽套组'结尾者);对应单件未建模 →
    ValueError(import 即炸,防新套组卡静默无绑定)。派生结果与改前
    手写套组表逐位对拍一致(对拍记录见 git 历史)。
    """
    out: dict[str, tuple[frozenset[str], frozenset[str]]] = {}
    for name in INVESTMENT_STRATEGIES:
        if name.endswith('星徽套组(二)'):
            single = name[:-len('星徽套组(二)')] + '星徽'
        elif name.endswith('星徽套组'):
            single = name[:-len('星徽套组')] + '星徽'
        else:
            continue
        bind = explicit.get(single)
        if bind is None:
            raise ValueError(f"星徽套组无对应单件建模:{name!r}(缺 {single!r})")
        out[name] = bind
    return out


STRATEGY_BINDINGS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    **_derive_megastar_set_bindings(_STRATEGY_BINDINGS_EXPLICIT),
    **_STRATEGY_BINDINGS_EXPLICIT,
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
    """按规范名取 InvestmentStrategy;无则 None(注册表已全量 335,miss = OCR 形变,走 pick_value_of 的 LCS;
    入参先经 normalize_invest_name 归一分隔符形变,如 `全都要•彩`→`全都要·彩`,run_20260826_004527)。"""
    return INVESTMENT_STRATEGIES.get(normalize_invest_name(name))


def blood_xp_mode(session) -> tuple[str, int] | None:
    """血本位 XP 购买模式解析(返回 (卡名, 每击血价);无 active 血本位卡 → None=金本位)。

    单一源 = 注册表 STRATEGY_ECONOMY.xp_buy_hp_cost 派生(先例 =
    prep_actions.record_hp_pay_event 的 mode 判定;[40]② 血闸与遥测写点
    经本助手同源消费,ADR-0578)。多卡命中取 active_strategies 序首个
    (现版本游戏仅『奋斗协议』单卡在册;新血本位卡落地零改动)。
    入参先经 get_strategy 归一(session 存量 OCR 原始名不静默 miss)。
    """
    for name in getattr(session, 'active_strategies', None) or []:
        s = get_strategy(name)
        if (s is not None and s.economy is not None
                and s.economy.xp_buy_hp_cost):
            return name, int(s.economy.xp_buy_hp_cost)
    return None

# ===== ADR-0143 选卡价值基准分(全量评估表派生)=====
# 评估口径:value_class 七分类 + quantizable 三档 + pick_priority 0-100(读 effect 原文逐条判定;
# 无上下文基准分,comp 匹配/HP 分档在 decide_event 消费侧调)。注册表 = plaza base 335,
# 键经 canon 归一对齐(ADR-0150)。
# **知识判据定序器声明(ADR-0524,16 号稿 §1.1)**:本表分值来自玩法研究/comp 知识
# (ADR-0143 评估口径),非数学判据——形态 = 定序分:仅在本表(335 条策略)内选项间
# 排大小有效;禁作为基数与其它分值族(comp-hit/augment/planner 等)做加减语义扩展。
# 跨族交互仅保留 decide_event 的 max() 覆盖结构,禁新增「叠加进其它面判据」的消费点。
# **层级归属声明(用户裁定:保留 kernel)**:本表与下文 ENV_PICK_VALUE/ENV_FACTION_MATCH_FLOOR
# 及其消费核 decide_event,承载的是**内置默认策略器(mandate_v1 → CwFlowStrategy.decide_invest
# 委托)的评估观点**,不是框架中立事实;第三方策略插件自带 decide_invest 实现时不消费本表。
# 保留在 kernel = 延续判据单源现状(sim/回放经 strat.decide_invest 同链消费),语义以本声明为准。
# 立项挂账:升级为台账价值判据(ΔP̂ 完成概率增量参数化)归事件面命题批(08 E1/E2)。
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

# (事件面经验加减分族已退役 2026-09-04,「未证即退役」裁定,保守缺省 0:
# - SURVIVAL_PICKS(HP<40 生存类策略集,decide_event 低血 +15 钩子);
# - EQUIP_FLOW_PICKS(P2 断崖装备流策略集,decide_event plane≥2 +25 钩子,
#   11 局实锤经验拟合——辖域与幅度双未证,重立须按板面装备存量观测参数化。)


def resolve_strategy_canonical(name: str) -> str | None:
    """候选名 → 投资策略注册表规范名(归一 + LCS 兜底;ADR-0578)。

    解析逻辑与 pick_value_of 原 LCS 路径逐字同源(阈值 0.6 + |Δlen|≤3,
    评审建议6:防未来新增短名/长名与现有卡高 LCS 借分;env 名的跨表污染
    由 cw_events 守卫另行拦截,此处只管策略表内部)。消费面:pick_value_of
    (评估分)与 decide_event 候选级血本位分类(评估表未命中的形变名也要
    能分类,[40]① 排除支辖域)。
    """
    name = normalize_invest_name(name)
    if name in INVESTMENT_STRATEGIES:
        return name
    from one_dragon.utils.str_utils import find_best_match_by_lcs
    names = list(INVESTMENT_STRATEGIES)
    idx = find_best_match_by_lcs(name, names, lcs_percent_threshold=0.6)
    if idx is not None and abs(len(names[idx]) - len(name)) <= 3:
        return names[idx]
    return None


def pick_value_of(name: str) -> int | None:
    """选卡价值基准分(ADR-0143)。精确名优先;OCR 形变走 LCS 兜底
    (解析单一源 = ``resolve_strategy_canonical``);未评估(codex 新条目/
    完全未知)→ None(回落品质先验)。"""
    canonical = resolve_strategy_canonical(name)
    if canonical is None:
        return None
    v = INVESTMENT_STRATEGIES[canonical].pick_value
    return v if v > 0 else None


# ===== ADR-0144 环境选卡价值基准分(83 条全量评估表派生)=====
# 环境与策略结构倒挂(评估实证,ADR-0144):synergy 主导 47/83(阵营定向);无品质分级(全 '-')。
# 经济类计数无评估口径持久出处(ADR-0620 §3),分类表口径见 ENV_CATEGORY(经济 15/83),两口径禁互替。
# 量化断层:yes-direct 仅 1 条(蓝海)—— 环境效果全是整局规则(费率覆写/分期/重复触发),EconomyEffect
# 现有字段结构性装不下(EnvEconomyEffect 扩字段待后续);接线防一次性错装点名 6 条见 ADR-0144 决策 3。
# **知识判据定序器声明(ADR-0524,16 号稿 §1.2)**:同 PICK_VALUE——分值仅在本表
# (83 条环境)内选项间定序有效,禁作为基数与其它分值族加减;跨族仅 max() 覆盖。
# 经济效果建模缺口(EnvEconomyEffect 扩字段)是升级为台账价值判据的真实卡点,
# 随立项挂账归事件面命题批(08 E1/E2)。
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

# 阵营定向类 comp 匹配定序门(ADR-0524 定形,16 号稿 §1.3):三档值 = category 间
# 定序档位(邀请 70 < 契约 72 < 概念股 78,评估实证序),非条件白名单的基数下限。
# 承重语义 = 「faction ∩ target_comp.factions ⇒ 提到本 category 档位,压过全体 env
# 裸分(上界 72)」;禁读作基数参与跨族加减。
ENV_FACTION_MATCH_FLOOR: dict[str, float] = {'概念股': 78.0, '邀请': 70.0, '契约': 72.0}
# (旧 ENV_SURVIVAL_BONUS = {白银时代 15, 敌后破坏 15, 人身意外险 10} 已退役
# 2026-09-04,「未证即退役」裁定:低血环境钩子保守缺省 0,消费分支同批删除。)


# ===== 环境经济通道注册表(2026-09-12 invest-env 迭代,design.md §2.2.2;白名单制)=====
# A 类精确四条 + B 类两条(长线利好/二手市场)+ C 类两条(经济过热/经济严重
# 过热),design §2.2.1 通道分类全量。表外环境 economy 恒 None,禁从效果原文
# 自动猜装(ADR-0144 决策 3 六条防错装对账 = _validate_env_economy);
# 轮岗/人才下沉无通道可装 → 「待建模」显式在册(cw_env_economy.
# ENV_ECONOMY_PENDING_MODELING,区别于漏登记,design §2.2.4)。
# B/C 通道的估算参数(概率/期望/增益)在 cw_env_economy.ENV_ECONOMY_ESTIMATES,
# 本表只落游戏定义结构值。
#: C 类通道在场哨兵(字段语义见 EnvEconomyEffect.reward_node_bonus;每奖励
#: 节点期望增益真值+CI 在估算注册表,按环境变体分键,非本字段)
_REWARD_NODE_BONUS_MARK: float = 1.0
ENV_ECONOMY: dict[str, EnvEconomyEffect] = {
    # 每位面开局 (6,8,12) 金晶矿(id 103 原文直读;晶矿自动开启假设见 schema 注)
    '增发货币': EnvEconomyEffect(gold_per_plane_start=(6, 8, 12)),
    # 开局额外 +6 金(id 113;随机环境期望不计,design §2.6 取舍)
    '蓝海': EnvEconomyEffect(gold_instant=6),
    # 升 8 级后 3 节点各 +12XP(id 138)= 36XP;×1:1 折金等价
    # (cw_env_economy.XP_GOLD_RATE 用户裁定暂定;「升 8 必然发生」假设在册)
    '成功经验': EnvEconomyEffect(xp_after_level=(8, 3, 12)),
    # 每取一张策略 +2×已持有数(id 147);3-5 节点额外策略不计(策略域价值)
    '策略大师': EnvEconomyEffect(gold_per_strategy_coef=2),
    # 花费金币刷新 30 次后 +20 金、之后刷价 2→1(id 120 原文直读;基价 2 =
    # cw_state.REFRESH_COST_BASE 游戏定义)。付费阈值(总数阈值 = 二手市场行),
    # 估值 = P(达 30)×[20 + (2−1)×E(后继刷新)],design §2.2.1 B 类公式
    '长线利好': EnvEconomyEffect(gold_after_refreshes=(30, 20),
                                 refresh_cost_after=(30, 1)),
    # 商店刷新 20 次后 +30 金(id 106);【员工投影仪】件不入经济(装备资产,
    # design §2.2.1 B 类行)。总刷新阈值,估值 = P(达 20)×30
    '二手市场': EnvEconomyEffect(gold_after_refreshes=(20, 30)),
    # 全部奖励节点替换为(超级)次元扑满、掉落(超)多战利品(id 105/119 原文
    # 直读;效果无数值,增益真值+CI 在估算注册表按变体分键,当前零有效估计
    # → 通道 fail-closed 裸分维持,数据批口径见 details/data-batch-estimates.md)
    '经济过热': EnvEconomyEffect(reward_node_bonus=_REWARD_NODE_BONUS_MARK),
    '经济严重过热': EnvEconomyEffect(reward_node_bonus=_REWARD_NODE_BONUS_MARK),
}


def _validate_env_economy() -> None:
    """ENV_ECONOMY 构建校验(import 即炸):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(沿 ENV_PICK_VALUE 先例,防版本更新
    改名/移除后静默失联);② **ADR-0144 决策 3 六条防一次性错装逐条对账**——
    点名六条(增发货币/成功经验/二手市场/长线利好/策略大师/劳务派遣合同)的
    效果全是分期/条件/触发形态,禁装成 gold_instant 单通道(一次性错装);
    劳务派遣合同(出售/合成触发金)现版本无对应通道字段,登记即错装 → 直接
    拒绝(专属字段建模后再收此闸);③ 挂载一致性:replace 后
    INVESTMENT_ENVS[name].economy 与表内实例同一对象(防后续构建段重挂漂移)。
    """
    orphans = [n for n in ENV_ECONOMY if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(f"ENV_ECONOMY 孤儿键(base 无此环境?):{sorted(orphans)}")
    _anti_instant = ('增发货币', '成功经验', '二手市场', '长线利好', '策略大师')
    for _n, _eff in ENV_ECONOMY.items():
        if _n in _anti_instant and _eff.gold_instant != 0:
            raise ValueError(
                f"ENV_ECONOMY 防错装(ADR-0144 决策 3):{_n!r} 效果为分期/条件形态,"
                f"禁装 gold_instant={_eff.gold_instant}(一次性错装)")
    if '劳务派遣合同' in ENV_ECONOMY:
        raise ValueError(
            "ENV_ECONOMY 防错装(ADR-0144 决策 3):劳务派遣合同(出售/合成触发金)"
            "无对应通道字段,禁以现有字段近似装表(专属字段建模后再收)")
    for _n, _eff in ENV_ECONOMY.items():
        if INVESTMENT_ENVS[_n].economy is not _eff:
            raise ValueError(f"ENV_ECONOMY 挂载不一致:{_n!r} economy 未挂载或实例漂移")


for _n, _eff in ENV_ECONOMY.items():
    INVESTMENT_ENVS[_n] = replace(INVESTMENT_ENVS[_n], economy=_eff)
_validate_env_economy()


# ===== 环境送卡发放注册表(2026-09-12 invest-env 迭代;details/env-value-models.md §2.1)=====
# 送卡型环境(契约 ×7 + 特邀专家 ×4)的具名发放登记,白名单制(表外环境一律无条目,
# 禁从效果原文自动猜装,ENV_ECONOMY 同款纪律)。档位机器 = cw_comps.gift_hit_tier
# (消费契约见其 docstring);档位是定序实现常数非金流期望(ADR-0524 定序/基数分账),
# 不经经济入口,消费位 = cw_events env 分支独立 max() 支(3.5 接线)。
# 逐条语义盘点与分档落点表 = details/env-value-models.md §2.1.1/§2.1.2;锁 = 测试仓
# test_cw_env_gift.py(G1 分档表/G2 失格门构造/G8 互斥断言半边)。
ENV_GIFTS: dict[str, GiftGrant] = {
    # 效果原文对账 id(cw_invest_data.PLAZA_PORTALS):量子同频 125/公司 126/持续伤害 127/
    # 战技点 128/星核猎手 129/欢愉 1201/命运圣杯 1202/特邀专家 141/142/143/148
    '量子同频契约': GiftGrant(chars_conditional=(
        ('符玄', '花火和缇宝升星时随机获得【符玄】或【希儿】'),
        ('希儿', '花火和缇宝升星时随机获得【符玄】或【希儿】'),
    )),
    '公司契约': GiftGrant(
        chars_immediate=('翡翠', '砂金'),
        chars_conditional=(('托帕&账账', '累计获得40利息后'),),
    ),
    '持续伤害契约': GiftGrant(
        chars_immediate=('椒丘', '卡芙卡'),
        chars_conditional=(('黑天鹅', '不同持续伤害状态计数达到180'),),
    ),
    '战技点契约': GiftGrant(
        chars_immediate=('丹恒·饮月', '花火'),
        chars_conditional=(('火花',
                            '打开20个晶矿后(并附1个随机战技点羁绊角色,不可具名不入全集机;'
                            '之后每打开10个晶矿可重复)'),),
    ),
    '星核猎手契约': GiftGrant(
        chars_immediate=('卡芙卡',),
        chars_conditional=(('流萤',
                            '刃或千冶·刃/卡芙卡/银狼LV.999或银狼同战一役后获得,'
                            '2个节点后才能上场'),),
    ),
    '欢愉契约': GiftGrant(
        chars_immediate=('银狼LV.999',),
        chars_conditional=(
            ('火花', '触发独立羁绊【头号玩家】选项时随机获得'),
            ('开拓者·欢愉', '触发独立羁绊【头号玩家】选项时随机获得'),
        ),
    ),
    '命运圣杯契约': GiftGrant(
        chars_immediate=('远坂凛', '吉尔伽美什'),
        chars_conditional=(('Archer', '完成两次圣杯试炼后'),),
    ),
    # 特邀专家 4 条 = 顾问入商店语义(advisor=True,付费购买期权);附加效果(停云
    # 终结技增益/加拉赫按击破档给钻头/桑博节点礼盒)异质不入估值,仅占位登记
    # (详设 §2.1.1 注;桑博礼盒无数值,invest_effects.md §5 同类裁定同源)
    '特邀专家:停云': GiftGrant(chars_immediate=('停云',), advisor=True),
    '特邀专家:加拉赫': GiftGrant(chars_immediate=('加拉赫',), advisor=True),
    '特邀专家:银狼': GiftGrant(chars_conditional=(
        ('银狼', '首次获得【银狼LV.999】时,顾问入商店'),
    ), advisor=True),
    '特邀专家:桑博': GiftGrant(chars_immediate=('桑博',), advisor=True),
}

# 送卡档位 floor 常数(定序实现常数;ENV_FACTION_MATCH_FLOOR 同族先例,ADR-0524):
# 值只承载档间定序与对既有域带的位次,禁读基数参与跨族加减。锚点推导(顺序即设计
# 内容,值是实现载体,details/env-value-models.md §2.1.2 表):
GIFT_FLOOR_CORE: int = 66           # > 58(契约裸分上界,战技点契约)∧ < 70(最低阵营
                                    #   floor,邀请)∧ ≤ 72(env 裸分上界,彩虹时代)
GIFT_FLOOR_SHARED: int = 60         # < CORE ∧ > 58(同上锚);只作演化结构位(当前无落地条目)
GIFT_FLOOR_ADVISOR_CORE: int = 54   # < SHARED(付费期权 < 白得,同档位类)∧ > 52(结构可比
                                    #   簇上界,过剩经费/劳务派遣合同)∧ < 55(头彩:单取卡
                                    #   品质升级的结构档让位其知识评估分)
# advisor shared/transition、条件降档后非 core/shared 无 floor(维持裸分;特邀专家:
# 停云/加拉赫/银狼全落此,floor 表行 4)——无常数,消费支按 gift_hit_tier 消费契约分流。


def _validate_env_gifts() -> None:
    """ENV_GIFTS 构建校验(import 即炸;details/env-value-models.md §2.1.3):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(沿 ENV_ECONOMY 先例,防版本更新改名/
    移除后静默失联);② 角色名漂移:发放角色(即时∪条件)必须在 CHARACTER_ROSTER
    (版本漂移不静默,与孤儿键同批校验);③ 空发放集条目拒绝(既无即时又无条件
    = 数据残缺,档位机器恒判 off,会把登记笔误放大成失格门误杀);④
    ``set(ENV_GIFTS) ∩ set(ENV_ECONOMY) = ∅``——单一环境只落一个估值结构,防
    双通道叠加(∩ ENV_POOL_REWRITE 半边由 3.6 品质改写建表时收全)。
    """
    orphans = [n for n in ENV_GIFTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(f"ENV_GIFTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _name, _grant in ENV_GIFTS.items():
        _drift = [c for c in (*_grant.chars_immediate,
                              *(c for c, _note in _grant.chars_conditional))
                  if c not in CHARACTER_ROSTER]
        if _drift:
            raise ValueError(
                f"ENV_GIFTS 角色名漂移({_name!r} 注册表无此人,版本改名?):{_drift}")
        if not _grant.chars_immediate and not _grant.chars_conditional:
            raise ValueError(f"ENV_GIFTS 空发放集:{_name!r} 既无即时又无条件发放,数据残缺")
    _overlap = set(ENV_GIFTS) & set(ENV_ECONOMY)
    if _overlap:
        raise ValueError(
            f"ENV_GIFTS ∩ ENV_ECONOMY 非空(单一环境只落一个估值结构):{sorted(_overlap)}")


_validate_env_gifts()


# ===== 环境品质改写注册表(2026-09-12 invest-env 迭代 3.6;
# details/env-value-models.md §2.2;白名单制)=====
# 品质改写型环境(时代 ×3 + 头彩/尾彩 + 银·金·彩 + 联席决策,恰 7 条)的池改写
# 事实登记。表外环境一律无条目,禁从效果原文自动猜装(ENV_ECONOMY/ENV_GIFTS
# 同款纪律)。两型两层拆分(详设 §2.2.2):层 E(基数,改写后取卡金流期望抬升
# ΔV)经 env_economy_value 单一入口分派(cw_env_economy._pool_rewrite_value),
# 当前态恒 fail-closed——受限通道 μ_E 不随品质单调(银 3.31 > 金 2.42 实测),
# 直接入域带会产出「白银时代>黄金时代」噪声序;层 E 转正准入门(全通道重算
# + 序一致性检验,详设 §2.2.2)经数据批判定未过,维持 fail-closed(判定依据
# = invest-env 迭代 layer-e-promotion-batch 详设,git 历史可溯);层 Q
# (定序残域,池内挑卡
# 与功能价值)= 环境裸分维持(ENV_PICK_VALUE 七条零改动,ADR-0144 知识评估
# 已对两半作过知识性净评),两层从不相加——max() 结构天然承载
# 「层 E 有值时以域带参与、无值时裸分兜底」(总纲 design.md §2.3)。
# 数量通道(联席额外三选一/银金彩刷新 +2)与 A 类策略大师同口径:策略域价值
# 不折金不进层 E,消费端零改动,字段只登记事实(详设 §2.2.4)。
# 锁 = 测试仓 test_cw_env_pool_rewrite.py(Q1-Q6)。
@dataclass(frozen=True)
class StrategyPoolRewrite:
    """投资环境的**策略池品质改写**结构(品质改写型估值;2026-09-12 invest-env
    迭代 3.6,details/env-value-models.md §2.2.5;与 EnvEconomyEffect/GiftGrant
    同属 InvestmentEnv 的估值 schema 家族,落点集中本段避免触碰已交付段)。

    字段语义(值全部 = cw_invest_data 效果原文直读;效果原文对账 id 见
    ENV_POOL_REWRITE 各条注释):
    - rewrite_quality: 改写目标品质('棱彩'/'金'/'银');空 = 非品质全改写型
      (银·金·彩为 offer 结构改写、联席决策为数量通道,无层 E 语义)
    - rewrite_picks: 被改写的取卡序号,**坐标系 = 本局投资策略取卡全局序,
      1 基**(头彩效果原文点名「第一个投资策略」/尾彩点名「第三个投资策略」
      → 固定取卡集基数 3 的序数承载,details/env-value-models.md §2.2.2;
      时代 = (1,2,3) 全改写);取值时机 = 注册表登记期常量(效果原文直读,
      非执行期现读)
    - offer_structure: offer 结构改写语义标记('silver_gold_prism_slots' =
      银·金·彩三槽按位面对应银/金/彩);注释性字段,层 E 公式不消费
    - extra_pick_refreshes: 策略取卡刷新次数增量(银·金·彩 +2,策略屏逐卡
      免费刷新计数,cw_node_obs.read_invest_refresh_counts('strategy') 通道;
      数量通道登记,§2.2.4,v1 无消费端)
    - extra_pick_node_range: 额外取卡发生的节点范围,**坐标系 = 本局全局节点
      序,1 基,含两端**(联席决策效果原文「2-6 节点」直读;数量通道登记,
      §2.2.4,v1 无消费端);None = 无额外取卡
    - difficulty_exempt: 敌人难度不随高品质策略提高(白银时代第二条效果;
      游戏【注·对拍】口径 = 白银 +0/黄金 +3/棱彩 +6 每拥有 1 个,
      docs/game/currency_war/research/economy.md 难度精确口径行——数值在册
      不折金,难度→收益需战力/胜率建模属宪法禁域 00_framework §1.1,§2.2.3)
    - pending_notes: 效果原文歧义挂账(单张改写型 offer 覆盖面歧义:三卡全改
      还是仅点名张;银·金·彩槽位-品质映射语义)——pending 条目必填
      (_validate_env_pool_rewrite 构建闸,_validate_strategy_effects 先例
      同款)
    """
    rewrite_quality: str = ''
    rewrite_picks: tuple[int, ...] = ()
    offer_structure: str = ''
    extra_pick_refreshes: int = 0
    extra_pick_node_range: tuple[int, int] | None = None
    difficulty_exempt: bool = False
    pending_notes: str = ''


ENV_POOL_REWRITE: dict[str, StrategyPoolRewrite] = {
    # 效果原文对账 id(cw_invest_data.PLAZA_PORTALS):彩虹 110/黄金 111/白银 112/
    # 头彩 123/尾彩 124/银·金·彩 135/联席决策 122
    '彩虹时代': StrategyPoolRewrite(rewrite_quality='棱彩', rewrite_picks=(1, 2, 3)),
    '黄金时代': StrategyPoolRewrite(rewrite_quality='金', rewrite_picks=(1, 2, 3)),
    # 白银时代第二效果「敌人难度不会由于选择高品质投资策略而提高」=
    # difficulty_exempt 如实登记(§2.2.3 辖域声明:数值不折金,不产生分值)
    '白银时代': StrategyPoolRewrite(rewrite_quality='银', rewrite_picks=(1, 2, 3),
                                    difficulty_exempt=True),
    # 头彩/尾彩 offer 覆盖面歧义(三卡全棱彩还是仅首/尾卡棱彩,效果原文
    # 「第一个/第三个投资策略」直读按单张登记,实采定谳前保守)→ pending_notes 必填
    '头彩': StrategyPoolRewrite(
        rewrite_quality='棱彩', rewrite_picks=(1,),
        pending_notes='效果原文「第一个投资策略」为棱彩;三卡全棱彩还是仅首卡'
                      '棱彩歧义,按单张保守登记,实采挂账(详设 §2.2.1)'),
    '尾彩': StrategyPoolRewrite(
        rewrite_quality='棱彩', rewrite_picks=(3,),
        pending_notes='效果原文「第三个投资策略」为棱彩;三卡全棱彩还是仅尾卡'
                      '棱彩歧义,按单张保守登记,实采挂账(详设 §2.2.1)'),
    # 银·金·彩 = offer 结构改写(三选项品质按槽位)+ 刷新 +2;槽位-品质映射
    # 语义与「三品质各一」直觉不同(实测 offer 金重仓,详设 §2.2.2 π_offer
    # 读数),实采挂账 → pending_notes 必填
    '银·金·彩': StrategyPoolRewrite(
        offer_structure='silver_gold_prism_slots', extra_pick_refreshes=2,
        pending_notes='固定取卡节点三选项品质 = 银/金/彩按槽位;槽位-品质映射'
                      '语义实采挂账(实测 offer 金重仓非三品质各一,详设 §2.2.2)'),
    # 联席决策 = 数量通道(2-6 节点一次额外投资策略三选一);与 A 类策略大师
    # 「额外取卡不计」同口径,价值由裸分承载(§2.2.4)
    '联席决策': StrategyPoolRewrite(extra_pick_node_range=(2, 6)),
}


def _validate_env_pool_rewrite() -> None:
    """ENV_POOL_REWRITE 构建校验(import 即炸;details/env-value-models.md §2.2.5):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(沿 ENV_ECONOMY/ENV_GIFTS 先例,防版本
    更新改名/移除后静默失联);② 三注册表互斥收全:``set(ENV_POOL_REWRITE) ∩
    set(ENV_GIFTS) = ∅`` 且 ``∩ set(ENV_ECONOMY) = ∅``——集合交对称,本闸与
    _validate_env_gifts 已收的 ∩ENV_ECONOMY 半边合起来 = 三表两两互斥
    (单一环境只落一个估值结构,防双通道叠加;G8 半边声明的「∩ ENV_POOL_REWRITE
    由 3.6 建表时收全」即本闸,不动已交付函数体);③ 结构完备:改写目标品质与
    被改写取卡序要么齐备要么俱无(半残 = 登记笔误,层 E 公式不可算);④ pending
    必填:单张改写型(有点名取卡序但非全改写,offer 覆盖面歧义)或 offer 结构
    改写型(槽位语义歧义)必须写保守支 notes(_validate_strategy_effects
    「pending 条目必须写保守支 notes」先例同款)。
    """
    orphans = [n for n in ENV_POOL_REWRITE if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(f"ENV_POOL_REWRITE 孤儿键(base 无此环境?):{sorted(orphans)}")
    _overlap_gifts = set(ENV_POOL_REWRITE) & set(ENV_GIFTS)
    if _overlap_gifts:
        raise ValueError(
            f"ENV_POOL_REWRITE ∩ ENV_GIFTS 非空(单一环境只落一个估值结构):"
            f"{sorted(_overlap_gifts)}")
    _overlap_econ = set(ENV_POOL_REWRITE) & set(ENV_ECONOMY)
    if _overlap_econ:
        raise ValueError(
            f"ENV_POOL_REWRITE ∩ ENV_ECONOMY 非空(单一环境只落一个估值结构):"
            f"{sorted(_overlap_econ)}")
    for _name, _rw in ENV_POOL_REWRITE.items():
        if bool(_rw.rewrite_quality) != bool(_rw.rewrite_picks):
            raise ValueError(
                f"ENV_POOL_REWRITE 结构半残:{_name!r} rewrite_quality="
                f"{_rw.rewrite_quality!r} 与 rewrite_picks={_rw.rewrite_picks!r}"
                f"须同有同无(层 E 公式不可算)")
        _partial_rewrite = bool(_rw.rewrite_quality) and _rw.rewrite_picks != (1, 2, 3)
        if (_partial_rewrite or _rw.offer_structure) and not _rw.pending_notes:
            raise ValueError(
                f"ENV_POOL_REWRITE pending 条目必须写保守支 notes:{_name!r}"
                f"(offer 覆盖面/槽位语义歧义挂账)")


_validate_env_pool_rewrite()
