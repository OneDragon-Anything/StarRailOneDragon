# 晶矿奖励附着通道 · 设计对抗审查报告(第五轮·定点复审)

> 复审范围 = 第四轮发现触碰面(P1 事件①快照对拍机制 / Z1-Z3 整改 / B1-B5 备注采纳 / 本轮触碰段落的交互),其余部分第四轮已确认收敛,不重攻。核验基准 = 第四轮报告(本文件上一版,结论已归档至 git 历史)。

## ① 结论

**打回(定点,一处)**——P1 的机制方向修订正确(「帧首快照对拍」与代码事实一致、observe_full 漏斗写点/锚定序号语义/live 写点全集全部核验属实),Z1-Z3、B1-B5 均已落实。但 **§5 前值载体的「快照」存在两种互斥读法,文本未定死**:按「快照时点 = observe_full 调用之前」读 = 帧内现读 gs 现值(机制全场景闭合);按「照 `_prev_spheres_raw` 先例的 op 成员帧间快照 + 跨环重触发由幂等守卫吸收」读 = 跨帧成员记忆(**live 声明金系统性超发**,plane 1 最多 3 次发放 18 金 vs 真值 6,sim 侧窗口守卫不超发 → live/sim 分歧,与第四轮 P1 同等危害)。先例引证天然导向错误形态,实现者按文档照先例写即错。须把快照载体一句话定死(修法见 N1)后定稿;其余残留均为半句级(Z3 引证失实、Z2 清单半句、B3 枚举序半句),随修订顺手带上。

## ② P1/Z/B 逐条核验表

### P1 事件①「帧首快照对拍」修复核验——**方向正确,载体未定死(见 N1)**

核验分四步,代码证据全部亲核:

**(a) 机制叙述与代码事实一致性——通过**:

| 设计断言(channel §5) | 代码实况 | 判定 |
|---|---|---|
| 快照时点 = observe_full 调用之前(heavy 帧);判定点 = 回执后、spheres 写前 | cw_screen_prep.py `_observe` heavy 段:observe_full 调用 :240 → observe_node_anchor :283-288 → spheres 观察 :384-391,次序与文档一致 | ✅ |
| 节点域 plane 写点在 observe_full 内的 read_game_state 漏斗,回执后 gs.node 已是新值 | cw_observe_full.py :123/:140(gold 重读)/:207 调 read_game_state;cw_observation.py :2596-2599(node_type 读到直写)与 :2601-2607(kind 继承写)两分支都写 `gs.observe(gs.node, NodeKey(plane=…))`——plane 真读更新 | ✅ |
| 「锚定写前现值 = 旧 plane」不成立;observe_node_anchor 锚的是序号、不更新 plane | cw_game_state.py :3501-3545:observe_node_anchor 只写 `gs.node_ord`(v==v 分支 :3538 `gs._swap('node_ord', …)`;advance 分支经 advance_node_effective :3377-3408,只写 node_ord :3402/:3404 + node_hist_ord :3405-3406),全路径不触 `gs.node` | ✅ |
| `_prev_spheres_raw` 先例 = op 成员、每备战环重建、环内连续帧 | cw_screen_prep.py :199-203(帧末存本帧原始读数、下帧消费);cw_loop.py :1735-1737 每次备战分发 `CwScreenPrep(self.ctx)` 新建实例 | ✅(但先例语义 = **跨帧记忆**,与快照对拍所需语义相反——见 N1) |
| design §2 第 3 条同步版 | 「op 成员帧首快照对拍 plane 边沿 + 漏斗写点回执后检测 + 入队先于同帧 spheres 写」,与 §5 同口径、与代码一致;但「op 成员」一词继承 §5 载体歧义 | ⚠ 随 N1 连带修 |
| landing 3.4 测试构造约束 | test_cw_prep_node_row_housekeeping.py :173-218 现行形态属实:monkeypatch observe_full(:199),fake 只回 read_receipt **不写 gs.node**(:190-197),node 由测试预摆(:187-188)——「fake 必须真实写 node(或走真漏斗)」约束真实必要 | ✅ |
| sig 形态(live = logic_hook 族) | cw_game_state.py write_logic/write_logic_rand 的 sig 族校验含 logic_hook(第四轮核验表 #28 维持,本轮触碰面未变) | ✅ |

**(b) 快照对拍机制自身推演——通过的部分**:

- **heavy/light 节律不漏边沿**:observe_full 生产调用方全集 = 仅 cw_screen_prep.py:240(tier='heavy',grep 全仓唯一生产调用);light 帧不调 → gs.node 不更新;live 侧 spheres 的 gs 写端也在 heavy 段内(:379-391,light 段只现读不落 gs)。位面变化必经节点推进/画面切换 → 新备战环 = 新 op 实例,环首帧 = 画面 op 入口 heavy 观察 → 快照对拍必覆盖每次位面变化。环内 plane 恒定(推进即画面切换、环结束),无边沿可漏。✅
- **gs.node 生产写点全集排查**(帧首快照可靠性的前提):read_game_state 漏斗之外无写点。三个非备战调用方逐一排除——cw_loop.py :1520-1526(仅 `iter==1 ∧ _is_new_match` 的 battle_or_transit 抢读,局首帧专用,不落在位面过渡期;其对 run 首帧的影响 = node 被抢写非 None → 备战首帧无边沿 → **plane 1 声明由事件②入队兜住,恰为设计「事件②兜序」断言的主路径**,闭合);cw_screen_shop.py :132-134(phase=prep_shop_open,商店子态帧,plane 不变);cw_match_recorder.py :18/:80(独立进程入口,进程隔离不触生产局容器)。cw_screen_battle_wait.py :368 只 read_phase_round 纯读;cw_screen_report/plane_transition.py :62-65 只写 node_path 族;cw_game_state.py :4054-4065 为一次性投影容器(独立实例)。✅ **位面过渡期间 gs.node 保持旧 plane,直至新位面首个备战 heavy 帧被漏斗更新——快照对拍的边沿检出前提成立。**
- **事件①/②互吸无双发**:同帧双触发时两事件共用守卫「该 (env,plane) 无在队条目」,先到者入队、后到者被拦(同帧内条目必在队),单条入队确定。✅
- **次序硬约束**:「observe_full(:240)→ 锚定(:284)→ spheres 写(:384)」现序天然满足,接线点固定在回执后即可;「入队先于同帧 spheres 写」承载性(首帧新现即含声明附着)由 landing 3.4 位面过渡帧判据锁住。✅
- **observe_full 内部 gold 重读**(:140,重新截图):重写发生在 observe_full 之内 → 属「回执后已落」范畴,对拍语义不变。✅

**(c) 未通过的部分——载体形态歧义导致超发**:见 N1(③新发现首条)。

### Z1-Z3 整改核验

| # | 修订落点 | 代码证据 | 判定 |
|---|---|---|---|
| Z1 审计行补 ore_declared_pending | ore-click-consume §3 末段:「新增 `ore_declared_pending` 域行:logic 写端 = 入队/消费/过期三口(同族行先例 = pending_item_grants),值语义 = 卡文推算登记非观察投影」 | cw_projection_audit.py :207-211 pending_item_grants 行(AUDIT_PROCESS_ONLY;「唯一逻辑写端 = 入队/消费回写,队列 = 卡文推算知识,无观察读端」)行形态属实;「三口」聚合表述完整覆盖四写点(事件①/②/sim 窗口起点入队 → 「入队」口;挂接入口出队 → 「消费」口;位面过渡过期 → 「过期」口) | ✅ 落实,无残留 |
| Z2 正本清单补 projection_contract.md | landing 正本更新清单第 3 条(:76):「flow/projection_contract.md:状态面板表逐域列举 GameState——补 ore_rewards / ore_declared_pending 两域行 ← 3.1」 | 条目已入清单 ✅;但残留两小缺口:① Z2 建议原文含「+ spheres 写端挂接说明」,修订丢失——正本该表 :19 行「晶矿域 OreSight.points 载点击坐标」在本迭代后语义不完整(附着值独立域 + spheres 写端唯一入口 = 挂接入口),失真残留;②「两域行」与正本表形态失配:该表为「层/载体/角色/关键契约」四列表,GameState 单行、域语义在关键契约列内嵌,无域级行可「补」 | ⚠ 半句级残留(见 N3) |
| Z3 常量公开化重命名 + lazy import 定形 | channel §4 步序 3「公开化重命名为 SPHERE_PERSIST_POS_TOL,kernel 在函数体内 lazy import 公开名;禁复制数值」+ design §2 契约「公开化供 kernel 函数内 lazy 引用」+ landing 3.1 文件面「含模块内引用点同步;kernel 侧函数体内 lazy import」——三方一致 ✅;方案本身(函数内 lazy import)技术可行、方向正确(避免模块级反向边) | cw_identity_obs.py :1434(`_SPHERE_PERSIST_POS_TOL`)/:1465(filter_persistent_ores 默认参数消费点,重命名须同步,landing 已写)属实;**但「lazy 先例 = cw_encounter_selection.py:39」引证失实**:该行位于 `if TYPE_CHECKING:` 块内(:35 起),运行时不执行,是类型注解专用导入;kernel 桶运行时导入 obs = 零先例(grep 全 kernel 桶仅此一处 obs import 且为 TYPE_CHECKING)。「会成环」亦措辞过强(cw_ore_channel → cw_identity_obs → cw_game_state 不必然成环;实害 = obs→kernel 单向分层被破) | ⚠ 方案定形 ✅,先例引证失实(见 N2) |

### B1-B5 备注采纳核验

| # | 修订落点 | 代码证据 | 判定 |
|---|---|---|---|
| B1 r 值补齐 | ore-sim §2:「半径 r = 10 与面板矿同,points 四元组齐整」 | cw_sim_backend.py :553-559 面板矿 r=10(`(color, i*10, 10, 10)`)属实;排序消费 = cw_prep_actions.py :61-62(r 降序大优先) | ✅ 落实 |
| B2 同长前提 | design §2 注册表契约 + channel §2 校验:「非空时**长度相等且逐位同值**」 | cw_investments.py :1176 `gold_per_plane_start=(6, 8, 12)` 长度 3,前提句已补 | ✅ 落实 |
| B3 平局打破定死 | channel §4:「距离平局 = 旧列序稳定优先,禁随机」 | 主语义(确定、稳定、无随机)已定,替换了「任取」歧义措辞 ✅;残留:「稳定」无附着点——候选对枚举序未定义,无序枚举(如 set)下「旧列序稳定优先」无意义 | ⚠ 半句级残留(见 N4) |
| B4「均检查」措辞 | ore-sim §2:「备战档呈现(battle/reward → SCREEN_PREP 分支)**均检查** ore_declared_pending 当前 plane 条目(无额外『首帧判定』状态——出队即消费,后续呈现自然无声明矿)」 | 措辞改为逐帧检查 + 机制理由写明,「首个」的状态机误读消除 | ✅ 落实 |
| B5 声明不改 | ore-click-consume §2 双层防线表述与 design §2 第 6 条维持原样 | 无动作 = 第四轮裁定(记录在案,不阻塞) | ✅ 按裁定 |

### 修订交互快攻(本轮触碰段落互洽)

- §5 三段(前值载体/事件①/事件②)内部:判定点统一(回执后、spheres 写前)、事件②段「gs.node.value 为 None → 本帧两事件都不触发」守卫覆盖事件①现值侧、互吸与守卫口径一致——除 N1 载体歧义外互洽。
- design ↔ channel ↔ landing 三方同步:快照对拍口径、「入队先于 spheres 写」次序、sig 形态、常量公开化三方一致;design §2 第 3 条「op 成员」与 landing 3.4 判据继承 §5 载体歧义(N1 修复须三处连带)。
- Z3 改动对 3.1 文件面/判据的传导:文件面(重命名 + 引用点同步 + lazy import)与 §4/design 一致;3.1 判据「轨迹继承(坐标漂移 ≤12px 连续两帧)」消费容差值,不依赖常量名,传导无缺口。

## ③ 新发现(仅限本轮触碰面)

### N1【打回·P1 残留】快照载体存在两种互斥读法——照先例实现 = live 声明金系统性超发

**问题**:channel §5 前值载体段同时给出两句互相矛盾的载体定义:

- 句 A(正确形态):「**快照时点 = `observe_full` 调用之前**(heavy 帧)……回执后检测」——快照 = 帧内现读 `gs.node.value` / `gs.active_env.value`(局部变量即可),对拍 = 该快照 vs 回执后现值。
- 句 B(失效形态):「`CwScreenPrep` 增 `_prev_node_plane`……(**照 `_prev_spheres_raw` 先例**,op 成员**帧间快照**)」「**跨环重触发由幂等守卫吸收**」——`_prev_spheres_raw` 的实际用法(cw_screen_prep.py :199-203)是**帧末存本帧读数、下一帧消费**的跨帧记忆;照此先例实现 `_prev_node_plane` = op 成员跨帧记忆。

**机制推演(两种形态分岔)**:

- 形态 A(帧内现读):快照源 = gs 现值,gs 跨备战环持久(cw_loop.py :1735-1737 每环新建的是 op,不是 gs)→ 同位面跨环首帧快照 = 上环 plane,对拍恒等、无边沿、**不重入队**;位面过渡环首帧快照 = 旧 plane vs 回执新 plane → 边沿检出。全场景闭合(run 首帧 None 互吸、iter1 抢读由事件②兜、light 帧无干扰——见 ②(b) 推演)。此形态下 op 成员**根本不需要**(帧首读、回执后用,同一函数作用域)。
- 形态 B(跨帧成员记忆):op 每备战环新建 → 环首帧 `_prev_node_plane`/`_prev_env` 必为初始值(None/'')→ 每环首帧「视为边沿」。幂等守卫「该 (env,plane) 无在队条目」拦不住跨环重入队:**上一环的条目已被挂接入口消费出队(消费即移除),守卫前提(条目在队)已不存在**。以增发货币、P1 节点序列(reward, reward, battle, battle, supply, battle, encounter, reward, boss——cw_node_schedule.py :28-31)逐环推演:节点 1 环入队 (env,1) → 消费,6 金附着 ✅;节点 2 环(reward,8 面板矿新现)首帧视为边沿 → 重入队 → 生成集非空 → 再消费 → **第二个 6 金** ❌;节点 3(battle)环重入队留队(生成集空),节点 4-7 守卫拦(在队);节点 8(reward)生成时出队 → **第三个 6 金** ❌。**plane 1 合计 18 金 vs 真值 6。** plane 2 碰巧只发一次(中途入队条目恰在唯一 reward 节点被消费),但机制同病。
- **live/sim 分歧**:sim 侧入队守卫 = `_window_begun_ord` 窗口幂等(位面过渡点/直进节点共用、重放不双发,cw_sim_backend.py 窗口起点序),窗口级去重不超发 → 形态 B 的 live 系统性多发直接击穿总纲「live 与 sim 同一生成函数、同一随机态写径」的目标——与第四轮 P1 同等危害形态。
- 文本证据表明设计心智偏向形态 B:「跨环重触发由幂等守卫吸收」这句**只在形态 B 下有指涉**(形态 A 跨环根本不重触发),且该断言在形态 B 下为假(消费即移除销毁守卫前提)。design §2 第 3 条「op 成员帧首快照」、landing 3.4(判据未点名跨环构造)同步继承歧义。
- **测试拦不住形态 B**:landing 3.4「同位面不双入队」判据未写明须以跨环形态(新 op 实例 + gs.node 保留上环 plane)构造;按同环连续帧构造,形态 B 也绿。fake observe_full 约束(真实写 node)只钉死时序面,钉不住载体面。

**建议修法**(一句话定死,三处连带):

- channel §5 前值载体段:快照 = `observe_full` 调用前**帧内现读** `gs.node.value`(plane)/`gs.active_env.value`(env),局部变量承载,**不设 op 成员、不照 `_prev_spheres_raw` 先例**(该先例是跨帧记忆,语义相反);「快照 None 视为边沿」仅覆盖 `gs.node` 无现值(run 首帧/恢复局,plane 1 由事件②互吸兜住);删「跨环重触发由幂等守卫吸收」句,改为「快照源 = gs 现值跨环连续,同位面跨环不重触发」。
- design §2 第 3 条:「op 成员帧首快照对拍」→「帧首现读快照对拍」。
- landing 3.4 判据:「同位面不双入队」补构造形态——「跨环形态(新 op 实例 + gs.node 保留上环 plane)首帧不得重入队」。

### N2【整改·Z3 残留】「lazy 先例」引证失实:kernel→obs 运行时导入实为零先例

channel §4「lazy 先例 = cw_encounter_selection.py:39」——该行在 `if TYPE_CHECKING:` 块内(:35 起),运行时不执行,属类型注解导入;kernel 桶运行时导入 obs = 零先例(第四轮报告 Z3 的证据陈述同误,修订照抄)。方案本身(公开化重命名 + 函数体内 lazy import)成立,但文档声称有先例而实为首例,依据可信度失真。另「模块级导入……会成环」措辞过强:cw_ore_channel → cw_identity_obs → cw_game_state 的加载链不必然成环,实害 = obs→kernel 单向分层被反向边破坏(obs 桶模块级导入 kernel 共 23 处,cw_identity_obs.py :40 即其一)。
**修法**:引证改「kernel→obs 运行时导入零先例(cw_encounter_selection.py :35-41 为 TYPE_CHECKING 类型注解);本设计首开函数体内 lazy 形态,动机 = 不在模块级新开 kernel→obs 反向边」;「会成环」改「破坏 obs→kernel 单向分层(有循环加载风险)」。

### N3【整改·Z2 残留】正本清单条目缺 spheres 写端/晶矿域语义更新半句

landing 清单第 3 条只写「补 ore_rewards / ore_declared_pending 两域行」;Z2 建议原有「+ spheres 写端挂接说明」丢失。正本 projection_contract.md :19「晶矿域 OreSight.points 载点击坐标」在本迭代后语义不完整(附着值独立成域、spheres 写端唯一入口 = 挂接入口),不补则该表失真残留——恰是 Z2 自己的立论。另「两域行」措辞与正本表形态(四列表、域语义在「关键契约」列内嵌)失配,实现者落笔需自行翻译。
**修法**:条目改「flow/projection_contract.md:状态面板表 GameState 行关键契约列——晶矿域语义更新(附着值独立域 ore_rewards、spheres 写端唯一入口 = 挂接入口)+ 追加 ore_rewards / ore_declared_pending 域语义 ← 3.1/3.4」。

### N4【备注·B3 残留】平局「旧列序稳定优先」缺枚举序附着点

「稳定」的前提 = 候选对枚举序确定;设计未定义枚举形态(实现者若以无序集合枚举候选对,「旧列序稳定优先」无附着点,平局仍依实现)。B3 建议的 (旧列序, 新列序) 字典序只落了主键。
**修法**:补半句「候选对枚举 = 旧列序外层 × 新列序内层,平局依该字典序,贪心序完全确定」。

### N5【备注·恢复局边界】接管局事件②入队一条不可防的多余声明

恢复对局接管时(cw_loop.py :1520-1535,iter1 读到残局 plane、`_invalidate_tracked_on_takeover` 后 gs 重建):若 active_env 已定,事件②帧边沿(''→非空,接管后首个备战帧)入队一条当前 plane 声明——接管局历史丢失,无法区分「该位面声明已发」。影响 = 至多多一条声明附着(随机态域,观察收口纠偏,零停机风险);与 N1 修复形态无关(形态 A 下同样存在)。建议在 §5 事件②段加一句披露(「恢复局可能多发一条声明,随机态由观察收口,接受」)即可,不阻塞。

## ④ 定稿试读

- **3.1 / 3.2 / 3.3**:维持第四轮「能开工」判定——本轮触碰面内核验未推翻,Z1/B1/B2/B4 落实,3.3 侧 sim 窗口幂等守卫(`_window_begun_ord`)经 N1 推演再次确认为不超发的正确形态。
- **3.4 live 挂接**:**不能定稿**——N1 快照载体形态未定死(照先例实现 = 声明金超发 + live/sim 分歧);测试构造约束(fake 真实写 node)钉住了时序面,钉不住载体面。N1 修法为一段文字 + design 一句 + landing 判据一句,修订后本节即可定稿。
- **末阶段正本更新**:清单可执行,补 N3 半句后闭合。
- **修订量与重审范围**:N1(必修)+ N2/N3(半句级)+ N4/N5(备注顺手)——集中在 channel §5 前值载体段、§4 引证句、design §2 第 3 条、landing 3.4 判据与正本清单,共五处文字;下轮定点复审仅这五处即可,无需重攻全篇。

**治本核维持**:第四轮「语义层归层/统一内容通道非同族复发」判定未被本轮触碰面推翻;N1 属修复载体未定形,非方案层级问题。

**规范遵循核**:本轮触碰段落依据就地标注密度保持;违例项 = N2(引证与代码事实不符——TYPE_CHECKING 块被当作运行时先例)。其余四份文档构成、landing 阶段小节、正文无过程叙事等第四轮已核项维持。
