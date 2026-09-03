"""货币战争 备战触发型 overlay 族 op(W971 P3a;06-overlays §4 统一模式)。

七 overlay 一 op:盛会之星 / 列车同行 / 武装箱 / 祈愿试炼 / 骇入策划 / 命运卜者 / 星徽秘典。
统一模式(W971 06-overlays §4):识别 overlay(id_mark)→ 待选项识别 + 决策 + 点选确认
→ 完成承诺 = 固定 1.0s(CW_OVERLAY_SETTLE_S,DD-011 形态①)交回循环。

现役 handler 的完整逻辑(读法 + 策略函数 decide_planner 等)本批不改:五 op 薄封装
委托现役 handler op,handler 退役与「点选 + 确认」原子两步化归后续批。例外:
- 星徽秘典(CwScreenBookcard)现役逻辑内联在 cw_loop 0i 分支(无独立 op),按其
  现役读法直写(决策待定 = 沿用 decide_star_tome + fallback 卡1);
- 盛会之星(CwScreenMegastar)已内联旧巨星节点执行器实现(旧「提交后验证+节点预算」基类
  退役批;完成验证模型选型判据见 NAMING.md §6)。
"""
import time
from collections.abc import Callable
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.obs.cw_node_obs import read_megastar_options
from sr_od.application.currency_war.operations.cw_flow.cw_flow_const import (
    CW_OVERLAY_SETTLE_S,
)
from sr_od.application.currency_war.operations.handlers._overlay_confirm import (
    safe_click,
)
from sr_od.application.currency_war.operations.handlers.handle_bookcard import (
    HandleBookcard,  # noqa: F401  专家邀请函链现状参照(七 overlay 外,不封装)
)
from sr_od.application.currency_war.operations.handlers.handle_fortune_picker import (
    HandleFortunePicker,
)
from sr_od.application.currency_war.operations.handlers.handle_planner_event import (
    HandlePlannerEvent,
)
from sr_od.application.currency_war.operations.handlers.handle_select_partner import (
    HandleSelectPartner,
)
from sr_od.application.currency_war.operations.handlers.handle_wish_trial import (
    HandleWishTrial,
)
from sr_od.application.currency_war.telemetry.recorder import record_event_choice
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 现役 handler 工厂(ctx → handler op)。
HandlerFactory = Callable[[SrContext], SrOperation]


class CwScreenOverlay(SrOperation):
    """overlay 族基类:id_mark 入口识别 → 委托现役 handler → 固定 1.0s 交回。

    入口识别不中 → round_fail(交上层循环/编排重新分流,不在错屏盲跑 handler);
    handler 失败原样上抛其结果(其内部 retry 预算已兜底);成功后固定时长等待
    (overlay 关闭动画)交回。
    """

    #: op 显示名(子类必设,构造参数化,基类不做无参默认)。
    LABEL: ClassVar[str]
    #: overlay 画面名 / 入口 id_mark area(screen_info 单一源)。
    SCREEN_NAME: ClassVar[str]
    MARK_AREA: ClassVar[str]
    #: 现役 handler 工厂(薄封装委托;P3b handler 退役后内联原子两步)。
    HANDLER_FACTORY: ClassVar[HandlerFactory]

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=f'货币战争-{self.LABEL}')

    @operation_node(name='overlay处理', is_start_node=True, node_max_retry_times=3)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success:
            return self.round_fail(f'非{self.LABEL}画面')
        _handler = self.HANDLER_FACTORY(self.ctx)
        _result = self.round_by_op_result(_handler.execute())
        if not _result.is_success:
            return _result
        # 完成承诺 = DD-011 形态①固定时长(overlay 关闭动画窗,06-overlays §4)。
        return self.round_success(f'{self.LABEL}处理完成', wait=CW_OVERLAY_SETTLE_S)


class CwScreenMegastar(SrOperation):
    """盛会之星:候选立绘 → decide_megastar 选巨星 + 确认(旧巨星节点执行器内联)。

    **完成验证模型 = op 内验证 + 节点预算**(NAMING.md §6 选型判据「多步序列/
    每步可独立失败/历史卡死」侧;旧节点基类退役批内联,行为等价红线):
    每轮验证「仍在巨星 overlay」(标识-盛会之星)→ 未离开 = 选候选/确认一个
    动作 → round_retry(计 node_max_retry_times=8 预算,超 → FAIL bail);
    overlay 消失 = 完成 → round_success。committed-but-verifying 循环与
    ADR-0264 关态稳定基线预置原样平移(旧基类节点循环语义)。

    **玩法机制(米游社 wiki content/6239 + 实机日志/截图核实,2026-08-07)**:
    盛会之星 = 阵营羁绊;「巨星」= 选 1 名盛会之星角色当巨星,给全队独特 buff。
    触发 = 羁绊激活时弹出(非固定节点),一局可多次 → 选中标记不能跨节点保持。
    dispatch 是 OCR 反应式(主循环 0b 检测「盛会之星」就接)→ 不管何时弹都接得住。
    强化角色**可选**(不选也能确认推进)——本节点维持「选巨星候选 → 确认(跳过
    step2,罕见残留再 confirm 安全网)」。候选坐标经 screen_info
    ``currency_war_megastar``(候选-左/右 + 按钮-确认选择);缺失用兜底常量。
    """

    # 左候选(花火)位 —— 实机 bot 点 (822,333) 已选中花火(金边);名位置 = 卡身选中区。
    # 常量=screen_info 缺失兜底;首选 area_center('候选-左')。
    CANDIDATE_LEFT: ClassVar[Point] = Point(822, 333)
    # 右候选(星期日)位 —— OCR 名 @x1061 y334(cw_megastar 实测 2026-08-07);同 y。
    # 常量=兜底;首选 area_center('候选-右')。
    CANDIDATE_RIGHT: ClassVar[Point] = Point(1061, 333)
    # 「确认选择」钮中心(OCR 确认选择 x1442y548;钮中心 ~1490,560)。常量=兜底;
    # 首选 area_center('按钮-确认选择')。
    CONFIRM: ClassVar[Point] = Point(1490, 560)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-巨星节点')

    def _in_node(self, screen) -> bool:
        # 巨星 overlay:盛会之星标题在(用 screen_info 标题 area 位置区分,非全屏 LCS)。原用「确认选择
        # AND NOT 选择伙伴」(lcs 0.7 防共享「选择」误匹配)—— 改用 megastar 独有标题「盛会之星」更直接。
        still_in = self.round_by_find_area(screen, '货币战争-盛会之星', '标识-盛会之星', crop_first=False).is_success
        # megastar 一局可能多次(每次持有盛会之星角色触发,见类 docstring),flag 不能跨节点保持 True。
        if not still_in:
            _match = self.ctx.cw_match
            if _match is not None:
                _match.session.megastar_candidate_clicked = False
        return still_in

    @operation_node(name='巨星处理', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        """committed-but-verifying 节点循环(旧基类逻辑内联,零行为变更)。"""
        screen = self.last_screenshot
        # 验证完成:已不在本节点画面 = overlay 消失 / 进了下一节点 → 节点完成,交还外层。
        if not self._in_node(screen):
            # ADR-0264 方案 B:overlay 关闭验证帧预置为关态稳定基线(外层回
            # 备战分支 gate 跳过「从零等 2 轮」;仍须过一次锚+指纹确认,不裸跳)。
            # best-effort(离线 mock 帧不阻塞)。
            from sr_od.application.currency_war.obs.cw_observation_gate import (
                PROFILE_CLOSED,
                preset_stable_baseline,
            )
            preset_stable_baseline(screen, profile=PROFILE_CLOSED)
            return self.round_success('巨星节点完成(已离开本节点画面)',
                                      wait=CW_OVERLAY_SETTLE_S)
        # 仍在节点内 → 做一个动作;round_retry 重跑本节点(计预算,超 → FAIL bail)。
        self._do_action(screen)
        return self.round_retry(wait=1.5)

    def _do_action(self, screen) -> None:
        # 选中标记挂 match.session(跨 re-dispatch 持久;原实例态在重派时重置
        # → re-click toggle 反选 → confirm 无候选 → 卡死)。megastar 选中态视觉(金边)。
        _match = self.ctx.cw_match
        _clicked = getattr(_match.session, 'megastar_candidate_clicked', False) if _match else False
        if not _clicked:
            options = read_megastar_options(self.ctx, screen)
            match = self.ctx.cw_match
            idx = 0
            reason = 'default(no match/options)'
            if match is not None and options:
                _state = match.session.last_state or GameState()   # overlay 时用上次备战快照
                _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
                pick = match.strategy.decide_megastar(options, _state, match.session, _cfg)
                if 0 <= pick.idx < len(options):
                    idx = pick.idx
                reason = pick.reason
                log.info(f'[cw-megastar] candidates={[o.char_id for o in options]} pick=idx{idx} {pick.reason}')
            else:
                log.info(f'[cw-megastar] options={len(options)} match={match is not None} → default idx0')
            # W312(遥测审计 G1):巨星候选面+选择落账本(此前只有结果回写
            # session.chosen_megastar,候选与依据只 log)。
            record_event_choice('megastar',
                                [{'char_id': o.char_id} for o in options],
                                idx, reason)
            # 候选坐标从 screen_info 读(task#103 化债,W265);缺失走历史实测兜底常量。
            candidate = ((area_center(self.ctx, '候选-左', '货币战争-盛会之星') or CwScreenMegastar.CANDIDATE_LEFT)
                         if idx == 0 else
                         (area_center(self.ctx, '候选-右', '货币战争-盛会之星') or CwScreenMegastar.CANDIDATE_RIGHT))
            self.ctx.controller.mouse_move(candidate)
            self.ctx.controller.click(candidate)
            if _match is not None:
                _match.session.megastar_candidate_clicked = True   # session 级:跨 re-dispatch 持久
                # r358d(遥测接线):巨星选择落 session → read_game_state
                # 回写 state.megastar_char(复盘「绑定与 comp 匹配」维度)。
                if options and 0 <= idx < len(options):
                    _match.session.chosen_megastar = options[idx].char_id or ''
            time.sleep(0.6)
        # confirm(候选已选一次 → confirm 跳过 step2(可选)→ overlay 关;retry 重 confirm 防 bug#1 落空)。
        # 确认钮中心从 screen_info 读(task#103 化债,W265);缺失兜底常量。
        confirm = area_center(self.ctx, '按钮-确认选择', '货币战争-盛会之星') or CwScreenMegastar.CONFIRM
        self.ctx.controller.mouse_move(confirm)
        self.ctx.controller.click(confirm)
        time.sleep(0.9)
        if self.round_by_find_area(self.screenshot(), '货币战争-盛会之星', '按钮-请选择强化角色', crop_first=False).is_success:
            log.info('[cw-megastar] step2 请选择强化角色 仍在(罕见)→ 再 confirm(安全网)')
            self.ctx.controller.mouse_move(confirm)
            self.ctx.controller.click(confirm)
            time.sleep(0.9)


class CwScreenPartner(CwScreenOverlay):
    """列车同行:SIFT 立绘识别候选真身 → core/build_around 命中兜底(decide_partner)。"""

    LABEL: ClassVar[str] = '列车同行'
    SCREEN_NAME: ClassVar[str] = '货币战争-列车同行'
    MARK_AREA: ClassVar[str] = '标识-选择伙伴'
    HANDLER_FACTORY: ClassVar[HandlerFactory] = HandleSelectPartner


class CwScreenWishTrial(CwScreenOverlay):
    """祈愿试炼:候选卡 objective → naive/decide_wish_trial 首张兜底 + 确认。"""

    LABEL: ClassVar[str] = '祈愿试炼'
    SCREEN_NAME: ClassVar[str] = '货币战争-祈愿试炼'
    MARK_AREA: ClassVar[str] = '标识-祈愿试炼'
    HANDLER_FACTORY: ClassVar[HandlerFactory] = HandleWishTrial


class CwScreenPlanner(CwScreenOverlay):
    """骇入策划(银狼「我来当策划」):两选项 OCR → decide_planner(升费优先)。"""

    LABEL: ClassVar[str] = '策划事件'
    SCREEN_NAME: ClassVar[str] = '货币战争-骇入策划'
    MARK_AREA: ClassVar[str] = '标识-我来当策划'
    HANDLER_FACTORY: ClassVar[HandlerFactory] = HandlePlannerEvent


class CwScreenFortune(CwScreenOverlay):
    """命运卜者强化:三强化卡 → 执行器文本规则(战力关键词)选卡 + 确认。"""

    LABEL: ClassVar[str] = '命运卜者强化'
    SCREEN_NAME: ClassVar[str] = '货币战争-命运卜者强化'
    MARK_AREA: ClassVar[str] = '标识-命运卜者'
    HANDLER_FACTORY: ClassVar[HandlerFactory] = HandleFortunePicker


class CwScreenBookcard(SrOperation):
    """星徽秘典四选一:OCR 卡名 → decide_star_tome 选卡(点卡即选,弹窗自关)。

    现役逻辑内联在 cw_loop 0i 分支(无独立 handler op),本批按现役读法直写:
    全屏 OCR 取「XX星徽」名 → 策略打分(target 阵营/board 已有/配方框架),
    无命中 fallback 卡1(06-overlays §4:决策待定,策略归口批 B 定)。
    点击坐标走 screen_info 星徽卡-1..4 area(OCR x 近邻匹配 area,不硬编码)。
    """

    SCREEN_NAME: ClassVar[str] = '货币战争-星徽秘典弹窗'
    MARK_AREA: ClassVar[str] = '标识-星徽秘典'
    CARD_AREAS: ClassVar[tuple[str, ...]] = ('星徽卡-1', '星徽卡-2', '星徽卡-3', '星徽卡-4')

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-星徽秘典')

    def _read_card_factions(self, screen) -> list[tuple[str, int]]:
        """全屏 OCR 取「XX星徽」卡名 → [(阵营名, x 中心)] 左→右(现役 0i 读法)。"""
        ocr = self.ctx.ocr_service.get_ocr_result_list(screen, crop_first=False)
        cards: list[tuple[str, int]] = []
        for o in ocr:
            t = (o.data or '').strip()
            if t.endswith('星徽') and len(t) > 2:
                cards.append((t[:-2], o.x + o.w // 2))
        cards.sort(key=lambda c: c[1])
        return cards

    def _card_point(self, idx: int, faction_x: int | None) -> Point | None:
        """卡身点击点 = 星徽卡-N area 中心;OCR x 已知时取 x 近邻 area(防 area 序与画面序错位)。"""
        centers: list[Point] = []
        for area in self.CARD_AREAS:
            pt = area_center(self.ctx, area, self.SCREEN_NAME)
            if pt is None:
                return None
            centers.append(pt)
        if faction_x is not None:
            idx = min(range(len(centers)),
                      key=lambda i: abs(centers[i].x - faction_x))
        return centers[idx]

    @operation_node(name='星徽秘典', is_start_node=True, node_max_retry_times=5)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success:
            return self.round_fail('非星徽秘典画面')
        cards = self._read_card_factions(screen)
        idx, pick_name = 0, '(fallback卡1)'
        if cards:
            _match = getattr(self.ctx, 'cw_match', None)
            if _match is not None:
                from sr_od.application.currency_war.kernel.cw_state import GameState
                _st = _match.session.last_state or GameState()
                _decided = _match.strategy.decide_star_tome(
                    [c[0] for c in cards], _st, _match.session,
                    getattr(_match, 'config', None))
                if 0 <= _decided < len(cards):
                    idx, pick_name = _decided, cards[_decided][0]
        # 近邻匹配锚 = 选中卡的 OCR x(决策后取,防把候选首位当选中位)
        faction_x = cards[idx][1] if idx < len(cards) else None
        target = self._card_point(idx, faction_x)
        if target is None:
            return self.round_fail('星徽秘典缺「星徽卡-N」建档')
        log.info('[cw-flow-bookcard] 候选=%s → 选 %s @(%s,%s)',
                 [c[0] for c in cards] or 'OCR未读到', pick_name, target.x, target.y)
        safe_click(self, target, tag='cw-flow-bookcard')
        time.sleep(1.0)   # 点卡即选,弹窗自关(现役 0i 实测口径)
        # 出口验真转移:弹窗消失;仍在 = 选卡未生效,重试计预算。
        if self.round_by_find_area(
                self.screenshot(), self.SCREEN_NAME, self.MARK_AREA,
                crop_first=False).is_success:
            return self.round_retry('选卡后秘典弹窗仍在')
        return self.round_success('星徽秘典选卡完成', wait=CW_OVERLAY_SETTLE_S)


#: 06-overlays §4 表序的 overlay op 全集(主循环按画面分发消费;武装箱选卡不经本族——主循环 0f 直派 HandleArmoryBoxDialog)。
OVERLAY_OPS: tuple[type[SrOperation], ...] = (
    CwScreenMegastar, CwScreenPartner, CwScreenWishTrial,
    CwScreenPlanner, CwScreenFortune, CwScreenBookcard,
)
