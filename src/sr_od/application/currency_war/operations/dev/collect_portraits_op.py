# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 · 角色图鉴批量采集立绘(固定网格点名字 + 移鼠标 + 采全判据)。

== 作用 ==
从「数据银行 → 角色图鉴」**固定网格点名字行选中** → 移开鼠标(截图不含鼠标)→ 采集选中卡片
**完整白框整卡(立绘+名,不裁名)** → OCR 右侧详情面板名 → 存 ``character_cw_portrait/<名>/raw.png``。
去重(滚动后不重复);**滚动到一屏 0 新增即停**(采全判据,非固定次数)。开头顶格先回顶。

== 前提:手动进到角色图鉴画面 == 数据银行 → 角色图鉴(op 开头会回顶)。
== 经 MCP == run_operation(op_id='...collect_portraits_op.CollectPortraits')
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.log_utils import log
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

# 固定几何(1080p 角色图鉴网格 7 列 × 3 可见行)
GRID_COLS = [134, 310, 486, 662, 838, 1014, 1190]   # 7 列 x 中心(列固定,横向不滚)
GRID_NAME_REGION = (40, 380, 1300, 950)             # 网格名带 OCR(x<1300 排除右侧详情)
NAME_REGION = (1430, 110, 1620, 160)                 # 右侧详情角色名 OCR 区
CURSOR_AWAY = Point(960, 1050)                       # 截图前移开鼠标(防截图含鼠标污染白框检测)
SCROLL_DOWN_FROM = Point(600, 800)                   # 上滑(看下方更多行)
SCROLL_DOWN_TO = Point(600, 520)
SCROLL_UP_FROM = Point(600, 520)                     # 下滑(回顶)
SCROLL_UP_TO = Point(600, 800)
OUT = Path(__file__).resolve().parents[6] / 'assets/template/character_cw_portrait'


class CollectPortraits(SrOperation):
    """采集角色图鉴全部立绘:回顶 → OCR 当前行 Y(滚动后 Y 变,每屏重取)→ 固定列 × 行Y 点名
    → 移鼠标 → 完整白框 crop 整卡 → OCR 详情名 → 去重 → 滚到 0 新增停。"""

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(
            self, ctx, op_name='货币战争-采角色立绘',
            need_check_game_win=False,
        )

    def _ocr_row_ys(self, img) -> list[int]:
        """OCR 网格名 → 当前可见的**行 Y**(名字中心 y,聚类去重)。滚动后 Y 会变,每屏重取。"""
        x0, y0, x1, y1 = GRID_NAME_REGION
        res = self.ctx.ocr_service.get_ocr_result_list(image=img[y0:y1, x0:x1], crop_first=False)
        ys: list[int] = []
        for r in res:
            t = (r.data or '').strip()
            if t and 2 <= len(t) <= 8 and r.w > 25:
                cy = int(r.center.y) + y0
                if not any(abs(cy - y) < 40 for y in ys):   # 同行聚类(40px 内算同行)
                    ys.append(cy)
        return sorted(ys)

    def _ocr_name(self, img) -> str:
        """OCR 右侧详情角色名,取最长(最像名)文本。"""
        x0, y0, x1, y1 = NAME_REGION
        res = self.ctx.ocr_service.get_ocr_result_list(image=img[y0:y1, x0:x1], crop_first=False)
        texts = [r.data.strip() for r in res if r.data and r.w > 20]
        return max(texts, key=len) if texts else ''

    def _white_box_crop(self, img) -> np.ndarray | None:
        """CV 定位选中卡片**完整白框** → crop 整卡(立绘+名,不裁名)。完整才返。"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thr = cv2.threshold(gray, 235, 255, cv2.THRESH_BINARY)
        thr = cv2.dilate(thr, np.ones((3, 3), np.uint8), iterations=1)
        contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if 80 < w < 200 and 180 < h < 320:   # 完整卡(立绘+名)
                return img[y:y + h, x:x + w]     # 保留整卡(含名)
        return None

    @operation_node(name='采角色立绘', is_start_node=True)
    def collect(self) -> OperationRoundResult:
        ctrl = self.ctx.controller
        OUT.mkdir(parents=True, exist_ok=True)
        seen: set[str] = {p.name for p in OUT.iterdir() if p.is_dir()}
        log.info(f'[采立绘] 已有 {len(seen)},目标 71;先回顶')
        # 回顶(下滑几格,确保从第 1 页开始)
        for _ in range(4):
            ctrl.drag_to(SCROLL_UP_TO, start=SCROLL_UP_FROM, duration=0.4)
            time.sleep(0.4)
        empty_screens = 0
        while True:
            # 每屏 OCR 当前行 Y(滚动后 Y 变,不能写死)
            img = ctrl.get_screenshot(independent=False)
            row_ys: list[int] = []
            if img is not None:
                row_ys = self._ocr_row_ys(ctrl.fill_uid_black(img))
            log.info(f'[采立绘] 本屏行 Y={row_ys}')
            new_this = 0
            for ry in row_ys:
                for cx in GRID_COLS:
                    try:
                        ctrl.click(Point(cx, ry), press_time=0.1, pc_alt=False)   # 固定列 × 行Y 点名选中
                        time.sleep(0.35)
                        ctrl.mouse_move(CURSOR_AWAY)   # 移开鼠标 → 截图不含鼠标
                        time.sleep(0.15)
                        nm = ''
                        img2 = None
                        for _ in range(3):   # OCR det 偶漏 → 多帧重试
                            img2 = ctrl.get_screenshot(independent=False)
                            if img2 is None:
                                continue
                            img2 = ctrl.fill_uid_black(img2)
                            nm = self._ocr_name(img2)
                            if nm:
                                break
                            time.sleep(0.2)
                        if not nm or nm in seen:   # 去重(滚动后不重复)
                            continue
                        crop = self._white_box_crop(img2)
                        if crop is None:            # 完整白框才采集
                            continue
                        seen.add(nm)
                        new_this += 1
                        d = OUT / nm
                        d.mkdir(parents=True, exist_ok=True)
                        cv2_utils.save_image(crop, str(d / 'raw.png'))
                        log.info(f'[采立绘] +{nm}({len(seen)})')
                    except Exception as e:  # noqa: BLE001 单格失败不致命
                        log.warning(f'[采立绘] 格({cx},{ry})失败: {e}')
            log.info(f'[采立绘] +{new_this} new (total {len(seen)})')
            if new_this == 0:
                empty_screens += 1
                if empty_screens >= 1:   # 一屏 0 新增 = 采全,停(非固定滚动次数)
                    break
            else:
                empty_screens = 0
            ctrl.drag_to(SCROLL_DOWN_TO, start=SCROLL_DOWN_FROM, duration=0.5)
            time.sleep(0.6)
        log.info(f'[采立绘] 完成 {len(seen)}')
        return self.round_success(f'采立绘完成: {len(seen)}')
