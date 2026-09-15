"""达标臂发射面的纯逻辑准入核(自 cw_loop/cw_op_deploy 迁出的单一实现)。

为什么在 kernel:发射面观测(sim/engine_p1 的 LaunchBattle 建模)需要
直调生产 G1 准入判据,而包依赖矩阵(sim 桶不可依 app/operations 桶,
分层纪律,归 review 与代码规范守卫)禁止 sim→cw_loop 直引。本模块只依
kernel(cw_line_defs/cw_state)与 data 注册表,三方消费面(sim 引擎/
cw_loop 调用面/测试)共用同一实现,零第二份。

victim 资格单一源 = offtarget_sell_allowed fenced 臂全条件(判据语义
见其 docstring,自 cw_op_deploy 迁出未改动);cw_op_deploy 保留同名
re-export,既有消费路径(生产 deploy 卖出臂/测试)零迁移。

armed 质量合取(ADR-0570):达标臂判据 = 配方完备(readiness_form_ok)
∧(板面承重满额 ∨ 部署计划不可得 fail-open)——质量维只消费 B_t 通道
承重结构派生量(目标线承重计数/槽位占用/部署计划存在性;承重判定 =
comp 自家核准集 core∪shared ∪ 外部阵营视图,全机制定义量零自由参数),
禁 2★ 计数/装备覆盖/强度评分直入(00 §1 禁战力建模 + P62 form_score
饱和零信息已证);命题与判据资格 = ADR-0570。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_game_state import (
    bench_slots_of,
    deployed_slots_of,
    max_units_of,
)
from sr_od.application.currency_war.kernel.cw_line_defs import (
    ENGINE_FACTIONS as _ENGINE_FENCE,
)
from sr_od.application.currency_war.kernel.cw_line_defs import (
    RECIPE_FACTIONS as _RECIPE,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )
    from sr_od.application.currency_war.kernel.cw_comps import Comp

# 部署围栏集 = RECIPE ∪ ENGINE(桥派生单一源 = cw_line_defs;r357 收口:
# 围栏必须随桥派生集走,局部 frozenset 双源已被 r271 批清退)。
# cw_op_deploy._DEPLOY_FENCE 自本常量别名(消费路径兼容,实现单一)。
DEPLOY_FENCE: frozenset[str] = frozenset(_RECIPE | _ENGINE_FENCE)

# 质量闸观测分键名(单一源;写点 = engine_p1 发射判定位 + cw_loop 达标
# 臂判定位,best-effort 双面 sink,ADR-0570 待标定①载体)——消费面禁
# 字面量散写(三审07轮 C2),键名改这里即全链跟随。
LAUNCH_QUALITY_DEFER_FRAMES_KEY: str = 'launch_quality_defer_frames'
#: 质量评估异常帧分键(fail-open 显影;armed∧quality_eval_error 帧,
# 与「配方不完备」常态帧单义区分,残量禁静默)。
LAUNCH_QUALITY_EVAL_ERROR_KEY: str = 'launch_quality_eval_error'


def offtarget_sell_allowed(char_id: str, bonds: set[str],
                           target_factions: set[str],
                           target_cores: set[str], *,
                           fenced_offline_sellable: bool = False,
                           protect_names: frozenset[str] = frozenset()
                           ) -> bool:
    """W209/ADR-0386:off-target 卖出候选判据(纯函数,锁测试面)。

    run 26 实锤(崩坏根因②):P2 定型后 deploy 侧只按终局 ``target_comp`` 判
    off-target,把买/演进层仍在买入的引擎·配方体系件(仙舟三人组:藿藿×3/
    饮月×2/爻光×1)反复卖出——同期商店 plan 不停 ``Buy(仙舟/...)`` = 买→卖→买
    振荡(两层目标视图分歧:deploy 看终局 comp,买/演进层看意向体系对/骨架纪律)。
    振荡熔断:**引擎/配方体系件(``DEPLOY_FENCE`` = RECIPE ∪ ENGINE,与散牌
    围栏同源)恒不卖**——deploy 自己都把它们当围栏件不许留 bench,卖出判定不得
    同源反向。真要换血走演进层显式 SellDeployed 原子序(有保护集分级,
    ADR-0382;原 CompTransaction 事务载体已随批2b R3 删除),不归 deploy 的机会性腾位通道管。

    换阵卖出义务臂(板满换阵死锁修复;第七局 r9 实证):
    ``fenced_offline_sellable=True`` 时,off-line 的引擎/配方件(**bonds ∌
    target、∉ protect_names**)让位可卖。依据:熔断防的振荡前提 =「买/演进层
    仍在买入该体系件」;线已成型(fp=1.00,单一源 ``cw_comps.form_progress``)
    后买侧对旧线 fenced 件已无需求,保留保护只剩闭死腾位通道的副作用
    (艾丝妲=旧线持续伤害/黑塔被护 → sold 0/2 → RunDeploy 单签名守卫停机)。
    ``protect_names`` = 新线 core∪shared(禁卖护栏不因换阵解除,P41②口径;
    core 件本就被 ``target_cores`` 挡,shared 件经本参显式兜住)。target 单位
    判定(阵营/流派交集)在两臂下都不变。
    """
    if char_id and (char_id in target_cores or char_id in protect_names):
        return False   # core/新线 core∪shared 保留(live 花火误卖根由;P41②)
    if bonds & target_factions:
        return False   # target 单位,保留
    if fenced_offline_sellable:
        return True    # 换阵卖出义务臂:off-line 引擎/配方件让位(线已成型)
    # 引擎/配方体系件恒不卖(W209 振荡熔断,ADR-0386)
    return not (bonds & DEPLOY_FENCE)


def protect_names_of(comp: Comp) -> frozenset[str]:
    """换阵卖出义务臂的保护域(新线禁卖集)= core∪shared∪替班者全集。

    替班者腿依据 = ``Comp.substitute_plan`` 字段契约原文「替班=『不卖、
    转副C沉淀』」(cw_comps)——卖替班者本就违替班语义。仅 core∪shared
    时存在保护域缺口:替班者凭 substitute_plan 直入买面义务集
    (``locked_buy_membership`` → ``_line_hoard``),不经任何羁绊检查,
    可对 comp 整体 off-line 且 fenced(P59 注册表反例:黄泉减益×卡芙卡,
    bonds={持续伤害,星核猎手} ∩ all_factions=∅)→ 义务臂判可卖,同一
    身份 M2 义务买 ↔ 换阵臂卖 = 买↔卖振荡。新增替班者自动入保护域。
    """
    names = set(getattr(comp, 'core_chars', []) or []) \
        | set(getattr(comp, 'shared_chars', []) or [])
    for sub in getattr(comp, 'substitute_plan', None) or []:
        name = sub.get('替班者') if isinstance(sub, dict) else None
        if name:
            names.add(name)
    return frozenset(names)


def readiness_form_ok(bs: GameState | None, comp: Comp | None) -> bool:
    """配方完备判据(form_progress≥1.0;单一源)。

    = comp/state 输入齐备 ∧ ``cw_comps.form_progress(comp, state) >= 1.0``
    ——配方腿语义与 v3_form_ok 镜像写端同式同源(禁各写端内联第二实现);
    消费面 = 镜像族写端(strategies.impl.flow.write_shop_mirrors)与
    :func:`readiness_launch_decision` armed 的配方腿(ADR-0570 起 armed
    在本判据之上叠加质量合取,本函数自身语义零改)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import form_progress
    return (comp is not None and bs is not None
            and form_progress(comp, bs) >= 1.0)


def launch_board_quality_report(bs: GameState, comp: Comp) -> dict:
    """armed 质量维报告(ADR-0570;纯函数,配方完备帧调用)。

    质量判据(零自由参数,两端均机制定义量):

    - ``line_weight``(目标线承重计数)= deployed 非空件中,名字 ∈ comp
      自家核准集(core_chars∪shared_chars——注册表成员名单是结构量:
      白厄类空羁绊单卡/不死途类视图外 shared 件经此计入承重,否则
      comp 自家核心被误判线外恒推迟)或全羁绊(CHARACTERS 注册表
      factions∪flows)∩ ``comp.all_factions`` 非空
      的件数——comp 视图 = 核心∪弹性羁绊(cw_comps.all_factions,
      ADR-0152 口径「弹性羁绊铺板不算 off-target」的板面判定同视图);
      未注册/未识别名按线外计(fail-closed:承重不认)。
    - ``occupied`` = ``cw_state.deployed_occupied``(ADR-0392 槽位占用
      单一源)。承重计数 ≤ 占用数恒成立,判据下限取该平凡上界 ⇒
      ``load_bearing_full`` ⟺ 板面零线外件(线外 = 非核准 ∧ 视图外)。四体系线 comp
      该口径与披露 B_t(kernel ``board_target_line_weight``)同族同源
      ——披露口径本体温测零改(ADR-0535),本报告附 ``b_t_disclosure``
      供判读对账。
    - ``deploy_plan_available`` = kernel ``has_deployable`` 判空(发射×执行契约
      单一源,禁第二套围栏语义)。输入装配取 mandate 部署放行判定同源缺省:
      cap = ``state.max_units()``(装配缺读退 10**6,与放行判定 None 兜底
      同口径)、target = ``comp.factions``(framework carry/locked
      factions 在判据核不可得 → 严格子集,只可能偏「计划不可得」=
      fail-open 方向,不可能造成关闸后无动作的守卫停摆)。

    fail-open 语义(ADR-0570 §判据):线外件在场但部署计划不可得 ⇒
    质量目标不可达帧,降格为配方完备发射(「不可达不关闸」防死锁教义,
    论证与出处 = ADR-0570 §判据/§Considered);推迟帧
    (``defer_by_quality``)必有部署动作在途(计划存在 ⇒ 下环
    RunDeploy 推进换血/填板,P61 族承重单调收敛),金尽稳态由 ADR-0554
    收益耗尽臂兜底(判据与 armed 零耦合)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        board_target_line_weight,
        deployed_bond_counts,
        has_deployable,
    )
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        deployed_occupied,
        iter_occupied_deployed,
    )
    deployed = list(iter_occupied_deployed(deployed_slots_of(bs)))
    view = set(getattr(comp, 'all_factions', None) or [])
    # 自家核准集 = comp 成员名单(core∪shared),注册表制裁的结构量——
    # 空羁绊单卡(白厄)与视图外 shared 件(不死途/布洛妮娅/刃)经此
    # 计入承重,防自家核心被误判线外致该线 armed 恒推迟(落地审 F1)。
    sanctioned = (set(getattr(comp, 'core_chars', None) or [])
                  | set(getattr(comp, 'shared_chars', None) or []))
    line_weight = 0
    for d in deployed:
        name = d.char_id or ''
        if name in sanctioned:
            line_weight += 1
            continue
        ch = CHARACTERS.get(name) if name else None
        if ch is None:
            continue   # 未识别件承重不认(fail-closed)
        if (set(ch.factions) | set(ch.flows)) & view:
            line_weight += 1
    occupied = deployed_occupied(deployed_slots_of(bs))
    cids = {d.char_id for d in deployed if d.char_id}
    try:
        cap = int(max_units_of(bs))
    except Exception:   # noqa: BLE001  cap 缺读 = 放行判定 None 兜底同口径
        cap = 10 ** 6
    plan_available = has_deployable(
        [b for b in bench_slots_of(bs) if b is not None],
        deployed_cids=cids,
        deployed_fac=deployed_bond_counts(cids),
        board=dict(bs.board.value or {}),
        cap=cap,
        target_factions=set(getattr(comp, 'factions', None) or ()),
        target_cores=set(getattr(comp, 'core_chars', None) or ()),
    )
    load_bearing_full = line_weight >= occupied
    return {'load_bearing_full': load_bearing_full,
            'deploy_plan_available': bool(plan_available),
            'line_weight': line_weight, 'occupied': occupied,
            'b_t_disclosure': board_target_line_weight(
                [d.char_id for d in deployed if d.char_id]),
            'defer_by_quality': not load_bearing_full
                                and bool(plan_available)}


def readiness_launch_decision(bs: GameState, comp: Comp | None,
                              *, line_members: Callable[[Comp], set[str]]
                              ) -> dict:
    """达标臂判据核(单一源;sim 决策下沉两小批之①上收,裁决 = ADR-0557;
    armed 质量合取 = ADR-0570)。

    返回 dict:``armed``(发射判据成立 = 配方完备 ``readiness_form_ok``
    ∧〔板面承重满额 ∨ 部署计划不可得 fail-open〕,质量维定义与防死锁
    语义见 :func:`launch_board_quality_report`/ADR-0570——配方腿阈值
    唯一面 = form_progress 语义,质量腿零自由参数)、``auth_basis``
    (触发臂名,与生产 LaunchBattle/LevelUp.auth_basis 观测同键名族)、
    ``admission``(armed 时的 G1 准入三元 = ``launch_admission_report``;
    best-effort:预估异常吞为 None——admission 仅观测位,消费门只读
    armed,见 ADR-0557 §4)、``quality``(配方完备帧的质量维报告;
    None = 配方不完备帧,或质量评估异常的 fail-open 帧——异常帧
    armed 维持配方腿结果,防死锁优先,论证 = ADR-0570 §判据)、
    ``quality_eval_error``(评估异常显影旗:True = quality=None 系
    异常 fail-open 而非配方不完备,消费面经
    ``LAUNCH_QUALITY_EVAL_ERROR_KEY`` 分键落盘,残量禁静默)。

    消费面拓扑(裁决 = ADR-0557,方案三混合):实机 = operations/cw_loop
    备战分支驱动执行(发射核 launch_prepared_battle 留 operations 不动);
    sim = engine_p1 轮入口消费同一输出驱动行为建模(发射帧短路决策段,
    门 = armed 单键)。两面差异全部属执行/观测皮肤,判据语义恰此处一份,
    禁任一消费面内联第二实现(布局守卫 + 测试单一源锁)。armed 关闸帧
    (配方完备 ∧ 质量推迟)的判读观测位 = ``quality.defer_by_quality``。

    :param line_members: 线成员谓词注入参,单一源 =
        strategies.impl.mandate_v1.statefn.predicates.line_members(kernel
        桶禁直引 strategies,由调用方注入同一函数对象——与
        launch_admission_report 同契约)。
    """
    armed = readiness_form_ok(bs, comp)
    quality = None
    quality_eval_error = False
    admission = None
    if armed:
        try:
            quality = launch_board_quality_report(bs, comp)
        except Exception:   # noqa: BLE001  质量评估异常 fail-open(算不出
            # 不关闸,防死锁优先;论证 = ADR-0570 §判据 fail-open 分界)
            quality = None
            # 异常显影旗(残量禁静默,ADR-0566 口径):quality=None 兼有
            # 「配方不完备」常态义,异常帧经本旗与消费面分键单义区分。
            quality_eval_error = True
        armed = True if quality is None else (
            quality['load_bearing_full']
            or not quality['deploy_plan_available'])
    if armed:
        try:
            admission = launch_admission_report(
                bs, comp, line_members=line_members)
        except Exception:   # noqa: BLE001  准入预估 best-effort(观测不炸)
            admission = None
    return {'armed': armed, 'auth_basis': 'readiness_form_ok',
            'admission': admission, 'quality': quality,
            'quality_eval_error': quality_eval_error}


def launch_admission_report(bs: GameState, comp: Comp, *,
                            line_members: Callable[[Comp], set[str]]) -> dict:
    """达标臂 G1 准入预估(§9.2 准入三元 + victim 收口,发射面显影用)。

    返回 dict(全 bool):``board_full``(三元①板满:占用部署数 ≥ 可上阵
    数 ``state.max_units()``;旧口径 = 物理槽位总数 DEPLOYED_CAPACITY,level 驱动 cap 全域
    <10 ⇒ 该分键结构性不显影;换占用数 vs max_units 与 swap 臂同一裁决
    先例(禁物理门),feed 单一源 = deployed_occupied)、``bench_core_waiting``(三元②:bench 存在线内
    待上场件——口径 = core∪shared(line_members)∨ 阵营交集,
    与买入/部署义务面对齐)、``victim_missing``(三元③:板上无合格
    victim)。

    victim 资格单一源 = offtarget_sell_allowed fenced 臂全条件(off-line
    ∧ 围栏 ∧ 非保护域,保护域 = core∪shared∪替班者),与执行侧
    _sell_offtarget_deployed 同款;**不附 1★ 全退门**——执行侧 swap 卖出
    无退款资格前置,提案侧多一道门只会造成 victim_missing 误显影。
    提案侧预估基于期望态现读;执行时刻以 CwScreenDeploy 现读重建为准。
    三元不全/victim 缺失**只显影不拦截**(出战优先;准入是观测面,
    非第二道闸)。

    :param line_members: 线成员谓词(注入参;单一源 =
        strategies.impl.mandate_v1.statefn.predicates.line_members——
        本模块在 kernel 桶,包依赖矩阵禁 kernel→strategies 直引,由
        调用方注入同一函数对象,禁各调用面自写第二实现)。
    """
    from sr_od.application.currency_war.data.cw_chars import get_char
    from sr_od.application.currency_war.kernel.cw_exec_state import deployed_occupied
    # 裸过滤债(ADR-0557 既有代码):内联 None 过滤未收敛到 deployed 迭代
    # 单一源 iter_occupied_deployed(同模块 launch_board_quality_report
    # 同型位已收敛);纯注记申报,收敛属行为面另行批次处置。
    deployed = [d for d in deployed_slots_of(bs) if d is not None]
    bench = [b for b in bench_slots_of(bs) if b is not None]
    cores = set(getattr(comp, 'core_chars', []) or [])
    line = set(line_members(comp))
    protect = protect_names_of(comp)
    t_factions = set(getattr(comp, 'all_factions', []) or [])
    # 板满口径 = 占用数 vs max_units(与 swap 臂同裁决:禁物理槽位门);
    # cap 缺读 = 质量闸兜底同口径(不显影板满)。
    try:
        _cap = int(max_units_of(bs))
    except Exception:   # noqa: BLE001  cap 缺读 = 放行判定 None 兜底同口径
        _cap = 10 ** 6
    board_full = deployed_occupied(deployed_slots_of(bs)) >= _cap
    bench_core_waiting = False
    for b in bench:
        name = b.char_id or ''
        if name in line:
            bench_core_waiting = True
            break
        ch = get_char(name)
        if ch is not None and (set(ch.factions) | set(ch.flows)) & t_factions:
            bench_core_waiting = True
            break
    victim_missing = True
    for d in deployed:
        name = d.char_id or ''
        if not name or name in cores or name in protect:
            continue
        ch = get_char(name)
        if ch is None:
            continue
        bonds = set(ch.factions) | set(ch.flows)
        if not offtarget_sell_allowed(name, bonds, t_factions, cores,
                                      fenced_offline_sellable=True,
                                      protect_names=protect):
            continue
        victim_missing = False
        break
    return {'board_full': board_full, 'bench_core_waiting': bench_core_waiting,
            'victim_missing': victim_missing}
