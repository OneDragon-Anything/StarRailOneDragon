# 池升格批(pool-kernel-promotion)迭代设计(总纲)

## 0. 元信息

- **迭代目标**:剩余牌库派生(固定牌库 − 持有)从 `sim/cw_sim_pool.py` 升格为
  kernel 共享单一源并接费用档感知,为效果批随机授予采样链(全员晋升/人力重组/
  晋升名额)提供 kernel 侧采样空间;顺手退役 sim M21 与定谳矛盾的死口径。
- **状态**:定稿(试读过;对抗报告 = 同目录 attack.md / attack2.md / attack3.md)
- **文档清单**:无详设(单文档方案,本篇即完整设计)

## 1. 问题与动机

### 1.1 现状症状(锚 = `文件::符号`,路径根 = `src/sr_od/application/currency_war/`)

1. **池派生住 sim,kernel 采样链够不着**:`sim/cw_sim_pool.py` 四函数
   (`fixed_pool`:33/`held_copies`:54/`remaining_pool`:90/`drawable_names`:100,
   私有共用体 `_remaining_and_held`:73)src 侧唯一消费方 =
   `sim/cw_sim_shop.py:43`(发牌,仅 `drawable_names` 被外部消费)。用户机制定谳
   (口述·权威 2026-09-20,记录处 = `research/economy.md` §1 随机授予采样空间
   条):**随机获取角色效果的采样空间 = 剩余池对应费用档桶**
   ——这些采样链(全员晋升/人力重组/晋升名额,效果批辖)住 kernel 上报/效果层,
   包布局约束(kernel 全域零 sim import,grep 实测):不升格,效果批只能重造
   第二份池派生 = 双源必漂移。
2. **桶归属不感知费用档**:`drawable_names` 过滤 = `CHARACTERS[name].cost == cost`
   (:109)。银狼LV.999 升费后当前档 = 4/5(`gs.lv999_cost_tier`,银狼升星记账批
   已落;读口 = `cw_economy.effective_cost`)——升费后 4 费桶抽不出银狼、3 费桶
   还在抽,sim 发牌与实机机制存在档缺口。
3. **M21 旧口径死代码**:`sim/cw_sim_special.py::SILVER_WOLF_COST_BY_STAR`(:39,
   {1★:3,2★:4,3★:5})+ `silver_wolf_effective_cost`(:45,星级×上场态双输入)
   与 2026-09-18 定谳「升费 = 变下一个费用档的 **1 星**」矛盾(1★ 可为 4 费;费用
   档 = 容器推演状态,非星级/位置可派生)。消费面:**src 侧零消费**(grep 证实,
   引擎只消费 `SILVER_WOLF_ID` 与 `planner_overlay_due`,cw_sim_engine.py:159-162);
   **测试仓有消费**(`sr-od-test/test/sr_od/application/currency_war/
   test_cw_sim_equips.py:49-55` import 两符号、:148-155 断言的正是旧口径映射表)
   ——随批退役,处置见 §2.4/§2.6。

### 1.2 基线事实(设计前代码态核实)

- 池四函数形状(§1.1 锚);副本数 `POOL_COPIES_PER_CARD`:1/2 费 27、**3/4/5 费同 9**
  (`data/cw_shop_odds.py:33`,口径出处 = `research/economy.md` §1)——档 3→4→5
  副本数不变,只有桶归属变;
- **剩余池数据结构按「名 → 剩余数」计,费用桶只在查询时现分**——档感知的
  过滤语义可以按出口拆分(§2.2),`fixed_pool` 无需引入 gs;
- `held_copies` 按**名**归并(Σ3^(star−1))——同名即同档定谳**无例外**:
  升费后全场银狼(含商店已刷新未购在架卡)一律为新费用档(口述·权威
  2026-09-18;2026-09-21 追加在架卡形态。两段记录处 =
  `docs/game/currency_war/research/equipment_mechanics.md` §7 升费边角段);
  升费变换 2★→1★ 令 held 3 份→1 份;守恒炸错(cw_sim_pool.py:82-86)跨档不误炸;
- `effective_cost(gs, char_id)` 已落地(`kernel/cw_economy.py`,银狼升星记账批;
  docstring 声明采样空间属其辖域);sim→kernel import 方向合法且现役
  (`cw_sim_pool.py:23` 即 import kernel.cw_game_state);
- 测试面基线:`sr-od-test/test/sr_od/application/currency_war/test_cw_sim_pool.py`
  (1 文件 7 测,其中 3 条直测池函数,:54/:69/:89)——迁移的等价锁载体;
  `test_cw_sim_equips.py` 消费 M21 两符号(§1.1-3);
- 装备池先例:`sim/cw_sim_equips.py::furnace_reroll`(同类别池)与工具上报
  `tool_use.py` 行内实现构成双实现、对拍锁在册——**装备池统一不在本批**(另批
  候选,本批只立角色池)。

### 1.3 根因归层

架构层(模块归属)——池是跨 sim/实机采样的共享概念,宿主放错层;症状 = 档缺口
与效果批前置缺口。

### 1.4 解决到哪 / 明确不解决

**解决**:症状 1–3(池派生 kernel 化 + 档感知双出口 + M21 死口径退役,含测试面
迁移)。

**明确不解决**(防外溢):

| 项 | 排除理由 |
|---|---|
| 装备池统一(`furnace_reroll` × `tool_use.py` 双实现) | 白名单定谳后对拍锁样本域收窄至简易/进阶内(仍绿);sim 冶金炉腿(cw_sim_engine:434 → furnace_reroll)无白名单、对特殊目标仍变异 = 与实机定谳分叉——挂账点名归装备池统一批;角色池先行验证升格形态 |
| 奖励球是否池驱动采证 | 效果批辖 |
| 策略估值族档传参(`refresh_prob` 等) | 残余半腿七处不带 gs(sell_gate:1019/shop:1165/criteria/sell:134,287,384/prep_actions:548/tool_use:479 投影仪费用门),升费银狼估价差 1 金、投影仪门判据反向——认领 = 估值族迁移账(starup §2.6 挂账清单该行「卖退款未定谳」已过时,文档卫生归该批);账实半腿已随 7b9c0d158 迁移 |
| sim 银狼升费行为建模(planner 选择后变换) | M22 planner 流辖;本批只保证「sim 若写档字段,**池出口**自动跟上」;在架卡重标半腿不归池(商店卡 cost = 发牌时快照),M22 需单列(§2.3) |
| 专家入池 U10 待核(EXPERT_COPIES_ASSUMED=9) | 维持现披露,参数透传原样;现役事实 = 生产零传参(唯一调用方 `cw_sim_engine.py:528` 不传,传参仅测试),随批如实申报 |
| sim 开局抽名点档感知迁移 | `sim/cw_sim_opening.py::_uniform_char_of_cost`(:87-93)按档抽名,现态与 kernel 档桶等价无漂移(sim 不写档);候选随 M22/效果批接线迁移,本批点名不迁 |
| 晶矿角色采样档感知 | `kernel/cw_ore_reward.py:88-92`(REFRESH_PROB 抽档 + 注册表均匀抽名,零池感知;v0 披露在册;消费 = `collect_ore.py:135`,实机/sim 同用)已落地在役,归其本批申报;本批点名不迁 |

## 2. 方案(完整设计)

### 2.0 总原则

- **搬家非重写**:函数体逐字迁入 kernel,唯一语义改造 = 档过滤(§2.2 双出口);
  守恒炸错、≥9 清空(商店出口)、专家入池透传语义原样;
- **import 方向 = sim→kernel**(合法且现役;kernel 全域零 sim import);
- 迁移前后非银狼路径行为等价,等价锁 = **现役测试原样随迁**(§2.4);
- **机械执行直接上报的邻域纪律沿用**:池是派生状态非动作,本批无上报语义;
  随机面采样(rand 采样值 + `logic_rand_outcome` 收口)由消费方(效果批)辖,
  本批只供采样空间查询。

### 2.1 kernel 新模块 `kernel/cw_pool.py`

五函数自 `sim/cw_sim_pool.py` 迁入(含私有共用体):`fixed_pool(*, extra_experts)` /
`held_copies(gs)` / `_remaining_and_held(gs, *, extra_experts)` /
`remaining_pool(gs, *, extra_experts)` / `drawable_names(gs, cost, *, extra_experts)`
(含 `EXPERT_COPIES_ASSUMED` 常量;`extra_experts` 生产零传参为现役事实,随 U10
披露保留透传)。

- **头注与 docstring 重写**(非逐字随迁):M06/U10/U11 等 changes/ 节号标记一律
  改语义表述 + 持久索引(副本数口径 = `research/economy.md` §1;常量单一源 =
  `data/cw_shop_odds.py`);**禁携带原文件的 changes/ 引用**(sim/cw_sim_pool.py
  :3-4 自引设计正本,违代码禁引 changes/ 铁律——不种进新 kernel 永久模块);
- **守恒炸错文案去层归因**:原「sim 内部 bug」改「池派生与持有约束不一致」
  (测试零断言该文本,改文案零代价);
- **守恒炸错 kernel 语义申报**(r4-F22):宿主迁 kernel 后,守恒破上抛的跨层
  后果 = 效果链 run 停(链上登记腿 best-effort 不兜容器写);实机 held 为观察
  派生,「负值不可能由合法动作产生」的 sim 论证不覆盖观测噪声——语义
  **接受**:响停修因优于静默夹零(「不存在偶发」总纲同向),非缺陷;
- **唯一语义改造**:`drawable_names` 过滤条件 `CHARACTERS[name].cost == cost` →
  `effective_cost(gs, name) == cost`(`kernel/cw_economy.py` import;档字段未观察
  = None 归约 3,非银狼角色恒等注册表值——零行为差路径);
- 其余函数零改动(`fixed_pool` 保持注册表纯派生:剩余池按名计,桶在查询时
  现分,副本数 3/4/5 同 9——档不进 `fixed_pool` 签名,gs 不入纯派生)。

### 2.2 双出口形态(档过滤与商店过滤解耦)

效果批契约空间(剩余池对应费用档桶)与商店发牌过滤**不是同一个集合**:商店
`drawable_names` = 档匹配 ∧ 剩余 >0 ∧ **held ≥9 清空**(U11 商店发牌过滤,仅
商店通道有定谳)。效果批采样是否受 ≥9 约束无定谳 → 解耦为两个命名出口:

- **`drawable_names(gs, cost, *, extra_experts)`**(商店出口,sim 发牌消费):
  档匹配 ∧ 剩余 >0 ∧ held <9——三条件语义原样;
- **`grant_bucket_names(gs, cost, *, extra_experts)`**(授予出口,新增,效果批
  消费):档匹配 ∧ 剩余 >0——**不含 ≥9 过滤**。v0 口径双维披露(均未实测):
  `grant_bucket_no_nine_filter_v0`(是否受 ≥9 清空约束)+
  `grant_bucket_uniform_by_name_v0`(**按名均匀**,非按剩余副本数加权),效果批
  消费后由 `logic_rand_outcome` 行候校准,同冶金炉采样池先例;
  **调用时序契约**(消费者侧):纯函数只吃 gs、held 仅容器派生——「先回归
  后重抽」(用户裁定 2026-09-21,invest_effects.md B 类)⇒ 消费方必须先把回归
  写落容器再采样;无工作副本派生入口,merge_step_once 范式不适用于本出口;
  **extra_experts 透传 = sim 兼容形态**:kernel 授予调用恒缺省 None(专家入池
  = 商店发牌概念 U10,「专家 ∈ 授予采样空间」无定谳,调用方禁自填);
- 两出口共用 `_remaining_and_held` 派生,单源无第二实现。

### 2.3 sim 侧

- `sim/cw_sim_pool.py` **删除**(src 侧唯一消费方 = `cw_sim_shop.py:43`,import
  直改 `kernel.cw_pool`;不留 re-export shim——单消费方,shim = 墓碑形态);
- `sim/cw_sim_special.py`:删 `SILVER_WOLF_COST_BY_STAR`(:39)与
  `silver_wolf_effective_cost`(:45-58);`SILVER_WOLF_ID`/
  `planner_overlay_due`/`trailblazer_form_of` 留守(引擎消费,cw_sim_engine.py
  :159-162/:473 不受影响);模块头注 M21 段**整段重写**:旧「星级×上场态双
  输入」模型句、「升费前商店只出基础费用档 = 池过滤器语义/池面天然只出 3 费档/
  无需额外过滤器」句、「试用角色」句(equipment_mechanics.md §7 指针失效,试用
  权威 = `docs/game/gameplay/currency_war.md`:81)一并处置——新口径 = 费用档 =
  容器推演状态(`gs.lv999_cost_tier`/`effective_cost`,2026-09-18 定谳),池桶
  归属经 `kernel.cw_pool` 档感知出口承接;
- **档透传形态申报**:sim 引擎现无 `lv999_cost_tier` 写点(grep sim/ 全域零命中;
  写端仅实机链 pick_planner/deploy_move)→ sim 运行态档恒 None 归约 3,
  两出口行为与现状一致——档感知对 sim 是无害透传;sim 将来模拟升费动作写档,
  **池出口**自动跟上;⚠️ 在架卡重标**不归池**(sim 商店卡 cost = 发牌时快照,
  cw_sim_shop.py:91-93;实机买卡透传同源)——sim 若模拟升费,在架重标是商店面
  独立腿,归 M22 申报(防漏)。

### 2.4 测试面(等价锁 = 现役测试原样随迁)

- **`test_cw_sim_pool.py`(1 文件 7 测)import 切换 `kernel.cw_pool`,测试体
  原样保留**——测试不变而全绿 = 搬家等价性的证明载体;3 条直测池函数
  (:54/:69/:89)随行;
- **档感知新增锁**:档 = 4 → `drawable_names(gs, 4)` 含银狼LV.999、
  `drawable_names(gs, 3)` 不含;档未观察(None)→ 3 费桶(归约语义);
- **双出口分野锁**:held ∈ [9,26] 的 1/2 费卡(构造形态)在 `drawable_names`
  被清空、在 `grant_bucket_names` 仍在册——两出口集合不等锁;
- **守恒跨档安全锁**:升费变换 2★→1★ 后 held 变化不炸守恒、旧档桶账面不出
  负值;
- **M21 退役改面**:`test_cw_sim_equips.py` 删两符号 import(:49-55)与旧口径
  映射断言(:148-155,断言对象 = 本批宣告矛盾的旧模型,随符号退役);
- 专家入池回归(extra_experts 透传 + 未注册名拒收);sim 发牌回归
  (`cw_sim_shop` dealing 测试族);L1 全量。

### 2.5 关键取舍

| 取舍点 | 选定 | 放弃 | why |
|---|---|---|---|
| 档感知单点 | 查询出口过滤(§2.2 双出口) | `fixed_pool` 带 gs 重分桶 | 剩余池按名计、桶查询时现分(§1.2);带 gs = 纯派生函数被容器污染,签名扩散 |
| 效果批出口 | `grant_bucket_names`(档 ∧ 剩余>0,无 ≥9,v0 披露) | 直接复用 `drawable_names` | ≥9 = 商店通道定谳,授予通道无定谳——继承 = 无据,拆出口 + outcome 校准 = 冶金炉采样池同款诚实先例 |
| sim 旧模块处置 | 删除 + 消费方直改 import | re-export shim | 单消费方;shim = 墓碑形态,项目纪律倾向删 |
| held 键 | 按「名」归并 | (名, 档) 双键 | 同名即同档定谳无例外(2026-09-21 追加在架卡),按名归并即正确,无证伪分支 |
| M21 范围 | 只退役死口径 | 重建 sim 升费模拟 | `silver_wolf_effective_cost` src 零消费;sim 升费建模 = M22/另批,缺位以档透传形态披露(§2.3) |
| 模块宿主 | 独立 `kernel/cw_pool.py` | 并入 `cw_economy` | 池 = 采样空间概念,与经济域分离;装备池统一/效果批采样同宿可期 |
| 装备池统一 | 不进本批 | 顺手统一 `furnace_reroll` 双实现 | 角色池先行验证升格形态;对拍锁样本域收窄至白名单内(仍绿);sim 冶金炉腿无白名单与实机分叉 = 装备池统一批挂账(r4-F24),非本批缺陷 |
| 等价锁载体 | 现役测试原样随迁 | 双实现并存一轮/git diff 对照 | 测试体不变而全绿 = 最强等价证明;git 对照不可脚本化入测试 |

### 2.6 文件面(全量)

`kernel/cw_pool.py`(新建)、`sim/cw_sim_pool.py`(删除)、`sim/cw_sim_shop.py`
(import)、`sim/cw_sim_special.py`(死口径退役 + 头注整段重写);
`sr-od-test/test/sr_od/application/currency_war/test_cw_sim_pool.py`(import 切换,
测试体原样)、`test_cw_sim_equips.py`(M21 两符号 import 与旧口径断言退役)、
新增授予出口测试(随 §2.4)。
