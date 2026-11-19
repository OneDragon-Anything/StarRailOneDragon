# loop→exit 交接接线 落地

## 1. 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级；工作区有并行批在飞文件绝不卷入），commit message 含阶段号与任务 id；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 2. 任务

### 2.1 T-1 app 交接节点（两段式 + 三形态判定）

**范围**：按 design.md §2.2/§2.5：①`currency_war_app.py`「对局循环到结束」节点后新增「退出收尾」节点（node_from 默认 success 边；fail 边不接——loop 硬失败走 app 失败收尾现状语义）；②交接节点两段式：先弹窗守卫段（复用进局链守卫注册表 `ENTRY_POPUP_GUARDS`，cw_entry_start.py——落地时核对注册表现值，局末自动弹的积分奖励/星琼详情/星徽详情等大厅态白名单弹窗须在覆盖面内，缺则迁入），后 exit 调用段；③三形态判定，载体 = `self._previous_round_result.status`（禁另起炉灶）：大厅完成 → exit 大厅确认形态；异常交接 → exit 清场退局形态；其余（max_rounds 停备战 / 假局守卫开局失败-中断）→ 跳过 exit 直接结束；④两交接形态完成后置 `ctx.cw_match=None`（兜底清理点，design.md §2.3 口径）；⑤出口文本常量落 loop 常量面（`STATUS_LOBBY_DONE` / `STATUS_HANDOFF_PREFIX`，cw_loop.py 模块级，loop 出口与 app 判定共用单一源，禁裸串散写）；⑥打桩测试六用例（新文件 `test_currency_war_app_handoff.py`，打桩先例 test_nameless_honor_app.py：大厅→exit 被调+置 None / 异常→exit 被调+置 None / max_rounds→零调用 / 假局守卫→零调用 / fail→零调用+失败收尾 / 积分奖励压大厅→守卫清→exit 被调）。
**设计依据**：design.md §2.2、§2.3（清理口径）、§2.5
**文件面**：`src/sr_od/application/currency_war/currency_war_app.py`、`operations/cw_loop.py`（常量面）、sr-od-test 新测试文件
**依赖**：无
**优先级建议**：1
**完成判据**：六用例全绿 + 既有 app 相关节零回归 + ruff + 常规检查
**验收凭据形式**：新测试 + 复跑记录

### 2.2 T-2 loop 出口语义（耗尽出口分流 + 链判定改读前缀）

**范围**：按 design.md §2.3/§2.4 五项：①耗尽点出口按模式分流——`CwLoop` 加构造参数 `cleanup_delegate: bool = False`（默认 False：`round_success(f'{STATUS_HANDOFF_PREFIX}{键}')`；True：维持 `round_fail` 现状语义）；②投资环境链早退判定改读 `STATUS_HANDOFF_PREFIX` 前缀（原 `result == FAIL` 判定退役），「链尾不空跑」语义保留；③注释与日志同步——`_dispatch_screen_op` 包装 docstring 的 FAIL 出口契约段重写（FAIL→交接前缀 success）、链首调用点注释、耗尽点 ERROR 日志行文案（原文写「round_fail 交上层处置」失实）；④route⑤ 构造点补 `cleanup_delegate=True` 一参（exit 侧唯一改动）；⑤测试同步——既有耗尽透传测试（test_cw_loop.py 耗尽透传用例）改断言：FAIL → success 带前缀，「链尾不空跑」断言保留不删；新增委托模式耗尽维持 fail 用例；大厅/max_rounds 出口文本不变断言。
**设计依据**：design.md §2.3、§2.4（委托清理模式）、attack.md §2.1/§2.2
**文件面**：`operations/cw_loop.py`、`operations/cw_entry_exit.py`（route⑤ 构造点一参）、sr-od-test test_cw_loop.py
**依赖**：T-1（常量面）
**优先级建议**：2
**完成判据**：出口语义测试全绿 + CW 域全量一次通过 + ruff + 常规检查
**验收凭据形式**：出口语义测试 + 全量复跑记录

### 2.3 T-3 收尾核签

**范围**：①CW 域全量复跑一次通过；②grep 复核（超限出口旧 round_fail 路径零残留；出口常量单一源零裸串散写；`cleanup_delegate` 构造点恰一处）；③实机项裁定：harness 覆盖不了的实机形态（异常交接的真实触发场景无法离线构造——申报「实机项：异常退出交接全链实机单跑复核」记货币战争待办，不阻批）；④核签记录落 reports/。
**设计依据**：design.md §2.3、§2.9
**文件面**：核签记录（迭代内 reports/）
**依赖**：T-1、T-2
**优先级建议**：3
**完成判据**：全量一次通过；grep 复核通过；实机项落档；常规检查（无代码改动，提交项仅核签文件）
**验收凭据形式**：核签记录文件

### 2.4 T-4 正本更新 + 挂账板（末位阶段）

**范围**：按正本更新清单逐条（清单 = 本节 §2.5）+ 挂账板动作（§2.6）。flow/ 审阅批在飞——落笔前对表已改段。
**设计依据**：design.md §2.4、§2.7、attack.md §3
**文件面**：清单所列正本文档 + 挂账板
**依赖**：T-1、T-2、T-3
**优先级建议**：4
**完成判据**：清单清零；挂账动作全部落板；正本与实现一致
**验收凭据形式**：文档对照 review

## 3. 正本更新清单（T-4 执行）

1. `skills/sr-od-dev-currency-war/references/flow/loop.md`：结束出口表补交接申报（两交接点 + max_rounds/假局守卫非退出触发边界 + 委托清理模式耗尽 fail 语义 + 幻影 run 噪音与假局守卫警告误导性申报 + 「可升级 data 载体」备忘一句）；
2. `skills/sr-od-dev-currency-war/references/flow/entry-exit.md`：route⑤ 语义重申（清理原语非所有权 + 「清理 = 处理到可交还态，期间按正常流程推进（含战斗），非瞬时放弃」+ 委托耗尽 fail 由节点重试承接 + 残局面申报）+ 消费面更新（现役三处：app 启动预检恢复链 / 回大世界链 back_to_normal_world_plus.py / 本批新增 app 交接节点）+ 敌人信息浮层特判改口「保留至浮层画面 op 落地，清偿义务挂挂账板 §二.9，非终态」；
3. `skills/sr-od-dev-currency-war/references/flow/guards.md`：外环 fail-streak 网出口语义段**重写**（语义从「停机显式化」变「停机转交接」，非改词——含委托模式维持 fail 的分流申报）；
4. app 编排正本（如有 app 节点链文档）：交接节点两段式补录。

## 4. 挂账板动作（T-4 执行，`.debug/progress/CW跨迭代挂账.md`）

1. **§二.7④ 销账拆两半**：「局终收尾归属」半——收尾簿记是对局流程的终点账，归 loop 本职（用户模型推演 2026-11-19）；「分发回调簿记」（统一置战斗窗回调）半——loop 运行期管理的组成部分（所有战斗窗交回路径统一设置），同归 loop 本职。两半各自一句理由，不捆绑；
2. **立新挂账两条**：a)「委托清理 loop 不参与运行记录生命周期（构造开关跳过启动门控）」——幻影 run/日志归属碎片化治理，涉及运行门控深水面（跳过后日志归属行为未实证）；b)「sim 走 app 全链需先补 exit 识别 sim 改道口」——exit 三处识别点接 sim_or_live_identity，后端答口已存在未接线；
3. **过时导航行订正**：§二.7 内对本批的「落地进行中」类导航行如仍指向旧态则一并订正。
