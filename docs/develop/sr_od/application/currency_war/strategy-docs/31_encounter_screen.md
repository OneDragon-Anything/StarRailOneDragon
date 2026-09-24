# 31 遭遇画面策略(encounter screen)

> 画面 = 货币战争-遭遇节点(选难度档二选一 + 每局一次分支刷新;**能力面** = [../screens/README.md](../screens/README.md) §5.2/§5.5)。本篇 = 该画面的**策略面**(宪法六「一画面一策略文件、一画面一策略文档」兑现;宪法五/六原文 = [00_framework.md](00_framework.md) §1 第 5/6 条)。
> 决策本体 = `strategies/impl/mandate_v1/encounter_pick.py::decide`(纯值出口);动作包装 = `strategies/impl/flow.py::decide_encounter`(零参口,候选自容器 `encounter` payload);画面 op = `operations/cw_screen/cw_screen_encounter.py`(观察 + 决策动作两 node,能力细节 = [../screens/encounter.md](../screens/encounter.md))。pick 族接口规格 = [13_pick_family.md](13_pick_family.md) §1 `decide_encounter` 行、事件面目录 = [08_events.md](08_events.md) E3 行——彼处只留指针,判据细节不在彼处复制,本篇 = 判据语义单一源(反向指针);数值单一源在代码(本篇只写常量名,立场值单一源 = `encounter_pick.py` 立场常量区)。
> 术语:**结算观测环** = 结算行滚动的定深容器(`gs.settlement_ring`,每普通战斗行记 killed/进度填充率等);**删失** = 某场结果的 killed 读数为 None(结果未观察到,不作胜负证据);**κ_S 能力态** = 由窗口两场胜负归纳的当前作战能力三态(足量/边缘/不足);**可及集** = 当前能力态下允许进入选档比较的候选档集合;**fill 分支** = 恰一胜时用败局侧进度填充率给能力态降档的分支;**fail-closed** = 读数缺失时取不放行/不动作的保守分支;**【拍】立场值** = 用户策略立场的登记值(非推导产物、非观测估计,合法性来自裁定本身;章程 = [01_math_framework.md](01_math_framework.md) §6)。

## 1. 裁定登记

本画面判据结构由四项裁定定死;立场值合法性 = 裁定本身(裁定即证据):

1. **结算观测授权**:以结算观测读数(敌方通道 killed/进度填充率)作遭遇决策输入并入 GameState 持久化——授权 = [04_survival_budget.md](04_survival_budget.md) §7 对账表第 9 行(用户 2026-09-12 逐项确认,硬闸门例外扩大程序完成)。**辖域 = 数据输入通道与持久化**:该行授权的是「读数可用 + 可持久化」,不构成判据结构的授权;结构合法性载体见第 3 项。kernel 保留面 = 结算观测持久化基建(`SettlementRing`/`record_settlement_row`/`EncounterLog`/兑现回调 `claim_encounter_reward`,驻 `kernel/cw_encounter_selection.py`)与观察载荷契约(`EncounterOption`)——判据与标定面已全部离开 kernel(2026-09-24 迁移批,宪法五)。
2. **刷新剩余语义**(用户 2026-09-21,全域规范 = [../screens/op-layer.md](../screens/op-layer.md) §1.4):「可否再刷」一律消费屏显「剩余次数：N」观察读数(容器 `gs.encounter_refresh_left`,None = 未观察 → 拒刷)。
3. **【拍】立场登记三项批准**(2026-09-24,同一裁决门一并批准生效):
   - **章程 §6 修订**(supersession [01_math_framework.md](01_math_framework.md) §6 分界条款):原文「凡『数值大小参与方向/闸门判断』的量归【推】/【拟】纪律」——本画面论证该归属对**偏好型闸门值**失义(【拟】三要素〔置信区间/标定义务/期限〕预设「对世界的观测信念」,而立场 cap 与偏好序是对偏好方向的登记:无观测对象、无置信区间语义);修订新增**闸门位立场值**形态:登记即立场、零拟合零观测。
   - **边缘态难度上限**:κ_S = 边缘时可及难度档 ≤ `EDGE_CAP`(立场常量,保守向:能力缺口最近出现过、无余量论证)。
   - **奖励偏好序**:钻 > 装备 > 金币 > 末档(立场常量,过目登记 = `REWARD_ORDER_APPROVED`)。
   - 两值登记表 = `encounter_pick.py` 立场常量区(集中一处,值单一源在代码)。**用户备注**:两项为暂定值,实机遥测数据累积后重拍(重拍触发器 = 遭遇帧判读积累)。**重拍回退机制**:立场常量任一置 None → decide 走「立场未过目」回退态(恒最低档零刷新,§2.6)——重拍 = 直接编辑立场常量区,commit 即过目凭据。
4. **EV 核退役删除**(2026-09-24 同日裁定):历史 EV 判据核 `mandate_v1/encounter.py`(EV(b) = V_r − Δλ_death·G_loss 形态)与 `audit/provisional.py` 双槽整体退役删除——三核并存使「遭遇判据单一源」语义永久含混;EV 数值臂被 P64 判死(静态映射不可标定)、悬置期零行为面(双 None 恒 fail 向选低难零刷新)。其数学形态(P26 同构)在 08 号稿 E3 锚行与 P26 单篇留档,git 历史可溯,设计资产不灭失。

## 2. 决策结构:能力态直通形

判据链 = 窗口 → κ_S 三态 → 可及集 → 选档主序 + 奖励 tiebreak → 刷新阀 → fail 向。原则:**零新数值、零新拍值**——结构沿用已授权的判据形态,立场两值为【拍】登记(裁定 3);可及性比值腿(`g^(D_win−D_enc) ≥ f_min` 形态)已退役(P64 判死,§4 挂账),能力态直接判。

决策入口(纯值出口,与 supply/invest_env 同构):

```
decide(options, gs)
    -> EncounterPickDecision(idx, reason) | EncounterRefreshSuggestion(reason)
```

- **签名最小**:无阵容意向参(词缀轴 = 死输入——遭遇选项 UI 不显词缀、战后才显,难度轴按能力态判);无刷新已用参(次数闸内嵌,读剩余语义)。
- **空候选帧**:`options` 空 → `EncounterPickDecision(idx=0, reason='no-options')`(纯函数定义完备;观察层守卫——读不到标题返空列表零点击——下不可达)。
- **依赖面**:容器读口 `gs.settlement_ring`(结算观测环窗口)/`gs.encounter_log`(经验档层)/`gs.encounter_refresh_left`(刷新阀);奖励检测集 = `kernel/cw_obs_core.DIAMOND_EQUIP_NAMES`(kernel 手维护读数域真值,生成文件不可作宿主);装备注册表 `data/cw_equipment_data.EQUIPMENT_ROSTER`。依赖方向:策略层 → kernel/data 单向(kernel 零指向 strategies、策略层零 import obs,宪法五)。

### 2.1 窗口(最近 2 普战行)

结算观测环最近 **2 个普通战斗行**(`SettlementRing.last_normal_battles(2)`;奖励/遭遇/boss 行不入窗)。<2 行 → **窗口不足独立态**(数据不足 ≠ 能力不足,与 κ_S「不足」分因可判读)→ 刷新阀(因词 `window-insufficient`)。窗口口径维持普战口径——曾评估「战斗类窗口(普战+遭遇)」改形并否决(节点日程两源分歧未定谳;变体触发器见 §4)。

### 2.2 κ_S 能力态三态

仅窗口足时评估;输入 = 窗口两场 killed(None = 删失),三态表语义单一源 = `encounter_pick.py::_kappa_state`:

| 窗口两场(killed) | 态 |
|---|---|
| 全胜 | `足量` |
| 恰一胜(另一场 = 败局或删失) | `边缘` |
| 两场全败 / 双删失 / 一败一删失 | `不足` |

- **fill 分支**(恰一胜、另一场为败局时):用败局侧进度填充率给能力态降档——仅在进度条双定谳槽 `PROGRESS_BAR_DIRECTION`/`BAR_SEMANTICS` 注入定谳后激活(注入位 = `encounter_pick.apply_calibration`,合法键 = fill 双键);未定谳期不激活,fill 只走删失分支(照旧 fail-closed)。删失优先于 fill:另一场为删失时整场按删失计,不读填充率。
- `不足` → 可及集空 → 刷新阀(因词 `kappa-不足`)。

### 2.3 可及集(cap 过滤在前;其五/六经验档层)

候选档 = `opt.difficulty`(OCR 卡标题「遭遇其X」派生,漏读「一」→ 1)。构造顺序:cap 过滤在前 → 档层判定:

- **t ≤ 4**(档位有源层):能力态直判——`边缘` 态难度档 ≤ `EDGE_CAP` 才可及;`足量` 态全档可及(cap = 档位值域上界,语义等效不设限,照判据形态逐位同构、不简化为无判定)。
- **t ≥ 5(其五/六,等级加成 Δ 无源层)**:**经验档层交集**——`gs.encounter_log.tier_cleared(t)`(本局该档存在 killed=True 遭遇行)才可及。依据:其五/六的 Δ 无源,经验正证据是唯一安全通道;遭遇奖励为伤害进度达标制非清场制(`docs/game/currency_war/research/combat.md` §3),killed=True 蕴含进度达标,方向安全。
- cap 过滤在前 ⇒ 边缘态下 t ≥ 3 全排除(含其五/六),经验档层不放大 cap。
- 可及集空(足量/边缘态但候选全被 cap/经验层排除)→ 刷新阀(因词 `empty-reachable`)。

### 2.4 选档主序与奖励 tiebreak

- **主序**:可及集按难度档**最高**取(依据 = 游戏原文「难度越高敌人越强大」+ 实测奖励随档升;采样验证挂账 §4)。
- **同档并列 → 奖励偏好序 tiebreak**(`reward_tier`,纯文字匹配序数,小 = 优):奖励预览文本命中钻石检测集(`DIAMOND_EQUIP_NAMES`)→ 钻档;命中装备注册表(含工具类,同档不细分)→ 装备档;含「金币」字面 → 金币档;映射不到(含空文本/奖励预览缺失)→ 末档。序 = 裁定 3(钻 > 装备 > 金币 > 末档);只用序数,无价值数值(奖励子型金等价建模不在册——「金币×2」金额非机制常量,P64 金额侧同判)。
- **仍并列 → 输入序先**(options 左→右 = 画面卡列序)。

### 2.5 刷新阀

- **建议刷 = 且仅 = 可及集空 ∧ `gs.encounter_refresh_left ≥ 1`**(闸内嵌 decide;None = 未观察 → 不建议刷,fail-closed;剩余缺/尽 → 直接落最低档)。因词三枚举:`window-insufficient`(窗口不足)/`kappa-不足`(能力不足)/`empty-reachable`(能力够但候选全被排除)——数据不足与能力不足分因,判读可分。
- 刷新只是建议——是否真刷由画面 op 按现读剩余与刷新锚点裁决(失败安全,`../screens/encounter.md` §4);刷新机会成本 v1 不建模(同分布假设下「留着以后刷」无期望优势;遭遇刷新每局 1 次)。

### 2.6 fail 向与归因串

- 标定缺失型暗装(判据所需标定值缺失 → 机械退保守缺省的旧形态)**已退役**——比值腿退役后无未定谳标定槽挡在判据前。fail 向仅两形:
  1. 可及集空且不可刷 → 最低档:reason = `e3-simple|dark-fallback:<因>`(因 = §2.5 三枚举);
  2. 立场常量未过目(任一置 None)→ **恒最低档零刷新**:reason = `e3-simple|dark-fallback:stance-unconfirmed`(立场未过目回退态,重拍回退的现成机制,裁定 3;窗口/κ_S 不评估)。
- **归因串格式**(判读侧契约,封闭枚举):前缀 `e3-simple|` 保留(遥测判读连续性);选档帧 = `pick:t{k}|kappa=<态>`;建议刷帧 = `refresh-valve:<因>`;fail 向帧 = `dark-fallback:<因>`(「不可刷」前置不另立因词)。标定缺失型 `dark-install` 段不再产出。

## 3. sim 盲区申报(结构性口径)

sim 局结算环无写端(sim 结算腿不调 `record_settlement_row`)→ κ_S 窗口恒空 → sim 遭遇决策恒「窗口不足 → 闸拒刷 → 最低档」,与迁移前 sim 行为逐位一致——**本批行为差异 sim 不可见,不可作 A/B 判据**。可见前置 = sim 结算腿接 `record_settlement_row`(单点,交接 sim 基建批)。接环后可见形态 = 占位奖励文本全落末档(tiebreak 维度恒并列),行为差异只在主序与刷新阀。验收 = 单帧锁(`sr-od-test/test/sr_od/application/currency_war/test_cw_encounter_pick.py`)+ 实机判读锚点(事前写定)。

## 4. 数学挂账

1. **比值腿复活 = 浮层读数通道批**:可及性比值腿被 P64 判死(旗牌→敌难度静态映射不可标定,证明 = [../proofs/p64-encounter-dstat-static-map-uncalibratable.md](../proofs/p64-encounter-dstat-static-map-uncalibratable.md));复活前置 = 敌方信息浮层「敌人难度」读数通道批(点亮前置链①;浮层画面知识 = [../../../../../game/screens/货币战争-敌人信息浮层.md](../../../../../game/screens/货币战争-敌人信息浮层.md),遭遇入口②形态已建档),比值腿结构与标定链 git 历史可溯。
2. **E-3 标定**:f_min/G_BASE 定标与进度条双定谳(fill 双槽),注入位 = 策略层 `encounter_pick.apply_calibration`(合法键 = fill 双键;kernel 侧注入口仅收 `D_ENC_VARIANT` 装填拨盘,两注入口物理隔离互不写入)。**申报义务**:fill 阈值 `_FILL_EDGE_THRESHOLD` 在双槽定谳注入后成活闸门数字——注入批须按【拟】纪律登记(置信区间 + fail-closed 退路 + 标定义务 owner 与期限);当前 None 期不激活。
3. **EV 形态挂 P26**:EV 判据形态(奖励增量 vs λ_death 敞口增量)挂 P26(硬节点备战 EV 门同构,08 号稿 E3 行立项锚);P26 待证明(条件表与分位口径未采)。EV 核退役删除(裁定 4)不灭失该锚。
4. **档位↑⇒奖励价值↑ 采样验证**:选档主序「难度档最高」的奖励侧依据现 = 游戏原文定性句 + 单帧实测(`docs/game/screens/currency_war_encounter.md`);升档的奖励价值增益须实机采样验证(原【拟】挂账载体 = 本节)。
5. **P2 序列两源对账**:节点日程两源分歧未定谳——kernel 真值表 `kernel/cw_node_schedule.py`(依据 `docs/game/currency_war/research/plane_schedule_observed.md`:P1 = 补给@r5 + 遭遇@r7,P2 = 补给@r3 + 遭遇@r5,两位面均单遭遇)vs [../../../../../game/currency_war/research/economy.md](../../../../../game/currency_war/research/economy.md) §10.2 实测表 P2 行 = 双遭遇(该行整体 1 帧待复核)。定谳前窗口维持普战口径。
6. **窗口战斗类变体触发器**:同位面第二遭遇确证 / 位面 P3 采齐运行任一出现 → 重评「战斗类窗口(普战+遭遇)」改形(遭遇行 killed 与普战行 killed 同为敌方通道生存证据,裁定 1 授权辖域内;boss 行不入窗——伤害锚异构档,两源表下 boss 均为位面末节点 = boss 后无遭遇决策点)。届时须补行为面论证(遭遇行证据适用性 × κ_S 三态组合语义 × fill/删失分支交互),无行为面确证的语义变更不做。
7. **补给孪生面防线交接**:补给屏重调分支存在同款「建议刷 ∧ 刷新锚读缺 → 零点击终结交回」无界循环面(`cw_screen_supply_node` 重调链;30 号稿落地后 `supply.decide` 可返 Suggestion 即激活)——同款防线(round_fail 交回计入重派上限)归补给域后续小批;跨件半问已升 **`../screens/op-layer.md` §1.4 全域条款批**(所有「建议刷 ∧ 锚读缺」同形分支统一防线形态,归流程域设计批)。
