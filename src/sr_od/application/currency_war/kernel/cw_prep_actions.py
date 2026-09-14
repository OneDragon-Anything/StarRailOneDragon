"""货币战争 备战决策环 统一观察视图 + 点球挑选 kernel(kernel 桶)。

本模块原为族B 备战动作词表宿主(PrepAction 动作全集 + PREP_ACTION_TYPES +
action_key);统一词表归一(unified-action-factory 批2b)后动作词表退役,
单一真相源 = :mod:`kernel.cw_vocab`(基类 ``CwAction`` + 全动作类 +
``CW_ACTION_TYPES`` + ``action_key``)。现役居民 = 决策单一输入的统一观察
视图 :class:`PrepObservation` 与点球挑选 kernel 纯函数
(:func:`select_sphere_clicks` + ``SPHERE_CLICK_HARD_CAP``)。

为何落在 kernel:观察视图由决策核(策略)与执行层(app)共同消费,任一侧
定义都会造成另一侧的反向依赖(分包依赖矩阵 §3.2:decision 只可依
kernel/data;app 依一切)——共享视图归 kernel 是唯一同时满足两侧的方向。
纯 dataclass + 纯函数,零副作用、零识别/执行逻辑——「执行一个动作」在
app/prep_actions.py 的 PrepActionExecutor,「产出动作」在策略层
CwStrategy.decide_prep_screen 决策接口。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.kernel.cw_exec_state import BenchChar

#: 点球单批硬上限(原执行器 SPHERE_MAX_CLICKS 常量迁居 kernel:挑选上界
#: 归挑选函数,执行器只机械点载荷;防识别抖动死循环的防线语义不变)。
SPHERE_CLICK_HARD_CAP: int = 12


def select_sphere_clicks(spheres: list, cap: int,
                         ) -> tuple[tuple[int, int], ...]:
    """奖励球挑选 kernel 单一源(R4 ClickSpheres 改形;纯函数)。

    输入 = ``PrepObservation.spheres``([(color, Point, r)];颜色与半径
    仅排序消费,不进载荷);``cap`` = 本批点击预算(发射位常量,如
    mandate_v1 SPHERE_CLICK_BATCH_MAX_K)。输出 = 有序 (x, y) 点击列——
    大球优先(r 降序;稳定排序保持观察序),上界 = min(cap, 硬上限
    SPHERE_CLICK_HARD_CAP)。席满让路门/占席球语义归发射位(既有门),
    本函数不辖。

    消费面:发射位(mandate_v1 entry)构造 ClickSpheres 载荷;执行器
    零排序零截断纯机械点(第二实现禁)。
    """
    budget = max(0, min(int(cap), SPHERE_CLICK_HARD_CAP))
    ordered = sorted(spheres, key=lambda t: t[2], reverse=True)[:budget]
    return tuple((int(p.x), int(p.y)) for _c, p, _r in ordered)


@dataclass
class PrepObservation:
    """备战决策环统一观察(决策单一输入,组合现成 reader 不新写识别)。

    P1 恒空字段(策略不得依赖):overlay_state / overlay_options / shop_cards。
    (owned_equips 原列本清单,已随 P4 观察接线转正——见下方装备域字段块。)

    分层语义:bench_chars/deployed_chars/deploy_vacancy 只在 heavy
    观察刷新(环入口 + 每个执行过的游戏动作后);light 步沿用上次 heavy 值(可能 stale,
    单线程内 stale 窗口 = 无动作步,安全)。轻字段(spheres/boxes/占用/shop_open/overlay)
    每步现读。
    局内事实不在帧上(容器化段 2:state 槽退役,黑板帧 = 纯视觉/占用
    观察载体,帧保留域封闭清单见设计件 §2.1-2;决策读 = session 容器
    单例 board_state_of,同帧同视图纪律)。
    state_gold_trusted = gold 仅 shop 开态可信(F2 门,heavy 刷新)。
    """
    state_gold_trusted: bool = False      # gold 是否可信(= heavy 时 shop 开)
    # 子态可读性(observe_full 产出;heavy 刷新/
    # light 沿用)——node_seq/shop_cards 本帧是否可读(按子态
    # 尽力读,跨步拼装全面性)。
    substate: dict = field(default_factory=dict)
    bench_chars: list[BenchChar] = field(default_factory=list)   # heavy: SIFT 身份
    deployed_chars: list[BenchChar] = field(default_factory=list)
    spheres: list = field(default_factory=list)       # read_reward_spheres [(color, Point, r)]
    boxes: list = field(default_factory=list)         # read_supply_boxes [(slot, Point)]
    tomes: list = field(default_factory=list)         # read_tomes [(slot, Point)] 秘密典籍
    free_bench_slots: int = 0           # 9 − 占用(角色+箱都占席;CV 每步现读)
    deploy_vacancy: int = 0             # deploy_cap − deployed_count(heavy 刷新)
    deploy_divergent: bool = False      # vacancy 分母双源分歧位(15 号稿批 C:
                                        # True=deployed 计数取的是低值仲裁,
                                        # 部署放行判定按 §4.2 延迟;准备面载体)
    deploy_stale: bool = False          # vacancy 陈旧位(True=缓存沿用:
                                        # cap/paddle 双缺,B5 陈旧值过门申报)
    shop_open: bool = False             # 锚点「按钮-收起」可见(每步现读)
    front_occupied: set = field(default_factory=set)  # 前排占用物理槽位号(每步现读)
    back_occupied: set = field(default_factory=set)
    front_size: int = 4
    # (back_size 字段已删(波 5b 死字段退役,写读闭环终端消费者零;决策链
    #  后排容量单一源 = 容器 back_capacity_of)。)
    overlay_state: str | None = None    # P5
    # 事件 overlay 检测(盛会之星/选择伙伴/祈愿试炼 —— 挡操作,检测到即
    # 交回外循环分支 handler;实锤:盛会之星 overlay 下 deploy 全灭 → 空场 HP 82→1)
    event_overlay: str | None = None
    overlay_options: list | None = None # P5
    shop_cards: list | None = None      # P1 恒 None(仅买牌阶段刷新)
    # ===== 装备域三路事实 P4 观察接线(ADR-0601 §3-C1 演进方向,T-171)=====
    # 采集点 = observe_full heavy 装配层(obs 域统一采集单一源);deployed
    # 名单已由上方 deployed_chars 覆盖,此三字段补 owned/occupied 两路。
    # None = 识别域资源未就绪(模板库/区域/TM grays 缺,原因在采集层
    # log 留证),消费方按各自 fail/保守通道处理;[]/{} = 真读到空。
    owned_equips: list | None = None     # 装备区 owned 件名池(全量含工具,W209g 口径;heavy 刷新)
    # occupied_equips 键坐标系:row ∈ 'front'|'back',slot = 画面物理槽位
    # 1-based(前排 1-4 / 后排 1-选档 N;执行域槽位语义,与机械动作参数
    # 字段同域);取值时机 = 生成期快照(heavy 帧现读)。
    occupied_equips: dict | None = None  # 已穿装备明细 {(row, 物理槽位): [件名]}
    # 消费 = 装备计划步后排槽位戳记上界(执行域)。决策链后排容量单一源
    # 仍 = 容器 back_capacity_of,勿回接本字段(波 5b 删除的 back_size 是
    # 决策链死字段;本字段是执行域戳记消费,两者不同源不互通)。
    back_layout_slots: int | None = None  # 后排布局选档槽数(select_back_layout 直传;None=布局未知态双弃权帧)
