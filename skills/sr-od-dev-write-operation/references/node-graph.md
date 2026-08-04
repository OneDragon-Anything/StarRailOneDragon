# 节点图机制(reference)

> `sr-od-dev-write-operation` 的 situational reference。SKILL.md 给心智模型,本文件给完整机制。

## 声明节点:`@operation_node`

装饰一个方法 = 声明一个节点。框架启动 op 时扫描类里所有 `@operation_node` 方法 + `@node_from` 边,构建节点图。

```python
@operation_node(name='等待目标画面', is_start_node=True, node_max_retry_times=5)
def wait_screen(self) -> OperationRoundResult:
    ...
```

关键参数:
- `name`:节点名(`@node_from(from_name=...)` / 路由日志用它匹配)。**重名会报错**。
- `is_start_node=True`:标记起始节点。不标则框架按"入度为 0"自动判起始;**多个起始节点报错**。
- `node_max_retry_times`:本节点 retry 上限(覆盖 op 级 `node_max_retry_times`)。
- `screenshot_before_round=True`:每轮进节点前自动 `self.screenshot()`。**纯计算节点(不读屏)设 `False`** 省截图。
- `mute=True`:不输出节点日志(高频轮询节点用它减日志噪声)。
- `save_status=True`:把本节点的 round 结果存进 `self.node_status[节点名]`,供后续节点查。

> `need_check_game_win=True`(op `__init__` 默认)会自动在真正起始节点**前面**插「检测游戏窗口」+「打开并进入游戏」节点 —— 所以你声明的起始节点不一定是运行时第一个跑的。

## 声明边:`@node_from`

叠在节点方法上(可多个),声明"从哪个节点、在什么条件下、来到本节点":

```python
@node_from(from_name='等待目标画面')                 # success 且 status 任意 → 走本节点
@node_from(from_name='识别画面', status=STATUS_DONE)  # success 且 status 精确匹配才走
@node_from(from_name='处理', success=False)          # 来源失败才走(fail 边)
@node_from(from_name='收尾', success=False, ignore_status=True)  # 兜底边
@operation_node(name='退出')
def exit_op(self) -> OperationRoundResult: ...
```

参数:
- `from_name`:来源节点名。
- `status`:来源节点的 round `status` 字符串,**精确匹配**才走这条边(多出口节点靠它分流)。不传 = status 任意。
- `success`:布尔,来源节点是 success 还是 fail 才走。默认 `True`。
- `ignore_status=True`:**兜底边** —— status 都没匹配上时走它(见路由规则)。

## 路由规则(框架怎么选下一节点)

某节点返回 round 结果后,框架从它的出边里选:

1. 先按 **success/fail** 过滤:success 边只在结果成功时考虑;fail 边(`success=False`)只在失败时考虑。
2. 在留下的边里按 **status** 匹配:`边.status == 结果.status` → 走它(status 都为 None 也算匹配);`ignore_status=True` 的边作**兜底**,只在没 status 匹配上时走。
3. 都没匹配 → 无下一节点 → op 按 round 结果(success→op 成功 / fail→op 失败)结束。

## ⚠️ 自环陷阱(必踩一次)

**别给节点加回到自身的 `@node_from`**。`round_wait` / `round_retry` 本就会重跑当前节点,不需要边;而自环边会让**连 `round_success` 都沿边回到自身** → 无限循环(日志:同一节点反复"返回状态…",OCR 每帧不变)。

判据:要"等画面变了再推进",用 `round_wait`(重跑当前节点)或拆成"等待节点 → 动作节点"两节点 + 正向边,**别自环**。

## `previous_node`:读上一节点结果

节点里 `self.previous_node` 返回上一节点的代理(`NodeStateProxy`):
- `.is_success` / `.is_fail`:上一节点成功/失败。
- `.status`:上一节点的 round status 字符串。
- `.data`:上一节点返回的 data。
- `.name`:上一节点名。

用途:本节点行为依赖上一步结果时分支(如上一步 status 是某具体值才做某动作)。`save_status=True` 的节点也存进 `self.node_status[节点名]` 供更晚的节点查。

## `handle_init`:op 执行前初始化

重写 `handle_init(self)`,在 op 每次执行前(`_init_before_execute`)调一次。用途:重置 op 内状态(让它可重复跑)。可返回:
- `None`:正常跑本 op。
- `round_success(...)`:跳过本 op(前置条件已满足,无需跑)。
- `round_fail(...)`:立即失败。

## `round_*` 的 `wait` 参数(控制节奏)

`round_success/wait/retry/fail` 都接 `wait`(秒,返回后 sleep)和 `wait_round_time`(睡到本轮总耗时达此值)。等动画 / 等画面切换用 `wait`;节流(固定每轮 N 秒)用 `wait_round_time`。
