# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 · 角色图鉴批量采集立绘(白框法;参考 HarvestEquipCodex 模式,CW 专属工具 op)。

== 作用 ==
从「数据银行 → 角色图鉴」逐个选中角色卡片 → 采集选中卡片的**白框内立绘**(CV 定位纯白选中
边框 → crop,比固定偏移准)→ 存 ``assets/template/character_cw_portrait/<名>/raw.png``。
按 OCR 右侧角色名去重,整页 0 新增即停。采的立绘供 ``read_bench_chars`` SIFT 库
(D-102 deploy 实际 bench 识别;canonical 半身同备战栏域,实测 STRONG)。

== 前提:手动进到角色图鉴画面 ==
数据银行 → 角色图鉴,停在第1页(左侧角色网格 + 右侧详情面板可见)。不在角色图鉴跑会乱点。

== 经 MCP run_operation ==
    run_operation(op_id='sr_od.application.currency_war.operations.dev.collect_portraits_op.CollectPortraits')

== 几何(1080p;角色图鉴网格 7 列 × 3 可见行;右侧详情角色名 OCR 区)==
对齐 HarvestEquipCodex 模式(ctrl.get_screenshot+fill_uid_black / 滚动翻页 / 去重 0 增即停)。
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

# 固定几何(1080p 角色图鉴)
GRID_COLS = [134, 310, 486, 662, 838, 1014, 1190]   # 7 列 x 中心(OCR 名 x +40)
GRID_ROWS = [360, 590, 820]                          # 3 可见行 y 中心
NAME_REGION = (1430, 110, 1620, 160)                 # 右侧详情角色名 OCR 区(瓦尔特 @1446,128)
SCROLL_FROM = Point(600, 800)                        # 上滑翻页(往下看更多行)
SCROLL_TO = Point(600, 520)
OUT = Path(__file__).resolve().parents[6] / 'assets/template/character_cw_portrait'


class CollectPortraits(SrOperation):
    """采集角色图鉴全部立绘(白框法):点格 → 截图 → 白框 crop 立绘 → OCR 右侧名 → 存 → 滚动 → 去重。"""

    def __init__(self, ctx: SrContext, max_pages: int = 8):
        SrOperation.__init__(
            self, ctx, op_name='货币战争-采角色立绘',
            need_check_game_win=False,   # 图鉴 overlay 内,不让框架 OpenAndEnterGame 纠正
        )
        self.max_pages = max_pages

    def _ocr_name(self, img) -> str:
        """OCR 右侧详情角色名区,取最长(最像名)文本。"""
        x0, y0, x1, y1 = NAME_REGION
        res = self.ctx.ocr_service.get_ocr_result_list(image=img[y0:y1, x0:x1], crop_first=False)
        texts = [r.data.strip() for r in res if r.data and r.w > 20]
        return max(texts, key=len) if texts else ''

    def _white_box_crop(self, img) -> np.ndarray | None:
        """CV 定位选中卡片白框(纯白边框)→ crop 立绘(白框内排除底部名 ~30px)。"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thr = cv2.threshold(gray, 235, 255, cv2.THRESH_BINARY)
        thr = cv2.dilate(thr, np.ones((3, 3), np.uint8), iterations=1)
        contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if 80 < w < 200 and 180 < h < 320:   # 卡片大小(立绘+名)
                return img[y:y + h - 30, x:x + w]
        return None

    @operation_node(name='采角色立绘', is_start_node=True)
    def collect(self) -> OperationRoundResult:
        ctrl = self.ctx.controller
        OUT.mkdir(parents=True, exist_ok=True)
        seen: set[str] = {p.name for p in OUT.iterdir() if p.is_dir()}
        log.info(f'[采立绘] 已有 {len(seen)},目标 71')
        pass_no = 0
        while pass_no < self.max_pages:
            pass_no += 1
            new_this = 0
            for ry in GRID_ROWS:
                for cx in GRID_COLS:
                    try:
                        ctrl.click(Point(cx, ry), press_time=0.1, pc_alt=False)
                        time.sleep(0.4)
                        nm = ''
                        img = None
                        for _ in range(3):   # OCR det 漏随机(缺10:刃/三月七/花火/...)→ 多帧重试取首个非空
                            img = ctrl.get_screenshot(independent=False)
                            if img is None:
                                continue
                            img = ctrl.fill_uid_black(img)
                            nm = self._ocr_name(img)
                            if nm:
                                break
                            time.sleep(0.3)
                        if not nm or nm in seen:
                            continue
                        crop = self._white_box_crop(img)
                        if crop is None:
                            continue
                        seen.add(nm)
                        new_this += 1
                        d = OUT / nm
                        d.mkdir(parents=True, exist_ok=True)
                        cv2_utils.save_image(crop, str(d / 'raw.png'))
                        log.info(f'[采立绘 pass{pass_no}] +{nm}({len(seen)}/71)')
                    except Exception as e:  # noqa: BLE001 单格失败不致命
                        log.warning(f'[采立绘] 格({cx},{ry})失败: {e}')
            log.info(f'[采立绘 pass{pass_no}] +{new_this} new (total {len(seen)})')
            if len(seen) >= 71:
                break
            ctrl.drag_to(SCROLL_TO, start=SCROLL_FROM, duration=0.5)
            time.sleep(0.6)
        log.info(f'[采立绘] 完成 {len(seen)}/71')
        return self.round_success(f'采立绘完成: {len(seen)}/71')
