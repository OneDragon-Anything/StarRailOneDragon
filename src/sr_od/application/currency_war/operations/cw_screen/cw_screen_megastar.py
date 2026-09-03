"""货币战争 盛会之星画面 op(NAMING 迁移:原 overlay 族文件收敛为巨星单画面 op)。

其余 overlay 已按 NAMING §2 迁独立 cw_screen_*.py(委托壳溶解:入口门由
主循环 0 系分支承担,处理本体 = 各画面 op 真身);本文件仅存巨星内联实现。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.obs.cw_node_obs import read_megastar_options
from sr_od.application.currency_war.operations.cw_screen.cw_flow_const import (
    CW_OVERLAY_SETTLE_S,
)
from sr_od.application.currency_war.telemetry.recorder import record_event_choice
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


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
        # 到账登记(§3.3 #29 ConfirmMegastar):chosen_megastar 更新(粗粒度
        # expected;本体已在候选选中时写 session,此处按确认动作落地登记)。
        _cid = (getattr(_match.session, 'chosen_megastar', '')
                if _match is not None else '')
        if _cid:
            from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
                register_confirm_arrival,
            )
            register_confirm_arrival(_match.session, 'ConfirmMegastar', _cid,
                                     produced_by='CwScreenMegastar')
