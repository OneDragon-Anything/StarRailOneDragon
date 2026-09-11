# ADR-0605: T-109/T-100 遥测数据病合并批——离场派生列 v10 + 复盘 075840 三件定谳(①真缺口修 ②申报 ③反证)

- 状态:已实施(commit 候编排者统一门)
- 关联:ADR-0577(v9 hp 事件模型;③ 定谳沿用其 §3.3「陈旧直到证伪」先验)、ADR-0567(loss_nodes 逐结算行化;v8 立案的「补给回血」见证已随 v9 勘误)、ADR-0571(T-88 四字段写读闭环;T-100 release_budget/overflow 两件的收口依据)、ADR-0534(swap 卖出逐件资格判定,执行期身份的发射侧)、复盘材料 `.debug/temp/cw_review_075840.md`、证据帧 `.debug/temp/currency_war/shots/obs_conflict_hp__32006c4d.png`(08:35:31 备战帧 HP HUD 视觉实证)
- 实施面:`telemetry/match_archive.py`(v10 departures 派生列)、测试仓 `test_cw_t109_departures.py`(新)+ `test_cw_adr0282_hp_layers.py`(件5 形态锁)

## 1. 背景

复盘 075840 提出数据病三件(账本 T-109):①场上件离场无逐件落账(挡 pivot 判读,曾由编排者直调质询降级、084421 复盘三例互证后本批复核);②p2r1→p2r2 约 52 金未建模收入通道;③hp 帧读漏补给回血(final_hp=1 陈旧读数,实际 17)。另 T-100 六件的未闭合残余项随批处置。

## 2. Considered Options

| 方案 | 裁决 | 理由 |
|---|---|---|
| ①修 = 在 `_sell_offtarget_deployed`(cw_op_deploy.py)加逐件遥测写点 | ✗(本批) | 该文件为 C1+T-167 在飞共存面,禁碰;写点修复候解冻批(见 §3.4) |
| ①修 = 装配端帧间差分派生列(本批) | ✓ | 零运行时侵入、旧档案重装配即补齐(v6/v9 先例);075840 源流仍在档案切片内可验证 |
| ①定谳 = 全盘维持「复盘侧消费缺口」(账本降级口径) | ✗ | 复核实锤执行期换血卖出通道确无逐件遥测(Saber 行为证据链见 §3.1),降级口径只对决策时点卖出成立 |
| ②处置 = 立即按「降本增效选卡即付」建模 exogenous 事件行 | ✗ | 机制未经实机帧定谳(板面未售与卡面文本矛盾,±6 金差额未闭合);未证机制入写点 = p42 组件级粒度事故同型风险 |
| ②处置 = 申报候选 + 挂一帧定谳步骤(本批) | ✓ | 时机唯一性 1/1 vs 0/6 + 注册表精算量级吻合,候选强度足够指导取证 |
| ③处置 = 按「帧读漏回血」修读取链 | ✗(反证) | 冲突帧截图视觉实证 HUD=1:1 是真值非陈旧值;候选方向与事实相反 |
| ③处置 = 定谳反证 + 形态锁钉住读数链采信方向(本批) | ✓ | 防后续下行守卫修订无意识翻转真值(锁的存在性纪律:先判锁再判改) |

## 3. 已实施架构

### 3.1 ①定谳:缺口 = 执行期 deploy 换血卖出(半真)

决策时点卖出(SellBench/SellDeployed)逐件在案(decisions.actions 身份+income+expect,期望态快照 `tracked_bench_chars[slot]=None`/`tracked_deployed[idx]=None` 登记),复盘候选对该面不成立。**真缺口**:执行期换血卖出(`CwOpDeploy._sell_offtarget_deployed`,victim 身份在执行时刻才确定)逐件身份只落 log 行与匿名计数键(`sell_offtarget_arm_*`/`sell_offtarget_regular`),无遥测行。实锤 = 075840 p1r1 Saber:08:00:18 帧 `[椒丘,藿藿,Saber]`(RunDeploy 计划)→ 08:00:42 帧 `[椒丘,艾丝妲,藿藿]`,无任何 Sell 动作,Saber 消失仅伴随 `sell_offtarget_regular:1` 匿名计数。

### 3.2 ①修:`departures` 派生列(v10,装配端纯读)

段内相邻决策帧(ts 升序)的 `state.deployed` 身份多重集差,通道闭集 `DEPARTURE_CHANNELS = (sell_recorded, merge_promoted, unexplained)`(判据见 `_derive_departures` docstring)。行形状 `{run_id, plane, round, ts, char, star, count, channel, same_window_arrivals}`。边界申报:①感知纠噪(SIFT 翻转)也会落 unexplained——075840 实测 24 行中 P2R1/P2R2 两窗各 5-7 行为 deployed_align 补齐/截断纠噪形态(大进大出、到场 1:1 比例破坏),判读并读 obs_conflicts;②deployed 身份不可知帧(缺/非列表)整对跳过,宁缺勿造;③末帧无后继,终局前最后一段备战窗不可见;④跨段帧对不入差分(段界变化归 resume 对账语义)。真实 075840 档案切片验证:Saber 行产出(archive slices;live 流已轮转,故旧档案依赖切片/重装配双路径)。源流在档的新局经 load_archive 版本检查自动重装配补齐;源流缺失时诚实退化保留旧档(v9 同机制)。

### 3.3 ②定谳:+64 金未建模收入,唯一性关联 P2 投资选卡(申报,不建模)

实测:P2R1 出战帧金 20(08:28:05,readable=True)→ P2R2 店开帧金 84(08:31:06,readable=True),+64;建模收入(基础 5+息 2+连胜 1)= 8,未建模 ≈56。跨局对照(7 局 18 个 P2 轮界差分):全部落在 +7~+22 建模带内,**唯一离群 = 075840,且唯一在 P2 选了「降本增效」(202301,08:30:54 落窗内)**。注册表精算候选量级:`sell_refund×2` 口径全场+备战变现 = 50 金 + 战斗收入 ≈8 = 58,与 64 差 ±6(公式 🟡 不确定带 + 巨星赠件在内)。**矛盾未闭合**:板面在 P2R2 完整保留,与卡面「出售…获得双倍价格的金币」的执行形态不符——「选卡即付不出售」假说需实机帧定谳。定谳步骤:下一局遇 202301(或同款前半句的 202101 大裁员)时,选卡确认前后各取一帧金读数。若证实,建模写点 = exogenous `kind='invest_gold'` 事件行(镜像 hp_pay 模式,choice 带 card_id/gold_delta/basis),装配端加法显影列。

### 3.4 ③定谳:反证(final_hp=1 是真值)+ 读数链形态锁

冲突帧 `obs_conflict_hp__32006c4d.png` 视觉实证:08:35:31 备战帧 HP HUD = **1**。故 075840 的 hp=1 读数链(结算屏 conf=1.0、08:35:31 帧读、08:36:35+ 帧读三方一致)全部为真值,runs.final_hp=1 正确;「实际 17」是补给合成行的陈旧 `last_state` 快照(P2R2 预战值,写点 = `cw_loop._record_supply_outcome` 读 `session.last_state`,旧码 conf 降权守卫落地前写 conf=1.0),与 ADR-0577 §3.3 鬼值同型——候选方向与事实相反,原缺陷不成立,零修。形态锁(`test_cw_adr0282_hp_layers.py` 件5):17→1 跨节点下行、窗内无战斗事实(观察缺口臂)→ 采新+留证,钉住真值采信方向。**附带观察(不立案)**:该帧走观察缺口臂而非胜战臂(P2R2 结算行未入 `performance.history`);若将来修复事实查找覆盖面,「胜战零损→拒信」臂会拒绝本帧真值——胜战可扣血(行动值外取胜,075840 P1R4 −4/P2R1 −17 实证)与守卫机制注「未在行动值内取胜扣血」的张力属 ADR-0431 判据面,候独立批重推。

### 3.5 T-100 残余件处置(全部收口,零新改码)

release_budget 恒 0 / overflow 新码帧读 0 = T-88 复核批定谳「三写端+读端+键戳全链在码,实机写读闭环」(账本 2026-09-08T23:31);死亡轮 conf=0 无条目 = v9 回落路径(loss_page 来源行)已修并由 `test_cw_t100_v9_assembly.py` 锁定;armed 检查帧无分母键 = 写点在 `strategies/impl/mandate_v1/entry.py:570-575`(advisor_bloodline_armed 族,策略核心判据禁碰面),本批不落,候解冻批补「分母键=armed 检查所在决策帧数」使「检查失败」与「没检查」可辨。

## 4. 验证

- 新锁 `test_cw_t109_departures.py` 6 例(075840 Saber 素材帧 / sell_recorded / merge_promoted / 不可知帧跳过 / 零变化空列 / 段界隔离)全绿。
- 形态锁 `test_cw_adr0282_hp_layers.py` 件5 全绿;受影响面 `test_cw_telemetry_archive.py`+`test_cw_t100_v9_assembly.py`+`test_cw_gold_flow_channel.py`+`test_cw_replay_to_md.py` 123 例全绿(schema 版本单一源 `arch.SCHEMA_VERSION` 无字面值锁,版本 bump 零波及)。
- ruff 全部改动文件通过。

## 5. 修订:sell_recorded 通道解析键勘误(三审 C1/T1 修复批)

### 5.1 缺陷:通道解析键与真实落盘形状错配,通道从未可用

§3.2 的 sell_recorded 通道装配后从未真正触发过——`_sell_deployed_target_names` 按 (position_pref, slot) 匹配动作的 row/slot 字段,这是 `cw_prep_actions.SellDeployed`(执行层拖拽规格,同名类)的形状;而能落 decisions 帧的唯一生产形状 = **kernel `cw_state.SellDeployed`**(序列化字段 `deployed_idx/income/reason/expect`,无 row/slot)。形状基准实证:全仓 SellDeployed 构造点仅两处(kernel 谷底回滚 `cw_evolution._sell_action` / sim `engine_p1`),prep 同名 row+slot 类零构造点、且策略辖外声明不发射(`test_cw4_shop_line` 辖外锁);存量语料 144 档案 decisions 切片 SellDeployed 行总数 = 0。通道恒空 ⇒ 决策时点卖出场上件一旦发生即被误归 unexplained。

### 5.2 修法:deployed_idx → (排, 排内槽号) 固定双射换算命中

解析键改动作 `deployed_idx`(= state.deployed 槽位表下标 0-9,ADR-0392),换算 0-3=前排 1-4、4-9=后排 1-6(`deployed_slot_no` 单一源)后按条目 position_pref/slot 命中。**不能下标直取**:`serialize_state` 落遥测的 deployed 是紧缩占用序(None 空槽剔除,ADR-0392),帧内列表下标 ≠ 槽位表下标;条目级 position_pref/slot 信息位随序列化保留、由 `deployed_place` 落位归一,是换算后唯一可靠的匹配面。键缺失/越界不入集合(该件落 unexplained,宁缺勿造不炸)。

- **备选不采**:「通道退役、闭集收敛为二元」——通道语义(决策时点卖出背书,防与 unexplained 换血通道混淆)成立,退役是放弃而非治理。
- **对存量档案零影响**:语料零 SellDeployed 行 ⇒ 修复前后派生输出逐档案相同,无数据病、无需 schema bump / 强制重装配。
- **075840 重分箱对照**(修复令预期「决策时点卖出误归 unexplained 重分箱」的裁决):重跑派生 = 24 行(19 unexplained + 5 merge_promoted + 0 sell_recorded),与修复前基线逐行相同——**重分箱 0 行,误归预判不成立**:该局无 SellDeployed 行可被错配;19 条 unexplained 全部是 RunDeploy 换血窗(§3.1 真缺口,归因如实)与买窗感知纠噪,非解析错配产物。
- **测试随改(T1)**:用例②弃虚构 row+slot 形状,改真实键面(deployed_idx/income/reason/expect)并取**紧缩错位形态**(目标件 compact 下标 ≠ 其 deployed_idx,前排空槽剔除所致)——直取列表下标与回退 row/slot 两种错实现都命中不了,变异打红亲跑;另加固 deployed_idx 越界防御用例(落 unexplained)。

### 5.3 修订:position_pref 写端归一落码(三审 C1 修复批,T-180)

§5.2「条目级 position_pref/slot 信息位……由 `deployed_place` 落位归一」在本批前只是**解析侧的假设**:`deployed_place` 兜底落位(首选排满跨排)只归一 `slot`,`position_pref` 保留原偏好值——条目信息位与权威下标错位的形态真实存在。后果沿 §5.2 的解析键链:换算命中要求条目 `(position_pref, slot) == (row(idx), deployed_slot_no(idx))`,错位件被 SellDeployed 解析恒漏匹配 → 决策时点卖出误归 unexplained(通道要消除的形态从解析键修复后的新边界复发)。修法 = 写端治本(kernel `cw_state.deployed_place`):放置时 `position_pref` 与 `slot` 同批归一到实际落位下标(与 `_apply_row_to_char` 换排归一同向;信息位恒为下标派生,`deployed_from_compact` 旧语料适配路径同吃)。解析侧(telemetry)零改动。锁:`test_cw_state.py::test_deployed_place_normalizes_pref_and_slot_to_authoritative_idx`(归一不变式:首选排内保持/兜底跨排改写/满表拒放不写)+ `test_cw_departures.py::test_departure_sell_recorded_pref_fallback_normalized`(pref 错位形态经生产写端→序列化→派生全链命中 sell_recorded);两锁对「拆 pref 改写」变异态亲跑全红,还原后全绿。
