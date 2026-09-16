# 设计对抗报告·第二轮:效果账本自推进迁移

> 攻击规范:`docs/develop/harness/iteration-design.md` §7(三核)/§5(写作硬规则三条)。
> 被攻击文本 = 同目录 design.md / landing.md / README.md,提交 d95815ab8(git log 实证为现 HEAD;
> 该提交只动 4 个文档文件,源码未动,故第一轮已核对的代码锚继续有效)。所有行号为本轮工作树实测。

## 结论

**打回**:无致命残留——F1/F2 的错误金面与 None 推进两处致命根已真实闭合(修正稿方案机制成立);但 1.d 金结算规格的操作面攻出三条重要新发现(N1 补给特例与递延机制冲突且引用失实/N2 形式触发条件缺备战帧闸且同条自相矛盾/N4 结算成功判据与参数求值失败路径未规格化,其中 N4 的一支自然实现会在首备战帧金未读形态永久漏结该节点金收入),按「带开放问题的定稿不存在」门槛(§6)未收敛——修正面集中在 1.d 一节,小改后可过。

## F1-F12 闭合核验表

| # | 判定 | 证据 |
|---|---|---|
| F1 | **闭合** | 四参来源全部定死且不再依赖节点镜像定窗:①`plane, round_num = _node_key_for_ord(effective)` 反解——函数实测存在且可反解(`cw_game_state.py:3183-3189`,`plane=(ordinal-1)//9+1, round_num=(ordinal-1)%9+1`,与正解 `node_ordinal_of :226-229` 同式自洽);②`node_type = self.node.value.kind` 显式申报保持镜像现值(与现码 `cw_loop.py:1953` 同源,非自然实现而是定死);③`streak = int(max(0, self.streak.value))` 定死;④倍率/息 = 提供方。0q 场景的错窗根((p+1,1) 帧读 (p,9,'boss') 的 plane/round)被反解消除,弹窗腿场景由递延机制承接。残余:递延闸未进形式条件、kind 镜像读与「禁读镜像」矛盾句并存 → N2(新发现,不回退本条判定) |
| F2 | **闭合** | `effective is None → 整段跳过` 写进管线段操作规格(design §2 1.a 第一句),禁令语义显式随迁(「语义 = 现码 `cw_loop.py:1895-1899` 禁令」,实测该行号恰为 None 守卫注释+短路初始化+条件,吻合);行为变化申报独立一条「守卫随迁保留(非废除)」;landing 3.1 判据①直测 None 帧(账本零推进零发放)。现码禁令实测仍在 `cw_loop.py:1895-1901`,申报与代码事实一致 |
| F3 | **闭合** | ①陈旧锚已移除:现稿 1.a 不再引 `cw_effect_inventory.py:240-254`,改引 `cw_loop.py:1895-1899`(实测吻合,见 F2);②目标态引用改指 `node-derivation.md` §3.3 规则六并带行号 `:302-313`——实测 302-313 恰为规则六全文(含迁移三面原文 `:309-310`),§0 同步改指同处。effect-domain.md 失实章节引用已从正文消失 |
| F4 | **合规关闭(申报)** | §1 明确不解决首条申报计数器退役挂效果域批 M3、双权威窗分叉风险登记;申报真实性核对:M3 批位在两处**活正本**在册——`node-derivation.md:310`(「迁移三面……挂 §3.7.2-M3 差异清单,批位 = 效果域设计定稿后的实施批」)、`strategy-env-impacts.md:97`(同文)。备注:差异清单本体住已删设计件,但正本自身如实标注「(已删,git 可溯)」,指针链诚实,不判失实 |
| F5 | **闭合** | kind 闸已撤:1.d 显式「**不设 kind 闸**:round_start_income 对未知/空 kind 落 else→combat 落袋是现值语义(anchor `cw_economy.py:528-531` 实测吻合——else 分支恰在 528-531),加闸 = 收入语义变化」;「kind 可知」定义问题随闸撤除消解;landing 3.1 判据⑦锁定空串照传非跳过。与现码无 kind 闸(`cw_loop.py:1942-1945` 四条件无 kind)一致 |
| F6 | **闭合** | 注册点单一定义:design §2 方案 2「生产注册点唯一 = ctx 级一次性注册(应用装配完成后;provider 闭包动态读 ctx.cw_match——恢复局 cw_match 在场即正常供参)」+ **显式排除**「禁止挂开局链初始化(恢复接管局不走开局链,挂那里 = 恢复局整局金结算静默缺失)」;landing 3.2 表述一致,二义消除。残余备注:注册点所在文件未点名(「应用装配」),单文件可实现面内可定位,不构成二义 |
| F7 | **闭合** | 原子切换三处一致:design §1「cw_loop tick 块删除(与管线接线**同一提交原子切换**,防双驱动窗口)」;landing 卷首拆分原则 + 3.1 范围明确「未接入 observe_screen_context」+ 3.2 即「原子切换(同一提交)」;弹窗腿双发判据存在:landing 3.2「F7 双驱动回归:弹窗腿先推进形态单测——后续备战帧结算恰一次、账本余期/刷新无双扣」 |
| F8 | **闭合** | 行为变化申报新增「日志形状」条:两行旧标签消失+新标签全文列出(与现码实测一致:`[cw-loop] 节点边界金结算…` 在 `cw_loop.py:1961-1966`、`[cw-loop] 效果账本 tick 失败(不阻塞)` 在 `:1968-1969`);到期留证行语义不变(1.b「[cw!][effect] 效果到期移除」与现码 `:1902-1905` 逐字一致);landing 3.3 重写为哨兵影响面核对而非「无节奏变化」申报。核对结论真实性实测:`LOOP_PREFIXES = ('[cw][director]', '[cw-loop]', '[cw][battle]', '[cw-deploy]')`(`skills/sr-od-currency-war-dev/scripts/cw_sentinel.py:247`)不含 `[cw][effect]`;HIT 词表(`:209-218`/`:221`)亦不含——「无哨兵语义影响」成立(备注:金结算成功行原属 LOOP 白名单计数面,新标签退出计数集,该行每节点 1 条、远低于 LOOP_N=10 阈值,无实质影响) |
| F9 | **闭合** | 判据①-⑦逐项对上第一轮盲区:None 帧(①)、备战帧推进(②)、错窗防护(③:written/branch/income_total 与反解键一致,锚 `NodeBoundarySettlement` 实测 `cw_effect_inventory.py:1067-1085`)、同序幂等(④)、killed=False(⑤)、提供方缺位(⑥)、kind 空串(⑦);3.2 另加 0q 错窗回归与 F7 双驱动回归两条集成判据 |
| F10 | **闭合** | 「设计 §8.4 备战帧观察后调用」悬空引用已从正文移除(现稿 1.a 改引现码行号);§1 不解决清单新增「旧设计件悬空指针全局清理不解决(本迭代仅保证新增文本不新增悬空引用)」的自我约束。抽查现稿全部新增引用:唯一悬空 = `frame_label` → N3 |
| F11 | **闭合** | 清单改为合并步**整步删除**并申报理由:「心跳采样半句已随先行提交(删除观察断流心跳采样)从代码移除」——实测成立:全 src `heartbeat(` 仅剩定义(`cw_game_state.py:3063`),生产零调用点;`outer_loop.md:91` 合并步仍在,整步删除语义正确,不再误伤(心跳采样已无代码对应物) |
| F12 | **未闭合(半)** | ②streak 归一已定死:`int(max(0, self.streak.value))`(符号归一保留现值)——闭合;①frame 值未闭合(换形):省略号改为 `frame=frame_label(effective)`,但 `frame_label` 全 src grep 零命中——悬空符号替代了省略号,值语义(`f'p{(o-1)//9+1}-r{(o-1)%9+1}'`)可推导但函数未定义也未声明为新增辅助,实现者仍须拍板 → N3 |

计数:闭合 9 / 合规关闭 1 / 未闭合 2(F12 为半闭合,残余归 N3)。

## 新增面发现清单

### N1 补给节点特例与递延机制冲突:引用的定义基准恰含推翻该机制特例的条款,补给收入结构性排除出 live 写端收口且未申报(重要)

- 位置:design.md §2 方案 1.d
- 问题:1.d 的递延机制 = 「金结算递延到该节点的**首个备战帧**」,并引「节点入口定义本尊,`node-derivation.md` §3.3 定义基准」背书。但该定义基准原文是:「**补给节点特例 = 补给选择画面即节点入口**(无备战画面)」(`node-derivation.md:164`,映射表 `:176`「补给节点无备战画面,补给选择画面即节点入口(定义特例)」)——**「备战帧 = 节点入口」对补给节点恰好为假**,设计引用的权威恰好含推翻自己的特例条款。后果:补给节点(标准形态)无备战帧 → 递延条件永不被满足 → `round_start_income` 的 supply 分支(base = 平面感知键,`cw_economy.py:515-518`)所对应的节点边界金**永不发生 logic 写**,永续观察覆盖兜底;唯一 kind='supply' 新鲜且 effective 对位的帧(补给屏帧自身:弹窗腿推进 + 类型直定同批,`SCREEN_CONTEXT_POPUP_FAMILY:169` 与 `SCREEN_NODE_TYPE_DIRECT:220` 实测均在)被递延机制跳过。与现码对齐性:现码 tick 同样只在备战分支触发,补给节点同样从不 logic 结算——**无数值回归,平价**;但①依据失实(硬规则 1:引用权威背书一个该权威否定的机制);②「节点边界金结算」的收口主张静默排除 supply 分支而 `NodeBoundarySettlement.branch` 明列 supply(`cw_effect_inventory.py:1071`),该不对称未进行为变化申报也未进明确不解决清单。
- 依据:`node-derivation.md:161-180`(定义基准+特例)、`cw_economy.py:515-518`(supply 分支)、`cw_game_state.py:166-171/218-223`(补给屏双注册)、design.md §2 1.d/行为变化申报。

### N2 1.d 操作规格两处缺陷:形式触发条件缺「备战帧」闸(字面实现 = F1 复发)+「禁读镜像」与镜像 kind 读同条自相矛盾(重要)

- 位置:design.md §2 方案 1.d
- 问题:①形式条件只写「触发条件 = `effective > (self.boundary_settled_ord or 0)`」;「递延到首个备战帧」的闸住在「理由:」段内。弹窗腿/0q 推进帧上该条件**同样为真**(effective 已跳到新节点、水位未落),若实现者按形式条件字面实现(不加床帧闸),0q 帧上即以反解 (p+1,1) + 继承陈旧 kind('boss') 结算——F1 的错窗金结算换参复发,且水位落地后永久错窗。整段通读可复原正确机制,但操作条件行呈现为完备条件,属规格精度缺陷。②同条开头加粗「参数源**全部派生层,禁读节点镜像**」,两行之下「node_type = self.node.value.kind(镜像现值……与现码同源同语义)」——kind 恰是镜像读,自相矛盾;应表述为「(plane, round) 切派生层反解,kind 保持镜像现值」。特定条款优先可解,但加粗禁令与白纸黑字的违例并置,实现者必停手或拍板(硬规则 2)。
- 依据:design.md §2 1.d 原文;`cw_observation.py:2520-2527`(kind 继承,0q 帧上镜像 kind = 上一节点)。

### N3 `frame_label` 为新增悬空符号,违反设计自设的「新增文本不新增悬空引用」约束(次要)

- 位置:design.md §2 方案 1.c
- 问题:`grant_effect_node_refresh_balance(self, frame=frame_label(effective))`——`frame_label` 全 src grep 零命中,既非现有函数也未声明为本迭代新增辅助。第一轮 F10 同类悬空引用判次要,F12① 的省略号换成了悬空符号,属换形未闭合;且 design §1 不解决清单自设「本迭代仅保证新增文本不新增悬空引用」,本处直接违反自设约束。载体现值 = 调用点内联 f-string(`cw_loop.py:1918`),序值形态需先反解,设计应写明「按 `_node_key_for_ord` 反解后取现值 f-string 形态」或声明新增辅助函数。
- 依据:design.md §2 1.c;grep `frame_label` 全 src 零命中;`cw_loop.py:1916-1919`(现值)。

### N4 1.d 失败路径零规格:「结算成功」判据未定义(一支自然实现 = 首备战帧金未读形态永久漏结节点金收入)、镜像/streak None 直接求值崩溃(重要)

- 位置:design.md §2 方案 1.d;landing.md 3.1 判据①-⑦
- 问题:三处失败路径无规格,实现者须自行拍板,其中一支自然实现产生真实漏账:
  1. **「结算成功 → 落 boundary_settled_ord」的「成功」未对齐载体返回值**。载体 `written=False` 有两形态:金未读自跳(`cw_effect_inventory.py:1107-1110`)与合计零跳过(`:1098-1101`)。若实现者把「结算流程执行完毕」当成功而落水位:首备战帧金未读(观察面存在 gold carry 分支,`cw_observation.py:2529-2534`)时 written=False 零写入但水位=effective → **该节点金收入永久漏结**(下帧金可读亦不补,水位已平)。另一支自然实现(written=True 才落)则逐帧重试——两支行为不同且设计未裁决。判据③-⑥均无此形态。
  2. **`node_type = self.node.value.kind` 无 None 守卫**:effective 非 None 而 `node.value` 为 None 可达(开局「等待期商店面板先被采到」弹窗腿候选 1,`node-derivation.md` §3.6 S1;镜像首读前漏斗不写镜像,`cw_observation.py:2528`「无现值且未读 → 不写」)→ 自然实现 AttributeError,被 1.f 兜住后每观察帧重试告警(开局段可达数十条 warning,现码同窗为静默跳过,`cw_loop.py:1942` `_nd_tick is not None` 闸)——运行面回归 + 行为变化申报未列。
  3. **`streak = int(max(0, self.streak.value))` 无 None 守卫**:streak 不可知时 TypeError,同 2 被兜住刷告警;现码闸显式要求 `_streak_nb is not None`(`cw_loop.py:1945`)。
  landing 3.1 判据①只测 effective=None,①-⑦无一覆盖「effective 非 None 而镜像/streak 缺位」与「written=False 时水位落不落」。
- 依据:`cw_effect_inventory.py:1098-1110`(written=False 两形态)、`cw_observation.py:2528-2534`(镜像不写/gold carry)、`cw_loop.py:1942-1945`(现码 None 闸)、design.md §2 1.d/1.f、landing.md 3.1。

## 已核对无误清单

| 项 | 核对结果 |
|---|---|
| 修正稿版本 | ✓ d95815ab8 = 现工作树 HEAD(git log 实证);该提交仅动 4 个文档文件,源码未动,第一轮代码锚继续有效 |
| `_node_key_for_ord` | ✓ 存在且可反解:`cw_game_state.py:3183-3189`,与 `node_ordinal_of`(`:226-229`)同式自洽 |
| `effective_node_ord` | ✓ `:3095-3106`,max 派生计算非存储,None 安全(双空 = None) |
| 四腿在产(非死代码) | ✓ 四腿本体 `cw_game_state.py:3109/3144/3223/3258`;`observe_screen_context` 固定次序调用 `:3032-3049`(类型派生 `:3053-3059`,尾段插入位成立);生产喂入 = 漏斗 `cw_observation.py:2682-2685`,`read_game_state` 调用点 5 处在产(`cw_loop.py:547/1732`、`cw_screen_buy_cards.py:907/922`、`cw_observe_full.py:105/120/182`、`cw_match_recorder.py:80`) |
| F2 前提复验 | ✓ `advance_node` None 旁路去重与登记守卫:`cw_effect_inventory.py:346-348/353-355` |
| 结算载体 | ✓ `settle_node_boundary_gold` 签名 `:1080-1085`;`NodeBoundarySettlement` 六字段 `:1067-1077`(判据③锚成立);金未读自跳 `:1107-1110` |
| 收入单一源 | ✓ `round_start_income` 四分支派发 `cw_economy.py:515-531`(supply/reward/loss_comp/else→combat;F5/N1 anchor 吻合) |
| 现码 tick 块 | ✓ `cw_loop.py:1885-1969`:None 禁令 1895-1901、五动作逐项在位、无 kind 闸 1942-1945、streak 归一 1954、金 log.info 1961-1966、失败 warning 1968-1969(申报的两行旧标签逐字吻合) |
| 哨兵核对(landing 3.3) | ✓ `LOOP_PREFIXES`(`cw_sentinel.py:247`)不含 `[cw][effect]`;HIT_EXIT/HIT_CONT(`:209-218/:221`)不含;`[cw][effect] 效果推进段失败` 不含『执行失败』子串,不触 HIT |
| F11 前提 | ✓ 全 src `heartbeat()` 生产零调用(仅定义 `cw_game_state.py:3063`);`outer_loop.md:91` 合并步仍在 |
| node-derivation.md 锚 | ✓ §① 四规则组/同坐标系 `:60-78`;§3.3 定义基准 `:161-180`(含补给特例 `:164/:176`——N1 的依据);规则六+迁移三面+M3 挂账 `:302-313` |
| M3 在册 | ✓ `node-derivation.md:310` + `strategy-env-impacts.md:97` 两处活正本登记批位(F4) |
| 双水位新工程字段形态 | ✓ 「非 Field,同 node_hist_ord 形态」:node_hist_ord 实为普通属性直赋(`:3141/3180/3255/3291`),形态引用准确;`boundary_settled_ord`/`register_boundary_economy_provider` 全仓 grep 零命中 = 待实现新面,与 3.1「未接线落地」一致 |
| 新面 3(链式弹窗每帧调用开销) | ✓ 非问题:`advance_node` 同序去重 O(1) 早退(`:346-347`);`project_effect_capacity` 幂等提前返回(`cw_game_state.py:1200-1201`,现值零容量条目 → 恒 no-op);`effective_node_ord` = 两整数取 max。备注:两桥 docstring 的采样点描述(「cw_loop 备战分支」)随 3.2 落码须同步改写,属实现批内代码注释义务,非清单缺漏 |
| 新面 2(递延窗失败/重启) | ✓ 与现码平价,无永久漏/重:水位均为内存态(非 Field),停机重启双丢 → 恢复局首节点 settlement/streak 缺位跳过 = 现码同值(第一轮附 2 结论沿用);重启后同节点重复结算面为现码共面(现码无任何跨重启去重),且金值受观察覆盖辖、失配自愈 |
| 新面 5(两水位 0q 跳变分叉) | ✓ 非问题:分叉即设计本意(推进≠结算,`_last_tick_node` 管推进幂等、`boundary_settled_ord` 管结算恰一次);effective 单调(腿级倒退免疫),无互相污染路径 |
| 新面 4(终局 cw_match=None 窗) | ✓ 非问题:漏斗 None 守卫(`cw_observation.py:2497-2498` `_match is not None` → session None → 容器块整体跳过)——cw_match=None 后管线根本不被调用;`cw_match=None` 写点(`cw_loop.py:1607/1672`)均为大厅回返路径,终局前最后节点的备战帧结算发生在 cw_match 在场时;终局后无腿触发(结算/结果屏不在弹窗族,末位面胜即局终无 0q),不存在「终局前最后一节点金结算被跳过」窗口 |
| 治本(核三) | ✓ §2 对迁移三面①②治本、③合规申报缓征(F4);修正稿对第一轮致命两根的修法(参数源反解+递延水位/None 整段跳过)均在根上,非症状补丁;新增机制(双水位)与 F1/F7 两根一一对应,关键取舍段如实记录放弃项及理由 |
| 规范遵循(核二) | ✓ 四节齐、landing 阶段七件齐、无过程叙事措辞(「对抗审一轮打回,本稿为修正稿」一句居 §0 状态行,属状态声明非叙事)、README 进度合规;违例集中为硬规则 1(N1 权威失实)与硬规则 2(N2/N3/N4 未定语义) |
