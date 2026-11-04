"""决策框架 v2 注册表(对抗修订③:剪枝显式化/全注册表化)。

归属:core/kernel 层(分包期 0b 自 decision_v2/registry.py 整文件下沉)——
本文件零 sr_od 依赖、``DEFAULT_REGISTRY`` 纯常量实例、全仓无动态注册,
kernel 与 decision_v2 必须共享**同一** registry 实例(A/B 注入契约:同一
调用链全部接缝传同一实例),拆两段会造双实例破契约,故整文件移动。

评分表 / 剪枝 K / 标签优先与互斥 / 过滤链 / 约束清单 / 完备性审计表
全部集中在此,``DecisionV2Registry`` 可整体注入(A/B:两套注册表各跑
一分支,sim 配对对照)——**禁止隐式排序、禁止散落硬编码**。

数值口径(**已部分标定**,首轮标定:refresh 族/目标件
持有基线四参已按 20 局诊断+30 局配对验证标定;其余仍为骨架初值,
后续批次继续):
- 档位期望:P3 已证边际(e0→e1 +1.4 / e1→e2 +1.6 金/轮)→ 累计档值;
- 战力:星级阶梯已清退禁引(禁胜率建模裁定,P3 禁引);
- 息律:[17][28](50 金息律 / P1 满息通关)进 interest_rule 约束;
决策记录已停用删除(随ADR 档案)(git 历史可溯)。

⚠️ 收入口径修正登记的待办(sim 侧已实现):sim 败轮金 + 奖励轮
成对修正使 P1 出口金约 +6.6 金/局(无反馈静态重放量化)——凡以 sim
经济轨迹为输入的历史门结论(典型:粗模型 vs Δ池的 P2 进场率差恰在
门界、零余量的门 1a)在新口径下须 regate(修正口径重跑基线分支)后才能
引用;regate 与基线重新确认一并登记的待办待执行。
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
    #: 卖候选标签优先序(off_target 最先;free_bench=腾位让位)
    sell_tag_priority: tuple[str, ...] = (
        'off_target', 'for_gold', 'free_bench',
    )
    #: 部署候选 top-K(K 与排序键显式:排序键=围栏序 cw_deploy_logic
    #: .select_deployments 的点火首键+桶序——同一源,不另造排序)
    deploy_top_k: int = 3
    deploy_sort_key: str = 'cw_deploy_logic_fence'
    #: 卖候选上限(bench 每件都生成,但执行轮内采纳上限——防整板清仓)
    sell_top_k: int = 2
    #: 同名副本上限(按 (名,星) 分星计数:各星 ≤2 存续,同星第 3 份买入
    #: 即合成——14号稿 §3.5 B6 口径回写,消解「星级加权」含糊;计数函数
    #: 单一源 = 全局面同名同星副本数,2★ 成件计 1 份不折算 1★)
    copies_cap: int = 3
    #: copy_swap 守卫×目标件豁免开关(落地;旧裁决曾取
    #: 默认关=守卫直通无豁免——当时三窗小负且无主病灶前提;
    #: **开分支翻默认 True**:`w436_merge_exempt_ab/` A/B 在 ①豁免扩同批前提下,
    #: 本开关相对单开 ① 分支第三张 offer 买率 +9.15pp(CI [2.31,15.76]
    #: 显著)、形态达标率 +3.0pp(方向正不显著)、守卫全净(真跌破利息档/
    #: hp0/bench 溢出/出口金)——`w431_generation_starve/` 定位的 r410 守卫 lv7-8 无分支接
    #: 15 笔窄段(目标名精确命中分支①条件)在生成通道打通后兑现。
    #: False=回退守卫直通(代码留作回退通道)。
    copy_swap_target_exempt: bool = True
    #: 非正分门 merge 完成豁免开关(第三张副本买候选 3合1 完成素材语义,
    #: 决策 why 见行内申报):True=arbiter 非正分门对 merge=True 的买候选
    #: 放行进入约束链(豁免≠必买:金地板/copies_cap/bench 容量/息账
    #: 照常覆盖)。依据:第三张副本买入即合成 2★,收益方向由 P20 方向级
    #: (已证)承载而非板面差分——评分维
    #(merge_progress 只计第 2 份,边界)对它构造性零增量,
    #: 非正分拒是评分零维测量伪影非 EV 判断;与既有 'copy' 标签 C 豁免
    #: 同型。按 (名,星) 分星计数的单一源 =
    #: ``cw_merge_simulate.same_star_count``(全局面同名同星)。
    #: (`w242_star_directed/`/C 项)同为「完成素材放行」语义对称,无条件于
    #: 末窗 gap(完成价值全程存在,不作定向授权)。仅覆盖 CwActionBuyCardParam
    #(synthesize 候选虽 merge=True 但不覆盖)。
    #: 开分支裁决(`w436_merge_exempt_ab/` A/B 兑现,CI 口径同 `w422_form_ab/`/`w429_dup_ab/`):第三张
    #: offer 买率 off 53.93%→ex 83.52%(+29.6pp CI [21.1,38.9] 显著)/
    #: 形态达标率 31.00%→44.33%(+13.33pp CI [5.81,21.08] 显著)/
    #: core2≥1 进场率 +20.67pp 显著;守卫全净(真跌破利息档 +0.33pp 不显著/
    #: hp0 −2.0pp 不显著/bench 满帧占比不升/出口金不降);差一张桶
    #: −6.86pp 方向对不显著(桶主体由 ②生成通道与 EV 约束链共同消化)。
    #: **默认开**;False=回退非正分拒(代码留作回退通道)。
    merge_completion_exempt: bool = True
    #: [31] 凑档降级的成本带上限(1-2 费=P1 过渡带)
    bond_fallback_max_cost: int = 2
    #: [31] 降级触发回合门(P3 边界:r1-r2 无战斗买件纯付息损)
    bond_fallback_min_round: int = 3
    #: carry_gate 腾位买的轮界(r≤7;r8-r9 终局段买入不影响结算)
    carry_gate_max_round: int = 7

    # ===== 层4 补偿趟(迁移审计回连机制)=====
    #: 补偿覆盖的买侧标签(含
    #: 'carry_gate'——:该标签落「非核心目标件+bench 满+
    #: 早期轮」,与 v3_core_names 空窗下的目标件,金补偿路径对两种
    #: 标签都稳健;不为非目标件变现——只有更高优先级购买才配动用
    #: 压牌库资产;pair/copy/bond_fallback 凑数凑对类与 refresh/levelup
    #: 不覆盖[refresh 的补偿走 S2 报警适用范围,不经本标签集])
    remedy_buy_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'carry_gate',
    })
    #: 补偿受益候选的分数下沿(被拒分 ≤ 此值不为它补偿——只救高价值买)
    remedy_min_score: float = 0.5
    #: 报警升级态 refresh 金不足是否纳入补偿(S2 残余;默认开)
    remedy_alarm_refresh: bool = True

    # ===== S5 统一卖件弱序(迁移审计)=====
    #: [22]③ 再遇窗口表(费级→再遇期望轮数)。实测基准两个:1费 11
    #: (7-15 中值)/ 5费 120(60-180 中值,7-8 级窗口);2-4费为基准点
    #: 间的**拟合经验值**——5费基准跨度 60-180 使中段既无实测也无可信
    #: 参数化形式(非线性),标定接口=sim 校准域。消费方
    #: sell_priority_key。
    remeet_window_rounds: dict[int, int] = field(default_factory=lambda: {
        1: 11, 2: 25, 3: 40, 4: 60, 5: 120})
    #: 去向表派生的费级终局贯穿率(E→F 留存):
    #: 证据等级=**推断近似**—— 报告(Q1)为逐角色值(贯穿层
    #: 2费 骨架 0.66-0.95 / 消耗品 1费 0.05,费级非严格单调),
    #: 此处取费级趋势近似(高费件终局留存低);sim 校准域。
    through_rate: dict[int, float] = field(default_factory=lambda: {
        1: 0.20, 2: 0.20, 3: 0.15, 4: 0.12, 5: 0.10})
    #: 卖分缩放权重常数(S5 评分侧;w=sell_key_weight_scale×
    #: (1+min_loss)/(1+loss),封顶 1.0——1=不缩放(回退均一 bias);
    #: A/B 通道保留)
    sell_key_weight_scale: float = 1.0

    # ===== 层2:硬过滤链(redesign §3 覆盖态严格优先序)=====
    #: 过滤链层级序:应急 > 模式(人口落后由通道 2 人口位升级+通道 4 概率等级窗
    #: +EV 总账涌现,兜底局由 form_score 承接「人口别落后」观察;位面绝对基线
    #: {5,7,9} 是阵容无关的粗糙代理)
    filter_chain_order: tuple[str, ...] = ('emergency', 'mode')
    #: 各层放行标签集(候选标签仅作过滤域标记,不携带优先级——)
    #: 应急集内容修正(合流批 并入):补 for_gold
    #: (卖弱件)+levelup(升级)——应急态语义=战力买+卖弱件+升级,
    #: 旧窄集把两通道在应急态整体滤死(迁移审计批(可解释性遥测) F4);pair/copy/
    #: bond_fallback/synthesize 在应急态仍滤出(应急集保持窄)
    emergency_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'carry_gate', 'off_target',
        'free_bench', 'deploy', 'for_gold', 'levelup',
    })
    economy_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'pair', 'copy', 'copy_press',
        'carry_gate',
        'bond_fallback', 'off_target', 'for_gold', 'free_bench',
        'levelup', 'refresh', 'deploy',
    })
    #: war 标签集(`w126_b_arm/`/:refresh 进 war 集——「war 模式滤 refresh」
    #: 废除,D 是一等花钱通道([17]「该D牌D牌」不因 war 覆盖态消失;
    #: 授权仍由 V_D 批口径评分+interest_rule EV 门覆盖,标签集只管在场)
    war_tags: frozenset[str] = frozenset({
        'line_carry', 'line_opportunistic', 'bridge_core',
        'engine_seed', 'plugin', 'pair', 'copy', 'copy_press',
        'bond_fallback',
        'carry_gate', 'off_target', 'for_gold', 'free_bench',
        'levelup', 'deploy', 'refresh',
    })
    #: P1-a 末窗支出降格总开关(True=承接门定向投资授权在预算不足局
    #: 降格为减损保板;依据=`w516_p2_conversion/` 排除证据 HG5/IF30——β 弱通道下战力
    #: 投资换不回 15-25 血/败,方向性结论不依赖 β 量级,非「待验证」
    #: 悬置开关;False=A/B 对照分支/回退基准,两态注入面)。
    p1_exit_downgrade_enabled: bool = True

    # ===== 概率校准的刷新预算(提案面=.debug/temp/currency_war/
    # ===== w645_proposal_v2/SPECS.md 提案 B-v2)=====
    #: 塌缩带归零线 ω:refresh_prob(当前级,目标费)/refresh_prob(峰值级,
    #: 目标费) < ω → 该帧刷新预算归零(refresh_ev_budget 合法 0 帧第三类)。
    #: 比值由 cw_shop_odds.REFRESH_PROB 表逐帧导出(概率单一址,与分配器
    #: Π_refresh 估计器同源互指,禁第二概率口径)。ω 是标定字段:初值 0.1
    #: 占位=「当前级单刷命中率不足峰值级十分之一」;标定网格 {0.05,0.1,0.2},
    #: 多分支同过判前锁死取最小者(最保守归零线,出处=SPECS B-v2 §3;
    #: 首批双分支验证记录)。归零的账=塌缩带留金弱占优纯烧
    #(留金保留全部未来期权,烧金灭失),不需要息成本参与。
    omega_collapse_ratio: float = 0.1
    #: 有望帧帽真分位 q:帽 = ⌈−ln(1−q)·E_find⌉,E_find =
    #: cw_shop_odds.expected_refreshes_for_card(level,目标费,
    #: target_star=2, owned=j)(有限池精确期望,单一址同上)。q 为真分位
    #: 语义,−ln(1−q) 是其闭式精确乘数(q=0.8→1.61,q=0.9→2.30;推导:
    #: 每刷命中率近恒定时 P(T≤kE)≈1−e^{−k}),非新常数。网格 {0.8,0.9},
    #: 初值 0.8=保守档。j=0(零持有)时全部 (level,费档) 组合帽值 ≥39 > 6
    #: 刷帽=结构性不绑定;帽的实际绑定面=E_find=0 帧(owned≥k 目标已
    #: 集齐,或该级出不了该费档 p=0)——帽归零=搜索价值归零的如实账
    #(第 4 份副本不可用/纯烧),sim 实测绑定集中于此。
    refresh_find_quantile: float = 0.8

    # ===== 血预算停手·终止分支(P1「止损转支出」;设计  v2 §0/§2)=====
    #: 总开关:True=数学已定案恒接入调用口径(金零值引理+EV 对比式:守钱局面
    #: 存活概率上界 S0≤ε 时一切守钱资产期望被压没,释放当轮转化路径
    #: 严格占优——不是「待验证」的悬置开关;False=A/B 对照分支/回退基准,
    #: 两态注入面)。
    terminal_release_enabled: bool = True
    #: 守钱局面存活概率上界释放阈 ε(S0=Π 单发穿透场条件胜率 ≤ ε →
    #: 终止分支触发)。默认 0.03 = 设计  v2 §2.2 EV 对比式反解的
    #: 最悲观角 ε*=ΔS·V_live/(g+ΔG)≈0.02×300/212≈0.0283 的诚实带
    #: 下沿档(诚实带 [0.03,0.10],超保底部分≈0.36 金当量/帧,显式
    #: 接受)。**重标定登记的待办(§2.4)**:p_i 源 streak_floor_win_rate 为
    #: sim 档证据;Δp(piece)(停手窗买 1★ 件次战胜负面差分 n≥30)与
    #: ε*(g) 随金自适应均未标定——落地后 ε 全带重推(敏感
    #: 性口径)。首批适用范围 P1 only(谓词内 state.plane==1 硬门);
    #: P2 扩覆盖独立批,不消费 p2_cond_loss_table/p_win_p2_by_rung。
    terminal_survival_eps: float = 0.03

    # ===== 成型停手纪律([13] 停手线;迁移审计并入)=====
    #: 停手语义恒接入调用。
    #: 停手覆盖轮**全局下界**(迁移审计迁移审计晚买证据窗=r7-r9);实际覆盖轮=
    #: max(锁定线 typical_form_round,此值)——阵容派生(迁移审计-B1,
    #: 固定 r≥7 会固化「早成型阵容多买两轮」偏差)
    formed_stop_min_round: int = 7
    # 等级不作为独立门槛——2026-08-25 用户裁决 Q2,等级通过上场完整性进入
    # form_ok 判定

    # ===== 相位观测与授权(迁移审计影子;迁移审计切授权)=====
    # 兜底门判据 = 板面真收敛到 ≥2 过渡体系,非分数可达性(用户判读原则
    # 2026-08-26「任何位面看阵容完成度」);form_score 降级纯遥测观测,不进判据
    #: 兜底局(意向未锁)form_ok 的轮数下限(迁移审计校准判据,迁移审计):
    #: `w118_baseline/` 实测 A 分支兜底局 form_score≥0.5 在 r2-r3 即转真——1 过渡体系≠战力
    #: OK。结构门下保留(合取):即使两体系早凑齐,r5 前板面人口/星级仍薄,
    #: 保守留 FORM(地板 20 允许买牌强化,不亏)
    phase_fallback_min_round: int = 5
    #: 兜底局 form_ok 的有效体系数下限(`w132_b_arm/`/):有效体系数 =
    #: ``_engines_count``(四体系单一源,deployed 口径)+ hp_charge_stack 型
    #: 全局累积角色豁免(上场 2★ 计 1,万敌;迁移审计字段消费)。取 2 =
    #: transition_combos 定稿「四体系两两组合=过渡成型,单体系点火≠成型」
    #: (三选二 140/328 帖;2026-08-23 用户定调)
    phase_fallback_min_engines: int = 2
    #: boss 跌破利息档窗 node_type 缺读兜底轮(迁移审计统一口径:
    #: boss 窗主判据=节点图 node_type∈boss_round_node_types,轮数口径
    #: 全仓只留 discipline.boss_window_active 一处且仅作缺读兜底——
    #: P1 末节点恒为 boss 的节点图先验,r≥9 兜底)
    boss_window_fallback_round: int = 9

    # ===== 层3:板面查表评分(初版=档位×P3 + 息律 EV + H3 插值)=====
    #: 剩余战斗节点估计(V_D P1 收益侧的**缺省兜底**:plane_node_table
    #: 槽序表缺失/裸 session 时退此值;有表时由 ev.battles_left_plane
    #: 逐轮推导;层3 score_state 的 power 视界仍用本值)
    battles_left_est: float = 5.0
    #: 利息封顶档([17]:50 金息律,5 金/轮)
    interest_cap: int = 5
    #: 息 EV 折算轮数(消费面现状见 ev 层)
    interest_rounds: float = 5.0
    #: 档位分数部分(recipe 档 → 小数 rung 的插值系数;未标定)
    rung_frac_per_recipe_tier: float = 0.3
    #: 买侧 C_interest 的回档折中视界(`w131_a2n_arm/`/):买候选跨利息档的
    #: C = 档数 × min(R跨位面,此值)。依据:P6 回档账下界(破档后
    #: 1-2 轮回档,真实息损 1-3 金)与平面 R 上界(P5⑤,≈20-23)的
    #: 折中——买是一次性金→板面资产兑换,「停在低档到位面末」的
    #: 上界前件描述的 FORM 政策态由相位地板覆盖,不在 EV 门重复计罚;
    #: 3.0=两界之间的保守中点,网格精调(1-5)留 sim 批。只覆盖买侧
    #: (arbiter.interest_rule 的 CwActionBuyCardParam 分支);刷新(D)与升级平台账
    #: 保持平面 R 上界不动(P5⑤ 退化输出/平台语义)。
    interest_recovery_rounds: float = 3.0
    # ===== `w154_p2d/`/P2 段 V_D 修法(P11/P12 口径;常数归本层可 A/B 注入)=====
    #: P2 段 V_D 口径总开关:False=回 迁移审计前行为(窗二分=level_plan 互斥,
    #: 成本=批口径面值,收益=P1 骨架参数)——A/B 基线分支。P1 分支与开关无关
    #: (逐位不动,P1 sim 零漂移回归门)。
    vd_p2_enabled: bool = True
    #: P1 收益侧战斗期望掉血=条件败局伤害的线性拟合**截距**(遥测拟合:
    #: `w324_coarse_battle/` 战斗粗模型冻结语料 417 条战斗类差分,battle 节点败局伤害
    #: =截距+斜率×成型档,battle n=278/73 局聚类稳健、斜率 SE 1.25;
    #: 拟合产物随粗模型语料归档);
    #: 语义=「打了但输了」的伤害期望,与 V_D 收益式的 Δwin_rate 相配
    #: ——无条件均值拟合会与胜率差双计)
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
    #: 基准与对抗审计记录);encounter=截距 24.32 +
    #: 斜率(−4.53)×成型档(斜率 SE 2.41 显著);boss 斜率 CI 含 0 →
    #: 退常数 26.71(背测 sim −22.61 vs obs −25.82)。
    streak_floor_loss_damage: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            'encounter': (24.32, -4.53),
            'boss': (26.71, 0.0),
        })
    #: 连胜 EV 地板胜率表(节点类型×成型档;取**注入后**值 p_injected
    #: =语料实测+plaza 先验只进 rung≥2、share≤0.25,来源同上
    #: 粗模型拟合产物的 win_rate_table_injected)。键域 0-2(消费侧成型档封顶 2)。
    streak_floor_win_rate: dict[str, dict[int, float]] = field(
        default_factory=lambda: {
            'battle': {0: 0.009, 1: 0.356, 2: 0.315},
            'encounter': {0: 0.038, 1: 0.026, 2: 0.264},
            'boss': {0: 0.077, 1: 0.027, 2: 0.187},
        })
    #: P2 掉血期望(P12 收益侧,**条件败局伤害**口径——与 Δwin_rate 相乘
    #: 不双计,P15 口径命题;=「打了但输了」的期望)。标定=P2 损血谱粗档
    #: (冻结语料同 run 相邻行 hp 差分;标定叙述与精度声明
    #: 增补 A):普通战斗桶 20.05(n=19;
    #: 桶内零损行=0,实测口径核验=条件伤害)。置信声明(`w371_recal_attack/` 审计 M3):
    #: SD 10.38,事件级 t95% CI [15.0, 25.1],run 级聚类 bootstrap CI
    #: [15.1, 23.6](19 事件来自 13 run)——区间半宽 ±25%,取 20.05 与
    #: 取保守 22-25 在现有 A/B 判据下不可分辨,本值不做精度主张。
    #: 三源对照:语料条件 20.05 / 实机存活局事件均值 −15.3(59 事件,
    #: `w350_p2_survival/` REPORT §4)/ sim coarse 分 rung 条件伤 ~11——取语料上沿的
    #: 理由=删失剔除 hp≤1 死亡行 → 低估方向。
    #: **benefit 项量级声明**:P2 分 rung 胜率表未标定(登记的待办)——本项只作「P2 掉血更贵 → 找件
    #: 账方向上调」的方向修正,量级未标定,不得引用「P2 胜率≈0」类
    #: 论证抬升(损失侧条件口径必须配同 regime 胜率,P15 精神)。
    #: encounter 16.67(n=3 样本极小不采)/boss 桶零样本(沿用 26.71)
    #: 不进本标量;普通战斗为 P2 主导节点型。
    vd_p2_loss: float = 20.05
    #: P2 穿 50 段回档轮上界(P11 成本侧:P2 收入 13-19/轮 → 回档 ≤2.31 轮;
    #: C_dec 的 Δinterest × min(R,此值))
    vd_p2_recovery_rounds: float = 2.31
    #: 富余金流动性影子价 ρ(P11:纯富余段 C_dec 下界=0 后的期权项上界;
    #: P10① 携带溢价利息分量背书,`w151_p2/` 四局实证实现值≈0 → 起步 0)
    vd_p2_liquidity_rho: float = 0.0
    #: P1 体系对缺件找牌通道总开关(`w170_p1_vd/`/):False=回 `w166_pair_guard/` 前行为
    #: (P1 找牌只有 core 通道,level_plan 窗互斥逐位旧语义)——A/B 基线分支。
    #: True=P1 锁定帧(配方锁 p1_pair/①锁 transition_pair)缺件 ∧ 金≥
    #: interest_floor+刷价+买价([3] 单次预算前提)时,pair 缺件账参与
    #: V_D(scoring._vd_p1_pair;core 通道不受本开关覆盖)
    vd_p1_pair_enabled: bool = True
    #: 板深单位值(板深=可上阵件数,板面形态维之一,非单卡拆分;方向
    #: 原引数据源已清退禁引,现未锚定;数值骨架占位未标定)
    depth_unit_value: float = 2.0
    #: 追级 EV 单位值(层2 查表项「追级 EV」:等级→部署
    #: cap→板深的期权价值;小数等级=level+xp 进度比,单击经验
    #: 即分数性推进;未标定)
    level_unit_value: float = 1.0
    #: 目标件持有进度项(板面形态维:持有域内∈当前目标集的件数
    #: /基线,封顶计值——cap 饱和+店员非引擎阵营时买入恒 0 分被
    #: 「非正分」拒,r3-r6 空转攒金团灭的解;集合隶属计数,非
    #: 单卡边际拆分;base **已标定**=9(首轮标定:base=6 时第 7 件
    #: 起目标件 0 分,中期买入饥饿→板弱团灭;9 让第 7-9 件暴露
    #: 正分,30 局 mean 31.37/团灭 0)
    target_hold_value: float = 3.0
    target_hold_base: int = 9
    #: 目标件持有进度项天花板系数(持有进度保留暴露但
    #: 封顶折减——顶格不再=满形态;targets=min(此系数, n/base)
    #: ×target_hold_value)。网格标定:1.0 无单独增益,维持 0.8
    target_hold_cap_frac: float = 0.8
    #: 引擎分数进度项单位值(成型攻坚,每满进度引擎)。
    #: 依据:P3 已证 e0→e1 +1.4/e1→e2 +1.6 金/轮——买进度件是
    #: 正期望期权暴露;deployed=cap 时进度件躺 bench,
    #: 混合域阈值不跨越 → 评分恒 0 → 「评分没买」主因(20 局
    #: 诊断 135/171 段引擎买候选评 0.0 被非正分拒)。本项对进度
    #: 小数余量(Σmin(w/tier,1)−整数引擎数)暴露,与 rung 整数档
    #: 互补不双计。0=关闭。
    #: **双窗网格标定 1.0**(A 窗 hp_ge_60 0→0.167 / B 窗
    #: 0.2→0.233,唯一双窗一致分支;2.0/4.0 过冲在 B 窗翻车——
    #: 高单位下进度件挤掉目标件买入)
    engine_frac_unit: float = 1.0
    #: 核心升星价值项单位值(迁移审计,[13] 成型三件套第三件:
    #: 过渡核心 2★)。持有域内 star≥2 且∈目标集(意向目标∪引擎件)
    #: 的件数 × 此值——deployed 全额、bench 折减。修的是第六局判读:star 此前只在阵营
    #: 计数(star×权重)与 targets 星级加权两条路径暴露,engines 封顶
    #: 后 2★ 分差≈0 → 换阵卖 2★ 不罚分/凑合副本 ≈0 分(升星投资
    #: 系统性贬值)。0=关闭(A/B 基线分支)。
    core_star_unit: float = 3.0
    #: 3合1 中间进度项单位值(迁移审计,[13] 副本凑合爬坡段:
    #: 目标件第 2 份 1★ 的期权暴露)。core_star 只覆盖 star≥2,迁移审计
    #: 断买根因①:第 2 份买入在 targets/eng_frac/core_star/rung
    #: 全维度零 delta → 「非正分」拒 → 金 59→90 溢出趴三轮
    #: (run_20260825_130151 r7-r9,[17] >50 每一分都该花)。每名
    #: 只计第 2 份(第 3 份 merge 后 core_star 承接,不双计);
    #: deployed 域 ×1.0 / 纯 bench 域折减。初值=core_star_unit 同量级(同一 2★ 目的地的期权),
    #: 未网格标定,sim A/B 方向见 deep_read/W96_报告.md;0=关闭。
    merge_progress_unit: float = 3.0
    off_target_sell_bias: float = 0.5
    # ===== 成型补充偏置(d2 评分批;P1 boss 转化) =====
    #: 成型补充偏置:未成型(引擎<2)+ 引擎件候选在跌破利息档窗(r≥5 P1,非应急)
    #: 的 0/小负分买入顶成正分的偏置。依据=[13] 成型即停手(未成型=继续买
    #: 配方件)+[27] 每场质量战(引擎完成 win 跳升×剩余战斗≈4.5-5.4 金);
    #: 量级=完成期权的保守下限,只顶 val∈[-interest_rounds, +0.5](单档
    #: 真实息损内;emergency 的 -25 息崖([18])与深负分不被翻越)。
    #: 0=关闭(A/B 通道)。
    forming_bias: float = 5.0
    #: 成型补充偏置的顶分上沿(原分 > 此值不加偏置——不叠加已正分买入,
    #: 防「高单位下进度件挤掉目标件」过冲)
    forming_bias_val_max: float = 0.5
    # ===== 体系集中度(d2 意向批;候选层配方亲和) =====
    #: engine_seed 板面配方亲和过滤开关([20] 过渡是配方不是散买):
    #: True=板面已有未成型体系时,新体系引擎件不生成 engine_seed 候选
    #: (散买断,空窗/成型可开新);False=关闭(回 迁移审计行为,全引擎件
    #: 见即买)——A/B 通道,默认开。
    engine_affinity_enabled: bool = True
    # ===== `w150_buy_lock/`/买侧通道锁定目标约束(`w143_formation/` 补充判读通道半边)=====
    #: 总开关:False=回 `w145_recipe_lock/` 后行为(A/B 基线分支)。锁定帧
    #: (cw_intention.locked_buy_scope 非 None)时,off_lock_buy_tags 覆盖的
    #: 买通道候选中「目标件 ∉ 锁定目标体系集」者在层3评分减
    #: off_lock_buy_penalty(降级非禁绝——板面差分显著为正仍可过;
    #: [31]④ 填充不变量:填充通道保持可回收垫层语义,不硬禁)。
    buy_lock_constraint_enabled: bool = True
    #: 约束覆盖的买标签(`w147_evolve/` 基调:优先级/围栏式,禁一刀切禁绝——
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
    #: [31]④ 梯队)不覆盖。
    off_lock_final_fence_enabled: bool = True
    # ===== `w155_evolve_lock/`/evolve 换人事务锁定目标件保护(`w147_evolve/` 执行半边)=====
    #: 总开关:False=回 `w150_buy_lock/` 后行为(A/B 基线分支)。锁定帧
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
    # ===== 迁移审计S1 型成型后引擎丢失修法(两件独立 A/B 通道)=====
    #: 件1·引擎下界守卫:False=回 `w155_evolve_lock/` 后行为(A/B 基线分支)。True 时
    #: execute_replacement 生成事务时,若事务净效果使过渡引擎数
    #: (cw_battle_calib._engines_count 口径)从 ≥2 跌破 2,被拆引擎体系的
    #: deployed 贡献件获得新线同级**留场资格**(不划进 old_line 下场)
    #: ——语义「换人可以,拆引擎不行」(只保「不卖」
    #: 不保「在场」,末轮无回场窗 → 永久丢失;迁移审计§2:S1 局全部
    #: 37/37 通道=evolve_tx 整批下场)。护的是在场引擎贡献,不是库存。
    evolve_engine_guard_enabled: bool = True
    #: 件2·末轮演进冻结:True 时位面末窗(剩 ≤1 轮,即位面内倒数第二轮
    #: 起;位面轮数 = 节点序列场字段现值长度,默认 P1=9/P2=7)演进换档
    #: (undeploy/sell 非空的拆板事务)
    #: 冻结不发出——纯加深(deploy-only)与填位照旧;与 `w150_buy_lock/`
    #: final_fence(买侧末轮围栏)语义对齐:末轮换档天然
    #: 无回场窗,「加深收益 < 引擎丢失风险」在该窗口系统性为真
    #: (迁移审计§1:r_loss 90% 落 r8-9)。
    evolve_final_freeze_enabled: bool = True
    # ===== `w174_deploy/`/引擎补完守卫(own-gap 修法)=====
    #: 总开关:False=回 `w170_p1_vd/` 后行为(A/B 基线分支)。True 时
    #: cw_evolution.evolution_step 在常规演进提案**之前**发补完事务:
    #: pair 体系(p1_pair ∪ transition_pair,含希儿系单卡判据)
    #: owned(bench∪deployed,全羁绊口径)≥ tier ∧ on-board
    #: (board_factions 口径)< tier → bench 该体系成员上场,room 不足
    #: 换下最弱非保护件(保护=pair 成员/引擎件/锁定目标件/种子窗)。
    #: 修「拥有≥门槛却从未同时上场」(`w173_supply/`:8/11 never-2 局,件躺备战
    #: 席到局终;[20] 件上场才算配方,[13] 过渡成型≈过 P1)。末窗冻结
    #: 豁免复核 = 净效果 pair on-board 与引擎数不减(
    #: 防丢语义同向:补上不是拆)。
    evolve_engine_completion_enabled: bool = True
    # ===== `w201_strand/`/补完缺口 owned 口径(distinct;修②)=====
    #: 补完事务缺口判定的 owned 计数口径:True=distinct 名单数——
    #: 同名副本是 3合1 升星素材非配方件([20] 配方=不同成员;board
    #: 同名唯一 → 副本永远不可上,全羁绊逐件计数会造出「永远填不满
    #: 的幻影缺口」,`w200_probe/`:227/276 补完轮轮空转);False=回 `w174_deploy/` 后
    #: 全羁绊逐件计数(首版口径)。
    engine_complete_distinct_owned: bool = True
    # ===== `w202_grade/`/补完保护集分级(136 型构造闭死修法)=====
    #: 补完事务 undeploy 常规候选枯竭(deployed 全保护,`w200_probe/` 136:
    #: 锁定线件+引擎件全覆,列车缺口 r6-r9 轮轮被选但 tx 永远建不出)
    #: 且缺口体系已连续被选 ≥4 轮(标定:门 2/3 有 benign→mal 坏翻转,
    #: 门 4 全硬门过——benign→mal=0/mal 24→20/never2 10→7)时,
    #: 按分级序降级换人:G0 非引擎锁定线件(locked_buy_scope∩非TT,
    #: 最可动)→ G1 未成型引擎件(下之不拆成型引擎)→ G2 已成型
    #: 引擎件/pair 成员/希儿系贡献件恒不可动。依据 [13] 过渡成型≈
    #: 过 P1(成型缺口=发令枪级)让位于 [23] 锁定线语义;False=回
    #: 后「不硬拆」。
    engine_complete_grade_down: bool = True
    # ===== `w179_gate/`/P1 早期新件买入门(双条件窗:缺件密度 × 利息档口径)=====
    #: 总开关:False=回 `w174_deploy/` 后行为(A/B 基线分支;FORM 相位地板对配方对
    #: 件买入照旧全拒)。True 时 arbiter.gold_floor 对满足窗的 CwActionBuyCardParam
    #: 放行「买入后同利息档」的购买(窗语义见 discipline.p1_early_gate_open
    #: 与 arbiter 的逐笔利息档/单轮上限检查)——修 `w173_supply/`/`w175_gate/` 的 pass_buy
    #: 形态(own<门槛=买少了:缺件曾 1-3 费出现在店、金 7-15 金穷轮,
    #: 被 FORM 地板 20 一刀切拦掉,违反口述 [11] 档内购买不损息)。
    p1_early_gate_enabled: bool = True
    #: 窗的缺件密度门槛:配方对方向未持有 distinct 对成员数 ≥ 此值
    #: 才开窗(历史窗语义,现行无行为消费点——读端已随旧决策栈退役,
    #: 考古走 git 历史;配置项保留已登记)。标定(`w179_gate/`,
    #: n=100 池 861fc9f6):全体 P1 轮 unheld 分布 [8,16](r1 p10=14 /
    #: r9 p10=8),pass_buy 病灶轮 unheld 11-15——k 在 [1,8] 带内对本
    #: 分布**无区分度**(诚实记档:operative 约束=利息档口径+单轮上限+
    #: 层3评分),取 6=「板面远未覆盖配方对」的语义守卫(关掉假想的
    #: 近成型窄窗,防未来分布漂移把门开进不该开的段)。
    p1_early_min_missing: int = 6
    #: 单轮放行笔数上限(防 r1 扫店):同利息档口径下金 12-19 连买 1费
    #: 可达 2-9 笔(`w179_gate/` 标定:门内笔数 p50 0-1 / p90 1-3 / max 7,
    #: 病灶轮 1-2 笔)——取 1=「目标件刷新出现=唯一最高优先级,只买它」
    #: ([31]② 逐字口径;n=100 扫描 cap1 出口金 34.23 与基线 34.25 持平
    #: =P13 同档零损的理论预测逐位兑现;cap2 −2.3 金换 hp +1.3,
    #: 出口金口径上不如 cap1 干净)。每轮增量支出 ≤3 金,息损上界=档内 0。
    p1_early_round_cap: int = 1
    # ===== `w194_p2line/` [33] 稳态 CwActionLevelUpParam 多击组(迁移审计泛化)=====
    #: 总开关:False=回 `w193_p2sim/` 后行为(A/B 基线分支——多击组只在轮内
    #: deploy_cap 拒绝触发补偿时发出,Catch-22 原状)。True 时
    #: arbiter 末段主动发稳态多击组(remediation.steady_state_
    #: levelup_group):进轮 cap 满 ∧ bench 有方向件([33] 稳态字面
    #: 语义)→ [CwActionLevelUpParam]*clicks_to_next_level 整组,授权=
    #: levelup_ev_basis 按 n×总价(稳态下人口位分支天然成立)+
    #: 逐动作 gold_floor 事务性重验(与 deploy_cap 补偿分支同一重验
    #: 链)。修「恒 lv6 通道缺陷」(迁移审计:每轮 1 击吞吐,lv6→lv7 需
    #: 7 轮,死亡窗内不跨;run15 型死局的 lv7 价格带永不可达)。
    #: 每轮至多一组(strategy_state_of(session).v2_steady_lv_used 轮键,防刷后 re-decide
    #: 段链连发);level_max 前置守卫保留。
    #: **适用范围 P2+**(首版全位面泛化 n=300 引入 P1 never2 9→10 回归,
    #: `w194_p2line/` 辙回——P1 多击已由 deploy_cap 补偿分支覆盖)。
    levelup_multihit_enabled: bool = True
    # ===== `w194_p2line/` 件3:P2 核心件首件同档买入门(`w183_carry/` 方向②)=====
    #: 总开关:False=回 `w193_p2sim/` 后行为(A/B 基线分支)。True 时 P2 段
    #: (plane≥2)意向核心(v3_core_names)的**首件**(working 现持无
    #: 同名)在 gold_floor 拒绝前放行「买入后同利息档」的自然店购买
    #: (arbiter._p2_core_firstpiece_exempt)——[31]②「目标件刷新出现
    #: =唯一最高优先级」+[11] 同档零息损+[22]③ 弃购代价=再遇窗口
    #: (3费@lv6 E=27 次刷新 / 5费 60-180 轮)。修 `w194_p2line/` 探针实证的
    #: 「P2 穷轮(gold<50)核心件在店被 HOARD 地板 50 一刀切拦」
    #: (n=10:核心在店 6 轮漏买 5,全部 gold≤12 穷轮)。单轮 1 笔
    #: ([31]② 只买它);零刷新授权(与 `w170_p1_vd/`/迁移审计刷门管辖不交集)。
    p2_core_firstpiece_enabled: bool = True

    # ===== `w300_dup_ruling/` press 通道:目标外同名副本压牌库购买(5 参数,V-B3 全量
    # registry 化;arm0=默认值全关零漂移,armA=注入开启;A/B 结论落地后
    # 按 先例逐字段裁决去留;评分偏置两字段已随 节
    # 已定案清理)。设计规格与 A/B 兑现裁决(v3 规格节与其谱系
    # 记录见该 ADR;A/B 兑换统一裁决表(V-B4;锚定义=规格 §5.3,冲突处以本表为准):
    # | R1 | star≥2 升≥MDE ∧ 进场金/出口质量/经济卫生副基准均不劣 → 实现+ADR+三同步 |
    # | R2 | star≥2 持平(<MDE)∧ seg 真拦残留≤0.15 ∧ 其余基准不劣 → 实现
    #      (「有效收敛」;P4 张力=收益主体在 sim 不可观测的期权/对手面,
    #      ADR Considered Options 必含张力节+向用户呈报观测极限) |
    # | R3 | star≥2 降超噪声带 ∨ seg 真拦残留>0.15 → 不合入,回炉
    #      (首要嫌疑=插入候选挤占金预算,看进场金分布移位) |
    # | R4 | star≥2 升 ∧ 经济卫生副基准劣化超噪声带 → 降级调常量
    #      (press 分支加 after≥利息档线同档语义收紧),不硬合入 |
    # | R5 | armA 触发样本不足(可达性短跑 E02 形态样本<30)→ 不合入,
    #      通道判「sim 内不可达」,转构造账本锁评估 |
    #: 全通道总闸(False=通道整体不评估,现行为零漂移;True=press 分支
    #: +candidates 守卫豁免分支+§3.3 三相位 [11] 地板前置分支+检查器
    #: C-B/C-C 发出同步开——A/B 捆绑为一分支,双分支同尺,V-B4.2)。
    #: 默认开(`w368_press_ab/` A/B:n=300/分支 R2 成立——seg 真拦 −85.6%、通道开通
    #: copy_press_channel_closed 41→0、439 轮替代买进、core2≥1 +24.7pp 显著、
    #: 成型率 +6pp 显著、零回退;star≥2 +3.0pp 不显著如实;对照分支注入 False 保留)。
    press_channel_enabled: bool = True
    #: band 推导质量线(V-B5.2:0.50 在 P1 开域内被口述依据 [30]「1-2 费带」
    #: 覆盖,仅 lv≥7 中后段生效而彼时带自洽闸已关通道——本参数是中后段
    #: 守卫参数非行为旋钮;敏感性扫描=主批硬前置,发现敏感再立项)。
    press_band_cum_threshold: float = 0.50
    #: 停机护栏(V-A2 继承):press_channel_open 的开域上界(lv≤此值
    #: ∧ plane==1)与带自洽闸参照系 press_band(此值)={1,2}。
    press_channel_max_level: int = 6
    #: press 候选逐轮采纳笔数上限(V-B8.1,更严一级;量级=单轮至多
    #: 一笔压牌库副本,与 p1_early_round_cap=1 同式轮键计数)。
    press_copy_round_cap: int = 1
    #: [11] 同档/1费豁免分支(§3.3 三相位共用前置分支)逐轮放行笔数上限
    #: (V-B8.1;量级基准=`w179_gate/` p1_early_round_cap=1 先例,取 2 因该分支覆盖
    #: 方向内候选+press 候选两股)。
    press_exempt_round_cap: int = 2


    # ===== `w242_star_directed/`/末窗星级定向授权(`w232_filler_star/` 待办项;设计件 08
    # §4.2 Phase 1b 星级投资方向)=====
    #: 末窗星级定向授权无条件启用:依据 = star 是 `w231_star_diag/`「评分结构性拒副本」病灶的
    #: 正解且 sim 无挤出(量级不足属参数调优非行为开关)。行为语义:
    #: P1 末窗承接缺口 gap>=1 对**同名副本买入**给定向授权
    #: ——candidates 层放行副本候选生成(r410 守卫+方向门,`w232_filler_star/` A/B
    #: 豁免的 gap 条件化分支)+ arbiter 非正分门放行副本(`w231_star_diag/` 主因:
    #: 副本评分零维被结构性拒,到不了 EV 账);地板族/copies_cap/r408
    #: 同轮守卫/bench 容量照常覆盖。

    # ===== `w252_ma_directed_refresh/`/M-A 定向 D 牌授权窗(`w249_core2_reach/` 诊断修法)=====
    #: M-A 定向刷新无条件启用:依据 = M-A 是 `w249_core2_reach/`「策略从不支付搜索成本」
    #: 病灶的对症修法且方向为正(量的解锁归 cap 提升独立批)。行为语义:P1
    #: 末窗承接缺口 gap>0(handoff.handoff_gate_gap 单一源复用)**且**
    #: 存在追名 peak≥2 的目标件(锁定采购目标名集内某名 star 加权在
    #: 手副本 ∈[2,3),距 3合1 只差最后一张)时,向刷新(CwActionRefreshShopParam)
    #: 开放有界预算。**只覆盖刷新维**(防双计,`w232_filler_star/` A/B/`w242_star_directed/` C 各覆盖买牌
    #: 维,互斥边界:同一动作只有一条授权来源——买候选走既有
    #: interest_rule 缺口项/copy 放行路径不动;refresh 候选要么走既有
    #: V_D 正分/gold_floor 路径,要么凭本预算有界放行,无叠加);
    #: copies_cap/r408/bench 容量等约束链照常覆盖。
    #: 单合资格轮刷新次数上限(`w249_core2_reach/` 白盒估算初值:每轮 ≤2 次)
    directed_refresh_per_round: int = 2
    #: 每局刷新总上限(`w249_core2_reach/` 白盒估算初值:≈覆盖一颗 2★ 的第二跳
    #: 6-7 次;原消耗计数字段 strategy_state_of(session).v3_dir_refresh_used
    #: 已随死代码清偿移除——本上限现为非消费的声明性约束)。金消耗披露面:预算放行的每次刷新照付刷价,
    #: 金账户由 simulate 真值扣减,P1 末窗利息损失随 A/B 守门指标判读。
    #: **本常量是非绑定约束(`w274_cap_batch/`/)**:合资格授权窗 = gap>0 ∧
    #: P1 末窗(窗 {r6..r9}),
    #: per_round 2 ⇒ 窗内可行上限 8 次曾在本值 6 之上;`w275_knob_ab/` gr6 分支
    #: (n=200 同 seed 配对)dir 授权 339 次、cap 开始参与钳制(窗容量
    #: 8 > cap6),行为面为正(core2≥1 +6.7pt)——cap 是否重新 bind 的
    #: 定标归后续实机/大批核对,非本批变更理由。历史候选档
    #: 保留证据:cap10/cap14 曾作为「第二跳吞吐量级」修复候选(迁移审计-R 断点),
    #: 实验证明无效,勿重复试错。「加量」的有效旋钮是
    #: directed_refresh_per_round 与授权窗宽度,
    #: 非 game_cap。
    directed_refresh_game_cap: int = 6

    # ===== 未成型期姿态:泄息通道(release)与换线判据参数 =====
    #: 设计决策单一源=行内申报**符号不稳参数一律默认值+标定接口,不拍死**:
    #: Δhp/boss 税由 sim 批网格标定后锁值(DESIGN §⑥ EV 参数门)。
    #: boss 税分位基准组 {P50, P75, P90}(sim 标定接口,非运行时值)
    boss_tax_anchor_group: tuple[float, float, float] = (32.0, 34.0, 36.0)
    #: 边际战力代理 Δhp·普通战(轮内去均值,hp/场;语料 166 局 5→6 人实测;
    #: 弱信号非单调,只作敏感度分支——DESIGN §①诚实判读)
    delta_hp_normal: float = 1.96
    #: 边际战力代理 Δhp·boss 层(裸差分,hp/场;P1 boss 全在 r9 轮次混杂极小,
    #: 末窗旗杆帧的正确语料层——DESIGN §①)
    delta_hp_boss: float = 4.30
    # (换线判据四参数族 line_switch_enabled/theta/debias_delta/min_dwell
    #  已随候选-锁定制撤账:唯一消费者 should_switch_e 已删——锁定一次性
    #  决策无换线判据对象(12 号篇 §1.4);零消费死字段,
    #  清理归后续批。)
    # (release 帧活栈消费门开关已随 第 4 态清理:开分支
    # A/B 结案,消费门恒接入调用;判据单一源 = economy_cycle 义务核算
    # (``overflow``/``obligation``)+ 预算披露面(``disclose_budget``),
    # 原 session.v3_release 泄息指令字段已随死代码清偿移除,
    # 旧开关/字段名见该 ADR。)

    # ===== P2 生存批:换线存活轮数门(C4) =====
    #: 设计决策(C3/C4 重设计裁决+C4 接入调用):
    #: C4 剩余节点序列逐节点投影/双源标定。
    #: 标定=双源重标定(死亡真源=实机对局台账局终行,
    #: hp≤1 不删失、hp_after=0 死亡行按 hp_before 全额入桶、不按置信度
    #: 过滤——旧删失口径「置信<1 剔除」系统性剔死亡局帧=反保守,已废;
    #: 产物为双源标定台账(记录=行内申报),双源互校:帧级合并均值 10.79 ∈
    #: run 级聚类 bootstrap CI [6.7,10.97])。
    #: P2 节点损血表(节点型→**无条件期望损血**,正数)。
    #: ⚠️ 消费面声明:本表**不进任何行为公式**(两态决策层与阈值层 μ
    #: 一律吃 p2_cond_loss_table,见该字段)——本表语义=迁移审计无条件期望
    #: 的**标定自洽基准**:与条件败面表的比值隐含各节点型桶的板强混合
    #: 平均存活率(1−无条件/条件:normal 0.204/encounter 0.100/boss
    #: 0.000,对齐锁钉死)。这是 kind 坐标上的桶均值,不是 rung 阶梯,
    #: 与 p_win_p2_by_rung 的 rung 坐标不同——「同 rung 恒等式无条件=
    #: (1−p)·条件」在两表间不成立也不应成立:样本窗(迁移审计实机深层局
    #: vs `w346_gate_validation/` sim Δ池)与坐标(kind 桶 vs rung)均不同,详见三表对齐节。
    #: 覆写=迁移审计双源重标定的无条件期望三档(normal 10.16/encounter
    #: 12.00/boss 15.50,CI 记录原「旧删失
    #: 口径条件常数暂抄」20.05/16.67/26.71 随两态消费口径定稿停用,
    #: 。node_type 缺读兜底=normal(战斗节点频率最高档,
    #: 2/5 槽;触发宽度居中——三档中 encounter 最小、boss 最大,normal
    #: 兜底既非最紧也非最松)。reward 零损档承接奖励+补给零损日历轮。
    #: 边界声明:本表与 p2_cond_loss_table 是同一 迁移审计标定的两个
    #: estimand(无条件期望 vs 条件败面),按消费语义分表,非双源漂移。
    p2_node_loss_table: dict[str, float] = field(default_factory=lambda: {
        'normal': 10.16, 'encounter': 12.00, 'boss': 15.50, 'reward': 0.0})
    #: P2 条件败面损血档(输了战斗这一条件下的期望伤害;两态决策层
    #: 损血幅度唯一源,消费点=阈值层 cw_first_passage._loss_dist 投影
    #: 与两态胜率映射(cw_plane_table.p_win_p2)——E[损血|板强]=(1−p_win(rung))·本表)。
    #: 值=迁移审计双源重标定条件败面(normal 12.77/encounter 13.33/boss
    #: 15.50,标定叙述见 p2_node_loss_table 段头):reward 零损档同上表(奖励/补给零损照走)。
    p2_cond_loss_table: dict[str, float] = field(default_factory=lambda: {
        'normal': 12.77, 'encounter': 13.33, 'boss': 15.50, 'reward': 0.0})
    #: P2 损血标定家族版本披露基准(第三维,与 cw_economy 收入口径版本
    #: 相互独立):任一 P2 损血
    #: 标定值/消费口径变动(p2_node_loss_table / p2_cond_loss_table /
    #: p_win_p2_by_rung / 两态递推形态)必须递增并随批重锁。sim 台账
    #: manifest 不承载本版本(cw_sim 禁触批,披露面=registry+锁,边界
    #: 如实声明)。v1=迁移审计覆写+两态递推定稿。
    p2_loss_calib_version: int = 1
    #: C1 定向刷新存在性名集的「高费强件」费用下界(买侧不覆盖名单,
    #: 只覆盖刷新存在性名集;消费点=filters._refreshable_names)。来源=
    #: 对抗审计 A1-β 反例画像「4 费通用强件是最高 Δp/g 选项」(记录=
    #: 登记的待办 2)+ sim 分
    #: rung 胜占比 0.34→0.65 单调(`w346_gate_validation/` 报告 §3.2 实证基础)=高费高星
    #: 战力优势。原批名 dying_band_high_cost_floor(C3 濒死带首用),
    #: C3 已定案清理(节)后随批改中性名,取值与消费
    #: 语义不变。
    directed_refresh_high_cost_floor: int = 4
    # (C4 换线存活轮数门三参数族(line_switch_survival_gate_enabled/
    #  rounds_two_state_enabled/line_switch_survival_margin)与投影参数
    #  (encounter_heal_est/line_switch_boss_ci_halfwidth)已随旧方案清退批
    #  删除:双开关默认关+开分支判据登记的待办未跑即整体出局,清查报告
    #  OLD_MIX_AUDIT §1.3;门机械(cw_line_switch.survival_gate 族)与
    #  cw_intention._switch_gate_open 接入调用同批删。损血表与两态 p_win 表
    #  保留——阈值层(cw_first_passage._loss_dist / cw_plane_table.
    #  p_win_p2)仍消费,math_proofs P12/P15v2 方向级引用。)
    #: C4 两态口径 p_win 表(成型度 rung(0-2 钳制)→P2 战斗条件胜率)。
    #: 值出处=`w346_gate_validation/` 门验证批分 rung 胜占比实测(冻结池 Δ池分支,
    #: 战斗 d>0 样本占比):k0=15/936=0.016,k1=879/2129=0.413,
    #: k2+k3 钳制并入=864/1316=0.657(生产 rung 0-2 钳制,k3 桶折叠)。
    #: 口径勘误:`w393_family_attack2/`/`w412_w370_debts/` 引文称「coarse 分支 0.34→0.65 单调」,原始
    #: 数据核对 coarse 分支实为 0.8%/35.6%/31.9%(非单调、无 0.65),
    #: 单调序列只在 Δ池分支——两态模型前提「p 对成型度单调不减」
    #(REDESIGN §5 条 1)覆盖下取 Δ池档,本注释为准。
    #: rung 取样坐标单一源=cw_battle_calib._settle_rung(与表坐标同源,
    #: 采样键;board 全集+星徽,deployed 域,0-4 钳到 0-2)。
    #: 证据等级=sim 档(单档 n≈900-2100,无实机 P2 分 rung 样本;
    #: 方向声明=低档 p_win 低估损血高估、存活轮数偏短、门偏紧)。
    p_win_p2_by_rung: dict[int, float] = field(default_factory=lambda: {
        0: 0.016, 1: 0.413, 2: 0.657})

    # ===== R3 撤销出口①意图证据(治 `w386_gate_energize/` BP1「门放行噪声换线」;
    # 设计决策;消费点=cw_intention.core_miss_n_required / _revoke_alt_evidence)=====
    #: 证据组 A:「核心实际可达但连续 N_req 轮未现」的容忍概率 ε。
    #: 闭式 N_req(core,level)=⌈ln ε/ln(1−q)⌉,q=1−(1−r)^5,
    #: r=refresh_prob(level,cost)/DISTINCT_CARDS_PER_COST[cost](再遇
    #: 窗口既有构件;推导 P(N 轮未现|单轮出现率 q)=(1−q)^N≤ε)。
    #: ε=5%=「可达却连续缺席」压到二十分之一以下才构成断供证据。
    #: 实表代入(cw_shop_odds):3 费@lv5 q=0.069→N_req=42,3 费@lv7
    #: q=0.135→21,1 费@lv5→27——拍死值 CORE_MISS_N=6 的 6 轮缺席在
    #: q≈0.07 下自然概率≈0.65,纯属噪声,定量坐实 `w386_gate_energize/` BP1「阈值降
    #: 到可达值后先到达的是出口本身」。ε 的 sim 扫描 {1%,5%,10%} 挂
    #: L2 注入分支(出口①触发率 × 误开窗占比权衡,设计 R3.5),5% 为
    #: 设计默认档。
    revoke_miss_tolerance_eps: float = 0.05
    #: 证据组 B:异线资产厚度下限 A_min(浮点;厚度口径=_asset_thickness:
    #: 终局件星级当量)。
    #: 测量协议(冻结池随机厚度基线曲线 f0(a) 的 5% 点,非拍值):池=
    #: w250_delta_pool/snapshot_v11,100 局 planes=2,分母=逐策略决策
    #: 帧(P2+ 段 1341 帧),统计量=「任一异线(除当轮锁定线)厚度 ≥ a」
    #: 的无条件频率;取最小整数 a 使 f0(a)≤5%。
    #: **校准失效披露**:下方实测值(f0(4)=7.68%>5%,
    #: f0(5)=1.27%≤5% → A_min=5)系 C1 删骨架件厚度项**之前**的旧口径
    #: 分布;C1 后度量定义已变,现行值 5.0 不再是现行口径的 5% 分位,
    #: 未按新口径重测——测量协议保留,重测挂「重derive 登记的待办」
    #: A_min 行,重测完成前本值按旧口径校准服役。
    #: 方向单调论证(使「服役偏保守」成证明):C1 只删项,
    #: 任一资产新口径厚度逐点 ≤ 旧口径 ⇒ P_new(≥5) ≤ P_old(≥5)=1.27%
    #: < 5%——新口径下 5 的通过率低于名义 5%,门槛偏严,fail-closed
    #: 门的偏严方向即保守服役。
    #: 对照曲线(任一 v2 线含锁定线/全帧
    #: 口径:f0(4)=3.68%→A_min=4)与逐帧明细的测量记录=行内申报
    #: (主口径取消费面一致的「异线 × P2+ 帧」)。
    #: **分辨力弱声明(设计 R3.1 预案)**:5% 点落在 ≥4 带=证据在本
    #: 牌池分辨力弱的形态,设计预案=如实降级回炉(证据组 A 单独撑或
    #: 换证据形态)——回炉裁决挂 L2 注入分支误开窗占比判据(开窗局新线
    #: 成型 ≥2/3),数据未出前本值按测量结果服役,不调参硬凑。
    revoke_evidence_min_thickness: float = 5.0

    # ===== DirectorV2 备战循环(蓝图 §7/§8;迁移(守卫分区)已完成升正)=====
    #: DirectorV2 接入调用 = 唯一生产路径——无开关 directive(蓝图 §8);
    #: 回退 = git revert。

    # ===== 层4:预算仲裁(约束清单——一处定义,全部候选受约束)=====
    #: 执行约束名序(仲裁器按序施加;filters/arbiter 按名映射实现)
    constraints: tuple[str, ...] = (
        'gold_floor',          # 金≥地板(地板按覆盖态分派)
        'interest_rule',       # [11][17][28] 利息档保持/满息结余
        'bench_capacity',      # bench 9 槽(含本轮已采纳买)
        'copies_cap',          # 同名星级加权 ≤3 份
        'same_round_mutex',    # 同轮已买禁卖/已卖禁买(r408 族)
        'boss_levelup_ban',    # 升级 EV 总账门(名字历史遗留;迁移审计
                               # 起 boss 禁令分支已删,节点无关)
        'deploy_cap',          # 上阵数 ≤ max_units
    )
    #: 地板表(金≥地板;覆盖态分派——审计表 gold 行的消费值)
    war_floor: int = 30           # 战力模式地板(计划内补强非 panic)
    rebirth_floor: int = 20       # [18] 应急保留重生基数
    #: 利息线覆盖通道(纪律视图专用,非标定旋钮):None=用派生利息线;
    #: ALL IN 窗 = 0(唯一清零路径,discipline 裁决视图注入)。
    #: A/B 常量注入面只留 interest_cap 一个旋钮(D3 验收判据)。
    interest_floor_override: int | None = None
    #: boss 轮判定(node_type='boss';P1 r9 兜底同样适用)。迁移审计:
    #: 消费面只剩 boss 窗地板/覆盖态语境(b 类保留)。
    boss_round_node_types: frozenset[str] = frozenset({'boss'})
    #: CwActionLevelUpParam 等级上限(封顶 10)
    level_max: int = 10
    #: bench 槽容量(游戏常数 9)
    bench_capacity: int = 9

    # ===== `w607_affix_consumption/` 词缀消费面三开关(`w628_migration_b2/` 已修复)=====
    # 设计单一源=设计件「词缀消费面」(.debug/temp/currency_war/w607_affix_consumption/DESIGN.md
    # §3);词条语义出处见 cw_comps.STRONG_ENV_MECHS / RUST_AFFIX_NAME 注释;
    # H2②/H3 读端 = kernel 判据消费位(`cw_equip_wear_plan._build_equip_wear_plan`
    # 判据链);原执行器读端已随装备组合壳停用。
    #: H1 环境判据的最小生效轮(位面内轮次,1-based;防位面切换首帧词缀窗口
    #: 误判的观察期)。简报词缀在位面切换即读得(cw_loop 位面简报分支),
    #: 无窗口误判实证,默认 1=判据全程在管辖内;如实机判读发现位面首帧词缀滞后,
    #: 经判读基准标定后上调(标定通道,非人为定死值)。
    line_env_lock_min_round: int = 1
    #: H2②:库藏生锈在场(cw_comps.RUST_AFFIX_NAME ∈ enemy_affixes)时豁免
    #: opening/过渡 hold——每件 owned 滞留=敌 +3%伤/-4%减伤(competitors.md:45),
    #: 滞留的边际代价随件数单调上升,压倒「攒给成型核心」的机会成本。
    #: 行为无条件化(恒 True);单帧测试已闭环、实机基准点预注册
    #: (w607_affix_consumption/AB_REPORT.md 开分支建议节)。
    rust_wear_release_enabled: bool = True
    #: H3:opening hold(P1 r≤2)收窄——仅「当前节点非战斗类」才 hold
    #: (node_type ∈ opening_hold_battle_nodes → 不 hold;r2 战斗节点白板挨打
    #: 病灶,局22 实证)。node_type 缺失(None)维持现状 hold(保守降级:观察
    #: 缺失不改变既有行为,宁缺勿错)。行为无条件化(恒 True),依据同上。
    opening_hold_battle_gate_enabled: bool = True
    #: H3 战斗类节点型名单(词汇表单一源 = 备战帧节点型顶部标签 OCR:
    #: boss/补给/遭遇/巨星/投资/战斗/精英/奖励)。巨星/投资等未知是否战斗
    #: →不入集=维持 hold(保守侧,不猜)。
    opening_hold_battle_nodes: frozenset[str] = frozenset(
        {'战斗', 'boss', '遭遇', '精英'})
    #: H2① 数据层(节):库藏生锈每件滞留的敌方增益份额与
    #: 计件上限,语义出处=competitors.md:45(敌伤 +3%/敌减伤 −4%,最多
    #: 10 件,2026-08-28 游戏内实采)。**只承载账面单一源,无行为分支**——
    #: 第二波数学裁决(证明测试 test_cw_w607_h2o_verdict):每件滞留金当量
    #: = 本份额 × expected_battle_loss × battles_left_est × hp_to_gold
    #: = 0.75(已定案时点历史推导;式中所用旧字段已于 2026-09-04 增量 B
    #: 停用;胜率/伤害折算链已停用(随禁胜率建模链),翻案重评时须按
    #: 路径总账口径全新重算)
    #: < 补给 key_fit 边际 10、< 策划面装备类与升费/弱化的分差 19 →
    #: 现有动作空间无翻转点,H2① 行为分支不合入(无效→不合入,
    #: strategy-work §4 兑换纪律)。重评触发器=该证明测试翻红,或 `w612_effect_inventory/`
    #: 效果清单批落地装备处置/inventory 动作面(届时扣减消费点挂其接口)。
    rust_hoard_damage_share: float = 0.03
    rust_hoard_penalty_cap: int = 10


    # ===== 完备性审计表(对抗修订④)=====
    #: 资源维 × 回合态维矩阵;每格 = constraints 内的约束名,或
    #: ('none',显式声明原因)。「无约束覆盖」必须显式声明,禁止空格。
    #: 检查项 decision_v2_arbiter_matrix 校验「无空格 + 约束名存在」。
    audit_matrix: dict[tuple[str, str], tuple[str, ...] | tuple[str, str]] = field(
        default_factory=lambda: {
            # (资源维,回合态维) → (约束名...) 或 ('none',原因)
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

    def interest_floor(self) -> int:
        """利息线单一源(D3 双源已修复,`w628_migration_b2/`):派生 = interest_cap × 10。

        - 恒等式出处 = `w611_econ_cycle/` §2.2(满息平台 = 封顶档 × 10 金);
          原独立字段 ``interest_floor``(=50)与派生式并存构成双源,标定
          批动 interest_cap 时两源分歧——本方法并入为唯一取值口;
        - 覆盖通道 = ``interest_floor_override``(仅纪律视图 ALL IN 清零,
          非标定旋钮);
        - 消费守卫:除本方法与本类定义处外 ``interest_floor`` 读点 = 0
          (API 契约防线归 review 与代码规范;grep 守卫系测试纪律禁源码
          扫描已停用,勿复活)。
        """
        if self.interest_floor_override is not None:
            return self.interest_floor_override
        return self.interest_cap * 10


#: 默认注册表(首轮标定后;A/B 时构造改动副本注入
#: DecisionV2Strategy)
DEFAULT_REGISTRY = DecisionV2Registry()
