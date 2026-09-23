# T-19 简易武装箱 修法设计(armory_box)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决(对抗轨迹:r1 收敛;攻击者附 2 条文字级备注[攻-1「F11 出处指认」落空/攻-2「R7」表述精度],定稿前文字级落实,见 reviews/T-19-attack-r1.md)
- 发现源:F-1..F-3 = `.debug/progress/2026-09-22-cw-screen-review/reports/T-19-r1.md`;本稿 §1 的症状与现状摘录均为该报告差距说明的转述,不新增事实。
- 修法文件面(全部为文档/注释文本,零行为变化):
  1. `docs/develop/sr_od/application/currency_war/screens/README.md`(§5.5 名册行,F-1)
  2. `src/sr_od/application/currency_war/operations/cw_screen/cw_screen_armory_box.py`(模块 docstring,F-2)
  3. `docs/develop/sr_od/application/currency_war/screens/armory_box.md`(开放设计注,F-3)
- 路径约定:本文 `screens/`、`flow/`、`strategy-docs/`、`game_state/` = `docs/develop/sr_od/application/currency_war/` 下路径;`operations/`、`kernel/`、`strategies/` = `src/sr_od/application/currency_war/` 下路径;screen_info 建档 = `assets/game_data/screen_info/` 下路径。

## 1. 问题与动机

### 1.1 F-1:screens/README.md §5.5 名册把「武装箱弹窗」错列 pick 决策族成员(中)

- **现状症状**:§5.5 名册行末成员写作「武装箱弹窗」。该名 = 简易武装箱说明弹窗的注册 screen_name(`currency_war_armory_box_dialog.yml`:`screen_name: 货币战争-武装箱弹窗`;分发臂 = `operations/cw_loop.py`「货币战争-武装箱弹窗」→ `CwScreenArmoryBox`)。本弹窗 as-built = 空决策形态:无选择面、零逻辑态账、零策略器问询(op-layer.md §3 全形态行「简易武装箱六屏为空决策变体:决策动作 node = 重入裁决 + 固定推进,零策略器问询」;`operations/cw_screen/cw_screen_armory_box.py` 全文件无 `decide_*`/strategy 触点)。真正消费 `decide_box_card` 的选卡屏 = 另一注册画面「货币战争-备战-武装箱选择」(`operations/cw_screen/cw_screen_box_pick.py::CwScreenBoxPick`,`operations/cw_loop.py` 独立身份臂,journal_name='武装箱选择')。名册该成员无论按字面(把空决策屏申报为 pick 族)还是按善意(实指选卡屏但写错屏名)读均不成立,且「武装箱弹窗」与选卡屏构成兄弟画面撞名,名册读者无法分辨。
- **根因归层**:表示层——正本名册的成员登记与画面分型事实不符(登记面错误;代码与 `screens/armory_box.md`、`screens/box_pick.md` 均站在 op-layer 一侧,无行为面问题);伴随表示层命名缺陷:成员名既非注册 screen_name 也未带模块锚,撞名无消歧手段。
- **解决到哪**:更正名册该位成员登记,使「名册 ↔ 决策句(`decide_box_card`)↔ op-layer §3 分型 ↔ 注册 screen_name」四方一致,并以「注册名 + 模块锚」双括注根除撞名歧义。
- **明确不解决**:
  - 名册其余成员的归属与 `screens/README.md` §8 文档索引的对应关系(如银狼升星)——各屏各面,归各自屏的审查/建档任务,本稿不核。
  - 名册决策句「pick 族九接口」的接口计数与成员映射核算——报告未列,本稿对该句逐字不动。
  - `strategy-docs/25_event_overlays.md` 的同族撞名面(篇头画面族清单与 §2 动作表「武装箱弹窗」行均以弹窗名承载 `decide_box_card` 选卡面,且该行残留已删符号 `PickBoxCard`)——strategy-docs 不在 T-19 审查正本集,归 strategy-docs 正本维护面;本稿仅指认,供编排方分流。
  - `game_state/fields.md` §3.4.5「装备三选一与武装箱选择面同屏性待采证」在册候裁面——不动。

### 1.2 F-2:cw_screen_armory_box.py 模块 docstring 变更史叙述 + 「R7 批 2a」弱引用(低)

- **现状症状**:模块 docstring 四处违 AGENTS.md §8:①「⚠️ M19 建档时曾按『点箱图标开箱→四选一』建模——错误(展示图不可点);M20 实锤后改关闭模型」= 勘误过程叙述;②「四选一选卡职责在独立画面 op(cw_screen_box_pick,CwScreenBoxPick;R7 批 2a 起替代原 CwActionPickBoxCardParam 备战动作形态)」= 替换史叙述;③机制条第 3 条尾「选卡 = 武装箱选择画面 op ``cw_screen_box_pick``,R7 批 2a」= 无路径迭代局部编号(×2 之一);④形态段「原单 node 形态的『pending 先行、miss fail 后置』位序随两 node 拆分自然消解(门在观察 node 先行,裁决住决策 node 顶部)」= 形态替换史。机制事实本体(顶部箱图标为展示图不可点、正确动作 = 点 × 关闭、不关挡死底层屏)无误,必须保留。
- **根因归层**:约定层——「变更史不进注释」「引用必须是持久索引」两条纪律的执行偏差(历史叙事壳未剥 + 批号未给路径),载体 = 代码注释。
- **解决到哪**:三处定向删改,docstring 只留当前时态机制事实与全路径符号锚;在册判例认可的面(M19/M20 对局编号实证锚、changes/ 目录名指针)保留。
- **明确不解决**:代码 `:103` 行内注释「bug#1 缓解」标签的去留——跨报告在册分歧,候 T-37 裁决,本稿不触碰;M19/M20 实证数据的档案回溯核对——审查不可核对面,需实机/档案批;全仓同类注释瑕疵扫描——各屏审查任务各覆盖各面,本稿不设新工具门。

### 1.3 F-3:armory_box.md 开放设计注「F11 例外清单」迭代条目号弱引用(低)

- **现状症状**:`screens/armory_box.md` 开放设计注写「sim 腿不适用(F11 例外清单)」——「F11」为 changes/2026-09-18-screen-op-flat-report 迭代 design 内部条目号,正本引用未给路径、正本不自足,与 AGENTS.md §8(引用必须是持久索引)、§9(正本禁引 changes/ 内容,正本必须自足)相抵。
- **根因归层**:约定层——与 F-2 同族根(持久索引纪律执行偏差),载体 = 正本文档。
- **解决到哪**:改纯语义表述,条目编号出正本;例外清单内容经本篇 §9 既有测试锁指针可达,自足性恢复。
- **明确不解决**:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py` 模块 docstring「F11 sim 腿不适用例外清单」节标题中的同族编号——审查未列发现,测试代码注释面;可在实施批连带去「F11」字样,非本稿必修面。前半句「按钮-开箱点击」定位区退役或保留的裁决——开放设计注在册候建档清理批,本稿不改其候裁状态。
- **同族根升层判断(F-2/F-3)**:两发现同属「持久索引/无变更史」纪律的执行偏差。同族第 2 件按根源两问核查:本审查迭代(逐屏静态审查 + T-37 汇总对账)已是系统性防漏机制,单屏设计稿不再新设 grep 守卫/CI 门类工具面;同族第 3 件再现时再议机制级升级。

## 2. 方案

### 2.1 F-1 修法:README §5.5 名册成员更名(一处编辑)

**编辑**(`screens/README.md` §5.5 名册行;该行是「武装箱弹窗」在本文件唯一出现位):

现状:

> 投资策略/补给/遭遇(货币战争-遭遇节点)/盛会之星/选择伙伴/选择装备/命运卜者(`cw_screen_fortune.py`)/银狼升星(`cw_screen_yinlang.py`)/祈愿试炼/星徽秘典四选一/专家邀请函/**武装箱弹窗**。决策 = pick 族九接口 + `decide_box_card`,规格 = strategy-docs 13 号篇。

改为:

> 投资策略/补给/遭遇(货币战争-遭遇节点)/盛会之星/选择伙伴/选择装备/命运卜者(`cw_screen_fortune.py`)/银狼升星(`cw_screen_yinlang.py`)/祈愿试炼/星徽秘典四选一/专家邀请函/武装箱选择(货币战争-备战-武装箱选择,`cw_screen_box_pick.py`)。决策 = pick 族九接口 + `decide_box_card`,规格 = strategy-docs 13 号篇。

**编辑要点**:
- 成员名 = 选卡屏短名「武装箱选择」+ 注册 screen_name「货币战争-备战-武装箱选择」+ 模块锚 `cw_screen_box_pick.py`:三重锚与名册既有两种括注样式(遭遇 = 注册名括注;命运卜者/银狼升星 = 模块锚括注)取并,弹窗/选卡屏撞名歧义就此消除。
- 顺带去除仅该成员携带的加粗(其余成员无加粗,纯排版噪声)。
- 决策句逐字不动:更名后「+ `decide_box_card`」与名册成员对应关系成立(`decide_box_card` 唯一消费方 = `CwScreenBoxPick`,依据 = `operations/cw_screen/cw_screen_box_pick.py` 决策段 `match.strategy.decide_box_card()`)。
- 本弹窗不迁入任何名册:README 对它的既有记载位 = §8 文档索引(「弹窗与部署」列 armory_box.md)+ §5.3 OpenBox 行与 §6 推进型弹窗行的泛化描述,已足;本编辑不改这些面。

**依据**(就地):分型判据 = op-layer.md §3 全形态行(CwScreenArmoryBox = 空决策变体、CwScreenBoxPick 在全形态清单)与 screens/README.md §3(入决策规范 ⇔ 选择面 ∧ 逻辑态账,本弹窗两者皆缺);分发事实 = `operations/cw_loop.py` 两独立身份臂(弹窗臂/武装箱选择臂);兄弟职责切分 = screens/box_pick.md §1(「前者 = 展示弹窗关闭,本屏 = 选卡画面」);本屏形态自申报 = screens/armory_box.md §2。

**验收锚**(静态可判):
- `screens/README.md` 全文「武装箱弹窗」归零;名册行含「武装箱选择(货币战争-备战-武装箱选择,`cw_screen_box_pick.py`)」。
- 决策句、其余成员、其余章节逐字不变(diff 仅名册行一处)。

**关键取舍**:
- 取「更名补正」,不取「删除成员」:删除会让决策句「+ `decide_box_card`」悬空(名册无成员对应),且 §8 索引(单选族含 box_pick.md)、§5.3 OpenBox 行、§6 终结总表均把选卡职责记在武装箱选择屏名下——删成员制造新的正本内不一致。
- 不取「连决策句一起裁掉 `decide_box_card`」:违背 as-built——`decide_box_card` 在役(flow/README.md §2.2 pick 族接口行、strategy-docs/13_pick_family.md §1 E18)。
- 括注取双锚而非单锚:单注册名括注(遭遇式)可解撞名但少模块入口;单模块锚括注(命运卜者式)不解撞名。双锚一次根治,不留第二处弱面。

### 2.2 F-2 修法:模块 docstring 定向删改(以整段替换实施)

**文件** = `operations/cw_screen/cw_screen_armory_box.py`,仅模块 docstring;类/函数体与全部行内注释不动。

三处删改:
1. 删勘误段(原 :12-14 整段 + 紧邻一个空行)。段内两条当前值事实去向:「箱图标展示图不可点」机制条第 2 条已在档;「选卡职责在独立画面 op、本 op 只关弹窗」并入机制条第 3 条(下条编辑)。
2. 机制条第 3 条尾:删「R7 批 2a」,符号锚升级为全路径 `cw_screen_box_pick.py::CwScreenBoxPick`。
3. 形态段:删「原单 node 形态的『pending 先行、miss fail 后置』位序随两 node 拆分自然消解(门在观察 node 先行,裁决住决策 node 顶部)。」(括注内容 = 现行两 node 形态的复述,形态段前文已申报,零信息损失;其后 sim 腿句顺势换行重排。)

**改后 docstring 全文**(实施 = 整段替换,消除行内手误空间):

```python
"""货币战争 道具获得弹窗 op(「简易武装箱」类说明弹窗;2026-08-15 M19 首见停机建档,M20 实锤机制)。

机制(M20 17:37-18:05 实证,3 候选点击坐标全无反应 + × 关闭露底层屏):
- 弹窗 = **获得道具时的说明弹窗**(标题「简易武装箱」+ 说明「点击后开启…从四件简易装备中选择
  一件获得。该道具使用后消失」),叠在 3 选 1 屏(投资策略/环境)或备战上;
- 弹窗内**顶部箱图标是展示图不可点**((812,175)/(810,194)/(960,837) 三点全无反应);
- 正确动作 = **点 × 关闭**弹窗(道具进背包,备战界面箱槽走 prep_actions 的
  CwActionOpenBoxParam 开箱链路;四选一选卡职责在独立画面 op
  ``cw_screen_box_pick.py::CwScreenBoxPick``,本 op 只关弹窗);
- 不关会挡死底层屏(M20 卡 19min/286 次 retry 实证)。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段
直继承 SrOperation(轻屏统一形态)。观察 node = 标识门(id_mark「标识-简易
武装箱」,miss 未发 = round_fail 交编排壳按步分流)+ obs{on_screen} → 调
占位 ``report_screen_armory_box_obs``(统一形态;本屏现役零容器写点,接口
为占位,match/gs 缺席跳过)→ obs 挂实例属性进决策 node。决策动作 node =
重入裁决顶部(点 × 已发 → 锚不在 = 弹窗已关(道具进背包)→ success 交回;
锚在 = 点击未落地 → 重点)→ 点 × 关闭 → ``round_wait`` 循环推进(不烧节点
重试预算;不收敛 = 动作 bug 响亮暴露,无防御上限)。本屏 sim 腿 = 不适用
(sim 无对应画面段),等价判据主承重 = 实机在册行为锁。
"""
```

**保留不动面与依据**(就地):
- 「2026-08-15 M19 首见停机建档」「M20 17:37-18:05 实证」「(812,175)/(810,194)/(960,837)」「M20 卡 19min/286 次 retry」= 对局编号持久实证锚,属 AGENTS.md §8 持久索引条款的合法形态(同「25 局实机 HP 轨迹校准」),保留。
- 「形态(迭代 2026-09-18-screen-op-flat-report)」= changes/ 持久目录名指针,在册判例不计(T-8/T-15 同款),保留。
- 机制条其余两条、形态段其余表述、sim 腿申报:与现状逐字一致。

**依据**:AGENTS.md §8「变更史不进注释:注释只留当前值成立的理由 + 指针」「引用必须是持久索引:要么持久索引(ADR-NNNN、文件路径、符号名),要么纯语义描述」;勘误/替换史判例 = T-19-r1 F-2 所引 T-16-r1 F-2、T-8-r1 口径。

**验收锚**(静态可判):该文件内「R7」「批 2a」「曾按」「原单 node」归零;「cw_screen_box_pick.py::CwScreenBoxPick」在档;除上述三处外 docstring 与现状逐字一致(对照本节改后全文)。实施注:属 Python 代码变更,落码后按 AGENTS.md §6 重启 MCP server;现役测试锁断言行为与结构(两 node 形态/占位 report 恰一次/重入裁决组合,依据 = T-19-r1 §3 第 5 项锁面核实),无 docstring 文本断言,锁面无需翻新。

**关键取舍**:
- 取「三处定向删改 + 整段替换实施」,不取「全文重写重排」:重排无信息收益、徒增对照验收噪声;整段替换保证结果逐字节可验收。
- 取「勘误段整段删除」,不取「仅去批号保留段落」:该段本体 = 「曾按 X 建模——错误;后改 Y」勘误叙述,删批号不治根(T-8-r1 判「从什么改成什么」叙述计入的同族面);段内当前值事实在机制条全数在档,零损失。
- 取「保留 M19/M20 实证锚与目录名指针」,不取「一并清理」:两者均有在册判例认可,本稿不重审在册判例(防跨稿口径漂移)。

### 2.3 F-3 修法:开放设计注改纯语义表述(一处编辑)

**编辑**(`screens/armory_box.md` 开放设计注):

现状:

> - 档案「按钮-开箱点击」定位区无生产消费点(退役或保留候建档清理批);sim 腿不适用(F11 例外清单),等价判据承重 = 实机行为锁 + 两 node 行为锁。

改为:

> - 档案「按钮-开箱点击」定位区无生产消费点(退役或保留候建档清理批);sim 腿不适用(sim 无对应画面段),等价判据承重 = 实机行为锁 + 两 node 行为锁(锁面 = §9)。

**要点与依据**(就地):
- 「sim 无对应画面段」= sim 腿不适用的语义理由,与模块 docstring「本屏 sim 腿 = 不适用(sim 无对应画面段)」同源——纯语义描述,AGENTS.md §8 持久索引合法形态。
- 锁面经本篇 §9 既有指针可达(`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py`,其 docstring 在册转录含 sim 腿不适用例外清单内容),正本自足恢复(AGENTS.md §9)。
- 前半句「按钮-开箱点击」候裁申报不动(在册候建档清理批)。

**验收锚**(静态可判):`screens/armory_box.md` 全文「F11」归零;「sim 无对应画面段」在档;§9 未变。

**关键取舍**:
- 取「纯语义表述」,不取「显式改指测试文件『F11』节」:后者把弱编号换一个载体继续携带(治标);§9 指针已把读者送到锁文件,语义自足。
- 测试文件 docstring 的「F11」节标题为同族连带面:实施批可顺手把节标题改为「sim 腿不适用例外清单」(去编号),但该项未列发现、不在本稿必修面——列此仅供编排方并批裁决。
