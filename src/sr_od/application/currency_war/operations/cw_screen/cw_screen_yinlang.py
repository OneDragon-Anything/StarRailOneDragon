# live-verified 2026-08-20:局29 P2r6 银狼策划事件 41min 卡死后建;坐标来自当场实测
# (左卡中心 (755,400) 命中选中)。机制见
# docs/game/gameplay/currency_war.md「银狼我来当策划事件」节(用户口述)。

"""货币战争 银狼「我来当策划」策划事件 overlay 处理 op(r103)。

银狼首次升 2 星(及 5 费升 2 星)触发的二选一 overlay:
- 首次:选项含「升费」(卡面「提升费用至 4 费」;升费腿 = 变为下一个
  费用档的 1 星银狼LV.999 [口述·权威 2026-09-18];机制单一源 =
  docs/game/currency_war/research/equipment_mechanics.md §7)
  vs 其他(破解芯片/专属装备)
  → **默认选升费**(成长滚动投资前提;用户口述:选了升费新费档银狼刷进商店,
  不选则停留当前费用——机会只有一次);
- 5 费升 2 星:两选项都是装备(无法升费),任选其一。

识别:OCR 左/右卡区域,找「提升费用」字样 → 那张是升费卡;无 → 任选(左)。
点卡 = 机械单发(用户裁定 2026-09-14:详情面板检测拆,用户定性 = 详情
弹出 = 点错所致)——选卡后可能自动弹「属性详情」面板(点错区所致),
不判不关,后果归下一帧重入(外循环按当前画面重分派自愈)。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两
段直继承 SrOperation。本屏无 op 内入口门(入口判定归主循环 0 系分发,
分发即门)→ 观察 node = 左右两卡 OCR 桶一次读(入口帧一次读,与现役决策
体读同帧等价)→ ``report_screen_planner_obs`` 落容器 ``planner_opts``
(恒写两卡,空桶照写)→ obs 挂实例属性进决策 node。决策动作 node =
零参决策(kernel 直调仅无 match 防御路径)→ ``classify_planner_leg``
腿型 → 组装 env → 选卡确认链派发即 ``round_success`` 终结交回外循环
(迭代 2026-09-21-pick-planner-equip-immediate-report design §2.0/§2.1,
action_ops.md §1 增补 2:动作 op 确认点击后立即上报完整效果腿,零重入
裁决、零落地相补写面——确认未生效 = 代码 bug,overlay 残留由外循环按
当前画面重识别重派)。本屏无 chosen_* 写端(选择存证行已随删除波 1
退役);本屏 sim 腿 = 不适用(sim 无对应画面段,事件
浮层族即时落定),等价判据主承重 = 实机在册行为锁
(test_cw_screen_two_node_family 两 node 形态锁;接线/基建锁补档 =
开放设计注,见 screens/planner.md §9)。
"""
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_events import (
    classify_planner_leg,
)
from sr_od.application.currency_war.kernel.cw_screen_report.planner import (
    CwScreenPlannerObs,
    report_screen_planner_obs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenYinLang(SrOperation):
    """银狼 2 星奖励画面(用户 2026-08-31 定名;弹窗标题「我来当策划」,银狼升
    2★ 时触发——非随机事件):OCR 两卡 → 策略选卡 → 确认 → 关详情面板。
    两选项=扑满病毒(敌人变扑满)vs 升费卡(升费腿 = 变为下一个费用档的
    1 星银狼LV.999,单位身份保持银狼LV.999、费用档升一级、星级为 1 星
    [口述·权威 2026-09-18]);选卡委托 kernel 纯函数 decide_planner 打分
    (升费卡基础分最高,
    target 银狼线加成/银狼不在场降权;弱化/装备类按通用原则评分)——
    handler 不写死优先级,「何时升费非最优」由策略模块表达(用户定调必接策略)。"""

    # 卡身选中点击点(⚠️ 23:33 交互实锤:卡上半部点击=弹「属性详情」((755,400)/
    # (1225,310) 均触发详情非选中)——**点卡下半部生效选中**(右卡选中+确认亮)。
    # 布局漂移修正(match3 实锤 2026-08-31,见 REPORT W944 §8):卡上移后固定点
    # (1225,480) 落卡外 → 未选中 → 确认无效死循环。改由 area rect 推导:71% 高度
    # (旧实证点击高度比例)+ 详情钮避让 clamp;rect 单一源在 cw_yinlang_star_up.yml。
    CARD_AREA_SCREEN: ClassVar[str] = '货币战争-银狼升星'
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
    # 确认按钮兜底常量(首选 area_center('按钮-骇入确认'):建档 cw_yinlang_star_up.yml
    # rect (1420,575,1560,625) 中心 (1490,600),与本常量同按钮差 1px——交互实锤在档:
    # 在**右侧偏下** (1440-1542,584-615),非画面中央!旧写 (960,615) 是猜的——
    # 局29 事件 1.5h 未消费的另一半原因)
    CONFIRM: ClassVar[Point] = Point(1491, 600)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-策划事件')
        # 观察结果(观察 node 产物,决策动作 node 消费;options = 入口帧一次
        # 读,恒两元素 0=左卡/1=右卡)。
        self._obs: CwScreenPlannerObs | None = None

    def _card_point(self, idx: int) -> Point:
        """卡选中点击点 = area rect 相对几何推导(中心 x,71% 高度)。

        详情钮避让 = rect 底缘上移 DETAIL_MARGIN_RATIO(相对几何,W952 返修
        ——绝对 y 常数对多布局不成立,见类属性注释)。两比例皆 rect 相对,
        布局再漂移时只更 yml rect,本方法零改;rect 缺失回退旧实证 rect。
        确认钮动画/多步 overlay 零覆盖声明:本方法只产选中点,确认链与
        上报归动作 op,本 op 派发即终结交回外循环。
        """
        area = self.ctx.screen_loader.get_area(
            CwScreenYinLang.CARD_AREA_SCREEN,
            CwScreenYinLang.CARD_AREAS[idx])
        if area is not None:
            rect = area.pc_rect
        else:
            lx, ly, rx, ry = CwScreenYinLang._LEGACY_CARD_RECTS[idx]
            rect = Rect(lx, ly, rx, ry)
        y = min(rect.y1 + int(rect.height * CwScreenYinLang.SELECT_Y_RATIO),
                rect.y2 - int(rect.height * CwScreenYinLang.DETAIL_MARGIN_RATIO))
        return Point(rect.center.x, y)

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """左右两卡 OCR 桶一次读 → report 落容器(恒写两卡,空桶照写;
        match/gs 缺席的局外兜底路径跳过 report,决策走 kernel 直调防御
        分支,分支原样)。"""
        screen = self.last_screenshot
        # OCR 两卡区域文字:单次全图读(贵操作只算一次),文本归属 =
        # 中心点落入建档两卡 rect(坐标单一真相源回 yml;判定语义 =
        # 中心点,先例 _anchor_hit_full_ocr 同式;area 缺失回退旧实证
        # rect。捕获集变化申报 = 旧 y 带 [300,420] → 卡全域 rect,卡内
        # 文本全属该卡语义,classify 关键词匹配面不变——设计 §2.4)。
        _rects: list[Rect] = []
        for _area_name in self.CARD_AREAS:
            _area = self.ctx.screen_loader.get_area(
                CwScreenYinLang.CARD_AREA_SCREEN, _area_name)
            if _area is not None and _area.pc_rect is not None:
                _rects.append(_area.pc_rect)
            else:
                _lx, _ly, _rx, _ry = CwScreenYinLang._LEGACY_CARD_RECTS[
                    len(_rects)]
                _rects.append(Rect(_lx, _ly, _rx, _ry))
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        left_text, right_text = [], []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cx = mrl.max.center.x
            cy = mrl.max.center.y
            for _i, _rect in enumerate(_rects):
                if _rect.x1 <= cx <= _rect.x2 and _rect.y1 <= cy <= _rect.y2:
                    (left_text if _i == 0 else right_text).append(text)
                    break
        from sr_od.application.currency_war.kernel.cw_events import PlannerOption
        obs = CwScreenPlannerObs(
            on_screen=True,
            options=[PlannerOption(idx=0, text=' '.join(left_text)),
                     PlannerOption(idx=1, text=' '.join(right_text))],
            screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_planner_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=5)
    def act(self) -> OperationRoundResult:
        """零参决策 → 腿型判定 → 组装 env → 派发即 ``round_success`` 终结。

        动作 op ``CwActionPickPlannerOp`` 确认点击后立即上报完整效果腿
        (单相即时上报,迭代 2026-09-21-pick-planner-equip-immediate-report
        design §2.0/§2.1)——本 op 派发即终结交回外循环重观察,零重入
        裁决轮、零证据闩(确认未生效 = 代码 bug,overlay 残留由外循环按
        当前画面重识别重派)。"""
        options = self._obs.options if self._obs is not None else []
        # 策略层决策(W953 批1 接线:唯一入口=策略对象,handler 禁 kernel 直调;
        # 写槽已由 report 落容器 → 零参决策。kernel 直调仅保留无 match 防御
        # 路径(局外独立跑;规约=沿用 cw_screen_invest_env 同款写法)。
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is not None:
            pick = _match.strategy.decide_planner()
        else:
            from sr_od.application.currency_war.kernel.cw_events import decide_planner

            # 换源(登记集消点):防御视图 = 裸容器(全域未观察空视图;
            # decide_planner 局面消费面未观察态 = 空视图口径)。
            # kernel 返回值包装动作子类型
            # (终态契约 §2.2:kernel 纯函数零触碰,包装归入口/防御路径)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                GAME_STATE_SCHEMA_VERSION,
                GameState,
            )
            from sr_od.application.currency_war.kernel.cw_vocab import (
                CwActionPickPlannerParam,
            )
            _kpick = decide_planner(list(options),
                                    GameState(schema_version=GAME_STATE_SCHEMA_VERSION),
                                    None)
            pick = CwActionPickPlannerParam(idx=_kpick.idx, reason=_kpick.reason)
        target = self._card_point(pick.idx)
        # 腿型载荷(银狼闭环 design §2.1①):判定单源 = kernel
        # classify_planner_leg(装备域优先);随 env 透传给动作 op 上报
        # (确认点击后立即写完整效果腿,单相即时上报)。
        _opt_text = (options[pick.idx].text
                     if 0 <= pick.idx < len(options) else '')
        leg_type, norm_item = classify_planner_leg(_opt_text)
        log.info('[cw][planner] 策划决策:%s → %s卡(%s) leg=%s/%s',
                 pick.reason, '左' if pick.idx == 0 else '右',
                 options[pick.idx].text[:24], leg_type, norm_item or '-')
        # 点卡选中 → 确认链经工厂(统一动作工厂批4:体迁
        # ``cw_pick_planner_action.CwActionPickPlannerOp``,方法级替身缝保留);
        # 决策半(策略选卡/腿型判定)留守上方,派发实例 = 策略 pick 本体,
        # 机械参数 target 经 env 传递。派发即 round_success 终结交回外循环
        # (效果腿已在动作 op 内即时上报;确认未生效 = 代码 bug,外循环
        # 按当前画面重识别重派)。
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, target=target,
                                  leg_type=leg_type, norm_item=norm_item)
        action_op_for(pick, self.ctx, _env).execute()
        return self.round_success('策划选卡已派发(结果已即时上报)')
