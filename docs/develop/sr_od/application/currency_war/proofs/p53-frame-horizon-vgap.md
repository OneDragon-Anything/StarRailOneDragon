# P53 V̄ 合成价值链的帧级 horizon 现算(R1 刷新门比较项的视界口径修正)

> 状态:**已退役(2026-09-04 修订单 R2)——V̄ 链整链退役,刷新决策改路径总账比较(形式二);结构存活部分(帧级视界现算纪律)由新判据继承。修订单 R1(2026-09-04,增量 B)见文末「修订单 R1」节,修订单 R2 见文末「修订单 R2」节**
> 数据源(单一源代码,数值不抄):`cw_registry`(`rung_value`/`h3_win_rate`/`expected_battle_loss`/`hp_to_gold`)、`cw_economy.STREAK_GOLD_TABLE`、`cw_plane_table.schedule_of`(经 `horizon.r_remaining`);机制面 = P40 ①/②/⑤、CALIB_REPORT §2.1/§2.2(**修订单 R1 后:前四字段已退役,现行因子=win_rate_dp_by_plane/vbar_hp_value_transitional,见文末**)
> 依据(修 A 的实证出处):REFRESH_CFO_REPORT(`.debug/temp/currency_war/ab_run_20260903_r2/`)§3/§5/§6——被拦帧 R_剩余 中位 12 vs 常数 5,512/512 拒刷定谳为系统性错误
> 计算脚本:`tools/cw/proofs/p53_frame_horizon_vgap_check.py`(入库可重跑)
> 提出:付费刷新拒刷复盘修 A 批(2026-09);证明 = 本篇
> 前置:P40(R1 承诺账形态)、P47(L 递推)、CALIB_REPORT(calib_vuh_v1 链与 R1 门裁决)

## 命题

R1 刷新门(`criteria/refresh.r1_commitment_account`)的比较项 V_gap,其 V̄_net 合成链中的视界因子从常数 `rounds_left_est=5` 换为决策帧现算 `r = horizon.r_remaining(session, plane, node)`:

```
V̄_net(r) = (rung_value[2] + Δp(e0→e1) × 单战价值) × r
Δp(e0→e1) = h3_win_rate[1] − h3_win_rate[0]
单战价值   = expected_battle_loss × hp_to_gold + 连胜金下界
连胜金下界 = min(STREAK_GOLD_TABLE[连胜 2-4 档]) = 2
门:启动 iff min(成员承诺账) ≤ V̄_net(r)   (卡价两侧相消,见假设 A2)
```

要证:①该链零新自由参数(每个因子都有注册表/日程出处);②V̄_net(r) 对 r 严格递增且在 r=5 处逐位等于旧静态注入值 24.7(修 A 是口径修正不是标定更换);③修正后开门形态 =「视界长 + 差 1-2 张成型」按视界单调,与 P40 ⑤ S1 自检「只有差 1-2 张成型的高边际缺口才可能过门 / 跨期持续追,本期刷窗用尽即停」的意图形态一致。

## 假设(显式)

- **A1 视界真值源**:`r = horizon.r_remaining` = 本位面剩余节点 + 后续位面按 `schedule_of(session)` 实际长度求和(未揭晓位面回退 `PLANE_FALLBACK_PRIORS=(9,9,9)` 上端)。边界:金跨位面继承 ⇒ 视界跨位面求和合法(horizon 层 R_全局 同口径)。
- **A2 卡价相消**:比较两侧为「成员承诺账 c_eff·E+L」对「V_gap(k=1)=V̄_net+同成员卡价」,k=1 形态下 Σ卡费与卡价项同成员相消(CALIB_REPORT §2.2 裁决)⇒ 生产比较项 = V̄_net(r) 本身。P40 待标定清单的 V_gap 毛值口径在此消去,非本篇新增假设。
- **A3 e2 变体沿用**:rung 流取 `rung_value[2]`(合格集条件凑档累计,CALIB_REPORT §2.1 的注入语义),修 A 只换 horizon 因子、不重开变体裁决。
- **A4 V̄ 近似恒定期内**(P40 A5 继承):缺口 1-2 张内边际成型价值平缓;帧级 r 只改视界因子,不引入期内价值漂移建模。

## 证明

### ① 零新自由参数(逐因子出处)

| 因子 | 值 | 出处 |
|---|---|---|
| `rung_value[2]` | 3.0 | cw_registry(P3 边际累计档值) |
| `h3_win_rate[1]−h3_win_rate[0]` | 0.277 | cw_registry H3 胜率阶梯跨档边际 |
| `expected_battle_loss × hp_to_gold` | 5.0 | cw_registry(条件败局伤害 × HP→金换算) |
| `min(STREAK_GOLD_TABLE[2:5])` | 2 | cw_economy 连胜弹窗金表 2-4 档下界(高连胜不计,下界口径) |
| `r` | 帧级 | `schedule_of` 单一源(禁写死,horizon 层纪律) |

每个因子都属 strategy-work §1 两类合法来源(规则数据或其推导),无常数替换常数。

### ② 单调性与连续性锚

- **单调**:r↦V̄_net(r) 线性且斜率 = rung_value[2]+Δp·单战价值 = 3.0+0.277×7.0 = 4.939 > 0 ⇒ 严格递增;视界越长,可兑现的档位流+胜率流越多——这是「V̄ 是跨期流的价值」的直接代数(与 calib_vuh_v1 链中 ×rounds_left_est 同一乘法位置,只把常数换成现值)。
- **连续性锚**:r=5 时 V̄_net=4.939×5=24.70,逐位等于旧静态注入值(`apply_core_swap_calibration` 的 `V_GAP_CALIB_V1`,即 calib_vuh_v1 `v_bar_e2`)。故修 A 不是重标定:**旧值是新链在 r=5 的特例**;决策帧 r 的真实分布(被拦帧中位 12、p25-p75=[8,15])决定门的新工作点。
- **r≤0 边界**:视界耗尽 ⇒ V̄_net=0 ⇒ 门恒关——「本期刷窗用尽即停」(P40 ⑤)的代数形态。

### ③ 修正后开门形态(P40 意图一致性)

对 REFRESH_CFO 批 arm2 全部被拦帧(n=512,修前静态门 100% 拦)用生产判据同形口径重放(脚本 §2):

| 口径 | 开门 | 备注 |
|---|---|---|
| 账 ≤ V̄_net(r)+卡价(报告 §6 表头) | 291/512 = **57%** | 分视界 r<4:0% / r4-7:0% / r7-10:15% / r10-14:68% / r≥14:**100%**;开门帧 j 分布 {0:39, 1:251, 2:1} |
| 账 ≤ V̄_net(r)(生产比较项,A2 相消) | 270/512 = **53%** | 与表头口径差 = 卡价项(1-4 金),形态同 |

形态读法(三行,逐条对 P40):

1. **按视界单调**:r<7 全关、r≥14 全开——「视界长 ⇒ 跨期流价值大 ⇒ 承诺账可过」,正是 P40 ⑤ S1「跨期持续追,本期刷窗用尽即停」的量化;短视界帧仍关,与 P40 ①「j 越深越难刷」合取后,修正后仍关的 43%(生产口径 47%)集中在 r<10 与 j=0(整缺口)——本就该关(REFRESH_CFO_REPORT §5)。
2. **开门集中在 j=1(差 2 张,87%)**:与 P40 ③ 结论 1「只有差 1-2 张成型的高边际缺口才可能过门」逐字一致——修 A 打开的恰是 P40 意图要开的门,不是把门整体拆掉。
3. **方向自检通过**:修前 512/512 全拦(门失去分辨力)→ 修后开门率按视界单调分层——门恢复了「P 边际 vs V̄ 流」的分辨功能,系统性错误(常数低估视界 2.4 倍)被口径修正消除。

### ④ 确认性 sim 对拍(mandate 臂 B1,同池同 seed 修前/修后)

池指纹 `44bdbd3a28d3d40a+eqg1`(snapshot,与 REFRESH_CFO replay 守卫同值)、seeds 0-29、planes=2、注入态(V_GAP 槽位开闸);修前/修后同进程口径切换(比较项静态槽位值 ↔ 帧级现算),修后对修前逐 seed 确定性(修后双跑逐位一致)。三件套(n=30/臂,误差范围=逐 seed 全量计数,无抽样;harness=`.debug/temp/currency_war/horizon_vgap_b1.py`):

| 指标(符号定义见 harness) | 修前 | 修后 | 判读 |
|---|---|---|---|
| refreshes/局(引擎计数) | 0.43(13/30 局) | 77.83 | 离开 0 ✓,**量级超调**(见下) |
| 空转波占比(零动作波/总波) | 0.4528 | 0.1039 | 下降 ✓ |
| 出现 2★ 的局数 | 0/30 | 0/30 | 未出现 ✗(辖域预判成立,见下) |
| 终局 hp 均值(参考,不作方向结论) | 7.1 | 11.5 | 参考值 |

两条如实申报(超出任务书预期形态的发现):

1. **刷新量超调与 R2 预留下界缺位的交互**:修后刷新经截断点重决策在波内循环发射(RefreshShop=截断点),终态受 r2 预算门约束——而消费位传入的 S 预留 = `b_target(0,0,0)=0`(P48 下界投影),即预算门实际形同 `gold≥2`,金被刷到 0-4/波,买入链饿死(11-12 买/局)。P40 R2 规范口径(息线约束:溢余段刷窗 `⌊(g−50−Σ预留卡价)/c_eff⌋`)在 cw4 未落码——修前被 R1 全拦掩蔽,修 A 解蔽。R2 预算门本批不动(REFRESH_CFO_REPORT §6 明令),此交互挂账待编排者裁决(候选=按 P40 R2 规范口径补息线 floor,独立批数学先行)。
2. **2★ 未出现的辖域解释**(REFRESH_CFO_REPORT §7 预判成立):成型需要买入侧允许凑第三张(合成跳变),不在本刷新门辖域;修 A 打开的 j=1 刷新通道要兑现为 2★,需买入/卖出席位策略批承接。

## 结论

1. 修 A = 同链 horizon 口径修正:V̄_net(r) 帧级现算,零新自由参数,旧静态值 24.7 是 r=5 特例;
2. 开门形态与 P40 ⑤/③ 的意图形态一致(按视界单调、集中 j=1),反事实重放逐位复现报告 §6 表;
3. 实现落点:`cw4/statefn/vbar.py`(链本体)+ `cw4/shop.py`(r1 门消费位);`cw_registry.rounds_left_est` **不动**(decision_v2 scoring 层3 消费它,冻结基线;修 A 只移除 cw4 R1 门对该常数的依赖,臂②域内变更);
4. **不要修 E 公式**、不要动 R2 预算门(REFRESH_CFO_REPORT §6 同款申报继续有效);修 B(集合级散刷门)不在本批,若修 A 落码后 sim 仍显示刷新不足再启。

## 对实现的检验点

1. 单测锚:`vbar.v_bar_net(reg,5)≈24.7`、r∈[1,20] 严格递增、连胜金下界=STREAK_GOLD_TABLE 表值;R1 门行为锁=短视界深缺口关(shop_r1_account_over_vgap)/长视界浅缺口开——旧行为锁「lv5 j=1 深缺口恒拒」按锁纪律重推改写(被锁语义「V_gap 静态 24.7」已被本证明取代,docstring 记一句为什么)。
2. 复算脚本:`tools/cw/proofs/p53_frame_horizon_vgap_check.py`(链锚 + 开门率重放 + 单调性,数据在档时全跑)。
3. sim 判读锚(事前写):修后刷新数/局 >0、空转占比下降、出现 2★ 局;不锚 hp/胜率(验收归正式 A/B)。

## 边界(本证明不覆盖)

- 开门率 57%/53% 是**被拦帧反事实重放**,不是整局重放——对 hp/胜率的净效应需确认性 A/B(REFRESH_CFO_REPORT §8 申报继承);
- `schedule_of` 回退先验 (9,9,9) 上端语义:未揭晓位面期视界偏长 ⇒ 门偏开;真值揭晓后收窄(与 horizon 层端点纪律同向,不新增偏差);
- 单成员承诺账(k=1)粒度不变——集合级散刷门 = 修 B(判据形式错配的次因,REFRESH_CFO_REPORT §0.1b/§6 修法 B),本批不辖;
- 修 A 与修 B 的关系:A 修价值侧口径、B 修成本侧粒度,不冲突;若 A 落码后 sim 仍刷新不足再启 B。

## 关联

- P40(R1 承诺账本体与 ⑤ S1 自检——本篇修其比较项的视界因子,不动门形态);
- CALIB_REPORT §2.1/§2.2(链的静态版与卡价相消裁决——A2 的出处);
- REFRESH_CFO_REPORT §3/§5/§6(修 A 的实证依据与反事实表);
- 决策记录已并入本篇(动机与出处节);代码:`cw4/statefn/vbar.py` + `cw4/shop.py` r1 消费位。

## 修订单 R1(2026-09-04,增量 B——因子 provenance 重接地)

**触发**:宪法第一条(策略不依赖战力建模)+ 用户裁定(未证即退役/A-B 无裁决权)。原 §①「零新自由参数」声明**作废**——其因子表把 cw_registry 当出处,而 registry 装的是三个经验拟合(rung_value=P3 拟合 / h3_win_rate=P1 校准且无位面维且 rung2 n=9 / expected_battle_loss×hp_to_gold=未标定×P3 废溯源),循环论证。

**结构存活**:帧级现算形态(V̄ 随 r 现算,禁常数视界)、单调性、r≤0 边界、R1 门形态——不变。

**因子重接地后的现行链**:

```
V̄_net(r, plane) = Δp[plane] × 单战价值 × r
  Δp = win_rate_dp_by_plane[plane]【推】p15 冻结语料(73 局,sha 848dc1aa)
       局聚类 bootstrap(n=2000,seed=20260910;battle-only,killed 结算屏
       权威口径):P1 Δp=0.450 [0.274,0.612](rung0 胜率 0.250 n=84/
       rung1 0.700 n=60);P2 点估计 −0.197 [−0.498,0.091](n=16/61,
       薄桶 CI 含 0)→ fail-closed 钳 0(P1/P2 CI 不重叠=必须分位面;
       P2 重derive 死线=语料扩至 n≥40/桶)
  单战价值 = vbar_hp_value_transitional(9.59,P15v2 P1 battle CI 下缘,
             P21 1:1 过渡口径,λ_death 重锚债挂账,P35_VALIDATION:116
             通道;先例=strategy-docs/04 §2 收益侧)
           + 连胜金下界(2,STREAK_GOLD_TABLE[2:5] min【注】;窗口下界
             论证:0-1 档无弹窗金、5+ 档金更高被排除=min=保守下界)
```

**因子处置**:rung_value 档位流退役(收入三元分解中无 rung 确定函数:息律=存金函数边际 0;连胜流已由 Δp 通道计账,再立=双计;史料=rung 档位流退役裁定,git 历史可溯);h3_win_rate 被 win_rate_dp_by_plane 取代(旧 rung0=0.139 比 P1 实测 0.250 低约 44%);expected_battle_loss/hp_to_gold/rounds_left_est 随消费端死亡一并退役。

**连续性锚作废**:原 §②「r=5 ⇒ 24.70=旧注入」随 slope 变化(4.939→P1 5.22)失效——旧值是旧因子组的特例,不再具锚地位;新 P1 锚 r=5 ⇒ 26.08(锁=test_cw_vgap_frame_horizon)。

**行为差**:P1 slope=0.450×11.59=5.22(CI [3.18,7.10] 覆盖旧值 4.939,决策温和);P2 slope=0(门实质关闭,与 economy「P2 少刷吃息」共识同向)。生产默认 V_GAP=None ⇒ R1 门 fail-closed 关闭不变,行为影响待 V_GAP 标定注入后兑现。

## 修订单 R2(2026-09-04——V̄ 链整链退役)

**触发**:用户裁定禁胜率建模(修订单 R1 重接地后的因子端 win_rate_dp_by_plane / vbar_hp_value_transitional 仍是统计拟合量,不属游戏定义量)+ 刷新决策改路径总账比较(形式二,推导批验收采纳)。

**退役面**:

- R1 刷新门比较项 V̄_net 整链退役:判据本体(criteria/refresh.r1_commitment_account)改为**形式二可负担性**——`c_eff·E(D|L*) + Σ卡费 + L(g, spend, R_剩余, Ī) ≤ g − g*`(E = expected_refreshes_for_card 按缺件集与等级选择输出 L*;g* = 10×cap_resolved);L* = 留级账 T_stay vs 升一级账 T_up(含 U_L 及其息损)取小(贪心序反例承载,11_shop_decisions.md §2 修正②)。输入全为游戏定义量(REFRESH_PROB 池参数 / XP 表 / 息律),零胜率。
- P57 搜索窗 V̄ 读法门随链消解:窗口重锚塌缩带 `refresh_prob(L,c) ≥ ω×峰值级命中率`(ω = registry.omega_collapse_ratio,同源);calib e2_24.7 对拍锚作废。
- 实现:`statefn/vbar.py` 墓碑;`win_rate_dp_by_plane` / `vbar_hp_value_transitional` 注册表字段退役(本修订单);V_GAP/V_MS provisional 槽位保留登记、消费端清零。

**结构存活(由新判据继承)**:帧级视界现算纪律(R_剩余 = horizon/schedule_of 现算,禁常数视界——本篇 §①r 因子行的纪律在新账的 L 项继续生效);「本期刷窗用尽即停」边界(新门由预算比较结构承载)。

**连续性锚再作废**:修订单 R1 的新 P1 锚 r=5 ⇒ 26.08 随链退役(锁=test_cw_vgap_frame_horizon 已重锚为可负担性行为锁)。
