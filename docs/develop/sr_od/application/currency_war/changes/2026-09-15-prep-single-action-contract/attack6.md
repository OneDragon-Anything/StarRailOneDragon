# attack6 —— 备战契约单动作收口(无前提对抗审查,干净上下文)

> 审查对象:①本目录 README.md / design.md / landing.md(现行工作区状态);②`src/sr_od/application/currency_war/strategies/impl/cw_strategy.py::CwStrategy.decide_prep_screen` docstring(工作区未提交修改);③`docs/develop/sr_od/application/currency_war/strategy-docs/README.md`(工作区未提交修改:§3 契约行改表述 + 19/20 两行归位)。未读同目录 attack.md–attack5.md;全部数值/引文/码点直调代码与正本文档复核,未转述。行号为当前工作区行号,漂移以符号定位为准。

## 结论摘要

- 发现总数 **4**:高 0 / 中 2 / 低 0+2(F1、F2 中;F3、F4 低)。
- 对象 2(docstring as-built 逐句核)**零发现**;对象 3(strategy-docs/README.md)**零发现**。
- 两个中危同属一个主题:**死引用/死口径收敛的完备性声明存在两个机械检查双盲的残留面**(bridge.py 类 docstring 裸 `§4.1`;决策核内灭失契约引用族)。行为面、语义面、验收判据可执行面未发现会导致实现错误或行为变更的问题。

## 发现清单

### F1(中)bridge.py 类 docstring 第二段裸「§4.1」——设计枚举与两道机械检查三重盲区,死引用必然随批存活

- 位置:`strategies/impl/mandate_v1/bridge.py` L81(`MandateV1Strategy` 类 docstring 第二段):「……复用生命周期冷建口、方向节拍内化刷新(ADR-0583)与 pick 族缺省实现(基线零改动,**§4.1**);……」;关联 design.md §2.3 第 4/5 条、landing.md 3.1 ②「§2.3 五处 + 定稿关键句」。
- 直调事实:
  1. design §2.3-4 只点名**模块 docstring 首段**裸「§4.1」(L3)删括注;§2.3-5 点名 L14「契约 §5」与类 docstring**首句**(L77)。L81 是类 docstring 第二段内的**第二个**裸「§4.1」,与 L3 同族(同为无文档锚的裸节号,指向不可解析),未被任何条目覆盖。
  2. 3.1 验收关键词集含 `§4.1`,但判据域 = **diff 新增行/本批改写行**;本批对类 docstring 的改写指定为「首句」(§2.3-5),L81 属未改行 → 验收 grep 不命中。
  3. §2.2 收尾扫尾关键词族(`契约 §`/`契约 v`/`序列契约`/`序列发射`/`空批`/`取首项`/`结算惰性 drain`/`unified-action-factory`)**不含裸 §-引用**;四文件全文扫尾对 L81 同样零命中。
  4. landing 3.1 ② 申报「docstring/DESCRIPTION/模块头死引用收敛(§2.3 五处…)」——bridge.py 内实际同族死引用为**六处**(L3/L14/L77/L81/L92/L109-115/L117 中按条目计),「五处」计数与实态不符。
- 后果:批后 bridge.py 类 docstring 呈「首句已改单动作、第二段仍挂不可解析的 §4.1」的半收敛态;「死引用逐一收敛」的完备性声明失真,且该残留无豁免申报、无任何机械检查可兜。
- 修正方向:§2.3-4 扩为「裸 `§4.1` 两处(模块首段 L3 + 类 docstring L81),均删括注/改语义表述」;landing 3.1 ② 计数同步改;或在 §2.2 扫尾关键词族补「裸 `§N` 引用(四文件全文,人工核指向可解析性)」。

### F2(中)灭失契约工作副本引用族在决策核(entry.py/mandate.py)同族存量:既不收敛也不申报保留,「扫尾=完备性兜底」的域与家族真实分布不一致

- 位置:`strategies/impl/mandate_v1/entry.py` L8(「帧稳定截断(契约 v2 §3.2)」)、L15/L19-20(「契约 v2 §3.2 备战线域 18 类逐类表……§3.3 fail-closed」)、L194、L210、L221、L245(「帧稳定截断发射器(契约 §2 帧稳定域 + §3 分域枚举 + §3.3)」)、L254、L266;`mandate.py` L1299(「契约截断点」)。
- 直调事实:
  1. 契约正本 `CONTRACT_SERIES_DECISION.md` 工作副本灭失由 entry.py L16-19 自证(全仓 grep 仅此一处提及,文件确不存在);design §2.2/§2.3 据此把 bridge.py 与 cw_screen_prep.py 内的**同节号同副本**引用(`契约 §4`/`契约 §2`/`契约 §3.2/§3.3`/`契约 v1/v2`)全部定性为死引用并收敛。
  2. 同一副本、同一节号(`§3.2`/`§3.3`)的引用在 entry.py 内密度最高(≥8 处),design 的死副本论断对其同样成立;但 landing 3.1 范围「不含:决策核(entry.py/mandate.py)」只划定**代码改动**边界,design §1「明确不解决」三条均谈机制不谈注释死引用,全篇无一处申报「决策核内灭失契约注释引用本批留存、归属何批收敛」。
  3. §2.2 扫尾自我定位为「防枚举漏孪生,结构性判据……完备性的机械兜底」,但扫描域 = 四文件——对该家族密度最高的两个文件结构性失明;「禁未处置命中」实际只辖四文件。
- 缓解(如实记):entry.py L16-19 模块头就地声明契约灭失并重锚 `flow/action_exec.md §1`,读者在该文件内有解毒剂;但 L194/L221/L245 等函数级 docstring 深处命中无邻接声明。同批内 bridge 同款引用判死收敛、entry 同款引用原样存活,无一致性说明。
- 后果:本批主题 = 死引用清零,收口后仓库内仍存同族死引用而设计/验收面对其不可见、不登记——症状修法缺「残留面 + 排期根治」申报(治本核验口径)。
- 修正方向(择一):①design §1「明确不解决」补一条「决策核内灭失契约注释引用(entry.py ≥8 处/mandate.py 1 处)本批不动,收敛挂将来决策核行为变更大批」;②landing 3.1 验收凭据的保留申报类别预登记该族(写明「决策核注释引用,另批收敛」),使三分处置有据。

### F3(低)cw_screen_prep.py 的 changes/ 引用注释实态四处,枚举只点两处;其中一处同行带正本路径笔误

- 位置:`operations/cw_screen/cw_screen_prep.py` L664、L984、L2103-2106、L2325-2326;关联 design §2.2「两处 `changes/` 引用注释(……L2103-2106 与 L2325-2326)……随本批注释收敛顺带清理」。
- 直调事实:
  1. `unified-action-factory` 在本文件实际命中 **4 处**:L2103/L2325(已点名,`design.md unified-action-factory §2.4`)+ L664(「box_overlay_open 采集已随 unified-action-factory 批2b 退役删除」= 退役史注)+ L984(「R9 逻辑态全覆盖(design.md unified-action-factory §2.6……)」= 语义指针型,与被点名的两处同类)。后两处未点名,依赖扫尾关键词 `unified-action-factory` 由实现者自行三分处置——机制可达,但「保留申报」一旦被用于 L664/L984(理由只能很弱:史注/既有债),验收仍绿而债留存,存在软收编口子。
  2. L984 同行声称「规则全集正本 = `flow/action-logic-state.md`」——该文件实际在 `game_state/action-logic-state.md`(正本更新清单 #13 即指向后者;prep.md L45 引用路径正确)。收敛该处 changes/ 指针时应顺带核正路径,设计未提。
- 修正方向:§2.2 点名四处(或写明「`unified-action-factory` 引用族四文件全文零保留」);L984 的正本路径笔误列入顺带收敛。

### F4(低)迭代 README 进度行漏列已存在的 attack5.md

- 位置:本目录 `README.md` L13:「设计对抗:进行中 · 报告=[attack.md](attack.md) / [attack2.md](attack2.md) / [attack3.md](attack3.md) / [attack4.md](attack4.md)」;目录内 `attack5.md` 已存在(迭代设计规范:README 记进度一处、串文档)。
- 修正方向:补链 attack5.md(本报告 attack6.md 落位后一并补)。

## 对象 2:`decide_prep_screen` docstring as-built 逐句核 —— 零发现

工作区现行文本(L121-144)逐句对照代码实态,全部属实:

| # | 主张 | 直调证据 |
|---|---|---|
| 1 | 返回形状 = 波批序列契约遗留的 `list` | 签名 L122 `-> list[CwAction]`;波批形态定性 = flow/README.md 卷首 L6(2026-09-06 单动作循环落码) |
| 2 | 现行消费 = 单动作循环逐帧取首项 | `cw_screen_prep.py` L2043/L2248 `action = actions[0]`,两处同构 |
| 3 | 输入 = `session.prep_obs_frame`,观察层写、跨步状态同 session | `kernel/cw_strategy_session.py` L202-206(帧槽);写者 = `cw_screen_prep.py` L975-977(入口装配)/L2115/L2315(逻辑态直写);defer 计数(`sphere_defer_streak` 等,`cw4_counters` 挂 strategy_state→session)与意向状态机(`v3_intention`)均在 session 侧 |
| 4 | 设计正本 = `screens/op-layer.md` §1.1 | op-layer §1.1「一次画面 op 调用 = 一轮『入口观察 + 逐动作决策循环』」在文 |
| 5 | 列表 = 决策核三遍编排发射组织,相对序决定首项,尾部动作生产不消费 | `bridge.decide_from_turn` L259-291(emit→route_tag→truncate)→ 消费端仅取 `[0]`,尾部逐帧丢弃 |
| 6 | 空序列合法 = 本帧无动作,交回外循环重观察(stall 兜底归外循环防线) | L2038-2041 / L2243-2246;外循环无进展守卫 L1995-1996(动作批签名计数) |
| 7 | 禁用空批表达控制流——画面转移一律走 OpenShop/StartBattle 终结 | `entry.py` 分类表(`_TRUNCATION_POINTS` 含 OpenShop / `_TERMINAL` = StartBattle);注册表 `terminal` 类属性消费 L2107-2109;prep.md §5 |
| 8 | 已退役语义 + 单一源 = `flow/action_exec.md` §2/§3 | action_exec §2「机械执行,无成败回执……落地判定归观察侧 reconcile」L15;§3「无 fail-stop/恢复原语」L31 |
| 9 | 帧稳定分类在决策核内仍活(mandate_v1 entry),辖发射组织,非流程侧契约 | `entry.py` L220/L241 及包内真实调用 4 处(bridge L290 截断发射、entry L297/L1157 分类、mandate L1965 M7 回排) |
| 10 | 生命周期机制四件(action_key/执行失败记忆/stall 门/强制出战)归流程侧 | `action_key`(`cw_vocab.py`,消费 L2047/L2252);`deploy_fail_counts`(`kernel/cw_exec_state.py` L111,与 flow/README §2.2 L82 同清单);stall 门 = 外循环 F2;强制出战(F5)L496/L505 |
| 11 | 「观察帧缺失即抛错」 | `bridge.py` L120-125 抛 `ValueError` 实码 |

注释规范(AGENTS §8)附核:中文、结论→出处→边界结构、引用全为持久索引(文件:节/符号/ADR 号),无变更史叙事、无会话局部标识符。git HEAD 版为「序列契约 v1(2026-09-03 冻结)」波批口径、工作区已重写为 as-built 口径——与 design §1「现行文本已是 as-built 口径;landing 3.1 ① 改写 = 新契约语义落位」的定位一致,非重复修复。

## 对象 3:strategy-docs/README.md 工作区修改核 —— 零发现

- **19/20 归位**:两文件实存(`19_reinforce_channel_and_survival_discount.md`/`20_large_balance_must_spend.md`);新行插于 §2 分篇表 18 与 22 之间,三列格式与邻行一致;文尾两孤立行已删,文件以 §5 要点列收尾,无残渣。一句话概述与两篇实际标题/结构相容(19 =「补强通道接线重估与 P51 生存折现消费位重立」的压缩;20 =「必花域 + §3 旱期金出口分层」)。
- **§3 契约行**:「契约成员 13、单动作循环;序列语义为历史注」逐项对 flow/README §2 核实——13 = 每局冷建 2 + 决策入口 11(abstract 12 + 工厂 1,L40/L84 同数);单动作循环 = §2.2 L64-65;历史注 = §2.2 L77;四身份分离 = §2.1。「flow/ 七篇」= flow/ 目录实有 7 个 .md,数目成立。
- 已知范围外(不计):§2 分篇表缺 14/15/16/17/21 五篇行(既有缺口,已另行申报);L3 的 `.debug/temp/...` 指针系未改动行。

## 验收判据可执行性专项(3.1/3.3)

- **关键词集 × 定稿文本互斥性**:对 §2.1 基类定稿句、§2.2 码块及 lifecycle docstring 定稿句、§2.3 bridge 五条改写与定稿句、flow.py 两处定稿句逐词过 3.1 关键词集(`空批`/`取首项`/`契约 §`/`契约 v`/`序列契约`/`list[CwAction]`/`结算惰性 drain`/`§4.1`)——**零碰撞**,「定稿文本已规避全部关键词」声明成立。
- **判据域读法**:「作用于 diff 新增行/本批改写行;被删行与未改行不在判据域」读法唯一;豁免申报(`decide_from_turn` 签名 `-> list[CwAction]`)与其域判定(非本批改动行)自洽且必要。
- **扫尾机制覆盖面**:四文件全文按 8 关键词族实扫,全部命中可归类为「已点名收敛」(逐一核对在码)或「未改行合法留存」(如 cw_screen_prep L218/L902「15 号稿批 C/§4.1」——15 号稿 = strategy-docs/15_observation_multisource_arbitration.md,持久文档,合法指针;flow.py L423「结算惰性 drain 已删除」节头注,扫尾可达需三分处置)。**唯一双机械盲区 = F1**。
- **3.3 闭域检查完备性(独立全树重跑 `首项|空批|list[PrepAction]`)**:全部命中归属清单 #1-#15(flow/README L17-18/L23/L64、projection_contract L89-90、action_exec L28、op-layer L14/L21、prep.md L15/L32/L53、screens/README L130、22_prep_screen L8/L28、action_exec L9、action-logic-state L163、prep-executor-actions L13、02_mandate_layer L82)或豁免表(flow/README L77/L81 历史注节、changes/ 全目录、`proofs/validations/P51_V3_REBUILD.md` L391——直调确认「R31-2 首项=1」系拟合器标签序位,豁免正当);PrepAction 裸名活正本位 = projection_contract L89 + action_exec L9,与「已知位」一致,其余命中均为 `PrepActionExecutor` 合法名。跨行拆句(flow/README L17-18)经「首项」单字面可命中且清单 #1 已预告归属。**清单完备。**

## 三核结论

- **核一(无前提)**:消费端全集(全 src `decide_prep_screen` 生产调用仅 cw_screen_prep 两处)、sim/replay/tools 零消费 prep 面(flow/README §2.3 L91 + op-layer §4 L153 + tools 零命中实证)、测试影响面(全仓仅 `test_cw_p2_blood_band.py` L213-218 `*a, **kw` 桩子类,形状/文案锁零命中)、正本更新清单 16 条引文/行号逐条在码在文——设计边界完整;发现 = F1-F4 的收敛完备性缺口。
- **核二(规范遵循)**:landing 阶段小节七件齐;依据就地标注(引文逐条核存在);无过程叙事;迭代内工件引 changes/ 合法、代码/正本 changes/ 引用清理符合铁律;§0 状态与 README 进度一致(除 F4)。规范遵循零违例。
- **核三(治本)**:§1 归层表示层成立(消费语义 2026-09-06 已迁移、签名 list 未跟上,双向实证);§2 修根 = 契约面形状收口,决策核内 list 保留有活机制依据(首项选择序 4 调用点 + `_merge_ev_before_frame_end`/M7 回排实证),非症状补丁;备选 A-D 弃因逐条对权威源核验无空洞(D 的「对称不是规范条款」与 op-layer §1.1 分域表述吻合);None 通道三点依据全部直调成立(⑥ 空则补 StartBattle = entry L936-944 实码;可达空边 = truncate 首位 SellBench/DeployMove 复检截空 L309-324;unknown 首位边不可达 = 决策核可发射 17 类全被四分类覆盖 1+11+1+4 直调数过,备战词表 18 类第 18 类 = OpenBookcard 画面 op 侧发射);行为零变化论证(bridge 取首项与消费端原取首项同源同位、空序列→None 逐义映射、None 文案/fail 文案变化已申报且测试仓/tools/src 消费零依赖)成立。残留缺口 = F2 的家族清点与残留登记。

## 实际攻击过的面(含直调码点)

1. **设计自洽**:design §0-§3 全节、landing 3.1-3.3 + 正本更新清单 16 条、README 进度结构;正本句引用逐条核存在与转述(flow/README §1 L6/L17-18/L21/L23、§2.1 L47、§2.2 L40/L53-66/L68-73/L75-84、§2.3 L88-91、§2.4 L95-97;op-layer §1.1 L14/L21、§1.2-§1.4、§4 L153;prep.md L13/L15/L22/L32/L44-45/L51-53;screens/README L118-133;action_exec §1 L5-11/§2 L13-24/§3 L26-31;projection_contract §4.1 L83-93;02_mandate_layer §7 L82;22_prep_screen L8/L28;game_state/action-logic-state.md L163;logic-updates/prep-executor-actions.md L13;26_battle_settlement 篇名行;P51_V3_REBUILD.md L391)。
2. **代码实态**:`cw_strategy.py` 全文(L97-144 契约面计数/docstring、L104-115 B4、L279-320 gated_hp);`cw_screen_prep.py` 主循环 L1995-2121、lifecycle L2204-2321、`_terminal_exit` L2323-2345、观察装配 L955-978、`_project_prep_obs` L980-989、安灯 L2660-2748、强制出战 L496/L505、L664/L984 上下文;`bridge.py` 全文(模块头 L1-31、类 L76-130、`decide_from_turn` L259-291);`flow.py` 头注 L1-36、帧代次消费 L422-467、`decide_shop_action` L688-740;`entry.py` 全文关键段(头注 L1-42、分类四元组 L194-238、truncate L241-331、emit L432-946 含⑥ L936-944、`_merge_ev_before_frame_end` L1140-1160);`mandate.py` L1285-1324(凑息接线位)、L1945-1972(M7 回排);`cw_vocab.py` 动作类全集(L359-830,备战域 18 类/分类覆盖 17 类逐一数);`cw_strategy_session.py` L202-221;`kernel/cw_exec_state.py` L111(`deploy_fail_counts`);`pyproject.toml` ruff select(F)。
3. **验收机制攻防**:3.1 关键词集×定稿文本互斥(逐词)、判据域读法、四文件 8 关键词全量实扫与逐命中归类、3.3 三关键词全树独立重跑 + PrepAction 裸名口径 + 豁免表三条逐一核真、跨行/裸名/未改行三类机械盲区定向攻击(F1 即由此得手)。
4. **影响面**:sr-od-test 全仓(`decide_prep_screen`/`空批`/`list[CwAction]`/`取首项`)、tools/(同词族)、src 旧文案消费方(`策略输出非`/`空批(本帧无动作)` 全 src 仅两循环自身)、遥测键族(`emitter_*`/`deploy_emit_*`/`deploy_exec_*`/`t1_interest_prep_emit`/`wanted_leg_*`/`m1p_*`/`sphere_defer_*` 实码在键;`prep_box`/`prep_tome`/`prep_spheres` 系 `Emitted.reason` 路由标签非计数键,entry L462/L464/L498)。
5. **契约成员数与边界**:abstract 12 + 工厂 1 = 13(cw_strategy L97-204 逐一数,flow/README §2.2 同数);注册面封闭集 {mandate_v1}(flow/README §2.1 L47);B4 缺省 None(cw_strategy L104-115);None 通道三点依据(⑥ 补 StartBattle/首位复检截空/unknown 不可达)逐边推演。
