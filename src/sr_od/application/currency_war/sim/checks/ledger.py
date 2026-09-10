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
    - **T-153 迁移(C1,ADR-0593)**:身份断言型自述(bridge_seed/engine)
    降级为「自算复核通过才豁免」——复核 = classify_buy 同源身份自算
    (channel 披露优先,见 selfcalc.buy_identity),失配 = 可疑项条目
    (自报词表绕过面显形,ADR-0593 §C1)+ 不豁免;其余通道
    语义自述与无 channel 旧账本 = 不可复核,豁免照旧(兼容先例 =
    ADR-0589 无键回退);
    - **仅 v2 栈账本适用**:生产配置 strategy_id=
      decision_v2(旧 line_v2 随 ADR-0336 已删)时实机 decisions.jsonl
      同样适用(BuyCard.reason 是共享 dataclass,生产遥测同带标签);
      **default 栈**(买牌走 cw_plan,reason='plan')不辖于 r368 门,
      跑此检查必误报——生产侧按局 strategy_id/actions reason 词表
      判栈后选择。
    """
    out: list[str] = []
    from sr_od.application.currency_war.sim.checks import selfcalc as _sl
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
                # T-153 迁移(C1/ADR-0593):身份断言型自述降级为自算复核
                # 通过才豁免(兼容策略见 docstring;失配→可疑项+不豁免)。
                _identity = _sl.buy_identity(row, a) \
                    if reason in _sl.COLDSTART_IDENTITY_CLAIMS else reason
                if _identity != reason:
                    card = a.get('card') or {}
                    out.append(
                        f"p{row.get('plane')}r{row.get('round_num')} "
                        f"可疑项(冷启动身份失配): 买 {card.get('name')}"
                        f" 自报 reason={reason} 自算身份={_identity}"
                        '——请裁决: 门内放行 / 改标绕门(ADR-0593)')
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
    static_ev, m3_batch}**('p2_auth_xp' 臂已随位面 2 支出授权定谳清理删除,
    ADR-0492:W785 sink 分解 XP 0 帧/0 金)。授权依据 = sim 账本 LevelUp 行的 ``auth`` 键
    (LevelUp.auth_basis 观测字段,放行时写入)。

    重定义动机(`w123_b_arm/` §3.3/§5.2):旧判据「金<50 且未曾满息即违规」把
    [33] 人口位(`w123_b_arm/` 实测 378 违规中绝大多数,`w126_b_arm/` 后 206)的合法
    <50 升级全数计违规——授权语义(迁移审计 w119(git 历史)/ADR-0347)落地后,判据应读
    授权依据而非金阈值。合法放行面:① pop_slot([33] 人口位:cap 满∧
    bench 有等待上场的目标件)、② dp(DP 花费授权,平台未破);
    ③ static_ev(静态 EV 平台账)——迁移审计 w255(git 历史) 前不在白名单(当时该臂花后
    <50 帧量级 0-1,保守计违规);**迁移审计 w255(git 历史)/ADR-0410 起并入**:boss 窗
    升级禁令删除后,static_ev 臂成为末窗升级的主授权臂(升级是否做=
    EV 总账问题,[32] 节点无关定调),继续计违规则系统性误报该合法面;
    ④ m3_batch(mandate_v1 换核后的 M3 批量授权臂)——换核批(ba1176c6
    里程碑)漏更本白名单致预存红,定谳批补入:m3_batch 发射前置 =
    arm1_existence(板满∧等待件∧边际贡献>0,= [33] 人口位语境,与
    pop_slot 同语义的现役核表述)∧ spend_unified(P48 整买纪律,一次
    买齐到下一级)∧ level_spend_blocked 让位(dd-034 危机带停付)∧
    lv9_stop——授权强度不低于旧三臂,出处 = strategy-docs
    02_mandate_layer.md §3 M3 行 / ADR-0518(单动作实施,shop.py M3
    发射位);
    无 auth 键/空值 = 无授权依据(default 栈旧调用/未过账路径)→ 违规
    ——本守卫的退化检测面(授权观测缺失)不受影响。

    近似声明(承旧):①升级前等级用**上一轮账本 level**(轮内升级
    完成会抬高本行 level,prev_level 才是购买时的等级;首轮 prev=3);
    ②时点金 = shop_waves 首波 gold(决策发生在收入后/花销前);
    ③授权依据是**放行时点的臂名快照**(动作对象携带),检查器不复
    判——重演需要 cost/val 等决策期中间量,账本不携(声明数据边界);
    gold≥50 的升级不报(与旧判据同:息平台在场,无追级风险面)。

    T-153 迁移(C2/ADR-0593):白名单降级为「自算复核通过才豁免」——
    pop_slot/m3_batch(含分键后缀)的可核前置(板满∧等待上场名册件)
    经 selfcalc.levelup_prereq_review 现算(执行点披露键优先,行末
    近似回退),失配 = 可疑项条目(自报臂名 vs 自算前置)+ 不豁免;
    dp/static_ev 腿需决策期中间量不可机械复算 = unverifiable,豁免
    照旧(语境条目交复盘检测器 D3)。预算闸辖域缺口(C3)由 D3 前置
    失配检测补位(闸判据本体保留机械检查器,ADR-0593 §4.3)。
    """
    out: list[str] = []
    from sr_od.application.currency_war.sim.checks import selfcalc as _sl
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
            # 白名单 = 前缀匹配:m3_batch 带触发臂分键后缀(arm1/arm0/pop,
            # 达标/升级授权三臂可归因分键),禁回退精确等值(分键后缀漂移
            # = 白名单误判违规,污染 ADR-0354 验收锚)
            _chasing = prev_level >= 5 and gold0 is not None and gold0 < 50
            _whitelisted = (basis in ('pop_slot', 'dp', 'static_ev')
                            or basis == 'm3_batch'
                            or basis.startswith('m3_batch:'))
            if _chasing and not _whitelisted:
                out.append(
                    f"p1r{row.get('round_num')} LevelUp 时点金 {gold0}<50"
                    f" 授权依据={basis or '(空)'}(lv{prev_level}"
                    f" 无授权依据——ADR-0354 违规)")
            elif _chasing and (basis == 'pop_slot'
                               or basis == 'm3_batch'
                               or basis.startswith('m3_batch:')):
                # T-153 迁移(C2/ADR-0593):自算可核前置,失配显形。
                if _sl.levelup_prereq_review(row, a, prev_level) \
                        == _sl.REVIEW_MISMATCH:
                    st = row.get('state') or {}
                    out.append(
                        f"p1r{row.get('round_num')} 可疑项(追级授权前置失配):"
                        f" LevelUp 自报授权={basis} lv{prev_level} 时点金"
                        f" {gold0}<50;自算前置: 板满="
                        f"{a.get('dec_board_full')} 待上场="
                        f"{a.get('dec_bench_wait_member')}"
                        f"(cap={st.get('cap')})"
                        '——请裁决: 授权成立 / 谎报臂名(ADR-0593)')
        prev_level = (row.get('state') or {}).get('level') or prev_level
    return out


def check_levelup_budget_gate(rows: list[dict]) -> list[str]:
    """P72 (3) 全段预算闸检查(ADR-0576;生产闸判据的检查器镜像,
    绕闸升级 = 违规)。

    判据镜像(生产 = criteria/levelup.levelup_budget_gate,P72 全段形):
    m3_batch 臂升级批**逐击**判定——

    ``g − s ≥ 10·τ(g) + ρ + Σ预留``

    g = 该击决策帧现读金(重放),s = 该击起同轮 m3 批实际余量,
    τ = interest 档数分量,ρ/Σ预留 = r2_card_reserve 同参同值(闸
    口径两分量同值,退化 10·τ(g)+2ρ)。违规 = 存在 m3 击其生产闸
    本应拒绝却已发射(闸被绕过/判据漂移);生产闸拦下的批零发射,
    天然无违规。

    三处口径对齐(T-79 验收线 / T-93 三分类修复):
    - **g\\* 单一源**(签名 B 假阳性根因修复):息档 floor 的 cap =
      息帽档数 cap_resolved 缺省口径(kernel cw_economy 单一源),
      **禁读 ``state.cap``**——那是部署人口 cap(=等级+宝钻)同名
      异义族,T-93 期当息帽推 g*=40~90 即假阳性源(4 处);
    - **金基准 = 决策帧现读金**(签名 A 真洞的观测面修复):自
      waves[0] gold 逐动作重放净额(买/刷/升扣、卖入账;动作行
      cost/income 单一源),非首波 g0——「义务买牌先花 + 逐击发射」
      的线下潜行形态在 g0 口径下结构性漏报(方案设计 §2 D2);
    - **ρ 名册**(D3):生产 k_members 同源解析——过渡配方标签
      ('过渡配方·A+B')走 kernel cw_intention.pair_target_comp,
      普通线名走 get_comp,成员 = predicates.line_members(core∪
      shared);禁名册自造(旧 faction 全集口径在过渡配方标签上
      解析为空名册,ρ 恒 0)。

    豁免镜像(与生产闸同谓词同帧判定,P72 §2.5 合取序禁分裂):
    - ~~reward/supply 节点~~(**已退役**,T-115 对齐 ADR-0580:原 [16]②
      「买经验合法」条目已删除,奖励节点 = 升级抑制对象;生产闸判据
      本身节点无关,镜像删除节点型 skip 后对闸的镜像更忠实——奖励帧
      m3_batch 绕闸 = 违规可见,扑满环境帧经 M3 闸链的合法批照常通过);
    - **ALL IN 位面末 boss 节**(R=0 机会成本恒零,生产闸同支豁免)
      ——位面长度 = 本 run rows 现推 max(round_num)(生产真值 =
      session.plane_node_table,账本不携;已完位面精确,P3 自适应
      同构);
    - **支A 兑现链**(板满 ∧ bench 2★,生产同步锚对谓词镜像);
      支B(ΔV_band 数值完备账)生产侧本批不落码(P39 接缝,
      ADR-0576 §判据),镜像侧同缺,两侧一致。realize 判定按击读
      引擎 LevelUp 执行点披露的 dec_board_full/dec_bench_2star
      (决策帧真值,T-135:行末快照在「帧内合成 2★→升级批→上板」
      序列下 bench 已无 2★,恒误报绕闸;定谳 = ADR-0589;无披露键
      账本回退行末近似,见近似声明);

    近似声明(与既有检查器同款口径,偏差方向逐条标注):
    - 升级前等级用上一轮账本 level(轮内升级完成会抬高本行);
    - 板满判定 cap 按轮内升级量回退(level+常数线性近似,宝钻语境
      ±1 量级窗口);bench/deployed 行末快照仅辖**无披露键账本的
      支A 回退判定**(轮内先升后买/上板的漂移窗口 ±1 件双向——
      T-135 起有披露键的击走决策帧真值,该窗口不再辖现役 sim 批);
    - 击序余量 s = 同轮 m3 击实际花费后缀和(生产 s =
      clicks_to_next_level 现读;轮内买牌 +4XP 令生产 s ≤ 本口径
      ——宽松向,不冤枉合法批);
    - 息帽 cap = 账本行覆写语境观测键解析(ADR-0598 兑现本检查器原
      预留义务):行携 ``sess_active_strategies``(轮末持卡快照,engine
      写端)→ ``aggregate_economy`` 聚合取 cap 覆写(None/0 判别语义 =
      kernel interest_cap_resolved 单点);键缺席(历史账本/无持卡局)
      → DEFAULT——历史账本在覆写语境下的旧读数仍带近似窗,只读不
      新产;无持卡局与 DEFAULT 同值,零行为差;
    - 逐击重放的动作净额:满栏合成买行携 count,净额按
      cost×count(与实际扣金差 ≤1 金的粒度窗口)。
    """
    from types import SimpleNamespace

    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    from sr_od.application.currency_war.kernel.cw_economy import (
        DEFAULT_INTEREST_CAP,
        interest,
        interest_cap_resolved,
    )
    from sr_od.application.currency_war.kernel.cw_intention import (
        pair_target_comp,
    )
    from sr_od.application.currency_war.kernel.cw_investments import (
        aggregate_economy,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.refresh import (
        r2_card_reserve,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
        line_members,
    )

    def _k_members(label: str) -> tuple[str, ...]:
        """生产 k_members 同源解析(单一源对拍,禁名册自造)。"""
        label = label or ''
        if label.startswith('过渡配方·'):
            comp = pair_target_comp(
                tuple(label.removeprefix('过渡配方·').split('+')))
        else:
            comp = get_comp(label)
        return line_members(comp)

    # 位面长度现推(ALL IN 镜像;账本不携 plane_node_table,run 内
    # 已完位面 max(round_num) = 真长)
    plane_len: dict[int, int] = {}
    for r in rows:
        p = r.get('plane')
        if p is not None:
            plane_len[p] = max(plane_len.get(p, 0), r.get('round_num') or 0)

    out: list[str] = []
    prev_level = 3
    for row in rows:
        st = row.get('state') or {}
        sim = row.get('sim') or {}
        level = prev_level
        row_lvl = st.get('level') or prev_level
        node = sim.get('node') or ''
        # 覆写语境 cap(行级观测键解析;ADR-0598):键缺席(历史账本/
        # 无持卡)→ DEFAULT,与 τ 旧钉值同值零漂移;键在 → 聚合覆写。
        _strats = row.get('sess_active_strategies')
        _cap = (interest_cap_resolved(
                    aggregate_economy(list(_strats)).interest_cap_override)
                if _strats else DEFAULT_INTEREST_CAP)
        # T-115 对齐(ADR-0580):原 reward/supply 节点型 skip 已退役
        #([16]② 删除,奖励节点 = 抑制对象),检查覆盖回归节点无关口径。
        actions = row.get('actions') or []
        waves = sim.get('shop_waves') or []
        g0 = waves[0].get('gold') if waves else None
        lv_pos = [i for i, a in enumerate(actions)
                  if a.get('__type__') == 'LevelUp'
                  and str(a.get('auth', '') or '').startswith('m3_batch')]
        if lv_pos and g0 is not None:
            # ALL IN 镜像(P72 §2.5):位面末 boss 节生产闸同支豁免
            is_allin = (node == 'boss' and (row.get('round_num') or 0)
                        >= plane_len.get(row.get('plane'), 0))
            if not is_allin:
                km = _k_members(row.get('target_comp') or '')
                bench = [SimpleNamespace(char_id=b.get('char_id'),
                                         star=b.get('star', 1) or 1)
                         for b in st.get('bench') or []]
                deployed = [SimpleNamespace(char_id=d.get('char_id'),
                                            star=d.get('star', 1) or 1)
                            for d in st.get('deployed') or []]
                rho = r2_card_reserve(km, bench, deployed,
                                      SimpleNamespace(level=level),
                                      level=level)
                # 支A 镜像·按击豁免(T-135,决策帧真值优先):引擎在
                # LevelUp 执行点披露的 dec_board_full/dec_bench_2star =
                # 发射帧支A 谓词输入(单动作架构 ADR-0517 下执行点状态 =
                # 发射帧状态),按击判定——行末快照在「帧内合成 2★→升级批
                # →轮末部署块当帧上板」确定性序列下 bench 已无 2★,旧口径
                # 恒误报绕闸(假阳定谳 = ADR-0589;谓词设计 =
                # ADR-0576 §2.5 支A 兑现链)。无披露键的账本(生产回放/
                # 历史批次)回退旧行末口径,整行同判(漂移窗口见近似声明)。
                lv_actions: list[dict] = [actions[i] for i in lv_pos]
                if all(isinstance(a.get('dec_board_full'), bool)
                       and isinstance(a.get('dec_bench_2star'), bool)
                       for a in lv_actions):
                    realize_by_click: list[bool] = [
                        bool(a['dec_board_full'])
                        and bool(a['dec_bench_2star'])
                        for a in lv_actions]
                else:
                    # 旧账本回退:板满(cap 按轮内升级量回退)∧ bench 2★
                    cap_dep = st.get('cap')
                    cap_dec = (cap_dep - (row_lvl - level)
                               if cap_dep is not None else None)
                    realize_row = (cap_dec is not None
                                   and len(deployed) >= cap_dec
                                   and any(b.star >= 2 for b in bench))
                    realize_by_click = [realize_row] * len(lv_actions)
                # 逐击余量(实际花费后缀和;缺 cost 行退化均摊)
                lv_costs = [a.get('cost') for a in lv_actions]
                s_total = (sim.get('spend') or {}).get('levelup') or 0
                if any(c is None for c in lv_costs):
                    per = s_total // len(lv_pos)
                    lv_costs = [per] * len(lv_pos)
                # 逐击决策帧金重放 + 闸式判定(支A 豁免按击短路)
                for j, idx in enumerate(lv_pos):
                    if realize_by_click[j]:
                        continue
                    gold_dec = g0
                    for a in actions[:idx]:
                        t = a.get('__type__')
                        if t == 'BuyCard':
                            gold_dec -= ((a.get('card') or {})
                                         .get('cost', 0) or 0) \
                                * (a.get('count') or 1)
                        elif t in ('RefreshShop', 'LevelUp'):
                            gold_dec -= a.get('cost') or 0
                        elif t == 'SellBench':
                            gold_dec += a.get('income') or 0
                    s_j = sum(lv_costs[j:])
                    tau = interest(gold_dec, _cap)
                    floor = tau * 10 + 2 * rho
                    if gold_dec - s_j < floor:
                        out.append(
                            f"p{row.get('plane')}"
                            f"r{row.get('round_num')} "
                            f"LevelUp 击{j + 1}/{len(lv_pos)} 批余 "
                            f"{s_j} 金,决策帧金 {gold_dec} < "
                            f"息档 floor {floor}"
                            f"(τ={tau}, ρ={rho}, g0={g0})——"
                            f"P72 (3a) 绕闸升级(ADR-0576)")
                        break
        prev_level = row_lvl
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
    **T3 同轮保留批扩豁免边(转化类卖出分键)**:ADR-0611 起按键分工判定
    (迁移期不并读零双源)——转化类豁免读
    convert_reason ∈ ``SELL_BENCH_CONVERT_REASONS``(M4 腾席唯一燃料
    放行 / 支付变现筹资,金转化成线成员/义务动作,非净零自旋;结构化
    证明键,值域收窄两类放行位);孤儿豁免读 sell_reason ∈
    ``cw_prep_actions.SELL_BENCH_ORPHAN_REASONS``(线账闭合孤儿清算,
    ADR-0591 §4 证明打标制;T-180 起与发射位登记门 SELL_BENCH_REASONS
    分离的独立闭集——登记门新增值不得静默放大豁免面,振荡零容忍)。
    豁免面按分键
    收敛,禁全开(缺省 '' 恒不豁免;reason 旧通道值不再放大豁免面)。
    键集单一源 = kernel/cw_state.SELL_BENCH_CONVERT_REASONS(镜像纪律
    同 XP_TO_NEXT_LEVEL:值漂移由双向锁暴露)。
    仅 v2 栈(line_v2/decision_v2)账本适用(default 栈 reason='plan' 的
    卖出语义不同,生产侧按 strategy_id 分栈后选择)。

    T-153 迁移(C4/ADR-0593):三连豁免全部降级为「自算复核通过才豁免」
    ——copy 复核收集语境(selfcalc.copy_collection_review:同轮同名≥2
    ∨购买前已持有)、engine_seed≥2 复核种子身份(selfcalc.
    seed_identity_review:引擎件∧购买时未持有)、转化类分键复核线成员
    (selfcalc.sell_line_membership_review:dec_sell_in_line 执行点披露,
    ADR-0591 §4 写端证明义务的检查端补位)。失配 = 可疑项条目 + 不豁免
    (按振荡 0 容忍判违);不可复核(旧账本无披露键)= 豁免照旧
    (兼容先例 = ADR-0589,避免一刀切翻旧案)。
    """
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        SELL_BENCH_ORPHAN_REASONS,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        SELL_BENCH_CONVERT_REASONS,
    )
    from sr_od.application.currency_war.sim.checks import selfcalc as _sl
    out: list[dict] = []
    # 净持有语境(复核基线;ADR-0593 后果.5(L2)):买入入集、卖出台账销账——
    # 「曾持有但中途已卖出」的名不再构成 copy 豁免的持有证据(封死
    # 「终身持有通行证」形态)。开局 bench 种子 = 首行末态扣除首行动作
    # 涉及名(首轮先买场景的 ±漂移窗口,与 check_buys_at_full_bench
    # 期初 bench 口径同款近似声明)。
    _held_net: set[str] = set()
    if rows:
        _row0_act_names = {(a.get('card') or {}).get('name')
                           for a in (rows[0].get('actions') or [])
                           if a.get('__type__') == 'BuyCard'}
        _st0 = rows[0].get('state') or {}
        _row0_held = {b.get('char_id') for b in (_st0.get('bench') or [])
                      if isinstance(b, dict)} | \
                     {d.get('char_id') for d in (_st0.get('deployed') or [])
                      if isinstance(d, dict)}
        _held_net = {n for n in (_row0_held - _row0_act_names) if n}
    for _row_idx, row in enumerate(rows):
        bought: list[str] = []
        _copy_names: set[str] = set()
        _seed_buys: dict[str, int] = {}   # 批⑩ F3 裁决(ADR-0276)
        _copy_round_buys: dict[str, int] = {}   # T-153(C4):收集语境判据
        _seed_acts: dict[str, list[dict]] = {}   # T-153(C4/C7):种子身份复核
        # 本轮前净持有快照(复核基线):本轮买入不污染、跨轮销账已生效——
        # r1买→r2卖→r3 copy 场景 r3 快照为空=谎报显形;r1买→r2 copy 卖
        # 场景 r2 快照含持有=合法第 2 份副本路径
        _held_before_round = set(_held_net)
        for a in row.get('actions') or []:
            if a.get('__type__') == 'BuyCard':
                _n = (a.get('card') or {}).get('name')
                _rs = _normalize_buy_reason(a.get('reason') or '')
                if _n and _rs == 'copy':
                    _copy_names.add(_n)   # 3合1 收集语境:让位豁免(复核面)
                    _copy_round_buys[_n] = \
                        _copy_round_buys.get(_n, 0) + 1
                    # ADR-0593 后果.5(L1):copy 买入 bought(纯「copy 买→同轮卖」对
                    # 由此可达复核分支——旧结构只挂标记不入集,该形态在
                    # 机械面整体不可达,申报「三连降级」言过其实)
                    bought.append(_n)
                elif _n and _rs == 'engine_seed':
                    _seed_buys[_n] = _seed_buys.get(_n, 0) + 1
                    _seed_acts.setdefault(_n, []).append(a)
                    bought.append(_n)
                elif _n:
                    bought.append(_n)
                if _n:
                    _held_net.add(_n)   # 净持有:买入入集
            elif a.get('__type__') == 'SellBench':
                _nm = a.get('name')
                # 净持有销账(ADR-0593 后果.5(L2)):所有卖出即时除名,不辖「是否
                # 同轮对」——跨轮 r1买→r2卖→r3 copy 买场景靠这里归零。
                _held_net.discard(_nm)
                if _nm not in bought:
                    continue   # 非同轮对:本检查(同轮买卖互斥)不辖
                _violation = (
                    f"p{row.get('plane')}r{row.get('round_num')} "
                    f"同轮买后卖: {_nm}"
                    f"(ADR-0267 买卖互斥违规)")
                if _nm in _copy_names:
                    # T-153 迁移(C4/ADR-0593):copy 豁免降级为自算复核
                    # 通过才豁免;失配 = 可疑项 + 不豁免(0 容忍恢复)。
                    if _sl.copy_collection_review(
                            _held_before_round,
                            _copy_round_buys.get(_nm, 0)) \
                            != _sl.REVIEW_MISMATCH:
                        bought.remove(_nm)   # 豁免照旧(每对只豁免一次)
                        continue
                    out.append(
                        f"p{row.get('plane')}r{row.get('round_num')} "
                        f"可疑项(同轮买卖分键失配): 卖 {_nm} 自报 copy"
                        f"(3合1 素材) 同轮同名 copy 买 "
                        f"{_copy_round_buys.get(_nm, 0)} 笔、购买时净持有="
                        f"{'是' if _nm in _held_before_round else '否'}"
                        f" 自算=无收集语境——请裁决: 合法让位 / 振荡"
                        '(ADR-0593)')
                    out.append(_violation)
                    bought.remove(_nm)   # 每对只报一次
                    continue
                # 批⑩ F3 裁决(ADR-0276):engine_seed 同名买入 ≥2
                # (同轮) = 3合1 素材收集语境,其同名卖出 = 合成冗余
                # 让位(与 copy 豁免同族),不报;单张买入即卖 = 振荡
                # (r408 主通道)仍 0 容忍。
                if _nm in _seed_buys and _seed_buys[_nm] >= 2:
                    # T-153 迁移(C4/C7/ADR-0593):收集语境份数照旧,
                    # 叠加种子身份自算复核(改标攻击面显形)。
                    if all(_sl.seed_identity_review(rows, _row_idx, _ba)
                           != _sl.REVIEW_MISMATCH
                           for _ba in _seed_acts.get(_nm, ())):
                        bought.remove(_nm)
                        continue   # 豁免照旧
                    out.append(
                        f"p{row.get('plane')}r{row.get('round_num')} "
                        f"可疑项(种子身份失配): 卖 {_nm} 自报 engine_seed"
                        f' 收集语境(同轮 ≥2) 自算=非引擎件/购买时已持有'
                        '——请裁决: 收集让位 / 改标振荡 (ADR-0593)')
                    out.append(_violation)
                    bought.remove(_nm)
                    continue
                # 转化类/孤儿豁免按键分工判定(ADR-0611;
                # 分支结构见函数 docstring「转化类卖出分键」段)
                _claim = ''
                _conv_key = a.get('convert_reason') or ''
                _orph_key = a.get('sell_reason') or ''
                if _conv_key in SELL_BENCH_CONVERT_REASONS:
                    _claim = _conv_key
                elif _orph_key in SELL_BENCH_ORPHAN_REASONS:
                    _claim = _orph_key
                if _claim:
                    # T-153 迁移(C4/ADR-0593):分键豁免降级——线成员
                    # 复核失配 = 可疑项 + 不豁免(键缺省/名册不可解析
                    # 豁免照旧)。
                    if _sl.sell_line_membership_review(row, a) \
                            != _sl.REVIEW_MISMATCH:
                        bought.remove(_nm)   # 每对只豁免一次,同报面语义
                        continue
                    out.append(
                        f"p{row.get('plane')}r{row.get('round_num')} "
                        f"可疑项(转化分键失配): 卖 {_nm} 自报分键="
                        f"{_claim} 自算=非当前线名册成员"
                        f"(dec_sell_in_line=False)——请裁决: 合法转化 / "
                        f'振荡 (ADR-0593;写端义务 = ADR-0591 §4)')
                    out.append(_violation)   # 失配不豁免:按振荡 0 容忍判违
                    bought.remove(_nm)
                    continue
                out.append(_violation)
                bought.remove(_nm)   # 每对只报一次
        # 同轮未消化的买入进净持有(跨轮复核基线;卖出已在上方销账)
        for _nm in bought:
            _held_net.add(_nm)
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

    T-153 迁移(C5/ADR-0593):ADR-0343 豁免降级为「自算成型复核通过
    才豁免」——复核 = engines_count 自算(单一源 = kernel
    cw_deploy_logic.engines_count,经 segments._seg_engines 适配器
    消费);自报停手 ∧ 自算未成型(engines<2) = 成型谎报形态
    (ADR-0593)→ 不断 streak(计入违规窗口);可疑项条目辖域收在
    本检查本职的溢金未泄轮(ADR-0593 后果.5(L5):非溢金轮的谎报只剥夺豁免,
    不产越辖条目,溢金语境外失配归 D2/seg 面);行无成型度可算键
    (旧账本无 board_factions/deployed)= 不可复核,豁免照旧。
    """
    from sr_od.application.currency_war.sim.checks.segments import (
        _seg_engines,
    )
    rid = rows[0].get('run_id', '?') if rows else '?'
    _suspects: list[str] = []
    streak = first_r = 0
    worst = worst_r = 0
    for row in rows:
        if (row.get('plane') or 1) != 1:
            continue    # 只辖 P1(金跨位面继承,P2+ 语义另裁)
        gold = row.get('gold') or 0
        spent = any(a.get('__type__') in ('BuyCard', 'LevelUp')
                    for a in row.get('actions') or [])
        _overflow_round = gold > 50 and not spent
        if row.get('formed_stop'):
            # T-153 迁移(C5/ADR-0593):自算成型复核通过才断 streak。
            _st = row.get('state') or {}
            if 'board_factions' not in _st and 'deployed' not in _st:
                streak = 0   # 旧账本无成型度键:不可复核,豁免照旧
                continue
            _engines = _seg_engines(row)
            if _engines >= 2:
                streak = 0   # ADR-0343:成型停手轮=合法零买,断 streak
                continue
            # ADR-0593 后果.5(L5):可疑项条目辖域收在本检查本职(溢金未泄轮);
            # 非溢金轮的谎报只剥夺豁免(不断 streak),不产越辖条目。
            if _overflow_round:
                _suspects.append(
                    f"p1r{row.get('round_num')} 可疑项(成型谎报): "
                    f'金 {gold} 零花费 自报停手=真 '
                    f'自算成型度={_engines}(<2)'
                    '——请裁决: 合法守息 / 谎报停手 (ADR-0593)')
            # 不豁免:落入下方 streak 计数(失配轮计入违规窗口)
        if _overflow_round:
            if streak == 0:
                first_r = row.get('round_num') or 0
            streak += 1
            if streak > worst:
                worst, worst_r = streak, first_r
        else:
            streak = 0
    if worst >= 2:
        _suspects.append(
            f'{rid}: P1 溢出金断买 {worst} 连'
            f'(r{worst_r} 起,金>50 零买零升级——[17] 溢余该花)')
    return _suspects



def check_streak_propagation_live(rows: list[dict]) -> list[str]:
    """sim_streak_propagation_live(观测态补齐哨兵,`w793_sim_enable_rerun/`)。

    判据:P1 段账本行 ``state.streak`` 恒非 None——结算段带符号 streak
    传播(生产口径:连胜 +/连败 −,备战帧读 session.last_streak 同语义)
    接线后恒成立;None = 传播断线,④连败金流/①连败门在 sim 退化为死
    输入(W790 判定③的根因之一)。
    变异证据:接线前 P1 决策帧 streak 100% None(30 局探针 6410/6410 帧,
    本目录 probe_bits 实测);去掉结算段写入即复现违规——非空转检查。
    """
    out: list[str] = []
    for row in rows:
        if (row.get('plane') or 1) != 1:
            continue
        st = row.get('state') or {}
        if 'streak' in st and st.get('streak') is None:
            out.append(f"r{row.get('round_num')} state.streak=None"
                       '(带符号 streak 传播断线)')
    return out



def check_observation_keys_live(rows: list[dict]) -> list[str]:
    """sim_observation_keys_live(观测硬依赖键面哨兵;W793 后继批)。

    判据(结构锁,非行为锁):P1 段每行账本必须带三个观测硬依赖键,
    且形状合法——
    - ``state.bench_full_flag``:bool(满栏旗标;消费 = 锁#10 D1 弱序
      量产对账;缺键/None = 写端断线,下游读端会静默退 0);
    - ``state.board_next_tier``:dict[str, int](Δp_tier 档位分解标定
      前置键;值域 2-12 = FACTIONS tier 阈值域);
    - ``sim.alloc_frame``:None 或含 active/domain 的 dict,active=True
      时 domain ∈ {stop_window, death}(ADR-0474 分配器帧位;消费 =
      锁#11 D2 接管可观测性);
    - ``sim.alloc_active_any``:bool,且为真时 alloc_frame 必非 None
      (自洽:OR 聚合源就是帧位)。
    变异证据:键缺失/形状错在旧账本 100% 命中(旧行无这些键)——
    去掉 engine 写端即复现,非空转。
    """
    out: list[str] = []
    for row in rows:
        if (row.get('plane') or 1) != 1:
            continue
        rn = row.get('round_num')
        st = row.get('state') or {}
        sm = row.get('sim') or {}
        bff = st.get('bench_full_flag', None)
        if not isinstance(bff, bool):
            out.append(f'r{rn} state.bench_full_flag 非布尔'
                       f'({bff!r}——满栏旗标写端断线)')
        bnt = st.get('board_next_tier', None)
        if not isinstance(bnt, dict) or not all(
                isinstance(k, str) and isinstance(v, int)
                and 2 <= v <= 12 for k, v in bnt.items()):
            out.append(f'r{rn} state.board_next_tier 形状非法'
                       f'({bnt!r}——下档阈值键写端断线)')
        af = sm.get('alloc_frame', None)
        if af is not None:
            if not isinstance(af, dict) or 'active' not in af:
                out.append(f'r{rn} sim.alloc_frame 形状非法({af!r})')
            elif af.get('active') and af.get('domain') not in (
                    'stop_window', 'death'):
                out.append(f'r{rn} sim.alloc_frame.domain 非法'
                           f'({af.get("domain")!r})')
        aaa = sm.get('alloc_active_any', None)
        if not isinstance(aaa, bool):
            out.append(f'r{rn} sim.alloc_active_any 非布尔({aaa!r})')
        elif aaa and af is None:
            out.append(f'r{rn} alloc_active_any=True 但 alloc_frame 缺'
                       '(自洽破:OR 源即帧位)')
        # (p1_downgrade_active 可信位检查已随 v2 退役链删除——统一迁移批
        #  ② 引擎账本位退役,MAP A7/B 类;键不再入必检集。)
        rp = st.get('refresh_probs', 'MISSING')
        if rp == 'MISSING':
            out.append(f'r{rn} state.refresh_probs 缺键(轮岗概率条'
                       '披露断线)')
        elif rp is not None and not isinstance(rp, dict):
            out.append(f'r{rn} state.refresh_probs 形状非法({rp!r})')
    return out


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
    T3 转化类卖出分键豁免与 check_no_same_round_buy_sell 同边,并随
    T-165 按键分工判定同步(转化类读 convert_reason / 孤儿读
    sell_reason ∈ cw_prep_actions.SELL_BENCH_ORPHAN_REASONS(T-180 起
    与发射位登记门分离的独立闭集),键集单一源 =
    cw_state.SELL_BENCH_CONVERT_REASONS + cw_prep_actions.SELL_BENCH_
    ORPHAN_REASONS)。
    T-153 迁移(C4/ADR-0593):豁免边同款降级为「自算复核通过才豁免」
    (copy 收集语境/seed 身份/转化分键线成员三复核,判定核单一源 =
    selfcalc;失配 = 可疑项条目 + 该对计入 osc 不豁免;键缺省照旧)。
    """
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        SELL_BENCH_ORPHAN_REASONS,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        SELL_BENCH_CONVERT_REASONS,
        XP_TO_NEXT_LEVEL,
    )
    from sr_od.application.currency_war.sim.checks import selfcalc as _sl
    out: list[str] = []
    # 净持有语境(ADR-0593 后果.5(L2):买入入集/卖出台账销账;首行种子口径同
    # check_no_same_round_buy_sell 的 _held_net 声明)
    _held_net: set[str] = set()
    if rows:
        _row0_act_names = {(a.get('card') or {}).get('name')
                           for a in (rows[0].get('actions') or [])
                           if a.get('__type__') == 'BuyCard'}
        _st0 = rows[0].get('state') or {}
        _row0_held = {b.get('char_id') for b in (_st0.get('bench') or [])
                      if isinstance(b, dict)} | \
                     {d.get('char_id') for d in (_st0.get('deployed') or [])
                      if isinstance(d, dict)}
        _held_net = {n for n in (_row0_held - _row0_act_names) if n}
    for _row_idx, row in enumerate(rows):
        bought: list[str] = []
        copy_names: set[str] = set()
        seed_buys: dict[str, int] = {}
        _seed_acts: dict[str, list[dict]] = {}
        _copy_round_buys: dict[str, int] = {}
        osc = 0
        _held_before_round = set(_held_net)   # 本轮前净持有(复核基线)
        for a in row.get('actions') or []:
            t = a.get('__type__')
            if t == 'BuyCard':
                _n = (a.get('card') or {}).get('name')
                if not _n:
                    continue
                _rs = _normalize_buy_reason(a.get('reason') or '')
                if _rs == 'copy':
                    copy_names.add(_n)
                    _copy_round_buys[_n] = _copy_round_buys.get(_n, 0) + 1
                    bought.append(_n)   # ADR-0593 后果.5(L1):copy 对可达复核分支
                else:
                    if _rs == 'engine_seed':
                        seed_buys[_n] = seed_buys.get(_n, 0) + 1
                        _seed_acts.setdefault(_n, []).append(a)
                    bought.append(_n)
                _held_net.add(_n)   # 净持有:买入入集
            elif t == 'SellBench':
                _nm = a.get('name')
                _held_net.discard(_nm)   # 净持有销账(跨轮;ADR-0593 后果.5(L2))
                if _nm not in bought:
                    continue   # 非同轮对:本检查(振荡)不辖
                if _nm in copy_names:
                    # T-153 迁移(C4/ADR-0593):copy 复核,失配计入 osc。
                    # 复核基线 = 本轮前净持有快照(本轮 copy 买不算持有)
                    if _sl.copy_collection_review(
                            _held_before_round,
                            _copy_round_buys.get(_nm, 0)) \
                            != _sl.REVIEW_MISMATCH:
                        bought.remove(_nm)   # 豁免照旧(每对只豁免一次)
                        continue
                    out.append(
                        f"p{row.get('plane')}r{row.get('round_num')} "
                        f"可疑项(同轮买卖分键失配): 卖 {_nm} 自报 copy "
                        f'自算=无收集语境——请裁决 (ADR-0593)')
                    osc += 1
                    bought.remove(_nm)
                    continue
                if seed_buys.get(_nm, 0) >= 2:
                    # 收集语境让位(ADR-0276)+ T-153(C7)种子身份复核
                    if all(_sl.seed_identity_review(rows, _row_idx, _ba)
                           != _sl.REVIEW_MISMATCH
                           for _ba in _seed_acts.get(_nm, ())):
                        bought.remove(_nm)
                        continue   # 豁免照旧
                    out.append(
                        f"p{row.get('plane')}r{row.get('round_num')} "
                        f"可疑项(种子身份失配): 卖 {_nm} 自报 engine_seed "
                        f'收集语境 自算=非引擎件/购买时已持有——请裁决 '
                        f'(ADR-0593)')
                    osc += 1
                    bought.remove(_nm)
                    continue
                # 转化类/孤儿豁免按键分工判定(ADR-0611,
                # 与 check_no_same_round_buy_sell 同构)
                _claim = ''
                _conv_key = a.get('convert_reason') or ''
                _orph_key = a.get('sell_reason') or ''
                if _conv_key in SELL_BENCH_CONVERT_REASONS:
                    _claim = _conv_key
                elif _orph_key in SELL_BENCH_ORPHAN_REASONS:
                    _claim = _orph_key
                if _claim:
                    # T3 转化类卖出分键豁免(非自旋)+ T-153(C4)降级
                    if _sl.sell_line_membership_review(row, a) \
                            != _sl.REVIEW_MISMATCH:
                        bought.remove(_nm)
                        continue   # 豁免照旧
                    out.append(
                        f"p{row.get('plane')}r{row.get('round_num')} "
                        f"可疑项(转化分键失配): 卖 {_nm} 自报分键="
                        f'{_claim} 自算=非线成员——请裁决 '
                        f'(ADR-0593)')
                    osc += 1
                    bought.remove(_nm)
                    continue   # 失配不豁免
                osc += 1
                bought.remove(_nm)
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
    """升级支出跟随决策费用载体锁(原 flat4 台账锁;T-240 语义重推)。

    锁意图沿革:LevelUp 单击价真值初裁 = flat 4(lv5-8 净证;
    lv3-4 推定,ADR-0289),字面判据 spend.levelup == 4 × LevelUp 行数。
    重推依据(锁的存在性纪律,禁机械跟绿):sim 支出载体自 ADR-0561
    申报表 #5 统一 = action.cost(策略层 xp_click_cost 真值,折扣感知)
    ——持商业间谍/成长的快乐(等级门)的局单击价 = 4−折扣 ≠ 4,注入臂
    可持卡(engine_p1 策略选卡注入),字面 4 与载体真值在先矛盾;「4」
    实为**无折扣局的快照**,非锁真不变量。重推后判据:

        spend.levelup == Σ(LevelUp 行 cost)

    (cost 缺读/0 按 engine_p1 同口径 ``getattr(a,'cost',0) or 4`` 兜,
    旧档案行不因代际漂移。)无折扣局该判据退化为原字面 4×行数,零松绑;
    折扣局单价真值(取价是否含对折扣)不在本锁辖域——由 kernel 侧
    xp 折扣修复锁族(sr-od-test test_cw_economy xp 买费折扣修复锁族:
    显示价直通/两支等价/成长的快乐真值表)把守,两域分工防同错互证。
    拒付行(LevelUpRejected)不入 LevelUp 行数,与本判据无交互
    (engine_p1 cap 守卫语义,双模型并存回归同前由本锁拦截(载体单一源
    = ADR-0561 申报表 #5):执行器弃 action.cost 回退私价模型即
    spend≠Σcost 必红)。
    """
    out: list[str] = []
    for row in rows:
        acts = row.get('actions') or []
        lv_acts = [a for a in acts if a.get('__type__') == 'LevelUp']
        spent = ((row.get('sim') or {}).get('spend') or {}) \
            .get('levelup', 0)
        expected = sum(int(a.get('cost', 0) or 4) for a in lv_acts)
        if spent != expected:
            out.append(
                f"p{row.get('plane')}r{row.get('round_num')}: "
                f"levelup 支出 {spent} ≠ 决策费用载体 {expected}"
                f"({len(lv_acts)} 击;执行支出未跟随 action.cost——"
                f"T-240 重推,原 flat4 字面判据已废止)")
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



def _pair_target_anchor(comp: str) -> frozenset[str] | None:
    """过渡配方伪 comp 名 → 体系键锚集(非过渡配方名 → None=原子段)。

    名格式 = ``'过渡配方·' + '+'.join(pair)``(cw_intention.pair_target_comp
    单一构造点);锚集 = 拆 '+' 后的体系键集合。ADR-0616 §3.3 裁决②
    (编排者 2026-09-10,T-166 批1 任务书前置裁决记录):门槛过滤先行
    落地后,1 元对为在册边缘帧,合法新增「{A,B}→{A}→{A,B'}」席位退场/
    补位链——同锚子集/超集转换是席位进出,不是方向切线,本函数是该
    豁免的锚集解析半部。"""
    prefix = '过渡配方·'
    if not comp.startswith(prefix):
        return None
    return frozenset(comp[len(prefix):].split('+'))


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

    段首轮号语义:history 每段记该配方「首次出现轮」,同段延续
    不更新——r_c - r_b 因此等于 B 段驻留轮数(≤3 轮 = 试错回摆
    relapse;>3 轮 = 合法 pivot,不辖)。若段首轮号被段末行覆盖,
    「A→B→A 且回锁后保持稳定」这一最常见回摆形态会把 r_c 推到
    A 段末,r_c - r_b 必然 >3,摇摆全部漏判(实测三批 sim 档案
    重测,摇摆率被该缺陷低估约一半;检测器实现层缺陷,判据表
    语义无歧义:回锁 = 该配方首次重新出现之轮)。

    同锚子集/超集转换豁免(ADR-0616 §3.3 裁决②,编排者解除该文件
    「零改动」条款后落码;T-194 先例:语义修正保留守卫意图即合法):
    过渡配方伪 comp 的体系键锚集互为子集/超集的相邻转换(席位退场/
    补位链,{A,B}→{A}→{A,B'} 型,1 元对为 ADR §2.1 在册边缘帧)并入
    前段延续——锚系未换,方向未切线,按段首语义并入不计新段;跨锚
    转换(锚集不交或交叉非包含,如 {A,B}→{A,C} 二席换人)仍各立段
    照判。守卫意图不变:A→B→A relapse 指纹与 ≤3 轮辖域零松动。
    """
    out: list[str] = []
    history: list[tuple[int, str]] = []   # (段首轮号, comp)
    for row in rows:
        if row.get('plane') != 1:
            continue
        comp = row.get('target_comp') or ''
        if not comp:
            continue
        rn = row.get('round_num') or 0
        if history:
            if history[-1][1] == comp:
                # 同段延续:保留段首(首次出现轮),不取段末覆盖——
                # 段末覆盖会把「回锁后稳定」段的 r_c 推远,漏判 relapse
                continue
            cur_anchor = _pair_target_anchor(comp)
            last_anchor = _pair_target_anchor(history[-1][1])
            if (cur_anchor is not None and last_anchor is not None
                    and (cur_anchor <= last_anchor
                         or last_anchor <= cur_anchor)):
                # 同锚子集/超集转换 = 席位退场/补位,并入前段延续
                # (段首轮号不更新,与前段同段判读;裁决②豁免语义)
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
    """批㉜ 检查项(ADR-0555 补值批扩为全量披露):价值表对策略层
    自声明关键装备的通用价值覆盖。

    判据:COMP_LIBRARY key_equips 中在 EQUIPMENT_ROSTER 内的**全部**
    装备名(不设引用次数阈值——批㉜ F4 实证 ≥3 阈值只看见 2 名、
    盲区 13 名同样恒 0 分),应存在于 _EQUIP_VALUE——缺失 = 该装备
    在本阵容未锁线时(decide_supply 第 3 分支,key_fit +10 不触发)
    通用价值恒 0 分,与策略层自己的重要性声明矛盾。清偿判据 =
    本检查归 0(补值入表 / 显式裁决「通用价值确为 0」后按 ADR-0298
    同款语义处理)。本检查不消费账本行(逐局循环里每 game 披露一次)。
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
                 if n in EQUIPMENT_ROSTER
                 and n not in _EQUIP_VALUE)
    if not gap:
        return []
    return [
        f"策略层 key_equips 引用但价值表缺值 {gap}"
        f"(未锁线局通用价值恒 0——批㉜ F4 缺口 ADR-0555 已裁决补值,"
        f"新缺值名按同批方法处置)"]



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



# --- T-115 恒买腾席判红检测器(写端位出口键完备性;ADR-0580)--------

#: C1/④ 腿写端位出口键闭集(恒买腾席方案 v2 §5.6)。镜像纪律(同
#: XP_TO_NEXT_LEVEL 先例):发射位计数键单一源在 shop.py 三腿发射位
#: (字面 _count 键),本元组 = 检查器侧镜像;值漂移由双向锁暴露
#: (测试仓 test_cw_core_seat_vacate.py:三腿 16 键逐一发射断言 ∈ 本集)。
_CORE_EXIT_KEYS: frozenset[str] = frozenset({
    # 未锁线恒买腿(T-115 规则③;席满静默病灶本体)
    'core_unlocked_buy_hit', 'core_unlocked_seat_swap',
    'core_unlocked_no_fuel', 'core_unlocked_unaffordable_strict',
    'core_unlocked_unaffordable_fundable',
    # 锁线支配支腿(资格门席位维已下放循环内,for-else 尾键收窄)
    'core_dominance_buy_hit', 'core_locked_seat_swap',
    'core_locked_no_fuel', 'core_locked_unaffordable_strict',
    'core_locked_unaffordable_fundable', 'core_numeric_fail_closed',
    # ④转线腿
    'transition_component_buy_hit', 'transition_seat_swap',
    'transition_no_fuel', 'transition_unaffordable_strict',
    'transition_unaffordable_fundable',
})
_CORE_SEEN_KEY = 'core_candidate_seen'
#: 观察桶键后缀(非红,分键披露):诚实停摆/金不足双桶。
_CORE_OBS_BUCKET_SUFFIXES = ('_no_fuel', '_unaffordable_strict',
                             '_unaffordable_fundable')


def check_core_ruling_seat_violation(rows: list[dict]) -> list[str]:
    """恒买裁定席满静默违判红(T-115/ADR-0580;恒买腾席方案 v2 §6)。

    判据(严格红域 = 写端位出口键完备性):``core_candidate_seen``
    (C1 候补支触发,帧级)落键而 §5.6 出口键闭集零落 = 席满帧静默弃买
    复活(病灶形态:s8r8 金 95 希儿在售被拒零显影,8 刷零买零卖)。
    落码后此域不可达,红 = 实现缺陷/回归。

    载体边界与红则形态(如实申报):判红载体 = 轮级 ``obs.cw4_counters``
    增量快照(engine_p1 行装配在役);shop_waves 波行无 counters,逐帧
    配对不可得 ⇒ 红则取**计数式轮级回退**(收口复审残注①钉死):
    ``Σseen > Σ出口键``。多候补帧逐帧出口 ≥1 ⇒ Σ出口 ≥ Σseen 恒成立
    不假红;违例即本轮至少一个 seen 帧零出口(静默违)。已知近似申报:
    ①轮级并集口径对「同轮混合帧」有稀释(任一出口键补位即掩盖同轮他
    帧静默;三腿并集含 ④腿键再稀释一档),逐帧精确配对候零行为加列
    contingency(方案 v2 §6.1 申报面,本批未落);②锁线腿/④腿辖域 =
    出口键完备性观测(候裁2:锁线腿逐帧严格红域候 ADR-0569 判据式与
    裁定辖域关系裁定),轮级计数式对三腿统一计 Σ 属同一载体近似。
    行无 obs.cw4_counters 键(旧账本)= 无判红载体,跳过不报(缺证据
    不定罪,ADR-0589 无键回退先例)。

    观察桶(非红):出口键 = *_no_fuel(无合法 victim 诚实停摆)/
    *_unaffordable_strict / *_unaffordable_fundable(A4 双桶)——本
    检查不产出违规;分布判读走批级披露 core_ruling_seat_buckets。
    """
    out: list[str] = []
    for row in rows:
        obs = (row.get('obs') or {}).get('cw4_counters')
        if not isinstance(obs, dict):
            continue
        seen = int(obs.get(_CORE_SEEN_KEY, 0) or 0)
        if seen <= 0:
            continue
        exits = sum(int(obs.get(k, 0) or 0) for k in _CORE_EXIT_KEYS)
        if seen > exits:
            out.append(
                f"p{row.get('plane')}r{row.get('round_num')}: "
                f"恒买候补帧静默违(seen={seen} > 出口键Σ={exits}"
                f"——席满弃买零显影复活,T-115 判红)")
    return out


def core_ruling_seat_bucket_disclosure(ledgers: list[list[dict]]) -> dict:
    """恒买腾席支出口键分布披露(批级数据面;非违规,violations 恒 0)。

    判读面:seen 总量(开火性)× 出口键逐键分布——buy_hit/seat_swap =
    买/转化开火;*_no_fuel = 诚实停摆桶;*_unaffordable_strict/
    *_fundable = A4 金闸双桶(候裁4 卖前金读,均不动作)。供种子批
    验收「零红 + seat_swap>0 + 桶分布披露」线(方案 v2 §11.2)。
    """
    seen = 0
    exits: dict[str, int] = {}
    games_with_seen = 0
    for rows in ledgers:
        _game_seen = 0
        for row in rows:
            obs = (row.get('obs') or {}).get('cw4_counters')
            if not isinstance(obs, dict):
                continue
            n = int(obs.get(_CORE_SEEN_KEY, 0) or 0)
            if n > 0:
                seen += n
                _game_seen += n
            for k in _CORE_EXIT_KEYS:
                v = int(obs.get(k, 0) or 0)
                if v:
                    exits[k] = exits.get(k, 0) + v
        if _game_seen:
            games_with_seen += 1
    buckets = {k: v for k, v in exits.items()
               if k.endswith(_CORE_OBS_BUCKET_SUFFIXES)}
    return {'violations': 0, 'seen': seen,
            'games_with_seen': games_with_seen,
            'exits': exits, 'observation_buckets': buckets}



