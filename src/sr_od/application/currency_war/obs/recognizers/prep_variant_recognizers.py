"""货币战争**备战变体画面**额外识别器(免战跳过态 / 选择主角态)。

两个变体与备战画面同布局、同全量可读(出战钮文本不同是唯一差异),识别器 =
``battle_prep_recognizer.read_prep_extras(full_read=True)`` 原样委托——变体 extras
与备战画面完全一致,不叠加不省略。**画面名本身即状态说明**:analyze 精准命中
「货币战争-备战-免战」= 出战钮当前为「跳过(N/N)」(免战牌激活,点击直接进战斗);
命中「货币战争-备战-选择主角」= 出战钮当前为「选择主角」(位面末 BOSS 战前需
重选主角,点击进主角光环选择流程)。

背景:此前两变体无识别器 → extras 恒 null(backend 仅精准命中产出),而这恰是
需要全量读数做决策的状态(免战次数/BOSS 前阵容)。三张选择主角实机样例帧与
免战 fixture 均已验证全量可读。

**并发安全**:与备战识别器同纪律——纯读(不写 self. / 模块全局 / session)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.application.currency_war.obs.recognizers.battle_prep_recognizer import (
    PREP_EXTRAS_DOC,
    read_prep_extras,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext


class BattlePrepSkipRecognizer(ScreenRecognizer):
    """货币战争备战-免战画面(出战钮=跳过(N/N),免战牌激活)额外识别器。"""

    screen_name: str = '货币战争-备战-免战'

    extras_doc: dict[str, str] = {
        **PREP_EXTRAS_DOC,
        'state_note': '本画面 = 备战全量 extras;出战钮形态为「跳过(N/N)」(免战牌激活,'
                      '点「按钮-跳过」直接进战斗,语义同出战)。剩余免战次数见跳过钮文案 N/N。',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002
    ) -> dict | None:
        """免战画面领域事实 → 备战全量 extras(原样委托,纯读)。"""
        return read_prep_extras(ctx, image, full_read=True)


class BattlePrepSelectHeroRecognizer(ScreenRecognizer):
    """货币战争备战-选择主角画面(位面末 BOSS 战前需重选主角)额外识别器。"""

    screen_name: str = '货币战争-备战-选择主角'

    extras_doc: dict[str, str] = {
        **PREP_EXTRAS_DOC,
        'state_note': '本画面 = 备战全量 extras;出战钮形态为「选择主角」(位面末 BOSS 战前'
                      '需重选主角,点「按钮-选择主角」进主角光环选择流程,选定后回备战恢复出战钮)。',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002
    ) -> dict | None:
        """选择主角画面领域事实 → 备战全量 extras(原样委托,纯读)。"""
        return read_prep_extras(ctx, image, full_read=True)
