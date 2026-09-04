# CW 零刷新修复批报告(ZERO_REFRESH_FIX_REPORT)

> 日期:2026-09-03。依据=编排者派单 + 诊断报告 `../ab_run_20260903/ZERO_REFRESH_DIAG.md`(权威)。
> 文件面:`decision/cw4/{shop.py, statefn/predicates.py, mandate.py, audit/provisional.py}`、`sim/ab_core_swap.py`、测试 `sr-od-test/test/sr_od/app/currency_war/test_cw_zero_refresh_fix.py`(新)+ `slow_marks.txt`(补 2 行)。
> 让路纪律:`sim/runner.py` git status 见并行未提交改动 → **runner.py 零触碰**,A/B 量具守卫全落 `ab_core_swap.py`。
> 冻结族零触碰;冻结残余 11 项不动;契约零改动;CASCADE 结论(分析件)不入本批。

## 1. 病灶1:r1 刷新 EV 接线缺口(代码修,按裁决)

- **改动**:`shop.py` 付费刷新发射位——`r1_start(None)` 字面量改读 `audit/provisional.get('V_GAP')`:None ⇒ `r1_start(None)`(**None 期行为逐字保持 fail-closed 零刷新,零漂移**);有值 ⇒ `r1_start(True)` 放行进 r2 预算门(编排者裁定「槽位有值即放行」)。
- **槽位登记(④-2 分臂纪律)**:V_GAP 槽位在 `provisional.py` 原已在册(NMF §3.3 #2b);本批补【拟·未标定】标注 + 消费位申报(r1 EV 输入,经 shop.py 接线)+ None 期语义声明。V_BAR 保持 R10-2 类型级封印不涉(测试锁:`test_v_bar_sealed_never_opens_r1`)。
- **规格对齐核查**:NMF/IMPL_DESIGN 既有条目(V̄ 只作比较项、R10-2 封印)与本接线**无冲突**——封印的是 V_BAR,V_GAP 明文「标定后 R1 门合法消费」。
- **⚠️ 显式呈报(裁决冲突点)**:编排者「有值即放行进 r2」与诊断 §6.2 回归判据「注入形态下 0<refreshes≪反事实 C 的 60+(EV 门有约束力)」存在张力——实测注入 V_GAP=10.0 后 n=5 刷新 40/66/66/67/45(≈反事实 C 量级 61-67),当前唯一约束是 r2 预算门(金−0≥刷价)。**P40 R1 启动门总账形态(c_eff·E[refreshes] ≤ V_gap)未落,属标定批既定欠账**;本批按编排者字面裁决实现,该欠账已在 shop.py 注释与 provisional 槽位申报中显式登记,防「标定完就好了」错觉。

## 2. 病灶2:arm1_existence 恒 False(先诊断后修;判=接线缺陷,修代码)

- **诊断(先跑)**:`core_swap/arm1_diag.py`(n=5,monkeypatch 仅本进程,raw=`arm1_diag_raw.json`)。假设与验证:谓词①板满条件拿**固定槽表常数 `DEPLOYED_CAPACITY`(=10,ADR-0392 定长槽表的物理长度)**当板满阈值,而板面实际上板量受**等级驱动 cap**(`GameState.max_units()`=level+宝钻、封顶 10;P1 期 3→5)约束 ⇒ `deployed_count` 构造性不可达 10 ⇒ arm1 恒 False。
- **数字**:按 cap 口径重算同语料,arm1 触发 seed0=10/13 波、seed4=5/12 波(as-is 0 波);seeds1-3 板面连 cap 都未满(deployed≤3=cap),arm1 两口径均 0(合法不触发:无等待件压板)。
- **裁决**:接线缺陷(谓词输入域错位——喂了错坐标系的容量常数),非谓词语义缺陷,不动规格。R2-2「板满=板面可观测量」的板满是**当前 cap 口径**,与 M3 语义自洽(升级→cap 涨→等待件可上场)。
- **修法**:`arm1_existence` 增 `deploy_cap` 参数(cap 口径=min(deploy_cap,10);None 兜底固定 10=保守端),两个消费位接线:shop.py 传 `state.max_units()`(单点收口),mandate.py 传 `frame.deploy_cap`(=obs.deploy_vacancy+deployed)。行为测试锁:构造板面(cap 满同阵营等待件)断言 M3 发射 + 板未满反面。

## 3. A/B 量具加固(ab_core_swap.py;runner.py 让路未触碰)

- **动作族活性下限守卫 `action_family_liveness_gate(n=10)`**:每臂每动作族(刷新/升级/买/卖)发射 ≥1,或该族全部发射路径 fail-closed 于未标定 provisional 槽位(豁免从槽位状态自动推导:`FAMILY_PROVISIONAL_DEPS` 只登记「全路径 fail-closed」依赖——refresh→V_GAP;buy/sell 含骨架义务路径、levelup 触发信号系结构谓词,恒不豁免),否则 raise「疑似结构性饥饿」。注释写明出处(2026-09-03 零刷新事故;组合性检查替代不可得的组合证明的实用下界)。=正式 A/B 前置步。计数兼容 ledger 动作对象/序列化 dict(`__type__`)两种形态。
- **判前锁 v6 检查单 `v6_checklist()` + `require_v6_green_for_formal_ab()`**:IMPL_DESIGN §5.1 v6 挂账单一源清单 16 行逐行「已落地/未落地/未到期(类条款不阻塞)」,未全绿 raise。三类判据:text 行=仓库文本锚自动判(行1 ab_judge 词表 mandate_v1/ev_arm;行7/11/13 telemetry schema 键——**当前全缺,如实读未落地**);mark 行=批操作者 `record_v6_landing(row, evidence)` 显式申报(文档/流程证据);order 行=批事件时间戳序(`record_batch_event`,R94-6 类条款:事件未到期不阻塞,到期序违=未落地)。**缺省态实测:行1/2/4-7/10-11/13-16 未落地 ⇒ 正式 A/B 被 raise 拦死——这正是诊断 §4.1 排程层缺陷(正式 A/B 在判前锁 v6 前置未落地态开跑)的代码化防线。**

## 4. 验收记录(全实测)

| 验收项 | 结果 |
|---|---|
| ① None 期零漂移 | n=5(seed0-4)新核 refreshes==0(5/5);`shop_r1_ev_unavailable` 分键计数保持(测试锁) |
| ① arm1 修复后升级>0 | 池化 LevelUp=21(seed0=6,seed4=15;修复前全 0)vs 旧臂 37-42/seed——量级未对齐旧臂(见 §5 呈报),派单口径「>0、不必相等」满足(测试锁,池化断言) |
| ② V_GAP 注入链通 | monkeypatch 注入 10.0 → 刷新 40/66/66/67/45(总 284>0,r1→r2 链通;约束力弱=§1 呈报项) |
| ③ 活性守卫正反测 | 饥饿臂(卖族 0 发射)raise「疑似结构性饥饿」✓;豁免臂(V_GAP None 期刷新族 0 发射)过 ✓;注入后豁免失效再饥饿 ⇒ raise ✓ |
| ④ v6 checklist | 缺省态 raise ✓(行1/2/4-7/10-11/13-16 未落地);全绿路径(文本锚 monkeypatch+全 mark 申报+批事件序合)放行 ✓;类条款行未到期不阻塞 ✓ |
| ⑤ CW 快速层 | `uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"` = **2377 passed, 2 skipped, 1 xpassed**(151.66s) |
| 慢桶 sim 门 | shop_line TestSimGates(基线自配对 n20/双臂相异/新核自配对 n10)+ mandate_v1 ZeroDrift + 本批 slow 验收 = **21 passed** |
| ruff | 6 个改动文件全过 |

原始数字:`core_swap/fix_acceptance.py` 输出(上文表);诊断件:`core_swap/arm1_diag.py` + `arm1_diag_raw.json`。

## 5. 呈报项(编排者/后续批裁决)

1. **r1 约束力欠账**(§1):「有值即放行」使注入形态刷新量 ≈ 反事实 C——P40 R1 启动门总账须随标定批落码,否则「刷新失控烧金」形态会原样复现(反事实 C 的 final_hp 63/6/1/21/67 已示该方向行为更差)。
2. **泛化步(同类还有吗)**:seeds1-3 新核 ledger 全空(买/卖/升级全 0,修复前后同形态,旧臂同 seed 正常)——非本批引入,疑 mandate_v1 M2「只买精确线成员、无候选回退」在发牌不配合时整局面零动作;建议单独立案(与 B1 劣化传导相关)。
3. **v6 检查单当前全红是预期态**:行1/2(判读器词表/叙述迁移)等须由判读批落地后才能放行正式 A/B——本批只代码化门,不替任何行做申报。
4. arm1 修复后 seeds1-3 仍 0 升级,根因同呈报项 2(无商店波动作 ⇒ M3 无机会),非谓词残留缺陷。

## 6. 登记节

design_telemetry「零刷新修复批」节:本批登记位=①shop.py r1 接线注释(出处/边界/欠账);②provisional V_GAP 槽位申报(【拟·未标定】+消费位);③predicates.arm1_existence docstring(cap 口径结论/出处/边界);④ab_core_swap 守卫组 docstring(事故出处+类条款依据)。每处注释含三元组(结论→出处→边界)。
