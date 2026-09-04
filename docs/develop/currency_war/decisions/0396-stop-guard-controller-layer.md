# 0396 停机刹车语义框架级重写:controller 层停机守卫(停机后零游戏输入)

- 状态:accepted
- 日期:2026-09-01
- 关联:0388(CW 局部两层刹车,第一代补丁)、0395(CV 读数防抖)

## 背景与问题

运维契约:「用户要用电脑 = 全停」——停机(stop_run / GUI 热键 / 钩子)后,bot
不得再向游戏/桌面注入任何输入(点击/拖拽/按键/滚轮/打字/移动光标),否则抢用户鼠标。

run 26(`run_20260826_122120`,08-26 白天)实证:.log/mcp_server.log 08-26 段
12:56:12.529 `指令[ 货币战争-全员装备 ] 执行失败 已停止[gui:hotkey]` 之后
**12:56:16.229 `step4 StartBattle → ✓ 出战成功`**——停止信号已被执行流看见
并上报,但同一轮次内的 director 步进链继续发起了下一步动作并点击了「出战」,
随后又进入了等待与收口(12:56:21 才完全退出)。跨轮次窗口更长的形态(备战
整环 1-2min、战斗等待 4-5.5min)即「7min 幽灵活动」量级的来源:stop 到达
与最后落点动作之间隔着「当轮节点方法的剩余执行链」。

## 根因环节链(stop 信号 → 实际停止,行号级)

1. **信号**:GUI 热键 `one_dragon_context.py:344` / MCP `backend_context.py:359`
   / 钩子直调 → `ApplicationRunContext.stop_running`
   (`application_run_context.py:417`)→ 只设 `_run_state=STOP` + 发事件,
   **不中断任何线程**。
2. **唯一消费点**:`Operation.execute` while 循环**顶部**的轮间检查
   `is_context_stop`(`operation.py:408`)——粒度 = 节点方法(一轮)。
3. **CW 的结构性放大**:整个对局循环是**单个节点**
   `CurrencyWarRunLoop.loop`(`battle_loop.py:609`,retry 400);`备战决策环`
   的节点方法内部跑完整 PrepDirector 步进链(买→部署→装备→出战,每步又是
   子 op.execute + 多次 controller 调用 + sleep,见 prep_actions.py /
   shop.py:471-488 / collect_plane_intel.py:156-206 等);战斗等待轮虽逐轮
   检查,但一轮内含「点击空白加速」等输入。
4. **子 op 收口被父链吞掉**:子 op 在轮顶看到 stop 返回 `已停止` 失败结果后,
   父链(director 环/loop 节点)把它当普通失败继续走下一步并点击
   (12:56:12 → 12:56:16 实证)。ADR-0388 曾以 CW 两层刹车环顶+executor
   入口)修补此洞,但属 CW 局部补丁:其余玩法、CW 未来新增调用点、绕环
   路径都不受保护。

## Considered Options

1. **逐调用点加 stop 检查**(CW ~20 处 controller 调用点各自判)——症状补丁:
   覆盖不全、新增点必漏、跨玩法不受益。否决。
2. **round_by_* 工具层检查**——只覆盖走工具的调用;prep_actions/shop 等裸
   controller 循环与 director 嵌套链不覆盖。否决。
3. **杀死/中断运行线程**——Python 无安全协作式中断,win32 调用中途强杀状态
   不明(按键未释放/拖拽未抬起)。否决。
4. **【选定】controller 层停机守卫 + 守卫异常穿透**:
   - `ApplicationRunContext` 增「停机中断闩」`stop_interrupted`:仅
     RUNNING/PAUSE 态被 `stop_running` 打断时置位;`start_running` 清位;
     idle 杂散 stop 不置位(STOP 也是 idle 初始态——沿用 ADR-0388 的判据
     教训);自然完成走新 `finish_running()`(不置闩)。
   - `ControllerBase.stop_guard`(谓词,由 `SrContext.init_controller` 接
     `run_context.is_stop_interrupted`);所有公开输入入口
     (click/drag_to/btn_tap/btn_press/scroll/input_str/mouse_move,
     pc_controller_base.py + sr_pc_controller.move_mouse_relative)入口首行
     `_check_stop_guard()` → 抛 `StopRunInterrupted`。
   - `Operation.execute` 捕获该异常:收口本 op 为 `已停止[guard:来源]` +
     `after_operation_done` 后**继续上抛**(`operation.py:440`)——不在中间
     op 层吞掉,父链无法「已停止后继续下一步」;顶层 `run_application` /
     backend 槽收口为 STOPPED。
   - 手动接管出口:MCP 手动输入端点(click_game/key_tap/drag/input_text)
     先 `consume_stop_interrupted()`——停机后的显式外部命令(残局清理)是
     接管者意图,放行。
5. **保留 ADR-0388 CW 两层刹车作纵深防御**(环顶早退省余下链路开销;executor
   入口挡绕环路径),不与其互斥。

## 决策与影响面

- **改 one_dragon 公共包**(跨玩法影响声明):
  - `controller/stop_guard.py`(新):异常 + 检查函数,零依赖。
  - `controller_base.py`:新增 `stop_guard` 属性与 `_check_stop_guard()`;
    默认 None = 不拦,**向后兼容**(未接线的项目/测试 mock 零感知)。
  - `pc_controller_base.py`:7 个输入入口加守卫(行为变化仅发生在
    「接线 + 运行中被停」时;正常路径零开销一行属性读)。
  - `application_run_context.py`:闩 + `finish_running()` + run_application
    收口守卫中断;`stop_running` 语义不变(仍幂等、仍直达 STOP)。
  - `operation.py`:round 异常处理新增守卫分支。
  - 其它 OneDragon 系项目(ZZZ 等)同步点:controller 接线在其项目侧
    (`init_controller` 挂谓词),不接线则守卫不生效——升级本包零破坏。
- **sr_od 侧**:`sr_context.init_controller` 接线;`backend_context.py`
  op 槽 finally 改 `finish_running()`(不再用 stop_running 做清理收口)、
  手动端点消费闩、key_tap 长按改走 `btn_press` 公开入口;
  `sr_pc_controller.move_mouse_relative` 加守卫。
- 截图/OCR 等**只读**操作不受守卫限制(不抢用户鼠标,轮顶检查自然停)。

## 验证

- 新锁 `sr-od-test/test/one_dragon/base/controller/test_stop_guard.py` 10 条:
  闩语义 5(idle 杂散 stop 不置闩/运行中被停置闩+start 清/暂停被停置闩/
  finish_running 不置闩/consume 消费)+ 守卫语义 3(全输入入口零落地/
  未置闩与未接线不误拦/真实 PcControllerBase 入口) + 穿透语义 2
  (嵌套链停机即整链中止、落地点击恰为停机前次数;run_application 收口
  「已停止[gui:hotkey]」非执行异常)。
- 既有锁适配:`test_run_slot.py` op 路径 finally 断言改 `finish_running`
  (语义变更点);ADR-0388 三锁不动(纵深防御共存)。
- ruff(新文件/改动段)+ cw 快速集 + 全量 pytest 0 failed。
