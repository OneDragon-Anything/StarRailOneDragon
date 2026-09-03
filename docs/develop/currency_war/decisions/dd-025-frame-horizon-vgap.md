# DD-025:R1 刷新门 V̄ 比较项换帧级 horizon 现算(修 A)——rounds_left_est=5 常数退役出 cw4 消费链

- Status: accepted
- 日期: 2026-09-12
- 出处: REFRESH_CFO_REPORT(`.debug/temp/currency_war/ab_run_20260903_r2/`)§3/§5/§6 + P53-frame-horizon-vgap

## Context(背景与问题)

付费刷新拒刷复盘(REFRESH_CFO_REPORT)定谳:P1 过渡带 512/512 可评帧全拒刷是系统性错误。主因 = R1 门比较项 V̄_net 的标定链(calib_vuh_v1)把视界因子钉死在 `rounds_left_est=5` 常数,而刷新决策帧的真实剩余视界(R_剩余)中位 12(p25-p75=[8,15])——V_GAP 被系统性压小 2.4 倍,门失去分辨力。次因 = k=1 单成员承诺账的粒度错配(修 B,另批)。E[refreshes] 超几何与 P40 原文逐位吻合(19.1 vs 19.2),不是病灶。

## Decision(决策)

cw4 R1 门(`shop.py` r1_commitment_account 消费位)的比较项改为帧级现算 `V̄_net(r) = (rung_value[2] + Δp(e0→e1)×单战价值) × r`,r = `horizon.r_remaining`(schedule_of 单一源)。链本体落 `cw4/statefn/vbar.py`;V_GAP provisional 槽位保持 fail-closed 开闸通道语义(None ⇒ r1 闭),槽位数值不再是比较项。零新自由参数:旧静态注入 24.7 = 新链在 r=5 的特例(连续性锚),不构成标定更换。

**共享面裁决(本 ADR 的关键申报)**:`cw_registry.rounds_left_est` 同时被 decision_v2 `scoring.py`(层3 板面查表评分)消费,属两臂共享字段与冻结基线——本批**不触碰该字段**,只在 cw4 臂②域内移除 R1 门对它的依赖。decision_v2/sim 判读面/判前锁 v6 零改动。

## Considered Options(备选与取舍)

1. **换 horizon 口径(采纳)**:零新参数、数学可证级(strategy-work §3 档 1 直接落码无开关)、旧值成特例可连续性对账。
2. 拍新常数(如 rounds_left_est=12):禁——常数替常数,决策帧视界是分布不是单值,拍死即下一个小视界病灶。
3. 修 E[refreshes] 超几何:被 §3 实证排除(与 P40 原文吻合),错误方向。
4. 修 B 集合级散刷门:与修 A 不冲突但属经验性(需 V̄_copy 标定),按档 2 先标定后 A/B,本批不辖。

## Consequences(后果)

- 正面:开门率 0%→53-57%(按口径),开门帧按视界单调、集中「差 2 张」(j=1 占 87%)——与 P40 ⑤/③ 意图形态一致;刷新服务买量的通道打开(REFRESH_CFO_REPORT §7 链条判断)。
- 代价/边界:开门率系被拦帧反事实重放,对 hp/胜率的净效应待确认性 A/B(预注册判据:过程量=刷新数/局、2★ 帧数、depth);`schedule_of` 回退先验 (9,9,9) 上端使未揭晓位面期门偏开(真值揭晓后收窄,与 horizon 端点纪律同向)。
- 测试面:旧锁「lv5 j=1 深缺口恒拒」被新语义取代(静态 24.7 语义过期),按锁纪律重推改写为「短视界深缺口拒/长视界浅缺口开」双面锁。
