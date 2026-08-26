"""决策框架 v2 注册表(ADR-0290 对抗修订③:剪枝显式化/全注册表化)。

评分表 / 剪枝 K / 标签优先与互斥 / 过滤链 / 约束清单 / 完备性审计表
全部集中在此,``DecisionV2Registry`` 可整体注入(A/B:两套注册表各跑
一臂,sim 配对对照)——**禁止隐式排序、禁止散落硬编码**。

数值口径(**已部分标定**,ADR-0293 首轮标定:refresh 族/目标件
持有基线四参已按 20 局诊断+30 局配对验证标定;其余仍为骨架初值,
后续批次继续):
- 档位期望:P3 已证边际(e0→e1 +1.4 / e1→e2 +1.6 金/轮)→ 累计档值;
- 战力:H3 阶梯矩阵胜率(e0 13.9% / e1 41.6% / e2 77.8%,n=187/89/9);
- 息律:[17][28](50 金息律 / P1 满息通关)进 interest_rule 约束;
- 地板初值镜像旧 line_strategy 同名常量(_EMERGENCY_HP 等;
  旧两臂 A/B 语义随 ADR-0336 结束,注册表独立演进)。

决策见 docs/develop/currency_war/decisions/0291-decision-v2-skeleton.md。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DecisionV2Registry:
    """决策框架 v2 全部可调参数与显式注册结构(单一注入点)。"""

    # ===== 层1:候选生成(剪枝显式化——K 值/排序键/标签优先序) =====
    #: 买候选标签优先序(单卡只取首个命中标签;顺序即裁决,可 A/B)
    buy_tag_priority: tuple[str, ...] = (
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'pair', 'copy', 'bond_fallback',
        'carry_gate',
    )
    #: 3合1 合成候选:标记位(不占标签序——第三张副本买入即合成,
    #: Candidate.merge=True;覆盖全部目标类买入)
    #: 卖候选标签优先序(off_target 最先;free_bench=腾位让位 [32])
    sell_tag_priority: tuple[str, ...] = (
        'off_target', 'for_gold', 'free_bench',
    )
    #: 部署候选 top-K(K 与排序键显式:排序键=围栏序 cw_deploy_logic
    #: .select_deployments 的点火首键+桶序——同一源,不另造排序)
    deploy_top_k: int = 3
    deploy_sort_key: str = 'cw_deploy_logic_fence'
    #: 卖候选上限(bench 每件都生成,但执行轮内采纳上限——防整板清仓)
    sell_top_k: int = 2
    #: 同名副本上限(星级加权 3 份;第 4 份纯浪费——line_strategy
    #: ._buy_guards 同语义,此处注册表化)
    copies_cap: int = 3
    #: copy_swap 守卫×目标件豁免开关(ADR-0303 落地,ADR-0304 裁决
    #: **默认关=回退 0302 守卫直通**):True=在场目标件(∈ _target_names
    #: 保护集)第 2 份不被 r410 守卫拦;False=回退(豁免代码留,
    #: A/B 通道可开)。裁决依据:ADR-0303 三窗小负(-4.67/-0.90/-0.27
    #: 一致向负)未兑现批㉞「下批杠杆」预期——指挥官裁决回退。
    copy_swap_target_exempt: bool = False
    #: [31] 凑档降级的成本带上限(1-2 费=P1 过渡带)
    bond_fallback_max_cost: int = 2
    #: [31] 降级触发回合门(P3 边界:r1-r2 无战斗买件纯付息损)
    bond_fallback_min_round: int = 3
    #: [32] carry_gate 腾位买的轮界(r≤7;r8-r9 终局段买入不影响结算)
    carry_gate_max_round: int = 7

    # ===== 层4 补偿趟(W52 回连机制;ADR-0326)=====
    #: 补偿辖的买侧标签(= 旧 LIQUIDITY_BUY_TAGS 语义迁入,含
    #: 'carry_gate'——ADR-0326 H1:该标签落「非核心目标件+bench 满+
    #: 早期轮」,与 v3_core_names 空窗下的目标件,金补偿路径对两种
    #: 标签都稳健;不为非目标件变现——只有更高优先级购买才配动用
    #: 压库资产;pair/copy/bond_fallback 凑数凑对类与 refresh/levelup
    #: 不辖[refresh 的补偿走 S2 报警辖域,不经本标签集])
    remedy_buy_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'carry_gate',
    })
    #: 补偿受益候选的分数下沿(被拒分 ≤ 此值不为它补偿——只救高价值买)
    remedy_min_score: float = 0.5
    #: 报警升级态 refresh 金不足是否纳入补偿(S2 残余;默认开)
    remedy_alarm_refresh: bool = True

    # ===== S5 统一卖件弱序(W52/ADR-0327)=====
    #: [22]③ 再遇窗口表(费级→再遇期望轮数):1费 11(7-15 中值)/
    #: 5费 120(60-180 中值,7-8 级窗口);2-4费线性内插。首版三档
    #: 近似,sim 校准域(ADR-0327)——消费方 sell_priority_key。
    remeet_window_rounds: dict[int, int] = field(default_factory=lambda: {
        1: 11, 2: 25, 3: 40, 4: 60, 5: 120})
    #: W4 去向表派生的费级终局贯穿率(E→F 留存;ADR-0327):
    #: 证据等级=**推断近似**——W4 报告(Q1)为逐角色值(贯穿层
    #: 2费 骨架 0.66-0.95 / 消耗品 1费 0.05,费级非严格单调),
    #: 此处取费级趋势近似(高费件终局留存低);sim 校准域。
    through_rate: dict[int, float] = field(default_factory=lambda: {
        1: 0.20, 2: 0.20, 3: 0.15, 4: 0.12, 5: 0.10})
    #: 卖分缩放权重常数(S5 评分侧;w=sell_key_weight_scale×
    #: (1+min_loss)/(1+loss),封顶 1.0——1=不缩放(回退均一 bias);
    #: A/B 通道保留)
    sell_key_weight_scale: float = 1.0

    # ===== 层2:硬过滤链(redesign §3 覆盖态严格优先序)=====
    #: 过滤链层级序:应急 > 模式(追赶态已随 W126/ADR-0349 退场——人口落后
    #: 由通道 2 人口位升级+通道 4 概率等级窗+EV 总账涌现,兜底局由 form_score
    #: 承接「人口别落后」观察;位面绝对基线 {5,7,9} 是阵容无关的粗糙代理)
    filter_chain_order: tuple[str, ...] = ('emergency', 'mode')
    #: 各层放行标签集(候选标签仅作过滤域标记,不携带优先级——ADR-0290)
    #: ADR-0302 应急集内容修正(合流批 ADR-0303 并入):补 for_gold
    #: (卖弱件)+levelup(升级)——应急态语义=战力买+卖弱件+升级,
    #: 旧窄集把两通道在应急态整体滤死(批㉝ F4);pair/copy/
    #: bond_fallback/synthesize 在应急态仍滤出(ADR-0300 应急集保持窄)
    emergency_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'carry_gate', 'off_target',
        'free_bench', 'deploy', 'for_gold', 'levelup',
    })
    #: 追赶窗口约束与追赶标签集已随 W126/ADR-0349 删除(用户 2026-08-25
    #: 裁决 F6/Q4:人口落后=阵容没上满的表现,由通道 2/4+EV 涌现承接)
    economy_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'pair', 'copy', 'carry_gate',
        'bond_fallback', 'off_target', 'for_gold', 'free_bench',
        'levelup', 'refresh', 'deploy',
    })
    war_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'pair', 'copy', 'bond_fallback',
        'carry_gate', 'off_target', 'for_gold', 'free_bench',
        'levelup', 'deploy',
    })
    #: 追赶窗口约束:追赶期禁 for_gold(不折现卖件)+ 禁 refresh
    #: (升人口窗口的钱不进刷新;redesign「追赶=升人口置顶」)
    #: war 标签集(W126/ADR-0349:refresh 进 war 集——「war 模式滤 refresh」
    #: 废除,D 是一等花钱通道([17]「该D牌D牌」不因 war 覆盖态消失;
    #: 授权仍由 V_D 批口径评分+interest_rule EV 门辖,标签集只管在场)
    war_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'pair', 'copy', 'bond_fallback',
        'carry_gate', 'off_target', 'for_gold', 'free_bench',
        'levelup', 'deploy', 'refresh',
    })
    #: 应急 HP 档(触发层2 应急过滤;旧 line_strategy._EMERGENCY_HP
    #: 镜像,ADR-0336 后独立)
    emergency_hp: int = 25
    #: ADR-0302 危机囤金金线(合流批 ADR-0303 上移):应急态金 ≥ 此值
    #: 时进危机囤金态(战力买偏置+搜牌解锁)。依据:批㉝ F3 指纹阈值
    #: 40(hp≤25 且金≥40 只升不买,金囤 85+ 板濒死零动作)
    crisis_hoard_gold: int = 40
    #: (catchup_min_level/pop_baseline 已随 W126/ADR-0349 删除:追赶态退场,
    #: 通道 2 人口位([33])+通道 4 概率等级窗([3])+EV 总账涌现承接)

    # ===== 成型停手纪律([13] 停手线;ADR-0343;W119/ADR-0347 收编)=====
    #: 总开关(False=旧行为,成型后照买;A/B 通道)
    formed_stop_enabled: bool = True
    #: 停手辖轮**全局下界**(W97/W105 晚买证据窗=r7-r9);实际辖轮=
    #: max(锁定线 typical_form_round, 此值)——comp 派生(W115-B1,
    #: 固定 r≥7 会固化「早成型阵容多买两轮」偏差)
    formed_stop_min_round: int = 7
    # (formed_stop_min_level 已随 W119 删除:等级不作为独立门槛——
    #  2026-08-25 用户裁决 Q2,等级通过上场完整性进入 form_ok 判定)

    # ===== 相位观测与授权(W114/ADR-0346 影子;W119/ADR-0347 切授权)=====
    #: (phase_form_score_gate 已随 W132/ADR-0353 删除:兜底门从 form_score 连续量
    #  改结构判据——W118 sim r2-r3 弱板误转真 + 实机 run15 r4 score 0.65 多线
    #  散板(仙舟3 单体系+配方档小数)过门两证;用户判读原则 2026-08-26「任何
    #  位面看阵容完成度」→ 判据 = 板面真收敛到 ≥2 过渡体系,非分数可达性。
    #  form_score 降级纯遥测观测,不进判据)
    #: 兜底局(意向未锁)form_ok 的轮数下限(W119/ADR-0347 校准判据,W113 §8-11):
    #: W118 实测 A 臂兜底局 form_score≥0.5 在 r2-r3 即转真——1 过渡体系≠战力
    #: OK。结构门下保留(合取):即使两体系早凑齐,r5 前板面人口/星级仍薄,
    #: 保守留 FORM(地板 20 允许买牌强化,不亏)
    phase_fallback_min_round: int = 5
    #: 兜底局 form_ok 的有效体系数下限(W132/ADR-0353):有效体系数 =
    #: ``_engines_count``(四体系单一源,deployed 口径)+ hp_charge_stack 型
    #: 全局累积角色豁免(上场 2★ 计 1,万敌;W127 字段消费)。取 2 =
    #: transition_combos 定稿「四体系两两组合=过渡成型,单体系点火≠成型」
    #: (三选二 140/328 帖;2026-08-23 用户定调)
    phase_fallback_min_engines: int = 2
    #: FORM 相位地板=保险丝(W113 Q1 已裁决:决策器=EV 授权,FORM_FLOOR
    #: 只防收益端估乐观时花光本金;初值 20=沿用应急保底语义,**Q1 四档
    #: sim 对照(不设/10/20/30)待校准,本批只接线不标定**)
    form_floor: int = 20
    #: boss 破息窗 node_type 缺读兜底轮(W119/ADR-0347 统一口径:
    #: boss 窗主判据=节点图 node_type∈boss_round_node_types,轮数口径
    #: 全仓只留 discipline.boss_window_active 一处且仅作缺读兜底——
    #: P1 末节点恒为 boss 的节点图先验,r≥9 兜底)
    boss_window_fallback_round: int = 9
    #: 扑满节点(奖励型战斗)单节点刷新豁免上限(W119/ADR-0348×W120 P8
    #: 上限:凑羁绊支出 s≤0.277R,R 采集前保守取节点基础收入 6-9 金
    #: → s≤2 金=1 次刷新;**禁深花保血**——扑满不掉血,真损失=打不过
    #: 没奖励,轻投入凑羁绊刷伤害;R 真值采集后等比重标)
    piggy_refresh_round_cap: int = 1

    # ===== 层3:板面查表评分(初版=档位×P3 + 息律 EV + H3 插值)=====
    #: 档位累计值(金/轮;P3 边际 e0→e1 +1.4 / e1→e2 +1.6 累计)
    rung_value: dict[int, float] = field(
        default_factory=lambda: {0: 0.0, 1: 1.4, 2: 3.0})
    #: H3 战力阶梯(battle 胜率;rung 插值键,x>2 取 2)
    h3_win_rate: dict[int, float] = field(
        default_factory=lambda: {0: 0.139, 1: 0.416, 2: 0.778})
    #: 档值折算的剩余轮数估计(P1 9 节点骨架的中段估值;未标定)
    rounds_left_est: float = 5.0
    #: 剩余战斗节点估计(同上,未标定)
    battles_left_est: float = 5.0
    #: 单场战斗典型掉血([27] B+P 合成;P1 battle -7~-13 取中;未标定)
    expected_battle_loss: float = 10.0
    #: HP→金换算(P3:4.4HP≈2.2金 → 0.5 金/HP)
    hp_to_gold: float = 0.5
    #: 利息封顶档([17]:50 金息律,5 金/轮)
    interest_cap: int = 5
    #: 息 EV 折算轮数(与 rounds_left_est 同源口径)
    interest_rounds: float = 5.0
    #: 档位分数部分(recipe 档 → 小数 rung 的插值系数;未标定)
    rung_frac_per_recipe_tier: float = 0.3
    #: 刷新常量 EV 族已随 W126/ADR-0349 删除(refresh_ev/refresh_max_round/
    #: refresh_min_gold/refresh_starve_*/refresh_game_cap/levelup_reserve_
    #: gold/form_refresh_*:refresh 附庸闸整体退场——D 候选评分改 V_D 批口径
    #: (scoring.vd_refresh_score,P5 定理:expected_refreshes×刷价 vs 收益侧),
    #: 预算前提=C_interest 在 50 档边界的输出(G2,不设常量金门))
    #: 扑满节点(奖励型战斗)刷新 EV(W126:轮界门删除后,扑满凑伤害 D 的
    #: 独立小额 EV——受 piggy_refresh_round_cap 辖(P8:s≤2金/节点),
    #: 扫满即无证拒;值=旧 refresh_ev 沿用,语义收窄到扑满节点专属)
    piggy_refresh_ev: float = 2.5
    #: 买侧 C_interest 的回档折中视界(W131/ADR-0352):买候选跨息档的
    #: C = 档数 × min(R跨位面, 此值)。依据:P6 回档账下界(破档后
    #: 1-2 轮回档,真实息损 1-3 金)与平面 R 上界(P5⑤,≈20-23)的
    #: 折中——买是一次性金→板面资产兑换,「停在低档到位面末」的
    #: 上界前件描述的 FORM 政策态由相位地板辖,不在 EV 门重复计罚;
    #: 3.0=两界之间的保守中点,网格精调(1-5)留 sim 批。只辖买侧
    #: (arbiter.interest_rule 的 BuyCard 分支);刷新(D)与升级平台账
    #: 保持平面 R 上界不动(P5⑤ 退化输出/平台语义)。
    interest_recovery_rounds: float = 3.0
    # ===== W154/ADR-0361 P2 段 V_D 修法(P11/P12 口径;常数归本层可 A/B 注入)=====
    #: P2 段 V_D 口径总开关:False=回 W153 前行为(窗二分=level_plan 互斥,
    #: 成本=批口径面值,收益=P1 骨架参数)——A/B 基线臂。P1 分支与开关无关
    #: (逐位不动,P1 sim 零漂移回归门)。
    vd_p2_enabled: bool = True
    #: P2 掉血期望(P12 收益侧:[27] B+P 公式的 P2 实测带 15-17 取保守中值 16;
    #: 真值采集点=结算屏 OCR 三项拆解,采前 16 为保守中值)
    vd_p2_loss: float = 16.0
    #: P2 穿 50 段回档轮上界(P11 成本侧:P2 收入 13-19/轮 → 回档 ≤2.31 轮;
    #: C_dec 的 Δinterest × min(R, 此值))
    vd_p2_recovery_rounds: float = 2.31
    #: 溢余金流动性影子价 ρ(P11:纯溢余段 C_dec 下界=0 后的期权项上界;
    #: P10① 携带溢价利息分量背书,W151 四局实证实现值≈0 → 起步 0)
    vd_p2_liquidity_rho: float = 0.0
    #: P1 体系对缺件找牌通道总开关(W170/ADR-0369):False=回 W166 前行为
    #: (P1 找牌只有 core 通道,level_plan 窗互斥逐位旧语义)——A/B 基线臂。
    #: True=P1 锁定帧(配方锁 p1_pair/①锁 transition_pair)缺件 ∧ 金≥
    #: interest_floor+刷价+买价([3] 单次预算前提)时,pair 缺件账参与
    #: V_D(scoring._vd_p1_pair;core 通道不受本开关辖)
    vd_p1_pair_enabled: bool = True
    #: 板深单位值(H3 板深条件化:深[6-8] -1.0 vs [3-5] -11.3 的
    #: 方向;depth=可上阵件数,板面形态维之一,非单卡拆分;未标定)
    depth_unit_value: float = 2.0
    #: 追级 EV 单位值(ADR-0290 层2 查表项「追级 EV」:等级→部署
    #: cap→板深的期权价值;小数等级=level+xp 进度比,单击经验
    #: 即分数性推进;未标定)
    level_unit_value: float = 1.0
    #: 目标件持有进度项(板面形态维:持有域内∈当前目标集的件数
    #: /基线,封顶计值——cap 饱和+店员非引擎阵营时买入恒 0 分被
    #: 「非正分」拒,r3-r6 空转攒金团灭的解;集合隶属计数,非
    #: 单卡边际拆分;base **已标定**=9(ADR-0293:base=6 时第 7 件
    #: 起目标件 0 分,中期买入饥饿→板弱团灭;9 让第 7-9 件显影
    #: 正分,30 局 mean 31.37/团灭 0)
    target_hold_value: float = 3.0
    target_hold_base: int = 9
    #: 形态域 bench 折减权重(ADR-0295 混合域):形态计数 deployed
    #: 星级×1.0 主导、bench 星级×此权重折减——ADR-0293 残差根因
    #: (持有域等权代理 r7-r8 全顶格而真实战力弱,seed 900032 一切
    #: 买入 0.00 分)的定向修;初值 0.35 由 20 局诊断定(ADR-0295)
    bench_form_weight: float = 0.35
    #: 目标件持有进度项天花板系数(ADR-0295:持有进度保留显影但
    #: 封顶折减——顶格不再=满形态;targets=min(此系数, n/base)
    #: ×target_hold_value)。ADR-0301 网格:1.0 无单独增益,维持 0.8
    target_hold_cap_frac: float = 0.8
    #: 引擎分数进度项单位值(ADR-0301 成型攻坚,每满进度引擎)。
    #: 依据:P3 已证 e0→e1 +1.4/e1→e2 +1.6 金/轮——买进度件是
    #: 正期望期权,但 rung_value 只在整数档跨越(deployed 上场)
    #: 显影;deployed=cap 时进度件躺 bench(×bench_form_weight),
    #: 混合域阈值不跨越 → 评分恒 0 → 「评分没买」主因(20 局
    #: 诊断 135/171 段引擎买候选评 0.0 被非正分拒)。本项对进度
    #: 小数余量(Σmin(w/tier,1)−整数引擎数)显影,与 rung 整数档
    #: 互补不双计(跨越时余量清零,值转进 rung_value)。0=关闭。
    #: **双窗网格标定 1.0**(A 窗 hp_ge_60 0→0.167 / B 窗
    #: 0.2→0.233,唯一双窗一致臂;2.0/4.0 过冲在 B 窗翻车——
    #: 高单位下进度件挤掉目标件买入)
    engine_frac_unit: float = 1.0
    #: 核心升星价值项单位值(W88/ADR-0339,[13] 成型三件套第三件:
    #: 过渡核心 2★)。持有域内 star≥2 且∈目标集(意向目标∪引擎件)
    #: 的件数 × 此值——deployed 全额、bench ×bench_form_weight 折减
    #: (ADR-0295 混合域同式)。修的是第六局判读:star 此前只在阵营
    #: 计数(star×权重)与 targets 星级加权两条路径显影,engines 封顶
    #: 后 2★ 分差≈0 → 换阵卖 2★ 不罚分/凑合副本 ≈0 分(升星投资
    #: 系统性贬值)。0=关闭(A/B 基线臂)。
    core_star_unit: float = 3.0
    #: 3合1 中间进度项单位值(W96/ADR-0340,[13] 副本凑合爬坡段:
    #: 目标件第 2 份 1★ 的期权显影)。core_star 只辖 star≥2,W93
    #: 断买根因①:第 2 份买入在 targets/eng_frac/core_star/rung
    #: 全维度零 delta → 「非正分」拒 → 金 59→90 溢出趴三轮
    #: (run_20260825_130151 r7-r9,[17] >50 每一分都该花)。每名
    #: 只计第 2 份(第 3 份 merge 后 core_star 承接,不双计);
    #: deployed 域 ×1.0 / 纯 bench 域 ×bench_form_weight(ADR-0295
    #: 同式)。初值=core_star_unit 同量级(同一 2★ 目的地的期权),
    #: 未网格标定,sim A/B 方向见 deep_read/W96_报告.md;0=关闭。
    merge_progress_unit: float = 3.0
    #: off_target 卖出评分偏置(弱件换金:持有域溢出件(cap 外 bench
    #: 囤件)的卖分本为 0,被「非正分」拒——偏置让纯占位件可换金
    #: 供刷新/买入;ADR-0291 遗留项,ADR-0293 标定;0.5 与 1.0
    #: 双窗逐位同分(任何正值同等翻转 0 分卖)
    off_target_sell_bias: float = 0.5
    #: ADR-0302 危机战力买偏置(合流批 ADR-0303 上移;量级=
    #: off_target_sell_bias 量级的买侧对偶;只把 0 分板面差分顶成
    #: 正分——金 52→49 的息崖 -25 不被它翻越,危机花费止于满息平台,
    #: 符合 [18]「不为苟住破息引擎」)
    crisis_buy_bias: float = 1.0
    #: 偏置辖的战力买标签(经济类买 pair/copy/bond_fallback 本就被
    #: 应急滤出,此处显式枚举防未来标签集变化误伤)
    crisis_buy_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'carry_gate',
    })
    #: (refresh_starve_discount/refresh_starve_gold/refresh_game_cap/
    #: levelup_reserve_gold 已随 W126/ADR-0349 删除:刷新×追级并存仲裁
    #: 的评分折扣与约束侧 A/B 通道整体退场——并存由 V_D(概率窗二分:
    #: goal=level_up 时 D 让位)与升级总账自然裁决,不再需要外加折扣)
    # ===== ADR-0305 件3:金充裕买偏置(批㉞④ 评分域杠杆) =====
    #: 金充裕段(≥goldrich_min_gold)的 0 分板面差分买候选顶成正分
    #: 的偏置。诊断(20 局 probe,seed 520-539):金 28-41 段 110 轮,
    #: 店有引擎 54 轮中 9 轮零采纳,主导拒因=「非正分」(0 分板面
    #: 差分 27 次,bond_fallback 32/bridge_core 15/pair 11/engine_seed
    #: 5 张卡评 0)——金充裕时板面差分 0 的成型/凑对件被一刀切拒,
    #: 金滞留无变现通道。**三窗 A/B 否决默认开**(0.5 臂 gap
    #: −1.80/+0.03/+2.47 无一致方向,SD 带 12-16 内):成型加速
    #: 确认(battles_before_e2 3.17→2.38)但 hp 不跟——rung2 保护弱
    #: (池 rung2 桶胜率 44.4%),与件2 结论同根。**默认 0=关闭,
    #: 通道保留**(A/B 可开,同 form_refresh_ev 模式)。
    goldrich_buy_bias: float = 0.0
    #: 偏置生效的金下沿(观察段下沿 28;花 1-4 金在此段内不破
    #: 30/40 息档的段内花费)
    goldrich_min_gold: int = 28
    #: 偏置辖的买标签(经济类 bond_fallback 不辖:凑数散件金充裕
    #: 也不值得占 bench;辖成型/核心/凑对/副本四类)
    goldrich_buy_tags: frozenset[str] = frozenset({
        'engine_seed', 'pair', 'copy', 'bridge_core',
    })
    # ===== ADR-0332 成型补充偏置(d2 评分批;P1 boss 转化) =====
    #: 成型补充偏置:未成型(引擎<2)+ 引擎件候选在破息窗(r≥5 P1,非应急)
    #: 的 0/小负分买入顶成正分的偏置。依据=[13] 成型即停手(未成型=继续买
    #: 配方件)+[27] 每场质量战(引擎完成 win 跳升×剩余战斗≈4.5-5.4 金);
    #: 量级=完成期权的保守下限,只顶 val∈[-interest_rounds, +0.5](单档
    #: 真实息损内;emergency 的 -25 息崖([18])与深负分不被翻越)。
    #: 0=关闭(A/B 通道,同 form_refresh_ev 模式)。
    forming_bias: float = 5.0
    #: 成型补充偏置的顶分上沿(原分 > 此值不加偏置——不叠加已正分买入,
    #: 防 ADR-0301「高单位下进度件挤掉目标件」过冲)
    forming_bias_val_max: float = 0.5
    # ===== ADR-0333 体系集中度(d2 意向批;候选层配方亲和) =====
    #: engine_seed 板面配方亲和过滤开关([20] 过渡是配方不是散买):
    #: True=板面已有未成型体系时,新体系引擎件不生成 engine_seed 候选
    #: (散买断,空窗/成型可开新);False=关闭(回 W70 行为,全引擎件
    #: 见即买)——A/B 通道,默认开。
    engine_affinity_enabled: bool = True
    # ===== W150/ADR-0359 买侧通道锁定目标约束(W143 补充判读通道半边)=====
    #: 总开关:False=回 W145 后行为(A/B 基线臂)。锁定帧
    #: (cw_intention.locked_buy_scope 非 None)时,off_lock_buy_tags 辖的
    #: 买通道候选中「目标件 ∉ 锁定目标体系集」者在层3评分减
    #: off_lock_buy_penalty(降级非禁绝——板面差分显著为正仍可过;
    #: [31]④ 填充不变量:填充通道保持可回收垫层语义,不硬禁)。
    buy_lock_constraint_enabled: bool = True
    #: 约束辖的买标签(W147 基调:优先级/围栏式,禁一刀切禁绝——
    #: 通道=run17 实证的 d2_line_opportunistic/d2_bond_fallback 两通道)
    off_lock_buy_tags: frozenset[str] = frozenset({
        'line_opportunistic', 'bond_fallback',
    })
    #: 非目标件降级分(设计推断,sim 校准;量级=target_hold_value 同阶,
    #: 让非目标件在同轮竞争中让位目标件,且与形成偏置(forming_bias)
    #: 同阶以抵消其对新体系引擎件的顶分)
    off_lock_buy_penalty: float = 3.0
    #: 末轮围栏(候选 B):位面末轮 boss 窗(discipline.plane_last_battle
    #: 口径)时 line_opportunistic 的非目标件直接拒(W143 strict 型=
    #: 末轮 opportunistic 买∧引擎上场件下降联判,run17 直证 r9 四张
    #: 零目标件买入;末轮买入无恢复轮次)。目标件+填充(bond_fallback,
    #: [31]④ 梯队)不辖。
    off_lock_final_fence_enabled: bool = True
    # ===== W155/ADR-0361 evolve 换血事务锁定目标件保护(W147 执行半边)=====
    #: 总开关:False=回 W150 后行为(A/B 基线臂)。锁定帧
    #: (cw_intention.locked_faction_scope 非 None)时,演进提案
    #: (cw_evolution.propose_upgrades)中「目标体系 ∉ 锁定体系集」者在
    #: 最优选择序(_best_option)中减 evolve_off_lock_penalty——
    #: 降级非禁换(W147 基调:成局 22% 良性中性轮换,禁换会伤;
    #: 优先级式让位,全部机会均 off-lock 时照选最优)。
    evolve_lock_constraint_enabled: bool = True
    #: off-lock 演进提案降级分(与 off_lock_buy_penalty 同阶设计:
    #: 让非锁定线提案在同轮竞争中让位锁定线;量级=一档
    #: _TIER_WEIGHT 的 3 倍,跨档压制单档优势)
    evolve_off_lock_penalty: float = 3.0
    # ===== W160/ADR-0363 S1 型成型后引擎丢失修法(两件独立 A/B 通道)=====
    #: 件1·引擎下界守卫:False=回 W155 后行为(A/B 基线臂)。True 时
    #: execute_replacement 生成事务时,若事务净效果使过渡引擎数
    #: (cw_sim._engines_count 口径)从 ≥2 跌破 2,被拆引擎体系的
    #: deployed 贡献件获得新线同级**留场资格**(不划进 old_line 下场)
    #: ——语义「换血可以,拆引擎不行」(ADR-0360 件3 只保「不卖」
    #: 不保「在场」,末轮无回场窗 → 永久丢失;W159 §2:S1 局全部
    #: 37/37 通道=evolve_tx 整批下场)。护的是在场引擎贡献,不是库存。
    evolve_engine_guard_enabled: bool = True
    #: 件2·末轮演进冻结:True 时位面末窗(剩 ≤1 轮,round_num ≥
    #: NODES_PER_PLANE-1)演进换档(undeploy/sell 非空的拆板事务)
    #: 冻结不发射——纯加深(deploy-only)与填位照旧;与 W150
    #: final_fence(ADR-0359 买侧末轮围栏)语义对齐:末轮换档天然
    #: 无回场窗,「加深收益 < 引擎丢失风险」在该窗口系统性为真
    #: (W159 §1:r_loss 90% 落 r8-9)。
    evolve_final_freeze_enabled: bool = True
    # ===== W174/ADR-0371 引擎补完守卫(own-gap 修法)=====
    #: 总开关:False=回 W170 后行为(A/B 基线臂)。True 时
    #: cw_evolution.evolution_step 在常规演进提案**之前**发补完事务:
    #: pair 体系(p1_pair ∪ transition_pair,含希儿系单卡判据)
    #: owned(bench∪deployed,全羁绊口径)≥ tier ∧ on-board
    #: (board_factions 口径)< tier → bench 该体系成员上场,room 不足
    #: 换下最弱非保护件(保护=pair 成员/引擎件/锁定目标件/种子窗)。
    #: 修「拥有≥门槛却从未同时上场」(W173:8/11 never-2 局,件躺备战
    #: 席到局终;[20] 件上场才算配方,[13] 过渡成型≈过 P1)。末窗冻结
    #: 豁免复核 = 净效果 pair on-board 与引擎数不减(ADR-0363 件2
    #: 防丢语义同向:补上不是拆)。
    evolve_engine_completion_enabled: bool = True
    # ===== W179/ADR-0372 P1 早期新件买入门(双条件窗:缺件密度 × 息档口径)=====
    #: 总开关:False=回 W174 后行为(A/B 基线臂;FORM 相位地板对配方对
    #: 件买入照旧全拒)。True 时 arbiter.gold_floor 对满足窗的 BuyCard
    #: 放行「买入后同息档」的购买(窗语义见 discipline.p1_early_gate_open
    #: 与 arbiter 的逐笔息档/单轮上限检查)——修 W173/W175 的 pass_buy
    #: 形态(own<门槛=买少了:缺件曾 1-3 费出现在店、金 7-15 金穷轮,
    #: 被 FORM 地板 20 一刀切拦掉,违反口述 [11] 档内购买不损息)。
    p1_early_gate_enabled: bool = True
    #: 窗的缺件密度门槛:派生配方对(cw_intention.p1_early_pair,未锁期
    #: 同样派生)未持有 distinct 对成员数 ≥ 此值才开窗。标定(W179,
    #: n=100 池 861fc9f6):全体 P1 轮 unheld 分布 [8,16](r1 p10=14 /
    #: r9 p10=8),pass_buy 病灶轮 unheld 11-15——k 在 [1,8] 带内对本
    #: 分布**无区分度**(诚实记档:operative 约束=息档口径+单轮上限+
    #: 层3评分),取 6=「板面远未覆盖配方对」的语义守卫(关掉假想的
    #: 近成型窄窗,防未来分布漂移把门开进不该开的段)。
    p1_early_min_missing: int = 6
    #: 单轮放行笔数上限(防 r1 扫店):同息档口径下金 12-19 连买 1费
    #: 可达 2-9 笔(W179 标定:门内笔数 p50 0-1 / p90 1-3 / max 7,
    #: 病灶轮 1-2 笔)——取 1=「目标件刷新出现=唯一最高优先级,只买它」
    #: ([31]② 逐字口径;n=100 扫描 cap1 出口金 34.23 与基线 34.25 持平
    #: =P13 同档零损的理论预测逐位兑现;cap2 −2.3 金换 hp +1.3,
    #: 出口金口径上不如 cap1 干净)。每轮增量支出 ≤3 金,息损上界=档内 0。
    p1_early_round_cap: int = 1
    # ===== W184/ADR-0373 卖侧唯一体系引擎守卫(S2 恶化谱系)=====
    #: 总开关:False=逐位回 W179 后行为(A/B 基线臂)。True 时
    #: discipline.sole_engine_sell_blocked 命中的件不进任何卖件通道——
    #: 判据=该件是四过渡体系(TRANSITION_TRAITS 三羁绊:仙舟/列车同行/
    #: 持续伤害,全羁绊 factions∪flows 口径;W192 起希儿系贡献件另经
    #: guard_seele_scope_enabled 并入辖域)成员,且其所属某体系的
    #: 在手件数(bench∪deployed 逐件计)≤ 该体系 tier 门槛 → 卖出会
    #: 「清空该体系当前唯一 owned 引擎件」或「在手数跌破 tier」。
    #: 消费面=candidates._sell_tag(arbiter off_target/for_gold/
    #: free_bench 候选生成)+ discipline.sell_priority_key 守卫
    #: (carry_gate ④/两补偿器统一挡)。修「演进换线把旧体系件下场到
    #: bench 后被 off_target 当死库存卖出 → 体系引擎永不回场」
    #: (W181 §3:S2 恶化 {37,71,90,43} 与 W174 残差 {45} 全此链;
    #: 卖出的件均非 engine_char_names 名单件,方向切换后失去目标身份)。
    #: 不辖:非 TT 件/owned>tier 的冗余件(体系有余量时清仓照旧)/
    #: execute_replacement 保留序卖出(ADR-0360 件3+ADR-0363 件1
    #: 已辖)/谷底回滚 SellDeployed(恢复机件)。
    sell_sole_engine_guard_enabled: bool = True
    # ===== W192/ADR-0375 希儿系守卫辖域补全(W190 巡检两件)=====
    #: 希儿系(四过渡体系之一,单卡判据)并入卖侧唯一体系引擎守卫与
    #: 演进保护集辖域(**核心条件辖**,域修正见 ADR-0375):希儿本人
    #: 唯一种子不可卖/恒保护;放大器件(量子同频/贝洛伯格)仅当希儿
    #: 在手时辖(卖拒=放大阵营在手 ≤2 成型门槛;保护集并入——补完
    #: undeploy/execute_replacement 保留序不下);无希儿时放大器
    #: 不是体系件(transition_combos:28 帖全部含希儿),照旧合法面。
    #: False=逐位回 W188 后行为(辖域=TRANSITION_TRAITS 三羁绊——
    #: deploy 排序语义被 ADR-0373/0371 借用造成的缺口,见 W190 洞一/二)。
    #: **新 flag 而非复用 sell_sole_engine_guard_enabled**:后者 off 会
    #: 连 TT 三羁绊辖域一起关,A/B 配对臂(只隔离辖域差)与回退粒度
    #: 都不对;辖域修正是 0373/0371「四体系」声称的语义补全,默认开。
    guard_seele_scope_enabled: bool = True
    # ===== W197/ADR-0380 卖侧下界守卫执行点补全(own_gap 演进谱系)=====
    #: 总开关:False=逐位回 W195 后行为(A/B 基线臂)。True 时
    #: ``sole_engine_sell_blocked`` 的「TT 体系件在手≤tier 不可卖」
    #: 语义在两个此前无守卫的执行点生效:
    #: ① arbiter 卖候选采纳点复检(对 working 前序采纳后的状态逐笔
    #:    复检——候选生成是对批前状态计数,同段两笔同名 TT 件逐笔
    #:    合法而聚合跌破 tier,136 r7 两笔三月七 3→1 实证);
    #: ② execute_replacement 溢出卖出下界(bench 满截断保留序时,
    #:    rank0 保护件被卖出 → 改为留场不下场,新上场名单收紧——
    #:    ADR-0373 不辖清单第 3 条对「卖出面」的豁免撤销,保留序/
    #:    undeploy 语义不变;136 r9 benchOcc=9 卖 deployed 椒丘实证)。
    #: 判据单一源 = discipline.sole_engine_sell_floor_plan(批量口径,
    #: 前序可卖件计数扣减;单笔与 sole_engine_sell_blocked 逐位一致)。
    #: 不辖:owned>tier 冗余件清仓/undeploy 下场(ADR-0373「禁下场
    #: 压死良性轮换」语义保持)/补完事务 sell(_locked_protected_names
    #: 引擎键∪pair 成员保护已覆盖,W192 辖域不变)。
    sell_floor_exec_guard_enabled: bool = True
    # ===== W194/ADR-0378 [33] 稳态 LevelUp 多击组(W185 泛化)=====
    #: 总开关:False=回 W193 后行为(A/B 基线臂——多击组只在轮内
    #: deploy_cap 拒绝触发补偿时发射,Catch-22 原状)。True 时
    #: arbiter 末段主动发稳态多击组(remediation.steady_state_
    #: levelup_group):进轮 cap 满 ∧ bench 有方向件([33] 稳态字面
    #: 语义)→ [LevelUp]*clicks_to_next_level 整组,授权=
    #: levelup_ev_basis 按 n×总价(稳态下人口位臂天然成立)+
    #: 逐动作 gold_floor 事务性重验(与 deploy_cap 补偿臂同一重验
    #: 链)。修「恒 lv6 通道缺陷」(W185:每轮 1 击吞吐,lv6→lv7 需
    #: 7 轮,死亡窗内不跨;run15 型死局的 lv7 价格带永不可达)。
    #: 每轮至多一组(session.v2_steady_lv_used 轮键,防刷后 re-decide
    #: 段链连发);boss 轮禁升([32])与 level_max 前置守卫保留。
    #: **辖域 P2+**(首版全位面泛化 n=300 引入 P1 never2 9→10 回归,
    #: W194 辙回——P1 多击已由 deploy_cap 补偿臂覆盖)。
    levelup_multihit_enabled: bool = True
    # ===== W194/ADR-0378 件3:P2 核心件首件同档买入门(W183 方向②)=====
    #: 总开关:False=回 W193 后行为(A/B 基线臂)。True 时 P2 段
    #: (plane≥2)意向核心(v3_core_names)的**首件**(working 现持无
    #: 同名)在 gold_floor 拒绝前放行「买入后同息档」的自然店购买
    #: (arbiter._p2_core_firstpiece_exempt)——[31]②「目标件刷新出现
    #: =唯一最高优先级」+[11] 同档零息损+[22]③ 弃购代价=再遇窗口
    #: (3费@lv6 E=27 次刷新 / 5费 60-180 轮)。修 W194 探针实证的
    #: 「P2 穷轮(gold<50)核心件在店被 HOARD 地板 50 一刀切拦」
    #: (n=10:核心在店 6 轮漏买 5,全部 gold≤12 穷轮)。单轮 1 笔
    #: ([31]② 只买它);零刷新授权(与 W170/W185 刷门管辖不交集)。
    p2_core_firstpiece_enabled: bool = True
    #: (form_refresh_ev/form_refresh_max_round/form_refresh_min_gold/
    #: form_refresh_engines_target 已随 W126/ADR-0349 删除:成型找件刷新
    #: A/B 残留通道退场——找件语义由 V_D 批口径承接(核心未齐+概率窗内
    #: 的定向找件是 V_D 的本体场景,不再需要独立常量通道))

    # ===== 层4:预算仲裁(约束清单——一处定义,全部候选受辖)=====
    #: 执行约束名序(仲裁器按序施加;filters/arbiter 按名映射实现)
    constraints: tuple[str, ...] = (
        'gold_floor',          # 金≥地板(地板按覆盖态分派)
        'interest_rule',       # [11][17][28] 息档保持/满息结余
        'bench_capacity',      # bench 9 槽(含本轮已采纳买)
        'copies_cap',          # 同名星级加权 ≤3 份
        'same_round_mutex',    # 同轮已买禁卖/已卖禁买(r408 族)
        'boss_levelup_ban',    # [32] boss 轮禁升级腾席
        'deploy_cap',          # 上阵数 ≤ max_units
    )
    #: 地板表(金≥地板;覆盖态分派——审计表 gold 行的消费值)
    interest_floor: int = 50      # [17] 满息地板(常态/追赶)
    war_floor: int = 30           # 战力模式地板(计划内补强非 panic)
    rebirth_floor: int = 20       # [18] 应急保留重生基数
    boss_floor: int = 10          # r278 boss 破息地板
    #: (levelup_interest_engine_gate 已随 W119 删除:[12] 门收编 EV 总账
    #:  ——ev.levelup_ev_authorized 单一裁决,ADR-0347;A1/A2 镜像清)
    #: (refresh_game_cap/levelup_reserve_gold 已随 W126/ADR-0349 删除:
    #: refresh_budget 约束整体退场,D 的预算由 V_D 批口径评分+
    #: gold_floor/interest_rule 辖)
    #: [32] boss 轮判定(node_type_current='boss';P1 r9 兜底同辖)
    boss_round_node_types: frozenset[str] = frozenset({'boss'})
    #: LevelUp 等级上限(封顶 10)
    level_max: int = 10
    #: bench 槽容量(游戏常数 9)
    bench_capacity: int = 9

    # ===== 完备性审计表(ADR-0290 对抗修订④)=====
    #: 资源维 × 回合态维矩阵;每格 = constraints 内的约束名,或
    #: ('none', 显式声明原因)。「无约束覆盖」必须显式声明,禁止空格。
    #: 检查项 decision_v2_arbiter_matrix 锁「无空格 + 约束名存在」。
    audit_matrix: dict[tuple[str, str], tuple[str, ...] | tuple[str, str]] = field(
        default_factory=lambda: {
            # (资源维, 回合态维) → (约束名...) 或 ('none', 原因)
            # ('catchup' 列已随 W126/ADR-0349 追赶态退场改为 'mode' 常态列)
            ('gold', 'boss'): ('gold_floor', 'interest_rule'),
            ('gold', 'emergency'): ('gold_floor',),
            ('gold', 'mode'): ('gold_floor', 'interest_rule'),
            ('bench', 'boss'): ('bench_capacity',),
            ('bench', 'emergency'): ('bench_capacity',),
            ('bench', 'mode'): ('bench_capacity',),
            ('slot', 'boss'): ('boss_levelup_ban',),
            ('slot', 'emergency'): ('bench_capacity',),
            ('slot', 'mode'): ('deploy_cap',),
            ('round_mutex', 'boss'): ('same_round_mutex',),
            ('round_mutex', 'emergency'): ('same_round_mutex',),
            ('round_mutex', 'mode'): ('same_round_mutex',),
        })
    #: 审计表两维的显式枚举(新增动作类型/资源维时审计表强制过检)
    audit_resource_dims: tuple[str, ...] = ('gold', 'bench', 'slot', 'round_mutex')
    audit_round_state_dims: tuple[str, ...] = ('boss', 'emergency', 'mode')


#: 默认注册表(ADR-0293 标定后;A/B 时构造改动副本注入
#: DecisionV2Strategy)
DEFAULT_REGISTRY = DecisionV2Registry()
