"""买经验动作 op(PrepLevelUpOp)——备战域动作文件(统一动作工厂批3 体迁:
体自 ``prep_actions.py::PrepActionExecutor._level_up`` 逐字迁移,原方法改
薄委托保持替身缝,design.md unified-action-factory §2.4)。

R6 定案④逐帧单击形态(批2 定形,本批只迁形)。命名申报:词表类
``LevelUp`` 的本域 op 不可与商店域 ``cw_level_up_action.LevelUpOp`` 同名
同包(批1 注册行更替为备战 op;``LevelUpShop`` is-a ``LevelUp`` 经
is-a 兜底同解析本 op),冠 ``Prep`` 前缀区分域。非终结。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_economy import (
    XP_CLICK_COST_FALLBACK,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class PrepLevelUpOp(ActionOp):
    """买经验(R6 逐帧单击形态:找钮 → 单击 → 固定等待,零授权零计数)。
    非终结。"""

    def execute(self, env: PrepExecEnv) -> bool:
        """买经验(R6 逐帧单击形态:找钮 → 单击 → 固定等待,零授权零计数)。

        执行器授权面全删(design.md unified-action-factory §2.6 LevelUp
        粒度定案):授权击数推导/血闸整级授权/逐击金地板全部上移发射位
        (kernel ``clicks_to_next_level`` 现算击数 > 0 = 每帧发射前置;
        spend_unified / levelup_budget_gate / posture 血闸 = 决策核发射门)。
        升 N 击 = N 帧(决策循环逐帧重组,与商店域单击形态
        ``cw_level_up_action`` 同构先例)。

        金腿 = 容器逻辑态直写(批2b 翻转定案):金账唯一写点 =
        ``apply_prep_action_logic`` LevelUp 分支按 ``action.cost`` 扣减
        (cost = 发射面 xp_click_cost 现算装载);原 2a 中间态执行缝金差
        (``_last_levelup_spent`` → ``_executed_gold_delta``)随翻转退役。
        单击价本处现算仅作 detail 显影(与发射面同源 kernel 读口)。
        经验/等级真值 = 下一帧观察对账族 + 逻辑态 xp/level 推进
        (``apply_prep_action_logic`` LevelUp 分支)双通道。
        """
        ex = env.executor
        match = ex._ctx.cw_match
        session = match.session if match is not None else None
        from sr_od.application.currency_war.kernel.cw_economy import (
            xp_click_cost,
        )
        btn = area_center(ex._ctx, '备战标识-购买经验') or Point(296, 860)
        # 单击价容器读口(kernel 单一源,失读回退兜底价;与假环境执行缝同式)
        _price = XP_CLICK_COST_FALLBACK
        if session is not None:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                board_state_of,
            )
            _price = xp_click_cost(board_state_of(session))
        ex._ctx.controller.mouse_move(btn)   # bug#1 缓解(review M-5)
        ex._ctx.controller.click(btn)
        # 光标 parking(审计 P0,2026-08-16 = M38 level 毒化注入点):按钮距等级显示区 18px,
        # 点击后光标压住 Lv.N 区 → 下帧 OCR 读错(4 毒化 3 位面的链头)。park 后再继续。
        ex._op.park_cursor(before_wait=0.3, after_wait=0.15)
        # W612 挂点A(升级事件;发出即登记,观测 best-effort,零决策语义)。
        try:
            if session is not None:
                session.effect_inventory.on_level_up()
        except Exception as e:   # noqa: BLE001  观测失败不阻塞对局
            log.warning('[cw][levelup] effect inventory 挂点失败(不阻塞): %s', e)
        detail = (f'买经验单击 1 击花金{_price}'
                  '(逐帧单击形态;级真值=下一帧观察 reconcile)')
        log.info(f'[cw][levelup] {detail}')
        env.detail, env.emitted = detail, True
        return True
