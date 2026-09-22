"""select-and-confirm overlay 通用收尾助手(bug#1 缓解 + 机械确认发射)。

货币战争事件节点(巨星/补给/遭遇/投资环境/投资策略/未达上限)都是同一交互结构:
点选项选中 → 点确认推进。旧 handler 曾普遍「点了就 ``round_success``」不观察 →
bug#1(``before_screenshot`` 移光标 → click 落空)/隐藏多步 overlay → overlay 不关 →
外层 loop 反复重跑本节点 → 卡到 MAX_ITER 才超时(伙伴 overlay reset 根因同类;
write-operation skill「反模式:点了≠成了」)。

本模块给这类 handler 统一收尾:确认点击带 bug#1 ``mouse_move`` 缓解 + 固定等待,
机械交回 ``round_retry``(观察驱动)。**不做落地判定**(用户裁定 2026-09-10:
动作 op 只管机械执行,禁止做任何验证;M1③ 发出即职责完成,调用方不问成败):
overlay 关没关由调用方节点下一轮重入的入口观察裁决——重入时入口词不在 = 已离开
本画面 → success 交回(重入观察出口,先例 = ``cw_entry_start`` 守卫
``_handle_entry_popup_spec`` / megastar 循环顶「已离开本节点画面?」同化先例);
仍在 = 基于新观察重做确认动作(计 ``node_max_retry_times`` 预算,耗尽 FAIL
bail = 有界终止单)。success/retry = 轮次流转语义,非动作成败回执。

注:仅收尾「确认 + 机械交回」。选项**选中**的点击(卡身/候选/勾选)各 handler
用 ``safe_click`` 带 bug#1 缓解即可;确认统一走 ``emit_overlay_confirm``。
"""
import time
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )


def register_confirm_arrival(session: 'StrategySession | None', op: str, item: str,
                             produced_by: str = 'overlay_confirm') -> None:
    """overlay 选卡确认逻辑推进(两态制 :推算值直接写 session 字段,
    策略器立即可读;实读帧照常覆盖)。

    语义按 op 分道:
    - ConfirmBox/ConfirmTome/ConfirmExpertCash(dict 形态现
      apply_confirm_effect):owned += item / 现金为王 gold +4(推进宿主 =
      容器单例金账,写通道单一源在 cw_exec_state;补给确认不在本族——
      其入栏/后果腿由 ``report_action_pick_supply_param`` 即时单相一口写);
    - ConfirmStrategy:本函数零写——投资策略选择事实经动作落地获得链写
      (动作 op 即时上报 → gain_invest_strategy,正本 = game_state/
      gain-chain.md;原 handler 确认写点已随投资两屏迁移批删除);
    - ConfirmMegastar/ConfirmPartner:本函数零写——chosen_* 写端 = 各
      handler 的 ``GameState.write_logic``(选择落地即写,cw_screen_megastar
      /cw_screen_partner)。

    best-effort:session 缺失 / infra 异常不阻塞确认收尾(选角色分支=
    专家入商店由商店逻辑接管,无 session 局状态变更,不推进)。
    """
    if session is None or not item:
        return
    try:
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            apply_confirm_effect,
        )
        if op in ('ConfirmBox', 'ConfirmTome', 'ConfirmExpertCash'):
            apply_confirm_effect(session, {'op': op, 'item': item},
                                 produced_by=produced_by)
            return
    except Exception as e:  # noqa: BLE001  观测面不阻塞确认
        log.info(f'[cw-overlay] 逻辑推进跳过: {e}')


def find_text_center(op: SrOperation, text: str) -> Point | None:
    """OCR 全屏找 ``text`` 的 center(没找到 None)。给动态定位确认按钮用(确认文字位置随 overlay 变,
    无固定坐标 / 未进 screen_info 时)。"""
    ocr_map = op.ctx.ocr_service.get_ocr_result_map(
        image=op.last_screenshot, rect=None, color_range=None, crop_first=False,
    )
    mrl = ocr_map.get(text)
    if mrl and mrl.max:
        return mrl.max.center
    return None


def safe_click(op: SrOperation, point: Point, *, tag: str = 'cw-overlay') -> None:
    """防吞点击:click 前 ``mouse_move``(零移动),防 ``before_screenshot`` 移光标 → click 落空。

    给选项选中点击(卡身/候选/勾选)用。确认点击走 ``emit_overlay_confirm``(已含 mouse_move)。
    """
    log.info(f'[{tag}] safe_click {point}')
    op.ctx.controller.mouse_move(point)
    op.ctx.controller.click(point)


def emit_overlay_confirm(
    op: SrOperation, *, confirm_point: Point, entry_keyword: str, lcs_percent: float = 0.5,
    confirm_wait: float = 1.0, success_wait: float = 2.0, tag: str = 'cw-overlay',
    press_time: float = 0.1,
) -> OperationRoundResult:
    """点确认按钮(``mouse_move`` 防吞点击)+ 固定等待,机械交回 ``round_retry``。

    验证废除形态(用户裁定 2026-09-10,替换原 ``confirm_and_verify`` 的
    「点后重截验入口词消失」判效半):

    - 确认点击带 ``mouse_move``(防吞点击,partner reset 根因同类)。
    - ``press_time``:按下时长;默认 0.1(框架默认)。输入管线半死态短按下
      可能不被采样(prep_actions 出战重发 0.15 人工解锁实证),需要者显式传入。
    - 确认后固定等待 ``confirm_wait``(确认关闭动画,固定时长口径)→ 无条件
      ``round_retry``(观察驱动):**不读屏判「是否生效」**——落地判定归下一轮
      重入的入口观察(调用方节点顶部裁决)与观察侧 reconcile 对账,不在动作层。
    - ``entry_keyword`` 仅作日志与调用方重入裁决的对照词(与 entry 检测同词);
      ``success_wait`` 保留为调用方重入裁决 success 出口的交回等待值。
    - 始终不落地 = 每圈耗 1 次节点预算,预算耗尽 FAIL bail(有界终止单,
      防 26 分钟超时事故形态)。
    """
    log.info(f'[{tag}] emit_confirm@{confirm_point} (entry_keyword={entry_keyword!r})')
    op.ctx.controller.mouse_move(confirm_point)
    op.ctx.controller.click(confirm_point, press_time=press_time)
    time.sleep(confirm_wait)
    # 机械交回(观察驱动):下一轮重入由调用方节点顶部入口观察裁决出口
    #(不在 = 已关 → success 交回;在 = 重做确认,计节点预算)。
    _ = success_wait   # 保留签名兼容调用方出口等待取值;本函数零观察零判效
    return op.round_retry(wait=1)
