# 设计对抗报告

> 审查对象 = 本目录 design.md / landing.md / README.md(草案态)。审查基线:docs/develop/harness/iteration-design.md 全文(§5 写作硬规则四条 / §7 三核)、项目 AGENTS.md(§8/§9/§10)。判据源全部直调复核:三份设计文档、op-layer.md(§1.1/§2.1/§2.2/§3)、plane_intel.md、prep.md、fields.md(§6.4/附录表)、docs/game/screens/货币战争-位面详情.md、代码锚逐个打开(cw_screen_plane_intel.py / cw_screen_prep.py / cw_entry_plane_intel.py / kernel 三屏文件 / cw_game_state.py / cw_projection_audit.py / cw_briefing_obs.py / cw_comps.py / telemetry/schema.py / briefing·encounter·megastar 屏文件)、sr-od-test 契约与形态锁测试、fixture 目录 glob + **read_image 亲验**。零转述。

## 发现清单

### A1 六 node 管线规格未处置现役 op 内四个存续附属机制,其中两个的输入头寸被新前提消灭

- 核:核一·无前提(边界完整性 / 实现者无需再设计)
- 位置:design.md §2.2 / §2.4 / §2.6
- 问题:现役 CwScreenPlaneIntel 除三位面 boss/词缀采集与 ctx 中转外,还承载四个活机制;§2.2 的 6 node 规格、§2.4 退役清单、§2.6 保留清单**三方都没提它们**——①节点序列互证(`_cross_check_node_seq` + 纯函数 `node_seq_cross_mismatch`,输入 = 备战帧节点序列快照);②节点类型台账两源落账(`ledger_update_plane` 'prep_row'/'plane_detail' + `fill_boss_by_position` boss 位回填);③敌人难度参考值(`read_plane_detail_difficulty` → `ledger.difficulty_ref`);④词缀效果账本登记(`register_affixes_from_names`)。实现者按 §2.2 重建 6 node 时,每个机制都面临「去留 + 挂点」的临场拍板,违反写作硬规则 2。更具体的结构性后果:②的 prep_row 源与①的备战快照住在现役备战入口分支(cw_screen_plane_intel.py:456-491),而 §2.2 新前提「已在位面详情屏为前提,node1 非详情屏 = round_fail」**直接消灭该分支**——想保留也没有输入;④在接管局是词缀登记唯一活源(简报侧登记挂点 cw_screen_briefing.py:110-112 在接管局不运行;cw_affix_effects.py:20 自述「简报/位面详情」双挂点),静默丢失 = 恰在本 op 服务的接管场景丢效果账本登记。
- 证据:cw_screen_plane_intel.py:456-491(备战快照 + prep_row)/:570-595(互证 + 难度参考)/:697-736(登记 + 台账落账);cw_screen_buy_cards.py:1207(台账另有跨 op 写点,证明是活机制);plane_intel.md §6(台账「详情条源为主」定位);cw_affix_effects.py:20;design §2.4 退役枚举与 §2.6 保留枚举逐行比对均不含四机制。
- 建议:§2.2 逐机制写明去向——随采节点保留(给挂点)/迁入 node6/随备战分支消亡而正式退役(补进 §2.4,并写明台账 prep_row 源与互证的替代输入或明确放弃);④至少进 §2.6 明确保留并给新挂点。
- 已消解(部分):design §2.2 新增附属机制处置表,②④挂 node6 簇可实现(session/gs 分通道与「先例 = 备战现行链写端」经核实成立)、prep_row 源随恒全采由 plane_detail 源+回填闭环成立;残留两处转新发现——③保留挂点只读位面1 与现役逐位面读矛盾(→A14)、①退役依据与机制实际职责不符(→A15)。

### A2 「对账网迁入 kernel 屏文件」撞分包矩阵,函数体搬迁面未定

- 核:核一·无前提(实现者无需再设计)
- 位置:design.md §2.3;landing.md §3.1 范围
- 问题:§2.3 把「简报 vs 实采对账网」列进 kernel report 写门的迁入面(kernel/cw_screen_report/plane_intel.py 转正),但 `reconcile_briefing_vs_plane_intel` 与 `briefing_reconcile_pairs` 住 obs/cw_briefing_obs.py:212/:177;op-layer.md §2.2 判断线明文「kernel→obs 直依被分包矩阵禁止,观察侧纯函数以『函数体搬进』kernel 屏文件的方式落地,不是 import」。设计未说哪些函数体搬、obs 旧位是否退役(不退役 = 第二抄本漂移);实现者要么违规 import、要么自行定搬迁面。
- 证据:op-layer.md §2.2 判断线原文;cw_briefing_obs.py:177/:212;依赖的 `find_best_match_by_lcs`/`longest_common_subsequence_length` 住 one_dragon/utils/str_utils.py:107/:47(kernel 可依,搬迁可行但须设计指认)。
- 建议:§2.3 补搬迁清单(两函数体进 kernel 屏文件,obs 旧位退役);或改口径为「对账调用留守 op 层、kernel 只承载写门」并同步改 §2.3 表述与 3.1 范围。
- 已消解:取退役口径(三选一之①)——design §2.3 对账网退役定稿段 + §2.4 退役行;obs 两函数零消费删除经 grep 核实(全库消费仅 entry 挂点 + 模块自身);config 字段处置指令可执行(行为消费唯一 = cw_entry_plane_intel.py:184,字段面 currency_war_config.py:99/:126 已入 3.2 文件面)。

### A3 设计两处引用已退役机制 REGISTERED_ACTORS;统一写门的 family/actor 在三现役形状间未指认

- 核:核一·无前提(依据标注不实 + 语义选择未定)
- 位置:design.md §2.3;landing.md §3.1 文件面
- 问题:①现役代码已无 `REGISTERED_ACTORS`:全 src grep 零命中;`_validate_sig`(cw_game_state.py:353-361)现役只校验渠道族,docstring 明言「actor 仅作遥测/台账行的动作身份标注,不设白名单闸」(2026-09-16 迭代期该注册表还在 cw_game_state.py:285-336,此后被拆)。design §2.3「沿用已注册 actor,REGISTERED_ACTORS 零扩面优先」与 landing 3.1「若 sig 对齐需动 REGISTERED_ACTORS,只允许 kernel/cw_game_state.py 渠道常量」均悬空——实现者按停手令回查会查无此物。②注册闸失效后,统一写门的 ChannelSig 成自由选择,而 gs.plane_bosses 现役有**三个**不同写端形状:`CwScreenBriefing`(family='logic_action', briefing.py:53-54)、`ResumeAttach`(family='logic_hook', kernel/cw_screen_report/prep.py:92-93)、`CwEntryPlaneIntel`(family='logic_action', cw_entry_plane_intel.py:166)——两处原写点迁并后沿用哪个,直接影响 journal 归因与审计行 basis,设计未指认(「先读 CwScreenBriefing 渠道形状」只给调查入口不给答案)。③op-layer.md §2.1 正本同样残留 REGISTERED_ACTORS 表述,而正本更新清单的 op-layer.md 行只列 §3 → 陈旧表述穿过本迭代继续存活。
- 证据:grep src `REGISTERED_ACTORS` = 0 命中;cw_game_state.py:353-361;三写端形状原文(上列行号);op-layer.md §2.1(:63)。
- 建议:§2.3 直接定死统一写门 sig(按 op-layer §2.1「sig 逐位沿原值」规则写明两原写点合并时沿用哪份、为什么);landing 3.1 删 REGISTERED_ACTORS 条款;正本更新清单 op-layer.md 行补 §2.1 陈旧表述清理。
- 已消解:sig 四元组 + evidence 定死、REGISTERED_ACTORS 措辞全文删除、正本清单 op-layer.md 行补 §2.1 清理,均落地;sig 依据标注与实定 screen 值的失真转新发现 A17(低)。

### A4 退役清单配套义务漏两项:审计申报行(在 3.4 文件面之外)与 match_facts 域版本 bump

- 核:核一·无前提(判据可达成性)
- 位置:design.md §2.4;landing.md §3.4 文件面/判据
- 问题:①kernel/cw_projection_audit.py:146-151 有 `takeover_collect_done`/`takeover_tries` 两行申报,且该表自带字段退役完备性锁——`audit_stale_keys`(:347-349,「本表中已不存在的字段键(字段退役后残留)」)在字段删除后必报孤儿键;3.4 文件面(cw_screen_prep.py、kernel/cw_screen_report/prep.py、kernel/cw_game_state.py、kernel/cw_comps.py、telemetry/schema.py + 测试)**不含 cw_projection_audit.py** → 「全库零残留」判据在本阶段文件面内不可达成(worker 越面改或停手申报,两者都是本可一行修掉的流程损耗)。②两字段宿主 = match_facts 域(cw_game_state.py:2169-2171,域版本 2),删域内字段 = 域内容变更,按仓内既定约定需 bump `DEFAULT_GS_SCHEMA['match_facts']`(先例 = 载体解散迭代 3.5「接管/恢复三字段迁入 = 域内容变更」即 bump 至 2;test_cw_game_state_contract.py:180 钉死 `== 2` 断言)——bump 则该断言必翻新,不 bump 则行内嵌 gs_schema 快照与域内容失配;design/landing 均未提。
- 证据:cw_projection_audit.py:25(维护纪律)/:146-151/:347-349;cw_game_state.py:158/:164/:2169-2188;test_cw_game_state_contract.py:170-194。
- 建议:§2.4 补两行(审计申报行随字段退役;match_facts bump + 合同断言翻新);landing 3.4 文件面补 kernel/cw_projection_audit.py,判据补域版本与完备性锁绿。
- 已消解:§2.4 补 bump(2→3)+ 合同断言翻新 + audit 两行申报;landing 3.2④ 收录(文件面含 cw_projection_audit.py,判据含域版本断言与 audit_stale_keys 绿)。

### A5 prep 侧新触发判定与委派失败语义未定稿(定稿试读不过)

- 核:核一·无前提(实现者无需再设计)
- 位置:design.md §2.1 / §2.2;landing.md §3.4 范围
- 问题:§2.1「判定接管(`gs.plane_bosses` 未观察)→ 委派 CwEntryPlaneIntel → round_success 交回外循环重识别」三处语义选择无答案:①「未观察」谓词未定义——plane_bosses 是普通 Field(cw_game_state.py:2198),**不在 tracked 账**(`tracked_unobserved` 单一源 :1954 辖 tracked_books,不含它),「未观察」= 值空(现役门 `.value` 真值,cw_screen_prep.py:869)还是引入显式失效标记?另现役门还有「节点条可读」半开帧守卫(prep:871-875)与 takeover_collect_done 闩,done 退役后重触发节奏是否等价替换未说。②委派失败时 prep 返回什么未定:沿现役无条件 round_success(prep:914)= 外循环每轮重触发、备战↔详情开合自旋(靠 op-layer §1.1「挂起可观测」兜);还是经 round_by_op_result 传播 fail 熔断——两者都「响亮」,形态完全不同,§2.2「响亮失败显影」未指认端到端形态。③识别 op fail 后位面详情屏留场处置未声明:现役 `_best_effort_close_detail` 在失败 op 内部;新形态关闭转场归 entry 的关闭 node,宿主 op fail 后该 node 不运行,残留屏靠外循环位面详情分支兜底——是否接受该兜底未写。
- 证据:cw_screen_prep.py:869/:871-875/:914;cw_game_state.py:1954/:2198/:2282-2292(tracked_books 载体);op-layer.md §1.1;design §2.1/§2.2 全文。
- 建议:§2.1 补三句——触发谓词(建议 = `not gs.plane_bosses.value` 逐字替换现役两臂,并明示可读守卫去留)、子 op 失败的宿主返回语义、失败转场处置归属。
- 已消解(部分):三问三答落地(触发谓词/委派经 round_by_op_result 透传/留场靠 entry 直通分支自愈),谓词与透传机制经现役代码核可实现;可读守卫退役的依据失真与档位变化未申报转新发现 A13(中)。

### A6 同一契约迁移跨阶段拆分:3.2 拆构造签名与 ctx 写点,调用方适配在 3.3/3.4——阶段中间态接管链破

- 核:核一·无前提(阶段粒度)
- 位置:landing.md §3.2/§3.3/§3.4
- 问题:3.2 完成态下:构造签名已改 `(ctx)`、ctx 写点已删,但 cw_entry_plane_intel.py:119 仍以 `start_plane=` 调用(3.3 才「start_plane 读取退役」)、cw_screen_prep.py:899 同(3.4 才删整方法)、prep:901-904 仍消费已停写的 ctx 通道 → 3.2↔3.3 窗口 entry 路径(MCP run_operation 手动调起,§2.6 明确保留的能力)构造即 TypeError;3.2↔3.4 窗口 prep 接管链同样破。测试不拦(sr-od-test 全仓 grep `start_plane` 零命中),L1 可绿,判据不设防。同型判例已裁定过:strategy-input-unification attack2.md B2-1(「同一符号/同一契约的迁移被拆进两阶段,中间态既破判据又破生产链」= 划分不当,iteration-design §3.1 阶段粒度)。
- 证据:cw_entry_plane_intel.py:119、cw_screen_prep.py:899/:901-904;grep sr-od-test `start_plane` = 0 命中;landing 依赖链 3.2→3.3→3.4。
- 建议:三选一——3.2 范围并入两调用点的一行适配(构造调用改 `(ctx)` 即可,prep 排干逻辑仍留 3.4);或 landing 首节显式声明阶段原子性总原则(整批分支合入、允许中间破态,照 strategy-input-unification landing 首节形态);或重排 3.2/3.3/3.4 依赖使契约迁移同批。
- 已消解:采纳为「原子切换」总原则——原 3.2/3.3/3.4 合并为单一原子阶段,首节显式声明;3.2 完成态闭合性经逐项核查(构造调用点/字段/通道/审计行/合同测试全入文件面),唯勘误面缺口见新发现 A12。

### A7 「比对语义零变化」把对账网原样迁入新单一写门,未问该机制在新架构下的可达性(迁的是死机制)

- 核:核三·治本
- 位置:design.md §2.3;landing.md §3.1 判据
- 问题:对账网现役唯一调用点在 `write_logic(plane_bosses)` **之后**(cw_entry_plane_intel.py:163 写、:187-188 取 `.value` 比对),而 write_logic 即时生效(test_cw_screen_report_ports.py:404-406 锚)→ 现役比对对象 = 刚写入的同一列表(自比较);已有真值不覆写门(:153-158)又保证有简报真值时提前 return 不进对账。即:简报真值唯一写点就是这个字段、写门前字段必空——该对账在**任何可达分支都不存在双源可比对**。§2.3 按「对账网……比对语义零变化」把它列为新写门迁并项、3.1 判据还配了单测项(「对账网 config 门控 off 时零行为」),等于把死机制在新单一源里落位并验收。本迭代主旨是退役无实效机制(None/计数/降级),唯独这一件没做同样的治本两问。
- 证据:cw_entry_plane_intel.py:153-158/:162-167/:175-188;cw_briefing_obs.py:212-245(比对本体);test_cw_screen_report_ports.py:404-406;design §2.3 对账网行。
- 建议:三选一并写进 §2.3——①承认不可达,随本迭代退役(§2.4 加一行,对账函数一并处置);②保留但注释明示「简报真值与实采同字段,此对账现为占位」(§1「明确不解决」记录);③真要双源对账,须给简报读数另立留存面(架构变化,应展开论证而非「零变化」迁入)。
- 已消解:并入 A2 处置(取①对账网退役),§2.3 划除 + §2.4 退役行 + 3.1 判据单测项删除,三点齐。

### A8 消费端 None 语义勘误枚举不全:至少三处同语义注释不在清单

- 核:核一·无前提(枚举完整性)
- 位置:design.md §2.4
- 问题:勘误枚举 = cw_comps.py:233/:1512、telemetry/schema.py:630(三点均核实存在、行号内容相符);但全 src「徽章态 None」语义注释至少还有三处不在列:cw_game_state.py:2198(plane_bosses **字段定义注释**「None=该位面无身份(ADR-0398)」——字段本体存续,注释与新语义直接矛盾,且该文件 3.4 本来就要动)、cw_vocab.py:235、cw_briefing_obs.py:182(reconcile docstring;若 A7 裁定保留占位则必改)。枚举式勘误漏点 = 修订后同一误读继续有据可查。
- 证据:grep src `徽章态` = 22 处,上列三处逐一读实。
- 建议:§2.4 勘误口径改为「grep『徽章态/该位面无身份』全量清点逐处改写」或直接补全枚举;3.4 判据挂勘误清零。
- 已消解(部分):全量清点口径 + 枚举补三处落地(§2.4/3.2⑥);判据与清扫的 grep 模式退化单模式、且清点面缺口漏 obs/cw_observation.py,转新发现 A12(中)。

### A9 五处完成判据的「§12 通用工程门(引用,不复述)」指针不可解析——同族缺陷第四犯

- 核:核二·规范遵循
- 位置:landing.md §3.1-§3.5 完成判据(五处)
- 问题:iteration-design.md 自身无 §12 节;项目 AGENTS.md §12 = 自维护指南,无工程门内容——该指针在全仓不可解析。此判例已三轮在案:chain-observation-landing attack.md F11、turnstate-retirement attack.md F-11、strategy-input-unification attack2.md B2-10(B2-10 已按跨件半问点过「三犯」);可解析形态两个先例:实指引用(changes/2026-09-15-prep-single-action-contract/landing.md:14)或首节自包含定义(changes/2026-09-16-chain-observation-landing/landing.md:3)。本 landing 五阶段原样照抄模板占位串,未采用任一可解形态。
- 证据:上列引用锚逐一可查。
- 建议:照先例二选一(推荐首节自包含定义,源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节),五阶段判据改引用行。
- 已消解:landing 首节自包含定义(ruff/L1/逐文件点名与入库面复核,源标注 AGENTS 对应节),现四阶段判据均为「通用工程门(见首节定义)」引用行,形态与可解析先例一致。

### A10 fixture 亲验相符;但用途边界与 game doc source_image 口径未随 §2.5 勘误方案闭合

- 核:核一·无前提
- 位置:design.md §2.5;landing.md 末阶段清单末行
- 问题:①fixture 存在(sr-od-test/screens/货币战争-位面详情/ 四帧俱全),关键帧位面详情-纹章风头像-run30.png 经**视觉亲验**:金色纹章图案同现于节点带最右 boss 节点(1-9)与详情条头像区,详情条仅「首领节点」标签 + 通用描述,无任何名字文字——设计的实拍描述成立;「该图案即 boss 的纹章风头像」这一升步依据 = 用户判读 2026-09-20,设计已就地标注(单帧无法从像素区分「该 boss 专属纹章」与「跨 boss 通用徽章」,此步信任用户裁定,记录备查)。②用途口径:fixture 仅作设计证据与 game doc 勘误证据,测试阶段不用它(3.2 判据用桩 SIFT 未命中;sr-od-test 全仓 grep 屏名/帧名零引用)——成立,但设计未写明,易被误读为 harness 帧义务。③game doc 行 4 source_image 记「三帧(全屏态/点节点直开态/敌人信息浮层态)」,目录实有四帧;§2.5 勘误方案只覆盖「徽章态」节改写,不含 source_image 行同步 → 修订后文档自带帧清单失真。
- 证据:glob 四帧;read_image 亲验(本报告即证);grep sr-od-test `纹章风头像|货币战争-位面详情` = 0 命中;docs/game/screens/货币战争-位面详情.md:4。
- 建议:§2.5 补 source_image 行同步义务;design §2.2 或 landing 3.2 注明该 fixture 仅证据用途、不进测试面。
- 已消解:fixture 用途边界进 §2.2(不进测试面,桩 SIFT 构造);source_image 三帧→四帧同步进 §2.5 与正本清单末行。

### A11 §1 归层段未覆盖五症状中的两个(巨型节点 / 防御性计数)

- 核:核一·无前提(§2.1 归层完整性)
- 位置:design.md §1「根因归层」段
- 问题:归层只映射了徽章态(语义)/写门双份 + 编排无单一源(流程)/ctx 中转 + 写门错层(约定);症状 1(巨型节点)与症状 5(防御性计数与降级)无层归属。归层是治本审查的锚,两项悬空使「§2 修的是根」对这两条只能靠读者自行补层。
- 证据:design §1 症状清单(5 条)与归层段(3 层)对读。
- 建议:归层段补两项(巨型节点 → 流程层结构问题,不可逐屏验收;防御性计数 → 约定层,违反 op-layer.md §1.1 循环无上限裁定)。
- 已消解:归层重写为三段全覆盖五症状(巨型节点入流程层;防御计数入约定层并在语义层点明「失败需容忍」建模误设)。

### 未发现声明(逐核)

- **核一其余子项未发现**:§1 五症状 → §2 逐条有方案(巨型节点→§2.2、ctx 中转→§2.3/§2.4、写门双份→§2.3、徽章态→§2.2/§2.4/§2.5、防御计数→§2.4);§2.6 保留面与 §2.4 退役清单无冲突(简报写点保留与 report 跳写门兼容,entry 独立入口与编排单一源一致);三 op 责任切分四问可答(开屏=entry、关屏=entry、写容器=plane_intel node6 经 kernel report、判跳过=prep 判触发 + entry 判真值直通);landing 各阶段设计依据指向真实存在、完成判据可独立验证、正本更新清单五行「← 阶段」全部真实(fields.md §6.4/附录表、prep.md:21、plane_intel.md 全篇、op-layer §3、game doc 徽章态节均核实);关键码锚逐条打开核对(cw_screen_plane_intel.py:695-696、cw_screen_prep.py:876-885/:901-904、cw_entry_plane_intel.py:131-137/:144-173/:175-188、takeover 字段定义、消费端三注释、op-layer §1.1/§2.2 引用、plane_intel.md 现役机制行)——内容全部相符,仅一处行锚不精确:prep 侧「已有真值不覆写」实际住触发门(prep:869-870)而非 §1.3 所标 905-913,语义主张本身成立。§2.2「识别 node 重试 3 / 点开 node 2」「恒全采」等数值与分支均已定稿,无「看情况/待定」。
- **核二除 A9 外未发现**:三件结构齐(design §0-§2 / landing 六小节×七件逐一核对 / README 两事);无过程叙事(design/landing 正文无「本轮/已改/修订后」措辞,「用户裁定 2026-09-20」为裁定指针非过程叙事);设计正文 as-built 无状态;README 进度与 §0 状态(草案)同步;§2.4 注释勘误方案写新语义不写变更史,合 AGENTS §8。
- **核三除 A7 外未发现**:已归层症状的归层结论成立(徽章态 = 语义层错误建模,有实拍 + 用户判读;写门双份 = 流程层,两份拷贝实证;ctx 中转 = 约定层,type: ignore 实证),未找到反例;ctx 通道删除修根(交接语义归容器写门,非换地方);6 node 拆分治「不可逐屏验收」之根,豁免两 node 形态已申报进正本更新;「识别失败响亮失败 + 模板缺口批外立项」的战术权衡声明完整(§1 明确不解决 + §2.2 显式接受战术风险 + 批外立项有用户裁定指针,失败显影为预期行为);跨件半问:抽查 briefing.py / encounter.py / megastar.py / prep 链域(kernel prep.py:85-87 幂等门)四屏文件,写门语义均已在 kernel 屏文件内,「判定住 op 层」无第 3 处残留——本迭代是 flat-report 范式迁移(2026-09-18-screen-op-flat-report)的收尾件,不需升架构级设计件。

## 结论

**需修订后再审。** 设计主线(编排单一源 / 6 node 管线 / 写门归 kernel / None·计数·降级退役)方向正确、治本性总体成立,fixture 实拍证据经视觉亲验相符;但 A1(四个存续附属机制无处置声明,其中两个被新前提连根拔)与 A2/A7(对账网:分包矩阵冲突 + 死机制迁入)属必须补的设计缺口,A3 引用已退役机制、A4/A6 会让 3.1/3.4 判据在交付时不可达成或生产链中间态破。按 iteration-design §6,以上修复收敛 + 本报告发现逐条消解前,不应立落地阶段任务。

## 复攻(第二轮)

> 复攻对象 = 修订后 design.md / landing.md / README.md(对抗审中态)。判据源同首轮全部直调复核;对处置声明逐条对码(附属机制四行、对账网退役消费面 grep、sig 三形状、原子阶段完成态闭合性、守卫退役依据、fixture 口径),并做定稿试读与全量同步复查。

### 消解确认清单

- **完全消解 8 条**:A2(对账网退役,消费面/config 处置经 grep 核实可执行)、A3(sig 定死 + 措辞全删 + 正本清单补 §2.1)、A4(bump + 断言 + audit 行 + 文件面全落)、A6(原子切换总原则,3.2 完成态闭合性逐项核查通过)、A7(并入对账网退役)、A9(首节自包含定义 + 引用行)、A10(fixture 边界 + source_image 同步)、A11(归层全覆盖)。
- **部分消解 3 条**(处置主体落地,各衍生新发现):A1 → 处置表成立且②④挂点可实现,残留③挂点矛盾(A14)与①依据错置(A15);A5 → 三问三答落地,残留守卫退役依据失真(A13);A8 → 全量清点口径落地,残留判据面缺口(A12)。
- 定稿试读(实现者凭 design + 阶段行开工):3.2 原子阶段七件范围语义完备度大幅提升,除 A12/A13/A14/A16 四处外均可直接开工;全量同步复查:design↔landing↔README 状态同步(对抗审中)、阶段数(0/3)、判据引用、设计依据指向、正本清单五行目标真实——除 A18 外未发现新失同步。

### 新发现

### A12 3.2 勘误清零判据与文件面矛盾:cw_observation.py 三处「徽章态」注释不在文件面;判据/清扫 grep 模式退化为单模式

- 核:核一·无前提(判据可达成性 / 全量同步复查)
- 位置:landing.md §3.2 文件面与判据、§3.3;design.md §2.4
- 问题:§2.4 全量清点口径要求 grep『徽章态/该位面无身份』全 src 逐处改写,obs/cw_observation.py:795/:798/:799 三处命中,但 3.2 文件面(12 项)不含该文件 → 3.2 判据「grep『徽章态』src 零命中」在本阶段文件面内不可达成(worker 越面或停手;3.3 文件面虽 grep 驱动,但依赖 3.2 先完成,卡在 3.2)。另:§2.4/3.2⑥ 用双模式,3.2 判据与 3.3 清扫退化为单模式『徽章态』——cw_game_state.py:2198 的实际措辞是「该位面无身份」(不含『徽章态』字样),单模式验不出此类残余。
- 证据:cw_observation.py:795-799 逐一读实;landing 3.2 文件面枚举与判据第 4 行;3.3 范围。
- 建议:3.2 文件面补 obs/cw_observation.py;3.2 判据与 3.3 模式补『该位面无身份』(或声明以 §2.4 枚举清点为验收口径)。
- 已消解:3.2 文件面补 obs/cw_observation.py;判据与 3.3 清扫均改双模式『徽章态』+『该位面无身份』;design §2.4 已知清单补 cw_observation.py:795-799 并注明 2198 实际措辞「该位面无身份」。

### A13 可读守卫退役依据失真:「半开帧不委派」防线被错述为 start_plane 专属,「免费等待 → 失败链消耗」档位变化未申报

- 核:核一·无前提(依据标注 / 实现者无需再设计)
- 位置:design.md §2.1「prep 侧语义定稿」
- 问题:退役理由「它只为推导 start_plane 存在」与代码自述不符——守卫现役语义 = 节点条不可读(过场/overlay 半开帧)→ 等下轮、不消耗预算(cw_screen_prep.py:871-875 注释原文),服务的是入口契约「必须是定型备战帧,半开备战帧点不开详情(两轮实跑 12 retry 全空证);过场帧首试失败后下个稳定帧再试」(cw_screen_plane_intel.py:26-28)。退役后半开帧委派 → entry 打开 node 重试耗尽 → op fail → prep round_fail → 外循环失败链:把零成本自愈换成失败预算消耗 + 开屏空转,该档位变化未申报。三问中另两答(触发谓词/委派透传)已定稿且经现役代码核可实现。
- 证据:cw_screen_prep.py:871-875;cw_screen_plane_intel.py:26-28;design §2.1 守卫退役句。
- 建议:二选一并如实标注——保留守卫(触发前置 = 节点条可读,免费自愈语义不变);或确认退役并显式申报「半开帧场景从等待改为失败链消耗」的代价与接受理由。
- 已消解:守卫保留——design §2.1 触发谓词条与 landing 3.2③ 均改写为保留语义,依据如实标注 prep:871-875,错误表述(「只为推导 start_plane」)已修正为「与 start_plane 无关——推导职责退役不变」的准确切分;免费重判与失败显影哲学的相容性已声明(瞬态帧过滤,非决策循环防御帽)。

### A14 难度参考值「保留」与挂点自相矛盾:挂「识别位面1 时同帧顺带」= 位面2/3 永不落账

- 核:核一·无前提(处置表可实现性)
- 位置:design.md §2.2 附属机制处置表③
- 问题:现役难度参考逐位面读(「随选中位面变,逐位面读」cw_screen_plane_intel.py:578-580 注释;difficulty_ref 按位面号逐位面写);处置表③裁「保留」但挂点定为「识别位面1 时同帧顺带」→ 位面2/3 的 difficulty_ref 在新管线中永不写入,静默行为缩减与「保留」自相矛盾(值仅参考、生产难度主源在备战旗牌,影响有限,但处置表自身失真)。
- 证据:cw_screen_plane_intel.py:578-595;design §2.2 处置表③。
- 建议:挂点改「每个识别 node 读出该位面后同帧顺带读,随 node6 落账」(等价保留);或明示缩减为仅位面1 并把「保留」改为「部分保留 + 理由」。
- 已消解:处置表③改「每个识别 node 同帧顺带读当位面值;node6 按现役 _collect_cycle 的落账口径逐位面落账」,并补注现役逐位面读前提;landing 判据改「③难度参考**逐位面**落账(三识别 node 各读、node6 落账)」——可验收(harness 断言 difficulty_ref 三位面齐)。

### A15 ①互证退役依据与机制实际职责不符

- 核:核一·无前提(依据标注)
- 位置:design.md §2.2 附属机制处置表①
- 问题:互证实际职责 = 备战/详情两读法的**全节点类型序列**对拍留证(观测自检,纯记账零决策;模块与函数 docstring 自述「观测自检框架设计 §1 行11」),不是 boss 位置防线。处置表称「其防护目标(位置先验错位)由标签验首领 + 失败响亮承接——错位帧过不了标签验」:该等价只对 boss 槽错位成立;非 boss 位的序列错型(奖励/战斗误读)不经过标签验,退役后此类感知冲突从「留证」变「无声」。退役决策本身可辩护(纯遥测、输入源已亡),依据应如实改写。
- 证据:cw_screen_plane_intel.py:155-181(两 docstring)、:635-676(纯记账零决策实现)。
- 建议:处置表①理由改为「感知冲突留证通道随备战输入源消亡而退役(纯遥测,无行为防线损失)」,勿错误等价替换。
- 已消解:表①理由如实改写——明示「全节点类型序列的感知冲突留证(纯记账,零决策),非 boss 位置防线;退役后非 boss 槽位的错型从『留证』变『无声』——显式接受的战术权衡;boss 槽错位仍由标签验+失败响亮承接」。

### A16 entry 真值跳过门在重写中失联

- 核:核一·无前提(实现者无需再设计)
- 位置:design.md §2.1 CwEntryPlaneIntel 行;landing.md §3.2②
- 问题:首轮 landing 判据曾明示「真值跳过零点击」,全量重写后 design §2.1 entry 行(门 → 打开 → 委派 → 关闭)与 landing 3.2② 均未提该门,退役清单未列、§2.6 保留清单也未列——实现者重建 entry 门时面临去留临场拍板。不保留的后果:MCP 手动调起(§2.6 明确保留的能力)在容器已有真值时会无谓开屏全采、再靠 report 不覆写门兜住,白开白关详情屏。
- 证据:现役实现 cw_entry_plane_intel.py:95-100;design §2.1/§2.4/§2.6 与 landing 3.2② 对读均无该门。
- 建议:§2.1 entry 行补「真值已在 → round_success 直通(零点击)」(建议保留现役语义),三处清单对齐。
- 已消解:design §2.1 entry 行门序补真值跳过(对局中/画面合法/真值跳过,顺序与现役「屏幕门先于跳过门」一致);landing 3.2② 补「真值跳过零点击直通(保留现役 entry 真值门语义)」;3.2 判据单列一条(容器已有真值 → 零点击直通),可验收。

### A17 §2.3 统一写门 sig 的依据标注与实定值不符;「迁并现散落三处」计数在对账网划除后悬空

- 核:核一·无前提(依据标注)
- 位置:design.md §2.3
- 问题:①sig 括注「沿用简报写点形状,写者身份换本 op」,但 screen 实定 '货币战争-位面详情' 而简报实值 = ''(briefing.py:52-53「照抄现役原值」);且 ChannelSig docstring 族-画面约定为「logic_action = None」(cw_game_state.py:372-373)——实定值可运行(无校验),但依据表述失真,实现者对照简报形状核验会对不上。②写门首行「迁并现散落三处」在对账网划除后只剩两处来源,计数悬空。
- 证据:briefing.py:51-55;cw_game_state.py:372-373;design §2.3 对读。
- 建议:括注改「沿用简报族 family/mode,screen 按关联画面记录(与简报先例同型的约定偏差,如实标注)」或改值对齐;「三处」改「两处」。
- 已消解:删「沿用简报写点形状」括注,定值依据改第一性表述(采集真值落账属 logic_action 族同简报族 / screen 标实际采集画面并明示与简报空 screen 的差异及理由 / actor = 写者本体;原 ResumeAttach 与 CwEntryPlaneIntel 两写端随迭代消亡);「迁并三处」改精确清单(词缀幂等门两份拷贝 + 不覆写门一份,带行锚)。

### A18 正本更新清单 game doc 行「← design.md §2.5」违反清单行格式

- 核:核二·规范遵循
- 位置:landing.md 正本更新清单末行
- 问题:iteration-design §3.2 规定清单行格式 = 「正本文档:节 ← 本迭代哪个阶段导致」;该行 ← 指向设计节而非阶段,其余四行均为阶段号。该勘误的行为成因 = 3.2(识别行为变更使命题翻覆),末阶段按 §2.5 执行是消费关系不是成因。
- 证据:landing 正本更新清单五行对读;iteration-design.md §3.2。
- 建议:改「← 3.2」(行内已括注 §2.5 出处,不冲突)。
- 已消解:正本清单 game doc 行改「← 3.2(勘误文本依据 = design.md §2.5)」,格式合规且文本出处保留。

### 复攻未发现声明

- 除 A12-A18 外:3.2 原子阶段完成态其余闭合项全部核实(构造调用点两处、ctx 通道三文件、takeover 字段+审计行+合同测试、start_plane 零测试引用、纯函数三件无外部 src 消费方——cw_observation.py:758/:798 的注释指针随勘误清点面覆盖,其中 :758 不含关键词的残留归 A12 修法一并处理);对账网退役的 config 消费面核实(行为消费唯一 = entry:184,字段面在文件面内);A1②④ 的 session/gs 分通道挂点可实现且先例真实;README 进度与 §0 状态同步;landing 首节通用工程门 L1 命令路径实存。

## 结论(复攻后更新)

**仍需修订(轻量),范围已大幅收敛。** 首轮 11 条:8 条完全消解、3 条主体消解;新发现 7 条(中 3:A12 文件面/模式缺口、A13 守卫依据失真+档位未申报、A14 难度参考挂点自相矛盾;低 4:A15/A16/A17/A18)。无新增结构性缺口——三条中档均为落点修正(补一个文件面 + 一个 grep 模式;守卫去留二选一;难度参考挂点一行改),低档四条为措辞/枚举/格式修正。修订落地后建议仅对 A12-A14 做点验,无需第三轮全量复攻。

## 点验(第三轮)

> 点验范围 = A12-A18 修订落点闭合性(按要求不做全量复攻)。判据源直调:修订后 design.md / landing.md 全文、cw_observation.py:748-802。

### A12-A18 消解确认(7/7)

- **A12 ✓**:3.2 文件面已含 obs/cw_observation.py;3.2 判据与 3.3 清扫均改双模式『徽章态』+『该位面无身份』;design §2.4 已知清单补 cw_observation.py:795-799 并注明 2198 实际措辞。
- **A13 ✓**:守卫保留(design §2.1 / landing 3.2③),错误依据已修正,语义表述准确——「半开帧不委派、等下轮免费重判;与 start_plane 无关,推导职责退役不变;瞬态帧过滤非决策循环防御帽」三句均与代码自述(prep:871-875)相符。
- **A14 ✓**:处置表③改「每个识别 node 同帧顺带读当位面值;node6 按现役落账口径逐位面落账」;landing 判据「③难度参考逐位面落账(三识别 node 各读、node6 落账)」——判据可验收(harness 可断言 difficulty_ref 三位面齐)。
- **A15 ✓**:表①理由如实改写(感知冲突留证定性 + 非 boss 槽错型「留证→无声」的显式战术权衡声明 + boss 槽仍由标签验承接)。
- **A16 ✓**:design §2.1 entry 门序补真值跳过(顺序与现役「屏幕门先于跳过门」一致)、landing 3.2② 补语义、判据单列可验收条。
- **A17 ✓**:第一性定值依据(logic_action 族 / screen 标实采画面并明示与简报空 screen 差异 / actor = 写者本体)替换失真括注;「三处」改精确清单(幂等门两份 + 不覆写门一份,带行锚)。
- **A18 ✓**:game doc 行改「← 3.2(勘误文本依据 = design.md §2.5)」,格式合规。

### 新发现

### A19 cw_observation.py:756-759 的「跳过过去位面 + 降级补采」行为描述不含清扫关键词,修订后仍会残留旧语义

- 核:核一·无前提(勘误清点口径的漏网单句;注释级,零行为影响)
- 位置:design.md §2.4 / landing.md §3.2⑥、§3.3
- 问题:`read_plane_detail_nodes` docstring 中「选中过去位面时节点全部变暗……消费方 CwScreenPlaneIntel 按 `decide_plane_skip` 跳过过去位面,仅台账缺值时降级补采一次」(cw_observation.py:756-759)——描述的正是本迭代退役的跳过/降级机制(恒全采 + 响亮失败取代);该段不含『徽章态』『该位面无身份』任一关键词,双模式 grep 与 3.3 清扫均不命中 → 3.2 勘误清零后此段旧行为描述照常存活,误导后来者以为跳过/降级仍是现役机制(渲染事实部分——过去位面变暗识别可能退化——仍然为真,应保留并改写行为指引)。
- 证据:cw_observation.py:756-759 逐句读实;3.3 清扫模式枚举(七项均不含 decide_plane_skip/降级补采)。
- 建议:随 3.2 的 cw_observation.py 改写顺手重写该段(渲染事实保留,行为指引改「接管管线恒全采径直读取,识别失败按失败语义响亮暴露」);或在 3.3 清扫模式补 `decide_plane_skip`。不阻塞定稿。

### 点验未发现声明

- 除 A19 外:A13 守卫保留与 §2.2 node1 门/失败语义无冲突(守卫 = prep 侧委派前置过滤,与识别 node 重试正交);A14 逐位面读与「词缀首位面同帧读」「单屏识别机制」互不干扰;A16 真值跳过门与 prep 触发谓词一致(双重判同一容器真值,幂等);A17 精确清单行锚(prep:911-913 / entry:168-173 / entry:153-158)与首轮核实值一致;3.2⑥「含 …」枚举为非穷尽表述 + 文件面 + 双模式判据三层兜底,cw_observation.py 的清零义务闭合;README 未动(对抗审中/0/3)与 design §0、landing 三阶段仍同步。

## 结论(点验后·最终)

**可定稿。** 首轮 11 条 + 二轮 7 条全部消解(A12-A18 处置经本轮逐点验证实落点闭合);唯一新增 A19 为注释级残留单句,零判据影响、零行为影响,建议随 3.2 的 cw_observation.py 改写顺手处理或 3.3 补一个清扫模式,不构成定稿阻塞。按 iteration-design §6,攻击已收敛、试读已过(第一/二轮完成,本轮落点闭合)——本迭代设计可定稿,可照 landing.md 立阶段任务。

## 定稿前点验(独立点验员)

> 点验范围 = A12-A18 修订落位逐条核验 + 修订未引入新问题的额外检查(轻量,不做全量重审)。判据源直调:修订后 design.md / landing.md / README.md 全文、残留措辞与模式 grep、代码锚抽查(cw_screen_prep.py:866-881、cw_observation.py:748-802、cw_game_state.py:2198)。零转述。
> 说明:本轮点验执行期间,attack.md 已并行出现上文「点验(第三轮)」节(含 A19);本节为独立点验员的独立核验记录,结论互为印证。

### 七条修订落位逐条核验(7/7)

- **A12 ✓**:landing 3.2 文件面含 obs/cw_observation.py;3.2 判据与 3.3 清扫范围均为双模式『徽章态』+『该位面无身份』;design §2.4 已知清单含 cw_observation.py:795-799 并注明 cw_game_state.py:2198 措辞为「该位面无身份」。代码核:cw_observation.py:795/:798/:799 确含『徽章态』;cw_game_state.py:2198 确为「None=该位面无身份(ADR-0398)」(不含『徽章态』——单模式验不出,双模式修订必要性属实)。
- **A13 ✓**:design §2.1 触发谓词条守卫保留(「现役语义 = 半开帧不委派、等下轮免费重判,cw_screen_prep.py:871-875;与 start_plane 无关——start_plane 推导职责退役不变」);landing 3.2③ 同口径(「节点条可读守卫保留——半开帧等下轮免费重判」)。grep 全目录:「节点条可读守卫退役」「守卫只为 start_plane」在 design/landing 正文零残留(attack.md 命中均为审查历史引述)。代码核:prep:874-875 注释「节点条不可读(过场/overlay 半开帧)→ 等下轮,不消耗预算」与修订表述相符。
- **A14 ✓**:design §2.2 表③ = 「每个识别 node 同帧顺带读当位面值;node6 按现役 _collect_cycle 的落账口径逐位面落账(session 通道,同②先例)」;landing 3.2 判据 = 「③难度参考逐位面落账(三识别 node 各读、node6 落账)」。
- **A15 ✓**:design §2.2 表① 理由如实——「全节点类型序列的感知冲突留证(纯记账,零决策),非 boss 位置防线」+「非 boss 槽位的错型从『留证』变『无声』——显式接受的战术权衡」+「boss 槽错位仍由『标签验首领 + 失败响亮』承接」,三要素齐备。
- **A16 ✓**:design §2.1 CwEntryPlaneIntel 行门序含「真值跳过——容器已有位面真值 → 零点击直通成功,防手动调起白开白关详情屏」;landing 3.2② 同语义(「保留现役 entry 真值门语义」);3.2 判据单列一条「entry 真值跳过门:容器已有真值 → 零点击直通」,可验收。
- **A17 ✓**:design §2.3 sig 段无「沿用简报写点形状」措辞(grep 全目录仅 attack.md 历史记录命中),定值依据为第一性表述(采集真值落账属 logic_action 族 / screen 标实际采集画面、非简报空 screen / actor = 写者本体);「迁并」处为精确清单——词缀幂等门两份拷贝(prep:911-913、entry:168-173)+ 已有真值不覆写门一份(entry:153-158),无悬空计数。
- **A18 ✓**:正本更新清单 game doc 行结尾「← 3.2(勘误文本依据 = design.md §2.5)」,← 后为阶段号,括注出处合规。

### 额外检查(修订未引入新问题)

- **守卫保留无残留**:design/landing 仅存保留表述与「start_plane 推导职责退役不变」的准确切分句,无旧错误表述残留。
- **难度参考逐位面与 node6 不冲突**:表③落账为 session 通道,与 §2.2「②③④均为 session 通道操作,与上报写门(gs 通道)同居 node6 簇但分通道」自洽;§2.6 保留清单同步(「敌人难度参考值」在列)。
- **修订间互洽**:A16 真值跳过门(entry 侧)与 prep 触发谓词 `not gs.plane_bosses.value` 判同一容器真值,双重判幂等不矛盾;A17 精确清单与 §2.3 对账网退役段(纯函数/挂点/config 处置)一致;A12 双模式判据与 3.2⑥ 非穷尽枚举 + 文件面三层兜底闭合。
- **README 同步**:README「对抗审中」= design §0「状态:对抗审中」一致;landing 阶段 = 3.1/3.2/3.3 + 末阶段(3 个落地阶段 + 末阶段),README「阶段 0/3 done」一致。观察项(非矛盾、非阻塞):README「设计对抗:进行中」行括注「首轮 11 条已修订进设计」滞后于 attack.md 实况(复攻 A12-A18 七条亦已修订落位),定稿时顺手更新括注即可。
- **并行点验 A19 复核**:本轮执行期间 attack.md 已出现「点验(第三轮)」节,其 A19(cw_observation.py:756-759「decide_plane_skip 跳过过去位面/降级补采」旧行为描述不含双模式关键词、勘误清零后残留)经独立读码属实——该段确在 :756-759、确不含『徽章态』『该位面无身份』任一关键词;注释级、零行为影响,处置建议(随 3.2 cw_observation.py 改写顺手重写,或 3.3 清扫补 `decide_plane_skip` 模式)合理,不构成定稿阻塞。本轮独立核验无 A19 之外的新发现。

### 结论

**可定稿。** A12-A18 七条修订全部落位且与代码事实相符;修订之间及与文档其余部分无矛盾;唯一残留 A19 为注释级单句(已由并行点验轮记录、经本轮独立复核属实),随落地顺手处理即可,不阻塞定稿。
