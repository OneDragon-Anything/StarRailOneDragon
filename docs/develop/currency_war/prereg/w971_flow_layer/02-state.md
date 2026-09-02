# 02 · 局状态收编 / 黑板模式 / 字段生命周期

> W971 分篇。总纲见 [../DESIGN.md](../DESIGN.md)。

## 1. 局状态 = 收编现役 StrategySession(用户拍板)

- **不新立状态对象**:StrategySession 字段已全、消费面广(遥测/对账/sim),收编避免双源迁移风险。
- 收编内容:
  1. **消灭 ctx 信箱**:简报三件(词缀/难度/boss 序)改由观察 op 直接写 session,删除 ctx 散字段(cw_briefing_*)与「取走拷贝」段;
  2. **字段更新者白名单**:session 每个字段族声明合法更新者(op/handler 名),新增写入点 = 违反架构;
  3. **遥测/对账统一读路径**:消费 session 的口径单一源。
- 边界:session 既有字段语义不动(只收编写路径,不改字段)。
- **match 生命周期前置**(对抗轮 1 代码现实 P1 补):现役 session 在 run 首帧 handle_init 才建立——BriefingOp 直写 session 要求 **match 建立前移**(进对局即建 session,先于首帧识别);P2 实施时同步迁移,否则 BriefingOp 无写目标。
- **reconcile 双输入显式化**(对抗轮 1 代码现实 P1 补):现役 reconcile_briefing_vs_plane_intel 依赖「ctx 槽(简报侧)+ session 槽(实采侧)」双轨比对;单槽黑板化后若两输入合并会对账变自比——保留两个**来源标记不同的** session 字段(briefing_bosses vs intel_bosses)供对账,「消灭 ctx 信箱」消灭的是搬运通道,不是对账的双输入语义。
- **阶段顺序修正**(对抗轮 1 P0 采纳):ctx 信箱的**删除**不随 P2(写路径收编批)——BriefingOp 在 P3 才存在,P2 删 copy 段 = 词缀/boss 链静默断流(中性退化对拍测不出)。修正:P2 期 BriefingOp 与旧 ctx 拷贝段**双写过渡**,P3 BriefingOp 稳定后删 ctx 段。

## 2. 黑板模式:决策统一读 session(用户拍板)

- **决策接口统一读 session,取消「每画面组装 obs 子集」**:
  - `decide_prep_screen(session, config)` / `decide_shop_screen(session, config)`。
  - 观察 op 读画面 → 写 session;决策读 session 出动作;遥测/对账读 session——**session 是唯一数据总线**,无搬运、无双源。
- **为什么可行(与现役同向)**:现役 `decide_prep(state, session, config)` 已是「本轮快照 + 跨轮状态」双输入,且 state 字段自带可信位(`hp_readable/hp_trusted/gold_readable`,ADR-0491 None 化、hp 新鲜度门 last_hp_t)——黑板模式下决策统一读 session,**新鲜度位原样复用**,决策侧按位保守(现状行为不变)。
- **代价与对策**:
  - 决策输入依赖隐式化 → 总纲 §4「字段 × 写者 × 读者」清单 + 决策实现 docstring 声明消费字段族;
  - 「本轮观察 vs 历史遗留」区分 → 可信位/新鲜度门(现役机制);
  - 单线程 op 顺序执行,无并发读写问题。
- **W970 接口签名变更注记**:W970 §4.1 签名与 §4.1.2「融合 obs 组装契约」由本节取代(§4.1.2 字段来源表语义转化为「观察 op 写 session 的字段清单」,仍是迁移规格)。

## 3. session 字段生命周期(黑板模式的失效管理)

session 字段按生命周期三分类,**离开产生它的画面时,画面态字段必须清理**(否则决策读到幽灵数据,如关店后残留上一波商店牌面):

| 类 | 语义 | 例 | 清理时机 |
|---|---|---|---|
| **持久知识** | 跨画面、跨轮有效 | briefing 词缀/boss 序、**refresh_probs**(等级函数,不清理,用户口述确认)、节点台账、tracked 角色 | 局终/显式覆写 |
| **画面态** | 只属于某画面的观察结果 | 商店牌 shop_cards、刷新花费——**商店关闭时清理** | 离开画面(op 完成承诺内清理) |
| **新鲜快照** | 每轮观察覆写,带可信位 | hp/gold/board/streak(readable/trusted/None 化) | 每轮观察覆写,不删只覆盖 |

- 清理者白名单:每个画面态字段的「清理 op」与「写入 op」同进白名单,禁止第三方清。
- 现役对照:快照链「每帧新建 GameState」天然无残留;黑板化后清理从「隐式(帧新建)」变「显式(完成承诺内清理)」——CloseShopOp 承诺 = 收起点击 + 1.0s 自等 + **商店族字段清理**,三者一体。

### 3.1 白名单宿主与豁免类目(对抗轮 1 代码现实 P1 修正)

- **宿主修正**:session 宿主实为 `cw_strategy_session.py`(StrategySession ~90 字段)+ `cw_state.py`(GameState)两处——白名单全量清点以两文件为准(可脚本化生成初稿,人工复核写者指派),总纲 §4 表只列「写路径收编」主字段族。
- **决策层字段族豁免类目**(新增):决策函数私有的状态字段(v3_* 族/prep_phase/defer_count/v2_round_bought 等 ~30 个,`cw_strategy_session.py:167-293`)——**写者 = 决策接口函数本身**,判据 = 「决策私有状态 vs 观察事实」二分:观察事实字段(画面读到的)归观察 op 写;决策私有字段归决策函数写;禁止跨类混写同一字段。无此豁免,黑板化会把现存决策写路径全部判违例。
- 已知遗漏族(对抗轮 1 点名,白名单补行):deploy_cap、streak、plane/round、owned 装备(equips/last_owned_equips)、bench_full_flag、active_env/megastar_char/partner_char/active_strategies(各 overlay op 写入)、_supply_refresh_used/_encounter_refresh_used(§2.13/§2.14 的「每局 1 次」状态)、投资环境台账写者、商店波 tracked 写者、备战 enemy_difficulty 通道、cw_plane_* 第二信箱族、cw_selected_difficulty——P2 实施时全量入表。

## 4. 字段 × 写者 × 读者白名单

见总纲 §4 表(本篇与总纲 §4 同源,总纲为准;此处不重复)。纪律:新增写入点 = 违反白名单;ctx 信箱字段随 BriefingOp 落地删除。
