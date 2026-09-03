# DD-017:W971 P3b 编排切换——开局编排接线/overlay 分发接管/纯分发器接管备战商店/ctx 信箱退役

> 类名已随 2026-09-03 命名迁移更替,对照 NAMING.md(本文为带日期决策记录,类名保持当时事实,未改)。

## 背景

W971 流程层重构 P3(P3a 建 cw_flow 包,P3b 接线)。P3b 落地:
- 开局序列(OpeningSequence)接进主循环开局路径,0a0b 位面简报内联/位面过渡内联点空白/开局投资环境段三段退役;接管局首帧分流(01-opening §2.1);
- 七 overlay op 接入循环分发(干扰弹窗分支保留,06-overlays §4);
- ctx 信箱退役:HandleBriefing 退役,BriefingOp 内联观察直写 session;`_absorb_ctx_mailbox` 收缩为仅职级难度;
- W970 批 C 全项:备战接口改发 `OpenShop/OpenShop(read_only)`(EnsureShopOpen/EnsureShopClosed/RunBuyPhase 意图退役);RunBuyPhase 解体为流程层编排 `_open_shop_phase`(壳直调三 op 调用点上移,BuyShopCards 壳仅存续 sim 兼容入口);买后收尾抽 `finalize_buy_phase` 单一源;节点探针挂点随迁 CloseShopOp 后(字符串匹配判据改类型分派);`_handle_bench_full` 双源消解(生产路径唯一腾席源 = director 破警告链);PREP_SETTLE_S 稳定门退役;`_post_settle_auto_shop` 标志位退役;接管局补采挂点迁干净备战观察(prep_director 环入口)。

## 决策

1. **位面简报只在入场出现**(用户裁决 2026-09-02)→ 主循环不再识别简报锚;P2/P3 切换只有位面过渡(PlaneTransitionOp 分发)。
2. **EnsureShop 双语义拆解**按 W970 §3:读数性开店 → `OpenShop(read_only=True)`(幂等开店→观察刷新→不调商店决策→CloseShopOp→回备战,M-6 门保持);画面切换 → `OpenShop()`;开态清洁面板(假球误开弹窗场景)→ `OpenShop(read_only=True)` 同收关店效果。
3. **RunBuyPhase 解体的编排落点 = 流程层**(prep_director 执行端口类型分派拦截),不经执行器;波循环/读互斥(hp 取开店前备战观察)/买后收尾按 W970 §4.3.2/§4.3.4 时序随迁。
4. **六 overlay handler 本批不退役**(仅 HandleBriefing 退役):overlay op 薄封装委托保持行为逐位等价,「点选+确认」原子化需逐 overlay 实机走查,归原子化后续批。

## Considered Options

- **EnsureShopClosed(开态收球场景)替代**:(a) 直接 ClickSpheres 不关店——重开 M11 假球误开弹窗事故,拒;(b) 新设 CloseShop 意图——词表膨胀且与 CloseShopOp 收尾语义重叠,拒;(c) ✅ 复用 `OpenShop(read_only)`——幂等开店(已开不点)+ 观察刷新 + 关店,语义精确覆盖且零新词表成员。
- **RunBuyPhase 解体编排落点**:(a) 留在执行器(PrepActionExecutor.execute 内编排)——执行层获编排职责,违反 W970 分层纪律,拒;(b) ✅ prep_director 执行端口拦截——流程层本职,引擎(DecisionV2)零改动,单元记账边界(spend_unit)原样随迁。
- **_handle_bench_full 处置**:(a) 物理删除——sim 组合入口(decide_prep)仍经壳跑买牌,删了断链,拒;(b) ✅ 生产路径退役(策略 M-6 门 + director 破警告链为唯一腾席源),壳内实现随 sim 兼容入口保留。

## 后果

- 生产路径动作词表:PrepScreenAction 不再含 EnsureShop*/RunBuyPhase(EnsureShop* 类仅旧环/离线兼容);OpenShop 为商店编排唯一入口。
- 半开帧防护从「3s 盲等」改为「识别到什么进什么 op」+ director 环入口清场/预收探针;待实机走查校准(P3b 验证口径)。
- 锁迁移:EnsureShopOpen/EnsureShopClosed/RunBuyPhase 断言 → OpenShop 变体断言;PREP_SETTLE_S 归属声明锁、_absorb_ctx_mailbox 锁、探针字符串锁改型(见 sr-od-test test_cw_prep_director / test_cw_w971_p3b_seg2)。
