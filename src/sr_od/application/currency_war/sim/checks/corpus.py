"""语料/锚点再生检查(w300/prefork/poverty/难度曲线/胜率表族,分包期6 拆分)。"""

from __future__ import annotations

from sr_od.application.currency_war.sim.checks.calib import ANCHOR_REGISTRY_N300
from sr_od.application.currency_war.sim.checks.pool import DELTA_POOL_COVERAGE_MIN_N

# --- 清偿批:锚登记扩展(第二参照段 / 低可见通道 / 噪声带) -------

# 批⑭ anchor_seed_portability_n600:第二参照段(seed 300-899,
# n=600,池指纹 e19afdfa4173077e 与当时锚一致)——未来锚漂移先分
# 「种子段噪声 vs 行为变化」(批⑭ F4:全指标在合并噪声带内,
# 锚可跨种子段引用)。
ANCHOR_REGISTRY_S300_N600: dict = {
    'pool_fingerprint_prefix': 'e19afdfa4173077e',
    'recorded': '2026-08-23(批⑭ F4,n=600,seed 300-899)',
    'metrics': {
        'engines2_by_r6': 0.240,
        'avg_final_hp': 27.89,
        'hp_ge_60': 0.025,
        'recipe5_by_r6': 0.563,
        'avg_refreshes': 1.125,   # 槽消费(ADR-0284)前口径
    },
    'note': '槽消费修复(ADR-0284)前读数;refresh 与新锚'
            '(3.943)不可直接对照,作历史段保留',
}


# 批⑳/批㉑ anchor_lowchannel_registry:低可见通道登记(防「headline
# 一致」掩盖低层移动),**每条必带 commit 归因注记**(批㉑ 补充:
# 不带归因 = 下批把 sim 真实化误读为策略漂移)。
ANCHOR_LOWCHANNEL_REGISTRY: dict = {
    'recorded': '2026-08-24(ADR-0289 清偿批登记)',
    'metrics': {
        # 末金:pre-r416 51.86 → r419 超容买守卫后 58.08(守卫拦截
        # 滞留,ADR-0283/0285;净口径见 check_sim_endgold_calib)
        'endgold_total_avg': {'pre_r416': 51.86, 'since_r419': 58.08},
        # 成型-hp 耦合 diff:+0.9(批⑪ 校准前)→ +4.28(批⑫ merge
        # +win 校准,ADR-0276/0277)→ +11.81(ADR-0279 rung 分桶)
        'formation_hp_coupling_diff': {
            'pre_adr0276': 0.9, 'adr0276_277': 4.28, 'adr0279': 11.81},
    },
}


# 批⑯ anchor_segment_noise_band:n=300 段间噪声带(A/B 判读门槛
# 引用此带;跨带差异才可叙述为行为变化)。
ANCHOR_SEGMENT_NOISE_BAND: dict = {
    'recorded': '2026-08-23(批⑯ F2)',
    'band': {'hp_ge_60': 0.02, 'avg_final_hp': 1.6},
}



def check_anchor_seed_portability_n600(report: dict) -> dict:
    """批⑭ anchor_seed_portability_n600(第二参照段;披露)。

    判据(设计表原文):本批 s300-899 读数登记为第二参照段
    (指纹必附);判据 = 未来锚漂移报告能区分种子段噪声与行为
    变化。本检查披露 report 与两段锚的距离(同段小幅=种子噪声;
    双段同向大幅=行为变化)。drift 非违规(登记制语义)。
    """
    out: dict = {'violations': 0}
    for name, reg in (('n300', ANCHOR_REGISTRY_N300),
                      ('s300_n600', ANCHOR_REGISTRY_S300_N600)):
        drift = {k: round(float(report[k]) - v, 4)
                 for k, v in reg['metrics'].items()
                 if k in report and isinstance(report[k], (int, float))}
        out[f'{name}_drift'] = drift
        out[f'{name}_fp_match'] = str(
            report.get('pool_fingerprint', '')).startswith(
            reg['pool_fingerprint_prefix'])
    out['note'] = '同段小幅=种子噪声;双段同向大幅=行为变化(批⑭ F4)'
    return out



def check_anchor_lowchannel_registry(report: dict) -> dict:
    """批⑳/批㉑ anchor_lowchannel_registry(低可见通道;披露)。

    判据(设计表原文):anchor_registry 除 headline 外纳入
    formation_hp_coupling/endgold 两个已见漂移的低可见通道,防
    「headline 一致」掩盖低层移动;**须连 commit 归因注记**(批㉑)。
    report 无对应键( cw_sim 接线待合流)→ 只披露登记表在位;
    有则并列披露漂移(归因链见 ANCHOR_LOWCHANNEL_REGISTRY 注)。
    """
    m = ANCHOR_LOWCHANNEL_REGISTRY['metrics']
    out: dict = {'violations': 0, 'registry_in_place': True}
    if 'sim_endgold_calib' in report:
        ec = report['sim_endgold_calib']
        if isinstance(ec, dict) and 'sim_avg_endgold' in ec:
            out['endgold_now'] = ec['sim_avg_endgold']
    if 'formation_hp_coupling_sentinel' in report:
        fs = report['formation_hp_coupling_sentinel']
        if isinstance(fs, dict) and 'diff' in fs:
            out['formation_diff_now'] = fs['diff']
    out['registered'] = m
    return out



def check_anchor_segment_noise_band(report_a: dict,
                                    report_b: dict) -> dict:
    """批⑯ anchor_segment_noise_band(段间噪声带;披露)。

    判据(设计表原文):n=300 段间噪声带登记(hp_ge_60 ±0.02/
    avg_final_hp ±1.6),A/B 判读门槛引用此带。本检查对两份报告
    的 headline 差值打标:带内=段间噪声(不得叙述为行为变化),
    带外=可叙述(池指纹须一致才可比)。
    """
    band = ANCHOR_SEGMENT_NOISE_BAND['band']
    marks: dict[str, dict] = {}
    for k, b in band.items():
        if k in report_a and k in report_b:
            d = float(report_a[k]) - float(report_b[k])
            marks[k] = {'diff': round(d, 4),
                        'in_band': abs(d) <= b, 'band': b}
    return {'violations': 0, 'marks': marks,
            'fp_same': report_a.get('pool_fingerprint')
            == report_b.get('pool_fingerprint'),
            'note': '带内=段间噪声;带外且指纹一致才可叙述行为变化'}



def check_rare_metric_min_n(metrics: dict[str, tuple[float, int]],
                            min_n: int = 60) -> dict:
    """批④ rare_metric_min_n(稀有指标 n 与噪声带标注;工具型)。

    判据(设计表原文):报告引擎(engines2/trio3 类)自带 n 与
    噪声带标注;n=60 时差值<带宽打「未定」标。入参 = 指标名 →
    (值, n);n<min_n 的指标标「未定」(undetermined),防小批
    稀有指标被当作结论引用。
    """
    undetermined = [k for k, (_, n) in metrics.items() if n < min_n]
    return {'violations': 0, 'min_n': min_n,
            'undetermined': undetermined}



ADR0266_GUARD_ANCHOR: dict = {
    'recorded': '2026-08-24(批⑤ F2 关闭臂 B2;n=300 配对)',
    'arm': 'B2 = v2_ever_full_interest 恒 True(ADR-0266 关闭臂)',
    # 账本量(不受 Δ 池混杂,可裁):总利息 -1.63,278/300 局降
    'interest_delta': -1.63, 'interest_down_games': 278,
    # hp 受 Δ池深度 6 边界混杂(批⑤ 声明):方向参考、幅度存疑
    'final_hp_delta': -1.22,
}



def check_adr0266_ab_guard(interest_delta: float,
                           hp_delta: float) -> dict:
    """批⑤ adr0266_ab_guard(ADR-0266 关闭臂回归锚;披露)。

    判据(设计表原文):B2 差值方向(interest↓ final_hp↓)作防
    倒退对照——未来任何「重开追级/弱化息引擎门」的 A/B 若复现
    interest↓→hp↓ 同向形态(即门的保护效应消失),提示 ADR-0266
    语义回归。账本量口径(interest 可裁;hp 方向参考,Δ池混杂
    声明见批⑤)。
    """
    same_shape = (interest_delta < 0 and hp_delta < 0)
    return {'violations': 0,
            'interest_delta': interest_delta,
            'hp_delta': hp_delta,
            'adr0266_closure_shape': same_shape,
            'note': '关闭臂形态(interest↓+hp↓)= ADR-0266 保护'
                    '效应存在;主臂出现该形态 = 门被绕过的回归信号'}



def check_w300_press_channel_probe() -> dict:
    """`w300_dup_ruling/` press 通道探针(design v3 V-B1.3/V-B1.5/V-B2.3/V-B6):
    压库副本态在两臂下的候选产出不变式 + E05 带外灰出反例。

    - arm0(默认注册表,通道关):压库副本被守卫拦=无候选(零漂移);
    - armA(press_channel_enabled=True):同态候选产出(V-B1.5「探针态
      必须产出候选」=空臂红线)、_buy_tag='copy_press'(V-B2 新具名
      标签);评分路由已随 ADR-0427 增补节定谳清理,本探针只锁机制面
      (标签落点 + 守卫放行),不再断言评分正分;
    - band 外反例(cost=3):两臂都不产出候选(V-B6 撤销插件臂后
      E05/E07 维持「不买」;防豁免臂过宽回归)。
    """
    from dataclasses import replace
    from types import SimpleNamespace

    from sr_od.application.currency_war.decision.cw_strategy import StrategySession
    from sr_od.application.currency_war.decision.decision_v2.candidates import (
        _buy_tag,
        generate_candidates,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        BuyCard,
        GameState,
        ShopCard,
    )

    st = GameState()
    st.plane, st.round_num = 1, 2
    st.level, st.gold, st.hp = 3, 15, 80
    st.bench = []
    st.deployed = [SimpleNamespace(char_id='刃', faction='星核猎手', star=1,
                                   slot=0, position_pref='back', equips=())]
    st.shop = [ShopCard(x=1, faction='星核猎手', name='刃', cost=1),
               ShopCard(x=2, faction='银河学者', name='黑塔', cost=3)]
    sess = StrategySession()
    # 锁线帧(方向不含仙舟):生产路径形态——'copy'/'pair' 既有豁免
    # 通道语义先于 press 臂(V-B2.1 放序),只有方向门拦下的目标外
    # 副本才落 'copy_press';裸 session 冷启动会让 pair_wants 先命中。
    from sr_od.application.currency_war.kernel.cw_intention import (
        HoardTarget,
        IntentionState,
    )
    ist = IntentionState()
    ist.phase = 'locked'
    ist.locked_comp = '姬子列车'
    sess.v3_intention = ist
    sess.v3_hoard = HoardTarget(
        frozenset({'姬子·启行', '三月七', '花火', '瓦尔特'}),
        frozenset(), 'locked')
    sess.v3_core_names = {'姬子·启行'}
    sess.target_comp = SimpleNamespace(factions=('列车同行',),
                                       core_chars=('姬子·启行',))

    def _names(reg) -> set[str]:
        return {c.action.card.name for c in generate_candidates(st, sess, reg)
                if isinstance(c.action, BuyCard)}

    def _tag(reg, card) -> str | None:
        return _buy_tag(card, st, sess, reg)

    arm_a = replace(DEFAULT_REGISTRY, press_channel_enabled=True)
    # arm0:显式注入通道关——开臂后 DEFAULT_REGISTRY 默认即通道开,直接拿它当
    # 「通道关零漂移」基线的前提失效(迁移审计 w374(git 历史) 开臂锁组同步)
    arm0 = replace(DEFAULT_REGISTRY, press_channel_enabled=False)
    violations: list[str] = []
    # arm0:通道关零漂移(守卫拦)
    if '刃' in _names(arm0):
        violations.append('arm0:通道关时压库副本产出候选(零漂移破)')
    # armA:候选产出(V-B1.5)+标签(评分路由已删,见函数 docstring)
    if '刃' not in _names(arm_a):
        violations.append('armA:探针态未产出压库副本候选(空臂红线)')
    else:
        if _tag(arm_a, st.shop[0]) != 'copy_press':
            violations.append(
                f"armA:标签={_tag(arm_a, st.shop[0])} ≠ copy_press")
    # 反例:cost=3 band 外(E05/E07 灰出,V-B6)两臂都无候选
    st2 = GameState()
    st2.plane, st2.round_num = 1, 2
    st2.level, st2.gold, st2.hp = 3, 15, 80
    st2.bench = []
    st2.deployed = [SimpleNamespace(char_id='黑塔', faction='银河学者',
                                    star=1, slot=0, position_pref='back',
                                    equips=())]
    st2.shop = [ShopCard(x=1, faction='银河学者', name='黑塔', cost=3)]
    for reg, label in ((arm0, 'arm0'), (arm_a, 'armA')):
        got = {c.action.card.name for c in generate_candidates(st2, sess, reg)
               if isinstance(c.action, BuyCard)}
        if '黑塔' in got:
            violations.append(f'{label}:band 外副本(cost=3)产出候选'
                              '(E05 灰出被破)')
    return {'violations': len(violations), 'detail': violations,
            'note': 'W300 press 通道探针:压库副本 arm0 关/armA 产出'
                    '+copy_press 标签;band 外反例两臂皆拒'}



# --- 批㊱ 检查项(2026-08-24;供给回声销账审计 / 三臂基线) -------------

def check_paired_prefork_wave_identity(ledgers_a: list[list[dict]],
                                       ledgers_b: list[list[dict]],
                                       ) -> dict:
    """批㊱:同 seed 双臂配对的「分叉前牌面恒等」不变式(0 容忍;
    批㊲ 扩全波)。

    背景(供给回声 61.6%→59.4% 销账审计,n=100 @066c4185):两臂策略
    均为确定性策略时,同 seed 的 RNG 流在**首轮动作差异出现之前**
    必须同源——任一轮只要此前两臂的动作序列(买/卖/刷/升/部署,
    按账本 __type__ 逐条)完全一致,该轮**全部牌面波**(含刷新后
    的第 2+ 波)必须逐位一致;分叉后的牌面/后续波差异(含刷新)
    是合法回声。违规 = sim 决策段在分叉前不对称消费 RNG,或策略侧
    引入隐藏随机性——此时「供给回声」「同 seed 配对差」类指标的
    合法性前提破裂(测得的差可能是引擎噪声而非策略效应)。

    **批㊲ 波覆盖修正**:旧版只比首波(waves[0])——同轮两臂都
    RefreshShop(动作 sig 一致)但刷新产生的**新波内容**不对称时,
    旧版漏检(下一轮首波是新抽,可能巧合一致)。全波比较后该
    漏检面闭合(变异锁:第二波篡改必红)。**比较顺序 = 三段式**
    (首波→动作序→剩余波):波是本轮动作的产物,轮内动作已分叉
    时波差是分叉结果(合法回声),只有「首波」先于本轮动作恒比、
    「剩余波」在动作序一致后才比——顺序反了会把「刷新次数不同」
    误报为 RNG 不对称(批㊲ 真 3 seed 双臂实测 game2 r1 修正)。

    交付口径:探针配对态不变式(需两臂账本,不入 run_batch_level_checks
    单臂签名;锁测试以 v1/v2 双臂直跑钉死 + 篡改变异必红)。
    """
    def _waves(rows: list[dict]) -> dict[int, list[list[str]]]:
        out: dict[int, list[list[str]]] = {}
        for row in rows:
            waves = (row.get('sim') or {}).get('shop_waves') or []
            out[row.get('round_num')] = [
                [c.get('name') for c in (w.get('cards') or [])]
                for w in waves]
        return out

    def _act_sig(rows: list[dict]) -> dict[int, list[tuple]]:
        out: dict[int, list[tuple]] = {}
        for row in rows:
            sig: list[tuple] = []
            for a in row.get('actions') or []:
                t = a.get('__type__')
                if t == 'BuyCard':
                    sig.append(('B', (a.get('card') or {}).get('name'),
                                (a.get('card') or {}).get('cost')))
                elif t == 'SellBench':
                    sig.append(('S', a.get('bench_idx')))
                else:
                    sig.append((t,))
            out[row.get('round_num')] = sig
        return out

    violations: list[str] = []
    for gi, (ra, rb) in enumerate(zip(ledgers_a, ledgers_b, strict=False)):
        wa, wb = _waves(ra), _waves(rb)
        sa, sb = _act_sig(ra), _act_sig(rb)
        diverged = False
        for rn in sorted(set(sa) | set(sb)):
            if diverged:
                break   # 分叉后差异合法,不再检查
            # 三段式(批㊲ 修正比较顺序):
            # ① 首波 = 本轮动作**之前**的状态(继承上轮一致性要求),
            #    先比——本轮动作分叉不影响首波,首波不一致 = RNG 在
            #    决策前已不对称(批㊱ 原判据,保留);
            a0 = (wa.get(rn) or [None])[0]
            b0 = (wb.get(rn) or [None])[0]
            if a0 != b0:
                violations.append(
                    f'game{gi} r{rn}: 动作分叉前首波不一致'
                    f'(A={a0} B={b0})'
                    f'——分叉前 RNG 消费不对称/策略隐藏随机性')
                diverged = True
                continue
            # ② 本轮动作序不一致 = 分叉起点(本轮后续波是分叉产物,
            #    合法回声,不辖——先比波面会把「刷新次数不同导致的
            #    波数差」误报为违规,批㊲ 真 3 seed 双臂实测修正);
            if sa.get(rn) != sb.get(rn):
                diverged = True
                continue
            # ③ 动作序一致 → 刷新波(waves[1:])是同 RNG 流的产物,
            #    必须逐位一致(批㊲ 扩全波:旧版只比首波,同轮同刷
            #    但刷新产出不对称的形态漏检)。
            if wa.get(rn) != wb.get(rn):
                violations.append(
                    f'game{gi} r{rn}: 动作一致但波面(含刷新波)不一致'
                    f'(A={wa.get(rn)} B={wb.get(rn)})'
                    f'——分叉前 RNG 消费不对称/策略隐藏随机性')
                diverged = True
    return {'violations': len(violations), 'detail': violations,
            'note': '批㊱ 分叉前牌面恒等(批㊲ 扩全波+三段式顺序:'
                    '首波→动作序→剩余波);红 = sim/策略侧隐藏随机性'}



# --- 批㊲ 检查项(2026-08-25;ADR-0306 Δ池扩容批对抗审计) -------------


def check_delta_pool_poverty_selfconsistency(pool_map: dict,
                                             meta: dict | None) -> dict:
    """批㊲ 检查项:贫困披露(bucket_poverty)↔ 池内容**双向**结构对拍。

    背景(ADR-0306 件4 判据漏洞):``check_delta_pool_bucket_coverage``
    的披露豁免靠**字符串集合精确匹配**——生成器(tools/cw/
    gen_delta_pool_snapshot ``_poverty_list``)与检查器两边独立
    f-string 拼串,格式漂移(半/全角、空格、措辞)即静默失配,
    「贫困须披露」防线形同虚设;且只查「池贫困→披露」单方向,
    披露了池中不存在/不贫困桶(过期披露)无人辖。本检查:
    - **反向解析** META ``bucket_poverty`` 每条串(结构化元组),
      解析失败 = 违规(格式漂移可见,不再静默);
    - **双向对拍**(与生成器同判据:battle rung 域 0-4 缺桶/薄桶 +
      非 battle 池内桶 n<``DELTA_POOL_COVERAGE_MIN_N``):
      池贫困未披露 → 违规;披露了池不贫困/不存在的桶 → 违规
      (过期披露);n 值不符 → 违规。
    - ``meta=None``(auto/JSON 回放无披露载体)/ 空池不辖(同
      coverage 先例)。
    调用方显式调(测试/审计脚本;快照自洽锁消费)。
    """
    import re
    #: 贫困披露串反向解析格式(与生成器 ``_poverty_list`` 的拼串格式
    #: 对偶——解析失败 = 生成器/检查器两侧拼串逻辑漂移,单源断裂可见)。
    poverty_re = re.compile(
        r'^(?:p2:)?(?P<nt>[a-z]+):桶(?P<b>\d+)\((?:n=(?P<n>\d+)|缺)\)$')
    if meta is None:
        return {'violations': 0, 'note': '无披露载体(meta=None)不辖'}
    if not any((pool_map or {}).values()):
        return {'violations': 0, 'note': '池空(fallback/历史快照)不辖'}
    violations: list[str] = []
    # ADR-0362(`w157_p2/`):``p2:`` 前缀条目 = plane≥2 桶贫困披露
    # (生成器单列,判据只辖 plane=1)——跳过双向对拍,仅计入解析
    # 可见性(P2 桶 n<5 全贫困是语料边界,不是披露断裂)。
    disclosed: set[tuple[str, int, str, int]] = set()   # (nt, 桶, kind, n)
    unparseable: list[str] = []
    p2_disclosed: list[str] = []
    for s in (meta.get('bucket_poverty') or []):
        m = poverty_re.match(str(s))
        if not m:
            unparseable.append(str(s))
            continue
        if str(s).startswith('p2:'):
            p2_disclosed.append(str(s))
            continue
        n = m.group('n')
        disclosed.add((m.group('nt'), int(m.group('b')),
                       'miss' if n is None else 'thin',
                       -1 if n is None else int(n)))
    if unparseable:
        violations.append(f'披露串不可解析 {unparseable[:3]}'
                          f'(生成器/检查器拼串格式漂移——单源断裂)')
    # 池侧:现算贫困(与生成器 _poverty_list 同判据)
    poor: set[tuple[str, int, str, int]] = set()
    battle = pool_map.get('battle') or {}
    for rg in range(0, 5):
        v = battle.get(rg) or []
        if len(v) < DELTA_POOL_COVERAGE_MIN_N:
            poor.add(('battle', rg, 'miss' if not v else 'thin',
                      0 if not v else len(v)))
    for nt, buckets in sorted((pool_map or {}).items()):
        if nt == 'battle':
            continue
        for b, v in buckets.items():
            if len(v) < DELTA_POOL_COVERAGE_MIN_N:
                poor.add((nt, int(b), 'thin', len(v)))
    # 双向 diff
    undisclosed = sorted(
        t for t in poor
        if (t[0], t[1], t[2]) not in {(d[0], d[1], d[2]) for d in disclosed})
    if undisclosed:
        violations.append(f'池贫困未披露 {undisclosed[:4]}')
    stale = sorted(
        d for d in disclosed
        if (d[0], d[1], d[2]) not in {(p[0], p[1], p[2]) for p in poor})
    if stale:
        violations.append(f'披露了池中不贫困/不存在的桶 {stale[:4]}'
                          f'(过期披露)')
    n_mismatch = sorted(
        p for p in poor if p[2] == 'thin'
        for d in disclosed
        if (p[0], p[1], p[2]) == (d[0], d[1], d[2]) and p[3] != d[3])
    if n_mismatch:
        violations.append(f'披露 n 值与池不符 {n_mismatch[:4]}')
    return {'violations': len(violations), 'detail': violations,
            'disclosed_n': len(disclosed), 'pool_poor_n': len(poor),
            'unparseable': unparseable[:3],
            'p2_disclosed_n': len(p2_disclosed),
            'note': '贫困披露↔池内容双向结构对拍(批㊲);'
                    '红 = 披露断裂/格式漂移'}



#: (批㊲ boss_win_p_cache_freshness 已随 ADR-0308 废除:rung 外推
#: 机制被 迁移审计 w31(git 历史) 节点胜率阶梯替换,无进程内缓存可查。)


def check_boss_rung_corpus_sample_gate(
        boss_rows: list[dict]) -> dict:
    """批㊲ 检查项:boss 结算行 rung×killed 语料样本门(披露型)。

    背景(ADR-0306 件2 跨节点外推反证;批㉗ F6「outcomes 侧另行
    统计」的落地):ADR-0306 的 rung≥3 掷胜率 = **battle** rung2
    实测 0.667(4/6)跨节点外推;而语料 boss 行自带 killed 实测可
    作**同节点**对照——批㊲ 探针实证(2026-08-25 语料,191 行):
    boss rung0=0/5、**rung1=0/9**(battle rung1=12/24=0.5,两 CI
    不相交)、rung2=1/2(0.5)——同 rung 下 battle 胜率不可平移到
    boss,跨节点外推方向系统性偏乐观;且 **boss rung2 同节点外推
    源(0.5,n=2)存在**但 ADR-0306 Considered Options 未评估。

    判据:吃 boss 配对行(``{'rung': int, 'killed': bool|None}``;
    配对口径与生成器同源:board_before + decisions deployed join
    算 _engines_count),逐 rung 桶披露 n/killed_known/killed_
    unknown/win_killed;直拟合样本门(批㉗ F6:n≥3 known/桶)
    逐桶标注——**门未就绪前 boss_win_p 的 rung≥3 外推结论只可
    标「单点外推敏感度」**(判读纪律,非违规)。唯一违规判据:
    行非空但 killed_known 总数 = 0(boss killed 采集断裂,外推
    无同节点对照地基)。空行不辖。
    """
    if not boss_rows:
        return {'violations': 0, 'note': '无 boss 配对行,不辖'}
    buckets: dict[int, dict] = {}
    for r in boss_rows:
        rg = int(r.get('rung') or 0)
        s = buckets.setdefault(rg, {'n': 0, 'known': 0, 'win': 0,
                                    'unk': 0})
        s['n'] += 1
        k = r.get('killed')
        if k is None:
            s['unk'] += 1
        else:
            s['known'] += 1
            if k:
                s['win'] += 1
    total_known = sum(s['known'] for s in buckets.values())
    violations: list[str] = []
    if total_known == 0:
        violations.append(f'{len(boss_rows)} 行 boss 配对样本 '
                          f'killed 全 None(采集断裂——外推无同节点'
                          f'对照地基,批㊲)')
    out_buckets = {
        str(rg): {'n': s['n'], 'killed_known': s['known'],
                  'killed_unknown': s['unk'],
                  'win_killed': round(s['win'] / s['known'], 4)
                  if s['known'] else None,
                  'direct_fit_ready': s['known'] >= 3}
        for rg, s in sorted(buckets.items())}
    ge3 = {rg: s for rg, s in buckets.items() if rg >= 3}
    return {
        'violations': len(violations), 'detail': violations,
        'buckets': out_buckets, 'rows': len(boss_rows),
        'rung3plus_exists': bool(ge3),
        'note': '直拟合门(known≥3/桶)未全就绪前,rung≥3 掷胜外推'
                '只可标「单点外推敏感度」(批㉗ F6);批㊲ 反证:'
                'battle→boss 同 rung 胜率不可平移(rung1 0.5 vs 0/9)',
    }



# --- 批37 检查项(2026-08-25;难度读链翻转 09cf8296 判读鲁棒性) -----


def check_difficulty_curve_live_contamination(rows: list[dict]) -> dict:
    """批37 检查项:难度曲线 live 帧污染守卫(判读面;语料级显式调)。

    背景(迁移审计批 F1 读链翻转,commit 09cf8296):``enemy_difficulty``
    旧链 = session 简报恒值(实测 108)压死逐帧真读,35 局 1785 帧
    零爬升样本;翻转后真读优先 + ``enemy_difficulty_live`` 保真位。
    批37 语料实证(首真值局 run_20260824_100252,36 帧):live 真值
    恒 8(plane1 r1-2,12 帧)与 non-live 兜底恒 108(24 帧)并存
    ——**全帧口径的爬升/均值是垃圾**(max−min=100 全来自假恒值)。

    判据(吃 decisions 行 ``{'plane','round_num','enemy_difficulty',
    'enemy_difficulty_live'}``;live 位缺失按 non-live 处理并单列):
    - **污染违规**:live 帧存在且 non-live 帧取值集与 live 真值集
      不相交(non-live 兜底值混入会制造假尖峰/假爬升)——该 run 的
      全帧难度口径判废,必须 live-only 过滤;
    - **schema 违规**:有难度读数但 live 位缺失(翻转后 schema 必须
      携带保真位;调用方选窗时对历史局(翻转前)自行豁免);
    - 全 live / 无难度读数 / 空行 → 不辖(披露 live 覆盖率)。
    """
    nn = [r for r in rows if r.get('enemy_difficulty') is not None]
    if not nn:
        return {'violations': 0, 'note': '无难度读数帧,不辖',
                'nonnull': 0}
    live = [r for r in nn if r.get('enemy_difficulty_live') is True]
    nonlive = [r for r in nn if r.get('enemy_difficulty_live') is not True]
    missing_flag = [r for r in nn
                    if r.get('enemy_difficulty_live') is None]
    violations: list[str] = []
    live_vals = sorted({r.get('enemy_difficulty') for r in live})
    nonlive_vals = sorted({r.get('enemy_difficulty') for r in nonlive})
    if missing_flag:
        violations.append(
            f'{len(missing_flag)} 帧有难度读数但缺 enemy_difficulty_live '
            f'保真位(09cf8296 后 schema 必携;历史局由调用方豁免)')
    if live and nonlive and not (set(live_vals) & set(nonlive_vals)):
        climb_all = max(r.get('enemy_difficulty') for r in nn) \
            - min(r.get('enemy_difficulty') for r in nn)
        violations.append(
            f'live 真值 {live_vals} 与 non-live 兜底值 {nonlive_vals} '
            f'不相交且并存(全帧爬升口径 {climb_all} 全为假恒值污染,'
            f'判读必须 live-only 过滤,批37)')
    # 批39 note 级:live 与 non-live 并存即使值集相交也是部分污染
    # (live{8}+nonlive{8,108} 型——假 108 兜底值藏进交集内,值集交集
    # 判据捕不到;批38 复审 P1/P2 实证静默放行)。不红(相交兜底无害
    # 不判废整段),但必须披露混帧计数与两组值集供调用方选窗。
    mixed_note: str | None = None
    if live and nonlive:
        mixed_note = (
            f'live {len(live)} 帧 {live_vals} 与 non-live '
            f'{len(nonlive)} 帧 {nonlive_vals} 并存(批39 note 级部分'
            f'污染披露:值集相交≠无污染,混帧段全帧口径仍须 live-only '
            f'过滤,假兜底值可藏于交集内)')
    return {
        'violations': len(violations), 'detail': violations,
        'nonnull': len(nn), 'live_n': len(live), 'nonlive_n': len(nonlive),
        'live_vals': live_vals, 'nonlive_vals': nonlive_vals,
        'mixed_note': mixed_note,
        'live_seq': [(r.get('plane'), r.get('round_num'),
                      r.get('enemy_difficulty')) for r in live][:12],
        'note': '难度曲线 live 帧污染守卫(批37;批39 补部分污染 note '
                '级披露);红 = 假恒值混入/保真位缺失——全帧难度口径'
                '判废;mixed_note 非空 = 混帧需 live-only 选窗',
    }



# --- 批38 检查项(2026-08-25;win_model M1 训练表特征面审计) -----


_WIN_TABLE_NUMERIC_FEATURES = (
    'char_count', 'star_sum', 'equip_count', 'total_cost', 'max_tier')



def _point_biserial(xs: list[float], ys: list[int]) -> float | None:
    """点二列相关(特征×二值标签);样本不足或零方差返 None。"""
    n = len(xs)
    if n < 3:
        return None
    mu_x = sum(xs) / n
    mu_y = sum(ys) / n
    sx = (sum((x - mu_x) ** 2 for x in xs) / n) ** 0.5
    sy = (sum((b - mu_y) ** 2 for b in ys) / n) ** 0.5
    if sx == 0 or sy == 0:
        return None
    cov = sum((x - mu_x) * (b - mu_y)
              for x, b in zip(xs, ys, strict=True)) / n
    return cov / (sx * sy)



def check_win_train_table_feature_health(rows: list[dict]) -> dict:
    """批38 检查项:win_model 训练表特征健康审计(训练前门;语料级显式调)。

    背景(win_model M1 第一段已合入 f1836d71;批38 实测 111 行训练表,
    报告 sim_压测_批38):``equip_count`` 全 0(零方差,装备维对 M1 无
    贡献——replay 语料 10927 个 deployed 条目仅 123 个(1.1%)有装备,
    写端正常,是语料面事实而非 bug);``total_cost``/``star_sum``/
    ``char_count`` 与 killed 的点二列相关近零且符号为负(-0.04/-0.06/
    -0.02,完成度代理在 A8 早期语料无区分度),唯一正分离特征
    ``max_tier``(r=+0.23)但 tier≥2 样本仅 3 例——高成型区零地基,
    与批㊲ boss 语料样本门同型的覆盖缺口。

    判据(吃训练表行 ``{'char_count','star_sum','equip_count',
    'total_cost','max_tier','killed'}``;killed 必须全 bool):
    - **零方差违规**:_WIN_TABLE_NUMERIC_FEATURES 中任一特征在表内
      取值恒一(该特征对模型无区分度,训练前必须剔除或显式豁免);
    - **tier 覆盖违规**:``max_tier>=2`` 样本 <3(高成型区外推无
      地基——与批㊲ check_boss_rung_corpus_sample_gate 同型的样本门,
      门未就绪前 win 概率对高成型阵容只可标「单点敏感度」);
    - **标签断裂违规**:killed 非 bool 的行存在(写端 schema 断裂);
    - 空表不辖;相关系数/正负占比只披露不判红(样本量小,方向性
      结论留给扩容后)。
    """
    if not rows:
        return {'violations': 0, 'note': '空训练表,不辖', 'rows': 0}
    violations: list[str] = []
    bad_label = [i for i, r in enumerate(rows)
                 if not isinstance(r.get('killed'), bool)]
    if bad_label:
        violations.append(f'{len(bad_label)} 行 killed 非 bool'
                          f'(写端 schema 断裂)')
    ys = [1 if r.get('killed') else 0 for r in rows
          if isinstance(r.get('killed'), bool)]
    feat_stats: dict[str, dict] = {}
    for key in _WIN_TABLE_NUMERIC_FEATURES:
        vals = [r.get(key) or 0 for r in rows]
        mu = sum(vals) / len(vals)
        zero_var = all(v == vals[0] for v in vals)
        feat_stats[key] = {
            'min': min(vals), 'max': max(vals), 'mean': round(mu, 3),
            'zero_variance': zero_var,
            'r_with_killed': _point_biserial(vals, ys)
            if len(vals) == len(ys) else None,
        }
        if zero_var:
            violations.append(
                f'特征 {key} 全表恒值 {vals[0]}(零方差无区分度——'
                f'训练前必须剔除或显式豁免,批38)')
    tier_ge2 = sum(1 for r in rows if (r.get('max_tier') or 0) >= 2)
    if tier_ge2 < 3:
        violations.append(
            f'max_tier>=2 样本仅 {tier_ge2} 例(<3,高成型区外推零地基;'
            f'win 概率对高成型阵容只可标「单点敏感度」,批38 同型批㊲)')
    pos = sum(ys)
    return {
        'violations': len(violations), 'detail': violations,
        'rows': len(rows), 'label_known': len(ys),
        'pos': pos, 'neg': len(ys) - pos,
        'features': feat_stats, 'tier_ge2_samples': tier_ge2,
        'note': 'win_model 训练表特征健康审计(批38);红 = 零方差特征/'
                'tier 覆盖门未就绪/标签断裂——训练前必须处理',
    }



# --- 批39 检查项(2026-08-25;r9 boss 语料判读口径守卫) -----


def check_boss_hp_floor_censoring(rows: list[dict]) -> dict:
    """批39 检查项:boss 行 hp 地板删失与异常跳变守卫(判读面;语料级显式调)。

    背景(批39 语料实证,21 boss 行/34 局,报告 sim_压测_批39):败局
    ``hp_after`` 被 1 点地板截断——「boss 掉血 18-24」的行实为 hp 早已
    见底,真实掉血 ≥ 观测值(**右删失**);把删失值当真值参与「boss
    伤害 vs 板面特征」相关/分组 = 系统性低估重败局的伤害。批39 扫描
    当场踩过:先按全行算掉血再发现 hp_after==1 的行 11/19,险些得出
    「散板 boss 伤害更轻」的反向结论。

    判据(吃 outcomes 行 ``{'node_type','killed','hp_after'}``,可选
    ``hp_before`` 键;缺省取上一行 ``hp_after``;只辖 ``node_type==
    'boss'`` 行):
    - **标签断裂违规**:boss 行 ``killed`` 非 bool(None = 采集断裂,
      与批㊲ boss 语料样本门同型;实证 21 行中 1 行 None);
    - **hp 跳变违规**:``killed=False`` 且 ``hp_before-hp_after<=0``
      (败局 hp 不可能不降——跳变 = 接管帧错值/回填错位;实证
      run_20260823_154910:3→58,-55);
    - **hp 缺失违规**(批40 补,批41 复审改判维持):``killed=False`` 且
      ``hp_after`` 缺失(None)——败局 boss 行缺 hp_after,掉血口径不可算,
      静默通过 = 判读面盲区。⚠️ 批41 边界复审:当前写端(``cw_settlement_obs.
      read_round_outcome`` hp None 兜 0 + telemetry dataclass ``hp_after:int``)
      **不产 None**——本分支实为 schema 防御(防未来写端变更/外部语料),
      非已观测语料缺口(语料实证 21 boss 行无 None);
    - **hp==0 披露(note 级,批41 改判)**:``killed=False`` 且 ``hp_after==0``
      ——批40 原判「写端矛盾(归零即败应标 killed=True)」是**语义倒置**:
      killed = 玩家击败对手(``挑战成功``),团灭 = 打不过 → killed=False
      恰是正确标签;写端 ``cw_settlement_obs`` 失败屏 hp=0 是 ground truth
      (conf=1.0),且 ``HP_MIN=0``(``cw_obs_core``)OCR 可解析真 0。故
      ``killed=False + hp_after==0`` = 合法团灭形态,与 ==1 同族按**删失
      披露**处理(伤害口径须剔除),不作违规;
    - **删失披露(note 级)**:``killed=False`` 且 ``hp_after==1`` 的
      行计数 + 行号——这些行的 boss 掉血是下界非真值,任何伤害口径
      必须剔除或单独标注。

    ``hp_before`` 回填(批41 补守卫):缺省取上一行 ``hp_after`` 时**须同
    ``run_id``——跨 run 边界回填会用上一局末 hp 当本局 boss 前值,产出
    伪「hp 未降」违规(批40 遗留:回填不分 run 边界)。
    """
    boss_idx = [i for i, r in enumerate(rows)
                if r.get('node_type') == 'boss']
    if not boss_idx:
        return {'violations': 0, 'note': '无 boss 行,不辖', 'boss_rows': 0}
    violations: list[str] = []
    censored: list[int] = []
    bad_label = 0
    for i in boss_idx:
        r = rows[i]
        k = r.get('killed')
        if not isinstance(k, bool):
            bad_label += 1
            continue
        hp_after = r.get('hp_after')
        # 批41:上一行回填须同 run——跨 run 边界 = 上一局末 hp,非本局前值
        _prev = rows[i - 1] if i > 0 else None
        hp_before = (r.get('hp_before') if r.get('hp_before') is not None
                     else (_prev.get('hp_after')
                           if _prev is not None
                           and _prev.get('run_id') == r.get('run_id')
                           else None))
        if not k:
            if hp_after is None:
                violations.append(
                    f'行{i}({r.get("run_id")} r{r.get("round_num")}):'
                    f'killed=False 但 hp_after 缺失(败局 boss 行掉血口径'
                    f'不可算,采集缺口/schema 防御,批40/批41)')
                continue
            if hp_after == 0:
                censored.append(i)   # 批41 改判:团灭合法形态,与 ==1 同族删失披露
            if hp_after == 1:
                censored.append(i)
            if hp_before is not None and hp_after is not None \
                    and hp_before - hp_after <= 0:
                violations.append(
                    f'行{i}({r.get("run_id")} r{r.get("round_num")}):'
                    f'killed=False 但 hp {hp_before}->{hp_after} 未降'
                    f'(败局不可能——接管帧错值/回填错位,批39)')
    if bad_label:
        violations.append(f'{bad_label} 行 boss killed 非 bool(采集断裂,'
                          f'批㊲同型;外推无同节点对照地基)')
    censor_note = (
        f'{len(censored)} 行 killed=False 且 hp_after∈{{0,1}}(boss 掉血为'
        f'下界/团灭非真值,右删失——伤害口径必须剔除或单独标注,行号 '
        f'{censored},批39/批41)') if censored else None
    return {
        'violations': len(violations), 'detail': violations,
        'boss_rows': len(boss_idx), 'bad_label': bad_label,
        'censored_rows': len(censored), 'censored_idx': censored,
        'censor_note': censor_note,
        'note': 'boss 行 hp 地板删失守卫(批39/40/41);红 = killed 采集断裂'
                '/败局 hp 未降/hp_after 缺失;'
                'censor_note 非空 = 伤害口径须剔删失行(含 hp_after==0 团灭行)',
    }

