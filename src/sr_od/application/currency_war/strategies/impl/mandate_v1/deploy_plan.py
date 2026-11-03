"""部署计划策略层单一源(mandate_v1;落位决策权归策略实现)。

设计原则(落位决策权归策略层):
**谁上场、去哪一排、落哪个槽,全部由本模块决定;框架(执行链/写侧)
在落位上零决定**——选人/排路由/槽位选择的本模块单一源见下。

- 选人 = 统一部署搜索(``deploy_search.search_deploy_target``,阶段
  5/6 乙起;旧七桶选人族已随部署统一批丁丁批收编删除——unified-
  deploy-order §2/§4):target_board = 角色名 → (排, 选定星);
- 排路由(:func:`deploy_row_pref`,三级):阵容站位覆盖(``Comp.char_
  positions`` 字段契约「阵容特定站位要求,覆盖注册表站位真值默认」)> 注册表
  ``get_char(char_id).position_pref()`` 派生 > back 兜底——旧链路备战
  候选恒按后排、注册表偏好被丢弃的行为变化申报项
  在此落地;
- 前排保证(随迁 kernel 规则):pref=back ∧ 前排全空(出战硬要求前排有
  角色)时队列后方真 front 候选先提,无 front 候选才强转当前件;
- 槽位选择(:func:`deploy_slot_plans`):策略遍历容器行列现值自定,后排
  上限 = ``back_layout`` 现值(:func:`back_capacity_of` 单一源)——消除
  「动作发出侧空槽可指扩展槽而执行面按基线 6 槽」的静默分歧(P2 遗留);
- 出战链计划单一源(:func:`battle_chain_deploy_params`):恢复局同步步/
  达标分支共用(统一搜索 + 差分执行器链),禁各写一套计划装配;
- 发射准入部署在途谓词(:func:`launch_deploy_pending` 族):kernel
  ``readiness_launch_decision`` 的 ``deploy_pending_fn`` 注入单一实现
  (diff 非空语义;推判重放虚拟面板同族);
- 单件可上场预检(:func:`can_deploy_single_unified`):快照+X 跑统一
  搜索、X ∈ target 判定(§4 can_deploy_single 行;序有关语义申报同彼)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import get_char
from sr_od.application.currency_war.kernel.cw_exec_state import (
    DEPLOYED_FRONT_CAPACITY,
    bench_slot_unit,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        GameState,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

# (七桶选人族(_deploy_plan_inputs/select_deployments/
#  select_deployments_reasoned/has_deployable/has_deployable_reasoned/
#  can_deploy_single)与部署计划装配 deploy_plan_moves/
#  DEPLOY_PLAN_SLOT_TABLE_UNHEALTHY_KEY 已随部署统一批丁丁批收编删除:
#  围栏/成对/点火序/核心桶/必需件首桶/cap/同名去重/配方底线门/板空保底 =
#  旧线性序补丁史,选人 = 统一部署搜索定型单属(unified-deploy-order
#  §2/§4);紧缩占席序 × 容器槽位表对位防线由差分执行器的容器直读
#  坐标系承载。)


def _slot_cid(b) -> str:
    """占席条目 → 身份名(单位 = 内嵌 Unit.char_id;占位件/None = '';
    P4 容器形,解包单一源 = kernel ``bench_slot_unit``)。"""
    u = bench_slot_unit(b)
    return (getattr(u, 'char_id', '') or '') if u is not None else ''


def deploy_row_pref(char_id: str, comp: object | None) -> str:
    """落位排路由(策略三级;design §2.2「每人的排全部由策略实现决定」)。

    ① 阵容 站位覆盖:``Comp.char_positions``(字段契约「阵容 特定站位
       要求(角色→front/back),覆盖注册表 position_pref 默认」;已登记实例
       = 爻光必后台/万敌独前排/知更鸟前台,攻略实证);
    ② 注册表派生:``get_char(char_id).position_pref()``(design §2.1
       「position_pref 不入形状,消费点经注册表按 char_id 派生;禁全局
       get_role_position」——旧链路备战候选恒按后排、注册表偏好恒被
       丢弃的行为变化申报项在此生效);
    ③ back 兜底:阵容 未覆盖 ∧ 注册表未登记(未识别名)→ 后排。

    返回 'front' | 'back'。
    """
    cp = getattr(comp, 'char_positions', None) or {}
    hit = cp.get(char_id)
    if hit in ('front', 'back'):
        return hit
    ch = get_char(char_id) if char_id else None
    if ch is not None:
        return ch.position_pref()
    return 'back'


def deploy_slot_plans(bench: list[BenchSlot], up_idx: list[int],
                      comp: object | None, state: GameState,
                      ) -> list[tuple[int, str, int]]:
    """落位策略(排路由 + 前排保证 + 槽位选择;P3 落位决策权归策略本体)。

    - 排 = :func:`deploy_row_pref` 三级路由;
    - **前排保证**(kernel 规则随迁,2026-08-16 修正口径):pref=back
      ∧ 前排全空(出战硬要求前排有角色)时队列后方真 front 候选提到
      当前位,无 front 候选才强转当前 back 件;
    - 槽位 = 策略遍历容器视图现值自定:deployed 视图子表下标(排内 1 基
      派生)取占用集,首选排取最低空槽、首选排满 fallback
      另一排,两排全满截断(调用侧 cap 门先行,防御停);
    - 后排上限 = ``back_layout`` 现值(back_capacity_of 单一源,值域 6-9)
      ——发出空槽集合按实值派生,扩展局(宝钻 7/8/9)才可能指到扩展槽,
      基线 6 槽局不再出现越界槽号(P2 遗留分歧消除)。

    返回 ``[(bench 下标, row, 排内 1 基槽号)]``(发出序 = 执行序;
    落位意图完整入载荷 (bench_idx, to_row, to_slot),执行/写侧按载荷
    直落,framework 零落位决定)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        back_capacity_of,
    )
    _view = state.deployed.value
    front_occ = {i + 1 for i, u in enumerate(
        getattr(_view, 'front_slots', None) or []) if u is not None}
    back_occ = {i + 1 for i, u in enumerate(
        getattr(_view, 'back_slots', None) or []) if u is not None}
    back_total = back_capacity_of(state)
    fe = [s for s in range(1, DEPLOYED_FRONT_CAPACITY + 1)
          if s not in front_occ]
    be = [s for s in range(1, back_total + 1) if s not in back_occ]
    pending = list(up_idx)
    out: list[tuple[int, str, int]] = []
    oi = 0
    while oi < len(pending):
        bi = pending[oi]
        pref = deploy_row_pref(_slot_cid(bench[bi]), comp)
        if pref == 'back' and len(fe) == DEPLOYED_FRONT_CAPACITY and fe:
            # 前排保证(重排):队列后方有真 front 候选提到当前位
            _later = next(
                (j for j in pending[oi + 1:]
                 if deploy_row_pref(
                     _slot_cid(bench[j]),
                     comp) == 'front'), None)
            if _later is not None:
                pending.remove(_later)
                pending.insert(oi, _later)
                continue   # 原地重处理当前位(现为真 front)
            pref = 'front'   # 无 front 候选 → 强转前排
        if pref == 'front':
            row, chosen, fallback = 'front', fe, be
        else:
            row, chosen, fallback = 'back', be, fe
        if chosen:
            slot = chosen.pop(0)
        elif fallback:
            row = 'front' if row == 'back' else 'back'
            slot = fallback.pop(0)
        else:
            break   # 两排全满(防御停;cap 门先行时不可达)
        out.append((bi, row, slot))
        oi += 1
    return out

# (部署计划装配 deploy_plan_moves(选人 × 落位 × 容器对位)已随七桶
#  选人族收编删除:三路定型(卖出评估器/获取让位/出战链)消费统一
#  部署搜索 target_board,装配链退役——unified-deploy-order §4;紧缩
#  占席序 × 容器槽位表对位防线由差分执行器的容器直读坐标系承载。)


def battle_chain_deploy_params(session: StrategySession) -> list:
    """出战链部署计划(统一拖动/换星直卖序;恢复局同步步/达标分支共用,
    计划单一源 = 统一部署搜索 + 差分执行器,unified-deploy-order §2.7/§3)。

    阶段 5/6 丁:发射器换统一链(旧七桶选人 ``deploy_plan_moves`` 在板满帧
    恒零计划——「板满 ∧ bench core 待上 ∧ 无合格 victim → 直接出战」的
    deploy_swap_no_victim 形态根因)。要不要换/换谁下 = 统一搜索定型
    (target_board);板满帧经交换交互上场(被换下者回 bench 源槽,由卖出
    场景按统一让位序处置——§2.7 职责边界)。差分动作序与第 6 步/计划游标
    共用 :func:`deploy_diff.deploy_diff_target_actions` 语义(fresh 拦截同源)。

    frame 装配 = 容器现读(原 cw_loop._battle_chain_deploy_moves 内联段
    迁入;design §2.2「出战链不再装配选人输入」——出战链只调策略层计划
    入口)。空板面/定型收敛 = 空 move 序(CwActionStartBattleParam 照发)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        deploy_diff,
        deploy_search,
    )
    gs = game_state_of(session)
    panel = deploy_search.build_deploy_panel(session, gs)
    target = deploy_search.search_deploy_target(panel)
    if not target:
        return []   # 候选全不可排 fail-closed(容量矛盾,结构不可达防御)
    return deploy_diff.deploy_diff_target_actions(session, gs, target)


# ============================================================ 发射准入/预检新面


def _diff_pending_of_panel(session: StrategySession, gs: GameState,
                           panel, diff_gs: GameState) -> bool:
    """面板 → 定型 → diff 非空判定(发射准入部署在途谓词核;搜索与差分
    两段共享,生产/虚拟两路径仅面板与 diff 容器来源不同)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        deploy_diff,
        deploy_search,
    )
    target = deploy_search.search_deploy_target(panel)
    if not target:
        return False   # 候选全不可排 fail-closed = 不在途(无动作可发)
    return not deploy_diff.diff_settled(diff_gs, target)


def launch_deploy_pending(session: StrategySession, gs: GameState) -> bool:
    """发射准入的部署在途谓词(diff 非空;生产路径)。

    kernel ``readiness_launch_decision``/``launch_board_quality_report``
    的 ``deploy_pending_fn`` 注入单一实现(依赖倒置:kernel 禁 strategies
    直引,由 bridge 注入本函数对象;unified-deploy-order §4 发射抑制谓词
    行——语义 = 统一部署搜索定型后差分执行器仍有动作在途,「还有部署
    可做」→ 质量推迟帧让部署先收敛)。旧 ``has_deployable`` 七桶判空
    随选人族退役,本函数为其语义后继。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        deploy_search,
    )
    panel = deploy_search.build_deploy_panel(session, gs)
    return _diff_pending_of_panel(session, gs, panel, gs)


def launch_deploy_pending_virtual(session: StrategySession, gs: GameState,
                                  bench_slots: list, field_units: list,
                                  ) -> bool:
    """发射在途谓词·虚拟面板路径(商店受限态推判重放的注入形态;§4
    「推判重放自动继承」——同一谓词族,虚拟 bench/场上单位替换,§1
    接口契约③虚拟路径)。

    ``bench_slots``/``field_units`` 语义与 :func:`mandate.select_deployment`
    的 ``virtual_bench``/``virtual_field`` 同(升星连锁模拟产物 SimAcquisition
    两半);diff 判定容器 = 虚拟 deployed/bench 视图 duck 面板。"""
    from types import SimpleNamespace

    from sr_od.application.currency_war.kernel.cw_exec_state import (
        DEPLOYED_FRONT_CAPACITY,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BENCH_CAPACITY_DEFAULT,
        BenchView,
        DeployedView,
        Field,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        deploy_search,
    )
    panel = deploy_search.panel_from_virtual(
        session, gs, bench_slots, field_units)
    _diff_gs = SimpleNamespace(
        deployed=Field(value=DeployedView(
            front_slots=list(field_units)[:DEPLOYED_FRONT_CAPACITY],
            back_slots=list(field_units)[DEPLOYED_FRONT_CAPACITY:])),
        bench=Field(value=BenchView(slots=list(bench_slots),
                                    capacity=BENCH_CAPACITY_DEFAULT)))
    return _diff_pending_of_panel(session, gs, panel, _diff_gs)


def can_deploy_single_unified(session: StrategySession, gs: GameState,
                              name: str, star: int) -> tuple[bool, str]:
    """单件可上场预检(快照+X 跑统一搜索、X ∈ target 判定;§4
    can_deploy_single 行)。

    语义变化申报(D2-14):预检从「单候选可入性(序无关)」变「定型含 X
    判定(**序有关**——组合效应使可买性依赖其余手牌)」;成本 = 每张店内
    牌一次全搜索(D8-4 复算 ≈ 0.1s 级/次,sim 实测随批校准)。候选 bench
    追加(快照+X),场上单位 = 现板紧缩行序;拒因口径 = '' 可入 /
    'not_in_target' 搜索定型未含 X / 'dead_stock_pair' 同名 1★ 第二张
    死库存对(买侧对偶守卫先行:搜索唯一性键归一把重复副本吸收进同键,
    X ∈ target 对既有副本恒平凡真,买面防重对语义由
    ``dead_stock_pair_buy_reject_reason`` 单一源承载,与 dominance 臂
    同守卫;旧七桶拒因闭集随选人族退役)。

    查询不可得(装配异常)由调用方按 ``precheck_unavailable`` 分键处理
    (与旧 ``can_deploy_single`` 契约同向)。"""
    try:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            BenchSlot,
            Unit,
            bench_entries_of,
            deployed_rows_of,
        )
        from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
            deploy_search,
            mandate,
        )
        from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.sell_candidates import (
            sell_line_membership,
        )
        bench = bench_entries_of(gs)
        _front, _back = deployed_rows_of(gs)
        deployed = [u for u in (*_front, *_back) if u is not None]
        if mandate.dead_stock_pair_buy_reject_reason(
                name, star, bench, deployed,
                k_members=tuple(sorted(sell_line_membership(gs)))):
            return False, 'dead_stock_pair'
        bench2 = [*bench,
                  BenchSlot(kind='unit', unit=Unit(char_id=name, star=star))]
        panel = deploy_search.panel_from_virtual(session, gs, bench2, deployed)
        target = deploy_search.search_deploy_target(panel)
    except Exception:   # noqa: BLE001  查询不可得 fail 向(调用方分键)
        return False, 'precheck_unavailable'
    return (True, '') if name in target else (False, 'not_in_target')
