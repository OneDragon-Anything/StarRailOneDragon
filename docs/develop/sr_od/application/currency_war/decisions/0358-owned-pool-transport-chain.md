# ADR-0358: owned 穿戴池搬运链(装备持有面进决策快照)

- Status: accepted
- Date: 2026-08-27
- Deciders: W148 worker(编排者派单,自主推进模式)

## Context

W92 诊断(2026-08-25,`deep_read/W92_M2采集设计.md`):装备「攒着」的持有面对决策与遥测完全不可见——`state.equips`(owned 池)在 3,061 条 decisions 行里 **0 条非空**。根因:持有面**有读点、无写链**(`battle_prep_recognizer` 已读 `owned_equips`,`EquipAll` 每轮 `read_equips` 后只自用即弃,没有任何代码把它搬进 session / 决策 state)。win_model 的装备特征因此只剩穿戴面(`deployed[].equips`,语料 1.1% 非空,过渡期持有策略下近乎零方差)。

## Considered Options

1. **修搬运链(选)**:`EquipAll` 写 session 新字段 `last_owned_equips`(仅穿戴类,复用 `_TOOL_CATEGORIES` 过滤,读点已在、零新增识别成本),`_pseudo_state` 拷入 `st.equips`。纯观测链,不碰策略行为面。
2. 强化 deployed 穿戴采集——W92 定谳不做:穿戴稀疏是「攒给成型核心」的策略真态,不是漏采;为特征改持有策略=行为面越权。
3. 遥测侧另开快照通道——不选:decisions schema 已含 `state.equips` 字段,经既有 GameState 序列化自动携带,开新通道=双源。

## Decision

三节搬运链:

1. `cw_strategy.StrategySession` 新字段 `last_owned_equips: list[str]`(局级,默认空);
2. `EquipAll` 两条路径(M7 角色级分配 / 旧 front-only fallback)在每次 `read_equips` 后以「穿戴类 owned 名单」覆写该字段(末次读=最新持有面);
3. `default_strategy._pseudo_state` 拷 `st.equips = list(session.last_owned_equips)`。

配套(win_model M2 特征面,训练脚本侧):`owned_equip_count`(持有量)与 `prev_damage`(同 run 上一战斗行 `damage_dealt` 的 lag-1,W92 修法 C 的敌方强度代理)进训练列序。**同局 `damage_dealt` 不入特征**——它在结算才可得,作同局特征=标签泄漏;用 lag-1 规避。

## Consequences

- 持有面从「写端修复加载后的下一局」起在 decisions 遥测再生;当前历史语料中 `owned_equip_count` 为零方差列(训练侧保留列、系数自然学 0,不造假数据)。
- `key_equips_held`(W92 提议的 target_comp 命中比例特征)未落:decisions 行不携带 target_comp,训练侧不可 derive,挂账待意向遥测(W146 IntentionState)覆盖后再评估。
- 加载后首局判读锚点(W92 §4):① 首个 RunEquip 后 decisions 行 `state.equips` 非空;② `deployed[].equips` 仍可稀疏(预期内);③ 结算行 damage_dealt 非空不回退。
- 单帧锁 `test_cw_w148_owned_pool_chain.py` 锁三节(写端过滤 / 读端拷贝 / 默认态),防链再断。

## Verification

- 单帧锁 4 项通过;全量 pytest 见进度树本批记录;
- 重训(win_model M1 管线 + M2 增列,209 行 / pos=38):holdout AUC 0.940(default)/0.951(balanced),GroupKFold5 OOF 0.875±0.036,bootstrap 95%CI [0.766, 0.912]——高于 W30 基线(0.749±0.145)。
