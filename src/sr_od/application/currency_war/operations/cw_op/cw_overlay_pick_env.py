"""事件线 pick 域共享执行环境(OverlayPickExecEnv 单一宿主)。

一 op 一文件(op-layer.md :48)拆分后,本模块只承载 pick 族共享的
``OverlayPickExecEnv``;各动作 op 类各自单文件
``operations/cw_op/cw_pick_<snake>_action.py``(snake 与上报侧
``kernel/cw_action_report/pick_<snake>.py`` 对称)。域 env = 结构化包,
构造时显式传入;机械参数(定位点/选定快照/未选中实证/确认钮定位)由
各画面 op 决策半现算后经 env 显式传入,op 类体内零决策零读决策输入。

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

    公共字段 ``op``/``match``/``config`` + 域字段 = 决策半产物(机械参数,
    构造时显式传入,op 类体内不自算):``idx`` = 生效选中下标(决策半
    钳位后)、``target`` = 点卡定位点(退役中——选择坐标观察上报收敛,
    已收敛屏停喂;全族收敛后删字段)、``picked`` = 选定快照(到账登记
    输入)、``unselected`` = 未选中提示在场实证。
    ``confirm`` = 确认钮中心(决策半从 screen_info 现取;None = 点卡即选
    族无确认步);``entry_keyword`` = 确认裁决词(emit_overlay_confirm
    消费,仅日志与调用方重入裁决对照);``need_select`` = 选中半开关
    (True = 先点候选选中再确认,点击坐标各 op 自取——巨星 = 容器
    ``megastar_opts[idx].xy``(选择坐标观察上报收敛),其余过渡期屏 =
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
    idx: int = 0              # [索引定义] 坐标系: 决策半候选列表下标(0 起);
    #             取值时机: 决策半现算快照(钳位后生效值,执行期恒稳)
    target: Any = None        # 退役中(选择坐标观察上报收敛,已收敛屏停喂;
    #             全族收敛后删字段;其余屏过渡期在用)——历史语义:Point|None
    #             点卡定位点(决策半从 screen_info/OCR 现算)
    confirm: Any = None       # Point|None 确认钮中心(决策半现取;None=点卡即选)
    entry_keyword: str = ''   # 确认裁决词(emit_overlay_confirm;仅日志/重入对照)
    need_select: bool = False  # True = 先点 target 选中再确认(巨星选中半)
    picked: dict | None = None
    unselected: bool = False
    leg_type: str = ''        # 策划腿型载荷(decision 半 classify_planner_leg 产物)
    norm_item: str = ''       # 策划装备腿归一件名('' = 未解析/非装备腿)
    round_result: OperationRoundResult | None = None
