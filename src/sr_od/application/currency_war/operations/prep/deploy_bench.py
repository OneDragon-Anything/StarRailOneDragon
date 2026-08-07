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

        # D-102:实际 bench 身份识别(read_bench_chars SIFT)→ 按角色 position_pref deploy,
        # 替代 tracked_bench idx(tracked_bench 与实际槽位错位 → 拖错角色,旧 D-98 bug 根因)。
        # 配饰/变体角色 SIFT 漏识别(D-75 待核)→ 漏的 naive 补舞台剩余;后续采图鉴立绘补全。
        templates = self._get_templates()
        actual = read_bench_chars(self.ctx, self.last_screenshot, templates) if templates else []
        # D-108:deploy 优先级(CW deployed 锁定 → 限槽时 target 阵营先占;off-target 留 bench 可 sell)。
        # bench>capacity(early:多牌低等级)时,target-first 保证 target 角色上任(非被 off-target 挤到 bench),
        # off-target 溢出留 bench(sellable)。board=deployed 锁定 → 先 deploy 谁 = 谁 locked 占槽 → target 优先。
        match = self.ctx.cw_match
        _tgt = match.session.target_comp if (match is not None and match.session is not None) else None
        target_factions: set[str] = set(_tgt.factions) if _tgt is not None else set()
        # D-108d:cap-limited deploy。CW deploy cap=level(max_units);旧码拖**全部**识别 bench(7),cap(level 4)
        # 只落 4,余 drag-to-occupied 被拒浪费(每轮多 3 drag)。cap_remaining=level-已部署 → 仅拖 cap_remaining 个
        # (D-108c target-first 占有限额,off-target 不再浪费 drag 也避免误 lock)。level/deployed 读不到 → None(全 deploy 兜底)。
        # D-108f:SIFT deployed count(read_deployed_chars → occupied 槽 len)替 OCR read_deployed_count。
        # OCR 死胡同(3 法全败:rect-scope/crop+zoom None,full-screen 读错元素);SIFT 同 read_bench_chars D-102
        # 管线 robust。无 templates → OCR 兜底(退化,可能 None)。
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
            self._deploy_by_identity(actual, bench, front, back, target_factions, cap_remaining, _deployed_before, _dep_sift)
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
                            front: list[Point], back: list[Point],
                            target_factions: set[str] | None = None,
                            cap_remaining: int | None = None,
                            deployed_before: int | None = None,
                            _dep_sift: list | None = None) -> None:
        """D-102:按**实际识别**的 bench 角色身份 deploy(替代 tracked_bench idx)。

        每个识别成功的角色(STRONG):按 ``position_pref``(front/back)拖到对应排下一个空槽。
        未识别槽(配饰/变体 SIFT 漏,D-75 待核):naive 补舞台剩余空槽(位置式,不靠身份)。
        绕过旧 bug(tracked_bench 顺序 ≠ 实际槽位 → 拖错)。

        D-108:target_factions 非空 → **target 阵营角色先 deploy**(sorted target-first)。CW deployed 锁定
        → 限槽(bench>capacity)时 target 先占槽 locked,off-target 溢出留 bench(sellable);非 target 被
        挤到 bench 而非 locked 占槽。无 target(早期/reactive)→ 不排序(原行为,全 deploy)。
        """
        if target_factions:
            # D-108b:用角色**全阵营**(get_char.factions)判 target,非 BenchChar.faction(=factions[0] 只首阵营)。
            # 多羁绊角色(飞霄=仙舟+追击)首阵营可能非 target → factions[0] 漏判 → 排序错(实跑 r1:飞霄 被排 off-target
            # 尽管是 仙舟/追击)。任一阵营 ∈ target 即 target。
            def _is_target(bc) -> bool:
                ch = get_char(bc.char_id)
                if ch is None:
                    return False
                # 角色全羁绊(factions 阵营 + flows 流派 + independent)—— comp.factions / board 混用阵营+流派
                # (巡击青雀=[仙舟(阵营),追击(流派)]),故匹配须取全羁绊:赛飞儿 factions=夜之半神 + flows=追击、减益
                # → 只取 factions 漏「追击」→ 误判 off-target。全羁绊任一 ∈ target 即 target。
                bonds = set(ch.factions) | set(ch.flows)
                if ch.independent:
                    bonds.add(ch.independent)
                return bool(bonds & target_factions)
            actual = sorted(actual, key=lambda bc: (0 if _is_target(bc) else 1, bc.slot))
        # D-116:SIFT slot-level occupied detection(替 D-108e front-first offset 猜测)。
        # deployed_sift(D-108f)的 BenchChar.slot = 排内 1-based idx;position_pref="front"/"back"。
        # 用 occupied set 跳过已占槽,只拖到空槽(不猜 offset → 不拖 occupied → 不 swap churn/target 不升)。
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
            self.ctx.controller.drag_to(end=dst, start=src, duration=1.0)
            time.sleep(0.4)
            dragged += 1
            log.info(f'[cw-deploy] 身份拖:bench[{bc.slot}]({bc.char_id}/{pref}) → {dst}')
        # 未识别槽 naive 补空槽
        deployed_slots = {bc.slot for bc in actual}
        remaining = [i for i in range(1, len(bench) + 1) if i not in deployed_slots]
        for slot_i in remaining:
            if cap_remaining is not None and dragged >= cap_remaining:
                break
            dst = (self._find_empty_slot('back', front, back, occupied_front, occupied_back)
                   or self._find_empty_slot('front', front, back, occupied_front, occupied_back))
            if dst is None:
                break
            self.ctx.controller.drag_to(end=dst, start=bench[slot_i - 1], duration=1.0)
            time.sleep(0.4)
            dragged += 1
        log.info(f'[cw-deploy] 身份拖完:共拖 {dragged} 个(识别 {len(actual)} + 补剩余 {len(remaining)})')

    @staticmethod
    def _find_empty_slot(pref: str, front: list[Point], back: list[Point],
                         occupied_front: set[int], occupied_back: set[int]) -> Point | None:
        """D-116:在 pref 排找第一个空槽(不在 occupied set 中的 idx 1..len)。无空槽 → 尝试另一排 → None。"""
        slots, occupied = (front, occupied_front) if pref == 'front' else (back, occupied_back)
        for i in range(1, len(slots) + 1):
            if i not in occupied:
                occupied.add(i)   # 标记已占(本函数调用方可能多次 deploy)
                return slots[i - 1]
        # pref 排满 → 尝试另一排
        other_slots, other_occ = (back, occupied_back) if pref == 'front' else (front, occupied_front)
        for i in range(1, len(other_slots) + 1):
            if i not in other_occ:
                other_occ.add(i)
                return other_slots[i - 1]
        return None

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
