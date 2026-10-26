# 3.3 阶段验收报告

- 验收对象：commit `405731119`（cw: 遭遇迁移 3.3 正本更新），8 文件 +113/−19，与申报入库面一致。
- 验收方法：独立干净上下文，仅依据 landing.md「正本更新清单」、design.md、strategy-docs 现态与 `encounter_pick.py` 等代码直调，不引会话历史。
- 验收日期：2026-09-24。

## 结论：通过（发现 6 条，其中高严重度 0 条；1 条中严重度建议随后续小批落地）

七条正本更新清单逐项落实且改写内容与清单意图一致；31 号稿判据语义与 `encounter_pick.py` 现态逐节比对一致；as-built 纪律、收口完整性、引用存在性、申报偏差 5 条、文档间一致性、零代码改动全部核过。唯一实质缺口（F1）在 3.3 清单之外：章程 §6 修订已裁定批准但未落 01 号稿正本，属清单漏项而非执行偏差，建议补一小批收口。

## 发现清单

### F1（中）章程 §6「闸门位立场值」修订已批准生效，但正本 01 号稿未落，正本间矛盾
- **位置**：`strategy-docs/01_math_framework.md` §6（L148 起）vs `strategy-docs/31_encounter_screen.md` §1 裁定 3 / `strategy-docs/04_survival_budget.md` §7 表第 9 行。
- **事实与直调证据**：
  - 迭代 README「已裁定」节第 2 条与 design §2.2 均载明「章程 §6 修订（新增闸门位立场值形态）+ 边缘态 cap = 2 批准生效（2026-09-24 用户，同一裁决门）」。
  - 但 01 号稿 §6 现行分界句仍为原文：「凡『数值大小参与方向/闸门判断』的量归【推】/【拟】纪律，【拍】只承载『登记即立场、分差即偏好强度』的**加法立场值**」——全文 grep「闸门位立场值」仅命中 design/迭代 README（过程区）与本批新写的 31/04 两篇，01 号稿零命中。
  - `EDGE_CAP = 2`（encounter_pick.py:53）是参与闸门判断的数值，按 01 §6 现文属违章量；31 号稿裁定 3 与 04 号稿裁定 9 行引用的合法性载体「章程 §6 修订」在正本中不存在。
  - landing 3.3 清单七条不含 01 号稿 → 清单漏项（迭代收尾义务「代码实现后更新正本」的缺口），非 worker 执行偏差。
- **修正方向**：补一小批把「闸门位立场值」形态落进 01 号稿 §6（supersession 该分界句：偏好型闸门值 = 登记即立场、零拟合零观测，EDGE_CAP/REWARD_ORDER_APPROVED 作先例）；不建议只挂待办——裁定已生效，正本应与裁定一致，否则下个读者按 01 §6 现文会判遭遇立场两值违章。

### F2（低）architecture.md:144 模块地图行过期——worker 申报属实，批外未动合理
- **位置**：`docs/develop/sr_od/application/currency_war/architecture.md` L144（「意向与事件」族行）。
- **事实与直调证据**：该行写「`cw_events`(投资 3 选 1/遭遇/补给/巨星决策核)、`cw_encounter_selection`(遭遇选档判定)」。直调现态：kernel 全目录 grep `decide_encounter` 零命中（投资/遭遇/补给判据均已迁策略层 `invest_env.py`/`encounter_pick.py`/`supply.py`，bridge.py 覆写已删）；`cw_encounter_selection.py` 现符号面 = 结算观测基建（`SettlementRing`/`EncounterLog`/`record_settlement_row`/`game_start_reset`）+ 兑现回调 `claim_encounter_reward` + 仅收 `D_ENC_VARIANT` 的注入口，选档判定已不在。
- **处置建议**：挂账 CW 正本维护小批（可与 F1 同批）：该族行改写为「`cw_events`（剩余事件画面决策核〔planner/巨星/圣杯/伙伴等〕+ 观察载荷契约 `EncounterOption`）、`cw_encounter_selection`（结算观测基建与兑现回调）」，并补策略层遭遇/补给/投资判据模块指针。该文件在 currency_war 根、非本批清单七条辖域，本批不动符合逐文件点名纪律。

### F3（低）迭代 README 进度节滞后
- **位置**：`changes/2026-09-24-encounter-screen-strategy-migration/README.md` 进度节。
- **事实**：「落地:未开始」「正本更新:未开始」与实际不符（3.1/3.2 已随 `8922f97d2` 落码、3.3 已随本 commit 落地）。过程区文件不受 as-built 纪律辖，但进度树是活状态单一源，应随批更新。
- **修正方向**：worker 收口时顺手把三阶段状态与 commit 号回写。

### F4（低·批外既存）25 号稿 §2 动作清单缺银狼升星行
- **位置**：`strategy-docs/25_event_overlays.md` §2 表。
- **事实**：头注画面族含「银狼升星(cw_yinlang_star_up)」，§2「会执行的动作清单(按画面)」无对应行（本批前后同态，非本批引入；design §2.9 对 25 号稿的改写指令已逐项精确执行）。
- **修正方向**：登记给 25 号稿后续维护批，本批不顺手扩面处理正确。

### F5（低·批外既存）screens/encounter.md 两条 game 侧链接的显示文本深度与目标不一致
- **位置**：`screens/encounter.md` §2（screen_flow_timing 链）与 §8（game 侧知识行）。
- **事实**：链接文本写 4 级上跳（`../../../../game/…`），实际目标为 5 级（`../../../../../game/…`）且目标正确——解析不受影响，显示文本易误读。两处均本批之前既存（diff 新旧行同文），非本批引入。
- **修正方向**：cosmetic，随下批触碰该文件时顺手校准。

### F6（低·措辞）31 号稿 §2.2「fill 只走删失分支」表述有歧义
- **位置**：`strategy-docs/31_encounter_screen.md` §2.2 fill 分支条。
- **事实**：design §2.2 原文为「fill 只走**不激活路径**」；31 号稿转写为「fill 只走**删失分支**」。实现现态（`_kappa_state`：删失帧与未定谳败局帧均返回「边缘」）下两者**结果语义等价**，但「删失分支」读作「败局帧按删失计」则与代码不符（败局帧按边缘计、仅 fill 降档不激活）。且 §2.2 同段后句「删失优先于 fill：另一场为删失时整场按删失计」已给出准确消歧。
- **修正方向**：措辞校准回「不激活路径」或删去该短语；判据语义单一源已明示在 `_kappa_state`，不构成正确性问题。

## 验收核对表

### 正本更新清单七条（landing.md「正本更新清单」节）

| # | 清单项 | 判定 | 证据 |
|---|---|---|---|
| 1 | 31 号稿新建（判据语义 = 落码现态；裁定登记〔含【拍】过目记录与章程 §6 修订〕/数学挂账七项/sim 盲区） | ✓ | 新建 91 行；§2.1–§2.6 与 `encounter_pick.py` 逐节比对一致（窗口普战过滤/κ_S 三态表/cap 过滤在前+经验档层交集/最高档主序+(档序,idx) tiebreak/闸内嵌刷新阀+三因词/fail 向两形+归因串封闭枚举/立场 None 回退态）；裁定四项、挂账七项、sim 盲区见下行专项 |
| 2 | 25 号稿画面族移除遭遇（头注/§1 prose/§2 表行）+「已拆 31」头注 | ✓ | 头注 8 项无遭遇 + 第 5 个「已拆」头注；§1 选卡决策行补「遭遇 = encounter_pick.py,正本 31 号稿」；§1 画面间差异行、§2 表第一行（7 画面）均无遭遇 |
| 3 | 13 号稿 `decide_encounter` 行「双轨」过期描述改单一源指 31 号稿；E3 目录行同改 | ✓ | §1 行改「策略层单一源 = encounter_pick.py::decide…旧『双轨』描述已随迁移整体退役」；§4 E3 目录行同改；头部判据单源分轴句补遭遇（申报偏差 1，合理） |
| 4 | 08 号稿 E3 行「现有语义」格替换为能力态直通形；「判据状态」维持待 derive；锚不变 | ✓ | E3 行 = 能力态直通形四组件 + 决策本体/单一源指针；判据状态「待 derive」保留、P26 锚不变 |
| 5 | 04 号稿裁定 9 行「判据正本」指针改策略层；同行补判据结构合法性载体分层 | ✓ | 「判据正本 = 策略层 encounter_pick.py（2026-09-24 迁移批；结算观测持久化基建留 kernel）；判据结构合法性载体 = 章程 §6 修订（闸门位立场值形态）+ 用户过目（2026-09-24），授权辖域原文不变」——与 31 号稿裁定 1 互相一致（载体本身未落正本 = F1） |
| 6 | README §2 增 31 行；导航句 18-30 → 18-31 | ✓ | 分篇表 L53 新增 31 行；导航句 L57「18-31」 |
| 7 | 画面文档策略指针面（screens/encounter.md 决策委托/刷新闸行为句；game/screens/currency_war_encounter.md 算法描述句，落批全路径核对） | ✓ | screens/encounter.md 6 处（§2 决策委托句改指 encounter_pick.py+31 号稿/§3 全克句改「词缀轴 = 死输入」/§4 分支刷新行改防线语义/§5 终结表+三出口句/§6 刷新单次行/§8 测试表述改「防线 round_fail」，与测试现态 `test_encounter_refresh_gate_mismatch_round_fail_redispatch` 一致）；game 侧算法句整句改写（能力态选档行为描述与实现一致，判据指针 = 31 号稿） |

### 判据语义与裁定/挂账/盲区专项（判据 2）

| 项 | 判定 | 证据 |
|---|---|---|
| §2.2–§2.5 判据语义转写 vs `encounter_pick.py` 现态 | ✓ | 三态表含 fill 双定谳槽门（`BAR_SEMANTICS=='node' ∧ PROGRESS_BAR_DIRECTION=='forward' ∧ fill<_FILL_EDGE_THRESHOLD`）与删失优先序；cap 过滤在前、足量态上界不设限表述与 `cap = EDGE_CAP if 边缘 else 6` 等效；经验档层 `tier_cleared` 交集；tiebreak `min((reward_tier, opt.idx))`；闸内嵌 `left is not None and left >= 1`；归因串四形态逐字一致（`pick:t{k}|kappa=<态>`/`refresh-valve:<因>`×3/`dark-fallback:<因>`/`stance-unconfirmed`） |
| §1 裁定登记四项 vs design §2.2/§2.10 | ✓ | 裁定 1 = 04 §7 表第 9 行授权 + 辖域限定 + kernel 保留面四符号（直调 `cw_encounter_selection.py` 现符号面一致）；裁定 2 = 2026-09-21 op-layer §1.4（该节现文含「刷新闸 = 剩余语义观察真值(全域)」）；裁定 3 = 两闸绑定批准 + 章程修订申报 + 重拍回退机制（`stance-unconfirmed` 分支在码）；裁定 4 = EV 核退役（`encounter.py` 已删、provisional 双槽已删、仅余改指策略层的指针句 L23） |
| §4 数学挂账七项 vs design §2.9/§2.11 | ✓ | 比值腿复活（P64 单篇存在 = `currency_war/proofs/`）/E-3 标定（注入位 fill 双键 vs `_CALIBRATABLE` 现态、kernel 侧仅收 `D_ENC_VARIANT` 现态、fill 阈值【拟】登记义务）/EV 形态挂 P26/档位↑采样验证/P2 两源对账/窗口变体触发器/补给孪生面防线交接（升 op-layer §1.4 全域条款批）——七项与 design §2.9 列举逐项对应 |
| §3 sim 盲区 vs design §2.12 | ✓ | sim/ 目录 grep `record_settlement_row` 零命中——「结算环无写端 → 恒窗口不足 → 闸拒刷 → 最低档」结构性盲区断言成立；不可作 A/B 判据、验收 = 单帧测试（`test_cw_encounter_pick.py` 存在）+ 实机锚点 |

### 申报偏差 5 条

| # | 申报 | 判定 | 依据 |
|---|---|---|---|
| 1 | 13 号稿头部「判据单源分轴」句补遭遇 = 策略层 | 合理 | 原句「其余 pick 族 = kernel/cw_events/cw_comps」在 kernel 遭遇核删除后会把遭遇错指已删核；补分轴消除失指，最小改动 |
| 2 | screens/encounter.md 三处同面过期叙述随批收口（§3 全克句/§5 失锚引用/§9 测试表述） | 合理 | 实际落地 6 处改动，覆盖 landing 清单第 7 条全部要求（决策委托句+刷新闸行为句多处同步）；「三处」为语义面归组口径，§9 实际节号为 §8，不影响实质；防线描述与 `cw_screen_encounter.py` L198-205 现态一致 |
| 3 | 25 号稿 README 行一句话补「遭遇已拆 31」 | 合理 | design §2.9 只要求头注；README 分篇表 25 行描述与头注同步属一致性增强，先例同形（投资策略已拆 29、投资环境已拆 28 同行并列） |
| 4 | 批外发现：architecture.md:144 模块地图行过期未动 | 属实，处置见 F2 | 直调证实该行与现役代码不符（本报告 F2）；批外文件不动符合逐文件点名纪律 |
| 5 | 工作区其他批在飞未触碰 | 属实 | `git status`：2026-09-21-tool-gain-report / 2026-09-23-invest-env / uv.lock / attack*.md / review-3*.md / 2026-09-24-action-world-decl/ / supply review-33* 均未进本 commit；入库面 8 文件与申报一致 |

### 其他判据

| 判据 | 判定 | 证据 |
|---|---|---|
| 3. as-built 纪律 | ✓ | 数值只写常量名（EDGE_CAP/REWARD_ORDER_APPROVED/_FILL_EDGE_THRESHOLD 均不抄值；t≤4/t≥5 为档位结构分界非立场值）；无进度标记/变更史叙事/会话快照（裁定日期 = 30 号稿「裁定登记(用户 2026-09-24)」先例同形）；术语节首现定义齐全（结算观测环/删失/κ_S/可及集/fill/fail-closed/【拍】） |
| 4. 收口完整性 | ✓ | strategy-docs 全目录 grep「双轨/全克刷新/默认选左/判据正本 = kernel/cw_encounter_selection/cw_events.py::decide_encounter」——过期遭遇描述零残留（「双轨」命中均系装备穿戴/部署换人/P47 递推等无关域术语，或 13 号稿退役注记本身；kernel/cw_encounter_selection 仅剩 31 号稿裁定 1 保留面陈述）；扩展扫 screens/flow/docs/game 亦净；README 31 行与导航句在册 |
| 5. 引用存在性 | ✓ | 31 号稿全部相对链接解析有效（`../proofs/p64-…` → currency_war/proofs/ 存在；`../../../../../game/…` 从 strategy-docs/ 5 级上跳正确，浮层/economy.md 均存在）；符号全核实（DIAMOND_EQUIP_NAMES 单一源 = kernel/cw_obs_core.py:50、EQUIPMENT_ROSTER = cw_equipment_data.py:233、GameState 三读口 L2132/2135/2161、`last_normal_battles` 普战过滤 = node_type=='普通战斗'、`tier_cleared` L179）；节号全核实（04 §7 表第 9 行/screens README §5.2 §5.5（§5.5 现文含遭遇条目）/op-layer §1.4/00 §1 第 5/6 条/01 §6/economy §10.2/combat §3（该节含「遭遇奖励 = 伤害进度达标制」条目，引用成立）） |
| 7. 文档间一致性 | ✓ | 31 vs 30/28 同构（头注三段式〔画面/决策本体/术语〕+ 裁定登记 + 决策结构 + 挂账/盲区；分节聚合粒度差异属合理演化）；08 E3 = 13 §1 行 = 13 §4 目录行三处口径一致；04 裁定 9 行与 31 裁定 1 互证一致；25 号稿改写后无内部矛盾（银狼升星表行缺失 = 批外既存，F4） |
| 8. 零代码改动 | ✓ | diff 8 文件全为 .md，无 .py |

## 备注

- F1 修正建议排期：与 F2（architecture.md 模块地图行）合并为一个小批一次收口（两者都是 CW 正本面欠账，互不依赖但同域）。
- 本报告依据 commit `405731119` 时点现态；工作区在飞批改动不在验收辖域。
