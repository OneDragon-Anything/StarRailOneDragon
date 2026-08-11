# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 部署 op(接入 plan() 的 DeployMove,替代 v1 naive 填位)。

**策略驱动部署**(,2026-08-07):读 ``session.pending_deploys``(plan 算出的 DeployMove 列表),
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
from sr_od.application.currency_war.currency_war_cv import slot_occupied
from sr_od.application.currency_war.cw_chars import get_char
from sr_od.application.currency_war.cw_identity_obs import (
    read_bench_chars,
    read_deployed_chars,
)
from sr_od.application.currency_war.cw_observation import (
    read_deploy_cap,
    read_deployed_count,
)
from sr_od.application.currency_war.cw_state import BenchChar, DeployMove
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
        # _dep_sift 不再算(D-5 后占用走 CV slot_occupied;_deploy_all_slots 活跃路径不用 _dep_sift。
        # _deploy_by_identity/_strategic 是死代码)。省一次 SIFT read_deployed_chars(提速)。
        _dep_sift = None
        # 改:遍历 bench 物理槽 drag→board,retry-stick 验 bench-count 降(有角色 deployed;空槽/板满 不降→跳/停),
        # deploy 全部 owned(target+off-target)→ target 上场→bond 激活。pref 无身份用 front 先填(次优,target 上场首要)。
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
        if _has_offtarget and templates is not None and _target_factions:
            # D-10:卖 off-target deployed 给 bench target 腾位(替一次性 sell-all)。死锁根因:bot 买到 target
            # 单位但板满(cap)+ off-target 卖不掉(旧 deploy_swapped 一次性冻结)→ bench target 上不了场 →
            # 板冻结 off-target → 慢失血。修:bench 有 target 单位时,卖 deployed 中的 off-target(留 target),
            # 腾位给 bench target(_deploy_deterministic 填)。自收敛(板全 target → _has_offtarget=False 停)。
            # 守卫(D-3):bench 有 target 才卖(有更好的要换上);无 target 留 off-target bodies(> 空板)。
            _bench_chars = read_bench_chars(self.ctx, self.last_screenshot, templates)

            def _is_tgt_char(name: str) -> bool:
                _c = get_char(name) if name else None
                return _c is not None and bool((set(_c.factions) | set(_c.flows)) & _target_factions)

            _bench_tgt_n = sum(1 for _bc in _bench_chars if _is_tgt_char(_bc.char_id))
            if _bench_tgt_n > 0:
                _n = self._sell_offtarget_deployed(front, back, _target_factions, templates,
                                                   max_sell=_bench_tgt_n)
                log.info(f'[cw-deploy] deploy-swap:sell {_n} off-target deployed(留 target,1:1 替换上限={_bench_tgt_n})'
                         f' 腾位; bench target={_bench_tgt_n}/{len(_bench_chars)} → redeploy 集中')
            else:
                log.info('[cw-deploy] deploy-swap 跳过:bench 无 target 单位(留 off-target bodies;'
                         ' 根因=buy 未买 target / economy 未攒金升级)')
        self._deploy_deterministic(bench, front, back, templates)   # D-7:CV 确定性部署(替 trial-and-error _deploy_all_slots)
        self._reconcile_tracking(templates)   # D-12(3.3.2):deploy 后 SIFT 真实身份纠 tracking 漂(观测回路)

        time.sleep(0.5)
        log.info('[cw-deploy] 拖完')

        return self.round_success(DeployBench.STATUS_DEPLOYED, wait=1)

    def _deploy_deterministic(self, bench: list[Point], front: list[Point], back: list[Point],
                              templates: AvatarTemplates | None) -> None:
        """D-7 确定性部署:CV 知占用 → 每个有角色的备战槽按**角色前后台属性**(position_pref)拖到对应排的
        空槽(target 阵营先)→ CV 验「源备战槽空了」=成功。

        **5.1.6(2026-08-12,live 观察 2)**:按 ``Character.position_pref()``(cw_chars 注册表)选排 ——
        前台角色→前排空槽、后台/flex 角色→后排空槽;对应排满才 fallback 另一排(避免不上场)。
        替旧「targets 一锅 pop(0) 前排优先」(不看角色属性 → 前台角色被拖后排 / 后台角色被拖前排 → 放错排
        无效果)。flex 默认 back(``position_pref`` 语义,后排槽多)。

        D-8 接身份:排序(target 先)+ position_pref(选排)都用 SIFT ``read_bench_chars`` 读 bench 身份 →
        ``get_char`` 查注册表。SIFT 未命中的 bench 角色 → 当 rest(pref 默认 back,照常 deploy,只不优先)。
        D-10:fresh screenshot(``self.screenshot()``)看 post-sell 状态(_sell_offtarget_deployed 腾出的空槽)。
        CV 验源槽空同时覆盖 place + swap(swap 时被换下角色回 bench,源槽仍空)。
        """
        scr = self.screenshot()
        bench_occ = [i for i, c in enumerate(bench) if slot_occupied(scr, int(c.x), int(c.y))]
        front_empty = [i for i, c in enumerate(front) if not slot_occupied(scr, int(c.x), int(c.y))]
        back_empty = [i for i, c in enumerate(back) if not slot_occupied(scr, int(c.x), int(c.y))]
        if not bench_occ or (not front_empty and not back_empty):
            log.info(f'[cw-deploy] deterministic: bench_occ={bench_occ} front空={len(front_empty)} back空={len(back_empty)}'
                     f' → {"无 bench 角色" if not bench_occ else "板满无空槽(swap 待身份)"}')
            return
        _match = self.ctx.cw_match
        _sess = (_match.session if (_match is not None and _match.session is not None) else None)
        _tgt = (set(_sess.target_comp.factions)
                if (_sess is not None and _sess.target_comp is not None) else set())
        # 5.1.8 deploy_cap(live 发现 drag 白拖根因 = cap 满,2026-08-12):deployed(CV front_occ+back_occ 实测阵上)
        # ≥ level(cap,D-19「cap=level」)→ 板满,bench 角色上不了 → 不拖(留 bench;防 drag 被拒源槽占 placed=0 白拖
        # + 用户 live 观察 bug4「未考虑上限」)。CV 实测 deployed 优于 state.deployed_count(board 重建可能虚高)。
        # cap 真值优先 read_deploy_cap(OCR X/Y 的 Y,含宝钻/诅咒加成);读不到 fallback level(D-19 cap≈level)。
        # ⚠️ level≠cap 场景(诅咒-1 / 宝钻+1):用 level 会误判 cap 未满 → 白拖(D-53 注 level=cap 无加成,但加成时偏)。
        _cap = read_deploy_cap(self.ctx, scr)
        if _cap is None:
            _cap = (_sess.last_state.level if (_sess is not None and _sess.last_state is not None) else None)
        if _cap is not None and _cap > 0:
            _deployed = (len(front) - len(front_empty)) + (len(back) - len(back_empty))
            if _deployed >= _cap:
                log.info(f'[cw-deploy] 板满 cap:deployed={_deployed} ≥ cap={_cap}(level,5.1.8)'
                         f' front空={len(front_empty)} back空={len(back_empty)} → bench 角色留 bench(不白拖)')
                return
        # D-8:bench 身份走 SIFT(read_bench_chars,71 CW 立绘库可靠)→ 真实羁绊(target 排序)+ position_pref
        # (5.1.6 选排)。两者都从 get_char 注册表查(SIFT 只给 char_id,BenchChar.position_pref 默认 "back"
        # 不可信 → 必查注册表)。无 target 也要读身份(选排需要),不再 _tgt gate。
        _bench_id: dict[int, set[str]] = {}   # bench_idx(0-based) → 该角色羁绊集合
        _bench_pos: dict[int, str] = {}       # bench_idx(0-based) → "front"/"back"(角色 position_pref)
        _bench_cid: dict[int, str] = {}       # bench_idx(0-based) → char_id(5.1.7 去重)
        if templates is not None:
            for bc in read_bench_chars(self.ctx, scr, templates):
                ch = get_char(bc.char_id) if bc.char_id else None
                if ch is not None and 1 <= bc.slot <= len(bench):
                    _bench_id[bc.slot - 1] = set(ch.factions) | set(ch.flows)
                    _bench_pos[bc.slot - 1] = ch.position_pref()
                    _bench_cid[bc.slot - 1] = bc.char_id
            log.info(f'[cw-deploy] bench 身份(SIFT):{ {i: sorted(b) for i, b in _bench_id.items()} }'
                     f' pos={_bench_pos} tgt={sorted(_tgt)}')
        # 5.1.7 同角色去重(live 观察 3,场上同角色只 1):read_deployed_chars → deployed char_id;
        # bench 角色已 deployed → deploy 循环跳过(避免场上重复角色 + 买/部署同名)。
        _deployed_cids: set[str] = set()
        if templates is not None:
            _deployed_cids = {bc.char_id for bc in read_deployed_chars(self.ctx, scr, templates) if bc.char_id}
            if _deployed_cids:
                log.info(f'[cw-deploy] deployed 身份(5.1.7 去重):{sorted(_deployed_cids)}')
        tgt_idx, rest = [], []
        for i in bench_occ:
            _bonds = _bench_id.get(i)
            _is_tgt = bool(_bonds and _bonds & _tgt) if _tgt else False
            (tgt_idx if _is_tgt else rest).append(i)
        order = tgt_idx + rest
        log.info(f'[cw-deploy] deterministic: bench_occ={bench_occ} target先={tgt_idx}'
                 f' front空={len(front_empty)} back空={len(back_empty)}')
        placed = 0
        for bi in order:
            # 5.1.7 同角色去重(live 观察 3,场上同角色只 1):bench 角色已 deployed → 跳过(避免重复)。
            _cid = _bench_cid.get(bi)
            if _cid and _cid in _deployed_cids:
                log.info(f'[cw-deploy] 去重(5.1.7):bench槽{bi+1}({_cid}) 已 deployed,跳过')
                continue
            # 5.1.6:按角色 position_pref 选排(前台→前排、后台/flex→后排);对应排满 fallback 另一排(避免不上场)。
            pref = _bench_pos.get(bi, 'back')   # SIFT 漏读身份 → 默认 back(后排槽多 6 > 前排 4,安全)
            # 前排保证(出战要求,5.1.6 补):pref=back 但前排完全空(无角色)→ 强制前排(back 放前排不
            # 触发赋能,但出战硬要求前排有角色;优于前排空出战拒卡局)。第一个 back 填前排,后续正常后排。
            if pref == 'back' and len(front_empty) == len(front):
                pref = 'front'
                log.info(f'[cw-deploy] 前排保证:bench槽{bi+1}(pref=back)→ 强制前排(前排空,出战要求)')
            if pref == 'front':
                chosen, chosen_pts, fallback, fallback_pts = front_empty, front, back_empty, back
            else:
                chosen, chosen_pts, fallback, fallback_pts = back_empty, back, front_empty, front
            if not chosen:
                if not fallback:
                    break   # 两排皆满,无槽可拖
                chosen, chosen_pts = fallback, fallback_pts
            ti = chosen.pop(0)
            dst = chosen_pts[ti]
            src = bench[bi]
            # 5.1.9(2026-08-12 米游社官方+VLM 诊断):deploy = 拖拽角色**头像 avatar**(角色卡左上角小圆,非立绘/名字)。
            # mouseDown 立绘(中心 y912 / 上部 y882)→ 游戏不拾取(判 click 开详情);mouseDown avatar 左上角才拾取。
            # D-118b drag 未 live 验(commit 明记)→ placed=0 长期未发现。avatar = 角色卡左上(center 偏 -40,-50)。
            # slot_occupied 验源槽仍用中心(src);click bench 开详情(D-118b/本轮验)确认 click 非 pickup。
            _src_drag = Point(int(src.x) - 40, int(src.y) - 50)
            _landed = False
            _row_cn = '前' if chosen_pts is front else '后'
            for _attempt in range(3):
                # bug#1 mitigation(对齐 equip_all 2f521915)+ 5.1.9 mouseDown 立绘上部(_src_drag)。
                self.ctx.controller.mouse_move(_src_drag)
                time.sleep(0.2)
                self.ctx.controller.drag_to(start=_src_drag, end=dst, duration=1.0, hold_time=1.0)
                time.sleep(0.7)
                if not slot_occupied(self.screenshot(), int(src.x), int(src.y)):
                    placed += 1
                    _landed = True
                    if _match is not None and getattr(_match, 'bench_slot_map', None):
                        _gone = next((n for n, s in _match.bench_slot_map.items() if s == bi + 1), None)
                        if _gone is not None:
                            del _match.bench_slot_map[_gone]
                    _fb = ' (fallback)' if (pref == 'front') != (_row_cn == '前') else ''
                    log.info(f'[cw-deploy] deterministic: bench槽{bi+1}(pref={pref}) → {_row_cn}排{ti+1} ✓{_fb}'
                             f' (CV 验源槽空)')
                    break
            if not _landed:
                log.info(f'[cw-deploy] deterministic: bench槽{bi+1}(pref={pref}) → {_row_cn}排{ti+1}'
                         f' 拖3次源槽未空(bug#1 间歇 / avatar 偏移;5.1.9 avatar 根因对 placed=3/5),跳过')
                chosen.insert(0, ti)   # 目标槽没占住,回收给下个角色
        log.info(f'[cw-deploy] deterministic 完成: placed={placed}/{len(order)}')

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
        """按**实际识别**的 bench 角色身份 deploy(替代 tracked_bench idx)。

        target_factions 非空 → target-first sorted deploy。
        d:cap_remaining 限 deploy 数。
        f:SIFT deployed count 替 OCR。
        SIFT slot-level occupied detection(_find_empty_slot)。
        bug#1 缓解(mouse_move 先)+ 长 duration + SIFT 验 + retry(3 次)。
        """
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
            # concentration-only 致 **front-empty 卡死**(2026-08-08 验「前台区域无角色 无法出战」—— 全 back-pref
            # 集中角色 → front 空 → 游戏拒出战 → stall)。fill 保证 valid board(front+back 都有)+ concentration
            # 优先(deepen target/集中)。accept 有限 spread-lock(deployed-lock 下 tempo 必要,off-target 沉没);
            _pool_n = sum(1 for bc in actual if _is_target(bc) or _conc(bc) >= 2)
            actual = sorted(actual, key=lambda bc: (0 if (_is_target(bc) or _conc(bc) >= 2) else 1,
                                                   -_conc(bc), bc.slot))
            log.info(f'[cw-deploy] fill(concentration-first):{_pool_n} 集中/target + {len(actual) - _pool_n} '
                     f'fill = {len(actual)} chars → 填板(retry-stick;front+back 都填)')

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
        consecutive_fail = 0
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
                # dragged 仍 0(从无 stick)+ 连续 2 次失败 = board 真 full(有空槽 retry-stick 会中)→ 早停,省 ~70s
                # (9→2 次失败)。仅 dragged==0 触发:已开始 deploy 后不早停(留 cap_remaining 控,防 under-deploy)。
                if dragged == 0 and consecutive_fail >= 2:
                    log.info('[cw-deploy] 早停:dragged=0 + 连续2次无 stick → board 满,停止试拖(b)')
                    break
        log.info(f'[cw-deploy] 拖完:retry-stick {dragged} 个(;fill concentration-first )')

    def _sell_offtarget_deployed(self, front: list[Point], back: list[Point],
                                 target_factions: set[str], templates: AvatarTemplates | None,
                                 max_sell: int = 99) -> int:
        """D-10:卖 deployed 中的 **off-target** 单位(留 target),给 bench target 腾位。

        SIFT ``read_deployed_chars`` 识别 deployed 身份 → off-target(羁绊 ∌ target)拖出售区。
        target 单位保留(替旧 sell-all 毁掉板上 target)。卖数 ≤ ``max_sell``(**1:1 替换上限** = bench
        target 数,保证每个卖出被一个 target 补上,板大小稳定;防 bench target 少却卖光 off-target → 板缩 HP 崩)。
        ⚠️ ``read_deployed_chars`` 首用(deployed SIFT 身份未单验,D-4 验的是占用);日志详记识别结果供核实,
        首跑即验证 —— 若身份错(误卖 target / 漏卖 off-target)据日志回退。
        """
        deployed = read_deployed_chars(self.ctx, self.last_screenshot, templates) if templates else []
        _sell = Point(70, 846)
        sold = 0
        for d in deployed:
            if sold >= max_sell:
                break
            ch = get_char(d.char_id) if d.char_id else None
            if ch is None:
                continue
            bonds = set(ch.factions) | set(ch.flows)
            if bonds & target_factions:
                continue   # target 单位,保留
            row = front if d.position_pref == 'front' else back
            if not (1 <= d.slot <= len(row)):
                continue
            src = row[d.slot - 1]
            self.ctx.controller.drag_to(start=src, end=_sell, duration=1.5)
            time.sleep(0.5)
            sold += 1
            log.info(f'[cw-deploy] sell-offtarget:{d.char_id}({sorted(bonds)}) @'
                     f'{"前" if d.position_pref == "front" else "后"}排{d.slot} → 出售区')
        if deployed:
            log.info(f'[cw-deploy] read_deployed_chars={[(d.char_id, d.position_pref, d.slot) for d in deployed]};'
                     f' sold {sold}/{max_sell} off-target (target_factions={sorted(target_factions)})')
        return sold

    def _reconcile_tracking(self, templates: AvatarTemplates | None) -> None:
        """D-12(3.3.2 · 观测回路):deploy 后用 SIFT 真实 bench/deployed 身份重置 session.tracking。

        根因:deploy op 视觉拖拽(D-7/D-8/D-10)不调 ``mutate_bench_deployed`` → session.tracked_bench_chars /
        tracked_deployed 滞留(还显示已上场的在 bench、已卖的在 deployed)→ 下轮 buy 用漂移 tracking 做集中度
        判断 → 错。本方法:deploy 完成(shop 关、bench/deployed 全可见、SIFT 准)后,读真实身份重置 tracking,
        **保留旧 tracking 的 star**(SIFT star 恒 1)。完成观测回路 → 解锁核心锁 ②。

        ⚠️ review 修(2026-08-09):① **pre-log**(纠漂前 log 旧 tracking)直证漂移被纠正(否则只 post 看不出纠没纠);
        ② **star 多副本**(用 multiset per char_id,非 dict)—— 重复 char_id(如两艾丝妲,一已升星)dict 塌缩 → star 错。
        """
        if templates is None:
            return
        _match = self.ctx.cw_match
        if _match is None or _match.session is None:
            return
        _old_bench = _match.session.tracked_bench_chars
        _old_dep = _match.session.tracked_deployed
        scr = self.screenshot()   # fresh post-deploy
        real_bench = read_bench_chars(self.ctx, scr, templates)
        real_deployed = read_deployed_chars(self.ctx, scr, templates)
        # pre-log:纠漂前旧 tracking char_id(直证漂移:旧 vs 真实不一致 = 漂了被纠正)
        log.info(f'[cw-deploy] tracking 纠漂前(D-12 pre):bench={[bc.char_id for bc in _old_bench]} '
                 f'deployed={[bc.char_id for bc in _old_dep]}')

        def _star_pool(old: list[BenchChar]) -> dict[str, list[int]]:
            pool: dict[str, list[int]] = {}
            for bc in old:
                pool.setdefault(bc.char_id, []).append(bc.star)
            return pool

        _bp, _dp = _star_pool(_old_bench), _star_pool(_old_dep)

        def _keep(bc: BenchChar, pool: dict[str, list[int]]) -> BenchChar:
            stars = pool.get(bc.char_id)
            star = stars.pop(0) if stars else bc.star   # multiset:重复 char_id 按序取 star,不塌缩
            return BenchChar(slot=bc.slot, char_id=bc.char_id, faction=bc.faction,
                             star=star, position_pref=bc.position_pref)

        _new_bench = [_keep(bc, _bp) for bc in real_bench]
        _new_dep = [_keep(bc, _dp) for bc in real_deployed]
        _match.session.tracked_bench_chars = _new_bench
        _match.session.tracked_deployed = _new_dep
        log.info(f'[cw-deploy] tracking 纠漂后(D-12 post):bench={[(bc.char_id, bc.star) for bc in _new_bench]} '
                 f'deployed={[(bc.char_id, bc.star) for bc in _new_dep]}')

    def _deploy_all_slots(self, bench: list[Point], front: list[Point], back: list[Point],
                          _dep_sift: list | None, templates: AvatarTemplates | None) -> None:
        """(review-a0610):deploy 全部 bench 角色(slot-iteration + retry-stick),非 SIFT-gated。

        旧主路径用 SIFT read_bench_chars 选部署对象 → SIFT 只 4 角色可靠()→ target 单位识别不了
        → 永远不上 board → board[追击] 卡 1(真因)。改:遍历 bench 物理槽(1..9),drag 每个→board,
        retry-stick 验 bench-count 降(benc SIFT count 可靠)= 有角色 deployed;空槽/板满 不降→跳。
        deploy 全部 owned(target+off-target)→ target 上场→bond 激活。pref 无身份用 front 先填(次优,
        target 上场首要;pref 精确位型待 identity/slot 跟踪修后补)。终止:bench-count=0(全 deploy)或 free 槽尽。
        """
        # 占用走 CV slot_occupied(灰度 std:空 placeholder ~11 vs 立绘 ~39+,阈值 25 干净分离)。
        # 替 SIFT(D-4:SIFT 误判空 front 占用 → 跳前排 → 前排空 → 出战阻塞)。CV 不依赖角色身份/颜色,稳。
        _scr = self.last_screenshot
        occupied_front: set[int] = {i for i, c in enumerate(front) if slot_occupied(_scr, int(c.x), int(c.y))}
        occupied_back: set[int] = {i for i, c in enumerate(back) if slot_occupied(_scr, int(c.x), int(c.y))}
        _bench_n = len(read_bench_chars(self.ctx, self.last_screenshot, templates)) if templates else 0
        log.info(f'[cw-deploy] fill-all():bench_count={_bench_n} occupied(CV) '
                 f'front={sorted(occupied_front)} back={sorted(occupied_back)}')
        # 集中阵营**(board+bench count>=2)的 bench 角色 —— 复刻 cw_decisions._should_deploy 语义,但在物理槽层
        # (用 bench_slot_map name→物理 slot,**绕开 logical bench_idx→物理映射墙**;map 即物理 slot,无需转换)。
        _match = self.ctx.cw_match
        _slot_map = getattr(_match, 'bench_slot_map', {}) if _match is not None else {}
        _sess = (_match.session if (_match is not None and _match.session is not None) else None)
        _tgt_factions: set[str] = (set(_sess.target_comp.factions)
                                   if (_sess is not None and _sess.target_comp is not None) else set())
        _board = (_sess.last_state.board if (_sess is not None and _sess.last_state is not None) else {})
        # 各羁绊计数(board deployed + bench_slot_map 角色)= concentration 判据。
        # ⚠️ 羁绊 = 阵营(factions) ∪ 流派(flows)统一命名空间(comp.factions 也混两者,见 D-2);
        # 只算 factions 会漏流派羁绊(椒丘 flows=持续伤害/减益 / 大丽花 flows=击破)→ 永不 match → fill-all。
        _fcount: dict[str, int] = dict(_board)
        for _cn in _slot_map:
            _ch = get_char(_cn) if _cn else None
            if _ch is not None:
                for _f in tuple(_ch.factions) + tuple(_ch.flows):
                    _fcount[_f] = _fcount.get(_f, 0) + 1
        _deploy_idx: list[int] = []
        for _cn, _slot in _slot_map.items():
            if not (1 <= _slot <= len(bench)):
                continue
            _ch = get_char(_cn) if _cn else None
            if _ch is None or not _ch.factions:
                continue
            _factions = set(_ch.factions) | set(_ch.flows)   # 羁绊 = 阵营 ∪ 流派(D-2:comp.factions 混两者)
            _is_target = bool(_factions & _tgt_factions) if _tgt_factions else False
            _is_conc = any(_fcount.get(_f, 0) >= 2 for _f in _factions)
            if _is_target or _is_conc:
                _deploy_idx.append(_slot - 1)
        # 诊断(D-1):为何 fill-all —— 记 bench 身份 / 目标阵营 / 每角色匹配
        _per: dict[tuple[str, int], tuple] = {}
        for _cn, _slot in _slot_map.items():
            _c = get_char(_cn) if _cn else None
            _fs = (_c.factions if (_c is not None and _c.factions) else [])
            _per[(_cn, _slot)] = (_fs, bool(set(_fs) & _tgt_factions))
        log.info(f'[cw-deploy] 集中度诊断:slot_map={dict(_slot_map)} tgt_factions={sorted(_tgt_factions)} '
                 f'fcount={_fcount} per_char_match={_per} deploy_idx={sorted(set(_deploy_idx))}')   # slot 1-indexed → bench idx
        # → 每轮输(baseline fill-all 满 5 unit 存活到 r6)。修:**target-priority + fill** —— target 槽先 deploy
        # (集中优先),再用 off-target 填满(满板存活;bodies 早期 > concentration 晚期;target 够多时自然集中)。
        _tgt_set = set(_deploy_idx)
        _iter_order = sorted(_tgt_set) + [i for i in range(len(bench)) if i not in _tgt_set]
        if _deploy_idx:
            log.info(f'[cw-deploy] target-priority+fill():target 槽 {sorted(_tgt_set)} 先,余 off-target 填满'
                     f'(target_factions={sorted(_tgt_factions)});满板存活 + target 优先集中')
        else:
            log.info(f'[cw-deploy] fill-all():无 target/集中 → 全 {len(bench)} 槽填满')
        dragged = 0
        consecutive_fail = 0   # 板满/空槽 早停(连续 bench 槽无 stick → 板满,停;省 ~2min 浪费)
        for i in _iter_order:
            if _bench_n <= 0:
                break  # bench 空(全 deployed 或开局无),无角色可 deploy
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
                    if len(_bench_now) < _bench_n:
                        occ.add(try_idx)
                        dragged += 1
                        _bench_n = len(_bench_now)
                        placed = True
                        if _match is not None and getattr(_match, 'bench_slot_map', None):
                            _gone = next((n for n, s in _match.bench_slot_map.items() if s == i + 1), None)
                            if _gone is not None:
                                del _match.bench_slot_map[_gone]
                        log.info(f'[cw-deploy] deploy:bench槽{i+1} → board ✓ stick(bench {_bench_n + 1}→{_bench_n})')
                        break
                if placed:
                    break
            if placed:
                consecutive_fail = 0
            else:
                # bench 槽 i 空(无角色)或板满(无 free 槽)→ consecutive_fail++(连续2→早停)
                consecutive_fail += 1
        log.info(f'[cw-deploy] fill-all 拖完():retry-stick {dragged} 个(全部 bench → board)')

    def _deploy_strategic(self, moves: list[DeployMove], bench: list[Point],
                          front: list[Point], back: list[Point]) -> None:
        """策略驱动:按 DeployMove(bench_idx, to_row) 拖到对应排的空槽。"""
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
