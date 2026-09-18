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

from one_dragon.base.geometry.point import Point

#: 点球单批硬上限(原执行器 SPHERE_MAX_CLICKS 常量迁居 kernel:挑选上界
#: 归挑选函数,执行器只机械点载荷;防识别抖动死循环的防线语义不变)。
SPHERE_CLICK_HARD_CAP: int = 12


def sphere_click_targets_of(gs) -> list[tuple[str, Point, int]]:
    """奖励球点击目标读口(容器 spheres 域 → select_sphere_clicks 消费
    形态;迭代 2026-09-18-prep-obs-retirement 阶段 3.4 立口)。

    SphereSight.points((color, x, y, r) 平铺元组)还原为
    ``[(color, Point, r)]``——与旧黑板 ``obs.spheres`` 产物形态逐位同构
    (read_reward_spheres 消费契约),调用方签名零改动。域未观察(None)
    = 空列(未观察 ≠ 有球,宁不点;与「点空由下一入口观察回补」机制
    配对)。
    """
    from one_dragon.base.geometry.point import Point

    view = gs.spheres.value if gs is not None else None
    if view is None or not view.points:
        return []
    return [(color, Point(x, y), r)
            for color, x, y, r in view.points]


def select_sphere_clicks(spheres: list, cap: int,
                         ) -> tuple[tuple[int, int], ...]:
    """奖励球挑选 kernel 单一源(R4 CwActionClickSpheresParam 改形;纯函数)。

    输入 = ``PrepObservation.spheres``([(color, Point, r)];颜色与半径
    仅排序消费,不进载荷);``cap`` = 本批点击预算(发射位常量,如
    mandate_v1 SPHERE_CLICK_BATCH_MAX_K)。输出 = 有序 (x, y) 点击列——
    大球优先(r 降序;稳定排序保持观察序),上界 = min(cap, 硬上限
    SPHERE_CLICK_HARD_CAP)。席满让路门/占席球语义归发射位(既有门),
    本函数不辖。

    消费面:发射位(mandate_v1 entry)构造 CwActionClickSpheresParam 载荷;执行器
    零排序零截断纯机械点(第二实现禁)。
    """
    budget = max(0, min(int(cap), SPHERE_CLICK_HARD_CAP))
    ordered = sorted(spheres, key=lambda t: t[2], reverse=True)[:budget]
    return tuple((int(p.x), int(p.y)) for _c, p, _r in ordered)


@dataclass
class PrepObservation:
    """备战决策环观察载体(阶段 3.5 瘦身版,迭代 2026-09-18-prep-obs-
    retirement)。

    **宿主降级申报**:本类已不再是策略器输入——名单/装备/占用/球全部
    容器域承载,策略器唯读容器契约归位;本帧仅承载**控制信号与识别
    元信息**(观察链/op 内部消费,不进 gs、不进 session):
    - ``shop_open``:观察链门参数(F2 gold 可信派生/卡池票门);
    - ``substate``:observe_full 可读性标注(对账/日志判读);
    - ``event_overlay``:bail 控制信号(交回外循环分发)。

    状态类字段(bench_chars/deployed_chars/装备三路/spheres/boxes/tomes/
    free_bench_slots/deploy_vacancy 族/front_occupied/back_occupied/
    front_size/state_gold_trusted/P1P5 恒空字段)已随黑板退役删除——
    去向表见迭代详设 obs-retirement §阶段 3.5。
    """
    substate: dict = field(default_factory=dict)   # observe_full 可读性(对账/日志)
    shop_open: bool = False             # 锚点「按钮-收起」可见(观察链门参数)
    # 事件 overlay 检测(盛会之星/选择伙伴/祈愿试炼 —— 挡操作,检测到即
    # 交回外循环分支 handler;实锤:盛会之星 overlay 下 deploy 全灭 → 空场 HP 82→1)
    event_overlay: str | None = None
