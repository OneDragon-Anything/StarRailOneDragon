# attack7 —— 策略器决策输入统一 迭代设计 对抗审查(r7)

> 审查对象:`design.md` / `landing.md` / `README.md`(本目录)。
> 判据源均直调复核:iteration-design.md(四硬规则/§7 三核/阶段七件/正本清单)、strategy-docs 00/01、game_state/fields.md(§2.1/§2.2/§2.3/§3.3/§3.4/§3.7.1/§8.8/§9.4)、flow/README.md(§2 全节)、flow/session.md(§5.1 B4)、正本树全族(flow/game_state/screens/strategy-docs/architecture/sim)、代码真值(`src/sr_od/application/currency_war/` 符号锚逐一读码体)、sr-od-test、在飞三迭代(execstate/turnstate/unified-obs 的 README/design/landing + commit 锚 git 直查)、AGENTS.md、strategy-work.md §4/§6。
> 引用一律码点/文件:节直调,无转述。

## 发现清单

### [B1] blocker | design.md §1.1 / §2.1-4 / §2.7;landing.md 3.4 | encounter `refresh_used` 退役的「逐字节保真」在重入路径不成立:写 False 点选错宿主,现状语义被刻画错

**发现内容**:design §1.1 把 encounter 旗标现状刻画为「调用方**首调**不传(缺省 False)、仅**本访问**刷新后的重决策传 True」,§2.1-4 据此把 per-visit 位的写 False 点定死在 `CwScreenEncounter.__init__`。**码点证伪现状刻画**:False 缺省的适用单位是「每次 `handle`/lifecycle 调用」,不是「每次 op 实例」——`handle` 节点 `node_max_retry_times=10`(cw_screen_encounter.py:248),重入裁决「锚仍在 = 确认未落地 → 清标志重走」分支(:254-271)落空后**同一 op 实例内再次完整走决策路径**,其首调 decide 同样不传 refresh_used(:304/:439,即 False)。由此可达分歧序列:首调(False)→ 建议刷新 → 发射(累计计数 +1;新方案同址写 per-visit 位 True)→ 重读失败未重决策 / 或重决策后确认未落地 → **重入重走再次 decide**:现状收 False,新方案收 True。

**分歧的量级(直调两核)**:生产核 `cw_encounter_selection.decide_encounter` 的刷新逃生阀三处两枝(kernel/cw_encounter_selection.py:387-390、:397-400、:428-432)——`refresh_used=False` 返回 `EncounterPick(idx=最低档, refresh=True, reason='…refresh-valve…')`,`True` 落 `_dark('…-refresh-used')`(refresh=False,reason 换暗装串):**idx 同档,refresh 旗标与 reason 必分歧**,且现状重入还会多打一行「建议刷新但本局已用」日志。契约抽象默认核 `cw_events.decide_encounter`(:670-672 刷新枝 `idx=options[0].idx` vs :699-703 评分枝)**连 idx 都可分叉**(非生产路径,但属契约面)。design §2.7 自己把这类分歧定为禁类:「会产生 refresh 旗标/reason/选择 idx 的可读分歧,行为变化,禁」——per-visit 位在重入路径恰好复现它自己禁掉的分歧类,「逐字节保真只有 per-visit 位一条路」的等价性主张被自证推翻。

**验证不可捕获**:§2.6-1 的 encounter 对照矩阵只有「两态对照(False/True → 与改前首调/重决策同返回)」、§2.6-2 三分支为「首调 / 累计闸命中 / 刷新重决策」——全部以「本 handle 调用内」为前提,重入重走路径的第三次 decide 不在任何对照格内。

**修正方向**:①写 False 点从 `CwScreenEncounter.__init__` 改为「每次 handle / run_lifecycle 决策首调前复位」(或等价的重入裁决重走分支复位)——现状语义本就是 per-调用,这样首调 False / 发射后重决策 True / 重入重走首调再 False 逐位还原;②同批扩 §2.6-1/-2 对照矩阵补「重入重走后再决策」格;③§1.1 现状刻画句同步改准(「首调」的主体 = 每次 handle 调用)。supply 侧不受影响(旗标 = 容器累计派生,逐次调用同值,已核逐字节等价)。

### [M1] major | design.md §2.8 | 「实机候窗不阻任何阶段开工」与本阶段依赖表矛盾:3.2/3.3 被 unified-obs 实机验证期传递阻塞

**发现内容**:§2.8 卷首断言「『实机候窗』类验证期不属落码面,不阻任何阶段开工」。但同表 3.2/3.3 的前置 = 「unified-obs-reconcile 3.4 落码收」,而 unified-obs 落地件直调:其 3.4「依赖:3.3(先武装后拆旧)」(unified-obs landing.md:49),其 3.3 完成判据含「实机验证期:武装后实机连跑 ≥3 局(需用户游戏窗口)」(:40),当前状态 = 「3.3 落码 done,实机验证期候用户窗口」(其 README)。即 unified-obs 3.4 的「落码收」本身被一个候用户窗口的验证期**传递阻塞**,本批 3.2/3.3 的开工随链被阻——卷首断言对本批自己的两个阶段为假,照它排工即违反同节依赖表。

**修正方向**:措辞二选一——①改为「实机候窗不阻零交集阶段(3.1/3.4)开工;3.2/3.3 经 unified-obs 3.4→3.3 链被传递阻塞,开工时点随其验证期收敛」;②与 unified-obs 协商把其 3.4 的依赖改判(如 3.3 的实机验证期与其 3.4 落码解耦),再保留现措辞。

### [M2] major | landing.md 末阶段·范围(否定式界定) | 普查范围未定义 `docs/game/` 归属,已有 2 处实证命中将随本批过期

**发现内容**:普查范围句 = 「仓库全部正本与代码(含应用根 README 正本区所列各篇),排除 `changes/` 与 `proofs/`」。应用根 README 的「文档区(正本)」只列设计文档区,`docs/game/` 不在其列——按「不在列举即不在范围」的读法,game 文档被静默排除,但排除项里没有它(对比:proofs/ 的排除带「已实测零命中」背书,changes/ 的排除有规范铁律)。**实测命中且将过期**:`docs/game/screens/currency_war_supply.md:39`「supply 无刷新按钮(`decide_supply` 传 `refresh_used=True` 跳过刷新找钻)」、`docs/game/screens/货币战争-补给.md:39`「…decide_supply refresh_used=True(supply 无刷新按钮)」——形参退役后「传 refresh_used=True」即假命题,两行不在预登记清单、不被词表机制覆盖(范围外),收尾将产出带假句的「零待更新」。

**修正方向**:范围句显式二选一——①把 `docs/game/` 纳入普查面并在正本清单加行(顺带按 AGENTS「知识归位」判据处理:这两句描述的是本系统调用形状而非游戏知识,应改指设计文档区或随批改写);②显式排除 `docs/game/` 并申报理由与已知残留(现措辞下不可成立)。

### [m1] minor | landing.md 3.2/3.4 完成判据 | 阶段级锚普查范围「代码树」仍未定义 sr-od-test 归属(attack6 同点只修了末阶段一处)

**发现内容**:3.2/3.4 的 grep 对账表范围写「代码树 + 正本树,排除 `changes/`」,末阶段却已明确「代码侧 = 两仓(`src/` 树 + `sr-od-test/` 独立仓)」。测试仓实存命中:`sr-od-test/test_cw_prep_contract_shape.py:64/:83`、`test_cw_budget_disclosure.py:374`(`prep_obs_frame`)。测试翻新义务由工程门兜住,但「零未承载项」对账表的普查口径在阶段级仍留两读——对账表漏列测试仓命中时,判据字面仍可判过。

**修正方向**:3.2/3.4 普查范围补齐为「代码树 = `src/` + `sr-od-test/` 两仓(execstate 同位先例)」,与末阶段口径对齐。

### [m2] minor | design.md §2.2 槽位表 #3/#4 + §2.2-a | payload 形状升级的 option 类宿主与 import 方向未定,存在循环导入陷阱

**发现内容**:`EncounterPayload.options: list[tuple[int, str]] → list[EncounterOption]`、`SupplyPayload.options → list[SupplyOption]`,两 payload 宿主 = `kernel/cw_game_state.py:610/:617`,而 `EncounterOption`/`SupplyOption` 宿主 = `kernel/cw_events.py`,且 **cw_events 在模块级 import cw_game_state**(cw_events.py:24)——cw_game_state 反向模块级引 cw_events 即循环导入。设计只写「类型名沿用现符号」,未定解法(选项类搬家进 cw_game_state 并由 cw_events 转出口 / `from __future__` 惰性注解 + TYPE_CHECKING / 其他),这是实现者必撞的第一个语义选择,按「实现者无需再设计」应落字;选型还牵动 kernel 内骨架层→判据层类型的依赖方向表述。

**修正方向**:§2.2-a 补一句定死解法(建议:option 类宿主随 payload 留 cw_game_state 或惰性注解,二选一,并写明 cw_events 侧 re-export 兼容面),landing 3.1 文件面相应核对其已含两文件。

### [m3] minor | design.md §2.2 #9/#12;landing.md 3.4 | 两新写端的 actor 登记义务未申报(CwScreenPlanner / CwScreenBoxPick 不在 REGISTERED_ACTORS)

**发现内容**:写入口硬校验 actor 须在册(`kernel/cw_game_state.py::_validate_sig:369`,未登记显式 ValueError)。3.4 后 `CwScreenYinLang`(写 `planner_opts` 槽)与 `CwScreenBoxPick`(写 `box_card_names` 槽)成为**新**容器写端,两者现不在 `REGISTERED_ACTORS`(:285-336 逐项核对;其余 pick handler 均已在册)。设计/landing 均未申报 `register_sig_actors` 扩面义务——首写即炸不会静默错,但属「实现者需自行补的设计决定」。

**修正方向**:landing 3.4 范围补「`CwScreenYinLang`/`CwScreenBoxPick` 两新写端 actor 登记(register_sig_actors)」,design §2.2-f 配套一句。

### [m4] minor | landing.md 末阶段·词表 | 旧符号 `decide_invest` 不在「decide_ 契约全族 12 符号」内,点名式读法存在漏清面

**发现内容**:末阶段词表的「12 符号」是改后契约集,被删除的旧符号 `decide_invest` 不在内。若普查按 12 符号点名执行(而非 `decide_` 前缀),正本树中仅含旧符号的行会漏清——实测如 `strategy-docs/25_event_overlays.md:16`「13 号篇 decide_invest;P81」(该行无其他在册符号可带出;25 号篇在预登记清单内属侥幸兜住,`strategy-docs/16_evaluation_tables_reassessment.md:120` 靠同行 decide_planner 带出)。3.4 已有「`decide_invest(` 契约调用全仓归零」判据,末阶段词表未对齐。

**修正方向**:词表显式补归零词 `decide_invest`(或一句「`decide_` 按前缀普查,含已删旧符号」),消除点名/前缀两读。

### [m5] minor | landing.md 全部阶段标题 | 阶段小节标题层级与 iteration-design.md §3.1 规定不符(形式门)

**发现内容**:规范要求「每个阶段一个小节(`### 3.x <阶段名>`)」,landing 全部阶段用 `## 3.x`。零实质影响,但属形式门偏离,且阻碍工具按标题层级定位阶段小节。

**修正方向**:阶段小节降为 `### 3.x`。

## 分核结论

- **核一(无前提)**:B1、M1、M2、m1、m2、m4(覆盖完整性/锚存在性/阶段可验收性/等价性主张的发现);另完成如下面的攻击且零发现——§1.1 现状症状其余各条逐条对码(supply 容器派生旗标 cw_screen_supply_node.py:210-232、encounter 四调用点 :304/:336/:439/:466、prep_obs 4 写点 532/897/1599/1763 与 3 读点 bridge.py:174 / cw_screen_prep.py:1865 / cw_equip_wear_plan.py:163、`_PAYLOAD_DOMAINS` 三域 :171、live 清点恰两处全 shop(cw_game_state.py:2033、cw_observation.py:2618)、encounter/supply 清点仅两 sim 口(:3970-3971/:4264-4265)、Encounter/SupplyPayload 现形状 :613/:620、flow.py decide_invest 过期 docstring :471、shop.py gs-first :749);契约成员计数(abstract 12 + 工厂 1 = 13,cw_strategy.py 逐成员数过)与 §2.1-5 的 12→13/13→14 推演;§2.3 属屏映射 10 行键与 `CW_DISPATCH_SCREENS`/各 op SCREEN_NAME 逐行对上(含列车同行/骇入策划/星徽秘典弹窗/备战-武装箱选择/武装箱弹窗无 decide 五个反直觉行);路由挂点位置与 stop_at_prep/未知兜底绕行次序(cw_loop.py:1754 早退 < :1818 识别 < :1821 分发);「已 None 跳过」先例(carry :3131)、leave_screen 域守卫依赖映射含 shop(:3158)、ChannelSig.group_id 随 write_seq+1 位移(flow.py:766-768);快照 restore 不对称申报(restore rebuild 表仅 shop 手写,:4073-4083;消费面仅 cw_replay);megastar_clicked 读侧 getattr 缺省 False 先例(cw_screen_megastar.py:157);execstate #3 写侧同型/#12-#14 域 bump 先例/#20 非 Field 先例、commit ee1f4e337、turnstate 7b50d690f/170d8366f/b6e88a902、工作树无在飞 src 冲突(git status 直查);cw_replay `--diff` 退役与 `--run/--rounds` 现行(模块头 :11/:16);decisions 流退役禁复用(cw_decision_trace.py 模块头);proofs/ 排除的「已实测零命中」对该词表成立;flow/README、session.md、projection_contract、screens 21 篇、strategy-docs 五篇、game_state 各篇的清单行锚全部存在;跨文档引用锚(fields.md §2.2/§2.3/§3.3/§3.4.4/§3.4.5/§3.7.1/§8.8/§9.4、flow/README §2/§2.3/§2.4、session.md §5.1 B4)逐个可解析。
- **核二(规范遵循)**:m5;m1/m4 兼涉硬规则 4(全量同步复查)。其余逐条过:依据就地标注(关键主张均带码点/裁定/正本指针)、无过程叙事(design/landing 正文无轮次/修订措辞;进度只在 README,合规)、文档构成与 README 模板、正本更新清单行格式、通用工程门「引用不复述」成立。
- **核三(治本)**:零发现。实际攻击过的面——§1.2 归层为「约定层」成立性(签名形状确无既定约定,载体规则(fields.md §2.2 例外/§3.7.1)已立而未定为唯一承载,归层判断与两正本吻合);§2 修根判定(统一签名约定 + 决策输入单一容器承载 = 约定层根治,非逐件补丁;本批即终态方向第一批,后批显式登记);症状修法的战术权衡合规申报(per-visit 位 vs 两屏旗标语义统一登记不解决、prep_obs 豁免、kernel 纯函数零触碰,均带理由与排期归属);「同族第二次出现升架构件」检查(输入承载分散是首次被系统性收编,无逐件修模式)。
