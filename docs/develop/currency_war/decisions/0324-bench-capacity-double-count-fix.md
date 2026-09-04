# ADR-0324:bench_capacity 双重计数修复(N1)

- 状态:accepted(W52 批)
- 日期:2026-08-25
- 决策:见下「决策」节;正文落点 = `decision_v2/arbiter.py` 的
  `bench_capacity` 约束 + 主循环采纳段;W52 执行序第 1 步。

## 背景(现象与根因)

`decision_v2/arbiter.py` 主循环采纳买候选时同时做了两件事:
`working = simulate(working, cand.action)`(买入已落 bench——W51
ADR-0316 槽位模型下占用计数已 +1),又 `pending_bench += 1`。而
`bench_capacity` 检查用 `bench_occupied(working.bench) + pending_bench
>= bench_capacity`——同一笔买入被**双计**。

双计只在「同轮第二笔买检查时 working 恰剩 1 空槽」处显现误拒:
初始 7/9 占用 + 两笔买 → 第一笔采纳后 working=8/9(恰剩 1 空槽),
第二笔检查 `8 + 1 = 9 >= 9` → 被误拒;正确判据 `8 < 9` → 应采纳。
(设计稿 §0.5 的「8/9」指**第二笔检查时 working 的占用态**,初始
构造为 7/9——实现时按此口径落锁。)

**根在哪一层**:表示层(W51 槽位模型)引入的记账与约束判据不一致——
容量判据应读**占用计数**(simulate 后的真值),`pending_bench` 是
紧缩 list 时代的「未 simulate 的预占」记账,槽位模型下无此用例。

## 决策

1. 采纳买后**不再** `pending_bench += 1`;`pending_bench` 计数整体
   删除(`_check_constraint` 签名同步移除该参数;调用点两处更新)。
2. `bench_capacity` 判据 = `bench_occupied(working.bench) >=
   bench_capacity`(占用计数,§0.5 口径)。
3. 候选二(采纳时不 simulate 只记账)否决——改动大且与槽位模型
   的 simulate 语义冲突。

S3 同星豁免(ADR-0325)是对本判据的**例外追加**,非本修复的组成部分。

## Considered Options

- ① 删 `pending_bench`,容量判据=占用计数(采纳)——simulate 已反映
  买入,双计消除;现状无「未 simulate 的预占」用例(W51 合流后
  simulate 无异步入槽语义,重估条件满足)。
- ② 采纳时不 simulate 只记账(否决)——破坏主循环逐候选重验的
  simulate 推进语义,波及面大。

## 影响面

- 测试:`test_cw_adr0297_coexist_arbitration.py` 的 6 处
  `pending_bench=0` 调用点删除(签名变更);新锁
  `test_cw_w52_remediation.py::test_n1_bench_double_count_two_buys_both_accepted`
  (7/9 初始 + 两笔买 → 双采纳,修复前红修复后绿)。
- 行为变化清单:同轮多笔买的第二笔在「恰剩 1 空槽」时由误拒改采纳
  ——**意图内**(双计 bug 的修正);其余场景零变化。

