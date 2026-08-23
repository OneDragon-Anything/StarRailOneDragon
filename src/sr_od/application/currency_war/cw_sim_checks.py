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


# 批量内嵌检查集(分布级;r371b 后冷启动门 sim 内可达,局49
# 检查升级进批量——真实 sim 批次自动扫)
_BATCH_CHECKS = {
    'ledger_consistency': check_ledger_consistency,
    'coldstart_direction': check_coldstart_seed_squander,
    'deploy_fills_cap': check_deploy_fills_cap,
    'equip_worn_in_battle': check_equip_worn_in_battle,
    'no_component_equipped_p1': check_no_component_equipped_p1,
    'levelup_interest_engine_gate': check_levelup_interest_engine_gate,
}


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
