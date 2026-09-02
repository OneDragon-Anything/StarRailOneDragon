"""decision_v2 决策链检查(候选覆盖/仲裁矩阵/遥测契约/线门,分包期6 拆分)。"""

from __future__ import annotations

# --- ADR-0291(决策框架 v2 骨架批)检查项 -----------------------------

def check_decision_v2_candidate_coverage(
        ledgers: list[list[dict]] | None = None) -> dict:
    """ADR-0291:候选生成必须覆盖全部合法动作类(decision_v2)。

    两层判据:
    ① **结构层(恒跑)**:对合成探针状态直接调
       ``decision_v2.candidates.generate_candidates``——探针覆盖各
       动作类的触发态(店有目标卡/bench 有杂件/bench 近满/有可上件/
       同名 2 份+店有第 3 张),生成候选的动作类并集必须 == 全部
       合法动作类(买/卖/LevelUp/Refresh/Deploy/合成)。层1 枚举
       义务(ADR-0290)的回归锁:新增动作类型而生成器没枚举 → 红。
    ② **执行层(账本有 d2_ 前缀 reason 时才辖)**:decision_v2 批次
       的全批已执行动作类必须含 BuyCard/LevelUp(每批必然态,缺 =
       死路形态);deploy/refresh/合成可策略性零采纳 → 披露不辖。
    """
    from sr_od.application.currency_war.decision.cw_strategy import StrategySession
    from sr_od.application.currency_war.decision.decision_v2.candidates import (
        ACTION_CLASSES,
        generate_candidates,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        BenchChar,
        GameState,
        ShopCard,
    )
    violations: list[str] = []
    seen_classes: set[str] = set()
    # 探针:锁线态(carry 在店=买;杂件在 bench=卖;等级<10+金足=
    # LevelUp;恒 Refresh;cap 未满+围栏认可=Deploy;同名 2 份+店有
    # 第 3 张=合成)
    s = GameState()
    s.plane, s.round_num, s.level, s.gold, s.hp = 1, 5, 5, 60, 80
    s.board = {'仙舟': 2, '持续伤害': 1}
    s.deployed = [BenchChar(slot=0, char_id='藿藿', faction='仙舟'),
                  BenchChar(slot=1, char_id='爻光', faction='仙舟')]
    s.bench = [BenchChar(slot=0, char_id='丹恒·饮月', faction='仙舟'),
               BenchChar(slot=1, char_id='青雀', faction='仙舟'),
               BenchChar(slot=2, char_id='娜塔莎', faction='护盾'),
               # ADR-0296 探针修正:上方注释判据「同名 2 份+店有第
               # 3 张」但旧探针只放了 1 份饮月 → 合成候选在任何
               # 生成器语义下都不可能触发(结构性不可绿);补第 2 份
               # 使判据成立(买入第 3 张 → merge 候选)。
               BenchChar(slot=3, char_id='丹恒·饮月', faction='仙舟'),
               # ADR-0316:pad 到槽位表定长
               None, None, None, None, None]
    s.shop = [ShopCard(x=1, faction='仙舟', name='丹恒·饮月', cost=2),
              ShopCard(x=2, faction='护盾', name='三月七', cost=1)]
    sess = StrategySession()
    # ADR-0336:旧载体探针形态(locked_line='jizi' 走线库派生)已随
    # line_strategy 删除失效——改用 v3_hoard 意向载体(生产真实形态):
    # hoard char_targets 含店卡 → buy 类候选生成。
    from sr_od.application.currency_war.kernel.cw_intention import HoardTarget
    sess.v3_intention = None
    sess.v3_hoard = HoardTarget(
        frozenset({'丹恒·饮月', '三月七'}), frozenset(), 'locked')
    sess.v3_core_names = {'丹恒·饮月'}
    for cand in generate_candidates(s, sess, DEFAULT_REGISTRY):
        if cand.merge:
            seen_classes.add('synthesize')
        elif cand.tag in ('line_carry', 'line_opportunistic',
                          'bridge_core', 'bond_fallback', 'carry_gate'):
            seen_classes.add('buy')
        elif cand.tag in ('off_target', 'for_gold', 'free_bench'):
            seen_classes.add('sell')
        else:
            seen_classes.add(cand.tag)   # levelup / refresh / deploy
    missing = ACTION_CLASSES - seen_classes
    if missing:
        violations.append(f'结构层:生成器未覆盖动作类 {sorted(missing)}')
    # ② 执行层(仅 decision_v2 批次辖)
    exec_classes: set[str] = set()
    is_d2 = False
    if ledgers:
        for rows in ledgers:
            for row in rows:
                for a in row.get('actions') or []:
                    r = a.get('reason') or ''
                    if r.startswith('d2_'):
                        is_d2 = True
                        if a.get('__type__') == 'BuyCard':
                            exec_classes.add(
                                'synthesize' if r.endswith('_merge')
                                else 'buy')
                        else:
                            exec_classes.add(a.get('__type__', ''))
        # ADR-0296:买映射为小写 'buy'(与结构层动作类名对齐),旧字面
        # {'BuyCard','LevelUp'} 里 BuyCard 永不可命中(buy≠BuyCard)
        # → 有买无升级的健康批也误报死路;LevelUp 账本行不带 d2_
        # reason(sim 序列化无 reason),故死路判据实际锚=buy。
        if is_d2 and 'buy' not in exec_classes:
            violations.append(
                f'执行层:d2 批次零 BuyCard/LevelUp(死路形态:'
                f'已执行类={sorted(exec_classes)})')
    return {'violations': len(violations), 'detail': violations,
            'struct_classes': sorted(seen_classes),
            'exec_classes': sorted(exec_classes) if is_d2 else None,
            'note': '结构层恒辖;执行层仅 d2_ 前缀批次辖,buy/levelup '
                    '必现,deploy/refresh/合成披露不辖'}



def check_decision_v2_arbiter_matrix() -> dict:
    """ADR-0291:仲裁器完备性审计表无空格(资源维×回合态维)。

    判据(ADR-0290 对抗修订④):``kernel.cw_registry`` 的审计矩阵
    每格=约束名(存在于 constraints 清单)或显式 ``('none', 原因)``
    声明;空格/未知约束名=违规。新增动作类型或资源维时本检查强制
    过检(通道制漏门病 r408/[32] 全是事后补的根治)。
    """
    from sr_od.application.currency_war.decision.decision_v2.arbiter import (
        build_audit_report,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    rep = build_audit_report(DEFAULT_REGISTRY)
    return {'violations': len(rep['violations']),
            'detail': rep['violations'],
            'matrix': rep['matrix'],
            'constraints': rep['constraints']}



def check_decision_v2_telemetry_contract() -> dict:
    """迁移审计批(可解释性遥测)(decision_v2 首超审计·题②):可解释性遥测契约锁。

    判据:``DecisionV2Strategy.decide_prep`` 执行后,
    ``session.last_candidate_scores`` 必须满足——
    ① 轮次戳新鲜(last_candidate_scores_round == 当前轮);
    ② 键格式可解析(``r<轮>:<标签>:<desc>`` ——遥测判读可用性
       的地基,键崩坏=判读端整字段不可读);
    ③ 分值为数值;
    ④ 有采纳动作时至少 1 个键(采纳必须留痕)。
    披露(非违规):键数与分值多样性——迁移审计批(可解释性遥测) 实测均分仅 ~1.1 键/
    ~1.0 个不同分值(只记 accepted,看不到落选替代方案的分),
    「每轮候选×分数」的可解释性承诺只兑现一半,登记待策略域
    裁决(是否把 result.log 未采纳行也写入遥测)。
    """
    import re

    from sr_od.application.currency_war.decision.cw_strategy import StrategySession
    from sr_od.application.currency_war.decision.decision_v2.strategy import (
        DecisionV2Strategy,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        BenchChar,
        GameState,
        ShopCard,
    )
    # 探针:中局常态(金足/店有目标件/bench 有杂件)——必有采纳
    s = GameState()
    s.plane, s.round_num, s.level, s.gold, s.hp = 1, 5, 5, 60, 80
    s.board = {'仙舟': 2, '持续伤害': 1}
    s.deployed = [BenchChar(slot=0, char_id='藿藿', faction='仙舟'),
                  BenchChar(slot=1, char_id='爻光', faction='仙舟')]
    s.bench = [BenchChar(slot=0, char_id='丹恒·饮月', faction='仙舟'),
               BenchChar(slot=1, char_id='青雀', faction='仙舟'),
               None, None, None, None, None, None, None]   # ADR-0316 pad
    s.shop = [ShopCard(x=1, faction='仙舟', name='丹恒·饮月', cost=2),
              ShopCard(x=2, faction='护盾', name='三月七', cost=1)]
    sess = StrategySession()
    strat = DecisionV2Strategy()
    strat.update_target(s, sess, None)
    acts = strat.decide_prep(s, sess, None)
    scores = dict(getattr(sess, 'last_candidate_scores', {}) or {})
    violations: list[str] = []
    if getattr(sess, 'last_candidate_scores_round', -1) != s.round_num:
        violations.append(f'轮次戳陈旧: {sess.last_candidate_scores_round}'
                          f' != r{s.round_num}')
    key_re = re.compile(r'^r(\d+):([a-zA-Z_0-9]+):(.+)$')
    bad_keys = [k for k in scores if not key_re.match(k)]
    if bad_keys:
        violations.append(f'键格式不可解析: {bad_keys[:3]}')
    non_num = [k for k, v in scores.items()
               if not isinstance(v, (int, float))]
    if non_num:
        violations.append(f'分值非数值: {non_num[:3]}')
    if acts and not scores:
        violations.append(f'有采纳动作({len(acts)})但遥测零键(采纳未留痕)')
    return {'violations': len(violations), 'detail': violations,
            'n_actions': len(acts), 'n_keys': len(scores),
            'distinct_scores': len(set(scores.values())),
            'note': '批㉝:键均分稀薄(只记 accepted)为已登记披露,'
                    '待策略域裁决是否记未采纳行'}



def check_decision_v2_remedy_loop(ledgers: list[list[dict]]) -> dict:
    """迁移审计 w52(git 历史)(ADR-0326 §1.5-3):补偿连续放弃轮 ≥3 报警(设计容量不足
    信号)。

    判据(仅 d2_ 前缀批次辖):某局存在**连续 ≥3 轮** sim.
    remedy_abandoned=1(补偿趟事务性重验整组放弃)——连续放弃 =
    设计在持续产出「想补偿但补偿不上」的拒绝,弱序降级链尽头被反复
    打脸;单发放弃是合法(资源不足),连续 3 轮是结构信号(该窗口
    策略层缺变现/腾位杠杆)。

    变异自检:测试仓锁测试 monkeypatch 补偿趟(arbiter._run_
    remediation_pass 置空)或删 abandon 置位 → 去门变异必红
    (检查器自身由变异自检锁钉死;锁见 test_cw_w52_remediation.py)。
    """
    violations: list[str] = []
    is_d2 = False
    for rows in ledgers:
        if not rows:
            continue
        rows = sorted(rows, key=lambda x: x.get('round_num', 0))
        d2_here = any(
            (a.get('reason') or '').startswith('d2_')
            for row in rows for a in row.get('actions') or [])
        if d2_here:
            is_d2 = True
        if not d2_here:
            continue
        rid = rows[0].get('run_id', '?')
        run = 0
        for row in rows:
            if (row.get('sim') or {}).get('remedy_abandoned'):
                run += 1
                if run >= 3:
                    violations.append(
                        f'{rid}: r{row.get("round_num")} 起连续 '
                        f'{run} 轮补偿放弃(设计容量不足)')
                    break
            else:
                run = 0
    return {'violations': len(violations), 'detail': violations,
            'd2_batch': is_d2,
            'note': '连续放弃轮 ≥3 = 补偿趟结构失败信号(§1.5-3);'
                    '单发放弃合法(资源不足)'}



def check_decision_v2_crisis_gold_hoard(ledgers: list[list[dict]]) -> dict:
    """迁移审计批(可解释性遥测)(题①解剖·危机局指纹):危机态囤金零买入哨兵(披露级)。

    判据(仅 d2_ 前缀批次辖):某局存在轮 r∈[5,8] hp≤25(危机态),
    且从该轮起 ≥2 个后续轮 gold≥40 且这些轮零 BuyCard → 违规
    (息引擎门/满息地板把危机局锁进「囤金不补板」形态;迁移审计批(可解释性遥测)
    seeds 0-99 实测 20 危机局中 1 例完整形态 s1:hp17 金85 r5+
    零买只升)。披露级非 0 容忍:危机局买入大多仍有响应(18/20),
    本哨兵防的是「金在手板濒死却零买」这一最重形态的回归扩大。
    """
    violations: list[str] = []
    is_d2 = False
    for rows in ledgers:
        if not rows:
            continue
        rows = sorted(rows, key=lambda x: x.get('round_num', 0))
        d2_here = any(
            (a.get('reason') or '').startswith('d2_')
            for row in rows for a in row.get('actions') or [])
        if d2_here:
            is_d2 = True
        if not d2_here:
            continue
        rid = rows[0].get('run_id', '?')
        crisis_start = next((row['round_num'] for row in rows
                             if row.get('round_num', 0) >= 5
                             and row.get('hp', 99) <= 25), None)
        if crisis_start is None:
            continue
        tail = [row for row in rows
                if row.get('round_num', 0) >= crisis_start]
        hoard_rounds = [row for row in tail if row.get('gold', 0) >= 40]
        buys_tail = sum(1 for row in tail for a in row.get('actions') or []
                        if a.get('__type__') == 'BuyCard')
        if len(hoard_rounds) >= 2 and buys_tail == 0:
            violations.append(
                f'{rid}: r{crisis_start} 起 hp≤25 危机,'
                f'{len(hoard_rounds)} 轮金≥40 且尾段零买')
    return {'violations': len(violations), 'detail': violations,
            'd2_batch': is_d2,
            'note': '披露级:危机态囤金零买入(批㉝ 指纹 s1 形态);'
                    '仅 d2 批次辖'}



# --- 迁移审计批(供给-标签一致性)(供给 vs 标签审计):直通门标签-候选一致性 --------------------

def check_decision_v2_supply_label_consistency() -> dict:
    """迁移审计批(供给-标签一致性):engine_seed/pair/copy 全直通后,标签裁决与候选生成必须
    双向一致(0 容忍结构不变式)。

    背景:攻坚批「店里没有类 17 轮升并列第一(供给面约束)」论断的
    审计题——sim 实测(n=100,指纹 066c4185)M1(应放行但无候选)= 0,
    供给不稀疏(目标件零在场最长连轮 4,均值 1.2);本检查把该不变式
    固化为回归锁:**对探针态店内每张有名卡,买候选存在 ⟺ 未被
    copies_cap/copy_swap 豁免且 _buy_tag 非 None**。任一方向破坏
    (标签漏接 = M1;幽灵候选 = 生成器绕过豁免)即红。

    变异自检:测试仓锁测试 monkeypatch _buy_tag 关标签 → 必须涌现
    违规(去门变异必红)。
    """
    from sr_od.application.currency_war.decision.cw_strategy import StrategySession
    from sr_od.application.currency_war.decision.decision_v2 import candidates as _c
    from sr_od.application.currency_war.decision.decision_v2.candidates import (
        generate_candidates,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        BenchChar,
        BuyCard,
        GameState,
        ShopCard,
        pad_bench,
    )

    def _mk(plane: int, rn: int, level: int, gold: int, bench, shop,
            line: str | None, bridge: str | None, dep=()):
        st = GameState()
        st.plane, st.round_num = plane, rn
        st.level, st.gold, st.hp = level, gold, 80
        st.bench = pad_bench(list(bench))   # ADR-0316 槽位表
        st.shop = list(shop)
        st.deployed = list(dep)
        sess = StrategySession()
        sess.locked_line = line
        sess.bridge_id = bridge
        return st, sess

    from types import SimpleNamespace as _NS

    def _dep(name: str, faction: str, slot: int = 0):
        return _NS(char_id=name, faction=faction, star=1, slot=slot,
                   position_pref='back', equips=())

    # 探针态覆盖:无方向种子态(引擎门)/ 锁线态(carry+凑档)/
    # 副本上限态(copies_cap)/ bench 杂件(卖通道不被误判为买候选)/
    # 第 4 态(`w300_dup_ruling/` 压库副本态,V-B1.3):deployed 已持目标外引擎阵营
    # 件同名 + 店出同角色 cost=1 副本(plane1/低 level/band 内)。
    # 通道关(DEFAULT_REGISTRY)下该卡被守卫拦=无候选,一致性不变式
    # 照辖;通道开的行为面由 check_w300_press_channel_probe 专检。
    probes = [
        _mk(1, 2, 3, 20,
            [BenchChar(slot=0, char_id='青雀', faction='仙舟')],
            [ShopCard(x=1, faction='仙舟', name='刃', cost=3),
             ShopCard(x=2, faction='巡猎', name='希儿', cost=5)],
            None, None),
        _mk(1, 5, 5, 40,
            [BenchChar(slot=0, char_id='藿藿', faction='仙舟'),
             BenchChar(slot=1, char_id='娜塔莎', faction='护盾')],
            [ShopCard(x=1, faction='智识', name='姬子', cost=4),
             ShopCard(x=2, faction='仙舟', name='三月七', cost=1)],
            'jizi', None),
        _mk(1, 6, 6, 30,
            [BenchChar(slot=0, char_id='青雀', faction='仙舟'),
             BenchChar(slot=1, char_id='青雀', faction='仙舟'),
             BenchChar(slot=2, char_id='青雀', faction='仙舟')],
            [ShopCard(x=1, faction='仙舟', name='青雀', cost=1)],
            'jizi', None),
        _mk(1, 2, 3, 15,
            [],
            [ShopCard(x=1, faction='仙舟', name='青雀', cost=1)],
            None, None,
            dep=[_dep('青雀', '仙舟')]),
    ]
    violations: list[str] = []
    for pi, (st, sess) in enumerate(probes):
        cands = generate_candidates(st, sess, DEFAULT_REGISTRY)
        cand_names = {c.action.card.name for c in cands
                      if isinstance(c.action, BuyCard)}
        for card in (st.shop or []):
            if not card.name:
                continue
            copies = _c._star_weighted_copies(card.name, st)
            blocked = (copies >= DEFAULT_REGISTRY.copies_cap
                       or _c._copy_swap_blocked(card, st, sess,
                                                DEFAULT_REGISTRY))
            tag = None if blocked else _c._buy_tag(
                card, st, sess, DEFAULT_REGISTRY)
            has_cand = card.name in cand_names
            if tag is not None and not has_cand:
                violations.append(
                    f'探针{pi} p{st.plane}r{st.round_num} {card.name}: '
                    f'tag={tag} 但无买候选(M1 标签漏接)')
            if tag is None and has_cand:
                violations.append(
                    f'探针{pi} p{st.plane}r{st.round_num} {card.name}: '
                    f'无标签/被豁免但存在买候选(幽灵候选)')
    return {'violations': len(violations), 'detail': violations,
            'note': '批㉞ 供给 vs 标签一致性:候选存在⟺标签非None且'
                    '未被 copies_cap/copy_swap 豁免;红 = 直通门回归'}


# (换线存活门三检查器 check_line_gate_decision_bits /
#  check_line_switch_midgame_bucket / check_line_gate_starvation_anchor
#  已随 C4 开关族删除——旧方案清退批,清查报告 OLD_MIX_AUDIT §1.3;
#  消费端 line_gate_blocked/cf_blocked 账本位与 gate_hold/
#  gate_relock 事件随门机械同批退役。)
