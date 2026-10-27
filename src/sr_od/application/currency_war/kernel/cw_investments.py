"""货币战争 投资策略 + 投资环境领域模型(meta 层,V4.4)。

**两层架构**:
- **base 事实层** = ``cw_invest_data.py``(``tools/cw/gen_plaza_invest.py`` 从米游社攻略广场
  官方 API 生成,勿手编):名字/品质/效果全文,数字 id 稳定主键,投资策略 334 + 投资环境 83
  官方全量(游戏内数据银行同口径,米游社百科 doc 的 19 条版本漂移缺口就此补齐)。
- **建模增量层** = 本文件手维护(API 给不了的人工建模):
  - ``STRATEGY_ECONOMY``(可数值化经济效果);
  - ``is_blood_economy``/``blood_xp_mode``(血本位判别与 XP 购买模式解析,
    [40]① 选择回避 / [40]② 血闸共享判据);
  - ``ENV_CATEGORY``/``ENV_FACTION``(环境 7 类分类 + 阵营绑定,ENV_FACTION_MAP 派生源);
  - ``_MANUAL_EXTRAS``(plaza 不收的补遗条目);
  - ``STRATEGY_GRANTS``(策略卡具名发放登记,机制事实留 kernel;「档→分」
    映射 = 策略层 gift_value,消费核 = ``strategies/impl/mandate_v1/
    invest_strategy.py``,正本 = strategy-docs/29_invest_strategy_screen.md);
  - ``env_faction_scope``/``strategy_faction_scope``(环境/策略的阵容指向集
    派生,零手抄登记;消费 = 投资选卡阵容冲突护栏,invest_strategy 冲突基准)。
  两屏选卡评序不在本文件(宪法五:衍生打分归策略层,正本 = strategy-docs
  28/29 号稿)。
- **合并层**:base × overlay → 注册表,构建时做孤儿校验(overlay 引用了 base 没有的键 →
  import 即炸,防版本更新后静默失联)。

**版本更新工作流**:重跑 ``uv run python tools/cw/gen_plaza_invest.py`` → 看 diff 报告
(新增/移除/改名/品质变)→ 修 overlay 孤儿键 → 完成。

**用途**:
- ``InvestmentEnv``(概念股/邀请/契约/时代/经济/规则/专家):**带 faction 字段** —— 概念股/
  邀请/命运圣杯契约对应哪个阵营是派生 ENV_FACTION_MAP 的单一真相源。
- ``InvestmentStrategy``(局内 3 选 1):策略层组件分评序(29 号稿)与用户转向轴(config strategy priority/forbid)的规范名来源。
- 键约定:canon 归一名(半角冒号/逗号、`·`、拉丁数字),与 OCR 精确匹配层一致;
  OCR 形变(全角标点/剎刹)走 ``resolve_strategy_canonical`` 的 LCS 兜底。

**为什么建模**(用户 2026-08-03):核心实体建正规 model 类 + 注册表(可查询/校验/派生),非散 dict。

⚠️ env_fit 策略影响目前只用「阵营亲和」一维(概念股/邀请/命运圣杯),其余类别(契约/时代/
经济/规则/专家)效果异质,待分类建模(阶段 3a)。版本依赖:赛季扩充会新增/调整。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, fields, replace

from sr_od.application.currency_war.data.cw_chars import (
    CHARACTER_ROSTER,
    CHARACTERS,
    chars_by_cost,
    chars_by_faction,
)
from sr_od.application.currency_war.data.cw_equipment_data import (
    EQUIPMENTS,
)
from sr_od.application.currency_war.data.cw_factions import (
    FACTIONS,
)
from sr_od.application.currency_war.data.cw_invest_data import (
    PLAZA_AUGMENTS,
    PLAZA_PORTALS,
)
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    BOARD_REWRITE_SELL_ALL,
    BOARD_REWRITE_UPGRADE_ALL,
    BattlefieldEffect,
    CounterKey,
    DurationKind,
    DutyFlags,
    EffectKind,
    EffectSpec,
    TriggerKind,
    UnitBuffRef,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    PLANE_NODE_TABLES,
)


@dataclass(frozen=True)
class InvestmentEnv:
    """投资环境(开局/固定节点整局增益)。"""
    name: str           # 规范名(如"昼之半神概念股")
    category: str       # "概念股"/"邀请"/"契约"/"时代"/"经济"/"规则"/"专家"
    effect: str         # 效果原文(官方 API 全文)
    faction: str = ""   # 对应阵营(概念股/邀请 boosts 的羁绊;ENV_FACTION_MAP 派生用;无则 "")
    source: str = ""    # 溯源(plaza:<id> 或 content_id)
    pick_value: int = 0  # (遗迹位,恒缺省 0:选卡评序迁策略层 invest_env 后无写端无消费,字段保留防 schema 破坏)
    economy: EnvEconomyEffect | None = None  # 整局经济通道(白名单制;ENV_ECONOMY 构建期 replace 挂载,表外恒 None)


@dataclass(frozen=True)
class EconomyEffect:
    """投资策略/环境的**可数值化经济效果**(用户 2026-08-15:效果要直接转经济模型)。

    只收能进策略层算账的效果(给金/免费刷新/利息/经验/连胜倍率);战力类(数值碾压/攻防一体等)
    不在此(走战力评估,不进经济)。全 0/None = 无经济效果。字段语义:
    - instant_gold: 选牌当场给金(一次性)
    - gold_per_node: 每次进入新节点给金
    - free_refresh_per_node: 每节点免费刷新次数(成本 0 的刷新)
    - free_refresh_burst: 一次性海量免费刷新(如高效决策 9999 次);限时窗口策略层不编排时机(执行层待办)
    - free_refresh_cond_gold_above/step/cap: 条件判定族三元组(本金充裕系=50/10/3)——每次进入
      新节点时,金 > above 每额外 step 金 +1 次免费刷新、至多 cap 次;发放经
      grant_effect_node_refresh_balance 桥(节点 tick 采样,金=gs.gold 现值评估)
    - refresh_surprise_every: 每 N 次刷新刷出 5 张同费卡(采购专员;稳定器,提高刷新期望)
    - gold_per_three_5cost: 每购买 3 个 5 费角色给金
    - interest_cap_override: 利利息档上限覆写(开源节流 9 档/利息上调 10 档/买断制 0)
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
    # —— v2 扩展(全量调研;仅 API 文本明说的数值)——
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
    # —— 合成/出售触发族(裁定;均为「正常成型路上
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
    """血本位突变判别([40]①「主动选择=回避」的候选判据)。

    判据 = 效果把 HP 写进经济循环的字段:购经验币种切换(xp_buy_hp_cost)
    ∨ HP↔金互换(hp_gold_swap)。补偿型字段(gold_per_20hp_lost/
    gold_per_hp_lost_now)不改支付币种,不入族;名字含「血」不可作判据
    (反例:鲜血阶梯 = 击杀增伤卡,effect 无 HP 经济字段)。当前族集 =
    {奋斗协议,不等价交换}——与 [40] 裁定原文点名完全一致;新血本位卡
    建模 EconomyEffect 对应字段即自动入族(零名单维护)。
    """
    if eff is None:
        return False
    return eff.xp_buy_hp_cost > 0 or eff.hp_gold_swap


# ===== 持续通道引擎判别(②类判据留驻 kernel 的划界依据 =
# proofs/p81-invest-refresh-dominance.md §7.2)=====

# 「引擎 vs 一次性」的界 = 效果原文持续/一次性**结构事实**(宪法五②类:
# 换一套策略实现,同一张卡的引擎/一次性判定不会不同),零幅度拍值。消费方
# = 策略层刷新判据的帧级顶级类(strategies/impl/mandate_v1/invest_strategy.
# py)与 op 层观测位;kernel 驻留依据 = P81 §7.2 依据一/三(判据线优先于
# 消费方定位;与 STRATEGY_BINDINGS 援 ENV_FACTION 先例同族对账)。

#: 引擎单字段通道:(字段,默认值)——非默认即通道存在;四族 = 利息(含
#: cap 覆写)/持续金流/刷新/经验。``interest_cap_override`` 默认 None,
#: 非 None 即覆写(0 也是有效覆写 = 息通道改写,如买断制 cap=0)。
_ENGINE_CHANNEL_SINGLE_FIELDS: tuple[tuple[str, float | None], ...] = (
    ('gold_per_node', 0), ('gold_per_boss_node', 0),
    ('gold_per_level_up', 0), ('gold_per_three_5cost', 0),
    ('gold_per_2star2cost_merge', 0), ('gold_per_3star_merge', 0),
    ('interest_flat_per_node', 0), ('interest_cap_override', None),
    ('win_reward_mult', 1.0), ('sell_price_mult', 1.0),
    ('free_refresh_per_node', 0), ('free_refresh_burst', 0),
    ('refresh_surprise_every', 0), ('refresh_per_compose', 0),
    ('refresh_free_chance', 0.0), ('refresh_shop_rewrite_every_3cost', 0),
    ('xp_per_refresh', 0), ('xp_per_node', 0), ('xp_buy_cost_discount', 0),
    ('xp_instant', 0),
)
#: 引擎配对字段通道:效果语义两半齐备才存在(「接下来 count 次每次
#: amount」/「level 起单击减金」)——任一半缺省 = 通道不存在。
_ENGINE_CHANNEL_PAIR_FIELDS: tuple[tuple[str, str], ...] = (
    ('gold_next_nodes_amount', 'gold_next_nodes_count'),
    ('xp_click_discount_from_level', 'xp_click_discount_from_level_at'),
)
#: 显式排除字段(判据 =「一次性/结构登记,不构成持续通道」的**显式负
#: 集合**,逐组带划界依据;与 strategy_economy 字段三分分类的交集说明:
#: 本桶跨其「计分/待建模/不计」三类——划分轴不同,这边答「是否持续
#: 通道」,那边答「现金通道怎么算」):
_ENGINE_CHANNEL_EXCLUDED_FIELDS: frozenset[str] = frozenset({
    # 一次性金族(当场/时点大额,无持续语义)
    'instant_gold', 'gold_at_node', 'gold_at_node_offset',
    'gold_at_level', 'gold_at_level_target',
    # 条件刷新三元组(本金充裕系):条件窗口内逐节点补刷,旧闭集裁决
    # 不入引擎族(非无条件持续通道),沿旧闭集原样划界
    'free_refresh_cond_gold_above', 'free_refresh_cond_gold_step',
    'free_refresh_cond_cap',
    # 补偿型(损血/上限损耗换算,不构成收入通道)
    'gold_per_20hp_lost', 'gold_per_hp_lost_now',
    'hp_max_loss_pct_of_loss', 'hp_max_loss_cap_pct',
    # 血本位族(另由 is_blood_economy 集合排除覆盖,不入引擎判定)
    'hp_gold_swap', 'xp_buy_hp_cost',
    # 难度/期权族(难度→价值需战力建模;远见品质改写系期权)
    'difficulty_delta', 'difficulty_per_streak', 'difficulty_node_types',
    'future_quality_upgrade', 'difficulty_inflation_exempt',
    # 负向结构登记(成本/加价,无正通道)
    'xp_click_surcharge_from_level', 'xp_click_surcharge_from_level_at',
})


def is_economy_engine(economy: EconomyEffect | None) -> bool:
    """持续通道引擎谓词(策略层刷新判据帧级顶级类的 kernel 判据源)。

    结构事实判据(存在性,非幅度):命中任意持续通道字段即真,字段值不
    参与任何定序。与血本位排除族零交集(两族字段不相交,对账声明见
    ``_ENGINE_CHANNEL_EXCLUDED_FIELDS`` 分组注)。新增 EconomyEffect 字段
    未显式落三分类 → :func:`_validate_engine_channel_closure` import 即炸
    (静默判「一次性」的治理缺口前置可见)。"""
    if economy is None:
        return False
    for name, default in _ENGINE_CHANNEL_SINGLE_FIELDS:
        if getattr(economy, name) != default:
            return True
    for amt, cnt in _ENGINE_CHANNEL_PAIR_FIELDS:
        if getattr(economy, amt) != 0 and getattr(economy, cnt) != 0:
            return True
    return False


def _validate_engine_channel_closure() -> None:
    """引擎字段闭集完备校验(P81 §7.2 依据二:
    闭集新字段默认不入闭集 = 静默判「一次性」,治理上劣于孤儿校验——
    构建期炸成可见)。三分类 = 引擎单字段/引擎配对/显式排除:
    ① 并集恰覆盖 EconomyEffect 全字段(新字段未分类即炸);
    ② 三桶两两互斥(单一定义 = 唯一归属);
    ③ 单字段默认值与 dataclass 缺省一致(防 (字段,默认) 对写错 →
       谓词恒触发/永不触发的静默失真)。"""
    _defaults = EconomyEffect()
    _all = {f.name for f in fields(EconomyEffect)}
    _single = {n for n, _d in _ENGINE_CHANNEL_SINGLE_FIELDS}
    _pair = {n for amt, cnt in _ENGINE_CHANNEL_PAIR_FIELDS for n in (amt, cnt)}
    _excluded = set(_ENGINE_CHANNEL_EXCLUDED_FIELDS)
    _missing = _all - _single - _pair - _excluded
    if _missing:
        raise ValueError(
            f"引擎字段闭集缺位(EconomyEffect 新字段未入三分类,"
            f"默认静默判一次性):{sorted(_missing)}")
    _overlap = (_single & _pair) | (_single & _excluded) | (_pair & _excluded)
    if _overlap:
        raise ValueError(f"引擎字段闭集双归属(三分类互斥破):{sorted(_overlap)}")
    _bad_default = [(n, d, getattr(_defaults, n))
                    for n, d in _ENGINE_CHANNEL_SINGLE_FIELDS
                    if getattr(_defaults, n) != d]
    if _bad_default:
        raise ValueError(
            f"引擎单字段默认值与 EconomyEffect 缺省不一致(闭集登记失真):"
            f"{_bad_default}")


_validate_engine_channel_closure()


@dataclass(frozen=True)
class EnvEconomyEffect:
    """投资环境的**整局经济通道**结构。

    区别于 EconomyEffect 的 per-node/一次性形态:环境效果是整局规则改写
    (位面开局分期/条件触发/费率覆写),字段按通道语义设计,全部带缺省值
    (无通道 = 全缺省)。估值单一入口 = 策略层
    ``strategies/impl/mandate_v1/env_economy.env_economy_value``
    (估值模块驻策略层;A 类精确 + 估算参数
    fail-closed + gold_after_refreshes 拍值注册)。
    **白名单制**:只收 ENV_ECONOMY 显式登记条目,禁从效果原文自动猜装
    (防错装对账 = _validate_env_economy,六条点名)。
    字段语义(值全部 = cw_invest_data 效果原文直读):
    - gold_per_plane_start: 每位面开局金,元组下标 = 位面−1(增发货币 (6,8,12);
      晶矿→金兑现按自动开启建模——晶矿开启是玩家动作面,自动与否未实采
      (战技点契约「打开20个晶矿后」为存在玩家动作的佐证),假设已登记
      登记;证非自动则 bot 具备开矿动作前该通道 fail-closed)
    - gold_instant: 获得时一次性金(蓝海 6;随机环境期望不计——选卡时未知
      且分布含未入模者,取舍已登记)
    - xp_after_level: (等级,节点数,每节点XP)(成功经验 (8,3,12);「升 8
      必然发生」假设显式登记(发展优先战略下 lv8 标配),
      证伪改条件概率)
    - gold_per_strategy_coef: 每取一张策略 +coef×含本张已持有数(策略大师 2;
      口径 = 含本张,用户裁定 2026-10-26:第 k 张到手发 coef×k,首张 coef×1;
      3-5 节点额外策略不计——策略域价值非经济通道,design §2.2.1)
    - gold_after_refreshes: (刷新阈值,返金)(长线利好 (30,20)/二手市场 (20,30);
      B 类,估值公式与参数归数据批)
    - refresh_cost_after: (刷新阈值,新成本)(长线利好 (30,1);基价 2 为游戏定义)
    - reward_node_bonus: C 类通道在场哨兵(1.0 = 通道在,经济过热/经济严重
      过热;每奖励节点期望增益真值+CI 在估算注册表,按环境变体分键——
      策略层 env_economy._REWARD_BONUS_VARIANTS;非零而缺变体映射 = 登记
      笔误,构建校验炸出)
    """
    gold_per_plane_start: tuple[int, ...] = ()
    gold_instant: int = 0
    xp_after_level: tuple[int, int, int] | None = None
    gold_per_strategy_coef: int = 0
    gold_after_refreshes: tuple[int, int] | None = None
    refresh_cost_after: tuple[int, int] | None = None
    reward_node_bonus: float = 0.0


@dataclass(frozen=True)
class RandomCharSpec:
    """随机赠卡规格(采样轴二选一:费用档或阵营;到手星级 + 类型过滤;
    「随机N费赠卡」与「随机【阵营】赠卡」两族共载体,立形首例 = 人才引进
    「随机4费」,阵营轴首例 = 追击概念股「获得【追击】角色」,禁第三形状):

    - cost: 费用轴采样(1-5,chars_by_cost 输入域;与 faction 互斥,恰好
      一轴非空,构建期校验);None = 非费用轴。
    - faction: 阵营轴采样(chars_by_faction 默认含流派匹配;池非空构建期
      校验,误登角色名 → 域空 → import 炸,天然防呆)。效果原文「获得
      【X】角色」X 为流派名非角色名,不入 chars_immediate 的具名检查域。
    - star: 到手星级 1-3(Unit.star 值域)。desc 明写 = 结构值;desc 未标
      = 填 1 的先验值(先验语义不因显式化而消失,披露键
      ``ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS`` 随卡保留——先验错走
      随机态观察覆盖,不响停);
    - type_tag: 非空 = 角色 ``char_type`` 按 '、' 切分后须含该标签才
      入池(取值 = 注册表 char_type 标签闭集,构建期校验);空 = 不过滤。
      两轴通用过滤词。
    """
    cost: int | None = None
    star: int = 1
    type_tag: str = ''
    faction: str = ''


@dataclass(frozen=True)
class GiftGrant:
    """投资环境的**具名发放**结构(送卡/送道具估值;InvestmentEnv 同区 schema)。

    发放按「取环境当场到手(即时)」与「满足条件后到手(条件)」两分——估值只对
    确定性部分给足档,条件部分降档处理(详设 §2.1.2 规则 3)。送卡的价值判据 =
    **所赠角色是否被候选终局阵容使用**(结构集合级,零数值零战力,开局静态可用;
    宪法 00_framework §1.1 禁战力建模,卖价残值对「送的人有没有人用」零判别力)。
    档位机器 = ``cw_comps.gift_hit_tier``;档位是定序实现常数非金流期望
    (定序/基数分账:(expected_gold, resolved) 契约装不下 66/60/54 档
    语义),**不经经济入口**,消费位 = 策略层 gift_value
    (gift_hit_tier 包装三口 = named_gift_value/random_faction_gift_value/
    grant_gift_value;28 号稿 §2 与 29 号稿 §2.3)。
    字段语义(值全部 = cw_invest_data 效果原文直读):
    - chars_immediate: 取环境当场发放的具名角色(效果原文「获得【X】」直读)
    - chars_conditional: (角色,条件描述原文摘要)二元组——注释性字段,不进判据
      (可读性 + 实采对账用);不可具名的随机发放(如战技点契约「随机战技点
      羁绊角色」)不入本字段,只随条件摘要留档
    - items_immediate: 取环境当场发放的具名道具,数量 = 元素重复次数(效果原文
      「获得N个【X】」直读)。道具非角色非装备,无 gain_* 原语与容器承载字段
      (容器 Field 归 sim 统一容器字段判据适用范围),消费端只产效果串 + 遥测申报;
      首条 = 火药味(开局 2 个简易武装箱)
    - items_scheduled: (节点键,道具名)二元组序列——指定「位-轮」节点发放的
      定时道具(「位面开始」= 该位面
      第 1 节点,权威先例 = 位面开局环境金 gold_per_plane_start 落
      (plane, 1) 节点窗)。数量 = 元素重复次数(与 items_immediate 同约定);
      登记不落席:入容器队列 pending_item_grants,到点经
      discharge_due_item_grants 发放(环境发放 = 确定发放)。首例 =
      特权阶级(效果原文「第二位面开始时,获得1个特权武装箱。」)
    - advisor: True=专家顾问入商店语义(特邀专家;创造一个可购买的购买选项,
      需再花店价且占购买预算,价值严格低于同档白得——资产账/可得性账分立,
      详设 §2.1.2 规则 2);False=直接送卡(契约,白得资产)
    - sell_value_note: 卖价残值注记(【注】下界;卖价 ≈ 按费用退金,度量费用
      不度量阵容价值,不进任何分值族,详设 §2.1.2-2)
    - chars_random_immediate: 取环境当场发放的随机角色,元素 =
      RandomCharSpec,数量 = 元素重复次数(效果原文「获得1个随机N费角色」
      直读形态的结构化承载)。「不可具名不入」注释覆盖 chars_immediate/
      chars_conditional 两个估值域字段(档位机器按具名角色打分);本字段
      是世界发放域形状,不进档位机器(恒判 off)。发放 = 采样支:规格过滤
      池内均匀掷骰选名 → gain_character(rand=True,gain-chain.md §5
      效果体含采样)。立形首例 = 人才引进(星级先验 1)
    - equips_random_immediate: 取环境当场发放的随机装备,元素 = 装备类别名
      (EQUIPMENTS category 词),数量 = 元素重复次数。发放 = 采样支:类别池
      (equips_by_category,注册表派生单源)内均匀掷骰选名 →
      gain_equipment(rand=True)(骇客改件先例)。首例 = 劳务派遣合同
      (「获得随机星徽」直读,池 = category '星徽')。与 items_immediate
      (占席道具,进 bench)通道不同:装备进 equips 库存,不占席、不进
      BENCH_ITEM_NAMES;世界发放域形状,不进档位机器(恒判 off,与
      chars_random_immediate 同判)
    - equips_immediate: 取环境当场发放的具名装备,数量 = 元素重复次数
      (效果原文「拥有【红钻】」直读)。承载 = gs.equips 装备库存,与
      equips_random_immediate(随机采样形状,类别池掷骰)互补:本字段 =
      确定性具名形状。与 items_*(占席道具,BENCH_ITEM_NAMES 词表身份)
      分域——装备名禁入 items 通道(会落成 BenchSlot 假身份污染溢出位
      判定),道具名禁入本通道(EQUIPMENTS 成员校验天然拒绝,武装箱系
      不在装备注册表)。不进档位机器(非角色,items 同待遇);不进
      BENCH_ITEM_NAMES 派生(装备非占席道具)。发放写通道 = 随机态
      (rand=True,2026-10-17 用户裁定:「选卡时点游戏实际发下」对首例
      环境未经实机判读核实,卡面文本是唯一证据——猜测写 + equips 观察
      覆盖纠偏,首观察静默覆盖落 logic_rand_outcome 台账不进失配网;
      先例 = T-5 财富宝钻随机态获得/T-29 奖励全腿随机态)。
      首例 = 红钻贵族。
    - replaces_opening_supply: True = 该环境的获得替换开局补给(on_env_gained
      先清席后发放,首例 = 人才储备 id 144「开局补给替换为3个随机3费角色」
      直读)。清席面 = bench 上 kind='unit' 槽(开局补给物 = 初始角色;
      占席道具类槽不在替换面——开局窗该形态结构性不存在,防御性保留);
      部署行/溢出席开局窗恒空,不触。登记防呆:True 须伴随至少一个角色支
      (chars_immediate/chars_random_immediate 非空),否则 = 「清空开局
      不发」怪卡,校验拒(_validate_env_gifts;仅环境域消费,策略表登记
      本字段 = 惰性无消费,箱腿先例同待遇)。
    """
    chars_immediate: tuple[str, ...] = ()
    chars_conditional: tuple[tuple[str, str], ...] = ()
    items_immediate: tuple[str, ...] = ()
    items_scheduled: tuple[tuple[str, str], ...] = ()
    advisor: bool = False
    sell_value_note: str = ''
    chars_random_immediate: tuple[RandomCharSpec, ...] = ()
    equips_random_immediate: tuple[str, ...] = ()
    equips_immediate: tuple[str, ...] = ()
    replaces_opening_supply: bool = False


#: ``items_scheduled`` 节点键格式('位-轮';位面 1 基 1-3,位面内轮 1 基
#: 1-9)。格式校验(_validate_env_gifts)与入队解析(on_env_gained)共消费
#: 本单一源,禁第二抄本。
_SCHEDULED_NODE_KEY_RE: re.Pattern[str] = re.compile(r'^[1-3]-[1-9]$')


@dataclass(frozen=True)
class InvestmentStrategy:
    """投资策略(局内 3 选 1,可刷新)。"""
    name: str           # 规范名(canon 归一)
    rarity: str         # "棱彩"/"金"/"银"(官方 quality)
    effect: str         # 官方效果全文(plaza API)
    source: str = ""    # 溯源(plaza:<id> / content_id / codex_20260815)
    economy: EconomyEffect | None = None   # 可数值化经济效果;战力类 None


def _strat(name: str, rarity: str, effect: str, source: str = "",
           economy: EconomyEffect | None = None) -> InvestmentStrategy:
    return InvestmentStrategy(name=name, rarity=rarity, effect=effect, source=source, economy=economy)


# ===== curated overlay:可数值化经济效果(手维护,键=注册表规范名)=====
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
    # ↑ 按 API 原文全额建模:×3 连胜奖励 + 敌人难度+N(N=连胜)+ +12XP
    '商业间谍': EconomyEffect(xp_buy_cost_discount=1),
    '返利+': EconomyEffect(instant_gold=6, gold_per_three_5cost=3),
    '采购专员·金': EconomyEffect(refresh_surprise_every=7),
    '定期福利': EconomyEffect(instant_gold=4, gold_per_node=2),
    # 加油站:官方「现在及每次进入新节点时获得1次免费刷新,立刻获得8金币」
    # (cw_invest_data.py:112,id 200301)。两腿分载:「现在」立即腿 =
    # free_refresh_burst=1(选卡登记期发放,载体惯例同固定理财/乱成一锅粥);
    # 持续腿 = free_refresh_per_node=1。当节点发放核查结论(逐效果 a/b)单一源 =
    # docs/game/currency_war/research/per_node_pick_node_grant.md。
    '加油站': EconomyEffect(instant_gold=8, free_refresh_burst=1,
                            free_refresh_per_node=1),
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
    # ↑ 免费刷 + 卖价×2。5=已裁漂移,官方卡文=6(base 层 plaza:202101):
    #   纠偏 5→6 是行为面变更,归建模批走方案审/审查;改 6 前以 5 为现行行为,读值方禁自行 +1。
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
    # —— v2 新建(调研落地;API 文本明说的数值)——
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
    # 合成/出售触发族(选卡照常评估)
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
# 首条语义全引 cw_invest_data 官方原文;二义条目 pending=True + notes 保守支,不拍死——
# 定案后回填 verdict(单一语义以实采为准)。
# 边界:只产策略源;环境('portal')/词缀('affix')双源注册属环境/词缀效果适用范围,此处不建其条目。
STRATEGY_EFFECTS: dict[str, EffectSpec] = {
    # 淘金客:官方「你每次消耗金币刷新商店,都会获得2经验值」;免费刷不产 XP(「消耗金币」
    # 文本充分;实采复核待办)。姿态谓词/CwActionLevelUpParam 抑制属淘金客姿态面适用范围,现不接。
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
    # 四歧义(改道是否吞策略给的 XP/转换同事件性/上限/版本变体)见该条目待采待办;
    # 定案前保守支=「吞」(组合在场按改道成立处理)。xp 改道算子字段待定案后补 payload。
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
        notes='CwActionLevelUpParam 后商店必刷新+偷最贵 3 张;shop 读牌/买牌对账须预知'),
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
        notes='全场出售事件;执行时序编排(卖→免费买→狂刷)=设计件 M8 编排,未接;'
              '写归属=出售面逻辑写/发牌面观察收口(详设 §5 人力重组行)'),
    # 躺平:官方「你无法在商店购买角色和刷新,持续3个节点。在此之后,获得20金币」。
    # inventory 余期追踪首例(remaining_nodes 3→0 移除);冻结姿态属姿态面适用范围。
    '躺平': EffectSpec(
        id='102001', name='躺平', trigger=TriggerKind.CONDITIONAL,
        duration=DurationKind.N_NODES, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['躺平'], duties=DutyFlags(track=True, respond=True),
        duration_nodes=3,
        notes='禁买+禁刷 3 节点后 +20 金'),
    # 免战牌:官方「进入战斗节点时,直接跳过战斗并进入下一个节点,可生效2次。
    # 获得30点经验。」(cw_invest_data.py:109,PlazaAugment 151301)。建模批件
    # 落注册表条目(设计 §次三件 5):次数类余量首例
    # (duration_uses=2 → remaining_uses,§3.2.19 正本=effect_inventory
    # .remaining_uses,§8.6-3),递减挂点 = 跳过型出战上报(kernel
    # 出战 op 自上报(report_action_start_battle_param)
    # 子态,上报时递减——出战域重设计),用尽移除。+30 经验 = 选牌当场
    # 即时经验(§4 投资选择通用通道,xp_instant 词表;§5.2 显式豁免——即时
    # 到账不入缺口清单,经观察覆盖收束)。trigger=NODE_ENTER(跳过发生在
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
    # 经同一桥」):桥按 gs.gold 现值逐条目评估,金未读(None)保守零授予。
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
    # 加油站:官方「现在及每次进入新节点时获得1次免费刷新,立刻获得8金币」
    # (cw_invest_data.py:112,id 200301)。入册使两腿经现行挂点生效:获得链
    # 登记腿(kernel/cw_gain_chain.py::gain_invest_strategy)
    # burst 桥发「现在」腿 +1;节点边界桥(per-node 形态)发持续腿。拿卡
    # 当节点不重复发:登记晚于本节点边界推进,advance_node 同节点去重位
    # 关闸。行为核查结论单一源 =
    # docs/game/currency_war/research/per_node_pick_node_grant.md。
    '加油站': EffectSpec(
        id='200301', name='加油站', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['加油站'], duties=DutyFlags(),
        notes='「现在」+1 刷=burst 腿登记期发放;每节点 +1=节点边界桥;'
              'instant_gold=8 选卡当场'),
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
# 真正的手维护信息只有例外条与不可派生名单;派生结果在构建期与逐位交叉核对基准比对
# (派生化零行为变化,决策与逐位交叉核对记录见 git 历史)。
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
    # 契约 7(阵营绑定 = 获赠该阵营角色,补)
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


# ===== 合并层:base(plaza API)× overlay → 注册表=====
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


#: 品质覆写族环境已登记名(注册表 id110/111/112/123/124/135):选中后改写
#: 后续 offer 品质分布的环境集合。游戏事实名单(单一源 = 本常量位,随
#: 注册表演进);消费面 = 测试仓一致性校验(test_sim_offer.py:本名单 ⊆
#: ENV_POOL_REWRITE 键集,防双名单漂移)——sim 抽样改写判据实际消费
#: ENV_POOL_REWRITE 结构字段(rewrite_picks 全改写型判据;部分型经
#: settled 定谳后同判据接入),本名单不作
#: 运行时判据;披露键 'invest_quality_rewrite_envs_pending' 已随
#: 2026-10-14 T-11 批整体退役,勿再引用。
QUALITY_REWRITE_ENV_NAMES: frozenset[str] = frozenset({
    '彩虹时代', '黄金时代', '白银时代', '头彩', '尾彩', '银·金·彩',
})

#: 追加随机环境型环境在册名(注册表 id113 蓝海):选中后先获得本环境
#: (其获得时效果照常触发,+6 金),随即立刻再随机获得一个环境(用户
#: 口径 2026-10-15:两次获得事件,追加非替换;「重掷」是本卡效果的
#: 口语名)。游戏事实名单(单一源 = 本常量位);世界掷骰消费端 = sim
#: 后端(世界真值层),live 端只产申报行(on_env_gained,行为
#: fail-closed——active_env 无观察覆盖通道,自掷 = 永久捏造门控输入)。
ENV_REROLL_NAMES: frozenset[str] = frozenset({'蓝海'})

#: 追加获得腿采样假设披露键(键面 = desc 未写明处的申报,消费 = sim 随局
#: 披露面 disclosures):随机池构成/分布/呈现均 desc 未写明,按 API 裁定
#: (invest_effects.md §5「desc 没写明的数值一律放弃建模」)不建模真值,
#: sim 按全集去本名均匀 v0 采样、以本键申报未证面。常量落位沿
#: ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS 先例(kernel 注册表模块)。
ENV_REROLL_ASSUMPTION_POOL: str = 'env_reroll_pool_uniform_pending'


def _validate_env_reroll_names() -> None:
    """ENV_REROLL_NAMES 成员校验(import 即炸,本模块 _validate_* 先例):
    键必须在 INVESTMENT_ENVS(防注册表改名/移除后名单静默失联——失联形态
    = sim 掷骰永不中、live 永不申报,无任何响亮信号)。"""
    orphans = ENV_REROLL_NAMES - set(INVESTMENT_ENVS)
    if orphans:
        raise ValueError(
            f"ENV_REROLL_NAMES 孤儿键(base 无此环境?):{sorted(orphans)}")


_validate_env_reroll_names()


# ===== 派生:ENV_FACTION_MAP(投资环境 → 加成阵营;从 INVESTMENT_ENVS 派生,单一真相源)=====
# ===== OCR 分隔符归一(查找边界单一源;AGENTS.md「OCR 文本匹配与修复」②无歧义形变先规范化)=====
# 实机缺陷链(run_20260826_004527):OCR 把间隔号 `·`(U+00B7)误读为圆点 `•`(U+2022)——
# cw_screen_invest_strategy L216 告警 `'全都要•彩'` 注册表 miss → 原始 OCR 名 append 进
# session.active_strategies → cw_economy 按名聚合经济效果精确查 miss → **策略经济效果被
# 静默丢弃**(真金影响)。
# 先例:cw_chars_data L5「规范名:• 已统一为·」(数据层手改);本函数是查找层归一
# (注册表数据不动,原采集路径保留原始 OCR 名不改——原始证据不碰;采集行
# 已停用,归一口径照旧覆盖查表面)。
# 无歧义性已量化(2026-08-26):INVESTMENT_STRATEGIES(335)/INVESTMENT_ENVS(83)中
# 含 `·` 的条目 33+1(如 全都要·彩/采购专员·彩/银·金·彩),含 bullet 族字符
# (•/‧/∙/・)的正规名 **0 条** → 归一不会撞任何真名。
_INVEST_SEP_CANON = '·'          # U+00B7 间隔号(注册表规范分隔符)
_INVEST_SEP_VARIANTS = (         # OCR 误读形变族 → 一律归一到 U+00B7
    '•',   # U+2022 bullet(实机日志已实测确认)
    '‧',   # U+2027 hyphenation point
    '∙',   # U+2219 bullet operator
    '・',  # U+30FB 片假名中点
)
# 全角冒号形变:注册表规范冒号 = 半角 `:`(如 特邀专家:银狼/决议:娱乐星球),
# OCR 误读全角 `：`;正规名含全角冒号 **0 条** → 归一不撞真名(无歧义性同上)。
_INVEST_COLON_CANON = ':'
_INVEST_COLON_VARIANT = '：'


def normalize_invest_name(name: str) -> str:
    """投资策略/环境名 OCR 形变归一(仅无歧义分隔符映射,不碰其它语义符号)。

    形变族两支:分隔符 bullet 族 → U+00B7;全角冒号 `：` → 半角 `:`。
    所有按名查找注册表的入口(get_strategy/get_env/economy_effect_of/
    is_known_env/env_faction/resolve_strategy_canonical)在查找前先归一入参——消费点统一受益,
    不逐 call site 改;写入端(采集/telemetry/session 存量名)保持原样。
    """
    if _INVEST_COLON_VARIANT in name:
        name = name.replace(_INVEST_COLON_VARIANT, _INVEST_COLON_CANON)
    for v in _INVEST_SEP_VARIANTS:
        if v in name:
            name = name.replace(v, _INVEST_SEP_CANON)
    return name


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
    """单策略经济效果(无/未注册 → 全 0 EconomyEffect)。

    入参先归一(normalize_invest_name)——session.active_strategies 里的存量 OCR 原始名
    (如 `全都要•彩`)也走此入口,归一后经济效果不再静默丢(run_20260826_004527 缺陷链)。
    """
    s = INVESTMENT_STRATEGIES.get(normalize_invest_name(name))
    return s.economy if (s is not None and s.economy is not None) else EconomyEffect()


def aggregate_economy(strategy_names: list[str]) -> EconomyEffect:
    """聚合多策略经济效果:加法字段求和;interest_cap_override 取**最大**(更宽上限赢,
    买断制 0 单独持有时生效 —— 与其它利息策略并持时游戏取宽值,保守建模取 max 非 min);
    win_reward_mult 取**最大**(不叠乘)。

    五族枚举补全(分型登记形态;原 design_economy §E6 已删档,取回口径=
    ;前置缺陷 R83-1/R85-3):
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


# ===== curated overlay:策略语义绑定(逐卡按效果含义手建模)=====
# 判据:**效果引用阵容专属机制/召唤物/星徽/赠 key 角色 → 绑定;泛用数值(全队强度/给金/装备)→ 不绑**。
# 为何逐卡手建模而非文本扫描:扫描有两类噪声——泛用效果顺带提及阵营误绑
# (战术义眼"恢复能量"≠能量队卡)/生命之花祝福(泛用治疗强度,误绑"治疗"),
# 且不可审不可纠;语义表可 dump 可逐条纠。
# 消费:策略层方向分触线集(strategies/impl/mandate_v1/invest_strategy)
# + cw_comps.held_strategy_fit(持卡影响 pivot)。
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
    # —— 阵容专属机制强化(金):效果点名声援某阵营机制 ——
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
    # —— 阵容专属机制强化(棱彩)——
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
    手写套组表逐位交叉核对一致(交叉核对记录见 git 历史)。
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
    """策略的(阵营绑定,角色绑定)—— 查 STRATEGY_BINDINGS 语义表(逐卡手建模;
    文本扫描派生不采用——扫描有两类噪声:泛用效果顺带提及阵营误绑
    (战术义眼"恢复能量"≠能量队卡)/不可审不可纠;语义表可 dump 可逐条纠)。

    用于策略层方向分触线集(strategies/impl/mandate_v1/invest_strategy)
    + cw_comps.held_strategy_fit(持卡影响 pivot)。
    未建模卡 → 空绑定(方向分 0;新 API 卡待 diff 提示后建模)。
    """
    return STRATEGY_BINDINGS.get(strategy.name, (frozenset(), frozenset()))


def get_strategy(name: str) -> InvestmentStrategy | None:
    """按规范名取 InvestmentStrategy;无则 None(注册表已全量 335,miss = OCR 形变,消费侧走 resolve_strategy_canonical 的 LCS 兜底;
    入参先经 normalize_invest_name 归一分隔符形变,如 `全都要•彩`→`全都要·彩`)。"""
    return INVESTMENT_STRATEGIES.get(normalize_invest_name(name))


def blood_xp_mode(session) -> tuple[str, int] | None:
    """血本位 XP 购买模式解析(返回 (卡名,每击血价);无 active 血本位卡 → None=金本位)。

    单一源 = 注册表 STRATEGY_ECONOMY.xp_buy_hp_cost 派生(先例 =
    prep_actions.record_hp_pay_event 的 mode 判定;[40]② 血闸与遥测写点
    经本助手同源消费)。多卡命中取 active_strategies 序首个
    (现版本游戏仅『奋斗协议』单卡已登记;新血本位卡落地零改动)。
    入参先经 get_strategy 归一(session 存量 OCR 原始名不静默 miss)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import game_state_of
    # 终态契约 §B:单一源 = gs.active_strategies(write_logic 选择写点)。
    for name in (game_state_of(session).active_strategies.value
                 or []) if session is not None else []:
        s = get_strategy(name)
        if (s is not None and s.economy is not None
                and s.economy.xp_buy_hp_cost):
            return name, int(s.economy.xp_buy_hp_cost)
    return None


def spy_on_level_up_active(session) -> int:
    """商业间谍升级偷牌张数现读(0 = 未持有;2026-10-17-levelup-shop-
    transition design §2.3 升级回调在册判定单一源)。

    在册判定 = EffectSpec 300201(STRATEGY_EFFECTS['商业间谍'],
    trigger=LEVEL_UP,payload.steal_on_level_up=3 官方「升级时刷新商店,
    并偷取其中最贵的3个角色」);持有判定 = 现役 held 判据
    (active_strategies 容器字段,先例 = :func:`blood_xp_mode`)。
    返回 = 偷牌张数(0 = 未持有/注册表漂移保守侧;张数只经本单一源,
    消费位 = 升级上报回调 + sim 世界腿,禁第二处内联)。
    入参先经 get_strategy 归一(session 存量 OCR 原始名不静默 miss)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import game_state_of
    spec = STRATEGY_EFFECTS.get('商业间谍')
    if spec is None or spec.id != '300201':
        return 0   # 注册表漂移保守侧(条目移除 = 效果退役,零行为)
    steal_n = int(getattr(spec.payload, 'steal_on_level_up', 0) or 0)
    if steal_n <= 0:
        return 0
    for name in (game_state_of(session).active_strategies.value
                 or []) if session is not None else []:
        s = get_strategy(name)
        if s is not None and s.name == '商业间谍':
            return steal_n
    return 0


def resolve_strategy_canonical(name: str) -> str | None:
    """候选名 → 投资策略注册表规范名(归一 + LCS 兜底)。

    LCS 兜底 = 阈值 0.6 + |Δlen|≤3(防未来新增短名/长名与现有卡高 LCS
    借分);env 名的跨表污染由调用侧 get_env 防御拦截(消费位 = 策略层
    invest_strategy env 名防御,此处只管策略表内部)。
    消费面:策略层组件查表与候选级血本位分类(形变名经此解析后入评分;
    刷新分类只认精确命中,LCS 结果不入分类——fail-closed)。
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


# ===== 阵容指向集(投资选卡阵容冲突护栏的判据源;设计 =
# docs/develop/sr_od/application/currency_war/changes/
# 2026-10-17-invest-direction-guard/design.md §2.1)=====
# 指向集 = 「这张投资服务哪些阵容阵营」的阵营名集合:非空 = 有阵容指向;
# 空 = 通用卡(纯经济/纯战力/随机角色族/时代规则类),无冲突可判。全部
# 派生自既有注册表(零手抄登记,版本重采自动跟);线库(cw_comps)反向
# 引用一律函数内延迟 import——cw_comps 模块级已引 cw_investments,反向
# 模块级即成环(augment_affinity 先例)。消费位 = strategies/impl/
# mandate_v1/invest_strategy 冲突基准(§2.2);锁定线指向不设函数
# (锁定 Comp.factions 消费侧现读)。

def env_faction_scope(env_name: str) -> frozenset[str]:
    """投资环境的阵容指向集(faction 腿 + 亲和腿;§2.1)。

    - faction 腿:``INVESTMENT_ENVS[env].faction`` 非空入集(概念股/邀请/
      契约全量登记;专家类例外 = 特邀专家:加拉赫→击破);
    - 亲和腿:``ENV_COMP_AFFINITY`` 该环境值键 = 线名,取各线 Comp.factions
      **全集**入集——副阵营随线带入(命运圣杯邀请亲和含双王圣杯 → 指向集
      = {命运圣杯, 能量}:能量组件卡可服务双王线的能量副羁绊,判兼容是
      语义本意;特邀专家:桑博 faction 空但亲和专家桑博DOT,单 faction 腿
      会误判通用)。线名缺 Comp(注册表漂移)→ 跳过不炸,指向集收窄
      宁放行(与角色腿未注册跳过同 fail 方向)。

    环境名不在注册表 → 空集;入参先 ``normalize_invest_name``——持有名
    OCR 形变不归一 = 查表 miss → 护栏基准弱化漏拦(与 strategy_lock_hit/
    env_fit/augment_affinity 查表先例同口径)。
    """
    e = INVESTMENT_ENVS.get(normalize_invest_name(env_name))
    if e is None:
        return frozenset()
    from sr_od.application.currency_war.kernel.cw_comps import (
        augment_env_affinity,
        get_comp,
    )
    out: set[str] = set()
    if e.faction:
        out.add(e.faction)
    for line_name in augment_env_affinity(env_name):
        comp = get_comp(line_name)
        if comp is not None:
            out |= set(comp.factions)
    return frozenset(out)


def strategy_faction_scope(strategy_name: str) -> frozenset[str]:
    """投资策略的阵容指向集(STRATEGY_BINDINGS 阵营腿 + 角色腿两源;§2.1)。

    - 阵营腿:绑定阵营直接入集;
    - 角色腿 ch 两源:① ``CHARACTERS[ch].factions`` **全集**入集(多阵营
      角色全展开,用户裁定「从角色去关联对应的阵容」,如丹恒·饮月 =
      仙舟/列车同行);② 成员腿:ch ∈ Comp.core_chars ∪ shared_chars 的
      线,该线 factions 全集入集——角色是某线登记成员 = 卡服务该线
      (装备党绑飞霄、飞霄是追击飞霄线 core 首席,该卡必须对锁定追击
      飞霄帧判兼容)。

    ch 不在 CHARACTERS → 跳过不炸(OCR 缺名 fail 方向一致:指向集收窄
    宁放行);策略名不在注册表/无绑定 → 空集(通用卡);入参先
    ``normalize_invest_name``(同 :func:`env_faction_scope` 口径)。
    """
    bind = STRATEGY_BINDINGS.get(normalize_invest_name(strategy_name))
    if bind is None:
        return frozenset()
    from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
    bound_facs, bound_chars = bind
    out: set[str] = set(bound_facs)
    for ch in bound_chars:
        chd = CHARACTERS.get(ch)
        if chd is not None:
            out |= set(chd.factions)
        for comp in COMP_LIBRARY:
            if ch in comp.core_chars or ch in comp.shared_chars:
                out |= set(comp.factions)
    return frozenset(out)


# ===== 环境经济通道注册表(白名单制)=====
# A 类精确四条 + B 类两条(长线利好/二手市场)+ C 类两条(经济过热/经济严重
# 过热),通道分类全量。表外环境 economy 恒 None,禁从效果原文
# 自动猜装(六条防错装对账 = _validate_env_economy);
# 轮岗/人才下沉无通道可装 → 策略层 env_economy.ENV_ECONOMY_PENDING_MODELING
# 显式登记(区别于漏登记):轮岗 = 待建模候迁出;人才下沉 = 已定案按 0
# (2026-10-16 用户裁定,永驻登记;商店 2★ 直出腿见下文
# ENV_SHOP_TWO_STAR_DEAL_PROB)。
# B/C 通道的估算参数(概率/期望/增益)在策略层 env_economy.ENV_ECONOMY_
# ESTIMATES(gold_after_refreshes 通道已改拍值注册,参数随迁停用),
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
    # (策略层 env_economy.XP_GOLD_RATE 用户裁定暂定;「升 8 必然发生」假设已登记)
    '成功经验': EnvEconomyEffect(xp_after_level=(8, 3, 12)),
    # 每取一张策略 +2×含本张已持有数(id 147;口径 = 含本张,用户裁定
    # 2026-10-26,世界面同源登记 = ENV_PICK_GRANTS);3-5 节点额外策略不计
    # (策略域价值)
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
    # → 通道 fail-closed 裸分维持,数据批口径归数据采集批(详设原文已删,git 历史可溯)
    '经济过热': EnvEconomyEffect(reward_node_bonus=_REWARD_NODE_BONUS_MARK),
    '经济严重过热': EnvEconomyEffect(reward_node_bonus=_REWARD_NODE_BONUS_MARK),
}


def _validate_env_economy() -> None:
    """ENV_ECONOMY 构建校验(import 即炸):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新
    改名/移除后静默失联);② **六条防一次性错装逐条对账**——
    点名六条(增发货币/成功经验/二手市场/长线利好/策略大师/劳务派遣合同)的
    效果全是分期/条件/触发形态,禁装成 gold_instant 单通道(一次性错装);
    劳务派遣合同(卡面效果 = 随机星徽授予 + 每首领节点发对应羁绊随机角色,
    流程侧已登记建模;经济通道零动作)无对应经济通道字段,登记即错装 →
    直接拒绝;③ 挂载一致性:replace 后
    INVESTMENT_ENVS[name].economy 与表内实例同一对象(防后续构建段重挂漂移)。
    """
    orphans = [n for n in ENV_ECONOMY if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(f"ENV_ECONOMY 孤儿键(base 无此环境?):{sorted(orphans)}")
    _anti_instant = ('增发货币', '成功经验', '二手市场', '长线利好', '策略大师')
    for _n, _eff in ENV_ECONOMY.items():
        if _n in _anti_instant and _eff.gold_instant != 0:
            raise ValueError(
                f"ENV_ECONOMY 防错装:{_n!r} 效果为分期/条件形态,"
                f"禁装 gold_instant={_eff.gold_instant}(一次性错装)")
    if '劳务派遣合同' in ENV_ECONOMY:
        raise ValueError(
            "ENV_ECONOMY 防错装:劳务派遣合同(卡面效果 = 随机星徽授予 + "
            "每首领节点发对应羁绊随机角色,非经济效果,流程侧已登记建模)"
            "无对应经济通道字段,禁以现有字段近似装表")
    for _n, _eff in ENV_ECONOMY.items():
        if INVESTMENT_ENVS[_n].economy is not _eff:
            raise ValueError(f"ENV_ECONOMY 挂载不一致:{_n!r} economy 未挂载或实例漂移")


for _n, _eff in ENV_ECONOMY.items():
    INVESTMENT_ENVS[_n] = replace(INVESTMENT_ENVS[_n], economy=_eff)
_validate_env_economy()


# ===== 环境声明矿注册表(details/ore-reward-channel.md §2)=====
# **世界发放域**(矿进入世界时的声明内容),与 ENV_ECONOMY(估值域)分域不互斥
# ——增发货币两表同时已登记是常态;ENV_GIFTS ∩ ENV_ECONOMY = ∅ 检查覆盖「单一
# 环境只落一个估值结构」,本表不参与该检查,代之以与估值面的双源同值校验
# (见 _validate_env_ore_grants 第③条)。消费面 = kernel/cw_ore_channel.py
# 声明入队电平检查(键查)与挂接入口生成(值出队)。
ENV_ORE_GRANTS: dict[str, tuple[int, ...]] = {
    # 每位面开局 6/8/12 金晶矿(id 103 原文直读,cw_invest_data PlazaPortal('103'))
    '增发货币': (6, 8, 12),
}


def _validate_env_ore_grants() -> None:
    """ENV_ORE_GRANTS 构建校验(import 即炸;沿 _validate_env_economy 先例,
    details/ore-reward-channel.md §2):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 值形:长度 3(位面 1-3)、逐项正整数的元组;
    ③ 双源同值:同键在 ENV_ECONOMY 有非空 gold_per_plane_start → 长度相等
    且逐位同值——估值面与世界面同出卡面(id 103),任一侧单独改金额即失同步,
    构建期炸(世界真值错档 = sim 里声明矿发错钱)。
    """
    orphans = [n for n in ENV_ORE_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(f"ENV_ORE_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, _golds in ENV_ORE_GRANTS.items():
        if not isinstance(_golds, tuple) or len(_golds) != 3 \
                or not all(isinstance(_g, int) and not isinstance(_g, bool)
                           and _g > 0 for _g in _golds):
            raise ValueError(
                f"ENV_ORE_GRANTS 值形({_n!r}):须为长度 3、逐项正整数的元组"
                f"(位面 1-3 声明金额),现值 {_golds!r}")
        _econ = ENV_ECONOMY.get(_n)
        _src = tuple(getattr(_econ, 'gold_per_plane_start', ()) or ())
        if _src and (len(_src) != len(_golds) or _src != tuple(_golds)):
            raise ValueError(
                f"ENV_ORE_GRANTS 双源失同步({_n!r}):ENV_ECONOMY."
                f"gold_per_plane_start={_src} ≠ 本表 {tuple(_golds)}"
                f"(估值面与世界面同出卡面,失同步即构建期炸)")


_validate_env_ore_grants()


# ===== 环境具名发放注册表(白名单制)=====
# 送卡型环境(契约 ×7 + 特邀专家 ×4)、道具型环境(火药味即时 + 特权阶级
# 定时)、随机角色环境(人才引进)、随机装备环境(劳务派遣合同)、召唤单位
# 环境(三星佩佩/粗星佩佩)与具名装备环境(红钻贵族)的具名
# 发放登记,白名单制(表外环境一律无条目,禁从效果原文自动猜装,ENV_ECONOMY
# 同款纪律)。
# 档位机器 = cw_comps.gift_hit_tier(消费契约见其 docstring);档位是定序实现
# 常数非金流期望(定序/基数分账),不经经济入口,消费位 = 策略层 gift_value
# (gift_hit_tier 包装;28 号稿 §2 与 29 号稿 §2.3)。
# 逐条语义与分档落点 = 本表登记 + 效果原文对账 id(详设盘点原文已删,git 历史可溯)。
# 锁面(测试仓):kernel/test_gain_chain.py(ENV_GIFTS 分道/道具/定时通道 +
# 落地相全量接入)、strategies/impl/mandate_v1/test_invest_strategy.py(档→分
# 映射/具名分档/键完备)、sim/test_sim_backend.py(sim 世界腿到点发放)。
ENV_GIFTS: dict[str, GiftGrant] = {
    # 效果原文对账 id(cw_invest_data.PLAZA_PORTALS):量子同频 125/公司 126/持续伤害 127/
    # 战技点 128/星核猎手 129/欢愉 1201/命运圣杯 1202/特邀专家 141/142/143/148
    # 道具型:火药味 101
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
    # 特邀专家 4 条 = 顾问入商店语义(advisor=True,付费购买期权);附加效果
    # (停云终结技增益/加拉赫击破档腿世界发放已接(ENV_BOND_TIER_GRANTS),
    # 装备资产不入估值维持/桑博节点礼盒)异质不入估值,停云/桑博仅占位登记
    # (详设 §2.1.1 注;桑博礼盒无数值,invest_effects.md §5 同类裁定同源)
    '特邀专家:停云': GiftGrant(chars_immediate=('停云',), advisor=True),
    '特邀专家:加拉赫': GiftGrant(chars_immediate=('加拉赫',), advisor=True),
    '特邀专家:银狼': GiftGrant(chars_conditional=(
        ('银狼', '首次获得【银狼LV.999】时,顾问入商店'),
    ), advisor=True),
    '特邀专家:桑博': GiftGrant(chars_immediate=('桑博',), advisor=True),
    # 道具通道首条(id 101 效果原文「开局时获得2个简易武装箱」直读;数量 =
    # 元素重复次数)。道具 = 占席待开箱,非角色非经济,档位机器恒 off(不进
    # 打分);消费 = on_env_gained 效果串 + 遥测申报(容器承载字段归 sim
    # 统一容器字段判据适用范围,现缺省不写)
    '火药味': GiftGrant(items_immediate=('简易武装箱', '简易武装箱')),
    # 即时装备通道首例(id 131 效果原文「开局时拥有【红钻】和一个【简易武装箱】。」
    # 直读,PlazaPortal('131');「开局时」= 环境注册时点,火药味/人才引进
    # 「开局时获得」同口径)。数量 = 元素重复次数,与 items 通道同约定;
    # 装备腿在前 = 卡文序(on_env_gained 装备支位于 items_immediate 支之前,
    # 遥测序与卡文对齐)。红钻 ∈ EQUIPMENTS(合成材料,非占席道具);箱 =
    # 道具通道现役(武装箱系不在装备注册表,装备名漂移校验天然互斥)。
    # 装备腿发放写通道 = 随机态(见 GiftGrant.equips_immediate docstring
    # 裁定注记)
    '红钻贵族': GiftGrant(equips_immediate=('红钻',),
                          items_immediate=('简易武装箱',)),
    # 即时装备通道第二卡(id 132 效果原文「开局时拥有【蓝钻】和一个【简易武装箱】。」
    # 直读,PlazaPortal('132');「开局时」= 环境注册时点,红钻贵族同口径)。
    # 机制件形状 = GiftGrant.equips_immediate(首例红钻贵族同字段同校验),本条目
    # 为纯数据行;蓝钻 ∈ EQUIPMENTS(合成材料,非占席道具);蓝钻合成面(流派星徽系)
    # 不在本卡辖域。
    '蓝钻贵族': GiftGrant(equips_immediate=('蓝钻',),
                          items_immediate=('简易武装箱',)),
    # 定时通道首例(id 102 效果原文「第二位面开始时,获得1个特权武装箱。」
    # 直读):「位面开始」= 该位面第 1 节点(节点键 '2-1';先例 = 位面开局
    # 环境金 gold_per_plane_start 落 (plane, 1) 节点窗)。登记不落席:入容器
    # 队列 pending_item_grants,到点经 discharge_due_item_grants 发放
    # (环境发放 = 确定发放;生产挂点 = sim 进节点收束,实机不接——队列登记
    # 后保持原样,备战真值归观察覆盖,迭代 2026-09-24-scheduled-env-gifts
    # design §2.5 不对称申报)
    '特权阶级': GiftGrant(items_scheduled=(('2-1', '特权武装箱'),)),
    # 随机支登记(id 109 效果原文「开局拥有1个随机4费角色。」直读,
    # PlazaPortal('109'));星级未标 = star 1 先验(晶矿 CHAR_DROP_STAR/
    # 骇客同句式先例,先验语义由披露键 star_prior 承载);无类型词 →
    # type_tag 空,池 = 4 费全档;时点「开局」= 环境注册时点,与火药味
    # 「开局时获得」同口径(items_immediate 选卡即发)
    '人才引进': GiftGrant(chars_random_immediate=(RandomCharSpec(cost=4, star=1),)),
    # 类型过滤随机支首例(id 136 效果原文「获得1个随机2星1费的输出角色」
    # 直读,PlazaPortal('136'));星级 2 = 卡面明写非先验;「输出」=
    # char_type 按 '、' 切分含标签即入池(多标签计入,用户裁定 2026-10-21,
    # 池为注册表现值派生非固定名单);采样/先验披露随家族常量
    # ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS 携带;属性加成腿(「进入新节点
    # 永久随机属性加成」)全腿不建模,披露键 env_char_buff_unmodeled
    '战力提升': GiftGrant(chars_random_immediate=(
        RandomCharSpec(cost=1, star=2, type_tag='输出'),)),
    # 类型过滤随机支姊妹卡·无类型词变体(id 137 效果原文「获得1个随机2星
    # 2费角色」直读,PlazaPortal('137'));星级 2 = 卡面明写非先验;无类型词 →
    # type_tag 空,池 = 2 费全档(注册表现值派生,爻光费用勘误 2→1 自动
    # 不入池);采样/先验披露随家族常量 ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS
    # 携带;属性加成腿(「进入新节点永久随机属性加成」)全腿不建模,披露键
    # env_char_buff_unmodeled 引用 T-36 批已立常量(卡区分靠效果账本上下文)
    '战力飙升': GiftGrant(chars_random_immediate=(
        RandomCharSpec(cost=2, star=2),)),
    # 随机装备支首例(id 118 效果原文「获得随机星徽」直读,
    # PlazaPortal('118');数量词缺省 = 1 件先验,披露键
    # ENV_STAR_GRANT_ASSUMPTION_KEYS 承载)。绑定腿:发放名以 done 条件键
    # 'star_grant#<名>' 落 env_grants_done(腿2「每次进入首领节点获得对应
    # 羁绊的随机角色」的绑定解析唯一源,触发函数 =
    # kernel/cw_env_grants.check_env_boss_grants,白名单 = ENV_BOSS_GRANTS)
    '劳务派遣合同': GiftGrant(equips_random_immediate=('星徽',)),
    # 召唤单位支首例(id 115 效果原文「获得一个穿戴三个随机星徽的佩佩。」直读,
    # PlazaPortal('115');佩佩 ∈ CHARACTER_ROSTER(cw_chars 召唤族,0 费后台
    # 系统单位,恒最右/不可拖/不可卖)。登记定性(用户裁定 2026-10-15):
    # 星徽佩戴在佩佩身上非入栏——equips 栏 = 未穿戴库存,穿戴件入栏 = 伪造
    # 世界真值;容器行 equips 的消费端(板面真值/巨星候选/行键)的穿戴输入
    # 对本卡结构性恒空(环境授予穿戴不入容器行 = 增量派生刻意基座),live
    # 面板观察承载;星徽随机池 desc 无载(放弃纪律)→ 申报键见
    # ENV_GIFT_UNMODELED_ASSUMPTION_KEYS。星级 = 用户裁定佩佩无星级,链必填
    # 实参落 1 为占位非先验(无星可观察,先验/校准语义不适用)。
    '三星佩佩': GiftGrant(chars_immediate=('佩佩',)),
    # 召唤单位支姊妹卡(id 116 效果原文「获得一个穿戴三个随机星徽的佩佩，粗心的
    # 佩佩有时候会把星徽落在你的物品栏。」直读,PlazaPortal('116');佩佩 ∈
    # CHARACTER_ROSTER(cw_chars 召唤族,0 费后台))。两腿零登记定性(披露键
    # 申报,防误判漏报):
    # - 佩戴星徽腿:同三星佩佩口径(穿戴非入栏,容器行 equips 消费端的穿戴
    #   输入对本卡结构性恒空 = 增量派生刻意基座,live 面板观察承载,随机池
    #   desc 无载按放弃纪律)。
    # - 掉落腿(「有时候…落在你的物品栏」):概率/时点/件数/池四维 desc 全
    #   无载(放弃纪律)+ 无登记字段可容(扩字段 = 提前抽象且无合法填充值);
    #   live 掉落真值归 equips 观察,sim 世界缺掉落物 = 申报缺口(特权阶级
    #   不对称申报同型);随机星徽整族建模现状:劳务派遣合同已按「获得」
    #   直读登记随机装备支(见上),买彩票系仍零建模,本卡佩戴/掉落两腿
    #   仍按上文口径归观察。
    # 星级 = 用户裁定佩佩无星级(2026-10-15):链必填实参落 1 为占位非先验。
    '粗星佩佩': GiftGrant(chars_immediate=('佩佩',)),
    # 专家研讨会(id 139,效果原文「获得1个【专家邀请函】和1个【简易武装箱】。」
    # 直读,PlazaPortal('139');卡文无「开局时」字样,环境效果唯一可实现
    # 时点 = 环境注册(选卡当场),用户裁定 2026-10-24)。卡文序 = 邀请函
    # 先箱后。专家邀请函 = kind='bookcard'(开卡链)、简易武装箱 =
    # kind='supply_box'(开箱链);落席类别判定单一源 = BENCH_ITEM_KINDS
    # (与本条目同批登记,缺一即被 _validate_bench_item_kinds 闭集校验
    # import 炸,无书写顺序语义)。不设 advisor=True:advisor 语义 = 顾问
    # 直接入商店(特邀专家),本卡为道具中间态,开启时点与选择权在玩家,
    # 开卡后语义归现役开卡/选卡链。bookcard 槽件发放首例(items 通道此前
    # 全为武装箱系)。
    '专家研讨会': GiftGrant(items_immediate=('专家邀请函', '简易武装箱')),
    # 开局替换型赠卡首例(id 144 效果原文「开局补给替换为3个随机3费角色」
    # 直读,PlazaPortal('144'))。时序 = 实机环境确认先于开局补给发放,替换
    # 挂环境获得链先清后发(on_env_gained 清席支,世界结果与「开局发放时点
    # 替换」无差)。三元素重复 = 数量 3(与 items 通道「数量 = 元素重复次数」
    # 同约定);星级未标 → star=1 先验(家族口径 T-10/T-36);三连抽独立可重
    # (用户裁定 2026-10-25 四项默认案:三同名 1★ 经获得链 3 合 1 合成 2★
    # = 链自然结果)。升星属性腿(11%/33% 速度、22%/66% 伤害)不建模(用户
    # 裁定随 T-36/T-37 家族同案同裁;「有值无容器」——数值卡面明写而 Unit
    # 无属性域/sim 战斗不消费/无观察读点),披露键 env_char_buff_unmodeled
    # 随家族常量携带;替换/合成语义假设申报 = ENV_OPENING_REPLACE_ASSUMPTION_
    # KEYS。3 费池 = chars_by_cost(3) 注册表派生(现值 14 名,含银狼LV.999;
    # 与特邀专家:银狼无交互面——两环境单局互斥)
    '人才储备': GiftGrant(
        chars_random_immediate=(
            RandomCharSpec(cost=3, star=1),
            RandomCharSpec(cost=3, star=1),
            RandomCharSpec(cost=3, star=1),
        ),
        replaces_opening_supply=True,
    ),
    # ===== 概念股族(id 1001-1016,模式卡 T-48;族展开登记模板见
    # docs/develop/sr_od/application/currency_war/game_state/fields.md §5.2)=====
    # id 1001 效果原文直读:「追击」= desc【追击】直读(流派名,与 ENV_FACTION
    # 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS);
    # 简易装备 1 件 = 单数叙述默认假设(ENV_CONCEPT_STOCK_ASSUMPTION_KEYS);
    # 简易池 = category '简易' 现值 8 件。
    '追击概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='追击', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1002 效果原文直读:「燃血」= desc【燃血】直读(流派名,与 ENV_FACTION
    # 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS);
    # 简易装备 1 件 = 单数叙述默认假设(ENV_CONCEPT_STOCK_ASSUMPTION_KEYS);
    # 简易池 = category '简易' 现值 8 件。
    '燃血概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='燃血', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1003 效果原文直读:「能量」= desc【能量】直读(流派名,与 ENV_FACTION
    # 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS);
    # 简易装备 1 件 = 单数叙述默认假设(ENV_CONCEPT_STOCK_ASSUMPTION_KEYS);
    # 简易池 = category '简易' 现值 8 件。
    '能量概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='能量', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1004 效果原文直读:「列车同行」= desc【列车同行】直读(阵容羁绊名,
    # 与 ENV_FACTION 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_
    # ASSUMPTION_KEYS);简易装备 1 件 = 单数叙述默认假设
    # (ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;economy.md「列车送幸运星」线索
    # 已随 fixed_hypothesis 键在册);简易池 = category '简易' 现值 8 件。
    '列车同行概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='列车同行', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1005 效果原文直读:「银河学者」= desc【银河学者】直读(阵营羁绊名,
    # 与 ENV_FACTION 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_
    # ASSUMPTION_KEYS);简易装备 1 件 = 单数叙述默认假设
    # (ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;economy.md 四卡线索名单不含
    # 银河学者 = 装备身份零先验,均匀 v0 + 按卡固定假说待校准);简易池 =
    # category '简易' 现值 8 件。
    '银河学者概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='银河学者', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1006 效果原文直读:「贝洛伯格」= desc【贝洛伯格】直读(阵营羁绊名,
    # 与 ENV_FACTION 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_
    # ASSUMPTION_KEYS);简易装备 1 件 = 单数叙述默认假设
    # (ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;economy.md 四卡线索名单不含
    # 贝洛伯格 = 装备身份零先验,均匀 v0 + 按卡固定假说待校准);简易池 =
    # category '简易' 现值 8 件。
    '贝洛伯格概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='贝洛伯格', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1007 效果原文直读:「星间旅人」= desc【星间旅人】直读(阵营羁绊名,
    # 与 ENV_FACTION 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_
    # ASSUMPTION_KEYS);简易装备 1 件 = 单数叙述默认假设
    # (ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;economy.md 四卡线索名单不含
    # 星间旅人 = 装备身份零先验,均匀 v0 + 按卡固定假说待校准);简易池 =
    # category '简易' 现值 8 件。
    '星间旅人概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='星间旅人', star=1),),
                            equips_random_immediate=('简易',)),
}


# 开拓者双形态(欢愉/记忆两条独立注册条目)在随机角色发放采样中按单一
# 角色位合并:牌库中开拓者占一位,备战席/商店恒欢愉形态,场上才分前台
# (记忆)/后台(欢愉)——「获得」类发放落备战席恒发欢愉(用户实机知识
# 2026-10-28,docs/game/currency_war/research/economy.md §8)。
# 键 = 剔除条目名,值 = 保留条目名(发放名)。
_DUAL_FORM_MERGE: dict[str, str] = {'开拓者·记忆': '开拓者·欢愉'}


def random_char_pool(spec: RandomCharSpec) -> list[str]:
    """规格过滤池(注册表派生,零硬编码第二源):采样轴内 + 类型标签含入
    (阵营轴 = chars_by_faction 默认含流派匹配,费用轴 = chars_by_cost;
    char_type 按 '、' 切分含标签,两轴通用过滤词)。尾部开拓者双形态按
    角色位合并收口(键侧条目剔除,采样即发放名 = 值侧形态,单一源 =
    模块级 ``_DUAL_FORM_MERGE``)——采样域即发放域,随机赠卡家族与
    boss 腿2/晶矿随机羁绊支(经本函数取池)三通道同源生效。构建期非空
    校验见 ``_validate_env_gifts``;运行期空池 = 注册表漂移,发放腿
    (cw_gain_chain ``on_env_gained`` 随机支)再查一道防御。"""
    base = chars_by_faction(spec.faction) if spec.faction else chars_by_cost(spec.cost)
    pool = [c.name for c in base
            if not spec.type_tag or spec.type_tag in c.char_type.split('、')]
    return [n for n in pool if n not in _DUAL_FORM_MERGE]


def equips_by_category(category: str) -> tuple[str, ...]:
    """装备注册表按类别派生池(零硬编码第二源;构建/运行期同源消费)。"""
    return tuple(n for n, e in EQUIPMENTS.items() if e.category == category)


#: 随机赠卡类型标签闭集(从 CHARACTERS.char_type 按 '、' 切分派生,空标签
#: 剔除;构建期校验 RandomCharSpec.type_tag 用,防手写错字致池空静默)。
_CHAR_TYPE_TAGS: frozenset[str] = frozenset(
    tag for _c in CHARACTERS.values()
    for tag in _c.char_type.split('、') if tag)

#: 随机赠卡家族的采样/先验假设申报键(家族常量,三键;键随家族携带不随
#: 单卡增减,消费面 = 实测校准与披露清单):
#: - uniform: 规格过滤池内均匀 v0(真分布未实测,实机校准源 =
#:   logic_rand_outcome 行掷骰名 vs bench 实读逐局积累);
#: - star_prior: desc 未标星时 star=1 为先验非结构值(直出高星由 bench
#:   观察星级覆盖模型值,随机态不响灯);
#: - type_tag: 类型过滤口径 = char_type 含标签(本键随家族常量携带,
#:   空标签卡不消费)。
ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS: tuple[str, ...] = (
    'env_gift_random_char_uniform',
    'env_gift_random_char_star_prior',
    'env_gift_random_char_type_tag',
)

#: 环境「desc 有载但刻意零建模」腿的申报键(家族常量,键随家族携带不随
#: 单卡增减,形态沿 ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS 先例;消费面 =
#: 披露清单,防未来把「无建模」误判为漏报):
#: - env_gift_worn_badges_unmodeled: 环境卡授予的星徽**穿戴**不建模(用户
#:   裁定 2026-10-15)——穿戴非入栏,容器行 equips 消费端(板面真值/巨星
#:   候选/行键)的穿戴输入对环境卡结构性恒空,live 面板观察承载;首例 =
#:   三星佩佩(id 115;姊妹卡粗星佩佩同款佩戴句,其卡落地时引用本键不重立)。
#: - env_gift_badge_drop_unmodeled: 环境卡的星徽**掉落入栏**不建模(用户
#:   裁定 2026-10-15)——概率/时点/件数/池四维 desc 全无载(放弃纪律),
#:   无登记字段可容;live 掉落真值归 equips 观察,sim 世界缺掉落物 = 申报
#:   缺口(特权阶级不对称申报同型);首例 = 粗星佩佩(id 116)。
#: - env_char_buff_unmodeled: 环境「每节点属性 buff」腿不建模(家族同案,
#:   用户裁定 2026-10-21/2026-10-25)——成员①战力提升/战力飙升(id 136/137):
#:   赠卡角色的「进入新节点永久随机属性加成」,属性集/数值/叠加规则 desc
#:   全无载(放弃纪律不实机查);成员②进化算法(id 145):全场上角色每节点叠
#:   4% 前后台强度+2% 伤害减免,数值卡面有载而机械三无(GameState 无角色
#:   属性域 = 容器零/sim 战斗纯随机面不消费战力 = 消费者零/无已建档识别面
#:   = 对账零,4%/2% 的基数口径/叠加上限/单位边界/首触发时点另四维零载)。
#:   共通:「每节点层数计数器」= 预建机制无驱动(命运礼物开盒内容同案判例)
#:   且现役 counters 为效果级非角色级、按角色叠层无落点,不建;真值实采后
#:   按周期触发器骨架起建零迁移(设计 = T-36 设计稿 §2.5/T-44 设计稿 §2.3
#:   预留指针);首例 = 战力提升(id 136)。
ENV_GIFT_UNMODELED_ASSUMPTION_KEYS: tuple[str, ...] = (
    'env_gift_worn_badges_unmodeled',
    'env_gift_badge_drop_unmodeled',
    'env_char_buff_unmodeled',
)

#: 开局替换型赠卡(首例 = 人才储备 id 144)的语义假设申报键(卡级两键,
#: 形态沿家族常量先例;消费面 = 披露清单,防 desc 空白处的模型口径被误当
#: 已证真值):
#: - env_opening_replace_semantics: 「替换」的模型口径 = 开局 4 张初始角色
#:   被 3 张随机 3 费 1★ 取代(非叠加)。开局补给的晶矿腿(开场矿)在场有载
#:   (screen_flow_timing.md「给开局角色 + 晶矿」)而全系统未建模(apply_
#:   opening 写入集零矿写端),本卡不引入新缺口也不动它;替换后是否保留
#:   其他开局呈现候实机首遇对账(证伪路径 = 首备战帧 bench 张数对照:
#:   模型 3;实机 7 = 叠加语义,4 = 替换未生效)。
#: - env_opening_replace_merge_semantics: 三同名 1★ 经获得链 3 合 1 合成
#:   2★ = 链自然结果的模型口径;游戏真值(开局补给发重名是否合并)未证;
#:   口径错 = live 首备战帧 bench 观察整表覆盖兜底,sim 侧申报缺口。
ENV_OPENING_REPLACE_ASSUMPTION_KEYS: tuple[str, ...] = (
    'env_opening_replace_semantics',
    'env_opening_replace_merge_semantics',
)

#: 随机星徽授予家族(劳务派遣合同,腿1 星徽 + 腿2 首领节点角色)的
#: 采样/先验假设申报键(六键;键随家族携带不随单卡增减,消费面 = 实测
#: 校准与披露清单):
#: - env_star_grant_uniform: 星徽等概率 v0(分布未实测,晶矿/全员晋升
#:   均匀 v0 先例,校准源 = equips 观察 vs 掷骰名 logic_rand_outcome 行
#:   逐局积累);
#: - env_star_grant_count1: 腿1 数量 1 件先验(desc 无数量词,自然语言
#:   单数省写;先验错 = sim 世界多/少装备,bench 无感、资产对照偏差);
#: - env_star_grant_bind_single: 「对应羁绊」= 腿1 采样单枚固定绑定
#:   (desc 句式回指解读;若实机为已持全部星徽各触发,模型少发);
#: - env_boss_grant_char_uniform: 羁绊成员池等概率 + flows 含入
#:   (chars_by_faction 默认参数,与 FactionInfo.members 同源);
#: - env_boss_grant_char_star1: 腿2 星级 1★ 先验(晶矿 CHAR_DROP_STAR
#:   同句式,先验错走 bench 观察星级覆盖);
#: - env_boss_grant_count1: 腿2 每 boss 节点 1 个先验(desc 无数量词)。
ENV_STAR_GRANT_ASSUMPTION_KEYS: tuple[str, ...] = (
    'env_star_grant_uniform',
    'env_star_grant_count1',
    'env_star_grant_bind_single',
    'env_boss_grant_char_uniform',
    'env_boss_grant_char_star1',
    'env_boss_grant_count1',
)

#: 概念股族(随机阵营赠卡 + 随机简易装备,首例 = 追击概念股 id 1001)的
#: 装备轴采样/假设申报键(家族常量,三键,形态沿 ENV_STAR_GRANT_ASSUMPTION_
#: KEYS 先例;消费面 = 实测校准与披露清单):
#: - env_concept_stock_equip_uniform: 简易池均匀 v0(实机真分布未知;
#:   校准源 = logic_rand_outcome ``env_equip_random:`` 行 vs equips 实读
#:   逐局积累);
#: - env_concept_stock_equip_count1: 件数 1 = 单数叙述默认假设非直读
#:   (实机多件 → 观察覆盖 + 登记行加元素);
#: - env_concept_stock_equip_fixed_hypothesis: 按卡固定假说在案待校准
#:   (economy.md「概念股送装备件」四卡线索:昼神/追击→轮滑鞋、仙舟→
#:   折叠小刀、列车送幸运星;校准 = 同卡实读件分布,恒同件 → 升级按卡
#:   表,离散 → 均匀口径维持)。
ENV_CONCEPT_STOCK_ASSUMPTION_KEYS: tuple[str, ...] = (
    'env_concept_stock_equip_uniform',
    'env_concept_stock_equip_count1',
    'env_concept_stock_equip_fixed_hypothesis',
)

#: 概念股族阵营刷新概率腿的「零建模」失真申报键(家族常量;键模板 =
#: ``env_<id>_faction_refresh_odds_unmodeled``,族卡随各自批次追加 id,
#: 本批收 env_1001、env_1002、env_1003、env_1004、env_1005、env_1006、env_1007;消费面 = 披露清单,invest_effects.md §5 在案裁定为
#: 主披露,键为登记面载体):失真方向 = sim 商店发牌不模拟阵营权重
#: (cw_shop_deal 采样按 REFRESH_PROB 费用基线,阵营轴无参数),刷出该
#: 阵营角色频率系统性低于实机 → 低估该环境的找牌运气收益;解禁条件 =
#: 版本更新 desc 带结构化数值,或用户对概念股族裁定重开建模(效力仅
#: 族内,不构成 §5 全面重裁);遥测对账只量化失真,不产落参。
ENV_FACTION_REFRESH_ODDS_UNMODELED_KEYS: tuple[str, ...] = (
    'env_1001_faction_refresh_odds_unmodeled',
    'env_1002_faction_refresh_odds_unmodeled',
    'env_1003_faction_refresh_odds_unmodeled',
    'env_1004_faction_refresh_odds_unmodeled',
    'env_1005_faction_refresh_odds_unmodeled',
    'env_1006_faction_refresh_odds_unmodeled',
    'env_1007_faction_refresh_odds_unmodeled',
)

# (送卡「档→分」映射与 advisor 折减 = 策略层 gift_value
# (GIFT_TIER_SCORE/ADVISOR_DISCOUNT,消费位 = invest_env/invest_strategy),
# 本文件不留分值常数——宪法五,衍生打分归策略层;floor 定序形态随
# 消费核停用 历史。)


def _validate_random_char_spec(table: str, name: str, spec: RandomCharSpec) -> None:
    """RandomCharSpec 构建校验(ENV_GIFTS 与 ENV_DEPLOY_LOCK_GRANTS 共享):
    轴互斥/费用域/星级域/类型标签闭集/过滤池非空。table/name = 报错定位
    (文案沿各表现款句式,费用域仅 cost 非 None 时查——cost/faction 恰好
    一轴非空,阵营轴条目无费用域可言)。"""
    if (spec.cost is None) == (spec.faction == ''):
        raise ValueError(
            f"{table} 随机赠卡采样轴({name!r}):cost 与 faction "
            f"须恰好一轴非空(双空 = 全角色池,双填 = 轴语义不明)")
    if spec.cost is not None and (isinstance(spec.cost, bool) or not 1 <= spec.cost <= 5):
        raise ValueError(
            f"{table} 随机赠卡费用档({name!r}):{spec.cost!r} "
            f"须为 1-5 整数(chars_by_cost 输入域)")
    if isinstance(spec.star, bool) or spec.star not in (1, 2, 3):
        raise ValueError(
            f"{table} 随机赠卡星级({name!r}):{spec.star!r} "
            f"须为 1-3 整数(Unit.star 值域)")
    if spec.type_tag and spec.type_tag not in _CHAR_TYPE_TAGS:
        raise ValueError(
            f"{table} 随机赠卡类型标签({name!r}):"
            f"{spec.type_tag!r} 不在注册表 char_type 标签闭集"
            f"(手写错字会致池空静默):{sorted(_CHAR_TYPE_TAGS)}")
    if not random_char_pool(spec):
        raise ValueError(
            f"{table} 随机赠卡池空({name!r}):"
            f"cost={spec.cost} faction={spec.faction!r} "
            f"type_tag={spec.type_tag!r} 过滤后无角色(注册表漂移?)")


def _validate_env_gifts() -> None:
    """ENV_GIFTS 构建校验(import 即炸):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(沿 ENV_ECONOMY 先例,防版本更新改名/
    移除后静默失联);② 角色名漂移:发放角色(即时∪条件)必须在 CHARACTER_ROSTER
    (版本漂移不静默,与孤儿键同批校验);③ 空发放集条目拒绝(即时角色/条件角色/
    即时道具/定时道具/随机角色/随机装备/即时装备全空 = 数据残缺,档位机器恒判
    off,会把登记笔误放大成失格门误杀);④ ``set(ENV_GIFTS) ∩ set(ENV_ECONOMY)
    = ∅``——单一环境只落一个估值结构,防双通道叠加(∩ ENV_POOL_REWRITE 半边由
    3.6 品质改写建表时收全);⑤ 定时通道两防呆(迭代 2026-09-24-scheduled-env-gifts):
    节点键格式'位-轮'(坏键 = on_env_gained 入队解析必炸的脏数据,import 拒收)、
    定时道具名禁∈ CHARACTER_ROSTER(道具/角色通道串行防呆,道具名混入角色注册表
    会在发放侧造假身份);⑥ 随机赠卡规格(RandomCharSpec)值域四查(共享助手
    ``_validate_random_char_spec``,与 ENV_DEPLOY_LOCK_GRANTS 同源单一):采样轴
    互斥(cost/faction 恰好一轴非空——双空 = 全角色池几乎必为登记笔误,双填 =
    轴语义不明)、cost 1-5(仅 cost 非 None 时,bool 显式拒——bool 是 int 子类,
    True 会被纯 int 判当 1 混过)、star 1-3、type_tag ∈ 注册表 char_type 标签
    闭集(错字致池空静默)、规格过滤池非空(阵营轴 = chars_by_faction 域非空
    防呆,误登角色名 → 域空 import 炸;注册表漂移防呆,先例 =
    _uniform_char_of_cost 的 ValueError);⑦ 随机装备支两查(类别名闭集:
    元素 ∈ EQUIPMENTS category 词集,越界 = 采样池必空构建期拒;类别过滤池非空,
    注册表漂移防呆)+ '星徽' 类别池独立非空闸(首例登记类别,防类别改名致
    首例登记池静默变空);⑧⑨ 即时装备支两查(首例 = 红钻贵族):⑧ 装备名漂移
    (逐名 ∈ EQUIPMENTS——发放写出库存里不存在的名字 = 假身份混进 equips,
    沿 ② 同思路;EQUIPMENTS 注册表在,可闭集校验;武装箱系不在装备注册表,
    误入本通道天然被拒);⑨ 装备/道具通道同名(同一 GiftGrant 内
    equips_immediate ∩ (items_immediate ∪ items_scheduled) = ∅,身份串行
    防呆,沿 ⑤ 同思路,防同卡误登记同名件);⑩ 开局替换防呆(首例 = 人才
    储备):replaces_opening_supply=True 而角色支(chars_immediate ∪
    chars_random_immediate)全空 = 「清空开局不发」怪卡,登记残缺拒收
    (替换必须产出替代者,开局补给物 = 角色,道具/装备支不算)。
    """
    orphans = [n for n in ENV_GIFTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(f"ENV_GIFTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    _equip_cats = frozenset(e.category for e in EQUIPMENTS.values())
    for _name, _grant in ENV_GIFTS.items():
        _drift = [c for c in (*_grant.chars_immediate,
                              *(c for c, _note in _grant.chars_conditional))
                  if c not in CHARACTER_ROSTER]
        if _drift:
            raise ValueError(
                f"ENV_GIFTS 角色名漂移({_name!r} 注册表无此人,版本改名?):{_drift}")
        for _node_key, _item in _grant.items_scheduled:
            if not _SCHEDULED_NODE_KEY_RE.fullmatch(_node_key):
                raise ValueError(
                    f"ENV_GIFTS 定时节点键格式({_name!r}):{_node_key!r} "
                    f"非 '位-轮'(位面1-3/位面内轮1-9)")
            if _item in CHARACTER_ROSTER:
                raise ValueError(
                    f"ENV_GIFTS 定时道具名进角色注册表({_name!r}):"
                    f"{_item!r}(道具/角色通道串行防呆)")
        for _spec in _grant.chars_random_immediate:
            _validate_random_char_spec('ENV_GIFTS', _name, _spec)
        for _cat in _grant.equips_random_immediate:
            if _cat not in _equip_cats:
                raise ValueError(
                    f"ENV_GIFTS 随机装备类别名({_name!r}):{_cat!r} "
                    f"不在 EQUIPMENTS category 词集(越界 = 采样池必空):"
                    f"{sorted(_equip_cats)}")
            if not equips_by_category(_cat):
                raise ValueError(
                    f"ENV_GIFTS 随机装备池空({_name!r}):"
                    f"category={_cat!r} 过滤后无装备(注册表漂移?)")
        for _eq in _grant.equips_immediate:
            if _eq not in EQUIPMENTS:
                raise ValueError(
                    f"ENV_GIFTS 装备名漂移({_name!r} 注册表无此装备,"
                    f"版本改名?):{_eq!r}")
        _equip_item_clash = (set(_grant.equips_immediate)
                             & {*_grant.items_immediate,
                                *(item for _node_key, item
                                  in _grant.items_scheduled)})
        if _equip_item_clash:
            raise ValueError(
                f"ENV_GIFTS 装备/道具通道同名({_name!r}):"
                f"{sorted(_equip_item_clash)}(身份串行防呆)")
        if _grant.replaces_opening_supply and not _grant.chars_immediate \
                and not _grant.chars_random_immediate:
            raise ValueError(
                f"ENV_GIFTS 开局替换无产出({_name!r}):"
                f"replaces_opening_supply=True 而角色支全空"
                f"(清空开局不发 = 登记残缺)")
        if not _grant.chars_immediate and not _grant.chars_conditional \
                and not _grant.items_immediate and not _grant.items_scheduled \
                and not _grant.chars_random_immediate \
                and not _grant.equips_random_immediate \
                and not _grant.equips_immediate:
            raise ValueError(
                f"ENV_GIFTS 空发放集:{_name!r} 即时角色/条件角色/即时道具/"
                f"定时道具/随机角色/随机装备/即时装备全空,数据残缺")
    if not equips_by_category('星徽'):
        raise ValueError(
            "ENV_GIFTS 随机装备类别池空:'星徽' 类别过滤后无装备"
            "(首例登记类别,类别改名致池静默变空 = 注册表漂移)")
    _overlap = set(ENV_GIFTS) & set(ENV_ECONOMY)
    if _overlap:
        raise ValueError(
            f"ENV_GIFTS ∩ ENV_ECONOMY 非空(单一环境只落一个估值结构):{sorted(_overlap)}")


_validate_env_gifts()


# ===== 策略卡具名发放登记表(白名单制)=====
# 底册 = 双母体对账(86 条):①STRATEGY_BINDINGS 角色绑定条目 ∩ 「获得…直读」
# 形态机械预筛(68 条白得 + 11 条顾问);②全表效果文本反扫(「获得…roster 名」)
# 补网 4 条(龙虎兄弟狸/佩佩驾到/艾丝妲的猛犬!/招财狗——无角色绑定的直读
# 发放,佩佩 ∈ CHARACTER_ROSTER);③箱腿 3 条(战术义眼++/保守派/快请专家·彩,
# 「获得…【进阶武装箱】」占席道具直读,迭代 2026-09-24-advanced-armory-box)。
# 发放角色归属 = 效果原文机制事实,宪法五
# 第②类判据留 kernel(与 ENV_GIFTS 留 kernel 同判据);「档→分」映射与
# advisor 折减 = 策略层 gift_value.grant_gift_value(消费位 =
# strategies/impl/mandate_v1/invest_strategy.py)。逐条登记判据(「获得…
# 角色名/占席道具」直读才入册、顾问型 advisor=True、即时/条件分档 = 效果原文时点
# 语义;roster-外目标与空名发放自动排除)= 29 号稿 §2.3;键 = 注册表规范
# 名(canon),与 INVESTMENT_STRATEGIES 同键空间。
STRATEGY_GRANTS: dict[str, GiftGrant] = {
    # —— 顾问型 11 条(advisor=True,付费期权沿 ×0.5 折减)——
    # 效果原文 = 「获得专家顾问【X】,并使其在本局游戏中加入商店」,与
    # env 批特邀专家完全同构的付费购买期权语义
    '停云顾问': GiftGrant(chars_immediate=('停云',), advisor=True),
    '加拉赫顾问': GiftGrant(chars_immediate=('加拉赫',), advisor=True),
    '战术专家:佩拉': GiftGrant(chars_immediate=('佩拉',), advisor=True),
    '潜行专家:貊泽': GiftGrant(chars_immediate=('貊泽',), advisor=True),
    '琼玉专家:青雀': GiftGrant(chars_immediate=('青雀',), advisor=True),
    '调饮专家:加拉赫': GiftGrant(chars_immediate=('加拉赫',), advisor=True),
    '贸易专家:停云': GiftGrant(chars_immediate=('停云',), advisor=True),
    '锻冶专家:刃': GiftGrant(chars_immediate=('刃',), advisor=True),
    '领航专家:姬子': GiftGrant(chars_immediate=('姬子',), advisor=True),
    '骇客专家:银狼': GiftGrant(chars_immediate=('银狼',), advisor=True),
    '摸个鱼吧I': GiftGrant(chars_immediate=('青雀',), advisor=True),
    # —— 白得型 72 条(绑定母体 68 + 反扫补网 4)——
    # 星徽单件族(金):「获得1个【X星徽】,和1个【角色】」即时直读
    '仙舟星徽': GiftGrant(chars_immediate=('藿藿',)),
    '减益星徽': GiftGrant(chars_immediate=('黄泉',)),
    '击破星徽': GiftGrant(chars_immediate=('阮·梅',)),
    '列车同行星徽': GiftGrant(chars_immediate=('丹恒·饮月',)),
    '命运圣杯星徽': GiftGrant(chars_immediate=('远坂凛',)),
    '夜之半神星徽': GiftGrant(chars_immediate=('万敌',)),
    '战技点星徽': GiftGrant(chars_immediate=('丹恒·饮月',)),
    '护盾星徽': GiftGrant(chars_immediate=('砂金',)),
    '持续伤害星徽': GiftGrant(chars_immediate=('卡芙卡',)),
    '星间旅人星徽': GiftGrant(chars_immediate=('银枝',)),
    '昼之半神星徽': GiftGrant(chars_immediate=('风堇',)),
    '欢愉星徽': GiftGrant(chars_immediate=('绯英',)),
    '治疗星徽': GiftGrant(chars_immediate=('风堇',)),
    '燃血星徽': GiftGrant(chars_immediate=('万敌',)),
    '狼狩星徽': GiftGrant(chars_immediate=('椒丘',)),
    '盛会之星星徽': GiftGrant(chars_immediate=('花火',)),
    '群攻星徽': GiftGrant(chars_immediate=('翡翠',)),
    '能量星徽': GiftGrant(chars_immediate=('星期日',)),
    '追击星徽': GiftGrant(chars_immediate=('飞霄',)),
    '量子同频星徽': GiftGrant(chars_immediate=('希儿',)),
    '贝洛伯格星徽': GiftGrant(chars_immediate=('希儿',)),
    '银河学者星徽': GiftGrant(chars_immediate=('艾丝妲',)),
    # 星徽套组族(棱彩):「获得1个【X星徽】,和1个【角色】,以及1个【装备】」
    '仙舟星徽套组': GiftGrant(chars_immediate=('藿藿',)),
    '减益星徽套组': GiftGrant(chars_immediate=('黄泉',)),
    '击破星徽套组': GiftGrant(chars_immediate=('阮·梅',)),
    '列车同行星徽套组': GiftGrant(chars_immediate=('丹恒·饮月',)),
    '夜之半神星徽套组': GiftGrant(chars_immediate=('万敌',)),
    '战技点星徽套组': GiftGrant(chars_immediate=('丹恒·饮月',)),
    '护盾星徽套组': GiftGrant(chars_immediate=('砂金',)),
    '持续伤害星徽套组': GiftGrant(chars_immediate=('卡芙卡',)),
    '星间旅人星徽套组': GiftGrant(chars_immediate=('银枝',)),
    '昼之半神星徽套组': GiftGrant(chars_immediate=('风堇',)),
    '治疗星徽套组': GiftGrant(chars_immediate=('风堇',)),
    '燃血星徽套组': GiftGrant(chars_immediate=('万敌',)),
    '狼狩星徽套组': GiftGrant(chars_immediate=('椒丘',)),
    '盛会之星星徽套组': GiftGrant(chars_immediate=('花火',)),
    '群攻星徽套组': GiftGrant(chars_immediate=('翡翠',)),
    '能量星徽套组': GiftGrant(chars_immediate=('星期日',)),
    '追击星徽套组': GiftGrant(chars_immediate=('飞霄',)),
    '追击星徽套组(二)': GiftGrant(chars_immediate=('飞霄',)),
    '量子同频星徽套组': GiftGrant(chars_immediate=('希儿',)),
    '贝洛伯格星徽套组': GiftGrant(chars_immediate=('希儿',)),
    '银河学者星徽套组': GiftGrant(chars_immediate=('艾丝妲',)),
    # 阵容专属机制强化族:「获得…【角色】」即时直读
    '人在旅途': GiftGrant(chars_immediate=('绯英', '银枝')),
    '借力打力': GiftGrant(chars_immediate=('黑塔', '缇宝')),
    '偶像经济': GiftGrant(chars_immediate=('火花',)),
    '双人舞': GiftGrant(chars_immediate=('千冶·刃', '卡芙卡')),
    '双龙会': GiftGrant(chars_immediate=('丹恒·腾荒', '丹恒·饮月')),
    '梦境大舞台': GiftGrant(chars_immediate=('花火',)),
    '月光宝盒': GiftGrant(chars_immediate=('赛飞儿', '万敌')),
    '摸个鱼吧II': GiftGrant(chars_immediate=('青雀',)),
    '摸个鱼吧III': GiftGrant(chars_immediate=('青雀',)),
    '燃起来了': GiftGrant(chars_immediate=('万敌', '千冶·刃')),
    '赞美太阳': GiftGrant(chars_immediate=('那刻夏',)),
    '装备党': GiftGrant(chars_immediate=('椒丘', '飞霄')),
    '读博深造': GiftGrant(chars_immediate=('艾丝妲', '阮·梅')),
    '超充站': GiftGrant(chars_immediate=('阿格莱雅', '藿藿')),
    '量子力学': GiftGrant(chars_immediate=('希儿',)),
    '钢铁美学': GiftGrant(chars_immediate=('希儿',)),
    # 兼即时腿与条件腿(条件腿 = 「获得3星【黑塔】时获得【大黑塔】」再得);
    # 216 张【黑塔】入商店系可购买供给非发放,不入册
    '黑塔纪元': GiftGrant(
        chars_immediate=('大黑塔',),
        chars_conditional=(('大黑塔', '你获得3星【黑塔】时获得【大黑塔】'),),
    ),
    # 本姑娘就是罗刹:首句「获得2星【三月七】」即时;「化身【罗刹】」系
    # 变身机制非发放,不入册
    '本姑娘就是罗刹': GiftGrant(chars_immediate=('三月七',)),
    # 白衣伙伴:「获得【白厄】」即时 +「3个节点后获得【星期日】」条件
    '白衣伙伴': GiftGrant(
        chars_immediate=('白厄',),
        chars_conditional=(('星期日', '3个节点后获得'),),
    ),
    # 盗用身份:「进入第二位面的首领节点时」条件发放【火花】;「1个【开拓者】」
    # 腿开拓者 ∉ CHARACTER_ROSTER 排除
    '盗用身份': GiftGrant(
        chars_conditional=(('火花', '进入第二位面的首领节点时'),),
    ),
    # 砂里淘金:「合成2星2费角色时」条件发放
    '砂里淘金': GiftGrant(
        chars_conditional=(('砂金', '合成2星2费角色时'),),
    ),
    # 迷之旅人:两腿均条件(激活4巡海游侠时 2星黄泉/下一奖励节点 波提欧)
    '迷之旅人': GiftGrant(
        chars_conditional=(
            ('黄泉', '激活4巡海游侠时获得2星黄泉'),
            ('波提欧', '进入下一个奖励节点时'),
        ),
    ),
    # 轮回不止:「获得【白厄】」即时;「进入第二/三位面时再获得一次」系
    # 同角色重复发放腿,角色集不变不入条件集
    '轮回不止': GiftGrant(chars_immediate=('白厄',)),
    # 飞光双件:「获得【彦卿】和【景元】」/「获得【镜流】和特殊的1费【景元】」
    '飞光·传剑': GiftGrant(chars_immediate=('彦卿', '景元')),
    '飞光·映月': GiftGrant(chars_immediate=('镜流', '景元')),
    # —— 反扫补网 4 条(无角色绑定的「获得…」直读发放)——
    '龙虎兄弟狸': GiftGrant(chars_immediate=('狸小龙', '狸小虎')),
    '佩佩驾到': GiftGrant(chars_immediate=('佩佩',)),
    '艾丝妲的猛犬！': GiftGrant(chars_immediate=('佩佩',)),
    '招财狗': GiftGrant(chars_immediate=('佩佩',)),
    # —— 箱腿型 3 条(占席道具发放;效果原文对账 id = cw_invest_data.
    # PLAZA_AUGMENTS:战术义眼++ 350403/保守派 351501/快请专家·彩 360201;
    # 「获得1个/一件【进阶武装箱】」直读,数量 = 元素重复次数)——
    # 三卡的战斗被动腿(战术义眼++能量恢复/保守派伤害减免/快请专家·彩能量
    # 恢复)非「获得时点」效果,不属 GiftGrant 登记适用范围(归策略效果建模批);
    # 快请专家·彩只登记箱腿:好运令牌非占席道具(入 items 会错进
    # BENCH_ITEM_NAMES 被当占席道具,归消耗品域)、「获得2个【】」空括号腿
    # 数据源缺口禁猜——两腿查无登记即安静不写,真值归实机/数据源勘误。
    '战术义眼++': GiftGrant(items_immediate=('进阶武装箱',)),
    '保守派': GiftGrant(items_immediate=('进阶武装箱',)),
    '快请专家·彩': GiftGrant(items_immediate=('进阶武装箱',)),
}

# ===== 占席道具「名字→类别」映射桥 + 词表(BenchSlot 身份轴/类别轴一致性权威)=====
# 实机真值(2026-09-24 用户确认):占席道具与角色同款溢出语义——席满落溢出
# 席并阻断进入战斗。溢出位身份串(overflow_card)因此有两分:角色 char_id /
# 占席道具名。
# BENCH_ITEM_KINDS = 占席道具槽件「名字→类别」全量显式映射(用户裁定
# 2026-10-24:全量显式制,漏登 import 炸成可见,静默落错身份的治理劣于
# 响亮缺登记)。「全量」口径 = 授予通道占席道具(键集闭合 = 两张授予表
# items_* 通道道具名并集,_validate_bench_item_kinds 双向闭合校验承接原
# 派生式「新增授予自动覆盖」);观察专属来源(星徽秘典,tome)不经授予
# 通道,不入本表不入词表(豁免,名字一致性由识别双渲染注册表承载)。
# 词表 BENCH_ITEM_NAMES 只答「是不是占席道具」;本表答「是哪种」并兼任
# BenchSlot 身份轴(item)与类别轴(kind)的一致性权威:授予通道道具类槽
# 构造一律 item=<名> 且 kind=BENCH_ITEM_KINDS[<名>]。kind 合法值 =
# 'supply_box' | 'bookcard'。消费方:
# - cw_gain_chain._place_bench_item 落席本体/_build_pool 溢出占位:道具
#   身份禁造 Unit 假身份进合成素材组,槽件带名;
# - cw_action_report.sell_bench 溢出腿:卖牌腾槽入位按映射落带名槽件。
BENCH_ITEM_KINDS: dict[str, str] = {
    '简易武装箱': 'supply_box',
    '特权武装箱': 'supply_box',
    '进阶武装箱': 'supply_box',
    '专家邀请函': 'bookcard',
}

BENCH_ITEM_NAMES: frozenset[str] = frozenset(BENCH_ITEM_KINDS)

# 反扫候选闭集防线的排除/假阳性白名单(逐条记因;键必须在注册表):
# - 愚者恶作剧:概率变形发放(2/4 费卡概率变为【花火】/【火花】),无「获得」
#   字样,非直读发放;
# - 快请专家·金/彩:「获得1个【】/2个【】」空名不可具名(注册键各自独立);
# - 孪生姵姵:发放对象「姵姵」∉ CHARACTER_ROSTER(反扫命中的「佩佩」系
#   「和你的佩佩一模一样」对比句非发放);
# - 溜佩佩/溜佩佩+:「…佩佩会在你的后排逛街」系效果实现发放但无「获得」
#   直读引导(反扫窗口命中的「获得9/15金币」 govern 金币非佩佩)。
# 統一排除口径覆盖未来同类:roster-外目标与空名发放天然不产反扫命中,自动
# 排除不逐条记因;本白名单只收现存例外。
_STRATEGY_GRANTS_SCAN_EXCLUSIONS: dict[str, str] = {
    '愚者恶作剧': '概率变形发放、无「获得」字样',
    '快请专家·金': '「获得1个【】」空名不可具名',
    '快请专家·彩': '「获得2个【】」空名不可具名',
    '孪生姵姵': '发放对象姵姵不在 CHARACTER_ROSTER',
    '溜佩佩': '实发放但非「获得」引导(佩佩逛街句)',
    '溜佩佩+': '实发放但非「获得」引导(佩佩逛街句)',
}


def _scan_strategy_grant_candidates(window: int = 30) -> set[str]:
    """机械反扫:效果文本中「获得」后 window 字内出现 CHARACTER_ROSTER 名的
    全部策略卡名(候选闭集防线的数据面;window=30 覆盖「获得1个携带着3个
    永久附着星徽的【佩佩】」类长修饰直读形态)。"""
    hits: set[str] = set()
    for _name, _st in INVESTMENT_STRATEGIES.items():
        _start = 0
        while True:
            _idx = _st.effect.find('获得', _start)
            if _idx < 0:
                break
            _seg = _st.effect[_idx + len('获得'): _idx + len('获得') + window]
            if any(_c in _seg for _c in CHARACTER_ROSTER):
                hits.add(_name)
                break
            _start = _idx + 1
    return hits


def _validate_strategy_grants() -> None:
    """STRATEGY_GRANTS 构建校验(import 即炸;沿 _validate_env_gifts 先例):

    ① 孤儿键:键必须在 INVESTMENT_STRATEGIES(防版本更新改名/移除后静默
    失联);② 角色名漂移:发放角色(即时∪条件)必须在 CHARACTER_ROSTER;
    ③ 空发放集拒绝(即时角色/条件角色/即时道具/定时道具/随机角色/随机装备/
    即时装备全空 = 登记笔误,档位机器恒判 off;items 两通道沿 _validate_env_gifts
    同款并入——箱腿条目 chars 两通道空而 items_immediate 非空,合法;
    chars_random_immediate 同款并入——GiftGrant 两表共享,策略侧随机
    登记后继[二/三/四费援军族]首登记不因旧判定误炸;equips_random_immediate
    同款并入——两表共享同一理由,策略侧随机装备登记后继首登记不误炸;
    equips_immediate 同款并入——两表共享同一理由,策略侧具名装备登记后继
    首登记不误炸;装备名漂移校验仅在环境侧,_validate_env_gifts ⑧);
    ④ **反扫候选
    闭集防线**:机械反扫(「获得…roster 名」全表命中)候选集
    ⊆ STRATEGY_GRANTS ∪ 排除/假阳性白名单——新增「获得」直读发放卡漏登记
    即炸;白名单键孤儿同样炸(防记因指向已删卡后防线空转)。
    """
    orphans = [n for n in STRATEGY_GRANTS if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(f"STRATEGY_GRANTS 孤儿键(base 无此卡?):{sorted(orphans)}")
    for _name, _grant in STRATEGY_GRANTS.items():
        _drift = [c for c in (*_grant.chars_immediate,
                              *(c for c, _note in _grant.chars_conditional))
                  if c not in CHARACTER_ROSTER]
        if _drift:
            raise ValueError(
                f"STRATEGY_GRANTS 角色名漂移({_name!r} 注册表无此人,版本改名?):{_drift}")
        if not _grant.chars_immediate and not _grant.chars_conditional \
                and not _grant.items_immediate and not _grant.items_scheduled \
                and not _grant.chars_random_immediate \
                and not _grant.equips_random_immediate \
                and not _grant.equips_immediate:
            raise ValueError(
                f"STRATEGY_GRANTS 空发放集:{_name!r} 即时角色/条件角色/"
                f"即时道具/定时道具/随机角色/随机装备/即时装备全空,数据残缺")
    _wl_orphans = [n for n in _STRATEGY_GRANTS_SCAN_EXCLUSIONS
                   if n not in INVESTMENT_STRATEGIES]
    if _wl_orphans:
        raise ValueError(
            f"STRATEGY_GRANTS 反扫白名单孤儿键(注册表无此卡):{_wl_orphans}")
    _candidates = _scan_strategy_grant_candidates()
    _covered = set(STRATEGY_GRANTS) | set(_STRATEGY_GRANTS_SCAN_EXCLUSIONS)
    _leaks = _candidates - _covered
    if _leaks:
        raise ValueError(
            f"STRATEGY_GRANTS 反扫闭集破口(「获得…角色名」直读发放候选未登记"
            f"也未记因排除,新增发放卡漏登记?):{sorted(_leaks)}")


_validate_strategy_grants()


def _validate_bench_item_kinds() -> None:
    """占席道具映射桥双向闭合校验(import 即炸;沿 _validate_env_gifts 先例):

    ① 键集双向闭合:BENCH_ITEM_KINDS 键集 == 两张授予表(ENV_GIFTS/
    STRATEGY_GRANTS)items_* 通道道具名并集——少登 = 授予通道道具落席
    直查 KeyError 前置炸(漏登 import 炸成可见);多登 = 孤儿键炸(静默
    落错身份风险)。调用落 :func:`_validate_strategy_grants` 调用点同区
    (ENV_GIFTS/STRATEGY_GRANTS/BENCH_ITEM_KINDS 全部定义之后,import 序
    成立);② 值域封闭:逐值 ∈ {'supply_box', 'bookcard'}(防拼写漂移
    静默落空;观察专属 tome 豁免不在检域)。
    """
    granted: set[str] = set()
    for _grant in (*ENV_GIFTS.values(), *STRATEGY_GRANTS.values()):
        granted.update(_grant.items_immediate)
        granted.update(item for _node_key, item in _grant.items_scheduled)
    keys = set(BENCH_ITEM_KINDS)
    _missing = granted - keys
    if _missing:
        raise ValueError(
            f"BENCH_ITEM_KINDS 键集缺登(授予通道占席道具落席直查会 "
            f"KeyError,漏登 import 炸):{sorted(_missing)}")
    _orphans = keys - granted
    if _orphans:
        raise ValueError(
            f"BENCH_ITEM_KINDS 孤儿键(非授予通道道具,静默落错身份风险,"
            f"多登 import 炸):{sorted(_orphans)}")
    _bad_values = {n: k for n, k in BENCH_ITEM_KINDS.items()
                   if k not in ('supply_box', 'bookcard')}
    if _bad_values:
        raise ValueError(
            f"BENCH_ITEM_KINDS 值域越界(合法 = 'supply_box' | 'bookcard',"
            f"观察专属 tome 不在检域):{_bad_values}")


_validate_bench_item_kinds()


# ===== 环境品质改写注册表(白名单制)=====
# 品质改写型环境(时代 ×3 + 头彩/尾彩 + 银·金·彩 + 联席决策,恰 7 条)的池改写
# 事实登记。表外环境一律无条目,禁从效果原文自动猜装(ENV_ECONOMY/ENV_GIFTS
# 同款纪律)。两型两层拆分:层 E(基数,改写后取卡金流期望抬升
# ΔV)经 env_economy_value 单一入口分派(策略层 env_economy._pool_rewrite_
# value 驻策略层),
# 当前态恒 fail-closed——受限通道 μ_E 不随品质单调(银 3.31 > 金 2.42 实测),
# 直接入现金分会产出「白银时代>黄金时代」噪声序;层 E 转正准入门(全通道重算
# + 序一致性检验,详设 §2.2.2)经数据批判定未过,维持 fail-closed(判定依据
# = invest-env 迭代 layer-e-promotion-batch 详设,git 历史可溯);层 Q
# (定序残域,池内挑卡
# 与功能价值)= 零现金分维持(现金通道 fail-closed 即无值;
# 知识评估已对两半作过知识性净评),两层从不相加——
# 「层 E 有值时以现金分参与、无值时零兜底」,取两层各自标尺下结果的较优
# 呈现(标尺语义正本 = strategy-docs/28_invest_env_screen.md;层 E 语义
# = 策略层 env_economy._pool_rewrite_value docstring)。
# 数量通道(联席额外三选一/银金彩刷新 +2)与 A 类策略大师同口径:策略域
# 价值不折金不进层 E,字段只登记事实(详设 §2.2.4);执行消费端 = sim
# (联席挂点派生 JOINT_DECISION_EXTRA_SLOT;银金彩刷新 = 策略屏刷新呈现
# 与刷新世界腿,2026-10-19 用户裁定批接入)。
# 测试 = 测试仓 test_sim_offer.py(判据单点 + 名单 ⊆ ENV_POOL_REWRITE 一致性)
# 与 test_sim_backend.py(时代局全流程:彩虹/黄金/白银;头彩/尾彩 settled 定谳局)。
@dataclass(frozen=True)
class StrategyPoolRewrite:
    """投资环境的**策略池品质改写**结构(品质改写型估值;与 EnvEconomyEffect/GiftGrant
    同属 InvestmentEnv 的估值 schema 家族,落点集中本段避免触碰已交付段)。

    字段语义(值全部 = cw_invest_data 效果原文直读;效果原文对账 id 见
    ENV_POOL_REWRITE 各条注释):
    - rewrite_quality: 改写目标品质('棱彩'/'金'/'银');空 = 非品质全改写型
      (银·金·彩为 offer 结构改写、联席决策为数量通道,无层 E 语义)
    - rewrite_picks: 被改写的取卡序号,**坐标系 = 本局投资策略取卡全局序,
      1 基**(头彩效果原文点名「第一个投资策略」/尾彩点名「第三个投资策略」
      → 固定取卡集基数 3 的序数承载;
      时代 = (1,2,3) 全改写);取值时机 = 注册表登记期常量(效果原文直读,
      非执行期现读)
    - offer_structure: offer 结构改写语义标记('silver_gold_prism_slots' =
      银·金·彩三槽按位面对应品质);与 slot_qualities 同有同无(结构标记
      无数据 = 登记半残,建表闸拒);层 E 公式不消费,真值消费端 = sim
      改写判据(rewrite_slot_qualities_for_pick 槽位向量)
    - slot_qualities: offer 三槽品质按位承诺(**坐标系 = 投资界面卡槽
      物理排位,左→右 0..2**,与 CwActionRefreshInvestCardsParam.slots 同
      坐标系;取值时机 = 注册表登记期常量,非执行期现读);值 = 品质词集
      成员、长度恒 3(卡面「左、中、右」三槽);登记依据 = 用户裁定
      2026-10-19 卡面直读即真值(银·金·彩 id135),旧「实测 offer 金重仓」
      观察记录同裁定作废;槽位品质承诺跨逐卡刷新保持(卡面语义直读,
      刷新只换卡不换槽品质)
    - extra_pick_refreshes: 策略取卡刷新次数增量(银·金·彩 +2,策略屏逐卡
      免费刷新计数,cw_node_obs.read_invest_refresh_counts('strategy') 通道;
      数量通道登记,§2.2.4;消费端 = sim 策略屏刷新呈现与刷新世界腿
      (基准每卡 1 次 + 本增量;2026-10-19 用户裁定 sim 与实机一致提供
      刷新次数批接入);live 不经本字段——bot 读屏幕现值)
    - extra_strategy_offer_node: 额外策略三选一发生的挂点节点,**坐标系 =
      (位面, 轮次) 单点,两元各 1 基**(效果原文「X-Y 节点」= 位-轮读法,
      用户裁定 2026-10-16;依据与边界 = ENV_POOL_REWRITE 登记处注释);
      数量通道登记,执行消费端 = sim JOINT_DECISION_EXTRA_SLOT 派生;
      None = 无额外策略三选一
    - extra_strategy_grant_node: 额外策略**直接发放**发生的挂点节点,
      **坐标系与 extra_strategy_offer_node 同 = (位面, 轮次) 单点两元各
      1 基**(T-46 策略大师数量腿;直发非 offer 三选一,不复用 offer 字段
      ——offer = 三选一槽语义;同条目两字段互斥,结构闸校验);数量通道
      登记,执行消费端 = sim 直发发放事件(kernel 单一源,sim 派生查询);
      None = 无直接发放
    - difficulty_exempt: 敌人难度不随高品质策略提高(白银时代第二条效果;
      游戏【注·交叉核对】口径 = 白银 +0/黄金 +3/棱彩 +6 每拥有 1 个,
      docs/game/currency_war/research/economy.md 难度精确口径行——数值已登记
      不折金,难度→收益需战力/胜率建模属宪法禁域 00_framework §1.1,§2.2.3)
    - pending_notes: 效果原文歧义待办(单张改写型 offer 覆盖面歧义:三卡全改
      还是仅点名张)——pending 条目必填
      (_validate_env_pool_rewrite 构建闸,_validate_strategy_effects 先例
      同款);定谳 settled 条目亦以非空 notes 记录裁定时点与结论
    - rewrite_settled: rewrite_picks 登记的覆盖范围已定谳,sim 照登记逐序
      接入(部分改写型的定谳标记;全改写型 picks==(1,2,3) 结构形状即
      定谳,设 True 属冗余但不校验)
    """
    rewrite_quality: str = ''
    rewrite_picks: tuple[int, ...] = ()
    offer_structure: str = ''
    slot_qualities: tuple[str, ...] = ()
    extra_pick_refreshes: int = 0
    extra_strategy_offer_node: tuple[int, int] | None = None
    extra_strategy_grant_node: tuple[int, int] | None = None
    difficulty_exempt: bool = False
    pending_notes: str = ''
    rewrite_settled: bool = False


ENV_POOL_REWRITE: dict[str, StrategyPoolRewrite] = {
    # 效果原文对账 id(cw_invest_data.PLAZA_PORTALS):彩虹 110/黄金 111/白银 112/
    # 头彩 123/尾彩 124/银·金·彩 135/联席决策 122/策略大师 147
    '彩虹时代': StrategyPoolRewrite(rewrite_quality='棱彩', rewrite_picks=(1, 2, 3)),
    '黄金时代': StrategyPoolRewrite(rewrite_quality='金', rewrite_picks=(1, 2, 3)),
    # 白银时代第二效果「敌人难度不会由于选择高品质投资策略而提高」=
    # difficulty_exempt 如实登记(§2.2.3 适用范围声明:数值不折金,不产生分值)
    '白银时代': StrategyPoolRewrite(rewrite_quality='银', rewrite_picks=(1, 2, 3),
                                    difficulty_exempt=True),
    '头彩': StrategyPoolRewrite(
        rewrite_quality='棱彩', rewrite_picks=(1,), rewrite_settled=True,
        pending_notes='效果原文「第一个投资策略」为棱彩;覆盖面已定谳 = offer 级'
                      '改写(第 1 次取卡机会 3 张候选全棱彩),用户裁决 2026-10-16'
                      '确认;sim 照登记接入第 1 次取卡(rewrite_settled)'),
    '尾彩': StrategyPoolRewrite(
        rewrite_quality='棱彩', rewrite_picks=(3,), rewrite_settled=True,
        pending_notes='效果原文「第三个投资策略」为棱彩;覆盖面已定谳 = offer 级'
                      '改写(第 3 次取卡机会 3 张候选全棱彩),用户裁决 2026-10-16'
                      '确认;sim 照登记接入第 3 次取卡(rewrite_settled)'),
    # 银·金·彩 = offer 结构改写(三选项品质按槽位)+ 刷新 +2;槽位-品质映射
    # 已定谳 = 卡面直读即真值(用户裁定 2026-10-19;旧「实测 offer 金重仓」
    # 观察记录同裁定作废,不再作为建模依据)
    '银·金·彩': StrategyPoolRewrite(
        offer_structure='silver_gold_prism_slots',
        slot_qualities=('银', '金', '棱彩'), extra_pick_refreshes=2,
        pending_notes='槽位-品质映射定谳记录:三槽品质 = 银/金/彩按卡面槽位'
                      '(用户裁定 2026-10-19 卡面即真值;旧实测记录作废);'
                      '数量通道 = 策略屏逐卡刷新 +2'),
    # 联席决策 = 数量通道(2-6 节点一次额外投资策略三选一);与 A 类策略大师
    # 「额外取卡不计」同口径,价值由裸分承载(§2.2.4)
    # 执行消费端 = sim JOINT_DECISION_EXTRA_SLOT 派生(单一源,勘误/改值
    # 只改本登记处,sim 自动跟随);
    # 挂点候实机对账:7 局在场样本全部止步 P2r4 或更早,无一达 P2r6;
    # 实机流程语义(用户确认 2026-10-16):2-5 战斗结算确认后、备战开商店前,
    # 先呈现该额外三选一。
    '联席决策': StrategyPoolRewrite(extra_strategy_offer_node=(2, 6)),
    # 策略大师 = 数量通道(3-5 节点额外获得一个投资策略,id 147);纯事实
    # 登记不折金不进估值(表头注释现役口径),与 ENV_ECONOMY 同键共存 =
    # 互斥闸语义化豁免(_validate_env_pool_rewrite:仅估值语义字段非空
    # 条目禁交);
    # 执行消费端 = sim 直发发放事件(单一源,勘误/改值只改本登记处,
    # sim 派生查询自动跟随);
    # 挂点候实机对账:实机直发出现节点 ≠ 3-5 → 改本登记值一处(sim 自动
    # 跟随);
    # 形态 = 直接发一张随机投资策略(用户裁定 2026-10-26;远见先例形态,
    # 无选卡界面,登记注释 = 「3-5节点」位-轮单点,T-23 裁决 1 判例联动)。
    '策略大师': StrategyPoolRewrite(extra_strategy_grant_node=(3, 5)),
}


def _validate_env_pool_rewrite() -> None:
    """ENV_POOL_REWRITE 构建校验(import 即炸):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(沿 ENV_ECONOMY/ENV_GIFTS 先例,防版本
    更新改名/移除后静默失联);② 三注册表互斥收全(语义化,T-46 策略大师
    数量通道登记引入豁免):``set(ENV_POOL_REWRITE) ∩ set(ENV_GIFTS) = ∅``
    全量禁交;``∩ set(ENV_ECONOMY)`` 收窄为**估值语义字段非空的条目**禁交
    (``rewrite_quality`` 或 ``offer_structure`` 非空——闸防的是估值双通道
    叠加:前者是层 E 估值公式实际消费字段,后者是池结构语义字段、层 E 转正
    后即第二估值通道,一并禁交取保守侧;纯数量事实条目〔仅挂点/刷新/
    难度豁免字段〕放行,未来新数量通道卡免逐个加白);③ 结构完备:改写目标
    品质与被改写取卡序要么齐备要么俱无(半残 = 登记笔误,层 E 公式不可算);
    结构标记 offer_structure 与槽位数据 slot_qualities 同有同无,槽位向量
    长度恒 3、值在策略品质词集、与品质改写型互斥(双型不同条共存);④ pending
    必填:单张改写型(有点名取卡序但非全改写,offer 覆盖面歧义)或 offer 结构
    改写型(槽位语义歧义)必须写保守支 notes(_validate_strategy_effects
    「pending 条目必须写保守支 notes」先例同款);⑤ 挂点形(T-46 扩展,
    offer/grant 两字段同闸):extra_strategy_offer_node /
    extra_strategy_grant_node 非 None 时两元各 ≥1、位面 ∈ PLANE_NODE_TABLES
    且轮次 ≤ 该位面序列长(坐标系 = (位面, 轮次) 单点两元各 1 基;不在表/
    超长 = 登记笔误,import 期炸,防 sim 挂点比对静默恒 False);同条目两
    挂点字段皆非 None → 炸(一环境一形态:offer 三选一与直接发互斥);
    ⑥ settled 定谳闸:rewrite_settled=True 且 rewrite_quality 为空 → 炸
    (settled 标记只对品质改写型有意义,防登记错位);⑦ 空条目闸:条目
    七结构字段全默认(rewrite_quality/rewrite_picks/offer_structure/
    extra_pick_refreshes/extra_strategy_offer_node/extra_strategy_grant_node/
    difficulty_exempt 皆取默认值)→ 炸(无任何语义的登记笔误形状;数量
    通道挂点被误清 None 即落此闸——检查置于⑥后:仅 rewrite_settled 单独
    非默认的条目归⑥现役闸网,不抢本闸报错形态)。
    """
    orphans = [n for n in ENV_POOL_REWRITE if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(f"ENV_POOL_REWRITE 孤儿键(base 无此环境?):{sorted(orphans)}")
    _overlap_gifts = set(ENV_POOL_REWRITE) & set(ENV_GIFTS)
    if _overlap_gifts:
        raise ValueError(
            f"ENV_POOL_REWRITE ∩ ENV_GIFTS 非空(单一环境只落一个估值结构):"
            f"{sorted(_overlap_gifts)}")
    _overlap_econ = [n for n in set(ENV_POOL_REWRITE) & set(ENV_ECONOMY)
                     if ENV_POOL_REWRITE[n].rewrite_quality
                     or ENV_POOL_REWRITE[n].offer_structure]
    if _overlap_econ:
        raise ValueError(
            f"ENV_POOL_REWRITE ∩ ENV_ECONOMY 非空(估值语义条目只落一个估值"
            f"结构,rewrite_quality/offer_structure 非空者不得与 ENV_ECONOMY "
            f"同键):{sorted(_overlap_econ)}")
    for _name, _rw in ENV_POOL_REWRITE.items():
        if bool(_rw.rewrite_quality) != bool(_rw.rewrite_picks):
            raise ValueError(
                f"ENV_POOL_REWRITE 结构半残:{_name!r} rewrite_quality="
                f"{_rw.rewrite_quality!r} 与 rewrite_picks={_rw.rewrite_picks!r}"
                f"须同有同无(层 E 公式不可算)")
        if bool(_rw.offer_structure) != bool(_rw.slot_qualities):
            raise ValueError(
                f"ENV_POOL_REWRITE 结构半残:{_name!r} offer_structure="
                f"{_rw.offer_structure!r} 与 slot_qualities="
                f"{_rw.slot_qualities!r}须同有同无(结构标记无槽位数据 = "
                f"判据不可算)")
        if _rw.slot_qualities:
            if _rw.rewrite_quality:
                raise ValueError(
                    f"ENV_POOL_REWRITE 双型互斥:{_name!r} 槽位向量型与品质"
                    f"改写型不同条共存(rewrite_quality={_rw.rewrite_quality!r})")
            if len(_rw.slot_qualities) != 3:
                raise ValueError(
                    f"ENV_POOL_REWRITE 槽位向量长度:{_name!r} "
                    f"slot_qualities={_rw.slot_qualities!r} 须恒 3"
                    f"(卡面「左、中、右」三槽)")
            _quality_vocab = {s.rarity for s in INVESTMENT_STRATEGIES.values()}
            _bad = [q for q in _rw.slot_qualities if q not in _quality_vocab]
            if _bad:
                raise ValueError(
                    f"ENV_POOL_REWRITE 槽位品质漂移:{_name!r} "
                    f"{_bad} 不在策略品质词集(注册表漂移?):"
                    f"{sorted(_quality_vocab)}")
        _partial_rewrite = bool(_rw.rewrite_quality) and _rw.rewrite_picks != (1, 2, 3)
        if (_partial_rewrite or _rw.offer_structure) and not _rw.pending_notes:
            raise ValueError(
                f"ENV_POOL_REWRITE pending 条目必须写保守支 notes:{_name!r}"
                f"(offer 覆盖面/槽位语义歧义挂账)")
        # 挂点结构闸(T-46 扩展:offer/grant 两字段同闸同报错形态)+
        # 双挂点互斥(一环境一形态)
        if (_rw.extra_strategy_offer_node is not None
                and _rw.extra_strategy_grant_node is not None):
            raise ValueError(
                f"ENV_POOL_REWRITE 双挂点互斥:{_name!r} "
                f"extra_strategy_offer_node={_rw.extra_strategy_offer_node}"
                f" 与 extra_strategy_grant_node="
                f"{_rw.extra_strategy_grant_node} 不得同条目共存"
                f"(一环境一形态:三选一与直接发互斥)")
        for _node_field in ('extra_strategy_offer_node',
                            'extra_strategy_grant_node'):
            _node = getattr(_rw, _node_field)
            if _node is not None:
                _plane, _round = _node
                if _plane not in PLANE_NODE_TABLES:
                    raise ValueError(
                        f"ENV_POOL_REWRITE 挂点位面不在节点真值表:{_name!r} "
                        f"{_node_field}={_node}(登记笔误?)")
                if not 1 <= _round <= len(PLANE_NODE_TABLES[_plane]):
                    raise ValueError(
                        f"ENV_POOL_REWRITE 挂点轮次超位面节点数:{_name!r} "
                        f"{_node_field}={_node}(位面 {_plane} 序列长 "
                        f"{len(PLANE_NODE_TABLES[_plane])},登记笔误?)")
        if _rw.rewrite_settled and not _rw.rewrite_quality:
            raise ValueError(
                f"ENV_POOL_REWRITE settled 定谳闸:{_name!r} rewrite_settled="
                f"True 而 rewrite_quality 空(settled 只对品质改写型有意义,"
                f"登记错位)")
        # 空条目闸(T-46;置 settled 闸后:仅 rewrite_settled 单独非默认的
        # 条目归 settled 闸网,七结构字段全默认才算「无任何语义的登记笔误」)
        if (_rw.rewrite_quality == '' and _rw.rewrite_picks == ()
                and _rw.offer_structure == '' and _rw.extra_pick_refreshes == 0
                and _rw.extra_strategy_offer_node is None
                and _rw.extra_strategy_grant_node is None
                and not _rw.difficulty_exempt):
            raise ValueError(
                f"ENV_POOL_REWRITE 空条目:{_name!r} 七结构字段全默认"
                f"(无任何语义的登记笔误;数量通道挂点被误清即落此闸)")


_validate_env_pool_rewrite()


# ===== 环境连胜触发发放注册表(
# details/env-conditional-grant.md §2;白名单制)=====
# 「条件达成的世界发放」首例登记:键 = 环境规范名,值 = (连胜阈值,发放装备名)。
# 表外环境一律无条目,禁从效果原文自动猜装(ENV_ECONOMY/ENV_GIFTS 同款纪律)。
# 消费面 = kernel/cw_env_grants.check_env_streak_grants(触发检查单一源,
# live/sim 结算接线都调它);表只收「连胜触发器」形状,升级类条件卡
# (钻石商人等)触发点各不相同,各建各表不并入本表(总纲「明确不解决」)。
ENV_STREAK_GRANTS: dict[str, tuple[int, str]] = {
    # 本局首次 5 连胜 → 财富宝钻(id 104 原文直读,cw_invest_data PlazaPortal('104'))
    '深井角斗场': (5, '财富宝钻'),
}


def _validate_env_streak_grants() -> None:
    """ENV_STREAK_GRANTS 构建校验(import 即炸;沿 _validate_env_ore_grants
    先例,details/env-conditional-grant.md §2):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 装备名漂移:发放装备必须在 EQUIPMENTS(版本改名不静默——发放写出
    库存里不存在的名字 = 假身份混进 equips);
    ③ 阈值形:连胜阈值 ≥ 1 的 int(≤0 = 条件永真,使「本局首次」一次性
    守卫在任何结算即刻触发,登记笔误前置可见)。
    """
    orphans = [n for n in ENV_STREAK_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_STREAK_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, (_threshold, _equip) in ENV_STREAK_GRANTS.items():
        if _equip not in EQUIPMENTS:
            raise ValueError(
                f"ENV_STREAK_GRANTS 装备名漂移({_n!r} 注册表无此装备,"
                f"版本改名?):{_equip!r}")
        if not isinstance(_threshold, int) or isinstance(_threshold, bool) \
                or _threshold < 1:
            raise ValueError(
                f"ENV_STREAK_GRANTS 阈值形({_n!r}):须为 ≥1 的 int,"
                f"现值 {_threshold!r}")


_validate_env_streak_grants()


# ===== 环境刷新次数触发发放注册表(二手市场;白名单制)=====
# **世界发放域**(条件达成的世界发放第二例,ENV_STREAK_GRANTS 同族):
# 键 = 环境规范名,值 = (计数键,阈值,金,装备名可空)。装备可空 =
# 金-only 触发器形状(长线利好族复用面)。表外环境一律无条目,
# 禁从效果原文自动猜装(ENV_ECONOMY/ENV_GIFTS 同款纪律)。
# 消费面 = kernel/cw_env_grants.check_env_refresh_grants(触发检查
# 单一源,唯一调用点 = 刷新上报函数尾部)。
# **表间豁免声明**(ENV_ORE_GRANTS 同款):本表键与 ENV_ECONOMY 共存
# (二手市场两表同时已登记),不参与 ENV_POOL_REWRITE 校验收的「单一
# 环境只落一个估值结构」三表互斥——本表条目非效果牌面,登记即常驻
# 触发器;正确性代之以与估值面的双源同值校验(见
# _validate_env_refresh_grants 第⑤条)。与 ENV_STREAK_GRANTS 两个世界
# 发放表可同键并存(某卡兼有两种触发):done 键 = (env,条件键) 带
# 条件键维度,语义无冲突。
ENV_REFRESH_GRANTS: dict[str, tuple[str, int, int, str | None]] = {
    # 商店刷新 20 次后 +30 金 + 员工投影仪(id 106 原文直读,
    # cw_invest_data PlazaPortal('106') desc「商店刷新20次后,获得30金币
    # 和【员工投影仪】」);
    # 计数域 = 全量(REFRESH_TOTAL):desc 无「花费金币」限定词,与
    # 长线利好 id 120(PlazaPortal('120'))desc 显式「花费金币进行30次
    # 刷新」构成官方文本自带的两域对照。
    '二手市场': (CounterKey.REFRESH_TOTAL, 20, 30, '员工投影仪'),
    # 花费金币刷新 30 次后 +20 金,之后本局刷价 2→1(id 120 原文直读,
    # PlazaPortal('120'))。计数域 = 付费(REFRESH_PAID):desc 显式
    # 「花费金币」限定词,与二手市场(无限定词→全量域)构成官方文本
    # 两域对照。装备腿 None = 金-only(T-7 预留形状,登记表注释点名
    # 本卡复用面);改价腿不在本表——live = 观察通道
    # (cw_shop_refresh_obs 标价 reader 采真),sim = 开店呈现经
    # cw_economy.world_shop_refresh_cost 现算渲染(两腿阈值同出卡面
    # 同一句「30 次」,构建校验⑥跨锁同值)。
    '长线利好': (CounterKey.REFRESH_PAID, 30, 20, None),
}


def _validate_env_refresh_grants() -> None:
    """ENV_REFRESH_GRANTS 构建校验(import 即炸;沿 _validate_env_ore_grants
    / _validate_env_streak_grants 先例):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 计数键闭集:须为 CounterKey.REFRESH_TOTAL / REFRESH_PAID 之一
    (计数读取按键分支,闭集外无读口);
    ③ 值形:阈值与金均须 ≥1 的 int(bool 排除——isinstance(bool, int)
    为真,0/False/1/True 形混入 = 登记笔误,前置可见);
    ④ 装备名漂移:装备腿非 None 时必须在 EQUIPMENTS(发放写出库存里
    不存在的名字 = 假身份混进 equips);
    ⑤ 双源同值:同环境在 ENV_ECONOMY 有 gold_after_refreshes 时须与
    (阈值,金) 逐位相等——世界面与估值面同出卡面(id 106),任一侧
    单独改数即失同步,构建期炸(先例 = _validate_env_ore_grants ③;
    估值域字段演化时本条随迁);
    ⑥ 跨锁同值:同环境在 ENV_ECONOMY 有 refresh_cost_after 时,其
    阈值须与本表阈值逐位相等——改价腿(sim 渲染 helper 读该字段)
    与发放腿(本表)同出卡面同一句「30 次刷新后」,两表独立可编辑,
    单侧改数静默漂移 = sim 翻价早于发放(与校验⑤同理由)。
    """
    orphans = [n for n in ENV_REFRESH_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_REFRESH_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, (_key, _threshold, _gold, _equip) in ENV_REFRESH_GRANTS.items():
        if _key not in (CounterKey.REFRESH_TOTAL, CounterKey.REFRESH_PAID):
            raise ValueError(
                f"ENV_REFRESH_GRANTS 计数键闭集外({_n!r}):"
                f"须为 CounterKey.REFRESH_TOTAL/REFRESH_PAID 之一,"
                f"现值 {_key!r}")
        for _label, _val in (('阈值', _threshold), ('金', _gold)):
            if not isinstance(_val, int) or isinstance(_val, bool) or _val < 1:
                raise ValueError(
                    f"ENV_REFRESH_GRANTS 值形({_n!r} {_label}):"
                    f"须为 ≥1 的 int,现值 {_val!r}")
        if _equip is not None and _equip not in EQUIPMENTS:
            raise ValueError(
                f"ENV_REFRESH_GRANTS 装备名漂移({_n!r} 注册表无此装备,"
                f"版本改名?):{_equip!r}")
        _econ = ENV_ECONOMY.get(_n)
        _src = tuple(getattr(_econ, 'gold_after_refreshes', ()) or ())
        if _src and _src != (_threshold, _gold):
            raise ValueError(
                f"ENV_REFRESH_GRANTS 双源失同步({_n!r}):ENV_ECONOMY."
                f"gold_after_refreshes={_src} ≠ 本表 ({_threshold}, {_gold})"
                f"(世界面与估值面同出卡面,失同步即构建期炸)")
        _cost = tuple(getattr(_econ, 'refresh_cost_after', ()) or ())
        if _cost and _cost[0] != _threshold:
            raise ValueError(
                f"ENV_REFRESH_GRANTS 跨锁失同步({_n!r}):ENV_ECONOMY."
                f"refresh_cost_after 阈值 {_cost[0]} ≠ 本表阈值 {_threshold}"
                f"(改价腿与发放腿同出卡面同一句「刷新阈值」,单侧改数 = "
                f"sim 翻价早于发放,失同步即构建期炸)")


_validate_env_refresh_grants()


# ===== 首领节点周期发放白名单(劳务派遣合同腿2;白名单制)=====
# **世界发放域**(条件达成的世界发放第三表,ENV_STREAK_GRANTS/ENV_REFRESH_
# GRANTS 同族):键 = 环境规范名,值 = 集合语义(现役无登记值,形态沿
# ENV_NODE_SUPPLY_BEFORE_BOSS 先例,cw_node_schedule)。表外环境一律无
# 条目,禁从效果原文自动猜装(ENV_ECONOMY/ENV_GIFTS 同款纪律)。
# 发放规则 = 腿1 绑定(done 条件键 'star_grant#<名>',登记于本卡在
# ENV_GIFTS 的即时腿)+ 固定每首领节点 1 个 1★ 角色;触发函数 =
# kernel/cw_env_grants.check_env_boss_grants(周期性,done 键带节点坐标)。
# **与估值三表的同键并存 = 本卡新立形态**(本卡腿1 归 ENV_GIFTS、腿2 归
# 本表,各表各腿、键语义无冲突):「世界发放表↔ENV_ECONOMY 可并存」的
# 现役豁免声明原辖 ENV_ORE/ENV_STREAK/ENV_REFRESH 与估值面的关系,不直接
# 覆盖估值三表∩世界发放表,故此处显式声明而非引先例。
ENV_BOSS_GRANTS: frozenset[str] = frozenset({'劳务派遣合同'})


def _validate_env_boss_grants() -> None:
    """ENV_BOSS_GRANTS 构建校验(import 即炸;沿 _validate_env_streak_grants
    先例):键 ⊆ INVESTMENT_ENVS(孤儿键,防版本更新改名/移除后静默失联)。
    与 ENV_GIFTS 同键 = 合法形态(两表同键各表各腿,见上区块注释显式
    声明),无反例校验。"""
    orphans = [n for n in ENV_BOSS_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_BOSS_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")


_validate_env_boss_grants()


# ===== 合并升星触发发放注册表(量子同频契约;白名单制)=====
# **世界发放域**(条件达成的世界发放第四表,ENV_STREAK_GRANTS/ENV_REFRESH_
# GRANTS/ENV_BOSS_GRANTS 同族):键 = 环境规范名,值 = (触发角色集, 发放池)
# 二元组。语义 = 持有该环境期间,触发角色集内任一角色每完成一级 3 合 1
# 升星,从发放池随机获得 1 个角色(1★ 先验,晶矿 CHAR_DROP_STAR 同句式;
# 逐级触发判例 = 该迭代裁定记录:级联 1★→2★→3★ = 两次发放,触发者星级
# 不限)。表外环境一律无条目,禁从效果原文自动猜装(ENV_ECONOMY/ENV_GIFTS
# 同款纪律)。消费面 = kernel/cw_env_grants.check_env_merge_grants(触发
# 检查单一源,事件携带事实无 done 标记;四发火点 = 买牌上报/补给单位腿/
# 晶矿角色腿/获得链顶层)。
# **表间豁免声明**(ENV_BOSS_GRANTS 同款显式声明):本表键与 ENV_GIFTS
# 共存 = 合法形态(两表同键各表各域——ENV_GIFTS 的 chars_conditional 辖
# 估值域档位机器,本表辖世界发放,各表各域),与 ENV_ECONOMY 无 ∩ 冲突。
ENV_MERGE_GRANTS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # 花火和缇宝升星时,随机获得【符玄】或【希儿】(id 125 原文直读,
    # cw_invest_data PlazaPortal('125'))
    '量子同频契约': (('花火', '缇宝'), ('符玄', '希儿')),
}


def _validate_env_merge_grants() -> None:
    """ENV_MERGE_GRANTS 构建校验(import 即炸;沿 _validate_env_boss_grants
    先例):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 角色名漂移:触发角色集与发放池逐名必须在 CHARACTERS(角色注册表
    改名不静默——触发集漂移 = 事件永不命中,发放池漂移 = 采出假身份
    混进席面);
    ③ 值形:两元组均非空(触发集空 = 条件永假,发放池空 = 采样必炸,
    登记笔误前置可见)。
    """
    orphans = [n for n in ENV_MERGE_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_MERGE_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, (_triggers, _pool) in ENV_MERGE_GRANTS.items():
        for _label, _names in (('触发角色集', _triggers), ('发放池', _pool)):
            if not _names:
                raise ValueError(
                    f"ENV_MERGE_GRANTS 值形({_n!r} {_label}):须为非空元组")
            for _name in _names:
                if _name not in CHARACTERS:
                    raise ValueError(
                        f"ENV_MERGE_GRANTS 角色名漂移({_n!r} {_label},"
                        f"角色注册表无此名,版本改名?):{_name!r}")


_validate_env_merge_grants()


# ===== 环境利息累计触发发放注册表(公司契约;白名单制)=====
# **世界发放域**(条件达成的世界发放第五表,ENV_STREAK/REFRESH/BOSS/MERGE
# GRANTS 同族):键 = 环境规范名,值 = (累计利息阈值, 发放角色名)。
# 计数语义 = 统一公式 interest 分量全分支累计(**含息 flat 修饰**;
# economy.md §10.1 收入口径),阈值语义 =「累计获得 N 利息后」一次性
# (done 封账)。表外环境一律无条目,禁从效果原文自动猜装(ENV_ECONOMY/
# ENV_GIFTS 同款纪律)。消费面 = kernel/cw_env_grants.check_env_interest_
# grants(触发检查单一源;调用点 = sim 收入应用两处 + live 三来源计数刻,
# T-27 迭代设计 §2.4/§2.5)。
# **表间豁免声明**(ENV_BOSS_GRANTS 同款显式声明):本表键与 ENV_GIFTS
# 共存 = 合法形态(两表同键各表各域——ENV_GIFTS 的 chars_conditional 辖
# 估值域档位机器,本表辖世界发放),与 ENV_ECONOMY 无 ∩ 冲突;双源一致性
# 代之以与 ENV_GIFTS 条件具名集的构建期对账(见 _validate_env_interest_
# grants 第④条)。
ENV_INTEREST_GRANTS: dict[str, tuple[int, str]] = {
    # 累计获得40利息后,获得【托帕&账账】(id 126 原文直读,
    # cw_invest_data PlazaPortal('126');阈值 40 卡面直读,发放单数缺省)
    '公司契约': (40, '托帕&账账'),
}


def _validate_env_interest_grants() -> None:
    """ENV_INTEREST_GRANTS 构建校验(import 即炸;沿 _validate_env_streak_
    grants 先例):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 值形:阈值须为 ≥1 的 int(bool 排除——isinstance(bool, int) 为真,
    ≤0 = 条件永真使 done 守卫登记刻即触发,登记笔误前置可见,沿 streak ③);
    角色名须为非空 str(空名 = 发放写出假身份);
    ③ 角色名漂移:发放角色必须在 CHARACTER_ROSTER(data/cw_chars 注册表;
    同文件 _validate_env_gifts ②先例——锁 data 注册表防版本改名静默失联,
    写出注册表外名字 = 假身份混进 bench,沿 streak ②装备名漂移同构。
    ``CHARACTERS`` 是 cw_pool 商店池域另一符号,勿混用);
    ④ 双源对账:键在 ENV_GIFTS 有条目时,其 chars_conditional 具名集
    (首元)须与本表发放角色一致——两表同出卡面(id 126),任一侧单独
    改名即漂移,构建期炸(_validate_env_ore_grants ③ 双源同值同构)。
    """
    orphans = [n for n in ENV_INTEREST_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_INTEREST_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, (_threshold, _char) in ENV_INTEREST_GRANTS.items():
        if not isinstance(_threshold, int) or isinstance(_threshold, bool) \
                or _threshold < 1:
            raise ValueError(
                f"ENV_INTEREST_GRANTS 阈值形({_n!r}):须为 ≥1 的 int,"
                f"现值 {_threshold!r}")
        if not isinstance(_char, str) or not _char:
            raise ValueError(
                f"ENV_INTEREST_GRANTS 角色名形({_n!r}):须为非空 str,"
                f"现值 {_char!r}")
        if _char not in CHARACTER_ROSTER:
            raise ValueError(
                f"ENV_INTEREST_GRANTS 角色名漂移({_n!r} 注册表无此人,"
                f"版本改名?):{_char!r}")
        _gift = ENV_GIFTS.get(_n)
        _cond = _gift.chars_conditional if _gift is not None else ()
        if not _cond or _cond[0][0] != _char:
            raise ValueError(
                f"ENV_INTEREST_GRANTS 双源失同步({_n!r}):ENV_GIFTS."
                f"chars_conditional 首元 "
                f"{_cond[0][0] if _cond else None!r} ≠ 本表发放角色 {_char!r}"
                f"(两表同出卡面,失同步即构建期炸)")


_validate_env_interest_grants()


# ===== 晶矿开启计数触发发放注册表(战技点契约;白名单制)=====
# **世界发放域**(条件发放登记表,与 ENV_STREAK/REFRESH/BOSS/MERGE/
# INTEREST_GRANTS 同族):键 = 环境规范名;
# 值 = (首阈值, 步长, 具名角色元组, 随机羁绊名) 四元组。
# 语义 = 持有该环境期间,每打开 N 个晶矿(全量计数,计数载体 =
# cw_effect_inventory.ore_open_total,写端 = 采晶矿上报单口)逐阈值
# 各发放一次:具名角色逐个 1★ + 随机羁绊池均匀采样 1 名 1★。
# 阈值序列 = 首阈值 + 步长×k(k=0,1,2,…,无限重复)。
# 与 ENV_ORE_GRANTS 辨析:彼表 = 发放「晶矿」(增发货币,值 = 各位面
# 矿金),本表 = 以「打开晶矿」为触发源发放角色,键形/值形/校验均不同。
# **表间豁免声明**(ENV_MERGE_GRANTS 同款):本表键与 ENV_GIFTS 共存
# = 合法形态(两表同键各表各域——ENV_GIFTS 的 chars_conditional 辖
# 估值域档位机器,本表辖世界发放),与 ENV_ECONOMY 无 ∩ 冲突。
ENV_ORE_OPEN_GRANTS: dict[str, tuple[int, int, tuple[str, ...], str]] = {
    # 战技点契约(id 128 原文直读:「打开20个晶矿后,获得【火花】和1个
    # 随机战技点羁绊角色;之后每打开10个晶矿,都可重复获得一次角色奖励」
    # ——首阈值 20/步长 10 卡面直读,重复次数上限无 = 无限重复)
    '战技点契约': (20, 10, ('火花',), '战技点'),
}


def _validate_env_ore_open_grants() -> None:
    """ENV_ORE_OPEN_GRANTS 构建校验(import 即炸;沿 _validate_env_
    interest_grants / _validate_env_refresh_grants 先例):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 值形:首阈值与步长须为 ≥1 的 int(bool 排除——isinstance(bool, int)
    为真;步长 ≤0 = 阈值 loop 死循环,首阈值 ≤0 = 登记刻即触发,
    登记笔误前置可见,沿 interest ②);
    ③ 具名角色名漂移:具名角色元组逐名必须在 CHARACTER_ROSTER(data/
    cw_chars 注册表;写出注册表外名字 = 假身份混进 bench,沿 interest ③。
    ``CHARACTERS`` 是 cw_pool 商店池域另一符号,勿混用);
    ④ 随机羁绊池现值非空:``chars_by_faction(随机羁绊名)`` 非空
    (羁绊名错字/版本改名 → 池空 = 采样腿永远发不出,运行期只剩整体
    缓发防御分支,登记笔误前置可见,T-19 池非空校验先例)。
    """
    orphans = [n for n in ENV_ORE_OPEN_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_ORE_OPEN_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, (_first, _step, _chars, _faction) in ENV_ORE_OPEN_GRANTS.items():
        for _label, _val in (('首阈值', _first), ('步长', _step)):
            if not isinstance(_val, int) or isinstance(_val, bool) or _val < 1:
                raise ValueError(
                    f"ENV_ORE_OPEN_GRANTS 值形({_n!r} {_label}):"
                    f"须为 ≥1 的 int,现值 {_val!r}")
        for _name in _chars:
            if _name not in CHARACTER_ROSTER:
                raise ValueError(
                    f"ENV_ORE_OPEN_GRANTS 角色名漂移({_n!r} 注册表无此人,"
                    f"版本改名?):{_name!r}")
        if not chars_by_faction(_faction):
            raise ValueError(
                f"ENV_ORE_OPEN_GRANTS 随机羁绊池空({_n!r}):"
                f"chars_by_faction({_faction!r}) 现值非空校验失败"
                f"(羁绊名漂移?),登记笔误前置可见")


_validate_env_ore_open_grants()


# ===== 同战共现触发发放注册表(星核猎手契约;白名单制)=====
# **世界发放域**(条件发放登记表,与 ENV_STREAK/REFRESH/BOSS/MERGE/
# INTEREST/ORE_OPEN_GRANTS 同族;结构化注册表新例 = dataclass 值形,先例
# 族值形均扁平元组,本表值含参与组嵌套结构故立载体):键 = 环境规范名。
# 语义 = 持有该环境期间,一场战斗的出战阵容(deployed 现读,参与即计)
# 使 presence_groups 逐组任一名在场(组间 AND、组内 OR)时发放
# reward_char(1★ 先验族),并给该张带上 deploy_lock_nodes 个节点的
# 上场锁(实例粒度,锁语义与解锁序位坐标系 = kernel/cw_env_grants.
# check_env_battle_grants / deploy_lock_block_reason 与
# cw_game_state.env_grant_deploy_locks 字段注释,单一源在彼处)。
# 表外环境一律无条目,禁从效果原文自动猜装(六表同款纪律)。
# **表间豁免声明**(ENV_INTEREST_GRANTS/ENV_ORE_OPEN_GRANTS 同款显式
# 声明):本表键与 ENV_GIFTS 共存 = 合法形态(两表同键各表各域——
# ENV_GIFTS 的 chars_conditional 辖估值域档位机器,本表辖世界发放),
# 与 ENV_ECONOMY 无 ∩ 冲突;双源一致性代之以与 ENV_GIFTS 条件具名集
# 的构建期对账(见 _validate_env_battle_grants 第⑤条)。
# 消费面 = kernel/cw_env_grants.check_env_battle_grants(触发检查单一
# 源;唯一调用点 = report_node_advance settle_confirm 分支,黑天鹅直登
# 相邻,live/sim 同口)。
@dataclass(frozen=True)
class EnvBattleGrant:
    """环境同战共现触发发放结构(世界发放域触发登记表新例;去序数族
    声明沿 ENV_ORE_OPEN_GRANTS 表头纪律)。字段语义(值 = id 129 原文直读):
    - presence_groups: 参与条件组,AND-of-ORs——外层逐组须同时满足,
      组内任一名出现在出战阵容即该组满足;坐标系 = settle_confirm 结算
      读 gs.deployed 现值(黑天鹅先例,参与即计)。
    - reward_char: 共现达成后发放的角色名。
    - deploy_lock_nodes: 发放后上场锁期(节点自然数);解锁序位 =
      发放刻生效序位(sequence_next 可达域)沿节点日程表步进本值步
      (K=2 → 步进 2 步;发放刻生效序位 = 战斗后继第一节点 X+1,步进
      K 步 = X+K+1,守卫拒 effective < 解锁序位 = 锁住 X+1..X+K 共
      K 个备战期,第 K+1 个节点起可上场)。"""
    presence_groups: tuple[tuple[str, ...], ...]
    reward_char: str
    deploy_lock_nodes: int


ENV_BATTLE_GRANTS: dict[str, EnvBattleGrant] = {
    # 星核猎手契约(id 129 原文直读):「刃或千冶·刃、卡芙卡、银狼LV.999
    # 或银狼一起参与一次战斗后,获得流萤,在2个节点后才能将其上场」
    '星核猎手契约': EnvBattleGrant(
        presence_groups=(('刃', '千冶·刃'), ('卡芙卡',), ('银狼LV.999', '银狼')),
        reward_char='流萤',
        deploy_lock_nodes=2),
}


def _validate_env_battle_grants() -> None:
    """ENV_BATTLE_GRANTS 构建校验(import 即炸;沿 _validate_env_
    interest_grants / _validate_env_ore_open_grants 先例):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 参与组形:presence_groups 非空且逐组非空(空外层 = 条件永真使
    done 守卫登记刻即触发,空组 = 该组永不满足使发放永不可达,登记笔误
    前置可见),逐名须为非空 str 且在 CHARACTER_ROSTER(data/cw_chars
    注册表;``CHARACTERS`` 是 cw_pool 商店池域另一符号勿混用,锁 data
    注册表防版本改名静默失联,沿 _validate_env_gifts ②先例);
    ③ 发放角色形:reward_char 非空 str 且在 CHARACTER_ROSTER(同②漂移
    面,写出注册表外名字 = 假身份混进 bench);
    ④ 锁期形:deploy_lock_nodes 须为 ≥1 的 int(bool 显式拒——bool 是
    int 子类,0/负 = 解锁序位不后移使锁无消费面,登记笔误前置可见);
    ⑤ 双源对账:键在 ENV_GIFTS 有条目时,其 chars_conditional 具名集
    (首元)须与本表发放角色一致——两表同出卡面(id 129),任一侧单独
    改名即漂移,构建期炸(_validate_env_interest_grants ④ 双源同值
    同构)。
    """
    orphans = [n for n in ENV_BATTLE_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_BATTLE_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, _grant in ENV_BATTLE_GRANTS.items():
        if not _grant.presence_groups \
                or any(not g for g in _grant.presence_groups):
            raise ValueError(
                f"ENV_BATTLE_GRANTS 参与组形({_n!r}):presence_groups "
                f"非空且逐组非空,现值 {_grant.presence_groups!r}")
        for _group in _grant.presence_groups:
            for _name in _group:
                if not isinstance(_name, str) or not _name:
                    raise ValueError(
                        f"ENV_BATTLE_GRANTS 参与名形({_n!r}):须为非空 str,"
                        f"现值 {_name!r}")
                if _name not in CHARACTER_ROSTER:
                    raise ValueError(
                        f"ENV_BATTLE_GRANTS 参与名漂移({_n!r} 注册表无此人,"
                        f"版本改名?):{_name!r}")
        _char = _grant.reward_char
        if not isinstance(_char, str) or not _char:
            raise ValueError(
                f"ENV_BATTLE_GRANTS 发放角色形({_n!r}):须为非空 str,"
                f"现值 {_char!r}")
        if _char not in CHARACTER_ROSTER:
            raise ValueError(
                f"ENV_BATTLE_GRANTS 发放角色漂移({_n!r} 注册表无此人,"
                f"版本改名?):{_char!r}")
        _lock = _grant.deploy_lock_nodes
        if not isinstance(_lock, int) or isinstance(_lock, bool) or _lock < 1:
            raise ValueError(
                f"ENV_BATTLE_GRANTS 锁期形({_n!r}):须为 ≥1 的 int,"
                f"现值 {_lock!r}")
        _gift = ENV_GIFTS.get(_n)
        _cond = _gift.chars_conditional if _gift is not None else ()
        if not _cond or _cond[0][0] != _char:
            raise ValueError(
                f"ENV_BATTLE_GRANTS 双源失同步({_n!r}):ENV_GIFTS."
                f"chars_conditional 首元 "
                f"{_cond[0][0] if _cond else None!r} ≠ 本表发放角色 {_char!r}"
                f"(两表同出卡面,失同步即构建期炸)")


_validate_env_battle_grants()


# ===== 环境「随机赠卡 + 节点上场锁」登记表(白名单制)=====
# 立形首例 = 英雄登场(id 133「获得1个2星5费角色,19个节点后才能将其上场。
# 战斗完胜后,上场节点额外提前1点。」,PlazaPortal('133'));登记本体 =
# 上场锁期 + 完胜加速两个机制维度,GiftGrant(估值域)无归属字段——T-10
# 裁决确立的「无锁随机赠卡归 GiftGrant.chars_random_immediate」不受影响,
# 本表只收「赠卡带锁」形。消费面:发放腿 = cw_gain_chain.on_env_gained
# (复用 random_char_pool 均匀采样 + env_grant_uid_seq 发号 + 解锁序位
# 沿日程表步进),完胜提前腿 = kernel/cw_env_grants.
# check_env_deploy_lock_perfect(report_node_advance settle_confirm 分支);
# 锁域 Field/守卫/审计行/快照 rebuild 复用 T-30 已落地件零新建。
@dataclass(frozen=True)
class EnvDeployLockGrant:
    """环境「随机赠卡 + 节点上场锁」结构(世界发放域专属登记表条目;
    值 = id 133 原文直读,cw_invest_data.py PlazaPortal('133')):
    - spec: 赠卡规格(复用「随机N费赠卡」家族载体 RandomCharSpec,
      立形首例 = 人才引进;英雄登场 = RandomCharSpec(cost=5, star=2),
      type_tag 空 = 类型不限、池 = 5 费全档);
    - deploy_lock_nodes: 上场锁期(「19个节点」直读);解锁序位 =
      获得刻生效序位沿节点日程表步进本值(计数起点 = 获得节点计入
      锁定段,系设计定读——卡文无计数起点词,证伪通道 = 实机环境选择后
      锁倒计时读数,披露键随 T-33 设计稿披露 9);
    - perfect_win_accel: 「战斗完胜后,上场节点额外提前1点」开关
      (desc 有该腿 = True;真实值在册,防后继无完胜腿的同形卡误挂)。"""
    spec: RandomCharSpec
    deploy_lock_nodes: int
    perfect_win_accel: bool


ENV_DEPLOY_LOCK_GRANTS: dict[str, EnvDeployLockGrant] = {
    # 英雄登场(id 133 原文直读)
    '英雄登场': EnvDeployLockGrant(spec=RandomCharSpec(cost=5, star=2),
                                   deploy_lock_nodes=19,
                                   perfect_win_accel=True),
}


def _validate_env_deploy_lock_grants() -> None:
    """ENV_DEPLOY_LOCK_GRANTS 构建校验(import 即炸;沿 streak/refresh/
    battle 登记表校验先例):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② spec 值域查(共享助手 ``_validate_random_char_spec`` 单一源,
    _validate_env_gifts ⑥ 同款判据):采样轴互斥(cost/faction 恰好一轴
    非空)/cost 1-5(仅 cost 非 None 时,bool 显式拒)/star 1-3 /
    type_tag ∈ 注册表 char_type 标签闭集(错字致池空静默)/规格过滤池
    非空(random_char_pool,注册表漂移防呆,T-10 校验先例);
    ③ 锁期形:deploy_lock_nodes 须为 ≥1 的 int(bool
    显式拒——ENV_BATTLE_GRANTS 锁期形④逐字同款);④ 双登记防呆:
    ``set(ENV_DEPLOY_LOCK_GRANTS) ∩ set(ENV_GIFTS) = ∅``——同卡双表 =
    赠卡双发 + 锁记录双写,import 期不可见(集合互斥同款先例 =
    _validate_env_gifts 尾段 ∩ ENV_ECONOMY;refresh 的值对账豁免段是
    值对账非集合互斥,不作先例)。
    """
    orphans = [n for n in ENV_DEPLOY_LOCK_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_DEPLOY_LOCK_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, _grant in ENV_DEPLOY_LOCK_GRANTS.items():
        _validate_random_char_spec('ENV_DEPLOY_LOCK_GRANTS', _n, _grant.spec)
        _lock = _grant.deploy_lock_nodes
        if not isinstance(_lock, int) or isinstance(_lock, bool) or _lock < 1:
            raise ValueError(
                f"ENV_DEPLOY_LOCK_GRANTS 锁期形({_n!r}):须为 ≥1 的 int,"
                f"现值 {_lock!r}")
    _overlap = set(ENV_DEPLOY_LOCK_GRANTS) & set(ENV_GIFTS)
    if _overlap:
        raise ValueError(
            f"ENV_DEPLOY_LOCK_GRANTS ∩ ENV_GIFTS 非空(同卡双表 = 赠卡双发"
            f" + 锁记录双写):{sorted(_overlap)}")


_validate_env_deploy_lock_grants()


# ===== 环境「战利品区倒计时件 + 节点倒计时开盒」登记表(白名单制)=====
# 立形首例 = 命运礼物(id 134「立刻获得一个【惊喜盒】,倒计时12个节点后
# 礼盒打开,战斗完胜后,倒计时额外减少1点。」,PlazaPortal('134'),
# cw_invest_data.py)。惊喜盒 = 战利品区浮动件非占席(实机板件实证 =
# 与晶矿球同区,T-34 设计稿 §1 两帧证据),故不入 GiftGrant(道具通道 =
# _place_bench_item 占席落位,与板件位置直接矛盾)、不入 BENCH_ITEM_NAMES
# 词表(非占席,词表派生式零扩)。消费面:到手腿 = cw_gain_chain.
# on_env_gained 延迟道具支线(纯队列登记零席位写);开盒腿 =
# cw_gain_chain.discharge_due_item_opens 原语(sim 进节点收口挂点,
# 实机局不接);完胜加速腿 = kernel/cw_env_grants.
# check_env_item_open_perfect(report_node_advance settle_confirm 分支)。
@dataclass(frozen=True)
class EnvDelayedItemGrant:
    """环境「战利品区倒计时件」结构(世界发放域专属登记表;
    字段语义 = id 134 原文直读 + 实机板件实证):
    - item: 倒计时件名(「【惊喜盒】」直读;战利品区浮动件非占席——
      实证 = reward_giftbox_phantom.webp 与晶矿球同区);
    - open_delay_nodes: 开盒倒计时节点数(「12个节点」直读);
      解锁位 = 获得刻生效序位沿日程步进本值(计数起点 = T-34 设计稿
      裁决点 3:获得节点计入);
    - perfect_win_accel: 「战斗完胜后,倒计时额外减少1点」加速腿旗
      (腿本体 = T-34 设计稿裁决点 1)。"""
    item: str
    open_delay_nodes: int
    perfect_win_accel: bool


ENV_DELAYED_ITEM_GRANTS: dict[str, EnvDelayedItemGrant] = {
    # 命运礼物(id 134 原文直读,cw_invest_data.py:402)
    '命运礼物': EnvDelayedItemGrant(item='惊喜盒', open_delay_nodes=12,
                                    perfect_win_accel=True),
}


def _validate_env_delayed_item_grants() -> None:
    """ENV_DELAYED_ITEM_GRANTS 构建校验(import 即炸;沿 deploy_lock
    登记表校验先例):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② item 形:非空 str 且 ∉ CHARACTER_ROSTER(道具/角色通道串行防呆,
    _validate_env_gifts 定时道具名同款判据);③ 倒计时形:open_delay_nodes
    须为 ≥1 的 int(bool 显式拒——ENV_DEPLOY_LOCK_GRANTS 锁期形逐字
    同款);④ 双登记防呆:
    ``set(ENV_DELAYED_ITEM_GRANTS) ∩ set(ENV_GIFTS) = ∅``——同卡双表 =
    道具双发(占席落位 + 队列登记各一份),先例 =
    ENV_DEPLOY_LOCK_GRANTS ∩ ENV_GIFTS;⑤ 加速旗形:perfect_win_accel
    必 bool(登记笔误前置可见)。
    """
    orphans = [n for n in ENV_DELAYED_ITEM_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_DELAYED_ITEM_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, _grant in ENV_DELAYED_ITEM_GRANTS.items():
        _item = _grant.item
        if not isinstance(_item, str) or not _item:
            raise ValueError(
                f"ENV_DELAYED_ITEM_GRANTS 件名形({_n!r}):须为非空 str,"
                f"现值 {_item!r}")
        if _item in CHARACTER_ROSTER:
            raise ValueError(
                f"ENV_DELAYED_ITEM_GRANTS 件名漂移({_n!r}):"
                f"倒计时件名混入角色注册表(道具/角色通道串行防呆):"
                f"{_item!r}")
        _delay = _grant.open_delay_nodes
        if not isinstance(_delay, int) or isinstance(_delay, bool) \
                or _delay < 1:
            raise ValueError(
                f"ENV_DELAYED_ITEM_GRANTS 倒计时形({_n!r}):须为 ≥1 的 int,"
                f"现值 {_delay!r}")
        if not isinstance(_grant.perfect_win_accel, bool):
            raise ValueError(
                f"ENV_DELAYED_ITEM_GRANTS 加速旗形({_n!r}):须为 bool,"
                f"现值 {_grant.perfect_win_accel!r}")
    _overlap = set(ENV_DELAYED_ITEM_GRANTS) & set(ENV_GIFTS)
    if _overlap:
        raise ValueError(
            f"ENV_DELAYED_ITEM_GRANTS ∩ ENV_GIFTS 非空(同卡双表 = 道具"
            f"双发):{sorted(_overlap)}")


_validate_env_delayed_item_grants()


# ===== 节点改写注册表归属校验(import 即炸)=====
# 注册表数据住序列模块(kernel/cw_node_schedule.ENV_NODE_REWRITE_RULES,
# 与序列真值同域、sim 同源直读);归属校验住 INVESTMENT_ENVS 的家——
# 版本更新改名/移除环境后注册表键静默失联在构建期炸出,不进运行时
# (防静默失联先例 =  登记表校验;依赖方向:cw_investments 顶层 import
# cw_node_schedule,后者零依赖,单向无环)。
def _validate_env_node_seq() -> None:
    """ENV_NODE_REWRITE_RULES 归属校验(沿 _validate_env_streak_grants
    先例):键 ⊆ INVESTMENT_ENVS(归一名口径;防版本改名静默失联)。"""
    from sr_od.application.currency_war.kernel.cw_node_schedule import (
        ENV_NODE_REWRITE_RULES,
    )
    orphans = [n for n in ENV_NODE_REWRITE_RULES
               if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_NODE_REWRITE_RULES 孤儿键(base 无此环境?版本改名?):"
            f"{sorted(orphans)}")


_validate_env_node_seq()


# ===== 环境补给选项装备携带数注册表(过剩经费;白名单制)=====
# 「补给选项内容修饰」环境首例:键 = 环境规范名,值 = 每列装备件数
# (默认 1 件不入表)。表外环境一律无条目,禁从效果原文自动猜装
# (ENV_STREAK_GRANTS 同款白名单纪律)。消费面 = sim 生成器
# (sim/cw_sim_backend.supply_options 查表发件);live 读链不消费本表
# (obs 层角色锚点+几何归并按实读描述画面真值,不读局状态)。表形状
# 预留「每列件数」泛化:读链天然携带 1..n 件,char-only 列 = 0 件;
# 未来 3 件/列环境 sim 侧落本表即两面同启。无估值三表互斥闸——本表是
# 世界/呈现修饰非估值结构(ENV_NODE_REWRITE_RULES 注册表同判,
# 无互斥先例)。
ENV_SUPPLY_EQUIP_COUNT: dict[str, int] = {
    # 补给阶段中，角色会携带两件装备(id 108 原文直读,
    # cw_invest_data PlazaPortal('108'))
    '过剩经费': 2,
}


def _validate_env_supply_equip_count() -> None:
    """ENV_SUPPLY_EQUIP_COUNT 构建校验(import 即炸;沿
    _validate_env_streak_grants 先例):
    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 值形:≥2 的真 int(bool 排除——<2 与默认 1 件无差,登记笔误
    前置可见)。"""
    orphans = [n for n in ENV_SUPPLY_EQUIP_COUNT if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_SUPPLY_EQUIP_COUNT 孤儿键(base 无此环境?版本改名?):"
            f"{sorted(orphans)}")
    for _n, _count in ENV_SUPPLY_EQUIP_COUNT.items():
        if not isinstance(_count, int) or isinstance(_count, bool) \
                or _count < 2:
            raise ValueError(
                f"ENV_SUPPLY_EQUIP_COUNT 值形({_n!r}):须为 ≥2 的 int,"
                f"现值 {_count!r}")


_validate_env_supply_equip_count()


# ===== 扑满环境奖励面板矿占位增量注册表(白名单制)=====
# 「经济过热/经济严重过热」两扑满环境局,sim 奖励面板矿在普通奖励锚
# (sim/cw_sim_backend.REWARD_ORE_PANEL_ANCHOR,8 矿)之上的增量矿数
# ——承载卡面「掉落(超)多战利品」幅度差异的 sim 占位:游戏 desc 无
# 数值,值 = 用户占位拍定(2026-10-15,设计 designs/T-20-jingji-
# yanzhong-guore.md §8),非核实游戏事实,待实机采证校准;占位申报
# 披露键 = sim/cw_sim_backend.PIGGY_ORE_PANEL_BONUS_PLACEHOLDER。
# 两键独立拍定、独立校准:「经济严重过热」=「经济过热」再 +4 的阶梯
# 关系只是本轮占位取值的来历,非不变量、不校验——实采可只调一键。
# 消费面 = sim 奖励面板装配单点(cw_sim_backend 按活跃环境查表扩尾);
# live 面板矿 = 实机渲染观察读画面,本表不进 live 读链。表外环境一律
# 无增量(表形状与 ENV_SUPPLY_EQUIP_COUNT 同判:禁从效果原文自动猜数)。
ENV_ORE_PANEL_BONUS: dict[str, int] = {
    '经济过热': 4,
    '经济严重过热': 8,
}


def _validate_env_ore_panel_bonus() -> None:
    """ENV_ORE_PANEL_BONUS 构建校验(import 即炸;沿
    _validate_env_supply_equip_count 先例):
    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 值形:≥1 的真 int(bool 排除;禁 0——表外默认即无增量,登记 0
    与表外无差,登记笔误前置可见);
    ③ 键集与扑满名单 PIGGY_ENV_NAMES **完全一致**(响亮向,禁 ⊆ 静默
    向):第三扑满环境出现(名单增员)或扑满卡移除(名单减员)即
    import 炸,强制逐环境显式拍定占位增量,防名单扩员后增量静默缺档。"""
    orphans = [n for n in ENV_ORE_PANEL_BONUS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_ORE_PANEL_BONUS 孤儿键(base 无此环境?版本改名?):"
            f"{sorted(orphans)}")
    for _n, _bonus in ENV_ORE_PANEL_BONUS.items():
        if not isinstance(_bonus, int) or isinstance(_bonus, bool) \
                or _bonus < 1:
            raise ValueError(
                f"ENV_ORE_PANEL_BONUS 值形({_n!r}):须为 ≥1 的 int,"
                f"现值 {_bonus!r}")
    # 函数内 import:沿 _validate_env_node_seq 先例,避免 cw_reward_node
    # → cw_game_state 一侧与本模块的潜在环(cw_reward_node 派生名单
    # 依赖 data 表 + cw_game_state,不依赖本模块,静态无环,但保持
    # 同先例形态)。
    from sr_od.application.currency_war.kernel.cw_reward_node import (
        PIGGY_ENV_NAMES,
    )
    if set(ENV_ORE_PANEL_BONUS) != set(PIGGY_ENV_NAMES):
        raise ValueError(
            f"ENV_ORE_PANEL_BONUS 键集与扑满名单 PIGGY_ENV_NAMES 不一致"
            f"(第三扑满环境增删须逐环境显式拍定占位增量):"
            f"仅表有 {sorted(set(ENV_ORE_PANEL_BONUS) - set(PIGGY_ENV_NAMES))},"
            f"仅名单有 {sorted(set(PIGGY_ENV_NAMES) - set(ENV_ORE_PANEL_BONUS))}")


_validate_env_ore_panel_bonus()


# ===== 商店 2★ 直出概率注册表(环境白名单;T-22 人才下沉)=====
# 语义:表内环境的发牌(kernel/cw_shop_deal 翻星腿,sim deal_shop 与实机
# 刷新随机态腿共用)中,每张非空商店牌独立按 p 升 2★;表外环境恒 1★。
# 值 = 用户占位非游戏真值(首例人才下沉 0.2/卡,2026-10-16 用户裁定;
# desc 无数值,待实机采证校准),禁从效果原文猜值——其余「商店出 2★」
# 类效果入表须各自取得用户拍定。占位申报披露键 =
# sim/cw_sim_backend.SHOP_TWO_STAR_DEAL_PLACEHOLDER。
ENV_SHOP_TWO_STAR_DEAL_PROB: dict[str, float] = {
    '人才下沉': 0.2,
}


def _validate_env_shop_two_star_deal_prob() -> None:
    """ENV_SHOP_TWO_STAR_DEAL_PROB 构建校验(import 即炸;沿
    _validate_env_ore_panel_bonus 先例):
    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 值形:0 < p < 1 的 float(bool 排除;概率语义自带上下界,本表无
    键集闭包要求——白名单制,表内即启用,与扑满矿表的名单闭包不同形)。"""
    orphans = [n for n in ENV_SHOP_TWO_STAR_DEAL_PROB
               if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_SHOP_TWO_STAR_DEAL_PROB 孤儿键(base 无此环境?版本改名?):"
            f"{sorted(orphans)}")
    for _n, _p in ENV_SHOP_TWO_STAR_DEAL_PROB.items():
        if not isinstance(_p, float) or isinstance(_p, bool) \
                or not 0.0 < _p < 1.0:
            raise ValueError(
                f"ENV_SHOP_TWO_STAR_DEAL_PROB 值形({_n!r}):"
                f"须为 0<p<1 的 float,现值 {_p!r}")


_validate_env_shop_two_star_deal_prob()


# ===== 环境羁绊档位条件发放注册表(特邀专家:加拉赫;白名单制)=====
# **世界发放域**(条件达成的世界发放新表,ENV_STREAK/REFRESH/BOSS/MERGE/
# INTEREST/ORE_OPEN/BATTLE/DEPLOY_LOCK/DELAYED_ITEM 同族):键 = 环境规范
# 名,值 = (羁绊名, 发放装备名)。**档位不入表**:单一源 =
# FACTIONS[bond].tiers(权威裁定「羁绊阈值仍以 cw_factions 为准」,
# docs/game/currency_war/research/invest_effects.md「羁绊激活口径」节;
# 跨档判据同源先例 = kernel/cw_faction_callbacks 弹窗阵营档位判定)。
# 表外环境一律无条目,禁从效果原文自动猜装(ENV_ECONOMY/ENV_GIFTS 同款
# 纪律)。消费面 = kernel/cw_faction_callbacks.check_env_bond_tier_grants
# (deployed 写尾门外必查)+ kernel/cw_env_grants.grant_env_bond_tier
# (发放原语:equips 尾追 + done 登记两笔同窗)。
# **表间豁免声明**(ENV_REFRESH_GRANTS 先例同款):本表为世界发放域表,
# 与估值域表分域不互斥——本条目键与 ENV_GIFTS['特邀专家:加拉赫'] 同键
# 并存合法(先例 = ENV_ORE_GRANTS ∩ ENV_ECONOMY 的增发货币两表并存),
# 不参与「单一环境只落一个估值结构」三表互斥校验。
ENV_BOND_TIER_GRANTS: dict[str, tuple[str, str]] = {
    # 激活2/4/6/9击破羁绊时,获得1件【以太钻头】(id 142 原文直读,
    # cw_invest_data PlazaPortal('142'))
    '特邀专家:加拉赫': ('击破', '以太钻头'),
}


def _validate_env_bond_tier_grants() -> None:
    """ENV_BOND_TIER_GRANTS 构建校验(import 即炸;沿 _validate_env_streak_
    grants 先例):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 羁绊名漂移:bond 必须在 FACTIONS(档位单一源失联 = 判据失效);
    ③ 装备名漂移:发放装备必须在 EQUIPMENTS(发放写出库存里不存在的
    名字 = 假身份混进 equips,ENV_STREAK_GRANTS ②同款);
    ④ 卡面档位对拍闸:FACTIONS[bond].tiers 串(现值 '2/4/6/9')必须是
    该环境 effect 原文的子串——击破 tiers V4.4 实证跨版本会变
    (2/4/6/8/10→2/4/6/9),plaza 重生成改 desc 或有人改 FACTIONS 后两侧
    失同步 = 构建期炸出强制人工复审,防档位漂移静默错发。对拍 = 子串
    包含形态,极端同形假通过可接受(闸目的 = 漂移可见性,非精确文本
    解析)。
    """
    orphans = [n for n in ENV_BOND_TIER_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_BOND_TIER_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, (_bond, _equip) in ENV_BOND_TIER_GRANTS.items():
        if _bond not in FACTIONS:
            raise ValueError(
                f"ENV_BOND_TIER_GRANTS 羁绊名漂移({_n!r} FACTIONS 无此"
                f"羁绊,版本改名?):{_bond!r}")
        if _equip not in EQUIPMENTS:
            raise ValueError(
                f"ENV_BOND_TIER_GRANTS 装备名漂移({_n!r} 注册表无此装备,"
                f"版本改名?):{_equip!r}")
        _tiers_str = '/'.join(str(t) for t in FACTIONS[_bond].tiers)
        if _tiers_str not in INVESTMENT_ENVS[_n].effect:
            raise ValueError(
                f"ENV_BOND_TIER_GRANTS 卡面档位对拍失同步({_n!r}):"
                f"FACTIONS[{_bond!r}].tiers={FACTIONS[_bond].tiers} 串 "
                f"{_tiers_str!r} 不在效果原文 {INVESTMENT_ENVS[_n].effect!r} "
                f"中(档位单一源 = FACTIONS,卡面/注册表任一侧改档 = "
                f"构建期强制人工复审)")


_validate_env_bond_tier_grants()


# ===== 环境取卡触发发放注册表(T-46 策略大师;白名单制)=====
# 世界发放域取卡触发器首例(事件式同型先例 = merge:事件携带事实无 done)。
# 每取卡事件一笔,无 done 封账。
# 表间豁免声明(见 _validate_env_pick_grants ③):本表键与 ENV_ECONOMY 共存,
# 不参与「单一环境只落一个估值结构」互斥;正确性代之以双源同值校验(③)。
ENV_PICK_GRANTS: dict[str, int] = {
    # 每取一张策略 +coef×含本张已持有数(id 147 原文直读「2*已拥有投资策略数」;
    # 口径 = 含本张(用户裁定 2026-10-26):第 k 张到手发 coef×k,首张 coef×1)
    '策略大师': 2,
}


def _validate_env_pick_grants() -> None:
    """ENV_PICK_GRANTS 构建校验(import 即炸;沿 _validate_env_ore_grants
    / _validate_env_refresh_grants 双源同值先例):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(防版本更新改名/移除后静默失联);
    ② 值形:正 int(bool 排除——isinstance(True, int) 为真,False/True 形
    混入 = 登记笔误,前置可见;0/负 = 条件永真或倒扣,禁);
    ③ 双源同值:同键在 ENV_ECONOMY 有非空 gold_per_strategy_coef → 相等
    (估值面与世界面同出卡面 id 147,任一侧单独改系数即失同步,构建期炸;
    ENV_ORE_GRANTS/ENV_REFRESH_GRANTS 家族同款)。
    """
    orphans = [n for n in ENV_PICK_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_PICK_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, _coef in ENV_PICK_GRANTS.items():
        if not isinstance(_coef, int) or isinstance(_coef, bool) or _coef < 1:
            raise ValueError(
                f"ENV_PICK_GRANTS 值形({_n!r}):须为 ≥1 的 int(禁 bool),"
                f"现值 {_coef!r}")
        _econ = ENV_ECONOMY.get(_n)
        _src = int(getattr(_econ, 'gold_per_strategy_coef', 0) or 0)
        if _src and _src != _coef:
            raise ValueError(
                f"ENV_PICK_GRANTS 双源失同步({_n!r}):ENV_ECONOMY."
                f"gold_per_strategy_coef={_src} ≠ 本表 {_coef}"
                f"(估值面与世界面同出卡面,失同步即构建期炸)")


_validate_env_pick_grants()
