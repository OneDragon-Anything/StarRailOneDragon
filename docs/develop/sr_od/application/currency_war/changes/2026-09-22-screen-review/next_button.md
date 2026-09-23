# T-26 下一步按钮 修法设计(next_button)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决(对抗轨迹:r1 未收敛 7 条→修订→r2 收敛 0 条实质;残留 2 条低[N-1 briefing 锚 §2.4→§2.5 三处/N-2 升架提案「第 4 件」应为「至少 4 件」补 op_close_shop]一句话级,随定稿清偿;见 reviews/T-26-attack-r2.md)
- 审查输入:`.debug/progress/2026-09-22-cw-screen-review/reports/T-26-r1.md`(发现 F-1/F-2;总判定 = 有问题,高 0 中 0 低 2)
- 真值基线:本稿全部「现状」陈述以审查时点工作树代码为准,落地时若代码已再变,以落地时点代码重新对账后再动笔。符号锚 = `文件::符号名`。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根)。
- 修法性质:F-1 = 辖内一处注释改写 + 族外清单登记与盘点件提案;F-2 = 正本文档单句修正。**零行为变化**(无任何逻辑/签名/常量改动;改动面 = 一处模块头注释 + 一句正本文档)。

## 1. 问题与动机

### 1.1 F-1 注释持久索引悬空(低)

- **现状症状**:`operations/cw_screen/cw_screen_next_button.py::CwScreenNextButton` 模块头首句「货币战争 前进按钮 op(空决策形态;ADR-0584,A10)。」——引用形态合规(ADR-NNNN 属 AGENTS.md §8 认可的持久索引),但目标文档不在正本树:`docs/develop/sr_od/application/currency_war/` 下无 `decisions/` 目录(glob 实查零命中),ADR-0584 全文仅存 `.debug/temp/` worktree 快照(gitignore 过程件,不构成持久索引)。此为家族面:pattern `ADR-0584` 在 src 树 + docs 正本树命中 = src 25 处(推进型族模块头 11 文件 13 处 + `operations/cw_loop.py` 12 处)+ screens 正本 3 处(精确总数不作稿面申报——含 changes/ 过程区命中的全树口径归盘点件统一复核,§2.1 B/C)。同根家族面更大:src 树 pattern `ADR-\d{4}` 命中千余处、数十个号,`decisions/` 不存在即全部悬空。
- **根因归层**(根源两问):①根在哪层 = **约定层**——`decisions/` ADR 档案已按用户令退役(在册口径 = `strategy-docs/README.md`「决策 why 进设计文档动机段与代码注释(ADR 档案已退役,仅经用户命令创建)」),退役动作与既有引用面迁移解耦,缺「退役符号引用面全量清查」收尾门;不是注释写法本身违例(退役前 ADR-NNNN 引用合规)。②修的是根还是症状 = **两件并做**:辖内点名点位按先例判据当场清偿(症状面,随本批落地);家族根 = **升架构件**——悬空 ADR 逐稿逐族登记在本迭代已第 4 件(跨件半问触发;iteration-design.md §7 核三「同族问题第二次出现 = 该升架构级设计件」),本稿提案 T-37 增设「全树退役 ADR 引用面一次性盘点」件替代逐件登记(§2.1 C)。
- **战术权衡显式声明**:盘点件裁决前,族外引用面悬空状态延续,代价 = 指针暂不可核验;影响面已知且低——各引用点位的合同/语义均有现役持久承载(本屏空决策合同 = `screens/op-layer.md` §3 推进型行 + `kernel/cw_screen_report/next_button.py` 模块头全路径指针双处自足),行为合规性零影响。
- **解决到哪**:本屏点位(`cw_screen_next_button.py:1`)并入本稿落地批当场改写(§2.1 A);族外引用面清单并入盘点件输入底册(§2.1 B);盘点件提案与处置范式冲突申报随本稿呈报 T-37(§2.1 C/D)。
- **明确不解决**:ADR 制度本体与 `decisions/` 目录去留(AGENTS.md §9 用户命令制,设计稿无权裁定;AGENTS §9 双层文档流模板列 decisions/ 为通用必有,与 CW 域用户令退役现状的制度张力 = 盘点件呈报用户的裁决点,本稿不裁);族外引用面 27 处(随盘点件统一清偿,禁本批零散动手);`.debug/temp/` 快照与 changes/ 过程区命中(过程件,不入登记面)。

### 1.2 F-2 形态分型判据摘要混入非分型维度(低)

- **现状症状**:`screens/README.md` §3 分型判据句「空决策形态 ⇔ 已建档分发画面且两者皆缺——纯推进为流程义务:观察 + 推进处理 + 交回外循环(新 op 单尝试,重试预算归外循环)」。按「已建档分发画面」字面,权威总表在册成员不满足判据:`CwScreenNextButton`(screen_info 无对应 yml,glob 实查;`screens/next_button.md` §1 自述「无画面档」)与商店框 2 类 `CwOpOpenShop`/`CwOpCloseShop`(编排壳 op,非画面档成员;在册锚 = `screens/op-layer.md` §3 推进型行「商店框,推进型只读/导航变体」+ `screens/README.md` §4 表 CloseShop 行「编排壳」)——判据摘要混入「已建档」这一非分型维度,致按字面无法涵盖总表在册成员。
- **根因归层**:①根在哪层 = **语义层**——判据摘要写作时点「画面 = 已建档分发画面」的隐含假设,与后来入册的非建档成员(兜底推进、商店框)不同步;README §3 同节已显式让渡总表权威给 op-layer §3,矛盾出在摘要措辞混维。②修的是根还是症状 = 直接修判据措辞本身(把判据收敛回本节分型维度「选择面/逻辑态账」)= 修根,非遮盖。
- **解决到哪**:`screens/README.md` §3 该句一处改写(逐字目标 = §2.2)。
- **明确不解决**:`screens/next_button.md` 本身(其「无画面档」自述与修后判据直接相容,零改动);`screens/next_button.md` §1 的「0r」退役分支旧号(在册欠账——`flow/outer_loop.md` §2.3 已退役号表显式在册申报「现行代码已无对应分支,属文档残留旧号」,本迭代边界 = 在册欠账不重复立项;若号制清偿批立项,该句随批清偿);行为面任何东西(审查报告 §3 已核对一致项 = 两 node 形态/观察门/重入裁决/无 report/零策略器问询/单尝试 + 重试预算归外循环/外循环接线,全部为落地禁触碰边界);`changes/2026-09-14-unified-action-factory/design.md` 中同短语命中(他迭代过程区,寿命自洽,不属正本清理面)。

## 2. 方案

### 2.1 F-1 修法:辖内点位当场清偿 + 悬空 ADR 清偿升架构件

**A. 辖内点位(本稿落地批执行)**:

| 位置 | 现状 | 目标语义(逐字) |
|---|---|---|
| `operations/cw_screen/cw_screen_next_button.py` 模块头首句 | 「货币战争 前进按钮 op(空决策形态;ADR-0584,A10)。」 | 「货币战争 前进按钮 op(空决策形态;合同正本 = docs/develop/sr_od/application/currency_war/screens/op-layer.md)。」 |

依据:①先例判据 = 同迭代 briefing/bookcard/op_open_shop 三稿统一口径「审查点名辖内悬空 ADR 引用当场清偿 + 族外同家族登记」(briefing §2.4 辖内改写 + 验证门辖内 grep 零命中;bookcard 清理准则④「不在册即换纯语义描述或现役符号锚」「引用即复刻违例」);②目标文本与 kernel 侧既有指针同形 = `kernel/cw_screen_report/next_button.py` 模块头「正本 = docs/develop/sr_od/application/currency_war/screens/op-layer.md」;③改写对任一出路无损失——op-layer 指针在任何出路裁决下均为真(ADR 若经用户命令复立,是否回挂号引用由盘点件统一裁,briefing §2.4 同款兼容性示范)。

**B. 族外底册(并入盘点件输入,本稿不落地)**:

计数口径:pattern = `ADR-0584`;scope = `src/` 树 + docs 正本树;changes/ 过程区命中(含各设计稿自身)不入登记面;精确总数不作稿面申报,归盘点件统一 pattern 复核。审查时点分布:

- src 24 处 = 推进型族模块头 10 文件 12 处(`cw_screen_plane_detail.py` A1、`cw_screen_refresh_odds_popup.py` A2、`cw_screen_item_detail_popup.py` A3 两处、`cw_screen_consumable_overlay.py` A4、`cw_screen_aha_equip_pick.py` A5 两处、`cw_screen_prep_locked_return.py` A6、`cw_screen_role_detail_overlay.py` A7、`cw_screen_emblem_detail_popup.py` A8、`cw_screen_interrupt_dialog.py` A9、`cw_screen_shop_card_detail.py`(合同,无条目号))+ `operations/cw_loop.py` 12 处([cw-op] 第三载体行窗口/异常安全出口/0n 适配形轻壳/分支统一 dispatch 包装/C1·C2 收口面/两 op 两对 journal 行/时序申报);
- screens 正本 3 处 = `screens/aha_equip_pick.md` 两处、`screens/item_detail_popup.md` 一处。

**C. 升架构件提案(跨件半问应答,呈 T-37)**:悬空 ADR 引用的处置在本迭代已第 4 次逐稿逐族登记(briefing:0559/0431/0397/0081;bookcard:0634 外溢;op_open_shop:0634;本稿:0584),而 src 树 pattern `ADR-\d{4}` 命中千余处、数十个号全部悬空(`decisions/` 不存在),承重族(例:ADR-0250 战斗窗口 watch 宽限、ADR-0574 入口链弹窗守卫契约、ADR-0581 起局前置码哈希闸)无稿认领——逐件登记不收敛。**提案:T-37 增设「全树退役 ADR 引用面一次性盘点」件**:单一 pattern `ADR-\d{4}` 全树盘点 → 分族归属(承重语义/纯出处)→ 处置范式统一裁决 → 逐族出路裁决(现役化改指现役承载 ∨ 用户命令补立 ADR)→ 逐族清偿。各稿族清单(含本稿 B)为其输入底册;本稿族的独立出路裁决随盘点统一,不单独立案。

**D. 处置范式冲突申报(随 C 一并呈 T-37)**:本迭代现存范式分裂——battle_wait 稿 §2.6 准则 4「ADR 引用全部保留」(其辖内 ADR-0638/0583 同判悬空)、briefing/bookcard/op_open_shop「辖内清 + 族外登记」、briefing §2.4 已在册申报该冲突并提出修订提案——「悬空 ADR 引用处置范式统一」= 盘点件的前置裁决项(先于逐族出路裁决)。

**辖内收尾判据(本稿落地批)**:`cw_screen_next_button.py` grep `ADR-0584` 零命中(改写即零命中,不留墓碑)。(盘点件全树门提案 = src 树 + docs 正本树内任一 `ADR-\d{4}` 命中,其指向的 `decisions/<号>-*.md` 在册存在,否则该族清偿未完成——随 C 归盘点件。)

**取舍**:

- 备选 A:族外与本屏一并零落地登记(全家族清单登记、辖内也不动)——放弃:与三份先例判据(辖内点名悬空引用当场清偿)相反;其支撑论点不成立——「中间态两口径」由统一裁决收口(三先例已实证接受该中间态并交统一收口),改写对出路②无损失(§2.1 A 依据③),改写随 F-2 同批落地零额外批成本。
- 备选 B:设计稿宣布补立 ADR-0584 恢复正本——放弃:ADR 仅经用户命令创建(AGENTS.md §9),设计稿无权;decisions/ 档案退役系用户既裁定。
- 备选 C:登记行维持逐族独立立案(不提案盘点件)——放弃:跨件半问已触发(第 4 件),逐件登记面对千余处在册悬空与无稿认领的承重族不收敛(iteration-design.md §7 核三),升架构件是规范明文的应答方式。

### 2.2 F-2 修法:README §3 分型判据句收敛回本节分型维度

单句改写(唯一修法点位;该 bullet 其余段与「单选族例外」句原样保留):

| # | 位置 | 现状(病句核心) | 目标语义(逐字) |
|---|---|---|---|
| 1 | `screens/README.md` §3 分型判据 bullet 中段 | 「空决策形态 ⇔ 已建档分发画面且两者皆缺——纯推进为流程义务:观察 + 推进处理 + 交回外循环(新 op 单尝试,重试预算归外循环)」 | 「空决策形态 ⇔ **无选择面 ∧ 无逻辑态账**——纯推进为流程义务:观察 + 推进处理 + 交回外循环(新 op 单尝试,重试预算归外循环);建档与否非分型维度——本型成员含无画面档的兜底推进(前进按钮)与商店框 2 类(编排壳 op,非画面档成员)」 |

依据(就地):①权威与维度 = `screens/op-layer.md` §3 推进型行「无选择面无容器域」+ 成员清单含 `CwScreenNextButton`(首位)与商店框 2 类;README §3 同节末 bullet 已显式让渡总表权威给 op-layer §3。判据用词取 README §2 模板「三选一」本节轴(选择面/逻辑态账;「逻辑态」定义 = README 卷首术语行,与 op-layer「容器域」同义),摘要服从权威总表。②成员反例 = `assets/game_data/screen_info/` 无 next_button 对应 yml(glob 实查)、`screens/next_button.md` §1「无画面档」自述;商店框 2 类 = 编排壳 op、非画面档成员(在册锚 = op-layer §3 推进型行 + screens/README §4 表 CloseShop 行「编排壳」)。③规范 = AGENTS.md §9(正本永远与代码现状一致)。

**取舍**:

- 备选 A:给 `CwScreenNextButton` 补建档以迁就「已建档」判据——放弃:兜底分支按设计不对应单一画面(能落到外循环分支 5 = 该「下一步」不属于任何已建档画面档,`screens/next_button.md` §1 与 `flow/outer_loop.md` §2.2 在册口径),建档会造无对应画面的空档违 AGENTS §5「建档对象是画面」;且方向反了——判据摘要服从权威总表,非反向改总表成员。
- 备选 B:删除 README §3 判据摘要 bullet、只留「总表 = op-layer §3」指针——放弃:摘要的价值 = README 读一遍知分型逻辑,删摘要把全部判据阅读压到 op-layer 单点;病在措辞混入非判据维度,不在摘要存在,修措辞即治本。

### 2.3 落地文件面总表

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `operations/cw_screen/cw_screen_next_button.py` | 模块头首句 ADR-0584 引用改指正本锚(F-1,§2.1 A) | 注释 |
| `screens/README.md` | §3 分型判据句一处改写(F-2,§2.2 #1) | 正本语义修正 |
| (登记/提案,零落地面)§2.1 B 族清单 → 盘点件输入底册;§2.1 C 盘点件提案 + D 范式冲突申报 → T-37 | F-1 家族根 | 登记/提案 |

统一验收:

1. `operations/cw_screen/cw_screen_next_button.py` grep `ADR-0584` 零命中(§2.1 辖内门);`git diff` 该文件仅模块头首句注释变化。
2. `screens/README.md` 修后句不再含「已建档」维度(正本树 `docs/develop/sr_od/application/currency_war/screens/` + `flow/` grep `已建档分发画面` 零命中;changes/ 过程区命中不入判据);判据维度与 README §2 模板「三选一」(选择面/逻辑态账)同文;与 `op-layer.md` §3 五型分类 = 子集相容——推进型成员均满足空决策判据,反向不蕴含(全形态型六屏空决策变体有 report 无逻辑态账,不在推进型清单;op-layer §3 自注在册)。
3. `git diff` 确认零行为变化(无逻辑/签名/常量 diff)。
