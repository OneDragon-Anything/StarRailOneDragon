# T-5 补给 修法设计(supply_node)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:用户裁决通过,直接辖面已实施(§2.1/§2.2 专篇/§2.3/§2.5/§2.6/§2.7 十九处落地并过验证门;§2.2 README 索引行让渡 T-1、§2.4 模块头段让渡 T-4 §2.3、域外扩散面留全仓清理批,均未随本裁决实施)。对抗轨迹:r1 未收敛 7 条→修订→r2 未收敛 4 条→修订→r3 收敛
- 输入:审查报告 = `.debug/progress/2026-09-22-cw-screen-review/reports/T-5-r1.md`(发现 F-1..F-7);涉事代码与文档以代码为真值逐处核读(清单行号均标注「现值」基线,并行批可能再位移,实施按「文件+定位描述」落点)
- 修法覆盖面 = 代码注释面:补给链三文件(`operations/cw_screen/cw_screen_supply_node.py`、`operations/cw_op/cw_overlay_pick_action.py`、`kernel/cw_action_report/pick_supply.py`)+ `obs/cw_node_obs.py`(F-5 修法面);文档四面:game_state/README.md 域表行、logic-updates/pick-supply.md + README 索引行、fields.md 三处、screens/supply.md §9

## 1. 问题与动机

总括:七个发现同指一个族根——即时单相上报等迁移批落地时代码与部分正本已更新,但 landing 正本更新清单漏覆盖了本批文档面与注释面,留下上一代「到账登记/已用计数/分步上报」语义的残留快照。本稿修法 = 逐面补齐语义到现役口径;「防 landing 清单漏项复发」是流程层问题,不属本稿(挂汇总任务 T-37 呈报)。

### 1.1 F-1(中)game_state 域表行未随剩余语义化批同步

- 现状症状:`game_state/README.md` §3.3 域清单表「节点屏刷新计数域(node_screen_refresh)」行(约 L114)①仍以现役口径列出已退役字段 `encounter_refresh_used`/`supply_refresh_used`;②主写渠道仍申报已退役的「on_outcome 发射型钩子」「live 刷新发射单点」写端;③字段全集未列 `encounter_refresh_left`/`supply_refresh_left`,行内「剩余两字段」措辞与列出的字段集自相矛盾(报告 F-1;现状摘录见报告)。
- 根因归层:约定层——域表行是域级摘要,字段级正本(fields.md §3.4.1/§3.4.2)已随剩余语义化批改齐,摘要行未跟上;文档同步流程漏项。
- 解决到哪:整行改写为现役口径(目标文本见 §2.1)。明确不解决:域表其余行(逐行核对不在本屏辖域);域/字段语义本体(单一源 = fields.md,本行只做摘要级对齐)。

### 1.2 F-2(中)补给逐动作专篇与索引行停留在「到账登记」代语义

- 现状症状:`game_state/logic-updates/pick-supply.md` 全篇四处与现役实现不符:①§2 称「容器主体零写 + 本族唯一确认到账登记面」,现役 = 即时单相一口写;②`register_confirm_arrival`(op='ConfirmSupply')→ `apply_confirm_effect` 补给分支链已退役(src 零命中,仅存 ConfirmTome/ConfirmExpertCash 在册面);③`chosen_supply` 被标为「观察写端/观察写入边」,现役 = 画面 op 选卡分支确认即写 write_logic(渠道族 logic_action);④§6 kernel 符号锚仍指向已退役调用链。同目录 README.md「事件线 pick 族」表 PickSupply 行(约 L58)同步同病(报告 F-2;报告另证:迭代 landing.md 正本更新清单未含 logic-updates 两篇,全 progress 树无该欠账登记)。
- 根因归层:语义层——专篇停留在上一代「到账登记」语义未随批改写;约定层——索引行与专篇同源漏更。
- 解决到哪:pick-supply.md 全篇按现役改写(目标全文见 §2.2);README PickSupply 行给目标语义与实施要件(见 §2.2 末)。明确不解决:`pick-encounter.md` 同病(仍称零写族+观察写端,与 fields.md §3.4.1「动作侧发射即写」矛盾)——归 T-4(遭遇)稿辖域(其 README 条目经 T-1 条 5 并入实施);`cw_vocab.py::CwActionPickSupplyParam` docstring 现文已即时单相口径(旧盘面「两相」措辞已随迁移批消失,无需修);其残余 `design §2.0B` 指针在 cw_vocab.py(本稿三文件之外),归 §2.7 全仓 changes/ 引用清理批辖域。

### 1.3 F-3(中)fields.md 三处未随即时单相批同步

- 现状症状:`game_state/fields.md` ①§3.2.15 装备库存写端清单(L450-464)末句「补给/事件获得的装备不记预期值,经观察覆盖收口(§4.1 豁免)」与现役 `pick_supply.py` 装备腿(owned += 规范名即时写)直接矛盾;②§4「事件选择(10 屏)」段(L1070-1083)把补给列进「默认不记预期值」名单——该段只改写了遭遇行(「遭遇臂 = 动作侧发射即写」),补给效果腿未改,且段内「有显式到账登记的照登记」所引载体对补给已退役;③§3.2.5 备战席自称「写端(完整清单)」的逻辑写端列表无补给单位腿(`grant_bench_unit_cascade`)(报告 F-3)。
- 根因归层:语义层——字段级正本三处未随批同步(landing 清单对 fields.md 只覆盖 §3.4.1/§3.4.2 与 §4 遭遇行)。
- 解决到哪:三处各补/改条目到现役口径(目标文本见 §2.3),含节标题计数联动,与 §3.4.1/§3.4.2 已改行同构自洽。明确不解决:§3.2.16 消耗品的同款豁免句(补给选择不产消耗品,不在发现面);§4.2 各 op 写入面不新增 PickSupply 专条目(事件线选择 op 的写入面统一住 §4「事件选择」段,与遭遇同构,依据 = fields.md §4 现行结构);§3.4.2 补给屏节不动(刷新剩余/刷新链行已现役);§4 段内邻句「余屏(命运卜者/装备三选一/骇入策划)写端未接线=先补档」(L1077-1078)已随两相清偿批失真(装备/策划现役即时单相上报效果腿,装备屏 chosen = 选择存证已退役)——归装备/策划两屏审查辖域(现无在册稿,挂 T-37 或全仓文档清理批),本稿只清补给臂。

### 1.4 F-4(低)动作 op 模块头「自上报统一」段残留史述与过程件指针

- 现状症状(代码现值):报告 F-4 摘录的旧文本(「上报发射相零写……由画面 op 原写点承载」「三线例外:pick_invest / pick_equip / pick_supply = 分步实现」)已随并行迁移批(投资两屏/供给/装备/策划全域清偿,planner/equip 现役 = 即时单相,action_ops.md §4.5 PickPlanner/PickEquip 行已同步)改写消失。段内现残留三处:①段首「撤销 2026-09-18 动作 op 重组批 §1.1『零上报例外登记』」——变更史叙述 + 指向过程件节号(AGENTS.md §8「变更史不进注释」);②「原『发射/落地两相』例外……已随投资两屏、供给、装备、策划各迁移批全域清偿(迭代 2026-09-21……)」——变更史叙述,其现役结论已由段内后句「现役全族 = 机械链发出后立即一口写完整结果」承载;③同文件模块头 L3 裸「design.md §1.1/§1.2」指针(无迭代名,悬空度更高)——归 F-7 清单一并处置。
- 根因归层:约定层(注释面)——迁移批改写了语义但留下变更史叙述与过程件指针。
- 解决到哪:**让渡(见 §2.4)**——该段归口经汇总任务 T-37 终裁 = T-4 修订版 encounter.md §2.3,本稿不持段改写规格,仅保留补给侧核对要点。明确不解决:planner/equip 的上报语义面(迁移批已落地,归其辖域);其他 op 类注释语义;泛化批名出处标签(见 §2.7 收敛判据)。

### 1.5 F-5(低)read_supply_options docstring 过期句

- 现状症状:`obs/cw_node_obs.py::read_supply_options` docstring 称「**无刷新按钮**(decide_supply 调用方传 `refresh_used=True` 跳过刷新逻辑)」——①刷新圆钮实存(screen op `_REFRESH_BTN_DX(-100)` 文本锚定点击链在役,刷新臂为终结动作);②`refresh_used` 引用已退役的「已用计数」语义,现役 = 容器剩余读数闸(`supply_refresh_left` 剩余语义观察真值,同名形参现仅作布尔旗标留存于 `cw_events.py::decide_supply` 签名)(报告 F-5)。读链本体(列探测/钻双通道/配对)与 supply.md §3 一致,仅此句过期。
- 根因归层:约定层(注释面)——旧「无刷新钮+已用计数」代语义残留。
- 解决到哪:该句改写为现役口径(目标文本见 §2.5)。明确不解决:`cw_events.py::decide_supply` 的 `refresh_used` 形参命名与 docstring(不在补给链三文件辖域,行为现役正确——闸已上移容器剩余读数,依据 = T-5-r1 §3.9)。

### 1.6 F-6(低)screens/supply.md §9 journal op 名不全

- 现状症状:§9 记「journal op 名 =『补给节点』」,代码 `CwScreenSupplyNode.__init__` 实参 = `'货币战争-补给节点'`,运行记录按 `operation=self.op_name` 落;按文档名检索会落空(报告 F-6)。
- 根因归层:表示层——文档少写命名空间前缀,检索面失配。
- 解决到哪:补全前缀(见 §2.6)。明确不解决:§9 其余锁面清单(报告已核无误)。

### 1.7 F-7(低)补给链代码注释引用 changes/ 过程件

- 现状症状:补给链三文件注释中存在指向 `changes/` 过程件的指针——「design §N」「design.md §N」、裸「design.md」、具名迭代引用(「迭代 <名>」可检索到 `changes/<名>/`)——changes/ 属可随时删减的过程区,引用随删减悬空,违反根 AGENTS.md §9「代码与正本文档禁引 changes/ 内容」铁律。**全集基线 = 修订时对三文件全量 grep(`design|迭代`)的现值命中,共 19 处**(分布 9/9/1;含报告 F-7 点名处、其代表性摘录之外的同型处、以及并行迁移批新落地的引用;逐处清单见 §2.7)。
- 根因归层:约定层——迭代落地时注释里的过程件指针未按铁律收敛为正本指针或纯语义描述。
- 解决到哪:三文件逐处收敛(目标文本见 §2.7)。明确不解决:同族形态在域外的扩散面——代码注释已见 `cw_events.py::decide_supply` docstring「design 07/08」、`cw_vocab.py` 多处「银狼闭环迭代 design.md §2.2」;**正本文档同有实锤**(fields.md §3.4 头部 L726-727「遭遇/补给的已用计数字段已随剩余语义化退役,归迭代 2026-09-21-event-refresh-unify-supply-pick §3.4.1/§3.4.2」带节号引用,AGENTS §9 同判正本文档禁引)——建议另立全仓「changes/ 引用清理批」(见 §2.7 联动面标注)。

### 1.8 已核对一致面

报告 §3「已核对无问题项」1-15 条(两 node 形态/读屏点纪律/推进形态/确认即写行为/刷新终结臂+剩余闸/派发即终结/一口写行为/观察上报规约/决策铁律/终结语义/九节 as-built/建档/退役符号零残留/测试锁在册/迭代对照)全部不立修法,本稿不触碰其承载的代码与文档面。

## 2. 方案

修法全部为文档与注释面的语义改写,零行为变更(代码可执行面不动);以下逐发现给目标文本,实现者照抄即可,无需再设计。

### 2.1 F-1 修法:game_state/README.md §3.3 域表行整行改写

目标文本(整行替换现 L114 行;markdown 表格行,列序 = 域(gs_schema 键)| 字段全集 | 主写渠道):

```
| 节点屏刷新计数域(node_screen_refresh) | env_refresh_left / strategy_refresh_left(逐卡,键 = 注册表规范卡名)/ encounter_refresh_left / supply_refresh_left(四字段均剩余语义:屏显「剩余次数」观察真值;旧 `*_refresh_used` 已用计数字段已退役,考古走 git) | ①观察(各屏观察 report 摄入,读缺跳写、None = 未观察 = 拒绝;encounter 写端 = `report_screen_encounter_obs`)+ sim 写端(仅 supply_refresh_left;遭遇/投资两屏无 sim 刷新执行面;逐字段规格 = fields.md §3.4.1–§3.4.4) |
```

依据(fields.md 字段级正本,本行为摘要级对齐):四字段语义与写端 = fields.md §3.4.3(env,观察写端)/§3.4.4(strategy,逐卡键 = normalize_invest_name,观察写端)/§3.4.1(遭遇,观察写端 `report_screen_encounter_obs`、读缺跳写、None = 未观察 = 拒绝、「sim 无遭遇刷新执行面 = 无 sim 写端」)/§3.4.2(补给,观察写端 + sim 写端「入口先写初始 left=1、刷新 left−1 ≥0 截断」);已用计数退役 = op-layer.md §1.4/§2.2、action_ops.md §2.3(「原 on_outcome 发射型钩子与 live +1 写点均已退役」)。

**交叉面声明(与 T-4 稿,裁决性)**:本行同时被 T-4(遭遇)审查命中,T-4 稿(encounter.md 其域表行条目的目标行)与本稿并存两版完整行文本。**实施时行文本以本稿 §2.1 为准,T-4 稿对应目标行版本作废**——T-4 版独有信息(「None = 未观察 = 拒绝」「encounter = `report_screen_encounter_obs`」「逐字段规格 = fields.md §3.4.1–§3.4.4」)已吸收进上行,两版语义兼容、行文本唯一化后无信息损失;**此裁决挂汇总任务 T-37 登记**。

### 2.2 F-2 修法:pick-supply.md 全篇改写 + README 索引行目标语义

pick-supply.md 整文件替换为以下目标全文:

```markdown
# 补给选择(PickSupply)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。事件线 pick 族五篇之一;本动作契约正本 = [flow/action_ops.md](../../flow/action_ops.md) §4.5(PickSupply 行)。

## 1. 动作是什么

补给节点弹窗点选一个候选并确认,选中内容(角色/装备)随确认即时入账。词表 = `kernel/cw_vocab.py::CwActionPickSupplyParam`(字段:`idx` = 画面候选下标 0 起(payload 槽 options 列表序)、`reason` = 归因记录字段、`char_name` = 选中列角色名('' = 列无角色/兜底点卡路径)、`norm_item` = 选中列装备归一规范名('' = 未解析;`kernel/cw_events.py::normalize_registry_equip_name` 分层归一现算:精确快道 → containment longest-first → 相似救援唯一命中))。op 载体 = `operations/cw_op/cw_overlay_pick_action.py::CwActionPickSupplyOp`(域 env = `OverlayPickExecEnv`;发射位 = `CwScreenSupplyNode._do_action` 经注册表工厂 `action_op_for` 派发)。

## 2. 逻辑态域集

**即时单相一口写**(用户裁定 2026-09-21 = [flow/action_ops.md](../../flow/action_ops.md) §1 增补 2;上报函数 = `kernel/cw_action_report/pick_supply.py::report_action_pick_supply_param`,确认点击后一次调用写全部效果逻辑态,无发射/落地两相、无到账登记、无证据闩):

- **装备腿(确定面)**:`norm_item` 在场 → owned += 归一规范名(`gs.equips` write_logic,账面恒标准名)+ 获得后果链 `kernel/cw_effect_inventory.py::apply_equip_acquire_consequence`(命中后果表送角色腿 → bench + 级联);`norm_item` = '' → 禁猜,equips 值不变翻来源 + `pick_supply_name_unresolved` 留证(fail-closed:错名不入账,观察覆盖自愈);
- **单位腿(确定面)**:`char_name` 在场 → `kernel/cw_effect_inventory.py::grant_bench_unit_cascade`(入席 1★ + 合成级联,与商店购买同语义);
- **内容全未知**(兜底点卡路径,char_name 与 norm_item 双空):bench/equips 值不变翻来源(`write_logic_rand`)+ `pick_supply_content_unresolved` 留证;
- **选择落地 `chosen_supply`**:画面 op `CwScreenSupplyNode` 选卡分支**确认即写 write_logic**(值 = (角色, 装备, 有钻石);渠道签名 family='logic_action'、actor='CwScreenSupplyNode',journal 记录为逻辑源非观察源;兜底点卡/刷新轮不写 = 真选守卫)——动作事实边界例外③([../screens/op-layer.md](../../screens/op-layer.md) §2.2),**非观察写端**;
- 刷新臂不在本动作:刷新圆钮机械点击留守画面 op 留守臂(刷新链 = `CwActionRefreshSupplyParam` 决策建议的执行半,终结形态交回);节点推进 = 确认点击落地即旁调 `kernel/cw_game_state.py::report_node_advance(trigger='supply_confirm')`(kernel 观察态门 = 唯一推进落账门)。

## 3. 确定面转移规则(逐条)

1. 点卡选中:定位点 = `env.target`(决策半从 screen_info/OCR 现算;op 类体内不自算)→ mouse_move + click → 固定等待 0.6s;
2. 确认:`round_by_find_and_click_area`(screenshot, '货币战争-补给', '按钮-确认', success_wait=1.5);
3. **即时自上报**:确认点击后无条件调 `report_action_pick_supply_param`(不判 confirm_result):装备腿 + 单位腿一口写;派发即终结,确认未生效由外循环按当前画面重识别重派(零判效零重试);
4. **推进上报**:`confirm_result.is_success` 门内旁调 `report_node_advance(trigger='supply_confirm')`(is_success 门 = 发出事实门,非判效;重复上报被 kernel 观察态门结构性挡)。

## 4. 随机面

补给候选内容(角色/装备/钻石)= 随机面归观察;上报按确定面即时入账(owned/入席/后果),真值以下一帧观察覆盖为准(两态制,观察赢);内容不可辨 = 受影响域值不变翻来源留证,禁猜、禁伪造确定面。

## 5. 拒绝语义

零验证确认链:确认未落地(overlay 残留)不重试不判效——下一轮外循环重识别重派;定位点缺失由决策半现算面处置(执行面不兜底坐标);归一件名多/零命中与内容双空 = 非拒绝面,按「内容未知/未解析」翻来源留证(上报 applied=True 受理,零效果写)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionPickSupplyParam`;`operations/cw_op/cw_overlay_pick_action.py::CwActionPickSupplyOp` / `OverlayPickExecEnv`;`kernel/cw_action_report/pick_supply.py::report_action_pick_supply_param`(写语义单点);`kernel/cw_effect_inventory.py::grant_bench_unit_cascade` / `apply_equip_acquire_consequence`;`kernel/cw_events.py::normalize_registry_equip_name`(归一件名现算);`kernel/cw_game_state.py::chosen_supply` / `report_node_advance`;`operations/cw_screen/cw_screen_supply_node.py::CwScreenSupplyNode`(确认即写写点/发射位)。

## 7. 语义验证

行为锁 = `test_cw_supply_pick_immediate_report.py`(即时单相写序)/ `test_cw_pick_channels_t60.py`(分层归一)/ `test_cw_supply_advance_wiring.py`(推进接线)/ `test_cw_obs_arch_event_screens_step3.py`(chosen 确认即写),在册路径 = `sr-od-test/test/sr_od/application/currency_war/`;owned 真值 = 下一帧装备区读数观察覆盖。

## 8. 判例注记(发射期)

补给节点画面期;发射位 = 画面 op act 段经注册表工厂分派。

## 9. 依据

`kernel/cw_action_report/pick_supply.py` 模块头(写序/腿型/留证分型);`operations/cw_op/cw_overlay_pick_action.py::CwActionPickSupplyOp` docstring 与 run 体(刷新臂留守/即时上报/推进旁调);[flow/action_ops.md](../../flow/action_ops.md) §4.5(PickSupply 行)与 §1 增补 2;[../fields.md](../fields.md) §3.2.15/§3.2.5(效果腿)/§3.4 头部(chosen 确认即写)/§4「事件选择」补给臂;[../../screens/supply.md](../../screens/supply.md) §4/§6(画面 op 侧契约)。
```

logic-updates/README.md「事件线 pick 族」表 PickSupply 行(现 L58)目标语义:

```
| PickSupply | `CwActionPickSupplyOp` | [pick-supply.md](pick-supply.md) | `report_action_pick_supply_param`(即时单相一口写:owned 规范名 + 单位腿 `grant_bench_unit_cascade` + 装备后果腿 `apply_equip_acquire_consequence`;内容未知/名未解析 = 翻来源留证;选择落地 = `chosen_supply` 画面 op 确认即写) |
```

依据:现役写序单一源 = `kernel/cw_action_report/pick_supply.py` 模块头与函数体;契约 = action_ops.md §4.5 PickSupply 行、screens/README.md §5.5、supply.md §6;chosen 渠道 = `cw_screen_supply_node.py` 选卡分支 write_logic(family='logic_action')。退役面佐证 = T-5-r1 §3.13(ConfirmSupply src 零命中)。

**交叉面声明(与 T-1 稿,含实施要件)**:logic-updates/README.md 索引面归 T-1 统改(prep.md 索引面条目;T-4 对该 README 的条目亦并入 T-1 实施)。**T-1 实施时 PickSupply 行以本稿 §2.2 目标全文为准(含 chosen_supply 渠道申报)**——该申报不在转录源 `pick_supply.py` 模块头中(chosen 渠道住 `cw_screen_supply_node.py` 选卡分支与 supply.md §6),T-1 稿「上报函数列 = 机械转录各上报函数模块头现值」的转录粒度对此行不适用;**此裁决挂汇总任务 T-37 登记**。另注:同表 PickEncounter 行同病(称零写族+观察写端)归 T-4 稿辖域,经 T-1 条 5 并入实施,本稿不认领。

### 2.3 F-3 修法:fields.md 三处

**(1) §3.2.15 装备库存(写端清单段,L450-464)**:
- 「逻辑写端(op,§4.2)」列表末尾(SellBench 项后)追加一项:`;PickSupply 补给即时获得腿(owned += 归一规范名 + 获得后果链 `apply_equip_acquire_consequence`,即时单相;`kernel/cw_action_report/pick_supply.py`)`
- 末句改写。现:「补给/事件获得的装备不记预期值,经观察覆盖收口(§4.1 豁免)。」→ 目标:「补给获得的装备 = 即时预期值写(上行 PickSupply 腿,`flow/action_ops.md` §4.5 即时单相,账面恒归一规范名);遭遇等事件获得的装备不记预期值,经观察覆盖收口(§4.1 豁免)。」

**(2) §3.2.5 备战席(写端清单段,L274-277)**:
- 「逻辑写端(op,§4.2)」列表末尾(SellBench 项后)追加一项:`;PickSupply 补给单位腿(`grant_bench_unit_cascade` 入席 1★ + 合成级联,与商店购买同语义;`kernel/cw_action_report/pick_supply.py`)`

**(3) §4「事件选择」段(L1070-1083)**:
- 节标题计数联动:现标题「#### 事件选择(10 屏)」→ 目标「#### 事件选择(9 屏)」(首句名单摘除「补给/」后剩 9 屏,标题与名单计数必须同批改,防出现标题 10 屏/名单 9 屏的自相矛盾——与 F-1 ③ 同型病);
- 首句名单摘除「补给/」:改后为「遭遇/盛会之星/伙伴/祈愿试炼/命运卜者/骇入策划/专家邀请函/星徽秘典/装备三选一的选择落地:**默认不记预期值**(选择瞬间画面即切,无定型帧可核对),后果走观察覆盖+缺陷台账;有显式到账登记的照登记——先例=专家邀请函屏「现金为王」兜底选项 gold+4(……原括注不动)」。
- 「遭遇臂」句之后、「遭遇/补给刷新闸全域」句之前插入:

```
**补给臂 = 即时单相效果写**(对齐遭遇臂的动作侧写形态;写端 =
`kernel/cw_action_report/pick_supply.py`,确认点击后一口写,
`flow/action_ops.md` §4.5 PickSupply 行):equips owned += 归一规范名 +
bench 单位腿(`grant_bench_unit_cascade` 入席 1★+合成级联)+ 获得后果链
(`apply_equip_acquire_consequence`);内容全未知/名未解析 = 受影响域值
不变翻来源 + 缺陷留证(禁猜);选择落地 = `chosen_supply` 画面 op 确认即写
(§3.4 头部口径;原「到账登记 ConfirmSupply」载体已退役,考古走 git)。
```

自洽校验:修后 §3.2.15/§3.2.5/§4 与 §3.4.1/§3.4.2 同构对齐(遭遇臂/补给臂句式一致;刷新闸两行已现役);§3.4 头部通用机制段「补给经画面 op 选卡分支确认即写」为现役口径不动(依据 = fields.md L718-727);「chosen_* 写端已接七屏」句含补给仍为真,不动。**段内邻句归属声明**:同自然段「余屏(命运卜者/装备三选一/骇入策划)写端未接线=先补档」(L1077-1078)已随两相清偿批失真(装备/策划现役即时单相上报效果腿,依据 = action_ops.md §4.5 PickEquip/PickPlanner 行现值;装备屏 chosen = 选择存证已退役,依据 = `CwActionPickEquipOp` docstring)——归装备/策划两屏审查辖域(现无在册稿,挂 T-37 或全仓文档清理批),本稿只清补给臂、不认领该句。依据:现役写序 = `pick_supply.py` 模块头;契约 = action_ops.md §4.5、supply.md §6;退役佐证 = T-5-r1 §3.13。

### 2.4 F-4 修法:让渡声明(模块头「自上报统一」段归口 = T-4 修订版 encounter.md §2.3)

**归口裁决**:汇总任务 T-37 登记条目③改口条终裁——模块头「自上报统一」段(语义面与注释纪律面)归口 = **T-4 修订版 encounter.md §2.3**;**本稿前版 §2.4 段规格(「残留史述收敛」整段替换文本及其「以本稿为准」交叉面声明)作废**,本稿改为让渡声明,不持该段改写规格。

依据:T-4 修订版 encounter.md §2.3 已承接施工权——其「残留修法 3——模块头段史述收敛(经 T-37 归口自 T-5 §2.4 承接)」完整覆盖本稿 F-4 发现本体:两处史述删除(①段首「撤销 2026-09-18 动作 op 重组批 §1.1『零上报例外登记』」;②「原『发射/落地两相』例外……已随投资两屏、供给、装备、策划各迁移批全域清偿(迭代 2026-09-21……)」句),保留面口径与本稿前版一致(泛化批名标签 pick-op-unify 批/「零写族落 zero_writes」/持久索引「用户裁定 = action_ops.md §1 增补 2」);其归口声明如实记录:本稿前版规格与代码无矛盾,停工依据 = 归口裁决而非规格失真(dag.jsonl T-37 条目③改口条在册)。

**本稿保留的补给侧核对要点**(实施与验收时的补给侧对照面,非改写规格):

1. 段申报「现役全族 = 机械链发出后立即一口写完整结果」对补给行的现值核对 = `CwActionPickSupplyOp` docstring 与 run 体(确认点击后无条件调 `report_action_pick_supply_param` 一口写 + `confirm_result.is_success` 门内旁调 `report_node_advance(trigger='supply_confirm')`;pick_equip/pick_planner 现役同为即时单相,三方一致,action_ops.md §4.5 两行已同步);
2. 报告 F-4 摘录的旧文本(「三线例外:pick_invest / pick_equip / pick_supply = 分步实现」)已不存在——supply 侧无残留收敛面;该段后续若再漂移,按 T-4 修订版 §2.3 声明的「模块头 + 函数体/调用方 run 体双证」重新核录,不以任何稿面转述为准;
3. §2.7 清单 #10(模块头 L3 裸 design.md §1.1/§1.2)在「自上报统一」段(L15-24)之外,属 F-7 清单实施,**不受本归口裁决影响,保留在本稿清单内**。

### 2.5 F-5 修法:read_supply_options docstring 过期句改写

现句(obs/cw_node_obs.py L294):「**无刷新按钮**(decide_supply 调用方传 ``refresh_used=True`` 跳过刷新逻辑)。」→ 目标:

```
**刷新圆钮实存**(「剩余次数」文本锚左侧固定偏移点击,宿主 = 画面 op
留守臂 ``cw_screen_supply_node.py``;本读链只读选项,不读刷新剩余——
剩余读数闸 = 容器 ``supply_refresh_left`` 剩余语义观察真值,由画面 op
观察 node 同帧读经 report 摄入,全域规范 = ``screens/op-layer.md`` §1.4)。
```

依据:`cw_screen_supply_node.py` 模块头与 `_REFRESH_BTN_DX(-100)` 注释(文本锚定点击链在役,刷新臂 = 终结动作);`supply_refresh_left` 写端 = fields.md §3.4.2(观察写端 + sim 写端);读屏分工 = supply.md §3(选项读链归 obs reader、剩余读数归画面 op `_read_refresh_anchor`)。

### 2.6 F-6 修法:screens/supply.md §9 journal op 名补全

现文:「journal op 名 =「补给节点」;」→ 目标:「journal op 名 =「货币战争-补给节点」;」(余句不动)。依据 = `cw_screen_supply_node.py::CwScreenSupplyNode.__init__` `op_name='货币战争-补给节点'`,运行记录落名 = `operation=self.op_name`(one_dragon/base/operation/operation.py;T-5-r1 §2 F-6)。

### 2.7 F-7 修法:补给链三文件 changes/ 引用收敛为正本指针或纯语义

收敛判据:清除对象 = ①「design §N」「design.md §N」及裸「design.md」指针;②具名迭代引用(「迭代 <名>」形态,可检索到 `changes/<名>/` 的)。保留 = 纯日期「迭代 2026-09-21,」(无名称不可检索悬空)与泛化批名出处标签(pick-op-unify 批/统一动作工厂批4/动作 op 重组批③ 等无对应目录检索入口)。收敛方向 = **正本指针优先**(`docs/develop/sr_od/application/currency_war/` 下 screens/flow/game_state 正本,禁悬空),指针无承载节或语义自足处用纯语义描述。逐处清单(**全集 = 修订时三文件全量 grep(`design|迭代`)现值命中 19 处**;行号 = 现值,并行批可能再位移,实施按定位描述落点):

**cw_screen_supply_node.py(9 处)**

| # | 定位(现值行号) | 现文(摘要) | 收敛方式 |
|---|---|---|---|
| 1 | 模块头 L24 | 「形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段直继承……」 | 删具名迭代标签:「形态:观察 node + 决策动作 node 两段直继承 SrOperation。……」(语义句自足) |
| 2 | 模块头 L26-27 | 「迭代 2026-09-20-node-advance-action-report design §2.3 触发点 2/§2.4 写端 2——补给『自动弹』形态的唯一锚定点」 | 改双指针:「锚定写端在册 = `screens/op-layer.md` §2.1;节点条锚定四分支处置规则表正本 = `game_state/node-derivation.md`(E10 行)——补给『自动弹』形态的唯一锚定点」 |
| 3 | 模块头 L32-35 | 「(迭代 2026-09-21-event-refresh-unify-supply-pick design §2.0B:动作 op 确认点击后立即上报完整结果,零重入裁决、零落地相补写面……)」 | 改正本指针:「(派发即终结正本 = `screens/op-layer.md` §1.1、`flow/action_ops.md` §4.5:动作 op 确认点击后立即上报完整结果,零重入裁决、零落地相补写面——确认未生效 = 代码 bug,overlay 残留由外循环按当前画面重识别重派)」 |
| 4 | 观察 node 注释 L195-197 | 「……divert 形态 = 备战帧已锚,本读数走处置规则表 reanchor/stale_dropped 分支承接,design §2.2/§2.4 写端 2)」 | 尾句改「……分支承接,处置规则表正本 = `game_state/node-derivation.md`(E10 行))」 |
| 5 | act docstring L218-220 | 「(迭代 2026-09-21-event-refresh-unify-supply-pick design §2.0B,零重入裁决、零落地相补写面)」 | 改「(正本 = `screens/op-layer.md` §1.1、`flow/action_ops.md` §4.5,零重入裁决、零落地相补写面)」 |
| 6 | 开出内容载荷注释 L247-249 | 「# 开出内容载荷(迭代 2026-09-21-event-refresh-unify-supply-pick:空串 = 兜底点卡路径/装备名未解析……)」 | 删迭代名指针,余句语义自足:「# 开出内容载荷(空串 = 兜底点卡路径/装备名未解析——报告侧按『内容未知/未解析』分型翻来源留证)」 |
| 7 | 选定快照注释 L252-253 | 「# 现役消费面 = 零(design §2.1:选定事实现场载荷,遥测接线候批)」 | 改「# 现役消费面 = 零(选定事实现场载荷,遥测接线候批)」 |
| 8 | 选定快照注释 L291-294 | 「……无『本局初始授予数』基线故携带而非推导,design §2.1)——」 | 删「,design §2.1」,余句不动 |
| 9 | 派发注释 L345 | 「# 内容空 = 报告侧内容未知分型)。派发即终结(design §2.0B)。」 | 删节号,纯语义:「……派发即终结。」(同语义正本指针已由 #3 承载,不复写) |

**cw_overlay_pick_action.py(9 处)**

| # | 定位(现值行号) | 现文(摘要) | 收敛方式 |
|---|---|---|---|
| 10 | 模块头 L3 | 「……构造 = (ctx, param, env),design.md §1.1/§1.2)。」(裸 design.md,无迭代名) | 删「,design.md §1.1/§1.2」(换壳描述语义自足;在「自上报统一」段 L15-24 之外,属 F-7 清单实施,不受模块头段归口裁决影响) |
| 11 | OverlayPickExecEnv docstring L124-125 | 「``leg_type``/``norm_item`` = 银狼策划腿型载荷(银狼闭环 design §2.1①;决策半经 ``classify_planner_leg`` 现算,随派发透传……)」(族公共面,补给 op 消费此 env,无从让渡) | 删「银狼闭环 design §2.1①;」节号指针,余句不动(其现值已由迁移批改写为「确认点击后立即上报完整效果腿」口径) |
| 12 | CwActionPickSupplyOp docstring L199-200 | 「**即时上报**(action_ops.md §1 增补 2,迭代 2026-09-21-event-refresh-unify-supply-pick):」 | 改「**即时上报**(契约单一源 = `flow/action_ops.md` §1 增补 2 与 §4.5 PickSupply 行):」 |
| 13 | CwActionPickSupplyOp run 注释 L231-232 | 「# 立即自上报完整结果(design §2.0B 单相:owned += norm_item 规范名 + 单位腿 + 装备后果腿;……)」 | 删「design §2.0B 」字样:「# 立即自上报完整结果(单相:owned += norm_item 规范名 + 单位腿 + 装备后果腿;……)」 |
| 14 | CwActionPickMegastarOp docstring L272 | 「(单次逻辑写入豁免面,派发前写——时序申报见迭代 design.md §2)。」 | 删「——时序申报见迭代 design.md §2」(「单次逻辑写入豁免面,派发前写」自足;巨星写时点正本 = op-layer.md §2.2 动作事实边界) |
| 15 | CwActionPickPlannerOp docstring L374-375 | 「**即时上报**(action_ops.md §1 增补 2,迭代 2026-09-21-pick-planner-equip-immediate-report):」 | 删「,迭代 2026-09-21-pick-planner-equip-immediate-report」(「action_ops.md §1 增补 2」保留) |
| 16 | CwActionPickPlannerOp run 注释 L420 | 「# 立即自上报完整结果(design §2.0/§2.1 单相:确认点击后一口写腿型分派效果……)」 | 删「design §2.0/§2.1 单相:」字样,余句不动 |
| 17 | CwActionPickEquipOp docstring L586-587 | 「**即时上报**(action_ops.md §1 增补 2,迭代 2026-09-21-pick-planner-equip-immediate-report):点卡后……」 | 删「,迭代 2026-09-21-pick-planner-equip-immediate-report」(「action_ops.md §1 增补 2」保留) |
| 18 | CwActionPickEquipOp run 注释 L612 | 「# 立即自上报完整结果(design §2.0/§2.1 单相:点卡后一口写装备入栏 + 获得后果链……)」 | 删「design §2.0/§2.1 单相:」字样,余句不动 |

**pick_supply.py(1 处)**

| # | 定位(现值行号) | 现文(摘要) | 收敛方式 |
|---|---|---|---|
| 19 | 模块头 L3-4 | 「**即时单相上报**(迭代 2026-09-21-event-refresh-unify-supply-pick design §2.0B;用户裁定 2026-09-21 = action_ops.md §1 增补 2:……)」 | 改「**即时单相上报**(行为正本 = `flow/action_ops.md` §4.5 PickSupply 行;用户裁定 2026-09-21 = action_ops.md §1 增补 2:……)」 |

**完成验证门(可执行)**:收敛完成后,三文件内 grep `design` 应零命中;grep `迭代 20\d\d-[a-z]`(具名迭代)应零命中;「迭代 2026-09-21,」(纯日期,cw_overlay_pick_action.py 模块头现 L21)与泛化批名标签不在清零面。清单执行完毕后验证门即绿——清单与验证门同源(同一次全量 grep 的现值),不存在「清完仍红」的剩余命中面。

**指针合法性依据**:op-layer.md §2.1 仅承载锚定写端在册申报(「锚定写端 = `CwScreenPrep`/`CwScreenSupplyNode` 观察 node(→ `observe_node_anchor`)」一句),**不承载处置规则表**——四分支处置(first_anchor/advance 补推/reanchor/stale_dropped)正本 = `game_state/node-derivation.md`(§3.3-4 四分支处置;场景走查 E10 行完整承载原注释语义:「补给屏节点条锚定(CwScreenSupplyNode 读『备战阶段 X-Y』节点条 → `observe_node_anchor`;自动弹形态唯一锚定点);divert 形态备战帧已锚,本读数走 reanchor/stale_dropped 分支」);派发即终结正本 = op-layer.md §1.1;动作契约正本 = action_ops.md §4.5(PickSupply/PickPlanner/PickEquip 行)与 §1 增补 2。均为正本区稳定节(AGENTS.md §9 双层文档流,正本必须自足)。

**同族联动面标注**:该「changes/ 引用」形态不限于代码注释——**正本文档同有实锤**(fields.md §3.4 头部 L726-727 带节号引用迭代 §3.4.1/§3.4.2,AGENTS §9 同判正本文档禁引);域外代码已见 `cw_events.py::decide_supply` docstring「design 07/08」、`cw_vocab.py` 多处「银狼闭环迭代 design.md §2.2」等同型指针。建议另立**全仓 changes/ 引用清理批**:grep 范围 = `src/` 代码注释 + `docs/` 正本区(screens/flow/game_state 等),逐处收敛正本指针或纯语义;本稿只清补给链三文件,不扩查不扩改。

**交叉落点统一登记**:域表行(§2.1)与 README PickSupply 行(§2.2)两处交叉落点以汇总任务 T-37 登记为准;模块头「自上报统一」段已终裁归 T-4 修订版 encounter.md §2.3(T-37 条目③改口条),本稿 §2.4 为让渡声明,不构成第三处落点。

### 2.8 关键取舍

1. **F-1 域表行「本稿版本为唯一落点,T-4 版作废」而非双版并存**:两版语义兼容但行文本唯一性必须上游裁决——双版并存时实施者拿任一单稿都无法确定行文本;本稿吸收 T-4 版独有两处信息后以 T-5 版收口,裁决挂 T-37 显式登记。代价 = T-4 稿对应条目失去落点(以作废声明 + T-37 登记保序)。
2. **F-2 chosen_supply 渠道标注为「确认即写 write_logic(逻辑源)」而非保留「观察写端」名**:旧名与值来源事实相反(sig family='logic_action',journal 为逻辑源;依据 = cw_screen_supply_node.py 选卡分支写点),保留旧名会把渠道族封闭集的核对面搅混;代价 = 与部分旧遥测文档措辞不一致,以本稿 + fields.md §3.4 头部为准。
3. **F-2 README 索引行「让渡 + 实施要件」而非本稿顺手改**:索引行措辞受 T-1 全表统改约束(表头/映射粒度由 T-1 定),单独改一行会与 T-1 批冲突;让渡必须附实施要件(chosen 渠道申报不在转录源模块头中,T-1 的机械转录粒度对此行不适用),否则链路在 T-1 侧断开、F-2 ③ 索引面无人修复。代价 = PickSupply 行修正晚于专篇到达,以 T-37 登记保序。
4. **F-3 摘除「补给」而非全句删除豁免**:「遭遇等事件获得的装备不记预期值」对遭遇仍为真(兑现回调防双源不直写数值,依据 = fields.md §3.4.1),句子的豁免面须保留;补给单列即时写条目,豁免句收窄到剩余事件屏。节标题计数同步改(9 屏),不为省一行字留下标题/名单矛盾。
5. **F-4 修法让渡而非保留规格**:模块头段归口经 T-37 终裁 = T-4 修订版 encounter.md §2.3,其「残留修法 3」与本稿前版规格语义一致并已承接施工权;保留本稿段规格会逆在册裁决行事、重演双规格并存。代价 = F-4 史述收敛面的施工与验收随归口移交,本稿只留补给侧核对要点(§2.4);§2.7 清单 #10 在该段之外,不受影响。
6. **F-7 收敛方式默认「正本指针」优先于「纯语义描述」**:同语义在正本已有承载节,指针比复述多一层防漂移(正本改了指针跟着节走);纯语义描述仅用于指针会显得空洞处(清单 #1/#6/#7/#8/#9/#10/#14)。代价 = 注释仍依赖正本节号稳定——所选节(op-layer §1.1/§2.1/§2.2、node-derivation E10、action_ops §4.5/§1 增补 2)均为结构性章节/走查行,可接受。
7. **全仓「changes/ 引用清理批」另立而非并入本稿**:清理面遍布代码注释与 docs 正本,需逐文件判读指针可替代性,与本屏设计节奏不同构;本稿只清辖域三文件并留判据、证据与可执行验证门,防清理批从零起稿。
