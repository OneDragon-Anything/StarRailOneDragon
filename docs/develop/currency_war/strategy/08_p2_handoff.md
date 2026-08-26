# 08 P2 承接形态/质量模型(设计件,W223)

> **状态声明(违反 as-built 约定的显式豁免)**:本文是**设计件**(W223 任务书:出设计不写实现码),
> 尚未实现。落地时:行为语义迁入本文 as-built 化 + 对应 ADR(why)+ 代码注释引 ADR;
> 未落地的分期节随进度树推进而收缩。判读依据 = W220 双局判读
> (`.debug/temp/currency_war/w220_verdict.md` §4 问题④)+ 进度树 W220 收账行。
>
> 读者 = 无会话历史的智能体。术语:「承接」= 从位面 1(P1)进入位面 2(P2)时,
> 板面/血量/经济/装备这一整套**带入 P2 的资产状态**;「承接质量」= 该状态满足
> P2 存活与后续运营需求的程度。

## 1. 问题(为什么需要这个模型)

两局实证败因同向(W220):

- **run 28**(run_20260826_230940):P1 出口 hp=1(形态 form 0.09、0 引擎、全 1★、装备全 hold)
  → P2-1 普通战斗即被推平(-16)。**带血不足型**:承接的 hp 维度归零,零容错。
- **run 26**(run_20260826_122120):P1 出口 hp=64(双引擎在板、form 1.00,但全 1★、
  过渡核心 2★ 未达)→ P2 p2r4 单轮 46→2(-44)战力断层 → 2-7 首领战败。**板面质量不足型**:
  hp 维度健康,板面质量维度(星级/成型深度)不济,敌强度跳档后断层。

两局是**同一个缺位的两个症状**:P1 出口 hp 与 P2 存活强相关但 P1 无回复机制(掉血不可逆,
[27] B+P 公式),而策略层对「进 P2 时该带什么」(板面形态/等级/金/装备)**没有任何建模**
——P1 的成型判据(form_ok/formed_stop,见 §3.3)是 **P1 语义**(能不能过 P1),不是
**P2 承接语义**(带进 P2 够不够活)。跨件半问裁决(AGENTS.local 根源两问 + W220 收账):
hp<10 保命路径与 P2 战力断层合并为一个架构级缺位,**禁逐个打补丁**。

模型必须让两局败因**都有解释位**(回验判据,§6.4):run 28 命中 hp 维度罚分,
run 26 命中板面质量维度罚分——两局都应被承接质量函数判为「承接差」且可指出差在哪一维。

## 2. 现状盘点(P1→P2 切换时策略层现有钩子)

### 2.1 现有钩子(全部查实,引行号)

| 钩子 | 位置 | 现状语义 |
|---|---|---|
| `on_match_start` | `decision_v2/strategy.py:102-140` | **开局一次**(整局,非位面级):意向/演进/报警/轮簿记全量初始化。**没有 `on_plane_start`——位面切换无对应生命周期钩子**。 |
| `update_target`(意向) | `strategy.py:172-197` → `cw_intention.update_intention`(cw_intention.py:615) | 每轮驱动锁线/撤销。位面感知仅三处:①出 P1 清过渡对(cw_intention.py:624-626,ADR-0357/W166);②P1 配方锁辖 plane==1(cw_intention.py:604);③P3 入口强制锁(cw_intention.py:719)。**P2 入口无任何「评估带入资产」动作**。 |
| `decide_prep` 入口相位派生 | `strategy.py:231-246` → `phase.py derive_phase/form_ok/form_score` | 相位(FORM/HOARD/SPEND)是**派生量**(每轮现算,不落跨轮存储,ADR-0346)。form_ok 是 P1 过渡语义(三件套=locked∧form_tiers∧核心上场 2★;兜底=轮数+有效体系数,phase.py:120+),**不含 hp/金/装备维度,也不区分「P1 内够用」与「带进 P2 够活」**。 |
| P1 成型检查点 | `cw_line_defs.p1_formation_target`(cw_line_defs.py:195-229) | P1 轮窗(3/6/8 边)的渐进成型目标(bridge2→recipe5→recipe7),**纯 P1 轮次语义,轮窗终止于 r8——不延伸到「P1 出口该长成什么样才能承接 P2」**。 |
| P2 段分支(散点) | scoring.py:597-680(V_D P2 段 refresh_budget 口径,ADR-0361)/ arbiter.py:402-450(P2 核心首件门,ADR-0378)/ remediation.py:457-481(P2+ 多击组)/ ev.py:109-145(battles_left_p2)/ discipline.py:628-647(nodes_of_plane 位面末窗,ADR-0366) | **全部是「已在 P2 内」的行为分支**,前提隐含「承接态已定」;没有一处回答「P1 末期该为承接做什么」。 |
| 掉血三臂/报警 | `decision_v2/discipline.py`(ADR-0313) | hp 低=运营质量报警(梯度:自然窗→弃息 D→位面末 ALL IN)。**位面末 ALL IN 的「位面末」语义已有(ADR-0366 后 P2=7 轮判正),但 P1 末战(1-9 boss)前的决策没有「这一战赢了之后带什么进 P2」的账**——三臂的账只算到本位面末([18]:位面末最后一战是损失最小的 ALL IN 时机),承接维度缺失正是 [18]「板面与血量带进下位面」前半句的未建模部分。 |

### 2.2 结论

P1→P2 切换在策略层是**被动继承**:sim 侧显式建模了「进场继承块」(cw_sim.py:1312-1338:
P1 末态 hp/gold/board/bench/deployed/equips/意向原样带过),生产侧等价于状态天然延续。
策略层对「带入什么」的唯一主动影响 = P1 全程决策的副产品。**缺的不是执行机构,
是一张「出口判据的账」**:P1 末期(r8-r9 boss 窗)的花钱决策没有把「承接质量」计入期望。

## 3. 数据面盘点(P2 承接质量的可观测指标)

### 3.1 现有遥测能支撑什么(判读报告 + cw_telemetry 实查)

- **decisions/rounds 视图带 plane 键**(cw_telemetry.py:991-1023,join 键含 plane;
  rounds 取每轮 actions 最多行):P2 逐轮 hp/gold/board/level 可查——run 26 判读即由此
  得出 p2r4 46→2 断层与金轨迹 75→40。
- **outcomes/runs.jsonl**:`plane_reached/final_hp/result`(run 26=stopped plane 2 hp 1;
  run 28=loss plane 2 hp 0)。
- **sim 侧 P2 观测族已存在**(cw_sim.py:389-408,ADR-0362/0377/W183):`p2_entered/
  p2_rounds/p2_combat_total/p2_combat_wins/p2_hp0/p2_refreshes` + W183 判读族
  `p2_gold_carried/p2_buys_by_cost/p2_switch_events/p2_lv6_round/p2_lv7_round` +
  账本 `sim.p2_win_p` 披露。**承接质量指标在 sim 侧的数据管道基本齐备,缺的是 P1 出口时点的快照字段**。
- **P2 战斗存活层已参数化**(ADR-0377):`win_p = clip(p0 + β·form − γ·drift)`,
  form=engines(deployed)+level 折算——**结算侧已有「板面质量→存活」的响应函数**,
  真值分帧校准过(41 run 对拍带内全过)。这是承接质量模型最直接的验证/标定基座。
- **已知缺口**(W220 §4 ①):`decisions.state.equips` 两局恒空(落盘链未穿透,
  W222 已派修复)——装备维度指标在修复落地前只能靠日志 grant 行,**分期上装备维度放后**。

### 3.2 承接质量指标候选(向量定义,Phase 0 全部落快照)

P1 出口时点(P2 r1 首次决策前,即 sim 进场继承块后/生产 P2 首轮 decide_prep 入口):

| 维度 | 指标 | 现有数据源 | 备注 |
|---|---|---|---|
| 血量 | `handoff_hp`(出口 hp) | rounds/outcomes | run 28 型的判别维;run 26 证 hp 单维不够 |
| 板面形态 | `handoff_engines`(deployed 体系数,`_engines_count` 单一源)、`handoff_form_score` | sim 账本 / 生产 form_score 遥测 | run 26 型的主判别维 |
| 星级深度 | `handoff_core2_count`(核心/体系件 star≥2 计数)、`handoff_star_sum` | board 快照 | run 26 全 1★ = 此维归零的实证 |
| 等级/人口 | `handoff_level`、`handoff_deployed_n`(上场数 vs cap) | state | ADR-0377 form 的 level 分量同源 |
| 经济 | `handoff_gold`(出口金) | rounds | [28] 表征维(非独立目标) |
| 锁线形态 | `handoff_locked`(进 P2 时意向 phase/locked_comp)、`handoff_hoard_n` | decisions tracks | 散局(run 28 型 P1 未锁)承接口径不同 |
| 装备 | `handoff_equips_n`(穿着数) | **W222 修复后**可用 | 分期后置 |

## 4. 设计:「P2 承接质量模型」架构

### 4.1 承接质量的定义(可验收判据)

**定义**:承接质量 = P1 出口快照向量经**分档评分**得到的档位,分档判据与 P2 存活outcome
挂钩标定(不是手拍阈值)。

**「承接好」的可验收判据(量化)**:

1. **区分度判据(标定)**:按承接档位分层,P2 存活指标(hp0 率 / 存活轮数 / p2_combat_wins)
   随档位**单调**(高档位严格不差于低档位)——在两个数据面各验一遍:
   - sim:planes=2 批(ADR-0362/0377 校准层,truth_bands.json 真值带);
   - 实机:21 run P2 语料(w193_p2sim)+ 后续新增局。
   单调性破坏 = 档位切点错,回炉重标定(三滤网第 1 滤:数学/数据答,不问用户)。
2. **回验判据(两局败因解释位)**:run 28 快照 → hp 维罚分档(其余维也差,但 hp=1 是
   独立可指认的归零维);run 26 快照 → hp 维健康、星级/成型深度维罚分档。**两局都必须
   被模型判为「承接不足」且可指出主罚维**——做不到 = 维度定义漏了,回去补 §3.2。
3. **干预判据(Phase 1 起的 A/B 验收)**:承接门生效臂 vs 基线臂(同池同 seed 配对,
   `simulate_p2_ab` 口径,ADR-0362 §③):P2 hp0 率下降 / 存活轮数上移,且 **P1 段零漂移门
   逐位一致**(改动只辖 P1 末窗的期望账,不改 P1 早中期行为)。

**反验收(防止重蹈「单优化出口金假达标」,[28] 病例)**:承接质量不是新的单指标——
**禁止**直接优化「承接分」数值本身(会复刻金 92 板面弱的镜像病:板面刷分不守息)。
它只作**门控/期望账的输入**,验收永远是 outcome 端(P2 存活/通关分布)。

### 4.2 模型挂哪(结构裁决)

三层递进,**观测先行**(ADR-0346 影子模式的成功先例:phase 先影子观测一期、
切授权在证据到位后独立成批):

- **Phase 0(观测层,零行为)**:新纯函数 `handoff_snapshot(state, session) -> HandoffSnapshot`
  (dataclass,§3.2 向量 + 派生档位)。挂载点 = P2 首轮 `decide_prep` 入口
  (strategy.py:231 相位派生同址,plane==2 且本位面首轮时算一次写
  `session.v3_handoff`)——与 phase 同型:**派生量、不落跨轮存储、天然免疫 session 丢失**。
  sim 侧同函数在进场继承块(cw_sim.py:1312-1338)后采样,进 SimResult
  (`p2_handoff_*` 字段族,与 p2_gold_carried 同批披露)。生产侧进 decisions 遥测行。
- **Phase 1(门控层,P1 末窗承接账)**:承接档位作为 **P1 r8-r9(boss 窗)花钱期望的
  门槛输入**——具体挂载点两个,均为既有接口、零新层:
  a. **formed_stop 消费面**(filters,ADR-0343):成型停手线的谓词族加承接维
     (现谓词=form_ok,是 P1 语义;承接未达标 → 不停手,继续投资);
  b. **boss 窗期望账**(arbiter/ev 既有授权通道):P1 末轮花钱的 EV 账
     (ADR-0347 EV 授权框架)加「承接缺口项」——缺口大 → 末窗破息投资的授权阈值
     放宽([18] 位面末 ALL IN 语义的承接扩展;[19] 三态谱的裁决变量④)。
- **Phase 2(姿态层,P2 早期)**:承接快照作 P2 r1-r2 姿态输入——质量差 → V_D
  refresh_budget/scoring P2 段口径(scoring.py:597-680)的参数向「补强优先」偏置;
  质量好 → 守息正常走。**不新建通道,偏置系数进 registry(A/B 可注入)**。
- **Phase 3(终局整合)**:hp<10 保命路径(run 28 型)收编——P1 末 hp 报警梯度
  (ADR-0313 三臂)与承接门**合账**:hp 低 + 承接差 = [18]「位面末最后一战是损失最小
  的 ALL IN 时机」的显式实现(末战 ALL IN 换当轮战力,[32](a) 当轮转化判据);
  hp 低 + 承接好 = 正常打。至此 W220 问题④的两个症状(保命路径/战力断层)在同一个
  模型里闭合,不再有独立补丁位。

**裁决:不做的事**——不建独立「phase machine」(ADR-0336 删相位机的教训:模式判定
由派生量承载);不给承接分做全局评分权重(评分表 score_all 不动,防「刷分病」);
不预测 P2 敌方具体强度(核心哲学 1:观测驱动——P2 敌强度跳档是已知机制事实,
由档位标定吸收,不建预测器)。

### 4.3 与既有体系的关系(接口查实,不推翻)

| 体系 | 接口 | 关系 |
|---|---|---|
| 意向/锁线(cw_intention) | `update_intention` 位面感知点(cw_intention.py:624-626 出 P1 清过渡对) | **不动状态机**。承接快照只读 `ist.phase/locked_comp/hoard`(§3.2 锁线形态维);Phase 1 不改锁线语义(承接差 ≠ 换线,[23] 锁定不 pivot)。 |
| 四体系过渡(transition_combos/cw_bridge_pool/cw_line_defs) | `p1_formation_target` 轮窗(cw_line_defs.py:195)、`fallback_engines_count`(phase.py:92) | **同向加强不替代**:成型检查点管「P1 内渐进成型」,承接门管「出口够不够」——出口判据复用同一批单一源计数器(`_engines_count`/`core_trio_count`),不建第二套形态表(防双源)。 |
| 经济循环总模型(ADR-0346/0347/0349 相位+EV) | `derive_phase`/`dp_posture`/EV 授权通道 | **承接门是 EV 账的一项新增输入**,不是新授权通道——Phase 1b 的「承接缺口项」进 ev 既有授权框架(与 [33] 人口位/DP 花费授权同层并列),授权 trace 入执行 log 同款。 |
| 相位体系(phase.py) | 派生量模式(每轮现算、写 session、遥测披露) | Phase 0 完全同型(影子→切授权两步走,ADR-0346→0347 的路径复刻)。 |
| 掉血三臂(discipline,ADR-0313) | `assess_discipline` 覆盖序 | Phase 3 才接触;合账方向=三臂的位面末 ALL IN 臂加承接条件变量,**不改报警梯度本身**([18] hp 低=报警语义不动)。 |
| sim/校准层(ADR-0362/0377) | `simulate_p1(planes=2)` 进场继承块(cw_sim.py:1312-1338)、`simulate_p2_ab`、truth_bands | 验证基座(§4.4);sim 侧唯一改动=进场后采样快照进 SimResult(观测字段,零漂移)。 |
| 遥测(cw_telemetry) | decisions 行 state 族、SimResult 字段族 | Phase 0 双侧落字段(生产 decisions + sim 账本),判读 CLI 视图后续按需加 view(纪律:别为复盘写一次性脚本,新需求=新视图)。 |

### 4.4 sim 验证路径(planes=2 采样能支撑什么)

已可支撑(零 sim 基建改动):

1. **标定对照**:planes=2 批 + invest 注入(ADR-0364)跑 n≥300,按 Phase 0 快照字段分层,
   验 §4.1 区分度判据(档位×P2 存活单调性);β/γ 敏感性网格(ADR-0377 §⑤裁决口径)
   复用于「单调性是否参数敏感」——端点一致翻正才裁分布级。
2. **A/B 配对**:Phase 1/2 每期改动走 `simulate_p2_ab` 同池同 seed 配对
   (ADR-0362 §③口径),P1 零漂移门(fallback n=20 逐 seed diff={})每批必附。
3. **案 b 臂交叉校验**(`simulate_p2_replay_entry`+P2ReplayEntry,ADR-0377):真值进场态
   直接跑 P2 段——Phase 0 快照函数可对 21 run 真值语料**离线回放计算**(快照是纯函数,
   喂历史 outcomes 重建态即可),回验判据(run 26/28)在此落地,不等新实机局。

不能支撑(边界声明):装备维度快照在 W222 落地前 sim 有建模但生产读不到
(§3.2 备注);P2 刷新实价仍无实机样本(W220 §1 标定缺口),经济维偏置(Phase 2)
的实机外推力受限——结论声明数据边界。

## 5. 分期(最小可验的第一步 ≤1 批)

| 期 | 内容 | 批量级 | 验收 |
|---|---|---|---|
| **Phase 0** | `handoff_snapshot` 纯函数 + sim/生产双侧观测字段 + 21 run 真值离线回放标定档位 | 1 批 | §4.1 判据 1(单调)+ 判据 2(run26/28 回验);P1 零漂移门;新单帧锁(快照字段/档位边界例) |
| Phase 1 | formed_stop 承接维 + EV 承接缺口项(A/B flag,registry 注入) | 1-2 批 | §4.1 判据 3(hp0 率↓/存活轮↑配对);P1 零漂移;行为变更三同步 |
| Phase 2 | P2 早期姿态偏置(V_D 参数偏置,registry A/B) | 1 批 | 同上配对口径;敏感性端点一致 |
| Phase 3 | hp<10 保命路径收编(三臂合账) | 1 批 | run 28 型构造局单帧锁 + sim 分层对照 |

第一步(Phase 0)= 纯观测 + 离线标定,**≤1 批可落地**,且它本身独立交付价值
(判读面:以后每局 P2 段判读先看承接档位,判读三问之外的第 4 问素材)。

## 6. 结论核对(任务合格线)

1. ☑ 承接质量定义可验收(§4.1 三判据 + 反验收条款,全部量化)。
2. ☑ 既有体系接口查实(§2.1/§4.3,行号亲核)。
3. ☑ 两局败因解释位(§4.1 判据 2,run 28=hp 维 / run 26=星级深度维,Phase 0 回验)。
4. ☑ 分期第一步 ≤1 批(Phase 0)。
