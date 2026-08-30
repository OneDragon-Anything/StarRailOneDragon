"""决策框架 v2 注册表(ADR-0290 对抗修订③:剪枝显式化/全注册表化)。

归属:core/kernel 桶(分包期 0b 自 decision_v2/registry.py 整文件下沉)——
本文件零 sr_od 依赖、``DEFAULT_REGISTRY`` 纯常量实例、全仓无动态注册,
kernel 与 decision_v2 必须共享**同一** registry 实例(A/B 注入契约:同一
调用链全部接缝传同一实例),拆两段会造双实例破契约,故整文件移动。

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

⚠️ 收入口径修正挂账(ADR-0439,sim 侧已落码):sim 败轮金 + 奖励轮
成对修正使 P1 出口金约 +6.6 金/局(无反馈静态重放量化)——凡以 sim
经济轨迹为输入的历史门结论(典型:粗模型 vs Δ池的 P2 进场率差恰在
门界、零余量的门 1a)在新口径下须 regate(修正口径重跑基线臂)后才能
引用;本批只落码不改判据,regate 与基线重锚一并挂账待执行。
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
    #: copy_swap 守卫×目标件豁免开关(ADR-0303 落地;ADR-0304 曾裁决
    #: 默认关=回退 0302 守卫直通——当时三窗小负且无主病灶前提;
    #: **ADR-0438 开臂翻默认 True**:`w436_merge_exempt_ab/` A/B 在 ①豁免扩同批前提下,
    #: 本开关相对单开 ① 臂第三张 offer 买率 +9.15pp(CI [2.31,15.76]
    #: 显著)、形态达标率 +3.0pp(方向正不显著)、守卫全净(真破息/
    #: hp0/bench 溢出/出口金)——`w431_generation_starve/` 定位的 r410 守卫 lv7-8 无臂接
    #: 15 笔窄段(目标名精确命中臂①条件)在生成通道打通后兑现。
    #: False=回退守卫直通(代码留作回退通道)。
    copy_swap_target_exempt: bool = True
    #: 非正分门 merge 完成豁免开关(第三张副本买候选 3合1 完成素材语义,
    #: 决策 why=ADR-0438):True=arbiter 非正分门对 merge=True 的买候选
    #: 放行进入约束链(豁免≠必买:金地板/copies_cap/bench 容量/息账
    #: 照常辖)。依据:第三张副本买入即合成 2★,其价值落在星级阶梯
    #: (H3:e0/e1/e2 胜率 13.9/41.6/77.8%)而非板面差分——评分维
    #(merge_progress 只计第 2 份,ADR-0340 边界)对它构造性零增量,
    #: 非正分拒是评分零维测量伪影非 EV 判断;与既有 'copy' 标签 C 豁免
    #: (`w242_star_directed/`/ADR-0405 C 项)同为「完成素材放行」语义对称,无条件于
    #: 末窗 gap(完成价值全程存在,不作定向授权)。仅辖 BuyCard
    #(synthesize 候选虽 merge=True 但不辖)。
    #: 开臂裁决(ADR-0438,`w436_merge_exempt_ab/` A/B 兑现,CI 口径同 `w422_form_ab/`/`w429_dup_ab/`):第三张
    #: offer 买率 off 53.93%→ex 83.52%(+29.6pp CI [21.1,38.9] 显著)/
    #: 形态达标率 31.00%→44.33%(+13.33pp CI [5.81,21.08] 显著)/
    #: core2≥1 进场率 +20.67pp 显著;守卫全净(真破息 +0.33pp 不显著/
    #: hp0 −2.0pp 不显著/bench 满帧占比不升/出口金不降);差一张桶
    #: −6.86pp 方向对不显著(桶主体由 ②生成通道与 EV 约束链共同消化)。
    #: **默认开**;False=回退非正分拒(代码留作回退通道)。
    merge_completion_exempt: bool = True
    #: [31] 凑档降级的成本带上限(1-2 费=P1 过渡带)
    bond_fallback_max_cost: int = 2
    #: [31] 降级触发回合门(P3 边界:r1-r2 无战斗买件纯付息损)
    bond_fallback_min_round: int = 3
    #: [32] carry_gate 腾位买的轮界(r≤7;r8-r9 终局段买入不影响结算)
    carry_gate_max_round: int = 7

    # ===== 层4 补偿趟(迁移审计 w52(git 历史) 回连机制;ADR-0326)=====
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

    # ===== S5 统一卖件弱序(迁移审计 w52(git 历史)/ADR-0327)=====
    #: [22]③ 再遇窗口表(费级→再遇期望轮数)。实测锚两个:1费 11
    #: (7-15 中值)/ 5费 120(60-180 中值,7-8 级窗口);2-4费为锚点
    #: 间的**拟合经验值**——5费锚跨度 60-180 使中段既无实测也无可信
    #: 参数化形式(非线性),标定接口=sim 校准域(ADR-0327)。消费方
    #: sell_priority_key。
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
    #: 过滤链层级序:应急 > 模式(追赶态已随 `w126_b_arm/`/ADR-0349 退场——人口落后
    #: 由通道 2 人口位升级+通道 4 概率等级窗+EV 总账涌现,兜底局由 form_score
    #: 承接「人口别落后」观察;位面绝对基线 {5,7,9} 是阵容无关的粗糙代理)
    filter_chain_order: tuple[str, ...] = ('emergency', 'mode')
    #: 各层放行标签集(候选标签仅作过滤域标记,不携带优先级——ADR-0290)
    #: ADR-0302 应急集内容修正(合流批 ADR-0303 并入):补 for_gold
    #: (卖弱件)+levelup(升级)——应急态语义=战力买+卖弱件+升级,
    #: 旧窄集把两通道在应急态整体滤死(迁移审计批(可解释性遥测) F4);pair/copy/
    #: bond_fallback/synthesize 在应急态仍滤出(ADR-0300 应急集保持窄)
    emergency_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'carry_gate', 'off_target',
        'free_bench', 'deploy', 'for_gold', 'levelup',
    })
    #: 追赶窗口约束与追赶标签集已随 `w126_b_arm/`/ADR-0349 删除(用户 2026-08-25
    #: 裁决 F6/Q4:人口落后=阵容没上满的表现,由通道 2/4+EV 涌现承接)
    economy_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'pair', 'copy', 'copy_press',
        'carry_gate',
        'bond_fallback', 'off_target', 'for_gold', 'free_bench',
        'levelup', 'refresh', 'deploy',
    })
    #: war 标签集(`w126_b_arm/`/ADR-0349:refresh 进 war 集——「war 模式滤 refresh」
    #: 废除,D 是一等花钱通道([17]「该D牌D牌」不因 war 覆盖态消失;
    #: 授权仍由 V_D 批口径评分+interest_rule EV 门辖,标签集只管在场)
    war_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'pair', 'copy', 'copy_press',
        'bond_fallback',
        'carry_gate', 'off_target', 'for_gold', 'free_bench',
        'levelup', 'deploy', 'refresh',
    })
    #: 应急 HP 档(触发层2 应急过滤)。持久依据=双失缓冲带:应急线须
    #: 高于「两次条件败局伤害」吸收上界 2×L_c(rung2)≈21.2(math_proofs
    #: P15:L_c=11.32−0.37·rung,registry.vd_p1_loss_* 单一源),且低于
    #: 「一次败局后仍不破重生基数」上界 rebirth_floor+L_c≈30.6
    #: (rebirth_floor=20,口述 [18] 应急保留重生基数);带 (21.2,30.6)
    #: 内取 5 网格点 25,与报警降档线 40(discipline.BLOOD_MARGIN_LOW_HP)
    #: 保持处置梯度:40=报警加速、25=应急覆盖态清仓。
    emergency_hp: int = 25
    #: ADR-0302 危机囤金金线(合流批 ADR-0303 上移):应急态金 ≥ 此值
    #: 时进危机囤金态(战力买偏置+搜牌解锁)。依据:迁移审计批(可解释性遥测) F3 指纹阈值
    #: 40(hp≤25 且金≥40 只升不买,金囤 85+ 板濒死零动作)
    crisis_hoard_gold: int = 40
    #: (catchup_min_level/pop_baseline 已随 `w126_b_arm/`/ADR-0349 删除:追赶态退场,
    #: 通道 2 人口位([33])+通道 4 概率等级窗([3])+EV 总账涌现承接)

    # ===== 血预算停手·停升级线(设计件 12 §3.1/§2.3-P1-b;ADR-0448)=====
    #: 总开关:True=停升级门恒接线(P21 数学定谳:hp ≤ d·L_c 域内升级
    #: EV=−C−I 严格为负,与 β 标定无关——不是「待验证」的悬置开关);
    #: False=A/B 对照臂/回退锚(sim 配对经 registry 注入实现,与
    #: vd_p2_enabled 同型:布尔两态=「血预算约束在场/退场」)。
    blood_budget_stop_enabled: bool = True
    #: P21 判据「存活到账 h > d·L_c」的到账延迟 d(战斗场次)。d=1=
    #: 升级→人口生效→下一场战斗的最短诚实延迟(P21 证 d=0 亦负,
    #: 取 1 更保守;设计件 12 §3.1 推导链步 3)。
    blood_budget_stop_d: int = 1
    #: P1 停追级线的 L_c 取样成型档:L_c(rung)=vd_p1_loss_intercept+
    #: vd_p1_loss_slope_rung×rung,rung=2 为代表帧(≈10.58)→
    #: 线=ceil(d×L_c)=11(设计件 12 §6 参数表 P1_LEVELUP_STOP_L_C
    #: 的取样坐标;拟合单一源=vd_p1_loss_*,不另立数值)。
    p1_levelup_stop_rung: int = 2

    # ===== 血预算停手·第二波(设计件 12 §2.3-P1-a/P1-c、§3.2;ADR-0451)=====
    #: P1 末窗期望预算线(设计件 12 §6 P1_EXIT_BLOOD_TARGET,推导 §2.2:
    #: 要求期望伤害 ≤ 进场血反解 w*=1−h/88,h=60 → w*=0.32 可达)。
    #: 语义=**期望预算线**——充分方向、非存活保证(`w524_audit_60line/` 对抗审计实测
    #: h≥60 存活率仅 0.60、分带平滑无崖,「分界」表述已废);触发动作=
    #: 末窗授权支出结构降格,不是保血承诺。
    p1_exit_blood_target: int = 60
    #: P1-a 末窗支出降格总开关(True=承接门定向投资授权在血预算不足局
    #: 降格为减损保血;依据=`w516_p2_conversion/` 排除证据 HG5/IF30——β 弱通道下战力
    #: 投资换不回 15-25 血/败,方向性结论不依赖 β 量级,非「待验证」
    #: 悬置开关;False=A/B 对照臂/回退锚,与 blood_budget_stop_enabled
    #: 同型的两态注入面)。
    p1_exit_downgrade_enabled: bool = True
    #: 搜索型刷新停付总开关(P1-c 锁线前移+停刷新结构语义,设计件 12
    #: §2.3-P1-c/§3.2;依据=[31]④ 刷新金合法用途硬约束归位——为找件
    #: 而付刷新费的搜索型支出在血预算不足域期望符号为负;False=A/B
    #: 对照臂。**数值停刷新线不在此**:收益项=Δp×β 不可算,挂 β 开臂
    #: 判据(设计件 12 §4.1),标定前只落结构不落数值)。
    blood_budget_refresh_stop_enabled: bool = True

    # ===== 概率校准的刷新预算(提案面=.debug/temp/currency_war/
    # ===== w645_proposal_v2/SPECS.md 提案 B-v2;决策 why=ADR-0475)=====
    #: 塌缩带归零线 ω:refresh_prob(当前级,目标费)/refresh_prob(峰值级,
    #: 目标费) < ω → 该帧刷新预算归零(refresh_ev_budget 合法 0 帧第三类)。
    #: 比值由 cw_shop_odds.REFRESH_PROB 表逐帧导出(概率单一址,与分配器
    #: Π_refresh 估计器同源互指,禁第二概率口径)。ω 是标定字段:初值 0.1
    #: 占位=「当前级单刷命中率不足峰值级十分之一」;标定网格 {0.05,0.1,0.2},
    #: 多臂同过判前锁死取最小者(最保守归零线,出处=SPECS B-v2 §3;
    #: 首批双臂验证记录=ADR-0475)。归零的账=塌缩带留金弱占优纯烧
    #(留金保留全部未来期权,烧金灭失),不需要息成本参与。
    omega_collapse_ratio: float = 0.1
    #: 有望帧帽真分位 q:帽 = ⌈−ln(1−q)·E_find⌉,E_find =
    #: cw_shop_odds.expected_refreshes_for_card(level, 目标费,
    #: target_star=2, owned=j)(有限池精确期望,单一址同上)。q 为真分位
    #: 语义,−ln(1−q) 是其闭式精确乘数(q=0.8→1.61,q=0.9→2.30;推导:
    #: 每刷命中率近恒定时 P(T≤kE)≈1−e^{−k}),非新常数。网格 {0.8,0.9},
    #: 初值 0.8=保守档。j=0(零持有)时全部 (level,费档) 组合帽值 ≥39 > 6
    #: 刷帽=结构性不绑定;帽的实际绑定面=E_find=0 帧(owned≥k 目标已
    #: 集齐,或该级出不了该费档 p=0)——帽归零=搜索价值归零的如实账
    #(第 4 份副本不可用/纯烧),sim 实测绑定集中于此(ADR-0475)。
    refresh_find_quantile: float = 0.8

    # ===== 血预算停手·终止分支(P1「止损转支出」;设计 W659 v2 §0/§2;ADR-0469)=====
    #: 总开关:True=数学定谳恒接线口径(金零值引理+EV 对比式:守钱世界
    #: 存活概率上界 S0≤ε 时一切守钱资产期望被压没,释放当轮转化路径
    #: 严格占优——不是「待验证」的悬置开关;False=A/B 对照臂/回退锚,
    #: 与 blood_budget_stop_enabled 同型两态注入面)。
    terminal_release_enabled: bool = True
    #: 守钱世界存活概率上界释放阈 ε(S0=Π 单发穿透场条件胜率 ≤ ε →
    #: 终止分支触发)。默认 0.03 = 设计 W659 v2 §2.2 EV 对比式反解的
    #: 最悲观角 ε*=ΔS·V_live/(g+ΔG)≈0.02×300/212≈0.0283 的诚实带
    #: 下沿档(诚实带 [0.03,0.10],超保底部分≈0.36 金当量/帧,显式
    #: 接受)。**重标定挂账(§2.4)**:p_i 源 streak_floor_win_rate 为
    #: sim 档证据;Δp(piece)(停手窗买 1★ 件次战胜负面差分 n≥30)与
    #: ε*(g) 随金自适应均未标定——落地后 ε 全带重推(ADR-0377 敏感
    #: 性口径)。首批辖域 P1 only(谓词内 state.plane==1 硬门);
    #: P2 扩辖独立批,不消费 p2_cond_loss_table/p_win_p2_by_rung。
    terminal_survival_eps: float = 0.03

    # ===== 成型停手纪律([13] 停手线;ADR-0343;迁移审计 w119(git 历史)/ADR-0347 收编)=====
    #: 总开关(False=旧行为,成型后照买;A/B 通道)
    formed_stop_enabled: bool = True
    #: 停手辖轮**全局下界**(迁移审计 w97(git 历史)/迁移审计 w105(git 历史) 晚买证据窗=r7-r9);实际辖轮=
    #: max(锁定线 typical_form_round, 此值)——comp 派生(迁移审计 w115(git 历史)-B1,
    #: 固定 r≥7 会固化「早成型阵容多买两轮」偏差)
    formed_stop_min_round: int = 7
    # (formed_stop_min_level 已随 迁移审计 w119(git 历史) 删除:等级不作为独立门槛——
    #  2026-08-25 用户裁决 Q2,等级通过上场完整性进入 form_ok 判定)

    # ===== 相位观测与授权(迁移审计 w114(git 历史)/ADR-0346 影子;迁移审计 w119(git 历史)/ADR-0347 切授权)=====
    #: (phase_form_score_gate 已随 `w132_b_arm/`/ADR-0353 删除:兜底门从 form_score 连续量
    #  改结构判据——`w118_baseline/` sim r2-r3 弱板误转真 + 实机 run15 r4 score 0.65 多线
    #  散板(仙舟3 单体系+配方档小数)过门两证;用户判读原则 2026-08-26「任何
    #  位面看阵容完成度」→ 判据 = 板面真收敛到 ≥2 过渡体系,非分数可达性。
    #  form_score 降级纯遥测观测,不进判据)
    #: 兜底局(意向未锁)form_ok 的轮数下限(迁移审计 w119(git 历史)/ADR-0347 校准判据,迁移审计 w113(git 历史) §8-11):
    #: `w118_baseline/` 实测 A 臂兜底局 form_score≥0.5 在 r2-r3 即转真——1 过渡体系≠战力
    #: OK。结构门下保留(合取):即使两体系早凑齐,r5 前板面人口/星级仍薄,
    #: 保守留 FORM(地板 20 允许买牌强化,不亏)
    phase_fallback_min_round: int = 5
    #: 兜底局 form_ok 的有效体系数下限(`w132_b_arm/`/ADR-0353):有效体系数 =
    #: ``_engines_count``(四体系单一源,deployed 口径)+ hp_charge_stack 型
    #: 全局累积角色豁免(上场 2★ 计 1,万敌;迁移审计 w127(git 历史) 字段消费)。取 2 =
    #: transition_combos 定稿「四体系两两组合=过渡成型,单体系点火≠成型」
    #: (三选二 140/328 帖;2026-08-23 用户定调)
    phase_fallback_min_engines: int = 2
    #: FORM 相位地板=保险丝(迁移审计 w113(git 历史) Q1 已裁决:决策器=EV 授权,FORM_FLOOR
    #: 只防收益端估乐观时花光本金;初值 20=沿用应急保底语义,**Q1 四档
    #: sim 对照(不设/10/20/30)待校准,本批只接线不标定**)
    form_floor: int = 20
    #: boss 破息窗 node_type 缺读兜底轮(迁移审计 w119(git 历史)/ADR-0347 统一口径:
    #: boss 窗主判据=节点图 node_type∈boss_round_node_types,轮数口径
    #: 全仓只留 discipline.boss_window_active 一处且仅作缺读兜底——
    #: P1 末节点恒为 boss 的节点图先验,r≥9 兜底)
    boss_window_fallback_round: int = 9
    #: 扑满节点(奖励型战斗)单节点刷新豁免上限(迁移审计 w119(git 历史)/ADR-0348×迁移审计 w120(git 历史) P8
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
    #: 刷新常量 EV 族已随 `w126_b_arm/`/ADR-0349 删除(refresh_ev/refresh_max_round/
    #: refresh_min_gold/refresh_starve_*/refresh_game_cap/levelup_reserve_
    #: gold/form_refresh_*:refresh 附庸闸整体退场——D 候选评分改 V_D 批口径
    #: (scoring.vd_refresh_score,P5 定理:expected_refreshes×刷价 vs 收益侧),
    #: 预算前提=C_interest 在 50 档边界的输出(G2,不设常量金门))
    #: 扑满节点(奖励型战斗)刷新 EV(`w126_b_arm/`:轮界门删除后,扑满凑伤害 D 的
    #: 独立小额 EV——受 piggy_refresh_round_cap 辖(P8:s≤2金/节点),
    #: 扫满即无证拒;值=旧 refresh_ev 沿用,语义收窄到扑满节点专属)
    piggy_refresh_ev: float = 2.5
    #: 买侧 C_interest 的回档折中视界(`w131_a2n_arm/`/ADR-0352):买候选跨息档的
    #: C = 档数 × min(R跨位面, 此值)。依据:P6 回档账下界(破档后
    #: 1-2 轮回档,真实息损 1-3 金)与平面 R 上界(P5⑤,≈20-23)的
    #: 折中——买是一次性金→板面资产兑换,「停在低档到位面末」的
    #: 上界前件描述的 FORM 政策态由相位地板辖,不在 EV 门重复计罚;
    #: 3.0=两界之间的保守中点,网格精调(1-5)留 sim 批。只辖买侧
    #: (arbiter.interest_rule 的 BuyCard 分支);刷新(D)与升级平台账
    #: 保持平面 R 上界不动(P5⑤ 退化输出/平台语义)。
    interest_recovery_rounds: float = 3.0
    # ===== `w154_p2d/`/ADR-0361 P2 段 V_D 修法(P11/P12 口径;常数归本层可 A/B 注入)=====
    #: P2 段 V_D 口径总开关:False=回 迁移审计 w153(git 历史) 前行为(窗二分=level_plan 互斥,
    #: 成本=批口径面值,收益=P1 骨架参数)——A/B 基线臂。P1 分支与开关无关
    #: (逐位不动,P1 sim 零漂移回归门)。
    vd_p2_enabled: bool = True
    #: P1 收益侧战斗期望掉血=条件败局伤害的线性拟合**截距**(遥测拟合:
    #: `w324_coarse_battle/` 战斗粗模型冻结语料 417 条战斗类差分,battle 节点败局伤害
    #: =截距+斜率×成型档,battle n=278/73 局聚类稳健、斜率 SE 1.25;
    #: 拟合产物随粗模型语料归档(复现锚=ADR-0424);
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
    #: 无条件均值拟合(胜态混在均值里)会系统性低估。来源=`w324_coarse_battle/` 冻结
    #: 语料 417 条拟合产物 two_state_model(粗模型定稿、语料快照复现
    #: 锚与对抗审计记录=ADR-0424);encounter=截距 24.32 +
    #: 斜率(−4.53)×成型档(斜率 SE 2.41 显著);boss 斜率 CI 含 0 →
    #: 退常数 26.71(背测 sim −22.61 vs obs −25.82)。
    streak_floor_loss_damage: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            'encounter': (24.32, -4.53),
            'boss': (26.71, 0.0),
        })
    #: 连胜 EV 地板胜率表(节点类型×成型档;取**注入后**值 p_injected
    #: =语料实测+plaza 先验只进 rung≥2、share≤0.25,来源同上
    #: 粗模型拟合产物的 win_rate_table_injected)。键域 0-2(消费侧
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
    #: (冻结语料同 run 相邻行 hp 差分;标定叙述与精度声明=ADR-0426
    #: 增补 A):普通战斗桶 20.05(n=19;
    #: 桶内零损行=0,实测口径核验=条件伤害)。置信声明(`w371_recal_attack/` 审计 M3):
    #: SD 10.38,事件级 t95% CI [15.0, 25.1],run 级聚类 bootstrap CI
    #: [15.1, 23.6](19 事件来自 13 run)——区间半宽 ±25%,取 20.05 与
    #: 取保守 22-25 在现有 A/B 判据下不可分辨,本值不做精度主张。
    #: 三源对照:语料条件 20.05 / 实机存活局事件均值 −15.3(59 事件,
    #: `w350_p2_survival/` REPORT §4)/ sim coarse 分 rung 条件伤 ~11——取语料上沿的
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
    #: P10① 携带溢价利息分量背书,`w151_p2/` 四局实证实现值≈0 → 起步 0)
    vd_p2_liquidity_rho: float = 0.0
    #: P1 体系对缺件找牌通道总开关(`w170_p1_vd/`/ADR-0369):False=回 `w166_pair_guard/` 前行为
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
    #: 核心升星价值项单位值(迁移审计 w88(git 历史)/ADR-0339,[13] 成型三件套第三件:
    #: 过渡核心 2★)。持有域内 star≥2 且∈目标集(意向目标∪引擎件)
    #: 的件数 × 此值——deployed 全额、bench ×bench_form_weight 折减
    #: (ADR-0295 混合域同式)。修的是第六局判读:star 此前只在阵营
    #: 计数(star×权重)与 targets 星级加权两条路径显影,engines 封顶
    #: 后 2★ 分差≈0 → 换阵卖 2★ 不罚分/凑合副本 ≈0 分(升星投资
    #: 系统性贬值)。0=关闭(A/B 基线臂)。
    core_star_unit: float = 3.0
    #: 3合1 中间进度项单位值(迁移审计 w96(git 历史)/ADR-0340,[13] 副本凑合爬坡段:
    #: 目标件第 2 份 1★ 的期权显影)。core_star 只辖 star≥2,迁移审计 w93(git 历史)
    #: 断买根因①:第 2 份买入在 targets/eng_frac/core_star/rung
    #: 全维度零 delta → 「非正分」拒 → 金 59→90 溢出趴三轮
    #: (run_20260825_130151 r7-r9,[17] >50 每一分都该花)。每名
    #: 只计第 2 份(第 3 份 merge 后 core_star 承接,不双计);
    #: deployed 域 ×1.0 / 纯 bench 域 ×bench_form_weight(ADR-0295
    #: 同式)。初值=core_star_unit 同量级(同一 2★ 目的地的期权),
    #: 未网格标定,sim A/B 方向见 deep_read/W96_报告.md;0=关闭。
    merge_progress_unit: float = 3.0
    #: (filler_star_unit/pair_copy_direction_exempt 已随 ADR-0402 定谳
    #: 清理删除:`w504_filler_star_adr0402/` 开臂 A/B 主判据双 wash,删除清单与证据链见该 ADR
    #: 定谳节;副本评分/放行现由 merge_completion_exempt(ADR-0438)与
    #: 末窗承接门 gap 豁免(ADR-0405)承载)
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
    #: levelup_reserve_gold 已随 `w126_b_arm/`/ADR-0349 删除:刷新×追级并存仲裁
    #: 的评分折扣与约束侧 A/B 通道整体退场——并存由 V_D(概率窗二分:
    #: goal=level_up 时 D 让位)与升级总账自然裁决,不再需要外加折扣)
    #: (goldrich_buy_bias/goldrich_min_gold/goldrich_buy_tags 已随
    #: ADR-0305 增补清理节删除:三窗 A/B 无一致方向 + ADR-0408 同构
    #: 复证「成型加速可见,hp 不跟」。与经济循环总模型(ADR-0445)的
    #: 辖域边界随之失效——本偏置原辖金 28-50 储备段,总模型溢余义务
    #: 只在 g>R* 激活,二者不重叠;删除依据=其自身 A/B 否决(开关
    #: 生命周期第 4 态),非义务覆盖。复活条件:储备段出现「0 分成型
    #: 件被结构性拒」的新病灶实证且修法经偏序/期望账论证,不复活
    #: 加性偏置形态。)
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
    #: (散买断,空窗/成型可开新);False=关闭(回 迁移审计 w70(git 历史) 行为,全引擎件
    #: 见即买)——A/B 通道,默认开。
    engine_affinity_enabled: bool = True
    # ===== `w150_buy_lock/`/ADR-0359 买侧通道锁定目标约束(`w143_formation/` 补充判读通道半边)=====
    #: 总开关:False=回 `w145_recipe_lock/` 后行为(A/B 基线臂)。锁定帧
    #: (cw_intention.locked_buy_scope 非 None)时,off_lock_buy_tags 辖的
    #: 买通道候选中「目标件 ∉ 锁定目标体系集」者在层3评分减
    #: off_lock_buy_penalty(降级非禁绝——板面差分显著为正仍可过;
    #: [31]④ 填充不变量:填充通道保持可回收垫层语义,不硬禁)。
    buy_lock_constraint_enabled: bool = True
    #: 约束辖的买标签(`w147_evolve/` 基调:优先级/围栏式,禁一刀切禁绝——
    #: 通道=run17 实证的 d2_line_opportunistic/d2_bond_fallback 两通道)
    off_lock_buy_tags: frozenset[str] = frozenset({
        'line_opportunistic', 'bond_fallback',
    })
    #: 非目标件降级分(设计推断,sim 校准;量级=target_hold_value 同阶,
    #: 让非目标件在同轮竞争中让位目标件,且与形成偏置(forming_bias)
    #: 同阶以抵消其对新体系引擎件的顶分)
    off_lock_buy_penalty: float = 3.0
    #: 末轮围栏(候选 B):位面末轮 boss 窗(discipline.plane_last_battle
    #: 口径)时 line_opportunistic 的非目标件直接拒(`w143_formation/` strict 型=
    #: 末轮 opportunistic 买∧引擎上场件下降联判,run17 直证 r9 四张
    #: 零目标件买入;末轮买入无恢复轮次)。目标件+填充(bond_fallback,
    #: [31]④ 梯队)不辖。
    off_lock_final_fence_enabled: bool = True
    # ===== `w155_evolve_lock/`/ADR-0361 evolve 换血事务锁定目标件保护(`w147_evolve/` 执行半边)=====
    #: 总开关:False=回 `w150_buy_lock/` 后行为(A/B 基线臂)。锁定帧
    #: (cw_intention.locked_faction_scope 非 None)时,演进提案
    #: (cw_evolution.propose_upgrades)中「目标体系 ∉ 锁定体系集」者在
    #: 最优选择序(_best_option)中减 evolve_off_lock_penalty——
    #: 降级非禁换(`w147_evolve/` 基调:成局 22% 良性中性轮换,禁换会伤;
    #: 优先级式让位,全部机会均 off-lock 时照选最优)。
    evolve_lock_constraint_enabled: bool = True
    #: off-lock 演进提案降级分(与 off_lock_buy_penalty 同阶设计:
    #: 让非锁定线提案在同轮竞争中让位锁定线;量级=一档
    #: _TIER_WEIGHT 的 3 倍,跨档压制单档优势)
    evolve_off_lock_penalty: float = 3.0
    # ===== 迁移审计 w160(git 历史)/ADR-0363 S1 型成型后引擎丢失修法(两件独立 A/B 通道)=====
    #: 件1·引擎下界守卫:False=回 `w155_evolve_lock/` 后行为(A/B 基线臂)。True 时
    #: execute_replacement 生成事务时,若事务净效果使过渡引擎数
    #: (cw_battle_calib._engines_count 口径)从 ≥2 跌破 2,被拆引擎体系的
    #: deployed 贡献件获得新线同级**留场资格**(不划进 old_line 下场)
    #: ——语义「换血可以,拆引擎不行」(ADR-0360 件3 只保「不卖」
    #: 不保「在场」,末轮无回场窗 → 永久丢失;迁移审计 w159(git 历史) §2:S1 局全部
    #: 37/37 通道=evolve_tx 整批下场)。护的是在场引擎贡献,不是库存。
    evolve_engine_guard_enabled: bool = True
    #: 件2·末轮演进冻结:True 时位面末窗(剩 ≤1 轮,round_num ≥
    #: NODES_PER_PLANE-1)演进换档(undeploy/sell 非空的拆板事务)
    #: 冻结不发射——纯加深(deploy-only)与填位照旧;与 `w150_buy_lock/`
    #: final_fence(ADR-0359 买侧末轮围栏)语义对齐:末轮换档天然
    #: 无回场窗,「加深收益 < 引擎丢失风险」在该窗口系统性为真
    #: (迁移审计 w159(git 历史) §1:r_loss 90% 落 r8-9)。
    evolve_final_freeze_enabled: bool = True
    # ===== `w174_deploy/`/ADR-0371 引擎补完守卫(own-gap 修法)=====
    #: 总开关:False=回 `w170_p1_vd/` 后行为(A/B 基线臂)。True 时
    #: cw_evolution.evolution_step 在常规演进提案**之前**发补完事务:
    #: pair 体系(p1_pair ∪ transition_pair,含希儿系单卡判据)
    #: owned(bench∪deployed,全羁绊口径)≥ tier ∧ on-board
    #: (board_factions 口径)< tier → bench 该体系成员上场,room 不足
    #: 换下最弱非保护件(保护=pair 成员/引擎件/锁定目标件/种子窗)。
    #: 修「拥有≥门槛却从未同时上场」(`w173_supply/`:8/11 never-2 局,件躺备战
    #: 席到局终;[20] 件上场才算配方,[13] 过渡成型≈过 P1)。末窗冻结
    #: 豁免复核 = 净效果 pair on-board 与引擎数不减(ADR-0363 件2
    #: 防丢语义同向:补上不是拆)。
    evolve_engine_completion_enabled: bool = True
    # ===== `w201_strand/`/ADR-0381 补完缺口 owned 口径(distinct;修②)=====
    #: 补完事务缺口判定的 owned 计数口径:True=distinct 名单数——
    #: 同名副本是 3合1 升星素材非配方件([20] 配方=不同成员;board
    #: 同名唯一 → 副本永远不可上,全羁绊逐件计数会造出「永远填不满
    #: 的幻影缺口」,`w200_probe/`:227/276 补完轮轮空转);False=回 `w174_deploy/` 后
    #: 全羁绊逐件计数(ADR-0371 首版口径)。
    engine_complete_distinct_owned: bool = True
    # ===== `w202_grade/`/ADR-0382 补完保护集分级(136 型构造闭死修法)=====
    #: 补完事务 undeploy 常规候选枯竭(deployed 全保护,`w200_probe/` 136:
    #: 锁定线件+引擎件全覆,列车缺口 r6-r9 轮轮被选但 tx 永远建不出)
    #: 且缺口体系已连续被选 ≥4 轮(标定:门 2/3 有 benign→mal 坏翻转,
    #: 门 4 全硬门过——benign→mal=0/mal 24→20/never2 10→7)时,
    #: 按分级序降级换血:G0 非引擎锁定线件(locked_buy_scope∩非TT,
    #: 最可动)→ G1 未成型引擎件(下之不拆成型引擎)→ G2 已成型
    #: 引擎件/pair 成员/希儿系贡献件恒不可动。依据 [13] 过渡成型≈
    #: 过 P1(成型缺口=发令枪级)让位于 [23] 锁定线语义;False=回
    #: ADR-0371/0381 后「不硬拆」。
    engine_complete_grade_down: bool = True
    # ===== `w179_gate/`/ADR-0372 P1 早期新件买入门(双条件窗:缺件密度 × 息档口径)=====
    #: 总开关:False=回 `w174_deploy/` 后行为(A/B 基线臂;FORM 相位地板对配方对
    #: 件买入照旧全拒)。True 时 arbiter.gold_floor 对满足窗的 BuyCard
    #: 放行「买入后同息档」的购买(窗语义见 discipline.p1_early_gate_open
    #: 与 arbiter 的逐笔息档/单轮上限检查)——修 `w173_supply/`/`w175_gate/` 的 pass_buy
    #: 形态(own<门槛=买少了:缺件曾 1-3 费出现在店、金 7-15 金穷轮,
    #: 被 FORM 地板 20 一刀切拦掉,违反口述 [11] 档内购买不损息)。
    p1_early_gate_enabled: bool = True
    #: 窗的缺件密度门槛:派生配方对(cw_intention.p1_early_pair,未锁期
    #: 同样派生)未持有 distinct 对成员数 ≥ 此值才开窗。标定(`w179_gate/`,
    #: n=100 池 861fc9f6):全体 P1 轮 unheld 分布 [8,16](r1 p10=14 /
    #: r9 p10=8),pass_buy 病灶轮 unheld 11-15——k 在 [1,8] 带内对本
    #: 分布**无区分度**(诚实记档:operative 约束=息档口径+单轮上限+
    #: 层3评分),取 6=「板面远未覆盖配方对」的语义守卫(关掉假想的
    #: 近成型窄窗,防未来分布漂移把门开进不该开的段)。
    p1_early_min_missing: int = 6
    #: 单轮放行笔数上限(防 r1 扫店):同息档口径下金 12-19 连买 1费
    #: 可达 2-9 笔(`w179_gate/` 标定:门内笔数 p50 0-1 / p90 1-3 / max 7,
    #: 病灶轮 1-2 笔)——取 1=「目标件刷新出现=唯一最高优先级,只买它」
    #: ([31]② 逐字口径;n=100 扫描 cap1 出口金 34.23 与基线 34.25 持平
    #: =P13 同档零损的理论预测逐位兑现;cap2 −2.3 金换 hp +1.3,
    #: 出口金口径上不如 cap1 干净)。每轮增量支出 ≤3 金,息损上界=档内 0。
    p1_early_round_cap: int = 1
    # ===== `w184_sellguard/`/ADR-0373 卖侧唯一体系引擎守卫(S2 恶化谱系)=====
    #: 总开关:False=逐位回 `w179_gate/` 后行为(A/B 基线臂)。True 时
    #: discipline.sole_engine_sell_blocked 命中的件不进任何卖件通道——
    #: 判据=该件是四过渡体系(TRANSITION_TRAITS 三羁绊:仙舟/列车同行/
    #: 持续伤害,全羁绊 factions∪flows 口径;`w192_seelex/` 起希儿系贡献件另经
    #: guard_seele_scope_enabled 并入辖域)成员,且其所属某体系的
    #: 在手件数(bench∪deployed 逐件计)≤ 该体系 tier 门槛 → 卖出会
    #: 「清空该体系当前唯一 owned 引擎件」或「在手数跌破 tier」。
    #: 消费面=candidates._sell_tag(arbiter off_target/for_gold/
    #: free_bench 候选生成)+ discipline.sell_priority_key 守卫
    #: (carry_gate ④/两补偿器统一挡)。修「演进换线把旧体系件下场到
    #: bench 后被 off_target 当死库存卖出 → 体系引擎永不回场」
    #: (`w181_residual/` §3:S2 恶化 {37,71,90,43} 与 `w174_deploy/` 残差 {45} 全此链;
    #: 卖出的件均非 engine_char_names 名单件,方向切换后失去目标身份)。
    #: 不辖:非 TT 件/owned>tier 的冗余件(体系有余量时清仓照旧)/
    #: execute_replacement 保留序卖出(ADR-0360 件3+ADR-0363 件1
    #: 已辖)/谷底回滚 SellDeployed(恢复机件)。
    sell_sole_engine_guard_enabled: bool = True
    # ===== `w192_seelex/`/ADR-0375 希儿系守卫辖域补全(迁移审计 w190(git 历史) 巡检两件)=====
    #: 希儿系(四过渡体系之一,单卡判据)并入卖侧唯一体系引擎守卫与
    #: 演进保护集辖域(**核心条件辖**,域修正见 ADR-0375):希儿本人
    #: 唯一种子不可卖/恒保护;放大器件(量子同频/贝洛伯格)仅当希儿
    #: 在手时辖(卖拒=放大阵营在手 ≤2 成型门槛;保护集并入——补完
    #: undeploy/execute_replacement 保留序不下);无希儿时放大器
    #: 不是体系件(transition_combos:28 帖全部含希儿),照旧合法面。
    #: False=逐位回 `w188_threestack/` 后行为(辖域=TRANSITION_TRAITS 三羁绊——
    #: deploy 排序语义被 ADR-0373/0371 借用造成的缺口,见 迁移审计 w190(git 历史) 洞一/二)。
    #: **新 flag 而非复用 sell_sole_engine_guard_enabled**:后者 off 会
    #: 连 TT 三羁绊辖域一起关,A/B 配对臂(只隔离辖域差)与回退粒度
    #: 都不对;辖域修正是 0373/0371「四体系」声称的语义补全,默认开。
    guard_seele_scope_enabled: bool = True
    # ===== `w197_comptx/`/ADR-0380 卖侧下界守卫执行点补全(own_gap 演进谱系)=====
    #: 总开关:False=逐位回 `w195_intent/` 后行为(A/B 基线臂)。True 时
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
    #: 引擎键∪pair 成员保护已覆盖,`w192_seelex/` 辖域不变)。
    sell_floor_exec_guard_enabled: bool = True
    # ===== `w194_p2line/`/ADR-0378 [33] 稳态 LevelUp 多击组(迁移审计 w185(git 历史) 泛化)=====
    #: 总开关:False=回 `w193_p2sim/` 后行为(A/B 基线臂——多击组只在轮内
    #: deploy_cap 拒绝触发补偿时发射,Catch-22 原状)。True 时
    #: arbiter 末段主动发稳态多击组(remediation.steady_state_
    #: levelup_group):进轮 cap 满 ∧ bench 有方向件([33] 稳态字面
    #: 语义)→ [LevelUp]*clicks_to_next_level 整组,授权=
    #: levelup_ev_basis 按 n×总价(稳态下人口位臂天然成立)+
    #: 逐动作 gold_floor 事务性重验(与 deploy_cap 补偿臂同一重验
    #: 链)。修「恒 lv6 通道缺陷」(迁移审计 w185(git 历史):每轮 1 击吞吐,lv6→lv7 需
    #: 7 轮,死亡窗内不跨;run15 型死局的 lv7 价格带永不可达)。
    #: 每轮至多一组(session.v2_steady_lv_used 轮键,防刷后 re-decide
    #: 段链连发);boss 轮禁升([32])与 level_max 前置守卫保留。
    #: **辖域 P2+**(首版全位面泛化 n=300 引入 P1 never2 9→10 回归,
    #: `w194_p2line/` 辙回——P1 多击已由 deploy_cap 补偿臂覆盖)。
    levelup_multihit_enabled: bool = True
    # ===== `w194_p2line/`/ADR-0378 件3:P2 核心件首件同档买入门(`w183_carry/` 方向②)=====
    #: 总开关:False=回 `w193_p2sim/` 后行为(A/B 基线臂)。True 时 P2 段
    #: (plane≥2)意向核心(v3_core_names)的**首件**(working 现持无
    #: 同名)在 gold_floor 拒绝前放行「买入后同息档」的自然店购买
    #: (arbiter._p2_core_firstpiece_exempt)——[31]②「目标件刷新出现
    #: =唯一最高优先级」+[11] 同档零息损+[22]③ 弃购代价=再遇窗口
    #: (3费@lv6 E=27 次刷新 / 5费 60-180 轮)。修 `w194_p2line/` 探针实证的
    #: 「P2 穷轮(gold<50)核心件在店被 HOARD 地板 50 一刀切拦」
    #: (n=10:核心在店 6 轮漏买 5,全部 gold≤12 穷轮)。单轮 1 笔
    #: ([31]② 只买它);零刷新授权(与 `w170_p1_vd/`/迁移审计 w185(git 历史) 刷门管辖不交集)。
    p2_core_firstpiece_enabled: bool = True

    # ===== `w300_dup_ruling/` press 通道:目标外同名副本压库购买(5 参数,V-B3 全量
    # registry 化;arm0=默认值全关零漂移,armA=注入开启;A/B 结论落地后
    # 按 ADR-0411 先例逐字段裁决去留;评分偏置两字段已随 ADR-0427 增补节
    # 定谳清理)。设计规格与 A/B 兑现裁决=ADR-0427(v3 规格节与其谱系
    # 记录见该 ADR;A/B 兑换统一裁决表(V-B4;锚定义=规格 §5.3,冲突处以本表为准):
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
    #: 默认开(`w368_press_ab/` A/B:n=300/臂 R2 成立——seg 真拦 −85.6%、通道开通
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
    #: (press_copy_unit/press_core_mirror_bonus 评分偏置两字段已随
    #: ADR-0427 增补节定谳清理:copy_press 评分路由双层悬置(生产默认
    #: 0.0 从未注入生产行为 ∧ 生成域被上游臂截流至近空),无观测支点。
    #: 评分臂删除后 copy_press 候选评分只由通用板面维决定,与删除前
    #: 默认态(press_copy_unit=0.0)逐位一致。通道价值主体(总闸/band/
    #: 双 cap/[11] 豁免臂)保留,见 ADR-0427 增补节删除清单。)
    #: press 候选逐轮采纳笔数上限(V-B8.1,更严一级;量级=单轮至多
    #: 一笔压库副本,与 p1_early_round_cap=1 同式轮键计数)。
    press_copy_round_cap: int = 1
    #: [11] 同档/1费豁免臂(§3.3 三相位共用前置臂)逐轮放行笔数上限
    #: (V-B8.1;量级锚=`w179_gate/` p1_early_round_cap=1 先例,取 2 因该臂辖
    #: 方向内候选+press 候选两股)。
    press_exempt_round_cap: int = 2

    #: (form_refresh_ev/form_refresh_max_round/form_refresh_min_gold/
    #: form_refresh_engines_target 已随 `w126_b_arm/`/ADR-0349 删除:成型找件刷新
    #: A/B 残留通道退场——找件语义由 V_D 批口径承接(核心未齐+概率窗内
    #: 的定向找件是 V_D 的本体场景,不再需要独立常量通道))

    # ===== `w227_handoff_gate/`/ADR-0400 P1 末窗承接门(设计件 08 §4.2 Phase 1)=====
    #: ADR-0411 flag 家族清理(2026-09-03):承接门自本批起**无条件启用**
    #: ——历史 handoff_gate_enabled 布尔字段删除。验证史:`w247_joint_full/`/迁移审计 w254(git 历史)-R
    #: 两轮复核 gate 单开 outcome 无正方向(迁移审计 w254(git 历史) 判边际为负),但门是
    #: star/refresh 两通道授权的判据语境(gap 单一源),行为面随其一并
    #: 转正;裁决与四通道验证结论单一源 = ADR-0411。
    #: 行为语义:P1 末窗(r>=handoff_gate_min_round)投影承接档位
    #: (handoff.handoff_gate_gap 单一源)未达标:①成型停手线不停手
    #: (filters.formed_stop_active 承接维,[18] 位面末 ALL IN 的承接
    #: 扩展);②interest_rule 买侧破息 EV 账加缺口项
    #: (handoff_ev_gap_bonus×缺口)。只辖 P1 末窗(P1 非末窗零漂移
    #: 门的结构前提)。量级常量保留供调优。
    #: 末窗下界。原初值 8 口径=`w227_handoff_gate/`/ADR-0400「P1 r8-r9(boss 窗)」。
    #: **`w288_gate_landing/`/ADR-0418 前移 8→6**(`w275_knob_ab/` 三映射兑换:「方向对、量级待
    #: 实机定标」类常量调整):合资格授权窗加宽到 {r6..r9},承接门家族
    #: (filters 成型停手承接维/arbiter 缺口项/candidates 副本放行/M-A
    #: 定向刷新窗)整体提前点火。证据链(`w275_knob_ab/` 四臂配对 AB,n=200,v11
    #: 冻结池 7af81977 同 seed):core2≥1 进场率 12.17%→18.85%(配对
    #: 翻转 22:9,二项单侧 p≈0.025;剂量-响应单调 gr7 15:7);进场金
    #: 均值差 −1.50 CI 含零(金面免费);末 HP/hp0/P2 进场率全无信号。
    #: 落地前置双核验过(记录=ADR-0418):
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

    # ===== 迁移审计 w238(git 历史)/ADR-0403 承接门 hp 维 boss 投影(设计件 09 §3.1)=====
    #: ADR-0411 flag 家族清理:投影自本批起**无条件启用**——历史
    #: handoff_boss_project 布尔字段删除(曾默认关:迁移审计 w238(git 历史) 三臂 A/B 后
    #: 未解锁;转正裁决见 ADR-0411——量级问题非行为开关)。语义:
    #: handoff_gate_gap 末窗投影的 hp 维由「当前 hp(boss 前)」换
    #: 「boss 后投影 hp」:
    #: hp_proj = hp + 2(r8 奖励胜,设计件 09 §1.1 五局恒 +2) −
    #: E[boss 伤害|净星深档](r9 无 +2;迁移审计 w240(git 历史) 起档键=净星深,
    #: ADR-0404)。修标定口径错位(喂给
    #: HANDOFF_HP_CUTS(boss 后真值标定,ADR-0399)的 hp 取 boss 前值
    #: = hp 维系统性高估一档;设计件 09 §2)。
    #: E[boss 伤害|净星深档] 常数表(**正数=期望掉血量**;离线标定非
    #: 运行时预测)。标定源=Δ池 plane=1 boss 桶(**净星深键** = 上场件
    #: Σ(star−1) 桶 min(sd//3,5)*3,迁移审计 w240(git 历史)/ADR-0404 替旧 Σboard 键——
    #: 修 3合1 升星使 Σboard −2/次落浅桶而浅桶期望伤害更大、sim 判
    #: 「升星→boss 伤害↑」与 [27] 机制相反的方向冲突)地板删失行剔除
    #: (hp_after∈{0,1}=下界非真值,ADR-0307 口径)后的桶均值:
    #: 2026-09-03 重标定 n=28 未删失/删失 21,**桶 0:n=28/27.57——
    #: P1 boss 语料净星深全落桶 0**(旧 Σboard 桶 9/12/15 的条件性
    #: 系键口径伪影:升星减件使强板落浅桶、浅桶均值被强板样本抬升
    #: ——方向冲突的语料侧成因,ADR-0404)。
    #: 标定口径与档键迁移裁决=ADR-0403/ADR-0404。**已知边界**:删失剔除使留存样本
    #: 偏向「存活 boss 的局」(弱板真值伤害被低估);净星深≥3 的
    #: 深桶零样本——star_depth 条件性在当前语料下不可辨,常数表
    #: 实为无条件期望,语料攒厚后复验。
    #: boss Δ 全分布双峰(迁移审计 w244(git 历史),2026-08-27):低伤簇 n=8 均值 13.25(SD 1.04)/
    #: 高伤簇 n=20 均值 34.10(SD 1.77),中间带 [16,26) 零观测——单值均值
    #: 27.57 落谷底不近似任何真实伤害。**投影口径取 Q3≈34**(保守:均值使
    #: hp 临界局 tier 高估一档=重蹈 迁移审计 w234(git 历史) 缺口;低估方向仅更保守可 AB 校正);
    #: 协变量(Σboard/净星深/日期/comp/streak)无一解释簇归属,嫌疑首因=
    #: boss 敌型(outcomes 无 boss_name 字段——数据采集欠账,攒齐后按敌型
    #: 混合重标定)。分布数字以本注释为单一源(2026-08-27 boss 伤害
    #: 分布重标定,离线标定产物随对局遥测语料归档);投影口径取 Q3 的
    #: 前移耦合挂账=ADR-0418。
    handoff_boss_e_damage: dict[int, float] = field(default_factory=lambda: {
        0: 34.0,
    })
    #: 缺桶 fallback:同上 Q3 口径(单桶语料下与桶 0 同值)
    handoff_boss_e_damage_default: float = 34.0
    #: r8 奖励节点胜 +2(设计件 09 §1.1:五局全部 r8→r9 恒 +2;hp 不可
    #: 回复下唯一正项)。触发条件历史绑定 handoff_gate_min_round(值=8
    #: 时恰为「r8 加、r9 不加」);`w288_gate_landing/`/ADR-0418 该常量前移到 6 后触发
    #: 点随移至 r6——语义已偏离「r8 奖励」本义(r6/r7 投影少算后续节点
    #: 期望伤害,偏乐观),解耦挂账 ADR-0418(改行为代码须重跑 AB)
    handoff_boss_reward_bonus: int = 2

    # ===== `w242_star_directed/`/ADR-0405 末窗星级定向授权(`w232_filler_star/` 挂账 C 项;设计件 08
    # §4.2 Phase 1b 星级投资方向)=====
    #: ADR-0411 flag 家族清理:末窗星级定向授权自本批起**无条件启用**
    #: ——历史 handoff_star_directed 布尔字段删除。验证史:`w242_star_directed/` 四臂
    #: A/B 行为面强正(core2≥1 进场率 +150%)但单独不改变结局;转正
    #: 依据 = star 是 `w231_star_diag/`「评分结构性拒副本」病灶的正解且 sim 无挤出
    #: (量级不足属参数调优非行为开关,裁决见 ADR-0411)。行为语义:
    #: P1 末窗(r>=handoff_gate_min_round)承接缺口 gap>=1
    #: (handoff.handoff_gate_gap 单一源)对**同名副本买入**给定向授权
    #: ——candidates 层放行副本候选生成(r410 守卫+方向门,`w232_filler_star/` A/B
    #: 豁免的 gap 条件化分支)+ arbiter 非正分门放行副本(`w231_star_diag/` 主因:
    #: 副本评分零维被结构性拒,到不了 EV 账)。**授权值单一源 =
    #: interest_rule 的 handoff_ev_gap_bonus×gap(零新增数值通道/
    #: 防双计)**;地板族/copies_cap/r408 同轮守卫/bench 容量照常辖。

    # ===== `w252_ma_directed_refresh/`/ADR-0409 M-A 定向 D 牌授权窗(`w249_core2_reach/` 诊断修法)=====
    #: ADR-0411 flag 家族清理:M-A 定向刷新自本批起**无条件启用**
    #: ——历史 handoff_refresh_directed 布尔字段删除。验证史:`w252_ma_directed_refresh/`
    #: 三臂 AB merges +47%/hp0 改善但 cap6≈半跳量级;转正依据 = M-A
    #: 是 `w249_core2_reach/`「策略从不支付搜索成本」病灶的对症修法且方向为正
    #: (量的解锁归 cap 提升独立批,裁决见 ADR-0411)。行为语义:P1
    #: 末窗承接缺口 gap>0(handoff.handoff_gate_gap 单一源复用)**且**
    #: 存在追名 peak≥2 的目标件(锁定采购目标名集内某名 star 加权在
    #: 手副本 ∈[2,3),距 3合1 只差最后一张)时,向刷新(RefreshShop)
    #: 开放有界预算。**只辖刷新维**(防双计,`w232_filler_star/` A/B/`w242_star_directed/` C 各辖买牌
    #: 维,互斥边界:同一动作只有一条授权来源——买候选走既有
    #: interest_rule 缺口项/copy 放行路径不动;refresh 候选要么走既有
    #: V_D 正分/gold_floor 路径,要么凭本预算有界放行,无叠加);
    #: copies_cap/r408/bench 容量等约束链照常辖。
    #: 单合资格轮刷新次数上限(`w249_core2_reach/` 白盒估算初值:每轮 ≤2 次)
    directed_refresh_per_round: int = 2
    #: 每局刷新总上限(`w249_core2_reach/` 白盒估算初值:≈覆盖一颗 2★ 的第二跳
    #: 6-7 次;消耗计数 session.v3_dir_refresh_used,decide_prep 轮首
    #: 不重置——局级累计)。金消耗披露面:预算放行的每次刷新照付刷价,
    #: 金账户由 simulate 真值扣减,P1 末窗利息损失随 A/B 守门指标判读。
    #: **本常量是非绑定约束(`w274_cap_batch/`/ADR-0413)**:合资格授权窗 = gap>0 ∧
    #: r>=handoff_gate_min_round(`w288_gate_landing/`/ADR-0418 前移到 6 ⇒ 窗 {r6..r9}),
    #: per_round 2 ⇒ 窗内可行上限 8 次曾在本值 6 之上;`w275_knob_ab/` gr6 臂
    #: (n=200 同 seed 配对)dir 授权 339 次、cap 开始参与钳制(窗容量
    #: 8 > cap6),行为面为正(core2≥1 +6.7pt)——cap 是否重新 bind 的
    #: 定标归后续实机/大批核对,非本批变更理由。历史候选档
    #: 留证:cap10/cap14 曾作为「第二跳吞吐量级」修复候选(迁移审计 w254(git 历史)-R 断点),
    #: 实验证明无效,勿重复试错。「加量」的有效旋钮是
    #: directed_refresh_per_round 与授权窗宽度(gate_min_round 前移),
    #: 非 game_cap(见 ADR-0413 Considered Options)。
    directed_refresh_game_cap: int = 6

    # ===== (early_pace 五字段已随 ADR-0408 增补清理节删除:三窗 A/B
    # ===== outcome 无一致正方向、机理核 rung 路径不动,见该 ADR。)=====

    # ===== W332b 未成型期姿态:泄息通道(release)与换线判据参数 =====
    #: 危机金出口臂(ADR-0503;W907 病灶:hp≤emergency_hp 帧应急让位使
    #: release 恒 None,溢余金在死亡门口零兑换)。True=危机帧(应急带∧
    #: 溢余)产 reason='crisis' 泄息指令(预算=min(溢余,REFRESH_ROLL_CAP×
    #: 刷价),posture 降级 tag='release');False=让位现行为(release 让位,
    #: 零漂移锚)。默认 True=开关生命周期第 3 态(开臂):开臂判据①sim A/B
    #: 实花面通过(W917/W930 补判 on 28.33% vs off 22.00%,配对 +20/−1;
    #: W933 病灶窗复测 on 27.20% vs off 22.00% 同向)+ 首局实机病灶复现
    #: (复盘 g_20260831_032006 P2 r1/r2:hp≤25 持金 72/85 零兑换,病灶
    #: 形态逐项吻合)——据此翻默认;实机观察局 ≥2(危机帧 release tag +
    #: 实花分项账非全零 + hp 可信位)为**确认门**,非开臂门,进行中
    #: 挂账 ADR-0503 §开臂判据(尾注)。
    crisis_release_enabled: bool = True
    #: 设计决策单一源=ADR-0426(谱系节含设计稿索引与两轮对抗修订记录)。**符号不稳参数一律默认值+标定接口,不拍死**:
    #: k(hp)/Δhp/boss 税由 sim 批网格标定后锁值(DESIGN §⑥ EV 参数门)。
    #: (总开关 release_enabled 已随 ADR-0426 增补 D 第 4 态清理:被经济
    #: 循环总模型 ADR-0445 的溢余义务吞并,行为恒接线。)
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
    #: ADR-0441 接线后运行时消费点(posture_release 末窗投影臂)已改读
    #: boss_tax_p75_by_plane,本标量无运行时消费者——保留原因=sim 标定
    #: 接口 boss_tax_anchor_group 的 P75 同源值 + 既有零漂移锁底座
    #: (test_cw_boss_tax_p75_by_plane)与 P1 语料出处引用锚;退役挂账
    #: sim 标定批裁定(届时锁与 anchor_group 一并迁 by_plane 单一源)。
    boss_tax_p75: float = 34.0
    #: boss 税分位锚组 {P50, P75, P90}(sim 标定接口,非运行时值)
    boss_tax_anchor_group: tuple[float, float, float] = (32.0, 34.0, 36.0)
    #: boss 税 p75 位面锚(消费点按位面取值;键 = GameState.plane,1/2)。
    #: plane 1 = 现值原样,与 boss_tax_p75 同源(P1 语料标定),零漂移锚;
    #: plane 2 槽位已就位但默认仍取现值——sim 侧位面观测
    #: (cw_coarse_battle 标定 manifest 的 hp_events_by_plane:P2 boss
    #: n=90 均损 −21.63 vs P1 −19.54)已给 P2 真值方向,但 P2 槽位换
    #: 数据的扰动未评估。激活挂账:待形态 A/B 开臂判据收口后,与 sim
    #: 收入口径修正同批评估;重标定覆写只改本字段(单一源)。
    #: ADR-0441:FLIP 末窗投影臂(posture_release)与 C1 投影安全带
    #: (filters)两消费点均已按位面取数;评估结论=暂不激活(plane 2
    #: 维持 34),复核触发条件见该 ADR。
    boss_tax_p75_by_plane: dict[int, float] = field(
        default_factory=lambda: {1: 34.0, 2: 34.0})
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
    # (release 帧活栈消费门开关 release_spend_gate_enabled 已随 ADR-0426
    # 增补 D 第 4 态清理:开臂 A/B 结案,消费门恒接线,判据单一源=
    # posture_release.spend_gate_active 读 session.v3_release。)

    # ===== P2 生存批:换线存活轮数门(C4) =====
    #: 设计决策=ADR-0426 增补 B(C3/C4 重设计裁决)+ADR-0429(C4 接线):
    #: C4 剩余节点序列逐节点投影/双源标定。
    #: 标定=双源重标定(死亡真源=实机对局台账 runs.jsonl,
    #: hp≤1 不删失、hp_after=0 死亡行按 hp_before 全额入桶、不按置信度
    #: 过滤——旧删失口径「置信<1 剔除」系统性剔死亡局帧=反保守,已废;
    #: 产物为双源标定台账(记录=ADR-0440 三表对齐节),双源互校:帧级合并均值 10.79 ∈
    #: run 级聚类 bootstrap CI [6.7,10.97])。
    #: P2 节点损血表(节点型→**无条件期望损血**,正数)。
    #: ⚠️ 消费面声明:本表**不进任何行为公式**(两态决策层与阈值层 μ
    #: 一律吃 p2_cond_loss_table,见该字段)——本表语义=迁移审计 w375(git 历史) 无条件期望
    #: 的**标定自洽锚**:与条件败面表的比值隐含各节点型桶的板强混合
    #: 平均存活率(1−无条件/条件:normal 0.204/encounter 0.100/boss
    #: 0.000,对齐锁钉死)。这是 kind 坐标上的桶均值,不是 rung 阶梯,
    #: 与 p_win_p2_by_rung 的 rung 坐标不同——「同 rung 恒等式无条件=
    #: (1−p)·条件」在两表间不成立也不应成立:样本窗(迁移审计 w375(git 历史) 实机深层局
    #: vs `w346_gate_validation/` sim Δ池)与坐标(kind 桶 vs rung)均不同,详 ADR-0440
    #: 三表对齐节。
    #: 覆写=迁移审计 w375(git 历史) 双源重标定的无条件期望三档(normal 10.16/encounter
    #: 12.00/boss 15.50,CI 记录=ADR-0440 三表对齐节;原「旧删失
    #: 口径条件常数暂抄」20.05/16.67/26.71 随两态消费口径定稿退役,
    #: 见 ADR-0440)。node_type 缺读兜底=normal(战斗节点频率最高档,
    #: 2/5 槽;触发宽度居中——三档中 encounter 最小、boss 最大,normal
    #: 兜底既非最紧也非最松)。reward 零损档承接奖励+补给零损日历轮。
    #: 边界声明:本表与 p2_cond_loss_table 是同一 迁移审计 w375(git 历史) 标定的两个
    #: estimand(无条件期望 vs 条件败面),按消费语义分表,非双源漂移。
    p2_node_loss_table: dict[str, float] = field(default_factory=lambda: {
        'normal': 10.16, 'encounter': 12.00, 'boss': 15.50, 'reward': 0.0})
    #: P2 条件败面损血档(输了战斗这一条件下的期望伤害;两态决策层
    #: 损血幅度唯一源,消费点=cw_line_switch.rounds_alive 逐节点投影
    #: 与两态胜率映射(cw_plane_table.p_win_p2)——E[损血|板强]=(1−p_win(rung))·本表)。
    #: 值=迁移审计 w375(git 历史) 双源重标定条件败面(normal 12.77/encounter 13.33/boss
    #: 15.50,标定叙述见 p2_node_loss_table 段头与 ADR-0440):reward 零损档同上表(奖励/补给零损照走)。
    p2_cond_loss_table: dict[str, float] = field(default_factory=lambda: {
        'normal': 12.77, 'encounter': 13.33, 'boss': 15.50, 'reward': 0.0})
    #: P2 损血标定家族版本披露锚(第三维,独立于 cw_coarse_battle.
    #: COARSE_CALIB_VERSION 与 cw_economy 收入口径版本):任一 P2 损血
    #: 标定值/消费口径变动(p2_node_loss_table / p2_cond_loss_table /
    #: p_win_p2_by_rung / 两态递推形态)必须递增并随批重锁。sim 台账
    #: manifest 不承载本版本(cw_sim 禁触批,披露面=registry+锁,边界
    #: 如实声明)。v1=迁移审计 w375(git 历史) 覆写+两态递推定稿(ADR-0440)。
    p2_loss_calib_version: int = 1
    #: C1 定向刷新存在性名集的「高费强件」费用下界(买侧不辖名单,
    #: 只辖刷新存在性名集;消费点=filters._refreshable_names)。来源=
    #: 对抗审计 A1-β 反例画像「4 费通用强件是最高 Δp/g 选项」(记录=
    #: ADR-0426 挂账 2)+ sim 分
    #: rung 胜占比 0.34→0.65 单调(`w346_gate_validation/` 报告 §3.2 实证底座)=高费高星
    #: 战力优势。原批名 dying_band_high_cost_floor(C3 濒死带首用),
    #: C3 已定谳清理(ADR-0426 增补节)后随批改中性名,取值与消费
    #: 语义不变。
    directed_refresh_high_cost_floor: int = 4
    #: C4 存活轮数门总开关:False=现行为逐位一致(零漂移锚;与 drought
    #: bail 的或-并存结构不变,本门是 E_rounds 主判据的第三道串联门,
    #: 不造第二换线机制)。True 时 E_rounds 换线裁决通过后加验
    #: rounds_alive(剩余节点序列逐节点投影)≥ E_rounds(新线)×(1+δ)
    #: +兑现余量——存活轮数不足=新线到不了兑现点,换线期望 0<驻留
    #: 旧线(「转进死线」堵门)。辖域 plane≥2(损血表为 P2 标定);
    #: drought bail 旁路不辖(或-并存结构不变,弃线不是转进)。
    #: **开臂判据挂账(锐化终版,W665 DESIGN v2 §4;退役批(ADR-0466/0467/0469) 初版挂账)**:
    #: 与 rounds_two_state_enabled 正交——本门辖「是否验存活轮数」、
    #: two-state 辖「怎么算存活轮数」(单变量归因,禁 2×2 耦合臂)。
    #: 主判 = W643 定钉谓词「r6–r8 换线且 ≤3 轮回锁原线」占比 on 相对
    #: off 降 ≥1/3 且 p<0.05(三窗联合 630000–630199/900000–900099/0–29,
    #: 窗敏感,单窗不判定)。机制判 = **反事实拦截精度 ≥2/3**:off 臂对
    #: 每次换线事件记反事实判定位 P(f)=[R(f)<E(alt,f)(1+δ)+m](账本行
    #: line_gate_cf_blocked;判据单一源=cw_line_switch.gate_counterfactual,
    #: on 臂即门判定不重复算、检查器禁复算判据式),精度 = P(f)=True 的
    #: 换线中「≤3 轮回锁原线 ∨ 新线未成型」占比——低于 2/3 = 门在该
    #: 参数域系统性拦错,回炉 δ/m 而非开臂。「换线拦截率>0」降格为冒烟
    #: 项(仅验接线正确性);「濒死带时长不劣」保留(方向独立)。A/B 另
    #: 带中盘分桶机制检查(target_comp 变更率按 r≤4/r5-r9 分桶,
    #: cw_sim_checks.check_line_switch_midgame_bucket,判前 off 臂定钉
    #: 基线)与 G4 饿死守卫锚(cw_sim_checks.check_line_gate_starvation_
    #: anchor:gate_hold 连续 ≥3 帧局占比零容忍)。排期 = W638 修复 A/B
    #: 批(三窗合计 330/臂 ≥ n≥300/臂口径)。
    #: **W683→v3 改道终态**:v2 §3-3 的 N=2 计数回锁被推翻(周期-3
    #: 极限环 + G4 锚自盲)已废弃,饿死纠错改门感知滞回闩(§3-3 R-A:
    #: 首次拦截置闩+一次性回锁恢复原锁层+闩内存续抑制出口①②;机制
    #: 载体=cw_intention 门闩分支 + session.v3_line_gate_latch)。门辖域
    #: 收窄 **plane==2**(R-G/FM-12:P2 损血表不辖 P3;P3 扩辖待
    #: p3_cond_loss_table 标定);survival_gate 对 E=inf 改拦 'alt_inf'
    #(R-E/FM-13:拦截归属唯一化,「上游已拦」假前提勘误)。G4 三判据
    #: 与中盘分桶两桶语义见 cw_sim_checks 两锚函数。禁无限挂起:不过 →
    #: 删码留 ADR(生命周期第 4 态);开臂翻默认时必须重推「断言
    #: gate_off 放行」的既有锁组语义(生命周期第 3 态义务)。
    line_switch_survival_gate_enabled: bool = False
    #: C4 两态口径总开关(rounds_alive 逐节点投影的 p_win 通道):
    #: False=现行为逐位一致(零漂移锚)——p_win_p2_by_rung 即使已注入
    #: 也不消费,投影按损血表条件常数走(M1a);True 时两态口径生效
    #: (M1b:loss=(1−p_win)·表值,rung 取样坐标见 p_win_p2_by_rung
    #: 注释)。与 line_switch_survival_gate_enabled 正交:后者辖门
    #(是否验存活轮数),本开关辖投影口径(怎么算存活轮数)。
    #: **开臂 A/B 判据挂账(不执行)**:按 `w371_recal_attack/` M4 口径——姿态面为主
    #(P2 生存/濒死带时长/换线拦截率过程指标),n=300/臂(合计 600)
    #: 之前不允许率差当主判据;姿态面过才翻 True。
    #: **验证排期挂账(退役批(ADR-0466/0467/0469) 补 deadline)**:排进sim A/B 批 sim A/B 批,与
    #: line_switch_survival_gate_enabled 同臂组(2×2 正交或分臂,由sim A/B 批
    #: 任务书定);姿态面不过 → 删码留 ADR。
    rounds_two_state_enabled: bool = False
    #: C4 兑现余量(轮;新线成型后仍需一轮兑现战斗,取 1=设计内保守下界)。
    #: 兼承载投影的近似残差(逐节点确定性投影 vs 真分布 E[min(t:ΣL>hp)]
    #: 的 Jensen 乐观差,REDESIGN §3.5 偏差表首行)。
    line_switch_survival_margin: float = 1.0
    #: C4 两态口径 p_win 表(成型度 rung(0-2 钳制)→P2 战斗条件胜率;
    #: 消费侧缺档=p_win=0=每战全损,loss=表值条件常数,两态退化 M1a;
    #: 消费开关=rounds_two_state_enabled,默认关=零漂移)。
    #: 值出处=`w346_gate_validation/` 门验证批分 rung 胜占比实测(冻结池 Δ池臂,
    #: 战斗 d>0 样本占比):k0=15/936=0.016,k1=879/2129=0.413,
    #: k2+k3 钳制并入=864/1316=0.657(生产 rung 0-2 钳制,k3 桶折叠)。
    #: 口径勘误:`w393_family_attack2/`/`w412_w370_debts/` 引文称「coarse 臂 0.34→0.65 单调」,原始
    #: 数据核对 coarse 臂实为 0.8%/35.6%/31.9%(非单调、无 0.65),
    #: 单调序列只在 Δ池臂——两态模型前提「p 对成型度单调不减」
    #(REDESIGN §5 条 1)辖下取 Δ池档,本注释为准。
    #: rung 取样坐标单一源=cw_battle_calib._settle_rung(与表坐标同源,ADR-0279
    #: 采样键;board 全集+星徽,deployed 域,0-4 钳到 0-2)——不用
    #: scoring._engines_formed(混合域加权,bench×0.35 推高 rung,
    #: 坐标错位=p_win 偏乐观=损血低估=门偏松)。
    #: 证据等级=sim 档(单档 n≈900-2100,无实机 P2 分 rung 样本;
    #: 方向声明=低档 p_win 低估损血高估、存活轮数偏短、门偏紧)。
    p_win_p2_by_rung: dict[int, float] = field(default_factory=lambda: {
        0: 0.016, 1: 0.413, 2: 0.657})
    #: C4 遭遇节点回血期望(hp;投影对每 encounter 节点加回)。默认 0=
    #: 0 下界(回血量未标定,禁拍死值;P2 生存实探局 hp=1 后有回血后继
    #: 观测实证(`w350_p2_survival/` REPORT §1),取 0=低估存活=门偏紧的保守方向);
    #: 值=该报告后继观测回血量标定后注入。
    encounter_heal_est: float = 0.0
    #: C4 boss 档不确定性附加费(轮;投影路径含 boss 节点时 need 加此
    #: 半宽——借档的不确定性由被比较量显式承担,REDESIGN §4.3)。值=
    #: 标定产出 |28.24−26.71|(P1 two_state 拟合与借档常数的源距,
    #: 双源标定台账 boss_bucket_injection,记录=ADR-0440),非魔数。
    line_switch_boss_ci_halfwidth: float = 1.53

    # ===== R3 撤销出口①意图证据(治 `w386_gate_energize/` BP1「门放行噪声换线」;
    # 设计决策=ADR-0436;消费点=cw_intention.core_miss_n_required / _revoke_alt_evidence)=====
    #: 证据组 A:「核心实际可达但连续 N_req 轮未现」的容忍概率 ε。
    #: 闭式 N_req(core,level)=⌈ln ε/ln(1−q)⌉,q=1−(1−r)^5,
    #: r=refresh_prob(level,cost)/DISTINCT_CARDS_PER_COST[cost](再遇
    #: 窗口既有构件;推导 P(N 轮未现|单轮出现率 q)=(1−q)^N≤ε)。
    #: ε=5%=「可达却连续缺席」压到二十分之一以下才构成断供证据。
    #: 实表代入(cw_shop_odds):3 费@lv5 q=0.069→N_req=42,3 费@lv7
    #: q=0.135→21,1 费@lv5→27——拍死值 CORE_MISS_N=6 的 6 轮缺席在
    #: q≈0.07 下自然概率≈0.65,纯属噪声,定量坐实 `w386_gate_energize/` BP1「阈值降
    #: 到可达值后先到达的是出口本身」。ε 的 sim 扫描 {1%,5%,10%} 挂
    #: L2 注入臂(出口①触发率 × 误开窗占比权衡,设计 R3.5),5% 为
    #: 设计默认档。
    revoke_miss_tolerance_eps: float = 0.05
    #: 证据组 B:异线资产厚度下限 A_min(浮点;厚度口径=_asset_thickness:
    #: 终局件星级当量+骨架件×SKELETON_ASSET_WEIGHT)。
    #: 测量协议(冻结池随机厚度基线曲线 f0(a) 的 5% 点,非拍值):池=
    #: w250_delta_pool/snapshot_v11,100 局 planes=2,分母=逐策略决策
    #: 帧(P2+ 段 1341 帧),统计量=「任一异线(除当轮锁定线)厚度 ≥ a」
    #: 的无条件频率;取最小整数 a 使 f0(a)≤5%。实测:f0(4)=7.68%>5%,
    #: f0(5)=1.27%≤5% → A_min=5。对照曲线(任一 v2 线含锁定线/全帧
    #: 口径:f0(4)=3.68%→A_min=4)与逐帧明细的测量记录=ADR-0436
    #: (主口径取消费面一致的「异线 × P2+ 帧」)。
    #: **分辨力弱声明(设计 R3.1 预案)**:5% 点落在 ≥4 带=证据在本
    #: 牌池分辨力弱的形态,设计预案=如实降级回炉(证据组 A 单独撑或
    #: 换证据形态)——回炉裁决挂 L2 注入臂误开窗占比判据(开窗局新线
    #: 成型 ≥2/3),数据未出前本值按测量结果服役,不调参硬凑。
    revoke_evidence_min_thickness: float = 5.0

    # ===== C1 溢余必花定向优先级(P1 末窗投影安全带;FLIP 正交补集)=====
    #: 设计决策=ADR-0443(期望账 §谱系与破息分支否决记录)。辖域裁决=与 FLIP 末窗投影臂
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
    #: **破息分支:概念定谳否决,永不实现(ADR-0443;开关生命周期第 4
    #: 态定谳注记——分支从未落码,无代码路径/无锁可删,本注释段即清理
    #: 物)**:破息花 X 金的过账判据要求胜率传导率 k > R̄/133.5
    #: (13.35 = E[损血|boss 败] 26.7 × hp_to_gold 0.5 的金当量系数;
    #: 息损 = Δfloor(g/10) × R̄)。E[R̄] 义务已从语料 runs.jsonl 离线
    #: 标定兑现(标定与对比表证据链=ADR-0443):全部档内破息事件均值
    #: 2.26 金(95% CI [1.42, 3.22],n=73),刷新密集口径(本分支真实
    #: 使用形态)条件均值 6.88 金(n=24)——门槛 k* ∈ [0.011, 0.052]/金;
    #: 可证传导链乐观上界(P17 +8 hp 链)k ≤ 0.012/金,全口径不过账
    #: (条件口径差 4.3 倍),期望收益为负或至多在乐观界处打平。
    #: 本开关辖域只含溢余段定向收窄主通道(已落码,默认关零漂移,
    #: 成本侧账独立成立),其开臂由两臂 A/B「基线 vs C1 本体」对照独立
    #: 裁决(判据=出口 hp 与 boss 胜率不降+删因逐笔可复算,事前预写见
    #: ADR-0443 Decision 3),不因破息否决受波及。
    #: **验证排期挂账(退役批(ADR-0466/0467/0469) 补 deadline)**:排进sim A/B 批 sim A/B 批;
    #: 不过 → 删码留 ADR-0443。
    c1_directed_spend_enabled: bool = False

    # (位面 2 支出授权 p2_spend_auth 全机制已随定谳清理删除,ADR-0492:
    # 四轮 A/B(W762/W772/W779/W785)M0b 四口径穷尽 0-4.1%,授权窗内
    # 花费结构性死路;W801 判根因=授权/方向类杠杆与档位累积型目标变量
    # 类型错配。窗前预转换思想由 W795/W803 P29/档位积分/D2 入口转化继承。

    # ===== 锁线后兑现链 v2(W802 实施批;设计单一源=
    # ===== .debug/temp/currency_war/w795_realization_design/REPORT.md v2/v3
    # ===== + 同目录 PREREG_兑现链A_B.md v3)=====
    #: 伞开关+七子旗标,生命周期第 1 态:默认关+零漂移锚(策略开关的
    #: 生命周期,唯一合法理由=行为输入未就绪:κ/γ/β/Δp_tier/R_min/时点
    #: 项权重全部占位值,不做生产决策)。**开臂判据挂账 = PREREG
    #: 兑现链A_B v3 主判据 M1-M4 + 机制判 G1-G7**(n≥500/臂+池指纹);
    #: A/B 数据齐即跑,不过则删码留 ADR(第 4 态),禁悬置默认关。
    #: 开臂翻默认时必须盘点「断言开关关闭行为」的锁组语义(第 3 态义务,
    #: test_cw_realization_chain 每锁带 off 臂零漂移断言)。
    #: 伞开关=True 且对应子旗标=True 才接线该侧机制;观测硬依赖
    #(board_next_tier/bench_full_flag/ADR-0474 遥测键)归 W793 后继批,
    #: 阻塞标定批清偿、不阻塞开臂(W796 复核 N2 措辞)。
    realization_chain_enabled: bool = False
    #: 搜牌侧:缺件感知定向刷新(设计侧一;修断点①-b)——锁定帧缺件
    #: 清单驱动刷新评分加项 Δp_tier·P(本刷出缺件);金水位辖域门
    #(花完仍≥息线,P5 自洽)+ 有效域=3-4 费缺件;低费死支不落
    #(等级只升不降,W796 面 2)。
    realization_search_enabled: bool = False
    #: 买入侧(设计侧二;修断点②-a/②-b):off-lock 罚分常数改机会成本
    #: 比例折扣制(val>0 部分乘 (1−κ);κ 占位)+ P29 羁绊感知囤牌
    #: 优先级(hp≥报警线 ∨ R_rest≥R_min 事前辖域门,含反向锁;bench
    #: 挤占用≥容量−1 禁囤定性门)。
    realization_buy_enabled: bool = False
    #: 合成时点侧(设计侧三;修断点③-a 重述):merge 候选排序加「合成
    #: 时点价值」项(非新豁免——ADR-0437/0438 豁免通道现行默认开不动,
    #: 防双计声明继续辖);档位未满守卫与星级守卫(合成产物与 deployed
    #: 同名不可上场 → 零时点价值)与搜牌缺件判据同一单一源;时点项
    #: 权重占位,**开臂前置=V(1★→2★) 条件 Δp 标定批**(PREREG 锁 #1:
    #: 标定前不把未证不等式钉进排序锁)。
    realization_merge_timing_enabled: bool = False
    #: 上阵/部署侧(设计侧四 ④-a;修断点③-c/④-a):锁定线 2★ bench 件
    #: cap 未满时部署候选必含(部署显影;cap 满走既有 SwapDeploy 臂
    #: 不新造)。
    realization_deploy_enabled: bool = False
    #: 方向侧(设计侧四 ④-b;修断点④-b):γ 衰减供给感知支持度
    #: support′ = γ^t·support + β·[成员在店],t=连续零在店轮数;γ 量级带
    #: [0.7,0.8] 经验锚(sim 扫描标定挂账,非「断供 5 轮等效」推导);
    #: 切换滞回复用 P16(δ=line_switch_theta 单一源)。G6 该翻不翻/
    #: G7 息基保住为开臂机制判(PREREG v3 §3)。
    realization_direction_enabled: bool = False
    #: D1 腾席选件弱序(W797 并入;修 ADR-0327 选件序输入反):腾席 sell
    #: 统一弱序键补 income(卖出回金+装备残值代理)升序分量——席满
    #: 腾席取最弱价值件,局 6 p2r7 卖高价值件留 1★ 散件反向消失。
    realization_d1_enabled: bool = False
    #: D2 跨位面入口帧转化授权(W797 并入;辖域协调:窗口判定归本设计、
    #: 分配账式复用 ADR-0474 死亡窗分配器(不造第二分配器)、报警源
    #: 消费既有应急带同一状态源):入口帧(round==1)hp 落死亡带 ∧
    #: 携金>息线 → 并入分配器 DEATH 域辖域,一次性转化授权由分配器
    #: 出清产生。
    realization_d2_enabled: bool = False
    #: —— 占位参数组(**占位值,不做生产决策**——伞开关默认关;全部
    #: 开臂前 sim 扫描标定,PREREG §6 挂账;出处=设计 REPORT v2 §2
    #: 如实占位纪律)——
    #: off-lock 比例折扣系数 κ。P11 下界/P12 拒绝域推不出点估计
    #: (v1「由 P11/P12 推出」表述已撤回);兑现链标定批 sim 扫描
    #: κ∈[0.5,0.85] 弹性平坦(线外买入占比/金纪律指标无位移——比例
    #: 折扣不变号,只改排序不改可买性,线外占比缺口是尾金 1 费件
    #: 的结构性余量非 κ 可达),维持 0.5;W789 Q1 反事实只约束
    #: 「降级非禁绝」(典型线外件 0.742 分折扣后仍正可买,成立)。
    realization_off_lock_kappa: float = 0.5
    #: Δp_tier 档位进度单位值(每完成一次档位步的价值,分/轮口径)。
    #: 推导:P3 羁绊期望表 e0→e1/e1→e2 ≈1.4-1.6 金/轮 × 锁定后剩余
    #: 战斗轮中位 8(sim 500 局) ≈ 全档位步 12 金当量;按候选单件
    #: 「金→分」比率 ~0.65(1-2 费件 0.5-0.8 分)折算 Δp≈0.9±0.15。
    #: 标定批 sim 扫描 [0.75,2.0]:G3/G7 弹性平坦、G2/G4 金席压力
    #: 随 Δp 单调升,取推导带下限 0.75(sim 内 hp 侧传导不可测:
    #: 出口 hp 对档位推进数平坦,实机档位阶跃锚=8 份实机局档案的
    #: r7 遭遇/r9 boss 税阶跃 ~19 血/档)。
    realization_delta_p_tier: float = 0.75
    #: P29 辖域门 R_rest 下限。推导:低血分支(hp<报警线 40)的存活
    #: 视野=实机对局档案按 P2 进场 hp 分桶的剩余存活轮中位(hp 20-40
    #: → 5 轮;hp<20 → 2 轮,≥40 → 7 轮),囤牌收益(档位阶跃落在
    #: 遭遇/boss 帧)需 ≥5 场兑现窗——取 5(先验带 [3,5] 上端)。
    #: sim 内弹性平坦(锁定集中在 r1,门槛缔合帧 <0.2%;实机晚锁局
    #: 缔合更紧,弹性以实机判读为准)。
    realization_p29_r_min: int = 5
    #: 缺件定向刷新的有效费用域(3-4 费;p(lv7,3)=0.40 档,低费死支
    #: 已删除,W796 面 2)。
    realization_member_cost_band: frozenset[int] = frozenset({3, 4})
    #: 合成时点项权重单位。与 Δp_tier 同语义(同一档位步价值 × 持有
    #: 份数比 2/3 × 剩余轮),故同值=0.75;标定批合成事件数对 unit
    #: 无可分辨弹性(sim 合成时点延迟结构性恒 0,M2 归实机锚)。
    realization_merge_timing_unit: float = 0.75
    #: 方向衰减系数 γ。标定批 sim 扫描(80-300 局/点):原经验带
    #: [0.7,0.8] 内任 β 值方向摇摆(G3)均超 off 基线 +60% 量级——
    #: 摇摆形态 81% 为相邻轮 A↔B 振荡,是「衰减降」×「在店上跳」
    #: 的轮间拉锯;G3 门(不升)约束下 γ=0.95 回门。代价声明:零
    #: 供给超越时距 ln(Δsup)/ln(1/γ) 升至 ~21 轮 > 位面长,衰减项
    #: 位面内近惰性,供给重估主要由 β 在店项承载(P16 滞回防粘死,
    #: G6 实测不升)。
    realization_direction_gamma: float = 0.95
    #: 方向供给项系数 β(窗口 W 的 ρ 项权重)。标定批取 0.05:单轮
    #: 上跳幅度须低于滞回 θ(line_switch_theta=1.0)的有效分辨差——
    #: β≥0.2 时在店/不在店的轮间交替即产生越带振荡(G3 摇摆主源,
    #: 与 γ 无关的下界);β≤0.05 摇摆回 off 水位。
    realization_direction_beta: float = 0.05

    # ===== P1 档位推进目标函数(W803 实施批)=====
    #: 伞开关+三子旗标(gate/deadline/r6_budget,仅 A/B 归因必需),
    #: 生命周期第 1 态:默认关+零漂移锚。设计单一源 =
    #: .debug/temp/currency_war/w803_tier_push_design/REPORT.md v2;
    #: **开臂判据挂账 = 同目录 PREREG_tier_push_AB.md v2 主判据 M1-M3
    #: + 机制判 G0-G5**(n=1000/臂+池指纹+零漂移锚);A/B 数据齐即跑,
    #: 不过则删码留 ADR(第 4 态),禁悬置默认关。决策 why=ADR-0494。
    #: 占位参数组(W(r) 形状/V_tier 线分权/报警线/压库豁免上界)不做
    #: 生产决策,开臂前 sim 标定批消偿(设计 §6/§8 挂账)。
    p1_tier_push_enabled: bool = False
    #: 散装板硬门(设计 §3④;r4 起 max_bond_tier<2 帧拒纯散件买入,
    #: 豁免=缺口前进判据同一 dist 函数/压库 ≤2 费+每帧 ≤2 张)。
    p1_tier_push_gate_enabled: bool = False
    #: r7 死线权重 W(r)(设计 §3②;r1-r5 平缓/r6-r7 陡升/r8+ boss 残差
    #: 坍缩;关=恒 1.0 纯缺口差分,消融归因)。
    p1_tier_push_deadline_enabled: bool = False
    #: r6 建档轮预算承诺(设计 §3⑤;EV 门式授权+血线辖域门最小实现)。
    p1_tier_push_r6_budget_enabled: bool = False
    #: —— 占位参数组(全部开臂前 sim 扫描标定;出处=设计 REPORT v2
    #: §3①② 如实占位纪律)——
    #: W(r) r1-r5 平缓段权重(占位)。
    tier_push_w_early: float = 0.2
    #: W(r) r6-r7 陡升段权重(占位;掉血帧 71% 集中 r7+r9 的方向性非自由
    #: 参数,陡度标定挂账;r7 备战帧购买直接作用于 r7 遭遇战)。
    tier_push_w_r6: float = 1.0
    #: W(r) r8+ boss 残差坍缩权重(占位;坍缩到平缓段之下=PREREG v2
    #: §5 锁 #3 的 r3>r8 序,r7 帧后新增档位只经 r8-r9 购买窗、只对
    #: r9 boss 兑现)。
    tier_push_w_late: float = 0.1
    #: V_tier 仙舟线锚定值(+19 血当量,P32.2 boss 帧单帧下界;占位)。
    tier_push_v_anchor: float = 19.0
    #: V_tier 列车/DOT 线降权系数(占位 0.5;2 人档线增量小,设计 §1.2)。
    tier_push_v_train_dot_scale: float = 0.5
    #: V_tier 希儿系最低权系数(占位 0.25;伤害在希儿技能层,设计 §1.2)。
    tier_push_v_seele_scale: float = 0.25
    #: 散装门生效起始轮(r4;r1-r3 空窗期豁免,[31]①)。
    tier_push_gate_min_round: int = 4
    #: 压库豁免费用档硬上界([34] 费用档判据 ≤2 费)。
    tier_push_press_cost_max: int = 2
    #: 压库豁免每帧张数上限(设计 §3④ 收口)。
    tier_push_press_round_cap: int = 2

    # (件价值模型 Phase 1 八字段(piece_value_enabled/buy/keep/merge/
    #  w_activation/w_retention/bench_gate_enabled/bench_reserve_cap)已随
    #  整机制定谳删除,删码留档 ADR-0496/0497;W902 终裁=活性但零疗效。
    #  原「开臂判据挂账」随删码偿清,登记漂移不再存在。)

    # ===== P1→P2 接口机制五开关——定谳清理,删码留档(ADR-0487)=====
    #: 曾以 p1_iface_{lockline_v2,carry_equip,hardnode_prep,lossstreak_
    #: flow,blood_bands}_enabled 五开关 + swing_degrade_n/swing_loss_n/
    #: board_match_min 三阈值落码默认关(设计决策=ADR-0484;行为锁=
    #: test_cw_p1_iface 六锁,随清理删除)。定谳依据(开关生命周期
    #: 第 4 态,W793 重跑批):W790 首轮 A/B 因 sim 死输入触发面未开火
    #: 判「数据不足」;补齐带符号 streak/hp_trusted/duty 观测桩后重跑
    #: (同预注册协议零改动),触发面全面开火(①397 局锁定/②1169 义务
    #: 帧/③40 授权帧/④112 授权帧/⑤80 血带帧,R 族出手率 77-94%)后
    #: 主判据仍双败——M1 P2 存活轮中位差 0.0(p=0.23),M2 P1 失血
    #: +0.81(方向反向),anchor 异族窗同形态 → 确认无效,删码。
    #: **M3 质量维正信号单独记档**:锁定局锁错率 2.02%(397 局中 8 局
    #: 交叠=0),交叠达标率 97.98% ≥90% 线——「锁前板面一致性验证、锁错
    #: 不如不锁」的锁线语义在成规模样本上成立,该语义不随本批删除作废;
    #: 若未来重立项接口判据面,锁线 FALLBACK 质量门按此证据复活。
    #: 锁线主机制本身 = [23] 锚(cw_intention 信号驱动,ADR-0357 P1 配方
    #: 锁),不在本批辖域。复活条件 = 机制/策略演进使「plane==1 接口
    #: 预算/禁令判据」重新立项且带新标定,依据本 ADR 证据链重走生命周期。

    # ===== C1 资产臂(跨位面资产通道 V_asset)——定谳清理,删码留档 =====
    #: 曾以 c1_asset_channel_enabled(总开关)+c1_asset_m_min(0.5)/
    #: p_slot(0.5,待标定)/delta_unit(0.03,待标定·主缺口)/l2_loss
    #: (12.0,待标定)五字段落码默认关(设计决策与定谳链=ADR-0444;行为锁=test_cw_c1_directed_spend 资产臂节)。定谳依据
    #: (ADR-0444,开关生命周期第 4 态):开臂前置「触发面非零」实测为零
    #: ——sim 300 局 C1 辖域 445 帧上意向从不处于锁线态(session 无
    #: v3_intention 或 phase≠locked),m 表结构性无定义,通道构造性恒不
    #: 激活(三臂冒测逐位相同);p_slot/delta_unit/l2_loss 三个「待标定」
    #: 量在触发面为零下永无标定数据源(标定数据源=A/B 兑现账回填,通道
    #: 不点火即无账)。开关、四参与 filters 谓词(_c1_asset_tables/
    #: _c1_asset_m_eff)一并删除,本注记留档。复活条件=机制/策略演进使
    #: 「P1 末窗溢余段帧 ∧ 意向已锁线」交集复归非零且触发面测量复归
    #: 非零,方可重新立项。


    # ===== 形态达标三方向(设计决策=ADR-0432/0433/0434)=====
    #: 三开关共同背景:形态达标是双指标(息基×形态)中塌掉的一根——
    #: before 基线=形态达标率实机 10%/sim 两臂 0%,头号缺项=配方件 2★
    #: (ADR-0432 判据节)。A/B 统一主判据=形态达标率(口径=配方档≥5
    #: ∧ 场上一枚配方 2★ ∧ 上场≥5),同池同种子对照先核池指纹。

    #: —— 方向一:购买围栏硬排序(recipe_fence)——
    #: 语义:未成型期(P1 ∧ form_ok 为假,谓词=filters.recipe_fence_active)
    #: 同一轮买候选中存在配方件(scoring._cand_system_bonds 名集单一源)
    #: 时,删除全部非配方件(散件)买候选,删因 'recipe_fence_scatter'
    #: (filters 层2 第二遍后置步,成型停手/C1 之后——C1 先行;时窗正交
    #: 声明:C1 只辖 P1 末窗溢余段,本围栏辖 P1 全程未成型段,C1 未删的
    #: 候选再过本围栏,删因链日志分列记账)。存在性围栏非全禁散件:店为
    #: 空配方件时散件照旧走原评分链;只重排同一笔预算内「买谁」,不改
    #: 金账/息账(单一源仍在 arbiter)。
    #: 开臂判据挂账(不执行):sim 同池 A/B n≥300 形态达标率 >0 ∧ 息基
    #: 保住率不劣于基线臂 2pp(判据只收台账可测项);
    #: 验证不过的出口=删码留 ADR-0432。
    #: **验证排期挂账(退役批(ADR-0466/0467/0469) 补 deadline)**:排进sim A/B 批 sim A/B 批,且为本组
    #: **第一个跑**的开关(形态达标率是当期头号缺项,sim 0%/实机 10%);
    #: 不过 → 删码留 ADR-0432。
    recipe_fence_enabled: bool = False

    #: —— 同名牌集中度约束(已定谳清理,删码留档;决策 why=ADR-0437,
    #: 复测与定谳链=ADR-0438 验证节)=====
    #: 曾以 dup_concentration_enabled(默认关)落码:配方名(cw_line_defs
    #: .recipe_char_names 名集单一源)在 board∪bench 已持 ≥2 张同名 1★
    #: (差一张凑 3合1)且 survivors 存在该名买候选时,删除全部散件买
    #: 候选(filters 层2 第三遍后置步,配方围栏之后)。定谳依据:开臂
    #: 前置「散买挤掉第三张」已消失——非正分门 merge 完成豁免
    #: (registry.merge_completion_exempt,ADR-0438)开臂后第三张副本
    #: 由豁免通道直接买走(四臂 A/B:offer 买率 53.93%→92.67%),集中度
    #: 约束双开复测专项指标与单豁免臂逐位同,零独立行为面;谓词与开关
    #: 删除,ADR-0437 留完整证据链。

    #: —— 方向二:成型后过渡件不拆(form_break_sell_blocked)——
    #: 语义:[13] 停手线的卖/下场侧对称口径(ADR-0343 买侧停手 +
    #: ADR-0363/0373 演进/卖侧引擎守卫同纪律族的辖域缺口,非新守卫族):
    #: 成型停手激活帧(filters.formed_stop_active 单一源;承接门未达时
    #: formed_stop 为假,本守卫自动不辖)下,卖出/下场候选的事务净效果
    #: 使 form_ok(decision_v2.phase 单一源)翻假的,拒。覆盖两型缝隙:
    #: 配方档 5→4(冗余份=档位构成,ADR-0373「冗余件照旧」不辖的盲区)
    #: 与上场人数 5→4。挂点面与 ADR-0373 同构:discipline.sell_priority_
    #: key(carry_gate/两补偿器)+ candidates._sell_tag(三卖 tag 生成
    #: 过滤)+ arbiter 卖候选采纳点对 working 复检(同批聚合)。卖了不破
    #: form_ok 的件照旧可卖(腾位/换金通道不堵,[22] 净0 件最先卖的
    #: 既有弱序保留)。
    #: 开臂判据挂账(不执行):「中途达过 form_ok 而最终帧不满足」的
    #: 拆队局改前实机 9 局/sim 同口径 0——sim A/B 已证触发面为零(sim 与
    #: off 逐位一致:闸全在卖候选采纳,无「中途达 form_ok 后拆队」路径),
    #: sim 判据结构性永不满足,有效性归实机判读。开臂判据=实机成型局
    #: 拆队笔数 before-after(改后应为 0)∧ 拆队后 benign→mal 不增 ∧
    #: strict_mal 不升(ADR-0373 先例:卖侧守卫曾有 benign→mal 回归);
    #: 验证不过的出口=删码留 ADR-0433。
    #: **验证排期挂账(退役批(ADR-0466/0467/0469) 补 deadline)**:可验时点=实机回归战役
    #(蓝图 §8,前置=sim A/B 批 说服包通过);实机判读量(拆队笔数/形态迁移
    #: 分账)入 §8 武装序判读清单,防「开臂时无人记得量什么」。
    form_break_sell_blocked_enabled: bool = False

    #: —— 方向三:花的时机判据(below_floor_spend_gate)——
    #: 语义:金 < interest_floor 时升级/刷新默认拒(删因
    #: 'below_floor_spend'),仅三条例外放行(白名单非加分):
    #: E1=[33] 人口位(ev.levelup_ev_basis 臂①原样收编,零改语义)/
    #: E2=[6] 精确化=店内有配方围栏名集件(与方向一共用 scoring.
    #: _cand_system_bonds 名集尺,不造第二把)→ 刷新放行,上限 1 次/轮
    #: (定向刷新语义,session.v3_bf_refresh_* 轮内计数)/ E3=[11] 零息
    #: 损显式化(⌊gold/10⌋ 不变的花/刷在息账上零成本,放行防误拦)。
    #: 落点:升级=levelup_ev_basis 前置门(花后 < interest_floor 时仅
    #: E1/E3 可达——② DP 臂本就要求平台未破不动;③ 静态 EV 账在 boss
    #: 前冲级语境放行过负期望破息花,`w410_p1_process_quality/` 实证 r9 破息笔中位 32 金换
    #: 2 档息损,胜率传导上界 0.12 < 过账所需 0.30);刷新=arbiter
    #: gold_floor HOARD 分支收窄(interest_rule 在金<50 时让位 gold_floor,
    #: 该分支才是息线下刷新的实际裁决点);gate 开时 dp_spend 不再单独
    #: 授权息线下刷新(三例外白名单收窄)。金账单一源不变,本门是授权
    #: 边界不是新账。
    #: 开臂判据挂账(不执行):改前 sim 真破息率 w42 26.3%/w43 5.5%,sim A/B
    #: 已证触发面为零(sim 与 off 逐位一致——被 never_50 高占比低金语境
    #: 架空,sim 判据结构性永不满足),有效性归实机判读。开臂判据=实机
    #: r9 破息升级笔息损分账 before-after(改后破息笔归零)∧ never_50
    #: ≤基线+2pp ∧ 形态达标不降;验证不过的出口=删码留 ADR-0434。
    #: **验证排期挂账(退役批(ADR-0466/0467/0469) 补 deadline)**:可验时点=实机回归战役
    #(蓝图 §8,前置=sim A/B 批 说服包通过);判读量(r9 破息分账,改前基线
    #: w42 26.3%/w43 5.5%)入 §8 武装序判读清单。
    below_floor_spend_gate_enabled: bool = False

    # ===== 支出门·买侧收门(W829 v3 设计落码;伞+两子旗标默认关 =
    # 生命周期第 1 态零漂移锚;三轮 A/B 终局定性见 ADR-0499)=====
    #: 设计单一源 = docs/develop/currency_war/prereg/w829_spend_gate_design/
    #: REPORT.md v3(§1.4 判据/§3 落码规格/§4 辖界切分;判前锁
    #: PREREG_v4/v4.1 同目录);终局决策记录 = ADR-0499。机制落点 =
    #: decision_v2.spend_gate(arbiter 约束链新增一节,拒因枚举
    #: d1_interest/d2_blood/d3_bench)。
    #: D1 息线臂 = 真破息(花后 < 息线 ∧ ⌊g/10⌋ 下降)拒,豁免
    #: E-a 合成完备 / E-b 锁定线缺档成员∧hp>应急线(内联判据,不引
    #: P29 项)/ E-c 人口位(门不辖升级);D2 血线臂不设旗标(消费
    #: 既有血线常量单一源,零新参数零新状态源,随伞);D3 位置臂 =
    #: bench 占用 ≥ 容量−1 拒非合成非当轮可部署,挤占判据单一实现
    #: (= P29 消费同一函数)。
    #: 开臂判据(已执行,ADR-0499):PREREG_v4 三臂判前锁三轮 A/B
    #: (W840/W848)定谳 = 清账门绿 ∧ 传导格三度双败 → 维持关保留
    #(语义按清账已证+传导归实机锚,禁第四态删码——W851 旧注释
    #: 「不过走第 4 态」措辞已废)。恢复开臂前置=实机锚量化判据
    #: (未定,见 ADR-0499 遗留挂账)。
    spend_gate_enabled: bool = False
    #: D1 息线臂子旗标(G7 归因消融用)
    spend_gate_interest_enabled: bool = False
    #: D3 位置臂子旗标(G4 归因消融用)
    spend_gate_bench_enabled: bool = False

    # ===== DirectorV2 备战循环(`w606_stage2_batch3/` 阶段2批③落件;`w620_migration_b1/` 迁移迁移批 1(守卫分区)(守卫分区)升正)=====
    #: `w620_migration_b1/` 迁移迁移批 1(守卫分区)(守卫分区)(蓝图 §7 迁移迁移批 1(守卫分区)(守卫分区) 行):DirectorV2 接线升正,新环 = 唯一生产
    #: 路径——无开关 directive(蓝图 §8),``director_v2_prep_enabled`` 随
    #: 接线完成删除(存在理由消失);回退 = git revert。
    #: 影子比对开关(纯诊断工具,sim/离线对拍用;不改任何游戏动作):
    #: True 时旧环每步 decide 后同帧跑适配器影子决策并逐位对照(异常全
    #: 隔离计数留证)。采集完成即回 False;旧环随迁移迁移批 3(ADR-0465)(ADR-0465) 退役时生产分支一并删。
    director_v2_shadow_compare: bool = False

    # ===== 层4:预算仲裁(约束清单——一处定义,全部候选受辖)=====
    #: 执行约束名序(仲裁器按序施加;filters/arbiter 按名映射实现)
    constraints: tuple[str, ...] = (
        'gold_floor',          # 金≥地板(地板按覆盖态分派)
        'interest_rule',       # [11][17][28] 息档保持/满息结余
        'bench_capacity',      # bench 9 槽(含本轮已采纳买)
        'copies_cap',          # 同名星级加权 ≤3 份
        'same_round_mutex',    # 同轮已买禁卖/已卖禁买(r408 族)
        'blood_budget_stop',   # 血预算停手·停升级门(设计件 12;ADR-0448
                               # ——授权通道前置拒付,与息线门独立谓词 AND)
        'boss_levelup_ban',    # 升级 EV 总账门(名字历史遗留;迁移审计 w255(git 历史)/ADR-0410
                               # 起 boss 禁令臂已删,[32] 节点无关)
        'deploy_cap',          # 上阵数 ≤ max_units
        # ('p1_iface_gate' 已随五开关定谳清理删除,ADR-0487)
        'spend_gate',          # 支出门·买侧收门(W829;伞默认关=零漂移。
                               # 置于链尾:既有守卫先到先记,守卫已拒的
                               # 候选门不求值不产生门拒因;d3_bench 只记
                               # 「未满栏但前瞻挤占」)
        # ('pv_bench_reserve' 已随件价值整机制删除,ADR-0497;
        #  spend_gate 恢复链尾。)
    )
    #: 地板表(金≥地板;覆盖态分派——审计表 gold 行的消费值)
    #: interest_floor 字段已删(D3 双源清偿,`w628_migration_b2/`):息线单一源 =
    #: ``interest_floor()`` 派生(interest_cap × 10,ADR-0463 恒等式),
    #: 纪律视图的 ALL IN 清零改走 ``interest_floor_override`` 注入通道。
    war_floor: int = 30           # 战力模式地板(计划内补强非 panic)
    rebirth_floor: int = 20       # [18] 应急保留重生基数
    boss_floor: int = 10          # r278 boss 破息地板
    #: 息线覆盖通道(纪律视图专用,非标定旋钮):None=用派生息线;
    #: ALL IN 窗 = 0(唯一清零路径,discipline 裁决视图注入)。
    #: A/B 常量注入面只留 interest_cap 一个旋钮(D3 验收判据)。
    interest_floor_override: int | None = None
    #: (levelup_interest_engine_gate 已随 迁移审计 w119(git 历史) 删除:[12] 门收编 EV 总账
    #:  ——ev.levelup_ev_authorized 单一裁决,ADR-0347;A1/A2 镜像清)
    #: (refresh_game_cap/levelup_reserve_gold 已随 `w126_b_arm/`/ADR-0349 删除:
    #: refresh_budget 约束整体退场,D 的预算由 V_D 批口径评分+
    #: gold_floor/interest_rule 辖)
    #: boss 轮判定(node_type='boss';P1 r9 兜底同辖)。迁移审计 w255(git 历史)/ADR-0410:
    #: 消费面只剩 boss 窗地板/覆盖态语境(b 类保留),升级特殊禁令已删。
    boss_round_node_types: frozenset[str] = frozenset({'boss'})
    #: LevelUp 等级上限(封顶 10)
    level_max: int = 10
    #: bench 槽容量(游戏常数 9)
    bench_capacity: int = 9

    # ===== `w607_affix_consumption/` 词缀消费面三开关(`w628_migration_b2/` 清偿)=====
    # 设计单一源=设计件「词缀消费面」(.debug/temp/currency_war/w607_affix_consumption/DESIGN.md
    # §3);词条语义出处见 cw_comps.STRONG_ENV_MECHS / RUST_AFFIX_NAME 注释。
    # 清偿记录(H1 已物理删字段;H2②/H3 行为无条件化、字段物理删除随迁移迁移批 3(ADR-0465)(ADR-0465)
    # ——读端在 operations/prep/equip_all.py,该文件迁移迁移批 3(ADR-0465)(ADR-0465) 在飞故本批禁碰,
    # 显式战术权衡,证据归 w628_migration_b2/STATUS):
    #: (H1 line_env_gate_enabled 已删:行为无条件化,cw_intention 锁线信号
    #: 过滤恒在;sim A/B 与单帧锁证据见 w607_affix_consumption/AB_REPORT.md)
    #: H1 环境判据的最小生效轮(位面内轮次,1-based;防位面切换首帧词缀窗口
    #: 误判的观察期)。简报词缀在位面切换即读得(battle_loop 位面简报分支),
    #: 无窗口误判实证,默认 1=判据全程在辖;如实机判读发现位面首帧词缀滞后,
    #: 经判读锚点标定后上调(标定通道,非拍死值)。
    line_env_lock_min_round: int = 1
    #: H2②:库藏生锈在场(cw_comps.RUST_AFFIX_NAME ∈ enemy_affixes)时豁免
    #: opening/过渡 hold——每件 owned 滞留=敌 +3%伤/-4%减伤(competitors.md:45),
    #: 滞留的边际代价随件数单调上升,压倒「攒给成型核心」的机会成本。
    #: 行为无条件化(恒 True);单帧锁已闭环、实机锚点预注册
    #: (w607_affix_consumption/AB_REPORT.md 开臂建议节)。
    rust_wear_release_enabled: bool = True
    #: H3:opening hold(P1 r≤2)收窄——仅「当前节点非战斗类」才 hold
    #: (node_type ∈ opening_hold_battle_nodes → 不 hold;r2 战斗节点白板挨打
    #: 病灶,局22 实证)。node_type 缺失(None)维持现状 hold(保守降级:观察
    #: 缺失不改变既有行为,宁缺勿错)。行为无条件化(恒 True),依据同上。
    opening_hold_battle_gate_enabled: bool = True
    #: H3 战斗类节点型名单(词汇表单一源=GameState.node_type 顶部标签 OCR:
    #: boss/补给/遭遇/巨星/投资/战斗/精英/奖励)。巨星/投资等未知是否战斗
    #: →不入集=维持 hold(保守侧,不猜)。
    opening_hold_battle_nodes: frozenset[str] = frozenset(
        {'战斗', 'boss', '遭遇', '精英'})
    #: H2① 数据层(ADR-0461 增补节):库藏生锈每件滞留的敌方增益份额与
    #: 计件上限,语义出处=competitors.md:45(敌伤 +3%/敌减伤 −4%,最多
    #: 10 件,2026-08-28 游戏内实采)。**只承载账面单一源,无行为分支**——
    #: 第二波数学裁决(证明锁 test_cw_w607_h2o_verdict):每件滞留金当量
    #: = 本份额 × expected_battle_loss × battles_left_est × hp_to_gold
    #: = 0.75(保守=只建模敌伤面,−4% 减伤面不映射=不猜),封顶 7.5
    #: < 补给 key_fit 边际 10、< 策划面装备类与升费/弱化的分差 19 →
    #: 现有动作空间无翻转点,H2① 行为分支不合入(无效→不合入,
    #: strategy-work §4 兑换纪律)。重评触发器=该证明锁翻红,或 `w612_effect_inventory/`
    #: 效果清单批落地装备处置/inventory 动作面(届时扣减消费点挂其接口)。
    rust_hoard_damage_share: float = 0.03
    rust_hoard_penalty_cap: int = 10

    # ===== 变宝为废·牺牲合成先行(机制真值单一源 =
    # data/affix_effects_data.AFFIX_EFFECTS['变宝为废']游戏内原文实采:
    # 「每个位面开始时,首次合成的进阶装备会有50%的概率变成垃圾袋」
    # ——粒度=每位面各一次,概率=50%,产物=垃圾袋;排序器 =
    # kernel/cw_junk_first.py)=====
    #: 策略开关生命周期第 1 态(默认关+零漂移锚:关=equip_allocation 基分配
    #: 原样,经 junk_first_allocation 包装,执行链零改动)。
    #: **开臂判据(挂账,双钥匙,由本批拍定阈值;机制数据已在库,不缺)**:
    #: ① 环境读取通道稳定——实机 ≥2 局含「变宝为废」词缀的局,
    #:   state.enemy_affixes 均读到该词缀(简报/位面详情横条通道零漏采);
    #: ② 牺牲对识别可靠——实机 ≥2 次 cw_junk_first 决策日志中
    #:   sacrifice_first/deferred 动作与画面合成事件对得上,误判 0
    #:   (误判 = 牺牲对吞了主线组件,或该排未排)。
    #: 两钥匙齐 → A/B 判据后翻默认值。
    #: ⚠️ 禁独立开臂(联动评审约束):本旗标(执行侧防护)翻默认值前须与选型侧
    #: w878_synth_equip_dep_enabled 联动评审——同一机制(变宝为废)的两面,
    #: 防护已覆盖多少风险、选型侧 -0.25 是否过反应,须同批对照拍板,不得各自单独定。
    junk_first_sacrifice_enabled: bool = False

    # ===== 装备穿满族 fill-to-3(软弱无力+额外打击合并量变体;
    # 机制真值单一源 = data/affix_effects_data.AFFIX_EFFECTS 游戏内原文实采:
    # 「没有穿戴3件装备的角色及其忆灵,造成的伤害为原伤害的80%.」/
    # 「我方队员每有1个空缺装备栏,受到敌人攻击后,额外受到本次攻击伤害8%的
    # 真实伤害。」——排序器后处理 = kernel/cw_equip_env.py)=====
    #: 策略开关生命周期第 1 态(默认关+零漂移锚:关=equip_allocation 基分配
    #: 原样,fill 变体 inactive,执行链零改动)。
    #: **开臂判据(挂账,设计件 .debug/temp/currency_war/w880_equip_env_design/
    #: DESIGN.md §4.1)**:① 环境通道:实机 ≥2 局含软弱无力/额外打击零漏采
    #: (state.enemy_affixes 命中,同 junk_first 判据①);② 行为对:fill 改派
    #: 日志与画面穿戴事件对得上、误挪 key/主线凑件 0 次;③ sim A/B(同池配对)
    #: 穿戴覆盖率/损血正向 → 翻默认值 + 同步改写行为锁组(第 3 态义务)。
    #: 验证不过 → 第 4 态清理(删码留 ADR),不悬置。
    equip_env_fill3_enabled: bool = False
    #: 穿满阈值 = 机制常量(真值「穿戴3件装备」的 3;非拍死值,版本变更时改此)。
    equip_fill_target: int = 3

    # ===== 完备性审计表(ADR-0290 对抗修订④)=====
    #: 资源维 × 回合态维矩阵;每格 = constraints 内的约束名,或
    #: ('none', 显式声明原因)。「无约束覆盖」必须显式声明,禁止空格。
    #: 检查项 decision_v2_arbiter_matrix 锁「无空格 + 约束名存在」。
    audit_matrix: dict[tuple[str, str], tuple[str, ...] | tuple[str, str]] = field(
        default_factory=lambda: {
            # (资源维, 回合态维) → (约束名...) 或 ('none', 原因)
            # ('catchup' 列已随 `w126_b_arm/`/ADR-0349 追赶态退场改为 'mode' 常态列)
            ('gold', 'boss'): ('gold_floor', 'interest_rule'),
            # (gold/boss 与 bench/boss 格不含 spend_gate:支出门在 boss
            # 窗让位,W774⑤ 同仲裁语义;p1_iface_gate 已随定谳清理删除,
            # ADR-0487;pv_bench_reserve 已随件价值整机制删除,ADR-0497)
            ('gold', 'emergency'): ('gold_floor', 'spend_gate'),
            ('gold', 'mode'): ('gold_floor', 'interest_rule', 'spend_gate'),
            ('bench', 'boss'): ('bench_capacity',),
            ('bench', 'emergency'): ('bench_capacity', 'spend_gate'),
            ('bench', 'mode'): ('bench_capacity', 'spend_gate'),
            # 血预算停手门只辖升级(全回合态生效——emergency 态内同样
            # 拒,设计件 12 §5.3「不是第五种覆盖态」;ADR-0448)
            ('slot', 'boss'): ('blood_budget_stop', 'boss_levelup_ban'),
            ('slot', 'emergency'): ('blood_budget_stop', 'bench_capacity'),
            ('slot', 'mode'): ('blood_budget_stop', 'deploy_cap'),
            ('round_mutex', 'boss'): ('same_round_mutex',),
            ('round_mutex', 'emergency'): ('same_round_mutex',),
            ('round_mutex', 'mode'): ('same_round_mutex',),
        })
    #: 审计表两维的显式枚举(新增动作类型/资源维时审计表强制过检)
    audit_resource_dims: tuple[str, ...] = ('gold', 'bench', 'slot', 'round_mutex')
    audit_round_state_dims: tuple[str, ...] = ('boss', 'emergency', 'mode')

    # ===== W875 环境B类评分补全包 + 长线利好刷价参数(开关生命周期第 1 态:默认关)=====
    #: 生命周期第 1 态纪律(策略开关的唯一合法存在理由 = 行为输入未就绪):
    #: 关 = 基表/基价零漂移;开臂判据 = sim A/B(同池配对)目标指标正向后翻默认值,
    #: 同时改写断言旧默认行为的行为锁组(hash 锁之外的锁最易漏)。
    #: 评分补全包子旗标(逐条独立;死映射防线 = 每行准入前已核查该 tag 的
    #: counter 值域至少被 1 个 comp 的 mechanic_attributes 携带,W872 攻击口径):
    #: 能量逃逸(敌受击使攻击者能量 -4,机制原文 affix_effects_data「能量逃逸」)
    #: → tag 能量削弱,克连携高频开大(Saber 连携队,tag 有载体)。
    w875_energy_leak_enabled: bool = False
    #: 同步行动(我方行动提前时敌也提前 20%,机制原文 affix_effects_data「同步行动」)
    #: → tag 行动喂敌,克速度依赖/量子拉条(阿雅鞋队/希儿量子,tag 均有载体)。
    #: 「敌多动=DoT 多结算」半边不走本表(cw_system_cards affix_likes 通道已覆盖,防双计)。
    w875_sync_action_enabled: bool = False
    #: ===== W878 死 tag 复活 4 批子旗标(开关生命周期第 1 态:默认关)=====
    #: 复活 4 个零携带死 tag 的 comp 侧载体(裁决依据=死映射三问:概念存在×判据可判×
    #: 量级匹配 mechanics_fit ±0.25/±0.20 粒度;判型出处见 cw_comps.W878_GATED_TAGS 注记):
    #: - 单属性队:属性熄火 7 词条(风/火/冰/雷/物理/量子/虚数,敌我方该属性伤害 1 点×4 次)
    #:   克纯色主档队;载体=希儿量子(量子同频4 属性型羁绊主档)——量子熄火局防错选希儿线。
    #: - 成型羁绊队:形单影只(1/2/3 个未激活羁绊 → 伤害 85%/60%/30%)利羁绊全的板;
    #:   载体=羁绊驱动型 comp(战力来自羁绊档位乘区,装备流/单核族不打,逐套判型理由
    #:   见 cw_comps COMP_LIBRARY 标注注释)——全表最大量级词条(-70%)。
    #: - 慢速:冻结族 3 词条(极速制冷/坠入陷阱/冷冻冬眠)克拖久+耗点队;
    #:   载体=DOT 磨血族(叠层×引爆胜利条件,final_dot_kafka)。
    #: - 依赖合成装备:变宝为废(每位面首次进阶合成 50% 垃圾袋)克全预算砸核心装的流;
    #:   载体=白厄反甲族(装备即胜利条件,final_baie_reflect);合成侧已由 junk_first
    #:   排序器处理,本 tag 补选型侧(comp_score 在该词缀下给装备流降分),两半互补不重复。
    #: 开臂判据挂账(环境恢复后补验):①单帧锁组(test_cw_w878_deadtag_revive)全绿;
    #: ②含对应词缀的 sim/实机局样本 ≥10 局判读方向一致(样本量恢复后由编排者定谳,
    #: 当前无模拟/实机输入,悬置默认关);
    #: ③成型羁绊队开臂前须补验「判非 3 套(红A/万敌单C/反甲白厄)在形单影只局的
    #: 伤害档位方向」——判非理由「羁绊不满也有战力」与词条罚的「伤害倍率出口」不同维,
    #: 万敌单C方向存疑(死 tag 裁决攻击批形单影只角度)。
    #: ⚠️ 两旗标禁独立开臂:w878_synth_equip_dep_enabled(选型侧 -0.25 降分)与
    #: junk_first_sacrifice_enabled(执行侧牺牲合成防护)是同一机制的两面——选型惩罚叠
    #: 已有防护疑过反应,开臂须两侧联动评审(junk+tag 对照),构造期校验禁选型侧单独开
    #: (见本类 __post_init__)。junk_first 侧单独开合法(防护先行、选型侧观望)。
    w878_mono_attribute_enabled: bool = False
    w878_formed_bond_enabled: bool = False
    w878_slow_burn_enabled: bool = False
    w878_synth_equip_dep_enabled: bool = False
    #: 长线利好刷价参数(机制原文 cw_invest_data id=120:花费刷新 30 次后得 20 金,
    #: 之后本局刷新只需 1 金)。阈值/折后价单一源在本表,消费点 =
    #: cw_economy.refresh_cost_effective(刷新 EV 判据参数化接缝)。
    #: 开臂判据挂账:①局内累计付费刷新计数接线(refresh_count 由调用方注入,
    #: 现无此观测,缺省 0 → 折后价永不生效);②sim A/B 刷新/经济指标正向。
    longterm_refresh_discount_enabled: bool = False
    longterm_refresh_threshold: int = 30
    longterm_refresh_price: int = 1
    #: ===== 巨星强化角色决策维度(开关生命周期第 1 态:默认关)=====
    #: 开 = ``decide_megastar`` 在巨星候选(既有 buff 契合路径,不受影响)之外
    #: 追加输出「强化角色」意向(``MegastarPick.enhance_char_id``,绑定序 =
    #: ``cw_comps.select_megastar_enhance``:target.core_chars 前排 → core 后台
    #: → 首个前排 → None)。注意:本开关只启**决策层意向输出**(落 reason/遥测),
    #: **执行面(巨星 overlay step2 点强化角色)未接**——巨星 step2 强化角色
    #: 候选坐标未建档(伙伴 overlay 的中心立绘 (960,300) 只在伙伴屏实机验过,
    #: 巨星屏无对应 ground truth),且巨星语境下强化角色的机制效果无文档真值
    #: (docs/game/screens/currency_war_megastar.md:可选步骤,跳过不锁出战)。
    #: 开臂判据挂账:①巨星 step2 画面建档(候选面/选中态/坐标 ground truth);
    #: ②强化角色机制效果语义确认(改 run_megastar_node 接执行面前必须先做);
    #: ③执行面接通后 sim/实机 A/B 正向 → 翻默认值;验证不过 → 删码留 ADR。
    megastar_enhance_enabled: bool = False

    def __post_init__(self) -> None:
        """开臂约束构造期校验(策略开关生命周期纪律,非行为分支)。

        w878_synth_equip_dep_enabled 禁独立开臂:选型侧 -0.25 降分与执行侧
        junk_first 牺牲合成防护是同一机制(变宝为废)的两面,选型惩罚叠已有防护
        属未对照的过反应风险——须两侧联动评审后同开(出处 = 死 tag 裁决攻击批
        旗标交互角度)。junk_first 侧单独开合法(防护先行、选型侧观望)。
        """
        if self.w878_synth_equip_dep_enabled and not self.junk_first_sacrifice_enabled:
            raise ValueError(
                "w878_synth_equip_dep_enabled 禁独立开臂:须与 junk_first_sacrifice_enabled"
                "联动评审后同开(选型侧 -0.25 与执行侧防护为同一机制两面,禁未对照单独开臂)")

    def interest_floor(self) -> int:
        """息线单一源(D3 双源清偿,`w628_migration_b2/`):派生 = interest_cap × 10。

        - 恒等式出处 = ADR-0463/`w611_econ_cycle/` §2.2(满息平台 = 封顶档 × 10 金);
          原独立字段 ``interest_floor``(=50)与派生式并存构成双源,标定
          批动 interest_cap 时两源分歧——本方法收编为唯一取值口;
        - 覆盖通道 = ``interest_floor_override``(仅纪律视图 ALL IN 清零,
          非标定旋钮);
        - 消费守卫:除本方法与本类定义处外 ``interest_floor`` 读点 = 0
          (grep 锁 test_cw_w628_migration_b2)。
        """
        if self.interest_floor_override is not None:
            return self.interest_floor_override
        return self.interest_cap * 10


# ===== hp 对账层下行守卫标定常量(ADR-0431;消费方 cw_reconcile.reconcile_hp)=====
# 值单一源在注册表(项目惯例:数值不散落);cw_reconcile 属观察对账层,
# 只读本模块常量,不进决策评分面。
#: 单战损血谱 p100 上界,按节点型分档——loss 帧下行采信的幅度上界。
#: 标定来源 = 损血表 p100(887 行遥测语料,只采 hp_confidence≥1 且按
#: (run,位面,round) 去重后的分位:普通战斗 23 / 遭遇 42 / boss 39);
#: 取 p100 不取 p99 的论证见标定报告(p99-p100 差 ≤7%,p100 顶级行
#: 逐条交叉核验非误读,压阈值只引入真掉血误杀)。精英/巨星等未标定
#: 节点型不入表 → 下行走复现确认通道,不拍值。
HP_LOSS_CAP_P100_BY_NODE: dict[str, int] = {
    '普通战斗': 23, '遭遇': 42, 'boss': 39,
}
#: 零损节点型(无战斗损血机制事实):这些节点的结算不产生合法损血,
#: 真值帧下行必为误读 → 一律拒信。
HP_ZERO_LOSS_NODE_TYPES: frozenset[str] = frozenset({'奖励', '补给'})
#: 下行拒信复现确认帧数:拒信后连续 N 个真值帧读数仍与拒信值一致
#: → 确认真掉血,采新出窗。2 = 最小独立复现数(1 帧可能是同一遮挡
#: 形态的系统性误读;实机遮挡是 shop 开态特有,结算/备战帧不复现)。
HP_SUSPECT_CONFIRM_FRAMES: int = 2
#: 毒化窗长上界(节点数):每节点至少一个真值帧(shop 开态才是 None),
#: 窗长 ≤ 1 节点 + 确认期;超窗 suspect 过期,下次下行重新走首拒帧。
HP_SUSPECT_WINDOW_NODES: int = 2


#: 默认注册表(ADR-0293 标定后;A/B 时构造改动副本注入
#: DecisionV2Strategy)
DEFAULT_REGISTRY = DecisionV2Registry()
