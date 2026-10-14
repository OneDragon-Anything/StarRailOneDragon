"""策略卡经济通道金等价折算(mandate_v1 共用模块;投资策略屏现金分承载面)。

设计正本 = strategy-docs/29_invest_strategy_screen.md §2.1(下称
「29 号稿」);复用契约形态与折算约定沿 env 批
env_economy.py——``(值, resolved)`` 返回、fail-closed 门、
:data:`XP_GOLD_RATE` 语义同源,但**通道公式分立**:
``EnvEconomyEffect``(整局规则改写)与本模块消费的 ``EconomyEffect``
(per-node/一次性流)字段空间不同构,公式不可共享(29 号稿 §2.1)。

归属(宪法五:框架层只留游戏原始真值,衍生估值归策略层):kernel 侧只留
游戏原始真值 ``cw_investments.STRATEGY_ECONOMY``(通道结构 = 游戏效果
原文的结构化,【注】);本模块承载策略层的金等价折算。

职责:策略卡可数值化经济通道折成**金等价期望** ``(expected_gold,
resolved)``——resolved=False = fail-closed(缺参/日程不可得/位置缺失帧
之外的异常形态),消费端按无现金处理(invest_strategy 组件组装处统一
``resolved ∧ expected_gold > 0`` 才计,半值禁出)。

**剩余口径**(沿 env_economy 同形态):从 gs 当前节点起算到局终——开局
取卡帧 = 全局期望,局内重发帧 = 剩余期望,同一函数自然覆盖。

**剩余节点数自算单一源**(宪法二查表键合法形态;框架不向
策略供视界量,序列模块只留键原语):长度唯一真值源 = GameState 场字段
``node_seq_by_plane``(修饰局 10/8、默认局 9/7;None = 未注册态回退默认
表),自算消费符号单一源 = 策略门面 ``statefn/horizon.r_remaining``/
``r_global``(本模块零新写视界实现);视界封顶 modeled planes(场字段
键集 = P1+P2,P3 = 建模域外 = 运行终局,不可达轮不计;行为申报 = 迭代
abolish-node-ordinal details/horizon-cleanup.md §8)。**口径偏差申报**
(29 号稿 §2.1 原文申报,如实保留):``r_global`` 含当前节点,而「进入
新节点给金/XP」类通道语义不含已进入的当前节点——原样消费 = per-node
通道系统性 +1 节点偏差(同向偏高,量级 ≤ 单节点流值);boss 通道同族偏高
(当前节点即 boss 位时多计一笔已发放 boss 金)。取上端 = 现金分计分偏高
已知并申报(29 号稿 §2.1 口径申报行),非防低估。``total_remaining_nodes``
恒按 9/位面的旧口径(01_math_framework §5 R_全局 行登记缺陷)已随视界族
清扫修正为场字段求和——本模块仍统一经门面自算,不直引该对照量。

**待建模通道**(v1 fail-closed = 0,建模落地自动进现金分):见
:data:`STRATEGY_ECONOMY_PENDING_MODELING` 与字段分类的「待建模」集
(刷新族/时点大额族/XP 折扣族/轨迹倍率族/合成与购买触发族/血补偿族/
息 cap 覆写/升级流——分类依据与29 号稿 §2.1 逐通道对应)。

**不计分通道**(结构登记、永不为分):血本位分区辖(xp_buy_hp_cost/
hp_gold_swap,invest_strategy 结构分区辖)、难度族(难度→价值需战力
建模,宪法一禁域)、期权/远见族(均匀分布假设未证)、负向结构登记
(无正账可折)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_investments import (
    INVESTMENT_STRATEGIES,
    STRATEGY_ECONOMY,
    EconomyEffect,
    get_strategy,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    PLANE_NODE_TABLES,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.env_economy import (
    XP_GOLD_RATE,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.horizon import (
    r_global,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState

# ===== 字段分类(45 字段三分;单一源 = 三集合,构建校验兜底)=====
# 分类判据与29 号稿 §2.1 逐通道对应:「计分」= v1 落地通道公式可算;
# 「待建模」= 有字段腿但价值模型缺(fail-closed = 0,建模落地自动进);
# 「不计」= 结构登记永不为分。字段分类校验辖「有字段腿」;卡级登记
# (PENDING_MODELING)辖「无字段腿 ∪ 字段在册未挂值腿」,两适用范围不重叠。

#: 计分通道字段(v1 公式直算,值全 = 注册表游戏定义【注】直读):
#: - instant_gold:选卡当场一次性金(面值);
#: - gold_next_nodes_amount/count:「现在及接下来 count 次」分期金配对
#:   字段——**配对 count 半字段同入计分类**(消费公式两半齐用,分类粒度
#:   = 字段,半字段缺席即分类校验炸出);
#: - gold_per_node / gold_per_boss_node / interest_flat_per_node:
#:   per-node 流(息上调整数腿金等价直读);
#: - xp_per_node / xp_instant:XP 通道(× XP_GOLD_RATE 折算)。
_CASH_SCORED_FIELDS: frozenset[str] = frozenset({
    'instant_gold',
    'gold_next_nodes_amount', 'gold_next_nodes_count',
    'gold_per_node', 'gold_per_boss_node', 'interest_flat_per_node',
    'xp_per_node', 'xp_instant',
})

#: 待建模通道字段(v1 fail-closed = 0;逐字段建模缺口与29 号稿 §2.1
#: 通道清单一一对应):
#: - 息 cap 覆写:interest_cap_override(金轨线依赖);
#: - 升级流:gold_per_level_up(E[剩余升级次数] = P58 期望等级日程,
#:   草案/证明骨架未证,处置规则 A 禁数值实现——P58 证明完成为解封条件);
#: - 时点大额族:gold_at_node/gold_at_node_offset(超发货币型,正腿条件
#:   兑现概率未建模且负腿 = 清空持有金轨迹依赖)、gold_at_level/
#:   gold_at_level_target(成长基金型,到达等级概率未建模);
#: - 刷新族:free_refresh_burst/free_refresh_per_node/refresh_surprise_
#:   every/refresh_per_compose/refresh_free_chance/refresh_shop_rewrite_
#:   every_3cost/free_refresh_cond_gold_above/step/cap(刷新机会成本模型
#:   缺,P97 预算只证可达性不证单次价值);
#: - XP 通道:xp_per_refresh(刷新 XP 收入的价值缺金值口径)、
#:   xp_buy_cost_discount/xp_click_discount_from_level/_at(P22 占优方向
#:   在册但金值未立);
#: - 轨迹依赖:win_reward_mult/sell_price_mult;
#: - 合成触发族:gold_per_2star2cost_merge/gold_per_3star_merge(频次
#:   分布未采);
#: - 购买触发族:gold_per_three_5cost(每购买 3 个 5 费给金,非合成;
#:   购买频次分布未采);
#: - 血补偿族:gold_per_20hp_lost(未来损血期望未采,且未来建模同样触发
#:   宪法三 hp 消费硬闸门)、gold_per_hp_lost_now(价值 = f(已损血),
#:   宪法三硬闸门外第三消费点须用户逐项确认,未确认期 fail-closed = 0)。
_PENDING_MODELING_FIELDS: frozenset[str] = frozenset({
    'interest_cap_override',
    'gold_per_level_up',
    'gold_at_node', 'gold_at_node_offset',
    'gold_at_level', 'gold_at_level_target',
    'free_refresh_burst', 'free_refresh_per_node',
    'refresh_surprise_every', 'refresh_per_compose',
    'refresh_free_chance', 'refresh_shop_rewrite_every_3cost',
    'free_refresh_cond_gold_above', 'free_refresh_cond_gold_step',
    'free_refresh_cond_cap',
    'xp_per_refresh', 'xp_buy_cost_discount',
    'xp_click_discount_from_level', 'xp_click_discount_from_level_at',
    'win_reward_mult', 'sell_price_mult',
    'gold_per_2star2cost_merge', 'gold_per_3star_merge',
    'gold_per_three_5cost',
    'gold_per_20hp_lost', 'gold_per_hp_lost_now',
})

#: 不计分通道字段(结构登记、永不为分):
#: - 血本位分区辖:xp_buy_hp_cost/hp_gold_swap(invest_strategy 血本位
#:   三态序以 is_blood_economy 集合排除辖,价值面不入现金账);
#: - 难度族:difficulty_delta/difficulty_per_streak/difficulty_node_types
#:   (难度→价值需战力建模,宪法一禁域);
#: - 期权/远见族:future_quality_upgrade/difficulty_inflation_exempt
#:   (远见品质改写 = 期权待建模,均匀分布假设未证);
#: - 负向结构登记:xp_click_surcharge_from_level/_at、hp_max_loss_pct_of_
#:   loss/hp_max_loss_cap_pct(无正账可折)。
_NOT_SCORED_FIELDS: frozenset[str] = frozenset({
    'xp_buy_hp_cost', 'hp_gold_swap',
    'difficulty_delta', 'difficulty_per_streak', 'difficulty_node_types',
    'future_quality_upgrade', 'difficulty_inflation_exempt',
    'xp_click_surcharge_from_level', 'xp_click_surcharge_from_level_at',
    'hp_max_loss_pct_of_loss', 'hp_max_loss_cap_pct',
})

# ===== 「待建模」卡级在册(键 = 注册表规范卡名,值 = 未建模腿清单描述)=====
# **卡级登记适用范围 = 无字段腿 ∪ 字段在册未挂值腿**(区别于字段分类校验的
# 「有字段腿」适用范围):字段分类校验只扫 EconomyEffect 已挂值条目,扫不到
# 「字段在册但条目未挂值」(如固定理财系 xp_instant 在字段闭集里而条目
# 缺省)与「无字段腿」(效果结构在注册表无对应字段),唯卡级登记辖得住。
# 在册行辖未建模腿的**可见性**(治理账,非运行时闸——已建模腿照常计分,
# 见 strategy_economy_value docstring);建模落地后改写对应行描述。
STRATEGY_ECONOMY_PENDING_MODELING: dict[str, str] = {
    # 固定理财系:官方「现在以及每个位面开始时,获得4/6经验值和2/3次免费
    # 刷新」——「现在」段 XP 腿字段在册未挂值 +「位面开始段」XP/刷新腿
    # 无字段(cw_investments.STRATEGY_ECONOMY 条目注释在册注明);
    # 「现在」段刷新腿 2/3 刷已挂 free_refresh_burst(归刷新族字段待建模)
    '固定理财': '「现在」段XP腿(字段在册未挂值);「位面开始段」XP腿+'
               '刷新腿(无字段);刷新腿(free_refresh_burst=2,刷新族待建模)',
    '固定理财+': '「现在」段XP腿(字段在册未挂值);「位面开始段」XP腿+'
                '刷新腿(无字段);刷新腿(free_refresh_burst=3,刷新族待建模)',
    # 孪生素数:首购计数经验腿(2/3/5/7/11——XP_GOLD_RATE 下数值与金同),
    # 字段全缺省 = 纯无字段腿( EconomyEffect(xp_instant=0) 全默认 )
    '孪生素数': '首购计数经验腿(2/3/5/7/11)无字段载体;行为条件流',
    # 狸财经狸:息腿已计(interest_flat_per_node=2);取款/存款腿无字段
    # (金<20 取 10、P3 首领取全部存款——存款累计值消费端推,行为条件流)
    '狸财经狸': '取款腿(金<20 取 10)+存款腿(P3 首领取全部存款)无字段载体;'
               '30 本金系非玩家收入语境值不进账',
    # 超发货币:gold_at_node 族字段已挂值(归时点大额族字段待建模),
    # 但「失去现有全部金」负腿无字段且方向不明——兼无字段腿在卡级在册
    '超发货币': '正腿兑现条件(5 节点后)概率未建模(gold_at_node 族字段'
               '待建模);负腿「失去现有全部金」无字段载体,方向不明',
    # —— 注册表外经济语义卡代表例(economy 未注册但 research 在册明列
    # 经济结构 = 建模待修问题形态,按无已建模机械成分 0 分申报低估;
    # invest_effects 批 3/4 在册,禁凭 research 记载凭直觉给分)——
    '被动收入': '每节点 XP = 备战席最左侧角色基础费用(量级可达 ~125 当量'
               '大于买断制现金流),无字段载体',
    '气氛组': '战斗结束按 0 伤害角色数给 XP,无字段载体',
    '气氛组+': '同气氛组 +「获得8经验」即时 XP 腿,均无字段载体',
    '存款回报': '条件免费刷新(上节点未花费 → 2 刷),无字段载体',
    '招财狗': '战斗胜利未损血 → 每佩佩 1 金(轨迹依赖:佩佩数×不败率),'
             '无字段载体',
    '免战牌': 'xp_instant=30 腿挂 STRATEGY_EFFECTS 载体(cw_investments.'
             'STRATEGY_EFFECTS 条目,不在 STRATEGY_ECONOMY 键空间;'
             '效果域文档在册)——未入现金通道',
}


# ===== 金等价折算(单一入口)=====


def strategy_economy_value(name: str, gs: GameState) -> tuple[float, bool]:
    """策略卡经济通道金等价期望(单一入口;契约沿 env_economy.env_economy_value)。

    返回 ``(expected_gold, resolved)``;resolved=False = fail-closed
    (未入册/全默认无通道/非正金期望),消费端按无现金处理。
    无 economy 条目或全默认 → (0, False)(无通道可装,非异常)。

    **卡级待建模登记不设运行时闸**:STRATEGY_ECONOMY_PENDING_MODELING
    辖「无字段腿 ∪ 字段在册未挂值腿」的可见性(治理账),已建模腿照常
    计分——狸财经狸的 interest_flat_per_node 活计分腿 × 剩余节点数照付
    (行为申报 7:计 2 金/节点流,取款/存款腿待建模塌 0);未建模字段
    天然不入下方通道公式 = 塌 0,建模落地加通道即自动进现金分。

    通道(值全部 = 注册表游戏定义【注】直读;剩余视界查表单一源 =
    策略门面 ``statefn/horizon.r_remaining``/``r_global`` 场字段自算,
    禁新写第三实现):
    - instant_gold:选卡当场一次性金,面值(**勿读 gold_next_nodes_amount
      代「现在」腿**——长期主义系「现在」腿由 amount 现值承载,误读即漏
      现在腿);
    - gold_next_nodes:「现在」腿 amount + count 节点腿 amount ×
      min(count, max(剩余节点数 − 1, 0))——「接下来」不含当前节点,按
      ``剩余节点数 − 1`` 截断(剩余节点数含当前节点,R≤count 终局帧多计
      1 腿消除);
    - gold_per_node × 剩余节点数(r_global 场字段自算,None 回退默认表);
    - gold_per_boss_node × 剩余 boss 节点数(场字段序列自当前节点(含)
      起 ``'boss'`` kind 直查;封顶 modeled planes,P3 虚拟末槽不再计入
      ——默认局 P1 段 3→2、P2 起 2→1,行为申报 details §8.3;含当前位面
      口径的偏差见模块 docstring 申报);
    - interest_flat_per_node × 剩余节点数(息上调整数腿,金等价直读);
    - xp_per_node × 剩余节点数 × XP_GOLD_RATE;
    - xp_instant × XP_GOLD_RATE。

    位置缺失帧:沿 env 屏先例退化 (1, 1) 现读(场字段/默认表读出照常)。
    """
    st = get_strategy(name)
    eff = st.economy if st is not None else None
    if eff is None or eff == EconomyEffect():
        return (0.0, False)

    node = gs.node.value
    if node is None:
        # 位置缺失帧退化 (1, 1)(沿 env 屏先例;分支行为有单测锁)
        cur_plane, cur_round = 1, 1
    else:
        cur_plane, cur_round = int(node.plane), int(node.round_num)
    remaining = r_global(gs, cur_plane, cur_round)

    acc = 0.0
    # 通道 1:选卡当场一次性金(面值;「现在」腿另由 gold_next_nodes 承载)
    if eff.instant_gold:
        acc += float(eff.instant_gold)
    # 通道 2:「现在及接下来 count 次进节点每次 amount 金」分期金
    # (长期主义系;count 腿按「剩余节点数 − 1」截断——「接下来」不含
    # 当前节点,剩余节点数含当前节点)
    if eff.gold_next_nodes_amount and eff.gold_next_nodes_count:
        _legs = min(eff.gold_next_nodes_count, max(remaining - 1, 0))
        acc += float(eff.gold_next_nodes_amount) * (1 + _legs)
    # 通道 3:每节点金流
    if eff.gold_per_node:
        acc += float(eff.gold_per_node) * remaining
    # 通道 4:每 boss 节点金(剩余 boss 数 = 场字段序列自当前节点(含)
    # 起 'boss' kind 直查——替代停用的「位面末槽 × 每位面恰一 boss」几何
    # 假设,修饰局 boss 位移与未来序列变异天然正确;封顶 modeled planes,
    # P3 虚拟末槽不再计入 → 默认局 P1 段 3→2、P2 起 2→1(行为申报
    # details §8.3);当前节点即 boss 位时多计一笔已发放 boss 金的同族
    # 偏高申报见模块 docstring)
    if eff.gold_per_boss_node:
        _seqs = gs.node_seq_by_plane.value or PLANE_NODE_TABLES
        _from = max(1, cur_round) - 1   # 自当前节点(含)起;round 缺效防御同旧 or 1 支
        _bosses = sum(
            (seq[_from:] if k == cur_plane else seq).count('boss')
            for k, seq in _seqs.items() if k >= cur_plane)
        acc += float(eff.gold_per_boss_node) * _bosses
    # 通道 5:固定息(每节点固定息上调整数,金等价直读)
    if eff.interest_flat_per_node:
        acc += float(eff.interest_flat_per_node) * remaining
    # 通道 6:每节点 XP 流
    if eff.xp_per_node:
        acc += float(eff.xp_per_node) * remaining * XP_GOLD_RATE
    # 通道 7:即时 XP
    if eff.xp_instant:
        acc += float(eff.xp_instant) * XP_GOLD_RATE

    if acc <= 0.0:
        # fail-closed 门:非正金期望 = 无通道可计(全通道非负,0 即空)
        return (0.0, False)
    return (acc, True)


# ===== 构建期校验(import 即炸)=====


def _validate_field_classification() -> None:
    """EconomyEffect 全字段三分分类校验(45 字段;未分类字段 = 建模缺口
    静默,炸出——沿 env 批立场表覆盖校验的治理形态,对象从 83 环境换成
    字段闭集)。

    扫 STRATEGY_ECONOMY 全表**非默认字段**:每个出现过的字段名必须落
    「计分/待建模/不计」三类之一(单一定义 = 唯一归属,双归属即炸);
    三分类并集必须恰覆盖 EconomyEffect 全字段闭集(注册表新字段未分类
    即炸,防静默塌 0)。"""
    from dataclasses import fields as _dc_fields

    _defaults = EconomyEffect()
    _seen: set[str] = set()
    for _eff in STRATEGY_ECONOMY.values():
        for _f in _dc_fields(EconomyEffect):
            if getattr(_eff, _f.name) != getattr(_defaults, _f.name):
                _seen.add(_f.name)
    _classified = _CASH_SCORED_FIELDS | _PENDING_MODELING_FIELDS | _NOT_SCORED_FIELDS
    _unclassified = _seen - _classified
    if _unclassified:
        raise ValueError(
            f"策略经济字段未分类(计分/待建模/不计三分缺位):{sorted(_unclassified)}")
    _double = (_CASH_SCORED_FIELDS & _PENDING_MODELING_FIELDS)
    _double |= (_CASH_SCORED_FIELDS & _NOT_SCORED_FIELDS)
    _double |= (_PENDING_MODELING_FIELDS & _NOT_SCORED_FIELDS)
    if _double:
        raise ValueError(f"策略经济字段双归属(分类互斥破):{sorted(_double)}")
    _all_fields = {_f.name for _f in _dc_fields(EconomyEffect)}
    _missing = _all_fields - _classified
    if _missing:
        raise ValueError(
            f"策略经济字段分类闭集缺位(EconomyEffect 新字段未入三分):{sorted(_missing)}")


def _validate_pending_modeling_registry() -> None:
    """卡级待建模登记校验(断言集合按 29 号稿 §2.1 定死,防「兜底」
    写成恒真断言):

    ① 键 = 注册表规范名(孤儿即炸);② 值非空(描述腿清单);
    ③ 「economy 条目在册而 EconomyEffect 全字段默认的登记条目必须在册」
    (现仅孪生素数——全默认卡不入字段分类校验视野,唯卡级登记可辖);
    ④ 按适用范围规则派生的登记卡闭集必须在册(直调 5 张:固定理财/固定理财+/
    孪生素数/狸财经狸/超发货币——前两者兼「字段在册未挂值」腿,后三者
    兼「无字段」腿)。混合卡的腿级明细不可自动验证,靠行为申报清单
    (29 号稿 §2.1)人工对账兜底。"""
    for _name in STRATEGY_ECONOMY_PENDING_MODELING:
        if _name not in INVESTMENT_STRATEGIES:
            raise ValueError(f"待建模在册孤儿键(注册表无此卡):{_name!r}")
        if not STRATEGY_ECONOMY_PENDING_MODELING[_name]:
            raise ValueError(f"待建模在册空描述:{_name!r}")
    # ③ 全默认 economy 条目必须在册(现仅孪生素数,直调亲核)
    _default_eff = EconomyEffect()
    _all_default = {n for n, eff in STRATEGY_ECONOMY.items()
                    if eff == _default_eff}
    _missing_default = _all_default - set(STRATEGY_ECONOMY_PENDING_MODELING)
    if _missing_default:
        raise ValueError(
            f"全默认 economy 条目缺卡级待建模登记:{sorted(_missing_default)}")
    # ④ 适用范围规则派生闭集必须在册(直调 5 张;固定理财系兼未挂值腿、
    # 后三者兼无字段腿——两适用范围形态各由本断言辖住代表)
    _required_closed_set = ('固定理财', '固定理财+', '孪生素数', '狸财经狸', '超发货币')
    _missing_closed = [n for n in _required_closed_set
                       if n not in STRATEGY_ECONOMY_PENDING_MODELING]
    if _missing_closed:
        raise ValueError(
            f"按辖域规则派生的待建模登记卡闭集缺位:{_missing_closed}")


_validate_field_classification()
_validate_pending_modeling_registry()
