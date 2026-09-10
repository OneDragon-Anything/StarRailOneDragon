# ADR-0629: sim 次引擎期限检查口径单一源化——局终(全账本)口径

## 背景与问题

sim 批级检查 `second_engine_deadline`(sim/checks/runtime.py)的判据是设计表原文
「首引擎后 ≤3 轮内达次引擎或记原因」「never = 首引擎后**至局终**仍未凑出次引擎」,
但 `simulate_p1_batch` 的批级检查入参长期吃 `_Plane1View` 切片账本(ADR-0362 的
P1 段辖域切片,为 P1 锚定 headline 指标而设),且同一 `_ledgers` 变量被批级检查
族共享——**检查器自身语义声明「局终」,实现口径却是「P1 末」**,名实分裂由调用方
喂入面静默制造。

后果(T-211 归因批实证):planes≥2 批的 `never_second_engine` 是 P1 截断值,与
泛找批/复测批判读的全局面直算值直接对比,产生「never 21 超带」假警报(冻结
s8550 批:截断 21 vs 全局面 15;6 局二引擎在 P2 形成被截断口径记成 never)。
诊断批 T-211 候选方向①:键名标注 P1 截断,或改全量 ledger 口径。

## 决策

**选「改全量 ledger 口径」**(局终口径),键名零变更。实施三件:

1. **输入单一源化**:`run_batch_level_checks` 增可选参 `full_ledgers`;
   `simulate_p1_batch` 直传 `[r.ledger for r in results]`(P1+P2 全行)。
   `full_ledgers` 缺省回退 `ledgers`——纯 P1 批(planes=1)两者恒同,历史批
   输出**逐位零漂移**;口径漂移只发生在 planes≥2 批,恰是陷阱所在。
2. **跨段轮轴单一源化**:检查器内新增 `_game_round_of_row`——P2 段行
   round_num 段内重计(1..P2_ROUNDS),跨段 gap/期限窗算术直接用 round_num
   会在位面边界回卷(负 gap 被并进「限期窗内达成」;T-211 收尾脚本的
   delayed=34 即此轴混用伪影,自洽值 45)。单一源 = 账本行 `ts` 写入端
   (跨位面累计,P1 段 == rn);缺 ts(合成夹具/只读面)回退 rn+P1 域偏移。
3. **输出自描述**:返回 dict 增 `caliber_note` 键,批报告消费方在陷阱现场
   (checks 段)直接看到口径声明。

### 为何否决「键名标注 P1 截断」

- 名字只对「看名字的人」生效,防不了比较错误——跨批对比仍要求每个消费者
  记得换算口径,陷阱每次对比重新可犯;值统一才结构性消除。
- planes=1 批下 P1 截断 ≡ 局终,`*_p1` 键名对存量大部批名实不符。
- 改键名破坏 T-206 分键的历史连续性(在案判读引用旧键名),扰动大于收益。

### 为何只换这一个检查的输入

其余批级检查的判据轮域是 P1 段锚定(r≥6/r≥7/rn==6 等),P2 行 round_num
段内重计会**别名撞进同数值 P1 轮域**(如 P2 r6 命中 `rn==6`),喂全量账本
= 静默污染。P1 段视图喂入对其余检查是承重的(ADR-0362),维持不变。

## 冻结账本实证(锚)

`.debug/temp/currency_war/validate_t212.py` 可复跑(20260910 九批,池指纹
460e6031):全局面 never 序列 2/0(n50)/1/11/12/12/15、P1 截断 3/0/1/22/
24/20/21,与 T-211 归因批 §2 直算表**逐位一致**;s8350 冻结↔收窄重放配对在
局终口径下零翻转保持(never 12→12 / delayed 45→45),T-211 配对结论跨口径
换算不失效。planes=2 真实小批(n=2 fallback)批出口出数且带 caliber_note。

## 影响

- 零策略代码、零策略行为;纯诊断基建面(观测口径)。
- planes≥2 批的 `never_second_engine`/`delayed_miss`/`avg_gap` 等键值自此为
  局终口径;planes=1 批逐位不变。跨批判读无需再核对账本辖域(陷阱消除)。
- 防回退锁:`test_second_engine_deadline_game_end_caliber`(语义+接线双钉,
  变异红证=T-212 批验证记录)+ `test_sim_batch_p2_second_engine_full_ledger_wiring`
  (生产穿线烟雾)。

## 状态

已实施(2026-09-10,T-212 批;归因=T-211 交付报告,数据锚=冻结 20260910 批)。
