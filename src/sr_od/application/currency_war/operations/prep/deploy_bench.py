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
from sr_od.application.currency_war.cw_observation import (
    read_deployed_count,
)
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
        _dep_sift = read_deployed_chars(self.ctx, self.last_screenshot, templates) if templates else None
        # D-145(review-a0610 重大发现):deploy 全部 bench(slot-iteration + retry-stick),非 SIFT-gated。
        # 旧 `if actual`(SIFT read_bench_chars)只迭代 SIFT 可见角色;SIFT 只 4 角色可靠(D-75)→ 大多数
        # target 单位识别不了 → 永远不上 board → board[追击] 卡 1(D-140 真因,非 merge/cap/deployed-lock)。
        # 改:遍历 bench 物理槽 drag→board,retry-stick 验 bench-count 降(有角色 deployed;空槽/板满 不降→跳/停),
        # deploy 全部 owned(target+off-target)→ target 上场→bond 激活。pref 无身份用 front 先填(次优,target 上场首要)。
        # D-151(用户确认 deployed 可卖):deploy-swap —— board 有 off-target 阵营(∃ faction ∉ target)
        # → sell all deployed + redeploy bench(comp-curated via D-138/D-142 buying)。board OCR factions 做条件
        # (不需身份)。deployed-lock(doc gameplay:78)是误判,deployed 可卖(用户实机确认 gold 增加)。
        _match = self.ctx.cw_match
        _board = (_match.session.last_state.board
                  if (_match is not None and _match.session is not None
                      and _match.session.last_state is not None) else None)
        _tgt_comp = (_match.session.target_comp
                     if (_match is not None and _match.session is not None) else None)
        _target_factions: set[str] = set(_tgt_comp.factions) if _tgt_comp is not None else set()
        _has_offtarget = bool(_board and _target_factions
                             and any(f not in _target_factions for f in _board))
        if _has_offtarget:
            _already_swapped = getattr(_match, 'deploy_swapped', False) if _match is not None else False
            if not _already_swapped:
                log.info(f'[cw-deploy] deploy-swap(D-151 one-time):board off-target({_board} vs {_target_factions})'
                         f' → sell all deployed(清 starters)+ redeploy bench;之后不再 sell(让 comp 累积)')
                self._sell_all_deployed(front, back)
                if _match is not None:
                    _match.deploy_swapped = True   # one-time:只第一次 swap,之后 comp 累积不被卖
            else:
                log.info('[cw-deploy] deploy-swap 已做过(D-151 one-time),不再 sell(comp 累积中)')
        if templates:
            self._deploy_all_slots(bench, front, back, _dep_sift, templates)
        else:
            log.info('[cw-deploy] 无 avatar 模板 → naive 填位')
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
        # D-122 L2b:concentration deploy(deployed-lock 防 spread;替 D-121 target-only/全 deploy)。
        # deploy target 阵营 OR 集中阵营(bench+deployed faction count≥2);off-target 单张留 bench 可 sell。
        # 配 L1(cw_decisions 集中化 buy)+ L3(emergent target)。无 target 无集中(board 空)→ tempo seed
        # (deploy ≤2 最高 count)防空板全掉血;board 非空 + 无 target/集中 → 不 deploy(off-target 留 bench)。
        if target_factions or actual:
            def _is_target(bc) -> bool:
                if not target_factions:
                    return False
                ch = get_char(bc.char_id)
                if ch is None:
                    return False
                bonds = set(ch.factions) | set(ch.flows)
                if ch.independent:
                    bonds.add(ch.independent)
                return bool(bonds & target_factions)
            _fcount: dict[str, int] = {}
            for _bc in (*actual, *(_dep_sift or [])):
                _f = getattr(_bc, 'faction', '')
                if _f and _f != '?':
                    _fcount[_f] = _fcount.get(_f, 0) + 1

            def _conc(bc) -> int:
                return _fcount.get(getattr(bc, 'faction', ''), 0)
            # D-125:deploy ALL bench chars(concentration-first 排序:target/高count 先),填满 board 到 cap。
            # concentration-only 致 **front-empty 卡死**(2026-08-08 验「前台区域无角色 无法出战」—— 全 back-pref
            # 集中角色 → front 空 → 游戏拒出战 → stall)。fill 保证 valid board(front+back 都有)+ concentration
            # 优先(deepen target/集中)。accept 有限 spread-lock(deployed-lock 下 tempo 必要,off-target 沉没);
            # D-123 retry-stick 保证真上 board;配 L1 集中化 buy + concentration-first 排序尽量减 spread + 优先集中。
            _pool_n = sum(1 for bc in actual if _is_target(bc) or _conc(bc) >= 2)
            actual = sorted(actual, key=lambda bc: (0 if (_is_target(bc) or _conc(bc) >= 2) else 1,
                                                   -_conc(bc), bc.slot))
            log.info(f'[cw-deploy] fill(concentration-first):{_pool_n} 集中/target + {len(actual) - _pool_n} '
                     f'fill = {len(actual)} chars → 填板(D-123 retry-stick;front+back 都填)')

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
        consecutive_fail = 0   # D-141b:连续 deploy 无 stick 计数(board 满/拖坏 早停)
        # D-123 retry-until-stick:SIFT 占位检测(_dep_sift)对 stage 角色 false-negative(2026-08-08 确认:
        # occupied(SIFT) 显 2 但 board 实际 4)→ _find_empty_slot 选占槽 → 游戏拒拖 → 角色回 bench →
        # board 卡 spread。改:不靠 SIFT 选槽,改 **deploy→verify(bench count 降 = 角色真上 board)→
        # 没中试下槽**。manual 验空槽 drag 能 stick(群攻 1→2)。bench SIFT 可靠(检 bench 角色),作 verify。
        _bench_n = len(read_bench_chars(self.ctx, self.last_screenshot, templates)) if templates else 0
        for bc in actual:
            if cap_remaining is not None and dragged >= cap_remaining:
                break
            if bc.slot < 1 or bc.slot > len(bench):
                continue
            src = bench[bc.slot - 1]
            pref = bc.position_pref or 'back'
            slots_row, occupied_set = (front, occupied_front) if pref == 'front' else (back, occupied_back)
            stuck = False
            for try_idx in range(1, len(slots_row) + 1):
                if try_idx in occupied_set:
                    continue
                dst = slots_row[try_idx - 1]
                # D-118b:CW deploy = long-press drag(hold 0.5s → drag → release)。
                self.ctx.controller.drag_to(start=src, end=dst, duration=1.0, hold_time=0.5)
                time.sleep(0.7)
                # verify:re-read bench,count 降 = 角色真上 board(stick)。bench SIFT 可靠。
                _bench_now = read_bench_chars(self.ctx, self.screenshot(), templates) if templates else []
                if len(_bench_now) < _bench_n:
                    occupied_set.add(try_idx)
                    dragged += 1
                    _bench_n = len(_bench_now)
                    stuck = True
                    log.info(f'[cw-deploy] retry-stick:bench[{bc.slot}]({bc.char_id}/{pref}) → {pref}-{try_idx} '
                             f'✓ stick(bench {_bench_n + 1}→{_bench_n})')
                    # task#105 step④(D-130/D-131):deploy 同步 tracked_bench_chars→tracked_deployed。
                    # 按 bc.char_id 匹配(SIFT 识别);char_id='?'(未识别)无法匹配 → 漂移靠 board 校正(D-131)。
                    # 保留 buy 的正确 star(pop tracked_bench_chars 的,非 SIFT star=1)。待 step⑥(cw_observation
                    # seed state.deployed=tracked_deployed)才生效;现仅维护 session 持久态。
                    _sess = self.ctx.cw_match.session if self.ctx.cw_match is not None else None
                    if _sess is not None and bc.char_id and bc.char_id != '?':
                        _idx = next((i for i, c in enumerate(_sess.tracked_bench_chars)
                                     if c.char_id == bc.char_id), None)
                        if _idx is not None:
                            _up = _sess.tracked_bench_chars.pop(_idx)
                            _up.position_pref = pref
                            _sess.tracked_deployed.append(_up)
                            log.info(f'[cw-deploy] task#105 sync:{bc.char_id} bench→deployed({pref})')
                    break
                # 未中:slot 实占(SIFT 漏读)或拖失败 → 试下槽(角色仍在 src)
            if stuck:
                consecutive_fail = 0
            else:
                consecutive_fail += 1
                log.info(f'[cw-deploy] bench[{bc.slot}]({bc.char_id}) 未能 deploy(槽满/拖失败,留 bench)')
                # D-141b:board 已满(cap 估偏高 level / paddle 未读到)时全 bench 试拖都失败 → 每个浪费 ~10s。
                # dragged 仍 0(从无 stick)+ 连续 2 次失败 = board 真 full(有空槽 retry-stick 会中)→ 早停,省 ~70s
                # (9→2 次失败)。仅 dragged==0 触发:已开始 deploy 后不早停(留 cap_remaining 控,防 under-deploy)。
                if dragged == 0 and consecutive_fail >= 2:
                    log.info('[cw-deploy] 早停:dragged=0 + 连续2次无 stick → board 满,停止试拖(D-141b)')
                    break
        log.info(f'[cw-deploy] 拖完:retry-stick {dragged} 个(D-123;fill concentration-first D-125)')

    def _sell_all_deployed(self, front: list[Point], back: list[Point]) -> None:
        """D-151(用户确认 deployed 可卖):卖全部 deployed 角色。遍历 stage 槽(front 4 + back 6)
        drag→出售区(70,846)。用户建议 drag 时间设长(duration 1.5,非 0.8)—— deployed 角色需更长拖拽
        才能拾起+拖到出售区。occupied → 卖(gold+),empty → 无影响。"""
        _sell = Point(70, 846)
        for slot in front + back:
            self.ctx.controller.drag_to(start=slot, end=_sell, duration=1.5)   # D-151: 用户建议 longer time
            time.sleep(0.5)
        log.info(f'[cw-deploy] sell-all-deployed(D-151):拖 {len(front) + len(back)} 个 stage 槽 → 出售区')

    def _deploy_all_slots(self, bench: list[Point], front: list[Point], back: list[Point],
                          _dep_sift: list | None, templates: AvatarTemplates | None) -> None:
        """D-145(review-a0610):deploy 全部 bench 角色(slot-iteration + retry-stick),非 SIFT-gated。

        旧主路径用 SIFT read_bench_chars 选部署对象 → SIFT 只 4 角色可靠(D-75)→ target 单位识别不了
        → 永远不上 board → board[追击] 卡 1(D-140 真因)。改:遍历 bench 物理槽(1..9),drag 每个→board,
        retry-stick 验 bench-count 降(D-123:benc SIFT count 可靠)= 有角色 deployed;空槽/板满 不降→跳。
        deploy 全部 owned(target+off-target)→ target 上场→bond 激活。pref 无身份用 front 先填(次优,
        target 上场首要;pref 精确位型待 identity/slot 跟踪修后补)。终止:bench-count=0(全 deploy)或 free 槽尽。
        """
        occupied_front: set[int] = set()
        occupied_back: set[int] = set()
        if _dep_sift:
            for d in _dep_sift:
                (occupied_front if d.position_pref == 'front' else occupied_back).add(d.slot)
        _bench_n = len(read_bench_chars(self.ctx, self.last_screenshot, templates)) if templates else 0
        log.info(f'[cw-deploy] fill-all(D-145):bench_count={_bench_n} '
                 f'occupied(SIFT) front={sorted(occupied_front)} back={sorted(occupied_back)}')
        # D-149 deploy-use:comp 卡优先 deploy(char→slot from buy pixel-diff D-147)。本轮新 comp buys 的
        # bench 槽先 deploy(集中:有限 free 槽优先给 comp 卡,而非随机 bench)。map 只含本轮 buys → 只优先本轮新 comp。
        _match = self.ctx.cw_match
        _slot_map = getattr(_match, 'bench_slot_map', {}) if _match is not None else {}
        _tgt = (_match.session.target_comp.factions
                if (_match is not None and _match.session is not None
                    and _match.session.target_comp is not None) else None)
        _comp_idx: list[int] = []
        if _slot_map and _tgt:
            for _cn, _slot in _slot_map.items():
                _ch = get_char(_cn) if _cn else None
                if (_ch is not None and (set(_ch.factions) & set(_tgt))
                        and 1 <= _slot <= len(bench)):
                    _comp_idx.append(_slot - 1)   # slot 1-indexed → bench idx
        _iter_order = _comp_idx + [i for i in range(len(bench)) if i not in _comp_idx]
        if _comp_idx:
            log.info(f'[cw-deploy] comp-priority(D-149):本轮新 comp 卡槽 {_comp_idx} 先 deploy(集中)')
        dragged = 0
        consecutive_fail = 0   # 板满/空槽 早停(连续 bench 槽无 stick → 板满,停;省 ~2min 浪费)
        for i in _iter_order:  # comp 槽优先(D-149),余按 0..8
            if _bench_n <= 0:
                break  # bench 空(全 deployed 或开局无),无角色可 deploy
            # D-150(2026-08-09):移除 consecutive_fail 早停 —— bench 有 gaps(前轮 deploy 了 bench[0,1] 留空)
            # → 早停在空槽 → 错过 bench[2+] 角色 → board under-filled(< cap)→ 弱 → HP 崩(实测 retry-stick 0!)。
            # 遍历全 9 槽容忍 gaps;board full 时 inner-loop 无 free 槽 → fast fail(无 drag,~0.5s/slot,可接受)。
            src = bench[i]
            placed = False
            for row, occ in ((front, occupied_front), (back, occupied_back)):
                for try_idx in range(len(row)):
                    if try_idx in occ:
                        continue
                    dst = row[try_idx]
                    self.ctx.controller.drag_to(start=src, end=dst, duration=1.0, hold_time=0.5)
                    time.sleep(0.7)
                    _bench_now = read_bench_chars(self.ctx, self.screenshot(), templates) if templates else []
                    if len(_bench_now) < _bench_n:   # bench-count 降 = 角色真上 board(D-123 验)
                        occ.add(try_idx)
                        dragged += 1
                        _bench_n = len(_bench_now)
                        placed = True
                        log.info(f'[cw-deploy] fill-all:bench槽{i+1} → board ✓ stick(bench {_bench_n + 1}→{_bench_n})')
                        break
                if placed:
                    break
            if placed:
                consecutive_fail = 0
            else:
                # bench 槽 i 空(无角色)或板满(无 free 槽)→ consecutive_fail++(连续2→早停)
                consecutive_fail += 1
        log.info(f'[cw-deploy] fill-all 拖完(D-145):retry-stick {dragged} 个(全部 bench → board)')

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
