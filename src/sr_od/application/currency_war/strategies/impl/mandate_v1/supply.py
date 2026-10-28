"""补给画面策略(mandate_v1;宪法六「一画面一策略文件」兑现)。

判据结构 = 三级字典序(用户裁定 2026-09-24):**钻 > 终局角色 > 装备**。
字典序而非加法合分:三轴量纲不可通约(人口位/终局阵容成员/装备),加法
需新拍跨轴权值;字典序 = 裁定偏好的直接编码,零自由参数(轴间不可补偿
——终局成员卡永远压过高价值装备卡,即裁定本意)。

- 第 1 级 钻:∃ ``SupplyOption.has_diamond`` → 带钻候选胜出(单钻直选;
  多张带钻 → 依次进第 2/3 级比出一张)。依据:财富宝钻 effect「团队规模
  上限+1,无论是否被角色穿戴…」、红钻/蓝钻 = 星徽合成材料
  (cw_equipment_data 装备注册表);检测集单一源 =
  ``kernel/cw_obs_core.DIAMOND_EQUIP_NAMES``(红钻/蓝钻/财富宝钻)。
- 第 2 级 终局角色:激活 = ``locked_comp`` 非 None ∧ 非降格帧(用户
  裁定「想要的角色只为终局考虑,不按过渡阵容选」)。名单 =
  ``Comp.core_chars ∪ shared_chars``(不含 transition_chars——过渡成员
  按裁定不入名单);``char`` 读缺(OCR 未命中,空串)的选项不进角色
  候选(不猜,仍参与装备轴)。候选内多候选 tiebreak:①能凑星者先
  (选入后与全场同名 1★ 恰成 3 张 = ``cw_merge_simulate.same_star_count``
  ``(char, 1, bench, deployed) == 2``;布尔判据零梯度,count 1 与 0 不分);
  ②仍并列 → 第 3 级装备比。
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
手牌三级全空(无带钻 ∧ 角色级无候选或未激活 ∧ 装备级全体落 tier 0,
**只看档位不看通用值**——用户裁定读法 A,tier 0 内高通用值件帧仍属
三级全空)∧ 次数闸放行。次数闸内嵌本函数(照 invest_env.decide 读
``env_refresh_left`` 同构):``gs.supply_refresh_left`` 读数 ≥1 才建议刷;
None = 未观察 → 不建议刷(fail-closed);left 缺/尽 → 直接落第 3 级选卡
(「三级全空 ∧ 建议刷但闸拒绝」的产出组合不存在,op 侧对照闸仅剩刷新
锚点缺失一种触发面)。``EQUIP_GENERIC_VALUE`` 表在本批降格为 tier 内
定序常数消费,表本体迁移义务不在本文件扩面。

已知失真申报:席满帧补给角色入账分支溢入单位不入 gs(记账层不建模溢出席)
→ 凑星判据对该单位系统性漏计,归观察/记账批,本文件如实消费现值。

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
    Unit,
    bench_units_of,
    deployed_rows_of,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    same_star_count,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_events import SupplyOption


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
           ) -> SupplyDecision | SupplyRefreshSuggestion:
    """补给选卡决策(三级字典序:钻 > 终局角色 > 装备;纯值出口,flow
    包装动作词表)。

    - options = 屏上候选(``gs.supply`` payload 槽序,左→右 = 画面列序);
    - locked_comp = flow 经 ``get_comp`` 解析后的阵容对象(None = 未锁,
      含套名解析失败回落);demoted_endgame = 降格帧直通(True → 角色级
      与 key_equips 参照一律按未锁口径;防御位——现役降格路径已清
      locked_comp,cw_intention 降格分支);
    - 空候选帧 → idx=0 no-options(与旧码同形;现役观察层/op 守卫下
      不应到达,纯函数定义须完备)。
    """
    if not options:
        return SupplyDecision(idx=0, reason='no-options')
    diamonds = [o for o in options if o.has_diamond]
    if len(diamonds) == 1:
        return SupplyDecision(idx=diamonds[0].idx, reason='第1级:带钻')
    wanted = _endgame_chars(locked_comp, demoted_endgame)
    # 决策比较池:多钻帧 = 带钻候选(第 1 级支配,钻内细分);无钻帧 =
    # 全体候选(空串 equip 名按未知参与,装备机器表外 0)。
    pool = diamonds if diamonds else options
    # 第 2 级:终局成员候选(pool 内;char 读缺不进候选)。
    char_pool = ([o for o in pool if o.char and o.char in wanted]
                 if wanted is not None else [])
    # 刷新判据(仅无钻帧可能三级全空):角色级空转 ∧ 装备级全体 tier 0
    #(只看档位不看通用值,读法 A)。
    if not diamonds and not char_pool and _all_tier_zero(
            options, gs, locked_comp, demoted_endgame):
        left = gs.supply_refresh_left.value
        if left is not None and left >= 1:
            return SupplyRefreshSuggestion(
                reason='refresh: 三级全空(无钻/角色级空转/装备全tier0)')
    if char_pool:
        return _pick_char_level(char_pool, gs, locked_comp, demoted_endgame,
                                bool(diamonds))
    return _pick_equip_level(pool, gs, locked_comp, demoted_endgame,
                             bool(diamonds))


def _endgame_chars(locked_comp: Comp | None,
                   demoted_endgame: bool) -> frozenset[str] | None:
    """第 2 级终局名单(None = 角色级空转:未锁定/降格帧)。

    名单 = core_chars ∪ shared_chars;不含 transition_chars(用户裁定
    「不按过渡阵容选」)。"""
    if locked_comp is None or demoted_endgame:
        return None
    return (frozenset(locked_comp.core_chars)
            | frozenset(locked_comp.shared_chars))


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


def _can_merge_star(char: str, gs: GameState, bench: list[Unit],
                    deployed: tuple[Unit, ...]) -> bool:
    """能凑星 = 选入该角色后与全场(上阵行域 ∪ 备战席)同名 1★ 恰成
    3 张(合成 2★)。deployed 须为行域展平的扁平 Unit 序列——(front,
    back) 二元组直传会被条目身份协议 fail-closed 静默跳过 = 上阵域漏计。
    补给入席单位恒 1★,3★ 合成不入判据(2×2★+1×1★ 不满足同名同星
    ≥3 合一)。bench = ``bench_units_of`` 槽序裸 Unit(条目身份协议对
    裸 Unit 正确,计数等价)。"""
    return same_star_count(char, 1, bench, deployed) == 2


def _reason(has_diamond: bool, tail: str) -> str:
    """归因串拼装(多钻帧带第 1 级前缀,标明钻内细分路径)。"""
    return f'第1级带钻 {tail}' if has_diamond else tail


def _pick_char_level(char_pool: list[SupplyOption], gs: GameState,
                     locked_comp: Comp | None, demoted_endgame: bool,
                     has_diamond: bool) -> SupplyDecision:
    """第 2 级选卡:能凑星者先(布尔,零梯度);仍并列 → 第 3 级装备比
    (候选内同一打分机器,禁第二套)。"""
    bench = bench_units_of(gs)
    front, back = deployed_rows_of(gs)
    deployed = (*front, *back)
    mergeable = [o for o in char_pool
                 if _can_merge_star(o.char, gs, bench, deployed)]
    cand = mergeable if mergeable else char_pool
    if len(cand) == 1:
        o = cand[0]
        tag = '凑星' if mergeable else '终局成员'
        return SupplyDecision(
            idx=o.idx, reason=_reason(has_diamond,
                                      f'第2级角色:{tag} {o.char}'))
    spare, total = _two_accounts(gs)
    keys = _key_equips(locked_comp, demoted_endgame)
    k = pick_equipment([o.equip for o in cand], key_equips=keys,
                       owned_spare=spare, owned_total=total)
    o = cand[k]
    tier = equip_tier(o.equip, key_equips=keys,
                      owned_spare=spare, owned_total=total)
    return SupplyDecision(
        idx=o.idx,
        reason=_reason(has_diamond,
                       f'第2级角色并列 装备定序 {o.equip or "?"}'
                       f' tier={tier}'))


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
    return SupplyDecision(
        idx=o.idx,
        reason=_reason(has_diamond,
                       f'第3级装备 {o.equip or "?"} tier={tier}'))
