"""金路径观察生成器 + 档名注册表(sim 统一迭代 flow-seam 详设 §3)。

生成器 = 「sim 世界 → 屏契约观察产物」的直译:从世界真值(容器
``GameState`` + 后端画面状态机运行时)填 ``CwScreenXxxObs`` 结构体,
零截图零识别。**写通道铁律**:产物必须经 ``kernel/cw_screen_report/``
同名上报函数落容器(与实机观察上报同一条写通道);观察口径(字段
映射/归一化/缺省语义)单一源在 report 消费端,生成器只产数据。

**注册表键 = screen_info 档名(唯一)**;子态不设独立键——同档名子态
(晶矿子态 / wait_one_one 变体 / 整店锁)由该档名生成器按状态机子态
内部分派出对应观察产物。金路径档名清单 13 档(权威 =
``flow-seam.md`` §3):备战(含晶矿子态、wait_one_one 变体)、商店、
battle_wait(战斗结算窗)、补给、投资环境、投资策略、简报、boss 简报、
位面过渡、遭遇、开箱、巨星、planner。**非金路径屏不出注册表**:
后端状态机呈现未注册屏时 ``observe`` = :class:`LookupError` 具名响错
(防静默失真——sim 不会走到的屏出现观察请求 = 接线 bug 或辖域外屏,
响亮暴露而非产空产物)。

合成坐标约定:实机观察产物里的点击坐标(x/y 中心等)在 sim 世界无
画面语义,生成器以「下标派生的合成值」填充(身份键用途,同后端呈现
写点 ``(i+1)*10`` 形);决策面只消费名字/选项载荷,不消费坐标。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PrepObservation,
)
from sr_od.application.currency_war.kernel.cw_screen_report.battle_wait import (
    CwScreenBattleWaitObs,
    report_screen_battle_wait_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.boss_briefing import (
    CwScreenBossBriefingObs,
    report_screen_boss_briefing_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.box_pick import (
    CwScreenBoxPickObs,
    report_screen_box_pick_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.briefing import (
    CwScreenBriefingObs,
    report_screen_briefing_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.encounter import (
    CwScreenEncounterObs,
    report_screen_encounter_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.invest_env import (
    CwScreenInvestEnvObs,
    report_screen_invest_env_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.invest_strategy import (
    CwScreenInvestStrategyObs,
    report_screen_invest_strategy_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.megastar import (
    CwScreenMegastarObs,
    report_screen_megastar_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.plane_transition import (
    CwScreenPlaneTransitionObs,
    report_screen_plane_transition_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.planner import (
    CwScreenPlannerObs,
    report_screen_planner_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.prep import (
    CwScreenPrepObs,
    report_screen_prep_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.shop import (
    CwScreenShopObs,
    report_screen_shop_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.supply_node import (
    CwScreenSupplyNodeObs,
    report_screen_supply_node_obs,
)
from sr_od.application.currency_war.sim.cw_sim_backend import (
    PREP_SUB_ORE,
    PREP_SUB_WAIT_ONE_ONE,
    SCREEN_BOSS_BRIEFING,
    SCREEN_BOX,
    SCREEN_BRIEFING,
    SCREEN_ENCOUNTER,
    SCREEN_INVEST_ENV,
    SCREEN_INVEST_STRATEGY,
    SCREEN_MEGASTAR,
    SCREEN_PLANE_TRANSITION,
    SCREEN_PLANNER,
    SCREEN_PREP,
    SCREEN_SETTLE,
    SCREEN_SHOP,
    SCREEN_SUPPLY,
    SimBackend,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )

    _GenFn = Callable[[SimBackend], object]
    _ReportFn = Callable[[GameState, object], None]

#: 金路径档名清单(flow-seam.md §3 权威清单的代码镜像;
#: 注册表覆盖核对测试消费 = 清单逐行有生成器)。
GOLDEN_PATH_SCREEN_NAMES: tuple[str, ...] = (
    SCREEN_PREP,              # 备战(含晶矿子态、wait_one_one 变体)
    SCREEN_SHOP,              # 商店
    SCREEN_SETTLE,            # battle_wait(sim 战斗窗口呈现屏 = 结算页)
    SCREEN_SUPPLY,            # 补给
    SCREEN_INVEST_ENV,        # 投资环境
    SCREEN_INVEST_STRATEGY,   # 投资策略
    SCREEN_BRIEFING,          # 简报
    SCREEN_BOSS_BRIEFING,     # boss 简报
    SCREEN_PLANE_TRANSITION,  # 位面过渡
    SCREEN_ENCOUNTER,         # 遭遇
    SCREEN_BOX,               # 开箱(武装箱选择)
    SCREEN_MEGASTAR,          # 巨星
    SCREEN_PLANNER,           # planner
)


# ============================================================ 生成器群
# (逐屏一函数:世界真值 → CwScreenXxxObs;screen 识别域载体恒 None
#  ——sim 无帧,消费面禁读该域。)


def _node_pos_or_default(backend: SimBackend) -> tuple[int, int, str]:
    """节点 (位面, 轮, 类型) 读口(容器 gs.node 单一源;未进窗 = (1,1,'')。"""
    node = backend.gs.node.value
    if node is None:
        return 1, 1, ''
    return node.plane, node.round_num, node.kind


def gen_prep(backend: SimBackend) -> CwScreenPrepObs:
    """备战档生成器(晶矿子态 / wait_one_one 变体按 ``_sub`` 内部分派)。

    - 控制信号(flow-seam §3:状态机已知商店开合与 overlay 呈现态):
      ``shop_open`` = 商店模态在场(状态机真值,观察备战时恒 False——
      模态在场则档名为开商店,非本生成器辖);``event_overlay`` = overlay
      呈现态(同理由,备战档在场 = 无 overlay 压顶,恒 None);
      ``substate`` = 备战子态可读性标注(ore / wait_one_one / 常规)。
    - ``front_occupied``/``back_occupied`` = live 观察链的识别对拍轻
      字段(方法内即弃消费),sim 产物不挂(零识别面)。
    - ``node_path_chain`` = None 诚实缺位:节点行读 = 实机画面识别域,
      sim 世界无此识别面(链 diff 治理消费面随联调批申报)。
    """
    sub = backend._sub
    if sub == PREP_SUB_WAIT_ONE_ONE:
        readable_sub = 'wait_one_one'
    elif sub == PREP_SUB_ORE:
        readable_sub = 'ore'
    else:
        readable_sub = 'prep'
    prep = PrepObservation(
        substate={'sub': readable_sub},
        shop_open=(backend._screen == SCREEN_SHOP),
        event_overlay=None,
    )
    return CwScreenPrepObs(prep=prep, event_overlay=None, node_path_chain=None)


def gen_shop(backend: SimBackend) -> CwScreenShopObs:
    """商店档生成器(入口回执镜像域,容器真值直填)。

    gold/hp/level/board 全部容器现值;``shop`` = 容器 ShopPayload.cards
    (遗留读牌列表形态的 sim 承载,kind 三态槽直透);``*_readable``/
    ``hp_trusted`` = True(sim 容器即世界真值,无 OCR 失读维度);plane/
    round/node_type 自容器节点键。
    """
    gs = backend.gs
    plane, round_num, node_kind = _node_pos_or_default(backend)
    hp = gs.hp.value
    level = gs.level.value
    payload = gs.shop.value
    return CwScreenShopObs(
        gold=int(gs.gold.value or 0),
        gold_readable=True,
        hp=(int(hp) if hp is not None else None),
        hp_readable=hp is not None,
        hp_trusted=hp is not None,
        level=(int(level) if level is not None else 1),
        level_readable=level is not None,
        plane=plane,
        round_num=round_num,
        node_type=(node_kind or None),
        board=dict(gs.board.value or {}),
        shop=(list(payload.cards) if payload is not None else []),
    )


def gen_battle_wait(backend: SimBackend) -> CwScreenBattleWaitObs:
    """战斗结算窗生成器(battle_wait;sim 结算瞬时完成,呈现即在场)。"""
    return CwScreenBattleWaitObs(on_screen=True)


def gen_supply(backend: SimBackend) -> CwScreenSupplyNodeObs:
    """补给档生成器(选项载荷 + 刷新剩余自容器呈现写点回读)。"""
    gs = backend.gs
    payload = gs.supply.value
    left = gs.supply_refresh_left.value
    return CwScreenSupplyNodeObs(
        in_node=True,
        options=list(payload.options) if payload is not None else [],
        refresh_left=(int(left) if left is not None else None),
    )


def gen_invest_env(backend: SimBackend) -> CwScreenInvestEnvObs:
    """投资环境档生成器(候选名自容器 opts 槽;x = 下标派生合成值)。"""
    names = list(backend.gs.invest_env_opts.value or [])
    return CwScreenInvestEnvObs(
        hit=True,
        options=[(n, (i + 1) * 10) for i, n in enumerate(names)],
        refresh=None,   # 环境刷新剩余 = sim 未建模呈现面,诚实缺位(report 跳写)
    )


def gen_invest_strategy(backend: SimBackend) -> CwScreenInvestStrategyObs:
    """投资策略档生成器(候选名自容器 opts 槽;逐卡刷新剩余 = sim 未
    建模呈现面,refresh_slots 空 → report 逐槽跳写,容器留旧值)。"""
    names = list(backend.gs.invest_strategy_opts.value or [])
    return CwScreenInvestStrategyObs(
        entry_ok=True,
        options=[(n, (i + 1) * 10, 10) for i, n in enumerate(names)],
        refresh_slots=[],
    )


def gen_briefing(backend: SimBackend) -> CwScreenBriefingObs:
    """简报档生成器(三读数自容器:词缀/位面序 boss/敌人难度;开局
    采样写点 = 后端 reset,report 恒覆写语义对同值幂等)。"""
    gs = backend.gs
    bosses = gs.plane_bosses.value
    diff = gs.enemy_difficulty.value
    return CwScreenBriefingObs(
        on_screen=True,
        enemy_affixes=list(gs.enemy_affixes.value or []),
        plane_bosses=(list(bosses) if bosses is not None else None),
        enemy_difficulty=(int(diff) if diff is not None else None),
    )


def gen_boss_briefing(backend: SimBackend) -> CwScreenBossBriefingObs:
    """boss 简报档生成器(门判定即可;report 半部 = boss 类型直定)。"""
    return CwScreenBossBriefingObs(on_screen=True)


def gen_plane_transition(backend: SimBackend) -> CwScreenPlaneTransitionObs:
    """位面过渡档生成器(链值诚实缺位:底部全亮行读 = 实机识别域,
    sim 不产链观察 → report 按「chain 缺不写」防御语义零写)。"""
    return CwScreenPlaneTransitionObs(on_screen=True, chain=None)


def gen_encounter(backend: SimBackend) -> CwScreenEncounterObs:
    """遭遇档生成器(档位候选自容器呈现写点回读;刷新剩余 = sim 未
    建模呈现面,诚实缺位)。"""
    gs = backend.gs
    payload = gs.encounter.value
    left = gs.encounter_refresh_left.value
    return CwScreenEncounterObs(
        options=list(payload.options) if payload is not None else [],
        refresh_left=(int(left) if left is not None else None),
    )


def gen_box(backend: SimBackend) -> CwScreenBoxPickObs:
    """武装箱档生成器(候选名 + 点击点自容器呈现写点回读;同序等长
    守卫在 report 写端,sim 产物同受约束)。"""
    gs = backend.gs
    names = list(gs.box_card_names.value or [])
    points = list(gs.box_card_names_xy.value or [])
    return CwScreenBoxPickObs(on_screen=True, card_names=names, points=points)


def gen_megastar(backend: SimBackend) -> CwScreenMegastarObs:
    """巨星档生成器(候选自容器呈现写点回读;含 sim 合成坐标 xy)。"""
    return CwScreenMegastarObs(
        in_node=True,
        options=list(backend.gs.megastar_opts.value or []),
    )


def gen_planner(backend: SimBackend) -> CwScreenPlannerObs:
    """planner 档生成器(两卡选项自容器;呈现写点缺位 = 空桶照写,
    与实机「恒写两卡 OCR 桶」空桶语义同形)。"""
    return CwScreenPlannerObs(
        on_screen=True,
        options=list(backend.gs.planner_opts.value or []),
    )


# ============================================================ 注册表

#: 档名 → (生成器, 同名上报函数)。(生成器只产数据,落容器 =
#: 上报函数单一源;两者成对注册 = 写通道铁律的注册表形态。)
_REGISTRY: dict[str, tuple[Callable[[SimBackend], object],
                           Callable[[object, object], None]]] = {
    SCREEN_PREP: (gen_prep, report_screen_prep_obs),
    SCREEN_SHOP: (gen_shop, report_screen_shop_obs),
    SCREEN_SETTLE: (gen_battle_wait, report_screen_battle_wait_obs),
    SCREEN_SUPPLY: (gen_supply, report_screen_supply_node_obs),
    SCREEN_INVEST_ENV: (gen_invest_env, report_screen_invest_env_obs),
    SCREEN_INVEST_STRATEGY: (gen_invest_strategy,
                             report_screen_invest_strategy_obs),
    SCREEN_BRIEFING: (gen_briefing, report_screen_briefing_obs),
    SCREEN_BOSS_BRIEFING: (gen_boss_briefing,
                           report_screen_boss_briefing_obs),
    SCREEN_PLANE_TRANSITION: (gen_plane_transition,
                              report_screen_plane_transition_obs),
    SCREEN_ENCOUNTER: (gen_encounter, report_screen_encounter_obs),
    SCREEN_BOX: (gen_box, report_screen_box_pick_obs),
    SCREEN_MEGASTAR: (gen_megastar, report_screen_megastar_obs),
    SCREEN_PLANNER: (gen_planner, report_screen_planner_obs),
}


def registered_screens() -> tuple[str, ...]:
    """已注册档名集(清单覆盖核对消费)。"""
    return tuple(_REGISTRY)


def observe_screen(backend: SimBackend, screen_name: str) -> object:
    """注册表分派:档名 → 生成器产物经同名上报函数落容器并返回。

    未注册档名 = :class:`LookupError` 具名响错(状态机呈现未注册屏 =
    sim 辖域外/接线 bug,防静默失真;flow-seam §3 锁)。判定基准 =
    注册表键集,非「当前呈现屏匹配」——观察请求与呈现屏错位由流程侧
    visible 门承接(且 wait_one_one 惰性完成会在问询间隙合法翻屏,
    身份断言会误伤)。
    """
    entry = _REGISTRY.get(screen_name)
    if entry is None:
        raise LookupError(
            f'sim 观察生成器未注册: {screen_name!r}'
            '(金路径 13 档名清单外 = 状态机不应呈现该屏或观察点接线错;'
            '防静默失真响错,flow-seam §3)')
    gen, report = entry
    obs = gen(backend)
    report(backend.gs, obs)
    return obs
