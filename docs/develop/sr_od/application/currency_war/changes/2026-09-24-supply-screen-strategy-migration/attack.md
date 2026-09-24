# 设计对抗报告(2026-09-24 补给屏策略迁移与选卡改形)

> 审查对象 = 本目录 design.md / landing.md / README.md(草案态)。
> 判据源 = iteration-design.md §7 三核、strategy-work.md(§1 零调参/§3 证据档/§4 验证阶梯/§5 单帧锁/§6 对抗纪律)、宪法 00_framework.md/01_math_framework.md、math_proofs 索引(P40/P42/P97/P81 行及单篇)、项目 AGENTS.md。
> 纪律 = 数值/口径/引文/码点全部直调源文件复核(文中每个 文件:行号 均为审查时实读);篇内自洽与对齐宪法/游戏真值分开验;结论只看证据。

## 发现清单

### 发现 1(高)`gs.board` 容器引用错——凑星判据按稿不可实现
- **位置**:design.md:53(§2.3)
- **发现**:§2.3 判据写「`gs.board` + `gs.bench` 中该角色名 1★ 计数 == 2」。实码 `gs.board: Field[dict[str, int]]` = **上阵羁绊计数**(cw_game_state.py:2123,键 = 羁绊名如「持续伤害」,派生量挂 `_resync_board_delta`),容器内**无角色名、无星级**;按此引用读不出任何「该角色名 1★ 计数」。上阵单位真值在 front_row/back_row 行域 Unit(name+star,读口 `deployed_rows_of` cw_game_state.py:3648)+ 备战席 `bench_units_of`(:3656);现役同名同星计数单一源 = `cw_merge_simulate.same_star_count`(:427,bench∪deployed 全场域)。`gs.bench`(BenchView)一半可用,`gs.board` 一半是错容器——「值对标签错」重点错误类,且是 §2.3 核心判据的数据源规格。
- **修正方向**:数据源改为「deployed_rows_of(gs) 行域 + bench_units_of(gs)」或直接引用 `cw_merge_simulate.same_star_count` 现役同名同星计数谓词;§2.3 的「board∪bench」表述改为「上阵行域∪备战席」。

### 发现 2(高)装备级复用 `equip_tier` 未定义持有账输入——行为申报②与验收凭据④按稿不可实现
- **位置**:design.md:50(§2.2 第 3 级);landing.md:12(凭据④)
- **发现**:`equip_tier(name, *, key_equips, owned_spare, owned_total)`(cw_equip_value.py:163-189)的需求计数(tier 3 判定 `total_counts < keys.count`)与近兑现(tier 2)判定全部消费持有账。设计只指定了 `key_equips = target_comp.key_equips`,**未指定 owned_spare/owned_total 从哪来**。若实现者按缺省空账调用:`total_counts` 全 0 → 一切 key 成品恒 tier 3(需求永未满足)、近兑现恒不触发——「已持够数的重复成品不再高分」(§2.6 行为申报②、landing 凭据④)反向失效,重复成品照旧最高档。箱选卡同文件内有现成账源先例(flow.py:719-740:备用账 `gs.equips` + deployed/bench 穿戴账合成总账)。这是「实现者必须自行设计」的缺口,且漏拍即静默错误。
- **修正方向**:§2.2 明确两账来源(照 decide_box_card 同口径:owned_spare = `gs.equips` 现值,owned_total = spare + 行域/备战席穿戴账),或声明由 flow 接线注入。

### 发现 3(中)`target_comp = ist.target_comp` 引用错载体
- **位置**:design.md:62(§2.5)
- **发现**:`IntentionState`(kernel/cw_intention.py:189 起,字段全集:phase/locked_comp/p1_pair/lock_layer/lock_plane/lock_round/transition_pair/forced/weak_comp/demoted_endgame/evicted/pair_evicted/pair_drought/shop_supply_streak/p1_pair_frozen_obs/p1_pair_frozen 等)**没有 target_comp 字段**。该字段住 `StrategyState`(mandate_state.py:73「战略层目标阵容(方向刷新维护)」,读口 `strategy_state_of(session).target_comp`),flow 现役即读 `self.state.target_comp`(flow.py:549)。实现者按稿写 `ist.target_comp` 直接 AttributeError。
- **修正方向**:改为「`target_comp` = `self.state.target_comp`(mandate_state.py:73)」;locked_comp/demoted_endgame 保持 ist 同源不变。

### 发现 4(中)刷新闸辖域与「三级全空 ∧ 闸拒绝」帧的选卡语义未定死;§2.5 路径描述与实码机制不符
- **位置**:design.md:57(§2.4 闸条)、design.md:62(§2.5「重调一次决策按现行评分选卡」)
- **发现**:新 `decide` 签名(design.md:42-44)无 refresh_used 参。§2.4 把次数闸写进决策判据节但依据指向「**flow** 现役闸语义原样,flow.py:545-546」(flow 侧闸代码)。两种读法只活一种:(a) 闸留 flow → 闸拒绝帧重调 decide 仍返 `SupplyRefreshSuggestion`(纯函数同输入同输出,且该载体无 idx),flow 无卡可选,现行「闸全败→选卡」路径断裂;(b) 闸内嵌 decide(照 invest_env.decide 先例读 `gs.env_refresh_left`,invest_env.py:388-401)→ 自洽,但设计未写明,且「三级全空 ∧ 闸拒绝」帧的产出(= tier 0 内通用值 argmax 输入序先的落选卡)全文未申报。另 §2.5「刷新闸全败 → 重调一次决策按现行评分选卡」对现状的转述不准:实码重调只发生在 **op handler 双闸不一致面**(容器闸过而刷新锚点缺,cw_screen_supply_node.py:276-288;重调后仍建议刷新 = 零点击终结交回),「按评分选卡」的面是 flow 单次调用内 refresh_used=True 直选,不存在「重调后按评分选卡」。
- **修正方向**:§2.4 显式声明闸位置(建议:内嵌 decide,照 invest_env.decide 同构,gs.supply_refresh_left 现读 + None fail-closed)+ 闸拒绝帧落选出卡语义;§2.5 的现状路径描述按实码改写(或删去现状转述,只写新契约)。

### 发现 5(中)sim 可观测性申报的机制叙述错误——「决策面零接线」不成立
- **位置**:design.md:78(§2.6 sim 申报)、design.md:26(§1「sim 结构性不消费 decide_supply」)、design.md:80(验收线保全申报以「该画面 sim 不可见」为据)
- **发现**:「sim 不消费 decide_supply」仅对 `cw_sim_backend` 模块本身成立(后端不直调);但 sim 全程跑**真 CwLoop + 真 mandate_v1 策略**:harness 装配 SimBackend + 真 CwLoop + 真 CurrencyWarMatch(sr-od-test/test/harness/sim_backend_runner.py:314-381),画面身份走后端答口(cw_loop.py:1476 + cw_sim_ports.py:141-155),补给屏正常分发(cw_loop.py:1088-1092),op 观察改道 sim 生成器(cw_screen_supply_node.py:189),`:275` 真调 `match.strategy.decide_supply()`;sim 后端 SCREEN_SUPPLY = '货币战争-补给'(cw_sim_backend.py:172),补给节点呈现屏(:1250-1257)并消费 pick_supply/refresh 事件(:875-882、:913)。**行为变化在 sim 局中机械可达**。本批 sim 不可见的真实机制是占位分布:`supply_options` 每帧恒置恰一带钻槽(cw_sim_backend.py:573-585,diamond_slot 均匀)→ 新旧算法都恒选钻卡、刷新判据在两侧都永不触发 → 读数恰同。结论(不可作 A/B 判据)碰巧成立,申报机制错误;strategy-work §4 的可观测性声明要求准确分层陈述,且「验收线保全申报」引用了错误依据。若未来 sim supply_options 换真实分布,本批差异即 sim 可见——按现申报会漏验证。
- **修正方向**:申报改为真实机制(占位分布恒带钻 → 判据差异被第 1 级吞掉),验收线保全的依据同步改;并注明该盲区是占位分布造成、非结构性。

### 发现 6(中)文档面遗漏:16 号稿改形挂账行与 13 号稿 E4 目录行不在更新清单
- **位置**:design.md:82-87(§2.7)、landing.md:47-52(正本更新清单)
- **发现**:本批正是 16 号稿在册改形挂账(16_evaluation_tables_reassessment.md:74:「经验拟合形态 → 改形…数值降格定序常数,**随执行批落**;`check_equip_value_*` 相干性检查锁(sim/checks/ledger.py:970/1035)随改形重推」)的执行批,但 §2.7 与正本更新清单均无 16 号稿。落地后该行即成「挂账已落地仍写未落地」,且其引用 `cw_events.py:293` 与 `sim/checks/ledger.py:970/1035` 均为死引用(后者全仓 src+测试仓 grep 零命中,前者机器随本批删除);该行「带钻支配(零参数已就位)」与 §2.2「不是已证支配论证」的定性张力也将留存。同类:13_pick_family.md:40 事件面目录 E4 行(「选项价值 vs 目标线组件/成品需求」旧知识判据描述)同样过期,§2.7 只列了 13 号稿 §1 `decide_supply` 行(:20)。
- **修正方向**:正本更新清单增两条——16 号稿 :74(挂账销账 + 死引用清理 + 支配性定性与 30 号稿对齐)、13 号稿 :40(E4 目录行改指 30 号稿)。

### 发现 7(中)§2.6 删除面行号锚 583-647 覆盖了两个不可删对象,与 §2.1 自相矛盾
- **位置**:design.md:66(§2.6),对照 design.md:33(§2.1)
- **发现**:cw_events.py 583-647 区间内:SupplyOption(585-596,§2.1 明文「留 kernel」)、`_equip_value`(609-612,`cw_events.py:786` 的 planner 装备档回落打分仍在消费,删除即运行期 NameError)。删除项清单(decide_supply + SupplyPick + EventPick 该位)本身正确,但行号锚按「整段删除」执行必然破坏。这属「修订后全量同步复查:逐一核设计引用的每个符号/路径」卡点类。
- **修正方向**:锚改为「decide_supply 函数体(:616-647)+ SupplyPick(:599-605)+ 段落注释(:583)」,并补一句「`_equip_value` 与 SupplyOption 保留(:786 消费面 / 观察载荷契约)」。

### 发现 8(中)P1 配方锁帧行为未申报;「非过渡阵容」定性在该帧不成立
- **位置**:design.md:50(§2.2 第 3 级 key_equips 依据)、design.md:92(§2.8)、design.md:72-76(§2.6 行为变化申报)
- **发现**:P1 配方锁局 `locked_comp` 恒空(flow.py:327),`state.target_comp` = `pair_target_comp` 物化的**过渡配方伪 comp**(cw_intention.py:1123-1194,name='过渡配方·…',core_chars = 体系对成员,key_equips 恒空)。于是该帧:角色级不激活(locked_comp 空)、装备级 key_equips 空 → 全体 tier 0。这与 §2.2「target_comp……战略终局向载体,**非过渡阵容**」的定性直接冲突(P1 锁帧它就是过渡载体),§2.8「装备级在未锁线期继续提供终局向参考」在该帧也不成立(无 key 可参照)。行为本身可由设计规则机械推出(且与「不按过渡阵容选」裁定精神一致),但属未申报的行为形态,判读锚点(§2.6 申报 ①②③)未覆盖该帧。
- **修正方向**:§2.2/§2.6 补 P1 配方锁帧行为申报(角色级不激活 + 装备级全体 tier 0 = 退化为「钻或通用值」),或显式声明该帧按未锁口径;「非过渡阵容」措辞限定到「P2+ 方向机的终局向载体」。

### 发现 9(中)landing 3.1 验收凭据缺 §2.3 凑星 tiebreak 的锁项
- **位置**:landing.md:5(设计依据含 §2.3)、landing.md:10(完成判据)、landing.md:12(验收凭据①-⑥)
- **发现**:设计依据列了 §2.3,但完成判据只对照 §2.2/§2.4,凭据①-⑥ 无一锁「能凑星者先」(多钻帧角色候选内 ①凑星 ②装备比的 tiebreak 语义)。设计指定的行为无对应可验收判据 = 核一「landing 阶段与设计一致(判据可验收)」缺口;也违 strategy-work §5 锁的存在性纪律的精神(设计出处的行为应有其锁)。
- **修正方向**:凭据增一项(如「⑦同星差一格的角色候选中,能凑星者先于不凑星者」)或并入①的细分描述。

### 发现 10(低)§2.1 import 面枚举不实:「无外部类型 import」与「三方引用」均不准
- **位置**:design.md:34(§2.1)、design.md:33(§2.1)
- **发现**:测试仓 `test_cw_unified_action_4.py:27-33` 对 SupplyPick 有类型 import(来自 cw_events)——「全仓 import 面 = …无外部类型 import(2026-09-24 直调核实)」不成立(3.2 文件面「sr-od-test/ 内引用被删符号的旧锁」虽可兜住删除面,但本句作为直调核实结论是错的)。SupplyOption 消费方实为**四方**(obs 写端 cw_node_obs.py:21 / 容器 cw_game_state.py:113 / 测试 / sim 占位采样 cw_sim_backend.py:78),§2.1「三方引用」漏 sim。
- **修正方向**:枚举补全;「无外部类型 import」改为「src 仓内无外部类型 import,测试仓类型 import 见 test_cw_unified_action_4.py(随 3.2 删除)」。

### 发现 11(低)sim 引用行号锚偏移
- **位置**:design.md:26/58/78
- **发现**:`cw_sim_backend.py:566` 实际是 `box_options` 定义前空行(目标 `supply_options` 在 :573);`:890` 实际是 `_record_box_click` 内 return(目标 `'pick_supply'` 事件分派在 :913)。三处同错,值对标签错的锚点漂移形态。
- **修正方向**:锚改 :573 与 :913。

### 发现 12(低)注释指针收口清单不全
- **位置**:design.md:69(§2.6 注释指针收口)
- **发现**:除 cw_vocab.py:729/917 外,随本批失指的注释还有:cw_events.py:1(模块 docstring「补给(decide_supply)」)、cw_survey19_hooks.py:1-8(模块头「P8 补给重刷判据/三件」,删 supply_reroll_decision 后失指)、cw_pick_supply_action.py:37(「SupplyPick.refresh 决策」)、cw_screen_supply_node.py:8-14/242-245(旧评分语义叙述「按 target_comp.key_equips 契合 + 装备通用价值」「规则 2 全无钻+刷新剩余>0→刷新找钻」)、cw_node_obs.py:206(「decide_supply 建模残缺」)。末阶段「全仓复扫旧指针零残留」可兜底,但 §2.6 申报面应完整。
- **修正方向**:§2.6 清单补全上述各点(或显式声明「旧指针收口以末阶段全仓复扫为准,§2.6 只列已知点」)。

### 发现 13(低)「P40 变体②(免费重掷期权)」再解释与 P40 单篇定义不符
- **位置**:design.md:58(§2.4)、design.md:11(§0)
- **发现**:P40 变体② 实义 = 「概率事件:45% 概率免费」的付费刷新折价变体(p40-refresh-ev.md:105,c_eff=1.1),非「免费重掷期权」;08 号稿 E4 原文口径是「重刷期权挂 P40 变体②(**补给刷新免费口径同**,非 P81 辖域)」的类比挂账。设计的再解释偏离被引对象。
- **修正方向**:删「(免费重掷期权)」的自行再解释,保留「重刷期权挂 P40 变体②(08 E4 在册口径)」即可。

### 发现 14(低)`locked_comp` 字符串到 comp 的解析与漂移回落未声明
- **位置**:design.md:49(§2.2 第 2 级「locked_comp.core_chars ∪ shared_chars」)
- **发现**:`locked_comp` 是套名字符串(IntentionState.locked_comp,cw_intention.py:197),取 core_chars/shared_chars 须经 `get_comp` 解析;注册表漂移(解析失败)的回落形态设计未写。同文件先例 = box_card:get_comp 失败按未锁态 + 日志哨兵(flow.py:712-718)。
- **修正方向**:§2.2 补一句「locked_comp 经 get_comp 解析,失败按未锁口径 + 告警(照 decide_box_card 先例)」。

### 发现 15(低)宪法五存量链未申报:新策略文件长期消费 kernel 内评估表
- **位置**:design.md:50(§2.2)、design.md:91(§2.8)
- **发现**:`EQUIP_GENERIC_VALUE`(V4.4 meta 先验拟合表)与契合定序驻 kernel/cw_equip_value.py,按宪法五「kernel 内存量评分 = 待迁策略内容,迁移为在册义务」(00_framework.md:18)读作待迁策略层内容。本批新建策略文件把装备判据继续锚在该 kernel 内表上,设计处理了 decide_supply 的迁移却未申报这一依赖的所有权归属(哪怕只登记「消费既有共享机器,其迁移归在册义务」)。
- **修正方向**:§2.1 或 §2.8 补一句申报:EQUIP_GENERIC_VALUE/equip_tier 本体按宪法五为待迁策略内容,本批仅消费不迁移,迁移归在册义务。

### 发现 16(低)「同目录 encounter.py 先例」引用错位——encounter.py 非画面策略文件
- **位置**:design.md:31(§2.1)
- **发现**:mandate_v1/encounter.py 实为**已搁置让位**的遭遇分支选卡 EV 核历史件(docstring:「已搁置让位——现役遭遇选档 = kernel/cw_encounter_selection.py,本模块保留禁删」),不是宪法六意义的画面策略文件;遭遇屏决策本体现役仍在 kernel。以它为「一画面一策略文件」先例与实态不符(真先例只有 invest_env.py)。
- **修正方向**:先例只引 invest_env.py(28 号稿首批兑现),或改述「encounter.py 为同目录既有件、非迁移先例」。

## 已核对无误的面(抽样列举,均直调复核)

- 码点引用:cw_equip_value.py:36(表自注)/:163-189(equip_tier 档位语义);cw_events.py:616-647(decide_supply 只消费 equip/has_diamond)、:1003/:1007(EventPick 登记面)、:633-635(无钻必刷);cw_comps.py:102/:111(core_chars/shared_chars,transition_chars :112 未入名单 ✓);flow.py:516-518(invest_env 意向三参先例)、:545-546(闸 fail-closed 语义);mandate_state.py:73;cw_game_state.py:210(supply 域版本 2,TYPE_CHECKING 引用 ✓);cw_equipment_data.py:53(财富宝钻 effect 原文逐字 ✓,且 has_diamond 检测集 = {红钻,蓝钻,财富宝钻} 三钻,cw_node_obs.py:215——:53/:64-65 双依据覆盖检测集 ✓);cw_action_report/pick_supply.py:48(1★ 先验口径);cw_vocab.py:729/917;cw_survey19_hooks.py:46-56(唯一 import 点 = cw_events.py:551-552 只取 encounter_tier_score,src+测试仓零消费 ✓)。
- 机制语义:equip_tier 与 pick_equipment 的 tier 序/需求计数/近兑现口径;「3 同星合成」规则(cw_merge_simulate.py:337 同名同星 ≥3)支持 §2.3 的 2×2★+1×1★ 不入判据;line_value 降格帧按未锁口径(line_value.py:16/62)与 §2.2 一致;kernel→strategies 零 import 现状成立;mandate_v1/invest_env.py 纯值出口形态与闸内嵌先例。
- 文档面:25 号稿族清单恰 11 屏、:3-4 拆分头注先例;13 号稿 :11 OCR 未就绪纪律、:20 decide_supply 行描述与实码不符(§1 症状 6 属实)、:18 decide_invest_env 改指先例;08 号稿 :19 E4 行(「component_demand/hoard_gaps/P40 变体②」转述与原文一致;P42 单篇确有 `component_demand`/`hoard_gaps`,🔴 待标定 = λ 流/partner 到位率,与「P42 数值标定待落地」表述一致);16 号稿 :74 在册改形挂账属实(其遗漏见发现 6);strategy-docs README §2 分篇表 28 为末篇、29 号稿确被投资策略批占用(invest-strategy design.md:22)、30 空闲;两份承接迭代 design §1 均登记补给为后续批(env 批 :18、投资策略批 :23)✓;P40/P42/P97/P81 索引行与本批涉猎面无被违反的判据(本批不消费 P81 判据、不声称期望最优,数学挂账走向与 08 E4 一致)。
- 规范面:landing 各阶段七件齐、无详设单文档方案合法(§0 申报)、README 符合模板、无过程叙事、字典序零自由参数与 §2.8 取舍自洽、16 号稿「数值降格定序常数」处置与 strategy-work §1 定序常数形态相容、逐画面迁移节奏 = 宪法六明文(非症状补丁,核三通过)。

## 结论

发现 16 项:高 2、中 7、低 7。高两项(发现 1/2)直接阻断 §2.3/§2.2 按稿实现或使其自declared行为修复失效,须先修设计再定稿;中七项涉及删除面自洽、闸辖域、sim 申报机制、正本清单完整性与验收判据缺口,定稿前应逐项消化;低七项为引用精度与申报完整性。零和稀泥:每项均给出实证位置与修正方向。
