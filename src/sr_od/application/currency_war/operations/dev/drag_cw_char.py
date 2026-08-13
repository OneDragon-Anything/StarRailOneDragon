"""货币战争 通用拖角色 op + **统一拖拽原语** ``drag_char``。

本模块提供两层:

1. ``DragCwChar.drag_char``(静态原语,**生产共用**):中心拖一个角色 ``src → dst`` —— ``mouse_move`` 源
   (bug#1 settle:框架截图前把光标移角落,紧接 drag 落空,先 settle 到源)→ ``drag_to(hold_time=0`` **按下即移**
   即拾取,2026-08-13 实测)→ ``mouse_move`` 羁绊面板区释放光标(防 drag 锁残留致后续 drag 落空)→ 验**源槽
   像素 diff**(角色离开 / swap 换人都致源槽变)= 生效;retry ``max_retry`` 次。deploy(``DeployBench``)/
   sell(``_sell_offtarget_deployed``)/ 本 op 都走它 —— **全仓角色拖拽机制单一源**(不再各处散落 drag_to + avatar 偏移)。

2. ``DragCwChar``(op,开发 / 测试用):``run_operation`` 按 ``(from_row, from_idx) → (to_row, to_idx)`` 拖,
   ``row ∈ {"front","back","bench"}``,`idx` 1-based。槽位坐标从 screen_info 读;**后排槽位数随财富宝钻
   (+1 团队规模)/ 诅咒·宝石剑泽尔里奇(−1)变化**(基准 6,可能 5-10),screen_info「后排-1..6」是基准,
   >6 时调用方传 ``back_centers``(运行时检测到的实际后排槽中心,含 7+ 槽)覆盖。

**拖拽机制(2026-08-13 实测,推翻 ADR-0100)**:整张卡可拖 —— 从**卡中心**拖、``hold_time=0``(按下即移)
即拾取上阵(实测:中心 drag 飞霄 bench→bench → 上阵 ✓)。旧结论「必须拖 avatar 左上小圆 + hold 1秒长按」
**全错**:左上小圆是**星标**非头像;详情面板是 **click(松开)** 触发非 mouseDown;drag = 按下+移动。旧 avatar
偏移 + 长按反易被判长按 / click 开详情 → ~50% 失败。详见 ADR-012x(推翻 ADR-0100)。

**已验方向(2026-08-13 实机)**:bench → bench ✓(飞霄,中心拖 + hold0)。**限制:deployed → bench 直接拖
不生效** —— CW 机制「舞台 → 备战」需 **swap**(拖 bench 角色到舞台角色 → 舞台角色回 bench),非舞台角色直接
拖到空 bench 槽。要「把 deployed 角色弄上 bench」用 bench → deployed swap(from=bench → to=deployed)。
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


class DragCwChar(SrOperation):
    """货币战争 拖动角色(通用,槽位输入;开发 / 测试用)+ 统一拖拽原语 ``drag_char``。

    ``run_operation`` 调用例::

        run_operation('...drag_cw_char.DragCwChar',
                      args={'from_row': 'bench', 'from_idx': 9, 'to_row': 'bench', 'to_idx': 1})

    生产侧(deploy / sell)直接调 ``DragCwChar.drag_char(op, src, dst)`` 静态原语(坐标输入,不走节点图)。
    """

    SCREEN_NAME: ClassVar[str] = '货币战争-备战'
    STATUS_DRAGGED: ClassVar[str] = '已拖动'
    STATUS_BAD_SLOT: ClassVar[str] = '槽位参数非法或 screen_info 读不到'

    def __init__(self, ctx: SrContext, from_row: str, from_idx: int,
                 to_row: str, to_idx: int,
                 back_centers: list[Point] | None = None) -> None:
        """拖 ``(from_row, from_idx)`` → ``(to_row, to_idx)``。

        Args:
            from_row / to_row: ``"front"`` / ``"back"`` / ``"bench"``。
            from_idx / to_idx: 1-based 槽位号(前排 1-4 / 后排 1-6 基准 / 备战栏 1-9)。
            back_centers: 后排实际槽位中心(覆盖 screen_info)。**财富宝钻**(团队规模 +1)致后排 >6 时,
                screen_info「后排-1..6」不够 → 调用方传运行时检测到的实际后排槽中心(含 7+ 槽)。
                ``None`` → 用 screen_info 后排-N(基准 6)。
        """
        SrOperation.__init__(self, ctx, op_name='货币战争-拖动角色')
        self.from_row: str = from_row
        self.from_idx: int = from_idx
        self.to_row: str = to_row
        self.to_idx: int = to_idx
        self.back_centers: list[Point] | None = back_centers

    def _slot_center(self, row: str, idx: int) -> Point | None:
        """解析 ``(row, idx)`` → 槽位中心。

        - front / bench:screen_info ``{前排 / 备战栏}-{idx}``。
        - back:``back_centers`` 优先(财富宝钻 >6 时调用方传);否则 screen_info ``后排-{idx}``。
        读不到 → ``None``。
        """
        if row == 'back' and self.back_centers is not None:
            if 1 <= idx <= len(self.back_centers):
                return self.back_centers[idx - 1]
            return None
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
                        f' to={self.to_row}-{self.to_idx}'
                        f'(screen_info 缺该 area / row 非法 / 后排>6 未传 back_centers)')
            return self.round_fail(status=DragCwChar.STATUS_BAD_SLOT)
        if DragCwChar.drag_char(self, src, dst):
            log.info(f'[cw-drag] {self.from_row}-{self.from_idx} → {self.to_row}-{self.to_idx}'
                     f' ✓ (中心拖 + hold0,源槽像素变)')
            return self.round_success(DragCwChar.STATUS_DRAGGED, wait=1)
        log.warning(f'[cw-drag] {self.from_row}-{self.from_idx} → {self.to_row}-{self.to_idx}'
                    f' 拖3次源槽未变(bug#1 间歇 / deployed→bench 限制),调用方可重跑')
        return self.round_fail(status=DragCwChar.STATUS_DRAGGED)

    @staticmethod
    def drag_char(op: SrOperation, src: Point, dst: Point, max_retry: int = 3) -> bool:
        """**统一角色拖拽原语**(生产共用:deploy / sell / 本 op)。

        中心拖 ``src → dst`` + ``hold_time=0`` + retry + 验源槽像素变。

        机制(2026-08-13 实测,推翻 ADR-0100):整张卡可拖,中心拖 + 按下即移(hold_time=0)即拾取。
        流程:``mouse_move`` 源(bug#1 settle,防截图移光标后紧接 drag 落空)→ ``drag_to(hold_time=0)``
        → ``mouse_move`` 羁绊面板区释放光标(防 drag 锁残留致后续 drag 落空)→ 验源槽像素 diff(角色离开 / 换人)。

        Args:
            op: 调用方 op(取 ``op.ctx.controller`` 操作 + ``op.screenshot()`` 验证)。
            src / dst: 源 / 目标槽中心(1080p)。
            max_retry: retry 次数(防 bug#1 间歇 click/drag 时序)。

        Returns:
            ``True`` = 源槽像素变(拖生效);``False`` = retry 尽源槽未变。
        """
        before = op.screenshot()
        for _attempt in range(max_retry):
            op.ctx.controller.mouse_move(src)                 # bug#1 settle(先到源)
            time.sleep(0.2)
            op.ctx.controller.drag_to(start=src, end=dst, duration=1.0, hold_time=0.0)
            time.sleep(0.5)
            op.ctx.controller.mouse_move(Point(100, 500))      # 释放光标(防 drag 锁残留)
            time.sleep(0.3)
            if DragCwChar._src_changed(before, op.screenshot(), src):
                return True
        return False

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
