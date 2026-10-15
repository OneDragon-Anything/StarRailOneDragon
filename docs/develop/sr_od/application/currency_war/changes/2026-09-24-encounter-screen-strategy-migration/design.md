# 遭遇画面策略层迁移与判据激活 迭代设计（总纲）

## 0. 元信息
- 迭代目标：宪法第五条（框架层/策略层所有权边界）与第六条（一画面一策略文件、一画面一策略文档）在**遭遇画面**（`货币战争-遭遇节点`，选难度档二选一 + 每局一次分支刷新）的兑现；同时把遭遇选档判据从「恒暗装」（标定槽未定谳 → 恒最低档 + 零刷新）激活为**零标定可判子集**（能力态 + 经验档层 + 奖励 tiebreak + 刷新阀），并结束同一画面三个判据本体并存的局面。
- 裁定指针：
  - 宪法五/六：`strategy-docs/00_framework.md` §1 第 5/6 条（用户裁定 2026-09-23，env 批兑现先例）
  - 遭遇选档结算观测授权：`strategy-docs/04_survival_budget.md` 判据来源裁定表第 9 行（用户 2026-09-12 逐项确认，硬闸门例外扩大程序完成；授权辖域 = 敌方通道结算观测〔killed/进度填充率〕作遭遇决策输入 + 入 GameState 持久化）
  - 刷新剩余语义：用户裁定 2026-09-21（全域规范 = `../screens/op-layer.md` §1.4；剩余 ≤0 或 None = 已刷尽/未观察）
  - P64「遭遇分支敌方难度读数→敌难度 stat 静态映射标定域为空」：已证结构命题（`../proofs/p64-encounter-dstat-static-map-uncalibratable.md`）
- 状态：定稿（对抗收敛，报告 = attack.md ~ attack-r9.md；三项用户裁定 2026-09-24 已回写 §2.2/§2.10）
- 文档清单：无详设（单文档方案，§2 即完整设计，深度 = 详设级）
- 承接：env 批「明确不解决」面登记遭遇等其余画面迁移为后续批（`changes/2026-09-23-invest-env-strategy-migration/design.md` §1）；补给批同（`changes/2026-09-24-supply-screen-strategy-migration/design.md` §1）。本批文档 = **31 号稿**。

## 1. 问题与动机

- 现状症状：
  1. **决策本体驻 kernel 且三核并存**。同一画面同时存在三个判据本体：
     - **生产现役核** = `kernel/cw_encounter_selection.py::decide_encounter`，经策略层覆写接线（`strategies/impl/mandate_v1/bridge.py` `MandateV1Strategy.decide_encounter`）。其六个标定槽（`F_MIN`/`G_BASE`/`DELTA_T`/进度条方向/进度条语义/`D_ENC_VARIANT`）**全部 None** → 恒暗装（**暗装** = 判据所需标定值缺失时判据不可评，机械退到恒最低难度档 + 零刷新的保守缺省形态）。生产行为 = 整局所有遭遇全选最低档、从不刷新——奖励轴整局放弃，裁定 9 已授权的结算观测**判据消费**（κ_S 窗口/经验层）闲置（观测写入端与兑现回调在产，闲置面仅判据读数）。
     - **旧知识判据核** = `kernel/cw_events.py::decide_encounter`（词缀契合 + 成型度 + 难度账本压档 + P3 永避高难），挂基类 `CwFlowStrategy.decide_encounter`（`strategies/impl/flow.py` `decide_encounter`）。生产壳 `MandateV1Strategy` 覆写了该入口，旧核只剩基类兜底面。其词缀轴消费 `EncounterOption.affixes`——**死输入**（遭遇选项 UI 不显词缀、战后才显，`obs/cw_node_obs.py` `read_encounter_options` 恒填空列表）；其 P3 分支按 `plane_of(gs) == 3` 枚举机制辖域 = 宪法第二条违例存量（「位面只能作查表键」）。
     - **历史 EV 核** = `strategies/impl/mandate_v1/encounter.py`（EV(b) = V_r − Δλ_death·G_loss）已搁置让位、保留禁删；双 provisional 槽（`ENCOUNTER_DSTAT_MAP`/`ENCOUNTER_G_GOLD`）None 期恒 fail 向选低难零刷新——**src 与测试仓双零消费**（全仓 grep 直调核实）。
     - 后果：13 号稿 `decide_encounter` 行仍描述「双轨」（基线核 + EV 核），与生产实际（暗装核）不符 = 文档漂移实证；「遭遇判据单一源」语义永久含混。
  2. **暗装门粒度过粗，把已授权可判的部分一起锁死**。裁定 9 已授权敌方通道结算观测作遭遇决策输入；κ_S 能力态、经验档层、奖励 tiebreak（纯序数）、刷新阀全部**零标定可判**，但被排在其前的四个未定谳标定槽（全部服务「可及性比值腿」`g^(D_win−D_enc) ≥ f_min`）一起暗装。
  3. **可及性比值腿的标定路径已被证明判死**。P64：敌方难度读数（「遭遇其X」的 X）不携带敌难度 stat 的构成分量，任何静态 `dict[敌方难度读数→stat]` 注入都产假真值（P64 原辖域 = EV 核 `ENCOUNTER_DSTAT_MAP` 静态映射）；E-2 核的 `DELTA_T` 净值表是同构「敌方难度读数→难度量静态表」，判死由 P64 的同一自由项论证覆盖（引申申报，非 P64 原文结论）。点亮前置 = 敌方信息浮层「敌人难度 NNN+N」读数通道（`docs/game/screens/货币战争-敌人信息浮层.md`，OCR 全可读，未接入）或条件表实采（未采）。比值腿在可见期内无法激活。
  4. **kernel→obs 反向依赖**。`reward_tier`（E-1 奖励 tiebreak 映射，驻 `cw_encounter_selection`）import obs 层 `DIAMOND_EQUIP_NAMES`——策略立场内容驻 kernel 且反向依赖观察层。治本落点 = 检测集单一源迁 **kernel 手维护件**（⚠️ 不迁 `data/cw_equipment_data.py`——该文件由 `tools/cw/gen_equip_registry.py` 整文件覆写，手加常量会在生成器重跑时静默蒸发；注册表内三钻无标志字段可派生，名单最小表达 = 三件名清单，宿主 = `kernel/cw_obs_core.py`〔读数域共用真值，手维护非生成〕，obs 与策略层同源消费）。
  5. **文档面**。`25_event_overlays.md` 画面族清单辖 8 活屏（头注 9 项含 1 项已退役屏的删除注记；§2 动作清单表行另含退役屏「装备」残留）——宪法六违例存量；`04_survival_budget.md` 裁定 9 行「判据正本 = kernel/cw_encounter_selection.py」指针将随迁移失配。
- 根因归层：**分层语义**（判据本体与策略 policy 未分离 + 三核并存无单一源，宪法五）+ **表示**（暗装门把「比值腿未标定」与「能力态可判」捆在一起 fail-closed，粒度过粗）。
- 解决到哪：遭遇画面一个迁移批——新画面策略文件 + kernel 剪除选档判据（保留结算观测基建与兑现回调）+ 三核收敛为一 + 暗装门收窄为「零标定可判子集」激活 + 文档拆分（31 号稿）。
- 明确不解决：
  - 敌方信息浮层读数通道（遭遇屏选卡 → 点「查看详情」→ 读难度分 → 关浮层）——流程层画面交互链，自成后续批（P64 点亮前置链①）；本批只保留容器读口。
  - 可及性比值腿（`g^(D_win−D_enc) ≥ f_min`）复活与 E-3 标定（f_min/G_BASE 定标、进度条双定谳）——待浮层读数通道批后另立。
  - EV 形态判据（P26 同构参数化）——P26 待证明（Δp_prep 条件表 + L_node 分位口径未采）。
  - 遭遇奖励内容的金等价建模——「金币×2」金额非机制常量（P64 金额侧同判）；本批 tiebreak 只用序数档。
  - sim 结算环写端（sim 局 κ_S 窗口无数据）——sim 基建批交接（§2.12）。
  - `EncounterOption.affixes` 死字段清理——观察载荷契约面，归观察批。
  - planner/伙伴/巨星/星徽秘典/祈愿/专家邀请函等其余画面迁移——各自后续批。

## 2. 方案

### 2.1 文件组织（宪法六）

- 新增画面策略文件 `strategies/impl/mandate_v1/encounter_pick.py`：决策入口 + κ_S 能力态 + 经验档层消费 + 奖励 tiebreak + 刷新阀，全在本文件。命名避开已占用名 `encounter.py`（历史 EV 核，§2.10 裁定点 1）；若 EV 核获裁退役、名字空缺也**不复用**（git 考古防混，申报于 §2.10）。
- 依赖方向：`strategies/impl/*` → kernel/data 单向。`encounter_pick.py` 消费 kernel 的 `GameState` 读口（`settlement_ring`/`encounter_log`/`encounter_refresh_left`）、`EncounterOption`（观察载荷契约）、`SettlementRing` 通用读口、kernel 读数域真值（`DIAMOND_EQUIP_NAMES`——宿主 `kernel/cw_obs_core.py`，§2.4）、data 注册表（`EQUIPMENT_ROSTER`）；**策略层不 import obs**（分包依赖矩阵在册禁 decision→obs 直依，`cw_strategy.py` 依赖矩阵句 + `bridge.py` 模块头；全 strategies/ 现零 obs import），kernel 零指向 strategies。
- **随判据本体迁策略层**（判据线 = 换一套策略实现会不会要不同的值/序）：
  - 选档判据函数本体（门序/可及集/选档主序/fail 向）；
  - κ_S 能力态三态表函数 `_kappa_state` **连体迁**（含败局 fill 分支与 `_FILL_EDGE_THRESHOLD` 阈值——fill 分支是三态表函数体的一部分，阈值 0.5 是判据值，随策略层；fill 激活的两定谳槽 `PROGRESS_BAR_DIRECTION`/`BAR_SEMANTICS` 同迁，见 §2.3）；
  - 奖励 tiebreak 映射（`reward_tier` + 四档序数常量——「钻>装备>金币>末档」是策略偏好序，不是游戏事实）；
  - 最低档 fail 向机械（`_lowest_idx` 语义）；
  - 边缘态天花板 cap（= 其二）语义；
  - 策略层标定注入面 `encounter_pick.apply_calibration`/`reset_calibration`（fill 双键；kernel 侧另保留仅收 `D_ENC_VARIANT` 的注入口，见 §2.3——全仓零外部引用，随迁零成本——直调核实）；
  - `selection_state_of`（判据取数 helper——迁出后 kernel 侧零消费，随本体迁）。
- **kernel 保留面**（非打分基建，宪法五③；逐项依据）：
  - `EncounterOption`——观察载荷契约（`obs/cw_node_obs.read_encounter_options` 写端、容器 `gs.encounter` payload、观察上报 `kernel/cw_screen_report/encounter.py`、sim 占位 `sim/cw_sim_backend.encounter_options`、测试仓五方引用），照补给批 `SupplyOption` 留 kernel 先例；
  - `SettlementRing`/`EncounterLog`/`_RingRow`/`SETTLEMENT_RING_DEPTH`/`game_start_reset`——裁定 9 授权的结算观测持久化（读源基建非打分；裁定 9 明文「持久化形态生效即登记」）。**孤儿申报**：`game_start_reset` 全仓零调用（其 docstring「RunLoop handle_init 或首结算时调」为失实声明，随批收口 docstring）——保留面（生命周期钩子的设计意图在册），不随迁不删码；
  - `record_settlement_row`——结算行入环单一写端（守卫抑制与残留排除两臂汇合后的唯一入口）；
  - `claim_encounter_reward`——遭遇奖励兑现回调（结算确认链挂点，2026-09-21 遭遇扩围批定谳形态；结算记账语义，非选档策略）；
  - `gs.enemy_difficulty` 容器与敌方难度读数管线——游戏真值读口（比值腿复活时消费）。
- 迁移后 `cw_encounter_selection` 文件 kernel 侧余量 = **结算观测基建 + 兑现回调**（上两条所列），判据与标定面全部离开 kernel。
- **窗口读口**：`SettlementRing.last_normal_battles` 的生产消费唯一 = 判据本体（本批迁出）。窗口定义维持普战口径（§2.2），读口**原样保留**（迁移后消费方 = 策略层画面文件，kernel 基建零改动）。`last_row`（兑现回调消费）不动。

### 2.2 判据换代：能力态直通形（零新数值）

设计原则：**本批零新数值、零新拍值**。激活的全部结构沿用已落码的判据正本形态（三态表/经验层/tiebreak/阀门，git 历史可溯）——合法性载体分层如实申报：
- **数据输入通道与持久化** = 裁定 9 授权（04 号稿 §7 表第 9 行，用户 2026-09-12 逐项确认）——该行授权对象是「结算观测读数作遭遇决策输入 + 入 GameState 持久化」，「判据正本 = 本模块」是载体登记，**不构成判据结构的授权**；
- **判据数字的形态申报（统一口径，全篇唯一）**：边缘态难度上限 cap = 2 与奖励偏好序（钻>装备>金币>末档）是**数值/序数闸门量**。**章程 supersession 申报**：01 §6 分界条款原文「凡『数值大小参与方向/闸门判断』的量归【推】/【拟】纪律」——本批论证该归属对偏好型闸门值失义（【拟】三要素〔CI/标定义务/期限〕预设「对世界的观测信念」，而 cap 与偏好序是对偏好方向的登记：无观测对象、无 CI 语义），提案以 **supersession 修订该分界条款**（新增闸门位立场值形态：登记即立场、零拟合零观测），随 31 号稿呈用户裁定。**两闸绑定（已裁定 2026-09-24 用户：全部批准生效）**：两项值的过目与章程 §6 修订裁定为**同一裁决门**——用户已一并批准（章程修订〔新增闸门位立场值形态〕+ cap = 2 + 奖励偏好序 钻>装备>金币>末档 均生效）；**用户备注：两项为暂定值，实机遥测数据累积后重拍**（【拍】「逐条重拍由实机判读驱动」条款承载，重拍触发器 = 遭遇帧判读积累）。裁定未过分支的工程形态仍保留（立场常量区 None → `dark-fallback:stance-unconfirmed` fail 向），作为将来重拍回退的现成机制。【拍】要件落点：①登记表 = `encounter_pick.py` 立场常量区（cap 与偏好序常量集中一处，值单一源在代码）+ 31 号稿裁定登记节（文档面）；②初值过目记录 = 定稿呈报对话（2026-09-24）。设计方申报：保留随时否决权。κ_S 三态/经验档层/刷新阀为结构门（killed 布尔与次数语义，无自由数字），不受本条辖。
- 唯一判据变化 = 暗装门收窄（比值腿退役，能力态直接判），窗口定义维持现役口径不变更（本节末申报）。落码形态参照**现役暗装核**（`cw_encounter_selection.py`，三态表/经验层/tiebreak/刷新阀的实址）在册的语义——该核自身的历史详设已随过程区清理退役，git 历史可溯。

决策函数（`encounter_pick.py`，纯值出口照 `supply.decide`/`invest_env.decide` 同构）：

```
decide(options: list[EncounterOption], gs: GameState)
    -> EncounterPickDecision(idx, reason) | EncounterRefreshSuggestion(reason)
```

- **闸内嵌**：刷新次数照补给批先例读 `gs.encounter_refresh_left`（剩余语义，None = 未观察 → 不可刷，fail-closed）；flow 现役的 `refresh_used` 预计算（`flow.py` `decide_encounter` 入口）随迁删除。
- **签名最小**：无 `target_comp`/`config` 参——遭遇判据不消费阵容意向（词缀轴是死输入，§1 症状 1；难度轴按能力态）。`locked_comp` 等意向解析不存在。
- 空候选帧：`options` 空 → `EncounterPickDecision(idx=0, reason='no-options')`（纯函数定义完备；现役观察层守卫——读不到标题返空列表零点击——下不可达）。

决策序（与现役核同构，门序收窄）：

1. **窗口提取**：`ring.last_normal_battles(2)`。<2 行 → **窗口不足**（独立态，与 κ_S「不足」严格区分——刷新阀因词 `window-insufficient`）→ 刷新阀（§2.5）。
2. **κ_S 能力态**（仅窗口足时评估；三态表语义照判据正本逐位沿用；窗口两场的 `killed`，None = 删失）：
   - 两场全胜 → `足量`；
   - 恰一胜 → `边缘`（另一场 = 败局或删失；败局侧的进度填充率分支在进度条双定谳前**不激活**——照旧 fail-closed，fill 只走不激活路径）；
   - 两场全败，或双删失，或一败一删失 → `不足`。
3. `不足` → 可及集空 → 刷新阀（§2.5，因词 `kappa-不足`）。
4. **可及集构造**（候选档 = `opt.difficulty`，OCR 标题「遭遇其X」派生，漏读「一」→ 1）：
   - `t ≤ 4`：`边缘` 态难度上限 **cap = 2**（t ≤ 2 才可及；数值闸门，形态 = 【拍】立场登记，见本节原则段——与原核逐位同构，非本批新立数字、激活合法性见上链）；`足量` 态 cap = 6（档位值域上界，OCR 标题正则到「其六」，语义等效不设限；同沿原核）。
   - `t ≥ 5`（其五/六，等级加成 L 值未录入册）：**经验档层交集**——`gs.encounter_log.tier_cleared(t)`（本局该档存在 killed=True 遭遇行）才可及。cap 过滤在前（`边缘` 态下 t ≥ 3 全排除，含五/六——照原核顺序同构）。
   - 依据：其五/六的 Δ 无源（L 值缺），经验正证据（本局清过 = killed=True）是唯一安全通道；「过线操作定义 = killed=True 无条件有效」照判据正本。遭遇奖励为伤害进度达标制非清场制（`docs/game/currency_war/research/combat.md` §3），killed=True 蕴含进度达标，方向安全。
5. 可及集空（足量/边缘态但 options 全被 cap/经验层排除）→ 刷新阀（因词 `empty-reachable`）。
6. **选档**：可及集按 `difficulty` 最高主序（依据 = 游戏原文「难度越高敌人越强大」+ 实测奖励随档升（`docs/game/screens/currency_war_encounter.md` 单帧 + 定性句；原核【拟·档位↑⇒奖励价值↑】的采样验证挂账载体 = 31 号稿数学挂账节——01 §6 在册清单与 provisional 槽位表均无此槽，登记即单一源）；同档并列 → tiebreak 映射（§2.4，小 = 优）；仍并列 → 输入序先（options 左→右 = 画面列序）。
7. 不可刷的空可及帧 → **最低档**（照旧 fail 向；reason 带窗口/κ 诊断）。

- **窗口定义维持现役口径（最近 2 个普通战斗行），不变更**。曾评估「战斗类窗口（普战+遭遇）」改形并否决，论证与事实面如下：
  - 节点日程两源在 P2 序列上分歧：kernel 真值表（`cw_node_schedule`，依据 `plane_schedule_observed.md`：P1 42 局零反例；P2 为 7 局对照且完整样本有限；P1 = supply@r5 + encounter@r7，P2 = supply@r3 + encounter@r5——两位面均单遭遇）vs `economy.md` §10.2 实测表 P2 行 = 双遭遇（r3/r5；该行整体 1 帧待复核）——**两源冲突未定谳**。
  - 候选 B 的工作示例与两源分歧（改形否决论据）：kernel 真值表（P1 = supply@r5 + encounter@r7；P2 = supply@r3 + encounter@r5——两位面均单遭遇）下逐帧推演：每个遭遇决策帧的「最近两战斗类行」恰为「最近两普战行」（同位面唯一遭遇行即决策帧自身，上一位面行已被本位面普战行挤出窗口）——**候选 B 与候选 A 逐位等价**。`economy.md` §10.2 实测表 P2 行 = 双遭遇（r3/r5；该行整体 1 帧待复核）——其下 P2 第二遭遇帧（r5）战斗类窗口 = r3 遭遇行 + r4 普战行（**同位面**首遭遇行入窗，行为差异面），与 kernel 表冲突且**两源未定谳**。
  - 维持候选 A：改形（遭遇行 killed 入窗）在两源任一下都未做行为面论证——同位面遭遇行 killed 对后续遭遇决策的证据适用性、与 κ_S 三态表的组合语义、对 fill/删失分支的交互均未推演；无行为面确证的语义变更不做。对账挂账（P2 序列两源定谳）+ 变体触发器（同位面第二遭遇确证 / 战争边疆 P3 采齐运行）登记 31 号稿数学挂账节——届时再评估遭遇行入窗。届时论证要点 = 遭遇行 killed 与普战行 killed 同为敌方通道生存证据（裁定 9 授权辖域）；boss 行排除（伤害锚异构档，P15v2 boss 26.79 vs 普战 10.45；两源表 boss 均为位面末节点 = boss 后无遭遇决策点〔`economy.md` §10.2 / `cw_node_schedule`〕；P3 结构未在册且不运行（`cw_node_schedule`）——若采齐后出现 P3 遭遇帧，其普战窗口可能含 P2 普战行（结算环跨位面累积，证据迁移性未证），该面随 P3 采齐批一并论证；当前该位面不运行、无行为面）；遭遇败局入窗使 κ_S 降档 = 反应提前，宪法三「危险只升不降」合法方向。
- **足量态 cap 精确口径**：现役核 cap = 2（边缘）/ 6（足量）——足量的 6 = 档位值域上界（OCR 标题正则到「其六」），语义等效不设限；沿用原值不改为「无 cap 判定」，保持与判据正本逐位同构。

**归因串格式**：保留 `e3-simple|` 前缀与现役段格式（`pick:t{k}|kappa=<态>`/`refresh-valve:<因>`/fail 向诊断）——遥测判读连续性（现役 reason 语义单一源随本体迁 `encounter_pick.py`）；标定缺失型 `dark-install` 段不再产出（§2.3）。**因词封闭枚举**（判读侧契约）：
- `refresh-valve:<因>`，因 ∈ {`window-insufficient`, `kappa-不足`, `empty-reachable`}（沿用现役三因）；窗口不足帧取 `window-insufficient`（数据不足与能力不足分因，判读可分）；
- fail 向帧（可及集空且不可刷）= `e3-simple|dark-fallback:<因>`，因同上三枚举（沿用因词，「不可刷」前置不另立词）；
- 立场未过目帧 = `e3-simple|dark-fallback:stance-unconfirmed`（恒最低档零刷新，§2.3 口径）。

### 2.3 标定注入面拆分与比值腿退役

- **退役三槽**：`F_MIN`/`G_BASE`/`DELTA_T`（物理删除）+ `g_ratio` + `_d_enc_snapshot` + `_Diagnostics`（诊断已随 reason 串透传，独立结构失去消费）。退役依据分层申报：P64 原辖域 = EV 核 `ENCOUNTER_DSTAT_MAP` 静态映射（敌方难度读数→stat）；`DELTA_T` 净值表是同构「敌方难度读数→难度量静态表」形态，判死由 P64 的同一自由项论证（B/q/s/m 运行时项）逐项覆盖——**引申申报，非 P64 原文结论**；`F_MIN`/`G_BASE` 退役理由 = 比值腿整体退役（其标定依赖 D_enc 读点定谳链，同属悬置面）。
- **`D_ENC_VARIANT` 槽保留 kernel（不退役）**：该槽除选档判据门外另有**装填语义消费**——`operations/cw_screen/cw_screen_battle_wait.py` `_cw_selection_write` 装填遭遇行 `difficulty_node` 的双态分支直依此槽（裁定 9 保留面「结算观测持久化」自身的依赖；直调 :303-306/:319-323）。判据门随本体迁出（decide 不再读它），槽与装填分支原样留 kernel：None 拨盘下装填行为 = 普战行 observation 直装、遭遇行恒 None（保守前置形态，照旧）。`cw_battle_wait` 装填分支零改动。
- **fill 双定谳槽随迁策略层**：`PROGRESS_BAR_DIRECTION`/`BAR_SEMANTICS` 两槽 + `_FILL_EDGE_THRESHOLD` 常量随 `_kappa_state` 迁 `encounter_pick.py`（None = fill 分支不激活，照旧 fail-closed；定谳后激活）。kernel 侧无标定面残留。
- 注入面拆分（两模块物理隔离，沿现役「两套标定面互不写入」纪律）：①策略层 `encounter_pick.apply_calibration`/`reset_calibration` 迁入，合法键 = fill 双键（`PROGRESS_BAR_DIRECTION`/`BAR_SEMANTICS`）——未知键名抛错防线照旧，全仓零外部引用（直调核实），E-3 标定批未来注入位 = 此口；②kernel `cw_encounter_selection.apply_calibration`/`reset_calibration` **保留**，合法键仅 `D_ENC_VARIANT`（装填拨盘定谳批/测试的注入位 = 此口，§2.3 保留决定配套）。**立场两值（cap/偏好序）非注入**——立场常量区直接编辑（None → 过目值），过目记录 = commit 凭据（【拍】要件「值单一源在代码」）。
- **暗装概念退场（口径对齐）**：标定缺失型暗装退役（六槽 None 全暗的旧形态不再存在）；fail 向仅剩两形——「可及集空且不可刷 → 最低档」与「立场两值未过目 → 恒最低档零刷新（`dark-fallback:stance-unconfirmed`，暗装等价的显式保守缺省，非标定型暗装）」。

### 2.4 奖励 tiebreak（E-1 映射随迁）

- `reward_tier`（奖励预览文本 → 偏好档：文本命中钻石注册表 → 钻档；命中装备注册表〔含工具类，同档不细分〕→ 装备档；含「金币」字面 → 金币档；映射不到〔含空文本/奖励预览缺失〕→ 末档）随判据本体迁 `encounter_pick.py`。
- 消费源：钻石检测集 `DIAMOND_EQUIP_NAMES` 单一源迁 **`kernel/cw_obs_core.py`**（读数域共用真值，手维护非生成——⚠️ 不可迁 `data/cw_equipment_data.py`：生成文件由 `tools/cw/gen_equip_registry.py` 整文件覆写，手加常量重跑即蒸发，且注册表内三钻无标志字段可派生）；`obs/cw_node_obs` 定义迁出改 import kernel（obs→kernel 方向合法）。`EQUIPMENT_ROSTER` 消费 data 注册表不变。§1 症状 4 的治本落点 = 真值归位 kernel 读数域（不把 kernel→obs 反向依赖搬成 decision→obs，依赖矩阵禁，§2.1）。
- **偏好序已裁定批准（2026-09-24，§2.2 形态申报同一裁决门）**：钻 > 装备 > 金币 > 末档生效；用户备注暂定值、遥测累积后重拍（同 cap）。
- tiebreak 输入 = `'/'.join(option.rewards)`（奖励预览 OCR 文本并接，照原核）；同档并列取输入序先（`(档, idx)` 序，照原核）。
- **序数形态申报**：tiebreak 只用偏好序（0..3 档），无价值数值；序已裁定批准（2026-09-24，同 §2.2 裁决门，暂定值遥测后重拍）。奖励子型的金等价建模（EV 核 V_r 形态）不在本批（P64 金额侧：金额非机制常量）。

### 2.5 刷新阀

- 建议刷 = 且仅 = **可及集空 ∧ `gs.encounter_refresh_left ≥ 1`**（闸内嵌；None = 未观察 → 不建议刷，fail-closed）。
- 闸拒绝帧的产出语义（照补给批同构论证）：decide 只在 left ≥ 1 时才可能返 Suggestion；left 缺/尽 → 直接落最低档。op 侧重调路径（`cw_screen_encounter` 建议刷但刷新锚点缺失时重调决策）——防线行为见下条（本批唯一 op 行为改动）。
- **重调兜底分支（机理定谳修正，2026-09-24 用户指正）**：观察先于决策——「剩余次数：N」文本是**同源双信号**（观察轮上报容器 `encounter_refresh_left` + 存为刷新圆钮定位锚），decide 建议刷 ⟹ 文本已读到 ⟹ 锚必在位；文本读缺 ⟹ 容器 None ⟹ 闸 fail-closed 直接选卡。故「建议刷 ∧ 锚读缺」**结构性不可达**，不存在无界循环面（本设计初稿「卡死一条龙级风险」的机理叙述有误，审查链按该错误前提复核，随本条修正）。`cw_screen_encounter` 重调分支仍落 `round_fail` 兜底（防观察与动作之间画面状态错乱的纵深防御，非活跃缺陷修复）；行为测试同步改写。其余 op 层无行为改动（仅注释收口，§2.8）。
- 刷新机会成本 v1 不建模（照投资环境批同构论证：同分布假设下「留着以后刷」无期望优势；遭遇刷新每局 1 次，跨遭遇节点分布同构性高于投资环境）。

### 2.6 输出契约与接线

- `encounter_pick.py` 纯值出口：`EncounterPickDecision(idx, reason)` / `EncounterRefreshSuggestion(reason)`（dataclass，不含动作词表——与 `invest_env`/`supply` 同构，便于直测与 sim 复用预留）。
- kernel 的 `EncounterPick` dataclass 随决策本体退役（历史 EV 核的 `EncounterPick` 依赖见 §2.7 EV 核条目）。消费面全列（直调核实）：
  - `cw_encounter_selection.decide_encounter`（判据本批迁移）与 `bridge.py` 顶层 import + 运行时注解——随判据迁移/覆写删除处理；
  - **动作链零改动**：`CwActionPickEncounterOp` 静态入参 = 词表动作 `CwActionPickEncounterParam`（生产派发链传词表动作，`idx` 鸭子式消费）；`report_action_pick_encounter_param` 入参 `param: Any` 鸭子取 `idx`——生产契约与 `EncounterPick` 无耦合；
  - 测试仓 `test_cw_unified_action_4.py`（类型 import + `:259`/`:278` 两处实例构造）：`EncounterPick` 实例是动作 op 的测试构造替身——随批**改传词表动作实例** `CwActionPickEncounterParam(idx=1)`（与生产派发同型，照补给批同款处理：载体退役 + 测试构造点随删换）;
  - `kernel/cw_events` 模块级构造：`EVENT_PICK_TYPES` 元组的 `EncounterPick` 位与 `EventPick` 联合别名的 `EncounterPick` 位**随类删除同批摘除**（模块级运行时构造，删类不摘位 = import 即 NameError；补给批同款先例；符号锚 `EVENT_PICK_TYPES`/`EventPick`，行号以落批实址为准）;
  - `kernel/cw_vocab.py` 两处 docstring「替代 EncounterPick」表述改指策略层载体（照补给批 `SupplyPick` 词表收口先例）。
- `flow.py::decide_encounter`：候选自 `gs.encounter` payload（`_require_slot_options` 守卫原样，含离屏 None 抛错——bridge 覆写删除后守卫不丢）；改调 `encounter_pick.decide(options, self.gs)`；`refresh_used` 预计算删除；入口内务 `_consume_prep_direction_frame()` 照兄弟入口保留；`EncounterRefreshSuggestion` → `CwActionRefreshNodeOptionsParam`，`EncounterPickDecision` → `CwActionPickEncounterParam`。词表、观察写槽、终结链零改动；op handler（`cw_screen_encounter`）除防线一处（§2.5）外零行为改动（其余注释收口，§2.8）。
- `bridge.py` `MandateV1Strategy.decide_encounter` 覆写**删除**：生产壳回落基类 flow 入口（与 `decide_supply`/`decide_invest_*` 同构——bridge 只覆写营业面，不覆写画面 pick 口）。

### 2.7 删除面（与接线同一 commit 原子切换，新旧不并存）

- `kernel/cw_events.py`：`decide_encounter` 函数体 + `_option_mechanics` + `_reward_value` + `EncounterPick` + 遭遇段头注释；模块 docstring 遭遇句收口（收口后本模块 = planner 等剩余画面决策 + 观察载荷契约）。
- `kernel/cw_survey19_hooks.py::encounter_tier_score`：唯一消费 = 被删的旧核 `_score`（全仓直调核实；P9_VALIDATION 已登记该模块「P1/P9/P8」旧编号与 math_proofs 无关，删除不受其影响）；**模块 docstring「P9 遭遇接难度账本」句随删件收口**（改述为「P1 狼狩穿戴纪律」单件模块头——`wear_discipline_alert` 零生产消费但属 P2 封存件活态后裔，**不动**，不在本批扩面）。
- `kernel/cw_encounter_selection.py` 删除/迁出面：`decide_encounter`/`g_ratio`/`_lowest_idx`/`_Diagnostics`/`_d_enc_snapshot`/五标定槽（`F_MIN`/`G_BASE`/`DELTA_T` 物理删除；`PROGRESS_BAR_DIRECTION`/`BAR_SEMANTICS` 迁策略层；**`D_ENC_VARIANT` 保留 kernel——装填语义消费，§2.3**）+ `_FILL_EDGE_THRESHOLD` + `_kappa_state` + `reward_tier` 与四档常量 + **`REWARD_TIER_LAST`（零消费公开符号，物理删除不留）** + `apply_calibration`/`reset_calibration`（全键版退役；kernel 按装填语义重建仅含 `D_ENC_VARIANT` 的注入口，§2.3）+ `selection_state_of`。模块 docstring 重写（暗装语义段退役；余量 = 结算观测基建 + 兑现回调契约 + 装填拨盘槽描述，§2.1）。
- `strategies/impl/mandate_v1/bridge.py`：`decide_encounter` 覆写删除 + 顶层 `EncounterPick` import 与运行时注解清理。
- `strategies/impl/mandate_v1/encounter.py`（历史 EV 核）+ `audit/provisional.py` 双槽（`ENCOUNTER_DSTAT_MAP`/`ENCOUNTER_G_GOLD`）——**已裁定退役删除**（§2.10 裁定点 1，2026-09-24 用户）；同步删除 provisional 头部标定注入指针句。
- `strategies/impl/flow.py`：`decide_encounter` 调用行与 `refresh_used` 预计算删除；`cw_events` import **保留**（`decide_planner`/`decide_fortune`/`choose_expert_index` 仍现役消费，直调核实 flow.py:656/793/807）。
- 注释指针收口（已知点全列；末阶段全仓复扫兜底）：`kernel/cw_vocab.py` 两处「替代 EncounterPick」表述、`obs/cw_node_obs.py` 模块 docstring「喂 `cw_events.decide_*` 等钩子」句、`read_encounter_options` docstring「decide_encounter 用 difficulty + comp 成型度选」句与「decide_encounter 按难度选」句、`kernel/cw_events.py` `EncounterOption.difficulty` docstring 三档旧知识句（「1=易/2=中/3=难」——实为六档，随载荷契约保留改写为六档事实）、`operations/cw_screen/cw_screen_encounter.py` 模块 docstring 与 act 段旧判据叙述（「全分支词缀克→刷新」「按 comp 成型度选」——均已非生产行为，改写为新判据指针）、`strategies/impl/flow.py` `decide_encounter` docstring「kernel 按原评分直接选卡」句（改写为新核语义）、`strategies/impl/mandate_v1/audit/provisional.py` 头部「新遭遇选档判据的标定注入 = kernel/cw_encounter_selection.apply_calibration」指针句（注入面迁策略层后改指——**无条件义务，EV 核两分支下都执行**）、`kernel/cw_events.py` `SupplyOption` docstring「检测集单一源 = cw_node_obs.DIAMOND_EQUIP_NAMES」句与 `strategies/impl/mandate_v1/supply.py` 同款句（钻石检测集单一源迁 kernel/cw_obs_core 后改指，§2.4）、`kernel/cw_economy.py` 败补参数 docstring「现役 6 个决策消费点…encounter.py」句（EV 核退役分支下失指，改写消费点清单；保留分支下不失指、不动）、`strategies/impl/cw_strategy.py` 接口注、`kernel/cw_difficulty_account.py` `from_strategies` docstring「挂 decide_encounter 消费批」句（消费批退役，改写为「marginal_value/DifficultyAccount 零生产消费，孤儿态登记」）。**fill 阈值形态登记义务（随 31 号稿）**：`_FILL_EDGE_THRESHOLD = 0.5` 在进度条双定谳注入后成活闸门数字——注入批须按【拟】纪律登记（CI + fail-closed 退路），31 号稿数学挂账明列该申报义务（本批 None 不激活）。
- `cw_difficulty_account` 孤儿申报：`marginal_value` 唯一消费链 = 被删的 `encounter_tier_score`；`DifficultyAccount` 全仓零生产消费（P9 时代遗留记账件）。本批只申报孤儿态 + 注释收口，物理删除归后续清理批（不在本批扩面）。**辖域注（后续清理批义务）**：模块常量 `GROWTH_PER_STREAK` 有 sim 活消费（`sim/cw_sim_enemy.py`），清理批不得整模块物理删除——按符号逐个处置。
- 测试面：`test_cw_obs_arch_event_screens.py` 的 `cw_encounter_selection` import 点消费**保留面符号**（`claim_encounter_reward`/`record_settlement_row`）——零改动；同文件重调行为测试（「重调仍建议刷新 → 零点击终结交回」）**随防线改写**（行为断言改写为零点击交回 → `round_fail` 交回，docstring 同步——与 §2.5 防线同一处置，非仅叙述更新）；`test_cw_unified_action_4.py` 的 `EncounterPick` 类型 import 与两处实例构造点改传词表动作实例（§2.6）；新决策本体测试随落地批落测试仓（landing 3.1）。`claim_encounter_reward` 分支测试（kernel 保留面）不动。

### 2.8 op 层收口（防线一处行为改动 + 注释收口）

- `cw_screen_encounter.py`：防线一处（§2.5 重调分支改 `round_fail`）；模块 docstring 与 act 段的旧判据叙述（§2.7 指针收口同面）；「重调按原评分选」类内联注随闸内嵌语义改写（照补给批 `cw_screen_supply_node` 同款收口先例）。
- 其余 op/上报层：`cw_pick_encounter_action` 动作 op、`cw_action_report/pick_encounter.py`、`cw_battle_wait` 遭遇观测面（`_cw_selection_write` 装填分支消费 `D_ENC_VARIANT` 照旧——None 期遭遇行恒 None，§2.3 保留决定）零改动。

### 2.9 文档面（宪法六）

- 新建 `strategy-docs/31_encounter_screen.md`：画面 = 货币战争-遭遇节点；决策本体指针 = `strategies/impl/mandate_v1/encounter_pick.py`；判据语义 = 本设计 §2.2–§2.5；**as-built 转写纪律**：数值/序数只写常量名与语义（cap、偏好序档等单一源在 `encounter_pick.py` 立场常量区），正本不抄值；裁定登记（结算观测授权 = 04 号稿裁定 9 指针〔辖域 = 数据通道与持久化〕、刷新剩余语义 2026-09-21、**cap 与偏好序的【拍】立场登记〔含章程 §6 修订提案与过目记录〕**、EV 核处置 = §2.10 裁定结论）；数学挂账（比值腿复活 = 浮层读数通道批、E-3 标定〔注入位 = 策略层；`_FILL_EDGE_THRESHOLD` 注入后按【拟】纪律登记的申报义务〕、EV 形态挂 P26、档位↑⇒奖励价值↑ 采样验证、P2 序列两源对账、窗口战斗类变体触发器 = §2.2、补给孪生面防线 = §2.11 挂账交接）；sim 盲区申报（§2.12）；能力面指针 `../screens/README.md`。正本 as-built，判据细节不复制 13/08 号稿（反向指针）。
- `25_event_overlays.md`：画面族清单移除遭遇（头注、§1 prose、§2 动作清单表行），头注加「遭遇已拆 31 号稿」（照 28/29/30 号稿拆分先例）；§2 表行退役屏「装备」残留一并清理。
- `13_pick_family.md`：`decide_encounter` 行（「双轨」过期描述）整体改写为单一源指 31 号稿；§2 事件面目录 E3 行同改。
- `08_events.md`：E3 行「现有语义」格整体替换为「能力态直通形（κ_S 三态 + 经验档层 + 奖励序数 tiebreak + 刷新阀；决策本体 = `strategies/impl/mandate_v1/encounter_pick.py`，语义单一源 = 31 号稿）」；「判据状态」列维持「待 derive」（比值腿/EV 形态仍待 P26 与读数通道）；立项锚不变（P26）。
- `04_survival_budget.md`：裁定 9 行「判据正本 = `kernel/cw_encounter_selection.py`」→「判据正本 = 策略层 `encounter_pick.py`（迁移批；结算观测持久化基建留 kernel）」；同行补判据结构合法性载体分层（授权辖域 = 数据通道与持久化；结构确认载体 = 对抗审查，§2.2）。
- `strategy-docs/README.md` §2 分篇表：增 31 行；阅读导航句「18-30」→「18-31」。
- 画面文档策略指针面随批去陈旧：`docs/develop/sr_od/application/currency_war/screens/encounter.md`（决策委托句、刷新闸行为叙述句——防线后过期）、`docs/game/screens/currency_war_encounter.md`（算法描述句；文件名 ≠ 画面名，落批全路径核对后改写）。

### 2.10 关键取舍与待用户裁定点

- **裁定点 1（已裁定 2026-09-24 用户：退役删除）**：历史 EV 核（`mandate_v1/encounter.py`）+ `audit/provisional.py` 双槽退役删除。裁定依据：三核并存使「遭遇判据单一源」语义永久含混（13 号稿双轨描述漂移即实证）；EV 数值臂被 P64 判死（静态映射不可标定），点亮前置（条件表 ≥3 局实采 + G_gold 定带）双悬空，悬置期零行为面（双 None 恒 fail 向）；其数学形态（P26 同构）在 08 号稿 E3 锚行与 P26 单篇留档，git 历史可溯，设计资产不丢失；现态 src+测试仓双零消费（全仓 grep 直调）——退役零功能损失。
- **暗装门收窄 vs 等待完整标定链**：收窄立即止损——恒最低档 = 奖励轴整局放弃，而 κ_S/经验层/tiebreak 全部在裁定 9 授权辖域内且零标定可判；等待 = 无限期闲置已授权基建。败局风险控制由 cap（边缘 ≤ 其二）+ 刷新阀 + fail 向最低档承担，与「发展优先默认 + 危险只升不降」相容（§2.2 宪法三方向核查）。
- **字典序/加法标尺均不适用**：遭遇判据是单轴风险门（可及性）+ 序数 tiebreak，不存在 env/supply 那种多轴不可通约合分问题——无需新标尺结构，沿用已授权三态结构是唯一零新数值形态。
- **窗口候选（取舍：维持候选 A——普战窗口）**：曾评估候选 B（战斗类窗口 = 普战 + 遭遇）——kernel 真值表下与候选 A 逐位等价（§2.2 逐帧推演）；economy.md 双遭遇表下有差异面但该表未定谳，且改形的行为面论证（遭遇行证据适用性 × κ_S 组合语义）未做。无行为面确证的语义变更不做；对账挂账 + 变体触发器登记 31 号稿。
- **`encounter_pick.py` 命名**：不复用 `encounter.py` 空名（即使 EV 核退役）——git 考古防混；与动作词表 `CwActionPickEncounterParam` 呼应。

### 2.11 批间协调（在飞批）

- **补给批（30 号稿）已落地**（正本/README §2/25 号稿头注/删除面均已入库——直调核实 `cw_survey19_hooks` 中 `supply_reroll_decision` 已不在），与彼批无在飞共享面。本批落批时仍按符号锚重核彼批触碰过的文件现态（`cw_survey19_hooks` 剩余面 = `encounter_tier_score` + `wear_discipline_alert`；`cw_events` 模块 docstring 现态已含补给收口句）。
- **sim 基建批（sim-backend-unification / action-world-decl，在飞）**：结算环 sim 写端交接（本批 sim 可见性的唯一前置，§2.12）；本批不改 sim 文件。
- **补给孪生面（定性修正，撤销「带病」申报）**：补给屏重调分支（`cw_screen_supply_node` 「建议刷 ∧ 对照闸拒绝 → 零点击终结交回」）与遭遇屏同源同构——观察先于决策、次数文本同源双信号（§2.5 机理定谳），该分支**同样结构性不可达**，非在产风险。两屏各自的死分支行为（遭遇 = round_fail 兜底 / 补给 = 零点击交回）无需强行统一；若将来补给域批顺手对齐为 round_fail 亦无害，非义务。撤销「在产带病」挂账。
- **浮层读数通道批（未立项）**：本批交付后其点亮路径 = `gs.enemy_difficulty` 读口（现成）+ 比值腿结构（git 可溯）+ 浮层画面 op 链（`货币战争-敌人信息浮层.md` 入口②形态已建档）。挂账指针进 31 号稿数学挂账节。

### 2.12 sim 可观测性申报与验收锚点

- **sim 结构性盲区**：sim 局结算环无写端（sim 结算腿不调 `record_settlement_row`）→ κ_S 窗口恒空 → sim 遭遇决策恒「窗口不足 → 闸 None 拒刷 → 最低档」，与改前 sim 行为（暗装：最低档 + 零刷新）**逐位一致**。本批差异 sim 不可见，不可作 A/B 判据（照补给批盲区申报口径）。
- 可见前置 = sim 结算腿接环（单点：coarse 战斗结算输出处调 `record_settlement_row`），交接 sim 基建批。接环后 sim 可见形态 = 四档占位（`ENCOUNTER_TIER_COUNT=4`，奖励占位文本）下 κ_S 驱动选档；占位奖励文本（「金+20(占位…)」不含「金币」字面，直调 `reward_tier` 语义）全落**末档**，tiebreak 维度 sim 恒并列（全候选同档）——行为差异只在主序与刷新阀。
- **验收 = 单帧测试 + 实机判读锚点（事前写定）**：
  1. 足量帧选最高可及档（reason `pick:t{k}|kappa=足量`）；
  2. 边缘帧 ≤ 其二（cap 生效）；
  3. 不足帧：有次数建议刷 / 无次数最低档（闸内嵌两臂）；
  4. 其五/六仅经验层放行（无 killed=True 历史行 → 不可及）；
  5. 同档并列 tiebreak 序（钻>装备>金币>末档，构造 fixture 验证）；
  6. 窗口维持普战口径（P1 首遭遇帧 = r7，窗口 = r4/r6 两场普战；奖励行不入窗）；
  7. 重调兜底分支（结构性不可达，§2.5）：若因状态错乱到达「建议刷 ∧ 锚读缺」→ 重调后 `round_fail` 交回（纵深防御形态测试）。
- **验收线保全申报**：盘点当期在册验收线（当期迭代 criteria + math_proofs 判据节 + batch_stats 读数行）——**无任何在册验收线以遭遇选档为直接判据面**；遭遇档位变化影响出口金/存活的通道受 κ_S 门 + cap + 刷新阀约束（风险受控向）。P85 前置升级命题的 A/B 分键（遭遇备战帧）与 λ 死亡带面不消费选档输出，零影响。

**行为变化申报（验收对照基线；①–⑤为判据语义变更或行为面变化，是本迭代目的非回归）**：
1. 从恒最低档 → 能力驱动：足量帧选最高可及档（t ≤ 4 直接判定；5/6 经验层）。
2. 刷新从从不 → 可及集空帧建议刷（每局 ≤ 1，闸内嵌）；重调兜底分支落 `round_fail`（结构性不可达的纵深防御，§2.5）。
3. tiebreak 激活：钻>装备>金币>末档（暗装期恒不触发）。
4. 旧核知识判据（词缀契合/成型度/难度账本压档/P3 位面支）退役——生产从未生效（壳覆写后恒走暗装核），基类兜底路径行为变化如实申报；P3 位面字面量分支退场 = 宪法第二条违例存量清除。
5. 窗口/κ_S 三态/经验档层结构相对生产现役无行为差异面（暗装期全部不可达）——激活即本批第 1–3 条本身，无单独申报项。
