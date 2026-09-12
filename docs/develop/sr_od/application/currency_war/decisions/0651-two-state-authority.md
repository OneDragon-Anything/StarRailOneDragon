# ADR-0651: 字段来源两态制——废除 expect/confirm 两步机制

**裁定**(用户权威,2026-09-11):BoardState 字段来源只保留 observation(观察态)与 logic(逻辑态)两种。废除 expect/confirm 两步机制全套:预期条目表、PendingEntry 五键、confirm 转正、discard_expected。

**语义**:逻辑推算值直接写字段(logic 直写,策略器立即可读)——逻辑态的职能回归「在观察态到来之前供决策使用」。

**错误哲学**:所有逻辑态的错误都是代码 bug——推算错了修推算代码,不靠运行时挂账对账兜底。观察赢原则不变(下一帧实读覆盖 logic)。

**废除面**:cw_game_state.py expect/confirm/discard_expected/expected 条目表/PendingEntry;cw_expected_state.py 条目表簿记镜像。tracked 族 reconcile 防抖语义(star 回退防抖等)=observation 写入路径防抖,重归属而非废除。

**取代**:ADR-0644 §2 中 expect/confirm 相关行、BoardState-数据结构设计.md §2.5/§8.1-8、候裁 5(ExpectedState 归一)就此定谳=两态制下自然消解。

**简明记录**:本 ADR 按用户裁定采用简明形态(决策+理由,不再展开长篇论证链)。
