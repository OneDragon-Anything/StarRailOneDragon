"""货币战争 部署 op(D-98:接入 plan() 的 DeployMove,替代 v1 naive 填位)。

**策略驱动部署**(D-98,2026-08-07):读 ``session.pending_deploys``(plan 算出的 DeployMove 列表),
按每个 move 的 ``to_row``(front/back)+ ``bench_idx``(对应 tracked_bench 顺序)拖到对应排的空槽。
不再无脑从槽 0 拖全部到前排优先。

**回退**:session 无 pending_deploys(独立 run / 旧 code)→ 退 naive 填位(前排优先,从已部署数起)。

槽位坐标固定在 screen_info「货币战争-备战」(备战栏-1..9 / 前排-1..4 / 后排-1..6)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_observation import read_deployed_count
from sr_od.application.currency_war.cw_state import DeployMove
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class DeployBench(SrOperation):
    """备战阶段:策略驱动部署(plan DeployMove → 按 to_row 拖到对应排)。"""

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
            log.info('[cw-deploy] 备战栏无槽坐标,跳过')
            return self.round_success(DeployBench.STATUS_NO_BENCH)

        # D-98:策略驱动部署 —— 读 session.pending_deploys(plan 算出的 DeployMove 列表)。
        match = self.ctx.cw_match
        moves: list[DeployMove] = (
            list(match.session.pending_deploys) if match is not None else []
        )

        if moves:
            log.info(f'[cw-deploy] 策略驱动:plan 给了 {len(moves)} 个 DeployMove')
            self._deploy_strategic(moves, bench, front, back)
        else:
            log.info('[cw-deploy] 无 pending_deploys → naive 填位(前排优先)')
            self._deploy_naive(bench, front, back)

        # 验落地(bug#1:drag 落空观测)。
        time.sleep(0.5)
        deployed_after = read_deployed_count(self.ctx, self.screenshot())
        log.info(f'[cw-deploy] 拖完 已部署={deployed_after}')

        return self.round_success(DeployBench.STATUS_DEPLOYED, wait=1)

    def _deploy_strategic(self, moves: list[DeployMove], bench: list[Point],
                          front: list[Point], back: list[Point]) -> None:
        """D-98 策略驱动:按 DeployMove(bench_idx, to_row) 拖到对应排的空槽。

        bench_idx 对应 tracked_bench 顺序(plan simulate 的 bench 顺序 = tracked_bench)。
        to_row = "front"/"back" → 拖到对应排下一个空槽(用计数器追踪已填)。
        """
        front_idx = 0  # 前排已填数(追踪空槽位置)
        back_idx = 0
        dragged = 0
        for mv in moves:
            if mv.bench_idx >= len(bench):
                log.warning(f'[cw-deploy] bench_idx={mv.bench_idx} 超出 bench 槽数 {len(bench)},跳过')
                continue
            src = bench[mv.bench_idx]
            if mv.to_row == 'front' and front_idx < len(front):
                dst = front[front_idx]
                front_idx += 1
            elif back_idx < len(back):
                dst = back[back_idx]
                back_idx += 1
            elif front_idx < len(front):  # back 满了,溢出到 front
                dst = front[front_idx]
                front_idx += 1
            else:
                log.warning(f'[cw-deploy] 舞台槽位已满,跳过 DeployMove(bench_idx={mv.bench_idx})')
                break
            self.ctx.controller.drag_to(end=dst, start=src, duration=1.0)
            time.sleep(0.4)
            dragged += 1
            log.info(f'[cw-deploy] 策略拖:bench[{mv.bench_idx}]({mv.faction}) → '
                     f'{mv.to_row}槽(前排已填{front_idx}/后排已填{back_idx})')

        # 部署剩余 bench 角色(naive 填位补满)
        remaining_bench = [i for i in range(len(bench))
                           if i not in {mv.bench_idx for mv in moves}]
        targets = front[front_idx:] + back[back_idx:]
        for i, bench_i in enumerate(remaining_bench):
            if i >= len(targets):
                break
            self.ctx.controller.drag_to(end=targets[i], start=bench[bench_i], duration=1.0)
            time.sleep(0.4)
            dragged += 1
        log.info(f'[cw-deploy] 策略拖完:共拖 {dragged} 个(plan {len(moves)} + 补剩余)')

    def _deploy_naive(self, bench: list[Point], front: list[Point],
                      back: list[Point]) -> None:
        """回退:naive 填位(前排优先,从已部署数起)。"""
        targets = front + back
        deployed = read_deployed_count(self.ctx, self.last_screenshot)
        start = deployed if deployed is not None else 0
        n = max(0, min(len(bench), len(targets) - start))
        log.info(f'[cw-deploy] naive:已部署={deployed} 从槽{start}起 拖{n}个')
        for i in range(n):
            self.ctx.controller.drag_to(end=targets[start + i], start=bench[i], duration=1.0)
            time.sleep(0.4)
