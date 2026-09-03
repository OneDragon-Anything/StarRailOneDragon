# CW 换核迁移序 步0 独立前置批报告(R189-3 裁决执行)

> 批范围(权威规格 = `../redesign/IMPL_DESIGN.md` §6.4-R R189-3 节 + §2.12 前置缺陷
> 清单;修复形态 = `../redesign/design_economy.md` §E6):共享底座两缺陷修复 +
> 定向零漂移门 + 基线 v4 重采。日期 2026-09-03,git HEAD
> `6afc919818b1719ed29d676531163e3cfd613d94`(工作树含并行批在飞改动,见下文
> 「执行事故与隔离」节)。

## 1. 前锚采集(n 与耗时)

- 跑法:`simulate_p1` 直跑,planes=1,seed_base=0,snapshot 池(指纹
  `a369f5ecf6626c66+eqg1`),PYTHONHASHSEED=0(见 §4 隔离说明);批量前单 seed
  计时预检 = **0.24s/局**(狸臂 0.26-0.31s/局实收)。
- 三臂(脚本 `pre_fix_anchor/run_anchor.py`,数据 `pre_fix_anchor/*.jsonl`):
  | 臂 | n | 注入 | 用途 |
  |---|---|---|---|
  | tanuki | 40 | SimInvestProfile 固定剧本 r1 选 狸财经狸 | 门主臂(flat=2,注册表亲读) |
  | noinvest | 40 | invest=False | 无持卡零漂移控制 |
  | capcard | 10 | r1 选 利息上调(cap=5 既有枚举) | 有持卡但与五族无关控制 |
  采集耗时 12.0+10.5+2.8 ≈ **25s**。
- **为什么用固定剧本而非 invest=True 随机采样**:plaza 实选频次表
  (`strategy_freq_table()` 亲跑)**不含 狸财经狸** ⇒ invest=True 永远采不到狸局,
  门会空转;固定剧本 = w162 SimInvestProfile 测试臂的既定用法,等效注入狸局。

## 2. 修法摘要(两处)

### 2a. aggregate_economy 五族枚举补全(R83-1/R85-3;形态 = §E6 分型登记)

`kernel/cw_investments.py` `aggregate_economy`(重建枚举)按 §E6 分型补:

- **数值字段加法求和**:`interest_flat_per_node` / `gold_at_node` / `gold_at_level` /
  `xp_click_discount_from_level`;
- **触发配对字段守卫 min 并宽(哨兵 0)**:`gold_at_node_offset` /
  `gold_at_level_target` / `xp_click_discount_from_level_at`——最早触发位代表
  聚合时点,与 `refresh_surprise_every` 既有形态(L600-602 批时快照)同构。
- 禁全字段直加恪守:五族未做任何 max/直加混写;docstring 声明边界 = 标量载体对
  「多条目不同触发位」有损,精确多条目消费走 cw_effect_ledger 逐策略路径
  (gold_at_level_effect / conditional_effects_at,不经聚合)。
- **分型登记机器可读单一源 = 测试位分型表**(§E6 裁决「代码即载体」):新测试
  `sr-od-test/test/sr_od/app/currency_war/test_cw_economy_aggregate_typing.py`
  内 `AGG_FIELDS`(26 聚合型字段→算子规约 sum/max/guarded_min/or/prob/filter_max)
  + `AGG_EXCLUDED`(12 个不进 aggregate 字段,各注归位通道:bool 行为条件流 /
  tuple 限定族 / 期权 str / 难度账逐策略 / xp_instant oneshot 选卡时点 /
  合成触发族 ledger 逐策略路由 / sell_price_mult 出售动作面)。
- **三半边断言**(同测试位共位):① `EconomyEffect` 全字段 ⊆ 分型登记
  (dataclass fields 亲数对照,未登记即红);② 聚合型 ⊆ 实现枚举(单条目非默认
  探针,静默丢值即红);③ 实现聚合形态 ≡ 登记语义——**测试位参考求值器**由
  分型表机械驱动(算子规约+哨兵+初值=字段默认恒等元;filter_max 走过滤后置
  通道),对拍 `aggregate_economy` 输出;求值器零字段名分支 = 不构成第二份聚合实现。
- **fixture 区分力义务**(§E6 伪护栏封口):or vs max(xp_buy_hp_cost (6,8)→6,
  注册表现状该字段至多一策略持有,区分输入系注册表外构造)、守卫 min vs 裸 min
  (含 0 值成员)、max vs sum、五族逐族 sum-vs-max / 触发位 guarded-min-vs-sum/max
  构造、economy=None 恒等元条目、未注册名 miss 路径;另含**区分力非零证明锚**
  (`test_half3_detection_power_proof`:篡改分型表 or→max 后,同 fixture 下求值器
  与实现必须分歧——「仅隶属断言恒绿、语义等价断言红」的构造存在性被显式验证)。
- 测试缝 = monkeypatch 整表替换 `INVESTMENT_STRATEGIES`,条目经
  `normalize_invest_name` 归一键入册(与生产同缝;§E6 落选案「改签名收效果列表」
  未采用)。

### 2b. sim 利息 flat 分量(R92-4,依赖 2a 先行)

`sim/engine_p1.py` 收入段利息行:`min(_icap, st.gold // 10)` →
`min(_icap, st.gold // 10) + _flat`,`_flat = _agg_inv.interest_flat_per_node`
(无持卡=0)。**量值与条件单一源 = cw_investments 注册表**(狸财经狸
`STRATEGY_ECONOMY['狸财经狸'] = EconomyEffect(interest_flat_per_node=2)`,亲读),
sim 侧零常量;与 interest_cap 无关(EconomyEffect 字段注释语义,加在 min 之外)。

## 3. 定向零漂移门(实测)

**执行环境**:`gate_env/` = 主工作树整树冻结副本(robocopy,13:17 时点)+ 字符串级
撤除/重挂两处修复(`gate_env_tool.py`,已清理)——改前臂=副本撤修复,改后臂=副本
挂修复,**两臂同底座**,与并行批的持续在飞编辑隔离(隔离动机见 §6)。两臂均
PYTHONHASHSEED=0(装备 set 迭代序跨进程噪声,§5)。比对 = 双侧同经 JSON 规范化
后逐局逐位(修前锚 jsonl vs 重跑 ledger;tuple/list 归一)。

**预注册利息行族清单**(门判定辖域,跑比对前显式枚举):
- 直接受影响:账本行内 `sim.income.interest`(利息行本体)、`gold`(轮末金)、
  `sim.spend.*`(金变化传导的支出分解);
- 由其派生的下游行:首差行之后的全部行为面键(actions/state.*/hp 族/sim.delta/
  refresh 族…)——金进入决策与状态,行为面整体下游,不设键位白名单;
- **门判据**:①无狸臂(noinvest/capcard)ledger **逐位相等**(清单外零 diff 的
  最强形式);②狸臂每局**首个差异行**必须含 `sim.income.interest` 差异(分歧源
  = 利息行;此前行逐位相等由「首差行」定义保证)。

**门结果(rc=0,全绿)**:
```
[gate:tanuki]   bit_equal=0/40  diff_games=40 first_diff_not_from_interest=[]   ← 40/40 局分歧,全部源于利息行
[gate:noinvest] bit_equal=40/40 diff_games=0  ← 清单外零 diff
[gate:capcard]  bit_equal=10/10 diff_games=0  ← 清单外零 diff
```
逐条辖域判定:狸臂 40 局首差行 = 第 2 行(r1 选卡在收入结算后,r1 收入未受染 ⇒
第 1 行恒等;亲验 40/40 局 row[1] 利息键在差集内);首差处利息增量恒 = +2
(注册表 flat 值);后续行增量谱 {+2:179, +3:59, ±1/-1/…} = flat 直加 + 金跨
十位档的复利效应 + 支出路径重排(预期下游,辖域内)。noinvest/capcard 两控制臂
零 diff 同时封死「aggregate 修复本身扰动决策」(kernel 决策链无五族消费者,
grep 亲验:cw_economy/cw_effect_ledger 消费面均不经聚合读五族)。

## 4. 基线 v4 摘要

- 落档 `../sim_baseline_20260903_v4/`(SUMMARY.md + 两批副本 + 检查网日志 +
  确定性复验档案 `detcheck/`)。B1 planes=1 n=500 seeds 0-494(161.9s);
  B2 planes=2 n=300 seeds 0-299(115.3s,P2 分母=进场局=300)。
- **池指纹(如实记录当前 snapshot 值)`a369f5ecf6626c66+eqg1`**;coarse=4 /
  economy=2(与 v3 同,唯池不同)。
- B1 主数:avg_final_hp 45.80±1.95 / hp_ge_60 0.298±0.040 / boss 胜率 0.254±0.038 /
  末金 53.44±1.27;B2 主数:p2_hp0_rate 0.610±0.055 / P2 存活 0.390±0.055 /
  p2_win_rate 0.257 / P2 末 hp 10.79±2.23 / 承接血量 45.88±2.54。
- v3→v4 全指标半径内(差异源=池漂移;两修复在 B 口径 invest=False 下零漂移,
  与本门 noinvest 臂互证)。**狸局路径 v4 已变**(每轮利息 +2)——invest 注入批
  禁用 v3 数字对拍。
- 确定性复验:前 20 局重跑 outcomes 逐行相等(180 行);decisions 跨进程差异
  辖域 = 装备列表序键(state.{bench,deployed,equipped}/worn_equips_total),
  **本批之前已存在的 set 迭代序噪声**,与本批无关(已定位并在 SUMMARY 声明)。

## 5. 执行事故与隔离(呈报)

1. **git stash 链事故**:临时 stash 两修复以重采改前锚时,与并行批对
   engine_p1.py 的在飞编辑冲突,pop 失败;恢复过程中一次 `git apply` 行为异常
   (仓库内 cwd 语义),一度使 engine_p1.py 落回 HEAD+CRLF 态并抹掉并行批的
   半截 import(`snapshot_expected_paths`,该 import 指向当时尚不存在的函数,
   本身使模块不可导入)。处置:①我的修复以字符串级重挂并核验;②并行批的
   半截 import 予以下线(恢复可导入态;其函数落地后由该批自行重挂);③后续
   改前/改后切换全部改用冻结副本 + 字符串级工具,不再碰 git stash/apply。
   **教训(跨批适用):并行批共用文件上禁用 stash/apply 类工作树级操作。**
2. **比对器两轮假红**:第一轮未固定 PYTHONHASHSEED(装备 set 序跨进程漂移,
   全臂假 diff 于 equips 键);第二轮 anchor 走 JSON 回读而活 ledger 含 tuple
   (tuple≠list 恒假不等,假 diff 于 p1_pair 键)——修正为双侧 JSON 规范化 +
   固定 hash 种子后门通过。假红均未据以做任何裁决。
3. **HEAD 不可用作门基座**(旁证):worktree HEAD 的 engine_p1 含未配套 import
   的 `_expected_paths_snapshot` 调用(并行批半落地提交),NameError——门基座
   最终取主树冻结副本(含并行在飞编辑,两臂同底座故有效)。

## 6. 测试锁处置

- 新增:`test_cw_economy_aggregate_typing.py` 5 用例(三半边+区分力+证明锚),
  全绿。
- 既有锁:**零锁红**——test_cw_investment.py(88 passed, 1 xpassed)+
  test_cw_decisions.py 全绿;sim 域 test_cw_sim_suite / test_cw_plane_p2 /
  test_cw_intention_switch 快速桶 189 passed。两修复均无既有锁钉住被改语义
  (aggregate 五族此前无消费断言;利息行无 sim 侧数值锁),无「跟绿/呈报」
  裁决项。
- ruff check(仅本批改动文件:kernel/cw_investments.py、sim/engine_p1.py、
  新测试):All checks passed。

## 7. 耗时

前锚预检+采集 ~1.5min;两修复落码 ~10min(含 stash 事故恢复 ~20min);门比对
三轮(两轮假红+终轮)~6min;typing 测试编写+调绿 ~25min;基线 v4 两批+复验+
指标 ~7min;SUMMARY+本报告 ~25min。**全程约 95min**(含事故开销)。

## 8. 本批文件清单

- 代码:`src/sr_od/application/currency_war/kernel/cw_investments.py`
  (aggregate_economy 五族+docstring)、`src/sr_od/application/currency_war/sim/engine_p1.py`
  (利息 flat 分量)。未触碰 decision/ 与 strategies/(策略器侧)与 redesign 文档。
- 测试:`sr-od-test/test/sr_od/app/currency_war/test_cw_economy_aggregate_typing.py`(新)。
- 数据:`core_swap/pre_fix_anchor/`(run_anchor.py + fix.patch + 三臂 jsonl)、
  `sim_baseline_20260903_v4/`(SUMMARY.md + 两批副本 + 日志 + detcheck +
  compute_baseline_metrics.py)。
