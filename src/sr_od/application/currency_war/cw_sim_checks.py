"""sim 账本异常断言(②;实机学费的回灌载体)。

设计定谳(两轮对抗审查):
- **纯函数**:吃账本 dict 列表(每局 = 逐轮行列表),不 import
  cw_sim——依赖方向 = 调用方(simulate_p1_batch/CLI)跑完把账本
  传进来(二轮#7,非模块级 import 不构成循环);
- **分布级预警在 batch 内嵌**(默认开,--checks False 关);
  确定性回归走测试仓合成账本双向锁(检查逻辑本身的锁);
- **局49 指纹(r371b 起)sim 内可达**:冷启动门判据扩到
  「owned 空 或 plane1 r≤2」后,sim 开局系统卡不再架空门——
  检查升级进 _BATCH_CHECKS 批量跑(旧版「只对构造账本」限制
  是二轮审查#3 基于 r368 判据的结论,已被 r371b 推翻)。

每条检查的 docstring 记来源局号/指纹(学费账本;ADR 见对应条目)。

检查网清单(ADR-0289 检查项清偿批后;29 批压测 123 条设计 →
29 已有 + 清偿批 48 新实现 + 46 归档,归档死因清单见 ADR-0289):
- 逐局违规锁(进 _BATCH_CHECKS,sim 批次自动扫):ledger_
  consistency / coldstart_direction / deploy_fills_cap /
  equip_worn_in_battle / no_component_equipped_p1 /
  levelup_interest_engine_gate / no_same_round_buy_sell /
  bench_full_deadlock_probe /
  shop_slot_consumption / deploy_after_buy_semantics /
  + 清偿批:gold_nonneg /
  bench_capacity / deployed_schema_filter / engine_seed_not_
  resold / buys_at_full_bench / oscillation_xp_cap /
  levelup_flat4_lock / phantom_equip_no_wear /
  degrade_recover_mutex;
  (旧 v1 线库语义检查器——carry_gate_bench_deadlock /
  bond_fallback_purchase_validity / carry_on_shelf_responded /
  no_future_carry_sold / dead_system_second_pivot /
  protect_set_bench_share / carry_gate_outcome_tracking /
  recipe_refresh_ev_guard——随 v1 策略删除,ADR-0336)
- 逐局披露归 0 锁:phantom_rebuy_disclosure /
  ledger_deploy_lag_disclosure / hp_upper_bound_truth;
- 批级聚合(cw_sim 接线;清偿批新条目经 run_batch_level_checks
  聚合入口,cw_sim.py 接线随 worker X 合流后并入 simulate_p1_
  batch):boss_win_calibration / formation_hp_coupling_sentinel /
  levelup_binding / r5plus_refresh_closure / sim_endgold_calib
  + 清偿批披露/哨兵(见该函数注释);
- 池级(吃 Δ 池 dict):delta_pool_bucket_min_n /
  depth_cliff_monotonicity / battle_rung_pool_bucket_lock /
  reward_delta_pool_bucket_lock(ADR-0292)/
  sim_pool_no_cost_truncation + encounter_rung_sample_budget;
- 语料级(吃 outcomes/summary dict,调用方显式调):
  attach_run_detector / hp_monotonic_sentinel /
  plane_reached_consistency;
- A/B 位:ab_depth_boundary_confound / ab_resolution_floor;
- 锚登记/工具:ANCHOR_REGISTRY_N300(+S300 第二参照段 +
  低可见通道 registry)/ anchor_segment_noise_band /
  anchor_seed_portability_n600 / rare_metric_min_n /
  adr0266_ab_guard / mc_faction_calib;
- 批㊲(ADR-0306 对抗审计):delta_pool_poverty_selfconsistency
  (贫困披露↔池内容双向结构对拍)/ boss_rung_corpus_sample_gate(boss
  rung 语料样本门);随批加固 ab_verdict_claim 词表反转(默认辖)
  + paired_prefork_wave_identity 扩全波。(boss_win_p_cache_
  freshness 随 ADR-0308 废除——rung 外推机制已被 W31 节点胜率
  阶梯替换,无进程内缓存可查。)
- 批37(难度读链翻转判读鲁棒性,commit 09cf8296):
  difficulty_curve_live_contamination(逐帧真读/简报兜底值混入
  难度曲线的污染判读守卫——live=False 恒值帧与 live 真值并存时,
  全帧口径的爬升/均值必须判废,live-only 过滤是硬前提;批39 补
  note 级部分污染披露——值集相交的混帧(live{8}+nonlive{8,108}
  型)不再静默,mixed_note 披露混帧计数与两组值集)。
- 批38(win_model M1 训练表特征面):win_train_table_feature_health
  (训练前门——零方差特征/tier≥2 覆盖样本门/killed 标签断裂,
  语料级显式调,不进 sim 批量内嵌)。
- 批39(r9 boss 语料判读口径):boss_hp_floor_censoring(boss 行
  hp 地板删失披露 + killed 采集断裂/败局 hp 未降跳变红——
  hp_after==1 的败局掉血是下界非真值,伤害口径必须剔删失行)。
"""
from __future__ import annotations


def check_ledger_consistency(rows: list[dict]) -> list[str]:
    """账本内部一致性(锁账本本身没写坏;generic,sim 批量内嵌)。

    逐轮守恒:gold == gold_before + income合计 − (buys+levelup+
    refresh) + sell_income。违例 = 账本记录 bug(非策略病)——
    先修账本再谈策略判读。
    """
    out: list[str] = []
    for row in rows:
        s = row.get('sim') or {}
        gb = s.get('gold_before')
        inc = s.get('income') or {}
        sp = s.get('spend') or {}
        if gb is None:
            out.append(f"r{row.get('round_num')}: 缺 gold_before")
            continue
        expect = (gb + sum(inc.values())
                  - sum((sp.get('buys') or {}).values())
                  - sp.get('levelup', 0) - sp.get('refresh', 0)
                  + sp.get('sell_income', 0))
        if row.get('gold') != expect:
            out.append(
                f"r{row.get('round_num')}: 金不守恒 "
                f"{row.get('gold')} != {expect}(gb={gb})")
    return out


def check_deploy_fills_cap(rows: list[dict]) -> list[str]:
    """局62 指纹(r387 回灌断言;ADR-0249 执行层代理)。

    指纹:开局轮后(plane1 r2-r4,首两轮系统卡未定排除)deployed
    数 < cap 且 bench 有可上件(≥1 张)——r387 修前形态(配方
    围栏无条件拦散牌,cap=3 只上 1 人空槽白丢血)。r390 执行层
    代理落地后 sim 内可达(deployed=真实围栏输出);变异探针
    实证:关 cap_roomy 守卫 → loss≤2 0.017→0.117 涌现
    (本检查=该差异的常态化拦截)。

    边界:bench 空(没牌可上)不报;**差 1 以内的贴 cap 不报**
    (配方围栏+cap 紧张是合法形态——r387 修的是「富余仍拦」);
    **同名副本不算「可上货」**(r404-A2:5.1.7 同角色在场只 1,
    第二张同名留 bench 是 3合1 素材的合法囤积,不是围栏拦截);
    **跨轮持续性门**(连续 2 轮 deployed≤cap-2 才报):sim 代理
    在决策前生成、同轮买入后不刷新——单轮差 2 常是「买了还没
    重新部署」的过渡态(game14 实证:r2 4/6→r3 6/6),连续 2 轮
    才是围栏系统性拦截的指纹;
    **增长豁免**(ADR-0260):连续 2 轮短缺但 deployed 在**增长**
    不报——deploy 代理先于买入跑,每轮都买入新可上件时,账本
    快照恒见「上轮买、未部署」滞后一拍的形态(engine_seed 放行
    后买面变宽,seed4 r2 4/6→r3 5/7 实证);围栏系统性拦截的
    指纹是 deployed 停滞,不是增长。
    """
    out: list[str] = []
    _short_rounds: list[tuple[int, int]] = []   # (轮号, deployed 数)
    for row in rows:
        if row.get('plane') != 1:
            continue
        rn = row.get('round_num') or 0
        if not (2 <= rn <= 4):
            continue
        st = row.get('state') or {}
        deployed = st.get('deployed')
        cap = st.get('cap')
        if deployed is None or not cap:
            continue
        bench = st.get('bench') or []
        # r404-A2:可上货=非同名副本(在场名单外的名字)
        dep_names = {d.get('char_id') for d in deployed}
        usable = [b for b in bench
                  if b.get('char_id') not in dep_names]
        if len(usable) + len(deployed) <= cap:
            continue
        if len(deployed) < cap - 1:
            _short_rounds.append((rn, len(deployed)))
    for (a, da), (b, db) in zip(_short_rounds, _short_rounds[1:],
                                strict=False):
        if b - a == 1 and db <= da:   # ADR-0260 增长豁免
            out.append(
                f"p1r{a}-r{b}: deployed 连续 ≤cap-2"
                f"(bench 有货,围栏系统性拦截空槽——r387 修前形态)")
    return out


def _normalize_buy_reason(reason: str) -> str:
    """买入 reason 归一化(W43 leader 裁决 4)。

    decision_v2 栈的账本 reason 带 ``d2_`` 前缀(可再带 ``_merge`` 尾,
    ``arbiter._materialize``)——检查器豁免边/计数用裸 reason 精确匹配时,
    ``d2_copy``/``d2_engine_seed`` 会同时造成**误报**(豁免失效)与
    **失明**(指纹匹配不上)。本 helper 与 coldstart 检查既有归一化做法
    同款(单一源化),三检查器统一走这里。
    """
    return (reason or '').removeprefix('d2_').removesuffix('_merge')


def check_coldstart_seed_squander(rows: list[dict]) -> list[str]:
    """局49 指纹(首条回灌断言;ADR-0240+r371b;r368 修前形态)。

    指纹:plane1 r≤2(开局轮)时买入 reason ∈ {'pair','off'}——
    _want_label 的 pair 谓词分支返回 classify_buy **身份**,非方向
    件的该分支产物就是 'pair'(同阵营线外)或 'off'(异阵营线外,
    **局49 原始形态**:翡翠/大丽花对空板 A5 门放行)。r368+r371b
    冷启动门在该窗口只放行方向件,violation 即门失效/回归。

    - r371b 起(sim 判读同构基建后)冷启动门在 **sim 内可达**
    (旧版 owned 空 判据被开局系统卡架空——二轮审查#3 的
    「只对构造账本」限制解除,已进 _BATCH_CHECKS);
    - 合法不报:reason=bridge_seed/engine(pair 通道放行的
    方向件)、line(锁线形态逻辑辖区)/p2_core/emergency/
    swap/board_focus(其它通道各有语义,不越权);
    - **仅 v2 栈账本适用**:生产配置 strategy_id=
      decision_v2(旧 line_v2 随 ADR-0336 已删)时实机 decisions.jsonl
      同样适用(BuyCard.reason 是共享 dataclass,生产遥测同带标签);
      **default 栈**(买牌走 cw_plan,reason='plan')不辖于 r368 门,
      跑此检查必误报——生产侧按局 strategy_id/actions reason 词表
      判栈后选择。
    """
    out: list[str] = []
    for row in rows:
        if row.get('plane') != 1 or (row.get('round_num') or 9) > 2:
            continue
        for a in row.get('actions') or []:
            if a.get('__type__') != 'BuyCard':
                continue
            reason = a.get('reason') or 'unknown'
            # d2_ 前缀归一化(原 2026-08-24 leader 核实;W48 裁决 4 起
            # 单一源到 _normalize_buy_reason)
            reason = _normalize_buy_reason(reason)
            if reason not in ('pair', 'off'):
                # r383b:copy=开局轮同名副本(3合1 素材,口述[15]
                # 压缩牌库)——合法放行,非门失效;区分见 docstring。
                continue
            card = a.get('card') or {}
            out.append(
                f"p{row.get('plane')}r{row.get('round_num')} "
                f"冷启动买入非方向件: {card.get('name')}"
                f"(reason={reason}, cost={card.get('cost')})")
    return out


def check_equip_worn_in_battle(rows: list[dict]) -> list[str]:
    """r388 反向指纹(装备层代理回灌断言;r393)。

    指纹:战斗轮(r3+,装备持有语义=r388 开局 hold 后)owned_equips
    非空但 equipped 空 **连续 2 轮**——装备该穿不穿(白板挨打;
    r388 修的是反向「开局乱穿」,本检查防「hold 太宽不穿」的
    过矫回归)。开局 r1-r2(r388 hold 语义)不报。

    边界:deployed 空(没人可穿)不报;**合成保留组件(ADR-0265
    RESERVED_COMPONENTS)不计入「owned 非空」**——组件 P1 留
    owned 待合成是修复语义本身,owned 全组件时 equipped 空合法;
    其余工具类(不可穿)的判定交由 equip_allocation 语义(不可穿
    件不会进 equipped,也不会被移出 owned——按 owned 余量判,工具
    留 owned 是合法)。
    近似:owned>0 且 equipped=0 且 deployed>0 连续 2 战斗轮 → 报
    (工具误报由 owned 名单含工具的概率压低,后续可精化)。
    """
    from sr_od.application.currency_war.cw_synthesis import (
        RESERVED_COMPONENTS,
    )
    out: list[str] = []
    _stalls: list[int] = []
    for row in rows:
        if row.get('plane') != 1:
            continue
        rn = row.get('round_num') or 0
        node = (row.get('sim') or {}).get('node')
        if node not in ('battle', 'encounter', 'boss') or rn < 3:
            continue
        st = row.get('state') or {}
        _owned = [e for e in (st.get('owned_equips') or [])
                  if e not in RESERVED_COMPONENTS]
        if _owned and not st.get('equipped') \
                and st.get('deployed'):
            _stalls.append(rn)
    for a, b in zip(_stalls, _stalls[1:], strict=False):
        if b - a == 1:
            out.append(f"p1r{a}-r{b}: owned 非空连续零穿着"
                       f"(白板挨打——r388 hold 过矫形态)")
    return out


def check_levelup_interest_engine_gate(rows: list[dict]) -> list[str]:
    """升级授权依据判据(W131 重定义,W123 §5.2;ADR-0354;旧 ADR-0266/r406 指纹)。

    **判据(重定义后)**:违规 = lv≥5(追级段)的 LevelUp 发生在时点金
    (本轮首波金,=收入后花销前)<50 **且授权依据 ∉ {pop_slot, dp}**。
    授权依据 = sim 账本 LevelUp 行的 ``auth`` 键(LevelUp.auth_basis
    观测字段,arbiter 升级门/remediation 补偿臂放行时写入,单一源=
    ``ev.levelup_ev_basis``)。

    重定义动机(W123 §3.3/§5.2):旧判据「金<50 且未曾满息即违规」把
    [33] 人口位(W123 实测 378 违规中绝大多数,W126 后 206)的合法
    <50 升级全数计违规——授权语义(W119/ADR-0347)落地后,判据应读
    授权依据而非金阈值。合法放行面:① pop_slot([33] 人口位:cap 满∧
    bench 有等待上场的目标件)、② dp(DP 花费授权,平台未破);
    ③ static_ev(静态 EV 平台账)**不在白名单**——W123 明示该臂
    花后<50 的帧量级 0-1,保留计违规(保守侧:静态账是估值端,息
    引擎口径下可疑面不豁免;涌现≥量级再裁决)。无 auth 键/空值 =
    无授权依据(default 栈旧调用/未过账路径)→ 违规。

    近似声明(承旧):①升级前等级用**上一轮账本 level**(轮内升级
    完成会抬高本行 level,prev_level 才是购买时的等级;首轮 prev=3);
    ②时点金 = shop_waves 首波 gold(决策发生在收入后/花销前);
    ③授权依据是**放行时点的臂名快照**(动作对象携带),检查器不复
    判——重演需要 cost/val 等决策期中间量,账本不携(声明数据边界);
    gold≥50 的升级不报(与旧判据同:息平台在场,无追级风险面)。
    """
    out: list[str] = []
    prev_level = 3
    for row in rows:
        if row.get('plane') != 1:
            continue
        waves = (row.get('sim') or {}).get('shop_waves') or []
        gold0 = waves[0].get('gold') if waves else row.get('gold')
        for a in row.get('actions') or []:
            if a.get('__type__') != 'LevelUp':
                continue
            basis = a.get('auth', '')
            if prev_level >= 5 and gold0 is not None and gold0 < 50 \
                    and basis not in ('pop_slot', 'dp'):
                if basis == 'static_ev':
                    kind = 'static_ev 估值账放行(息引擎口径下保留可疑)'
                else:
                    kind = '无授权依据'
                out.append(
                    f"p1r{row.get('round_num')} LevelUp 时点金 {gold0}<50"
                    f" 授权依据={basis or '(空)'}(lv{prev_level}"
                    f" {kind}——ADR-0354 违规)")
        prev_level = (row.get('state') or {}).get('level') or prev_level
    return out


def check_no_component_equipped_p1(rows: list[dict]) -> list[str]:
    """压测经济批 [29] 指纹(装备组件保留;ADR-0265;r405)。

    指纹:P1 任意轮 equipped 含合成保留组件(cw_synthesis.
    RESERVED_COMPONENTS = 7 件标准基础件 ∪ 光能电池)——
    过渡期把组件穿给过渡角色 = 锁死合成路线 + 浪费转移成本
    (口述 [29],局70 实机 + sim 16/60 局同构实证,sim/实机
    同一 equip_allocation 纯函数)。

    0 容忍:key_equips 豁免在 equip_allocation 内部(comp 显式
    声明的关键装备意图;COMP_LIBRARY 实查零重叠),违规即
    过滤失效/回归。P1 窗口(plane==1 全轮,不只 supply 轮——
    组件可跨轮滞留 equipped)。
    """
    from sr_od.application.currency_war.cw_synthesis import (
        RESERVED_COMPONENTS,
    )
    out: list[str] = []
    for row in rows:
        if row.get('plane') != 1:
            continue
        for eq in (row.get('state') or {}).get('equipped') or []:
            if eq.get('equip') in RESERVED_COMPONENTS:
                out.append(
                    f"p1r{row.get('round_num')} 合成组件被穿着:"
                    f" {eq.get('equip')} → {eq.get('char')}"
                    f"(ADR-0265 组件保留违规)")
    return out


def check_no_same_round_buy_sell(rows: list[dict]) -> list[str]:
    """压测自由批 F1 指纹(同轮买卖互斥;ADR-0267;r408)。

    指纹:同轮(同账本行)内「BuyCard(X) 先于 SellBench(X)」——
    bench 满员态 engine_seed 买通道与卖通道在同名卡上互踩,单轮
    最高 8 连振荡(自由批实测 235 次/38 局),白拿 XP/引擎种子
    归零/boss 轮段预算烧尽。r408 修后 0 容忍。

    边界:卖→买的同轮序(先卖腾位再买入)是合法经济动作,不报;
    **3合1 让位豁免的检查侧镜像**:reason='copy' 的买入是 r383b
    同名副本素材(口述[15] 压缩牌库),其同名卖出=卖合成冗余的
    让位(ADR-0267 豁免边),不报——**批⑩ F3 裁决(ADR-0276)扩
    豁免边**:reason='engine_seed' 同名买入 ≥2(同轮)同属 3合1
    素材收集语境(买青雀×3 后卖冗余 1),同样豁免;单张买入即卖
    (振荡主通道)仍 0 容忍。
    仅 v2 栈(line_v2/decision_v2)账本适用(default 栈 reason='plan' 的
    卖出语义不同,生产侧按 strategy_id 分栈后选择)。
    """
    out: list[dict] = []
    for row in rows:
        bought: list[str] = []
        _copy_names: set[str] = set()
        _seed_buys: dict[str, int] = {}   # 批⑩ F3 裁决(ADR-0276)
        for a in row.get('actions') or []:
            if a.get('__type__') == 'BuyCard':
                _n = (a.get('card') or {}).get('name')
                _rs = _normalize_buy_reason(a.get('reason') or '')
                if _n and _rs == 'copy':
                    _copy_names.add(_n)   # 3合1 收集语境:让位豁免
                elif _n and _rs == 'engine_seed':
                    _seed_buys[_n] = _seed_buys.get(_n, 0) + 1
                    bought.append(_n)
                elif _n:
                    bought.append(_n)
            elif a.get('__type__') == 'SellBench' \
                    and a.get('name') in bought \
                    and a.get('name') not in _copy_names:
                # 批⑩ F3 裁决(ADR-0276):engine_seed 同名买入 ≥2
                # (同轮) = 3合1 素材收集语境,其同名卖出 = 合成冗余
                # 让位(与 copy 豁免同族),不报;单张买入即卖 = 振荡
                # (r408 主通道)仍 0 容忍。
                if a.get('name') in _seed_buys \
                        and _seed_buys[a.get('name')] >= 2:
                    continue
                out.append(
                    f"p{row.get('plane')}r{row.get('round_num')} "
                    f"同轮买后卖: {a.get('name')}"
                    f"(ADR-0267 买卖互斥违规)")
                bought.remove(a.get('name'))   # 每对只报一次
    return out


def check_sim_pool_no_cost_truncation(copies: dict[str, int]) -> dict:
    """批④F1(实机已裁决;ADR-0272):sim 牌池不得按费用截断。

    判据:池 copies(名→剩余副本)必须含 4 费与 5 费角色——旧
    `_Pool(max_cost=3)` 把 4/5 费概率质量静默重归一化(lv9 4费
    .30→0),14 个 4 费角色不进池,低费虚高频 = 供给失真。P1 等级
    可达 9(REFRESH_PROB lv7 起 5 费 .01→lv9 .10)→ 5 费可达,
    一并入池。simulate_p1 池构造后硬断言本检查(不变式,违规即
    raise);batch 报告 `checks_violations` 同步披露。纯 dict 入参,
    不 import cw_sim。
    """
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    missing = [cost for cost in (4, 5) if not any(
        CHARACTERS[n].cost == cost for n in copies)]
    return {'violations': len(missing), 'missing_costs': missing}


# --- ADR-0289 检查项清偿批:逐局违规锁(29 批压测设计清偿) -------

def check_gold_nonneg_invariant(rows: list[dict]) -> list[str]:
    """批⑮ F6(gold≥0 不变量;ADR-0289 清偿)。

    判据(设计表原文):ledger 检查器加 gold≥0 断言——基线
    4/2698 轮违规(修复前),执行器守卫/账本修复后应归 0。
    轮末口径(批⑦ 边界声明:轮内动作顺序不可见,负金不变量
    仅轮末口径成立)。违规 = 执行器 BuyCard 前守卫回归或账本
    写坏。
    """
    out: list[str] = []
    for row in rows:
        g = row.get('gold')
        if g is not None and g < 0:
            out.append(
                f"p{row.get('plane')}r{row.get('round_num')}: "
                f"gold={g}<0(负金不变量破——批⑮ F6)")
    return out


def check_bench_capacity_invariant(rows: list[dict]) -> list[str]:
    """批⑰ F6(bench 容量不变式;ADR-0283 伴随;ADR-0289 清偿)。

    判据(设计表原文):任意轮 ledger len(bench)>9 → 违规(状态
    合法性;修复=sim 买守卫全段累计——ADR-0283 超容买守卫已落
    地,违规 = 守卫回归或 reward/发件通道破容)。BENCH_CAPACITY=9
    同步自 cw_state(镜像纪律;值漂移由锁测试暴露)。
    """
    out: list[str] = []
    for row in rows:
        n = len((row.get('state') or {}).get('bench') or [])
        if n > 9:
            out.append(
                f"p{row.get('plane')}r{row.get('round_num')}: "
                f"bench={n}>9(容量不变式破——批⑰ F6/ADR-0283)")
    return out


def check_deployed_schema_filter(rows: list[dict]) -> list[str]:
    """批⑧ F3(deployed/bench 空 char_id 过滤;ADR-0289 清偿)。

    判据(设计表原文):写入端不序列化空 char_id 条目(或消费端
    统一过滤)——生产语料 15.7% deployed 条目空 char_id(958/6089)
    曾让一切 len(deployed) 计数虚高。sim 账本侧不变量:bench/
    deployed 条目 char_id 必须非空(cw_sim 写入端已过滤 deployed,
    本检查锁写入端不再回归;bench 侧同辖)。
    """
    out: list[str] = []
    for row in rows:
        st = row.get('state') or {}
        for key in ('bench', 'deployed'):
            if any(not item.get('char_id')
                   for item in (st.get(key) or [])):
                out.append(
                    f"p{row.get('plane')}r{row.get('round_num')}: "
                    f"{key} 含空 char_id 条目(计数虚高源——批⑧ F3)")
    return out


def check_engine_seed_not_resold(rows: list[dict]) -> list[str]:
    """自由批(engine_seed 买入 ≥2 轮内不回卖;0 容忍;ADR-0289 清偿)。

    判据(设计表原文):reason=engine_seed 的买入在其后 ≥2 轮内
    不被卖出——现状(设计时)169 次即卖。引擎种子被当回合素材
    卖回 = 种子归零 + 白烧预算(r408 前振荡主通道的跨轮残留形态)。

    豁免边(与 ADR-0276 同轮豁免同族):买入轮同名买入 ≥2 =
    3合1 素材收集语境,其冗余让位不报(合成消化时序内卖出合法);
    单张买入即跨轮卖回(振荡主通道)仍 0 容忍。

    W88(ADR-0339 件3):真根因=carry_gate 死锁豁免(discipline
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


def check_overflow_gold_zero_buy_streak(rows: list[dict]) -> list[str]:
    """W96 溢出金断买(W93 根因回灌;[17] >50 溢余该花;违规型)。

    判据:位面1 内连续 ≥2 个决策轮金 >50 且零买入(BuyCard)——
    金趴在 50 上方不动 = [17]「>50 的每一分都该花」被违反。升级
    (LevelUp)也算花金,有升级的轮不计数(金在滴漏不算冻结);
    [32] boss 轮 LevelUp 禁令辖内的轮照常计数(boss 轮该花在买牌/
    装备上,断买仍违规)。W93 病例:run_20260825_130151 r7-r9 金
    59→90 溢出,目标件第 2 份生成层(r410 守卫)+评分层(份数零
    显影)双盲区,三连零买只靠升级滴漏。
    豁免(ADR-0343):行带 formed_stop=True 的轮**重置 streak**——
    成型停手是 [13]「过渡成型即可停手攒息」的正确行为,与 [17]
    在「成型」谓词处分割状态空间(未成型金趴窝=违规,成型停手=
    守息);旧局无该字段不豁免(兼容)。
    """
    rid = rows[0].get('run_id', '?') if rows else '?'
    streak = first_r = 0
    worst = worst_r = 0
    for row in rows:
        if (row.get('plane') or 1) != 1:
            continue    # 只辖 P1(金跨位面继承,P2+ 语义另裁)
        if row.get('formed_stop'):
            streak = 0   # ADR-0343:成型停手轮=合法零买,断 streak
            continue
        gold = row.get('gold') or 0
        spent = any(a.get('__type__') in ('BuyCard', 'LevelUp')
                    for a in row.get('actions') or [])
        if gold > 50 and not spent:
            if streak == 0:
                first_r = row.get('round_num') or 0
            streak += 1
            if streak > worst:
                worst, worst_r = streak, first_r
        else:
            streak = 0
    if worst >= 2:
        return [f'{rid}: P1 溢出金断买 {worst} 连'
                f'(r{worst_r} 起,金>50 零买零升级——[17] 溢余该花)']
    return []


def check_buys_at_full_bench(rows: list[dict]) -> list[str]:
    """自由批(bench 满不买;0 容忍;ADR-0283 守卫的账本锁)。

    判据(设计表原文):bench≥上限 时不再输出 BuyCard——现状
    (设计时)655 次;上限真值已核(BENCH_CAPACITY=9,cw_state
    design doc 实测)→ 锁 0。ADR-0283 超容买守卫落地后 BuyCard
    动作只在该轮容量允许时出现。

    容量口径(近似声明):期初 bench = 上一轮末 bench;本轮可买
    上限 = 9 − 期初 + 本轮卖出数 + 2×本轮 merges(3合1 每次腾
    2 席;守卫在执行层逐笔判,账本只能轮末重放近似)+ 本轮 bench
    腾位数(DeployMove 上阵 + applied CompTransaction 的
    bench_delta 披露[执行点真值,W101 涌现修正]:过渡型板面轮内
    重排变多,缺该项会把合法买误报超容——seeds 18/22 实证,r8
    九买伴随 8 笔事务,执行层守卫 cw_sim r419 逐笔判活状态无回归)。
    SwapDeploy 净零/SellDeployed 不动 bench/shop 源填位不占
    bench,均不计;旧账本(无 bench_delta 字段)按 0 读——重放
    旧批时该检查以现口径为准,历史违规记录见 git 历史。
    """
    out: list[str] = []
    prev_bench = 0
    for row in rows:
        st = row.get('state') or {}
        acts = row.get('actions') or []
        buys = sum(1 for a in acts if a.get('__type__') == 'BuyCard')
        sells = sum(1 for a in acts if a.get('__type__') == 'SellBench')
        deploys = sum(1 for a in acts if a.get('__type__') == 'DeployMove')
        for a in acts:
            if a.get('__type__') == 'CompTransaction' \
                    and a.get('result') == 'applied':
                # W101:applied 事务的 bench 净腾位(执行点真值
                # bench_delta;账本不展开事务明细,重放只能吃该披露)
                deploys += int(a.get('bench_delta', 0) or 0)
        merges = (row.get('sim') or {}).get('merges') or 0
        allowed = 9 - prev_bench + sells + 2 * merges + deploys
        if buys > max(allowed, 0):
            out.append(
                f"p{row.get('plane')}r{row.get('round_num')}: 买入 {buys}"
                f" 笔超容量上限 {max(allowed, 0)}(期初 bench {prev_bench}"
                f"+卖 {sells}+merge {merges}+腾位 {deploys}"
                f"——满仓买守卫回归,"
                f"自由批/ADR-0283)")
        prev_bench = len(st.get('bench') or [])
    return out


def check_oscillation_xp_cap(rows: list[dict]) -> list[str]:
    """自由批观测项(白拿 XP 上限报警;ADR-0289 清偿)。

    判据(设计表原文):白拿 XP(振荡次数×4)超过升级所需 XP
    的 30% → 报警(设计时 seed4=152 XP)。振荡 = 同轮买后卖
    (r408 通道,ADR-0267/0276 豁免边同源:copy/engine_seed≥2
    收集语境不计);XP_PER_BUY=4 同步自 cw_state(镜像纪律)。
    r408 修后振荡应归 0 → 本检查恒绿;涌现即买卖互踩回归。
    """
    from sr_od.application.currency_war.cw_state import (
        XP_TO_NEXT_LEVEL,
    )
    out: list[str] = []
    for row in rows:
        bought: list[str] = []
        copy_names: set[str] = set()
        seed_buys: dict[str, int] = {}
        osc = 0
        for a in row.get('actions') or []:
            t = a.get('__type__')
            if t == 'BuyCard':
                _n = (a.get('card') or {}).get('name')
                if not _n:
                    continue
                _rs = _normalize_buy_reason(a.get('reason') or '')
                if _rs == 'copy':
                    copy_names.add(_n)
                else:
                    if _rs == 'engine_seed':
                        seed_buys[_n] = seed_buys.get(_n, 0) + 1
                    bought.append(_n)
            elif t == 'SellBench' and a.get('name') in bought \
                    and a.get('name') not in copy_names:
                if seed_buys.get(a.get('name'), 0) >= 2:
                    continue   # 收集语境让位(ADR-0276)
                osc += 1
                bought.remove(a.get('name'))
        if osc:
            level = (row.get('state') or {}).get('level') or 3
            need = XP_TO_NEXT_LEVEL.get(level, 4)
            if osc * 4 > 0.3 * need:
                out.append(
                    f"p{row.get('plane')}r{row.get('round_num')}: 振荡 "
                    f"{osc} 次白拿 XP {osc * 4} > 升级所需 {need} 的 30%"
                    f"(自由批观测报警)")
    return out


def check_levelup_flat4_ledger_lock(rows: list[dict]) -> list[str]:
    """批⑳ F3 裁决(LevelUp 单击价 flat 4 消费侧采纳锁;ADR-0289)。

    判据:批⑳ 裁决 levelup 单击价真值 = flat 4(lv5-8 净证;
    lv3-4 推定),无逐级真值表——账本侧锁:每轮 spend.levelup
    == 4 × 本轮 LevelUp 动作数。不一致 = 执行器支出通道未采纳
    flat4(批⑨ F1 双模型并存回归)或账本写坏。批⑲ 原设计
    (逐级真值表)已被本裁决作废(归档,见 ADR-0289)。
    """
    out: list[str] = []
    for row in rows:
        acts = row.get('actions') or []
        n_lv = sum(1 for a in acts if a.get('__type__') == 'LevelUp')
        spent = ((row.get('sim') or {}).get('spend') or {}) \
            .get('levelup', 0)
        if spent != 4 * n_lv:
            out.append(
                f"p{row.get('plane')}r{row.get('round_num')}: "
                f"levelup 支出 {spent} ≠ 4×{n_lv}(flat4 采纳回归"
                f"——批⑳ F3 裁决)")
    return out


def check_phantom_equip_no_wear(rows: list[dict]) -> list[str]:
    """批⑲ F2(幻影装备不进穿着;0 容忍;ADR-0289 清偿)。

    判据(设计表原文):equipped 含装备注册表外名字('钻石'/
    '未知装备')→ 违规——supply 节点的带钻幻影件(SIFT 未识别
    占位)以真装备身份进穿着 = 装备分配层吃到伪实体。注册表 =
    cw_equipment_data.EQUIPMENT_ROSTER(生成器产物,单一源);
    合成保留组件(RESERVED_COMPONENTS)本身是注册表内真件,
    穿着是否合法由 no_component_equipped_p1 另辖。
    """
    from sr_od.application.currency_war.cw_equipment_data import (
        EQUIPMENT_ROSTER,
    )
    out: list[str] = []
    for row in rows:
        for eq in (row.get('state') or {}).get('equipped') or []:
            name = eq.get('equip')
            if name and name not in EQUIPMENT_ROSTER:
                out.append(
                    f"p{row.get('plane')}r{row.get('round_num')}: "
                    f"幻影装备被穿着: {name} → {eq.get('char')}"
                    f"(注册表外实体——批⑲ F2)")
    return out


def check_degrade_recover_mutex(rows: list[dict]) -> list[str]:
    """批⑯ F5(degrade_recover_mutex;条件违规;ADR-0289 清偿)。

    判据(设计表原文):降级事件后 N 轮内 _recover_line_from_board
    重锁原线 → 违规([31] 实现的前置守卫);基线 57% relapse。
    **前置依赖**:[31] 降级通道未实现(线库 degrade_to 存在但
    策略侧无降级动作)→ 当前树 target_comp 不应出现「弃线 →
    ≤3 轮内回锁原线」形态;条件违规口径 = 任意 A→B 切线后 ≤3
    轮内回锁 A(relapse 指纹)。降级落地后本检查语义自动升级
    (真降级事件的 relapse 同型命中);pivot 合法来回(>3 轮)
    不辖。
    """
    out: list[str] = []
    history: list[tuple[int, str]] = []   # (轮号, comp)
    for row in rows:
        if row.get('plane') != 1:
            continue
        comp = row.get('target_comp') or ''
        if not comp:
            continue
        rn = row.get('round_num') or 0
        if history and history[-1][1] == comp:
            history[-1] = (rn, comp)
            continue
        history.append((rn, comp))
    for i in range(1, len(history) - 1):
        r_a, a = history[i - 1]
        r_b, b = history[i]
        r_c, c = history[i + 1]
        if a == c and r_c - r_b <= 3:
            out.append(
                f"p1: 切线 {a}→{b}(r{r_b})后 ≤3 轮回锁 {a}(r{r_c})"
                f"(降级 relapse 指纹——批⑯ F5;[31] 未实现期涌现"
                f"即 pivot 摇摆)")
    return out


# 批量内嵌检查集(分布级;r371b 后冷启动门 sim 内可达,局49
# 检查升级进批量——真实 sim 批次自动扫)
def check_bench_full_deadlock_probe(rows: list[dict]) -> list[str]:
    """批⑩ F4 指纹(bench 满复合死锁常态检查;ADR-0276)。

    指纹:连续 ≥3 轮 零 BuyCard 且 bench 满(≥9)且 gold>20 且
    **deployed < cap**(上通道同时堵——围栏拦散牌,deploy 没满)——
    买通道(bench_is_full 门)与上通道(配方围栏)互锁,滞留金无
    出口(seed174 r3-r9 零买入仅刷新×2+LevelUp×11,末 HP 37;
    批⑩ F4 首个完整机制链样本)。deployed=cap 的末段停买(板满+
    攒金)是合法终局形态,不报——判据表原文的「bench=9 且零买入
    且金>20」在末段普遍成立(n=60 预跑 41/60 误报,deployed<cap
    才是 F4 的特异性维度)。

    3合1 merge 接入 sim 执行层(ADR-0276)后副本被消化、席位
    回流,本形态应消失;涌现即买/上通道回归。生产侧 merge 同在
    (simulate/mutate_bench_deployed 同源)——生产同型理论上可达,
    违规按真死锁处理,非 sim-only 形态。连续窗口用连续 3 个
    停滞轮(轮号相邻)判,孤立 2 轮(过渡态)不报。
    """
    out: list[str] = []
    _stall_rounds: list[int] = []
    for row in rows:
        if row.get('plane') != 1:
            continue
        st = row.get('state') or {}
        has_buy = any(a.get('__type__') == 'BuyCard'
                      for a in row.get('actions') or [])
        _dep_n = len(st.get('deployed') or [])
        if not has_buy \
                and len(st.get('bench') or []) >= 9 \
                and (row.get('gold') or 0) > 20 \
                and _dep_n < (st.get('cap') or 99):
            _stall_rounds.append(row.get('round_num') or 0)
    for a, b, c in zip(_stall_rounds, _stall_rounds[1:],
                       _stall_rounds[2:], strict=False):
        if b - a == 1 and c - b == 1:
            out.append(
                f"p1r{a}-r{c}: bench 满(≥9)连续 ≥3 轮零买入且金>20"
                f"(买/上通道互锁——批⑩ F4 死锁形态,ADR-0276)")
            break
    return out


def check_shop_slot_consumption(rows: list[dict]) -> list[str]:
    """批㉒ F1(ADR-0284):商店槽消费不变式——波内同名买入数 ≤
    该波同名供给槽位数。

    生产语义:槽买后消失(买走即下架)。旧 sim 买入不消费槽 →
    同槽幻影再买(批㉒ 账本实测 65.13% 买轮含槽再买、超量槽买
    3553 次/300 局、单槽最高 6 连买),3合1 被同槽重复点击无限
    兜底 → 成型类指标系统性偏乐观(批㉒ F3:trio3/engines2/
    formed_n 全部含幻影供给水分)。判据走账本波序列:
    RefreshShop 动作切波(动作序与波序同源——刷新后立即
    re-decide),波内逐笔 BuyCard 按名计数,超该波供给即违规
    (执行层忘消费槽 / 账本写坏)。被守卫跳过的买(bench 满/
    幻影槽)不入 actions,不影响本判据。
    """
    out: list[str] = []
    for row in rows:
        if row.get('plane') != 1:
            continue
        waves = (row.get('sim') or {}).get('shop_waves') or []
        if not waves:
            continue
        rn = row.get('round_num')

        def _supply(wave: dict) -> dict[str, int]:
            s: dict[str, int] = {}
            for c in wave.get('cards') or []:
                n = c.get('name')
                if n:
                    s[n] = s.get(n, 0) + 1
            return s

        supply = _supply(waves[0])
        bought: dict[str, int] = {}
        wi = 0
        for a in row.get('actions') or []:
            t = a.get('__type__')
            if t == 'RefreshShop':
                wi += 1
                if wi >= len(waves):
                    break
                supply = _supply(waves[wi])
                bought = {}
            elif t == 'BuyCard':
                n = (a.get('card') or {}).get('name')
                if not n:
                    continue
                bought[n] = bought.get(n, 0) + 1
                if bought[n] > supply.get(n, 0):
                    out.append(
                        f"p1r{rn}: {n} 波内买入 {bought[n]} 份 > "
                        f"供给 {supply.get(n, 0)} 槽(槽消费缺失"
                        f"/账本写坏——批㉒ F1,ADR-0284)")
    return out


def check_phantom_rebuy_disclosure(rows: list[dict]) -> list[str]:
    """批㉒ F1(ADR-0284):幻影再买披露归 0 锁。

    判据:执行层已消费槽/店外卡的买提案数(账本 sim.phantom_
    rebuys)应恒 0——真策略提案恒来自 st.shop 活槽;>0 = 策略
    对已买槽再提案(批㉒ F1 幻影通道回归)或店外构造混入真批次
    (仅测试桩合法)。批㉒ 设计为披露口径(buys − 波内供给槽
    上限),槽消费落地(ADR-0284)后升格归 0 锁:修复前 65.13%
    买轮含槽再买 → 修复后 0。
    """
    out: list[str] = []
    for row in rows:
        n = (row.get('sim') or {}).get('phantom_rebuys') or 0
        if n:
            out.append(
                f"p1r{row.get('round_num')}: 幻影再买提案 {n} 次"
                f"(已消费槽/店外——批㉒ F1 回归,ADR-0284)")
    return out


def check_deploy_after_buy_semantics(rows: list[dict]) -> list[str]:
    """批㉘ F1(ADR-0287):部署时序归 0 锁(买后部署语义)。

    判据:每轮账本 sim.deploy_lag_units(轮末重放围栏的残留可上
    件数)应恒 0——部署块已移到买/升级之后(生产序对齐),轮末
    围栏无件可上才是语义正确。>0 = 部署时序回归轮首序(重构再犯)
    或围栏漏上(批㉘ F1 观测口径的常态化拦截;基线 n=300 观测臂
    33.0% 轮存在「当轮可上未上」,修复后应归 0)。
    """
    out: list[str] = []
    for row in rows:
        n = (row.get('sim') or {}).get('deploy_lag_units')
        if n:
            out.append(
                f"p1r{row.get('round_num')}: 轮末残留可上件 {n}"
                f"(部署时序回归/围栏漏上——批㉘ F1,ADR-0287)")
    return out


def check_ledger_deploy_lag_disclosure(rows: list[dict]) -> list[str]:
    """批㉘ 检查项(ADR-0287):deploy_lag_units 披露字段在位锁。

    判据:每轮账本 sim 节必须含 deploy_lag_units 键(值可为 0)
    ——字段的**存在**是 deploy_after_buy_semantics 检查的数据
    地基;缺键 = 账本写入端断链(部署块重构时把披露丢了),检查
    静默失明比违规更危险。
    """
    out: list[str] = []
    for row in rows:
        if row.get('plane') != 1:
            continue
        if 'deploy_lag_units' not in (row.get('sim') or {}):
            out.append(
                f"p1r{row.get('round_num')}: 账本缺 deploy_lag_units"
                f"(披露断裂——批㉘ 检查项,ADR-0287)")
    return out


def check_hp_upper_bound_truth(rows: list[dict]) -> list[str]:
    """批㉘ F6(ADR-0287):HP 上界哨兵(hp>100 恒 0)。
    判据:任意轮 hp > HP_UPPER_BOUND(100)= 结算端上界钳制回归
    (cw_sim HP_UPPER_BOUND min 钳被移除)。游戏机制真值未见文档
    证据(语料 max 88 / sim max 92 均未触界,非 cap 证明)——暂
    cap 100;批㉗ reward 胖尾修复(+20~39 回血)落地后 hp 可破百,
    该修复与本哨兵联动(缺任一,hp_ge_60 换方向虚高)。实机满血
    样本核真后更新 cw_sim.HP_UPPER_BOUND 与本检查的同步镜像
    (检查模块不 import cw_sim,依赖方向纪律;值漂移由双向锁暴露)。
    """
    cap = 100   # 同步自 cw_sim.HP_UPPER_BOUND(单一源在 sim;镜像纪律)
    out: list[str] = []
    for row in rows:
        hp = row.get('hp')
        if hp is not None and hp > cap:
            out.append(
                f"p1r{row.get('round_num')}: hp={hp}>{cap}"
                f"(上界钳制回归/真值已改未同步——批㉘ F6,ADR-0287)")
    return out


def check_hp1_dead_end_candidate(rows: list[dict]) -> list[str]:
    """W120 P9(死局锚;run 监控侧标记):HP=1 ⟺ 0hp 保底已耗尽 ⟹
    下一败局即终局——**候选下界标记,非违规、非触发线**(violations
    恒 0;hp1_rounds 披露供早停判读:HP=1 局的继续局期望 = P(全胜)×
    通关价值 − 时间成本,板面/日程联合判在 cw_first_passage,本检查
    只提供锚)。早停裁决归编排者/哨兵,检查器不自动停局。
    (数据面走 hp1_dead_end_rounds,本函数保持 _BATCH_CHECKS 签名。)
    """
    return []   # 披露型:违规恒空


def hp1_dead_end_rounds(rows: list[dict]) -> list[int]:
    """check_hp1_dead_end_candidate 的数据面(批报告聚合读)。"""
    return [r.get('round_num') for r in rows
            if r.get('hp') is not None and r.get('hp') <= 1]



def check_hp_ge60_frame_lock(rows: list[dict]) -> list[str]:
    """批㉚ F1(锚帧位锁):sim 锚 hp_ge_60 的口径 = **r9 boss 结算后**
    的末行 hp(sim 结算先于账本 append,cw_sim L1153→L1207)。

    锁的语义:完整局(末行 round_num==9)末行 node 必须 == 'boss'
    ——若未来部署/结算/账本时序改动把末行变成 boss 前帧,锚值会
    静默漂移到「boss 前血量」口径,与实机对照时产生帧错位伪裂口
    (批㉚实证:prep 帧口径实机 26.1% vs 结算后口径 9.5%,同一批
    数据差 16.6pp)。生产对照必须用 outcomes hp_after(结算后帧)
    ——decisions 末行是备战帧、runs.jsonl final_hp 含接管段 100
    误读污染,两者都不可作 hp_ge_60 对照锚。
    """
    if not rows:
        return []
    last = rows[-1]
    if (last.get('round_num') or 0) == 9 \
            and (last.get('sim') or {}).get('node') != 'boss':
        return [
            f"完整局末行 node={(last.get('sim') or {}).get('node')}"
            f"≠boss:锚帧位漂移,hp_ge_60 不再是结算后口径(批㉚ F1)"]
    return []


def check_supply_pool_roster_purity(rows: list[dict]) -> list[str]:
    """批㉛ 检查项(ADR-0294 件2 回归锁):供给采样池注册表纯净性。

    判据:每轮账本 state.owned_equips / state.equipped 的装备名必须
    ⊆ EQUIPMENT_ROSTER(注册表单一源)——ADR-0294 件2 修复后,
    sim 供给采样池 = _EQUIP_VALUE ∩ EQUIPMENT_ROSTER,注册表外
    名(价值表死名/「未知装备」)不得再进 owned 池或被穿上。
    违规 = 采样池过滤被绕过/回退(phantom_equip 通道回归),或
    账本写入端混入未建模名(0 容忍)。
    """
    from sr_od.application.currency_war.cw_equipment_data import (
        EQUIPMENT_ROSTER,
    )
    out: list[str] = []
    for row in rows:
        st = row.get('state') or {}
        bad: set[str] = set()
        for e in (st.get('owned_equips') or []):
            if e not in EQUIPMENT_ROSTER:
                bad.add(e)
        for pair in (st.get('equipped') or []):
            if pair.get('equip') not in EQUIPMENT_ROSTER:
                bad.add(str(pair.get('equip')))
        if bad:
            out.append(
                f"p1r{row.get('round_num')}: 注册表外装备进池/上身 "
                f"{sorted(bad)}(供给采样池纯净性破——批㉛,ADR-0294 件2)")
    return out


def check_equip_value_table_roster_coherence(rows: list[dict]) -> list[str]:
    """批㉛ 检查项(数据层债披露,预期红灯):价值表键-注册表一致性。

    判据:_EQUIP_VALUE(cw_events,V4.4 先验)的每个键应存在于
    EQUIPMENT_ROSTER——注册表外键 = 死名(游戏已改名/先验陈旧),
    它们被 ADR-0294 件2 的采样过滤静默剔除出 sim 供给池(批㉛ 实测
    3/12 键、约 20% 表值质量),且 decide_supply 生产侧对真名供给
    恒打 0 分(价值表查不到)。本检查**不消费账本行**(逐局循环里
    每 game 重复披露一次,直至数据层清偿);清偿 = 修/删价值表死名
    (数据治理纪律:能修复就修复,不能就删),修后本检查归 0。
    批㉛ F2 登记:超级电池/能量饮料/翁瓦克 3 死名——**ADR-0298 已清偿**
    (语料核证为表残留:超级电池=超充站 buff 词/能量饮料=零出现/
    翁瓦克=局外遗器名误收;翁瓦克 4 分转投蓄能帆),本检查现应恒绿。
    """
    from sr_od.application.currency_war.cw_equipment_data import (
        EQUIPMENT_ROSTER,
    )
    from sr_od.application.currency_war.cw_events import _EQUIP_VALUE
    stale = sorted(n for n in _EQUIP_VALUE if n not in EQUIPMENT_ROSTER)
    if not stale:
        return []
    return [
        f"价值表死名 {stale}(不在 EQUIPMENT_ROSTER;"
        f"ADR-0294 件2 采样过滤静默剔除+生产侧恒 0 分——批㉛ F2 待清偿)"]


def check_equip_supply_wear_closure(rows: list[dict]) -> list[str]:
    """批㉜ 检查项(供给面-穿戴面耦合锁):非保留件获取后必须上过身。

    判据:本局经供给获取(owned∪equipped 首现口径)的装备名,凡不在
    cw_synthesis.RESERVED_COMPONENTS(P1 合成保留件,ADR-0265 有意
    不穿)者,局内必须至少上身一次——前提是本局有过部署(board 非空
    的轮行存在)。违规 = 价值面(decide_supply 给分选入)与穿戴面
    (equip_allocation 放置)脱钩:装备被高分选中却永远躺在 owned
    (批㉜ 锚 n=100 基线:非保留件获取/上身 1:1,0 违规;蓄能帆
    入池 12 局 12 上身)。
    """
    from sr_od.application.currency_war.cw_synthesis import (
        RESERVED_COMPONENTS,
    )
    acquired: set[str] = set()
    worn: set[str] = set()
    deployed_seen = False
    for row in rows:
        st = row.get('state') or {}
        for n in (st.get('owned_equips') or []):
            acquired.add(n)
        for pair in (st.get('equipped') or []):
            worn.add(pair.get('equip'))
        if st.get('board'):
            deployed_seen = True
    if not deployed_seen:
        return []
    stuck = sorted(n for n in acquired - worn
                   if n and n not in RESERVED_COMPONENTS)
    if not stuck:
        return []
    return [
        f"非保留件获取后整局未上身 {stuck}"
        f"(供给价值面与穿戴面脱钩——批㉜)"]


def check_equip_value_strategy_key_coverage(rows: list[dict]) -> list[str]:
    """批㉜ 检查项(策略域待裁决披露,预期红灯):价值表对策略层
    自声明关键装备的通用价值覆盖。

    判据:COMP_LIBRARY key_equips 被 ≥3 个阵容引用(策略层自声明
    「重要」)且在 EQUIPMENT_ROSTER 内的装备名,应存在于
    _EQUIP_VALUE——缺失 = 该装备在本阵容未锁线时(decide_supply 第 3
    分支,key_fit +10 不触发)通用价值恒 0 分,与策略层自己的重要性
    声明矛盾。批㉜ F4 实测缺口:光速螺旋桨(5 comps)/动能激发剑
    (3 comps)。本检查不消费账本行(逐局循环里每 game 披露一次);
    裁决归策略域(补值入表 / 显式裁决「通用价值确为 0」后按
    ADR-0298 同款语义处理),裁决前恒红。
    """
    from collections import Counter

    from sr_od.application.currency_war.cw_comps import COMP_LIBRARY
    from sr_od.application.currency_war.cw_equipment_data import (
        EQUIPMENT_ROSTER,
    )
    from sr_od.application.currency_war.cw_events import _EQUIP_VALUE
    kc: Counter[str] = Counter()
    for c in COMP_LIBRARY:
        for k in c.key_equips:
            kc[k] += 1
    gap = sorted((n, v) for n, v in kc.items()
                 if v >= 3 and n in EQUIPMENT_ROSTER
                 and n not in _EQUIP_VALUE)
    if not gap:
        return []
    return [
        f"策略层 key_equips ≥3 引用但价值表缺值 {gap}"
        f"(未锁线局通用价值恒 0——批㉜ F4 待策略域裁决)"]


_EXPLICIT_V2_ACTIONS = ('SellDeployed', 'SwapDeploy', 'CompTransaction')


def _board_agg_of_deployed_row(row: dict) -> dict[str, int]:
    """账本行的 deployed 羁绊全集聚合(动作 v2 一致性检查的本地口径)。

    ADR-0312(W50):口径与 ``cw_state._recount_board`` 同形 = **全集 +
    星徽装备贡献**——per-unit 标签经 ``cw_bond_equips.unit_bond_tags``
    (与 cw_state/cw_observation 三侧同一函数,非镜像复制;检查模块
    不 import cw_sim/cw_state 的依赖方向纪律不变,消费的是更底层的
    口径单一源模块)。值漂移由双向锁暴露,同 HP_UPPER_BOUND 镜像纪律。"""
    from types import SimpleNamespace

    from sr_od.application.currency_war.cw_bond_equips import unit_bond_tags
    agg: dict[str, int] = {}
    for d in (row.get('state') or {}).get('deployed') or []:
        ns = SimpleNamespace(
            char_id=d.get('char_id') or '',
            position_pref=d.get('position_pref') or 'back',
            faction=d.get('faction') or '',
            equips=d.get('equips') or [])
        tags = unit_bond_tags(ns)
        if tags:
            for t in tags:
                agg[t] = agg.get(t, 0) + 1
            continue
        f = d.get('faction')
        if f and f != '?':
            agg[f] = agg.get(f, 0) + 1
    return agg


def check_comp_tx_atomicity(rows: list[dict]) -> list[str]:
    """动作 v2(契约包 C1 验收3,步2):显式动作后的一致性/半档残留锁。

    判据:
    - 轮内含 **applied** 显式部署动作(SellDeployed/SwapDeploy/
      CompTransaction)时,该轮账本 state.board 必须与 deployed 名单的
      羁绊全集聚合一致(转移后 board 由 _recount_board 维护;不一致 =
      半档残留/board 派生断裂);
    - **rejected** 显式动作必须带非空 reject_reason(拒绝记录可见性
      ——冻结 invariant「拒绝记录进账本」的账本侧镜像)。
    """
    out: list[str] = []
    for row in rows:
        acts = row.get('actions') or []
        has_applied = any(
            a.get('__type__') in _EXPLICIT_V2_ACTIONS
            and a.get('result') == 'applied' for a in acts)
        if has_applied:
            board = dict((row.get('state') or {}).get('board') or {})
            agg = _board_agg_of_deployed_row(row)
            if agg != board:
                out.append(
                    f"p1r{row.get('round_num')}: 显式动作后 board 与 "
                    f"deployed 聚合不一致(board={board} agg={agg}"
                    f"——半档残留/派生断裂,契约包 C1)")
        for a in acts:
            if a.get('__type__') in _EXPLICIT_V2_ACTIONS \
                    and a.get('result') == 'rejected' \
                    and not a.get('reject_reason'):
                out.append(
                    f"p1r{row.get('round_num')}: 拒绝的显式动作缺 "
                    f"reject_reason(拒绝记录可见性,契约包 C1)")
    return out


def check_skip_fence_pairing(rows: list[dict]) -> list[str]:
    """动作 v2(契约包 C1 + 六矛盾裁决1,步2):围栏跳过可见性/同轮配对锁。

    判据(裁决1:显式>围栏,同轮互斥;围栏跳过必须记账本一行):
    - 轮内含 **applied** 显式部署动作(SellDeployed/SwapDeploy/
      CompTransaction)→ 该轮 actions 必须恰有一条 skip_fence 且
      reason 非空(缺 = 围栏静默跳过或叠加,双违规;多 = 误记);
    - **rejected** 显式动作**不**占显式通道(W65/ADR-0323:被拒不消耗
      围栏,同轮围栏照跑)→ 不要求配对;被拒轮若仍记 skip_fence = 误记;
    - skip_fence 存在但轮内无 applied 显式动作 = 误记(围栏没跳却记账)。
    """
    out: list[str] = []
    for row in rows:
        acts = row.get('actions') or []
        explicit = [a for a in acts
                    if a.get('__type__') in _EXPLICIT_V2_ACTIONS
                    and a.get('result') == 'applied']
        skips = [a for a in acts if a.get('__type__') == 'skip_fence']
        rn = row.get('round_num')
        if explicit and not skips:
            out.append(
                f"p1r{rn}: 显式部署动作未配对 skip_fence"
                f"(围栏静默跳过/叠加——六矛盾裁决1)")
        if skips and not explicit:
            out.append(
                f"p1r{rn}: skip_fence 无同轮显式动作(误记,裁决1)")
        if len(skips) > 1:
            out.append(f"p1r{rn}: 同轮多条 skip_fence(应恰一行)")
        for _s in skips:
            if not _s.get('reason'):
                out.append(f"p1r{rn}: skip_fence 缺 reason(裁决1)")
    return out


_BATCH_CHECKS = {
    'ledger_consistency': check_ledger_consistency,
    'coldstart_direction': check_coldstart_seed_squander,
    'deploy_fills_cap': check_deploy_fills_cap,
    'equip_worn_in_battle': check_equip_worn_in_battle,
    'no_component_equipped_p1': check_no_component_equipped_p1,
    'levelup_interest_engine_gate': check_levelup_interest_engine_gate,
    'no_same_round_buy_sell': check_no_same_round_buy_sell,
    'bench_full_deadlock_probe': check_bench_full_deadlock_probe,
    'shop_slot_consumption': check_shop_slot_consumption,
    'phantom_rebuy_disclosure': check_phantom_rebuy_disclosure,
    'deploy_after_buy_semantics': check_deploy_after_buy_semantics,
    'ledger_deploy_lag_disclosure': check_ledger_deploy_lag_disclosure,
    'hp_upper_bound_truth': check_hp_upper_bound_truth,
    # W120 P9:HP=1 死局/早停候选标记(披露型,violations 恒 0)
    'hp1_dead_end_candidate': check_hp1_dead_end_candidate,
    # --- ADR-0289 检查项清偿批(逐局违规锁) ---
    'gold_nonneg': check_gold_nonneg_invariant,
    'bench_capacity': check_bench_capacity_invariant,
    'deployed_schema_filter': check_deployed_schema_filter,
    'engine_seed_not_resold': check_engine_seed_not_resold,
    'overflow_gold_zero_buy_streak': check_overflow_gold_zero_buy_streak,
    'buys_at_full_bench': check_buys_at_full_bench,
    'oscillation_xp_cap': check_oscillation_xp_cap,
    'levelup_flat4_lock': check_levelup_flat4_ledger_lock,
    'phantom_equip_no_wear': check_phantom_equip_no_wear,
    'degrade_recover_mutex': check_degrade_recover_mutex,
    'hp_ge60_frame_lock': check_hp_ge60_frame_lock,
    'supply_pool_roster_purity': check_supply_pool_roster_purity,
    'equip_value_table_roster_coherence':
        check_equip_value_table_roster_coherence,
    'equip_supply_wear_closure': check_equip_supply_wear_closure,
    'equip_value_strategy_key_coverage':
        check_equip_value_strategy_key_coverage,
    # --- 动作 v2(契约包 C1,步2):显式动作一致性/围栏配对 ---
    'comp_tx_atomicity': check_comp_tx_atomicity,
    'skip_fence_pairing': check_skip_fence_pairing,
}




# --- Δ池标定检查(压测批③ F1 检查项 1/2/3;ADR-0268) ---------------
# 前两条吃池 dict(simulate_p1_batch 有 resolve_pool 产物;纯 dict
# 入参,不 import cw_sim);第三条吃两臂账本(A/B 对照调用方使用,
# 不进 _BATCH_CHECKS——单臂批次无对照对象)。
_POOL_BUCKET_MIN_N = 5       # 同 cw_sim._BUCKET_MIN_N(值同步维护)
_POOL_DEPTH_BUCKET_W = 3     # 同 cw_sim._DEPTH_BUCKET_W(值同步维护)

# W109(ADR-0344):池新鲜度滞后红线——runs.jsonl 里晚于池内最新 run
# 的行数 ≥ 此值 = 再生管线断。2 = 1 局容忍(再生挂局终后、下一局
# 未结束前 lag=1 是管线健康瞬态)+1 局缓冲;>2 只能是钩子/手工链
# 断了(2026-08-25 事故:池停 41 局 12 小时零报警)。
POOL_FRESHNESS_LAG_LIMIT = 2


def check_pool_freshness(replay_dir=None, *,
                         lag_limit: int = POOL_FRESHNESS_LAG_LIMIT) -> dict:
    """W109(ADR-0344):Δ池快照新鲜度——再生管线断裂的常设报警。

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

    from sr_od.application.currency_war import cw_delta_pool_data as _dpd
    if replay_dir is None:
        from sr_od.application.currency_war.cw_delta_pool_gen import (
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
        if nt == 'battle':   # rung 键,深度单调语义不辖(ADR-0279)
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

# 批⑬ F2 真值表(battle rung 桶均值;全量 replay 分桶实测,
# r0 n=26 / r1 n=24 双主桶)。r2 方差未判(时代分层混杂)/r3 无
# 样本——真值表只锁双主桶;池重生成后均值漂移 >3hp 报警
# (判据表原值)。
BATTLE_RUNG_TRUTH: dict[int, float] = {0: -11.5, 1: -6.3}
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
    - battle rung 桶真值表(r0 -11.5/r1 -6.3)锁进池——rung0/rung1
      双主桶存在且 n≥10,均值距真值漂移 ≤3hp;
    - battle 桶键全落 rung 域(0-4)——出现 depth 域键(≥6)= rung
      分桶未生效(快照未重生成/生成器回归);
    - encounter 未分桶边界声明:encounter 非空时桶键应含 depth 域
      (≥6)键(批⑬ F1:encounter rung 样本不足暂沿用 depth 分桶,
      全落 rung 域 = 边界声明被破坏);
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
    if enc and all(int(b) <= 4 for b in enc):
        out.append('encounter 桶键全落 rung 域(≤4)——批⑬ F1 边界'
                   '声明被破坏(encounter 样本不足暂 depth 分桶)')
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
    """批㉗ 检查项 reward_delta_pool_bucket_lock(ADR-0292;W111 判据修正
    见 ADR-0345)。

    判据(规格原文「分布入池且均值≈语料真值」):
    - reward 池非空且 n≥30(分布**入池**:结算采样源是语料经验
      分布而非 EARLY_WIN_DELTA 常数);
    - reward 全样本均值距语料真值(+2.0)漂移 ≤1hp;
    - reward 跨 run 配对伪影哨兵:max |Δ| ≤ 20 且无负值——批㉗ F4 的
      +27~+61/−2 形态若在重生成后涌现,先查生成器 run 分组/语料
      接管段,不当作真值入锚;
    - supply **无真值锚**(W111/ADR-0345):批㉗ 落地时语料 supply 零
      样本,「非空时同判 reward」是外推假设;W109 再生后语料首现
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


# 四体系口径(同步自 cw_sim._engines_count/_TRANSITION_TRAITS——检查
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


#: boss 恒败回归判定的 n 地板(ADR-0308):W31 阶梯 boss 胜率
#: ~0.05,小于此轮数的 0 胜是抽样噪声(0.95^n),不判回归。
_BOSS_WIN_MIN_ROUNDS: int = 100


def check_boss_win_calibration(ledgers: list[list[dict]]) -> dict:
    """批⑪ F1 验收(boss 胜率校准;ADR-0277 → ADR-0308 修订)。

    - 胜 = boss 轮 sim.delta ≥ 0(outcomes.killed 同极性);
    - 违规 ①:boss 轮 ≥ ``_BOSS_WIN_MIN_ROUNDS`` 且 0 胜(结构性
      恒败回归——胜分支失效)。n 地板 = ADR-0308 修订:回退层
      胜负面换 W31 阶梯后 boss 实测胜率仅 ~0.05,小批(如 smoke
      n=25)全负是**抽样噪声不是回归**(0.95^25≈28%)——原「存在
      即判」判据在该量级下恒假红;n≥100 时 0 胜概率 <1%,恢复
      判定力;
    - 旧违规 ②(胜率随深度单调)已删(ADR-0308):W31 阶梯的
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
    W50 v7 采样键换 Σboard 后 13/12 侧再假红 −4.11,同批 n=300
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


# 实机末金均值(批⑧ F1,18 局;批⑩ F5 对照侧:sim 52.5 vs 实机
# 24.3 = 2.2× 虚高)。merge 落地(ADR-0276)后此比值应为收敛判据。
REAL_AVG_ENDGOLD: float = 24.3
ENDGOLD_RATIO_MAX: float = 1.5   # 收敛阈值(仍 >1.5 = 滞留金虚高未收敛)


def check_sim_endgold_calib(ledgers: list[list[dict]]) -> dict:
    """批⑨ 设计/批⑩ 追加数据(末金校准;ADR-0276/0285)。

    判据:sim 末轮金均值 vs 实机 24.3 的比值——3合1 建模落地后
    重测此比值为收敛判据(批⑩ F5:sim 52.5 = 2.2×,「sim 虚高
    1.6-2.3×」形态)。违规 = 比值 > 1.5(买通道死锁/滞留金虚高
    未恢复判读力)。

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
    import math
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
    import math
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
# 旧锚(886f8a39,ADR-0306 批)已失效:ADR-0308(W37,W31 节点×
# 轮次胜率阶梯进回退层)_SAMPLER_VERSION 5→6——回退层胜负面换
# 实测边际(旧策略病局语料):hp 类指标**下移属预期**(boss 回退
# 胜率 rung2 0.25/rung≥3 0.667 → 0.05;battle 回退 ~0.29;此前
# rung 外推本身是跨节点拍脑袋外推,高估);策略侧指标零漂移
# (engines2/recipe5/refreshes 逐位持平 = 只有结算校准变了,
# 决策行为面没动)。
# 旧锚(fd48f135,ADR-0308 批)已失效:ADR-0312(W50 口径统一)
# _SAMPLER_VERSION 6→7——sim 侧 board 全集口径(_recount_board)+采样键
# Σboard(池语料同口径,旧 min(level,len(deployed)) 与池语料不同口径,
# 采样系统性偏浅,W49 Q4)。**校准口径修正非策略变化**:hp 类下移属
# 预期(同局面落更深的 encounter/boss 桶 → 更真实的战损);策略侧
# 基本零漂移(engines2/recipe5 与 v6 锚逐位持平);哨兵大样本仍绿
# (n=300 diff +5.39 vs v6 批 +5.33)。遗留:n=300 涌现边缘违规
# engine_seed_not_resold(1/300,g188)/carry_on_shelf_responded
# (2/300,g243/296)——行为面随口径变化的涌现信号,待 leader 对拍
# 裁决(W50 报告 §遗留)。
ANCHOR_REGISTRY_N300: dict = {
    'pool_fingerprint_prefix': '46066bbe90647c02',
    'recorded': '2026-08-25(ADR-0334 W73:语料扩容重生成,池内容变'
                '指纹重算,n=300,seed 0-299;W72 在飞树——合流后'
                '若策略面漂移按 drift 披露处置)',
    'metrics': {
        'engines2_by_r6': 0.33,       # 旧 0.38(ADR-0312 6c0c8397 锚)
        'avg_final_hp': 28.69,        # 旧 27.97(hp 上移=池扩容含今夜'
                                      # 部分更优战斗样本,校准修正)
        'hp_ge_60': 0.08,             # 旧 0.05(同上)
        'battle_losses_le_2': 0.11,   # 旧 0.11
        'recipe5_by_r6': 0.67,        # 旧 0.72(策略面微漂,同 W72 在飞)
        'avg_refreshes': 2.36,        # 旧 2.31
    },
}


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


def run_checks_on_ledgers(ledgers: list[list[dict]]) -> dict[str, dict]:
    """批量执行 generic 检查 → {检查名: {violations: n, games: [idx...]}}。

    违规局数与前 5 个局索引(供 seed 重放定位:simulate_p1(
    seed_base+idx) 重放该局)。
    """
    report: dict[str, dict] = {}
    for name, fn in _BATCH_CHECKS.items():
        games: list[int] = []
        for idx, rows in enumerate(ledgers):
            if fn(rows):
                games.append(idx)
        report[name] = {
            'violations': len(games),
            'games': games[:5],
        }
    return report


# =====================================================================
# --- ADR-0289 检查项清偿批:批级聚合 / 条件披露 / 语料级 / 锚登记 ---
# 批级入口 = run_batch_level_checks(ledgers, report, pool_map);
# cw_sim.simulate_p1_batch 的接线随 worker X 合流后并入(冲突隔离:
# 本批不碰 cw_sim.py)。全部为披露型/哨兵型(violations 语义见
# 各 docstring),新发现红条目按 ADR-0289「新发现待裁」清单流转。
# =====================================================================


def _combat_streak_by_round(rows: list[dict]) -> dict[int, int]:
    """重算逐轮「进轮时连胜数」(批⑫ streak_break_interest_fires /
    成型批 no_streak_buy_freeze 的决策侧连胜口径)。

    近似声明:sim 结算写 session.last_streak(cw_sim 批⑤ F4 段)
    但**不进账本**——本重放按战斗类轮(battle/encounter/boss)
    delta≥0=胜 累积连胜;奖励/补给轮不动 streak(生产 streak
    只在战斗结算变)。与 session.last_streak 的差 = 重放口径
    边界,方向披露不裁。
    """
    streak = 0
    out: dict[int, int] = {}
    for row in rows:
        out[row.get('round_num') or 0] = streak
        s = row.get('sim') or {}
        if s.get('node') in ('battle', 'encounter', 'boss'):
            streak = streak + 1 if (s.get('delta') or 0) >= 0 else 0
    return out


def check_late_deploy_full(ledgers: list[list[dict]]) -> dict:
    """成型批 late_deploy_full(末段部署欠员观测;披露型)。

    判据(设计表原文):r7+ 每轮 deployed==cap 或 bench 无 ≥2
    同阵营 → 现状(设计时)159 欠员实例/59 局,先建观测。披露
    计数(违规语义待观测分布定型后再裁——设计表原文「先建观测」)。
    """
    short = tot = 0
    for rows in ledgers:
        for row in rows:
            if (row.get('round_num') or 0) < 7:
                continue
            st = row.get('state') or {}
            dep_n = len(st.get('deployed') or [])
            if dep_n >= (st.get('cap') or 99):
                continue
            tot += 1
            facs: dict[str, int] = {}
            for b in st.get('bench') or []:
                f = b.get('faction')
                if f:
                    facs[f] = facs.get(f, 0) + 1
            if not any(v >= 2 for v in facs.values()):
                continue   # bench 无 ≥2 同阵营 = 合法形态
            short += 1
    return {'violations': 0, 'late_rounds': tot, 'short_instances': short}


def check_no_streak_buy_freeze(ledgers: list[list[dict]]) -> dict:
    """成型批 no_streak_buy_freeze(连胜期买入冻结观测;披露型)。

    判据(设计表原文):连胜≥5 的决策轮 buys 金 >0(或板面投资
    >0)——现状(设计时)0.11/轮,先观测后定阈。连胜口径 =
    _combat_streak_by_round 重放(批⑤ F4:session.last_streak 不
    进账本,重放近似,边界见该函数)。
    """
    hot = frozen = 0
    for rows in ledgers:
        streaks = _combat_streak_by_round(rows)
        for row in rows:
            if streaks.get(row.get('round_num') or 0, 0) < 5:
                continue
            hot += 1
            buys = ((row.get('sim') or {}).get('spend') or {}) \
                .get('buys') or {}
            if not sum(buys.values()):
                frozen += 1
    return {'violations': 0, 'streak5_rounds': hot,
            'zero_buy_rounds': frozen,
            'freeze_share': round(frozen / hot, 3) if hot else None}


def check_hoard_gold_no_engine(ledgers: list[list[dict]]) -> dict:
    """成型批 hoard_gold_no_engine(r6 囤金无引擎观测;披露型)。

    判据(设计表原文):r6 结束金≥40 且 engines<2 → 报观测项
    (与 levelup_interest_engine_gate 联动)——现状(设计时)
    48/60。engines 口径 = _rung_of_row 四体系数(同步镜像)。
    """
    n = tot = 0
    for rows in ledgers:
        for row in rows:
            if (row.get('round_num') or 0) != 6:
                continue
            tot += 1
            if (row.get('gold') or 0) >= 40 \
                    and _rung_of_row(row) < 2:
                n += 1
    return {'violations': 0, 'r6_rounds': tot, 'hoard_no_engine': n}


def check_second_engine_deadline(ledgers: list[list[dict]]) -> dict:
    """成型批 second_engine_deadline(次引擎期限观测;披露型)。

    判据(设计表原文):首引擎后 ≤3 轮内达次引擎或记原因——
    现状(设计时)gap=8 存在(2/11)。sim 账本无原因字段 →
    披露 gap 分布(engines 口径=_rung_of_row;「引擎」=四体系
    数≥1/≥2 的首达轮)。
    """
    gaps: list[int] = []
    for rows in ledgers:
        first = second = None
        for row in rows:
            r = _rung_of_row(row)
            rn = row.get('round_num') or 0
            if first is None and r >= 1:
                first = rn
            if first is not None and second is None and r >= 2:
                second = rn
                break
        if first is not None:
            gaps.append((second - first) if second is not None else 99)
    miss = sum(1 for g in gaps if g > 3)
    return {'violations': 0, 'first_engine_games': len(gaps),
            'deadline_miss': miss,
            'avg_gap': round(sum(gaps) / len(gaps), 2) if gaps else None}


def check_endgold_residue_channel_probe(ledgers: list[list[dict]]) -> dict:
    """批⑫ endgold_residue_channel_probe(末段零买入轮分流归因;披露)。

    判据(设计表原文):末段零买入轮(r≥7、无 BuyCard、金≥10)
    分流归因:bench 满 / 无可负担牌 / 有牌有位不买(围栏)——
    本批(设计时)基线 739:0:2。判读:卖出/囤件侧策略改动后
    bench 满占比下降且末金比值向 1.5 收敛。
    """
    ch = {'bench_full': 0, 'no_affordable': 0, 'has_card_room_no_buy': 0}
    for rows in ledgers:
        for row in rows:
            if (row.get('round_num') or 0) < 7 \
                    or (row.get('gold') or 0) < 10:
                continue
            if any(a.get('__type__') == 'BuyCard'
                   for a in row.get('actions') or []):
                continue
            st = row.get('state') or {}
            if len(st.get('bench') or []) >= 9:
                ch['bench_full'] += 1
                continue
            affordable = any(
                (w.get('gold') or 0) >= (c.get('cost') or 99)
                for w in (row.get('sim') or {}).get('shop_waves') or []
                for c in w.get('cards') or [])
            if affordable:
                ch['has_card_room_no_buy'] += 1
            else:
                ch['no_affordable'] += 1
    return {'violations': 0, **ch}


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


def check_formation_gradient_sentinel(ledgers: list[list[dict]]) -> dict:
    """批⑫ formation_gradient_sentinel(rung0 vs rung1 hp 梯度;哨兵)。

    判据(设计表原文):rung0 vs rung1 段 final_hp 差(设计时
    +0.2≈0);战斗 Δ 池按成型分桶拟合落地后应转正,否则耦合仍
    只有 boss 门槛。小批护栏同 ADR-0286(任一侧 <5 局只披露)。
    """
    r0: list[int] = []
    r1: list[int] = []
    for rows in ledgers:
        if not rows:
            continue
        hp = rows[-1].get('hp')
        if hp is None:
            continue
        (r1 if any(_rung_of_row(r) >= 1 for r in rows) else r0) \
            .append(int(hp))
    diff = (sum(r1) / len(r1) - sum(r0) / len(r0)) \
        if r0 and r1 else None
    small_n = r0 and r1 and min(len(r0), len(r1)) < 5
    violations = 1 if (diff is not None and diff <= 0
                       and not small_n) else 0
    out = {'violations': violations, 'rung0_n': len(r0),
           'rung1_n': len(r1),
           'rung0_hp': round(sum(r0) / len(r0), 2) if r0 else None,
           'rung1_hp': round(sum(r1) / len(r1), 2) if r1 else None,
           'diff': round(diff, 2) if diff is not None else None}
    if small_n:
        out['note'] = '样本不足(<5/侧)只披露不判定'
    return out


def check_streak_break_interest_fires(ledgers: list[list[dict]]) -> dict:
    """批⑫ streak_break_interest_fires(破息门行为观测;条件披露)。

    判据(设计表原文):连胜≥2 当轮的买入/破息动作计数进账本
    (或遥测字段),验证 last_streak 接线的行为效果——设计时仅
    日志可见、账本无字段。**依赖标注**:账本无 last_streak 字段
    → 用 _combat_streak_by_round 重放(边界:与 session 真值可能
    差奖励轮口径);依赖在(未来接线 sim.last_streak)则本检查
    自动切真值口径(优先读字段,缺则重放)。
    """
    hot = acted = 0
    streak_source = 'replay'
    for rows in ledgers:
        streaks: dict[int, int] | None = None
        for row in rows:
            s = row.get('sim') or {}
            if streaks is None:
                if isinstance(s.get('last_streak'), dict):
                    streaks = s['last_streak']
                    streak_source = 'ledger'
                else:
                    streaks = _combat_streak_by_round(rows)
            if streaks.get(row.get('round_num') or 0, 0) < 2:
                continue
            hot += 1
            spend = (s.get('spend') or {})
            if sum((spend.get('buys') or {}).values()) \
                    or spend.get('levelup') or spend.get('refresh'):
                acted += 1
    return {'violations': 0, 'streak2_rounds': hot,
            'acted_rounds': acted,
            'act_share': round(acted / hot, 3) if hot else None,
            'streak_source': streak_source}


def check_encounter_rung_sample_budget(pool_map: dict) -> dict:
    """批⑬ encounter_rung_sample_budget(encounter rung 样本预算;条件)。

    判据(设计表原文):encounter rung 桶 n 追踪(r1=9 距 10 仅
    差 1;设计时 4/9/2/0);达标(rung 各桶 n≥10)即并入 battle
    同法分桶。**依赖标注**:encounter 仍 depth 分桶(批⑬ F1
    边界声明)→ 桶键全落 depth 域(≥6)时披露「rung 分桶未
    启用」,不判违规;桶键落 rung 域(≤4)时逐桶披露 n。
    """
    enc = pool_map.get('encounter') or {}
    if not enc:
        return {'violations': 0, 'note': 'encounter 池空不辖'}
    rung_like = {int(b): len(v) for b, v in enc.items() if int(b) <= 4}
    if not rung_like:
        return {'violations': 0,
                'note': 'encounter 仍 depth 分桶(批⑬ 边界声明),'
                        'rung 预算追踪不辖;桶键域 '
                        f'{sorted(int(b) for b in enc)[:6]}'}
    ready = all(n >= 10 for n in rung_like.values())
    return {'violations': 0, 'rung_buckets': rung_like,
            'all_ge_10': ready,
            'note': '达标可并入 battle 同法分桶(批⑬ 设计)'}


def check_mc_faction_calib(ledgers: list[list[dict]]) -> dict:
    """批⑭ d_mc_faction_calib(发牌阵营分布校准;披露型)。

    判据(设计表原文):`_sample_shop` 阵营分布改为按 CHARACTERS
    档内构成采样;judgment = MC 目标阵营单格命中概率/档内真实
    密度 ∈ 1.0±0.1(设计时基线 0.40-0.85×,MC 低估)。**前置
    依赖**:cw_sim 采样器修复未落地(worker X 辖区)→ 本检查
    先披露 sim 批次全波卡池的阵营经验分布 vs 注册表期望密度
    (按经验费用构成加权)的逐阵营比值;修复落地后升格判据带
    (比值出 0.9-1.1 即违规)。
    """
    from collections import Counter

    from sr_od.application.currency_war.cw_chars import CHARACTERS
    obs = Counter()
    cost_mix = Counter()
    draws = 0
    for rows in ledgers:
        for row in rows:
            for w in (row.get('sim') or {}).get('shop_waves') or []:
                for c in w.get('cards') or []:
                    f = c.get('faction')
                    if f:
                        obs[f] += 1
                        cost_mix[c.get('cost') or 0] += 1
                    draws += 1
    if not draws:
        return {'violations': 0, 'note': '无波数据不辖'}
    total_cost = sum(cost_mix.values())
    exp: dict[str, float] = {}
    norm = 0.0
    for _n, ch in CHARACTERS.items():
        if ch.factions:
            f = ch.factions[0]
            w = cost_mix.get(ch.cost, 0) / (total_cost or 1)
            exp[f] = exp.get(f, 0.0) + w
            norm += w
    if norm > 0:
        exp = {f: v / norm for f, v in exp.items()}
    ratios = {f: round(obs[f] / (exp[f] * draws), 2)
              for f in sorted(exp) if exp[f] > 0.01 and obs.get(f)}
    out_of_band = [f for f, r in ratios.items()
                   if not 0.9 <= r <= 1.1]
    return {'violations': 0,   # 披露:采样器修复落地前不判
            'draws': draws, 'ratios': ratios,
            'out_of_band': out_of_band,
            'note': '前置=_sample_shop 修复(批⑭ F1);落地后'
                    'out_of_band 非空即违规'}




def check_streak_combat_only_income(ledgers: list[list[dict]]) -> dict:
    """W129 streak_combat_only_income(连胜金仅战斗轮口径;已裁决,断言化)。

    口径裁决(2026-08-26,run13/run15 实机;ADR-0351):奖励/补给节点
    既不计连胜数也不发连胜金(结算屏无 streak 分量);战斗/遭遇/boss
    轮胜后计数+发金不变(counter0 照发 table[0]=1,run15 r3=5+3+1)。
    sim 发金已按此口径修正(cw_sim 收入段)→ 本检查从「双口径并列
    披露」收紧为断言:**奖励/补给轮 income.streak != 0 即违规**;
    combat-only 重算和并列保留为披露面(对拍 sim 计数侧与重放口径
    的残差,>0=奖励轮计数侧回归)。

    W133 缺键守卫:账本行 schema 演化(如 node→node_type)时裸
    `.get()` 静默读 None → 奖励轮永远走不进断言分支 → violations
    恒 0、全量仍绿(断言永久失明)。生产账本(cw_sim L1570 起)
    每行必带 sim.node 与 sim.income.streak → 缺任一键 = 数据异常,
    计入 violations 并经 missing_key_rows 披露,不静默绿(锁:
    test_cw_sim_checks_streak_income)。
    """
    from sr_od.application.currency_war.cw_economy import streak_gold
    violations = ledger_sum = combat_sum = 0
    missing_key_rows = 0
    for rows in ledgers:
        streaks = _combat_streak_by_round(rows)
        for row in rows:
            sim = row.get('sim')
            inc = sim.get('income') if isinstance(sim, dict) else None
            if (not isinstance(sim, dict) or 'node' not in sim
                    or not isinstance(inc, dict) or 'streak' not in inc):
                missing_key_rows += 1   # schema 异常:计入违规,不静默跳过
                continue
            node = sim['node']
            inc_streak = inc['streak'] or 0
            ledger_sum += inc_streak
            if node in ('reward', 'supply'):
                if inc_streak != 0:
                    violations += 1
                continue   # 战斗口径连胜金不含奖励/补给轮(裁决口径)
            combat_sum += streak_gold(
                streaks.get(row.get('round_num') or 0, 0))
    return {'violations': violations + missing_key_rows,
            'ledger_streak_income': ledger_sum,
            'combat_only_streak_income': combat_sum,
            'delta': combat_sum - ledger_sum,
            'missing_key_rows': missing_key_rows}


def check_shop_distinct_names_invariant(ledgers: list[list[dict]]) -> dict:
    """批⑱ F4 shop_distinct_names_invariant(同波名字唯一性;披露)。

    判据(设计表原文):同波 cards 名字唯一性断言——真值裁决
    「允许/禁止」后启用其一(禁→违规;允→删除本检查)。**悬置
    待 F4 裁决** → 披露计数(重复名波数),violations 恒 0;
    裁决后按裁决侧切换。
    """
    dup_waves = tot = 0
    for rows in ledgers:
        for row in rows:
            for w in (row.get('sim') or {}).get('shop_waves') or []:
                names = [c.get('name') for c in w.get('cards') or []
                         if c.get('name')]
                tot += 1
                if len(names) != len(set(names)):
                    dup_waves += 1
    return {'violations': 0, 'waves': tot, 'dup_name_waves': dup_waves,
            'note': '悬置待批⑱ F4 真值裁决(允许/禁止)'}


def check_supply_agent_semantics(ledgers: list[list[dict]]) -> dict:
    """批⑲ supply_agent_semantics(supply 子账本披露;条件披露)。

    判据(设计表原文):supply 事件披露 pick_reason / refresh 分支
    是否真执行 / char 通道缺失标记(sim.supply 子账本)。**依赖
    标注**:sim.supply 子账本未接线(cw_sim 侧,worker X)→
    字段在则披露计数,不在则披露跳过(依赖断裂不静默)。
    """
    with_supply = 0
    for rows in ledgers:
        if any('supply' in (row.get('sim') or {}) for row in rows):
            with_supply += 1
    if with_supply:
        return {'violations': 0, 'games_with_supply_ledger': with_supply,
                'note': 'sim.supply 子账本在位,细节披露随接线补'}
    return {'violations': 0, 'games_with_supply_ledger': 0,
            'note': '依赖未接线:sim.supply 子账本(cw_sim 侧)'
                    '——披露跳过,不判'}


def check_refresh_cost_channel(ledgers: list[list[dict]]) -> dict:
    """批⑲ refresh_cost_channel(刷新成本通道;披露型)。

    判据(设计表原文):sim 按真值分布(或至少显式披露「恒 2
    假设」)更新 shop_refresh_cost;0/3/5 语义先由实机/数据裁决。
    **悬置待语义裁决** → 披露账本观测到的刷新成本取值集(期望
    {2}=恒 2 假设在用;出现 0/3/5 = 真值分布已接,届时随裁决
    判读)。
    """
    costs: set[int] = set()
    n = 0
    for rows in ledgers:
        for row in rows:
            for a in row.get('actions') or []:
                if a.get('__type__') == 'RefreshShop':
                    n += 1
                    c = a.get('cost')
                    if c is not None:
                        costs.add(int(c))
    return {'violations': 0, 'refreshes': n,
            'observed_costs': sorted(costs),
            'note': '恒 2 假设在用' if costs == {2} else
                    '成本取值偏离恒 2——真值分布可能已接,随批⑲ '
                    'F4 裁决判读'}


def check_hp_readable_disclosure(ledgers: list[list[dict]]) -> dict:
    """批⑳ sim_hp_readable_disclosure(hp_readable 字段;条件披露)。

    判据(设计表原文):sim 账本行补 `hp_readable: true`(或文档
    声明 sim 侧隐含完美观测,免跨侧 join 误读 absent)。**依赖
    标注**:字段未接线(cw_sim 侧)→ 本检查即「文档声明」载体:
    sim 侧 hp 隐含完美观测(结算真值,无 OCR 读失败),跨侧
    join 时 absent ≠ 读失败;字段接线后本检查转计数披露。
    """
    with_field = sum(
        1 for rows in ledgers for row in rows
        if 'hp_readable' in (row.get('sim') or {}))
    return {'violations': 0, 'rows_with_field': with_field,
            'note': 'sim 侧 hp 隐含完美观测(结算真值);'
                    'hp_readable 接线前以此声明为准(批⑳ F4)'}


def check_briefing_pipeline_liveness(ledgers: list[list[dict]]) -> dict:
    """批㉓ briefing_pipeline_liveness(简报管线活跃度;条件披露)。

    判据(设计表原文):line_v2/decision_v2 栈批结果披露「comp_score 系调用
    次数」(设计时恒 0=简报管线休眠标);策略栈切换时本披露自动
    翻转语义,防「管线复活没人知道」。**依赖标注**:comp_score
    计数未进账本(cw_sim 侧)→ 字段在则披露,不在则披露休眠标
    (依赖断裂不静默)。
    """
    calls = sum(
        (row.get('sim') or {}).get('comp_score_calls', 0)
        for rows in ledgers for row in rows
        if isinstance((row.get('sim') or {})
                      .get('comp_score_calls'), int))
    has_field = any('comp_score_calls' in (row.get('sim') or {})
                    for rows in ledgers for row in rows)
    return {'violations': 0,
            'comp_score_calls': calls,
            'note': ('计数披露(管线活跃度)'
                     if has_field else
                     '依赖未接线:comp_score_calls 不在账本——'
                     '按批㉓ F1 计数包装口径,当前树恒 0'
                     '(简报管线休眠标)')}


def check_deploy_cap_reader_noise(ledgers: list[list[dict]]) -> dict:
    """批㉔ deploy_cap_reader_noise(cap<level 冲突族;条件披露)。

    判据(设计表原文):cap<level 冲突族治理:diff≥2 判读错
    (diff=1 留「诅咒」空档)、复现阈值实化;读链守卫(与 level
    交叉)。生产侧为读链质量门;sim 账本侧披露 cap<level 行计数
    (sim cap=max_units() 与 level 同源,理论恒 0;>0 = cap 写入
    通道回归/宝钻通道接线后的语义变化,先披露后裁)。
    """
    n = tot = 0
    for rows in ledgers:
        for row in rows:
            st = row.get('state') or {}
            cap, level = st.get('cap'), st.get('level')
            if cap is None or level is None:
                continue
            tot += 1
            if cap < level:
                n += 1
    return {'violations': 0, 'rows': tot, 'cap_lt_level': n,
            'note': 'sim 侧理论恒 0;>0 = cap 写入通道变化,'
                    '批㉔ F5 读链守卫侧另辖'}


def check_calibration_dead_knob_disclosure(report: dict | None) -> dict:
    """批㉗ calibration_dead_knob_disclosure(死旋钮绕过标;披露)。

    判据(设计表原文):死旋钮族(WIN/LOSS/ENCOUNTER_MULT/
    NODE_TYPE_POOL)在 snapshot 批报告打「被 Δ 池绕过」标,防
    误读(F5:死旋钮改动不改 snapshot 行为)。**依赖标注**:
    report 标记键由 cw_sim 接线(worker X)→ 无 report / 无标记
    时披露提醒(判读 snapshot 批勿读死旋钮),不判违规。
    """
    if report is None:
        return {'violations': 0,
                'note': '无报告对象;判读提醒:snapshot 口径下 '
                        'WIN/LOSS/ENCOUNTER_MULT/NODE_TYPE_POOL 被 '
                        'Δ 池绕过(批㉗ F1/F5)'}
    if report.get('dead_knob_bypassed'):
        return {'violations': 0, 'marked': True}
    return {'violations': 0, 'marked': False,
            'note': '报告缺「被 Δ 池绕过」标(cw_sim 接线待合流);'
                    '判读 snapshot 批勿读死旋钮'}


def check_reward_heal_fat_tail(ledgers: list[list[dict]]) -> dict:
    """批㉗ reward_heal_fat_tail(奖励胖尾生效哨兵;披露型)。

    判据(设计表原文):奖励/补给轮结算由恒 +2 改经验分布采样
    (语料 41 样本 F4 分布;至少加「17% 概率 +20~39」混合);A/B
    预测 avg_final_hp +15~25——**上移量即裂口归因份额,改前先
    留基线**。**前置依赖**:sim 结算改造未落地(cw_sim,worker
    X)→ 本哨兵披露 reward/supply 轮 Δ 分布:全 ≤2 = 胖尾未落
    地(基线态);出现 >5 = 已落地(与 hp_upper_bound_truth
    联动,ADR-0287)。
    """
    deltas: list[int] = []
    for rows in ledgers:
        for row in rows:
            s = row.get('sim') or {}
            if s.get('node') in ('reward', 'supply') \
                    and s.get('delta') is not None:
                deltas.append(int(s['delta']))
    if not deltas:
        return {'violations': 0, 'note': '无奖励轮样本'}
    big = sum(1 for d in deltas if d > 5)
    return {'violations': 0, 'rounds': len(deltas),
            'max_delta': max(deltas),
            'gt5_share': round(big / len(deltas), 3),
            'fat_tail_landed': big > 0,
            'note': '未落地=恒 +2 基线态(批㉗ F3/F4 修复前置)'}


def check_boss_win_curve_sample_gate(ledgers: list[list[dict]]) -> dict:
    """批㉗ boss_win_curve_sample_gate(boss 胜局样本门;披露)。

    判据(设计表原文):boss 胜率表扩锚点前置条件=实机 boss 胜局
    样本(rung 分桶 n≥3/桶);到点前 boss 族 A/B 结论只标「单点
    外推敏感度」,不作策略裁决依据。本检查披露 sim 批 boss 轮
    的 rung 分桶 n(观察面;实机样本门在 outcomes 侧另行统计)。
    """
    buckets: dict[int, int] = {}
    for rows in ledgers:
        for row in rows:
            if (row.get('sim') or {}).get('node') != 'boss':
                continue
            b = _rung_of_row(row)
            buckets[b] = buckets.get(b, 0) + 1
    gate = all(n >= 3 for n in buckets.values()) if buckets else False
    return {'violations': 0, 'rung_buckets': buckets,
            'gate_met': gate,
            'note': 'sim 侧观察面;实机 boss 胜局样本门(批㉗ F6)'
                    '到点前 boss 族 A/B 只标单点外推敏感度'}


def check_pool_hit_rate_disclosure(ledgers: list[list[dict]]) -> dict:
    """批㉗ pool_hit_rate_disclosure(池命中率三数;条件披露)。

    判据(设计表原文):批报告加 battle/encounter/boss 池命中率
    三数;fallback 池模式下三数应为 0/0/0——命中率>0 却标
    fallback = 配置回归哨兵。**依赖标注**:池命中率计数未进
    账本(cw_sim wrap,批㉗ F2 探针法)→ sim.pool_hits 字段在
    则披露三数,不在则披露跳过。
    """
    for rows in ledgers:
        for row in rows:
            ph = (row.get('sim') or {}).get('pool_hits')
            if isinstance(ph, dict):
                agg: dict[str, int] = {}
                for rows2 in ledgers:
                    for row2 in rows2:
                        h = (row2.get('sim') or {}).get('pool_hits')
                        if isinstance(h, dict):
                            for k, v in h.items():
                                agg[k] = agg.get(k, 0) + int(v)
                return {'violations': 0, 'pool_hits': agg}
    return {'violations': 0,
            'note': '依赖未接线:sim.pool_hits(cw_sim 批㉗ F2 '
                    'wrap 法)——披露跳过,不判'}


def check_shop_cost_conformance(ledgers: list[list[dict]]) -> dict:
    """批④ shop_cost_conformance(发牌费用分布符合性;混合判据)。

    判据(设计表原文):sim 逐 level 发牌成本分布 vs REFRESH_PROB
    (按 sim 实际 max_cost 口径)最大偏差 ≤0.01,且「池内存在某
    费档但 0 供给」= 0——设计时现状 lv9 4费偏差 .30(0 供给,
    旧池截断;ADR-0272 已修)。**口径声明**:①0.01 带是 MC 专用
    (专用大样本),批级经验分布带 MC 噪声 → 偏差只披露不判;
    ②等级 join 用行末 state.level,26% 行有 XP 重放偏差(批⑭
    解析自纠)——zero-supply 判据用 p≥0.05 且该级抽牌 ≥200 的
    强条件压制两类噪声;违反 = 池截断回归(ADR-0272)。
    """
    from sr_od.application.currency_war.cw_shop_odds import REFRESH_PROB
    by_level: dict[int, dict[int, int]] = {}
    for rows in ledgers:
        for row in rows:
            level = (row.get('state') or {}).get('level')
            if not level:
                continue
            d = by_level.setdefault(level, {})
            for w in (row.get('sim') or {}).get('shop_waves') or []:
                for c in w.get('cards') or []:
                    d[c.get('cost') or 0] = d.get(c.get('cost') or 0, 0) + 1
    issues: list[str] = []
    max_dev = 0.0
    for level, d in sorted(by_level.items()):
        tot = sum(d.values())
        if tot < 200:
            continue
        for cost, p in (REFRESH_PROB.get(level) or {}).items():
            emp = d.get(cost, 0) / tot
            max_dev = max(max_dev, abs(emp - p))
            if p >= 0.05 and emp == 0:
                issues.append(
                    f'lv{level} {cost}费 p={p} 但 0 供给'
                    f'(池截断回归——批④/ADR-0272)')
    return {'violations': len(issues), 'issues': issues[:5],
            'max_dev': round(max_dev, 4),
            'note': 'max_dev 含 MC 噪声+XP 重放偏差,只披露;判据'
                    '只辖 zero-supply 强条件'}




def check_boss_round_real_actions(ledgers: list[list[dict]]) -> dict:
    """自由批 boss_round_real_actions(r9 金足零真实动作;披露)。

    判据(设计表原文):boss 轮(r9)8 段中非振荡的 Buy/LevelUp
    ≥1(或金≥cost 时必有真实动作)——设计时现状 seed4 r9 金101
    全振荡。**口径降级声明**:sim 每轮单决策段(8 段生产语义
    sim 不建模)→ 账本口径 = r9 轮内「波里有可负担件且金≥10
    且零 Buy/LevelUp」局计数;r408 后振荡已由 no_same_round_
    buy_sell 辖,本检查盯「金足全静默」形态——设计为断言式,
    但「策略不花末段金」是批⑦ endgame_gold_sink 立项(归档)
    的已知面 → 先披露计数,红量大时按 math_proofs 立项裁决。
    """
    stalls = tot = 0
    for rows in ledgers:
        for row in rows:
            if (row.get('round_num') or 0) != 9:
                continue
            tot += 1
            if (row.get('gold') or 0) < 10:
                continue
            if any(a.get('__type__') in ('BuyCard', 'LevelUp')
                   for a in row.get('actions') or []):
                continue
            affordable = any(
                (w.get('gold') or 0) >= (c.get('cost') or 99)
                for w in (row.get('sim') or {}).get('shop_waves') or []
                for c in w.get('cards') or [])
            if affordable:
                stalls += 1
    return {'violations': 0, 'r9_rounds': tot,
            'gold_affordable_no_action': stalls,
            'note': '披露口径;末段金出口裁决归 math_proofs 立项'
                    '(批⑦ endgame_gold_sink)'}


# --- 清偿批:语料级检查(outcomes/summary dict,调用方显式调) ----

def check_attach_run_detector(outcome_rows: list[dict]) -> list[str]:
    """批⑬ attach_run_detector(run 接管段标签;语料级)。

    判据(设计表原文):首条 exogenous 行 plane=1 且 round>1 →
    runs 打 attach 标签;判读/池生成默认排除。吃 outcomes 行
    (run_id/plane/round_num 键),按 run 分组判首行形态。
    接管段遥测降权纪律(skill)的机械化前置。
    """
    seen_first: set[str] = set()
    out: list[str] = []
    for row in outcome_rows:
        rid = row.get('run_id')
        if rid is None or rid in seen_first:
            continue
        seen_first.add(rid)
        if (row.get('plane') or 0) == 1 \
                and (row.get('round_num') or 0) > 1:
            out.append(f'{rid}: 首行 plane=1 r{row.get("round_num")}'
                       f'>1(attach 接管段——判读/池生成默认排除,'
                       f'批⑬)')
    return out


def check_hp_monotonic_sentinel(outcome_rows: list[dict]) -> list[str]:
    """批⑬ hp_monotonic_sentinel(同 run hp 只降不升;语料级)。

    判据(设计表原文):同 run outcomes hp_after 序列出现上升 →
    报警(HP 只降不升;run154910 71→100 接管帧实证——重启接管
    段 hp 一律不可作判据的机械化哨兵)。hp_after 缺失行跳过。
    """
    last: dict[str, int] = {}
    out: list[str] = []
    for row in outcome_rows:
        rid = row.get('run_id')
        hp = row.get('hp_after')
        if rid is None or hp is None:
            continue
        if rid in last and hp > last[rid]:
            out.append(
                f'{rid}: hp {last[rid]}→{hp} 上升(接管帧错值/'
                f'读链毒化——批⑬,该段判读降权)')
        last[rid] = int(hp)
    return out


def check_plane_reached_consistency(summary: dict,
                                    outcome_rows: list[dict]) -> list[str]:
    """批⑧ F4 plane_reached_consistency(summary↔outcomes 对拍)。

    判据(设计表原文):summary 的 plane_reached 与 outcomes 末条
    plane 对拍(run_20260823_105348 实锤:runs 记 3 / outcomes
    真值 2)。不一致 = summary 写入路径口径可疑(FAIL/崩溃/
    重启兜底缺失族,批⑧ F2)。
    """
    last_plane: dict[str, int] = {}
    for row in outcome_rows:
        rid = row.get('run_id')
        if rid is not None and row.get('plane') is not None:
            last_plane[rid] = int(row['plane'])
    out: list[str] = []
    rid = summary.get('run_id') or summary.get('runId')
    claimed = summary.get('plane_reached')
    if rid is None or claimed is None:
        return out
    truth = last_plane.get(rid)
    if truth is not None and int(claimed) != truth:
        out.append(
            f'{rid}: summary plane_reached={claimed} vs outcomes '
            f'末条 plane={truth}(汇总写入路径不一致——批⑧ F4)')
    return out


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
    from sr_od.application.currency_war.cw_state import (
        BenchChar,
        GameState,
        ShopCard,
    )
    from sr_od.application.currency_war.cw_strategy import StrategySession
    from sr_od.application.currency_war.decision_v2.candidates import (
        ACTION_CLASSES,
        generate_candidates,
    )
    from sr_od.application.currency_war.decision_v2.registry import (
        DEFAULT_REGISTRY,
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
    from sr_od.application.currency_war.cw_intention import HoardTarget
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

    判据(ADR-0290 对抗修订④):``decision_v2.registry`` 的审计矩阵
    每格=约束名(存在于 constraints 清单)或显式 ``('none', 原因)``
    声明;空格/未知约束名=违规。新增动作类型或资源维时本检查强制
    过检(通道制漏门病 r408/[32] 全是事后补的根治)。
    """
    from sr_od.application.currency_war.decision_v2.arbiter import (
        build_audit_report,
    )
    from sr_od.application.currency_war.decision_v2.registry import (
        DEFAULT_REGISTRY,
    )
    rep = build_audit_report(DEFAULT_REGISTRY)
    return {'violations': len(rep['violations']),
            'detail': rep['violations'],
            'matrix': rep['matrix'],
            'constraints': rep['constraints']}


def check_decision_v2_telemetry_contract() -> dict:
    """批㉝(decision_v2 首超审计·题②):可解释性遥测契约锁。

    判据:``DecisionV2Strategy.decide_prep`` 执行后,
    ``session.last_candidate_scores`` 必须满足——
    ① 轮次戳新鲜(last_candidate_scores_round == 当前轮);
    ② 键格式可解析(``r<轮>:<标签>:<desc>`` ——遥测判读可用性
       的地基,键崩坏=判读端整字段不可读);
    ③ 分值为数值;
    ④ 有采纳动作时至少 1 个键(采纳必须留痕)。
    披露(非违规):键数与分值多样性——批㉝ 实测均分仅 ~1.1 键/
    ~1.0 个不同分值(只记 accepted,看不到落选替代方案的分),
    「每轮候选×分数」的可解释性承诺只兑现一半,登记待策略域
    裁决(是否把 result.log 未采纳行也写入遥测)。
    """
    import re

    from sr_od.application.currency_war.cw_state import (
        BenchChar,
        GameState,
        ShopCard,
    )
    from sr_od.application.currency_war.cw_strategy import StrategySession
    from sr_od.application.currency_war.decision_v2.strategy import (
        DecisionV2Strategy,
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
    """W52(ADR-0326 §1.5-3):补偿连续放弃轮 ≥3 报警(设计容量不足
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
    """批㉝(题①解剖·危机局指纹):危机态囤金零买入哨兵(披露级)。

    判据(仅 d2_ 前缀批次辖):某局存在轮 r∈[5,8] hp≤25(危机态),
    且从该轮起 ≥2 个后续轮 gold≥40 且这些轮零 BuyCard → 违规
    (息引擎门/满息地板把危机局锁进「囤金不补板」形态;批㉝
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


# --- 清偿批:批级聚合入口(cw_sim 接线随 worker X 合流) ---------

def run_batch_level_checks(ledgers: list[list[dict]],
                           report: dict | None = None,
                           pool_map: dict | None = None) -> dict:
    """清偿批批级聚合入口:披露/哨兵/条件型检查一次跑全。

    逐局违规锁已在 _BATCH_CHECKS(run_checks_on_ledgers 自动扫);
    本入口辖批级聚合(吃全批账本)、池级条件(encounter 预算)、
    报告级披露(死旋钮/锚登记)。simulate_p1_batch 的接线归
    cw_sim.py(worker X 合流后;冲突隔离,本批不碰 cw_sim)。
    """
    out: dict[str, dict] = {
        'late_deploy_full': check_late_deploy_full(ledgers),
        'no_streak_buy_freeze': check_no_streak_buy_freeze(ledgers),
        'hoard_gold_no_engine': check_hoard_gold_no_engine(ledgers),
        'second_engine_deadline': check_second_engine_deadline(ledgers),
        'endgold_residue_channel_probe':
            check_endgold_residue_channel_probe(ledgers),
        'p2_precache_gate_closure':
            check_p2_precache_gate_closure(ledgers),
        'formation_gradient_sentinel':
            check_formation_gradient_sentinel(ledgers),
        'streak_break_interest_fires':
            check_streak_break_interest_fires(ledgers),
        'mc_faction_calib': check_mc_faction_calib(ledgers),
        'streak_combat_only_income':
            check_streak_combat_only_income(ledgers),
        'shop_distinct_names_invariant':
            check_shop_distinct_names_invariant(ledgers),
        'supply_agent_semantics': check_supply_agent_semantics(ledgers),
        'refresh_cost_channel': check_refresh_cost_channel(ledgers),
        'hp_readable_disclosure': check_hp_readable_disclosure(ledgers),
        'briefing_pipeline_liveness':
            check_briefing_pipeline_liveness(ledgers),
        'deploy_cap_reader_noise':
            check_deploy_cap_reader_noise(ledgers),
        'calibration_dead_knob_disclosure':
            check_calibration_dead_knob_disclosure(report),
        'reward_heal_fat_tail': check_reward_heal_fat_tail(ledgers),
        'boss_win_curve_sample_gate':
            check_boss_win_curve_sample_gate(ledgers),
        'pool_hit_rate_disclosure':
            check_pool_hit_rate_disclosure(ledgers),
        'shop_cost_conformance': check_shop_cost_conformance(ledgers),
        'boss_round_real_actions':
            check_boss_round_real_actions(ledgers),
        # ADR-0291(决策框架 v2 骨架批):候选覆盖面 + 审计表完备性
        'decision_v2_candidate_coverage':
            check_decision_v2_candidate_coverage(ledgers),
        'decision_v2_arbiter_matrix':
            check_decision_v2_arbiter_matrix(),
        # 批㉝(首超审计):可解释性遥测契约 + 危机囤金哨兵
        'decision_v2_telemetry_contract':
            check_decision_v2_telemetry_contract(),
        'decision_v2_crisis_gold_hoard':
            check_decision_v2_crisis_gold_hoard(ledgers),
        # W52(ADR-0326 §1.5-3):补偿连续放弃轮 ≥3(容量不足信号)
        'decision_v2_remedy_loop':
            check_decision_v2_remedy_loop(ledgers),
        # 批㉞(供给 vs 标签审计):直通门标签-候选一致性不变式
        'decision_v2_supply_label_consistency':
            check_decision_v2_supply_label_consistency(),
    }
    if pool_map is not None:
        out['encounter_rung_sample_budget'] = \
            check_encounter_rung_sample_budget(pool_map)
    if report is not None:
        out['anchor_seed_portability_n600'] = \
            check_anchor_seed_portability_n600(report)
        out['anchor_lowchannel_registry'] = \
            check_anchor_lowchannel_registry(report)
    return out


# --- 批㉞(供给 vs 标签审计):直通门标签-候选一致性 --------------------

def check_decision_v2_supply_label_consistency() -> dict:
    """批㉞:engine_seed/pair/copy 全直通后,标签裁决与候选生成必须
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
    from sr_od.application.currency_war.cw_state import (
        BenchChar,
        BuyCard,
        GameState,
        ShopCard,
        pad_bench,
    )
    from sr_od.application.currency_war.cw_strategy import StrategySession
    from sr_od.application.currency_war.decision_v2 import candidates as _c
    from sr_od.application.currency_war.decision_v2.candidates import (
        generate_candidates,
    )
    from sr_od.application.currency_war.decision_v2.registry import (
        DEFAULT_REGISTRY,
    )

    def _mk(plane: int, rn: int, level: int, gold: int, bench, shop,
            line: str | None, bridge: str | None):
        st = GameState()
        st.plane, st.round_num = plane, rn
        st.level, st.gold, st.hp = level, gold, 80
        st.bench = pad_bench(list(bench))   # ADR-0316 槽位表
        st.shop = list(shop)
        sess = StrategySession()
        sess.locked_line = line
        sess.bridge_id = bridge
        return st, sess

    # 探针态覆盖:无方向种子态(引擎门)/ 锁线态(carry+凑档)/
    # 副本上限态(copies_cap)/ bench 杂件(卖通道不被误判为买候选)
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
        r'^(?P<nt>[a-z]+):桶(?P<b>\d+)\((?:n=(?P<n>\d+)|缺)\)$')
    if meta is None:
        return {'violations': 0, 'note': '无披露载体(meta=None)不辖'}
    if not any((pool_map or {}).values()):
        return {'violations': 0, 'note': '池空(fallback/历史快照)不辖'}
    violations: list[str] = []
    # 披露侧:反向解析
    disclosed: set[tuple[str, int, str, int]] = set()   # (nt, 桶, kind, n)
    unparseable: list[str] = []
    for s in (meta.get('bucket_poverty') or []):
        m = poverty_re.match(str(s))
        if not m:
            unparseable.append(str(s))
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
            'note': '贫困披露↔池内容双向结构对拍(批㊲);'
                    '红 = 披露断裂/格式漂移'}


#: (批㊲ boss_win_p_cache_freshness 已随 ADR-0308 废除:rung 外推
#: 机制被 W31 节点胜率阶梯替换,无进程内缓存可查。)


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

    背景(批㉖ F1 读链翻转,commit 09cf8296):``enemy_difficulty``
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
