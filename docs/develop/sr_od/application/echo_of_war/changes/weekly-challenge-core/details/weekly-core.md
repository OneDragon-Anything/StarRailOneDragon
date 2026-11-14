# 周本挑战循环核心 ChallengeEchoOfWarCore（详设）

## 问题与约束
- 边界：起点 = 「挑战副本-历战余响」挑战态（无弹窗覆盖），入口导航由调用方负责（资源窗口行二进入或传送均可）；核心不导航、不读计划配置、不做开拓力/次数记账（调用方按 `mission.power × plan_times` 预估授权；手动路径不写 run_record，见总纲「明确不解决」）。
- 总纲划给的接口契约：纯参数 `team_num`/`plan_times`/`support`；status 中文诊断句；战斗失败新形态处理经共享失败继续件 `ResumeFromBattleFail`（定义见 fail-form-adaptation.md）。
- 放置：`src/sr_od/application/echo_of_war/challenge_echo_of_war_core.py`（用户裁定：核心放周本 app 包）。与 `ChallengeEchoOfWar` 本迭代并存（循环逻辑两份）为已知临时重复，app 切换后续迭代消除。

## 方案

### 构造签名（MCP 契约，反射源）
```python
class ChallengeEchoOfWarCore(SrOperation):
    def __init__(self, ctx: SrContext, team_num: int, plan_times: int,
                 support: str | None = None):
```
- 第一参数逐字 `ctx`；无 `*args/**kwargs`；参数全 JSON 直传型。
- 校验：`plan_times >= 1` 否则 `ValueError`（带得到值）；`team_num` 语义 = 队伍编号从 1 起，0 = 跳过选择沿用当前编队（依据 choose_team.py:30），负数 `ValueError`。
- 类 docstring 两段式（效果一句话 + 起终点 + 副作用行；`:param` 段）：
  - 效果：「在历战余响挑战画面发起挑战并完成指定次数的自动战斗循环」。起点：挑战副本-历战余响·挑战态；终点：按结果落挑战画面或大世界（见 status 表）。副作用：消耗周本挑战次数与开拓力（30/次，指南档位数据），真实不可逆。
  - `:param team_num:` 队伍编号从 1 起；0 = 不切队沿用当前编队。
  - `:param plan_times:` 计划成功次数，>=1。
  - `:param support:` 支援角色 ID；None = 不用支援。**约定：'none' 的翻译在带 mission 语义的包装层完成（包装读计划时已翻译为 None）**，核心委托前仍兜底归一（`None`/`'none'` 一律跳过支援）——ChooseSupportInTeam 现约定只认 None（choose_support_in_team.py:45），编排层翻译先例见 echo_of_war_app.py:93。
- `op_name = gt('历战余响挑战循环')`。
- 重试预算落**节点级**（各节点卡点名），op 级不设——框架每轮以节点装饰器值覆盖 op 级参数（operation.py:528），op 级声明无效；节点级取值照家族先例（choose_support_in_team.py:36=10、back_to_normal_world_plus.py:56=20、upgrade_trace.py:142=5）。
- **委托型节点口径**（②④⑤⑥⑧'）：`node_max_retry_times` 为装饰器声明值（供 describe 核对与边结构）；委托失败按 `round_by_op_result` 默认（`retry_on_fail=False`）`round_fail` 透传出节点、不消耗本节点预算——失败处置归调用方/包装层，节点预算不承担子 op 重试。①入口核对为判定节点（check_and_update_current_screen + round_fail，非委托），fail 同样透传。防线确认节点（③⑦⑬）与等待/结果节点的 round_retry/round_wait 预算在节点内真实生效。

### 节点卡（分支链）

**① 入口核对**（is_start_node，node_max_retry_times=5）
- 识别：`check_and_update_current_screen(screen, screen_name_list=['挑战副本-历战余响'])`（id_mark = 标题-历战余响 + 挑战按钮，2026-11-14 实机精准命中）
- 命中 → ②；不命中 → `round_fail('不在历战余响挑战画面')`

**② 点击挑战**（委托 `ClickChallenge` 子 op——子 op 只处理点击，编队态等待由 ③ 弹窗防线循环承担；node_max_retry_times=10——发起关键步）
- 点「挑战按钮」→ ③

**③ 挑战后确认**（三弹窗防线，结构照家族先例 use_trailblaze_power.py:160-170 与边 :338-345——check_dialog 命中走对应取消分支；无弹窗 `round_retry('无对话框')` 且 `@node_from(success=False, status='无对话框')` 出边承接「弹窗迟到」；**预算耗尽（=弹窗从未出现，编队态已就绪）经该出边 → ④**，node_max_retry_times=10；识别区域用「挑战副本-历战余响」镜像副本）
- 命中 开拓力弹框-标题 → 点 开拓力弹框-取消 → `round_success('开拓力不足')`（出口：停挑战画面）
- 命中 提示弹框-标题 + 提示弹框-次数用完 → 点 提示弹框-取消 → `round_success('本周次数耗尽')`（出口：停挑战画面；负责人裁定 0/3 不打）
- 命中 阵亡弹框-标题 → 点 阵亡弹框-取消 → ⑧'阵亡传送恢复

**④ 选择配队**（委托 `ChooseTeam(ctx, team_num)`，0 = 跳过）→ **⑤ 选择支援**（先归一 `support in (None,'none')` → 不用支援路径；否则委托 `ChooseSupportInTeam(ctx, support)`，node_max_retry_times=10 照 choose_support_in_team.py:36 先例）→ **⑥ 点击开始挑战**（委托 `ClickStartChallenge`）→ **⑦ 开始挑战后确认**（三弹窗防线同③结构重放，node_max_retry_times=10；无弹窗 `round_retry('无对话框')`，预算耗尽（=编队态就绪无弹窗）经 `@node_from(success=False, status='无对话框')` 出边 → ⑨等待战斗结果）
- 命中 开拓力弹框-标题 → 点 开拓力弹框-取消 → `round_success('开拓力不足')`（出口：停**编队态**——弹窗盖在编队态上，取消即露编队态）
- 命中 提示弹框-标题 + 提示弹框-次数用完 → 点 提示弹框-取消 → `round_success('本周次数耗尽')`（出口：停**编队态**）
- 命中 阵亡弹框-标题 → 点 阵亡弹框-取消 → ⑧'阵亡传送恢复

**⑨ 等待战斗结果**（`timeout_seconds = 25 分钟`，家族口径复用 use_trailblaze_power 的等待窗常量——贪饕侵蚀可把战斗拖得远超常速（use_trailblaze_power.py:250-255 根因实证；该文件迁移开拓力 app 归外溢迭代 trailblaze_power/changes/use-trailblaze-power-rehome（占位），行号按现状引用），窗口内不清场；`battle_screen_state.get_tp_battle_screen_state(battle_success=True, battle_fail=True)`，失败锚 = battle.yml「战斗失败」文本区，2026-11-14 花萼+周本失败画面实测命中）
- `BATTLE_SUCCESS` → 成功计数 +1 → ⑩战斗结果处理
- `BATTLE_FAIL` → 失败计数 +1 → ⑪失败画面继续
- 仍在打 → `round_wait('等待战斗结束', wait=1)`
- 超时沿边（`@node_from(success=False, status=STATUS_TIMEOUT)`）→ ⑫战斗超时收尾

**⑩ 战斗结果处理（胜利路径）**（`timeout_seconds = 3 分钟` 交互级封顶——「点击恒成功但锚恒不出现」的 until 无界等待防线，退出关卡是即时交互，不搬 25 分钟战斗窗口径）
- 成功次数 >= plan_times → 点 战斗画面·退出关卡按钮 → until `['挑战副本-历战余响','标题-历战余响']` 回归（2026-11-14 实测：退出关卡→挑战画面）→ `round_success('已完成计划次数')`（出口：停挑战画面）
- 未够 → 点 战斗画面·再来一次按钮 → ⑬再来一次后确认

**⑪ 失败画面继续（版本更新新形态适配）**
- 委托共享失败继续件 `ResumeFromBattleFail`（定义见 fail-form-adaptation.md：点「大世界-战斗失败·点击区-空白继续」→ until 挑战画面锚回归；挑战态锚回归失败时回退尝试旧结算按钮锚再判失败，防其余副本类型形态未变时误伤）
- 回到挑战画面后分支：失败计数 >= 5 → `round_success('连败放弃')`（出口：停挑战画面）；否则 → ②点击挑战（重新发起，③弹窗防线自动重放）
- 注：到达 ⑪ 时成功计数必 < plan_times（达标在 ⑨/⑫ 已退出），无「成功已达标」分支。

**⑬ 再来一次后确认**（三弹窗防线同③结构重放——弹窗盖在战斗结算画面上；node_max_retry_times=10）
- 命中 开拓力弹框-标题 → 点 开拓力弹框-取消 → `round_success('开拓力不足')`（出口：停**战斗结算画面**）
- 命中 提示弹框-标题 + 提示弹框-次数用完 → 点 提示弹框-取消 → `round_success('本周次数耗尽')`（出口：停**战斗结算画面**）
- 命中 阵亡弹框-标题 → 点 阵亡弹框-取消 → ⑧'阵亡传送恢复
- 无弹窗 → ⑨等待战斗结果

**⑧' 阵亡传送恢复**：`TransportToRecover` → `round_success('有阵亡角色已复活')`（出口：停大世界复活点；调用方自行重入——负责人裁定「核心退出、入口无关」）

**⑫-a 战斗超时收尾·观察判定**（`timeout_seconds = 25 分钟`，与 ⑨ 主窗统一取家族常量口径——主窗语义 = 战斗死锁兜底（周本实测约 2 分 23 秒/场，探索记录 screen-flow.md；贪饕侵蚀拖长战斗是拟造花萼机制，对周本为兜底口径挪用，如实声明），超时后不清场继续观察至结算——贪饕教训防战场残留，机制照 use_trailblaze_power.py:246-278）
- `BATTLE_SUCCESS` → 补记成功计数 → ⑫-b
- `BATTLE_FAIL` → ⑪
- 仍无结算 → `round_wait(5)`
- ⑫-a 自身超时 → 框架 `round_fail(STATUS_TIMEOUT)` → 经 `@node_from(from_name='战斗超时收尾', success=False, status=STATUS_TIMEOUT)` 出边转**终态节点「战斗卡死终局」**：`round_fail('战斗超时无结算')`（使自定义文案可落，status 表成立）

**⑫-b 超时退出与达标判定**（`timeout_seconds = 3 分钟` 交互级封顶，同 ⑩ 口径）
- 点 战斗画面·退出关卡按钮（`node_clicked` 门控：点击成功前不得进行达标判定）→ until `['挑战副本-历战余响','标题-历战余响']` 回归
- 成功次数 >= plan_times → `round_success('已完成计划次数')`（出口：停挑战画面）；未达标 → `round_success('超时胜利已退出')`（日志带「成功 N/计划 M」，防假成功——包装透传后由调用方向用户如实汇报；出口：停挑战画面）

### status 出口表（全部中文，家族惯例依据：ChallengeEchoOfWar '有阵亡角色'、battle_screen_state 值 '挑战成功' 等）

| status | 类型 | 落点 | 触发 |
|---|---|---|---|
| `'已完成计划次数'` | success | 挑战画面 | 成功次数达标，退出关卡后 |
| `'超时胜利已退出'` | success | 挑战画面 | 主等待窗超时后战斗胜利且未达计划（日志带 成功N/计划M） |
| `'连败放弃'` | success | 挑战画面 | 失败计数 >= 5 |
| `'本周次数耗尽'` | success | 触发点画面（挑战画面/编队态/胜利结算，视防线触发点而定） | 次数耗尽弹窗取消 |
| `'开拓力不足'` | success | 触发点画面（同上） | 开拓力补充弹窗取消 |
| `'有阵亡角色已复活'` | success | 大世界复活点 | 阵亡取消 + 已复活 |
| `'不在历战余响挑战画面'` | fail | 原地 | 入口不符 |
| `'战斗超时无结算'` | fail | 原地 | ⑫ 观察窗二次超时（经 STATUS_TIMEOUT 出边转终态节点） |

连败阈值 5 与 use_trailblaze_power/ChallengeEchoOfWar 现值一致（use_trailblaze_power.py:297）。

### mock 场景表（sr-od-test，fixture_controller 剧本驱动）

| 场景 | 剧本要点 | 断言 |
|---|---|---|
| 全胜循环 plan_times=2 | 挑战→编队→开始→胜→再来一次→战斗→胜→退出关卡 | status 已完成计划次数；成功计数=2；再来一次点击 1 次 |
| 一败后重试成功 | 败→失败画面→共享失败继续件→挑战画面→重新发起→胜→退出关卡 | status 已完成计划次数；失败计数=1；空白点击 1 次 |
| 本周次数耗尽 | 挑战→次数耗尽弹窗→取消 | status 本周次数耗尽；无编队点击 |
| 开拓力不足 | 挑战→开拓力弹窗→取消 | status 开拓力不足 |
| 挑战后阵亡 | 挑战弹阵亡→取消→恢复 | status 有阵亡角色已复活 |
| 编队后阵亡 | 开始挑战后弹阵亡→取消→恢复 | status 有阵亡角色已复活 |
| 再来一次后阵亡 | 再来一次弹阵亡→取消→恢复 | 同上 |
| 连败 5 次 | 败×5（每场经共享失败继续件） | status 连败放弃 |
| 入口不符 | 首帧给大世界 | fail 不在历战余响挑战画面 |
| 超时后胜利未达计划（⑫-b） | 直呼 ⑫-b、桩画面给挑战画面回归、预置成功计数 < plan_times | status 超时胜利已退出；退出关卡按钮已被委托点击；日志带 成功N/计划M |
| 超时后判负（⑫-a→⑪） | 直呼 ⑫-a、桩画面给失败画面 | 转委托共享失败继续件（点空白→挑战画面） |
| 超时观察窗二次超时（⑫-a 终局） | 直呼 ⑫-a、桩画面恒为战斗 | 断言 = 边结构（a：⑫-a 有且仅一条 STATUS_TIMEOUT 出边指向终局节点）+ 终局节点行为直呼（b：round_fail 战斗超时无结算）组合锁 |
| 支援 'none' 归一 | 构造 support='none' | ChooseSupportInTeam 未被委托（跳过支援） |

⑫ 三场景验证手法照家族三分法（先例 test_use_trailblaze_power_timeout.py:61 直接读 `op._node_map['等待战斗结果'].timeout_seconds`）：
a) **边结构断言**——⑨/⑫-a 各有且仅一条 `(success=False, status=STATUS_TIMEOUT)` 出边且指向正确节点（锁路由，纯静态可不依赖墙钟）；
b) **行为分支直呼**——直接调节点方法 + 桩 last_screenshot + mock `round_by_find_and_click_area`（锁节点逻辑，家族 test_cleanup_on_success 同款）；
c) **可选 execute() 全链**——monkeypatch 节点对象 `timeout_seconds` 至毫秒级（节点属性为普通字段可 monkeypatch）锁端到端，优先级最低。
实机 25 分钟窗口由落地批 3.3 describe 核对节点声明值 + 长战斗局观察收尾流转盯防。

## 关键取舍
- **阵亡复活后核心退出**（备选：核心内固定 TP 重入）——复活停大世界，重入路径随入口不同（TP vs 资源窗口），写死 TP 会封死资源窗口入口；用户裁定「核心退出、入口无关」。
- **中文 status**（备选：英文大写）——挑战域家族先例全中文；status 是日志主体，中文即诊断句；用户裁定。
- **无回调参数**（备选：像 ChallengeEchoOfWar 带 `on_battle_success`）——回调破坏 MCP 反射契约；核心内部计数（`battle_success_times`/`battle_fail_times` 属性）供代码调用方读取；周本 app 后续切换时再解决其记账回调需求。
- **超时收尾不清场继续观察**——主等待窗 25 分钟 = 战斗死锁兜底口径（家族常量；周本实测约 2 分 23 秒/场，探索记录；贪饕侵蚀拖长战斗是拟造花萼机制，对周本为兜底口径挪用、如实声明），超时即放弃会留战场残留污染后续 app 入口导航（use_trailblaze_power.py:250-255 根因实证 run 48）；观察窗统一同取 25 分钟（二次窗内仍无结算才是真死锁）。
- **支援 'none' 双层归一**（备选：只靠包装翻译）——包装翻译是主责（契约），核心兜底归一是防线；ChooseSupportInTeam 只认 None 的现约定在编排层翻译先例（echo_of_war_app.py:93）支撑。
