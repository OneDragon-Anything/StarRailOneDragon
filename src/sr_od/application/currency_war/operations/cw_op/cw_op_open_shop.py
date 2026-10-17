"""货币战争-开商店 动作原语(直调体;动作 op 规范形态)。

规范 = flow/action_ops.md §1 裁定原文:动作 op 是机械执行——把动作
发出去 + 如实上报动作事实,禁验证、禁重试、禁判断。生产路径 =
``cw_screen_prep._open_shop_phase`` 直调 :func:`open_shop`(宿主 op
复用其 round_by_* 判定与测试替身桩;返回值弃置,调用方不问成败)。
幂等已开判定归流程层(``visit_open_shop`` 入口观察 + 外循环 0n 三锚),
本函数零观察、零幂等分支。
"""
import time

from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.prep_actions import SHOP_OPEN_ANIM_S
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.operations.sr_operation import SrOperation


def _note_receipt(op: SrOperation, reason: str) -> None:
    """开商店动作回执(唯一写点 = kernel 口 `note_action_receipt`;
    reason = 动作事实码,'' = 已正常发出,词表见 kernel docstring)。

    两出口全簿记(每动作 op 恰一条回执行):已发出 = reason='';
    实机定位缺失(动作没发出)= reason=定位缺失(按钮-商店)——失败
    可见性(exec_events 并入),journal 唯一直接痕迹(宿主弃 round
    结果,无 [cw-op] 行)。发出即簿记非验证(不读屏核验);journal 常开
    (语义申报 = `kernel/cw_state_journal.py` 模块头)回执写入无条件,
    无局跳过在 kernel 口。回执 op 名/actor 硬编码
    `'CwOpOpenShop'`(journal 词表稳定;渲染器词表与类删除解耦)。
    """
    try:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_from_ctx,
            note_action_receipt,
        )
        gs = game_state_from_ctx(getattr(op, 'ctx', None))
        if gs is None:
            return
        note_action_receipt(gs, op='CwOpOpenShop',
                            reason=reason, screen=SHOP_SCREEN_NAME,
                            actor='CwOpOpenShop')
    except Exception as e:  # noqa: BLE001  回执失败不阻塞动作链
        from one_dragon.utils.log_utils import log
        log.warning('[cw][receipt] 开商店回执写入失败(不阻塞): %s', e)


def open_shop(op: SrOperation) -> OperationRoundResult:
    """开商店动作原语(直调体;机械执行 + 发出即记账,禁验证/重试)。

    ``op`` = 宿主 op(``CwScreenPrep``;复用其 round_by_* 判定与测试替身桩)。
    唯一受阻出口 = 实机定位缺失(「按钮-商店」未命中 = 动作没发出,
    回执 reason=定位缺失(按钮-商店));
    sim 下点击经端口 click_answer 受理即已发出(世界推进通道,见分支内注),
    恒按已发出簿记(reason='')。
    """
    # 动作 op 规范(action_ops.md 裁定原文):机械执行 + 发出即记账,禁验证/重试。
    clicked = op.round_by_find_and_click_area(
        op.screenshot(), '货币战争-备战', '按钮-商店').is_success
    if cw_sim_ports.mechanical_io_allowed():
        # 实机:is_success = 发出事实。False = 定位缺失(唯一受阻出口,
        # 回执 reason 码申报未发出)。
        if not clicked:
            _note_receipt(op, '定位缺失(按钮-商店)')
            return op.round_fail('定位缺失(按钮-商店)')
        op.park_cursor()
        time.sleep(SHOP_OPEN_ANIM_S)
    else:
        # sim:点击经端口 click_answer 感知 = 世界推进通道(sim-design §3.2
        # 转移源 2:_handle_click_source → _open_shop 呈现 + 离屏牌面补写 +
        # 刷价写回);屏门按点击前档名问询的 retry 是转移后可见性语义,不作
        # 发出判读——点击已受理即已发出,按已发出簿记名副其实。
        pass
    _note_receipt(op, '')
    return op.round_success('开商店已发')
