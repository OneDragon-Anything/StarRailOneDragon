# T-10 骇入策划/银狼升星 修法设计(planner)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:已实施(落地批 commit 54af975df,验收 = 本报告;cw_overlay_pick_env.py 与巨星两文件的在飞 hunk 由并行批 dbffcb326 携带入库。前史:对抗收敛待用户裁决+新规范增补待裁决(对抗轨迹:r1 未收敛 7 条 → 修订 → r2 未收敛 3 条 → 修订 → r3 未收敛 1 条 → 修订 → r4 收敛 0 条;新规范增补 = §3,依据 2026-09-22 两条款符合性重审;增补节对抗:respec-attack-AB 判未收敛 11 条(中 2 低 9)→ 按 11 条定点修订 §3→复攻(respec-attack-AB-r2)残留 3 条一行级→二轮修订→编排侧机械验证收口(2026-09-22,T-37 晨报 G4);二轮规范增补 = §4——用户裁定 2026-09-22 两条款,均已入正本(op-layer.md §1.1 :35「选择坐标观察上报」/ §1.2 :48「每个动作 op 单独一个文件」),稿内按正本注册名集成;r5 攻击未收敛(中 3 低 4)→ 修订;r6 复攻未收敛(新 中 1 低 3,并行批装备退役 d37d78fab 与 :35 插入移位)→ 修订;r7 复攻未收敛(新 中 1 低 2,并行批坐标 canonical 化 97c81cdf3/02057f6c8 + :36 残留清尾)→ 修订;r8 末轮未收敛仅余 低 2 一行级稿件文本缺陷(落盘文本裸节号自指 + 替换范围终点假 as-built)——两处已按 r8 处方清偿(未经再攻,裁决注意),4 轮上限触顶;终审修订(2026-09-22 用户裁决):F-1 按辖域澄清改形 + 新增 F-1b 行为项(确认钮查找全族统一 round_by_find_and_click_area,免对抗入稿)+ T-9 撤销余波收回(§2.2(4)/§3.3 落点 2 升格自持);另含 §2.3/§2.4/§2.5 现值核验修订:先行实施批已清出面结案)
- 输入:审查报告 = `.debug/progress/2026-09-22-cw-screen-review/reports/T-10-r1.md`(发现 F-1..F-5;总判定 = 有问题,高 0 中 2 低 3)。涉事代码与文档以仓库现状为真值逐处核读;定位一律符号锚 / 文档节号(行号仅作本稿定位辅助,并行批可能位移,实施按「文件 + 定位描述」落点)。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根)。
- 修法性质:F-1..F-5 主体 = 文档语义更新与注释清理,零行为;**唯一行为项 = F-1b 确认钮查找机制全族统一**(用户裁定 2026-09-22,§2.1b:各屏确认钮改 `round_by_find_and_click_area`、`env.confirm` 字段与决策半组装点退役、兜底常量与伙伴 OCR 找钮退役、area 缺失失败语义改显式 round_fail)。
- 修法覆盖面 = 代码注释三文件(`operations/cw_screen/cw_screen_yinlang.py` 全文件、`operations/cw_op/cw_overlay_pick_action.py` 仅 `OverlayPickExecEnv` 类与 `CwActionPickPlannerOp` 域、`kernel/cw_action_report/pick_planner.py` 全文件)+ 正本文档四面(`flow/action_ops.md` §4.5 头句与段首、`flow/action_exec.md` §2 事件线 pick 族段、`game_state/fields.md` §3.2.18 与 §4 骇入策划写端臂、`screens/planner.md` §3 与开放设计注)+ `game_state/logic-updates/pick-planner.md`(§1、§2/§3 与 §4 连带)。

## 1. 问题与动机

### 1.1 F-1(中→含行为项 F-1b)机械参数契约句辖域未声明 + 确认钮查找机制全族统一(用户裁定 2026-09-22)

- 现状症状:契约句「机械参数由各画面 op 决策半现算经 env 传入,op 类体内零决策」未声明「机械参数」辖域,且多处同断言文本以列举措辞扩大读者预期——`flow/action_ops.md` §4.5 标题行、`flow/action_exec.md` §2 事件线 pick 族段末句(「机械参数(定位点/确认钮/裁决词)由画面 op 决策半现算经 `OverlayPickExecEnv` 传入(op 类体内零决策)」)、`cw_overlay_pick_action.py` 模块头(「机械参数(定位点/选定快照/未选中实证/确认钮定位)由各画面 op 决策半现算后经 env 显式传入」)、同文件 `OverlayPickExecEnv` 类 docstring(「域字段 = 决策半产物(机械参数,构造时显式传入,op 类体内不自算)」/「``confirm`` = 确认钮中心(决策半从 screen_info 现取;None = 点卡即选族无确认步)」)——「定位点/确认钮」列举使确认钮定位看似在辖域内,初审即如此误读。用户澄清(2026-09-22,裁决):「机械参数…经 env 传入」不包括点确认——确认都是动作 op 里,由瞄准查找处理(各屏机制:补给/祈愿 = `round_by_find_and_click_area`,遭遇/巨星/策划/卜者 = `area_center`(+兜底常量),伙伴 = OCR 找钮,投资两屏 = 现役变体经 `env.confirm` 传入)。经 env 的机械参数实为选卡定位(`env.target`,例外两行)+ 域载荷。逐行现值对照见 §2.1 表。用户第二道裁定(2026-09-22):确认钮查找机制**全族统一 = `round_by_find_and_click_area`**(项目 AGENTS §3 找元素点按钮第一原则;area 找不到 = 显式 round_fail,禁兜底坐标静默点击——BuyCard 行同款先例),一并入本批(F-1b 行为项)。
- 根因归层:约定层——契约句辖域未声明(列举措辞扩大读者预期);行为面在册合规(action_ops.md §1 增补 3「瞄准」= 动作 op 唯一允许的元素查找;确认钮 = 静态控件锚,op-layer.md §1.1 :35 辖域判据明文不入坐标观察上报;area 缺失回退兜底常量 = 族在册派生模式)。不符面 = 契约文字辖域,非参数流设计。
- 解决到哪:两层——①契约句改写为带辖域声明的口径(落点清单 = §2.1 (1)–(5)):两正本(`flow/action_ops.md` §4.5 标题行与段首、`flow/action_exec.md` §2 句)+ `cw_overlay_pick_action.py` 模块头 + `OverlayPickExecEnv` 类 docstring;②**F-1b 行为项:确认钮查找机制全族统一 `round_by_find_and_click_area`**(遭遇/巨星/策划/卜者的 `area_center`(+兜底常量)、伙伴 OCR 找钮、投资两屏 `env.confirm` 变体全部退役;补给/祈愿现役已是、无确认步三行不动;兜底常量随批退役 = T-37 家族待裁项 #1 由本批清偿;伙伴/投资两屏确认钮 area 建档核查为实施批首步)——行为变化申报与不变量见 §2.1b。明确不解决:①选卡定位机制(env.target 及两例外原地,坐标收敛归 :35/增补 5 族级欠账线);②`OverlayPickExecEnv.idx` 字段注释的钳位措辞(归 T-37 在册的 pick 族守卫家族批裁决面,原 T-9 §2.2 登记、该稿已撤销);③§4.5 各行「说明」列(逐行已按行如实;巨星行归 T-8 稿 F-2 辖域)。

### 1.2 F-2(中)fields.md 策划域两行未随 2026-09-21 两批同步

- 现状症状:`game_state/fields.md` 两处与代码真值相反/失真——①§3.2.18「随机/待证面」名单仍把**欢愉契约**归「不建逻辑写,观察收口」组,而现役条件腿 = `kernel/cw_action_report/pick_planner.py::_grant_joy_conditional`(`gain_character(1★, rand=True)` 走获得链采样直写落位/回调/合成,校准面 = `logic_rand_outcome` 行);正式模型正本 `game_state/gain-chain.md` §3 与 §6、采样口径正本 fields.md §2.5 均已申报,字段级行未随;②§4「事件选择」段对骇入策划面已失真——段首总括「默认不记预期值……后果走观察覆盖+缺陷台账」与现役相反(现役 = 即时单相记预期值:equip 腿入栏+后果链、升费腿变换+档行),段内「余屏(命运卜者/装备三选一/骇入策划)写端未接线=先补档」同句滞后(策划/装备现役有写端;「chosen_hack 写端未接线」部分仍真,与 planner.md 开放设计注一致)。该段经 T-5 实施、装备退役批(d37d78fab)与坐标伴随域批(02057f6c8)多轮落地(现值 = 标题 8 屏 :1110/余屏句两件套 + 装备退役注 :1117-1118/补给臂 :1122;fields.md 行号随并行批持续位移,以内容锚为准),本发现残余面 = 总括句与余屏句的策划子句。
- 根因归层:语义层 + 约定层——字段级正本行停留在上一代「观察收口/不记预期值」模型;`2026-09-21-joy-conditional-leg` 与 `2026-09-21-pick-planner-equip-immediate-report` 两批的正本更新清单均未辖 fields.md(申报面随批同步缺口)。
- 解决到哪:§3.2.18 欢愉契约行本稿自持改写(全仓无他稿涉足,核验:T-5 稿 §2.3 = §3.2.15/§3.2.5/§4 补给臂,T-9 稿 §2.3 = §4 余屏句/§3.4.5/§3.2.15〔该稿已随装备屏撤销删除〕,均不含 §3.2.18);§4 事件选择段升格本稿自持(见 §2.2;T-9 稿已撤销,原认领悬空,用户裁决 2026-09-22 收回本稿)。明确不解决:①§3.2.5 备战席「写端(完整清单)」不单点补条件腿行(审查未列;其效果写端已有「发牌进席族……按归属判据逐卡分面,§3.2.18/§5.3」收全指针,修后新分面即被其覆盖,无缺员);②量子同频契约等其余「随机/待证面」名单行(现值无写端,不动);③§3.4.5(选择装备域,随装备屏退役归退役批);④命运卜者写端接线本体(归 T-12 稿)。

### 1.3 F-3(低)注释引用含 W/rN 类编号与死指针

- 现状症状:`cw_screen_yinlang.py`(模块头「r103」「局29 P2r6」、类常量注「match3 实锤……见 REPORT W944 §8」「W952 审计 P1-1/P2-1 返修」、`_card_point` docstring「W952 返修」)与 `cw_overlay_pick_action.py::CwActionPickPlannerOp`(类 docstring 与 run 注「r326/P1⑦」「r327 终审 E」「局29」)——命中 AGENTS.md §8「注释里禁出现会话局部标识符(W 轮次号/rN/批N/[N] 之类只在当次会话有意义的编号);出处要么写成持久索引,要么写成纯语义描述」。其中「REPORT W944 §8」全进度树仅 archived ADR 内一处转引 = 死指针,读者无法重建出处;各处技术结论均有语义句或持久锚承载,仅出处指针形态违规。
- 根因归层:约定层——注释纪律为后立规范,存量注释未回溯清理;「W944」类出处本就没有持久锚(Dead reference)。
- 解决到哪:策划域两文件命中点按统一准则清零(准则 = 本迭代 T-3 稿 `battle_wait.md` §2.6 五条清理准则,引用不重复定义;两文件做同深度扫描——全文件/类体全扫描,逐处清单与目标文本见 §2.3;与 T-6 稿对同四点位的并行主张按 §2.3 交叉稿声明归口 T-37)。明确不解决:①`cw_overlay_pick_action.py` 非策划域的同型命中(如巨星「W265」、伙伴「r6 stall」——归各屏审查稿/全仓注释卫生批,T-3 §2.6 与 T-6 稿均有同款联动登记);②全仓注释卫生(T-3 §2.6 已建议另立批);③live-verified 头的日期(审查 §3.9 在册「存量 live-verified 头为项目既有风格」合规面,保留)。

### 1.4 F-4(低)代码注释与正本篇引用 changes/ 迭代名

- 现状症状:策划域注释与正本引用可检索到 `changes/<迭代名>/` 的具名迭代与 design §N 指针,拉丁与中文两形态并存——`cw_screen_yinlang.py`(模块头「迭代 2026-09-18-screen-op-flat-report」「迭代 2026-09-21-pick-planner-equip-immediate-report design §2.0/§2.1」、act docstring 同引、「银狼闭环 design §2.1①」、observe 注「设计 §2.4」、act 防御注「终态契约 §2.2」)、`kernel/cw_action_report/pick_planner.py`(模块头同引、三处「design §N」、两处「设计 §2.2」、一处裸「§2.1」)、`screens/planner.md`(§3 与开放设计注两处「银狼升星记账批 §2.4」);命中 AGENTS.md §9 铁律「changes/ 会不定期、无理由删减——代码与正本文档禁引其内容(长期引用),正本必须自足」。各处被引实质均已在正本条款或注释内自足(同句并引 action_ops.md §1 增补 2 等),断链不丢语义,故低。
- 根因归层:约定层——迭代落地时注释与正本里的过程件指针未按铁律收敛。
- 解决到哪:策划域自持命中点收敛为正本指针或纯语义(判据引用 T-5 稿 §2.7 并扩中文形态与裸节号,逐处清单与目标文本见 §2.4);`cw_overlay_pick_action.py` 内四处命中(env docstring「银狼闭环 design §2.1①」、模块头裸「design.md §1.1/§1.2」、`CwActionPickPlannerOp` docstring 与 run 注的同款)在 T-5 §2.7 清单(#10/#11/#15/#16)与 T-6 §2.5 收回处置两边均有并行主张,落点归 T-37 裁决(见 §2.4 让渡面)。明确不解决:同族面在全仓的扩散(fields.md §3.2.23 自身的 changes/ 引用、`cw_vocab.py` 多处「银狼闭环 design」等)——T-5 §2.7 已建议全仓「changes/ 引用清理批」,本稿只清策划域自持命中点。

### 1.5 F-5(低)专篇死符号指针:`CwScreenYinLang._handle_overlay` 已不存在

- 现状症状:`game_state/logic-updates/pick-planner.md` §1「op 载体 = `CwActionPickPlannerOp`(体迁自 `cw_screen_yinlang.py::CwScreenYinLang._handle_overlay` 点卡确认尾段,**替身缝 = 方法级桩保留**;域 env = `OverlayPickExecEnv`)」;同款措辞见 `cw_screen_yinlang.py` act 注(「方法级替身缝保留」)。`_handle_overlay` 全 src grep 零命中(两 node 改写后该方法已不存在),按符号锚定位落空;「方法级桩」与现状失配——现文件无任何桩方法,在册的缝 = 注册表工厂派发调用点(测试经 monkeypatch `action_op_for` 承接)。
- 根因归层:表示层——符号锚指向已删除符号,定位落空;缝形态描述随两 node 改写漂移。
- 解决到哪:两处改现役缝锚(目标文本见 §2.5),连带同专篇 §4 首句的反口径残留(「选择后果不记预期值」与同篇 §2 即时单相申报直接相反;该文件已在触碰面内,已知矛盾不登记 = 放行)。明确不解决:测试文件零改动(monkeypatch 即在册承接形态,非欠账);「统一动作工厂批4」泛化批名——除 §2.5 #2 病段随缝锚改写一并清出外,其余实例(如 `OverlayPickExecEnv` docstring「统一动作工厂批4 起;……」)按 T-5 §2.7 判据保留面不动;`_overlay_confirm.py` 模块头(T-4 稿残留修法 2 辖域)。

### 1.6 已核对一致面

审查报告 §3 九项(即时单相三方一致 / `lv999_cost_tier` 写语义 / 派发即终结 / 决策控制分层 / 画面 op 零容器写 / 观察上报规约 / 动作 op 行为面 / planner.md 九节 as-built / 注释规范合规面)全部不立修法,本稿不触碰其承载面。正面结论特别记录:**本屏无盲选回退(决策出口合规)**——策略返回 None/非法类型/idx 越界时 `_card_point` 处 `CARD_AREAS[idx]` 直接 AttributeError/IndexError/TypeError 响亮暴露,遭遇屏 T-4-r1 F-1 型「决策非法 → 盲选回退」结构本屏不存在,op-layer.md §1.3「非法返回 = 策略器 bug 响亮暴露」合规;T-37 在册的 pick 族守卫族级建议(原 T-9 §2.2 提出,该稿已撤销)对本屏无施工面。

## 2. 方案

修法全部为文档与注释面的语义改写,零行为变更;以下逐发现给目标文本,实现者照抄即可,无需再设计。

### 2.1 F-1 修法:参数流契约改「双源分工」现役口径(同断言各面一次成文,落点 (1)–(5))

as-built 逐行对照(依据 = 各 run 体与全部发射位 env 组装现值,符号锚就地):

| 行 | 选中定位源(现值) | 确认钮源(现值) |
|---|---|---|
| PickEncounter | 体内 `area_center`(遭遇卡-其一/其二)or 兜底常量(env 组装 = op-only) | 体内 `area_center`(按钮-选择) |
| PickSupply | `env.target` | 体内 `round_by_find_and_click_area`(按钮-确认) |
| PickMegastar | `env.target`(`need_select` 开关经 env) | 体内 `area_center`(按钮-确认选择)or 兜底常量 |
| PickPartner | `env.op._pick_point`(宿主画面 op 属性;env 无 target) | 体内 OCR 找「确认选择」 |
| PickPlanner | `env.target` | 体内 `area_center`(按钮-骇入确认)or 兜底常量 |
| PickInvestStrategy / PickInvestEnv | `env.idx` / `env.target` | `env.confirm`(消费)+ `env.entry_keyword`(消费) |
| PickFortune | `env.target` | 体内 `area_center`(按钮-确认选择)or 兜底常量(`entry_keyword` 经 env 组装而 run 体消费体内同词字面量——组装值现役未消费) |
| PickWishTrial | `env.target` | 体内 `round_by_find_and_click_area`(按钮-确认选择) |
| PickBoxCard / PickStarTome / PickExpertInvite | `env.target` | 无确认步(点卡即选) |

现值核验(2026-09-22,装备退役批 d37d78fab 后):PickEquip 全套退役(`flow/action_ops.md` §4.5 :138 留名行),本表不列;族活跃行 = 12,无确认步 = 三行。

**单一表述(下称「机械参数辖域段」;各面中 (2) 为申报单一源,(3)(4)(5) 与其同文或显式指认 (2),禁另起第三种口径)**:

```
机械参数辖域段(as-built;申报单一源):
- 辖域 = 选卡定位 + 域载荷,经 env 传入;确认钮不属机械参数 env 传入范围
  ——确认查找与点击 = 动作 op 执行体 `round_by_find_and_click_area`(全族
  统一,用户裁定 2026-09-22;§1 增补 3「瞄准」在册唯一允许查找;area 缺失
  = 显式 round_fail,禁兜底坐标静默点击);投资两屏 `env.confirm` 变体随
  本批退役;
- 选卡定位 = `env.target`(决策半现算;例外两行:PickEncounter = op 体内
  `area_center` 候选卡 or 兜底常量、PickPartner = 宿主属性经 `env.op`);
  选卡定位坐标欠账 = 标题行尾段(§1 增补 5,观察上报收敛),此处不重复;
- 域载荷逐行 = `idx`(10 行 = 全族除 PickEncounter/PickPlanner)/
  `need_select`(巨星)/`leg_type`+`norm_item`(策划)/`unselected`(伙伴)/
  `match`+`picked`(补给)/`confirm`+`entry_keyword`(投资两屏;卜者另组装
  `entry_keyword` 而 run 体消费体内同词字面量,组装值现役未消费);
  PickEncounter 组装 = 零域字段。
「op 类体内零决策」= 零选择/零腿型判定(全在决策半),瞄准定位查找非决策。
逐行落点 = 各行动作列/对照表。
```

**(1) `flow/action_ops.md` §4.5 标题行**整行替换:

```
### 4.5 事件线 pick 族(12 行;域 env = `OverlayPickExecEnv`;机械参数辖域见段首申报,op 类体内零决策)。**坐标源欠账(§1 增补 5,用户裁定 2026-09-22)**:全族现役点击坐标 = 决策半现算经 `env.target`,逐屏收敛到「观察上报入容器坐标伴随域(§3.4.5a)、动作 op 按 idx 自取」;收敛完成前 `env.target` 为合法过渡形态,禁新增第二坐标源(欠账登记先例 = StartBattle 行增补 3)。
```

计数现值 = 12 行(装备退役批 d37d78fab 已把标题计数收敛到现值;T-1 稿原认领的「12→13」计数修正随 PickEquip 退役失去前提,归 T-37 重导,非本稿辖域);本稿对标题行只改机械参数分句,计数保持现值。**尾段保留义务**:坐标源欠账尾段 = 并行批 02057f6c8 已落的族级登记(§1 增补 5),整行替换时逐字保留、禁静默删除——本稿机械参数分句与该尾段同行共存;实施批落笔前对尾段做最后一次正本现值逐字重核(修订-落笔窗并行批已四次显影,r8 对账项)。

**(2) 同节段首**(标题行之后、现「**上报形态 = 全族即时上报**……」段之前)插入上「机械参数辖域段」全文(此处理 = 本事实申报单一源),并附 §2.1 对照表为段首附表(逐行 as-built 基准,与各行动作列互查)。

**(3) `flow/action_exec.md` §2 事件线 pick 族段末句**替换(现「机械参数(定位点/确认钮/裁决词)由画面 op 决策半现算经 `OverlayPickExecEnv` 传入(op 类体内零决策)。」):

```
机械参数(辖域申报单一源 = [action_ops.md](action_ops.md) §4.5 段首;确认钮
不属机械参数,由动作 op 执行体瞄准处理,增补 3 在册例外):选卡定位 =
`env.target`(例外:PickEncounter = op 体内 `area_center`、PickPartner =
`env.op._pick_point`);域载荷逐行见段首。op 类体内零决策(决策 = 选中哪个
与腿型载荷,瞄准定位查找非决策)。
```

**(4) `operations/cw_op/cw_overlay_pick_action.py` 模块头「域 env」段的机械参数句**替换(替换范围 = 「域 env = ……」起至「……op 类体内零决策零读决策输入。」句尾(现文句尾;「瞄准定位查找非决策」为替换后文本非现文,不作定界依据);同段后续「轮次结果(确认链末步 ``round_*`` 产物)经 ``round_result`` 旁路字段回传……」句与「族先例 = cw_tool_use_action。」句**不在替换面,保留不动**——防整段替换误删旁路回传契约句):

```
域 env = :class:`OverlayPickExecEnv`(结构化包,构造时传入);机械参数辖域
(申报单一源 = flow/action_ops.md §4.5 段首)= 选卡定位 + 域载荷经 env 传入;
确认钮不属机械参数,由本 op 执行体瞄准查找(action_ops.md §1 增补 3 在册
例外)。op 类体内零决策零读决策输入(决策 = 选中哪个与腿型载荷,瞄准定位
查找非决策)。
```

**(5) 同文件 `OverlayPickExecEnv` 类 docstring 两处 + confirm 字段注释(三处同断言,一次成文)**:

- 域字段总起句(现「公共字段 ``op``/``match``/``config`` + 域字段 = 决策半产物(机械参数,构造时显式传入,**op 类体内不自算**):``idx`` = ……」)→ 冒号前改:

```
公共字段 ``op``/``match``/``config`` + 域字段 = 机械参数(选卡定位/域载荷 =
决策半产物,构造时显式传入;确认钮 = 本 op 执行体 `round_by_find_and_click_area`
查找点击,不入 env——机械参数辖域申报单一源 = `flow/action_ops.md`
§4.5 段首,本模块头同文转抄):
```

(冒号后 ``idx``/``target``/``picked``/``unselected`` 逐字段描述不动;``idx`` 的钳位措辞归 T-37 在册面(原 T-9 §2.2 登记,该稿已随装备屏撤销删除),本稿不碰。)

- confirm 句与字段注释 = **随 F-1b 退役规格**(docstring confirm 句与字段注现文见下引,整句/整行删除,``confirm`` 字段本体随 F-1b 删除):

```
``confirm`` 字段退役(确认钮查找 = 本 op ``round_by_find_and_click_area``,
见机械参数辖域段;决策半组装点与消费点同批删除)
```

依据:代码现值 = §2.1 对照表逐行 + 发射位 env 组装 grep `OverlayPickExecEnv(` 全集(encounter op-only / partner idx+unselected / supply match+idx+target+picked / 卜者 entry_keyword 组装未消费,其余如对照表);规范 = action_ops.md §1 增补 3(瞄准 = 唯一允许查找)、辖域澄清(用户裁决 2026-09-22:确认钮不属机械参数 env 传入,投资两屏 env.confirm = 现役变体不立欠账)、「坐标单一真相源 = screen_info」(AGENTS §5);docstring/字段注/模块头/两正本同断言一事实,一次成文防同 dataclass 内新互斥(T-9 F-3 连带修正同款先例)。

**验证门(F-1)**:①`cw_overlay_pick_action.py` 内 grep `由各画面 op 决策半现算(后)?经` 零命中;②`OverlayPickExecEnv` 类 docstring 与 confirm 字段注释 grep `体内不自算|决策半从 screen_info 现取|决策半现取` 零命中;③action_ops.md §4.5 段首辖域段与段首附表互查一致(例外两行/域载荷逐行/卜者组装未消费三面逐项对得上);④**确认钮统一门(F-1b)**:该文件 grep `env\.confirm` 零命中(字段退役)、grep `area_center\([^)]*'按钮-` 零命中(确认钮 area_center 消费点全退;选卡定位 area_center 不在限)、伙伴确认 OCR 查找零命中。

**F-1b 行为项:确认钮查找机制全族统一(用户裁定 2026-09-22,免对抗入稿)**:
- 改动:遭遇/巨星/策划/卜者确认钮 `area_center`(+兜底常量)→ `round_by_find_and_click_area`;伙伴 OCR 找钮 → 同;投资两屏 `env.confirm`(决策半现算经 env)→ 同;补给/祈愿现役已是,不动;无确认步三行不动。
- 连带退役:`OverlayPickExecEnv.confirm` 字段 + 决策半组装点与动作 op 消费点;各屏确认钮兜底常量(CONFIRM 等,T-2 稿「家族待裁项 #1」由本批清偿);伙伴 OCR 找钮代码。
- 行为变化申报:①失败语义——area 缺失从「兜底常量静默点击」变「round_fail 显式失败交框架轮次」(同 BuyCard 行先例「禁兜底坐标静默点击」);②点击坐标来源从「area_center 中心 or 兜底」变「`round_by_find_and_click_area` 查找点击」(同一建档 area 中心,正常路径坐标一致);③`OverlayPickExecEnv` 数据类形状变化(confirm 字段删除)。
- 不变量:确认点击后固定等待 + 即时上报时序不变(各屏确认链现役时序保留);`round_by_find_and_click_area` 不带 until(动作 op 禁验证,§1 增补 2/3);确认未生效仍由外循环重识别重派。
- 前置核查(实施批首步):伙伴/投资两屏确认钮 area 是否在册,缺则先建档(od-dev-screen-onboarding 流程)再落机制。
- 测试:L1 全绿 + 确认链受影响测试点名;模拟确认链机械断言随 op 改动同步。

### 2.2 F-2 修法:fields.md §3.2.18 自持改写 + §4 事件选择行跨稿并入

**(1) §3.2.18「随机/待证面」名单摘除欢愉契约**——现「……劳务派遣合同、量子同频契约、欢愉契约;愚者恶作剧已移出本族(……)」→「……劳务派遣合同、量子同频契约;愚者恶作剧已移出本族(……)」。

**(2) 同段「随机/待证面」bullet 之后、「随机面到席与星级后果全部等观察覆盖收口」句之前插入新 bullet**:

```
- **采样口径在册的随机发牌 = 随机态直写(§2.5)**:欢愉契约——条件腿正式
  模型 = 银狼策划选择上报的条件腿 rider(`kernel/cw_action_report/
  pick_planner.py::_grant_joy_conditional`;触发 = 头号玩家选项弹窗被处理 +
  欢愉契约在册,候选集 = `cw_investments.ENV_GIFTS['欢愉契约'].
  chars_conditional` 均匀采样一枚,`gain_character(1★, rand=True)` 走获得链
  固定时序落位/回调/合成,校准面 = `logic_rand_outcome` 行,均匀分布未实测
  候校准;授予失败不阻塞腿型分派 = 调用点级 best-effort 例外)。链式规范
  正本 = [gain-chain.md](gain-chain.md) §3。
```

**(3) 同段收束句改写**——现「随机面到席与星级后果全部等观察覆盖收口。」→「未接采样口径的随机面到席与星级后果全部等观察覆盖收口(采样口径在册者 = 上行随机态直写,§2.5)。」

依据:代码 = `_grant_joy_conditional` 函数体(`normalize_invest_name` 门 + 候选集采样 + `gain_character(rand=True, evidence='joy_conditional:<单位名>')`);正式模型正本 = gain-chain.md §3(条件腿不在 `on_env_gained` 枚举、正式模型申报)与 §6(调用点级 best-effort 唯一容器写例外);采样口径正本 = fields.md §2.5(「采样口径在册的动作走随机态直写……未接采样口径的随机效果仍按域级跳写留观察」——收束句改写即此分工句的发牌族落位);分面结构依据 = §3.2.18 既有「按归属判据逐卡分面」框架,新增分面 = §2.5 采样口径在该框架的正交补位。

**(4) §4「事件选择」段——骇入策划写端臂升格本稿自持(T-9 稿已随装备屏撤销删除,原「归 T-9 落笔」认领悬空;用户裁决 2026-09-22 收回本稿辖域)**:

- 现值核对:fields.md §4 现文 = 标题 8 屏(:1110)/「余屏(命运卜者/骇入策划)写端未接线=先补档」+ 装备退役注(:1117-1118)/补给臂(:1122);「默认不记预期值」总括对策划面失真同前(§1.2 ②)。
- 落笔规格 = 余屏句整句替换(「…祈愿试炼);」起至「写端未接线=先补档。」句尾;其后装备退役注「(原装备三选一…)」原样保留):

```
chosen_* 写端已接七屏(盛会之星/伙伴/星徽秘典/遭遇/补给/专家邀请函/
祈愿试炼);余屏(命运卜者)写端未接线=先补档。**骇入策划写端 = 即时单相
一口写**(动作侧,与遭遇臂/补给臂申报粒度对齐;写端 =
`kernel/cw_action_report/pick_planner.py::report_action_pick_planner_param`:
条件腿 rider 先行(欢愉契约在册 = `gain_character(1★, rand=True)` 采样直写,
§3.2.18 / gain-chain.md §3)→ equip 腿 = 入栏 + 获得后果链(§3.2.15)/
升费腿 = 变换 + `lv999_cost_tier` 档行(§3.2.23)/ unknown = 留证零记账 /
unrouted = 终态兜底零写;件名归一现役在决策半与动作上报层 =
op-layer.md §1.1 :34 欠账,收敛终态 = 观察侧转换、动作上报只携 idx,
逐批收敛禁新增)。
```

- 实施时一次成文(本稿自持,无跨稿对账面)。
- 依据:代码写序 = `pick_planner.py::report_action_pick_planner_param`(条件腿 rider 先行 → 三腿分派,模块头申报);unknown/unrouted 分态依据 = `pick_planner.py`(unknown = `_emit_defect(kind='planner_leg_unknown')` 留证 + 零记账;unrouted = `return LogicOutcome(reason='unrouted_leg_zero_write')` 终态兜底零写、无留证行;模块头自申报两态分明),句式照正本 screens/planner.md §4/§6,「选择效果 = 动作侧即时单相写」口径与遭遇臂/补给臂粒度对齐;「默认不记预期值」总括的策划面例外由本臂句式承载。

### 2.3 F-3 修法:W/rN 类编号清理(策划域两文件)

准则 = T-3 稿 `changes/2026-09-22-screen-review/battle_wait.md` §2.6 五条清理准则(禁形一会话局部标识符 / 禁形二变更史叙述 / 改写方向「结论→出处→边界」+ 实证改纯语义 / 保留豁免 / 跨修法交叠一次成文),本稿引用不重复定义;命中即改写,清编号必需的邻近史述随同句一次清出(准则 2/3),不做全文件史述普查(归全仓注释卫生批)。两文件扫描深度同款:全文件(yinlang)/类体全扫描(pick op),不混用「点名-only」。

**cw_screen_yinlang.py(10 处,含审查点名 5 处 + 同型扩展 5 处;扩展依据 = T-3 §2.6「准则做全文件扫描」同款)**:

| # | 定位 | 现文(病段) | 目标文本 |
|---|---|---|---|
| 1 | 文件头注(点名「局29 P2r6」) | 「live-verified 2026-08-20:局29 P2r6 银狼策划事件 41min 卡死后建;坐标来自当场实测(左卡中心 (755,400) 命中选中)。机制见……」 | 「live-verified 2026-08-20:坐标来自实机对局当场实测(左卡中心 (755,400) 命中选中)。机制见 docs/game/gameplay/currency_war.md「银狼我来当策划事件」节(用户口述)。」(清局号轮次号与「41min 卡死后建」建档缘由叙事;日期 = live-verified 头既有风格保留) |
| 2 | 模块 docstring 首句(点名「r103」) | 「……overlay 处理 op(r103)。」 | 「……overlay 处理 op。」 |
| 3 | 类常量注(点名「REPORT W944 §8」) | 「布局漂移修正(match3 实锤 2026-08-31,见 REPORT W944 §8):卡上移后固定点 (1225,480) 落卡外 → 未选中 → 确认无效死循环。改由 area rect 推导:……」 | 「布局漂移实证:卡上移后固定点 (1225,480) 落卡外 → 未选中 → 确认无效死循环;防线 = 由 area rect 推导:71% 高度(旧实证点击高度比例)+ 详情钮避让 clamp;rect 单一源在 cw_yinlang_star_up.yml。」(「REPORT W944 §8」死指针删除;「match3 实锤 2026-08-31」对局俗称+日期归 git) |
| 4 | CLICK_PRESS_TIME 注(同型) | 「(match2 复盘实证 prep_actions 参数;漏定义=live AttributeError,match3 首局实锤——……)」 | 「(值沿 prep_actions 同族参数实证;漏定义 = live AttributeError——类属性与引用点同批落码的纪律)」 |
| 5 | SELECT_Y_RATIO 注(同型) | 「(⚠️ 迁移样本 n=1,08-20 局29 单次交互实证;半区经验值非充分统计)」 | 「(⚠️ 迁移样本 n=1,单次交互实证;半区经验值非充分统计)」 |
| 6 | DETAIL_MARGIN_RATIO 注(点名「W952 审计 P1-1/P2-1」) | 「详情钮避让 = **rect 底缘上移固定比例**(W952 审计 P1-1/P2-1 返修):实帧详情钮带贴卡底……」 | 「详情钮避让 = **rect 底缘上移固定比例**:实帧详情钮带贴卡底(高 20-28px ≈ 卡高 8-10%,含余量取 11%)。……」(删括注;单帧耦合边界、相对几何「只更 yml」承诺逐句保留) |
| 7 | `_LEGACY_CARD_RECTS` 注(同型) | 「旧实证 rect(match3 布局实测前为单一源;area 缺失时兜底)。」 | 「旧实证 rect(area 缺失时兜底)。」(「布局实测前为单一源」= 变更史) |
| 8 | CONFIRM 注(同型「局29」+勘误叙事) | 「……交互实锤在档:在**右侧偏下** (1440-1542,584-615),非画面中央!旧写 (960,615) 是猜的——局29 事件 1.5h 未消费的另一半原因)」 | 「……交互实锤:按钮在**右侧偏下** (1440-1542,584-615),非画面中央)」(「旧写 (960,615) 是猜的」勘误叙事与局号归因 = 变更史;几何事实保留) |
| 9 | `_card_point` docstring(点名「W952 返修」) | 「(相对几何,W952 返修——绝对 y 常数对多布局不成立,见类属性注释)」 | 「(相对几何——绝对 y 常数对多布局不成立,见类属性注释)」 |
| 10 | act 决策注(同型「W953 批1」) | 「# 策略层决策(W953 批1 接线:唯一入口=策略对象,handler 禁 kernel 直调;……」 | 整格目标文本 = §3.1 增补 A 落点 1(含后半句「kernel 直调局外支 = :37 违规欠账……」显式替换)——以该处为单一文本源,本格不重复承载防双文本;「W953 批1」清出同前 |

**cw_overlay_pick_action.py::CwActionPickPlannerOp(原 4 处;2026-09-22 现值核验:并行已实施批已清出,残余施工面仅 1 处)**:

现值核验(grep `r326|r327|局29|终审|P1⑦` 类域零命中):#11(r327 终审 E)/#12(局29 手动点)/#13(r326/P1⑦)的编号已由并行已实施批清出(T-6 §2.5「只清编号」处置已落;清出后语义与各自目标文本等价,#11 仅缺「全词理由见 run 体注」导航短句,不另落笔);#14 半清出(r327 前缀已清),残余施工面 = 行号锚换持久锚:

| # | 定位 | 现文(2026-09-22 现值) | 目标文本 |
|---|---|---|---|
| 14 | run 注裁决词句 | 「# 裁决词用全词「我来当策划」(入场锚同词,cw_yinlang_star_up.yml:26 live-verified)——短词「策划」在艺术字漏读时可能假通过。」 | 「# 裁决词用全词「我来当策划」(入场锚同词 = 建档「货币战争-银狼升星.标识-我来当策划」,screens/planner.md §1)——短词「策划」在艺术字漏读时可能假通过。」(yml 行号锚换建档 area 名持久锚;依据 = screens/README.md 卷首约定「符号锚 = `文件::符号名`(行号随代码漂移,不作定位依据)」——该句住卷首块引,非 §2) |

**交叉稿声明(与 T-6 稿;2026-09-22 更新:结案)**:T-6 稿(invest_strategy.md)§2.5 曾对本类四点位(:372/:398/:407/:409)登记「编号清出,周边语义不动——语义归 T-10」并挂 T-37 归口(防双规格并存);2026-09-22 现值核验 = 四点位编号已随先行实施批清出(见上核验行),归口裁决失去对象,**结案**;残余语义施工面 = #14 行号锚(归属本稿)。

依据:规范 = AGENTS.md §8 两禁形;准则与改写方向 = T-3 稿 battle_wait.md §2.6(实证类出处改纯语义描述、日期局号俗称归 git、字段定义注释与 ADR 引用保留);「REPORT W944 §8」死指针判定 = 审查 F-3 差距说明(全进度树仅 archived ADR 转引、非定义处)。

**验证门**:`cw_screen_yinlang.py` 全文件 + `CwActionPickPlannerOp` 类体(docstring + 方法注释,与 §2.3 清单同源同广度)grep `[Ww]\d+|局\d+|match\d+|终审|P1⑦` 零命中,并检 `\b[Rr]\d+\b` 零命中(词边界保证 `Rect`/`press_time`/`round_` 类词形不误伤;判不准词形停手回本稿提请,禁自行豁免)。清单与门同源:清单执行完毕门即绿,不存在「清完仍红」的剩余命中面。

### 2.4 F-4 修法:changes/ 长期引用收敛(策划域自持命中点)

判据与方向引用 T-5 稿 §2.7(清除对象 = ①「design §N」「design.md §N」及裸「design.md」;②具名迭代引用(「迭代 <名>」可检索 `changes/<名>/`);保留 = 泛化批名标签与纯日期;方向 = 正本指针优先,指针无承载节或语义自足处用纯语义),并扩两形态:③中文形态过程件指针(「设计 §N」及以中文名指称的具名迭代如「终态契约 §2.2」——均可经 `changes/<名>/` 重建归属,同属过程件指针);④无文档名归属的裸「§N」节号(不可重建)。清单 = 两代码文件 + `screens/planner.md` 全量 grep `design|设计 §|迭代 20|§`(拉丁 + 中文形态;裸节号命中经人工归属复核)现值命中 **15 处**:

**cw_screen_yinlang.py(6 处)**:

| # | 定位 | 现文(摘要) | 收敛方式 |
|---|---|---|---|
| 1 | 模块头 | 「形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段直继承 SrOperation。……」 | 删具名迭代标签:「形态:观察 node + 决策动作 node 两段直继承 SrOperation。……」(语义句自足;T-5 清单 #1 同型同句先例) |
| 2 | 模块头(点名) | 「(迭代 2026-09-21-pick-planner-equip-immediate-report design §2.0/§2.1,action_ops.md §1 增补 2:动作 op 确认点击后立即上报完整效果腿,……)」 | 改正本指针:「(`flow/action_ops.md` §1 增补 2 与 §4.5 PickPlanner 行:动作 op 确认点击后立即上报完整效果腿,零重入裁决、零落地相补写面——确认未生效 = 代码 bug,overlay 残留由外循环按当前画面重识别重派)」 |
| 3 | act docstring(点名) | 「(单相即时上报,迭代 2026-09-21-pick-planner-equip-immediate-report design §2.0/§2.1)——本 op 派发即终结交回外循环重观察,……」 | 改「(单相即时上报,正本 = `flow/action_ops.md` §1 增补 2 与 §4.5 PickPlanner 行)——本 op 派发即终结交回外循环重观察,……」 |
| 4 | act 腿型载荷注 | 「# 腿型载荷(银狼闭环 design §2.1①):判定单源 = kernel classify_planner_leg(装备域优先);……」 | 删「银狼闭环 design §2.1①;」:「# 腿型载荷:判定单源 = kernel classify_planner_leg(装备域优先);随 env 透传给动作 op 上报……」(载荷透传契约正本 = action_ops.md §4.5 PickPlanner 行「leg_type/norm_item 经 env 随派发透传」) |
| 5 | observe 捕获集注(中文形态) | 「……classify 关键词匹配面不变——设计 §2.4)。」 | 删「——设计 §2.4」:「……classify 关键词匹配面不变)。」(与 #14 正本孪生句同批同文清出,防正本/代码半新半旧) |
| 6 | act 防御分支注(中文形态) | 「# kernel 返回值包装动作子类型(终态契约 §2.2:kernel 纯函数零触碰,包装归入口/防御路径)。」 | 删「终态契约 §2.2:」:「# kernel 返回值包装动作子类型(kernel 纯函数零触碰,包装归入口/防御路径)。」(包装语义句自足;「终态契约」= 已归档迭代 `changes/2026-09-16-strategy-terminal-contract/` 的中文名,过程件指针同判清除) |

**pick_planner.py(7 处,含点名模块头)**:

| # | 定位 | 现文(摘要) | 收敛方式 |
|---|---|---|---|
| 7 | 模块头(点名) | 「**即时单相上报**(迭代 2026-09-21-pick-planner-equip-immediate-report design §2.0/§2.1;用户裁定 2026-09-21 = action_ops.md §1 增补 2:……)」 | 改「**即时单相上报**(行为正本 = `flow/action_ops.md` §4.5 PickPlanner 行;用户裁定 2026-09-21 = action_ops.md §1 增补 2:……)」(T-5 清单 #19 同型先例) |
| 8 | `_apply_equip_leg` docstring | 「装备腿(确定性通道,design §2.1②):入栏 + 获得后果链。」 | 删「,design §2.1②」(写序申报 = 同文件模块头,自足) |
| 9 | `_apply_upgrade_transform` docstring | 「升费腿 = 变换窗三态 + 档行(design §2.2/§2.1③):前置硬校验……」 | 删「(design §2.2/§2.1③)」(三态语义本 docstring 逐条自足;字段正本 = fields.md §3.2.23) |
| 10 | 同 docstring 时序论证句 | 「(单相时序等价论证 = design §2.0:确认点击到本调用之间容器零写入,观察态与原落地相时点等值)」 | 删「= design §2.0」(论证本体自足) |
| 11 | 同 docstring 连带腿句(中文形态) | 「「新费档银狼刷进商店」连带腿 = 档行兼任(池桶归属随档迁移),不另造申报行(设计 §2.2)。」 | 删「(设计 §2.2)」:「……不另造申报行。」(档行兼任语义本 docstring 自足;字段正本 = fields.md §3.2.23) |
| 12 | 同函数封顶闸注(中文形态) | 「# 现档封顶闸(设计 §2.2):5 费档 upgrade 腿不期出现,出现即留证零写。」 | 删「设计 §2.2:」:「# 现档封顶闸:5 费档 upgrade 腿不期出现,出现即留证零写。」(闸语义同 docstring 已自足申报) |
| 13 | 变换窗工作副本注(裸节号) | 「# P1 容器原生工作副本:bench = BenchView 槽序、deployed = 行域下标派生表(§2.1);」 | 删「(§2.1)」:「# P1 容器原生工作副本:bench = BenchView 槽序、deployed = 行域下标派生表;」(派生表语义自足;裸节号无文档名归属,不可重建。注:「P1」前缀属 F-3 禁形同族,该文件不在 F-3 门辖,本条只清节号指针、不为编号扩面) |

**screens/planner.md(2 处,均点名「银狼升星记账批 §2.4」)**:

| # | 定位 | 现文 | 收敛方式 |
|---|---|---|---|
| 14 | §3 捕获集句尾 | 「……classify 关键词匹配面不变——银狼升星记账批 §2.4)join 为」 | 删出处标签:「……classify 关键词匹配面不变)join 为」(申报句自身完整承载捕获集变化语义,标签纯出处;与本表 #5 代码孪生句同批) |
| 15 | 开放设计注第三条 | 「观察捕获集变化(旧 y 带 → 卡全域 rect)的实机对拍候实机窗(银狼升星记账批 §2.4 申报)。」 | 「观察捕获集变化(旧 y 带 → 卡全域 rect)的实机对拍候实机窗。」 |

**让渡面(2026-09-22 现值核验:结案)**:`cw_overlay_pick_action.py` 曾有四处命中并行主张——模块头 L3 裸「design.md §1.1/§1.2」(T-5 清单 #10;T-6 §2.5 同点位)、env docstring「银狼闭环 design §2.1①」(T-5 清单 #11;T-6 联动登记「归 T-10」)、`CwActionPickPlannerOp` docstring 具名迭代(T-5 清单 #15;T-6 §2.5 同)、run 注「design §2.0/§2.1」(T-5 清单 #16;T-6 §2.5 同);2026-09-22 现值 grep `design|银狼闭环` 该文件**零命中**——四处已随先行实施批清出,T-5/T-6 并行主张与 T-37 归口裁决均失去对象,**结案**;该文件 F-4 无残余施工面,§2.4 验证门对 `cw_overlay_pick_action.py` 不再适用。**核验零命中面**:`logic-updates/pick-planner.md` grep 拉丁与中文形态现值零命中——审查 F-4 所列该处不复存在,记录在案、不立规格。

依据(指针合法性):派发即终结/即时上报正本 = action_ops.md §1 增补 2 与 §4.5 PickPlanner 行(结构性章节,AGENTS §9 正本自足;T-5 §2.7 指针合法性段同款论证);腿型载荷契约 = §4.5 PickPlanner 行;档行字段正本 = fields.md §3.2.23;中文形态同判依据 = AGENTS §9 禁引对象是「changes/ 内容」本身,与指针书写语言无关。

**验证门**:`cw_screen_yinlang.py` / `pick_planner.py` / `screens/planner.md` 三文件 grep `design §|design\.md|设计 §|迭代 20\d\d-|记账批 §` 零命中;并 grep `§\d` 命中逐条人工归属复核(带文档名的正本指针如「fields.md §3.2.23」「gain-chain.md §3」豁免;无文档名归属的裸节号 = 漏项,补入清单或随正本更新批修正;判不准停手回本稿提请,禁自行豁免)。清单与门同源:清单执行完毕门即绿(`cw_overlay_pick_action.py` 四处已随先行实施批清出、让渡面结案,门对该文件无施工面)。

### 2.5 F-5 修法:死符号指针改现役缝锚(两处)+ 同专篇 §4 连带

| # | 位置 | 现文 | 目标文本 |
|---|---|---|---|
| 1 | `game_state/logic-updates/pick-planner.md` §1 | 「op 载体 = `operations/cw_op/cw_overlay_pick_action.py::CwActionPickPlannerOp`(体迁自 `cw_screen_yinlang.py::CwScreenYinLang._handle_overlay` 点卡确认尾段,**替身缝 = 方法级桩保留**;域 env = `OverlayPickExecEnv`)」 | 「op 载体 = `operations/cw_op/cw_overlay_pick_action.py::CwActionPickPlannerOp`(域 env = `OverlayPickExecEnv`);发射位 = `operations/cw_screen/cw_screen_yinlang.py::CwScreenYinLang.act` 决策动作 node 经注册表工厂 `action_op_for` 派发(替身缝 = 工厂派发调用点,测试经 monkeypatch `action_op_for` 承接,锁 = `test_cw_screen_two_node_family`)」 |
| 2 | `cw_screen_yinlang.py` act 注(点名同款措辞) | 「# 点卡选中 → 确认链经工厂(统一动作工厂批4:体迁 ``cw_overlay_pick_action.CwActionPickPlannerOp``,方法级替身缝保留);」 | 「# 点卡选中 → 确认链经注册表工厂 ``action_op_for`` 派发 ``CwActionPickPlannerOp``(替身缝 = 工厂派发调用点,测试经 monkeypatch ``action_op_for`` 承接);」 |

**(3) 连带 `logic-updates/pick-planner.md` §4 首句**(同文件已在触碰面;审查未列,同型扩展先例 = §2.3 类体扩展;不登记 = F-2 落地后正本链同口径而该句留反口径残留):

- 现文:「策划候选内容 = 随机面归观察;**选择后果不记预期值**。升费腿为确定面(档 +1 与变换窗输入均容器现算)。」(首句与同篇 §2 即时单相申报及第二句直接相反)
- 目标:「策划候选内容 = 随机面归观察;选择存证(chosen_hack)无写端 = 申报不变,选择效果 = §2 即时单相一口写。升费腿为确定面(档 +1 与变换窗输入均容器现算)。」(区分句式照 screens/planner.md 开放设计注第一条「chosen_hack 字段位仍无写端(单相上报写的是腿效果域,非选择存证)」)

依据:`_handle_overlay` 全 src grep 零命中(死符号,审查 F-5 差距说明);`cw_screen_yinlang.py` 现文件无任何桩方法;现役缝 = act 尾 `action_op_for(pick, self.ctx, _env).execute()`(工厂调用点);monkeypatch 承接先例 = `sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(现值两处 :263/:335 `monkeypatch.setattr(_reg, 'action_op_for', …)`;行号随测试文件演进漂移,符号锚为准);「体迁自……」= 变更史叙述(AGENTS §8 / T-3 §2.6 准则 2 同判),随死指针一并清出;§4 连带依据 = 同篇 §2 写序申报 + §2.2(4) 确立的 fields.md §4 策划面口径。F-3 与 F-4 在 `cw_screen_yinlang.py` 同文件多处相邻,实施**一次成文**(T-3 §2.6 准则 5 同款),各节验证门分别过。

### 2.6 关键取舍

1. **F-1 改契约文字 + 确认钮统一化(用户裁定 2026-09-22 两道)**:确认钮查找原各屏机制(area_center+兜底/OCR/env.confirm)全族统一 `round_by_find_and_click_area`——AGENTS §3 找元素点按钮第一原则,兜底静默点击退役(BuyCard 行先例),兜底常量存废(T-37 家族待裁项 #1)随批清偿;辖域澄清文本让契约句与实况一致(确认钮不属机械参数 env 传入)。原「上移决策半」备选作废:确认钮归动作 op 执行体,决策半零确认几何。
2. **F-1 各面一次成文 + 单一表述**:同一分工事实散在模块头/docstring/字段注/两正本多处,只改族级三处会造同 dataclass 内新互斥;各面中指定 action_ops.md §4.5 段首为申报单一源,(3)(4)(5) 与其同文或显式指认 (2),禁第三种口径——同一事实的表述唯一化优先于各处行文风格。
3. **F-1 §4.5 标题行「一行两段」共存(本稿机械参数分句 + 并行批坐标源欠账尾段)**:同一物理行两段文本,整行替换时尾段逐字照抄禁静默删除(尾段保留义务,§2.1(1),r8 对账项);T-1 原「12→13」计数认领随装备退役废止,归 T-37 重导。
4. **F-2 §4 升格本稿自持整句(T-9 撤销后原「并入 T-9 + 要件增补」路径悬空,用户裁决 2026-09-22 收回)**:同一事实单一落点防双源漂移;策划写端臂与遭遇臂/补给臂申报粒度对齐,直接给整句规格,实现者零再设计;:34 欠账注内联于整句末括注(原独立落点撤销,防同句双文本)。
5. **F-2 §3.2.18 新增「采样口径在册的随机发牌」分面而非改列确定性组**:欢愉契约授予体含采样(二选一),非确定面;新分面 = fields.md §2.5 采样口径在「按归属判据逐卡分面」框架的正交补位,不立第三套机制。
6. **F-3 四点位整体归属本稿、T-6 侧销项**:本稿目标文本 = 语义改写 + 编号清出一体(T-6 自申报「只清编号、语义归 T-10」),整体归属使四点位恰有一份落笔文本;备选「编号归 T-6、语义归本稿」会把同句拆两次触碰,违背一次成文且实施顺序耦合。归口 T-37 登记保序。
7. **F-4 清单扩中文形态与裸节号 + 门同源扩模式**:「设计 §N」与裸「§N」同属指向过程件的不可重建指针,清拉丁留中文 = 同语义指针残留且门绿盲区;裸节号经人工归属复核豁免带文档名的正本指针,机械门与人工门双保险(T-5 §2.7「清单与验证门同源」同款承诺)。
8. **F-3/F-4 只清策划域自持命中点**:同族扩散(cw_overlay_pick_action.py 非策划类、全仓正本与注释的 W/rN 与 changes/ 引用)已有 T-3 §2.6(全仓注释卫生批)与 T-5 §2.7(全仓 changes/ 引用清理批)建议在册;单屏稿越权扩面会与全仓批重复劳动,且让审查与设计辖域错位。
9. **F-5 缝锚改「工厂派发调用点 + 测试 monkeypatch」而非删句**:缝位置申报 = 测试 mock 点的导航(两 node 形态锁靠它定位替换点),删句丢导航;改锚修指针保语义。「体迁自」叙事随死指针一并清出(变更史归 git);同专篇 §4 反口径句为已知矛盾面,借同文件触碰一并收口,不留「修 §1 留 §4」的半新半旧。

## 3. 新规范增补(2026-09-22 两条款)

> **基准** = 正本两条新条款(`screens/op-layer.md` §1.1,均用户裁定 2026-09-22,commit 2f35d4011 入正本):**:34 观察标准化门**——观察内容在所属域存在标准注册数据(名字类)时,观察 node 必须在观察时转换成标准注册数据再上报(①形变归一后精确匹配;②不中再 LCS 相似,`one_dragon.utils.str_utils::find_best_match_by_lcs`;两段皆不中 = 转换失败);任一候选转换失败 = 观察失败,观察 node round_fail 早退、零写零上报;多候选命中同一注册名(选项互斥屏)= 识别质量不足以区分,同判转换失败;标准化后动作上报只携 idx,动作/上报层零名字转换;欠账逐批收敛,禁新增未标准化直报。**:37 画面 op 不支持局外单独调用**(行号现值 :37;本节成稿时为 :36,9c8e9016b 插入 :35 后移位——下文规范锚随现值写 :37,族级批专名「:36 局外支收敛 + :34 登记族级批」按 T-37 注册名保留)——不支持脱离对局(`cw_match` 缺席)单独调用调试,此类支持代码不做;无 match(局外)= 零决策零点击 round_success 终结交回(遭遇屏在册先例同款),不设任何兜底决策路径;先例代码锚 = `operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter.act`(:156-165,`match is None` → `round_success('候选读缺/局外,零点击终结交回重读', wait=1.5)`)。
>
> 增补源 = 新规范符合性重审报告 `.debug/progress/2026-09-22-cw-screen-review/reports/respec-T9-T15.md`(本屏 = §2.2,增补 A/B/C 三点;跨屏共性 = §2.8)。时序:本稿对抗收敛在先、两条款入正本在后,增补 = 在已收敛修法(零行为批主体)上叠加申报与改写,不推翻主体、不回退 §1.6 已核对一致面;本节不改 §0–§2 正文,正文需连带改写处在本节逐字给目标文本与落点节号,归实施批按本节落笔。**本稿修法性质 = 零行为批(§0),本节全部为申报级增补:注释/目标文本/登记面,零行为变更;:37 行为改写归属 pick 族族级批(§3.4),本批不动行为、只改申报,防「文档批沉默 = 默认保留」。**

### 3.1 增补 A(:37 残留失效申报清出:#10 目标文本 + observe docstring 连带)

**结论**:§2.3 表 #10 目标文本以「……」截断——现文 `cw_screen_yinlang.py:179-181` 后半句「kernel 直调仅保留无 match 防御路径(局外独立跑;**规约=沿用 cw_screen_invest_env 同款写法**)」若被实施保留,则「规约」申报随 :37 失效(:37 明文「此类支持代码不做」,不存在该规约)。目标文本须显式含该半句的替换文本;同文件 observe docstring(:123-125)「决策走 kernel 直调防御分支,分支原样」同判(respec 报告明示:T-10 站点清单未列,文件已在施工面,连带收录)。

- **落点 1(§2.3 表 #10 目标文本格,整格替换为全文)**:

  ```
  # 策略层决策(唯一入口 = 策略对象,handler 禁 kernel 直调——决策控制分层铁律,flow/README.md §1;写槽已由 report 落容器 → 零参决策。kernel 直调局外支 = op-layer.md §1.1 :37 违规欠账,归族级批改零决策零点击 round_success 终结交回)。
  ```

  (即「W953 批1」清出同前;截断号「……」扩为后半句显式替换:「kernel 直调仅保留无 match 防御路径(局外独立跑;规约=沿用 cw_screen_invest_env 同款写法)」整段删除,以「kernel 直调局外支 = :37 违规欠账,归族级批改零决策零点击 round_success 终结交回」承接。)

- **落点 2(连带站点新增——`cw_screen_yinlang.py::CwScreenYinLang.observe` docstring 尾句)**:现文「match/gs 缺席的局外兜底路径跳过 report,决策走 kernel 直调防御分支,分支原样)。」中「决策走 kernel 直调防御分支,分支原样」替换为:

  ```
  决策走 kernel 直调防御分支 = op-layer.md §1.1 :37 违规欠账,归族级批改零决策零点击 round_success 终结交回
  ```

  (「分支原样」四字随替换删除;「match/gs 缺席的局外兜底路径跳过 report」半句不动——观察侧跳 report 继续有效,op-layer.md §1.1 :18 在册。)

依据(respec-T9-T15.md §2.2 Q2 增补 A + Q3):现役 else 支 = `cw_screen_yinlang.py:185-202`(`decide_planner(list(options), GameState(裸), None)` kernel 直调 → 包装 `CwActionPickPlannerParam` → 派发),出口 = 决策 + 点击 = :37 违规欠账。验收锚:①实施后 grep `cw_screen_yinlang.py` 内 `规约=沿用|同款写法|分支原样` 零命中;②两落点落笔后本文件不再存在「局外支合法保留」类申报(欠账申报形态取而代之;else 支体内注释「kernel 返回值包装动作子类型(kernel 纯函数零触碰,包装归入口/防御路径)」〔:190-191,§2.4 #6 改写后保留〕除外——该注不辖两落点、锚① grep 词表亦不辖,其「防御路径」框定随族级行为批删支一并消失,不作悬账);③行为零变化(本批改动仅注释文本,无逻辑面;§2.3 F-3 验证门 grep 词表不含本两 token,两门互不干扰)。

### 3.2 增补 B(:37 局外支欠账显式登记)

**结论**:本稿对现役 `CwScreenYinLang.act` 无 match else 支零处置(修法性质自申报「零行为变化」,全文无该支条款)——沉默在 :37 下 = 默认保留态势,须显式登记为违规欠账并声明处置归属。

**登记(本节即登记面,原文同 §3.5 报 T-37 台账)**:本屏现役 `CwScreenYinLang.act` 无 match else 支(`cw_screen_yinlang.py:185-202`,kernel 直调 `decide_planner` → 包装 → 派发)= op-layer.md §1.1 :37 违规欠账;处置归属 = pick 族族级批(「:36 局外支收敛 + :34 登记族级批」,T-37 已有归口面);本批(零行为)不动行为、只改申报(§3.1 两落点)。

依据(respec-T9-T15.md §2.2 Q2 增补 B)。验收锚:本节登记在案 + §3.5 台账行;族级批落地验收 = 无 match → round_success、零派发零点击(共享测试锁模板,§3.4)。

### 3.3 增补 C(:34 欠账注:机械参数辖域段 + fields §4 策划子句)

**结论**:观察面 = 左右两卡 OCR 全文裸文本直报(`CwScreenYinLang.observe` :121-166,`planner_opts`),卡文含装备件名,装备注册表在册(`kernel/cw_events.py`:`_PLANNER_EQUIP_ANCHORS` :911 / `_similar_equip_hits` :919 / `_REGISTRY_EQUIP_NAMES` :947);现役转换点 = 决策半(`act` :204-209,`classify_planner_leg` → `leg_type`+`norm_item`,形变救援在决策半)+ 动作上报层(`kernel/cw_action_report/pick_planner.py` 模块头「equip:件名命中 → 装备入栏」;`_apply_equip_leg` :130)= :34 欠账形态(同已撤销的装备屏稿同型)。§2.1(2) 机械参数辖域段把「`leg_type`+`norm_item`(策划)经 env 透传」写成申报单一源、§2.2(4) 把装备腿写端整句写进 fields.md §4,原均无 :34 欠账注——正本会把欠账形态写成无欠账终态契约,补注(零行为,纯申报文本;§3.3 增补 C 同款先例)。

- **落点 1(§2.1(2) 机械参数辖域段代码块)**——在「域载荷逐行」bullet 末行(`  PickEncounter 组装 = 零域字段。`)之后、「op 类体内零决策」行之前插入一行:

  ```
    (件名归一现役在决策半与动作上报层 = op-layer.md §1.1 :34 欠账,收敛终态 =
    观察侧转换、动作上报只携 idx,逐批收敛禁新增)
  ```

- **落点 2(已并入 §2.2(4) 自持整句)**——原「合并要件 + :34 注」独立落点随 T-9 撤销作废,:34 欠账注已内联为 §2.2(4) 整句的末括注(「件名归一现役在决策半与动作上报层 = op-layer.md §1.1 :34 欠账…」,见 §2.2(4) 落笔规格),随本稿实施批一次成文,不再单列防同句双文本。

依据(respec-T9-T15.md §2.2 Q1 增补 C)::34「标准化后下游全链只在标准名上工作:……动作上报只携带选择序号(idx)……动作/上报层零名字转换。收敛在途:……其余名字类观察屏为欠账,逐批收敛,禁新增未标准化直报」。验收锚:①两落点落笔后机械参数辖域段与 §2.2(4) 整句各含一处「:34 欠账」注;②fields.md §4 骇入策划写端臂随本稿实施批落笔(§2.2(4) 整句含 :34 注,自持);③本批零行为(无代码逻辑面)。

### 3.4 :37 行为改写归属与族级批合流申报(G1 跨屏共性②)

- 本稿为零行为批,respec 报告 §2.8 共性②明示「T-10 为零行为批,只做申报级增补」——:37 行为改写不在本稿施工面。
- **归属 = pick 族族级批**:5 屏(T-11/T-12/T-13/T-14/T-15;T-9 随装备屏撤销除名)的 :37 行为改写为同一形态(else 支/守卫臂 → round_success 终结交回),一次族级批实施 + 共享测试锁模板(无 match → round_success 零派发零点击);本屏 else 支随该批一并改写,族级口径已由 :37 统一(kernel 判据直调支不豁免),不留候裁措辞。
- **行为批落地时的注释同步义务**:§3.1 两落点的欠账申报文本(「归族级批改……」)在族级批落地时同步改为现役形态申报(else 支 = 零决策零点击 round_success 终结交回),防注释申报滞后于行为(同批一次成文)。
- 与 §1.6「已核对一致面」的关系:「本屏无盲选回退(决策出口合规)」结论辖对局内决策出口(策略返回 None/非法类型/idx 越界 = 响亮暴露),:37 面为局外支(kernel 直调兜底决策路径),两不相涉——§1.6 结论维持,:37 欠账面以 §3.2 登记为准。

### 3.5 T-37 登记行(欠账面,原文)

> - [T-37 登记][欠账] planner(T-10)::37 局外支欠账(条款注册名「画面 op 不支持局外单独调用」;注册时锚 :36,9c8e9016b 插入 :35 后移位)——`CwScreenYinLang.act` 无 match else 支(`cw_screen_yinlang.py:185-202`,kernel 直调 `decide_planner` → 派发)= 决策 + 点击,违 :37;处置 = 归「:36 局外支收敛 + :34 登记族级批」改零决策零点击 round_success 终结交回;本稿零行为批只改申报(act 决策注 + observe docstring 尾句,§3.1),不动行为。
> - [T-37 登记][欠账] planner(T-10)::34 观察标准化门欠账——观察面裸文本直报 `planner_opts`(`CwScreenYinLang.observe` :121-166),件名归一现役在决策半(`classify_planner_leg` :204-209 → `leg_type`+`norm_item`)与动作上报层(`kernel/cw_action_report/pick_planner.py` equip 腿,`_apply_equip_leg` :130);收敛终态 = 观察侧转换、动作上报只携 idx;欠账注落点 = flow/action_ops.md §4.5 段首机械参数辖域段域载荷行后 + fields.md §4 骇入策划写端臂整句(§2.2(4) 自持,:34 注已内联)。逐批收敛,禁新增未标准化直报。

## 4. 二轮新规范增补(2026-09-22 用户裁定两条款:选择坐标观察上报 + 每个动作 op 单独一个文件)

> **基准** = 用户裁定 2026-09-22 原文,两条款均已入正本(本节以正本注册名指称;行号 = 落笔时正本现值,消费以条款名为准——与 §2.5 #14「行号随代码漂移,不作定位依据」判据同源):
> **条款一「选择坐标观察上报」**(`screens/op-layer.md` §1.1 :35):裁定原文 = 「观察上报选项时候，除了要将识别内容归一化到标准注册数据外，还需要上报具体的坐标，存到game state，即选中这种选项具体的坐标，这里包括商店、各个需要选择的overlay，这样策略侧，只需要输出下标就可以了，执行的动作op，也可以根据下标，从game state获取坐标来执行。」;正本要点 = 归一化与坐标在同一次观察一并入容器、**坐标单一真相源 = 观察上报**(由决策侧半现算改为观察时上报)、动作/上报层零坐标现算、适用范围 = 商店与各需选择的 overlay、收敛在途 = 现役坐标决策半现算经 env 传入动作 op 逐批收敛禁新增第二坐标源。稿内「选中点几何随观察入容器/env 定位载荷退役」= 该条款执行面的推演表述(几何现算即第二坐标源,收敛后自然退役),非正本原文。
> **条款二「每个动作 op 单独一个文件」**(`screens/op-layer.md` §1.2 :48):裁定原文 = 「另外就是必须每个动作op单独一个文件。」(逐字含前缀;「另外就是」= 用户语句衔接词,非条款内容;兄弟稿引语转写差异归 T-37 对账);正本条款 = 一 op 一文件禁多类同居,与上报侧每动作一文件对称;`cw_overlay_pick_action.py` 11 类同居欠账已在正本在册申报(:48 现值,装备退役批后),本节不重复立项。
>
> 性质:本稿主体(§0–§2)与一轮增补(§3)同判——本节全部为申报级增补(欠账登记/申报文本/正本互指注),零行为变更;两条款的行为迁移(观察报坐标 + env 定位载荷退役 + 动作 op 取点改容器源;pick 族文件拆分)归 pick 族族级批(§3.4 同一归属面),本批不动行为、只改申报,防「文档批沉默 = 默认保留」。同型欠账在 pick 族其余屏与商店域扩散,各屏稿同型增补与族级汇总归编排侧,不在本稿扩面(§2.6 取舍 8 同款辖域纪律)。

### 4.1 增补 D(条款一:坐标欠账申报)

**结论**:本屏三面现值 = 条款一欠账形态——①观察面 `CwScreenYinLang.observe`(:121-166)组装 `PlannerOption(idx, text)` 零坐标上报;②选中点几何住决策半(`act` :203 `_card_point(pick.idx)`,含避开卡内详情钮的点位推导)经 `env.target` 传入;③动作 op `CwActionPickPlannerOp.run` 消费 `env.target` 点卡,不经容器按下标取点。

**对账声明(2026-09-22,并行批 canonical 化后)**:条款一的登记面已由并行批三面落正本——全域 = `flow/action_ops.md` §1 增补 5(:21,键特形/守卫语义/禁第二坐标源)、族级 = 同文件 §4.5 标题行尾段(:120「坐标源欠账」,`env.target` = 合法过渡形态、逐屏收敛)、字段面 = fields.md §3.4.5a「选项坐标域」(:843,`*_opts_xy` 族/typed `xy`/payload 坐标字段)+ §3.4 头部伴随域总声明(:740-741)。本节不重复任何一层登记,只补**屏域站点挂接**两处(落点 1/2);原处方「机械参数辖域段插独立坐标注」作废——段居标题尾段之下,族级欠账申报已在同节,再插 = 同节双源,违本稿一次成文纪律。

- **落点 1(screens/planner.md 开放设计注新增一条)**——现三条(:73 chosen_hack / :74 选中点击高度比例 / :75 观察捕获集)之后追加:

  ```
  - 选择坐标观察上报欠账(用户裁定 2026-09-22,op-layer.md §1.1 :35;全域/族级
    登记 = action_ops.md §1 增补 5 与 §4.5 标题尾段,字段面 = fields.md §3.4.5a):
    planner_opts 观察载荷现役零坐标(observe 组装 PlannerOption(idx, text)),
    选中点几何住决策半(_card_point 避开详情钮的点位推导)经 env.target 传入
    动作 op——收敛终态 = 坐标与归一化同次观察入容器(坐标单一真相源 = 观察
    上报)、策略只出下标、动作 op 按 idx 从容器取点执行;收敛归 pick 族
    族级批(与局外支收敛族级批同批)。
  ```

- **落点 2(`game_state/logic-updates/pick-planner.md` 两处同型句挂注;该文件已在 §2.5 触碰面,§2.5(3) 自立判据同款连带;逐站点挂注 = 并行批 PickSupply 行欠账注同款先例)**:
  - §2 末行(「**选中点几何**(避开卡内「详情」按钮区)归决策半 `_card_point` 单一源现算,经 `env.target` 传入。」)句尾追加:

    ```
    (决策半现算经 env = 「选择坐标观察上报」欠账,action_ops.md §1 增补 5,收敛归族级批)
    ```

  - §3 第 1 条括注内句尾(「……点错触详情面板的实证几何治理」之后、右括号之前)追加:

    ```
    ;选中点经 `env.target` = 选择坐标观察上报欠账(action_ops.md §1 增补 5,§2 行注同源)
    ```

依据:用户裁定 2026-09-22 条款一原文 + 正本三面 = `screens/op-layer.md` §1.1 :35(注册名/辖域判据/过渡期规则/收敛在途句)、`flow/action_ops.md` §1 增补 5(:21)与 §4.5 标题尾段(:120,并行批 97c81cdf3/02057f6c8 落)、fields.md §3.4.5a(:843);现值 = `observe` :155-160(`PlannerOption(idx=…, text=…)` 组装零坐标)/ `act` :203(`_card_point(pick.idx)` → `env.target`)/ `CwActionPickPlannerOp.run`(`target = env.target` 点击,行号随装备退役批位移,符号锚为准);登记面取舍 = 全域/族级/字段三层已在册,屏域站点(开放设计注 + 专篇两处)补挂接,机械参数辖域段不再插注(标题尾段即其欠账申报,防同节双源)。验收锚:①screens/planner.md 开放设计注含本条(含三层登记指针);②pick-planner.md §2/§3 两处含欠账注;③§2.1(2) 机械参数辖域段内无坐标欠账注(对账声明成立);④行为零变化(`_card_point` 迁观察侧、`env.target` 退役均归族级批,本批无代码逻辑面)。

### 4.2 增补 E(条款二:每个动作 op 单独一个文件——planner 域涉事面申报)

**结论**:条款二正本(op-layer.md §1.2 :48)已在册申报全域欠账 = `cw_overlay_pick_action.py` 单文件同居 11 个动作 op 类(:48 现值,装备退役批后);本节只申报 planner 域涉事面与缝锚随迁义务,不重复立项。涉事面 = `CwActionPickPlannerOp`(11 类之一)与域 env `OverlayPickExecEnv`(数据类,非动作 op,拆分时的归置随族级批裁决);拆分归 pick 族族级批(:37 行为改写同批面,§3.4);本批(零行为)不动文件结构。

- **落点 1(施工注,住本稿、不进任何正本目标文本)**:`cw_overlay_pick_action.py` 拆分批落地时,§2.5 表 #1 与专篇 `logic-updates/pick-planner.md` §1 的 op 载体文件路径锚(`operations/cw_op/cw_overlay_pick_action.py::…`)随迁失效——定位一律以符号锚 `文件::符号名` 的符号名为准,族级批实施时同步改写该两处路径。
- **落点 2(登记面)** = 本节 + §4.3 台账行,原文同报 T-37。

依据:用户裁定 2026-09-22 条款二原文 + 正本条款 `screens/op-layer.md` §1.2 :48(含 11 类欠账在册申报);现状核验 = `operations/cw_op/` 目录逐文件比 action_ops.md §4 清单,唯 `cw_overlay_pick_action.py` 多类同居(`cw_tool_use_action.py` 七注册行同指一 op 类不违);F-5 缝锚不受损(缝 = 注册表工厂派发调用点,住 `cw_screen_yinlang.py`,文件拆分不影响;op 载体路径锚随迁,符号名不变)。验收锚:①本节登记在案 + §4.3 台账行;②§2.5 #1 目标文本保持无 changes/ 自引与本稿节号(路径随迁义务由本施工注承载);③文件结构零改动(拆分归族级批)。

### 4.3 T-37 登记行(欠账面,原文)

> - [T-37 登记][欠账] planner(T-10):选择坐标观察上报欠账(屏域站点挂接;全域/族级/字段三层登记已由并行批在册 = action_ops.md §1 增补 5/§4.5 标题尾段/fields.md §3.4.5a)——`planner_opts` 观察载荷零坐标(`CwScreenYinLang.observe` :121-166,`PlannerOption(idx, text)` 组装),选中点几何住决策半(`act` :203 `_card_point` → `env.target`),动作 op 消费 env 而非容器下标取点(`CwActionPickPlannerOp.run`);欠账注落点 = screens/planner.md 开放设计注(§4.1 落点 1)+ `logic-updates/pick-planner.md` §2/§3(§4.1 落点 2);机械参数辖域段不另插注(族级申报 = §4.5 标题尾段,防同节双源,§4.1 对账声明);收敛终态 = 坐标单一真相源 = 观察上报、策略只出下标、动作 op 按 idx 从容器取点执行;行为迁移归 pick 族族级批。
> - [T-37 登记][欠账] planner(T-10):每个动作 op 单独一个文件(op-layer.md §1.2 :48 在册全域欠账的 planner 域涉事面)——`cw_overlay_pick_action.py` 11 类同居中之 `CwActionPickPlannerOp`,域 env `OverlayPickExecEnv` 归置随批裁决;拆分归 pick 族族级批;拆分时 `logic-updates/pick-planner.md` §1 与 §2.5 表 #1 的 op 载体文件路径锚随迁失效,定位以符号名为准(§4.2 落点 1 施工注);本稿零行为批只登记,不动文件结构。
