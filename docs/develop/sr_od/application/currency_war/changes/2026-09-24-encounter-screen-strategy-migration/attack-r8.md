# 遭遇迁移设计 对抗审查报告(第八轮)

> 审查对象:design.md / landing.md / README.md(三件全读)。判据源全部直调:00/01 号稿、04 号稿 §7 裁定表第 9 行、screens/op-layer.md §1.4、proofs/p64 单篇与 math_proofs 索引 P15/P26/P85 行、先例两件(supply 30 号稿 / invest-env)、现役代码逐符号、全仓 grep。行号以本报告撰写时工作区现态为准。

## 发现清单

### R8-F1 [严重度:高] `D_ENC_VARIANT` 消费面盘点遗漏 `cw_screen_battle_wait.py`,物理删除将打断结算行入环保留面;§2.8「cw_battle_wait 遭遇观测面零改动」失实

- 位置:design §2.3(退役四槽)/§2.7(kernel 删除面)/§2.8(其余 op 层零改动);landing 3.2(文件面、零残留清单)
- 发现:设计申报 `D_ENC_VARIANT` 物理删除且 kernel 无标定面残留,同时申报「其余 op/上报层(…、cw_battle_wait 遭遇观测面)零改动」。直调证伪:`operations/cw_screen/cw_screen_battle_wait.py:303-306` 在 `_cw_selection_write` 内 `from …kernel.cw_encounter_selection import (D_ENC_VARIANT, record_settlement_row)`,`:319-323` 按 `D_ENC_VARIANT == "i"/"ii"` 双态装填遭遇行 `difficulty_node`。全 src 词边界 grep:`D_ENC_VARIANT` 生产消费仅两处——`cw_encounter_selection.py` 本体与 `cw_screen_battle_wait.py`;测试仓零引用。该 import 在方法体内,槽物理删除后**每场结算行入环即 ImportError**,直接打断裁定 9 授权的结算观测持久化(本批自己的 kernel 保留面)。landing 3.2 文件面未列 `cw_screen_battle_wait.py`;其零残留 grep ② 网虽含 `D_ENC_VARIANT`(会拦住),但设计未给出该消费点的处置语义,实现者撞网后无答案可依(停手令回路由)。另注:现役 `D_ENC_VARIANT=None` 下遭遇行 `difficulty_node` 恒装 None(`:319-323` 两分支均不中),即现网行为 = 普战行 observation 直装、遭遇行恒 None——退化目标形态有现成定义,设计漏写。
- 修正方向:①§2.7 增列该消费点处置:装填双态退化为定谳前形态(普战行 observation 直装不变、遭遇行 `difficulty_node` 恒 None——与现 None 拨盘行为逐位一致),或显式论证该装填位改读新归属(若定谳拨盘随迁策略层,须给出 op 层取值通道,注意决策控制分层铁律);②§2.8 撤回「cw_battle_wait 零改动」申报,改为「结算行装填双态收窄一处」;③landing 3.2 文件面增列 `operations/cw_screen/cw_screen_battle_wait.py`,测试面补结算行装填锁(普战行 diff 有值/遭遇行 diff=None)。

### R8-F2 [严重度:中] 章程缺口申报误述 01 §6 原文——章程并非「未预见」闸门量,而是明文把「数值大小参与方向/闸门判断」的量划归【推】/【拟】纪律

- 位置:design §2.2 形态申报段(「章程缺口申报」句)
- 发现:设计称「01 §6【拍】字面辖域 =『登记即立场、分差即偏好强度的加法立场值』,**未预见**闸门位离散立场值」。直调 01_math_framework.md §6(line 168)原文:「【拍】禁用于伪装经验拟合——**凡『数值大小参与方向/闸门判断』的量归【推】/【拟】纪律**,【拍】只承载『登记即立场、分差即偏好强度的加法立场值』……」。即章程对闸门量**有预见且有显式归属**([拟]),不是辖域空洞。按现行章程,cap=2 属【拟】纪律辖域(其三要素:挂账登记 + CI 方向不变扫描 + 标定义务),而 cap 无可观测对象可估——真正的修订理由应是「该类偏好型闸门值不满足【拟】的观测信念语义,属偏好登记」,这是对章程显式条款的** supersession 申报**,不是补盲区。
- 修正方向:申报改写为引用原文的 supersession 形态:章程 line 168 明文将闸门量划归【推】/【拟】;本批申报该归属对「无可观测对象的偏好型闸门值」不适用(无 CI 语义可承载),提请 §6 修订重划辖域,裁定门不变。修订提案的论证义务(为何【拟】三要素对此类失义)随之显式化。

### R8-F3 [严重度:中] 裁定未过的退化形态未定义且自相矛盾;landing 3.1 无裁定前置,存在「章程真空窗落码」路径

- 位置:design §2.2(两闸绑定段、决策序 step 4/6);landing 3.1(范围、依赖:无、完成判据)
- 发现:①设计自缚「修订未裁或未过 = cap 与偏好序不落码激活,遭遇选档维持 fail 向最低档(现役暗装等价保守形态)」。但按 §2.2 决策序推演:去掉边缘 cap=2 后,κ_S 足量帧仍可及 t≤4(足量 cap=6 系「档位值域上界」非【拍】申报项)、其五/六照走经验层、主序照选最高——**推不出「恒最低档」**;若反向把「无 cap」解释为可及集恒空,则刷新阀(`可及集空 ∧ left≥1`)照建议刷——也不等于暗装零刷新。两条实现路径都到不了申报的退化形态,该分支不可施工。②landing 3.1 依赖 = 「无」,但其范围含「边缘 cap 立场常量(【拍】登记表落点)」、完成判据的单帧锁覆盖 §2.12 锚点 2(边缘 cap)与锚点 5(tiebreak 序)——即**在用户裁定完成前落码并锁定两项【拍】值**,与设计自己的「禁章程真空窗落码」相抵;3.2 把「裁定点 1 结论」列为依赖,§2.2 同一裁决门(章程修订 + 两项值过目)却未列为任何阶段依赖,不对称。
- 修正方向:①显式定义裁定未过时的落码形态(建议:立场常量区留位 + 判据侧恒 fail 向短路,即 cap/偏好序槽位 None 语义 = 边缘态可及集空 ∧ tiebreak 全落同档,并同步关阀;或该分支 = 整批缓发,二选一写死);②landing 3.1 依赖增列「§2.2 同一裁决门完成(过目记录在册)」,或 3.1 完成判据按裁定分支双态写明。

### R8-F4 [严重度:中] 补给孪生面已落地即在产带病(零点击无界循环),本批仅无期限挂账;跨件半问未升架构级条款,修后两屏行为分叉

- 位置:design §2.5/§2.11(补给孪生面挂账);landing 3.2 落地检查项
- 发现:同款「建议刷 ∧ 锚读缺 → 重调仍 Suggestion → 零点击 round_success 交回」面在**已落地的补给屏在产存在**:`cw_screen_supply_node.py:284-291` 零点击终结交回(30 号稿已入库,`supply.decide` 可返 Suggestion);外循环无防护已由设计自己定谳(`cw_loop.py:824-836`:round_success = ok → `op_fail_redispatch_tick(…, True)` 清零连续 fail 窗)。触发面 = 容器 `*_refresh_left` 读缺跳写残留旧值 + 当帧锚读缺(同一读链失败但容器留旧值),窄但后果为卡死一条龙级。设计在遭遇屏落 `round_fail` 防线、补给屏只挂账「归补给域后续批」,无 owner 无期限;修完后全域两屏同形分支行为分叉(遭遇有界/补给无界),判读者需记两套语义。AGENTS.local 跨件半问:同族修法第 2 件出现,根同(op 层重调分支的零点击终结对外循环无界)——治本形态是行为规范条款,不是逐屏补丁。
- 修正方向:至少二选一:①把「刷新建议 ∧ 锚读缺 → round_fail 交回(计入重派上限)」升为 `screens/op-layer.md` §1.4 全域行为规范条款(与「刷新闸 = 剩余语义观察真值」同位),本批落遭遇屏,补给屏随最小批即改(一处行为改动,不属画面迁移、不违宪法六节奏);②保留挂账但登记 owner + 期限(「一个对局周期未决即回炉」,同 01 §6 三要素 3 口径)并写入 31 号稿挂账节。

### R8-F5 [严重度:低] P3 行为面申报机制失实——环跨位面累积下 P3 遭遇帧窗口非「不足」而是被 P2 普战行填满,方向未知非保守

- 位置:design §2.2(窗口候选论证末段「P3 结构未在册…失败方向保守」)
- 发现:设计称 P3「行为面按『窗口不足 → 保守退化』承担,失败方向保守」。直调:`cw_encounter_selection.py:162-164` `last_normal_battles` 全环过滤 `node_type == '普通战斗'`,**无位面过滤**;环生命周期 = 局、跨位面累积(`:128-133` docstring、设计 §2.2 自己的表述)。P1+P2 打完后环内 ≥5 个普战行,故 P3 任一遭遇帧(若存在)窗口 = P2 末两场普战行,κ_S 评在**跨位面证据**上——正是设计否决候选 B 的同一理由(「位面间难度结构不同,迁移适用性未经论证」)。同理「现役普战窗口无此问题」只在 P1→P2 成立(P2 唯一遭遇决策点 r5 前已有本位面两场普战);P2→P3 不成立。P3 遭遇节点存在性未证实(7 局进 P3 仅观测 1-2 普战节点),实际暴露面窄,故低。
- 修正方向:改报为如实形态:「P3 遭遇帧(存在性未证)窗口由 P2 普战行填充,κ_S 评于未经论证的跨位面证据上,方向未知——采齐前按未知承担」;变体触发器已有「战争边疆 P3 采齐运行」,可加注「P3 提前遭遇帧的跨位面窗口风险」。

### R8-F6 [严重度:低] 「档位↑⇒奖励价值↑」的旁证引据失准——competitors.md 节点表行无奖励随档信息

- 位置:design §2.2 决策序 step 6(「M13 competitors 节点表旁证」)
- 发现:直调 `docs/game/currency_war/data/competitors.md:123` 节点表遭遇行 = 「A8 常比 BOSS 凶;可刷新 1 次重置分支难度/奖励;阵容未成型选最低难度」——无任何奖励-难度关系记载;`currency_war_encounter.md` 侧真实证据 = 单帧 fixture(左卡难度1+金币×2 / 右卡难度4+随机4费角色×3,line 80)+ 定性 prose「右卡通常难度高、奖励更好」(line 31/43)。采样验证挂账已在(31 号稿),但「旁证」标签把单帧+定性句拔高成两源旁证,依据标注强度失真(iteration-design 硬规则 1 卡点)。
- 修正方向:依据改为「游戏原文『难度越高敌人越强大』+ currency_war_encounter.md 单帧方向性观察(定性)」,competitors 引据撤除或注明「无奖励随档记载」;挂账义务不变。

### R8-F7 [严重度:低] 「曾记的…经查不存在」勘误叙事入设计正文(写作硬规则 3 边缘)

- 位置:design §1.1(历史 EV 核条)、§2.10 裁定点 1 推荐理由
- 发现:两处「曾记的『测试仓 EV 核纯函数锁』经查不存在/(直调核实,曾记的…不存在)」——对既往记录的勘误过程叙事。事实本体(测试仓无 EV 核锁;全仓双零消费)已独立直调核实成立(本报告复核:`decide_encounter_ev` src 零调用方、测试仓 `mandate_v1.encounter`/`ENCOUNTER_DSTAT_MAP`/`encounter_ev` 零引用),勘误过程不进正文(iteration-design 硬规则 3:过程住对抗报告与账本)。
- 修正方向:改写为纯现状事实句:「测试仓无 EV 核行为锁(src+测试仓双零消费,直调核实)」,删「曾记的」指称。

## 零发现面申报(实际攻击过且无实质发现的面)

- **宪法/章程原文核对**:00_framework §1 六条(宪法五判据线/宪法六迁移节奏与共用模块条款逐字)、01 §6【拍】三要件与禁域条款、01 §8 位面参数化不变量——设计引用与原文一致(除 F2 的转述面)。
- **授权与裁定链**:04 号稿 §7 裁定表第 9 行逐字(授权对象 = 结算观测读数作遭遇决策输入 + GameState 持久化、环深 10、「判据正本」系依据列载体登记——设计 §2.2 对该行「不构成判据结构授权」的读法与原文相符);op-layer.md §1.4 刷新剩余语义(None = 未观察、节点屏闸 None = 拒刷)与设计 §2.2/§2.5 闸内嵌一致。
- **已证命题**:P64 单篇辖域(静态 `dict[旗牌→stat]`、B/q/s/m 自由项、G_gold 金额侧、点亮前置链①②③)与设计引申申报的边界声明相符;math_proofs 索引 P15(boss 26.79 [24.25,29.23] / 普战 10.45)、P26(待证明,Δp_prep+L_node 双挂账)、P85(D_N={遭遇,boss}、A/B 分键候裁)行——设计 §1/§2.2/§2.12 引用逐项对得上。
- **现役暗装核直调**:六标定槽全 None、门序(F_MIN→G_BASE→bar 双定谳→D_ENC_VARIANT→Δ_t)、`_kappa_state` 三态表逐位(含删失优先/fill 不激活分支)、cap 2/6 与过滤顺序(cap 在前,边缘态 t≥3 全排除含五/六)、tiebreak `(档, idx)` 序、`_lowest_idx` 并列取先读、三因词刷新阀、reason 串格式——设计 §2.2「与现役核同构,门序收窄」申报与代码逐位相符。
- **三核架构与双零消费**:基类 flow.decide_encounter → cw_events 旧核(flow.py:594-609,含 refresh_used 预计算 :602)、bridge 覆写 → cw_encounter_selection(bridge.py:252-285,含自带离屏守卫)、EV 核 mandate_v1/encounter.py(`decide_ev` 零生产调用、测试仓零引用、「纯函数锁」不存在);bridge 仅覆写 decide_prep_screen/decide_encounter/decide_shop_screen——「删覆写后 bridge 只覆写营业面」申报成立。
- **动作链解耦**:CwActionPickEncounterOp 静态入参 = 词表动作、`report_action_pick_encounter_param(param: Any)` 鸭子取 idx——生产契约与 EncounterPick 无耦合;测试替身仅 test_cw_unified_action_4.py(:28/:259/:278,行号精确)。
- **删除面/收口清单完备性**(除 F1 外):EncounterPick 全部 src 消费点、EVENT_PICK_TYPES/EventPick 运行时构造位、cw_vocab 两处「替代 EncounterPick」(:715/:906)、flow.py:656/793/807 三符号锚、apply_calibration/reset_calibration/selection_state_of/game_start_reset/REWARD_TIER_LAST 零外部引用(全仓 grep 定谳)、注释指针收口 15 处逐一在实址核到、测试面清单(claim/record 保留符号 import 零改动、重调行为锁改写对象 = test_cw_obs_arch_event_screens.py:387-403)与实址一致。
- **kernel 保留面**:SettlementRing/EncounterLog/_RingRow/SETTLEMENT_RING_DEPTH(=10)、record_settlement_row 单一写端(cw_game_state.py:123-126 与 cw_op_settle_confirm.py:98 的消费均为保留符号)、claim_encounter_reward 兑现回调、gs.enemy_difficulty 容器——宪法五③非打分基建归层成立。
- **refresh 阀-外循环交互**:cw_loop T-266 计数语义(只计连续 fail、零点击 round_success 清零窗,cw_loop.py:824-836/852-868)与设计 §2.5 定谳逐位一致;遭遇重调分支现态(cw_screen_encounter.py:180-195 零点击 round_success)与「由死转活」申报一致;防线条件(重调仍 Suggestion ∧ 锚读缺)与唯一可达失配子态吻合。
- **sim 面**:结算腿零 `record_settlement_row` 调用(sim 目录 grep 零命中)、`ENCOUNTER_TIER_COUNT=4` 与占位文本「金+20(占位,…)」(cw_sim_backend.py:488/491/536-539)按 reward_tier 语义直推落末档——§2.12 sim 盲区申报成立。
- **生成契约**:tools/cw/gen_equip_registry.py:354-355 整文件 write_text、生成文件头「勿手改」;三钻无单一标志字段可派生(category='特殊' 17 件、official_category 仅财富宝钻带 '宝钻'、名含'钻'有钻头类误命中)——不迁 data/ 的理由成立;kernel/cw_obs_core.py 为手维护读数域模块,宿主选择与 obs→kernel 既有先例(cw_node_obs.py:23 已 import kernel.cw_obs_core)一致。
- **文档面**:25 号稿头注 9 项含退役删除注记(8 活屏)与 §2 表行「装备」残留、13 号稿 decide_encounter 行「双轨」漂移(且未提现役暗装核,漂移比设计申报的还多一层)、08 E3 行、strategy-docs/README.md「18-30」、04 裁定 9 行「判据正本」指针、screens/encounter.md 决策委托句与刷新闸叙述句、docs/game/screens/currency_war_encounter.md 算法描述句——设计 §1.5/§2.9 收口对象全部实址核到。
- **玩法知识面**:combat.md §3「遭遇奖励 = 伤害进度达标制非清场制」(killed=True 蕴含达标的经验层方向安全论证成立)、economy.md §10.2 P2 行双遭遇(r3/r5,1 帧待复核)与 cw_node_schedule(P1 supply@r5/encounter@r7、P2 supply@r3/encounter@r5,42 局零反例/7 局对照)两源冲突如实登记;§2.12 锚 6 的 P1 r7 窗口 = r4/r6 与真值表吻合;跨位面窗口示例(P2 r5 帧 = P1 遭遇行 + P2 r4 普战行)与环语义逐位推演一致。
- **先例对照**:30 号稿 §1 承接登记、纯值出口/闸内嵌/词表收口/EVENT_PICK_TYPES 摘位同款处理、补给批 §2.7 的 survey19 处置与本批 §2.11 现态申报(supply_reroll_decision 已删、剩余两符号)一致。
- **治本核验(核三)**:§1 归层成立(三核并存 = 宪法五所有权层;暗装门粒度 = 表示层);§2 主体修法为根因层处置(单一源收敛 + 门收窄 + 真值归位 kernel),非症状补丁——保留面与删除面的判据线划分(「换一套策略实现会不会要不同的值/序」)逐项过检无归层错误;EV 核退役建议符合「未证即退役」通则。存疑面已列为 F4(跨件半问未升级)与 F5(P3 申报失实)。
- **规范遵循(核二)**:iteration-design 四节齐、landing 阶段七件齐、末阶段正本更新在册、README 索引态、依据就地标注总体密度合格(例外 = F2/F5/F6 各自注明);「分层语义」归层措辞与 30 号稿先例同款,不作发现。
