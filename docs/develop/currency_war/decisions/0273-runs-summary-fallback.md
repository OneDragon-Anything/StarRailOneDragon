# 0273 - runs.jsonl 局终汇总多路径兜底(批⑧ F2 断流修复)

- 日期:2026-08-24
- 状态:accepted
- 关联:批⑧ F2(`sim_压测_批⑧_2026-08-23.md`)/ 批⑨ F7;r363(审计 P1-6 stop 路径兜底);批⑧检查项 `summary_write_path_coverage`

## 背景 / 决策驱动

2026-08-22 17:00 起 18 局仅 2-3 局落 runs.jsonl(批⑧实测 16/18 缺,批⑨复认 3/10)。r363 的兜底
只在 **loop 顶检测 stop 信号**时补 abandoned——battle_loop.py:482 注释自认的盲区仍在:
FAIL(对局循环超时/节点失败)、进程崩溃、重启杀局,这些路径既不走 3c 回大厅也不经 loop 顶
stop 检测 → decisions/outcomes 已落盘而 runs.jsonl 缺行。消费影响:一切以 runs.jsonl 为分母的
跨局统计(胜率/终局分布/ADR-0245 checks 的 coldstart 分母)当前失真。

## 决策

收口改「**多路径兜底**」,落点在 telemetry 侧(recorder 落盘时点统一兜,不改 battle_loop):

1. `start_run()`(每局起点)先调 `recover_dangling_run_summaries()`:扫 outcomes.jsonl 里
   没有 runs.jsonl 行的 run,`build_recovered_summary` 从逐轮行重算补一条,
   **幂等**(runs.jsonl 已有该 run_id 则跳过;同 run 不重复)。
   - 下一局起点兜 = 覆盖 FAIL/崩溃/重启三类路径的最小公共收口点(进程活着 → 下局启动时兜;
     进程死了 → 新进程首局启动时兜;两者都读盘,内存态非必需)。
2. 重建口径:末条真值按 **(plane, round) 排序**(round_num 是位面内编号,批⑧边界);final_hp
   取 conf≥0.9 末条(镜像 loop `_last_true_hp`,死局 100 兜底不毒化);final_hp≤0 → `loss`,
   否则 `abandoned`(FAIL/崩溃局无终局判定,如实标);pivot/gold 轨迹从 decisions 重算
   (内存 _comms 同语义)。
3. `RunSummary` 加 `source` 字段:'' = 正常/stop 路径写;'recovered' = 兜底回填(数据治理
   「补算回填行标注来源」的 schema 落点,防再犯不靠手工)。
4. 无 outcomes 的 run(开局失败/假局守卫合法跳过)→ **留缺口不造伪值**。
5. 检查项 `summary_write_path_coverage` 入生产 checks 栈(`run_checks_on_replay` 头部,
   与逐局 coldstart 检查正交——它是「分母完整性」):最近 10 局 runs.jsonl 覆盖率,
   违规带 run_id 溯源;验收线 = 连续 10 局 100%。

### 数据治理执行(2026-08-24)

污染窗口 = 8/22 17:00 起(采集 bug 引入批——即 r363 之前的盲区,非发现日)。真值可从
outcomes/decisions 重算 → 补算回填:**15 局**补写(source=recovered,全部 result=abandoned),
局63-72 的 10 行含于其中;回填后最近 10/18 局 coverage 100%。口径边界:recovered 行的
`result` 可能偏保守(战败结算屏 hp 真值未落高置信 outcome 的局标 abandoned 非 loss)——
判读时以 notes='recovered:...' 区分。

## Considered Options

| 选项 | 结论 |
|---|---|
| **A(选定):start_run 时点盘扫兜底(telemetry 侧)** | 单一收口点盖 FAIL/崩溃/重启全部路径;幂等读盘,内存态非必需;battle_loop 不动(他批在飞区) |
| B:battle_loop 各 FAIL/异常路径逐一补写 | 路径枚举不可穷尽(崩溃/重启根本不执行代码);每加一个出口就要记得补一处 = 漏网永存 |
| C:recorder 析构时兜(`__del__`) | 崩溃/强杀不保证执行;时序不可控 |
| D:只加检查项不修写端 | 分母失真持续,检查项沦为恒报警 |

## 后果

- 跨局统计分母恢复完整;`checks` CLI 首行即披露覆盖率。
- recovered 行是**重算近似**(rounds_survived=末条位面内编号;pivot 由 target 序列推导)——
  与正常行混排时按 source 区分,统计口径敏感的判读(如 result 分布)建议过滤或分层。
- 开局失败局永久无行(合法缺口;分母语义 = 「打过至少一回合的局」)。

## 验证

- 锁:`test_cw_r412_runs_summary_fallback.py`(重建口径 loss/abandoned/conf 门 / 幂等二次空 /
  无 outcomes 不造伪值 / 检查项双向)。
- 实数据:回填 15 行后 `check_summary_write_path_coverage(recent=10/18)` 均 100%。
- 既有锁适配:`test_cw_telemetry_checks.py` fixture 补 runs.jsonl(合成语料本就该有,非断言放宽)。
