# 设计对抗报告(第 5 轮)

> 审查对象:design.md / landing.md / README.md(草案·对抗审中)。
> 判据源:strategy-docs/00_framework.md、strategy-work.md 硬门、iteration-design.md、math_proofs 索引、代码注册表与机器、先例批(env 批)、在飞并行批(投资策略屏批)。
> 纪律:数值/口径/引文/码点全部直调复核(本轮亲验码点清单见文末);零和稀泥。

## 发现清单

### R5-1 [中] landing 四阶段判据引用「§12 通用工程门」为不可解析悬空指针(核二;根在规范模板,同族缺陷多犯)

- **位置**:landing.md:11、:23、:35、:47(3.1/3.2/3.3/3.4 完成判据「§12 通用工程门(引用,不复述)」);规范根 = docs/develop/harness/iteration-design.md:64、:197(§3.1 与附录 C 模板自带该行)。
- **发现**:iteration-design.md 正文止于 §7(§1-§7 + 附录 A-D),全文档无 §12;项目 AGENTS.md §12 = 自维护指南,无工程门内容。全仓 grep「§12 通用工程门」无可解析定义体——本批 landing 四处引用全部悬空,该判据行不可验收。仓内已有两类被对抗审查裁定可解析的形态:实指引用(changes/2026-09-15-prep-single-action-contract/landing.md:14「引用 = 项目 AGENTS.md『测试规范』§10.3 与『MCP』节」)或 landing 首节自包含定义(changes/2026-09-16-chain-observation-landing/landing.md:3、changes/2026-09-20-takeover-intel-pipeline/landing.md:3)。同族缺陷在 turnstate-retirement F-11、chain-observation F11、strategy-input-unification B2-10、takeover-intel A9、event-refresh-unify F10、投资策略屏批 R6-L-15② 多轮被裁并各自消解——本批 landing 照抄模板原句,复发。在飞并行批(2026-09-23-invest-strategy-screen-migration)landing 已改「通用工程门(自包含)」形态并显式注明「iteration-design 止于 §7」。
- **修正方向**:①landing.md 首节加通用工程门单一定义(源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节:改面 ruff 零告警 + 直接受影响测试 + L1 快速集 + 逐文件点名 + `git show --stat` 入库面复核),四阶段判据改「通用工程门(本文首节定义)」引用行;②治本 = iteration-design.md §3.1/附录 C 模板行的「§12」改可解析指引(规范侧修订,防下一批再抄)。

### R5-2 [中] strategy-work §4 必跑项 `cw_replay --diff` 未入本批验证计划,且该工具旗标已随切源退役——双向失真均未申报(核二 + 核三)

- **位置**:design.md §2.6(sim 可观测性申报 :90、验收线保全申报 :92)与 landing.md 全部验收凭据形式(:24、:36、:48)均无改动影响面步骤;规范出处 = .dsh/skills/sr-od-currency-war-dev/references/strategy-work.md:50「改动影响面:改动后必跑 `cw_replay --diff`(秒级)看行为漂移首发点」。
- **发现**:①策略行为改动批(strategy-work §6 对象三档之「实现」档)按 §4 硬门应跑 `cw_replay --diff` 看漂移首发点,本批 design/landing 全无此步骤,亦未声明豁免理由。②直调 src/sr_od/application/currency_war/sim/cw_replay.py:10-12:`--diff 分歧对比` 已在退役面清单(「旧 decisions.jsonl 源与其整帧重建/会话恢复面已随本切源退役……退役面 = _rebuild_state/_restore_session/--diff 分歧对比/意向 latch 回读/执行态可信位回读」),且现役回放面只覆盖商店黑板决策(decide_shop_screen),根本不经过补给决策——§4 的必跑项指向一个已不存在的旗标。规范自身已申报「批跑 CLI 已删、A/B 挂起」(§4 括注),但 --diff 退役未同步,规范处于半更新态。③本批对 sim 读数的盲区申报(sim 恒置一带钻槽 → 新旧读数恰同)是诚实且正确的,但那只覆盖 A/B 面,不覆盖「改动影响面必跑」义务的处置。
- **修正方向**:①design §2.6 验收线保全申报(或 landing 3.2 验收凭据)补一行申报:「strategy-work §4 改动影响面步骤的现状 = cw_replay --diff 旗标已随切源退役(cw_replay.py 退役面清单在册)、现役回放面不辖补给轴,本批影响面改由单帧测试(3.1)+ sim 盲区申报 + 实机判读锚点①-⑤ 承载」;②规范侧 = 按 skill 反馈流程把 strategy-work §4 的 --diff 必跑行与 cw_replay 现状对齐(根在规范半更新,逐批静默跳过 = 症状漂移)。

### R5-3 [中] §2.7 跨批共享编辑面枚举不完备:漏 08_events.md 与 kernel/cw_events.py 模块 docstring,两处均为与在飞 29 号稿批的实共享面(核一·边界完整性)

- **位置**:design.md:102(「本批与其共享 ≥4 份文档编辑面(25/13/strategy-docs README §2/16)。批序纪律:本批各阶段落批时重读**这些文件**当前态再动笔」)。
- **发现**:枚举的四个文件定义了「重读」义务的绑定面,但直调在飞批 landing 正本更新清单(changes/2026-09-23-invest-strategy-screen-migration/landing.md):
  - :59「`strategy-docs/08_events.md`:**E2 行 + E15 行**更新 ← 3.3」——29 批编辑 08 号稿同一张 E1-E18 表,本批编辑同表 E4 行(design.md:99);两批对同一文件的同一表格先后动笔。
  - :66「`kernel/cw_events.py`/`kernel/cw_investments.py`:模块头策略轴归属注与消费位契约注…… ← 3.2/3.3」——29 批改写 cw_events 模块头,本批收口同一行「补给决策句」(design.md:80,cw_events.py:1)。
  两处均落在「这些文件」枚举之外;08 号稿行号锚虽出现在同段「以落批时实址为准」清单里(:102 括注含「08 `:19`」),但重读义务按字面不辖它,worker 照枚举执行可在 29 批落批后的陈旧态上编辑 E4 行/模块头。
- **修正方向**:§2.7 末条枚举扩为「25/13/08/strategy-docs README §2/16 + kernel/cw_events.py 模块头」,重读义务显式覆盖;lz 落批时以实址为准的纪律不变。

### R5-4 [低] §2.1「SupplyOption 消费方四方」枚举漏第五消费方:kernel/cw_screen_report/supply_node.py(核一·依据标注精确性)

- **位置**:design.md:33(「消费方四方:obs 写端 cw_node_obs.read_supply_options(:21)、容器 gs.supply payload(cw_game_state.py:211 域版本 2,TYPE_CHECKING :114)、sim 占位采样 cw_sim_backend.py:78、测试仓」)。
- **发现**:直调 `kernel/cw_screen_report/supply_node.py:16`(`from ...kernel.cw_events import SupplyOption`,运行时 import 非 TYPE_CHECKING)、:41(`options: list[SupplyOption]`)——`CwScreenSupplyNodeObs.options` 载体类型即 SupplyOption,该模块是补给观察写路径的 payload 宿主(实机 op 与 sim 共用,sim 经 `report_screen_supply_node_obs` 摄入)。留 kernel 的**决策不变**(观察载荷契约留 kernel 恰好覆盖此消费方),但「四方」作为保留决策的依据性枚举计数失真;同清单若将来有人按它反推「可安全迁移/改形 SupplyOption」会漏点。
- **修正方向**:§2.1 消费方枚举补「观察报告载体 `kernel/cw_screen_report/supply_node.py:16/:41`(CwScreenSupplyNodeObs.options 元素类型)」,或把「四方」改「五方」。

### R5-5 [低] 3.3「三份画面文档去陈旧」锚清单缺口:supply.md 与 game 画面文档各残留旧闸语义/陈旧流程叙述未入「已知点全列」(核一)

- **位置**:design.md:100(supply.md 锚 = `:12`/`:33`/`:40`;currency_war_supply.md 锚 = `:37`/`:57`/`:39`;货币战争-补给.md 锚 = `:32`/`:39`)。对照实读:
  - `docs/develop/sr_od/application/currency_war/screens/supply.md:63`(§5 终结与交回表行「闸数据不一致(重调仍建议刷新)」)——闸内嵌后 decide 与容器不可能不一致,该行残留触发面只剩「建议刷 ∧ 锚点缺」,行名与成因已过期;
  - `screens/supply.md:80`(§8「拒绝 → 重调一次落选卡;重调仍建议刷新 → 零点击终结交回」)——「拒绝 → 重调落选卡」分支不可达(与设计对 cw_screen_supply_node.py:272-280 内联注的判定同款:读缺分支与按评分选均不可达),文档侧同语义未入清单;
  - `screens/supply.md:88`(§9 测试描述「0 与 None 零点击按原评分选」)——测试本体(op 防御面）仍有效,但文档对测试语义的描述按旧端到端行为写,随批应改写为新闸语义(建议刷不可能出自 0/None);
  - `docs/game/screens/currency_war_supply.md:19`(「bot 流程缺口(待 Loop 接线):Loop 现在在补给节点备战走 备战分支误派 → 出战(失败)」)——接线早已完成(cw_loop.py:1610-1619 在册派发),与本文件 :37/:57 同代的陈旧现状断言,不在锚清单。
- **发现**:设计对代码注释自称「已知点全列;末阶段另有全仓复扫兜底」,对画面文档给出了逐行锚却漏上述四处同语义面;末阶段复扫兜底可接住,但「全列」申报与实际清单不符。
- **修正方向**:§2.7 画面文档收口补锚(supply.md :63/:80/:88、currency_war_supply.md :19),改写口径 = 新闸语义(建议刷仅出自 left ≥ 1 帧;op 侧唯一拒绝面 = 锚点缺)与现状流程。

### R5-6 [低] §2.3 凑星论证句与判据粒度不一致:「差一格先于差更远」暗示的梯度判据未实现亦未显式拒绝(核一·实现者无需再设计)

- **位置**:design.md:61(「同轴内『差一格』先于『差更远』= 最小步数兑现」)对照同段判据「`same_star_count(char, 1, bench, deployed) == 2`」与 §2.2 tiebreak「①能凑星者先;②仍并列 → 第 3 级装备比」。
- **发现**:判据只把候选二分为「能凑星(count==2)」与其余;count==1(差两张)与 count==0(差三张)在 tiebreak ① 中同列,均落到第 3 级装备比——论证句「差一格先于差更远」若按字面读是三级梯度(2 > 1 > 0),实现口径是布尔。两种口径都自洽且零参数,但设计只给了一种;实现者按论证句扩成 count 降序或按判据式做布尔,均能自圆——语义选择未收敛到唯一答案。裁定面(三级序 + 刷新结构)不含此细化,该 tiebreak 系会话内设计细化、确认载体 = 本对抗审查,故须在本轮把粒度定死。
- **修正方向**:二选一并写死——①论证句收窄为「恰成 3 张的完成态优先,其余同列」(布尔口径,改动最小);②tiebreak 扩为 count 降序(2 > 1 > 0,「最小步数」论证的完全形态,需在 §2.3 同步说明为何 count==1 也应先于 count==0)。推荐 ①(最小语义面,越出裁定面的细化越少越好)。

## 攻击过的面清单(码点/文档点全部直调亲验)

**代码面(src)**:
- `kernel/cw_events.py`:1(模块 docstring 补给句)/:552(唯一 cw_survey19_hooks import 点,只取 encounter_tier_score)/:583(段头)/:585-596(SupplyOption)/:599-605(SupplyPick)/:609-612(`_equip_value` 委托壳)/:616-647(decide_supply 全文——只消费 equip/has_diamond,char 未触;:627-628 空帧 idx=0 no-options;:633-635 无钻必刷;:637/:641-642 key_fit set 隶属 +10)/:786(`_equip_value` 的 planner 装备档回落消费,保留后唯一消费点)/:1002-1007(EVENT_PICK_TYPES/EventPick,登记面摘位安全——完备测试遍历不走本表）
- `kernel/cw_equip_value.py`:36(「V4.4 meta 先验;实玩校准」表自注)/:42-80(EQUIP_GENERIC_VALUE 表体)/:163-189(equip_tier 档位语义、key 可含重复、需求按计数、空 key 序列恒 tier 0)/:192-210(pick_equipment (tier, base) 字典序——箱选卡消费面不受本批影响)
- `kernel/cw_survey19_hooks.py`:1-8(模块头 P8 句)/:46-56(supply_reroll_decision 三支);全仓消费面 = src 唯一 import 点 cw_events.py:552 + sr-od-test 零命中(grep 双仓亲跑)——死代码判定成立
- `kernel/cw_node_obs.py`(obs/):21(SupplyOption import)/:206(「decide_supply 建模残缺」)/:215(三钻集合)/:260-304(read_supply_options——char roster 校验、has_diamond 双通道、按 x 左→右)
- `kernel/cw_game_state.py`:102-115(TYPE_CHECKING)/:211-212(supply 域版本 2)/:616-618(SupplyPayload.options)/:2124(board = 羁绊计数禁双写)/:2211-2231(溢出席 overflow_warning/overflow_card 定义,单槽机制锚)/:3645-3651(deployed_rows_of 行域二元组)/:3654-3663(bench_units_of 单位紧缩序)
- `kernel/cw_screen_report/supply_node.py`:16/:41(SupplyOption 第五消费方——R5-4 证据)
- `kernel/cw_comps.py`:102(core_chars)/:111(shared_chars)/:112(transition_chars,按 102-111 锚不在名单 ✓)
- `kernel/cw_merge_simulate.py`:93-107(_entry_identity 非容器形状 fail-closed None——二元组直传漏域实证)/:337(同名同星 ≥3 合一)/:424-433(same_star_count)
- `kernel/cw_intention.py`:1123-1156(pair_target_comp 伪 comp,key_equips 走缺省恒空——申报 ⑤ 成立)/:2075-2077(降格清 locked_comp)
- `kernel/cw_effect_inventory.py`:1502-1505(bench_full 拒落零写)/:1516(BenchGrantResult)
- `kernel/cw_action_report/pick_supply.py`:48-50(入席恒 1★ 先验)/:79-84(单位腿走 grant_bench_unit_cascade)
- `kernel/cw_vocab.py`:728/:916(「替代 SupplyPick」表述)
- `operations/cw_op/cw_pick_supply_action.py`:37(SupplyPick.refresh 决策句)
- `operations/cw_screen/cw_screen_supply_node.py`:8-14/:39-40(sim 接线未接陈旧注)/:242-245(旧评分叙述)/:264-292(重调路径与双闸——闸内嵌后唯一剩余触发面 = 锚点缺,重调纯函数同输入同输出,op 语义不变判定成立)
- `operations/cw_loop.py`:1089-1092/:1610-1619(补给屏派发在产——sim 申报「flow.decide_supply 在 sim 局中真实被调」成立,:39-40 陈旧注判定成立)
- `sim/cw_sim_backend.py`:78/:573-585(supply_options 占位分布:char 恒空 + diamond_slot 每帧恰一带钻槽 → 新旧 sim 读数恒同,盲区申报成立)/:867-882(补给刷新点击源)
- `sim/cw_replay.py`:10-12(--diff 退役面在册——R5-2 证据)/:14-17(现役用法无 --diff)
- `strategies/impl/flow.py`:326-353(锁线 comp 物化链/P1 伪 comp 臂/target_comp 写入)/:516-518(invest_env 意向两参先例)/:538-553(现役 decide_supply——refresh_used 预计算 :545-546)/:693-740(decide_box_card 先例:get_comp 失败回落 :712-718、两账构造 :719-740、deployed 展平 :729-731)
- `strategies/impl/mandate_v1/invest_env.py`:381-401(次数闸内嵌 decide + None fail-closed 先例)
- `strategies/impl/mandate_v1/encounter.py`:1-3(搁置让位注——「非迁移先例」判定成立)
- `data/cw_equipment_data.py`:53(财富宝钻 effect 原文逐字核对 ✓)/:64-65(红钻/蓝钻星徽合成材料)
- `strategies/impl/cw_strategy.py`:172-175(decide_supply ABC 契约——flow 方法名保留则 stub 存活判定成立)

**测试仓(sr-od-test)**:
- test_cw_unified_action_4.py:27-33(SupplyPick 类型 import)/:303(实例构造)——随删面恰此两处 ✓
- test_cw_obs_arch_event_screens_step3.py:47/:61(decide_supply stub)/:130-181(supply 刷新闸行为测试——桩在 flow 方法名,op 侧防御面语义,3.2 后继续有效 ✓)
- test_cw_supply_pick_immediate_report.py:125(stub)✓;test_cw_supply_advance_wiring.py(零 decide_supply 消费,不受影响 ✓);全仓 grep `decide_supply|SupplyPick|supply_reroll` 双仓核对,design §2.6 测试面申报(「在册无 kernel 侧 supply 决策专项测试」）属实 ✓
- test/harness/sim_backend_runner.py:314-381(真 CwLoop + 真 MandateV1Strategy 装配——sim 申报的装配依据属实 ✓)

**文档面**:
- strategy-docs/25_event_overlays.md:3/:11/:18(三锚 ✓,头注先例 :4);13_pick_family.md:20/:40(「选项价值 vs 目标线组件/成品需求」与实码不符的判定属实 ✓;§0 fallback 纪律 :11 ✓);08_events.md:19(E4 行,P42/P40 变体② 口径 ✓;E1 行 = 28 批改写先例 :16);16_evaluation_tables_reassessment.md:74(改形挂账行、cw_events.py:293 死锚、sim/checks/ledger.py:970/1035——glob 双查该文件全仓不存在,「清理」判定成立 ✓);strategy-docs/README.md §2(分篇表现到 28,增 30 行合法 ✓)
- screens/supply.md:12/:33/:40(在册锚 ✓)+ :63/:80/:88(未入锚——R5-5);docs/game/screens/currency_war_supply.md:37/:39/:57(在册锚 ✓)+ :19(R5-5);docs/game/screens/货币战争-补给.md:32/:39(在册锚 ✓)
- math_proofs.md 索引:P40(变体①-⑩)/P42(装备机器 EV,🔴待标定)/P81(投资策略屏逐卡刷新——「非 P81 辖域」判定 ✓)/P97(刷新预算)行全读,设计引用口径与索引一致
- 先例批:changes/2026-09-23-invest-env-strategy-migration/design.md 全文(结构/立场序合法性形态/共用模块消费先例——supply 批的先例引用全部真实)
- 在飞批:changes/2026-09-23-invest-strategy-screen-migration/design.md + landing.md(29 号稿占用、共享编辑面真实清单——R5-3 证据)

**规范面**:
- iteration-design.md 全文(四条写作硬规则/阶段七件/三核/引用寿命);strategy-work.md §1(零调参两分类、未证即退役——+10 随删件退役、EQUIP_GENERIC_VALUE 按 16 号稿在册处置降格定序常数,均走的在册通道)/§3(无开关直落)/§4(验证阶梯——R5-2)/§5(单帧测试与出处纪律——landing 3.1 凭据①-⑨逐条引 design 节 ✓)/§6(对抗纪律);AGENTS.md(注释/文档/测试规范)
- README.md 索引(链接目标实存性——attack.md/r2/r3/r4 在册,attack-r5 待本报告创建,「启动后创建」申报属实;轮次计数内部自洽)
