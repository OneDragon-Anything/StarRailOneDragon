"""货币战争 通用拖角色 op(开发/测试用,槽位直接输入)。

从 ``(from_row, from_idx)`` 拖一个角色到 ``(to_row, to_idx)``。``row ∈ {"front","back","bench"}``,
``idx`` 1-based。用途:开发 / 测试时精确移动角色(如覆盖各槽位 ``read_star``);也供未来需精确拖角色的流程复用。

拖拽机制(同 ``DeployBench`` 5.1.9 / ADR-0100):``mouse_move`` 源 **avatar**(bug#1 settle —— 截图移光标
后紧接 drag 落空,先 settle 到源)→ ``drag_to(hold_time=1.0`` **长按拾取** —— 短按被判 click 开详情不拾取,
**长按才拾取角色**,这是 MCP ``drag`` 没有 hold 导致 deployed→bench 拖不动的根因)→ ``mouse_move`` 羁绊面板区
释放光标(防 drag 锁残留致后续 drag 落空)。avatar = 槽中心 + 上左偏移(~20px 小目标 grounding 不稳,retry 多偏移)。
验:drag 前后**源槽像素 diff**(角色离开 / swap 换人 都致源槽变)= 生效;全偏移都没变 → round_fail。

**已验方向(2026-08-13 实机)**:bench→bench ✓(飞霄)、deployed→deployed(同排 / 跨排)✓(万敌)。
**限制:deployed→bench 直接拖不生效**(6 种拾取策略 back→bench 全失败)—— CW 机制上「舞台→备战」需 **swap**
(拖 bench 角色到舞台角色 → 舞台角色回 bench),非舞台角色直接拖到空 bench 槽。要「把 deployed 角色弄上 bench」,
用 bench→deployed swap(from=bench → to=deployed),而非 deployed→bench。

TODO(后排槽位数动态):后排槽位数随**财富宝钻**(+1 团队规模上限,D-19 / gameplay doc)/ 诅咒·宝石剑泽尔里奇(−1)
变化,基准 6,可能 5-10。screen_info「后排-1..6」是基准;>6 时「后排-7..N」**未建档** → 本 op 读不到该 idx 会
``round_fail``,待画面建档补动态后排槽(运行时 CV 检测实际槽数 + upsert 后排-N area)后再支持。
"""
import time
from typing import ClassVar

import cv2
import numpy as np

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# row 英文 → screen_info area 前缀
_ROWS: dict[str, str] = {'front': '前排', 'back': '后排', 'bench': '备战栏'}
# 拾取策略(retry,按 (off_x, off_y, hold_time, duration) 逐个试,源槽像素变 = 中):
#  - **deployed(前/后排)立绘 center 可直接拖**(deploy_bench._sell_offtarget_deployed 实证:center + duration1.5 无 hold);
#  - **bench 卡需 avatar 偏移 + 长按**(deploy_bench 5.1.9:center mouseDown 判 click 开详情不拾取 → avatar 左上 + hold)。
# center 先试(两类都覆盖),avatar 偏移兜底(bench 卡 / ~20px avatar grounding 不稳)。
_PICKUPS: list[tuple[int, int, float, float]] = [
    (0, 0, 0.0, 1.5),       # center + 长拖(deployed-style,_sell_offtarget_deployed 实证)
    (0, 0, 1.0, 1.0),       # center + 长按(bench 卡 long-press 拾取)
    (-40, -50, 1.0, 1.0),   # avatar 左上(bench 5.1.9 校准)
    (-4, -30, 1.0, 1.0),
    (-25, -40, 1.0, 1.0),
    (-15, -35, 1.0, 1.0),
]


class DragCwChar(SrOperation):
    """货币战争 拖动角色(通用,槽位输入;开发/测试用)。

    ``run_operation`` 调用例::
        run_operation('...drag_cw_char.DragCwChar',
                      args={'from_row': 'bench', 'from_idx': 9, 'to_row': 'bench', 'to_idx': 1})
    """

    SCREEN_NAME: ClassVar[str] = '货币战争-备战'
    STATUS_DRAGGED: ClassVar[str] = '已拖动'
    STATUS_BAD_SLOT: ClassVar[str] = '槽位参数非法或 screen_info 读不到'

    def __init__(self, ctx: SrContext, from_row: str, from_idx: int,
                 to_row: str, to_idx: int) -> None:
        """拖 ``(from_row, from_idx)`` → ``(to_row, to_idx)``。

        Args:
            from_row / to_row: ``"front"`` / ``"back"`` / ``"bench"``。
            from_idx / to_idx: 1-based 槽位号(前排 1-4 / 后排 1-6 基准 / 备战栏 1-9)。
        """
        SrOperation.__init__(self, ctx, op_name='货币战争-拖动角色')
        self.from_row: str = from_row
        self.from_idx: int = from_idx
        self.to_row: str = to_row
        self.to_idx: int = to_idx

    def _slot_center(self, row: str, idx: int) -> Point | None:
        """从 screen_info 读 ``{前排/后排/备战栏}-{idx}`` 区域中心;读不到 → None。"""
        si = self.ctx.screen_loader.get_screen(DragCwChar.SCREEN_NAME)
        if si is None:
            return None
        prefix = _ROWS.get(row)
        if prefix is None:
            return None
        area = next((a for a in si.area_list if a.area_name == f'{prefix}-{idx}'), None)
        if area is None or area.pc_rect is None:
            return None
        return area.pc_rect.center

    @operation_node(name='拖动角色', is_start_node=True)
    def drag(self) -> OperationRoundResult:
        src = self._slot_center(self.from_row, self.from_idx)
        dst = self._slot_center(self.to_row, self.to_idx)
        if src is None or dst is None:
            log.warning(f'[cw-drag] 槽位读不到 from={self.from_row}-{self.from_idx}'
                        f' to={self.to_row}-{self.to_idx}(screen_info 缺该 area;row 非法 或 后排>6 见模块 TODO)')
            return self.round_fail(status=DragCwChar.STATUS_BAD_SLOT)
        before = self.screenshot()
        for ox, oy, hold, dur in _PICKUPS:
            pickup = Point(int(src.x) + ox, int(src.y) + oy)
            self.ctx.controller.mouse_move(pickup)                      # bug#1 settle(先到源)
            time.sleep(0.2)
            self.ctx.controller.drag_to(start=pickup, end=dst, duration=dur, hold_time=hold)
            time.sleep(0.5)
            self.ctx.controller.mouse_move(Point(100, 500))             # 释放光标(防 drag 锁残留)
            time.sleep(0.3)
            if self._src_changed(before, self.screenshot(), src):
                log.info(f'[cw-drag] {self.from_row}-{self.from_idx} → {self.to_row}-{self.to_idx}'
                         f' ✓ (pickup off=({ox},{oy}) hold={hold} dur={dur},源槽像素变)')
                return self.round_success(DragCwChar.STATUS_DRAGGED, wait=1)
            log.info(f'[cw-drag] pickup off=({ox},{oy}) hold={hold} dur={dur} 源槽未变,试下一策略')
        log.warning(f'[cw-drag] {self.from_row}-{self.from_idx} → {self.to_row}-{self.to_idx}'
                    f' 拖 {len(_PICKUPS)} 次源槽未变(center/avatar 都试过;bug#1 间歇;调用方可重跑)')
        return self.round_fail(status=DragCwChar.STATUS_DRAGGED)

    @staticmethod
    def _src_changed(before: np.ndarray, after: np.ndarray, src: Point,
                     diff_thr: float = 8.0) -> bool:
        """drag 前后源槽中心 40×40 crop 像素均值 diff > 阈 = 变(角色离开 / swap 换人都致变)。"""
        x, y = int(src.x), int(src.y)
        b = before[y - 20:y + 20, x - 20:x + 20]
        a = after[y - 20:y + 20, x - 20:x + 20]
        if b.size == 0 or a.size == 0:
            return False
        return float(np.mean(cv2.absdiff(b, a))) > diff_thr


_EXPORT = DragCwChar
