"""补给画面策略(mandate_v1;宪法六「一画面一策略文件」兑现)。

判据结构 = 三级字典序(用户裁定 2026-09-24):**钻 > 角色 > 装备**。
字典序而非加法合分:三轴量纲不可通约(人口位/角色获取/装备),加法
需新拍跨轴权值;字典序 = 裁定偏好的直接编码,零自由参数(轴间不可补偿
——幸存角色卡压过高价值装备卡,即裁定本意)。统一让位优先级迭代 3.2:
第 2 级从「终局角色布尔判定 + 凑星平手裁决」改**虚拟全局评估形态**
(规格 = changes/2026-10-29-unified-priority/details/acquisition-and-
sell.md §3.1——补给选项中的角色按获取角色流程的评估形态逐个判定,
与商店牌同一逻辑;「是否终局角色」布尔门随统一序列退役,总纲 §2.6
消费点映射):

- 第 1 级 钻:∃ ``SupplyOption.has_diamond`` → 带钻候选胜出(单钻直选;
  多张带钻 → 依次进第 2/3 级比出一张)。依据:财富宝钻 effect「团队规模
  上限+1,无论是否被角色穿戴…」、红钻/蓝钻 = 星徽合成材料
  (cw_equipment_data 装备注册表);检测集单一源 =
  ``kernel/cw_obs_core.DIAMOND_EQUIP_NAMES``(红钻/蓝钻/财富宝钻)。
- 第 2 级 角色(虚拟全局评估):候选 = 读到角色名的选项(char 读缺
  不进候选、不猜,仍参与装备轴);每个候选按获取角色流程评估形态
  逐个判定——虚拟置入局面 → 升星连锁模拟 → 部署重排 → 统一序列
  定位:**被虚拟阵容淘汰的(排序末位 = 自己)排除**;幸存者按其虚拟
  排序键(priority.sort_key,键小 = 优先级高)赋值;多个幸存者取键
  最小。全部淘汰(候选皆劣于手里任一持有)→ 角色级空转,落第 3 级。
- 第 3 级 装备:打分单一源 = 直调共享机器
  ``cw_equip_value.pick_equipment``((tier, base) 字典序,并列取输入序
  先者;「候选多选一禁第二套打分」= cw_equip_value 模块头裁定)。tier =
  ``equip_tier``(3 key 直击且需求未满足/2 近兑现/1 key 材料/0 其余;
  key_equips 可含重复,需求按计数——修掉旧「成品隶属 +10」对已持够数
  重复成品的误加分)。三参:``key_equips`` = locked_comp.key_equips(与
  角色级同源;未锁/降格 → 空序列,全体落 tier 0);两账 = ``owned_spare``
  = ``gs.equips`` 现值(备用库存账)、``owned_total`` = spare + 行域/
  备战席穿戴账(照 flow.decide_box_card 两账先例,本函数内自 gs 构造;
  gs 为纯函数输入,同口径同源)。

刷新判据(用户裁定 2026-09-24「三级全空才刷」结构):建议刷 = 且仅 =
手牌三级全空(无带钻 ∧ 角色级无幸存候选 ∧ 装备级全体落 tier 0,
**只看档位不看通用值**——用户裁定读法 A,tier 0 内高通用值件帧仍属
三级全空)∧ 次数闸放行。次数闸内嵌本函数(照 invest_env.decide 读
``env_refresh_left`` 同构):``gs.supply_refresh_left`` 读数 ≥1 才建议刷;
None = 未观察 → 不建议刷(fail-closed);left 缺/尽 → 直接落第 3 级选卡。
``EQUIP_GENERIC_VALUE`` 表在本批降格为 tier 内定序常数消费,表本体迁移
义务不在本文件扩面。

虚拟重算载体纪律(acquisition-and-sell §1 定案):局面快照纯计算
(``mandate.snapshot_frame`` 构造 + ``simulate_acquired_units`` 轻量
升星连锁),禁容器深拷贝;副本零遥测——journal/策略遥测/决策帧三通道
零写入(本模块判据为纯值出口,动作包装留 flow)。

输出契约:纯值 dataclass(:class:`SupplyDecision` /
:class:`SupplyRefreshSuggestion`),不含动作词表——动作包装
(CwActionPickSupplyParam / CwActionRefreshSupplyParam)留 flow(与
invest_env 同构,便于直测与 sim 复用预留)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_equip_value import (
    equip_tier,
    pick_equipment,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_units_of,
    deployed_rows_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_events import SupplyOption
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.priority import (
        PriorityKey,
    )


# ===== 输出契约(纯值 dataclass,不含动作词表)=====

@dataclass(frozen=True)
class SupplyDecision:
    """选卡决策。

    [索引定义] idx = options 容器下标(0 基;坐标系 = 调用方传入候选序
                左→右 = 画面列序,与选项 ``SupplyOption.idx`` 同一坐标系;
                取值时机 = 本帧决策期快照,恒稳);reason = 归因串
                (命中级与 tiebreak 路径,仅观测)。
    """
    idx: int
    reason: str


@dataclass(frozen=True)
class SupplyRefreshSuggestion:
    """刷新建议(动作包装 CwActionRefreshSupplyParam 留 flow;次数闸已
    内嵌 :func:`decide`,op 侧对照闸与重调链零改动)。"""
    reason: str


# ===== 判据件(三级字典序 + 闸内嵌刷新;语义见模块头)=====

def decide(options: list[SupplyOption], gs: GameState,
           locked_comp: Comp | None, demoted_endgame: bool,
           *, config: object | None = None,
           ) -> SupplyDecision | SupplyRefreshSuggestion:
    """补给选卡决策(三级字典序:钻 > 角色〔虚拟全局评估〕> 装备;纯值
    出口,flow 包装动作词表)。

    - options = 屏上候选(``gs.supply`` payload 槽序,左→右 = 画面列序);
    - locked_comp/demoted_endgame = 第 3 级装备轴参照(角色级不再消费
      ——终局布尔门随统一序列退役);config = 随机流种子供给(缺省
      None → 策略器构造缺省播法,``priority.priority_rng_of``);
    - 空候选帧 → idx=0 no-options(与旧码同形;现役观察层/op 守卫下
      不应到达,纯函数定义须完备)。
    """
    if not options:
        return SupplyDecision(idx=0, reason='no-options')
    diamonds = [o for o in options if o.has_diamond]
    if len(diamonds) == 1:
        return SupplyDecision(idx=diamonds[0].idx, reason='第1级:带钻')
    # 决策比较池:多钻帧 = 带钻候选(第 1 级支配,钻内细分);无钻帧 =
    # 全体候选(空串 equip 名按未知参与,装备机器表外 0)。
    pool = diamonds if diamonds else options
    char_pool = [o for o in pool if o.char]
    # 第 2 级:虚拟全局评估(角色候选逐个虚拟判定,幸存者升序)。
    ranked = _rank_char_candidates(char_pool, gs,
                                   config=config) if char_pool else []
    # 刷新判据(仅无钻帧可能三级全空):角色级无幸存 ∧ 装备级全体
    # tier 0(只看档位不看通用值,读法 A)。
    if not diamonds and not ranked and _all_tier_zero(
            options, gs, locked_comp, demoted_endgame):
        left = gs.supply_refresh_left.value
        if left is not None and left >= 1:
            return SupplyRefreshSuggestion(
                reason='refresh: 三级全空(无钻/角色级无幸存/装备全tier0)')
    if ranked:
        o, key = ranked[0]
        return SupplyDecision(
            idx=o.idx,
            reason=f'第2级角色:虚拟全局评估幸存 {o.char} '
                   f'键首档={int(key[0])}')
    return _pick_equip_level(pool, gs, locked_comp, demoted_endgame,
                             bool(diamonds))


def _rank_char_candidates(
        char_pool: list[SupplyOption], gs: GameState, *,
        config: object | None = None,
) -> list[tuple[SupplyOption, PriorityKey]]:
    """第 2 级虚拟全局评估(acquisition §3.1;与商店牌同一逻辑)。

    每个候选角色:虚拟置入备战位 → 升星连锁模拟 → ``select_deployment``
    部署重排 → 虚拟局面内统一序列定位。淘汰判定 = 排序末位 = 新牌自己
    (含同优先级在手旗标的不换手形态),**仅置换需要存在时适用**——虚拟
    置入后备战位仍有空位(含合成净释放) = 无让路对象,候选不经淘汰
    (与获取角色流程「不再满位 → 无需让路直接买」同构,总纲 §2.3 步骤
    2)。幸存者按新牌虚拟排序键赋值,返回按键升序(键小 = 优先级高,
    取首位)。判定全程快照纯计算零遥测(禁容器深拷贝,
    acquisition-and-sell §1)。

    装配 = 统一入口 :func:`priority.assemble_candidate_eval`(候选评估
    装配整函数,与商店获取让位同一实现;域差异仅候选牌三件套——补给
    候选恒 1★、选卡零成本)。候选不进档 1 保护(裁定五 2026-11-01:
    补给沿用统一优先级,候选 = 假设性入场者按卡面档定序,与商店 X 同
    款;同名凑星价值由档 2 成员星目标聚合承载)。
    """
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        BENCH_CAPACITY,
        bench_slot_unit,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        mandate,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.priority import (
        assemble_candidate_eval,
        sort_key,
    )
    frame = mandate.snapshot_frame(gs)
    out: list[tuple[SupplyOption, PriorityKey]] = []
    for o in char_pool:
        sim = mandate.simulate_acquired_units(
            frame.bench, frame.deployed, o.char, 1)
        # 位移判定 = 置入后单位可用空槽 ≤ 0(占位件占槽不计入单位数,
        # 与 BENCH_CAPACITY 同一口径):满位 = 需要让路 → 排序定位;
        # 有空位 = 直接幸存(键取新牌虚拟排序键,供候选间比序)。
        _n_items = sum(1 for b in frame.bench
                       if bench_slot_unit(b) is None)
        displacement = BENCH_CAPACITY - _n_items - len(sim.bench) <= 0
        # 部署定型:virtual 两半传升星连锁模拟产物,虚拟定型真实消费
        # 候选置入的虚拟局面(升星连锁合成/换人定型均被感知;原「构造
        # v_frame 传第一参」形态 = 定型读真实容器、候选从未进定型,
        # 已随统一装配修复——第一参本就是生产路径形参,virtual 分派
        # 不消费它)。
        prep = mandate.assemble_prep_context(gs, gs, frame)
        target = mandate.select_deployment(
            frame, prep,
            virtual_bench=[bs for _i, bs in sim.bench],
            virtual_field=sim.field)
        ctx, units = assemble_candidate_eval(
            gs, gs, sim=sim, base_bench_len=len(frame.bench),
            target=target, name=str(o.char), star=1, cost=0,
            config=config)
        # 排序定位一次求键(禁第二排序实现:判定消费 sort_key 本体,
        # 升序末位 = 最先让路 = 键最大者)。
        if displacement:
            keys = [sort_key(u, ctx) for u in units]
            last = max(range(len(units)), key=lambda i: keys[i])
            if last == len(units) - 1:
                continue   # 末位 = 新牌自己(最易让路)→ 被虚拟阵容淘汰
            out.append((o, keys[-1]))
        else:
            out.append((o, sort_key(units[-1], ctx)))
    out.sort(key=lambda t: t[1])
    return out


def _key_equips(locked_comp: Comp | None,
                demoted_endgame: bool) -> tuple[str, ...]:
    """第 3 级 key 参照(未锁/降格 → 空序列,全体落 tier 0;可含重复,
    需求按计数——``equip_tier`` 契约,禁去重)。"""
    if locked_comp is None or demoted_endgame:
        return ()
    return tuple(locked_comp.key_equips or ())


def _two_accounts(gs: GameState) -> tuple[list[str], list[str]]:
    """两账口径(照 flow.decide_box_card 先例,本函数内自 gs 构造):
    spare = 备用库存账(``gs.equips`` 现值);total = spare + 行域/备战席
    穿戴账(部署位成员 equips 透传,需求守卫用)。"""
    spare = list(gs.equips.value or [])
    front, back = deployed_rows_of(gs)
    worn = [eq
            for u in (*front, *back, *bench_units_of(gs))
            if u is not None
            for eq in (getattr(u, 'equips', None) or [])]
    return spare, spare + worn


def _all_tier_zero(options: list[SupplyOption], gs: GameState,
                   locked_comp: Comp | None,
                   demoted_endgame: bool) -> bool:
    """装备级「全体落 tier 0」判定(刷新判据第三空;只看档位不看通用值
    ——读法 A,tier 0 内高通用值件帧仍属三级全空)。"""
    spare, total = _two_accounts(gs)
    keys = _key_equips(locked_comp, demoted_endgame)
    return all(equip_tier(o.equip, key_equips=keys,
                          owned_spare=spare, owned_total=total) == 0
               for o in options)


def _pick_equip_level(pool: list[SupplyOption], gs: GameState,
                      locked_comp: Comp | None, demoted_endgame: bool,
                      has_diamond: bool) -> SupplyDecision:
    """第 3 级装备选卡(单一源 = ``pick_equipment``,(tier, base) 字典序,
    并列取输入序先者 = 画面列序)。"""
    spare, total = _two_accounts(gs)
    keys = _key_equips(locked_comp, demoted_endgame)
    k = pick_equipment([o.equip for o in pool], key_equips=keys,
                       owned_spare=spare, owned_total=total)
    o = pool[k]
    tier = equip_tier(o.equip, key_equips=keys,
                      owned_spare=spare, owned_total=total)
    tail = f'第3级装备 {o.equip or "?"} tier={tier}'
    return SupplyDecision(
        idx=o.idx,
        reason=f'第1级带钻 {tail}' if has_diamond else tail)
