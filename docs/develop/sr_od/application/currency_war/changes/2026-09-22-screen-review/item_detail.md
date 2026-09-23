# T-30 物品详情弹窗 修法设计(item_detail)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决(对抗轨迹:r1 收敛·0 条实质;残留 1 条低随定稿清偿,见 reviews/T-30-attack-r1.md)
- 命名注:本稿标题「物品详情弹窗」与建档/正本/代码的实名「道具详情弹窗」同指(画面实名 = 货币战争-道具详情弹窗,以建档 `screen_name` 为准,正文一律用实名)。
- 审查输入:`.debug/progress/2026-09-22-cw-screen-review/reports/T-30-r1.md`(发现 F-1/F-2 各一条;总判定 = 有问题,高 0 中 0 低 2)
- 真值基线:本稿全部「现状」陈述以审查时点工作树代码为准,落地时若代码已再变,以落地时点代码重新对账后再动笔。符号锚 = `文件::符号名`,行号仅作本稿定位辅助。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根;建档 yml 以仓库根 `assets/` 起算)。
- 修法性质:F-1/F-2 同句同修——`operations/cw_screen/cw_screen_item_detail_popup.py` 模块 docstring 一处括号注改写,**零行为变化**(无任何逻辑/签名/常量/建档改动;`sr-od-test/` 零触碰)。
- 准则参照:注释清理一致性参照 T-3 稿([battle_wait.md](battle_wait.md))§2.6 五条准则(禁形一·会话局部标识符 / 禁形二·变更史叙述 / 改写方向 = 结论→出处→边界 / 保留豁免 / 跨修法交叠一次成文)。F-1 命中面 = 对当前事实的假陈述(非两禁形直接形态),适用条款 = 仓库根 AGENTS.md §8「注释写『为什么』……他只看代码与注释就要能重建你的推导」义务(审查 F-1 规范条款同一出处;AGENTS.md §9 as-built 精神同判:会失效的现状快照不入记载);F-2 命中面 = 准则 1 禁形一(会话局部标识符「N9」)直接形态(AGENTS.md §8「引用必须是持久索引」)。同族先例:T-28 稿([consumable_overlay.md](consumable_overlay.md))对同族「注释对现役事实的假陈述」取指针现役化路线,本稿同判据取舍见 §2.2。

## 1. 问题与动机

### 1.1 F-1 docstring「本画面尚无 screen_info 档案」与建档现状相反,OCR 回退根因写错(低)

- **现状症状**(审查报告 F-1):`operations/cw_screen/cw_screen_item_detail_popup.py` 模块 docstring(L4)写「**入口观察用 OCR 回退**(本画面尚无 screen_info 档案,方案审 N9)」。三方对照证伪:①建档在册 = `assets/game_data/screen_info/currency_war_item_detail.yml`(screen_name 货币战争-道具详情弹窗,单 area「按钮-关闭」,`id_mark: false`);②本 op 自身消费建档 = 同文件 `CwScreenItemDetailPopup::progress_once` 的 `area_center(self.ctx, self.CLOSE_AREA, self._screen_name)`(`CLOSE_AREA='按钮-关闭'`、`_screen_name='货币战争-道具详情弹窗'`);③正本 [screens/item_detail_popup.md](../../screens/item_detail_popup.md) §1 已按现状表述「**有档案但无 id_mark**(仅「按钮-关闭」定位区)→ 入口维持 OCR 回退」,且同 docstring 后文(L7-8)「建档含 id_mark 后 op 侧可切 area 锚」以建档存在为前提——「尚无档案」为写作时点旧状态,与三面直接矛盾。注释把 OCR 回退根因写成「无档案」,真实根因 = 「有档案但 id_mark 缺位、无画面身份锚」,错误根因误导读者重建推导。行为面零影响,纯注释失真。
- **根因归层**(根源两问):①根在哪层 = **表示层(注释内嵌会失效的现状快照)**——建档批更新了正本 doc 与建档 yml,模块 docstring 的「尚无档案」现状声明未被点名清偿;②修的是根还是症状 = 本稿把该句改写为现役事实陈述(治已发生的漂移)+ 落地批配机械验证门(§2.3);『建档/迁移批收尾缺「注释现状声明引用面清查」门』的流程级根已由 T-3 稿 §2.1 跨批登记面立案(归宿 = harness landing 模板固定判据方向),本稿不重复立项(跨件半问:同根,共用同一登记,禁第三件症状补丁)。
- **解决到哪**:L4 括号注逐字改写为现役根因(目标文本 = §2.1);改写后该句与建档 yml、正本 §1、同 docstring 后文四面口径一致。
- **明确不解决**:①建档 id_mark 缺位本身(OCR 回退的机制层根因)——持久挂账已在册:正本 §1 开放设计注(「档案 id_mark 缺位(OCR 回退根因)」)+ registry 条目注(`kernel/cw_overlay_registry.py` L329-332:「建档后 screen_name/anchor_area 取建档终值(id_mark 用独有标题行),判定坍缩为单 area 锚」);补 id_mark 需实机帧与模板素材,静态设计批无法代劳,注释内复写挂账 = 与上述在册载体成第二源,禁;②registry 道具详情条目段(L329-343,`active=False`、`close_point=(1862,65)` 硬编码)「待实机建档」措辞相对「建档已存在」的滞后——审查报告 §4.4 已在册登记为边界观察(该文件不属本审查三面、迁移候批口径无正本条款直接辖定),归宿随 registry 迁移候批裁决,本稿不触;③兄弟屏 `cw_screen_consumable_overlay.py`(复用本屏建档「货币战争-道具详情弹窗.按钮-关闭」)零交叠——T-28 稿辖域;④审查报告 §3 全部已核对一致面(含 op-layer.md §3 分型归属、screens/README.md §2 as-built 纪律辖下的两 node 形态与出口语义/决策控制铁律/观察上报形态/文档 as-built 九节/完备锁形态归属/坐标单一真相源等)为落地禁触碰边界,禁借清理之名改动在码语义。

### 1.2 F-2 注释引用「方案审 N9」无持久索引可循(低)

- **现状症状**(审查报告 F-2):同句括号注内「方案审 N9」为会话局部标识符——「N 编号」在仓内无可定位持久载体(审查报告全仓检索:仅 `docs/develop/sr_od/application/currency_war/proofs/math_proofs.md` 的「N9:」为无关同名),既非持久索引(ADR-NNNN/文件路径/符号名)亦非纯语义描述,读者无法重建该 OCR 回退裁决的出处。规范出处 = 仓库根 AGENTS.md §8「引用必须是持久索引」。
- **根因归层**:**约定层**——持久索引纪律为后立规范,存量注释未回溯清理(T-3 稿 §1.6 F-6 同判:同族禁形系统性命中 CW 全域);辖内清偿本句,机制缺口的根治归 T-3 稿 §2.6 已立的全仓注释卫生批(含增量防线腿),本稿不另立第二套机制。
- **解决到哪**:随 §2.1 同一处改写一并清出——「方案审 N9」无独立存续内容(其指向的裁决语义由括号注现役事实陈述与该段既有纯语义描述完整承载,见 §2.1 依据面),删除零信息损失,不补第二处引用。
- **明确不解决**:①`strategies/impl/mandate_v1/mandate.py` L1748-1749 同形态「方案审 N5/R2」——同族面,取舍 = 登记 T-37 不并入本稿(§2.2);②同文件「ADR-0584,A3」(L1)/「ADR-0584 §2.2」(L8)悬空 ADR 引用与「0e3」号制——任务明示在册家族面(审查报告 §3.5 同证),归宿随 T-37 出路裁决(T-26 稿 [next_button.md](next_button.md) 提案的「全树退役 ADR 引用面一次性盘点」件已入 T-37 裁决面),本稿不触;③「bug#1 缓解」标签(本文件两处)——语义持久载体在 `operations/cw_screen/_overlay_confirm.py` 模块头(bug#1 机制定义,审查报告 §3.5 判持久),保留;④「× 位于 (1862,65) 原 VLM 定位已 area 化」(`progress_once` docstring)——审查报告 §3.5 判其承担 area rect 出处职能、不判变更史违例,保留;⑤src 树其余「方案审」字样命中(`kernel/cw_card_identity.py`、`kernel/cw_economy.py`、`kernel/cw_intention.py`、`kernel/cw_reward_node.py`、`kernel/cw_vocab.py`、`strategies/impl/mandate_v1/` 数文件等)——非本稿审查对象文件面,族级清偿归全仓注释卫生批,本稿不外推命中清单、不扩文件面。

## 2. 方案

### 2.1 F-1/F-2 修法:入口观察括号注逐字改写(同句一次成文)

单点位(F-1 与 F-2 同句,一次改写同时清偿两发现;T-3 稿 §2.6 准则 5 跨修法交叠一次成文;行号仅定位辅助,改动面 = 第 4 行):

现状(逐字,模块 docstring 第 3-8 行整段):

```
获得道具(如 3 费聘用书)后自动弹介绍 modal(0e3)的处理迁移:点 × 关闭,
无验效。**入口观察用 OCR 回退**(本画面尚无 screen_info 档案,方案审 N9):
「聘用书」∧ 非祈愿屏,与外循环分发判定同源同参——祈愿试炼选项名含
「聘用书」(4 费聘用书)的截胡死循环修复(实机实锤单次 15min+)靠这道排他,
排他双写于外循环分支判定与本 op 入口(两处同参,建档含 id_mark 后 op 侧
可切 area 锚,切换属实施批内部对齐,ADR-0584 §2.2)。
```

目标(逐字;第 4 行一分为二,其余五行逐字不动):

```
获得道具(如 3 费聘用书)后自动弹介绍 modal(0e3)的处理迁移:点 × 关闭,
无验效。**入口观察用 OCR 回退**(建档 currency_war_item_detail.yml
在册但无 id_mark——仅「按钮-关闭」定位区,无画面身份锚):
「聘用书」∧ 非祈愿屏,与外循环分发判定同源同参——祈愿试炼选项名含
「聘用书」(4 费聘用书)的截胡死循环修复(实机实锤单次 15min+)靠这道排他,
排他双写于外循环分支判定与本 op 入口(两处同参,建档含 id_mark 后 op 侧
可切 area 锚,切换属实施批内部对齐,ADR-0584 §2.2)。
```

目标文本逐成分依据(就地):

- 「建档 currency_war_item_detail.yml 在册」= 建档事实(`assets/game_data/screen_info/currency_war_item_detail.yml`:screen_name 货币战争-道具详情弹窗,单 area「按钮-关闭」);消费点证明 = 同文件 `progress_once` 的 `area_center` 调用(§1.1 ②)。
- 「无 id_mark——仅「按钮-关闭」定位区,无画面身份锚」= OCR 回退现役根因,口径与正本 `screens/item_detail_popup.md` §1「有档案但无 id_mark(仅「按钮-关闭」定位区)」同文;id_mark 语义 = 仓库根 AGENTS.md §5(画面独有的稳定元素,组合内全部命中才算精准匹配)——本档唯一 area 为 × 点击定位区且 `id_mark: false`,不构成画面身份锚,入口门故不能走 area 锚。
- 与同 docstring 后文的自洽分工:后文「建档含 id_mark 后 op 侧可切 area 锚」讲切换路径,括号注讲现在为何回退,两半不重复;改写后同段内建档存在性陈述前后一致。
- 改写纪律 = T-3 稿 §2.6 准则 2/3:纯现在时陈述,零变更史成分(「写作时无档案/建档后未随更新」类叙事禁入,现状对错归 git 历史);「方案审 N9」按准则 1 清出——裁决语义(为什么 OCR 回退、排他为何承重)由括号注现役事实 + 该段既有纯语义描述(「截胡死循环修复(实机实锤单次 15min+)」)完整承载,改写后出处形态 = 持久索引(建档文件名)+ 纯语义描述,合 AGENTS.md §8 二者取一。

### 2.2 取舍

- **路线 = 注释改写现役事实(T-22 稿 [plane_transition.md](plane_transition.md) §2.2 / T-28 稿的指针现役化路线),不取 T-27 稿 [plane_detail.md](plane_detail.md) §2.2 补对号表路线**。判据 = 陈述面/引用面真伪:「尚无 screen_info 档案」不是待对号的历史指称,而是对现役事实的假陈述(建档在册且被本 op 消费)——补录进任何历史状态登记位 = 读者按表解析出假前提;「方案审 N9」连可对号的持久载体都不存在(全仓零落点),「补录」无对象。唯一治愈 = 改写为现役事实 + 持久索引(建档文件名)。
- **备选 A:仅删「,方案审 N9」、保留「本画面尚无 screen_info 档案」**——放弃:F-1 未治,假根因仍在,读者据其误判「补建档即可切 area 锚」(实际缺的是 id_mark),且与同 docstring「建档含 id_mark 后……」句矛盾(建档不存在则该句无所指)。
- **备选 B:括号注内补「正本 §1」文档指针或复写「待补 id_mark」挂账**——放弃:挂账的持久载体已是正本 §1 开放设计注与 registry 条目注(§1.1 明确不解决 ①),注释内复写 = 第二源漂移面(T-28 同判:理由/挂账复制即第二源);本修法只须使该句与建档事实及正本口径一致,正本导航由正本自身索引体系承担。
- **F-2 同族面 mandate.py L1748-1749「方案审 N5/R2」:登记 T-37,不并入本稿**。理由:①**文件面纪律**——`mandate.py` 属策略实现层,非本审查对象三面(画面 op/正本 doc/建档 yml);审查报告 F-2 位置点名 = 本 op 文件,mandate.py 仅作「同族面供收敛批参考」登记;本稿落地扩面进策略层文件 = 借清理扩面。②**语义域不相交**——L1748-1749 引文辖血闸「破息批无金可破 → 解锁包件①转化语义不适用」的收窄申报(ADR-0578 血闸注释块),其改写需策略层语境对账(收窄申报的语义本体与持久出处都要在策略侧重建),本稿无法在不做该对账的前提下给足「实现者无需再设计」的目标文本;与本屏 OCR 门无共同上下文,并入互不借力。③**同根处置已有归宿**——「N 编号会话局部标识符」清理准则 = T-3 稿 §2.6 准则 1,全仓注释卫生批为清偿载体;登记路径 = T-37 汇总清单点名 `mandate.py` L1748-1749(与 src 树其余「方案审」字样命中同族归并),随卫生批或 T-37 逐族出路裁决清偿(跨件半问:N9 与 N5 同根 = 注释持久索引纪律,共用同一登记,禁第二件逐件修)。

### 2.3 落地文件面总表与统一验收

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `operations/cw_screen/cw_screen_item_detail_popup.py` | 模块 docstring 入口观察括号注改写(§2.1) | 注释(零逻辑) |
| (T-37 登记面,待裁决)`strategies/impl/mandate_v1/mandate.py` | L1748-1749「方案审 N5/R2」同族面(§2.2 取舍;归宿 = T-37 汇总清单 → 全仓注释卫生批或逐族出路裁决) | 不在本稿落地批文件面 |

统一验收(验证门,机械可判;落地批照此对账):

1. `grep -n "方案审" src/sr_od/application/currency_war/operations/cw_screen/cw_screen_item_detail_popup.py` 零命中;`grep -n "尚无 screen_info 档案" src/sr_od/application/currency_war/operations/cw_screen/cw_screen_item_detail_popup.py` 零命中;
2. 正向核对:修后 docstring 含「currency_war_item_detail.yml」「无 id_mark」「按钮-关闭」「画面身份锚」四成分(建档事实 + 现役根因 + 身份锚缺位语义在场);
3. `git diff` 确认该文件仅模块 docstring 该段改动(类体、`entry_ok`/`act`/`progress_once`、常量与 import 零触碰,零逻辑 diff);`uv run ruff check src/sr_od/application/currency_war/operations/cw_screen/cw_screen_item_detail_popup.py` 通过;
4. 四方口径互查一致:修后 docstring ≡ `screens/item_detail_popup.md` §1(「有档案但无 id_mark(仅「按钮-关闭」定位区)→ 入口维持 OCR 回退」)≡ `assets/game_data/screen_info/currency_war_item_detail.yml`(单 area「按钮-关闭」,`id_mark: false`)≡ 同 docstring 后文「建档含 id_mark 后 op 侧可切 area 锚」;
5. 零行为变化(src 树无逻辑 diff);`sr-od-test/` 零触碰;与审查报告 §3 全部一致面零交叠。
