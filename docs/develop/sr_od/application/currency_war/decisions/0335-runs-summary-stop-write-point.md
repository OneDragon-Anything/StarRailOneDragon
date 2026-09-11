# 0335 - runs.jsonl stop 路径写端治本:收口迁 after_operation_done(W75)

- **Status**: accepted(2026-08-25;ADR-0273 之后 runs 断流的最后一块——stop
  路径哨兵 [RUNS-GAP] 四连报治本)
- **Context**:ADR-0273 已把 FAIL/崩溃/重启路径的 runs.jsonl 缺行用「start_run
  时点盘扫兜底(source='recovered')」堵上,但其前提是 **r363 已盖 stop 路径**。
  实机四局(时间窗 02:14/02:30/03:5x/05:5x)stop_run 后 [RUNS-GAP] 哨兵连报
  四连:r363 的 stop 兜底实际**从未触发**。根因排查(非判读,是写端实锤):
  r363 把检查放在 ``loop()`` 顶 —— 但 ``operation.execute()`` 每轮前
  (``operation.py:408``)先查 ``is_context_stop``,stop 到达后 ``loop()`` 不再
  被调,loop 顶检查几乎永不触发(MCP stop 到达 = execute() 下一轮 408 即 break,
  loop() 顶的检查在 stop 之后没有执行机会)。写端三路径审计:
  ① 3c 回大厅(正常终局 win/loss)——stop 不走此路;
  ② r363 loop 顶兜底(abandoned)——死码(本 ADR 治);
  ③ ADR-0273 兜底回填(source='recovered')——只在**下一局 start_run** 时补,
  最后一局/长时间停跑时缺口持续存在,哨兵在 5 分钟静默窗后即报。
- **Decision**:runs 行在「对局确定结束」的最早确定点写 —— ``after_operation_done``
  钩子(``operation.py:492``,execute() 对成功/失败/停止**全路径必达**)。在
  ``CurrencyWarRunLoop.after_operation_done`` 收口:未写 summary 且非假局时补写,
  取 ``session.last_state`` 最后已知 hp/plane/round(hp 走既有 ``_last_true_hp``
  防 100 兜底毒化),``result='stopped'``(is_context_stop)或 ``'abandoned'``
  (超时/异常退出)。r363 loop 顶死码删除;ADR-0273 兜底保留(仍盖进程崩溃/重启
  杀局——after_operation_done 在进程死亡时不执行,两类路径互补)。
- **Considered Options**:
  1. **r363 loop 顶补丁(维持现状 + 调阈值)**:否决——根因是检查点位置,不是
     阈值;loop 顶对 MCP stop 是结构性死码,任何阈值都救不活。
  2. **start_run 兜底提前(哨兵触发即回填)**:否决——把「下一局起点」改成
     「哨兵检测点」= 把遥测写端绑到监控脚本上,时序脆弱且违背「写端在游戏
     代码内」的单一职责。
  3. **after_operation_done 收口(采纳)**:execute() 全路径必达(成功/失败/
     停止/超时),与 3c 正常终局天然互斥(_summary_written 守卫),假局守卫
     (无 outcome 数据不写)镜像 3c 的 r10 判据,不污染分母。
- **验证**:单帧锁测试(构造 run 上下文 → stop → 断言 runs 行存在且
  result='stopped';非 stop 异常 → 'abandoned';已写/假局 → 不重复写)入
  ``test_cw_r363_audit_p0.py``;CW 快速集绿;schema 兼容性已核——runs.jsonl
  消费点(runs_gap 哨兵按 run_id 存在性判 / ``check_summary_write_path_coverage``
  按 run_id 判 / telemetry query 视图读 decisions/outcomes 不读 runs result)
  对新值 'stopped' 零破坏。
- **Consequences**:
  - 正:stop 路径 runs 行在停止瞬间写出(不再等下一局 start_run),[RUNS-GAP]
    哨兵源消除;超时/异常退出也从「等兜底」提前到「收口即写」;result 语义
    细分(stopped=停止 / abandoned=异常退出,与 recovered=崩溃重启互补)。
  - 负/风险:after_operation_done 在进程被强杀时不执行(覆盖不到崩溃路径,
    由 ADR-0273 兜底补位——互补非重叠);'stopped' 是 runs result 新值,
    历史统计脚本若按 result 白名单硬编码需加值(当前消费点已核零破坏)。
