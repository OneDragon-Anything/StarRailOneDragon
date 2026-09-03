# CW 对拍2标定批报告 V2(CALIB_REPORT_V2)——分析面:EV 面其余槽位定谳

> 日期:2026-09-11。性质=**纯分析推导,零代码改动**(排程硬门「EV 面标定开闸」的
> 分析面;落码批等并行返工批结清后另派)。先例与纪律单一源 =
> `core_swap/CALIB_REPORT.md`(V1:零新自由参数/带 CI/出处可复算/禁硬凑——
> 不可标定槽位显式 None+豁免申报)。
> 本批产物:`redesign/calib_v2_analysis.py` + `calib_v2_analysis.json`
> (复算脚本与原始数字,零仓库代码触碰);`calib_vuh_v1_report.json`
> (V1 工件 2026-09-11 重跑刷新,87 局语料)。

## 1. 槽位全集盘点(provisional.py 23 槽;消费点=文件:行)

登记表 = `src/sr_od/application/currency_war/decision/cw4/audit/provisional.py`
L43-88(计数口径:13 编号行 −#11(λ 表承载)+#2 拆两槽+后补 10 槽 = 23)。
[计数勘误(编排者验收 2026-09-03,打标不删原文):机械复核
`len(_SLOTS)`=**24**——原口径式「后补 10 槽」系手数误差,NMF 段 13 槽
+后补段 11 槽(THETA/D_MIN/DELTA_HYST/DELTA_PRIOR/CONV_GOLD_PER_ROUND/
P_REC/BLOODLINE_HP_THRESHOLD/N_CRISIS/P3_LENGTH_STAT/F7_CONTINGENCY_ARMED/
P_LAMBDA_QUANTILE)=24;同族复发 R199「共 42 节」算术误差,计数申报一律
附机械复算式(本条勘误式=python len(_SLOTS))。§2.4「14 个无消费位槽」
相应勘误:名单实列 13(W_POP…DELTA_PRIOR)+CONV_GOLD_PER_ROUND 有消费注记
(窗口帧 C_stay/χ)未入 §1 表单列,BLOODLINE/P_LAMBDA 各有消费位系单列行;
不影响任何行为判断(涉事槽全部 None 豁免态)。]
注入态:「有值」= 经 `sim/ab_core_swap.py:76-97 apply_core_swap_calibration()`
注入(显式调用,sim/A-B 驱动专用 `injected_form=True`;缺省态仍全 None)。

| 槽位 | 当前态 | 消费点(文件:行) | 所属决策线 |
|---|---|---|---|
| V_GAP | **有值** 24.7(V1 注入) | shop.py:650(r1 发射位→criteria/refresh.r1_commitment_account);contracts.py:43 | 付费刷新线(P40 R1 总账) |
| V_MS | **有值** 24.7(V1 同源注入) | proof.py:256、sell.py:44(均 is_none 前置门;数值形态无消费位) | 换线塌缩出口线(P41 ② max 通道) |
| U_X | None | buy.py:47(ev_buy 前置)、proof.py:256、sell.py:44(均 is_none 前置门;数值形态无消费位) | EV 买线 + 换线出口线(P41 ① u_x) |
| T_SEARCH_A | None | buy.py:51(档窗口)、shop.py:332(_t_search_active)、stockpile.py:23、mandate.py:358(M6 溢余)、sell.py:64(凑息卖)——**全部 is_none 门,窗口={1,2,3} 系 shop.py:334/buy.py:52 硬编码「注入形态:档窗口随标定批定谳」** | EV 买/压库/溢余/凑息卖线(P49 档匹配) |
| THETA / D_MIN / DELTA_HYST | None | proof.py:148-150(resolve_switch_params;任一 None ⇒ should_switch 不评估) | 换线滞回线(P16/R24-2) |
| P_LAMBDA_QUANTILE | None | entry.py:290(λ 顾问;None 期影子键) | 升档器线(R28-1/R29-1) |
| BLOODLINE_HP_THRESHOLD | None | entry.py:302(血线地板;None 期构造性不触发) | 升档器线(R27-1②/R36-2) |
| W_POP / RHO_IMPUTE / NBAR_ESTIMATOR / LAMBDA_S_EQUIP / V_FURNACE / C_FRAME_Q / DELTA_P_WIN / P_HIT_Q_CONV / P_REC / N_CRISIS / P3_LENGTH_STAT / F7_CONTINGENCY_ARMED / DELTA_PRIOR / CONV_GOLD_PER_ROUND | None | **无 cw4 消费位**(全仓 grep 仅 provisional.py 登记行+proof_consts.py:33 的 CONV_GOLD_PER_ROUND_LB 常量旁注) | 登记在案、消费位未落(NMF §3.3 批时快照 + 后补) |
| V_BAR | None(封印) | 无(get 恒 None、inject 拒绝;R10-2 类型级封印) | —(永不作闸门) |

## 2. 逐槽位定谳(值·推导链·CI·状态)

### 2.1 V_MS = 24.7 金,CI [16.7, 24.7](复核确认 V1,同源单标定)

- **论断**:V_MS 维持 V1 同源注入值 24.7(带 [16.7, 24.7])。本批复核三项后确认,
  无新推导面:
  1. **同源纪律成立**:provisional #2a/#2b「同源单标定禁双源」+ p46 待标定清单
     「V_ms 与 V_gap 同源共用——两篇必须同一标定,禁双源」——V_GAP 既按 V̄_net
     合成链标定,V_MS 只能同值同源,独立推导反而违禁双源;
  2. **推导链复算吻合**(calib_v2_analysis.py 注册表直调):rung 流 e2 =
     `rung_value[2]` 3.0 × `rounds_left_est` 5.0 = 15.0;胜率流 = Δp(e0→e1)
     (`h3_win_rate` 0.416−0.139=0.277)× 单战 7.0(`expected_battle_loss`
     10 × `hp_to_gold` 0.5 + 连胜金下界 2)× `battles_left_est` 5.0 = 9.695;
     V̄_net(e2) = 24.695 ≈ 24.7;e1 变体(rung_value[1] 1.4×5=7.0)= 16.695 ≈
     16.7 = 带下沿。**第三方按上式重算得同值**(锚全部 = cw_registry 既有字段,
     零新自由参数);
  3. **消费面零变成立**:V_MS 全部消费位(proof.py:256 / sell.py:44)均为
     `is_none` 前置门,数值形态无消费位——注入不改变任何行为面(实测 L1 全量
     无红,V1 §3 ⑦),同源注入无歧义风险。
- **状态**:【拟·标定批 V1 复核确认】;`injected_form=True`(sim/A-B 驱动专用;
  生产开闸须 CI 验收五件套)。

### 2.2 U_X:不可标定(语料行为污染 + 槽位粒度双缺口)——显式 None+豁免

- **论断**:U_X 维持 None。p41 语义(使用概率 P(这张牌未来真的被需要),A5
  「件类的标定输入」)在现有全部工件上**推不出带 CI 的合格标定值**;且单浮点
  槽位与分档语义粒度不匹配(R17-4)。禁硬凑。
- **证据与推理链**(三步,可复算):
  1. **唯一在档数值不授权**:p41 首版分档点值(1费0.05/2费0.4/3费1.0/4费0.8/
     5费0.15)经 P41 修复批明文降级「保留仅作历史对照与二维表生成口径,
     **不授权消费**」(p41-hoard-sell-ev.md 待标定清单 u_x 行)——上游已判
     「calib_v1 无 CI 点值注入卖出闸门违规」,不可复用;
  2. **语料直测表不可识别目标量**(本批新证据,calib_vuh_v1 87 局重跑):
     终局在场口径 u = 1费 0.848 [0.820, 0.873] / 2费 0.510 [0.459, 0.560] /
     3费 0.562 [0.502, 0.621] / 4费 0.212 [0.119, 0.349] / 5费 1.000 [0.526,
     1.000](Wilson 90% CI,calib_v2_analysis.json `u_table_wilson90`)——
     **档间序与 p41 先验全链倒挂**(语料 1费最高 0.848 vs 先验最低 0.05)。
     机理:语料系旧策略「买入即上场、填满板面」行为的产出,u 测的是
     「旧策略买的牌留在终局」的频率(策略需求侧选择效应),而 p41 语义要的是
     新决策规则候选人群(线外/未定型件)的「未来被需要」反事实概率——两者
     人群不同、不可经任何零参数换算互推(同因,H 口径已被 calib_vuh_v1 明文
     判「语料不可识别」,u 属同族污染,本批补齐申报);
  3. **槽位形态缺口**:即使有合格表,单浮点 CalibValue 装不下分档带序结构
     (R17-4「分槽/带序逐格」)——V1 §2.4 已裁,落码需槽位重设计,出本批
     (分析面)范围。
- **豁免后 fail-closed 行为判读**:buy.py:47 ⇒ EV 买候选恒空(`shop_ev_
  u_unavailable` 计数);proof.py:256/sell.py:44 ⇒ 换线塌缩出口不评估
  (`switchline_exit_blocked`)。**A/B 判读含义**:这些面两臂恒等关闭,臂间
  diff 不含 EV 买/换线卖出路径的贡献——B1/B2 对这些面仍测「共同降级态」,
  预注册必须披露(见 §4)。方向申报:买面少买/卖面少卖,均保守向。
- **留给落码批的确定性输入**(本批交付):语料 u 表+CI 已归档
  (calib_v2_analysis.json);若未来槽位重设计为分槽,U_X 首个合格数据源
  应是新核自身 sim/实机语料的决策语境条件频率,非本表(污染申报在案)。

### 2.3 T_SEARCH_A:不可标定为常数(两读法均随等级漂移且互相矛盾)——显式 None+豁免 + 确定性查表交付

- **论断**:T_SEARCH_A 维持 None。其消费形态不是数值而是**档窗口集合**
  (shop.py:334/buy.py:51-52 的 `frozenset({1,2,3})`「注入形态占位,档窗口随
  标定批定谳」)。本批结论:**不存在可注入的常数窗口**——任何固定 frozenset
  都是新增自由参数(选读法+选等级锚两重任意),违「零新自由参数」禁令。
  硬编码 {1,2,3} 在两读法全等级表上均无一处吻合(calib_v2_analysis.json),
  即它本身不是可推导值。
- **证据与推理链**(确定性查表,全部锚 = REFRESH_PROB 实机 OCR 权威表 +
  V̄_net 标定带,零新自由参数;门式 = p40 单步 EV 门 V* = c_eff/P ≤ V̄):
  1. **读法甲(档级,P=该档槽概率)**:窗口(c) ⟺ p(L,c) ≥ c_eff/V̄。
     带上沿 24.7(thr=0.081):L1-3 {1};L4-6 {1,2,3};L7-8 {1,2,3,4};
     **L9 {1,2,3,4,5}、L10 {2,3,4,5}**。带下沿 16.7(thr=0.120):L4 {1,2};
     L7-8 {1,2,3};L9 {1,2,3,4}。→ 窗口随 L 单调扩张且**对 V̄ 带端敏感**
     (L7 在两端间差一个 4费档);
  2. **读法乙(单卡,P_shop=1−(1−p/v)^5 满池,p41 ①退化式)**:窗口(c) ⟺
     c_eff/P_shop ≤ V̄。上沿 24.7:L1-4 {1};L5 {1,2};L6-7 {2,3};**L8 {3}**;
     L9 {3,4};L10 {4,5}。→ 与读法甲**逐级矛盾**(L4 甲含 {2,3} 乙只 {1};
     L8 甲含 {1,2} 乙只 {3}),且带下沿下 L5/L8/L9 出现**空窗**(该级任何
     单卡追刷都过不了价值门——与 p40 ③「V* 19-148 金随档位」形态一致);
  3. **物理复核**:两读法分别对应 p49 档匹配(压缩/凑息,任意同档牌算命中)
     与 p40/p41 追特定卡(单卡缺口)——它们本就该用不同窗口,**这恰恰证明
     窗口是「读法×等级×(带端)」的三元状态量,不是槽位常数**。读法甲在 L9-10
     开 5费档还与 p40 S2(5费深缺口 V*≈148 金不可 D)/p49「限深缺口」结论
     张力,进一步排除常数化。
- **豁免后 fail-closed 行为判读**:buy.py:51(候选第三类不发射)、
  shop.py:332/_t_search_active(空集)、stockpile.py:23(M6/压库不买,
  mandate.py:358 `m6_overflow_strand` 溢余滞留计数)、sell.py:64(凑息档
  不卖 `t_search_unavailable`)。A/B 判读含义同 §2.2:两臂恒等关闭,预注册
  披露。方向:少买+少卖,保守向;溢余滞留有遥测计数可观测。
- **留给落码批的治本规格**(本批交付,零调参):两处硬编码 {1,2,3} 应改为
  **运行时确定性查表**——档级消费位(压库/凑息/M6)用读法甲、单卡消费位
  (ev_buy 追件)用读法乙,等级现读 REFRESH_PROB,V̄ 现读 provisional V_MS
  (端点随消费位走:开门判据用上沿 24.7,敏感臂判读用带);表值即
  calib_v2_analysis.json `tier_level_gate`/`card_level_gate`,第三方按
  `p ≥ 2/24.7`(甲)/`2/P_shop ≤ 24.7`(乙)重算可得同表。

### 2.4 其余 None 槽位豁免申报(复核 V1 §2.4,全部维持)

| 槽位族 | 维持 None 的依据(本批复核) |
|---|---|
| THETA/D_MIN/DELTA_HYST | 在档值(θ=1.0/δ=0.15/D_min=2)系注入形态量级论证级(P16_VALIDATION 门⑤),非标定值;A/B 两臂换线恒为影子面不写 target_comp ⇒ 不影响臂间 ledger;v6 行 3/8 类条款未到期不阻塞 |
| CONV_GOLD_PER_ROUND(χ) | 标定通道=sim 轨迹滞留事件回归(R44-2),无既有工件数值;CONV_GOLD_PER_ROUND_LB=5.8 经 R64-1 已降格「依附申报、λ 表重建后从未重推导」——禁充当标定;行 9 未到期 |
| 14 个无消费位槽(W_POP/RHO_IMPUTE/NBAR/LAMBDA_S_EQUIP/V_FURNACE/C_FRAME_Q/DELTA_P_WIN/P_HIT_Q_CONV/P_REC/N_CRISIS/P3_LENGTH_STAT/F7/DELTA_PRIOR+BLOODLINE/P_LAMBDA_QUANTILE) | 消费位未落(§1 盘点:全仓无 cw4 消费点)——「标定值无消费面」与「None fail-closed」行为等价,标定无收益;各自类条款(血线 ≤p_open、η/χ 锚批、P3 通关语料)均未到期;禁为开表硬凑 |
| V_BAR | 类型级封印(R10-2),永不作闸门(测试锁在案) |

## 3. 与 A/B 重跑就绪的接口(裁决点,呈编排者)

1. **排程硬门形式上可达**:「全槽位非 None(或豁免在案)」经本批后成立——
   有值 2(V_GAP/V_MS)+ 豁免在案 21(本报告 §2.2/2.3/2.4 = V1 §2.4 的
   复核+扩充)。**但豁免 ≠ 行为面开闸**:U_X/T_SEARCH_A None 期 EV 买/
   压库/M6/凑息卖/换线塌缩出口五面两臂恒等关闭。
2. **B1/B2 判读边界的强制披露**(预注册批采纳):ZERO_REFRESH_DIAG §4.3 的
   CASCADE 三件套中,零刷新已由 V_GAP+R1 总账闭合(V1 §3 ② 实测 0<refreshes
   ≪60+),但**零 EV 买(shop_ev_u_unavailable)与零升级(M3 arm1_existence,
   另案)在重跑中仍将两臂同现**——B1/B2 仍含「共同降级代价」分量,headline
   必须披露 `shop_ev_u_unavailable`/`m6_overflow_strand`/`shop_r1_*` 计数,
   与 ZERO_REFRESH_DIAG §6.1 判读纪律一致。
3. **活性守卫前置不解除**:V1 §1 呈报的 `new_core:sell` 结构性饥饿(预存红)
   与本批无关,立案前正式 A/B 不得开跑——该阻塞位仍在。

## 4. A/B 重跑就绪清单(v6 判前锁核对位)

标定面(本批辖):
- [x] V_GAP = 24.7 [16.7, 24.7](V1 注入;合成链本批复算 24.695/16.695 吻合)
- [x] V_MS = 24.7 [16.7, 24.7](同源单标定;消费面 is_none 门,零行为变)
- [x] U_X:None+豁免在案(§2.2:不授权点值+语料污染+粒度三证;fail-closed
      判读与 A/B 披露项列明)
- [x] T_SEARCH_A:None+豁免在案(§2.3:常数窗口不可推导;确定性查表两读法
      交付落码批;fail-closed 判读与 A/B 披露项列明)
- [x] 其余 19 槽:None+豁免在案(§2.4 复核 V1;类条款未到期不阻塞)
- [x] V_BAR:封印保持

非标定面(他批辖,沿 V1 §4 清单不动):`new_core:sell` 饥饿立案、v6 行 1/2
(判读器)、行 7/11/13(schema)、行 4/5/10(预注册)、行 6/14/15/16(语料/
登记/落码验收)。

## 5. 可复算检验式

```powershell
$env:PYTHONPATH='src'
uv run python tools/cw/calibration/calib_vuh_v1.py          # u 表/V̄ 链语料侧
uv run python .debug/temp/currency_war/redesign/calib_v2_analysis.py
```

判定式:①V̄_net 链 stdout 打印 16.695/24.695(=报告 §2.1);②u 表 Wilson CI
与 calib_v2_analysis.json `u_table_wilson90` 逐档一致;③窗口表与
`tier_level_gate`/`card_level_gate` 一致(第三方按 §2.3 门式手算 L7 甲读法
得 {1,2,3,4}、乙读法得 {2,3} 即锁死两读法分立)。
