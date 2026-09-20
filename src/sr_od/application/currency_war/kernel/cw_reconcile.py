"""tracking 对账公共层(观察冲突审计 P0 #12)。

两处对账实现(deploy_bench._reconcile_tracking / cw_screen_prep._reconcile_tracking)同语义
但强弱不一 —— director 版有空读守卫(M14 实锤)+截图留证,deploy_bench 版直接覆盖(过渡帧
双空读会污染 tracking)→ bug 温床。本模块抽公共 helper:统一守卫 + obs_conflict 证据链。
"""
from __future__ import annotations

import weakref
from dataclasses import replace

from cv2.typing import MatLike

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    BenchView,
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
# 保旧经门后副本承载(frozen 容器形状不可就地改写,P6 直产载体:replace
# 新构造),其后的纠漂快照与写回消费门后副本——单帧抖动不进 drift 判定
# (不产「对账纠漂」噪声行),同帧容器席位视图观察写端(备战帧 director
# 消费门后副本)同得保旧值。
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


def _tracked_identity(t) -> tuple[str, int, int] | None:
    """tracked 条目身份读(bench 侧 BenchSlot → 内嵌 Unit;deployed 侧
    Unit 直读)。返回 (char_id, star, slot 信息位);无身份(占位/空)→ None。"""
    kind = getattr(t, 'kind', None)
    if kind is not None:
        if kind != 'unit' or getattr(t, 'unit', None) is None:
            return None
        t = t.unit
    cid = str(getattr(t, 'char_id', '') or '')
    return (cid, int(getattr(t, 'star', 1) or 1),
            int(getattr(t, 'slot', 0) or 0))


def _bench_read_entries(view: BenchView | None) -> list[tuple]:
    """观察视图 → 门/签名用的读条目 ``[(anchor, char_id, star, unit|None)]``。

    [索引定义] anchor = ('bench', 物理槽号 1 基)(星级门锚 = 物理槽,ADR-0605
    §5.2 权威槽位 = 表下标、信息位为派生,下标+1 即槽号);占用槽按视图序
    (下标升序)排列;占位件槽(kind ≠ unit/empty)char_id=''(与旧读链
    is_item_slot 空名位同形,门内走「无身份 → 清候选」分支)。"""
    if view is None:
        return []
    out: list[tuple] = []
    for i, s in enumerate(view.slots):
        if s.kind == 'empty':
            continue
        u = s.unit if s.kind == 'unit' else None
        out.append((('bench', i + 1),
                    str(getattr(u, 'char_id', '') or '') if u else '',
                    int(getattr(u, 'star', 1) or 1) if u else 1,
                    u))
    return out


def _deployed_read_entries(rows) -> list[tuple]:
    """观察行域 → 门/签名用的读条目(形态同 :func:`_bench_read_entries`)。

    [索引定义] anchor = (排 'front'|'back', 排内 1 基槽号);条目序 = 前排
    行序 + 后排行序(与旧 read_deployed_chars 的 front+back 拼接读序一致,
    漂移签名按序比较不受载体影响)。"""
    if rows is None:
        return []
    out: list[tuple] = []
    for row, units in (('front', rows[0]), ('back', rows[1])):
        for u in (units or []):
            out.append(((row, int(getattr(u, 'slot', 0) or 0)),
                        str(getattr(u, 'char_id', '') or ''),
                        int(getattr(u, 'star', 1) or 1),
                        u))
    return out


def _apply_star_holds(reads, holds: dict[int, int]):
    """星级保旧副本(frozen 容器形状不可就地改写 → replace 新构造)。

    ``holds`` 键 = id(Unit 读对象),值 = 保旧星;命中读对象逐一换星,
    其余槽/行原样(同引用)。无保旧项原样返回(零拷贝快路径)。"""
    if not holds:
        return reads
    if isinstance(reads, BenchView):
        slots = [BenchSlot(kind='unit', unit=replace(s.unit, star=holds[id(s.unit)]))
                 if (s.kind == 'unit' and s.unit is not None
                     and id(s.unit) in holds) else s
                 for s in reads.slots]
        return BenchView(slots=slots, capacity=reads.capacity)
    front = [replace(u, star=holds[id(u)]) if id(u) in holds else u
             for u in (reads[0] or [])]
    back = [replace(u, star=holds[id(u)]) if id(u) in holds else u
            for u in (reads[1] or [])]
    return front, back


def _gate_star_jitter(session, bench, deployed, screen, *,
                      source: str) -> tuple:
    """星级抖动门本体(语义与出处见上方门注释块)。

    P6 载体适配:读对象为 frozen 容器形状(BenchView/Unit 行),不可就地
    改写 star —— 保旧写账改经 **replace 副本** 承载(返回门后副本),语义
    与旧「就地改写读对象 star」等价:单帧抖动不进 drift 判定与写回,同帧
    容器席位视图观察写端(director 消费门后副本)同得保旧值。候选态
    按局身份旁表存(键 = (域, 槽号, 规范名))。锚上身份未锚定
    (空槽/换人/占位件)与读失败侧(None)不辖,候选随锚作废防陈旧假确认;
    读侧已取得但锚未出现(部分缺读)= 证据中断,该锚候选清除重计
    (整帧双空读的候选清除在对账守卫分支,本函数不可达)。

    Returns:
        (门后 bench 视图, 门后 deployed 行)。
    """
    gs = game_state_of(session)
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        deployed_row_slot,
    )
    pending = _star_gate_pending(session)
    frozen = is_merge_effect_window(screen)
    out: dict[str, object] = {}
    for domain, reads, tracked_table in (
            ('bench', bench, gs.tracked_books.bench),
            ('deployed', deployed, gs.tracked_books.deployed)):
        if reads is None:
            out[domain] = reads
            continue   # 读失败侧无读数无证据:候选态保持,不辖
        entries = (_bench_read_entries(reads) if domain == 'bench'
                   else _deployed_read_entries(reads))
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
        _seen = {e[0] for e in entries}
        for k in [k for k in pending
                  if (k[0] == 'bench') == _in_bench
                  and (k[0], k[1]) not in _seen]:
            del pending[k]
        holds: dict[int, int] = {}   # id(读 Unit) → 保旧星
        for anchor, cid, star, unit in entries:
            t = tracked_at.get(anchor)
            _tident = _tracked_identity(t) if t is not None else None
            if t is None or _tident is None or not cid \
                    or cid != _tident[0]:
                # 锚上身份未锚定 = 单元更替,星级随身份直采;该锚旧候选
                # 作废(防陈旧候选对后续同名单元假确认)。
                for k in [k for k in pending
                          if k[0] == anchor[0] and k[1] == anchor[1]]:
                    del pending[k]
                continue
            if star == _tident[1]:
                pending.pop(anchor + (cid,), None)
                continue
            key = anchor + (cid,)
            if not frozen and pending.get(key) == star:
                pending.pop(key, None)   # 连续两帧同值 → 采新(读星保持)
                continue
            if not frozen:
                pending[key] = star   # 首帧差:登记候选,下帧同值才采新
            if unit is not None:
                holds[id(unit)] = _tident[1]   # 保旧写账:门后副本换星
            _conflict('star', _tident[1], star, screen,
                      verdict=('保旧-合成特效窗(窗内星读不可信,不计两帧;'
                               f'source={source})' if frozen else
                               '保旧-星级抖动门(单帧差弃读,两帧一致才采新;'
                               f'source={source})'),
                      source=source, char=cid,
                      slot=anchor[1], domain=anchor[0])
        out[domain] = _apply_star_holds(reads, holds)
    return out['bench'], out['deployed']


#: 星级稳定性口径沿革:终态契约 §A 曾以「回退即采新」替换旧 N=2 防抖
#: (旧确认门被「连续 2 帧」抖动 episode 骗过,2026-09-15 局深检
#: .debug/currency_war/deep_review/run_20260915_054718.md §5 三次 episode
#: 实证);识别优化批以「槽位锚定 + 两帧一致才采新」取代采新口径
#:(门本体 = :func:`_gate_star_jitter`,与本门特效窗判别正交合并:
#: 时间维两帧一致 + 帧态维窗内冻结)。


def _old_equips_pools(old_list) -> dict[str, list[list[str]]]:
    """旧 tracked 表的装备池(char_id → 按表序的 equips 队列;ADR-0387)。

    对账覆盖装备的历史病灶:对账写回若整批替换 tracked 主账(新读 equips=[]
    默认),动作链写入的装备在下次对账即被冲(希儿装备闪烁实证)。修法 =
    旧账 equips 按 char_id 组池,新读按序续接(同名多副本逐个配对消耗,
    次序无关)。"""
    pools: dict[str, list[list[str]]] = {}
    for t in (old_list or []):
        if t is None:
            continue
        ident = _tracked_identity(t)
        if ident is not None and ident[0]:
            pools.setdefault(ident[0], []).append(
                list(getattr(t.unit if hasattr(t, 'kind') else t,
                             'equips', None) or []))
    return pools


def _continue_equips_bench(old_list, view: BenchView | None) -> BenchView | None:
    """对账合并语义(ADR-0387)·bench 侧:旧 tracked equips 按 char_id 续接
    到新读视图的 unit 槽(frozen 形状 → replace 新构造)。

    新读自带的非空 equips(画面真值)优先保留不覆盖;旧有新无(角色离场)
    自然丢弃。装备续接结果随门后副本返回 —— 同帧容器观察写端消费同一副本,
    与旧「就地改写读对象 equips」的同帧共享语义等价。"""
    if view is None:
        return None
    pools = _old_equips_pools(old_list)
    slots = []
    for s in view.slots:
        if (s.kind == 'unit' and s.unit is not None
                and not (s.unit.equips or [])):
            eq = pools.get(s.unit.char_id)
            if eq:
                s = BenchSlot(kind='unit',
                              unit=replace(s.unit, equips=eq.pop(0)))
        slots.append(s)
    return BenchView(slots=slots, capacity=view.capacity)


def _continue_equips_rows(old_list, rows):
    """对账合并语义(ADR-0387)·deployed 侧:旧 tracked equips 续接到新读
    行域(frozen replace)。续接结果只进 tracked 写回(容器行域观察写端
    恒空表,不造假值 —— 旧 deployed_rows_from_obs 同款边界申报)。"""
    if rows is None:
        return None
    pools = _old_equips_pools(old_list)

    def _row(units):
        out = []
        for u in (units or []):
            if not (getattr(u, 'equips', None) or []):
                eq = pools.get(str(getattr(u, 'char_id', '') or ''))
                if eq:
                    u = replace(u, equips=eq.pop(0))
            out.append(u)
        return out

    return _row(rows[0]), _row(rows[1])


def reconcile_tracking(session, bench: BenchView | None,
                       deployed, screen=None, *,
                       source: str = 'reconcile', ctx=None,
                       ) -> tuple[bool, BenchView | None, tuple | None]:
    """tracking 对账统一入口:新 SIFT 读 vs 旧 session tracking,守卫后写回。

    P6 观察链直产:入参即容器形状 —— bench = :class:`BenchView`(占位件
    kind 识别期细分,写回不再经 orig_view 回查/降级);deployed =
    (前排 Unit 行, 后排 Unit 行)。None = 该侧失读(不写该侧、星级门不辖、
    候选态保持);空视图/双空行 = 空读(可触发双空读守卫/清账,与旧紧缩
    空表语义一致)。

    守卫(审计 #11/#12):
    - **双空读守卫**(M14 实锤):新读 bench/deployed 双空 + 前值非空 = 疑 SIFT 过渡帧
      → 保旧不写(空读是读失败,不是「板真没了」);
    - **漂移留证**:新旧不一致 → obs_conflict(裁决=采新-对账纠漂)+ [cw!] 日志;
      一致 → 静默(常态无噪声)。

    (star 回退停机钩子已随「星回退处置归观察对账」批退役,2026-09-16:
    merge 预估星被实读证伪 → observe-vs-logic 对账承接,不再单设钩子。)

    Args:
        session: StrategySession(tracked_books.bench/deployed 被写回)
        bench/deployed: 新读容器形状(None = 该侧失读,不写)
        screen: 冲突帧(传则 obs_conflict 存去重截图)
        source: 证据行来源标记(deploy_bench/director)
        ctx: SrContext(兼容形参;star 回退停机钩子已随「星回退处置归观察
            对账」批退役,不再消费)
        星级抖动门(槽位锚定 + 两帧一致才采新,单帧差保旧写账 + surface=
        'star' 台账行);合成特效窗内星读不可信(冻结,不计两帧)——窗判别
        实现经模块级 ``set_merge_effect_gate`` 注入(分包矩阵禁 kernel→obs
        直依),缺省关 = 无窗(纯两帧时间维门)。

    Returns:
        ``(是否写回, 门后 bench 视图, 门后 deployed 行)``。门后副本 =
        星级抖动门保旧写账 + 装备续接后的读副本(frozen 形状以 replace
        承载与旧「就地改写读对象」等价的同帧共享语义),director 同帧
        容器观察写端消费门后值。是否写回:False 仅双空读守卫与 session
        为 None 两处早退产生(门保旧仍属写回,计数 True)。
    """
    if session is None:
        return False, bench, deployed
    # 旧账基准 = game state 簿记(宿主 = GameState.tracked_books,本函数 =
    # game state 层内部实现,就地处置)。P1 tracked 形状:bench =
    # BenchSlot | None(unit 才有身份,占位件以 ('',1) 入漂移基准——与旧
    # is_item_slot 空名位同形)/ deployed = Unit | None。
    _books = game_state_of(session).tracked_books

    def _tracked_sig(entries) -> list:
        out = []
        for t in (entries or []):
            if t is None:
                continue
            ident = _tracked_identity(t)
            out.append((ident[0], ident[1]) if ident is not None else ('', 1))
        return out

    old_b = _tracked_sig(_books.bench)
    old_d = _tracked_sig(_books.deployed)
    _bench_entries = _bench_read_entries(bench)
    _dep_entries = _deployed_read_entries(deployed)
    if not _bench_entries and not _dep_entries and (old_b or old_d):
        log.warning(f'[cw!][{source}] 对账跳过:SIFT 双空读(疑过渡帧)+前值非空 → 保旧 tracking')
        _conflict('tracking', f'{old_b}|{old_d}', '[]|[]', screen,
                  verdict='保旧-双空读守卫(疑SIFT过渡帧)', source=source)
        # 双空读 = 全帧无读证据,星级候选一并清除(缺读 = 证据中断,两帧
        # 重计):守卫早退绕过星级门,候选若原样存活,缺读后同值复现帧
        # 会单帧假确认(击穿「连续两帧一致」契约)。
        _star_gate_pending(session).clear()
        return False, bench, deployed
    # 星级抖动门(槽位锚定 + 两帧一致才采新):门后副本供纠漂判定、写回
    # 与同帧容器观察写端 —— 保旧锚读账一致,不产「对账纠漂」噪声行
    #(出处见 _gate_star_jitter 上方门注释块)。
    bench, deployed = _gate_star_jitter(session, bench, deployed, screen,
                                        source=source)
    new_b = [((e[1], e[2]) if e[3] is not None else ('', 1))
             for e in _bench_read_entries(bench)]
    new_d = [(e[1], e[2]) for e in _deployed_read_entries(deployed)]
    drifted = (old_b != new_b) or (old_d != new_d)
    if bench is not None:
        # P6 直产写回 = 视图槽表直落:占用槽(含占位件 kind)原样入 tracked,
        # 空槽 → None 洞(ADR-0316 保洞)。占位件 kind 随读帧细分直达
        # (P4 遗留「缺观察帧降级 supply_box」边界随直产消除)。槽号 =
        # 下标+1 结构性健康(直产读链槽号来自建档 rect 枚举,ADR-0646
        # 「无守卫槽号」面随形状消失,旧写回槽号健康门拒绝分支失去可达
        # 输入,随直产退役)。入口防御 pad 到定长(空视图 = 空读载体,
        # 与旧 bench_from_compact([]) 的定长输出契约一致)。
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            BENCH_CAPACITY,
        )
        _bench_final = _continue_equips_bench(_books.bench, bench)
        _table = [s if s.kind != 'empty' else None for s in _bench_final.slots]
        while len(_table) < BENCH_CAPACITY:
            _table.append(None)
        game_state_of(session).tracked_books.bench = _table
        bench = _bench_final
        try:
            # 锚定写回 = 观察态退出点:屏幕真值写回成功即「已观察」
            # ——容器观察态字段置 True(策略商店门放行;bench 读失败/双空
            # 读守卫不走此处 = 保持未观察)。best-effort:容器缺席/写失败
            # 不阻断对账主链(簿记已照常写回)。
            game_state_of(session).write_logic(
                game_state_of(session).tracked_account_observed, True,
                produced_by=f'reconcile_tracking:{source}',
                evidence='observation_anchor',
                sig=ChannelSig(family='logic_action',
                               actor='CwReconcile', mode='compute'))
        except Exception as _e:  # noqa: BLE001  观察态置位不阻断对账
            log.warning(f'[cw!][{source}] 观察态置位失败(不阻断): {_e}')
    if deployed is not None:
        # P6 直产写回 = 行域 → 下标工作表(容器原生派生单一源,§2.1;元素
        # 即行内 Unit,零中间形),装备续接只进 tracked(容器行域观察写端
        # 恒空表)。
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            deployed_rows_to_indexed,
        )
        _front, _back = _continue_equips_rows(
            game_state_of(session).tracked_books.deployed, deployed)
        game_state_of(session).tracked_books.deployed = \
            deployed_rows_to_indexed(_front, _back)
    if drifted:
        log.warning(f'[cw!][{source}] 对账纠漂(read≠tracking):bench {old_b}→{new_b} |'
                    f' deployed {old_d}→{new_d}')
        _conflict('tracking', f'{old_b}|{old_d}', f'{new_b}|{new_d}', screen,
                  verdict='采新-对账纠漂(SIFT 实读)', source=source)
    return True, bench, deployed


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
