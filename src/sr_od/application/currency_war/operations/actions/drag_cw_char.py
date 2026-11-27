"""货币战争 通用拖角色 op + **统一拖拽原语** ``drag_char``。

本模块提供两层:

1. ``DragCwChar.drag_char``(静态原语,**生产共用**):中心拖一个角色 ``src → dst`` —— ``mouse_move`` 源
   (settle:框架截图前把光标移角落,紧接 drag 落空,先 settle 到源)→ ``drag_to(hold_time=0`` **按下即移**
   即拾取 实测)→ ``park_cursor`` 把光标停到中立区(防 drag 锁残留致后续 drag 落空)。
   **机械执行零判效**(阶段三判效拆除,总纲阶段三族2):原「验源槽像素 diff + retry 3 次」
   随拆除停用——发出即职责完成,落地事实归下一帧入口观察 reconcile 对账;deploy(``CwActionDeployMoveOp``)/
   穿戴工具原子(prep_actions 机械原语经统一拖拽原语)/ sell(``drag_bench_to_sell``)/ 本 op 都走它
   —— **全仓角色拖拽机制单一源**(不再各处散落 drag_to + avatar 偏移)。

2. ``DragCwChar``(op,开发 / 测试用):``run_operation`` 按 ``(from_row, from_idx) → (to_row, to_idx)`` 拖,
   ``row ∈ {"front","back","bench"}``,`idx` 1-based。槽位坐标从 screen_info 读;**后排槽位数随财富宝钻
   (+1 团队规模)变化**(6-9 格,各档独立建档「后排 / 后排7槽 / 后排8槽 / 后排9槽」)——涉 back 拖拽
   调用方必须声明布局档 ``back_slot_count``(零声明构造期拒绝,禁静默落 6 格基线:基线拖点在 7+ 格局
   恰骑真实槽右边界 ≈70px,拖拽成败变硬币);``back_centers``(当帧实测槽中心)保留为显式几何覆盖,
   优先于布局档消费(存量直调兼容,坐标不进 screen_info 单一真相源,仅存留非推荐)。
   drag 节点机械段走 ``drag_char_guarded`` 守卫宿主(失焦先激活 + sim 装配静默,
   prep_actions 单一宿主申报辖内)。

**拖拽机制(实测,推翻旧 avatar 假设)**:整张卡可拖 —— 从**卡中心**拖、``hold_time=0``(按下即移)
即拾取上阵(实测:中心 drag 飞霄 bench→bench → 上阵 ✓)。旧结论「必须拖 avatar 左上小圆 + hold 1秒长按」
**全错**:左上小圆是**星标**非头像;详情面板是 **click(松开)** 触发非 mouseDown;drag = 按下+移动。旧 avatar
偏移 + 长按反易被判长按 / click 开详情 → ~50% 失败。

**已验方向(实机)**:bench → bench ✓(飞霄,中心拖 + hold0)。**限制:deployed → bench 直接拖
不生效** —— CW 机制「舞台 → 备战」需 **swap**(拖 bench 角色到舞台角色 → 舞台角色回 bench),非舞台角色直接
拖到空 bench 槽。要「把 deployed 角色弄上 bench」用 bench → deployed swap(from=bench → to=deployed)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.obs.cw_back_layout import _layout_prefixes
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# row 英文 → screen_info area 前缀
_ROWS: dict[str, str] = {'front': '前排', 'back': '后排', 'bench': '备战栏'}


class DragCwChar(CwOperation):
    """货币战争 拖动角色(通用,槽位输入;开发 / 测试用)+ 统一拖拽原语 ``drag_char``。
    起点:货币战争-备战画面;终点:原画面(角色已拖到目标槽位)。
    消耗:零(纯界面拖拽;落地事实归调用方下一帧 analyze_screen 对账)。

    槽位坐标系(本 op 恒 1 基画面物理槽位):from_idx / to_idx = 「货币战争-备战」
    画面物理槽位号 = screen_info「前排-N / 后排-N / 备战栏-N」area 序号,1 基,
    构造期校验 1-99;取值时机 = 调用方按当帧读数传参(本 op 零读屏不现读,坐标
    新鲜度纪律归调用方)。与 extras 换算:extras.bench.slots 数组为 0 基下标,
    备战栏槽位号 = 数组下标 + 1(同 CwSellBenchBySlot.slot 口径)。
    与 CwActionMoveUnitOp(cw_op 域)基差异:其 bench 参数为 0 基状态容器
    下标、front/back 为排内 1 基画面槽号——同族拖动动作两类基不同,跨类传参
    前先对表,勿以本 op 口径直填其参数(反之亦然)。back 声明纪律的差异
    (仅本 op 侧,MoveUnit 侧不动):MoveUnit 的 back_slot_count 缺省 6——
    其调用方是框架发出点(恒戳当帧真值),缺省只是签名兼容;本 op 主要受众
    是 MCP 直调 agent,缺省 6 会把「没传」静默解释成 6 格,恰复活基线骑界
    事故形态,故零声明构造期拒绝(两种显式声明形态见 back_slot_count /
    back_centers 参数段)。

    ``run_operation`` 调用例::

        run_operation('...drag_cw_char.DragCwChar',
                      args={'from_row': 'bench', 'from_idx': 9,
                            'to_row': 'back', 'to_idx': 2,
                            'back_slot_count': 7})
        # from_idx/to_idx 均 1 基画面物理槽位:bench 9 = 备战栏第 9 槽(extras 下标 8);
        # 拖到后排(back)必须带 back_slot_count,零声明的调用构造期即拒绝

    生产侧(deploy / sell)直接调 ``DragCwChar.drag_char(op, src, dst)`` 静态原语(坐标输入,不走节点图)。

    :param from_row: 源行:``"front"`` / ``"back"`` / ``"bench"``。
    :param from_idx: 源槽位号,1 基画面物理槽位(前排 1-4 / 后排 1-9 / 备战栏 1-9;
        = screen_info 对应 area 序号);越界构造期拒绝。
    :param to_row: 目标行(同 ``from_row``)。
    :param to_idx: 目标槽位号(同 ``from_idx`` 口径)。
    :param back_slot_count: 后排布局档(画面物理总槽数,键域 6-9,布局档表 =
        screen_info「后排(6)/后排7槽/后排8槽/后排9槽」)。涉 back 拖拽
        (from_row 或 to_row 为 back)必须二选一声明本参数或 ``back_centers``,
        两者都缺 = 构造期 ValueError(带直调指引);直调者按当帧 extras
        部署上限 −4 取值。不涉 back 时忽略(None 合法)。
    :param back_centers: (兼容保留,非推荐)后排实际槽位中心 ``[[x, y], ...]``,
        1080p 画面像素坐标;数组 0 基,第 N 项 = 后排物理槽位 N+1。语义 =
        显式几何覆盖,优先于布局档消费(存量直调形态兼容;坐标不进
        screen_info 单一真相源,新调用优先用 ``back_slot_count`` 布局档)。
        与 ``back_slot_count`` 双传时本参数优先(调用方自担几何真值,
        声明档仅存档不消费)。
    """

    SCREEN_NAME: ClassVar[str] = '货币战争-备战'
    STATUS_DRAGGED: ClassVar[str] = '已拖动'
    STATUS_BAD_SLOT: ClassVar[str] = '槽位参数非法或 screen_info 读不到'

    def __init__(self, ctx: SrContext, from_row: str, from_idx: int,
                 to_row: str, to_idx: int,
                 back_slot_count: int | None = None,
                 back_centers: list[list[int]] | None = None) -> None:
        CwOperation.__init__(self, ctx, op_name='货币战争-拖动角色')
        # 槽号 1 基(前排 1-4/后排 1-9/备战栏 1-9),0 或负数 = 参数错误
        #(实测传 0 曾静默无效无报错)——构造期拒绝,与 slot/max_clicks 同口径。
        for name, idx in (('from_idx', from_idx), ('to_idx', to_idx)):
            if not 1 <= idx <= 99:
                raise ValueError(f'{name} 越界: {idx}(可用值 1-99,槽位 1 基)')
        self.from_row: str = from_row
        self.from_idx: int = from_idx
        self.to_row: str = to_row
        self.to_idx: int = to_idx
        # back_centers 数组 0 基 ↔ 槽位 1 基:取用侧 idx-1(见 _slot_center)
        self.back_centers: list[Point] | None = (
            [Point(c[0], c[1]) for c in back_centers] if back_centers else None)
        self.back_slot_count: int | None = back_slot_count
        # —— 涉 back 声明守卫(构造期 fail-closed):「零声明静默落基线」= 布局
        # 骑界事故形态(基线拖点在 7+ 格局恰骑真实槽右边界),响亮拒绝即修法
        # 本体。四分支:零声明拒 / 仅档放行(键域校验)/ 仅实测中心豁免放行 /
        # 双传放行(实测中心优先)。键域纪律只管「声明了档」不管「档对不对」
        # ——声明 6 实况 7 的骑界风险类与 MoveUnit 同口径,已设计接受。
        if 'back' in (from_row, to_row):
            if back_slot_count is None and self.back_centers is None:
                raise ValueError(
                    '后排拖拽零声明被拒——二选一声明:back_slot_count'
                    '(当帧布局档 6-9;直调者按当帧 extras 部署上限 −4 取;'
                    '档表 = screen_info 后排/后排7槽/后排8槽/后排9槽)'
                    '或 back_centers(当帧实测槽中心,仅存留兼容)')
            # 键域校验只辖「布局档解析路径」(back_centers 在场 = 几何显式
            # 覆盖优先消费,声明档不参与解析,不校验)。
            if self.back_centers is None \
                    and back_slot_count not in _layout_prefixes():
                raise ValueError(
                    f'back_slot_count={back_slot_count} 域外'
                    '(6-9,布局档键域;档表 = screen_info '
                    '后排/后排7槽/后排8槽/后排9槽)')

    def _slot_center(self, row: str, idx: int) -> Point | None:
        """解析 ``(row, idx)`` → 槽位中心。

        - front / bench:screen_info ``{前排 / 备战栏}-{idx}``。
        - back:``back_centers`` 优先(显式几何覆盖);否则按 ``back_slot_count``
          布局档前缀查 area(构造期守卫保证档在键域内)。
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
        if row == 'back':
            prefix = _layout_prefixes()[self.back_slot_count]
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
                        f'(screen_info 缺该 area / row 非法 / 后排档 area 缺失'
                        f'——核对 back_slot_count 声明档={self.back_slot_count})')
            return self.round_fail(status=DragCwChar.STATUS_BAD_SLOT)
        # 机械段走守卫宿主(失焦先激活 + sim 装配静默;节点内惰性导入,
        # 宿主对 drag_cw_char 是函数级导入,模块级互导会成环向)。
        from sr_od.application.currency_war.prep_actions import (
            drag_char_guarded,
        )
        drag_char_guarded(self, self.ctx, src, dst)
        log.info(f'[cw-drag] {self.from_row}-{self.from_idx} → {self.to_row}-{self.to_idx}'
                 f' ✓ (中心拖 + hold0,机械发出)')
        return self.round_success(DragCwChar.STATUS_DRAGGED, wait=1)

    @staticmethod
    def drag_char(op: SrOperation, src: Point, dst: Point) -> None:
        """**统一角色拖拽原语**(生产共用:deploy / sell / 本 op)。

        中心拖 ``src → dst`` + ``hold_time=0``,机械执行零判效(阶段三
        判效拆除:原「验源槽像素 diff + retry 3 次」停用,发出即职责完成;
        落地事实归下一帧入口观察 reconcile 对账)。

        机制(实测,推翻旧 avatar 假设):整张卡可拖,中心拖 + 按下即移(hold_time=0)即拾取。
        流程:``mouse_move`` 源(settle,防截图移光标后紧接 drag 落空)→ ``drag_to(hold_time=0)``
        → ``park_cursor`` 把光标停到中立区(防 drag 锁残留致后续 drag 落空)。

        Args:
            op: 调用方 op(取 ``op.ctx.controller`` 操作)。
            src / dst: 源 / 目标槽中心(1080p)。
        """
        op.ctx.controller.mouse_move(src)                 # settle(先到源)
        time.sleep(0.2)
        op.ctx.controller.drag_to(start=src, end=dst, duration=1.0, hold_time=0.0)
        time.sleep(0.5)
        # 光标 parking:拖完把光标停到 UID 黑块中立区,免得停在画面元素上挡住后续识别。
        op.park_cursor(after_wait=0.3)
