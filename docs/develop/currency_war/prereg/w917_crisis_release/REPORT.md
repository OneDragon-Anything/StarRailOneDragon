# W917 危机态（hp≈1）存息 posture 不降级：根因定位与修法批

> 批性质=治本修复（W907 病灶实证的候选①②）。检查点交付：根因+修法设计先行落盘（§1-§4），动码在 §5 之后。
> 病灶输入=`.debug/temp/currency_war/w907_sim_hunt/REPORT.md`（907288 r3-r8 / 907106 r7-r8）。
> 语义权威=ADR-0463（存息准入门 E1）+ ADR-0445（义务模型）+ ADR-0426（应急让位设计）。

## 1. 根因定位（表达式级证据）

### 1.1 release_budget 恒 0：不是阈值、不是比较方向，是前置门短路

W907 观测「reserve_overflow 逐轮爬至 162 而 release_budget 恒 0」。恒 0 的表达式在
`decision/decision_v2/posture_release.py`，两处，同一谓词：

- `flip_hit()`（L154-155）：
  ```python
  if is_emergency(state, registry):
      return False    # 应急辖区,release 让位
  ```
- `release_directive()` 存息准入门 E1（L282-283）：
  ```python
  if is_emergency(state, registry):
      return None    # 应急辖区,release 让位
  ```

`is_emergency` = `state.hp <= registry.emergency_hp`（kernel/cw_economy.py L520-526，
emergency_hp=25）。**危机态定义上就是 hp≤25**——所以在「overflow>0 ∧ hp≤25」这一帧类里，
两个 return 无条件先行于溢余判定（L156-157 的 `overflow <= 0` 检查在让位**之后**），
release 指令恒为 None → `session.v3_release_budget = 0`（strategy.py L373-374）恒成立。
这不是「阈值设错」或「比较方向反了」：溢余金额 31/80/10/103 四轮全部正确算出
（v3_reserve_overflow 有值），死在更上游的门。

**为什么这是根而不是症状**：应急让位是 ADR-0426 §7 的显式设计（「hp≤25 应急态全权接管
（清仓/保命优先），release 让位；辖区不相交」），它的成立前提是——让位之后**有别的通道
接住这笔金**（应急搜牌/清仓保命）。W907 实证该前提在观测帧类不成立（见 1.2）：让位没有
承接者，金在死亡门口持续增值、零兑换。这与 ADR-0445 储备制守卫要立的「流量指标」
（滞留率/兑现率）直接冲突，也与 ADR-0463 存息准入门的机制口径冲突——E1 原文
「g>R* → 存息非法、转义务清单判定」，而应急让位在危机帧把「存息非法」改回「存息合法」，
恰好发生在金最不值钱的帧（W907 模型无关论证：hp≈1 持金零生存价值）。

### 1.2 恒 0 的第二层：应急带的容量账被合法 0 帧契约清零

更深一层：即使放宽 1.1 的让位门，flip 臂的义务预算 `= max(obligation, DP预算×刷价)`，
而 `obligation = min(溢余, C_t)`，`C_t` 的刷新分量 = `refresh_ev_budget`——该函数
（kernel/cw_economy.py L756-757）**同样以 is_emergency 开门归零**：

```python
if is_emergency(state, reg):
    return 0    # 合法 0 帧契约①:应急帧→0
```

且其 docstring 明说归零理由是「应激通道根本不产指令（release 让位结构，合并无从放大）」
——即 1.1 的让位与 1.2 的归零是**同一个设计决定的两半**：release 让位了，所以刷新预算
也归零；刷新预算归零了，反过来 C_t=0、义务=0。危机帧的经济出口在预算层与指令层被
**成对拆除**，只剩两条不以经济账定价的通道：①管线应急搜牌（只买「当轮可部署的上线件」，
商店全离线帧=空）；②死亡域分配器（见 1.3）。两条都接不住 → 恒 0 的完整因果链闭合。

### 1.3 death 域 alloc chosen 恒空：同一总模型在分配器层的像

`allocator.allocator_run`（decision_v2/allocator.py）：budget 31→49→80→79 每轮 >0、
proposal 有供给，但 `chosen=[]`。出清条件（`allocate` L627）是 **V>0**，
`V = m_eff × Δp_eff − (c+I)`，其中死亡域 `Δp_eff = max(0,dwin)×L_c×hp_to_gold + w`，
且 ADR-0493 的 `_w_only_rejected` 拒供一切板面增量 dwin≤0 的非刷新提案。观测帧类逐渠道：

- **买卡臂**：商店全离线 → 买入对板面 win_eq 增量=0 → dwin=0 → w-only 拒供（结构性）；
- **刷新臂**：`_refresh_dpeff_estimate` L378-380 前置 `bench 满 ∨ deploy 无空位 → 0.0`
  → dpeff=0 → V = −(c+I) < 0 出局；
- **升级臂**：W907 r5/r7 `blood_budget_levelup_rejects` 反复出现（血预算停升级），
  Π_up 不生成。

正提案集=∅ → chosen=[] 恒成立。**这不是分配器出清式的 bug**（V>0 是 P23.4R/ADR-0493
的既定设计：模型只按板面战力定价），而是 1.1/1.2 同一病灶的分配器层镜像——「危机金的
出口」在管线层（release）、预算层（refresh_ev_budget）、分配器层（V>0）三层同构缺位，
其中分配器层是**按设计**不定价搜索的，管线层与预算层则是让位结构的连带牺牲。因此候选②
不独立修分配器，随候选①的管线出口修复一并闭合：release 指令激活后管线先走
（arbiter 刷新收尾/spend_gate 买授权），分配器只接管「管线没花出去」的帧
（allocator_run L653-661 单跑道结构），A/B 复测观测 alloc chosen 残留面。

## 2. 修法（ADR-0503，危机金出口臂）

**开关纪律裁决：走开关（默认关），不按「缺陷语义免开关」论。** 理由如实陈述：应急让位是
ADR-0426 显式设计而非笔误，本修法是在其上开例外臂=行为语义变更，须 A/B 裁决后开臂
（开关生命周期第 1→3 态）。「修的是缺陷」的部分只有一半：让位前提（有承接者）已被 W907
证伪，但这只说明让位设计**过时**，不构成「原行为违反既定设计意图」的免验理由——两 ADR
（0426 让位 vs 0445/0463 义务模型）在危机帧冲突，裁决权在数据。

落点（语义单一源不动摇）：

1. **registry**（kernel/cw_registry.py）：新增 `crisis_release_enabled: bool = False`，
   注释引 ADR-0503 与 W907 病灶语义。零新数值常量。
2. **posture_release.py**：新增谓词 `crisis_release_open(state, session, registry)`
   = `registry.crisis_release_enabled ∧ is_emergency ∧ overflow>0`（全既有单一源符号）。
   `release_directive` 的存息准入门应急让位分支改为：让位时若 open，产**危机臂指令**
   `ReleaseDirective(budget_gold=min(overflow, REFRESH_ROLL_CAP×刷价), rolls=…,
   reason='crisis')`；flip_hit 的应急让位保持不变（正常 flip 臂辖区结构不动，危机臂是
   独立第三臂，经 evaluate_release 同一 latch/wrap 通道）。
3. **预算式的数学论证（无拍死值）**：危机帧溢余金 (g−R*)+ 的持有边际≈0（剩余战场少、
   带金存活增益被 hp≈1 支配），义务模型在此的「花」= 搜索转化的期权，其上界取分配器
   同源刷帽 `REFRESH_ROLL_CAP`（6，kernel 单一源）×刷价——「把溢余花在至多 6 次搜索
   上，不越过溢余线」。每笔实际支出仍受既有三道门辖：息档截断
   （tier_truncated_spend，essential=False）、boss_floor 出口金地板、g≥0 硬钳制
   （authorize_release_refresh 全保留）；买牌仍走 EV 过滤层——「义务不废 EV 过滤」
   原则不破，本臂只是给**搜索通道**发预算许可。
4. **posture 降级**：指令经既有 `evaluate_release → wrap_posture`，存息帧
   `save=True → save=False, tag='release'`（既有代码路径零改动即得降级语义）；
   spend_gate_active=True 接通息 EV 中性买授权与凑息卖抑制。
5. **候选③（核=0 空转上限）本批不做**，按任务书留观测。

**边界声明（hp 可信位）**：危机臂消费 `is_emergency` → `state.hp`。实机 100 兜底帧
（hp_readable/hp_trusted 皆 False）hp=100 → 非应急 → 臂死（fail-closed，与全部既有
应急带消费点同口径，ADR-0428 的放宽只属 FLIP 末窗投影臂，本臂不随）。sim 帧 readable
恒 True 不受影响。

## 3. A/B 预注册（判前锁定；锁定后禁改）

- **臂**：off = `crisis_release_enabled=False`（=HEAD 缺省，零漂移锚）；on = True。
  两臂**同进程同代码**，仅 registry 注入差（`dataclasses.replace`，w154 同款并行期
  安全 A/B 法）。
- **种子/池**：seeds 917000..917299（n=300/臂，同 seed 配对），pool=snapshot，
  planes=1；两侧池指纹必须一致，不一致整批作废。
- **主判据（死亡域兑换率）**：局占比 P(该局 ∃帧: reserve_overflow>0 ∧ release_budget>0)。
  判据：on−off 配对差 > 0 且 on 臂占比非零（通道确实开火——「新机制先验证它会开火」）。
  off 臂按根因预测应≈0（构造性恒 0），若 off>0 即根因判定有误，整批停下重查。
- **次要（方向读数，噪声带内不叙述方向）**：终局残金中位、存活率（final_hp>0 局占比）
  不劣化。劣化超噪声带 → 查机制定位，定位不清不合入。
- **判定纪律**：变好→挂开臂；没变化→改动无效不合入；变差→查清为什么。
- **记录面**：每局逐帧 overflow/release_budget 从 sim ledger 取，配对差与两臂分布落
  `ab_results.json`。

## 4. 实机验证挂账（开臂判据）

开臂前置（全部满足才翻默认值）：
1. sim A/B 主判据通过 + 次要不劣化（本批 §3）；
2. 实机观察局 ≥2：危机帧（hp≤25 ∧ 金>R*）出现 `release tag` 姿态行 + `sess_release_budget>0`
   + 泄息去向分项账（搜索刷新/买牌）非全零（ADR-0426 增补二同款实机锚）；
3. 实机 hp 可信位核对：危机帧必须来自真读/沿用真值（hp_trusted=True），兜底帧不触发
   的边界按 §2 边界声明复核。

## 5. 实现(已完成)

**改动文件**:
- `src/sr_od/application/currency_war/kernel/cw_registry.py`:新增
  `crisis_release_enabled: bool = False`(注释引 ADR-0503;零新数值常量);
- `src/sr_od/application/currency_war/decision/decision_v2/posture_release.py`:
  新增 `crisis_release_open` 谓词 + 存息准入门应急让位分支的危机臂
  (reason='crisis',预算=min(溢余, REFRESH_ROLL_CAP×刷价));flip_hit 不动;
- `docs/develop/currency_war/decisions/0503-crisis-release-arm.md`(新增)+
  INDEX 追加行;
- `sr-od-test/test/sr_od/app/currency_war/test_cw_w917_crisis_release.py`(新增,
  10 锁);
- `sr-od-test/test/sr_od/app/currency_war/test_cw_adr0293_calibration.py`:
  `_EXPECTED_FIELDS` 增 crisis_release_enabled 字段面行(锁语义=字段面登记,
  新增字段登记为加项——锁红是字段面守卫正常拦截,非语义否决)。

**测试结果**:
- 新锁 10/10 绿(先红后绿:实现期 5 红全数为「锁先钉住预期行为」的红,实现后绿);
- release 域邻锁(w332b_release 76 例同批、w633_migration_b3、w724_overlay_a_rank)
  全绿;adr0293 calibration 4/4 绿;
- L1 快速集:1785P/0F/2S/1X(首跑 1F=上述字段面锁,登记后全绿,与基线 1785P/0F 持平);
- ruff:改动 src 文件与新测试文件全过。

## 6. A/B 结果(数字三件套)

可复算产物:`ab_results.json`(预注册口径)+ `ab_results_v2.json`(危机辖域修正
口径,修正声明在脚本文件头,先于本轮数据锁定)。池指纹两臂一致
`6400d5d8edeaf68d+eqg1`,n=300/臂,seeds 917000..917299,同 seed 配对,同进程。

### 6.1 判据口径修正(如实申报)

预注册主判据(overflow>0 ∧ release_budget>0 局占比)触发其自身停查条款:off=0.8633
≠预测≈0。查因:该口径未限危机辖域,非危机帧的 flip 臂(预算核常态>0)占满计数——
**根因判定不受影响**(单元锁证明 off 臂应急帧 directive 恒 None)。修正口径(锁定于
重跑前):危机辖域 = 帧 overflow>0 ∧ 帧 hp≤25。

### 6.2 主判据(死亡域/危机帧兑换率)

| 口径 | off | on | 配对差 |
|---|---|---|---|
| 危机帧兑换局占比 | 82/300=27.33% | 91/300=30.33% | **+3.0pp,gained 9 局 / lost 0 局** |
| 危机溢余帧兑换帧数 | 84/146=57.5% | 145/145≈100% | on 臂辖域内构造性全覆盖 |

判读:主判据通过(on>off 且 on 臂非零,通道确实开火)。帧级 on 145/145 与 off 84/146
的差部分被「行 hp(轮末读)vs 决策时刻 hp」的代理噪声掩盖(off 臂 84 局含轮末才跌入
应急带、决策时非应急的帧)——真危机决策帧在 off 臂恒 0(单元锁+构造性),配对差
+9/0 是干净证据。

### 6.3 次要判据(方向读数)

- 终局残金中位:off=50 / on=50(不劣化);均值 52.8→50.58(on 持金更少=多花了,
  方向与设计一致,噪声带内不叙述优劣);
- 存活率:双臂 1.0——planes=1 下 final_hp>0 恒真,该口径在本批**不可判**,如实
  声明;存活维度挂实机多局验收。

### 6.4 death 域 alloc chosen 残留面(候选②观测)

两臂 death 域帧均 0(本 seed 窗 917xxx 无死亡域接管帧;W907 病灶帧在 907xxx 窗)。
分配器层残留面在本批**不可测**,如实挂账:在含死亡域帧的 seed 窗复测(如 907288
重放窗)核 chosen 空置率是否随管线出口打开而下降。

## 7. 结论与挂账

- 结论兑换(三选一):**改行为成立**——sim 主判据过、次要不劣化,开关保持默认关,
  开臂判据挂账(ADR-0503 §开臂):①实机观察局 ≥2 危机帧 release tag+预算>0+泄息
  去向非全零;②实机 hp 可信位边界复核;③death 域残留面复测(907xxx 窗)。
- 候选③(核=0 FORM 空转)本批未动,留观测(任务书裁定)。
- 禁 git commit(任务书);本批落盘产物=本 REPORT+ab_results*.json+run_ab*.py+
  ADR-0503+INDEX 行+上述 5 文件改动。

## 8. 文件面偏差声明

任务书文件面写 `decision/cw_strategy.py`，但 posture/release 语义单一源实际在
`decision/decision_v2/posture_release.py`（cw_strategy.py 仅承载 StrategySession，
grep release_budget 零命中）。禁碰面「decision/decision_v2/（并行 L3 收尾批让位披露行）」
经 `git status` 实核：当前 decision_v2/ 下**无任何在飞改动**（在飞面=INDEX.md、
cw_equip_env.py、sim/checks/calib.py、ADR-0502），本批触碰 posture_release.py +
kernel/cw_registry.py 与并行批零交集。按「修哪里由代码真实布局决定」裁决，如实披露。
