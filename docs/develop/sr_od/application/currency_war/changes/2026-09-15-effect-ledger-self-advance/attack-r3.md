# 设计对抗报告·第三轮（聚焦核验）

> 攻击规范:`docs/develop/harness/iteration-design.md` §7(三核)/§5(写作硬规则三条)。
> 本轮只核验第二轮 N1-N4 的修正面(design.md §2 方案 1.c/1.d/行为变化申报 + landing.md 3.1 判据),不重开全量攻击。
> 版本基准:设计修正 = 提交 019472b66(「CW 迭代设计:二轮对抗修正」,git log 实证);其上有 README 链接提交 f884ee8a9 与**后置代码提交 44e91987a**(统一观察对账机制批,动 cw_game_state/cw_observation/cw_loop 等 7 文件)——**该代码提交使设计所引行号整体漂移**(如 `_node_key_for_ord` 3183→3240、`effective_node_ord` 3095→3152),属环境漂移非设计失实;本文行号均为现工作树(HEAD=44e91987a)实测,落地时按符号名定位。

## 结论

**仍有阻断项**:N2/N3/N4 三项真实闭合(N2 触发条件完整自洽且入口帧清单对 18 边全景完备、N3 内联无悬空、N4 三分支恰覆盖载体全部返回形态);但 **N1 的修复机制生产不可达**——「补给选择画面当帧结算」的前提是该画面帧进入派生管线,而生产链路**从未**以 `货币战争-补给` 喂入 `observe_screen_context`(漏斗画面名映射封闭于备战/开商店/战斗等待三相位,权威 node-derivation.md:232-233 自我申报「漏斗仅挂备战/商店/战斗三相位」;补给屏 op `CwScreenSupplyNode` 零 `read_game_state` 调用;design/landing 无任何阶段补喂入),补给入口金结算在实机永不触发,行为变化申报「补给节点入口收入…变为入口帧管线 logic 结算」失实、landing 3.1 补给判据直调可绿而生产恒死——按第二轮同一「带开放问题的定稿不存在」门槛(§6)打回;小改(补生产喂入,或收缩申报挂喂入面批)后可过。

## N1-N4 闭合核验表

| # | 判定 | 核验与证据 |
|---|---|---|
| N1 | **未闭合**(换形:a 子项真、机制生产不可达 → R3-1) | **(a) 段序与直定 = 实证成立**:`SCREEN_NODE_TYPE_DIRECT` 含 `'货币战争-补给': 'supply'`(`cw_game_state.py:225-230`,值 :227);类型派生块 = `observe_screen_context` 方法体最后一段(:3107-3116,弹窗族专属屏直定经 `_write_derived_node_type` 写 `bs.node` 镜像 kind,条件含 `node_hist_ord is not None`——补给屏自动弹形态下弹窗腿同帧已推进 hist,守卫通过),设计 1.d「段序在类型派生之后,当帧已直定 kind=supply」与代码实构一致。**(b) 状态对齐 = 语义成立但前提失效**:补给屏帧上 settlement/streak 与现码备战帧同源(结算窗段内由漏斗写入,弹窗不重置),supply 分支收入语义(`cw_economy.py:515-518`,base=平面感知键、streak_amt=0)无分歧;申报「现码不在补给入口做 logic 结算」属实(现 tick 块仅在备战分支,`cw_loop.py:1885-1969`)。**但该帧生产永不进入管线** → 申报的「变为入口帧管线 logic 结算(supply 分支首次进 logic 面)」不可达,详见 R3-1。措辞精度附注:divert 形态(备战帧先行,nodeseq current=supply,`cw_loop.py:2210-2219`)下现码 tick 已在补给节点的备战帧 logic 结算(镜像 kind 由 prep spec 节点行现读)——「supply 分支首次进 logic 面」严格说已有先例,申报宜限定为「补给入口面首次」 |
| N2 | **闭合** | ①三 conjunction 已进形式条件行(design.md:27「`effective` 非 None ∧ `effective > (boundary_settled_ord or 0)` ∧ 本帧为该节点的入口可结算帧」),原「闸住只在理由段」的规格精度缺陷消除;②镜像矛盾消解:「序与位置禁读节点镜像;**kind 为唯一镜像读取**」(:28)显式豁免 + 参数源逐项标注(序/位=反解 :29、kind=镜像现值 :30),与现码「plane/round 取镜像、kind 取镜像」的差异面如实申报为「派生序反解 + 镜像 kind」(:44);③**入口帧清单对 18 边全景完备**:逐边核对 `node-derivation.md:105-124`——全部推进边的入口帧均落 `{备战帧 ∨ 补给选择画面}`:E4/E7/E9/E11/E13/E14 规则①落备战帧;E12 boss 依赖 boss 备战帧同序补录(E12 列「boss 备战帧规则① (p,9) 同序补录」);E8 弹窗族四类的后续入口:遭遇/投资策略/商店面板 → E9 回备战帧,补给 → E10「确认即完成节点,无后续本节点备战帧」→ 恰由补给选择画面承接(定义特例 `:164`);E10 divert 形态(备战帧先行)= 备战帧即入口。无误触发面:清单内非入口帧(备战环重入 E5、补给屏 revisit divert 形态后段)由水位 conjunction 中和(`effective > (boundary_settled_ord or 0)` 在已结后为假);开局补给误采形态被节点序排除(supply 不落 r1/r2,`cw_economy.py:511-512`)。引用修复如实:1.d 所引定义基准(`node-derivation.md:163-165` 含补给特例 :164)现与机制一致——特例被纳入入口清单而非被引用权威推翻 |
| N3 | **闭合** | design.md:24 `frame=f'p{(effective - 1) // 9 + 1}-r{(effective - 1) % 9 + 1}'` 已内联,全 src grep `frame_label` 仍零命中而现稿不再引用该符号;公式与 `node_ordinal_of`(`cw_game_state.py:233-236`,`(plane-1)*9+round_num`)严格互逆,与现值载体形态 `f'p{plane}-r{round}'`(`cw_loop.py:1923-1924/:1964-1965`)同形;None 路径安全:1.c 受 `advanced` 位闸住而 advanced 蕴含 effective 非 None(1.a 守卫),现码的 `else ''` 兜底分支在新形态下不可达、无需随迁 |
| N4 | **闭合** | ①水位三分支 ↔ 载体返回形态一一对应且完备:`settle_node_boundary_gold` 恰三种返回——金未读自跳 `written=False`(gold None,`cw_effect_inventory.py:1107-1110`)、合计零跳过 `written=False ∧ total<=0`(:1122-1127)、正常写 `written=True`(:1131-1134);design.md:35 三分支(written=True 落 / written=False∧total<=0 落 / written=False∧金未读不动+下入口帧重试)与三形态逐一对上,无第四形态(gold None 形态的 branch=''/total=0 亦被「金未读」支涵盖);landing 3.1 新增判据直锁两形态(`landing.md:14`「gold=None 帧:金结算跳过且水位不动;total<=0:水位照落」),原「首备战帧金未读永久漏结」的漏账通路被规格封死。②None 守卫与现码同窗语义吻合:design.md:34 三 None(node/streak/settlement)静默跳过 ↔ 现码闸 `_nd_tick is not None ∧ _sett_nb is not None ∧ _streak_nb is not None`(`cw_loop.py:1947-1950`,静默无告警)+ advance 侧 None 闸(:1900-1904),「与现码同窗同语义」申报与实码一致;landing `:15` 锁「静默跳过(无告警刷屏)、其余段照常」 |

## 新增发现

### R3-1 补给选择画面生产零喂入:N1 修复机制在实机永不触发,行为变化申报失实 + 验收判据假绿(重要,阻断定稿)

- 位置:design.md §2 方案 1.d(:27 入口帧清单第二析取支、:46 补给行为变化申报);landing.md 3.1(:13 补给判据)、3.2(接线范围)
- 问题:1.d 的补给特例结算要求「补给选择画面帧」流经 `observe_screen_context` 尾段,但生产链路无任何路径以 `screen_name='货币战争-补给'` 调用它:
  1. **漏斗画面名映射封闭**:`observe_screen_context` 的生产喂入唯一 = `read_game_state` 漏斗(`cw_observation.py:2695-2698`),画面名来自 `_phase_screen_context`(`:2719-2749`)——封闭映射仅产出备战帧(`:2740-2741`)/开商店面板(`:2742-2746`)/战斗等待 token(`:2747-2748`)/未知 None(`:2749`);`read_game_state` 的 `screen_name` 形参仅作失配豁免签名键、**不进上下文域**(`:2164-2170` docstring 明示)。权威正本自我申报同此:「0p 分支体无 read_game_state,**漏斗仅挂备战/商店/战斗三相位与 iter1**」(`node-derivation.md:232-233`);
  2. **分支写点不覆盖补给**:`_note_branch_screen`(`cw_loop.py:1010-1039`,写点 :1034)全部调用点仅五个开局链名(BOSS简报/位面过渡/简报/投资环境/等待1-1,:1499/1513/1543/1554/1572/1822/1843);
  3. **补给屏 op 零漏斗调用**:补给分支 dispatch `CwScreenSupplyNode`(`cw_loop.py:1383-1387`),该 op 全文无 `read_game_state`(grep 零命中;对 GameState 仅 `board_state_of` 写 chosen_supply/读决策,:187-196/:258-265),dispatch 包装亦零喂入(`:1079-1123`);其余全部 `read_game_state` 生产调用点的 phase/screen_name 均不出备战/商店/战斗三相位(cw_loop.py:551/1737、cw_screen_prep.py:3430、cw_screen_buy_cards.py:907/923、cw_observe_full.py:108/125/188)。
  - **后果**:①补给节点(自动弹标准形态)入口金结算实机恒不触发,水位对补给节点永滞后、金收入维持观察覆盖兜底——**与现码平价,无错误金面**,但 design.md:46 申报「从『永续观察覆盖兜底』变为『入口帧管线 logic 结算』」在生产不成立 = 行为变化申报失实(硬规则核三申报义务);②landing.md:13 补给判据按 3.1「直调单测」形态可用合成管线 pass 测绿,验收与生产行为脱钩(假绿);③附带面:弹窗腿的遭遇/投资策略/补给三触发面在现生产同为死面(仅开商店面板经 PHASE_PREP_SHOP_OPEN 活),本设计覆盖面申报(:43)按管线语义读法成立、不另立发现,但 1.d 补给承诺恰踩在同一喂入缺口上。
- 修法二选一(均为小改):**(i) 补喂入**——设计增补一条生产写点规格(如补给分支 dispatch 前以 `货币战争-补给` 调 `observe_screen_context`,与 `_note_branch_screen` 同形;prev=战斗等待 token ∈ 守卫族 → 弹窗腿同帧推进、尾段同帧结算,机制自洽),landing 3.2 文件面同步列 cw_loop;(ii) **收缩申报**——本迭代 supply 保持观察覆盖兜底,1.d 入口清单与 :46 申报改为「管线语义就绪(直调可测),生产生效挂喂入面批(M2 第二漏斗域)」,landing :13 判据显式标注合成帧定位。两案均消除「带开放问题定稿」。

### R3-2 1.d 前置守卫清单漏败局闸(killed=True),操作面失败路径规格不完整(次要)

- 位置:design.md §2 方案 1.d(:34 前置守卫)
- 问题:守卫清单只列三 None(node/streak/settlement),现码闸的第四条件 `_sett_nb.killed is True`(`cw_loop.py:1949`)未入 1.d 操作面。语义有钉死:§1 明确不解决「节点边界金结算口径(**败局保守闸**/宝钻透传 0 语义)保持现值」+ landing 3.1 判据⑤(killed=False → 跳过),文档整体可实现;但 1.d「守卫与水位落点(失败路径规格)」段自我呈现为完备失败路径规格——只读 1.d 的实现者会在败局帧调 settle,`round_start_income` 落 else→combat 发胜局收入且 written=True 水位落定(错误金面 + 永久账),判据⑤才能拦住。建议一行补进 :34 守卫清单(`settlement.value.killed is False → 静默跳过`),消除规格局部性缺口。
- 依据:`cw_loop.py:1945-1950`(现码四条件闸);design.md:34/§1 不解决清单;landing.md 判据⑤。

### R3-3 1.d 反解伪码与 helper 实签名不符:字面实现 TypeError(次要)

- 位置:design.md §2 方案 1.d(:29)
- 问题:`plane, round_num = _node_key_for_ord(effective)` 与 helper 实签名不符——实为 `_node_key_for_ord(ordinal: int, kind: str) -> NodeKey`(`cw_game_state.py:3240-3247`;**d95815ab8 时即此形态**,第二轮「可反解」核验未察):它**消费** kind、返回整键(NodeKey 为 frozen dataclass 不可二元解包,:507-515),伪码按字面实现即 TypeError。公式本体正确(与 `node_ordinal_of` :233-236 互逆、与 1.c 内联式同式);属符号方向描述失真非机制缺陷。建议改写为「`_node_key_for_ord(effective, node_type)` 取 `.plane`/`.round_num`」或直书公式。
- 依据:`cw_game_state.py:3240-3247/:507-515`;design.md:29。
- 附(环境注,非发现):R2 定稿基线 d95815ab8 之后入库的代码提交 44e91987a 使 design/landing 所引 `cw_game_state.py`/`cw_observation.py`/`cw_loop.py` 行号锚整体漂移(本报告已按现工作树重锚),落地审时按符号名定位,勿按行号判失实。

## 已核对无误清单

| 项 | 核对结果 |
|---|---|
| 修正提交面 | ✓ 019472b66 = 三轮修正(design/landing + README 链接 f884ee8a9);其后唯一代码提交 44e91987a(对账机制批)未触及本迭代设计语义面(四腿/载体/收入公式/economy 分支均未改,仅行号漂移) |
| 类型派生段序(N1a) | ✓ `observe_screen_context` 固定次序:上下文对(:3077-3083)→ 顶栏观察层(:3085-3086)→ 四腿(:3089-3106)→ 类型派生(:3107-3116,方法体末段);效果段插入位(类型派生后、返回前)成立 |
| supply 直定 | ✓ `SCREEN_NODE_TYPE_DIRECT['货币战争-补给']='supply'`(:225-230);`_write_derived_node_type` 写 `bs.node` 镜像 kind(kernel :3140-3149 docstring + 类型派生调用 :3113-3116) |
| 载体三形态(N4) | ✓ `cw_effect_inventory.py:1107-1110/1122-1127/1131-1134` 与 design 三分支一一对应;`NodeBoundarySettlement` 六字段 :1067-1077 |
| 现码闸(N4 对照) | ✓ `cw_loop.py:1947-1950` 四条件(None/None/killed=True/None)静默跳过;:1900-1904 advance None 禁令原样在位(F2 修正面未回退) |
| 18 边全景对照(N2) | ✓ E1-E18(`node-derivation.md:105-124`)逐边核对:推进边入口帧全覆盖、无误触发面(见核验表 N2 行) |
| 收入语义(平价) | ✓ `round_start_income` supply 分支 `cw_economy.py:515-518`(base=平面感知键、streak=0);else→combat :528-531(F5 关闭面未回退);supply 不落 r1/r2 :511-512 |
| frame 现值形态(N3) | ✓ `cw_loop.py:1923-1924/:1964-1965` `f'p{plane}-r{round}'`;grant 签名收 frame 形参 |
| landing 3.1 判据增补 | ✓ :13(补给入口)/:14(gold=None 水位不动、total<=0 照落)/:15(三 None 静默)三条新增,与 N4/N1 修正面一一对应(:13 的可达性缺陷归 R3-1) |
| 反解公式自洽 | ✓ `_node_key_for_ord` 反解式(`:3243-3246`)与 `node_ordinal_of`(`:233-236`)同式互逆;`effective_node_ord`(:3152-3163)max 派生、None 安全 |
