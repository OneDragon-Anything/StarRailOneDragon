# ADR-0515: rung_value 档位流退役(V̄_net 链因子重接地·增量 B)

## 背景

宪法第一条(策略不依赖战力建模)+ 用户裁定(2026-09-04:「未经数学证明的就退役」「A/B 无裁决权——旧策略也是垃圾」)要求清退 V̄_net 链上的经验拟合因子。架构审计(清单一组1 #1/#2/#3)判定三个 load-bearing 输入违例:rung_value(P3 经验拟合)、h3_win_rate(P1 校准/无位面维/rung2 n=9)、expected_battle_loss×hp_to_gold(未标定×P3 废溯源)。

## 决策

1. **rung_value 档位金/轮值退役**:收入三元分解(基础奖励+利息+连胜金,economy.md §10.1/§11)中无任何 rung 确定函数——利息=存金函数(对 rung 边际 0);连胜流已由 Δp×单战价值通道计账,再立档位流=双计。档位流无游戏定义确定值,按「未证即退役」除名。
2. **h3_win_rate 被 win_rate_dp_by_plane 取代**:分位面实测(P1 Δp=0.450 [0.274,0.612];P2 −0.197 [−0.498,0.091] 薄桶 fail-closed 钳 0),语料=p15 冻结语料(73 局,sha 848dc1aa),局聚类 bootstrap n=2000 seed=20260910,battle-only+killed 权威口径。P2 重derive 死线=语料扩至 n≥40/桶。
3. **hp 分量换 vbar_hp_value_transitional(9.59)**:P15v2 P1 battle CI 下缘×P21 1:1 过渡口径(λ_death 重锚债挂账,P35_VALIDATION:116 通道)。连带 expected_battle_loss/hp_to_gold/rounds_left_est 退役(消费端死亡)。

## 行为影响

P1 slope 4.939→5.22(CI 覆盖旧值,温和);P2 slope→0(P2 追档门实质关闭,与 economy「P2 少刷吃息」共识同向)。生产默认 V_GAP=None ⇒ R1 门 fail-closed 不变,影响待标定注入后兑现。测试锁:test_cw_vgap_frame_horizon(P1 锚 26.08 + P2 全视界关闭锁)。

## 备选

- 保留 rung_value 挂标定接口——被否:机制上无对应物,标定无从附着(与 P14 定理 4「不可规划」同构)。
- P2 用负点估计——被否:CI 含 0 的薄桶负值进账违 fail-closed 纪律,钳 0 由注册表层承载。

## 关联

P53 修订单 R1(证明侧);vbar.py/cw_registry.py(实现);p15 冻结语料(848dc1aa,tools/cw/proofs/p15/)。
