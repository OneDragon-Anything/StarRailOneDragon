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
        'engine_seed', 'plugin', 'pair', 'copy', 'copy_press',
        'bond_fallback', 'carry_gate',
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
        'engine_seed', 'plugin', 'pair', 'copy', 'copy_press',
        'carry_gate',
        'bond_fallback', 'off_target', 'for_gold', 'free_bench',
        'levelup', 'refresh', 'deploy',
    })
    war_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'pair', 'copy', 'copy_press',
        'bond_fallback',
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
        'engine_seed', 'plugin', 'pair', 'copy', 'copy_press',
        'bond_fallback',
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
    #: 剩余战斗节点估计(V_D P1 收益侧的**缺省兜底**:plane_node_table
    #: 槽序表缺失/裸 session 时退此值;有表时由 ev.battles_left_plane
    #: 逐轮推导,ADR-0425;层3 score_state 的 power 视界仍用本值)
    battles_left_est: float = 5.0
    #: 单场战斗典型掉血(层3 power 视界骨架值,V_D P1 收益侧已改用
    #: vd_p1_loss_* 遥测拟合+state 推导,ADR-0425;本值仍辖层3 power)
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
    #: P1 收益侧战斗期望掉血=条件败局伤害的线性拟合**截距**(遥测拟合:
    #: W324 战斗粗模型冻结语料 417 条战斗类差分,battle 节点败局伤害
    #: =截距+斜率×成型档,battle n=278/73 局聚类稳健、斜率 SE 1.25;
    #: 产物=fit_results.json 的 two_state_model.battle,W324 归档目录;
    #: 语义=「打了但输了」的伤害期望,与 V_D 收益式的 Δwin_rate 相配
    #: ——无条件均值拟合会与胜率差双计,ADR-0425)
    vd_p1_loss_intercept: float = 11.32
    #: 同上**斜率**(每级成型档;遥测拟合,负号=成型越高败局伤害越低;
    #: rung 域 0-3,越界钳制在消费函数)
    vd_p1_loss_slope_rung: float = -0.37
    #: 连胜 EV 地板(discipline._streak_floor)的**条件败局伤害**拟合表
    #: (encounter/boss;battle 复用 vd_p1_loss_* 单一源,不立第二份)。
    #: 口径=条件败局伤害(two_state_model:「打了但输了」的期望,胜率
    #: 单列)——与胜率相乘不双计(math_proofs P15 口径命题);误用
    #: 无条件均值拟合(胜态混在均值里)会系统性低估。来源=W324 冻结
    #: 语料 417 条拟合产物 two_state_model(.debug/temp/currency_war/
    #: w324_coarse_battle/fit_results.json);encounter=截距 24.32 +
    #: 斜率(−4.53)×成型档(斜率 SE 2.41 显著);boss 斜率 CI 含 0 →
    #: 退常数 26.71(背测 sim −22.61 vs obs −25.82)。
    streak_floor_loss_damage: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            'encounter': (24.32, -4.53),
            'boss': (26.71, 0.0),
        })
    #: 连胜 EV 地板胜率表(节点类型×成型档;取**注入后**值 p_injected
    #: =语料实测+plaza 先验只进 rung≥2、share≤0.25,来源同上
    #: fit_results.json 的 win_rate_table_injected)。键域 0-2(消费侧
    #: 成型档封顶 2,与 h3_win_rate 同法);不与 h3_win_rate 合并
    #: (h3=battle 骨架插值表辖层3,本表=实测注入表辖连胜地板)。
    streak_floor_win_rate: dict[str, dict[int, float]] = field(
        default_factory=lambda: {
            'battle': {0: 0.009, 1: 0.356, 2: 0.315},
            'encounter': {0: 0.038, 1: 0.026, 2: 0.264},
            'boss': {0: 0.077, 1: 0.027, 2: 0.187},
        })
    #: P2 掉血期望(P12 收益侧,**条件败局伤害**口径——与 Δwin_rate 相乘
    #: 不双计,P15 口径命题;=「打了但输了」的期望)。标定=P2 损血谱粗档
    #: (.debug/temp/currency_war/w353_p2_survival/w354_p2_loss_calib.json,
    #: 冻结语料 w324 同 run 相邻行 hp 差分):普通战斗桶 20.05(n=19;
    #: 桶内零损行=0,实测口径核验=条件伤害)。置信声明(W371 审计 M3):
    #: SD 10.38,事件级 t95% CI [15.0, 25.1],run 级聚类 bootstrap CI
    #: [15.1, 23.6](19 事件来自 13 run)——区间半宽 ±25%,取 20.05 与
    #: 取保守 22-25 在现有 A/B 判据下不可分辨,本值不做精度主张。
    #: 三源对照:语料条件 20.05 / 实机存活局事件均值 −15.3(59 事件,
    #: W350 REPORT §4)/ sim coarse 分 rung 条件伤 ~11——取语料上沿的
    #: 理由=删失剔除 hp≤1 死亡行 → 低估方向。
    #: **benefit 项量级声明**:dwin 侧 h3_win_rate 为 P1 校准骨架阶梯,
    #: P2 分 rung 胜率表未标定(挂账)——本项只作「P2 掉血更贵 → 找件
    #: 账方向上调」的方向修正,量级未标定,不得引用「P2 胜率≈0」类
    #: 论证抬升(损失侧条件口径必须配同 regime 胜率,P15 精神)。
    #: encounter 16.67(n=3 样本极小不采)/boss 桶零样本(沿用 26.71)
    #: 不进本标量;普通战斗为 P2 主导节点型。旧值 16.0 系实测带拍值,
    #: 无标定依据,已重校。
    vd_p2_loss: float = 20.05
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
    #: 填充件升星期权项单位值(W232/ADR-0402 方案A,[15]/[22] 压库
    #: 副本素材 × [27] 中期投资持续变现)。merge_progress/core_star
    #: 只辖目标集内名字——降级梯队填充件(bond_fallback/pair 通道
    #: 买入、板上多数)的第 2 份买入全评分维零 delta 被「非正分」
    #: 结构性拒(W231 诊断 §②-1:478 机会八成漏买、进场 star≥2 仅
    #: 7.7%)。本项对**已 deployed** 填充件(目标集外名字)的第 2 份
    #: 同名 1★ 计期权分。硬边界:只辖已持有名的第 2 份(压库语义,
    #: 不授权为填充件 D 牌刷新);copies_cap 沿用(仲裁层守卫);
    #: 只辖已 deployed 名(纯 bench 囤件不折,ADR-0295 同式边界)。
    #: **默认 0=关闭**(=现行为零漂移,同 goldrich_buy_bias 的
    #: A/B 通道保留模式,ADR-0305 先例);三臂 A/B 见 W232 报告。
    filler_star_unit: float = 0.0
    #: 方案B(W232/ADR-0402):同名副本豁免 pair_wants 方向门。副本是
    #: 升星素材(filler_star/merge_progress 期权通道)而非新方向投资,
    #: 方向门拦它=语义错位(W231 §②-3:45 张/100 局同名机会被方向门拦)。
    #: 判定位置=candidates._buy_tag 方向门(pair_wants)之前、r408 同轮
    #: 已卖守卫之后(与冷启动例外 r383b 同型,提为全轮域)。**与 A 同臂
    #: 开**:单独开 B 时解锁的副本买入在评分层仍零 delta(unit=0 时仅
    #: 偶发 depth 分),零漂移门要求默认关=现行为逐位一致——两开关
    #: 默认同为关,A/B 臂(u0.5/u1.0)同时开。
    pair_copy_direction_exempt: bool = False
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
    # ===== W201/ADR-0381 补完缺口 owned 口径(distinct;修②)=====
    #: 补完事务缺口判定的 owned 计数口径:True=distinct 名单数——
    #: 同名副本是 3合1 升星素材非配方件([20] 配方=不同成员;board
    #: 同名唯一 → 副本永远不可上,全羁绊逐件计数会造出「永远填不满
    #: 的幻影缺口」,W200:227/276 补完轮轮空转);False=回 W174 后
    #: 全羁绊逐件计数(ADR-0371 首版口径)。
    engine_complete_distinct_owned: bool = True
    # ===== W202/ADR-0382 补完保护集分级(136 型构造闭死修法)=====
    #: 补完事务 undeploy 常规候选枯竭(deployed 全保护,W200 136:
    #: 锁定线件+引擎件全覆,列车缺口 r6-r9 轮轮被选但 tx 永远建不出)
    #: 且缺口体系已连续被选 ≥4 轮(标定:门 2/3 有 benign→mal 坏翻转,
    #: 门 4 全硬门过——benign→mal=0/mal 24→20/never2 10→7)时,
    #: 按分级序降级换血:G0 非引擎锁定线件(locked_buy_scope∩非TT,
    #: 最可动)→ G1 未成型引擎件(下之不拆成型引擎)→ G2 已成型
    #: 引擎件/pair 成员/希儿系贡献件恒不可动。依据 [13] 过渡成型≈
    #: 过 P1(成型缺口=发令枪级)让位于 [23] 锁定线语义;False=回
    #: ADR-0371/0381 后「不硬拆」。
    engine_complete_grade_down: bool = True
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

    # ===== W300 press 通道:目标外同名副本压库购买(7 参数,V-B3 全量
    # registry 化;arm0=默认值全关零漂移,armA=注入开启;A/B 结论落地后
    # 按 ADR-0411 先例逐字段裁决去留)。设计=唯一规格:
    # .debug/temp/currency_war/w300_dup_ruling/design.md v3 节(V-B0~V-B9)。
    # A/B 兑换统一裁决表(V-B4;锚定义=design §5.3,冲突处以本表为准):
    # | R1 | star≥2 升≥MDE ∧ 进场金/出口质量/经济卫生副锚均不劣 → 落码+ADR+三同步 |
    # | R2 | star≥2 持平(<MDE)∧ seg 真拦残留≤0.15 ∧ 其余锚不劣 → 落码
    #      (「有效收敛」;P4 张力=收益主体在 sim 不可观测的期权/对手面,
    #      ADR Considered Options 必含张力节+向用户呈报观测极限) |
    # | R3 | star≥2 降超噪声带 ∨ seg 真拦残留>0.15 → 不合入,回炉
    #      (首要嫌疑=插入候选挤占金预算,看进场金分布移位) |
    # | R4 | star≥2 升 ∧ 经济卫生副锚劣化超噪声带 → 降级调常量
    #      (press 臂加 after≥息档线同档语义收紧),不硬合入 |
    # | R5 | armA 触发样本不足(可达性短跑 E02 形态样本<30)→ 不合入,
    #      通道判「sim 内不可达」,转构造账本锁评估 |
    #: 全通道总闸(False=通道整体不评估,现行为零漂移;True=press 臂
    #: +candidates 守卫豁免臂+§3.3 三相位 [11] 地板前置臂+检查器
    #: C-B/C-C 发射同步开——A/B 捆绑为一臂,双臂同尺,V-B4.2)。
    #: C-B/C-C 发射同步开——A/B 捆绑为一臂,双臂同尺,V-B4.2)。
    #: 默认开(W368 A/B:n=300/臂 R2 成立——seg 真拦 −85.6%、通道开通
    #: copy_press_channel_closed 41→0、439 轮替代买进、core2≥1 +24.7pp 显著、
    #: 成型率 +6pp 显著、零回退;star≥2 +3.0pp 不显著如实;对照臂注入 False 保留)。
    press_channel_enabled: bool = True
    #: band 推导质量线(V-B5.2:0.50 在 P1 开域内被口述锚 [30]「1-2 费带」
    #: 覆盖,仅 lv≥7 中后段生效而彼时带自洽闸已关通道——本参数是中后段
    #: 守卫参数非行为旋钮;敏感性扫描=主批硬前置,发现敏感再立项)。
    press_band_cum_threshold: float = 0.50
    #: 停机护栏(V-A2 继承):press_channel_open 的开域上界(lv≤此值
    #: ∧ plane==1)与带自洽闸参照系 press_band(此值)={1,2}。
    press_channel_max_level: int = 6
    #: 评分偏置(V-B2.2):tag='copy_press' 候选的板面差分加此值——
    #: press 通道自带独立给分域,修 W231 副本评分结构性零分;不改
    #: filler_star_unit 默认值,既有 A/B 通道零波及。armA 初值 0.5,
    #: 网格 {0.25, 0.5, 1.0}(量级锚=off_target_sell_bias 0.5 /
    #: crisis_buy_bias 1.0 的「顶零为正」先例);0=关闭。
    press_copy_unit: float = 0.0
    #: press 候选逐轮采纳笔数上限(V-B8.1,更严一级;量级=单轮至多
    #: 一笔压库副本,与 p1_early_round_cap=1 同式轮键计数)。
    press_copy_round_cap: int = 1
    #: [11] 同档/1费豁免臂(§3.3 三相位共用前置臂)逐轮放行笔数上限
    #: (V-B8.1;量级锚=W179 p1_early_round_cap=1 先例,取 2 因该臂辖
    #: 方向内候选+press 候选两股)。
    press_exempt_round_cap: int = 2
    #: E08 评分前置分量(V-B7):copy_press 候选中「同名 ∈ 己方上场核心」
    #: (压库+断对手粮双重红利,〔补②〕)再加此值——E08 相对前置落为
    #: 评分分量,arbiter 分数贪心(arbiter.arbitrate 的 sorted key)为
    #: 唯一跨候选序,V-A4 COPY_PRIORITY_* 整数键系废除不实现。0=关闭。
    press_core_mirror_bonus: float = 0.0

    #: (form_refresh_ev/form_refresh_max_round/form_refresh_min_gold/
    #: form_refresh_engines_target 已随 W126/ADR-0349 删除:成型找件刷新
    #: A/B 残留通道退场——找件语义由 V_D 批口径承接(核心未齐+概率窗内
    #: 的定向找件是 V_D 的本体场景,不再需要独立常量通道))

    # ===== W227/ADR-0400 P1 末窗承接门(设计件 08 §4.2 Phase 1)=====
    #: ADR-0411 flag 家族清理(2026-09-03):承接门自本批起**无条件启用**
    #: ——历史 handoff_gate_enabled 布尔字段删除。验证史:W247/W254-R
    #: 两轮复核 gate 单开 outcome 无正方向(W254 判边际为负),但门是
    #: star/refresh 两通道授权的判据语境(gap 单一源),行为面随其一并
    #: 转正;裁决与四通道验证结论单一源 = ADR-0411。
    #: 行为语义:P1 末窗(r>=handoff_gate_min_round)投影承接档位
    #: (handoff.handoff_gate_gap 单一源)未达标:①成型停手线不停手
    #: (filters.formed_stop_active 承接维,[18] 位面末 ALL IN 的承接
    #: 扩展);②interest_rule 买侧破息 EV 账加缺口项
    #: (handoff_ev_gap_bonus×缺口)。只辖 P1 末窗(P1 非末窗零漂移
    #: 门的结构前提)。量级常量保留供调优。
    #: 末窗下界。原初值 8 口径=W227/ADR-0400「P1 r8-r9(boss 窗)」。
    #: **W288/ADR-0418 前移 8→6**(W275 三映射兑换:「方向对、量级待
    #: 实机定标」类常量调整):合资格授权窗加宽到 {r6..r9},承接门家族
    #: (filters 成型停手承接维/arbiter 缺口项/candidates 副本放行/M-A
    #: 定向刷新窗)整体提前点火。证据链(W275 四臂配对 AB,n=200,v11
    #: 冻结池 7af81977 同 seed):core2≥1 进场率 12.17%→18.85%(配对
    #: 翻转 22:9,二项单侧 p≈0.025;剂量-响应单调 gr7 15:7);进场金
    #: 均值差 −1.50 CI 含零(金面免费);末 HP/hp0/P2 进场率全无信号。
    #: 落地前置双核验过(.debug/temp/currency_war/w288_gate_landing):
    #: ① cw_replay 双臂重放历史局,分歧仅限 P1 r6+(r1-5/P2/P3 零漂移);
    #: ② 提前窗买质量**反升**:r6/r7 买入的 off 散件率 6.1%→3.6%
    #: ——不是拿便宜副本填窗。已知耦合(wart,详见 ADR-0418):
    #: handoff_boss_reward_bonus 触发条件绑定本常量,前移后 +2 在 r6
    #: 触发,且投影公式(r8 视角标定)在 r6/r7 少算后续节点期望伤害——
    #: 该畸变端到端存在于测量臂内=被测行为的一部分;解耦需改行为代码
    #: 并重跑 AB,挂账 ADR-0418。
    handoff_gate_min_round: int = 6
    #: 承接达标总档位(handoff_tier 下限;ADR-0399 标定结论:总档位
    #: 实际两档,门控语义足够——目标 1=「承接不足判定档」)
    handoff_gate_tier_target: int = 1
    #: EV 承接缺口项单位值(缺口 1 档 = 买侧 V 加此值;量级=forming_bias
    #: 同阶的保守下限——只放宽末窗破息买的 EV 授权,不触地板族/升级账/
    #: 刷新口径(ADR-0352 D 平面 R 上界纪律不动))
    handoff_ev_gap_bonus: float = 5.0

    # ===== W238/ADR-0403 承接门 hp 维 boss 投影(设计件 09 §3.1)=====
    #: ADR-0411 flag 家族清理:投影自本批起**无条件启用**——历史
    #: handoff_boss_project 布尔字段删除(曾默认关:W238 三臂 A/B 后
    #: 未解锁;转正裁决见 ADR-0411——量级问题非行为开关)。语义:
    #: handoff_gate_gap 末窗投影的 hp 维由「当前 hp(boss 前)」换
    #: 「boss 后投影 hp」:
    #: hp_proj = hp + 2(r8 奖励胜,设计件 09 §1.1 五局恒 +2) −
    #: E[boss 伤害|净星深档](r9 无 +2;W240 起档键=净星深,
    #: ADR-0404)。修标定口径错位(喂给
    #: HANDOFF_HP_CUTS(boss 后真值标定,ADR-0399)的 hp 取 boss 前值
    #: = hp 维系统性高估一档;设计件 09 §2)。
    #: E[boss 伤害|净星深档] 常数表(**正数=期望掉血量**;离线标定非
    #: 运行时预测)。标定源=Δ池 plane=1 boss 桶(**净星深键** = 上场件
    #: Σ(star−1) 桶 min(sd//3,5)*3,W240/ADR-0404 替旧 Σboard 键——
    #: 修 3合1 升星使 Σboard −2/次落浅桶而浅桶期望伤害更大、sim 判
    #: 「升星→boss 伤害↑」与 [27] 机制相反的方向冲突)地板删失行剔除
    #: (hp_after∈{0,1}=下界非真值,ADR-0307 口径)后的桶均值:
    #: 2026-09-03 重标定 n=28 未删失/删失 21,**桶 0:n=28/27.57——
    #: P1 boss 语料净星深全落桶 0**(旧 Σboard 桶 9/12/15 的条件性
    #: 系键口径伪影:升星减件使强板落浅桶、浅桶均值被强板样本抬升
    #: ——方向冲突的语料侧成因,ADR-0404)。
    #: 标定脚本与逐行口径=.debug/temp/w240_calibrate_boss_star.py
    #: (W238 旧标定见 ADR-0403)。**已知边界**:删失剔除使留存样本
    #: 偏向「存活 boss 的局」(弱板真值伤害被低估);净星深≥3 的
    #: 深桶零样本——star_depth 条件性在当前语料下不可辨,常数表
    #: 实为无条件期望,语料攒厚后复验。
    #: boss Δ 全分布双峰(W244,2026-08-27):低伤簇 n=8 均值 13.25(SD 1.04)/
    #: 高伤簇 n=20 均值 34.10(SD 1.77),中间带 [16,26) 零观测——单值均值
    #: 27.57 落谷底不近似任何真实伤害。**投影口径取 Q3≈34**(保守:均值使
    #: hp 临界局 tier 高估一档=重蹈 W234 缺口;低估方向仅更保守可 AB 校正);
    #: 协变量(Σboard/净星深/日期/comp/streak)无一解释簇归属,嫌疑首因=
    #: boss 敌型(outcomes 无 boss_name 字段——数据采集欠账,攒齐后按敌型
    #: 混合重标定)。分布数字与脚本=.debug/temp/currency_war/w244_*
    handoff_boss_e_damage: dict[int, float] = field(default_factory=lambda: {
        0: 34.0,
    })
    #: 缺桶 fallback:同上 Q3 口径(单桶语料下与桶 0 同值)
    handoff_boss_e_damage_default: float = 34.0
    #: r8 奖励节点胜 +2(设计件 09 §1.1:五局全部 r8→r9 恒 +2;hp 不可
    #: 回复下唯一正项)。触发条件历史绑定 handoff_gate_min_round(值=8
    #: 时恰为「r8 加、r9 不加」);W288/ADR-0418 该常量前移到 6 后触发
    #: 点随移至 r6——语义已偏离「r8 奖励」本义(r6/r7 投影少算后续节点
    #: 期望伤害,偏乐观),解耦挂账 ADR-0418(改行为代码须重跑 AB)
    handoff_boss_reward_bonus: int = 2

    # ===== W242/ADR-0405 末窗星级定向授权(W232 挂账 C 项;设计件 08
    # §4.2 Phase 1b 星级投资方向)=====
    #: ADR-0411 flag 家族清理:末窗星级定向授权自本批起**无条件启用**
    #: ——历史 handoff_star_directed 布尔字段删除。验证史:W242 四臂
    #: A/B 行为面强正(core2≥1 进场率 +150%)但单独不改变结局;转正
    #: 依据 = star 是 W231「评分结构性拒副本」病灶的正解且 sim 无挤出
    #: (量级不足属参数调优非行为开关,裁决见 ADR-0411)。行为语义:
    #: P1 末窗(r>=handoff_gate_min_round)承接缺口 gap>=1
    #: (handoff.handoff_gate_gap 单一源)对**同名副本买入**给定向授权
    #: ——candidates 层放行副本候选生成(r410 守卫+方向门,W232 A/B
    #: 豁免的 gap 条件化分支)+ arbiter 非正分门放行副本(W231 主因:
    #: 副本评分零维被结构性拒,到不了 EV 账)。**授权值单一源 =
    #: interest_rule 的 handoff_ev_gap_bonus×gap(零新增数值通道/
    #: 防双计)**;地板族/copies_cap/r408 同轮守卫/bench 容量照常辖。

    # ===== W252/ADR-0409 M-A 定向 D 牌授权窗(W249 诊断修法)=====
    #: ADR-0411 flag 家族清理:M-A 定向刷新自本批起**无条件启用**
    #: ——历史 handoff_refresh_directed 布尔字段删除。验证史:W252
    #: 三臂 AB merges +47%/hp0 改善但 cap6≈半跳量级;转正依据 = M-A
    #: 是 W249「策略从不支付搜索成本」病灶的对症修法且方向为正
    #: (量的解锁归 cap 提升独立批,裁决见 ADR-0411)。行为语义:P1
    #: 末窗承接缺口 gap>0(handoff.handoff_gate_gap 单一源复用)**且**
    #: 存在追名 peak≥2 的目标件(锁定采购目标名集内某名 star 加权在
    #: 手副本 ∈[2,3),距 3合1 只差最后一张)时,向刷新(RefreshShop)
    #: 开放有界预算。**只辖刷新维**(防双计,W232 A/B/W242 C 各辖买牌
    #: 维,互斥边界:同一动作只有一条授权来源——买候选走既有
    #: interest_rule 缺口项/copy 放行路径不动;refresh 候选要么走既有
    #: V_D 正分/gold_floor 路径,要么凭本预算有界放行,无叠加);
    #: copies_cap/r408/bench 容量等约束链照常辖。
    #: 单合资格轮刷新次数上限(W249 白盒估算初值:每轮 ≤2 次)
    directed_refresh_per_round: int = 2
    #: 每局刷新总上限(W249 白盒估算初值:≈覆盖一颗 2★ 的第二跳
    #: 6-7 次;消耗计数 session.v3_dir_refresh_used,decide_prep 轮首
    #: 不重置——局级累计)。金消耗披露面:预算放行的每次刷新照付刷价,
    #: 金账户由 simulate 真值扣减,P1 末窗利息损失随 A/B 守门指标判读。
    #: **本常量是非绑定约束(W274/ADR-0413)**:合资格授权窗 = gap>0 ∧
    #: r>=handoff_gate_min_round(W288/ADR-0418 前移到 6 ⇒ 窗 {r6..r9}),
    #: per_round 2 ⇒ 窗内可行上限 8 次曾在本值 6 之上;W275 gr6 臂
    #: (n=200 同 seed 配对)dir 授权 339 次、cap 开始参与钳制(窗容量
    #: 8 > cap6),行为面为正(core2≥1 +6.7pt)——cap 是否重新 bind 的
    #: 定标归后续实机/大批核对,非本批变更理由。历史候选档
    #: 留证:cap10/cap14 曾作为「第二跳吞吐量级」修复候选(W254-R 断点),
    #: 实验证明无效,勿重复试错。「加量」的有效旋钮是
    #: directed_refresh_per_round 与授权窗宽度(gate_min_round 前移),
    #: 非 game_cap(见 ADR-0413 Considered Options)。
    directed_refresh_game_cap: int = 6

    # ===== W251/ADR-0408 假设 A:r3/r4 投资节奏前置(评分偏置)=====
    #: 总开关:False=回 W248 后行为(A/B 基线臂;默认关=现行为零漂移,
    #: ADR-0305 先例)。True 时 P1 r∈[early_pace_min_round,
    #: early_pace_max_round](缺省 3-4,W248 报告 §四:高损耗局的分化
    #: 在 r3-r4 已发生,当前策略按息纪律延后投资、r3/r4 常带浅板上阵)
    #: 的**战力买标签**(=crisis_buy_tags 同集,战力买语义复用不另造
    #: 标签集)候选,val ≤ early_pace_val_max 的 0/小分买入顶成 +
    #: early_pace_bias——与 forming_bias(ADR-0332)同构的「成型期权
    #: 显影」前移版,把破息战力投资的 EV 授权阈值在 r3-r4 放宽一档
    #: (W248 假设 A:败场数是出口 hp 最强负相关 −0.635,投资前移→
    #: 更早把金转化为战力→压低 r7/boss 高损耗轮败场数)。
    #: **防双计**(W232/W238 三件套纪律):本项只顶非正分买进约束链,
    #: 息账仍由 interest_rule EV 账单一裁决(V 随偏置进入 = 授权放宽
    #: 是本修法的本体语义,非第二份授权);地板族/copies_cap/bench
    #: 容量照常辖;forming_bias 不重叠(r3-r4 在其 r≥5 窗外)。
    #: 默认关论证见 ADR-0408(A/B outcome 裁决)。
    early_pace_enabled: bool = False
    #: 窗下界(P1 备战轮;r3 是首个战斗节点前的最后一轮备战)
    early_pace_min_round: int = 3
    #: 窗上界(W248 §四干预口径:「r3-r4 备战期放宽破息授权一档」;
    #: r5 起 supply 回补,由既有息纪律接管)
    early_pace_max_round: int = 4
    #: 偏置单位值(顶 0/小分买入;量级=forming_bias 同阶,只改变约束链
    #: 是否可达,排序面让位天然正分目标件)
    early_pace_bias: float = 5.0
    #: 顶分上沿(原分 > 此值不加偏置——防「已正分买入被二次加分」双计,
    #: forming_bias_val_max 同款边界)
    early_pace_val_max: float = 0.5

    # ===== W332b 未成型期姿态:泄息通道(release)与换线判据参数 =====
    #: 设计=唯一规格:`.debug/temp/currency_war/w328_unformed_posture/DESIGN.md`
    #: (对抗修订二轮已吸收)。**符号不稳参数一律默认值+标定接口,不拍死**:
    #: k(hp)/Δhp/boss 税由 sim 批网格标定后锁值(DESIGN §⑥ EV 参数门)。
    #: 总开关:False=回 W332b 前行为(FLIP 谓词不评估,纯增量设计的 A/B 基线臂;
    #: DESIGN §②「防间隙:FLIP 为假时维持原姿态,旧行为是退化输出」)。
    release_enabled: bool = True
    #: 血量边际价值 k(hp) 报警带值(DESIGN §①:非标定设计参数;动机=语料 66 场
    #: P1 boss 战战后 hp≤3 占 43.9% → 末窗边际 hp 是生死价,线性折价 0.5 金/hp
    #: 系统性低估)。k=3 臂的符号结论对 k_hp_calibration_grid 不稳,只作敏感度臂。
    k_alert: float = 3.0
    #: k(hp) 线性区值(hp≥40 且末窗投影未命中)
    k_linear: float = 1.0
    #: k(hp) sim 标定网格(标定接口,非运行时值;DESIGN §①标定计划)
    k_hp_calibration_grid: tuple[float, ...] = (1.0, 2.0, 3.0, 5.0)
    #: FLIP 持续兑现臂的低血上沿(非末窗 hp<此值命中;与 discipline
    #: BLOOD_MARGIN_LOW_HP=40 同值口径,registry 注入化)
    blood_margin_low_hp: int = 40
    #: boss 税 p75 分位锚(DESIGN §②:语料 66 场 P1 boss 战掉血 median=32/
    #: p75=34/p90=36/max=58/mean=26.7)。末窗投影判据 = hp − 此值 < emergency_hp。
    #: max=58 肥尾是遗留风险(贴边带当前语料 0 帧);sim 标定时 boss 税以
    #: 分位锚组进 registry,不做单点(boss_tax_anchor_group)。
    boss_tax_p75: float = 34.0
    #: boss 税分位锚组 {P50, P75, P90}(sim 标定接口,非运行时值)
    boss_tax_anchor_group: tuple[float, float, float] = (32.0, 34.0, 36.0)
    #: 边际战力代理 Δhp·普通战(轮内去均值,hp/场;语料 166 局 5→6 人实测;
    #: 弱信号非单调,只作敏感度臂——DESIGN §①诚实判读)
    delta_hp_normal: float = 1.96
    #: 边际战力代理 Δhp·boss 层(裸差分,hp/场;P1 boss 全在 r9 轮次混杂极小,
    #: 末窗旗杆帧的正确语料层——DESIGN §①)
    delta_hp_boss: float = 4.30
    #: 换线判据总开关(False=回 W332b 前行为;E_rounds 主判据 A/B 通道)
    line_switch_enabled: bool = True
    #: 切换阈值 θ 轮(滞回余量;只承载去偏后的双向估计噪声,不兼职补偏差
    #: ——DESIGN §③修订 2)
    line_switch_theta: float = 1.0
    #: p̄ 乐观偏差修正 δ(NPC 消耗/争夺上界估计;双线 E_rounds 同乘 (1+δ)
    #: 先修偏再比较——DESIGN §③修订 1)
    line_switch_debias_delta: float = 0.15
    #: 当前线最短驻留轮 D_min(压振荡频率硬上限至 1/(2·D_min);DESIGN §③修订 3)
    line_switch_min_dwell: int = 2
    #: release 帧活栈消费门(判据单一源=posture_release.spend_gate_active
    #: 读 session.v3_release;消费面=scoring 息 EV 中性 + candidates 凑息向
    #: 卖候选抑制)。False=回消费门未接线行为(release 生产链只辖义务预算
    #: /arbiter 放行,评分与卖候选不感知 release)——A/B 通道,先例同
    #: evolve_engine_guard_enabled;开臂依据=W355 开臂 A/B(凑档卖 25→4 笔 −84%、
    #: 回退守卫全净、触发面一致)+C2 前置(W367 C_dec 门辖)已修;对照臂经
    #: registry 注入 False 保留。
    release_spend_gate_enabled: bool = True

    # ===== P2 生存批:濒死带支出收窄(C3)与换线存活轮数门(C4) =====
    #: 设计=唯一规格:`.debug/temp/currency_war/w373_c3c4_redesign/REDESIGN.md`
    #: §2(C3 Δp_board 代理)/§3(C4 剩余节点序列逐节点投影)/§4(双源标定)。
    #: 标定=同目录 w375_calibrate_dual_source.py(死亡真源=runs.jsonl,
    #: hp≤1 不删失、hp_after=0 死亡行按 hp_before 全额入桶、不按置信度
    #: 过滤——旧删失口径「置信<1 剔除」系统性剔死亡局帧=反保守,已废;
    #: 产物=w375_dual_source_calib.json,双源互校:帧级合并均值 10.79 ∈
    #: run 级聚类 bootstrap CI [6.7,10.97])。
    #: C3 总开关:False=现行为逐位一致(零漂移锚,A/B 基线臂)。True 时
    #: 应急深带(hp≤emergency_hp,触发线不动)内「再输一场即死」帧
    #: (hp≤下一战期望损血,粗档查表)做**支出收窄**:删除下一战部署
    #: 增量为零(Δp_board=0)的支出——bench 满且无空位的纯 hoard 买/
    #: 升完仍无件可上的 LevelUp/店无可上件的盲刷;可上件买/可引爆
    #: bench 的 LevelUp/定向刷新放行(数值比较交给既有 EV 层,滤网只
    #: 做可证明零期望的符号判定,REDESIGN §2.3 推导链);卖(变现)/
    #: 部署非支出不辖。判据强制 state.hp_readable 守卫(置信 0 帧 hp
    #: 为沿用值,假帧不评估);辖域 plane≥2(P2 生存批);与 release
    #: FLIP 辖区(hp>emergency_hp)零交集——濒死帧恒不在 release 辖区,
    #: 结构互斥。
    dying_band_account_enabled: bool = False
    #: P2 节点损血单一表(C3 濒死带「下一战期望损血」粗档与 C4 存活轮数
    #: 投影共用;节点型→期望损血,正数)。单一源不变量:两消费点
    #: (filters._next_battle_loss 桶位查表 / cw_line_switch.rounds_alive
    #: 逐节点投影)读同一份表,消费语义各自投影、数值源唯一——重标定
    #: 覆写只改此处。标定=同目录 w375_calibrate_dual_source.py(死亡真源
    #: =runs.jsonl,hp≤1 不删失、hp_after=0 死亡行按 hp_before 全额入桶、
    #: 不按置信度过滤——旧删失口径「置信<1 剔除」系统性剔死亡局帧=反
    #: 保守,已废;产物=w375_dual_source_calib.json,双源互校:帧级合并
    #: 均值 10.79 ∈ run 级聚类 bootstrap CI [6.7,10.97])。
    #: 默认值=旧删失口径三档(结构性低估挂账;暂抄现行=零漂移);重标定
    #: 无条件期望(normal 10.16/encounter 12.00/boss 15.50,条件败面
    #: 12.77/13.33/15.50,CI 见 w375_dual_source_calib.json)待消费口径
    #: 定稿后覆写。node_type 缺读兜底=normal(战斗节点频率最高档,2/5 槽;
    #: 触发宽度居中——三档中 encounter 16.67 最小、boss 26.71 最大,normal
    #: 兜底既非最紧也非最松;濒死带缺读帧向「多拦」方向偏差约
    #: (20.05−16.67)/16.67 ≈ +20% 触发面,属收窄方向的温和假阳性,容忍
    #: 并在此声明,不做双档兜底)。reward 零损档承接奖励+补给零损日历轮
    #: (C3 侧查表命中 0.0、C4 投影零损照走,与缺读 .get 0.0 兜底同值)。
    p2_node_loss_table: dict[str, float] = field(default_factory=lambda: {
        'normal': 20.05, 'encounter': 16.67, 'boss': 26.71, 'reward': 0.0})
    #: C3 R2 定向刷新存在性判据的「高费强件」费用下界(买侧不辖名单,
    #: 只辖刷新存在性名集;来源=对抗审计 A1-β 反例画像「4 费通用强件是
    #: 最高 Δp/g 选项」(报告=`.debug/temp/currency_war/w363_c3c4_attack/
    #: ATTACK.md`)+ sim 分 rung 胜占比 0.34→0.65 单调
    #: (W346 报告 §3.2 实证底座)=高费高星战力优势)。
    dying_band_high_cost_floor: int = 4
    #: C4 存活轮数门总开关:False=现行为逐位一致(零漂移锚;与 drought
    #: bail 的或-并存结构不变,本门是 E_rounds 主判据的第三道串联门,
    #: 不造第二换线机制)。True 时 E_rounds 换线裁决通过后加验
    #: rounds_alive(剩余节点序列逐节点投影)≥ E_rounds(新线)×(1+δ)
    #: +兑现余量——存活轮数不足=新线到不了兑现点,换线期望 0<驻留
    #: 旧线(「转进死线」堵门)。辖域 plane≥2(损血表为 P2 标定);
    #: drought bail 旁路不辖(或-并存结构不变,弃线不是转进)。
    line_switch_survival_gate_enabled: bool = False
    #: C4 兑现余量(轮;新线成型后仍需一轮兑现战斗,取 1=设计内保守下界)。
    #: 兼承载投影的近似残差(逐节点确定性投影 vs 真分布 E[min(t:ΣL>hp)]
    #: 的 Jensen 乐观差,REDESIGN §3.5 偏差表首行)。
    line_switch_survival_margin: float = 1.0
    #: C4 两态口径 p_win 表(成型度 rung(0-2 钳制)→P2 战斗胜率;缺省
    #: 空 dict(或 rung 缺档)=消费侧缺省 p_win=0=每战全损,loss=表值
    #: 条件常数,两态退化为 M1a)。占位,值=sim 分 rung 胜占比(W346 报告
    #: §3.2;或 P2 损血重校批的 P2 胜率表)注入后生效。
    p_win_p2_by_rung: dict[int, float] = field(default_factory=dict)
    #: C4 遭遇节点回血期望(hp;投影对每 encounter 节点加回)。默认 0=
    #: 0 下界(回血量未标定,禁拍死值;P2 生存实探局 hp=1 后有回血后继
    #: 观测实证(W350 REPORT §1),取 0=低估存活=门偏紧的保守方向);
    #: 值=该报告后继观测回血量标定后注入。
    encounter_heal_est: float = 0.0
    #: C4 boss 档不确定性附加费(轮;投影路径含 boss 节点时 need 加此
    #: 半宽——借档的不确定性由被比较量显式承担,REDESIGN §4.3)。值=
    #: 标定产出 |28.24−26.71|(P1 two_state 拟合与借档常数的源距,
    #: w375_dual_source_calib.json boss_bucket_injection),非魔数。
    line_switch_boss_ci_halfwidth: float = 1.53

    # ===== C1 溢余必花定向优先级(P1 末窗投影安全带;FLIP 正交补集)=====
    #: 设计=唯一规格:`.debug/temp/currency_war/w382_c1_design/DESIGN.md`
    #: §2(期望账)/§3(路线 B 辖域裁决)。辖域裁决=与 FLIP 末窗投影臂
    #: (ADR-0426)同锚两分支的**正交补集**:末窗帧按投影残差
    #: d = hp − boss_tax_p75 一刀切,d < emergency_hp 归 FLIP 泄息义务
    #: (既有,不动),d ≥ emergency_hp 归本通道评估——辖域互斥由谓词
    #: 构造保证,不靠开关序。
    #: 总开关:False=现行为逐位一致(零漂移锚,A/B 基线臂)。True 时
    #: P1 末窗(discipline.boss_window_active 统一口径)∧ 投影安全带
    #: (d ≥ emergency_hp)∧ 溢余段(g > interest_floor,[17])∧ hp
    #: 可信位(hp_readable or hp_trusted,ADR-0428 同款守卫)帧内,
    #: 支出候选按 boss 战胜率增量做定向收窄(filters 层2 符号判定,判据
    #: 复用濒死带同款 Δp_board 逐动作谓词):可部署买/3合1 即时合成买、
    #: 升完立刻多上件的 LevelUp、店有可买+上名集件的定向刷新放行;
    #: 零增量支出(纯 hoard 买/盲刷/升完无件可上)删。数学账(规格 §2):
    #: 溢余段花金零息损(P11 参数无关确定性结论,成本恒 0),收益=
    #: Δp × E[损血|boss 败] × hp_to_gold 金当量——Δp≤0 的支出确定性
    #: 零收益;「溢余必花+定向 boss 战力」的优先级语义=零贡献支出让位
    #: 有增量支出,贡献间的相对排序仍归 EV 评分层单一裁决(禁双判定源,
    #: 评分末窗权重不在本通道重复)。判据单一源纪律:末窗锚=
    #: ``posture_release.boss_first_buy_phase``(唯一 latch 所有者经
    #: discipline 统一口径),filters 不重算末窗谓词;阈值全部复用
    #: registry 单一源(boss_tax_p75/emergency_hp/interest_floor),
    #: 不立第二常量(常量即判定源,复刻即双源)。
    #: **破息分支存档(本批不实现,待 E[R̄] 标定后评估)**:息线以下
    #: (g≤50)跨档破息花 X 的过账判据 = Δp(X) × 13.35 > 息损(X, g,
    #: R̄),其中 13.35 = E[损血|boss 败](26.7)× hp_to_gold(0.5)的
    #: 金当量系数,息损 = Δfloor(g/10) × R̄(R̄=花后剩余生息轮数,P2
    #: 死亡率压制下保守区间 [4,10],精确期望未标定)。线性近似
    #: Δp(X)=k·X 时门槛 k > R̄/(10×13.35) ≈ 0.03~0.075/金;现有最乐观
    #: 传导链 proxy(P17 +8 hp 链)隐含 k ≤ 0.012/金,比门槛低 2.5~6 倍
    #: → 破息分支当前账面不成立,默认不触发;E[R̄] 从既有语料 runs.jsonl
    #: 离线标定到位后按上式重裁,公式与代入验证见规格 §2.3。
    c1_directed_spend_enabled: bool = False


    # ===== 层4:预算仲裁(约束清单——一处定义,全部候选受辖)=====
    #: 执行约束名序(仲裁器按序施加;filters/arbiter 按名映射实现)
    constraints: tuple[str, ...] = (
        'gold_floor',          # 金≥地板(地板按覆盖态分派)
        'interest_rule',       # [11][17][28] 息档保持/满息结余
        'bench_capacity',      # bench 9 槽(含本轮已采纳买)
        'copies_cap',          # 同名星级加权 ≤3 份
        'same_round_mutex',    # 同轮已买禁卖/已卖禁买(r408 族)
        'boss_levelup_ban',    # 升级 EV 总账门(名字历史遗留;W255/ADR-0410
                               # 起 boss 禁令臂已删,[32] 节点无关)
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
    #: boss 轮判定(node_type='boss';P1 r9 兜底同辖)。W255/ADR-0410:
    #: 消费面只剩 boss 窗地板/覆盖态语境(b 类保留),升级特殊禁令已删。
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
