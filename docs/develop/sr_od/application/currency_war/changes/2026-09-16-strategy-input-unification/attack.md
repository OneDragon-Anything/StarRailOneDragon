# 策略器决策输入统一 · 无前提对抗审查报告

> 审查对象 = 本目录 design.md / landing.md / README.md。判据源 = iteration-design.md(形式门)、strategy-docs 00/01(宪法)、game_state/fields.md、flow/README.md + flow/session.md、strategy-docs 13/22/23/25、在飞迭代四份(execstate-dissolution / turnstate-retirement / unified-obs-reconcile / chain-observation-landing)、AGENTS.md §8/§9、strategy-work.md §6。代码断言全部直调 `src/sr_od/application/currency_war/` 复核(行号为 2026-09-16 时点,仅定位用)。
> 结论无和稀泥项:三核全部有发现。blocker 4 / major 7 / minor 10,共 21 条。

## 1. 发现清单

### blocker(定稿门槛问题)

**[BLK-1] `leave_screen` 域集遍历与 prep/shop 覆盖嵌套结构冲突,等价性断言不成立,改后 prep 环会断**
- 位置:design.md §2.2 配套契约「离屏置 None 收口单点化」(design.md:87)。
- 内容:设计主张「既有逐槽调用点改域集遍历后行为等价(多置 None 的槽本就属离屏语义)」。直调复核:**不等价**。既有 live 逐槽调用点只有两处,全部发生在**备战屏仍在屏**的语境:`kernel/cw_game_state.py:2029-2034`(CloseShop 逻辑腿,`gs.leave_screen(gs.shop, …)`——关店后流程仍在备战屏,紧接的 finalize/节点探针/备战单动作循环会再次调 `decide_prep_screen`)与 `obs/cw_observation.py:2617-2619`(prep 相位观察中商店锚 miss 分支)。域集遍历 = 这两处会一并清掉 `gs.prep_obs`;而槽位表 #1 明确 prep_obs 属画面附加域全集(在域集内),且 §2.1-2 规定 payload None = 观察层失约抛错(`bridge.py:179-184` 现行同型)。商店对备战是**覆盖态**不是兄弟屏(fields.md §3.3 开篇),「当前画面 payload」模型在此不自洽——关店不是「离开备战画面」。改后首次关店即触发 decide_prep_screen 抛错,行为零变化被直接证伪。
- 修正方向:放弃单一全域集合。把画面附加域分两组(覆盖层 payload = shop;屏 payload = prep_obs 与各 pick 屏域),`leave_screen` 只清覆盖层 + 与当前屏绑定的域;或保留逐槽语义、由调用点显式声明辖域。等价性论证须逐调用点重写。

**[BLK-2] `refresh_used` 改容器读在 encounter 入口产生可读决策输出分歧,行为零变化申报被证伪**
- 位置:design.md §2.1-④(design.md:62)、§2.5 申报「决策输出相同」(design.md:114)。
- 内容:现状 encounter 调用方首调**不传旗标**(缺省 False,`cw_screen_encounter.py:304/439`),仅后刷重决策传字面 True(:336-337/:466-467);「已用」的闸在 handler 侧读容器计数(:320-325/:452-457,命中时打「建议刷新但本局已用→按原评分选」并**不重决策**)。改成入口内部读 `encounter_refresh_used` 后:同局第 2+ 个遭遇节点(计数>0,写端=发射型钩子,局内累计不复位)首调即见 True——
  - 现役 mandate 核(`cw_encounter_selection.py:337-389`):选择 idx 恰好两枝同为最低档,但 `PickEvent.refresh` 旗标(True→False)、reason 串、handler 的「本局已用」日志分支全部变化——decisions 行/遥测判读面可见;
  - 基线核(`cw_events.py:670-672` 刷新建议枝返回 `idx=options[0].idx`,True 时走评分枝取最优):**选择 idx 可分叉**,flow 中间层缺省路径与既有单帧锁辖面行为改变。
  设计对这条路径零讨论;§2.5 的验证主凭据也抓不到它(见 [BLK-4])。
- 修正方向:二选一并写入设计:①申报这是语义修正(行为批),列明分歧路径与判读锚;②保持等价语义——入口只在「本访问已发生刷新后的重决策」语境读容器,handler 闸与日志保留。
- 附:supply 侧无此问题(调用方现状就传容器派生旗标,`cw_screen_supply_node.py:210-211,230-232`);后刷重决策路径等价(`_emit_refresh_click`→on_outcome 钩子同步写计数,`cw_screen_encounter.py:144-175`)。

**[BLK-3] prep_obs 迁移漏 kernel 读者 `cw_equip_wear_plan.py`,槽位表读者列与迁移面不全,且与自身判据矛盾**
- 位置:design.md §2.2 槽位表 #1(读者列只写 decide_prep_screen,design.md:71)、§2.4;landing.md 3.1/3.2 文件面(landing.md:9/23)。
- 内容:直调 `session.prep_obs_frame` 全集——写点 4 处全在 `cw_screen_prep.py`(:549/:914/:1617/:1781,设计的写者白名单成立);但**读者**除 bridge(:179)与 cw_screen_prep(:1883)外,还有 `kernel/cw_equip_wear_plan.py:163`(`getattr(session, 'prep_obs_frame', None)`,装备穿戴计划构造的**唯一事实源**,fail_reason='备战观察帧缺失' 通道)。该文件不在 landing 3.1/3.2 任何文件面;若按文件面施工,槽删除后此 getattr 恒 None → M7 穿戴计划每帧 fail(行为变化);若 worker 自行补改,则撞「文件面=本阶段允许动的文件」边界。同时 3.1 完成判据「`prep_obs_frame` 符号全仓归零(代码面)」与该文件面直接矛盾。
- 修正方向:槽位表 #1 读者列补 `cw_equip_wear_plan._build_equip_wear_plan`(及 `mandate_v1/shop.py:11`、`bridge.py:11` 等 docstring 锚的处置归属);landing 3.1 文件面补 `kernel/cw_equip_wear_plan.py`(并注明该读者在「同点改名」外还需改宿主解析:`session.` → `game_state_of(session).`);参照 execstate-dissolution 先例补「注释历史锚随正本批处置」句。

**[BLK-4] 验收主凭据与改动面结构错位:cw_replay 零漂移对本批实际改动面结构性零覆盖**
- 位置:design.md §2.5「零漂移 = 本批验收主凭据」(design.md:117)、§2.4 sim 行(design.md:107)。
- 内容:设计自证「sim 引擎不调 pick 入口、不建模 prep_obs、prep 面 sim 不可达」——即本批四大改动面(pick 族 10 handler 的写槽-调 decide 链、encounter/supply 活写端接通、离屏置 None 收口、prep_obs 迁移)全部在 sim/回放**不可达域**;replay 唯一消费的 `decide_shop_screen` 驱动器路径本批「签名不动」。故「零漂移 = 主凭据」对能出事的面**只能产出空真**(`no不变` ≠ `验证过`),strategy-work §4「缺声明的对照 = 假阴性高危」在此以验收面形态复发。单帧锁/拆分对照(landing 3.2/3.4)只锁 decide 层,handler 接线与离屏写端无锁。
- 修正方向:把主凭据改为「单帧锁/契约锁 + handler 级行为锁(encounter 闸分支/空选项分支/写槽后调 decide 的单源链)+ L1/L3 + 实机预测锚点」;replay 零漂移降级为「shop 驱动器路径未受扰」的旁证,并在 §2.5 显式写明其辖域局限。

### major(须修)

**[MAJ-1] 「invest 策略屏逐卡读 strategy_refresh_used」无消费路径,篇内自相矛盾**
- 位置:design.md §2.1-④(design.md:62)。
- 内容:`decide_invest` 现状无 refresh 输入(§1.1 自己也只列 supply/encounter 带该形参);kernel `cw_events.decide_event` 签名不收计数(`cw_events.py:204-206`),逐卡闸全在 handler(闸1 屏上余量现读/闸2 容器计数/闸3 L1,`cw_screen_invest_strategy.py:425-459`);设计又锁 kernel 零改动(§2.6)。则入口「读 strategy_refresh_used」读来无处可去——疑似把 execstate-dissolution #6 的 handler 闸2 误写进入口契约。实现者撞上即需再设计。
- 修正方向:删去该半句,或写明它只是 handler 闸2 的既有事实引用而非入口新读。

**[MAJ-2] §1.1 现状断言「调用方从执行侧旗标取值传参」与代码不符;前置依赖的实质内容被高估**
- 位置:design.md §1.1(design.md:17)、§2.6 末条、§2.7 前置①「refresh_used 容器读口的字段位」。
- 内容:直调复核——①`kernel/cw_exec_state.py` 已无任何 `*_refresh_used` 字段(全文仅注释残留);②supply 调用方传的是**容器派生**旗标(非执行侧旗标);③encounter 首调传缺省 False(见 [BLK-2]);④容器字段位与 live 写端**已在产**:`gs.encounter_refresh_used/supply_refresh_used/env_refresh_used/strategy_refresh_used` 定义于 `cw_game_state.py:2757-2760`,写端分别在 `cw_screen_encounter.py:144-167`、`cw_screen_supply_node.py:239-254`、`cw_screen_invest_strategy.py:310-334`。execstate-dissolution #4-#6 删的是 ExecState 半边并收口读点,并非「交付字段位」。「落地后的字段位」前提失真 → §2.7 前置的真实内容只剩同文件冲突排序(该排序成立,应如实改写)。
- 修正方向:改写 §1.1 症状句与 §2.7 前置①为「容器读口与写端已在产;前置 = execstate 收尾消除 ExecState 双源与同文件在飞面」。

**[MAJ-3] 槽位表 #3/#4 类型名 `EncounterObs`/`SupplyObs` 无处落码,改名未申报**
- 位置:design.md §2.2 槽位表(design.md:73-74)。
- 内容:现符号 = `EncounterPayload`/`SupplyPayload`(`cw_game_state.py:610/617`;fields.md §8.1-8.5 结构类型正本同名)。设计直接写新名且未声明「改名」动作;worker 按表找符号落空,正本更新时也会与 fields.md 撞名。
- 修正方向:沿用现名,或显式申报改名并列入 gs_schema/正本更新面。

**[MAJ-4] invest 槽类型「注册表规范卡名」与现决策输入(OCR 原文名)冲突,违反行为零变化**
- 位置:design.md §2.2 槽位表 #5(design.md:75)。
- 内容:现状进 decide 的是 OCR 原文名(`cw_screen_invest_strategy.py:394`),kernel 判据对**原名**做 eval-lcs 形变裸分与品质回落(`cw_events.py:233-236`、:278;ADR-0144b 跨表守卫也按原名)。若槽按表存规范卡名(normalize_invest_name 归一——该口径本属 `strategy_refresh_used` 计数键,fields.md §3.4.4),decide_event 收到的字符串改变 → 形变帧评分/归因变 → 决策可变。「每帧同输入值」申报不成立;若本意是存原名,则标签错(「值对标签错」类)。
- 修正方向:槽类型标注改「OCR 原文名(与现 decide 输入逐字节一致)」;规范名归一只归计数键,不进决策输入。

**[MAJ-5] 在屏失读/空选项语义未定义,「沿用旧值」规则对瞬态选项槽产生陈旧消费风险**
- 位置:design.md §2.2(在屏失读处置沿用 fields.md §2.2)、§2.1-2 在屏前置。
- 内容:fields.md §2.2 画面附加域规则「在屏失读不写、沿用旧值」是为持久游戏事实设计的;对逐访问瞬态的选项槽,第二节点同型屏 OCR 全 miss 时槽内是**上一节点的选项**,入口按「非 None 即在屏合法」消费陈旧列表,handler 却按当局画面点击——idx 与卡面错位。[]与 None 的分界(零选项是 `[]` 还是 None)、OCR 全 miss 时是否调 decide(现状 handler 零选项直接盲点默认、不调 decide,`cw_screen_encounter.py:296/431`)均未规定。
- 修正方向:为新槽显式定义三分语义(离屏=None / 在屏失读=保留上帧**并声明本屏不再消费旧值直接走失败安全** / 在屏读得=覆盖,含零选项=[]时的入口行为),写入槽位表配套契约。

**[MAJ-6] 离屏置 None 对新域在 live 无触发写端,不变量落空**
- 位置:design.md §2.2 槽位表「离屏置 None」列语义、配套契约二。
- 内容:live 既有 leave_screen 调用点仅 shop 域两处(见 [BLK-1]);encounter/supply 离屏清点只存在于 sim 合成口(`cw_game_state.py:3973-3974/:4266-4268`)。8 个新 opts 域 + 接通后的 encounter/supply 在**画面退出时无任何调用点**——「非当前画面 = None」在 live 只能惰性等到下一个 shop 边界,期间违反 fields.md §2.2 结构事实语义;「进决策 None = 观察层失约」守卫因 None 态几乎不出现而空转;§2.6 的「dump gs 即重建策略当时看见什么」审计主张被陈旧非 None 槽破坏。设计未指定新域的离屏写端挂点(画面 op 出口?外循环路由?)。
- 修正方向:为各 pick 屏域指定离屏写端(建议 = 画面 op 出口/外循环画面切换点统一触发域集清点),并在配套契约中写明触发时机与 sim 口的关系。

**[MAJ-7] 跨文档引用锚不存在(硬规则 4「全量同步复查」靶点,两处)**
- 位置:①design.md §2.1-④「见 §4 依赖」(design.md:62)——design.md 无 §4(依赖表在 §2.7);②design.md §2.7「unified-obs-reconcile 3.4–3.5 收尾」(design.md:136)——该迭代 landing 只有 3.1–3.4 + 末阶段,README 进度「阶段 3/5」即 3.1/3.2/3.3/3.4/末,不存在 3.5。
- 修正方向:①改「见 §2.7」;②改「unified-obs-reconcile 收尾(3.4;3.3 实机验证期候窗)」。

### minor(建议)

**[MIN-1]** design.md §2.2 配套契约自称「四条」(landing.md:8 同引),实列五条(gs_schema 申报/离屏收口/选项单源/prep_obs 迁移/注释归属)。计数标签改五或合并条目。

**[MIN-2]** landing.md 3.2 文件面「`entry.py`(如签名传导)」=「看情况」措辞,违 iteration-design §5-2(硬规则 2 卡点:看情况/待定/酌情 = 未定稿)。应写死:ABC 加 gs 后 bridge/flow 调 `decide_from_turn`/`entry.emit` 的形参是否传导、与 turnstate-retirement 对同链(`decide_from_turn` 改名删 turn 参)的先后次序下的最终形态。

**[MIN-3]** landing.md 3.1–3.5 与末阶段的完成判据均缺「§12 通用工程门(引用,不复述)」行——iteration-design §3.1 阶段七件之一(unified-obs-reconcile landing 在册对照可查)。

**[MIN-4]** README.md 文档节缺「落地:[landing.md](landing.md)」行——iteration-design §4 模板固定构成,landing.md 实存。

**[MIN-5]** §2.2 配套契约「gs_schema 申报」只覆盖 #5–#12 与 #3/#4,**漏 #1 prep_obs 新域登记**(fields.md §3.7.1:缺域键 = 未建模);且 #5–#12 是 8 个独立域键还是并入既有分组未写(实现者裁量点)。landing 3.1 判据「新域/变域登记」能兜住执行,但设计面应补齐。

**[MIN-6]** §2.7 冲突文件面清单不全:execstate-dissolution 实际文件面还含 `cw_screen_prep.py`(3.2/3.5)、`cw_screen_buy_cards.py`(3.5)、`obs/cw_observation.py`(3.5)、`kernel/cw_strategy_session.py`(3.2 头注),全与本迭代文件面重叠;turnstate-retirement 面含 `cw_screen_buy_cards.py`(import 路径)与 `entry.py` 也未列。收尾排序兜得住,但作为冲突声明失真。

**[MIN-7]** §2.1-④「`node_screen_refresh.supply_refresh_used`」是伪路径:域 'node_screen_refresh' 仅是 `DEFAULT_GS_SCHEMA` 版本键分组(`cw_game_state.py:146`),实际访问 = `gs.supply_refresh_used` 顶层字段(:2758)。worker 按表找属性落空(标签类)。

**[MIN-8]** 正本更新清单 25_event_overlays.md 行「事件面画面输入面同上」:该篇画面族含 选择装备(cw_equip_pick)/命运卜者/专家邀请函 等无 pick 接口、本批无槽的画面,更新范围未界定(改什么/不改什么)。

**[MIN-9]** 配套契约「域集 = schema 画面附加域清单,单一源」:代码已有现成锚 `_PAYLOAD_DOMAINS`(`cw_game_state.py:171`,恰含 shop/encounter/supply),设计未提;且 `DEFAULT_GS_SCHEMA` 本体无「画面附加域」分类标记——应写明单一源 = 扩展 `_PAYLOAD_DOMAINS` 还是为 schema 增分类维度,避免双源。

**[MIN-10]** 新容器写入面的可观测性变化未申报:接通后的 encounter/supply/8 新槽观察写入改变 journal 行量与 `write_seq`(下游 `ChannelSig.group_id` 字符串随 `gs.write_seq+1` 位移,`bridge.py:261-263`),快照行 gs_prov 将出现新域(fields.md §8.8 遥测行形状规格)。strategy-work §4 的 sim 可观测性声明已写,但 live 判读面(日志/快照行/journal 体积)的申报缺位。

## 2. 三核结论与实际攻击过的面

- **核一(无前提)**:非零发现([BLK-3][BLK-4][MAJ-5][MAJ-6][MAJ-7][MIN-2][MIN-5] 等)。攻击过的面:decide 调用点全集普查(ABC 12 入口 × 全仓 grep:prep×2 / shop×1 / buy_cards 循环+防御 / 10 pick handler / bridge、flow 两驱动器 / cw_replay / planner 与 invest_strategy 局外防御路径)——**入口/调用面覆盖本身无遗漏**(12 入口、10 handler、两调用点计数均与代码吻合);跨文档引用锚(design↔landing↔正本↔在飞迭代四份);阶段可验收性逐条试读;「实现者无需再设计」试读(撞点:[MIN-2][MAJ-5][MAJ-1]);槽位表逐槽对代码与 fields.md。
- **核二(规范遵循)**:[MAJ-7][MIN-1][MIN-2][MIN-3][MIN-4](出处均标 iteration-design 具体条);依据就地标注总体达标(关键主张带符号锚/文档节),无过程叙事违例,状态/进度仅在 README(合规)。
- **核三(治本)**:§1 归层「约定层」成立——签名三形状与「payload 域未定为唯一承载」确属约定缺失,非表示/语义层;§2 方向(统一契约 + 容器单源)是治本而非症状,且与商店容器化既定方向同轨、后批(构造注入/Session 解散)已显式立项,不属逐件打补丁。**但**治本的两根承重柱——离屏置 None 机制([BLK-1][MAJ-6])与行为零变化验收([BLK-2][BLK-4])——按现稿不成立,治本结论成立、机制细节须返工后再定稿。
- **行为零变化专攻**:四条攻击线(域形状升级×快照/回放消费、leave_screen 域集等价性、refresh_used 时间窗差、invest 拆分内务次序)全部落锤:第一条=新写端改变 journal/write_seq/快照([MIN-10],决策面本身安全,encounter/supply 域现无消费者);第二条=[BLK-1];第三条=[BLK-2][MAJ-2];第四条=拆分次序经与 flow.py:469-515 逐段对照**未发现分叉**(共享段顺序与现实现一致)。
- **声明**:本报告零发现面 = invest 拆分本体(§2.3)、契约成员计数(13→14,与 flow/README §2 及代码一致)、返回类型表、sim 不调 pick 入口/不建模 prep_obs 断言、防御路径三条纪实(planner/buy_cards:834/invest_strategy)、prep 写点白名单(4 点全在 cw_screen_prep.py)、cw_screen_buy_cards/planner/sim 各调用面描述。
