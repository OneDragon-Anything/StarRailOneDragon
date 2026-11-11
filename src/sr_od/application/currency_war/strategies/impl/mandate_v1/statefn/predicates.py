"""板面/目标线谓词(目标线 K/零重叠)+ 卖出资格物理谓词。

目标线 K 的在产实现:终局成员集(core ∪ shared,成员集单一源 =
cw_comps.Comp.members;口径 = strategy-docs/12_line_and_intention.md
§2 与 strategy-telemetry `k_members` 行)与零重叠资格。升级触发不落
本模块——单判据三分派单一源 = criteria/levelup.upgrade_trigger。

(「挂后台效果」资格谓词族 bench_effect_qualified/bench_effect_context
已随旧评估器退役删除——统一让位优先级迭代 3.4:四处消费位整批退役,
该维度由统一序列档 9 判定承载;cw_chars 的 bench_effect 数据字段保留
为游戏数据。)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_comps import Comp
from sr_od.application.currency_war.kernel.cw_economy import loss_exact
from sr_od.application.currency_war.kernel.cw_exec_state import (
    bench_slot_unit,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    plane_of,
    round_num_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
    )


def line_members(comp: Comp | None) -> tuple[str, ...]:
    """目标线 K = 阵容 的终局成员集(core ∪ shared,COMP_LIBRARY 运行时
    可判定;线内/线外分类的基准,strategy-docs/12_line_and_intention.md §2
    与 strategy-telemetry `k_members` 行)。阵容 缺 → 空元组(零重叠全开,
    fail 方向=可逆面默认做)。成员集单一源 = Comp.members,本函数只承载
    None 语义与 strategies 层入口。"""
    return comp.members if comp is not None else ()


def zero_overlap(name: str, k: tuple[str, ...]) -> bool:
    """与目标线 K 零重叠(P41 分类表第一行资格条件「与终局阵容锁定零重叠」;
    M4 燃料件卖出的前提之一)。"""
    return name not in k


def item_slot_unsellable(unit: BenchSlot) -> bool:
    """占位件物理门(腾席卖出资格跨通道共享谓词;三通道资格循环首门)。

    真值 = 备战席槽位 kind ∈ ('tome','bookcard','supply_box')
    (观察写端按状态容器观察 kind 落位)——备战槽非角色占席物品(补给箱/星徽秘典/典籍书册等)
    无卖出交互且无金币现值——实机采证:同参数拖拽出售,角色 9 连全卖、
    箱零效果;宝箱面 = 4 选 1 装备面板,无金币现值、无出售项。任何星级
    不可变现 ⇒ 恒不入腾席卖出资格集。知识基准 =
    docs/game/currency_war/research/board_structure.md §备战栏
    「备战槽可被非角色物品占据」。

    消费位 = ``mandate.fuel_sell_candidates``(M4 燃料)/ ``criteria/sell.
    sell_for_interest``(凑息)/ ``criteria/sell.funding_support_sell``
    (支付变现)三通道资格循环首门,判读先于其余资格门;生产观察层
    SIFT 不产占位件条目,sim 假环境经观察面直喂 bench——本门 = 各卖出
    通道发出前唯一的占位件资格防线。新卖出通道必须经本谓词,禁第三处
    kind 判定内联复制(静态测试 = sr-od-test
    test_sell_candidates.py 占位件物理门段)。与部署侧 ``cw_deploy_logic``
    'item_slot' 恒 held 同谓词同向(该面防误上,本面防误卖)。
    缺省 False = 无标记形态不误伤(与部署侧同款防御读)。
    """
    return bench_slot_unit(unit) is None


def is_unsellable_system_unit(name: str) -> bool:
    """系统召唤单位物理门(cost=0 注册表单位,卖出资格跨通道共享谓词)。

    真值 = 注册表登记 cost=0(现行 = 狸小虎/狸小龙/佩佩/狸职狸狸——
    投资策略召唤单位,恒占后排、不可拖/不可卖,数据基准 = cw_chars.py
    特殊召唤单位段)。真卖出系统单位是游戏无效交互;同时 cost=0 在
    实费档缺失时会按中费 3 估(priority 档 10 概率分档),让位排序对它
    产生无意义键值——本门 = 场景判据件池构建面唯一的系统单位防线,
    与 :func:`item_slot_unsellable`(占位件物理门)同向互补:那面防
    「非角色占席」误卖,本面防「cost=0 角色」误卖。未登记名(识别
    残缺)不拦——按 mid-fee 估参与排序,卖出失败由上报链负结果兜底。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    c = CHARACTERS.get(name)
    return c is not None and not c.cost


def p1_blood_floor(state: GameState) -> bool:
    """P1 濒死带域谓词(hp ≤ HP_BAND_NEAR_DEATH ∧ plane 1 ∧ 可信)。

    **现行消费面 = 纯观测**(entry.py 形态⑥金滞留观测的带判定/
    flow.py 锁生成可行性观察件共谓词)——决策面消费(血线硬地板
    解锁包三件:经验停付让位/凑息禁令/跌破利息档批解锁)已随血线地板
    删除链停用(11 号稿 §2 拦截层 血线地板解锁行;正典依据 口述条目 39(登记簿已退役)「HP 不作决策依据」——濒死响应 = 修经济/阵容本身)。本谓词
    保留为观测分键的带判定读口。

    判定:信任门 = ``hp_decision_trusted``(kernel 单一源;不可信帧/
    hp 无值帧 fail 向不判线);位面域 = 仅 plane 1(P2+ 半边 =
    :func:`p2_blood_floor`,两域互补且不交);阈值常量单一源 =
    ``lambda_death.HP_BAND_NEAR_DEATH``(血带结构基准,禁本处字面量
    第二份)。
    """
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        hp_decision_trusted,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.lambda_death import (
        HP_BAND_NEAR_DEATH,
    )
    if state is None:
        return False   # 缺供给 fail-closed(D2 语义族;None 守卫显式化)
    if not hp_decision_trusted(state):
        return False
    if plane_of(state) != 1:
        return False
    hp = state.hp.value
    return hp is not None and hp <= HP_BAND_NEAR_DEATH


def p2_blood_floor(state: GameState) -> bool:
    """P2 濒死带域谓词(与 p1_blood_floor 同构的 P2+ 半边)。

    **现行消费面 = 纯观测**(flow.py 锁生成可行性观察件的 boss 濒死
    死区分键 / entry.py 形态⑥金滞留观测的带判定)——决策面消费
    (解锁包三件:M3 停付让位/凑息禁令/濒死解锁)已删除(随血线地板删除链;
    11 号稿 §2 拦截层 血线地板解锁行),本谓词保留为观测分键的
    带判定读口,不再有解锁包合成口(原 ``p2_blood_floor_unlock``
    随决策消费面消亡)。

    判定(同构不同域,与同族 p1 谓词镜像):
    - 信任门 = ``hp_decision_trusted``(kernel 单一源,同 p1);
    - 位面域 = plane ≥ 2(与 p1 的 plane==1 互补且不交);
    - 阈值常量单一源 = ``lambda_death.HP_BAND_NEAR_DEATH``(血带结构
      基准,禁本处字面量第二份)。
    """
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        hp_decision_trusted,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.lambda_death import (
        HP_BAND_NEAR_DEATH,
    )
    if state is None:
        return False   # 缺供给 fail-closed(D2 语义族;None 守卫显式化)
    if not hp_decision_trusted(state):
        return False
    if plane_of(state) < 2:
        return False
    hp = state.hp.value
    return hp is not None and hp <= HP_BAND_NEAR_DEATH


def t5_p1_false(gold: int, spend: int, rounds: int, net_income: int,
                cap_resolved: int) -> bool:
    """T5 未锁定止血买的结构判据支撑谓词(/§4;p46 P1 谓词
    原式,判据 = loss_exact 现算,不按任何帧集清单)。

    ``L(g,c,R_全局,Ī,cap) == 0`` ⟺ P1 假 ⟺ 该帧出 p46 否决域(D =
    P1∧P2∧P3 恒假)——无需 E_rev、无需 V_deploy、无需 P2 分析,止血买
    的正当性由「占用集合基数严格扩 + 全额可退可逆 + 息账零损」三结构量
    的支配论证独立承载(仅作「有比没有强」接受
    形态的已登记先例,适用范围限定同节)。判据全为注册表派生量,零 hp/胜率/
    掉血先验/板面评分消费——不在 00_framework §3 硬闸门适用范围,无开关。

    ``net_income`` 形参 = 逐节点净收入 Ī 的现算值(调用方经
    cw_economy.net_income 供给;非 i_bar 常量,命名随 cw_economy
    docstring 术语口径)。边界:cap=0(买断制)局 L≡0 ⇒ 全帧 P1 假
    ⇒ T5 全开,方向安全;P1 真帧(现算 L>0)结构层
    不发出,落行为层挂起(V_deploy 候用户逐项授权,宪法硬闸,禁自裁)。
    """
    return loss_exact(gold, spend, rounds, net_income, cap_resolved) == 0


# ===== 前窗/零成型谓词族(P90 面①;设计权威版本 =
# 11 号稿 §3.1(P90 前窗行);
# 命题 = math_proofs P90-P94 行)=====

#: 零战斗节点词集(节点表查表的战斗性判定的非战斗半边):生产表中文词
#: (就地展开;原 ``P1_NODE_TEMPLATE`` 词表/``tools/cw_node_validate`` 校验器
#: 已随死代码清偿移除)+ 英文词;英文半边的单一源 =
#: kernel cw_line_switch._ZERO_LOSS_NODE_KINDS 同集(此处展开因该常量
#: 为模块私有,战斗性判定需中英并集,勿再散落第三份)。
_FRONT_NONCOMBAT_NODES: frozenset[str] = frozenset(
    {'reward', 'supply', '奖励', '补给'})


def front_window_table_ready(gs: GameState) -> bool:
    """前窗查表前提探针(front_window_frame 的表在场半边;调用方用于
    「P1 帧但表缺」的零静默分键,避免调用侧复刻锚定逻辑)。"""
    return (gs.node_books.plane_node_table_plane == 1
            and bool(gs.node_books.plane_node_table))


def front_window_frame(state: GameState) -> bool:
    """P1 前窗备战帧谓词(v3 面①;位面参数化 = 节点表查表定义,禁位面
    字面量,01 §8-1)。

    语义 = plane==1 ∧ 当前轮 ≤ 首个战斗节点槽位(前窗 = 首战前窗,含
    首战备战帧——v3 面①(b)「r3 备战帧上」的 r3 即查表产物,P1 众数
    表下 = 第 3 轮)。节点表单一源 = ``gs.node_books.plane_node_table``
    (开局帧实读槽序;唯一写端 = cw_screen_prep.store_plane_table 每
    位面首帧写,读端同源先例 = cw_plane_table.nodes_of_plane);位面
    基准 = ``node_books.plane_node_table_plane``(防旧表滞留跨位面误
    读);战斗性判定 = 槽词不在 ``_FRONT_NONCOMBAT_NODES`` 零战斗词集
    (中英并集,出处见常量注)。

    fail-closed 边界:表缺/基准不符 ⇒ False(前窗行为不发生 = 现行为),
    调用方分键 ``p90_front_table_missing`` 暴露;表全为零战斗词(脏表,
    每位面必有战斗的结构下退化域)⇒ 静默 False **不落分键**(审查
    H4 修:暴露主张收窄至表缺/基准不符两支)。
    """
    plane = plane_of(state)
    round_num = round_num_of(state)
    if plane != 1:
        return False
    node_books = state.node_books
    if node_books.plane_node_table_plane != 1:
        return False
    table = node_books.plane_node_table or []
    first_battle_idx: int | None = None
    for i, node in enumerate(table):
        if str(node).strip() not in _FRONT_NONCOMBAT_NODES:
            first_battle_idx = i
            break
    if first_battle_idx is None:
        return False   # 脏表退化域:静默 False(边界注见 docstring)
    return 1 <= int(round_num or 0) <= first_battle_idx + 1


def zero_form_frame(deployed: list) -> bool:
    """零成型帧谓词(P90 收窄适用范围 e=0;P94 谓词原文 = per-体系
    ``board_factions[s] < FACTIONS[s].tiers[0]``,希儿系复合判据单列)。

    四体系 = 三羁绊系(阈值对 = knowledge/cw_engine_facts.
    TRANSITION_TRAITS 的同注册表派生式——SYSTEM_CARDS × FACTIONS tiers[0];
    strategies→knowledge 非法桶边故本地同式派生,零漂移契约同款:
    同一注册表派生不存在字面双源,禁写字面阈值)+ 希儿系(复合判据
    单一实现 = kernel ``seele_system_formed``)。板面计数 = 已上场全
    羁绊计数(kernel ``deployed_bond_counts`` 单一源,bench 持有不计
    ——激活档是板面档)。``engines_count`` 为四体系合计标量,禁作
    per-体系谓词(设计轮一低 8③ 口径),本函数逐体系比较。
    """
    from sr_od.application.currency_war.data.cw_factions import FACTIONS
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        deployed_bond_counts,
        seele_system_formed,
    )
    from sr_od.application.currency_war.kernel.cw_system_cards import (
        SYSTEM_CARDS,
    )
    system_tiers = tuple(
        (card.judge_factions[0], FACTIONS[card.judge_factions[0]].tiers[0])
        for card in SYSTEM_CARDS.values() if card.card_id != 'seele')
    deployed_names = {d.char_id or '' for d in (deployed or [])
                      if d is not None and (d.char_id or '')}
    board_factions = deployed_bond_counts(deployed_names)
    for bond, tier in system_tiers:
        if board_factions.get(bond, 0) >= tier:
            return False
    return not seele_system_formed(board_factions, deployed_names)


def advances_four_system(name: str) -> bool:
    """四体系推进件判定(零成型帧排序层前移对象;P20 方向级背书,
    非金量纲、不构成支出放行)。

    推进件 = 店内卡所属阵营/流派命中三羁绊体系键(SYSTEM_CARDS ×
    FACTIONS 注册表同注册表派生,zero_form_frame 同源注释)∨ 希儿系
    贡献件(kernel ``is_seele_system_member`` 单一源,入参 = 该卡自身
    bonds:希儿本人 + 量子/贝放大器)。零成型帧上全部体系 < tiers[0],
    任一体系成员买入都单调推进激活进度(P90 收益面 iii)。
    """
    if not name:
        return False
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        is_seele_system_member,
    )
    from sr_od.application.currency_war.kernel.cw_system_cards import (
        SYSTEM_CARDS,
    )
    ch = CHARACTERS.get(name)
    if ch is None:
        return False
    bonds = {card.judge_factions[0]
             for card in SYSTEM_CARDS.values() if card.card_id != 'seele'}
    if bonds & ({*ch.factions} | {*ch.flows}):
        return True
    return is_seele_system_member(name, {*ch.factions} | {*ch.flows})


__all__ = [
    'advances_four_system',
    'front_window_frame', 'front_window_table_ready', 'line_members',
    't5_p1_false', 'zero_form_frame', 'zero_overlap',
]
