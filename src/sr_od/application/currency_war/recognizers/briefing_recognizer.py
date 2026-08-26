"""货币战争**简报画面**额外识别器(per-screen recognizer)。

``analyze_screen`` 精准命中「货币战争-简报」后,框架按 ``screen_name`` 查表调用本识别器,把简报画面的
结构化领域事实(**敌人词缀** + **3 位面首领名**)塞进返回的 ``extras``,供智能体 / HTTP 消费方直接读用,
不必自己 OCR / 看图。词缀 / boss 是敌人对策的核心输入(``mechanics_fit`` / ``boss_fit``)。

**并发安全(关键)**:本 ``recognize`` 必须是**纯读** —— 不写 ``self.``、不写模块全局、不读写
``cw_match.session``(同 ``battle_prep_recognizer``,原因见该模块)。故:

- ``affixes`` / ``bosses`` 复用 ``cw_briefing_obs.read_affixes`` / ``read_bosses`` —— 它们是**纯 OCR + 正则**
  (只经 ``cw_obs_core._area_rect`` 取 area + ``_ocr`` OCR + 正则筛选,不写任何 session / 全局),可安全复用。
- **不复用 ``read_affix_effect``**:它语义上要求**先 click 词缀弹 tooltip 再 OCR**(recognizer 是纯读观察,
  不 click);recognizer 不产词缀效果原文(需要时消费方自己点开查,或走 ``affix_effects_data`` 注册表)。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.application.currency_war.cw_briefing_obs import read_affixes, read_bosses
from sr_od.application.currency_war.cw_obs_core import BRIEFING_SCREEN

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext


@dataclass
class _BriefingState:
    """简报画面领域事实(组装后 ``asdict()`` 转 dict 回传;类型化单一真相源)。

    字段类型对齐各 reader 返回(读不到均返空 ``list``,不伪造)。
    """

    affixes: list[str]   # 敌人词缀 OCR 原名(read_affixes,读不到→[])
    bosses: list[str]    # 3 boss 名候选集(read_bosses,画面 x 序无位面序语义,ADR-0397;读不到→[])


class BriefingRecognizer(ScreenRecognizer):
    """货币战争简报画面额外识别器。"""

    screen_name: str = BRIEFING_SCREEN   # '货币战争-简报'

    # extras 字段说明(随 analyze 响应平级返回 extras_doc;键集与 _BriefingState 一致)
    extras_doc: dict[str, str] = {
        'affixes': '敌人词缀 OCR 原名 list(读不到→[],不伪造)。仅名不含效果原文 —— '
                   'recognizer 纯读不 click,效果需消费方自查或走 affix_effects_data 注册表',
        'bosses': '3 位面首领名候选集 list(画面 x 序,无位面序语义,勿按序当 plane_bosses 用;读不到→[];ADR-0397)',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002  命中画面 ScreenInfo;本识别器经 cw_obs_core 读 area,暂未直接用
    ) -> dict | None:
        """读简报画面的敌人词缀 / 首领领域事实 → dict(纯读,见模块 docstring 并发安全说明)。

        Args:
            ctx: 运行上下文。
            image: 简报画面截图(analyze 已截,复用)。
            screen_info: 命中画面的 ScreenInfo。

        Returns:
            ``_BriefingState`` 的 dict 视图(``affixes`` / ``bosses``);字段含义见 ``_BriefingState``。
        """
        return asdict(_BriefingState(
            affixes=read_affixes(ctx, image),
            bosses=read_bosses(ctx, image),
        ))
