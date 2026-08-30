"""账本基础不变量与装备/bench 族检查(DESIGN §4.2 ledger 段,分包期6 拆分)。"""

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

    指纹:开局轮后(plane1 r2-r9,首轮系统卡未定排除)deployed
    数 < cap 且**围栏认可件未上 ≥2**(= 账本统一口径
    ``sim.deploy_lag_units``,补部署后重放围栏的残余可上件数,
    W716 设计 §四-2:skip/非 skip 轮统一计算)——r387 修前形态
    (配方围栏无条件拦散牌,cap=3 只上 1 人空槽白丢血)。r390
    执行层代理落地后 sim 内可达(deployed=真实围栏输出);变异
    探针实证:关 cap_roomy 守卫 → loss≤2 0.017→0.117 涌现
    (本检查=该差异的常态化拦截)。

    窗口口径:原 r2-r4 是 ADR-0253 时代的窗口先验,W716 F1 实证
    欠载形态系统性发生在 r4-r8(合成/换阵密集期;W714 三例全在
    旧窗外)→ 扩到 P1 全段 r2-r9。

    「有货」口径单一源(W748/W767 两波归因收敛):原「非在场同名
    副本」计数是**围栏判据外的近似**——跨线散牌被配方底线/非
    roomy 规则合法 held 时(换阵过渡期,643567 r5-r8 四轮连锁
    取证:lag=0 而旧口径可上货 ≥3)会误报;改吃 ``deploy_lag_units``
    (同一围栏纯函数的认可残余),检查器与部署行为零口径差。

    边界:**差 1 以内的贴 cap 不报**(配方围栏+cap 紧张是合法
    形态——r387 修的是「富余仍拦」);**在场同名素材/保留集件
    不算「有货」**(r404-A2 + W748 收窄:素材交围栏 dedup,天然
    不进 lag);**跨轮持续性门**(连续 2 轮才报):单轮差 2 常是
    「买了还没重新部署」的过渡态(game14 实证:r2 4/6→r3 6/6);
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
        if not (2 <= rn <= 9):
            continue
        st = row.get('state') or {}
        deployed = st.get('deployed')
        cap = st.get('cap')
        if deployed is None or not cap:
            continue
        # 「有货」= 围栏认可件未上(账本统一 lag 口径;见 docstring
        # W748/W767 口径单一源裁决)——旧「非在场同名」计数废弃
        lag = int((row.get('sim') or {}).get('deploy_lag_units') or 0)
        if lag < 2:
            continue
        if len(deployed) < cap - 1:
            _short_rounds.append((rn, len(deployed)))
    for (a, da), (b, db) in zip(_short_rounds, _short_rounds[1:],
                                strict=False):
        if b - a == 1 and db <= da:   # ADR-0260 增长豁免
            out.append(
                f"p1r{a}-r{b}: deployed 连续 ≤cap-2"
                f"(围栏认可件未上,围栏系统性拦截空槽——r387 修前形态)")
    return out



def _normalize_buy_reason(reason: str) -> str:
    """买入 reason 归一化(迁移审计 w43(git 历史) leader 裁决 4)。

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
            # d2_ 前缀归一化(原 2026-08-24 leader 核实;迁移审计 w48(git 历史) 裁决 4 起
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

    边界:deployed 空(没人可穿)不报;**基础件(RESERVED_
    COMPONENTS)不计入「owned 非空」**——基础件可合法留 owned(锁线
    合成备料/囤积 ADR-0391/配对守卫拦下的危险配对件;P1 穿着已合法化,
    ADR-0265 增补),owned 全基础件且守卫拦下时 equipped 空合法;
    其余工具类(不可穿)的判定交由 equip_allocation 语义(不可穿
    件不会进 equipped,也不会被移出 owned——按 owned 余量判,工具
    留 owned 是合法)。
    近似:owned>0 且 equipped=0 且 deployed>0 连续 2 战斗轮 → 报
    (工具误报由 owned 名单含工具的概率压低,后续可精化)。
    """
    from sr_od.application.currency_war.data.cw_synthesis import (
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
    """升级授权依据判据(`w131_a2n_arm/` 重定义,`w123_b_arm/` §5.2;ADR-0354;旧 ADR-0266/r406 指纹;
    迁移审计 w255(git 历史)/ADR-0410 static_ev 并入合法面)。

    **判据(重定义后)**:违规 = lv≥5(追级段)的 LevelUp 发生在时点金
    (本轮首波金,=收入后花销前)<50 **且授权依据 ∉ {pop_slot, dp,
    static_ev}**。授权依据 = sim 账本 LevelUp 行的 ``auth`` 键
    (LevelUp.auth_basis 观测字段,arbiter 升级门/remediation 补偿臂放行
    时写入,单一源=``ev.levelup_ev_basis``)。

    重定义动机(`w123_b_arm/` §3.3/§5.2):旧判据「金<50 且未曾满息即违规」把
    [33] 人口位(`w123_b_arm/` 实测 378 违规中绝大多数,`w126_b_arm/` 后 206)的合法
    <50 升级全数计违规——授权语义(迁移审计 w119(git 历史)/ADR-0347)落地后,判据应读
    授权依据而非金阈值。合法放行面:① pop_slot([33] 人口位:cap 满∧
    bench 有等待上场的目标件)、② dp(DP 花费授权,平台未破);
    ③ static_ev(静态 EV 平台账)——迁移审计 w255(git 历史) 前不在白名单(当时该臂花后
    <50 帧量级 0-1,保守计违规);**迁移审计 w255(git 历史)/ADR-0410 起并入**:boss 窗
    升级禁令删除后,static_ev 臂成为末窗升级的主授权臂(升级是否做=
    EV 总账问题,[32] 节点无关定调),继续计违规则系统性误报该合法面。
    无 auth 键/空值 = 无授权依据(default 栈旧调用/未过账路径)→ 违规
    ——本守卫的退化检测面(授权观测缺失)不受影响。

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
                    and basis not in ('pop_slot', 'dp', 'static_ev'):
                out.append(
                    f"p1r{row.get('round_num')} LevelUp 时点金 {gold0}<50"
                    f" 授权依据={basis or '(空)'}(lv{prev_level}"
                    f" 无授权依据——ADR-0354 违规)")
        prev_level = (row.get('state') or {}).get('level') or prev_level
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
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
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



def check_overflow_gold_zero_buy_streak(rows: list[dict]) -> list[str]:
    """迁移审计 w96(git 历史) 溢出金断买(迁移审计 w93(git 历史) 根因回灌;[17] >50 溢余该花;违规型)。

    判据:位面1 内连续 ≥2 个决策轮金 >50 且零买入(BuyCard)——
    金趴在 50 上方不动 = [17]「>50 的每一分都该花」被违反。升级
    (LevelUp)也算花金,有升级的轮不计数(金在滴漏不算冻结);
    [32] boss 轮 LevelUp 禁令辖内的轮照常计数(boss 轮该花在买牌/
    装备上,断买仍违规)。迁移审计 w93(git 历史) 病例:run_20260825_130151 r7-r9 金
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
    """自由批(bench 满不买非合成牌;0 容忍;ADR-0283 守卫的账本锁)。

    判据(设计表原文):bench≥上限 时不再输出非合成 BuyCard——现状
    (设计时)655 次;上限真值已核(BENCH_CAPACITY=9,cw_state
    design doc 实测)→ 锁 0。ADR-0283 超容买守卫落地后 BuyCard
    动作只在该轮容量允许时出现。ADR-0453/`w566_sim_guard/` 语义收窄:满栏
    **合成买**(merge_buy_completes)已合法执行、照常入账本——本
    检查的容量近似(下方公式含 2×merges)自动豁免其席位消耗,无
    需改判据;bench_full_skipped_buys 只计非合成拒买。

    容量口径(近似声明):期初 bench = 上一轮末 bench;本轮可买
    上限 = 9 − 期初 + 本轮卖出数 + 2×本轮 merges(3合1 每次腾
    2 席;守卫在执行层逐笔判,账本只能轮末重放近似)+ 本轮 bench
    腾位数(DeployMove 上阵 + applied CompTransaction 的
    bench_delta 披露[执行点真值,迁移审计 w101(git 历史) 涌现修正]:过渡型板面轮内
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
                # 迁移审计 w101(git 历史):applied 事务的 bench 净腾位(执行点真值
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
    from sr_od.application.currency_war.kernel.cw_state import (
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
    P1 穿着已合法化(ADR-0265 增补:穿戴可逆,简易件默认穿)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
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
    """批㉘ F1(ADR-0287)·重放语境冻结(W652 §5 处置①):漏上归 0 锁。

    判据边界(W678 围栏残留调查销案):满板(cap 满)下围栏 hold 目标件是
    设计行为——同名去重/r288 列车让位/cap 硬约束三条路径均有设计出处
    (cw_deploy_logic.select_deployments 终段循环),「围栏 hold」本身
    不计为漏上,本检查只盯「围栏认可却未执行」。

    判据:每轮账本 sim.deploy_lag_units > 0 = 违规。残余语义(冻结后)
    = 「**行动语境**下仍有围栏认可件未上」——重放趟吃真部署趟行动前
    的 board/deployed/bench 快照,与真趟同输入同源围栏,不再因本轮
    自身部署翻转围栏「成对」判据而产生口径过判(W652 取证:seed
    630027/630035 r6 的 lag=2 帧在冻结后判 0)。>0 = 部署时序回归轮首
    序(重构再犯)或围栏在行动语境下漏上可上件。
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
    样本核真后更新 engine_p1.HP_UPPER_BOUND 与本检查的同步镜像
    (检查模块不 import cw_sim,依赖方向纪律;值漂移由双向锁暴露)。
    """
    cap = 100   # 同步自 engine_p1.HP_UPPER_BOUND(单一源在 sim;镜像纪律)
    out: list[str] = []
    for row in rows:
        hp = row.get('hp')
        if hp is not None and hp > cap:
            out.append(
                f"p1r{row.get('round_num')}: hp={hp}>{cap}"
                f"(上界钳制回归/真值已改未同步——批㉘ F6,ADR-0287)")
    return out



def check_hp1_dead_end_candidate(rows: list[dict]) -> list[str]:
    """迁移审计 w120(git 历史) P9(死局锚;run 监控侧标记):HP=1 ⟺ 0hp 保底已耗尽 ⟹
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
    from sr_od.application.currency_war.data.cw_equipment_data import (
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
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIPMENT_ROSTER,
    )
    from sr_od.application.currency_war.kernel.cw_events import _EQUIP_VALUE
    stale = sorted(n for n in _EQUIP_VALUE if n not in EQUIPMENT_ROSTER)
    if not stale:
        return []
    return [
        f"价值表死名 {stale}(不在 EQUIPMENT_ROSTER;"
        f"ADR-0294 件2 采样过滤静默剔除+生产侧恒 0 分——批㉛ F2 待清偿)"]



def check_equip_supply_wear_closure(rows: list[dict]) -> list[str]:
    """批㉜ 检查项(供给面-穿戴面耦合锁):非保留件获取后必须上过身。

    判据:本局经供给获取(owned∪equipped 首现口径)的装备名,凡不在
    cw_synthesis.RESERVED_COMPONENTS(基础件可合法留 owned——锁线合成
    备料/囤积原则 ADR-0391/配对守卫拦下的危险配对件)者,局内必须至少
    上身一次——前提是本局有过部署(board 非空
    的轮行存在)。违规 = 价值面(decide_supply 给分选入)与穿戴面
    (equip_allocation 放置)脱钩:装备被高分选中却永远躺在 owned
    (批㉜ 锚 n=100 基线:非保留件获取/上身 1:1,0 违规;蓄能帆
    入池 12 局 12 上身)。
    """
    from sr_od.application.currency_war.data.cw_synthesis import (
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

    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIPMENT_ROSTER,
    )
    from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
    from sr_od.application.currency_war.kernel.cw_events import _EQUIP_VALUE
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

    ADR-0312(迁移审计 w50(git 历史)):口径与 ``cw_state._recount_board`` 同形 = **全集 +
    星徽装备贡献**——per-unit 标签经 ``cw_bond_equips.unit_bond_tags``
    (与 cw_state/cw_observation 三侧同一函数,非镜像复制;检查模块
    不 import cw_sim/cw_state 的依赖方向纪律不变,消费的是更底层的
    口径单一源模块)。值漂移由双向锁暴露,同 HP_UPPER_BOUND 镜像纪律。"""
    from types import SimpleNamespace

    from sr_od.application.currency_war.kernel.cw_bond_equips import unit_bond_tags
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
    - **rejected** 显式动作**不**占显式通道(迁移审计 w65(git 历史)/ADR-0323:被拒不消耗
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



def check_refresh_roll_cap_frame(ledgers: list[list[dict]]) -> dict:
    """刷新预算帽披露(批级):普通车道轮级刷新数 vs REFRESH_ROLL_CAP。

    语义依据(单一源 = cw_economy.REFRESH_ROLL_CAP(kernel 桶,期 0b 下沉),
    refresh_ev_budget 预算式的授权刷数上界 min(帽,溢余/刷价))。
    **披露型,批级聚合入口消费,不作逐局归零锁**:决策语义是逐段
    重决策(刷后见新店再裁),每段各自重读预算,轮级累计刷新数自然
    可越帽——账本轮行无法重构段界,「单决策帧越帽」与自然多段行为
    在账本上同构,故本项只出计数披露供决策层收权批判读;真正的硬
    不变式在定向车道局帽(directed_refresh_game_cap_lock,在
    _BATCH_CHECKS)。车道口径:轮行 sim.dir_refreshes(cw_sim 轮末
    对 session 局级累计计数器取差值)= M-A 定向车道执行数,先扣除;
    历史批次无此键按 0 扣。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        REFRESH_ROLL_CAP,
    )
    over_frames = 0
    max_ordinary = 0
    for rows in ledgers:
        for row in rows:
            acts = row.get('actions') or []
            total = sum(1 for a in acts
                        if a.get('__type__') == 'RefreshShop')
            if total <= 0:
                continue
            directed = int((row.get('sim') or {}).get('dir_refreshes') or 0)
            ordinary = max(0, total - directed)
            max_ordinary = max(max_ordinary, ordinary)
            if ordinary > REFRESH_ROLL_CAP:
                over_frames += 1
    return {'violations': 0, 'frames_over_cap': over_frames,
            'max_ordinary_per_round': max_ordinary,
            'cap_const': REFRESH_ROLL_CAP}



def check_directed_refresh_game_cap(rows: list[dict]) -> list[str]:
    """定向刷新局帽:M-A 定向车道全局执行数 > directed_refresh_game_cap。

    语义依据(单一源 = kernel.cw_registry 的
    ``directed_refresh_game_cap``):M-A 末窗定向刷新授权的局级代价
    上界(ADR-0409 预算式 min(per_round, 局帽−已耗),授权点在
    arbiter 刷新收尾;结构上限推导:合资格轮 ≤2 × per_round 2 <
    帽,超越 = 授权链失效)。数据源 = 轮行 sim.dir_refreshes
    (cw_sim 轮末差值归因,见 check_refresh_roll_cap_frame 车道口径)。
    """
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    cap = DEFAULT_REGISTRY.directed_refresh_game_cap
    total = sum(int((row.get('sim') or {}).get('dir_refreshes') or 0)
                for row in rows)
    if total > cap:
        return [f'定向刷新全局 {total} 次 > 局帽 {cap}'
                f'(directed_refresh_game_cap,M-A 授权链失效)']
    return []




