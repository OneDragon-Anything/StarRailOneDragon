"""货币战争 观测统一入口(ADR-0213 批次1;方案 v4)。

「等待画面稳定 → 一次全面识别」的稳定门原语——替代散布
4+ 层的等待实现(连续 3s 锚窗/单锚探/轮询消失/固定 sleep;
见 ADR-0213 Context)。设计定案(四轮对抗 review 收敛):

- wait_stable_frame: min_stable_s 连续稳定窗(首尾帧一致,
  非相邻对——慢动画假稳定)+ 先 park_cursor;一致性基元=
  锚命中向量 + per-area 像素指纹(OCR 只用于锚);
- 三 profile(关态/开态/弹窗态),锚常量收敛不参数化分裂;
- 离线契约:截图异常→放行旧路径(环级测试依赖);
- None 返回语义 per-callsite(director=同因 bail 计数/
  shop=round_retry/钩子=skip+log);
- 消化门失败走既有 _bail 3-strike(session 计数),不引入
  round_fail 路径(battle_loop 忽略返回值→ping-pong)。

flag:CurrencyWarConfig.observation_gate_enabled(默认 off,
旧路径;save() 白名单必须含——GUI 静默抹值前科)。
批次1 接线点见方案 v4;本文件先落地原语(flag off 零影响)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils.log_utils import log

if TYPE_CHECKING:
    from sr_od.operations.sr_operation import SrOperation

# ===== profile 常量(两态+弹窗;锚/读区/超时收敛于此,调用方只选套) =====

#: 关态(备战+商店关):锚=按钮-出战 presence + 「按钮-收起」
#: absence(shop 开→收起可见→拒)。
#: ⚠ 实证史(对拍局35 首日):圆数门(circle_gate)误杀 1-1
#: 奖励面板帧(reward 节点面板展开遮节点行→圆<6 恒 fail→
#: 3-strike 停机)——「读不到圆」在 shop 开帧与奖励面板帧
#: 语义相反,圆数门不能当关态判据;收起 absence 只防 shop
#: 开(其判据即 shop 开态专属按钮),奖励面板帧正确放行。
PROFILE_CLOSED: dict = {
    'anchor_screen': '货币战争-备战',
    'anchor_area': '按钮-出战',
    # shop 开态互斥锚(absence):开商店屏的「按钮-收起」可见=拒
    'absence_screen': '货币战争-备战-开商店',
    'absence_area': '按钮-收起',
    # 读区像素指纹(1080p;不含立绘 idle 呼吸区/球区 VFX——排除表)
    # ⚠ HP 在关态右上(文本-剩余血量 1408-1498/23-103);
    # 原 (1620,890) 是 gold 区(关态恒空,指纹恒同无意义——对拍局35 发现)
    'fingerprint_rects': (
        Rect(1408, 23, 1498, 103),  # HP 数字区(关态右上真值)
        Rect(60, 895, 320, 975),     # LV/XP
        Rect(250, 30, 520, 120),     # 阶段区(位面-轮次)
    ),
    'circle_gate': False,           # 误杀实证(局35),弃用
    'timeout_s': 4.5,               # r299 实测关店动画 ~3s
    'min_stable_s': 0.8,
}

#: 开态(商店开):锚=按钮-收起 presence(⚠ 禁用「备战标识-购买
#: 经验」——shop 开/关两态均可见,r297 实证)。
PROFILE_OPEN: dict = {
    'anchor_screen': '货币战争-备战-开商店',
    'anchor_area': '按钮-收起',
    'fingerprint_rects': (
        Rect(1620, 890, 1700, 945),   # gold 数字区(开态右下)
        Rect(300, 228, 1560, 326),    # 商店牌行
    ),
    'circle_gate': False,
    'timeout_s': 4.5,
    'min_stable_s': 0.8,
}

#: 弹窗态(奖励采集钩子点六边形后):锚=弹窗标题区 OCR「金币说明」。
PROFILE_POPUP: dict = {
    'anchor_screen': '货币战争-备战',
    'anchor_area': '',               # 弹窗未建档:ocr_keyword 代替
    'ocr_keyword': '金币说明',
    'fingerprint_rects': (
        Rect(1000, 580, 1560, 1010),  # 节点预计收入明细区
    ),
    'circle_gate': False,
    'timeout_s': 3.0,
    'min_stable_s': 0.6,
}

#: 帧间隔(方案 v4:0.2-0.3s)
_POLL_S: float = 0.25


def _fingerprint(frame: MatLike, rects: tuple[Rect, ...]) -> tuple:
    """读区像素指纹(dHash 风格:逐区缩小灰度差分)。

    比 OCR 便宜一个数量级(每区 8x8 灰度),对光标/VFX 通过
    排除表规避(读区不含动画区)。
    """
    import cv2
    parts = []
    for r in rects:
        crop = frame[r.y1:r.y2, r.x1:r.x2]
        if crop.size == 0:
            parts.append(b'empty')
            continue
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        small = cv2.resize(gray, (8, 8))
        parts.append(small.tobytes())
    return tuple(parts)


def wait_stable_frame(
        op: SrOperation, *, profile: dict,
        timeout_s: float | None = None,
        clock=None) -> MatLike | None:
    """等待画面稳定(方案 v4 定案语义;终验 P1① 修正)。

    - 先 park_cursor(op 方法;签名传 op 因 park_cursor 是
      SrOperation 成员,ctx 上没有——D-2.1);
    - 循环:截帧 → 锚命中(OCR/圆数门)→ 首尾帧指纹一致且
      持续 min_stable_s → 返回稳定帧;
    - **截图异常 → raise**(终验 P1①:异常与超时必须分流——
      折叠进 None 会被按 None 语义表接线成 3-strike 停机,
      把离线/瞬断升级成停局,违背环级测试依赖的 except-break
      放行语义;调用方 try/except 接住=放行旧路径);
    - 超时 → None(调用方按 per-callsite 语义表处理:
      director=同因 bail / shop=round_retry / 钩子=skip+log);
    - clock 可注入(默认 time.monotonic;测试 seam,Y-4)。
    """
    _now = clock or time.monotonic
    _sleep = (lambda s: None) if clock else time.sleep
    t0 = _now()
    deadline = t0 + (timeout_s if timeout_s is not None
                     else profile['timeout_s'])
    import contextlib
    with contextlib.suppress(Exception):   # 离线无控制器
        op.park_cursor()
    stable_since = None
    first_fp = None
    _diag = {'anchor': 0, 'absence': 0, 'circle': 0, 'fp': 0, 'ok': 0}
    while _now() < deadline:
        frame = op.screenshot()   # 异常直传(调用方 except=放行旧路径)
        # 锚命中(presence)
        if profile.get('ocr_keyword'):
            if not op.round_by_ocr(frame, profile['ocr_keyword']).is_success:
                _diag['anchor'] += 1
                _sleep(_POLL_S)
                stable_since = None
                continue
        elif not op.round_by_find_area(
                frame, profile['anchor_screen'],
                profile['anchor_area'], crop_first=False).is_success:
            _diag['anchor'] += 1
            _sleep(_POLL_S)
            stable_since = None
            continue
        # 互斥锚(absence):shop 开态按钮可见 = 非关态 → 拒
        # (对拍局35:替代圆数门——奖励面板帧读不到圆≠shop 开)
        if profile.get('absence_area') and op.round_by_find_area(
                frame, profile['absence_screen'],
                profile['absence_area'], crop_first=False).is_success:
            _diag['absence'] += 1
            _sleep(_POLL_S)
            stable_since = None
            continue
        # 圆数门(弃用——局35 实证误杀奖励面板帧;保留字段兼容)
        if profile.get('circle_gate'):
            from sr_od.application.currency_war.cw_observation import (
                read_node_sequence,
            )
            if not read_node_sequence(op.ctx, frame):
                _diag['circle'] += 1
                _sleep(_POLL_S)
                stable_since = None
                continue
        # 指纹首尾一致
        fp = _fingerprint(frame, profile['fingerprint_rects'])
        if first_fp is None or fp != first_fp:
            _diag['fp'] += 1
            first_fp = fp
            stable_since = _now()
            _sleep(_POLL_S)
            continue
        if stable_since is not None and \
                _now() - stable_since >= profile['min_stable_s']:
            log.info('[cw][gate] stable frame (profile=%s, %.1fs)',
                     profile.get('anchor_area') or profile.get('ocr_keyword'),
                     _now() - t0)
            return frame
        _diag['ok'] += 1
        _sleep(_POLL_S)
    log.info('[cw][gate] timeout (%.1fs) profile=%s diag=%s',
             _now() - t0,
             profile.get('anchor_area') or profile.get('ocr_keyword'))
    return None
