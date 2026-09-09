# ADR-0601: 动作 op=机械执行,画面/失败判断属分发层(用户裁定 2026-09-08;T-164 批A 执行断言化+报告硬化+死代码下线的决策 why 收编)

- **Status**: 已实施(主仓 f465c39dd + 测试仓 a18a2612 已入库;本 ADR 为该批决策 why 的持久收编与代码注释出处指针的回填目标)。**修订(T-174/ADR-0610,2026-09-09)**:§3 D2 增补板满失配窄豁免分支、§5「执行位现读不可信」论断按双源仲裁真值改写辖域(对幻影满板成立/对板满失配不成立)——修订依据与本批实现面见 ADR-0610。**修订(T-164 C1,2026-09-09)**:§3 补 C1 条(C1 整改落地 = 计划随指令下发,产出位/空计划闩闭合/计划失效三参数定谳见 §3-C1/§4-9),方案审+轻复审两轮放行后实施。**修订(T-199,2026-09-10)**:§4-7 失败状态具名常量枚举补 §4-9 新增的装备版 `STATUS_PLAN_STALE`/`STATUS_PLAN_EMPTY` 两常量(枚举当时漏收,判读侧按旧清单建分键映射会漏两状态);§3-C1「全树 grep 锁」表述改准确辖域(实锁只扫 `cw_op_equip_all.py` 单文件)——纯文档对账修订,零决策内容变更。**修订(T-203,2026-09-10)**:§3-C1「词表与分键锁零改」声明补时点消解括注(该声明止于 C1 批时点,其后词表补两计划失效行、分键锁随批新增,演进指针见 T-199 修订与 §4-9);§4-7 补 `STATUS_PLAN_EMPTY` 合法稳态成功态立场声明(非失败、不入零穿戴哨兵归域词表)——纯文档对账修订,零决策内容变更
- **Date**: 2026-09-08(裁定与实施同日;ADR 补立同日三审事后批;2026-09-09 T-174 修订;2026-09-09 T-164 C1 修订;2026-09-10 T-199 文档对账修订;2026-09-10 T-203 文档对账修订)
- **关联**: dd-037(部署发射×执行契约接缝——本裁定在其三分契约上扩第④分支)、ADR-0517/0518(单动作画面 op 架构——动作 op 的宿主形态)、ADR-0530(板满换阵装配源契约——C2 晚帧重放豁免的「同函数同参」判据)、ADR-0532(工具执行通道——C3 replan 删除的宿主)、ADR-0554(备战收益耗尽出战臂——RunDeploy 合法稳态 no-op 的环级出口)、ADR-0596(备战旗标状态机——分发层职权面的同代定义)、ADR-0610(板满失配窄豁免与部署出口不变量——§3 D2/§5 修订的依据件)
- **原始材料**: 合规清查与方案审原文在 `.debug/temp/currency_war/attacks/action_op_compliance/`(不入 git,易失);本文为其决策内容的持久收编,两者冲突时以本文为准。

## 1. 背景与决策 why

### 1.1 用户裁定原文(2026-09-08)

> 「动作 op 的规范是机械执行,不能在里面额外做画面判断、失败判断。」

展开(同场澄清):动作 op 收到分发层指令后机械执行(点击/拖拽/读取),不自己判断「当前画面对不对」「要不要跳过/下轮再来」;**该不该执行的判断属分发/流程层**;执行结果以状态报告返回(报告 ≠ 路由判断)。

### 1.2 为什么需要这条裁定(合规清查结论)

对 `operations/` 动作类 op(cw_op_* 族 5 个备战动作 op + cw_shop_action_ops 族 + cw_entry 族)的全量清查发现 **11 个违规实例**,分布 5 个文件,形态四类:

| 违规范畴 | 实例数 | 典型 |
|---|---|---|
| ① 画面判断 → 跳过/停批 | 5 | equip_all 前置画面闸 success 跳过、M7 批内漂移 break 停整批 |
| ② 失败判断 → 自调度(下轮再试/交外循环) | 3 | deploy 板满 cap 门报 NOOP、zero-place 熔断跳槽 |
| ③ 换路 / op 内编排其它 op | 1 | collect_spheres 掉箱分支自开箱 |
| ④ 前置条件/决策内嵌自判 | 2 | sell_off_target 无 target 跳过、卖/留内嵌决策 |

最重发现:「非干净画面 → 成功态跳过」已从已知单点扩散成三文件五处的族,其中两处用 `round_success` 把「弃执行」记成成功——闩被置位/分发被吞,而实际什么都没做。而分发层早已有同功能闸(cw_loop 0 系 overlay 分支与备战双锚、mandate 发射位同源谓词、环级无进展守卫),op 内这些闸是**重复越权**,两个判定主体会对同一事实给出不同动作(op 跳过 vs 守卫停机),报告语义被稀释。

### 1.3 参考实现就在仓内(商店域)

`cw_shop_action_ops` 族零违规,即本规范的参考实现(模块头「决策 10,用户 2026-09-06 确认」):**execute 机械执行无判断 + project 纯计算零读屏 + 守卫断言零读屏**(防 bug 非路由分支)。分发宿主 `run_buy_waves`(ADR-0517)承担入口观察/决策循环/终结语义。备战域(equip/deploy/tools/spheres)向此同构迁移,不发明新架构。

## 2. 规范本体(裁定落地后的动作 op 契约)

- **op 保留面(执行闭环,全部合规)**:拖前稳帧、坐标现读重定位、逐件效果验证(avatar CV-diff/源槽验证/卡片裁片 diff/球消失验证)、失败帧存证、逐件状态报告、机械安全边界(见 §3 动态停)。删除的只有「据判断改路」(跳过/停批/换路/下轮再来)。
- **报告语义硬化**:弃执行不得记 `round_success`。op 对「没法执行」只有两种合法出口:机械失败(`round_fail` 具名状态)或语义由分发层消费的具名成功(dd-037 的 `STATUS_NOOP` 形态,计划空 = 合法稳态)。
- **画面/失败判断的上提承接点**(逐闸落名,分发层现状已可接):前置画面闸 → `_run_composite` guard_screen 派发前置(T-163 已落地);执行中画面漂移 → op 执行断言 fail → Director fail-stop → 交外循环 heavy 重观察;事件 overlay → cw_loop 0 系分支 + 宿主入口防线(第一道)+ op 内窗口期执行断言(第二道,D1);失败记忆 → cw_loop 环级无进展守卫(同签名计数 + 停机留证)。

## 3. 区分线裁决(清查争议项逐条定谳)

- **D2 三分**(deploy 入口 cap 门/幻影满板/批内动态停不是一个东西):
  - 入口板满失配(cap 门)与幻影满板矛盾帧 → **fail 化**(具名状态 `STATUS_BOARD_FULL_MISMATCH`/`STATUS_PHANTOM_FULL_BOARD`):发射位谓词正常时这两形态不可达,命中即「发射面读与执行面读失配」的 bug 信号,禁旧 `(0, True)` 伪装 plan_empty 合法稳态吞失配。
  - **批内动态停(拖拽循环内每槽 cap 复查截断)保留**:它不是与分发层重复的闸,是批内机械安全边界。区分判据:闸读「本批已部分执行后的动态状态」且行为是截断剩余 → 执行细节;读「执行前状态」且行为是不执行 → 闸,上提。一刀切删除 = 游戏拒收弹回 → 每槽 3×2s 白烧 + 假失败帧(白拖事故回归)。
- **C1(equip 的 hold/释放判定与分配求值点在 op)**:随本批(T-164 C1)完整整改——**计划产出上提到分发段**(`prep_actions` 派发前置同位,`_build_equip_wear_plan`;发射位产出路线依赖 P4 观察接线(owned 件名池/occupied 件名明细),登记为 P4 落地后的演进方向,计划载体(`EquipWearStep`)与 op 消费契约不变,仅产出点搬家):分发段对执行帧现读 owned/occupied/deployed → kernel 判据单一源求值(release/hold 逐件/词缀序/环境变体 → `equip_allocation`)→ 静态计划(`EquipWearStep` 列表)随 op 构造下发;op 对四 kernel 判据(resolve_wear_release/classify_item_hold/apply_equip_env_variants/resolve_affix_priority_order)**零引用**(验收 = op 源码单文件 grep 锁 `test_cw_equip_plan_builder::test_equip_op_kernel_criteria_free`,辖域 = `cw_op_equip_all.py` 一个文件、非全树——「零引用」红线的锁定面即 op 文件本身,op 外判据引用不在此锁辖域,与退役墓碑锁同型),机械执行计划(逐步定位/拖拽补救链/CV-diff 验穿/失败记忆)+ 逐件报告。**空计划 = 合法稳态具名 NOOP**(分发段 `_run_equip` 短路,ok=True 闩照置 + landed=False;dd-037 形态,闩写点仍唯一在 `prep_actions.execute` 执行位,「发射位只读不写」零触碰)——hold 期闭环不变量:每期 RunEquip 恰一次 ok=True 收敛,门①真时门②必闭,dd-027 活锁三条件缺二。**计划失效**(件被合成消耗/reflow 不可定位)→ 装备版 `STATUS_PLAN_STALE` round_fail,闩不置,下帧重派重算(tools C3 同形,保住期内穿戴极大性)。**回退路径**(身份读失败 front-only)一并计划化,不设豁免(豁免会把第二套微分配语义留在执行位,与红线冲突);**dd-015 拉黑过滤**随产出位(登记面留执行位);**零穿戴哨兵**双挂点(计划面原因挂产出位、执行面原因留 op,单一源 = `record_zero_wear_defect`),词表与分键锁零改(该声明止于 C1 批时点;其后词表补两计划失效行、分键锁随批新增,已随批登记——见 Status 行 T-199 修订与 §4-7,词表现状 = `cw_equip_env._ZERO_WEAR_EXECUTION_REASONS` 全枚举)。S1 清键门行为中性申报(R2 修正后口径):RunEquip 本就不命中 `mark_s1_route_check` 三路径封闭枚举(route_tag 白名单不含装备类、RunDeploy 分支才消费 landed、bench 翻正路径装备不改席恒不翻),NOOP 化把 landed 置 False 对清键门**行为中性**,仅语义归正——0 件完成本无「落地」可言,与 RunDeploy NOOP 的 landed=False 先例同构。Considered Options:①发射位产出(P4 未接线前只能吃 op 回写的陈旧 owned 快照 = 把陈旧数据源合法化,否);②分发段产出(本裁);③维持 op 求值(= 违规照旧,否)。
- **C2(deploy 三组现读重建:卖出臂/换排纠正/P24 补)**:首批取显式豁免形态——「**与发射面同函数同参的晚帧重放**」(装配单一源 = kernel `assemble_swap_plan_inputs`,ADR-0530 装配源契约);执行位板面真值只在画面上,project 纯内存推演替代不了。治本形(卖/挪/补三段计划随 RunDeploy 下发)归后续批单独方案审。
- **C3(tools 执行中 replan)**:随首批完整整改——删除 op 内 `_replan`(「重评 admitted」是策略判据在 op 内第二次触发);计划失效(首件消费后 reflow)→ `STATUS_PLAN_STALE` round_fail 上报交回,分发层下一环重派即天然重算(发射位 G1 对 fresh owned 重评 = 判据单一源)。
- **C4(防御性重复闸总体定性)**:「上提 + 报告制」适配 D2 入口门与 D3 熔断;批内动态停按上文判据区分出去。D3 的 zero-place 熔断(同签名 placed=0 跨轮失败记忆 → 跳槽)整机制删除:失败记忆单一源收敛到分发层 cw_loop `PREP_NO_PROGRESS_ROUNDS` 无进展守卫(同签名计数 + 停机留证);op 侧只留失败帧存证与逐次如实上报。
- **C5/C6(open_shop 幂等前置读/RefreshShop 刷前现读)**:维持「倾向合规、备案」——目标态已达成时动作是 no-op 属幂等执行的机械语义;读数只进对账遥测不改变行为,「据此改变行为」要件不成立。
- **S1/S2(collect_spheres)**:op 已零调用死代码,分发层动作载体(`ClickSpheres`/`OpenBox`/`DeferSpheres`)已建成——确认下线 + 删除文件(死 op 每批合规清查都是噪音源,其 docstring 还写着违规设计「外层腾席后下轮再收」)。
- **O1/O2(sell_off_target)**:零调用已复核,登记不整改;若后续重接,按「参数化(卖槽清单随指令)」重写。

## 4. 实施形态(批A 落码面)

1. **E2/E3**(equip_all):M7 主循环与 front-only 回退路径的批内画面漂移 → `round_fail(STATUS_SCREEN_DRIFTED)`(禁旧 break+success 假完成);哨兵观测保留(纯观测零行为,stop_reason 串不变)。
2. **D1**(deploy):事件 overlay 三锚 → `round_fail(STATUS_EVENT_OVERLAY+命中画面名)`(op 内检查降级为**派发间隙窗口期第二道执行断言**,不升 guard_screen——deploy 派发不带回环守卫的现状由测试边界申报锁固化);禁旧 success-skip 吞分发。
3. **D2**(deploy):`_deploy_deterministic` 契约扩 3 元组 `(placed, plan_empty, gate_fail)`;板满失配/幻影满板具名 fail(先于 dd-037 三分判定,禁被 NOOP 分支吞);批内动态停保留(§3);bench 空 = `(0, True, None)` 合法稳态 NOOP 输入形态(三审 C1:旧 2 元组 return 是契约漏改,运行时 ValueError,行为锁堵漏)。
4. **D3**(deploy):熔断跳槽机制删除(计数器/签名/跳槽符号全清);节点 placed=0 且计划非空 → `STATUS_LANDED_NONE` round_fail 如实上报,持续无进展交分发层守卫停机留证。
5. **C3**(tools):`run_tool_queue` 删 replan 参数,返 `(consumed, attempts, plan_stale)`;节点 plan_stale → `STATUS_PLAN_STALE` round_fail(闩不置位,下环重派重算)。
6. **S1/S2 下线**(collect_spheres 文件删除):模态金 `'spheres'` 分键断喂缺口如实登记在 `recorder.record_modality_gold` docstring(补喂点候选 = `PrepActionExecutor._click_spheres` 收取前后金现读,是否接通属观测面排期裁决)。
7. **失败状态具名常量**(禁散字符串,判读侧可分键):deploy 4 个(`STATUS_EVENT_OVERLAY`/`STATUS_BOARD_FULL_MISMATCH`/`STATUS_PHANTOM_FULL_BOARD`/`STATUS_LANDED_NONE`)+ equip_all `STATUS_SCREEN_DRIFTED` + 装备版 `STATUS_PLAN_STALE`/`STATUS_PLAN_EMPTY`(随 §4-9 C1 计划消费化新增;T-199 修订补录。**`STATUS_PLAN_EMPTY` 为合法稳态成功态**——空计划防御分支的 `round_success` 出口,非失败;收编本清单仅供判读分键,且**不入零穿戴哨兵归域词表**:非停手归因、不进哨兵输入、无归域语义)+ tools `STATUS_PLAN_STALE`。
8. **T-174 修订实施面**(ADR-0610):deploy 节点 gate_fail 分支增补板满失配窄豁免(门值 `STATUS_BOARD_FULL_MISMATCH` ∧ fresh 帧前排 4 槽全空 ∧ 后排非系统单位在场 → `_fix_misplaced_rows` 场内换排修复 → 2.0s 后出口复验前排 ≥1 → 新具名成功状态 `STATUS_ROWFIX_RECOVERED` / 维持 fail;分键 `board_full_front_empty_rowfix`);幻影满板门值永不进豁免(负锁 L4b)。既有闸三元组契约与 `STATUS_BOARD_FULL_MISMATCH`/`STATUS_PHANTOM_FULL_BOARD` 常量语义不动,既有闸锁(`test_cap_gate_full_board_mismatch_fails_not_noop`)保绿。
9. **C1 整改实施面**(T-164 C1,2026-09-09):`prep_actions.py` 新增模块级 `EquipPlanBuild` + `_build_equip_wear_plan`(求值块自 op 整体搬迁,kernel 判据调用序逐行保留,W880「signals 构造点唯一」随迁改指该函数)与 `_run_equip`/`_guard_screen_mismatch`(`_run_composite` 守卫体改调共用 helper,部署/工具路径零波及;`_execute_dispatch` RunEquip 分支改调 `_run_equip`);`cw_op_equip_all.py` 计划消费化——`__init__(ctx, plan)` 必填、主循环改 for-计划步(屏断言 E2/E3 语义原样保留 → 网格现读定位计划件(miss → 一次机械现读重试 → 仍 miss = `STATUS_PLAN_STALE` round_fail)→ 拖点解析(缺失跳步,今日 stall<2 中断面随迭代重规划一并退役,计划 for 有界无死循环面)→ 拖拽补救链/CV-diff 验穿/dd-015 登记(全保留)→ 拖拽硬失败终止本 pass 与今日 break 语义一致(round_success 已穿件数,闩照置));空计划防御分支 `STATUS_PLAN_EMPTY`(生产路径不可达,直接构造面对称出口);旧 M7 求值块与 front-only 回退路径整体删除;`_prioritize_wearable`/`_empty_slots`/dd-015 纯函数留在原文件(调用点迁出,符号零迁移,`test_cw_equip_blacklist` 不红);零穿戴哨兵抽模块级 `record_zero_wear_defect` 双挂点(计划面 = `_run_equip` 空计划短路,front_only 分支不挂与今日覆盖面一致;执行面 = op 内全出口保留)。测试:新锁五件(`test_cw_equip_plan_builder.py`:产出位接线锁含 empty_reason 字面量逐字对拍+alloc 同参对拍、闩闭合锁直钉 `cw4_m7_equipped_phase`(断言入口 = 公共 `execute(RunEquip())`,轻复审 R1 修正)+ STALE 三面 + 门①同源对读)+ E2/E3 桩改(plan 参数,断言面不动)+ 守卫接线锁结构跟进(锁义 = 两处派发点都有守卫,不变)。

## 5. 消费链与收敛责任(fail 化之后谁兜底)

- **闩语义**(正向收益):`mark_equip_pass_executed`/`mark_tools_pass_executed`/`mark_s1_route_check` 只在 ok=True 置位——旧 success-skip 会置闩吞分发(装备没装但闩已置),fail 化后闩不置 → 下一环重发,正确。
- **期望态**:`apply_op_effect` 只在 ok 时登记,失败不污染期望态投影。
- **Director 失败链**:fail-stop → 同动作连败 2 → `try_recovery` 一次 → 仍连败 → 分型 bail/屏蔽,交外循环 heavy 重观察。
- **失配闸命中帧立即 return**(三审 C2 显式裁决;**T-174 修订辖域,ADR-0610**):闸命中两形态的「帧不可信」判定**分辖**——「执行位现读不可信」论断对**幻影满板**(CV 采样结构性失真)**成立**;对**板满失配不成立**:双源仲裁取低值(paddle = 游戏计数器权威,r64 口径)已使「板满」为可信真值,失配实质 = 发射位谓词违约(0j 无条件派发),不是帧不可信。故:①幻影满板命中帧在闸返回点**立即 round_fail 速回**不变——该帧上的换排纠正是对坏帧做真实状态变更拖拽(放大失配),SIFT 重观测/2s 等待/装备快照同属对坏帧的后续投入,一律不做;②板满失配命中帧的换排纠正不再一概视为「对坏帧的真实变更」——「满板 ∧ 前排 4 槽全空 ∧ 后排有人」是合法的场内换排工作形态(非幻影帧),走 T-174 窄豁免(ADR-0610 §2.2):fresh 帧现读三条件 → 场内换排修复 → 出口复验前排 ≥1 → 新具名成功状态 `STATUS_ROWFIX_RECOVERED` 或维持 fail;其余板满失配形态(前排有人等)仍立即 round_fail 速回。「如实速报交回重判」的注释自我定位由此在修订后的辖域内自洽。
- **收敛终局**(依赖声明):失配/失败形态若持续,同签名动作批 + 状态零推进 → cw_loop 环级无进展守卫(`PREP_NO_PROGRESS_ROUNDS=3` 同签名计数 + 停机留证)停机;RunDeploy 合法稳态 no-op 形态由 ADR-0554 出战臂接管。**op 侧禁为任何 fail 形态自建「连续 N 次即跳过/停出」的第二份失败记忆**——那会重演 D3 刚删掉的双份计数。
- **「失败重试风暴」结构性排除**:Director fail-stop 每环一次不环内重试;环间有 heavy 重观察;组合 op 是单节点 op,round_fail = 失败终止(不耗 node_max_retry_times)。

## 6. 出处指针表(代码注释 → 本文)

批A 在代码注释中以「T-164 批A」为出处(进度树任务号,git 树内不可解析),本 ADR 补立后全部回填为本文 § 号。对应关系(回填后注释只引 ADR-0601 §N,语义描述保留):

| 注释主题 | 文件 | 指针 |
|---|---|---|
| 失败状态具名常量块(deploy 4 个) | cw_op_deploy.py | §4-7 |
| overlay 窗口期第二道执行断言(D1) | cw_op_deploy.py | §3 D1 / §4-2 |
| dd-037 契约第④分支(失配闸) | cw_op_deploy.py | §3 / §4-3 |
| 3 元组契约扩展 docstring | cw_op_deploy.py | §4-3 |
| 板满失配执行断言(D2 三分之一) | cw_op_deploy.py | §3 D2 / §4-3 |
| 幻影满板矛盾帧执行断言(D2 三分之二) | cw_op_deploy.py | §3 D2 / §4-3 |
| 失败记忆单一源(D3 熔断删除) | cw_op_deploy.py | §3 C4 / §4-4 |
| 失败状态具名常量(equip) | cw_op_equip_all.py | §4-7 |
| E2 批内漂移执行断言 | cw_op_equip_all.py | §4-1 |
| E3 回退路径同形 | cw_op_equip_all.py | §4-1 |
| C1 计划产出位(_build_equip_wear_plan/_run_equip/空计划 NOOP/闩写点不变) | prep_actions.py | §3-C1 / §4-9 |
| 计划消费循环(机械执行/STATUS_PLAN_STALE/STATUS_PLAN_EMPTY/pass 终止语义) | cw_op_equip_all.py | §3-C1 / §4-9 |
| 哨兵双挂点单一源(record_zero_wear_defect) | cw_op_equip_all.py | §3-C1 / §4-9 |
| 拖曳参数注释(replan 删除语境) | cw_op_tools.py | §3 C3 |
| run_tool_queue docstring(C3 整改) | cw_op_tools.py | §3 C3 |
| 失败状态具名常量(tools) | cw_op_tools.py | §4-7 |
| 节点内 _replan 删除注记 | cw_op_tools.py | §3 C3 |
| 模态金 spheres 分键断喂登记 | telemetry/recorder.py | §4-6 |

测试仓锁面 docstring 同批回填(test_cw_t164_action_op_compliance / test_cw_deploy_pseudo_slot / test_cw_p4r_deploy_battle_chain / test_cw_tools_exec_channel)。测试侧残余两处单行出处注(test_cw_recipe_floor_lock_exempt / test_cw_t163_popup_dispatch 的「契约扩 3 元组」语境注)未随本批文件面回填,语义仍可由本文 §4-3 覆盖,留待该两文件下次被批触碰时顺手回填。
