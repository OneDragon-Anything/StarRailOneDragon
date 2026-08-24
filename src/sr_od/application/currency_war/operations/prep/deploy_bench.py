# ⚠️ 本文件**拖拽机制已验证**(2026-08-13:中心拖+hold0,推翻 avatar 假设(原 ADR-0100,文件已删,见 ADR-0120);统一走 DragCwChar.drag_char);
# 其余部署逻辑(CV 占用 / SIFT 身份 / cap 门 / off-target 卖)仍待逐画面 review。

"""货币战争 部署 op(备战阶段:bench 角色 → 舞台空槽)。

**部署逻辑(``_deploy_deterministic``,活跃路径)**:CV ``slot_occupied`` 知 bench / 前排 / 后排占用 → 每个
有角色的备战槽按**角色前后台属性**(``Character.position_pref()``,cw_chars 注册表)拖到对应排的空槽(target
阵营先)→ 验「源备战槽空了」=成功。**角色拖拽统一走 ``DragCwChar.drag_char``**(中心拖 + hold_time=0,2026-08-13
实测推翻 avatar 假设(原 ADR-0100,文件已删,见 ADR-0120);avatar 偏移 / 长按全是旧错诊)。off-target deployed 挡 target 上场时,先
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
from sr_od.application.currency_war.cw_line_defs import (
    ENGINE_FACTIONS as _ENGINE_FENCE,
)
from sr_od.application.currency_war.cw_line_defs import (
    RECIPE_BASE as _RECIPE_BASE,
)
from sr_od.application.currency_war.cw_line_defs import (
    RECIPE_FACTIONS as _RECIPE,
)
from sr_od.application.currency_war.cw_observation import read_deploy_cap
from sr_od.application.currency_war.operations.dev.drag_cw_char import DragCwChar
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# r263b 过渡配方纪律 → r271 收口 cw_line_defs 单一源(此前模块级
# frozenset 与 line_strategy 的局部 set 双源;两份审查共同点名)。
# 语义:配方基础(_RECIPE_BASE 档)未满时,off-recipe 阵营 pair
# 不上板(防散件稀释配方;局15 r6-r8 实证)。
# r357(局44 判读,r353 集成缺口):围栏集 = RECIPE ∪ ENGINE
# (桥派生)——r353 把狼狩/贝洛伯格入桥后,买来的 hunt3 件被
# 旧四阵营围栏按「非配方」摁 bench(局44 r2 板 2/5 空槽+
# bench 7 实证:四飞霄全 bench)。V4.0 过渡配方含 3狼狩系,
# 围栏必须随桥派生集走(单一源)。
_DEPLOY_FENCE: frozenset[str] = frozenset(_RECIPE | _ENGINE_FENCE)


def _cap_roomy_of(front_empty: int, back_empty: int, must_up: int) -> bool:
    """r387:空位 > 必上件数(target+成对)→ cap 富余——配方围栏放行散牌填空。

    配方纪律(r263b)防的是「散件挤占 target 槽位」(cap 竞争),不是「填空」:
    cap 富余时散牌填空不稀释任何人(配方件来了仍有位);紧张(空位 ≤ 必上)→
    围栏照旧。局62 r2 实锤根因:deploy_cap=3 只上 1 人(三月七成对),bench 躺
    5 张(艾丝妲/阿格莱雅/缇宝/万敌全被判「不成对/非 target」留 bench)——两条
    纪律真冲突,r263b 无条件拦截压过 M18 填位。用户 live 口径「随便上填空位
    也可以」。锁测试:test_cw_r387_deploy_fill_vacancy(3 条)。
    """
    return front_empty + back_empty > must_up


def _tier_completes(bonds: 'frozenset[str] | set[str] | tuple[str, ...]',
                    deployed_fac: dict[str, int]) -> int:
    """r361 补档键:该角色上阵后任一阵营计数**恰达激活档** → 1,否则 0。

    纯函数(模块级可测):``bonds`` = 角色全部羁绊 tag 集合
    (factions+flows,同 _bench_id 口径;review B-1 已把生产
    _deployed_fac 统一为全羁绊口径);``deployed_fac`` = 当前
    板面阵营计数;档表单一源 FACTIONS.tiers。
    """
    from sr_od.application.currency_war.cw_factions import FACTIONS
    for _f in bonds:
        _now = (deployed_fac.get(_f, 0) or 0) + 1
        if _now in (FACTIONS.get(_f).tiers if FACTIONS.get(_f) else ()):
            return 1
    return 0


def _deployment_order(tgt_idx: list[int], rest: list[int],
                      bench_id: dict[int, set[str]],
                      bench_fac: dict[int, str],
                      deployed_fac: dict[str, int]) -> list[int]:
    """r404-A1/ADR-0258 点火排序(ADR-0261 裁决选项1;模块级可测,锁测试直调)。

    与 cw_deploy_logic.select_deployments 的排序**同语义**(单一源
    `ignition_gain`,import 不复制):
    - tgt 序:点火增量首键(-ignition_gain)+ r361 补档键次键
      (旧版纯 tier_completes,无点火键);
    - rest 序:点火增量首键 + r251 引擎身份键次键(降为次键——
      探针实证 vacancy=1 时冗余第4仙舟曾挤掉点火列车2);
    - 桶序修正:点火 rest 件先于 ignition=0 的 tgt 件(纯函数侧
      探针④:冗余 tgt 件压点火 rest 件)。

    输入口径与 _deploy_deterministic 内部字典一致:``bench_id`` =
    bench_idx(0-based) → 全羁绊集;``bench_fac`` = bench_idx → 主阵营;
    ``deployed_fac`` = 起始板面阵营计数(全羁绊口径,静态——排序只做
    一次,与纯函数一致;r288 门的动态仲裁在 drag 循环内另行维护)。
    """
    from sr_od.application.currency_war.cw_deploy_logic import (
        ignition_gain as _ign,
    )
    _ENGINE = {'仙舟', '列车同行', '持续伤害'}
    tgt_sorted = sorted(tgt_idx, key=lambda i: (
        -_ign(bench_id.get(i) or (), deployed_fac),
        -_tier_completes(bench_id.get(i) or (), deployed_fac)))
    rest_sorted = sorted(rest, key=lambda i: (
        -_ign(bench_id.get(i) or (), deployed_fac),
        0 if (bench_fac.get(i) in _ENGINE
              or (bench_id.get(i, set()) & _ENGINE)) else 1))
    ignite_rest = [i for i in rest_sorted
                   if _ign(bench_id.get(i) or (), deployed_fac) > 0]
    plain_rest = [i for i in rest_sorted if i not in ignite_rest]
    return ignite_rest + tgt_sorted + plain_rest


def exclude_system_units(chars: list) -> list:
    """剔除系统单位(ADR-0281 件4):cost==0 的 roster 特殊召唤单位(狸小虎/狸小龙/
    佩佩类)恒最右、**不可拖** —— 重排/换排/卖出等一切拖拽候选一律剔除(拖必失败,
    游戏拒 → 3 次重试白烧;选中态光效还可能假成功)。char_id 未知/不在 roster → 保留
    (未知单位保持旧行为,由识别侧钩子管)。"""
    out = []
    for d in chars:
        ch = get_char(d.char_id) if getattr(d, 'char_id', '') else None
        if ch is not None and ch.cost == 0:
            continue
        out.append(d)
    return out


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

        数量 = screen_info 已建模数(不硬编码):前排 4 / 备战栏 9 / 后排按
        ``_back_row_centers_by_level`` 选档(6/8 格两档,ADR-0281;**别假设
        「后排-」只有 6 个**——档前缀由调用方传入)。
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

    def _session_level(self) -> int | None:
        """session 等级链(``last_level_obs`` 单调链 vs ``last_state.level`` 取大)→ None(无 session)。

        布局选档的 level 源(ADR-0281:后排槽数 level 驱动,cap 与布局无关)。
        """
        _m = self.ctx.cw_match
        if _m is None or _m.session is None:
            return None
        lv = getattr(_m.session, 'last_level_obs', 0) or 0
        st = _m.session.last_state
        if st is not None and st.level:
            lv = max(lv, st.level)
        return lv or None

    def _back_row_centers_by_level(self) -> list[Point]:
        """r77e→ADR-0281:后排槽位按 **level** 选档布局(狸猫局 8 槽错位根修)。

        槽数 = ``effective_back_slots(level)``(level≤5→6 / ≥7→8 / ==6→保守 6+
        留证);按「后排N槽-」档取(与 read_deployed_chars 同源);level 读不到/无档
        → 退基线「后排-」(旧行为)。旧 cap 驱动已废(cap=宝钻叠加,与布局无关)。
        """
        from one_dragon.utils.log_utils import log as _log
        from sr_od.application.currency_war.cw_back_layout import (
            _LAYOUT_PREFIX,
            effective_back_slots,
            note_pending_7slots,
        )
        lv = self._session_level() or 6
        note_pending_7slots(self.last_screenshot, lv, 'deploy_bench')
        n = effective_back_slots(lv)
        if n in _LAYOUT_PREFIX:
            return self._row_centers(_LAYOUT_PREFIX[n])
        _log.warning('[cw!][layout] deploy 侧 后排 %d 槽布局未建档(退 6 槽基线;'
                     '补档流程见 ADR-0281)', n)
        return self._row_centers('后排')

    @operation_node(name='部署备战栏角色', is_start_node=True)
    def deploy(self) -> OperationRoundResult:
        si = self.ctx.screen_loader.get_screen(DeployBench.SCREEN_NAME)
        if si is None:
            log.warning('[cw-deploy] 未加载「货币战争-备战」screen_info,跳过部署')
            return self.round_fail(status=DeployBench.STATUS_NO_SCREEN)
        # live 2026-08-15:事件 overlay(盛会之星等)挡 drag —— 拖全灭(源槽未变连环)+ 空场上阵
        # HP 82→1。overlay 在 → 跳过部署(success 态交还上层,Director 观察会 bail 交外环 handler)。
        for _scr, _area in (('货币战争-盛会之星', '标识-盛会之星'),
                            ('货币战争-选择伙伴', '标识-选择伙伴'),
                            ('货币战争-祈愿试炼', '标识-祈愿试炼')):
            if self.round_by_find_area(self.last_screenshot, _scr, _area, crop_first=False).is_success:
                log.warning(f'[cw-deploy] 事件 overlay({_scr})在,跳过部署(交主循环 handler)')
                return self.round_success('事件overlay,跳过部署')

        bench = self._row_centers('备战栏')
        front = self._row_centers('前排')
        # r77e 审计 BUG-4b/1c → ADR-0281:后排槽位必须按 **level 档布局**取(与
        # read_deployed_chars 同源)——狸猫局 lv7+ 的 8 槽坐标若用基线 6 槽会错位
        # (编号↔坐标两套参照系):_deploy_deterministic 漏计固定单位(假未满白拖)
        # + _sell_offtarget_deployed 用 8 槽编号索引 6 槽表 → 卖错邻槽。统一走
        # cw_back_layout 选档(level 驱动)。
        back = self._back_row_centers_by_level()
        if len(bench) == 0:
            log.info('[cw-deploy] 备战栏无槽坐标,跳过')
            return self.round_success(DeployBench.STATUS_NO_BENCH)

        templates = self._get_templates()
        # deployed-lock(doc gameplay:78)是误判,deployed 可卖(用户实机确认 gold 增加)。
        _match = self.ctx.cw_match
        _board = (_match.session.last_state.board
                  if (_match is not None and _match.session is not None
                      and _match.session.last_state is not None) else None)
        # r120(断层①修复:配方从不成型的执行层根因):deploy 的 target 判定原读
        # session.target_comp(终局 comp)——双轨期预囤的框架件(藿藖/卡芙卡=仙舟)
        # 不是终局 comp 的阵营/core → deploy-swap 当 off-target 卖(局35 r7 卡芙卡
        # 被卖 4 次实证)+「target 先」排序不认 → 板面配方永不成型(P1 通关全靠
        # 人口硬扛)。修:双轨期走 decision_target 单一入口(=配方伪 comp),
        # 框架件成为部署一等公民——与买/卖两侧 r72「三侧单一源」对齐(deploy
        # 侧此前是缺口)。
        from sr_od.application.currency_war.cw_recipe import decision_target as _dt_fn
        _tgt_comp = None
        if _match is not None and _match.session is not None:
            _st_dual = getattr(_match.session, 'dual_track_phase', False)
            if _st_dual:
                _pseudo = _match.session.last_state
                _tgt_comp = _dt_fn(_match.session, _pseudo) if _pseudo is not None else None
            if _tgt_comp is None:
                _tgt_comp = _match.session.target_comp
        # ADR-0152(评审🔴1):all_factions(核心+弹性)—— flex 板面单位(砂金=公司/护盾 是列车护盾流
        # 常驻)不判 off-target;与 _card_hits_target 同源(策略层奖励的 flex 铺板 ≠ 执行层可卖的散牌)。
        _target_factions: set[str] = set(_tgt_comp.all_factions) if _tgt_comp is not None else set()
        # live 2026-08-15(M1 位面2 列车同行4→1 稀释根因):comp 核心辅助(花火/瓦尔特/符玄等)的阵营标签
        # ∌ comp 阵营(列车同行)—— 只按阵营判 target 会把 core_char 辅助当 off-target 卖掉 → 板成型度崩。
        # target 判定 = 阵营/流派交集 **或** core_chars 成员(_card_hits_target 同语义,ADR-0103)。
        _target_cores: set[str] = set(_tgt_comp.core_chars) if _tgt_comp is not None else set()
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
                if name in _target_cores:
                    return True   # core_char 辅助(阵营∉comp)也是 target(勿卖/优先上)
                _c = get_char(name) if name else None
                return _c is not None and bool((set(_c.factions) | set(_c.flows)) & _target_factions)

            _bench_tgt_n = sum(1 for _bc in _bench_chars if _is_tgt_char(_bc.char_id))
            if _bench_tgt_n > 0:
                _n = self._sell_offtarget_deployed(front, back, _target_factions, templates,
                                                   max_sell=_bench_tgt_n, target_cores=_target_cores)
                log.info(f'[cw-deploy] deploy-swap:sell {_n} off-target deployed(留 target,1:1 替换上限={_bench_tgt_n})'
                         f' 腾位; bench target={_bench_tgt_n}/{len(_bench_chars)} → redeploy 集中')
            else:
                log.info('[cw-deploy] deploy-swap 跳过:bench 无 target 单位(留 off-target bodies;'
                         ' 根因=buy 未买 target / economy 未攒金升级)')
        self._deploy_deterministic(bench, front, back, templates)   # D-7:CV 确定性部署(CV 占用 + position_pref 选排)
        self._reconcile_tracking(templates)   # D-12(3.3.2):deploy 后 SIFT 真实身份纠 tracking 漂(观测回路)
        # r241 换排纠正(用户实锤:三月七被兜底强推前排,后续永不被挪回):
        # deploy 只管 bench→场,场内错排(pref=back 在前排/fallback 遗留)无人纠正
        # → 兜底一旦发生就永久错排。此处扫 read_deployed_chars,错排者拖回正排。
        try:
            self._fix_misplaced_rows(front, back, templates)
        except Exception as e:   # noqa: BLE001  纠正失败不阻塞部署
            log.debug('[cw-deploy] 换排纠正失败(不阻塞): %s', e)

        # ⚠️ 拖完整队等待(用户 2026-08-16 实证):末次 drag 的羁绊特效/升星 overlay(盛会之星/
        # 圣杯/银狼升级)可能仍在播 → 后续读(heavy state/SIFT/equip)被遮挡污染。等 1.5s 稳定。
        time.sleep(1.5)
        log.info('[cw-deploy] 拖完')

        # r132 装备遥测采集(穿戴侧盲区修复):decisions.jsonl 的 deployed.equips 恒空
        # (决策点 state 来自 session.tracking 深拷贝,tracking 无 equips 字段;r117 定位)
        # → 判读永远看不见装备齐度。deploy 后此处是**全量读时机**(画面稳定/正对
        # 备战)——读 equipped below icon 并写 session.tracked_deployed[].equips,
        # 后续决策快照自动携带。best-effort,失败不阻塞。
        try:
            self._snapshot_equips_into_tracking()
        except Exception as e:   # noqa: BLE001  采集失败不影响部署
            log.debug('[cw-deploy] equips 采集失败(不阻塞): %s', e)

        return self.round_success(DeployBench.STATUS_DEPLOYED, wait=1)

    def _fix_misplaced_rows(self, front: list, back: list,
                            templates: AvatarTemplates | None) -> None:
        """r241 场内换排纠正 + r250 前排保证(场内版)。

        r241:pref=back 却在前排(或反之)→ 拖回正排
        (兜底强推遗留的永久错排)。
        r250(用户局实锤「前台区域无角色,无法出战」卡 12min):
        全部角色在后排+前排完全空 → 游戏拒出战;deploy 的
        前排保证只管 bench→场,场内全后排无人纠正 → 死循环。
        修:此情形强制把一个后排(pref=front 优先)挪前排——
        出战硬要求 > 站位偏好。"""
        if templates is None:
            return
        _all_deployed = read_deployed_chars(self.ctx, self.screenshot(), templates)
        # ADR-0281 件4:系统单位剔除统一走 exclude_system_units(r250 场内版此前取
        # back_chars[0] 可能选中狸猫 → 拖必失败白烧重试)。
        deployed = exclude_system_units(_all_deployed)
        if not deployed:
            return
        # r250 前排保证(场内版):前排全空 + 后排有人 → 挪一
        front_occupied = [d for d in deployed
                          if (d.position_pref or 'back') == 'front']
        if not front_occupied:
            back_chars = [d for d in deployed
                          if (d.position_pref or 'back') == 'back']
            if back_chars and back:
                # 优先真 front(pref)在后排的;否则第一个后排
                cand = next(
                    (d for d in back_chars
                     if get_char(d.char_id) is not None
                     and get_char(d.char_id).position_pref() == 'front'),
                    back_chars[0])
                ch = get_char(cand.char_id) if cand.char_id else None
                if ch is not None and 1 <= cand.slot <= len(back):
                    src = back[cand.slot - 1]
                    if front:
                        dst = front[0]
                        if DragCwChar.drag_char(self, src, dst):
                            log.info(f'[cw-deploy] 前排保证(场内 r250):'
                                     f'{cand.char_id} 后排{cand.slot}'
                                     f' → 前排1(前排空,出战硬要求) ✓')
                            time.sleep(1.2)
                            self._reconcile_tracking(templates)
                            return
        # r241 原逻辑:错排者归位
        front_empty = [i for i, c in enumerate(front)
                       if not slot_occupied(self.screenshot(), int(c.x), int(c.y))]
        back_empty = [i for i, c in enumerate(back)
                      if not slot_occupied(self.screenshot(), int(c.x), int(c.y))]
        moved = 0
        for d in deployed:
            ch = get_char(d.char_id) if d.char_id else None
            if ch is None:
                continue   # 系统单位(cost==0)已在函数头统一剔除(ADR-0281 件4)
            want = ch.position_pref()
            cur = d.position_pref or 'back'
            if want == cur:
                continue    # 排对了
            # 错排:目标排的空槽
            if want == 'front':
                if not front_empty:
                    continue
                ti = front_empty.pop(0)
                dst = front[ti]
                _row_cn = '前'
            else:
                if not back_empty:
                    continue
                ti = back_empty.pop(0)
                dst = back[ti]
                _row_cn = '后'
            src_row = front if cur == 'front' else back
            if not (1 <= d.slot <= len(src_row)):
                continue
            src = src_row[d.slot - 1]
            if DragCwChar.drag_char(self, src, dst):
                moved += 1
                log.info(f'[cw-deploy] 换排纠正:{d.char_id} {cur}排{d.slot}'
                         f' → {_row_cn}排{ti + 1}(pref={want}) ✓')
                time.sleep(1.2)    # 特效等待(同 drag 后约定)
            else:
                log.info(f'[cw-deploy] 换排纠正:{d.char_id} 拖3次未动,跳过')
                # 槽没占住,回收
                (front_empty if want == 'front' else back_empty).insert(0, ti)
        if moved:
            log.info(f'[cw-deploy] 换排纠正完成: {moved} 个角色归位')
            self._reconcile_tracking(templates)   # 换排后 tracking 再纠一次

    def _snapshot_equips_into_tracking(self) -> None:
        """读当前画面已上阵装备 → 回写 session.tracked_deployed 的 equips 字段。"""
        _match = self.ctx.cw_match
        if _match is None or _match.session is None:
            return
        from sr_od.application.currency_war.cw_bench_equips import (
            EquipsInconsistencyError,
            assert_equips_consistency,
        )
        from sr_od.application.currency_war.cw_equipment import (
            ensure_equip_tm_templates,
        )
        from sr_od.application.currency_war.cw_identity_obs import read_row_equipped
        equip_grays = ensure_equip_tm_templates(self.ctx)
        if equip_grays is None:
            return
        scr = self.last_screenshot
        front_eq = read_row_equipped(self.ctx, scr, equip_grays, '前排', 4)
        back_eq = read_row_equipped(self.ctx, scr, equip_grays, '后排', 6)
        tracked = _match.session.tracked_deployed
        _n = 0
        for c in tracked:
            slot = getattr(c, 'slot', None)
            if slot is None:
                continue
            eq = (front_eq if c.position_pref == 'front' else back_eq).get(slot, [])
            if eq:
                # C6 装备对账(契约 2,W38):deployed 侧画面可读 → 与账面交叉校验,
                # 不一致告警留痕(禁静默用账;哨兵停机留证归后续实机运维批),
                # 然后画面真值覆盖(deployed 侧画面 = truth,tracking 是 bench 侧单一源)。
                try:
                    assert_equips_consistency(c, eq, source='deploy_bench.snapshot')
                except EquipsInconsistencyError as e:
                    log.warning('[cw!] %s(账本漂移,画面真值覆盖)', e)
                c.equips = list(eq)
                _n += len(eq)
        if _n:
            log.info('[cw-deploy] equips 采集:tracked %d 件写入(决策快照将携带)', _n)

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
        # r70 过渡框架并进 deploy target 集(双轨期):框架牌 = 当前阶段的「临时 target」,
        # 否则保血资产(三月七/藿藿/饮月)被判 off-target 散牌留 bench → 白板挨打
        # (r70 审计「买了→不上场→被卖」三侧断裂的 deploy 侧)。定型后 framework 已清空,
        # 集合退化为原 target-only 行为。
        _fw = getattr(_sess, 'transition_framework', '') if _sess is not None else ''
        if _fw:
            from sr_od.application.currency_war.cw_transition import (
                FRAMEWORK_FACTIONS,
                TRANSITION_PACK,
            )
            _tgt = _tgt | set(FRAMEWORK_FACTIONS.get(_fw, ()))
            # r72 口径对齐(review #3):与 plan._should_deploy 同口径 ——
            # 当先框架非 drop + 通用件(散件 drop 不认;通用 carry 千冶·刃认)。
            _fw_carry = {n for n, (f, t) in TRANSITION_PACK.items()
                         if (f == _fw or f == '通用') and t != 'drop'}
        else:
            _fw_carry = set()
        # 5.1.8 deploy_cap(live 发现 drag 白拖根因 = cap 满,2026-08-12):deployed(CV front_occ+back_occ 实测阵上)
        # ≥ level(cap,D-19「cap=level」)→ 板满,bench 角色上不了 → 不拖(留 bench;防 drag 被拒源槽占 placed=0 白拖
        # + 用户 live 观察 bug4「未考虑上限」)。CV 实测 deployed 优于 state.deployed_count(board 重建可能虚高)。
        # cap 真值优先 read_deploy_cap(OCR X/Y 的 Y,含宝钻/诅咒加成);读不到 fallback level(D-19 cap≈level)。
        # ⚠️ level≠cap 场景(诅咒-1 / 宝钻+1):用 level 会误判 cap 未满 → 白拖(D-53 注 level=cap 无加成,但加成时偏)。
        # r60(2026-08-18 用户实锤「明明随便上填空位也可以」):cap 低读 = 部署阻塞(lv5 真值被
        # paddle 失读/last_state 毒化成 3 → 板满假判 → 2 人留 bench,11:56:24 实锤)。cap 误差
        # 两个方向不对称:低读阻塞上阵(战力真空,贵)/高读多拖一次被游戏拒(源槽弹回,重试停,便宜)。
        # r64 review P1 修(语义分层):**paddle 直读 = 权威**(屏幕 X/Y 显示的就是真 cap,含
        # 诅咒-1/宝钻+1 —— 读到时直用,max 会把诅咒降级吃掉);**失读才 max 兜底**(单调链
        # last_level_obs[_resolve_level 维护已防毒化] vs last_state.level 取大 —— 低读阻塞
        # 上阵的代价 > 高读白拖一次,不对称取舍)。
        _cap = read_deploy_cap(self.ctx, scr)
        # r80 审计 d-风险1:入场帧(收起商店 1s 过渡)失读时布局已退基线 6 槽;
        # 此处 fresh 帧按 **level** 重建 back 布局(ADR-0281:level 驱动;cap 误读
        # 不再影响选档——cap 只用于上面的板满门)。
        from sr_od.application.currency_war.cw_back_layout import (
            _LAYOUT_PREFIX,
            effective_back_slots,
            note_pending_7slots,
        )
        _lv = self._session_level()
        if _lv is not None:
            note_pending_7slots(scr, _lv, 'deploy_bench.midloop')
            _n = effective_back_slots(_lv)
            if _n in _LAYOUT_PREFIX:
                back = self._row_centers(_LAYOUT_PREFIX[_n])
        if _cap is None:
            _lv_chain = (getattr(_sess, 'last_level_obs', 0)
                         if _sess is not None else 0) or 0
            _lv_state = (_sess.last_state.level
                         if (_sess is not None and _sess.last_state is not None) else None)
            _cap_candidates = [c for c in (_lv_chain, _lv_state) if c is not None and c > 0]
            if _cap_candidates:
                _cap = max(_cap_candidates)
                log.info(f'[cw-deploy] cap paddle 失读 → 单调链={_lv_chain} state={_lv_state}'
                         f' 取 max={_cap}(低读阻塞上阵 > 高读白拖,r60/r64)')
            else:
                log.info('[cw-deploy] cap 全源失读 → None(不设板满门,拖到游戏拒即真值)')
        if _cap is not None and _cap > 0:
            _deployed = (len(front) - len(front_empty)) + (len(back) - len(back_empty))
            if _deployed >= _cap:
                log.info(f'[cw-deploy] 板满 cap:deployed={_deployed} ≥ cap={_cap}(level,5.1.8)'
                         f' front空={len(front_empty)} back空={len(back_empty)} → bench 角色留 bench(不白拖)')
                return
        # D-8:bench 身份走 SIFT(read_bench_chars,plaza 官方立绘库可靠)→ 真实羁绊(target 排序)+ position_pref
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
        # ADR-0139:comp 特定站位覆盖命途默认(爻光必后台/万敌独前排——攻略实证,同 _pick_deploy_row 语义)
        if (_sess is not None and _sess.target_comp is not None
                and _sess.target_comp.char_positions):
            for bi2, cid2 in list(_bench_cid.items()):
                if cid2 in _sess.target_comp.char_positions:
                    _bench_pos[bi2] = _sess.target_comp.char_positions[cid2]
            log.info(f'[cw-deploy] bench 身份(SIFT):{ {i: sorted(b) for i, b in _bench_id.items()} }'
                     f' pos={_bench_pos} tgt={sorted(_tgt)}')
        # 5.1.7 同角色去重(live 观察 3,场上同角色只 1):read_deployed_chars → deployed char_id;
        # bench 角色已 deployed → deploy 循环跳过(避免场上重复角色 + 买/部署同名)。
        _deployed_cids: set[str] = set()
        _deployed_fac: dict[str, int] = {}   # r288 配方底线仲裁用
        if templates is not None:
            _deployed_cids = {bc.char_id for bc in read_deployed_chars(self.ctx, scr, templates) if bc.char_id}
            if _deployed_cids:
                log.info(f'[cw-deploy] deployed 身份(5.1.7 去重):{sorted(_deployed_cids)}')
            # 已上场角色的阵营档(多阵营角色每阵营 +1,同板面 OCR 口径)
            # r361b(review B 修:口径统一):补 flows——_tier_completes
            # 的补档键按 factions+flows 全羁绊判档,而此处只累 factions
            # → 流派补档件(击破2→3)在生产永不优先,锁测试锁了个
            # 生产走不到的路径。同口径修复(板面 OCR 含流派行)。
            from sr_od.application.currency_war.cw_chars import CHARACTERS as _CH
            for _dc in _deployed_cids:
                _dch = _CH.get(_dc)
                if _dch:
                    for _f in ((_dch.factions or ()) + (_dch.flows or ())):
                        _deployed_fac[_f] = _deployed_fac.get(_f, 0) + 1
        tgt_idx, rest = [], []
        # live 2026-08-15:target 优先 = 阵营交集 **或** core_char(_bench_cid;辅助如花火/瓦尔特
        # 阵营 ∉ comp 阵营,只按 _bonds 判会把核心辅助排到 rest 尾部 → 上场晚/被换血)。
        _cores = (_sess.target_comp.core_chars
                  if (_sess is not None and _sess.target_comp is not None) else None) or []
        for i in bench_occ:
            _bonds = _bench_id.get(i)
            _cid0 = _bench_cid.get(i)
            # r70:框架 carry/partial 也算 target(双轨期临时 target 语义,同 _tgt 并集)
            _is_tgt = (((_bonds and _bonds & _tgt) or _cid0 in _cores)
                       if _tgt else False) or _cid0 in _fw_carry
            (tgt_idx if _is_tgt else rest).append(i)
        # r361(局46 实锤,tgt 序内补档优先)+ r404-A1/ADR-0258 点火首键
        # (ADR-0261 裁决选项1):排序统一走 `_deployment_order`(与纯函数
        # cw_deploy_logic.select_deployments 同语义)——tgt/rest 序均加
        # ignition_gain 首键 + 桶序修正(点火 rest 件先于 ignition=0 的
        # tgt 件)。旧版此处只有 r361 tier_completes + r251 引擎身份键,
        # 无点火键(r404-A1 当时只落了纯函数侧)。
        # ADR-0130(用户节奏 §7-1「开场买牌囤 bench 不上阵」+ 复查确认 spread 种子):off-target 散牌
        # 单张**留 bench 不上阵**(对齐 planner `_should_deploy` 语义)—— 上场条件:① target;② 同阵营
        # 成对(board+bench 计数 ≥2,凑过渡羁绊,「买过渡阵容」人玩节奏);③ SIFT 未识别(无法判,
        # 照旧上防空板);④ 保底:板完全空且无 target 无对 → 上 1 个(body > 空板)。旧 deploy-all 把
        # 每个买单张都推上场 = spread 吸引子种子(fp 冻结 0.25 根因,M14/M15 遥测实锤)。
        _pair_counts: dict[str, int] = {}
        if _sess is not None and _sess.last_state is not None:
            _pair_counts.update(_sess.last_state.board)
        _bench_fac: dict[int, str] = {}
        for i, _cid0 in _bench_cid.items():
            _c = get_char(_cid0) if _cid0 else None
            if _c is not None and _c.factions:
                _bench_fac[i] = _c.factions[0]
                _pair_counts[_c.factions[0]] = _pair_counts.get(_c.factions[0], 0) + 1
        _held: list[int] = []
        # M18 复盘回归修正(ADR-0130 补):散牌留 bench 是**P1 开局囤牌**语义;P2+ 人口扩展期
        # (vacancy>2,等级 7-8 撑起的人口)空位本身就是战力,散牌该填位(M18 实测放置 3/18、满员率 76%,
        # 未达上限弹窗频发 = 留 bench 过严的回归)。门:plane≥2 或 vacancy>2 → 散牌照旧上场。
        _fill_mode = (len(front_empty) + len(back_empty)) > 2
        # r263b(配方纪律,局15 鉴别诊断):配方基础未满(<5 档)时,
        # **非配方件即使成对也不上板**(占槽稀释配方深度)。
        _board_recipe = sum(
            v for k, v in (_sess.last_state.board
                           if _sess is not None
                           and _sess.last_state is not None
                           else {}).items()
            if k in _RECIPE)
        _recipe_starved = _board_recipe < _RECIPE_BASE
        # r387(富余=填空):必上件数 = target 候选 + 同阵营成对件(两者必然要上);
        # 空位扣除必上仍有富余 → 配方围栏放行散牌填空(围栏只在 cap 紧张时拦)。
        _roomy = _cap_roomy_of(
            len(front_empty), len(back_empty),
            len(tgt_idx) + sum(1 for i in rest
                               if _bench_fac.get(i) is not None
                               and _pair_counts.get(_bench_fac[i], 0) >= 2))
        for i in list(rest):
            if i not in _bench_cid:
                continue   # SIFT 未识别:照旧上(无法判 target/阵营)
            _f = _bench_fac.get(i)
            if (_f is not None and _f not in _DEPLOY_FENCE
                    and _recipe_starved and not _roomy):
                rest.remove(i)   # 非过渡配方件 + 配方基础未满 + cap 紧张 → 留 bench
                _held.append(i)
                continue
            if _f is not None and _pair_counts.get(_f, 0) >= 2:
                continue   # 同阵营成对(board+bench ≥2):凑过渡羁绊,上
            if _fill_mode:
                continue   # 人口扩展期:空位>2,散牌填位(body>空位,防未达上限弹窗)
            rest.remove(i)
            _held.append(i)
        _board_empty = (len(front_empty) == len(front)) and (len(back_empty) == len(back))
        if _board_empty and not tgt_idx and not rest:
            _fallback = _held[:1]
            if _fallback:
                rest.extend(_fallback)
                _held = _held[1:]
                log.info(f'[cw-deploy] 板空保底:上 1 个散牌(body > 空板):{_fallback}')
        if _held:
            log.info(f'[cw-deploy] 散牌留 bench(不成对/非 target,ADR-0130):slots={[h + 1 for h in _held]}')
        # r251 修 B(引擎 pair 优先)+ r404-A1 点火首键(ADR-0261 裁决
        # 选项1):cap 有限时序竞争——「恰好点火」件(第 tier 人)最优先,
        # r251 引擎身份键降为次键(纯函数侧探针实证:vacancy=1 时冗余
        # 第4仙舟曾挤掉点火列车2)。排序体单一源 `_deployment_order`。
        order = _deployment_order(tgt_idx, rest, _bench_id, _bench_fac,
                                  _deployed_fac)
        log.info(f'[cw-deploy] deterministic: bench_occ={bench_occ} target先={tgt_idx}'
                 f' front空={len(front_empty)} back空={len(back_empty)}')
        placed = 0
        _skipped = 0   # 合法跳过(去重/配方底线/源槽已空)≠ 上阵失败
        _cap_stopped = False
        for bi in order:
            # live 2026-08-15(match5 根因终定位):起始 cap 检查只做一次 —— 循环中途 deployed 达 cap 后
            # 游戏拒收后续 drag(单位弹回 = 「源槽未变」连环假失败 + 每槽 3×2s 白烧)。每槽动态复查。
            if _cap is not None and _cap > 0:
                _deployed_now = (len(front) - len(front_empty)) + (len(back) - len(back_empty))
                if _deployed_now >= _cap:
                    log.info(f'[cw-deploy] 板满 cap(动态停):deployed={_deployed_now} ≥ cap={_cap}'
                             f' placed={placed} → 剩余 bench 角色留 bench(不白拖)')
                    _cap_stopped = True
                    break
            # ⚖️ 同名在场禁双(5.1.7,全局不变量;语义单一源 cw_plan.deploy_legal)。
            # 执行层直查 char_id 集合(此处在 SIFT 读身份后的确定性部署,不走 _should_deploy)。
            _cid = _bench_cid.get(bi)
            if _cid and _cid in _deployed_cids:
                log.info(f'[cw-deploy] 去重(5.1.7,不变量 cw_plan.deploy_legal 同源):'
                         f'bench槽{bi+1}({_cid}) 已 deployed,跳过')
                _skipped += 1
                continue
            # r288(局23/24 连续实锤:锁 jizi 线列车 3 档吃板挤掉仙舟,
            # 仙舟 2→1 → r3-r4 battle -13×2):配方基础线优先仲裁——
            # 仙舟档 < 基础线(攻略[20] 3仙舟+2DOT)时,列车件封顶
            # 2 档(锁线路径的线内件上板也要守配方底线;配方纪律
            # 此前只在散 pair 路径生效,锁线路径无守门=审查②盲区)。
            # ADR-0261 裁决选项3:cw_deploy_logic.select_deployments 已补
            # 同语义门(running 阵营档仲裁)——sim 从此能测出本形态。
            _fac = _bench_fac.get(bi, '')
            if _fac == '列车同行' and _RECIPE is not None:
                # ADR-0261 裁决修订3(单一源):门的 2/3 档数值从
                # TRANSITION_TRAITS 派生(与 cw_deploy_logic.select_
                # deployments 的 r288 门同源)——旧硬编码 2/3 是历史双源。
                from sr_od.application.currency_war.cw_deploy_logic import (
                    TRANSITION_TRAITS as _TT,
                )
                _tier_of = dict(_TT)
                _train_cap = _tier_of.get('列车同行', 2)
                _xz_base = _tier_of.get('仙舟', 3)
                _train_now = _deployed_fac.get('列车同行', 0)
                _xz_now = _deployed_fac.get('仙舟', 0)
                if _train_now >= _train_cap and _xz_now < _xz_base:
                    log.info(f'[cw-deploy] 配方底线(r288):列车{_train_now}档+仙舟{_xz_now}'
                             f'→列车件留bench(仙舟<3 基础线优先,防挤占)')
                    _skipped += 1
                    continue
            # live 2026-08-15(match4 deploy storm 根因):起始帧 slot_occupied 瞬时假阳(商店关闭/卖出
            # 动画残影 → 对空槽白烧 3×2s drag 重试)。每槽 drag 前 fresh 复查占用,空 → 跳过。
            if not slot_occupied(self.screenshot(), int(bench[bi].x), int(bench[bi].y)):
                log.info(f'[cw-deploy] deterministic: bench槽{bi+1} fresh 复查空(起始帧假阳/已上阵) → 跳过')
                _skipped += 1
                continue
            # 5.1.6:按角色 position_pref 选排(前台→前排、后台/flex→后排);对应排满 fallback 另一排(避免不上场)。
            pref = _bench_pos.get(bi, 'back')   # SIFT 漏读身份 → 默认 back(后排槽多 6 > 前排 4,安全)
            # 前排保证(出战要求,5.1.6 补;2026-08-16 修正用户实锤):pref=back 但前排完全空(无角色)
            # → 强制前排(出战硬要求前排有角色)。⚠️ 旧实现"当前队首 back 强转前排"错在**没看后续
            # 队列**——M47 22:32 实锤:target 先行把三月七(back)排队首,而队列后面就有真理医生/
            # 乱破(真 front),旧逻辑强转三月七去前排、真 front 也进前排 → back 角色错占前排位。
            # 修正:前排全空时**先重排**(剩余 order 中 pref=front 角色提到当前位前),无 front
            # 候选才强转当前 back 角色。
            if pref == 'back' and len(front_empty) == len(front):
                _pos = order.index(bi)
                _later_front = next(
                    (j for j in order[_pos + 1:]
                     if _bench_pos.get(j, 'back') == 'front'
                     and _bench_cid.get(j) not in _deployed_cids),
                    None)
                if _later_front is not None:
                    order.remove(_later_front)
                    order.insert(_pos, _later_front)
                    log.info(f'[cw-deploy] 前排保证(重排): 真front槽{_later_front + 1} 提前'
                             f'(当前槽{bi + 1}为back不强转)')
                    continue   # 重排后重处理当前位置(现在是真 front)
                pref = 'front'
                log.info(f'[cw-deploy] 前排保证:bench槽{bi+1}(pref=back)→ 强制前排(前排空且队列无front候选)')
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
                # r288:成功上场同步阵营档(配方底线仲裁的状态源)
                # r363b(review B-2 修):增量口径对齐初始快照——该角色
                # **全部**羁绊(factions+flows)各 +1(旧只计第一阵营,
                # 多阵营角色上阵后与真实板面漂移,r288 门错判风险)。
                _bonds_all = (_bench_id.get(bi) or ())
                for _f2 in _bonds_all:
                    _deployed_fac[_f2] = _deployed_fac.get(_f2, 0) + 1
                if _match is not None and getattr(_match, 'bench_slot_map', None):
                    _gone = next((n for n, s in _match.bench_slot_map.items() if s == bi + 1), None)
                    if _gone is not None:
                        del _match.bench_slot_map[_gone]
                # ⚠️ 拖后特效等待(用户 2026-08-16 实证):拖上场会触发羁绊特效/升星 overlay
                # (盛会之星/圣杯/银狼升级等)遮挡画面 —— 紧跟的下个 drag/CV 验槽/SIFT 读全被
                # 污染。每个成功 drag 后等 1.2s 让特效播完/overlay 稳定(下轮 loop/director
                # 的事件 overlay 检测再接管真正的交互型 overlay)。
                time.sleep(1.2)
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
        # r349(局38 判读):合法跳过(去重/配方底线/源槽已空)≠ 上阵失败——
        # 旧 `placed < len(order)` 把「target 已在场,bench 同名拷贝被去重」
        # 误报 [cw!] 假警报(placed=0/2,局38 01:29 实证)。分母扣除跳过数。
        if placed + _skipped < len(order) and not _cap_stopped:
            log.warning(f'[cw!] [deploy] 上阵不全: placed={placed}/'
                        f'{len(order) - _skipped}(跳过{_skipped};失败帧已存证)')
        log.info(f'[cw-deploy] deterministic 完成: placed={placed}/{len(order) - _skipped}'
                 f'(跳过{_skipped})')

    def _get_templates(self) -> AvatarTemplates | None:
        """加载 avatar SIFT 模板(缓存到 ctx.cw_avatar_templates,首次 load 后复用)。"""
        cached = getattr(self.ctx, 'cw_portrait_templates', None)
        if cached is not None:
            return cached
        base = Path(__file__).resolve().parents[6] / 'assets/template'
        portrait_dir = base / 'currency_war' / 'portrait_plaza'   # 官方立绘库(plaza 烘焙;唯一库,旧手采库已删 2026-08-17)
        if not portrait_dir.is_dir():
            log.warning(f'[cw-deploy] 立绘库目录不存在 {portrait_dir},退非身份 deploy')
            return None
        templates = load_avatar_templates(portrait_dir)
        self.ctx.cw_portrait_templates = templates
        log.info(f'[cw-deploy] 加载 {len(templates)} 个 avatar 模板(缓存 ctx)')
        return templates

    def _sell_offtarget_deployed(self, front: list[Point], back: list[Point],
                                 target_factions: set[str], templates: AvatarTemplates | None,
                                 max_sell: int = 99, target_cores: set[str] | None = None) -> int:
        """D-10:卖 deployed 中的 **off-target** 单位(留 target),给 bench target 腾位。

        SIFT ``read_deployed_chars`` 识别 deployed 身份 → off-target(羁绊 ∌ target)拖出售区。
        target 单位保留(替旧 sell-all 毁掉板上 target)。卖数 ≤ ``max_sell``(**1:1 替换上限** = bench
        target 数,保证每个卖出被一个 target 补上,板大小稳定;防 bench target 少却卖光 off-target → 板缩 HP 崩)。
        ⚠️ ``read_deployed_chars`` 首用(deployed SIFT 身份未单验,D-4 验的是占用);日志详记识别结果供核实,
        首跑即验证 —— 若身份错(误卖 target / 漏卖 off-target)据日志回退。
        """
        deployed = exclude_system_units(
            read_deployed_chars(self.ctx, self.last_screenshot, templates)
        ) if templates else []
        _sell = Point(70, 846)
        sold = 0
        for d in deployed:
            if sold >= max_sell:
                break
            if d.char_id and d.char_id in (target_cores or set()):   # core_char 辅助保留(live 花火误卖根因)
                continue
            ch = get_char(d.char_id) if d.char_id else None
            if ch is None:
                continue   # 系统单位(cost==0)已在入口剔除(ADR-0281 件4)
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

        2026-08-16(观察冲突审计 P0 #12):改调公共 ``cw_reconcile.reconcile_tracking`` ——
        旧实现直接覆盖无空读守卫(M14 实锤的过渡帧双空读会污染 tracking;守卫此前只在
        director 版),同语义两处强弱不一是 bug 温床;统一后另接 obs_conflict 证据链。
        """
        if templates is None:
            return
        _match = self.ctx.cw_match
        if _match is None or _match.session is None:
            return
        scr = self.screenshot()   # fresh post-deploy
        real_bench = read_bench_chars(self.ctx, scr, templates)
        real_deployed = read_deployed_chars(self.ctx, scr, templates)
        from sr_od.application.currency_war.cw_reconcile import reconcile_tracking
        reconcile_tracking(_match.session, real_bench, real_deployed, scr,
                           source='deploy_bench', ctx=self.ctx)
