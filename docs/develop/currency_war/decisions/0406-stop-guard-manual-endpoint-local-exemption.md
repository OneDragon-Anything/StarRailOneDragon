# 0406 停机守卫手动端点本地豁免:run 收口期不再清全局停机闩(W243,W241 A1b)

- 状态:accepted
- 日期:2026-08-27
- 关联:0396(停机守卫 as-built)、0388(CW 局部两层刹车,纵深防御共存)

## 背景与问题(W241 巡检实证)

ADR-0396 的手动接管出口是「MCP 手动输入端点先 `consume_stop_interrupted()`
清全局闩」。W241 审计五轮 A1b 发现该语义在 **run 收口期**是缺口:

- `stop_run` 返回 ≠ run 线程结束(`get_run_status` 过渡期仍 running,
  已文档化行为);run 线程 unwind 中时,状态已 STOP、停机闩已置。
- 「stop_run → 立即残局清理手动点击」是运维标准序——编排者在过渡期发
  第一笔手动点击,`consume_stop_interrupted` 把全局闩清位。
- W217 守卫层保护的正是 prep 流之外的**多动作 op 节点**(结算翻页/装备
  迭代类,单节点方法内连续点击;轮间 `is_context_stop` 检查拦不住轮内)。
  闩被清后,unwind 中节点的剩余点击全部放行 = 幽灵输入。
- W209j 层(prep 流,`last_run_result is not None` 判据)不受影响——
  单层剥落,但 W217 层恰是防轮内多动作的那层。

根因两问:根在「**单一全局闩被单 actor(手动意图)清除**」——守卫谓词是
全局的,消费者是局部的;修症状(消费前加状态检查)会把同一窗口内合法的
收口期手动清理一并挡掉。

## Considered Options

1. **消费前加状态检查**(`consume_stop_interrupted` 判 run 线程是否仍在
   unwind)——拒:合法的收口期手动清理恰好发生在同一窗口(stop_run 返回后
   立即清理是标准流程),状态检查无法区分「run 还在 unwind」与「run 已
   收完」,要么全放(=现状缺口)要么全挡(=挡残局清理)。且 unwind 完毕
   无可靠信号(run 线程物理结束才能观测,收口与线程退出之间仍有尾巴)。
2. **双层闩**(全局闩 + 手动闩,手动端点清手动闩)——拒:引入第二状态源,
   两闩组合语义(谁置谁清谁读)要全调用点重新论证,复杂度买不来比本地
   豁免更多的保护。
3. **【选定】手动端点本地豁免(thread-local exemption)**:`stop_guard`
   检查增豁免令牌(`threading.local`),MCP 手动端点以
   `stop_guard_exemption()` 上下文包裹 controller 调用——动作放行但
   **闩不清位**。豁免按线程隔离:手动端点跑在 MCP 请求线程,run 跑在
   executor 线程,unwind 中的 run 线程输入永远不持有令牌,守卫在收口期
   保持活跃。手动端点自身就是显式接管(外部主动发令 = 接管者意图),
   「豁免本次调用」与「清除全局状态」语义上本就该分开。

## 决策与影响面

- **改 one_dragon 公共包**(跨玩法影响声明):
  - `controller/stop_guard.py`:新增 `stop_guard_exemption()`(可嵌套
    context manager)与 `is_stop_guard_exempted()`;`check_stop_guard`
    在本线程持有令牌时不拦。**移除消费闩路径**。
  - `application_run_context.py`:**移除 `consume_stop_interrupted()`**
    (无剩余调用方;移除防再引入「单 actor 清全局闩」)。闩生命周期收窄
    为:stop_running 置位 / start_running 清位。
  - 未接线的项目/测试 mock 零感知(stop_guard=None 分支不变),向后兼容。
- **sr_od 侧**:`backend_context.py` 四手动输入端点(click_game/key_tap/
  drag/input_text)从「先消费闩」改为「豁免上下文内调 controller」。
- 正常期(闩未置)行为零变化:守卫本就不触发,豁免令牌是 no-op。
- ZZZ 同步点:见 `.debug/temp/zzz/2026-08-27-stop-guard-local-exemption.md`。

## 验证

- 锁跟语义变更(`test_stop_guard.py`):
  - `test_no_consume_entry_on_latch`:consume 入口已移除(防再引入);
  - `test_exemption_passes_but_keeps_latch_armed`:闩置位下豁免内动作
    放行、闩不清位、豁免退出后同线程(模拟 run 线程视角)输入仍被拦;
  - `test_exemption_is_thread_local`:豁免线程内,另一线程输入被拦
    (线程隔离,不引入新竞态)。
- 既有锁回归:闩语义 4 + 守卫语义 3 + 穿透语义 2 原样通过(仅 consume
  锁替换为移除锁)。
- ruff(改动文件)+ L1(cw_quick)+ 全量 pytest 0 failed。
