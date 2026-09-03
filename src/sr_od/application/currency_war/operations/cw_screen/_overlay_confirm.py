"""select-and-confirm overlay 通用收尾助手(bug#1 缓解 + 出口验证)。

货币战争事件节点(巨星/补给/遭遇/投资环境/投资策略/未达上限)都是同一交互结构:
点选项选中 → 点确认推进。旧 handler 普遍「点了就 ``round_success``」**不验 overlay 关** →
bug#1(``before_screenshot`` 移光标 → click 落空)/隐藏多步 overlay → overlay 不关 →
外层 loop 反复重跑本节点(不计 retry)→ 卡到 MAX_ITER 才超时(伙伴 overlay reset 根因同类;
write-operation skill「反模式:点了≠成了」)。

本模块给这类 handler 统一收尾:确认点击带 bug#1 ``mouse_move`` 缓解 + 确认后验入口关键词消失,
没关则 ``round_retry``(计 ``node_max_retry_times`` 兜底退出,不再无限 flat-loop)。

注:仅收尾「确认 + 验关」。选项**选中**的点击(卡身/候选/勾选)各 handler 用 ``safe_click``
带 bug#1 缓解即可;确认统一走 ``confirm_and_verify``。
"""
import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log


def register_confirm_arrival(session, op: str, item: str,
                             produced_by: str = 'overlay_confirm') -> None:
    """overlay 选卡确认到账登记(EXPECTED_STATE §3 C 区到账登记区;
    DD-019 后果节「handler 侧到账登记」缺口接线)。

    语义按 op 对照 §3.3 表分道,不逐一硬编码:
    - ConfirmSupply/ConfirmBox/ConfirmTome(dict 形态 apply_op_effect 已实现):
      owned += item(apply 同时推进 session.last_owned_equips 本体)+ 登记;
    - ConfirmStrategy:apply 登记 active_strategies[item] 条目(本体追加由
      handler 既有写入点承担,效果走台账不进 session 推进,§3.3 #22);
    - ConfirmMegastar/ConfirmPartner(chosen_*,infra 未建 dict op):经公开
      接口 register_expected 直登 kind='strategy',值带「待实读」= 覆盖点
      (prep_obs)可信读只清账不 diff;
    - ConfirmExpertCash(专家邀请函「现金为王」):gold +4(待实读),绑
      shop_wave_top 覆盖点(gold 可信源)。

    best-effort:session 缺失 / infra 异常不阻塞确认收尾(账实一致由覆盖点
    实读兜底;选角色分支=专家入商店由商店逻辑接管,无 session 局状态变更,
    §3 C 区无对应行,不登记)。
    """
    if session is None or not item:
        return
    try:
        from sr_od.application.currency_war.kernel.cw_expected_state import (
            ExpectedEntry,
            apply_op_effect,
            expected_round_key,
            register_expected,
        )
        if op in ('ConfirmSupply', 'ConfirmBox', 'ConfirmStrategy',
                  'ConfirmTome'):
            apply_op_effect(session, {'op': op, 'item': item},
                            produced_by=produced_by)
            return
        at_round = expected_round_key(session)
        if op in ('ConfirmMegastar', 'ConfirmPartner'):
            register_expected(session, ExpectedEntry(
                path=('chosen_megastar' if op == 'ConfirmMegastar'
                      else 'chosen_partner'),
                value=f'{item}(待实读)', produced_by=produced_by,
                at_round=at_round, kind='strategy',
                confirm_point='prep_obs'))
        elif op == 'ConfirmExpertCash':
            register_expected(session, ExpectedEntry(
                path='gold', value='+4(现金为王,待实读)',
                produced_by=produced_by, at_round=at_round,
                kind='gold', confirm_point='shop_wave_top'))
    except Exception as e:  # noqa: BLE001  观测面不阻塞确认
        log.info(f'[cw-overlay] 到账登记跳过: {e}')


def find_text_center(op, text: str) -> Point | None:
    """OCR 全屏找 ``text`` 的 center(没找到 None)。给动态定位确认按钮用(确认文字位置随 overlay 变,
    无固定坐标 / 未进 screen_info 时)。"""
    ocr_map = op.ctx.ocr_service.get_ocr_result_map(
        image=op.last_screenshot, rect=None, color_range=None, crop_first=False,
    )
    mrl = ocr_map.get(text)
    if mrl and mrl.max:
        return mrl.max.center
    return None


def safe_click(op, point: Point, *, tag: str = 'cw-overlay') -> None:
    """bug#1 缓解点击:click 前 ``mouse_move``(零移动),防 ``before_screenshot`` 移光标 → click 落空。

    给选项选中点击(卡身/候选/勾选)用。确认点击走 ``confirm_and_verify``(已含 mouse_move)。
    """
    log.info(f'[{tag}] safe_click {point}')
    op.ctx.controller.mouse_move(point)
    op.ctx.controller.click(point)


def confirm_and_verify(
    op, *, confirm_point: Point, entry_keyword: str, lcs_percent: float = 0.5,
    confirm_wait: float = 1.0, success_wait: float = 2.0, tag: str = 'cw-overlay',
    press_time: float = 0.1,
) -> OperationRoundResult:
    """点确认按钮(bug#1 ``mouse_move`` 缓解)→ 等 → 验 ``entry_keyword`` 消失 → 没关 ``round_retry``。

    - 确认点击带 ``mouse_move``(bug#1 缓解,partner reset 根因同类)。
    - ``press_time``:按下时长;默认 0.1(框架默认,既有 handler 零影响)。输入管线
      半死态短按下可能不被采样(prep_actions 出战重发 0.15 人工解锁实证),需要者
      显式传入(策划事件 match3 连败防御)。
    - 确认后重截屏验 ``entry_keyword`` 消失(overlay 关 = 真推进;见 write-operation「op 出口验转移」)。
    - 仍在 → ``round_retry``(计节点预算兜底退出;**不**盲目 ``round_success`` / ``round_wait`` 致无限 flat-loop)。
      若是隐藏多步 overlay(如伙伴 step2),retry 会重入本节点并重打日志 → 下次 match 日志可见,可再补 handler。

    ``entry_keyword`` = 该 overlay 的入口关键词(与 entry 检测同词,对称),消失即关。
    """
    log.info(f'[{tag}] confirm@{confirm_point} (entry_keyword={entry_keyword!r})')
    op.ctx.controller.mouse_move(confirm_point)
    op.ctx.controller.click(confirm_point, press_time=press_time)
    time.sleep(confirm_wait)
    frame = op.screenshot()
    if op.round_by_ocr(frame, entry_keyword, lcs_percent=lcs_percent).is_success:
        log.info(f'[{tag}] 确认后 {entry_keyword!r} 仍在 → round_retry(确认未落地 bug#1 / 或隐藏多步 overlay)')
        return op.round_retry(wait=1)
    log.info(f'[{tag}] {entry_keyword!r} 已消失 → overlay 关,推进')
    # (gate 清尾批 2026-09-03:原此处向已退役的 gate 稳定门预置基线;
    #  wait_stable_frame 在 旧内环拆除后已无生产调用方,基线写端
    #  无读端 → 调用删除。外循环重判兜底,等待语义不变。)
    return op.round_success(wait=success_wait)
