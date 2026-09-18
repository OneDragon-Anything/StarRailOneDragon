# attack8 —— 策略器决策输入统一 迭代设计 对抗审查(r8)

> 审查对象:`design.md` / `landing.md` / `README.md`(本目录,当前工作区状态)。
> 判据源均直调复核,无转述:iteration-design.md(四硬规则/§7 三核/阶段七件/正本清单/标题层级)、strategy-docs 00/01(宪法)、game_state/fields.md(§2.1/§2.2/§2.4/§3.3/§3.4/§3.7.1/§8.1-8.5/§8.8/§9.4)、flow/README.md(§2 全节)、flow/session.md(§5.1 B4)、正本树全族(flow/game_state/screens/strategy-docs/sim/design/architecture.md/docs/game)、代码真值(`src/sr_od/application/currency_war/` 符号锚逐一读码体:cw_strategy.py/cw_game_state.py/cw_strategy_session.py/flow.py/bridge.py/cw_events.py/cw_encounter_selection.py/cw_equip_wear_plan.py/cw_screen_encounter.py/cw_screen_supply_node.py/cw_screen_prep.py/cw_screen_buy_cards.py/cw_loop.py/cw_observation.py/cw_screen_op_base.py/cw_node_obs.py/sim/cw_replay.py)、sr-od-test 路径、在飞三迭代(execstate/turnstate/unified-obs 的 README/design/landing,commit 锚 git 直查)、AGENTS.md、strategy-work.md §4/§6。
> 词表/计数词/符号面用全仓 grep 普查法对账(见分核结论各条)。

## 发现清单

### [M1] major | design.md §2.6-1/§2.6-2 ↔ landing.md 3.4 | encounter 对照矩阵 design 侧未随重入格修复同步扩格,两处判据源数值冲突

**发现内容**:attack7-B1 的修正方向②明令「同批扩 §2.6-1/-2 对照矩阵补『重入重走后再决策』格」,落地只在 landing 侧生效:landing 3.4 已是「encounter 四格对照——首调/累计闸命中/刷新重决策/**重入重走首调收 False**」(landing.md 3.4 完成判据两处),而 design §2.6-1 仍是「encounter 入口 `encounter_refreshed_in_visit` **两态对照**(False/True → 与改前首调/重决策同返回)」、§2.6-2 仍是「专锁 encounter **三分支**(首调/累计计数命中闸/刷新后重决策)与空选项分支」。3.4 的设计依据引用「design.md §2.1-4、§2.2…、§2.6(主凭据 1/2)」——worker 凭 design §2.6 建锁得三格,凭 landing 判据得四格;landing 阶段小节虽是账本唯一源,iteration-design.md 硬规则 4 明令「判据同步…禁只改触碰段」,且该规范对 design↔landing 失同步的同族失分已两次实证(其卡点原文:二次复发即流程级)。

**修正方向**:design §2.6-1 两态对照扩为三态(首调 False/刷新后重决策 True/重入重走首调复位 False,各与改前同返回);§2.6-2 三分支扩为四格(补重入重走格),与 landing 3.4 逐格对齐。

### [M2] major | design.md §2.6(快照 restore 申报) ↔ landing.md 正本更新清单/新增面核对单 | fields.md §8.1-8.5 申报面无承载行,普查与核对单双兜底均不可达

**发现内容**:design §2.6 末句申报「**快照 restore 面不对称**:encounter/supply payload 升级后,restore 侧仍循 shop 手写重建先例不扩展——两 payload 经『其余域直透』落 dict…该判读面边界随正本批在 **fields.md §8.1-8.5 结构符号指针节**申报」。但 landing 正本更新清单的 fields.md 行只列「§2.2/§3.4/§3.7.1/§9.4」四节,无 §8.1-8.5(目标节实存:fields.md「### 8.1-8.5 结构与 API 符号指针」)。该申报属「新增内容该进册」类——普查词表(旧符号/计数词)对新增申报零命中,末阶段「新增面核对单」四项(8 新域键入册/新字段新槽规格行/路由清点与属屏映射/兼容裁定句)也不含它:预登记、普查、核对单三重机制都兜不住,末阶段「清单清零 + 核对单全核销」可判过而 design 承诺的申报面静默丢落。

**修正方向**:landing fields.md 清单行补「§8.1-8.5(restore 判读面边界申报:encounter/supply payload 升级后 restore 直透不扩展)← 3.1」,或新增面核对单补该项;二选一,给申报面一个验收承载。

### [m1] minor | landing.md 末阶段·范围(否定式界定) | `docs/game/screens/` 归属仍未定义,投资两篇「空 board stub」失真句(与 §1.1 顺带勘误同族)三无覆盖

**发现内容**:范围句只「含…`docs/game/currency_war/` 游戏知识正本」——attack7-M2 的修复把 `docs/game/currency_war/` 纳入并把两篇 supply 文档预登记进清单,但两篇 supply 文档实际住在 `docs/game/screens/`,该目录既不在「含」列举也不在排除列举,按 attack7-M2 确立的「不在列举即不在范围」读法仍在普查面之外。同目录实存与 design §1.1 顺带勘误同源的失真句:`docs/game/screens/currency_war_invest_env.md:33`「overlay 时 board 不可读 → decide_event 用空 board stub」、`currency_war_invest_strategy.md:34`「…空 board stub」——调用方现直传容器单例(flow.py:471 过期 docstring 的同一失真族,design §1.1 只勘误 flow.py 一处),两句不被任何词表命中、不在清单、不在范围:批后 flow.py 已改而游戏文档同族句仍假,勘误口径一族两态且无机制面能再发现。

**修正方向**:①范围句把 `docs/game/screens/` 与 `docs/game/currency_war/` 一并纳入普查面(或显式排除并申报理由);②清单补一行「`docs/game/screens/` 投资两篇『空 board stub』句随 3.4 按 §1.1 同款勘误改写」。

### [m2] minor | landing.md 末阶段·范围否定式 | proofs/ 排除理由「已实测零命中」对词表首项 `decide_` 前缀普查不成立

**发现内容**:排除项写「`proofs/`(数学证明,**已实测零命中**)」。对目标符号与计数词(decide_invest/refresh_used/prep_obs_frame/九接口/五个计数词形态)该断言成立(grep 实证 proofs 树零命中);但对词表首项「`decide_` **前缀普查**」不成立——proofs 实存前缀命中:`proofs/math_proofs.md:91`「cw_events decide_event」、`proofs/p81-invest-refresh-dominance.md:3`「decide_event 刷新判据段」、`proofs/validations/P36A_VALIDATION.md:53` 与 `P5_REMEASURE.md:27/28/49/72`「decide_prep」、`P41_VALIDATION.md:53/64`「decide_sell」。排除 proofs 本身合理(命中皆 kernel 存活纯函数或已退役 cw3 符号,分类恒「不辖」),但排除理由的依据标注与词表首项自相矛盾(硬规则 1:依据不实即攻击目标)。

**修正方向**:排除理由改写为「目标符号与计数词实测零命中;`decide_` 前缀宽命中皆为 kernel 存活符号(decide_event)或已退役 cw3 符号(decide_prep/decide_sell),分类恒不辖,排除以免对账表噪声」。

### [m3] minor | design.md §2.2-c | 瞬态槽「在屏读得零选项写 []」与「在屏失读帧不写」缺判别信号,写槽行为二义

**发现内容**:三分语义定死「在屏失读帧 = 不写不读(handler 走自身失败安全分支——现状**零选项/OCR miss** 即不调 decide 同型)」与「在屏读得 = 覆盖(**零选项 = `[]` 合法写入**)」。但现役选项读链对「OCR miss」与「读得零选项」同形返回 `[]`(cw_node_obs.read_supply_options「读不到 → []」、cw_screen_encounter.py:202「传入帧读缺 → 返回空表」)——handler 在选项读取这一步没有区分二者的信号,「读得零选项写 [] 占一个 write_seq/journal 行」还是「失读跳写保 None」两读都可满足字面,而两者的可观测面(journal 行量/审计面形态)不同,恰是本批申报过增量口径的面。§2.2-c 同一括号里把「零选项/OCR miss」并列为决策门失败安全,又给「零选项」合法写入地位,实现者必撞这个选择。

**修正方向**:一句定死判别口径。建议:屏锚/身份门通过后的选项读取结果恒按「读得」处理(含 `[]` 一律覆盖写,失败安全 = 不调 decide 不变)——「失读帧」收窄为屏锚门失败早退;或反向定死「选项读返回 `[]` 恒跳写」,两者取一并写明审计面口径。

### [m4] minor | design.md §2.1-4 | per-visit 位「写 True 同址沿用 on_outcome best-effort 形态」时,发射后重决策存在与现状硬编码 True 的失败窗分歧,异常语义未申报

**发现内容**:现状刷新后的重决策传的是**字面量** `refresh_used=True`(cw_screen_encounter.py:337/:467),不依赖任何容器写落地;新方案重决策经入口读 `gs.encounter_refreshed_in_visit`。设计定死「写 True 点 = 刷新发射点(与累计计数的 on_outcome 写点**同址**)」——同址钩子体的现行异常语义是吞异常 best-effort(cw_screen_encounter.py:153-167 `except … log.warning(记录面失败不阻塞)`):若 True 写随该形态,容器写失败窗内重决策读 False(读侧缺省亦 False),基线核刷新建议枝 True/False 两枝 idx 可分叉(design §2.7 自证的分叉类,cw_events.decide_encounter:670-672 vs :699-703),与现状逐字节保真主张在该窗被破。设计对 True 写的异常语义(随吞 or 传播)零字。

**修正方向**:§2.1-4 补一句定死:True 写不吞异常(发射点同栈直写,失败上抛——发射链本就不再有后续依赖该次决策落地的语义),或显式申报「容器写失败窗的分歧可接受」及其量级依据。

### [m5] minor | design.md §1.1 | 「已用」闸现状刻画「命中时打日志分支」只对 encounter 成立,supply 闸命中为静默分支

**发现内容**:§1.1 对两处旗标共用一句刻画:「『已用』闸本体在 handler 侧读容器累计计数,**命中时打日志分支**并不重决策」。直调:encounter 闸命中打 `[cw-encounter] 建议刷新但本局已用`(cw_screen_encounter.py:322-323/:454-455)✓;supply 闸命中(`if pick.refresh and not _refresh_used:` 为假)直接落入 `elif` 选卡支,**无任何专属日志**(cw_screen_supply_node.py:233-268,仅 ：261 文本锚读缺与 ：297 常规决策行)。「值对标签错」类:共用刻画句对 supply 半边不真,且该句是 §2.7「逐字节保真」论证的现状基线之一。

**修正方向**:§1.1 该句改分述:「encounter 闸命中打日志分支不重决策;supply 闸命中静默落选卡支」。

### [m6] minor | README.md | 索引多出模板外小节,偏离 iteration-design §4「只做两件事」

**发现内容**:iteration-design.md §4 定义 README「只做两件事——串文档、记进度」,模板只有「文档/进度」两节;本 README 另有「## 承接出处与依赖」节(内容为两行纯指针,指 design §0/§2.8,不设第二抄本)。实质无害(指针非判据非笔记),但属模板外结构,形式门偏离。

**修正方向**:两行指针并入「文档」节作列表行,或删除(design §0/§2.8 已自足承载)。

## 分核结论

- **核一(无前提)**:M1、M2、m1、m3、m4(覆盖完整性/判据同步/等价性主张/实现者无需再设计);另完成如下面的攻击且零发现——§1.1 现状症状逐条对码:ABC 11 决策入口签名三形状(cw_strategy.py:117-187 逐一读)、pick 族 9 入口 4–5 参、decide_invest kind 分叉(:140)、supply/encounter refresh_used 布尔(:146-148/:152-154);supply 旗标 = 容器派生(cw_screen_supply_node.py:206-213 派生式逐字节核对、:230-232 调用点;局外实例兜底 :120/:213 永不进入口——decide 调用仅在 match 在场支 :222,等价主张成立);encounter 首调无参/重决策 True 四调用点(:304/:336/:439/:466,两路径各一对);「已用」闸读累计计数不重决策(:320-325/:452-457);重入路径实证(:254-264 锚在清标志重走 → fall-through 再次无参首调;cw_overlay_pick_action round_retry 链);`prep_obs_frame` 槽(cw_strategy_session.py:203 刻意字符串注解先例)+ 4 写点(cw_screen_prep.py:532/897/1599/1763)+ 3 读点(bridge.py:174/cw_screen_prep.py:1865/cw_equip_wear_plan.py:163)读者封闭性逐一过;`_open_shop_phase` 的 `obs` 形参现行零消费(:2119-2164 方法体无 obs 引用,死参申报属实);`gs.shop` 活写端在产(cw_observation.py:2611)、encounter/supply live 清点缺位与 sim 口清点(cw_game_state.py:3970-3971/:4264-4265)、live 清点恰两处全 shop(cw_game_state.py:2033 CloseShop 腿/cw_observation.py:2618 prep 相位锚 miss 支);Encounter/SupplyPayload 现形状(:613/:620 元组形);`_PAYLOAD_DOMAINS` 三域(:171)/leave_screen 域守卫(:3158)/carry None 跳过先例(:3131);`node_screen_refresh` 为 schema 分组名非访问路径(DEFAULT_GS_SCHEMA:146 vs 顶层 Field :2756-2757);`_dispatch_identity_screen` 十行属屏键逐一与分发臂对上(含列车同行:1374/骇入策划:1380/盛会之星:1400/星徽秘典弹窗:1458/祈愿试炼:1453/备战-武装箱选择:1437;武装箱弹窗:1431 派发 CwScreenArmoryBox 无 decide、投资环境 :1598 在分发臂内);挂点位置序(cw_loop.py:1754 stop_at_prep 早退 < :1818 识别 < :1821 分发,绕行无害性成立;PREP_DIRECT_EXIT_SCREENS 成员与映射属屏零交集);flow.py decide_invest 方法体拆两半可行性(:468-514 入口内务/D* 三参/CommitSignals src 分叉逐段核对)、decide_shop_action 内取容器(:708)、decide_shop_screen 驱动器内自取容器且覆写体是 sim 消费面(flow.py:798/bridge.py:273/cw_replay.py:112);mandate_v1/shop.py 本体 gs-first(:749)零改动申报成立;`REGISTERED_ACTORS` 缺席者恰 CwScreenPlanner/CwScreenBoxPick(:285-336 逐项点名);EncounterOption/SupplyOption asdict 序列化安全(_json_safe:1501-1511 dataclass→dict);eval-lcs 吃 OCR 原名(cw_events.py:233/:376、cw_investments.py:1320-1322);基线核/生产核 True/False 两枝可分叉(cw_events:670-672 vs :699-703;cw_encounter_selection:387-390);megastar_clicked 读侧 getattr 缺省 False 先例(cw_screen_megastar.py:157);execstate #3 写侧同型/#4-#6 分工/#12-#14 域 bump 先例/#20 非 Field 先例(execstate design.md 逐行)、commit ee1f4e337 与 turnstate 7b50d690f/170d8366f/b6e88a902(git log 直查)、unified-obs 3.3 候窗验证期与 3.4 依赖链(其 README+landing:40/:49)与 §2.8 冲突表文件面(其 3.4 文件面实含 cw_screen_prep.py/cw_screen_buy_cards.py,landing:48)三方吻合;cw_replay `--diff` 退役/`--run/--rounds` 现行(模块头:11/:16);kernel/cw_decision_trace.py 实存; proofs 目标词零命中;末阶段五计数词形态对正本树全量命中句逐一覆盖(flow/README L32/L47/L53/L67/L73/L91、session.md L14、strategy-docs README L33/L60、13 号篇 L1、25 号篇 L4、screens README L77/L107、fortune.md L11/expert_invite.md L12);`refresh_used`/`prep_obs_frame`/`decide_` 前缀在正本树的逃逸命中(11/14/16/19 号稿、fields.md L474、outer_loop.md L91、projection_contract L83/L94、architecture.md L111、cw_node_obs.py:282 注释等)全部落在词表辖域内可被末阶段普查收口归类;跨文档引用锚(fields.md §2.2/§3.3/§3.4.4/§3.4.5/§3.7.1/§8.8/§9.4/§8.1-8.5、flow/README §2/§2.3/§2.4、session.md §5.1 B4、AGENTS 测试/提交节、strategy-work §4/§6、sr-od-test L1 路径)逐个实存可解析。
- **核二(规范遵循)**:m2(硬规则 1 依据标注)、m3(m2 无需再设计)、M1/M2(硬规则 4 全量同步复查)、m6(README 模板);其余逐条过——依据就地标注(关键主张均带码点/裁定/正本指针,抽查二十余条全实)、无过程叙事(design/landing 正文无轮次/修订措辞,进度只住 README)、四节齐/单文档方案合法、阶段小节七件齐(3.1–3.5+末阶段逐项点过)、阶段标题层级已合规(`### 3.x`)、通用工程门单点定义+引用不复述、README 进度行不属过程叙事违规(进度住 README 是规范明文归宿)。
- **核三(治本)**:零发现。实际攻击过的面——§1.2 归层「约定层」成立性(三签名形状并存实锚 + payload 治理规则已在(fields.md §2.2 例外/§3.7.1)而未定为唯一承载,归层与两正本吻合);§2 修根判定(签名约定统一 + 决策输入单源入容器 = 约定层根治;kernel 纯函数零触碰的边界论证成立——判据层输入来源归调用方组装);症状修法的战术权衡申报合规(per-visit 位 vs 两屏旗标统一登记不解决、prep_obs 豁免、payload 内容扩展归行为批,均带理由与归属批);「同族第二次出现升架构件」检查(输入承载分散属首次系统收编,终态方向第一批显式登记后批,无逐件修模式);per-visit 旗标落容器的宿主选型(megastar_clicked→StrategyState 与刷新计数→容器两先例之间,决策输入选容器与 #4-#6 格局一致,非新载体发明)。
