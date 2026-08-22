"""货币战争**结算画面**额外识别器(per-screen recognizer)。

``analyze_screen`` 精准命中「货币战争-结算」后,框架按 ``screen_name`` 查表调用本识别器,把结算画面的
结构化领域事实(**战后小队 HP** + **是否挑战失败**)塞进返回的 ``extras``。战后 HP / 胜负是客观指标
(进度 / 存活 trend 的 ground truth)。

**并发安全(关键)**:本 ``recognize`` 必须是**纯读** —— 不写 ``self.``、不写模块全局、不读写
``cw_match.session``(同 ``battle_prep_recognizer``)。故:

- 复用 ``cw_settlement_obs.parse_settlement_hp`` —— **纯函数**(入参 OCR 文本 list → hp 或 None,不碰 ctx /
  session),可安全复用。OCR 取全屏(``crop_first=False`` + ``color_range=None``)命中 analyze 同一份缓存
  (见 screen-recognizers.md「OCR 缓存复用」),不触发冗余 OCR。
- **不复用 ``read_round_outcome``**:它要 ``plane`` / ``round_num`` / ``comp_tag`` 由调用方(loop,知当前节点
  + ``session.target_comp``)传入 —— 结算屏本身不暴露这些;recognizer 不读 session,拿不到也不该读。
- **hp 语义**:`parse_settlement_hp` 读到 → 该值;失败屏(「挑战失败」= 团灭)常读不到数字(hp_after 本就是 0
  ground truth)→ 取 0;非失败屏读不到 → None(不硬塞,见 spec「不稳定字段不硬塞」)。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.application.currency_war.cw_settlement_obs import parse_settlement_hp

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext

# 结算屏 screen_info(currency_war_settlement.yml)screen_name
SETTLEMENT_SCREEN: str = '货币战争-结算'

# 团灭屏 OCR 标志(parse_settlement_hp 在失败屏常读不到数字,hp 仍按 0 ground truth 取)
_FAIL_MARKER: str = '挑战失败'


@dataclass
class _SettlementState:
    """结算画面领域事实(组装后 ``asdict()`` 转 dict 回传;类型化单一真相源)。"""

    hp_after: int | None   # 战后小队 HP(parse_settlement_hp;失败屏→0;非失败读不到→None 不硬塞)
    is_failed: bool        # 是否「挑战失败」(团灭屏)


class SettlementRecognizer(ScreenRecognizer):
    """货币战争结算画面额外识别器。"""

    screen_name: str = SETTLEMENT_SCREEN   # '货币战争-结算'

    # extras 字段说明(随 analyze 响应平级返回 extras_doc;键集与 _SettlementState 一致)
    extras_doc: dict[str, str] = {
        'hp_after': '战后小队 HP(int;「挑战失败」团灭屏→0;非失败屏读不到→None,不硬塞)',
        'is_failed': '是否「挑战失败」(团灭屏;bool)',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002  命中画面 ScreenInfo;本识别器全屏 OCR,暂未直接用 area
    ) -> dict | None:
        """读结算画面的战后 HP / 胜负领域事实 → dict(纯读,见模块 docstring 并发安全说明)。

        Args:
            ctx: 运行上下文(``ocr_service``)。
            image: 结算画面截图(analyze 已截,复用;全屏 OCR 命中 analyze 缓存)。
            screen_info: 命中画面的 ScreenInfo。

        Returns:
            ``_SettlementState`` 的 dict 视图(``hp_after`` / ``is_failed``);字段含义见 ``_SettlementState``。
        """
        ocr_texts = [
            r.data for r in ctx.ocr_service.get_ocr_result_list(image=image, rect=None, crop_first=False)
        ]
        hp = parse_settlement_hp(ocr_texts)
        is_failed = any(_FAIL_MARKER in (t or '') for t in ocr_texts)
        if hp is None and is_failed:
            hp = 0   # 团灭 = hp 0 ground truth(parse_settlement_hp 在失败屏常读不到数字)
        return asdict(_SettlementState(hp_after=hp, is_failed=is_failed))
