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
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.telemetry.recorder import record_event_choice
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenPlanner(SrOperation):
    """银狼 2 星奖励画面(用户 2026-08-31 定名;弹窗标题「我来当策划」,银狼升
    2★ 时触发——非随机事件):OCR 两卡 → 策略选卡 → 确认 → 关详情面板。
    两选项=扑满病毒(敌人变扑满)vs 银狼LV.999(费用升至 4,变 1 星银狼
    LV.999);选卡委托 kernel 纯函数 decide_planner 打分(升费卡基础分最高,
    target 银狼线加成/银狼不在场降权;弱化/装备类按通用原则评分)——
    handler 不写死优先级,「何时升费非最优」由策略模块表达(用户定调必接策略)。"""

    # 卡身选中点击点(⚠️ 23:33 交互实锤:卡上半部点击=弹「属性详情」((755,400)/
    # (1225,310) 均触发详情非选中)——**点卡下半部生效选中**(右卡选中+确认亮)。
    # 布局漂移修正(match3 实锤 2026-08-31,见 REPORT W944 §8):卡上移后固定点
    # (1225,480) 落卡外 → 未选中 → 确认无效死循环。改由 area rect 推导:71% 高度
    # (旧实证点击高度比例)+ 详情钮避让 clamp;rect 单一源在 cw_hacker_planner.yml。
    CARD_AREA_SCREEN: ClassVar[str] = '货币战争-骇入策划'
    CARD_AREAS: ClassVar[tuple[str, str]] = ('骇入选项-左卡', '骇入选项-右卡')
    # 点卡/确认按住时长(match2 复盘实证 prep_actions 参数;漏定义=live
    # AttributeError,match3 首局实锤——类属性与引用点同批落码的纪律)
    CLICK_PRESS_TIME: ClassVar[float] = 0.15
    # 选中点击高度比例:旧实证 (755/1225,480) 对旧 rect y 280-560 = 卡内 71%
    # (⚠️ 迁移样本 n=1,08-20 局29 单次交互实证;半区经验值非充分统计)。
    SELECT_Y_RATIO: ClassVar[float] = 0.71
    # 详情钮避让 = **rect 底缘上移固定比例**(W952 审计 P1-1/P2-1 返修):实帧
    # 详情钮带贴卡底(高 20-28px ≈ 卡高 8-10%,含余量取 11%)。绝对 y 常数对
    # 多布局不成立(单帧耦合:弹窗整体下移 >46px 即被压回详情危险半区,
    # legacy 兜底 478 会被压成 425 落 (755,400) 型危险带);相对几何下布局
    # 再漂移恢复「只更 yml」承诺。clamp 语义 = 详情钮在其上方。
    DETAIL_MARGIN_RATIO: ClassVar[float] = 0.11
    # 旧实证 rect(match3 布局实测前为单一源;area 缺失时兜底)。
    _LEGACY_CARD_RECTS: ClassVar[tuple[tuple[int, int, int, int], ...]] = (
        (500, 280, 980, 560), (1020, 280, 1500, 560))
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

    def _card_point(self, idx: int) -> Point:
        """卡选中点击点 = area rect 相对几何推导(中心 x,71% 高度)。

        详情钮避让 = rect 底缘上移 DETAIL_MARGIN_RATIO(相对几何,W952 返修
        ——绝对 y 常数对多布局不成立,见类属性注释)。两比例皆 rect 相对,
        布局再漂移时只更 yml rect,本方法零改;rect 缺失回退旧实证 rect。
        确认钮动画/多步 overlay 零覆盖声明:本方法只产选中点,确认收尾的
        失败语义归 confirm_and_verify 验关(动画期误判可能仍开)。
        """
        area = self.ctx.screen_loader.get_area(
            CwScreenPlanner.CARD_AREA_SCREEN,
            CwScreenPlanner.CARD_AREAS[idx])
        if area is not None:
            rect = area.pc_rect
        else:
            lx, ly, rx, ry = CwScreenPlanner._LEGACY_CARD_RECTS[idx]
            rect = Rect(lx, ly, rx, ry)
        y = min(rect.y1 + int(rect.height * CwScreenPlanner.SELECT_Y_RATIO),
                rect.y2 - int(rect.height * CwScreenPlanner.DETAIL_MARGIN_RATIO))
        return Point(rect.center.x, y)

    @operation_node(name='处理策划事件', is_start_node=True, node_max_retry_times=5)
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
        from sr_od.application.currency_war.kernel.cw_events import PlannerOption
        options = [PlannerOption(idx=0, text=' '.join(left_text)),
                   PlannerOption(idx=1, text=' '.join(right_text))]
        # 2. 策略层决策(W953 批1 接线:唯一入口=策略对象,handler 禁 kernel 直调;
        # 见 .debug/temp/currency_war/w953_overlay_strategy/DESIGN.md §3.4)。
        # DecisionV2Strategy.decide_planner 委托同一 kernel 纯函数(kernel 版保底,
        # 本批零行为变化;局面感知升级归批4)。kernel 直调仅保留无 match 防御路径
        # (局外独立跑;规约=沿用 cw_screen_invest_env 同款写法)。
        from sr_od.application.currency_war.kernel.cw_state import GameState
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is not None:
            _st = _match.session.last_state
            _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
            pick = _match.strategy.decide_planner(
                options, _st or GameState(), _match.session, _cfg)
        else:
            from sr_od.application.currency_war.kernel.cw_events import decide_planner
            pick = decide_planner(options, GameState(), None)
        target = self._card_point(pick.idx)
        log.info('[cw][planner] 策划决策:%s → %s卡(%s)',
                 pick.reason, '左' if pick.idx == 0 else '右',
                 options[pick.idx].text[:24])
        # 遥测:左右卡 OCR 文本+选择落账本(升费机会只有一次,
        # 选错代价复盘依赖此行;此前只 log)。
        record_event_choice('planner_event',
                            [{'text': o.text} for o in options],
                            pick.idx, pick.reason)
        # 3. 点卡选中(⚠️ 避开卡内「详情」按钮区 x~880-950/y~420-450——局29 手动点
        # (755,400) 触发详情面板的实证;点卡身上部 y=310)
        self.ctx.controller.mouse_move(target)
        self.ctx.controller.click(target, press_time=self.CLICK_PRESS_TIME)
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
        from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
            confirm_and_verify,
        )
        return confirm_and_verify(
            self, confirm_point=self.CONFIRM,
            entry_keyword='我来当策划', tag='cw-planner',
            press_time=self.CLICK_PRESS_TIME)
