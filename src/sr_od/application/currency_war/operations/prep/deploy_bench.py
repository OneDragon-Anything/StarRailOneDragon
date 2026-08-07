# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

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
from sr_od.application.currency_war.cw_chars import get_char
from sr_od.application.currency_war.cw_identity_obs import (
    read_bench_chars,
    read_deployed_chars,
)
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

        templates = self._get_templates()
        actual = read_bench_chars(self.ctx, self.last_screenshot, templates) if templates else []
        match = self.ctx.cw_match
        _tgt = match.session.target_comp if (match is not None and match.session is not None) else None
        target_factions: set[str] = set(_tgt.factions) if _tgt is not None else set()
        _dep_sift = read_deployed_chars(self.ctx, self.last_screenshot, templates) if templates else None
        _deployed_before: int | None = (len(_dep_sift) if _dep_sift is not None
                                        else read_deployed_count(self.ctx, self.last_screenshot))
        _lv = (match.session.last_state.level
               if (match is not None and match.session is not None
                   and match.session.last_state is not None) else None)
        cap_remaining: int | None = (max(0, _lv - _deployed_before)
                                     if (_lv and _deployed_before is not None) else None)
        if actual:
            log.info(f'[cw-deploy] 身份驱动:识别 {len(actual)} 个 '
                     f'{[(b.char_id, b.position_pref) for b in actual]} '
                     f'target_factions={target_factions or "(无 target)"} '
                     f'cap_remaining={cap_remaining}(lv={_lv} deployed={_deployed_before})')
            self._deploy_by_identity(actual, bench, front, back, target_factions,
                                     cap_remaining, _deployed_before, _dep_sift, templates)
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

        time.sleep(0.5)
        log.info('[cw-deploy] 拖完')

        return self.round_success(DeployBench.STATUS_DEPLOYED, wait=1)

    def _get_templates(self) -> AvatarTemplates | None:
        """加载 avatar SIFT 模板(缓存到 ctx.cw_avatar_templates,首次 load 后复用)。"""
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
                            front: list[Point], back: list[Point],
                            target_factions: set[str] | None = None,
                            cap_remaining: int | None = None,
                            deployed_before: int | None = None,
                            _dep_sift: list | None = None,
                            templates: AvatarTemplates | None = None) -> None:
        """D-102:按**实际识别**的 bench 角色身份 deploy(替代 tracked_bench idx)。

        D-108:target_factions 非空 → target-first sorted deploy。
        D-108d:cap_remaining 限 deploy 数。
        D-108f:SIFT deployed count 替 OCR。
        D-116:SIFT slot-level occupied detection(_find_empty_slot)。
        D-117:bug#1 缓解(mouse_move 先)+ 长 duration + SIFT 验 + retry(3 次)。
        """
        if target_factions:
            def _is_target(bc) -> bool:
                ch = get_char(bc.char_id)
                if ch is None:
                    return False
                bonds = set(ch.factions) | set(ch.flows)
                if ch.independent:
                    bonds.add(ch.independent)
                return bool(bonds & target_factions)
            actual = sorted(actual, key=lambda bc: (0 if _is_target(bc) else 1, bc.slot))

        occupied_front: set[int] = set()
        occupied_back: set[int] = set()
        if _dep_sift:
            for d in _dep_sift:
                if d.position_pref == 'front':
                    occupied_front.add(d.slot)
                else:
                    occupied_back.add(d.slot)
            log.info(f'[cw-deploy] occupied(SIFT) front={sorted(occupied_front)} back={sorted(occupied_back)} '
                     f'(共 {len(occupied_front) + len(occupied_back)} occupied)')

        dragged = 0
        for bc in actual:
            if cap_remaining is not None and dragged >= cap_remaining:
                break
            if bc.slot < 1 or bc.slot > len(bench):
                continue
            src = bench[bc.slot - 1]
            pref = bc.position_pref or 'back'
            dst = self._find_empty_slot(pref, front, back, occupied_front, occupied_back)
            if dst is None:
                continue
            # D-118:**CW deploy = click-select→click-deploy**(非 drag!2026-08-08 实测:drag_to 100% 不 land,
            # click(bench)→click(stage slot) 成功 deploy)。旧码 D-102~D-117 全用 drag_to → 从未真正 deploy。
            self.ctx.controller.click(src)
            time.sleep(0.3)
            self.ctx.controller.click(dst)
            time.sleep(0.5)
            dragged += 1
            log.info(f'[cw-deploy] click-deploy:bench[{bc.slot}]({bc.char_id}/{pref}) → {dst}')

        deployed_slots = {bc.slot for bc in actual}
        remaining = [i for i in range(1, len(bench) + 1) if i not in deployed_slots]
        for slot_i in remaining:
            if cap_remaining is not None and dragged >= cap_remaining:
                break
            dst = (self._find_empty_slot('back', front, back, occupied_front, occupied_back)
                   or self._find_empty_slot('front', front, back, occupied_front, occupied_back))
            if dst is None:
                break
            # D-118:click-deploy(naive 补槽也用 click,非 drag)
            self.ctx.controller.click(bench[slot_i - 1])
            time.sleep(0.3)
            self.ctx.controller.click(dst)
            time.sleep(0.5)
            dragged += 1
        log.info(f'[cw-deploy] click-deploy 完:共拖 {dragged} 个(识别 {len(actual)} + 补剩余 {len(remaining)})')

    @staticmethod
    def _find_empty_slot(pref: str, front: list[Point], back: list[Point],
                         occupied_front: set[int], occupied_back: set[int]) -> Point | None:
        """D-116:在 pref 排找第一个空槽(不在 occupied set 中的 idx 1..len)。无空槽 → 尝试另一排 → None。"""
        slots, occupied = (front, occupied_front) if pref == 'front' else (back, occupied_back)
        for i in range(1, len(slots) + 1):
            if i not in occupied:
                occupied.add(i)
                return slots[i - 1]
        other_slots, other_occ = (back, occupied_back) if pref == 'front' else (front, occupied_front)
        for i in range(1, len(other_slots) + 1):
            if i not in other_occ:
                other_occ.add(i)
                return other_slots[i - 1]
        return None

    def _deploy_strategic(self, moves: list[DeployMove], bench: list[Point],
                          front: list[Point], back: list[Point]) -> None:
        """D-98 策略驱动:按 DeployMove(bench_idx, to_row) 拖到对应排的空槽。"""
        front_idx = 0
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
            elif front_idx < len(front):
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
