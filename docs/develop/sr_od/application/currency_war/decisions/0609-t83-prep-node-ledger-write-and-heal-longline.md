# ADR-0609: P2 备战时点节点条观测链修复 + 结算 tooltip「长线作战」回血分量补链(T-83)

- 状态:已实施
- Date:2026-09-09
- 关联:ADR-0587(ledger_node_type 查表制,消费面单一源)、ADR-0398(位面详情采集/接管补采通道)、ADR-0241(「长线作战」战斗回血 +2/场口述与连胜实证;本批 §2 有数据收窄回指针)、`p26_calibration/CONDITION_TABLE.md`(T-57 标定批,本批两缺口的判读来源)

## 1. 背景与问题

T-57 P26 标定批交付的条件表披露两个系统性缺口(本批为其实施批):

1. **P2 备战轮节点条台账 miss 18/24(75%)**,miss 集中 P2 前中段;p26 备战帧采样(`decisions.p26_prep_obs.node_type_next`,读链 = `cw_state.ledger_node_type` 查「当前轮」)整批落 MISS 桶,P26 辖域标签维度在 P2 结构性不可用。本批实机 4 局对照钉死根因为**写入端缺位**(结构性,非识别失败):正常局 P1 每轮命中、P2 r1-r6 全 miss;接管局(session 重建、写点①触发)P2 反而命中。
2. **结算 tooltip 与 hp 链差的系统偏移**:败面同源 20 行里 19 行满足「tooltip 两分量幅度 = 链差 + 2」,机制未定谳;且档案行内无回血分量,判读侧无法验证任何候选机制。

## 2. Considered Options

### 缺口 1(P2 台账 miss)

- **A(采纳)备战帧 heavy 观察加台账写点③**:`CwScreenPrep._probe_node_type` 每备战帧已在读节点行序列(节点行 CV 读数是现成产物),读数按位合并进 session 权威表。P2/P3 从本位面首个 clean 备战帧起查表命中;P1 行为不变(按位合并幂等)。
- **B(否决)扩写点①触发条件**(P2 进位面也跑位面详情采集):需额外开/关详情画面交互(转场+动画窗 2-3s/位面),为观测面引入行为面成本;且接管通道触发语义(briefing_bosses 空门)会被稀释,ADR-0398 通道契约受损。
- **C(否决)telemetry recorder 侧逐帧识别回退**(p26 采样 miss 时回退逐帧 OCR):观测面造第二读链 = 单一源回潮;且逐帧识别在店开帧结构性恒 None(ADR-0587 病灶),回退链在关键帧上恰好最弱。
- **D(否决)只登记不修**:缺口 4 判读原文已定性「修 P2 位面节点条读链后自动回填」;登记不修会让 P26 标定的 P2 侧引用面长期空转。

### 缺口 2(tooltip +2 偏移)

- **A(采纳)机制定谳 + 补采集字段**:定谳 = 「长线作战」行(战斗回血,ADR-0241 口述「胜利回血 ~+2/场」+80→82→84 连胜轨迹;CONDITION_TABLE 败面 19/20 也 +2 ⇒ 回血非胜局专属,口述的「胜利」限定被数据收窄为「每场战斗结算回血」,此处如实申报);补链 = `heal_longline` 从解析器一路进 outcomes 行(此前解析器已解析但 schema 缺字段被静默丢弃)。补齐后链差恒等式(链差 = 掉血两分量 + 回血)行内三量齐,偏移可直接验证——**偏移本身不是数据错误,是「掉血分量」与「净变化」两个口径测的量不同**。
- **B(否决)改 L_node 对比公式把 +2 抹平**:在消费侧硬编码 +2 修正 = 拍死值倒灌;回血量是游戏可变量(ADR-0241 即以 ~ 波动登记),单一源在游戏 tooltip 本身。
- **C(否决)申报不修**:schema 缺字段使判读侧永远无法行内验证偏移机制, CONDITION_TABLE 的「登记待查」无法闭环;字段追加为可选兼容面,成本最低。

## 3. 已实施架构与消费面申报

### 3.1 写点③本体

`operations/cw_screen/cw_screen_prep.py::_probe_node_type`:备战帧读数 `[s.node_type for s in slots]`(全槽含 None,按 idx 0-based = 第 idx+1 轮,与台账 seq 下标同基零换算)按位合并 `ledger_update_plane(sess, plane, seq, 'prep_row')`;位面键 = `last_state.plane`;**投资环境变异窗内不写**(`env_grace_until` 守卫,与三票校验豁免窗同语义——变异中序列禁落权威表);**轮位对齐门**(落地审建议修):写入前校验 current 槽 `idx == last_state.round_num - 1`——槽 idx 是检测圆枚举序,HoughCircles 中段漏检一圆 → 后续槽整体左移 → 按绝对位合并会把类型写错位且 past 位不可自愈,错位帧拒写本帧等下个 clean 备战帧;best-effort 失败不阻塞备战环。current 槽值由 `read_node_sequence` 的 OCR 标签带位置覆盖填值(r80 审计 P0 锚定门),past 槽 None 靠合并语义保旧。

### 3.2 heal_longline 补链(六点)

`cw_performance.RoundOutcome` 加字段 → `cw_settlement_obs.read_round_outcome` 透传 → `cw_screen_battle_wait` 页1 暂存两处 + 页1 暂存合并键一处 → `telemetry/schema.OutcomeRecord` 加字段(可选字段追加,关键字序列化位置无关,旧记录缺省 None 读端 `.get` 容忍)→ `recorder.record_outcome` getattr 镜像透传。注释统一指 ADR-0609。

### 3.3 消费面全清单(`ledger_node_type` 在役 6 处,写点③使 P2/P3 从恒 None 变有值,**全部随之激活**)

写点③不是纯观测面——台账从 P1 专属变为三位面有值,所有查表消费面在 P2/P3 的行为从「恒 miss 走回退分支」变为「查表命中」。逐面如实分类(grep `ledger_node_type` 全库清点):

| # | 消费面 | 层级 | P2 填表后的行为变化 |
|---|---|---|---|
| 1 | `telemetry/recorder.py` p26 备战帧采样 | 遥测观测 | miss 变命中(本批主目标),值语义「查表有值则用」不变 |
| 2 | `strategies/impl/flow.py` 掉血报警 node_type 空值回落 | 遥测/判读回落 | 「查不到退空串+blood_alarm_node_type_fallback 分键」变「查到回落出 token」——回落质量提升,分键缺失率下降 |
| 3 | `obs/cw_observation.py` `read_game_state` 的 `state.node_type` 查表优先(ADR-0587 制) | **决策级·策略主输入** | P2 帧级 `state.node_type` 从「逐帧 OCR 回退值」翻转为「台账值」;店开帧此前恒 None(fail-open)变为有台账值——**策略主输入的来源翻转**,一致性增益(P1 同制,P2 补齐)如实申报 |
| 4 | `obs/cw_observation.py` `verify_node_type_votes` 三票校验 | 观测自检→**停线触发面** | P2 从恒 skip(无表值不可比)变激活:台账/逐帧/标签三票在 P2 可比对拍,不一致落缺陷台账;缺陷复现升 L0 走分级安灯(**自动停线**,defects 用户裁决「确认缺陷即停实机」)——P2 出现新停线触发面,属识别错误防线按设计生效 |
| 5 | `operations/cw_op/cw_op_buy_cards.py` 店开帧台账查 node | **决策级·发射臂** | ②(b) `dead_gold_press_buy` 发射与 M3 规则①抑制在 P2 从结构性关闭(查表恒 None fail-open)变可达——发射语义的决策行为变更,判据本体(ADR-0580/奖励帧抑制)零改动,辖域扩大 |
| 6 | `operations/cw_op/cw_op_equip_all.py` 装备 wear/release 查 node_type 与 next_node_type | **决策级·装备释放判据** | O1 门/保留域⑤的 `next_node_type` 判据在 P2 从 None 维持 hold 变为可查表判定——装备释放时点在 P2 从保守 hold 可转为按判据释放 |

**口径声明(落地审需修项的回应)**:代码不回退——三处决策级消费面在 P2 的激活是「P2 补齐与 P1 同等查表制」的一致性增益,P1 上同判据已实跑多局无异常;但「纯观测面/行为不变」的原始申报**不成立**,以本清单为准。各判据在 P2 的实际发射质量(②(b) 是否误发射/装备是否误释放/三票是否误报)挂实机局判读,回归信号 = P2 出现 [cw!] 缺陷台账行或安灯停线。

### 3.4 sim 可观测性申报

本批全部落 operations 层与遥测层(sim 引擎不跑 `_probe_node_type`/`read_round_outcome`,sim 决策帧无 `p26_prep_obs` 字段——已实测确认)→ **sim 对本批修复双重结构性不可见**(既无写点③宿主也无 heal_longline 读端),禁 sim A/B 作验收;验收 = 行为锁(构造场景)+ 实机局判读。

## 4. 边界

- past 槽类型不回填:备战行读法对已通过节点(变暗)结构性 None,合并保旧;历史轮查表 miss 的消费面(flow 回落)维持原退化路径。P26 辖域只需「当前轮」,不为判读舒适扩识别面。
- 接管局行为不变:写点①(位面详情)仍为主通道,写点③同帧叠加按位合并幂等。
- 档案兼容:heal_longline 仅新局产出;旧档案行内无此键,判读侧 `.get` 容忍(与 damage_base 同款)。
- 「长线作战」回血量恒 +2 为当前实机读数(19/20 + ADR-0241 双源),非建模承诺;L_node 对比口径按行内三量现算,不落 +2 常量。

## 5. 验证

- 行为锁 `test_cw_t83_prep_ledger_write.py`(6 用例,构造场景锁):P2 空台账备战帧后 p26 读链必命中 / 位面键对齐(P2 帧禁落 P1)/ 变异窗守卫(窗内拒写+过期恢复)/ None 位保旧合并 / P1 幂等 / **轮位对齐门**(漏检圆错位帧拒写+下帧对齐恢复)。**变异红证**:短路写点③ → 前 5 锁全红;松开轮位对齐门 → 对齐门锁红,均还原绿。
- 行为锁 `test_cw_settle_telemetry.py` 追加 3 用例:透传(面板三行齐 → heal_longline=2 + 净变化恒等式 -10-1+2=-9)/ recorder round-trip(outcomes 行含值)/ 页1 暂存键面接线锁。**变异红证**:分别删 recorder 透传、改 read_round_outcome 传 None → 对应用例红,还原绿。
- 点名直接受影响测试(33 文件)全绿(slow 桶在案红 `test_ci_smoke_snapshot_batch` 与本批零机制交集,T-133 归因在案)+ ruff 全部改动文件,见交付报告。
