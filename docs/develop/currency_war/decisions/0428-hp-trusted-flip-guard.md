# ADR-0428:hp_trusted 可信位——FLIP 假帧守卫区分「沿用真值」与「100 兜底」

- 日期:2026-08-28
- 状态:accepted
- 谱系:实机两局 FLIP「应触发未触发」定位(shop 开态血量区物理遮挡 → OCR 恒空 → reconcile_hp 返回沿用真值+hp_readable=False → posture_release.flip_hit 假帧守卫全量拒绝;两局 26/26 个 P1 商店决策帧 readable=False,FLIP 唯一消费点 shop decide_prep 实机恒死)→ 最小修法落地
- 关联:ADR-0282(hp 三层对账——本位语义的母设计)、ADR-0426(release 通道本体)

## Context(为什么)

`flip_hit` 的假帧守卫原为 `if not state.hp_readable: return False`,而 `hp_readable` 把两种语义不同的 False 混为一位:①shop 开态血量区读不到,但 hp 是同轮沿用的 `session.last_hp_real` 真值(ADR-0282 对账层);②开局全无真值兜底的假 100。守卫把①也当「值不可信」拒绝,而实机所有商店决策帧恒为①(商店开态血量区被 UI 遮挡),导致 FLIP 在唯一消费点上结构性 0 触发——release 通道静默关闭,正是 ADR-0426 模块自证的「通道静默关闭是确定性缺陷」。sim 侧 hp 恒可读(readable 恒 True),该风险面 sim 完全不可见(ADR-0426 触发面 27/300 是 sim 口径)。

## Decision(逐条)

1. **GameState 新增 `hp_trusted: bool = False`**:True=hp 是可信值(真读帧,或沿用 last_hp_real 的帧);False=仅「开局全无真值兜底 100」的假值帧。默认 False=未知帧按不可信(保守)。
2. **写入端唯一=read_game_state**(reconcile_hp 调用处):按「现读非 None ∨ 对账前已有真值(`last_hp_real` 存在)」派生,与 ADR-0282 对账层的两分支一一对应;reconcile_hp 签名(二元组)不动,既有调用方/测试零波及。
3. **flip_hit 假帧守卫改 `not (state.hp_readable or state.hp_trusted)`**:沿用真值帧放行,兜底假值帧仍拒。**波及面仅此一处消费点**(全仓核查:hp_readable 其余消费面——filters.dying_band_active 濒死带收窄守卫/telemetry 记录位/discipline/battle_loop 结算读——语义均不变;dying_band 是濒死深带判据非 FLIP 类判断,且其辖域 hp≤应急带与 release 零交集,不随本批放宽)。
4. **无误触发面(构造性论证)**:兜底帧 hp=100 时,末窗投影臂 100−34=66≥25 不命中、持续臂 100<40 不成立——守卫放宽只对「hp 真值本身命中谓词带」的帧生效,假值帧两臂天然不命中。
5. **sim 行为不变声明**:hp_readable=False 的唯一写入点是实机 read_game_state;sim 帧该位恒 True → 新守卫 `readable or trusted` 在 sim 逐位等价(readable=True 短路),ADR-0426 口径触发面 27/300 构造性不变,不另跑对拍;既有 release 锁全量回归作证。

## Consequences

- 实机商店帧 FLIP 恢复可达:定位局的 r9 帧形态(hp=41 沿用真值/gold=75/boss 末窗,投影 41−34=7<25)修后必触发,release 预算 g−50=25 金解锁。
- 三层锁:hp_trusted 语义/写入端源级锁(派生式钉死)、FLIP 新行为锁(实机 r9 帧形态 fixture)、既有假帧守卫锁(兜底帧仍拒)防回归。
- 已知残留:posture_release 第三路径(slot 守卫显式注入)仍用 `hp_readable` 单位守卫,同类实机商店帧下同型收窄——但该路径需 posture.level_up+末窗+slot 空位组合,本批按最小切口不动,若实机观测其触发同样被 readable 压死再单独裁决。

## 增补(2026-08-28,W403/ADR-0431):Decision 4 论证分态重写 + hp_trusted 帧龄门

原 Decision 4 的「无误触发面」论证(兜底帧 hp=100 两臂天然不命中)**只覆盖 FALLBACK 态**。hp_trusted 引入下行守卫(ADR-0431)后,「守卫放宽无误触发」的引用必须按对账层三态分态声明:

- **VERIFIED 态**(真读且过守卫):值是物理读数,谓词命中即真实危险,不存在无误触发问题;
- **STALE 态**(同节点内沿用):帧间无战斗,值必然未变,等价于真值帧——这正是本 ADR 原本要救的 shop 开态帧,论证不变;
- **SUSPECT 态**(真读被下行守卫拒信):值是「被战斗事实否定了下行」的旧值——读低毒化方向已被守卫拦截;残留的「沿用偏高」方向,其代价即 ADR-0431 的误报账(见其 R2.4 式分析),不再享有「无误触发」论证。

同时 `hp_trusted` 派生式收紧为帧龄门:`(真读且过守卫) ∨ (had_real ∧ last_hp_real_node == 当前节点号)`。跨节点沿用帧(stale 帧龄 >1 节点)降 False——「曾存在真值 ≠ 当前可信」;帧间节点号差是「漏采了多少次战斗」的直接计数,同节点内帧间无战斗、值必然未变,不是新拍阈值而是从「可信」的物理定义读出。消费面(`hp_readable or hp_trusted` 合取)零改。
