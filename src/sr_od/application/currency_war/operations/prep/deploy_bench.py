# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)
# ⚠️ 本文件**拖拽机制已验证**(2026-08-13:中心拖+hold0,推翻 ADR-0100;统一走 DragCwChar.drag_char);
# 其余部署逻辑(CV 占用 / SIFT 身份 / cap 门 / off-target 卖)仍待逐画面 review。

"""货币战争 部署 op(备战阶段:bench 角色 → 舞台空槽)。

**部署逻辑(``_deploy_deterministic``,活跃路径)**:CV ``slot_occupied`` 知 bench / 前排 / 后排占用 → 每个
有角色的备战槽按**角色前后台属性**(``Character.position_pref()``,cw_chars 注册表)拖到对应排的空槽(target
阵营先)→ 验「源备战槽空了」=成功。**角色拖拽统一走 ``DragCwChar.drag_char``**(中心拖 + hold_time=0,2026-08-13
实测推翻 ADR-0100;avatar 偏移 / 长按全是旧错诊)。off-target deployed 挡 target 上场时,先
``_sell_offtarget_deployed`` 卖 off-target 腾位(卖拖拽同样走 drag_char)。

**槽位坐标**:screen_info「货币战争-备战」(备战栏 9 / 前排 4 / 后排 N),经 ``_row_centers`` 读全部已建模
``{prefix}-N`` area。**后排 N 随财富宝钻(+1 团队规模)/ 诅咒·宝石剑泽尔里奇(−1)变化**,基准 6;>6 时
screen_info 需补 后排-7+ area(或运行时检测传入),``_row_centers`` 自动跟上(读全,不硬编码)。
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
from sr_od.application.currency_war.cw_observation import read_deploy_cap
from sr_od.application.currency_war.operations.dev.drag_cw_char import DragCwChar
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class DeployBench(SrOperation):
    """备战阶段:bench 角色 → 舞台空槽(CV 占用 + SIFT 身份 + position_pref 选排;拖拽走 DragCwChar.drag_char)。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-备战'
    STATUS_DEPLOYED: ClassVar[str] = '已部署角色'
    STATUS_NO_BENCH: ClassVar[str] = '备战栏无角色'
    STATUS_NO_SCREEN: ClassVar[str] = '未加载货币战争-备战 screen_info'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-部署角色')

    def _row_centers(self, prefix: str) -> list[Point]:
        """从 screen_info 读**全部** ``{prefix}-N`` 区域中心(按 N 升序)。

        数量 = screen_info 已建模数(不硬编码):前排 4 / 备战栏 9 / 后排 基准 6。
        **后排 >6**(财富宝钻 +1)时 screen_info 补 后排-7+ area 后本方法自动跟上(读全)。
        """
        si = self.ctx.screen_loader.get_screen(DeployBench.SCREEN_NAME)
        if si is None:
            return []
        pts: list[tuple[int, Point]] = []
        pfx = f'{prefix}-'
        for a in si.area_list:
            if a.area_name.startswith(pfx) and a.pc_rect is not None:
                try:
                    n = int(a.area_name[len(pfx):])
                except ValueError:
                    continue
                pts.append((n, a.pc_rect.center))
        pts.sort(key=lambda t: t[0])
        return [p for _, p in pts]

    @operation_node(name='部署备战栏角色', is_start_node=True)
    def deploy(self) -> OperationRoundResult:
        si = self.ctx.screen_loader.get_screen(DeployBench.SCREEN_NAME)
        if si is None:
            log.warning('[cw-deploy] 未加载「货币战争-备战」screen_info,跳过部署')
            return self.round_fail(status=DeployBench.STATUS_NO_SCREEN)

        bench = self._row_centers('备战栏')
        front = self._row_centers('前排')
        back = self._row_centers('后排')
        if len(bench) == 0:
            log.info('[cw-deploy] 备战栏无槽坐标,跳过')
            return self.round_success(DeployBench.STATUS_NO_BENCH)

        templates = self._get_templates()
        # deployed-lock(doc gameplay:78)是误判,deployed 可卖(用户实机确认 gold 增加)。
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
        self._deploy_deterministic(bench, front, back, templates)   # D-7:CV 确定性部署(CV 占用 + position_pref 选排)
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
            # live 2026-08-15(match4 deploy storm 根因):起始帧 slot_occupied 瞬时假阳(商店关闭/卖出
            # 动画残影 → 对空槽白烧 3×2s drag 重试)。每槽 drag 前 fresh 复查占用,空 → 跳过。
            if not slot_occupied(self.screenshot(), int(bench[bi].x), int(bench[bi].y)):
                log.info(f'[cw-deploy] deterministic: bench槽{bi+1} fresh 复查空(起始帧假阳/已上阵) → 跳过')
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
            _row_cn = '前' if chosen_pts is front else '后'
            # 5.1.9 重诊(2026-08-13 实测推翻 ADR-0100):整张卡可拖 —— 从**卡中心**拖 + 按下即移(hold_time=0)
            # 即拾取上阵(实测:中心 drag 飞霄 → 上阵 ✓)。avatar/左上星标/hold1s 全是旧错诊(详情=click 触发非
            # mouseDown;drag=按下+移动;左上小圆是星标非头像)。**拖拽统一走 ``DragCwChar.drag_char``**(中心拖
            # + hold0 + retry + 验源槽像素变),本处不再内联 drag_to。
            if DragCwChar.drag_char(self, src, dst):
                placed += 1
                # 5.1.7 补(2026-08-13):同轮 drag 成功 → 刚 deploy 的角色入去重集,
                # 防 bench 同角色 2 张时第 2 张重复 drag(场上已有该角色 → 上场失败)。
                if _cid:
                    _deployed_cids.add(_cid)
                if _match is not None and getattr(_match, 'bench_slot_map', None):
                    _gone = next((n for n, s in _match.bench_slot_map.items() if s == bi + 1), None)
                    if _gone is not None:
                        del _match.bench_slot_map[_gone]
                _fb = ' (fallback)' if (pref == 'front') != (_row_cn == '前') else ''
                log.info(f'[cw-deploy] deterministic: bench槽{bi+1}(pref={pref}) → {_row_cn}排{ti+1} ✓{_fb}'
                         f' (CV 验源槽变)')
            else:
                # live 2026-08-15(match4 根因):drag_char 的 before 帧取自 retry 循环外,成功验证可滞后;
                # 失败后 fresh 复查源槽 —— 已空 = 实际拖成(验证滞后)计 placed;仍占 = 真失败。
                time.sleep(0.3)
                if not slot_occupied(self.screenshot(), int(src.x), int(src.y)):
                    placed += 1
                    if _cid:
                        _deployed_cids.add(_cid)
                    log.info(f'[cw-deploy] deterministic: bench槽{bi+1} fresh 复查源槽已空 → 判拖成(验证滞后)')
                else:
                    log.info(f'[cw-deploy] deterministic: bench槽{bi+1}(pref={pref}) → {_row_cn}排{ti+1}'
                             f' 拖3次源槽未变,跳过(失败帧存证)')
                    import contextlib
                    with contextlib.suppress(Exception):
                        self.save_screenshot(prefix=f'deploy_fail_slot{bi + 1}')
                    chosen.insert(0, ti)   # 目标槽没占住,回收给下个角色
        if placed < len(order):
            log.warning(f'[cw!] [deploy] 上阵不全: placed={placed}/{len(order)}(失败帧已存证)')
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
            if DragCwChar.drag_char(self, src, _sell):
                sold += 1
                log.info(f'[cw-deploy] sell-offtarget:{d.char_id}({sorted(bonds)}) @'
                         f'{"前" if d.position_pref == "front" else "后"}排{d.slot} → 出售区 ✓ (源槽变)')
            else:
                log.info(f'[cw-deploy] sell-offtarget:{d.char_id} 拖3次源槽未变,跳过')
        if deployed:
            log.info(f'[cw-deploy] read_deployed_chars={[(d.char_id, d.position_pref, d.slot) for d in deployed]};'
                     f' sold {sold}/{max_sell} off-target (target_factions={sorted(target_factions)})')
        return sold

    def _reconcile_tracking(self, templates: AvatarTemplates | None) -> None:
        """D-12(3.3.2 · 观测回路):deploy 后用 SIFT 身份 + ``read_star`` 实机星级 重置 session.tracking。

        根因:deploy op 视觉拖拽不调 ``mutate_bench_deployed`` → tracking 滞留(已上场在 bench / 已卖在 deployed)
        → 下轮 buy 用漂移 tracking 错。本方法:deploy 后(SIFT 准)读真实 bench/deployed 身份重置 tracking。

        ⚠️ 2026-08-12:star 用 ``identify_slots`` 的 ``read_star`` 实机金星(非旧 tracking pool 保留)。旧逻辑「保留
        旧 star(SIFT star 恒1)」注释过期 —— read_star 已接(commit 672aa838,identify_slots L159 读实机金星)。
        用户:假设 star 识别对(read_star 实机 > simulate 推算;且 simulate _merge 只看 bench,3合1 是全场
        deployed+bench+买)。read_star 1星验过,2星逻辑同(数金星)。
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

        # identify_slots 已带 read_star 实机 star(real_*.bc.star);直接用,不再用旧 tracking star 覆盖
        # (用户 2026-08-12:假设 star 识别对 —— read_star 实机观测 > simulate 推算;且绕过 simulate _merge
        # 只看 bench 的局限 —— 3合1 是全场 deployed+bench+买)。read_star 1星验过(commit 672aa838),2星逻辑同。
        _match.session.tracked_bench_chars = list(real_bench)
        _match.session.tracked_deployed = list(real_deployed)
        log.info(f'[cw-deploy] tracking 纠漂后(D-12 post,star=read_star 实机):'
                 f'bench={[(bc.char_id, bc.star) for bc in real_bench]} '
                 f'deployed={[(bc.char_id, bc.star) for bc in real_deployed]}')
