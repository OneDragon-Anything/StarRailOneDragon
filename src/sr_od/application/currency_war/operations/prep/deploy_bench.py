import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_observation import read_deployed_count
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class DeployBench(SrOperation):
    """备战阶段:把备战栏角色拖拽部署到舞台(前排优先,满后再后排)。

    槽位坐标**固定写死在 screen_info「货币战争-备战」**(备战栏-1..9 / 前排-1..4 / 后排-1..6),
    不做运行时 CV(槽位无可靠视觉标记;坐标一次性测准,游戏拖拽会 snap 到槽)。
    naive 策略:能填就填,不选角色/羁绊。空备战栏位的拖拽是无害 no-op。

    注:智能选角(识别角色→按羁绊/命途部署)依赖角色识别,见 char_id 思路;
    本 op 是 v1 naive 填位。待接进 app + 实机测试(需游戏到备战)。
    """

    SCREEN_NAME: ClassVar[str] = '货币战争-备战'
    STATUS_DEPLOYED: ClassVar[str] = '已部署角色'
    STATUS_NO_BENCH: ClassVar[str] = '备战栏无角色'
    STATUS_NO_SCREEN: ClassVar[str] = '未加载货币战争-备战 screen_info'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-部署角色')

    def _centers(self, prefix: str, n: int) -> list[Point]:
        """从 screen_info 读 prefix-1..n 的区域中心。"""
        si = self.ctx.screen_loader.get_screen(DeployBench.SCREEN_NAME)
        if si is None:
            return []
        pts: list[Point] = []
        for i in range(1, n + 1):
            name = f'{prefix}-{i}'
            area = next((a for a in si.area_list if a.area_name == name), None)
            if area is not None and area.pc_rect is not None:
                pts.append(area.pc_rect.center)
        return pts

    @operation_node(name='部署备战栏角色', is_start_node=True)
    def deploy(self) -> OperationRoundResult:
        si = self.ctx.screen_loader.get_screen(DeployBench.SCREEN_NAME)
        if si is None:
            log.warning('[cw-deploy] 未加载「货币战争-备战」screen_info,跳过部署')
            return self.round_fail(status=DeployBench.STATUS_NO_SCREEN)

        bench = self._centers('备战栏', 9)
        front = self._centers('前排', 4)
        back = self._centers('后排', 6)
        if len(bench) == 0:
            log.info('[cw-deploy] 备战栏无槽坐标(screen_info 缺 备战栏-1..9?),跳过')
            return self.round_success(DeployBench.STATUS_NO_BENCH)

        targets = front + back  # 前排优先,满后再后排
        # 从「已部署数 X」起部署(跳过已占的前 X 个槽)。货币战争 drag-to-occupied **不交换(直接拒)**,
        # 故必须拖到空位:读舞台「X/Y」指示得 X,从 targets[X] 起。读不到 X → 退原行为(轮首空板)。
        deployed = read_deployed_count(self.ctx, self.last_screenshot)
        start = deployed if deployed is not None else 0
        n = max(0, min(len(bench), len(targets) - start))
        log.info(f'[cw-deploy] bench槽={len(bench)} 前/后排={len(front)}/{len(back)} '
                 f'已部署={deployed} 从槽{start}起 拖{n}个')
        for i in range(n):
            self.ctx.controller.drag_to(end=targets[start + i], start=bench[i], duration=1.0)
            time.sleep(0.4)
        # 验落地(bug#1:drag 被判拖拽落空 / 拖到已占槽被拒 → 角色没上去,曾因无日志没察觉;D-43 重置根因之一)。
        # 重读已部署数比 delta;**仅观测供复盘不硬 fail**(部分部署仍可出战;且备战栏空槽 drag 是 no-op,
        # 增量<拖数也可能是空槽而非 bug)。deployed_after=None = 读不到「X/Y」,无法验。
        time.sleep(0.5)
        deployed_after = read_deployed_count(self.ctx, self.screenshot())
        log.info(f'[cw-deploy] 拖完 已部署 {deployed or 0}->{deployed_after}(拖了{n}个;'
                 f'空槽 no-op / bug#1 落空都让增量<拖数)')

        return self.round_success(DeployBench.STATUS_DEPLOYED, wait=1)
