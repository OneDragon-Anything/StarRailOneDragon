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
29 已有 + 清偿批 46 新实现 + 48 归档,归档死因清单见 ADR-0289):
- 逐局违规锁(进 _BATCH_CHECKS,sim 批次自动扫):ledger_
  consistency / coldstart_direction / deploy_fills_cap /
  equip_worn_in_battle / no_component_equipped_p1 /
  levelup_interest_engine_gate / no_same_round_buy_sell /
  bench_full_deadlock_probe / carry_gate_bench_deadlock /
  shop_slot_consumption / deploy_after_buy_semantics /
  bond_fallback_purchase_validity + 清偿批:gold_nonneg /
  bench_capacity / deployed_schema_filter / engine_seed_not_
  resold / buys_at_full_bench / oscillation_xp_cap /
  levelup_flat4_lock / phantom_equip_no_wear /
  carry_on_shelf_responded / no_future_carry_sold /
  dead_system_second_pivot / degrade_recover_mutex;
- 逐局披露归 0 锁:phantom_rebuy_disclosure /
  ledger_deploy_lag_disclosure / hp_upper_bound_truth;
- 批级聚合(cw_sim 接线;清偿批新条目经 run_batch_level_checks
  聚合入口,cw_sim.py 接线随 worker X 合流后并入 simulate_p1_
  batch):boss_win_calibration / formation_hp_coupling_sentinel /
  levelup_binding / r5plus_refresh_closure / sim_endgold_calib /
  protect_set_bench_share + 清偿批披露/哨兵(见该函数注释);
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
  adr0266_ab_guard / mc_faction_calib。
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
    - **仅 LineStrategy(v2)栈账本适用**:生产配置 strategy_id=
      line_v2 时实机 decisions.jsonl 同样适用(BuyCard.reason 是
      共享 dataclass,生产遥测同带标签);**default 栈**(买牌走
      cw_plan,reason='plan')不辖于 r368 门,跑此检查必误报——
      生产侧按局 strategy_id/actions reason 词表判栈后选择。
    """
    out: list[str] = []
    for row in rows:
        if row.get('plane') != 1 or (row.get('round_num') or 9) > 2:
            continue
        for a in row.get('actions') or []:
            if a.get('__type__') != 'BuyCard':
                continue
            reason = a.get('reason') or 'unknown'
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
    """压测经济批 [12]/①残差指纹(升级门息引擎前置;ADR-0266;r406)。

    指纹:lv≥5(追级段)的 LevelUp 发生在「息引擎未立」——时点金
    (本轮首波金,=收入后花销前)<50 **且** 本局此前从未有任何轮
    金 ≥50。追级局形态:每轮 40-50 徘徊反复够升级门槛,50 永远
    攒不满(压测 25.9% 局终局未满 50,14/15 从未攒到)。

    近似声明:①升级前等级用**上一轮账本 level**(轮内升级完成会
    抬高本行 level,prev_level 才是购买时的等级;首轮 prev=3);
    ②时点金 = shop_waves 首波 gold(决策发生在收入后/花销前);
    ③「曾达满息」按此前各轮 max(首波金, 轮末金) ≥50——轮中段
    金峰(买后卖回)不可见,声明数据边界。合法放行:lv<5(r263
    过渡成型基线宽松门)、曾满息、时点金≥50(gold-cost≥50 分支
    的上界)均不报;时点金 <50 但 gold-cost≥50 的合法升级会**误报
    成可疑**(cost 不可逐动作重演——压测原批按账本逐动作重演过,
    检查侧退化为保守近似,违规率高发时按 seed 重放精查)。
    """
    out: list[str] = []
    ever_full = False
    prev_level = 3
    for row in rows:
        if row.get('plane') != 1:
            continue
        waves = (row.get('sim') or {}).get('shop_waves') or []
        gold0 = waves[0].get('gold') if waves else row.get('gold')
        has_lv = any(a.get('__type__') == 'LevelUp'
                     for a in row.get('actions') or [])
        if has_lv and prev_level >= 5 \
                and gold0 is not None and gold0 < 50 and not ever_full:
            out.append(
                f"p1r{row.get('round_num')} LevelUp 时点金 {gold0}<50"
                f" 且未曾满息(lv{prev_level} 追级,息引擎未立"
                f"——ADR-0266 违规)")
        end_gold = row.get('gold')
        if (gold0 is not None and gold0 >= 50) \
                or (end_gold is not None and end_gold >= 50):
            ever_full = True
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
    仅 v2 栈(line_v2)账本适用(default 栈 reason='plan' 的
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
                if _n and a.get('reason') == 'copy':
                    _copy_names.add(_n)   # 3合1 收集语境:让位豁免
                elif _n and a.get('reason') == 'engine_seed':
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
    """
    out: list[str] = []
    seed_buys: dict[str, tuple[int, int]] = {}   # name → (轮号, 同轮份数)
    for row in rows:
        rn = row.get('round_num') or 0
        for a in row.get('actions') or []:
            t = a.get('__type__')
            if t == 'BuyCard' and a.get('reason') == 'engine_seed':
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


def check_buys_at_full_bench(rows: list[dict]) -> list[str]:
    """自由批(bench 满不买;0 容忍;ADR-0283 守卫的账本锁)。

    判据(设计表原文):bench≥上限 时不再输出 BuyCard——现状
    (设计时)655 次;上限真值已核(BENCH_CAPACITY=9,cw_state
    design doc 实测)→ 锁 0。ADR-0283 超容买守卫落地后 BuyCard
    动作只在该轮容量允许时出现。

    容量口径(近似声明):期初 bench = 上一轮末 bench;本轮可买
    上限 = 9 − 期初 + 本轮卖出数 + 2×本轮 merges(3合1 每次腾
    2 席;守卫在执行层逐笔判,账本只能轮末重放近似)。
    """
    out: list[str] = []
    prev_bench = 0
    for row in rows:
        st = row.get('state') or {}
        acts = row.get('actions') or []
        buys = sum(1 for a in acts if a.get('__type__') == 'BuyCard')
        sells = sum(1 for a in acts if a.get('__type__') == 'SellBench')
        merges = (row.get('sim') or {}).get('merges') or 0
        allowed = 9 - prev_bench + sells + 2 * merges
        if buys > max(allowed, 0):
            out.append(
                f"p{row.get('plane')}r{row.get('round_num')}: 买入 {buys}"
                f" 笔超容量上限 {max(allowed, 0)}(期初 bench {prev_bench}"
                f"+卖 {sells}+merge {merges}——满仓买守卫回归,"
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
                if a.get('reason') == 'copy':
                    copy_names.add(_n)
                else:
                    if a.get('reason') == 'engine_seed':
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


def check_carry_on_shelf_responded(rows: list[dict]) -> list[str]:
    """成型批 carry_on_shelf_responded(终局线 carry 在架响应;ADR-0289)。

    判据(设计表原文):任意波 carry(终局线)在架且波金≥cost+10
    → 该轮必有 BuyCard(carry 或引擎件)或日志拒绝原因。sim 账本
    无拒绝原因字段 → 违规锁口径:终局线(末次非空 target_comp)
    锁定轮内,carry 在架 + 波金−cost≥10 + **轮末 bench<9**
    (满员滞留由 carry_gate_bench_deadlock 辖)+ **carry 未持有**
    (已持有 = 囤件合法形态,同 ADR-0280 口径)且该轮无目标件/
    引擎件买入 → 违规。设计基线 21/60 零持有;r416 腾位门后
    残留即漏边。轮末 bench 是决策时点的下界近似(买后 bench 更
    高,方向只放宽不收紧——漏判风险小于误判)。
    """
    from sr_od.application.currency_war.cw_line_library_v1 import line_of
    final_comp = ''
    for row in rows:
        if row.get('target_comp'):
            final_comp = row['target_comp']
    line = line_of(final_comp) if final_comp else None
    if line is None or not line.carry:
        return []
    carry = line.carry
    targets = {carry} | set(line.core_cards) \
        | set(line.opportunistic_cards)
    out: list[str] = []
    for row in rows:
        if row.get('plane') != 1 or row.get('target_comp') != final_comp:
            continue
        st = row.get('state') or {}
        if len(st.get('bench') or []) >= 9:
            continue
        owned = {b.get('char_id') for b in st.get('bench') or []}
        owned |= {d.get('char_id') for d in st.get('deployed') or []}
        if carry in owned:
            continue
        responded = any(
            a.get('__type__') == 'BuyCard'
            and ((a.get('card') or {}).get('name') in targets
                 or a.get('reason') in ('engine_seed', 'engine',
                                        'bridge_seed', 'line'))
            for a in row.get('actions') or [])
        if responded:
            continue
        hit = False
        for w in (row.get('sim') or {}).get('shop_waves') or []:
            for c in w.get('cards') or []:
                if c.get('name') == carry \
                        and (w.get('gold') or 0) - (c.get('cost') or 0) \
                        >= 10:
                    out.append(
                        f"p1r{row.get('round_num')}: carry {carry} 在架"
                        f"金足(≥cost+10)未响应(无目标/引擎件买入"
                        f"——成型批 carry_on_shelf_responded)")
                    hit = True
                    break
            if hit:
                break
    return out


def check_no_future_carry_sold(rows: list[dict]) -> list[str]:
    """成型批 no_future_carry_sold(终局线 carry P1 零卖出;0 容忍)。

    判据(设计表原文):终局线 carry 在 P1 阶段零卖出——现状
    (设计时)7 次。carry 是终局线的引擎本体,P1 卖出 = 线死信号
    (腾位门弱序把 carry 当最弱件卖 = ADR-0280 保护集回归)。
    终局线口径 = 末次非空 target_comp(卖出时点可能尚未锁线,
    用终局线回看是设计原意「未来 carry 不得卖」)。
    """
    from sr_od.application.currency_war.cw_line_library_v1 import line_of
    final_comp = ''
    for row in rows:
        if row.get('target_comp'):
            final_comp = row['target_comp']
    line = line_of(final_comp) if final_comp else None
    if line is None or not line.carry:
        return []
    out: list[str] = []
    for row in rows:
        if row.get('plane') != 1:
            continue
        for a in row.get('actions') or []:
            if a.get('__type__') == 'SellBench' \
                    and a.get('name') == line.carry:
                out.append(
                    f"p1r{row.get('round_num')}: 终局线 carry "
                    f"{line.carry} 被卖出(线死信号——成型批 "
                    f"no_future_carry_sold 0 容忍)")
    return out


def _engine_of_line(line) -> tuple[str, int] | None:
    """线的引擎体系(bond, tier):线内卡(carry/core/opportunistic)
    的阵营命中 _ENGINES_TRAITS_SYNC 首个引擎档。识别不出 → None
    (dead_system 检查披露跳过;希儿系非阵营档不辖)。
    """
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    names = [line.carry] + list(line.core_cards) \
        + list(line.opportunistic_cards)
    for bond, tier in _ENGINES_TRAITS_SYNC:
        for n in names:
            ch = CHARACTERS.get(n)
            if ch and bond in (ch.factions or []):
                return bond, tier
    return None


def check_dead_system_second_pivot(rows: list[dict]) -> list[str]:
    """成型批 dead_system_second_pivot(死体系二次 pivot;ADR-0289)。

    判据(设计表原文):目标线所属体系供给<tier 连续 3 轮 →
    必须 pivot 或记原因——现状(设计时)13/60 死体系、二次 pivot
    0。sim 账本无「记原因」字段 → 违规锁口径:锁线段内该体系
    (线内卡命中的引擎 bond)店内供给(全波该阵营卡数)<tier
    连续 3 轮且 target_comp 未变 → 违规(该 pivot 而不 pivot 的
    死守形态)。体系识别不出(非四引擎线)→ 披露跳过(空返回)。
    供给按波卡 faction 单值口径(卡 faction 是注册表首阵营,
    多阵营卡按首阵营计——方向只收紧, tier 门槛本就保守)。
    """
    from sr_od.application.currency_war.cw_line_library_v1 import line_of
    final_comp = ''
    for row in rows:
        if row.get('target_comp'):
            final_comp = row['target_comp']
    line = line_of(final_comp) if final_comp else None
    if line is None:
        return []
    engine = _engine_of_line(line)
    if engine is None:
        return []
    bond, tier = engine
    out: list[str] = []
    short = 0
    last_rn: int | None = None
    for row in rows:
        if row.get('plane') != 1 or row.get('target_comp') != final_comp:
            short = 0   # target 变了 = pivot 发生,窗口断
            continue
        rn = row.get('round_num') or 0
        if last_rn is not None and rn - last_rn > 1:
            short = 0   # 轮号不连续(跨段),窗口断
        supply = sum(
            1
            for w in (row.get('sim') or {}).get('shop_waves') or []
            for c in w.get('cards') or []
            if c.get('faction') == bond)
        short = short + 1 if supply < tier else 0
        last_rn = rn
        if short >= 3:
            out.append(
                f"p1r{rn}: 体系 {bond} 供给<{tier} 连续 {short} 轮"
                f"未 pivot(死体系死守——成型批 dead_system_second"
                f"_pivot)")
            short = 0   # 报一次断窗,防刷屏
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


# ADR-0285(批㉑ F1 裁决):carry 门金足判据对齐调用方地板——
# 检查模块不 import 策略(依赖方向纪律),地板值与 line_strategy
# 三档同步维护(值漂移由 floor 边界双向锁暴露,同
# _ENGINES_TRAITS_SYNC 纪律):_INTEREST_FLOOR=50 / _WAR_FLOOR=30 /
# _BOSS_BREAKER_FLOOR=10(P1 r≥5 恒 boss_breaker;连胜降档 5 /
# economy 低位 0 更宽松 → 取梯级最大保保守:宁可漏报不误报,
# 对齐后残留违规即真死锁/门漏边)。
_CARRY_FLOOR_INTEREST: int = 50
_CARRY_FLOOR_WAR: int = 30
_CARRY_FLOOR_BOSS: int = 10


def _carry_floor_est(round_num: int, gold: int) -> int:
    """carry 腾位门地板保守估计(按象限梯级最大;ADR-0285)。

    r≥5 恒 boss_breaker(地板 10);r<5 economy(50/gold%10/0)
    或 war(30/5)象限并存 → 取梯级最大。
    """
    if round_num >= 5:
        return _CARRY_FLOOR_BOSS
    if gold >= _CARRY_FLOOR_INTEREST:
        return _CARRY_FLOOR_INTEREST
    if gold >= _CARRY_FLOOR_WAR:
        return _CARRY_FLOOR_WAR
    return max(gold % 10, 5) if gold >= 10 else 5


def check_carry_gate_bench_deadlock(rows: list[dict]) -> list[str]:
    """批⑯ F3/F4(ADR-0280):carry 腾位门死锁指纹。

    指纹:P1 r≤7(收益域——r8-r9 miss 买不买无差异,批⑯ F4)、
    锁线、carry 在店(任一牌面波)且金足(批⑯ F3 口径:gold−已提案
    花销≥cost)、bench=9 满、**当轮零买入且零卖出**——即腾位门
    该出手而未出手(基线 56 局/148 事件,18.7%)。
    修复后该指纹应归 0(腾位门产出 SellBench+BuyCard,行不再
    「零买零卖」);残留违规=保护集窒息复发或门条件漏边。

    金足口径(ADR-0285,批㉑ F1 裁决):wave_gold − cost ≥
    _carry_floor_est(轮次, wave_gold)——旧口径 wave_gold≥cost
    不含调用方地板,把「金足但破息档地板」的合法 miss 误报为
    死锁(seed30/39 恒 2 违规的结构成因,r416 起逐 commit 恒 2);
    对齐后违规应真归 0,残留即真死锁信号。
    """
    from sr_od.application.currency_war.cw_line_library_v1 import line_of
    out: list[str] = []
    for row in rows:
        if row.get('plane') != 1:
            continue
        rn = row.get('round_num') or 0
        if rn > 7:
            continue   # 收益域:r8-r9 不辖(批⑯ F4)
        line = line_of(row.get('target_comp') or '')
        if line is None or not line.carry:
            continue
        st = row.get('state') or {}
        if len(st.get('bench') or []) < 9:
            continue
        # 未持有口径(批⑯ F3:miss=carry 在店+金足+**未持有**):
        # bench/deployed 已有 carry 名 = 已持有,不辖([21] 买而不上
        # 的合法囤件形态;修后 r416b 诊断实证 4/25 残留全是此口径差)
        owned = {b.get('char_id') for b in st.get('bench') or []}
        owned |= {d.get('char_id') for d in st.get('deployed') or []}
        if line.carry in owned:
            continue
        if any(a.get('__type__') in ('BuyCard', 'SellBench')
               for a in row.get('actions') or []):
            continue   # 有买或有腾位动作 → 非死锁形态
        for w in (row.get('sim') or {}).get('shop_waves') or []:
            _g = w.get('gold') or 0
            if any(c.get('name') == line.carry
                   and _g - (c.get('cost') or 0)
                   >= _carry_floor_est(rn, _g)
                   for c in w.get('cards') or []):
                out.append(
                    f"p1r{rn}: carry {line.carry} 在店+金足(含地板)"
                    f"+bench=9+零买零卖(carry 腾位门死锁指纹"
                    f"——批⑯ F3,ADR-0280/0285)")
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


def check_bond_fallback_purchase_validity(rows: list[dict]) -> list[str]:
    """[31] 凑档降级(ADR-0288):bond_fallback 买入谓词有效性,0 容忍。

    判据:每笔 reason='bond_fallback' 的 BuyCard 必须满足买侧谓词
    (line_strategy._bond_fallback_wants 的账本侧镜像):
    ① 锁线(target_comp 可查线库;未锁线买入 = 谓词首门失效);
    ② 战斗轮(r≥3;P3:r1-r2 买件纯付息);
    ③ 本波目标件全缺(该笔买入时的牌面波——按 RefreshShop 动作
    切波重放,波内槽消费后——无 carry/opportunistic/P1 桥 core 任一);
    ④ [30] 成本带:cost ≤ 2;
    ⑤ 凑 2 档:card.faction ∈ 决策时点 board∪bench 已有阵营(轮末
    bench ∪ 轮末 board(部署侧)∪ 本轮卖出/更早买入件重构;副本
    同阵营也计——买 #2 与在场 #1 凑 2 档是合法语义,copies 上限
    由 _buy_guards 管)。
    违规任一 = 谓词门失效/回归。目标集口径与 _bond_fallback_wants
    同源镜像(检查模块不 import 策略,依赖方向纪律;漂移由双向锁
    暴露)。sim 为 P1 口径,桥 core 名单取 BRIDGE_POOL。
    """
    from sr_od.application.currency_war.cw_bridge_pool import BRIDGE_POOL
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    from sr_od.application.currency_war.cw_line_library_v1 import line_of
    p1_core = {n for combo in BRIDGE_POOL for n in combo.core}
    out: list[str] = []
    for row in rows:
        rn = row.get('round_num') or 0
        st = row.get('state') or {}
        line = line_of(row.get('target_comp') or '')
        targets: set[str] = set()
        if line is not None:
            targets = ({line.carry} | set(line.opportunistic_cards)
                       | p1_core)
        # ⑤ 的「已有阵营」重构:决策时点的 bench = 轮末 bench ∪ 本轮
        # 卖出件 ∪ 本轮更早买入件(部署在买后,轮末 board 已含部署侧;
        # 买入→卖出/买入→部署的件在轮末 bench 不可见,从动作序找回;
        # SellBench 只有名字,faction 查注册表)。方向只放宽不收紧
        # ——漏判风险小于误判(0 容忍检查误报会淹死真违规)。
        base_owned = set((st.get('board') or {}).keys())
        base_owned |= {b.get('faction') for b in st.get('bench') or []
                       if b.get('faction') and b.get('faction') != '?'}
        waves = (row.get('sim') or {}).get('shop_waves') or []
        wi = 0
        bought_in_wave: dict[str, int] = {}
        owned = set(base_owned)
        for a in row.get('actions') or []:
            t = a.get('__type__')
            if t == 'RefreshShop':
                wi += 1
                bought_in_wave = {}
                continue
            if t == 'SellBench' and a.get('name'):
                ch = CHARACTERS.get(a['name'])
                if ch and ch.factions:
                    owned.add(ch.factions[0])
                continue
            if t == 'BuyCard':
                _c = a.get('card') or {}
                _n = _c.get('name')
                if _n:
                    # 槽消费语义(ADR-0284):波内买走即下架——重放
                    # 剩余槽,买时点判「目标件全缺」才与决策时点的
                    # st.shop 同口径(先买走的目标件不算「在店」)。
                    bought_in_wave[_n] = bought_in_wave.get(_n, 0) + 1
                    # 更早买入件入 owned;**当前 bond_fallback 件自身
                    # 不入**(副本与自己凑 2 档由 copies≥2 判,但首买
                    # 件自身不能自我满足「已有第一块砖」)。
                    if _c.get('faction') and _c['faction'] != '?' \
                            and a.get('reason') != 'bond_fallback':
                        owned.add(_c['faction'])
                if a.get('reason') != 'bond_fallback':
                    continue
            else:
                continue
            card = a.get('card') or {}
            name = card.get('name')
            where = f"p{row.get('plane')}r{rn} bond_fallback {name}"
            if line is None:
                out.append(f"{where}: 未锁线(谓词首门失效,ADR-0288)")
                continue
            if rn < 3:
                out.append(f"{where}: r{rn}<3 非战斗轮(P3 纯付息,"
                           f"ADR-0288)")
            if (card.get('cost') or 0) > 2:
                out.append(f"{where}: cost={card.get('cost')}>2"
                           f"([30] 成本带违规,ADR-0288)")
            wave_supply: dict[str, int] = {}
            if wi < len(waves):
                for c in waves[wi].get('cards') or []:
                    if c.get('name'):
                        wave_supply[c['name']] = \
                            wave_supply.get(c['name'], 0) + 1
            remaining = {n for n, k in wave_supply.items()
                         if k - bought_in_wave.get(n, 0) > 0}
            hit = remaining & targets
            if hit:
                out.append(f"{where}: 波内仍有目标件 {sorted(hit)[:3]}"
                           f"(应走主通道,ADR-0288)")
            fac = card.get('faction')
            if not fac or fac == '?' or fac not in owned:
                out.append(f"{where}: faction={fac} 不在 board∪bench"
                           f"已有阵营(凑 2 档不成立,ADR-0288)")
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
    'carry_gate_bench_deadlock': check_carry_gate_bench_deadlock,
    'shop_slot_consumption': check_shop_slot_consumption,
    'phantom_rebuy_disclosure': check_phantom_rebuy_disclosure,
    'deploy_after_buy_semantics': check_deploy_after_buy_semantics,
    'ledger_deploy_lag_disclosure': check_ledger_deploy_lag_disclosure,
    'hp_upper_bound_truth': check_hp_upper_bound_truth,
    'bond_fallback_purchase_validity': check_bond_fallback_purchase_validity,
    # --- ADR-0289 检查项清偿批(逐局违规锁) ---
    'gold_nonneg': check_gold_nonneg_invariant,
    'bench_capacity': check_bench_capacity_invariant,
    'deployed_schema_filter': check_deployed_schema_filter,
    'engine_seed_not_resold': check_engine_seed_not_resold,
    'buys_at_full_bench': check_buys_at_full_bench,
    'oscillation_xp_cap': check_oscillation_xp_cap,
    'levelup_flat4_lock': check_levelup_flat4_ledger_lock,
    'phantom_equip_no_wear': check_phantom_equip_no_wear,
    'carry_on_shelf_responded': check_carry_on_shelf_responded,
    'no_future_carry_sold': check_no_future_carry_sold,
    'dead_system_second_pivot': check_dead_system_second_pivot,
    'degrade_recover_mutex': check_degrade_recover_mutex,
}


def check_protect_set_bench_share(ledgers: list[list[dict]]) -> dict:
    """批⑯ F3(ADR-0280):保护集 bench 占有率披露(设计张力指标)。

    判据(批⑯设计表原文):锁线局 r6+ 保护件占 bench 槽 ≥7/9 →
    披露级——本检查不构成违规(violations 恒 0),供保护集收窄
    裁决跨批对照(基线批⑯ F3:保护集均 7.45/槽,faction-close
    1.52/槽,真可卖 0.51/事件)。

    保护集口径与 line_strategy._protect_set 同源镜像(双桥池
    fixed∪core+锁线 carry+opportunistic;检查模块不 import 策略,
    值漂移由锁测试双向暴露——同 _ENGINES_TRAITS_SYNC 纪律)。
    跨局聚合检查(吃全批账本,调用方显式调;未进 _BATCH_CHECKS
    的逐局循环——cw_sim 接线归下批)。
    """
    from sr_od.application.currency_war.cw_bridge_pool import (
        BRIDGE_POOL,
        BRIDGE_POOL_P2,
    )
    from sr_od.application.currency_war.cw_line_library_v1 import line_of
    base_protect: set[str] = set()
    for pool in (BRIDGE_POOL, BRIDGE_POOL_P2):
        for combo in pool:
            base_protect.update(combo.fixed + combo.core)
    shares: list[float] = []
    n_ge7 = 0
    peak: dict = {'where': '', 'prot': 0, 'bench': 0, 'share': 0.0}
    for rows in ledgers:
        for row in rows:
            if row.get('plane') != 1 \
                    or (row.get('round_num') or 0) < 6:
                continue
            line = line_of(row.get('target_comp') or '')
            if line is None:
                continue   # 未锁线局不辖
            protect = (base_protect | {line.carry}
                       | set(line.opportunistic_cards))
            names = [b.get('char_id') for b in
                     (row.get('state') or {}).get('bench') or []
                     if b.get('char_id')]
            if not names:
                continue
            prot_n = sum(1 for n in names if n in protect)
            share = prot_n / len(names)
            shares.append(share)
            if prot_n >= 7:
                n_ge7 += 1
            if share > peak['share']:
                peak = {'where': f"p1r{row.get('round_num')}",
                        'prot': prot_n, 'bench': len(names),
                        'share': round(share, 3)}
    return {'violations': 0,   # 披露级(批⑯设计表):设计张力指标
            'rows': len(shares), 'ge_7_of_9_rows': n_ge7,
            'ge_7_share': round(n_ge7 / len(shares), 3) if shares else None,
            'avg_share': round(sum(shares) / len(shares), 3) if shares else None,
            'peak': peak}


# --- Δ池标定检查(压测批③ F1 检查项 1/2/3;ADR-0268) ---------------
# 前两条吃池 dict(simulate_p1_batch 有 resolve_pool 产物;纯 dict
# 入参,不 import cw_sim);第三条吃两臂账本(A/B 对照调用方使用,
# 不进 _BATCH_CHECKS——单臂批次无对照对象)。
_POOL_BUCKET_MIN_N = 5       # 同 cw_sim._BUCKET_MIN_N(值同步维护)
_POOL_DEPTH_BUCKET_W = 3     # 同 cw_sim._DEPTH_BUCKET_W(值同步维护)


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
    """批㉗ 检查项 reward_delta_pool_bucket_lock(ADR-0292)。

    判据(规格原文「分布入池且均值≈语料真值」):
    - reward 池非空且 n≥30(分布**入池**:结算采样源是语料经验
      分布而非 EARLY_WIN_DELTA 常数);
    - 全样本均值距语料真值(+2.0)漂移 ≤1hp;
    - 跨 run 配对伪影哨兵:max |Δ| ≤ 20 且无负值——批㉗ F4 的
      +27~+61/−2 形态若在重生成后涌现,先查生成器 run 分组/语料
      接管段,不当作真值入锚;
    - supply 池语料零样本(标签未见),非空时同判。

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
        if nt == 'reward' and len(vals) < REWARD_POOL_MIN_N:
            out.append(f'reward n={len(vals)}<{REWARD_POOL_MIN_N}'
                       f'(分布证据不足)')
        if abs(mean - REWARD_POOL_TRUTH_MEAN) > REWARD_POOL_DRIFT_MAX:
            out.append(f'{nt} 均值{mean:+.2f} 距语料真值'
                       f'{REWARD_POOL_TRUTH_MEAN:+.1f} 漂移>'
                       f'{REWARD_POOL_DRIFT_MAX}hp')
        if max(vals) > REWARD_POOL_MAX_ABS or min(vals) < 0:
            out.append(f'{nt} 域[{min(vals)},{max(vals)}] 越伪影哨兵带'
                       f'(0~{REWARD_POOL_MAX_ABS})——疑跨 run 配对伪影'
                       f'混入(批㉗ F4 形态),先核生成器 run 分组')
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


def check_boss_win_calibration(ledgers: list[list[dict]]) -> dict:
    """批⑪ F1 验收(boss 胜率校准;ADR-0277)。

    判据(判据表原文):300 局 boss 胜率 >0 且随 depth 单调。
    - 胜 = boss 轮 sim.delta ≥ 0(outcomes.killed 同极性);
    - 违规 ①:boss 轮存在但 0 胜(结构性恒败回归——胜分支失效);
    - 违规 ②:可信深度桶(n≥5)间胜率随深度递减(胜率=f(成型度)
      且成型度与板深正相关 → 聚合胜率应单调不减;n<5 薄桶不判,
      声明数据边界)。
    """
    wins = tot = 0
    by_depth: dict[int, list[int]] = {}
    for rows in ledgers:
        for row in rows:
            s = row.get('sim') or {}
            if s.get('node') != 'boss':
                continue
            dep = s.get('depth')
            win = 1 if (s.get('delta') or 0) >= 0 else 0
            wins += win
            tot += 1
            if dep is not None:
                b = min(int(dep) // _POOL_DEPTH_BUCKET_W, 5) \
                    * _POOL_DEPTH_BUCKET_W
                by_depth.setdefault(b, [0, 0])
                by_depth[b][0] += win
                by_depth[b][1] += 1
    issues: list[str] = []
    if tot > 0 and wins == 0:
        issues.append(f'boss {tot} 轮 0 胜(结构性恒败回归,'
                      f'ADR-0277 胜分支失效)')
    ok = sorted((b, w, n) for b, (w, n) in by_depth.items() if n >= 5)
    for (b1, w1, n1), (b2, w2, n2) in zip(ok, ok[1:], strict=False):
        if w2 / n2 < w1 / n1:
            issues.append(
                f'深度桶{b1} 胜率{w1 / n1:.2f} > 桶{b2} '
                f'{w2 / n2:.2f}(胜率随深度应单调不减)')
    return {'violations': len(issues), 'boss_rounds': tot,
            'boss_wins': wins, 'issues': issues[:5]}


def check_formation_hp_coupling_sentinel(ledgers: list[list[dict]]) -> dict:
    """批⑪ F2 验收哨兵(成型→hp 价值链;ADR-0277)。

    判据(判据表原文):e≥2 局(任一轮 rung≥2)与未达局的 final_hp
    差——win 侧校准落地前恒≈0(批⑪ 实测 26.9 vs 26.0,零耦合);
    落地后应显著为正,否则校准失败。违规 = 双侧都有局且差 ≤0
    (成型局不比未达局活得久 = 价值链仍断)。
    小批护栏(ADR-0286):任一侧 <5 局 = 均值噪声主导,只披露不
    判定(CI smoke n=25 曾以 formed_n=2 的 −0.35 假红;真批次
    n≥300 两侧几十局起,护栏不削判定力)。
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
    small_n = formed and unformed and min(len(formed), len(unformed)) < 5
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


# 批⑩ 检查项 anchor_registry_n300:基线锚登记制——engines2/recipe5/
# avg_hp 等锚一律 n=300 口径登记(池指纹必附),n=60 值只作快速回归
# 哨兵。数值演进链:ADR-0276/0277(merge+win 校准)→ ADR-0279
# (battle rung 分桶)→ ADR-0284(商店槽消费,批㉒ F3 波及:成型类
# 指标回落到真实供给口径——旧值含幻影槽超买水分,新旧对照表进
# ADR-0284)→ ADR-0292(reward/supply Δ池采样 + 池数据增长
# 2026-08-23 晚批语料,battle 桶增样 r0 26→40/r1 24→31;换锚主因
# = 池数据增长,**采样语义本身 A/B 差 0.85hp 在分辨率底 ±2.80 内**,
# 归因分解见 ADR-0292 回归验证节)。
ANCHOR_REGISTRY_N300: dict = {
    'pool_fingerprint_prefix': '066c41856dd5d4f5',
    'recorded': '2026-08-24(ADR-0292 reward/supply Δ池采样批,'
                'n=300,seed 0-299)',
    'metrics': {
        'engines2_by_r6': 0.407,     # 旧 0.237(ADR-0284);池增长侧
        'avg_final_hp': 33.98,       # 旧 29.25
        'hp_ge_60': 0.127,           # 旧 0.047(向实机 32% 收敛中)
        'battle_losses_le_2': 0.127,  # 旧 0.073
        'recipe5_by_r6': 0.713,      # 旧 0.533
        'avg_refreshes': 4.003,      # 旧 3.943
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
