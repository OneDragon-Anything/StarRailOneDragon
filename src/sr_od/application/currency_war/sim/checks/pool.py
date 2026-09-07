"""池·Δ池·桶族检查(DESIGN §4.2 pool 段,分包期6 拆分)。"""

from __future__ import annotations

from sr_od.application.currency_war.data.cw_battle_tables import (
    BUCKET_MIN_N as _POOL_BUCKET_MIN_N,
)
from sr_od.application.currency_war.data.cw_battle_tables import (
    DEPTH_BUCKET_W as _POOL_DEPTH_BUCKET_W,
)
from sr_od.application.currency_war.sim.checks.ledger import _normalize_buy_reason


def check_engine_seed_not_resold(rows: list[dict]) -> list[str]:
    """自由批(engine_seed 买入 ≥2 轮内不回卖;0 容忍;ADR-0289 清偿)。

    判据(设计表原文):reason=engine_seed 的买入在其后 ≥2 轮内
    不被卖出——现状(设计时)169 次即卖。引擎种子被当回合素材
    卖回 = 种子归零 + 白烧预算(r408 前振荡主通道的跨轮残留形态)。

    豁免边(与 ADR-0276 同轮豁免同族):买入轮同名买入 ≥2 =
    3合1 素材收集语境,其冗余让位不报(合成消化时序内卖出合法);
    单张买入即跨轮卖回(振荡主通道)仍 0 容忍。

    迁移审计 w88(git 历史)(ADR-0339 件3):真根因=carry_gate 死锁豁免(discipline
    ``_seed_cands`` 兜底)在唯可卖=新鲜种子时卖种子买 carry——
    已裁决移除(窗口内种子赢过腾位,carry 延后有界);本检查器
    语义不变,0 容忍恢复成立(seed16 姬子·启行 r4 买 r6 卖 r7 再
    买的涌现形态随兜底移除消失)。
    """
    out: list[str] = []
    seed_buys: dict[str, tuple[int, int]] = {}   # name → (轮号, 同轮份数)
    for row in rows:
        rn = row.get('round_num') or 0
        for a in row.get('actions') or []:
            t = a.get('__type__')
            if t == 'BuyCard' and _normalize_buy_reason(
                    a.get('reason') or '') == 'engine_seed':
                _n = (a.get('card') or {}).get('name')
                if not _n:
                    continue
                if _n in seed_buys and seed_buys[_n][0] == rn:
                    prev_rn, cnt = seed_buys[_n]
                    seed_buys[_n] = (prev_rn, cnt + 1)
                else:
                    seed_buys[_n] = (rn, 1)
            elif t == 'SellBench' and a.get('name') in seed_buys:
                bought_rn, cnt = seed_buys[a['name']]
                if 1 <= rn - bought_rn <= 2 and cnt < 2:
                    out.append(
                        f"p{row.get('plane')}r{rn}: engine_seed 买入 "
                        f"{a.get('name')}(r{bought_rn})≤2 轮内回卖"
                        f"(种子归零——自由批 0 容忍)")
    return out



# --- Δ池标定检查(压测批③ F1 检查项 1/2/3;ADR-0268) ---------------
# 前两条吃池 dict(simulate_p1_batch 有 resolve_pool 产物;纯 dict
# 入参,不 import cw_sim);第三条吃两臂账本(A/B 对照调用方使用,
# 不进 _BATCH_CHECKS——单臂批次无对照对象)。
# (池标定常数单一源=数据表 BUCKET_MIN_N/DEPTH_BUCKET_W;分包期 3 起改 import,
# 原「值同步维护」双源注释废除——期 0b 收拢 data 桶后此处残留别名已完成对齐)

# 迁移审计 w109(git 历史)(ADR-0344):池新鲜度滞后红线——runs.jsonl 里晚于池内最新 run
# 的行数 ≥ 此值 = 再生管线断。2 = 1 局容忍(再生挂局终后、下一局
# 未结束前 lag=1 是管线健康瞬态)+1 局缓冲;>2 只能是钩子/手工链
# 断了(2026-08-25 事故:池停 41 局 12 小时零报警)。
POOL_FRESHNESS_LAG_LIMIT = 2



def check_pool_freshness(replay_dir=None, *,
                         lag_limit: int = POOL_FRESHNESS_LAG_LIMIT) -> dict:
    """迁移审计 w109(git 历史)(ADR-0344):Δ池快照新鲜度——再生管线断裂的常设报警。

    判据:快照 ``META.runs`` 覆盖的最新 run_id,距本机生产
    ``runs.jsonl`` 的最新 run_id 落后 ≥lag_limit 局 → 违规(管线断)。
    lag 口径 = runs.jsonl 中晚于池内最新 run_id 的行数(run_id 为
    ``run_YYYYMMDD_HHMMSS``,字典序即时间序)。META 经数据模块取
    (镜像 resolve_pool 的访问方式;本检查只读构成元数据,不消费
    池数值)。

    边界:本机无 replay(CI/裸 checkout)→ 跳过不辖(freshness 是
    **本机管线**属性,不是池内容属性);池 META.runs 为空 → 违规
    (快照异常)。

    接线:sim 批量 checks(simulate_p1_batch,snapshot/auto 池)+
    生产局终钩子(cw_telemetry 再生后自检)双端。
    """
    import json
    from pathlib import Path

    # 池冻结(退役第一步):战斗类节点已切粗参数两态模型
    # (cw_coarse_battle),再生管线停更是**有意停机**而非断裂——
    # 新鲜度滞后不再构成违规,检查跳过(delta 模式对照臂恢复辖)。
    from sr_od.application.currency_war.kernel import cw_coarse_battle as _cb
    if _cb.BATTLE_ENGINE_MODE == 'coarse':
        return {'violations': 0, 'lag': None,
                'skipped': 'Δ池已冻结(退役第一步):战斗类节点已切'
                           '粗参数两态模型,快照停更为预期'}
    from sr_od.application.currency_war.data import cw_delta_pool_data as _dpd
    if replay_dir is None:
        from sr_od.application.currency_war.sim.cw_delta_pool_gen import (
            REPLAY_DIR as _rd,
        )
        replay_dir = _rd
    runs_path = Path(replay_dir) / 'runs.jsonl'
    if not runs_path.exists():
        return {'violations': 0, 'lag': None, 'skipped': 'no local replay'}
    real_ids: set[str] = set()
    for ln in runs_path.read_text(encoding='utf-8').splitlines():
        if not ln.strip():
            continue
        try:
            rid = json.loads(ln).get('run_id')
        except json.JSONDecodeError:
            continue   # 半写行容忍(与生成器同口径)
        if rid:
            real_ids.add(str(rid))
    pool_runs = {str(r) for r in (_dpd.META.get('runs') or {})}
    if not pool_runs:
        return {'violations': 1, 'lag': None,
                'detail': ['池 META.runs 为空——快照异常或未生成']}
    pool_latest = max(pool_runs)
    lag = sum(1 for rid in real_ids if rid > pool_latest)
    detail: list[str] = []
    if lag >= lag_limit:
        detail.append(
            f'Δ池快照落后实机 {lag} 局(池内最新 {pool_latest},实机最新 '
            f'{max(real_ids) if real_ids else "?"})——局终自动再生管线断'
            '(ADR-0344):查 cw_telemetry 局终钩子日志,或手工重跑 '
            'uv run python tools/cw/gen_delta_pool_snapshot.py')
    return {'violations': len(detail), 'lag': lag,
            'pool_latest': pool_latest,
            'real_latest': max(real_ids) if real_ids else None,
            'detail': detail}



def check_delta_pool_bucket_min_n(pool_map: dict,
                                  min_n: int = _POOL_BUCKET_MIN_N,
                                  ) -> dict:
    """压测批③ F1 检查项 1(ADR-0268):Δ池被采样桶的饥饿审计。

    判据:任一节点类型的任一深度桶 n<min_n → 违规——该桶真值
    不可靠(sim 防饥饿守卫会降级采样,但池本身饥饿说明**经验
    分布在该桶缺证据**,方向判断须声明边界)。批③ 实锤:battle
    桶6 n=1 恒 -11(深度 6 悬崖伪惩罚的来源)、encounter 全桶
    n≤1。生产语料该桶同样不足时,守卫是唯一解(补样不可得)。
    """
    hungry: list[str] = []
    for nt, buckets in sorted(pool_map.items()):
        for b, v in sorted(buckets.items(), key=lambda x: int(x[0])):
            if len(v) < min_n:
                hungry.append(f'{nt}:桶{b}(n={len(v)})')
    return {'violations': len(hungry), 'buckets': hungry[:10]}



def check_depth_cliff_monotonicity(
        pool_map: dict, min_n: int = _POOL_BUCKET_MIN_N) -> dict:
    """压测批③ F1 检查项 2(ADR-0268):桶均值随深度单调不减血。

    判据:同一节点类型内,可信桶(n≥min_n)的 Δ 均值随深度
    **单调不减血**(更深板 ≥ 更浅板,板深效应的既定方向)——
    违反即深度条件化失去方向意义(池不可用于方向判断,桶间差异
    是混杂而非效应)。批③ 实锤:桶6 -11 vs 桶9 -7.1(桶6 饥饿
    由检查项 1 辖,本检查只评可信桶,避免饥饿噪声淹没结构性
    单调违反)。均值含回合混杂声明:深桶样本多来自晚轮,违反
    时先查桶×轮分布再下结论。

    ADR-0279:battle 桶键已是 rung(非 depth)——本检查的深度
    单调方向不辖 battle(rung 方向锁在 battle_rung_pool_bucket_
    lock 真值表;r2 方差未判,批⑬盲区声明)。
    """
    out: list[str] = []
    for nt, buckets in sorted(pool_map.items()):
        if nt in ('battle', 'encounter'):
            # rung 键(ADR-0279;battle+encounter v11/ADR-0407)——
            # 深度单调语义不辖(rung 方向锁在
            # battle_rung_pool_bucket_lock 真值表;r2 方差未判,
            # 批⑬盲区声明)。
            continue
        ok = sorted(
            (int(b), v) for b, v in buckets.items() if len(v) >= min_n)
        for (b1, v1), (b2, v2) in zip(ok, ok[1:], strict=False):
            m1 = sum(v1) / len(v1)
            m2 = sum(v2) / len(v2)
            if m2 < m1:
                out.append(
                    f'{nt}:桶{b1}均值{m1:+.1f} > 桶{b2}均值{m2:+.1f}'
                    f'(更深反而更痛——池不可用于方向判断)')
    return {'violations': len(out), 'pairs': out[:10]}



def check_ab_depth_boundary_confound(ledgers_a: list[list[dict]],
                                     ledgers_b: list[list[dict]],
                                     ) -> list[str]:
    """压测批③ F1 检查项 3(ADR-0268):A/B 深度分布跨桶边界混杂标。

    判据:两臂战斗类轮(battle/encounter/boss)的深度桶占用集
    不对称——某桶仅一臂到达 → 两臂的 Δ 采样来自不同经验分布,
    hp 差含「池桶差异」混杂,不能读作策略效应(打标而非否决:
    对照结论须先剥离池混杂,如 fallback 口径复核)。批③ 实锤:
    B/C 臂把板深推过桶 6 边界后摔进 battle 桶6 n=1 恒 -11 悬崖,
    snapshot 口径 hp 降幅大半由此贡献。
    """
    def _hist(ledgers: list[list[dict]]) -> dict[int, int]:
        h: dict[int, int] = {}
        for rows in ledgers:
            for row in rows:
                s = row.get('sim') or {}
                dep = s.get('depth')
                if s.get('node') in ('battle', 'encounter', 'boss') \
                        and dep is not None:
                    b = min(int(dep) // _POOL_DEPTH_BUCKET_W, 5) \
                        * _POOL_DEPTH_BUCKET_W
                    h[b] = h.get(b, 0) + 1
        return h

    ha, hb = _hist(ledgers_a), _hist(ledgers_b)
    out: list[str] = []
    for b in sorted(set(ha) | set(hb)):
        na, nb = ha.get(b, 0), hb.get(b, 0)
        if (na > 0) != (nb > 0):
            arm = 'A' if na else 'B'
            out.append(
                f'桶{b} 仅 {arm} 臂到达(A n={na}, B n={nb})'
                f'——两臂 Δ 采样跨桶边界,hp 差含池混杂')
    return out



# --- 批⑬ 检查项(2026-08-24 裁决落地;ADR-0279) ---------------------
# battle Δ池 rung 分桶锁:sim 压测批⑬ F1/F2/F7 的常态化防线。

# 批⑬ F2 真值表(battle rung 桶均值;b13 时代全量 replay 分桶
# 实测,r0 n=26 / r1 n=24 双主桶)。v13(ADR-0582)随 Δ池合成行/
# conf 门治理**用过滤后语料重推**——旧值(-11.5/-6.3)是含毒语料
# (合成行入配对)的产物,治理后 rung1 漂移 3.06hp 超带;重推值 =
# 过滤后语料同口径实测(r0 n=256 mean −9.73 / r1 n=238 mean −3.24,
# 快照指纹 a0722904)。r2 方差未判(时代分层混杂)/r3 无样本——
# 真值表只锁双主桶;池重生成后均值漂移 >3hp 报警(判据表原值)。
BATTLE_RUNG_TRUTH: dict[int, float] = {0: -9.73, 1: -3.24}

BATTLE_RUNG_DRIFT_MAX: float = 3.0

BATTLE_RUNG_MAIN_MIN_N: int = 10   # 批⑬ F1 主桶门槛(主桶各≥10)

# 批⑬ F7:boss 池域覆盖锁——重生成不得丢失既有极值样本(旧域
# [-36,-13] 的 -36 下界)。F7 原始读数「-42」是**决策帧口径**
# (run154910 r9 决策帧 hp100 → 结算 58);本池口径 = outcomes
# 相邻轮差分,该局 boss Δ=71→58=-13 已入池——-42 差分不可达,
# 扩域诉求按差分口径兑现为「域不缩」(ADR-0279 Considered Options)。
BOSS_POOL_DOMAIN_FLOOR: int = -36



def check_battle_rung_pool_bucket_lock(pool_map: dict) -> dict:
    """批⑬ 检查项 battle_rung_pool_bucket_lock(ADR-0279)。

    判据(批⑬检查项设计表原文):
    - battle rung 桶真值表(BATTLE_RUNG_TRUTH,v13/ADR-0582 起=
      过滤后语料重推锚)锁进池——rung0/rung1 双主桶存在且 n≥10,
      均值距真值漂移 ≤3hp;
    - battle 桶键全落 rung 域(0-4)——出现 depth 域键(≥6)= rung
      分桶未生效(快照未重生成/生成器回归);
    - encounter rung 化(v11/ADR-0407):encounter 桶键应全落 rung
      域(0-4)——出现 depth 域键(≥6)= 键迁移未生效(快照未
      重生成;批⑬ F1 的「暂 depth 分桶」边界声明已被 v11 解禁取代);
    - boss 池域覆盖:boss 池非空时 min ≤ -36(重生成不丢失既有
      极值样本;批⑬ F7 的 -42 是决策帧口径读数,outcomes 差分
      口径下不可达,见 BOSS_POOL_DOMAIN_FLOOR 注)。

    空 battle 池(fallback/历史 Path 快照)不辖,violations=0。
    """
    battle = pool_map.get('battle') or {}
    if not battle:
        return {'violations': 0,
                'note': 'battle 池空(fallback/Path 历史快照)不辖'}
    out: list[str] = []
    depth_like = sorted(int(b) for b in battle if int(b) > 4)
    if depth_like:
        out.append(f'battle 桶键 {depth_like[:5]} 落 depth 域(≥6)'
                   f'——rung 分桶未生效(ADR-0279:重跑生成器)')
    for rg, truth in sorted(BATTLE_RUNG_TRUTH.items()):
        v = battle.get(rg) or []
        if not v:
            out.append(f'battle rung{rg} 桶缺失(批⑬ F1 双主桶)')
            continue
        if len(v) < BATTLE_RUNG_MAIN_MIN_N:
            out.append(f'battle rung{rg} n={len(v)}'
                       f'<{BATTLE_RUNG_MAIN_MIN_N}(主桶饥饿)')
        mean = sum(v) / len(v)
        if abs(mean - truth) > BATTLE_RUNG_DRIFT_MAX:
            out.append(f'battle rung{rg} 均值{mean:+.1f} 距批⑬真值'
                       f'{truth:+.1f} 漂移>{BATTLE_RUNG_DRIFT_MAX}hp'
                       f'(池与真值表失配)')
    enc = pool_map.get('encounter') or {}
    enc_depth_like = sorted(int(b) for b in enc if int(b) >= 6)
    if enc_depth_like:
        out.append(f'encounter 桶键 {enc_depth_like[:5]} 落 depth 域(≥6)'
                   f'——v11/ADR-0407 rung 分桶未生效(快照未重生成)')
    boss_vals = [d for v in (pool_map.get('boss') or {}).values()
                 for d in v]
    if boss_vals and min(boss_vals) > BOSS_POOL_DOMAIN_FLOOR:
        out.append(f'boss 池域 min={min(boss_vals)} 未覆盖批⑬ F7 '
                   f'新极值(≤{BOSS_POOL_DOMAIN_FLOOR})'
                   f'——快照未重生成或语料缺失')
    return {'violations': len(out), 'issues': out[:6],
            'battle_bucket_means': {
                str(b): round(sum(v) / len(v), 2)
                for b, v in sorted(battle.items())}}



# --- ADR-0306(Δ池扩容批)桶覆盖披露检查 ------------------------------
# 各桶 n≥10 或在快照 META bucket_poverty 显式披露贫困(n<10 /
# battle rung 域缺桶)——「语料不足」如实报,不虚构样本;未披露的
# 贫困桶 = 快照 META 与池内容失配(重生成断裂)。
DELTA_POOL_COVERAGE_MIN_N = 10  # 同 gen_delta_pool_snapshot.BUCKET_COVERAGE_MIN_N(值同步维护)



def check_delta_pool_bucket_coverage(pool_map: dict,
                                     meta: dict | None = None) -> dict:
    """ADR-0306 件5 检查项 delta_pool_bucket_coverage。

    判据:
    - 任一节点任一桶 n<``DELTA_POOL_COVERAGE_MIN_N`` → 贫困桶,
      必须出现在 ``meta['bucket_poverty']``(生成器写入的显式披露)
      ——未披露 = 违规(贫困桶的胜率外推/方向判断缺边界声明);
    - battle rung 域(0-4)缺桶同样须披露(缺桶≠可忽略:采样走
      下探/兜底链,消费方须知情);
    - ``meta=None``(auto 池/fallback,无快照 META)时贫困桶一律
      计违规——auto 池无披露载体,贫困即应可见;
    - 空池(fallback/历史 Path 快照)不辖,violations=0(池语义
      检查不辖旧模型,同 battle_rung_pool_bucket_lock 先例)。
    """
    if not any((pool_map or {}).values()):
        return {'violations': 0, 'poor_buckets': [],
                'undisclosed': [], 'disclosed_by_meta': bool(meta),
                'note': '池空(fallback/Path 历史快照)不辖'}
    poor: list[str] = []
    battle = pool_map.get('battle') or {}
    for rg in range(0, 5):
        v = battle.get(rg) or []
        if len(v) < DELTA_POOL_COVERAGE_MIN_N:
            poor.append(f'battle:桶{rg}(n={len(v)})' if v
                        else f'battle:桶{rg}(缺)')
    for nt, buckets in sorted((pool_map or {}).items()):
        if nt == 'battle':
            continue
        for b, v in sorted(buckets.items(), key=lambda x: int(x[0])):
            if len(v) < DELTA_POOL_COVERAGE_MIN_N:
                poor.append(f'{nt}:桶{b}(n={len(v)})')
    disclosed = set((meta or {}).get('bucket_poverty') or [])
    undisclosed = [p for p in poor if p not in disclosed]
    return {'violations': len(undisclosed), 'poor_buckets': poor[:12],
            'undisclosed': undisclosed[:6],
            'disclosed_by_meta': bool(meta)}



# --- ADR-0292(批㉗ F3/F4)reward/supply Δ池分布锁 ---------------------
# 批㉗ F4 断言的「右胖尾 mean 9.15/p90+39」经语料复核为**跨 run 配对
# 伪影**:同 run 内奖励轮差分 n=43 全 +2;+27~+61/负值样本只出现在
# 「上一 run 末行 → 下一 run 首个奖励行」的跨 run 相邻行(reward 常为
# run 首节点,配对未按 run_id 分组即混入)。真值 = 恒 +2 分布。
REWARD_POOL_TRUTH_MEAN: float = 2.0    # 语料真值(同 run 差分,n=43)

REWARD_POOL_DRIFT_MAX: float = 1.0     # 均值漂移带(hp)

REWARD_POOL_MIN_N: int = 30            # 语料 n=43(2026-08-24)

# 伪影哨兵带:真值分布内不应出现跨 run 量级的大正值/负值(若语料
# 未来真出现回血机制,先按数据治理纪律核 run 边界再放宽本带)
REWARD_POOL_MAX_ABS: int = 20



def check_reward_delta_pool_bucket_lock(pool_map: dict) -> dict:
    """批㉗ 检查项 reward_delta_pool_bucket_lock(ADR-0292;迁移审计 w111(git 历史) 判据修正
    见 ADR-0345)。

    判据(规格原文「分布入池且均值≈语料真值」):
    - reward 池非空且 n≥30(分布**入池**:结算采样源是语料经验
      分布而非 EARLY_WIN_DELTA 常数);
    - reward 全样本均值距语料真值(+2.0)漂移 ≤1hp;
    - reward 跨 run 配对伪影哨兵:max |Δ| ≤ 20 且无负值——批㉗ F4 的
      +27~+61/−2 形态若在重生成后涌现,先查生成器 run 分组/语料
      接管段,不当作真值入锚;
    - supply **无真值锚**(迁移审计 w111(git 历史)/ADR-0345):批㉗ 落地时语料 supply 零
      样本,「非空时同判 reward」是外推假设;迁移审计 w109(git 历史) 再生后语料首现
      supply 真实样本(同 run 差分 Δ=0,n=1)——数据证伪 +2.0 锚。
      supply 只辖伪影哨兵(|Δ|>20 的跨 run 量大跳变,符号不敏感:
      无真值锚时负值不能直接判伪影),样本量入 stats 披露不设门
      (n 不足=证据不足,非违规——同空池语义)。

    空 reward/supply 池(fallback/历史 Path 快照)不辖,violations=0
    (同 battle 锁空池语义;分布入池的回归防线 = 采样器版本锁 +
    快照自洽锁,见 test_cw_adr0292_reward_pool_sampling)。
    """
    if not (pool_map.get('reward') or pool_map.get('supply')):
        return {'violations': 0,
                'note': 'reward/supply 池空(fallback/Path 历史快照)不辖'}
    out: list[str] = []
    stats: dict = {}
    for nt in ('reward', 'supply'):
        vals = [d for v in (pool_map.get(nt) or {}).values() for d in v]
        if not vals:
            continue
        mean = sum(vals) / len(vals)
        stats[nt] = {'n': len(vals), 'mean': round(mean, 2),
                     'max': max(vals), 'min': min(vals)}
        if nt == 'reward':
            # reward:语料真值锚完整辖(n 门 + 均值带 + 伪影哨兵带)
            if len(vals) < REWARD_POOL_MIN_N:
                out.append(f'reward n={len(vals)}<{REWARD_POOL_MIN_N}'
                           f'(分布证据不足)')
            if abs(mean - REWARD_POOL_TRUTH_MEAN) > REWARD_POOL_DRIFT_MAX:
                out.append(f'reward 均值{mean:+.2f} 距语料真值'
                           f'{REWARD_POOL_TRUTH_MEAN:+.1f} 漂移>'
                           f'{REWARD_POOL_DRIFT_MAX}hp')
            if max(vals) > REWARD_POOL_MAX_ABS or min(vals) < 0:
                out.append(f'reward 域[{min(vals)},{max(vals)}] 越伪影'
                           f'哨兵带(0~{REWARD_POOL_MAX_ABS})——疑跨 run'
                           f'配对伪影混入(批㉗ F4 形态),先核生成器'
                           f' run 分组')
        elif max(abs(d) for d in vals) > REWARD_POOL_MAX_ABS:
            # supply:无真值锚,只辖跨 run 量大跳变伪影(符号不敏感)
            out.append(f'supply 域[{min(vals)},{max(vals)}] 越伪影'
                       f'哨兵带(|Δ|>{REWARD_POOL_MAX_ABS})——疑跨 run'
                       f'配对伪影混入,先核生成器 run 分组')
    return {'violations': len(out), 'issues': out[:6], **stats}



# 以下为**批级聚合检查**(吃全批账本,跨局聚合;由 simulate_p1_batch
# 显式调用,不进 _BATCH_CHECKS 的逐局循环)与豁免边裁决探针。


def check_engine_seed_sell_exemption(rows: list[dict]) -> list[str]:
    """批⑩ F3 裁决探针(engine_seed 让位豁免边;ADR-0276)。

    判据(判据表原文):对照生产 r408 语义判 engine_seed 同名副本
    买入后的同轮卖出属「让位豁免」还是振荡——裁决=**豁免边扩到
    engine_seed 收集语境**(同轮同名买入 ≥2,与 copy 豁免同族:
    买 3 同名+卖冗余 1 是 3合1 素材收集,非通道互踩)。本探针只报
    豁免边之外的残留振荡(单张 engine_seed 买入即同轮卖回),与
    check_no_same_round_buy_sell 的豁免边界单一源一致(实现各自
    独立,判据漂移时双向锁会红)。
    """
    out: list[str] = []
    for row in rows:
        _seed_buys: dict[str, int] = {}
        _sold: set[str] = set()
        for a in row.get('actions') or []:
            if a.get('__type__') == 'BuyCard' \
                    and a.get('reason') == 'engine_seed':
                _n = (a.get('card') or {}).get('name')
                if _n:
                    _seed_buys[_n] = _seed_buys.get(_n, 0) + 1
            elif a.get('__type__') == 'SellBench' and a.get('name'):
                _n = a.get('name')
                if _n in _seed_buys and _seed_buys[_n] < 2 \
                        and _n not in _sold:
                    out.append(
                        f"p{row.get('plane')}r{row.get('round_num')} "
                        f"engine_seed 单张买入即同轮卖回: {_n}"
                        f"(振荡,非 3合1 收集语境——ADR-0276 裁决)")
                    _sold.add(_n)
    return out



# 四体系口径(同步自 cw_battle_calib._engines_count/_TRANSITION_TRAITS——检查
# 模块不 import cw_sim,依赖方向纪律;值漂移由双向锁暴露)
_ENGINES_TRAITS_SYNC: tuple[tuple[str, int], ...] = (
    ('持续伤害', 2), ('列车同行', 2), ('仙舟', 3),
)



def _rung_of_row(row: dict) -> int:
    """账本行的成型度 rung(四体系数;希儿系=希儿在场且量2/贝2)。"""
    st = row.get('state') or {}
    bf = st.get('board_factions') or {}
    dep = frozenset(d.get('char_id', '')
                    for d in (st.get('deployed') or []))
    n = sum(1 for bond, tier in _ENGINES_TRAITS_SYNC
            if bf.get(bond, 0) >= tier)
    if '希儿' in dep and (bf.get('量子同频', 0) >= 2
                          or bf.get('贝洛伯格', 0) >= 2):
        n += 1
    return n



#: boss 恒败回归判定的 n 地板(ADR-0308):迁移审计 w31(git 历史) 阶梯 boss 胜率
#: ~0.05,小于此轮数的 0 胜是抽样噪声(0.95^n),不判回归。
_BOSS_WIN_MIN_ROUNDS: int = 100



def check_boss_win_calibration(ledgers: list[list[dict]]) -> dict:
    """批⑪ F1 验收(boss 胜率校准;ADR-0277 → ADR-0308 修订)。

    - 胜 = boss 轮 sim.delta ≥ 0(outcomes.killed 同极性);
    - 违规 ①:boss 轮 ≥ ``_BOSS_WIN_MIN_ROUNDS`` 且 0 胜(结构性
      恒败回归——胜分支失效)。n 地板 = ADR-0308 修订:回退层
      胜负面换 迁移审计 w31(git 历史) 阶梯后 boss 实测胜率仅 ~0.05,小批(如 smoke
      n=25)全负是**抽样噪声不是回归**(0.95^25≈28%)——原「存在
      即判」判据在该量级下恒假红;n≥100 时 0 胜概率 <1%,恢复
      判定力;
    - 旧违规 ②(胜率随深度单调)已删(ADR-0308):迁移审计 w31(git 历史) 阶梯的
      胜负面与深度/成型度**无条件性**(语料是旧策略病局镜像,
      条件性未标定);池侧 boss 深度桶也无单调先验——保留该
      判据 = 把已废弃的 ADR-0277 设计(胜率=f(成型度))当真值
      锁,合法校准变更必假红。
    """
    wins = tot = 0
    for rows in ledgers:
        for row in rows:
            s = row.get('sim') or {}
            if s.get('node') != 'boss':
                continue
            wins += 1 if (s.get('delta') or 0) >= 0 else 0
            tot += 1
    issues: list[str] = []
    if tot >= _BOSS_WIN_MIN_ROUNDS and wins == 0:
        issues.append(f'boss {tot} 轮 0 胜(结构性恒败回归,'
                      f'ADR-0308 胜分支失效)')
    return {'violations': len(issues), 'boss_rounds': tot,
            'boss_wins': wins,
            'min_rounds': _BOSS_WIN_MIN_ROUNDS,
            'issues': issues[:5]}



def check_formation_hp_coupling_sentinel(ledgers: list[list[dict]]) -> dict:
    """批⑪ F2 验收哨兵(成型→hp 价值链;ADR-0277)。

    判据(判据表原文):e≥2 局(任一轮 rung≥2)与未达局的 final_hp
    差——win 侧校准落地前恒≈0(批⑪ 实测 26.9 vs 26.0,零耦合);
    落地后应显著为正,否则校准失败。违规 = 双侧都有局且差 ≤0
    (成型局不比未达局活得久 = 价值链仍断)。
    小批护栏(ADR-0286):任一侧 <20 局 = 均值噪声主导,只披露不
    判定(CI smoke n=25 曾以 formed_n=2 的 −0.35 假红;ADR-0312
    迁移审计 w50(git 历史) v7 采样键换 Σboard 后 13/12 侧再假红 −4.11,同批 n=300
    真判 diff +5.39 绿——护栏从 <5 提到 <20,对齐判据原意
    「真批次 n≥300 两侧几十局起」,判定力不减)。
    """
    formed: list[int] = []
    unformed: list[int] = []
    for rows in ledgers:
        if not rows:
            continue
        hp = rows[-1].get('hp')
        if hp is None:
            continue
        (formed if any(_rung_of_row(r) >= 2 for r in rows)
         else unformed).append(int(hp))
    diff = (sum(formed) / len(formed) - sum(unformed) / len(unformed)) \
        if formed and unformed else None
    small_n = formed and unformed and min(len(formed), len(unformed)) < 20
    violations = 1 if (diff is not None and diff <= 0
                       and not small_n) else 0
    out = {'violations': violations, 'formed_n': len(formed),
           'unformed_n': len(unformed),
           'formed_hp': round(sum(formed) / len(formed), 2) if formed else None,
           'unformed_hp': round(sum(unformed) / len(unformed), 2) if unformed else None,
           'diff': round(diff, 2) if diff is not None else None}
    if small_n:
        out['note'] = '样本不足(<5/侧)只披露不判定'
    return out



def check_levelup_binding(ledgers: list[list[dict]]) -> dict:
    """批⑪ F4 披露(LevelUp binding 率;ADR-0277)。

    判据(判据表原文):LevelUp 动作时 len(deployed) ≥ level 记
    binding(当轮 depth 可受益:dep<lv 时 depth=min 卡在 dep),
    否则记 loose;r8/r9 loose 占比 >60% 报警(阈值策略语义批⑪
    裁:60% 取判据表原值)。升级前等级 = 上一轮账本 level(轮内
    升级完成会抬高本行 level;首轮 prev=3,同批③检查近似声明)。
    r9 升级在 P1 内收益恒 0(P1 截止 r9;P2 入口继承价值 sim
    不可判)——本检查辖 r8/r9 窗口披露,不断言 r9 该不该升。
    """
    binding = loose = 0
    for rows in ledgers:
        prev_level = 3
        for row in rows:
            if (row.get('round_num') or 0) in (8, 9):
                if any(a.get('__type__') == 'LevelUp'
                       for a in row.get('actions') or []):
                    dep_n = len((row.get('state') or {}).get('deployed')
                                or [])
                    if dep_n >= prev_level:
                        binding += 1
                    else:
                        loose += 1
            prev_level = ((row.get('state') or {}).get('level')
                          or prev_level)
    total = binding + loose
    share = loose / total if total else 0.0
    return {'violations': 1 if (total and share > 0.6) else 0,
            'binding': binding, 'loose': loose, 'loose_share': round(share, 3)}



def check_r5plus_refresh_closure(ledgers: list[list[dict]]) -> dict:
    """批⑪ F6 披露(r5+ 刷新闭合;ADR-0277)。

    判据:sim r5-r9 刷新次数(批⑪ 实测 0/483,78% 刷新集中 r3/r4,
    r5 后刷通道事实关闭)——实机遥测对照后定性。**纯披露型**
    (violations 恒 0):刷新次数偏离 0 不是违规,是行为变化信号
    (成本带窗口开合),供跨批对照。
    """
    n = 0
    for rows in ledgers:
        for row in rows:
            if (row.get('round_num') or 0) >= 5:
                n += sum(1 for a in row.get('actions') or []
                         if a.get('__type__') == 'RefreshShop')
    return {'violations': 0, 'r5plus_refreshes': n}

