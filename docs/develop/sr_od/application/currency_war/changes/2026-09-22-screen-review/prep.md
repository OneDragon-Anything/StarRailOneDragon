# T-1 备战(画面+动作面全集) 修法设计(prep)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:**触顶定稿随批落地**(对抗轨迹:r1 未收敛 13 条→修订→r2 未收敛 6 条→修订→r3 未收敛 5 条→修订→r4 触 4 轮上限;**残留随批清偿**:终轮 3 条按末轮攻击报告(T-1-attack-r4.md)处方落稿——R4-1 跨稿承接声明落 §2.2-7(R11h 归口已裁定:action-logic-state.md 认领归 T-1)、R4-2 哨兵面清单漏项落 §2.5.5-4⑦、R4-3 T-6 承接项落 §2.4-5,均为一句话级文本修正,不影响修法主体)
- 审查输入:`.debug/progress/2026-09-22-cw-screen-review/reports/` 下 `T-1-r1.md`(合并索引)/`T-1a-r1.md`(面a F-1..F-5)/`T-1b-r1.md`(面b F-1..F-12)/`T-1-orchestrator-notes.md`(P-1/P-2)
- 真值基线:本稿全部「现状」陈述以审查时点工作树代码为准(涉事符号均已逐点开验);落地时若代码已再变,以落地时点代码重新对账后再动笔。符号锚 = `文件::符号名`,行号仅作本稿定位辅助。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根)
- 修法性质:以文档语义更新与注释清理为主(含 docs 正本面对账点位,§2.5.6),**零行为变化**;2 条(面b F-1/F-2,主题A)涉及动作 op 内只读/等待形态的微差清除,行为差异逐条申报于 §2.1;2 个文件退役删除(P-1/P-2)与 1 个 helper 归一裁决(§2.5.5-1)。零策略判据面改动、零容器写语义改动

## 1. 问题与动机

### 1.0 发现覆盖总表(逐条回应索引)

| 发现 | 主题 | 修法节 |
|---|---|---|
| 面a F-1(统一验证幻影步骤) | F | §2.6 |
| 面a F-2(PrepObservation 契约措辞) | G | §2.7-1 |
| 面a F-3(帧代次槽名滞后) | G | §2.7-2 |
| 面a F-4(段迹锁失效指针) | G | §2.7-3 |
| 面a F-5(裁定日期/事故史进正文) | G | §2.7-4 |
| 面b F-1(DeployMove 拖后 overlay 快查) | A | §2.1 |
| 面b F-2(WearEquip 拖前稳帧轮询) | A | §2.1 |
| 面b F-3(WearEquip 零写文档不符) | B | §2.2 |
| 面b F-4(tools.md 专篇整体过时) | B | §2.2 |
| 面b F-5(README §6 漏 OpenBookcard) | C | §2.3 |
| 面b F-6(logic-updates README 索引面过时) | D | §2.4 |
| 面b F-7(deploy.md 符号归属错误) | E | §2.5.1 |
| 面b F-8(两篇引用退役执行载体) | E | §2.5.2 |
| 面b F-9(注释散布退役 CwScreenDeploy 引用) | E | §2.5.3 |
| 面b F-10(cw_vocab.py HoldFrame 残留) | G | §2.7-5 |
| 面b F-11(三 slot 字段缺索引定义注释) | G | §2.7-6 |
| 面b F-12(「统一验证」残留措辞) | F | §2.6 |
| P-1(CwOpSellOffTarget 死文件) | E | §2.5.4 |
| P-2(CwOpEquipAll 半死文件) | E | §2.5.5 |

### 1.1 主题A:动作 op 读屏越禁令且欠账未登记(面b F-1/F-2,中×2)

- **现状症状**:两处动作 op 执行路径读屏,落 `flow/action_ops.md` §1 增补 3 禁令射程(「动作 op 无论执行前后均不做观察识别;唯一允许的查找 = 点击/拖拽目标定位」),而 §1 增补 3 欠账清单仅列 buy_card/refresh_shop/start_battle 三处,未收此两处——正本间不一致 + 欠账登记缺失。①`operations/cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp.run`(L90-95):拖拽发出后 `screenshot()` + `round_by_find_area` 快查盛会之星 overlay,命中只进 log/detail,不改控制流;`action_ops.md` §4.2 DeployMove 行与 `logic-updates/deploy-move.md` §3.7 把它作为现役形态在册。②`operations/cw_op/cw_wear_equip_action.py::CwActionWearEquipOp.run`(L74)拖拽前调 `prep_actions.py::PrepActionExecutor._wait_stable_frame`(L703-718):截两帧算全图像素差的 `while` 轮询(预算 1.2s),既非固定等待亦非目标定位;`wear-equip.md` §3.1 有「输入条件化等待,非判效」as-built 声明,但规范欠账面未收。
- **根因归层**(根源两问):根在**约定层**——增补 3 是后立规范,清查欠账时只盘点了商店域与 start_battle,备战域动作面漏盘;修的是根(把备战域两处欠账清偿到零,增补 3 违例清单恢复完整自洽),不是症状(不新增豁免条款、不把快查/轮询改名保留)。
- **解决到哪**:两处清除到增补 3 全合规(§2.1),行为微差显式申报。
- **明确不解决**:商店域两欠账(buy_card 买前裁片/refresh_shop 三读,在册、清法 = 商店迭代)与 start_battle 出战后单帧弹窗识别(在册、清法候批);动作点击链可靠性本体(落空治理链不变)。

### 1.2 主题B:零写→容器直写升格的文档漂移(面b F-3/F-4,中×2)

- **现状症状**:WearEquip 与工具原子七类的上报已从 `zero_writes.py` 零写占位升格为容器直写(代码真值:`kernel/cw_action_report/wear_equip.py::report_action_wear_equip_param` L43-47 容器 `gs.equips` 写 owned−1;`kernel/cw_action_report/tool_use.py` 七函数 `write_logic`/`write_logic_rand` 采样链 + `gain_character` 获得链;`zero_writes.py` 头注明示工具七类已迁出),但**五处正本**仍按旧零写形态描述:`logic-updates/wear-equip.md` §2/§7、`game_state/fields.md` 备战动作逻辑态写口覆盖面申报段(「零写族……= OpenBox/WearEquip/工具原子七类集中在 `zero_writes.py`」,L1473-1476)、`screens/prep.md` §4 零写族行、`logic-updates/README.md` WearEquip 行与工具七行;`logic-updates/tools.md` 全篇(§2 域集/§3 转移规则/§6 符号锚)仍写零写族 + 已退役符号 `apply_tool_execution_write`(全仓零符号);`action_ops.md` §4.2 WearEquip 行把容器 owned−1 腿误归 tracked 账。另 `wear-equip.md`/`tools.md` §1 均申报「不在 `cw_vocab.py::Action` 联合内」——代码事实 = `kernel/cw_vocab.py` CwAction union 与 `CW_ACTION_TYPES` 均在册。
- **根因归层**:根在**流程层(批收尾义务)**——升格批只改了代码与 `action_ops.md` §4.2 工具段,逐动作正本篇、容器域申报正本(fields.md)与索引面不在该批文件清单;语义层表现为「文档申报的写语义与代码行为不符」,是上报函数族作为动作语义单一源(logic-updates README 总则 1)被文档面背叛。修文档到代码,不引第二源。机制性防线的登记见 §2.9(候批)。
- **解决到哪**:五处正本 + tools.md 专篇按现役写语义改写(§2.2);退役符号 `apply_tool_execution_write` 从符号锚剔除。
- **明确不解决**:`EQUIP_WRITE_SIDES`/`EQUIP_REWRITE_DECLARATIONS` 登记面与效果桥(`cw_affix_effects.py`/`cw_effect_inventory.py`,在役,tools.md 保留为效果写端桥引用);pick 族上报形态现役 = 全族即时单相(`action_ops.md` §4.5 现文已申报清偿,索引面按两档如实落行,§2.4-2)。

### 1.3 主题C:终结语义总表漏行(面b F-5,中)

- **现状症状**:`screens/README.md` §6 终结总表无 OpenBookcard 行;代码真值 = `operations/cw_op/cw_open_bookcard_action.py` L40/L44 `terminal = True`/`terminal_wait = 1.8`,`screens/README.md` §5.5 与 `screens/prep.md` §4/§5 均已按「备战访问终结」记载。滞后记载点共**三处**:①§6 总表漏行;②`action_ops.md` §4.2 OpenBookcard 行标「(非终结)」;③`screens/README.md` §4 动作词表表「领取类」行把 `CwActionOpenBookcardParam` 与 CollectOre/OpenTome 并行列、终结性列标「非终结」——与同文件 §5.5/§6 的现役申报并存矛盾。
- **根因归层**:**表示层**——OpenBookcard 终结化(开卡时机归策略器批)改了类属性,总表/§4.2 行/§4 词表表三处记载面未随更;修表示(补行/改行)即治根,总表 = 终结集完备清单的唯一读面(op-layer.md §1.4)。
- **解决到哪**:三处同步(§2.3)。
- **明确不解决**:终结判定机制本体(注册表类属性为判定现值,消费点经 `action_op_class_for`,行为无损,零改动)。

### 1.4 主题D:logic-updates README 索引面过时 + 跨稿联动(面b F-6,中)

- **现状症状**:`game_state/logic-updates/README.md` 自述基准 = `operations/cw_op/cw_action_registry.py`,但写「注册表 26 行 / 20 op 类」「事件线 pick 族(5 行)」并把 SwapDeploy 列为「`CW_ACTION_TYPES` 白名单但无注册行」;代码真值 = 注册表 **36 行 / 28 op 类**(`cw_action_registry.py::_REGISTRY` 逐行清点,当前快照),pick 族 **13 行全在册**(L179-191),Obs 行在册(L175),LevelUpShop 显式独立行(L154);`CW_ACTION_TYPES` 白名单元组(`cw_vocab.py` L1021-1037)**不含** `CwActionSwapDeployParam`(该类仅在 CwAction union L1011 在册)——README「词表在册、不经注册表分发」节的 SwapDeploy bullet 现状即自相矛盾。同根顺带:①`prep-executor-actions.md` §4「全集映射(26 注册行)」同款;②`action_ops.md` §4.2 标题「备战族(9 行)」与同节「LevelUpShop 显式独立行」计数口径矛盾(物理行 = 10);③`action_ops.md` §3 偏离清单「注册表 27 行 / 20 个 op 类」与同文件 §4 覆盖声明「36 行」文内矛盾。
- **根因归层**:**表示层**——pick-op-unify 批/投资两屏拆类/Obs 行/LevelUpShop 行/pick-planner-equip 即时上报批多次变更,索引面未随更;「handler 自管不经注册表」句与注册表现状直接矛盾,会误导「新增 pick 动作要不要注册」的实现决策。修索引到代码现值,且计数陈述改「以代码现值为准」口径防再漂移(§2.4-1)。
- **解决到哪**:README 索引面整段重建(§2.4),含跨稿承接声明(T-2/T-4/T-5)与缺档显式申报。
- **明确不解决**:8 个 pick 行 + Obs 行的**专篇补齐**(内容创作批量外溢,登记于 §2.4-1);真实在册欠账面 = `action_ops.md` §2.3(L59)pick 族旁路的「落地与否由下一轮重入裁决」写法(辖未迁移屏,与注册行无一一对应,不在本表逐行申报)。

### 1.5 主题E:退役残留清理包(面b F-7/F-8/F-9 + P-1/P-2,中×3 低×1 + 疑点×2)

- **现状症状**:部署机退役(`CwScreenDeploy`,op-layer.md §3 退役行 + screens/README.md §4)与组合壳退役的收尾清查不彻底,散布六个面:
  1. **F-7** `screens/deploy.md` §1 环节表把「部署选人」归 `kernel/cw_deploy_logic.py::select_deployments_reasoned`——该符号实定义于 `strategies/impl/mandate_v1/deploy_plan.py`(L335;kernel 侧 `recipe_floor_holds`/`select_swap_plan`/`residual_fill_plan` 三谓词确在 `cw_deploy_logic.py`),与 `flow/action_exec.md` §5 的分层表述(选人/排路由/槽位 = 策略层;kernel = 围栏常量+共用判定谓词)冲突。
  2. **F-8** `logic-updates/sell-deployed.md` §1/§6 执行载体指向已删除文件 `cw_screen_deploy.py::_sell_offtarget_deployed`(现役 = `CwActionSellDeployedOp` 注册行 + mandate m1p 换血发射臂);`prep-executor-actions.md` §3「备战域部署换位经部署机拖拽承载」同款。
  3. **F-9** 多处代码注释以现在时引用已退役符号(消费面/写入端/时序叙事),逐点清单见 §2.5.3(含 docs 正本面,§2.5.6)。
  4. **P-1** `operations/cw_op/cw_op_sell_off_target.py::CwOpSellOffTarget` 全仓零引用死文件(文件头有【退役·禁接旧码】申报,但申报的承接者 `deploy_bench._sell_offtarget_deployed` 本身也已退役——承接链断裂,op-layer §3 36 op 总表外)。
  5. **P-2** `operations/cw_op/cw_op_equip_all.py::CwOpEquipAll` 类体零构造调用;唯一跨文件消费 = `prep_actions.py::_owned_grid_locate` 只 import 模块级 helper `get_equip_templates_cached`;`kernel/cw_equip_env.py` L155 写入端注释仍指 `CwOpEquipAll.STATUS_PLAN_STALE`;src/docs/tools 多处历史叙述性引用待逐点处置(§2.5.3/§2.5.5/§2.5.6)。
- **根因归层**:根在**流程层(退役批收尾义务清单缺「退役符号引用面全量对账」这道门)**——本稿五主题(B/C/D/E/F)同此根构;语义层症状 = 死代码 + 现在时死句误导排障。本批修法 = 一次性清偿本域残留 + 可满足的机械验证门(§2.8);**该收尾义务的长效载体(正本条款)本稿不落,登记机制防线候批**(§2.9,与 T-3 稿同款登记面合并,交用户裁决)。
- **解决到哪**:F-7 归属修正、F-8 执行载体改现役、F-9 注释逐点改写、P-1 文件删除、P-2 文件退役 + helper 归一 + 哨兵面退役裁定(§2.5)。
- **明确不解决**:清存量 off-target 能力面的策略级重建(现役 m1p 换血卖出臂与 SwapDeploy 能力面已覆盖主要形态,重接评估归策略迭代);零穿戴哨兵重挂(§2.5.5 显式裁定退役,重挂归观测迭代);mandate 判据面正确性(T-1b §4 无法核对面);测试锁断言内容全量开验(T-1b §4)。

### 1.6 主题F:「统一验证」判效时代残留措辞(面a F-1 + 面b F-12,同根;中+低)

- **现状症状**:`screens/prep.md` §4 执行要点行、`screens/README.md` §5.3 CollectOre 行与 `docs/game/currency_war/research/screen_flow_timing.md` L82(时序 #16 行)三处均写「**统一验证**」(前两处 = 批式一次全点 → 等 2s → 统一验证;#16 行另并列已退役的逐矿「点击+1.2s 验证」);代码真值 = `operations/cw_op/cw_collect_ore_action.py` 零验证(点击列 + park + `time.sleep(2.0)` + op 自上报交回,src 内「统一验证」零命中);「验证」本身属 `action_ops.md` §1 明文禁止面,`action_ops.md` §4.2 CollectOre 行(「固定等待 2s 等飞行动画;席满未点开的晶矿由下一帧观察回补」)已是准确表述。
- **根因归层**:**表示层**——验证废除批清了代码与 action_ops,画面篇两处措辞未随更;残留词与「禁验证」契约字面冲突,误导维护者以为存在验证段。修措辞到 `action_ops.md` §4.2 口径即治根。
- **解决到哪**:三处措辞改写(§2.6),docs 全树验证门兜底(§2.8 门1)。
- **明确不解决**:CollectOre 执行本体(批式点击/固定等待/席满回补语义零改动)。

### 1.7 主题G:低危单点面(面a F-2/F-3/F-4/F-5 + 面b F-10/F-11,低×6)

- **面a F-2**:`kernel/cw_prep_actions.py::PrepObservation` docstring 与 `flow/projection_contract.md` §1/§4.4 申报「不承载占用/状态面」,而 `operations/cw_screen/cw_screen_prep.py::_observe`(L218-226)在同帧以动态属性挂 `front_occupied`/`back_occupied` 对拍轻字段(L442 消费,方法内即弃)——契约**行为面**未破(不进 gs/session/report),但字面与运行时形态不一致,且与 docstring 的删除申报相抵。
- **面a F-3**:`flow/README.md` §2.2 非契约成员段仍写黑板时代槽名 `session.prep_frame_class`/`shop_frame_class`;现役宿主 = GameState 非 Field 双槽 `gs.frame_class_prep`/`gs.frame_class_shop`(`kernel/cw_game_state.py` L2151-2152;写点 = `cw_screen_prep.py` L633/L760、`cw_screen_buy_cards.py` L798;消费 = `strategies/impl/flow.py` L373-395 读后即清)。同族残留两处:`flow/session.md` L57/L59 现态申报「两帧代次标注槽留 session」(与代码相反——`cw_strategy_session.py` L143-148 退役注:session 槽已退役迁 gs 双槽);`screens/shop.md` L25 `shop_frame_class` 裸引。
- **面a F-4**:`screens/prep.md` §9 测试锁句含「生命周期段迹锁」——段迹机制及其锁已整体退役(op-layer.md §4「任何一侧的重新出现即架构回潮」);句内点名的 `test_cw_deploy_cap_gate.py`/`test_cw_unified_action_2a.py` 实查在场,`_write_prep_node_chain` 有专锁 `test_cw_prep_node_chain.py`。
- **面a F-5**:`screens/prep.md` §2/§3/§4/§5/§8 多处携带裁定日期与事故叙述,违 `screens/README.md` §2 纪律行「as-built 无状态(事故史/裁定日期不进正文)」;内容与代码行为一致,纯纪律瑕疵。
- **面b F-10**:`kernel/cw_vocab.py` L994-999——HoldFrame 退役注块之后残留 `reason`/`route_tag` 两行孤立字段声明(与 L988-991 同名重复,dataclass 行为不变,纯死代码)。
- **面b F-11**:`cw_vocab.py` 的 `CwActionOpenBoxParam`/`CwActionOpenTomeParam`/`CwActionOpenBookcardParam` 三类 `slot` 字段无 [索引定义] 注释(坐标系/取值时机),违 AGENTS §8「索引/槽位字段必须带定义注释」;同族 `SellBenchParam.bench_idx`/`DeployMoveParam`/`WearEquipParam.slot` 均合规,坐标系事实(画面物理槽位 1 基)与 `screens/README.md` §4 二分及上报函数 `slot−1` 换算一致。
- **根因归层**:六条各自独立的小面——F-2/F-3 属**表示层**(契约措辞/指针滞后),F-4/F-10 属**流程层退役收尾残留**(同主题E家族,量小单列),F-5 属**约定层**(文档纪律执行),F-11 属**约定层**(注释规范执行)。逐条修法句见 §2.7,无架构动作。
- **解决到哪**:逐条措辞/注释/死代码修法(§2.7)。
- **明确不解决**:`PrepObservation` 动态属性改局部变量的代码形态重构(零行为收益的 churn,取舍见 §2.7-1);其他画面篇的同类日期/事故史残留(本批只辖 prep.md,不外推)。

### 1.8 已核对一致面

两面报告 §3 已核对一致的重要面(重型屏申报形态/识别-落容器分工/审计链留守/发射铁律/in_place 通道/商店编排口径/节点锚定/出口三语义/坐标系二分/词表注册表完备/守卫/发射判据归属/SwapDeploy 与商店锁在册欠账/上报族写语义除 F-3/F-4 两篇等)本稿不立修法,仅作为修法不得触碰的现状边界——落地时禁借清理之名改动这些在码语义。

## 2. 方案

### 2.0 系统级变化(读一遍知全貌)

本稿落地后:①备战域动作面全集对 `action_ops.md` §1 增补 3 **零违例**(两处读屏形态清除);②逐动作正本篇/索引面/终结总表/容器域申报正本与代码行为逐字一致(升格、终结化、注册表扩表三个滞后面全部对齐);③部署机/组合壳两个退役时代的残留清偿:`cw_op_sell_off_target.py` 与 `cw_op_equip_all.py` 两文件删除、注释死指针逐点改写、docs 正本面对账点位清偿(§2.5.6)、外溢面显式登记(§2.5.6);④画面篇 prep.md 达成 screens README §2 全部纪律(无状态/无幻影步骤/无失效指针)。**零容器写语义改动、零策略判据改动、零新增机制**(机制防线候批 = §2.9);唯一行为微差 = §2.1 申报的两处。

### 2.1 主题A 修法:两处欠账本批直接清(面b F-1/F-2)

**裁定:方案②(本批直接清),否决方案①(登记欠账随批清除)。** 取舍依据:两案行为差异面都极小(F-1 命中只进 log/detail,从无控制流;F-2 预算耗尽照样拖),案①需在 `action_ops.md` §1 清单、§4.2 行、deploy-move.md、wear-equip.md 四处按「现役违例+欠账标注」双语写,清除批还要再改一遍 = 双倍文档工且违例长期在册;案②清后备战域动作面全集零违例,规范收敛最快,批大小可控(两代码点 + 三文档行)。逐条:

1. **F-1 DeployMove 拖后 overlay 快查 = 删除**。删 `cw_deploy_move_action.py::run` L84-95 注释与快查段(`_post`/`_overlay` 两赋值 + `if _overlay` log 分支)及 L106-107 的 `_overlay` detail 分支(round_success 恒走「部署已发…」detail)。依据:快查动机(防下一步动作打在 overlay 上)在删后由既有两道面承接——拖后 2s 固定等待(徽章动画窗,保留面)+ 批尾/下一入口 heavy 观察的 `event_overlay` 检测(`cw_screen_prep.py::_observe` L212-217,命中即 `CwObsOverlayBail` 交回外循环);快查本身从未改控制流,删除 = 零防线损失。行为微差申报:round_success detail 不再含「盛会之星 overlay 弹出」标注(仅诊断措辞面)。文档同步:`logic-updates/deploy-move.md` §3.7 删「触发型 overlay 快查(……)」句(保留 2s 固定等待句);`action_ops.md` §4.2 DeployMove 行删「+ 盛会之星 overlay 快查(detail 标注,外环接管)」句。测试同步:`sr-od-test` 的 `test_cw_action_emit_book.py`/`test_cw_deploy_to_slot_semantics.py` 中为该快查存在的 `round_by_find_area` 桩键核实后摘除(桩无害但属死桩)。
2. **F-2 WearEquip 拖前稳帧轮询 = 改固定等待**。`prep_actions.py::PrepActionExecutor._wait_stable_frame`(L703-718)整函数删除;`cw_wear_equip_action.py::run` L74 的 `ex._wait_stable_frame()` 调用替换为固定等待 `time.sleep(PREP_DRAG_SETTLE_WAIT_S)`,新常量 `PREP_DRAG_SETTLE_WAIT_S: float = 0.5` 落 `prep_actions.py` 执行器常量区。常量取值依据:被替换轮询的首次检测间隔 0.3s 即典型稳帧档(`prep_actions.py` L703 原 `interval=0.3`),1.2s 预算是其最坏动画窗上限,0.5s = 典型档向上取整,与固定等待族 pick 确认 0.6-1.2s 同量级(`action_ops.md` §2.2);后随动作的动画由既有拖后 1.5s 固定等待覆盖,拖前等待只辖「上一变动(入口动画/上件 reflow)未收尾」一窗。失败治理不变:极端 reflow 未收尾致按压抓空 = 未发出形态,由下一入口观察对账显影 + 决策环自然重派;实机若该形态复发,按 `action_ops.md` §1 增补「不存在偶发丢失」纪律查根因调常量,**禁恢复轮询**。行为微差申报:拖前等待从「条件化至多 1.2s」变「恒 0.5s」——画面已稳时多睡 ≤0.5s,未稳时少等,均不产生判效。文档同步五处:`action_ops.md` §2.2 固定等待族清单补一行(穿戴拖前 settle 0.5s `PREP_DRAG_SETTLE_WAIT_S`);`logic-updates/wear-equip.md` §3.1 「`_wait_stable_frame`(输入条件化等待,非判效)」改「固定等待 `PREP_DRAG_SETTLE_WAIT_S`(等备战面板/上件 reflow 动画收尾,非判效)」、§6 符号锚同步(删 `_wait_stable_frame` 补常量名);`cw_wear_equip_action.py::run` docstring L53「稳帧确认(动画收尾输入条件化等待,非判效)」改「固定等待 `PREP_DRAG_SETTLE_WAIT_S`(非判效)」;`prep_actions.py` L639-641 域注释「机械原语 `_equip_slot_drag_point`/`_owned_grid_locate`/`_wait_stable_frame` 留守本 runner」删 `_wait_stable_frame` 项;`flow/projection_contract.md` L112「装备穿戴的执行期时序」段(CV-diff 判穿/稳帧确认/落空补救链/`last_owned_equips` 快照均为已退役机制)整段改写为现役机械半形态(定位读 + 固定等待 + 单次拖拽 + 自上报,落地归观察对账)。测试同步:`test_cw_action_emit_book.py` L173 `ex._wait_stable_frame = lambda…` 桩行删除(monkeypatch `time.sleep` 已覆盖新等待)。

### 2.2 主题B 修法:零写升格面五处正本 + tools.md 专篇对齐(面b F-3/F-4)

统一口径(依据 = `kernel/cw_action_report/wear_equip.py`/`tool_use.py`/`zero_writes.py` 头注 + `action_ops.md` §4.2 工具段):**WearEquip = 容器 `gs.equips` 写 owned−1 + tracked 目标角色 +1;工具原子七类 = 容器直写(确定面 `write_logic`/随机面 `write_logic_rand` 采样链,投影仪复制走 `gain_character` 获得链,变异面不走链,零写分支留证 `tool_*`);零写族现役成员 = OpenBox/OpenShop/事件线零写 pick 族/刷新建议三动作/Obs,集中在 `zero_writes.py`**。

1. `logic-updates/wear-equip.md`:§1 删「不在 `cw_vocab.py::Action` 联合内——零容器动作转移语义」错申报(改「在册词表类,注册行 = 备战域 op」);§2 开头「容器 GameState `equips` 域不写(零写族申报 = `zero_writes.py` 集中承载)」改为「容器 `equips` 域**有写**:owned −1(在册才减),上报函数单点」(§2 表内 owned 腿行已是正确描述,去节首矛盾即可);§7 「零写族成员……write_seq 不变」整段改为容器写语义申报(非零写族成员;落地真值归观察边界 reconcile)。§2 表/§3 转移规则/§6 符号锚已与代码一致,不动。
2. `game_state/fields.md` 备战动作逻辑态写口覆盖面申报段(L1473-1476):「零写族……= OpenBox/WearEquip/工具原子七类集中在 `zero_writes.py`」改「零写族(消费真值归观察/终结化)= OpenBox/OpenShop/事件线零写 pick 族/刷新建议三动作/Obs;**WearEquip 与工具原子七类 = 容器写侧**(`gs.equips` 写,正本 = `kernel/cw_action_report/wear_equip.py`/`tool_use.py`),与 `zero_writes.py` 迁出注记对齐」。
3. `logic-updates/tools.md` 整篇改写:§1 末句「七类均在 Action 联合外」改「七类均在册」;§2 域集整节改写(容器 `equips` 域**有写**:消耗移除与效果腿同域**合并单笔** `write_logic`/`write_logic_rand`,禁拆两笔;获得走 `gain_character` 链;变异面不走链;零写分支留证)——`EQUIP_WRITE_SIDES` 登记面与效果桥(`transform_equip_to_privilege`/`spawn_equip_bench_unit`/`grant_equip_item`/`settle_wrench_duplicate_gold`,均在役)保留为「效果写端桥」引用,不再表述为「执行写端分派」宿主;§3 第 3 条「执行写端分派 = `apply_tool_execution_write`」整条改写为「上报写端 = `kernel/cw_action_report/tool_use.py` 七具名上报函数(`_REPORT_BY_CLASS` 按 param 类型解析,一族一文件先例),逐类语义与采样口径以函数 docstring 为正本」;§6 符号锚剔除 `zero_writes.py`(七类零写上报函数)与 `apply_tool_execution_write`,补 `kernel/cw_action_report/tool_use.py`;§9 依据行同步(删 `apply_tool_execution_write` docstring 指针,补 `tool_use.py` 模块头)。逐类写语义表以 `action_ops.md` §4.2 工具七行(已与代码核对一致)为准转写,不新造语义。
4. `screens/prep.md` §4 零写族行(L67)改为:「有容器写语义动作 = SellBench/SellDeployed/DeployMove/LevelUp/CollectOre/OpenTome/OpenBookcard/**WearEquip(容器 equips 写 owned−1 + tracked 目标 +1)**/工具原子七类(容器直写,正本 = `tool_use.py`);零写族 = OpenBox(终结化)/OpenShop/事件线 pick 族集中 `zero_writes.py`」。
5. `logic-updates/README.md` 索引表 WearEquip 行「容器 equips 零写 + tracked 账内聚」改「容器 equips 写 owned−1 + tracked 账内聚」;工具七行「零写族 `zero_writes`(容器零写)+ `apply_tool_execution_write`」改「容器直写(正本 = `tool_use.py` 七函数)」。
6. `flow/action_ops.md` §4.2 WearEquip 行「(tracked 账:owned −1 + 目标角色 +1)」改「(容器 equips 写 owned−1 + tracked 目标角色 +1)」。
7. **同退役符号两文件三点(门4「全范围零命中」的全集补全)**:`game_state/action-logic-state.md` L41 被指对象清单与 L299 依据行的 `kernel/cw_affix_effects.py::apply_tool_execution_write` 锚改现役(上报写端 = `kernel/cw_action_report/tool_use.py` 七具名上报函数;登记表 `EQUIP_WRITE_SIDES` 与效果桥四函数保留);`game_state/logic-updates/op-effects.md` L49 机制锚段「分派口 = `apply_tool_execution_write`」改现役上报写端口径(同上),并同步同句「容器域 = 合法零写集」旧括注为 §2.2 统一口径(工具七类 = 容器直写)。跨稿承接声明(残留 R4-1 清偿;R11h 归口裁定 = 本稿):`action-logic-state.md` 认领归 T-1,本稿辖 L41 被指对象清单的 `apply_tool_execution_write` 锚片段(本条)与 L299 依据行;T-2 稿辖同清单的刷新计数括注片段(目标文本见 buy_cards.md §2.3-10)与 L108 依据行(buy_cards.md §2.4),两片段不相交零互覆,T-2 片段随 T-2 落地批凭其稿目标文本落笔,后落批以落地时点现值为准对账,禁双写。

### 2.3 主题C 修法:终结语义三处记载对齐(面b F-5)

1. `screens/README.md` §6 表补一行(位置紧随 OpenBox 行):「| 备战 OpenBookcard | **访问终结** | 开卡 = 专家邀请函弹窗在场 = 新事实,交回外循环按该画面分发选卡(`terminal_wait=1.8`;发射位 = 策略器 entry ① prep 实体面卡片臂) |」。依据:`cw_open_bookcard_action.py` L40/L44、`screens/README.md` §5.5、`screens/prep.md` §5。
2. `flow/action_ops.md` §4.2 OpenBookcard 行「开书册卡(非终结)」改「开书册卡(**访问终结**,`terminal_wait=1.8`)」,行内交回语义句与 §6 新行对齐。
3. `screens/README.md` §4 动作词表表:OpenBookcard 从「领取类」三合一合并行(`CwActionCollectOreParam`/`CwActionOpenTomeParam`/`CwActionOpenBookcardParam` | 非终结)拆出为独立行,终结性 = 「**访问终结**(§6)」,执行载体列不变(同名 `_action.py` op)。

### 2.4 主题D 修法:logic-updates README 索引面重建 + 跨稿承接(面b F-6)

对 `game_state/logic-updates/README.md`:

1. **计数口径改「以代码现值为准」**(采纳 T-4 稿同款论证:计数类陈述反复漂移的根因是把快照值写死进正文,禁静默择一):索引节声明「行数/类数/专篇缺档数一律以**落码时点 `cw_action_registry.py` 现值**清点为准,本节不固化计数;落码时注册表已演进 = 以当时代码现值重清」。当前快照括注 = 36 行 / 28 op 类 / 专篇在档 27 行(20 个专篇文件,工具 7 行共 `tools.md` 一篇、LevelUpShop 显式行并入 `level-up.md`)/ 缺档 9 行(8 个 pick 行 + Obs 行:语义现役记载 = `flow/action_ops.md` §4.5/§4.4 行 + 上报函数 docstring,补篇外溢不批)。
2. **pick 族表 5 行扩为 13 行全列,按现役两档分型落行**(依据:`cw_action_registry.py` L179-191 + `kernel/cw_action_report/` 各上报模块头 + `cw_overlay_pick_action.py` op docstring;**以落码时点代码现值为准逐模块头复核**——本表分型不得沿用任何快照时点的档成员,迁移批落地前后盘面不同):
   - **即时单相(6 行)**:PickEncounter(发射即写 `chosen_encounter`)、PickSupply(一口写 owned+单位腿+后果腿)、PickInvestStrategy/PickInvestEnv(整支走获得链)、PickPlanner(条件腿 rider 先行 → equip/upgrade 腿一口写,具名模块 `pick_planner.py`,模块头申报即时单相)、PickEquip(归一件名 `write_logic` + 后果链,具名模块 `pick_equip.py`);
   - **零写族(7 行)**:PickMegastar/PickPartner/PickFortune/PickWishTrial/PickStarTome/PickBoxCard/PickExpertInvite(`zero_writes.py` 在册)。
   现役**无分步两相行**:`action_ops.md` §4.5 现文已申报「全族即时上报……两相与证据闩形态已全域清偿」,本表不设分步档、不引用失效的欠账标注——把已清偿面固化进目标文本 = 制造同族新漂移。
3. **「词表在册、不经注册表分发」节重建**:删「7 个 handler 自管 pick 子类……不经注册表」整行(与注册表现状直接矛盾);**SwapDeploy bullet 移出本节**——代码真值 = `CW_ACTION_TYPES` 白名单不含 `CwActionSwapDeployParam`(仅 CwAction union 在册),本节节首句「以下词表类在白名单但无注册行」对它不成立;SwapDeploy 改作**非词表类注**(采纳 T-4 稿同款处置):「union 在册 / 白名单外 / 无注册行 / 上报与 sim 消费在役,宿主 = `prep-executor-actions.md` §3」。节内剩余 = 3 刷新动作行 + 商店域旧 op 文件注销行。
4. **观察族**:转场族表后补 Obs 行(1 行,`CwActionObsOp`,零写占位 `report_action_obs_param`,专篇缺档注)。
5. **跨稿承接与归属声明(防双改)**:`game_state/logic-updates/README.md` 归**本稿统改**;**T-2/T-4/T-5 三稿对该 README 的条目均并入本稿实施**——T-2 稿 RefreshShop 行行级修正(`record_refresh_execution` → `record_refresh` 单口,目标文本见 buy_cards.md §2.3-9)、T-4 稿事件线索引段与 pick 行分型(按其修订版)、T-5 稿 PickSupply 行目标语义(整行文本见 supply_node.md §2.2)。已归口 T-4 修订版的模块头分型段(经 T-37 汇总登记)按 T-4 修订版落行,本稿不另立口径;分型成员判值以落码时点代码现值为准(§2.4-2)。**T-6 稿(invest_strategy.md L31/L104)对同一 README 的三项输入并入承接(残留 R4-3 清偿,消除「T-6 侧等待、T-1 侧无钩子」双边悬挂)**:①PickInvest 索引行目标语义——已由 §2.4-2 即时单相档覆盖(PickInvestStrategy/PickInvestEnv 整支走获得链);②「handler 自管不经注册表」句删除——已由 §2.4-3 覆盖;③专篇缺位二选一 = 新增 pick-invest.md 专篇(T-6 稿 §2.3 骨架),落档后 pick 缺档 8→6,§2.4-6①「pick 族专篇五篇」句与 §2.4-1 缺档快照括注随其落档批以落码时点现值重清(§2.4-1 口径自愈,本条 = T-1 侧接管钩子);接缝归口 = T-37 汇总登记(与对岸 invest_strategy.md L104 缝合登记对账)。
6. **同根顺带计数同步**:①`logic-updates/prep-executor-actions.md` §4「全集映射(26 注册行)」改「全集映射见 README(计数以注册表现值为准)」+「pick 族五篇」改「pick 族专篇五篇(其余行缺档,见 README 索引)」;②`flow/action_ops.md` §4.2 标题「备战族(9 行 + 工具原子 7 行)」改「备战族(10 行,含 LevelUpShop 同字段双类型显式独立行)+ 工具原子 7 行」,消除与 §4 覆盖声明的口径矛盾;③`flow/action_ops.md` §3 偏离清单「(注册表 27 行 / 20 个 op 类)」同步改现值口径,消除与同文件 §4 覆盖声明「36 行」的文内矛盾;④`flow/action_ops.md` §4.5 标题「事件线 pick 族(12 行;…)」改「(13 行;…)」——表体实 13 行,与 §4 覆盖声明验算一致(3+17+2+1+13=36)。

### 2.5 主题E 修法:退役残留清理包(面b F-7/F-8/F-9 + P-1/P-2)

#### 2.5.1 deploy.md 符号归属修正(F-7)

`screens/deploy.md` §1 环节表首行「部署选人/围栏/排序/底线门」拆为两行,对齐 `flow/action_exec.md` §5 分层:

- 「部署选人/排路由/槽位计划 | `strategies/impl/mandate_v1/deploy_plan.py`(`select_deployments_reasoned`/`deploy_row_pref`/`deploy_slot_plans`/`deploy_plan_moves`)」;
- 「围栏常量与共用判定谓词 | `kernel/cw_deploy_logic.py`(`recipe_floor_holds`/`select_swap_plan`/`residual_fill_plan`)」。

依据:符号定义位置实查(grep `def select_deployments_reasoned` 等八符号)+ `action_exec.md` §5 原文。

#### 2.5.2 logic-updates 两篇执行载体改现役(F-8)

- `logic-updates/sell-deployed.md`:§1 「执行载体 = ……与部署面换血 `cw_screen_deploy.py::_sell_offtarget_deployed`」改「执行载体 = `operations/cw_op/cw_sell_deployed_action.py::CwActionSellDeployedOp`(注册表行);换血卖出(m1p 臂)= mandate 发射位逐件产 `CwActionSellDeployedParam` 原子,同一执行载体,卖谁判据单一源 = `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`」;§6 符号锚删 `cw_screen_deploy.py::_sell_offtarget_deployed` 项,补 `cw_sell_deployed_action.py::CwActionSellDeployedOp`。§8 「商店 op 表(`cw_action_registry.py`)未收录本动作」句与注册表现值字面矛盾(`CwActionSellDeployedParam` 备战族行在册)——改写为自足现役申报:「生产策略面归备战期(注册表单行在册,备战域 op);商店期默认发射面 = 买/刷/关(判例 = [screens/README](../../screens/README.md) §5)」。
- `logic-updates/prep-executor-actions.md`:§3 括注「(备战域部署换位经部署机拖拽承载)」改「(备战域部署换位 = DeployMove 原子序,部署机画面 op 已退役)」;§4 计数与 pick 专篇句见 §2.4-6①。

#### 2.5.3 退役符号注释清理(F-9)

**清理准则(与 T-3 稿 §2.6 对齐,全迭代统一基准)**:①**现役语义描述**(消费面/写入端/执行载体/时序关系)必须用现役符号或纯语义描述,禁以现在时引用已退役符号;②**历史实证句**(某时点某局/某次验证的可复核实证)改**纯语义描述**(`实机对局实证:<机制>` 形态)+ 退役申报,日期/局号/轮次号等局部标识符归 git(AGENTS §8 禁会话局部标识符);③**退役申报史注**可用「已随 X 退役」句式指称退役机制本身(为读者指认考古对象),但禁写成现役指向;④与该处无史注价值的退役符号引用 → 直接改写现役或删除。本文件族已有的合规史注(如 `mandate.py` L1942/L1975「原消费方 = CwScreenDeploy 部署段(组合壳退役后…)」、`projection_contract.md` L110)按准则③保留不动。逐点清单(处置 = 改写后的现役指向):

| 位置 | 现句要点 | 处置 |
|---|---|---|
| `kernel/cw_deploy_logic.py` L389/L647/L923/L1150/L1261/L1327 | 消费面写「执行侧卖出臂(CwScreenDeploy `_sell_offtarget_deployed`)」 | 改「发射面谓词消费(mandate m1p 换血臂 `select_swap_plan` 调用面);机械执行侧 `CwActionSellDeployedOp` 不消费本函数」(依据:全仓 grep,执行侧现役零调用) |
| `kernel/cw_deploy_logic.py` L1141-1143 | 「执行侧卖出后补部署重 derive 的同名穿参(**cw_screen_deploy R1-b 回落臂**)」——文件形态退役引用 + 审计号 | 改现役:「执行侧卖出后补部署重 derive 已随部署机退役,现役归 m1p 发射臂逐件产原子 + 环内重 derive」;R1-b 审计号归 git(准则②) |
| `kernel/cw_launch_admission.py` L344 | 「执行时刻以 CwScreenDeploy 现读重建为准」 | 改「执行时刻机械单发零现读,落地归观察对账(预估与执行间无现读重建面)」(依据:`action_ops.md` §2.1 现行为模型) |
| `obs/cw_observation.py` L1287/L1300 | 「CwScreenDeploy 用它定位空位/应用本 Y」 | 改现役消费面 = 备战观察装配环(`cw_screen_prep.py` cap 段 L411/L441)与后排布局选档(`obs/cw_back_layout.py`) |
| `obs/cw_observation.py` L2237 | 「deploy 走 CwScreenDeploy」 | 改「部署 = DeployMove 原子序(备战决策环动作)」 |
| `telemetry/match_archive.py` L150/L810 | 「执行期 deploy 换血卖出(CwScreenDeploy._sell_offtarget_deployed)的逐件身份只在 log 行」 | 按准则②改纯语义:「实机对局实证(部署机时代):执行期换血卖出逐件身份只在 log 行与匿名计数键,无遥测行」+ 退役申报;departures 列「帧间差分吃未记录卖出」的派生口径保留(现役同类通道 = m1p 臂 SellDeployed 原子,决策时点逐件在案) |
| `telemetry/match_archive.py` L573/L1073、`telemetry/schema.py` L196 | 「先于 CwScreenDeploy/CwOpEquipAll 执行」 | 改「先于备战期动作执行(部署/装备原子序)」(纯时序关系,无需具体符号) |
| `strategies/impl/mandate_v1/mandate.py` L1853/L1868 | 「卖谁由执行侧 CwScreenDeploy 卖出臂现读仲裁」「消费点 = CwScreenDeploy.deploy 卖出臂(读后即清)」 | 改现役 m1p 发射臂口径:发射位逐件产 `CwActionSellDeployedParam`+`CwActionDeployMoveParam` 原子,卖出件 = 发射位按同一判定集现算,机械执行侧零仲裁;`cw4_m1p_arm_pending` 分键消费申报对齐 `projection_contract.md` L110 在册口径 |
| `strategies/impl/mandate_v1/mandate_state.py` L245-247 | 「消费面 = CwScreenDeploy 部署段(R1-a 直投核对…)」 | 改对齐 `projection_contract.md` L110 在册申报(消费半随部署机退役,现役零读端显影),禁再写成现役消费面 |
| `operations/dev/drag_cw_char.py` L9-10 | 「deploy(`CwScreenDeploy`)」消费列举 | 改「`CwActionDeployMoveOp`/穿戴工具原子(经统一拖拽原语)」 |
| `prep_actions.py` L283-284 | validate docstring「动态前置……由 execute 的完成验证覆盖」 | 删该句(实现中无完成验证段,T-1b §3 备忘;F3 = 执行前输入契约检查,`action_ops.md` §1 在册) |
| `kernel/cw_registry.py` L891 | 「H2②/H3 读端在 operations/cw_op/cw_op_equip_all.py」 | 改「H2②/H3 读端 = kernel 判据消费位(`cw_equip_wear_plan._build_equip_wear_plan` 判据链);原执行器读端已随装备组合壳退役」 |
| `data/cw_equipment_data.py` L46 | 「消费 = cw_op_equip_all(工具不进 drag 穿戴循环)——双方均 import 本常量」 | 改「消费 = kernel 判据面(`cw_equip_wear_plan` 穿戴候选过滤)与执行边定位读(`prep_actions._owned_grid_locate`)——双方均 import 本常量;工具消费 = `CwActionToolUseOp`」 |
| `tools/cw/gen_equip_registry.py` L406 | 同句(生成器注释) | 同上口径同步(src 侧改写后两处保持同句) |

docs 正本面点位(projection_contract/session/architecture/game 侧)见 §2.5.6 处置清单。

#### 2.5.4 P-1:CwOpSellOffTarget 死文件 → 删除

删除 `operations/cw_op/cw_op_sell_off_target.py` 整文件。理由(依据逐条):①文件头自有【退役·禁接旧码】申报 = 定性「退役不彻底」而非「待重接资产」,重接前置(补建档 + 策略判据迁策略侧 + 禁带入 ESC/硬编码违例)意味着重接路径 = 重写,文件本体无可保留的实现价值;②申报的承接者 `deploy_bench._sell_offtarget_deployed` 已随部署机退役,承接链断裂,保留价值只剩考古 = git 历史职能;③op-layer.md §3 的 36 op 总表无此 op,全仓零引用,删除零行为影响;④在册保留候选(登记能力面理由)被否:清存量 off-target 的现役覆盖 = m1p 换血卖出臂(板满形态)+ SwapDeploy 能力面(对调形态),且「谁该卖」判据在册单一源 = `swap_sell_exclusion_reason`,死文件不含任何在役判据。

#### 2.5.5 P-2:CwOpEquipAll 半死文件 → 整文件退役 + helper 归一

裁定:**`operations/cw_op/cw_op_equip_all.py` 整文件退役删除**,唯一活 helper 的职能**归一进目标文件既有的同职能单一缓存口**,随类死亡成员一并删除。依据:类体零构造调用(全仓 grep);文件仅存的跨文件消费 = `prep_actions.py::_owned_grid_locate` 的 `get_equip_templates_cached`;其余模块成员消费面全部在类体内(死)。逐项:

1. **helper 归一(目标态裁决)**:`get_equip_templates_cached`(SIFT 模板缓存装载,缓存 `ctx.cw_equip_templates`)与目标文件 `obs/cw_equipment.py` 既有的 `ensure_equip_sift_templates`(缓存 `ctx.cw_equip_sift_templates`)为**同职能装载器**——函数体逐行同构(同 `equip_plaza`→`equip_legacy` 目录回退序、同包装 `load_equip_templates`),仅缓存属性名不同;迁入不归一 = 同文件两套 SIFT 缓存口并存(同一模板库各加载一份内存,观察链走 `cw_equip_sift_templates`、执行边走 `cw_equip_templates`)= 本批正在清的同职能多源漂移新实例。**裁定:消费面切到既有单一口**——`prep_actions.py::_owned_grid_locate` L679-682 改 import 并调用 `obs/cw_equipment.py::ensure_equip_sift_templates`,`get_equip_templates_cached` 随文件删除;缓存属性统一为 `ctx.cw_equip_sift_templates`(归一是纯消费口切换,同库同 loader 零行为差,仅缓存属性名与首载时点归属变化)。连带失效注同步:`ensure_equip_tm_templates` docstring「装备区模板由 equip_all._get_templates 另加载,不冲突」句删除(其所述双口并存形态随归一消失)。测试同步:`test_cw_unified_action_2a.py` L502-506 monkeypatch 目标改 `cw_equipment.ensure_equip_sift_templates`(函数内 import 在调用时解析,改模块属性即生效,机制不变)。依赖方向顺带修正:`prep_actions.py`(包根模块)→ `operations/cw_op` 的跨层 import 随归一消除,改指向 `obs/`。
2. **随类死亡成员删除**(唯一消费面 = 类体,src/测试 grep 实证):`get_equip_tm_grays_cached`/`get_avatar_templates_cached`/`register_equip_worn`/`_owned_wearable_names`/`record_zero_wear_defect`。其中 `get_equip_tm_grays_cached` 与 `ensure_equip_tm_templates` 写同一缓存属性 `ctx.cw_equip_tm_grays`(隐性双写端),随删除消除。
3. **零穿戴哨兵面退役裁定(显式申报,本批唯一语义收缩点)**:`record_zero_wear_defect`(执行面挂点唯一调用者 = 死类)与 `kernel/cw_equip_env.py` 的 `classify_zero_wear_stop_reason` + `ZERO_WEAR_*` 五常量(L132/L136/L137/L138/L139)+ `_ZERO_WEAR_EXECUTION_REASONS` 枚举(唯一消费面 = 被删函数;哨兵面引用全集 = src 三处——被删文件、`cw_equip_env` 自身、`cw_equip_wear_plan` L97 已列改写——加 strategy-docs 18/21 外溢登记;src/测试/tools 零其他引用实查,tools/ 全域零 ZERO_WEAR 族引用)**随批整体退役**。依据与理由:哨兵执行面挂点已随组合壳退役断线(现役原子序逐件发射,「零穿戴」在发射位天然显形 = mandate 发射位计数 `equip_plan_empty_noop`/`equip_plan_resource_missing`,`mandate.py` L2035/L2046),哨兵无独立信息增量;保留零消费面的分类器与常量 = 本批正在清除的同一漂移类。备选(保留分类器+注释申报零消费)放弃:死代码保留与 §2.5.3 准则①冲突,git 可溯。落码面(**语义锚定,勿按行号整段删**——模块头 L18-41 为现役/待删混合列表):删哨兵两条 bullet(`classify_zero_wear_stop_reason` 条,L23-24;哨兵分键句,L35-37);L20 现役 `resolve_wear_release` bullet 内「执行层(CwOpEquipAll)只消费」随句改写去符号(「执行层只消费 `WearReleaseDecision.hold`,禁第二套时机判断」);枚举注释块(L141-162,含 L155「写入端 = CwOpEquipAll.STATUS_PLAN_STALE」失效指向)随枚举整体删除;`kernel/cw_equip_wear_plan.py` `EquipPlanBuild.empty_reason` 注释「`classify_zero_wear_stop_reason` 词表与分键锁零漂移」句改为「字面量消费面 = 遥测分键计数,无分类器依赖」(empty_reason 字面量本身由计划面继续产出,保留)。
4. **关联注释/遥测叙事逐点**:①`kernel/cw_equip_wear_plan.py` 模块头 L7-8「机械执行半留守 `cw_op_equip_all.py`」改「机械执行半现役宿主 = `cw_wear_equip_action.py::CwActionWearEquipOp` + `prep_actions.py` 机械原语(`_equip_slot_drag_point`/`_owned_grid_locate`)」;L72-74 `EquipWearStep` docstring「随 `CwOpEquipAll.__init__(ctx, plan)` 构造下发」改「发射位逐步产 `CwActionWearEquipParam`」;L29 `FRONT_SLOT_COUNT` 史注「原 CwOpEquipAll.FRONT_SLOT_COUNT 迁居」按准则②改纯语义「自备战执行器模块迁居(考古归 git)」;L138「`cw_op_equip_all.py` 零引用(机械执行红线)」改「执行器侧对四判据零引用(机械执行红线)」;②`mandate.py` L2045 注释「零穿戴哨兵执行面在 CwOpEquipAll」随哨兵退役删除;③`kernel/cw_comps.py` L2073 `equip_allocation` docstring 末「CwOpEquipAll 消费。」改「消费面 = `kernel/cw_equip_env.py`(判据求值位)」;④`obs/recognizers/battle_prep_recognizer.py` L25 「2026-08-16 M34 live(CwOpEquipAll 身份)通过」按准则②改纯语义 + 退役申报:「实机对局实证:plaza 烘焙立绘库经备战执行面身份链 live 验证通过(该执行面已退役,考古归 git)」;⑤`kernel/cw_equip_env.py` L372-373/L394/L408-409 三处 docstring「自 cw_op_equip_all 迁入策略侧」改「自备战执行器模块迁入(语义逐字不变;考古归 git)」;⑥`prep_actions.py` L644「与 CwOpEquipAll._slot_drag_point 同式」改自足描述(「与同文件拖点派生式同构:rect 中心 x + y1+21」);⑦`kernel/cw_equip_wear_plan.py` `EquipPlanBuild.owned_wearable_names` docstring「零穿戴哨兵双挂点之计划面输入;哨兵内部再做工具类过滤,幂等」改现役语义「计划面产出的本帧可穿名单快照,测试锁消费」(去哨兵/双挂点指称;残留 R4-2 清偿——字段本体存活,`test_cw_exclusive_wear_gate` 断言消费,处置 = 注释现役化改写而非删除)。
5. **取舍**:备选 a「类体删除、helper 迁居 `obs/cw_equipment.py` 原样并存」放弃——同文件同职能双缓存口 = 新多源;备选 b「helper 原地保留(仅删类体)」放弃——单函数文件名(`equip_all`)与内容失配,且保留跨层 import(包根→operations/cw_op)与双缓存口,治标;备选 c「哨兵重挂到原子路径」放弃——重挂 = 新观测行为设计(选挂点/预算/辖域),超出符合性审查批,登记归观测迭代。

#### 2.5.6 docs 正本面处置清单(docs 敞口闭合)

**本批处置**(现役指向失真、直接误导,逐点):

| 位置 | 现状要点 | 处置 |
|---|---|---|
| `flow/projection_contract.md` L80 | 「装备 owned 名单写端 = `cw_op_equip_all.py::CwOpEquipAll`…穿戴落地销账 = `register_equip_worn`」 | 改现役:装备 owned 快照写端 = 备战入口观察装配点(`cw_screen_prep._observe` heavy 装备域三路直写容器 `gs.equips`);穿戴腿 = `report_action_wear_equip_param`(owned−1 + tracked 目标 +1);执行器时代写端已随组合壳退役 |
| `flow/projection_contract.md` L112 | 执行期时序段 = CV-diff 判穿/稳帧/补救链/`last_owned_equips`(全退役) | 整段改现役机械半形态(§2.1-2 第五个同步点,同一行两主题漏项一次清) |
| `flow/projection_contract.md` L125 | 装备臂行 = `cw_op_equip_all.py::CwOpEquipAll` | 改现役:装备域判据 = `kernel/cw_equip_wear_plan._build_equip_wear_plan`(容器读口),机械执行 = `CwActionWearEquipOp` |
| `flow/projection_contract.md` L141 | 合规抽样列举含 `cw_op_equip_all.py::register_equip_worn` | 删该项(随其退役) |
| `flow/session.md` L91 | 「`equip_drag_fail_counts` … CwOpEquipAll 拉黑」行 | 删行(字段与拉黑族已随执行层状态类目退役,失败记忆现役仅 deploy_fail_counts) |
| `flow/session.md` L219 | 迁宿主候选列举含 `CwOpEquipAll` | 删死项,候选 = `PrepActionExecutor`/动作 op 实例字段 |
| `architecture.md` L106 | 模块地图行列 `cw_op_equip_all.py`/`cw_op_sell_off_target.py`/`cw_op_tools.py` 为现役执行器 | 改现役:装备/工具执行 = `cw_wear_equip_action.py`/`cw_tool_use_action.py` + `prep_actions.py` 机械原语;死文件两项删除 |
| `docs/game/screens/currency_war_equip_detail.md` L40/L42 | 「CwOpEquipAll 穿戴决策/按 key_equips 优先穿戴」 | 死类指向改现役载体(穿戴判据 = `kernel/cw_equip_wear_plan`,机械 = `CwActionWearEquipOp`) |
| `docs/game/screens/currency_war_prep.md` L62 | 「CwOpEquipAll = 修 drag 回归」叙述 | 按准则②改纯语义 + 退役申报(历史实证指向现行执行载体 `CwActionWearEquipOp`/统一拖拽原语) |
| `docs/game/currency_war/research/equipment_mechanics.md` L223 | 「现状描述」句:执行侧零操作/工具自动化为待办 | 改现役:工具过滤单一源 = kernel 判据面;工具自动化消费已在役(`CwActionToolUseOp` 七类 + `cw_equip_env.evaluate_tool_actions` 准入) |
| `docs/game/currency_war/research/board_structure.md` L92 | 「`cw_screen_deploy.py` 布局选档 / `cw_observation.read_deployed_chars` 槽位读取」 | 布局选档改现役 = `obs/cw_back_layout.py::select_back_layout`;槽位读取改现役消费面(`cw_observation` 现役读口);死文件名删除 |
| `flow/projection_contract.md` L145 | 两任务判读「穿上/没穿上」证据「以 `register_equip_worn` 销账链与 `equip_zero_wear` 哨兵的契约语义为准」(两符号均随本批退役) | 判读依据改现役:真值 = 下一入口装备区观察读数覆盖;判读纪律 = 观察赢两态制(对账唯一发生点 = 观察边界,op-layer.md §1.3);该行所引 §3.7/§4.3/§5 失真面已由本清单 L80/L112/L125 行覆盖 |

**外溢登记(不本批,显式列出供 §2.8 门豁免)**:strategy-docs 三篇的判据叙述面——`strategy-docs/10_prep_decisions.md` L100/L152-157(判据源符号锚表,改写需逐锚核现役宿主)、`18_equip_wear_semantics.md` L8/L154/L206、`21_opening_window_and_tool_consume.md` L52/L77/L124/L184——属策略域语义稿,登记「退役符号指向现役化」候批(随策略稿维护批);`proofs/p95` L17/L42 = 命题存档的历史证据句(准则②史注形态在册),不动。

### 2.6 主题F 修法:「统一验证」措辞对齐(面a F-1/面b F-12)

两处画面篇改为 `action_ops.md` §4.2 CollectOre 行的准确口径,#16 研究表行同批改现役(依据 = `cw_collect_ore_action.py`:点击列 + park + 固定 2s + 自上报,零验证):

- `screens/prep.md` §4 执行要点行:「CollectOre 批式一次全点 → 等 2s → 统一验证」→「CollectOre 批式一次全点 → 固定等待 2s 等飞行动画 → 自上报交回;席满未点开的晶矿由下一帧观察回补」;
- `screens/README.md` §5.3 CollectOre 行「(批式:一次全点→等 2s→统一验证;…)」→「(批式:一次全点→固定等待 2s→自上报交回;席满未点开的晶矿由下一帧观察回补;…)」;
- `docs/game/currency_war/research/screen_flow_timing.md` L82(时序 #16 行)「逐晶矿『点击+1.2s 验证』×N → 批式:一次全点(大晶矿优先)→ 等 2.0s → 一次截图统一验证」改现役口径:「批式:一次全点 → 固定等待 2s → 自上报交回,零验证;席满未点开的晶矿由下一帧观察回补」(游戏时序事实「飞行动画最长 ~2s」保留)。**裁定:补处置而非豁免**——该行后半段 = bot 行为描述(系统面混入研究表),失真危害与画面篇两处同性质;「历史实测存档」豁免不成立(非纯历史档案,现态描述句式)。

docs 全树「统一验证」落码后归零(§2.8 门1;src/sr-od-test 现状零命中,门兼防回潮)。

### 2.7 主题G 修法:低危单点逐条

1. **面a F-2 PrepObservation 契约措辞**:契约与 docstring 三处各补一短句,把对拍轻字段显式入册——`flow/projection_contract.md` §1 观察载体行与 §4.4「只载控制信号……」句后补「(另挂观察链内部存续对拍轻字段 `front_occupied`/`back_occupied`:`deployed_count` 双源对拍消费,方法内即弃,不进 gs/session/report)」;`kernel/cw_prep_actions.py::PrepObservation` docstring 删除申报同步补同句。依据:`cw_screen_prep.py` L218-226 挂载 + L442 消费,方法内即弃,契约行为面未破。取舍:不改代码形态(动态属性改局部变量 = 跨方法传参 churn,零行为收益),只统一字面。
2. **面a F-3 帧代次槽名**:`flow/README.md` §2.2 「触发信号 = 黑板帧代次标注(`session.prep_frame_class`/`shop_frame_class` ∈ full/view/none,…)」改「触发信号 = GameState 非 Field 双槽帧代次标注(`gs.frame_class_prep`/`gs.frame_class_shop` ∈ full/view/none,写点 = 备战/商店域观察装配点与决策环直写,读者 = 决策入口方向节拍,读后即清)」;`flow/session.md` L57/L59 两段「两帧代次标注槽留 session」现态申报按现役改写(两槽宿主 = `gs.frame_class_prep`/`gs.frame_class_shop`,清册统计行同步——与代码相反的现态申报,病重于 README 触发信号句);`screens/shop.md` L25 括注「(shop_frame_class;续段 none 保持首段值)」改现役槽名(`gs.frame_class_shop`)。依据:`cw_game_state.py` L2144-2152(槽定义 + 值域/消费协议)+ 写点 `cw_screen_prep.py` L633/L760、`cw_screen_buy_cards.py` L798 + 消费 `strategies/impl/flow.py` L373-395 + `cw_strategy_session.py` L143-148(退役申报)。
3. **面a F-4 段迹锁失效指针**:`screens/prep.md` §9 测试锁句删「生命周期段迹锁、」;保留词表覆盖锁(写口两集)、部署 cap 板满门与已点名的测试文件(实查在场),可补 `test_cw_prep_node_chain.py`(链域专锁,实查在场)。依据:op-layer.md §4 段迹机制整体退役申报。
4. **面a F-5 裁定日期/事故史出正文**:判定线——**裁定日期与事故过程一律出正文**;可保留的「墓碑」类内容 = **纯技术边界注**(不标日期、不叙裁定与撤销过程、只陈述当前禁令与理由,如「X = 动画帧误判,禁再建模」);停机钩子的「临时段·采够删整段」性质注保留(当前状态的边界申报),去指令日期。逐点:`screens/prep.md` §2 书册卡臂句去「用户裁定 2026-09-19」、末句去「(原 HoldFrame 收编,用户裁定 2026-09-20)」(保留「空发射 = CwActionObsParam scope='outer_loop' 交回外循环重观察」语义);§3 书册卡句去日期、幻影墓碑句去「2026-09-19 定谳撤销」改纯边界注(墓碑 = `cw_identity_obs` 模块内注,禁再建模);§4 动作全集句去「用户裁定 2026-09-20」;§5 OpenBookcard 行去「(2026-09-19 卡片臂策略器化)」、HoldFrame 行去裁定日期;§8 安灯行去「2026-09-16 裁定」(保留「未建档实证的故障形态不作兜底理由」理由句)、停机钩子行去两处日期。裁定 why 的归宿 = 各迭代设计动机段与 git 历史(screens README §2 纪律 + AGENTS §9)。
5. **面b F-10 HoldFrame 残留**:`kernel/cw_vocab.py` L997-999 两行孤立字段声明(`reason`/`route_tag`,与 L988-991 重复)删除;L994-996 退役注保留(当前语义去向 + 考古指针,合规)。
6. **面b F-11 slot 字段索引定义注释**:`cw_vocab.py` 三类 `slot: int | None = None` 字段各补行内注释:「`[索引定义] slot = 备战栏画面物理槽位 1 基(area 序,坐标参数化机械动作族同系,screens README §4 二分);取值时机 = 发射期快照(决策半按观察 bench kind 槽位现算);None = 首个该类槽位`」。依据:上报函数 `slot−1` 执行换算 + `screens/README.md` §4 坐标系二分。

### 2.8 落地验证门(可机械核验 + 门红处置)

**门范围** = `src/` + `sr-od-test/` + `tools/cw/` + docs 正本树(`docs/develop/sr_od/application/currency_war/` 与 `docs/game/currency_war/`;**豁免** = 各迭代 `changes/` 过程区、`proofs/` 存档、§2.5.6 外溢登记点位)。人工执行,禁立源码扫描测试(AGENTS §10.4)。**门红处置**:门红 → 先判残留性质——属本稿处置清单漏项 = 补清单(修订本稿对应表)后重跑;属新语义/新裁定 = 停手回本稿提请修订,禁自行降门或放宽键。

1. **门1(docs 主验证)**:docs 正本树「统一验证」零命中(src/sr-od-test/tools 零命中兼防回潮)(主题F)。
2. **门2(退役符号·部署机)**:`CwScreenDeploy`/`cw_screen_deploy`(**类与文件双形态**,与门3 对称)零命中——豁免仅「已随 cw_screen_deploy.py 退役删除」申报句式(准则③)与活类 `CwScreenDeployNotFull`(主题E)。
3. **门3(退役符号·装备执行器)**:`CwOpEquipAll`/`cw_op_equip_all` 零命中——豁免仅 §2.5.6 外溢登记点位与「已随装备组合壳退役」申报句式(§2.5.5 各保留/改写点施工后,src/docs 正本无裸符号残留;`data/cw_equipment_data.py`/`tools/cw` 同句随 §2.5.3 表末行同步)。
4. **门4(零写族申报对照,人工 checklist 非 grep)**:五处正本(`logic-updates/wear-equip.md`/`game_state/fields.md` 覆盖面段/`screens/prep.md` §4/`logic-updates/README.md` 索引表/`logic-updates/tools.md`)的零写族成员列举逐一对照 §2.2 统一口径——断言「WearEquip 与工具原子七类不在零写族列举内、在容器写侧申报内」;`apply_tool_execution_write` 全范围零命中(主题B)。
5. **门5(黑板槽名)**:裸槽名两串 `prep_frame_class`/`shop_frame_class` 全范围零命中——豁免仅准则③墓碑注(`cw_game_state.py` 槽定义处「退役迁此」申报、`cw_strategy_session.py` L143-148 退役注)与各迭代 `changes/` 过程区(主题G-2/R3-1)。
6. **门6(轮询符号)**:`_wait_stable_frame` 在 `src/` 零命中(轮询函数已删、调用点替换、docstring/域注释/正本 L112 同步后)(主题A)。
7. **门7(P-1)**:`CwOpSellOffTarget`/`cw_op_sell_off_target` 全范围零命中(主题E)。
8. **门8(测试与回归)**:`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 全绿——覆盖 §2.1/§2.5.5 的测试同步面(桩删除/monkeypatch 目标迁移至 `ensure_equip_sift_templates`)。

本门集 = §2.9 登记条款(「退役/迁移批收尾固定清查门」)的首次人工执行。

### 2.9 机制防线登记(候批,交用户裁决)

五主题(B/C/D/E/F)根因同构:**变更批的收尾义务清单没有「正本引用面全量对账」这道门**——升格批漏正本篇与 fields.md、终结化批漏总表与词表表、扩表批漏索引面、退役批漏引用面清查、验证废除批漏画面篇措辞。本稿修法 = 逐主题症状清偿 + 一次性门(§2.8);**长效防线外溢登记,不在本批落**:

- **登记项**:「退役/迁移批收尾固定清查门」正本条款——内容 = 变更批(退役符号/机制迁移/索引扩表)落地收尾时,执行退役符号全仓 grep(含 docs 正本树)+ 索引面/总表计数对账,门红处置 = 补清单或回设计稿;
- **候选宿主**:`screens/op-layer.md` 批收尾节 或 `docs/develop/harness/iteration-design.md` 落地义务节(二选一由该候批裁决);
- **归口**:与 T-3 稿同款登记面(全仓注释卫生类架构防线)合并成一处,交用户裁决后另立小批,禁散入本批。

本批与该条款的关系:§2.8 门集即其首次人工执行;条款落地前,后续各屏设计稿(T-2..T-36)的落地批沿用本 §2.8 门形态作批级判据。
