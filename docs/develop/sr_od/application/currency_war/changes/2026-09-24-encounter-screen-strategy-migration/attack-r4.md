# 遭遇迁移设计 对抗审查报告(第四轮)

> 审查对象:design.md / landing.md / README.md(三件全读)。判据源直调:00/01 号稿(含 §6 三形态章程与【拍】禁域条款原文)、04 号稿 §7 裁定表第 9 行、op-layer.md §1.4、p64 单篇辖域原文、math_proofs 索引 P15/P26/P85 行、iteration-design.md、strategy-work.md §1/§6、项目 AGENTS.md。代码面逐符号直调(cw_encounter_selection / cw_events / cw_survey19_hooks / cw_economy / cw_difficulty_account / flow / bridge / encounter.py / provisional / supply / cw_strategy / cw_screen_encounter / cw_pick_encounter_action / cw_node_obs / cw_equipment_data / cw_node_schedule / cw_sim_backend / cw_game_state / cw_action_report/pick_encounter / cw_loop / 测试仓两文件),全仓 grep 验证消费面声明。

## 发现清单

### R4-F1 [严重度:高] 钻石名单真值迁 `data/cw_equipment_data` 撞上「生成文件勿手改」契约,落地文件面缺生成器
- 位置:design.md §2.4;landing.md 3.2 文件面
- 发现:`data/cw_equipment_data.py:3-4` 模块头明文「**生成**:本文件由 `tools/cw/gen_equip_registry.py` 生成(**勿手改**;重跑 `uv run python tools/cw/gen_equip_registry.py`)」;生成器 `tools/cw/gen_equip_registry.py:355` 以 `out_path.write_text(module)` **整文件覆写**,模板内嵌于生成器(:359-360「勿手改生成产物——改 docs 后重跑生成器」)。design §2.4 与 landing 3.2 均只列 `data/cw_equipment_data.py`(接收钻石名单真值)为改动面,**未列生成器**——实现者按 landing 照做只能手改生成文件,下次任何人按文件头指令重跑生成器(装备 docs 更新是常规操作),`DIAMOND_EQUIP_NAMES` 即被静默抹掉,`obs/cw_node_obs` 与 `encounter_pick.py` 的 import 直接 ImportError,CW 全链炸。
- 修正方向:三选一并把所选写入 design §2.4 + landing 3.2 文件面:①把 `DIAMOND_EQUIP_NAMES` 加进生成器模板(`tools/cw/gen_equip_registry.py` 进文件面 + 重跑步骤);②真值放独立手维护 data 模块(照 `cw_equipment.py` SIFT 手维护先例);③由注册表派生(三件全在册:`cw_equipment_data.py:53` 财富宝钻 / :64 红钻 / :65 蓝钻)。

### R4-F2 [严重度:中] 立场结构(白名单/cap/偏好序)四种形态全不落,绕开「无标注数字不得进决策门」且章程缝隙未申报
- 位置:design.md §2.2(形态申报段、足量态 cap 精确口径段)、§2.4;README.md 待裁定点 2
- 发现:01_math_framework.md §6 硬规则:「框架内每个进决策门的数字必须标注三形态之一(含扩展形态【拍】)」「**无标注数字不得进决策门**」;【拍】分界条款:「凡『数值大小参与方向/闸门判断』的量归【推】/【拟】纪律,【拍】只承载…加法立场值」。本批进闸门的数字:边缘态可及白名单 {其一,其二}(= cap 2)、四档偏好序 0..3。design.md:86 申报「01 §6【拍】字面辖域(加法立场值)不覆盖闸门数字,本白名单**不走【拍】登记**」,合法性链 = 「原判据正本已落码结构 + 对抗审查确认 + 用户追认候记」——前三条链都不是章程承认的形态;且「原判据正本已落码」的授权来历被设计自己证伪(§2.2 明说裁定 9「判据正本 = 本模块」是载体登记,**不构成判据结构的授权**)。结果:这些数字在章程体系内无任何形态标注地进了决策门,与公理 1/公理 5 直接相抵,设计未把这一冲突申报为章程缺口。
- 修正方向:二选一并写入 §2.2/§2.9:①按【拍】登记入策略层立场分表(登记即立场;白名单非战力建模,不触【拍】禁域条款,登记理由栏写明「离散保守序结构、非经验拟合」以对齐分界条款意图);②显式申报 01 §6 存在「离散立场结构」分类缺口,把章程修订立项为本批或独立件,31 号稿裁定节登记缺口本身。现状的「对抗审查确认 + 追认候记」只是过程合法性,补不了形态合法性。

### R4-F3 [严重度:中] 决策序把「窗口不足」与 κ_S「不足」同名混流,`window-insufficient` 因词在决策序清单内不可推导
- 位置:design.md §2.2 决策序步骤 1/3 与归因串段
- 发现:决策序步骤 1「`ring.last_normal_battles(2)`。<2 行 → **不足态**」;步骤 3「`不足` → 可及集空 → 刷新阀(§2.5)」。按字面执行,窗口 <2 帧会流入步骤 2/3 的 κ_S『不足』支,产出 `refresh-valve:kappa-不足`;而归因串段(:96)声明 `window-insufficient`(窗口 <2 行)是**独立因词**且「数据不足与能力不足分因,判读可分」——该分流在决策序编号清单内推不出来,只有现役核(`cw_encounter_selection.py:390-397`:窗口不足先于 κ_S 计算、独立因词)才有完整语义。归因串被声明为「判读侧契约」,且 landing 3.1 完成判据要求单帧锁覆盖「因词封闭枚举」——两种读法会各自落一把互相矛盾的锁。
- 修正方向:决策序步骤 1 改写为独立分流,如「<2 行 → 刷新阀(因词 `window-insufficient`;不可刷 → 最低档,fail 向),不计算 κ_S」,与现役核门序逐位对齐。

### R4-F4 [严重度:中] landing 零残留集含 `_CALIBRATABLE`,与注入面随迁自相矛盾(完成判据按字面不可执行)
- 位置:landing.md 3.2 完成判据;design.md §2.3
- 发现:landing 3.2 要求「全仓 grep 零残留集 = …`_CALIBRATABLE`…」;但 design §2.3 申报「注入面随迁:apply_calibration(合法键缩为两保留键…)迁移 `encounter_pick.py`」——随迁的 `apply_calibration` 必然携带合法键集常量(沿用 `_CALIBRATABLE` 原名则全仓 grep 在新文件命中,零残留判据自炸;改名则改名动作无任何文档申报,实现者自行拍板 = 撞停手令场景)。kernel 旧址零残留与全仓零残留是两个不同判据,landing 写成了后者。
- 修正方向:零残留集限定为「`kernel/cw_encounter_selection.py` 内零残留」,或在 design §2.3 明确迁移后键集常量的新名/内联形态。

### R4-F5 [严重度:低] 注释收口清单声称「已知点全列」,cw_node_obs.py 同类过期指针至少还有两处未列
- 位置:design.md §2.7 注释指针收口清单
- 发现:清单只列 `obs/cw_node_obs.py` 遭遇读取段「decide_encounter 按难度选」句(实址 :26)。同文件还有:模块 docstring :2「(喂 `cw_events.decide_*` / 策略 `decide_encounter` 等钩子)」(迁移后 decide_encounter 不在 cw_events 也不叫此名)、`read_encounter_options` docstring :40「decide_encounter 用 difficulty + comp 成型度选(formed→高难度拿好奖励,未成型→低难度保生存)」(旧知识核叙述,与本批退役声明直接矛盾)。「已知点全列」按字面为假;有「末阶段全仓复扫兜底」承接,故低。
- 修正方向:清单补列这两处(或把该文件的收口面改为「全文件 decide_encounter/旧核语义指针对账」)。

### R4-F6 [严重度:低] README 报告链接缺 attack-r3;「待用户裁定点」为模板外增节且含会过期的第二抄本表述
- 位置:README.md 进度节、待裁定点节
- 发现:迭代目录实存 `attack.md` / `attack-r2.md` / `attack-r3.md`(glob 直调),README 报告链接只列前两个——README 是进度唯一载体,同步漏项(本报告落盘后 r4 同需补链)。另:iteration-design.md §4 规定 README「只做两件事——串文档、记进度」,附录模板无「待用户裁定点」节;该节第 2 条「确认载体 = 对抗审查**三轮收敛**」是对 design §2.2 的转述抄本,「三轮」数在第四轮进行中的此刻已经失真(补给批先例 README 把全部轮次链接进文档节,未见裁决内容抄本)。
- 修正方向:补齐 r3/r4 链接;待裁定点节压缩为纯指针(「裁定点 1/2 → design §2.10/§2.2」),删掉「三轮收敛」类会随轮次漂移的计数表述。

### R4-F7 [严重度:低] 「25 号稿画面族清单辖 8 屏」计数与实文不符;§2 动作清单表行含退役屏「装备」残留
- 位置:design.md §1 症状 5、§2.9
- 发现:`25_event_overlays.md:3` 头注画面族清单实列 **9** 项(遭遇节点/盛会之星/选择伙伴/命运卜者/银狼升星/祈愿试炼/星徽秘典/专家邀请函/武装箱弹窗);§2 动作清单表行(:19)也是 9 项且含「装备」——该屏(选择装备)已随 2026-09-22 误判退役删除(头注自注)。design「辖 8 屏」仅在「排除武装箱弹窗」的特定读法下成立,数值口径直调不符(设计自身要求口径直调);§2.9 改 §2 表行时应顺带清「装备」残留,设计未提。
- 修正方向:§1 症状 5 改为按实文口径(「头注 9 项/§2 表行 9 项含退役『装备』残留」),§2.9 该文件的动作面补「表行『装备』残留清除」。

### R4-F8 [严重度:低] 保留面符号 `EncounterOption` docstring 携带三档旧知识,未列入收口
- 位置:design.md §2.1(kernel 保留面)、§2.7(收口清单)
- 发现:`kernel/cw_events.py:55` `EncounterOption.difficulty` 注释「难度档 1=易/2=中/3=难(越高奖励越好但敌人越凶)」与读端真值矛盾(`cw_node_obs.py:29-30`:`_CN_NUM` 一~六 → 1..6,标题正则容纳其五/其六)。该契约符号本批明确留 kernel(§2.1),收口清单未含其 docstring——迁移后新核按 1..6 判、契约注释说 1..3,留给脱离本对话的读者一个必错的知识。
- 修正方向:§2.7 收口清单补 `EncounterOption.difficulty` docstring 改写(六档口径 + 指向 `_TITLE_RE` 派生)。

### R4-F9 [严重度:低] 「建议刷 ∧ 锚读缺」收敛保障的落地检查项,答案现在就能给出(外循环防线 = fail 专用)
- 位置:design.md §2.5(收敛申报);landing.md 3.2 落地阶段检查项
- 发现:design 把「外循环同画面重派防护是否存在」留作落地阶段核实。直调现在可定谳:`operations/cw_loop.py:521-529` `OP_FAIL_REDISPATCH_LIMIT = 5` 只计**连续 fail**;:796「任一 op 的 ok → 连续 fail 计数窗归零」。零点击 `round_success` 终结交回是成功出口——不计数、且把 fail 窗归零。即「锚持续读缺 ∧ 可及集持续空」的成功活锁在现架构下**确无收敛保障**,唯一止振 = 循环无上限规范的「挂起可观测」(op-layer.md §1.1)。检查项照做只会重复得出此结论。
- 修正方向:把该直调结论直接写进 design §2.5 / landing 检查项(预期结论 = 无防护,触发即按申报回流程层修锚读缺),避免落地批重查一遍;31 号稿数学挂账/申报节同步登记。

### R4-F10 [严重度:低] fail 向最低档帧的 reason 格式未封闭,`dark-install` 段退役后无现役格式可循
- 位置:design.md §2.2 决策序步骤 7 与归因串段、§2.3
- 发现:步骤 7 只说「reason 带窗口/κ 诊断」;归因串段声明保留 `e3-simple|` 前缀与 `pick:…`/`refresh-valve:<因>` 段格式,并申报「`dark-install` 段不再产出」——但现役 fail 向 reason 正是 dark 形态(`cw_encounter_selection.py:367-373`:`e3-simple|dark-install:<why>|d_enc=…|live=…`)。退役后 fail 帧的段格式(是否 `fail:<why>|kappa=<态>`?)无定义,而归因串被定位为判读连续性契约。验收锚点 3 只查「无次数最低档」行为不查因词,故低。
- 修正方向:归因串段补一行 fail 向段格式定义(如 `e3-simple|fail:<why>|kappa=<态>`),把「窗口/κ 诊断」落到具体段名。

### R4-F11 [严重度:低] 「【拟·档位↑⇒奖励价值↑】E-3 采样验证挂账保留」无登记载体(不在册【拟】)
- 位置:design.md §2.2 决策序步骤 6
- 发现:设计称主序依据保留「原核【拟·档位↑⇒奖励价值↑】的 E-3 采样验证挂账」(标签现址 `cw_encounter_selection.py:356-357`)。但该【拟】不在 01_math_framework.md §6 在册【拟】清单(13 项逐一对照,无此条),也不在 `audit/provisional.py::_SLOTS` 注册表——按章程三要素,无登记 = 无 owner/期限 = 「超过一个对局周期未决即回炉」的硬时限无处起算;`reward_tier` docstring 的「E-3 全量采样顺带验证装备段序」(:261)同病。31 号稿数学挂账节枚举(比值腿/E-3 标定/EV 挂 P26/窗口变体)也未显式收这两条验证义务。
- 修正方向:主序合法性改以「难度=奖励量」知识判据(13 号稿 E3 行 + competitors 节点表,设计已引)单腿承载并去掉【拟】标签,或把该验证义务正式登记(provisional 槽 / 01 §6 清单 / 31 号稿挂账三处取一为单一源),装备段序验证同批登记。

## 零发现面申报

以下攻击面经直调核实**无发现**:

- **裁定与授权链**:裁定 9 行原文(04 号稿 §7 表 :111)与 design §0/§2.2 转述逐点一致(授权辖域 = 敌方通道 killed/进度填充率 + 持久化;「判据正本」指针失配已列 §2.9 修);刷新剩余语义指针与 op-layer.md §1.4 一致(None = 节点屏拒刷;闸内嵌 fail-closed 同口径);宪法五/六指针与 00_framework §1 第 5/6 条原文一致(均用户裁定 2026-09-23)。
- **判据源**:P64 辖域原文(静态 `dict[敌方难度读数→stat]`、条件表不在辖域)与 design 的引用及「DELTA_T 判死系引申申报,非 P64 原文结论」的诚实分层一致(自由项 B/q/s/m 论证对净值表同构覆盖,复核成立);math_proofs 索引 P15 行(boss 26.79 [24.25,29.23] / 普战 10.45)、P26 行(待证明,Δp_prep + L_node 双挂账)、P85 行(A/B 分键与选档输出零耦合)与 design 引用一致;strategy-work §1 零调参两类来源 / §6 对抗循环与 prereg 完整性门(§2.12 验收线保全申报 = 逐条盘点 + 零影响论证,格式合规)。
- **窗口论证的事实面**:`cw_node_schedule.py`(P2 = supply@r3 + encounter@r5 单遭遇、P1 encounter@r7、boss 均位面末节点、P1 42 局零反例/P2 7 局对照)与 §2.2/§2.12 锚点 6(P1 首遭遇帧窗口 = r4/r6)逐位核对一致;economy.md §10.2 P2 行双遭遇(1 帧、待多局复核)的两源冲突如实申报,「无行为面确证的语义变更不做」取舍成立;plane_schedule_observed.md / combat.md §3(伤害进度达标制)/ 敌人信息浮层.md(入口②已建档、难度分 OCR 全可读)均实存且与引用一致。
- **判据结构逐位对照**:κ_S 三态表(含一败一删失→不足、败局 fill 分支双定谳前不激活)、cap 2/6、经验档层(killed=True 无条件有效)、tiebreak 四档序与 `'/'.join(rewards)`、刷新阀三因词、fail 向最低档——与现役暗装核逐位同构,唯一差异 = 暗装门收窄,与申报一致。
- **消费面/删除面声明**:`encounter_tier_score` 唯一消费 = cw_events `_score`(:129/:145,src+测试仓 grep 定谳);`apply_calibration`/`reset_calibration` 全仓零外部引用;`EVENT_PICK_TYPES`/`EventPick` 零外部消费;EV 核(`decide_encounter_ev`)src+测试仓双零消费、「测试仓 EV 核纯函数锁」确认不存在(现 docstring :1 的「锁承载」表述与现实不符,两裁定点分支下均被覆盖);P9_VALIDATION:10 确证 cw_survey19_hooks「P1/P9/P8」旧编号与 math_proofs 无关;`cw_economy.py:414` 败补 6 消费点句、`cw_difficulty_account.py:59` 消费批句、provisional 头部注入指针句(:22-23)、supply.py 单一源句(:11-12)、cw_vocab 两处「替代 EncounterPick」(:715/:906)、flow.py:656/793/807 现役消费、`test_cw_unified_action_4.py` :28/:259/:278、`test_cw_obs_arch_event_screens.py:417` 保留面 import 与重调零点击锁(:387-404)——全部直调属实。
- **依赖方向与接线面**:全 strategies/ 零 obs import、kernel 零 strategies import(grep 定谳);`cw_strategy.py:254` 依赖矩阵句、bridge 模块头矩阵句实存;`report_action_pick_encounter_param` `param: Any` 鸭子取 idx(:47-58);动作 op 静态入参词表类型(:54);`_require_slot_options` 离屏抛错(:414-422);bridge 删覆写后回落基类入口与 `decide_supply`/`decide_invest_*` 同构属实;op 层重调一次 + 零点击终结现态与 §2.5/锚点 7 一致。
- **sim 面**:sim 全目录零 `record_settlement_row`;`ENCOUNTER_TIER_COUNT=4`、占位奖励文本「金+20(占位…)」不含「金币」字面 → tiebreak 全落末档;sim 无 `encounter_refresh_left` 写端 → 闸内嵌下 sim 恒最低档,与改前逐位一致,§2.12 盲区申报成立。
- **规范遵循面**:landing 三阶段七件套齐全、正本更新清单格式合规、单文档方案(§2 = 详设深度)合法;design/landing 正文无过程叙事;31 号稿编号空闲(分篇表现存至 30);承接指针(env 批/supply 批 §1「明确不解决」)逐字核实。
- **治本核验**:§1 归层(分层语义 = 判据本体驻 kernel + 三核并存;表示 = 暗装门粒度)成立;§2 修根(所有权迁移 + 真值归位不搬家 + 三核收敛 + 暗装门收窄激活已授权可判子集),症状面(敌浮层读数通道、EV 复活、affixes 死字段)全部显式划出并各有承接;逐画面迁移 = 宪法六既定节奏,非逐件补丁。
