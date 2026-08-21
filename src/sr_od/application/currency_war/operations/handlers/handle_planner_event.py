# live-verified 2026-08-20:局29 P2r6 银狼策划事件 41min 卡死后建;坐标来自当场实测
# (左卡中心 (755,400) 命中选中;详情面板 × 归一化 775,245→(1488,265))。机制见
# docs/game/gameplay/currency_war.md「银狼我来当策划事件」节(用户口述)。

"""货币战争 银狼「我来当策划」策划事件 overlay 处理 op(r103)。

银狼首次升 2 星(及 5 费升 2 星)触发的二选一 overlay:
- 首次:选项含「升费」(提升费用至 4 费,变为 1 星银狼)vs 其他(破解芯片/专属装备)
  → **默认选升费**(成长滚动投资前提;用户口述:选了升费新费档银狼刷进商店,
  不选则停留当前费用——机会只有一次);
- 5 费升 2 星:两选项都是装备(无法升费),任选其一。

识别:OCR 左/右卡区域,找「提升费用」字样 → 那张是升费卡;无 → 任选(左)。
选卡后可能自动弹「属性详情」面板 → 点右上 × 关闭。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandlePlannerEvent(SrOperation):
    """银狼策划事件 overlay:OCR 两卡 → 策略选卡 → 确认 → 关详情面板。"""

    # 卡身选中点击点(⚠️ 23:33 交互实锤:卡上半部点击=弹「属性详情」((755,400)/
    # (1225,310) 均触发详情非选中)——**点卡下半部 y≈480 生效选中**(右卡选中+
    # 确认亮,点确认消费事件成功)。别用卡中心/上部。
    CARD_LEFT: ClassVar[Point] = Point(755, 480)
    CARD_RIGHT: ClassVar[Point] = Point(1225, 480)
    # 卡文字 OCR 过滤带(卡描述在 y~330-370;标题 y~376)
    CARD_TEXT_Y_LO: ClassVar[int] = 300
    CARD_TEXT_Y_HI: ClassVar[int] = 420
    # 确认按钮(⚠️ 交互实锤:在**右侧偏下** (1440-1542,584-615),非画面中央!
    # 旧写 (960,615) 是猜的——局29 事件 1.5h 未消费的另一半原因)
    CONFIRM: ClassVar[Point] = Point(1491, 600)
    # 详情面板关闭 ×(归一化 780,220 → 1080p;23:30 实测点击生效)
    DETAIL_CLOSE: ClassVar[Point] = Point(1497, 238)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-策划事件')

    @operation_node(node_name='处理策划事件', is_start_node=True, node_max_retry_times=5)
    def handle(self) -> OperationRoundResult:
        screen = self.screenshot()
        # 1. OCR 两卡区域文字(卡描述 y~300-420 带,左卡 x<960 / 右卡 x≥960)
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        left_text, right_text = [], []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            cx = mrl.max.center.x
            if not (self.CARD_TEXT_Y_LO <= cy <= self.CARD_TEXT_Y_HI):
                continue
            (left_text if cx < 960 else right_text).append(text)
        from sr_od.application.currency_war.cw_events import (
            PlannerOption,
            decide_planner,
        )
        options = [PlannerOption(idx=0, text=' '.join(left_text)),
                   PlannerOption(idx=1, text=' '.join(right_text))]
        # 2. 策略模块决策(r104 用户定调:由策略模块定,handler 不写死)
        _match = getattr(self.ctx, 'cw_match', None)
        _tgt = None
        _st = None
        if _match is not None:
            _tgt = _match.session.target_comp
            _st = _match.session.last_state
        from sr_od.application.currency_war.cw_state import GameState
        pick = decide_planner(options, _st or GameState(), _tgt)
        target = self.CARD_LEFT if pick.idx == 0 else self.CARD_RIGHT
        log.info('[cw][planner] 策划决策:%s → %s卡(%s)',
                 pick.reason, '左' if pick.idx == 0 else '右',
                 options[pick.idx].text[:24])
        # 3. 点卡选中(⚠️ 避开卡内「详情」按钮区 x~880-950/y~420-450——局29 手动点
        # (755,400) 触发详情面板的实证;点卡身上部 y=310)
        self.ctx.controller.mouse_move(target)
        self.ctx.controller.click(target)
        time.sleep(1.2)   # 等选中动画
        # 3b. 验选中(「已选择」或确认亮);若弹出详情面板(点错区)→ 关掉重试点卡
        screen_m = self.screenshot()
        ocr_m = self.ctx.ocr_service.get_ocr_result_map(
            image=screen_m, rect=None, color_range=None, crop_first=False,
        )
        if any('属性详情' in t for t in ocr_m):
            log.info('[cw][planner] 点卡触发详情面板(非选中)→ 关闭后 retry 重点')
            self.ctx.controller.click(self.DETAIL_CLOSE)
            time.sleep(0.8)
            return self.round_retry(wait=1)
        # 4. 点确认+验关(r326/P1⑦ 等画面审查:确认落空→
        # overlay 不关→外环反复重跑本节点——confirm_and_verify
        # 统一收尾,计节点预算兜底替代无限重点)。
        # r327(终审 E):验证词用全词「我来当策划」(入场锚同词,
        # cw_hacker_planner.yml:26 live-verified)——短词「策划」
        # 在艺术字漏读时可能假通过。
        from sr_od.application.currency_war.operations.handlers._overlay_confirm import (
            confirm_and_verify,
        )
        return confirm_and_verify(
            self, confirm_point=self.CONFIRM,
            entry_keyword='我来当策划', tag='cw-planner')
