# 临时 probe(D-148 equip 机制调查,2026-08-09):点 deployed → 详情面板 → 点装备槽 → log 出现啥
"""调查 CW equip 机制(owned-equip source / drag / slot-click 行为)。

D-148 确认 equip 是高价值 lever(裸装输一切 + 敌方词缀惩罚裸装),但 equip 机制未明(点「+」闭面板;
drag-from-where 不清)。本 probe:遍历 deployed 槽 → click 头像 → 检测详情面板(OCR「出售」)→
click 空装备槽 → log 出现的内容(OCR + 截图)→ 探明 slot-click 开 equip list/inventory 还是其他。

**临时 debug op**(验证完机制即删,转正式 equip op)。复用 clean_offtarget 的 slot-iteration + panel-detect。
"""
import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class EquipMechanismProbe(SrOperation):
    """临时:probe equip 机制(slot-click → ?)。"""

    # deployed 槽 figure center(同 clean_offtarget;前排 y450 / 后排 y680)
    FRONT_SLOTS: list[Point] = [Point(743, 450), Point(887, 450), Point(1033, 450), Point(1179, 450)]
    BACK_SLOTS: list[Point] = [Point(604, 680), Point(746, 680), Point(888, 680),
                                Point(1032, 680), Point(1173, 680), Point(1315, 680)]
    EQUIP_SLOT: Point = Point(1468, 866)   # 详情面板空装备槽 □(panel 区 x1400-1800;1344 在 panel 外会闭面板)
    EQUIP_PLUS: Point = Point(1654, 911)   # 详情面板「+」(D-153;点它曾闭面板,待复测)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='cw-equip-probe')

    @operation_node(name='equip-probe', is_start_node=True)
    def probe(self) -> OperationRoundResult:
        for slot in self.FRONT_SLOTS + self.BACK_SLOTS:
            self.ctx.controller.click(slot)
            time.sleep(1.0)
            screen = self.screenshot()
            if not self.round_by_ocr(screen, '出售', lcs_percent=0.8).is_success:
                continue   # 空槽/无角色 → 无面板 → 下个槽
            log.info(f'[cw-equip-probe] 详情面板开 @ slot{slot}')
            self.save_screenshot(prefix='cw_equip_probe_panel')

            # probe 1:点空装备槽 → 出现啥(equip list / inventory / nothing)
            self.ctx.controller.click(self.EQUIP_SLOT)
            time.sleep(1.2)
            after_slot = self.screenshot()
            _ocr = self.ctx.ocr_service.get_ocr_result_map(
                image=after_slot, rect=None, color_range=None, crop_first=False)
            _texts = [k for k, m in _ocr.items() if m.max is not None]
            _still_panel = self.round_by_ocr(after_slot, '出售', lcs_percent=0.8).is_success
            log.info(f'[cw-equip-probe] 点装备槽{self.EQUIP_SLOT} 后:面板仍开={_still_panel} OCR={_texts[:25]}')
            self.save_screenshot(prefix='cw_equip_probe_afterslot')
            # **勿 ESC**(中断挑战 bug)。安全关:re-click 同 char(toggle close)。集成 BattlePrepCycle 时
            # 需关面板(否则出战被遮);toggle 不保证关 → 下个 op verify 兜底。
            self.ctx.controller.click(slot)
            time.sleep(0.5)
            return self.round_success(f'equip-probe done(panel @ {slot})')
        log.info('[cw-equip-probe] 未找到详情面板(无 deployed char 在所点槽)')
        return self.round_success('no panel found')


_EXPORT = EquipMechanismProbe
