# 动作逻辑态（action-logic-state）

> **逐动作计算规则分篇见 [logic-updates/](logic-updates/README.md)**（每动作 op 一篇：域集/转移规则/随机面/拒绝语义/符号锚/语义验证（M1 直锁）/判例）；本篇保留总则与原则。
> 定位：货币战争主链**每个动作 op 的逻辑态计算规则全集**（地基文档）。动作 op 机械发出后，不经任何画面观察，按游戏规则从动作前状态推算出预期状态并直写容器——这份推算规则的确定性全集就是本篇。真值永远以下一帧画面观察为准。
> 用户裁定：不许以「逻辑态未建模」为由把动作交回外循环——在役动作全集逐个有逻辑态；除 §5 两类转移动作显式声明「逻辑态=空」、§6 声明的事件选择边界外，本篇不存在「无逻辑态」的动作。
> 机制事实依据 = `docs/game/currency_war/research/`（merge_mechanics / xp-rules / economy / equipment_mechanics / screen_flow_timing）+ `docs/game/currency_war/data/gameplay.md`（官方原文）+ `../proofs/`（数学证明）。kernel 现位依据 = 符号锚 `文件::符号名`（路径根 = `src/sr_od/application/currency_war/`，行号不写，随代码漂移）。
> 读者 = 无会话历史的工程师/智能体。职责分界：「一次访问内怎么编排动作」= [action_exec.md](../flow/action_exec.md) / [prep.md](../screens/prep.md) / [shop.md](../screens/shop.md)；「每个字段怎么记」= [fields.md](fields.md)。与 fields.md 的分工：fields.md 按**字段**记写入面，本篇按**动作**记计算规则，同源互指。

## 1. 总则

### 1.1 逻辑态与两态制

**逻辑态**（本篇主题）= 一个动作 op 机械发出后，**不经观察**、只按已核实的游戏规则、从动作前容器状态**推算并直写**的预期状态。

**两态制** = 容器——局内状态唯一快照 `kernel/cw_game_state.py::GameState`（下称「容器」）——的每个字段只保留两种值来源：**观察态**（画面读数，`observe()` 写入）与**逻辑态**（动作后推算，`write_logic()` 写入）；同帧冲突时**观察赢**（观察值覆盖逻辑推算值）。依据：`fields.md` §2.3/§2.5；架构裁定锚 = ADR-0651。

一句话读法：逻辑态回答「这一下点完，容器**应该**变成什么样」；下一帧观察回答「实际变成了什么样」；两者不等 = 逻辑态模型缺陷，走缺陷台账（不静默、不改道）。

### 1.2 确定性原则：随机面不进逻辑态

动作后果一分为二：

- **确定面** = 规则上唯一可推算的部分：扣多少金、哪个槽位清空、谁升星、退多少金。逻辑态只写确定面。
- **随机面** = 游戏内部掷随机数的部分：刷新后的新牌面、冶金炉的变异产物、奖励球的掉落内容、掉落的金币数额。**随机面不进逻辑态，归下一帧观察。**

### 1.3 写口归属：op 上报动作，game state 独占写逻辑态（硬规则）

- **动作 op 的职责边界** = 执行画面动作（点击/拖拽）+ **向 game state 上报自己的动作事实**。逻辑态的更新写入由 game state 独占完成：商店域经 `apply_shop_action_logic`/`apply_shop_merge_leg`，备战域经 `apply_prep_action_logic`，效果账经 `apply_op_effect`（§1.4 表）。
- **禁令**：op 层/策略层不得自带逻辑态记账函数或并行登记路径——同一动作存在两条写逻辑态的通道是账实分离类缺陷的温床。执行遥测计数（次数/金额/证据留档）不属逻辑态,不受本条辖,但不得反向写容器。
- **逐动作计算规则的梳理文档** = [logic-updates/](logic-updates/README.md)（总-分结构：总览 + 每动作 op 一篇,说明该动作的逻辑态应如何计算）;本篇保留总则与原则,分篇逐节指向子目录。

这是**原则，不是缺口**：随机面上不存在任何可写的真值，替它编一个预期值只会制造假缺陷票。随机面对应的容器域在该动作轮按**域级跳写**纪律跳过（该域值留观察覆盖，与容器写口的输入域 None 语义同型，`kernel/cw_game_state.py::apply_shop_action_logic` 注）。

### 1.3 kernel 单一源指针纪律

- **规则已实现**：本篇只写语义 + 指向 kernel 函数（符号锚）；数值只写常量名，不复制数值（值的单一源在代码）。本篇被指对象：`kernel/cw_merge_simulate.py::merge_buy_k` / `merge_buy_completes` / `_merge_bench` / `_apply_full_bench_merge_buy` / `same_star_count`；`kernel/cw_economy.py::sell_refund` / `bench_char_cost` / `xp_apply_clicks` / `xp_click_cost` / `clicks_to_next_level` / `blood_xp_full_clicks`；`kernel/cw_game_state.py::apply_shop_action_logic` / `apply_shop_merge_leg` / `detect_merge_upgrade` / `apply_prep_action_logic`；`kernel/cw_vocab.py::mutate_bench_deployed`；`kernel/cw_exec_state.py::apply_op_effect`；`kernel/cw_affix_effects.py::apply_tool_execution_write`（及登记表 `EQUIP_WRITE_SIDES`）；`kernel/cw_effect_inventory.py::spawn_equip_bench_unit` / `grant_equip_item` / `transform_equip_to_privilege` / `transform_worn_equip_to_privilege`。
- **规则未实现**（无 kernel 落码写口）：**本篇该节即实现规格**——实现时按本节规则落码，不另立规格文档。
- 同一规则多载体若漂移，以 kernel 单一源为准修齐（`kernel/cw_merge_simulate.py` 模块头注）。

### 1.4 逻辑态的三个落点（载体）

同一套规则按宿主分落点落码；本篇按动作写规则一次，在役落点同规则消费（推演帧落点的写口已退役，见末行）：

| 落点 | 宿主 | 写口（符号锚） | 消费方 |
|---|---|---|---|
| 容器逻辑态直写 | `GameState` 字段（渠道 family='logic_action'） | `apply_shop_action_logic`（商店域转移函数）/ `apply_shop_merge_leg`（合成升星腿，既有口）/ `apply_prep_action_logic`（备战域，域集 = gold/bench/xp/level/front_row/back_row/board）/ `apply_op_effect`（备战金账与库存腿） | 单动作循环逐动作逻辑态直写；观察赢修正 |
| 执行态跟踪账 | `ExecState.tracked_bench_chars` / `tracked_deployed` 槽位表 | `mutate_bench_deployed` + 执行器 tracked 同步分支（`prep_actions.py::PrepActionExecutor._track_remove_bench` / `_track_remove_deployed` / `_track_move_deployed`） | 执行侧随动账;双账比对已退役（2026-09-15,对账唯一发生点 = 观察边界,见 screen_op §2.3/§4） |
| 推演帧 | sim 引擎 `CwSimFrame` 整帧副本 | 原写口 `simulate`（整帧副本单步动作应用器）已退役（零生产消费，考古归 git） | 动作转移语义单一源 = 容器逻辑态直写（首行）；语义验证 = M1 直锁（`test_cw_shop_projection_logic`） |

另有一个非容器落点：**备战观察帧**（`kernel/cw_prep_actions.py::PrepObservation`，宿主 `session.prep_obs_frame`）——球/箱/典籍/装备/工具等视觉域动作的逻辑态推进落在它上面（`operations/cw_screen/cw_screen_prep.py::_project_prep_obs`），容器零写（`apply_prep_action_logic` 对这些动作显式返回）。

### 1.5 枚举范围与动作计数

本篇枚举 = 商店域 6 个动作词条（§2）+ 备战域原子动作（§3：DeployMove/SellDeployed/LevelUp/OpenBox/OpenTome/ClickSpheres/OpenBookcard + §3A WearEquip 与工具原子类，规则见 §4）+ 转场类 2 个（§5）+ 词表完备性注 2 条（§2.7）。事件线选择（pick 族，含武装箱四选一画面 op）按 §6 声明为非逻辑态通道。动作词表本体与执行载体表 = [action_exec.md](../flow/action_exec.md) §1、[screens/README](../screens/README.md) §4（能力面/策略面之分不在本篇重复）。

各动作条目统一形状：**词表/op → 确定面规则（逐腿）→ 随机面 → 拒绝边界（游戏拒/提案陈旧 = 零容器写）→ 依据**。

## 2. 商店域动作

商店域动作的容器写口单一源 = `kernel/cw_game_state.py::apply_shop_action_logic`（逐域 `write_logic`，域集封闭 = `SHOP_PROJECTION_DOMAINS`：gold / bench / shop / xp / front_row / back_row / board / equips）；合成升星腿既有口 = `apply_shop_merge_leg`（先简单腿后整表覆盖，两写合计为商店动作投影语义单一源，直锁 M1（`test_cw_shop_projection_logic`））。商店域 op 载体 = `operations/cw_op/cw_<action>_action.py`（一 op 一文件）。

### 2.1 BuyCard（买牌）

op = `operations/cw_op/cw_buy_card_action.py::BuyCardOp`（非终结）。词表 = `kernel/cw_vocab.py::BuyCard`。

**确定面**（按买入落点分支，两分支共用应用机器）：

1. **常态腿（备战席有空槽）**：
   - 新单位落备战席**首个空槽**（`bench_place`，槽号归一 = 下标+1）；
   - gold −= 牌单价 × 购买张数 k（常态 k=1；金账全款，无打包价——自动多买也无价格优惠，`research/merge_mechanics.md` §2.5）；
   - 商店载荷：被买槽 kind 置 empty（**留空不紧缩**——买后右邻槽像素零变化实锤，`research/economy.md` §2.1；同 (name, star) 匹配槽对前 k 个置换，三态定长模型）；
   - **全场合成连锁**：买入后同名同星计数（备战∪场上，`same_star_count`）≥3 即升星，落点 = 场上那张的位置（装备/站位随之继承）或全在备战栏时最左一张的位置；连锁可多级（2★ 产物再凑 3 → 3★）；三只身上的装备**全部**继承到产物（`kernel/cw_merge_simulate.py::_merge_bench` 不动点循环；装备继承 = 玩家定谳，merge_simulate 模块头规则 4）；升星触发时 front_row/back_row 整表 + board 重算随写（值签名变化才写）。升星触发判定单一源 = `kernel/cw_game_state.py::detect_merge_upgrade`（同名最高星抬升）。
   - 买牌不产经验（XP 域零写；零购买子集反证，`research/xp-rules.md` §2）。
2. **满栏例外腿（备战席满）**：满栏仍买得进当且仅当本次点击能完成一次合成（判据单一源 = `merge_buy_completes`，前提门 = 已有同名同星素材 ≥1；own=0 满栏域游戏拒买，ADR-0619/ADR-0283）。一击多买张数 k = `merge_buy_k` = min(店内同名同星张数, 3 − 已有数 mod 3)（绝不多买，`research/merge_mechanics.md` §2.5）；k 张逐张原价扣金（总价 = k×单价）、店载荷下架 k 张同身份牌、合成腾槽（应用机器 = `_apply_full_bench_merge_buy`，逻辑态直写与 tracked 双账同构单一源，T-182）。执行器张数回执 = `BuyCardOp` 的 `merge_buy_k` 现算，执行账补差 (k−1)×单价。

**随机面**：商店直出 2★/3★ 的概率与出现（星级经费用徽章倍数反推，识别面不进逻辑态）；买入触发合成后画面上的升星动画（~1s，`research/screen_flow_timing.md` #8b）。

**拒绝边界**：满栏且合成不可达 = 游戏拒买（applied=False + reason='bench_full'，零写——金不扣、牌不下架）；提案 expect 失配（SellBench 族语义，买牌无此域）。

**知识缺口（fallback 申报）**：非满栏时一次点击恒买 1 张是**框架推论**，未实测（fields.md §4.2 BuyCard 行同款标注，详 §7 G1）。缺口闭合前按 k=1 记账；若买后观察发现多张，对账纠偏 + 缺陷台账暴露。

**依据**：`research/merge_mechanics.md` §1/§2/§2.5/§2.6/§3；`kernel/cw_game_state.py::apply_shop_action_logic` BuyCard 腿 + `apply_shop_merge_leg`；`kernel/cw_merge_simulate.py` 合成规则族；`kernel/cw_vocab.py::mutate_bench_deployed`（执行侧 tracked 同步）；`operations/cw_op/cw_buy_card_action.py::BuyCardOp`；`fields.md` §4.2 BuyCard。

### 2.2 RefreshShop（刷新商店）

op = `operations/cw_op/cw_refresh_shop_action.py::RefreshShopOp`（**段终结**：刷新是唯一引入新事实的动作，执行即本段结束，下一段入口观察重建期望态）。

**确定面**：

- gold −= 实付刷新费。刷价真值 = 容器 `shop_refresh_cost`（备战帧现场 OCR，ADR-0622 观察通道；缺读 = 建模基价 `REFRESH_COST_BASE` 显式缺省，`kernel/cw_economy.py::refresh_cost_effective`）。免费帧（paid=0）金域不写（付费域纯净性，fields.md §3.3.4）。
- 计数组腿（容器写端 = 刷新执行落地门）：`total_refresh_count` 恒 +1；付费帧 `paid_refresh_count` +1；免费帧 `free_refresh_balance` −1（下限 0）且 paid 不写（fields.md §4.2 RefreshShop）。
- 修饰腿（注册表口径）：免费刷新来源（概率事件 / 按节点免费额度）只影响实付金，不改「整店全换」；按刷产经验（淘金客，`xp_per_refresh`）= 经验域 logic 写（fields.md §4.2 修饰段）。

**随机面**：刷新后的牌面 = 整店 5 槽全换（非逐槽补空，实机实锤 `research/economy.md` §2.1）→ **店载荷失效，新牌面归下一段入口观察**；容器 shop payload 本动作不写（随机面域级跳写，新牌面留观察覆盖）。UI 陷阱在册：面板右下「刷新金币数」区域实际印的是利息徽标不是刷价（三流对拍定谳，`REFRESH_COST_BASE` 注）。

**依据**：`research/economy.md` §2/§2.1；`kernel/cw_economy.py::REFRESH_COST_BASE`/`refresh_cost_effective`；`fields.md` §4.2 RefreshShop；[shop.md](../screens/shop.md) §5（visit 级刷新硬墙）。

### 2.3 CloseShop（关商店）

op = `operations/cw_op/cw_close_shop_action.py::CloseShopOp`（动作 op 内 no-op，关店点击由编排壳 `operations/cw_op/cw_op_close_shop.py::CwOpCloseShop` 承担；**访问终结**，恒可用）。

**确定面**：shop 域**结构离屏**（`apply_shop_action_logic` CloseShop 腿 = `leave_screen(bs.shop)`，载荷语义失效）；其余域零写。**关店本身不改牌面事实**：节点内关店→重开不刷新（牌面持久），跨节点才自动刷新全店（`research/economy.md` §2.1）——牌面去留由节点推进事件锚定，不由本动作推算。

**随机面**：无。

**依据**：`kernel/cw_game_state.py::apply_shop_action_logic` CloseShop 腿；`research/economy.md` §2.1；`research/screen_flow_timing.md` #15（收起 ~1s 过场）；[screens/README](../screens/README.md) §6（终结语义总表）。

### 2.4 SellBench（卖备战席角色）

商店域 op = `operations/cw_op/cw_sell_bench_action.py::SellBenchOp`（能力面在役、策略面收缩至备战期，判例见 [screens/README](../screens/README.md) §5）；备战域执行器 = `prep_actions.py::PrepActionExecutor._sell_bench`。双族坐标系：族 A（`cw_vocab`）= 槽位下标，族 B（`cw_prep_actions`）= 物理槽位 1-9，换算 = 族 B = 族 A + 1（screens/README §4 动作坐标系二分注）。

**确定面**：

1. 备战席该槽位清空（置 None **不移位**，ADR-0316 槽位语义；跨动作组下标恒稳）；
2. gold += 退款，公式单一源 = `kernel/cw_economy.py::sell_refund`：退款 = 招募费（`bench_char_cost`，注册表单一源，未知按中位保守估）× 星级倍数表 `_SELL_MULT`（星级倍数 = 合成副本数结构：1★=全额，2★/3★/4★ = `star_base_copies` 同构倍数）；**手续费口径**：star≥2 且 cost≥2 再 −1；cost=1 豁免（2★1费 卖出=全额倍数，live 实测定谳，`sell_refund` 注 + `research/economy.md` §3）；3★/4★ 的手续费档 = 推测待 live 核（§7 G3）；
3. **装备全量回装备区**：被卖单位身上的全部装备（简易/进阶/核心不分）进入 owned 装备库存——穿戴是可逆暂借（【口述·权威】`research/equipment_mechanics.md` §1「卖出角色=装备全量回装备区」；kernel 按 C6 装备守恒回收建模，`cw_vocab.py` 卖出分支注；实机帧级证据未采 = §7 G5）；商店逻辑态直写腿已落码 equips 回收（`apply_shop_action_logic` SellBench 腿）；备战写口域集 = gold/bench（`apply_prep_action_logic`，equips 域留观察覆盖——域集封闭申报）；
4. 陈旧提案拒：expect 身份与槽内不符 = 零写（ADR-0317）。
5. **溢出条件腿**（2026-09-15 实机建档 [prep.md 告警节](../../../../../game/screens/currency_war_prep.md)）：`overflow_warning` 在场（备战席满告警横幅 = 存在未安置溢出角色，此刻出战点击被游戏忽略）时，卖出语义补一条——**腾出槽当帧记溢出卡入位**（`bench[i] := 溢出卡`，「卖 → 溢出卡自动入自由槽」是游戏侧行为；有溢出时席必满、自由槽恒唯一，落位无歧义）+ `overflow_card` 消费清空 + 旗标 logic 消亡（下帧实读覆盖，两态制观察赢）。入位对象身份缺读（`overflow_card=''`）= 跳过入位（槽留空等观察），卖出语义本体不受阻；星级缺读按 1 兜底。容器字段 = `overflow_warning: bool` / `overflow_card: str`（观察写端 = `cw_screen_prep` 备战 heavy 溢出观察写端，渠道①）；策略消费门 = mandate 溢出门（flag 在场 → 本帧决策强收窄单动作 SellBench，禁发 StartBattle/冻结买面）。**三账同帧**：腿落地是跨账事件，容器腿（本写口）/ 执行侧 tracked 主账吸收（本写口 `session` 形参在场时，摘该槽 + 追加入位卡后经 `bench_from_compact` 重建槽位表——缺吸收 = 商店播种守卫 expected-vs-tracked 双账分叉，实机 2-4 停机实证）/ 黑板帧镜像（`_project_prep_obs` 入位卡补进 `bench_chars`、`free_bench_slots` 不 +1——腾出槽即刻回占）三面同帧同源。

**随机面**：无（卖价修饰效果 = 大裁员/降本增效的卖价 ×2，其作用口径待实证 = §7 G4，缺口闭合前不写修饰腿）。

**备战域金腿载体**：卖出动作的执行点金差 = `PrepActionExecutor._executed_gold_delta`（+sell_refund，对象 = dispatch 前 tracked 快照）→ `cw_exec_state.py::_advance_gold` 直推容器金账（logic_action 渠道，观察赢）；身份不可辨 = None 诚实缺失，禁保守估值假账。

**依据**：`research/economy.md` §3；`kernel/cw_economy.py::sell_refund`/`bench_char_cost`；`kernel/cw_game_state.py::apply_shop_action_logic`/`apply_prep_action_logic` SellBench 腿；`kernel/cw_exec_state.py::apply_op_effect` SellBench 分支；`research/equipment_mechanics.md` §1。

### 2.5 LevelUp / LevelUpShop（买经验·商店单击形态）

op = `operations/cw_op/cw_level_up_action.py::LevelUpOp`（单击「购买经验」；能力面在役、策略面收缩至备战期）。机制依据 = `research/xp-rules.md` §2。

**确定面**：

- 单击 = +`XP_PER_BUY` 经验、−单击价；攒满当前级门槛即升级、溢出结转（推进算子单一源 = `kernel/cw_economy.py::xp_apply_clicks`；门槛表 = `XP_TO_NEXT_LEVEL`）；
- 满（`MAX_PLAYER_LEVEL`）级点击无效 = 拒（applied=False + reason='level_cap'，零写——零金零经验，行为由投影直锁 M1（`test_cw_shop_projection_logic`）钉住）；
- 单击价单一源 = `kernel/cw_economy.py::xp_click_cost` 两支语义：**显示价支**（容器 `level_up_cost` 观察价直通——游戏侧已算好全部折扣）/**兜底支**（基价 `XP_CLICK_COST_FALLBACK` 减在册折扣效果；折扣只降价不减经验，`xp-rules.md` §2）；
- 金：gold −= 单击价 × 实击数（击数 = 执行回执 `ShopActionExecuted.levelup_clicks`；缺回执 = 本轮不写逻辑态，等观察覆盖）；
- 经验域写入 = `(当前级已攒, XP_TO_NEXT_LEVEL[新级])`；**level 字段不在商店逻辑态直写域集**（升档等观察覆盖，域集封闭申报）。

**随机面**：无。**修饰效果副作用**（商业间谍「升级时刷新商店并偷最贵 3 张」、晋升名额「随机一槽变高费」）= 未建模，后果归观察（§7 G7/G8）。

**依据**：`research/xp-rules.md` §2；`kernel/cw_economy.py::xp_apply_clicks`/`xp_click_cost`/`XP_PER_BUY`/`XP_TO_NEXT_LEVEL`；`kernel/cw_game_state.py::apply_shop_action_logic` LevelUp 腿；`fields.md` §4.2 LevelUp。

### 2.6 CompTransaction（整档替换事务）

op = `operations/cw_op/cw_comp_transaction_action.py::CompTransactionOp`（**终结邻接 fallback**：执行即本画面访问结束，交回重观察——合成建模 fallback 语义，禁半档中间态）。

**确定面**（语义源 = 容器写口 `apply_shop_action_logic` CompTransaction 腿，C1 冻结不变量：**拒 = 整批零写，应用后无半档残留**）：

1. 先全量校验（`_resolve_comp_transaction`）：任一子步资源不足 → 整批拒（applied=False + 拒因，零容器写）；
2. 应用序 = 卖出 → 部署源清槽 → 下场（deployed 置 None + `bench_place` 放回）→ 上场（排/槽归一 + `deployed_place` 落槽）→ 填位（bench 源按后置槽位表解析；shop 源 = 买后即上：gold −卡价 + 该商店槽置 empty）——顺序保证 bench 满时保留件不被静默丢弃（单位守恒，ADR-0380 件③）；
3. 汇总：gold = −fill_cost + income；卖出单位装备回装备区；board 重算（`_recount_board` 单一源）。

**随机面**：无。**依据**：`kernel/cw_game_state.py::apply_shop_action_logic` CompTransaction 腿（携 income/fill_cost 出参）。

### 2.7 词表完备性注：SellDeployed / SwapDeploy 的商店逻辑态直写腿

- **SellDeployed**（卖上阵）：商店逻辑态直写腿在役（`apply_shop_action_logic`，v2 动作族），生产商店 op 表未收录（策略面由备战域承担，§3.2 主述）。规则与 §3.2 同一条。
- **SwapDeploy**（上阵↔备战对调）：词表 + 容器逻辑态直写 + sim 消费在役，**生产执行器未接线**（备战域部署换位经部署机拖拽承载）。逻辑态（规则在册，供接线/sim 消费）：deployed 槽 di 与 bench 槽 bi **原槽对调**（置空不移位坐标系）；上场者继承下场者的排（含开拓者形态归一），槽号信息位重写；board 重算；同名同星已在场其余位 = 拒（`duplicate_on_board`）；expect 双侧失配 = 陈旧提案拒。装备随人走（对象迁移）。依据：`kernel/cw_game_state.py::apply_shop_action_logic` SwapDeploy 腿 + `cw_vocab.py::mutate_bench_deployed` SwapDeploy 分支（W43 裁决 1/2 代际校验 + 同名唯一性）。

## 3. 备战域动作（原子词表）

备战域动作词表 = `kernel/cw_prep_actions.py::PREP_ACTION_TYPES` 白名单；执行器 = `prep_actions.py::PrepActionExecutor`（机械执行，发出即职责完成，落地判定归观察对账）。容器写口 = `kernel/cw_game_state.py::apply_prep_action_logic`（域集封闭 = gold / bench / xp / level / front_row / back_row / board，集外动作零写，批 2a 扩域申报）+ `kernel/cw_exec_state.py::apply_op_effect`（金账/库存腿，显式不建模盲区在册）。slot 语义全局统一 = 画面物理槽位（备战栏 1-9 / 前排 1-4 / 后排 1-N），与族 A 的换算见 §2.4。

**发射形态（R2 原子通路，批 2a 起）**：决策核逐帧发原子动作（部署 = DeployMove 序 / 穿戴 = WearEquip 序 / 工具 = 各消耗品原子类 / 卖出 = SellBench/SellDeployed），备战环逐帧取决策输出首项执行；组合壳（RunDeploy/RunEquip/RunTools）不再是生产发射形态（类与登记行删除归批 2b 归一删除面）。发射位计划构造单一源 = `kernel/cw_deploy_logic.py::select_deployments`+`assign_deploy_slots`（部署）、`kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`（穿戴）、`kernel/cw_equip_env.py::evaluate_tool_actions`+`admitted_tool_actions`（工具 G1 准入）、`kernel/cw_prep_actions.py::select_sphere_clicks`（点球载荷）。

### 3.1 DeployMove（备战席 → 上阵单步拖拽）

**确定面**：

1. 备战席 `from_slot` 槽位清空（置 None 不移位）；目标单位对象整体迁移（身份/星级/装备随人走），落 `to_row` 排的 `to_slot`（`deployed_place` 按排路由，ADR-0392 定长槽表；槽号信息位重写）；
2. board 羁绊计数**增量** +1：按上场单位的羁绊标签全集（`unit_bond_tags`——星徽/卡带贡献在内；无标签回退阵营），逐标签 +1（ADR-0312 增量全集，防全量重算抹掉 OCR 真值）；
3. 上阵计数 +1（= 部署空位 deploy_vacancy −1；heavy 帧重读校准）；
4. 腾席链语境：`from_slot` 常为开箱/开典籍腾出的槽（§3.4/§3.5 先行）。

**随机面**：无（羁绊徽章动画 ~2s、达标触发的 overlay 延迟弹出 = 画面时序，`research/screen_flow_timing.md` #10/#24，非逻辑态）。

**拒绝边界**：同名同星已在场 = 游戏拒（恒成立约束「场上同名同星 ≤1」，`research/merge_mechanics.md` §3；kernel `mutate_bench_deployed` 同名唯一性守卫 duplicate_on_board）→ 零容器写；目标槽被占/拖拽未落地 = 零变化，落地事实归下一帧观察。

**依据**：`kernel/cw_game_state.py::apply_prep_action_logic` DeployMove 腿（批 2a 落码：bench 摘槽 + 落槽 + board 增量）；`prep_actions.py::_deploy_move` + `_track_move_deployed`；`research/merge_mechanics.md` §3。

### 3.2 SellDeployed（卖上阵角色）

**确定面**：

1. deployed 该槽位清空（置 None 不移位，ADR-0392）；
2. gold += `sell_refund(star, bench_char_cost)`（退款公式与手续费口径 = §2.4 同一条，单一源相同）；
3. 装备全量回装备区（同 §2.4 第 3 腿：口述·权威 + C6 守恒建模 + 缺口 G5；商店逻辑态直写腿 equips 回收在役，`apply_op_effect` SellDeployed 分支同步 owned 恢复腿）；
4. board 重算（`_recount_board`）；上阵计数 −1；
5. 拒绝边界：槽空/越界/expect 失配 = 零写。

**依据**：`kernel/cw_game_state.py::apply_shop_action_logic` SellDeployed 腿 + `apply_prep_action_logic` SellDeployed 腿（批 2a 落码：摘槽 + board 重算 + 回金）；`kernel/cw_exec_state.py::apply_op_effect` SellDeployed 分支（金腿 + owned 恢复腿）；`prep_actions.py::_sell_deployed` + `_track_remove_deployed`。

### 3.3 LevelUp（买经验·逐帧单击形态，R6 定案④）

词表 = `kernel/cw_prep_actions.py::LevelUp`。**粒度定案（design.md unified-action-factory §2.6 LevelUp 粒度定案④/R6）**：LevelUp 是单动作意图 = **单击**「购买经验」；升 N 击 = N 帧各发一次（决策循环逐帧重组，与商店域单击形态 `cw_level_up_action` 同构先例）。原「执行器有界连点（一次发射=升完一级）」随定案退役——把「一次发射=升完一级」留在执行器与统一类单击语义冲突（cost 字段失义）且授权滞留执行层与发射面门构成双源。

**确定面**：

- 每击：+`XP_PER_BUY` 经验、−单击价（单击价单一源 = `kernel/cw_economy.py::xp_click_cost` 两支语义：显示价支容器 `level_up_cost` 直通 / 兜底支基价 `XP_CLICK_COST_FALLBACK` 减在册折扣）；
- **授权/发射门全在决策核发射位**（执行器授权面全删）：每帧发射前置 = kernel `clicks_to_next_level` 现算击数 > 0；金地板逐击查金（`spend_unified`）/预算闸（`levelup_budget_gate`）/血闸（`blood_xp_gate`）= 发射位既有门链；满级 = 击数 0，无授权不发射；
- **容器逻辑态**（批 2a 落码，`apply_prep_action_logic` LevelUp 分支）：xp/level 跨门槛推进（推进算子单一源 = `xp_apply_clicks`，单击步长；level/xp 缺读 = 域级跳写）；**deploy_cap 不写**（容量真值由观察写端防抖读承接，`max_units` 的 cap<level 兜底规则保守承接升级增量）；
- **金腿（批 2a 中间态）** = 执行缝金差（`PrepActionExecutor._executed_gold_delta` → `_advance_gold`，单击价 `xp_click_cost` 现算、失读回退 `XP_CLICK_COST_FALLBACK`）；`action.cost` 字段装载（`xp_click_cost` 现算 / 失读回退）与金腿切 `action.cost` 直写、auth_basis 分键，随批 2b 类合并翻转生效（§3.2b 消费面收口）；
- 经验/等级真值 = 下一帧观察经验对账族承接（XpLedger 通道单击推进 + OCR 真值 reconcile）。

**随机面**：无。**修饰效果副作用**（商业间谍/晋升名额）归观察（§7 G7/G8）。

**依据**：`prep_actions.py::PrepActionExecutor._level_up`（单击化）；`kernel/cw_economy.py::clicks_to_next_level`/`xp_apply_clicks`/`xp_click_cost`；`kernel/cw_game_state.py::apply_prep_action_logic` LevelUp 分支；design.md unified-action-factory §2.6 LevelUp 粒度定案④。

### 3.4 OpenBox（开补给箱）

**腾席**（本篇用词）= 备战席占用槽位被释放、可用空槽数增加。

**确定面**：被点补给箱所在备战槽位的占位物品离席 → 槽位腾出（「开箱即腾席」，`kernel/cw_prep_actions.py::OpenBox` 注；逻辑态直写已建模面 = `cw_screen_prep.py::_project_prep_obs`）。**容器 GameState 零写**（`apply_prep_action_logic` 对本动作显式返回——箱/典籍是视觉域推进，落点 = 备战观察帧）。

**随机面 / 观察面**：箱内四选一内容 = 掉落内容归观察；本动作点「开启」后**本访问交回（终结化，R7）**——武装箱选择画面由外循环按画面分发独立画面 op 选卡（`operations/cw_screen/cw_screen_box_pick.py`，见 §6 单选族边界），备战动作词表无选卡动作（`PickBoxCard` 已删，批 2a）。动画等待 `_OVERLAY_ANIM_WAIT_S`，弹窗就位与否交下一帧观察（`research/screen_flow_timing.md` #28）。

**拒绝边界**：画面无箱（观察-执行竞态）= 未发出，交回重观察重派。

**依据**：`kernel/cw_prep_actions.py::OpenBox`；`prep_actions.py::_open_box`；`fields.md` §4.2 OpenBox。

### 3.5 OpenTome（开秘密典籍）

**确定面**：秘密典籍道具占备战席 1 槽（类补给箱；**获得时入席** = 投资策略「秘密典籍」的发放事件，属观察面非本动作）。本动作点槽两次（选中→开启）→ 典籍离席腾槽 + 星徽四选一 overlay 弹出；容器零写（同 §3.4 视觉域推进）。

**随机面 / 观察面**：四选一卡面内容归观察；选卡决策 = 外循环 0i handler（板上阵营匹配），落地记录走 chosen_tome（§6 边界），本动作不选卡。

**依据**：`kernel/cw_prep_actions.py::OpenTome`；`prep_actions.py::_open_tome`。

### 3.6 ClickSpheres（点奖励球）

**确定面**：坐标列表（奖励球观察面 `spheres`）中**被点的球按载荷坐标精确摘除**（逻辑态精确摘球，`_project_prep_obs`——坐标匹配，R4 改形后载荷即点击列；原「保守清空」随改形退役）。容器 GameState 零写（视觉域推进）。

**发射形态（R4 坐标参数化机械动作）**：载荷 = 有序球坐标点击列表（大球优先/上界挑选归决策侧 kernel 单一源 = `kernel/cw_prep_actions.py::select_sphere_clicks`，发射位以预算常量 `SPHERE_CLICK_BATCH_MAX_K` 调用）；执行器纯机械逐个点（原读屏选球与批内截断半随改形退役）。

**随机面 / 观察面**：球内容（金币/角色/装备/掉箱）与金额 = 随机面归观察——执行点金差显式申报为 None 盲区（`PrepActionExecutor._executed_gold_delta` ClickSpheres 支，禁拍值）；点开占席球（角色/箱）落席占 1 槽；掉箱 → 下一帧观察 → OpenBox 臂统筹。

**前置谓词（席满拦截）**：bench 空闲 >0 ∨ 球均不占席，才发射点球（fields.md §4.2 ClickSpheres；席满让路门 = 策略发射面席满探针）。席满点占席球 = 游戏侧点不动，球仍在 → 下一帧观察回补、下轮再派。

**依据**：`kernel/cw_prep_actions.py::ClickSpheres`/`select_sphere_clicks`；`prep_actions.py::_click_spheres`；`fields.md` §4.2 ClickSpheres；`research/screen_flow_timing.md` #16（飞行动画 ≤2s）。

### 3.7 OpenBookcard（开书册卡）

**词表**：`kernel/cw_vocab.py::OpenBookcard`（R10 开卡归位备战词表：书册卡 = 备战席占槽道具，与补给箱/秘密典籍并列第三件；与 OpenBox/OpenTome 同签名，`slot: int | None`，None = 首张）。

**确定面**：书册卡道具占备战席 1 槽；点槽「开启」→ 书册卡离席腾槽 + 专家邀请函五选一弹窗弹出。书册卡无独立载荷列表字段（箱/典籍有 `boxes`/`tomes`，书册卡占席事实只在 `free_bench_slots` 现读口径）→ 逻辑态 = 腾席 +1（`_project_prep_obs`，与 heavy 现读 `slot_occupied` 扫描同式）；**容器 GameState 零写**（`apply_prep_action_logic` 集外动作型直接返回，同 §3.4/§3.5 视觉域推进）。

**随机面 / 观察面**：五选一卡面内容归观察；选卡决策 = 弹窗画面 op `CwScreenExpertInvite`（默认策略单一源 = `choose_expert_index` 原位，chosen_expert 落地记录 §6 边界），本动作不选卡。动画等待 `_OVERLAY_ANIM_WAIT_S`，弹窗就位与否交下一帧观察。

**发射形态**：本批发射位 = 备战环入口清场段（`cw_screen_prep._clear_prep_cards` 改产本动作经执行器发射 + 本访问交回，外循环 0k 按画面分发选卡；R7 OpenBox 终结化同构）。是否升 director 门控留策略侧定——升门控时需随 OpenBox 同构补备战 visit 终结分支（当前词表发射形态已备完整逻辑态分支，R9 全覆盖）。

**依据**：`kernel/cw_vocab.py::OpenBookcard`；`prep_actions.py::PrepActionExecutor._open_bookcard`；design.md unified-action-factory §2.6 R10；`landing.md` §3.2c。

## 3A. 穿装备与工具消耗（R2/R8 原子类）

### 3A.1 WearEquip（穿装备）

词表 = `kernel/cw_prep_actions.py::WearEquip`（装备库 owned 件 → 目标角色物理槽位；R2 穿戴原子通路，RunEquip 组合壳溶解后的发射形态）。

**确定面**：

- 装备归属转移：owned 库存 −1 件（视觉域逻辑态 = `obs.owned_equips` 摘件，`_project_prep_obs`；容器 equips 域留观察覆盖——域集封闭申报；tracked 面 = `apply_op_effect` WearEquip 分支 owned −1 + 目标角色 equips +1）；目标角色已穿域 +1（角色装备上限 = `EQUIP_CAPACITY`）；
- **零比对出生（裁决 3）**：动作 op 内零 CV-diff 验穿——穿没穿归观察写入边对账（装备期望态对账族下一入口暴露）；原 avatar-slot CV-diff 验穿面随原子化删除；
- 计划构造 kernel 单一源 = `kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`（决策侧逐帧现算）。

**穿着即合成**（在册建模裁定）：两件可合成组件穿到同一角色 = 自动合成；**不记合成预期值**（fields.md §4.1 豁免），后果走观察覆盖 + 缺陷台账——该豁免是建模裁定，不是知识缺口。

**依据**：`kernel/cw_prep_actions.py::WearEquip`；`prep_actions.py::PrepActionExecutor._wear_equip`；`kernel/cw_equip_wear_plan.py`；design.md unified-action-factory §2.6/R2/裁决 3。

### 3A.2 工具原子类（R8 按消耗品各立类）

词表七类（裁决 1 定案命名）：`FurnaceUse`（冶金炉，双模式）/`PrivilegeCardUse`（特权赋予卡，双腿）/`WrenchUse`/`PrecisionWrenchUse`/`StaffProjectorUse`/`PerfectProjectorUse`/`LuckyTokenUse`。执行载体 = `prep_actions.py::PrepActionExecutor._use_tool`（owned 网格内 icon → 目标机械拖曳，零消耗确认对拍——原 `CwOpTools` 三态对拍随原子化由观察承接，消费真值 = 下一帧装备区读数）。逐件逻辑态规则 = §4（规则本体不变，执行载体由组合 op 换为原子类）。

## 4. 工具族逐件逻辑态（7 件）

工具类（category='工具'）7 件登记于装备注册表（`research/equipment_mechanics.md` §5 全量；不可 drag 穿，消耗交互 = owned 网格内 icon→icon 拖曳）。**逐件写端登记单一源** = `kernel/cw_affix_effects.py::EQUIP_WRITE_SIDES`（每件恰一个落码写端，值词表四形：`bridge:`=写端桥确定性直写 / `contribution:`=贡献算术零直写组合收口 / `op:`=执行域既有写端 / `observation`=负写端随机面观察收口）+ 逐件归属申报 `EQUIP_REWRITE_DECLARATIONS`。

**执行载体（批 2a 起）**：工具消耗 = 备战词表原子类（§3A.2，R8 按消耗品各立类；裁决 1 定案命名），发射位 = mandate_v1 entry ②′（判据单一源 = `kernel/cw_equip_env.py::evaluate_tool_actions` → `admitted_tool_actions` G1 准入，本层禁第二套时机判断），机械半 = `prep_actions.py::PrepActionExecutor._use_tool`。原组合 op 载体（`CwOpTools`，含消耗确认对拍）随原子化退役。

**分档结构**（执行接线 = 哪个执行面消费本件规则）：

- **档 1（判据准入放行，原子类发射）**：冶金炉（→`FurnaceUse`，furnace_single）、特权赋予卡（→`PrivilegeCardUse`，privilege_upgrade）；
- **档 2（判据面 fail-closed，类随族立档、发射位禁无判据发射）**：拆装扳手（→`WrenchUse`）、精密拆装扳手（→`PrecisionWrenchUse`）、员工投影仪（→`StaffProjectorUse`）、完美投影仪（→`PerfectProjectorUse`）、好运令牌（→`LuckyTokenUse`）——判据面拒因分键在册（dest_unready/cold_start_later/rc_missing）；其中员工投影仪/完美投影仪/好运令牌的 kernel 写端桥已备（接线 = 桥调用），拆装扳手走执行域既有装备转移链。

**通用边界**：工具消耗品 −1 与目标件消失的逻辑态 = 视觉域帧面直写（`_project_prep_obs` 工具分支，按 `EQUIP_WRITE_SIDES` 申报逐类落）+ 下一帧装备区读数覆盖；消耗确认三态对拍随原子化退役（消费真值归观察）。首件消费后画面网格重排（reflow）→ 工具原子 = 截断类（发射帧独占，后续网格目标动作下帧重评）。装备获得固定入栏序（第 1 排消耗品从右往左、装备区先右列后左列，`research/equipment_mechanics.md` §5）= 观察剪枝知识，不进逻辑态。

### 4.1 冶金炉（装备目标·档 1 已接）

- **炉·装备腿**（拖到一件装备 icon）：确定面 = 工具 −1、原装备件从库存消失；**变异产物** = 同类型随机装备 = 随机面 → 负写端 observation（`EQUIP_WRITE_SIDES['冶金炉']`），产物名归下一帧装备区读数。
- **炉·角色腿**（拖到角色）：确定面 = 该角色全部装备（≤`EQUIP_CAPACITY`）从穿戴域移除归入库存域；**随机面** = 每件各自变为同类型随机装备 → 观察收口。期望口径已证：产物「有无放回」对决策不敏感、k=3 角色用法首中期望在册（proofs/p14 定理 2/Q2、proofs/p50）——决策表不依赖产物分布，故随机面豁免无决策代价。
- 依据：`research/equipment_mechanics.md` §5 冶金炉行 +「冶金炉回收流水线」节；`EQUIP_REWRITE_DECLARATIONS['冶金炉']`；`operations/cw_op/cw_op_tools.py::plan_tool_drags` furnace_single 腿（目标 = 死库存件 `recycle_qualified` 命中，禁「画面可读首件」宽取）。

### 4.2 特权赋予卡（装备目标·档 1 已接）

- **库存腿**（拖到一件进阶装备 icon）：**确定性变换** = 该件名替换为对应 ·特权 装备名（映射 = `kernel/cw_effect_inventory.py::privilege_counterpart`，进阶↔特权全量双射由测试锁钉死）；写端 = `transform_equip_to_privilege`（库存中该名单件替换，数量守恒）。零写分支：库存未观察 / 无此件 → 跳写留观察。
- **穿域腿**（拖到角色）：该角色已穿**进阶**装备随机一件变特权——「哪件被选」= 随机面 → 即使执行接线，逻辑态只写**选定后确定面**（选定件 → 特权名，桥 = `transform_worn_equip_to_privilege`）；游戏自选形态归观察收口。现役执行臂只消费库存腿。
- 依据：`EQUIP_REWRITE_DECLARATIONS['特权赋予卡']`；`kernel/cw_affix_effects.py::apply_tool_execution_write` 特权化双腿段。

### 4.3 拆装扳手（角色目标·档 2 未接）

**逻辑态规则（本节即实现规格）**：目标角色的全部已穿装备移出穿戴域、**全量回装备区**（owned 库存 += 全部件名）；工具消耗品 −1（用后消失）。装备转移不可角色间直拖（拖拽无响应），转移两途径 = 卖角色或扳手（`research/equipment_mechanics.md`「装备转移机制」节）。写端登记 = `EQUIP_WRITE_SIDES['拆装扳手']`（op 域既有装备转移链流向锚）。**依据**：equipment_mechanics §5 拆装扳手行、fields.md §4.2 RunTools。

### 4.4 精密拆装扳手（角色目标·档 2 未接）

- 取下全装备同 §4.3，但**不消耗**（无限次使用，工具库存面不递减）。
- **重复获得金腿**：已持精密扳手后再获得拆装扳手改 +1 金——确定面（金账 +1），写端 = 贡献算术 `equip_wrench_duplicate_gold`，组合写收口 = 获得回执窗 `settle_wrench_duplicate_gold`（窗口独占：获得回执 → 下一次金读数之间无其他金变更源）。
- 依据：`EQUIP_WRITE_SIDES['精密拆装扳手']`；equipment_mechanics §5。

### 4.5 员工投影仪（角色目标·档 2 未接，写端桥已备）

**逻辑态规则**：拖到 **3 费及以下**角色（官方前置门）→ 备战席创造该角色的 1 星复制（同 char_id、零装备）；工具 −1。写端 = `kernel/cw_effect_inventory.py::spawn_equip_bench_unit`（费用门形，`STAFF_PROJECTOR_COST_GATE`）。**席满语义（定谳）**：备战席满 / 超费用门 / bench 未观察 = **拒落零写**（与游戏端拒拖语义同源）→ 跳写留观察——席满不是部分成功，是无落位。**随机面**：无（确定性动作）。**依据**：`EQUIP_REWRITE_DECLARATIONS['员工投影仪']`；`_TOOL_SPAWN_COST_GATE`；fields.md §4.2 RunTools。

### 4.6 完美投影仪（角色目标·档 2 未接，写端桥已备）

同 §4.5，**无费用门**（gate=0）：拖到任意角色 → 其 1 星复制入备战席首个空槽；席满/未观察 = 拒落零写。**依据**：`EQUIP_REWRITE_DECLARATIONS['完美投影仪']`；`spawn_equip_bench_unit`。

### 4.7 好运令牌（角色目标·档 2 未接，写端桥已备）

**逻辑态规则**：拖到角色 → 从其**推荐进阶装备**中获得一件；工具 −1。**选定后确定**：选件事实（chosen_equip）已知时 = 装备库存 +1（桥 = `grant_equip_item`，非进阶类别 = 调用错；库存未观察 = 零写留观察）。**随机面 / 缺口**：候选池真实结构（效果文「四件」vs 图鉴「3+3」）待实测 = §7 G6（proofs/p14 Q5 在册）；选哪件 = 策略决策面，选定前无容器可算面。**依据**：`EQUIP_REWRITE_DECLARATIONS['好运令牌']`；equipment_mechanics §5。

## 5. 转场类动作（逻辑态 = 空）

**OpenShop**（开店意图，`kernel/cw_prep_actions.py::OpenShop`，备战环终结）与 **StartBattle**（出战，备战访问终结·唯一完成态）是**转移动作**：它们只把画面从 A 转移到 B，不按游戏规则改写任何局内资源。

- **OpenShop**：容器逻辑态 = 空（显式声明）。开店不触发刷新（基础刷新触发只有「节点切换」+「手动」，`research/economy.md` §2.1）；开店后牌面/gold = 入口观察重建（read_only 形态的读数目标 = gold 真值，观察面）。
- **StartBattle**：容器逻辑态 = 空（显式声明）。进战斗后 hp/gold/streak 全部由结算屏真值覆盖接管（`apply_op_effect` StartBattle 显式不推进清单；败轮金按轮首补发口径，fields.md §4.2 轮首收入）。**免战牌子态**：出战按钮变「跳过」；跳过执行落地后效果账本次数递减（`consume_use`，归零移除——效果账本侧确定性维护，非 GameState 字段逻辑态）；「跳过后 hp/streak/收入不动」= 待实机实证的暂定表述（§7 G9）。发射重发/连败停机 = 流程防线（[action_exec.md](../flow/action_exec.md) §7），不属逻辑态。

依据：`kernel/cw_prep_actions.py::OpenShop`/`StartBattle`；`kernel/cw_exec_state.py::apply_op_effect` 显式不推进清单；`fields.md` §4.2 出战。

## 6. 事件线选择（pick 族）：非逻辑态通道边界

事件单选族（投资环境/投资策略/补给/遭遇/盛会之星/伙伴/祈愿试炼/命运卜者/骇入策划/专家邀请函/星徽秘典/装备三选一/**武装箱四选一**）的**选择落地不进本篇动作逻辑态枚举**：选择结果由各画面 handler 单次记录到 chosen_* 字段（观察写端记录，`kernel/cw_game_state.py::GameState` chosen_* 域组），选择**后果**默认不记预期值——选择瞬间画面即切、无定型帧可核对，后果走观察覆盖 + 缺陷台账；有显式到账登记的照登记（在册先例 = 专家邀请函「现金为王」gold+4）。武装箱四选一（R7 批 2a 正位）= 独立建档画面「货币战争-备战-武装箱选择」的画面 op（`operations/cw_screen/cw_screen_box_pick.py`，选卡即终结的单选族例外；决策面 = 策略契约 `decide_box_card` / 局外 kernel `pick_equipment` 机器单一源）——它**不是备战动作词表成员**（原 `PickBoxCard` 动作形态已删）。依据：`fields.md` §4.2 事件选择/投资选择节；决策规格 = `../strategy-docs/13_pick_family.md`。

## 7. 知识缺口与补档清单

> 缺口只辖「确定面内的参数/规则未实证」，不辖「整条规则缺席」（规则缺席 = 本篇即实现规格，§1.3）。**缺口闭合前的统一过渡形态：该动作执行后交回重观察**（观察覆盖兜底 + 缺陷台账暴露）——这是过渡手段，不是架构：每条缺口闭合后按其「在册处置」列收敛为纯逻辑态直写。

| 编号 | 缺口 | 波及动作 | 在册处置（闭合前记账规则） | 补档方法 |
|---|---|---|---|---|
| G1 | 非满栏一击买牌张数（「恒 1 张」= 框架推论，零实测样本） | BuyCard | 按 k=1 记账；买后观察多张 → 对账纠偏 + 缺陷台账 | 实机局买牌动作行 × 备战席增量对账；或停机钩子采集「非满栏一击多张」帧 |
| G2 | 满栏连升（own=0 基础星满栏连买 3 张触发合成；merge_mechanics §2.5「连升同理」自标低置信未亲见） | BuyCard（满栏例外腿） | `merge_buy_completes` own≥1 门按**拒买**实现（ADR-0619 申报边界）；若拖动对账网实证连升可行 → 回该单一源改门 | 满栏 + 商店 3 张同牌帧采集；对账层出现「拒买但画面买成」缺陷票即触发复测 |
| G3 | sell_refund 3★/4★ 手续费精确值(−1 为推测) | SellBench / SellDeployed / CompTransaction | 退款消费按保守端(下界)组装;live 核定 = 单局复盘检查项 | 3★ 已 live 定谳(2026-09-15 详情面板实测:3★2费=+17=cost×9−1 ✓,1★/2★ 同场三点全中,详 economy.md §3——4★ 档仍未核,剩余缺口收敛到 4★) |
| G4 | 卖价修饰 ×2（大裁员/降本增效）作用口径（净额 vs 基础价） | SellBench / SellDeployed | 不写修饰腿，退款按基础公式；实持效果局观察覆盖 | 持修饰效果局卖 2★ 看回金差 |
| G5 | 卖带装角色装备去向（口述·权威 = 全量回区；实机帧级证据未采） | SellBench / SellDeployed / CompTransaction | 按 C6 装备守恒回收建模直写（在役）；对账层认「账面 2 组件 == 画面 1 进阶」类合法态 | 卖带装单位前后装备区逐格对拍（heavy 帧采集） |
| G6 | 好运令牌定向池结构（「四件」vs「3+3」）与判据面（R(c) 推荐表未采集） | 好运令牌（§4.7/§3A.2） | 判据面 fail-closed 永不进准入；`LuckyTokenUse` 类随族立档 + 发射位禁无判据发射（批 2a 申报），逻辑态 = 工具 −1 + 获得面按选定后确定直写 | 拖一次令牌数选项实机采集（proofs/p14 Q5）+ 判据面建模批补档 |
| G7 | 商业间谍「升级时刷新商店并偷最贵 3 张」副作用 | LevelUp（两形态） | 升级腿只写经验/金；牌面偷取后果归下一帧观察 | 持商业间谍局升级时刻前后商店牌面对拍 |
| G8 | 晋升名额「买经验时随机一槽变高 1 费」副作用 | LevelUp（两形态） | 同 G7（随机面归观察） | 持晋升名额局买经验前后牌面费用对拍 |
| G9 | 免战牌跳过后 hp/streak/收入「不动」（暂定表述） | StartBattle（跳过子态） | 跳过无结算帧；下一备战帧观察覆盖时三字段必核对 | 免战局跳过前后三字段对拍 |

（随机面类目——刷新新牌、冶金炉产物、奖励球内容、掉落金额——**不在本表**：它们受 §1.2 确定性原则管辖，是原则性的观察收口，不是待补档缺口。）
