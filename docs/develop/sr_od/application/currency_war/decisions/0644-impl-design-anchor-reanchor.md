# ADR-0644: IMPL_DESIGN 规格锚重锚(断锚面处置与编号族映射)

- **Status**: accepted(T-301 重锚批;纯文档零行为,重锚前该批引用禁当可执行规格)
- **Date**: 2026-09-11
- **关联**: ADR-0585 §5(CONTRACT_SERIES_DECISION 灭失重锚先例,同款处置模式)、ADR-0565:35(自认「契约 anchor 保留历史指针」,其 §2.3 锚随本批获得现行落点)、dd-007(Status 所引 IMPL_DESIGN §6.1 语义,映射见下表;ADR 正文 immutable 不回改)、ADR-0366/0368(位面轮次单一源)、dd-020(序列决策契约权威链)

## 1. 背景(断锚事实链)

mandate_v1 契约域数十处注释/注册表锚引用「IMPL_DESIGN §x / R19x 症N」(T-298 规范验收发现 F1:全仓 glob `IMPL_DESIGN*` 零命中,设计正本↔实现对账对该批引用不可执行)。物理灭失链(git 全程可溯):

1. `IMPL_DESIGN.md` 路径演化:`redesign/`(ba1176c68 入库)→ `design/`(0bd7a1c39)→ `archive/design/`(00a5eaa1a 归档);
2. commit **90f1acdb2**(用户裁定「删除旧设计文档」):删 IMPL_DESIGN.md、IMPL_FIX_LEMMAS.md、design_telemetry.md 三件(定性=「已丧失可执行性的 R1-R189 修复史」),保留 design_economy.md 等八件;
3. commit **4e32b2e4**(用户裁定「吸收后删除」):删 archive/ 整树含 design_economy.md、design_latch.md(明文「**内容已塌缩进 strategy-docs 与 flow**」;文档树终态=strategy-docs/flow/decisions/proofs/prereg/sim 六类)。

即:被引用的设计正本不是「写错了」,而是**按用户裁定分两轮退役**;strategy-docs/README.md §3 已声明旧树「素材已删除、git 历史可溯、R 标链/勘误史不搬入本链」。缺口只在代码注释面——注释里的死路径与死节号没有跟着这次退役更新。本批即补这一步。

**取回口径(持久索引)**:

- 三件修复史:`git show 90f1acdb2^:docs/develop/currency_war/archive/design/<IMPL_DESIGN|IMPL_FIX_LEMMAS|design_telemetry>.md`
- archive 整树八件(含 design_economy/design_latch):`git show 4e32b2e4^:docs/develop/currency_war/archive/design/<文件>.md`

## 2. 编号族重锚映射(单一源,逐族)

| 被引编号族 | 原语义 | 现行落点(重锚后引用这个) |
|---|---|---|
| IMPL_DESIGN §1(依赖方向/包树/状态函数层纪律/lambda_death PL 键行) | 模块结构与分层纪律 | 依赖方向与权限=01_math_framework §1;状态函数清单与单一源纪律=01_math_framework §5;lambda_death PL 键结构=proofs/validations/P51_V3_REBUILD v3.3+statefn/lambda_death.py 本体 |
| IMPL_DESIGN §2.0(λ 姿态架构/升档器只升不降/λ 合法消费形态) | λ 危险信号层哲学 | 00_framework §4(姿态架构)、§6(λ 表使用纪律);不变量=01_math_framework §8 |
| IMPL_DESIGN §2.1-§2.6/§2.8(七面判据正文:买/卖/升级/刷新/压库/装备/横切) | 判据域规格 | 01_math_framework §3.1-§3.8(每面一个权威);商店域细则=11_shop_decisions;装备语义=18_equip_wear_semantics |
| IMPL_DESIGN §2.10(组-端表/canonical 枚举/审计代码形态) | 数字取端与零调参纪律 | 01_math_framework §6(数字三形态章程)、§9(零调参审计结论);各消费位取端以代码注释与命题号为锚 |
| IMPL_DESIGN §2.12(前置缺陷清单,R92-4 sim 利息 flat) | 已修复的落码前置缺陷 | 修复已兑现=sim/engine_p1.py 利息行 flat 分量;缺陷登记原文=git 取回 |
| IMPL_DESIGN §3.1/§3.2/§3.3/§3.4(执行序/四硬约束/输入缺失定向 fail/EV 只追加) | 骨架行为层规格 | 02_mandate_layer §3(M1-M7 逐条)、§4(硬约束封闭定义)、§5(按可逆性定向 fail)、§2+§7(三层权限与决策机器划界) |
| IMPL_DESIGN §4.2.1(臂①旁路集函数级枚举表) | 旁路权威表 | **criteria/__init__.py `BYPASS_TABLE`=现行单一源**(R199 批既立「以代码表实况为单一源,表-代码逐行同步」) |
| IMPL_DESIGN §4.2.2(判据契约纪律;R198b=K 空窗回退规格补注) | 判据契约 assume-guarantee | **criteria/contracts.py=现行单一源**(CONTRACTS 注册表+模块 docstring;R198 批产物自足);违例键=contracts.ensure_contract **动态构造**的计数键 `criteria_contract_violation:<模块>.<函数>`(键写点与语义单一源=criteria/contracts.py;telemetry/schema.py 无该键静态声明,schema.py 仅承载 depsilon_advisor_violation/f7_exempt_emission 等静态声明键) |
| IMPL_DESIGN §5.1(判前锁 v6 挂账清单,16+1 行) | 正式 A/B 判前锁 | **sim/ab_core_swap.py `_v6_row_specs`=现行单一源**(清单的可执行镜像,逐行带落地判据);行 7/11/13 的键语义=telemetry/schema.py 键声明 |
| IMPL_DESIGN §5.2(观察键全集) | 遥测键名与语义 | telemetry/schema.py(键声明单一源);登记节原文=git 取回 |
| IMPL_DESIGN §5.4(实机验证阶梯/检查项⑮ fee live 核定) | 实机核验通道 | sr-od-currency-war-dev skill 单局复盘协议(references/match-review.md);fee 语义现行载体=kernel/cw_state.sell_refund docstring |
| IMPL_DESIGN §6.1(位面长度单一源/R3-2) | schedule_of 真值 | ADR-0366/0368+kernel/cw_plane_table.schedule_of(既有持久索引,不变) |
| IMPL_DESIGN §6.4-R(R189 换核重切:R189-1 四分歧裁决/R189-4 结构签名/R189-5 修复池收编/R189-6 迁移序) | 换核迁移序与批1 规格 | 历史批(已执行完毕,产出=现行代码)。活语义:结构签名/发射面截断判=序列决策契约(dd-020 权威链+flow/action_exec.md §1 as-built+kernel/cw_prep_actions,重锚申报=ADR-0585 §5);证明层四函数位=proof.py 本体;修复池 D-* 各项现行落点=mandate_v1 各实现本体与 18_equip_wear_semantics |
| R 批号族(R3-R94 对照表/R95 起对照表节/IMPL_ADV_RNNN 对抗审查报告/RN-x 修复注) | 修复史出处 | 修复史,不搬入现行文档(README §3 既定口径)。载体=上节取回口径(design_telemetry.md 文末对照表节/IMPL_FIX_LEMMAS.md 对照表)。现行行为语义一律以代码+strategy-docs+math_proofs 为准,批号仅作出处注 |
| D-* 修复池编号(D-B/D-D/D-F46/D-P3/D-lv7/D-BUYNOTE/D-FM1 等) | R189-5 修复池收编项 | 编号出处=R189-5 表(git 取回);各项现行落点=mandate_v1 对应实现本体(criteria/equipment、criteria/refresh、criteria/levelup 等)与 18 号稿 |
| design_economy(§E4.0 四审计形态/§E4.1 组-端对照表/§E4.2 canonical 枚举表/§E6 分型登记) | 判据正文分文档(同族灭失,commit 4e32b2e4) | 四审计形态=01_math_framework §6(数字三形态章程)+audit 包各模块本体;组-端取端纪律与 cap_sup 消费=各消费位注释+01_math_framework §6/§9;分型登记形态=kernel/cw_investments.aggregate_economy docstring;原文取回=`git show 4e32b2e4^:docs/develop/currency_war/archive/design/design_economy.md` |
| design_telemetry 键节/「标定批」/「复审返工批」等登记节 | 遥测键登记与修复批对照表(同批灭失,commit 90f1acdb2) | 计数键登记单一源=**各写点注释**(mandate_v1 各模块 cw4_counters 键清单/contracts.ensure_contract 动态键/披露键=sim/ab_core_swap);schema.py 仅静态声明键(f7_contingency_armed/depsilon_advisor_violation/f7_exempt_emission);原文取回=`git show 90f1acdb2^:docs/develop/currency_war/archive/design/design_telemetry.md` |

## 3. Decision

1. 代码注释/注册表锚中的「IMPL_DESIGN §x」字面逐处改指上表现行落点;R 批号与 D-* 编号保留(出处注性质),其解析口径统一=本 ADR。
2. contracts.py `Contract.anchor` 字段值(纯描述性字符串,无运行时行为,无测试锁——test_cw_contracts 2026-09-09 起连「锚非空」断言已删)逐值改写为现行落点;`ZERO_REFRESH_DIAG`/`SEEDS_EMPTY_LEDGER_DIAG`/`FIX_REVIEW_20260903`/`CALIB_REPORT` 等诊断报告锚系另一族,不在本批辖域(见 §5)。
3. docs 侧 `design/冻结残余清单.md` 头注的「解读按 git 历史原文」补两笔删除 commit 精确哈希;dd-007/ADR-0565 等 ADR 正文(immutable)不回改,其引用由本表承载。

## 4. Consequences

- 重锚后:「设计正本↔实现对账」对该批引用可执行——规格语义查现行文档/代码单一源,修复史查 git 取回口径。
- 注释规范回归:出处引用全部为持久索引(文件路径/ADR 号/符号名)或语义描述。
- 后续新增注释禁再引 IMPL_DESIGN § 字面;新增判据/遥测键的规格锚写现行落点。

## 5. 辖域边界(如实申报,不扩面)

- `ZERO_REFRESH_DIAG §3/§4`(contracts.py 多处 anchor 值)、`SEEDS_EMPTY_LEDGER_DIAG`、`FIX_REVIEW_20260903`、`CALIB_REPORT(_V2)`、`g_20260904_054904` 等诊断/评审报告引用**不在本批锚族**(任务面=IMPL_DESIGN §x/R19x);其中 ZERO_REFRESH_DIAG.md 经查 `.debug` 亦已不在盘,同属断锚,待编排者裁决是否另批处置。
- `strategies/impl` 域「设计正本 §8.5/§8.6-6」所指=docs/develop/sr_od/application/currency_war/changes/2026-09-11-unified-state/details/BoardState-数据结构设计.md(已迁移至此,2026-09-11 迁移;§8.5 在位),非断锚,仅措辞未带路径,不动。
