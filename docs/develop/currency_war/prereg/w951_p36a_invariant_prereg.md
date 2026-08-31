# W951 · P36-a 危机帧刷新通道不变式 · A/B 预注册(判前锁)

> 状态:判前锁——本文件在 A/B 跑批**之前**落盘,判读口径禁中途改。
> 命题出处 = `w945_strategy_design/DESIGN.md` P-新1-a(B>0⟹n≥1,结构已证零参数)
> + `w946_p36b_calib/REPORT.md` §3(实机 crisis 帧 RefreshShop p50=0、哑火帧 12/30、
> p_hit 宽口径 ≥0.94 两源)。机制定位 = `w951_p36a_impl/REPORT.md` §1
> (息档截断门 essential=False 车道在危机帧先拒,预算门未触达)。

## 1. 臂设计与单因子纪律

- **臂 off(对照)**:`sim_decision_registry()` 缺省(`crisis_refresh_invariant_enabled=False`,
  即现生产行为:息档截断门全域适用)。
- **臂 on(处理)**:同 registry 仅 `crisis_refresh_invariant_enabled=True`
  (预算>0 危机帧首刷 essential 车道,其余门不变)。
- 唯一差异 = 该开关一位;两臂其余注册表字段逐位相同(sim_decision_registry 派生)。

## 2. 窗口、n、配对

- seeds 连续 150 个(基座见执行脚本),**n=150/臂**,同 seed 配对,
  `simulate_p1(pool='snapshot', planes=2)` 同进程双臂(跨臂污染防线同 W947/W154 法)。
- 池指纹两臂一致先核(不一致=作废重查)。

## 3. 判据(跑前写死,判读零自由裁量)

| # | 判据 | 定义 | 达标线 |
|---|---|---|---|
| M1 | **主判据:哑火帧占比** | crisis 帧(`release_reason='crisis'` ∧ `release_budget>0`)中无 RefreshShop 动作的帧占比;配对差(on−off)+bootstrap 95% CI(B=2000,seed 20260912) | on 臂 ≈0(允许个别帧预算被买/升耗尽或无通道节点的合法残余);配对差 < 0 且显著 |
| M0 | 开火面 smoke(判前声明) | on 臂危机帧内出现由不变式车道放行的刷新(≥1 帧哑火被翻正) | ≥1 帧翻正,否则=输入死,中止并先补观测 |
| G1 | 守门:实花面不劣化 | 危机帧行动率(有 Buy/LevelUp/Refresh 任一动作的帧占比)配对差 95% CI | CI 下界 ≥ −2pp |
| G2 | 守门:hp 方向不劣化 | final_hp 配对差均值(只报方向,不判格) | 只报数 |
| S1 | 次要:危机帧刷新次数分布 | crisis 帧 RefreshShop 计数中位数/均值两臂对照 | on > off(方向性) |

## 4. 结论兑换映射(strategy-work §4 三选一,跑完当场兑换)

- M1 过 ∧ M0 过 ∧ G1 过 → 本批结论=**验证通过**,开臂判据成立,建议翻默认
  (翻默认=编排者裁决批,本批不翻)。
- M1 不过或 G1 破 → 开关保持默认关 → **删码留 ADR**(开关生命周期第 4 态),
  禁悬置默认关。
- off 臂哑火帧率 = 0(主窗内)→ sim 侧无复现域,本 A/B 不构成证据,判据改挂
  实机观察局(如实记 REPORT,不算通过也不算否决)。

## 5. 落码清单(判前登记)

1. `kernel/cw_registry.py`:`crisis_refresh_invariant_enabled`(默认关,并入 crisis 族)。
2. `decision/decision_v2/posture_release.py`:`crisis_invariant_lane` 判据单一址
   + `authorize_release_refresh` 截断门按车道分类 essential。
3. `decision/decision_v2/arbiter.py`:刷新收尾预截断门同址分类(消费点两处同判据,
   防预门拒/授权门放行的分类漂移)。
4. `sr-od-test/test/sr_od/app/currency_war/test_cw_w951_p36a_invariant.py`:
   单帧锁(on 保底 1 刷)/关臂零漂移锚/车道谓词边界/协同核对(W944 血预算门
   应急豁免不冲突)。
5. 禁碰面遵守:operations/、telemetry/、battle_loop.py、handlers/、prep_director.py、
   sim/ 零改动;禁 git commit。
