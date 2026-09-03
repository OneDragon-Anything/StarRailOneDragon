# CW 换核标定批报告(CALIB_REPORT)——mandate_v1 provisional【拟】槽位灌值

> 日期:2026-09-03。性质=A/B 重跑前置件(④-2 分臂裁决:标定值只经
> `audit/provisional.py inject` 显式注入,每值带出处/方法/状态;禁改判据数学;
> 【拟】→【注】/【证】改判须走登记)。
> 文件面:`cw4/criteria/refresh.py`(r1_commitment_account 新)、`cw4/shop.py`
> (_r1_member_accounts 装配 + r1 发射位换总账形态)、`cw4/criteria/{contracts.py,
> __init__.py}`(新判据两表登记)、`sim/ab_core_swap.py`
> (apply_core_swap_calibration 注入通道)、`sr-od-test/.../test_cw_zero_refresh_fix.py`
> (旧锁改写)。**让路**:`sim/runner.py` 与 decision_v2 系并行在飞零触碰。
> 冒烟脚本/原始数字:`core_swap/calib_smoke.py` + `calib_smoke.json`。

## 1. 标定面盘点(v6 checklist 逐行红绿)

`ab_core_swap.v6_checklist()` 实测(缺省态,16 行):

| 行 | 判据 | 状态 |
|---|---|---|
| 1 | ab_judge 词表含 mandate_v1/ev_arm | **未落地**(tools/cw/ab_judge.py 无该词表) |
| 2 | 判读器迁移+v6 变更记录(prereg 含 v6 节) | **未落地**(hint_pass=false:PREREG 无 'v6') |
| 3 | 血线阈值标定 ≤ p_open(时间戳序) | 未到期(类条款,不阻塞) |
| 4 | 锚批/判读批分离(拆半预注册) | **未落地**(mark 未申报) |
| 5 | 激活率门验收口径重开+预注册(非窗口相位) | **未落地** |
| 6 | P3 fallback 9→CI 上端治本事件入变更记录 | **未落地** |
| 7 | telemetry schema 含 f7_contingency_armed | **未落地**(schema.py 实测无键) |
| 8 | η/θ 标定 ≤ p_open | 未到期(不阻塞) |
| 9 | χ 标定 ≤ 换线判读锚批 | 未到期(不阻塞) |
| 10 | 激活率门锚/#T 相位分键重开(窗口相位) | **未落地** |
| 11 | schema 含 depsilon_advisor_violation | **未落地** |
| 12 | D_ε 带宽与 η 同批标定 | 未到期(不阻塞) |
| 13 | schema 含 f7_exempt_emission | **未落地** |
| 14 | P2 段档位登记批 ≤ P2_IDLE_SWITCH_W 激活 | **未落地** |
| 15 | 01 §4.4 [41] S 公式物理补指针 | **未落地** |
| 16 | 01 §4.1 [17] 息律三处字面参数化核读 | **未落地** |

**阻塞正式 A/B 的槽位/行清单**(本批后):
- 槽位面:**V_GAP 已标定(本批,§2)**——原 P1 阻塞槽位解除;
  其余【拟】槽位保持 None(§3 豁免申报),其中 θ/χ/η 族对应行 3/8/9/12
  系类条款「未到期不阻塞」,**不构成当前阻塞**。
- 行面(剩余阻塞,归属其它批):行 1/2(判读器迁移,判读批)、行 4/5/10
  (锚批分离+激活率门预注册,预注册批)、行 6(P3 统计量,语料批)、
  行 7/11/13(telemetry schema 三键,schema 批)、行 14(P2 档位登记批)、
  行 15/16(落码批验收申报)。
- 量具面(独立于 v6 的前置):**活性守卫 `action_family_liveness_gate(n=10)`
  红——`new_core:sell` 饥饿**(卖族 0 发射、无豁免)。实测 None 期同红
  ⇒ 预存、非本批引入;根因=M4 腾席路径(卖族唯一骨架义务位)在 10 seed
  从未触发(bench 未满)+卖 EV 面 T_SEARCH_A fail-closed,与
  SEEDS_EMPTY_LEDGER_DIAG 呈报项 2(M2 无候选回退→整局面零动作)同根。
  **建议单独立案**(`new_core:sell` 结构性饥饿),立案前正式 A/B 不得开跑。

**可豁免面**(活性守卫豁免机制自动推导):本批注入后 V_GAP 有值 ⇒ 刷新族
豁免失效且实测发射 >0(2 次/10 seed);buy/levelup 族骨架路径恒不豁免且
实测活;sell 族恒不豁免——即上述红。

## 2. 逐槽位标定(值·出处·方法·状态)

### 2.1 V_GAP = 24.7 金(P1 优先槽位)

- **值**:24.7,CI 带 [16.7, 24.7](CalibValue(ci_lo=16.7, ci_hi=24.7))。
- **出处**:既有校准工件 `tools/cw/calibration/calib_vuh_v1.py`「V̄ 合成价值链」
  (注册表锚、零新自由参数):rung 流 15.0(rung_value[2]=3.0 × rounds_left_est=5,
  e2 变体=合格集条件语义,P3 凑档累计)+ 胜率流 9.7(Δp(e0→e1)=0.277 ×
  单战 7.0 金 × battles_left_est=5;单战=expected_battle_loss 10 × hp_to_gold
  0.5 + 连胜金下界 2)。报告通道=calib_vuh_v1 stdout/JSON;同源声明=
  cw3 calibration.py V1(`v_bar_net_v1()` 注入源,k≥2 线性外推无标定出处 ⇒ 禁落码)。
- **方法(推导式)**:P40 待标定清单换算式 `V_gap(k=1) = V̄_net + 卡价`
  (毛值口径;A5 净值 V̄=V̄_net)。k=1 是唯一有标定出处的粒度。
- **端点纪律申报**(区间→取端):注入取**工件指定的 e2 变体(带上沿 24.7)**
  ——两变体不是同一量的 CI,而是两种语义读法(e1=每件一档跨越 16.7 /
  e2=合格集条件凑档累计 24.7),工件明文指定 e2 为注入值;带 [16.7,24.7]
  恰括 P40 S1 边界(16.7 关门/24.7 开门),A/B 敏感臂可用。**保守端对照实测**:
  16.7 注入下 n=5 刷新全 0(=关门端,双向实证);取 24.7 后刷新约束由 R1
  总账结构承载(§2.2),非「fail-open 放任」——diag §6.2「0<refreshes≪60+」
  由总账保证(实测 §4)。
- **状态申报**:【拟·标定批 V1】;`injected_form=True`(sim/A-B 驱动专用;
  生产开闸须标定批 CI 验收五件套,provisional.py 模块纪律)。改判
  【拟】→【注】/【证】须走登记。

### 2.2 R1 启动门总账裁决(诊断 §6.2 张力收口)

- **规格原文**(docs/game/currency_war/research/proofs/p40-refresh-ev.md ②):
  「R1 完成门(启动判据)——追缺口是不可分投资……启动 iff
  `c_eff·E[refreshes|j] + Σ卡费 + L(g, spend, R_全局, Ī) ≤ V_gap`」。
- **裁决**:**带总账(=「带预算上限」形态)**,非「开闸即放行进 r2」。
  后者系零刷新接线批的过渡形态(ZERO_REFRESH_FIX_REPORT §1 显式登记的
  标定批欠账:注入形态刷新 40-67/局 ≈ 反事实 C,EV 门无约束力);本批按
  规格落码闭合。判据本体=`criteria/refresh.r1_commitment_account`
  (k=1 单卡代表形态:Σ卡费在 k=1 与 V_gap(k=1)=V̄_net+同成员卡价两侧
  同成员相消 ⇒ 实际比较 `c_eff·E + L ≤ V̄_net`);装配=`shop.py
  _r1_member_accounts`。多类合格集 E[refreshes] DP 系 P40 结论待办,
  「逐成员单卡账取 min」为其可落码下界(独立近似偏紧向,P40 ①表注)。
- **口径申报**(全部保守向):j = bench∪deployed 1★ 副本 len 口径
  (decision_v2 `_vd_core_copies` 同源;j 低估 ⇒ E 高估 ⇒ 账高估 ⇒ 门收紧);
  c_taken=0(P40 清单「缺则 0 保守低估 q」);Ī = `income.net_income(
  round_num, streak_pre=0)`(streak 下界 ⇒ L 上界 ⇒ 账高估);R_剩余 =
  `horizon.r_remaining`(schedule_of 单一源,禁写死)。发射粒度=每商店波
  ≤1 刷(RefreshShop 截断点)⇒ 总账逐波以现 state 重算(波边界=新启动
  决策;j/gold 均已更新),期中续刷不建模——sim 波粒度边界,如实申报。
- **冲突呈报**:无残留冲突——编排者 2026-09-03「有值即放行」裁定系接线批
  在「开闸路径不可达」语境下的过渡口径,本批按规格取代并在其登记欠账处
  闭合;裁决变化链已在 shop.py 注释与 design_telemetry「标定批」节留痕。

### 2.3 V_MS = 24.7(同源注入)

provisional #2a/#2b 拆槽「**同源单标定禁双源**」:V_GAP 既标定,V_MS 必须
同值同源。行为面零变(V_MS 全部消费位均另有 U_X/T_SEARCH_A 前置 fail-closed,
实测 L1 全量无红)。状态同 V_GAP。

### 2.4 保持 None 的槽位(豁免申报,fail-closed)

| 槽位 | 状态 | 豁免/保持申报 |
|---|---|---|
| THETA / D_MIN / DELTA_HYST | None | 在档值(θ=1.0/δ=0.15/D_min=2)系**注入形态量级论证级**(R24-2/R36-2,非生产开闸口径)非标定值,禁充当标定灌入;A/B 预注册=两臂换线行为恒等(cw4 换线=影子面,不写 target_comp)⇒ 不灌值不影响 A/B 臂间 ledger;None 期 should_switch 不评估=设计内 fail-closed;行 3/8 类条款未到期不阻塞 |
| CONV_GOLD_PER_ROUND(χ) | None | 标定通道=sim 轨迹滞留事件回归(R44-2),无既有工件数值,禁硬凑;R63-3 采样循环(案③ 两态注入重标)未启动;None=窗口帧 C_stay/χ fail-closed;行 9 未到期 |
| U_X | None | 唯一在档值=p41 证明首版带**分档表**(1费0.05/…/5费0.15),与单浮点槽位粒度不匹配(R17-4 分槽/带序逐格)——落码需槽位重设计,出本批范围;ev_buy/ev_sell 面保持 fail-closed |
| T_SEARCH_A / LAMBDA_S_EQUIP / V_FURNACE / C_FRAME_Q / DELTA_P_WIN / P_HIT_Q_CONV / W_POP / RHO_IMPUTE / NBAR_ESTIMATOR | None | 无既有校准工件可推(查 calib_vuh_v1/注册表/证明件均无对应数值),按「推不出=显式 None+豁免申报,禁硬凑」保持;各自消费位 fail-closed 语义不变 |
| P_REC / BLOODLINE_HP_THRESHOLD / N_CRISIS / P3_LENGTH_STAT / F7_CONTINGENCY_ARMED / P_LAMBDA_QUANTILE / DELTA_PRIOR | None | 同上(P3_LENGTH_STAT 另有「通关语料出现前不可填」硬前提,R41-3) |
| V_BAR | None(封印) | R10-2 类型级封印:get 恒 None、inject 拒绝(测试锁在案),永不作闸门 |

## 3. 注入与验证(全实测)

注入通道:`ab_core_swap.apply_core_swap_calibration()`(显式调用;正式 A/B
入口与活性守卫前调;重注入前 `provisional.reset()` 清场)。

| 验收项 | 结果 |
|---|---|
| ① None 期零漂移(n=5,seed0-4) | 刷新 5/5 == 0;升级池化 156(与修复批一致) |
| ② 标定注入 n=5 冒烟 | 刷新 0/0/0/0/2(**>0,V_GAP 生效;总 2 ≪ 反事实 C 的 61-67**——diag §6.2「EV 门有约束力」达标);升级 168 正常;异常 0 |
| ③ K 回退正常 | `shop_k_fallback_p1_gap` 通道未动(K 空窗修复批代码零触碰);buy 族 61 次/10 seed(活性守卫计数) |
| ④ 保守端 16.7 敏感臂(n=5) | 刷新全 0(端点纪律双向实证:16.7 关门/24.7 开门,与 P40 S1 边界括注一致) |
| ⑤ 活性守卫 n=10(注入态) | baseline 全族活(refresh 77/levelup 372/buy 170/sell 41);**new_core:sell 饥饿 raise(0 发射)——预存红**(None 期同红实测;根因与豁免见 §1) |
| ⑥ v6 checklist 复跑 | 12 行未落地(判读批/schema 批/预注册批面)+4 行未到期不阻塞;`require_v6_green_for_formal_ab` raise(拦截态保持) |
| ⑦ CW L1 全量 | 2401 passed / 2 skipped / 1 xpassed + 1 预存红(test_cw_w614 旧核 digest——本批零触碰 decision_v2/runner.py,并行在飞文件所致,R198/K 空窗批同款申报) |
| ⑧ 本文件测试件 | test_cw_zero_refresh_fix 18 passed(含 slow 2);contracts/mandate 枚举 77 passed |
| ⑨ ruff | 4 个 src 改动文件全过 |

## 4. v6 终态判定

**不可开正式 A/B**。剩余阻塞清单(优先序):
1. `new_core:sell` 结构性饥饿(活性守卫红,预存;建议单独立案,根因疑与
   SEEDS_EMPTY_LEDGER 呈报项 2 同根——M2「只买精确线成员」无候选回退
   → bench 永不满 → M4 腾席永不触发);
2. v6 行 1/2(判读器词表迁移+prereg v6 节,判读批);
3. v6 行 7/11/13(telemetry schema 三键,schema 批);
4. v6 行 4/5/10(锚批/判读批分离+激活率门双相位重开预注册,预注册批);
5. v6 行 6(P3 fallback 治本事件,通关语料依赖)、行 14-16(登记/验收申报)。
标定面本身:V_GAP/V_MS 已灌值(§2),原「EV 槽位全 None」阻塞解除;
θ/χ/η 族类条款未到期不阻塞。

## 5. 登记节

- design_telemetry「标定批 V1」节:值/出处/方法/状态+R1 门裁决+新键
  (`shop_r1_account_over_vgap` / `shop_r1_no_chaseable_member`;
  `shop_r1_ev_unavailable` 语义收窄为 None 期专用)+复验数字(已落)。
- provisional.py 槽位状态申报:V_GAP/V_MS 经 inject 注入(值带 CI 与
  injected_form 标记);槽位表登记文本未改(【拟·未标定】标注由本报告与
  telemetry 节承载状态变化;槽位表原文描述消费位仍准确)。
- 测试锁改写申报:旧「注入 10.0 即刷」锁锁的是已废过渡形态,按锁纪律
  重推语义改写(新锁=总账过/深缺口拒双面,出处=本报告 §2.2)。
