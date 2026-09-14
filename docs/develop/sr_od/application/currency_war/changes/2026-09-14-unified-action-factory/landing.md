# 统一动作工厂(unified-action-factory)落地

> 阶段唯一源:立任务 = 照本文件逐阶段 `dag.py add`;设计改 → 本文件改 →
> 账本跟着改。总纲 = [design.md](design.md)。
> 全局时序约束:批1 外部等待条件 = 2026-09-11-cw-clear-run 迭代收官实机局
> 完成(行为基线尺;跨账本条件,账本上记 cond 不记 deps)。
>
> **验证门口径(2026-09-14)**:本迭代各批的回归门 = ①全量测试绿
> `uv run pytest sr-od-test/ -m "not slow"`(CW 域测试按
> `sr-od-test/CW_TEST_SPEC.md` 七域规范分域落位,现役代表见该文 §1);
> ②批前/批后 diff 等价比对(逐节点 vs git HEAD,T-201 拆分批先例;审查
> 手续,非测试件)+ 遥测键/发射序列对照;③批判据点名的行为专锁随该批
> 交付,锁面落位遵循 CW_TEST_SPEC 域形态(源码扫描测试一律禁止,锁面
> 只准锁运行时行为,AGENTS.md §10.3)。任务书与账本 criteria 引用判据
> 以本节为准。

## 3.1 批1:通用基类升格 + 注册表单一 + 商店域搬家(零行为)

**范围**:`ShopActionOp` 升格 `ActionOp` + `ActionExecEnv` 协议
(design.md §2.2);新立 `cw_action_registry.py`(`_REGISTRY` +
`action_op_for`),商店六行在册,`shop_action_op_for` 转薄委托
(§2.3)。**不含**:备战/事件线入表;词表与坐标任何语义改动;
CompTransaction 行删除(行键先稳,删除归批2,R3)。
**设计依据**:design.md §2.1/§2.2/§2.3。
**文件面**:`operations/cw_op/cw_action_base.py`、
`operations/cw_op/cw_action_registry.py`(新)、
`operations/cw_op/cw_shop_actions.py`、`operations/cw_op/cw_shop_action_ops.py`、
`operations/cw_op/__init__.py`(再导出)、消费点
`operations/cw_screen/cw_screen_buy_cards.py`(如需改调新工厂)、
`sr-od-test/` 对应测试。
**依赖**:无(cw-clear-run 收官局为其 cond)。
**优先级建议**:8。
**完成判据**:
- 行为对照 design.md §2.2/§2.3:商店域动作发射序列、遥测键、guard 断言
  语义零变化(对照收官实机局基线口径);
- 回归门①+②(见卷首「验证门口径」)+ `ruff check` 本批文件零告警。
**验收凭据形式**:L1 通过记录 + `git diff` 面对照(零行为审查:diff 内
无语义改动)+ 消费点调用链核对。

## 3.2a 批2a:原子通路就位(语义批,账本节点一;裁决2)

**范围**(按内部步序执行,步间有依赖序):
1. **全仓符号扫描**(本节点第一步,报告同时供 2b 归一删除面使用;漏点不合格):四同名类 + `PREP_ACTION_TYPES`
   全类 + `CompTransaction`/`FillSpec` + 组合壳三件(RunDeploy/RunEquip/
   RunTools)+ `ClickSpheres` 的定义/构造/消费点(含 telemetry
   `serialize_action` 与 journal 判读工具、`tools/cw` 判读脚本);报告附
   任务书。
2. **原子通路就位**:`WearEquip` 与工具原子类按裁决1 定案命名
   (FurnaceUse/PrivilegeCardUse/WrenchUse/PrecisionWrenchUse/投影仪按
   型号两类/LuckyTokenUse,各带作用对象参数声明,坐标参数化,
   design.md §2.6);部署/穿戴计划构造 kernel 化(select_deployments 消费
   上移发射位;`_build_equip_wear_plan` 迁 kernel);WearEquip 零比对出生,
   旧 CV-diff 验穿批2 同批删(裁决3,穿没穿归观察写入边对账);发射面
   (mandate_v1 + cw_loop 出战链)改产原子动作(DeployMove/WearEquip/
   各工具原子类(裁决1)/SellDeployed/SellBench);`EXHAUSTION_WINDOW_ACTIONS` 白名单
    重推记录;LevelUp 逐帧单击形态(执行器单击化 + 逻辑态建模 + 决策
    判据每帧一击;2a 中间态定案:族B `LevelUp` 本批尚无 cost/auth_basis
    字段,金腿维持执行缝金差(`_executed_gold_delta`,执行包络留守)、
    逻辑态 LevelUp 分支只落 xp/level 推进不写 gold;cost(`xp_click_cost`
    现算,失读回退 `XP_CLICK_COST_FALLBACK`)与 auth_basis 分键装载
    随 2b 类合并翻转生效,翻转时金腿切 `action.cost` 直写,该切换落
    §3.2b 消费面收口);ClickSpheres 改形
   (载荷 = 有序球坐标列表,大球优先挑选迁 kernel 纯函数,执行器机械化);
   备战逻辑态建模扩域(逻辑态 = 动作执行后不经观察、按游戏规则推算预期
   状态并直写容器的状态;用户裁定 2026-09-14 正名,旧称「投影」;本批
   代码标识符不改名)(`apply_prep_action_logic` 域集 + xp/level 的
   LevelUp 分支;owned_equips 摘件;ClickSpheres 精确摘球);执行器
   `_level_up` 单击化、`_click_spheres` 机械化的体内语义半删除(授权/
   挑选/读屏选球归决策侧——本步含执行器体改,批3 只迁形);武装箱
   四选一独立画面 op(R7):新画面 op 独立立文件(「货币战争-备战-
   武装箱选择」,勿与 cw_screen_armory_box.py 道具说明弹窗混)+ cw_loop
    画面分发行 + OpenBox 开箱后本访问交回(终结化;`_project_prep_obs`
    OpenBox 分支删;交回等待值来源写死 = 现役 `_open_box` 动画等待
    `_OVERLAY_ANIM_WAIT_S`,`prep_actions.py:73`)+ PickBoxCard 全链删除(词表类/entry 发射点 :457/
   执行器 validate-分派-_pick_box_card-_default_box_card/adapter :106/
    cw_exec_state :308/:342),OCR 读卡名与调用编排自执行器
    (`_default_box_card`)迁新画面 op `cw_screen_box_pick.py`
    (decide_box_card 策略侧 / pick_equipment kernel 侧原位消费,
    不搬家);逻辑态全覆盖(R9):实现规格来源 =
    `flow/action-logic-state.md`(动作 op × 逻辑态计算枚举;该文档已
    在案,其 §3.3 备战 LevelUp 行现为连点旧形态「逻辑态显式不推进」
    申报、与 design.md 定案④相反,§3.7 PickBoxCard/§3.8 组合动作/
    §4 工具族亦随本批删除与新原子类过时;随本批落码同步转录:LevelUp
    行按 design.md 定案④重写、PickBoxCard/组合动作条目删、工具 7 类
    与 WearEquip 落 §4 新原子类形态,转录落码前先在 §3.3 加「待 2a
    转录,实现以 design.md 定案④为准」提示行防按旧语义施工),
   逐动作补逻辑态计算,废除未建模保守回退分支;知识缺口临时回退须带
   补档计划(随枚举文档标注)。

**设计依据**:design.md §2.1/§2.6(原子通路/逻辑态全覆盖段)/§2.7。
**文件面**:`kernel/cw_vocab.py`(新原子类入词表)、
`kernel/cw_prep_actions.py`(PickBoxCard 删 + 新类登记)、
`prep_actions.py`(体改)、`kernel/cw_deploy_logic.py`(部署计划构造
kernel 落位;穿戴计划/球挑选的 kernel 模块选址随任务书,单一源语义按
design.md §2.6 不变)、`operations/cw_loop.py`(发射链 +
EXHAUSTION_WINDOW_ACTIONS + 武装箱分发行)、
`operations/cw_screen/cw_screen_prep.py`(逻辑态 + 发射消费面)、
`operations/cw_screen/cw_screen_box_pick.py`(新;武装箱选择画面 op)、
`strategies/impl/mandate_v1/`(mandate/entry 发射面 + adapter 映射行删)、
`kernel/cw_exec_state.py`(PickBoxCard 分支删)、
`kernel/cw_game_state.py`(逻辑态写口 `apply_prep_action_logic`:
域集 `PREP_PROJECTION_DOMAINS` 扩 ('xp','level') + LevelUp 分支 +
owned_equips 摘件/ClickSpheres 精确摘球写口,按 design.md §2.6 R9)、
`decision_assembly.py`、`sr-od-test/` 回归与专锁。
**依赖**:批1(注册表行键先行就位);`flow/action-logic-state.md` 在案
(本节点实现规格来源;其与定案④相反的现状行随本批同步转录,见
范围第 2 步)。
**优先级建议**:7。
**完成判据**:
- 扫描报告在案(定义/构造/消费点全量,含 telemetry 与判读工具面;
  底册供 2b 逐点闭环);
- **LevelUp 形态锁**(2a 半):每帧至多一击;逻辑态 xp/level 推进与
  下一入口 heavy 对账闭合(中间态金腿 = 执行缝金差,不写 gold,
  2b 类合并翻转切 `action.cost` 直写);posture_unfulfilled 对账按
  新口径绿;
- **ClickSpheres 专锁**:载荷 = 有序球坐标列表;执行器零读屏选球;
  逻辑态按载荷精确摘球;
  观察四卡 → decide_box_card(策略侧)→ 点卡 → 确认 → 交回(选卡即
  终结,单选族例外);全仓无 PickBoxCard 构造/发射残留;
  终结,单选族例外);全仓无 PickBoxCard 构造/发射残留;
- **逻辑态覆盖锁**(R9):词表全动作对照 `flow/action-logic-state.md`
  逐行有逻辑态计算;未建模保守回退分支删除;无标注缺口的动作零
  「无逻辑态发射」残留;
- **零比对出生锁**(裁决3):WearEquip 与工具原子类体内零比对(diff/
  验穿面不存在);CV-diff 验穿删除;
- **原子通路对照锁**:旧组合发射 ↔ 新原子序列逐域映射(部署 = DeployMove
  序;换血 = SellDeployed/SellBench 序;穿戴/工具 = 逐件序);旧 RunTools/
  RunEquip 执行序约束由发射序等价表达(对照记录);
- `EXHAUSTION_WINDOW_ACTIONS` 重推记录在案;
- 回归门①+②(见卷首「验证门口径」)+ `ruff check` 本节点文件零告警。
**验收凭据形式**:扫描报告 + 各专锁测试名 + 原子通路对照记录 + 重推
记录 + L1/回归门记录。

## 3.2b 批2b:词表归一与删除(语义批,账本节点二;裁决2)

**范围**:
1. **词表归一与删除**:四对同名合并(统一类 = 现役族A 类原样,字段/
   顺序/metadata 逐字保留);族B 专有动作迁入 `kernel/cw_vocab.py`;
   基类 `PrepAction` 随迁更名 `CwAction`,`action_key` 函数随迁
   (附 action_key 输出前后对照锁);`SELL_BENCH_REASONS`/
   `SELL_BENCH_ORPHAN_REASONS` 迁居;`RunDeploy`/`RunEquip`/`RunTools`/
   `CompTransaction`(+`FillSpec`)与族B 同名旧类删除;import 一次翻清,
   不留转发 shim。
2. **消费面收口**:`cw_prep_expect.py`(DragExpect 坐标系翻转);
   `cw_exec_state.py`(apply_op_effect 字段消费与换算收口);
   `cw_game_state.py`(CompTransaction 提案分支删;LevelUp 逻辑态
   金腿翻转 = `action.cost` 直写,替换 2a 中间态执行缝金差,中间态
   定义见 §3.2a);换算收口判据
   (物理换算仅存观察写入边与执行坐标边各一处,函数化);遥测跨批判读
   兼容窗(SellBench 载荷 slot→bench_idx 改名 + 值域换算式,读侧双键
   兼容落 telemetry/query.py、journal_query.py 与 tools/cw 判读脚本)。

**设计依据**:design.md §2.6/§2.7。
**文件面**:`kernel/cw_vocab.py`(四对合并/族B 迁入/基类更名/常量迁居)、
`kernel/cw_prep_actions.py`(词表退役)、`prep_actions.py`(消费面参数切换)、
`kernel/cw_prep_expect.py`(DragExpect 坐标系翻转)、`kernel/cw_exec_state.py`
(apply_op_effect 字段消费与换算收口)、
`kernel/cw_game_state.py`(CompTransaction 提案分支删)、
`operations/cw_loop.py`、`operations/cw_screen/cw_screen_prep.py`(消费面
类切换)、`operations/cw_op/cw_comp_transaction_action.py`(删档)、
`operations/cw_op/cw_shop_actions.py`(行删)、
`strategies/impl/mandate_v1/`(mandate/entry/bridge/shop 发射面与截停集)、
`strategies/impl/flow.py`、`strategies/impl/cw_strategy.py`、
`strategies/mandate_v1_strategy.py`、`decision_assembly.py`、
`kernel/cw_strategy_session.py`、`cw_game_ports.py`(import 翻转面,仅
import 行)、`sim/engine_p1.py`、`sim/checks/suspects.py`、
`sim/checks/ledger.py`(CompTransaction 消费删 + SELL_BENCH_* import
翻转)、`sim/pool.py`(注释面)、`telemetry/schema.py`、
`telemetry/query.py`、`telemetry/journal_query.py`、`tools/cw/` 判读脚本
(兼容窗)、`sr-od-test/` 回归与专锁。sim 侧除申报删除/翻转面外零语义。
**依赖**:批2a(原子通路就位;LevelUp 发射面 cost/auth_basis 装载与本
节点类合并同步翻转)。
**优先级建议**:7。
**完成判据**:
- 归一删除面以 2a 扫描报告为底册逐点闭环;
- 全仓无族B 旧类/组合壳/CompTransaction 的构造与 import 残留(一次翻清,
  无 shim;扫描报告逐点闭环);
- 换算收口:物理换算仅存观察写入边与执行坐标边各一处(函数化);发射与
  决策面散点换算零残留;
- **LevelUp 装载锁**(2b 半):发射面 cost = xp_click_cost 现算、失读
  回退 XP_CLICK_COST_FALLBACK;auth_basis 分键装载(类合并同步翻转);
  逻辑态金腿切 `action.cost` 直写(2a 中间态执行缝金差退役);
  posture_unfulfilled 对账新口径总复验;
- **逻辑态覆盖锁复验**(R9):合并后统一词表逐行有逻辑态计算;
- 商店域发射序列对照不变(CompTransaction 行消失除外);
- sim:固定 seed 对局(动作流不含 CompTransaction)动作序列与结果逐项
  不变;sim/checks import 翻转零语义;
- 跨批判读口径落位:判读工具双键兼容窗 + 换算式申报 diff 在案;
- 回归门①+②(见卷首「验证门口径」)+ `ruff check` 本批文件零告警。
**验收凭据形式**:各专锁测试名 + sim seed
锁测试名 + 兼容窗申报 diff + L1/回归门记录。

## 3.3 批3:备战执行器收编(执行器方法 → op 类,零行为)

**范围**:备战动作 op 类逐字迁移(体迁 + executor 薄委托,§2.4;LevelUp/
ClickSpheres 体已批2 定形,本批只迁形;PickBoxCard 已批2 随 R7 删除,
不立 op 类;OpenBoxOp 置 terminal=True,terminal_wait 与批2a 落地
交回等待值等价(`_OVERLAY_ANIM_WAIT_S`,来源写死见 §3.2a);`PrepExecEnv`;执行包络留守;
分派链删除改查注册表;终结判定改读 `terminal` + `terminal_wait` 类属性
(wait 3/1.0 等价锁;决策循环与生命周期孪生环两处对齐);OpenShop 注册行
= terminal 承载行(execute 抛 AssertionError,正常路径不可达;read_only
两形态由动作字段承载,消费在流程层);StartBattle 注册行 = 基类契约在册
例外(判效/重发/停机 as-built 保留,退役挂账指向统一观察架构 A6);
退役成员无注册行(R1:退役=删);比对收口(裁决3):批3 辖 prep 域
现役零留证比对面(CV-diff 已批2 删、工具对拍随批2 原子化由观察承接),
发现比对面即随批3 迁观察侧。
**不含**:词表面(批2 已归一);包络语义改动;`validate` 迁移(留守 runner)。
**设计依据**:design.md §2.4。
**文件面**:`operations/cw_op/cw_action_registry.py`、`cw_action_base.py`、
备战 op 类新文件(`operations/cw_op/` 下,一 op 一文件沿用 T-201 约定)、
`prep_actions.py`(薄委托)、`operations/cw_screen/cw_screen_prep.py`
(结束判定两处 + executor 装配点)、`operations/cw_loop.py` 消费点、
`sr-od-test/` 对应测试。
**依赖**:批2b。
**优先级建议**:6。
**完成判据**:
- 行为对照 design.md §2.4:备战动作发射行为/detail 文案/emitted 语义/
  包络账务零变化;终结集与 terminal 属性逐一等价、terminal_wait 与
  现行 wait 值(3/1.0 与 OpenBox 批2a 落地交回等待值)逐一等价(测试锁);OpenShop 行
  不可达性锁;StartBattle
  例外条款与 A6 挂账指向在册;
- 回归门①+②(见卷首「验证门口径」)+ `ruff check` 本批文件零告警。
**验收凭据形式**:L1 + 备战域测试记录 + terminal/terminal_wait 等价锁
测试名 + OpenShop 不可达锁测试名 + diff 零行为审查。

## 3.4 批4:事件线 pick 收编 + 词表纪律注册完备锁(零行为)

**范围**:pick 词表 op 类注册(overlay act 经工厂,§2.5);词表纪律
注册完备锁——运行时锁:遍历词表元组单一源(统一词表 `CW_ACTION_TYPES`,
随基类迁 `cw_vocab`;pick 族新增运行时元组常量,先例 =
`PREP_ACTION_TYPES` :174),逐类断言注册表解析可命中该类(is-a 兜底
语义同注册表,经注册表类级查询,不构造业务动作实例);退役 = 删类,
元组中不存在即天然不可复活。**禁源码扫描测试**(AGENTS.md
§10.3:不在测试里读取/扫描源码做断言,无例外)。**比对收口迁移**
(裁决3):具名三面迁观察侧——投资环境刷新零效果留证
(`cw_screen_invest_env.py` :316-333)/RefreshShopOp 刷新牌面三值
(`cw_refresh_shop_action.py` :141-143)/刷新期望对账
(`cw_refresh_shop_action.py` :144-171);任务书第一步全仓扫描动作 op 内
比对面补全清单(漏面不合格);迁移时零决策留证语义由观察侧缺陷台账
(`defects.record_defect`)承接;过渡期保留但标注违规待迁。
**不含**:overlay 画面 op 的决策/观察段改动;推进型(用户裁定不入)。
**设计依据**:design.md §2.5。
**文件面**:`operations/cw_op/cw_action_registry.py`、pick op 类新文件、
`kernel/cw_events.py`(pick 运行时元组常量)、各 overlay 画面 op
(`operations/cw_screen/cw_screen_encounter.py` 等 act 段)、
`operations/cw_screen/cw_screen_invest_env.py`(refresh_no_effect 迁观察)、
`operations/cw_op/cw_refresh_shop_action.py`(两比对面迁观察)、
`sr-od-test/` 新锁测试(锁运行时行为,落位与写法遵循
`sr-od-test/CW_TEST_SPEC.md` 域形态)。
**依赖**:批3。
**优先级建议**:4。
**完成判据**:
- 注册完备锁测试在册且绿(词表全类型覆盖:统一词表 `CW_ACTION_TYPES` +
  cw_events pick 族,遍历运行时元组,零源码读取);
- 比对收口迁移完成(裁决3):具名三面 + 扫描补全面迁观察侧,留证语义
  由缺陷台账承接的记录在案;全仓动作 op 内比对面清零(过渡期标注面
  清零);
- 回归门①+②(见卷首「验证门口径」)+ `ruff check` 本批文件零告警。
**验收凭据形式**:锁测试名 + L1 记录。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本;迭代收尾义务兑现。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:批1-批4 全部。
**优先级建议**:0。
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- `flow/action-logic-state.md`:备战域随批2a 落码同步转录(LevelUp 行
  按 design.md 定案④;PickBoxCard/组合动作条目删;工具 7 类与
  WearEquip 落 §4 新原子类形态;转录义务正文见 §3.2a,此处为末阶段
  一致性复核登记)← 批2a
- `flow/screens-actions-capability.md` §2:七动作族执行载体列更新
  (单一工厂 + 域 env);双族坐标系节改「统一词表 + 容器下标规范系 +
  执行边换算」;补词表边界声明(原子动作 + 坐标参数化机械动作入词表,
  组合/挑选逻辑属策略实现)← 批2/批3
- `flow/action_exec.md` §1/§2/§4:词表节(备战动作表 → 统一词表指针;
  退役 = 删纪律;逻辑态计算枚举指针 = `flow/action-logic-state.md`);
  执行载体表述统一(PrepActionExecutor 表述改「备战
  runner 包络」);组合动作节删除,改原子发射通路表述(部署/穿装备/工具
  的决策核逐帧发射形态)← 批2/批3
- `flow/统一观察架构-画面op基类设计.md` §6.1(词表纪律回填:单一词表
  落码 + 词表边界声明 + 锁形改形申报——「AST 扫描」验收按源码扫描测试
  禁令改形为运行时注册完备锁)与 §6.2(点击链载体清单回填 as-built =
  `cw_action_registry.py`)← 批4
- `flow/prep_visit.md`:备战单动作消费段分派形态表述;LevelUp 逐帧单击
  与逻辑态建模;OpenBox 开箱交回(武装箱选择画面 op 分发);刷新终结
  结构语义先例(投资环境刷新,已落码)← 批2/批3
- `flow/shop_visit.md`:CompTransaction 终结邻接 fallback 与整档替换
  表述删(终结集收缩为 RefreshShop/CloseShop)← 批2
- `flow/guards.md`:恒指纹窗白名单口径重推(EXHAUSTION_WINDOW_ACTIONS
  = {OpenShop};DeployMove 为进展性动作不入窗)← 批2
- `flow/screen_op.md` §7 盘点表:新增「货币战争-备战-武装箱选择」行
  (单选族例外、选卡即终结;decide_box_card kernel 单一源);武装箱弹窗
  行「四选一不属本画面」表述同步 ← 批2
- `flow/projection_contract.md`(文件名不改;标识符正名登记见 design.md
  §2.6):悬空符号指针修正(T-201 遗留);备战逻辑态域集扩 xp/level 申报;
  逻辑态正名表述同步 ← 末阶段顺手
