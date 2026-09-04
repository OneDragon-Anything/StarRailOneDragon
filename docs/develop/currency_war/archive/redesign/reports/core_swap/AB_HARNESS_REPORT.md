# CW sim 换核 A/B harness 实跑报告(零漂移门 + 自配对)

> 任务:在 sim 侧实现「策略对象双臂换核 A/B harness」并实跑「零漂移门」,
> 为策略器换核对拍做好基础设施。需求书 = 本目录 `SIM_CONSUMPTION_MAP.md`
> §② 第 1 条 + §③「公平对拍判据」。
> 文件面声明(实际改动,git status 核对):
> - `src/sr_od/application/currency_war/sim/runner.py`(纯新增,见下)
> - `sr-od-test/test/sr_od/app/currency_war/test_cw_core_ab_harness.py`(新增测试)
> - `sr-od-test/cw_quick.txt`(登记上述测试一行)
> - 本目录 `run_gate.py` / `zero_drift_gate.json` / `self_pairing.json` / 本报告
> 主仓 `git status --short` 确认 src/ 下仅 runner.py 一处改动。

## 一、实现摘要

`sim/runner.py` 新增两个符号(插在 `simulate_p2_ab` 之后,`simulate_handoff_ab`
墓碑注释之前;既有函数零改动——`git diff` 可核,纯新增块):

1. **`_first_ledger_diff(ledger_a, ledger_b)`**(私有助手):两账本流首个差异
   行的定位描述(行号/轮次/差异键集;行数不等时报长度差)。只报定位不报
   数值——零漂移门锁的是「同环境同输入下逐位相等」这个事实,不是任何数字。
2. **`simulate_core_ab(old_strategy_factory=None, new_strategy_factory=None,
   n=100, *, pool='snapshot', seed_base=0, planes=1, use_refresh=True,
   invest=False, p2_combat=None, synthesis_chain=False,
   equip_wear_effect=0.0)`**:
   - 双臂同 seed_base/同 pool/同 planes/同 use_refresh/同
     invest/p2_combat/synthesis_chain/equip_wear_effect(全部显式透传给
     `simulate_p1`,与 `simulate_p2_ab` 形态对齐);工厂为无参可调用,
     **传 None = 该臂走 `simulate_p1` 默认构造**(不传 strategy 参数)。
   - **工厂每局各调一次**(非整臂复用单例):与 `simulate_p1` 默认分支
     「每局新构造 DecisionV2Strategy」对齐——策略对象若持有跨局可变状态,
     复用单例会产生与核差异无关的行为差,污染零漂移门。工厂必须确定性、
     不消费局内 rng 流(会话流派生 = seed 契约,`engine_p1.py` 内
     `StrategySession(rng=random.Random(f'sim-p1-{seed}'))`)。
   - **池一致性守卫**:双臂所有 `pool_fingerprint`(含 simulate_p1 内追加的
     `+eqgN` 位,`engine_p1.py` L641)必须全同,否则 raise——显式失败
     优于静默不公平对比。
   - **聚合双臂指标**(B1/B2 口径见下节)+ **配对差值与噪声带**
     (`check_ab_resolution_floor`,与 `simulate_p1_ab` 同款纪律)+ **零漂移
     读数**(`ledger_diff_pairs` 逐局账本逐位比、`ledger_first_diff` 首差定位、
     `identical_result_pairs` SimResult 全字段恒等对计数,dataclass eq)。
   - rng 中立性:harness 与工厂零 rng 消费;`logging.disable` 静音复用
     `simulate_p2_ab` 既有模式(finally 还原)。

测试锁 `test_cw_core_ab_harness.py` 三条(README 纪律:恒等断言取最小
n=1-2、池用 fallback、纯内存零落盘):
- `test_core_ab_zero_drift_gate`:工厂注入臂 ≡ 默认构造臂(n=2 恒等);
- `test_core_ab_self_pairing_identity`:同工厂双臂全字段恒等 + 配对差口径自洽;
- `test_core_ab_pool_fingerprint_guard`:monkeypatch 污染一臂指纹 →
  RuntimeError,且断言守卫在两臂各跑至少一局后才触发(非入口参数拒绝)。

## 二、零漂移门实跑结果(n=50,planes=1,seed_base=0,pool=snapshot)

臂 A = `DecisionV2Strategy(registry=sim_decision_registry())` 经 harness
注入(工厂每局新构造,注册表工厂外派生一次);对照组臂 B = `simulate_p1`
默认构造(不传 strategy)。命令 = `uv run python
.debug/temp/currency_war/core_swap/run_gate.py`(逐字可复跑,产物 =
`zero_drift_gate.json`)。**实测输出**(命令回显,非声称):

```
GATE: PASS {'n': 50, 'pool_fingerprint': 'a369f5ecf6626c66+eqg1',
 'ledger_diff_pairs': 0, 'identical_result_pairs': 50,
 'avg_hp_a': 49.82, 'avg_hp_b': 49.82, 'wall_seconds': 28.6}
```

逐位结论:
- **`ledger_diff_pairs = 0 / 50`**:50 个同 seed 配对局,`SimResult.ledger`
  逐行逐键全部相等(diff={},先例 = `engine_p1.py` simulate_p1 docstring
  planes=1 回归门);
- **`identical_result_pairs = 50 / 50`**:SimResult 全字段(dataclass eq,
  含 hp_trail/refreshes/p2_* 等全部观测面)恒等——注入路径零 rng 消耗
  差、零调用时点漂移;
- `avg_hp_a == avg_hp_b == 49.82`,headline 两臂完全一致
  (hp_ge_60=0.32, avg_refreshes_p1=7.28)。

门绿 ⇒ harness 注入路径对现役核**行为不可区分**,换核 A/B 的「臂 A」
可信。**未发现需要修复的漂移**。

## 三、自配对校验结果(双臂同工厂)

同 `run_gate.py` 第二段(产物 = `self_pairing.json`),n=50、planes=1、
pool=snapshot、两臂同一工厂:

```
SELF: PASS {'n': 50, 'ledger_diff_pairs': 0,
 'identical_result_pairs': 50, 'wall_seconds': 26.8}
```

50/50 配对局 SimResult 全字段恒等 ⇒ harness 自身不引入臂间不对称
(参数拼装、seed 编排、工厂调用次数两臂对称)。

## 四、耗时(实测,含计时数据)

| 项 | 实测 |
|---|---|
| 单局预检(seed=0 默认构造,snapshot,planes=1) | 0.25 s/局 |
| n=2 冒烟(4 局) | 0.96 s |
| 零漂移门 n=50(100 局) | 28.6 s(0.286 s/局) |
| 自配对 n=50(100 局) | 26.8 s(0.268 s/局) |
| 测试文件 3 条 | 5.95 s(单条 call ≤2.03 s,不入慢桶) |

均在基线 v3 单局 profile(0.34/0.49 s/局,SUMMARY「耗时总账」)量级内,
无热点。

## 五、B1/B2 口径核对

对照 `../sim_baseline_20260902_v3/SUMMARY.md` 的符号定义:
- **B1(planes=1)**:`avg_final_hp` = r9 boss 结算后 final_hp 均值
  (SUMMARY §B1 表第 1 行)——harness `headline.avg_final_hp` 同源
  (`statistics.mean([r.final_hp])`);`hp_ge_60` 同口径(final_hp≥60 占比,
  分母 = 全部局)。
- **B2(planes=2)**:`p2_hp0_rate` = 进 P2 后打到 hp0 占比,**分母 =
  进场局**(SUMMARY §B2:p2_entered_rate=1.0 时与全量同值;sim P1 无死亡
  出局建模,planes=2 时恒 1.0)——harness `headline.p2_hp0_rate` 分母 =
  `p2_entered` 局,与 `simulate_p2_ab._headline` 同实现形态;
  `p2_win_rate`(P2 内逐战斗轮胜率)、`avg_p2_rounds`、`avg_p2_refreshes`
  亦同构。本批实跑 planes=1 故 p2_* 为 null(边界如实报,不造假)。
- 噪声带判据 = `check_ab_resolution_floor`(配对差 sd 现算,|Δavg| <
  95% 底 = 噪声带内不得叙述方向;先例 `simulate_p1_ab` docstring)。

## 六、已知边界

1. **当前 snapshot 池指纹 = `a369f5ecf6626c66+eqg1`,与基线 v3 的
   `bfaf1c955ccc7752+eqg1` 不同**——池自基线采集后已再生。零漂移门/
   自配对是「双臂同池内部一致性」判据,不受影响;但**与基线 v3 跨池
   对拍不可比**(SIM_CONSUMPTION_MAP §③ 判据 1:跨日对照必核指纹)。
   换核 A/B 正式跑前需重采基线或核对新池归属。
2. `check_ab_resolution_floor` 在双臂恒等时 sd=0 → floor=0 →
   `noise_band=False` 且 note 提示「可叙述方向」——既有函数的边界行为
   (mean_diff 也是 0,实际无方向可叙),本批不改其语义;读者以
   mean_diff=0 ∧ sd_pair=0 判「恒等」。
3. harness 输出的 `avg_hp_a/b` 与 `headline.avg_final_hp` 是同一数字的
   两处回显(与 `simulate_p1_ab` 报告形态保持一致)。
4. 截断契约未碰:`engine_p1.py` L1027 / L1306-1312 的截断语义本批零改动
   (任务约束;契约冻结后若变,先过本 harness 零漂移门再动)。
5. sim 的决策日志(stderr)在 harness 静音模式下仍会输出——框架 logger
   不走 `logging.disable` 管辖(与 `simulate_p2_ab` 同现状),批量跑建议
   stderr 重定向;不影响结果与计时结论。
