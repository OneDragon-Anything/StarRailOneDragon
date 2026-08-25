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
    #: 过滤链层级序:应急 > 追赶 > 模式(redesign §5.4 唯一真值序)
    filter_chain_order: tuple[str, ...] = ('emergency', 'catchup', 'mode')
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
    catchup_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'pair', 'copy', 'levelup',
        'off_target', 'free_bench', 'deploy',
    })
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
    catchup_forbidden_tags: frozenset[str] = frozenset({
        'for_gold', 'refresh',
    })
    #: 应急 HP 档(触发层2 应急过滤;旧 line_strategy._EMERGENCY_HP
    #: 镜像,ADR-0336 后独立)
    emergency_hp: int = 25
    #: ADR-0302 危机囤金金线(合流批 ADR-0303 上移):应急态金 ≥ 此值
    #: 时进危机囤金态(战力买偏置+搜牌解锁)。依据:批㉝ F3 指纹阈值
    #: 40(hp≤25 且金≥40 只升不买,金囤 85+ 板濒死零动作)
    crisis_hoard_gold: int = 40
    #: 追赶等级门(P1 早期人口低于基线是常态;旧 line_strategy
    #: ._CATCHUP_MIN_LEVEL 镜像,ADR-0336 后独立)
    catchup_min_level: int = 6
    #: 位面人口基线(r191 中位;旧 line_strategy._POP_BASELINE 镜像,
    #: ADR-0336 后独立)
    pop_baseline: dict[int, int] = field(
        default_factory=lambda: {1: 5, 2: 7, 3: 9})

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
    #: 兜底局(意向未锁)form_ok 降级门:form_score ≥ 此值判「战力 OK」
    #: (W113 §3.1;sim 校准域)。初值量纲推算:form_score 满分=2 过渡
    #: 体系(rung2,H3 胜率 77.8%),1 体系=0.5(rung1,胜率 41.6%)——
    #: 「战力 OK」保守取 1 体系档 = 0.5(与 formed_stop_min_round=7 的
    #: 「成型下界」保守取向同族;门值标定留步②b sim 网格)
    phase_form_score_gate: float = 0.5
    #: 兜底局 form_ok 的轮数下限(W119/ADR-0347 校准判据,W113 §8-11):
    #: W118 实测 A 臂兜底局 form_score≥0.5 在 r2-r3 即转真(首真直方图
    #: r2=10/r3=4)——1 过渡体系≠战力 OK,抱弱板进 HOARD 攒息=守弱板
    #: 掉血。加轮数下限判据(与 gate 合取;取 5:灭 r2-r3 误转真,r5 双
    #: 体系帧保留;标定留 ②b,独立于 Q1 四档对照)
    phase_fallback_min_round: int = 5
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
    #: 刷新常量 EV(板面查表不可预知新店 → 表外常量;**已标定**,
    #: ADR-0293:2.5=早刷净收益(成本 2 + 0.5 方向期权);恒刷会
    #: 抽干金流,配 refresh_max_round/refresh_min_gold 双门)
    refresh_ev: float = 2.5
    #: 刷新 EV 生效轮界(r≤ 此值才按 refresh_ev 计正值;超出恒负分
    #: 不刷)。标定依据(ADR-0293):v1 r258 早期方向刷新 + 中期找件
    #: (1.76 次/局);恒刷(=9)抽干金流挤死升级,过窄(=3)中期
    #: 找件断供,双窗 A/B 定 6
    refresh_max_round: int = 6
    #: 刷新金保底(金< 此值不刷)。标定依据:无保底时刷后 re-decide
    #: 链把早期金抽干至 <10,中期永远够不到满息平台 → [12] 息引擎
    #: 门锁死晚期升级通道(0.45 次 vs v1 6.25 次;标定批诊断,ADR-0293)
    refresh_min_gold: int = 20
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
    #: 评分侧联动折扣(ADR-0297 刷新×追级并存,采纳方案):金<
    #: refresh_starve_gold 时 refresh_ev 乘此系数——排序自然让位给
    #: 追级/买入。**已按 ADR-0297 双窗+终验标定:0.6/40**(金<40 时
    #: EV=1.5-2=-0.5 恒负分不刷;≥40 全额)是全部并存变体中唯一
    #: 双窗一致臂(原窗 -5.23/验证窗 -4.80;终验 n=100 -5.76);
    #: lvl 2.07→6.27(通道病治愈,≈v1 6.83)refr 10.3→2.91。
    #: 约束侧(方案 a:refresh_game_cap/levelup_reserve_gold)为本批
    #: 诊断否决的通道(双窗不稳),保留为注册 A/B 通道默认关闭
    refresh_starve_discount: float = 0.6
    #: 评分侧联动的饥饿金阈值(金< 此值触发折扣)
    refresh_starve_gold: int = 40
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
    # ===== 成型找件刷新(ADR-0301 strike2,域 b) =====
    #: 成型找件刷新 EV:未成型(引擎数<target)且当前店无引擎卡时,
    #: 刷新=定向找件。**双窗 A/B 否决(30+30 配对 -4.13/-4.70,
    #: hp_ge_60 双降)**:找件命中率低于常量 EV 假设,且高分刷新
    #: 挤掉同轮买入;通道保留注册默认关闭(A/B 可开,同
    #: refresh_game_cap 模式)
    form_refresh_ev: float = 0.0
    #: 成型找件刷新生效轮界(r≤ 此值;r7 遭遇前是找件窗,
    #: 常规 refresh_max_round=6 不辖本通道)
    form_refresh_max_round: int = 7
    #: 成型找件刷新金保底(找件可破常态息档但不破此底——
    #: 金流抽干防护,高于常规 refresh_min_gold 的 20)
    form_refresh_min_gold: int = 30
    #: 「已成型」判定阈值(引擎数 ≥ 此值=不再找件刷)
    form_refresh_engines_target: int = 2

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
        'refresh_budget',      # ADR-0297 每局刷新预算+追级保留金
    )
    #: 地板表(金≥地板;覆盖态分派——审计表 gold 行的消费值)
    interest_floor: int = 50      # [17] 满息地板(常态/追赶)
    war_floor: int = 30           # 战力模式地板(计划内补强非 panic)
    rebirth_floor: int = 20       # [18] 应急保留重生基数
    boss_floor: int = 10          # r278 boss 破息地板
    #: (levelup_interest_engine_gate 已随 W119 删除:[12] 门收编 EV 总账
    #:  ——ev.levelup_ev_authorized 单一裁决,ADR-0347;A1/A2 镜像清)
    #: ADR-0297 刷新×追级并存·约束侧(方案 a,诊断否决默认关闭):
    #: 每局刷新预算上限(v1 量级 4-6);0=不限。诊断证据:cap+reserve
    #: 双窗不稳(原窗 -3.27/验证窗 -11.70),评分侧联动更稳
    refresh_game_cap: int = 0
    #: ADR-0297 追级保留金(约束侧,同上默认关闭):等级未满时,
    #: 刷新后金低于此值即让位(不刷只攒);0=关闭
    levelup_reserve_gold: int = 0
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
            ('gold', 'boss'): ('gold_floor', 'interest_rule'),
            ('gold', 'emergency'): ('gold_floor',),
            ('gold', 'catchup'): ('gold_floor', 'interest_rule'),
            ('bench', 'boss'): ('bench_capacity',),
            ('bench', 'emergency'): ('bench_capacity',),
            ('bench', 'catchup'): ('bench_capacity',),
            ('slot', 'boss'): ('boss_levelup_ban',),
            ('slot', 'emergency'): ('bench_capacity',),
            ('slot', 'catchup'): ('deploy_cap',),
            ('round_mutex', 'boss'): ('same_round_mutex',),
            ('round_mutex', 'emergency'): ('same_round_mutex',),
            ('round_mutex', 'catchup'): ('same_round_mutex',),
        })
    #: 审计表两维的显式枚举(新增动作类型/资源维时审计表强制过检)
    audit_resource_dims: tuple[str, ...] = ('gold', 'bench', 'slot', 'round_mutex')
    audit_round_state_dims: tuple[str, ...] = ('boss', 'emergency', 'catchup')


#: 默认注册表(ADR-0293 标定后;A/B 时构造改动副本注入
#: DecisionV2Strategy)
DEFAULT_REGISTRY = DecisionV2Registry()
