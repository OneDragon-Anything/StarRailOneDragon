"""达标分支动作发出面的纯逻辑准入核(单一实现)。

单一实现居 kernel(只依 kernel(cw_line_defs/cw_state)与 data 注册表):
消费面(生产 cw_loop 调用面/测试)共用,零第二份。

出战就绪质量合取:达标分支判据 = 配方完备(readiness_form_ok)
∧(板面支撑满额 ∨ 部署差分不在途 fail-open)——质量维只消费 B_t 通道
支撑结构派生量(目标线支撑计数/槽位占用/部署差分在途;支撑判定 =
阵容自家核准集 core∪shared ∪ 外部阵营视图,全机制定义量零自由参数),
禁 2★ 计数/装备覆盖/强度评分直入(00 §1 禁战力建模 + P62 form_score
饱和零信息已证)。

部署差分在途谓词(``deploy_pending_fn`` 注入;部署统一批丁换语义,原
``has_deployable`` 七桶判空退役——unified-deploy-order §4 发射抑制谓词
行):语义 = 统一部署搜索定型 + 差分执行器对当前容器 **diff 非空**
(还有部署动作在途 → 质量推迟帧让部署收敛);注入实现在策略层
deploy_plan(``launch_deploy_pending`` 族,含推判重放的虚拟面板路径,
kernel 层禁 strategies 直引的依赖倒置契约同 line_members)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_game_state import (
    deployed_rows_of,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )

# 质量闸观测分键名(单一源;写点 = cw_loop 达标
# 分支判定位,best-effort sink,待标定①载体)——消费面禁
# 字面量散写(三审07轮 C2),键名改这里即全链跟随。
LAUNCH_QUALITY_DEFER_FRAMES_KEY: str = 'launch_quality_defer_frames'
#: 质量评估异常帧分键(fail-open 暴露;出战就绪∧quality_eval_error 帧,
#: 与「配方不完备」常态帧单义区分,残量禁静默)。
LAUNCH_QUALITY_EVAL_ERROR_KEY: str = 'launch_quality_eval_error'


def readiness_form_ok(gs: GameState | None, comp: Comp | None) -> bool:
    """配方完备判据(form_progress≥1.0;单一源)。

    = 阵容/state 输入齐备 ∧ ``cw_comps.form_progress(阵容, state) >= 1.0``
    ——配方分支语义与 v3_form_ok 镜像写端同式同源(禁各写端内联第二实现);
    消费面 = 镜像族写端(strategies.impl.flow.write_shop_mirrors)与
    :func:`readiness_launch_decision` 出战就绪的配方分支(起 出战就绪
    在本判据之上叠加质量合取,本函数自身语义零改)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import form_progress
    return (comp is not None and gs is not None
            and form_progress(comp, gs) >= 1.0)


def launch_board_quality_report(gs: GameState, comp: Comp, *,
                                deploy_pending_fn: Callable[[GameState], bool]
                                ) -> dict:
    """出战就绪质量维报告(纯函数,配方完备帧调用)。

    质量判据(零自由参数,两端均机制定义量):

    - ``line_weight``(目标线支撑计数)= deployed 非空件中,名字 ∈ 阵容
      自家核准集(core_chars∪shared_chars——注册表成员名单是结构量:
      白厄类空羁绊单卡/不死途类视图外 shared 件经此计入支撑,否则
      阵容自家核心被误判线外恒推迟)或全羁绊(CHARACTERS 注册表
      factions∪flows)∩ ``comp.all_factions`` 非空
      的件数——阵容视图 = 核心∪弹性羁绊(cw_comps.all_factions,
      口径「弹性羁绊铺板不算 off-target」的板面判定同视图);
      未注册/未识别名按线外计(fail-closed:支撑不认)。
    - ``occupied`` = 容器占用数(占用判定 = 元素非 None 计 1;P4 容器形,
      行域本身即紧凑占用序,含未识别占位单位)。支撑计数 ≤ 占用数恒成立,
      判据下限取该平凡上界 ⇒
      ``load_bearing_full`` ⟺ 板面零线外件(线外 = 非核准 ∧ 视图外)。
    - ``deploy_pending`` = 注入的部署差分在途谓词(单一源 =
      mandate_v1 deploy_plan.launch_deploy_pending 族;kernel 层禁
      strategies 直引,由调用方注入同一函数对象——依赖倒置契约同
      line_members)。

    fail-open 语义:线外件在场但部署差分不在途 ⇒
    质量目标不可达帧,降格为配方完备发出(「不可达不关闸」防死锁教义);
    推迟帧
    (``defer_by_quality``)必有部署动作在途(差分非空 ⇒ 下环
    统一拖动序推进换人/填板;换人触发有限性载体 = 统一部署搜索
    定型的稳定键/rng 局面哈希播种,unified-deploy-order §1),金尽稳态由
    收益耗尽分支兜底(判据与 出战就绪零耦合)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    front, back = deployed_rows_of(gs)
    deployed = [d for d in (*front, *back) if d is not None]
    view = set(getattr(comp, 'all_factions', None) or [])
    # 自家核准集 = 阵容成员名单(core∪shared),注册表制裁的结构量——
    # 空羁绊单卡(白厄)与视图外 shared 件(不死途/布洛妮娅/刃)经此
    # 计入支撑,防自家核心被误判线外致该线 出战就绪恒推迟。
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
            continue   # 未识别件支撑不认(fail-closed)
        if (set(ch.factions) | set(ch.flows)) & view:
            line_weight += 1
    occupied = len(deployed)
    plan_available = bool(deploy_pending_fn(gs))
    load_bearing_full = line_weight >= occupied
    return {'load_bearing_full': load_bearing_full,
            'deploy_plan_available': plan_available,
            'line_weight': line_weight, 'occupied': occupied,
            'defer_by_quality': not load_bearing_full
                                and plan_available}


def readiness_launch_decision(gs: GameState, comp: Comp | None,
                              *, line_members: Callable[[Comp], set[str]],
                              deploy_pending_fn: Callable[[GameState], bool]
                              ) -> dict:
    """达标分支判据核(单一源;sim 决策下沉两小批之①上收;
    出战就绪质量合取见行内申报)。

    返回 dict:``armed``(发出判据成立 = 配方完备 ``readiness_form_ok``
    ∧〔板面支撑满额 ∨ 部署差分不在途 fail-open〕,质量维定义与防死锁
    语义见 :func:`launch_board_quality_report`)、``auth_basis``
    (触发分支名,与生产 LaunchBattle/CwActionLevelUpParam.auth_basis 观测同键名族)、
    ``quality``(配方完备帧的质量维报告;
    None = 配方不完备帧,或质量评估异常的 fail-open 帧——异常帧
    出战就绪维持配方分支结果,防死锁优先)、
    ``quality_eval_error``(评估异常暴露旗:True = quality=None 系
    异常 fail-open 而非配方不完备,消费面经
    ``LAUNCH_QUALITY_EVAL_ERROR_KEY`` 分键落盘,残量禁静默)。

    消费面拓扑(方案三混合):实机 = operations/cw_loop
    备战分支驱动执行(动作发出核 launch_prepared_battle 留 operations 不动);
    判据语义恰此处一份,
    禁任一消费面内联第二实现(布局守卫 + 测试单一源)。出战就绪关闸帧
    (配方完备 ∧ 质量推迟)的判读观测位 = ``quality.defer_by_quality``。

    :param line_members: 线成员谓词注入参,单一源 =
        strategies.impl.mandate_v1.statefn.predicates.line_members(kernel
        桶禁直引 strategies,由调用方注入同一函数对象——与
        ``readiness_form_ok`` 消费面同契约)。
    :param deploy_pending_fn: 部署差分在途谓词注入参,单一源 =
        strategies.impl.mandate_v1.deploy_plan.launch_deploy_pending 族
        (kernel 层禁直引 strategies,由调用方注入同一函数对象——依赖
        倒置契约同 line_members;语义 = 统一部署搜索定型 + 差分非空,
        推判重放经 ``launch_deploy_pending_virtual`` 同族注入)。
    """
    armed = readiness_form_ok(gs, comp)
    quality = None
    quality_eval_error = False
    if armed:
        try:
            quality = launch_board_quality_report(
                gs, comp, deploy_pending_fn=deploy_pending_fn)
        except Exception:   # noqa: BLE001  质量评估异常 fail-open(算不出
            # 不关闸,防死锁优先)
            quality = None
            # 异常暴露旗(残量禁静默,口径):quality=None 兼有
            # 「配方不完备」常态义,异常帧经本旗与消费面分键单义区分。
            quality_eval_error = True
        armed = True if quality is None else (
            quality['load_bearing_full']
            or not quality['deploy_plan_available'])
    return {'armed': armed, 'auth_basis': 'readiness_form_ok',
            'quality': quality,
            'quality_eval_error': quality_eval_error}


# (G1 准入预估 launch_admission_report(victim 三元:board_full/bench_
#  core_waiting/victim_missing)与 victim 资格单一源 offtarget_sell_allowed/
#  protect_names_of、部署围栏 DEPLOY_FENCE(振荡熔断份)已随部署统一批
#  丁收编删除:统一部署搜索下板满帧 bench core 经交换交互上场,「无合格
#  victim → 出战无腾位」形态结构性不存在,消费位(cw_loop 达标臂 G1
#  预估块)同批删除——unified-deploy-order §2.7/§4;部署在途观测改由
#  质量维 deploy_pending 承载。)
