# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争**投资策略画面**额外识别器(per-screen recognizer)。

``analyze_screen`` 精准命中「货币战争-投资策略」后,框架按 ``screen_name`` 查表调用本识别器,把当前
**3 选 1 投资策略选项名**塞进返回的 ``extras``,供智能体 / HTTP 消费方直接读用,不必自己 OCR / 看图。
投资策略是局内核心决策(选哪个增益),选项名是决策输入。

**并发安全(关键)**:本 ``recognize`` 必须是**纯读** —— 不写 ``self.``、不写模块全局、不读写
``cw_match.session``(同 ``battle_prep_recognizer``)。故只经 ``cw_obs_core._area_rect`` 取
``区域-卡名行`` area + ``_ocr`` OCR + 正则筛选,**不碰** session / 全局。

**刻意不产 rarity(品质)**:投资策略全量在 ``investment_strategies.md``(315 条),代码注册表
``INVESTMENT_STRATEGIES`` 只收 T0(``cw_investments``),非 T0 透传原名(rarity 留空);按 spec
「不稳定字段不硬塞」,v1 只产可靠的名列表,rarity 待注册表全量后再加。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.application.currency_war.cw_obs_core import _area_rect, _ocr

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext

# 投资策略屏 screen_info(currency_war_invest_strategy.yml)
INVEST_STRATEGY_SCREEN: str = '货币战争-投资策略'
A_STRATEGY_NAMES: str = '区域-卡名行'   # 3 张策略卡名行(与投资策略 yml 的 area 名一致)

# 卡名筛选:投资策略名 2-10 字中文为主(乱成一锅粥5 / 盗用身份4 / 远见2 / 团队力量·金5 等)
_NAME_MIN, _NAME_MAX = 2, 10


@dataclass
class _InvestStrategyState:
    """投资策略画面领域事实(组装后 ``asdict()`` 转 dict 回传)。"""

    strategies: list[str]   # 当前 3 选 1 投资策略名(OCR,读不到→[])


class InvestStrategyRecognizer(ScreenRecognizer):
    """货币战争投资策略画面额外识别器。"""

    screen_name: str = INVEST_STRATEGY_SCREEN   # '货币战争-投资策略'

    # extras 字段说明(随 analyze 响应平级返回 extras_doc;键集与 _InvestStrategyState 一致)
    extras_doc: dict[str, str] = {
        'strategies': '当前 3 选 1 投资策略选项名 list(OCR;读不到→[])。'
                      '刻意不产 rarity(注册表未全量,非 T0 透传原名,见模块 docstring)',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002  命中画面 ScreenInfo;经 cw_obs_core 读 area,暂未直接用
    ) -> dict | None:
        """读投资策略画面的 3 选 1 选项名 → dict(纯读,见模块 docstring 并发安全说明)。

        Args:
            ctx: 运行上下文。
            image: 投资策略画面截图(analyze 已截,复用)。
            screen_info: 命中画面的 ScreenInfo。

        Returns:
            ``_InvestStrategyState`` 的 dict 视图(``strategies``);字段含义见 ``_InvestStrategyState``。
        """
        rect = _area_rect(ctx, A_STRATEGY_NAMES, INVEST_STRATEGY_SCREEN)
        strategies: list[str] = []
        for r in _ocr(ctx, image, rect):
            name = (r.data or '').strip()
            # 中文为主、长度合理、滤纯数字/符号噪声(投资策略名含「·金/·银/·彩」符号但必有中文)
            if _NAME_MIN <= len(name) <= _NAME_MAX and re.search(r'[一-鿿]', name):
                strategies.append(name)
        return asdict(_InvestStrategyState(strategies=strategies))
