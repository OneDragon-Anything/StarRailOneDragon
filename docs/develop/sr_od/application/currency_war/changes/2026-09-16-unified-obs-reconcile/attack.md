# 对抗审报告（两路攻击 · 合并）

> 攻击对象版本：design.md 二轮修订前稿（攻击者读到的为初稿与一轮修订稿，见各发现位置注记）。修订落点以当前 design.md / landing.md 为准。

## 攻击者 A（核一·无前提 + 核三·治本）

**结论：核一打回（初稿）→ 修订；核三有保留通过（本迭代确认为「逻辑态 vs 实读分歧治理」同根第 4 次出现的架构级正解）。**

| # | 级别 | 发现 | 修订落点 |
|---|---|---|---|
| B1 | blocker | 豁免键坐标系前提虚假：ChannelSig.screen 可空、_validate_sig 不校验、主喂入口 _sig_read/_sig_carry 不带 screen——精确键 (screen, field) 在主要辖域结构性失效，一切豁免塌缩字段级 | design §2.2 重写：三维度键（画面×字段×logic_evidence 前缀）+ 主喂入口 sig.screen 补齐改造项（3.1）+ screen=None 仅通配可豁免语义 |
| M1 | major | 「ledger.fact_rows 不受影响」虚假：唯一读端 = 安灯派生，退役后成无上界死通道 | design §2.5 补 fact_rows 死通道退役；receipts 行与 include_payload 保留、注释动机改归「动作留证」；3.4 文件面与 grep 词表同步 |
| M2 | major | 免刷 proc / 金 ±2 不可观项（finalize 现役容差注释自认）在精确等值下 = 高频停机源；「±2 属 w494 口径」依据失真；归因出口二选一对不可观项无解 | design §2.1 修正容差出处表述；§2.6 归因辖域扩为金失配全模式、免刷列首位线索（锚 ADR-0456）；出口改三分类（建模/申报/修识别）各带验收；evidence 前缀维度解「免刷 vs 真点击落空」不可分 |
| M3 | major | write_logic 直写端族（关店金直写 / node_ledger_backfill / 恢复局）与下帧观察的时序失配面未清点；无装配后实机验证 | design §2.6 补直写端族清点与逐个定性出口；landing 3.3 加实机验证期（≥3 局） |
| m4 | minor | 事实暂存块指位错（实际在 visit_open_shop 非 _open_shop_phase） | design §2.5 / landing 3.4 已改指 |
| m5 | minor | 「测试面随删」为幽灵删除面（sr-od-test 零 exec_fail 测试） | design §2.5 改「无在册测试，grep 判据覆盖注释残留」 |
| m6 | minor | journal.md 硬约束①在 §6 非 §4 | design §2.1 已改 §6 |
| m7 | minor | landing 正本更新清单把缺陷行型挂错 journal.md（正本在 game_state/README.md、fields.md、node-domain.md） | landing 正本更新清单重排：去 journal.md，补 README/fields/node-domain 具体段 |
| m8 | minor | 「7 态」实为 8 verdict；run_id 空串时闩行为未定义 | design §1.1 改 8 verdict 全列；§2.4 钉「run_id 空 → 只落证不停机」；landing 3.3 判据补该分支 |

正面核实（免复核）：observe 判定语义、抑制语义直接 return、现役表 ('sim:engine',)、失配数据统计逐项吻合、注入槽先例、not_effective≈金失配等价性写端支撑、_spend_unit 族唯一职责、删除面文档锚点、阶段依赖链——全部为真。

## 攻击者 B（核二·规范遵循 + 定稿试读）

**结论：核二有保留通过；定稿试读有保留通过（F1-F4 修订并复查后才达定稿门槛）。**

| # | 级别 | 发现 | 修订落点 |
|---|---|---|---|
| F1 | major | 豁免键 screen 依据失真（与攻击者 A B1 同根）+ 比对双方各有一个 sig、取哪次写入未钉死 | 一轮修订已改「现状缺口」表述；二轮补钉「键 = 本次 observe 写入的 sig.screen（logic 族恒 None 不参与）」+ screen=None 查表语义 |
| F2 | major | 正本更新清单漏 3.4 波及正本：shop.md L55/L81/L98、action_exec.md L37、logic-updates/refresh-shop.md L24；fields.md「如涉」悬空；prep.md L69 引 guards §4 实为 §3 | landing 正本更新清单补全四文档具体行；fields.md 点名段；prep.md 纠错入清单 |
| F3 | major | 3.4 grep 词表不完备（_unit_facts/_unit_meta/run_state import 不被覆盖）+ 扫描范围未限定 | landing 3.4 词表补全；扫描范围钉 = src/sr_od/application/currency_war + sr-od-test |
| F4 | major | 3.2 修模出口验收不可执行（「复现路径不再产生」无载体定义）+ journal 回溯无指路 | design §2.6 / landing 3.2：复现载体二选一（sim 重放单元序列 / 实机局后缺陷台账零新增）钉入判据与验收凭据；判读手段引 telemetry-reading.md |
| F5 | minor | journal.md 节号两处失真（§6 硬约束；§1-§4 账本机制） | design §2.1 已改；§1.2 已改 §1-§4 |
| F6 | minor | 「7 态」实为 8 verdict | 同攻击者 A m8 |
| F7 | minor | 引用寿命：bs_defect 易失档作依据指针；w494/w577 代际词 | design §1.1 改纯语义+时点（文件名仅作台账身份提及）；w577 → ADR-0456；w494 → 符号/语义表述 |
| F8 | minor | 幽灵测试面（同 A m5）+ 3.1 受影响存量测试未点名 | 已改；landing 3.1 补 test_cw_game_state.py / test_cw_game_state_consume.py 同步判据 |
| F9 | minor | L1 命令含未注册 marker legacy_baseline；全角逗号笔误 | landing 判据命令改 `-m "not slow"`；标点已修 |
| F10 | minor | 语义留白束（接线点/ts 格式/exempt 行形状/导入方向/stop_running 接收者/装配文件与闩载体/lookup 返回/截图手段） | design §2.1-§2.4 逐项钉死 |
| F11 | minor | 豁免出口与粒度纪律交互未决（('*', 'gold') 通配后门） | design §2.6 出口②钉「逐画面申报，禁字段级通配用于执行敏感字段」 |
| F12 | minor | cw_obs_reconcile 与既有 cw_reconcile.py 语义撞车 | 模块更名 `kernel/cw_mismatch_policy.py`（design/landing 全同步） |
| F13 | minor | README 索引出模板（attack.md/attribution.md 位置） | README 文档节只留 design/landing；attack.md 归进度行；attribution.md 注「3.2 批产出」 |

核查通过项：删除面符号实存且无第三消费点、装配点实存（CurrencyWarApp.__init__ 多注入槽同点）、guard/prep/flow 文档锚点实存、current_run_id_safe/注入槽先例/仓根锚定教训注释实存、suppress 语义与动机互证、telemetry-reading/sim-testing 参考线实存、测试落点有现成样例、总纲四节齐、landing 七件齐、无过程叙事、README 只串文档记进度。

## 复查状态
- 攻击者 A 定向复查（2026-09-16）：**9 项发现全部修复确认，核一通过**。新失真 2 项 minor 已修：①§1.1 存量分解改「102 完整失配行（86+7+9）+ 2 坏行片段」（坏行 = JSON 跨行截断残片，非失配行）；②§2.6 免刷持久锚改指 `classify_spend_unit` docstring free_refresh_proc 段（ADR-0456 编号仅存代码注释，decisions/ 无落盘）。归因情报：慢性模式实时复现中（统计间隔内 86→91 行），landing 3.2 已补「抓现行」指引。
- 攻击者 B 终确认（2026-09-16）：N1/N2/N3 修复确认，**核二通过、试读通过**。附注两条零阻塞项：①`read_game_state(` 实为 5 个调用文件（申报 3 个外另有 `obs/cw_observe_full.py`、`telemetry/cw_match_recorder.py`——路线①下不知画面名传 None 即合法，worker 复 grep 见到按「不知者传 None」处置，无需停手）；②§0 状态行括注属过程叙事，定稿改「定稿」时一并删除（已删）。
- **定稿达成**：攻击收敛（A：核一通过；B：核二通过 + 试读通过）+ 试读过——按 iteration-design §6 可立阶段任务。
