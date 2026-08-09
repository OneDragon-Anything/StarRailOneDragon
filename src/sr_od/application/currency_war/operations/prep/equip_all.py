
"""货币战争 全员装备 op —— DORMANT(未接进 BattlePrepCycle,待建档后重写)。

**状态(D-18)**:本 op 已撤销重接(e9747690 解绑 + D-18),BattlePrepCycle 回「买→部署→出战」(无装备节点)。
原 `_detect_equip_icons` 亮度检测区域 **x1800-1918 已证伪 = 装饰球体非 owned equip icon**(D-18:
r1-1 + r1-6 VLM 两样本一致),整个检测建在错区域 → 假阳性(误判球体为装备)→ drag 假 icon 破坏棋盘/出战。
bot 当前裸装 → 装备是 A8 大杠杆(D-17),但**必须先建档再重写,不能在错区域上叠补丁**。

**重写计划(onboarding-first,防 D-148 churn)**:先按 `od-dev-screen-onboarding` 给装备区正式建档
(多 crop 交叉验证 + 三态样本:空槽占位符 / 填充装备 / 工具;owned 装备实际位置待定位)→ 再重建检测
(形状/边框/图案,非亮度)→ 再重开 drag(穿戴机制 = drag,见 D-17/D-18 + strategy/07)。

**当前代码**:detect-only 探针(equip_all node 截图 `cw_equip_detect_*`)是 D-18 诊断遗留,已得出
"区域错"结论,区域证伪后探针不再有诊断价值(保留作存档);unreachable drag 代码已删。
"""
import cv2
import numpy as np

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class EquipAll(SrOperation):
    """备战阶段:全员装备(drag 装备区 owned equip icon → 前排 char grid slot,/)。

    前置:已在「货币战争-备战」(shop 关,detail panel 关 —— 装备区 visible)。部署后跑(板已满)。
    """

    SCREEN_NAME: str = '货币战争-备战'
    # 装备区右列(equip icon column)x1800-1918;icon 在 x~1851(亮度检测)
    EQUIP_COL_X1: int = 1800
    EQUIP_COL_X2: int = 1918
    ZONE_Y1: int = 90
    ZONE_Y2: int = 710
    ICON_Y_MAX: int = 450   # icon 在上半区(y90-450);下半(y>450)是别的 UI(过滤)
    # 头像**(slot 顶 ~y350,char 小肖像+HP bar 处)。screen_info 前排-1..4 x:743/887/1033/1179。
    FRONT_SLOTS: list[Point] = [Point(743, 350), Point(887, 350), Point(1033, 350), Point(1179, 350)]

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
        self.save_screenshot(prefix='cw_equip_detect')   # D-18 detect-only:捕获 equip 区(球体 vs 真装备),供修检测
        # D-18 detect-only(诊断检测假阳性根因):不 drag(假 icon=装饰球体会破坏棋盘/出战),只截图捕获。
        # 跑到 r1-5(补给后真装备)→ 对比 cw_equip_detect 截图区分真装备 icon vs 空槽球体 → 修 _detect_equip_icons → 重开 drag。
        return self.round_success(f'detect-only {len(icons)} icon(D-18 区域证伪,探针存档;待建档重写)')
        # unreachable drag 代码已删(D-18:建在证伪的 x1800-1918 装饰球体区域 → 假阳性破坏棋盘)。
        # 重写走 onboarding-first:先建档装备区三态 → 重建 _detect_equip_icons(非亮度)→ 重开 drag(见 docstring)。
