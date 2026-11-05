# 设计对抗报告 · 第 7 轮（attack-r7）

> 审查日期 2026-09-24。无前提独立审查：攻击对象 = 本目录 design.md / landing.md / README.md（当前工作区状态）。判据源自取并全部直调复核，未采信任何前轮报告结论。规范源：docs/develop/harness/iteration-design.md（四硬规则/§7 三核/阶段七件/正本清单）、.dsh/skills/sr-od-dev-currency-war/references/strategy-work.md（§1 零调参/§4 验证阶梯与可观测性声明/§5 单帧测试/§6 对抗纪律）、strategy-docs/00_framework.md 与 README.md（宪法五/六）、项目 AGENTS.md。行号锚按任务纪律以符号锚优先，±3 漂移且语义锚成立者不登记。

## 发现清单

### R7-1 [中] 「空串 → None + 告警」口径 §2.5 与 §2.2 自相矛盾（R6-5 半吸收残留；核一·篇内自洽 + 核二·硬规则 4）
- **位置**：design.md:73（§2.5「`locked_comp` 套名经 `get_comp` 解析（空串/失败 → None + 告警，`decide_box_card` 先例 `flow.py:712-718`）」）对照 design.md:47（§2.2「空串按未锁口径 None（无告警 = 未锁常态）、解析失败 None + 告警哨兵」）。
- **发现**：R6-5 点名两处（:47 与 :73）都需按先例拆分口径，落地时只改了 :47，:73 原样残留——先例实码（flow.py:710-715）空串走 `if locked:` 之外**无告警**，仅非空解析失败才 `log.warning`。现在同一份设计对同一语义给出两个相反答案：实现者读 §2.2 实现空串静默、读 §2.5 实现空串告警，撞上即停手提请修订（硬规则 2 卡点），且 README「第 6 轮 6 项均已全部吸收」的申报被证伪（同见 R7-5/R7-6）。
- **修正方向**：:73 改述为与 :47 一致——「空串按未锁口径（无告警）；非空但解析失败 → None + 告警哨兵（照 `decide_box_card` 先例）」。

### R7-2 [中] 跨批共享编辑面清单漏 `flow.py` 与 `cw_vocab.py` 两处（核一·边界完整性 + 核二·硬规则 4）
- **位置**：design.md:104（§2.7 末条「共享 **6 处**编辑面——strategy-docs 4 份 + `08_events.md` + `cw_events.py` 模块 docstring」）。
- **发现**：直调在飞 29 批（changes/2026-09-23-invest-strategy-screen-migration）landing.md:18/:32：其 3.1 改写 `flow.py::decide_invest_strategy` 分支、注释收口清单含 `flow.py`（:438-444）与 `cw_vocab.py`（:406-410/:414/:428-430）；本批 3.1 改写同文件 `flow.py::decide_supply`（:537-552）、3.2 收口同文件 `cw_vocab.py`（:728/:915）。两文件都是双批编辑面，却不在「6 处」清单内——批序纪律「落批时重读上述文件当前态再动笔」对这两处不触发，且 29 批先落时其行数增删会使本批 design 引用的 flow.py 行号锚（:326/:327/:335-352/:353/:516-518/:544-545/:712-740）整体漂移，而漂移重核义务（§2.7 只写了 cw_events 代码锚与 13 号稿锚）不覆盖 flow.py。
- **修正方向**：§2.7 共享编辑面清单由 6 处扩为 8 处（+`strategies/impl/flow.py`、+`kernel/cw_vocab.py`），批序纪律同步覆盖；并补一句「29 批先落则本批 flow.py 行号锚按符号名（decide_supply/decide_box_card/_refresh_direction_views）重定位」。

### R7-3 [中] 新 `flow.decide_supply` 对入口内务 `_consume_prep_direction_frame()` 的去留未申报（核一·实现者无需再设计）
- **位置**：design.md:73（§2.5 flow 接线段）；现码 flow.py:546。
- **发现**：设计对现役方法体做了逐行编排——候选读口「原样」（:542-543）、闸前移「随迁删除」（:544-545）、kernel 调用换 `supply.decide`——唯独 :546 的 `self._consume_prep_direction_frame()   # 入口内务` 只字未提。该方法体是全部兄弟入口的公共协议（decide_encounter :563、decide_megastar :579、decide_partner :598、decide_planner :615、decide_box_card :704 均在候选读口后调用），照 §2.5 的枚举重写方法体时它是唯一无处置答案的现存行：删掉 = 备战黑板帧在补给入口不被消费、方向视图滞留（未申报的行为变化）；保留 = 应显式申报。语义选择无出处即分叉点。
- **修正方向**：§2.5 补一句「入口内务 `_consume_prep_direction_frame()` 保留原位（候选读口后、决策前，与兄弟入口同构）」；若有意删除则给行为申报。

### R7-4 [低] P1 配方锁帧的刷新分支未申报：申报⑤描述不全，判读锚④与锚③同帧冲突，单帧测试⑧构造缺前置（核一·判据可验收）
- **位置**：design.md:88（§2.6 申报⑤「选卡退化为『钻或通用值定序』——……如实申报该帧形态」）、design.md:92（实机锚④「P1 配方锁帧按『钻或通用值』选卡」）；landing.md:14（测试⑧同口径）。
- **发现**：按 §2.4 判据，P1 帧（`locked_comp` 恒 None）角色级不激活、装备级全落 tier 0 → **三级全空恒真**：无钻且 `supply_refresh_left ≥ 1` 时产出 `SupplyRefreshSuggestion`（刷新），只有闸拒绝（left 缺/尽）才落第 3 级按通用值选卡。申报⑤自称「如实申报该帧形态」却只写了选卡分支、漏刷新分支；锚④（按通用值选卡）与锚③（三级全空帧仍刷新）在同一 P1 无钻帧上不可同时成立，实机判读按锚④对账会把正常刷新误记为不命中；单帧测试⑧照字面构造 P1 帧断言「按钻或通用值选卡」，若未把 `supply_refresh_left` 置缺/尽则断言必红。
- **修正方向**：申报⑤补全为「无钻且次数未尽 → 刷新（同锚③）；次数缺/尽 → 选卡退化为钻或通用值定序」；锚④与测试⑧注明「闸拒绝帧（left 缺/尽）构造」。

### R7-5 [低] `cw_vocab.py` 第二锚行号仍为 :916，实址 :915（R6-3 第 3 项未吸收）
- **位置**：design.md:34（§2.1）与 design.md:80（§2.6 注释收口清单），均写「`cw_vocab.py:728/916`」。
- **发现**：直调 cw_vocab.py：「替代 SupplyPick」docstring 起于 :728（CwActionPickSupplyParam，正确）与 :915（CwActionRefreshSupplyParam「替代 SupplyPick.refresh 旗标」）；:916 是该 docstring 的续行。R6-3 已点名，未改。语义锚成立（±3 漂移类），但该文件不受 29 批漂移影响、属现状锚写错，且随 R7-1 同证 README「全部吸收」申报失真。
- **修正方向**：两处改 `cw_vocab.py:728/915`。

### R7-6 [低] 删除面标签把 `EventPick` 联合误罩进「EVENT_PICK_TYPES 元组」（R6-3 第 4 项半吸收，改错方向）
- **位置**：design.md:77（「`EVENT_PICK_TYPES` 元组中该位（`:1003`/`:1007`）」）。
- **发现**：直调 cw_events.py:1002-1007——:1003 是 `EVENT_PICK_TYPES` 运行时登记元组中 `SupplyPick` 位；:1007 是 `EventPick` 类型联合（另一构造，注释自注「运行时零消费」）。R6-3 原发现是「两行共用『联合』标签不准」，修正方向为「登记元组 + 联合」双表述；现稿把标签统一改成「元组」罩住两锚，:1007 反被错标（元组不含联合）。删除意图两行都对，属值对标签错。
- **修正方向**：改「`EVENT_PICK_TYPES` 元组中该位（`:1003`）+ `EventPick` 联合中该位（`:1007`）」。

### R7-7 [低] 在飞 sim-redesign 批的 `decide_supply` 复用面失配无交接申报（核一·边界完整性）
- **位置**：design.md:104（§2.7 跨批协调只辖 29 批）；关联 changes/2026-09-15-sim-redesign/design.md:70/:104/:267（三处声明复用面 = `kernel/cw_events.decide_supply`，该批 landing 状态 = 未落地）。
- **发现**：本批 3.2 删除 `decide_supply` 后，sim-redesign 批 design 声明的复用面失指。先例：29 批 landing:33 对自己的 `decide_event` 删除向 sim-redesign 批作了显式交接申报（「该批开工前置 = 复用面改指策略层」）；本批对同批的同类波及零申报。实际危害低——changes/ 过程区由该批自行换基，且该 design 的旧引擎引用面已大量被 sim-backend-unification 批超越——但按本仓已确立的跨批交接惯例，申报面应完整。
- **修正方向**：§2.7 末补一句交接申报（照 29 批 landing:33 形态）：「在飞 sim-redesign 批 design :70/:104/:267 以 `kernel/cw_events.decide_supply` 为复用面，本批删除后由该批开工前自行换基指策略层载体」。

### R7-8 [低] 行为变化申报头注的分类标签漏第 4 条（值对标签错轻症）
- **位置**：design.md:83（「**行为变化申报（验收对照基线；①②③为判据语义变更，是本迭代目的非回归）**」）。
- **发现**：第 4 条「多钻 tiebreak 新增角色/装备细分（单钻行为不变）」同样是判据语义变更（旧制多钻取首张带钻，新制进 2/3 级细分），却不在 ①②③ 的分类内；第 5 条（P1 帧形态申报，行为与旧制同）不入分类正确。分类标签少计一条，验收对照时第 4 条的「目的性变更」定性会被读成附带申报。
- **修正方向**：头注改「①②③④为判据语义变更（④仅多钻帧）；⑤为帧形态申报」。

## 零发现面（实际攻击过且对得上的面）

- **kernel/策略码锚直调（~45 处全对上）**：cw_events.py `:1`（模块 docstring 补给句在册）/:583（段头注）/:585-596（SupplyOption）/:599-605（SupplyPick）/:609-612（`_equip_value` 委托壳）/:616-647（decide_supply 全文——只消费 `equip`/`has_diamond`，`char` 全程未触；:627-628 空帧 idx=0；:633-635 无钻必刷；:637/:641-642 key_fit set 隶属 +10）/:786（`_equip_value` 保留后唯一消费点 = planner 装备档回落，decide_planner 不在迁移面）/:1002-1007（登记面与联合）；cw_equip_value.py `:36`（表自注「V4.4 meta 先验；实玩校准」逐字）/:42-80（EQUIP_GENERIC_VALUE 表本体）/:163-189（equip_tier 3/2/1/0 语义、key 可含重复按 count 计需、近兑现按备用账）/:192-210（pick_equipment = (tier, base) 字典序 argmax、并列取输入序先者——与 §2.2 排序语义逐位同构，R6-4 直调指令已补）/:1 模块头（「禁第二套打分」裁定在册）；cw_survey19_hooks.py `:1-8`（P8 句）/:46-56（supply_reroll_decision 三支；全仓 src+sr-od-test grep 仅定义点，唯一 `cw_survey19_hooks` import = cw_events 只取 `encounter_tier_score`——死代码判定成立）；cw_node_obs.py `:21`（SupplyOption import）/:206（「建模残缺」注）/:215（三钻集合）；cw_game_state.py `:114`（TYPE_CHECKING）/:209（supply 域版本 2）/:2283（supply 字段）/:2210-2229（溢出位单槽双写端，§2.5 机制锚成立）；cw_merge_simulate.py `:93-119`（`_entry_identity` fail-closed——「直传二元组静默跳过」机制核实成立：list 非 Unit/BenchSlot → None 跳过）/:337（同名同星 ≥3 合一）/:424-433（same_star_count 全场域单一源）；cw_comps.py `:102-112`（core_chars :102/shared_chars :111 入名单、transition_chars :112 明示排除）；cw_intention.py `:2075-2077`（降格路径清 `locked_comp`——`demoted_endgame` 防御位申报成立）；cw_effect_inventory.py `:1472/:1502-1505`（grant_bench_unit_cascade 席满拒落零写）；cw_action_report/pick_supply.py `:48-50`（入席恒 1★ 先验）；cw_screen_report/supply_node.py `:16/:41`；cw_vocab.py `:728/:915`；cw_pick_supply_action.py `:37`；cw_sim_backend.py `:78/:573-585`（占位分布恒置恰一带钻槽——sim 盲区申报机制链成立：两侧恒选钻、刷新两侧永不触发）；cw_replay.py `:10-12`（--diff 随切源退役、现役只辖商店决策——豁免申报成立）；cw_strategy.py `:172-175`（ABC 方法名保留，非第二 kernel 调用点）；cw_equipment_data.py `:53`（财富宝钻 effect 原文逐字）/:64-65（红钻/蓝钻星徽材料）。
- **flow/invest_env 先例锚**：flow.py `:326`（锁线 get_comp）/:327（P1 锁帧 locked_comp 恒空注）/:335-352（P1 伪 comp 物化臂）/:353（target_comp 写入）/:515-518（invest_env 意向 ist 直通先例）/:537-552（现役 decide_supply：闸前移恰 :544-545）/:692-739（decide_box_card：空串无告警/解析失败告警 :710-715、两账构造 :719-739、deployed 展平 `*_wf, *_wb` :728-730）；invest_env.py `:365-401`（decide 签名 + 闸内嵌 `env_refresh_left` None fail-closed 先例 :388-401）；op 侧重调路径 cw_screen_supply_node.py `:272-288`——「闸内嵌后仅剩锚点缺失触发面、重调同输入同输出仍返 Suggestion → 零点击终结、op 层零行为改动」的推理经实码逐分支核验成立。
- **测试面**：sr-od-test grep 全量——`decide_supply`/`SupplyPick` 命中恰 design 申报四处（test_cw_obs_arch_event_screens_step3.py:47/61、test_cw_supply_pick_immediate_report.py:125 为 strategy 级 stub 桩在 flow 方法名，不随删；test_cw_unified_action_4.py:27-33/:303 类型 import 与构造点随删）；「在册无 kernel 侧 supply 决策专项测试」属实；新测试文件名无冲突。
- **sim/验证面**：sim_backend_runner.py:314-381 真 CwLoop + 真 mandate_v1 装配属实；strategy-work §4 可观测性声明、`cw_replay --diff` 豁免、验收线保全申报（.debug/progress 各迭代 criteria + math_proofs 索引无以补给选择为判据面的在册线）复核无反证；实机锚点①-⑤与行为申报①-⑤一一对应（④的帧内冲突见 R7-4）。
- **文档面**：25 号稿 `:3`（族清单恰 11 屏）/:11（差异要点）/:18（表行）/:3-4（拆分头注先例）；13 号稿 `:20`（行描述与实码不符属实）/:40（E4 目录行）/:11（OCR 未就绪纪律）；08 号稿 `:19`（E4 行 P42 component_demand/hoard_gaps + P40 变体②口径逐字；「待 derive」列保留与 08 §0 章程自洽）；16 号稿 `:74`（挂账在册、死引用 `cw_events.py:293` 与 `sim/checks/ledger.py:970/1035` 均实、替锚口径正确）；strategy-docs README §2（末篇 28）§3（kernel 存量 = 待迁）；三份画面文档锚点（supply.md `:12/:33/:40/:63/:80/:88`、currency_war_supply.md `:19/:37/:39/:57`、货币战争-补给.md `:32/:39`）全部实存且确为随批过期面；landing 3.3 grep 验收词表（25 号稿补给仅剩拆分头注 1 行）按现文可满足；flow/README.md:81 的 `decide_supply` 为 ABC 契约方法名指称、方法名保留后续约不失效，不属收口面。
- **跨批/承接面**：29 号稿编号占用声明（29 批 landing「新建 strategy-docs/29_invest_strategy_screen.md」）；两承接批「明确不解决」均登记补给为后续批（env 批 design:18、29 批 design:23）；29 批 landing:33 对本批的锚漂移交接申报与本批 §2.7 的重核义务互证成立（清单完整性缺口见 R7-2/R7-7）。
- **宪法/规范面**：宪法五（SupplyOption 留 kernel = 观察载荷契约五方消费面逐一核实；EQUIP_GENERIC_VALUE/equip_tier「本批仅消费不迁移」所有权申报与 00_framework §1.5 判据线一致）；宪法六（新画面文件 + 30 号稿一一对应；逐画面节奏 = 宪法明文，非逐件症状修补——同族半问不触发）；零调参（新判据零新增自由参数：star=1/count==2/left≥1 均游戏定义量；通用值表按 16 号稿在册处置降格 tier 内定序常数、表值零变化）；未证即退役（+10 隶属判据物理删除、无墓碑）；iteration-design 结构（§0-§2 齐、landing 阶段七件齐、README 模板合规、design/landing 无过程叙事、引用寿命合规——无代码或正本引 changes/ 的长期引用）；核三治本（§1 归层「分层语义 + 语义」成立；§2 迁移治所有权、改形治价值模型缺轴、刷新收窄治无质量条件闸，经验值表残留以在册处置显式申报并排期 E4 批——症状修法的战术权衡齐备）。
