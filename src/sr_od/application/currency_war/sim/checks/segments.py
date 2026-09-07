"""段级检查(seg_*)与段注册表/执行器(分包期6 拆分)。"""

from __future__ import annotations

from sr_od.application.currency_war.sim.checks.runtime import _combat_streak_by_round

# =====================================================================
# --- 段级检查表 _SEGMENT_CHECKS(sim 段级短跑批;sim-testing §6 B 类病
# --- 三缺口之①「过程不可观测」的轮级检验载体) ------------------------
#
# 与 _BATCH_CHECKS 平行的第二张表:
# - 输入 = 单局前 K 轮决策流(runner.simulate_p1_batch 的 max_rounds
#   窗口切片;不传窗口时即整局逐轮账本,语义同构);
# - 输出 = **带定位的事件列表**(哪局·哪轮·违反哪条·当时 state 关键
#   值),不是 _BATCH_CHECKS 的「违规局数+局索引」聚合——段级病的归因
#   需要轮级现场(seed+指纹可重放,sim-testing §6 回放纪律);
# - 全部断言**单轮可判**(不跨轮累积状态,除成型判定与连胜重算两类
#   由既有口径单源供给)——段级截断在第 K 轮切账本后语义不变;
# - 口述条对齐:user_playstyle.md [6][11][12][13][17][19][22④];
#   例外条件([6] 店全想要 / [19] 连胜保三态谱 / [11] 同息档零息损 /
#   [16] 奖励节点买经验)编进断言,一刀切 = 误报泛滥。
# =====================================================================

def _seg_gold0(row: dict) -> int | None:
    """决策时点金 = 本轮首牌面波 gold(收入后花销前;与
    check_levelup_interest_engine_gate 的 gold0 同口径)。"""
    waves = (row.get('sim') or {}).get('shop_waves') or []
    if waves and isinstance(waves[0].get('gold'), int):
        return int(waves[0]['gold'])
    g = row.get('gold')
    return int(g) if isinstance(g, int) else None



def _seg_spent(row: dict) -> bool:
    """本轮是否有任何花费动作(买/升级/刷;免费刷 cost=0 不计)。"""
    s = row.get('sim') or {}
    sp = s.get('spend') or {}
    if (sp.get('buys') or {}) or sp.get('levelup', 0) \
            or sp.get('refresh', 0):
        return True
    return any(a.get('__type__') in ('BuyCard', 'LevelUp', 'RefreshShop')
               for a in row.get('actions') or [])



def _seg_engines(row: dict) -> int:
    """过渡体系达成数(迁移审计 w278(git 历史) 单一源 = cw_deploy_logic.engines_count,
    即原 cw_battle_calib._engines_count 本体——检查网不 import cw_sim 的架构
    锁由依赖方向保证)。"""
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        engines_count,
    )
    st = row.get('state') or {}
    bf = st.get('board_factions') or {}
    dep = frozenset(d.get('char_id', '') for d in (st.get('deployed') or []))
    return engines_count(bf, dep)



def seg_check_gold_identity(rows: list[dict]) -> list[dict]:
    """金账恒等式(实现层探针,非口述):上轮金+本轮收入−本轮支出=本轮金。

    与 check_ledger_consistency 的差别:那条用行内 ``sim.gold_before``
    (单行自洽),本条用**链式**上一行末金——跨行的记账断裂(轮间
    丢一笔/收入重复入账)只有链式才能暴露。违规 = 账本/执行层 bug
    (非策略病);每个事件带前后金与收支分解供定位。
    """
    out: list[dict] = []
    prev_gold: int | None = None
    for row in rows:
        gold = row.get('gold')
        if not isinstance(gold, int):
            continue
        if prev_gold is not None:
            s = row.get('sim') or {}
            inc = s.get('income') or {}
            sp = s.get('spend') or {}
            expect = (prev_gold + sum(inc.values())
                      - sum((sp.get('buys') or {}).values())
                      - sp.get('levelup', 0) - sp.get('refresh', 0)
                      + sp.get('sell_income', 0))
            if gold != expect:
                out.append({
                    'plane': row.get('plane'),
                    'round_num': row.get('round_num'),
                    'detail': f'金不守恒 {gold} != {expect}'
                              f'(上轮末 {prev_gold}, 收入 {sum(inc.values())}'
                              f' 支出 {sum((sp.get("buys") or {}).values()) + sp.get("levelup", 0) + sp.get("refresh", 0)}'
                              f' 卖出回收 {sp.get("sell_income", 0)})',
                })
        prev_gold = gold
    return out



#: 溢余容忍带(ADR-0478):g0 ≤ interest_floor + 容差视为息线邻近浮动态,
#: 不构成 [17] 残量违规。边界依据:51-52 带内同息档 discharge 依赖店里
#: 恰有 1-2 费件,店里没有时空坐是设计内最优(ADR-0434 息线以下支出门
#: 默认拒跨档花,1 死金 < 跨档息损);真堆积(≥53)不受影响仍红。
_OVERFLOW_TOLERANCE: int = 2


def seg_check_overflow_idle_spend(rows: list[dict]) -> list[dict]:
    """[17] 溢余即花(段级单轮版):金>50 且存在高边际价值购买目标却
    整轮无花费动作。

    「高边际价值」代理口径:**未成型**(过渡体系达成数<2,[13] 成型
    前战力件/压库件都有边际价值;成型后的攒息是 [13]/ADR-0343 合法面
    ——与 check_overflow_gold_zero_buy_streak 的豁免边界一致,但那条
    要连续 ≥2 轮才报,本条单轮即报,诊断灵敏度更高、预期噪声也更高,
    违规率按「量级说明」读不按达标线读)。
    豁免:formed_stop 行(策略自认停手攒息)、bench 满守卫拦截轮
    (想买买不了,``bench_full_skipped_buys``>0 披露在场)、息线邻近
    容忍带(g0 ≤ interest_floor+``_OVERFLOW_TOLERANCE``,ADR-0478)。
    """
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    out: list[dict] = []
    for row in rows:
        if (row.get('plane') or 1) != 1:
            continue
        if row.get('formed_stop'):
            continue
        sim = row.get('sim') or {}
        if (sim.get('bench_full_skipped_buys') or 0) > 0:
            continue
        g0 = _seg_gold0(row)
        if g0 is None or g0 <= 50 or _seg_spent(row):
            continue
        if g0 <= DEFAULT_REGISTRY.interest_floor() + _OVERFLOW_TOLERANCE:
            continue
        engines = _seg_engines(row)
        if engines >= 2:
            continue
        node = sim.get('node') or ''
        out.append({
            'plane': 1, 'round_num': row.get('round_num'),
            'detail': f'金 {g0}>50 整轮零花费未成型(engines={engines})'
                      f' 节点={node}——[17] 溢余该花',
            'gold_before': g0, 'engines': engines, 'node': node,
        })
    return out



def _seg_target_roster(target_label: str) -> set[str]:
    """锁定目标名册代理(与 seg_check_formed_still_buying_transition
    的 _is_target_piece 同口径:bridge 框架件 ∪ COMP_LIBRARY 该 comp
    的 core_chars∪factions 成员;C-A 目标内判定用,§4.2 单一源复用)。"""
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
    from sr_od.application.currency_war.kernel.cw_line_defs import BRIDGE_POOL
    roster: set[str] = set()
    for combo in BRIDGE_POOL:
        roster.update(combo.fixed + combo.core)
    comp = next((c for c in COMP_LIBRARY
                 if getattr(c, 'name', '') == (target_label or '')), None)
    if comp is not None:
        roster.update(getattr(comp, 'core_chars', ()) or ())
        for fn in getattr(comp, 'factions', ()) or ():
            roster.update(n for n, c in CHARACTERS.items()
                          if fn in (c.factions or ()))
    return roster



def _seg_offered_cards(row: dict) -> list[dict]:
    """本轮出现过的店面板(全部波合并去重,按名;末波为最终可见态)。"""
    seen: dict[str, dict] = {}
    for w in (row.get('sim') or {}).get('shop_waves') or []:
        for c in w.get('cards') or []:
            seen[c.get('name') or ''] = c
    return list(seen.values())



def seg_check_break_interest_exception(rows: list[dict]) -> list[dict]:
    """[6]/[19] 破息例外记账(段级):发生破息的那笔购买必须落在例外
    条件内。

    「破息」= 本轮从时点金 ≥50 跨到末金 <50(破息由本轮花费引发;
    逐笔粒度账本不携,轮级近似声明)。例外条件(任一成立合法):
    ① **店全想要**代理 = 本轮买入 ≥2 笔且无一笔 channel=='off'
    (channel=classify_buy 身份单一源,'off'=线外杂卡);
    ② **连胜保三态谱**([19]:已连胜值得花保)= 进入轮时重算连胜
    ≥2(``_combat_streak_by_round`` 单一源;连胜只有战斗类节点累积,
    重算口径与该 helper 相同);
    ③ ~~奖励/补给节点买经验~~(**已收编退役**:[16]② 原条目已删除,
    节点限定口径随「息律节点无关」定调由④收编——ADR-0471;T-115 起
    奖励节点 = 升级抑制对象(ADR-0580 规则①),不再构成独立豁免依据,
    奖励帧 LevelUp 支出仍由④通道口径覆盖);
    ④ **追级经验通道**(spend.levelup>0):升级授权单一源 =
    ev.levelup_ev_basis([12]/[33] 总账,ADR-0347/0354;[32] 定调
    升级节点无关)——任意节点的升级破息都是授权通道的表征,不是
    无例外破息;
    ⑤ **刷新找牌通道**(spend.refresh>0):[3] 刷新找牌,授权面 =
    refresh_ev_budget 预算式([3] 花后保息线)/M-A 有界预算
    (ADR-0409)/迁移审计 w332b(git 历史) 义务预算——按预算显式裁定搜索成本,破息
    是授权语义内的代价。
    ⑥ **boss 窗地板授权**(ADR-0478):boss 节点(node ∈
    ``boss_round_node_types``)是 interest_rule 的旁路窗(ADR-0347 ⑤/
    ADR-0356——窗内唯一授权器 = boss_floor 破息地板 10),授权范围内
    合法跌破息基、下探至 boss_floor 属设计内行为(ADR-0426 同一语义);
    花后金仍 ≥ boss_floor → 豁免;跌破 boss_floor → 不豁免照报
    (越权信号,ADR-0426 边界原文)。
    ④⑤同时把升级/刷新/买件花费分解(spend_breakdown)写进事件,
    归因不需人工分账(`w649_mutation/` B2)。
    仍不满足 = 买件引发的凭空破息(真破息候选,行为判读输入)。
    事件带该轮店面板(最终可见波)与最终选择(买入名单+通道)供归因。
    """
    out: list[dict] = []
    streaks = _combat_streak_by_round(rows)
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    for row in rows:
        if (row.get('plane') or 1) != 1:
            continue
        g0 = _seg_gold0(row)
        gold_end = row.get('gold')
        if g0 is None or not isinstance(gold_end, int):
            continue
        if g0 < 50 or gold_end >= 50 or not _seg_spent(row):
            continue
        bought = [{'name': (a.get('card') or {}).get('name'),
                   'cost': (a.get('card') or {}).get('cost'),
                   'channel': a.get('channel'),
                   'reason': a.get('reason')}
                  for a in row.get('actions') or []
                  if a.get('__type__') == 'BuyCard']
        node = (row.get('sim') or {}).get('node') or ''
        _spend = (row.get('sim') or {}).get('spend') or {}
        spend_lv = int(_spend.get('levelup') or 0)
        spend_rf = int(_spend.get('refresh') or 0)
        exceptions = []
        if len(bought) >= 2 and all(b.get('channel') != 'off'
                                    for b in bought):
            exceptions.append('store_all_wanted')
        if streaks.get(row.get('round_num'), 0) >= 2:
            exceptions.append('streak_hold')
        # T-115 对齐(ADR-0580):原③奖励/补给节点豁免已退役——奖励节点
        # = 升级抑制对象,不再构成节点型独立豁免;LevelUp 支出由④
        # levelup_spend 通道口径覆盖(ADR-0471 收编口径)。
        if spend_lv > 0:
            exceptions.append('levelup_spend')
        if spend_rf > 0:
            exceptions.append('refresh_spend')
        if node in DEFAULT_REGISTRY.boss_round_node_types:
            if gold_end >= DEFAULT_REGISTRY.boss_floor:
                exceptions.append('boss_floor_authorized')
            # else: boss 窗越权跌破地板(ADR-0426 边界),不豁免照报
        if exceptions:
            continue
        last_cards = ((row.get('sim') or {}).get('shop_waves') or [{}])[-1] \
            .get('cards') or []
        out.append({
            'plane': 1, 'round_num': row.get('round_num'),
            'detail': f'破息 {g0}->{gold_end} 无例外依据(购 {len(bought)} 笔'
                      f' channels={[b.get("channel") for b in bought]},'
                      f' 进轮连胜 {streaks.get(row.get("round_num"), 0)},'
                      f' 节点={node})'
                      + ('——boss 窗跌破地板越权'
                         if node in DEFAULT_REGISTRY.boss_round_node_types
                         else '')
                      + '——[6]/[19]',
            'gold_before': g0, 'gold_after': gold_end,
            # 花费分解(升级/刷新/买件按通道;`w649_mutation/` B2:归因不看人工)
            'spend_breakdown': {'levelup': spend_lv, 'refresh': spend_rf,
                                'buys': dict(_spend.get('buys') or {})},
            'buys': bought, 'final_shop_panel': last_cards,
        })
    return out



def seg_check_formed_still_buying_transition(rows: list[dict]) -> list[dict]:
    """[13] 成型停手(段级):过渡阵容已成型后仍买**过渡件**。

    成型判据复用现有单一源(cw_battle_calib._transition_formed 同判据的
    ``_engines_count≥2``,见 sim-testing §6「判定口径复用现有成型
    判据,不新造」);**目标阵容件照买照囤是 [13] 明文的正常行为**
    ([21]/[22]),故只对「过渡填充件」断言——排除目标件的代理口径:
    卡 ∈ 锁定 target_comp 名册(COMP_LIBRARY core_chars∪factions 内
    角色)或 ∈ BRIDGE_POOL fixed∪core(框架件)→ 合法囤积;其余
    engine/pair 身份买入 = 成型后过渡件,违规。
    数据边界:target 未锁定时的 bridge 白名单兜底;pairs 周边件在
    两名单之外的极端形态可能误报——事件率仅供诊断。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
    from sr_od.application.currency_war.kernel.cw_line_defs import BRIDGE_POOL
    bridge_names: set[str] = set()
    for combo in BRIDGE_POOL:
        bridge_names.update(combo.fixed + combo.core)

    def _is_target_piece(name: str, target_label: str) -> bool:
        if name in bridge_names:
            return True
        # COMP_LIBRARY 是 list[Comp](按 name 定位;非 dict)
        comp = next((c for c in COMP_LIBRARY
                     if getattr(c, 'name', '') == (target_label or '')),
                    None)
        if comp is None:
            return False
        roster = set(getattr(comp, 'core_chars', ()) or ())
        for fn in getattr(comp, 'factions', ()) or ():
            roster.update(n for n, c in CHARACTERS.items()
                          if fn in (c.factions or ()))
        return name in roster

    out: list[dict] = []
    formed = False
    for row in rows:
        if (row.get('plane') or 1) != 1:
            continue
        formed = formed or _seg_engines(row) >= 2
        if not formed:
            continue
        # 同名在场豁免:已持有该件再买 = 副本合成路径([4] 核心 2★,
        # [28] 形态达标的过渡核心升星维),不是新增过渡填充。
        st_names = {d.get('char_id') for d in
                    ((row.get('state') or {}).get('deployed') or [])} \
            | {b.get('char_id') for b in
               ((row.get('state') or {}).get('bench') or [])}
        target_label = row.get('target_comp') or ''
        # v3 过渡配方标签拆解(target_comp 形如 过渡配方·A+B → A/B)
        labels = target_label.removeprefix('过渡配方·').split('+')
        for a in row.get('actions') or []:
            if a.get('__type__') != 'BuyCard':
                continue
            name = (a.get('card') or {}).get('name') or ''
            if a.get('channel') not in ('engine', 'pair'):
                continue
            if name in st_names:
                continue
            if any(_is_target_piece(name, lb) for lb in labels):
                continue
            rn = row.get('round_num')
            out.append({
                'plane': 1, 'round_num': rn,
                'detail': f'成型后仍买过渡件 {name}(channel='
                          f'{a.get("channel")}, target={target_label})'
                          f'——[13] 成型停手线',
                'bought': name, 'channel': a.get('channel'),
                'target_comp': target_label,
            })
    return out



_LEVELUP_AUTH_WHITELIST = ('pop_slot', 'dp', 'static_ev', 'm3_batch')
# ('p2_auth_xp' 臂已随位面 2 支出授权定谳清理删除,ADR-0492;XP sink
# 在 W785 sink 分解中 0 帧/0 金,供给面从未开火。m3_batch = mandate_v1
# 换核后的 M3 批量授权臂(arm1_existence=[33] 人口位语境 + P48 整买
# spend_unified + dd-034 危机让位),定谳批补入——出处与逐臂论证 =
# check_levelup_interest_engine_gate docstring。m3_batch 现带触发臂分键后缀(m3_batch:arm1/arm0/pop,授权可归因),匹配走前缀(见 seg_check_unjustified_levelup 门内),禁回退精确等值。)

# 同 check_levelup_interest_engine_gate(ADR-0410 static_ev 并入;
# m3_batch 随 mandate_v1 换核定谳批并入)——
# 常量此处镜像声明防跨表 import 私名;两侧语义漂移由测试仓双向锁辖。


def seg_check_unjustified_levelup(rows: list[dict]) -> list[dict]:
    """[12]/[33] 升级驱动(段级):无「有框架单位等待上场」依据的升级
    (凭空追级)。

    授权依据观测(LevelUp.auth_basis,`w131_a2n_arm/`/ADR-0410)为准——白名单
    pop_slot([33] 人口位=有框架单位等待上场)/ dp(DP 授权)/
    static_ev(EV 平台账)外 = 凭空追级。[12] 主条(连 50 金都没凑到
    不急升级)落在授权门的金维:与 batch 表 check_levelup_interest_
    engine_gate 同谓词,差异只在输出粒度(那里=违规局数,这里=逐事件
    带 state 关键值供段级归因)。T-115 对齐(ADR-0580):原「豁免奖励/
    补给节点([16]② 买经验合法)」节点型 skip 已退役——奖励节点 = 升级
    抑制对象(T-115 规则①),授权判定按 ADR-0471 收编口径回归节点无关
    的通道分类(auth 白名单);奖励帧无授权升级 = 违规可见,白名单内
    授权(如扑满环境帧经 M3 闸链的 m3_batch:*)照常放行。
    近似声明同 batch 版:升级前等级用上一行 level;时点金=首波 gold。
    """
    out: list[dict] = []
    prev_level = 3
    for row in rows:
        if (row.get('plane') or 1) != 1:
            continue
        waves = (row.get('sim') or {}).get('shop_waves') or []
        g0 = waves[0].get('gold') if waves else row.get('gold')
        for a in row.get('actions') or []:
            if a.get('__type__') != 'LevelUp':
                continue
            basis = a.get('auth', '')
            if prev_level < 5:
                continue   # 与 batch 版同界:lv≥5 才算追级段
            if basis in _LEVELUP_AUTH_WHITELIST or basis.startswith('m3_batch:'):
                continue
            st = row.get('state') or {}
            out.append({
                'plane': 1, 'round_num': row.get('round_num'),
                'detail': f'LevelUp 时点金 {g0}<50 授权={basis or "(空)"}'
                          f'(lv{prev_level}, cap={st.get("cap")})'
                          f'——[12]/[33] 凭空追级',
                'gold_before': g0, 'auth_basis': basis,
                'level_before': prev_level, 'cap': st.get('cap'),
            })
        prev_level = ((row.get('state') or {}).get('level')
                      or prev_level)
    return out



# 血预算停手线镜像(设计件 12 §6;ADR-0448):本文件「纯函数,不
# import cw_sim/决策栈」纪律下的镜像声明(先例=_LEVELUP_AUTH_WHITELIST);
# 单一源=decision_v2.discipline.p1/p2_levelup_stop_hp(由 registry
# vd_* 常量推导),漂移由测试仓双向锁辖。
_P2_LEVELUP_STOP_HP: int = 21   # ceil(1×registry.vd_p2_loss=20.05)

_P1_LEVELUP_STOP_HP: int = 11   # ceil(1×(11.32−0.37×2)=10.58)

# 血预算停手·第二波镜像(设计件 12 §6;ADR-0451):P1_EXIT_BLOOD_TARGET
# (期望预算线,`w524_audit_60line/` 审计后语义)+ 末窗起点(ADR-0418
# 定窗 r6..r9;原 registry 旋钮已随承接门家族死链删除,2026-09-04
# 用户裁定清理)+
# 应急带下限 emergency_hp(急救型豁免面;检查域=两者开区间)
_P1_EXIT_BLOOD_TARGET: int = 60

_P1_HANDOFF_GATE_MIN_ROUND: int = 6

_P1_EMERGENCY_HP: int = 25

# 位面节点数镜像(plane_last_battle 的轮维;P1=NODES_PER_PLANE=9,
# P2=engine_p1.P2_ROUNDS=7——ALL IN 帧=node='boss' ∧ 轮≥节点数)
_ALLIN_MIN_ROUND: dict[int, int] = {1: 9, 2: 7}


def terminal_release_bit(sess, st) -> bool:
    """血预算停手·末窗终止豁免位写入侧(ADR-0469;单一源 = 本函数,
    账本行键 terminal_release 的唯一写入依据,sim 引擎轮入口调用;
    实机遥测透传位 = telemetry schema sess_terminal_release,schema
    缺省未写)。辖域 = P1 末窗(rn ≥ 末窗起点)∧ 血预算不足带
    (应急带 < hp < 退血线,开区间);boss ALL-IN 窗豁免归检查器轮键,
    本位不辖。本函数 = 上述常量的唯一同源写入点——检查器消费行键
    禁复算 S0。
    """
    if (getattr(st, 'plane', None) or 1) != 1:
        return False
    if int(getattr(st, 'round_num', None) or 0) < _P1_HANDOFF_GATE_MIN_ROUND:
        return False
    hp = int(getattr(st, 'hp', None) or 0)
    return _P1_EMERGENCY_HP < hp < _P1_EXIT_BLOOD_TARGET



def _blood_budget_levelup_events(rows: list[dict], plane: int,
                                 stop_hp: int) -> list[dict]:
    """血预算停手·停升级线段级检查公共实现(设计件 12 §3.1/§2.3-P1-b;
    ADR-0448):备战帧 hp ≤ 停升级线时出现 LevelUp = 追级泵未停转,
    违规。豁免=ALL IN 帧(node='boss' ∧ 轮≥位面节点数;位面末最后一战
    是损失最小的花光时机,[18] 停手让位)。

    hp 口径:决策帧 hp = **上一行**的 hp(账本行 hp 是本轮回后结算值,
    决策发生在本轮回战斗之前;局首帧=开局满血,恒不触线)——逐行滚动
    prev_hp 取上一行,跨位面连续(P2 首帧决策 hp=P1 末行 hp,与生产
    进场继承同真值)。"""
    out: list[dict] = []
    prev_hp: int | None = None
    for row in rows:
        hp_decision = prev_hp
        prev_hp = row.get('hp') if row.get('hp') is not None else prev_hp
        if (row.get('plane') or 1) != plane:
            continue
        hp = hp_decision
        if hp is None or hp > stop_hp:
            continue
        node = (row.get('sim') or {}).get('node') or ''
        rn = int(row.get('round_num') or 0)
        if node == 'boss' and rn >= _ALLIN_MIN_ROUND.get(plane, 9):
            continue    # ALL IN 窗豁免(反例锁=测试仓构造帧)
        lv = sum(1 for a in row.get('actions') or []
                 if a.get('__type__') == 'LevelUp')
        if lv:
            out.append({
                'plane': plane, 'round_num': rn,
                'detail': f'备战帧hp{hp}≤停升级线{stop_hp} 仍升级×{lv}'
                          f'(追级泵未停转)——血预算停手(ADR-0448)',
                'hp': hp, 'stop_hp': stop_hp, 'levelups': lv,
            })
    return out



def seg_check_p2_blood_budget_levelup(rows: list[dict]) -> list[dict]:
    """血预算停手·P2 停升级线(段级):plane=2 ∧ hp≤21(非 ALL IN 帧)
    的 LevelUp 事件(设计件 12 §3.1;ADR-0448;⑳+1 局病灶
    「血线 16/1 追级泵 6/12 次」的 sim 回灌面)。"""
    return _blood_budget_levelup_events(rows, 2, _P2_LEVELUP_STOP_HP)



def seg_check_p1_blood_budget_levelup(rows: list[dict]) -> list[dict]:
    """血预算停手·P1 停追级线(段级):plane=1 ∧ hp≤11(非 ALL IN 帧)
    的 LevelUp 事件(设计件 12 §2.3-P1-b 完备性条款;ADR-0448)。"""
    return _blood_budget_levelup_events(rows, 1, _P1_LEVELUP_STOP_HP)



def seg_check_p1_blood_budget_refresh(rows: list[dict]) -> list[dict]:
    """血预算停手·末窗搜索型刷新停付(段级;设计件 12 §2.3-P1-c/§3.2;
    ADR-0451;终止豁免改账本位判据=迁移审计 w659(git 历史) v2 §5.1 R4;ADR-0469):P1 末窗
    (轮≥6,末窗起点=ADR-0418 定窗;原 handoff_gate_min_round 旋钮已随
    承接门家族死链删除,2026-09-04 用户裁定清理)∧ 血预算不足带(emergency_hp < 决策帧
    hp < P1_EXIT_BLOOD_TARGET——应急带内刷新=急救型豁免面,ALL IN 窗
    让位)出现 RefreshShop ∧ 账本终止位非真 = 搜索型停付未生效,违规。

    **账本位口径(禁同式复算 S0)**:行键 ``terminal_release``=
    ``terminal_release_bit`` 单一址记账(本模块实现,sim 引擎轮入口
    写行键;决策发生在
    本轮回战斗前)——位真=终止豁免辖内(刷新行为合法,含当轮转化
    双门放行面);位假=停付应生效。键缺省(旧批账本)=False,行为
    与停付语义兼容。hp 口径同停升级检查(决策帧=上一行结算 hp)。"""
    out: list[dict] = []
    prev_hp: int | None = None
    for row in rows:
        hp_decision = prev_hp
        prev_hp = row.get('hp') if row.get('hp') is not None else prev_hp
        if (row.get('plane') or 1) != 1:
            continue
        hp = hp_decision
        if hp is None or hp >= _P1_EXIT_BLOOD_TARGET \
                or hp <= _P1_EMERGENCY_HP:
            continue
        rn = int(row.get('round_num') or 0)
        if rn < _P1_HANDOFF_GATE_MIN_ROUND:
            continue
        node = (row.get('sim') or {}).get('node') or ''
        if node == 'boss' and rn >= _ALLIN_MIN_ROUND.get(1, 9):
            continue    # ALL IN 窗豁免([18] 停手让位)
        rf = sum(1 for a in row.get('actions') or []
                 if a.get('__type__') == 'RefreshShop')
        if not rf:
            continue
        if row.get('terminal_release'):
            continue    # 终止豁免辖内(账本位;ADR-0469)
        out.append({
            'plane': 1, 'round_num': rn,
            'detail': f'末窗备战帧hp{hp}<{_P1_EXIT_BLOOD_TARGET} '
                      f'仍刷新×{rf}(搜索型停付未生效;急救带'
                      f'hp≤{_P1_EMERGENCY_HP}豁免;终止位=假)——血预算停手'
                      '(ADR-0451/ADR-0469)',
            'hp': hp, 'refreshes': rf, 'terminal_release': False,
        })
    return out



def seg_check_untrusted_hp_levelup(rows: list[dict]) -> list[dict]:
    """不可信 hp 帧发 LevelUp = 违规(段级;`w580_hp_trust_defense/` DESIGN 测试计划组5)。

    判据:决策帧 hp 不可信(非(hp_readable or hp_trusted),即两位
    皆 False——不可信谓词镜像消费门单一源 decision_v2.posture_release
    .hp_decision_trusted;(False, True) 同节点沿用帧/(True, False)
    真读帧是消费门放行面(DESIGN 组3 锁),检查器同面放行不虚报)
    时出现 LevelUp 决策。与 decision_v2 消费门(discipline.blood_budget_
    levelup_blocked,迁移审计 w580a(git 历史))两层分工:消费门在 decision 层**拒付**
    (不可信帧 fail-closed),本检查在 checks 层**显形**——若账本/
    回放里不可信帧仍出现 LevelUp(门旁路、账本错位、或未来合成器/
    策略变化引入不可信帧),检查器即刻命中,不依赖门被触发。

    可信位读取口径:hp_readable = 行顶层键(生产 decisions 帧同构;
    cw_telemetry 显影同位)、hp_trusted = state 子字典键(GameState
    快照位)。**键缺省 = 可信**——sim 账本恒真读不携带两键 → 恒零
    命中(纯防线验证面;旧批账本同样兼容)。

    ALL IN 帧豁免(node='boss' ∧ 轮≥位面节点数,_ALLIN_MIN_ROUND
    镜像):消费门语义「豁免优先于守卫——末战花光是时机不是血线
    判断」的检查侧同构,不因证据缺失收紧豁免面。
    """
    out: list[dict] = []
    for row in rows:
        readable = row.get('hp_readable')
        trusted = (row.get('state') or {}).get('hp_trusted')
        # 缺省位 = 可信(sim 恒真读零命中);谓词镜像 hp_decision_trusted
        # = readable or trusted——仅两位皆 False 才不可信
        if readable is not False or trusted is not False:
            continue
        plane = row.get('plane') or 1
        rn = int(row.get('round_num') or 0)
        node = (row.get('sim') or {}).get('node') or ''
        if node == 'boss' and rn >= _ALLIN_MIN_ROUND.get(plane, 9):
            continue    # ALL IN 窗豁免(消费门语义镜像)
        lv = sum(1 for a in row.get('actions') or []
                 if a.get('__type__') == 'LevelUp')
        if not lv:
            continue
        bits = []
        if readable is False:
            bits.append('hp_readable=False')
        if trusted is False:
            bits.append('hp_trusted=False')
        out.append({
            'plane': plane, 'round_num': rn,
            'detail': f'不可信 hp 帧({" & ".join(bits)})'
                      f' LevelUp×{lv}(hp={row.get("hp")})'
                      '——不可信帧违规(`w580_hp_trust_defense/` 消费门镜像)',
            'hp': row.get('hp'), 'levelups': lv, 'bits': bits,
        })
    return out



def seg_check_p2_bleed_gold_stack(rows: list[dict]) -> list[dict]:
    """[17] 位面2 延伸:血线下降段金堆积(连续 ≥2 轮报警)。

    出处:2026-08-30 三实机局 P2 线已锁定、hp 连败、带金 86-113 堆积
    死亡,段级检查只辖 P1 全程零标红(跨局复盘立案A;检查器接线批
    落地,ADR-0479)。判据与复盘口径一致:「hp 在掉 ∧ 金未泄 ∧ 溢余
    在手」——
    - plane≥2 决策轮,决策时点金 > interest_floor+``_OVERFLOW_TOLERANCE``
      (带宽与 P1 [17] 同源,ADR-0478);
    - 金较上一轮**未下降**:买入支出被收入盖过 = 溢余在堆积——
      「有买」不豁免(实机局2 P2 小买 2-3 张不改 86→112 堆积趋势,
      按「零花费动作」判会漏报);
    - hp 较上一轮下降:血在掉是本检查的合法性判别器——血线稳定/上行的
      P2 攒息不辖;formed_stop **不豁免**([13] 成型停手是 P1 过渡段
      语义,P2 质量期带血攒息正是病理本体);
    - 连续 ≥2 轮才报:单轮持息是灰区,连续堆积才是病理量级
      (对偶门 = 防恒触发,sim-testing §6)。
    只读报警:事件走 defect 通道供判读,不触发任何决策动作。
    hp 可信位口径(实机接线实测修正):生产行 hp_readable=False = 本帧
    未读到、字段为 ``last_hp_real`` 沿用值(ADR-0282)——沿用值只在
    真读时变化,**下降必是真读**,血线下降判据可用;沿用值停滞只可能
    造成漏报(保守向),不造成误报,故不做可读位硬门(sim 行恒真读
    零命中;开局无真值的 100 兜底只在 P1 出现,不入 P2 段)。金不可读
    帧跳过且断 streak(溢余判据直接吃金值,不可信金不猜)。
    """
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    out: list[dict] = []
    prev_gold: int | None = None
    prev_hp: int | None = None
    streak = 0
    for row in rows:
        if (row.get('plane') or 1) < 2:
            prev_gold = prev_hp = None
            streak = 0
            continue
        gold = row.get('gold')
        hp = row.get('hp')
        # 金不可读 = 不可信,跳过并断链(溢余判据直接吃金值,不猜);
        # hp 沿用值口径见 docstring(False = last_hp_real 沿用,下降必真读)
        if not isinstance(gold, int) or row.get('gold_readable') is False \
                or not isinstance(hp, int):
            prev_gold = prev_hp = None
            streak = 0
            continue
        overflow = gold > DEFAULT_REGISTRY.interest_floor() \
            + _OVERFLOW_TOLERANCE
        stacking = prev_gold is not None and gold >= prev_gold
        bleeding = prev_hp is not None and hp < prev_hp
        if overflow and stacking and bleeding:
            streak += 1
            if streak >= 2:
                out.append({
                    'plane': 2, 'round_num': row.get('round_num'),
                    'detail': f'P2 血线下降段金堆积第 {streak} 连轮:'
                              f' 金 {prev_gold}→{gold} 未泄、hp '
                              f'{prev_hp}→{hp} 在掉——[17] 溢余该定向花'
                              '([18] 最小必要支出止损)',
                    'gold_before': gold, 'prev_gold': prev_gold,
                    'hp': hp, 'prev_hp': prev_hp, 'streak': streak,
                })
        else:
            streak = 0
        prev_gold, prev_hp = gold, hp
    return out


def seg_check_must_spend_observation(rows: list[dict]) -> list[dict]:
    """必花域观测三键聚合(20 号稿 §6;行内键 = engine_p1 ledger obs)。

    非违规检查(恒出摘要事件,给 sim 批报告收账用):合计
    zone_frames/zero_consume + 零消费帧定位 + 层命中分布。零消费帧
    判读看归因(物理残量白名单帧带分键,非直接判失败)。
    """
    zone = zero = 0
    layer: dict[str, int] = {}
    zero_rounds: list = []
    for row in rows:
        obs = row.get('obs') or {}
        z = obs.get('must_spend_zone_frames')
        if z is None:
            continue   # 无键行(旧账本/生产合并行)跳过,不造零
        zone += z
        zc = obs.get('must_spend_zero_consume') or 0
        zero += zc
        if zc:
            zero_rounds.append(row.get('round_num'))
        for k, v in (obs.get('must_spend_layer_hit') or {}).items():
            layer[k] = layer.get(k, 0) + int(v or 0)
    if not zone:
        return []
    return [{'plane': rows[0].get('plane') or 1, 'round_num': None,
             'detail': (f'必花域动作帧 {zone}、零消费 {zero}'
                        f'(帧号 {zero_rounds[:20]})、层命中 {layer}'),
             'zone_frames': zone, 'zero_consume': zero,
             'zero_consume_rounds': zero_rounds[:20],
             'layer_hit': layer}]


#: 段级检查表(名字 → fn(rows)->list[event_dict];与 _BATCH_CHECKS
#: 平行,输出粒度不同——事件带定位,见本节头注释)。
_SEGMENT_CHECKS = {
    'seg_gold_identity': seg_check_gold_identity,
    'seg_overflow_idle_spend': seg_check_overflow_idle_spend,
    'seg_break_interest_exception': seg_check_break_interest_exception,
    'seg_formed_still_buying_transition': seg_check_formed_still_buying_transition,
    'seg_unjustified_levelup': seg_check_unjustified_levelup,
    'seg_p2_blood_budget_levelup': seg_check_p2_blood_budget_levelup,
    'seg_p1_blood_budget_levelup': seg_check_p1_blood_budget_levelup,
    'seg_p1_blood_budget_refresh': seg_check_p1_blood_budget_refresh,
    'seg_untrusted_hp_levelup': seg_check_untrusted_hp_levelup,
    'seg_p2_bleed_gold_stack': seg_check_p2_bleed_gold_stack,
    'seg_must_spend_observation': seg_check_must_spend_observation,
}


#: 事件列表上限(报告侧;全量走 seed 重放可再取,防批报告膨胀)
_SEGMENT_EVENTS_CAP: int = 20


def run_segment_checks(ledgers: list[list[dict]], *,
                       seed_base: int = 0) -> dict:
    """段级检查批量入口 → {检查名: {'count','events'},'_summary'}。

    事件字段追加 game_idx/seed/check(same-contract:seed = seed_base+
    game_idx,cw_sim replay --seed N --pool snapshot 可逐步还原现场)。
    events 截断至 ``_SEGMENT_EVENTS_CAP``(count 是真值)。
    """
    report: dict = {}
    for name, fn in _SEGMENT_CHECKS.items():
        events: list[dict] = []
        for idx, rows in enumerate(ledgers):
            try:
                evs = fn(rows) or []
            except Exception as exc:   # noqa: BLE001  检查器异常不炸批
                report.setdefault('_errors', {})[name] = repr(exc)
                continue
            for ev in evs:
                ev = dict(ev)
                ev['game_idx'] = idx
                ev['seed'] = seed_base + idx
                ev['check'] = name
                events.append(ev)
        report[name] = {
            'count': len(events),
            'events': events[:_SEGMENT_EVENTS_CAP],
            'truncated': len(events) > _SEGMENT_EVENTS_CAP,
            'seed_base': seed_base,
        }
    report['_summary'] = {
        'total_events': sum(v['count'] for k, v in report.items()
                            if isinstance(v, dict) and 'count' in v),
        'rates_note': 'count/n 为诊断用违规率量级,非达标线'
                      '(段级检查是过程病扫描仪);分母 = 批局数',
    }
    return report
