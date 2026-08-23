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


_BATCH_CHECKS = {
    'ledger_consistency': check_ledger_consistency,
    'coldstart_direction': check_coldstart_seed_squander,
    'deploy_fills_cap': check_deploy_fills_cap,
    'equip_worn_in_battle': check_equip_worn_in_battle,
    'no_component_equipped_p1': check_no_component_equipped_p1,
    'levelup_interest_engine_gate': check_levelup_interest_engine_gate,
    'no_same_round_buy_sell': check_no_same_round_buy_sell,
    'bench_full_deadlock_probe': check_bench_full_deadlock_probe,
}


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
    """
    out: list[str] = []
    for nt, buckets in sorted(pool_map.items()):
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


# --- 批⑩/批⑪ 检查项(2026-08-24 裁决落地;ADR-0276/0277) ---------
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
    violations = 1 if (diff is not None and diff <= 0) else 0
    return {'violations': violations, 'formed_n': len(formed),
            'unformed_n': len(unformed),
            'formed_hp': round(sum(formed) / len(formed), 2) if formed else None,
            'unformed_hp': round(sum(unformed) / len(unformed), 2) if unformed else None,
            'diff': round(diff, 2) if diff is not None else None}


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
    """批⑨ 设计/批⑩ 追加数据(末金校准;ADR-0276)。

    判据:sim 末轮金均值 vs 实机 24.3 的比值——3合1 建模落地后
    重测此比值为收敛判据(批⑩ F5:sim 52.5 = 2.2×,「sim 虚高
    1.6-2.3×」形态)。违规 = 比值 > 1.5(买通道死锁/滞留金虚高
    未恢复判读力)。
    """
    golds = [rows[-1].get('gold') for rows in ledgers if rows]
    golds = [g for g in golds if g is not None]
    avg = sum(golds) / len(golds) if golds else 0.0
    ratio = avg / REAL_AVG_ENDGOLD if golds else 0.0
    return {'violations': 1 if ratio > ENDGOLD_RATIO_MAX else 0,
            'sim_avg_endgold': round(avg, 2),
            'real_avg_endgold': REAL_AVG_ENDGOLD,
            'ratio': round(ratio, 2)}


# 批⑩ 检查项 anchor_registry_n300:基线锚登记制——engines2/recipe5/
# avg_hp 等锚一律 n=300 口径登记(池指纹必附),n=60 值只作快速回归
# 哨兵。数值为 ADR-0276/0277(merge+win 校准)落地批 n=300 实测。
ANCHOR_REGISTRY_N300: dict = {
    'pool_fingerprint_prefix': 'e19afdfa4173077e',
    'recorded': '2026-08-24(ADR-0276/0277 落地批,n=300,seed 0-299)',
    'metrics': {
        'engines2_by_r6': 0.277,     # 旧栈 0.083(merge 前;批⑩ F1 锚)
        'avg_final_hp': 28.81,       # 旧 26.03;win 校准 +4 抬升
        'hp_ge_60': 0.04,            # 旧 0.017(boss 恒败钉死解除)
        'battle_losses_le_2': 0.033,  # 旧 0.027
        'recipe5_by_r6': 0.62,
        'avg_refreshes': 1.11,       # 旧 1.61(merge 后买通道活,早刷减少)
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
