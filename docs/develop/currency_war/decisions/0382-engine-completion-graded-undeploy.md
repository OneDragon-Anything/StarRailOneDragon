# 0382 — 补完保护集分级(136 型构造闭死修法:缺口持续门 + 分级降级换血)

- 日期: 2026-09-01
- 状态: accepted (采纳)
- 关联: ADR-0371(补完守卫——本批修其「全保护即闭死」的边界)、ADR-0381(W201 修法①②——本批为其记档的③)、W200(证据基准:136 型 undeploy 全保护 ×4)、W201(A/B 锚:never2 10/mal 24)、ADR-0363/0375(「补上不是拆」/希儿系辖域——分级序的不可动级依据)、ADR-0374(A/B 硬门否决与回退模式)
- 批: W202

## 背景与问题

W200 发现 136 型构造闭死:列车缺口 r6-r9 轮轮被选但 `_engine_completion_tx`
永远建不出——room 1、需上 2、deployed 五件全在保护集(黑塔/翡翠/阮·梅=
锁定线件,艾丝妲/椒丘=DOT 引擎件),undeploy 候选 0。W201 修①② 后锚
never2 10/mal 24,136 仍在名单内。W200 建议保护集分级「独立批先 A/B」。

W202 判读先行(形态分布扫描,同池 n=300,只读诊断包装 `_engine_completion_tx`):
- undeploy 全保护点出现在 **91/300 局**——远比 W200 单局归因常见;但绝大多数
  是**暂时性缺口**(单轮多决策点重复计,之后经常规通道自愈,seed 9 持续 6 轮
  仍健康终局);
- 按缺口持续性分桶:同体系连续 ≥2 轮 34 局 / ≥3 轮 18 局 / ≥4 轮 12 局;
  never2 ∩ 持续 ≥2 轮 = 5 局(68/136/144/230/293);
- 结论:136 型是策略权衡级(换下锁定线件可能伤锁定 comp 战力),但代价面
  (91 局的板面扰动)决定了**必须窄门**——「缺口持续」是把激活面收窄到
  持续闭死态的自然判据。

## 决策

**保护集分级降级换血**(flag `registry.engine_complete_grade_down`,
默认开,关=逐位回 ADR-0371/0381 后「不硬拆」语义):

1. **持续门**(`_GRADE_PERSIST_ROUNDS`=4):同一缺口体系同位面连续被选中
   ≥4 轮(`EvolutionState.completion_deficit` 追踪,键=体系,值=
   (plane, first_round, last_round);间隔 >1 轮断档或换位面重置)才允许
   降级——标定:门=2 → never2 10→5/mal 24→22 但 **benign→mal=[65,119,172]**
   3 局坏翻转;门=3 → benign→mal=[119] 残留;**门=4 → 全硬门过**
   (benign→mal=0/mal 24→20/never2 10→7)。形态学依据:136 缺口持续
   r6-r9 共 4 轮,门=4 恰覆盖「轮轮被选仍建不出」的闭死长度。
2. **分级序**(`_graded_undeploy_cands`,依据 [13]/[23]/[31] 口述):
   - **G0 非引擎锁定线件**(最可动):`locked_buy_scope` ∩ 非 TT 引擎件
     (全羁绊 ∩ TRANSITION_TRAITS 为空)——锁定线的填充件,换下只伤锁定
     comp 即时战力,不伤任何引擎。p1_pair-only 配方帧该级恒空
     (buy_scope=pair 成员=被补体系自己),G0 只在 locked_comp 帧生效——
     与 136 实况吻合(黑塔/翡翠=大黑塔线采购件);
   - **G1 未成型引擎件**(中档):引擎件但其全部引擎体系当前未成型
     (on-board < tier,`_engine_systems_formed` 判)——下之不拆任何已
     成型引擎,只是延缓该体系;
   - **G2 已成型引擎件恒不可动**(下了即拆引擎,违反 ADR-0363/0371
     「补上不是拆」不变量);pair 成员/希儿系贡献件(W192 核心条件辖)/
     未识别件同样恒不可动(原保护语义保留)。
   级内弱序 = 星级 → 费用(低星低费先下,与常规候选同序)。
3. 触发条件:常规 undeploy 候选枯竭 ∧ 门过 ∧ flag 开;任一不满足回
   「不硬拆,归常规通道」。

## Considered Options

- **零修法记档(W200 ④ 方向)**:拒为首选——形态扫描把代价面摸清后
  (91 局触碰但持续 ≥4 轮仅 12 局),持续门使激活面足够窄,A/B 门值
  标定出现全过硬门的配置(门=4);且 never2 残差中 5 局与持续缺口重合,
  是「拥有已够、轮轮想上、结构上永远上不去」的最典型 own-gap 形态。
- **门=2/3(更宽激活面)**:A/B 否决——benign→mal 坏翻转(65/119/172/
  119)违反硬门「任一恶化即回退」;宽度换来的额外治愈(68/144)被
  坏翻转抵消,收窄到门=4 后翻转清零。
- **无门直接分级(凡枯竭即降级)**:即门=1,比门=2 更宽,同族否决;
  91 局的暂时性缺口全部被激活,扰动面最大。
- **swap 语义(deploy 与 undeploy 原子对调,bench 容量不占)**:越界——
  CompTransaction 无 swap 动作类型,引入新动作类型改动执行层契约
  (cw_state/sim 双消费面),且 136 型 bench 容量本就够,分级 undeploy
  已闭合,不为未来形态预付契约成本。
- **G0 含 pair 成员(p1_pair-only 帧也能降级)**:拒——pair 成员=被补
  体系自己的件,下 A 补 B 在构造上自相矛盾(补完的目标就是把这些件
  送上场);p1_pair-only 帧缺口持续时走 G1(未成型引擎件)通道。
- **sell 腾位放宽(W200 ④,99 型)**:维持 W201 记档不修——单局,
  sell_insufficient 形态在本批 A/B 中零恶化,边际。

## 验证

- 新单帧锁 5(`test_cw_w202_grade_down.py`):主锁(locked_comp 帧
  全保护 + 缺口持续门值轮 → G0 最弱件被换下、列车 ob 达 tier、G2
  成型引擎件不动)/持续门首遇不降级/flag off 逐位回退/断档重置
  /registry 默认与 evolution_step 注入链。
- 既有锁:W174 8 邻锁全绿(保护序主锁不回归——G2/pair 不可动保持);
  W35 接线锁随参扩展(+grade_down 断言);0293 registry hash 锁同步
  (新 hash 1be534f9…)。
- sim A/B n=300(同池 861fc9f6 导出件重放,seeds 0-299,invest on,
  A 臂=grade_down off 精确复现锚 never2 名单逐位/mal 24):never2
  10→7(136/230/293 脱离,68/144 留=缺口持续 <4 轮,门收窄的已知
  代价)、mal 24→20(mal→benign=[136,230,282,293])、**benign→mal=0**、
  出口金 31.35→31.57(带内)、final_hp 持平——数字见 W202 报告
  (`.debug/temp/currency_war/cw_dev/deep_read/W202_报告.md`)。
- 门值标定三跑(门=2/3/4)全记录于 W202 报告,门=2/3 的坏翻转
  局明细(65/119/172)如实记档。

## 影响

- cw_evolution(`_GRADE_PERSIST_ROUNDS` 常量、`EvolutionState.
  completion_deficit` 字段、`_weak_piece_key`/`_graded_undeploy_cands`
  helper、`_engine_completion_tx` +grade_down/deficit_memory 参与
  分级分支、`evolution_step` +grade_down 透传)、
  decision_v2/registry(`engine_complete_grade_down`)、
  decision_v2/strategy(注入一行)。
- ADR-0371 的「腾不出 → None(不硬拆)」边界由本批修订(持续缺口
  下分级降级);strategy/02_comp.md §10 同步;W200 记档的 136 型
  修法③收口,99 型(sell 腾位)维持记档。
