# T-13 祈愿试炼 修法设计(wish_trial)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决+新规范增补待裁决+坐标规范增补待裁决(对抗轨迹:r1 未收敛 4 条→修订→r2 未收敛 1 条低→修订→r3 收敛 0 条→增补节定点对抗(`respec-attack-C16.md`)未收敛 5 条低→按攻击结论修订 §3[F-1 落本稿 §3.2 增补 §2.2 族级统一修法建议 bullet 拆写;F-2/F-3/F-4/F-5 落 bookcard/box_pick/expert_invite 三姊妹稿];攻击结论 = `.debug/progress/2026-09-22-cw-screen-review/reviews/T-13-attack-r1.md` / `T-13-attack-r2.md` / `T-13-attack-r3.md` / `respec-attack-C16.md`;新规范增补 = §3,依据 = 重审报告 respec-T9-T15.md §2.5 + op-layer.md §1.1 :34/:36;坐标规范增补 = §4,依据 = 增补底册 `.debug/progress/2026-09-22-cw-screen-review/reports/coord-norm-addenda-plan.md` §1/§2.1 + op-layer.md §1.1 :35/:48(commit 9c8e9016b);坐标增补定点对抗(`.debug/progress/2026-09-22-cw-screen-review/reviews/coord-attack-T13-14.md`)未收敛 8 条(中1 低7)→按攻击结论修订 §4[F-3(两稿)落本稿 §4.1-7 增补 e/f;F-4 落本稿 §4.2 门句按屏特化 + §4.5-1 删不可构造判据;F-5 落本稿 §4.4 连带申报 2 补类头逐字改文 + 指针改指;F-6(T-13 半边)落本稿 §4.2 画面 op 模块 docstring 改文;A-3 同族对账(coord-attack-T15-16-17.md 同款)落本稿 §4.2/§4.6;F-1/F-2/F-7/F-8(T-14 半边)落 bookcard.md]))
- 发现源:`.debug/progress/2026-09-22-cw-screen-review/reports/T-13-r1.md`(F-1..F-3;总判定高1 低2)。涉事代码与代码内文档以仓库现状为真值;本文定位一律符号锚 / 文档节号(行号不作定位依据,约定 = flow/README.md 卷首)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 问题与动机

### F-1 画面 op 决策出口:None/非法类型/策略异常盲选 idx0 回退 + idx 越界静默钳位(高)

- **现状症状**:`operations/cw_screen/cw_screen_wish_trial.py::CwScreenWishTrial.act` 决策段,报告 F-1 三条路径——①`decide_wish_trial()` 返回 None/无 `.idx` 的异型 → AttributeError 落入宽 `except Exception` → 盲选第 1 张降级续跑;②策略入口按契约抛错(含 `strategies/impl/flow.py::_require_slot_options` 对「离屏 None = 观察层失约」的 ValueError)被同一 `except` 吞掉转盲选——契约要求的响亮暴露在消费侧被静默吸收;③返回 idx 越界 → `if 0 <= idx < len(self.CARD_XS)` 不命中 → 保持 idx=0/FIRST_CARD 静默钳位续跑(流程侧值域改写)。另有一条报告未单列的同段残留(路径④):`_match` 缺席时决策不被调用,以 `FIRST_CARD` 常量盲发首卡(纯常量盲发,无任何判据调用)。三条主路径均为策略器 bug 才可达(现役 `flow.py::decide_wish_trial` 返回契约上合法,报告 F-1 差距说明),但正本恰规定该情形必须响亮暴露而非静默兜底;下游后果 = 盲选轮 objective 文本在场时 `_record_chosen` 把无策略依据的选择写入 `chosen_wish`(记录面口径在册,后果面 = F-1 下游)。
- **根因归层(根源两问)**:根在**流程层**——handler 时代「决策失败安全兜底」残留(act 内注释自述「决策链异常 fallback 第 1 张(姊妹 handler 同姿态)」)。决策控制分层铁律(flow/README.md §1)已把「动作值域过滤」划归策略侧、禁流程侧任何决策闸门与政策判断;流程侧合法判断面仅防 bug 守卫断言(非控制流)与失败治理;op-layer.md §1.1 出口③(「决策无有效输出也走此出口——零盲发」)与 §1.3(「非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)」)反向禁止。本修法删兜底、换守卫,修根非症状。跨件半问已过:同族七例同根(→ §2.2),根的载体 = 各屏 act 内残留代码,画面 op 层不设共享基类/端口(op-layer.md §4 在册),族级形态统一收敛、归口 T-37,不升架构级设计件。
- **解决到哪**:决策段改三重守卫(无策略器可问/返回 None/词表外 = 具名 round_fail 零盲发;idx 越界 = 守卫断言 AssertionError;策略异常删宽 except 自然传播),删全部默认 idx/钳位/兜底常量,派发改直发策略产实例;`screens/wish_trial.md` as-built 申报守卫出口、退役原回退面。
- **明确不解决**:空候选/无文本 = 策略侧自主决策(报告 F-1 差距说明在册「空候选返回 idx=0 属策略侧自主决策」;观察侧空桶照写在册 = screens/wish_trial.md §3)——策略域判据不动;「离屏 None = 观察层失约抛错」口径本体(修法 = 不再被吞,不改口径);策略器返回契约本体(`strategies/impl/cw_strategy.py::decide_wish_trial` 返回注解在册);重入裁决/`chosen_wish` 留守写点形态(检查②一致面 = 在册欠账,`flow/action_ops.md` §2.3 存量禁新增;迁移归逐批,本稿不顺手迁移);卡身卡位/objective 读区未 area 化(fields.md §3.4.5 + screens/wish_trial.md §4 挂账实机批的在册欠账);`_record_chosen` 守卫逻辑(零改动,仅 docstring 口径句随守卫同步);兄弟屏同族面(→ §2.2 家族联动面,归口 T-37);报告 §4 无法核对面(实机验证归运行期)。

### F-2 注释会话局部编号 / 行号锚 / 变更史残留(低)

- **现状症状**(三站点,以现盘代码为准):①`cw_screen_wish_trial.py` 模块头前三行注——「已接入 cw_loop:255(2026-08-08 实测:……D-87~89 闭环)」「r104(2026-08-20):选卡接入策略模块……」:「cw_loop:255」= 随代码漂移的行号锚、「r104」「D-87~89」= 会话局部编号、「接入/闭环」= 变更史;②同文件 `__init__` 注——「r116 热修(局33 实证:r104 重写本类时漏传 ctx……空转 553 iter;签名对齐其他 handler)」:r116/r104/局33/553 iter = 会话局部编号 + 变更史叙事;③同族:`strategies/impl/flow.py::decide_wish_trial` docstring「r104 接入策略模块;原固定第1张」——「r104」= 会话局部编号、「原固定第1张」= 变更史。
- **根因归层**:**约定层(注释纪律残留)**——仓库根 AGENTS.md §8「引用必须是持久索引:注释里禁出现会话局部标识符(W 轮次号 / rN / 批N / `[N]` 之类只在当次会话有意义的编号)」「变更史不进注释:『何时改的 / 从什么改成什么 / 勘误过程』归 git 历史」。
- **解决到哪**:三站点逐处给目标处置(§2.3);模块头「OCR 失败 fallback 第 1 张」句同时是 F-1 退役行为面,随 §2.1 一次施工。
- **明确不解决**:模块 docstring/act 内其余注释面(泛化批名 = 在册可溯形态,审查已判不计;其余句子随 F-1 §2.1 守卫语义注施工,不在本条重复立);`flow.py::decide_wish_trial` 打分说明段(仍准确);F-3 辖面(`cw_overlay_pick_action.py`)。

### F-3 CwActionPickWishTrialOp 类 docstring 坐标来源申报失实(低)

- **现状症状**:`operations/cw_op/cw_overlay_pick_action.py::CwActionPickWishTrialOp` 类 docstring 申报「选中点 = 建档卡位决策半现算」;实际 `env.target` 组装 = `cw_screen_wish_trial.py` 决策段 `Point(self.CARD_XS[idx], CwScreenWishTrial.CARD_Y)`——槽 x/y 为实测类常量,卡位未建档(yml 无卡位/objective 读区 area,报告 F-3 双证)。读者会误以为点击点已走 screen_info 单一真相源,与同屏画面 op 类头申报(「卡位为实测字面量,未 area 化」)及 screens/wish_trial.md §4(「现走槽常量」)自相矛盾。
- **根因归层**:**约定层(注释出处失实)**——AGENTS.md §8(注释须让读者只看代码与注释即可重建推导,出处失实即失效)。
- **解决到哪**:失实子句改写为现值来源申报(§2.4)。
- **明确不解决**:卡位 area 化消费改造(行为变更,在册欠账归实机批);同文件其余 pick op 类 docstring(各屏审查辖);「pick-op-unify 批」泛化批名(正本文档在册迭代名 = 持久索引,报告 §3.8 已判不计);「bug#1 缓解」标签保留 = 与 T-11 稿同判(跨文件在册交互陷阱标签,非会话局部;T-7 稿对同形标签判清出——两派分歧随 §2.2 登记候 T-37);run 体机械链描述(逐位准确,不动)。

### 在册核对结论

审查报告 §3 八项一致面(节点循环形态/重入裁决与留守 chosen 写点/决策控制正面半——打分全在策略器、idx 坐标系对齐/容器写纪律/观察上报/动作 op 行/wish_trial.md 九节主体/注释纪律其余面)核对通过,不立修法;在册欠账(卡身卡位与 objective 读区未 area 化、重入裁决写法迁移、logic-updates/README 整体过时、action_ops §4.5 计数滞后)不重复立项。本稿全部修法不回退任何一致面。

## 2. 方案

### 2.1 F-1 修法(核心·本屏)

**代码面**(`operations/cw_screen/cw_screen_wish_trial.py::CwScreenWishTrial.act` 决策段):

1. **删三件兜底残留**:默认初始化三行(`target = CwScreenWishTrial.FIRST_CARD` / `pick_desc = 'fallback第1张'` / `pick_idx = 0`)、宽 `try/except Exception` 全体(含 `log.warning('[cw-wish] 策略决策异常(fallback 第1张)…')`)、钳位句 `if 0 <= idx < len(self.CARD_XS):`(默认值改写形态的钳位);连带删类常量 `FIRST_CARD`(唯一消费点 = 兜底分支,删后零消费)。
2. **守卫①(决策输入:无策略器可问 = 具名 fail 零盲发)**——重入裁决块之后、调策略器之前:

   ```python
   _match = getattr(self.ctx, 'cw_match', None)
   if _match is None:
       return self.round_fail(
           '[cw-wish] 决策无有效输出零盲发(无策略器可问,禁流程侧代行选卡)')
   ```

   依据:op-layer.md §1.1 出口③「决策无有效输出也走此出口——零盲发」+ flow/README.md §1 铁律(决策的值域由策略器定,流程侧禁代行);round_fail 消息经框架节点状态日志落盘即留证,不另加日志行。**语义变化显式申报**:无 match 局外直跑由「盲发首卡」变「fail 零盲发」(路径④;收编理由见关键取舍 2)。落点 = op fail 交回外循环,受外环连续 fail 重派网兜底(flow/README.md §4,`cw_loop.py::CwLoop.OP_FAIL_REDISPATCH_LIMIT`)。
3. **守卫②(返回契约:None/词表外 = 具名 fail 零盲发)**——决策调用后:

   ```python
   pick = _match.strategy.decide_wish_trial()
   if not isinstance(pick, CwActionPickWishTrialParam):
       return self.round_fail(
           f'decide_wish_trial 决策无有效输出(词表外/None): {pick!r}')
   ```

   依据:契约注解 `decide_wish_trial() -> CwActionPickWishTrialParam`(flow/README.md §2.2 pick 族行 + `strategies/impl/cw_strategy.py::decide_wish_trial`)的运行期执行;消息含策略器返回原值(repr)= 留证。先例 = 备战决策循环「非 CwAction 返回 → 具名 fail 留证」(flow/README.md §2.2 decide_prep_screen 行)与同族遭遇/装备修法守卫①(encounter.md/equip_pick.md §2.1 同形态)。`CwActionPickWishTrialParam` 已在本文件 import 面,零新增依赖。原「AttributeError 落 except」路径①由本守卫收编(该子径本属合规异常出口,具名消息含原值,诊断面优于 NoneType 反推)。
4. **删宽 except = 路径②修法**:决策调用不包 try——策略异常(含 `_require_slot_options` 按契约故意抛出的离屏失约 ValueError、gs 缺席 AttributeError)自然传播 = 出口③异常 fail;框架异常路径 = 出口③现役实现形态(节点异常 → 留证截图 → `node_max_retry_times=8` 预算耗尽 op fail;该预算「现役值仅框架异常路径消费」在册 = screens/wish_trial.md §2)——确定性 bug 每轮必炸,预算内有界响亮终止。
5. **守卫③(值域:idx 越界 = 守卫断言恒炸)**——紧随守卫②:

   ```python
   if not (0 <= pick.idx < len(self.CARD_XS)):
       raise AssertionError(
           f'[cw-wish] pick idx 越界(策略器 bug,禁钳位): '
           f'idx={pick.idx} 槽数={len(self.CARD_XS)} pick={pick!r}')
   ```

   依据:op-layer.md §1.3「执行侧只余守卫断言——防 bug 路栏而非控制流分支,非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)」;同款先例 = `operations/cw_op/cw_action_registry.py::action_op_class_for_type`(词表外 AssertionError 响亮暴露)。
6. **守卫次序与位置**:①→②→③依次(先输入、后契约、再值域);三守卫均在任何点击之前——动作 op 执行即发出「点卡选中 → 确认」点击链,无决策/越界放行 = 盲发不可逆消耗,必须派发前拦;守卫位于重入裁决块之后,每轮重入(未落地重走轮)重新过守卫,单一 choke 点无重复布防。
7. **组装与日志**(守卫③后,`pick.idx` 已保证在界):

   ```python
   target = Point(self.CARD_XS[pick.idx], CwScreenWishTrial.CARD_Y)
   pick_desc = f'卡{pick.idx + 1}({objs[pick.idx][:20] or "OCR空"})'
   log.info('[cw-wish] 祈愿决策: %s → 点 (%s,%s)', pick_desc, target.x, target.y)
   ```

   `objs[pick.idx]` 取值安全 = 生产编排内的结构保证(两跳):①`node_from` 边保证 act 只在观察 node 成功后执行,`_obs` 恒由观察产物组装;②观察组装恒走 `_read_objectives`——对每槽各产一串,与 `CARD_XS` 等长。故生产编排内 options 恒与 `CARD_XS` 等长;该保证**不辖测试注入面**(现役测试即注入 2 项 options 而 `CARD_XS` 为 3 槽)——日志组装与现役决策段同点同险(`objs[idx][:20]`),不新增防御。零判效零决策,纯日志描述。
8. **置 pending 与派发改直发**:`self._confirm_pending = (list(objs), pick.idx)`;`_env = OverlayPickExecEnv(op=self, idx=pick.idx, target=target)`;`action_op_for(pick, self.ctx, _env).execute()`(删 `CwActionPickWishTrialParam(idx=pick_idx)` 重建行)。直发后:注册表按 isinstance 解析(词表内无该类型父类行,单一命中);动作 op 自上报 `report_action_pick_wish_trial_param` 消费 `action` = 策略产实例(携带策略真实 idx/reason)——上报 param 单一源 = 策略产值。
9. **`_record_chosen` 零逻辑改动 + docstring 口径句同步**:写端守卫(objective 未读到/选中槽文本空不写)语义保持;docstring「守卫口径=事实落地选择记录(含策略降级路径的选择,区别于 tome 的决策不可判不写式)」改为「守卫口径 = 事实落地选择记录:objective 未读到/选中槽文本空不写(None 保持「无记录」,与 chosen_tome 式同口径);策略异常 = 决策出口守卫 fail 零盲发,不存在降级选择轮,故无『策略降级路径选择』记录」(目标文本 = 纯现值陈述,不带史述引导语)。
10. **注释废弃与替换**:删决策段注「策略决策(r104):写槽已由 report 落容器 wish_trial_opts → 零参决策;决策链异常 fallback 第 1 张(姊妹 handler 同姿态)」(r104 面 = F-2 同站点;兜底自述废弃理由见 §1 F-1),原位替换守卫语义注:无策略器可问/返回 None/词表外 = 具名 fail 零盲发(op-layer §1.1 出口③);idx 越界 = 守卫断言(op-layer §1.3);策略异常自然传播(离屏失约 ValueError 不再被吞);空候选 = 策略侧自主决策,非兜底。删派发注「(上报 param 即真实选择;fallback/越界 = 0)」→「(直发策略产实例,上报 param = 策略产值原值)」。
11. **docstring/注释同步(画面 op 三处 + kernel 屏文件两处)**:①act docstring 补一句守卫出口(口径同上);②模块 docstring 形态段「决策动作 node = 重入裁决顶部……→ 决策从容器零参读 → 选卡+确认链经……」句后补守卫出口句;③observe docstring 括注「(决策走决策面 fallback 分支,分支原样)」→「(决策面无局外兜底:无 match = 决策无有效输出走守卫 fail)」;④kernel 屏文件配套(`kernel/cw_screen_report/wish_trial.py`,零行为):obs 类 docstring「空桶照持(原写点无空门,决策侧 fallback 首卡)」与 report 函数 docstring「段内直写,无空门——OCR 空桶照写,决策侧 fallback 首卡」两处「决策侧 fallback 首卡」子句改「决策侧无兜底:决策无有效输出 = 守卫 fail 零盲发(申报见 screens/wish_trial.md §8)」(目标文本 = 纯现值陈述,参照 megastar 稿 `obs/cw_node_obs.py::read_megastar_options` 配套处置的同形判例)——观察侧「空桶照写」的合法性不得挂靠退役中的决策兜底(T-4-r1 F-5 教训:调用方行为随修法改变,注释单方滞后即新漂移)。**零容器写保持**:fail/异常路径不新增 kernel 写端(留证 = 日志 + round_fail/断言消息);画面 op 对容器触点维持 report 调用 + `_record_chosen` 留守写点(报告 §3.4/§3.5 一致面不回退)。

**文档面**(`docs/develop/sr_od/application/currency_war/screens/wish_trial.md` as-built 更新):

- **§2 画面形态声明**:决策子句「(候选自容器槽;打分:……13_pick_family.md §1 E5)」后补——决策出口无屏内兜底:无策略器可问/返回 None/词表外 = 具名 round_fail 零盲发交回外循环(op-layer.md §1.1 出口③),pick idx 越界 = 守卫断言 AssertionError(op-layer.md §1.3,禁钳位),策略异常自然传播;守卫均在派发前、零点击,fail 出口非循环出口、非防御上限;选卡派发 = 策略产实例直发,流程侧零值域改写。
- **§4 动作面**:伪码块改写(原「策略异常 = 留证告警 fallback 第 1 张;越界 = 不改 target」两行随行为退役)——

  ```
  objs = 观察轮 obs 载体 → 无 match = 守卫 fail 零盲发
  pick = decide_wish_trial()(零参;候选读容器 wish_trial_opts 槽)
    (返回 None/词表外 = round_fail 含原值;idx 越界 = AssertionError;策略异常自然传播)
  target = (槽 x 常量[idx], 卡身 y 常量 340) → 置确认 pending → 直发 pick 派发
    (动作 op 内:target mouse_move + click[点卡身选中:金色边框 + 确认选择亮]
     → 1.0s → 点「按钮-确认选择」[round_by_find_and_click_area,success_wait 1.5;
     本屏独有检测,不与 partner/megastar 的同名钮撞——祈愿锚在前已分流]
     → 自上报 report_action_pick_wish_trial_param)
    (机械交回零判效;落地判定归决策动作 node 顶部重入裁决,
     chosen_wish 写端随之在裁决点,防未落地轮留幻影登记)
  ```

  对照表 `CwActionPickWishTrialOp` 行「发出方式」列改「注册表工厂 `action_op_for` 直发策略产 `CwActionPickWishTrialParam` 实例(决策半组装 `OverlayPickExecEnv`:定位点;两守卫派发前,流程侧零值域改写)」;表末补一行:`| (决策无有效输出/pick idx 越界,非动作) | — | — | 守卫 fail:无 match/词表外/None = round_fail(含原值)、idx 越界 = AssertionError;零点击零派发,交回外循环 |`。交互陷阱句(ESC 不关/卡身挂账)不动。
- **§5 终结与交回表**补一行:`| 决策无有效输出/pick idx 越界 | 守卫 fail(op FAIL) | round_fail / 框架异常路径(留证截图 + node_max_retry_times=8 预算耗尽)交回外循环;连续 fail 由外环重派网兜底(flow/README §4) |`——与「入口锚 miss」行同落点类,补行保表完备。
- **§8 守卫与防线**首条「策略异常留证降级(fallback 首卡,不阻塞);盲选 fallback 轮不写 chosen(防把无依据选择固化成记录值)。」改写为三条:①决策出口守卫:无策略器可问/返回 None/词表外 = 具名 round_fail 零盲发——原「策略异常 fallback 首卡」退役申报;②值域守卫:pick idx 越界 = 守卫断言 AssertionError——原「越界保持 idx=0 静默钳位」退役申报;③chosen 记录面:objective 未读到/选中槽文本空不写(None 保持「无记录」)——语义保持,策略异常降级轮已随守卫退役。其余两条(重入裁决/守卫总册指针)不动。
- **§6 状态上报面**:「objective 未读到/选中槽文本空 = 盲选 fallback 不写」→「objective 未读到/选中槽文本空不写」(「盲选 fallback」词面随行为退役;记录面测试既定口径 = 无文本不写,语义不变)。
- op-layer.md 行为规范条款无需新增:出口③/§1.3 已辖本屏情形,屏级申报归 wish_trial.md(正本分层 = op-layer 行为规范 + 各屏 as-built);§1.3 守卫清单登记义务不随本句豁免,单一口径见 §2.2 归口④。

**测试锁**(`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py` 祈愿臂,实现随功能写,锁设计约定 = sr-od-test/README.md):

1. **桩型同型化**:`test_wish_chosen_written_at_reentry_adjudication_only` 决策桩 `SimpleNamespace(idx=0, reason='stub')` → 真词表类 `CwActionPickWishTrialParam(idx=0, reason='stub')`——守卫②收紧类型后 SimpleNamespace = 词表外返回即具名 fail,旧桩打红现役锁;`reason` 字段在册(`kernel/cw_vocab.py::CwActionPickWishTrialParam`),补 import 即可。
2. **定位点断言换锚**:同锁 `(mod.CwScreenWishTrial.FIRST_CARD.x, .y)` → `(mod.CwScreenWishTrial.CARD_XS[0], mod.CwScreenWishTrial.CARD_Y)`——`FIRST_CARD` 随本修法删除;值等价(660/340),断言语义「定位点 = 首卡」不变。
3. **直发适配**:守卫后派发 = 直发策略产实例,`dispatches[0].param` 即桩实例,`param.idx == 0` 断言零改动;其余断言面(未落地不写/WAIT 交回/落地写 chosen/pending 快照重置)全部不变。
4. **补两锁**:①无 match / 策略返回 None / 词表外对象 → `act` 返回 round_fail 且零派发(派发桩零调用),三支合并一锁或分案均可;②策略返回 `CwActionPickWishTrialParam(idx=3)`(槽常量现值 3)→ AssertionError 传播且零派发。
5. **在册锁不冲突核对**:`test_cw_game_state_consume.py` 祈愿案 fallbacks 全部直调 `_record_chosen`(记录面自身守卫,逻辑零改动)——零改动;`test_cw_unified_action_4.py` 祈愿 op 锁 = 机械链行为锁(直传真实词表类,不经画面 op 决策出口)——零改动;`test_cw_screen_report_ports.py` 观察上报面——零改动。

**关键取舍**:

1. **三路径出口分工**:None/词表外 = 守卫②具名 fail(出口③明文「决策无有效输出走异常 fail——零盲发」;具名消息含原值,诊断面优于任由 AttributeError 裸炸);策略异常 = 删宽 except 让传播(出口③现役实现形态,零新增结构);idx 越界 = 守卫③ AssertionError(§1.3 守卫断言语义 + 注册表同款先例)。两 fail 落点(round_fail 直落 / 框架异常路径预算耗尽)均为既有框架语义,不引入第三种出口语义。
2. **无 match 支收编守卫①(语义变化申报)**:报告 F-1 三条路径均以「策略器被调用且非法」为前提,无 match 支未被单列;但该支与三路径同段同根(流程侧代行决策——纯 `FIRST_CARD` 常量盲发,无任何判据调用),修后若保留则同段并存「守卫零盲发」与「盲发首卡」自相矛盾。收编对齐 T-8 巨星稿守卫①形态;与 T-9 装备稿「保留无 match 支」不冲突——装备支 = kernel 判据直调(真实判断,豁免面在册),本屏支 = 纯常量盲发(无豁免基础);两判据的族级对账归 T-37(§2.2)。生产行为零变化(cw_loop 对局内 cw_match 恒在场),变化面仅局外直跑/MCP 手动语境。
3. **删宽 except 而非 except 内转 round_fail**:任何 `except Exception` 形态都会再把「策略侧按契约故意抛出的离屏失约 ValueError」吞成盲选——正是被查处路径②的机制;传播即合规。
4. **直发 vs 重建**:重建 = 流程侧值域改写载体 + 第二构造点;本屏无缓存复用轮(每轮重入重决策,无巨星确认轮的决策轮缓存形态),直发无「两形并存派发点」问题;idx/reason 单一源 = 策略产值(同 T-4 形态)。
5. **空候选/无文本不设输入守卫**:空候选时策略器被正常调用并自主返回 idx=0(报告 F-1 差距说明在册「空候选返回 idx=0 属策略侧自主决策」;观察侧「空桶照写」在册)——与巨星 F-1 的「屏内自定 idx0」(策略器完全不被调用)型差明确;升级为 fail 会误伤策略域合法缺省。
6. **删 `FIRST_CARD` 而非留死常量**:唯一消费点 = 被删兜底分支;测试断言随值等价锚(`CARD_XS[0]`/`CARD_Y`)同步,不留无消费常量。

### 2.2 F-1 家族联动面(pick 族统一修法建议)

- **家族性模式认定**:「盲选 idx0 回退 + idx 静默钳位(伴生吞策略契约抛错)」已在七例查出——遭遇(T-4-r1 F-1;修法 = 同目录 encounter.md §2.1)、盛会之星(T-8-r1 F-1;megastar.md §2.1)、选择装备(T-9-r1 F-1;equip_pick.md §2.1)、选择伙伴(T-11-r1 F-1;设计稿在途)、命运卜者(T-12-r1 F-1;设计稿在途)、专家邀请函(同款 catch→fallback 实现位互认,T-12 报告辅助事实在册,T-15 审查辖)、本屏(第 7 例)。共同根 = handler 时代「决策失败安全兜底」在画面 op 化迁移中,观察侧失败安全已各自重立(空桶照写/离屏抛错),决策侧兜底残留为流程侧决策闸门与值域改写,违 op-layer.md §1.1 出口③/§1.3/flow/README.md §1 铁律。跨件半问已过:根同层但载体是各屏 act 内残留代码,画面 op 层「不设共享基类/端口」= op-layer.md §4 在册口径,不升架构级设计件,以族级形态统一收敛。
- **族级统一修法建议(形态统一,不建共享代码)**:每个 pick 族画面 op 的决策动作 node 在「调策略器」与「派发」之间内联守卫——①决策无有效输出(输入侧:无策略器可问;返回侧:None/词表外)= 具名 round_fail 零盲发,消息含策略器原值 repr;②值域非法(idx 越界)= 守卫断言 AssertionError(禁钳位);③删全部默认 idx 初始化/钳位句/宽 except(策略契约抛错自然传播);守卫均在任何点击之前。屏幕特形出口以正本在册申报为准(如遭遇「空候选 = 零点击终结交回重读」op-layer §1.1 显名在册),无在册申报的屏一律走 fail 出口。不建共享守卫函数:各守卫 2-3 行、各屏词表类/槽数/日志 tag 不同,共享 helper 的去重收益低于新跨屏依赖与消息语境损失(同 T-9 判)。
- **跨稿分歧登记(候 T-37 裁决)**:无 match 局外支的处置已现分歧——T-9 装备稿保留(kernel 判据直调 = 真实判断,豁免面在册)、T-8 巨星稿收编守卫①(屏内自定 idx0 = 流程代行)、投资环境稿已登记跨稿分歧候裁(T-12 报告 §3 在册欠账 4 汇录);本稿立场 = 收编(祈愿支 = 纯常量盲发,无判据调用可豁免)。建议族级判据 = **按支内是否含真实判据调用分流**(判据直调支可豁免保留,纯常量盲发支一律守卫收编),供 T-37 对账裁定。另一族级口径分歧一并登记:**「bug#1 缓解」标签去留**(T-7 稿判裸缺陷件编号清出 / T-11 稿判跨文件在册交互陷阱标签保留;本稿取保留,与 T-11 同派,依据见 §1 F-3/§2.4)。
- **归口 = 汇总任务 T-37**:①伙伴/卜者两在途稿与本稿守卫形态是否并入一个族级实施批(统一守卫形态、共享测试锁模板、一次对抗);②`operations/cw_op/cw_overlay_pick_action.py::OverlayPickExecEnv.idx` 字段注释「决策半现算快照(钳位后生效值)」陈旧措辞随族级批一次改净——单屏改会让共享 env 注释与未修屏临时不一致,本稿 §2.1 不动它,挂本裁决面;③无 match 支族级口径(上条);④op-layer.md §1.3 守卫清单登记——**无条件默认:本屏两条守卫出口登记 = 本迭代正本更新阶段必做**(现役清单为单例枚举 `guard_proposal_vs_expected`,守卫落地后清单缺员 = 正本申报滞后);T-37 裁族级合并时该登记改族级统一条目、由族级批执行,裁独立实施时由本稿正本更新执行——登记义务不悬置、不随裁决结果消失。本稿 §2.1 独立可实施;若裁族级合并,本稿即族级形态在祈愿试炼的实例,以族级批统一口径为准、不另立第二套。
- **明确不联动**:kernel 判据侧缺省(空候选 idx0 = 策略自主决策,任何屏不得借「家族统一」改判据);已合规屏(投资两屏/遭遇现役出口,T-6/T-7 报告同面核对通过)零改动。

### 2.3 F-2 修法(逐站点目标处置)

`operations/cw_screen/cw_screen_wish_trial.py`:

| 站点 | 现文(节选) | 处置 |
|---|---|---|
| 模块头前三行注 | 「已接入 cw_loop:255(2026-08-08 实测:bot 卡此 overlay 68min 后接入检测 + ……;D-87~89 闭环)。」「r104(2026-08-20):选卡接入策略模块 decide_wish_trial(……)——」「OCR 各卡 objective 文字 → 策略打分(……)→ 点选中卡。OCR 失败 fallback 第 1 张。」 | **整段删除**——「cw_loop:255」行号锚、「r104」「D-87~89」会话局部编号、「接入/闭环」变更史;残余语义(overlay 是什么/怎么决策)已由模块 docstring 完整承载,「OCR 失败 fallback 第 1 张」句 = F-1 退役行为面随 §2.1 一次施工 |
| `__init__` 注 | 「r116 热修(局33 实证:r104 重写本类时漏传 ctx → 祈愿试炼触发即崩,loop 空转 553 iter;签名对齐其他 handler)」 | **整段删除**——r116/r104/局33/553 iter 会话局部编号 + 变更史;现值面「构造显式传 ctx」= 框架构造契约自明,无「为什么」可留 |

`strategies/impl/flow.py::decide_wish_trial`:

| 站点 | 现文(节选) | 处置 |
|---|---|---|
| docstring 首句括注 | 「(终态零参口;候选 = ``gs.wish_trial_opts``;r104 接入策略模块;原固定第1张)」 | 改「(终态零参口;候选 = ``gs.wish_trial_opts``)」——「r104」会话局部编号、「原固定第1张」变更史;后续打分说明段仍准确,不动 |

依据:AGENTS.md §8(禁会话局部标识符/行号锚不作定位依据/变更史不进注释)。全组零行为变更;与 §2.1 同文件的站点(模块头 fallback 句、act 内 r104 注)一次施工,不重复列。

**关键取舍**:模块头注选「整段删除」而非改写——其仅有的现值语义已被模块 docstring 承载,保留改写版 = docstring 与头注双源;`__init__` 注选删除而非留「签名对齐」一句——签名 = 框架契约,自明。

### 2.4 F-3 修法

`operations/cw_op/cw_overlay_pick_action.py::CwActionPickWishTrialOp` 类 docstring 第二段首句:

- 现文:「点试炼卡身选中(bug#1 缓解,选中点 = 建档卡位决策半现算)→ 选中动画固定等待 → ……」
- 目标:「点试炼卡身选中(bug#1 缓解,选中点 = 画面 op 决策半按槽 x/y 实测常量现算、经 `env.target` 传入——卡位未 area 化,坐标单一真相源缺口挂账实机批,申报同 `cw_screen_wish_trial.py` 类头与 screens/wish_trial.md §4)→ 选中动画固定等待 → ……」

依据:AGENTS.md §8(出处失实即失效);交叉证据 = 画面 op 类头「卡位为实测字面量,未 area 化……卡身建档挂账实机批」+ screens/wish_trial.md §4「卡身建档(卡位坐标)挂账实机批,现走槽常量」+ 报告 F-3 双证(`env.target` 组装点 = `Point(self.CARD_XS[idx], CwScreenWishTrial.CARD_Y)`)。docstring 其余句(确认钮 area 点击/`chosen_wish` 留守申报)与 run 体逐位一致,不动。

**关键取舍**:只改失实子句、不扩面;「卡位未 area 化」如实保留为挂账申报而非删掉——防「改注释 = 消欠账」假闭环(同 T-9 F-3 取舍);area 化消费改造 = 行为变更,归在册实机批。

### 2.5 实施文件面全集(合并实施对账用)

- **行为变更(仅 F-1)**:`operations/cw_screen/cw_screen_wish_trial.py`(守卫/直发/删 `FIRST_CARD`/注释与 docstring 同步;含 F-2 同文件两站点)、`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(桩型同型化 + 断言换锚 + 补两锁)。
- **代码内文档(零行为变更)**:`operations/cw_op/cw_overlay_pick_action.py::CwActionPickWishTrialOp` 类 docstring(F-3)、`strategies/impl/flow.py::decide_wish_trial` docstring(F-2)、`kernel/cw_screen_report/wish_trial.py` 两处「决策侧 fallback 首卡」子句(F-1 连带,见 §2.1.11④)。
- **正本文档(F-1 as-built)**:`screens/wish_trial.md`(§2/§4/§5/§6/§8);`screens/op-layer.md` 零条款新增(§1.3 守卫清单登记义务归属本迭代正本更新阶段,见 §2.2 归口④)。
- **跨稿共享面(本稿不独立实施)**:`OverlayPickExecEnv.idx` 字段注释(pick 族共享 env,挂 §2.2 T-37 裁决面);族级实施批归口 T-37。
- 其余文件零触碰;F-2/F-3 零行为变更(纯注释)。

## 3. 新规范增补(2026-09-22 两条款)

> **增补依据**:正本 `screens/op-layer.md` §1.1 两条款(commit 2f35d4011 入正本,用户裁定 2026-09-22)——**:34 观察标准化门**、**:36 画面 op 不支持局外单独调用**;重审报告 = `.debug/progress/2026-09-22-cw-screen-review/reports/respec-T9-T15.md`(本屏节 = §2.5,跨屏共性 = §2.8)。两条款入正本晚于本稿对抗收敛,本节 = 在已收敛守卫化主体上的申报级/改写级增补,不推翻主体(报告卷首时序说明)。
> **条款①(:34)本屏不适用**:观察面 = objective 自由文本(`cw_screen_wish_trial.py::CwScreenWishTrial._read_objectives` 报 `wish_trial_opts`),决策 = `decide_wish_trial` + `PICK_BIAS` 关键词打分,无标准注册表在册(报告 §2.5 Q1)——无登记面、无欠账。
> **增补方式**:本稿 §0..§2 已收敛内容零直接改动;凡既有目标文本需连带改写处,逐字目标文本在本节给出(含落点节号),待用户裁决后随落地批一次落笔;本节自身为待裁决工件,裁决前不落任何代码与正本文档(迭代边界 = `changes/2026-09-22-screen-review/README.md`「只设计不落码」)。§0 状态行已就地更新。

### 3.1 增补点①(:36)守卫① match 臂 round_fail → round_success 终结交回

**判据**::36 明文「无 match(局外)= 零决策零点击 round_success 终结交回(遭遇屏在册先例同款),不设任何兜底决策路径」——守卫①的 match 缺席臂零决策零点击 ✓,但出口 = fail ≠ :36 裁定的 round_success(报告 §2.5 Q2)。凡断言该臂出口 = fail 的站点全部连带改写。

**逐字改写文本(落点 → 目标)**:

1. **§2.1 第 2 条守卫①标题与目标代码块**:标题「守卫①(决策输入:无策略器可问 = 具名 fail 零盲发)」改「守卫①(决策输入:match 缺席 = 局外零决策零点击 round_success 终结交回,op-layer.md §1.1 :36)」——位置声明(重入裁决块之后、调策略器之前)不变;代码块改:

   ```python
   _match = getattr(self.ctx, 'cw_match', None)
   if _match is None:
       return self.round_success(
           '[cw-wish] 局外无 match,零决策零点击终结交回(op-layer §1.1 :36)')
   ```

2. **§2.1 第 2 条依据段**整段改写为:「依据:match 缺席(局外)= op-layer.md §1.1 :36 直接落码——『零决策零点击 round_success 终结交回(遭遇屏在册先例同款),不设任何兜底决策路径』;先例代码锚 = `operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter.act`(:156-165,`match is None` 臂 → `round_success('候选读缺/局外,零点击终结交回重读')`,实查在册)。返回 None/词表外臂(守卫②)才是出口③『决策无有效输出——零盲发』辖面,不受本增补影响。**语义变化显式申报**:无 match 局外直跑由『盲发首卡』变『零决策零点击 round_success 终结交回』(路径④;收编理由见关键取舍 2 与 §3-②)。落点 = success 终结访问交回外循环,外循环重进重读;不涉 fail 预算面,原『外环连续 fail 重派网兜底』描述随出口改写作废。」
3. **§2.1 第 10 条守卫语义注**(原位替换注)第一分句拆写为:「match 缺席(局外)= 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36);返回 None/词表外 = 具名 fail 零盲发(op-layer §1.1 出口③);」——其后分句(idx 越界/策略异常/空候选)不变。
4. **§2.1 第 11 条③ observe docstring 目标文本**(报告 §2.5 增补 A 列名):「(决策面无局外兜底:无 match = 决策无有效输出走守卫 fail)」改「(决策面无局外兜底:无 match = 零决策零点击 round_success 终结交回,op-layer.md §1.1 :36)」。
5. **§2.1 文档面 §2 决策子句**:「决策出口无屏内兜底:无策略器可问/返回 None/词表外 = 具名 round_fail 零盲发交回外循环(op-layer.md §1.1 出口③)」改「决策出口无屏内兜底:match 缺席(局外)= 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36);返回 None/词表外 = 具名 round_fail 零盲发交回外循环(op-layer.md §1.1 出口③)」——其后子句(idx 越界/策略异常/直发申报)不变。
6. **§2.1 文档面 §4 伪码首行**(报告列名):`objs = 观察轮 obs 载体 → 无 match = 守卫 fail 零盲发` 改 `objs = 观察轮 obs 载体 → 无 match = 零决策零点击 round_success 终结交回(op-layer §1.1 :36)`。
7. **§2.1 文档面 §4 对照表末行**拆写为两行:

   ```
   | (无 match,局外,非动作) | — | — | 零决策零点击 round_success 终结交回(op-layer §1.1 :36);零点击零派发 |
   | (决策无有效输出/pick idx 越界,非动作) | — | — | 守卫 fail:词表外/None = round_fail(含原值)、idx 越界 = AssertionError;零点击零派发,交回外循环 |
   ```

8. **§2.1 文档面 §5 补行**拆为两行(新增一行 + 原行收窄改写,「与『入口锚 miss』行同落点类,补行保表完备」注保留):

   ```
   | 无 match(局外) | 零决策零点击 round_success 终结交回(op-layer §1.1 :36) | success 终结访问,交回外循环重进重读(先例 = cw_screen_encounter.py::CwScreenEncounter.act) |
   | 决策无有效输出(返回 None/词表外)/pick idx 越界 | 守卫 fail(op FAIL) | round_fail / 框架异常路径(留证截图 + node_max_retry_times=8 预算耗尽)交回外循环;连续 fail 由外环重派网兜底(flow/README §4) |
   ```

9. **§2.1 文档面 §8 首条①**:「①决策出口守卫:无策略器可问/返回 None/词表外 = 具名 round_fail 零盲发——原『策略异常 fallback 首卡』退役申报;」改「①决策出口守卫:match 缺席(局外)= 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36)——原『盲发首卡』退役申报;返回 None/词表外 = 具名 round_fail 零盲发——原『策略异常 fallback 首卡』退役申报;」(②③不变)
10. **§1 F-1「解决到哪」首句**:「决策段改三重守卫(无策略器可问/返回 None/词表外 = 具名 round_fail 零盲发;idx 越界 = 守卫断言 AssertionError;策略异常删宽 except 自然传播)」改「决策段改三重守卫(match 缺席 = 局外零决策零点击 round_success 终结交回[op-layer §1.1 :36];返回 None/词表外 = 具名 round_fail 零盲发;idx 越界 = 守卫断言 AssertionError;策略异常删宽 except 自然传播)」——其后子句不变。

**边界注(不改写)**:§2.1 第 11 条④ kernel 侧两处 docstring 目标文本「决策侧无兜底:决策无有效输出 = 守卫 fail 零盲发(申报见 screens/wish_trial.md §8)」按守卫②辖面(返回 None/词表外)窄读成立——无 match 臂非「决策无有效输出」形态(:36 = 局外终结交回),该句无需连带改写。

**依据**:重审报告 §2.5 Q2/增补 A;op-layer.md §1.1 :36 条款原文;先例代码锚 = `cw_screen_encounter.py::CwScreenEncounter.act`(:156-165)。
**验收锚**:落地批后 ①无 match 臂返回 round_success 且零点击零派发(测试锁见 §3-③);②本稿 §1/§2.1 全部站点无「无 match = fail」残留表述(grep「无 match」逐点对照本节清单 1-10)。

### 3.2 增补点②(:36)取舍 2 出口语义改写 + 族级判据提议作废 + §2.2 族级统一修法建议 bullet 拆写

1. **关键取舍 2**整条改写为:

   > 2. **无 match 支收编(:36 裁定出口语义)**:报告 F-1 三条路径均以「策略器被调用且非法」为前提,无 match 支未被单列;但该支与三路径同段同根(流程侧代行决策——纯 `FIRST_CARD` 常量盲发,无任何判据调用),修后若保留则同段并存「守卫零盲发」与「盲发首卡」自相矛盾。出口语义按 op-layer.md §1.1 :36(用户裁定 2026-09-22)裁定 = **零决策零点击 round_success 终结交回**(遭遇屏先例同款),非 fail——原「fail 零盲发」申报随 :36 改写;与 T-9 装备稿「保留无 match 支」的原对照(「判据直调支可豁免保留」)已被 :36 否定(kernel 判据直调支同样不可豁免,§3-②),族级口径归一。生产行为零变化(cw_loop 对局内 cw_match 恒在场),变化面仅局外直跑/MCP 手动语境。

2. **§2.2「跨稿分歧登记(候 T-37 裁决)」**首半改写为(「bug#1 缓解」标签登记半句保留原样):

   > - **跨稿分歧登记(:36 已裁定,候 T-37 仅裁实施)**:无 match 局外支的处置**已由 op-layer.md §1.1 :36(用户裁定 2026-09-22)裁定终结**——族级口径统一 = 无 match 一律零决策零点击 round_success 终结交回(遭遇屏先例同款),kernel 判据直调支同样不可豁免;原「建议族级判据 = 按支内是否含真实判据调用分流(判据直调支可豁免保留,纯常量盲发支一律守卫收编)」提议与 :36「不设任何兜底决策路径」正面相抵,**作废**(T-9/T-12/T-15 的「保留/候裁」立场一并失效);本稿立场 = 收编(出口语义按 :36 = round_success 终结交回,非 fail)。T-37 对账面收窄为**实施批合并**(§2.2 归口①),不再裁口径。

3. **§2.2「族级统一修法建议」bullet 拆写**(定点攻击 F-1;该 bullet 成文早于 :36 入正本,为 §3 既有条目唯一未覆盖的「输入侧 = fail」残留——与 §3.1 条目 1 守卫①改 round_success 同稿并存即正面矛盾,并使本节验收锚与 §3.4 登记行「族级口径统一 = round_success」相抵):bullet ①「决策无有效输出(输入侧:无策略器可问;返回侧:None/词表外)= 具名 round_fail 零盲发,消息含策略器原值 repr;」拆写为「①决策无有效输出(返回侧:None/词表外)= 具名 round_fail 零盲发,消息含策略器原值 repr;match 缺席(局外,即原句『输入侧:无策略器可问』所指)= 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,遭遇屏先例同款);」——②③分句与尾句「不建共享守卫函数……(同 T-9 判)」不变;特形出口句「屏幕特形出口以正本在册申报为准(如遭遇「空候选 = 零点击终结交回重读」op-layer §1.1 显名在册),无在册申报的屏一律走 fail 出口。」句尾补 :36 在册特形豁免半句,改「屏幕特形出口以正本在册申报为准(如遭遇「空候选 = 零点击终结交回重读」op-layer §1.1 显名在册),无在册申报的屏一律走 fail 出口(:36 在册特形除外——无 match(局外)= 零决策零点击 round_success 终结交回,不属 fail 一律句辖面)。」

**依据**:重审报告 §2.5 增补 B/Q3;op-layer.md §1.1 :36;定点攻击 F-1(respec-attack-C16.md,§2.2 族级 bullet 拆写)。
**验收锚**:本稿全文无「判据直调支可豁免」与「无 match = fail 零盲发」残留(含 §2.2 族级统一修法建议 bullet——条目 3 拆写后全稿残留清零);§2.2 归口③指针随 §2.2 改写自动指向新口径,无悬置。

### 3.3 增补点③(:36)测试锁第 4 条①拆分

**§2.1 测试锁第 4 条**改写为:

> 4. **补两锁**(①按 :36 增补拆分):①拆两锁——a 无 match(`cw_match=None`,观察链桩正常给 obs)→ `act` 返回 round_success(局外终结交回)、零派发零点击;b 策略返回 None/词表外对象 → round_fail 且零派发(派发桩零调用),b 内两支合并一锁或分案均可;②策略返回 `CwActionPickWishTrialParam(idx=3)`(槽常量现值 3)→ AssertionError 传播且零派发(不变)。

**依据**:重审报告 §2.5 增补 C;共享测试锁模板(无 match → round_success、零派发零点击)见 §3-⑤ 合流申报。
**验收锚**:两锁分别独立可跑,断言面互不合并;无 match 锁断言 round_success 而非仅「非 fail」。

### 3.4 T-37 登记行(原文)

```text
T-13 祈愿试炼:op-layer.md §1.1 :36(用户裁定 2026-09-22)落地增补——守卫① match 臂 round_fail→round_success 终结交回(先例 = cw_screen_encounter.py::CwScreenEncounter.act :156-165);原「族级判据提议:判据直调支可豁免保留」与 T-9/T-12/T-15「保留/候裁」立场随 :36 一并销项,族级口径统一 = 无 match 零决策零点击 round_success 终结交回,T-37 仅裁实施批合并;行为改写归 6 屏同形态族级实施批(T-9/T-11/T-12/T-13/T-14/T-15),与本稿 §2.2 归口①「族级合并实施批」裁决面合流,共享测试锁模板(无 match → round_success、零派发零点击);:34 不适用(objective 自由文本,无标准注册表,无登记面)。设计稿增补节 = changes/2026-09-22-screen-review/wish_trial.md §3(待用户裁决)。
```

### 3.5 合流申报(:36 行为改写 × 既有族级合并裁决面)

- 本增补点①的行为改写与 §2.2 归口①「伙伴/卜者两在途稿与本稿守卫形态是否并入一个族级实施批」裁决面天然合流:重审报告 §2.8 认定 6 屏(T-9 选择装备/T-11 选择伙伴/T-12 命运卜者/T-13 祈愿试炼/T-14 星徽秘典/T-15 专家邀请函)的 :36 行为改写为同一形态(else 支/守卫臂 → 零决策零点击 round_success 终结交回),建议一次族级批实施 + 共享测试锁模板(无 match → round_success、零派发零点击);T-10 为零行为批(申报级),不在该批。
- 若 T-37 裁族级合并:本稿即族级形态在祈愿试炼的实例,以族级批统一口径为准、不另立第二套(§2.2 归口①既判),本节改写文本随族级批一次落笔;若裁独立实施:本节随本稿单独落地,出口语义与改写文本不变(:36 已是正本裁定,不留候裁措辞——报告 §2.8 共性 1)。
- §2.2 归口④ op-layer.md §1.3 守卫清单登记义务不受本次重审影响,维持(报告 §1 卷首注)。

## 4. 坐标规范增补(op-layer :35/:48)

> **增补依据**:正本 `screens/op-layer.md` §1.1 两新条款(commit 9c8e9016b 入正本,用户裁定 2026-09-22)——**:35 选择坐标观察上报**(坐标单一真相源 = 观察上报,由决策侧半现算改为观察时上报;策略侧只输出下标,动作 op 按下标从 game state 获取坐标执行;归一化与坐标在同一次观察一并入容器;禁新增第二坐标源)、**:48 每个动作 op 单独一个文件**(`cw_overlay_pick_action.py` 单文件同居 12 个动作 op = 在册欠账,拆分逐批收敛,禁新增同类同居)。增补前置设计底册 = `.debug/progress/2026-09-22-cw-screen-review/reports/coord-norm-addenda-plan.md`(§1 = gs 坐标容器字段骨架一次定谳,本屏域 = `wish_trial_opts_xy`[A 类纯名单域伴随域];§2.1 = 本稿增补点清单;§3 = :48 拆文件批;§4 = 实施顺序,批1 字段骨架批先行 → 批2 逐屏收敛批)。
> **增补方式**:本稿 §0..§3 已收敛内容零直接改动;凡既有目标文本需连带改写处,逐字改写文本在本节给出(含落点节号),待用户裁决后随落地批一次落笔;本节自身为待裁决工件,裁决前不落任何代码与正本文档(迭代边界 = `changes/2026-09-22-screen-review/README.md`「只设计不落码」)。§0 状态行已就地更新。边界申报:§2.0/§2.5 的「零行为变更/其余文件零触碰」清单为 F-1/F-2/F-3 修法批辖面声明,:35 坐标增补 = 追加实施面,其行为变化全部由本节申报(与 §3 的 :34/:36 增补同判,§3 卷首「不推翻主体」口径延续)。

### 4.1 增补点①(:35)被推翻目标文本的改写声明(决策半坐标组装 / env.target)

**核心判据**::35 明文「坐标单一真相源 = 观察上报:由决策侧半现算改为观察时上报——策略侧只输出下标,动作 op 根据下标从 game state 获取坐标来执行」。本稿 §2.1 第 7/8 条目标文本的决策半坐标组装(`Point(self.CARD_XS[pick.idx], CwScreenWishTrial.CARD_Y)` 槽常量现算、经 `env.target` 传入;实查 `operations/cw_screen/cw_screen_wish_trial.py` :133-134/:156 现役同形)= :35 辖面,**被推翻**;坐标消费迁动作 op(§4.3),坐标生产迁观察上报(§4.2)。

**逐字改写文本(落点 → 目标)**:

1. **§2.1 第 7 条(「组装与日志」)条目标题与目标代码块**:标题「组装与日志」改「决策日志」;代码块——
现文:

   ```python
   target = Point(self.CARD_XS[pick.idx], CwScreenWishTrial.CARD_Y)
   pick_desc = f'卡{pick.idx + 1}({objs[pick.idx][:20] or "OCR空"})'
   log.info('[cw-wish] 祈愿决策: %s → 点 (%s,%s)', pick_desc, target.x, target.y)
   ```

   改文(:35 下决策半零坐标组装):

   ```python
   pick_desc = f'卡{pick.idx + 1}({objs[pick.idx][:20] or "OCR空"})'
   log.info('[cw-wish] 祈愿决策: %s → idx=%d', pick_desc, pick.idx)
   ```

   (`target = Point(...)` 行整行删除;日志行不再携带坐标——坐标由动作 op 自容器取后于动作侧申报,决策日志只述决策。)该条「`objs[pick.idx]` 取值安全 = 生产编排内的结构保证(两跳)……不新增防御」论证段**保留**(名字域消费不变,与坐标无关);「零判效零决策,纯日志描述」句保留。

2. **§2.1 第 8 条 env 构造句**:
现文:「`_env = OverlayPickExecEnv(op=self, idx=pick.idx, target=target)`;`action_op_for(pick, self.ctx, _env).execute()`(删 `CwActionPickWishTrialParam(idx=pick_idx)` 重建行)。」
改文:「`_env = OverlayPickExecEnv(op=self, idx=pick.idx)`(op-layer.md §1.1 :35 坐标单一真相源收敛,env 零 target——坐标由动作 op 自容器 `wish_trial_opts_xy` 取,见 §4.3);`action_op_for(pick, self.ctx, _env).execute()`(删 `CwActionPickWishTrialParam(idx=pick_idx)` 重建行)。」(「置 pending」句与其后「直发后:……上报 param 单一源 = 策略产值」段不变。)

3. **act 内派发括注第一句(现役代码注释站点,本稿 §2 未立条目,:35 连带新增改写;现文实查 = `cw_screen_wish_trial.py` :140-142)**:
现文:「(pick-op-unify 批:机械链迁入 ``CwActionPickWishTrialOp``,本 op 只决策;定位点决策半现算经 env 显式传入)」
改文:「(pick-op-unify 批:机械链迁入 ``CwActionPickWishTrialOp``,本 op 只决策;定位点 = 动作 op 自容器 `wish_trial_opts_xy` 按 idx 取,op-layer.md §1.1 :35)」
(批名「pick-op-unify 批」保留 = §1 F-3 既判「正本文档在册迭代名 = 持久索引」;§2.1 第 10 条对同注第二句「派发实例携真实选中下标……」的改写不变。)

4. **§2.2 归口②扩面(底册 §2.1-5)**:
现文:「②`operations/cw_op/cw_overlay_pick_action.py::OverlayPickExecEnv.idx` 字段注释「决策半现算快照(钳位后生效值)」陈旧措辞随族级批一次改净——单屏改会让共享 env 注释与未修屏临时不一致,本稿 §2.1 不动它,挂本裁决面;」
改文:「②共享 env 字段挂账扩为双面:`operations/cw_op/cw_overlay_pick_action.py::OverlayPickExecEnv.idx` 字段注释现值化(「决策半现算快照(钳位后生效值)」→「守卫后策略产值原值」)+ `target` 字段退役申报(过渡期注释加「退役中(:35 坐标单一真相源收敛,逐屏停喂)」,全族收敛完成后字段删除、挂收敛尾批;底册 §1.5)——单屏改会让共享 env 注释与未修屏临时不一致,本稿 §2.1 不动它们,挂本裁决面;」

5. **CARD_XS/CARD_Y 常量归宿改写(归宿申报,非逐字站点;底册 §2.1-6)**:§2.1 第 7 条(改写前)隐含「常量为决策半消费」——:35 后两常量**保留**,唯一**坐标**消费点迁**观察侧**(x = `CARD_XS` 桶锚、y = `CARD_Y`,观察期一次解析随 obs 上报,与 `_read_objectives` 同源);决策段零**坐标**消费(守卫③ `len(self.CARD_XS)` = 槽数值域取值,非坐标消费,维持不变)。

6. **测试锁第 2 条断言锚连带改写**:
现文:「**定位点断言换锚**:同锁 `(mod.CwScreenWishTrial.FIRST_CARD.x, .y)` → `(mod.CwScreenWishTrial.CARD_XS[0], mod.CwScreenWishTrial.CARD_Y)`——`FIRST_CARD` 随本修法删除;值等价(660/340),断言语义「定位点 = 首卡」不变。」
改文:「**定位点断言换锚(:35 二次改写)**:断言锚 = 容器值——点击桩捕获坐标 == `gs.wish_trial_opts_xy.value[0]`(观察上报写入值;生产形态 = `CARD_XS` 桶锚 x + `CARD_Y` 卡身 y,值仍等价 660/340);断言语义改「定位点 = 观察上报坐标(动作 op 容器取点)」,不再锚类常量现算——类常量自 :35 收敛后非决策半消费面,锚常量即残留被退役形态。」

7. **`screens/wish_trial.md` as-built 目标文本(落点 = §2.1「文档面」节;底册 §2.1-4)**:
   a. **§4 伪码行**:
现文(§2.1 文档面 §4 伪码行;as-built 现行 :31 同形):「target = (槽 x 常量[idx], 卡身 y 常量 340) → 置确认 pending → 直发 pick 派发」
改文:「坐标 = 容器 wish_trial_opts_xy[pick.idx](动作 op 内取;缺席 = 守卫断言,op-layer §1.1 :35)→ 置确认 pending → 直发 pick 派发」
   b. **§4 对照表「发出方式」列**(§2.1 文档面对照表改写句内括注):
现文:「(决策半组装 `OverlayPickExecEnv`:定位点;两守卫派发前,流程侧零值域改写)」
改文:「(`OverlayPickExecEnv`:idx;坐标由动作 op 自容器取[op-layer §1.1 :35];两守卫派发前,流程侧零值域改写)」
   c. **§2 画面形态声明补坐标域一句**(落点 = §2.1 文档面 §2 决策子句改写文本之尾,§3.1-5 :36 连带改写后的句尾追加):「选卡坐标 = 容器 `wish_trial_opts_xy`(选项坐标伴随域,与候选名域 `wish_trial_opts` 同序等长):观察上报与名字域同门一并入容器(op-layer.md §1.1 :35,坐标单一真相源 = 观察上报),动作 op 按 idx 自容器取点,缺席/越界 = 守卫断言;确认钮等静态控件锚 = screen_info area 现取不变(底册 §1.6)。」
   d. **§4 交互陷阱句尾半句连带改写**(本稿 §2.1 既判「交互陷阱句(ESC 不关/卡身挂账)不动」,:35 下「卡身挂账……现走槽常量」半边失真,连带改写;ESC 半边不动。现文 as-built §4 实查 :40):「卡身建档(卡位坐标)挂账实机批,现走槽常量。」改「卡位不建 screen_info area(:35 辖域边界既判 = 选项坐标入坐标域,底册 §1.6);选卡坐标 = 观察上报容器 `wish_trial_opts_xy`(op-layer.md §1.1 :35)。」(objective 读区 area 化为另一在册欠账,不涉本句、维持挂账。)
   e. **§3 观察面 payload 字段集与 report 句(F-3;落点 = as-built 现行 :16)**:现文「观察 payload = `CwScreenWishTrialObs`(`on_screen`/`options`/`screen`,住 `kernel/cw_screen_report/wish_trial.py`);report = `report_screen_wish_trial_obs` 候选写容器 `wish_trial_opts` 槽(空桶照写;match/gs 缺席的局外兜底路径跳过)。」改「观察 payload = `CwScreenWishTrialObs`(`on_screen`/`options`/`option_points`/`screen`,住 `kernel/cw_screen_report/wish_trial.py`);report = `report_screen_wish_trial_obs` 候选与槽位坐标一并写 `wish_trial_opts` / `wish_trial_opts_xy`(同门同写,op-layer.md §1.1 :35;空桶照写;match/gs 缺席的局外兜底路径跳过)。」——obs 扩 `option_points` + report 同门双写落地后原句失真(缺坐标域字段与双写申报);§3 观察面 = 坐标快照申报的天然宿主节。
   f. **§6 候选观察句(F-3;落点 = as-built 现行 :54)**:现文「- 候选观察:`report_screen_wish_trial_obs` 候选写容器 `wish_trial_opts` 槽(空桶照写)。」改「- 候选观察:`report_screen_wish_trial_obs` 候选与槽位坐标一并写 `wish_trial_opts` / `wish_trial_opts_xy`(同门同写,op-layer.md §1.1 :35;空桶照写)。」

8. **§2.5 实施文件面追加(落点 = §2.5 末尾追加,不改既有行)**::35/:48 增补新增实施面——行为变更(坐标收敛批)= `operations/cw_screen/cw_screen_wish_trial.py`(观察 node 组装坐标快照 + report 同门双写 + act 删坐标组装/env 零 target/派发括注改写)+ 动作 op 宿主 `operations/cw_op/cw_pick_wish_trial_action.py`(:48 拆分批后形态,动作 op 自容器取坐标;env import 改 `cw_overlay_pick_env.py`,底册 §3.1)+ `kernel/cw_screen_report/wish_trial.py`(obs 扩 `option_points` + report 双写 + docstring 半句)+ `kernel/cw_game_state.py`(`wish_trial_opts_xy` 域定义,归批1 字段骨架批,§4.6)+ 测试双锁(§4.5)。宿主文件名 = :48 拆分批(底册 §3,先行清场)落地后形态;若坐标批先于拆分批施工(不建议,底册 §4 顺序 = 拆分先行),落点暂为 `cw_overlay_pick_action.py` 原文件,拆分批再随迁。

### 4.2 增补点②(:35)观察上报增补(obs 扩坐标 + report 同门双写,写端唯一)

- **obs 扩坐标**:`CwScreenWishTrialObs`(`kernel/cw_screen_report/wish_trial.py`)扩 `option_points: list[tuple[int, int]]`(命名与 A 类伴随域族同形)——与 `options` **同序等长**;x = `CARD_XS` 桶锚、y = `CARD_Y`,观察期一次解析(**取值时机 = 观察期快照**,禁执行期现读现算,底册 §1.2);值形状 = 平铺元组(1080p 游戏空间,遥测 JSON 序列化安全形,底册 §1.2)。
- **report 同门双写(写端唯一)**:`report_screen_wish_trial_obs` **同一次调用、同一写门**一并写 `wish_trial_opts` + `wish_trial_opts_xy`——本屏无观察标准化门(:34 本屏不适用,§3 卷首增补依据:观察面 = objective 自由文本,无标准注册表在册),双写**无条件同门**;写端构造守卫保证 `len(option_points) == len(options)` **等长断言**(不等长 = 观察 bug 响亮暴露,底册 §1.3);失读/离屏语义与名字域同格(Field 机制原样:已有正式值失读 = carried,从未读过 = None,底册 §1.4-W1)。**禁新增第二坐标源**:除本写门外任何写端不得写坐标域;sim 无画面识别不建模、值恒未观察 None(底册 §1.4-W4)。
- **kernel docstring 连带(底册 §2.1-3;落点 = §2.1 第 11 条④目标文本再追加)**:`report_screen_wish_trial_obs` 函数 docstring 现文「祈愿试炼屏观察上报:objective 写 ``wish_trial_opts``。」(实查 :38)改「祈愿试炼屏观察上报:objective 与槽位坐标一并写 ``wish_trial_opts`` / ``wish_trial_opts_xy``(同门同写,op-layer.md §1.1 :35)。」(§2.1-11④ 已定的「决策侧 fallback 首卡」改写与 §3.1 边界注定格不受影响;obs 类 docstring 索引定义注随 `option_points` 扩字段同步补索引声明——「``option_points`` = 各卡槽位坐标,与 ``options`` 同序等长」,坐标收敛批施工。)
- **画面 op 模块 docstring 连带(F-6;T-13 半边,与上行 kernel report 函数 docstring 同判句族)**:`cw_screen_wish_trial.py` 模块 docstring 观察链句现文(实查 :17)「→ ``report_screen_wish_trial_obs`` 落容器 ``wish_trial_opts``(无空门,空桶照写)」改「→ ``report_screen_wish_trial_obs`` 落容器 ``wish_trial_opts`` / ``wish_trial_opts_xy``(无空门,空桶照写,同门双写,op-layer.md §1.1 :35)」——双写落地后原句描述不全,同判不同待遇随本条补齐,坐标收敛批施工。
- **伴随域离屏清值机制载体登记(A-3 同族对账,coord-attack-T15-16-17.md 同款;T-37 对账)**:「失读/离屏语义与名字域同格」的机制载体 = 名字域 `wish_trial_opts` 的离屏清值由 `_PAYLOAD_DOMAINS` 在册承载(`kernel/cw_game_state.py` 画面附加域映射 + 路由清点 `cw_loop.py::_route_clear_stale_payloads` 逐域 `leave_screen` 置 None;`leave_screen` 硬门「非画面附加域禁离屏清值」)——坐标伴随域若不入该映射,离屏时名字域置 None、坐标域跨屏携带陈值,「同格」落不了地。**批1 字段骨架批随域登记**:`_PAYLOAD_DOMAINS['wish_trial_opts_xy'] = ('货币战争-祈愿试炼', True)`(与名字域同属屏、同 route_clearable);批1 落点面见 §4.6。

### 4.3 增补点③(:35)动作 op 取坐标改写(env.target → gs 坐标域[idx])

- **改写**:`CwActionPickWishTrialOp.run` 现消费 `env.target`(`mouse_move`/`click` 形态;本稿 §2.1-8 经 §4.1-2 改写后 env 零 target)→ :35 终态:`gs = game_state_from_ctx(self.ctx)` → `pts = gs.wish_trial_opts_xy.value` → 守卫断言(`pts is not None` 且 `0 <= action.idx < len(pts)`;缺席(None)/越界 = **AssertionError 响亮暴露**)→ `mouse_move`/`click(pts[action.idx])`;上报调用零改动(动作 op 自上报 `report_action_pick_wish_trial_param` 按 idx 写效果逻辑态,与坐标无关 = 底册 §1.4-W3)。
- **禁回退申报(硬约束)**:禁回退 `env.target`、禁 screen_info 二次 `area_center` 现取——任一回退 = **第二坐标源**,:35 明文禁止(底册 §1.4-W2);gs 缺席(局外)= :36 已裁 act 局外门 round_success 终结交回(§3.1),动作 op 不会在局外被派发;直构动作 op 的测试语境 = 显式注入坐标域,缺席即炸 = 防线非缺陷(底册 §1.4-W2)。
- **宿主文件(:48)**:随拆分批(底册 §3,批0 先行)迁 `operations/cw_op/cw_pick_wish_trial_action.py`,env 自 `cw_overlay_pick_env.py` import;本稿坐标改造落该新文件(§4.1-8 批序注)。
- **测试锁连带**:§2.1 测试锁第 2 条按 §4.1-6 换锚;直构动作 op 的机械链锁(`test_cw_unified_action_4.py` 祈愿行)= 「零改动」既判(§2.1 测试锁 5)随坐标源换容器**改为补显式注入坐标域**(import 面随 :48 拆分批一并改,底册 §3.2-3;缺席即炸 = 防线非缺陷)。

### 4.4 增补点④(:35)§2.4 F-3 docstring 目标文本纠正(欠账形态写成终态)

**纠正判据**:§2.4 目标行把 :35 下的**欠账/过渡形态**(决策半按槽 x/y 实测常量现算、经 `env.target` 传入)申报为**终态**——:35 入正本(commit 9c8e9016b)晚于本稿收敛,时序错位所致;:35 已裁定坐标单一真相源 = 观察上报,该形态属被收敛面,不得为目标文本。

**逐字改写文本(落点 = §2.4 目标行)**:
现文:「点试炼卡身选中(bug#1 缓解,选中点 = 画面 op 决策半按槽 x/y 实测常量现算、经 `env.target` 传入——卡位未 area 化,坐标单一真相源缺口挂账实机批,申报同 `cw_screen_wish_trial.py` 类头与 screens/wish_trial.md §4)→ 选中动画固定等待 → ……」
改文:「点试炼卡身选中(bug#1 缓解,选中点 = 动作 op 自容器 `wish_trial_opts_xy` 按 `param.idx` 取——op-layer.md §1.1 :35,坐标单一真相源 = 观察上报;观察上报与名字域同门一并入容器,等长同进退)→ 选中动画固定等待 → ……」

**连带申报**:
1. **§2.4 关键取舍连带改写**(其「欠账如实保留」判据被 :35 反转,不改则与上文改文自相矛盾):
现文:「**关键取舍**:只改失实子句、不扩面;「卡位未 area 化」如实保留为挂账申报而非删掉——防「改注释 = 消欠账」假闭环(同 T-9 F-3 取舍);area 化消费改造 = 行为变更,归在册实机批。」
改文:「**关键取舍(:35 增补后)**:只改失实子句、不扩面;「坐标单一真相源缺口」欠账由 :35 坐标收敛批**实销**(销账载体 = 观察上报 + 容器 `wish_trial_opts_xy` + 动作 op 取点三件同屏批落地,§4.5 验收锚),目标文本不再申报该欠账;「卡位不建 area」= :35 辖域边界既判(选项坐标入坐标域,底册 §1.6),非缺口;objective 读区 area 化为另一在册欠账,维持挂账不动。」
2. §2.4 依据段「申报同 `cw_screen_wish_trial.py` 类头与 screens/wish_trial.md §4」对齐声明随整句改写作废;类头坐标句补逐字改文(实查 `cw_screen_wish_trial.py` :48-49,系 :35 直接受影响站点——其「挂账」申报被上文关键取舍改文自述「实销」,不改即注释申报失实;F-5):
现文:「⚠️ 待实机核(坐标单一源清点项):以下卡位为实测字面量,未 area 化
(确认按钮已 area 化;卡身建档挂账实机批——本批实机纪律不可测)。」
改文:「卡位不建 screen_info area(:35 辖域边界既判,底册 §1.6);选卡坐标 = 观察上报容器 `wish_trial_opts_xy`(op-layer.md §1.1 :35),随 obs 观察期一次解析。」
(as-built §4 半边连带由 §4.1-7 承载;原指针「按 §4.1-3/§4.1-7」中 §4.1-3 落点 = act 内派发括注、非类头,类头不再引 §4.1-3。)
3. 宿主文件路径随 :48 拆分改 `operations/cw_op/cw_pick_wish_trial_action.py`(现文宿主 `cw_overlay_pick_action.py` = 拆分批前形态)。

### 4.5 增补点⑤验收锚(含过渡期铁律)

**验收锚**(坐标收敛批落地批后;底册 §2.1):
1. **report 双写锁**:`report_screen_wish_trial_obs` 同一次调用同门写 `wish_trial_opts` + `wish_trial_opts_xy`(无条件同门);等长断言不等即炸。(原「任一候选转换失败 → 双零写」半句删——本屏无 :34 转换门、转换路径不可达,该测试不可构造,违背验收锚可机械执行标准;门句按屏特化见 §4.2,同门双写 + 等长断言两判据保留,F-4。)
2. **动作 op 取坐标锁**:坐标域 None / `action.idx` 越界 → AssertionError 且零点击零派发副作用;注入合法坐标域 → 点击坐标 == 容器值。
3. **grep 零残留**:`cw_screen_wish_trial.py` 决策段无 `Point(` 组装、env 构造无 `target=`;act 内无「定位点决策半现算经 env」字样(§4.1-3 改写后)。
4. **全绿门槛** = 祈愿臂既有锁(§2.1 测试锁清单,锁 2 按 §4.1-6 换锚、机械链锁按 §4.3 注入)+ 本节双锁。

**过渡期铁律**(底册 §1.7 / §4 衔接要点 3,批间与屏间有效):
- **禁新增第二坐标源**:批1(字段骨架批)落地到本屏收敛批完成之间,已定义字段与未收敛屏并存 = 合法过渡(现役坐标链未断);过渡期内任何新屏/新 op **不得再走「决策半现算经 env.target」**,新写法直接按底册 §1 骨架。
- **禁半截状态**:逐屏一次到位——观察上报 + act 删坐标现算(env 零 target)+ 动作 op 自容器取坐标,三件**同一屏批**做完;只加观察上报不删现算 = 双坐标源并存,违「禁新增第二坐标源」,为硬验收判据。
- **同屏合并施工建议**::34/:36(§3)与 :35(本节)三面全在 observe+act 两段,建议同屏批合并施工(底册 §4 批2 注);逐屏派发顺序建议 = box_pick → wish_trial → star_tome → expert_invite(底册 §4)。

### 4.6 增补点⑥fields.md 增补条目指针(引用不重复设计)

- **本域字段骨架(一次定谳,引用底册 §1.2/§1.3)**:`wish_trial_opts_xy` = A 类纯名单域(`Field[list[str]]` 名字域 `wish_trial_opts`)的坐标伴随域,形态 `Field[list[tuple[int, int]] | None]`,与名字域**同序等长**;键 = idx(0 起,左→右画面物理序,与策略器输出下标、`CwActionPickWishTrialParam.idx` **同一坐标系零换算**);值 = `tuple[int, int]`(x, y,1080p 游戏空间,平铺元组 JSON 序列化安全形);等长不变量由写端构造守卫保证,读端不做长度调和。
- **fields.md 增补条目目标文本草案 = 底册 §1.8(a)(b)**(§3.4 头部引注段追加一句 + 新增小节 §3.4.5a「选项坐标域」,字段登记行含 `wish_trial_opts_xy`)——本稿**引用不重复设计**,条目全文以底册 §1.8 为单一源。
- **落点 = 批1 字段骨架批**(底册 §4):`kernel/cw_game_state.py` 域定义 + `DEFAULT_GS_SCHEMA` 新域键 `wish_trial_opts_xy: 1`(version 1)+ `_PAYLOAD_DOMAINS` 新键登记(`'wish_trial_opts_xy': ('货币战争-祈愿试炼', True)`,伴随域离屏清值与名字域同格的机制载体,§4.2 A-3 申报,T-37 全域对账)+ fields.md 目标文本落笔 + schema 对齐锁(对齐锁反向扫描面不受 `_opts_xy` 尾影响 = 底册 §1.8(b) 同判,正向清单扩展随批1 申报)+ 快速集;批1 先行于本屏收敛批(批2),后续屏批不碰容器(底册 §4 衔接要点 1)。
