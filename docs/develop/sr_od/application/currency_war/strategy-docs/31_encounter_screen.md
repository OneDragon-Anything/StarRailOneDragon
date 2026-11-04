# 31 遭遇画面策略(encounter screen)

> 画面 = 货币战争-遭遇节点(选难度档二选一 + 每局一次分支刷新;**能力面** = [../screens/README.md](../screens/README.md) §5.2/§5.5)。本篇 = 该画面的**策略面**(宪法六「一画面一策略文件、一画面一策略文档」兑现;宪法五/六原文 = [00_framework.md](00_framework.md) §1 第 5/6 条)。
> 决策本体 = `strategies/impl/mandate_v1/encounter_pick.py::decide`(纯值出口);动作包装 = `strategies/impl/flow.py::decide_encounter`(零参口,候选自状态容器(GameState) `encounter` payload);画面 op = `operations/cw_screen/cw_screen_encounter.py`(观察 + 决策动作两 node,能力细节 = [../screens/encounter.md](../screens/encounter.md))。pick 族接口规格 = [13_pick_family.md](13_pick_family.md) §1 `decide_encounter` 行、事件面目录 = [08_events.md](08_events.md) E3 行——彼处只留指针,判据细节不在彼处复制,判据权威定义即本篇、无需外跳(反向指针);数值单一源在代码(本篇只写常量名,立场值单一源 = `encounter_pick.py` 立场常量区)。
> 术语(首现定义):**单一源** = 该信息的唯一权威出处;**帧** = 一次截取游戏画面并做一次决策的时点;**结算观测环** = 结算行滚动的定深状态容器(`gs.settlement_ring`,每普通战斗行记 killed/进度填充率等);**删失** = 某场结果的 killed 读数为 None(结果未观察到,不作胜负证据);**κ_S 战力状态** = 由窗口两场胜负归纳的当前作战能力三档(足量/边缘/不足);**可及集** = 当前战力状态下允许进入选档比较的候选档集合;**fill 分支** = 恰一胜时用败局侧进度填充率给战力状态降档的分支;**fail-closed** = 读数缺失时取不放行/不动作的保守分支;**【拍】立场值** = 用户策略立场的登记值(非推导产物、非观测估计,合法性来自裁定本身;章程 = [01_math_framework.md](01_math_framework.md) §6);**数字来源标注(四种)**:【注】游戏定义值 /【推】已证推导 /【拟】观测估计 /【拍】用户立场登记值。

## 1. 裁定登记

本画面判据结构由四项裁定定死;立场值合法性 = 裁定本身(裁定即证据):

1. **结算观测授权**:以结算观测读数(敌方通道 killed/进度填充率)作遭遇决策输入并入 GameState 持久化——授权 = [04_survival_budget.md](04_survival_budget.md) §7 对账表第 9 行(用户 2026-09-12 逐项确认,硬闸门例外扩大程序完成)。**适用范围 = 数据输入通道与持久化**:该行授权的是「读数可用 + 可持久化」,不构成判据结构的授权;结构合法性载体见第 3 项。kernel 保留面 = 结算观测持久化基建(`SettlementRing`/`record_settlement_row`/`EncounterLog`/兑现回调 `claim_encounter_reward`,驻 `kernel/cw_encounter_selection.py`)与观察载荷契约(`EncounterOption`)——判据与标定面已全部离开 kernel(2026-09-24 迁移批,宪法五)。
2. **刷新剩余语义**(用户 2026-09-21,全域规范 = [../screens/op-layer.md](../screens/op-layer.md) §1.4):「可否再刷」一律消费屏显「剩余次数：N」观察读数(状态容器 `gs.encounter_refresh_left`,None = 未观察 → 拒刷)。
3. **【拍】立场登记三项批准**(2026-09-24,同一裁决门一并批准生效):
   - **章程 §6 修订**(取代 [01_math_framework.md](01_math_framework.md) §6 分界条款):原文「凡『数值大小参与方向/闸门判断』的量归【推】/【拟】纪律」——本画面论证该归属对**偏好型闸门值**失义(【拟】三要素〔置信区间/标定义务/期限〕预设「对状态副本(GameState)的观测信念」,而立场 cap 与偏好序是对偏好方向的登记:无观测对象、无置信区间语义);修订新增**闸门位立场值**形态:登记即立场、零拟合零观测。
   - **战力状态为边缘时的难度上限**:κ_S = 边缘时可及难度档 ≤ `EDGE_CAP`(立场常量,保守向:能力缺口最近出现过、无余量论证)。
   - **奖励偏好序**:钻 > 装备 > 金币 > 末档(立场常量,过目登记 = `REWARD_ORDER_APPROVED`)。
   - 两值登记表 = `encounter_pick.py` 立场常量区(集中一处,值单一源在代码)。**用户备注**:两项为暂定值,实机遥测数据累积后重拍(重拍触发器 = 遭遇帧判读积累)。**重拍回退机制**:立场常量任一置 None → decide 走「立场未过目」回退态(恒最低档零刷新,§2.6)——重拍 = 直接编辑立场常量区,commit 即过目凭据。
4. **EV 核已停用并删除**(2026-09-24 同日裁定):历史 EV 判据核 `mandate_v1/encounter.py`(EV(b) = V_r − Δλ_death·G_loss 形态)与 `audit/provisional.py` 双槽整体停用删除——三核并存使「遭遇判据单一源」语义永久含混;EV 数值分支已被 P64 证伪并删除(静态映射不可标定)、悬置期零行为面(双 None 恒走保守兜底选低难零刷新)。其数学形态(原 P26 同构,已废弃删除——2026-10-29 证明史清理,git 可溯)在 `08_events.md` E3 依据行按历史注记读,设计资产 git 历史可溯。

## 2. 决策结构:战力状态直选

决策流程:取最近两场普战结果 → 归纳战力状态(足量/边缘/不足)→ 过滤可选难度档 → 选最高档(同档按奖励偏好)→ 全不可选则建议刷新 → 刷新不可用则保底选最低档。原则:**零新数值、零新拍值**——结构沿用已授权的判据形态,立场两值为【拍】登记(裁定 3);可及性比值判据(`g^(D_win−D_enc) ≥ f_min` 形态)已停用(P64 证伪并删除,§4 登记待办),战力状态直接判。

决策入口(纯值出口,与 supply/invest_env 同构):

```
decide(options, gs)
    -> EncounterPickDecision(idx, reason) | EncounterRefreshSuggestion(reason)
```

- **签名最小**:无阵容意向参(词缀轴 = 死输入——遭遇选项 UI 不显词缀、战后才显,难度轴按战力状态判);无刷新已用参(次数闸内嵌,读剩余语义)。
- **空候选帧**:`options` 空 → `EncounterPickDecision(idx=0, reason='no-options')`(纯函数定义完备;观察层守卫——读不到标题返空列表零点击——下不可达)。
- **依赖面**:状态容器读口 `gs.settlement_ring`(结算观测环窗口)/`gs.encounter_log`(经验档层)/`gs.encounter_refresh_left`(刷新阀);奖励检测集 = `kernel/cw_obs_core.DIAMOND_EQUIP_NAMES`(kernel 手维护读数域真值,生成文件不可作宿主);装备注册表 `data/cw_equipment_data.EQUIPMENT_ROSTER`。依赖方向:策略层 → kernel/data 单向(kernel 零指向 strategies、策略层零 import obs,宪法五)。

### 2.1 窗口(最近 2 普战行)

结算观测环最近 **2 个普通战斗行**(`SettlementRing.last_normal_battles(2)`;奖励/遭遇/boss 行不入窗)。<2 行 → **窗口不足独立态**(数据不足 ≠ 能力不足,与 κ_S「不足」分因可判读)→ 刷新阀(原因编码 `window-insufficient`)。窗口口径维持普战口径——曾评估「战斗类窗口(普战+遭遇)」改形并否决(节点日程两源分歧未定案;变体触发器见 §4)。

### 2.2 κ_S 战力状态三档

仅窗口足时评估;输入 = 窗口两场 killed(None = 删失),三档表语义单一源 = `encounter_pick.py::_kappa_state`:

| 窗口两场(killed) | 态 |
|---|---|
| 全胜 | `足量` |
| 恰一胜(另一场 = 败局或删失) | `边缘` |
| 两场全败 / 双删失 / 一败一删失 | `不足` |

- **fill 分支**(恰一胜、另一场为败局时):用败局侧进度填充率给战力状态降档——仅在进度条双定案槽 `PROGRESS_BAR_DIRECTION`/`BAR_SEMANTICS` 注入定案后激活(注入位 = `encounter_pick.apply_calibration`,合法键 = fill 双键);未定案期该分支不激活(fail-closed 照旧)。删失优先于 fill:另一场为删失时整场按删失计,不读填充率。
- `不足` → 可及集空 → 刷新阀(原因编码 `kappa-不足`)。

### 2.3 可及集(cap 过滤在前;难度 5-6 档的经验档层)

候选档 = `opt.difficulty`(OCR 卡标题「遭遇其X」派生,漏读「一」→ 1)。构造顺序:cap 过滤在前 → 档层判定:

- **难度 1-4 档(t ≤ 4):数据有出处,直接判**——`边缘` 态难度档 ≤ `EDGE_CAP` 才可及;`足量` 态全档可及(cap = 档位值域上界,语义等效不设限,照判据形态逐位同构、不简化为无判定)。
- **难度 5-6 档(t ≥ 5,其五/其六):等级加成 Δ 无数据来源,只允许在本局已打赢过该档时选**——经验档层交集:`gs.encounter_log.tier_cleared(t)`(本局该档存在 killed=True 遭遇行)才可及。依据:其五/六的等级加成 Δ 无数据来源,经验正证据是唯一安全通道;遭遇奖励为伤害进度达标制非清场制(`docs/game/currency_war/research/combat.md` §3),killed=True 蕴含进度达标,方向安全。
- cap 过滤在前 ⇒ 边缘态下难度 ≥3 全排除(含其五/其六),经验档层不放大 cap。
- 可及集空(足量/边缘态但候选全被 cap/经验层排除)→ 刷新阀(原因编码 `empty-reachable`)。

### 2.4 选档主序与奖励平手裁决

- **主序**:可及集按难度档**最高**取(依据 = 游戏原文「难度越高敌人越强大」+ 实测奖励随档升;采样验证登记 §4)。
- **同档并列 → 奖励偏好序平手裁决**(`reward_tier`,纯文字匹配序数,小 = 优):奖励预览文本命中钻石检测集(`DIAMOND_EQUIP_NAMES`)→ 钻档;命中装备注册表(含工具类,同档不细分)→ 装备档;含「金币」字面 → 金币档;映射不到(含空文本/奖励预览缺失)→ 末档。序 = 裁定 3(钻 > 装备 > 金币 > 末档);只用序数,无价值数值(奖励子型金等价建模不已登记——「金币×2」金额非机制常量,P64 金额侧同判)。
- **仍并列 → 输入序先**(options 左→右 = 画面卡列序)。

### 2.5 刷新阀

- **建议刷 = 且仅 = 可及集空 ∧ `gs.encounter_refresh_left ≥ 1`**(闸内嵌 decide;None = 未观察 → 不建议刷,fail-closed;剩余缺/尽 → 直接落最低档)。原因编码三枚举:`window-insufficient`(窗口不足)/`kappa-不足`(能力不足)/`empty-reachable`(能力够但候选全被排除)——数据不足与能力不足分因,判读可分。
- 刷新只是建议——是否真刷由画面 op 按现读剩余与刷新按钮定位裁决(失败安全,`../screens/encounter.md` §4);刷新机会成本 v1 不建模(同分布假设下「留着以后刷」无期望优势;遭遇刷新每局 1 次)。

### 2.6 保守兜底与原因编码

- 标定缺失时自动退保守默认的旧机制**已停用**——比值判据停用后无未定案标定槽挡在判据前。数据缺失时的保守兜底仅两形:
  1. 可及集空且不可刷 → 最低档:reason = `e3-simple|dark-fallback:<因>`(原因段 `dark-fallback` 的语义 = 数据缺失时的保守兜底;因 = §2.5 三枚举);
  2. 立场常量未过目(任一置 None)→ **恒最低档零刷新**:reason = `e3-simple|dark-fallback:stance-unconfirmed`(立场未过目回退态,重拍回退的现成机制,裁定 3;窗口/κ_S 不评估)。
- **原因编码格式**(判读侧契约,封闭枚举;`e3-simple|`/`dark-fallback:` 为遥测字符串字面量,保持原样):前缀 `e3-simple|` 保留(遥测判读连续性);选档帧 = `pick:t{k}|kappa=<态>`;建议刷帧 = `refresh-valve:<因>`;保守兜底帧 = `dark-fallback:<因>`(「不可刷」前置不另立因词)。标定缺失型 `dark-install` 段不再产出。

## 3. sim 盲区申报(结构性口径)

sim 局结算环无写端(sim 侧结算链不调 `record_settlement_row`)→ κ_S 窗口恒空 → sim 遭遇决策恒「窗口不足 → 闸拒刷 → 最低档」,与迁移前 sim 行为逐位一致——**本批行为差异 sim 不可见,不可作 A/B 判据**。可见前置 = sim 结算链接入 `record_settlement_row`(单点,交接 sim 基建批)。接环后可见形态 = 占位奖励文本全落末档(平手裁决维度恒并列),行为差异只在主序与刷新阀。验收 = 单帧测试(`sr-od-test/test/sr_od/application/currency_war/test_encounter_pick.py`)+ 实机判读验收点(事前写定)。

## 4. 数学登记待办

1. **比值判据重新启用 = 浮层读数通道批**:可及性比值判据已被 P64 证伪并删除(敌方难度读数→敌难度静态映射不可标定,证明 = [../proofs/p64-encounter-dstat-static-map-uncalibratable.md](../proofs/p64-encounter-dstat-static-map-uncalibratable.md));重新启用前置 = 敌方信息浮层「敌人难度」读数通道批(点亮前置链①;浮层画面知识 = [../../../../../game/screens/货币战争-敌人信息浮层.md](../../../../../game/screens/货币战争-敌人信息浮层.md),遭遇入口②形态已建档),比值判据结构与标定链 git 历史可溯。
2. **E-3 标定**:f_min/G_BASE 定标与进度条双定案(fill 双槽),注入位 = 策略层 `encounter_pick.apply_calibration`(合法键 = fill 双键;kernel 侧注入口仅收 `D_ENC_VARIANT` 装填拨盘,两注入口物理隔离互不写入)。**申报义务**:fill 阈值 `_FILL_EDGE_THRESHOLD` 在双槽定案注入后成活闸门数字——注入批须按【拟】纪律登记(置信区间 + fail-closed 退路 + 标定义务 owner 与期限);当前 None 期不激活。
3. **EV 形态登记(登记对象已废弃)**:EV 判据形态(奖励增量 vs λ_death 敞口增量)原登记 P26(硬节点备战 EV 门同构)——P26 已废弃删除(2026-10-29,git 可溯),该形态重立须走新命题批。EV 核停用删除(裁定 4)的裁定不受影响。
4. **档位↑⇒奖励价值↑ 采样验证**:选档主序「难度档最高」的奖励侧依据现 = 游戏原文定性句 + 单帧实测(`docs/game/screens/currency_war_encounter.md`);升档的奖励价值增益须实机采样验证(原【拟】登记待办载体 = 本节)。
5. **位面 2 序列两源对账**:节点日程两源分歧未定案——kernel 真值表 `kernel/cw_node_schedule.py`(依据 `docs/game/currency_war/research/plane_schedule_observed.md`:位面 1 = 补给@r5 + 遭遇@r7,位面 2 = 补给@r3 + 遭遇@r5,两位面均单遭遇)vs [../../../../../game/currency_war/research/economy.md](../../../../../game/currency_war/research/economy.md) §10.2 实测表位面 2 行 = 双遭遇(该行整体 1 帧待复核)。定案前窗口维持普战口径。
6. **窗口战斗类变体触发器**:同位面第二遭遇确证 / 位面 3 采齐运行任一出现 → 重评「战斗类窗口(普战+遭遇)」改形(遭遇行 killed 与普战行 killed 同为敌方通道生存证据,裁定 1 授权适用范围内;boss 行不入窗——伤害读数结构异构(不同档),两源表下 boss 均为位面末节点 = boss 后无遭遇决策点)。届时须补行为面论证(遭遇行证据适用性 × κ_S 三档组合语义 × fill/删失分支交互),无行为面确证的语义变更不做。
7. **补给屏同形分支行为统一(非风险,随补给域批顺手对齐)**:补给屏重调分支(「建议刷 ∧ 对照闸拒绝 → 零点击结束本次访问、返回主循环」)与遭遇屏同构——观察先于决策、次数文本同源双信号(上报状态容器 + 圆钮定位读数),「建议刷 ∧ 定位读数缺失」结构性不可达,两屏该分支均为死分支兜底;遭遇屏形态 = round_fail / 补给屏形态 = 零点击返回主循环,行为统一随补给域批顺手对齐即可,非义务。
