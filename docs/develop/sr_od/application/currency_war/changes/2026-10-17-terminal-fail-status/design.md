# terminal-fail-status 迭代设计（总纲）

## 0. 元信息
- 迭代目标：**删除六个查表型动作 op 的防御性失败出口（共 8 个检查段：5 段删检查直接使用〔area 类+弹窗〕、3 段改 op 内守卫断言〔参数类〕）**——检查代码整段删除，取值直接使用；area 缺失/下标越界由 Python 自然异常报错（实测形态 = AttributeError 坐标解引用/TypeError/IndexError 系族，验收偏差①裁定为措辞级），栈回溯直指使用行。用户裁定 2026-10-16（「项目里之前都是取了 area 就直接使用的，写防御性代码冗余」——第三轮裁定，撤停机闸机制案与 raise 案）。
- 状态：终版（四裁定 QA/QB/QC/QD 已落，待开工前最后扫）
- 文档清单：无详设（单文档方案）
- **四裁定终值**：QA = StartBattle 弹窗确认 area 缺失检查删除（自然炸，`未生效:*` 族零供给退役）；QB = 框架重试放大**什么都不做**（既有吞点与重试行为维持现状）；QC = 终结出口失败透传**本批修**；QD = DeployMove **零校验直接使用**（错槽后果由既有失配治理链承接）。
- **边界申报**：①LogicOutcome 契约不动；②屏幕现读落空族不动（受阻码 + 重派，见 §2.2）；③T-4 分账**保留不撤**（§2.5 注记改写）。

## 1. 问题与动机
- **现状缺陷**：六个查表型动作 op 为「area 未配置/下标越界」写了防御性检查（round_fail 出口），确定性 bug 被吸收循环。**实证口径（attack 三轮修正）**：同期 live 失败主导族为「发出后不落地」静默循环（5456× 执行未落地，receipt-applied-retire 迭代账本 T-4）；六口吸收循环本身缺直接 live 实证（现词表 journal 零命中），现存证据 = 机制推演。
- **裁定依据**：开发期 bug——「没有选到就是代码 bug：显式报错修根因，不在 bug 上做无畏的补丁操作」；显式报错的现役形态 = 取值直接使用、自然异常（用户裁定：项目既有风格即取了 area 直接使用，防御检查冗余）。
- **对抗史**：初版停机闸机制案 → 撤（防御性编程）；二版 raise 案 → 撤（连 raise 都不写）；三版零防御案经四轮攻击收敛至本终版。

## 2. 方案（单文档完整设计）

### 2.1 删除检查清单（六 op 七段，直接使用）

| op | 删除的检查段 | 自然失败形态 | 代码锚 |
|---|---|---|---|
| PickEncounter | `if card is None: round_fail(遭遇卡 area 缺失...)` | card=None → 下游 click 自然 TypeError | `cw_pick_encounter_action.py:70-75` |
| PrepLevelUp | `if btn is None: round_fail(购买经验 area 缺失...)` | btn=None → 下游 click 自然 TypeError | `cw_prep_level_up_action.py:99-101` |
| StartBattle | `if btn is None: round_fail(area 缺失:按钮-出战...)`（跳过子态同构） | btn=None → mouse_move/click 自然 TypeError | `cw_start_battle_action.py:121-126`（:120 取值行保留） |
| StartBattle 弹窗（QA 删） | `if detail.startswith('area 缺失'): round_fail(...)` | 弹窗 area=None → 确认点击自然 TypeError | `cw_start_battle_action.py:135-137` |
| WearEquip | `if target is None: round_fail(装备槽位坐标缺失...)` | target=None → 下游拖拽自然 TypeError | `cw_wear_equip_action.py:67-70` |
| BuyCard | `if _slot_no is None: round_fail(槽解析失败...)` + `if not (1 <= _slot_no <= len(pts)): round_fail(越界...)` | **改 op 内守卫断言**：`raise AssertionError(消息原文)`（:21 坐标裁定域——参数违法由 op 自判） | `cw_buy_card_action.py:105-120` |
| DeployMove | `if not (1 <= slot_no <= len(pts)): round_fail(落位载荷越界...陈旧载荷,观察重派)` | **改 op 内守卫断言**：`raise AssertionError(消息原文)` + **补 to_slot ≥ 1 下界**（负下标缺口闭合——:21「禁负下标直取列表——负下标回环 = 静默错点」裁定落位）；「陈旧载荷/观察重派」语义废弃 | `cw_deploy_move_action.py:71-74` |

- **保留面辨析**：BuyCard 槽匹配循环（:88-98，身份匹配 = 业务定位逻辑）保留；StartBattle 两屏查 + 免战跳过变体检测（:105-118）与 **:119 找不到按钮口保留**（屏幕现读族受阻码生产者，词表既有成员）；PrepLevelUp area 自读回落（:89-98，商店域锚定缺失 → area 自读 = 业务定位逻辑）保留。
- **StartBattle 中间形态申报**：find 命中 ∧ area_center None 的跨档漂移形态 → `mouse_move(None)` 自然异常，接受消息降级（栈含 op 行）。
- **前置断言修正申报**：六口中仅 :121-126 一口在点击前；弹窗口（QA 删）在点击后——其删除由 QA 终裁覆盖（自然炸先于回执与上报，回执义务由失败运行整体证据承接，§2.2 例外从句）。

### 2.1.1 策略侧参数纪律（成文，非新代码；attack 三轮实证定域）

动作参数的合法性由**现算纪律**保证，不靠 op 侧校验。**同帧性承诺限定域 = 单动作决策环**（备战 act `cw_screen_prep.py:772-852` 每动作重 decide、shop visit act `cw_screen_shop.py:613-710`，attack 逐行实证 decide→op 取值间零容器写）：decide 读容器 C → 产参数 → op 立即执行，op 面对同一 C——坏参数只能是决策逻辑 bug，自然异常即正确处置。

**边界载体登记（现役生产路径，不适用本纪律句）**：战斗链批量发射（`launch_prepared_battle` `cw_loop.py:230-258`，达标臂+锁定恢复局两调用面）——`_battle_chain_deploy_moves` 一次产整批 DeployMove 参数（基于 C_0），逐个 execute 间容器被自上报改写（move k 面对的是 C_{k-1}）。其陈旧化治理 = **report 静态域拒绝 + 观察 reconcile**（既有），「持有窗口 = 同一发射批内」为该路径的登记豁免。除战斗链外全仓无第二处参数跨决策帧持有（attack 全仓 grep 实证）。

**违纪承接双层**（「陈旧参数形态不存在」的全称断言不成立——商店环 proposal 守卫 `cw_shop_action_ops.py:139-193` 因跨代际提案策略 bug 而建，守卫存在反证形态发生过）：纪律下陈旧参数**不应存在**；违纪现行承接 = ①商店环 proposal 守卫（loop 级同帧复检，既有，收编为论据）+ ②动作 op 取值自然异常（兜底）。**自然异常覆盖边界**：Python 语义会炸的形态（None/正越界）；索引类负值形态不炸（to_slot≤0 → `pts[-1]` 合法索引静默错槽）——**QD 终裁（用户四轮后定案）**：参数违法类校验收拢到对应动作 op 内、由 op 守卫断言（`raise AssertionError`，消息语义保留）——DeployMove 补 to_slot ≥ 1 下界闭合负下标缺口；集中式 validate() 的逐动作参数分支已按同原则**本批收拢完成**（validate 整体退役 + 决策环调用点删除,扩展批 f100a7959）。

1500 事故根因 = 计划跨帧持有且不消费（违反本纪律）；其循环源治理 = 失配告警停局 + NODE-DWELL 900s 哨兵（T-4 注记口径，§2.5——T-4 保留不撤），本纪律防复发。

**规范成文落点**（attack 四轮 #1/#2 定稿）：

- **零防御纪律句 = :11 裁定的应用条款，不立平行段**：「上款『显式报错修根因』的现役形态 = 取值直接使用、Python 自然异常；不为建档缺失/参数违法设检查出口（本批六口，2026-10-17）」。**限定域申报**：本批六口的建档缺失检查段删除 = 处置事实记录；**下标/坐标域参数的缺席与越界仍按 :21 坐标裁定守卫断言（含禁负下标）——该裁定域 = 选择类 pick 族；DeployMove 拖拽域按 QD 终裁 (d) 适用对账治理链**——pick 族 6+ 处既有显式出口条目不在本批范围、不被此句判为待修。
- **参数现算纪律句 = :21 裁定的调用方侧条款**：与「策略侧只输出下标」同段或紧邻，指针式成文（:11「显式报错修根因」/:28「判重禁保护」/:38「归属表」三处既有成文不重复）。`n- **校验落点契约（用户裁定 2026-10-16 成文）**：动作参数合法性校验的唯一落点 = 对应动作 op 内守卫断言——op 是参数语义的唯一所有者，校验随语义走；执行器不设集中参数校验（原 `PrepActionExecutor.validate` 随本批退役，集中式 if-elif 链迫使执行器知晓全部动作参数语义 = 按层打散知识，废弃理由随条目申报）；:21 坐标裁定即本条的坐标域先例。
- 落点：action_ops.md §1（:11/:21 裁定区就近应用条款）+ §4.2 DeployMove 行、§4.1 BuyCard 行指针；不落 §5（回执契约域不同）、不落 §2.1（发出后治理链，参数陈旧是发出前形态）。
- 互引申报：「识别不到就是 bug」（观察域停机闸，住 screens/shop.md）与本句为观察/动作两域同族规范，成文互引一句。

### 2.2 词表与回执语义收窄

- `prep_actions.py` `_PREP_RECEIPT_BLOCK_CODES` 删行清单（attack 实证 + QA 终裁，共 8 行）：弹窗三行（:114-119，QA 删）、备战标识（:121）、装备槽位（:124）、落位载荷（:133）、槽解析（:135）、槽号越界（:136）。**保留行**：按钮-出战/按钮-跳过（**:109-111 三行**——:109 即 :119 保留口的映射行，误删则该链走原文兜底）、无简易武装箱/无秘密典籍/无书册卡（现读族）、owned 网格通用行（:127，ToolUse/WearEquip 现读族）。
- `cw_screen_shop.py:309-310` `_SHOP_VISIT_BLOCK_CODES` 2 行整表退役（`_visit_block_code` 成死代码随删）。
- **词表收缩后闭集**：`定位缺失(按钮-商店)`/`定位缺失(按钮-收起)`/`未执行:定位缺失(按钮-出战|按钮-跳过)`/`未执行:无简易武装箱|无秘密典籍|无书册卡|owned 网格未定位族`——「五族不变」表述作废；`未生效:*` 族随 QA 零供给**退役**。
- `fields.md` 回执契约节 invariant 措辞改写（attack 二轮 #8 句式 + QA 例外从句）：「回执行以分派为单位——回执域（备战 executor 分派 + 商店 visit 分派 + 开/关店自记）内每动作恰一行；reason='' ⇔ 已发出，非空 = 现读落空受阻码（收缩后闭集）；**异常终止的分派不产行**（主点击已发的回执义务由失败运行整体证据承接：栈回溯 + 失败记录）；建档缺失类检查段已删，不在回执域」。旧表述「每动作 op 恰一条」废弃（PickEncounter 本就无回执行，不可证）。
- `action_ops.md` §5 词表跟随（与 fields.md 收缩**同批落**，防两处词表短暂不一致）。

### 2.3 传播路径与框架层语义（QB 裁定 (a) 落定）

自然异常沿异常上抛通道传播，站点清单与终态（attack 实证 + QB 裁定 (a) 落定）：op.run() → 落地门（shop）/`_dispatch_action`（prep）→ **`cw_screen_prep.py:817-819` 既有 `except Exception → round_fail` 维持现状不动**（prep 域自然异常在此转 round_fail 重派，OP_FAIL_REDISPATCH_LIMIT=5 熔断 = 实际终态防线）→ 访问环收尾 → **框架 `operation.py:452-465` `except Exception → round_retry` 维持现状**（shop 域自然异常穿框架重试至 node_max_retry_times=400 上限后失败收尾，每次全栈日志+截图 = 用户裁定接受）→ app runner（`application_run_context.py:688` FAILED+exc_info 收口 ✓）。全链 except 扫描报告随验收交付（口径 = 「无**未申报**吞点」，本节即申报清单）。

### 2.3.1 终结出口失败透传（QC 裁定 (b) 本批修）

`cw_screen_prep.py:831-833` 终结口 `_terminal_exit`（方法体 :858 一带）现无条件转 round_success（访问级成功语义），副作用 = 外环 5 连败防线数不到终结口失败 → 现读落空族终结口（OpenBox 无箱等）无界重进，仅 NODE-DWELL 900s 哨兵兜底（attack 二轮新发现事实）。**修法**：`_terminal_exit` 增收 op round 结果，失败 → 返回 round_fail（访问仍结束、收尾照常，但外环防线可数 → 有界）。申报：这不是新增检查，是把既有出口的「失败伪装成成功」改正为如实上报——终结语义（访问结束）与成败语义（本拍动作发没发出）正交分层。

### 2.2.1 不动面补遗（attack 二轮）

WearEquip owned 网格未定位（:74-76，与 ToolUse 同族现读落空）——不纳入删除面，维持受阻码+重派。CwScreenShop.observe 三口（商店牌-N/购买经验(商店屏)/按钮-刷新 area_center 静态查表，:492-503）——同为建档漂移家族但宿主 = 画面 op，留 round_fail→重派（5 次熔断兜底）：**同 bug 双语义划界申报**（划界依据 = 宿主类型；后续批可统一，不混本批）。

### 2.5 分账收口（理由修正）

- T-4 分账（receipt-applied-retire 迭代）**保留不撤**，注记改写 = 「用户裁定不做防御性编程；参数类三口改 op 内守卫断言、area 类五段删检查直接使用；残余未落地循环由失配告警停局 + NODE-DWELL 900s 哨兵承接」。
- 终结出口失败透传随 QC 裁定 (b) 本批修（§2.3.1）。
- 原「终态前缀机制」「raise 案」全部作废，不留分账。

## 3. 裁定终值表（四轮收敛，全落）

| # | 裁定项 | 终值 |
|---|---|---|
| QA | StartBattle 弹窗确认 area 缺失（:135-137，点击后出口） | **删除检查，直接使用自然炸**；`未生效:*` 族零供给退役 |
| QB | 框架层重试放大（400 次上限+截图） | **什么都不做**——既有吞点与重试行为维持现状，用户接受 |
| QC | 终结出口失败伪装成成功（`_terminal_exit` 无条件 round_success） | **本批修**——增 op round 结果入参，失败返回 round_fail |
| QD | DeployMove 负下标静默错槽（to_slot≤0 不炸） | **参数校验收拢 op 内**——参数违法类三口 op 内守卫断言（raise AssertionError，消息保留；DeployMove 补 to_slot≥1 下界）；validate() 逐分支退役后续批 |

## 4. 验收基准（预写）

- sim 驱动整局收口（`terminal=death|p3_enter`，fail_streak<5）——正常局零触发（attack 实证：六口条件 sim 健康驱动不可达），行为不变；
- 自然失败可达：fixture **直驱层**（op.run()/executor.execute()/act()）构造五口条件（DeployMove 正越界 → IndexError；**to_slot≤0 → 守卫断言 AssertionError（QD 终稿，可构造用例）**；其余口 → AttributeError 系族）→ 异常上抛；harness 全流程 `op.execute()` 路径异常被框架吸收成 retry（既有行为，判据按直驱层口径）；
- 终结出口透传可达：fixture 构造终结口 round_fail → visit 返回 round_fail（外环防线可数）；
- 传播路径验证记录（全链 except 扫描报告，口径 = 无未申报吞点，§2.3 即申报清单）；
- 非成员回归：现读落空族受阻码行为不变（StartBattle :119 → `未执行:定位缺失(按钮-出战|跳过)` 链不动）；
- grep 清零（白名单口径）：六 op 文件 `round_fail` 仅剩 **StartBattle :119 + WearEquip owned 网格口 :74-76** 两处；「陈旧载荷,观察重派」「禁兜底坐标交回重读」等注释清除；映射表删行清单（§2.2）逐行核；
- 全量测试过（sr-od-test 相关子集）；测试迁移面 **6 文件点名**：test_prep_action_ops（LevelUp+DeployMove）/test_action_report（BuyCard 两口）/test_shop_screen_op（BuyCard 经 act + :285-297 `_visit_block_code` 映射单测**删除**）/test_overlay_ops（PickEncounter 失败臂）/test_prep_actions（StartBattle 两回执行测试**删除**，:100-119 受阻码链保留）/test_deploy（DeployMove 越界直驱）；
- §3 偏离清单「三禁零条」核查随批重跑（六口 round_fail 段删除改变清点面）；
- 完成前常规检查（landing 首节）。
