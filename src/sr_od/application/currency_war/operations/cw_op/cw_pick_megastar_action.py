"""盛会之星 pick 确认链动作 op(:class:`CwActionPickMegastarOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:``env.need_select`` 驱动的选中半(点候选——点击坐标 = 容器
``megastar_opts[idx].xy``,观察上报,按下标取;选择坐标观察上报规范 =
op-layer.md §1.1 + action_ops.md §1 增补 5)→ 确认钮单发;机械链发出后
直调自上报单口 ``report_action_pick_megastar_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_pick_megastar_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickMegastarParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionPickMegastarOp(SrOperation):
    """盛会之星 pick 确认链(统一动作工厂批4 迁入)。

    候选选中半迁入本类(pick-op-unify 批,``env.need_select`` 驱动,见
    ``run``);``chosen_megastar`` 写端留守画面 op(单次逻辑写入豁免面,
    派发前写)——确认机械半 = 确认钮单发。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickMegastarParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickMegastarOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_megastar', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(选中半[need_select] → 确认钮单发 + 固定等待;零判效)。

        选中半(pick-op-unify 批自画面 op 迁入;选择坐标观察上报收敛批
        改容器取点):``env.need_select`` → 点候选选中 + 固定等待(原选
        中后 0.6s 动画窗,时序逐位保留)。点击坐标 = 容器
        ``megastar_opts[param.idx].xy``(观察上报,按下标取;坐标单一真相
        源 = 观察上报,本 op 零坐标现算、零 screen_info 二次取点)。
        ``chosen_megastar`` 写端与选中旗标留守画面 op(单次逻辑写入豁免
        面,派发前写)。"""
        param = self.param
        env = self.env
        op = env.op
        if env.need_select:
            # 选中半取点守卫(防 bug 路栏,非控制流):容器缺席/下标越界/
            # 元素缺坐标 = 观察上报链或策略器 bug,AssertionError 响亮
            # 暴露——禁静默跳过选中(旧 target None 消极臂退役)、禁坐标
            # 现算回退(action_ops.md §1 增补 5;op-layer.md §1.3)。
            # 取点键 = param.idx(动作语义单一源,与上报函数同源;env.idx
            # 已退役停喂——钳位删除后与 param.idx 恒等,镜像无存在意义)。
            _gs = game_state_from_ctx(self.ctx)
            _opts = (_gs.megastar_opts.value if _gs is not None else None) or []
            assert _opts, (
                '[cw-pick-megastar] 容器 megastar_opts 缺席/空(观察上报'
                f'缺失,禁坐标现算回退): idx={param.idx}')
            assert 0 <= param.idx < len(_opts), (
                f'[cw-pick-megastar] param.idx 越界容器选项槽(策略器 bug): '
                f'idx={param.idx} len={len(_opts)}')
            assert _opts[param.idx].xy is not None, (
                '[cw-pick-megastar] 容器选项缺 xy(观察上报未产坐标,禁'
                f'二次取点): idx={param.idx} opt={_opts[param.idx]!r}')
            pt = Point(*_opts[param.idx].xy)
            op.ctx.controller.mouse_move(pt)
            op.ctx.controller.click(pt)
            time.sleep(0.6)
        # 确认 = 建档「按钮-确认选择」查找点击(round_by_find_and_click_area
        # 全族统一,用户裁定 2026-09-22;不带 until = 动作 op 禁验证;area
        # 缺失 = 显式失败交框架轮次,兜底常量 CONFIRM 随批退役)。
        # overlay 关否由下一帧重入裁决。
        env.round_result = op.round_by_find_and_click_area(
            op.screenshot(), '货币战争-盛会之星', '按钮-确认选择',
            success_wait=0.9)
        # 确认 = 纯机械单发(用户裁定 2026-09-14):「请选择强化角色」
        # 文本 = 确认钮旁伴随文案,禁据它判步。
        # 确认未落地 overlay 残留 =
        # 下一帧重入裁决自愈:节点循环读「仍在巨星 overlay?」(标识锚仍
        # 命中)→ 重走本方法 → 候选已选 → 机械单发确认再推进
        # (宿主 round_wait 循环推进,不烧节点重试预算)。
        # chosen_megastar 写端留守画面 op(动作事实边界,派发前写 =
        # 选择点),无挂账登记环节。
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_megastar_param(
                gs, param,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('盛会之星确认已发')
