# 未验证(货币战争 D-153 selective-sell,2026-08-09)

"""货币战争 清存量 off-target deployed(D-153:点 deployed 头像→详情面板露阵营+出售按钮)。

**背景(D-153 突破)**:整个 session 根本瓶颈 = 身份墙(无 per-char 身份 → 无法 selective 清
off-target → board 永久 spread → r6+ HP 崩)。D-153 实机验证:点 deployed 舞台角色 → 弹**详情面板**,
含 per-char 阵营/羁绊(OCR 可读)+「出售」按钮(work!点→真卖)。故可逐个识别 deployed 角色 →
sell off-target(阵营 ∌ target)→ 清板 → concentrate target。互补 D-152(D-152 防**新** off-target deploy;
本 op 清**存量** off-target)。

**机制**:遍历 deployed 槽(前排4+后排6)→ click 头像 → OCR 检测「出售」(面板开?)→ 开则 OCR 阵营栏 →
阵营 ∌ target_comp.factions → click 出售 → 清 off-target;target 角色保留(ESC 关面板)。空槽(无角色)
→ click 无面板 → skip。

**坐标(D-153 实机观测,待 screen_info 化)**:deployed 槽 click = 前排槽(x,~450)/后排槽(x,~680)
(figure center,非 slot rect center;figure 在 slot rect 下沿);详情面板 出售按钮 ~(1746,901);
阵营栏 ~x1400-1600 y290-320。坐标准确性待多样本核实(screen-onboarding)。
"""
import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_factions import FACTIONS
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CleanDeployedOffTarget(SrOperation):
    """备战阶段:点 deployed 头像 → 详情面板 → sell 阵营 ∌ target 的 off-target(D-153)。

    前置:已在「货币战争-备战」(shop 关)。target_comp 由 session 给(D-152 同源);无 target → 不清
    (无判据,全 sell 会清光 target)。清完交上层 deploy(D-152 selective deploy target)。
    """

    SCREEN_NAME: str = '货币战争-备战'
    # deployed 槽 figure center(D-153 实机 + screen_info slot rect 下沿估算;待多样本核实)
    # 前排 slot rect y329-467,figure center ~y450;后排 slot rect y600-739,figure center ~y680
    FRONT_SLOTS: list[Point] = [Point(743, 450), Point(887, 450), Point(1033, 450), Point(1179, 450)]
    BACK_SLOTS: list[Point] = [Point(604, 680), Point(746, 680), Point(888, 680),
                                Point(1032, 680), Point(1173, 680), Point(1315, 680)]
    SELL_BTN: Point = Point(1746, 901)        # 详情面板「出售」按钮(D-153 实机)
    FACTION_RECT: Rect = Rect(1395, 285, 1605, 330)   # 详情面板阵营/羁绊栏(D-153 实机 藿藿=仙舟/能量/治疗)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-清存量off-target')

    def _target_factions(self) -> set[str]:
        """session.target_comp.factions(无 target → 空 → 本 op 不清,return None 语义由调用判)。"""
        _match = self.ctx.cw_match
        if (_match is not None and _match.session is not None
                and _match.session.target_comp is not None):
            return set(_match.session.target_comp.factions)
        return set()

    def _read_panel_factions(self, screen) -> set[str]:
        """OCR 详情面板阵营栏 → 命中的 FACTIONS 规范名集合(如 {仙舟,能量,治疗})。"""
        _r = self.FACTION_RECT
        crop = screen[_r.y1:_r.y2, _r.x1:_r.x2]
        if crop.size == 0:
            return set()
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=crop, rect=None, color_range=None, crop_first=False)
        texts = [k for k, mrl in ocr_map.items() if mrl.max is not None]
        joined = ''.join(texts)
        return {f for f in FACTIONS if f in joined}

    @operation_node(name='清存量off-target', is_start_node=True)
    def clean(self) -> OperationRoundResult:
        _tgt = self._target_factions()
        if not _tgt:
            log.info('[cw-clean] 无 target_comp → 不清(防误清 target;待 target 选定)')
            return self.round_success('无 target,跳过')
        log.info(f'[cw-clean] target_factions={sorted(_tgt)} → 遍历 deployed 槽清 off-target')

        sold = 0
        kept = 0
        for slot in self.FRONT_SLOTS + self.BACK_SLOTS:
            # click deployed 头像 → 详情面板(D-153)
            self.ctx.controller.click(slot)
            time.sleep(1.2)   # 等面板动画 settle(短了 OCR 读空阵营)
            screen = self.screenshot()
            # 检测面板开:「出售」按钮出现(detail panel 独有)
            if not self.round_by_ocr(screen, '出售', lcs_percent=0.8).is_success:
                continue   # 空槽(无角色)/click 落空 → 无面板 → skip
            # OCR 阵营栏 → 命中 FACTIONS
            _factions = self._read_panel_factions(screen)
            _is_target = bool(_factions & _tgt)
            # 安全(D-153):阵营读不出([])→ **保守保留**(防 OCR 漏读 target 阵营 → 误卖 target)。
            # 只在「阵营可读 且 ∌ target」时 sell。可读性靠 panel settle + FACTION_RECT(待多样本核实)。
            _unreadable = not _factions
            _do_sell = (not _is_target) and (not _unreadable)
            log.info(f'[cw-clean] slot{slot} 面板开 阵营={sorted(_factions)} '
                      f'{"target→保留" if _is_target else ("off-target→sell" if _do_sell else "阵营不可读→保留")}')
            if _do_sell:
                self.ctx.controller.click(self.SELL_BTN)   # D-153 出售按钮
                time.sleep(0.8)
                sold += 1
            else:
                kept += 1
                self.ctx.controller.btn_tap('esc')   # 关面板,保 target / 不可读保守保留
                time.sleep(0.4)
        # 收尾:确保面板关(末个 target 保留后 ESC;末个 sell 后面板自关)
        self.ctx.controller.btn_tap('esc')
        time.sleep(0.3)
        log.info(f'[cw-clean] 清完:sold={sold} off-target,kept={kept} target')
        return self.round_success(f'sold {sold} off-target / kept {kept} target', wait=1)
