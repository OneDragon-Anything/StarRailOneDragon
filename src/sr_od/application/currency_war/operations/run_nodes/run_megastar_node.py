"""货币战争 巨星节点 RunNode(盛会之星羁绊的「选巨星」overlay)。

**玩法机制(米游社 wiki content/6239 + 实机日志/截图核实,2026-08-07)**:
- 盛会之星 = 阵营羁绊(花火/星期日/知更鸟/黑天鹅/大丽花/加拉赫 + 盛会之星星徽)。
- 「巨星」= 选 1 名盛会之星角色当巨星,**给全队独特 buff**(各巨星不同,随羁绊等级 2/3/4/5/6 递增):
  花火=进战给战技点+普攻/战技增伤;星期日=前台首位前台强度+后台首位后台强度;
  知更鸟=幸运一击;黑天鹅=5费增伤;大丽花/加拉赫=击破伤害增幅+治疗强度。
- **触发条件【待实机验证 TODO】**:强指向 = **盛会之星羁绊激活时**(≥2 名上阵前排/后台凑够激活数)弹出 —— 非固定节点。
  依据:① 用户 2026-08-07 给机制(羁绊激活=角色上阵凑数,盛会之星是羁绊);② 受控实验:上阵 1 个星期日(未激活)2-2 不弹;
  ③ 旧样本(局A/旧图 2 个上阵→弹)。**但尚未亲眼看到 bot 上阵 ≥2 盛会之星激活→弹巨星**(用户告知 ≠ 实机验证),验证前不当事实。
  候选=持有的盛会之星角色(每局不同)。overlay 叠备战屏:`请选择1名角色成为巨星`+候选立绘(左右)+
  可选`请选择强化角色`+`确认选择`。
- **dispatch 是 OCR 反应式**(battle_loop 0b 检测「确认选择」就接)→ 不管何时弹 bot 都接得住。
- 强化角色**可选**(不选也能确认推进)—— 点确认后 overlay 消失回备战出战。套 RunNode 验证
  (overlay 消失=完成)+ 预算(点不动 bail,不再无限烧预算)。

TODO(策略):候选按 target_comp 选(decide_megastar 已接,按 buff 契合);强化角色可后续接。
TODO(task#20):候选/确认坐标进 screen_info。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_node_obs import read_megastar_options
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.operations.run_nodes.run_node import RunNode
from sr_od.context.sr_context import SrContext


class RunMegastarNode(RunNode):
    """巨星节点:read 候选 → decide_megastar(select_megastar 按 target.core_chars)→ 点选中候选 + 确认。"""

    # 左候选(花火)位 —— 实机 bot 点 (822,333) 已选中花火(金边);名位置 = 卡身选中区。
    CANDIDATE_LEFT: ClassVar[Point] = Point(822, 333)
    # 右候选(星期日)位 —— OCR 名 @x1061 y334(cw_megastar 实测 2026-08-07);同 y。
    CANDIDATE_RIGHT: ClassVar[Point] = Point(1061, 333)
    # 「确认选择」钮中心(OCR 确认选择 x1442y548;钮中心 ~1490,560)。
    CONFIRM: ClassVar[Point] = Point(1490, 560)

    def __init__(self, ctx: SrContext):
        RunNode.__init__(self, ctx, op_name='货币战争-巨星节点')

    @operation_node(name='巨星节点', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        return self._run_node()

    def _in_node(self, screen) -> bool:
        # 巨星 overlay:盛会之星标题在(用 screen_info 标题 area 位置区分,非全屏 LCS)。原用「确认选择
        # AND NOT 选择伙伴」(lcs 0.7 防共享「选择」误匹配)—— 改用 megastar 独有标题「盛会之星」更直接。
        still_in = self.round_by_find_area(screen, '货币战争-盛会之星', '标识-盛会之星', crop_first=False).is_success
        # megastar 一局可能多次(每次持有盛会之星角色触发,见模块 docstring),flag 不能跨节点保持 True。
        if not still_in:
            _match = self.ctx.cw_match
            if _match is not None:
                _match.session.megastar_candidate_clicked = False
        return still_in

    def _do_action(self, screen) -> None:
        # RunMegastarNode 实例重置 → re-click toggle 反选 → confirm 无候选 → 卡死)。megastar 选中态视觉(金边)。
        _match = self.ctx.cw_match
        _clicked = getattr(_match.session, 'megastar_candidate_clicked', False) if _match else False
        if not _clicked:
            options = read_megastar_options(self.ctx, screen)
            match = self.ctx.cw_match
            idx = 0
            if match is not None and options:
                _state = match.session.last_state or GameState()   # overlay 时用上次备战快照
                _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
                pick = match.strategy.decide_megastar(options, _state, match.session, _cfg)
                if 0 <= pick.idx < len(options):
                    idx = pick.idx
                log.info(f'[cw-megastar] candidates={[o.char_id for o in options]} pick=idx{idx} {pick.reason}')
            else:
                log.info(f'[cw-megastar] options={len(options)} match={match is not None} → default idx0')
            candidate = RunMegastarNode.CANDIDATE_LEFT if idx == 0 else RunMegastarNode.CANDIDATE_RIGHT
            self.ctx.controller.mouse_move(candidate)
            self.ctx.controller.click(candidate)
            if _match is not None:
                _match.session.megastar_candidate_clicked = True   # session 级:跨 re-dispatch 持久
            time.sleep(0.6)
        # confirm(候选已选一次 → confirm 跳过 step2(可选)→ overlay 关;retry 重 confirm 防 bug#1 落空)。
        self.ctx.controller.mouse_move(RunMegastarNode.CONFIRM)
        self.ctx.controller.click(RunMegastarNode.CONFIRM)
        time.sleep(0.9)
        if self.round_by_find_area(self.screenshot(), '货币战争-盛会之星', '按钮-请选择强化角色', crop_first=False).is_success:
            log.info('[cw-megastar] step2 请选择强化角色 仍在(罕见)→ 再 confirm(安全网)')
            self.ctx.controller.mouse_move(RunMegastarNode.CONFIRM)
            self.ctx.controller.click(RunMegastarNode.CONFIRM)
            time.sleep(0.9)
