"""tracking 对账公共层(观察冲突审计 P0 #12)。

两处对账实现(deploy_bench._reconcile_tracking / cw_screen_prep._reconcile_tracking)同语义
但强弱不一 —— director 版有空读守卫(M14 实锤)+截图留证,deploy_bench 版直接覆盖(过渡帧
双空读会污染 tracking)→ bug 温床。本模块抽公共 helper:统一守卫 + obs_conflict 证据链。
"""
from __future__ import annotations

import weakref

from cv2.typing import MatLike

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_of,
)

# (终态契约 §A:下行守卫标定常量 HP_REAL_JUMP_CONFLICT/HP_LOSS_CAP_P100_BY_NODE/
#  HP_SUSPECT_*/HP_ZERO_LOSS_NODE_TYPES 随守卫删除——cw_registry 标定面
#  失去消费方,标定段归属复核归 docstring 桶。)
from sr_od.application.currency_war.kernel.cw_opening_hp import opening_hp_prior

# 合成特效帧态门注入槽(分包依赖矩阵禁 kernel→obs 直依):kernel 只持槽位,
# 实现由 app 装配点(decision_assembly.install_obs_ports)从 obs 桶注入。
# 缺省关(None)= 门放行,回退直接走「连续 2 次确认采新」——与门函数自身
# 「screen=None → False 不拦」的 best-effort 语义同向,不引入新故障面。
_IS_MERGE_EFFECT_FRAME = None


def set_merge_effect_gate(fn) -> None:
    """注入合成特效帧态门实现(obs 桶 ``is_merge_effect_frame``;生产武装点接通)。"""
    global _IS_MERGE_EFFECT_FRAME
    _IS_MERGE_EFFECT_FRAME = fn


def is_merge_effect_window(screen: MatLike | None) -> bool:
    """合成特效窗判定读口(P3-10 批次二复审):观察消费前的窗内统一判别口。

    复用 ``_IS_MERGE_EFFECT_FRAME`` 注入槽(生产武装点 =
    decision_assembly.install_obs_ports 注入 obs 桶 ``is_merge_effect_frame``——
    与 star 回退帧态门是同一特效窗物理事实的两个消费口)。``screen=None`` 或
    槽缺省关(未装配)恒 False = 核对放行,与既有门 best-effort 语义同向,
    不引入新故障面;注入后 True = 窗内星读数物理不可信,消费方顺延核对
    (本帧不写观察、保 logic 逻辑态值,下帧干净帧实读覆盖)。
    """
    if screen is None or _IS_MERGE_EFFECT_FRAME is None:
        return False
    return bool(_IS_MERGE_EFFECT_FRAME(screen))


# ===== 星级抖动门(槽位锚定 + 两帧一致才采新)=====
# 病灶(run_20260915_054718 §5/§8 候选2):同名多星单元并存(bench 同名
# 1/2/3★ 三副本)时 read_star 星级-槽位映射逐帧抖动(不死途 3★→1★,
# episode ×3 全部「连续 2 帧」形态),「回退即采新」让单帧抖动直进
# tracked 主账 → 3★ 合成判断与 buy_expect 对账被污染(3★ 合成线整局
# 未落地实证)。修法两层正交:
# 1. **槽位锚定**:星级差逐槽判定,锚 = (域, 物理槽号) + 规范名同名——
#    bench 权威槽位 = 槽位表下标+1(ADR-0605 §5.2 信息位为派生);
#    deployed = 表下标经 deployed_row_slot 换 (排, 排内槽号)(ADR-0392)。
#    锚上身份变换(空槽落新单元/换人)= 单元更替事实,星级随身份直采。
# 2. **两帧一致才采新**:锚上星读 ≠ tracked = 候选(保旧写账 + 抖动
#    台账行 surface='star');连续两帧候选同值才采新(升/降同门,银狼
#    升费形态无豁免)。「连续」以锚每帧在-read 为前提:候选锚在本帧
#    读侧未出现(部分缺读)或整帧双空读(守卫早退)即清除其候选——
#    缺读 = 证据中断,两帧重计;候选跨缺读帧存活会把门击穿成「隔缺读
#    帧两读一致即采新」的同值单帧假确认。合成特效窗内读数物理不可信:
#    保旧且不登记候选、不确认(冻结非清零,帧态维 ADR-0420,与时间维
#    两帧门正交)。
# 候选态宿主 = 按局身份 session 的旁表(WeakKeyDictionary 主路,同
# game_state_of 模式;新局新 session = 天然清零,无跨局串染面。GameState
# 本体是 eq-dataclass 不可哈希,故不以其为键;不可弱引用桩面回退 id 键
# 旁表,超限清空只保在册——同 _DEPLOYED_2SRC_RUN_COUNTS 纪律)。
# 保旧就地改写读对象 star,其后的纠漂快照与写回消费门后值——单帧抖动
# 不进 drift 判定(不产「对账纠漂」噪声行),同帧容器席位视图观察写端
# (备战帧 director 消费同一批读对象)同得保旧值。
_STAR_GATES: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
#: 桩面兜底第二级:不可弱引用 session 的 id 键旁表(驻留上限见下)。
_STAR_GATES_BY_ID: dict[int, dict] = {}
#: id 键旁表驻留上限(超限清空只保新入——测试桩面数量级,生产不走此路)。
_STAR_GATES_BY_ID_MAX: int = 32


def _star_gate_pending(session) -> dict:
    """星级抖动候选态取口(局身份旁表;缺失惰性建)。"""
    try:
        pending = _STAR_GATES.get(session)
    except TypeError:   # 不可弱引用/不可哈希对象(测试桩面)
        pending = _STAR_GATES_BY_ID.get(id(session))
        if pending is None:
            if len(_STAR_GATES_BY_ID) >= _STAR_GATES_BY_ID_MAX:
                _STAR_GATES_BY_ID.clear()
            pending = {}
            _STAR_GATES_BY_ID[id(session)] = pending
        return pending
    if pending is None:
        pending = {}
        _STAR_GATES[session] = pending
    return pending


def _gate_star_jitter(session, bench, deployed, screen, *,
                      source: str) -> None:
    """星级抖动门本体(语义与出处见上方门注释块)。

    就地改写 ``bench``/``deployed`` 读对象的 ``star`` = 保旧写账;候选态
    按局身份旁表存(键 = (域, 槽号, 规范名))。锚上身份未锚定
    (空槽/换人)与读失败侧(None)不辖,候选随锚作废防陈旧假确认;
    读侧已取得但锚未出现(部分缺读)= 证据中断,该锚候选清除重计
    (整帧双空读的候选清除在对账守卫分支,本函数不可达)。
    """
    gs = game_state_of(session)
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        deployed_row_slot,
    )
    pending = _star_gate_pending(session)
    frozen = is_merge_effect_window(screen)
    for reads, tracked_table, domain in (
            (bench, gs.tracked_books.bench, 'bench'),
            (deployed, gs.tracked_books.deployed, 'deployed')):
        if reads is None:
            continue   # 读失败侧无读数无证据:候选态保持,不辖
        tracked_at: dict[tuple[str, int], object] = {}
        for i, t in enumerate(tracked_table or []):
            if t is None:
                continue
            # 权威锚 = 槽位表下标(bench 下标+1 = 物理槽号;deployed 下标
            # → (排, 排内槽号)),信息位(槽号字段)为派生不作锚。
            tracked_at[(domain, i + 1) if domain == 'bench'
                       else deployed_row_slot(i)] = t
        # 缺读 = 证据中断:本帧读侧未出现的锚清除其星级候选(两帧重计)。
        # 候选键首元分域(bench = 'bench';deployed = 排名 front/back),
        # 只清本域候选——他域可能本帧整体读失败(None,照旧不辖)。
        # 缺读帧不清会让候选原样存活,同值复现帧单帧假确认(击穿
        # 「连续两帧一致」契约)。
        _in_bench = domain == 'bench'
        _seen = {((domain, bc.slot) if _in_bench
                  else (bc.position_pref, bc.slot))
                 for bc in reads if bc is not None}
        for k in [k for k in pending
                  if (k[0] == 'bench') == _in_bench
                  and (k[0], k[1]) not in _seen]:
            del pending[k]
        for bc in reads:
            if bc is None:
                continue
            anchor = ((domain, bc.slot) if domain == 'bench'
                      else (bc.position_pref, bc.slot))
            t = tracked_at.get(anchor)
            if t is None or not bc.char_id or bc.char_id != t.char_id:
                # 锚上身份未锚定 = 单元更替,星级随身份直采;该锚旧候选
                # 作废(防陈旧候选对后续同名单元假确认)。
                for k in [k for k in pending
                          if k[0] == anchor[0] and k[1] == anchor[1]]:
                    del pending[k]
                continue
            if bc.star == t.star:
                pending.pop(anchor + (bc.char_id,), None)
                continue
            key = anchor + (bc.char_id,)
            if not frozen and pending.get(key) == bc.star:
                pending.pop(key, None)   # 连续两帧同值 → 采新(bc.star 保持)
                continue
            if not frozen:
                pending[key] = bc.star   # 首帧差:登记候选,下帧同值才采新
            held = bc.star
            bc.star = t.star             # 保旧写账:就地改写读对象
            if frozen:
                _verdict = ('保旧-合成特效窗(窗内星读不可信,不计两帧;'
                            f'source={source})')
            else:
                _verdict = ('保旧-星级抖动门(单帧差弃读,两帧一致才采新;'
                            f'source={source})')
            _conflict('star', t.star, held, screen,
                      verdict=_verdict,
                      source=source, char=bc.char_id,
                      slot=anchor[1], domain=anchor[0])


#: 星级稳定性口径沿革:终态契约 §A 曾以「回退即采新」替换旧 N=2 防抖
#: (旧确认门被「连续 2 帧」抖动 episode 骗过,2026-09-15 局深检
#: .debug/currency_war/deep_review/run_20260915_054718.md §5 三次 episode
#: 实证);识别优化批以「槽位锚定 + 两帧一致才采新」取代采新口径
#:(门本体 = :func:`_gate_star_jitter`,与本门特效窗判别正交合并:
#: 时间维两帧一致 + 帧态维窗内冻结)。


def _merge_equips(old_list, new_list) -> list:
    """对账合并语义(ADR-0387,对账覆盖装备):char_id 续接保留 equips。

    断点实锤:对账写回若**整批替换** tracked 主账 deployed 面(新读对象
    equips=[] 默认,宿主现 = GameState.tracked_books),则 ``deploy_bench._
    snapshot_equips_into_tracking`` 写入的装备在下次对账即被冲(希儿装备
    闪烁实证——当年经决策行快照显影:round6 三条快照仅一条有装备)。

    修法:按 char_id 把**旧 tracking 的 equips 续接到新读对象**(同名多副本
    逐个配对消耗,次序无关);新读自带的非空 equips(画面真值,如 deploy_bench
    快照后传参)优先保留不覆盖;旧有新无(角色离场)自然丢弃。
    """
    old_eq: dict[str, list[list[str]]] = {}
    for bc in (old_list or []):
        if bc is not None and bc.char_id:
            old_eq.setdefault(bc.char_id, []).append(
                list(getattr(bc, 'equips', None) or []))
    out = []
    for bc in (new_list or []):
        if bc is not None and getattr(bc, 'char_id', ''):
            if not getattr(bc, 'equips', None):
                pools = old_eq.get(bc.char_id)
                if pools:
                    bc.equips = pools.pop(0)   # 同名逐个配对消耗
        out.append(bc)
    return out


def reconcile_tracking(session, bench, deployed, screen=None, *,
                       source: str = 'reconcile', ctx=None) -> bool:
    """tracking 对账统一入口:新 SIFT 读 vs 旧 session tracking,守卫后写回。

    守卫(审计 #11/#12):
    - **双空读守卫**(M14 实锤):新读 bench/deployed 双空 + 前值非空 = 疑 SIFT 过渡帧
      → 保旧不写(空读是读失败,不是「板真没了」);
    - **漂移留证**:新旧不一致 → obs_conflict(裁决=采新-对账纠漂)+ [cw!] 日志;
      一致 → 静默(常态无噪声)。

    (star 回退停机钩子已随「星回退处置归观察对账」批退役,2026-09-16:
    merge 预估星被实读证伪 → observe-vs-logic 对账承接,不再单设钩子。)

    Args:
        session: StrategySession(tracked_bench_chars/tracked_deployed 被写回)
        bench/deployed: 新读 list[BenchChar](None = 读失败,不写该侧)
        screen: 冲突帧(传则 obs_conflict 存去重截图)
        source: 证据行来源标记(deploy_bench/director)
        ctx: SrContext(兼容形参;star 回退停机钩子已随「星回退处置归观察
            对账」批退役,不再消费)
        星级抖动门(槽位锚定 + 两帧一致才采新,单帧差保旧写账 + surface=
        'star' 台账行);合成特效窗内星读不可信(冻结,不计两帧)——窗判别
        实现经模块级 ``set_merge_effect_gate`` 注入(分包矩阵禁 kernel→obs
        直依),缺省关 = 无窗(纯两帧时间维门)。

    Returns:
        是否发生了写回(False = 守卫拦截保旧)。边界:槽号健康门拒绝
        (bench 侧保旧)**不**计入 False——该门只辖 bench 写回分支,
        deployed 侧照常写回,函数整体仍返回 True;False 仅双空读守卫
        与 session 为 None 两处早退产生。
    """
    if session is None:
        return False
    # 形状契约(ADR-0316):tracked_bench_chars 在买牌后被
    # mutate_bench_deployed→pad_bench 就地 pad 成定长 9 槽**含 None**
    # (槽位表语义写入端)——本消费端若假设紧凑无 None 即双写冲突
    # (曾致验证局数百次 AttributeError 崩溃-重派循环)。
    # 守卫:跳过 None 槽(空槽在对账语义里=无信息,不是冲突)。
    # 旧账基准 = game state 簿记(宿主 = GameState.
    # tracked_books,本函数 = game state 层内部实现,就地处置)。
    _books = game_state_of(session).tracked_books
    old_b = [(bc.char_id, bc.star) for bc in _books.bench
             if bc is not None]
    old_d = [(bc.char_id, bc.star) for bc in _books.deployed
             if bc is not None]
    if not bench and not deployed and (old_b or old_d):
        log.warning(f'[cw!][{source}] 对账跳过:SIFT 双空读(疑过渡帧)+前值非空 → 保旧 tracking')
        _conflict('tracking', f'{old_b}|{old_d}', '[]|[]', screen,
                  verdict='保旧-双空读守卫(疑SIFT过渡帧)', source=source)
        # 双空读 = 全帧无读证据,星级候选一并清除(缺读 = 证据中断,两帧
        # 重计):守卫早退绕过星级门,候选若原样存活,缺读后同值复现帧
        # 会单帧假确认(击穿「连续两帧一致」契约)。
        _star_gate_pending(session).clear()
        return False
    new_b = [(bc.char_id, bc.star) for bc in (bench or [])]
    new_d = [(bc.char_id, bc.star) for bc in (deployed or [])]
    # 星级抖动门(槽位锚定 + 两帧一致才采新):单帧星读抖动保旧写账
    #(就地改写读对象 star)+ 抖动台账行 surface='star';合成特效窗内
    # 星读不可信(冻结不计两帧)。门后快照才作纠漂判定与写回基准——
    # 保旧锚读账一致,不产「对账纠漂」噪声行(出处见 _gate_star_jitter
    # 上方门注释块)。
    _gate_star_jitter(session, bench, deployed, screen,
                      source=source)
    # 纠漂判定与日志必须取**门后**快照(门可能原地改读对象 star,
    # 改前快照会误导排障)。bench/deployed 入参是 SIFT 紧凑列表
    # (无 None),但入参若被上游 pad 过则守卫之(同形状契约)。
    new_b = [(bc.char_id, bc.star) for bc in (bench or []) if bc is not None]
    new_d = [(bc.char_id, bc.star) for bc in (deployed or []) if bc is not None]
    drifted = (old_b != new_b) or (old_d != new_d)
    # 布局代次写回事实位:bench 侧是否实际写回(健康门通过)。
    # drifted 分支据此决定是否递增 bench_layout_epoch——deployed 驱动的
    # 纠漂不递增(bench 布局未变);误递增无害(重播种幂等)、漏递增有害
    #(布局变化无人知晓),故取「bench 写回 ∧ drifted」。
    _bench_written = False
    if bench is not None:
        # ADR-0646 S2 主修:写回经 bench_from_compact 重建槽位表——
        # 与下方 deployed 侧 deployed_from_compact 同构(ADR-0392 单一源
        # 适配先例,bench 侧为同构修法补齐,非发明新机制)。SIFT 读的
        # slot = 画面物理槽号(read_bench_chars→identify_slots 逐槽赋值,
        # 与读序同帧同源;亲读结论见 ADR-0646),重建后列表布局=画面布局、
        # slot=下标+1 天然一致,紧凑态从写入端消失,两域播种自动同源——
        # 消灭 tracked 下标布局 vs BenchChar.slot 脱节的持续制造点
        #(本函数旧写回直拷 SIFT 紧凑列表,违反 ADR-0316 形状契约)。
        # 前置槽号健康门:
        # 占用槽号唯一 ∧ 全在 1..BENCH_CAPACITY——把 bench_from_compact 对
        # 无效槽号的静默 fallback(冲突走 bench_place 首空槽)在写回点升级
        # 为显式拒绝,防脏读数固化为形状自洽的槽位表(布局错而守卫恒过,
        # 比现状更难发现)。违者拒绝写回保旧+留证:经 _conflict 通道
        #(obs_conflict 行经旁路进缺陷台账;kernel 层落账走出口约束)。
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            BENCH_CAPACITY,
            bench_from_compact,
            bench_occupied_slot_nos,
            bench_slots_healthy,
        )
        _slots = bench_occupied_slot_nos(bench)
        _healthy = bench_slots_healthy(_slots)
        if _healthy:
            # 锚定写回 = 观察态退出点:屏幕真值写回成功即「已观察」
            # ——容器观察态字段置 True(策略商店门放行;bench 读失败/双空
            # 读守卫/槽号健康门拒绝不走此处 = 保持未观察)。best-effort:
            # 容器缺席/写失败不阻断对账主链(簿记已照常写回)。
            game_state_of(session).tracked_books.bench = bench_from_compact(
                _merge_equips(_books.bench, bench))
            _bench_written = True
            try:
                game_state_of(session).write_logic(
                    game_state_of(session).tracked_account_observed, True,
                    produced_by=f'reconcile_tracking:{source}',
                    evidence='observation_anchor',
                    sig=ChannelSig(family='logic_action',
                                   actor='CwReconcile', mode='compute'))
            except Exception as _e:  # noqa: BLE001  观察态置位不阻断对账
                log.warning(f'[cw!][{source}] 观察态置位失败(不阻断): {_e}')
        else:
            # 留证排序 str 化:健康门防御的对象正是非 int 槽号,拒绝分支若
            # 对混型列表(如 [None, 2])直接 sorted 会先 TypeError——防御
            # 分支自伤,拒绝留证与保旧都未完成;此处取 str 化保排序
            # 可读且混型安全)。
            _slots_disp = sorted(map(str, _slots))
            log.warning(f'[cw!][{source}] 对账写回拒绝:bench 槽号不健康'
                        f'(唯一∧1..{BENCH_CAPACITY})slots={_slots_disp}'
                        f' → 保旧 tracking(脏读数不固化为槽位表)')
            _conflict('bench', '占用槽号唯一∧全在1..9',
                      f'slots={_slots_disp}', screen,
                      verdict=('保旧-写回槽号健康门拒绝(SIFT 读 slot 重复/'
                               '越界,拒写防脏布局固化为槽位表;'
                               'ADR-0646;处理:频发→查 SIFT 槽位识别)'),
                      source=source)
    if deployed is not None:
        # ADR-0392:tracked_deployed 是槽位表——_merge_equips 出紧缩占用序,
        # 写回前经 deployed_from_compact 转槽位表(单一源适配)。
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            deployed_from_compact,
        )
        game_state_of(session).tracked_books.deployed = deployed_from_compact(
            _merge_equips(game_state_of(session).tracked_books.deployed,
                          deployed))
    if drifted:
        log.warning(f'[cw!][{source}] 对账纠漂(read≠tracking):bench {old_b}→{new_b} |'
                    f' deployed {old_d}→{new_d}')
        _conflict('tracking', f'{old_b}|{old_d}', f'{new_b}|{new_d}', screen,
                  verdict='采新-对账纠漂(SIFT 实读)', source=source)
        # ADR-0646 S3:布局代次递增(churn 事件通道最小面)。对账纠漂
        # = 布局可能重排,visit 内未来消费者(单动作循环每动作消费前检差)
        # 据此截断在飞计划并按 tracked 重播种。当前架构 reconcile 均在
        # visit 外跑,恒无消费者(S2+S1 后 epoch 只递增不消费,纯未来防御:
        # 防 visit 中段未来引入读屏/对账点时布局变化无人知晓)。
        if _bench_written:
            game_state_of(session).exec_books.bench_layout_epoch += 1
    return True


# (终态契约 §A:hp 同域上行留证阈值/下行守卫三助手(_battle_facts_between/
#  _outcome_is_no_loss/_reject_down)已随 session 防御锚退役删除——
#  行为变化登记 design §1.3,实机失准走识别优化批。)


def reconcile_hp(session, new_hp: int | None, screen=None, *,
                 source: str = 'read_game_state',
                 node_t: int | None = None) -> tuple[int | None, bool]:
    """hp 对账统一入口(终态契约 §A 简化形态)。

    旧三层(保旧不写沿用/下行守卫/复现确认/帧龄门)随 session 防御锚
    (last_hp_real/last_hp_real_node/hp_suspect)退役删除——「上一真值」
    职责由 gs.hp 结算覆盖写端 + carried 语义承载(该三层 = ADR-0282 hp
    三层设计「读不到保旧沿用 last_hp_real」;ADR 档案目录已删,原文 =
    git 历史 docs/develop/currency_war/decisions/0282-hp-three-layers.md。
    定谳:结算观测 hp_after 与沿用锚的先后语义随退役消解——结算覆盖是
    hp 唯一真值入口,本读侧无锚可遮蔽之;行为变化登记 design §1.3:
    失读窗不再有锚补,实机识别失准走识别优化批)。

    保留两支:
    - 开局初值表先验(ADR-0559):读不到 → 实证档先验(readable=False,
      真值帧到达即被覆盖);先验输入 briefing_*/enemy_difficulty 待 T-3
      重复账退役换源 gs 正本;
    - 真值帧直传(真值帧是物理读数,判读侧消费证据)。

    Args:
        session: StrategySession(开局先验输入面;None=离线/测试,只透传)
        new_hp: read_hp_opt 现读(None=读不到,shop 开态血量区空)
        screen/source/node_t: 留证兼容形参(守卫删除后 node_t 不再消费)

    Returns:
        (决策用 hp, 是否真读):真值帧=(新读, True);读不到=(先验或
        None, False)——诚实未知(ADR-0491,不再 100 兜底)。
    """
    if new_hp is None:
        # 开局全无真值 → 遥测实证的初值表先验(ADR-0559;实证档 A8/108:
        # 基础 82、「开局不利」62;无实证档 → None 诚实未知,ADR-0491)。
        # 先验非真读,readable=False;真值帧到达即被观察覆盖。
        # (终态契约 §B:三先验输入全读容器——briefing 写端直入
        #  gs.enemy_affixes/selected_difficulty/enemy_difficulty。)
        prior = (opening_hp_prior(
            game_state_of(session).enemy_affixes.value,
            (game_state_of(session).selected_difficulty.value or '')
            if session is not None else '',
            game_state_of(session).enemy_difficulty.value)
            if session is not None else None)
        if prior is not None:
            log.info(f'[cw][{source}] hp 开局无真值 → 初值表先验 {prior}'
                     f'(词缀={sorted(set(game_state_of(session).enemy_affixes.value or []))};'
                     f'ADR-0559,readable=False,真值帧到达即被覆盖)')
            return prior, False
        return None, False   # 无实证档(其他难度/未读到难度)→ None 诚实未知(ADR-0491)
    return new_hp, True


def _conflict(field: str, old, new, screen, *, verdict: str, source: str,
              **ctx) -> None:
    """obs_conflict 封装(best-effort,导入失败/异常不阻塞)。**ctx 透传(如 char=)。"""
    try:
        from sr_od.application.currency_war.kernel.cw_observe import obs_conflict
        obs_conflict(field, old, new, screen, verdict=verdict, source=source, **ctx)
    except Exception:  # noqa: BLE001  留证 best-effort
        pass
