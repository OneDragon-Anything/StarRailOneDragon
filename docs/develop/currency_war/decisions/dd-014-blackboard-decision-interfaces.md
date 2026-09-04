# dd-014:黑板模式决策接口落地——decide_prep_screen/decide_shop_screen(session 签名)+ 观察写路径收编 + match 建立前移

> 类名已随 2026-09-03 命名迁移更替,对照 NAMING.md(本文为带日期决策记录,类名保持当时事实,未改)。

- Status: accepted(2026-09-02,W971 P2 实施时落;设计出处 = `prereg/w971_flow_layer/DESIGN.md[已删·git 84370361 可溯]` §2 + `02-state.md` §2/§3/§4 + W970 §4.1 amendment)
- 关联: W970 §4.1(被本 ADR 对应的 W971 §2.7 amendment 取代 obs 组装签名)、DD-011、dd-013

## 背景

P1 前决策接口是「每画面组装 obs 子集」形态:备战环步决策 `decide_prep_action(obs, session, config)`、商店 d2 决策 `decide_prep(state, session, config)`——输入由调用方逐次组装(融合段散在 shop.py/buy_cards),观察结果无单一落点;简报数据绕「ctx 信箱」(入口存 ctx → run loop 首帧 handle_init 取走拷贝),且 session 建立在 run 首帧,先于 run loop 出现的简报观察(P3 BriefingOp)将无写目标。

## 决策

1. **黑板接口**:新增 `decide_prep_screen(session, config)` / `decide_shop_screen(session, config)`——决策统一读 StrategySession,观察帧缺失即抛错(禁静默按空观察决策)。旧两接口保留为**薄委托**(旧签名 → 写 session 帧字段 → 同一决策核),调用方逐个迁移;sim 适配独立批,兼容期 `decide_prep` 输出保持逐字节等价(升级意图仍产基类 LevelUp)。
2. **观察写路径收编(第一步,双写过渡)**:备战观察结果由 `prep_director._observe` 写 `session.prep_obs_frame`;商店融合观察态由 `buy_cards.run_buy_waves` 波顶融合段写 `session.shop_state_frame`。ctx 信箱**不删**(BriefingOp P3 才存在,先删 = 词缀/boss 链断流);run loop 信箱吸收段抽为 `_absorb_ctx_mailbox` 并改无条件调用(match 前移后简报读数晚于建立点)。
3. **决策层字段族豁免**:session 决策私有字段(v3_*/v2_* 族)写者 = 决策函数本身,与观察事实字段二分(判据 = 02-state §3.1);全量清点表落 02-state §4.1/§4.2。
4. **match 建立前移**:容器建立从 run 首帧 handle_init 前移到入口链新局确凿信号处(`establish_new_match`,与 ADR-0419 残留弃置同址衔接);handle_init 建立分支保留作绕过入口链直跑 loop 的兜底,同一 helper 无逻辑分叉。
5. **LevelUp 拆 LevelUpShop**:商店屏出口产 `LevelUpShop`(cw_state,无新字段子类,is-a LevelUp)——执行器/simulate 按 isinstance 零改动;旧入口不映射(sim 等价前提)。
6. **reconcile 双输入保留**:`briefing_bosses`(简报侧)与实采侧 intel 字段语义不合并,对账双输入原样。

## Considered Options

- **接口加第四参(session)演化**:签名不破但「组装 obs」病灶保留 → 否决;
- **黑板整帧容器(prep_obs_frame/shop_state_frame) vs 逐字段扇出**:决策核内部视图整帧消费,逐字段扇出为纯机械改名,归 P3 随编排接管一并做(实现决策) → 采纳容器;
- **新入口内部也走旧 decide_prep**:输出类型升级意图分叉无法表达 → 否决;
- **删 ctx 信箱随本批**:BriefingOp P3 才存在,先删 = 断流(2026-09-02 对抗审查裁决 P0) → 否决,双写过渡。

## Consequences

- 决策输入隐式化(session 唯一总线)→ 白名单纪律(02-state §4)成为 review 门;
- 旧接口成 deprecated 薄委托,调用点迁移完随 P5 删除;
- `LevelUpShop` 对拍口径 = LevelUpShop ≡ LevelUp(归一化后字段逐项全等),锁定于 `test_cw_w971_blackboard.py`。
