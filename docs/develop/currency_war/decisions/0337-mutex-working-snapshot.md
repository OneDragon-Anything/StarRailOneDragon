# ADR-0337:no_same 双快照互斥窗口修复(same_round_mutex 快照源对齐 working)

- 状态:accepted(W82 批)
- 日期:2026-08-25
- 决策:见下「决策」节;正文落点 = `decision_v2/arbiter.py`
  (`_check_constraint` 的 `same_round_mutex` SellBench 分支)。
  W81 全窗复验(ADR-0336 AD8 条件①)钉死的新机制补丁——ADR-0328
  的既有修复(登记点=采纳处 + 执行域对齐)未覆盖的残留窗口。

## 背景(现象与根因)

W81 全窗复验(seeds 0-399,pool snapshot 46066bbe):ADR-0328 修复后
0-99 段归零,但 **100-399 段仍有 3/300 no_same 违规**(seeds 259/304/
342,点估计 1.0%,95% CI [0.34%, 2.90%];oscillation 全窗 0——3 个
违规无 XP 获益伴随,与 W66 时「osc 20/20 全为 no_same 子集」不同)。

**机制(探针钉死,3/3 同根)**——双快照窗口:

1. 演进 CompTransaction(decide_prep ②前置已采纳动作)腾空 bench 槽
   idx → `exec_state.bench[idx]=None`;
2. 同趟 arbitrate 内先采纳 BuyCard X(分高),`simulate(working,…)` 把
   X 落入该空槽 → `working.bench[idx]=X`;
3. `same_round_mutex` 守卫的 SellBench 分支读 **state**(exec_state)
   槽位 = None → `_bc is None` → 短路跳过 → **放行**;
4. `index_drift` 守卫读 **working** 槽位 = X,与候选 intended(原始态
   槽名 X)同名 → **放行**;
5. SellBench(idx) 执行 → 实卖刚买的同名卡 X → 账本转录「BUY X →
   SELL X」→ no_same 违规(实卖刚买卡,非名义违规)。

**根在哪一层**:流程层——`same_round_mutex` 与 `index_drift` 两个守卫
读**两个不同快照**(mutex 读 exec_state、index_drift 读 working)。ADR-
0328 的执行域对齐只修了「working 初始化源」(exec_state 传入),但
mutex 的槽位读取仍停留在 `state`(exec_state 快照)——当演进腾空槽且
同趟买入落该槽时,守卫链出现漏缝。r408 的观测域(卖动作执行时的真实
目标卡)与守卫读取的观测点不一致。

## 决策

`same_round_mutex` 的 SellBench 分支槽位读取从 `state.bench[idx]`
改为 **`working.bench[idx]`**(与 index_drift 同快照源):

- r408 语义 = 「同轮已买禁卖」,卖动作执行时**真正卖出的卡** =
  `working.bench[idx]`(index_drift 已保证 working 槽 == intended;
  卖是该槽在 arbitrate 内最后一次被触碰)——守卫按执行目标卡裁决,
  而非 pre-arbitrate 快照;
- 双快照窗口结构性关闭:演进腾空槽后,同趟买入同名卡落槽时,新守卫
  读 working 槽 = X ∈ `v2_round_bought`(采纳即登记,ADR-0328)→ 拒卖。
- 不变量不变(r408 语义在趟内完整):同趟内买过的名字不可卖、卖过的
  名字不可买;SellBench 执行时槽位内容与提案一致(index_drift 保持)。

## Considered Options

- **A. mutex 改读 working 槽位(采纳)**:与 index_drift 同快照源,
  一行改读、零新机制;「买后复核」天然由候选按分序评估 + working 逐
  采纳推进实现。安全性已推演:对**已接受的卖**,working.bench[idx].
  char_id ≡ state.bench[idx].char_id(证明:working 从 exec_state 初始
  化,仅被采纳动作改槽;BuyCard 落槽同名 → ∈bought → 新守卫拒;
  DeployMove/卖/Synthesize 腾空槽 → index_drift 拒;Synthesize 保留
  同名 → char_id 不变),故 `_register_accepted`(SellBench 分支仍读
  state)登记名与执行名一致,无新漂移。
- **B. 采纳 BuyCard 后对同槽 SellBench 候选补 working 态复核**:被
  A 吸收(读 working 天然实现「买后复核」);B 需额外机制(回退已采纳
  卖/槽标记),无增益——否决。
- **C. arbitrate 候选补 `expect` 字段(执行侧 stale_proposal 兜底)**:
  与 remediation 同式,执行期槽位不符 → no-op。症状修法:决策层仍
  「接受」卖、arbiter log 误导;r408 不变量应在决策层成立(防「log
  接受但执行 no-op」的双层语义分裂)——否决。
- **D. exec_state 槽 None 即拒卖**:覆盖面窄(只挡腾空槽情形;
  working 落不同名卡已被 index_drift 挡);绕开 bought 集机制,
  语义不如 A 正——否决。

## 影响面

- 行为变化清单:
  - 双快照窗口:演进腾空槽 + 同趟买入同名落槽 → SellBench 被
    「同轮已买」拒(不再实卖刚买卡)——**意图内**(本修复目标,
    W81 3/300 违规消除)。
  - 其余正常卖路径(槽未被采纳动作改动):mutex 读 working == 读
    state,裁决不变——**无变化**。
  - remediation 补偿卖件:两补偿器已有「working 占用守卫」
    (remediation.py `wb.char_id != b.char_id → continue`),补偿卖件
    working 槽 ≡ state 槽,mutex 改读 working 不改变其裁决——
    **无变化**。
  - ADR-0276 检查侧豁免(engine_seed ≥2 / copy 3合1 语境):检查级
    豁免只管账本报告;决策层 mutex 对「卖刚买同名卡」的拒绝语义
    本就存在(现行 mutex 对 exec_state 槽 == X ∈ bought 同样拒),
    本修复只补腾空槽回填的漏缝,不新增拒绝面——**无变化**。
  - headline 三件套(avg_final_hp / hp_ge_60):被拒卖卡不再被误卖,
    金/板面/经验路径微动——sim 全窗复核如实报。
- 测试:新增 `test_cw_adr0337_mutex_working_snapshot.py`(三锁:
  双快照不一致态拒卖 / 去登记变异涌现违规[守卫=唯一闸门] /
  W81 违规 seed 259/304/342 确定性重放零违规);ADR-0328 六锁
  保持绿(131 受影响域锁全绿)。

## 与既有文档的关系

- ADR-0328(r408 时序缺口修复):本 ADR 是其补丁——登记点前移 +
  执行域对齐之后,守卫**槽位读取**的快照源仍未对齐(index_drift 已
  读 working,mutex 仍读 state),本 ADR 闭合该漏缝。
- W67 报告「no_same 归零」叙述修正:仅对 seeds 0-99 成立(其池
  6c0c8397 下);100-399 段残留由本批修复并全窗复核(数字见报告)。
- strategy as-built 03_tactics.md「同轮买卖互斥」段同步守卫快照源
  语义(ADR-0337 指针);代码注释引 ADR-0337(arbiter.py
  `same_round_mutex`)。
