# 补给选卡价值模型与刷新判据（详设）

> 承接总纲初稿深化；角色机器单一源 = `2026-09-12-invest-env` details/env-value-models.md §2.1（下称 env §2.1），本篇是它的第二消费位，禁二次建模。
> 实现者遇到本文未覆盖的语义选择 → 停手回任务书指认本文件提请修订，禁自行拍板（iteration-design 写作硬规则 2）。
> 依据标注约定：`cw_events.py:n` / `flow.py:n` 等 = 直调行号（2026-09-12 注册表态）；「直调」= 本详设写作时实跑注册表/代码取得的值；用户裁定 = README 裁定汇编（均为 2026-09-12）。
> 宪法对账：禁战力建模（00_framework §1.1）、数字三形态（01_math_framework §6）、位面零字面量（00_framework §1.2）、定序与基数分账。

## 问题与约束

### 边界

本篇辖：`decide_supply` 价值模型定稿（带钻层细分 / 角色层两态 / 装备层两态）、刷新判据数学、`_EQUIP_VALUE` 升格共享机器的落点与消费位迁移、组件缺口维度 v1 裁决、锁表、阶段划分、装备穿戴面 stash_comp 去留（已裁：移除，OQ-2 收口）。
不辖：装备合成的 P42 数值参数化（挂账，见 §4）、`decide_encounter` / `decide_planner` 的 target_comp 锚定语义（同辖域问题，开放问题 OQ-3）、补给 offer 分布的实采（挂账，见 §3.4）。

### 从总纲/env 承接的接口契约（不改口，只消费）

1. **角色候选机器**（env §2.1.3）：`candidate_char_universe(evicted) -> frozenset[str]`（∪ core∪shared over 非 evicted COMP_LIBRARY）；单角色档位判定（core/shared/transition/off 四档，遍历域与 evicted 过滤同源）落 `kernel/cw_comps.py` helper 区，**归属 env 侧机器**——env §2.1.3 的 `gift_hit_tier` 以单角色判定为底座，本篇要求该底座以可复用形态落地（`char_candidate_tier(char, evicted) -> str`，返回 `'core'|'shared'|'transition'|'off'`）；若 env 落地形态缺独立单角色 helper，由 env 侧扩底座，**本迭代禁复制第二套 COMP_LIBRARY 遍历**。
2. **过渡维机器**（README 裁定 7 指定单一源）：`cw_card_identity.line_identity_tier(name) -> str`（`TIER_REGISTRY_CORE`/`TIER_TRANSITION`/`TIER_UNRELATED`，cw_card_identity.py:96-112；其 transition 档 = TRANSITION_PACK 档 ∈ {carry, partial}，drop 档不入选）。
3. **锁线布尔与锚**（单源定谳）：锁线 ⇔ `ist.locked_comp` 非空（cw_deploy_logic.py:1548 引 ；17_stall_form_spend_authority §1.1）；锁定 comp 解析 = `get_comp(ist.locked_comp)`（flow.py:404 同款读法）；P1 配方锁帧 locked_comp 恒空（flow.py:405-410 注）→ 自然落入未锁分支。
4. **pick 族接线先例**（T-155）：flow `decide_invest` 从意向状态解析 `locked_comp/demoted_endgame/evicted` 传 kernel（flow.py:507-513），本篇 `decide_supply` 接线镜像同款；flow.py:495-497「supply/encounter 等 pick 族消费面不变」的括注随本迭代**过期**（supply 面改两态锚定），修正项入落地清单。
5. **失格/垫底语义**（gate-and-audit-spec §3 先例）：结构性无价值 = 落 0 垫底，非集合排除；本篇角色层全集外同款（off → 0）。
6. **执行模型不变式**：刷新 = 终结本轮、下轮重进重读（cw_screen_supply_node.py:21-25 申报）；整排重掷（advantage_layouts.md:18）；每节点免费 1 次（README 机制事实）。

### 现状接线盘点（2026-09-12 直调）

- 决策链全通：`read_supply_options`（obs/cw_node_obs.py:276-317，每列角色+装备 OCR、钻双通道 SIFT+文本、动态列数）→ op `CwScreenSupplyNode._do_action`（cw_screen_supply_node.py:310-406）→ `match.strategy.decide_supply` → flow 包装（flow.py:535-539）→ kernel `decide_supply`（cw_events.py:676-709）。
- kernel 三分支现行：带钻选钻 / 无钻无条件刷新找钻 / key_equips +10 与 `_EQUIP_VALUE`（cw_events.py:676-709）。
- `_EQUIP_VALUE` 消费位全量：①`decide_supply` 评分（cw_events.py:702）；②`decide_planner` 装备档回落（cw_events.py:831）；③sim 供给采样池名集（engine_p1.py:2838-2844）；④sim 审计两检查（sim/checks/ledger.py:1540、:1606，跨模块 import 私有符号——升格后消除）。
- 装备域既有第二套估值：`MATERIAL_VALUE_TABLE`（合成材料通用性，cw_prep_expect.py:32-40，喂 decide_box_card ②）；`decide_box_card` 打分 = key +100 / 材料通用性 / key 材料两跳 +30（flow.py:658-694）；装备穿戴 `cw_screen_equip_pick` = key_equips 子串 +100（target_comp+stash_comp）/ 泛用关键词 +1（cw_screen_equip_pick.py:137-159）。
- 刷新旗标缺陷：`_supply_refresh_used` 为 session 级布尔、置 True 后**无任何复位点**（全仓仅两处写 True：cw_screen_supply_node.py:349、engine_p1.py:2896）——多补给节点局（「人身意外险」类加补给阶段，op docstring :4-6 自证存在）后续节点刷新被吞，违反每节点 1 次机制。

## 方案

### 1. 三层价值模型定稿

决策序：**带钻分支（结构性先行）→ 非 dot 带宽值比较（角色维 + 装备维加性）**。同一选项价值 = 角色档分 + 装备分；argmax 取整选项（bundle：角色+装备一并取得——打捞人才库类效果原文，总纲 §1.1 gap 1）。

#### 1.1 带钻层（裁定 1，分支先行）

带钻选项直接胜出（先于一切分值比较）；**分支内部细分**：

| 档 | 判据 | 排序依据 |
|---|---|---|
| 财富宝钻 | `equip == '财富宝钻'` | ①效果本体 = 团队规模上限+1（结构量，01_math_framework §3.3 ΔV_pop 同族的合法人口增量）+ 每 3 备战阶段 1 金（效果原文【注】，cw_equipment_data.py:53）；②合成账 = 宝钻是 2 钻的合成产物（recipes 三路全为双钻：蓝蓝/红红/红蓝，【注】同 :53）→ 材料当量 2 钻 + 自身穿戴效果 ⟹ 严格高于任一单钻。【推·注册表】 |
| 红钻/蓝钻 | `equip ∈ {'红钻','蓝钻'}` | 同档并列：红=阵营星徽材料、蓝=流派星徽材料（效果原文【注】，cw_equipment_data.py:64-65）；星徽配方两侧对称（各 9 条，含欢愉双材料，【注·直调】:111-131）→ 无推导序。零新常数，并列时 argmax 取先。【注】plaza 方向注记（蓝钻×31 > 红钻×17，plaza_meta.md:65）不入判据——帖级统计 + 幸存者偏差（plaza_meta.md:87 自注）。 |

- 同排多钻：宝钻 > 任意单钻；多宝钻/多单钻取先（列序）。
- **辖域声明（裁定 1）**：带钻分支不比较该选项的角色维——用户裁定「带钻仍优先选」的整机辖域；角色价值随 bundle 一并取得，作为上行注记不入比较。若未来裁定改口，此处是唯一改点。
- 带钻分支同时是**跳刷判据的输入**（§2），两处消费同一 `has_diamond` + 钻名细分读数。

#### 1.2 角色层（两态，裁定 3/7）

**相位判定**：锁线 ⇔ `locked_comp` 非空且 `get_comp` 可解析（契约 3）；否则未锁态。

**未锁态（P1 为主；裁定 7 相位感知）**——单角色价值取两台机器的档位并：

```
char_tier(c) = max( env_machine: char_candidate_tier(c, evicted),   # 终局候选维（core/shared/transition/off）
                    identity_machine: line_identity_tier(c) 映射 )  # 过渡维（registry_core/transition_component/unrelated）
```

档序与分值（定序实现常数族，锚点推导内建位次、禁读基数——/ env §2.1.2 GIFT_FLOOR 先例）：

| 档 | 常数 | 值 | 锚点推导 |
|---|---|---|---|
| 候选 comp core | `CHAR_TIER_COMP_CORE` | 40 | > SHARED + 装备域极值 16（锁定态 key_fit 10 + 通用 6，§1.3）→ core 角色严格压过「shared 角色 + 满配装备」组合（裁定 3「角色 > 装备质量」的强形态） |
| 候选 comp shared | `CHAR_TIER_COMP_SHARED` | 20 | > 装备域极值 16 → 目标阵容结构成员压过任何纯装备选项（裁定 3）；< CORE − 16 |
| registry_core（③恒买类） | `CHAR_TIER_REG_CORE` | 12 | > 通用装备上界 6（全游戏持有类 > 单件通用装备）∧ < SHARED − 6 ∧ > transition 恒成立（序承总纲初稿「registry_core > transition_component > unrelated」） |
| 过渡件 | `CHAR_TIER_TRANSITION_BASE=9` × w_P1 | (0, 9] | 邻档带 (6, 12) 内取位：全窗高于通用装备上界、低于 registry_core；有效值随服务窗衰减（下式） |
| 全集外/未知名/OCR 空 | — | 0 | off → 0 垫底（契约 5）；OCR 空名保守落 0（漏放不错杀，gate spec §5 缺键语义同款） |

**P1 剩余时长衰减（定量形式）**：

```
w_P1 = (PLANE_NODE_COUNT[1] − round_num_of(bs)) / PLANE_NODE_COUNT[1]
       若 plane_of(bs) == 1；否则 0
PLANE_NODE_COUNT = {1: 9, 2: 9, 3: 9}  【注·节点表：node_ordinal_of =
    (plane-1)*9 + round（cw_board_state.py:201-204）+ economy.md §10.2 P1 = 9 节点（r5 = supply）】
```

- **位面合宪形态（00_framework §1.2 / 01_math_framework §8.1）**：位面只以节点数表查表键入场（PLANE_NODE_COUNT）；`plane == 1` 条件是过渡域的**相位谓词**而非机制辖域门——过渡包本身就是 P1 构造（TRANSITION_PACK 服务 P1、P2 交接弃置，cw_transition.py 模块头），且「Early 期判定 (plane1 + 未定型) 由消费方内联声明」是 后的既定内联形态（cw_transition.py 模块头原文）——本式沿用该既定形态，未新立按位面枚举的模块辖域。
- 线性形状 = 服务窗长度的恒等形（过渡成员的剩余兑现机会 ∝ 剩余 P1 节点数），**线性是推导基线**；任何非线性形状需额外推导，无则不取（禁拍形状）。
- w_P1 为【推】（【注】坐标恒等式 + 声明的恒等形状），无拟合参数、无 CI 义务。
- 平面 ≥ 2 时 w_P1 = 0：过渡包服务 P1（cw_transition.py 模块头语义），P2 未锁帧无过渡分可给——与裁定 7「锁线后收敛」方向一致。
- 量纲自检（r5 补给节点，w=4/9）：过渡件有效值 4.0 < 通用装备上界 6 ——过渡角色需自带不差的装备或处早 P1（r1: 8.0 > 6 全窗碾压）才胜出纯装备选项；此即「随 P1 剩余时长衰减」的可检行为形态（锁 S7 钉住）。

**已锁态（裁定 7 收敛）**：仅锁定 comp 成员计分——`c ∈ locked_comp.core_chars` → 40；`∈ shared_chars` → 20；其余（含其他候选线成员、registry_core、过渡件）→ 0。理由：方向已定，非本线成员的 optionality 价值消失（总纲初稿「core 命中提权、shared 次之、全集外 0」）。

#### 1.3 装备层两态（裁定 5/6）

**共享机器升格（未锁态主载体 + 已锁态通用底座）**：

- **落点选型：新模块 `kernel/cw_equip_value.py`**。理由：①消费位横跨 kernel（supply/planner）/strategies（box）/operations（equip_pick）/sim（engine_p1 采样池 + ledger 审计），需独立于任何单一消费面的公共落点；`cw_prep_expect` 的模块界 = 备战期望态对账（其 docstring :1-9），混入决策期通用价值会破其边界；`cw_equipment_data`（data 层）只放注册表真值不放决策价值。②sim/checks 现跨模块 import 私有符号 `_EQUIP_VALUE`（ledger.py:1540/:1606）——升格同时消除该坏味。
- **内容三件**：
  1. `EQUIP_GENERIC_VALUE: dict[str, int]` —— 现 `_EQUIP_VALUE` **逐值平移**（cw_events.py:604-642，值零变化； 审计注释随迁；键 ⊆ EQUIPMENT_ROSTER 断言保持 判据）。值不再重推：对位锚法产出的现表是已过审计的单一源，重拍 = 违禁拍值。
  2. `equip_material_generality(name) -> int` —— **注册表化**：合成材料通用性 = 全 EQUIPMENTS 配方引用**条数**（【注·注册表派生】），替换 `MATERIAL_VALUE_TABLE` 手表（cw_prep_expect.py:32-40 自注「v1:进阶配方引用数」）。**修订指针（armory-box-value 定稿）**：实跑证实注册表无梯度（简易 8 件各 10 条完全同值）与 V2 原文互斥（手表出处文档已删）——V2 改独立构造对拍 + 形态快照；`material_value` 薄委托**暂缓**，保持手表本体至该迭代 3.2 随打分器整体退役消灭。
  3. `key_fit_names(key_equips) -> frozenset[str]` —— 契合全集 = key_equips 成品 ∪ 各成品 recipes 全部材料（两跳，【注·注册表】cw_equipment_data.recipes）；单一源供三个消费位（supply +10/+3、box +100/+30、equip_pick 子串集）。
- **未锁态（裁定 5）**：装备分 = `equip_generic_value(equip)`，**无任何阵容绑定项**——现行 key_equips +10 消费 `target_comp` 伪 comp（P1 配方对物化，T-155 同款辖域错位，flow.py:405-410 自证）随两态化**移除**。行为变化锚点 = 锁 S8。
- **已锁态**：`key_fit_names(locked_comp.key_equips)` 契合——成品命中 +10（现行 +10 语义保留，总纲初稿 §2.1-3）；成品 recipes 材料命中 +3（**组件缺口维度 v1 结构版**，§4）；+10/+3 比例承袭 decide_box_card 现行 100:30 结构（flow.py:662-664，对位锚非新拍值）。装备分 = 通用值 + 契合项（成品与材料不叠加，成品优先）。

**消费位迁移清单（禁第二套）**：

| 消费位 | 迁移内容 | 锚定变化 |
|---|---|---|
| `decide_supply`（cw_events） | 通用值 + key_fit_names 消费 | target_comp 伪 comp → 两态（未锁=无绑定项；已锁=locked_comp.key_equips） |
| `decide_box_card`（flow.py:658） | ①③ 消费 key_fit_names；② 消费 equip_material_generality | 同上两态：未锁 = 仅材料通用性 + 通用值（裁定 5 同构，现行 ①③ 伪 comp 项移除）；已锁 = +key/+30 两跳 |
| 装备穿戴 `cw_screen_equip_pick`（:137） | 泛用关键词 +1 不变；未锁态无任何绑定项，已锁态 key 子串集消费 key_fit_names(locked) | target_comp 与 **stash_comp 均移除**（用户裁定 2026-09-12 严格版裁定 5：未锁态装备选择不绑囤牌方向）——未锁态装备分 = 纯通用值；已锁态 = key_fit_names(locked) 命中 |
| `decide_planner`（cw_events.py:831） | `_equip_value` 改 import 共享机器（符号重接，行为零变化）；其 target_comp 锚不入本迭代（OQ-3） | 不变 |
| sim `engine_p1`（:2838） | `_EV` 改 import 共享机器表 | 不变（采样池语义不变） |
| sim `ledger`（:1540/:1606） | 两检查改 import 共享机器符号（判据语义不变） | 不变 |

#### 1.4 评分总装（kernel 定稿形态）

**签名**（kernel 侧；strategy 契约面签名不变，wrapper 内部解析——op 调用点零改动）：

```python
def decide_supply(options: list[SupplyOption], bs: BoardState, *,
                  locked_comp: str = '', evicted: frozenset[str] = frozenset(),
                  refresh_used: bool = False) -> SupplyPick
```

- flow 包装（flow.py:535-539 重写）：`_ist = self._ensure_intention(state_of(session))` 后传 `locked_comp=_ist.locked_comp, evicted=frozenset(_ist.evicted)`（decide_invest 先例 flow.py:507-513）；`config` 参数从 kernel 签名移除（现行未消费）。sim 调用点（engine_p1.py:2893/:2898）同步改参。
- 决策序（完整）：

```
0. options 空 → idx=0, reason='no-options'（现行不变，op 侧 CARD_BODY 兜底承接）
1. 任一 has_diamond → 选宝钻列，否则首钻列；同时命中「带钻→跳刷」（§2）
   reason='diamond-treasure' | 'diamond'
2. 未刷（refresh_used=False 且节点戳非本节点）→ refresh=True（无条件先刷，§2）
   reason='refresh-then-pick'
3. 已刷 → 两态评分 argmax：
   score(o) = char_score(o.char) + equip_score(o.equip)
   reason 按胜出维度主项 = 'char-comp-core' | 'char-comp-shared' | 'char-reg-core'
        | 'char-transition(w=…)' | 'equip-key-fit' | 'equip-key-material' | 'equip-generic'
   归因串仅观测（op 日志面），不进检查器白名单（C1→D4 口径）
```

- fail-closed 面：`locked_comp` 非空但 `get_comp` 解析失败（注册表漂移）→ 按未锁态评分 + 日志哨兵（保守向：漏提权非错提权）；char 空/未知 → 0；w_P1 计算所需的 plane/round 读数缺省帧（NodeKey 缺省 (1,1)）在补给节点实际不可达（补给居位面中段，前置备战腿已立节点账，cw_board_state §3.4.1）——如实声明，不做额外防。

### 2. 刷新判据数学（裁定 2/4；整排重掷 + 每节点免费 1 次）

**结构式**：设当前 offer 最优 `M = max_i V(o_i)`；重掷 offer 独立同分布，重掷期望最优 `E[M'] = E[max_i V(o'_i)]`。判据 = 刷 ⇔ `E[M'] > M`。

**可闭合子式（带钻 → 跳刷，严格支配）**【推】：带钻时 `M ≥ V_diamond`，且 `E[M'] = P(D)·E[M'|D] + (1−P(D))·E[M'|¬D] ≤ P(D)·V_diamond + (1−P(D))·V_sub_top < V_diamond ≤ M` 对一切 `P(D) < 1` 成立——两前提均零分布依赖：①钻为严格顶层（§1.1 推导）；②`P(D) < 1` 必然（offer 非全钻分布，实机对拍 27/31 帧零钻，obs/cw_node_obs.py:246-248 直调在案）。∴ **带钻 → 跳刷是唯一数学可证的刷新例外，零分布参数**。

**一般式不可闭合（如实 fail-closed）**：`E[M']` 依赖补给 offer 分布（槽位物品率/角色池率/钻率）——无注册表（cw_equipment_data 只有效果/配方无出现率）、无 plaza 供给面统计（plaza_meta 为帖级终局构成）→【拟】无 CI → 不入任何数值闸（公理 1；01_math_framework §6 三要素）。

**默认起步形态 = 无条件先刷：成立，依据 = 用户权威 + 结构侧证**：
- 裁定 4 原文「有高优先级选项也不立刻锁——先用免费刷新看新 offer 再终局选择」为 playstyle 先验，**最高权威**；数学上它**不是**弱占优定理（对非钻 offer，M 与 E[M'] 同档竞争无支配关系——当前 offer 只是一次普通抽样，观测到的 M 约半数情形高于 E[M']），本设计如实声明其为用户先验而非推导结论。
- 结构侧证：先刷成本为 0；非钻档内 M 与 E[M'] 的差无分布可判 ⇒ 不存在「反证先刷劣」的推导，故用户先验无数学障碍。
- **「候选核心角色在场跳刷」不采纳为 v1 规则**：判定需 `P(核心角色 ∈ 单次 offer)`，推导不闭合，采纳 = 拍分布（违公理 1）。挂 sim/实采钩子：offer 分布标定后按结构式重裁（§3.4）。
- 边界汇总：**跳刷例外有且仅有「带钻」**；其余一律先刷。

**执行模型（现行保留 + 一处修正）**：刷新 = 终结本轮、下轮重进重读（契约 6）；修正 = `_supply_refresh_used: bool` 升格为 **`_supply_refresh_node: tuple[int, int] | None`**（ExecState 新字段，值 = 刷新发生节点的 `(plane_of, round_num_of)`，写入点 = op 刷新分支与 sim 刷新分支；刷新允许 ⇔ `_supply_refresh_node != (plane_of(bs), round_num_of(bs))`）——修复 session 级布尔吞掉多补给节点后续节点免费刷新的缺陷（盘点节「刷新旗标缺陷」）；旧布尔字段随本批删除（无第二消费方，全仓仅两处写点已盘点）；文本锚读缺 → 零点击 + 照常落当前节点戳（现行失败安全语义平移，cw_screen_supply_node.py:351-358）。

### 3. 参数源与挂账登记

| 量 | 形态 | 状态 |
|---|---|---|
| PLANE_NODE_COUNT=9/位面、plane/round 坐标 | 【注】节点表 | 可消费 |
| 钻效果/配方、星徽配方对称、装备 recipes | 【注】注册表 | 可消费 |
| w_P1、档位序、+10/+3 比例 | 【推】恒等式/对位锚 | 可消费 |
| 档位常数 40/20/12/9 | 定序实现常数（族） | 位次载体，锁表冻结；禁读基数 |
| 补给 offer 分布（物品/角色/钻率；「钻石闪耀」词缀抬升） | 【拟】无数据 | **挂账**：实采源 = op 已逐帧 log 识别选项清单（cw_screen_supply_node.py:377-378）+ chosen_supply 遥测行聚合；owner = 编排者；回炉时限 = 一个对局周期未决即回炉（01_math_framework §6 三要素 3）。消费位 = 刷新边界扩展（核心角色跳刷重裁）+ sim 带钻率 15% 粗估（engine_p1.py:2821）替换 |
| P42 hoard_gaps 数值参数化（V_comp 流期望 × 边际、近兑现距离 × partner 到位率） | 【拟】λ 未标定 | **挂账**（§4） |

### 4. 组件缺口维度（总纲待深化项 3）——v1 裁决：结构版入、数值化挂账

- **入 v1 的结构切片** = §1.3 已锁态「key_equip recipes 材料命中 +3」。理由：①纯注册表推导（recipes【注】），零新参数；②与 decide_box_card 现行两跳材料项同构（对位锚比例），消费同一 `key_fit_names` 单一源；③兑现 as-designed 规格「选项价值 vs 目标线组件需求」（13_pick_family.md:19）的知识判据半部。
- **挂账的数值半部** = P42 V_comp 参数化（近兑现距离 × partner 到位率的连续计分）。成熟度判据（P42_VALIDATION.md 直读）：P42 只站住序/支配级结论，绝对 EV 空转待 λ 标定（④门未检验、λ 🔴）；partner 到位率在册【拟】——数值化入闸双前置 = λ 标定批 + 补给时点 owned 装备读数接线（现行 op 无装备区读，仅到账登记粗粒度账）。owner = 编排者，时限同 §3 表。
- 未锁态**不入**组件契合（绑定项）——裁定 5 通用先验辖域；阵容无关的材料通用性已在共享机器（box 消费），supply 未锁态不消费它（最小忠实裁定 5，取舍见 §7）。

### 5. 锁表（`sr-od-test/test/sr_od/app/currency_war/test_cw_supply_pick.py` 新建；kernel 纯逻辑帧 + 模块头直调漂移锁）

**漂移锁（模块头，先行）**：

| 编号 | 断言 | 依据 |
|---|---|---|
| V1 | `EQUIP_GENERIC_VALUE` 键集 = 迁移前 `_EQUIP_VALUE` 键集（快照对拍）∧ ⊆ EQUIPMENT_ROSTER | §1.3 平移；|
| V2 | ~~`equip_material_generality(n)` == 旧 `MATERIAL_VALUE_TABLE[n]` ∀ 8 名~~ **已修订（armory-box-value）**：机器计数 vs 直查注册表独立构造逐名相等 + 形态快照（简易 8 名各 10 条/钻 11/垃圾袋 2/进阶 0；单位 = 配方引用条数）——原对拍与注册表真相互斥（手表梯度无据），实跑定谳见该迭代 design §1.1 gap 4 | §1.3 注册表化（修订版） |
| V3 | `key_fit_names(k)` ⊆ EQUIPMENT_ROSTER ∧ k ⊆ key_fit_names(k) ∀ k ∈ {任一 comp key_equips 抽样} | §1.3 |

**行为锁**（选项帧 = SupplyOption 列表；角色名/装备名用注册表实名，模块头断言其档位归属防漂移）：

| 编号 | 帧 | 断言 | 标注 | 依据 |
|---|---|---|---|---|
| S1 | {钻列, 候选 core 角色列}（未锁） | 选钻列，reason=diamond | 先行 | §1.1 裁定 1 |
| S2 | {财富宝钻列, 红钻列} | 选宝钻列 | 先行 | §1.1 细分 |
| S3 | {无钻帧} 未刷 | refresh=True，reason=refresh-then-pick | 先行 | §2 无条件先刷 |
| S4 | {带钻帧} 未刷 | refresh=False 且选钻（跳刷支配） | 先行 | §2 唯一例外 |
| S5 | 锁定态（locked_comp=实名套）：{key_equip 列, 通用 6 分列} | 选 key_equip 列（+10 压通用） | 先行 | §1.3 已锁 |
| S6 | 锁定态：{core 角色列(+垃圾装备), key_equip 列} | 选 core 角色列（40 > 16） | 先行 | §1.2 锁定档序 |
| S7 | 未锁态：P1 r5（bs.node=(1,5)）：{过渡件角色列(垃圾装备), 反重力皮靴列} | 选皮靴列（9×4/9=4 < 5）；同帧改 r2（w=7/9，过渡分 7）→ 过渡列胜（7 > 5）——衰减两侧 | 先行 | §1.2 衰减 |
| S8 | 未锁态 P1：{伪 comp key_equip 名列, 同值通用列} | 不再因契合胜出（现行 +10 行为移除锚点；两列同值时 idx 先者胜） | **先行·行为变化** | §1.3 裁定 5 |
| S9 | 未锁态：{候选 core 角色列, 通用 6 分列} | 选 core 角色列（40 > 6） | 先行 | §1.2 |
| S10 | `evicted`=全候选线：{原 core 角色列, 通用列} | 角色列落 0，选通用列（universe 收窄传导） | 先行 | 契约 1/5 |
| S11 | 锁定态：{key 材料(两跳)列, 同值通用列} | 选材料列（+3，reason=equip-key-material） | 先行 | §4 |
| S12 | sim 供给形态（char='' 全列） | 行为与现行 equip 分支逐位一致（sim 回归锚） | 先行 | §1.4 |
| S13 | 装备穿戴未锁态：{stash 方向 key_equip 列, 同值通用列} | 不再因 stash 契合胜出（+100 移除；与 S8 同族行为变化锚点） | **先行·行为变化** | §1.3 OQ-2 裁决 |

**回归面**：`test_cw_supply_options_dualrow.py`（obs 层不动，应全绿）；sim 供给路径冒烟（engine_p1 供给节点决策不炸）；`test_cw_*.py` 中 decide_box_card/equip_pick 相关帧（§1.3 迁移消费位行为等价/变化点各一帧）。

### 6. 落地阶段划分（供 landing.md 派生；依赖切分，非依赖阶段可先行）

| 阶段 | 范围 | 依赖 | 完成判据核心 |
|---|---|---|---|
| P-1 装备价值共享机器 | 新建 `kernel/cw_equip_value.py`（表平移/通用性注册表化/key_fit_names）+ §1.3 迁移表六消费位重接（本阶段行为等价：box/wear/supply 锚定不变，仅符号与数据源换） | 无 | V1/V2/V3 + 六消费位回归帧全绿（值零变化） |
| P-2 执行面卫生 | `_supply_refresh_used` → 节点戳（op + sim）；`flow.py:537` / `cw_strategy.py:173` 滞后 docstring 修正 | 无 | 多补给节点帧刷新可用锁（op 级测试）；现有供给 op 锁全绿 |
| P-3 补给决策两态化 | kernel `decide_supply` 重写（带钻细分/跳刷/先刷/装备两态/锁定锚/角色维占位 0）+ flow wrapper 接线（locked_comp/evicted）+ sim 改参 | P-1（共享机器 import）；**不依赖 env 迭代** | 锁 S1-S6、S8、S11、S12 |
| P-4 角色层接入 | char_candidate_tier（env 机器第二消费位）+ line_identity_tier 过渡维 + w_P1 衰减 + evicted 传递 | P-3 ∧ **env 迭代 §2.1 机器落地** | 锁 S7、S9、S10 |
| P-5 正本更新（固定末阶段） | strategy-docs/13_pick_family.md E4 行判据列重写 + :11 滞后标注清除；08_events.md E4 组件缺口状态（结构版落地/数值化挂账指针）；flow.py:497 括注过期修正 | P-1..P-4 | 正本与实现一致 |

正本更新清单：`strategy-docs/13_pick_family.md` §判据表 supply 行、§滞后标注 ← P-3/P-4；`strategy-docs/08_events.md` E4 节 ← P-3/P-4；`flow.py` docstring（:497 括注、:537）随 P-3 代码批内修，语义面归 P-5 核对。

### 7. 关键取舍

| 备选 | 为何放弃 |
|---|---|
| 带钻层不分档（宝钻=红钻=蓝钻） | 宝钻 = 2 钻合成产物 + 独立人口上限效果，严格序可证（§1.1），不区分 = 白丢免费信息 |
| 红/蓝钻分档 | 星徽配方对称（各 9 条），无推导序；plaza 方向注记受幸存者偏差不作判据（§1.1） |
| 带钻分支再比较角色维（宝钻列 vs core 角色列择优） | 裁定 1「带钻仍优先选」的明确辖域；改口唯一点已声明（§1.1） |
| 无条件先刷写成数学定理 | 对非钻 offer 无支配关系（M 与 E[M'] 同档），如实声明为用户先验 + 零成本侧证（§2）；写定理 = 伪造推导 |
| 候选核心角色在场跳刷 | 需 offer 分布，推导不闭合，采纳 = 拍分布；挂实采钩子（§2/§3） |
| 角色档用 transition_score 数值（cw_transition 现成 0-1.85 尺度） | 该尺度服务买牌框架选择（含框架加成/预囤语义），迁作补给档序需重锚且混两辖域；定序常数族 + 两机器档位消费更贴裁定 7 的「身份分档」语义 |
| 衰减用阈值门（剩余 ≥k 节点才给过渡分） | 阈值 k 无推导 = 拍值；线性恒等形零参数（§1.2） |
| 档位常数压到装备域内（如 core=8） | 破裁定 3「角色 > 装备质量」的强形态（角色可被满配装备组合翻越）；锚点推导要求档距 > 装备域极值 16 |
| 组件缺口 v1 全量参数化（P42 V_comp） | λ 未标定 + owned 读数缺位，双前置不在（§4，P42_VALIDATION 直读） |
| 装备机器落 cw_prep_expect / cw_equipment_data | 前者模块界 = 备战期望态对账；后者是 data 注册表层不放决策价值；跨四层消费需独立公共落点（§1.3） |
| `_EQUIP_VALUE` 值借 plaza 装备频次重标 | 频次→价值无推导（幸存者偏差帖级统计）；plaza 频次仅可作**覆盖缺口审计**输入（表外高频名 = 对位锚补值候选，归 P-1 后续审计批，不阻塞本迭代） |
| supply 未锁态消费材料通用性 | 裁定 5 = 「输出最需要」先验，通用性是囤料维不同族；box 消费不变（§4 取舍注） |
| wear 面 stash_comp 保留 | **已否（用户裁定 2026-09-12 OQ-2 裁决，严格版裁定 5）**：裁定 5 辖域覆盖装备穿戴面——未锁态装备选择不绑囤牌方向；囤牌方向的意图信号仍由买牌侧（意向层）消费，装备面不重复表达。行为变化锚点 = 锁 S13 |
