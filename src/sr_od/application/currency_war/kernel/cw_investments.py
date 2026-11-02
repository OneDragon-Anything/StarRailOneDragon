"""货币战争 投资策略 + 投资环境领域模型(meta 层,V4.4)。

**两层架构**:
- **base 事实层** = ``cw_invest_data.py``(``tools/cw/gen_plaza_invest.py`` 从米游社攻略广场
  官方 API 生成,勿手编):名字/品质/效果全文,数字 id 稳定主键,投资策略 334 + 投资环境 83
  官方全量(游戏内数据银行同口径,米游社百科 doc 的 19 条版本漂移缺口就此补齐)。
- **建模增量层** = 本文件手维护(API 给不了的人工建模):
  - ``STRATEGY_ECONOMY``(可数值化经济效果);
  - ``is_blood_economy``/``blood_xp_mode``(血本位判别与 XP 购买模式解析,
    [40]① 选择回避 / [40]② 支付能力检查定性——经验批支付门共享判据);
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

from dataclasses import dataclass, replace

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
    BENCH_REROLL_RIGHT3,
    BOARD_REWRITE_SELL_ALL,
    BOARD_REWRITE_SELL_ALL_DEAL,
    BOARD_REWRITE_UPGRADE_ALL,
    EQUIPS_REROLL_SAME_QUALITY,
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
    - free_refresh_cond_prev_node_unspent: 条件判定族·花费布尔形(存款回报=2)——
      每次进入新节点时,上节点未花费(gs.prev_node_spent=False)才授予该值次数;
      True 不授予,未写(None)= 保守零授予(禁猜);置位写端 = 四花费通道
      mark_gold_spent,滚位 = 节点边界 roll_prev_node_spent(发放同经节点桥)
    - refresh_surprise_every: 每 N 次刷新刷出 5 张同费卡(采购专员;稳定器,提高刷新期望)
    - gold_per_three_5cost: 每购买 3 个 5 费角色给金
    - interest_cap_override: 利利息档上限覆写(开源节流 9 档/利息上调 10 档/买断制 0)
    - xp_per_refresh: 每次刷新 +经验
    - xp_per_node: 每节点 +经验
    - xp_buy_cost_discount: 每击「购买经验」减金
    - win_reward_mult: 连胜奖励倍率(伟大征服 3)
    - gold_per_boss_node: 进首领节点给金(特战资金系;boss 占节点 ~1/9,消费侧折算)
    - gold_at_final_supply: 进入最后一个补给阶段后给金(尾款交付;整局一次,
      锚 = 展平全序列最末 supply 位,载体 = cw_node_schedule.final_supply_pos)
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
    # 条件免费刷·单字段双职(次数+激活开关,>0 即激活;存款回报=2,卡面只有
    # 固定值无梯度无封顶,不需要三元组式多字段配对):每次进入新节点时,
    # 上节点未花费(prev_node_spent=False)→ 授予该值次数;True = 不授予;
    # None/未写 = 保守零授予(禁猜,本金充裕金 None 同款口径);不做
    # aggregate_economy 标量聚合(同三元组)
    free_refresh_cond_prev_node_unspent: int = 0
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
    encounter_tier_extremes_only: bool = False
    # 遭遇候选空间收窄旗标(二极管):持卡局遭遇节点呈现集 = 档位全集
    # 最低+最高两档。语义旗标无数值;端点由 sim 呈现面从 encounter_options()
    # (档数单一源 = ENCOUNTER_TIER_COUNT)首尾派生,禁在此写数。
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
    hp_instant: int = 0                   # 即时生命(健康充值 +30;负值 = 损失,
                                          # 先亏后盈 −20):选卡当场 hp 直加,
                                          # 不 clip(上下界同此——sim 扣血绝对值制
                                          # 无上限消费,hp_max 字段缺位,缺口申报
                                          # = fields.md HP 面行),clip 属无消费端
                                          # 语义;负值支写端与损血档位触发扩挂点
                                          # 见 apply_strategy_pick_hp;0 = 无此腿
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
    gold_at_final_supply: int = 0         # 「进入最后一个补给阶段后」给金(尾款交付;锚 =
                                          # 展平全序列最末 supply 位,整局一次;载体 =
                                          # cw_node_schedule.final_supply_pos;修饰局
                                          # 随场字段现值派生零特判,域内无 supply =
                                          # None〔序列表未来形状防御,现表恒非空〕)
    streak_set: int = 0                   # 「使当前连胜数变为N」选卡当场带符号绝对置位
                                          # (首例 胜利,还是胜利 4;值全部 =
                                          # cw_invest_data 效果原文直读)。置位 =
                                          # 赋值非增益:高连胜回落/连败翻转均字面
                                          # 语义(卡文「变为」无 max/只升限定);0 =
                                          # 无此腿
    # —— 刷新触发条件金族(每次刷新事件条件触发,非选牌当场——
    #    instant_gold 一次性语义辖不动;登记形态等值迁移先例 =
    #    尾款交付 gold_at_final_supply)——
    gold_per_refresh_pair: int = 0        # 合并同类项:刷新出 2 同名 +1 金
                                          # (每次刷新事件条件触发;发放 =
                                          # 刷新上报随机态腿后检查腿)
    # —— 战斗结算修饰族(败局帧修饰,非收入通道;聚合 =
    #    strategy_loss_battle_modifier,live 游戏自算 + 观察覆盖零写)——
    loss_hp_extra: int = 0                # 败局额外扣血:战斗失败时在基础败局伤害上追加
                                          # (「伤害提高」语义 = 加重,非减免;首例 嘴硬 5,
                                          # 值 = cw_invest_data 效果原文直读)。仅作用于
                                          # 存在基础伤害的败局帧(三重门 = 败局 ∧
                                          # hp_delta<0 ∧ 本字段非零;扑满帧豁免优先,
                                          # 零基础不产生伤害——「扑满不掉血」同向);
                                          # 0 = 无此腿
    keep_streak_on_loss: bool = False     # 败局连胜维持:战斗失败时连胜计数不清零(首例
                                          # 嘴硬)。读法边界 = 仅带符号正值维持——
                                          # 「原来的连胜数」字面辖域 = 连胜计数,零/
                                          # 连败无连胜数可维持,非正值照常败局转移
                                          # (desc 未写负值分支 = 判读申报制,后继族稿
                                          # 禁当定谳转引);False = 无此腿
    # —— 位面开始周期族(「现在以及每个位面开始时」双段卡的位面段;
    #     首例 固定理财 4/2,策略域位面粒度周期发放)——
    xp_per_plane: int = 0                 # 每位面开始 +经验(固定理财 4)。XP = 世界
                                          # 真值:live 零写观察覆盖,sim 世界腿 =
                                          # 位面首节点窗(cw_sim_backend)——双挂点
                                          # 分工同 xp_instant 通道
    free_refresh_per_plane: int = 0       # 每位面开始 +免费刷新次数(固定理财 2)。
                                          # 刷新 = bot 决策逻辑态:发放 = kernel 位面
                                          # 开始桥 apply_effect_plane_start_grant
                                          # (推进 tick 位面 1 号节点),中途拿卡时
                                          # 所在位面登记拍全额补发 =
                                          # apply_effect_plane_refire_grant


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
    ('free_refresh_per_plane', 0),
    ('refresh_surprise_every', 0), ('refresh_per_compose', 0),
    ('refresh_free_chance', 0.0), ('refresh_shop_rewrite_every_3cost', 0),
    ('xp_per_refresh', 0), ('xp_per_node', 0), ('xp_buy_cost_discount', 0),
    ('xp_instant', 0), ('xp_per_plane', 0),
    ('gold_per_refresh_pair', 0),
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
    # 时点金·序列位置锚(尾款交付):整局一次的必经节点条件金,世界腿 =
    # sim 节点窗独立笔(final_supply_pos 锚),非持续通道
    'gold_at_final_supply',
    # 条件刷新三元组(本金充裕系):条件窗口内逐节点补刷,旧闭集裁决
    # 不入引擎族(非无条件持续通道),沿旧闭集原样划界
    'free_refresh_cond_gold_above', 'free_refresh_cond_gold_step',
    'free_refresh_cond_cap',
    # 条件刷新·上节点未花费位(存款回报):同三元组划界——授予条件依赖
    # 玩家上节点行为(逐节点边界评估),非无条件持续通道,不入引擎族
    'free_refresh_cond_prev_node_unspent',
    # 补偿型(损血/上限损耗换算,不构成收入通道)
    'gold_per_20hp_lost', 'gold_per_hp_lost_now',
    'hp_max_loss_pct_of_loss', 'hp_max_loss_cap_pct',
    # 血本位族(另由 is_blood_economy 集合排除覆盖,不入引擎判定)
    'hp_gold_swap', 'xp_buy_hp_cost',
    # 难度/期权族(难度→价值需战力建模;远见品质改写系期权)
    'difficulty_delta', 'difficulty_per_streak', 'difficulty_node_types',
    'future_quality_upgrade', 'difficulty_inflation_exempt',
    # 遭遇收窄旗标(二极管):结构旗标不构成持续通道,难度族同组同依据
    # (2026-10-28 校验治理后本桶无 import 炸防线,漏登记 = 漏分类静默
    # 不炸,评审面把关 = is_economy_engine 治理注)
    'encounter_tier_extremes_only',
    # 负向结构登记(成本/加价,无正通道)
    'xp_click_surcharge_from_level', 'xp_click_surcharge_from_level_at',
    # 一次性状态置位(非持续通道;一次性金族同款划界):「使当前连胜数
    # 变为N」= 选卡当场对连胜真值绝对赋值,无双端持续语义;世界腿 =
    # sim 选卡落地拍独立笔,live 观察覆盖兜底
    'streak_set',
    # 一次性 hp 直给(选卡当场对 hp 真值 +N 直加,无双端持续语义;
    # 一次性金族同款划界):世界腿 = sim 选卡落地拍独立笔,live 观察覆盖
    # 兜底;不入现金通道——hp 定价通道作废正本(invest_effects.md 血金
    # 互兑裁定),hp 永不折金
    'hp_instant',
    # 战斗结算修饰族(非收入通道;难度族同款划界):败局帧战斗结算修饰
    # (hp 加重/连胜维持),世界腿 = sim 结算 hp 腿与 streak 转移形参,
    # live 游戏自算 + 观察覆盖;修饰不产生金流,不入引擎判定
    'loss_hp_extra', 'keep_streak_on_loss',
})


def is_economy_engine(economy: EconomyEffect | None) -> bool:
    """持续通道引擎谓词(策略层刷新判据帧级顶级类的 kernel 判据源)。

    结构事实判据(存在性,非幅度):命中任意持续通道字段即真,字段值不
    参与任何定序。与血本位排除族零交集(两族字段不相交,对账声明见
    ``_ENGINE_CHANNEL_EXCLUDED_FIELDS`` 分组注)。新增 EconomyEffect 字段
    须同步落入三分类常量(治理注 = 2026-10-28 校验治理移除闭集完备校验:
    漏分类的后果 = 本谓词族不消费该字段,估值零贡献,评审面把关)。"""
    if economy is None:
        return False
    for name, default in _ENGINE_CHANNEL_SINGLE_FIELDS:
        if getattr(economy, name) != default:
            return True
    for amt, cnt in _ENGINE_CHANNEL_PAIR_FIELDS:
        if getattr(economy, amt) != 0 and getattr(economy, cnt) != 0:
            return True
    return False


def strategy_loss_battle_modifier(active_names: list[str]) -> tuple[int, bool]:
    """持卡败局修饰聚合(战斗结算修饰族首例 嘴硬):败局额外扣血求和、
    连胜维持取或。

    逐名归一后直读 :data:`STRATEGY_ECONOMY` 现值(卡直读禁
    ``aggregate_economy``:其聚合字段集不含战斗结算修饰族字段,误走 =
    静默漏读);表外卡名跳过。零 rng 零副作用纯读;sim 结算帧调用,
    live 零消费(游戏自算,结算屏观察覆盖)。返回 ``(hp_extra_sum,
    keep_any)``。
    """
    hp_extra_sum = 0
    keep_any = False
    for name in active_names:
        eff = STRATEGY_ECONOMY.get(normalize_invest_name(str(name or '')))
        if eff is None:
            continue
        hp_extra_sum += eff.loss_hp_extra
        keep_any = keep_any or eff.keep_streak_on_loss
    return hp_extra_sum, keep_any


# 引擎字段三分类常量的完备校验已随 2026-10-28 校验治理移除(闭集缺位/
# 互斥/默认值一致三类均只能由开发动作自身触发,防笔误类;新字段漏分类的
# 后果 = 谓词族不消费该字段 = 估值零贡献,评审面把关)。


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
      先例 = T-5 财富宝钻随机态获得/T-29 全奖励分支随机态)。
      首例 = 红钻贵族。
    - replaces_opening_supply: True = 该环境的获得替换开局补给(on_env_gained
      先清席后发放,首例 = 人才储备 id 144「开局补给替换为3个随机3费角色」
      直读)。清席面 = bench 上 kind='unit' 槽(开局补给物 = 初始角色;
      占席道具类槽不在替换面——开局窗该形态结构性不存在,防御性保留);
      部署行/溢出席开局窗恒空,不触。登记语义:True 必须产出替代者
      (角色支非空)——开局补给物 = 角色,道具/装备支不算;按登记纪律
      自守,防呆校验已随治理口径移除(2026-10-28 用户裁定,
      _validate_env_gifts docstring;仅环境域消费,策略表登记本字段 =
      惰性无消费,开箱分支先例同待遇)。
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
    # id 301001/301002)。两卡条件分支卡文逐字同文 → 三元组同值;棱彩加强值
    # 只在 instant_gold(26 vs 45)。条件分支发放经节点桥(§3.3.6)。
    '本金充裕': EconomyEffect(instant_gold=26, free_refresh_cond_gold_above=50,
                              free_refresh_cond_gold_step=10, free_refresh_cond_cap=3),
    # 存款回报:官方「每次进入新节点时,如果在上个节点没有花费金币,则获得
    # 2次免费刷新。」(cw_invest_data.py:40,id 100501)。条件判定族第二形
    # (花费布尔条件;本金充裕系=金梯度条件):单字段双职(次数+激活开关),
    # 条件输入置位 = 四花费通道 mark_gold_spent,节点边界滚位 =
    # roll_prev_node_spent(评估毕复位);发放经节点桥条件腿自动生效
    # (prev_node_spent=False 才授予,None 保守零授予)。
    '存款回报': EconomyEffect(free_refresh_cond_prev_node_unspent=2),
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
    # (cw_invest_data.py:112,id 200301)。两条分支分载:「现在」立即分支 =
    # free_refresh_burst=1(选卡登记期发放,载体惯例同固定理财/乱成一锅粥);
    # 持续分支 = free_refresh_per_node=1。当节点发放核查结论(逐效果 a/b)单一源 =
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
    '成本控制': EconomyEffect(instant_gold=8, hp_instant=15),
    '剩余价值': EconomyEffect(gold_per_node=1),
    '四费晋升': EconomyEffect(instant_gold=12),
    '小复制+': EconomyEffect(instant_gold=13),
    '小复制': EconomyEffect(instant_gold=7),
    '长期主义+': EconomyEffect(gold_next_nodes_amount=9, gold_next_nodes_count=3),
    '长期主义': EconomyEffect(gold_next_nodes_amount=7, gold_next_nodes_count=3),
    '大裁员': EconomyEffect(free_refresh_burst=6, sell_price_mult=2.0),
    # ↑ 免费刷 + 卖价×2。free_refresh_burst=6 = 官方卡文直读(base 层
    #   plaza:202101,cw_invest_data.py:134),反转裁定 = 以官方卡文为准
    #   (fields.md §3.3.5 burst 来源族 + §4 SellBench 修饰行在册);注册值
    #   原为 5 = 已裁漂移且无运行时消费点(当时无 STRATEGY_EFFECTS 条目,
    #   两桥不触发),非任何一端的现行行为——「6 次免费刷新」真正落码载体
    #   = STRATEGY_EFFECTS['大裁员'] 条目(burst 桥同条目双载),本注册行
    #   = 估值面与条目载荷的对账源。卖价 ×2 施于净额/基础价 = 缺口 G4 待
    #   实采(fields.md §4 SellBench 修饰行单一源),闭合前退款按基础公式。
    # 嘴硬:败局修饰两腿 = 卡面「受到的小队生命值伤害提高5点/维持原来的连胜数」
    #   直读;消费 = strategy_loss_battle_modifier 聚合 + sim 结算 hp 腿与
    #   streak 转移形参(读法边界见字段注)。金腿「获得6金币」选卡当场在册。
    '嘴硬': EconomyEffect(instant_gold=6, loss_hp_extra=5, keep_streak_on_loss=True),
    '秘密典籍+': EconomyEffect(instant_gold=12),
    '秘密典籍': EconomyEffect(instant_gold=8),
    '经验就是财富': EconomyEffect(instant_gold=4),
    '二极管': EconomyEffect(instant_gold=6, hp_instant=10,
                            encounter_tier_extremes_only=True),
    # ↑ hp=卡面「获得10小队生命值和生命上限」即时半句直读(hp_max 半句
    #   零建模,缺口 = cw_affix_effects 四源注);收窄旗标 = sim 呈现面
    #   encounter_options_for 消费(端点全档首尾派生,本表无数值)。
    '免费升舱': EconomyEffect(instant_gold=4),
    '无害垃圾': EconomyEffect(instant_gold=8),
    '胜利,还是胜利': EconomyEffect(instant_gold=4, streak_set=4),
    '打捞人才库+': EconomyEffect(instant_gold=4),
    '尾款交付': EconomyEffect(gold_at_final_supply=30),
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
    # 合并同类项(id 102901):「刷新商店时，若刷新的角色中出现2个相同的角色，
    # 获得1金币。获得4次免费刷新。」(cw_invest_data.py:69 卡面直读)。金腿 =
    # 刷新事件条件金,登记形态等值迁移自 instant_gold——「选牌当场给金」的
    # 一次性语义与卡文「每次刷新条件触发」时点错位;双登记会在未来 instant_gold
    # 世界发放腿建模时与本腿双发(需排除集特判 = 埋雷),迁移治本。发放 =
    # 刷新上报随机态腿后检查腿(cw_effect_inventory.apply_on_refresh_pair_
    # gold_grant,sim 装配态观察通道);估值 = 条件概率型(出对频次分布未采)
    # fail-closed 0,策略侧待建模桶在册(strategy_economy._PENDING_MODELING_
    # FIELDS);burst 4 刷经获得链登记腿自动发放。
    '合并同类项': EconomyEffect(gold_per_refresh_pair=1, free_refresh_burst=4),
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
    '固定理财': EconomyEffect(xp_instant=4, xp_per_plane=4,
                              free_refresh_burst=2, free_refresh_per_plane=2),
    # ↑ 「现在以及每个位面开始时,获得4经验值和2次免费刷新」双腿分段:
    #   即时段(xp_instant/burst,登记期发放)+ 位面段(xp_per_plane/
    #   free_refresh_per_plane,策略域位面周期发放首例)——位面段刷新支经
    #   效果推进 tick 位面开始桥(cw_game_state.apply_effect_plane_start_
    #   grant)、XP 支经 sim 位面首节点窗腿(cw_sim_backend);中途拿卡时
    #   所在位面(已开始)位面段登记拍全额补发 = 用户裁定 2026-11-01 拍定,
    #   承载 = apply_effect_plane_refire_grant(语义正本 = STRATEGY_EFFECTS
    #   本卡条目 notes)
    '固定理财+': EconomyEffect(xp_instant=6, xp_per_plane=6,
                              free_refresh_burst=3, free_refresh_per_plane=3),
    # ↑ 「现在以及每个位面开始时,获得6经验值和3次免费刷新」双腿分段
    #   (姊妹行同构):即时段(xp_instant/burst,登记期发放)+ 位面段
    #   (xp_per_plane/free_refresh_per_plane)——位面段刷新支经效果推进
    #   tick 位面开始桥(cw_game_state.apply_effect_plane_start_grant)、
    #   XP 支经 sim 位面首节点窗腿(cw_sim_backend);中途拿卡时所在位面
    #   (已开始)位面段登记拍全额补发与姊妹固定理财同判(用户裁定
    #   2026-11-01),承载 = apply_effect_plane_refire_grant(语义正本 =
    #   STRATEGY_EFFECTS 本卡条目 notes)
    '空仓+': EconomyEffect(xp_instant=10),
    '经验到账': EconomyEffect(xp_instant=10),
    '气氛组+': EconomyEffect(xp_instant=8),   # 即时腿;条件腿(战斗结束零伤害角色计数)无字段载体,PENDING 在册
    '免战牌': EconomyEffect(xp_instant=30),
    # ↑ 免战牌经验半句(id 151301「获得30点经验」)——选牌当场即时型,
    #   xp_instant 字段分派通用通道(sim 选卡落地拍腿)自动覆盖并现金
    #   计分;跳过机制本体非经济流,由 STRATEGY_EFFECTS 条目次数余量
    #   承载(duration_uses=2)。本行 = 条目 payload 的单一源(条目改引
    #   同一实例,登记时代旧口径 = 条目内联 EconomyEffect)。
    '健康充值': EconomyEffect(hp_instant=30),   # 即时 hp 腿(卡面数值直读);+30 上限半句
                                                # hp_max 字段缺位零建模,缺口申报单一源 =
                                                # fields.md HP 面行
    '先亏后盈': EconomyEffect(hp_instant=-20),
    # ↑ 损血即时腿 = 卡面「损失20点小队生命值」数值直读取负(desc 明写
    #   20,非设计数);延时腿(4 节点 2 箱)另走 STRATEGY_DELAYED_GRANTS,
    #   两腿分道登记。负值 = sim 选卡落地拍扣血(直加不 clip,下界无消费端
    #   语义镜像 +30 上界裁决),写端与损血档位触发扩挂点 =
    #   apply_strategy_pick_hp 负值支;同字段正负成员并存(健康充值 +30 /
    #   本卡 −20),字段分派通用通道自动双向覆盖。
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
    #   (v_c/a_c 池面改写;消费规范单一源 = fields.md「市场干预」节,
    #   docs/develop/sr_od/application/currency_war/game_state/fields.md;
    #   burst 5 刷发放面 = STRATEGY_EFFECTS 本卡条目登记腿)
}


# ===== curated overlay:策略效果规格 EffectSpec(效果清单骨架实现;手维护,键=注册表规范名)=====
# 机制 = cw_effect_inventory.py(EffectSpec/ActiveEffectInventory);本 overlay 只放**数据**,
# 与 STRATEGY_ECONOMY 同键空间同孤儿校验(见 _validate_strategy_effects),防两套 overlay 漂移。
# 首条语义全引 cw_invest_data 官方原文;二义条目 pending=True + notes 保守支,不拍死——
# 定案后回填 verdict(单一语义以实采为准)。
# 边界:只产策略源;环境('portal')/词缀('affix')双源注册属环境/词缀效果适用范围,此处不建其条目。
# ===== 超发货币单卡判别常量(金面播值负债卡首例)=====
# 负债播值腿(kernel 获得链登记腿)与 sim 清零/回流两腿共用的条目判别键,
# 集中此处防字面量散落(cw_gain_chain/cw_sim_backend 双消费)。与注册表的
# 一致性由 _validate_strategy_effects id 双匹配闸兜底(漂移 import 即炸),
# 键×id 对拍另有测试直锁。
HYPEREMIT_SPEC_ID: str = '202501'
HYPEREMIT_SPEC_NAME: str = '超发货币'

# ===== 大扩招扣金计划(策略卡扣金腿的现算单一源)=====
# 卡文「每损失4金币，获得一个随机4费角色，最多扣除40金币」(cw_invest_
# data.py id 203101)的三结构常数与现算函数。消费两端 = sim 扣金负腿
# (cw_sim_backend 选卡落地拍,世界真值)与获得链随机角色腿
# (cw_gain_effects 效果体,发放数量)——数量口径必须同源,分写两处会
# 在基数变化时漂移。放 kernel:两消费端中 sim 在 sim 包,import 方向
# 只允许 sim→kernel(kernel 模块级禁 import sim,gain-chain 模块边界),
# 故函数不能住 sim 侧。

#: 卡文「每损失4金币」直读(步进单位)。
RECRUIT_STEP_GOLD: int = 4
#: 卡文「最多扣除40金币」直读(扣金上限)。
RECRUIT_MAX_DEDUCT: int = 40


def dakuozhao_deduction_plan(gold: int) -> tuple[int, int]:
    """大扩招扣金计划(扣金额, 角色数),纯函数。

    ``n = min(gold // 4, 10)``;扣金 = ``n * 4``。取整读法 = 只扣
    4 的整数倍、余金保留:「每损失4金币」按步进单位整数倍计,残金
    不消失;全扣式(扣 min(gold, 40) 再整除)会出现「扣了金没发角色」
    的残金损失,与交换率字面相悖且无先例支撑。
    """
    n = min(gold // RECRUIT_STEP_GOLD,
            RECRUIT_MAX_DEDUCT // RECRUIT_STEP_GOLD)
    return n * RECRUIT_STEP_GOLD, n


STRATEGY_EFFECTS: dict[str, EffectSpec] = {
    # 淘金客:官方「你每次消耗金币刷新商店,都会获得2经验值」;免费刷不产 XP(「消耗金币」
    # 文本充分;实采复核待办)。姿态谓词/CwActionLevelUpParam 抑制属淘金客姿态面适用范围,现不接。
    '淘金客': EffectSpec(
        id='301601', name='淘金客', trigger=TriggerKind.ON_REFRESH,
        duration=DurationKind.WHILE_HELD, category=EffectKind.STATE,
        payload=STRATEGY_ECONOMY['淘金客'], duties=DutyFlags(respond=True),
        notes='每次付费刷新+2XP;查询键 xp_per_refresh'),
    # 固定理财:官方「现在以及每个位面开始时,获得4经验值和2次免费刷新」。
    # 双腿分段:即时段(现在)= xp_instant+free_refresh_burst 登记期发放;
    # 位面段 = xp_per_plane+free_refresh_per_plane 位面开始发放(刷新支 =
    # kernel 推进 tick 位面开始桥 apply_effect_plane_start_grant、XP 支 =
    # sim 位面首节点窗腿)。中途拿卡时所在位面(已开始)是否补发位面段
    # 曾为二义冻结面,用户裁定(2026-11-01)拍定补发:登记时点判位面已
    # 开始 → 登记拍全额补发(非按比例),后续位面开始事件照常——承载 =
    # kernel 登记拍补发桥 apply_effect_plane_refire_grant(刷新支)+ sim
    # 选卡拍补发 XP 腿(apply_strategy_plane_refire_xp);原保守支(不补
    # 发)随裁定消解,pending 撤除。族级:同触发词族稿(公司严选/终身学习)
    # 明文共享本裁定不另立键。
    '固定理财': EffectSpec(
        id='201801', name='固定理财', trigger=TriggerKind.PLANE_START,
        duration=DurationKind.PERMANENT, category=EffectKind.STATE,
        payload=STRATEGY_ECONOMY['固定理财'], duties=DutyFlags(track=True, respond=True),
        notes='双腿分段:即时段(现在)=xp_instant+free_refresh_burst 登记期'
              '发放;位面段=xp_per_plane+free_refresh_per_plane 位面开始发放'
              '(刷新支=kernel 推进 tick 位面开始桥、XP 支=sim 位面首节点窗'
              '腿);中途拿卡所在位面(已开始)位面段登记拍全额补发(用户'
              '裁定 2026-11-01 拍定,原保守支不补发随裁定消解)'),
    # 固定理财+:官方「现在以及每个位面开始时,获得6经验值和3次免费刷新」。
    # 与姊妹固定理财卡文同构(6/3),双腿分段/发放载体/中途拿卡补发读法
    # 全量同判(用户裁定 2026-11-01 对两卡一次拍定,语义正本 = 姊妹条目
    # 注释;裁决联动禁两态)。
    '固定理财+': EffectSpec(
        id='201802', name='固定理财+', trigger=TriggerKind.PLANE_START,
        duration=DurationKind.PERMANENT, category=EffectKind.STATE,
        payload=STRATEGY_ECONOMY['固定理财+'],
        duties=DutyFlags(track=True, respond=True),
        notes='双腿分段:即时段(现在)=xp_instant+free_refresh_burst 登记期'
              '发放;位面段=xp_per_plane+free_refresh_per_plane 位面开始发放'
              '(刷新支=kernel 推进 tick 位面开始桥、XP 支=sim 位面首节点窗'
              '腿);中途拿卡所在位面(已开始)位面段登记拍全额补发(用户'
              '裁定 2026-11-01 拍定,与姊妹固定理财同判)'),
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
        notes='代买使「牌自己消失」,商店读牌/买牌对账必须预知(挂时序实证归采集批);腿3 自动购买零登记 = bot 双端零响应(触发面型① eligible 载体未建,scoped 决策禁落放弃表防锚死后继族);召唤单位零建模,实机名待族级实机取证批'),
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
    # 归类同族:全员晋升/人力重组/大裁员/现金为王=即时全场板面重写/出售)。
    '人力重组': EffectSpec(
        id='102801', name='人力重组', trigger=TriggerKind.INSTANT,
        duration=DurationKind.ONCE, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(board_rewrite=BOARD_REWRITE_SELL_ALL_DEAL),
        duties=DutyFlags(predict=True),
        notes='全场出售事件;执行时序编排(卖→发牌);'
              '写归属=出售面逻辑写/发牌面 live 观察收口·sim 发牌腿承接'
              '(cw_sim_backend.apply_strategy_pick_sell_all_deal)'),
    # 大裁员:官方「出售场上和备战席的所有角色，获得双倍价格的金币。获得6次免费刷新。」
    # (cw_invest_data.py:134)。卖全场族注册卡,板面重写桥素出售语义清场+基础
    # 公式退款;发牌腿非本卡卡文面(sim 发牌判据按语义值细分,素出售不入集,
    # 防假 2★ 注入)。刷腿 = free_refresh_burst=6 挂战场载体(burst 桥登记拍
    # 单次发放,载体扩字段首例双载——选卡一次性发放与 board_rewrite 清场
    # 两桥同条目各司其职);×2 卖价修饰缺口 G4 申报见 STRATEGY_ECONOMY
    # 注册行注。
    '大裁员': EffectSpec(
        id='202101', name='大裁员', trigger=TriggerKind.INSTANT,
        duration=DurationKind.ONCE, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(board_rewrite=BOARD_REWRITE_SELL_ALL,
                                  free_refresh_burst=6),
        duties=DutyFlags(predict=True),
        notes='卖全场+6 刷选卡当场;×2 卖价修饰缺口 G4 待实采(净额/基础价),'
              '退款按基础公式'),
    # 降本增效:官方「出售场上和备战席的所有角色，获得双倍价格的金币。
    # 你接下来6次购买角色是免费的。」(cw_invest_data.py:136)。卖全场族
    # 素出售第二张注册卡(姊妹大裁员同构出售腿;人力重组走 _DEAL 值非素);
    # 卖价 ×2 修饰 = sell_price_mult(STRATEGY_ECONOMY 在册),退款施径 =
    # 缺口 G4(fields.md §4 SellBench 修饰行单一源),闭合前退款按基础公式。
    # 免费购买腿 = 次数类余量载体(duration_uses=6 → remaining_uses,免战牌
    # 首例机制):uses 维度与 duration 类别独立播种(_seed_progress),
    # duration=ONCE 只注记出售腿一次性语义;递减挂点 = 买牌上报单点
    # (report_action_buy_card_param,按张计,k 张 = k 次),用尽移除。
    '降本增效': EffectSpec(
        id='202301', name='降本增效', trigger=TriggerKind.INSTANT,
        duration=DurationKind.ONCE, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(board_rewrite=BOARD_REWRITE_SELL_ALL),
        duties=DutyFlags(predict=True, track=True),
        duration_uses=6,
        notes='卖全场+双倍卖价缺口 G4 待实采(净额/基础价),退款按基础公式;'
              '6 次购买免费(remaining_uses 正本,买牌上报递减,用尽移除)'),
    # 躺平:官方「你无法在商店购买角色和刷新,持续3个节点。在此之后,获得20金币」。
    # inventory 余期追踪首例(remaining_nodes 3→0 移除);冻结姿态属姿态面适用范围。
    '躺平': EffectSpec(
        id='102001', name='躺平', trigger=TriggerKind.CONDITIONAL,
        duration=DurationKind.N_NODES, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['躺平'], duties=DutyFlags(track=True, respond=True),
        duration_nodes=3,
        pending=True,
        notes='禁买+禁刷 3 节点后 +20 金;待采:持续期读法(§10-3,登记当节点不推进守卫'
              '为现役保守读)与 +20 金入账时点(§10-4,保守支=N+3 节点入口入账)'),
    # 免战牌:官方「进入战斗节点时,直接跳过战斗并进入下一个节点,可生效2次。
    # 获得30点经验。」(cw_invest_data.py:109,PlazaAugment 151301)。建模批件
    # 落注册表条目(设计 §次三件 5):次数类余量首例
    # (duration_uses=2 → remaining_uses,§3.2.19 正本=effect_inventory
    # .remaining_uses,§8.6-3),递减挂点 = 跳过型出战上报(kernel
    # 出战 op 自上报(report_action_start_battle_param)
    # 子态,上报时递减——出战域重设计),用尽移除;sim 消费面 =
    # battle_skip 声明分支(跳过过程,战斗不发生、节点照常推进)。
    # +30 经验 = 选牌当场即时经验(xp_instant 通用通道;payload 引
    # STRATEGY_ECONOMY['免战牌'] 同一实例 = 单一源,选卡落地拍世界腿与
    # 估值现金计分同此行)。trigger=NODE_ENTER(跳过发生在
    # 进入战斗节点时点);归 STATE 族(发给自己的经验)而跳过机制本体由
    # 次数余量维度承载,不占 BattlefieldEffect 改写载荷。
    '免战牌': EffectSpec(
        id='151301', name='免战牌', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.STATE,
        payload=STRATEGY_ECONOMY['免战牌'], duties=DutyFlags(track=True),
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
    # instant_gold 26/45,条件分支两卡逐字同文同值。
    '本金充裕': EffectSpec(
        id='301001', name='本金充裕', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['本金充裕'], duties=DutyFlags(),
        notes='条件免费刷 50/10/3 经节点桥发放;instant_gold=26 选卡当场'),
    '本金充裕+': EffectSpec(
        id='301002', name='本金充裕+', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['本金充裕+'], duties=DutyFlags(),
        notes='条件分支与本金充裕逐字同文(50/10/3);加强值=instant_gold 45'),
    # 加油站:官方「现在及每次进入新节点时获得1次免费刷新,立刻获得8金币」
    # (cw_invest_data.py:112,id 200301)。入册使两条分支经现行挂点生效:获得链
    # 登记分支(kernel/cw_gain_chain.py::gain_invest_strategy)
    # burst 桥发「现在」分支 +1;节点边界桥(per-node 形态)发持续分支。拿卡
    # 当节点不重复发:登记晚于本节点边界推进,advance_node 同节点去重位
    # 关闸。行为核查结论单一源 =
    # docs/game/currency_war/research/per_node_pick_node_grant.md。
    '加油站': EffectSpec(
        id='200301', name='加油站', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['加油站'], duties=DutyFlags(),
        notes='「现在」+1 刷=burst 分支登记期发放;每节点 +1=节点边界桥;'
              'instant_gold=8 选卡当场'),
    # 免费午餐:官方「获得11次免费刷新。」(cw_invest_data.py:36,id 100301)。
    # 登记期一次性发放的定性 = per_node_pick_node_grant.md §4 惯例表
    # (纯立即型,无持续部分);卡文无「现在/立刻」措辞不触发「拿卡当节点
    # 不发放」反推——该反推只辖需拆分立即/持续两段发放时点的卡,本卡
    # 整卡即一段。入册使获得链登记腿 burst 桥按 payload.free_refresh_burst
    # 一次性发放(live/sim 同链);同族其余挂值卡单卡边界另批接线。
    '免费午餐': EffectSpec(
        id='100301', name='免费午餐', trigger=TriggerKind.INSTANT,
        duration=DurationKind.ONCE, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['免费午餐'], duties=DutyFlags(),
        notes='「获得11次免费刷新」=burst 腿,获得链登记期发放'),
    # 存款回报:官方「每次进入新节点时,如果在上个节点没有花费金币,则获得
    # 2次免费刷新。」(cw_invest_data.py:40,id 100501,T-92)。条件判定族
    # (形态镜像本金充裕):触发=节点进入、条件=上节点未花费
    # (prev_node_spent=False)、授予=2;发放经节点桥条件腿自动生效
    # (未写 None = 保守零授予禁猜);无即时腿(卡面无「现在/立刻」段)→
    # burst 桥对本条目零额度 no-op。counter 不建(授予量恒 2 无累计量),
    # duties 全空(无计数器/无预知/无姿态消费面)。payload 引
    # STRATEGY_ECONOMY 同一实例(单一源)。
    '存款回报': EffectSpec(
        id='100501', name='存款回报', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['存款回报'], duties=DutyFlags(),
        notes='条件免费刷 2/节点:上节点未花费才授予,经节点桥发放;无即时腿'),
    # 打捞人才库:官方「每次进入补给阶段后，随机获得一个未被选择的角色
    # 及其携带的装备。」(cw_invest_data.py,id 100701)。触发面 =
    # SUPPLY_PHASE(枚举成员随本条目首个在册使用);发放域 = 补给未选列
    # (世界既有列,SupplyOption 具名结构,非注册表池)→ BATTLEFIELD
    # 载体(发放类世界写入非 ECONOMY/STATE 载体形态),新字段
    # salvage_unchosen_supply = 本卡取值语义。检查函数 =
    # cw_effect_inventory.check_strategy_supply_salvage(挂观察上报尾部,
    # 直查 active_strategies 不消费条目——登记与消费分离现役形态);
    # STRATEGY_GRANTS 不入册(具名-only 宪章:发放物 = 世界既有列,
    # 非「获得…角色名」直读,不可具名)。触发语义二义保守支 =
    # R-entry 读法(进入补给阶段 N+1 首个成功观察帧消费阶段 N 未选列;
    # 官方文本对照:全都要·银同域「未选择」带显式「选择后」时点措辞),
    # pending=True 待实采定案(披露键 strategy_salvage_trigger_entry_reading)。
    '打捞人才库': EffectSpec(
        id='100701', name='打捞人才库', trigger=TriggerKind.SUPPLY_PHASE,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(salvage_unchosen_supply=True),
        duties=DutyFlags(),
        pending=True,
        notes='待采:触发二义保守支=R-entry 读法(进入下一补给阶段时点'
              '发放,源=上一阶段选定时刻未选列;裁 R-choice 则改值)'),
    # 打捞人才库+:姊妹展开卡(id 100702),句 1 与基础卡逐字同文 → 主腿
    # 同 payload 同 trigger 纯登记(机制单一源 = 基础卡条目 + 检查函数,
    # 本批零新设计;持卡判定 = 名单集 _SALVAGE_STRATEGY_NAMES 双名,集合
    # 语义防同持双发)。句 2「获得1个随机简易装备和4金币」三面拆分注记
    #(先例 = 商业间谍条目拆分注记):
    # ① 主腿(未选列打捞)= 本条目辖域,触发二义沿基础卡保守支 R-entry,
    #    pending=True 同判据;
    # ② 句 2 装备腿 = 获得时点效果体,归 cw_gain_effects.PICK_INVEST_
    #    EFFECTS(非本条目),时点保守支 = R-instant,披露键
    #    strategy_salvage_plus_instant_reading;
    # ③ 句 2 金腿 = STRATEGY_ECONOMY instant_gold=4 在册零动,发放端
    #    缺口 = 族级待办(T-112 公司人才流动同款),非本条目辖域。
    '打捞人才库+': EffectSpec(
        id='100702', name='打捞人才库+', trigger=TriggerKind.SUPPLY_PHASE,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(salvage_unchosen_supply=True),
        duties=DutyFlags(),
        pending=True,
        notes='待采:主腿触发二义沿基础卡(100701)保守支=R-entry 读法;句2 '
              '装备腿=获得时点效果体归 PICK_INVEST_EFFECTS,时点保守支='
              'R-instant(披露键 strategy_salvage_plus_instant_reading);'
              '句2 金腿=STRATEGY_ECONOMY instant_gold=4 在册零动,发放端'
              '缺口=族级待办非本条目辖域'),
    # 全队的希望:官方「处在前台1号位的我方角色获得15%伤害增幅和15%生命增幅。」
    # (cw_invest_data.py:45,PlazaAugment 101001)。战力类零响应登记
    # (invest_effects.md §0 战力类行:不进经济模型;EffectKind.UNIT_BUFF
    # 「游戏侧自算,bot 仅登记零响应」),策略源 UNIT_BUFF 首条 = ~155 战力类
    # 后继登记形态的模式卡。trigger 占位形对齐环境源 _portal_placeholder_spec
    # 先例(无离散触发事件,duties 全空零消费);effect_text 经数据面表达式
    # 单一源,版本更新改文自动跟随。
    '全队的希望': EffectSpec(
        id='101001', name='全队的希望',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '101001')),
        duties=DutyFlags(),
        notes='战力类零响应登记(策略源 UNIT_BUFF 模式卡首条);'
              '游戏侧自算,bot 仅登记;无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 幸运星祝福:官方「获得1个【幸运星】」(cw_invest_data.py, id 230101)。
    # 战力类零响应登记(祝福族首例):祝福面游戏侧自算,bot 零响应;
    # effect_text 经数据面表达式单一源,版本更新改文自动跟随。
    '幸运星祝福': EffectSpec(
        id='230101', name='幸运星祝福',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '230101')),
        duties=DutyFlags(),
        notes='战力类零响应登记(祝福族首例);'
              '游戏侧自算,bot 仅登记;无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    '折叠小刀祝福': EffectSpec(
        id='230201', name='折叠小刀祝福',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '230201')),
        duties=DutyFlags(),
        notes='战力类零响应登记(祝福族第 2 条);'
              '游戏侧自算,bot 仅登记;无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    '和平手枪祝福': EffectSpec(
        id='230301', name='和平手枪祝福',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '230301')),
        duties=DutyFlags(),
        notes='战力类零响应登记(祝福族第 3 条);'
              '游戏侧自算,bot 仅登记;无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    '生命之花祝福': EffectSpec(
        id='230401', name='生命之花祝福',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '230401')),
        duties=DutyFlags(),
        notes='战力类零响应登记(祝福族第 4 条);'
              '游戏侧自算,bot 仅登记;无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    '量产型装甲祝福': EffectSpec(
        id='230501', name='量产型装甲祝福',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '230501')),
        duties=DutyFlags(),
        notes='战力类零响应登记(祝福族第 5 条);'
              '游戏侧自算,bot 仅登记;无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 成长基金:官方「在你到达9级时，提供40金币。」(cw_invest_data.py:56,
    # id 101701)。数值/形状 = STRATEGY_ECONOMY 注册行在册零动(级数配对
    # 字段 gold_at_level/gold_at_level_target,引擎排除桶一次性金族——
    # 时点大额无持续语义,不参与 is_economy_engine 判定)。trigger 占
    # CONDITIONAL:词表注释明列本卡(LEVEL_UP = 每次升级语义,本卡仅
    # 9 级一次,不占);世界发放腿 = sim 到级检查函数
    # (kernel/cw_gain_chain.check_strategy_level_grants,advance 双点接
    # 线,现役 sim 经验常量下 9 级不可达 = 休眠正确路径,gain-chain.md
    # §2.12);登记条目本批零行为消费(登记端可见性优先,成功经验同姿
    # 态),行为在检查函数不经 inventory 条目驱动。duties 全空(无计数
    # 器/无预知/无姿态消费面,本金充裕同形态);burst/板面两桥零行为
    # (payload 无 instant/burst 字段、非 BattlefieldEffect)。
    '成长基金': EffectSpec(
        id='101701', name='成长基金', trigger=TriggerKind.CONDITIONAL,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['成长基金'], duties=DutyFlags(),
        notes='一次性到级金门:到达 9 级 +40(级数配对字段 '
              'gold_at_level/gold_at_level_target,引擎排除桶一次性金族);'
              '世界发放腿 = sim 到级检查函数(check_strategy_level_grants),'
              'trigger 占 CONDITIONAL 沿成功经验同族先例(词表 CONDITIONAL '
              '注释明列本卡)'),
    # 武力刷新:官方「合成装备时，获得2次刷新。」(cw_invest_data.py:57,
    # id 101801)。策略源 ON_MERGE 首条(词缀源先例 = 变宝为废,异表异链
    # ——该条在 AFFIX_EFFECT_SPECS,不入本表故天然不在本发放腿辖域);
    # 世界发放腿 = 穿戴上报函数 applied 出口合成事件检查
    # (apply_on_merge_refresh_grant,合成次数 = 输入件数−输出件数),
    # 发放进 free_refresh_left(三写端之发放登记第三写端)。登记期两桥
    # 对本 payload 零额度/非战场 = no-op;数值单一源 = STRATEGY_ECONOMY
    # 同一实例。
    '武力刷新': EffectSpec(
        id='101801', name='武力刷新', trigger=TriggerKind.ON_MERGE,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['武力刷新'], duties=DutyFlags(),
        notes='每次装备合成 +2 免费刷新,经穿戴上报合成事件腿发放;'
              '官方限定装备合成(角色升星另域,fields.md §5.3 分开计数禁混账)'),
    # 星星相印:官方「每次合成3星角色时，获得5金币。立刻获得1个【员工投影
    # 仪】。」(cw_invest_data.py:83,id 104001)。策略侧 ON_MERGE 后继条目
    # (首条 = 武力刷新):触发面归一口径 = 角色 3 星合成共用 ON_MERGE 载体,
    # 两事件域由「生产点分离 + payload 字段判别」保证零交叉——本卡发放腿只
    # 认角色合成生产点(buy/gain 两域 check_strategy_star_merge_gold),装备
    # 合成域经 apply_on_merge_refresh_grant 名单集另路,本 payload 无
    # refresh_per_compose 字段、反向同构,双向鸭子缺省 0 天然隔离
    # (fields.md §5.3 分开计数禁混账)。世界发放腿 = 合成事件条件金(仅 sim
    # 装配态经观察通道发金,live 零写观察覆盖兜底);装备腿 = PICK_INVEST_
    # EFFECTS 登记行(员工投影仪 ×1,具名装备授予工厂),两腿异族。duties
    # 全空(事件直结 = 计数门槛 N=1 退化形,无跨帧计数器/无预知/无姿态
    # 消费面);数值单一源 = STRATEGY_ECONOMY 同一实例。
    '星星相印': EffectSpec(
        id='104001', name='星星相印', trigger=TriggerKind.ON_MERGE,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['星星相印'], duties=DutyFlags(),
        notes='每次合成3星角色 +5金经合成事件发放腿(角色合成生产点;装备'
              '合成域不经本条目,两域分开计数 fields.md §5.3);装备腿 = '
              '具名装备登记行另路(员工投影仪×1)'),
    # 节省工位:官方「在接下来3个节点只有3个备战席位置。随后，获得3件简易
    # 装备。」(cw_invest_data.PLAZA_AUGMENTS 同 id 行,id 101901)。容量时限族
    # 模式卡(在册唯一容量改写条目):容量窗本体 = 效果账本条目(N_NODES×3,
    # 余期追踪与窗口算术同躺平),容量消费走容器派生(bench_free_slots/
    # bench_is_full),经容量逻辑态直写桥 project_effect_capacity 逐拍回写
    # (payload.capacity_limit 声明契约);「随后」= 条目到期移除拍,构造性
    # 锁步——单一载体零第二账本(不走 STRATEGY_DELAYED_GRANTS 队列第二登记),
    # 到期 3 件简易装备 = tick 到期段发放腿 apply_effect_expiry_grants(策略源
    # N_NODES 到期面首个消费客户端)。duties 只 track:容量消费端读容器派生,
    # 无 predict(不做效果预知)/无 respond(姿态面不在范围)。
    '节省工位': EffectSpec(
        id='101901', name='节省工位',
        trigger=TriggerKind.CONDITIONAL,          # 条件窗口族(躺平同形)
        duration=DurationKind.N_NODES,
        category=EffectKind.BATTLEFIELD,          # 容量 = 备战/板面域
        payload=BattlefieldEffect(capacity_limit=3, expiry_simple_equips=3),
        duties=DutyFlags(track=True),
        duration_nodes=3,
        pending=True,
        notes='容量 3×3 节点后到期发 3 件简易装备;窗口读法沿 advance_node '
              '现役待实采旗(披露键 strategy_capacity_window_node_reading);'
              '到期发放物随机性=v0 假设——简易池独立均匀可重复,desc 未标'
              '「随机」(披露键 strategy_expiry_grant_simple_pool_uniform);'
              '进窗占席>3 行为不建模(披露键 '
              'bench_capacity_shrink_overflow_unmodeled)'),
    # 公司人才流动:官方「每次进入新节点时，处在备战席最右侧3个位置的角色变为
    # 随机的同费用角色。获得2金币。」(cw_invest_data.py:60,id 102101)。
    # bench_reroll 族(备战席区间重掷族)效果面首个登记条目 = 族模式卡;
    # 重掷面零执行端(游戏侧自行重掷,bot 备战帧观察收真值),登记腿三桥对
    # 本 payload 全零动作(no-op 回归哨 = test_gain_chain.py 两锁)。
    '公司人才流动': EffectSpec(
        id='102101', name='公司人才流动', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(bench_reroll=BENCH_REROLL_RIGHT3),
        duties=DutyFlags(track=True),
        notes='随机重掷面零逻辑写、观察收口(effect-domain.md §6.3/§6.4);'
              '区间=现役 capacity 尾 3 槽(与节省工位组合 capacity=3 时全席,'
              '实采可校正);辖域仅 kind=unit 槽(箱/典/书卡位不涉);星级分布/'
              '装备归属/被替换去向未采证(invest_effects.md 全员晋升行同式'
              '申报);拿卡当节点不重掷(per_node_pick_node_grant.md §4,'
              '无立即措辞,C 级佐证);+2 金=instant_gold=2 选卡当场 live '
              '游戏发放+观察收口,sim 无此金腿(选卡即时金缺口=族级既有'
              '待办,禁按双端生效找/建通道);族模式卡:姊妹乱成一锅粥/+'
              '换 BENCH_REROLL_LEFT6,双载荷裁决位(bench_reroll 需 '
              'BattlefieldEffect 载体、爆腿过 burst 桥需 EconomyEffect '
              '载体,EffectSpec 单 payload 字段不可并存)归族展开批先裁'),
    # 公司军火更新·银:官方「每次进入新节点时，你物品栏里的装备变为同品质的
    # 其他装备。获得1件随机简易装备。」(cw_invest_data.py:86,id 130101)。
    # 双腿异注册面组合卡:变异腿 = 本条目(NODE_ENTER 持续触发,「物品栏装备
    # 同品质变异」效果面首个登记条目 = 族模式卡);发放腿「获得1件随机简易
    # 装备」= cw_gain_effects 泛化随机装备表行('简易' 行,与打捞人才库+
    # 同池同形),两注册面各辖一腿零冲突(不经组合子:组合子辖同一效果体内
    # 多腿,本卡两腿异效果体)。变异面零执行端(游戏侧节点进入自行变异,
    # bot 备战帧 equips 整表观察收真值),登记腿三桥对本 payload 全零动作
    # (no-op 回归哨 = 测试锁)。
    '公司军火更新·银': EffectSpec(
        id='130101', name='公司军火更新·银', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(equips_reroll=EQUIPS_REROLL_SAME_QUALITY),
        duties=DutyFlags(track=True),
        notes='物品栏装备同品质变异面零逻辑写、观察收口(effect-domain.md '
              '§6.3 随机分支/§6.4 随机资产面);「同品质」=同 category 先验'
              '(冶金炉 same_category 在册先例 tool_use.py:82,未证);变异'
              '辖域类别集/是否排除自身/工具特殊类可变性未采证,零落码零消费'
              ';拿卡当节点不变异(per_node_pick_node_grant.md,无立即措辞,'
              'C 级佐证);duties 不设 predict(现役读链无节点进入前需预知'
              '物品栏变异的消费面);发放腿=泛化随机装备表行(简易 1 件,'
              '随机性由家族单键 strategy_random_equip_uniform 承载);族模式'
              '卡:金 230601 展开腿2=简易 2 件/彩 330601 展开腿2=特权 1 件,'
              '本条目 payload 复用同词表值'),
    '公司军火更新·金': EffectSpec(
        id='230601', name='公司军火更新·金', trigger=TriggerKind.NODE_ENTER,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(equips_reroll=EQUIPS_REROLL_SAME_QUALITY),
        duties=DutyFlags(track=True),
        notes='物品栏装备同品质变异面零逻辑写、观察收口(银卡同词表值);'
              '发放腿=泛化随机装备表行(简易 2 件,放回抽 T-167 判例,'
              '随机性由家族单键 strategy_random_equip_uniform 承载);'
              '族模式卡:银 130101/彩 330601 同源词表'),
    # 市场干预:官方「下一次和每4次商店刷新都将是全3费角色。获得5次刷新」。
    # payload 引 STRATEGY_ECONOMY 同一实例(单一源):free_refresh_burst=5 经
    # 获得链登记腿 burst 桥一次性发放(live/sim 同链,免费午餐 T-88 同形);
    # refresh_shop_rewrite_every_3cost=4 载改写面(引擎判据/聚合语义已在册)。
    # 改写面零功能写端:live 商店牌面观察即真值(采购专员同型);sim 世界
    # 真值缺强制 3 费面(不建模边界申报)。
    '市场干预': EffectSpec(
        id='102201', name='市场干预', trigger=TriggerKind.ON_REFRESH,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['市场干预'],
        duties=DutyFlags(track=True, predict=True, respond=True),
        notes='改写面=下一次+每4次刷新全3费(周期值载体='
              'refresh_shop_rewrite_every_3cost;计数面=duties.track 挂 '
              'CounterKey.REFRESH;采购专员·金/彩为同族 BattlefieldEffect '
              'counter_every 形态对照);待实机核:赠刷是否计入每4次计数/'
              '效果持续期(p40-refresh-ev.md 变体⑤);burst=5 登记期发放'),
    # 合并同类项:官方「刷新商店时，若刷新的角色中出现2个相同的角色，获得1金币。
    # 获得4次免费刷新。」(cw_invest_data.py:69,id 102901)。两腿:
    # ① burst=4 经获得链登记腿自动发放(live/sim 同链,免费午餐同形);触发面
    #    = ON_REFRESH/持续 = WHILE_HELD 为腿 B 的语义声明取准(桥/腿运行时不读
    #    trigger,发放过滤按 trigger∧category 与声明一致);
    # ② 金腿 = 每次手动刷新事件条件金——「刷新商店时」玩家语境 = 手动 D 牌,
    #    刷新触发闭集 = 节点切换 + 手动(docs/game/currency_war/research/
    #    economy.md),挂点 = 刷新上报 = 手动动作唯一生产点,节点切换自动全刷
    #    (sim deal_shop 另口)不经此口;辖域待实采,披露键
    #    STRATEGY_REFRESH_PAIR_SCOPE_UNVERIFIED 登记(cw_effect_inventory)。
    #    发放 = 刷新上报随机态腿后检查腿 apply_on_refresh_pair_gold_grant
    #    (逐 ON_REFRESH∧ECONOMY 条目过滤;sim_backend_installed 门控——
    #    sim 采样即世界真值、判定成立经观察通道发金,live 采样是猜测金面禁
    #    直写零写)。duties 全空(出对判定逐刷独立无累计量,无计数器/预知/
    #    姿态消费面);per-node/板面两桥对本 payload 零行为(字段全缺省)。
    '合并同类项': EffectSpec(
        id='102901', name='合并同类项', trigger=TriggerKind.ON_REFRESH,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['合并同类项'], duties=DutyFlags(),
        notes='刷新出对 +1 金经刷新上报随机态腿后检查腿(sim 真值判定,'
              'live 观察覆盖兜底);burst=4 获得链登记腿自动发放'),
    # 溜佩佩/溜佩佩+:官方「获得9金币，什么都没带的佩佩会在你的后排逛街，
    # 让小队获得1%前/后台强度。」/「获得15金币，…」(cw_invest_data.py
    # PLAZA_AUGMENTS 103401/103402)。三腿分治登记:金腿(9/15 金)=
    # STRATEGY_ECONOMY instant_gold 在册承载,不属本条目(选卡即时金世界
    # 写端缺口 = 族级待办禁直写);佩佩发放腿 = STRATEGY_GRANTS 登记 +
    # PICK_INVEST_EFFECTS 效果体(获得链分派);本条目只辖战力类腿(1%
    # 前/后台强度)= UNIT_BUFF 零响应登记(游戏侧自算 bot 仅登记)。
    # 无离散触发事件,trigger/duration 占位形(_portal_placeholder_spec
    # 先例);effect_text 经数据面表达式单一源,版本更新改文自动跟随。
    '溜佩佩': EffectSpec(
        id='103401', name='溜佩佩',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '103401')),
        duties=DutyFlags(),
        notes='战力类零响应登记(佩佩逛街 1% 前/后台强度);'
              '游戏侧自算,bot 仅登记;无离散触发事件,trigger/duration '
              '占位形'),
    '溜佩佩+': EffectSpec(
        id='103402', name='溜佩佩+',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '103402')),
        duties=DutyFlags(),
        notes='战力类零响应登记(佩佩逛街 1% 前/后台强度);'
              '游戏侧自算,bot 仅登记;无离散触发事件,trigger/duration '
              '占位形'),
    # 全都要·银:官方「本局游戏中，补给阶段的可选项减少2个。下1个补给阶段
    # 选择后，额外获得所有未选择的角色及装备。」(cw_invest_data.py:95,
    # id 131001)。卡面两句双腿分治,同卡双 spec **异键登记首例**——申报键
    # 约定正本(后继族卡沿用):同卡第二腿占 ``'<规范名>#<腿名>'`` 申报键,
    # spec.name 恒为规范名(孤儿/id 校验按 name 查,两形态过校验面一致);
    # 单取登记链 ``STRATEGY_EFFECTS.get(canon)`` 只自动登记 canon 键条目,
    # 申报键条目 = 纯注册表声明,经该链永不入效果账本。
    # 腿2(一次性全捞)占 canon 键(功能腿优先键位,族后继载体兼容):发放
    # 腿 = cw_effect_inventory.check_strategy_take_all_supply(挂补给选定
    # 上报三 applied 出口前,R-choice 时点——卡面「选择后」字面锚,与打捞
    # 人才库 R-entry 分立;登记与消费分离,检查函数直查 active_strategies
    # 不消费本条目);触发面 = SUPPLY_PHASE 第二在册使用。pending 保守支
    # 承载两件待实采:兜底轮配额消耗制(事件消耗制 A 案)与未选钻列钻归属
    # 零建模(披露键 strategy_take_all_unchosen_diamond_pending)。
    '全都要·银': EffectSpec(
        id='131001', name='全都要·银', trigger=TriggerKind.SUPPLY_PHASE,
        duration=DurationKind.ONCE, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(salvage_all_unchosen_supply=True),
        duties=DutyFlags(),
        pending=True,
        notes='待采:兜底轮配额消耗制保守支=事件消耗制(首个 applied 选择'
              '事件即耗,含内容全未知兜底轮;漏记列由观察覆盖承接)+ 未选钻'
              '列钻归属零建模(披露键 strategy_take_all_unchosen_diamond_'
              'pending)'),
    # 腿1(列数修饰 -2)占申报键(声明面条目):live 读链按实屏识别列数
    # 跟随,字段零消费挂点(sim 列数面零建模 = M18 简化域上游缺口);经
    # 单取登记链永不入效果账本,纯注册表声明。无未裁数值(-2 明写),
    # 不设 pending。分立理由 = payload 字段互斥 + pending 异构(腿2 带保守
    # 支/腿1 声明面),单 payload 不可并载两持续期语义(WHILE_HELD vs ONCE)。
    '全都要·银#supply_delta': EffectSpec(
        id='131001', name='全都要·银', trigger=TriggerKind.SUPPLY_PHASE,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(supply_option_delta=-2),
        duties=DutyFlags(),
        notes='列数修饰腿(声明面,申报键条目经单取登记链不入效果账本);'
              'live 读链实屏识别跟随零消费挂点,sim 列数面零建模'),
    # 全都要·金:官方「本局游戏中，补给阶段的可选项减少2个。下2个补给阶段
    # 选择后，额外获得所有未选择的角色及装备。」(cw_invest_data.py:150,
    # id 203501)。全都要族第二实例,双腿异键登记沿银卡首例(申报键约定正本
    # = 上方全都要·银条目注释),姊妹卡面同构唯「下 N 个」N = 配额差异。
    # 腿2(配额 2 逐事件全捞)占 canon 键:发放腿 =
    # cw_effect_inventory.check_strategy_take_all_supply 族共享引擎(配额
    # 单一源 = 该模块 _TAKE_ALL_SUPPLY_QUOTA map,银 1/金 2,挂点与银卡同三
    # applied 出口)。duration 用 WHILE_HELD 而非银卡 ONCE:「下2个」非一次
    # 性,ONCE 形在配额 2 下失真,配额耗尽即停语义由计数闩承载(免战牌用尽
    # 即停语义形)。pending 保守支沿银卡同形两件待实采。
    '全都要·金': EffectSpec(
        id='203501', name='全都要·金', trigger=TriggerKind.SUPPLY_PHASE,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(salvage_all_unchosen_supply=True),
        duties=DutyFlags(),
        pending=True,
        notes='待采:兜底轮配额消耗制保守支=事件消耗制(每个 applied 选择'
              '事件耗 1 格,含内容全未知兜底轮;漏记列由观察覆盖承接)+ 未选'
              '钻列钻归属零建模(披露键 strategy_take_all_unchosen_diamond_'
              'pending)'),
    # 腿1(列数修饰 -2)占申报键(声明面条目,银卡同形第二实例):live 读链
    # 按实屏识别列数跟随,字段零消费挂点(sim 列数面零建模 = M18 简化域上游
    # 缺口);经单取登记链永不入效果账本,纯注册表声明。无未裁数值(-2 明写),
    # 不设 pending。
    '全都要·金#supply_delta': EffectSpec(
        id='203501', name='全都要·金', trigger=TriggerKind.SUPPLY_PHASE,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(supply_option_delta=-2),
        duties=DutyFlags(),
        notes='列数修饰腿(声明面,申报键条目经单取登记链不入效果账本);'
              'live 读链实屏识别跟随零消费挂点,sim 列数面零建模'),
    # 团队力量·银:官方「每有一个已激活的非独立羁绊，小队就会获得3%前/后台强度。」
    # (cw_invest_data.py:98,PlazaAugment 150101)。战力类零响应登记
    # (invest_effects.md 战力类行:不进经济模型;EffectKind.UNIT_BUFF
    # 「游戏侧自算,bot 仅登记」),同形先例 = 全队的希望/溜佩佩/溜佩佩+ 条目。
    # 羁绊激活计数 = 游戏侧真值(实机 OCR 左面板激活数,currency_war_config.py:6);
    # 「非独立」= cw_factions.py 独立羁绊段七名排除,desc 明文。
    '团队力量·银': EffectSpec(
        id='150101', name='团队力量·银',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '150101')),
        duties=DutyFlags(),
        notes='战力类零响应登记(每有一个已激活的非独立羁绊 3% 前/后台强度,'
              '计数游戏侧自算,bot 仅登记);无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 应援团:官方「进入战斗时，如果后排至少有4个角色，我方小队速度增幅提高15%。」
    # (cw_invest_data.py:99,PlazaAugment 150201)。战力类零响应登记
    # (invest_effects.md 战力类行:不进经济模型;EffectKind.UNIT_BUFF
    # 「游戏侧自算,bot 仅登记」),同形先例 = 全队的希望/溜佩佩/溜佩佩+/
    # 团队力量·银 条目。条件「后排至少有4个角色」= 上阵后排计数(与备战栏
    # 分立,drag_cw_char.py:39 _ROWS 三键;后排容量 6-9),进入战斗时由
    # 游戏评估施加,bot 零消费(back_capacity_of 观察读口不接线);15%
    # 速度增幅由游戏自算。
    '应援团': EffectSpec(
        id='150201', name='应援团',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '150201')),
        duties=DutyFlags(),
        notes='战力类零响应登记(进入战斗时后排≥4 名小队 15% 速度增幅,'
              '游戏侧自算,bot 仅登记);无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 正能量:官方「进入战斗时，我方小队恢复等同于能量上限20%的能量。」
    # (cw_invest_data.py:100,PlazaAugment 150301)。战力类零响应登记
    # (invest_effects.md 战力类行:不进经济模型;EffectKind.UNIT_BUFF
    # 「游戏侧自算,bot 仅登记」),同形先例 = 全队的希望/溜佩佩/溜佩佩+/
    # 团队力量·银/应援团 条目。恢复型(非增幅光环)归类:能量为战斗内
    # 资源,与伤害减免同桶「战斗被动分支」(cw_gain_effects.py 三卡箱腿
    # 注释),sim 战斗零建模;「能量上限」基数 = 受益角色自身上限(装备
    # 同构措辞旁证:电光履·特权),游戏侧定义。
    '正能量': EffectSpec(
        id='150301', name='正能量',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '150301')),
        duties=DutyFlags(),
        notes='战力类零响应登记(进入战斗时小队每名角色恢复自身能量上限 20%,'
              '游戏侧自算,bot 仅登记);恢复型非增幅光环——能量为战斗内资源,'
              '与伤害减免同桶战斗被动分支(cw_gain_effects.py 三卡箱腿注释),'
              'sim 战斗 U01 零建模;「进入战斗时」无离散触发事件消费,'
              'trigger 占位形(对齐 _portal_placeholder_spec 先例);'
              '能量上限基数=受益角色自身(装备同构措辞惯例推断,非 desc 逐字,'
              '游戏侧定义,bot 零响应)'),
    # 完美开局:官方「战斗中，关卡进度小于40%时，我方小队前/后台强度提高40%。」
    # (cw_invest_data.py:101,PlazaAugment 150501)。战力类零响应登记
    # (invest_effects.md 战力类行:不进经济模型;EffectKind.UNIT_BUFF
    # 「游戏侧自算,bot 仅登记」),同形先例 = 全队的希望/溜佩佩/溜佩佩+/
    # 团队力量·银/应援团/正能量 条目。条件「关卡进度<40%」由游戏在战斗中
    # 评估(战斗内进度条机制见 docs/game/currency_war/research/combat.md
    # 「遭遇奖励=伤害进度达标制」条),读数定义游戏侧,bot 零消费不接线;
    # 「前/后台」与代码词表「前排/后排」(drag_cw_char.py:39 _ROWS)字面
    # 不同字,对应系判读非直译——全队两排泛用增幅无位置限定,零行为后果;
    # 数值 40% 由游戏自算。
    '完美开局': EffectSpec(
        id='150501', name='完美开局',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '150501')),
        duties=DutyFlags(),
        notes='战力类零响应登记(战斗中关卡进度<40% 小队前/后台强度提高40%,'
              '条件与数值游戏侧自算,bot 仅登记;关卡进度读法定义游戏侧,'
              '判读申报制不在读法间拍死);无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 效率员工奖:官方「进入战斗时，速度最高的三名角色及其忆灵速度增幅提高10%。」
    # (cw_invest_data.py:102,PlazaAugment 150601)。战力类零响应登记
    # (invest_effects.md 战力类行:不进经济模型;EffectKind.UNIT_BUFF
    # 「游戏侧自算,bot 仅登记」),同形先例 = 全队的希望/溜佩佩/溜佩佩+/
    # 团队力量·银/应援团/正能量/完美开局 条目。对象选择(速度排序取前三、
    # 及其忆灵绑定、并列取法)= 游戏侧定义,bot 零消费;速度真值与排序全
    # 游戏侧,sim 不建模速度。「及其忆灵」系官方卡文词面(更快,更幸运/
    # 绕口令/软弱无力词缀逐字同型;幸运之子/人海战术系忆灵词面同域近似
    # 型),非注册名域对象。
    '效率员工奖': EffectSpec(
        id='150601', name='效率员工奖',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '150601')),
        duties=DutyFlags(),
        notes='战力类零响应登记(UNIT_BUFF 族第 8 条);对象选择(进入战斗时'
              '速度最高三名角色及其忆灵)与数值(10% 速度增幅)游戏侧自算,'
              'bot 仅登记;无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 基层贡献:官方「你的场上每有一个1费角色，我方小队获得3%速度增幅和2%伤害减免。
    # 3星1费改为提供3倍。」(cw_invest_data PlazaAugment 150701;出处持久锚不挂
    # 行号——该文件系 gen_plaza_invest.py 再生件,行号随重跑漂移)。战力类零响应
    # 登记(invest_effects.md 战力类总览行「速度」明列:不进经济模型;
    # EffectKind.UNIT_BUFF「游戏侧自算,bot 仅登记」),同形先例 = 全队的希望/
    # 溜佩佩/溜佩佩+/团队力量·银/应援团/正能量/完美开局/效率员工奖 条目。
    # 逐体计数语义(上阵 1 费角色计数、3星1费按 3 计、并列取法)= 游戏侧定义,
    # bot 零消费(kernel cost 读口群 card_cost/bench_char_cost/effective_cost/
    # sell_refund 系经济域观察读口,非效果建模件,零接线);速度/伤害减免真值
    # 全游戏侧,sim 不建模(全域零命中)。「场上」= 上阵编队(与备战栏分立,
    # drag_cw_char.py _ROWS 三键)。
    '基层贡献': EffectSpec(
        id='150701', name='基层贡献',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '150701')),
        duties=DutyFlags(),
        notes='战力类零响应登记(单位强化:游戏侧自算,bot 仅登记);'
              '计数(上阵 1 费角色数,3星1费按 3 计)与双属性数值(3% 速度/2% 伤害减免)'
              '游戏侧自算,bot 仅登记;无离散触发事件消费,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 榜样的力量·银:官方「战斗中，伤害统计排名第一的队员成为【榜样】，前/后台强度
    # 提高25%。」(cw_invest_data PlazaAugment 150801;出处持久锚不挂行号——该文件系
    # gen_plaza_invest.py 再生件,行号随重跑漂移)。战力类零响应登记
    # (invest_effects.md 战力类总览行「强度」明列:不进经济模型;
    # EffectKind.UNIT_BUFF「游戏侧自算,bot 仅登记」),同形先例 = 全队的希望/
    # 溜佩佩/溜佩佩+/团队力量·银/应援团/正能量/完美开局/效率员工奖/基层贡献 条目。
    # 「伤害统计排名第一→榜样」标记选择语义(伤害统计计量口径/并列排名第一取法/
    # 榜样标记持续期)desc 无载 = 游戏侧定义,bot 零消费,判读申报不实机查;
    # 「榜样」系官方卡文词面非注册名域对象:kernel 命中仅敌侧词缀「榜样激励」
    # comp 适配映射面(cw_comps 榜样激励键),与本卡注册名异键零耦合;
    # sim/strategies 零建模。「前/后台」与代码词表「前排/后排」字面不同字,
    # 对应系判读非直译——单体两排泛用强度增益无位置限定,零行为后果。
    '榜样的力量·银': EffectSpec(
        id='150801', name='榜样的力量·银',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '150801')),
        duties=DutyFlags(),
        notes='战力类零响应登记(单位强化:游戏侧自算,bot 仅登记);'
              '标记选择(伤害统计排名第一,战斗中评估)与数值(25% 前/后台强度)'
              '游戏侧自算,bot 仅登记;无离散触发事件消费,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 当头一棒:官方「每个波次开始时，对生命上限最高的敌方目标造成1000%基础伤害，
    # 并使其陷入【脆弱】：受到的伤害提高30%。」(cw_invest_data PlazaAugment 150901;
    # 出处持久锚不挂行号——该文件系 gen_plaza_invest.py 再生件,行号随重跑漂移)。
    # 战斗数值零响应登记(invest_effects.md 战力类总览行「强度」申报归类:不进经济
    # 模型;EffectKind.UNIT_BUFF「游戏侧自算,bot 仅登记」),同形先例 = 全队的希望/
    # 溜佩佩/溜佩佩+/团队力量·银/应援团/正能量/完美开局/效率员工奖/基层贡献/
    # 榜样的力量·银 条目。族内首条敌方侧效果卡:对敌伤害+易伤,非我方单位增益,
    # 载体词面张力经 notes 显式申报。波次触发/目标选取(生命上限最高)与数值全程
    # 游戏侧自算:波次与脆弱词面 kernel/sim 全域零命中,cw_sim_enemy 系难度记录
    # 非战斗单位,敌方目标域不存在读口,bot 零建模零观察。
    '当头一棒': EffectSpec(
        id='150901', name='当头一棒',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '150901')),
        duties=DutyFlags(),
        notes='战力类零响应登记(战斗被动卡:对敌伤害+易伤,非我方单位增益,'
              '载体词面张力显式申报);波次触发/目标选取与数值(1000% 伤害/'
              '30% 易伤)游戏侧自算,bot 仅登记;无离散触发事件消费,'
              'trigger 占位形(对齐 _portal_placeholder_spec 先例)'),
    # 幸运喷雾:官方「我方小队的幸运一击伤害提高25%。」(cw_invest_data.py
    # PlazaAugment 151201;出处持久锚不挂行号——该文件系 gen_plaza_invest.py
    # 再生件,行号随重跑漂移)。战力类零响应登记(invest_effects.md 战力类
    # 总览行「幸运」明列:不进经济模型;EffectKind.UNIT_BUFF「游戏侧自算,
    # bot 仅登记零响应」),同形先例 = 全队的希望/溜佩佩/溜佩佩+/团队力量·银/
    # 应援团/正能量/完美开局/效率员工奖/基层贡献/榜样的力量·银/当头一棒
    # 条目。「幸运一击伤害」= 战斗内独立乘区伤害增幅(幸运一击与暴击独立
    # 计算,机制正本 = combat.md 幸运一击乘区节),非泛用强度、非双端盲区
    # 形态:机制有正本承载,后继族卡禁转引「盲区」口径;「幸运一击」系战斗
    # 机制名非召唤单位注册名(kernel 命中仅敌侧词缀克制映射/机制属性映射/
    # 敌侧依赖面,与本卡注册名异键零耦合),敌侧词缀域零触碰。
    '幸运喷雾': EffectSpec(
        id='151201', name='幸运喷雾',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '151201')),
        duties=DutyFlags(),
        notes='战力类零响应登记(同「全队的希望」泛用属性 buff 登记形态);'
              '全队幸运一击伤害 +25%(战斗内独立乘区,机制正本 combat.md '
              '幸运一击乘区节,非盲区形态)游戏侧自算,bot 仅登记;'
              '无离散触发事件消费,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 延迟收益:官方「在战斗开始100行动值后，我方小队伤害增幅提高40%。」
    # (cw_invest_data PlazaAugment 200701,再生件不挂行号——版本更新重跑
    # gen_plaza_invest.py 行号必漂)。战力类零响应登记(EffectKind.UNIT_BUFF
    # 「游戏侧自算,bot 仅登记零响应」),登记形态 = UNIT_BUFF 族零响应形。
    # 触发条件(战斗开始后行动值累计达 100,战斗中评估;行动值读数定义正本
    # 无机制条目,判读申报制)由游戏在战斗中评估,bot 零消费、读数不接线;
    # 无板面/备战席写入面,归 UNIT_BUFF 零响应形(非容量/槽位约束载体);
    # 数值(伤害增幅 40%)由游戏自算。
    '延迟收益': EffectSpec(
        id='200701', name='延迟收益',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '200701')),
        duties=DutyFlags(),
        notes='战力类零响应登记(UNIT_BUFF 族展开卡);'
              '触发(战斗开始后行动值达 100,战斗中评估)与数值(伤害增幅 40%)游戏侧自算,'
              'bot 仅登记;无离散触发事件消费,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 星级压制:官方「我方小队获得10%速度增幅，攻击星级低于自身的敌人后，
    # 额外造成1次等同于原伤害20%的真实伤害。」(cw_invest_data PlazaAugment
    # 201001,再生件不挂行号——版本更新重跑 gen_plaza_invest.py 行号必漂)。
    # 战力类零响应登记(EffectKind.UNIT_BUFF「游戏侧自算,bot 仅登记零响应」),
    # 复合卡单条目 = 速度光环 + 攻击条件追伤被动双 clause 由 effect_text
    # 全文承载。clause 2 触发(逐攻击命中后比较攻击者与目标敌人星级)与数值
    # (20% 原伤害的真实伤害)由游戏在战斗中评估:敌方星级无 repo 读口
    # (cw_sim_enemy 系难度记录非战斗单位,敌人信息浮层屏档在册读数 = 等级),
    # sim 战斗 U01 无逐攻击事件流;bot 零消费、读数不接线。无板面/备战席
    # 写入面;无离散触发事件消费,trigger 占位形(对齐 _portal_placeholder_spec
    # 先例)。
    '星级压制': EffectSpec(
        id='201001', name='星级压制',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '201001')),
        duties=DutyFlags(),
        notes='战力类零响应登记(复合卡:速度光环+攻击条件追伤);'
              '触发(攻击星级低于自身的敌人后,战斗中逐攻击评估)与数值游戏侧自算,'
              'bot 仅登记;星级读法判读申报制留痕(读法并列不拍死);'
              '无离散触发事件,trigger 占位形(对齐 _portal_placeholder_spec 先例)'),
    # 星变:官方「战斗开始时，使一个随机1费角色变为3星。」(cw_invest_data
    # PlazaAugment 201601,再生件不挂行号——版本更新重跑 gen_plaza_invest.py
    # 行号必漂)。战斗变形零响应登记(星级结构变形,非数值增益——载体取最
    # 邻近零响应桶 UNIT_BUFF「游戏侧自算,bot 仅登记」,词面张力显式申报)。
    # 变形持续性 desc 未明文(同语体「永久」与「在这场战斗中」两方向标记词
    # 均缺席,同构姊妹读博深造同缺席),用户裁定(2026-11-01)拍定临时:变形
    # 仅当次战斗内生效,战斗结束复原,板面零净变化——卖价/合成池账/星级读点
    # 不受影响;变形世界写端未建模(板面临时态零读写口),临时性仅申报。
    # 触发拍(战斗开始时)/对象选取(随机1费角色,判读申报默认上阵参战)/
    # 战斗数值全程游戏侧自算:战斗开始机制轴 kernel/sim 全域零命中
    # (TriggerKind 无对应成员,sim 战斗为瞬时结算随机面)。随机目标选卡默认
    # 不选:变形随机改写羁绊构成破坏策略预判,按「随机发放不可具名,不入具名
    # 打分,恒 off」在册先例口径,本卡选卡估值零承载恒 off(不进
    # STRATEGY_ECONOMY/STRATEGY_GRANTS/立场表)。
    '星变': EffectSpec(
        id='201601', name='星变',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '201601')),
        duties=DutyFlags(),
        notes='战力类零响应登记(星级结构变形非数值增益,载体词面张力显式'
              '申报);变形持续性用户裁定 2026-11-01 拍定临时(仅当次战斗内'
              '生效,战斗结束复原,板面零净变化,卖价/池账/星级读点不受影响;'
              '变形世界写端未建模,临时性仅申报);触发拍(战斗开始时)/对象'
              '选取(随机1费角色,判读申报默认上阵参战)与数值游戏侧自算,'
              'bot 仅登记;随机目标效果不入具名打分,选卡估值恒 off(策略'
              '默认不选);无离散触发事件消费,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 超发货币:官方「失去你现在所有的金币，并在5个节点后，获得该金币数+70
    # 的总金币。」(cw_invest_data.py:139,id 202501)。金面播值负债卡首例,
    # 两腿分治:负债分支 = 拿卡拍持有金 G→0(X=G 快照);回流分支 = 拿卡后
    # 第 6 次节点入口一次性回流 G+70,条目同拍移除,不重发不补发。
    # duration_nodes=6 = 触发入口序的载体表达——发放入口序 = 注册行
    # gold_at_node_offset(5)+1,换算依据 = strategy-env-impacts.md 超发货币
    # 条目用户裁定(2026-09-10)「5个节点后=第6个节点才获取」。负债额 X =
    # 实例 counters[CounterKey.LOST] 伴生数值空间(fields.md §5.3 处方载体,
    # effect-domain §4 伴生数值空间先例),播值端 = 获得链登记腿
    #(kernel/cw_gain_chain.gain_invest_strategy,登记帧金读数)。live 零写金
    #(游戏自扣自发,金整字段观察覆盖兜底——effect-domain「到期与尾款」
    # 防双计裁定;impacts 条目「逻辑写」字样的实现位 = sim 世界写端);
    # sim 两腿 = 世界真值(清零腿挂选卡落地拍、回流腿挂节点窗推进锚
    # pre-read 两拍,evidence 前缀 strategy:hyperemit_drain:<卡名> /
    # strategy:hyperemit:<卡名>:p{plane}r{r})。duties 全空:余期推进 =
    # N_NODES 结构自动,回流发放不住 duties(消费面 = sim 世界腿直读
    # 条目,登记与消费分离现役形态)。不入 STRATEGY_DELAYED_GRANTS 族表:
    # 发放物为金不入物品词表族表(族表构建校验发放物闸在码亦拒),回流
    # 载体 = 本条目单载体制(sim 腿消费条目,零第二份状态)。
    '超发货币': EffectSpec(
        id='202501', name='超发货币', trigger=TriggerKind.CONDITIONAL,
        duration=DurationKind.N_NODES, category=EffectKind.ECONOMY,
        payload=STRATEGY_ECONOMY['超发货币'], duties=DutyFlags(),
        duration_nodes=6,
        notes='负债拍播值 counters[LOST] = 登记帧金读数(获得链登记腿);'
              '回流 = 拿卡后第 6 次节点入口(入口序 = offset+1,impacts '
              '用户裁定 2026-09-10);live 零写观察覆盖,sim 世界真值两挂点;'
              '发放物为金不入 STRATEGY_DELAYED_GRANTS 物品词表族表'),
    # 人海战术:官方「我方小队的前/后台强度提高10%。战斗中，我方小队在场的
    # 角色与忆灵数量之和大于8时，我方小队的前/后台强度提高20%。」
    # (cw_invest_data.py, id 250101)。
    # 战力类零响应登记(UNIT_BUFF 族):两段强度增幅游戏侧自算,bot 零响应;
    # 条件段「在场数>8」条件面零建模(判读申报制留痕+pending=False,完美
    # 开局/星级压制同形);「召唤物」词面张力有在码同型先例(效率员工奖含
    # 「及其忆灵」落码不绑,本卡不绑,绑定面零登记);effect_text 经数据面
    # 表达式单一源,版本更新改文自动跟随。
    '人海战术': EffectSpec(
        id='250101', name='人海战术',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '250101')),
        duties=DutyFlags(),
        notes='战力类零响应登记(UNIT_BUFF 族);'
              '两段增幅与条件段(在场数>8)游戏侧自算,bot 仅登记;'
              '无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 打通上下游·金:官方「我方小队速度增幅提高10%。每个节点开始时，速度
    # 增幅额外提高1%。」(cw_invest_data.py, id 250201)。
    # 战力类零响应登记(UNIT_BUFF 族):两段速度增幅与节点增长句游戏侧自算,
    # bot 零响应(增长句 bot 零响应域判读申报制);trigger 占位形
    # (PLANE_START 与 NODE_ENTER 稿明文零行为差);effect_text 经数据面
    # 表达式单一源,版本更新改文自动跟随。
    '打通上下游·金': EffectSpec(
        id='250201', name='打通上下游·金',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '250201')),
        duties=DutyFlags(),
        notes='战力类零响应登记(UNIT_BUFF 族);'
              '两段增幅与节点增长句游戏侧自算,bot 仅登记;'
              '无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 独狼:官方「若角色不具有已激活的非独立羁绊，使其获得120%前/后台强度
    # 和36%伤害减免。」(cw_invest_data.py, id 250401)。
    # 战力类零响应登记(UNIT_BUFF 族):条件段「非独立羁绊」与两段增幅游戏
    # 侧自算,bot 零响应(条件时点读法游戏侧内部口径判读申报制);effect_text
    # 经数据面表达式单一源,版本更新改文自动跟随。
    '独狼': EffectSpec(
        id='250401', name='独狼',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '250401')),
        duties=DutyFlags(),
        notes='战力类零响应登记(UNIT_BUFF 族);'
              '条件段与两段增幅游戏侧自算,bot 仅登记;'
              '无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 中产阶级:官方「我方小队里每有1位2星角色，使小队获得5%伤害减免和
    # 15%前/后台强度。」(cw_invest_data.py, id 250501)。
    # 战力类零响应登记(UNIT_BUFF 族):计数辖域与两段增幅游戏侧自算,bot
    # 零响应(计数辖域两读法 bot 行为恒同判读申报制留痕,T-253 同判形);
    # effect_text 经数据面表达式单一源,版本更新改文自动跟随。
    '中产阶级': EffectSpec(
        id='250501', name='中产阶级',
        trigger=TriggerKind.PLANE_START,
        duration=DurationKind.WHILE_HELD,
        category=EffectKind.UNIT_BUFF,
        payload=UnitBuffRef(effect_text=next(
            a.effect for a in PLAZA_AUGMENTS if a.id == '250501')),
        duties=DutyFlags(),
        notes='战力类零响应登记(UNIT_BUFF 族);'
              '计数辖域与两段增幅游戏侧自算,bot 仅登记;'
              '无离散触发事件,trigger 占位形'
              '(对齐 _portal_placeholder_spec 先例)'),
    # 现金为王:官方「出售场上和备战席的所有角色，之后每场进入战斗时，为我方
    # 前台提供护盾，护盾量等同于该次出售角色所获得总金币数*1000。」
    # (cw_invest_data.py:200)。卖全场族素出售第三张注册卡(大裁员/降本增效
    # 姊妹,人力重组走 _DEAL 值非素):出售面 = 板面重写桥素出售语义清场 +
    # 基础公式退款(卡文无「双倍」句,无卖价修饰);护盾面 = 「每场进入战斗
    # 时前台获盾」持久被动游戏侧自算(bot 零响应,U01 sim 战斗零消费),
    # 记忆量 = 桥退款权威写入同闸记账实例 counters[CounterKey.SHIELD_BANK]
    # (= 退款×1000 卡文明写,常量承载;写端唯一 = 板面重写桥,空场/部分读
    # 零记账),不设独立字段(正本 fields.md 卖全场族行/effect-domain §4
    # 伴生数值空间)。
    '现金为王': EffectSpec(
        id='250301', name='现金为王', trigger=TriggerKind.INSTANT,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(board_rewrite=BOARD_REWRITE_SELL_ALL),
        duties=DutyFlags(predict=True),
        notes='出售面=板面重写桥素出售(人力重组同构);护盾记忆量=桥退款'
              '×1000 记实例 counters[SHIELD_BANK](正本 fields.md 卖全场族'
              '行/effect-domain §4);护盾授予=每场进入战斗游戏侧自算 '
              'bot 零响应'),
}


def _validate_strategy_effects() -> None:
    """STRATEGY_EFFECTS 构建校验(import 即炸,只留漂移哨;治理口径 =
    用户裁定 2026-10-28,见 _validate_env_gifts docstring):

    ① 孤儿键:name 必须在 base 注册表(版本更新改名/移除后静默失联);
    ② id 双匹配:spec.id 必须等于 plaza id(改名且 id 仍在的漂移也炸)。
    payload↔category 一致性与 pending-notes 必填属防登记笔误类,已移除。
    """
    for spec in STRATEGY_EFFECTS.values():
        base = INVESTMENT_STRATEGIES.get(spec.name)
        if base is None:
            raise ValueError(f"STRATEGY_EFFECTS 孤儿键(base 无此卡):{spec.name!r}")
        if base.source != f"plaza:{spec.id}":
            raise ValueError(
                f"STRATEGY_EFFECTS id 漂移:{spec.name!r} spec.id={spec.id} base={base.source}")


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

#: 追加获得分支采样假设披露键(键面 = desc 未写明处的申报,消费 = sim 随局
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
            gold_at_final_supply=eff.gold_at_final_supply + e.gold_at_final_supply,
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
    prep_actions.record_hp_pay_event 的 mode 判定;经验批支付门
    (kernel/cw_economy.xp_batch_payment_gate_for,R-1 币种通式)与遥测
    写点经本助手同源消费)。多卡命中取 active_strategies 序首个
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
    消费位 = 升级上报回调 + sim 世界分支,禁第二处内联)。
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
    """投资环境的阵容指向集(faction 分支 + 亲和分支;§2.1)。

    - faction 分支:``INVESTMENT_ENVS[env].faction`` 非空入集(概念股/邀请/
      契约全量登记;专家类例外 = 特邀专家:加拉赫→击破);
    - 亲和分支:``ENV_COMP_AFFINITY`` 该环境值键 = 线名,取各线 Comp.factions
      **全集**入集——副阵营随线带入(命运圣杯邀请亲和含双王圣杯 → 指向集
      = {命运圣杯, 能量}:能量组件卡可服务双王线的能量副羁绊,判兼容是
      语义本意;特邀专家:桑博 faction 空但亲和专家桑博DOT,单 faction 分支
      会误判通用)。线名缺 Comp(注册表漂移)→ 跳过不炸,指向集收窄
      宁放行(与角色入账分支未注册跳过同 fail 方向)。

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
    """投资策略的阵容指向集(STRATEGY_BINDINGS 阵营分支 + 角色入账分支两源;§2.1)。

    - 阵营分支:绑定阵营直接入集;
    - 角色入账分支 ch 两源:① ``CHARACTERS[ch].factions`` **全集**入集(多阵营
      角色全展开,用户裁定「从角色去关联对应的阵容」,如丹恒·饮月 =
      仙舟/列车同行);② 成员分支:ch ∈ Comp.core_chars ∪ shared_chars 的
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
# 自动猜装(错装防线归评审与经济域测试;六条防错装对账校验已随
# 2026-10-28 治理移除);
# 轮岗/人才下沉无通道可装 → 策略层 env_economy.ENV_ECONOMY_PENDING_MODELING
# 显式登记(区别于漏登记):轮岗 = 待建模候迁出;人才下沉 = 已定案按 0
# (2026-10-16 用户裁定,永驻登记;商店 2★ 直出分支见下文
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
    """ENV_ECONOMY 构建校验(import 即炸;治理口径 = 用户裁定 2026-10-28,
    见 _validate_env_gifts docstring):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联)。
    六条防一次性错装对账/劳务派遣拒绝/挂载实例一致性属防登记笔误与构建
    段自身防呆类,已移除(错装后果 = 估值通道错位,评审与经济域测试把关)。
    """
    orphans = [n for n in ENV_ECONOMY if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(f"ENV_ECONOMY 孤儿键(base 无此环境?):{sorted(orphans)}")


for _n, _eff in ENV_ECONOMY.items():
    INVESTMENT_ENVS[_n] = replace(INVESTMENT_ENVS[_n], economy=_eff)
_validate_env_economy()


# ===== 环境声明矿注册表(details/ore-reward-channel.md §2)=====
# **世界发放域**(矿进入世界时的声明内容),与 ENV_ECONOMY(估值域)分域不互斥
# ——增发货币两表同时已登记是常态;两侧金额同出卡面(id 103),一致性归
# 评审与 ore 域测试把关(双源同值校验已随 2026-10-28 治理移除)。
# 消费面 = kernel/cw_ore_channel.py 声明入队电平检查(键查)与挂接入口
# 生成(值出队)。
ENV_ORE_GRANTS: dict[str, tuple[int, ...]] = {
    # 每位面开局 6/8/12 金晶矿(id 103 原文直读,cw_invest_data PlazaPortal('103'))
    '增发货币': (6, 8, 12),
}


def _validate_env_ore_grants() -> None:
    """ENV_ORE_GRANTS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联)。
    值形与双源同值(ENV_ECONOMY.gold_per_plane_start 对拍)属防登记笔误/
    单侧改数类,已移除——两侧金额对账归评审与 ore 域测试把关。
    """
    orphans = [n for n in ENV_ORE_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(f"ENV_ORE_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")


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
# 映射/具名分档/键完备)、sim/test_sim_backend.py(sim 世界分支到点发放)。
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
    # (停云终结技增益/加拉赫击破档分支世界发放已接(ENV_BOND_TIER_GRANTS),
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
    # 装备入账分支在前 = 卡文序(on_env_gained 装备支位于 items_immediate 支之前,
    # 遥测序与卡文对齐)。红钻 ∈ EQUIPMENTS(合成材料,非占席道具);箱 =
    # 道具通道现役(武装箱系不在装备注册表,装备名漂移校验天然互斥)。
    # 装备入账分支发放写通道 = 随机态(见 GiftGrant.equips_immediate docstring
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
    # ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS 携带;属性加成分支(「进入新节点
    # 永久随机属性加成」)该分支整体不建模,披露键 env_char_buff_unmodeled
    '战力提升': GiftGrant(chars_random_immediate=(
        RandomCharSpec(cost=1, star=2, type_tag='输出'),)),
    # 类型过滤随机支姊妹卡·无类型词变体(id 137 效果原文「获得1个随机2星
    # 2费角色」直读,PlazaPortal('137'));星级 2 = 卡面明写非先验;无类型词 →
    # type_tag 空,池 = 2 费全档(注册表现值派生,爻光费用勘误 2→1 自动
    # 不入池);采样/先验披露随家族常量 ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS
    # 携带;属性加成分支(「进入新节点永久随机属性加成」)该分支整体不建模,披露键
    # env_char_buff_unmodeled 引用 T-36 批已立常量(卡区分靠效果账本上下文)
    '战力飙升': GiftGrant(chars_random_immediate=(
        RandomCharSpec(cost=2, star=2),)),
    # 随机装备支首例(id 118 效果原文「获得随机星徽」直读,
    # PlazaPortal('118');数量词缺省 = 1 件先验,披露键
    # ENV_STAR_GRANT_ASSUMPTION_KEYS 承载)。绑定分支:发放名以 done 条件键
    # 'star_grant#<名>' 落 env_grants_done(分支2「每次进入首领节点获得对应
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
    # CHARACTER_ROSTER(cw_chars 召唤族,0 费后台))。两条分支零登记定性(披露键
    # 申报,防误判漏报):
    # - 佩戴星徽分支:同三星佩佩口径(穿戴非入栏,容器行 equips 消费端的穿戴
    #   输入对本卡结构性恒空 = 增量派生刻意基座,live 面板观察承载,随机池
    #   desc 无载按放弃纪律)。
    # - 掉落分支(「有时候…落在你的物品栏」):概率/时点/件数/池四维 desc 全
    #   无载(放弃纪律)+ 无登记字段可容(扩字段 = 提前抽象且无合法填充值);
    #   live 掉落真值归 equips 观察,sim 世界缺掉落物 = 申报缺口(特权阶级
    #   不对称申报同型);随机星徽整族建模现状:劳务派遣合同已按「获得」
    #   直读登记随机装备支(见上),买彩票(选卡落地)已按「获得」直读登记
    #   策略侧随机装备支(cw_gain_effects._STRATEGY_RANDOM_EQUIP_GRANTS
    #   星徽行,池同源 equips_by_category),本卡佩戴/掉落两条分支仍按上文
    #   口径归观察。
    # 星级 = 用户裁定佩佩无星级(2026-10-15):链必填实参落 1 为占位非先验。
    '粗星佩佩': GiftGrant(chars_immediate=('佩佩',)),
    # 专家研讨会(id 139,效果原文「获得1个【专家邀请函】和1个【简易武装箱】。」
    # 直读,PlazaPortal('139');卡文无「开局时」字样,环境效果唯一可实现
    # 时点 = 环境注册(选卡当场),用户裁定 2026-10-24)。卡文序 = 邀请函
    # 先箱后。专家邀请函 = kind='bookcard'(开卡链)、简易武装箱 =
    # kind='supply_box'(开箱链);落席类别判定单一源 = BENCH_ITEM_KINDS
    # (与本条目同批登记,缺一 = 落席直查 KeyError 响亮可见,无书写顺序
    # 语义)。不设 advisor=True:advisor 语义 = 顾问
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
    # = 链自然结果)。升星属性分支(11%/33% 速度、22%/66% 伤害)不建模(用户
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
    # id 1008 效果原文直读:「仙舟」= desc【仙舟】直读(阵营羁绊名,与 ENV_FACTION
    # 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS);
    # 简易装备 1 件 = 单数叙述默认假设(ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;
    # economy.md 四卡线索名单含仙舟→折叠小刀,先验随 fixed_hypothesis 键在册);
    # 简易池 = category '简易' 现值 8 件;采样域 = 牌库时点过滤(用户裁定
    # 2026-10-28:未解锁专家不入候选,域 9 名过滤后 7 名,青雀/停云为专家)。
    '仙舟概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='仙舟', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1009 效果原文直读:「狼狩」= desc【狼狩】直读(阵营羁绊名,与 ENV_FACTION
    # 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS);
    # 简易装备 1 件 = 单数叙述默认假设(ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;
    # economy.md 四卡线索名单不含狼狩,身份零先验,fixed_hypothesis 家族键
    # 在册);简易池 = category '简易' 现值 8 件;采样域 = 牌库时点过滤
    # (族级裁定 2026-10-28:未解锁专家不入候选,域 7 名过滤后 6 名,貊泽
    # is_expert=True)。
    '狼狩概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='狼狩', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1010 效果原文直读:「昼之半神」= desc【昼之半神】直读(阵营羁绊名,与 ENV_FACTION
    # 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS);
    # 简易装备 1 件 = 单数叙述默认假设(ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;
    # economy.md「昼神送轮滑鞋」先验已随 fixed_hypothesis 键在册);简易池 =
    # category '简易' 现值 8 件;本域无专家(6 名 is_expert 全空),牌库时点
    # 过滤对本域恒等;独立单位昔涟照发(族级口径 economy.md:94)。
    '昼之半神概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='昼之半神', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1011 效果原文直读:「夜之半神」= desc【夜之半神】直读(阵营羁绊名,与
    # ENV_FACTION 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_ASSUMPTION_
    # KEYS);简易装备 1 件 = 单数叙述默认假设(ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;
    # economy.md 四卡线索名单不含夜之半神 = 装备身份零先验,均匀 v0 + 按卡固定
    # 假说待校准);简易池 = category '简易' 现值 8 件;本域无专家(7 名 is_expert
    # 全空),牌库时点过滤对本域恒等;独立单位昔涟照发(族级口径 economy.md:94)。
    '夜之半神概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='夜之半神', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1012 效果原文直读:「击破」= desc【击破】直读(流派名,与 ENV_FACTION
    # 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS);
    # 简易装备 1 件 = 单数叙述默认假设(ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;
    # economy.md 四卡线索名单不含击破,身份零先验,fixed_hypothesis 家族键
    # 在册);简易池 = category '简易' 现值 8 件;采样域 = 牌库时点过滤
    # (族级裁定 2026-10-28:未解锁专家不入候选,域 9 名过滤后 7 名,加拉赫/
    # 姬子 is_expert=True;独立条目「姬子·启行」flows 空非本域,勿混淆)。
    '击破概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='击破', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1013 效果原文直读:「群攻」= desc【群攻】直读(流派羁绊名,与
    # ENV_FACTION 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_ASSUMPTION_
    # KEYS);简易装备 1 件 = 单数叙述默认假设(ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;
    # economy.md 四卡线索名单不含群攻 = 装备身份零先验,均匀 v0 + 按卡固定
    # 假说待校准);简易池 = category '简易' 现值 8 件;本域无专家(7 名 is_expert
    # 全空),牌库时点过滤对本域恒等;缇宝 flows「群攻、量子同频」双羁绊
    # (量子同频无概念股卡,零联动);翡翠为公司契约具名发放对象(:1502,
    # 具名 vs 随机字段不相交,正交零冲突)。
    '群攻概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='群攻', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1014 效果原文直读:「减益」= desc【减益】直读(流派羁绊名,与
    # ENV_FACTION 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_ASSUMPTION_
    # KEYS);简易装备 1 件 = 单数叙述默认假设(ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;
    # economy.md 四卡线索名单不含减益 = 装备身份零先验,均匀 v0 + 按卡固定
    # 假说待校准);简易池 = category '简易' 现值 8 件;采样域 = 牌库时点过滤
    # (族级裁定 2026-10-28:未解锁专家不入候选,域 7 名过滤后 6 名,佩拉
    # is_expert=True;千冶·刃 ≠ 专家「刃」);椒丘为「持续伤害契约」具名发放
    # 对象(具名 vs 随机字段不相交,正交零冲突);千冶·刃 flows
    # 「燃血、减益」双羁绊(燃血域已落地,跨域共享非独占;星核猎手
    # 无概念股卡且星核猎手契约具名对象仅卡芙卡,零联动)。
    '减益概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='减益', star=1),),
                            equips_random_immediate=('简易',)),
    # id 1016 效果原文直读:「战技点」= desc【战技点】直读(流派羁绊名,与
    # ENV_FACTION 派生名同源);星级 1 = 先验(ENV_RANDOM_CHAR_GRANT_ASSUMPTION_
    # KEYS);简易装备 1 件 = 单数叙述默认假设(ENV_CONCEPT_STOCK_ASSUMPTION_KEYS;
    # economy.md 四卡线索名单不含战技点 = 装备身份零先验,均匀 v0 + 按卡固定
    # 假说待校准);简易池 = category '简易' 现值 8 件;采样域 = 牌库时点过滤
    # (族级裁定 2026-10-28:未解锁专家不入候选,域 7 名过滤后 6 名,青雀
    # is_expert=True);独立单位 Archer 照发(族级口径 economy.md:94 点名
    # 战技点(Archer),independent='魔术师');花火(2费,flows 战技点、量子同频)
    # ≠ 火花(4费,flows 战技点、欢愉)两名形近成员,量子同频/欢愉均无概念股卡
    # 零联动;具名交集 5 名正交:丹恒·饮月/花火 = 战技点契约具名、火花 =
    # 战技点契约条件∪欢愉契约条件、远坂凛/Archer = 命运圣杯契约具名/条件
    # (具名 vs 随机字段不相交);域独占 3 名 = 远坂凛/花火/Archer。本卡 =
    # 概念股族第十五实例(族收官:登记至此 15/15)。
    '战技点概念股': GiftGrant(chars_random_immediate=(RandomCharSpec(faction='战技点', star=1),),
                            equips_random_immediate=('简易',)),
    # —— 邀请族首例(模式卡 T-63;后继邀请卡 T-64..T-82 逐卡套用本行形状,
    # 纯数据行零机制新增)——
    # id 1101 效果原文「获得一个【列车同行星徽】。」直读,PlazaPortal('1101');
    # 「一个」= 1 件,数量 = 元素重复次数与 items 通道同约定;无时点修饰词
    # = 环境注册时点(专家研讨会裁定 2026-10-24 同判)。列车同行星徽 =
    # EQUIPMENTS category='星徽' 件(具名装备通道,非占席道具;装备身份与
    # items 词表分域,BENCH_ITEM_NAMES 派生只扫 items 两通道)。通道语义 =
    # 发放一件可穿戴的羁绊授予装备入栏,穿戴时机与目标 = 玩家动作面
    # (观察域),发放面不涉。
    '列车同行邀请': GiftGrant(equips_immediate=('列车同行星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见模式卡设计稿 T-63 §2.4)——
    # id 1102 效果原文「获得一个【银河学者星徽】。」直读,PlazaPortal('1102');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。银河学者星徽
    # recipes 非空可合成(红钻+光能电池)——合成获得路径与发放腿正交,零触碰。
    '银河学者邀请': GiftGrant(equips_immediate=('银河学者星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1103 效果原文「获得一个【贝洛伯格星徽】。」直读,PlazaPortal('1103');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。贝洛伯格星徽
    # recipes 非空可合成(红钻+量产型装甲)——合成获得路径与发放腿正交,零触碰。
    '贝洛伯格邀请': GiftGrant(equips_immediate=('贝洛伯格星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1104 效果原文「获得一个【星间旅人星徽】。」直读,PlazaPortal('1104');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。星间旅人星徽
    # recipes 非空可合成(红钻+以太钻头)——合成获得路径与发放腿正交,零触碰。
    '星间旅人邀请': GiftGrant(equips_immediate=('星间旅人星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1105 效果原文「获得一个【仙舟星徽】。」直读,PlazaPortal('1105');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。仙舟星徽
    # recipes 非空可合成(红钻+折叠小刀)——合成获得路径与发放腿正交,零触碰。
    '仙舟邀请': GiftGrant(equips_immediate=('仙舟星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1106 效果原文「获得一个【狼狩星徽】。」直读,PlazaPortal('1106');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。狼狩星徽
    # recipes 非空可合成(红钻+生命之花)——合成获得路径与发放腿正交,零触碰。
    '狼狩邀请': GiftGrant(equips_immediate=('狼狩星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1107 效果原文「获得一个【盛会之星星徽】。」直读,PlazaPortal('1107');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。盛会之星星徽
    # recipes 非空可合成(红钻+幸运星)——合成获得路径与发放腿正交,零触碰。
    '盛会之星邀请': GiftGrant(equips_immediate=('盛会之星星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1108 效果原文「获得一个【昼之半神星徽】。」直读,PlazaPortal('1108');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。昼之半神星徽
    # recipes 非空可合成(红钻+轮滑鞋)——合成获得路径与发放腿正交,零触碰。
    '昼之半神邀请': GiftGrant(equips_immediate=('昼之半神星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1109 效果原文「获得一个【夜之半神星徽】。」直读,PlazaPortal('1109');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。夜之半神星徽
    # recipes 非空可合成(红钻+和平手枪)——合成获得路径与发放腿正交,零触碰。
    '夜之半神邀请': GiftGrant(equips_immediate=('夜之半神星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1110 效果原文「获得一个【追击星徽】。」直读,PlazaPortal('1110');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。追击星徽
    # recipes 非空可合成(蓝钻+轮滑鞋)——合成获得路径与发放腿正交,零触碰。
    '追击邀请': GiftGrant(equips_immediate=('追击星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1111 效果原文「获得一个【击破星徽】。」直读,PlazaPortal('1111');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。击破星徽
    # recipes 非空可合成(蓝钻+以太钻头)——合成获得路径与发放腿正交,零触碰。
    '击破邀请': GiftGrant(equips_immediate=('击破星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1112 效果原文「获得一个【群攻星徽】。」直读,PlazaPortal('1112');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。群攻星徽
    # recipes 非空可合成(蓝钻+幸运星)——合成获得路径与发放腿正交,零触碰。
    '群攻邀请': GiftGrant(equips_immediate=('群攻星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1113 效果原文「获得一个【能量星徽】。」直读,PlazaPortal('1113');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。能量星徽
    # recipes 非空可合成(蓝钻+光能电池)——合成获得路径与发放腿正交,零触碰。
    '能量邀请': GiftGrant(equips_immediate=('能量星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1114 效果原文「获得一个【燃血星徽】。」直读,PlazaPortal('1114');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。燃血星徽
    # recipes 非空可合成(蓝钻+生命之花)——合成获得路径与发放腿正交,零触碰。
    '燃血邀请': GiftGrant(equips_immediate=('燃血星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1115 效果原文「获得一个【减益星徽】。」直读,PlazaPortal('1115');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。减益星徽
    # recipes 非空可合成(蓝钻+和平手枪)——合成获得路径与发放腿正交,零触碰。
    '减益邀请': GiftGrant(equips_immediate=('减益星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1116 效果原文「获得一个【持续伤害星徽】。」直读,PlazaPortal('1116');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。持续伤害星徽
    # recipes 非空可合成(蓝钻+量产型装甲)——合成获得路径与发放腿正交,零触碰。
    '持续伤害邀请': GiftGrant(equips_immediate=('持续伤害星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1117 效果原文「获得一个【量子同频星徽】。」直读,PlazaPortal('1117');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。量子同频星徽
    # recipes 空,合成路径不存在(获取 = 本卡发放+策略卡 220901+套组 320901);零合成面触碰。
    '量子同频邀请': GiftGrant(equips_immediate=('量子同频星徽',)),
    # id 1118 效果原文「获得一个【战技点星徽】。」直读,PlazaPortal('1118');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。战技点星徽
    # recipes 非空可合成(蓝钻+折叠小刀,合成获得路径与发放腿正交);desc 机制
    # 尾巴(战技/普攻无视 20% 防御)为装备自身穿戴面语义,发放面无感。
    '战技点邀请': GiftGrant(equips_immediate=('战技点星徽',)),
    # —— 邀请族展开卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1119 效果原文「获得一个【欢愉星徽】。」直读,PlazaPortal('1119');
    # 「一个」= 1 件,无时点修饰词 = 环境注册时点(族模板同判)。欢愉星徽
    # recipes 非空可合成(蓝钻+垃圾袋/红钻+垃圾袋,22 件星徽唯一双配方件)——合成获得路径与发放腿正交,零触碰。
    '欢愉邀请': GiftGrant(equips_immediate=('欢愉星徽',)),
    # —— 邀请族收官卡(逐卡套用上方族模板形状,纯数据行零机制新增;
    # 卡卡特有面就地申报,族展开契约见上方族模板注释)——
    # id 1120 效果原文「获得1个【命运圣杯星徽】。」直读,PlazaPortal('1120');
    # 「1个」= 数字形态 1 件(族内唯一数量词异形,与他卡「一个」同义直读),无时点修饰词 = 环境注册时点(族模板同判)。命运圣杯星徽
    # recipes 空 = 合成路径不存在(获取 = 本卡发放+策略卡 211401+棱彩策略卡 352801);零合成面触碰。
    '命运圣杯邀请': GiftGrant(equips_immediate=('命运圣杯星徽',)),
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
    模块级 ``_DUAL_FORM_MERGE``)。**静态基底池**:构建期非空校验
    (``_validate_env_gifts``/``_validate_env_deploy_lock_grants``)与
    运行期授予采样(经 cw_pool ``grant_char_pool`` 叠加牌库时点过滤——
    未解锁专家剔除,用户裁定 2026-10-28)共同的本函数消费点;直接以本
    函数取池采样 = 静态口径,授予通道已统一改经 grant_char_pool。运行期
    空池 = 注册表漂移(或全专家域未解锁),发放分支再查一道防御。"""
    base = chars_by_faction(spec.faction) if spec.faction else chars_by_cost(spec.cost)
    pool = [c.name for c in base
            if not spec.type_tag or spec.type_tag in c.char_type.split('、')]
    return [n for n in pool if n not in _DUAL_FORM_MERGE]


def equips_by_category(category: str) -> tuple[str, ...]:
    """装备注册表按类别派生池(零硬编码第二源;构建/运行期同源消费)。"""
    return tuple(n for n, e in EQUIPMENTS.items() if e.category == category)


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

#: 环境「desc 有载但刻意零建模」分支的申报键(家族常量,键随家族携带不随
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
#: - env_char_buff_unmodeled: 环境「每节点属性 buff」分支不建模(家族同案,
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

#: 策略卡「聘用书授予」族道具腿的刻意零建模申报键(家族常量,键 = 族卡
#: 名,族卡随各自实现批追加并入,首卡 = 招聘资金;消费面 = 披露清单,防
#: 「获得 N 张聘用书」被误判为漏报):聘用书类凭证道具的获得发放未建模
#: ——存放形态(是否占席)与开启语义(打开所得)无 desc/知识正本/实机
#: 遥测载,禁猜不登记(箱腿通道落席会假身份并误派开箱动作,live 亦无聘
#: 用书识别模板,双端一致的申报缺口非单端失真);金腿(instant_gold)经
#: STRATEGY_ECONOMY 在册计分,不受本键辖。退役条件 = 凭证道具通道族批
#: 落地(占席/裁片/开启证据到位,以 BENCH_ITEM_KINDS 为机制单一源扩表
#: 接入),族键随族批退役。
STRATEGY_HIRING_LETTER_UNMODELED_ASSUMPTION_KEYS: tuple[str, ...] = (
    '招聘资金',
    '招聘资金+',
    '专家招募',
    '专家招募+',
)


# 广聚天下英才(203601)假设申报三键(全员发放族首例;键粒度 = 卡别键
# 独立,随机赠卡 star_prior 家族键不混用——本卡全员确定性发放无采样面,
# star_prior 系随机赠卡族专用):
STRATEGY_ALL_CHARS_ASSUMPTION_KEYS: tuple[str, ...] = (
    'strategy_all_chars_pool_includes_expert',
    'strategy_all_chars_star_prior_1',
    'strategy_all_chars_overflow_truncation',
)

# 策略卡「desc 有载但刻意零建模」行为申报键(策略卡侧家族常量,键随家族
# 携带不随单卡增减,形态沿 ENV_GIFT_UNMODELED_ASSUMPTION_KEYS 先例;消费面
# = 披露清单,防「卡面写了但模型没建」被误判为漏报)。逐键语义:
# - strategy_worn_equip_unmodeled: 策略卡授予单位的**穿戴**件不建模(用户
#   裁定 2026-10-15,环境侧同判)——穿戴非入栏,live 观察管线回报行 equips
#   整表覆盖为空恒冲突,容器行消费端(板面真值/巨星候选/行键)穿戴输入
#   结构性恒空,双端真值割裂,游戏侧自算承载;首例 = 艾丝妲的猛犬!
#   (203801,穿刺死棘之枪);同形消费方:步狸村之谜(203901)/这么大的钻石
#   (231101,佩佩携带宝钻句——用户裁定 2026-11-02 拍读法 B 确认消费,佩佩
#   本体入队另行建模,携钻句零建模语义不变)/狸职手续(204001,穿戴物身份
#   未指名——哪件/是否随机/是否扣
#   库存 desc 全无载,放弃纪律叠加),后继引用本键不重立。
# - strategy_periodic_unit_leave_unmodeled: 策略卡召唤单位的**周期离场**
#   (含离场所留)不建模——四缺口:kernel 单位移除仅卖出/合成摘除/板面
#   清场三径,「无退款消失」无原语可调;「留下装备」因穿戴未建模无指涉物;
#   「每 N 个节点」起点 desc 未指明(拿卡节点起算/全局节点序两读法并存,
#   desc 未写明不实机查在册裁定);单位发放/离场域无重复周期触发形状
#   (延时发放通道 STRATEGY_DELAYED_GRANTS/STRATEGY_DELAYED_OFFERS = 一次
#   性倒计时形状,周期型异形另案在册)。首例 = 狸职手续(204001),后继
#   狸狸族卡引用本键不重立;同卡歧义句(「狸职狸会使不是狸职狸的狸也
#   狸职」= 召唤单位使其他来源的同名单位进入离场轮换)现模型内「非本卡
#   同名单位」成员集为空,辖域空转由本键注记承载不另立键,族卡建模批联动
#   复核。live 流程侧零义务(离场与装备归游戏侧自算,备战/equips 观察
#   自动承接)。
STRATEGY_DESC_UNMODELED_KEYS: tuple[str, ...] = (
    'strategy_worn_equip_unmodeled',
    'strategy_periodic_unit_leave_unmodeled',
)

#: 开局替换型赠卡(首例 = 人才储备 id 144)的语义假设申报键(卡级两键,
#: 形态沿家族常量先例;消费面 = 披露清单,防 desc 空白处的模型口径被误当
#: 已证真值):
#: - env_opening_replace_semantics: 「替换」的模型口径 = 开局 4 张初始角色
#:   被 3 张随机 3 费 1★ 取代(非叠加)。开局补给的晶矿分支(开场矿)在场有载
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

#: 随机星徽授予家族(劳务派遣合同,分支1 星徽 + 分支2 首领节点角色)的
#: 采样/先验假设申报键(六键;键随家族携带不随单卡增减,消费面 = 实测
#: 校准与披露清单):
#: - env_star_grant_uniform: 星徽等概率 v0(分布未实测,晶矿/全员晋升
#:   均匀 v0 先例,校准源 = equips 观察 vs 掷骰名 logic_rand_outcome 行
#:   逐局积累);
#: - env_star_grant_count1: 分支1 数量 1 件先验(desc 无数量词,自然语言
#:   单数省写;先验错 = sim 世界多/少装备,bench 无感、资产对照偏差);
#: - env_star_grant_bind_single: 「对应羁绊」= 分支1 采样单枚固定绑定
#:   (desc 句式回指解读;若实机为已持全部星徽各触发,模型少发);
#: - env_boss_grant_char_uniform: 羁绊成员池等概率 + flows 含入
#:   (chars_by_faction 默认参数,与 FactionInfo.members 同源);
#: - env_boss_grant_char_star1: 分支2 星级 1★ 先验(晶矿 CHAR_DROP_STAR
#:   同句式,先验错走 bench 观察星级覆盖);
#: - env_boss_grant_count1: 分支2 每 boss 节点 1 个先验(desc 无数量词)。
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

#: 概念股族阵营刷新概率分支的「零建模」失真申报键(家族常量;键模板 =
#: ``env_<id>_faction_refresh_odds_unmodeled``,族卡随各自批次追加 id,
#: 本批收 env_1001、env_1002、env_1003、env_1004、env_1005、env_1006、env_1007、env_1008、env_1009、env_1010、env_1011、env_1012、env_1013、env_1014、env_1016(族收官,登记 15/15 齐);消费面 = 披露清单,invest_effects.md §5 在案裁定为
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
    'env_1008_faction_refresh_odds_unmodeled',
    'env_1009_faction_refresh_odds_unmodeled',
    'env_1010_faction_refresh_odds_unmodeled',
    'env_1011_faction_refresh_odds_unmodeled',
    'env_1012_faction_refresh_odds_unmodeled',
    'env_1013_faction_refresh_odds_unmodeled',
    'env_1014_faction_refresh_odds_unmodeled',
    'env_1016_faction_refresh_odds_unmodeled',
)

# (送卡「档→分」映射与 advisor 折减 = 策略层 gift_value
# (GIFT_TIER_SCORE/ADVISOR_DISCOUNT,消费位 = invest_env/invest_strategy),
# 本文件不留分值常数——宪法五,衍生打分归策略层;floor 定序形态随
# 消费核停用 历史。)


def _validate_random_char_spec(table: str, name: str, spec: RandomCharSpec) -> None:
    """RandomCharSpec 构建校验(ENV_GIFTS 与 ENV_DEPLOY_LOCK_GRANTS 共享):
    规格过滤池非空单一哨——手写错字与版本漂移(阵营/费用档改名)都表现为
    池空,一道闸兼顾两类;治理口径(防登记笔误的值域四查移除)见
    :func:`_validate_env_gifts` docstring。table/name = 报错定位
    (文案沿各表现款句式)。"""
    if not random_char_pool(spec):
        raise ValueError(
            f"{table} 随机赠卡池空({name!r}):"
            f"cost={spec.cost} faction={spec.faction!r} "
            f"type_tag={spec.type_tag!r} 过滤后无角色(注册表漂移?)")


def _validate_env_gifts() -> None:
    """ENV_GIFTS 构建校验(import 即炸;只留漂移哨)。

    治理口径(用户裁定 2026-10-28):防登记笔误的值域/互斥类校验全部移除
    且不再新增(空发放集、∩ ENV_ECONOMY、定时节点键格式、定时道具名串行、
    RandomCharSpec 值域四查、装备/道具通道同名、开局替换无产出)——此类
    校验只能由写表人自己的笔误触发,收益不抵加载开销,登记错误靠评审与
    测试拦。本函数只留「能被游戏版本变更独立触发」的漂移哨:

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联 → 炸);
    ② 角色名漂移:发放角色(即时∪条件)必须在 CHARACTER_ROSTER(版本改名
    不静默);③ 随机赠卡规格过滤池非空(共享助手
    ``_validate_random_char_spec``,错字与版本漂移都致池空);④ 随机装备
    类别过滤池非空(类别错字/改名致池空);⑤ 装备名漂移:逐名 ∈
    EQUIPMENTS(版本改名;武装箱系不在装备注册表,误入本通道天然被拒);
    ⑥ '星徽' 类别池独立非空闸(首例登记类别,类别改名致池静默变空)。
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
        for _spec in _grant.chars_random_immediate:
            _validate_random_char_spec('ENV_GIFTS', _name, _spec)
        for _cat in _grant.equips_random_immediate:
            if not equips_by_category(_cat):
                raise ValueError(
                    f"ENV_GIFTS 随机装备池空({_name!r}):"
                    f"category={_cat!r} 过滤后无装备(错字/注册表漂移?)")
        for _eq in _grant.equips_immediate:
            if _eq not in EQUIPMENTS:
                raise ValueError(
                    f"ENV_GIFTS 装备名漂移({_name!r} 注册表无此装备,"
                    f"版本改名?):{_eq!r}")
    # 本闸系环境登记首例(劳务派遣合同)所立,消费面含策略侧随机装备支
    # (买彩票经 cw_gain_effects._STRATEGY_RANDOM_EQUIP_GRANTS 星徽行搭
    # 便车——泛化表不另设 import 期闸,沿族既定裁定)——单一闸两消费者,
    # 环境登记迁移时勿误删本闸。
    if not equips_by_category('星徽'):
        raise ValueError(
            "ENV_GIFTS 随机装备类别池空:'星徽' 类别过滤后无装备"
            "(首例登记类别,类别改名致池静默变空 = 注册表漂移)")


_validate_env_gifts()


# ===== 策略卡具名发放登记表(白名单制)=====
# 底册 = 双母体对账(92 条):①STRATEGY_BINDINGS 角色绑定条目 ∩ 「获得…直读」
# 形态机械预筛(68 条白得 + 11 条顾问);②全表效果文本反扫(「获得…roster 名」)
# 补网 4 条(龙虎兄弟狸/佩佩驾到/艾丝妲的猛犬!/招财狗——无角色绑定的直读
# 发放,佩佩 ∈ CHARACTER_ROSTER);③开箱分支 6 条(战术义眼++/保守派/快请
# 专家·彩/军火贸易/军火贸易+/步狸村之谜,「获得…【箱】」占席道具直读,迭代
# 2026-09-24-advanced-armory-box);④非直读人工转正 3 条(溜佩佩/溜佩佩+,
# 卡面「佩佩逛街」句 = 效果实现发放但非「获得」直读引导,人工裁定入册,
# 反扫白名单两键同批退役;这么大的钻石 = 用户裁定 2026-11-02 拍读法 B
# 「佩佩真实入后台」,佩佩携钻句同判入册);⑤非候选直读登记 1 条(狸职
# 手续,「获得」直读
# 但发放对象为卡面用名「狸狸」∉ CHARACTER_ROSTER,反扫零命中自动排除,
# 按实机录名归一登记)。
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
    # 兼即时分支与条件分支(条件分支 = 「获得3星【黑塔】时获得【大黑塔】」再得);
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
    # 分支的开拓者 ∉ CHARACTER_ROSTER 排除
    '盗用身份': GiftGrant(
        chars_conditional=(('火花', '进入第二位面的首领节点时'),),
    ),
    # 砂里淘金:「合成2星2费角色时」条件发放(估值域登记,本条目零世界
    # 发放运行时消费;世界发放通道 = STRATEGY_MERGE_GRANTS +
    # cw_gain_chain.check_strategy_merge_grants)
    '砂里淘金': GiftGrant(
        chars_conditional=(('砂金', '合成2星2费角色时'),),
    ),
    # 迷之旅人:两条分支均条件(激活4巡海游侠时 2星黄泉/下一奖励节点 波提欧)
    '迷之旅人': GiftGrant(
        chars_conditional=(
            ('黄泉', '激活4巡海游侠时获得2星黄泉'),
            ('波提欧', '进入下一个奖励节点时'),
        ),
    ),
    # 轮回不止:「获得【白厄】」即时;「进入第二/三位面时再获得一次」系
    # 同角色重复发放分支,角色集不变不入条件集
    '轮回不止': GiftGrant(chars_immediate=('白厄',)),
    # 飞光双件:「获得【彦卿】和【景元】」/「获得【镜流】和特殊的1费【景元】」
    '飞光·传剑': GiftGrant(chars_immediate=('彦卿', '景元')),
    '飞光·映月': GiftGrant(chars_immediate=('镜流', '景元')),
    # —— 反扫补网 4 条(无角色绑定的「获得…」直读发放)——
    '龙虎兄弟狸': GiftGrant(chars_immediate=('狸小龙', '狸小虎')),
    '佩佩驾到': GiftGrant(chars_immediate=('佩佩',)),
    '艾丝妲的猛犬！': GiftGrant(chars_immediate=('佩佩',)),
    '招财狗': GiftGrant(chars_immediate=('佩佩',)),
    # —— 开箱分支 5 条(占席道具发放;效果原文对账 id = cw_invest_data.
    # PLAZA_AUGMENTS:战术义眼++ 350403/保守派 351501/快请专家·彩 360201/
    # 军火贸易 101401/军火贸易+ 101402;「获得1个/一件【箱】」直读,箱名 =
    # items 元素,数量 = 元素重复次数)——
    # 另三卡的战斗被动分支(战术义眼++能量恢复/保守派伤害减免/快请专家·彩
    # 能量恢复)非「获得时点」效果,不属 GiftGrant 登记适用范围(归策略效果
    # 建模批);
    # 快请专家·彩只登记开箱分支:好运令牌非占席道具(入 items 会错进
    # BENCH_ITEM_NAMES 被当占席道具,归消耗品域)、「获得2个【】」空括号分支
    # 数据源缺口禁猜——两条分支查无登记即安静不写,真值归实机/数据源勘误。
    '战术义眼++': GiftGrant(items_immediate=('进阶武装箱',)),
    '保守派': GiftGrant(items_immediate=('进阶武装箱',)),
    '快请专家·彩': GiftGrant(items_immediate=('进阶武装箱',)),
    # 军火贸易:「获得1个【简易武装箱】」直读;金腿「获得4金币」经
    # STRATEGY_ECONOMY instant_gold=4 在册(经济聚合面),不属本表登记范围。
    '军火贸易': GiftGrant(items_immediate=('简易武装箱',)),
    # 军火贸易+:「获得1个【简易武装箱】」直读;金腿「获得8金币」经
    # STRATEGY_ECONOMY instant_gold=8 在册(经济聚合面),不属本表登记范围。
    '军火贸易+': GiftGrant(items_immediate=('简易武装箱',)),
    # 步狸村之谜:箱腿直读「和一个【简易武装箱】」(狸狸腿零建模 = 快请
    # 专家·彩部分登记 + 孪生姵姵 roster-外处置双在册先例,禁猜;穿戴腿
    # 零建模 = T-16 §8-1 用户裁定同判,披露键申报)。
    '步狸村之谜': GiftGrant(items_immediate=('简易武装箱',)),
    '阿哈大悦': GiftGrant(items_immediate=('简易武装箱',)),
    # 秘密典籍:箱腿直读「获得1个【星徽秘典】」(对账 id 230901;
    # 金腿 instant_gold=8 在册零改动;流程面占席→开典籍→星徽四选一
    # →选卡观察全链在码零触碰)。
    '秘密典籍': GiftGrant(items_immediate=('星徽秘典',)),
    # 秘密典籍+:箱腿直读「获得1个【星徽秘典】」(对账 id 230902;
    # 金腿 instant_gold=12 在册零改动;KINDS 进阶武装箱 supply_box 在码
    # 零改动,姊妹典籍 tome 槽件差分)。
    '秘密典籍+': GiftGrant(items_immediate=('进阶武装箱',)),
    # —— 非直读人工转正 3 条(佩佩逛街句/佩佩携钻句:「效果实现发放但非
    # 『获得』直读引导」,人工裁定入册;溜佩佩/+ 反扫白名单两键已随注册
    # 退役,注册后排除因「未登记」不复存在)——
    '溜佩佩': GiftGrant(chars_immediate=('佩佩',)),
    '溜佩佩+': GiftGrant(chars_immediate=('佩佩',)),
    # 这么大的钻石(231101):卡文「佩佩携带【财富宝钻】出现，这么大
    # 的钻石，送给你！」无「获得」动词,佩佩入队腿 = 效果实现发放非直读,
    # 用户裁定 2026-11-02 拍读法 B(佩佩真实入后台)人工转正入册;宝钻
    # 装备腿不进本表(装备无估值档位,星徽族先例 = 欢愉星徽只登记
    # chars_immediate 同判),世界发放 = cw_gain_effects.PICK_INVEST_
    # EFFECTS 组合登记行(佩佩×宝钻双腿);宝钻「携带」句零建模 =
    # STRATEGY_DESC_UNMODELED_KEYS 披露键 strategy_worn_equip_unmodeled
    # 申报。
    '这么大的钻石': GiftGrant(chars_immediate=('佩佩',)),
    # —— 非候选直读登记 1 条(「获得3个…【狸狸】」直读,但发放对象为卡面
    # 用名「狸狸」∉ CHARACTER_ROSTER,反扫零命中 = 统一排除口径自动排除
    # 不逐条记因):登记名按实机录名「狸职狸狸」归一,依据 = cw_chars.py
    # 该员 source 注记逐字辖本卡 id 204001(source="live:狸职手续204001"),
    # 按卡面用名登记会被角色名漂移哨炸,归一为唯一可行登记形态;数量 3
    # 不进登记(估值档位与只数无关,摸个鱼吧II 单名先例同判),承载于世界
    # 发放腿 cw_gain_effects._STRATEGY_CHAR_GRANTS('狸职手续' → ×3);穿戴
    # 句/周期离场句零建模 = STRATEGY_DESC_UNMODELED_KEYS 两键申报。
    '狸职手续': GiftGrant(chars_immediate=('狸职狸狸',)),
}

# ===== 占席道具「名字→类别」映射桥 + 词表(BenchSlot 身份轴/类别轴一致性权威)=====
# 实机真值(2026-09-24 用户确认):占席道具与角色同款溢出语义——席满落溢出
# 席并阻断进入战斗。溢出位身份串(overflow_card)因此有两分:角色 char_id /
# 占席道具名。
# BENCH_ITEM_KINDS = 占席道具槽件「名字→类别」全量显式映射(用户裁定
# 2026-10-24:全量显式制,静默落错身份的治理劣于响亮缺登记)。「全量」
# 口径 = 授予通道占席道具(键集闭合 = 两张授予表 items_* 通道道具名并集;
# 2026-10-28 治理后闭合校验移除,键集一致性归数据性质测试与评审,漏登
# 后果 = 落席直查 KeyError 响亮);观察专属来源(星徽秘典,tome)不经授予
# 通道,不入本表不入词表(豁免,名字一致性由识别双渲染注册表承载)。
# 词表 BENCH_ITEM_NAMES 只答「是不是占席道具」;本表答「是哪种」并兼任
# BenchSlot 身份轴(item)与类别轴(kind)的一致性权威:授予通道道具类槽
# 构造一律 item=<名> 且 kind=BENCH_ITEM_KINDS[<名>]。kind 合法值 =
# 'supply_box' | 'bookcard'。消费方:
# - cw_gain_chain._place_bench_item 落席本体/_build_pool 溢出占位:道具
#   身份禁造 Unit 假身份进合成素材组,槽件带名;
# - cw_action_report.sell_bench 溢出分支:卖牌腾槽入位按映射落带名槽件。
BENCH_ITEM_KINDS: dict[str, str] = {
    '简易武装箱': 'supply_box',
    '特权武装箱': 'supply_box',
    '进阶武装箱': 'supply_box',
    '专家邀请函': 'bookcard',
    '星徽秘典': 'tome',
}

BENCH_ITEM_NAMES: frozenset[str] = frozenset(BENCH_ITEM_KINDS)

# 反扫候选闭集防线的排除/假阳性白名单(逐条记因;键必须在注册表):
# - 愚者恶作剧:概率变形发放(2/4 费卡概率变为【花火】/【火花】),无「获得」
#   字样,非直读发放;
# - 快请专家·金/彩:「获得1个【】/2个【】」空名不可具名(注册键各自独立);
# - 孪生姵姵:发放对象「姵姵」∉ CHARACTER_ROSTER(反扫命中的「佩佩」系
#   「和你的佩佩一模一样」对比句非发放)。
# 統一排除口径覆盖未来同类:roster-外目标与空名发放天然不产反扫命中,自动
# 排除不逐条记因;本白名单只收现存例外。
# (溜佩佩/溜佩佩+ 两键已随注册入 STRATEGY_GRANTS 退役——记因「实发放但
# 非『获得』引导」在注册后失真,防线由注册表覆盖,删留行为等价取洁净。)
_STRATEGY_GRANTS_SCAN_EXCLUSIONS: dict[str, str] = {
    '愚者恶作剧': '概率变形发放、无「获得」字样',
    '快请专家·金': '「获得1个【】」空名不可具名',
    '快请专家·彩': '「获得2个【】」空名不可具名',
    '孪生姵姵': '发放对象姵姵不在 CHARACTER_ROSTER',
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
    """STRATEGY_GRANTS 构建校验(import 即炸;沿 _validate_env_gifts 先例,
    治理口径同源——只留漂移哨,防登记笔误类校验见其 docstring):

    ① 孤儿键:键必须在 INVESTMENT_STRATEGIES(防版本更新改名/移除后静默
    失联);② 角色名漂移:发放角色(即时∪条件)必须在 CHARACTER_ROSTER;
    ③ **反扫候选
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


# 占席道具映射桥的双向闭合/值域校验已随 2026-10-28 校验治理移除(键集
# 闭包与拼写闭集均只能由登记动作自身触发,防笔误类)——漏登的运行期后果
# = 授予通道落席直查 KeyError,响亮可见,登记面归评审把关。


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
# 与刷新世界分支,2026-10-19 用户裁定批接入)。
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
      数量通道登记,§2.2.4;消费端 = sim 策略屏刷新呈现与刷新世界分支
      (基准每卡 1 次 + 本增量;2026-10-19 用户裁定 sim 与实机一致提供
      刷新次数批接入);live 不经本字段——bot 读屏幕现值)
    - extra_strategy_offer_node: 额外策略三选一发生的挂点节点,**坐标系 =
      (位面, 轮次) 单点,两元各 1 基**(效果原文「X-Y 节点」= 位-轮读法,
      用户裁定 2026-10-16;依据与边界 = ENV_POOL_REWRITE 登记处注释);
      数量通道登记,执行消费端 = sim JOINT_DECISION_EXTRA_SLOT 派生;
      None = 无额外策略三选一
    - extra_strategy_grant_node: 额外策略**直接发放**发生的挂点节点,
      **坐标系与 extra_strategy_offer_node 同 = (位面, 轮次) 单点两元各
      1 基**(T-46 策略大师数量分支;直发非 offer 三选一,不复用 offer 字段
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
    # 互斥闸语义化豁免的现值形态(互斥校验已随 2026-10-28 治理移除,
    # 单一估值落点归评审把关);
    # 执行消费端 = sim 直发发放事件(单一源,勘误/改值只改本登记处,
    # sim 派生查询自动跟随);
    # 挂点候实机对账:实机直发出现节点 ≠ 3-5 → 改本登记值一处(sim 自动
    # 跟随);
    # 形态 = 直接发一张随机投资策略(用户裁定 2026-10-26;远见先例形态,
    # 无选卡界面,登记注释 = 「3-5节点」位-轮单点,T-23 裁决 1 判例联动)。
    '策略大师': StrategyPoolRewrite(extra_strategy_grant_node=(3, 5)),
}


def _validate_env_pool_rewrite() -> None:
    """ENV_POOL_REWRITE 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联);
    ② 槽位品质词集:slot_qualities 逐值 ∈ 策略品质词集(rarity 注册表
    派生——错字与版本增删品质都表现为词集外);
    ③ 挂点形:extra_strategy_offer_node / extra_strategy_grant_node 非
    None 时位面 ∈ PLANE_NODE_TABLES 且轮次 ≤ 该位面序列长(节点真值表
    跨版本变化可独立触发)。
    三表互斥/结构完备/pending notes/双挂点互斥/settled 定谳闸/空条目闸
    属防登记笔误类,已移除。
    """
    orphans = [n for n in ENV_POOL_REWRITE if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(f"ENV_POOL_REWRITE 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _name, _rw in ENV_POOL_REWRITE.items():
        if _rw.slot_qualities:
            _quality_vocab = {s.rarity for s in INVESTMENT_STRATEGIES.values()}
            _bad = [q for q in _rw.slot_qualities if q not in _quality_vocab]
            if _bad:
                raise ValueError(
                    f"ENV_POOL_REWRITE 槽位品质漂移:{_name!r} "
                    f"{_bad} 不在策略品质词集(注册表漂移?):"
                    f"{sorted(_quality_vocab)}")
        for _node_field in ('extra_strategy_offer_node',
                            'extra_strategy_grant_node'):
            _node = getattr(_rw, _node_field)
            if _node is not None:
                _plane, _round = _node
                if _plane not in PLANE_NODE_TABLES:
                    raise ValueError(
                        f"ENV_POOL_REWRITE 挂点位面不在节点真值表:{_name!r} "
                        f"{_node_field}={_node}(版本漂移/登记笔误?)")
                if not 1 <= _round <= len(PLANE_NODE_TABLES[_plane]):
                    raise ValueError(
                        f"ENV_POOL_REWRITE 挂点轮次超位面节点数:{_name!r} "
                        f"{_node_field}={_node}(位面 {_plane} 序列长 "
                        f"{len(PLANE_NODE_TABLES[_plane])},版本漂移/登记笔误?)")


_validate_env_pool_rewrite()


# ===== 环境连胜触发发放注册表(
# details/env-conditional-grant.md §2;白名单制)=====
# 「条件达成的世界发放」首例登记:键 = 环境规范名,值 = (连胜阈值,发放装备名)。
# 表外环境一律无条目,禁从效果原文自动猜装(ENV_ECONOMY/ENV_GIFTS 同款纪律)。
# 消费面 = kernel/cw_env_grants.check_env_streak_grants(触发检查单一源,
# live/sim 结算接线都调它);表只收「连胜触发器」形状,升级类条件卡
# (钻石商人等)触发点各不相同,各建各表不并入本表(总纲「明确不解决」;
# 钻石商人已立 STRATEGY_LEVEL_GRANTS 专表,下方邻位)。
ENV_STREAK_GRANTS: dict[str, tuple[int, str]] = {
    # 本局首次 5 连胜 → 财富宝钻(id 104 原文直读,cw_invest_data PlazaPortal('104'))
    '深井角斗场': (5, '财富宝钻'),
}


def _validate_env_streak_grants() -> None:
    """ENV_STREAK_GRANTS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联);
    ② 装备名漂移:发放装备必须在 EQUIPMENTS(版本改名不静默)。
    阈值形属防登记笔误类,已移除。
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


_validate_env_streak_grants()


# ===== 策略卡等级触发发放注册表(钻石商人;白名单制)=====
# 「升级类条件卡各建各表」在码指令(上方 ENV_STREAK_GRANTS 表注释)与
# 用户裁定(env-conditional-grants design.md:19「不预建统一条件框架」)
# 的承接表:与 ENV_STREAK_GRANTS(连胜触发器)分表不并。表只收「等级
# 触发装备发放」形状;金发放等级卡归 STRATEGY_ECONOMY 等级触发族字段
# (gold_at_level/gold_at_level_target),两载体并存显式豁免合并(条件源
# 同形、发放通道异构)。表外卡一律无条目,禁从效果原文自动猜装
# (STRATEGY_CONDITIONAL_GRANTS 同款纪律);消费端 =
# cw_gain_chain.check_strategy_level_equip_grants(live 结算位 + sim
# advance 双点同链调用)。

@dataclass(frozen=True)
class StrategyLevelGrant:
    """策略卡「升到目标等级后发放具名装备」登记结构(策略卡等级触发
    发放通道专属登记表,首例钻石商人;字段语义 = 卡面效果原文直读):

    - level_target: 触发等级(「升到9级时」直读「9」;等级单调不减,
      达标态持续为真靠 done 闩封账非靠跨越检测——状态检查型语义,
      check_strategy_level_grants 金支同款先例);
    - item: 发放装备名(「【财富宝钻】」直读;值域 = 装备注册表名
      闭集,构建期装备名漂移哨拦截——STRATEGY_CONDITIONAL_GRANTS
      校验③同款)。"""
    id: str
    level_target: int
    item: str


STRATEGY_LEVEL_GRANTS: dict[str, StrategyLevelGrant] = {
    # 钻石商人(id 130401 原文直读,cw_invest_data.PLAZA_AUGMENTS 同 id
    # 行;「升到9级时,获得【财富宝钻】」直读入册)
    '钻石商人': StrategyLevelGrant(id='130401', level_target=9,
                                   item='财富宝钻'),
}


def _validate_strategy_level_grants() -> None:
    """STRATEGY_LEVEL_GRANTS 构建校验(import 即炸;治理口径与三漂移哨
    形状 = _validate_strategy_conditional_grants 同款——只能由写表人
    笔误触发的校验删〔level_target 形/值域属手抄常量纯笔误类,按
    2026-10-28 裁定不加〕,能被游戏版本变更独立触发的漂移哨留):

    ① 孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后
    静默失联);② id 双匹配:登记 id 必须等于 base 溯源 id(改名且 id
    仍在的漂移也炸);③ 装备名漂移:item ∈ EQUIPMENTS——错名运行期
    实况 = 静默幻影(gain_equipment 盲追加 + on_equipment_gained 查表
    .get() 安静不写 + live 调用位返回值刻意忽略),import 期哨是唯一
    响亮拦截面。"""
    orphans = [n for n in STRATEGY_LEVEL_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_LEVEL_GRANTS 孤儿键(base 无此卡?):{sorted(orphans)}")
    for _name, _grant in STRATEGY_LEVEL_GRANTS.items():
        _base = INVESTMENT_STRATEGIES.get(_name)
        if _base is not None and _base.source != f'plaza:{_grant.id}':
            raise ValueError(
                f"STRATEGY_LEVEL_GRANTS id 漂移:{_name!r} 登记 id="
                f"{_grant.id} base={_base.source}")
        if _grant.item not in EQUIPMENTS:
            raise ValueError(
                f"STRATEGY_LEVEL_GRANTS 装备名漂移({_name!r} 注册表无此"
                f"装备,版本改名?):{_grant.item!r}")


_validate_strategy_level_grants()


# ===== 策略卡损血档位触发发放注册表(保险;白名单制)=====
# 「触发点各不相同,各建各表」纪律的承接表(段注释正本 = 上方
# STRATEGY_LEVEL_GRANTS 段):与 STRATEGY_LEVEL_GRANTS 等级一次性通道
# 分表——本表 = 损血档位**周期型**触发器(无 done 闩,发放记账 = 累积器
# 取模,累积容器 = cw_game_state.strategy_hp_loss_accum),触发点/状态
# 形状/载荷三重不同构,禁并入;与 STRATEGY_WIN_GOLD_GRANTS(胜利结算
# 条件金)触发点亦不同(损血败局 vs 胜局)。键 = 策略规范名,值 =
# (档位阈值损血, 每档金, 随机装备类别, 每档件数)。表外卡一律无条目,
# 禁从效果原文自动猜装(STRATEGY_LEVEL_GRANTS 同款纪律)。
# 消费面 = kernel/cw_gain_chain.check_strategy_hp_loss_grants(触发检查
# 单一源,唯一调用点 = sim 结算腿;live 零写观察覆盖——金由游戏侧自发
# 入账、equips 为观察域整表覆盖,实机局不接本通道)。
STRATEGY_HP_LOSS_GRANTS: dict[str, tuple[int, int, str, int]] = {
    # 保险(id 130501 原文直读,cw_invest_data.PLAZA_AUGMENTS 同 id 行;
    # 「每损失20点小队生命值,获得5金币和1个随机简易装备」直读:阈值
    # 20/每档 5 金/随机装备类别简易/每档 1 件,数值面全 desc 明写)。
    # 金载荷与 STRATEGY_ECONOMY 注册行 gold_per_20hp_lost 同值(同出
    # 卡面同句;两表面同值对账归本表域测试断言把关,2026-10-28 治理
    # 裁定 import 校验不加)。
    '保险': (20, 5, '简易', 1),
}


def _validate_strategy_hp_loss_grants() -> None:
    """STRATEGY_HP_LOSS_GRANTS 构建校验(import 即炸;治理口径 = 用户
    裁定 2026-10-28「只能由写表人笔误触发的校验删,能被游戏版本变更独立
    触发的漂移哨留」,同 _validate_strategy_level_grants docstring——
    阈值/金/件数形与双源同值属手抄常量纯笔误、单侧改数类,不加,对账
    归评审与本表域测试把关;只留两漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后静默
    失联);② 装备类别漂移:类别池 equips_by_category 非空——类别名
    漂移的运行期实况 = 池空静默幻影(发放腿零写无发放,无异常无台账),
    import 期哨是唯一响亮拦截面(on_env_gained 随机装备支池空防御分支
    同理由,彼处为运行期 log,本处前移至 import 期)。"""
    orphans = [n for n in STRATEGY_HP_LOSS_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_HP_LOSS_GRANTS 孤儿键(base 无此卡?):{sorted(orphans)}")
    for _name, (_thr, _gold, _cat, _cnt) in STRATEGY_HP_LOSS_GRANTS.items():
        if not equips_by_category(_cat):
            raise ValueError(
                f"STRATEGY_HP_LOSS_GRANTS 装备类别漂移({_name!r} 类别"
                f"注册表无装备,版本改名?):{_cat!r}")


_validate_strategy_hp_loss_grants()


#: 损血档位触发发放建模假设披露键(desc 无载面的申报,消费 = sim 随局
#: 披露面 disclosures setdefault):一键承载三项建模假设——①「每损失
#: 20 点」按当前局全程累计读法(发放刻取模,余数跨战结转);②损血记账
#: = 实际写值差(保底截断后真值,「损失」不超持有量);③触发源域 =
#: 战斗结算损血 + 选卡即时损血腿(先亏后盈类 hp_instant<0;扩挂点已
#: 落码 = apply_strategy_pick_hp 负值支,选卡损血同拍入累计器,键名/
#: 值串 battle_only 系落码时点形态冻结不随域扩展改名)。实机持卡局败局
#: 金/装备收入对照可校准,差额暴露归本键。常量落位沿
#: STRATEGY_WIN_GOLD_SCOPE_ASSUMPTION 先例(kernel 注册表模块)。
STRATEGY_HP_LOSS_BUCKET_ASSUMPTION: str = \
    'strategy_hp_loss_bucket_carry_truth_diff_battle_only'


# ===== 环境刷新次数触发发放注册表(二手市场;白名单制)=====
# **世界发放域**(条件达成的世界发放第二例,ENV_STREAK_GRANTS 同族):
# 键 = 环境规范名,值 = (计数键,阈值,金,装备名可空)。装备可空 =
# 金-only 触发器形状(长线利好族复用面)。表外环境一律无条目,
# 禁从效果原文自动猜装(ENV_ECONOMY/ENV_GIFTS 同款纪律)。
# 消费面 = kernel/cw_env_grants.check_env_refresh_grants(触发检查
# 单一源,唯一调用点 = 刷新上报函数尾部)。
# **表间豁免声明**(ENV_ORE_GRANTS 同款):本表键与 ENV_ECONOMY 共存
# (二手市场两表同时已登记),不参与「单一环境只落一个估值结构」三表
# 互斥——本表条目非效果牌面,登记即常驻触发器;两侧数值同出卡面
# (id 106),一致性归评审与刷新域测试把关(双源/跨锁校验已随
# 2026-10-28 治理移除)。与 ENV_STREAK_GRANTS 两个世界
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
    # 两域对照。装备入账分支 None = 金-only(T-7 预留形状,登记表注释点名
    # 本卡复用面);改价分支不在本表——live = 观察通道
    # (cw_shop_refresh_obs 标价 reader 采真),sim = 开店呈现经
    # cw_economy.world_shop_refresh_cost 现算渲染(两条分支阈值同出卡面
    # 同一句「30 次」,构建校验⑥跨锁同值)。
    '长线利好': (CounterKey.REFRESH_PAID, 30, 20, None),
}


def _validate_env_refresh_grants() -> None:
    """ENV_REFRESH_GRANTS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联);
    ② 装备名漂移:装备入账分支非 None 时必须在 EQUIPMENTS(版本改名
    不静默)。计数键闭集/值形/双源同值/跨锁同值属防登记笔误/单侧改数类,
    已移除(阈值对估值面/改价面的对账归评审与刷新域测试把关)。
    """
    orphans = [n for n in ENV_REFRESH_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_REFRESH_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, (_key, _threshold, _gold, _equip) in ENV_REFRESH_GRANTS.items():
        if _equip is not None and _equip not in EQUIPMENTS:
            raise ValueError(
                f"ENV_REFRESH_GRANTS 装备名漂移({_n!r} 注册表无此装备,"
                f"版本改名?):{_equip!r}")


_validate_env_refresh_grants()


# ===== 首领节点周期发放白名单(劳务派遣合同分支2;白名单制)=====
# **世界发放域**(条件达成的世界发放第三表,ENV_STREAK_GRANTS/ENV_REFRESH_
# GRANTS 同族):键 = 环境规范名,值 = 集合语义(现役无登记值,形态沿
# ENV_NODE_SUPPLY_BEFORE_BOSS 先例,cw_node_schedule)。表外环境一律无
# 条目,禁从效果原文自动猜装(ENV_ECONOMY/ENV_GIFTS 同款纪律)。
# 发放规则 = 分支1 绑定(done 条件键 'star_grant#<名>',登记于本卡在
# ENV_GIFTS 的即时分支)+ 固定每首领节点 1 个 1★ 角色;触发函数 =
# kernel/cw_env_grants.check_env_boss_grants(周期性,done 键带节点坐标)。
# **与估值三表的同键并存 = 本卡新立形态**(本卡分支1 归 ENV_GIFTS、分支2 归
# 本表,各表各分支、键语义无冲突):「世界发放表↔ENV_ECONOMY 可并存」的
# 现役豁免声明原辖 ENV_ORE/ENV_STREAK/ENV_REFRESH 与估值面的关系,不直接
# 覆盖估值三表∩世界发放表,故此处显式声明而非引先例。
ENV_BOSS_GRANTS: frozenset[str] = frozenset({'劳务派遣合同'})


def _validate_env_boss_grants() -> None:
    """ENV_BOSS_GRANTS 构建校验(import 即炸;沿 _validate_env_streak_grants
    先例):键 ⊆ INVESTMENT_ENVS(孤儿键,防版本更新改名/移除后静默失联)。
    与 ENV_GIFTS 同键 = 合法形态(两表同键各表各分支,见上区块注释显式
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
# 检查单一源,事件携带事实无 done 标记;四发火点 = 买牌上报/补给单位入账分支/
# 晶矿角色入账分支/获得链顶层)。
# **表间豁免声明**(ENV_BOSS_GRANTS 同款显式声明):本表键与 ENV_GIFTS
# 共存 = 合法形态(两表同键各表各域——ENV_GIFTS 的 chars_conditional 辖
# 估值域档位机器,本表辖世界发放,各表各域),与 ENV_ECONOMY 无 ∩ 冲突。
ENV_MERGE_GRANTS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # 花火和缇宝升星时,随机获得【符玄】或【希儿】(id 125 原文直读,
    # cw_invest_data PlazaPortal('125'))
    '量子同频契约': (('花火', '缇宝'), ('符玄', '希儿')),
}


def _validate_env_merge_grants() -> None:
    """ENV_MERGE_GRANTS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联);
    ② 角色名漂移:触发角色集与发放池逐名必须在 CHARACTERS(版本改名
    不静默)。值形非空属防登记笔误类,已移除。
    """
    orphans = [n for n in ENV_MERGE_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_MERGE_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, (_triggers, _pool) in ENV_MERGE_GRANTS.items():
        for _label, _names in (('触发角色集', _triggers), ('发放池', _pool)):
            for _name in _names:
                if _name not in CHARACTERS:
                    raise ValueError(
                        f"ENV_MERGE_GRANTS 角色名漂移({_n!r} {_label},"
                        f"角色注册表无此名,版本改名?):{_name!r}")


_validate_env_merge_grants()


# ===== 策略卡合并升星触发发放注册表(砂里淘金;白名单制)=====
# **世界发放域**(条件发放登记表,ENV_STREAK/REFRESH/BOSS/MERGE/INTEREST/
# ORE_OPEN/BATTLE/DEPLOY_LOCK_GRANTS 同族;**键域首例 = 投资策略卡**,
# 先例族键 = 环境规范名):键 = 卡规范名,值 = (判据星级, 判据费用,
# 发放角色名) 三元组。语义 = 持有该卡期间,每合成出「产物星级 ∧ 产物
# 费用」双匹配的角色(new_star+cost 双匹配),获得 1 个发放角色
# (1★ 先验:卡面无星级,沿合成发放族用户裁定「发放 1★」先验,实机
# 取证后可校正);逐级逐事件 = 用户裁定「每完成一级 3 合 1 各发一次」
# 判例同判(级联逐级各查各发)。表外卡一律无条目,禁从效果原文自动
# 猜装(白名单制注册纪律,ENV_MERGE_GRANTS 区块同款)。
# **表间豁免声明**(ENV_MERGE_GRANTS 同款显式声明):本表键与
# STRATEGY_GRANTS 共存 = 合法形态(两表同键各表各域——STRATEGY_GRANTS
# 的 chars_conditional 辖估值域档位机器,本表辖世界发放);与
# STRATEGY_ECONOMY 的 gold_per_2star2cost_merge(折金近似估值腿)无写
# 冲突(彼腿按金折算下界估值,本表按角色具名世界真值,语义正本 =
# fields.md §5.3 砂里淘金小节)。消费面 =
# kernel/cw_gain_chain.check_strategy_merge_grants(触发检查单一源,
# 事件携带事实无 done 标记;四发火点 = 买牌上报/晶矿角色入账分支/
# 补给级联/获得链顶层,与 check_env_merge_grants 同点独立 try 并排)。
STRATEGY_MERGE_GRANTS: dict[str, tuple[int, int, str]] = {
    # 砂里淘金(id 201501 原文直读,cw_invest_data.py「合成2星2费角色时，
    # 获得1张【砂金】。」):判据 2星+2费,发放 1 个砂金(2 费,cw_chars)
    '砂里淘金': (2, 2, '砂金'),
}


def _validate_strategy_merge_grants() -> None:
    """STRATEGY_MERGE_GRANTS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨,
    _validate_env_merge_grants 同字形):

    ① 孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后静默
    失联);
    ② 发放角色名漂移:发放角色必须在 CHARACTER_ROSTER(版本改名不静默)。
    判据值域(星级/费用)与三元组非负属防登记笔误类,已移除(值形对账
    归注册行直测锁承担)。
    """
    orphans = [n for n in STRATEGY_MERGE_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_MERGE_GRANTS 孤儿键(base 无此卡?):{sorted(orphans)}")
    for _n, (_star, _cost, _char) in STRATEGY_MERGE_GRANTS.items():
        if _char not in CHARACTER_ROSTER:
            raise ValueError(
                f"STRATEGY_MERGE_GRANTS 角色名漂移({_n!r} 注册表无此人,"
                f"版本改名?):{_char!r}")


_validate_strategy_merge_grants()


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
    """ENV_INTEREST_GRANTS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联);
    ② 角色名漂移:发放角色必须在 CHARACTER_ROSTER(版本改名不静默)。
    阈值形/角色名形/双源对账(ENV_GIFTS.chars_conditional 首元对拍)属
    防登记笔误/单侧改名类,已移除。
    """
    orphans = [n for n in ENV_INTEREST_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_INTEREST_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, (_threshold, _char) in ENV_INTEREST_GRANTS.items():
        if _char not in CHARACTER_ROSTER:
            raise ValueError(
                f"ENV_INTEREST_GRANTS 角色名漂移({_n!r} 注册表无此人,"
                f"版本改名?):{_char!r}")


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
    """ENV_ORE_OPEN_GRANTS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联);
    ② 具名角色名漂移:具名角色元组逐名必须在 CHARACTER_ROSTER(版本
    改名不静默);
    ③ 随机羁绊池现值非空:``chars_by_faction(随机羁绊名)`` 非空(羁绊名
    错字/版本改名都表现为池空)。值形属防登记笔误类,已移除。
    """
    orphans = [n for n in ENV_ORE_OPEN_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_ORE_OPEN_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, (_first, _step, _chars, _faction) in ENV_ORE_OPEN_GRANTS.items():
        for _name in _chars:
            if _name not in CHARACTER_ROSTER:
                raise ValueError(
                    f"ENV_ORE_OPEN_GRANTS 角色名漂移({_n!r} 注册表无此人,"
                    f"版本改名?):{_name!r}")
        if not chars_by_faction(_faction):
            raise ValueError(
                f"ENV_ORE_OPEN_GRANTS 随机羁绊池空({_n!r}):"
                f"chars_by_faction({_faction!r}) 现值非空校验失败"
                f"(羁绊名漂移/登记笔误?)")


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
    """ENV_BATTLE_GRANTS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联);
    ② 参与名漂移:presence_groups 逐名 ∈ CHARACTER_ROSTER(版本改名
    不静默);
    ③ 发放角色漂移:reward_char ∈ CHARACTER_ROSTER(版本改名不静默)。
    组形/名形/锁期形/双源对账(ENV_GIFTS.chars_conditional 首元对拍)属
    防登记笔误/单侧改名类,已移除。
    """
    orphans = [n for n in ENV_BATTLE_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_BATTLE_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, _grant in ENV_BATTLE_GRANTS.items():
        for _group in _grant.presence_groups:
            for _name in _group:
                if _name not in CHARACTER_ROSTER:
                    raise ValueError(
                        f"ENV_BATTLE_GRANTS 参与名漂移({_n!r} 注册表无此人,"
                        f"版本改名?):{_name!r}")
        if _grant.reward_char not in CHARACTER_ROSTER:
            raise ValueError(
                f"ENV_BATTLE_GRANTS 发放角色漂移({_n!r} 注册表无此人,"
                f"版本改名?):{_grant.reward_char!r}")


_validate_env_battle_grants()


# ===== 环境「随机赠卡 + 节点上场锁」登记表(白名单制)=====
# 立形首例 = 英雄登场(id 133「获得1个2星5费角色,19个节点后才能将其上场。
# 战斗完胜后,上场节点额外提前1点。」,PlazaPortal('133'));登记本体 =
# 上场锁期 + 完胜加速两个机制维度,GiftGrant(估值域)无归属字段——T-10
# 裁决确立的「无锁随机赠卡归 GiftGrant.chars_random_immediate」不受影响,
# 本表只收「赠卡带锁」形。消费面:发放分支 = cw_gain_chain.on_env_gained
# (经 cw_pool.grant_char_pool 牌库时点池均匀采样 + env_grant_uid_seq
# 发号 + 解锁序位沿日程表步进),完胜提前分支 = kernel/cw_env_grants.
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
      (desc 有该分支 = True;真实值在册,防后继无完胜分支的同形卡误挂)。"""
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
    """ENV_DEPLOY_LOCK_GRANTS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联);
    ② 规格过滤池非空(共享助手 ``_validate_random_char_spec`` 单一源,
    错字与版本漂移都致池空)。锁期形/双登记防呆(∩ ENV_GIFTS)属防登记
    笔误类,已移除。
    """
    orphans = [n for n in ENV_DEPLOY_LOCK_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_DEPLOY_LOCK_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")
    for _n, _grant in ENV_DEPLOY_LOCK_GRANTS.items():
        _validate_random_char_spec('ENV_DEPLOY_LOCK_GRANTS', _n, _grant.spec)


_validate_env_deploy_lock_grants()


# ===== 环境「战利品区倒计时件 + 节点倒计时开盒」登记表(白名单制)=====
# 立形首例 = 命运礼物(id 134「立刻获得一个【惊喜盒】,倒计时12个节点后
# 礼盒打开,战斗完胜后,倒计时额外减少1点。」,PlazaPortal('134'),
# cw_invest_data.py)。惊喜盒 = 战利品区浮动件非占席(实机板件实证 =
# 与晶矿球同区,T-34 设计稿 §1 两帧证据),故不入 GiftGrant(道具通道 =
# _place_bench_item 占席落位,与板件位置直接矛盾)、不入 BENCH_ITEM_NAMES
# 词表(非占席,词表派生式零扩)。消费面:到手分支 = cw_gain_chain.
# on_env_gained 延迟道具支线(纯队列登记零席位写);开盒分支 =
# cw_gain_chain.discharge_due_item_opens 原语(sim 进节点收口挂点,
# 实机局不接);完胜加速分支 = kernel/cw_env_grants.
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
    - perfect_win_accel: 「战斗完胜后,倒计时额外减少1点」加速分支旗
      (分支本体 = T-34 设计稿裁决点 1)。"""
    item: str
    open_delay_nodes: int
    perfect_win_accel: bool


ENV_DELAYED_ITEM_GRANTS: dict[str, EnvDelayedItemGrant] = {
    # 命运礼物(id 134 原文直读,cw_invest_data.py:402)
    '命运礼物': EnvDelayedItemGrant(item='惊喜盒', open_delay_nodes=12,
                                    perfect_win_accel=True),
}


def _validate_env_delayed_item_grants() -> None:
    """ENV_DELAYED_ITEM_GRANTS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联)。
    件名形/串行防呆/倒计时形/双登记防呆/加速旗形属防登记笔误类,已移除。
    """
    orphans = [n for n in ENV_DELAYED_ITEM_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_DELAYED_ITEM_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")


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
    """ENV_SUPPLY_EQUIP_COUNT 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):
    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联)。
    值形属防登记笔误类,已移除。"""
    orphans = [n for n in ENV_SUPPLY_EQUIP_COUNT if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_SUPPLY_EQUIP_COUNT 孤儿键(base 无此环境?版本改名?):"
            f"{sorted(orphans)}")


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
    """ENV_ORE_PANEL_BONUS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):
    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联);
    ② 键集与扑满名单 PIGGY_ENV_NAMES **完全一致**(响亮向,禁 ⊆ 静默
    向):第三扑满环境出现(名单增员)或扑满卡移除(名单减员)即
    import 炸,强制逐环境显式拍定占位增量,防名单扩员后增量静默缺档
    (游戏版本变更可独立触发 = 漂移哨)。值形属防登记笔误类,已移除。"""
    orphans = [n for n in ENV_ORE_PANEL_BONUS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_ORE_PANEL_BONUS 孤儿键(base 无此环境?版本改名?):"
            f"{sorted(orphans)}")
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
# 语义:表内环境的发牌(kernel/cw_shop_deal 翻星分支,sim deal_shop 与实机
# 刷新随机态分支共用)中,每张非空商店牌独立按 p 升 2★;表外环境恒 1★。
# 值 = 用户占位非游戏真值(首例人才下沉 0.2/卡,2026-10-16 用户裁定;
# desc 无数值,待实机采证校准),禁从效果原文猜值——其余「商店出 2★」
# 类效果入表须各自取得用户拍定。占位申报披露键 =
# sim/cw_sim_backend.SHOP_TWO_STAR_DEAL_PLACEHOLDER。
ENV_SHOP_TWO_STAR_DEAL_PROB: dict[str, float] = {
    '人才下沉': 0.2,
}


def _validate_env_shop_two_star_deal_prob() -> None:
    """ENV_SHOP_TWO_STAR_DEAL_PROB 构建校验(import 即炸;治理口径 =
    用户裁定 2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):
    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联)。
    值形属防登记笔误类,已移除。"""
    orphans = [n for n in ENV_SHOP_TWO_STAR_DEAL_PROB
               if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_SHOP_TWO_STAR_DEAL_PROB 孤儿键(base 无此环境?版本改名?):"
            f"{sorted(orphans)}")


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
# 表间豁免声明:本表键与 ENV_ECONOMY 共存,不参与「单一环境只落一个估值
# 结构」互斥;两侧系数同出卡面(id 147),一致性归评审与取卡域测试把关
# (双源同值校验已随 2026-10-28 治理移除)。
ENV_PICK_GRANTS: dict[str, int] = {
    # 每取一张策略 +coef×含本张已持有数(id 147 原文直读「2*已拥有投资策略数」;
    # 口径 = 含本张(用户裁定 2026-10-26):第 k 张到手发 coef×k,首张 coef×1)
    '策略大师': 2,
}


def _validate_env_pick_grants() -> None:
    """ENV_PICK_GRANTS 构建校验(import 即炸;治理口径 = 用户裁定
    2026-10-28,见 _validate_env_gifts docstring——只留漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_ENVS(版本更新改名/移除后静默失联)。
    值形/双源同值(ENV_ECONOMY.gold_per_strategy_coef 对拍)属防登记
    笔误/单侧改数类,已移除。
    """
    orphans = [n for n in ENV_PICK_GRANTS if n not in INVESTMENT_ENVS]
    if orphans:
        raise ValueError(
            f"ENV_PICK_GRANTS 孤儿键(base 无此环境?):{sorted(orphans)}")


_validate_env_pick_grants()


# ===== 策略卡延时 offer 注册表(白名单制;策略延时三选一 offer 通道
# ===== 模式件,黄金期货首例)=====

@dataclass(frozen=True)
class StrategyDelayedOffer:
    """策略卡「N个节点后,一次定品质三选一」登记结构(策略延时
    offer 通道专属登记表;字段语义 = 卡面效果原文直读):

    - delay_nodes: 延时节拍(「5个节点后」直读);**0 = 拿卡拍立即呈现**
      (「立刻进行一次…三选一」直读,呈现挂点 = sim 拿卡拍立即腿,
      与 ≥1 的窗首到期腿双挂点分立);≥1 = 到点窗 = 拿卡节点的
      第 N 个后继节点窗(计数起点语义与效果账本「后继 N 节点」口径对齐,
      desc 未写明计数起点处不实机查);
    - offer_quality: 候选品质(「黄金投资策略三选一」直读为金;值域 =
      注册表 rarity 闭集 {'银','金','棱彩'},InvestmentStrategy.rarity
      注释同源);
    - refresh_count: offer 刷新授权次数(「选择有3次刷新机会」直读 3;
      0 = 不可刷 = 「不能刷新」卡面直读,呈现恒空刷新授权(refresh_slots
      空表 = op 闸无授权)、live 刷新闸读缺 = 无授权,两侧零分支即承载;
      数值单一源 = 本字段,呈现授权逐卡按其呈现(sim 呈现面与实机
      「计数印在卡上」同形),对账面 = 实机局该 offer 刷新钮读数对照)。

    立专表辨析:效果账本 EffectSpec payload 闭集(经济/战场/单位增益)
    不容「延时流程事件」维度;STRATEGY_GRANTS(GiftGrant)维度不符
    (具名发放物 vs 延时流程事件,消费端 = 估值两处)——新机制维度
    (倒计时 + 定品质)专属专表。"""
    id: str
    delay_nodes: int
    offer_quality: str
    refresh_count: int = 0


STRATEGY_DELAYED_OFFERS: dict[str, tuple[StrategyDelayedOffer, ...]] = {
    # 黄金期货(效果原文「5个节点后，进行一次不能刷新的黄金投资策略
    # 三选一。」直读;效果原文对账 id = cw_invest_data.PLAZA_AUGMENTS
    # 同 id 行。同族展开卡各自独立批领取,禁顺手代登记——金池内被选中
    # 的未注册卡 = 安静不写,真值归观察覆盖。值形 = 腿元组(登记序 =
    # 确定性;单腿卡一元元组):窗首到期腿呈现取元组内最大节拍腿,
    # delay_nodes=0 立即腿由 sim 拿卡拍挂点消费、窗首通道不辖——
    # 呈现语义只读品质+刷新授权,同值腿序无歧义)
    '黄金期货': (StrategyDelayedOffer(id='101101', delay_nodes=5,
                                       offer_quality='金'),),
    # 黄金期货+(效果原文「4个节点后，进行一次不能刷新的黄金投资策略
    # 三选一。」直读;效果原文对账 id = cw_invest_data.PLAZA_AUGMENTS
    # 同 id 行;与黄金期货仅倒计时数值不同,机制全量继承)
    '黄金期货+': (StrategyDelayedOffer(id='101102', delay_nodes=4,
                                        offer_quality='金'),),
    # 彩虹期货(效果原文「5个节点后，进行一次不能刷新的棱彩投资策略
    # 三选一。」直读;效果原文对账 id = cw_invest_data.PLAZA_AUGMENTS
    # 同 id 行(PlazaAugment 201101)。数据行 rarity='金' 与 offer 定
    # 品质「棱彩」两语义并列——卡自身品质与 offer 产出池品质,混淆
    # 即反转)
    '彩虹期货': (StrategyDelayedOffer(id='201101', delay_nodes=5,
                                       offer_quality='棱彩'),),
    # 彩虹期货+(效果原文「4个节点后，进行一次不能刷新的棱彩投资策略
    # 三选一。」直读;效果原文对账 id = cw_invest_data.PLAZA_AUGMENTS
    # 同 id 行(PlazaAugment 201102);与彩虹期货仅倒计时数值不同,机制
    # 全量继承——卡自身品质与 offer 产出池品质两语义并列,混淆即反转)
    '彩虹期货+': (StrategyDelayedOffer(id='201102', delay_nodes=4,
                                        offer_quality='棱彩'),),
    # 白银投资(效果原文「立刻进行一次白银投资策略三选一，选择有3次
    # 刷新机会。3个节点后，再获得一个。」直读;效果原文对账 id =
    # cw_invest_data.PLAZA_AUGMENTS 同 id 行)——族首个双腿卡,两腿
    # 元组(登记序 = 腿序,确定性):腿1 立刻三选一(delay_nodes=0,
    # 拿卡拍立即呈现);腿2 「3个节点后再获得一个」= 完整包复刻(再来
    # 一次「白银三选一+3刷」,句序一致读法)。两腿同品质银池 + 同刷新
    # 授权 3;本卡品质金 ∈ 金池、offer 定品质银 → 采样无自指。
    '白银投资': (StrategyDelayedOffer(id='203201', delay_nodes=0,
                                       offer_quality='银',
                                       refresh_count=3),
                 StrategyDelayedOffer(id='203201', delay_nodes=3,
                                      offer_quality='银',
                                      refresh_count=3)),
}


def _validate_strategy_delayed_offers() -> None:
    """STRATEGY_DELAYED_OFFERS 构建校验(import 即炸;沿
    _validate_strategy_effects 同款治理口径——只留漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_STRATEGIES(防版本更新改名/移除后
    静默失联);② id 双匹配:登记 id 必须等于 base 溯源 id(改名且 id
    仍在的漂移也炸;逐腿检——双腿卡两腿同 id 同源对拍)。值域类校验
    (delay_nodes int/quality 越域/refresh_count 值域)属防登记笔误类,
    按 2026-10-28 治理裁定不加(漏登/错值后果 = 拿卡入队或呈现腿查表
    KeyError,响亮可见)。
    """
    orphans = [n for n in STRATEGY_DELAYED_OFFERS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_DELAYED_OFFERS 孤儿键(base 无此卡?):{sorted(orphans)}")
    for _name, _legs in STRATEGY_DELAYED_OFFERS.items():
        _base = INVESTMENT_STRATEGIES.get(_name)
        for _offer in _legs:
            if _base is not None and _base.source != f'plaza:{_offer.id}':
                raise ValueError(
                    f"STRATEGY_DELAYED_OFFERS id 漂移:{_name!r} 登记 id="
                    f"{_offer.id} base={_base.source}")


_validate_strategy_delayed_offers()


# ===== 策略卡条件发放登记表(白名单制;策略卡条件发放通道模式件)=====
# 「首次达成世界条件后发放具名装备」族首例(规模效应 id 101301):条件
# 检查不在拿卡时点(拿卡即时腿 = PICK_INVEST_EFFECTS 通道,handler 只在
# 拿卡时点分派一次,维度不符),而在节点边界 tick 内联腿对容器现值求值
# ——获路全集不可枚举(买入双端不经获得链角色原语/补给走 cascade/选卡
# 真值归观察覆盖),tick 单钩状态检查零枚举覆盖全获路。表外卡一律无
# 条目,禁从效果原文自动猜装(STRATEGY_GRANTS/ENV_GIFTS 同款纪律);
# 同族后续卡按「注册行直用本通道」接入,异形条件(非同名计数)另案。
# 消费端 = cw_gain_chain.check_strategy_conditional_grants(唯一调用点 =
# cw_game_state tick advanced 闸)。

@dataclass(frozen=True)
class StrategyConditionalGrant:
    """策略卡「首次拥有 N 个同名角色后发放具名装备」登记结构(策略卡
    条件发放通道专属登记表;字段语义 = 卡面效果原文直读):

    - item: 发放装备名(「【完美投影仪】」直读;值域 = 装备注册表名
      闭集,EQUIPMENTS 为游戏数据派生注册表、版本改名可独立触发 →
      构建期装备名漂移哨拦截,本表校验③);
    - threshold_same_name: 同名角色单位数阈值(「8个一样的角色」直读
      8;计数口径 = 单位数,升星产物计 1——量词「个」直修饰角色单位,
      池口径 = 备战 ∪ 上阵 ∪ 溢出全池,与升星判断同池)。
    """
    id: str
    item: str
    threshold_same_name: int


STRATEGY_CONDITIONAL_GRANTS: dict[str, StrategyConditionalGrant] = {
    # 规模效应(id 101301 原文直读,cw_invest_data.PLAZA_AUGMENTS 同 id
    # 行;「获得1个【完美投影仪】」直读入册,登记判据与 STRATEGY_GRANTS
    # 「获得…」直读同源)
    '规模效应': StrategyConditionalGrant(id='101301', item='完美投影仪',
                                          threshold_same_name=8),
}


def _validate_strategy_conditional_grants() -> None:
    """STRATEGY_CONDITIONAL_GRANTS 构建校验(import 即炸;治理口径 =
    2026-10-28 裁定「只能由写表人笔误触发的校验删,能被游戏版本变更
    独立触发的漂移哨留」,本表落三漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_STRATEGIES(防版本更新改名/移除后
    静默失联);② id 双匹配:登记 id 必须等于 base 溯源 id(改名且 id
    仍在的漂移也炸);③ 装备名漂移:item ∈ EQUIPMENTS(同
    _validate_env_gifts 装备名漂移哨同形——EQUIPMENTS 为游戏数据派生
    注册表,版本更新改名/移除装备可独立触发)。③的运行期实况 = 错名
    静默:gain_equipment 对未知名盲追加(幻影装备入栏)、
    on_equipment_gained 查表 .get() 安静不写、检查腿居 tick 吞异常位
    ——错名最终 = 静默幻影装备 + placed=True 永久落闩全程零报错,
    import 期哨是唯一响亮拦截面。threshold 值域(形/下界)= 手抄
    常量纯笔误类(游戏版本变更不可能独立触发),按治理裁定不加。
    """
    orphans = [n for n in STRATEGY_CONDITIONAL_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_CONDITIONAL_GRANTS 孤儿键(base 无此卡?):"
            f"{sorted(orphans)}")
    for _name, _grant in STRATEGY_CONDITIONAL_GRANTS.items():
        _base = INVESTMENT_STRATEGIES.get(_name)
        if _base is not None and _base.source != f'plaza:{_grant.id}':
            raise ValueError(
                f"STRATEGY_CONDITIONAL_GRANTS id 漂移:{_name!r} 登记 id="
                f"{_grant.id} base={_base.source}")
        if _grant.item not in EQUIPMENTS:
            raise ValueError(
                f"STRATEGY_CONDITIONAL_GRANTS 装备名漂移({_name!r} "
                f"注册表无此装备,版本改名?):{_grant.item!r}")


_validate_strategy_conditional_grants()


# ===== 策略卡首购经验登记表(白名单制;购买触发族「获得本投资策略后,
# ===== 首次购买X费角色时,获得Y点经验值」首例)=====
# 世界发放单一源;消费端 = cw_gain_chain.check_strategy_first_buy_xp_grants
# (唯一调用点 = 买牌上报尾段发火腿,live 零写观察覆盖)。表外卡一律无
# 条目,禁从效果原文自动猜装(STRATEGY_CONDITIONAL_GRANTS 同款纪律);
# 同族后续「首购」卡按「注册行直用本通道」接入。值下标 = 费用−1(费用
# 域 1..5,表外费用零发放留证);一次性闩 = strategy_conditional_done
# 复合键 ``first_buy_xp#<费用>``(费用粒度五桶各一发,纯卡名键会让同卡
# 第二费用桶被误短路——对条件腿纯卡名键条款的显式扩展)。

STRATEGY_FIRST_BUY_XP_GRANTS: dict[str, tuple[int, int, int, int, int]] = {
    # 孪生素数:官方「获得本投资策略后，首次购买1/2/3/4/5费角色时，获得
    # 2/3/5/7/11点经验值。」(id 200201 原文直读,cw_invest_data.PLAZA_
    # AUGMENTS 同 id 行;五桶全 desc 明写,零披露键——读法申报制)
    '孪生素数': (2, 3, 5, 7, 11),
}


def _validate_strategy_first_buy_xp_grants() -> None:
    """STRATEGY_FIRST_BUY_XP_GRANTS 构建校验(import 即炸;治理口径 =
    用户裁定 2026-10-28「只能由写表人笔误触发的校验删,能被游戏版本
    变更独立触发的漂移哨留」,同 _validate_strategy_win_gold_grants
    docstring——本表只落孤儿键一哨):

    孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后静默
    失联)。五桶经验数为手抄常量,纯笔误类(游戏版本变更不可能把
    5 元全正 int tuple 变非法;卡面数值漂移后元组仍是合法形,哨不响),
    值形校验按治理裁定不加,对账归评审与本表域测试把关(行值精确
    断言 + id 对拍,防线强于 import 期形查)。
    """
    orphans = [n for n in STRATEGY_FIRST_BUY_XP_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_FIRST_BUY_XP_GRANTS 孤儿键(base 无此卡?):"
            f"{sorted(orphans)}")


_validate_strategy_first_buy_xp_grants()


# ===== 策略卡装备获得转换登记表(自由市场/好运来;白名单制)=====
# 「每当你将要获得一件X装备时,改为获得Y」族登记面(装备获得转换族:
# 模式卡自由市场 = 占席道具目标分支;姊妹卡独家代言 331401 目标为装备,
# 独立批领取禁顺手代登记)。拦截点 = 获得原语 gain_equipment 顶段单一
# 咽喉(消费端 = cw_gain_chain.gain_equipment 守卫;获路全集不可枚举,
# T-102-attack F1 教训同源——原语内拦截对一切经原语的获得事件自动全域
# 覆盖,含持卡自身卡腿与开箱链;live 零写观察覆盖,实机转换由游戏自算,
# 双容器观察自然对账)。表外卡一律无条目,禁从效果原文自动猜装
# (STRATEGY_CONDITIONAL_GRANTS 同款纪律);键 = 卡规范名,值 = (源装备
# 类别, 目标名);目标域判别 = 目标名 ∈ BENCH_ITEM_NAMES → 占席道具
# 分支(消费端转发占席道具原语),∉ → 装备分支(消费端名字替换落原
# 插入路径,两分支语义住 cw_gain_chain.gain_equipment 顶段)。
STRATEGY_EQUIP_GAIN_CONVERSIONS: dict[str, tuple[str, str]] = {
    # 自由市场(id 130601 原文直读,cw_invest_data.PLAZA_AUGMENTS 同 id
    # 行;「将要获得一件简易装备」→ 源类别简易,「改为获得1个【简易武装
    # 箱】」→ 目标占席道具,转换确定事件零采样)
    '自由市场': ('简易', '简易武装箱'),
    # 好运来(id 231601 原文直读,cw_invest_data.PLAZA_AUGMENTS 同 id 行)
    # 的获得腿:「合成与获得进阶装备时，改为获得一个【好运令牌】」→ 源
    # 类别进阶、目标 = 装备注册表在册工具类物(消费端装备分支:名字替换
    # 落原插入路径,单事件单转换)。卡面合成腿不走获得链,游戏自算观察
    # 覆盖零建模;sim 现役进阶获得通道为零 = 转换休眠正确路径,任一进阶
    # 通道(如回收计划双卡随机进阶组合腿)落地即被原语顶段自动覆盖。
    '好运来': ('进阶', '好运令牌'),
}


def _validate_strategy_equip_gain_conversions() -> None:
    """STRATEGY_EQUIP_GAIN_CONVERSIONS 构建校验(import 即炸;治理口径 =
    用户裁定 2026-10-28「只能由写表人笔误触发的校验删,能被游戏版本变更
    独立触发的漂移哨留」,同 _validate_strategy_hp_loss_grants docstring
    ——源类别 ≠ 目标类别防自指属写表人纯笔误类不加,降为表域数据性质
    测试〔设计稿 §2.2 四查按治理收敛〕;只留三漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后静默
    失联);② 源类别漂移:类别池 equips_by_category 非空——类别名漂移
    的运行期实况 = 拦截谓词永不命中、转换静默失效(无异常无台账),
    import 期哨是唯一响亮拦截面(STRATEGY_HP_LOSS_GRANTS 装备类别漂移哨
    同形);③ 目标名漂移:目标名 ∈ BENCH_ITEM_NAMES ∪ EQUIPMENTS——
    错名运行期实况 = 占席道具域落席直查 KeyError 炸原语(BENCH_ITEM_
    KINDS 全量显式制)或装备域盲追加幻影,import 期哨是唯一响亮拦截
    面(_validate_strategy_conditional_grants 装备名漂移哨同理由)。"""
    orphans = [n for n in STRATEGY_EQUIP_GAIN_CONVERSIONS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_EQUIP_GAIN_CONVERSIONS 孤儿键(base 无此卡?):"
            f"{sorted(orphans)}")
    for _name, (_cat, _target) in STRATEGY_EQUIP_GAIN_CONVERSIONS.items():
        if not equips_by_category(_cat):
            raise ValueError(
                f"STRATEGY_EQUIP_GAIN_CONVERSIONS 源类别漂移({_name!r} 类别"
                f"注册表无装备,版本改名?):{_cat!r}")
        if _target not in BENCH_ITEM_NAMES and _target not in EQUIPMENTS:
            raise ValueError(
                f"STRATEGY_EQUIP_GAIN_CONVERSIONS 目标名漂移({_name!r} 词表"
                f"与装备注册表均无此名,版本改名?):{_target!r}")


_validate_strategy_equip_gain_conversions()


# ===== 策略卡战后触发发放注册表(以战养战;白名单制)=====
# 「战斗结算后的世界发放」策略域首例:键 = 策略规范名,值 = 战后发放占席
# 道具名元组。表外策略一律无条目,禁从效果原文自动猜装(ENV_STREAK_GRANTS/
# STRATEGY_CONDITIONAL_GRANTS 同款纪律);表只收「遭遇节点战斗结算后」
# 触发器形状(节点类型条件内嵌于触发函数,表不设节点键;扩形状时各建
# 各表,沿 ENV_STREAK_GRANTS 表族先例)。与 GiftGrant items_immediate
# 通道的语义边界:那条 = 选卡当场发放(登记本语义即错发),本表 =
# 战后事件 + 可重复(无 done 闩,防重归调用方节点键幂等守卫)。
# 消费面 = kernel/cw_gain_chain.check_strategy_battle_grants(触发检查
# 单一源,唯一调用点 = sim 结算腿;live 零写观察覆盖——箱落备战席有画面
# 真值可读,实机局不接本通道)。
STRATEGY_ENCOUNTER_BATTLE_GRANTS: dict[str, tuple[str, ...]] = {
    # 每次遭遇节点战斗后获得 1 个简易武装箱(id 101501 原文直读,
    # cw_invest_data.PLAZA_AUGMENTS 同 id 行;卡面金腿「获得6金币」归
    # STRATEGY_ECONOMY instant_gold 在册,不进本表)
    '以战养战': ('简易武装箱',),
}


def _validate_strategy_encounter_battle_grants() -> None:
    """STRATEGY_ENCOUNTER_BATTLE_GRANTS 构建校验(import 即炸;治理口径 =
    用户裁定 2026-10-28「只能由写表人笔误触发的校验删,能被游戏版本变更
    独立触发的漂移哨留」,同 _validate_env_streak_grants docstring——
    本表落两漂移哨):

    ① 孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后静默
    失联);② 道具名漂移:发放道具必须在 BENCH_ITEM_NAMES(占席道具
    词表,游戏数据派生,版本改名/移除可独立触发)。②的运行期实况 =
    落席原语查名字→类别映射直查 KeyError(响亮但迟:错误潜伏到首次
    遭遇结算才炸,持卡局才可达),import 期哨把拦截面前移到构建期,
    与「登记道具须在占席词表」的发放契约对齐。
    """
    orphans = [n for n in STRATEGY_ENCOUNTER_BATTLE_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_ENCOUNTER_BATTLE_GRANTS 孤儿键(base 无此卡?):"
            f"{sorted(orphans)}")
    for _name, _items in STRATEGY_ENCOUNTER_BATTLE_GRANTS.items():
        for _item in _items:
            if _item not in BENCH_ITEM_NAMES:
                raise ValueError(
                    f"STRATEGY_ENCOUNTER_BATTLE_GRANTS 道具名漂移"
                    f"({_name!r} 占席道具词表无此名,版本改名/漏并入?):"
                    f"{_item!r}")


_validate_strategy_encounter_battle_grants()


# ===== 策略首领战后发放注册表(枪在手;白名单制)=====
# 「首领节点战斗结算后世界发放」策略域:键 = 策略规范名,值 = (装备类别
# 词, 件数) 扁平二元组(单档;多档族卡出现时沿表值形状泛化先例扩序列,
# 本批不预泛化——首例触发器形状单一)。触发面 = boss 节点战斗结算(节点
# 类型条件内嵌于触发函数,表不设节点键——扩形状各建各表,设计
# designs/T-105-yizhan-yangzhan.md §2.1 口径);发放物 = 随机装备(类别
# 池采样),与 STRATEGY_ENCOUNTER_BATTLE_GRANTS(占席道具确定发放)形状
# 异构故不共表。卡面无「胜利」限定 = 败局存活也发、无「首次」限定 =
# 可重复(无 done 闩,防重归调用方节点键幂等守卫);live 零写观察覆盖
# (装备入栏有画面真值可读,实机局不接本通道)。
# 消费面 = kernel/cw_gain_chain.check_strategy_boss_battle_grants(触发
# 检查单一源,唯一调用点 = sim 结算腿)。
STRATEGY_BOSS_BATTLE_GRANTS: dict[str, tuple[str, int]] = {
    # 每次 boss 节点战斗结算后 1 件随机简易装备(枪在手 id 200501 原文
    # 直读,cw_invest_data.PLAZA_AUGMENTS 同 id 行;同卡「立刻获得」即时
    # 腿 = cw_gain_effects._STRATEGY_RANDOM_EQUIP_GRANTS 泛化表行,两腿
    # 触发时点异构分表)
    '枪在手': ('简易', 1),
    # 枪在手+(id 200502)战后腿「首领战后,获得1件随机简易装备」与模式卡
    # 逐字同句直读行;同卡即时腿「立刻获得2件」= 泛化表行(count=2 放回)。
    # 两卡同持各自独立发放(触发函数逐持卡查表零跨卡判重,流键节点粒度
    # 共享——T-166 批前瞻注记的首个扩卡实成员,零改键)。
    '枪在手+': ('简易', 1),
}


def _validate_strategy_boss_battle_grants() -> None:
    """STRATEGY_BOSS_BATTLE_GRANTS 构建校验(import 即炸;治理口径 =
    用户裁定 2026-10-28「只能由写表人笔误触发的校验删,能被游戏版本变更
    独立触发的漂移哨留」,同 _validate_strategy_encounter_battle_grants
    docstring——本表只落孤儿键一哨):

    孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后静默
    失联)。类别词/件数为手抄常量,纯笔误类按治理裁定不加值形/件数查;
    类别池随注册表传导,池空属数据面事故非本表职责(泛化表族既定裁定),
    运行期走触发函数 log 防御分支零写兜底,对账归表域测试。"""
    orphans = [n for n in STRATEGY_BOSS_BATTLE_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_BOSS_BATTLE_GRANTS 孤儿键(base 无此卡?):"
            f"{sorted(orphans)}")


_validate_strategy_boss_battle_grants()


# ===== 策略卡羁绊条件战后发放注册表(不要小看我们的羁绊;白名单制)=====
# 「激活 N 个羁绊并完成一场战斗后,进入节点时获得 M 个随机 X 装备」策略域
# 首例:键 = 策略规范名,值 = (羁绊激活数阈值, 装备类别词, 件数) 扁平三元
# 组(单档;多档族卡出现时沿表值形状泛化先例扩序列,本批不预泛化——首例
# 触发器形状单一)。触发-发放两拍制:结算拍评估「持卡 ∧ 战斗完成 ∧ 激活
# 羁绊数 ≥ 阈值」写武装标记,节点窗拍武装在场即采样发放——desc「进入节点
# 时获得」= 发放时点在下一节点窗开非结算拍,与既有战后腿(结算拍直发)
# 形状异构故不共表(扩形状各建各表,STRATEGY_ENCOUNTER_BATTLE_GRANTS 同
# 款纪律);频次 = 可重复无 done 闩(卡面无「首次」限定,战后触发族直读
# 一致:每有一场合格战斗,其下一节点窗交付 1 次)。武装标记 = GameState
# 场字段 strategy_bond_battle_armed(两拍间唯一状态载体)。
# 消费面 = kernel/cw_gain_chain.check_strategy_bond_battle_grants(结算拍
# 武装)/ discharge_strategy_bond_battle_grants(节点窗拍交付)两枚触发
# 函数(唯一调用点 = sim 结算腿与节点窗收口腿;live 零写观察覆盖——装备
# 入栏有画面真值可读,实机局不接本通道)。
STRATEGY_BOND_BATTLE_GRANTS: dict[str, tuple[int, str, int]] = {
    # 激活8个羁绊并完成一场战斗后,进入节点时获得5个随机星徽
    # (id 200901 原文直读,cw_invest_data.PLAZA_AUGMENTS 同 id 行;
    # 数值两枚为卡面明写常量,非 desc 未写明的猜测建模)
    '不要小看我们的羁绊': (8, '星徽', 5),
}


def _validate_strategy_bond_battle_grants() -> None:
    """STRATEGY_BOND_BATTLE_GRANTS 构建校验(import 即炸;治理口径 =
    用户裁定 2026-10-28「只能由写表人笔误触发的校验删,能被游戏版本变更
    独立触发的漂移哨留」,同 _validate_strategy_boss_battle_grants
    docstring——本表只落孤儿键一哨):

    孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后静默
    失联)。阈值/类别词/件数为手抄常量,纯笔误类按治理裁定不加值形查;
    类别池随注册表传导,池空属数据面事故非本表职责(泛化随机装备族既定
    裁定),运行期走触发函数 log 防御分支零写兜底,对账归表域测试。"""
    orphans = [n for n in STRATEGY_BOND_BATTLE_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_BOND_BATTLE_GRANTS 孤儿键(base 无此卡?):"
            f"{sorted(orphans)}")


_validate_strategy_bond_battle_grants()


# ===== 策略卡胜利结算条件金注册表(招财狗;白名单制)=====
# 「战斗胜利后，若未损失小队生命值，则每有一个佩佩就会为你提供1金币」
# 策略域首例:键 = 策略规范名,值 = 每佩佩金数。表外策略一律无条目,
# 禁从效果原文自动猜装(STRATEGY_ENCOUNTER_BATTLE_GRANTS 同款纪律)。
# 与 STRATEGY_ECONOMY instant_gold 的语义边界:那条 = 获得时点一次性
# 金,本表 = 战斗结算条件可重复金(每战斗结算重查,无 done 闩;防重
# 归调用方节点键幂等守卫)。佩佩召唤腿「获得一个佩佩」归 cw_gain_effects
# 具名角色发放名单在册,不入本表。
# 消费面 = kernel/cw_gain_chain.check_strategy_win_gold_grants(触发
# 检查单一源,唯一调用点 = sim 结算腿;live 零写观察覆盖——金由游戏
# 侧自发入账,下一结算屏金真值覆盖自动吸收,实机局不接本通道)。
STRATEGY_WIN_GOLD_GRANTS: dict[str, int] = {
    # 招财狗(id 103501 原文直读,cw_invest_data.PLAZA_AUGMENTS 同 id
    # 行;卡面两数值明写:每佩佩 1 金)
    '招财狗': 1,
}


def _validate_strategy_win_gold_grants() -> None:
    """STRATEGY_WIN_GOLD_GRANTS 构建校验(import 即炸;治理口径 =
    用户裁定 2026-10-28「只能由写表人笔误触发的校验删,能被游戏版本
    变更独立触发的漂移哨留」,同 _validate_strategy_encounter_battle_
    grants docstring——本表只落孤儿键一哨):

    孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后静默
    失联)。每佩佩金数为手抄常量,纯笔误类(游戏版本变更不可能独立
    触发),值域校验按治理裁定不加。
    """
    orphans = [n for n in STRATEGY_WIN_GOLD_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_WIN_GOLD_GRANTS 孤儿键(base 无此卡?):"
            f"{sorted(orphans)}")


_validate_strategy_win_gold_grants()


#: 胜利结算条件金触发域假设披露键(desc 未写明处的申报,消费 = sim
#: 随局披露面 disclosures setdefault):desc「战斗胜利后」未限定节点
#: 类型,建模 v0 = 全部结算节点(含奖励关/扑满关)——奖励关恒胜白拿
#: 即发,扑满败局(won=False ∧ hp_delta=0)由双判据短路不发;实机
#: 持卡局奖励关/扑满关结算屏金收入对照可校准,差额暴露归本键。常量
#: 落位沿 ENV_REROLL_ASSUMPTION_POOL 先例(kernel 注册表模块)。
STRATEGY_WIN_GOLD_SCOPE_ASSUMPTION: str = \
    'strategy_win_gold_scope_all_settlement_nodes'

#: 策略延时发放随机 choice-set 行的均匀 v0 假设申报键(家族常量,后继
#: 随机发放行随批扩元组,形态沿 ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS
#: 先例;消费面 = 实测校准与披露清单):desc 对「或」无概率载,红/蓝
#: 各半为建模假设非游戏真值,禁猜数值;实机分布对照发现显著偏离 →
#: 升级采集批校准,禁改码硬凑。首例 = 是钻石总会发光。
STRATEGY_DELAYED_RANDOM_CHOICE_ASSUMPTION_KEYS: tuple[str, ...] = (
    'strategy_delayed_choice_uniform_v0',
)


# ===== 策略卡延时发放注册表(白名单制;策略延时世界发放通道模式件,
# ===== 人才激励首例——双腿卡:即时装备腿走 PICK_INVEST_EFFECTS 工厂
# ===== 即时支,延时腿经本表入倒计时队列)=====

@dataclass(frozen=True)
class StrategyDelayedGrant:
    """策略卡「N个节点后,获得发放物」登记结构(策略延时发放通道专属
    登记表;字段语义 = 卡面效果原文直读):

    - delay_nodes: 延时节拍(「4个节点后」直读);到点窗 = 拿卡节点的
      第 N 个后继节点窗(计数起点语义与效果账本「后继 N 节点」口径、
      StrategyDelayedOffer 计数读法同族,desc 未写明计数起点处不实机查);
    - item: 发放物名。分道判据:∈ EQUIPMENTS → 装备腿 gain_equipment;
      ∈ BENCH_ITEM_NAMES → 占席道具腿 gain_bench_item(消费原语内逐次
      查两词表,零新词表)。员工投影仪不入 BENCH_ITEM_NAMES:该词表
      只从两张 GiftGrant 表派生,装备名并入即被误判占席道具(溢出腿
      假道具),本表并列新表、不接入派生。
    - count: 单次入队条目数(「获得N个」直读,先亏后盈 2 = 族内首例
      >1)。数量单一源落注册表:登记效果体按 count 循环逐条调用入队
      原语(同拍 2 条队列条目,到点逐条独立发放/独立席满判定);
      default 1 使既有行纸面与行为零变。数量不入 import 校验(2026-10-28
      治理口径「防登记笔误校验不加」,同 delay_nodes 值形查),对账归
      表域测试与评审。
    - item_choices: 随机发放物封闭集合(「获得【红钻】或【蓝钻】」直读,
      是钻石总会发光首例)。空 () = 确定发放行,发放物走 item 字段,既有
      全部行纸面与行为零变;非空 = 到点发放时在集合内均匀掷一枚(掷骰
      时点 = 到点发放窗,队列仍只存卡名随机值不入队;均匀 v0 = 建模
      假设非游戏真值,desc 无概率载禁猜数值,披露键申报
      STRATEGY_DELAYED_RANDOM_CHOICE_ASSUMPTION_KEYS)。与 item 恰一
      有效(防登记笔误类,按 2026-10-28 治理口径不入 import 校验,对账
      归表域测试);元素各过漂移哨(逐元素 ∈ EQUIPMENTS ∪
      BENCH_ITEM_NAMES,版本改名/移除可独立触发,见
      _validate_strategy_delayed_grants ④)。
    - item_category: 随机发放物类别池(「获得1件随机简易装备」直读,回收
      计划首例)。空串 = 非池形行,既有全部行纸面与行为零变;非空 = 到点
      发放时在 ``equips_by_category(本值)`` 注册表派生池内均匀掷一枚
      (掷骰时点 = 到点发放窗现掷,队列同样只存卡名随机值不入队;均匀 v0
      = 建模假设,池形分布与泛化随机装备族同一,家族披露键
      STRATEGY_RANDOM_EQUIP_ASSUMPTION_KEYS 类别无关单键承载,零新增键;
      词表单一源 = Equipment.category 字段注释,池随注册表传导,漂移哨
      见 _validate_strategy_delayed_grants ⑤)。与 item/item_choices
      三选一登记(防登记笔误类同治理口径不入 import 校验,三方恰一对账
      归表域测试)。

    立专表辨析:GiftGrant items_scheduled = 绝对节点键域('位-轮')且
    会把发放物错收进占席词表;效果账本 EffectSpec payload 闭集(经济/
    战场/单位增益)不容「延时世界发放」维度;与 STRATEGY_DELAYED_OFFERS
    消费形态不同(世界发放写 vs 选卡屏事件)不合并——新维度
    (倒计时 + 具名发放物)专属专表。"""
    id: str
    delay_nodes: int
    item: str
    count: int = 1
    item_choices: tuple[str, ...] = ()
    item_category: str = ''


STRATEGY_DELAYED_GRANTS: dict[str, StrategyDelayedGrant] = {
    # 人才激励(效果原文「获得1个【员工投影仪】，4个节点后，获得1个
    # 【员工投影仪】。」直读;效果原文对账 id = cw_invest_data
    # .PLAZA_AUGMENTS 同 id 行;即时腿「获得1个【员工投影仪】」由
    # PICK_INVEST_EFFECTS 工厂同批注册,不入本表)。同族展开卡各自
    # 独立批领取,禁顺手代登记——池内被选中的未注册卡 = 安静不写,
    # 真值归观察覆盖
    '人才激励': StrategyDelayedGrant(id='101601', delay_nodes=4,
                                      item='员工投影仪'),
    # 人才激励+(id 101602 原文直读,cw_invest_data.py:55;与姊妹卡
    # 唯一差异 = 倒计时 4→3,卡面「3个节点后」)
    '人才激励+': StrategyDelayedGrant(id='101602', delay_nodes=3,
                                       item='员工投影仪'),
    # 许诺特权(id 130201 原文直读,cw_invest_data.py:87;卡文
    # 「在进入7个节点后，获得1个【特权武装箱】。」纯延时单句——
    # 零即时腿,故登记腿载体 = cw_gain_effects 延时-only 单腿工厂,
    # 禁走两腿工厂派生;发放物特权武装箱 = 占席道具,BENCH_ITEM_NAMES
    # 分道的族内首个实成员,到点走 gain_bench_item)
    '许诺特权': StrategyDelayedGrant(id='130201', delay_nodes=7,
                                      item='特权武装箱'),
    # 先亏后盈(id 130701 原文直读,cw_invest_data.py:92;卡文延时腿 =
    # 「4个节点后获得2个【简易武装箱】」,数量 2 = 族内首例 >1,承载见
    # count 字段;伴随损血腿「损失20点小队生命值」另走 STRATEGY_ECONOMY
    # hp 通道(hp_instant=-20),不入本表——两腿分道,同卡双通道登记)
    '先亏后盈': StrategyDelayedGrant(id='130701', delay_nodes=4,
                                      item='简易武装箱', count=2),
    # 好运令牌·银(id 130901 原文直读,cw_invest_data.py:94;卡文
    # 「进入3个节点后，获得1个【好运令牌】。」纯延时单句——零即时腿,
    # 登记腿载体 = cw_gain_effects 延时-only 单腿工厂,禁走两腿工厂
    # 派生;发放物「好运令牌」与卡名异名(族内首例),= EQUIPMENTS
    # 注册表工具类装备(cw_equipment_data.py:192),非占席道具
    # (BENCH_ITEM_NAMES 负成员,禁入占席通道),到点走装备分道
    # gain_equipment;获得时点零级联(∉ EQUIP_ACQUIRE_CONSEQUENCES))
    '好运令牌·银': StrategyDelayedGrant(id='130901', delay_nodes=3,
                                        item='好运令牌'),
    # 是钻石总会发光(id 131101 原文直读,cw_invest_data.py:96;卡文
    # 「2个节点后，获得【红钻】或【蓝钻】。」纯延时单句零即时腿,登记腿
    # 载体 = cw_gain_effects 延时-only 单腿工厂;发放物 = 红钻/蓝钻具名
    # 二元封闭集(族内首个随机发放行,item='' 占位走 item_choices,掷骰
    # 时点 = 到点发放窗现掷,队列只存卡名随机值不入队);非类别池——
    # 「特殊」类全类 17 件,财富宝钻/分身墨镜等 15 件非集合成员,池形
    # 不适配;红钻/蓝钻 = EQUIPMENTS 特殊类装备非占席道具(BENCH_ITEM_
    # NAMES 负成员,禁入占席通道),到点走装备分道 gain_equipment;
    # 获得时点零级联(∉ EQUIP_ACQUIRE_CONSEQUENCES);概率红/蓝均匀 v0
    # = 建模假设,披露键申报)
    '是钻石总会发光': StrategyDelayedGrant(
        id='131101', delay_nodes=2, item='',
        item_choices=('红钻', '蓝钻')),
    # 回收计划(id 230701 原文直读,cw_invest_data.py:185;卡文延时腿 =
    # 「并在5个节点后获得1件随机简易装备」→ 类别池形(item_category
    # 族首例,item='' 占位,简易 8 件全集即目标全集,掷骰时点 = 到点
    # 发放窗现掷,队列只存卡名随机值不入队)。同卡即时腿「获得1件进阶
    # 装备」不在本表——两腿同属选卡获得时点,登记腿 = PICK_INVEST_
    # EFFECTS 组合登记行(随机进阶腿×延时入队腿,cw_gain_effects,不入
    # 泛化表防同名键覆盖丢即时腿);「随机」词在本腿显式,即时腿进阶
    # 装备缺词判读申报制(随机类别池均匀 v0 读法 =
    # designs/T-237-huishou-jihua.md §1.3,后继引用禁当定谳转引))
    '回收计划': StrategyDelayedGrant(id='230701', delay_nodes=5, item='',
                                     item_category='简易'),
    # 回收计划+(id 230702 原文直读,cw_invest_data.py:186;卡文延时腿 =
    # 「并在4个节点后获得1件随机简易装备」→ 类别池形第 2 例(item=
    # 占位,简易池到点现掷;即时腿「获得1件进阶装备」不在本表——
    # PICK_INVEST_EFFECTS 组合登记行承载,判读申报制随 T-237 在案口径))
    '回收计划+': StrategyDelayedGrant(id='230702', delay_nodes=4, item='',
                                     item_category='简易'),
    # 红钻闪耀(id 231201 原文直读,cw_invest_data.py:192;卡文延时腿 =
    # 「进入3个节点后，获得【简易武装箱】」→ 定名道具直填形(item 直填
    # count 缺省 1;即时腿「获得1个【红钻】」不在本表——PICK_INVEST_
    # EFFECTS 组合登记行承载,两腿异构不入泛化表防撞键);到点 BENCH
    # 分道 gain_bench_item(rand=False),四查 BENCH 分支过)。
    '红钻闪耀': StrategyDelayedGrant(id='231201', delay_nodes=3, item='简易武装箱'),
    # 蓝钻闪耀(id 231301 原文直读,cw_invest_data.py:193;卡文延时腿 =
    # 「进入3个节点后，获得【简易武装箱】」→ 定名道具直填形(item 直填
    # count 缺省 1;即时腿「获得1个【蓝钻】」不在本表——PICK_INVEST_
    # EFFECTS 组合登记行承载,两腿异构不入泛化表防撞键);到点 BENCH
    # 分道 gain_bench_item(rand=False),四查 BENCH 分支过)。
    '蓝钻闪耀': StrategyDelayedGrant(id='231301', delay_nodes=3, item='简易武装箱'),
}


def _validate_strategy_delayed_grants() -> None:
    """STRATEGY_DELAYED_GRANTS 构建校验(import 即炸;治理口径 =
    2026-10-28 裁定「只能由写表人笔误触发的校验删,能被游戏版本变更
    独立触发的漂移哨留」,镜像 _validate_strategy_delayed_offers 同款
    收缩形态——本表落五哨,值域类(delay_nodes 形/下界)与防登记笔误
    类(item 与 item_choices 恰一)不加,恰一对账归表域测试):

    ① 孤儿键:键必须在 INVESTMENT_STRATEGIES(防版本更新改名/移除后
    静默失联);② id 双匹配:登记 id 必须等于 base 溯源 id(改名且 id
    仍在的漂移也炸);③ 发放物名漂移:item 非空的确定行 ∈ EQUIPMENTS ∪
    BENCH_ITEM_NAMES(两词表均游戏数据派生,版本改名/移除可独立触发;
    双域皆非 = 消耗品域/未知名,发放腿无从分道;choice-set 行 item=''
    跳过本哨,物名由④逐元素辖);④ choice-set 元素漂移:非空
    item_choices 逐元素 ∈ EQUIPMENTS ∪ BENCH_ITEM_NAMES(镜像③形态,
    采样行发放腿同按两词表分道);⑤ 类别池漂移:非空 item_category 的
    类别池 equips_by_category 非空(值 ∈ 装备类别词表的派生承载——池 =
    注册表 category 等值过滤,词表成员资格与池非空充要,词表单一源 =
    Equipment.category 字段注释,镜像 _validate_strategy_hp_loss_grants
    ②同形;池空的运行期实况 = 发放腿类别池查空防御 log + 条目保留,
    import 期哨把拦截面前移到构建期)。③④的运行期实况 = 发放腿查行后零
    分道防御(log + 条目保留),import 期哨把拦截面前移到构建期。
    delay_nodes 错值后果 = 拿卡入队按错拍倒计时(响亮面在对账),防
    笔误类按治理裁定不加。
    """
    orphans = [n for n in STRATEGY_DELAYED_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_DELAYED_GRANTS 孤儿键(base 无此卡?):{sorted(orphans)}")
    for _name, _grant in STRATEGY_DELAYED_GRANTS.items():
        _base = INVESTMENT_STRATEGIES.get(_name)
        if _base is not None and _base.source != f'plaza:{_grant.id}':
            raise ValueError(
                f"STRATEGY_DELAYED_GRANTS id 漂移:{_name!r} 登记 id="
                f"{_grant.id} base={_base.source}")
        if _grant.item \
                and _grant.item not in EQUIPMENTS \
                and _grant.item not in BENCH_ITEM_NAMES:
            raise ValueError(
                f"STRATEGY_DELAYED_GRANTS 发放物名漂移({_name!r} 装备表/占席"
                f"词表均无此名,版本改名?):{_grant.item!r}")
        for _choice in _grant.item_choices:
            if _choice not in EQUIPMENTS and _choice not in BENCH_ITEM_NAMES:
                raise ValueError(
                    f"STRATEGY_DELAYED_GRANTS 发放物元素漂移({_name!r} "
                    f"choice-set 装备表/占席词表均无此名,版本改名?):"
                    f"{_choice!r}")
        if _grant.item_category \
                and not equips_by_category(_grant.item_category):
            raise ValueError(
                f"STRATEGY_DELAYED_GRANTS 类别漂移({_name!r} 类别池注册表"
                f"无装备,版本改名?):{_grant.item_category!r}")


_validate_strategy_delayed_grants()


# ===== 策略卡购买翻星登记表(白名单制;购买触发翻星族「购买的下1个
# ===== X费角色立刻升到N星」首例)=====
# 翻转判定单一源;消费端 = kernel/cw_gain_chain.check_strategy_buy_star_
# flip(纯谓词,买牌上报链落位星级判定消费——Unit 构造位翻星/applied 后
# 置闩两处接线,翻转不改 payload 移除匹配与 on_buy 回调的购买原星)。
# 表外卡一律无条目,禁从效果原文自动猜装(STRATEGY_FIRST_BUY_XP_GRANTS
# 同款纪律);同族后续「购买下1个X费升星」类卡按「注册行直用本通道」
# 接入(姊妹卡着眼当下全档枚举行共用本表,值形迁移归其实现批对表)。
# 一次性闩 = strategy_conditional_done 纯卡名键(「下1个」= 下一次购买
# 事件语义封账;首购经验的复合键是费用粒度五桶扩展,本族无桶面不沿用)。
# 时序口径 = 翻星在落位时生效、先于合成级联(卡面「立刻」字面 + 发牌
# 2★ 直出同构先例;家族判读申报制承载非定谳——后继族稿引用须现值重核,
# 实机采证路径 = 持同名高星件购买观察落席星级)。

STRATEGY_BUY_STAR_FLIP_GRANTS: dict[str, tuple[int, int]] = {
    # 四费晋升:官方「你购买的下1个4费角色将立刻升到2星。获得12金币。」
    # (id 202201 原文直读,cw_invest_data.PLAZA_AUGMENTS 同 id 行;费用
    # 过滤档 4/目标星级 2 两维全卡面明写,零披露键;同卡金腿「获得12金
    # 币」归 STRATEGY_ECONOMY instant_gold 在册,不进本表)
    '四费晋升': (4, 2),
}


def _validate_strategy_buy_star_flip_grants() -> None:
    """STRATEGY_BUY_STAR_FLIP_GRANTS 构建校验(import 即炸;治理口径 =
    用户裁定 2026-10-28「只能由写表人笔误触发的校验删,能被游戏版本变更
    独立触发的漂移哨留」,同 _validate_strategy_win_gold_grants
    docstring——本表只落孤儿键一哨):

    孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后静默
    失联)。费用档/目标星级系卡面手抄常量,游戏数值改版只改「正确值」,
    正确转录值恒在域内(哨不响),纯笔误类值域查按治理裁定不加,对账归
    评审与本表域测试把关(行值精确断言 + id 对拍,防线强于 import 期
    形查);顾问型跨表双登记互斥(STRATEGY_GRANTS 顾问行)同属防呆类
    同判不加——手工注册表版本变更不可能自动产生冲突行。
    """
    orphans = [n for n in STRATEGY_BUY_STAR_FLIP_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_BUY_STAR_FLIP_GRANTS 孤儿键(base 无此卡?):"
            f"{sorted(orphans)}")


_validate_strategy_buy_star_flip_grants()


# ===== 策略卡空仓经验登记表(白名单制;「进入新节点时，如果物品栏和备战
# ===== 席没有任何装备(消耗品除外)，则获得N经验值」节点条件 XP 族首例)=====
# 判定单一源;消费端 = kernel/cw_gain_chain.check_strategy_empty_equip_xp
# (纯读零写零 rng,世界写端 = sim 节点窗挂点唯一调用口;零 done 闩——卡面
# 无「首次」限定,每节点窗可重复,幂等归窗口守卫)。表外卡一律无条目,禁从
# 效果原文自动猜装(STRATEGY_FIRST_BUY_XP_GRANTS 同款纪律);同族后继卡
# (姊妹展开/同触发面族)按「注册行直用本通道」接入(消耗品判据词表 =
# data 层 CONSUMABLE_EQUIP_CATEGORIES,判据面 import,禁本地平行定义)。

STRATEGY_EMPTY_EQUIP_XP_GRANTS: dict[str, int] = {
    # 空仓:官方「进入新节点时，如果物品栏和备战席没有任何装备(消耗品
    # 除外)，则获得2经验值。」(id 202401 原文直读,cw_invest_data
    # .PLAZA_AUGMENTS 同 id 行;值 = 每满足一次发放的 XP 量,卡面明写;
    # 即时腿「获得1件随机的简易装备」归 cw_gain_effects 随机装备族泛化表,
    # 不入本表)
    '空仓': 2,
    '空仓+': 2,
}


def _validate_strategy_empty_equip_xp_grants() -> None:
    """STRATEGY_EMPTY_EQUIP_XP_GRANTS 构建校验(import 即炸;治理口径 =
    用户裁定 2026-10-28「只能由写表人笔误触发的校验删,能被游戏版本变更
    独立触发的漂移哨留」,同 _validate_strategy_buy_star_flip_grants
    docstring——本表只落孤儿键一哨):

    孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后静默
    失联)。XP 量系卡面手抄常量,游戏数值改版只改「正确值」,正确转录值
    恒为正 int(哨不响),纯笔误类值形查按治理裁定不加,对账归本表域测试
    把关(行值精确断言 + id 对拍,防线强于 import 期形查)。"""
    orphans = [n for n in STRATEGY_EMPTY_EQUIP_XP_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_EMPTY_EQUIP_XP_GRANTS 孤儿键(base 无此卡?):"
            f"{sorted(orphans)}")


_validate_strategy_empty_equip_xp_grants()


# ===== 策略卡备战席计数经验登记表(白名单制;「节点开始时，如果备战席角色
# ===== 小于等于/大于等于N名，则获得N经验值」节点条件 XP 族)=====
# 判定单一源;消费端 = kernel/cw_gain_chain.check_strategy_bench_count_xp
# (纯读零写零 rng,世界写端 = sim 节点窗挂点唯一调用口;零 done 闩——卡面
# 无「首次」限定,每节点窗可重复,幂等归窗口守卫)。表外卡一律无条目,禁从
# 效果原文自动猜装(STRATEGY_FIRST_BUY_XP_GRANTS 同款纪律);同族后继卡按
# 「注册行直用本通道」接入(姊妹人才济济 202701 已接入,见下)。

STRATEGY_BENCH_COUNT_XP_GRANTS: dict[str, tuple[str, int, int]] = {
    # 人才空洞:官方「节点开始时，如果备战席角色小于等于4名，则获得3经验。」
    # (id 202601 原文直读,cw_invest_data.PLAZA_AUGMENTS 同 id 行);值 =
    # (比较符, 备战席单位数门槛, 每满足一次发放的 XP 量),数值全 desc 明写;
    # 计数口径 = bench_units_of 仅单位槽(占位件与空槽不计,desc「角色」
    # 文义直读 + 读口 docstring 语义,判读申报制非定谳);比较符闭集 =
    # {'le'(≤), 'ge'(≥)}。
    '人才空洞': ('le', 4, 3),
    # 人才济济:官方「节点开始时，如果备战席角色大于等于8名，则获得3经验。」
    # (id 202701 原文直读,同上机制);门槛 8 ≤ 现役容量 9,条件可达。
    '人才济济': ('ge', 8, 3),
}


def _validate_strategy_bench_count_xp_grants() -> None:
    """STRATEGY_BENCH_COUNT_XP_GRANTS 构建校验(import 即炸;治理口径 =
    用户裁定 2026-10-28「只能由写表人笔误触发的校验删,能被游戏版本变更
    独立触发的漂移哨留」,同 _validate_strategy_empty_equip_xp_grants
    docstring——本表只落孤儿键一哨):

    孤儿键:键必须在 INVESTMENT_STRATEGIES(版本更新改名/移除后静默
    失联)。比较符/门槛/XP 量系卡面手抄常量,游戏数值改版只改「正确值」,
    正确转录值恒在域内(哨不响),纯笔误类值形/值域查按治理裁定不加,对账
    归本表域测试把关(行值精确断言 + id 对拍,防线强于 import 期形查)。"""
    orphans = [n for n in STRATEGY_BENCH_COUNT_XP_GRANTS
               if n not in INVESTMENT_STRATEGIES]
    if orphans:
        raise ValueError(
            f"STRATEGY_BENCH_COUNT_XP_GRANTS 孤儿键(base 无此卡?):"
            f"{sorted(orphans)}")


_validate_strategy_bench_count_xp_grants()
