# CW K 空窗回退修复报告(第三病灶:seeds1-3 整局零动作死锁)

> 修复日期:2026-09-03。权威诊断=`.debug/temp/currency_war/ab_run_20260903/SEEDS_EMPTY_LEDGER_DIAG.md`
> (先读);修法=诊断 §4 第一案(编排者裁)。本报告=修法/契约/行为锁数字/
> 反事实复验对照的单一事实源;登记节=design_telemetry「K 空窗回退修复批」。

## 1. 修法(代码面)

**病灶**(诊断 §2-§3):`decide_shop_wave` ①段 K 投影 `k = session.target_comp`
在 P1 空窗期(`target_comp=None`,bench∪deployed 四体系最高支持度 <
`P1_PAIR_LOCK_MIN_SUPPORT=0.5`)投影为空 ⇒ M2/M4/支付支撑全关 ⇒ 整局零动作
死锁(K 空→零买入→板面零变化→支持度永不涨→永不锁)。第三例
「单一值域的一端当全域」域错位(arm1 cap 口径/零刷新 r1 输入同型)。

**修法**(逐文件):

| 文件 | 改动 |
|---|---|
| `kernel/cw_intention.py` | 新增只读判定 `p1_gap_window(state)`:`max(_p1_system_support) < P1_PAIR_LOCK_MIN_SUPPORT`(与 `_derive_p1_pair` 不锁分支同源,单一支持度算式,判据数学零改动) |
| `decision/cw4/shop.py` | ①段加 K 空窗回退:`k is None` 且 plane=1 且意向供给在(`v3_intention` 非 None)且 `p1_gap_window(state)` ⇒ `k_members = tuple(sorted(hoard_target_set(state, ist).char_targets))` + `shop_k_fallback_p1_gap` 计数。sorted=确定性发射序(str 哈希随机化下 frozenset 迭代序跨进程不稳定)。**单一源=hoard_target_set(旧核空窗回退同一函数,禁复制四体系全集逻辑)**;非空窗期(锁线物化⇒k 非 None;支持度≥0.5⇒pair 锁)行为不变;意向供给缺帧=保守侧不回退(现行 () 行为) |
| `decision/cw4/criteria/contracts.py` | 契约登记(见 §2) |
| `IMPL_DESIGN.md` §4.2.2 | 规格补注(见 §5):空窗期方向形态=R198 标形态,2026-09-03 第三病灶裁定,单一源指向 hoard_target_set |

连带口径(诊断 §4 预告,实测确认):回退使 `missing` 成员集变大 ⇒ M4/M2/
支付支撑通道在空窗域开通——与旧核空窗行为对齐,即诊断反事实脚本的行为面。

## 2. 契约登记(R198 契约纪律形态)

- `CONTRACTS[('shop', 'k_projection')]`:前提谓词 `_k_projection_domain_full`
  =「战略层产物字段值域全集含空窗期——K 投影域覆盖 None,空窗回退单一源
  =hoard_target_set」;消费位(shop.py ①段)声明
  `ContractCtx(k_none_domain_covered=True)`,违例 ⇒ 不回退 + 
  `criteria_contract_violation:shop.k_projection` 计数(键族前缀=R198 节
  ensure_contract 单一源,分键自动展开)。
- 规格锚=SEEDS_EMPTY_LEDGER_DIAG §3/§4 + IMPL_DESIGN §4.2.2 规格补注。
- 新键 `shop_k_fallback_p1_gap` 登记=design_telemetry「K 空窗回退修复批」节。
- 约束遵守:判据数学零改动;契约 v2 正文零触碰;冻结族/冻结残余 11 项零触碰;
  每处代码修注含三元组语义(病灶出处/修法依据/边界)。

## 3. 行为锁(测试,7 条新用例全绿)

`test_cw4_shop_line.py::TestKGapFallback`:

1. **①空窗死锁场景**:bench=注册表外散件(支持度 0<0.5),target_comp=None,
   意向供给在 ⇒ 店面引擎件经 M2 发射(`reason='m2_line_member'`)+
   `shop_k_fallback_p1_gap≥1` ✓
2. 回退单一源锚:空窗帧回退计数在(投影=hoard char_targets)✓
3. **②非空窗行为不变**(支持度恰在锁线 0.5):bench=桑博单件 ⇒ 不回退
   (无 m2 发射/无回退计数)✓
4. **②非空窗行为不变**(锁线后):target_comp 非 None ⇒ 回退分支不辖 ✓
5. 边界:v3_intention 缺失 ⇒ 保守不回退 ✓

`test_cw4_contracts.py`:

6. **③契约正反测**:`k_none_domain_covered=True` 放行 / `None`(字面量
   空元组回退形态)弃权+`criteria_contract_violation:shop.k_projection` 计数 ✓
   (注册完备性断言同步扩 `('shop','k_projection')` 键)
7. 接线零误伤锚:空窗帧 k_projection 零违例计数 + 回退计数在 ✓

## 4. 反事实复验(全实测;脚本=core_swap/k_fallback_recheck.py,原始数据=k_fallback_recheck_raw.json)

口径=诊断批同款(mandate_v1,planes=1,use_refresh=True,pool=snapshot;
基线=诊断批 `seeds_empty_ledger_cf_raw.json` baseline 字段,seeds 0-99):

| 指标 | 诊断(修复前) | 修复后 | 诊断反事实 | 判定 |
|---|---|---|---|---|
| 零动作局(n=100) | **21/100** | **0/100** | 0/100 | ✓ 21→0 |
| 受累 21 局 avg_final_hp | **16.05** | **33.52** | 33.52 | ✓ 与反事实逐位一致 |
| 受累局 avg 动作数(修复后) | 0 | 41.8 | 41.8 | ✓ |
| 全 100 局 avg_final_hp | 31.93 | 39.24 | 39.24 | ✓ (+7.31,B1 缺口回收带≈36% 口径维持) |
| seeds1-3 逐局 | 0/0/0 动作 | 全部有动作(诊断脚本逐波复跑确认 K 回退+买入/升级发射) | 有动作 | ✓ |
| seed0 | 31 动作/hp1/ref0 | 31/hp1/ref0 | — | **drift=0** ✓ |
| seed4 | 20 动作/hp7/ref0 | 20/hp7/ref0 | — | **drift=0** ✓ |

与反事实逐位一致的原因:实装回退集=hoard_target_set 空窗分支(p1_transition
=四体系引擎件全集),与反事实 monkeypatch 的 `sorted(_pair_members(_P1_PAIR_PREF))`
同集合同序;空窗门(支持度<0.5)在 P1 域与「target_comp=None」重合
(pair 锁即物化 target_comp),两路径等价。

## 5. 规格补注(IMPL_DESIGN,附带项)

IMPL_DESIGN §4.2.2(判据契约纪律节)追加 R198 标形态规格补注:战略层产物
字段(`update_target` 的 `target_comp`)值域全集含空窗期(None);商店波方向
pass 的 K 投影域必须覆盖 None——P1 空窗期 K 回退单一源=
`cw_intention.hoard_target_set(state, ist).char_targets`(禁复制逻辑);
非空窗行为不变;消费位契约=`CONTRACTS[('shop','k_projection')]`。注内注明
2026-09-03 第三病灶裁定(SEEDS_EMPTY_LEDGER_DIAG §4)。

## 6. 验收记录

- **cw4 快集**(`uv run pytest sr-od-test/test/sr_od/app/currency_war -m
  "not slow and not legacy_baseline"`):**2400 passed**,2 skipped,1 xpassed,
  **1 failed=test_cw_w614 旧核零漂移 digest**——预存红,与本批无关(证据:
  `git stash` 本批唯一 tracked 改动 kernel/cw_intention.py 后单测仍红;红源=
  并行批在飞文件 decision_v2/sim 等工作区改动,R198 节同款预存红申报;
  本批对旧核路径零调用面改动)。
- **ruff**:三改动源文件(cw_intention.py / shop.py / contracts.py)
  All checks passed。
- **seed0/4 行为不变**:上表 drift=0(actions/final_hp/refreshes 逐位相等)。

## 7. 呈报项

- 空窗首波边界:开局第一波商店若发生在 update_target 首跑前(v3_intention
  尚 None),保守不回退(该帧 K=();sim 实测该帧亦无预算异常,后续帧回退即
  接管)——与 committed_authority 缺供给保守侧同款语义,非缺陷;如实申报。
- B1 剩余劣化大头仍系零刷新 V_GAP 标定开闸、EV 面标定等既知未标定面
  (诊断 §5 口径维持,本批不动)。
