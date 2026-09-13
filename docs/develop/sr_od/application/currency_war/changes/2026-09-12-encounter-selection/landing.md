# 遭遇选档简化 落地

> 阶段唯一源纪律：本文件 = 账本阶段唯一源；设计改 → 本文件改 → 账本跟着改，禁两处各自演化。
> 通用工程门 = od-dev-progress-tracking §12（含 `ruff check` 仅改动文件、测试纪律；各阶段完成判据统一引用，不逐条复述）。
> 阶段骨架单一源 = details/encounter-criterion-spec.md「阶段」节。**W4 暗装锚：E-2 落码后、E-3 标定前，实机行为与现行恒低难逐位一致（行为零变化），开闸只在 E-3 标定注入后发生。**
> 数据通路前提（details §8）：判据读源 = GameState 结算观测环（E-2 新建，深度 10）+ GameState 遭遇经验表；`performance.history` 保留为观测分析层不动；outcomes 写端已退役，跨局持久化挂账不在本迭代。

## 3.1 E-1 奖励读法结构化 + tiebreak 映射表

**范围**：现读法评估与结构化（`read_encounter_options` 奖励带已读**单项文本**——多件预览结构化评估，确有二件以上同卡 → 扩读法；单件够 → 如实申报不扩）；奖励文本 → tiebreak 偏好档映射表（**降级分支比较器定义义务**：奖励预览缺失/空集卡字典序 + 档位并列降级比较器，随映射表一并定义；词表权威 = `DIAMOND_EQUIP_NAMES`（cw_node_obs.py:231）∪ `EQUIPMENT_ROSTER`/`EQUIPMENTS`/`EQUIP_TOOL_CATEGORY`（data/cw_equipment_data.py）∪ 金币字面，逐项注册表出处核对，给不出 → 映射表整表退化取低档并申报）。**不含 tiebreak 消费端**（判据耦合，归 3.2）。锁：映射表单测（词表样本逐项）。

**设计依据**：details/encounter-criterion-spec.md §6 + 接口契约 4

**文件面**：`obs/cw_node_obs.py`（若扩读法）、`kernel/cw_encounter_selection.py`（映射表，与 3.2 同模块先落）、`sr-od-test/test/sr_od/app/currency_war/`（映射表单测）

**依赖**：无

**优先级建议**：4

**完成判据**：
- 映射表单测全绿（词表逐项 + 未映射落末档）；多件结构化结论（扩或不扩）带依据申报
- 既有 encounter 读数锁回归全绿
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + ruff check

## 3.2 E-2 判据落码（暗装）

**范围**：新模块 `kernel/cw_encounter_selection.py`（能力态 κ_S 敌方通道标尺（killed + 进度填充率，含删失归态——删失仅统计败局帧）/ 双值可及性不等式（**D_enc = 决策时读 GameState 现存值 + Δ_t〔读点归属两假设未定谳，details 契约 2〕**；无现场真读/值空 → 判据弃权走暗装；**不经 cw_difficulty_account 解析合成**，锁 W10）/ 经验档层交集（局内 scope，读 GameState 遭遇经验表）/ 刷新逃生阀（可及集=∅ 单一判据，两分支同口径）/ 单卡与无选项帧）；**GameState 扩结算观测环（深度 10，建议名 settlement_ring）+ 遭遇经验表（建议名 encounter_log）**，结算观察半既有写点单点双落 + **败局行拓扑改造**（环写位 = 守卫后三路过守卫者入环、同场去重合并、环/经验表开局清空 + 残留排除接线（生命周期 = 局）——裁定 6：结算观测数据入 GameState 持久化，深度论证 details §8）；`RoundOutcome` 双扩字段 `difficulty_node` + `encounter_tier`（结算快照取备战帧**现场真读**旗牌值——live 位为门，carry 恒值不入，无现场读 → None / 决策落点 `chosen_encounter` 取档位；产出端锁 W13）；flow 层窗口提取传入 kernel（纯函数收显式输入）；`MandateV1Strategy.decide_encounter` 改投新函数；EV 核模块头搁置注释（指针 = 13_pick_family E3 行正本 + 替代语义为主，禁引 changes/；13 E3 行正本化改写随 E-4，避免循环指认）+ **死分键（encounter_ev_*）消费面盘点** + f_min 注入通道与 EV 核双 provisional 槽物理隔离声明 + **现存 ADR-0536 代码注释引用清理**（bridge 3 / encounter 10 / provisional 4 处，直调计数；语义单一源改指代码本体与正本，清理验收按此对账）；归因串 `e3-simple` 走 journal 决策行（禁依赖已退役 decision-row 通道；**journal 行携带 D_enc 口读值与 live 判别子结果**——E-3 配对采集通道，防简报恒值毒化）；tiebreak 消费端（dep 3.1 映射表）；`cw_game_state.py` Settlement 字段准入注释理由修订（「无决策消费」已被推翻——修订注释 ≠ 扩字段）+ `cw_performance.py` 过期 docstring 如实化（「enemy_hp/damage 仍未灌值」与生产写端现状不符——damage_dealt 生产写端 = cw_settlement_obs.py:453/:494）。锁 W1-W6、W7、W8-W13（W14 见 3.3；测试语境 = 三常量 + 进度条语义（两假设+方向维度）注入态，f_min 变量位——见 details 锁表表注）；**W4 = 暗装锚**（含 D 真值缺失分支）。边界：不碰 ADR 本体（0536 已删，其余不动）、不碰观察层读数语义（3.1 域）、`GameState.Settlement` 域不扩字段。**可观测性申报**：sim 引擎无遭遇决策段（cw_screen_encounter.py:37-38）——本判据对 sim 结构性不可见，行为验证仅实机（E-3 批）。

**设计依据**：details/encounter-criterion-spec.md §1-§3/§5-§8（锁表 W 组）

**文件面**：`kernel/cw_encounter_selection.py`（新建）、`kernel/cw_game_state.py`（结算观测环/遭遇经验表新增 + Settlement 准入注释修订）、`kernel/cw_performance.py`（RoundOutcome 双扩字段 + docstring 如实化）、`obs/cw_settlement_obs.py`（双扩字段装填——构造参/行后填形态 E-2 落码定）、`telemetry/schema.py`（OutcomeRecord 双字段同步，恢复同 schema 性质）、`strategies/impl/flow.py`（窗口提取与改投）、`strategies/impl/mandate_v1/bridge.py`（改投 + ADR 引用清理）、`strategies/impl/mandate_v1/encounter.py`（搁置注释 + ADR 引用清理）、`strategies/impl/mandate_v1/audit/provisional.py`（ADR 引用清理）、`operations/cw_screen/cw_screen_encounter.py`（journal 归因行——E-2 新增写点，现役仅 log.info）、`operations/cw_screen/cw_screen_battle_wait.py`（结算链改造（`difficulty_node` 快照装配〔两变体随读点定谳开关——details §8 表，定谳前双态实现、定谳后裁定〕 + **败局行拓扑改造**：环写位 = 守卫后三路过守卫者入环、同场去重合并、fill 暂存战斗窗生命周期、**环完整性对账 = E-3 离线项**（不对齐率〔缺行/多行/序错〕= 开闸门成员）——写点禁惰性 drain 位：取错帧且撞 D-94 红线）、`sr-od-test/test/sr_od/app/currency_war/test_cw_encounter_selection.py`（新建）

**依赖**：3.1（tiebreak 映射表；判据本体其余部分无依赖，可先行落）

**优先级建议**：5

**完成判据**：
- W1-W6、W7、W8-W13 全绿（W14 = E-3 离线对账锁，见 3.3）；**W4 暗装锚全绿（行为零变化，含 D 真值缺失/窗口无 D_win 行分支）**
- 死分键盘点清单交付（逐分键列消费面）；`test_cw_mandate_encounter_ev.py` 保持全绿（EV 核纯函数禁删）
- `test_cw_mandate_decide.py` 遭遇代表锁按新语义重推后全绿（锁红 ≠ 改动错，先对照 details §1-§3/§5）+ 既有 encounter/mandate 锁回归全绿
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + 回归文件 + 死分键盘点清单 + ruff check

## 3.3 E-3 需求线标定批（开闸）

**范围**：实机窗口采集（**自备采集脚本**落 `.debug/`，禁依赖现役 settle_frame_collect 临时件）——遭遇决策帧与其后结算帧配对（决策帧 D_enc 口读值/选档档位/填充率/胜负）——**按选档结果标定净值 Δ_t 与 f_min**（读点归属两假设未定谳〔契约 2〕：判 (ii) → 净值 Δ_t 与 f_min、判 (i) → 原始口径线族；敌方信息浮层读数通道未接线〔建档已完成，provisional.py:96-102〕，结果标定无需自身旗牌；浮层读点为升级路径），n≥5 起步（比例型单参数最小可行样本，采样随对局继续累积）→ f_min CI；**进度条语义定谳 = 开闸前置**（离线可先行：归档对局 fill 轨迹 vs 逐节点胜负对账，判别式 details §2）+ Δ_t 净值语义配对定谳；g 曲线客户端配置表查表并行（命中 → 【注】切换，W8）；**f_min/g/Δ_t 三常量登记 01_math_framework §6 在册【拟】清单**（消费面/分级/fail-closed 退路/owner=编排者/期限=下一实机对局窗口——超期未决按 strategy-work §3（开关生命周期）回炉）；fill 读取率（结算遥测页 1 帧态）、**遭遇败局行入表率、环完整性对账不对齐率〔缺行/多行/序错〕**、节点类型解析率、档位读出率与分级混淆矩阵量测；**档位翻转线族（净值口径）= {0.738, 0.444, 0.268} 预置分支**：CI 跨任一线 → 按 01 §6 要素②「方向翻转 = 数据不足」处置（继续采样/维持暗装），禁硬选端点。f_min/g/Δ_t 注册落点定死 = `kernel/cw_encounter_selection.py` 常量区。**开闸门 = 三常量逐个满足 01 §6 要素①②③ ∧ 进度条语义（两假设 + 方向维度）已定谳 ∧ D_enc 读点归属定谳 ∧ 环完整性对账不对齐 = 0〔缺行/多行/序错〕∧ fill 读取率达标 ∧ D_enc 现场读命中率达标（W14 离线对账），任一不可得/不合格 → 维持暗装并如实申报**。算法质量验证通道 = 实机本批（sim 无遭遇决策段，判据 sim 不可观测——3.2 申报）。

**设计依据**：details/encounter-criterion-spec.md §3（三态表/翻转分支/登记义务）+ §4（读链申报）+ §9 零调参对账

**文件面**：`kernel/cw_encounter_selection.py`（常量注入）、采集脚本（`.debug/` 域，不入库）、`docs/develop/sr_od/application/currency_war/strategy-docs/01_math_framework.md`（§6 清单登记）、`sr-od-test/test/sr_od/app/currency_war/`（标定值注入锁）

**依赖**：3.2；实机对局窗口（用户裁定配合）

**优先级建议**：4

**完成判据**：
- f_min 带 CI 注入（或不可得 → 维持暗装的申报记录）；01 §6 登记完成（f_min/g/Δ_t 三行，含 owner/期限）
- 进度条语义定谳结论记录（两假设二选一 + 红段方向 + 证据帧指针；判为累计 → 按 details §2 保守回退条款回写设计）
- W14 环完整性对账锁绿（对账不对齐〔缺行/多行/序错〕= 0 在册）
- fill 读取率达标判定记录在册（开闸门成员）
- W1-W3 激活全绿（g 不可得场景以三常量 + 条语义测试注入态判定，见 details 锁表表注）；W8 两态全绿
- §12 通用工程门（引用，不复述）

**验收凭据形式**：标定数据表（样本数/CI/来源帧指针）+ 01 §6 登记行 + 测试名清单

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1、3.2、3.3
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `strategy-docs/13_pick_family.md` §判据表 E3 行（双轨 → 简单判据正稿 + EV 核搁置指针）← 3.2
- `strategy-docs/08_events.md` E3 表行（判据轴换向：输出 vs 需求线；标定批指针）← 3.3
- `docs/develop/sr_od/application/currency_war/strategy-docs/04_survival_budget.md` §7 hp 进决策授权对账表：登记裁定 6 行（授权日期 2026-09-12/形态 = 结算屏现成读数含 B/P 进遭遇决策/v1 不消费辖域/敌方通道退路）← E-4
- `strategies/impl/mandate_v1/encounter.py` 搁置声明与代码批内一致性的语义面核对 ← 3.2
- `decisions/INDEX.md` 墓碑行语义承接核对（E-2 改投后「遭遇判据语义承接 = 13_pick_family E3 行」仍成立）+ proofs/（p64、T-175:194 等）ADR-0536 引用处置核对——存档性引用加注、现态引用改指代码本体/正本 ← 末阶段
