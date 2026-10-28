# 补给屏策略层迁移与选卡改形 迭代设计（总纲）

## 0. 元信息
- 迭代目标：宪法第六条（一画面一策略文件、一画面一策略文档）在补给画面（`货币战争-补给`）的兑现，同时把补给选卡算法从「kernel 三支判据（带钻→必刷→成品+10+通用值）」改形为用户裁定的**三级字典序（钻 > 角色 > 装备）**。
- 裁定指针：
  - 宪法五/六：`strategy-docs/00_framework.md` §1 第 5/6 条（用户裁定 2026-09-23，env 批兑现先例）
  - 选卡三级优先与刷新「三空才刷」结构：**用户裁定 2026-09-24**（立场序合法性 = 裁定本身，同 28 号稿立场分形态；「末级」读法 A——只看档位，已确认 2026-09-24，见 §2.4）
  - 「想要的角色只为终局考虑，不按过渡阵容选」：**用户裁定 2026-09-24**
  - 备战席满时选角色卡 → 角色入**溢出席**（不会失败）：用户口径 2026-09-24，按机制事实登记
  - 16 号稿（`16_evaluation_tables_reassessment.md`）在册改形挂账：`decide_supply` 通用装备价值（经验拟合形态）→「带钻支配 > key_equip 命中 > 功能定序」，数值降格定序常数
  - 08 号稿 E4 挂账：组件缺口 = P42 `component_demand`/`hoard_gaps` 参数化；重刷期权挂 P40 变体②（08 E4 在册口径，类比挂账）
- 状态：对抗审中
- 文档清单：无详设（单文档方案，§2 即完整设计，深度 = 详设级）
- 承接：env 批与投资策略批「明确不解决」面均登记补给迁移为各自后续批（`changes/2026-09-23-invest-env-strategy-migration/design.md` §1、`changes/2026-09-23-invest-strategy-screen-migration/design.md` §1）；29 号稿编号已被投资策略批占用，本批文档 = **30 号稿**

## 1. 问题与动机
- 现状症状：
  1. **决策本体驻 kernel**：`kernel/cw_events.py::decide_supply`（带钻→选 / 无钻未刷→必刷 / 成品∈key_equips +10 + 通用价值定序）= 宪法五违例存量（kernel 内存量评分 = 待迁策略内容，`strategy-docs/README.md` §3）。
  2. **数值经验拟合进决策门**：固定 `+10` 与 `EQUIP_GENERIC_VALUE`（表自注「V4.4 meta 先验；实玩校准」，`cw_equip_value.py:36`）——16 号稿在册改形挂账未执行。
  3. **角色维度缺失**：`SupplyOption.char` 观察读取但完全不参与评分（`cw_events.py:616-647` 只消费 `equip`/`has_diamond`）；补给选项 = 角色+装备对，角色一半的价值被丢弃。
  4. **key_fit 仅成品直击**：`equip ∈ set(target_comp.key_equips)` 隶属判断——无需求计数（已持够数的重复成品照常 +10）、无组件/近兑现维度；与箱选卡共享机器 `equip_tier`（3/2/1/0 序数档，含需求计数与材料对）同语义两形态。08 号稿 E4 在册方向（「组件缺口 = P42 参数化」）即指此缺口。
  5. **刷新判据过粗**：全无钻 → 必刷（`cw_events.py:633-635`）——会把手握成品直击/近兑现的强帧无条件刷掉。
  6. **文档面**：`25_event_overlays.md` 族文档辖 11 屏（宪法六违例存量）；`13_pick_family.md` §1 `decide_supply` 行与 §2 E4 目录行描述（「选项价值 vs 目标线组件/成品需求」）与实码不符（实码无组件/成品需求计算）。
- 根因归层：**分层语义**（判据本体与策略 policy 未分离，宪法五）+ **语义**（选卡价值模型缺角色轴与合成维度、刷新判据无手牌质量条件）。
- 解决到哪：补给画面一个迁移批——新画面策略文件 + kernel 剪除补给决策 + 死代码删除 + 文档拆分（30 号稿）+ 算法改形（三级字典序）。
- 明确不解决：遭遇/planner/伙伴/巨星/星徽秘典/祈愿/专家邀请函/武装箱等其余画面迁移（各自后续批）；E4 数学判据完整 derive（P42 数值标定 🔴 待标定项落地后；本批以用户裁定序数结构落地，不声称期望最优）；钻石出现概率实采与刷新期望账数学化（重刷期权数学化留数据批；sim 侧 `supply_options` 为占位分布，`cw_sim_backend.py:573`）；augment 改写面建模（过剩经费双装备 = `SupplyOption` 单装备字段读面缺口、全都要/打捞人才库对选项集合的改写——登记观察面缺口，不在本批）；sim 补给决策分支接线与占位分布换真实池（sim 可见的双前置，见 §2.6 sim 申报——两前置均不在本批）。

## 2. 方案

### 2.1 文件组织（宪法六）
- 新增画面策略文件 `strategies/impl/mandate_v1/supply.py`：决策入口 + 三级判据 + 刷新判据，全在本文件（宪法六画面文件现役先例 = 同目录 `invest_env.py`，28 号稿首批兑现；同目录 `encounter.py` 为已搁置让位的历史 EV 核，非迁移先例）。
- 依赖方向：`strategies/impl/*` → kernel 单向（`supply.py` 消费 kernel `pick_equipment`〔内部 `equip_tier`〕/`same_star_count`/`GameState` 读口；kernel 零指向 strategies 的 import）。
- `SupplyOption` **留 kernel**（`cw_events.py:585-596`）：它是观察载荷契约——消费方五方：obs 写端 `cw_node_obs.read_supply_options`（`:21`）、容器 `gs.supply` payload（`cw_game_state.py` `supply` 字段，域版本 2；TYPE_CHECKING 引用同文件）、观察上报载体 `kernel/cw_screen_report/supply_node.py`（`:16`/`:41` `CwScreenSupplyNodeObs.options`）、sim 占位采样 `cw_sim_backend.py:78`、测试仓。观察形状归框架层（宪法五：与策略无关的游戏事实载体），只迁决策本体。
- `SupplyPick` 随决策本体迁出：src 仓内无外部类型 import（消费 = `cw_events` 内部 `EVENT_PICK_TYPES` 元组与 `EventPick` 联合别名 + flow 鸭子式字段消费 + `cw_vocab.py:728/915` 与 `cw_pick_supply_action.py:37` docstring 提及）；测试仓 `test_cw_unified_action_4.py:27-33` 有类型 import，随 3.2 删除面处理。

### 2.2 决策结构：三级字典序（零自由参数）
比较序 = **钻 > 角色 > 装备**（用户裁定 2026-09-24）。采用字典序而非加法合分：三轴量纲不可通约（人口位 / 终局阵容成员 / 装备），加法需新拍跨轴权值（违零调参方向）；字典序 = 用户偏好的直接编码，零自由参数（取舍详述 §2.8）。

决策函数（`supply.py`，纯值出口照 `invest_env.decide` 形）：

```
decide(options, gs, locked_comp: Comp | None, demoted_endgame: bool)
    -> SupplyDecision(idx, reason) | SupplyRefreshSuggestion(reason)
```

- 空候选帧：`options` 为空 → `SupplyDecision(idx=0, reason="no-options")`（与旧码同形；现役观察层/op 守卫下不应到达，纯函数定义须完备）。
- `locked_comp` 由 flow 解析后传入（已解析 comp 对象或 None）：套名字符串经 `get_comp` 解析，空串按未锁口径 None（无告警 = 未锁常态）、解析失败 None + 告警哨兵（照 `decide_box_card` 先例，`flow.py:712-718`）。`demoted_endgame` = 意向状态直通（True → 角色级与 key_equips 参照一律按未锁口径；防御位——现役降格路径已清 `locked_comp`，`cw_intention.py:2075-2077`）。

- **第 1 级 钻**：∃ `option.has_diamond` → 选。多张带钻 → 依次进第 2/3 级比出一张。
  依据：财富宝钻 effect 原文「拥有宝钻可以使团队规模上限+1，无论是否被角色穿戴。装备者每3个备战阶段提供1金币」（`cw_equipment_data.py:53`）；红钻/蓝钻 = 星徽合成材料（`:64-65`）；`has_diamond` 检测集 = {红钻, 蓝钻, 财富宝钻} 三钻（`cw_node_obs.py:215`）。
  边界申报：「带钻压过角色/装备级一切候选」是用户裁定序，不是已证支配论证——完整支配性论证（人口位价值 × 后续装备再遇期望）留 E4 数学批；实机判读锚点见 §2.6。
- **第 2 级 角色（只为终局）**：激活条件 = `locked_comp` 非 None ∧ 非降格帧（用户裁定：不按过渡阵容选；降格帧按未锁口径，同 env 批 `line_value` 口径）。激活时：`option.char ∈ locked_comp.core_chars ∪ shared_chars`（字段 = `cw_comps.py:102-111`；不含 `transition_chars`——过渡成员按裁定不入名单）的选项构成角色候选；候选非空 → 在候选内选；多候选 tiebreak：①能凑星者先（§2.3）；②仍并列 → 第 3 级装备比。角色级空转（未锁线 / 降格帧 / 全部 `char` 读缺）→ 全体进第 3 级。`char` 读缺（OCR 未命中，空串）的选项不进角色候选（仍参与装备轴）——不猜；取 13 号稿 §0 OCR 未就绪纪律之**精神**并显式申报偏离：该纪律字面辖域为「接口级 idx=0 兜底」，此处为「画面级候选剔除」，系同原则（读缺不猜）在选卡轴上的细化。
- **第 3 级 装备**：装备轴打分单一源 = **直调共享机器 `cw_equip_value.pick_equipment`**（`cw_equip_value.py:192-210`）：输入 `names` = 各选项 equip 序列，返回选中 idx——其 (tier, base) 字典序与下述排序语义逐位同构，并列取输入序先者（模块头「候选多选一禁第二套打分」裁定的辖内执行，不另写打分）。tier 语义（`equip_tier`，`:163-189`）：3 = key 直击且需求未满足 / 2 = 近兑现 / 1 = key 材料 / 0 = 其余；key_equips 可含重复、需求按计数——修掉 §1 症状 4 的重复成品误加分。输入三参：
  - `key_equips` = `locked_comp.key_equips`（与角色级同源；可含重复，需求 = 计数；None → 空序列，全体落 tier 0）；
  - `owned_spare` = `gs.equips` 现值（备用库存账）；
  - `owned_total` = spare + 行域/备战席穿戴账（`deployed_rows_of` + `bench_units_of` 成员 `equips` 透传）——两账口径照 `decide_box_card` 现役先例（`flow.py:719-740`），`supply.decide` 内自 gs 构造（gs 为纯函数输入，同口径同源）。
  排序：tier 高者先；同 tier → `equip_generic_value`（通用价值表，**降格为 tier 内定序常数**，16 号稿处置，表值零变化）高者先；仍并列 → 输入序先（`options` 左→右 = 画面列序）。
  所有权申报：`EQUIP_GENERIC_VALUE`/`equip_tier` 本体按宪法五读作待迁策略内容（在册迁移义务），本批仅消费不迁移、不扩面。

### 2.3 凑星 tiebreak 语义
「能凑星」= 选入该角色后与全场（上阵行域 ∪ 备战席）同名 1★ 恰成 3 张（合成 2★）。判据 = `cw_merge_simulate.same_star_count(char, 1, bench, deployed) == 2`（全场域同名同星计数单一源，`cw_merge_simulate.py:424-433`）。入参形状：`bench` = `bench_units_of(gs)` 槽序（`list[Unit]`，与 `same_star_count` 注解 `list[BenchSlot | None]` 形状不同层——运行时经条目身份协议对裸 Unit 正确、计数等价，形状差在此申报）；`deployed` **须为扁平 Unit 序列**——`deployed_rows_of` 返回 (front, back) 行域二元组，须展平拼接 `(*front, *back)`（照 `flow.py:729-731` `*_wf, *_wb` 先例）；直传二元组会被条目身份协议 fail-closed 静默跳过 = 上阵域漏计、凑星只数备战席。注意 `gs.board` 字段是上阵**羁绊计数**派生量（键 = 羁绊名，无角色名星级，字段 docstring 自注禁双写），不是本判据数据源。3★ 合成不入判据：补给入席单位恒 1★（`kernel/cw_action_report/pick_supply.py:48` 先验口径），2×2★ + 1×1★ 不满足 3 同星合成规则（`cw_merge_simulate.py:337` 同名同星 ≥3 合一）。席满帧已知失真：溢入单位不入 gs（§2.5 记账失真申报）。**排序依据**：用户裁定明示面 = 三级序与刷新结构；「能凑星者先」为会话内设计细化——结构论证 = 同名合成升星是终局成员战力成长的既有通道，**完成态优先、其余同列**（判据为布尔：恰 2 张同名 1★ 者优先，count 1 与 0 不分梯度），零自由参数。确认载体 = 对抗审查（2026-09-05 用户裁定：玩家过目门删除，符合策略核心即可落码）。——设计方申报：此 tiebreak 用户未明示，保留随时否决权。

### 2.4 刷新判据
- 建议刷 = 且仅 = **手牌三级全空 ∧ 次数闸放行**：
  - 三级全空 = 无带钻 ∧ 角色级无候选（或未激活）∧ 装备级全体落 tier 0（用户裁定 2026-09-24：字典序下「存在任一非末级项」= 值得拿）；
  - 次数闸 = `gs.supply_refresh_left ≥ 1`，**闸内嵌 decide**（照 `invest_env.decide` 读 `gs.env_refresh_left` 同构先例，`invest_env.py:388-401`）：容器读数 None = 未观察 → 不建议刷（fail-closed）。flow 现役的闸前移（`flow.py:544-545` 的 refresh_used 预计算随迁删除），decide 签名因此无 refresh_used 参。
- 闸拒绝帧的产出语义：闸内嵌后「三级全空 ∧ 建议刷但闸拒绝」组合**不存在**（decide 只在 left ≥ 1 时才可能返 Suggestion；left 缺/尽 → 直接落第 3 级选卡）。op 侧重调路径（`cw_screen_supply_node.py:275-292`）仅剩一种触发面：建议刷但刷新锚点缺失（`_refresh_point is None`）——重调同输入同输出（纯函数），仍返 Suggestion → 零点击终结交回，op 语义不变、op 层零行为改动。
- 全 tier-0 帧口径（**读法 A，用户裁定确认 2026-09-24**）：三级全空的判定只看 `equip_tier` 档位、**不看通用值**——tier 0 内含高通用值件（如表内 6 分档）的帧仍属「三级全空」、仍建议刷。裁定引文「存在任一非末级项 = 值得拿」兼容两读（「末级」= 装备轴序数末档 / = 全序末项 tier 0 ∧ 通用值 0，行为相反），**用户确认取前者**；30 号稿裁定登记收原文与确认记录；与旧制同域（旧制该帧同样刷：无钻即刷），非回归；实机锚③即验证该口径的行为表现。
- 依据与边界：本批判据是裁定结构，不声称期望最优；重刷期权的期望账数学化（08 E4「重刷期权挂 P40 变体②」在册口径）留数据批——钻石分布实采前任何期望式都是占位（sim `supply_options` 恒置一带钻槽，`cw_sim_backend.py:573-585`）。

### 2.5 输出契约与接线（接口契约，本批定死）
- `supply.py` 纯值出口：`SupplyDecision(idx, reason)` / `SupplyRefreshSuggestion(reason)`（dataclass，不含动作词表——与 `invest_env`/`deploy_plan` 同构，便于直测与 sim 复用预留）。
- `flow.py::decide_supply`：候选自 `gs.supply` payload（`_require_slot_options` 原样）；意向解析照 `invest_env` 同源自 `ist`（`flow.py:516-518` 先例）：`locked_comp` 套名经 `get_comp` 解析（空串按未锁 None 无告警、解析失败 None + 告警，与 §2.2 签名注同口径；`decide_box_card` 先例 `flow.py:712-718`）后传入，`demoted_endgame` 直通；入口内务 `_consume_prep_direction_frame()` 照兄弟入口原样保留（现 `flow.py:546`，全部 decide_* 入口同款）；`RefreshSuggestion` → `CwActionRefreshSupplyParam`，`Decision` → `CwActionPickSupplyParam`。词表、op handler（`cw_screen_supply_node`）、观察写槽、终结链**零行为改动**（3.2 对 `cw_screen_supply_node` 仅注释收口）。
- 席满：**选卡侧无需特殊处理**——选角色卡入溢出席（用户口径 2026-09-24；机制锚 = 实机建档溢出位单槽，`cw_game_state.py:2210-2229`）。**记账失真申报**：记账层在册「不建模溢出席」（gain-chain 迭代），补给角色分支经 `grant_bench_unit_cascade` 席满拒落零写（`cw_effect_inventory.py:1502-1505`）→ 席满帧溢入单位对 gs 不可见，§2.3 凑星判据对该单位系统性漏计；溢出位已被占的实机语义未核。失真归观察/记账批，不在本批修；触发器 = 实机席满补给帧判读。

### 2.6 删除面（与接线同一 commit 原子切换，新旧不并存；landing 3.1 工作区自验、入库随 3.2 一并执行）
- `cw_events` 精确删除项：`decide_supply` 函数体（`:616-647`）+ `SupplyPick`（`:599-605`）+ 段头注释（`:583`）+ `EVENT_PICK_TYPES` 元组该位（`:1003`）与 `EventPick` 联合别名该位（`:1007`）。**`SupplyOption`（`:585-596`）与 `_equip_value`（`:609-612`）保留**——前者 = 观察载荷契约（§2.1），后者仍被 planner 装备档回落打分消费（`:786`）。
- `kernel/cw_survey19_hooks.py::supply_reroll_decision`（`:46-56`）：全仓零消费死代码（唯一 `cw_survey19_hooks` import 点在 `decide_encounter._score`，只取 `encounter_tier_score`；src+测试仓 grep 零消费，2026-09-24 直调核实），三支语义与 `decide_supply` 内联重复——**物理删除，不留墓碑注**（垃圾代码纪律）。
- `+10` 常数与 key_fit set 隶属判据（被 `equip_tier` 需求计数替代）。
- 注释指针收口（已知点全列；末阶段另有全仓复扫兜底）：`cw_vocab.py:728/915`（「替代 SupplyPick」表述改指策略层载体）、`cw_events.py:1`（模块 docstring 补给决策句）、`cw_survey19_hooks.py:1-8`（模块头「P8 补给重刷判据」句随删件改写）、`cw_pick_supply_action.py:37`（「SupplyPick.refresh 决策」）、`cw_screen_supply_node.py:8-20`（模块 docstring 旧闸/旧决策语义叙述，含「重调一次决策按原评分选」）/`:242-245`（旧评分语义叙述）/`:39-40`（「sim 接线未接」——对决策分支为准确句〔§2.6 结构性盲区〕，随批精确化为「观察分支在产、决策链未接」防误读，非删除）/`:272-280`（「kernel 刷新闸同源同值」「重调按原评分选」内联注——闸内嵌后读缺分支与按评分选均不可达，随批改写为新闸语义）、`cw_node_obs.py:206`（「decide_supply 建模残缺」）、`cw_events.py:588-592`（`SupplyOption` 字段 docstring 两句旧决策语义〔「钻 = 拿到基本赢，碾压一切」「equip 旧打分用途」〕——载体保留但语义随批改写为载荷契约描述）。
- 测试面：在册无 kernel 侧 supply 决策专项测试（如实申报）；strategy 级 stub 两处（`test_cw_obs_arch_event_screens_step3.py:47/61`、`test_cw_supply_pick_immediate_report.py:125`）在 flow 方法名保留后继续有效、不随删；`test_cw_obs_arch_event_screens_step3.py:130-136` 幸存闸行为测试的 docstring 旧叙述（「重调按原评分选」）随批补语义过期注记（闸内嵌后该生产路径不可达；行为断言保留、叙述更新）；`test_cw_unified_action_4.py` 的 SupplyPick 类型 import（`:27-33`）与实例构造点（`:303`）随删；新决策本体测试随 3.1 落（`sr-od-test` 独立仓）。

**行为变化申报（验收对照基线；①②③④为判据语义变更，是本迭代目的非回归）**：
1. 角色级新增：锁线后终局成员卡优先于高价值装备卡（此前角色完全不参与）。
2. 装备级从「成品直击 +10 + 通用值」改为「需求计数 tier 序（含持有账）+ 通用值定序」：已持够数的重复成品不再高分；组件（key 材料）与近兑现升档。**归因口径**：key_fit 参照在现役锁线帧即生效（`flow.py:326` 锁线帧把注册表 comp 写入 `target_comp` → `:353`，kernel `cw_events.py:637/641-642` 消费）——本条真实变化 = **判据形态变更**（+10 隶属 → tier 需求计数/两账口径），非「从无到有」；key_fit 从未生效的只有 P1 配方锁局（伪 comp `key_equips` 恒空，申报 ⑤）。
3. 刷新从「无钻必刷」收窄为「三级全空才刷」：手握成品/组件/终局成员的帧不再被刷。
4. 多钻 tiebreak 新增角色/装备细分（单钻行为不变）。
5. **P1 配方锁带帧**（`flow.py:327` locked_comp 恒空）：角色级不激活；装备级无 key 参照（`locked_comp` 为 None → 空序列）→ 全体落 tier 0，选卡退化为「钻或通用值定序」；**刷新分支**：P1 无钻帧三级全空恒真 → 有次数即建议刷（次数闸内；实机锚③「三级全空仍刷」与锚④同帧先刷后选，不冲突）——与「不按过渡阵容选」裁定精神一致，如实申报该帧形态。

- `cw_replay --diff` 豁免申报：该旗标已随切源退役（`sim/cw_replay.py:10-12`），现役回放面只辖商店决策、不辖补给——本批影响面验证改由单帧测试（3.1）+ sim 盲区申报 + 实机判读锚点（3.4）承载，不构成验证缺口。

- **sim 可观测性申报（结构性盲区）**：sim 局中 `decide_supply` **零调用**——代码体链：op 决策分支以实例载体 `_sup_opts` 非空为门（`cw_screen_supply_node.py:264`，decide 调用点 `:275`/`:281` 在门内），`_sup_opts` 唯一写点在 live 读链 `_observe_live`（`:218`），sim 装配下 `sim_or_live_observation` 直返生成器产物、不执行 live_read（`cw_sim_ports.py:128-138`），生成器不回填实例载体 → sim 局 act 恒走 CARD_BODY 兜底（`:337-338`）。旧 kernel 判据同路径同样零调用——本批与旧制在 sim 中读数恰同（都零参与）。结论：sim 不可作本批 A/B 判据，盲区 = **决策链未接的结构性盲区**（`cw_screen_supply_node.py:39-40`「sim 接线未接」对决策分支为准确句，仅观察分支已随生成器在产——该注释按此精确化，非整句删除）。sim 可见的前置有二：①决策链接线（随 sim-redesign 批 M18 落地，§2.7 交接条目含此）；②占位分布换真实池。两前置齐后本批差异即 sim 可见，届时须补 A/B 申报。验收 = 单帧测试（3.1）+ 实机判读锚点（事前写定）：①锁线局补给帧，终局成员卡优先于高价值装备卡；②手握成品直击/组件的无钻帧不再刷新；③三级全空帧仍刷新——含 tier 0 内高通用值件帧（§2.4 显式解读申报；此锚验证该解读，不命中即回设计层）；④P1 配方锁帧：无钻三级全空 → 先刷（有次数），刷尽后按「钻或通用值」选卡（申报 ⑤ 刷新分支）；⑤席满帧凑星漏计已知（§2.5 记账失真申报，不判为异常）。

**验收线保全申报**：盘点当期在册验收线（当期迭代 criteria + math_proofs 判据节 + batch_stats 读数行），**无任何在册验收线以补给选择为判据面**；sim 侧无补给策略读数口径（现役占位分布下新旧读数恒同，§2.6 sim 申报）。`EQUIP_GENERIC_VALUE` 表值零变化，箱选卡（`decide_box_card`/`pick_equipment`）与装备穿戴/回收消费面行为零变化。

### 2.7 文档面（宪法六）
- 新建 `strategy-docs/30_supply_screen.md`：画面 = 货币战争-补给；决策本体指针 = `strategies/impl/mandate_v1/supply.py`；判据语义 = 本设计 §2.2-§2.5；裁定登记（**四项**：三级优先 / 终局名单 / 溢出席 / 刷新「三空才刷」结构含裁定原文与读法 A 确认记录〔§2.4〕，用户 2026-09-24）；数学挂账（E4 derive、带钻支配论证、重刷期权数学化）；sim 盲区申报（**结构性口径**：决策链未接，可见双前置 = 决策链接线 + 真实分布，§2.6）；能力面指针 `../screens/README.md`。正本 as-built，判据细节不复制 13 号稿（反向指针）。
- `25_event_overlays.md`：画面族清单移除补给（头注 `:3`、§1 prose `:11` 画面间差异要点、§2 动作清单表行 `:18`），头注「补给已拆 30 号稿」（照投资环境拆分先例，`:3-4`）。
- `13_pick_family.md`：§1 `decide_supply` 行（`:20`）改指 30 号稿单一源（照 `decide_invest_env` 行先例）；§2 事件面目录 E4 行（`:40`）同改（旧「组件/成品需求」知识判据描述随实态过期）。
- `strategy-docs/README.md` §2 分篇表：增 30 行；`:54` 阅读导航句随批改述「18-30」（落批前实为 18-29：env 批增 28 行时漏改仍为 18-27，投资策略批 3.3〔`9cce56962`〕已收口 18-27→18-29——彼时无 30 号稿可加；本批改 18-29→18-30）。
- `08_events.md` E4 行（`:19`）：实现形态注更新——**「现有语义」格整体替换**为「三级字典序（钻 > 角色 > 装备；决策本体 = `strategies/impl/mandate_v1/supply.py`，语义单一源 = 30 号稿）」，旧「选项价值 vs 目标线组件/成品需求」描述删除（与实态不符）；「待 derive」列挂账不变。
- **画面文档收口（策略指针面）**：三份画面文档随批去陈旧——`docs/develop/sr_od/application/currency_war/screens/supply.md`（`:12` 「缺省实现委托 kernel/cw_events.decide_supply」改指 `strategies/impl/mandate_v1/supply.py`；`:33`/`:40` 「重调按原评分选」、`:63` 「闸数据不一致」、`:80` 「拒绝→重调落选卡」、`:88` 测试描述「按原评分选」——均为旧闸语义，随批改写）、`docs/game/screens/currency_war_supply.md`（`:37`/`:57`/`:39` 算法描述/符号指称过期、`:19` 「待 Loop 接线」陈旧现状，随批更新）、`docs/game/screens/货币战争-补给.md`（`:32`/`:39` 同）。正本更新清单同步在列。
- `16_evaluation_tables_reassessment.md` `:74` 行：本批即其在册改形的执行批——挂账销账；该行**整体改写**为新结构映射：带钻支配 = 选卡第一级；「key_equip 命中」= 装备轴 tier 3（需求未满足直击）；「功能定序」= 同 tier 通用值定序；原挂账没有的角色轴 = 新增第二级细则——禁部分改写残留旧表述。行内死引用替锚（「`_EQUIP_VALUE`…`cw_events.py:293`」所指内联 +10/key_fit 形态现址 = `cw_events.py:616-647`，随批删除；`EQUIP_GENERIC_VALUE` 表本体现址 = `cw_equip_value.py:42-80`，本批保留为定序常数源；`sim/checks/ledger.py:970/1035` 全仓 src+测试仓零命中，清理）；「带钻支配（零参数已就位）」定性与 30 号稿对齐（定序最高档 + 支配论证留 E4 批）。
- **跨批协调（在飞 29 号稿批）**：本批与其共享 **8 处**编辑面——strategy-docs 4 份（25/13/README §2/16）+ `08_events.md`（29 批编辑 E2/E15 行，本批编辑同表 E4 行）+ `kernel/cw_events.py` 模块 docstring（29 批改模块头，本批收口 `:1` 补给句）+ `strategies/impl/flow.py` 与 `kernel/cw_vocab.py`（29 批 landing 证实两批都改这两文件）。批序纪律：本批各阶段落批时重读上述文件当前态再动笔；**行号锚以落批实址为准、符号锚优先**（29 批将删除 `decide_event` 全段约 270 行，届时本批 §2.6 全部 `cw_events` 代码锚漂移——其 landing 已点名该重核义务，本批 3.2 落批时按符号定位重核；29 批先落则 13 号稿锚随其 landing 增补〔共用判据节〕重定位）。
- **sim-redesign 批（2026-09-15）在册复用面交接**：`changes/2026-09-15-sim-redesign/design.md` 三处（`:70`/`:104`/`:267`）声明 kernel `decide_supply` 为复用面——本批迁移后该声明失配，交接 = 其落地接线时改指策略层 `supply.decide`（符号锚，照 29 批对 `decide_event` 的同款交接先例）；交接含 **sim 决策链接线提示**（其 M18 决策链落地 = sim 可见前置①，§2.6）；本批不改彼 design（changes/ 工件寿命 = 迭代）。

### 2.8 关键取舍
- **字典序 vs 加法合分**：三轴量纲不可通约，加法需拍跨轴权值（违零调参方向，也是 16 号稿要在补给清掉的形态）；字典序 = 裁定偏好的直接编码，零自由参数。代价：轴间不可补偿（终局成员卡永远压过高价值装备卡）——这正是裁定本意，如实申报。
- **复用 `equip_tier` vs 保留窄口径**：统一「同语义一套打分」（`cw_equip_value` 模块头「装备价值做成通用机器，禁第二套」裁定 5/6 的精神延伸），需求计数顺带修掉重复成品误加分；代价 = 装备分序与旧 +10 形态不同（申报 ②）。
- **两轴同源挂锁线 comp**：用户裁定「只为终局考虑」的字面执行——角色名单与 `key_equips` 都取锁线 comp。备选「装备级挂 `target_comp`」放弃的真实理由：①裁定语义——`target_comp` 的 P1 物化臂是**过渡配方伪 comp**（`flow.py:335-352`），让过渡载体为终局装备选卡背书与裁定精神相悖；②单源更简——锁线帧两载体同为注册表 comp（`flow.py:326`），key_equips 轴逐帧等价（P1 帧双方皆空），挂 `locked_comp` 少一载体少一解析。申报 ② 已按此归因（判据形态变更，非参照激活）；降格帧两轴随未锁口径空转（`demoted_endgame` 直通为防御位，见 §2.2 签名注）。
- **`SupplyOption` 留 kernel vs 随迁**：观察形状契约五方引用（obs 写端 / 容器 / 观察上报 / sim 占位 / 测试），kernel 所有；只迁决策本体，接口面最小。
- **两账构造第二份 inline 副本（跨件半问登记）**：`supply.decide` 的 spare+穿戴账构造与 `flow.decide_box_card`（`flow.py:719-740`）同形——同族第二次出现。本批保持 inline（改动面最小、读口机器未熟），抽公共读口（候选 = cw_game_state 级穿戴账读口，两处共消费）挂后续小批。
