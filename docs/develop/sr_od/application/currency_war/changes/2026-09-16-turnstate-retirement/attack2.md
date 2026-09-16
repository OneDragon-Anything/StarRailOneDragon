# turnstate-retirement 设计对抗报告（r2 收敛复核）

- **被审对象**：`design.md` / `landing.md` / `README.md`（本目录，2026-09-16 按 r1 报告修订后的落盘版本）
- **审查角色**：设计对抗（r2 收敛复核；r1 报告 = 同目录 [attack.md](attack.md)，F-1…F-14）
- **日期**：2026-09-16
- **行号声明**：修订稿行号以本次亲读时点为准；代码证据行号沿用 r1 亲读时点并已复核未变。
- **r2 攻击范围纪律**：只攻修订新增面（阶段1 搬迁形态、adapter.py 同删裁定、match_archive 判别规则、泛化反查样式充分性），不重复 r1 已收敛面。

---

## 一、r1 发现消解判定（F-1…F-14）

| # | r1 发现 | 判定 | 依据（修订稿节名 + 要点） |
|---|---|---|---|
| F-1 | 阶段1 合并形态致 assemble 供给链断 | **消解** | design §2.2「阶段1 形态（原签名搬迁）」：三函数迁 economy_cycle.py 签名函数体逐字不变、`_budget` 仍返回 BudgetView、内嵌披露不变、"assembly.py 改为 import"；§2.4 新增取舍行（"先迁后并，合并归阶段2"）；landing §3.1 范围同口径 + 完成判据第 2 条给 `assemble` 供给链具体载体（test_cw_migration_direction_layer 原样绿）。r1 的 NameError 中间态不再存在。 |
| F-2 | 披露落点锚与"时点不变"在 armed 短路帧不相容 | **消解** | design §2 数据流图显式补画前置发射位（"短路帧不披露 = 现状逐位保持"）并把 disclose_budget 落点钉在"原 `_assemble_turn` 调用位（前置发射位判定之后，非 armed 帧才到达）"；§2.2 阶段2 形态同款 + "若未来要 armed 帧也披露，属行为变化，另批立项"；§2.4 取舍行 6；landing §3.2 判据增"armed 短路帧不披露语义逐位保持"。 |
| F-3 | 读端申报过期（engine_p1）+ sim 披露列判据无对象 | **消解** | design §2.2 现状行改为"recorder sess_* 透传 + cw_decision_trace 披露族封闭清单"，并如实申报"engine_p1 读端已亡（仅死 pyc）/sim 全目录 grep 零命中"；§2.5 验收总门 sim 冒烟收窄为"单一用途 = 决策分布无漂移确认"+ 完整可观测性盲区申报；landing §3.1 判据 3 同口径。（残余问题见 R2-2/R2-5，属修订新增面的新缺口。） |
| F-4 | grep 判据命中面外文件（adapter.py:5 / test_cw_unified_action_2b.py:137） | **消解** | adapter.py 整模块删（§2.1 #10、landing §3.2 文件面"adapter.py（删）"），死指针随模块消亡；test_cw_unified_action_2b.py 入 §2.1 #6 指针清单、§2.3 第 4 条、§2.5 表第 6 行（仅注释）、landing"§2.5 表列六文件"。 |
| F-5 | 失效指针清单漏项（mandate_state ×3 / cw_economy P6 锚 / schema:488 / decision_assembly 叙事 / match_archive） | **消解** | §2.3 改"泛化反查 + 已知命中清单"：反查样式 6 组样式、写端指针类（mandate_state）、锚例失效类（cw_economy BudgetView.interest_floor + prep_brain._budget 锚例、cw_screen_buy_cards、schema 装配键戳）、失效叙事（contracts.py）、cw_exec_state 两处、match_archive 判别规则；landing §3.2 文件面补 mandate_state.py 与 telemetry/match_archive.py。（残余表述问题见 R2-2/R2-3/R2-7。） |
| F-6 | cw_screen_buy_cards.py 注释属阶段2 范围但文件面漏列 | **消解** | landing §3.2 文件面补列 `cw_screen_buy_cards.py`（注释）。 |
| F-7 | 正本更新清单漏 4 处 | **消解** | landing 正本更新清单扩为 9 行：§0 头注定位句、不变式3（明确"改写为 Snapshot 隔离承诺…不变式本体不消失"的改写形态）、不变式5、§4.1（补前置发射位与披露落点）、G7、flow/README live 链（补前置发射位）、依赖方向段（同时删 L92 装配链句与 L93 obs→Snapshot 半部句）、篇导读行。 |
| F-8 | adapter.py 全孤儿未申报归宿 | **消解** | §2.1 #10 整模块删除裁定（含"零 import 方、零调用点"依据）；§1.3 解决到哪与外溢清单同步更新（"adapter.py 已随本批删除，不在其列"）；§1.3 外溢立项输入修正为"src 级生产消费方 = 零（曾有的模块级 import 方 adapter.py 随本批删除）"；§2.4 新增取舍行。r2 已复核无隐藏消费方：`strategies/impl/mandate_v1/__init__.py` 仅注册 StrategyState 工厂、不转出 adapter 符号；sr-od-test 对 `mandate_v1.adapter|action_to_atomop|PREP_SUBSTATE_NAME` 零命中（r1 grep 沿用）。 |
| F-9 | 在飞协调缺账本载体 | **消解** | landing §3.2 依赖栏："阶段1；execstate-dissolution 对应在飞阶段（同文件在飞面 = `cw_exec_state.py` + `telemetry/schema.py`，防冲突最小前置，两迭代账本对齐后开工）"——两文件齐、载体入依赖栏。 |
| F-10 | ADR-0571 死指针 | **消解** | §0/§1.3/§2.2/§2.3 统一改"裁决语义锚 = mandate_state.py 披露字段注释 + 守卫锁 test_cw_budget_disclosure；ADR-0571 档案已按用户令退役，历史副本不入 git"；§1.3 外溢表述同步（"牵接口形态历史裁决（ADR 档案已退役）"）；landing 判据豁免行改为"历史 ADR 记录/decisions 遗留/changes/ 豁免"。 |
| F-11 | 通用工程门缺失且指针不可解析 | **消解** | landing 首节"通用工程门（单一定义；源 = 项目 AGENTS.md「测试规范」10.4 与「提交流程与协作边界」11）"，内容与源相符（grep 消费点/ruff/受影响测试+全量/逐文件点名/git show --stat）；三阶段判据各加"通用工程门：本文件「通用工程门」节"引用行。 |
| F-12 | "均已亲读核实"过程叙事 | **消解** | §1.1 改"（依据 = projection_contract.md §6 G7 + 代码锚，锚以符号名定位）"。 |
| F-13 | §2.5 两处处置表述与实况偏差 | **消解** | migration_direction_layer 行补"保留测试同步清 assembly/contracts import 与失活助手（防 ImportError 连坐全文件）"；budget_disclosure 行补"断言右端 `turn.budget.*` 改独立现算 oracle（文件内已有 kernel 独立重算先例可循）"。 |
| F-14 | cw_exec_state"三处"与实况 2 处不符 | **消解** | §2.3 与 landing §3.2 均改"两处（`BenchChar.equips` 字段注释块 + `snapshot_copy` docstring）"。 |

**小结**：14/14 消解，无未消解、无部分消解。

---

## 二、r2 新发现（只攻修订新增面）

### R2-1 [低] [核一·试读] 阶段1 判据"test_cw_budget_disclosure 原样全绿——断言载体未改"与阶段1 自身选择矛盾（monkeypatch 接线缝必断）

- **发现**：修订稿把阶段1 定为原签名搬迁 + "cw_screen_buy_cards 调用点仅改 import 路径"（design §2.2 阶段1）。生产侧店开帧披露是函数内**懒加载**（cw_screen_buy_cards.py:1033-1037 每次调用取模块属性）；测试的两个接线锁正是经该缝注入替身——`monkeypatch.setattr(assembly_mod, 'disclose_budget_at_shop_frame', …)`（test_cw_budget_disclosure.py:162-163，宿主构造 :112-114）。import 改指 economy_cycle 后，patch assembly_mod 不再拦截生产调用 → `test_shop_frame_disclosure_wired_at_shop_entry` 与 `test_shop_frame_disclosure_failure_degrades_with_warning` 必红，缝目标须随迁 economy_cycle_mod。故"原样全绿/断言载体未改"（landing §3.1 判据 1）按文字不成立；文件虽在面内（"如涉 import 路径"），缝目标改写不属"import 路径"字面。
- **修正方向**：二选一——①判据 1 改"断言载体语义未改；monkeypatch 接线缝目标随 import 路径同步改 economy_cycle（两接线锁预期先红后绿）"；②更简方案：阶段1 保持 cw_screen_buy_cards 懒加载源为 assembly（assembly 转出 re-export），import 改路延至阶段2——则"原样全绿"字面成立、阶段1 生产面零编辑。

### R2-2 [低] [核一] 「engine_p1 读端已亡」的更正未传导到随迁注释；反查样式缺 `engine_p1`

- **发现**：design §2.2 申报"该 docstring 系过期转述，随 assembly.py 删除消亡"——但同一节的阶段1 形态是"签名与函数体逐字不变"（搬迁），语义清单又明言"随批迁注于新函数"：`_disclose_budget` docstring 的"读端只有 recorder.py 透传与 sim engine_p1 轮快照"（assembly.py:116）会原样搬进 economy_cycle 并存活过 assembly.py 的删除，"消亡"申报与自身搬迁形态矛盾。同款：mandate_state.py 披露字段注释块的"读端=recorder/engine_p1 轮快照"半句（:189/:196），§2.3 mandate_state 条目只写"改新写端 economy_cycle.disclose_budget"，未覆盖读端半句；反查样式（§2.3：`_disclose_budget|disclose_budget_at_shop_frame|snapshot_from_obs|prep_brain._budget|装配键戳|decide_from_turn`）不含 `engine_p1`，该残留不会被判据或反查拦截。
- **修正方向**：§2.3 mandate_state 条目扩为"写端指针与读端半句一并按 §2.2 现行实况（recorder sess_* + cw_decision_trace）改写"；阶段2 合并迁注时明示改写读端半句；仓内其余既有 engine_p1 陈旧指针（约 20 处，本批不新增失真）在 §1.3 外溢批（墓碑清点）立项输入中补一笔。

### R2-3 [低] [核一] §2.3 末条"decision_assembly.py 失效叙事 → 随模块删除消亡（#8/#10）"与 #8 实况不符

- **发现**：#8 只删 `snapshot_from_obs`，decision_assembly.py **模块本体存活**（"删后余量为空则整模块删"的条件不成立——`install_obs_ports` 及三个 sink 工厂留守，生产武装点 = currency_war_app.py:187-188）。模块头"observe 端口 snapshot_from_obs（…与 sim 合成器共享字段映射语义）"与"观察端口半部"定位叙事（decision_assembly.py:1-7、:127 段头）随 #8 失锚，须按反查样式改写；现表述会让 worker 先跳过（gate 的 `snapshot_from_obs` 项最终会强制，但按错误指示走会绕一圈）。
- **修正方向**：§2.3 末条拆开——adapter.py 确随 #10 模块删除消亡；decision_assembly.py 改为"模块头观察端口定位与 snapshot_from_obs/sim 合成器叙事随 #8 改写（模块本体因 install_obs_ports 存活）"。

### R2-4 [低] [核一] 新增判据"armed 短路帧不披露语义逐位保持"无具名验证载体

- **发现**：landing §3.2 判据新增该行为保持项，但验收凭据形式（grep 清单 + L3 全量 + sim 批头分布对照）无一辖它：sim 对该面结构性不可见（设计自报）；既有测试不辖 armed 分支（test_cw_prep_contract_shape 走非 armed 桩路径；无任何测试断言"armed 帧披露零调用"）。该判据现状只能靠 code review 承载，而设计未明示。
- **修正方向**：§2.5 增一条单帧锁（armed 态 session 桩披露缝断言零调用 + 非 armed 帧断言恰一次调用；锁出处 = design §2.2 落点规则），或在判据旁明示"以 code review 承载，无测试载体"。

### R2-5 [低] [核一] 阶段1/阶段2 验收凭据"sim batch 批头分布对照"缺对照基线来源

- **发现**：landing §3.1/§3.2 验收凭据均为"sim batch 批头分布对照"，但未写对照物：单批无 baseline 时"分布无漂移"不可判定（strategy-work §4：改前基线→改后同参对照、两侧同池指纹；"没跑基线的改后达标不构成证据"）。且设计自报 sim 对本批两面结构性不可见——该对照对本批无鉴别力，只有通用回归价值。
- **修正方向**：二选一——①降格为"冒烟跑通（退出码 0 + 批头产出非空）"，披露等价验证明确归 test_cw_budget_disclosure 与实机 recorder 行；②保留分布对照则补"改前同参基线批（同池指纹）"义务。

### R2-6 [低] [核二] design §0 状态与 README 进度失同步

- **发现**：design §0"状态：对抗审中"，README"迭代设计:草案"——两处状态位（iteration-design §2.1 模板字段 + §4 README 进度）须一致；本次只改了 design 侧。
- **修正方向**：README 改"对抗审中"（或按编排者口径统一）。

### R2-7 [低] [核一] match_archive 判别规则的"改写"分支缺目标内容，且本实例是两可混合句

- **发现**：§2.3 规则给两桶（历史口径描述 = 保留 / 现行时态声明 = 改写）+ worker 判别申报义务，可操作；但 ①"改写"分支未写改写成什么——worker 需自行撰写新语义文本 = 停手令射程内的设计决策；②本实例（match_archive.py:1266-1268"prev 侧「不可信」依赖 decision_assembly 对 readable=False 帧写 hp=None 的远端约定"）是混合句：它描述的是**存档数据的既有写入约定**（历史口径，对既有档案恒真），但锚定了将删的写端符号——按"保留"桶处理后，读者沿 `decision_assembly` 追写端会扑空（writer 是已删的 snapshot_from_obs）。
- **修正方向**：规则补一句"混合句按『历史口径描述』保留语义，符号锚改纯语义描述（本实例可作『存档写入约定：readable=False 帧 hp=None』），禁锚已删符号"——与 AGENTS 注释规范"出处 = 持久索引或纯语义描述"对齐。

### R2-8 [中危] [核一] landing §3.2 文件面漏列 economy_cycle.py——阶段2 核心操作（合并）的落点文件不在允许面

- **发现**：§3.2 范围含"§2.2 阶段2 形态（`_budget`+`_disclose_budget` 合并为 `disclose_budget -> None`…）"，而阶段1 后三函数住 economy_cycle.py——合并即编辑 economy_cycle.py（合并实现 + bridge 新 import 的来源模块）。§3.2 文件面（landing:23）枚举了 17 个 src 文件，**无 economy_cycle.py**。worker 执行到合并步即撞文件面墙（停手令）。
- **修正方向**：§3.2 文件面补 `economy_cycle.py`（合并）；顺带在 design §2.2 阶段2 形态写明"合并后 `disclose_budget` 住 economy_cycle.py，bridge 自该模块 import"（现文本只暗示）。

### R2-9 [中危] [核一] assembly.py 阶段2 后成纯 docstring 空壳，整模块删除未申报——#10（adapter.py）同型问题在 assembly 本体复发

- **发现**：阶段2 删 `assemble`/`_direction`/`hoard_consumer_domain`（#2-#4）并随合并移除对 economy_cycle 三函数的转出 import 后，assembly.py 余量 = 模块 docstring（:1-16，且含 `_disclose_budget` 字样，会被 §2.3 反查样式命中）+ `_tracking_view` 墓碑注块（:60-65）——恰是 2026-09-16 用户裁定废除的"注记留码"形态，也是本批立项要清除的孤儿模块形态。设计与落地均未申报 assembly.py 整模块删除（#8 对 decision_assembly 有"余量为空则整模块删"措辞，assembly.py 无对应句；landing 只写"assembly.py（删余部）"）。与 F-8 同型：修订在 #10 消解了 adapter.py 的孤儿化，却漏了删除面自身的主模块。缓解面：反查样式 `_disclose_budget` 会命中空壳 docstring，逼 worker 处置——但"删 docstring 留空文件 vs 删整模块"是设计决策，不该留给在飞 worker 拍板。
- **修正方向**：design §2.1 注行补"assembly.py 于 #2-#4 及合并完成后余量为空，整模块删（同 #8 措辞）"；landing §3.2 文件面"assembly.py（删余部）"改"assembly.py（整模块删）"。复核过整删无第三方引用：stage-2 后测试三文件对该模块的 import 均在 §2.5 处置面内，src 消费方仅 mandate_v1_strategy（在面内）。

---

## 三、r2 独立攻击面结论（按任务书四点）

1. **阶段1 搬迁形态自身**：自洽——原签名搬迁保住 `assemble`→`TurnState.budget` 供给（F-1 消解），无循环 import（economy_cycle 不反向依赖 assembly；`_budget` 体内对 obligation 的同模块自引用惰性 import 搬迁后仍合法），`DEFAULT_REGISTRY` 等模块顶 import 随迁属机械步骤。遗留两个表述级缺口：R2-1（判据矛盾）、R2-2（docstring 搬迁与"消亡"申报矛盾）。
2. **adapter.py 同删裁定**：成立——零 import 方/零调用点双复核（含 `__init__.py` 非转出、测试仓零命中），删除后 contracts.py 的 src 级 import 方归零，§1.3 外溢立项输入表述随之变准。无新发现。
3. **match_archive 判别规则**：可操作但"改写"分支缺目标内容，且对本实例（混合句）两桶皆不完全适配——R2-7。
4. **泛化反查样式充分性**：六组样式覆盖 r1 F-5 全部点名类与 gate 互为补充（BudgetView/TurnState 类由 gate 兜底）；两个缺口：缺 `engine_p1`（R2-2）、对空壳模块的处置无着落（R2-9）。`decide_from_turn`/`snapshot_from_obs`/`prep_brain._budget`/`装配键戳`/`_disclose_budget` 逐一样式对已知命中集试跑均收口。

---

## 四、三阶段试读清单（r2 重跑）

| 阶段 | 判定 | 说明 |
|---|---|---|
| 阶段1（原签名搬迁） | **过** | 搬迁形态自洽、供给链判据有具体载体（migration tests 原样绿）、零行为变化可验（披露语义锁原样跑）。R2-1（判据"原样全绿"措辞）、R2-5（对照基线）为验收口径修订建议，不阻开工。 |
| 阶段2（物理删除） | **有条件过** | 删除面 #1-#10、反查收口、依赖栏、判据均齐；但 R2-8（economy_cycle.py 漏列文件面，合并步撞墙）与 R2-9（assembly.py 整删未申报，空壳处置撞停手令）两处落在文件面/停手令射程——两行修订后全过。 |
| 末阶段（正本更新） | **过** | 清单 9 行齐备（含不变式3 改写形态、前置发射位补画），对照实现清零可验收。 |

---

## 五、收敛判定

**未收敛（一步之遥）。** 阻断 0；r1 的 14 项全部消解；r2 新发现 9 项（中危 2：R2-8/R2-9，均为修订新增面的一行级遗漏——文件面漏列与整模块删未申报；低 7：R2-1…R2-7）。按本次收敛门槛（无阻断且试读全过），阶段2 因 R2-8/R2-9 未全过。两处中危的修订量 = landing 文件面补 `economy_cycle.py`、"assembly.py（删余部）"改"整模块删"各一处 + design 对应两短句；低危项建议随定稿顺手落（措辞/载体补强，无语义未定项）。修订后再走一轮轻量复核（只验 R2-8/R2-9 落点与 R2-1 判据措辞）即可判收敛。

## 附录：r2 复核手段

- 亲读：修订后 design.md/landing.md/README.md 全文；对照 attack.md（r1）逐条回查。
- 新增面复核：`strategies/impl/mandate_v1/__init__.py` 全文（adapter 转出排查）；`telemetry/match_archive.py:1248-1287`（判别对象实文）；test_cw_budget_disclosure.py 懒加载缝段（:92-168）与生产侧 cw_screen_buy_cards.py:1026-1043 复核；currency_war_app.py:185-188（decision_assembly 存活武装点）；assembly.py 结构清点（阶段2 后余量推演）。
- 沿用 r1 已核实且未变的证据：mandate_v1_strategy.py:55-58、bridge.py:185-196、entry.py:432-946、decision_assembly.py:22-24/36-76/129-195、cw_economy.py:268/1147-1148、mandate_state.py:172-208、schema.py:301/479-500、cw_decision_trace.py:121-139、engine_p1 pyc 孤儿、sim 五组 grep 零命中、sr-od-test 六测试文件相关段。

---

# r3 轻量复核（2026-09-16，针对 R2-1…R2-9 修订稿；只验指定点，不重开全面攻击）

## 一、R2 发现消解判定（9/9）

| # | R2 发现 | 判定 | 依据（修订稿节名 + 要点） |
|---|---|---|---|
| R2-1 | 阶段1 判据"原样全绿"与缝必断矛盾 | **消解** | landing §3.1 判据改"test_cw_budget_disclosure 全绿——缝目标随迁后断言本体原样"；文件面改"（monkeypatch 缝目标随迁）"；design §2.5 行写明"懒加载 import 改指后原缝必断"。措辞与实况相容（先红后绿被预告）。 |
| R2-2 | engine_p1 更正未随迁 + 反查样式缺样式 | **消解** | design §2.3 反查样式加 `engine_p1`；新增"过期读端叙事随迁面"条（economy_cycle 迁入 docstring 读端句 → 阶段2 更正）；mandate_state 条目扩"读端半句 → 新读端口径"；§2.2 现状行改"该过期句随逐字搬迁进入 economy_cycle，阶段2 按 §2.3 更正"——r2 指出的"消亡 vs 搬迁"自相矛盾已消除。 |
| R2-3 | decision_assembly"随模块删除消亡"表述错误 | **消解** | §2.3 末条拆分：decision_assembly"模块本体因 install_obs_ports 存活，按反查样式改写"；adapter 随 #10 消亡。§2.1 #8 同步改"模块本体因 install_obs_ports 存活（仅删半部）"。 |
| R2-4 | armed 不披露判据无验证载体 | **消解** | design §2.5 budget_disclosure 行补"armed 短路帧不披露单帧锁（armed 帧入口断言披露字段零写，承载 §2.2 落点规则的验证）"；landing §3.2 判据挂"载体 = §2.5 新增单帧锁"、验收凭据含"armed 单帧锁"。断言目标与出处明确，实现自由度（真 armed 判定 vs 桩前置发射位）不构成再设计项——两者证同一性质（短路先于披露）。 |
| R2-5 | sim 分布对照缺基线且无鉴别力 | **消解** | design §2.5 验收总门降格"冒烟跑通（分布对照无鉴别力、不作判据，冒烟仅证流程不炸）"；landing §3.1/§3.2 判据与验收凭据同步改"冒烟跑通（记录）"，分布对照撤销。 |
| R2-6 | design §0 与 README 状态失同步 | **消解** | README 进度改"迭代设计:对抗审中"，与 design §0 一致。 |
| R2-7 | match_archive 规则改写分支缺目标 + 混合句无桶 | **消解** | §2.3 判别规则扩三支：纯历史口径 = 保留；纯现行声明 = 改写；混合句 = "保留语义、符号锚改纯语义描述（去符号名，语义自足）"——与 AGENTS 注释规范"持久索引或纯语义描述"对齐。 |
| R2-8 | §3.2 文件面漏 economy_cycle.py | **消解** | landing §3.2 文件面补"`economy_cycle.py`（§2.2 阶段2 合并落点：…合并为 `disclose_budget -> None`）"。可关闭性：合并未做则 bridge 新 import 无源 → L1 必红，判据机械闭合。 |
| R2-9 | assembly.py 整模块删未申报 | **消解** | design §2.1 #2 补"#2/#3/#4 删除 + §2.2 三函数迁出后…无剩余符号（余部 = 模块头 docstring 与墓碑注块）→ 整模块删"；landing §3.2 改"assembly.py（整模块删：删除面出清后无剩余符号）"。归宿申报成立（空壳 docstring+墓碑注 = 被废除的留码形态，整删与 #8/#10 口径一致）。 |

## 二、r3 残留发现

### R3-1 [中危] [核一] `engine_p1` 进 gate 使阶段2 判据按面不可关闭：约 16 个面外文件的既有陈旧命中无从处置

- **发现**：本次修订把 `engine_p1` 同时加进了 §2.3 反查样式（正确）与 landing §3.2 完成判据的 grep 零活引用模式（过度）。gate 现为"…|decide_from_turn|engine_p1` 零活引用（历史 ADR 记录/decisions 遗留/changes/ 豁免；flow/ 正本留末阶段…）"——但仓内 engine_p1 陈旧指针是 **sim-redesign 前的既有债**，本批不新增失真，且命中遍布面外文件（r1 grep 实证约 25 处 / 16 文件：cw_battle_calib.py:412,425、cw_deploy_logic.py:951,1245、cw_economy.py:262,319,393,568、telemetry/query.py:31、cw_game_state.py:959、cw_intention.py:2698、cw_launch_admission.py:3,49,237、cw_launch_arbitrage.py:28、predicates.py:407、cw_strategy_session.py:194,210、cw_screen_supply_node.py:45、cw_vocab.py:434,821、cw_exec_state.py:187、schema.py:465、entry.py:181、shop.py:484 等）。豁免面（ADR/decisions/changes/flow 正本）一个都不覆盖它们；面内文件也多仅许可动特定注释行（如 cw_exec_state 仅两处、schema 仅 :301/:488）。worker 按判据执行 = 必须改约 16 个面外文件（越面）或判据永远红（不可验收）。§2.3 反查样式的"命中处逐点处置"措辞同病（worker 义务被写成全仓处置）。这正是 r2 R2-2 建议刻意避开的方向——当时建议的是"反查样式加 engine_p1 + **面内**随迁注释改写；面外既有残留申报归墓碑清点外溢批（§1.3 立项输入补笔）"，未建议进 gate。
- **修正方向**（一行级）：①landing §3.2 判据的 grep 模式**去掉 `engine_p1`**（恢复 r2 版七符号）；②§2.3 反查样式保留 engine_p1 但加辖域限定："engine_p1 命中处置辖域 = 本批文件面与随迁注释；面外既有残留逐处清点申报，归 §1.3 墓碑清点外溢批立项输入"；③§1.3 外溢条补"仓内 engine_p1 陈旧指针（约 25 处/16 文件）"一笔。

## 三、三阶段试读（r3 重跑）

| 阶段 | 判定 | 说明 |
|---|---|---|
| 阶段1 | **过** | 搬迁形态、缝目标随迁、判据载体全部就位。 |
| 阶段2 | **有条件过** | 删除面 #1-#10、文件面（含 economy_cycle/assembly 整删/decision_assembly 存活申报）、armed 单帧锁载体齐备；唯 R3-1 使 grep 判据按面不可关闭——一行修订后全过。 |
| 末阶段 | **过** | 清单 9 行未动，仍与实现后一致。 |

## 四、r3 收敛判定

**未收敛（仅剩 R3-1 一项中危，一行级修订）。** 无阻断；R2-1…R2-9 九项全部消解；唯 gate 混入 engine_p1 使阶段2 判据按面不可关闭。按本节"修正方向"三点落盘后，无需再开全量复核轮——编排者对照 R3-1 修正方向三点逐字核对即可关闭收敛。
