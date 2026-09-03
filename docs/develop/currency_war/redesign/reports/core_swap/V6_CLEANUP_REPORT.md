# v6 判前锁清理批报告(V6_CLEANUP_REPORT)

> 日期:2026-09-11。性质=量具/判读面批(A/B 重跑前最后一批量具面工作)。
> 任务书=v6 判前锁清理(§5.1 逐行对账/症4/症7/预注册件/零漂移复核)。
> 写面声明:`sim/ab_core_swap.py` + `tools/cw/ab_judge.py`(判读器件)
> + `redesign/PREREG_cw3_vs_legacy_AB.md`(预注册文档)
> + `sr-od-test/.../test_cw_v6_cleanup.py`(新增)/`test_cw_zero_refresh_fix.py`
> (锁值更新)。零 git;冻结族/残余 11 项/契约 v2/cw4 生产代码零触碰。
> 单一源纪律:v6 清单权威=IMPL_DESIGN §5.1 表(+本批新增行 17,登记见
> §1);预注册判据落 PREREG v6 行(独立预注册文档形态,未在 IMPL_DESIGN
> 重复正文——防双源)。

## 1. §5.1 v6 清单逐行对账表

清单原文=IMPL_DESIGN §5.1「判前锁 v6 挂账单一源清单」(R44-7)16 行
+ 本批新增行 17(症4;按 R44-7 纪律新增挂账条目入 §5.1 本表——**申报:
本批未直接编辑 IMPL_DESIGN.md(保留面,编排者辖),行 17 的清单侧登记
以本报告 §1 对账表为过渡载体,待编排者回写 §5.1 表后消账**;可执行
镜像已落 `ab_core_swap._v6_row_specs` 行 17)。

| 行 | 内容(清单原文摘要) | 状态 | 落点/处置 |
|---|---|---|---|
| 1 | 三臂单被测体两因子叙述+多重比较声明(预指定主对照 ②−①;次对照 ①-③ 仅描述性);ab_judge 词表含 mandate_v1/ev_arm | **本批落地** | `ab_judge.py` v6 节:`ARM_FACTORS`(mandate_v1/ev_arm/skeleton_only/decision_v2)+`judge_v6`(主对照进门/次对照描述性)+PREREG v6 行三臂叙述。验证:grep 亲跑两文件词表命中;`test_ab_judge_v6_vocabulary_anchor` 绿 |
| 2 | 判读器迁移与 v6 变更绑定为判读前硬前置 | **本批落地(文本面)** | 判读器迁移=ab_judge v6 模式+self-test v6;v6 变更=PREREG 修订表 v6 行(亲验:`'\| v6 \|' in PREREG` 计 1)。hint 判据 `'v6' in PREREG` 亲跑 True。mark 行申报(record_v6_landing)留判读批操作者携证据执行——申报本身系流程事件,不属本批 |
| 3 | 血线阈值标定 ≤ p 开闸(时间戳序) | 未到期(类条款,R94-6) | 零触碰;`_BATCH_EVENTS` 数据源已在位 |
| 4 | 锚批/判读批分离(拆半方案预注册) | 预注册文本已落 PREREG v6(拆半方案:前半定阈后半判读);申报留判读批操作者 | mark 行,证据位=PREREG v6 (iii) |
| 5 | 激活率门验收口径重开+预注册(非窗口相位) | 预注册文本已落 PREREG v6(锚参考值 137/926≈14.8% 带 R59-3 构造口径标;禁跨相位混用);申报留判读批 | mark 行,证据位=PREREG v6 (iii) |
| 6 | P3 fallback 9→CI 上端治本落地事件入变更记录 | 未到期(mark;治本落地批辖) | 按清单原文处置:留置,批事件形态 |
| 7 | f7_contingency_armed 进 telemetry schema | **挂起+申报(让路规则)** | `telemetry/schema.py` 系并行批在飞文件(git status ` M`),本批禁硬改;三键(f7_contingency_armed/depsilon_advisor_violation/f7_exempt_emission)现树 grep 零命中——**正式 A/B 在该批落键前被 v6 检查单阻塞(设计内)**,待 schema 批结清或后续批落键 |
| 8 | η/θ 标定 ≤ p 开闸(时间戳序) | 未到期(类条款) | 零触碰 |
| 9 | χ 标定 ≤ 换线判读锚批(时间戳序) | 未到期(类条款) | 零触碰 |
| 10 | 激活率门锚/#T 相位分键重开+预注册(窗口相位={k∈C\D_ε} 集合谓词) | 预注册文本已落 PREREG v6(窗口相位=R51-1/R52-4 口径);申报留判读批 | mark 行,证据位=PREREG v6 (iii) |
| 11 | depsilon_advisor_violation 漂移哨兵语义(telemetry schema 含该键) | **挂起+申报(让路规则)** | 同行 7 |
| 12 | D_ε 带宽与 η 同批标定(时间戳一致) | 未到期(类条款) | 零触碰 |
| 13 | f7_exempt_emission 观察键(telemetry schema 含该键) | **挂起+申报(让路规则)** | 同行 7 |
| 14 | P2 段档位登记批 ≤ P2_IDLE_SWITCH_W 激活 | 未到期(mark;登记批辖) | 按清单原文处置:留置 |
| 15 | 01 §4.4 [41] S 公式物理补指针 | 未到期(mark;落码批验收时点,R92-6/R94-6 类条款) | 按清单原文处置:留置 |
| 16 | 01 §4.1 [17] 息律三处字面参数化核读 | 未到期(mark;落码批验收时点,R99 类条款) | 按清单原文处置:留置 |
| 17 | **本批新增**:formal A/B ⟹ V_GAP 注入态(或显式豁免批文落档)——IMPL_ADV_R200 症4 落地,零刷新事故防护 | 判据已代码化并测试锁死;当前态=V_GAP None+无豁免 ⇒ 红(设计内:A/B 跑批入口先 `apply_core_swap_calibration()` 或走豁免批文) | `ab_core_swap._v6_row_specs` 行 17(kind=calib)+`record_formal_ab_exemption`;事故复演红测试=`test_incident_config_must_be_red` |

对账结论:v6 生效前置=text 行 1 落地 + 行 7/11/13(schema 批辖,挂起
申报)+mark 行(2/4/5/6/10/14/15/16,申报/事件归各自承载批)+行 17
(A/B 入口注入/豁免)。**正式 A/B 当前被行 7/11/13 阻塞(schema 三键
缺)——该阻塞系并行批在飞的让路结果,非本批遗漏**;解除路径=schema
批结清后三 text 行自动转绿。

## 2. 子项三元组(修法+验证数字+测试)

### 2.1 症4 落地(事故防护代码化)

- **修法**:①`_v6_row_specs` 增行 17(kind=`calib`,运行时判据:V_GAP
  非 None ∨ `_FORMAL_AB_EXEMPTIONS` 非空);②豁免批文登记
  `record_formal_ab_exemption(slot, ruling)`(空/纯空白批文 raise,与
  v6 mark 行 evidence 硬化同纪律);③活性守卫豁免清单自动落档
  (`_LIVENESS_EXEMPT_DISCLOSURE`,守卫产物快照);④`require_v6_green_
  for_formal_ab` 返回值扩 `prereg_manifest`(`formal_ab_prereg_manifest`
  =v6 全单+V_GAP 态+豁免批文+豁免快照)——判读产物落档形态;⑤
  **判读器侧等强防线**:ab_judge v6 拒读缺 `formal_ab_prereg` 块/v6
  未绿/V_GAP=none 无豁免的 formal 批(双防线)。
- **验证数字(亲跑)**:事故复演(其余 16 行全绿,V_GAP=None,无豁免)
  ⇒ `rows[17]['status']=='未落地'`,`require_v6_green_for_formal_ab`
  raise(消息含「行17」);注入通道(`apply_core_swap_calibration`)
  ⇒ `report['prereg_manifest']['vgap_state']=='injected'` 放行;豁免
  通道 ⇒ `vgap_state=='none'` 且批文入 manifest 放行;liveness 守卫
  (V_GAP=None,fake sim)⇒ 豁免快照 `{'baseline': {'refresh':
  'fail-closed:V_GAP'}, 'new_core': {...}}` 落档。ab_judge v6 自测
  W-B(V_GAP=none 无豁免)SystemExit 拒读。
- **测试锁**:`test_cw_v6_cleanup.py::TestRow17IncidentGuard` 6 条全绿
  (含事故复演红——必带项);`test_cw_zero_refresh_fix.py` 锁值 16→17
  更新(锁纪律:清单新增判据行属设计演进,随行数更新,理由注记在码)。

### 2.2 症7 落地(测量域对齐)

- **修法**:①模块头预注册声明:原「diff 全部归于 prep/shop 决策面」
  收窄——归因域**实际=shop 决策面**(sim 唯一决策入口=
  decide_shop_screen,prep 面 sim 不可达),B1/B2 不得外推全决策面;
  ②门组 docstring 加辖域限定句(new_core_self_pairing_gate 明示 prep
  线确定性归 checks/decision_v2.py 契约门承载);③活性守卫 sell 族
  证据辖域:`ACTION_FAMILY_TYPES` 注记+liveness 报告新键
  `sell_evidence_scope`(shop 侧发射位仅;prep 侧 m4_fuel_sell_for_m2
  无 sim 证据);④PREREG v6 行④同款声明(判读面消费)。
- **验证数字(亲跑)**:liveness 报告
  `sell_evidence_scope=='shop 侧发射位仅(prep 侧无 sim 证据,
  IMPL_ADV_R200 症7)'`;ab_core_swap 文本锚
  `'实际=shop 决策面' in text` 且 `'prep 面 sim' in text`(测试绿)。
- **测试锁**:`test_measurement_domain_narrowed_in_ab_core_swap` +
  `test_liveness_exemptions_filed_and_consumed`(辖域句断言)。

### 2.3 判读器迁移(行 1/2)

- **修法**:ab_judge 新增 v6 节——`ARM_FACTORS` 三臂词表、`judge_v6`
  (预指定主对照 ②−① 走 v5 三闸主门+硬哨兵;次对照 ①-③ 仅描述性
  Δ/CI、无 verdict 字段)、`render_human_v6`、`self_test_v6`(W-A/B/C
  三场景)、CLI `--prereg v6 --arm1/--arm2/--arm3`。
- **验证数字(亲跑)**:`uv run python tools/cw/ab_judge.py --self-test`
  ⇒ v1(11 场景)+v5(6 场景)+v6(3 场景)全过,输出「v6 自测通过:
  W-A 缺 prereg 块拒读 / W-B V_GAP=none 无豁免拒读(症4 事故形态复演
  红)/ W-C 全件齐备判读(主对照进门+次对照描述性+披露随 headline+
  措辞限定)」;W-C 断言:同分布三臂总判 PASS、次对照无 verdict、
  headline 含「不得读作全量处理效应」、披露计数渲染
  (`shop_r1_ev_unavailable=5`)、词表含 mandate_v1。
- **测试锁**:`test_ab_judge_selftest_v6_green`(importlib 直载复跑)、
  `test_ab_judge_v6_vocabulary_anchor`。

### 2.4 预注册件落地(CALIB_REPORT_V2 §3 裁决附条件)

- **修法**:落 **PREREG 修订表 v6 行**(单一源=预注册文档;未在
  IMPL_DESIGN 重复正文,防双源)。内容:①强制披露清单
  (shop_ev_u_unavailable/m6_overflow_strand/shop_r1_* 前缀族随
  headline;数据源=`ab_core_swap.cw4_disclosure_from_session`,批次
  manifest `cw4_disclosure` 块,ab_judge v6 强制消费——缺块拒读);
  ②headline 措辞限定(「已开闸面处理效应+共同降级分量(披露计数)
  显式分离」,B1/B2 不得读作全量处理效应;判读器侧=`V6_HEADLINE_NOTE`
  常量+渲染必带);③激活率门 R37-1 系预注册(基线=骨架+EV 臂 sim 首批
  实测触发集访问率;拆半方案=前半定阈后半判读;**预判红处置预指定**
  =按红因分层:实现缺陷→修复重锁锚批 / 相位域错配→按行 5/10 相位分键
  口径重开,禁判读后择优;相位分键锚参考值=行 5/10 清单原文口径逐字
  引用,含 R59-3 构造口径标与 R51-1/R52-4 窗口相位集合谓词口径);
  ④卖族活性证据辖域限定(症7);⑤行 17 事故防护门+豁免强制消费链。
- **验证数字(亲跑)**:PREREG 文本锚测试——`'| v6 |'` 计 1,
  `'单被测体两因子'/'预指定主对照 ②−①'/'shop_ev_u_unavailable'/
  '不得读作全量处理效应'/'骨架+EV 臂 sim 首批实测'` 全命中
  (`test_prereg_doc_v6_section_anchor` 绿);披露键族过滤亲跑:
  `cw4_disclosure_from_session` 对 6 键计数 dict 输出恰 4 键(无关键
  shop_wave_idle_gold/emitter_conditional_truncated 剔除)。
- **测试锁**:`test_prereg_doc_v6_section_anchor` +
  `test_disclosure_counter_filter` + ab_judge W-C 披露断言。

### 2.5 零漂移门/三门组复核(量具自身未漂移)

- **修法**:无(复核项)。改动面=判据行/词表/披露/辖域句,不改判读
  统计口径(judge_main/judge_sentinels/bootstrap 零触碰)。
- **验证数字(亲跑,2026-09-11)**:
  - `baseline_self_pairing_gate(n=5, planes=1, pool='fallback')` ⇒
    ok=True,mismatches=[](指纹 32b6139f73629263…);
  - `new_core_self_pairing_gate(n=3)` ⇒ ok=True,mismatches=[];
  - `arm_diff_probe(n=3)` ⇒ diff_pairs=3,ok=True;
  - `action_family_liveness_gate(n=3)` ⇒ ok=True,豁免快照落档正确;
  - ab_judge `--self-test` v1+v5 全过(既有判读行为零漂移);
  - 受影响 L1 集(harness/shop_line/mandate_v1/v6_cleanup/zero_refresh,
    `-m "not slow"`)⇒ **142 passed, 1 deselected**。
- **测试锁**:既有 `test_cw_core_ab_harness.py` 三锁全绿(含在 142)。

### 2.6 T_SEARCH_A 查表对账(任务书指派的对账项,零改动)

- **对账结论**:`statefn/odds.py` 已落 `tier_search_window`(读法甲,
  档级消费位:压库/凑息/M6——shop.py `_t_search_active` L341 单一源
  消费)与 `card_search_window`(读法乙,单卡消费位:ev_buy 追件——
  buy.py L60 消费),两读法分立消费与 CALIB_REPORT_V2 §2.3 治本规格
  一致;V̄ 现读 provisional V_MS、None ⇒ 空集 fail-closed、零新自由
  参数、R200 症5 例 1/2 的硬编码 {1,2,3} 已不在树(grep
  `frozenset({1, 2, 3})` 零命中)。**对账通过,本批零改动。**

### 2.7 v6 mark 行 evidence 持久化落盘(编排者增补子任务;外部交叉
评审 2026-09-03 20:32 首轮建议级→本批落地)

- **修法**:①`record_v6_landing(row, evidence, context='')` 增补落盘
  ——evidence 连同行号/时间戳(`recorded_at`)/标记者语境(`context`)
  追加写 `.debug/temp/currency_war/core_swap/v6_landing.jsonl`(A/B
  判读产物目录族;jsonl 逐行);重复登记以**落盘首行为准**(不追加、
  不改写,证据不可事后篡改);②checklist mark 行复验改**从落盘文件
  回读**(`_load_v6_landings_from_disk`,持久权威;进程内缓存仅补文件
  未及行;坏行=缺 evidence 字段/纯空白/非法 JSON ⇒ 该行不入有效集=
  行红);③测试重定向缝=`_V6_LANDING_FILE_OVERRIDE`(测试零真实
  .debug 写入,run 后亲验真实路径无文件生成)。
- **验证数字(亲跑)**:`test_cw_v6_cleanup.py::TestV6LandingPersistence`
  3 条绿——落盘+清内存后 checklist 仍绿(evidence 自文件回读,文件行
  含 row/evidence/recorded_at/context 四字段);落盘行缺 evidence 字段
  与纯空白两种形态 ⇒ 行 4/5 双红(**测试锁必带项**);重复登记 ⇒ 文件
  恰 1 行且 checklist 用首份证据。全套 33 passed(两测试文件),
  受影响 L1 集 145 passed,ab_judge v1/v5/v6 self-test 全过,ruff 过。
- **既有测试适配**:`test_cw_zero_refresh_fix.py::TestV6Checklist` 四
  测试加 monkeypatch+tmp_path 重定向(防真实 .debug 写入+隔离真实落盘
  档回读串扰);锁语义零变更。
- **等强形态申报**:任务书①②③三要件全落(evidence 含行号/时间戳/
  语境随判读产物目录族落盘=①;checklist 回读核对=②;缺 evidence 字段
  红=③)。

## 3. 让路/挂起申报汇总

| 子项 | 阻塞 | 处置 |
|---|---|---|
| 行 7/11/13(schema 三键) | `telemetry/schema.py` 并行批在飞(git ` M`) | 挂起+申报(本报告 §1);禁硬改;解除=schema 批结清或后续批落键,v6 text 行自动转绿 |
| IMPL_DESIGN §5.1 表体回写行 17 | 总纲保留面,编排者辖 | 本报告 §1 对账表为过渡载体,待编排者回写消账 |
| 行 2/4/5/10 的 mark 申报 | 申报系判读批操作者流程事件 | 预注册文本已备齐(PREREG v6),申报携证据执行 |

## 4. 复审自查节(可推翻条件;供独立 review 对表)

1. **行 17 形态可推翻点**:实现为 kind=`calib` 运行时判据(V_GAP 注入
   态 ∨ 豁免批文非空),判据行原文=「formal A/B ⟹ V_GAP 注入态(或
   exempt 清单为空的显式豁免批文)」——若复审裁定必须为 text/mark 型
   (仓库文本锚),`_v6_row_specs` 行 17 的 kind 与 `v6_checklist` calib
   分支需改型;判据语义(两通道)不变。
2. **豁免「强制消费」强度可推翻点**:本批落=守卫豁免快照自动落档 +
   prereg manifest 落档 + ab_judge v6 拒读三件;未做「跑批侧 manifest
   豁免块与守卫快照逐字段一致性比对」(formal 跑批入口尚不存在,比对
   无对象)——若复审要求等强形态升级,补位点=未来跑批入口在序列化
   manifest 前调用 `formal_ab_prereg_manifest()`(现成 API)。
3. **披露计数的运行时链路可推翻点**:`cw4_disclosure_from_session`
   已备但 formal 跑批侧尚无逐局聚合调用点(同上,入口不存在);ab_judge
   v6 已强制消费 manifest `cw4_disclosure` 块(缺块拒读)。若复审认为
   「预注册①未落地直到跑批批出现」,接受该收窄——本批交付=判据+数据
   源+消费端三件,链路闭环待跑批批。
4. **次对照统计口径可推翻点**:①-③ 描述性报 Δ+正态 CI_lo(未走
   bootstrap)——次对照不进门,精度要求低;若复审要求与主对照同口径,
   `judge_v6` secondary 分支换 `bootstrap_lb` 即可(结构已留)。
5. **行 5/10 锚参考值引文风险**:PREREG v6 (iii) 的锚数字(137/926、
   #T=4、C\D_ε 口径)系对 IMPL_DESIGN §5.1 行 5/10 清单原文的逐字转
   引;若清单原文后续批次再改(如 D_ε 排除重算落地),PREREG v6 行需
   同步(单一源=IMPL_DESIGN §5.1,PREREG 为消费面)。
6. **测试锁值 16→17**:若编排者裁定行 17 应编为 §5.1 表外独立门(非
   清单行),则 `_v6_row_specs` 行 17 与两处测试锁值需回退、改独立
   guard 函数形态——判据语义不变,载体变。
