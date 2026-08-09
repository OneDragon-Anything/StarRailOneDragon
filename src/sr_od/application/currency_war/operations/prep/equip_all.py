# 未验证(D-148 drag-equip op,2026-08-09)

"""货币战争 全员装备 op(D-148 + D-155:drag 装备区 equip icon → char grid slot)。

**背景**:bot own equip(decide_supply 无钻时拣)但**不装备**(equips UNREAD + 无 equip op)→ 单位裸装
→ 弱(敌方词缀「软弱无力/额外打击」惩罚裸装)。D-155 web 确认机制:**棋盘 prep board 装备区**(右侧
`区域-道具装备` x1252-1918 y90-710)的 owned equip icon(**long-press/drag** → char 头像/格 → 穿戴)。

**机制实跑(D-155)**:装备 icon 在右列(x~1851,y 随 owned equip 数;亮度列检测可定位);drag icon →
char grid slot(前排槽 center,test 验 tentative 生效 —— body figure drop 失败,grid slot drop 成功)。

**op**:① 亮度列检测 装备区 右列(x1800-1918)owned equip icon 位置;② 每个 icon drag → 前排 char
grid slot(循环 前排-1..4 center);③ 验证(re-detect:icon 数减少 = 装上)。接 BattlePrepCycle(部署后)。

**注意**:① drop zone = grid slot center(y398),非 body figure(后者失败);② 勿 ESC(中断挑战 bug#2);
③ owned equip 数有限(3/match),全装是边际改善(但每局都裸装输,装上即改善)。
"""
import time

import cv2
import numpy as np

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class EquipAll(SrOperation):
    """备战阶段:全员装备(drag 装备区 owned equip icon → 前排 char grid slot,D-148/D-155)。

    前置:已在「货币战争-备战」(shop 关,detail panel 关 —— 装备区 visible)。部署后跑(板已满)。
    """

    SCREEN_NAME: str = '货币战争-备战'
    # 装备区右列(equip icon column)x1800-1918;icon 在 x~1851(亮度检测)
    EQUIP_COL_X1: int = 1800
    EQUIP_COL_X2: int = 1918
    ZONE_Y1: int = 90
    ZONE_Y2: int = 710
    ICON_Y_MAX: int = 450   # icon 在上半区(y90-450);下半(y>450)是别的 UI(过滤)
    # 前排 char grid slot center(D-155 grid drop zone;screen_info 前排-1..4 center y398)
    FRONT_SLOTS: list[Point] = [Point(743, 398), Point(887, 398), Point(1033, 398), Point(1179, 398)]

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-全员装备')

    def _detect_equip_icons(self, screen) -> list[Point]:
        """亮度列检测 装备区右列 owned equip icon 位置(x~1851,上半区 y90-450)。

        equip icon 是亮(>90 灰度)的 item 图像 vs 暗蓝紫 bg。per-row 亮像素数 > 阈值 = icon 行;
        连续 icon 行聚类 = 一个 icon。返 icon center 列表(top-to-bottom)。
        """
        col = screen[self.ZONE_Y1:self.ICON_Y_MAX, self.EQUIP_COL_X1:self.EQUIP_COL_X2]
        gray = cv2.cvtColor(col, cv2.COLOR_BGR2GRAY)
        row_bright = (gray > 90).sum(axis=1)
        icon_rows = np.where(row_bright > 30)[0]   # >30 稳定(>40 漏中间 icon;2026-08-09 实跑调)
        icons: list[Point] = []
        if len(icon_rows) == 0:
            return icons
        start = int(icon_rows[0])
        prev = int(icon_rows[0])
        for raw_r in icon_rows[1:]:
            r = int(raw_r)
            if r - prev > 15:   # 间隙 > 15px = 新 icon
                icons.append(Point(1851, self.ZONE_Y1 + (start + prev) // 2))
                start = r
            prev = r
        icons.append(Point(1851, self.ZONE_Y1 + (start + prev) // 2))
        return icons

    @operation_node(name='全员装备', is_start_node=True)
    def equip_all(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # 前置:detail panel 关(装备区 visible)—— 检「出售」(panel 标志)不在
        if self.round_by_ocr(screen, '出售', lcs_percent=0.8).is_success:
            log.info('[cw-equip] 详情面板开(出售可见)→ 装备区被遮,跳过(下轮 panel 关时再装)')
            return self.round_success('panel 开,跳过')
        icons = self._detect_equip_icons(screen)
        if not icons:
            log.info('[cw-equip] 装备区无 owned equip icon → 无可装,跳过')
            return self.round_success('无 equip')
        log.info(f'[cw-equip] 检测 {len(icons)} 个 owned equip icon:{[(p.x, p.y) for p in icons]} → drag 到前排槽')

        equipped = 0
        for i, icon in enumerate(icons):
            if i >= len(self.FRONT_SLOTS):
                break   # icon 多于前排槽 → 只装前排(余下装后排待扩)
            dst = self.FRONT_SLOTS[i]
            # D-155:long-press/drag 装备 icon → char grid slot。hold_time=0.8(long-press 拾起 equip icon;
            # 无 hold_time drag 不拾起 → 不装备,2026-08-09 实跑 icon 数未减 = drag 未生效)
            self.ctx.controller.drag_to(start=icon, end=dst, duration=1.5, hold_time=0.8)
            time.sleep(0.8)
            equipped += 1
            log.info(f'[cw-equip] drag equip{i+1}({icon.x},{icon.y}) → 前排-{i+1}({dst.x},{dst.y})')

        # 验证:re-detect icon(应减少 = 装上)
        time.sleep(0.5)
        after_icons = self._detect_equip_icons(self.screenshot())
        log.info(f'[cw-equip] 装后 re-detect:{len(after_icons)} icon(装前 {len(icons)})')
        if len(after_icons) < len(icons):
            log.info(f'[cw-equip] ✓ icon 减少({len(icons)}→{len(after_icons)})= 装备成功')
        else:
            log.warning('[cw-equip] ⚠ icon 未减(drag 可能未生效 / drop zone / panel 遮)')
        return self.round_success(f'equip drag {equipped}(icon {len(icons)}→{len(after_icons)})', wait=1)
