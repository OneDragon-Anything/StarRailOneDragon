"""货币战争 部署 op(D-98:接入 plan() 的 DeployMove,替代 v1 naive 填位)。

**策略驱动部署**(D-98,2026-08-07):读 ``session.pending_deploys``(plan 算出的 DeployMove 列表),
按每个 move 的 ``to_row``(front/back)+ ``bench_idx``(对应 tracked_bench 顺序)拖到对应排的空槽。
不再无脑从槽 0 拖全部到前排优先。

**回退**:session 无 pending_deploys(独立 run / 旧 code)→ 退 naive 填位(前排优先,从已部署数起)。

槽位坐标固定在 screen_info「货币战争-备战」(备战栏-1..9 / 前排-1..4 / 后排-1..6)。
"""
import time
from pathlib import Path
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_char_id import (
    AvatarTemplates,
    load_avatar_templates,
)
from sr_od.application.currency_war.cw_identity_obs import read_bench_chars
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

        # D-102:实际 bench 身份识别(read_bench_chars SIFT)→ 按角色 position_pref deploy,
        # 替代 tracked_bench idx(tracked_bench 与实际槽位错位 → 拖错角色,旧 D-98 bug 根因)。
        # 配饰/变体角色 SIFT 漏识别(D-75 待核)→ 漏的 naive 补舞台剩余;后续采图鉴立绘补全。
        templates = self._get_templates()
        actual = read_bench_chars(self.ctx, self.last_screenshot, templates) if templates else []
        if actual:
            log.info(f'[cw-deploy] 身份驱动:识别 {len(actual)} 个 '
                     f'{[(b.char_id, b.position_pref) for b in actual]}')
            self._deploy_by_identity(actual, bench, front, back)
        else:
            match = self.ctx.cw_match
            moves: list[DeployMove] = (
                list(match.session.pending_deploys) if match is not None else []
            )
            if moves:
                log.info(f'[cw-deploy] 识别失败 → 退 plan DeployMove({len(moves)},tracked_bench idx 可能错位)')
                self._deploy_strategic(moves, bench, front, back)
            else:
                log.info('[cw-deploy] 识别失败且无 pending_deploys → naive 填位')
                self._deploy_naive(bench, front, back)

        # 验落地(bug#1:drag 落空观测)。
        time.sleep(0.5)
        deployed_after = read_deployed_count(self.ctx, self.screenshot())
        log.info(f'[cw-deploy] 拖完 已部署={deployed_after}')

        return self.round_success(DeployBench.STATUS_DEPLOYED, wait=1)

    def _get_templates(self) -> AvatarTemplates | None:
        """加载 avatar SIFT 模板(缓存到 ctx.cw_avatar_templates,首次 load 后复用)。

        ``read_bench_chars`` 从没在 op 集成过(cw_identity_obs 是旁路离线用),故 op 里无现成预加载;
        首次 deploy 时 load,挂 ctx 缓存供本局后续 deploy/识别复用。
        """
        cached = getattr(self.ctx, 'cw_portrait_templates', None)
        if cached is not None:
            return cached
        portrait_dir = Path(__file__).resolve().parents[6] / 'assets/template/character_cw_portrait'
        if not portrait_dir.is_dir():
            log.warning(f'[cw-deploy] 立绘库目录不存在 {portrait_dir},退非身份 deploy')
            return None
        templates = load_avatar_templates(portrait_dir)
        self.ctx.cw_portrait_templates = templates
        log.info(f'[cw-deploy] 加载 {len(templates)} 个 avatar 模板(缓存 ctx)')
        return templates

    def _deploy_by_identity(self, actual: list, bench: list[Point],
                            front: list[Point], back: list[Point]) -> None:
        """D-102:按**实际识别**的 bench 角色身份 deploy(替代 tracked_bench idx)。

        每个识别成功的角色(STRONG):按 ``position_pref``(front/back)拖到对应排下一个空槽。
        未识别槽(配饰/变体 SIFT 漏,D-75 待核):naive 补舞台剩余空槽(位置式,不靠身份)。
        绕过旧 bug(tracked_bench 顺序 ≠ 实际槽位 → 拖错)。
        """
        front_idx = back_idx = 0
        dragged = 0
        for bc in actual:
            if bc.slot < 1 or bc.slot > len(bench):
                continue
            src = bench[bc.slot - 1]
            pref = bc.position_pref or 'back'
            if pref == 'front' and front_idx < len(front):
                dst, front_idx = front[front_idx], front_idx + 1
            elif back_idx < len(back):
                dst, back_idx = back[back_idx], back_idx + 1
            elif front_idx < len(front):   # back 满,溢出 front
                dst, front_idx = front[front_idx], front_idx + 1
            else:
                break
            self.ctx.controller.drag_to(end=dst, start=src, duration=1.0)
            time.sleep(0.4)
            dragged += 1
            log.info(f'[cw-deploy] 身份拖:bench[{bc.slot}]({bc.char_id}/{pref}) → '
                     f'{pref}槽(前{front_idx}/后{back_idx})')
        # 未识别槽(配饰/变体漏)naive 补舞台剩余空槽
        deployed_slots = {bc.slot for bc in actual}
        remaining = [i for i in range(1, len(bench) + 1) if i not in deployed_slots]
        targets = front[front_idx:] + back[back_idx:]
        for i, slot_i in enumerate(remaining):
            if i >= len(targets):
                break
            self.ctx.controller.drag_to(end=targets[i], start=bench[slot_i - 1], duration=1.0)
            time.sleep(0.4)
            dragged += 1
        log.info(f'[cw-deploy] 身份拖完:共拖 {dragged} 个(识别 {len(actual)} + 补剩余 {len(remaining)})')

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
