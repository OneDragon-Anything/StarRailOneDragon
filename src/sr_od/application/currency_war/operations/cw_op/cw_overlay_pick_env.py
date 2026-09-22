"""事件线 pick 域共享执行环境(OverlayPickExecEnv 单一宿主)。

一 op 一文件(op-layer.md :48)拆分后,本模块只承载 pick 族共享的
``OverlayPickExecEnv``;各动作 op 类各自单文件
``operations/cw_op/cw_pick_<snake>_action.py``(snake 与上报侧
``kernel/cw_action_report/pick_<snake>.py`` 对称)。域 env = :class:`OverlayPickExecEnv`
(结构化包,构造时传入);机械参数辖域(申报单一源 = flow/action_ops.md
§4.5 段首)= 选卡定位 + 域载荷经 env 传入;确认钮不属机械参数,由本 op
执行体瞄准查找(action_ops.md §1 增补 3 在册例外)。op 类体内零决策零读
决策输入(决策 = 选中哪个与腿型载荷,瞄准定位查找非决策)。

**自上报统一**:pick 族每类 run 体在机械链(选中点击 → 确认点击)发出
后直调自己的上报函数 ``report_action_pick_<snake>_param``
(``kernel/cw_action_report``,零写族落 zero_writes)——与 buy_card 等
其它动作 op 同一执行契约,容器写语义单点 = 各上报函数,零证据闩零重入
裁决补写面。partner 确认点读缺的 retry 旁路分支未发确认点击,不上报。

体迁契约(零行为):各 op 类 run 体 = 现役 overlay act 确认链逐字迁移,
接收者 ``self``→``env.op``、机械参数→env 字段两处归一;轮次结果(确认链
末步 ``round_*`` 产物)经 ``round_result`` 旁路字段回传——op 自身 round
结果恒成功(发出即职责完成),画面 op act 分派面读旁路字段。族先例 =
cw_tool_use_action。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.operations.sr_operation import SrOperation


@dataclass
class OverlayPickExecEnv:
    """事件线 pick 域执行环境(统一动作工厂批4 起;pick-op-unify 批扩字段)。

    公共字段 ``op``/``match``/``config`` + 域字段 = 机械参数(选卡定位/域载荷 =
    决策半产物,构造时显式传入;确认钮 = 本 op 执行体 ``round_by_find_and_click_area``
    查找点击,不入 env——机械参数辖域申报单一源 = ``flow/action_ops.md``
    §4.5 段首,本模块头同文转抄):``idx`` = 生效选中下标(决策半
    钳位后)、``target`` = 点卡定位点(退役中——选择坐标观察上报收敛,
    已收敛屏停喂;全族收敛后删字段)、``picked`` = 选定快照(到账登记
    输入)、``unselected`` = 未选中提示在场实证。
    ``need_select`` = 选中半开关
    (True = 先点候选选中再确认,点击坐标各 op 自取——巨星 = 容器
    ``megastar_opts[param.idx].xy``(选择坐标观察上报收敛),其余过渡期屏 =
    ``target``;False = 跳过选中直发确认)。
    ``round_result`` = 旁路回传(确认链末步 ``round_*`` 产物;op 自身
    round 结果恒成功不携带语义),op 类写;现行两 node 宿主画面 op 均不
    消费本字段(循环推进按宿主自身形态返回 round_wait),保留作分派面
    需要逐结果路由时的旁路面。
    ``leg_type``/``norm_item`` = 银狼策划腿型载荷(决策半经
    ``classify_planner_leg`` 现算,随派发透传给上报函数
    ——确认点击后立即上报完整效果腿;leg_type ∈ upgrade|equip|unknown,
    norm_item = 归一件名或空)。
    """

    op: SrOperation
    match: object = None      # CurrencyWarMatch(避免运行时导入环,注解宽松)
    config: object = None     # 公共面(pick 确认链零 config 消费)
    idx: int | None = None    # [索引定义] 退役中(选择坐标观察上报收敛:
    #             取点/取名键单一源 = ``param.idx``,已收敛屏停喂本字段;
    #             全族收敛后删)。历史语义: 决策半候选列表下标(0 起,钳位
    #             后生效值)——钳位随守卫化退役后与 param.idx 恒等,镜像
    #             语义消失;其余过渡期屏仍在喂仍在读
    target: Any = None        # 退役中(选择坐标观察上报收敛,已收敛屏停喂;
    #             全族收敛后删字段;其余屏过渡期在用)——历史语义:Point|None
    #             点卡定位点(决策半从 screen_info/OCR 现算)
    need_select: bool = False  # True = 先点候选选中再确认(巨星选中半;
    #             点击坐标取源见类 docstring need_select 句)
    picked: dict | None = None
    unselected: bool = False
    leg_type: str = ''        # 策划腿型载荷(decision 半 classify_planner_leg 产物)
    norm_item: str = ''       # 策划装备腿归一件名('' = 未解析/非装备腿)
    round_result: OperationRoundResult | None = None
