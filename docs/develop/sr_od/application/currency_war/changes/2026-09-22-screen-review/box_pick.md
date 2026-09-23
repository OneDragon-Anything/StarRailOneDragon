# T-16 武装箱选卡 修法设计(box_pick)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决+新规范增补待裁决+坐标规范增补待裁决(对抗轨迹:r1 未收敛 6 条低→修订→r2 未收敛 6 条低→修订→r3 未收敛 3 条低→修订→r4 收敛 0 条;发现持续降级,无结构性返工;攻击报告 = `.debug/progress/2026-09-22-cw-screen-review/reviews/T-16-attack-r1.md`、`…/T-16-attack-r2.md`、`…/T-16-attack-r3.md`、`…/T-16-attack-r4.md`;增补节定点对抗(`respec-attack-C16.md`)未收敛 5 条低→按攻击结论修订 §3[F-3 落本稿 §3.2 行段锚改 :138-162;F-4 落本稿 §3.3 咬合表补 #14 行;F-1/F-2/F-5 落 wish_trial/bookcard/expert_invite];新规范增补(2026-09-22 两条款)= §3,重审输入 = `.debug/progress/2026-09-22-cw-screen-review/reports/respec-T16-T25.md`;坐标规范增补(:35/:48)= §4,依据 = 前置底册 coord-norm-addenda-plan.md §2.4 + op-layer.md §1.1 :35/§1.2 :48;坐标增补节定点对抗(`.debug/progress/2026-09-22-cw-screen-review/reviews/coord-attack-T15-16-17.md`)未收敛 6 条低(本稿 A-3)→按攻击结论修订 §4[A 类伴随域 `_PAYLOAD_DOMAINS` 映射登记补录为批1 义务(不入映射 = 离屏清场时坐标域跨屏携陈值),T-13/T-14 同族随 T-37 对账],状态维持待用户裁决)
- 发现源:`.debug/progress/2026-09-22-cw-screen-review/reports/T-16-r1.md`(F-1..F-6;总判定 = 有问题,高0 中1 低5)。涉事代码与代码内文档以审查时点工作树为真值;本文定位一律符号锚 / 文档节号(行号仅定位辅助)。代码路径根 = `src/sr_od/application/currency_war/`,文档路径根 = `docs/develop/sr_od/application/currency_war/`(下文反引号短路径均相对此两根)。
- 修法性质:**生产代码零行为变化**——F-1/F-5 = 正本文档措辞与失效节删;F-2 = 注释/docstring 卫生;F-3 = schema 登记键名纠偏 + 测试断言同步(登记面,零按键读端)+ 随批新增 schema 键对齐测试锁一条(防线,零生产行为);F-4 = 函数签名类型注解;F-6 = 跨区登记(不实施)。
- 文档形态:单文档方案(无详设),§2 即完整设计。

## 1. 问题与动机

### F-1 box_pick.md 开放设计注陈旧:宣称的预检缺口已不存在且所指符号已消失(中)

- **现状症状**:`screens/box_pick.md::开放设计注`(末节,唯一一条)申报「分发锚未登记外循环分发锚预检表 `cw_loop.py::DISPATCH_AREA_ANCHORS`(iter1 可解析性预检覆盖缺该行,申报不自定案)」。两处与现值不符:①`DISPATCH_AREA_ANCHORS` 符号全 src 零命中(grep 核),所指预检表已不存在;②现役预检 = `operations/cw_loop.py::_dispatch_anchor_precheck` 遍历 `CW_DISPATCH_SCREENS`,条件 = 画面档存在 ∧ 有 id_mark 锚——「货币战争-备战-武装箱选择」在册于清单(cw_loop.py:779),建档 `assets/game_data/screen_info/currency_war_battle_prep_supply_box.yml` 的「标识-请选择」`id_mark: true`(建档现值核),预检条件满足。即注所申报的缺口在现机制下已闭合,正本向维护者申报一个不存在的缺口并指向一个不存在的符号。
- **根因归层**:约定层——预检机制换装(`DISPATCH_AREA_ANCHORS` → `CW_DISPATCH_SCREENS` + `_dispatch_anchor_precheck`)时未同步清除该画面篇已闭合的候裁注;as-built 无状态纪律(screens/README.md §2「纪律:as-built 无状态」)的维护缺位。
- **解决到哪**:删除 `screens/box_pick.md` 末节「开放设计注」整节(该节仅此一条,候裁事项已失效,无残留开放问题);判定依据就地标注于修法(§2.1)。
- **明确不解决**:预检机制本体与「缺画面不中止运行」口径(现役形态 = 报告 F-1 差距说明同款口径,合规面);分发判定语义(单一源 = `flow/outer_loop.md` §2.2,本稿零触);其他画面篇各自的开放设计注(各归其稿);`changes/` 内对该注的迭代工件残留引用(寿命 = 迭代,随清理自灭)。

### F-2 cw_screen_box_pick.py 注释引用失效文档与未定位迭代标识(低)

- **现状症状**:`operations/cw_screen/cw_screen_box_pick.py` 注释站点——①失效文档指针:`screen_op.md §7` 三处(模块 docstring :9-10、:37,类 docstring :61;`screen_op.md` 在 screens/ 目录不存在,单选族例外正本现为 `screens/README.md` §3 形态分型判据 / `screens/op-layer.md` §3);②模块头会话局部标识与无路径迭代件引用:「R7 独立立档;unified-action-factory 批 2a」(:1)、「R7 正位(用户裁定,design.md §2.6/R7)」(:3)、「批 2a 起形态」(:6)、「2026-09-12 动作 op 规范判读应修②」(:20)——R7/批 2a 为迭代局部编号,`design.md` 未给全路径(可解析性依赖读者自行猜 changes/ 目录);③「pick-op-unify 批」(:36 模块 docstring、:114 act docstring)在 changes/ 目录已无可解析目标(报告 F-2 差距说明 glob 零命中)。判据语义本身与正本一致,仅指针失效/弱引用。
- **根因归层**:约定层(注释纪律执行残留)——AGENTS.md §8「引用必须是持久索引:注释里禁出现会话局部标识符……出处要么写成持久索引(ADR-NNNN、文件路径、符号名),要么写成纯语义描述」「变更史不进注释」;AGENTS.md §9「changes/ 会不定期、无理由删减——代码与正本文档禁引其内容(长期引用)」。
- **解决到哪**:本文件全文件注释/docstring 按全迭代统一清理准则(T-3 稿 `changes/2026-09-22-screen-review/battle_wait.md` §2.6 五条:禁形一·会话局部标识符 / 禁形二·变更史叙述 / 改写方向·「结论→出处→边界」当前时态 / 保留豁免 / 跨修法交叠一次成文;本稿引用不重复定义)机械清零,逐站点目标文本见 §2.2;失效 `screen_op.md §7` 换持久索引 `screens/README.md §3`。同屏正本 `screens/box_pick.md` 内同型残留(§2「pick-op-unify 批」、§4 伪码块「[bug#1 缓解]」会话局部缺陷编号)随本稿 box_pick.md 修法(F-1/F-5 同文件施工)一并清出。
- **明确不解决**:`cw_overlay_pick_action.py` 的「pick-op-unify 批」等注释残留(全文件卫生执行权 = T-6 稿 `invest_strategy.md` §2.5 已认领,本稿不触,归口对账随 T-37);`flow/action_ops.md` §4.5 PickBoxCard 行内批名/任务号标签(正本文档面,归正本维护批,T-37 对账);全仓注释卫生与增量防线(建议另立批,T-3 §2.6 已登记);CARD_Y 注的「2026-08-14 实测」日期(语义化实证出处,报告检查⑧在册合规判例,保留);模块头链路/决策分层/fail-closed 判据语义本体(与正本一致,只清史述保留语义)。

### F-3 DEFAULT_GS_SCHEMA 域键 'box_card_opts' 与在册字段 box_card_names 错位(低)

- **现状症状**:`kernel/cw_game_state.py::DEFAULT_GS_SCHEMA`(:185)域键 `'box_card_opts'`,同文件字段定义(:2187)= `box_card_names: Field[list[str] | None]`;同域另一登记表 `_PAYLOAD_DOMAINS`(:232)键 = `'box_card_names'`。同区块单字段域键全部与字段名逐一对应(megastar_opts/partner_opts/planner_opts/star_tome_opts/wish_trial_opts/fortune_opts/expert_invite/equip_pick_opts,:180-188 对照字段 :2182-2192),唯一合并标签先例 = `invest_opts` 辖两字段(invest_strategy_opts/invest_env_opts);`'box_card_opts'` 辖恰一字段却与字段名不一致,且按字段名全仓无同名键(字面消费 = 定义点 + 测试断言,§2.3 ⑤)。按域版本映射语义「缺域键 = 该域未建模」(fields.md §3.7.1),按字段名检索 schema 时武装箱候选域呈「未建模」,与 fields.md §3.4 候选域清单在册(box_card_names)自相矛盾——疑为字段定名时的登记残留。
- **根因归层**:表示层(schema 域键登记面与字段名脱同步):登记残留,零行为影响。
- **解决到哪**:域键统一为 `'box_card_names'`(:185 一行)+ 唯一测试消费点同步(`sr-od-test/test/sr_od/application/currency_war/test_cw_route_clear.py::test_terminal_contract_schema_and_match_shape` 断言键 :121);容器读写双方评估与判定依据见 §2.3。
- **明确不解决**:schema 版本机制与域版本 bump 政策本体(本改动非域增删、非字段语义变更,不 bump,依据见 §2.3);遥测历史数据跨版本键名对比(gs_schema 随容器遥测透传的标签值变化,由落地 commit message 申报知悉);`cw_game_state.py` :2178-2179/:2188-2189 与 `cw_strategy.py` :208-210 的迭代件引用禁形残留(同库注释卫生,归全仓注释卫生批,F-3 仅动 :185 一行及其测试消费点);`test_cw_route_clear.py` :141「landing §3.2」/:142「终态契约 §A」(同文件未点名测试的同型迭代件指向,在 (b)/(c) 施工面之外,归全仓注释卫生批);`box_card_names` 字段本体、写端 `report_screen_box_pick_obs` 与 fields.md 在册表述(一致面,零触)。

### F-4 _read_card_names 参数缺类型注解(低)

- **现状症状**:`operations/cw_screen/cw_screen_box_pick.py::_read_card_names`(:136)参数 `screen` 无类型注解(同文件其余签名均合规;返回注解在册)。
- **根因归层**:约定层——AGENTS.md §7「所有函数签名、类成员变量都要有类型注解;使用 `list[str]`、`X | Y`」漏标。
- **解决到哪**:补 `screen: MatLike` 注解 + 对应 import(§2.4);与 F-2 同文件一次施工。
- **明确不解决**:同目录姊妹屏同型漏标(`cw_screen_equip_pick.py::_read_cards`/`cw_screen_fortune.py::_read_cards`/`cw_screen_bookcard.py::_read_card_factions` 等裸 `screen` 参数,同 grep 面在册)——归各屏审查稿/全仓注解卫生,本稿辖域仅本文件。

### F-5 box_pick.md §4 上报描述残留已退役的「发射相/落地相」两相词汇(低)

- **现状症状**:`screens/box_pick.md` §4 对照表上报列「零写:发射相意图遥测,容器零写;无落地相——落地归下一帧观察覆盖」。行为申报与代码一致(零写占位上报、真值归下一帧观察),但「发射相/无落地相」是以已全域清偿的两相形态词汇描述现役单相零写上报;正本 `flow/action_ops.md` §4.5「上报形态 = 全族即时上报……发射/落地两相与证据闩形态已全域清偿,零重入裁决补写面,禁新增分步写法」及 PickBoxCard 行「同上形态」(= 零写自上报)、`kernel/cw_action_report/zero_writes.py::report_action_pick_box_card_param` docstring「武装箱选择上报:容器零写」,均不再用两相口径。
- **根因归层**:表示层(文档措辞残留)——即时上报统一迭代后正本篇局部未跟平。
- **解决到哪**:上报列改现役口径(§2.5 目标文本);行为本体零改动。
- **明确不解决**:零写占位上报形态本体(现役合规面,报告检查⑥ 在册);同文件其余上报表述(§2/§5「落地由下一帧观察覆盖」为在册现役口径,保留)。

### F-6 决策规格指针目标 13_pick_family.md §1 接口列旧参签名与零参契约不符(低)

- **现状症状**:`strategy-docs/13_pick_family.md` §1 逐接口规格表 E18 行接口列 `decide_box_card(names)`,与契约正本不符——`strategies/impl/cw_strategy.py::decide_box_card`(:204)abstract **零参**(docstring「候选读 `gs.box_card_names` 槽」)、`strategies/impl/flow.py`(:652)实现同型零参、`flow/README.md` §2.2 pick 族行「容器槽零参读(候选自各 `*_opts` 槽/payload 槽……)」;该表同列 8 个旧接口(supply/encounter/megastar/partner/planner/star_tome/wish_trial/box_card)均残留旧参签名,仅后补三接口(fortune/expert_invite/equip_pick)为 `()`。判据半(薄壳 → `pick_equipment`、fallback idx=0)与实现一致;实现零参无行为差。
- **根因归层**:语义层(规格文档签名列与契约演进脱同步)——签名列整列陈旧,属目标文档(策略侧)内容面。
- **解决到哪**:本稿登记该 game/strategy 侧指针修正诉求,归口 **T-37**(汇总任务;13 号篇在 strategy-docs,跨区修正不落本屏辖域),登记内容见 §2.6。
- **明确不解决**:签名列整列修正的实施与家族级计数对账(归 T-37);13 号篇其他内容面;box_pick.md 侧指针本身(§2/§9 所指「13_pick_family.md §1 E18」目标存在、判据半与实现一致,指针语义保持,零改动)。

### 已核对一致面

报告 §3 十项一致面(分发衔接/全形态申报/决策 fail-closed 三路/零容器写/观察上报/动作 op 行/as-built 主体/其余注释面/在册欠账/确认链零消费)核对通过,不立修法;正面结论在册:本屏决策出口无盲选回退——`decide_box_card` 异常留证上抛、越界索引 ValueError、两路均无内联打分/钳位/默认值续跑,空候选在观察侧两道闸即 round_fail 交回重派(T-16-r1.md §3.3)——pick 族决策出口家族模式(T-4-r1 F-1 同类面)未现于本屏。本稿全部修法不回退任何一致面。

## 2. 方案

### 2.1 F-1 修法:删除 box_pick.md 开放设计注整节

`screens/box_pick.md` 末节整节删除(`## 开放设计注` 标题 + 其下唯一一条 bullet);文件以 §9 收尾。

**判定依据(销项三证,就地标注)**:①`DISPATCH_AREA_ANCHORS` 全 src grep 零命中(仅 box_pick.md 本条与一处 changes/ 迭代工件残留引用,报告 F-1 差距说明);②现役预检 = `cw_loop.py::_dispatch_anchor_precheck`(:788,loop 主入口 :1658 调用)遍历 `CW_DISPATCH_SCREENS`(:775),条件 = 画面档存在 ∧ 有 id_mark 锚;③本屏两条件现值满足——「货币战争-备战-武装箱选择」在册清单(:779)、建档「标识-请选择」`id_mark: true`(currency_war_battle_prep_supply_box.yml)。候裁事项已闭合 = 非开放问题,按 screens/README.md §2「as-built 无状态」删除,不改写为「已闭合」注(改写 = 状态位残留,同条纪律所禁)。

**取舍**:备选 = 改写注为现值申报(「已登记 `CW_DISPATCH_SCREENS`,预检条件满足」)——放弃:预检机制属外循环域,screens/README.md §2 纪律明定「分发判定不复制外循环表」且 README 卷首与 §2 模板第 1 节已指 `flow/outer_loop.md` §2.2 单一源,正本篇留机制现值快照 = 第二抄本必漂移;删除后无信息丢失(预检覆盖语义由 outer_loop 侧承载)。

### 2.2 F-2 修法:cw_screen_box_pick.py 注释卫生 + box_pick.md 同批残留清出

清理准则 = T-3 稿 `battle_wait.md` §2.6 五条(本稿不重立);验证门 = T-3 稿 §2.6「验证门(双门)」条款,本稿 §2.7 收敛为两文件的实施形态。与 F-4 同文件一次施工(准则5 一次成文);`screens/box_pick.md` 的同批命中与 F-1/F-5 同文件一次施工。

**(a)模块 docstring 整段替换**(命中站点 :1/:3-6/:8-10/:16-17/:20/:23/:32-34/:36-37 一体改写;目标全文如下,替换现 :1-39 整段——逐句均为现役真值,出处随句标注):

```python
"""货币战争 备战-武装箱选择 四选一画面 op。

武装箱 4 选 1 的访问面 = **独立建档画面**「货币战争-备战-武装箱选择」,
外循环阶段一身份分发进本 op(分发判定单一源 = ``flow/outer_loop.md``
§2.2);武装箱选卡不属备战动作词表(单选族例外:选卡即终结,判据 =
``screens/README.md`` §3)。链路:备战环 ``CwActionOpenBoxParam`` 点开启
(**终结化**——开箱即交回)→ 外循环按本画面分发本 op → OCR 卡名 →
选卡决策(局内策略 ``decide_box_card`` 契约面,局外 kernel
``pick_equipment`` 机器单一源)→ 点卡 → 固定动画等待 →
**选卡即终结交回**(选卡落地由下一帧观察覆盖)。

决策分层纪律:打分只住机器——策略契约 ``decide_box_card``
(``strategies/impl/cw_strategy.py`` abstract 零参 + ``strategies/impl/flow.py``
实现)与 kernel 机器 ``pick_equipment``(``kernel/cw_equip_value.py``)
是仅有的两处决策面,本 op 禁第二打分实现;``decide_box_card`` 异常留证
(完整栈)后显式上抛、返回越界索引同 fail-closed 上抛——两者都禁无声
回落内联打分(策略 bug 禁遮蔽;正本 = ``flow/README.md`` §1 决策控制
分层铁律 + ``screens/op-layer.md`` §1.1 出口三语义)。局外回落行为 =
机器空键纯通用输出先验排序(与局内未锁态同构)。

单选族交互(实机实测口径):点卡选中即确认(单步,无独立确认钮);
点卡名带下方一点(y=290,避「查看详情」按钮)。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation):
观察 node = 入口锚复验(「标识-请选择」,分发即门,op 内机械复验防误派;
miss 未发 = round_fail 交回外循环按画面重分发)+ OCR 卡名行读数(2-8 字
过滤,x 升序;空 = 变体字型/动画帧读缺 = 未发出通道 round_fail 交回
外循环重派,禁盲点首卡兜底——选错不可逆,读数闸属观察处理)→
``CwScreenBoxPickObs`` → ``report_screen_box_pick_obs`` 写槽
``box_card_names`` 落容器(「写槽以本访问将决策为前提」由门 + 非空闸
保证,桩无 gs → 跳过写、决策照走)→ obs 与原始读数(x 坐标对)挂实例
属性进决策动作 node。决策动作 node = 选卡决策(``_decide_card_index``,
fail-closed 契约)→ 选卡链经 ``CwActionPickBoxCardOp`` 派发(点卡选中即
确认 + 动画等待 + 自上报住动作 op,机械链契约 = ``flow/action_exec.md``
§2)→ 选卡即终结交回(单选族例外,判据 = ``screens/README.md`` §3;
选卡落地由下一帧观察覆盖,无重入裁决旗标)。
"""
```

删除内容的判定:①「R7/批 2a/design.md §2.6-R7/2026-09-12 应修②」= 会话局部编号与无路径迭代件引用(准则1;fail-closed 语义改指正本 `flow/README.md` §1 + `op-layer.md` §1.1 出口③);②「此前选卡以备战动作承载……错挂画面归属。批 2a 起形态」「全链删除(词表类/发射点/……)」「自原 `PrepActionExecutor._default_box_card` 原位平移,……不搬家」「原决策半内联写点收编」「决策半原位消费,失败契约不变」「迁入动作 op」= 变更史/平移叙事(准则2),其中旧发射点的考古申报已在册于 `strategies/impl/mandate_v1/entry.py`(prep_box_pick 臂退役申报,报告 §3.1 检查①),本处无重复史注价值(准则4);③「词表类全链删除」句与现值矛盾(词表类 `CwActionPickBoxCardParam` 在役 = `kernel/cw_vocab.py` 词表 + 注册表行 + act 派发构造,报告检查⑥)——保留会向读者申报假现状,必删;④`screen_op.md §7` ×2 → `screens/README.md §3`(单选族例外判据在册节);⑤「pick-op-unify 批」→ 机械链契约改指 `flow/action_exec.md` §2;⑥「实测口径,原执行器注释存档」→「实机实测口径」(实证出处纯语义,准则3)。

**(b)类体与方法注释站点表**(准则命中即改写;行号定位辅助):

| 站点 | 现文(节选) | 目标文本 |
|---|---|---|
| 类 docstring(:61) | 「(选卡即终结;单选族例外,screen_op.md §7)。」 | 「(选卡即终结;单选族例外,判据 = screens/README.md §3)。」 |
| act docstring(:114-116) | 「pick-op-unify 批:点卡选中即确认 + 动画等待迁入 ``CwActionPickBoxCardOp``……本 op 只决策(fail-closed 契约不变)与交回。」 | 「点卡选中即确认 + 动画等待 + 自上报住 ``CwActionPickBoxCardOp``(机械链契约 = flow/action_exec.md §2)……本 op 只决策(fail-closed 契约)与交回。」 |
| CARD_Y 注(:64-65) | 「……;2026-08-14 实测,自原执行器 CARD_Y 常量平移)」 | 「……;2026-08-14 实测)」——实测日期保留(报告检查⑧在册合规判例),平移史删(准则2) |
| observe docstring(:80) | 「两道闸(现役单 node 首闸/读数闸逐位平移):」 | 「两道闸(入口锚/读数,均在观察 node):」 |
| observe 写槽注(:102-104) | 「写槽原位调用(原决策半内联写点收编:同访问覆盖写,……」 | 「写槽调用(report 落容器:同访问覆盖写,……」——其余语义逐字保留 |
| `_decide_card_index` docstring(:149-150) | 「决策面原位消费,不搬家;写槽半已收编至观察 node 的 report 调用,本方法只决策」 | 「容器写归观察 node 的 ``report_screen_box_pick_obs`` 调用,本方法只决策」 |

**(c)box_pick.md 同批残留**(与 2.1/2.5 同文件一次施工):

| 站点 | 现文(节选) | 目标文本 |
|---|---|---|
| §2 形态声明 | 「派发(点卡选中即确认 + 动画等待迁入动作 op,pick-op-unify 批)」 | 「派发(点卡选中即确认 + 动画等待 + 自上报住动作 op,契约 = [../flow/action_exec.md](../flow/action_exec.md) §2)」 |
| §4 伪码块 | 「target mouse_move + click [bug#1 缓解]→」 | 「target mouse_move + click →」——「[bug#1 缓解]」= 会话局部缺陷编号(准则1);mouse_move+click 机械事实保留(action_ops.md §4.5 机械链口径) |

**跨稿分歧登记(候 T-37 裁决)**:本稿对「pick-op-unify 批」「[bug#1 缓解]」两标记取**清出派**——判据 = 本屏报告 F-2 可解析性核(两标记在 changes/ 目录 glob 零命中;box_pick.md 为正本,AGENTS §9 禁引迭代件)。族级在册分歧:「bug#1 缓解」标签 = T-7 稿(invest_env.md §2.5 表行)判裸缺陷件编号清出 / T-11 稿(partner.md,保留判 + 目标文本在册)、T-13 稿(wish_trial.md §2.4 跨稿分歧登记)判跨文件在册交互陷阱标签保留;「pick-op-unify 批」泛化批名 = T-9/T-12/T-13 稿与 supply_node.md §2.7 收敛判据(encounter.md §2.3 保留面同口径)判出处标签保留(非过程件指针)。两标记处置随 T-37 裁决同向修订(本稿辖内站点 = §2.2(a) 删除判定⑤/(b) act docstring 行/(c) 表两行),裁决前本稿按清出派施工。

**取舍**:范围 = 报告点名点位 + 准则全文件扫描兜底(T-3 §2.6 同款:「准则做全文件扫描,点名表为已核对点位、非穷举」),不做跨文件外推(cw_overlay_pick_action.py 执行权 = T-6 稿,action_ops.md = 正本维护面,均登记不触)。失效指针的替换目标选 `screens/README.md §3` 而非 `op-layer.md §3`:两者同判据,README §3 为 screens/ 目录内单选族例外的分类正本(与被引的「screen_op.md §7」同域),op-layer §3 作并列依据随文保留。

### 2.3 F-3 修法:schema 域键统一为 'box_card_names'

**(a)定义点**:`kernel/cw_game_state.py::DEFAULT_GS_SCHEMA` :185 一行——

```python
'box_card_names': 1,       # 武装箱候选槽(str)
```

(仅键名变化;注释与姊妹行同款保留;对齐缩进按现文件排版。)

**(b)测试消费点同步**(同断言块四处一次成文,准则5):①`test_terminal_contract_schema_and_match_shape` :121 断言元组 `'box_card_opts'` → `'box_card_names'`;②:119 计数注「# 八新域键在册」→「# 七新域键在册(终态契约八新槽,invest_opts 辖两字段)」——该循环实为 7 键(invest_opts 合并两字段),既有计数失注与 :121 改键同段随批修;③:130 注释「十二槽:8 新槽(7 opts + box_card_names 经 getattr 同名域字段)在容器上可解析(声明健康性)」→「十二槽:8 新槽(经 getattr 同名域字段在容器上可解析(声明健康性);box_card_names 的 schema 键与字段同名,invest 两槽属合并域 'invest_opts' 显式例外)」——目标文本按字段口径断言 getattr 可解析性(对 8 槽全真),不把「schema 键与域字段同名」写作全称断言(invest 两槽经合并标签在册,第一循环 :120-122 本身就以合并键断言,全称断言对其中 2 槽为假);措辞当前时态,勘误过程词不入持久注释(AGENTS §8 / T-3 §2.6 准则2;测试文件在门一/门二扫描面外,无门可拦,目标文本自净);④同测试 docstring(:102-103)「(landing §3.1 判据:8 新域键 + …)」删除迭代件指向(AGENTS §9 禁引 changes/,判据语义已在本测试内自足),其中「8 新域键」计数随 :119 同步为「七新域键(终态契约八新槽,invest_opts 辖两字段)」——与 :119 同源失注,不清则修后 :119 注与 docstring 直接互相矛盾(同块一次成文)。

**(c)随批新增对齐防线锁**(同文件,增于 `test_terminal_contract_schema_and_match_shape` 之后):现行测试无任何 schema 键 ↔ 字段名对齐断言(仅点键值与容器可解析性),错位残留得以长期存活正因无校验——修实例同时补该缺口,目标形态:

```python
def test_single_field_slot_schema_keys_align_with_field_names():
    """schema 域键 ↔ 槽字段名同名对齐(登记漂移防线)。正向辖域 =
    九个在册单字段槽域键(非 ``_opts`` 后缀成员 = box_card_names/
    expert_invite)双向同名断言(域键在册 ∧ 字段在册);反向辖域 =
    ``_opts`` 型域键(除 invest_opts 合并标签)必须为字段名。组域
    语义域名键(node/units/economy 等)无 ``_opts`` 后缀天然不入;
    invest_opts 为唯一显式豁免。新增槽域须同步扩正向清单。"""
    from dataclasses import fields

    from sr_od.application.currency_war.kernel.cw_game_state import (
        DEFAULT_GS_SCHEMA,
        GameState,
    )
    single_field_slots = (
        'megastar_opts', 'partner_opts', 'planner_opts',
        'star_tome_opts', 'wish_trial_opts', 'box_card_names',
        'fortune_opts', 'expert_invite', 'equip_pick_opts',
    )
    field_names = {f.name for f in fields(GameState)}
    for name in single_field_slots:
        assert name in DEFAULT_GS_SCHEMA, name
        assert name in field_names, name
    for key in DEFAULT_GS_SCHEMA:
        if key.endswith('_opts') and key != 'invest_opts':
            assert key in field_names, key
```

正向 = 在册九槽封闭清单双向同名断言(域键在册 ∧ 字段在册——原病「字段在、键错名」与其镜像「字段改名、键留存」均即红;新增槽域须同步扩清单,不自动受锁);反向 = `_opts` 型域键不得指向不存在字段(防孤儿键);组域键不以 `_opts` 结尾天然不入反向扫描,invest_opts 为唯一显式豁免。

**判定依据(改键名,就地标注)**:①命名一致性——同区块八个单字段域键全部 = 字段名(cw_game_state.py :180-188 ↔ :2182-2192),唯一合并标签先例 `invest_opts` 辖两字段(:2180-2181),本域辖恰一字段无合并需求;②检索语义——「缺域键 = 该域未建模」(fields.md §3.7.1 + cw_game_state.py :152-153),键名错位使按字段名检索呈「未建模」,与 fields.md §3.4 候选域清单(「box_card_names(武装箱选卡)」)自相矛盾,改注无法修复该检索语义;③同域对齐锚——`_PAYLOAD_DOMAINS` 同域键已是 `'box_card_names'`(:232),两登记表同域同键;④**写端评估**:`gs_schema` 字段 default = `dict(DEFAULT_GS_SCHEMA)`(cw_game_state.py :2278-2279),改键自动生效,字段 `box_card_names` 本体与写端 `report_screen_box_pick_obs` 零改动;⑤**读端评估**:`src/`、`sr-od-test/`、`tools/` 扫描面字面消费仅两处 = 定义点 :185 + 测试断言 test_cw_route_clear.py :121(grep 核);生产读端 = 遥测透传 `'gs_schema': dict(gs.gs_schema)`(:1293)与快照(:2459)的整 dict 拷贝,零按字段名取键——改键零行为影响;⑥版本语义——域版本 bump 条件 = 「域增删或字段语义破坏性变更」(:152-153),本改动 = 登记标签纠偏(域前后同域、字段语义零变化),**保持 1 不 bump**。

**取舍**:备选 = 改注方案(保留 `'box_card_opts'` 键 + 注释声明「辖 box_card_names 字段」)——放弃:①检索语义破口仍在(按字段名 grep schema 仍呈未建模);②唯一错位需唯一特例注释 = 长期税;③键名统一 = 让 schema 表的单字段 opts 型槽域键回归「域键 = 字段名」不变式(invest_opts 合并标签显式例外;组域键 node/units/economy 等为语义域名、无字段名同名事实,本就不入该对齐面)——该不变式以 §2.3(c) 对齐锁承载,同病复发即红,弃改注方案所换来的可校验性由此有落地载体。遥测标签值变化的知悉义务由落地 commit message 申报,不进注释(变更史不进注释,AGENTS §8)。

### 2.4 F-4 修法:_read_card_names 参数补类型注解

```python
def _read_card_names(self, screen: MatLike) -> list[tuple[str, int]]:
```

顶部 import 区新增 `from cv2.typing import MatLike`。

**依据**:注解型选 `MatLike` = 直通下游 `_ocr(ctx, screen: MatLike, rect)` 入参同型(`kernel/cw_obs_core.py` :85)且与调用实参 `self.last_screenshot`(观察 node 门后非空帧)匹配;同目录在册先例 = `cw_screen_invest_strategy.py::_entry_anchor_hit(self, screen: MatLike)` 与各弹窗屏 `entry_ok(self, screen: MatLike | None)`。不用 `Any`:obs 类的 `screen: Any` 是「稳定帧引用」载荷字段口径(op-layer.md §2.1),读链参数口径以 `MatLike` 为准,两者分工在册不混用。与 F-2 同文件一次施工;零行为变化(仅注解)。

### 2.5 F-5 修法:box_pick.md §4 上报列改现役口径

§4 对照表上报列目标文本:

```
自上报 `report_action_pick_box_card_param`(零写占位上报,容器零写;选择落地真值归下一帧观察覆盖)
```

**依据**:现役口径词 = 「零写占位上报」(op-layer.md §3 注:「其余屏 = 零写占位上报」)+ 「落地归下一帧观察覆盖」(本篇 §2/§5 与 README 卷首术语注在册同款);正本禁两相口径 = action_ops.md §1 增补 2(选择动作点完立即按成功上报)+ §4.5(「发射/落地两相与证据闩形态已全域清偿……禁新增分步写法」;PickBoxCard 行「同上形态」);kernel 现值 = `zero_writes.py::report_action_pick_box_card_param`「武装箱选择上报:容器零写」。行为申报不变(仍申报零写与下一帧观察覆盖),仅词汇换现役口径。

### 2.6 F-6 登记:决策规格目标签名列修正诉求(归口 T-37,本稿不实施)

**登记内容**(交 T-37 汇总对账):`strategy-docs/13_pick_family.md` §1 逐接口规格表**接口列签名整列更新为现役零参形态**——E18 行 `decide_box_card(names)` → `decide_box_card()`;报告差距说明在册同列其余 7 行(supply/encounter/megastar/partner/planner/star_tome/wish_trial)同病,整列一次成文、家族级计数对账归 T-37(本稿只登记 box-pick 相关行证据,不固化成员数)。

**判定依据**:契约正本 = `cw_strategy.py:204` abstract 零参 + `flow.py:652` 实现同型 + `flow/README.md` §2.2 pick 族行「容器槽零参读」;候选真源 = `gs.box_card_names` 槽(写端 = `report_screen_box_pick_obs`,fields.md §3.4)。

**归口理由**:13 号篇在 `strategy-docs/`(game/strategy 侧文档区),跨区修正不在画面篇审查稿辖域内实施;本稿辖内(`screens/box_pick.md` §2/§9 的「13_pick_family.md §1 E18」指针)零改动——指针目标存在、判据半与实现一致(报告 §3.2),指针语义保持。

### 2.7 实施文件面全集与验证门

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `screens/box_pick.md` | 末节「开放设计注」整节删(F-1);§2/§4 同批残留清出(F-2);§4 上报列现役口径(F-5) | 正本文档修正 |
| `operations/cw_screen/cw_screen_box_pick.py` | 模块/类/方法 docstring 与行内注卫生(F-2);`_read_card_names` 签名注解 + import(F-4) | 注释 + 签名注解 |
| `kernel/cw_game_state.py` | `DEFAULT_GS_SCHEMA` :185 键名一行(F-3) | 登记面 |
| `sr-od-test/test/sr_od/application/currency_war/test_cw_route_clear.py` | 断言键同步 + :119/:130 注释随批修 + docstring 迭代件指向删(F-3(b));新增对齐防线锁(F-3(c)) | 测试同步 + 防线 |
| (登记面,不实施)`strategy-docs/13_pick_family.md` §1 接口列 | 签名列整列零参化(F-6) | 归口 T-37 |

**验证门**(实施批执行;设计批不落码不跑):

1. 门一·模式 grep:`cw_screen_box_pick.py` 与 `screens/box_pick.md` 对禁形模式(`screen_op\.md|R7|批 ?2a|pick-op-unify|bug#\d|2026-09-12|design\.md §` 及 T-3 §2.6 门一全模式)零命中;豁免 = CARD_Y 注「2026-08-14 实测」(语义化实证出处,检查⑧在册合规判例)。`'box_card_opts'` 于扫描根 `src/` 与 `sr-od-test/` 零命中——changes/ 论证文本与本稿自身、`.debug/` 历史进度件豁免(字面在两处必然残留,不作扫描对象;口径与 §2.3 ⑤ 消费面调查一致)。
2. 门二·人工复查:两文件全注释段按 AGENTS §8 两禁形人工判(模式不可判形态);`screens/box_pick.md` 修后九节结构与 screens/README.md §2 模板对齐(§9 收尾、无状态节残留)。
3. 收尾:`uv run ruff check` 两 .py 文件通过;`git diff` 确认生产代码零逻辑改动(代码面:F-3 仅常量行,F-4 仅注解;测试面 = 断言键同步 + 注释 + 新增锁一条);`test_cw_route_clear.py::test_terminal_contract_schema_and_match_shape` 与 `test_cw_route_clear.py::test_single_field_slot_schema_keys_align_with_field_names`(新增)及 `test_cw_screen_progression_inline.py`/`test_cw_screen_report_ports.py` box_pick 相关锁全绿(一致面不回退的凭据)。

## 3. 新规范增补(2026-09-22 两条款)

> **背景**:正本 `screens/op-layer.md` §1.1 新入两条款(commit 2f35d4011,用户裁定 2026-09-22)——**条款①观察标准化门**(:34)/ **条款②画面 op 不支持局外单独调用**(:36)。新规范符合性重审(G2)= `.debug/progress/2026-09-22-cw-screen-review/reports/respec-T16-T25.md` §2「T-16 武装箱选卡」节,总判定 = **需增补 2 点**(条款②局外出口清偿 = 行为级,本组唯一现役正面违例 + 设计稿正面保留;条款①卡名域欠账登记)。本节只追加,不改 §0-§2 任何已收敛内容;既有修法(F-1..F-6)全部维持。
>
> **时点差与辖域申报**:§2.2(a) 目标 docstring 的局外回落申报成文早于两条款入正本,属时点差非有意违范;收敛稿必须对齐——**§2 原文与本节冲突处,以本节为准**(落地批按「§2 目标文本 + §3.3 站点表套改」施工,不存在两份竞争的整段目标文本)。§0「修法性质:生产代码零行为变化」辖 F-1..F-6 修法面;增补 1 为行为级(局外路径行为变化),两申报并行不悖(辖域不同)。

### 3.1 增补 1(条款②·行为级):`_decide_card_index` 局外臂清偿,局外出口 = 零决策零点击 round_success 终结交回

**违例认定(依据就地标注)**:

- 代码锚:`operations/cw_screen/cw_screen_box_pick.py::_decide_card_index`(:148-173)——`match = self.ctx.cw_match`;`match is None` → `kernel/cw_equip_value.pick_equipment(names)` 机器决策返回 idx(:168-173),act(:118-134)照常组点点击选卡。局外 = **有决策(kernel 机器)+ 有点击** = 条款②明令「不设任何兜底决策路径」的兜底决策路径,且属「支持脱离对局(`cw_match` 缺席)单独调用选卡」的支持代码(条款②:「此类支持代码不做」)。
- 设计稿冲突(逐字级):§2.2(a) 目标 docstring 两处正面保留局外回落——①链路句「选卡决策(局内策略 ``decide_box_card`` 契约面,局外 kernel ``pick_equipment`` 机器单一源)」;②决策分层段尾「局外回落行为 = 机器空键纯通用输出先验排序(与局内未锁态同构)。」——连带改写目标文本见 §3.3 表 #1/#2。
- 规范出口 = 遭遇屏在册先例:`cw_screen_encounter.py::act`(:156-165)`match is None` → 零点击 `round_success` 终结交回;条款②正文字面「无 match(局外)= 零决策零点击 round_success 终结交回(遭遇屏在册先例同款),不设任何兜底决策路径」。

**修法(目标文本逐字给足)**:

(a)**act 顶部新增局外门**(插于 act 体首行、`idx = self._decide_card_index(...)` 之前;门住 act 而非 `_decide_card_index` 入口 = round_success 交回语义只能由 node 方法承载,`_decide_card_index` 返 int 无法终结,且与遭遇屏先例同位同式;`self.ctx.cw_match` 直读与现役/先例同款):

```python
        match = self.ctx.cw_match
        if match is None:
            # 局外(无对局)= 零决策零点击 round_success 终结交回
            # (op-layer.md §1.1「画面 op 不支持局外单独调用」;遭遇屏
            # 先例同款,禁兜底决策路径)。观察 node 的 report 已因 gs
            # 缺席跳过、容器零写;外循环重进 = 重观察重派。
            log.info('[cw][boxpick] 局外(无对局)→ 零决策零点击终结交回')
            return self.round_success('局外(无对局),零决策零点击终结交回',
                                      wait=1.5)
```

(b)**`_decide_card_index` 删局外臂、改局内专用**(目标全文,替换现 :148-173;act 门保证进入时 match 非 None,方法内不再设 match 分支——分支即兜底形态;方法内对 `pick_equipment` 的局部 import 随臂删除):

```python
    def _decide_card_index(self, names: list[str]) -> int:
        """选卡决策(局内专用;容器写归观察 node 的
        ``report_screen_box_pick_obs`` 调用,本方法只决策):策略契约
        ``decide_box_card``(fail-closed:异常留证上抛/越界上抛,禁
        无声回落)。局外出口住 act 顶部(零决策零点击终结交回),本
        方法无兜底臂(op-layer.md §1.1 局外单跑条款;遭遇屏先例同款)。"""
        try:
            idx = self.ctx.cw_match.strategy.decide_box_card().idx
        except Exception:   # noqa: BLE001  留证后显式上抛,禁无声回落
            import traceback

            log.error('[cw!][boxpick] decide_box_card 异常(留证后上抛):\n%s',
                      traceback.format_exc())
            raise
        if not (0 <= idx < len(names)):
            raise ValueError(
                f'decide_box_card 返回越界索引 {idx}(实读卡数 '
                f'{len(names)});策略契约违约 fail-closed,禁回落内联选卡')
        return idx
```

(c)**测试对账**(重审增补点 B3):

- `test_cw_unified_action_2a.py::test_pick_box_decision_fail_closed`(:534-554):锁局内 fail-closed(ctx 挂 match 走策略契约),删局外臂后行为不变——**不受影响,不改**。
- `test_cw_screen_progression_inline.py` `_make_box_pick`(:336-352)恒挂 match,现役三把 box_pick 锁(观察上报接线/两道闸 skip report/点卡决策)全走局内臂——**不受影响,不改**。
- 全测试仓排查(grep 核):`sr-od-test/` 对 `pick_equipment`/「机器空键」零命中——**无锁「局外走机器」的既有断言,无需翻转**。
- 随批新增局外出口锁一条(防线,防兜底决策回潮;落 `test_cw_screen_progression_inline.py` box_pick 段,目标形态逐字):

```python
def test_box_pick_act_off_match_terminates_without_click(test_context,
                                                         monkeypatch):
    """局外出口锁:match 缺席(局外)= 零决策零点击 round_success 终结
    交回(op-layer.md §1.1「画面 op 不支持局外单独调用」;遭遇屏先例
    同款),观察 report 跳过容器零写、act 零派发。红 = 兜底决策路径
    回潮(局外调机器决策/发点击/写容器)。"""
    op, session = _make_box_pick(test_context, monkeypatch, gate_ok=True,
                                 cards=list(_CARDS))
    monkeypatch.setattr(test_context, 'cw_match', None, raising=False)
    _run_node(test_context, op, op.observe)   # 局外观察:report 跳过,obs 照常装载
    dispatched: list = []

    class _SpyPickOp:
        def __init__(self, param, env) -> None:
            dispatched.append(self)

        def execute(self) -> bool:
            return True

    import sr_od.application.currency_war.operations.cw_op.cw_action_registry as _reg
    monkeypatch.setattr(_reg, 'action_op_for',
                        lambda act, ctx, env: _SpyPickOp(act, env))
    rs = _run_node(test_context, op, op.act)
    assert rs.is_success and '局外' in (rs.status or ''), (
        f'局外零决策零点击终结交回:{rs!r}')
    assert dispatched == [], '零派发(局外禁选卡动作)'
    assert game_state_of(session).box_card_names.value is None, '容器零写'
```

(d)**验收锚(增补 1)**:

1. grep `pick_equipment` 于 `operations/cw_screen/cw_screen_box_pick.py` 全文零命中;`kernel/cw_equip_value.py`(机器本体)与 `strategies/impl/flow.py`(:652-699 `decide_box_card` 薄壳,内部 :694-696 消费 `pick_equipment` = 策略器自限域,合法)**零改动**。
2. `_decide_card_index` 全函数无 match-None 分支(唯一决策面 = 策略契约);act 体首个分支 = 局外门;新增读屏点为零。
3. 测试全绿:`test_pick_box_decision_fail_closed` + progression inline 三把 box_pick 锁 + (c) 新增局外出口锁。
4. `kernel/cw_screen_report/box_pick.py`(report 写端)零改动——局外 report 跳过由 observe 既有 gs 门承载,不动。

### 3.2 增补 2(条款①·登记级):卡名域标准化欠账登记 + 重复名附加边界

**欠账认定(依据就地标注)**:

- 观察链 = `_read_card_names`(:136-146,「区域-卡名行」rect OCR,2-8 字过滤、x 升序)→ `CwScreenBoxPickObs.card_names` → `report_screen_box_pick_obs`(`kernel/cw_screen_report/box_pick.py` :48)对 `gs.box_card_names` 直写——**零形变归一、零 LCS、零注册表比对**,即条款①「观察 node 必须在观察时把读数转换成标准注册数据再上报」未达成;定性 = 存量欠账(条款①:「其余名字类观察屏为欠账,逐批收敛,禁新增未标准化直报」),非本批违例。
- 所属域标准注册数据在册(条款①辖面成立):装备全量注册表 `data/cw_equipment_data.py::EQUIPMENTS`(158 件;`EQUIPMENT_ROSTER` = 键集 frozenset)+ 序数分档/先验值面 `kernel/cw_equip_value.py`(`EQUIP_GENERIC_VALUE` 键 ⊆ EQUIPMENT_ROSTER,ADR-0298 在册)+ 识别库 `obs/cw_equipment.py`(手维护 TM 分类)。
- 动作侧已合规(零触):选卡上报 = `CwActionPickBoxCardParam(idx=idx)`(act :128)只带序号、零名字转换,符合条款①「动作上报只携带选择序号(idx)」。
- 失败语义现状:仅覆盖「读空」(observe :91-94 卡名空 = round_fail 零写零上报交回重派,与条款①失败语义同型);「读出但转换失败」路径随收敛批补齐(现无转换故缺)。
- 决策消费随欠账:`decide_box_card` 读 `gs.box_card_names` 槽打分(`strategies/impl/flow.py` :652-699),标准化前消费 OCR 原名——「下游全链只在标准名上工作」随收敛批达成,不另立修法。

**修法 = 登记欠账(本稿不实施;归后续标准化收敛批,与投资环境落地批同族;收敛批一次性做齐,禁半截状态)**:

1. **两段转换**:形变归一(OCR 形变族)后精确命中 `EQUIPMENT_ROSTER` → 不中再 `one_dragon.utils.str_utils::find_best_match_by_lcs`(阈值常量住代码);同构参照 = 投资环境首个落地 `cw_screen_invest_env.py::_standardize_options`(:138-162)。转换住观察侧(画面 op 观察 node,op-layer §2.2「生产半住观察侧」),落容器半照旧 `report_screen_box_pick_obs`。
2. **失败语义**:任一候选转换失败 = 观察失败——观察 node round_fail 早退、零写零上报、交外循环重观察重读(与「读空」闸同型并列;禁带病上报)。
3. **重复名附加边界(屏契约登记)**:武装箱四卡可能同名(同装备多张)→ 属条款①「重复名合法的观察面」,不适用「多候选命中同一注册名 = 转换失败」互斥判(该判辖选项互斥屏);转换按逐候选独立归一,容器 `box_card_names` 允许重复项,卡位序(x 升序)与选卡 idx 的对应关系不变。屏契约落点 = `screens/box_pick.md`(目标语义文本见 §3.3 表 #13,随收敛批施工)。
4. 动作侧与决策零参契约零触(已合规面,本批与收敛批均不改)。

**T-37 登记行原文**(逐字,交 T-37 汇总对账;载体同 §2.6 F-6 登记面):

> T-16 增补 2(条款①观察标准化门):武装箱选卡卡名域 = 标准化欠账在册——OCR 原名直写 `gs.box_card_names` 零转换(`_read_card_names` → `report_screen_box_pick_obs`;注册数据在册 = `data/cw_equipment_data.py::EQUIPMENTS` 158 件 + `kernel/cw_equip_value.py` 序数分档表 + `obs/cw_equipment.py` 识别库)。收敛批(与投资环境落地批同族,宿主稿 = box_pick.md §3.2)须做:观察读数 → 装备注册表两段转换(形变归一精确 → LCS `find_best_match_by_lcs`);任一候选转换失败 = 观察失败 round_fail 零写零上报交回重读;重复名附加边界(四卡可能同名,同装备多张)入 `screens/box_pick.md` 屏契约。动作侧已合规(`CwActionPickBoxCardParam` 只带 idx)零触;禁新增未标准化直报。

**验收锚(登记级)**:

1. 本节 + T-37 登记行在册(汇总清单可查),欠账认定有代码锚可复核。
2. 行为面零变化(本批):`gs.box_card_names` 写端唯一 = `report_screen_box_pick_obs`(`kernel/cw_screen_report/box_pick.py` :48)零改动;**本批不得出现半截转换或改名**(两段转换 + 失败语义 + 边界登记由收敛批一次性做齐)。
3. 收敛批开工入口 = 本节 §3.2 + T-37 登记行,不重做认定。

### 3.3 与既有修法的咬合申报(连带改写站点,逐字;落地批按「§2 原文 + 本表套改」施工)

本稿既有节需连带改写的站点全集如下(#1-#10、#14 = 本稿面;#11-#12 = 正本 `screens/box_pick.md` 随批面,该文件已在 F-1/F-2(c)/F-5 施工辖内,下列站点与既有修法站点跨距零重叠;#13 = 正本屏契约登记点,随收敛批;#14 = 定点攻击 F-4 增补):

| # | 宿主 | 站点现文(= §2 目标文本内原文) | 连带改写目标文本(逐字) | 缘由 |
|---|---|---|---|---|
| 1 | 本稿 §2.2(a) 链路句 | 「选卡决策(局内策略 ``decide_box_card`` 契约面,局外 kernel ``pick_equipment`` 机器单一源)」 | 「选卡决策(局内策略 ``decide_box_card`` 契约面;局外 = 零决策零点击 ``round_success`` 终结交回,op-layer.md §1.1 局外单跑条款、遭遇屏先例同款,禁兜底决策路径)」 | 增补 1:删局外正面保留 |
| 2 | 本稿 §2.2(a) 决策分层段尾句 | 「局外回落行为 = 机器空键纯通用输出先验排序(与局内未锁态同构)。」 | 「局外(无 match)= 零决策零点击 ``round_success`` 终结交回(op-layer.md §1.1「画面 op 不支持局外单独调用」;遭遇屏先例同款),本 op 不设任何兜底决策路径;``pick_equipment`` 打分单一源留守策略器 ``decide_box_card`` 消费(策略器自限域)。」 | 增补 1:删局外回落申报句,换条款口径 |
| 3 | 本稿 §2.2(a) 形态段观察句尾 | 「……禁盲点首卡兜底——选错不可逆,读数闸属观察处理)」 | 句尾补「(卡名域标准化欠账在册:读数待经装备注册表两段转换后上报,重复名附加边界随屏契约登记——见本文 §3.2;收敛前 OCR 原名直写为欠账形态,非终态)」 | 增补 2(重审增补点 A2:欠账指针短句,防重写后的模块头把未标准化直报申报为终态) |
| 4 | 本稿 §2.2(a) 形态段决策动作句 | 「决策动作 node = 选卡决策(``_decide_card_index``,fail-closed 契约)」 | 「决策动作 node = 局外门(match 缺席 = 零决策零点击 ``round_success`` 终结交回,见本文 §3.1)→ 选卡决策(``_decide_card_index`` 局内专用,fail-closed 契约)」 | 增补 1:形态段如实申报局外门 |
| 5 | 本稿 §2.2(b) act docstring 行目标文本尾句 | 「本 op 只决策(fail-closed 契约)与交回。」 | 「本 op 只决策(局内;fail-closed 契约)与交回;局外(match 缺席)= 零决策零点击 round_success 终结交回(op-layer.md §1.1 局外单跑条款,遭遇屏先例同款)。」 | 增补 1 |
| 6 | 本稿 §2.2(b) `_decide_card_index` docstring 行目标文本 | 「容器写归观察 node 的 ``report_screen_box_pick_obs`` 调用,本方法只决策」 | 「容器写归观察 node 的 ``report_screen_box_pick_obs`` 调用,本方法只决策(局内专用;局外出口住 act 顶部零决策零点击终结交回,本方法无兜底臂)」 | 增补 1 |
| 7 | 本稿 §2.7 文件面表 `cw_screen_box_pick.py` 行 | 修法点位列「模块/类/方法 docstring 与行内注卫生(F-2);`_read_card_names` 签名注解 + import(F-4)」;性质列「注释 + 签名注解」 | 修法点位追加「;`_decide_card_index` 局外臂删除 + act 顶部局外门(§3.1,行为级)」;性质列改「注释 + 签名注解 + 行为级局外出口」 | 增补 1 |
| 8 | 本稿 §2.7 文件面表(测试行后新增一行) | ——(现表无此行) | 新增表行逐字:「\| `sr-od-test/test/sr_od/application/currency_war/test_cw_screen_progression_inline.py` \| 新增局外出口锁 `test_box_pick_act_off_match_terminates_without_click`(§3.1(c)) \| 防线锁 \|」 | 增补 1 |
| 9 | 本稿 §2.7 验证门门一 | ——(现门一末句为 `'box_card_opts'` 扫描) | 门一末尾追加:「`pick_equipment` 于 `cw_screen_box_pick.py` 全文零命中(豁免:`kernel/cw_equip_value.py` 机器本体与 `strategies/impl/flow.py` 策略器消费面,零改动)。」 | 增补 1 |
| 10 | 本稿 §2.7 验证门门三收尾句 | 「`git diff` 确认生产代码零逻辑改动(代码面:F-3 仅常量行,F-4 仅注解;测试面 = 断言键同步 + 注释 + 新增锁一条)」;绿清单尾「……box_pick 相关锁全绿(一致面不回退的凭据)。」 | 前者括注后补「——辖域 = F-1..F-6;增补 1 局外出口为行为级变化,凭据 = §3.1(d) 验收锚」;绿清单尾追加「+ §3.1(c) 新增局外出口锁」。 | 增补 1 |
| 11 | 正本 `screens/box_pick.md` §2 决策句(随批) | 「局外防御 = kernel 机器空键纯通用排序」 | 「局外(match 缺席)= 零决策零点击 round_success 终结交回(op-layer.md §1.1 局外单跑条款,遭遇屏先例同款,无兜底决策)」 | 增补 1 行为级清偿后正本申报过时 |
| 12 | 正本 `screens/box_pick.md` §4 伪码块行(随批) | 「局外 = kernel pick_equipment(机器空键)」 | 「局外(match 缺席)= 零决策零点击 round_success 终结交回(op-layer.md §1.1 局外单跑条款;遭遇屏先例同款)」(缩进随伪码块同级行) | 同上 |
| 13 | 正本 `screens/box_pick.md` 观察面节(随收敛批,非本批) | §3 观察句 report 写槽句 | 补语义句(as-built 合法面,边界登记):「卡名读数经装备注册表两段转换后上报(转换失败 = 观察失败,round_fail 零写零上报交回重读);重复名合法(四卡可能同名,同装备多张),逐候选独立归一,不适用『多候选命中同一注册名 = 转换失败』互斥判。」 | 增补 2 屏契约登记(条款①「附加边界由屏契约登记」落点;收敛批施工,本批只登记诉求) |
| 14 | 本稿 §2.2(a) 形态段写槽括注(同句族经 §2.2(b) observe 写槽注行「其余语义逐字保留」落入现役代码注尾「桩无 gs → 跳过写,fail-closed 判据照走」) | §2.2(a):「(「写槽以本访问将决策为前提」由门 + 非空闸保证,桩无 gs → 跳过写、决策照走)」;§2.2(b) observe 写槽注行尾注:「——其余语义逐字保留」 | §2.2(a) 括注窄化为「(「写槽以本访问将决策为前提」由门 + 非空闸保证,桩无 gs(有 match)→ 跳过写、决策照走;局外(match 缺席)= act 局外门终结(本文 §3.1))」;§2.2(b) observe 写槽注行目标文本尾注同步改「——其余语义逐字保留,唯『桩无 gs → 跳过写、fail-closed 判据照走』句随 §2.2(a) 括注同步窄化为『桩无 gs(有 match)→ 跳过写、决策照走;局外(match 缺席)= act 局外门终结(本文 §3.1)』」 | 增补 1:match 缺席(= 无 gs 主局外态)在 act 局外门 round_success 终结,决策不走,「决策照走/判据照走」对该子态失真(落地后 docstring 与代码注将与行为自相矛盾) |

**一致面非冲突申报**:§1「已核对一致面」句「两路均无内联打分/钳位/默认值续跑」——增补 1 落地后局外路退役,该结论对存留的局内路继续成立;原文不回改(落地后按「局内单路」解读),不构成一致面回退。

## 4. 坐标规范增补(op-layer :35/:48)

> **增补依据**:正本 `screens/op-layer.md` 两条款(commit 9c8e9016b 入正本,用户裁定 2026-09-22)——**:35 选择坐标观察上报**(§1.1,全域行为规范:观察上报选项时,归一化标准名与选项坐标**一并**入 game state;归一化与坐标在同一次观察一并入容器;**坐标单一真相源 = 观察上报**——策略侧只输出下标,动作 op 按下标从 game state 取坐标执行;适用 = 商店与各需选择的 overlay;现役「决策半现算经 env 传入」= 逐批收敛辖面,**禁新增第二坐标源**)、**:48 每动作 op 单独一个文件**(§1.2:`operations/cw_op/cw_overlay_pick_action.py` 单文件同居 11 个动作 op(equip pick 已随选择装备屏退役后现值,正本 :48 已同步;coord-attack A-6 对账面)= 现役欠账,拆分逐批收敛,禁新增同类同居)。前置底册(字段骨架一次定谳 + 逐稿增补点清单)= `.debug/progress/2026-09-22-cw-screen-review/reports/coord-norm-addenda-plan.md`(下称**底册**;本稿增补输入 = 其 §2.4,字段骨架 = 其 §1——本稿引用不重复设计)。
> **本屏适用判定**:本屏 = 选卡 overlay(武装箱四选一),:35 辖面成立;现役坐标形态 = 「x 坐标不入容器,act 内 `Point` 现组装经 `env.target` 传入」(实查 `operations/cw_screen/cw_screen_box_pick.py` :72-73 注/:119-120/:127)= :35 所述「现役形态」实例,且「x 对留守本 op 不进容器」代码注 = :35 **反向政策**。字段宿主 = **A 类纯名单域伴随域**(底册 §1.3):`box_card_names_xy: Field[list[tuple[int, int]] | None]`(与名字域 `box_card_names` 同序等长;后缀随名字域本名,不强加 `_opts`)。底册 §4 建议逐屏收敛顺序本屏居首(现成 x 读数,改动最小)。
> **增补方式与辖域**:本稿 §0..§3 已收敛内容零直接改动;凡既有目标文本需连带改写处,逐字现文→改文在本节给出(含落点节号),待用户裁决后随落地批一次落笔;§0 状态行已就地更新。§0「修法性质:生产代码零行为变化」辖 F-1..F-6 修法面;本节坐标收敛为行为级增补批面(观察/act/动作 op 坐标链迁移),两申报并行不悖(先例 = 本文 §3 时点差与辖域申报)。本节与 §3.2 条款①标准化收敛批**同门同批**施工(两段转换 + 坐标解析同一次观察,4.4⑤);与 §3.1/§3.3(#1-#14)改写站点分属不同句段,叠加施工互不覆盖,本节改文以「§3 落笔后」为底稿。
> **增补节修订轨迹(coord-attack)**:`.debug/progress/2026-09-22-cw-screen-review/reviews/coord-attack-T15-16-17.md` 判本节未收敛 6 条低(本稿 A-3),已按攻击结论就地修订,零行为设计变更——A-3 = A 类伴随域「失读/离屏语义与名字域同格」补机制载体申报:新域 `box_card_names_xy` 须随批1 入 `_PAYLOAD_DOMAINS` 映射(§4.2 补录条;不入映射则离屏清场时名字域置 None、坐标域跨屏携陈值),§4.1(5)/§4.5 同步补批1 义务指针,T-13/T-14 同族(`wish_trial_opts_xy`/`star_tome_opts_xy`)随 T-37 全域对账;另 §4 preamble :48 计数随正本现值 12→11 对账(正本已更新为 11,底册 §3.1 表 equip 行归底册随批修订面,A-6 对账面)。

### 4.1 被推翻目标文本的改写声明(逐字,:35 推翻面 6 处)

**(1)「x 坐标不入容器」政策面推翻(代码注 + §2.2(a) docstring 目标文本)**:

- 代码注现役文本(实查 `cw_screen_box_pick.py` :72-73):「OCR 原始读数 [(卡名, 卡 x 中心), ...](x 升序;点击定位要 x 坐标,容器槽只收卡名表,x 对留守本 op 不进容器)。」= :35 反向政策(坐标不入容器、留守本 op 现算),随收敛批删除换申报——改文:「OCR 原始读数 [(卡名, 卡 x 中心), ...](x 升序;卡名与坐标一并上报入容器 `box_card_names` / `box_card_names_xy`(op-layer.md §1.1 :35 坐标单一真相源 = 观察上报),本 op 零坐标现算,读数 x 仅供观察侧解点)。」
- §2.2(a) 目标 docstring 形态段现文(本稿 :104-107):「``CwScreenBoxPickObs`` → ``report_screen_box_pick_obs`` 写槽 ``box_card_names`` 落容器(「写槽以本访问将决策为前提」由门 + 非空闸保证,桩无 gs → 跳过写、决策照走)→ obs 与原始读数(x 坐标对)挂实例属性进决策动作 node。」→ 改文(§3.3 #14 括注窄化落笔后的底稿上,仅动两处):「写槽 ``box_card_names`` 落容器」→「写槽 ``box_card_names`` / ``box_card_names_xy`` 落容器」;「obs 与原始读数(x 坐标对)挂实例属性进决策动作 node。」→「obs 读数(名 + x)与坐标一并上报入容器 ``box_card_names`` / ``box_card_names_xy``(同门双写,本文 §4.2);决策动作 node 零坐标现算。」

**(2)act 坐标组装删除(代码面,收敛批)**:现役(实查 :118-127)「`chosen, choose_x = self._cards[idx]`(:119)→ `card_point = Point(choose_x, CwScreenBoxPick.CARD_Y)`(:120)→ …… `_env = OverlayPickExecEnv(op=self, idx=idx, target=card_point)`(:127)」→ 改:`choose_x` 解包与 `card_point` 组装两行删除(坐标消费迁动作 op,4.3),env 改 idx-only `_env = OverlayPickExecEnv(op=self, idx=idx)`;`CARD_Y` 常量唯一消费点迁观察侧(4.2,与底册 T-13-6 同判);`chosen` 名字留守日志消费(act log :130-131)。

**(3):48 拆分连带(宿主路径 + 动作 op docstring)**:宿主类随拆分批迁 `operations/cw_op/cw_pick_box_card_action.py`(底册 §3.1);迁入批 docstring 坐标半句连带改写——详见 4.3(「点击点 = 卡名带下方 y=290 避「查看详情」按钮,决策半现算经 env 传入」→「点击点 = 容器 `box_card_names_xy[idx]`(观察期按避让几何解出),动作 op 自取」;避让几何留观察侧)。

**(4)§3.2 增补 2(条款①标准化收敛批)范围扩**:§3.2 修法第 1 条(两段转换)现文句尾「……转换住观察侧(画面 op 观察 node,op-layer §2.2「生产半住观察侧」),落容器半照旧 `report_screen_box_pick_obs`。」→ 改文「……转换住观察侧(画面 op 观察 node,op-layer §2.2「生产半住观察侧」),落容器半照旧 `report_screen_box_pick_obs`,且与**坐标解析上报同一次观察一并做齐**(op-layer.md §1.1 :35「归一化与坐标在同一次观察一并入容器」硬要求;坐标解析 = 候选 x + `CARD_Y` 解点,随两段转换同门入容器 `box_card_names_xy`,本文 §4.2)。」;§3.2 修法第 2 条(失败语义)现文「2. **失败语义**:任一候选转换失败 = 观察失败——观察 node round_fail 早退、零写零上报、交外循环重观察重读(与「读空」闸同型并列;禁带病上报)。」→ 改文句尾补「;**名字与坐标同进退**——转换失败时坐标域随名字域一并零写零上报(底册 §1.4-W1),禁坐标域先于名字域单独收敛(半截状态禁止,本文 §4.4⑤)。」;§3.3 表 #13「补语义句」目标文本句尾(『……不适用「多候选命中同一注册名 = 转换失败」互斥判。』后)补:「坐标与标准名一并入容器 ``box_card_names_xy``(观察期解点、同门双写),转换失败名字坐标同进退(op-layer.md §1.1 :35)。」

**(5)schema 登记连带(与 F-3 咬合)**:`DEFAULT_GS_SCHEMA` 新域键 `box_card_names_xy: 1`(批1 字段骨架批,4.5);F-3(c) 对齐锁(§2.3(c))影响核查:**反向扫描面不受影响**(`box_card_names_xy` 不以 `_opts` 结尾,不入 `endswith('_opts')` 扫描);**正向清单扩展点** = `single_field_slots` 封闭清单随批1 增补 `'box_card_names_xy'`(锁自述「新增槽域须同步扩正向清单」;底册 §1.8(b) 同判「正向清单扩展点随实施批申报」);批1 义务再补一项(coord-attack A-3)——`_PAYLOAD_DOMAINS` 映射登记 `'box_card_names_xy': ('货币战争-备战-武装箱选择', True)`(离屏清场载体,机制与不入映射的后果见 §4.2 补录条)。

**(6)screens/box_pick.md 文档面(正本,随收敛批施工)**:§4 伪码「target mouse_move + click」行(§2.2(c) 落笔后形态「target mouse_move + click →」)行前补一行「坐标 = 容器 ``box_card_names_xy[idx]``(动作 op 内取)→」;§2 形态声明(§2.2(c) 表行落笔后形态「派发(点卡选中即确认 + 动画等待 + 自上报住动作 op,契约 = flow/action_exec.md §2)」,链接格式保留)句尾补坐标域句「;点击坐标 = 观察上报容器 `box_card_names_xy`(op-layer.md §1.1 :35,动作 op 按下标自取)」。

### 4.2 观察上报增补(obs 扩坐标 + report 同门双写,写端唯一)

- **obs 扩**:`_read_card_names` 已产 `(name, x)` 对(实查 :136-146,x 升序)= 坐标生产现成一半——观察 node 就地解点 `points[i] = (x_i, CwScreenBoxPick.CARD_Y)`(y = 卡名带下方避让几何,观察期一次解出;`CARD_Y` 常量唯一消费点迁观察侧,4.1(2));`CwScreenBoxPickObs` 扩 `points: list[tuple[int, int]]`(与 `card_names` 同序等长)。取值时机 = 观察期快照、值形状 = 1080p 平铺元组(底册 §1.2)。
- **report 同门双写(写端唯一)**:`report_screen_box_pick_obs`(`kernel/cw_screen_report/box_pick.py`,写点锚 :48)**同一调用、同一写门**一并写 `gs.box_card_names` + 新域 `gs.box_card_names_xy`;坐标域写端唯一 = 本 report——act 内 `Point` 组装拆除后全 op 零第二坐标源。标准化收敛批(§3.2)落地后,坐标解析与两段转换同一次观察、经观察标准化门同门入容器。
- **转换失败同进退 + 等长断言**:任一候选转换失败 = 名字与坐标同进退(零写零上报,交回重观察;底册 §1.4-W1);report 内等长断言 `len(points) == len(names)`,不等长 = 观察 bug 响亮暴露(底册 §1.3,读端不做长度调和)。「读空」闸(observe 现役 :91-94)已同型零写零上报,坐标域天然随行;失读/离屏语义与名字域同格(底册 §1.4-W1;离屏清值机制载体 = `_PAYLOAD_DOMAINS` 映射登记,见下条补录)。
- **画面附加域映射登记(离屏清场载体;coord-attack A-3 补录,批1 义务)**:新域 `box_card_names_xy` 须随批1 入 `_PAYLOAD_DOMAINS` 映射(`kernel/cw_game_state.py` :220-234),登记值 = `('货币战争-备战-武装箱选择', True)`——与名字域 `box_card_names`(:231)同属屏、同 route_clearable。机制:离屏清值 = 路由清点循环逐域 `leave_screen` 置 None(`cw_loop.py` :1052-1062,遍历键 = `_PAYLOAD_DOMAINS`),`leave_screen` 对映射外域硬炸(`cw_game_state.py` :2735-2736「非画面附加域,禁离屏清值」)——不入映射则名字域离屏置 None、坐标域跨屏携带陈值,本节「失读/离屏语义与名字域同格」(底册 §1.4-W1)落不了地(实践风险有界:同门双写 + §3.1 局外门使 act 消费不到陈值,但批1 按缺登记清单落笔 = 系统性缺口,故选登记而非豁免)。底册 §1.8(b)/§4 批1 清单未列该登记,本稿补录为批1 字段骨架批义务交汇总批收编;T-13/T-14 同族 `wish_trial_opts_xy`/`star_tome_opts_xy` 同判,随 T-37 对 A 类伴随域全域对账。
- **schema 与 sim**:新域键 `box_card_names_xy: 1` 入 `DEFAULT_GS_SCHEMA`(version 1,A 类逐域新键,底册 §1.8(b));sim 分界 = 坐标域不建模,值恒 None(底册 §1.4-W4)。

### 4.3 动作 op 取坐标改写(env → gs 坐标域[idx],缺席/越界断言禁回退)

- **取点改写**:`CwActionPickBoxCardOp.run`(现 `cw_overlay_pick_action.py` :651-652 `mouse_move(env.target)/click(env.target)`)→ 自容器按 idx 取点,目标形态:

  ```python
  # 点击点 = 观察上报容器(op-layer.md §1.1 :35 坐标单一真相源);
  # 禁回退 env.target、禁 Point 现组装(均 = 第二坐标源)。
  gs = game_state_from_ctx(self.ctx)
  pts = None if gs is None else gs.box_card_names_xy.value
  if pts is None or not (0 <= self.param.idx < len(pts)):
      raise AssertionError(
          f'box_card_names_xy 坐标域缺席/下标越界(观察上报欠供,'
          f'禁现算回退): idx={self.param.idx} pts={pts!r}')
  op.ctx.controller.mouse_move(pts[self.param.idx])
  op.ctx.controller.click(pts[self.param.idx])
  ```

  (缺席/越界 = 守卫断言 AssertionError 响亮暴露、零点击——禁控制流分支、禁回退,底册 §1.4-W2。gs 缺席(局外)= §3.1 act 局外门 round_success 终结,动作 op 不在局外被派发;直构动作 op 的测试语境 = 显式注入坐标域,缺席即炸 = 防线非缺陷(底册 §1.4-W2)。)
- **上报零改动**:`report_action_pick_box_card_param` = 零写占位上报,与坐标无关,零触(底册 §1.4-W3);「本 op 零 chosen 写端,容器写零」申报维持(坐标取用 = 读端,非写)。
- **:48 拆分连带**:迁入批(4.1(3))docstring 坐标半句改写——现文(实查 `cw_overlay_pick_action.py` :625-626)「点卡(mouse_move+click bug#1 缓解;点击点 = 卡名带下方 y=290 避「查看详情」按钮,决策半现算经 env 传入)」→ 改文(按本稿 §2.2 清出派同步去「bug#1 缓解」标签)「点卡(mouse_move+click;点击点 = 容器 `box_card_names_xy[idx]`——观察期按避让几何(卡名带下方 y,避「查看详情」按钮)解出上报,op-layer.md §1.1 :35,动作 op 自取,缺席/越界 = 守卫断言)」——避让几何知识留观察侧,动作 op 零几何。act 侧 env 构造随 4.1(2) 改 idx-only = target 停喂(底册 §1.5;全族收敛完成后字段退役挂收敛尾批)。

### 4.4 验收锚(含过渡期铁律)

1. **report 双写锁**:同调用同门写 `box_card_names` + `box_card_names_xy`;等长断言触发即红;转换失败双零写(名字与坐标同进退,随 §3.2 标准化收敛批语义同门验收)。
2. **动作 op 取坐标锁**:坐标域 None / idx 越界 → AssertionError 且零点击;注入容器值 → 点击坐标 = 容器值。
3. **grep 零残留(本屏收敛批门)**:「x 对留守本 op 不进容器」零命中;`cw_screen_box_pick.py` act 无 `Point(` 组装、`choose_x` 零坐标消费(chosen 名字日志留守);env 构造无 `target=`;动作 op 无 `env.target`。
4. **全绿门槛** = §3.1(c) 局外出口锁 + `test_pick_box_decision_fail_closed` + progression inline 现役三把 box_pick 锁 + F-3 锁面(`test_terminal_contract_schema_and_match_shape`、`test_single_field_slot_schema_keys_align_with_field_names`——正向清单扩 `'box_card_names_xy'` 后)+ 新双锁(1/2)。
5. **过渡期铁律**(底册 §1.7):批1(字段骨架)落地至本屏收敛批完成之间 = 合法过渡(现役坐标链未断);**任何新屏/新 op 不得再走「决策半现算经 env.target」**(禁新增第二坐标源,新写法直接按底册骨架);**半截状态禁止**——本屏收敛批 = 「观察上报(坐标)+ act 删现算 + 动作 op 自容器取点」三件一批做完,且与 §3.2 标准化收敛批同门同批(两段转换 + 坐标解析同一次观察;只做一半 = 双坐标源/未标准化直报并存 = 违规)。

### 4.5 fields.md 增补条目指针(引用不重复设计)

- 字段设计单一源 = 底册 §1(五稿共用一次定谳):本屏宿主 = A 类纯名单域伴随域——`box_card_names_xy: Field[list[tuple[int, int]] | None]`(与 `box_card_names` 同序等长;后缀随名字域本名,不强加 `_opts`);键坐标系三要素(基 = 名字域列表下标 idx,0 起左→右画面物理序,与策略器输出下标/`param.idx` 同坐标系零换算/取值时机 = 观察期快照、动作执行期恒稳/值形状 = 1080p 平铺元组)按底册 §1.2 申报。
- fields.md 落点 = **批1 字段骨架批**(底册 §4 实施顺序):§3.4 头部引注段追加句 + 新增 §3.4.5a 小节(目标文本 = 底册 §1.8(a)/(b) 草案逐字;字段登记行含 `box_card_names_xy`;schema 登记 = 「A 类逐域新键入 `DEFAULT_GS_SCHEMA`(version 1)」;批1 随附义务(coord-attack A-3)= `_PAYLOAD_DOMAINS` 映射登记 `'box_card_names_xy': ('货币战争-备战-武装箱选择', True)` 一行(离屏清场载体,§4.2 补录条))。本稿引用不重复设计,fields.md 落笔以底册 §1.8 为准。
- 本稿辖内 schema 连带(与 F-3 咬合,4.1(5)):新域键 `box_card_names_xy: 1`;F-3(c) 对齐锁反向扫描面不受影响(`_xy` 后缀),正向清单 `'box_card_names_xy'` 扩展随实施批申报。
