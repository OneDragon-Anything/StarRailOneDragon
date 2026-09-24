# 设计对抗报告 · 第 12 轮（定稿门确认审）

> 审查对象：design.md / landing.md / README.md（当前稿）。
> 三核并重（iteration-design.md §7）；全部 文件:行号/函数名/字段名/表值/文档锚 均本轮直调复核（禁转述），行号漂移按任务书 ±3/符号锚纪律处置。
> 结论：**未收敛到零发现——1 中 4 低**；无高危。design↔landing 全量同步复查发现 1 处失同步（含 1 项前轮已在设计侧回写、落地侧未跟进的复发形态）。

---

## 发现清单

### R12-1 [中] design §2.7 要求的 `strategy-docs/README.md:54` 阅读导航句改述在 landing 全程缺席（design↔landing 失同步；硬规则 4）

- **位置**：design.md:100（「`:54` 阅读导航句『18-27』随批改述『18-30』……本批顺手收口」）↔ landing.md:29（3.3 范围只写「`strategy-docs/README.md` §2 分篇表增 30 行」）、landing.md:38（验收凭据 grep 词表无此项）、landing.md:62（正本更新清单「`strategy-docs/README.md` §2 分篇表 ← 3.3」）。
- **发现**：design.md:100 的 README 编辑面是两项——①分篇表增 30 行；②`:54` 导航句「18-27」改述「18-30」（已直调核实：strategy-docs/README.md:54 现文「……18-27 是画面/专项面……」，且 §2 表末篇已到 28，导航句确属 env/29 两批先后漏改的过期句）。landing 3.3 的范围/完成判据/验收凭据/正本更新清单四处均只携带①、不见②。阶段小节 = 账本唯一源（iteration-design §3.1），照小节 `dag.py add` 派工则该编辑面必漏，落批后导航句继续过期——恰是设计自述要收口的漏改形态。此项为前轮已在**设计侧**回写、**落地侧**未跟进的修订后全量同步复查缺口（硬规则 4 卡点类复发）。
- **修正方向**：landing 3.3 范围句补「README `:54` 阅读导航句『18-27』→『18-30』」；正本更新清单该行同步改为「§2 分篇表与 `:54` 导航句 ← 3.3」。

### R12-2 [低] landing 3.3 完成判据「五处指针」无枚举，验收对照不可复算

- **位置**：landing.md:36（「五处指针内容逐条对照 design §2.7」）。
- **发现**：design §2.7 的指针型编辑位按任何自然口径都数不出唯一的 5：25 头注拆分注（1）、13 §1 行 + §2 E4 行（2）、README §2 增行（+ R12-1 的 `:54` 项）、08 E4 行（1）、三份画面文档指针（3）、16 号稿销账行（1）——按「文件」数是 7，按「编辑位」数 ≥10。执行者与验收者各数各的 = 判据不可复算（iteration-design §3.1「判据可验证」卡点）。
- **修正方向**：landing 3.2 验收词表处枚举五处（或改为「§2.7 全部指针面逐条对照」并把计数词删去）。

### R12-3 [低] 幸存闸行为锁的 docstring 旧语义叙述无「语义过期」注记义务（strategy-work §5）

- **位置**：design.md:81（「strategy 级 stub 两处……在 flow 方法名保留后继续有效、不随删」）；sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens_step3.py:130-136（`test_supply_refresh_gate_left_semantics` docstring「剩余 0 / None → 零点击不按刷新终结，重调一次决策按原评分选卡」）。
- **发现**：该测试非纯 stub——是完整的 op 闸行为锁（注入 pick 序列驱动）。闸内嵌 decide 后，生产路径上「left 0/None → 建议刷 → 重调按评分选」不可达（design §2.6 自认「读缺分支与按评分选均不可达」，已直调核实 cw_screen_supply_node.py:275-288 门序与 :274 闸读源同容器同值）；锁以注入序列锁的是 op 防御分支机械，行为仍绿，但 docstring 叙述的生产语义过期。strategy-work §5：「语义演进时旧断言随改，docstring 记一句为什么旧语义过期」——本批对该锁只申报「不随删」，未在任何阶段落这条注记义务。
- **修正方向**：design §2.6 测试面补一句（或 landing 3.2 范围补该文件 docstring 注记）：该锁 docstring 随批补「闸内嵌后 0/None 建议刷不可达，本锁只辖 op 防御重调分支」语义过期注。

### R12-4 [低] §2.3 凑星判据 bench 入参形状与 `same_star_count` 注解形状不同层，未申报

- **位置**：design.md:61（「`bench` = `bench_units_of(gs)` 槽序」）↔ cw_merge_simulate.py:424-426（`same_star_count(name, star, bench: list[BenchSlot | None], deployed: list[Unit | None] | None = None)`）。
- **发现**：`bench_units_of` 返回 `list[Unit]`（cw_game_state.py:3654-3663），传给注解为槽表形状的 `bench` 形参。运行时正确已核实：`_entry_identity`（:93-107）对裸 `Unit` 走 `isinstance(x, Unit)` 分支出身份，占位件/空槽在 `bench_units_of` 侧已被滤除，计数与槽表口径等价；`deployed` 侧的二元组 fail-closed 静默漏域机制同样核实成立（:110-119 对非 BenchSlot/Unit 形状返 None 跳过）。但「注解形状 ≠ 实参形状」未在设计申报——后续任何人按注解收紧校验或按注解读形状，都会把这处正确代码读成违例。
- **修正方向**：design §2.3 该句补半句申报：「注解为 `BenchSlot` 槽表形状；条目身份协议（`_entry_identity`）对裸 Unit 同样成立，两口径计数等价」。

### R12-5 [低] landing 3.2 grep 三段式验收的豁免集枚举不全（历史 changes/ 工件 + 迁移后仍真实的存活指称）

- **位置**：landing.md:23（「③白名单外零命中」；白名单 = flow 入口方法名/cw_screen_supply_node 调用点/cw_strategy ABC/stub 两处/3.3 前的 docs 旧指针（3.3 收口）/`changes/` 本迭代工件）。
- **发现**：全仓 grep `decide_supply`/`SupplyPick` 在 3.2 时点还将命中两类白名单未列的合法面：①**其他迭代**的 changes/ 历史工件——如 `changes/2026-09-21-event-refresh-unify-supply-pick/design.md:30/:41`、`changes/2026-09-16-strategy-terminal-contract/`、`changes/2026-09-16-strategy-input-unification/` 多处 decide_supply 记载（过程件寿命豁免、禁改）；②**迁移后仍真实的存活指称**——正本 `flow/README.md:81`（pick 族清单含 decide_supply 入口，入口保留即此行真实）与 `screens/supply.md:3/:39`（描述 `match.strategy.decide_supply()` 存活调用），二者不属「3.3 收口的旧指针」，字面执行会在白名单外命中。执行者只能自行裁定或悄悄扩白名单——判据换算由执行者补齐（iteration-design §3.1 可验证性）。
- **修正方向**：白名单补两类豁免：「各迭代 `changes/` 历史工件（寿命豁免）」「迁移后仍真实的入口指称（flow/README.md pick 族清单、screens/supply.md op 调用叙述）」。

---

## 本轮实际攻击过的面（全量直调，非转述）

1. **三份审查对象**逐行读毕；design↔landing↔README 全量同步复查（阶段四件套齐/依赖序/工程门自包含/README 锚存在性——attack.md~r11 共 11 份报告文件全部实存，r12「启动后创建」注记属实）。
2. **代码锚逐点打开核对**（design 引用的每个 文件:行号）：cw_events.py :1/:1003/:1007/:583/:585-596/:588-592/:599-605/:609-612/:616-647/:633-635/:637/:641-642/:786；cw_equip_value.py :36/:42-80/:163-189/:192-210（tier 语义、key 可含重复按 count 计需、(tier,base) 字典序严格大于换位=并列取先，与 §2.2 排序语义逐位同构）；cw_node_obs.py :21/:206/:215（三钻集合）；cw_game_state.py :114（TYPE_CHECKING）/:209（域版本 2）/:2124（board=羁绊计数派生，禁双写）/:2146（supply_refresh_left 剩余语义）/:2210-2229（溢出位单槽锚）/:3645-3663（deployed_rows_of 二元组/bench_units_of）；cw_comps.py :102-112（core_chars/shared_chars 入名单、transition_chars :112 不入——「字段=102-111」所指两名均在锚区间内）；cw_intention.py :1123-1194（pair_target_comp 构造未传 key_equips→恒空，申报②成立）/:2075-2077（降格清锁防御位）；cw_merge_simulate.py :93-119（_entry_identity fail-closed）/:337（同名同星 ≥3 合一全场域）/:424-433（same_star_count 单一源）；cw_effect_inventory.py :1502-1505（席满拒落零写）；cw_action_report/pick_supply.py :48（1★ 先验）；cw_screen_report/supply_node.py :16/:41；cw_sim_backend.py :78/:573-585（恒置一带钻槽）；cw_sim_ports.py :128-138；cw_sim_obs_gen.py :204/:309（观察腿在产）；cw_replay.py :10-12（--diff 已退役）；cw_survey19_hooks.py :1-8/:46-56；cw_vocab.py :728/:915；cw_pick_supply_action.py :37；cw_screen_supply_node.py :8-20/:39-40/:99/:189/:218/:242-245/:252/:264/:272-280/:275/:281/:337-338；flow.py :326/:327/:335-352/:353/:516-518/:544-545/:546/:547/:712-718/:719-740/:729-731；invest_env.py :388-401（闸内嵌 fail-closed 同构先例）；line_value.py :16/:44/:62（降格未锁口径）；mandate_v1 目录清单与 encounter.py:1（「已搁置让位」逐字）。
3. **申报机制沿数据流逐跳验证**：sim 结构性盲区申报（:252 门→:264 gate→:275/:281 门内→:218 唯一写点→sim_or_live_observation 改道不执行 live_read→:337-338 兜底）五跳全成立；「两前置齐后 sim 可见」的表述与占位分布机制自洽；重调路径唯一触发面（锚缺）推导核实；`_sup_opts` 写点唯一性 grep 核实。
4. **删除面完备性**：src+sr-od-test+tools 全仓 grep `decide_supply`/`SupplyPick`/`supply_reroll_decision`——所有命中逐一归类（删除面/收口清单/白名单/保留面），「在册无 kernel 侧专用锁」「src 无 SupplyPick 外部类型 import」「supply_reroll_decision 零消费」三申报成立；`sim/checks/ledger.py` 目录不存在（16 号稿死引用申报成立）；`check_equip_value_*` 双仓零命中。
5. **文档锚逐点打开核对**：25 号稿 :3/:3-4/:11/:18（族清单逐屏清点恰 11）；13 号稿 :11（OCR 纪律字面辖域）/:18（decide_invest_env 改指先例）/:20/:40；08 号稿 :19（E4 行逐字，component_demand/hoard_gaps 在 P42 单篇 :4/:27 实存）；16 号稿 :74（挂账行逐字+「带钻支配（零参数已就位）」引文逐字）；strategy-docs/README.md §2/:54；screens/supply.md :12/:33/:40/:63/:80/:88；docs/game/screens/currency_war_supply.md :19/:37/:39/:57；货币战争-补给.md :32/:39；math_proofs.md P40/P42/P97/P81 索引行（P42 🔴 待标定 = λ 流/partner 到位率，与设计表述一致）。
6. **跨批协调核对**：env 批 design:18、29 批 design:23 承接登记；29 批 landing:33-34（decide_event 约 270 行删除、本批行号锚重核义务、30 号稿编号互相承接、13 号稿增补共用判据节）；共享编辑面 8 处逐处对上（flow.py:21 行、cw_vocab.py:33 行、cw_events 模块头:67 行、08 E2/E15:60 行）；sim-redesign design:70/:104/:267 三处复用面声明逐字核实，交接条款与 29 批对 decide_event 的交接先例同构（landing:34）。
7. **核二规范**：宪法五/六条文本（00_framework §1 第 5/6 条，2026-09-23 裁定日期逐字）；strategy-work §1 零调参（本批零新数字；EQUIP_GENERIC_VALUE 消费=16 号稿在册处置执行、所有权申报在位；凑星=布尔零参数）、§3 开关（默认无开关合规）、§4 验证阶梯（可观测性声明分层准确、cw_replay --diff 豁免有代码依据、实机锚事前写定）、§5 单帧锁（位置模式/语义断言/⑦跨域构造）、§6 对抗纪律；iteration-design 硬规则四条（依据就地标注逐条抽验全中；试读——3.1 照单可开工、判据语义每个分支有答案；无过程叙事——design/landing 正文无轮次/修订措辞；全量同步复查=本轮执行，得 R12-1）；AGENTS.md 测试规范/提交流程（landing 工程门引文逐字）；01_math_framework §6 数字三形态（本批无新数字入决策门，【拍】章程增补义务不触发）。
8. **核三治本**：§1 归层（分层语义+语义）与 §2 修法对应核实（kernel 剪除=宪法五治本、文档拆分=宪法六治本、判据改形=16 号稿在册处置的执行批）；跨件半问已在 §2.8 登记（两账 inline 副本第二例，战术权衡+抽公共读口挂后续批，合 AGENTS.local 症状修法申报义务）；「明确不解决」面（E4 derive/重刷期望账/augment 改写面/sim 双前置）均有归属与申报，SupplyOption 单装备读面缺口与 env 批 design:96 机制记载互证。
