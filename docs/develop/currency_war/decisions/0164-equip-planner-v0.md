# ADR-0164 装备组合规划器 v0(期权价值/行权判断/转型壁垒;07 号)

## Status

Accepted(2026-08-16;分配维待 live 验回收机制;expectimax v1/涌现序对拍待后续)

## Context

07 号提案诊断:装备感知端全建（read_equips/合成图 K7 闭合 7×28 零缺口），决策端是全系统最薄层——四接缝（equip_fit 比例分/decide_supply 固定优先级/箱选卡 _material_value 静态表/穿戴槽序）全是**当帧静态排序**，共同盲区：没有任何一处持有装备库存的序贯视角（不看剩余渠道/存活 comp/合成不可逆/装备跨 comp 可迁移性）。plaza 把装备定为 A8 最高杠杆（「裸装输」「1 鞋 1 风扇成型」），order_compose 是攻略作者专门写的结构化字段。

## Decision Drivers

1. 合成图 K7 闭合 → 库存状态空间极小（每局获取事件 5-15 次）—— 全系统唯一能精确求解的决策子问题：最值得优化的杠杆 × 最容易做对的模块。
2. plaza 648 亲写文本含大量装备时序行为锚（「尽早合皮靴」「风暴潮前不合小件」「三月一鞋一风扇」），可逐条转单测断言（提案判据①）。

## Considered Options

- **继续静态评分加项**（strategy/07 P1-4/P1-5/R2-20 路线）：拒绝 —— 不改变决策种类。
- **全量 expectimax + 分配回收维**：M 级且分配维依赖 live 验证拆装/回收机制；按提案三维先行。
- **v0 = 三维静态近似 + 行为锚单测**（采纳）：获取（期权价值）/合成（行权判断）/转型（重叠壁垒）。

## Decision

1. 新增 `cw_equip_planner.py`：
   - `EquipPlanner.value_of_take(item, owned, channels_left)`：组件期权价值 = 对存活 comp 的缺口边际 × 稀缺（渠道少加成）+ 未锁度 × 通用期权（versatility 先验）—— 同一组件随局面变（提案核心断言）；
   - `should_exercise(a, b, owned, urgent_power)`：行权三规则（命脉缺口→行权/通用件+战力紧急→行权/组件是他路临门→**持有**「风暴潮前不合小件」锚）+ 可解释理由；
   - `equip_overlap_matrix()`：comp×comp key_equips 价值加权 Jaccard（**派生量**从 COMP_LIBRARY 算，风暴潮 ubiquity 自动体现；15/19 comp 含它 → 高重叠对）；
   - `pivot_equip_cost(from, to, owned_advanced)`：转型装备沉没比例（0..1，消费端乘金当量与 formation_cost 同货币）。
2. 接缝映射（全部现有接缝零新建）：decide_supply/pick_box_card → value_of_take 排序；ComposeEquip → should_exercise；select_comp/maybe_pivot → 重叠矩阵/沉没成本项；全部异常回退静态规则。**本轮只落核心库不切流**（接缝消费后续按 ADR-0154 M7 同窗口灰度）。
3. 测试 6 条（提案判据①行为锚单测）：锁 target 取核心件/已齐≈0/命脉缺口行权/持有期权/重叠矩阵派生性/沉没成本。

## Consequences

- 涌现序对拍（判据②：模拟局首次合成分布 vs plaza order_compose 风暴潮 185>皮靴 60>以牙还牙甲 52）待模拟局基建；决策 diff（判据③）止损门（≈0 则不 ship）同。
- 分配维（过渡角色穿装「三月一鞋一风扇」）保守化待 live 验拆装扳手/卖人掉装机制。
- 提案原文删档；决策单一源移本 ADR。
