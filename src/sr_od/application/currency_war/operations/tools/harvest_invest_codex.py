
"""货币战争 · 投资策略/环境图鉴批量采集(参考 collect_portraits_op / harvest_equip_codex 模式)。

数据银行 → 投资策略图鉴 / 投资环境图鉴:固定列 X(4列) × OCR 行 Y(聚类,滚动后每屏重取)
→ 点格 → OCR 右侧详情(名+效果+出现位面) → 去重 → 小滚(~1行,滚动后验证行Y变化,失败重试)
→ 连续 3 屏 0 新增停。输出:.debug/temp/currency_war/codex_{kind}.jsonl(逐行 JSON)。
经 run_operation 在 backend(Session 1)执行。**须从列表顶部开始**(回顶 + 首屏验证)。
"""
from __future__ import annotations

import contextlib
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

GRID_COLS = [152, 308, 484, 660]            # 4 列 x 中心(策略页实测;环境页同列距)
NAME_REGION = (740, 100, 1900, 900)         # 右侧详情 OCR 区(名+效果)
GRID_NAME_REGION = (40, 200, 700, 900)      # 左侧网格名带(推行 Y)
SCROLL_FROM = Point(500, 800)               # 小滚 ~1 行(collect_portraits 实测拖距 280px)
SCROLL_TO = Point(500, 520)
OUT_DIR = Path(__file__).resolve().parents[6] / '.debug/temp/currency_war'


class HarvestInvestCodex(SrOperation):
    """采当前图鉴页(策略或环境);kind 只影响输出文件名。**从顶部开始**(回顶+验证)。"""

    def __init__(self, ctx: SrContext, kind: str = 'strategies'):
        SrOperation.__init__(self, ctx, op_name=f'采投资图鉴-{kind}',
                             need_check_game_win=False)
        self.kind: str = kind
        self.out = OUT_DIR / f'codex_{kind}.jsonl'
        self.seen: set[str] = set()
        if self.out.exists():
            for line in self.out.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line:
                    with contextlib.suppress(Exception):
                        self.seen.add(json.loads(line)['name'])

    def _ocr_texts(self, img, region):
        x0, y0, x1, y1 = region
        res = self.ctx.ocr_service.get_ocr_result_list(image=img[y0:y1, x0:x1], crop_first=False)
        return [(r.data.strip(), int(r.center.x) + x0, int(r.center.y) + y0)
                for r in res if r.data and r.w > 18]

    def _row_ys(self, img) -> list[int]:
        """OCR 网格名带 → 当前行 Y(60px 聚类)。"""
        ys = []
        for t, _cx, cy in self._ocr_texts(img, GRID_NAME_REGION):
            if 2 <= len(t) <= 12 and not t[0].isdigit():
                if not any(abs(cy - y) < 60 for y in ys):
                    ys.append(cy)
        return sorted(ys)

    def _first_row_text(self, img) -> str:
        """首行文字标记(回顶/滚动验证用):网格名带 y 最小的文本。"""
        ts = [t for t, _x, _y in self._ocr_texts(img, GRID_NAME_REGION)
              if 2 <= len(t) <= 12 and not t[0].isdigit()]
        if not ts:
            return ''
        ys = self._row_ys(img)
        if not ys:
            return ''
        return next((t for t, _x, y in self._ocr_texts(img, GRID_NAME_REGION)
                     if abs(y - ys[0]) < 60 and 2 <= len(t) <= 12), '')

    def _scroll_to_top(self) -> None:
        """回顶:退到数据银行菜单再重进图鉴(重进 = 列表天然回顶;比拖拽回顶可靠,用户 2026-08-15)。

        ESC 关图鉴 overlay → 菜单点「投资策略图鉴/投资环境图鉴」入口重进。kind 映射入口文本。
        兜底:重进失败(找不到入口)退回拖拽回顶。
        """
        ctrl = self.ctx.controller
        entry = '投资策略图鉴' if self.kind == 'strategies' else '投资环境图鉴'
        ctrl.btn_tap('esc')
        time.sleep(1.5)
        img = ctrl.get_screenshot(independent=False)
        if img is not None:
            res = self.ctx.ocr_service.get_ocr_result_list(image=img, crop_first=False)
            for r in res:
                if entry in (r.data or ''):
                    ctrl.click(Point(int(r.center.x), int(r.center.y)), press_time=0.1, pc_alt=False)
                    time.sleep(2.0)
                    log.info(f'[采图鉴] 重进 {entry}(回顶)')
                    return
        log.info('[采图鉴] 重进失败,兜底拖拽回顶')
        self._scroll_to_top_drag()

    def _scroll_to_top_drag(self) -> None:
        """拖拽回顶(兜底):下拉多次 + 首行标记连续 2 次不变。"""
        ctrl = self.ctx.controller
        last = None
        for _ in range(10):
            ctrl.drag_to(Point(500, 820), start=Point(500, 500), duration=0.4)
            time.sleep(0.5)
            img = ctrl.get_screenshot(independent=False)
            if img is None:
                continue
            mark = self._first_row_text(img)
            if mark and mark == last:
                log.info(f'[采图鉴] 拖拽回顶完成(首行={mark!r})')
                return
            last = mark

    def _scroll_down(self) -> bool:
        """小滚 1 行;验证行 Y 集合变化,失败重试(拖距递增)。"""
        ctrl = self.ctx.controller
        img = ctrl.get_screenshot(independent=False)
        ys_before = self._row_ys(img) if img is not None else []
        for extra in (0, 120, 240):
            ctrl.drag_to(Point(500, 520 - extra // 2), start=Point(500, 800 + extra // 2), duration=0.5)
            time.sleep(0.8)
            img2 = ctrl.get_screenshot(independent=False)
            if img2 is None:
                continue
            ys_after = self._row_ys(img2)
            if ys_after and ys_after != ys_before:
                return True
        log.info('[采图鉴] 滚动未生效(可能到底)')
        return False

    def _detail(self, img):
        """右侧详情:(名, 效果, 出现位面)。名 = 面板顶部标题(y 最小非 UI 文本)。"""
        texts = self._ocr_texts(img, NAME_REGION)
        if not texts:
            return None
        top = sorted(texts, key=lambda t: t[2])[:8]
        name = ''
        for t, _x, _y in top:
            if (2 <= len(t) <= 14 and not t[0].isdigit()
                    and not t.startswith(('全部', '出现', '位面', '奖励', '获得', '每', '进入',
                                          '战斗', '装备$', '图鉴'))):
                name = t
                break
        if not name:
            return None
        eff_parts = []
        grab = False
        for t, _x, _y in texts:
            if t == name and not grab:
                grab = True
                continue
            if grab:
                if t.startswith(('出现位面', '位面[')):
                    break
                eff_parts.append(t)
        planes = ' '.join(t for t, _x, _y in texts if t.startswith('位面['))
        return name, ''.join(eff_parts)[:200], planes

    @operation_node(name='采投资图鉴', is_start_node=True, node_max_retry_times=3)
    def harvest(self) -> OperationRoundResult:
        ctrl = self.ctx.controller
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        self._scroll_to_top()
        empty = 0
        total_new = 0
        screens = 0
        with self.out.open('a', encoding='utf-8') as f:
            while empty < 3 and screens < 40:
                screens += 1
                img = ctrl.get_screenshot(independent=False)
                if img is None:
                    time.sleep(0.5)
                    continue
                row_ys = self._row_ys(img)
                log.info(f'[采图鉴] 屏{screens} 行Y={row_ys} seen={len(self.seen)}')
                new_this = 0
                for ry in row_ys:
                    for cx in GRID_COLS:
                        ctrl.click(Point(cx, ry), press_time=0.08, pc_alt=False)
                        time.sleep(0.9)   # 详情切换动画(实测 0.5 不够)
                        img2 = ctrl.get_screenshot(independent=False)
                        if img2 is None:
                            continue
                        det = self._detail(img2)
                        if det is None:
                            continue
                        name, eff, planes = det
                        if name in self.seen:
                            continue
                        self.seen.add(name)
                        new_this += 1
                        f.write(json.dumps({'name': name, 'effect': eff, 'planes': planes},
                                           ensure_ascii=False) + '\n')
                        f.flush()
                total_new += new_this
                empty = empty + 1 if new_this == 0 else 0
                if not self._scroll_down():
                    # 滚到底:再扫一屏确认后收尾
                    empty = 3
        return self.round_success(f'采毕:屏{screens} 新增{total_new} 总{len(self.seen)} → {self.out.name}')
