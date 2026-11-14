# 设计对抗报告

## 第一轮（attacker-weekly-flow：无前提+规范遵循；attacker-weekly-scope：治本+分层/范围）

攻击方：attacker-weekly-flow（无前提+规范遵循）、attacker-weekly-scope（治本+分层/范围）。均为只读审查。

## 汇总

- 无「不改会翻车架构级」问题；流程攻击员报 1×P0；两员合计 P1×9（去重后）、P2 一批。
- 范围攻击员总判：设计可开工、引用抽查基本属实（17 处行号仅 2 处语义错位）；配队「必可查」、失败检测锚、镜像档案均核过成立。

## P0

1. **support='none' 翻译职责悬空**：周本计划补齐默认 `support='none'`（echo_of_war_config.py:51），而 ChooseSupportInTeam 只认 None 跳过（choose_support_in_team.py:45），传 'none' 会走模板匹配失败；现状编排层都在调用前翻译（echo_of_war_app.py:93、trailblaze_power_app.py:127,131）。设计的包装读计划直传核心、核心⑤直传子 op，两处都无翻译 → 首跑默认计划必翻车；weekly-core docstring「与 ChooseSupportInTeam 现约定一致」表述失实（现约定在编排层）。
   → 修正：翻译层定死在包装（读计划时 'none'→None 再传核心）；核心 ⑤ 委托前归一 `None/'none'`→跳过；docstring 表述改「编排层翻译后传 None」。

## P1（按采纳动作归组）

- 共享件缺失：失败「点空白→回挑战画面」逻辑三份同构（核心⑩/use_trailblaze_power/ChallengeEchoOfWar，光锥角色挂账后还会长）→ 抽 challenge_mission 共享小 op，三方共用（scope-1、flow 同源）。
- 外溢面无承载：光锥/角色手动失败适配、battle-loop 统一（Phase 2）只有名词无目录无排期 → 立外溢迭代占位目录 + Phase 2 写明强制触发条件（scope-2）。
- use_trailblaze_power 超时收尾 BATTLE_FAIL 分支漏适配（use_trailblaze_power.py:273-275 → _click_exit_after_result 找不存在按钮）→ 并入共享失败继续处理（scope-3、flow-P1 同点）。
- ChallengeEchoOfWar 无战斗超时防线（round_wait 无限继续 = 一条龙挂死）→ 3.3 顺带补 timeout 节点 + 场景（scope-4）。
- 记账缺口未声明：手动路径不写 run_record、不清 left_times → 周本 app 按陈旧次数多跑/漏跑；「明确不解决」补声明 + 包装在次数耗尽分支清 left_times（镜像 challenge_ehco_of_war.py:112）+ 成功链日志带实际消耗（scope-5）。
- 核心⑫超时胜利假成功（计划 3 次第 1 场超时后胜报「已完成计划次数」）→ 独立 status「超时胜利已退出」，日志带 N/计划M（scope-6）。
- 核心⑧未写 timeout_seconds → 超时边永不触发、⑫死节点、MCP 挂死（flow-P1）→ 显式写值（家族口径 use_trailblaze_power 25 分钟窗）。
- ⑫二次超时框架文案不可控（operation.py:526 STATUS_TIMEOUT='执行超时'）→ ⑫ 挂 status=STATUS_TIMEOUT 出边转终态节点 round_fail('战斗超时无结算')（flow-P1）。
- 「node_max_retry_times 与 ChallengeEchoOfWar 同档现值 24」证伪（app 未设，默认 3）→ 改显式声明 24 + 真实依据（flow-P1、scope-9）。
- use_trailblaze_power 失败重发回链矛盾（回点击挑战则滑条不重放）→ 定死回「选择次数」节点（重算剩余次数，记账自洽）；周本侧无滑条不受影响（flow-P1、scope-11）。
- 包装收尾「跳过节点4/统一走4」二选一未定死且对外 status 契约不同 → 定死统一走节点 4，status 恒「已返回大世界」（flow-P1）。

## P2（择要，全部采纳）

- 核心⑩「成功已达标」为不可达分支 → 删除；⑫超时胜利未达计划如实报。
- ⑧/⑫ timeout_seconds 值未写（同 P1 超时条一并落实）；⑫三分支无 mock → 补直呼式单测场景。
- ③「挑战后」阵亡分支未单列场景 → mock 补。
- 包装解析零命中场景缺、op_name 未定义 → 补（op_name 照 app 先例「历战余响 <关卡名> 次数 N」）。
- 包装节点 3 未列明 status 一律 round_fail 透传 → 补。
- team_num=0 授权显性化（docstring+运行日志报「计划配队=0，沿用当前编队」）。
- design.md:29 花萼配队证据错位（get_history_by_uid 是计划新建后备非执行期）→ 改如实表述。
- 推荐链②「实现待补」口径过期（券刷四态已实现，缺连刷参数与券耗口径回填——券 1/次实测 vs 常量 3 待修）；总纲症状 1 表述同步收窄。
- 推荐链口径失真另涉：trace-integration 与总纲表述同步修正。
- TP 入口选型依据落纸（无条件可用 vs 资源窗口仅缺料态出现+依赖面板态）。
- 失败形态实测面只花萼+周本 → 通用纪律补兜底（点空白后挑战锚回归失败时回退试旧锚再判失败）。
- landing 3.4 跨详设拼凑（status 全名单补进 trace-integration）；3.2 判据点名 challenge_mission 测试目录。
- 两处无依据标注（BackToNormalWorldPlus 幂等、FarmLightConeMaterialOp 实机验证）→ 补指针。
- README 与 design §0 状态失同步 → 已同步（对抗审中/进行中）。

## 核过成立（交叉参照）

配队「必可查」（init_plan_list 二次全量补齐）；失败检测锚与空白点击区在档；镜像画面档 20 区域齐全；共享子 op 通用区域无新增风险；体力计划与周本计划配队源不相交（show_in_power_plan=false）；行号引用 17 处仅 2 处错位；正本更新清单锚存在。

## 第二轮（attacker-weekly-r2：修订验证 + 复攻）

修订验证：第一轮 1×P0 + 9×P1 中 10 条真实落地且落对；1 条落错层（见 R2-1）；P2 全部落实；硬规则 4 全量同步复查基本通过（两处计数/契约小失同步）。

### P1

1. **op 级 `node_max_retry_times=24` 无效**——框架每轮以节点装饰器值覆盖 op 级（operation.py:528），所有节点实际预算仍为默认 3（修订引入）。→ 修订：预算落节点级（②发起链=10、③⑦⑬防线=10、⑤照 choose_support_in_team.py:36=10、①=5），删 op 级声明与「现值 24」锚。
2. **⑫ 三场景「直呼节点方法」手法与断言不匹配**——until 语义下直呼单次返回 round_wait、边路由直呼不触发；「墙钟不可 mock」前提不成立（timeout_seconds 是节点普通属性可 monkeypatch，先例 test_use_trailblaze_power_timeout.py:61）。→ 修订：验证改三分法（边结构断言 / 行为直呼+mock 点击 / 可选毫秒级 execute 全链）。
3. **共享失败继续件旧锚兜底挂错位置**——入口识别判「大世界-战斗失败」精准（id_mark 含点击空白提示），旧形态失败画面无该提示 → 入口即 fail，兜底永远轮不到。→ 修订：入口两态分流（新形态态 A 点空白 / 旧形态态 B 直接点退出关卡 / 双不中 fail）。
4. **landing 3.2（旧编号）判据与既有测试冲突**——test_use_trailblaze_power_timeout.py:112-129 锁旧失败行为，行为变更必红。→ 修订：该条随「UseTrailblazePower 迁移+失败适配」外溢迭代走，占位目录补判据同步声明。

### P2

5. 包装「终点恒为大世界」未限定失败路径 → 限定成功终态恒「已返回大世界」、fail 原样透传不收尾。
6. 「七类」计数错（status 表 8 行）→ 「八类」。
7. ⑫ 观察窗 10 分钟偏离家族 25 分钟无依据、贪饕表述对周本为挪用 → 统一 25 分钟、贪饕表述如实化为兜底口径挪用。
8. 共享件点空白→until 无连等封顶（纯定位区点击恒成功，round_wait 无界）→ 补连等 5 轮转旧锚、再 5 轮 fail + 节点 timeout_seconds=3 分钟兜底。
9. 核心②「until 弹窗或编队态」until_find_all 语义不可直接表达；③「无弹窗→round_success」丢家族防线（弹窗迟到漏检）→ ③⑦⑬ 改家族同款结构（check_dialog 命中走取消分支；无弹窗 round_retry('无对话框') + success=False 出边承接，先例 use_trailblaze_power.py:160-170/:338-345）。
10. 「实机 25/10 分钟窗口由 3.5 盯防」引用悬空（3.5 判据不触超时窗）→ 改落地 3.3 describe 核对声明值 + 长战斗局观察。
11. 完成链日志「×30 开拓力」硬编码档位 → 统一 `mission.power`。
12. ⑫ 节点卡粒度过粗（中间边与重入门控未写）→ 拆 ⑫-a（超时态判定/补记+点退出关卡）/⑫-b（退出后达标判定，node_clicked 门控）。
13. 包装节点 1 从行迹面板态回家未实测（BackToNormalWorldPlus docstring 是声明非证据；角色页关闭区几何可能重叠但未验证）→ 落地 3.3 验收补「从行迹面板态起跑」观察项。
14. ⑫ 三场景无 mock 覆盖 → 已补直呼场景（本轮进一步改为三分法，见 P1-2）。
15. 包装解析零命中场景缺 → 已补（本轮核过）。

### 核过成立（第二轮）

第一轮修订 10 条落实正确（support 双层归一/外溢三目录/超时判负分支/app 超时防线/记账声明+left_times 清理路径核真 sr_context.py:335/假成功独立 status/回链定死/收尾统一/各 P2 落实）；节点图无死路；防线单轮识别无重入累积副作用；失败重入无重复计数；四个委托子 op 通用区域可跑；引用抽查全部核真。

## 第三轮（attacker-weekly-r3：收敛校验）

结论：未达收敛但接近——2×P1 + 8×P2（其中 3 条为第二轮修订自身的半落实）。全部已修：

### P1

1. **核心⑩/⑫-b until 循环无界**（「点击恒成功但锚恒不出现」round_wait 无界，operation.py:1004-1006 明文；同题已在共享件上补过、节点级漏改）→ ⑩/⑫-b 显式 `timeout_seconds = 3 分钟`（交互级口径，不搬 25 分钟战斗窗）；落地 3.3 describe 核对项扩为全节点 timeout/retry 声明值。
2. **⑦/⑬ 三弹窗出口去向与落点未定**（照③同款会把「停挑战画面」带到编队态/胜利结算语境；节点卡只写「无弹窗→⑨」）→ ⑦/⑬ 各自显式写三弹窗出口（开拓力/次数耗尽→success 落点=编队态/胜利结算；阵亡→⑧'）；status 表落点列改「触发点画面（挑战画面/编队态/胜利结算，视防线触发点而定）」；包装层无感（success 统一收尾契约不变）。

### P2

3. landing 3.2 判据「七类」残留 → 八类。
4. design.md §2 第 4/5 条内容重复（编辑残留）→ 删。
5. 「ChallengeEchoOfWar 切换到核心」无占位锚 → battle-loop-unification README 范围句补「含 app 切换到核心」+ design §1 指向声明。
6. use-trailblaze-power-rehome 占位缺「既有测试同步改」声明 → README 补（点名 test_use_trailblaze_power_timeout.py:112-129）+ 承接出处补第二轮 attack.md。
7. 共享件 fail 出口集合与声明不一致（转态未验锚会落框架默认文案）→ 转态前先验锚、不在场直接自定义 fail。
8. weekly-core ② 「子 op 内部处理点击与编队态等待」失实（ClickChallenge 只点按钮）→ 改「子 op 只处理点击，编队态等待由 ③ 防线循环承担」。
9. trace-integration TP 依据引用失真（requirement.md 无「只在缺料态出现」原句）→ 改两文档合成表述。
10. mock 场景 12 断言与三分法「c 可选」张力 → 断言列写明「边结构(a)+终局节点直呼(b)组合锁」。

### 核过成立（第三轮）

status 表 8 行与节点终态一一对应无死路；⑫-a/⑫-b 拆分与 STATUS_TIMEOUT 边经 operation.py:87/:523-528 框架行为验证成立；包装八类分支+未知透传防御闭合；共享件两态锚在档；镜像档 20 区域齐全；team_num=0 与 'none' 语义核真；计划必可查核真；花萼零新建核真；**范围红线干净（全文档无旧口径残留，app 侧内容已正确移入外溢占位）**；规范硬规则 3 正文干净。

## 第四轮（attacker-weekly-r4：收敛判定）

判定：未收敛——残留 1×P1 + 2×P2（第三轮 10 条修复 9 条落实、1 条落实有误），全部已修：

### P1

1. **③/⑦「无弹窗」处置二义**（第二轮 P2-9 半落实：头部改家族结构、列表行残留 round_success 旧表述——两行互斥 = 弹窗迟到漏检风险）→ 删列表旧表述，统一家族结构（无弹窗一律 round_retry('无对话框')，预算耗尽经 status 限定的 success=False 出边进下一步），③→④、⑦→⑨ 写死。
2. （范围攻击员报告的落点修正并入本条执行：status 表「本周次数耗尽/开拓力不足」落点列改「触发点画面」）。

### P2

2. TP 入口选型第二引语失真（screen-flow.md 无「只列缺料行」原句）→ 改实际支撑表述（「快速刷取」按钮进入的缺料路径产物 + 「独立常态入口」未见档）。
3. 委托型节点重试预算声明与框架机制脱节（round_by_op_result 默认 retry_on_fail=False，②①等预算为死参数）→ 补委托型节点口径声明（声明值供 describe 核对；失败透传不消耗预算）。

### 定点复查（checker-r4-1）

四项全过：③/⑦ 二义消除且预算去向写死（③→④、⑦→⑨）；出边集合与 status 表一致无幽灵边；家族先例机制兼容（round_retry 耗尽→FAIL 保留 status→success=False 边承接，operation.py:475-480/:550-604 核真）；委托型口径与 round_by_op_result 默认 retry_on_fail=False 一致。
落地对齐点两条（已采纳）：防线出边补 `status='无对话框'` 限定（裸 success=False 会成 ignore_status 兜底边，误接意外 fail）；委托型分组移出 ①（判定节点非委托）。

### 核过成立（第四轮）

第三轮 10 条修复 9 条落实核真（含 ⑩/⑫-b 3 分钟交互级封顶、⑦/⑬ 出口显式化+落点列、八类计数、占位锚、rehome 判据声明、共享件验锚、②表述、TP 依据、mock 组合锁）；「从行迹面板态起跑」观察项在 landing 3.3；连败阈值/25 分钟家族窗/mission.power 统一/left_times 镜像/ctx 访问路径/game-coach 实跑记录全部核真在位。

