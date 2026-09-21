# gain-chain 设计对抗报告(核一·无前提攻击)

## 卷首

- **攻击范围**:design.md / landing.md / README.md 三份(2026-09-21-gain-chain),按 iteration-design.md §7 核一(无前提,攻击角度自选)+ §5 写作硬规则(依据就地标注/实现者无需再设计/无过程叙事/修订后全量同步复查)执行。方法:逐条打开 design.md 引用的权威源锚核对内容、试读(假实现者逐阶段问「凭这份能开工吗」)、landing 判据/文件面/正本清单逐项对真。
- **总结论**:**需修订后重审**——无致命发现,链原语核心时序/对拍锁/rand 纪律钉得住,但 4 条重要发现(advisor 条目语义矛盾 / 溢出字段写端单一源失真未申报 / op-effects.md §8 正本清单锚漂移 / §2.7 best-effort 依据锚失效)落在「定稿门槛」之内,须修订 design/landing 并复查后再定稿。

## 发现清单

严重度:致命=无法开工 / 重要=语义缺口 / 次要=表述与规范。

### F1(重要)advisor 条目的 immediate 腿语义矛盾

- 位置:design.md §2.3(on_env_gained 枚举)。
- 主张摘录:「`chars_immediate` 逐个 → `gain_character(char, 1★, rand=rand)`」「`advisor=True` → **不入席**:专家顾问入商店语义」。
- 攻击:两条是并列枚举腿,未声明互斥。而 ENV_GIFTS 中 3 条 advisor 条目(特邀专家:停云/加拉赫/桑博)**同时携带 chars_immediate**(顾问身份本身,供构建校验用)——字面实现会对同一顾问先入席再申报入店,双重落账;正确语义应为 advisor=True ⇒ 不消费 chars_immediate 入席、仅遥测申报。§2.6-2 的「现经链入席/advisor 申报」同样含混。
- 证据:`kernel/cw_investments.py:1588-1593`(`'特邀专家:停云': GiftGrant(chars_immediate=('停云',), advisor=True)` 等三条);顾问语义锚 `:227-229`(advisor=True = 付费购买期权,不入席)。
- 备注:特邀专家:银狼(无 immediate)不受影响;契约类(无 advisor)不受影响。

### F2(重要)溢出字段写端单一源声明被链写打破,未申报任何更新面

- 位置:design.md §2.1(gain_character 溢出落位「写 overflow_warning=True + overflow_card=name」)、§2.6-3;landing.md 正本更新清单。
- 攻击:overflow_warning/overflow_card 现行声明「写入端单一源 = CwScreenPrep 观察写端(渠道①)」+ sell 溢出腿 logic 直写(消费向),投影审计 basis 亦按此成文。gain_chain 新增第三写端(生产向直写 True/name),但 landing 正本清单七条中**无一条**覆盖 fields.md §3.2.20 溢出字段写端、cw_game_state.py 字段定义注释、cw_projection_audit.py basis 串——收尾后字段「写入端单一源」注释与审计依据即失真,且违反项目 AGENTS §8(期望校验类/索引字段的写入端注释必须声明)。
- 证据:`kernel/cw_game_state.py:1992-2008`(两字段写端单一源注释);`docs/develop/sr_od/application/currency_war/game_state/fields.md:508-524`(§3.2.20 写端声明);`kernel/cw_projection_audit.py:216-220`(basis = 「观察写端单一源 + 溢出腿入位消费直写」)。

### F3(重要)正本更新清单锚漂移:op-effects.md §8 所指内容不存在

- 位置:landing.md 正本更新清单「logic-updates/op-effects.md §8(portal 效果登记迁链)← 3.2」。
- 攻击:op-effects.md §8 实为「语义验证(观察边界 reconcile)」,与 portal 效果登记无关;且 op-effects.md **全文没有 portal 登记/register_portal_from_env 的任何记述**(现役登记面的正本记述在 screens/invest_env.md §6)。清单要么节号错、要么该条实为「op-effects.md 需新增登记面条目」——两种读法落码动作不同,正本更新批无法照单执行。
- 证据:`docs/develop/sr_od/application/currency_war/game_state/logic-updates/op-effects.md:62`(§8 标题);全文检索无 register_portal/portal 登记内容;`screens/invest_env.md:80`(现役登记面正本)。

### F4(重要)§2.7「best-effort 现役同款」依据锚失效,异常粒度未定

- 位置:design.md §2.7「链内异常:登记面 best-effort 不阻塞确认链(pick_invest 现役同款,锚 pick_invest.py:186)」。
- 攻击:pick_invest.py 全文无 try/except、无 best-effort 形态;:186 是 `_apply_effect_joy_contract` 体内一行 `steps: list[str] = []`,锚内容完全不支持主张。「现役同款」实际存在于**调用方**画面 op 的 try/except(cw_screen_invest_env.py:380-389,已由 §2.1-2 正确引用)——§2.7 此句锚错源;且「链内异常不阻塞」的粒度(try 包整链 / 只包登记腿 / 逐原语)未定,实现者必须自行拍板。
- 证据:`kernel/cw_action_report/pick_invest.py:186`(锚内容);对照 `operations/cw_screen/cw_screen_invest_env.py:380-389`。

### F5(重要)active_env 写点迁移与 op-layer.md 动作事实边界硬规则的合同张力未申报

- 位置:design.md §2.5(选择事实归落地链);landing.md 正本更新清单(未列 screens/op-layer.md)。
- 攻击:op-layer.md §1.1「动作事实边界(硬规则)」:选择落地记录(chosen_* 类)留守画面 op、记账随判定点走、**不进 report**。本设计把 active_env 写从画面 op 选择点迁入 kernel 链(经 report_action_pick_invest_param → gain_invest_env),与该硬规则直接张力;设计未声明 active_env 是否属 chosen_* 域组、也未把 op-layer.md 列进正本更新清单(若合同要改,op-layer.md §1.1/§2 必须同步,否则收尾后合同正本与实现矛盾)。
- 证据:`docs/develop/sr_od/application/currency_war/screens/op-layer.md:35/75`(重入裁决点记 chosen_* + 硬规则原文);现役写点 `cw_screen_invest_env.py:361-372`。
- 备注:这是「合同该跟着改但没人改」的漏申报,不是方案本身错——裁定①(用户裁定)优先级高于 op-layer 旧表述,但正本清单必须包含它。

### F6(次要)「概念股类环境」术语错位

- 位置:design.md §2.6-2。
- 主张摘录:「概念股类环境(chars_immediate 8+ 条,如 翡翠/砂金)此前零容器写,现经链入席」。
- 攻击:ENV_GIFTS **无任何概念股键**;翡翠/砂金来自「公司契约」(:1554-1557)。含 chars_immediate 的是契约类与特邀专家类;概念股(追击/燃血等,data/cw_invest_data.py:416-430)效果未建模、新链下依旧安静不写,属 §1「明确不解决」的推广批——例证选错族名,读者会把「行为扩张面」理解错一圈。
- 证据:`kernel/cw_investments.py:1547-1594`(ENV_GIFTS 全键集);`data/cw_invest_data.py:416-430`(概念股 = PLAZA_PORTALS 另一族)。

### F7(次要)gain_invest_env 写行溯源字段与 GainOutcome 分形状未钉死

- 位置:design.md §2.1。
- 攻击:①gain_invest_env 签名无 evidence/producer,但其内部 active_env write_logic 现役带 produced_by='CwScreenInvestEnv'(cw_screen_invest_env.py:368-372);迁移后写行的 produced_by/evidence 取值设计未定。②GainOutcome 字段(落位/落点/合成级数/回调命中列表)是对 gain_character 量身描述,gain_invest_env/gain_equipment 返回同一 dataclass 时哪些字段恒空/失效未说明——留证消费与测试断言会各写各的。
- 证据:`cw_screen_invest_env.py:368-372`;design.md §2.1 GainOutcome 段。

### F8(次要)session 参数签名细节未钉死

- 位置:design.md §2.5。
- 攻击:「增加 session 关键字参数(portal 支消费)」未定缺省值(必带 vs 缺省 None)。三个现役调用点中两个不消费(发射相 cw_overlay_pick_action.py:480、策略屏落地 cw_screen_invest_strategy.py:449)——缺省 None 才兼容,但这是实现者自行推断的选择,属 §5-2 卡点边缘。另:策略屏 handler 是否也要顺手传(为后续策略屏迁移批预留)未表态。
- 证据:`cw_overlay_pick_action.py:480-483`;`cw_screen_invest_strategy.py:449`。

## 试读结论(实现者视角)

- **阶段 3.1(链原语与回调)**:主体可开工——固定时序(落位→回调→升星→产物递归)、合成池口径(备战∪上阵∪溢出,观察源溢出卡 1★ 兜底)、单级合成对齐 merge_simulate 不动点段(:206-279 逐条规则在源可查)、对拍锁写法、rand 透传/翻转、未观察与溢出位被占的失败安全,均有答案。**卡点 = F1**:on_env_gained 对特邀专家 advisor 条目的处理必须先裁决(停云入不入席),否则该枚举只能写错或停手。
- **阶段 3.2(投资环境落地相接入)**:可开工——portal 支改调 gain_invest_env、画面 op 尾段删两块、PICK_INVEST_EFFECTS 删行、session 由重入裁决出口传 ctx.cw_match.session,调用点与签名兼容性核过(cw_screen_invest_env.py:233-249 出口在手,session 可达)。弱卡点 = F4(链内异常 try 的粒度)与 F5(合同面是否同步改)。
- **末阶段(正本更新)**:照单执行会漏——F2(overflow 字段写端/审计 basis)与 F5(op-layer.md)不在清单上,F3 一条无法照单执行。

## 符号/路径存在性核对结果(design+landing 引用面全量)

| 引用 | 结果 |
|---|---|
| cw_effect_inventory.py::grant_bench_unit_cascade / merge_cascade_write / apply_equip_acquire_consequence / register_portal_from_env / EQUIP_ACQUIRE_CONSEQUENCES / BenchGrantResult | ✓(1451/1385/1508/636/1360/1443) |
| cw_effect_inventory.py 锚 :1483-1484(bench_full)/:1489-1492(级联)/:1475-1488(基座)/:1461-1464(写通道)/:1442-1448/:1421(#mergeN)/:1525-1533(表消费) | ✓ 全部命中且内容支持 |
| cw_merge_simulate.py::merge_simulate 不动点段 :206-279 | ✓(载体优先/最左/溢出归位/装备继承/分组键逐条在段内) |
| cw_game_state.py::overflow_warning/overflow_card(:1992-2008)、write_logic(:2579)/write_logic_rand(:2607)、:2004-2006(1★ 兜底) | ✓ |
| cw_investments.py::ENV_GIFTS(:1547-1634)/GiftGrant(:233-)/构建校验(:1609-1634)/advisor(:227-229) | ✓(F1/F6 为内容层问题,锚本身在) |
| pick_invest.py::report_action_pick_invest_param(:225)/PICK_INVEST_EFFECTS(:208)/EVIDENCE_OVERLAY_CLOSED(:51)/:98-100/:106-109/:133-137 | ✓;**:186 锚内容不支持主张(F4)** |
| cw_screen_invest_env.py::_decide_and_act active_env 写(:361-372)与 portal 登记(:380-389)、重入裁决出口(:233-249) | ✓ |
| cw_action_report/sell_bench.py 溢出腿(:29/:68) | ✓ |
| sim/cw_sim_nodes.py「席满不丢,溢出悬挂由容器」(:264) | ✓ |
| strategies/impl/mandate_v1/mandate.py 溢出告警门(:1329) | ✓ |
| docs/game/screens/currency_war_prep.md 告警/溢出节(:52-53) | ✓ |
| docs 正本:game_state/fields.md §3.4.3(:708)/§3.2.20(:508)、action-logic-state.md 事件单选族(:335)、screens/invest_env.md §1-9、flow/action_exec.md、flow/action_ops.md | ✓ 存在 |
| logic-updates/op-effects.md §8 | **节存在但内容 = 语义验证,非 portal 登记(F3)** |
| 测试:test_cw_yinlang_phase32.py / test_cw_obs_arch_phase_screens.py / test_cw_unified_action_4.py | ✓ 存在;test_cw_gain_chain.py 为新建 ✓ 合规 |
| kernel 依赖方向(cw_gain_chain ← pick_invest;→ cw_effect_inventory/cw_merge_simulate/cw_exec_state/cw_game_state/cw_investments) | ✓ 无环(cw_effect_inventory 不回依新模块) |

其余核过无发现:§1 现状症状四条与 §2 覆盖一一对应,「明确不解决」五项无偷偷外溢;landing 设计依据节号全部真实、判据可写成测试、依赖序正确(3.1→3.2→末阶段);无过程叙事措辞;README 除进度行外无需动。

## r2 复核(修订稿对照 + 新锚全量复查)

r1 发现处置对照:

| 发现 | 判定 | 核对依据(修订后) |
|---|---|---|
| F1(重要)advisor 互斥 | **解决** | design §2.3 改「先按 advisor 分道,两道互斥」;advisor 行 chars_immediate 仅作申报身份、禁再入席;新锚 cw_investments.py:229「False=直接送卡(契约,白得资产)」实存且支持 advisor=False 分道语义 |
| F2(重要)溢出写端单一源失真 | **基本解决,残留 R1** | design §2.1 写端声明(双写端,先例 = 卖牌溢出腿直写——已核 sell_bench.py:71-78 确为 overflow_card/overflow_warning 的 logic 直写,锚成立)+ §2.6-6 + landing 清单 fields.md §3.2.20 行已加;projection_audit 溢出两行(:214-220)与 active_env basis(:152)已核存在。残留见 R1 |
| F3(重要)op-effects.md §8 锚漂移 | **解决** | 该行已删,改为 effect-domain.md(文件实存;「原无正本记述本批首立」与 effect-domain.md 现状相符)+ fields.md §5.1(「在场效果激活账本」实存,:1019) |
| F4(重要)best-effort 锚失效 | **解决** | §2.7 重写为三条粒度(原语零吞错 / best-effort 收在非容器写登记·申报腿 / 调用方零额外吞错),旧锚显式作废;「语义自画面 op 现行登记面 try/except 迁入」与 cw_screen_invest_env.py:380-389 相符 |
| F5(重要)op-layer 合同张力 | **解决** | §2.6-7 申报合同收窄(投资环境域,裁定①);landing 清单加 op-layer.md §2.2——已核 §2.2「辖域边界」实存(op-layer.md:71,动作事实边界硬规则在其辖内) |
| F6(次要)概念股术语 | **解决** | §2.6-2 改「契约类…特邀专家走 advisor 申报分道」 |
| F7(次要)GainOutcome/produced_by | **解决,残留 R2** | GainOutcome 五字段钉死(placed/landing/merge_levels/effects/detail,三原语共用);producer 入 §2.1 签名。残留见 R2 |
| F8(次要)session 缺省 | **解决** | §2.5 `session: object | None = None`,None = 登记腿跳过、容器写照常 |

新锚全量复查(修订引入):sell_bench.py 溢出腿直写 ✓(:71-78);effect-domain.md 存在 ✓;fields.md §3.2.20(:508)/§5.1(:1019)✓;cw_projection_audit.py :152(active_env basis)/:214-220(溢出两行)✓;design §2.1 与 §2.5 的 gain_invest_env 签名/调用形态一致 ✓((gs, session, env_name) 位置形参两处一致)。

r2 新发现:

- **R1(重要)landing 3.2「范围」与「文件面」失同步**:范围新增「容器字段注释(`cw_game_state.py` overflow 两字段双写端)与 `kernel/cw_projection_audit.py` 对账 basis 行同步」,但 3.2 **文件面**仍只列 pick_invest.py / cw_screen_invest_env.py / 测试——两个必改文件不在允许动文件清单内:照文件面干 = 范围做不完,照范围干 = 动未申报文件。正是 iteration-design §5-4(修订后全量同步复查:文件面真实路径)防的事故形态。修法 = 3.2 文件面补 `kernel/cw_game_state.py`(仅注释)与 `kernel/cw_projection_audit.py`(basis 行)。
- **R2(次要)design §2.1 内部措辞矛盾**:「`producer` 必传入参」(第 33 行)与签名 `producer='CwGainChain'` 带缺省值(第 31 行)互相矛盾——「必传」与「有缺省」二选一。

r2 试读:3.1(F1 解决后)**可开工**——时序/对拍锁/rand 纪律/advisor 分道/异常粒度全部有答案;3.2 **可开工**,唯 R1 需先修文件面(补两个路径),否则该阶段的合法改动面写错。

r2 总结论:**接近收敛,未达收敛**——r1 四条重要全部解决,但修订自身引入 R1(重要,范围↔文件面失同步)与 R2(次要)。修 R1(必)+ R2(顺手)后即可定稿;README 进度维持「设计对抗:进行中」。
