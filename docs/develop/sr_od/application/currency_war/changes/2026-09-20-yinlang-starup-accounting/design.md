# 银狼升星记账 迭代设计（总纲）

> **承接出处**：`changes/2026-09-18-yinlang-exclusive-loop/design.md` §2.1⑤ 推广批挂账（迁入
> `kernel/cw_action_report/pick_planner.py`），外溢扩展费用档建模后自立迭代（iteration-design §1.1）。

## 0. 元信息

- **迭代目标**：用户指令「银狼升星 overlay 全面审查 + 处理」（2026-09-20）：审查确认的处理面 =
  ①`pick_planner` 上报迁移（§2.1⑤ 本体）；②费用档建模（game state match 级字段 +
  kernel 单一访问器）；③商店费用观察误记修复；④观察面 OCR 走建档 area。
- **状态**：定稿（两轮核一无前提攻击收敛：attack.md 8 条 + attack2.md 6 条全量清偿，全量同步复查通过）
- **文档清单**：无详设（单文档方案，本文件 §2 即完整设计）

## 1. 问题与动机

### 1.1 现状症状

1. **pick_planner 上报宿主错位**：发射相 = `kernel/cw_action_report/zero_writes.py`
   `report_action_pick_planner_param`（意图遥测，容器零写）；落地记账
   `apply_pick_planner_landing` 宿主 = 画面 op 文件 `operations/cw_screen/cw_screen_yinlang.py:273`
   （文件头自declared 过渡位）。违规范
   `flow/action_ops.md` §1「op 内机械执行后**直调自己的上报函数**
   （`kernel/cw_action_report/report_action_<snake>_param`，容器逻辑态单点）」。
   同构范式 = `kernel/cw_action_report/pick_invest.py` 两相 report 已在库。
2. **升费腿无牌库改变表达**：`_apply_upgrade_transform` 只有 2★→1★ 变换 + 合成级联；
   「新费档银狼刷进商店」仅代码注释申报（cw_screen_yinlang.py §2.1③ 注），无容器表达、无遥测行。
   用户口径：升费效果 = 2星变1星 + **费用上升** + **牌库改变**（2026-09-20 审查裁定）。
3. **观察面 OCR 未走建档 area**：`CwScreenYinLang.observe` 全图 OCR + 硬编码文本带
   （`CARD_TEXT_Y_LO/HI`=300/420）+ x<960 二分归左右卡。建档
   `cw_yinlang_star_up.yml` 的 `骇入选项-左卡(560,180,1030,455)`/`骇入选项-右卡(1065,180,1545,455)`
   在册未用——违项目 AGENTS §5「坐标单一真相源」。
4. **银狼LV.999 费用档零建模 → 商店观察系统性误记**：`obs/cw_observation.py::resolve_cost_star:1806`
   星级公式 = 徽章读数 ÷ 注册表原费，倍数 ∈ {1,3,9} 才认，否则 roster 兜底。升费后商店
   4费1★：4÷3 不整除 → 记 **3费1★**（`cost_source='roster_fallback'` 留证但值错）；该卡被买时
   记支出按错价 → 金账与实扣失配响停。机制依据 = 升费卡结果「变为下一个费用档的 1 星」
   （口述·权威 2026-09-18，`docs/game/currency_war/research/equipment_mechanics.md` §7）。
5. **上阵变费腿无档落行**：`kernel/cw_action_report/deploy_move.py` 变换窗（3★ 拖上场变
   下一费档 1★，银狼闭环 design §2.1A 已落）只变换星级；「费用档 +1」容器无表达。

### 1.2 基线事实（设计前代码态核实，HEAD 可复核）

- **建档/符号已改名**（commit `4b57b9f3b`；测试仓 `cfc656a7`）：画面
  `货币战争-银狼升星`（`cw_yinlang_star_up.yml`，5 area）、op 类 `CwScreenYinLang`
  （`cw_screen_yinlang.py`）、actor 遥测身份 `'CwScreenYinLang'`。
- **两相 report 范式在库**：`kernel/cw_action_report/pick_invest.py`——`EVIDENCE_OVERLAY_CLOSED`
  分相（发射相 = op 机械链发出后，意图遥测；落地相 = handler 重入裁决出口「入口锚不在 =
  overlay 已关」，应用一次）；pick 族落地时机口径 =
  `flow/action_ops.md` §2.3（「落地与否由下一轮重入的入口观察裁决」）。
- **腿型判定单源在库**：`kernel/cw_events.py::classify_planner_leg`（装备域优先，银狼专属
  10 件名单锚 longest-match；银狼闭环 design §2.1① 对抗审① 产物）。
- **池派生在 sim**：`sim/cw_sim_pool.py`——不变量派生（固定牌库
  `POOL_COPIES_PER_CARD`：1/2 费 27、3/4/5 费 9（`data/cw_shop_odds.py:33`）− 持有
  Σ3^(star−1)）；`drawable_names(gs, cost)` 档过滤 = 注册表 `ch.cost`。
  **3/4/5 费副本数相等 → 档移不改变池量，只变桶归属**。
- **随机授予效果族现状 = 零逻辑写端观察收口**：全员晋升（`cw_effect_inventory.py:727`
  apply_board_rewrite 随机分支）、人力重组再发牌面（同 :736）、晋升名额（未建模）。
  **用户机制定谳（口述·权威 2026-09-20）：随机获取角色效果的采样空间 = 剩余池对应费用档桶**。
- **同名即同档**（口述·权威 2026-09-18，记录处 = `changes/2026-09-18-yinlang-exclusive-loop/design.md` §2.0）：升费后商店只出
  新费用档、赠送单位只给该费用档，**容器内费用档不同时存在**。游戏侧正本未清偿：
  `docs/game/currency_war/research/equipment_mechanics.md` §7:162-163 仍将「升费后牌池
  费用档归属(原档还是新档)」列为待实测边角——本批档行 + 观察对账即清偿手段，
  清偿列入正本更新清单。
- **Unit 容器判据**（`cw_game_state.py` §8.2 头注）：静态属性由 char_id 查注册表派生、
  禁在 Unit 另存（防注册表双源）；动态状态才进容器。
- **费用档不可派生（必须存状态）**：升费后 4费1★ 与未升费 3费1★ 同 (char_id, star) 不同费
  ——(char_id, star, 位置) 任意纯函数推不出当前档。sim M21 的星级查表函数
  （`sim/cw_sim_special.py::SILVER_WOLF_COST_BY_STAR` {1:3,2:4,3:5}）是 2026-09-15 旧口径，
  与 2026-09-18「下一个费用档的 **1 星**」定谳矛盾（1★ 可为 4 费）——sim 域另有批修。
- **费用消费面四族**（2026-09-20 会话内 grep 清点，清点工件未入库；家族结构化以代表锚可复核）：
  **账实结算族**（`obs/cw_observation.py:1988` 观察除数、买支出 `card.cost` 链、
  `sell_refund` 消费面 `cw_action_report/sell_bench.py:100`/`sell_deployed.py:66`/
  `cw_effect_inventory.py:797`/`telemetry/schema.py:186`）、
  **估值概率族**（`cw_intention.py:386`、`strategies/impl/mandate_v1/shop.py:314`、
  `strategies/impl/mandate_v1/statefn/vopt.py:94`）、
  **sim 池族**（`sim/cw_sim_pool.py:43/:108`）、
  **静态画像族**（`cw_comps.py:507`、`cw_line_defs.py:102`、`telemetry/cw_win_features.py:99`）。
  裁决表见 §2.6。

### 1.3 根因归层

- 症状 1 = **架构层**（上报宿主违 §1 单点形态）；症状 2/4/5 = **语义层**（效果/动态状态建模缺位）；
- 症状 3 = **约定层**（坐标单一真相源）。

### 1.4 解决到哪 / 明确不解决

**解决**：症状 1–5 全部——pick_planner 两相迁移、费用档字段 + kernel 单一访问器 +
两个写端（升费腿/上阵变费腿）、观察除数修复、观察 OCR 走建档 area。

**明确不解决**（防范围外溢）：

| 项 | 排除理由 |
|---|---|
| 卖退款档口径（`cw_economy.py::sell_refund:128`/`bench_char_cost:147` 对升费银狼按起始费算） | 游戏按起始费还是当前档退**未实测**，两向皆猜——禁猜，挂实机采证账，一次卖出事件定谳后迁当前档 |
| 估值概率族传参（`refresh_prob(level, 档)`/`DISTINCT_CARDS_PER_COST[档]` 搜银狼按档） | 精度面非对账面；纯函数零改动，调用方传 `effective_cost` 即可，候策略需要时迁 |
| sim 池 `drawable_names` 过滤换访问器 + M21 旧口径修正 | sim 域独立批（池升格批/M21 合并）；本批 §2.7 定接口契约 |
| 静态画像族（cost≤2 集合、费用分布画像、telemetry 特征） | 语义 = **起始费**（入手基准），永不迁；边界在访问器 docstring 声明 |
| 随机授予采样链（全员晋升/人力重组/晋升名额） | 效果批（R9 挂账）；依赖 = 本批档字段 + 池升格批（kernel 剩余池派生），已在 §2.7 声明 |
| 池派生升格 kernel（`cw_sim_pool` → kernel 共享） | 自成小批（池升格批）；本批只保证访问器接口是它的前置 |
| resume 档重建（断线重连后档从动作历史重建） | 现 resume 面无档消费；挂 resume 链路账 |
| 飞光·映月景元变费（策略赋予型 1费景元随镜流星级 3/5 费，gameplay:75 在册） | 变费族第二成员；访问器档分支已留扩展位（§2.1），效果批/策略批辖——禁另起平行访问器 |
| 奖励球开出角色是否池驱动 | 效果批采证 |

## 2. 方案

### 2.0 总原则与定谳

- **动作 op 规范**（`flow/action_ops.md` §1）：机械执行 + 发出即记账；禁验证禁重试。
  pick 族两相 report（发射相意图遥测 / 落地相证据闩应用一次）= 族 as-built 形态
  （§2.3 pick 族旁路 + pick_invest 范例），本批把 planner 收编进同一形态。
- **两态制**：确定面 `write_logic`；随机面 `write_logic_rand` 采样链；未建模不可猜 = 留证行。
- **用户定谳三条**（2026-09-20）：overlay 观察 = **只上报选项**；动作 = **只有选哪个哪项**；
  效果腿 = 升费（2★→1★ + 档升 + 牌库变）/ 装备（入栏 + 触发获得装备后的计算函数）。
- **费用档归属判据**：动态状态进 game state，静态属性查表派生（§8.2 判据）——费用档
  不可由 (char_id, star, 位置) 派生（§1.2 反例），必须存状态；**粒度 = match 级单字段**
  （同名即同档口径 §1.2 → per-unit 冗余 + 对 99% 角色引入恒等派生快照 = 真双源）；
  口径若被实机证伪（双档共存），观察对账暴露后升级 per-unit。

### 2.1 费用档字段与 kernel 单一访问器

- **字段**：`GameState` 新增顶层 `lv999_cost_tier: Field[int]`（默认未观察 None；
  值域 {3,4,5}）。**纯逻辑态**：无观察写端，写端仅两个动作报告（§2.2 升费腿 /
  §2.5 上阵变费腿）；字段注释声明坐标系语义（当前费用档，非星级、非注册表起始费）
  与写端清单。归 `match_facts` 域（域版本 bump，`DEFAULT_GS_SCHEMA` 对应行注明），
  `cw_projection_audit.py` 登记投影审计行。
- **kernel 单一访问器**：`cw_economy.py::effective_cost(gs, char_id) -> int`，与既有
  招募费口 `bench_char_cost`（:147，**起始费**语义，不动）并排双口：
  - 银狼LV.999 → `gs.lv999_cost_tier.value`，None 归约 3（开局档语义默认，读口免
    None 分支；字段「未观察 = 未触发任何变换」）；
  - 其余角色 → 注册表 `CHARACTERS[char_id].cost`；**未注册名 → 0**（无费用语义，
    禁用于金额计算）——与并排招募费口 `bench_char_cost` 未知 → 3（退款保守估）
    分野显式声明，两口径不互借（docstring 落点）。
- **语义双轨边界（docstring 内联声明）**：`effective_cost` = 当前费用档（账实结算/
  采样空间/估值概率用）；起始费（静态画像族）**继续直读注册表 `ch.cost`，永不经本口**。
  双口径中间态挂账清单随 docstring（§2.6 表）。**档分支扩展位**：现役仅银狼LV.999
  有档分支；第二变费成员（飞光·映月：特殊 1 费景元随镜流星级 3/5 费，策略赋予型，
  gameplay:75）接入时在本口扩展成员档表，禁另起平行访问器。

### 2.2 pick_planner 迁移（两相 report，与 pick_invest 同构）

- **新建** `kernel/cw_action_report/pick_planner.py`：
  `report_action_pick_planner_param(gs, param, sig, *, leg_type='', norm_item='', evidence='')`
  - **发射相**（evidence 缺省）：意图遥测日志行，容器零写（确认未落地重走不重复）；
  - **落地相**（evidence = `EVIDENCE_OVERLAY_CLOSED`，常量自 `pick_invest.py` import，
    同族同值单一定义）：腿型分派应用一次——
    - **equip**：归一件名命中 → 装备入栏（`write_logic`）+ 获得后果链
      `apply_equip_acquire_consequence`；未解析 → 禁猜，值不变翻来源 + 留证行
      （现役形态原样迁入）；
    - **upgrade**：变换窗三态（恰一枚变换+级联 / 多枚值不变翻来源留证 / 零枚
      fail-closed 留证响停）+ **档行**：恰一枚分支且前置校验现档 < 5
      （现档 = `effective_cost(gs, '银狼LV.999')`，§2.7 唯一读口）通过后，
      变换落行后、`merge_cascade_write` 前 `write_logic(lv999_cost_tier, 现档+1)`
      （evidence=`planner_upgrade_tier`；档行与级联写域不相交，定点时序防实现分叉）——
      **牌库改变 = 档行兼任**（档即池桶归属的容器事实；不另造申报行——hacker 的
      `shop_pool_decl` 是「无容器字段」替代，本批有字段即不需要）。
      **现档 = 5 误走 upgrade 腿**（机制上 5 费升 2 星两选项皆装备，upgrade 腿不应
      出现；出现 = 识别或机制异常）→ 不写变换不写档，留证行
      （kind=`planner_upgrade_tier_ceiling`）；多枚/零枚分支档不动（留证行已证异常，
      禁在异常分支推档）；
    - **unknown**：零记账 + 留证行；**weaken**：零记账（现役原样）。
  - 腿函数（`_apply_equip_leg`/`_apply_upgrade_transform`）与常量自
    `cw_screen_yinlang.py` 原样迁入，producer 常量随迁。
  - **落地相载荷来源**：发射 param 挂画面 op 实例（`self._pick_param`，与
    `_pending_leg` 同生命周期），重入裁决出口落地相复用。
  - **op 重建边角（申报）**：确认已发后画面 op 实例重建（node 预算耗尽等）=
    载荷与证据同丢，效果腿零应用——实读失配照安灯，归 fail-closed 治理链
    （action_ops §2.1）；正常 round_wait 路径实例存活，链路闭合。
- **`cw_screen_yinlang.py` 瘦身**：删落地记账块（:263–419）；重入裁决出口改调
  `report_action_pick_planner_param(..., evidence=EVIDENCE_OVERLAY_CLOSED)`。
- **`cw_overlay_pick_action.py` PickPlannerOp**：发射上报改调新 report（参数不变，
  evidence 缺省）。
- **`zero_writes.py`**：`report_action_pick_planner_param` 委托退役（函数删除）。
- **公开符号退役**：`apply_pick_planner_landing` 删除；消费测试改走 report 落地相。
- **测试迁移面（如实申报）**：`sr-od-test/test/sr_od/application/currency_war/
  test_cw_yinlang_phase32.py` 8+ 处 `apply_pick_planner_landing` 直调改走 report
  落地相（迁移后断言零影响已逐条预演）；zero_writes 导入面（同测试 :55-57）与
  两相对照测试（:292-320）随委托退役改面；§2.5 上阵变换窗三测（:325-385）断言面
  复核 + 新增档行断言；两个新写端（`planner_upgrade_tier`/`deploy_upgrade_tier`）
  随批各补档行断言；§2.3/§2.4 观察面现役测试零消费，§2.3 随批补
  `resolve_cost_star` 纯函数用例（LV.999 档 ≠ 起始费两形态：badge=4/档=4→1★/4费、
  badge=12/档=4→2★/12费；倍数体系 3^(星级−1)）。

### 2.3 商店费用观察除数修复

- `resolve_cost_star(badge_cost, roster_cost)` 签名不变，参数语义升级并改名：
  `roster_cost` → `base_cost`（**1 星基准费 = 当前费用档**）；调用点
  （`cw_observation.py:1988`）由 `ch.cost` 改传 `effective_cost(gs, 卡名)`。
  观察读容器已有字段做换算 = 读非写，两态制合法。
- **穿线定点**：调用链 `read_shop_cards`(:1857) → `_read_once`(:1924) 作用域无
  `gs`——经 `game_state_from_ctx(ctx)` 取局容器（动作上报侧现役取口，docstring
  自declared；obs 同族另有 `game_state_of(session)` 口，本调用点无 session 形参
  不适用）；返回 None（局外/无 match）→ 维持现役 `ch.cost` 兜底（该路径本就落
  roster_fallback 留证，语义不变）。
- 效果（倍数体系 = 3^(星级−1)：1★×1 / 2★×3 / 3★×9）：升费后 badge=4 档=4 →
  1★/4费 ✓；badge=12 档=4 → 2★/12费 ✓；倍数 ∉ {1,3,9} 的
  roster_fallback 分支保留（badge 缺失/名字未识别语义不变）。
- 买支出链自动随修：`ShopCard.cost` = 徽章真值后，买卡上报支出与实扣一致。

### 2.4 观察面 OCR 走建档 area

- observe node 保持**单次全图 OCR**（贵操作只算一次），文本归属过滤从
  「y 带 + x<960 二分」改为「两卡 area rect 包含判定」——rect 经
  `screen_loader.get_area('货币战争-银狼升星', '骇入选项-左卡/右卡')` 取（坐标单一
  真相源回 yml）；area 缺失回退现役硬编码带（兜底常量模式，同 `CONFIRM` 先例）。
- `CARD_TEXT_Y_LO/HI` 常量退役（被 area 取代）；`_LEGACY_CARD_RECTS` 保留
  （点击兜底,仍被 `_card_point` 消费）。
- **rect 包含判定语义** = 文本中心点落入 area rect（先例 =
  `_anchor_hit_full_ocr` 中心点位匹配同式，cw_observation.py:1851-1852）；
  **捕获集变化申报**：旧 y 带 [300,420]（卡描述+标题）→ 卡全域 rect
  y∈[180,455]（含费用角标/星级饰件文本）——卡内文本全属该卡语义，
  `classify_planner_leg` 关键词匹配面不变；卡间间隙文本双不落，零影响。

### 2.5 上阵变费腿补档行

- `kernel/cw_action_report/deploy_move.py` 变换窗：落位单位 = (银狼LV.999, 3★) 且
  现档 < 5（现档 = `effective_cost(gs, '银狼LV.999')`，§2.7 唯一读口）→ 落场写
  （下一费档 1★）后补 `write_logic(lv999_cost_tier, 现档+1)`
  （evidence=`deploy_upgrade_tier`）；**现档 = 5 → 不触发变换，恒等搬运**
  （5 费为费用封顶，无下一档——机制推断，与「5 费升 2 星两选项都是装备」同源口径，
  [机制推断·实机候证] 标注，证伪即改）。

### 2.6 消费面迁移裁决表（双口径中间态申报）

| 消费面 | 费用语义 | 本批 | 归宿 |
|---|---|---|---|
| 商店观察除数 | 当前档 | ✅ | §2.3 |
| 买支出（card.cost） | 当前档（随观察自动正确） | ✅ | §2.3 连带 |
| 升费腿/上阵变费腿写档 | 当前档（写端） | ✅ | §2.2/§2.5 |
| 卖退款 `sell_refund`×`bench_char_cost` | 未定谳 | ❌ | 实机采证账（§1.4） |
| 估值概率族（refresh_prob/DISTINCT/POOL_COPIES 调用方传参） | 当前档 | ❌ | 估值族账（纯函数零改动） |
| sim `drawable_names`/`fixed_pool` | 当前档 | ❌ | 池升格批/M21 |
| 随机授予采样链（全员晋升/人力重组/晋升名额） | 当前档（桶归属） | ❌ | 效果批；依赖 = 档字段（本批）+ 池升格批 |
| 静态画像族（cost≤2 集合/分布画像/telemetry） | 起始费 | 永不 | 访问器 docstring 边界声明 |

### 2.7 接口与生效纪律

- **接口**：`effective_cost(gs, char_id)` = 当前费用档唯一读口（观察/结算/未来采样链
  统一走此口，禁散查 gs）；`lv999_cost_tier` 写端仅两个动作报告；
  `EVIDENCE_OVERLAY_CLOSED` 单一定义（pick_invest），pick_planner import。
  **池升格批前置契约**：kernel 剩余池派生的档过滤统一走 `effective_cost`，
  采样空间 = 对应档桶剩余池（用户定谳 口述·权威 2026-09-20）。
- **生效纪律**：改 Python 须重启项目 MCP server（项目 AGENTS §6）；实机验证窗
  按攒批纪律（改码批期不打断在跑局）。

### 2.8 关键取舍

| 取舍点 | 选定 | 放弃 | why |
|---|---|---|---|
| 档字段粒度 | match 级单字段 | per-unit 字段 | 同名即同档定谳下 per-unit 冗余，且对 99% 角色引入恒等派生快照（真双源）；证伪由观察对账暴露再升级（§2.0） |
| 档字段宿主 | game state 纯逻辑态 | 注册表多条目（广场 15061/2/3 式） | 动态状态进静态单一源 = 可变注册表毁源 / 拆条目破「名字→角色」映射与合成键 (char_id, star) |
| 费用读口 | kernel 访问器单点（cw_economy 双口并排） | 各消费点散查 gs | 防「获取费用到处过 game state」失控；起始费/当前档双语义边界内联可查 |
| 牌库改变表达 | 档行兼任 | 另造 shop_pool 申报行 | hacker 申报行是「无容器字段」替代；有字段后申报行冗余、行噪声 |
| 本批范围 | 账实一致族 + 写端 | 全量消费面迁移 | 估值/画像的逐点语义裁决未做、卖退款未定谳——未定谳面禁猜，分批挂账（§2.6） |
| 观察除数修法 | 参数语义升级（base_cost = 当前档） | badge 多除数尝试/保留 badge 原值旁路 | 隐式猜档违禁猜；旁路 = 双真相源 |
| 5 费 3★ 上场 | 恒等搬运 | 继续变换 | 费用封顶，与「5 费升 2 星两选项皆装备」同源口径；[机制推断·实机候证] |
