# 动作逻辑态（action-logic-state）

> **逐动作计算规则分篇见 [logic-updates/](logic-updates/README.md)**（每动作 op 一篇：域集/转移规则/随机面/拒绝语义/符号名引用/语义验证（投影测试）/先例）；本篇保留总则与原则。
> 术语与图例:保留词(两态制/逻辑随机态/对账/帧/帧代次等)与数字来源标注四形态【注】【推】【拟】【拍】见
> [README](README.md) §6 术语表;对账 = 推算状态与下一帧实读逐项比对,对不上即 bug;帧 = 一次拍画面+做决策的时点,帧代次 = 帧的版本标记。
> 定位：货币战争主链**每个动作 op 的逻辑态计算规则全集**（地基文档）。动作 op 机械发出后，不经任何画面观察，按游戏规则从动作前状态推算出预期状态并直写状态容器(GameState)——这份推算规则的确定性全集就是本篇。真值永远以下一帧画面观察为准。
> 用户裁定：不许以「逻辑态未建模」为由把动作返回主循环——在用动作全集逐个有逻辑态；除 §5 两类转移动作显式声明「逻辑态=空」、§6 声明的事件选择边界外，本篇不存在「无逻辑态」的动作。
> 机制事实依据 = `docs/game/currency_war/research/`（merge_mechanics / xp-rules / economy / equipment_mechanics / screen_flow_timing）+ `docs/game/currency_war/data/gameplay.md`（官方原文）+ `../proofs/`（数学证明）。kernel 现位依据 = 符号名引用 `文件::符号名`（路径根 = `src/sr_od/application/currency_war/`，行号不写，随代码漂移）。
> 读者 = 无会话历史的工程师/智能体。职责分界：「一次访问内怎么编排动作」= [action_exec.md](../flow/action_exec.md) / [prep.md](../screens/prep.md) / [shop.md](../screens/shop.md)；「每个字段怎么记」= [fields.md](fields.md)。与 fields.md 的分工：fields.md 按**字段**记写入面，本篇按**动作**记计算规则，同源互指。

## 1. 总则

### 1.1 逻辑态与两态制

**逻辑态**（本篇主题）= 一个动作 op 机械发出后，**不经观察**、只按已核实的游戏规则、从动作前状态容器状态**推算并直写**的预期状态。

**两态制** = 状态容器——局内状态唯一快照 `kernel/cw_game_state.py::GameState`（下称「状态容器」）——的每个字段只保留两种值来源：**观察态**（画面读数，`observe` 写入）与**逻辑态**（动作后推算，`write_logic` 写入）；同帧冲突时**以实际观察为准**（观察值覆盖逻辑推算值）。依据：`fields.md` §2.3/§2.5。**逻辑随机态扩展**（来源 `logic_rand`，`write_logic_rand` 写入；**采样语义**）：效果随机的动作在上报函数真掷随机、按采样结果走完整确定性链逐步直写，全部字段写操作标随机态；观察覆盖差异预期内（`logic_rand_outcome` 记录行，不进失配的三种标准处理分支），**策略器消费前必须重观察**（查询入口 = `logic_rand_fields`）；详见 `fields.md` §2.1/§2.5 与 [logic-updates/collect-ore.md](logic-updates/collect-ore.md)（首个落地）。

一句话读法：逻辑态回答「这一下点完，状态容器**应该**变成什么样」；下一帧观察回答「实际变成了什么样」；两者不等 = 逻辑态模型缺陷，走缺陷记录表（不静默、不改道）。

### 1.2 确定性原则：随机面不进确定逻辑态

动作后果一分为二：

- **确定面** = 规则上唯一可推算的部分：扣多少金、哪个槽位清空、谁升星、退多少金。逻辑态只写确定面。
- **随机面** = 游戏内部掷随机数的部分：刷新后的新牌面、冶金炉的变异产物、晶矿的掉落内容、掉落的金币数额。

随机面的落法两档：

1. **采样口径已登记** → 按**逻辑随机态**直写（`write_logic_rand`，来源 `logic_rand`）:上报函数**真掷随机**、按采样结果走完整确定性链逐步写,全部字段写操作标随机态;实机上采样是猜测（观察覆盖差异预期内,`logic_rand_outcome` 记录行,不触发失配告警——首现注:失配告警 = 发现失配即报警并停机）,sim 里采样即状态副本里的值（同一上报函数两副面孔,sim 零自算）。采样错形态时交由观察收尾兜底——**安全的不准确**。首个落地 = 点晶矿（[logic-updates/collect-ore.md](logic-updates/collect-ore.md);临时口径 v0 待采集校准,常量面 = `kernel/cw_ore_reward.py`）;后续迁移批 = 冶金炉/特权卡/好运令牌采样迁入上报函数、投资卡随机授予写入方。
2. **无确定面可写且采样口径未建**（如刷新后的整店铺面）→ 域级跳写，归下一帧观察（跳写纪律与上报函数同型——未读域跳写、值留观察覆盖,`kernel/cw_action_report/__init__.py` 模块头申报）。

原则底线不变：随机面**不存在可写的确定真值**——确定逻辑态（`write_logic`）禁写随机面（编确定值会制造假缺陷票）,随机后果只能走随机态直写或跳写两档。

### 1.3 写入入口归属：op 上报动作，game state 独占写逻辑态（硬规则）

- **动作 op 的职责边界** = 执行画面动作（点击/拖拽）+ **机械执行后直调自己的上报函数**（动作语义单一源 = `kernel/cw_action_report/` 上报函数族，每动作一文件一函数 `report_action_<snake>_param`；零写动作族集中在 `zero_writes.py`）。逻辑态的更新写入由上报函数族独占完成（函数内 `gs.write_logic`，kernel → 状态容器单向依赖）；dict 确认族到账效果经 `kernel/cw_exec_state.py::apply_confirm_effect`（§1.5 表）。
- **禁令**：op 层/策略层不得自带逻辑态记账函数或并行登记路径——同一动作存在两条写逻辑态的通道是账实分离类缺陷的温床。执行遥测计数（次数/金额/证据留档）不属逻辑态,不受本条约束,但不得反向写状态容器。
- **逐动作计算规则的梳理文档** = [logic-updates/](logic-updates/README.md)（总-分结构：总览 + 每动作 op 一篇,说明该动作的逻辑态应如何计算）;本篇保留总则与原则,分篇逐节指向子目录。

### 1.4 kernel 单一源指针纪律

- **规则已实现**：本篇只写语义 + 指向 kernel 函数（符号名引用）；数值只写常量名，不复制数值（值的单一源在代码）。本篇被指对象：`kernel/cw_merge_simulate.py::merge_buy_k` / `merge_buy_completes` / `_merge_bench` / `_apply_full_bench_merge_buy` / `same_star_count`；`kernel/cw_economy.py::sell_refund` / `bench_char_cost` / `xp_apply_clicks` / `xp_click_cost` / `clicks_to_next_level` / `blood_xp_full_clicks`；`kernel/cw_action_report/` 上报函数族（每动作一文件 `report_action_<snake>_param`，零写族 `zero_writes.py`；刷新计数 = 效果账本 `record_refresh` 唯一入口，经刷新上报函数触发，`kernel/cw_effect_inventory.py`）与 `kernel/cw_game_state.py::detect_merge_upgrade`；`kernel/cw_exec_state.py::apply_confirm_effect`（dict 确认族）；上报写入方 = `kernel/cw_action_report/tool_use.py` 七具名上报函数（工具七类状态容器直写；登记表 `EQUIP_WRITE_SIDES` 保留）；`kernel/cw_effect_inventory.py::spawn_equip_bench_unit` / `grant_equip_item` / `transform_equip_to_privilege` / `transform_worn_equip_to_privilege`。
- **规则未实现**（无 kernel 代码写入口）：**本篇该节即实现规格**——实现时按本节规则写入代码，不另立规格文档。
- 同一规则多载体若漂移，以 kernel 单一源为准修齐（`kernel/cw_merge_simulate.py` 模块头注）。

### 1.5 逻辑态的三个落点（载体）

同一套规则按宿主分落点写入代码；本篇按动作写规则一次，在用落点同规则消费：

| 落点 | 宿主 | 写入口（符号名引用） | 消费方 |
|---|---|---|---|
| 状态容器逻辑态直写 | `GameState` 字段（渠道 family='logic_action'） | 上报函数族 `kernel/cw_action_report/<snake>.py::report_action_<snake>_param`（每动作一函数、商店/备战两域统一；快照与升星分支内聚于买牌函数单点；备战金账与库存分支内聚于各函数 `session` 形参面；零写族 = `zero_writes.py`；dict 确认族 = `apply_confirm_effect`） | 动作 op 机械执行后直调自己的上报函数（sim 与实机同一段 op 代码同口直调——驱动反转后无独立引擎委托入口，旧 `cw_sim_actions.apply_player_action` 委托串已随自驱动引擎停用）；商店序列驱动器（`bridge.py::decide_shop_screen`，回放/既有序列测试消费面）逐动作直调；以实际观察为准修正 |
| （席位平行账已停用） | — | — | 席位真值单账 = 主域字段（bench/deployed）,动作落地由上报函数直写主域;平行账与执行器同步分支已停用,对账唯一发生点 = 观察边界（见 screen_op §2.3/§4） |

(sim 整帧副本单步应用器 `simulate` 及其宿主推演帧已随 sim 帧通道停用删除——sim 与实机共用状态容器逻辑态直写落点（首行）,考古归 git;语义验证 = 投影测试(`kernel/cw_action_report/test_<snake>.py` 按被测方法拆分)。)

视觉域动作的状态容器面（黑板帧停用后直写状态容器）：晶矿/箱/典籍
的状态容器分支已进各自上报函数（CollectOre 精确摘晶矿 = `report_action_collect_ore_param` /
OpenTome·OpenBookcard 腾位 = `report_action_open_tome_param`/`report_action_open_bookcard_param`，§3.4-§3.7）；`PrepObservation`（`kernel/cw_prep_actions.py`）
降级为备战环 op 局部控制信号载体（shop_open/substate/event_overlay），不再是
策略器输入，黑板宿主 `gs.prep_obs`/`session.prep_obs_frame` 已停用删除。
WearEquip/工具原子/OpenBox 的装备域状态容器分支 = 状态容器零写（消费真值归观察的权威版本申报，
§3.4/§3A；发射帧独占零中间窗口，下一入口完整观察(全量识别)覆盖）。

### 1.6 枚举范围与动作计数

本篇枚举 = 商店域 6 个动作词条（§2）+ 备战域原子动作（§3：DeployMove/SellDeployed/LevelUp/OpenBox/OpenTome/CollectOre/OpenBookcard + §3A WearEquip 与工具原子类，规则见 §4）+ 转场类 2 个（§5）+ 动作类型清单完备性注 2 条（§2.7）。事件线选择（pick 族，含武装箱四选一画面 op）按 §6 声明为非逻辑态通道。动作类型清单本体与执行载体表 = [action_exec.md](../flow/action_exec.md) §1、[screens/README](../screens/README.md) §4（能力面/策略面之分不在本篇重复）。（已证伪机制：「试用角色揭示卡」实为备战栏动画误识别，2026-09-19 用户确认撤销，禁止再建模；备注见 `cw_identity_obs` 模块注释。）

各动作条目统一形状：**动作类型清单/op → 确定面规则（逐分支）→ 随机面 → 拒绝边界（游戏拒/提案陈旧 = 零字段写操作）→ 依据**。

## 2. 商店域动作

商店域动作的字段写操作语义单一源 = 上报函数 `kernel/cw_action_report/<snake>.py::report_action_<snake>_param`（每动作一函数，逐域 `write_logic`，域覆盖全集 = gold / bench / shop / xp / level / deployed / board / equips——原 `SHOP_PROJECTION_DOMAINS` 登记常量已随死代码清偿移除,域集由上报函数族承载）；买牌的买前快照与合成升星分支内聚于 `report_action_buy_card_param` 单点（快照函数内第一时间取），投影测试（`kernel/cw_action_report/test_<snake>.py` 按被测方法拆分）。商店域 op 载体 = `operations/cw_op/cw_<action>_action.py::CwAction<Action>Op`（一 op 一文件，op 内机械执行后直调自己的上报函数）。

### 2.1 BuyCard（买牌）

op = `operations/cw_op/cw_buy_card_action.py::CwActionBuyCardOp`（非终结）。动作类型清单条目 = `kernel/cw_vocab.py::CwActionBuyCardParam`。

**确定面**（按买入落点分支，两分支共用应用机器）：

1. **常态分支（备战席有空槽）**：
   - 新单位落备战席**首个空槽**（`bench_place`，槽号归一 = 下标+1）；
   - gold −= 牌单价 × 购买张数 k（常态 k=1；金账全款，无打包价——自动多买也无价格优惠，`research/merge_mechanics.md` §2.5）；
   - 商店载荷：被买槽 kind 置 empty（**留空不紧缩**——买后右邻槽像素零变化实证，`research/economy.md` §2.1；同 (name, star) 匹配槽对前 k 个置换，三态定长模型）；
   - **全场合成连锁**：买入后同名同星计数（备战∪场上，`same_star_count`）≥3 即升星，落点 = 场上那张的位置（装备/站位随之继承）或全在备战栏时最左一张的位置；连锁可多级（2★ 产物再凑 3 → 3★）；三只身上的装备**全部**继承到产物（`kernel/cw_merge_simulate.py::_merge_bench` 不动点循环；装备继承 = 玩家定案，merge_simulate 模块头规则 4）；升星触发时 deployed 视图整值替换 + board 重算随写（值签名变化才写）。升星触发判定单一源 = `kernel/cw_game_state.py::detect_merge_upgrade`（同名最高星抬升）。
   - 买牌不产经验（XP 域零写；零购买子集反证，`research/xp-rules.md` §2）。
2. **满栏例外分支（备战席满）**：满栏仍买得进当且仅当本次点击能完成一次合成（判据单一源 = `merge_buy_completes`，前提门 = 已有同名同星素材 ≥1；own=0 满栏域游戏拒买，/）。一击多买张数 k = `merge_buy_k` = min(店内同名同星张数, 3 − 已有数 mod 3)（绝不多买，`research/merge_mechanics.md` §2.5）；k 张逐张原价扣金（总价 = k×单价）、店载荷下架 k 张同身份牌、合成腾槽（应用机器 = `_apply_full_bench_merge_buy`，主域直写单一源）。执行器张数回执 = `CwActionBuyCardOp` 的 `merge_buy_k` 现算，执行账补差 (k−1)×单价。

**随机面**：商店直出 2★/3★ 的概率与出现（星级经费用徽章倍数反推，识别面不进逻辑态）；买入触发合成后画面上的升星动画（~1s，`research/screen_flow_timing.md` #8b）。

**拒绝边界**：满栏且合成不可达 = 游戏拒买（applied=False + reason='bench_full'，零写——金不扣、牌不下架）；提案 expect 失配（SellBench 族语义，买牌无此域）。

**知识缺口（fallback 申报）**：非满栏时一次点击恒买 1 张是**框架推论**，未实测（fields.md §4.2 BuyCard 行同款标注，详 §7「非满栏一击张数」行）。缺口闭合前按 k=1 记账；若买后观察发现多张，对账纠偏 + 缺陷记录表暴露。

**依据**：`research/merge_mechanics.md` §1/§2/§2.5/§2.6/§3；`kernel/cw_action_report/buy_card.py::report_action_buy_card_param`（简单落位 + 合成升星分支内聚单点）；`kernel/cw_merge_simulate.py` 合成规则族；主域席位单账（bench/deployed 上报函数直写）；`operations/cw_op/cw_buy_card_action.py::CwActionBuyCardOp`；`fields.md` §4.2 BuyCard。

### 2.2 RefreshShop（刷新商店）

op = `operations/cw_op/cw_refresh_shop_action.py::CwActionRefreshShopOp`（**访问终结**：刷新是唯一引入新事实的动作，执行即本访问结束返回主循环，下一访问入口观察重建期望态）。

**确定面**：

- gold −= 实付刷新费。刷价真值 = 状态容器 `shop_refresh_cost`（备战帧现场 OCR，观察通道；缺读 = 建模基价 `REFRESH_COST_BASE` 显式缺省，`kernel/cw_economy.py::refresh_cost_effective`）。免费帧（paid=0）金域不写（付费域纯净性，fields.md §3.3.4）。
- 计数组（效果账本统一计算）：`refresh_total` 恒 +1；付费帧 `refresh_paid` +1(免费帧不进);免费余额扣减 = 状态容器字段 `free_refresh_left` Field 免费分支（写入方 = 上报函数 `report_action_refresh_shop_param` 唯一入口;fields.md 商店免费刷新节）。
- 修饰分支（注册表口径）：免费刷新来源（概率事件 / 按节点免费额度）只影响实付金，不改「整店全换」;按刷产经验（淘金客，`xp_per_refresh`）效果声明已登记,刷新侧经验逻辑写分支未接入调用（零写入方）,经验真值归观察。

**随机面**：刷新后的牌面 = 整店 5 槽全换（非逐槽补空，实机实证 `research/economy.md` §2.1）→ **随机态分支写入**：上报函数经 kernel 发牌采样器采样后走 `write_logic_rand` 随机态通道写商店载荷（观察覆盖差异 = 预期内,真值 = 下一入口观察）。UI 陷阱已登记：面板右下「刷新金币数」区域实际印的是利息徽标不是刷价（三流比对已定案，`REFRESH_COST_BASE` 注）。

**依据**：`research/economy.md` §2/§2.1；`kernel/cw_economy.py::REFRESH_COST_BASE`；`fields.md` 商店免费刷新节；[shop.md](../screens/shop.md) §5（刷新 = 访问终结）。

### 2.3 CloseShop（关商店）

op = `operations/cw_op/cw_close_shop_action.py::CwActionCloseShopOp`（执行位 = 真机械点击「按钮-收起」+ 幂等已关出口 + 自上报清场;原编排壳 `CwOpCloseShop` 已随执行位并入而停用删除;**访问终结**，恒可用）。

**确定面**：shop 域**结构离屏**（上报函数 `report_action_close_shop_param` = `leave_screen(bs.shop)`，载荷语义失效）；其余域零写。**关店本身不改牌面事实**：节点内关店→重开不刷新（牌面持久），跨节点才自动刷新全店（`research/economy.md` §2.1）——牌面去留由节点推进事件确认，不由本动作推算。

**随机面**：无。

**依据**：`kernel/cw_action_report/close_shop.py::report_action_close_shop_param`；`research/economy.md` §2.1；`research/screen_flow_timing.md` #15（收起 ~1s 过场）；[screens/README](../screens/README.md) §6（终结语义总表）。

### 2.4 SellBench（卖备战席角色）

op = `operations/cw_op/cw_prep_sell_bench_action.py::CwActionSellBenchOp`（动作类型清单摊平后商店/备战共用清单单一注册行，备战 op 即唯一活执行路径；原商店域文件 `cw_sell_bench_action.py` 已停用删除，能力面语义由上报函数 `report_action_sell_bench_param` 保留，先例见 [screens/README](../screens/README.md) §5；原执行器薄委托 `prep_actions.py::PrepActionExecutor._sell_bench` 已随死代码清偿移除,执行 = op 直执行 + 自上报,备战访问侧经注册表 `action_op_for` 分派）。坐标系 = `bench_idx` 槽位表下标直取（清单摊平统一，零换算；原两套槽位口径的二分随两域统一消亡）。

**确定面**：

1. 备战席该槽位清空（kind → `empty` **不移位**，槽位语义；跨动作组下标恒稳）；
2. gold += 退款，公式单一源 = `kernel/cw_economy.py::sell_refund`：退款 = 招募费（`bench_char_cost`，注册表单一源，未知按中位保守估）× 星级倍数表 `_SELL_MULT`（星级倍数 = 合成副本数结构：1★=全额，2★/3★/4★ = `star_base_copies` 同构倍数）；**手续费口径**：star≥2 且 cost≥2 再 −1；cost=1 豁免（2★1费 卖出=全额倍数，live 实测定案，`sell_refund` 注 + `research/economy.md` §3）；3★/4★ 的手续费档 = 推测待 live 核（§7「手续费精确值」行）；
3. **装备全量回装备区**：被卖单位身上的全部装备（简易/进阶/核心不分）进入 owned 装备库存——穿戴是可逆暂借（【口述·权威】`research/equipment_mechanics.md` §1「卖出角色=装备全量回装备区」；kernel 按装备守恒约束回收建模，`cw_vocab.py` 卖出分支注；实机帧级证据未采 = §7「装备去向」行）；equips 回收统一落上报函数（`report_action_sell_bench_param` 装备守恒分支——原「商店分支有/备战域缺口」的不对称随两域统一补齐）；
4. 陈旧提案拒：expect 身份与槽内不符 = 零写。
5. **溢出条件分支**（2026-09-15 实机建档 [prep.md 告警节](../../../../../game/screens/currency_war_prep.md)）：`overflow_warning` 在场（备战席满告警横幅 = 存在未安置溢出角色，此刻出战点击被游戏忽略）时，卖出语义补一条——**腾出槽当帧记溢出卡入位**（`bench[i] := 溢出卡`，「卖 → 溢出卡自动入自由槽」是游戏侧行为；有溢出时席必满、自由槽恒唯一，落位无歧义）+ `overflow_card` 消费清空 + 旗标 logic 消亡（下帧实读覆盖，两态制以实际观察为准）。入位对象身份缺读（`overflow_card=''`）= 跳过入位（槽留空等观察），卖出语义本体不受阻；星级缺读按 1 兜底。状态容器字段 = `overflow_warning: bool` / `overflow_card: str`（观察写入方 = `cw_screen_prep` 备战完整观察(全量识别)的溢出观察写入方，渠道①）；策略消费门 = mandate 溢出门（flag 在场 → 本帧决策强收窄单动作 SellBench，禁发 StartBattle/冻结买面）。**单账同帧**：入位卡回占槽位由本写入口直接落主域 bench（席空数派生自然不 +1，腾出槽即刻回占）。（原第三面「黑板帧镜像」已随黑板帧停用删除,镜像语义由状态容器回占面全量承载。）

**随机面**：无（卖价修饰效果 = 大裁员/降本增效的卖价 ×2，其作用口径待实证 = §7「卖价修饰」行，缺口闭合前不写修饰分支）。

**回金唯一写入位置** = 上报函数（`report_action_sell_bench_param` 按 `sell_refund` 直写金账）；执行缝金差已退役（executor-gold-delta-retire 批，原 `_executed_gold_delta` 证据分支随批删除）——金归属证据 = journal 写行归因（`sig.actor` + gold 写行 prov evidence）+ 账实对账告警（`[cw!][alarm][gold_delta]`，生产者 = 备战帧账实对比）；身份不可辨 = None 诚实缺失，禁保守估值假账。

**依据**：`research/economy.md` §3；`kernel/cw_economy.py::sell_refund`/`bench_char_cost`；`kernel/cw_action_report/sell_bench.py::report_action_sell_bench_param`（双域统一单点：置 empty + 回金 + 装备回收 + 溢出分支）；`research/equipment_mechanics.md` §1。

### 2.5 LevelUp（买经验）

op = `operations/cw_op/cw_prep_level_up_action.py::CwActionLevelUpOp`（单击「购买经验」；原商店域文件 `cw_level_up_action.py` 已停用删除；原 LevelUpShop 同字段双类型已随 2026-10-17 迭代 T-4 词表退役删除，单类型单 op）。机制依据 = `research/xp-rules.md` §2。

**确定面**：

- 单击 = +`XP_PER_BUY` 经验、−单击价；攒满当前级门槛即升级、溢出结转（推进算子单一源 = `kernel/cw_economy.py::xp_apply_clicks`；门槛表 = `XP_TO_NEXT_LEVEL`）；
- 满（`MAX_PLAYER_LEVEL`）级点击无效 = 拒（applied=False + reason='level_cap'，零写——零金零经验，行为由投影测试（`kernel/cw_action_report/test_level_up.py`）钉住）；
- 单击价单一源 = `kernel/cw_economy.py::xp_click_cost` 两支语义：**显示价支**（状态容器 `level_up_cost` 观察价直通——游戏侧已算好全部折扣）/**兜底支**（基价 `XP_CLICK_COST_FALLBACK` 减已登记折扣效果；折扣只降价不减经验，`xp-rules.md` §2）；
- 金：gold −= 单击价 × 实击数（击数 = 执行回执 `ShopActionExecuted.levelup_clicks`；缺回执 = 本轮不写逻辑态，等观察覆盖）；
- 经验域写入 = `(当前级已攒, XP_TO_NEXT_LEVEL[新级])`；level 升档直写（2026-09-18 扩域,域覆盖含 level（域集全集见 §2 头注,原 `SHOP_PROJECTION_DOMAINS` 登记常量已随死代码清偿移除）；跳写对 (level, xp) 同进退——任一未读则推进对整体跳写）。

**随机面**：无。**修饰效果副作用**：商业间谍「升级时刷新商店并偷最贵 3 张」**已建模**（2026-10-17 迭代 T-3,2026-11-04 迭代 T-432 收尾:升级值变更回调置随机态信号 + sim 状态副本分支抽 5 偷 3,EffectSpec 300201;写端 = `cw_levelup_callbacks.on_level_up_change`,源 = 任意经验来源升级;状态容器 shop 状态容器域零直写,实机状态副本(GameState)后果归游戏引擎）;晋升名额「随机一槽变高费」= 未建模,后果归观察（§7「晋升名额副作用」行）。

**依据**：`research/xp-rules.md` §2；`kernel/cw_economy.py::xp_apply_clicks`/`xp_click_cost`/`XP_PER_BUY`/`XP_TO_NEXT_LEVEL`；`kernel/cw_action_report/level_up.py::report_action_level_up_param`；`fields.md` §4.2 LevelUp。

### 2.6 CompTransaction（整档替换事务·已停用）

**已整档停用**：动作类型清单行与 op 文件（`cw_comp_transaction_action.py`）删除，注册表模块头注销登记；前身上报载体 = 上报函数族拆分前的 `apply_shop_action_logic` CompTransaction 分支（已删除，考古归 git）。

历史语义留档（供考古对照）：**拒 = 整批零写，应用后无半档残留**（整批原子性不变量）；应用序 = 卖出 → 部署源清槽 → 下场（deployed 置 None + `bench_place` 放回）→ 上场（排/槽归一 + `deployed_place` 落槽）→ 填位（bench 源按后置槽位表解析；shop 源 = 买后即上）——顺序保证 bench 满时保留件不被静默丢弃（单位守恒）；汇总 gold = −fill_cost + income，携 income/fill_cost 出参。现行整档替换意图由策略器拆发原子动作序列承载。

### 2.7 动作类型清单完备性注：SellDeployed / SwapDeploy 的商店逻辑态直写分支

- **SellDeployed**（卖上阵）：上报函数 `report_action_sell_deployed_param` 在用（v2 动作族，双域统一单点），生产商店 op 表未收录（策略面由备战域承担，§3.2 主述）。规则与 §3.2 同一条。
- **SwapDeploy**（上阵↔备战对调）：动作类型清单 + 状态容器逻辑态直写 + sim 消费在用，**生产执行器未接入调用**（备战域部署换位经部署机拖拽承载）。逻辑态（规则已登记，供接入调用/sim 消费）：deployed 下标 di 与 bench 下标 bi **原槽对调**（置空不移位坐标系）；上场者继承下场者的排（含开拓者形态归一）；board 重算；同名同星已在场其余位 = 拒（`duplicate_on_board`）；expect 双侧失配 = 陈旧提案拒。装备随人走（对象迁移）。依据：`kernel/cw_action_report/swap_deploy.py::report_action_swap_deploy_param` + 上报函数 SwapDeploy 分支(代际校验 + 同名唯一性)。

## 3. 备战域动作（原子动作类型）

备战域动作类型清单 = `kernel/cw_vocab.py::CW_ACTION_TYPES` 备战域子集；执行器 = `prep_actions.py::PrepActionExecutor`（机械执行，发出即职责完成，落地判定归观察对账）。字段写操作语义单一源 = 各动作的上报函数 `kernel/cw_action_report/<snake>.py::report_action_<snake>_param`（写域申报面 = 各函数 docstring；金账/库存分支内聚于函数 `session` 形参面；零写动作族 = `zero_writes.py` 集中申报）；dict 确认族到账 = `kernel/cw_exec_state.py::apply_confirm_effect`。slot 语义 = 清单摊平后统一为槽位表下标（原生 `BenchSlot` 形态，零换算；历史「备战栏物理槽位 1-9」口径随两域统一消亡）。

**动作发出形态（原子通路）**：决策核逐帧发原子动作（部署 = DeployMove 序 / 穿戴 = WearEquip 序 / 工具 = 各消耗品原子类 / 卖出 = SellBench/SellDeployed），备战环逐帧执行决策输出的恰一个动作（None = 本帧无动作，返回主循环重新观察）；组合壳（RunDeploy/RunEquip/RunTools）不再是生产的动作发出形态（类与登记行已删除）。动作发出点计划构造单一源 = `strategies/impl/mandate_v1/deploy_plan.py::deploy_plan_moves`（部署：选人 `select_deployments` + 落位策略 `deploy_row_pref`/`deploy_slot_plans`——排 = 阵容站位覆盖 > 注册表 `position_pref` 派生 > back 兜底，前排保证随迁，槽位按状态容器行列现值自定，后排上限 = `back_layout` 现值；出战链经 `battle_chain_deploy_params` 共用同源）、`kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`（穿戴）、`kernel/cw_equip_env.py::evaluate_tool_actions`+`admitted_tool_actions`（工具 G1 准入,即代码侧动作发出点准入门）、`kernel/cw_prep_actions.py::select_ore_clicks`（采晶矿载荷）。

### 3.1 DeployMove（备战席 → 上阵单步拖拽）

**确定面**：

1. 备战席 `from_slot` 槽位清空（kind → `empty` 不移位）；目标单位对象整体迁移（身份/星级/装备随人走），落 `to_row` 排的 `to_slot`（载荷 `(to_row, to_slot)` 直指——排内 1 基槽号内联换算定子表下标；目标槽空 = 放置、有人 = 交换，被占位单位回源槽）；
2. board 羁绊计数重算：按上场单位的羁绊标签全集（`unit_bond_tags`——星徽/卡带贡献在内；无标签回退阵营）随行写派生重算（行写入方挂钩 `_resync_board_delta` 自动承载，增量全集，防全量重算抹掉 OCR 真值）；
3. 上阵计数 +1（= 部署空位 deploy_vacancy −1；完整观察帧重读校准）；
4. 腾位链语境：`bench_idx` 常为开箱/开典籍腾出的槽（§3.4/§3.5 先行）。

**随机面**：无（羁绊徽章动画 ~2s、达标触发的 overlay 延迟弹出 = 画面时序，`research/screen_flow_timing.md` #10/#24，非逻辑态）。

**拒绝边界**：同名同星已在场 = 游戏拒（恒成立约束「场上同名同星 ≤1」，`research/merge_mechanics.md` §3；上报函数同名唯一性守卫 duplicate_on_board）→ 零字段写操作；目标槽被占/拖拽未落地 = 零变化，落地事实归下一帧观察。

**依据**：`kernel/cw_action_report/deploy_move.py::report_action_deploy_move_param`（bench 摘槽 + deployed 视图整值替换(载荷 `(to_row, to_slot)` 经下标定位)+ 开拓者形态归一 + board 随写）；`research/merge_mechanics.md` §3。

### 3.2 SellDeployed（卖上阵角色）

**确定面**：

1. deployed 该槽位清空（置 None 不移位）；
2. gold += `sell_refund(star, bench_char_cost)`（退款公式与手续费口径 = §2.4 同一条，单一源相同）；
3. 装备全量回装备区（同 §2.4 第 3 条：口述·权威 + 装备守恒约束建模 + §7「装备去向」行；equips 回收统一进上报函数 `report_action_sell_deployed_param` 单点）；
4. board 重算（`_recount_board`）；上阵计数 −1；
5. 拒绝边界：槽空/越界/expect 失配 = 零写。

**依据**：`kernel/cw_action_report/sell_deployed.py::report_action_sell_deployed_param`（摘槽 + board 重算 + 回金 + owned 恢复分支内聚单点）。

### 3.3 LevelUp（买经验·逐帧单击形态）

动作类型清单条目 = `kernel/cw_prep_actions.py::LevelUp`。**粒度定案**：LevelUp 是单动作意图 = **单击**「购买经验」；升 N 击 = N 帧各发一次（决策循环逐帧重组，与商店域单击形态 `cw_level_up_action` 同构先例）。原「执行器有界连点（一次发射=升完一级）」随定案停用——把「一次发射=升完一级」留在执行器与统一类单击语义冲突（cost 字段失义）且授权滞留执行层与发射面门构成双源。

**确定面**：

- 每击：+`XP_PER_BUY` 经验、−单击价（单击价单一源 = `kernel/cw_economy.py::xp_click_cost` 两支语义：显示价支状态容器 `level_up_cost` 直通 / 兜底支基价 `XP_CLICK_COST_FALLBACK` 减已登记折扣）；
- **授权/放行条件全在决策核动作发出点**（执行器授权面全删）：每帧发出前置 = kernel `clicks_to_next_level` 现算击数 > 0；花后守线（`spend_unified`，升级资金线门内联式）/经验批支付门（`xp_batch_payment_gate`，币种通式）= 动作发出点资格门链（判定单一源 = `criteria/levelup.upgrade_gate_verdict` 六道门序）；满级 = 击数 0，无授权不发出；
- **状态容器逻辑态**（上报函数 `report_action_level_up_param`）：xp/level 跨门槛推进（推进算子单一源 = `xp_apply_clicks`，单击步长；level/xp 缺读 = 域级跳写）；**deploy_cap 不写**（容量真值由观察写入方防抖读承接，`max_units` 的 cap<level 兜底规则保守承接升级增量）；
- **金分支** = 上报函数按 `action.cost`×击数直写（`report_action_level_up_param`；击数 = 执行回执 `ShopActionExecuted.levelup_clicks`，缺回执 = levelup_clicks_not_fed 拒零写；执行缝金差对 LevelUp 恒 0/已停用）；
- 经验/等级真值 = 下一帧观察经验对账族承接（XpLedger 通道单击推进 + OCR 真值 reconcile）。

**随机面**：无。**修饰效果副作用**（商业间谍/晋升名额）归观察（§7「商业间谍副作用」/「晋升名额副作用」行）。

**依据**：`prep_actions.py::PrepActionExecutor._level_up`（单击化）；`kernel/cw_economy.py::clicks_to_next_level`/`xp_apply_clicks`/`xp_click_cost`；`kernel/cw_action_report/level_up.py::report_action_level_up_param`。

### 3.4 OpenBox（开补给箱）

**腾位**（本篇用词）= 备战席占用槽位被释放、可用空槽数增加。

**确定面**：被点补给箱所在备战槽位的占位物品离席 → 槽位腾出（「开箱即腾位」，`kernel/cw_prep_actions.py::OpenBox` 注）。**状态容器 GameState 零写**（零写族申报 = `zero_writes.py::report_action_open_box_param`——终结化：本访问结束后下一入口完整观察(全量识别)覆盖，零窗口暴露）。

**随机面 / 观察面**：箱内四选一内容 = 掉落内容归观察；本动作点「开启」后**本访问结束（终结化）**——武装箱选择画面由外循环按画面分发独立画面 op 选卡（`operations/cw_screen/cw_screen_box_pick.py`，见 §6 单选族边界），备战动作类型清单无选卡动作（`PickBoxCard` 已删）。动画等待 `_OVERLAY_ANIM_WAIT_S`，弹窗就位与否交下一帧观察（`research/screen_flow_timing.md` #28）。

**拒绝边界**：画面无箱（观察-执行竞态）= 未发出，返回主循环重新观察重派。

**依据**：`kernel/cw_vocab.py::CwActionOpenBoxParam`；op 载体 = `operations/cw_op/cw_open_box_action.py::CwActionOpenBoxOp`（机械执行 + 自上报，备战访问经注册表 `action_op_for` 分派）；`kernel/cw_action_report/zero_writes.py`（上报）；`fields.md` §4.2 OpenBox。

### 3.5 OpenTome（开秘密典籍）

**确定面**：秘密典籍道具占备战席 1 槽（类补给箱；**获得时入席** = 投资策略「秘密典籍」的发放事件，属观察面非本动作）。本动作点槽一次开启（游戏侧单次点击即弹星徽四选一）→ 典籍离席腾槽 + overlay 弹出；**状态容器腾位分支**（本写入口直写）：bench 槽 kind `tome` → `empty`（OpenTome 非终结，同一次访问的后续帧晶矿谓词消费 bench 席空数存在真实窗口；陈旧提案 = 槽类型不符零写）。

**随机面 / 观察面**：四选一卡面内容归观察；选卡决策 = 星徽秘典画面 op CwScreenBookcard（板上阵营匹配），落地记录走 chosen_tome（§6 边界），本动作不选卡。

**依据**：`kernel/cw_vocab.py::CwActionOpenTomeParam`；op 载体 = `operations/cw_op/cw_open_tome_action.py::CwActionOpenTomeOp`（机械执行 + 自上报）。

### 3.6 CollectOre（点晶矿）

**随机面直写（logic-rand-sampling 迭代起,采样语义首个落地）**：坐标列表中被点的晶矿按载荷坐标**逐点顺序推演**——每点独立守卫（该点时 bench 无空位 = 晶矿留在 spheres 不摘不采,前点奖励耗席累计判）→ 独立采样（临时口径 v0:金 1–5/简易装备池/概率表抽角色,`kernel/cw_ore_reward.py` 常量面,待采集校准）→ **逐步随机态写**（spheres 摘除/抽中域采样值/未抽中域值不变标记/角色落位 + 3合1 连锁每级受影响域各落一行,board 派生随行继承随机态）。全部字段写操作 = `write_logic_rand`;观察覆盖差异 = 随机效果落地预期内（`logic_rand_outcome` 记录行）。逐动作规格权威版本 = [logic-updates/collect-ore.md](../game_state/logic-updates/collect-ore.md)。

**动作发出形态（坐标参数化机械动作）**：载荷 = 有序晶矿坐标点击列表（大晶矿优先/上界挑选归决策侧 kernel 单一源 = `kernel/cw_prep_actions.py::select_ore_clicks`，动作发出点以预算常量 `ORE_CLICK_BATCH_MAX_K` 调用）；执行器纯机械逐个点（原读屏选晶矿与批内截断半随改形停用）。

**前置谓词（席满拦截）**：bench 空闲 >0 ∨ 晶矿均不占席，才发射采晶矿（fields.md §4.2 CollectOre；席满让路门 = 策略发射面席满探针）；上报层同口径双保险（逐点守卫）。席满点占席晶矿 = 游戏侧点不动，晶矿仍在 → 下一帧观察回补、下轮再派。

**依据**：`kernel/cw_prep_actions.py::ore_click_targets_of`/`select_ore_clicks`；op 载体 = `operations/cw_op/cw_collect_ore_action.py::CwActionCollectOreOp`（原执行器薄委托 `prep_actions.py::_collect_ore` 已随死代码清偿移除）；`kernel/cw_action_report/collect_ore.py::report_action_collect_ore_param`（采样+逐步随机写单点）；`kernel/cw_ore_reward.py`（采样器常量面）；`fields.md` §4.2 CollectOre；`research/screen_flow_timing.md` #16（飞行动画 ≤2s;席满搁浅观察回补）。

### 3.7 OpenBookcard（开书册卡）

**动作类型清单条目**：`kernel/cw_vocab.py::CwActionOpenBookcardParam`（开卡归位备战清单：书册卡 = 备战席占槽道具，与补给箱/秘密典籍并列第三件；与 `CwActionOpenBoxParam`/`CwActionOpenTomeParam` 同签名，`slot: int | None`，None = 首张）。

**确定面**：书册卡道具占备战席 1 槽；点槽「开启」→ 书册卡离席腾槽 + 专家邀请函五选一弹窗弹出。**状态容器腾位分支**（本写入口直写；槽 kind = `bookcard`，不再统一降级 `supply_box`）：腾位 = 该槽 kind → `'empty'`（按 `action.slot` 定位，None = 首张；陈旧提案零写）；状态容器腾位即 `bench_free_slots` 派生 +1。

**随机面 / 观察面**：五选一卡面内容归观察；选卡决策 = 弹窗画面 op `CwScreenExpertInvite`（默认策略单一源 = `choose_expert_index` 原位，chosen_expert 落地记录 §6 边界），本动作不选卡。动画等待 `_OVERLAY_ANIM_WAIT_S`，弹窗就位与否交下一帧观察。

**动作发出形态**（用户裁定 2026-09-19 开卡时机归策略实现管）：动作发出点 = 策略器 entry ① prep 实体面卡片分支（状态容器 bench kind `'bookcard'` 触发；原备战环入口清场段 `_clear_prep_cards` 代发通道撤销）。**终结动作**（op 类 `terminal=True`，弹窗 = 新事实，返回主循环重新分发选卡；备战单次访问终结分支已随批补齐）。

**依据**：`kernel/cw_vocab.py::CwActionOpenBookcardParam`；`prep_actions.py::PrepActionExecutor._open_bookcard`（薄委托替身函数的接缝(stub seam),真实保留理由 = 单帧测试直调面 `test_prep_action_ops.py::test_open_bookcard_executor_mechanical`;src 生产面零调用,分派单一形态 = 注册表 `action_op_for`）；op 载体 = `operations/cw_op/cw_open_bookcard_action.py::CwActionOpenBookcardOp`（机械执行 + 自上报）。

## 3A. 穿装备与工具消耗（原子类）

### 3A.1 WearEquip（穿装备）

动作类型清单条目 = `kernel/cw_vocab.py::CwActionWearEquipParam`（装备库 owned 件 → 目标角色物理槽位；穿戴原子通路，RunEquip 组合壳溶解后的发射形态）。

**确定面**：

- 装备归属转移：owned 库存 −1 件（状态容器 equips 域零写——消费真值归观察的权威版本申报；WearEquip = 发射帧独占，下一入口完整观察(全量识别)装备区读数覆盖，零窗口；equips 域 = op 自上报 `report_action_wear_equip_param`（owned −1 + 目标角色 equips +1））；目标角色已穿域 +1（角色装备上限 = `EQUIP_CAPACITY`）；
- **零比对出生**：动作 op 内零 CV-diff 验穿——穿没穿归观察写入边对账（装备期望态对账族下一入口暴露）；原 avatar-slot CV-diff 验穿面随原子化删除；
- 计划构造 kernel 单一源 = `kernel/cw_equip_wear_plan.py::_build_equip_wear_plan`（决策侧逐帧现算）。

**穿着即合成**（已登记建模裁定）：两件可合成组件穿到同一角色 = 自动合成；**不记合成预期值**（fields.md §4.1 豁免），后果走观察覆盖 + 缺陷记录表——该豁免是建模裁定，不是知识缺口。

**依据**：`kernel/cw_vocab.py::CwActionWearEquipParam`；op 载体 = `operations/cw_op/cw_wear_equip_action.py::CwActionWearEquipOp`（机械执行 + 自上报；原执行器薄委托 `prep_actions.py::PrepActionExecutor._wear_equip` 已随死代码清偿移除）；`kernel/cw_equip_wear_plan.py`。

### 3A.2 工具原子类（按消耗品各立类）

清单七类（摊平后类名形 = `CwAction<Xxx>UseParam`）：`FurnaceUse`（冶金炉，双模式）/`PrivilegeCardUse`（特权赋予卡，两分支）/`WrenchUse`/`PrecisionWrenchUse`/`StaffProjectorUse`/`PerfectProjectorUse`/`LuckyTokenUse`。执行载体 = `operations/cw_op/cw_tool_use_action.py::CwActionToolUseOp`（七类共用;owned 网格内 icon → 目标机械拖曳，零消耗确认比对——原 `CwOpTools` 三态比对随原子化由观察承接，消费真值 = 下一帧装备区读数;原执行器薄委托 `prep_actions.py::PrepActionExecutor._use_tool` 已随死代码清偿移除）。逐件逻辑态规则 = §4（规则本体不变，执行载体由组合 op 换为原子类）。

## 4. 工具族逐件逻辑态（7 件）

工具类（category='工具'）7 件登记于装备注册表（`research/equipment_mechanics.md` §5 全量；不可 drag 穿，消耗交互 = owned 网格内 icon→icon 拖曳）。**逐件写入方登记单一源** = `kernel/cw_affix_effects.py::EQUIP_WRITE_SIDES`（每件恰一个代码写入方，取值清单四形：`bridge:`=写入方桥确定性直写 / `contribution:`=贡献算术零直写组合收尾 / `op:`=执行域既有写入方 / `observation`=负写入方随机面交由观察收尾）+ 逐件归属申报 `EQUIP_REWRITE_DECLARATIONS`。

**执行载体**：工具消耗 = 备战动作类型清单原子类（§3A.2，按消耗品各立类），动作发出点 = mandate_v1 entry ②′（判据单一源 = `kernel/cw_equip_env.py::evaluate_tool_actions` → `admitted_tool_actions` G1 准入〔首现注:G1 准入 = 代码侧动作发出点准入门,拒因键 `g1_not_admitted`〕，本层禁第二套时机判断），机械半 = `cw_tool_use_action.py::CwActionToolUseOp`（经 `prep_actions.py` 机械原语 `_owned_grid_locate` 定位）。原组合 op 载体（`CwOpTools`，含消耗确认比对）随原子化停用。

**分档结构**（执行接入调用 = 哪个执行面消费本件规则）：

- **档 1（判据准入放行，原子类发射）**：冶金炉（→`FurnaceUse`，furnace_single）、特权赋予卡（→`PrivilegeCardUse`，privilege_upgrade）；
- **档 2（判据面 fail-closed〔首现注:fail-closed = 判据缺失或不可判时取不动作的保守分支〕，类随族立档、动作发出点禁无判据发出）**：拆装扳手（→`WrenchUse`）、精密拆装扳手（→`PrecisionWrenchUse`）、员工投影仪（→`StaffProjectorUse`）、完美投影仪（→`PerfectProjectorUse`）、好运令牌（→`LuckyTokenUse`）——判据面拒因细分键已登记（dest_unready/cold_start_later/rc_missing）；其中员工投影仪/完美投影仪/好运令牌的 kernel 写入方桥已备（接入调用 = 桥调用），拆装扳手走执行域既有装备转移链。

**通用边界**：工具消耗品 −1 与目标件消失 = **状态容器零写**（消费真值归观察——装备域下一帧读数覆盖；工具原子 = 发射帧独占类，无中间窗口）；消耗确认三态比对随原子化停用（消费真值归观察）。首件消费后画面网格重排（reflow）→ 工具原子 = 发射帧独占类（后续网格目标动作下帧重评）。装备获得固定入栏序（第 1 排消耗品从右往左、装备区先右列后左列，`research/equipment_mechanics.md` §5）= 观察剪枝知识，不进逻辑态。

### 4.1 冶金炉（装备目标·档 1 已接）

- **炉·装备分支**（拖到一件装备 icon）：确定面 = 工具 −1、原装备件从库存消失；**变异产物** = 同类型随机装备 = 随机面 → 负写入方 observation（`EQUIP_WRITE_SIDES['冶金炉']`），产物名归下一帧装备区读数。
- **炉·角色分支**（拖到角色）：确定面 = 该角色全部装备（≤`EQUIP_CAPACITY`）从穿戴域移除归入库存域；**随机面** = 每件各自变为同类型随机装备 → 交由观察收尾。期望口径已证：产物「有无放回」对决策不敏感、k=3 角色用法首中期望已登记（proofs/p14 定理 2/Q2、proofs/p50）——决策表不依赖产物分布，故随机面豁免无决策代价。
- 依据：`research/equipment_mechanics.md` §5 冶金炉行 +「冶金炉回收流水线」节；`EQUIP_REWRITE_DECLARATIONS['冶金炉']`；`operations/cw_op/cw_op_tools.py::plan_tool_drags` furnace_single 分支（目标 = 死库存件 `recycle_qualified` 命中，禁「画面可读首件」宽取）。

### 4.2 特权赋予卡（装备目标·档 1 已接）

- **库存分支**（拖到一件进阶装备 icon）：**确定性变换** = 该件名替换为对应 ·特权 装备名（映射 = `kernel/cw_effect_inventory.py::privilege_counterpart`，进阶↔特权全量双射由测试钉死）；写入方 = `transform_equip_to_privilege`（库存中该名单件替换，数量守恒）。零写分支：库存未观察 / 无此件 → 跳写留观察。
- **穿域分支**（拖到角色）：该角色已穿**进阶**装备随机一件变特权——「哪件被选」= 随机面 → 即使执行接入调用，逻辑态只写**选定后确定面**（选定件 → 特权名，桥 = `transform_worn_equip_to_privilege`）；游戏自选形态交由观察收尾。在用执行臂只消费库存分支。
- 依据：`EQUIP_REWRITE_DECLARATIONS['特权赋予卡']`；上报写入方 = `kernel/cw_action_report/tool_use.py` 七具名上报函数（特权化两分支段 = `report_action_privilege_card_use_param`）。

### 4.3 拆装扳手（角色目标·档 2 未接）

**逻辑态规则（本节即实现规格）**：目标角色的全部已穿装备移出穿戴域、**全量回装备区**（owned 库存 += 全部件名）；工具消耗品 −1（用后消失）。装备转移不可角色间直拖（拖拽无响应），转移两途径 = 卖角色或扳手（`research/equipment_mechanics.md`「装备转移机制」节）。写入方登记 = `EQUIP_WRITE_SIDES['拆装扳手']`（op 域既有装备转移链流向识别标志）。**依据**：equipment_mechanics §5 拆装扳手行、fields.md §4.2 RunTools。

### 4.4 精密拆装扳手（角色目标·档 2 未接）

- 取下全装备同 §4.3，但**不消耗**（无限次使用，工具库存面不递减）。
- **重复获得金分支**：已持精密扳手后再获得拆装扳手改 +1 金——确定面（金账 +1），写入方 = 贡献算术 `equip_wrench_duplicate_gold`，组合写收尾 = 获得回执窗 `settle_wrench_duplicate_gold`（窗口独占：获得回执 → 下一次金读数之间无其他金变更源）。
- 依据：`EQUIP_WRITE_SIDES['精密拆装扳手']`；equipment_mechanics §5。

### 4.5 员工投影仪（角色目标·档 2 未接，写入方桥已备）

**逻辑态规则**：拖到 **3 费及以下**角色（官方前置门）→ 备战席创造该角色的 1 星复制（同 char_id、零装备）；工具 −1。写入方 = 上报函数 `kernel/cw_action_report/tool_use.py::report_action_staff_projector_use_param`（费用门 ≤3 前置查,门值 3 由调用位 `cost_gate=3` 传入;原 `STAFF_PROJECTOR_COST_GATE`/`_TOOL_SPAWN_COST_GATE` 门表常量已随死代码清偿移除）→ 获得链 `kernel/cw_gain_chain.py::gain_character`（1★ 复制进席,3合1 触发随链语义;原入席桥 `spawn_equip_bench_unit` 的投影仪服务面已随 tool-gain-report 迭代收窄为拷贝仪计数分支）。**席满语义（已定案）**：备战席满 / 超费用门 / bench 未观察 = **拒落零写**（与游戏端拒拖语义同源）→ 跳写留观察——席满不是部分成功，是无落位。**随机面**：无（确定性动作）。**依据**：`EQUIP_REWRITE_DECLARATIONS['员工投影仪']`；fields.md §4.2 RunTools。

### 4.6 完美投影仪（角色目标·档 2 未接，写入方桥已备）

同 §4.5，**无费用门**（gate=0）：拖到任意角色 → 其 1 星复制入备战席首个空槽；席满/未观察 = 拒落零写。**依据**：`EQUIP_REWRITE_DECLARATIONS['完美投影仪']`；`spawn_equip_bench_unit`。

### 4.7 好运令牌（角色目标·档 2 未接，写入方桥已备）

**逻辑态规则**：拖到角色 → 从其**推荐进阶装备**中获得一件；工具 −1。**选定后确定**：选件事实（chosen_equip）已知时 = 装备库存 +1（桥 = `grant_equip_item`，非进阶类别 = 调用错；库存未观察 = 零写留观察）。**随机面 / 缺口**：候选池真实结构（效果文「四件」vs 图鉴「3+3」）待实测 = §7「定向池结构」行（proofs/p14 Q5 已登记）；选哪件 = 策略决策面，选定前无状态容器可算面。**依据**：`EQUIP_REWRITE_DECLARATIONS['好运令牌']`；equipment_mechanics §5。

## 5. 转场与观察类动作（逻辑态 = 空）

**OpenShop**（开店意图，`kernel/cw_prep_actions.py::OpenShop`，备战环终结）与 **StartBattle**（出战，备战访问终结·唯一完成态）是**转移动作**：它们只把画面从 A 转移到 B，不按游戏规则改写任何局内资源。**Obs**（环内重观察，`operations/cw_op/cw_obs_action.py::CwActionObsOp`）同类逻辑态 = 空：它的状态容器更新通道 = 宿主画面 op 的完整观察(全量识别)链重跑（观察聚合入口直写 = 观察边界对账，非动作逻辑态直写）；动作上报面零写（`zero_writes.py::report_action_obs_param` 占位）。

- **OpenShop**：状态容器逻辑态 = 空（显式声明）。开店不触发刷新（基础刷新触发只有「节点切换」+「手动」，`research/economy.md` §2.1）；开店后牌面/gold = 入口观察重建（观察面）。
- **StartBattle**：状态容器逻辑态 = 空（显式声明）。进战斗后 hp/gold/streak 全部由结算屏真值覆盖接管（op 自上报 `report_action_start_battle_param`：hp/gold/streak 零推进；败轮金按轮首补发口径，fields.md §4.2 轮首收入）。**免战牌子态**：出战按钮变「跳过」；跳过经上报即递减（`report_action_start_battle_param` 内 `consume_use`，归零移除——效果账本侧确定性维护，非 GameState 字段逻辑态）；跳过事实走声明通道（免战牌建模批：skip_substate 出口构造 `battle_skip` 声明，`next_screen` = 跳过后下一节点窗稳态屏推导 `_skip_next_screen`；常规出口 (结算屏, battle_resolve) 不变），sim 消费 = `_skip_battle`（被跳节点经验照常入账 + 状态副本直进下一节点窗、零战斗面）——「跳过后 hp/streak/收入不动」已按暂定表述建模（披露键 `cw_skip_settlement_semantics_pending` 随局申报），实机比对仍挂 §7「跳过不动」行。发射重发/连败停机 = 流程防线（[action_exec.md](../flow/action_exec.md) §7），不属逻辑态。
- **Obs**：状态容器逻辑态 = 空（显式声明；策略发射后宿主 `CwScreenPrep.reobserve_in_visit` 重跑观察链，帧代次标 full 归决策循环写入位置——方向重估触发同入口帧）。重观察见事件 overlay = 抛 `CwObsOverlayBail` 返回主循环重新分发（画面路由归外循环，环内不消化）。

依据：`kernel/cw_prep_actions.py::OpenShop`/`StartBattle`；`kernel/cw_action_report/zero_writes.py::report_action_open_shop_param`、`start_battle.py::report_action_start_battle_param` 与 `report_action_obs_param` docstring（零写/零推进申报）；`fields.md` §4.2 出战。

## 6. 事件线选择（pick 族）：非逻辑态通道边界

事件单选族（投资环境/投资策略/补给/遭遇/盛会之星/伙伴/祈愿试炼/命运卜者/骇入策划/专家邀请函/星徽秘典/**武装箱四选一**;原装备三选一随选择装备屏误判停用删除,2026-09-22）的**选择落地不进本篇动作逻辑态枚举**：选择结果由各画面 handler 单次记录到 chosen_* 字段（观察写入方记录，`kernel/cw_game_state.py::GameState` chosen_* 域组），选择**后果**默认不记预期值——选择瞬间画面即切、无定型帧可核对，后果走观察覆盖 + 缺陷记录表；有显式到账登记的照登记（已登记先例 = 专家邀请函「现金为王」gold+4）。**投资环境域例外（豁免收窄）**：投资环境的选择落地经**获得链**写状态容器（`kernel/cw_gain_chain.py::gain_invest_env`——active_env 注册/环境赠卡入席/席满溢出落位，接入点 = 动作落地时点；链式规范权威版本 = [gain-chain.md](gain-chain.md)），「选择后果默认不记预期值」的豁免对投资环境域不适用；其余单选族维持。武装箱四选一 = 独立建档画面「货币战争-备战-武装箱选择」的画面 op（`operations/cw_screen/cw_screen_box_pick.py`，选卡即终结的单选族例外；决策面 = 策略契约 `decide_box_card` / 局外 kernel `pick_equipment` 机器单一源）——它**不是备战动作类型清单成员**（原 `PickBoxCard` 动作形态已删）。依据：`fields.md` §4.2 事件选择/投资选择节；决策规格 = `../strategy-docs/13_pick_family.md`。

## 7. 知识缺口与补档清单

> 缺口只限「确定面内的参数/规则未实证」，不适用于「整条规则缺席」（规则缺席 = 本篇即实现规格，§1.4）。**缺口闭合前的统一过渡形态：该动作执行后返回主循环重新观察**（观察覆盖兜底 + 缺陷记录表暴露）——这是过渡手段，不是架构：每条缺口闭合后按其「已登记处置」列收敛为纯逻辑态直写。

| 缺口 | 波及动作 | 已登记处置（闭合前记账规则） | 补档方法 |
|---|---|---|---|---|
| 非满栏一击买牌张数（「恒 1 张」= 框架推论，零实测样本） | BuyCard | 按 k=1 记账；买后观察多张 → 对账纠偏 + 缺陷记录表 | 实机局买牌动作行 × 备战席增量对账；或停机钩子采集「非满栏一击多张」帧 |
| 满栏连升（own=0 基础星满栏连买 3 张触发合成；merge_mechanics §2.5「连升同理」自标低置信未亲见） | BuyCard（满栏例外分支） | `merge_buy_completes` own≥1 门按**拒买**实现（申报边界）；若拖动对账网实证连升可行 → 回该单一源改门 | 满栏 + 商店 3 张同牌帧采集；对账层出现「拒买但画面买成」缺陷票即触发复测 |
| sell_refund 3★/4★ 手续费精确值(−1 为推测) | SellBench / SellDeployed / CompTransaction | 退款消费按保守端(下界)组装;live 核定 = 单局复盘检查项 | 3★ 已 live 定案(2026-09-15 详情面板实测:3★2费=+17=cost×9−1 ✓,1★/2★ 同场三点全中,详 economy.md §3——4★ 档仍未核,剩余缺口收敛到 4★) |
| 卖价修饰 ×2（大裁员/降本增效）作用口径（净额 vs 基础价） | SellBench / SellDeployed | 不写修饰分支，退款按基础公式；实持效果局观察覆盖 | 持修饰效果局卖 2★ 看回金差 |
| 卖带装角色装备去向（口述·权威 = 全量回区；实机帧级证据未采） | SellBench / SellDeployed / CompTransaction | 按装备守恒约束回收建模直写（在用）；对账层认「账面 2 组件 == 画面 1 进阶」类合法态 | 卖带装单位前后装备区逐格比对（完整观察帧采集） |
| 好运令牌定向池结构（「四件」vs「3+3」）与判据面（R(c) 推荐表未采集） | 好运令牌（§4.7/§3A.2） | 判据面 fail-closed 永不进准入；`LuckyTokenUse` 类随族立档 + 动作发出点禁无判据发出，逻辑态 = 工具 −1 + 获得面按选定后确定直写 | 拖一次令牌数选项实机采集（proofs/p14 Q5）+ 判据面建模批补档 |
| 商业间谍「升级时刷新商店并偷最贵 3 张」副作用 | LevelUp（两形态）+ 任意经验来源升级（值变更回调辖域） | 升级分支只写经验/金；连锁写端 = 升级值变更回调（`cw_levelup_callbacks`）；牌面偷取后果归下一帧观察 | 持商业间谍局升级时刻前后商店牌面比对 |
| 晋升名额「买经验时随机一槽变高 1 费」副作用 | LevelUp（两形态） | 同商业间谍行（随机面归观察） | 持晋升名额局买经验前后牌面费用比对 |
| 免战牌跳过后 hp/streak/收入「不动」（暂定表述） | StartBattle（跳过子态） | 跳过无结算帧；下一备战帧观察覆盖时三字段必核对。sim 侧已按暂定表述建模（`_skip_battle` 零战斗面,披露键 `cw_skip_settlement_semantics_pending`）,证伪即改 sim 消费分支对应部分 | 免战局跳过前后三字段比对 |

（随机面类目——刷新新牌、冶金炉产物、晶矿内容、掉落金额——**不在本表**：它们受 §1.2 确定性原则约束，是原则性的观察收尾，不是待补档缺口。）
