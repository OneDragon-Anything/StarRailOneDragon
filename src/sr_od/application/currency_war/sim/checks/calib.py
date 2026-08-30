"""校准锚检查(boss_win/gold_dist/shop_cost/ab_*/p2_*/anchor 族,分包期6 拆分)。"""

from __future__ import annotations

import math

# 实机末金均值(批⑧ F1,18 局;批⑩ F5 对照侧:sim 52.5 vs 实机
# 24.3 = 2.2× 虚高)。merge 落地(ADR-0276)后此比值应为收敛判据。
# ⚠️ 锚已随 economy v2 重锚(ADR-0447,编排者裁决):24.3 采于穷 sim
# 时代/败局死亡时点口径,与 v2 校准目标(实机 P1 出口富状态)错位;
# 现值 45.1 = v2(r9 δ 退坡后)n=200 实测 P1 出口金均值(种子窗
# 500000,.debug/temp/currency_war/w493_income_calib/REPORT.md §1)。
# **语义降级声明**:本检查自 v2 起为「末金漂移哨兵」(锚=当前交付值,
# 防未来静默漂移;比值 >1.5 = 注水/泄金通道回归),真实验收语义待
# 实机 P1 出口金干净语料(spend_ledger 队列)重锚。
REAL_AVG_ENDGOLD: float = 45.1

ENDGOLD_RATIO_MAX: float = 1.5   # 漂移阈值(v2 起;见上语义降级声明)



def check_sim_endgold_calib(ledgers: list[list[dict]]) -> dict:
    """批⑨ 设计/批⑩ 追加数据(末金校准;ADR-0276/0285;v2 重锚 ADR-0447)。

    判据:sim 末轮金均值 vs 锚的比值。锚已随 economy v2 重锚为当前
    交付值 45.1(v2 r9 δ 退坡后 n=200 实测;旧 24.3 = 穷 sim 时代/
    败局死亡时点口径,与 v2 校准目标错位)——**v2 起语义 = 末金漂移
    哨兵**(比值 >1.5 = 注水/泄金通道回归),真实验收语义待实机 P1
    出口金干净语料重锚。

    双口径(ADR-0285,批㉑ F3/F5):r419 超容买守卫(ADR-0283)
    拦截的合法滞留(bench 满时策略仍提案买,金留下)混入总口径
    分子,endgold 51.9→58.1 漂移全部来自它——**净滞留口径 =
    末金 − bench_full_skipped_gold 折算**,判读可区分「策略滞留」
    vs「守卫拦截」;违规按净口径(总口径并行披露供跨批对照)。
    """
    golds: list[float] = []
    skip_gold: list[float] = []
    for rows in ledgers:
        if not rows:
            continue
        g = rows[-1].get('gold')
        if g is None:
            continue
        golds.append(g)
        skip_gold.append(sum(
            (r.get('sim') or {}).get('bench_full_skipped_gold', 0)
            for r in rows))
    avg = sum(golds) / len(golds) if golds else 0.0
    avg_sk = sum(skip_gold) / len(skip_gold) if skip_gold else 0.0
    ratio = avg / REAL_AVG_ENDGOLD if golds else 0.0
    net_avg = avg - avg_sk
    net_ratio = net_avg / REAL_AVG_ENDGOLD if golds else 0.0
    return {'violations': 1 if net_ratio > ENDGOLD_RATIO_MAX else 0,
            'sim_avg_endgold': round(avg, 2),
            'real_avg_endgold': REAL_AVG_ENDGOLD,
            'ratio': round(ratio, 2),
            # 净滞留口径(ADR-0285):守卫残金剔除后的策略真滞留
            'guard_skipped_gold_avg': round(avg_sk, 2),
            'net_endgold_avg': round(net_avg, 2),
            'net_ratio': round(net_ratio, 2)}



# `w493_income_calib/`(ADR-0447):sim↔实机金分布/费用曲线对拍锚(实机 2026-08-28
# 当日 15 局 P1 全帧口径,Phase 1 实测基线;数据源与整定程序见
# engine_p1.EVENT_GOLD_BY_ROUND 注释)。锚点随实机新局补充后原地更新。
REAL_P1_GOLD_MEAN: float = 29.4

REAL_P1_GOLD_GE50: float = 0.141     # P(g≥50) 帧占比

REAL_P1_GOLD_GE70: float = 0.022

REAL_P1_GOLD_BAND: tuple[float, float] = (25.0, 35.0)   # M1 判据 30±5

REAL_P1_SHOP_COST_SHARE: dict[int, float] = {1: 0.613, 2: 0.243, 3: 0.133, 4: 0.010}



def check_gold_dist_calib(ledgers: list[list[dict]]) -> dict:
    """`w493_income_calib/` 对拍项:P1 备战帧金分布 vs 实机基线(ADR-0447)。

    披露 sim 金均值/ge50/ge70 占比;软告警 = 金均值越出实机带
    [25,35](M1 判据 30±5;n<100 不判,数据边界)。被检对象 =
    环境校准层(事件金总闸),非策略——告警语义是「状态分布漂移」,
    消费方先核 economy_calib_version 与池指纹再归因。
    """
    golds: list[int] = []
    for rows in ledgers:
        golds.extend(r['gold'] for r in rows
                     if r.get('plane') == 1 and r.get('gold') is not None)
    n = len(golds)
    if n == 0:
        return {'violations': 0, 'n': 0, 'note': '无 P1 帧(数据边界)'}
    mean = sum(golds) / n
    ge50 = sum(1 for g in golds if g >= 50) / n
    ge70 = sum(1 for g in golds if g >= 70) / n
    lo, hi = REAL_P1_GOLD_BAND
    out = {'violations': 0, 'n': n,
           'sim_gold_mean': round(mean, 2),
           'sim_ge50': round(ge50, 4), 'sim_ge70': round(ge70, 4),
           'real_gold_mean': REAL_P1_GOLD_MEAN,
           'real_ge50': REAL_P1_GOLD_GE50, 'real_ge70': REAL_P1_GOLD_GE70}
    if n < 100:
        out['note'] = 'n<100 不判(数据边界)'
    if n >= 100 and not (lo <= mean <= hi):
        out['violations'] = 1
        out['note'] = f'金均值 {mean:.1f} 越出实机带 [{lo},{hi}](M1)'
    return out



def check_shop_cost_curve(ledgers: list[list[dict]]) -> dict:
    """`w493_income_calib/` 对拍项:P1 商店费用曲线 vs 实机 OCR 基线(ADR-0447)。

    纯披露(不判):1-4 费占比偏离的已知主根 = 等级轨迹差(策略
    追级行为域,环境侧无合法旋钮;`w493_income_calib/` 预注册 S1 best-effort)——
    消费方据等级轨迹逐轮表归因,禁直接调商店概率表(机制真值)。
    """
    costs: list[int] = []
    for rows in ledgers:
        for r in rows:
            if r.get('plane') != 1:
                continue
            for w in (r.get('sim') or {}).get('shop_waves', []):
                if w.get('event') != 'offer':
                    continue
                costs.extend(int(c.get('cost', 0)) for c in w.get('cards', []))
    n = len(costs)
    if n == 0:
        return {'violations': 0, 'n': 0, 'note': '无 offer 波(数据边界)'}
    share = {c: sum(1 for x in costs if x == c) / n
             for c in sorted(set(costs) | {1, 2, 3, 4})}
    return {'violations': 0, 'n': n,
            'sim_cost_share': {str(k): round(v, 4) for k, v in share.items()},
            'real_cost_share': {str(k): v for k, v in REAL_P1_SHOP_COST_SHARE.items()}}



def check_ab_resolution_floor(hps_a: list[float],
                              hps_b: list[float]) -> dict:
    """批㉒ F4(ADR-0285):A/B 配对差分辨率底披露。

    单流 RNG 共享(节点序/开局 bench/事件金/商店抽同一条流)只
    消掉约 1/3 方差(批㉒ 实测耦合比 0.675,38.2% 局 A/B hp 完全
    相同)——**|Δavg| < 1.96·sd_pair/√n 的差值在噪声带内,不得
    叙述为方向性结论**(n=300 实测底 ±1.93hp;底按本批配对差
    现算,勿写死)。A/B 报告调用方(simulate_p1_ab / 手工对照)
    附本披露;批㉑ 判 r416 +0.08 为噪声与此一致。n<30 不判
    (声明数据边界)。
    """
    import statistics
    n = min(len(hps_a), len(hps_b))
    if n < 2:
        return {'violations': 0, 'n': n, 'note': 'n<2 不判(数据边界)'}
    diffs = [a - b for a, b in zip(hps_a[:n], hps_b[:n], strict=False)]
    mean_diff = sum(diffs) / n
    sd = statistics.stdev(diffs)
    floor = 1.96 * sd / math.sqrt(n) if sd > 0 else 0.0
    noise_band = abs(mean_diff) < floor
    return {'violations': 0,   # 披露级:标注噪声带,不构成违规
            'n': n,
            'mean_diff': round(mean_diff, 3),
            'sd_pair': round(sd, 3),
            'ci95_floor': round(floor, 3),
            'noise_band': noise_band,
            'note': ('差值在噪声带内(|Δavg|<95% 底),'
                     '不得叙述为方向性结论' if noise_band
                     else '差值超过 95% 底,可叙述方向')}



#: 批㉟(战役收官归因审计):方向性叙述的最小配对窗 n。
#: 实证:0302-0304 收官「三窗领先 -3.00/-1.00/-0.27」全部产生于
#: n=30 窗(0-29/900000-29/900030-59),逐窗 95% 底 ~±5hp——方向性
#: 叙述越过自身分辨率底;同代码同池在 n=100 anchor 窗(seeds 0-99)
#: gap=+1.87 符号相反、900000 族 n=100 双窗 +0.19/+2.07、异族窗
#: 500000/123450 +7.10/+2.69——n=30 的「领先」在更大窗上不稳。
#: n<100 只允许披露级(claim='noise'),不允许方向性叙述。
AB_VERDICT_MIN_N = 100


#: 非方向性叙述词表(claim 参数;白名单豁免,其余一律按方向性辖)。
#: **批㊲ 裁决反转**:旧版方向词表 ``{'leads','behind','领先','落后'}``
#: 命中才辖——claim 换措辞('首超'/'wins'/'更高'/'better')即绕过,
#: 判罚面形同虚设;反转为**默认辖 + 非方向白名单豁免**后,任何新
#: 措辞默认被辖(保守面:未登记的非方向同义词会被误辖=多报噪声,
#: 漏报面归零——误辖可加白名单修正,漏报无补救)。
_AB_VERDICT_NONDIRECTIONAL = frozenset({
    'noise', 'noise_band', 'tie', 'draw', 'equal', 'flat', 'parity',
    'same', 'within_noise',
    '平局', '噪声', '持平', '无差异',
})



def check_ab_verdict_claim(mean_diff: float, sd_pair: float, n: int,
                           claim: str) -> dict:
    """批㉟ 检查项:A/B 方向性叙述的窗口口径守卫(判罚面;批㊲ 加固)。

    与 ``check_ab_resolution_floor``(披露面)配对:floor 只标注噪声
    带,本函数对「越底仍叙述方向」记违规。判据:
    ① n < ``AB_VERDICT_MIN_N`` 时方向性叙述 = 违规(窗分辨率不足);
    ② |mean_diff| < 1.96·sd_pair/√n 时方向性叙述 = 违规(噪声带内);
    非方向叙述(白名单词,见 ``_AB_VERDICT_NONDIRECTIONAL``)不辖;
    **批㊲ 起白名单外的任何 claim(含空串/未知措辞)一律按方向性
    辖**(旧方向词表可被换措辞绕过,词表反转堵死)。
    来源:批㉟ 战役收官归因审计(sim_压测_批㉟;0302-0304 三窗
    n=30 领先叙述被 n=100 复验翻转)+ 批㊲ 判据漏洞审计(词表
    绕过攻击面)。
    """
    directional = claim not in _AB_VERDICT_NONDIRECTIONAL
    reasons: list[str] = []
    if directional and n < AB_VERDICT_MIN_N:
        reasons.append(f'verdict_below_min_n(n={n}<{AB_VERDICT_MIN_N})')
    if directional and n >= 2 and sd_pair > 0:
        floor = 1.96 * sd_pair / math.sqrt(n)
        if abs(mean_diff) < floor:
            reasons.append(f'verdict_within_noise_band(|{mean_diff:.2f}|'
                           f'<{floor:.2f})')
    return {'violations': len(reasons), 'reasons': reasons,
            'n': n, 'claim': claim, 'directional': directional,
            'min_n': AB_VERDICT_MIN_N}



# 批⑩ 检查项 anchor_registry_n300:基线锚登记制——engines2/recipe5/
# avg_hp 等锚一律 n=300 口径登记(池指纹必附),n=60 值只作快速回归
# 哨兵。数值演进链:ADR-0276/0277(merge+win 校准)→ ADR-0279
# (battle rung 分桶)→ ADR-0284(商店槽消费,批㉒ F3 波及:成型类
# 指标回落到真实供给口径——旧值含幻影槽超买水分,新旧对照表进
# ADR-0284)→ ADR-0292(reward/supply Δ池采样 + 池数据增长
# 2026-08-23 晚批语料,battle 桶增样 r0 26→40/r1 24→31;换锚主因
# = 池数据增长,**采样语义本身 A/B 差 0.85hp 在分辨率底 ±2.80 内**,
# 归因分解见 ADR-0292 回归验证节)。
# 旧锚(066c4185,ADR-0292 批)已失效:ADR-0306(Δ池扩容批)
# _SAMPLER_VERSION 4→5 + boss 胜分支 rung≥3 胜率改 rung2 桶实测外推
# (0.25→0.667)——**校准修正非策略变化**,hp_ge_60 0.127→0.137 上移
# 属预期;历史报告对旧池重放须用 v4 指纹导出 JSON 快照。
# 旧锚(886f8a39,ADR-0306 批)已失效:ADR-0308(迁移审计 w37(git 历史),迁移审计 w31(git 历史) 节点×
# 轮次胜率阶梯进回退层)_SAMPLER_VERSION 5→6——回退层胜负面换
# 实测边际(旧策略病局语料):hp 类指标**下移属预期**(boss 回退
# 胜率 rung2 0.25/rung≥3 0.667 → 0.05;battle 回退 ~0.29;此前
# rung 外推本身是跨节点拍脑袋外推,高估);策略侧指标零漂移
# (engines2/recipe5/refreshes 逐位持平 = 只有结算校准变了,
# 决策行为面没动)。
# 旧锚(fd48f135,ADR-0308 批)已失效:ADR-0312(迁移审计 w50(git 历史) 口径统一)
# _SAMPLER_VERSION 6→7——sim 侧 board 全集口径(_recount_board)+采样键
# Σboard(池语料同口径,旧 min(level,len(deployed)) 与池语料不同口径,
# 采样系统性偏浅,迁移审计 w49(git 历史) Q4)。**校准口径修正非策略变化**:hp 类下移属
# 预期(同局面落更深的 encounter/boss 桶 → 更真实的战损);策略侧
# 基本零漂移(engines2/recipe5 与 v6 锚逐位持平);哨兵大样本仍绿
# (n=300 diff +5.39 vs v6 批 +5.33)。遗留:n=300 涌现边缘违规
# engine_seed_not_resold(1/300,g188)/carry_on_shelf_responded
# (2/300,g243/296)——行为面随口径变化的涌现信号,待 leader 对拍
# 裁决(迁移审计 w50(git 历史) 报告 §遗留)。
# 旧锚(46066bbe,ADR-0334 迁移审计 w73(git 历史) 批)已失效:其后三批有口径/行为影响的
# 改动叠加——`w126_b_arm/` 切调度(ADR-0349,V_D 批口径化等决策面改动=策略
# 变化)+ `w129_smoke/` 连胜金口径(ADR-0351,奖励节点不计连胜/counter0 发 1 金
# =校准口径变化,金轨迹系统性 −4~−6 金/局)+ `w132_b_arm/` form_ok 兜底门
# 结构判据(ADR-0353,有效体系数≥2 替代连续分门=策略变化)。混合
# 漂移:engines2/recipe5/refreshes 下移属策略变化预期,hp 类下移属
# 连胜金口径(经济变弱→板面更浅→战损更深)与兜底门收严的合成;
# 分批归因细表见 ADR-0355。`w129_smoke/` 报告已记档「跨日对照不可比,后续
# sim 批需重建基线」——本锚即该重建。
# 新锚池口径(ADR-0355/迁移审计 w140(git 历史)):池=w118 导出快照(pool_snapshot.json
# 指纹 bab146c68c5df11a,resolve_pool Path 模式),与 `w126_b_arm/`/`w131_a2n_arm/`/`w132_b_arm/`/
# `w135_crosscheck/` 各 A/B 臂同源——跨批 A/B 对照可比性优先。**注意:主仓提交
# 快照(cw_delta_pool_data)指纹随局终自动再生管线(ADR-0344)持续
# 前移(HEAD=4d28822c,工作树在飞=ddfea057),与本锚指纹不同——
# 用 snapshot 池跑的 n=60 快验 pool_fp_match=False 属预期,drift 才
# 是对照主体;跨池对照一律走 Path 重放本锚池。
# 旧锚(bab146c6,ADR-0355/迁移审计 w140(git 历史))已失效:ADR-0362(`w157_p2/`,P2 段扩展)
# Δ池 plane 维键化——_SAMPLER_VERSION 7→8,指纹随重算;键化顺手清除
# 既有 P1 池 P2 污染(44 条 plane=2 差分混入含 16 条跨位面差分,迁移审计 w156(git 历史)
# 勘察 §5.1),P1 桶语料变化(battle rung1 混入差分清除→均值 -3.98/
# win_killed 0.65,旧池 -5.86/0.50)。**P2 段扩展换锚**:新锚=主仓
# 提交快照 v8(0bf6c0d6),与 `w157_p2/` simulate_p2_ab 同池;P1 侧 drift
# 相对 迁移审计 w140(git 历史) 锚 = 池口径修正(污染清除)+语料前移(至 08-26)合成,
# 非策略变化(`w157_p2/` 决策代码零改动,杠杆全在 harness 层,迁移审计 w156(git 历史) 结论)。
# ⚠️ 池出处勘误(迁移审计 w165(git 历史) 巡检 #2):「主仓提交快照」措辞失实——git 内无此池
# JSON(Δ池快照 .gitignore);真身=本地导出件
# .debug/temp/currency_war/w157_p2/pool_v8_plane_keyed.json(meta 指纹
# 0bf6c0d695f5052c 亲核)。跨池重放以该导出件为准;登记即导出纪律见
# ADR-0362 遗留(锚池资产随批落 .debug,勿再只留指纹)。
# 常红披露(非本批引入,见各检查项口径):equip_value_strategy_key_
# coverage(批㉜ 策略域待裁决恒红)/delta_pool_bucket_min_n+depth_
# cliff_monotonicity(池语料贫困,META 披露)。
ANCHOR_REGISTRY_N300: dict = {
    'pool_fingerprint_prefix': '0bf6c0d6',
    'recorded': '2026-08-28(`w157_p2/`/ADR-0362:Δ池 plane 维键化后重建'
                '——sampler v8,池=主仓提交快照 0bf6c0d695f5052c,'
                'n=300,seed 0-299,planes=1)',
    'metrics': {
        'engines2_by_r6': 0.20,       # 旧 0.15(bab146c6 锚;池污染清除
                                      # +语料前移的合成漂移,见上方注)
        'avg_final_hp': 25.03,        # 旧 19.81(同上)
        'hp_ge_60': 0.05,             # 旧 0.03(同上)
        'battle_losses_le_2': 0.07,   # 旧 0.05(同上)
        'recipe5_by_r6': 0.57,        # 旧 0.48(同上)
        'avg_refreshes': 0.0,         # 旧 1.23(⚠️ 现策略 P1 段在 sim
                                      # 语料下 V_D 批口径化后零刷新——
                                      # `w157_p2/` 抽核 5+20 seed 改前后一致
                                      # (同 0),非池效应;锚如实记)
    },
}


# `w162_inject/`/ADR-0364:**策略环境注入换锚**——invest-on 口径并行锚。off 口径
# 锚(上表)不变(默认关 = 主路径口径);本表 = simulate_p1_batch(
# invest=True) 的 n=300 基线(注入激活①资格通道 → P1 锁定分布/
# 刷新分布结构性改变,`w161_refresh/` 缺口闭合;含 D 的 P1 侧 sim 结论自此以
# 本口径为基准)。⚠️ 池指纹 1762b1cf 与 `w157_p2/` 锚 0bf6c0d6 不同——快照
# 池随局终自动再生管线(ADR-0344)前移 + 并行批在飞,跨日对照不可比;
# on/off drift 表以**同池同 seed 配对**为准(`w162_inject/` 报告 §drift):
# engines2 0.213→0.170 / recipe5 0.573→0.473 / avg_hp 24.4→21.8 /
# avg_refreshes 0.0→0.553(①通道点火直证)/ invest_p1_lock_rate 0.51。
# 成型类指标下移 = 锁定分布变化的预期方向(P1 锁终局 comp 把囤货
# 方向从过渡引擎上引开,迁移审计 w159(git 历史)/`w161_refresh/` 同结论域),非回归。
ANCHOR_REGISTRY_N300_INVEST: dict = {
    'pool_fingerprint_prefix': '1762b1cf',
    'recorded': '2026-08-29(`w162_inject/`/ADR-0364:策略环境注入换锚——'
                'invest=True 口径首记,n=300,seed 0-299,planes=1,'
                '池=主仓提交快照 1762b1cf9fb44cd7)',
    'metrics': {
        'engines2_by_r6': 0.17,
        'avg_final_hp': 21.80,
        'hp_ge_60': 0.04,
        'battle_losses_le_2': 0.08,
        'recipe5_by_r6': 0.47,
        'avg_refreshes': 0.55,
        # invest 专属 headline(注入口径新增键)
        'invest_env_rate': 1.0,
        'avg_invest_strategies': 1.85,
        'invest_p1_lock_rate': 0.51,
        'avg_p1_locked_rounds': 4.23,
    },
}



# --- ADR-0362(`w157_p2/`)P2 段检查器最小集 ---------------------------------
# P2 段(planes>=2 批)的最低防线:金轨迹非负 + 段形状。P2 语料
# 边界(44 行/16 局)支撑行为分布验证,不支撑更多口径校准——检查
# 面到此为止,后续语料攒厚再扩(迁移审计 w156(git 历史) §2 分层结论)。

def check_p2_gold_nonneg(ledgers: list[list[dict]]) -> dict:
    """P2 段金轨迹非负(ADR-0362,`w157_p2/`)。

    判据:plane=2 账本行的 gold < 0 = 违规——sim 经济层守卫
    (地板/可负担性)在 P2 段照常辖,负金=结算/买扣款层回归。
    无 plane=2 行的批(planes=1)恒绿。
    """
    games: list[int] = []
    detail: list[str] = []
    for idx, rows in enumerate(ledgers):
        for row in rows:
            if (row.get('plane') or 1) != 2:
                continue
            g = row.get('gold')
            if isinstance(g, (int, float)) and g < 0:
                games.append(idx)
                detail.append(f"g{idx} p2r{row.get('round_num')} "
                              f"gold={g}")
    return {'violations': len(detail), 'games': games[:5],
            'detail': detail[:5]}



def check_p2_segment_shape(ledgers: list[list[dict]]) -> dict:
    """P2 段账本形状(ADR-0362,`w157_p2/`):ts 单调跨位面、plane 字段
    真值、round_num 域 1-P2_ROUNDS。

    判据:①全账本 ts 严格递增(P2 段续 P1 段单调,write_batch_ledger
    排序语义);②plane 值 ∈ {1, 2};③plane=2 行 round_num ∈
    [1, P2_ROUNDS]。违规=位面段迭代结构回归(如 P2 行挂 plane=1
    = 污染 P1 指标辖域)。
    """
    out: list[str] = []
    for idx, rows in enumerate(ledgers):
        last_ts = -1
        for row in rows:
            ts = row.get('ts')
            if not isinstance(ts, int) or ts <= last_ts:
                out.append(f'g{idx} ts 非单调:{ts}(prev {last_ts})')
            last_ts = ts if isinstance(ts, int) else last_ts
            if row.get('plane') not in (1, 2):
                out.append(f"g{idx} plane={row.get('plane')} 越域")
            if (row.get('plane') or 1) == 2 \
                    and not 1 <= int(row.get('round_num') or 0) <= 7:
                out.append(f"g{idx} p2 round_num="
                           f"{row.get('round_num')} 越域")
    return {'violations': len(out), 'detail': out[:6]}



# --- `w193_p2sim/`/ADR-0377:P2 战斗存活层检查器(参数化校准族带锚) ------------
# 辖 calibrated 批(report['p2_combat_calibrated']=True);uncalibrated
# 批(legacy 回退档/Δ池路径)不辖——恒绿跳过(legacy 档的池采样值
# 天然不在参数化带内,辖了=常红假检查)。

def _p2_band_of(node: str, round_num: int, bands: dict) -> tuple[int, int]:
    """掉血带路由(与 cw_battle_calib.p2_loss_band 同式;bands 来自批报告
    ``p2_calib.bands``——检查消费本批实参,非模块默认)。"""
    if node == 'battle':
        if round_num == 1:
            key = 'battle_r1'
        elif round_num <= 3:
            key = 'battle_early'
        else:
            key = 'battle_late'
    elif node == 'encounter':
        key = 'encounter'
    else:
        key = 'boss'
    return tuple(bands.get(key) or (0, 0))



def check_p2_loss_band_anchor(ledgers: list[list[dict]],
                              report: dict | None = None) -> dict:
    """P2 掉血带覆盖锚(`w193_p2sim/`/ADR-0377)。

    判据:calibrated 批的 plane=2 战斗类行(plane=2 ∧ node∈
    battle/encounter/boss ∧ sim.p2_win_p 非 None)结算值必须落在
    参数化带内——胜=win_delta(+2)/负=带内(容差 ±1 防取整边)。
    违规=结算层绕过参数族(如回退档混入/带路由错段)。
    """
    if not (report or {}).get('p2_combat_calibrated'):
        return {'violations': 0, 'detail': [],
                'note': 'uncalibrated 批不辖(legacy 档)'}
    calib = report.get('p2_calib') or {}
    bands = calib.get('bands') or {}
    win_delta = int(calib.get('win_delta', 2))
    out: list[str] = []
    games: list[int] = []
    for idx, rows in enumerate(ledgers):
        for row in rows:
            if (row.get('plane') or 1) != 2:
                continue
            s = row.get('sim') or {}
            node = s.get('node')
            if node not in ('battle', 'encounter', 'boss'):
                continue
            if s.get('p2_win_p') is None:
                continue   # 非校准路径行(reward/supply 不辖)
            d = s.get('delta')
            rn = int(row.get('round_num') or 0)
            lo, hi = _p2_band_of(node, rn, bands)
            if d == win_delta:
                continue
            if not -(hi + 1) <= d <= -(lo - 1):
                out.append(f'g{idx} p2r{rn} {node} Δ={d} 带外'
                           f'[{lo},{hi}]')
                games.append(idx)
    return {'violations': len(out), 'games': games[:5],
            'detail': out[:5]}



# P2 战斗类聚合胜率带(w193_p2sim/ADR-0377 校准族)。
# 重锚依据:旧上沿 0.35(语料边际 0-0.15 + β 上沿 headroom,ADR-0377)被
# 行为批真实抬升常态化越过——分配器预算纪律与 overlay 分配批(fcebbe50
# 确切口径读数首越带至 0.3514,66e2b562 至 0.400;n=10 局/约 40 战斗行
# 固定样本)累积提升 P1 末态质量,批均值 ~0.17→~0.28(n=100×3 窗
# 0.2401/0.2836/0.3083,pool 指纹 6400d5d8edeaf68d+eqg1);测量确定性由
# session rng 种子化修复(commit 69a18ca0)前后跨 commit 逐位一致佐证,
# 位移归因=代码行为真实改良、非随机抖动。新上沿 = 最高窗实测 0.2836
# 圆整 0.30 + headroom 0.15(与原锚同构:观测上沿 + 模型失控缓冲);
# 语义不变——只防胜率模型失控(β 注入回归/clip 失效),不钉策略胜率
# 点值,行为批位移靠重锚吸收。
P2_WIN_RATE_BAND: tuple[float, float] = (0.0, 0.45)

# 胜率带判读的最小战斗结算行数(坐标系:``total`` = 全批 plane=2 战斗类
# 结算行数,非局数;写入端 = check_p2_win_rate_band 判读臂)。
# n=10 局批只有 ~40 行,窗口读数 σ≈0.085,对「失控检测」带(真实分布距
# 上沿 ~0.5σ)无判别力——合法改良即可假红。判读只挂 ≥本值的大样本窗
# (n=100 局批 ~330 行,σ≈0.025);小样本批仍输出 win_rate 供披露,
# 只是 violations 恒 0。
P2_WIN_RATE_MIN_JUDGE_ROWS: int = 100


def check_p2_win_rate_band(ledgers: list[list[dict]],
                           report: dict | None = None) -> dict:
    """P2 胜率带锚(`w193_p2sim/`/ADR-0377;重锚依据见 P2_WIN_RATE_BAND 注)。

    判据:calibrated 批的 P2 战斗类胜率聚合必须落在带
    ``P2_WIN_RATE_BAND``(>上沿=胜率模型失控[如 β 注入回归/clip 失效],
    <下沿=全败同样异常)。战斗结算数<``P2_WIN_RATE_MIN_JUDGE_ROWS`` 的批
    不判(样本贫困,只披露 win_rate)。
    """
    if not (report or {}).get('p2_combat_calibrated'):
        return {'violations': 0, 'detail': [],
                'note': 'uncalibrated 批不辖(legacy 档)'}
    total = wins = 0
    for rows in ledgers:
        for row in rows:
            if (row.get('plane') or 1) != 2:
                continue
            s = row.get('sim') or {}
            if (s.get('node') in ('battle', 'encounter', 'boss')
                    and s.get('p2_win_p') is not None):
                total += 1
                wins += 1 if (s.get('delta') or 0) >= 0 else 0
    rate = wins / total if total else None
    out = []
    if total >= P2_WIN_RATE_MIN_JUDGE_ROWS and rate is not None and not (
            P2_WIN_RATE_BAND[0] <= rate <= P2_WIN_RATE_BAND[1]):
        out.append(f'P2 战斗胜率 {rate:.3f}({wins}/{total}) '
                   f'带外{list(P2_WIN_RATE_BAND)}')
    return {'violations': len(out), 'detail': out,
            'win_rate': round(rate, 4) if rate is not None else None,
            'combat_total': total}



def check_anchor_registry_n300(report: dict) -> dict:
    """批⑩ 检查项(锚登记制;ADR-0276)。

    判据(判据表原文):下次基线引用能直接取 n=300 值——本检查
    验证报告含登记表的全部锚指标(缺 = 登记制断裂),并披露与
    登记值的漂移(跨批对照用;drift 非违规——策略改动本就改变
    基线,违规只盯「引用键缺失」)。n=60 快验报告引用本表时,
    drift 仅作噪声带参考(批⑩ F1:n=60 噪声带 ±0.071)。
    """
    metrics = ANCHOR_REGISTRY_N300['metrics']
    missing = [k for k in metrics if k not in report]
    drift = {k: round(float(report[k]) - v, 4)
             for k, v in metrics.items() if k in report
             and isinstance(report[k], (int, float))}
    return {'violations': len(missing), 'missing': missing,
            'drift': drift,
            'pool_fp_match': str(report.get('pool_fingerprint', ''))
            .startswith(ANCHOR_REGISTRY_N300['pool_fingerprint_prefix'])}



def check_p2_precache_gate_closure(ledgers: list[list[dict]]) -> dict:
    """批⑫ p2_precache_gate_closure(P2 预买容量门闭合占比;代理披露)。

    判据(设计表原文):r≥7 轮 `_p2_precache_wants` 容量门(bench≤7)
    关闭占比——P1-only sim 下它是「末段花金主通道是否存在」的
    代理读数;实机对照后定性。**依赖标注**:策略内部函数不进
    账本 → 代理口径 = r≥7 轮末 bench>7 占位(门关);策略侧
    直读口径待遥测/账本接线(旧 line_strategy 机制锚随
    ADR-0336 删除——decision_v2 侧同代理口径)。
    """
    closed = tot = 0
    for rows in ledgers:
        for row in rows:
            if (row.get('round_num') or 0) < 7:
                continue
            tot += 1
            if len((row.get('state') or {}).get('bench') or []) > 7:
                closed += 1
    return {'violations': 0, 'r7plus_rounds': tot,
            'gate_closed_rounds': closed,
            'closed_share': round(closed / tot, 3) if tot else None,
            'note': '代理口径(轮末 bench>7);策略直读待接线'}

