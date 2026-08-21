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

flag(终审③文档漂移修):gate_director / gate_shop_close /
gate_shop_open / gate_hook——CurrencyWarConfig 字段(默认
off;save() 白名单已含)。锚判定=框架 screen_utils
.get_match_screen_name(id_mark 体系;r324);指纹基元=
cv2_utils.fingerprint_in_rects/same(r324 下沉)。
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

#: 关态(备战+商店关)。
#: 锚设计(用户指路+r324 轮子审查修法1):**删自拼 presence/
#: absence 双锚**——用框架 screen_match 精准判定一次搞定:
#: get_match_screen_name(['备战','开商店'])精准命中「备战」
#: = 关态(id_mark 全中体系:备战屏 id_mark=购买经验/出战/
#: 前台/后台,开商店屏精准命中时必然不是关态)。
#: 圆数门弃用(局35 误杀奖励面板帧)。
PROFILE_CLOSED: dict = {
    'screen_list': ('货币战争-备战', '货币战争-备战-开商店'),
    'expect_screen': '货币战争-备战',
    # 读区像素指纹(1080p;排除表:立绘 idle 呼吸区/球区 VFX)
    'fingerprint_rects': (
        Rect(1408, 23, 1498, 103),  # HP 数字区(关态右上真值)
        Rect(60, 895, 320, 975),     # LV/XP
        Rect(250, 30, 520, 120),     # 阶段区(位面-轮次)
    ),
    'timeout_s': 4.5,               # r299 实测关店动画 ~3s
    'min_stable_s': 0.8,
}

#: 开态(商店开):同用框架精准判定——精准命中「开商店屏」
#: (其 id_mark=收起/购买经验 全中)。
PROFILE_OPEN: dict = {
    'screen_list': ('货币战争-备战-开商店',),
    'expect_screen': '货币战争-备战-开商店',
    'fingerprint_rects': (
        Rect(1620, 890, 1700, 945),   # gold 数字区(开态右下)
        Rect(300, 228, 1560, 326),    # 商店牌行
    ),
    'timeout_s': 4.5,
    'min_stable_s': 0.8,
}

#: 弹窗态(奖励采集钩子点六边形后):锚=弹窗标题区 OCR「金币说明」。
PROFILE_POPUP: dict = {
    # r324 修法3:弹窗改走建档(upsert_screen_area「标识-金币
    # 说明」id_mark 待建)——ocr_keyword 特例是绕过建档的平行
    # 通道,审查标重复。建档前此 profile 不接线(钩子仍走
    # r304 流程;钩子本身「采完删」,见方案 v4)。
    'screen_list': ('货币战争-金币说明弹窗',),
    'expect_screen': '货币战争-金币说明弹窗',
    'fingerprint_rects': (
        Rect(1000, 580, 1560, 1010),  # 节点预计收入明细区
    ),
    'timeout_s': 3.0,
    'min_stable_s': 0.6,
}

#: 帧间隔(方案 v4:0.2-0.3s)
_POLL_S: float = 0.25

# r324(轮子审查修法2):指纹原语下沉 one_dragon.utils.cv2_utils
# (fingerprint_in_rects/fingerprint_same,与 is_same_image 并列)——
# gate 不再私有实现;阈值语义注解见 cv2_utils(局36 diag 实证)。


def wait_stable_frame(
        op: SrOperation, *, profile: dict,
        timeout_s: float | None = None,
        clock=None) -> MatLike | None:
    """等待画面稳定(r324 重构:框架能力复用版)。

    - 锚判定=**框架 screen_match 精准判定**(id_mark 全中):
      get_match_screen_name(profile['screen_list'])精准命中
      expect_screen——删自拼 presence/absence(轮子审查 A2)
      与 ocr_keyword 特例(A5);
    - 帧一致=**cv2_utils.is_same_in_rects**(审查 A3:指纹
      下沉框架,与 is_same_image 并列);
    - 时间维度稳定窗(min_stable_s 首尾帧)+异常/超时分流
      (raise vs None)是本模块仅存的净增量(审查 D);
    - 截图异常→raise(调用方 except=放行旧路径);
      超时→None(per-callsite 语义表);
    - clock 可注入(测试 seam)。
    """
    from one_dragon.base.screen import screen_utils
    from one_dragon.utils import cv2_utils
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
    _diag = {'screen': 0, 'fp': 0, 'ok': 0}
    while _now() < deadline:
        frame = op.screenshot()   # 异常直传(调用方 except=放行旧路径)
        # 画面判定:框架 is_target_screen(id_mark 体系;一次调用
        # 替代自拼 presence/absence 双锚与 ocr_keyword 特例)
        _name = screen_utils.get_match_screen_name(
            ctx=op.ctx, screen=frame,
            screen_name_list=list(profile['screen_list']),
            crop_first=False)
        if _name != profile['expect_screen']:
            _diag['screen'] += 1
            _sleep(_POLL_S)
            # r327(终审 B):锚 miss 连 first_fp 一起重置——
            # 只重置 stable_since 会在「锚短暂 miss 后恢复且
            # 指纹未变」时卡死:L139 same 成立跳过重设分支,
            # stable_since 恒 None → 稳定窗永不达成 → 必超时
            # →(director 站)同因 3 次 3-strike 停机——瞬时锚
            # miss 被放大成停局,违背时间稳定窗初衷。
            stable_since = None
            first_fp = None
            continue
        # 帧一致:框架 per-rect(与全图 is_same_image 并列的增量)
        fp = cv2_utils.fingerprint_in_rects(
            frame, profile['fingerprint_rects'])
        if first_fp is None or not cv2_utils.fingerprint_same(
                fp, first_fp):
            _diag['fp'] += 1
            first_fp = fp
            stable_since = _now()
            _sleep(_POLL_S)
            continue
        if stable_since is not None and \
                _now() - stable_since >= profile['min_stable_s']:
            log.info(f'[cw][gate] stable frame ({profile["expect_screen"]}, {_now() - t0:.1f}s)')
            return frame
        _diag['ok'] += 1
        _sleep(_POLL_S)
    log.info(f'[cw][gate] timeout ({_now() - t0:.1f}s) '
             f'profile={profile["expect_screen"]} diag={_diag}')
    return None
