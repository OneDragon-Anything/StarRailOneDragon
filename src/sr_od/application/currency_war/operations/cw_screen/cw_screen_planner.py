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

统一观察架构逐屏迁移(试点步骤 3;架构设计 §9.2 迁移步骤 4 + 开放问题清单
B3 三段走第二段「补给 + 余事件屏按族批量」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(两端口完整在场 → 五段生命周期新路径;缺省 None =
生产直连旧路径,生产行为零变化 §9.1)。迁移手法单一源 = 盛会之星先例
(reviews/T-215-r1.md 验收;T-215-r1 §五.5 统一形态注意项 = lifecycle_observe
消费 ``_observation_port()`` 位):handle 体纯移入 ``_handle_overlay``
(两路径共享零转录);**本屏无 op 内入口门**(入口判定归主循环 0 系分发,
observe 段 = 轻观察帧引用,盛会之星同式);本屏无 on_outcome 落地登记件
(§6.4 收编面无事件屏 chosen 行;planner 无 chosen_* 写端,选择存证行已随
删除波 1 退役)。本屏 sim 腿 = 不适用(F11 例外清单:sim 无对应画面段,
事件浮层族即时落定),等价判据主承重 = 实机在册行为锁(test_cw_planner_
strategy_wiring + test_cw_infra_locks + 本批锁
test_cw_obs_arch_event_screens_step3)。
"""
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


@dataclass
class PlannerObservation:
    """策划事件观察 payload(五段之段1产物;试点步骤 3 实机转录形态)。

    observe 段 = 轻观察帧引用(卡面 OCR 读取归共享动作体现役内聚,避免新增
    读屏;实机识别域载体,不出端口,架构设计 §2.1;sim 适配器 = 不适用,
    F11 例外清单)。
    """

    screen: Any = None


class PlannerLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,试点步骤 3)。

    本屏无 op 内入口门(分发即门),适配器仅装配帧引用。sim 实现 =
    不适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenPlanner') -> PlannerObservation:
        return op._observe_frame()


class CwScreenPlanner(CwScreenOpBase):
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
    # 确认按钮兜底常量(首选 area_center('按钮-骇入确认'):建档 cw_hacker_planner.yml
    # rect (1420,575,1560,625) 中心 (1490,600),与本常量同按钮差 1px——交互实锤在档:
    # 在**右侧偏下** (1440-1542,584-615),非画面中央!旧写 (960,615) 是猜的——
    # 局29 事件 1.5h 未消费的另一半原因)
    CONFIRM: ClassVar[Point] = Point(1491, 600)
    # 详情面板关闭 ×(归一化 780,220 → 1080p;23:30 实测点击生效)
    DETAIL_CLOSE: ClassVar[Point] = Point(1497, 238)

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-策划事件')
        # 适配器位缺省装配(试点步骤 3;先例 = CwScreenPrep/盛会之星):观察口 =
        # 实机适配器(帧引用封口);动作口 = None = 直连现役共享体
        # ``_handle_overlay``(多步链,无单意图 act 分派面)。on_outcome 注册
        # 表:本屏无落地登记件(§6.4 收编面无事件屏 chosen 行,见模块
        # docstring)。
        self._observation_adapter = PlannerLiveObservationAdapter()
        # 确认已发待重入裁决标志(验证废除形态):本屏分发即门(无 op 内入口
        # 守卫),重入出口裁决见 _handle_overlay 顶部。
        self._confirm_pending: bool = False

    def _observe_frame(self) -> PlannerObservation:
        """轻观察帧装配(实机适配器①封口内容;卡面读取归共享体现役内聚)。"""
        return PlannerObservation(screen=self.last_screenshot)

    def _card_point(self, idx: int) -> Point:
        """卡选中点击点 = area rect 相对几何推导(中心 x,71% 高度)。

        详情钮避让 = rect 底缘上移 DETAIL_MARGIN_RATIO(相对几何,W952 返修
        ——绝对 y 常数对多布局不成立,见类属性注释)。两比例皆 rect 相对,
        布局再漂移时只更 yml rect,本方法零改;rect 缺失回退旧实证 rect。
        确认钮动画/多步 overlay 零覆盖声明:本方法只产选中点,确认收尾的
        交回语义 = 机械 round_retry(验证废除;重入裁决见 _handle_overlay 顶部)。
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
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run):
        # cw_game_ports 两端口完整在场(= 测试 harness 显式装配)→ 五段生命
        # 周期新路径;缺省 None = 生产直连旧路径(原序列整体移入
        # _handle_overlay 共享体,试点等价门通过前生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        return self._handle_overlay()

    def _handle_overlay(self) -> OperationRoundResult:
        """选卡+确认链(旧 handle 体纯移入,两路径共享零转录;试点步骤 3,
        先例 = 盛会之星 ``_do_action`` 共享式)。策略接线(W953:唯一入口 =
        策略对象,kernel 直调仅无 match 防御分支)/press_time 加固/详情面板
        防御语义逐位保留;验关半拆除(用户裁定 2026-09-10)。"""
        # 重入裁决(观察驱动,M7 同化先例 + cw_entry_start 守卫先例):本屏
        # 分发即门(无 op 内入口守卫),round_retry 重入不经外循环分发 →
        # 顶部出口门补位:入口词不在 = overlay 已关(上轮确认已落地)→
        # success 交回外循环;在 = 重走选卡+确认(计节点预算)。
        if self._confirm_pending:
            self._confirm_pending = False
            if not self.round_by_ocr(self.screenshot(), '我来当策划',
                                     lcs_percent=0.5).is_success:
                return self.round_success('策划事件已确认(重入观察裁决)',
                                          wait=2.0)
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
        from sr_od.application.currency_war.kernel.cw_game_state import (
            BS_SCHEMA_VERSION,
            GameState,
            board_state_of,
        )
        options = [PlannerOption(idx=0, text=' '.join(left_text)),
                   PlannerOption(idx=1, text=' '.join(right_text))]
        # 2. 策略层决策(W953 批1 接线:唯一入口=策略对象,handler 禁 kernel 直调;
        # 见 .debug/temp/currency_war/w953_overlay_strategy/DESIGN.md §3.4)。
        # DecisionV2Strategy.decide_planner 委托同一 kernel 纯函数(kernel 版保底,
        # 本批零行为变化;局面感知升级归批4)。kernel 直调仅保留无 match 防御路径
        # (局外独立跑;规约=沿用 cw_screen_invest_env 同款写法)。
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is not None:
            # 决策输入消费切换(迁移批次二):GameState 视图替 last_state 直读。
            _st = board_state_of(_match.session)
            _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
            pick = _match.strategy.decide_planner(
                options, _st, _match.session, _cfg)
        else:
            from sr_od.application.currency_war.kernel.cw_events import decide_planner
            # 换源 T-146(登记集消点):防御视图 = 裸容器(全域未观察空视图;
            # decide_planner 局面消费面未观察态等价旧空帧);旧合成
            # CwSimFrame + 过渡桥装箱退役。
            pick = decide_planner(options,
                                  GameState(schema_version=BS_SCHEMA_VERSION),
                                  None)
        target = self._card_point(pick.idx)
        log.info('[cw][planner] 策划决策:%s → %s卡(%s)',
                 pick.reason, '左' if pick.idx == 0 else '右',
                 options[pick.idx].text[:24])
        # (planner 左右卡存证行已随 exogenous 流写入端退役删除——删除波 1。)
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
        # 4. 点确认+机械交回(r326/P1⑦ 防线语义由重入裁决+预算耗尽 bail
        # 承接,验关半拆除——用户裁定 2026-09-10:动作 op 禁验证)。
        # r327(终审 E):裁决词用全词「我来当策划」(入场锚同词,
        # cw_hacker_planner.yml:26 live-verified)——短词「策划」
        # 在艺术字漏读时可能假通过。
        from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
            emit_overlay_confirm,
        )
        self._confirm_pending = True
        # 确认点主源 = 建档「按钮-骇入确认」中心(坐标单一真相源);area 缺失回退
        # 兜底常量(megastar/invest_env 同款派生 + 缺损兜底模式)。
        _confirm = (area_center(self.ctx, '按钮-骇入确认', CwScreenPlanner.CARD_AREA_SCREEN)
                    or CwScreenPlanner.CONFIRM)
        return emit_overlay_confirm(
            self, confirm_point=_confirm,
            entry_keyword='我来当策划', tag='cw-planner',
            press_time=self.CLICK_PRESS_TIME)

    # ---- 五段生命周期(统一观察架构 §5.1;试点步骤 3,先例 = 盛会之星)----

    def lifecycle_observe(self
                          ) -> tuple[PlannerObservation,
                                     OperationRoundResult | None]:
        """段1 observe:本屏无 op 内入口门(入口判定归主循环 0 系分发,
        分发即门)→ 轻观察 payload 直接交后续段(盛会之星同式,帧引用
        载体)。"""
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_frame())
        return obs, None

    def lifecycle_decision_cycle(self, payload: PlannerObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作内聚):decide+act 内聚于 ``_handle_overlay`` 共享体
        (卡面 OCR/策略决策/遥测/点卡/详情面板防御/确认收尾全部原位,两路径
        共享零转录)。段5 on_outcome = 本屏无落地登记件(注册表缺席 = 零
        动作,见 __init__ 申报);轮次结果语义在共享体内逐位保留(段迹到
        act)。"""
        self._lifecycle_mark('decide')
        rs = self._handle_overlay()
        self._lifecycle_mark('act')
        return rs
