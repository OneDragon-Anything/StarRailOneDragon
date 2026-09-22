# T-9 选择装备 修法设计(equip_pick)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决+新规范增补待裁决(对抗轨迹:r1 未收敛 7 条→修订→r2 未收敛 1 条低→修订→r3 收敛 0 条;新规范增补 = §3,依据 2026-09-22 两条款符合性重审;增补节对抗:respec-attack-AB 判未收敛 11 条(中 2 低 9)→ 按 11 条定点修订 §3→复攻(respec-attack-AB-r2)残留 3 条一行级→二轮修订→编排侧机械验证收口(2026-09-22,T-37 晨报 G4))。批形态已裁决(2026-09-22 用户裁定):**逐屏实施,本稿只辖本屏(T-9)**——§2.2 裁决面①/§3.4 合流申报随之销项(见 §4.0)。增补二 = §4(选项坐标观察上报 + 动作 op 单文件,用户裁定草案待入册),待无前提对抗
- 发现源:`.debug/progress/2026-09-22-cw-screen-review/reports/T-9-r1.md`(F-1..F-5;总判定高1 中1 低3)。涉事代码与代码内文档以仓库现状为真值;本文定位一律符号锚 / 文档节号(行号不作定位依据,约定 = flow/README.md 卷首)。

## 1. 问题与动机

### F-1 画面 op 决策出口:策略异常/idx 越界双路径盲选回退首卡 + idx 静默钳位(高)

- **现状症状**:`operations/cw_screen/cw_screen_equip_pick.py::CwScreenEquipPick.act` 三条违规路径,全部以「点卡即选」派发并即时上报 = 决策无有效输出下的盲发——①`decide_equip_pick()` 返回 `None`/无 `.idx` 的异型 → AttributeError 落入宽 `except Exception` → 静默盲选首卡;②返回 idx 越界 → `best_i = 0` 静默钳位续跑(流程侧值域改写);③策略侧按契约**故意抛出**的「离屏 None = 观察层失约」ValueError(`strategies/impl/flow.py::_require_slot_options`,flow/README.md §2.2 在册口径)被同一宽 except 吞掉转盲选,契约要求的响亮暴露被流程侧抵消。
- **根因归层(根源两问)**:根在**流程层**——handler 时代「决策失败安全兜底」在画面 op 化迁移中,观察侧失败安全已重立(空表照写/局外跳 report 在册),决策侧兜底未随迁退役;兜底 = 流程侧决策闸门与值域改写,正本反向禁止:op-layer.md §1.1 出口③(「决策无有效输出也走此出口——零盲发」)、§1.3(「非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)」)、flow/README.md §1 决策控制分层铁律(「动作值域过滤必须在策略侧实现……流程侧禁止任何形式的决策闸门与政策判断」)。修法 = 删兜底、换守卫,修根非症状。act 内注释自述「越界防御 = 缺省首卡(判据侧并列同款)」——**本设计显式废弃**:kernel `cw_equip_value.decide_equip_overlay_pick` 的「并列/全无命中 = 首卡」是判据自身对**有效候选**的确定性决策语义,与「决策失败后兜底首卡」两回事(T-9-r1 F-1 差距说明同判),该辩护不成立。
- **解决到哪**:三条路径改响亮暴露——①词表守卫(None/词表外)= 具名 round_fail 零盲发;②idx 越界 = 守卫断言 AssertionError;③删宽 except,策略异常(含离屏失约 ValueError)自然传播 = 出口③异常 fail;派发改直发策略产实例;`screens/equip_pick.md` as-built 申报守卫出口。
- **明确不解决**:空候选/全无命中 = 首卡(kernel `decide_equip_overlay_pick` docstring 在册「并列/全无命中 = 首卡」= 判据自身合法决策语义,审查同判;观察端「空表照写」= equip_pick.md §3 在册);「离屏 None = 观察层失约抛错」口径本体(修法 = 不再被吞,不改口径);策略器返回契约本体(`flow.py::decide_equip_pick` 返回注解 `CwActionPickEquipParam` 在册);无 match 局外兜底分支(kernel 直调,代码自申报豁免面,观察 node 局外跳 report 同款在册);零参决策形态与观察写端(报告 §3 一致项);验证结构零回加(flow/action_ops.md §1)。

### F-2 fields.md 装备选卡域未随 2026-09-21 单相化迭代更新(中)

- **现状症状**:字段级正本三处与代码相反/自相矛盾——①fields.md §4「事件选择(10 屏)」:「余屏(命运卜者/装备三选一/骇入策划)写端未接线=先补档」,而现役 `kernel/cw_action_report/pick_equip.py` = 即时单相写(归一件名命中 = `write_logic` 入栏 + `apply_equip_acquire_consequence` 获得后果链;未解析 = 值不变翻来源留证),骇入策划同批已即时单相(§3.2.23 已登记 pick_planner 升费腿为 `lv999_cost_tier` 写端——§4 与 §3.2.23 内部矛盾);②§3.4.5 单选事件屏行:「各屏选卡写入 chosen_*」「装备三选一=卡名(专档在册,缺卡名读区)」——装备三选一无 chosen_* 写端(选择存证退役),选择效果 = 动作侧即时单相写,读取形态 = 全图 OCR、卡名 y 带过滤 + 槽 x 常量近邻分桶(非 area 读);③§3.2.15 equips「写端(完整清单)」仅列 OpenBox/工具七类/SellBench,同批次新增的两臂零登记——pick_equip 获得链与 pick_planner 装备腿(`kernel/cw_action_report/pick_planner.py` 模块头「equip:件名命中 → 装备入栏(write_logic)+ 获得后果链」,未解析 = `planner_equip_unresolved` 翻来源留证;fields.md 全文仅 §3.2.23 升费腿在册),末句「补给/事件获得的装备不记预期值」豁免同样未划出两屏例外。
- **根因归层**:**约定层(申报面随批同步缺口)**——迭代 2026-09-21-pick-planner-equip-immediate-report 的正本更新清单未辖 fields.md 任何一节(报告 F-2,申报面遗漏非在册欠账);同步义务在册 = docs/develop/harness/iteration-design.md 固定末阶段正本更新。
- **解决到哪**:fields.md 四处补单相写端口径(§4 余屏句/§3.4.5 两处/§3.2.15 两臂与末句/§3.4 头注例外括注)+ 连带 `screens/equip_pick.md` §6 滞后指针句;fields.md 的跨稿重叠面(§3.2.15 末句 ↔ T-5 稿、§4 计数联动 ↔ T-5 稿、§4 策划行 ↔ T-10-r1 F-2、§3.4 头注 ↔ T-8-r1 F-3)逐面归属声明见 §2.3,合并目标句挂 T-37 登记。任务书提示的 flow/action_ops.md §4.5「现盘文字滞后」经审查核验**不存在**(§4.5 PickEquip 行与「上报形态 = 全族即时上报」头注均已随批更新,报告 §0 真值背景/检查①),不立修法。
- **明确不解决**:fields.md §3.4 头注的**判定点枚举半边**(重入裁决点/选择点与各屏现状对齐,归 T-8-r1 F-3 辖内;「其余屏」句的装备/骇入例外括注 = 本稿自清,见 §2.3,同句双改合并文本挂 T-37);§4 策划面滞后本体(「默认不记预期值」总括对策划失真 + §3.2.18 欢愉契约行,归 T-10 稿);§4 节标题计数联动(10→9 屏,归 T-5 稿);命运卜者写端接线本体;「装备三选一与武装箱同屏性待采证」句(审查未列);logic-updates 索引与缺档 pick 专篇(统改权归 T-1 稿,T-4 稿 §2.2 已立口径);sim 写面(sim 无装备选卡画面段,模块 docstring 申报不适用,无写端可补)。

### F-3 equip_pick.md §8 引用已退役符号 + 欠账描述与建档现状不符(低)

- **现状症状**:§8 两处事实失真——①「`_resolve_locked_key_fit` 注册表漂移按未锁保守处理」指向已退役符号(src 全目录零命中),现役语义宿主 = `kernel/cw_equip_value.py::decide_equip_overlay_pick`(「解析失败(注册表漂移)= 按未锁态仅泛用腿」);②「卡位为实拍字面量类常量(**未 area 化**)」——建档现状 = `assets/game_data/screen_info/cw_equip_pick.yml` 已建「卡-装备1/2/3」三个点击区域(三 area 中心 x = 780/1070/1385,与 `CARD_XS=(780,1070,1380)` 前两位精确相等、第三位差 5px,常量取点均落在各 area 内),src 全目录 grep「卡-装备」零命中 = **建档在册而代码未消费**;欠账本身成立且在册,失真的只是「未 area 化」描述。
- **根因归层**:**约定层(申报面漂移)**——判据迁 kernel 与建档两个批次各自落地,§8 未随更。
- **解决到哪**:§8 两处改写为现役口径;连带 `cw_screen_equip_pick.py:59-60` 类常量上方注释同款「未 area 化」失真一并改写(审查未单列,同一事实断言,随批一并)。
- **明确不解决**:卡位 area 化消费改造(行为变更,坐标单一源清点挂账项在册,归实机批);kernel 判据本体。

### F-4 CwActionPickEquipOp.run 终态消息「结果经旁路回传」与实现不符(低)

- **现状症状**:`operations/cw_op/cw_overlay_pick_action.py::CwActionPickEquipOp.run` 末句 `round_success('装备选卡点击已发(结果经旁路回传)')` + run docstring「轮次结果经旁路回传恒成功」——本屏点卡即选、无 `emit_overlay_confirm` 末步,`env.round_result` 在本 run 体从未赋值,宿主画面 op 派发后亦不消费;消息向读者申报了一条不存在的旁路路径。同形态还有 PickBoxCard/PickStarTome/PickExpertInvite 三类(本屏域外)。
- **根因归层**:**约定层(注释/消息面)**——即时单相迁移改写了上报形态,轮次结果消息沿用两相时代的旁路措辞。
- **解决到哪**:消息与 run docstring 改为即时上报口径(对齐同族 supply/planner 行文)。
- **明确不解决**:域外三类消息面(归 T-37 随家族批一并核);`OverlayPickExecEnv.round_result` 字段注释(对其余真消费方仍准确)。

### F-5 注释出处弱索引:「删除波 1」「S13 裁定」无持久指针(低)

- **现状症状**:`cw_screen_equip_pick.py` 模块 docstring 两处——:31「选择存证已随删除波 1 退役」(「删除波 1」全仓无持久锚,读者无法重建指哪次清理);:19「S13 裁定语义随判据在 kernel 注释在案」(编号与其指向的 kernel 在册表述编号不接——`cw_equip_value.py` 模块头作「supply-selection 迭代裁定 5/6」、函数 docstring 作「S13 裁定」,追链靠猜)。
- **根因归层**:**约定层(注释纪律)**——AGENTS.md §8「引用必须是持久索引……出处要么写成持久索引(ADR-NNNN、文件路径、符号名),要么写成纯语义描述」。
- **解决到哪**:两处改写为纯语义描述 + 符号锚指针。
- **明确不解决**:`cw_equip_value.py` 内部两处编号表述不接(判据文件非本稿涉事面,归 T-37 汇总);「pick-op-unify 批」「普查迁移批 2」等泛化批名(正本文档同用的在册可溯形态,审查已判不计)。

### 在册核对结论

审查报告 §3 八项一致面(即时单相三方核验/派发即终结/决策形态正面半/容器写纪律/观察上报/动作 op 行/equip_pick.md 九节主体/退役零残留)核对通过,不立修法;本稿全部修法不回退任何一致项。

## 2. 方案

### 2.1 F-1 修法(核心)

**代码面**(`operations/cw_screen/cw_screen_equip_pick.py::CwScreenEquipPick.act`):

1. 删 `best_i = 0` 默认初始化、宽 `try/except Exception` 全体(含 `log.warning` 兜底日志)与钳位句 `if not (0 <= best_i < len(self.CARD_XS)): best_i = 0`。
2. **守卫①(决策无有效输出 = 具名 fail 零盲发)**——决策调用之后、任何组装/派发之前:

   ```python
   act = _match.strategy.decide_equip_pick()
   if not isinstance(act, CwActionPickEquipParam):
       return self.round_fail(
           f'decide_equip_pick 决策无有效输出(词表外/None): {act!r}')
   ```

   依据:op-layer.md §1.1 出口③「决策无有效输出也走此出口——零盲发」(此出口 = 异常 fail);先例 = 备战决策循环「非 CwAction 返回 → 具名 fail 留证」(flow/README.md §2.2 decide_prep_screen 行)与同族遭遇修法(changes/2026-09-22-screen-review/encounter.md §2.1 守卫①,同形态)。消息含策略器返回原值(repr)= 留证,不另加独立日志行(round_fail 消息经框架节点状态日志落盘)。round_fail = op fail 交回外循环,受外环连续 fail 重派网兜底(flow/README.md §4:同一定分发 op 连续 fail 显式停)——确定性 bug 必响亮且可观测。`CwActionPickEquipParam` 本文件已在 import 面,零新增依赖。
3. **守卫②(pick idx 越界 = 守卫断言恒炸)**——紧随守卫①:

   ```python
   if not (0 <= act.idx < len(self.CARD_XS)):
       raise AssertionError(
           f'[cw-equip-pick] pick idx 越界(策略器 bug,禁钳位): '
           f'idx={act.idx} 槽数={len(self.CARD_XS)} act={act!r}')
   ```

   依据:op-layer.md §1.3「执行侧只余守卫断言——防 bug 路栏而非控制流分支,非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)」;同款先例 = `operations/cw_op/cw_action_registry.py::action_op_class_for_type`(词表外 AssertionError 响亮暴露)。界 = `len(self.CARD_XS)`(点击目标数组物理槽数,现值 3;与候选槽 `equip_pick_opts` 恒 3 同长——观察写端 `_read_cards` 恒返 3 桶,equip_pick.md §3;idx 坐标系 = 容器槽下标,`kernel/cw_vocab.py::CwActionPickEquipParam` [索引定义] 在册)。落点语义 = 框架节点异常收口(留证截图 → `node_max_retry_times=5` 预算耗尽 op fail;该预算「现役值仅框架异常路径消费」在册,equip_pick.md §2)——确定性 bug 每轮必炸,预算内有界响亮终止。
4. **删宽 except = 路径③修法**:决策调用不再包 try——策略异常(含 `_require_slot_options` 按契约故意抛出的离屏失约 ValueError)自然传播 = 出口③异常 fail,契约要求的响亮暴露恢复;框架异常路径即出口③现役实现形态(落点同上)。依据:op-layer.md §1.1 出口③「策略异常/执行异常,错误传播交外循环」。
5. **norm_item 载荷原位补齐 + 直发策略产实例**(守卫②后):

   ```python
   act.norm_item = normalize_registry_equip_name(
       texts[act.idx] if 0 <= act.idx < len(texts) else '')
   best_i = act.idx
   ```

   派发改 `action_op_for(act, self.ctx, _env).execute()`(删 `_param = CwActionPickEquipParam(...)` 重建行)。norm_item 现算点不动 = 决策半(flow/action_ops.md §4.5 PickEquip 行「`norm_item` 由决策半经 `normalize_registry_equip_name` 归一现算」在册口径);`norm_item` = `action_key_exclude` 元数据载荷(`kernel/cw_vocab.py::CwActionPickEquipParam` 字段在册),非决策值,idx 单一源 = 策略产值零改写。守卫①已收窄类型,直发无分派歧义(注册表按 isinstance 解析,词表内无该类型父类行)。下游消费面不变:`env = OverlayPickExecEnv(op=self, idx=act.idx, target=Point(self.CARD_XS[best_i], self.CARD_Y))`;`log.info` 消息字段改引 `best_i`/`act.norm_item`。
6. 注释废弃与替换:删「越界防御 = 缺省首卡(判据侧并列同款)」「策略失败 fallback 第1张」「派发实例携真实选中下标与归一件名(上报 param 即真实选择;越界防御/策略异常 fallback = 0)」三处兜底自述(废弃理由见 §1 F-1),原位替换守卫语义注:词表外/None = 具名 fail 零盲发;idx 越界 = 守卫断言;派发实例 = 策略产值(norm_item 决策半载荷原位补齐)。无 match 局外兜底 else 分支**原样保留**(kernel 直调未锁态语义,豁免面在册)。
7. docstring 同步:act docstring 与模块 docstring 形态段各补一句守卫出口——「决策返回 None/词表外 = 具名 round_fail 零盲发;pick idx 越界 = 守卫断言 AssertionError;策略异常自然传播(离屏失约 ValueError 不再被吞);两守卫均在派发前、零点击」;模块 docstring「决策动作 node = 零参决策 → 组装 param(idx + 注册表分层归一 norm_item)」句改「零参决策 → 守卫 → 直发策略产实例(norm_item 决策半载荷原位补齐)」。**零容器写保持**:fail/异常路径不新增 kernel `_emit_defect` 调用(该面 = 观察对账缺陷台账,kernel 侧专用);留证 = 日志 + round_fail/断言消息。

**文档面**(`docs/develop/sr_od/application/currency_war/screens/equip_pick.md` as-built 更新点):

- **§2 画面形态声明**:「决策动作 node = 零参决策 …」句后补守卫出口句(口径同上,含「选卡派发 = 策略产实例直发,流程侧零值域改写」)。
- **§4 动作面**:选卡链伪码块改为——

  ```
  act = decide_equip_pick()(零参;候选读容器 equip_pick_opts 槽)
  守卫①:act 非 CwActionPickEquipParam(None/词表外)→ round_fail(含原值)零盲发
  守卫②:act.idx 越界 [0, 3) → AssertionError(禁钳位)
  norm_item = normalize_registry_equip_name(texts[act.idx])(决策半载荷原位补齐)
  target = (槽 x 常量[act.idx], 卡名带 y 常量 280) → 直发 act 派发
    (动作 op 内:target mouse_move + click → 1.2s → 即时自上报;机械交回,零判效)
  → 派发即 round_success 终结交回
  ```

  对照表 `CwActionPickEquipOp` 行「发出方式」列补「派发实例 = 策略产 `CwActionPickEquipParam`(两守卫后 norm_item 原位补齐)」;表末补一行:`| (决策无有效输出/pick idx 越界,非动作) | — | — | 守卫 fail:词表外/None = round_fail(含原值)、idx 越界 = AssertionError;零点击零派发,交回外循环 |`。
- **§5 终结与交回表**补一行:`| 决策无有效输出/pick idx 越界 | 守卫 fail(op FAIL) | round_fail / 框架异常路径(留证截图 + 预算耗尽)交回外循环;连续 fail 由外环重派网兜底(flow/README §4) |`。
- **§8 守卫与防线**补两条:①决策词表守卫:decide_equip_pick 返回 None/词表外 = 具名 round_fail 零盲发——原「越界防御/策略异常 fallback = 0」退役申报;②值域守卫:pick idx 越界 = 守卫断言 AssertionError——原「静默钳 0」退役申报。

**测试锁**(实现随功能写,锁设计约定 = sr-od-test/README.md;文件 = `sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py` 装备臂):

- 现役锁 `test_equip_act_decides_from_container_and_dispatch_terminal` 的决策桩 `SimpleNamespace(idx=1, reason='stub')` **必须换真词表类** `CwActionPickEquipParam(idx=1, reason='stub')`——SimpleNamespace 桩 = 旧钳位形态伴生物,守卫①落地后词表外返回即 fail 出口,旧桩会打红现役锁;其余断言面(零参恰一次/单次派发携真实 idx/norm_item 归一命中/定位点/派发即 round_success)不变(直发后 `dispatches[0].param` 即桩实例,norm_item 断言仍成立)。
- 补两锁:①决策返回 `None`/词表外对象 → round_fail 且零点击零派发;②决策返回 `CwActionPickEquipParam(idx=3)`(越界)→ AssertionError 且零派发。
- 落码时全量 grep `decide_equip_pick` 桩消费面复核:该符号在 sr-od-test 现役命中仅两处——test_cw_screen_two_node_family.py(决策桩,见上)、test_cw_overlay_judgement_migration.py(锁策略契约本体,策略实现返回真词表类,不受影响);test_cw_unified_action_4.py 消费 `CwActionPickEquipOp` 注册行(点击链/上报桩),不经 `decide_equip_pick`,不在本符号复核面内、不受影响。

**关键取舍**:

1. **路径③ = 删宽 except 让传播,而非 try/except 内转 round_fail**:任何 `except Exception` 形态都会再把「策略侧按契约故意抛出的离屏失约 ValueError」吞成盲选——这正是被查处的第三条路径;出口③对策略异常的现役实现形态 = 异常传播交框架节点异常收口,传播即合规,零新增结构。
2. **守卫①用 round_fail 而非任由 AttributeError 自然炸出**:None/异型返回现形态会以 `AttributeError: .idx` 炸出,技术上「响亮」但消息无策略器语义(读者需从 NoneType 反推);出口③明文该情形走异常 fail 出口,具名 fail 带原值 repr 直接指认,且与遭遇修法同形态(家族一致)。
3. **直发 + 原位补载荷,不重建实例**:重建 = 第二构造点,`CwActionPickEquipParam` 增字段时拷贝构造漏字段漂移;norm_item 上移策略器 = 改决策入口契约(strategy-docs/13_pick_family.md + action_ops.md §4.5「由决策半现算」在册口径)= 契约改版超出本发现辖域。直发后「派发实例 = 策略产值」与遭遇修法同型;norm_item = 决策半在册注入点的载荷补齐,非决策改写。
4. **无 match 局外兜底分支不动**:代码自申报豁免面(kernel 直调未锁态语义),观察 node 局外跳 report 同款豁免在册(equip_pick.md §3),审查未列为发现。
5. **判据侧「并列/全无命中 = 首卡」不动**:kernel 判据对有效候选的确定性 tie-break(含空桶/空表输入)= 判据自身决策语义;§1.3 禁的是流程侧静默降级,不是策略判据的确定性排序(T-9-r1 F-1 差距说明同判)。

### 2.2 F-1 家族联动面(pick 族画面 op 决策出口守卫)

- **家族性模式认定**:同一模式三次独立查出——遭遇(T-4-r1 F-1:词表外穿透盲选默认 idx0 + 钳位)、盛会之星(T-8-r1 F-1:空候选/无 match 屏内自定 idx0 盲发 + 钳位)、本屏(T-9 F-1:宽 except 吞异常盲选 + 钳位)。共同根 = handler 时代「决策失败安全兜底」在画面 op 化迁移中,观察侧失败安全已各自重立(空候选零点击/离屏抛错),决策侧兜底残留为流程侧决策闸门与值域改写,违 op-layer.md §1.1 出口③/§1.3/flow/README.md §1 铁律。跨件半问已过:三件同根,但根的载体是各屏 act 内残留代码而非更高层抽象缺位(画面 op 层「不设共享基类/端口」= op-layer.md §4 在册口径),故不升架构级设计件,以**族级形态统一**收敛。
- **族级统一修法建议(形态统一,不建共享代码)**:每个 pick 族画面 op 的决策动作 node 在「调策略器」与「派发」之间内联两守卫——①词表守卫:返回 None/词表外 = 具名 round_fail 零盲发(消息含策略器原值 repr);②值域守卫:pick idx 越界 = 守卫断言 AssertionError(禁钳位);删全部默认 idx 初始化/钳位句/宽 except;两守卫均在任何点击之前(派发即点击,越界放行 = 不可逆消耗)。不建共享守卫函数:两守卫各 2-3 行,各屏词表类/槽数/日志 tag 不同,共享 helper 的去重收益低于新跨屏依赖与消息语境损失;先例 = encounter.md §2.1 同款内联形态。
- **兄弟屏清单(已查出)**:`operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter.act`(T-4-r1.md F-1;修法 = 同目录 encounter.md §2.1)、`operations/cw_screen/cw_screen_megastar.py::CwScreenMegastar._do_action`(T-8-r1.md F-1;设计稿 megastar.md 同批并行)、`operations/cw_screen/cw_screen_equip_pick.py::CwScreenEquipPick.act`(本稿 §2.1)。其余 pick 族屏(伙伴/策划/卜者/祈愿/星徽/邀请函/武装箱/投资两屏/补给)同模式核查归各屏审查任务(T-5/T-6/T-7/T-10..T-16),本稿不代查不预设。
- **归口 T-37 裁决面**:①三屏 F-1 修法是否合并为一个实施批——三稿语义互不依赖,可独立实施;合并批优势 = 同形态一次过全量锁,且 `OverlayPickExecEnv.idx` 字段注释「决策半现算快照(钳位后生效值)」(`operations/cw_op/cw_overlay_pick_action.py` 字段 [索引定义],pick 族共享 env)的陈旧措辞可随家族批一次改净——单屏改会让共享注释与未修屏临时不一致,故本稿 §2.1 不动它,挂本裁决面;②op-layer.md §1.3 守卫登记 = **无条件默认动作,非开放裁决**:本稿落地批正本更新阶段必登记本屏两条守卫出口(词表守卫/值域守卫,§2.1 文档面 screens/equip_pick.md §8 同批一并;现役 §1.3 守卫清单仅 `guard_proposal_vs_expected` 单例枚举,不登记 = 守卫落地后正本缺员)——T-37 仅裁族级合并实施时是否把逐屏条目改写为族级统一条目,不存在无人登记路径。
- **明确不联动**:kernel 判据侧 tie-break(各屏判据自身的合法决策语义,任何屏不得借「家族统一」改判据);已迁移屏的派发即终结与即时上报形态(报告 §3 一致项,与守卫无关)。

### 2.3 F-2 修法

**`docs/develop/sr_od/application/currency_war/game_state/fields.md` 四处**(目标口径,依据就地标注;fields.md = 跨稿共享面,逐面归属声明见本节末「交叉面归属」):

- **§4「事件选择(10 屏)」余屏句**:「余屏(命运卜者/装备三选一/骇入策划)写端未接线=先补档」改写为——「命运卜者写端未接线=先补档。装备三选一无 chosen_\* 写端(选择存证已退役)/骇入策划无 chosen_hack 写端(写端未接线,字段位申报不变),选择效果 = **动作侧即时单相写**(用户裁定 = flow/action_ops.md §1 增补 2):装备三选一写端 = `kernel/cw_action_report/pick_equip.py`(归一件名命中 = equips 入栏 + 获得后果链,未解析 = 值不变翻来源留证,§3.2.15);骇入策划写端 = `kernel/cw_action_report/pick_planner.py` 腿型分派(equip 腿 = 装备入栏 + 获得后果链,升费腿 = `lv999_cost_tier` 档行,§3.2.23)」。依据 = pick_equip.py 模块头/函数体(即时单相三方一致,报告 §3.1)、pick_planner.py 模块头(「equip:件名命中 → 装备入栏(write_logic)+ 获得后果链」,未解析 = `planner_equip_unresolved` 翻来源留证)+ §3.2.23 现文(§4 与 §3.2.23 的内部矛盾由此消解);状态括注按屏分列的出处——装备退役 = `operations/cw_screen/cw_screen_equip_pick.py` 模块 docstring「选择存证已随删除波 1 退役」+ equip_pick.md §6,骇入策划未接线 = `screens/planner.md` §6「该字段位申报不变」+ 开放设计注(chosen_hack 字段位仍无写端,单相上报写的是腿效果域非选择存证)+ T-10-r1 F-2 ②(「chosen_hack 写端未接线」部分仍真)——两屏状态不同质(装备 = 曾接后拆,骇入策划 = 从未接线),括注禁并写。遭遇臂句及其后全部不动。**同段前置依赖(在册认领面,本稿不动)**:节标题「(10 屏)」计数与首句名单摘「补给/」的联动 = T-5 稿 §2.3(2) 认领(本稿引用节名按其修后「9 屏」口径理解,其未落地前按现盘文本);「默认不记预期值」总括对策划面的失真与 §3.2.18 欢愉契约行 = T-10-r1.md F-2 认领面,归 T-10 稿。
- **§3.4.5 单选事件屏行**:①「装备三选一=卡名(专档在册,缺卡名读区)」→「装备三选一=卡名(全图 OCR,卡名 y 带过滤 + 槽 x 常量近邻分桶,`CwScreenEquipPickObs.options` 写槽 `equip_pick_opts`,空表照写;非 area 读);选择效果 = 动作侧即时单相写(§4 事件选择)」——读取机制按代码真值申报(`operations/cw_screen/cw_screen_equip_pick.py::_read_cards`:y 带构成过滤、分桶维度 = 槽 x 常量近邻;「缺卡名读区=接线缺口」的旧框架随单相化失效);②收束句「各屏选卡写入 chosen_\*」→「各屏选卡写入 chosen_\*(命运卜者写端未接线 = 先补档,§4 事件选择;装备三选一/骇入策划无 chosen_\* 写端 = 动作侧即时单相效果写,见 §4 事件选择)」——例外补足三块,防修后收束句仍隐含「命运卜者写入 chosen_\*」与同稿 §4 改写同文档矛盾(T-12-r1 §3.2 证实卜者零写点 = 真实现状)。
- **§3.2.15 装备库存 equips**:①逻辑写端清单「SellBench 卖出角色(装备全量回区)」后**同批追加两臂**——「PickEquip 装备三选一动作上报(`CwActionPickEquipOp` 自上报 = 容器写:归一件名命中 = `write_logic` 入栏 + `apply_equip_acquire_consequence` 获得后果链同源写;未解析 = `write_logic_rand` 值不变翻来源 + `pick_equip_name_unresolved` 留证禁猜;装备区未观察态 = 入栏跳写等观察);PickPlanner 骇入策划 equip 腿(`report_action_pick_planner_param` 腿型分派:件名命中 = 装备入栏 + 获得后果链;未解析 = 值不变翻来源 + `planner_equip_unresolved` 留证)」(依据 = pick_equip.py 模块头写序 ①②、pick_planner.py 模块头 equip 腿与 `_apply_equip_leg`;同批次同性质写端一次登齐,防「写端(完整清单)」修后即缺员);②末句豁免句——**与 T-5 稿 §2.3(1) 同句双认领,合并目标句如下(挂 T-37 登记,实施以本句为单一文本)**:「补给获得的装备 = 即时预期值写(上行 PickSupply 腿,`flow/action_ops.md` §4.5 即时单相,账面恒归一规范名);装备三选一/骇入策划 equip 腿获得的装备 = 即时预期值写(写端见上 PickEquip/PickPlanner 臂);其余事件获得的装备不记预期值,经观察覆盖收口(§4.1 豁免)」——补给半边逐字沿用 T-5 稿目标文本(其施工权在册不变),装备域两例外为本稿追加;尾部连接词「遭遇等事件」改「其余事件」= 对齐性微调(豁免集合语义不变,减去三个已单列屏),以 T-37 登记版为实施文本;遭遇仍真留豁免(T-5 稿关键取舍 4 同判)。
- **§3.4 头注「其余屏 = 重入裁决点单次逻辑写入」句**:追加例外括注——「其余屏(巨星/伙伴/祈愿/星徽等)= 重入裁决点单次逻辑写入(装备三选一/骇入策划无 chosen_\* 写端,效果 = 动作侧即时单相写,见 §3.4.5/§4)」——防修后 §3.4.5/§4 与头注正面矛盾;该句的**判定点枚举半边**(巨星选择点等与各屏现状对齐)归 T-8-r1 F-3 辖内,同句双改合并文本挂 T-37 登记。

**交叉面归属(fields.md 跨稿共享面,防双源)**:§3.2.15 末句豁免句 = T-5 稿 §2.3(1) 与本稿双认领,合并目标句单一文本挂 T-37(上条②,补给半边施工权 = T-5 稿、装备域例外 = 本稿);§4 节标题/首句名单计数联动 = T-5 稿;§4 策划面滞后(「默认不记预期值」总括失真/§3.2.18 欢愉契约行)= T-10-r1 F-2 归 T-10 稿;§3.4 头注判定点枚举 = T-8-r1 F-3;本稿辖面 = §4 余屏句 + §3.4.5 两处 + §3.2.15 两臂 + §3.4 头注例外括注。T-37 汇总时按本节合并文本落定,后到稿不得另立第二套目标文本。

**连带 `screens/equip_pick.md` §6**:指针句「字段节 = fields.md §3.4.5(「装备三选一」行,写端未接线申报)/ §4「事件选择」」→「字段节 = fields.md §3.2.15(equips 写端清单)/ §3.4.5(「装备三选一」行)/ §4「事件选择」(装备获得 = 即时单相写端口径)」;§6 首句现文(无 chosen_\* 写端 + 即时一口写)已与代码一致,不动。

**关键取舍**:①修法 = 口径补写,不新增字段、不复活选择存证——装备选择效果现役有真实写端,缺口纯在申报面;「写端未接线」句若仅删不补,读者失去「装备获得怎么进容器」的索引,故逐处补正本指针。②§3.2.15 追加 PickPlanner 装备腿而非让渡——该臂与 pick_equip 同批次(2026-09-21-pick-planner-equip-immediate-report)同性质(equips 逻辑写端),且全部在册发现(T-10-r1 F-2 辖 §3.2.18/§4、T-5 辖补给臂与 §3.2.5)均不含 §3.2.15 清单段,默认让渡 = 无人施工;本稿正以「补齐写端清单」为目标,留缺员即自我矛盾。③末句豁免句对齐 T-5 而非各写半句——同句两份目标文本 = 合并实施时替换基准句失配,实现者被迫自行合并(违 iteration-design.md §5 硬规则 2);以 T-5 在册文本为补给半边基底、本稿只追加装备域例外,单一合并句挂 T-37 登记,双源消失。

### 2.4 F-3 修法

**`screens/equip_pick.md` §8 两处改写**:

- ①「`_resolve_locked_key_fit` 注册表漂移按未锁保守处理,漏提权非错提权」→「锁线解析失败(注册表漂移)= `kernel/cw_equip_value.py::decide_equip_overlay_pick` 按未锁态仅泛用腿(保守向:漏提权非错提权)」——符号锚换现役宿主,语义照 kernel docstring。
- ②「卡位为实拍字面量类常量(**未 area 化**,坐标单一源清点挂账项;布局变更需实拍重校)」→「卡位点击区域已建档(`cw_equip_pick.yml` 卡-装备1/2/3;三 area 中心 x = 780/1070/1385,与 `CARD_XS` 前两位精确相等、第三位差 5px,常量取点均落在各 area 内)而代码未消费,点击点 = 字面量常量现算——坐标单一真相源缺口仍在(清点挂账项,消费改造归实机批);布局变更需实拍重校」。

**连带 `operations/cw_screen/cw_screen_equip_pick.py` 类常量上方注释**:「⚠️ 待实机核(坐标单一源清点项):以下卡位为 2026-08-20 实拍字面量,未 area 化(本批实机纪律不可测,建档 area 化挂账实机批);布局变更需实拍重校。」→「⚠️ 待实机核(坐标单一源清点项):以下卡位为 2026-08-20 实拍字面量;点击区域已建档(卡-装备1/2/3,三 area 中心 x = 780/1070/1385,常量取点均落在各 area 内)而代码未消费,消费改造挂账实机批;布局变更需实拍重校。」

**关键取舍**:只改描述、不消费建档区域——area 化消费 = 行为变更(取点几何从常量换 area 中心),审查明判「本条只判描述失真」;欠账本体(单一真相源缺口)如实保留挂账,防「改描述 = 消欠账」的假闭环。

### 2.5 F-4 修法

**`operations/cw_op/cw_overlay_pick_action.py::CwActionPickEquipOp`** 两处:

- run 末句 `round_success('装备选卡点击已发(结果经旁路回传)')` → `round_success('装备选卡点击已发(结果已即时上报)')`(对齐同族即时上报行文先例:`CwActionPickSupplyOp`「补给选择确认链已发(结果已即时上报)」/`CwActionPickPlannerOp`「策划选择确认链已发(结果已即时上报)」)。
- run docstring「机械执行(点卡即选 + 固定等待;轮次结果经旁路回传恒成功)。」→「机械执行(点卡即选 + 固定等待 → 立即上报完整结果;本 op 无确认链末步,不产旁路产物——`env.round_result` 保持 None)。」

**关键取舍**:只修本屏行——旁路措辞在点卡即选族(BoxCard/StarTome/ExpertInvite)同形误用属域外,归 T-37 随家族批一并核;`OverlayPickExecEnv.round_result` 字段注释对其余真消费方(encounter/planner/invest/fortune/wish/partner)仍准确,不动。

### 2.6 F-5 修法

**`operations/cw_screen/cw_screen_equip_pick.py` 模块 docstring 两处**(AGENTS.md §8:出处 = 持久索引 ∨ 纯语义描述,二者取一):

- 「本屏无 chosen_\* 写端(选择存证已随删除波 1 退役)。」→「本屏无 chosen_\* 写端(选择效果 = 动作侧即时单相写,写端 = `kernel/cw_action_report/pick_equip.py`;选择存证通道已退役)。」——「删除波 1」批次指称删除,现役语义 + 符号锚自足。
- 「locked_comp 意向读随判据迁策略侧(策略入口自 self.state 取值注入 kernel 参数);S13 裁定语义随判据在 kernel 注释在案:」→「locked_comp 意向读由策略入口自 self.state 取值注入 kernel 参数;未锁线不绑囤牌方向的裁定语义 = 判据本体行为(锁线解析失败按未锁态仅泛用腿,保守向漏提权非错提权),单一源 = `kernel/cw_equip_value.py::decide_equip_overlay_pick` docstring:」——「S13」编号删除,改纯语义描述 + 符号锚;「随判据迁策略侧」变更史短语一并收敛为现役形态陈述。

**关键取舍**:选「纯语义描述」而非补一个持久索引——两处指向的裁定本体已由 kernel docstring 以行为语义完整承载(「解析失败按未锁态仅泛用腿」),语义自足后编号无需存在;kernel 内部「S13 裁定」vs「裁定 5/6」编号不接是另一处面(判据文件非本稿涉事面),归 T-37。

### 2.7 实施文件面全集(合并实施对账用)

- **行为变更(仅 F-1)+ 同文件注释面(F-3 连带/F-5)**:`operations/cw_screen/cw_screen_equip_pick.py`(act 守卫/直发/docstring;类常量注释;模块 docstring 两处)。
- **测试(F-1)**:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(决策桩换真词表类 + 补两锁)。
- **代码内文档/消息面(F-4,零行为变更)**:`operations/cw_op/cw_overlay_pick_action.py`(`CwActionPickEquipOp` run docstring + 终态消息字符串)。
- **正本文档(F-1 as-built/F-2/F-3/F-1 家族登记)**:`screens/equip_pick.md`、`game_state/fields.md`(§4 余屏句/§3.4.5 两处/§3.2.15 两臂与末句/§3.4 头注例外括注)、`screens/op-layer.md`(§1.3 守卫清单补本屏两条守卫出口 = 本稿落地批正本更新阶段**必登记**,§2.2 裁决面②)。
- **跨稿共享文件对账(fields.md,归属声明 = §2.3 交叉面归属)**:§3.2.15 末句合并目标句挂 T-37 登记(补给半边施工权 = T-5 稿 §2.3(1),装备域例外 = 本稿);§4 节标题/首句名单计数联动 = T-5 稿;§4 策划面滞后 = T-10 稿;§3.4 头注判定点枚举 = T-8-r1 F-3(同句双改合并文本挂 T-37)。
- 其余文件零触碰(F-1 家族联动面兄弟屏归各自稿/T-37;`OverlayPickExecEnv.idx` 字段注释挂 §2.2 T-37 裁决面;action_ops.md §4.5 经核验无修法面);F-2..F-5 零行为变更。

## 3. 新规范增补(2026-09-22 两条款)

> **基准** = 正本两条新条款(`screens/op-layer.md` §1.1,均用户裁定 2026-09-22,commit 2f35d4011 入正本):**:34 观察标准化门**——观察内容在所属域存在标准注册数据(名字类)时,观察 node 必须在观察时转换成标准注册数据再上报(①形变归一后精确匹配;②不中再 LCS 相似,`one_dragon.utils.str_utils::find_best_match_by_lcs`;两段皆不中 = 转换失败);任一候选转换失败 = 观察失败,观察 node round_fail 早退、零写零上报;多候选命中同一注册名(选项互斥屏)= 识别质量不足以区分,同判转换失败;标准化后动作上报只携 idx,动作/上报层零名字转换;欠账逐批收敛,禁新增未标准化直报。**:36 画面 op 不支持局外单独调用**——不支持脱离对局(`cw_match` 缺席)单独调用调试,此类支持代码不做;无 match(局外)= 零决策零点击 round_success 终结交回(遭遇屏在册先例同款),不设任何兜底决策路径;先例代码锚 = `operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter.act`(:156-165,`match is None` → `round_success('候选读缺/局外,零点击终结交回重读', wait=1.5)`)。
>
> 增补源 = 新规范符合性重审报告 `.debug/progress/2026-09-22-cw-screen-review/reports/respec-T9-T15.md`(本屏 = §2.1,增补 A/B/C 三点;跨屏共性 = §2.8)。时序:本稿对抗收敛在先、两条款入正本在后,增补 = 在已收敛修法(F-1 守卫化主体)上叠加申报与改写,不推翻主体、不回退 §1 在册核对结论;本节不改 §0–§2 正文,正文需连带改写处在本节逐字给目标文本与落点节号,归实施批按本节落笔。

### 3.1 增补 A(:36 局外支改零决策零点击 round_success 终结交回)

**结论**:现役 `CwScreenEquipPick.act` 无 match else 支(kernel 直调 `decide_equip_overlay_pick(list(texts))` → `best_i` → 组装派发,代码 `cw_screen_equip_pick.py:129-135`)为 :36 违规欠账——该支 = 决策 + 点击,且正文三处「代码自申报豁免面在册/原样保留」stance 被 :36 否定(:36 为后立特别条款,明文「此类支持代码不做」,不存在代码自申报豁免的判法)。改法 = 零决策零点击 round_success 终结交回;kernel 判据本体(`kernel/cw_equip_value.py::decide_equip_overlay_pick`)与策略器入口(`decide_equip_pick`)零触碰。

- **落点 1(§2.1 代码面第 6 点尾句)**——现文「无 match 局外兜底 else 分支**原样保留**(kernel 直调未锁态语义,豁免面在册)。」整句替换为:

  > 无 match 局外兜底 else 分支按 op-layer.md §1.1 :36 改零决策零点击 round_success 终结交回(先例 = `cw_screen_encounter.py::CwScreenEncounter.act`),目标代码 else 臂删除 kernel 直调、改 `return self.round_success('局外无 match,零决策零点击终结交回')`(置于守卫①同位)。

- **落点 2(§2.1 关键取舍 4)**——现文全条替换为:

  > 4. **无 match 局外兜底分支改写(原「不动」立场随 :36 废弃)**:else 分支按 op-layer.md §1.1 :36 改零决策零点击 round_success 终结交回(先例 = `cw_screen_encounter.py::CwScreenEncounter.act` :156-165,`match is None` → `round_success('候选读缺/局外,零点击终结交回重读', wait=1.5)`),目标代码 else 臂删除 kernel 直调、改 `return self.round_success('局外无 match,零决策零点击终结交回')`(置于守卫①同位);观察 node 局外跳 report 不冲突,继续有效(op-layer.md §1.1 :18 在册)。

- **落点 3(§1 F-1 明确不解决 无 match 条)**——现文「无 match 局外兜底分支(kernel 直调,代码自申报豁免面,观察 node 局外跳 report 同款在册);」替换为:

  > 无 match 局外兜底分支 = op-layer.md §1.1 :36 违规欠账,不在「不解决」豁免之列(改法见 §3.1 = 零决策零点击 round_success 终结交回);观察 node 局外跳 report 继续有效(op-layer.md §1.1 :18 在册);

- **落点 4(§2.1 测试锁,追加一条)**:

  > - 补局外臂锁(:36):`cw_match=None`(观察桩照常,决策桩与派发桩零调用断言)→ act 返回 round_success(零决策零点击终结交回)、零派发零点击——共享测试锁模板(族级统一形态,§3.4)。

- **落点 5(§2.7 实施文件面,三处扩容)**——①首条 bullet 现文「- **行为变更(仅 F-1)+ 同文件注释面(F-3 连带/F-5)**:`operations/cw_screen/cw_screen_equip_pick.py`(act 守卫/直发/docstring;类常量注释;模块 docstring 两处)。」替换为:

  > - **行为变更(F-1 + :36 局外支改写,§3.1)+ 同文件注释面(F-3 连带/F-5/:36 连带尾句)**:`operations/cw_screen/cw_screen_equip_pick.py`(act 守卫/直发/无 match else 臂改写/docstring;类常量注释;模块 docstring 两处;observe docstring 尾句「决策走 kernel 直调防御分支,分支原样」连带改写——「分支原样」删除,改为「决策面无局外兜底,无 match = 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,遭遇屏先例同款),守卫见 act」(现役形态申报,fortune.md 3.2-f observe 句同款句式;本屏 :36 行为改写与 F-1 两守卫同批落地〔§3.4〕,不取「欠账待改」过渡文本,落笔即终态);该连带站点 respec 报告未单列,依其对 T-10 同型句的判语(逐字「T-10 站点清单未列,文件已在施工面,连带收录」)同判收录,文件已在 §2.7 施工面)。

  ②「测试(F-1)」bullet 现文「(决策桩换真词表类 + 补两锁)」替换为「(决策桩换真词表类 + 补两锁 + 局外臂锁,§3.1 落点 4)」。③screens/equip_pick.md as-built 的局外支出口申报随族级批落地批更新(已在 §2.7 正本文档 face 内,无新增文件面)。

- **落点 6(§2.1 代码面第 7 点 docstring 同步句族,补 :36 局外出口句)**——act docstring 补句「决策返回 None/词表外 = 具名 round_fail 零盲发;pick idx 越界 = 守卫断言 AssertionError;策略异常自然传播(离屏失约 ValueError 不再被吞);两守卫均在派发前、零点击」句尾「两守卫均在派发前、零点击」后加「;无 match(局外)= 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36)」;模块 docstring 形态段改句「零参决策 → 守卫 → 直发策略产实例(norm_item 决策半载荷原位补齐)」句尾同加该局外出口半句——:36 行为改写同批落地后,代码 docstring 出口枚举补齐局外出口,与落点 5 observe docstring 现役形态改写、§2.1 文档面 screens as-built 申报三方同形,对齐 partner 3.1-b / fortune 3.1-e 的 docstring 同步句族形态(不留「as-built 有申报、代码 docstring 无」的半新半旧)。

依据(respec-T9-T15.md §2.1 Q2 增补 A + Q3)::36 明文「无 match(局外)= 零决策零点击 round_success 终结交回……不设任何兜底决策路径」;「豁免面在册」自申报判法被 :36 否定(同法判例 = T-15-r1 F-1 对「防御路径豁免在案」自述的否决);观察侧跳 report 的在册依据 = op-layer.md §1.1 :18(「report_screen_xxx_obs(gs, obs) 落容器(match/gs 缺席的局外兜底路径跳过)」)。**注释同步义务**(planner.md §3.4 同款):本屏 :36 行为改写与 F-1 两守卫同批落地(§3.4),本节各落点目标文本以现役形态落笔、落笔即终态;若实施批拆分致某「欠账待改」形态文本先于行为批落地,行为批落地时同步改为现役形态申报,防注释申报滞后于行为。验收锚:①实施后 `act` 方法体内 grep `decide_equip_overlay_pick` 零命中(else 臂 kernel 直调与 import 消失;不作文件级 grep——模块 docstring 现存该符号、§2.6 F-5 改写后仍合法保留该符号作持久锚,文件级零命中不可满足);②局外臂锁绿(无 match → round_success + 决策桩/派发桩零调用 + 零点击);③同文件 observe docstring 无「分支原样」残留。

### 3.2 增补 B(:34 norm_item 决策半现算「在册口径」申报改欠账形态)

**结论**:§2.1 第 5 点与取舍 3 把决策半转换点申报为稳定「在册口径」且无欠账注。:34 下该形态 = 欠账:观察侧零转换(`_read_cards` :71-86 裸文本直报 `equip_pick_opts`)、决策消费裸文本(key_fit_names 子串匹配)、动作上报层消费 `norm_item`(`kernel/cw_action_report/pick_equip.py::report_action_pick_equip_param` :50)——与门「观察侧转换、决策消费标准名、动作/上报层零名字转换」的终态相逆。须改写为欠账形态申报,防「在册口径」被后续读者当作终态契约。

- **落点 1(§2.1 代码面第 5 点中句)**——现文(引语按 :86 实文逐字,respec 强调记号不入引语)「norm_item 现算点不动 = 决策半(flow/action_ops.md §4.5 PickEquip 行「`norm_item` 由决策半经 `normalize_registry_equip_name` 归一现算」在册口径);」替换为:

  > norm_item 决策半现算 = op-layer.md §1.1 :34 观察标准化门**欠账形态**(收敛终态 = 观察侧转换 + 动作/上报层零名字转换,动作上报只携 idx、名字由容器单一源按 idx 提供),逐批收敛,禁新增未标准化直报(现役在册口径 = flow/action_ops.md §4.5 PickEquip 行「`norm_item` 由决策半经 `normalize_registry_equip_name` 归一现算」,随收敛批挂欠账注同步);

- **落点 2(§2.1 关键取舍 3 整条替换;扩面缘由 = 该条前半句第二处 norm_item「在册口径」语境同样无欠账注〔:119,不在原末句落点面内〕,不扩则验收锚①自打红)**——现文全条替换为:

  > 3. **直发 + 原位补载荷,不重建实例**:重建 = 第二构造点,`CwActionPickEquipParam` 增字段时拷贝构造漏字段漂移;norm_item 上移策略器 = 改决策入口契约(strategy-docs/13_pick_family.md + action_ops.md §4.5「由决策半现算」在册口径(= :34 欠账形态,§3.2))= 契约改版超出本发现辖域。直发后「派发实例 = 策略产值」与遭遇修法同型;norm_item = 决策半注入点的载荷补齐,非决策改写——该注入点为 op-layer.md §1.1 :34 欠账形态(§3.2),本稿不迁点(收敛面超本发现辖域),随族级收敛批归位观察侧。

- **落点 3(§2.7 末条 bullet)**——现文「其余文件零触碰(F-1 家族联动面兄弟屏归各自稿/T-37;`OverlayPickExecEnv.idx` 字段注释挂 §2.2 T-37 裁决面;action_ops.md §4.5 经核验无修法面);F-2..F-5 零行为变更。」替换为:

  > 其余文件零触碰(F-1 家族联动面兄弟屏归各自稿/T-37;`OverlayPickExecEnv.idx` 字段注释挂 §2.2 T-37 裁决面);action_ops.md §4.5 = :34 收敛批欠账注落点(非本批落笔面:PickEquip 行「由决策半现算」句为 :34 欠账形态的在册口径,随族级收敛批挂欠账注,§3.5 登记);F-2..F-5 零行为变更。

依据(respec-T9-T15.md §2.1 Q1 增补 B):现役转换点两处 = 决策半 `act`(`normalize_registry_equip_name(texts[best_i])` → `CwActionPickEquipParam.norm_item`,代码 :142-144)+ 动作上报层(pick_equip.py 模块头「归一件名命中 → 入栏 + 获得后果链;未解析 = 值不变翻来源留证」);注册表 = `kernel/cw_events.py::_REGISTRY_EQUIP_NAMES`(:947)+ `normalize_registry_equip_name`(:951,精确快道 → containment → 相似救援)。验收锚:①两落点落笔后本稿 norm_item 语境不再出现无欠账注的「在册口径」表述;②action_ops.md §4.5 PickEquip 行欠账注随族级收敛批落地(T-37 对账,§3.5)。

### 3.3 增补 C(:34 失败语义与互斥屏多候选同名边界登记)

**结论**:本稿未按 :34 登记本屏收敛方向与屏级转换成功性边界,登记如下(申报级,本批不动观察行为):

- **失败语义(收敛方向)**:任一候选转换失败(:34 两段——形变归一精确 / LCS 相似——皆不中)= 观察失败,观察 node round_fail 早退、零写零上报,交外循环重观察重读。现役该态无独立出口:候选读到但 `normalize_registry_equip_name` 不中 → `norm_item=''` → 动作上报层「未解析 = 值不变翻来源留证」续跑(`pick_equip.py` 模块头「pick_equip_name_unresolved」在册)——收敛后该态迁观察侧,上报层留证支随批退役。
- **互斥屏多候选同名(同判面)**:装备三选一 = 选项互斥屏,多候选命中同一注册名 = 识别质量不足以区分,同判转换失败(round_fail 零写零上报);现役无此检测,随收敛批迁观察侧同面实现。
- **边界澄清(与「空表照写」的关系)**:空读(OCR 未命中,`_read_cards` 恒 3 桶拼串、空桶 = 空串)≠ 转换失败(读到但归一不中)——「空表照写」(screens/equip_pick.md §3 在册)与 :34 两门并行不悖,空读不改判、不折算转换失败。
- **落地批义务**:screens/equip_pick.md §3 登记本屏转换成功性边界(上述三面),与 F-1 as-built 同批落笔。

**落点(§2.7 正本文档 bullet)**——现文「- **正本文档(F-1 as-built/F-2/F-3/F-1 家族登记)**:`screens/equip_pick.md`、`game_state/fields.md`(§4 余屏句/§3.4.5 两处/§3.2.15 两臂与末句/§3.4 头注例外括注)、`screens/op-layer.md`(§1.3 守卫清单补本屏两条守卫出口 = 本稿落地批正本更新阶段**必登记**,§2.2 裁决面②)。」替换为:

> - **正本文档(F-1 as-built/F-2/F-3/F-1 家族登记/:34 边界登记)**:`screens/equip_pick.md`(as-built 各节 + §3 转换成功性边界登记 = §3.3 落地批义务)、`game_state/fields.md`(§4 余屏句/§3.4.5 两处/§3.2.15 两臂与末句/§3.4 头注例外括注)、`screens/op-layer.md`(§1.3 守卫清单补本屏两条守卫出口 = 本稿落地批正本更新阶段**必登记**,§2.2 裁决面②)。

依据(respec-T9-T15.md §2.1 Q1 增补 C)::34 原文「任一候选转换失败 = 观察失败:观察 node round_fail 早退、零写零上报……多候选命中同一注册名(选项互斥屏)= 识别质量不足以区分,同判转换失败……各屏转换成功性的附加边界由屏契约(screens/ 各篇)登记」。验收锚:落地批后 screens/equip_pick.md §3 含转换成功性边界申报(失败语义 / 多候选同名同判 / 空读≠转换失败三面齐);本批验收 = 本节登记在案 + §3.5 台账行。

### 3.4 :36 行为改写与族级合并裁决面合流申报(G1 跨屏共性②)

- **合流点**:本稿既有族级合并裁决面 = §2.2「归口 T-37 裁决面」①(三屏 F-1 修法合并为一个实施批)。:36 的行为改写与该面天然合流(respec 报告 §2.8 共性②):6 屏(T-9/T-11/T-12/T-13/T-14/T-15)的 :36 行为改写为同一形态(else 支/守卫臂 → round_success 终结交回),一次族级批实施 + 共享测试锁模板(无 match → round_success 零派发零点击)。
- **落点(§2.2「归口 T-37 裁决面」追加一条)**:

  > - ③**:36 局外支收敛并入本族级批(op-layer.md §1.1 :36,§3.4)**:本屏无 match else 支按 :36 改零决策零点击 round_success 终结交回(改法 = §3.1),与 F-1 两守卫同批实施;族级口径已由 :36 统一(kernel 判据直调支不豁免;原跨稿分歧「T-9 判保留/T-8·T-11 判收编」随之销项,不留候裁措辞),本裁决面仅裁实施批合并形态与共享测试锁模板落地序。

- **族级批边界(承 §2.2「明确不联动」)**::36 改写只动流程侧局外支出口,kernel 判据与策略器入口零触碰;T-10 为零行为批不在本行为批内(其 :36 面只做申报级增补);批名沿 respec 报告 §3 派工建议 = 「:36 局外支收敛 + :34 登记族级批」。

### 3.5 T-37 登记行(欠账面,原文)

> - [T-37 登记][欠账] equip_pick(T-9)::34 观察标准化门欠账——norm_item 件名归一现役在决策半(`cw_screen_equip_pick.py::act` :142-144)与动作上报层(`kernel/cw_action_report/pick_equip.py::report_action_pick_equip_param` :50),观察侧零转换、决策消费裸文本;收敛终态 = 观察侧转换(两段;`kernel/cw_events.py::normalize_registry_equip_name` :951 现役归一函数随批迁观察侧消费)+ 动作/上报层零名字转换(动作上报只携 idx);失败语义 = 任一候选转换失败 round_fail 零写零上报、多候选命中同一注册名同判;正本随批挂注面 = flow/action_ops.md §4.5 PickEquip 行 + screens/equip_pick.md §3(转换成功性边界)+ screens/equip_pick.md §4 对照表 `CwActionPickEquipOp` 行动作列(第三同断言站点:现文「携归一件名 `norm_item` = 决策半经 `normalize_registry_equip_name` 归一现算」,收敛后随批挂欠账注,不留无欠账注申报)。逐批收敛,禁新增未标准化直报。
> - [T-37 登记][欠账] equip_pick(T-9)::36 局外支欠账——`CwScreenEquipPick.act` 无 match else 支(kernel 直调 → 派发)= 决策 + 点击,违 :36;处置 = 归「:36 局外支收敛 + :34 登记族级批」改零决策零点击 round_success 终结交回 + 测试局外臂锁(共享模板);与 §2.2 归口 T-37 裁决面①(F-1 三屏合并实施批)合流同批;T-10 零行为批不在本行为批内。

## 4. 新规范增补二(2026-09-22:选项坐标观察上报 + 动作 op 单文件)

### 4.0 前置裁定与草案条款基准

- **批形态前置裁定(2026-09-22 用户裁定)**:逐屏实施,本稿只辖本屏(T-9)——§2.2 归口 T-37 裁决面①(三屏 F-1 合并实施批)与 §3.4(:36 局外支收敛并族级批)随之**销项**:本屏 F-1 两守卫 + :36 局外支改写 + 本节增补 = 本屏独立实施批一次落地;`OverlayPickExecEnv.idx` 字段注释陈旧措辞不随本批改(共享面,挂 §4.7);§2.2 裁决面②守卫登记按**逐屏条目**落(本批正本更新阶段登记,无族级统一条目形态)。
- **基准** = 用户裁定 2026-09-22(会话口头裁定;两条款均未入正本——本节所引草案全文即设计基准,入册时点 = 本节对抗收敛经用户确认后随批 commit,入册后本节引用补正本锚号)。用户裁定原文(口语,条款保真度审查基准):「观察上报选项时候,除了要将识别内容归一化到标准注册数据外,还需要上报具体的坐标,存到 game state,即选中这种选项具体的坐标,这里包括商店、各个需要选择的 overlay,这样策略侧,只需要输出下标就可以了,执行的动作 op,也可以根据下标,从 game state 获取坐标来执行。另外就是必须每个动作 op 单独一个文件。」据此整理:
>
> **草案条款 A(选项坐标观察上报)**:观察上报选项时,除将识别内容归一化到标准注册数据(op-layer.md §1.1 :34)外,必须上报每个选项的可点击坐标并存入 game state(逐选项一坐标,与选项列表同序、同坐标系、同一写点)。策略侧只输出下标;执行的动作 op 按下标从 game state 读坐标执行——决策半与动作 op 均不自算选项坐标。辖域 = 商店与各需要选择的 overlay。
>
> **草案条款 B(动作 op 单文件)**:每个动作 op 单独一个文件。
>
> 时序:本节在 §0-§3 已收敛修法上叠加,不推翻主体;与 §3 同类增补、不同基准形态(§3 基于 :34/:36 已入正本,本节基于草案条款,引用形态 =「草案 + 入册待办」)。本节不改 §0-§3 正文,正文需连带改写处在本节逐字给目标文本与落点节号。商店与其余兄弟屏的条款 A 适配归各自屏批,本稿只辖本屏。

### 4.1 本屏适配映射(条款 → 本屏语义)

- **条款 A 三段**:
  - ①观察上报增坐标 = `CwScreenEquipPickObs`(`kernel/cw_screen_report/equip_pick.py`)增 `option_points` 字段(恒 3 槽,与 `options` 同序;元素 = `(x, y)` 元组,坐标系 = 1080p 游戏空间,None = 读缺已兜底),`report_screen_equip_pick_obs` 同一写点增写容器新域 `equip_pick_opts_points`;
  - ②策略侧只输出下标 = **现役已合规零改动**(`strategies/impl/flow.py::decide_equip_pick` 零参产 `CwActionPickEquipParam.idx`,候选读 `gs.equip_pick_opts` 槽不变,零策略文件触碰);
  - ③动作 op 按下标取坐标 = `CwActionPickEquipOp.run` 增容器坐标读 + 守卫断言,`env.target` 不再消费(决策半删 target 现算)。
- **坐标单一源** = screen_info 建档「卡-装备1/2/3」area 中心(`kernel/cw_obs_core.py::area_center` 现读;三 area 中心 = 780/1070/1385,坐标真值见 §2.4 F-3)——**本适配同时清偿 F-3 挂账的「建档在册而代码未消费」**(原「消费改造归实机批」撤销,落点见 §4.4);area 读缺 = 回退 `(CARD_XS[i], CARD_Y)` 兜底常量 + log 留证(同屏在册先例 = 巨星/策划/投资确认钮「area 主源 + 兜底常量」派生模式,`cw_overlay_pick_action.py::CwActionPickMegastarOp.run` 同款)。
- **坐标与 OCR 解耦**:坐标源 = 建档 area(非 OCR 桶),OCR 全空时坐标照报——与「空表照写」(screens/equip_pick.md §3 在册)及 §3.3 空读边界并行不悖;选卡点击恒有合法落点(空读下策略按 kernel 首卡 tie-break 出 idx,动作 op 仍有点可点)。
- **条款 B 映射**:`CwActionPickEquipOp` 迁出 `cw_overlay_pick_action.py` → 新文件 `operations/cw_op/cw_pick_equip_action.py`(命名对齐同目录单文件动作 op 惯例 = `cw_buy_card_action`/`cw_tool_use_action` 同款);`cw_action_registry.py` import 面该类改源新模块;`OverlayPickExecEnv` 家族共享留原文件,新文件跨文件导入(过渡态申报 + 全家族拆分挂账见 §4.7)。

### 4.2 代码面落点(§2.1 主体上叠加)

1. **kernel 载荷**(`kernel/cw_screen_report/equip_pick.py`):`CwScreenEquipPickObs` 增字段 `option_points: list[tuple[float, float] | None]`(`field(default_factory=list)`;[索引定义] 注释 = 坐标系:画面物理卡位序下标(0 起),与 `options` 同容器同序恒稳;取值时机 = 入口帧快照;元素 None = 建档 area 读缺已兜底);`report_screen_equip_pick_obs` 增一行 `gs.write_logic(gs.equip_pick_opts_points, list(obs.option_points), produced_by='CwScreenEquipPick', sig=sig)`(与 options 行同函数相邻,对齐性由同一写点同帧保证)。
2. **容器域**(`kernel/cw_game_state.py`,与 `equip_pick_opts` 三处镜像相邻):槽表 1 行 `'equip_pick_opts_points': 1`(注释「选择装备候选点击坐标槽(list[tuple[float,float]|None];草案条款 A)」)+ 屏归属表 1 行 `'equip_pick_opts_points': ('货币战争-选择装备', True)` + Field 声明 1 行 `equip_pick_opts_points: Field[list[tuple[float, float] | None] | None]`。
3. **投影对账表**(`kernel/cw_projection_audit.py`):`equip_pick_opts_points` 增行 `AUDIT_OBSERVATION_ONLY`(basis「选择族坐标读面(草案条款 A),零逻辑写端」,与 equip_pick_opts 行相邻)。
4. **观察 node**(`observe`):`_read_cards` 后增坐标读——逐槽 `area_center(self.ctx, '卡-装备{N}', '货币战争-选择装备')` 取 `(x, y)`;None = 回退 `(CARD_XS[i], CARD_Y)` 并 `log.warning` 单行留证;obs 构造传 `option_points`;模块 import 面增 `area_center`(自 `kernel/cw_obs_core`)。
5. **决策动作 node**(`act`,§2.1 修法主体不变,本点叠加):删 `target = Point(self.CARD_XS[best_i], self.CARD_Y)` 行与 `best_i` 中介变量(`log.info` 卡序字段改引 `act.idx + 1`,卡名文本字段沿用 `texts[act.idx]` 守卫式取值);派发 env 构造改 `_env = OverlayPickExecEnv(op=self)`(零 target 零 idx:坐标归容器、下标归 param);守卫①②、:36 局外支、norm_item 原位补齐全部保持;模块 import 面 `Point` 随 target 删除退役。
6. **动作 op**(`cw_pick_equip_action.py::CwActionPickEquipOp.run`,迁移与适配一体):机械链前增坐标读与守卫——

   ```python
   gs = game_state_from_ctx(self.ctx)
   pts = gs.equip_pick_opts_points.value if gs is not None else None
   if pts is None or not (0 <= action.idx < len(pts)) \
           or pts[action.idx] is None:
       raise AssertionError(
           f'[cw-equip-pick] 选项坐标读缺(容器/idx 不一致,禁兜底): '
           f'idx={action.idx} pts={pts!r}')
   target = Point(pts[action.idx][0], pts[action.idx][1])
   ```

   守卫语义 = op-layer.md §1.3 同款(防 bug 路栏:坐标缺 = 观察链/容器 bug 响亮暴露,禁执行侧兜底常量——兜底已前移观察侧,执行侧再兜 = 双源回潮);gs None 折入 pts None 同判(:36 改写后局外不派发,gs None = 链路 bug)。机械链 `env.target` 消费改本地 `target`;上报调用点 gs 判空分支随守卫退役(守卫后 gs 恒非 None,直调);env 其余字段不消费保持(env 构造由画面 op 传入,字段集家族共享不动)。
7. **类常量注释**(`cw_screen_equip_pick.py`,§2.4 F-3 修订后文本再修):CARD_XS/CARD_Y 注释消费申报改「消费点 = 观察 node 坐标上报(area 主源 + 兜底,草案条款 A);执行侧不自算坐标」。

### 4.3 测试锁(§2.1 测试锁与 §3.1 落点 4 之上修订/追加)

- **观察上报锁**(`test_cw_screen_two_node_family.py` `_OBS_ROWS` 表 equip_pick 行):期望容器面扩为双域——`equip_pick_opts`(现值)+ `equip_pick_opts_points`(3 槽定值;area 读桩 = monkeypatch `area_center` 回定值,恒稳断言不读真实建档);表驱动形状若不容双域,该行拆独立锁(实施时定,锁语义不变)。
- **决策锁修订**(现役 `test_equip_act_decides_from_container_and_dispatch_terminal`):删 `env.target` 断言,增断言「env 仅携 op(零 target 零 idx)」——直发形态申报随适配收紧。
- **动作 op 坐标锁(新,`test_cw_unified_action_4.py`)**:①行为锁 equip 行适配——gs 桩携 `equip_pick_opts_points` 种子坐标,点击点断言改自容器值(env.target 不再是坐标源;模块迁移后 monkeypatch 目标改新模块 `cw_pick_equip_action`);②三态守卫锁——容器缺域 / idx 越界 / 点 None → AssertionError 且零点击。
- **局外臂锁(§3.1 落点 4)/守卫①②锁/决策桩换真词表类**:不变。
- **不受影响面复核**:`test_cw_pick_channels_t60.py` 仅消费 kernel 上报函数与 ChannelSig actor 字符串,不经动作 op 类,零触碰。

### 4.4 既有正文落点修订(逐字)

- **§1 F-3「明确不解决」首项**:现文「卡位 area 化消费改造(行为变更,坐标单一源清点挂账项在册,归实机批);kernel 判据本体。」→「卡位 area 化消费改造 = 本稿增补二清偿(§4.2 第 4 点观察侧坐标上报消费建档 area;原「归实机批」撤销);kernel 判据本体。」
- **§2.1 第 5 点整点替换**(并入 §3.2 落点 1 的欠账语义,§3.2 落点 1 随之销项,以本条为实施文本):

  > 5. **norm_item 载荷原位补齐 + 直发策略产实例**(守卫②后;增补二修订:target 现算删,坐标归容器):
  >
  >    ```python
  >    _opt_text = texts[act.idx] if 0 <= act.idx < len(texts) else ''
  >    act.norm_item = normalize_registry_equip_name(_opt_text)
  >    ```
  >
  >    派发改 `action_op_for(act, self.ctx, OverlayPickExecEnv(op=self)).execute()`(删 `_param = CwActionPickEquipParam(...)` 重建行;删 `target` 现算行——点击坐标 = 动作 op 自容器 `equip_pick_opts_points[act.idx]` 读,§4.2 第 6 点)。norm_item 决策半现算 = op-layer.md §1.1 :34 观察标准化门**欠账形态**(收敛终态 = 观察侧转换 + 动作/上报层零名字转换),逐批收敛,禁新增未标准化直报;直发后「派发实例 = 策略产值」与遭遇修法同型。`log.info` 消息字段改引 `act.idx`/`act.norm_item`。

- **§2.1 文档面 screens/equip_pick.md §4 伪码块整块替换**:

  ```
  act = decide_equip_pick()(零参;候选读容器 equip_pick_opts 槽)
  守卫①:act 非 CwActionPickEquipParam(None/词表外)→ round_fail(含原值)零盲发
  守卫②:act.idx 越界 [0, 3) → AssertionError(禁钳位)
  norm_item = normalize_registry_equip_name(texts[act.idx])(决策半载荷原位补齐,:34 欠账形态)
  → 直发 act 派发(env 仅携 op;env.target/idx 停传)
    (动作 op 内:target = 容器 equip_pick_opts_points[act.idx](条款 A;缺 = 守卫断言)
     → mouse_move + click → 1.2s → 即时自上报 report_action_pick_equip_param)
    (机械交回,零判效)
  → 派发即 round_success 终结交回
  ```

- **§2.1 文档面清单追加两处**:screens/equip_pick.md §3 观察面增坐标申报句(建档 area 主源 + 兜底 + 空读照报边界,草案条款 A);§4 对照表「发出方式」列 target 申报改「env 仅携 op,点击坐标 = 动作 op 自容器读」。
- **§2.4 F-3 修法连带**:代码类常量注释目标文本以 §4.2 第 7 点为准(「未消费」改「观察侧消费」);screens/equip_pick.md §8 卡位 bullet 同步再修(同语义)。

### 4.5 关键取舍

1. **容器存 `(x, y)` 元组而非 `Point`**:容器域 = 纯数据面(投影对账/遥测序列化面最小,现役容器域全为标量/纯 dataclass,无几何对象先例),几何载体转换归执行层(动作 op 转 Point)。
2. **area 读缺回退常量而非观察失败**::34 的「转换失败 = 观察失败」辖识别内容(OCR 归一);坐标源 = 建档(非识别),读缺 = 建档缺损非识别失约,同屏「area 主源 + 兜底常量」在册派生模式平移;防双源 = 执行侧守卫断言禁再兜(§4.2 第 6 点),兜底只许一层。
3. **`env.target`/`env.idx` 字段保留不删**:`OverlayPickExecEnv` = 家族共享,未迁移屏仍消费;equip 停传后本屏零死代码,字段注释(「钳位后生效值」陈旧措辞)修订随家族批(§4.7 登记)。
4. **单文件先拆本屏**:条款 B 全家族适用,兄弟 op 留旧文件 = 过渡态(全家族拆分 + env 提取独立模块随族级批,§4.7);本屏新文件即终态命名,不产生二次迁移。
5. **norm_item 决策半现算不动**::34 欠账收敛(名字归一迁观察侧)与本坐标适配同写点不同义务——坐标先行零新增欠账(:34 欠账已在册);族级收敛批落观察侧时名字归一与坐标同一写点归位。
6. **策略侧零触碰**:`decide_equip_pick` 契约与容器读面不变(条款 A ② 本屏现役已合规)——本适配零策略文件。

### 4.6 实施文件面全集(以本清单为实施对账基准;§2.7、§3.1 落点 5、§3.2 落点 3 并入销项,冲突处以本节为准)

- **行为变更(F-1 + :36 局外支 + 条款 A/B 适配)+ 同文件注释面(F-3 连带/F-5/:36 连带尾句)**:`operations/cw_screen/cw_screen_equip_pick.py`(act 守卫/直发/无 match else 臂改写/observe 坐标读/docstring;类常量注释;模块 docstring 两处)。
- **kernel**:`kernel/cw_screen_report/equip_pick.py`(obs 载荷 + report 双写)、`kernel/cw_game_state.py`(新域三处镜像)、`kernel/cw_projection_audit.py`(对账行)。
- **动作 op(条款 B)**:`operations/cw_op/cw_pick_equip_action.py`(新文件,`CwActionPickEquipOp` 迁入 + 坐标读守卫)、`operations/cw_op/cw_overlay_pick_action.py`(删 `CwActionPickEquipOp` 类)、`operations/cw_op/cw_action_registry.py`(import 改源)。
- **测试**:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(决策桩换真词表类 + 守卫两锁 + 局外臂锁 + 观察/决策锁修订)、`sr-od-test/test/sr_od/application/currency_war/test_cw_unified_action_4.py`(equip 行适配 + 三态守卫锁)。
- **正本文档**:`screens/equip_pick.md`(as-built 各节 + §3 转换成功性边界登记 + §3 坐标申报 + §8 守卫两条)、`game_state/fields.md`(§4 余屏句/§3.4.5 两处/§3.2.15 两臂与末句/§3.4 头注例外括注 + 新域 `equip_pick_opts_points` 登记(§3.4 头注候选域清单 + §3.4.5 装备三选一行))、`screens/op-layer.md`(§1.3 守卫清单补本屏守卫出口逐屏条目 + 草案条款 A/B 入册(用户确认后))。
- **其余文件零触碰**:`flow/action_ops.md` §4.5 = :34 收敛批欠账注落点(非本批落笔面,§3.5/T-37 在册);kernel 判据本体;策略文件;兄弟屏与商店(条款 A/B 家族面归各自批,§4.7)。

### 4.7 T-37 登记行追加(欠账/过渡态/入册面)

> - [T-37 登记][过渡态] equip_pick(T-9)条款 B 单文件拆分只辖本屏——`OverlayPickExecEnv` 仍驻 `cw_overlay_pick_action.py`,新文件跨文件导入;全家族动作 op 单文件拆分 + env 提取独立模块随族级批。
> - [T-37 登记][欠账] 草案条款 A 家族推广:装备三选一外的选择 overlay 与商店的坐标观察上报适配归各自屏批;`OverlayPickExecEnv.idx`/`target` 字段注释(「钳位后生效值」等陈旧措辞)随族级批修订。
> - [T-37 登记][入册待办] 草案条款 A/B 正本化:op-layer.md §1.1 入册两条款(全文 = §4.0 基准段,含辖域「商店与各需要选择的 overlay」),入册 commit 后 §4 引用补锚号。
