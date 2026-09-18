# attack11 —— 策略器决策输入统一 对抗审查报告(r11)

> 审查日期 2026-09-16。无前提独立审查:攻击对象 = 本目录 design.md / landing.md / README.md(当前工作区状态);判据源自取并全部直调复核,未采信任何前轮报告结论:iteration-design.md(四硬规则/§7 三核/阶段七件/README 构成/正本清单)、strategy-docs/00_framework.md(全篇)与 01_math_framework.md(检索无契约面条目)、game_state/fields.md(§2.1/§2.2/§2.4/§3.3/§3.4/§3.7.1/§8.1-8.8/§9.4)、game_state/README.md(§3.3 域清单全表)、game_state/journal.md(§2 渠道族)、flow/README.md(§1/§2 全节/§5)、flow/session.md(§0/§2.1/§5.1 B4)、正本树全族(screens/strategy-docs/action-logic-state/logic-updates/projection_contract/docs/game/currency_war/docs/game/screens,排除 sources/changes/proofs)、代码真值(cw_strategy.py ABC 逐成员、cw_game_state.py 治理面 DEFAULT_GS_SCHEMA/_PAYLOAD_DOMAINS/REGISTERED_ACTORS/_validate_sig/observe/carry/leave_screen/write_logic/payload 形状、cw_loop.py loop() 行序与分发臂全集、cw_screen_encounter.py 全文、cw_screen_supply_node.py 全文、cw_screen_prep.py 写读点/_open_shop_phase/_act_execute_default、cw_screen_buy_cards.py run_buy_waves、flow.py/bridge.py 决策入口与驱动器、cw_events.py 选项类与 kernel 判据、cw_equip_wear_plan.py、cw_prep_actions.py、sim/cw_replay.py、cw_decision_trace.py、cw_screen_state.py)、sr-od-test 独立仓 git grep 普查、三在飞迭代(execstate/turnstate/unified-obs 的 README/design/landing + commit 锚 git 直查)、AGENTS.md、strategy-work.md §4/§6。

## 发现清单(共 7 条:blocker 0 / major 0 / minor 7)

### [M1] minor | landing.md:26(3.2 文件面) | 两处文件条目无已识别改动对象,括注依据失实

- **发现**:3.2 文件面列 `kernel/cw_prep_actions.py`（PrepObservation 注解指向）与 `strategies/impl/flow.py`,但两文件在本阶段均无实锚:①`cw_prep_actions.py` 全文 grep `prep_obs_frame` 零命中(仅 3 处 PrepObservation 类本体/模块头字样),类 docstring(L48-62)无宿主指向句——契约 e 自己申报「来源分级已由 PrepObservation 字段注释内部承载……不新增 evidence 面」,即该类注释本批不动;gs.prep_obs 的新字段声明与 `'PrepObservation | None'` 注解落点在 `cw_game_state.py`(已单列入文件面),不在本文件。②`flow.py` 无 prep_obs_frame 锚(grep 零命中);其 L33 `decide_prep_screen` 注释属 decide_ 词表(3.4 普查辖,flow.py 亦在 3.4 文件面),L162/L349/L436 为已退役 `PrepObservation.state` 槽的历史叙述,非本批对象;3.2 改 ABC 签名不要求未实现该方法的 flow.py 改动。文件面是允许动边界,超配无行为风险,但「括注依据」即依据标注(硬规则 1),失实括注 = 攻击目标自带的错误坐标。
- **修正方向**:删 `cw_prep_actions.py`/`flow.py` 两条件目;若保留须写明真实改动对象(如 flow.py 归 3.4 decide_ 普查兜底、不属 3.2)。

### [M2] minor | landing.md:38(3.3 范围/文件面) | 「sim/回放驱动器消费面调用点」无改动对象,与 design §2.5 自身申报不一致

- **发现**:3.3 范围句含「sim/回放驱动器消费面调用点」、文件面列 `sim/`。代码事实:sim 树唯一策略消费点 = `sim/cw_replay.py:112` `strat.decide_shop_screen(sess, _Cfg())`——驱动器签名本批不动(design §2.5:「驱动器签名不动(非契约成员,内部已自取容器)」「sim 侧改动收敛于驱动器内调用点」),驱动器体内调用点在 flow.py/bridge.py(均已入 3.3 文件面);sim 引擎不调任何契约入口(sim 树 grep 仅注释提及 decide_supply/decide_encounter)。即 sim 代码本批**零改动对象**,范围句暗示的 sim 侧编辑面不存在。design §2.5 申报准确,landing 范围句与之失同步(硬规则 4 轻度形态)。
- **修正方向**:3.3 范围句改为「sim 侧零改动核对申报(唯一消费点 `cw_replay.py` 的 decide_shop_screen 调用签名不变)」;文件面 `sim/` 保留仅辖回放 smoke 运行证(只读)或删除。

### [M3] minor | design.md §2.3(挂点时序①「早退轮无识别结果」) | 依据句与同句括注自相矛盾,按字面为假(机制结论正确)

- **发现**:design 称「stop_at_prep 早退(识别屏名 ∈ PREP_DIRECT_EXIT_SCREENS 即 return)发生在识别之前——早退轮无识别结果」。代码事实:早退分支(`cw_loop.py:1754-1756`)自身调用 `get_in_match_screen_name` 做了一次画面识别(判定名单 = `cw_screen_state.py:46-48` PREP_DIRECT_EXIT_SCREENS = {货币战争-备战, 货币战争-备战-免战},非空集)——「早退轮无识别结果」按字面为假,且同句括注「识别屏名 ∈ …」自证该轮有识别。机制结论全部经直调核实成立:挂点钉在阶段一识别(L1818)与分发(L1821)之间则早退轮确实不经过挂点;早退屏与 §2.3 十行属屏映射零交集(「备战/备战-免战」均不在映射);下轮路由补清成立。属「值对标签错」的表述层残留——r10-F1 消解时改写了机制申报,依据句未随之校准。
- **修正方向**:依据句改为「早退轮不产出阶段一(CW_DISPATCH_SCREENS)识别结果、挂点复用的输入不存在,故不清点」;无害申报(非映射属屏/无 decide 消费/下轮补清)保持不变。

### [M4] minor | landing.md:96(正本更新清单·flow/session.md 行) | 计数句锚字面一半落空:「契约成员 13」在 session.md 不存在,「卷首」定位不准

- **发现**:清单行写「**卷首计数句『决策入口 11/契约成员 13』改 12/14**」。session.md 全篇 grep 无「契约成员 13」表述;唯一契约计数句在 §0 术语节(L14,非卷首):「后契约形状 = 每局冷建 2 + 分画面决策入口 11」——本批后应改 12,无「13→14」可改对象(成员总数计数句只住 flow/README 与 cw_strategy.py 模块头)。末阶段词表含「决策入口 11」可兜住该行命中,不产生假零,但实现者按清单锚字面 grep「契约成员 13」@session.md 零命中,归类时产生锚不可解析困惑(引用锚可解析性,核二)。
- **修正方向**:该行改写为「§0 术语节计数句『每局冷建 2 + 分画面决策入口 11』改 12」;删「契约成员 13」与「卷首」两处失准锚。

### [M5] minor | landing.md:98-99(正本更新清单·game_state/README.md 行与 fields.md 行) | 3.2 的 prep_obs 非 Field 申报面在两行中缺位或阶段标签错置

- **发现**:`gs.prep_obs` 非 Field 容器字段随 **3.2** 落容器(3.1 边界明写「不含 gs.prep_obs 字段新增(归 3.2)」),但:①game_state/README.md 行(← 3.1)只列「node_screen_refresh 域成员枚举句补 encounter_refreshed_in_visit;§3.3 域清单增 8 新域行」——漏 **§3.3 工程结构(非 Field) 行(L95,现列 schema_version/…/exec_books/tracked_books/plane_node_sequences)须增列 prep_obs**;先例 = 同行的 plane_node_sequences 正是 execstate 正本批在该行申报的(L96 在册),漏列即同族面不同待遇。②fields.md 行内「prep_obs 豁免与非 Field 处置申报(§2.2)」的触发阶段标 ⟨3.1/3.4⟩ 缺 **3.2**——该项随 3.2 落地才成真。末阶段「新增面入册核对单·新字段/新槽规格行」可兜底捞出,不产生假零,但预登记清单的阶段归属列失真(清单 = 末阶段消费的账,归属错 = 对账口径错)。
- **修正方向**:game_state/README.md 行补「工程结构(非 Field) 行增 gs.prep_obs ← 3.2」;fields.md 行阶段标改 ⟨3.1/3.2/3.4⟩。

### [M6] minor | landing.md:30(3.2 完成判据·锚普查对账表) | 「零未承载项」的承载桶未含「正本批辖」,判据按字面不可满足

- **发现**:3.2 判据要求「每条锚标注承载(**本阶段换源/改指**),表随批产出零未承载项;普查范围 = 两仓 + **正本树**」。正本树实存命中(flow/README.md:71、flow/session.md:54/:135、flow/projection_contract.md:13/:93、game_state/action-logic-state.md:50、game_state/logic-updates/open-bookcard.md:13)在 3.2 阶段**不可换源/改指**——正本文档更新归末阶段,3.2 文件面不含任何正本文档。按字面,这些命中要么无处承载(判据不可满足)、要么逼实现者私设未申报的第三桶(自行拍板,违停手令)。3.4 的同型判据已显式给四归类桶(契约调用点/kernel 纯函数/入口内部委托/纯注释锚——含「只归类不改正」的桶),3.2 缺同构桶定义,属阶段可验收性缺口(判据二读即歧义)。
- **修正方向**:3.2 判据括注改为「本阶段换源/改指/**正本批辖(命中登记入表,末阶段改指)**」,与 3.4 的四桶结构对齐。

### [M7] minor | design.md §2.5(迁移契约表) | decide_encounter 的第二实现位(bridge 覆写体)未在册,实现位枚举与 3.2/shop 行的口径不对称

- **发现**:decide_encounter 有**两个实现位**:`flow.py:522` 缺省体(委托 `cw_events.decide_encounter`)与 `mandate_v1/bridge.py:203` 覆写体(委托 `kernel/cw_encounter_selection.decide_encounter`;生产唯一注册核 mandate_v1 走覆写体)。统一签名 + 旗标来源切换(形参 → `gs.encounter_refreshed_in_visit` 读)+ 选项来源切换(槽读)在两处都要落。design §2.5 对 shop 线显式点名了覆写体(「bridge.py 同名覆写……sim 回放/序列锁消费的正是覆写体」),3.2 范围句也显式申报了 prep 的实现位分布(「实现 = bridge.py 覆写体(唯一实现,flow.py 无此方法)」),唯独 encounter 的覆写实现位全篇未提;landing.md:54(3.4 文件面「bridge.py(decide_encounter 覆写随改)」)已载,落地不会漏,但总纲「读一遍知全貌」下决策入口实现位分布三线两处在册、一处在册缺失,且 encounter 旗标等价论证(§2.1-4/§2.6 四格)未言明其验证对象含覆写体路径。
- **修正方向**:§2.5 pick 族行或 §2.1 表后补一句:「decide_encounter 实现位 ×2(flow 缺省体 + bridge 覆写体,后者 = 生产唯一在用;两实现体内旗标/选项来源切换随 3.4,四格对照辖覆写体路径)」。

## 零发现面(实际攻击过且未发现问题的面)

### 核一(无前提)

- **§1.1 现状症状全符号锚逐条对码(全部成立)**:契约 11 入口三形状(cw_strategy.py:116-187 逐成员读:prep :117/shop :130 无 gs、invest :140 带 kind、supply :146/encounter :152 带 refresh_used、pick 族 4-5 参)+ create_session(:93)/create_state(:100 非 abstract)= 抽象 12 + 工厂 1 = 13;supply 旗标 = 容器派生 `int(gs.supply_refresh_used.value or 0) > 0`(cw_screen_supply_node.py:206-213),decide 调用仅在 match 在场支(:222),局外实例兜底(:213)不可达入口;encounter 四调用点(:304/:336-337/:439/:466-467,两路径各首调无参/重决策字面 True 一对)、「已用」闸读累计计数命中打日志不重决策(:320-325/:452-457)、重入清标志重走(:254-264)后 fall-through 无参首调;`gs.shop` 活写端在产(cw_observation.py:2611 域)、encounter/supply live 清点缺位(live `leave_screen` 恰两处全 shop:cw_game_state.py:2033 CloseShop 逻辑腿、cw_observation.py:2618 prep 相位锚 miss 支;encounter/supply 清点仅在 sim 合成口/恢复 :3965-3971/:4263-4265);invest 一方法两画面(:303/:404);flow.py:471「空 stub」docstring 过期(调用点已直传容器单例)。
- **契约签名表(§2.1)逐行对账 + 计数推导**:11 现签名/返回类型/形参名与 ABC 逐字节一致;统一后 12 入口/抽象 13/总成员 14 推导成立;与 flow/README §2(L47/L53/L67/L91)三方一致。
- **§2.2 槽位表 12 行对码**:prep_obs 4 写点(cw_screen_prep.py:532/897/1599/1763)与 3 读点(bridge.py:174、cw_screen_prep.py:1865、cw_equip_wear_plan.py:163)读者封闭;`_open_shop_phase` obs 形参零消费(:2119-2164 方法体无引用);EncounterPayload.options `list[tuple[int,str]]`(:613)/SupplyPayload.options `list[tuple[str,str,bool]]`(:620)现形状;Encounter/Supply/Megastar/Partner/PlannerOption 字段全 JSON 安全(int/str/bool/list[str],asdict 主张成立);REGISTERED_ACTORS(:285-336)缺席者恰 CwScreenPlanner/CwScreenBoxPick(landing 3.4 补登记申报精确),CwLoop(:324)/CwScreenEncounter(:296)在册;`_PAYLOAD_DOMAINS` 三域(:171)与 leave_screen 域守卫(:3158)/无条件写语义、carry None 跳过先例(:3131-3132)与设计引用一致;`node_screen_refresh` 为 DEFAULT_GS_SCHEMA 版本分组名(:146)非访问路径、supply_refresh_used 顶层 Field(:2757)属实;8 新域键「每画面一域」先例(shop/encounter/supply)与域 bump 先例(execstate #12-#14「域内容变更 bump match_facts」,其 design/landing 原文直查在册)成立;execstate #20 非 Field 先例与 fields.md §8.1-8.5 plane_node_sequences 行一致。
- **§2.3 离屏机制**:loop() 行序(stop_at_prep 早退 :1754 → 阶段一识别 :1818 → 分发 :1821 → 阶段三/二 → 循环尾未知兜底 :2032)与「唯一真绕行 = 早退」申报一致;识别前无第二 return 面;十行属屏键与 `_dispatch_identity_screen` 分发臂逐行对上(列车同行 :1374/骇入策划 :1380/盛会之星 :1400/遭遇节点 :1406/补给 :1425/武装箱弹窗 :1431→CwScreenArmoryBox 无 decide/备战-武装箱选择 :1437→CwScreenBoxPick/祈愿试炼 :1453/星徽秘典弹窗 :1458/投资环境 :1598→CwScreenInvestEnv);PREP_DIRECT_EXIT_SCREENS 两成员与映射不相交;「已 None 跳过」落挂点侧、leave_screen 本体不动的分工与现 API 语义相符;strategy 锁定/开商店等映射外臂清十槽无害走查(无 decide 消费);invest 重入轮次轮路由保槽(只清属屏 ≠ 它)语义自洽。
- **§2.2-c 瞬态槽三分语义与刷新链三屏形态**:零选项不调 decide(encounter :296/:431、supply :222)与「写槽以将调用 decide 为前提」判别信号对应;encounter 同调用内重读重决策(:331-337/:461-467)、supply 发射 return + round_retry 重入(:233-265,:346-364 lifecycle 同经 _do_action 单一 decide 点)、invest 交回重入(screens/README.md:78/:112 正本与码一致)——三屏分形态申报与码逐屏吻合,无统一改形歧义。
- **§2.1-4 refresh 旗标等价**:supply 入口读同字段派生式逐字节等价;encounter per-visit 位四格逐路径推演与现状无分歧;累计计数不进入口的禁类论证与 kernel 刷新建议枝两枝可分叉一致;写 False/True 同型可靠性 + `cw_match` None 守卫缺席跳过已定死;读侧 None 缺省 False 先例(megastar_clicked getattr,cw_screen_megastar.py:157)实证;跨 handle 无读面成立(旗标仅入口读,新访问首调前置先复位)。
- **prep_obs 非 Field 化论证**:PrepObservation 实含 `set`/`Point`/`BenchChar`(cw_prep_actions.py:68-82/:70)非 JSON 形状,spheres 发射面消费 Point;快照 restore rebuild 面不涉非 Field 字段——可观测面与现状 session 槽一致的申报成立。
- **阶段可验收性逐阶段试读**:3.1 纯增量(新槽无人写读、live 恒 None 清点 no-op、新字段无写者无读者)= 零行为独立绿;3.2(prep 线 2 调用点 + bridge 唯一实现 + 读者全集换源 + 两测试文件 census 可达)、3.3(flow 实现 + bridge 覆写体调用点 + buy_cards:1099 全收同阶段)、3.4(13 契约调用点 + 10 handler + 2 actor 登记 + invest 拆分全收同阶段)各线读写点/签名/调用点/测试锁不跨阶段;3.5/末阶段依赖闭合。
- **在飞对账**:execstate 6/6 done + 正本清零(README + commit ee1f4e337 git 直查)、turnstate 3/3 done(7b50d690f/170d8366f/b6e88a902 均实存)、unified-obs 3/5(3.3 落码 done + 实机验证候窗,3.4 依赖 3.3、其文件面含 cw_screen_prep.py/cw_screen_buy_cards.py 与本批 3.2/3.3 相交属实;3.1 阶段面与其剩余阶段零交集属实)——§2.8 表成立。
- **词表普查兜底充分性(独立重跑)**:九接口/五计数词形态正本树命中(flow/README 六处、session.md:14、strategy-docs/README.md:33/:60、13 号篇:1、25 号篇:4、screens/README.md:107、expert_invite.md:12、fortune.md:11)全被词表兜住;`PickBoxCard` 正本残留(25 号篇:19、18 号篇 §7、screens/prep.md 历史节)被词表 + 清单两行兜住;`prep_obs_frame` 正本命中(flow/README:71、session.md:54/:135、projection_contract.md:13/:93、action-logic-state.md:50、open-bookcard.md:13)全在清单行或普查辖内;`refresh_used` 命中(screens 两篇、docs/game/screens 两篇 :39、fields.md §3.4、game_state/README.md:83)在册;sr-od-test 独立仓 git grep:decide_invest 1 文件/prep_obs_frame 2 文件/Encounter·SupplyPayload 0/PickBoxCard 0——全部落在对应阶段测试翻新面;kernel 无 decide_invest 同名函数(F5 修复后豁免语已改对)。

### 核二(规范遵循)

- **四硬规则逐条**:依据就地标注(关键主张均带源,抽查密度高);实现者无需再设计(除 M1/M6/M7 三处枚举/桶缺口外,逐阶段试读可开工);无过程叙事(design/landing 正文无轮次号/修订叙述;r10-F6/R9-4 类残留已清);全量同步复查(design↔landing↔README 判据数值一致:四格、计数 12/13/14、十槽、八域键、两 bump 逐字对账)。
- **r8-r10 修复落地逐项复核(全部在现文)**:F1/R9-2 挂点辖域与「未识别 = 清全部十槽」+ 早退绕行无害申报 + 3.1 双剧本断言;F2 三屏刷新链分形态;F3 写 False/True 同型失败语义 + None 守卫;F4 清单补面(session 计数句/strategy-docs README §3/expert_invite+fortune/九接口双口径申报);F5 豁免语改对;F6 计数句归 3.4;F7 归属判据双锚(flow/session.md §2 + fields.md §8.8);F8 README 收紧为「零发现轮」;F9 shop 映射内豁免 + leave_screen 守卫放宽申报;F10 防御路径行改「零改动」;R9-3 PickBoxCard 词表 + 18 号篇行;R9-4 过程句删除。
- **形式项**:三文档构成齐;阶段小节七件齐(3.1-3.5 + 末阶段逐一对照);通用工程门单点定义 + 各阶段引用式;design §0 状态(对抗审中)与 README 进度同步;标题层级合规;README 构成合规(攻击报告链接 attack.md-attack10.md 实存)。

### 核三(治本)

- **§1.2 归层成立**:契约形状从未立统一约定、容器 payload 域治理规则已在而「决策输入唯一承载」未立——约定层定性准确(非语义层:每帧喂给策略的事实本身无争议)。
- **§2 修根判定**:签名一次统一 12 入口 + 决策输入单源入容器 + 唯一写者表 + 离屏机制 = 约定与机制本体的结构收编,非逐点补丁;kernel 纯函数零触碰的边界论证成立(输入来源组装归调用方);症状修法的战术权衡均显式(per-visit 位 vs 语义统一登记不解决、prep_obs 豁免、payload 内容扩展归行为批)并带排期(后批/行为批/帧机制合并批)。
- **同族检查**:本批是商店线黑板容器化的延续收编(输入承载首次系统化),终态方向(构造注入/零参/Session 解散/StrategyState 显式化)显式登记自成后批——非第 N 件症状补丁模式。

### 行为零变化专攻(申报专列逐线)

- 新写端量级(journal 行经 _swap、write_seq 位移、`ChannelSig.group_id` 随 `gs.write_seq+1` 形态 flow.py:766-768/bridge.py:257-259)、路由清点增量(真离屏转换帧每槽至多一行)与 §2.6 申报吻合。
- 路由清点时序两路径语义(早退绕行单轮窗口/未知兜底不绕行)经 loop 行序走查成立(M3 表述层残留除外)。
- refresh 旗标等价(见核一);prep_obs 读者封闭(3 读点全集,普查兜底);每阶段切换线独立可绿(见核一);快照 restore 不对称(encounter/supply 升级形状经直透落 dict、shop 手写重建不扩展——与 restore_state_snapshot 现形态申报一致);actor 登记义务(缺席面恰两点,精确);瞬态槽判别信号与现码 `match is not None and options` 支结构一一对应。

## 结论

无 blocker,无 major。7 条 minor 均为清单锚精度/文件面依据标注/判据桶定义/总纲枚举补句级别的局部修订,不动摇方案本体与等价性论证;逐条消解后可进入零发现复攻轮。
