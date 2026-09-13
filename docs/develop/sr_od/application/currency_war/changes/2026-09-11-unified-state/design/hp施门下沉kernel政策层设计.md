# hp 施门下沉 kernel 政策层设计（详设）

> **文档定位**：本设计件 = W6 波 2（经济与血线门）的硬前置（依据 = 账本 T-5 交付报告
> `.debug/progress/2026-09-11-cw-clear-run/reports/T-5-r1.md` ③波次前置申报；波次范围
> 单一源 = 账本目录 `w6-切换波次调研草案.md` §3 波 2 行）。辖域 = hp 施门族从调用面
> 下沉 kernel 政策层的结构/语义/接口契约/数据流/边界/动机。字段级语义正本 =
> `docs/develop/sr_od/application/currency_war/game_state/fields.md`（§3.2.13 hp 门前
> 真值+消费侧施门；§2.1 Field 来源两态）；本文不复制正本内容，只定消费切换的落码契约。
> 数值/阈值只写常量名，单一源在代码。本件含波 2 落地卡 criteria 的「读口专项锁」输入
> （§4；挂账义务来源 = T-5 卡注：读口专项锁写进波 2 落地卡 criteria 防悬空）。
> **状态**：已定稿（设计对抗批 T-90 收敛；对抗记录 =
> `.debug/progress/2026-09-11-cw-clear-run/reports/T-90-r1.md`）。引用注：本文所引
> 「决策行 schema 终版」= 正本树 `design/决策行文件schema设计.md`。

## 0. 术语（首次出现给定义）

- **施门**：决策消费 hp 前对「门前真值」施加的政策修正。本文件辖两族：**结算新鲜度门**
  （结算屏真值在可信窗内覆盖现读，函数锚 = `gated_hp`，`strategies/impl/cw_strategy.py`）
  与**开局先验门**（开局无真值时按遥测实证先验写入，含词缀修正；载体 =
  `cw_opening_hp.opening_hp_prior` / `_AFFIX_HP_DELTA`）。
- **门前真值 / 门后消费值**：容器 `BoardState.hp` 存的是门前真值（记录面，不经门，
  fields.md §3.2.13）；门后消费值 = 施门后的决策输入，不入记录。
- **结算锚**：`StrategySession.last_hp` / `last_hp_t`（kernel/cw_strategy_session.py；
  唯一写点 = `cw_screen_battle_wait._write_settlement_observation`，置信门 =
  `HP_CONFIDENCE_THRESHOLD`）。门政策窗口 = 现读可信时限结算锚 gap==
  `HP_FRESH_GAP_TRUSTED` 可覆盖、现读不可信时放宽至 `HP_FRESH_GAP_UNTRUSTED_MAX`
  （两常量随波 2 落地批自 `gated_hp` 现行字面提取；语义依据 = `gated_hp` docstring
  r68/r69 实证记录）。
- **hp 可信位**：决策消费面「该 hp 值可否参与决策」的单一位，现役实现 =
  `cw_discipline_rules.hp_decision_trusted`（`hp_readable or hp_trusted`，W393 A1.1
  单一源）。容器侧读法定谳见 §2.2 定谳二。
- **kernel 政策层**：kernel 内承载跨消费域统一决策政策（准入/门/阈值读口）的模块层，
  先例 = `cw_launch_admission`（发射准入政策）。依赖方向纪律：策略实现层可依赖 kernel，
  kernel 禁反向依赖策略实现层（`cw_bs_view` hp 段在码申报）。
- **候裁位 / 定谳**：候裁位 = 设计中留给裁决的开放决策点；定谳 = 对候裁位作出的最终
  裁决（术语单一源 = 决策行 schema 终版 §0）。本件定谳两处（§2.2），依据就地标注。

## 1. 问题与约束

### 1.1 门族地图（现状全景与迁移处置）

| # | 门族 | 现居所 | 施门侧 | 波 2 处置 |
|---|---|---|---|---|
| 1 | 开局先验门（含「开局不利」词缀 −修正，常量 = `_AFFIX_HP_DELTA`） | `kernel/cw_opening_hp.py` + `cw_reconcile.reconcile_hp` 开局分支 | 写侧（先验写入，readable=False） | **不迁**（已在 kernel；本设计只定其读侧语义衔接，§2.2） |
| 2 | 下行拒信门（真读较沿用上行 ≥ 疑误读阈即留证拒信，常量锚 = `cw_reconcile` 模块常量） | `kernel/cw_reconcile.py` | 写侧对账 | **不迁**（写侧对账，非决策消费面） |
| 3 | hp_trusted 帧龄门（同节点沿用窗，，`_same_node_stale`） | `kernel/cw_reconcile.py` | 写侧对账 | **不迁**（同上；其消费语义由定谳二收编，§2.2） |
| 4 | **结算新鲜度门**（本设计下沉对象） | `strategies/impl/cw_strategy.gated_hp` | 消费读点显式施（现役 6 调用点，§2.4 迁移表） | **下沉 kernel 政策层** |
| 5 | 血线消费门（停升级线/急救分位/血预算停手；常量 = `emergency_hp` / `blood_budget_stop_d` / `vd_p1_loss_*` / `vd_p2_loss` 等） | `kernel/cw_economy.py` / `kernel/cw_discipline_rules.py`（血线常量载体 = `kernel/cw_registry.py` DecisionV2Registry 字段） | —（是门的**消费者**，非施门者） | 波 2 本体切换；其 hp 读点改经政策层读口（§2.4） |

依据：调用点清单 = `gated_hp` docstring 全仓 grep 口径（6 点）；血线消费面 =
`cw_discipline_rules.blood_budget_levelup_blocked` / `all_in_xp_domain_hit` /
`cw_economy.blood_xp_gate` / `is_emergency`（各函数 docstring 与签名）。
kernel 评估簇挂账 hp 读点另有两处（`cw_comps.maybe_pivot` 保命分位 /
`cw_performance.is_run_dead` 死局门，直读 `bs.hp.value`；生产调用面现空 = 挂账层，
测试仓经桥调用）——不占门族行，读法约束见 §2.4 迁移表挂账行与 §4-L2。

### 1.2 症状与根因归层

- **症状**：波 1 后 kernel 评估簇存在直读 `bs.hp.value`（门前真值）的读点（例 =
  `cw_comps.maybe_pivot` / `cw_performance.is_run_dead` hp 读点在码注释「门前真值，
  可信位门在决策侧」；两点现挂账层无生产调用，注释即旁路候补位的在码自申报）；
  波 2 的 kernel 决策函数
  （cw_economy / cw_discipline_rules）切容器签名后同样拿到门前真值，而门函数居策略
  实现层——kernel 不能反向 import 策略层（§0 依赖方向纪律），施门只能：漏门（不同门 =
  行为分叉，实证 = `gated_hp` docstring r68「先调方假 hp、后调方真 hp，同节点两次方向
  相反换线」）或每读点手写第二门实现（漂移温床，违反 W393 A1.1 单一源纪律）。
- **根因归层（流程层）**：施门点分散在调用面，靠纪律（」）
  维持一致性；门政策本体与消费读口未单点化。修法 = 门语义下沉 kernel 政策层、消费经
  单一读口——属流程层治本，非表示层换名。
- **归层依据**：调用点分散事实 = §1.1 表 #4 列；同门纪律同源；
  波 2 硬前置定位 = 调研草案 §5 风险 2「kernel 门居所未定……门放错层=消费拿到未施门
  真值，禁拆批」。

### 1.3 约束

1. 依赖方向：kernel 禁反向依赖策略实现层（`cw_bs_view` hp 段在码申报）；门输入全部
   kernel 类型（`BoardState.hp` Field / `NodeKey` / `StrategySession` 锚字段）。
2. 记录/消费分离（fields.md §3.2.13）：容器与 journal/遥测只记门前真值；门只辖决策
   内存消费面。决策行文件不发射 hp（决策行 schema 终版 §2.3 退役面判据），门不涉
   行载荷。
3. 波次边界：写侧 4 调用点属旧链（`cw_screen_prep` 环入口×2 + 终饰×2），随波 5
   last_state 链退役删除（调研草案 §3 波 5 行）；波 2 不动它们。
4. 数值零迁移：门政策窗口、置信门、先验值表全部沿用现行常量，本设计不改任何数值
   （常量名见 §0/§2.2；`gated_hp` docstring r68/r69 为政策语义的实证记录）。

### 1.4 明确不解决

- hp_max 字段缺位建模（fields.md §5.2 缺口登记在案，挂后续建模批）；
- 奋斗协议 hp 支付链的 hp 逻辑写端接线（fields.md §4 LevelUp 修饰行；接线归消费批，
  接线前 `hp` 无 logic 来源，§2.2 定谳二已预留该来源的门语义）；
- sim 内部真值模型改造（波 5 辖）；
- 旧链写侧预施门点的提前删除（波 5 辖，§1.3-3）。

## 2. 方案

### 2.1 结构：kernel 政策层模块（双层接口）

新建 `kernel/cw_hp_policy.py`，承载双层接口：

1. **门本体（纯函数层）**：`apply_hp_freshness_gate(current_hp, last_hp, last_t, now_t,
   current_readable) -> int | None`——显式参数、零 session/容器依赖，语义与现役
   `gated_hp` 逐位等价（窗口政策两常量 `HP_FRESH_GAP_TRUSTED` /
   `HP_FRESH_GAP_UNTRUSTED_MAX` 提取入本模块，§0）。
2. **决策读口（装配层）**：`decision_hp(bs, session) -> int | None`——门前真值取
   `bs.hp.value`、可信位取 `bs.hp.source`（§2.2 定谳二）、时基 t 自 `bs.node` 派生
   （`(plane−1)×9+round_num`；`NodeKey` 缺席 = t=None = 门恒等支，与现役
   `adapter.decision_state` t 派生同式）、结算锚自 session 鸭子读（`last_hp`/
   `last_hp_t`，kernel 内类型，无依赖环）后调门本体。
3. **可信位读口**：`hp_decision_trusted_of(bs) -> bool`（§2.2 定谳二单一实现）。

既有居所处置：`strategies/impl/cw_strategy.gated_hp` 改**薄委托**（函数体 = 一行调
`apply_hp_freshness_gate`，docstring 实调点清单同步标注下沉归宿）——其 6 个既有调用点
（写侧 4 + 消费侧 2）零改动续用，行为零变化；`kernel/cw_discipline_rules.
hp_decision_trusted` 随波 2 签名切换改委托 `hp_decision_trusted_of`（容器签名形态），
GameState 版随 W8 本体删除消亡（调研草案 §6 残留表）。

依据（落位选型）：新模块而非 `cw_state.py` 同居所——调研草案 §3 波 2 行提议「与
`DIFFICULTY_HP_TABLE` 同居所」，但该常量居 `cw_state.py`（旧 GameState 本体），该文件
挂 W8 切割删除（landing.md §3.4 / 调研草案 §6 残留表）；新门落将拆之屋 = 反治本，
故立新模块。模块命名对齐「政策层」先例 `cw_launch_admission`（§0）。

### 2.2 语义定谳（两候裁位，本件定谳）

**定谳一·门居所 = 下沉 kernel 政策层（方案 A），否注入槽（方案 B）**。论据：
①依赖方向干净——门输入全 kernel 类型（§1.3-1），注入槽唯一的存在理由（kernel 不可知
的策略私有行为）不成立；②单一源强制——kernel 消费簇与策略层消费点调同一读口，注入槽
在未装配态（裸调用/离线工具/单测）需另定义 fail 语义，多一个静默漂移面；③先例一致
——`hp_decision_trusted` 已按同纪律自策略层下沉 kernel（`cw_discipline_rules` 模块头
MAP ⓪ A3）。方案 B 对比详见 §3。

**定谳二·hp 可信位容器读法**（调研草案 §3 波 2 行 / §5 风险 1：容器无现成对应，禁猜，
本件定谳）：

- 容器 hp 写端全集与来源形态（依据 = 写点在码）：
  - 备战帧真读 → `observe`，`sig.quality['hp']='real_read'`，source=`observation`
    （`cw_observation._feed_board_state` hp 段）；
  - 开局先验 → `write_prior`，quality=`'prior'`（同上；先验语义 = 历史遥测调查先验,非本局亲见,载体 cw_opening_hp）；
  - 沿用 → `carry`，quality=`'same_node_carried'`（同上；同节点窗）；
  - 结算覆盖 → `apply_settlement_cover` observe（source=`observation`，无 quality 标记，
    `kernel/cw_board_state.py`）；
  - sim 合成 → `synthesize_from_game_state` observe（evidence 恒 `sim:synthesized`，
    「sim 恒真值帧」约定）。
- **定谳映射**（决策读口单一实现）：
  - 本帧真读位（现役 `hp_readable` 语义）≡ `bs.hp.source == 'observation'`；
  - **hp 决策可信位 ≡ `bs.hp.source in ('observation', 'carried')`**。
- 等价性论证：旧口径 `hp_readable or hp_trusted` 在容器来源二分下恒等于上式
  （observation ⊆ 两支并集；carried 支 = `hp_trusted=True` 沿用放行语义，`cw_state.py`
  hp_trusted 字段注释）；prior/logic 支两位皆 False = fail-closed（血线谓词
  唯一收口（None 保守）——映射保序。跨节点沿用帧旧位 False/新映射 True 的
  行为差已在 W5 视图收编时申报（`cw_bs_view` hp_trusted 映射段在码申报面），本定谳
  沿用不重裁。
- **quality 词表处置**：`sig.quality['hp']` 三值（`real_read`/`prior`/
  `same_node_carried`）保留为判读证据，**不参与决策位**；「同节点限定」的严格语义若
  未来需恢复，消费面按 quality 词表收窄即可，不新增容器字段（字段准入四问③：可从
  现有 sig 派生，fields.md §8.8）。词表封闭：新写端扩词表须随批登记申报
  （ChannelSig quality 纪律，cw_board_state.py 类 docstring）。
- **logic 来源预留**：现役 hp 无逻辑写端（`cw_bs_view` hp_trusted 映射段在码申报
  「现无 hp 写端」）；奋斗协议接线后 hp 出现 logic 来源，按映射两位皆 False（推算值
  非真读）——届时若需放行随批重推，本定谳不预放。

### 2.3 接口契约（实现者按此落码，零再设计）

```text
# kernel/cw_hp_policy.py（新建）
HP_FRESH_GAP_TRUSTED: int          # 值 = gated_hp 现行字面（现读可信窗）
HP_FRESH_GAP_UNTRUSTED_MAX: int    # 值 = gated_hp 现行字面（不可信放宽窗上界）

def apply_hp_freshness_gate(current_hp: int | None, last_hp: int | None,
                            last_t: int | None, now_t: int | None,
                            current_readable: bool) -> int | None:
    """结算新鲜度门本体。语义逐位等价 gated_hp：锚缺任一（last_hp/last_t/now_t
    为 None）→ 恒等返回 current_hp（None 现读恒等支穿透）；锚全时
    gap=now_t−last_t：可信窗（gap==1）与放宽窗（current_readable=False 且
    1<gap≤HP_FRESH_GAP_UNTRUSTED_MAX）→ 返回 last_hp，窗外返回 current_hp。
    None 现读非恒等豁免——锚全时在窗内同样被结算值覆盖（现役同型语义：门只
    决定「是否被结算值覆盖」，不产兜底值）。门幂等：门后值再过门不变。
    时基契约：now_t/last_t 同式派生（(plane−1)×9+round_num），结算锚写点
    （cw_screen_battle_wait._write_settlement_observation）与决策读口禁单侧
    改式。NodeKey 缺席 → now_t=None=恒等支；与现役 adapter 形态（缺省
    plane/round=1 → t=1）在锚在场时 gap≤0 判负同回 current_hp，行为等价。"""

def decision_hp(bs: BoardState, session: StrategySession) -> int | None:
    """决策面 hp 读口（门后消费值）。装配序：门前真值 = bs.hp.value；
    current_readable = (bs.hp.source == 'observation')；now_t 自 bs.node 派生
    （NodeKey 缺席 → None）；last_hp/last_t = session 结算锚（鸭子属性读，
    缺席 = None → 门恒等支）。"""

def hp_decision_trusted_of(bs: BoardState) -> bool:
    """hp 决策可信位容器版单一实现 = (bs.hp.source in ('observation','carried'))
    （定谳二）。"""
```

- `strategies/impl/cw_strategy.gated_hp`：函数签名与调用面不变，函数体改薄委托
  `apply_hp_freshness_gate`；docstring 标注本体归宿与新调用点申报纪律。
- `kernel/cw_discipline_rules.hp_decision_trusted`：波 2 签名切换后容器形态 =
  委托 `hp_decision_trusted_of`；消费点（`blood_budget_levelup_blocked` /
  `all_in_xp_domain_hit`）照旧调本名，禁手写双位判定。
- `kernel/cw_economy`：波 2 切换后 hp 决策消费点（`blood_xp_gate` 调用包装 /
  `is_emergency` / 攒息门急救分位读点）改经 `decision_hp`；**缺 session 形参的消费
  函数（`is_emergency` 族）随波 2 签名切换补 session 形参**（调用方 = kernel 内部
  与策略装配，均持 session；依据 = 现役 `blood_budget_levelup_blocked(state, session,
  registry)` 同形态），禁函数内私有第二门。
- 消费同门申报纪律（承接）：波 2 后新增 hp 决策消费点，要么经
  `decision_hp` / 上游门后值传递，要么在豁免清单登记（豁免判据见 §2.5）。

### 2.4 数据流与迁移点表

**写侧（波 2 零改动）**：备战帧观察漏斗（`reconcile_hp` → bs.hp 三态写入，§2.2 写端
表）与结算链（`_write_settlement_observation` 写结算锚 + `apply_settlement_cover`
覆盖 bs.hp，同分支同序）不变；开局先验分支不变。

**读侧迁移点表**（波 2 范围 = 前两行；后两行为衔接申报）：

| 调用点 | 现态 | 波 2 后 | 终态（波 4/5） |
|---|---|---|---|
| kernel 消费簇（cw_economy / cw_discipline_rules 的 hp/可信位读点） | 决策帧门后值（上游 adapter 施门间接保证） | **改经政策层读口**（§2.3） | 同左 |
| 策略消费侧 2 点（`adapter.decision_state` / `encounter._hp_gate_state`） | 调 `strategies gated_hp`（薄委托） | 零改动（薄委托行为等价） | 波 4 随 strategies 全簇切 `decision_hp`（跨件接口：波 4 商店/备战链 hp 消费同源） |
| 写侧 4 点（`cw_screen_prep` 环入口×2+终饰×2） | 调 `strategies gated_hp`（帧值显式施门，旧链） | 零改动（薄委托） | 波 5 随旧链删除 |
| sim | 无结算锚 → 门恒等支（engine_p1 不写 `last_hp`，grep 口径） | 不变 | 波 5 真值直写后同构 |
| kernel 评估簇挂账 hp 读点（`cw_comps.maybe_pivot` / `cw_performance.is_run_dead`；生产调用面现空，测试仓经桥调用） | 直读 `bs.hp.value`；maybe_pivot 经 `_HpShim` 手抄镜像字段喂 `effective_hp_threshold`（GameState 签名） | `_HpShim` 消亡（阈值函数随波 2 切容器签名，§2.4 shim 收编申报）；hp 直读约束照旧——**重挂生产消费必经政策层读口** | 波 4 批首 grep 复核 kernel 决策簇 hp 直读点全集——新增消费点一律走 `decision_hp`/`hp_decision_trusted_of` 或登记豁免（§4-L2 申报面） |

依据：调用点清单 = `gated_hp` docstring grep 口径；波次归属 = 调研草案 §3 波 2/波 4/
波 5 行；策略消费侧波 4 全集以落地批批首 grep 复核为准（调研草案 §4 决策热点列在册
hp 读点含 entry 3 处，随 strategies 全簇切换一并走 `decision_hp`）；波 2 文件面较
调研草案行增 3 面（`kernel/cw_hp_policy.py` 新建、`strategies/impl/cw_strategy.py`
薄委托改写、`kernel/cw_state.py` 的 `effective_hp_threshold` 单函数容器签名切换，
见下段 shim 收编申报）——**波 2 落地卡文件面以本表为准**。

**过渡期鸭子 shim 散点收编申报**（跨波排期，禁留无消亡日的 shim）：现树 kernel 内
两处手抄镜像字段清单的鸭子 shim（`cw_comps.maybe_pivot` 内 `_HpShim` 喂
`effective_hp_threshold`；`cw_recipe.decision_target` 内 `_PlaneShim(plane=…)` 喂
`committed_from`），均为「容器已切签名消费面 → 未切换签名的被喂函数」的过渡桥接：
①`effective_hp_threshold`（cw_state，GameState 签名）随**波 2** 切容器签名（输入
字段 selected_difficulty/plane/round_num/level/board 波 1 全就绪；hp 阈值域与政策层
同批收编）——`_HpShim` 即消亡，maybe_pivot 改直传 bs；②`committed_from` /
`committed_authority` 的 state 参数切 BoardState 挂**波 3**（cw_intention 切换面）——
连带消费点 `cw_recipe.decision_target` 的 `_PlaneShim` 同波消亡（现态单字段喂入恰
等价：committed_authority 仅读 state.plane，cw_intention:2348；被喂函数多读字段即
喂不足成静默劣化面，波 3 立卡时 cw_recipe 该调用点列入批首 grep 复核清单）。两 shim
消亡前禁新增同型鸭子桥——新消费点一律直接按容器形态调用。

### 2.5 边界

1. **门辖域**：只辖决策内存消费面。豁免清单（不经门的合法直读）= 记录面（journal
   快照/遥测 recorder/局终写口 `write_match_final` 的 hp 参数）+ 写侧对账面
   （`reconcile_hp`）+ 投影过渡桥（`board_state_bridge` 搬运，见 4）。
2. **幂等与组合**：门幂等（同 gap 窗内重复施门值不变），读口可在装配层与消费层
   叠加施门而不判分叉；幂等性由 §4-L1 锁钉。
3. **None 语义**：门不产兜底值；`bs.hp.value is None`（未读过）穿门为 None，消费面
   按 保守（血线条件不触发/授权位 fail-closed）。
4. **过渡桥失真申报**：`board_state_bridge` / `synthesize_from_game_state` 产出的
   BoardState 视图上 hp source 恒 `observation`（合成口写死，`synthesize_from_game_state`
   在码）——可信位读法在该视图上恒 True，**语义只在生产容器单例上成立**。过渡期
   （波 2-4）行为仍一致：桥输入帧的 hp 已被上游施门（幂等保证重复施门无差）、None
   帧不写桥字段（未知态穿透）。波 4 黑板容器化后跨桶直读 session 容器，失真窗关闭
   （`board_state_bridge` docstring 退役条款）。
5. **依赖方向**：政策层模块仅 import kernel 内类型；禁 import `strategies/`（§1.3-1）。
6. **正本对账申报**：fields.md §3.2.13/§8.6 现行声明 hp 可信位语义单一源 =
   `cw_bs_view`（W5 收编口径）；本件定谳二与 §2.1 读口落地后，语义单一源改指
   `hp_decision_trusted_of` / `decision_hp`——fields.md 两节随波 2 落地改指（挂
   landing.md 正本更新清单随批消费）。过渡窗内字段记录语义（门前真值 + 写端全集）
   不变，本件只迁消费读口，非正本语义改写。

## 3. 关键取舍

- **下沉 kernel 政策层（选）vs 注入槽（弃）**：注入槽形态 = kernel 留
  `set_hp_gate(fn)` 装配槽（先例 = `set_obs_reset_hook`），策略层在 app 装配时注入门
  函数。弃因：①门本体不依赖任何策略私有状态，注入只引入「未注入态语义」这个新决策
  （identity？fail-fast？）——两案都有静默漂移窗（漏注入 = 全链无门）；②消费同门
  从「编译期可查（import 单一读口）」退化为「装配期可查（运行时槽状态）」，验收锁
  只能做运行时断言；③与 `hp_decision_trusted` 下沉先例同纪律更一致。注入槽的合法域
  = kernel 不可知的策略私有行为（如 obs 缓存清理回调），门不属之。
- **薄委托 vs 直改全部调用点（选薄委托）**：直改 = 波 2 一次改 6 调用点 import 与
  装配，其中写侧 4 点属旧链（波 5 删）——为将死代码改两遍；薄委托 = 策略层符号保留、
  本体单点、波 4/5 各自切各自删，改动面最小且每波可独立验收。
- **新模块 vs `DIFFICULTY_HP_TABLE` 同居所（选新模块）**：见 §2.1 依据段——
  同居所目标文件挂 W8 切割，新门不落将拆之屋。

## 4. 锁面（波 2 落地卡 criteria 输入：读口专项锁）

> 本节 = 调研草案 §3 波 2 行锁族清单之外的**新增读口专项锁**（T-5 卡注挂账义务）；
> 波 2 落地卡 criteria 引用本节编号。格式对齐决策行 schema 终版 §10 先例。

| # | 锁 | 断格内容 |
|---|---|---|
| L1 | 门语义等价锁 | `apply_hp_freshness_gate` vs 旧 `gated_hp`：同输入序逐位等价；夹具覆盖 gap∈{0,1,2,3,4}×current_readable×锚缺席组合 + 幂等断言（门后值再过门不变）+ None 穿透断言 |
| L2 | 决策消费同门锁 | 波 2 后 kernel 决策簇全模块 grep（cw_economy / cw_discipline_rules 全量 + §2.4 挂账读点申报位）：`bs.hp.value`（或 `.hp` 字段直读）仅出现在政策层读口内部与 §2.5 豁免清单/§2.4 挂账申报位；决策分支零旁路直读 |
| L3 | 可信位单一源锁 | ①`hp_decision_trusted_of` 唯一实现（`hp_decision_trusted` 容器形态委托之）；②容器消费面 `hp_readable or hp_trusted` 手写双位模式 grep=0；③`sig.quality['hp']` 词表封闭断言（三值全集，外来值抛错/留证） |
| L4 | 薄委托零漂移锁 | `strategies/impl gated_hp` 任意输入委托输出 == kernel 门本体输出（防委托层再长肉）；写侧 4 调用点既有门行为锁（test_cw_strategy_helpers 族）续辖零改 |

> 锁生命周期：L1/L4 的等价参照旧 `gated_hp` 随波 5 消亡——波 5 后两锁改钉
> `decision_hp` 单一形态（件② M1「波 5 收敛后改钉单形态」同手法）；L4 内写侧 4
> 调用点行为锁随波 5 旧链删除退役。
