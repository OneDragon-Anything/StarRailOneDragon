# T-4 遭遇 修法设计(encounter)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:触顶定稿,残留 3 低按用户裁定**残留随批清偿**(对抗轨迹:r1 未收敛 2 条→修订→r2 未收敛 3 条→修订→r3 未收敛 2 条低→修订→r4 触 4 轮上限;清偿 = N-r4-1 残留修法 2 分型注限员改写(已迁移屏中经 `emit_overlay_confirm` 收尾者 = 遭遇/策划/投资两屏,补给 = `round_by_find_and_click_area` 确认、装备 = 点卡即选,不经本模块)+ N-r4-2 归口声明补「T-5 侧已随其修订履行让渡,跨稿待办已闭」对账句并删两处「现文仍写」快照表述 + N-r4-3 §2.2 §9 补删既有「§4.4(pick 族行)」错节引用(改挂 §4.5)、删除指令落点改 §1/§7 交叉引用、§6 清零面扩「陈旧括注与失效符号锚(含 `/ PickOption`)」;修法主体零改动,均词级修)
- 发现源:`.debug/progress/2026-09-22-cw-screen-review/reports/T-4-r1.md`(F-1..F-5;总判定高1 中3 低1)。涉事代码与代码内文档以仓库现状为真值;本文定位一律符号锚 / 文档节号(行号不作定位依据,约定 = flow/README.md 卷首)。
- 落地申报(施工时点盘面相对本稿的先批位移,按「仓库现状为真值」处置):①`cw_overlay_pick_action.py` 已拆一 op 一文件——`CwActionPickEncounterOp` 现居 `cw_pick_encounter_action.py`、「自上报统一」段现居 `cw_overlay_pick_env.py`;残留修法 1(类 docstring)与残留修法 3(段史述收敛)经核现值已被先批清偿(确认钮机制切换批重写类 docstring 删「重入裁决/预算耗尽 bail」两句;注释卫生批清段内两处史述),免修;②确认钮查找全族统一 `round_by_find_and_click_area` + 选择装备屏整体删除——残留修法 2 分型注按落地时点现值落笔(`emit_overlay_confirm` 现役唯一消费方 = 未达上限 `cw_screen_deploy_not_full`,已迁移屏成员 = 遭遇/补给/策划/投资两屏、确认均不经本模块);③F-4 的 game_state/README.md 域表行已随 T-5 批按其 §2.1 落地、F-2 的 logic-updates/README.md 统改已随 T-1 批落地并含本稿输入(计数现值口径 + PickEncounter 行发射即写语义),两处本稿免施;④两项先行现状照办:遭遇屏「无 match 局外早退支」维持已删不回填(commit 1ecec478a),「③空候选/局外」表述按「空候选」现值(commit 073fb7565)。

## 1. 问题与动机

### F-1 画面 op 决策出口:盲选回退 + pick idx 静默钳位(高)

- **现状症状**:`operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter.act` 两条违规路径——①`decide_encounter()` 返回 `None`/词表外类型时,现有 isinstance 分支全不命中,执行穿透到选卡派发,以默认 `idx, reason = 0, 'default(no-options/match)'` 盲选左卡派发;②返回 `CwActionPickEncounterParam` 但 `idx` 越界时,被 `if 0 <= act.idx < len(options): idx = act.idx` 静默钳回 0 续跑。两条路径都把策略器 bug 转嫁为「左卡被确认消耗」——选卡确认不可逆消耗本节点(screens/encounter.md §4 交互陷阱)。
- **根因归层(根源两问)**:根在**流程层**。「决策失败安全」是观察-决策分离前 handler 时代的兜底形态;画面 op 化时观察侧失败安全已重立为「空候选 = 零点击终结交回」(encounter.md §4),决策侧兜底未随迁移退役,残留为流程侧决策闸门与值域改写。本修法删兜底、换守卫(流程侧唯一合法判断面 = 「防 bug 守卫断言(非控制流)」,op-layer.md §1.1),修根非症状。act 内注释「策略 pick 缺席/越界时本实例即唯一载体」自述有意设计——**本设计显式废弃**,理由:①正本无任何背书,op-layer.md §1.1 出口③(「决策无有效输出也走此出口——零盲发」)、§1.3(「非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)」)与 flow/README.md §1 决策控制分层铁律(「动作值域过滤必须在策略侧实现……流程侧禁止任何形式的决策闸门与政策判断」)反向禁止;②效果 = 确定性策略器 bug 被静默降级为不可逆的左卡消耗。
- **解决到哪**:两条路径改为响亮暴露(①具名 fail 零盲发;②守卫断言 AssertionError),删除默认 idx 与钳位,派发直发策略产实例;encounter.md as-built 申报该 fail 出口。
- **明确不解决**:空候选/局外零点击终结交回路径(合规在册:op-layer.md §1.1「遭遇空候选 = 零点击终结交回重读」、报告 §3.4——勿误伤);刷新对照闸(op-layer.md §1.4 在册双闸设计,报告 §3.3 一致项);策略器返回契约本体(`strategies/impl/cw_strategy.py::decide_encounter` 返回注解 `CwActionPickEncounterParam | CwActionRefreshNodeOptionsParam` 在册,守卫 = 注解的运行期执行,不改契约);「确认未生效窗」暂态假值三防线(fields.md §3.4.1 发射即写 + 重派覆盖自愈 + 兑现后清,已在册);词缀读数未接线(encounter.md §3 在册欠账);其他 pick 屏画面 op 决策出口的守卫形态(各屏审查辖内)。

### F-2 逻辑态专篇与索引未随现役形态更新(中)

- **现状症状**:`game_state/logic-updates/pick-encounter.md` 整篇申报已退役形态:§2「容器 GameState 零写——事件线选择非逻辑态通道」「选择落地观察写端:chosen_encounter = 画面 op 观察写入边」「遭遇刷新链 = 同访问重决策,发射 RefreshNodeOptions 前须以重读产物覆盖写槽」;§7「零写族上报函数 `zero_writes.py::report_action_pick_encounter_param`」。现役 = `kernel/cw_action_report/pick_encounter.py` 具名模块**发射即写**(fields.md §3.4.1)、画面 op 零容器写(`cw_screen_encounter.py` 容器唯一触点 = report 调用)、刷新 = 终结交回(op-layer.md §1.4)、零重入裁决(encounter.md §2)。`game_state/logic-updates/README.md` PickEncounter 索引行同(「零写族 `zero_writes`」);另「注册表 26 行 ↔ 专篇 1:1」「26 注册行 / 20 op 类」「事件线 pick 族(5 行)」「7 个 handler 自管 pick 子类」的计数与分面已被 pick-op-unify 批与注册表现状抛离(现值:注册表 36 行 / 28 op 类、事件线 pick 13 行,单一源 = `operations/cw_op/cw_action_registry.py::_REGISTRY` 计数,action_ops.md §4 覆盖声明同值;词表 39 类、非注册分发 3 刷新动作,`kernel/cw_vocab.py::CW_ACTION_TYPES`,action_ops.md §4.6 同口径)。
- **根因归层**:**约定层(申报面随批同步缺口)**——遭遇扩围/刷新终结化批的正本更新清单未辖 logic-updates 两篇(报告 F-2,申报面遗漏非在册欠账)。修根 = 申报面改写至代码现值 + 计数类陈述立「以代码现值为准」口径(单一源 = 注册表 / 字段级正本),防计数固化再漂移;不立新机制(同步义务在册 = docs/develop/harness/iteration-design.md 固定末阶段正本更新)。
- **解决到哪**:pick-encounter.md 整篇改写(本稿辖);README 面收缩为 PickEncounter 行目标语义 + 现值口径输入,文件级实施并入 T-1 稿 §2.4 统改批(T-1 已认领统改并显式声明 T-4 条目并入,见 §2.2)。
- **明确不解决**:`game_state/logic-updates/README.md` 文件级统改(归 T-1,本稿只供输入);其余 pick 专篇正文改写(归各屏审查;PickSupply 与 T-5 同面);目录级「专篇↔注册行」完备性审计(缺失专篇补写归索引维护)。

### F-3 同族上报形态申报残段:CwActionPickEncounterOp docstring 与 _overlay_confirm.py 模块头(中)

- **现状症状(以现盘代码为准,双证核录 = 上报函数模块头 + 函数体/调用方 run 体)**:本发现原申报面——模块头「自上报统一」段旧口径(「发射相零写」「三线例外 = 分步实现」)、pick_equip/pick_planner 分步两相、action_ops.md §4.5 欠账标注——已随迭代 2026-09-21-pick-planner-equip-immediate-report **全域清偿**,逐项核验:①模块头现文本申报「原『发射/落地两相』例外(invest/equip/supply/planner……)已随投资两屏、供给、装备、策划各迁移批全域清偿:现役全族 = 机械链发出后立即一口写完整结果,容器写语义单点 = 各上报函数,零证据闩零重入裁决补写面」;②`kernel/cw_action_report/pick_equip.py` 与 `pick_planner.py` 模块头、函数 docstring、函数体三方一致即时单相(初版攻击时点的「planner 头单相、体两相」漂移已随体迁移落地消解);③`CwActionPickEquipOp`/`CwActionPickPlannerOp` 类 docstring 与 run 体同口径即时上报;④action_ops.md §4.5 欠账标注段已摘除,现文「上报形态 = 全族即时上报……发射/落地两相与证据闩形态已全域清偿,禁新增分步写法」。本稿初版按旧盘面立的三档改写规格(档 2 =「pick_planner / pick_equip 分步两相」)随之整体作废——把已清偿面固化进目标文本 = 制造同族新漂移,恰是本发现要治的病。**现役残留三面**:①`CwActionPickEncounterOp` 类 docstring 仍申报「落地由画面 op handle 顶部**重入裁决**承载」「防线由**重入裁决 + 预算耗尽 bail** 承接」——与其自身 run 体(末尾已发射即写 `report_action_pick_encounter_param`)直接矛盾、与同族类 docstring(planner/equip/supply/invest 即时口径)不一致,是同族随批同步缺口的遭遇腿残段;②`operations/cw_screen/_overlay_confirm.py` 模块头通用段「overlay 关没关由调用方节点下一轮重入的入口观察裁决……仍在 = 基于新观察重做确认动作」对遭遇调用方(派发即终结,round_retry 旁路产物经 `env.round_result` 回传且宿主不消费)不适用;③模块头「自上报统一」段内两处变更史句/过程件指针在册——段首括注「(pick-op-unify 批,撤销 2026-09-18 动作 op 重组批 §1.1『零上报例外登记』)」撤销史、段中「原『发射/落地两相』例外……已随投资两屏、供给、装备、策划各迁移批全域清偿(迭代 2026-09-21……)」变更史句,属 AGENTS.md §8「变更史不进注释」违规面(该段语义面经 T-37 归口本稿,史述收敛面随之承接,见 §2.3 残留修法 3)。
- **根因归层**:**约定层(申报面随批同步缺口)**,与 F-2/F-4/F-5 同根族;跨件半问已过——同步机制在册,缺口 = 个别批清单面遗漏,不升架构级设计件。本面另获一个当场实证:初版设计稿成稿与该批落地交叠,按旧盘面立的规格即刻过期——反证核录纪律必须是「模块头 + 函数体/调用方 run 体双证」,单证模块头在头体漂移的中间盘面上会自败。
- **解决到哪**:残留三面改写(`CwActionPickEncounterOp` 类 docstring、`_overlay_confirm.py` 模块头分型注、模块头段史述收敛——第三面经 T-37 归口自 T-5 §2.4 承接,见 §2.3);模块头段语义面以代码现值即目标形态,余下仅注释纪律面。
- **明确不解决**:planner/equip 已清偿面的再申报(核验结论记录于上,无修法);模块头「域 env」「体迁纪律」两段(仍准确);`emit_overlay_confirm` 函数自身 docstring(round_retry 机械交回语义仍准确,变的只是调用方形态);action_ops.md §4.5(已随批与代码一致,本稿不再引其为「欠账在册」依据——初版如此引用已失真);其余未迁移屏(巨星/伙伴/祈愿/星徽/卜者/专家六屏)的类 docstring 与调用方形态(各自审查辖)。

### F-4 已退役刷新计数在正本文档残留(中)

- **现状症状**:`game_state/README.md` §3.3 域清单「节点屏刷新计数域(node_screen_refresh)」行仍以 `encounter_refresh_used`/`supply_refresh_used` 为域成员、漏列现役 `encounter_refresh_left`/`supply_refresh_left`(fields.md §3.4.1/§3.4.2 在册),主写渠道申报「遭遇/策略经 on_outcome 发射钩子写、补给为 live 刷新发射单点」——on_outcome 落地登记注册表已整体退役(op-layer.md §4「任何一侧的重新出现即架构回潮」),现役全域 = 剩余语义观察写端(op-layer.md §2.2「刷新计数出辖」)。`flow/session.md` §2.4 迁出落点表「`_supply_refresh_used` / `_encounter_refresh_used`」行申报「画面 op 实例/节点级执行载体」、§5.5 同符号条目「按 §2.4 落点迁,**防重入语义逐字段保持**」——两符号在 src/ 与 sr-od-test/ grep 零命中(报告 §3.9),遭遇现无跨轮载体、三出口均终结(encounter.md §5),「防重入语义保持」无保持对象。
- **根因归层**:**约定层(正本残留,landing 兜底 grep 条款应清未清)**,同根族。**同族联动面与归属**:README 域表行 supply 侧残留与 T-5(补给)审查同面——T-37 裁决全行落点 = T-5 §2.1(本稿行文本作废、遭遇侧语义输入已吸收,见 §2.4);flow/session.md 两处为本稿独占发现面(T-5 修法覆盖面不含该文件),本稿自清。
- **解决到哪**:README §3.3 域表行落点 = T-5 §2.1(T-37 裁决,本稿交付遭遇侧语义输入);flow/session.md 两处本稿自清(遭遇 + 补给半边一并,见 §2.4)。
- **明确不解决**:域键 `node_screen_refresh` 更名(gs_schema 键改名 = 代码/schema 变更,超出残留清理辖);session.md §2.4 as-built 退役注「刷新计数 → GameState `node_screen_refresh` 域容器计数」一句的措辞精度(未列 F-4,不在本稿面);supply 侧语义本体与 README 域表行文本(T-5 §2.1 统辖)。

### F-5 obs 解析器 docstring 残留旧「退默认 idx0」描述(低)

- **现状症状**:`obs/cw_node_obs.py::read_encounter_options` docstring 末句「读不到 title(OCR 漏/非遭遇屏)→ 返 [](handler 退默认 idx0)」——现役调用方行为 = 空候选 → act 零点击 round_success 终结交回重读(encounter.md §2/§4;盲选 idx0 已随迭代 2026-09-21-event-refresh-unify-supply-pick 退役,报告 F-5)。
- **根因归层**:**约定层(注释申报面漂移)**,同根族。
- **解决到哪**:末句改为现役调用方行为。
- **明确不解决**:`affixes` 恒空接线(encounter.md §3 在册欠账)。

### 在册核对结论

审查报告 §3 九项一致面(派发即终结/刷新终结臂/刷新闸/chosen 发射即写/观察上报/动作 op 契约/决策分层其余面/encounter.md 九节/代码面退役残留)核对通过,不立修法。

## 2. 方案

### 2.1 F-1 修法(核心)

**代码面**(`operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter.act`):

1. 删 `idx, reason = 0, 'default(no-options/match)'` 默认初始化、`act = None` 预初始化与钳位句 `if 0 <= act.idx < len(options): idx = act.idx`。
2. **守卫①(决策无有效输出 = 具名 fail 零盲发)**——置于刷新臂分支之后(该臂对 `CwActionRefreshNodeOptionsParam` 已 return)、选卡派发之前,单一 choke 点:

   ```python
   if not isinstance(act, CwActionPickEncounterParam):
       return self.round_fail(
           f'decide_encounter 决策无有效输出(词表外/None): {act!r}')
   ```

   消息含策略器返回原值(repr)= 留证,不另加独立日志行(round_fail 消息经框架节点状态日志落盘,与观察门 `round_fail('非遭遇节点屏')` 同形态)。依据:op-layer.md §1.1 出口③「决策无有效输出也走此出口——零盲发」(此出口 = 异常 fail);先例 = 备战决策循环「非 CwAction 返回 → 具名 fail 留证」(flow/README.md §2.2 decide_prep_screen 行)。round_fail = op fail 交回外循环,受外环连续 fail 重派网兜底(flow/README.md §4:同一定分发 op 连续 fail 5 显式停)——确定性 bug 必响亮且可观测。
3. **守卫②(pick idx 越界 = 守卫断言恒炸)**——紧随守卫①:

   ```python
   if not (0 <= act.idx < len(options)):
       raise AssertionError(
           f'[cw-encounter] pick idx 越界(策略器 bug,禁钳位): '
           f'idx={act.idx} len(options)={len(options)} act={act!r}')
   ```

   依据:op-layer.md §1.3「执行侧只余守卫断言——防 bug 路栏而非控制流分支,非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)」;同款先例 = `operations/cw_op/cw_action_registry.py::action_op_class_for_type`(「词表外类型 AssertionError 响亮暴露」)。落点语义 = 框架节点异常收口(`one_dragon/base/operation/operation.py` 节点异常 → `round_retry('异常')` + 留证截图)→ `node_max_retry_times=10` 预算耗尽 op fail(该预算「现役值仅框架异常路径消费」在册,encounter.md §5)——确定性 bug 每轮必炸,预算内有界响亮终止。
4. 守卫次序 = 先词表后值域;**两守卫均在任何点击之前**——动作 op 执行即发出点击链,越界 idx 放行会点右卡并确认(不可逆),必须在派发前拦。置单点不前置:刷新闸分支只对 Refresh 类型触发,词表外值直达守卫①;首调与闸拒重调两次 decide 调用共享同一 choke 点,不在闸分支重复布防。
5. 派发改**直发策略产实例**:`action_op_for(act, self.ctx, env).execute()`(act 已被守卫①收窄;删原「重建 `CwActionPickEncounterParam(idx=idx)`」)。机械语义不变:动作 op 只消费 `param.idx`(`CwActionPickEncounterOp.run`),注册表按 isinstance 解析;`env = OverlayPickExecEnv(op=self)` 不变(encounter.md §4「env 只携宿主 op」)。依据:flow/README.md §1 铁律——直发后流程侧零值域改写,idx/reason 单一源 = 策略产值。
6. 日志行改 `pick=idx{act.idx} {act.reason}`(reason 取自直发实例,`CwActionPickEncounterParam.reason` 字段在册)。
7. 注释废弃与替换:删 act 内「派发实例 = 生效选中下标的规范实例(决策半钳位后的 idx;策略 pick 缺席/越界时本实例即唯一载体……)」注(废弃理由见 §1 F-1),原位替换为守卫语义注:词表外/None = 具名 fail 零盲发;idx 越界 = 守卫断言;空候选零点击为另一条合规路径。
8. 模块 docstring 形态段与 act docstring 各补一句守卫出口:「决策返回词表外/None = 具名 round_fail 零盲发;pick idx 越界 = 守卫断言 AssertionError;两守卫均在派发前、零点击」——口径与 encounter.md §2 同步。
9. **零容器写保持**:fail 路径不新增 kernel `_emit_defect` 调用(该面 = 观察对账缺陷台账,kernel 侧专用,`kernel/cw_game_state.py::_emit_defect`);留证 = 日志 + round_fail/断言消息。画面 op 对容器唯一触点维持 report 调用(报告 §3.5 一致项不回退)。

**文档面**(`docs/develop/sr_od/application/currency_war/screens/encounter.md` as-built 更新点,申报该 fail 出口):

- **§2 画面形态声明**:「三出口均终结访问」句后补——决策返回词表外/None = 具名 round_fail 零盲发(op-layer §1.1 出口③,消息含策略器原值);pick idx 越界 = 守卫断言 AssertionError(op-layer §1.3,禁钳位);两守卫均派发前零点击,非循环出口、非防御上限;选卡派发 = 策略产实例直发(无重建无钳位,流程侧零值域改写)。
- **§4 动作面表**:`CwActionPickEncounterOp` 行「发出方式」列改「注册表工厂 `action_op_for` 直发策略产 `CwActionPickEncounterParam` 实例(env 只携宿主 op;idx 即策略产值,流程侧零改写;越界 = 守卫断言、词表外 = 具名 fail,均在派发前)」;「上报」列补一句「画面 op 守卫先中词表/值域,report 层离屏/越界留证不写保留为字段级防线」;表末补一行:`| (决策无有效输出/pick idx 越界,非动作) | — | — | 守卫 fail:词表外/None = round_fail(含原值)、idx 越界 = AssertionError;零点击零派发,交回外循环 |`。
- **§5 终结与交回表**补一行:`| 决策无有效输出/pick idx 越界 | 守卫 fail(op FAIL) | round_fail / 框架异常路径(留证截图 + 预算耗尽)交回外循环;连续 fail 由外环重派网兜底(flow/README §4) |`——与「入口锚 miss」行同落点类,补行保表完备;「三出口均终结访问」收束句不动(fail 出口非终结动作,同类 = 入口锚 miss 行)。
- **§8 守卫与防线**补两条:①决策词表守卫:decide_encounter 返回 None/词表外 = 具名 round_fail 零盲发——原「默认 idx0 盲选回退」退役申报;②值域守卫:pick idx 越界 = 守卫断言 AssertionError——原「静默钳 0」退役申报。原「空候选防线」条不动。
- **§9 遥测与锁面**:测试锁清单补两臂(见下)。

**测试锁**(实现随功能写,锁设计约定 = sr-od-test/README.md):`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens.py` 遭遇臂补两条——①策略返回 `None`/词表外类型 → round_fail 且零点击零派发;②策略返回越界 idx → AssertionError 且零点击。现役遭遇臂清单(门/观察接线/派发即终结/空候选零点击/刷新终结/闸拒绝/闸不一致/兑现回调)无一锁回退或钳位面(单一源 = 该文件遭遇段测试清单),本改造不与在册锁冲突。

**关键取舍**:

1. **路径①round_fail vs 路径②AssertionError 的分工**:出口③明文把「决策无有效输出」归异常 fail 出口(op-layer §1.1),该出口既有实现形态 = round_fail(观察门先例),具名消息携带策略器原值,诊断面优于类型名断言;越界 = 非法参数进动作通道,§1.3 守卫断言语义 + 注册表同款先例。两路径最终落点同为 op fail 交回外循环(round_fail 直落 / 框架异常路径预算耗尽),差异只在留证形态,不引入第三种出口语义;框架异常路径的 10 次重试 = 现役注册表 AssertionError 同款传播,非本设计新引入。
2. **守卫①不依赖注册表分派兜底**:`action_op_class_for_type` 对词表外本会 AssertionError,但那是分派机制路栏,消息无策略器语义上下文;出口③要求该情形在决策出口具名 fail(零盲发显式 + 消息含原值)。守卫①先中,分派 AssertionError 保留为深层兜底,两层不冲突。
3. **直发实例 vs 重建参数**:重建正是流程侧值域改写的载体;直发后 idx/reason 单一源 = 策略产值,机械链消费面不变(动作 op 只读 `param.idx`,注册表按类型解析,词表内无该类型父类行,行序解析无歧义),无兼容代价。
4. **刷新对照闸不动**:与 kernel 刷新闸同源同值的对照闸 = op-layer §1.4 在册双闸设计(报告 §3.3 一致项),不属流程侧决策闸门禁令辖(在册例外);误删即破坏「闸拒绝 → 重调一次 → 终结」的活锁安全论证。

### 2.2 F-2 修法

**`game_state/logic-updates/pick-encounter.md` 整篇改写**(改写后逐节申报现役形态,依据就地标注,正文自足不引迭代工件):

- **§1 动作是什么**:词表字段不变,词表形态描述按现役口径改写——「(`PickOption` 子类:字段 `idx`…」→「(摊平后叶子类,原 `PickOption` 基类契约逐类重声明:字段 `idx` = 画面候选卡位下标 0 起(左→右)、`reason` = 归因记录字段)」(`PickOption` 基类已消亡,单一源 = `kernel/cw_vocab.py` 选择族公共契约注「原 PickOption 基类,摊平后 12 个叶子逐类重声明 idx/reason」+ `cw_action_registry.py` 模块头「词表摊平后 is-a 链消亡」);删「体迁自 `CwScreenEncounter._confirm_default`,替身缝 = 原方法薄委托保留」(该方法已不存在——现码 `cw_screen_encounter.py` 无 `_confirm_default` 符号,体迁已完成),改「由画面 op `CwScreenEncounter.act` 经注册表工厂分派,无替身缝」。
- **§2 逻辑态域集**:整节反转申报面——删「容器 GameState 零写——事件线选择非逻辑态通道」「选择落地观察写端 = 画面 op 观察写入边」「刷新链 = 同访问重决策、发射前覆盖写槽」三条;改为:①**chosen_encounter = 动作侧发射即写**,写端 = `kernel/cw_action_report/pick_encounter.py::report_action_pick_encounter_param`,值组装 = 容器 `encounter` payload 槽 `options[param.idx]`,payload 离屏/越界 = `_emit_defect` 留证不写 fail-closed(`LogicOutcome(applied=False, reason='chosen_unresolved')`),兑现后清 = `kernel/cw_encounter_selection.py::claim_encounter_reward` 达标兑现写 `encounter_reward_claimed` 并清 chosen(单次消费)——依据 fields.md §3.4.1、op-layer.md §2.2 例外三腿②;②画面 op 零容器写(容器唯一触点 = `report_screen_encounter_obs` 调用);③刷新不经本动作:刷新 = 终结动作交回外循环,重进 = 入口重建,新选项由入口观察现读(op-layer.md §1.4),原同访问重决策形态退役。
- **§3 确定面转移规则**:机械链三步保留(点卡选中 / 固定等待 0.8s / 确认机械交回,裁决词「遭遇节点」),补第 4 步「发射即写:确认点击后立即 `report_action_pick_encounter_param`」;idx 语义补「idx = 策略产候选下标,画面 op 直发策略产实例、流程侧零值域改写(词表/值域守卫在派发前,见本迭代 §2.1)」。
- **§5 拒绝语义**:删「重入裁决 + 预算耗尽 bail 防线」句(退役);改为——派发即终结零验证:确认未生效 = 代码 bug,overlay 残留由外循环按当前画面重识别重派(op-layer.md §1.1);发射即写 = 意图记录,暂态假值窗由重派覆盖自愈 + 兑现后清单次消费双防线(fields.md §3.4.1);report 层拒绝面 = payload 离屏/越界留证不写(`pick_encounter.py` docstring);screen_info 坐标缺失兜底常量例外保留(在册,encounter.md §4)。
- **§6 kernel 符号锚**:增 `kernel/cw_action_report/pick_encounter.py::report_action_pick_encounter_param`、`kernel/cw_encounter_selection.py::claim_encounter_reward`;§6 全节陈旧括注与失效符号锚清零(N-r4-3 扩面)——「替身缝」挂于 `CwScreenEncounter`(替身缝/写点) 括注(`_confirm_default` 已不存在;「写点」半边随 §2 现役改写同过期)、「`/ PickOption`」死锚(类已消亡,单一源 = `kernel/cw_vocab.py` 选择族契约注);落地并删 `emit_overlay_confirm` 锚(该 op 确认已改动作 op 体内 `round_by_find_and_click_area` 查找,不再消费该 helper——落地时点现值)。
- **§7 语义验证**:删「零写族上报函数 `zero_writes.py::report_action_pick_encounter_param`」句;改为——写语义单一源 = 具名上报函数(发射即写契约,上报函数族独占容器写,logic-updates/README.md 总则 1);验证锁 = `test_cw_game_state_consume.py`(chosen 记录面:真选/离屏/越界,encounter.md §9 在册)。
- **§9 依据**:增 pick_encounter.py 模块头、op-layer.md §1.4/§2.2 例外三腿②、action_ops.md §4.5 PickEncounter 行;删既有「§4.4(pick 族行)」错节引用改挂 §4.5(§4.4 现为观察族,N-r4-3 清偿);「删 `_confirm_default`/zero_writes 旧指针」的落点实为 §1/§7 既有条款各自由本稿 §1/§7 规格辖及(§9 全文不含该两指针),此处按交叉引用闭合、§9 无删除动作(N-r4-3 空靶修正)。

**`game_state/logic-updates/README.md`(文件级实施归 T-1,本稿只交付目标语义与口径输入)**:T-1 稿(prep.md)§2.4 条 5 现文已认领该文件统改(含事件线索引段/pick 族表),并显式声明「**T-2/T-4/T-5 三稿对该 README 的条目均并入本稿实施**——…T-4 稿事件线索引段与 pick 行分型(按其修订版)…已归口 T-4 修订版的模块头分型段(经 T-37 汇总登记)按 T-4 修订版落行,本稿不另立口径」。本稿相应收缩,向 T-1 统改批交付三项输入:

1. **PickEncounter 行目标语义**:「零写族 `zero_writes`(选择落地 = chosen_encounter 观察写端)」→「`report_action_pick_encounter_param`(具名模块 `kernel/cw_action_report/pick_encounter.py`,发射即写 chosen_encounter;兑现后清单次消费)」。
2. **自洽约束**:该行落地后须与本稿改写的 pick-encounter.md 同口径(同一上报函数、发射即写、兑现后清单次消费;两文互为索引,行文详略以 pick-encounter.md 为详)。
3. **计数与分面现值口径(本稿发现面,供统改采纳,不逐字代写)**:全部计数陈述(标题「注册表 26 行 ↔ 专篇 1:1」、「26 注册行 / 20 op 类」、「事件线 pick 族(5 行)」、「篇数对账」句)以代码现值为准——注册行数与行集单一源 = `operations/cw_op/cw_action_registry.py::_REGISTRY` 现值计数(现值 36 行 / 28 op 类,事件线 pick 段 13 行,其中 PickInvestStrategy/PickInvestEnv 两行同指 `CwActionPickInvestOp`;action_ops.md §4 覆盖声明同值);非注册分发分面单一源 = `kernel/cw_vocab.py::CW_ACTION_TYPES` 键集 − 注册表键集(现值 = 3 刷新动作,action_ops.md §4.6 同口径);「7 个 handler 自管 pick 子类」bullet 删除(该 7 类已随 pick-op-unify 批收编为注册行,action_ops.md §4.6 括注在册);SwapDeploy 移出「词表在册」节(现值 `CW_ACTION_TYPES` 不含 `CwActionSwapDeployParam`,单一源 = `kernel/cw_vocab.py` 词表元组;若需保留提及,改作非词表类注,归宿以 prep-executor-actions.md §3 现状为准)。落码时注册表若已演进,以当时代码现值为准,不照抄本文数字。缺档 8 个 pick 行的「专篇」列落法**按 T-1 §2.4 的缺档显式申报形态落地**(T-1 方案:缺档行显式申报,语义现役记载 = `flow/action_ops.md` §4.4/§4.5 行 + 上报函数 docstring,补篇外溢不批)。

**关键取舍**:README 文件级施工让渡 T-1 而非本稿直改——两稿对同一文件各留一套施工指令 = 双改冲突(T-1 已认领统改并声明 T-4 条目并入,本稿成稿时序不能豁免现盘冲突);本稿收缩为行级目标语义 + 口径输入后,T-1 统改批单点施工,缺档行落法沿用 T-1 已有方案,本稿不再另立第二套。计数立「以代码现值为准」口径而非固化新数字——计数类陈述反复漂移的根因是把快照值写死进正文,口径化后漂移面消失。

### 2.3 F-3 修法

**初版规格作废申报**:初版「自上报统一」段三档改写规格(档 1 即时上报 / 档 2 分步两相 = pick_planner、pick_equip / 档 3 零写族)整体作废——档 2 成员与现盘代码三方矛盾(equip/planner 均已即时单相,见 §1 F-3 核验①–④),且该段目标文本已由迭代 2026-09-21-pick-planner-equip-immediate-report 落地(模块头现文本即目标形态)。本稿不再保留该段改写指令,防双源。

**核录规则(保留,治初版自败)**:上报形态档成员的任何核录 = **各上报函数模块头 + 函数体/调用方 run 体双证**,单证模块头不作数——pick_planner 曾处「头单相、体两相」中间盘面,单证规则在该盘面上会把 planner 核进即时档、与实况相反。本稿 F-3 相关三面(遭遇/planner/equip)均已按双证复核(核验记录见 §1 F-3)。

**残留修法 1——`CwActionPickEncounterOp` 类 docstring 改写**(对齐同文件 `CwActionPickSupplyOp`/`CwActionPickInvestOp`/`CwActionPickPlannerOp`/`CwActionPickEquipOp` 已自述口径):机械链(点卡选中[safe_click bug#1 缓解,area 缺失兜底常量]→ 0.8s → `emit_overlay_confirm` 机械确认,裁决词「遭遇节点」)+ **即时上报**(action_ops.md §1 增补 2:确认点击后立即 `report_action_pick_encounter_param` 发射即写 chosen_encounter,值组装自容器 payload 槽、离屏/越界留证不写);无分步、无落地证据等待、无重入裁决——落地判定归观察侧(外循环按当前画面重识别重派,修法 = 点击链可靠性);派发即终结,画面 op 派发后 round_success 交回。交互陷阱事实保留、换承载表述:「点卡身选中 → 点选择确认,中间禁插空白点击(取消选中 → 死循环;交互模型 = docs/game/screens/currency_war_encounter.md)——固定顺序确认链本身即承载,无额外防线结构」(原「落地由画面 op handle 顶部重入裁决承载」「防线由重入裁决 + 预算耗尽 bail 承接」删除)。依据 = 该 op 自身 run 体(发射即写已落地,类 docstring 单方滞后)+ action_ops.md §4.5 PickEncounter 行现文。

**残留修法 2——附带 `operations/cw_screen/_overlay_confirm.py` 模块头**:通用段「overlay 关没关由调用方节点下一轮重入的入口观察裁决——重入时入口词不在 = 已离开本画面 → success 交回;仍在 = 基于新观察重做确认动作」补现役分型注:重入裁决出口语义仅**未迁移屏**(节点循环单选屏未迁移六屏:巨星/伙伴/祈愿/星徽/卜者/专家;名单 = op-layer.md §3 节点循环行去除已迁移成员装备/策划——武装箱为全形态点卡即选零写屏,模块头自申报无重入裁决旗标,不属此列)承载;已迁移屏中经 `emit_overlay_confirm` 收尾者(遭遇/策划/投资两屏)= round_retry 旁路产物经 `env.round_result` 回传且宿主不消费;补给 = `round_by_find_and_click_area` 确认、装备 = 点卡即选,不经本模块(N-r4-1 清偿:机制描述限员到经 `emit_overlay_confirm` 收尾者,不再均摊全迁移族——补给确认走 `round_by_find_and_click_area`、装备点卡即选,均不产生 round_retry 旁路产物)。机械语义描述(mouse_move 缓解 / 固定等待 / 无条件 round_retry / 零读屏)不动。

**残留修法 3——模块头「自上报统一」段史述收敛(经 T-37 归口自 T-5 §2.4 承接)**:段内两处史述删除——①段首括注中的撤销史「撤销 2026-09-18 动作 op 重组批 §1.1『零上报例外登记』」(变更史 + 过程件节号);②「原『发射/落地两相』例外……已随投资两屏、供给、装备、策划各迁移批全域清偿(迭代 2026-09-21……)」整句(变更史叙述,其现役结论由段内保留句「现役全族 = 机械链发出后立即一口写完整结果,容器写语义单点 = 各上报函数,零证据闩零重入裁决补写面」承载)。保留面:段首泛化批名标签「(pick-op-unify 批)」(收敛判据允许的泛化批名,同 T-5 §2.7 口径)、「零写族落 zero_writes」(现值为真)、持久索引「用户裁定 = `flow/action_ops.md` §1 增补 2」。依据 = AGENTS.md §8「变更史不进注释」(该两处即 T-5 F-4 的发现本体);收敛界线与 T-5 §2.4 目标段一致(现役声明句保留),施工方由 T-5 §2.4 改为本稿(T-37 归口裁决,见下)。

**归口声明(模块头「自上报统一」段)**:T-37 裁决 = 该段归本稿 §2.3(同批登记:game_state/README.md 域表行以 T-5 §2.1 为准、logic-updates/README.md PickSupply 行以 T-5 §2.2 为准)。被让渡对象如实描述:T-5 稿(supply_node.md)前版 §2.4 = 「『自上报统一』段残留史述收敛」规格——保留现役声明句、只删两处变更史句与过程件节号,**语义与代码一致,无「与代码矛盾」**;其停止施工的依据是 T-37 归口裁决本身(该段全部待清面——语义面已清偿、注释纪律面即史述收敛——由本稿 §2.3 承接,见残留修法 3),非对方规格失真;其前版交叉面声明「该段残留收敛以本稿 §2.4 为准,T-4 稿 §2.3 该段规格作废」攻击对象为本稿初版三档规格(已作废),方向与 T-37 裁决(段归 T-4 §2.3)相反。**现状对账(N-r4-2 清偿)**:T-5 侧已随其修订履行让渡——supply_node.md §2.4 现文 = 让渡声明(前版段规格与「以本稿为准」交叉面声明自declared 作废,其 §2.7 同步声明「本稿 §2.4 为让渡声明,不构成第三处落点」),上述跨稿待办已闭,无遗留反向声明。本段后续若再漂移,按「模块头 + 函数体/调用方 run 体双证」重新核录,不以任何稿面转述为准。

**关键取舍**:①残留修法只触三面(encounter 类 docstring、`_overlay_confirm.py` 模块头、模块头段史述收敛),不动已清偿语义面——对已清偿面再立改写规格 = 制造同族新漂移(初版 A-1 的教训);②模块头段归口收本稿且史述收敛面一并承接——归口若只转移语义面,AGENTS §8 违规面将因 T-5 §2.4 停工而无人施工;T-5 §2.4 为纯注释纪律规格、与代码无矛盾,其停工依据 = 归口裁决而非规格失真,归口声明如实记录,防后续读者以「对方规格失真」误拒重启该面;③`emit_overlay_confirm` 函数 docstring 不动——其机械语义(round_retry 旁路、零读屏)仍准确,陈旧的是调用方形态描述,归模块头。

### 2.4 F-4 修法

**`game_state/README.md` §3.3 域表行(落记 T-37 裁决,本稿不持行文本)**:T-37 裁决 = 该行行文本唯一落点 = T-5 稿(supply_node.md)§2.1,本稿原目标行文本作废——本稿遭遇侧语义输入(删 `encounter_refresh_used`/`supply_refresh_used` 退役字段、补 `encounter_refresh_left` 等剩余语义四字段、主写渠道改①观察、删 on_outcome 退役机制描述、「None = 未观察 = 拒绝」口径与 fields.md §3.4.1–§3.4.4 逐字段指针)已由 T-5 §2.1 吸收(其交叉面声明在册:「实施时行文本以本稿 §2.1 为准,T-4 稿对应目标行版本作废……此裁决挂汇总任务 T-37 登记」)。字段语义核正随裁决在册:逐卡限定词仅辖 `strategy_refresh_left`(键 = 注册表规范卡名,fields.md §3.4.4),`env_refresh_left` = 投资环境屏屏级单值(fields.md §3.4.3)——本稿原行「env/strategy 逐卡」措辞与字段级正本不符,不采。

**`flow/session.md` 两处(本稿自清,遭遇 + 补给半边一并;认领依据 = T-5 修订版 §0 修法覆盖面不含 flow/session.md,让渡无对手方)**:

- §2.4 迁出落点表「`_supply_refresh_used` / `_encounter_refresh_used`」行:整行删除——两符号均已退役、无载体、无防重入语义(遭遇半:三出口均终结,encounter.md §5;补给半:`supply_refresh_used` 随剩余语义化退役在册,fields.md §3.4.2;两符号 src/ 与 sr-od-test/ grep 零命中,报告 §3.9)。
- §5.5「`_supply_refresh_used`/`_encounter_refresh_used`:按 §2.4 落点迁,防重入语义逐字段保持(…)」条目:整条删除(遭遇现无保持对象——三出口均终结;补给同——补给刷新链 = 终结形态,fields.md §3.4.2);「`star_regression_count` 随停机钩子退役删除,不迁移」与「`megastar_candidate_clicked` 按 §2.4 定案落 `ctx.cw_match` 级局容器」两分句仍真,保留原位。

**关键取舍**:①session.md 两处收回本稿自清而非让渡 T-5——T-5 修订版修法覆盖面(其 §0)不含 flow/session.md,维持让渡 = 残段无人施工;「同一行一次改写避免中间态」的让渡理由只对 README 域表行成立(T-5 §2.1 认领全行,裁决在册),session.md 是本稿独占发现面,无同行冲突可避;补给半边的退役证据与遭遇半同源(fields.md §3.4.2 在册 + grep 零命中),一并落定不构成再设计。②域表行不持行文本——T-37 已裁全行落点 = T-5 §2.1,双版并存时实施者无法确定行文本;本稿遭遇侧语义已吸收进裁决版,落记裁决即保序,行文本语义真值锚定 fields.md §3.4.1–§3.4.4(逐卡/屏级单值以字段级正本为准)。

### 2.5 F-5 修法

`obs/cw_node_obs.py::read_encounter_options` docstring 末句「读不到 title(OCR 漏/非遭遇屏)→ 返 [](handler 退默认 idx0)」→「读不到 title(OCR 漏/非遭遇屏)→ 返 [](画面 op act 空候选零点击 round_success 终结交回重读,禁盲选派发——选卡确认不可逆消耗本节点;screens/encounter.md §4/§8)」。docstring 其余句(难度默认 1/奖励带/排序)不动(仍准确)。依据 = encounter.md §2/§4 现役空候选口径(报告 F-5)。

### 2.6 实施文件面全集(合并实施对账用)

- **行为变更(仅 F-1)**:`operations/cw_screen/cw_screen_encounter.py`(act 守卫/直发/注释/docstring)、`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens.py`(补两锁)。
- **代码内文档(F-3/F-5,零行为变更)**:`operations/cw_op/cw_overlay_pick_action.py`(`CwActionPickEncounterOp` 类 docstring + 模块头段史述收敛,见 §2.3 残留修法 1/3;模块头语义面已随批清偿)、`operations/cw_screen/_overlay_confirm.py`(模块头分型注)、`obs/cw_node_obs.py`。
- **正本文档(F-1 as-built / F-2 / F-4)**:`screens/encounter.md`、`game_state/logic-updates/pick-encounter.md`、`flow/session.md`(§2.4 迁出落点表行整行删 + §5.5 条目删,遭遇 + 补给半边一并自清)。
- **跨稿共享文件(本稿不独立实施)**:`game_state/README.md` §3.3 域表行(全行落点 = T-5 稿 §2.1,T-37 登记;本稿行文本作废、遭遇侧语义输入已吸收)、`game_state/logic-updates/README.md`(统改权 = T-1 稿 §2.4;本稿交付 PickEncounter 行目标语义、计数现值口径与缺档落法指针,见 §2.2)。
- 其余文件零触碰;F-2..F-5 零行为变更(纯文档/注释)。
