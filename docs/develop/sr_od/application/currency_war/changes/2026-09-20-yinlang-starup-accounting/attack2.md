# 设计对抗审查报告——银狼升星记账迭代（第二轮核一·无前提攻击）

- **审查对象**：`design.md`（银狼升星记账迭代设计·总纲，单文档方案，状态：草案，已按第一轮 attack.md 八条发现修订）
- **审查标准**：`docs/develop/harness/iteration-design.md` §5 写作硬规则四条、§7 核一（无前提攻击：符号/路径/行号全量核验、试读、依据标注逐条攻、边界完整性）+ §7 核三（治本）
- **方法**：只读核验。A 部分对照 attack.md 八条逐条核修订是否真落地、修得对不对、有无修出新问题；B 部分全新角度无前提攻击（不锚定第一轮）。设计引用的符号/路径/行号逐一对照代码与文档现值；关键主张对照权威源原文；以实现者视角逐节试读「凭这份能开工吗」。
- **与第一轮的关系**：第一轮八条只作核对输入，本轮发现均为全新检出或修订引入。

---

## A. 第一轮八条修订核验

| # | 第一轮发现 | 结论 | 核验记录 |
|---|---|---|---|
| F1 | 同名即同档定谳标注与权威源冲突（待实测 vs 定谳） | **落地**（带一条残余注记，见下） | 修订后 §1.2（design.md:58-62）把记录处改指 `changes/2026-09-18-yinlang-exclusive-loop/design.md` §2.0。核该处原文（:60）：「定谳 = **容器内费用档不同时存在**（升星选择升费后商店只出新费用档、赠送单位也只给该费用档，同名即同档；口述·权威 2026-09-18）」——**引文链闭合**：被引处逐字承载口径本体，且自带口述出处，不再假手 equipment_mechanics。同时 §1.2 如实申报「游戏侧正本未清偿」（equipment_mechanics.md §7:162-163 确仍在册待实测行，本轮复核属实），并把清偿列入正本更新清单——待实测与定谳的矛盾不再被掩盖而是被显式承认 + 排期。 |
| F2 | 观察调用点作用域无 gs，穿线与回退未定 | **落地**（但新依据标注失真 → 见 B-G2） | §2.3 补了穿线定点（design.md:176-179）：`game_state_from_ctx(ctx)` + None → 现役 `ch.cost` 兜底。核锚：`game_state_from_ctx` 在库（cw_game_state.py:1133-1145，异常/无局安全返 None ✓）；`test_cw_game_state.py:712-716` 桩对齐注释与桩真实在册 ✓。机制可行、回退语义明确，试读可开工。唯「观察管线现役取口」一语与代码现值不符（详见 G2），依据标注本身需要修。 |
| F3 | sell_refund 行号差一行 | **落地** | design.md:93 现引 `cw_economy.py::sell_refund:128`——实测 def 在 :128 ✓；`bench_char_cost:147` 不变仍准 ✓。 |
| F4 | 「44 读点」无出处锚 | **落地** | §1.2 改为「会话内 grep 清点，清点工件未入库；家族结构化以代表锚可复核」（design.md:69-77）。四族 12 个代表锚逐一核对全部命中：账实结算族 sell_bench.py:100 / sell_deployed.py:66 / cw_effect_inventory.py:797 / telemetry/schema.py:186-187 ✓；估值概率族 cw_intention.py:386（CHARACTERS 查表）✓ / mandate_v1/shop.py:314（卡费口径 docstring 段）✓ / vopt.py:94（DISTINCT_CARDS_PER_COST[cost]）✓；sim 池族 cw_sim_pool.py:43（POOL_COPIES_PER_CARD.get(ch.cost)）✓（:108 在 drawable_names 函数体内 ✓）；静态画像族 cw_comps.py:507（cost<=2）✓ / cw_line_defs.py:102（cost==1）✓ / cw_win_features.py:99（total_cost += ch.cost）✓。申报口径诚实（未入库 + 代表锚），可对账。 |
| F5 | §2.5「现档」读源未点名 | **落地** | design.md:196 显式「现档 = `effective_cost(gs, '银狼LV.999')`，§2.7 唯一读口」✓。deploy_move.py 的上报函数自带 gs 形参（deploy_move.py:52），读口在作用域内，可实现。 |
| F6 | 升费腿写档两个未闭合边界 | **落地** | ①时序已定点：变换落行后、`merge_cascade_write` 前（design.md:148-149），且声明「档行与级联写域不相交」——行为无差、行序防分叉，与现码插入点（cw_screen_yinlang.py:405-414 变换行 / :415 级联）严丝合缝；②现档=5 防护已定义：不写变换不写档 + 留证行 kind=`planner_upgrade_tier_ceiling`（design.md:152-155），越界写不复存在。与 §2.5 deploy 腿口径（design.md:196-199）自洽：planner 侧档 5 走 upgrade 腿 = 机制不可达（gameplay/currency_war.md:77「5费升 2 星两选项都是装备」）故按异常留证；deploy 侧 3★ 档 5 上场可达属常态故恒等搬运无留证行——不对称有机制依据，且 §2.5 标注 [机制推断·实机候证]。残余自由度：§2.5 未定点其档行相对级联的先后（§2.2 已声明写域不相交，仅遥测行序自由度，不构成卡点）。 |
| F7 | 测试迁移面申报不完整 | **部分落地**（残留 → 见 B-G4） | §2.2 申报面（design.md:165-168）覆盖了 landing 直调迁移（实测 `apply_pick_planner_landing` 直调恰 9 处，「8+」相符 ✓）与 §2.3/§2.4 零消费申报（全测试仓 grep `resolve_cost_star`/`CARD_TEXT_Y` 零命中 ✓，属实）。但 §2.5 上阵变换窗三测（test_cw_yinlang_phase32.py:325-385）的断言面复核仍未申报，另有两个新写端零新增测试申报——详见 G4。 |
| F8 | 未注册名→0 口径归属模糊 | **落地** | §2.1（design.md:128-130）改按语义陈述「无费用语义，禁用于金额计算」，并显式声明与并排 `bench_char_cost` 未知→3 的分野（实测 :155 未知→3 ✓）+ docstring 落点。歧义消除。附带核验：该边界与 §2.3 自洽——调用点（cw_observation.py:1987-1988）在 `ch is not None` 分支内，未注册名走 :1997-2002 徽章直读分支不经 resolve_cost_star，「未注册→0」在该调用点不可达；且 resolve_cost_star 本身有 roster_cost<=0 守卫（:1817），双保险无除零风险。 |

**A 部分附带发现（修订后全量同步复查产物，非 design.md 正文问题）**：`README.md:11-12` 已预记「核一 8 条发现已全量修订……候定稿」「设计对抗:收敛」——本轮攻击在审中且下文有实质发现，「收敛」状态超前落笔。按 iteration-design §6「带开放问题的定稿不存在」，本轮报告落定后 README 进度行应回改（收敛判定以攻击报告为准）。

---

## B. 全新发现

**G1. [major] | design.md §2.3/§2.2 | 「badge=8 → 2★/8费」两处用例违反 {1,3,9} 倍数体系，与同节自述自相矛盾；按其申报落笔的新增测试将锁一个错误期望。**
§2.3 效果行（design.md:180）同一名子里先写「badge=8 → 2★/8费 ✓」、后写「倍数 ∉ {1,3,9} 的 roster_fallback 分支保留」——前半句按「星级 = 读数 ÷ 档」的倍数即星（{1,2,3}）口径心算，后半句是代码在册的真体系。真体系（代码现值）：`_SHOP_COST_MULT_TO_STAR = {1:1, 3:2, 9:3}`（cw_observation.py:1677），2★ 费用 = 基准 ×3（cw_vocab.py:145、cw_economy.py:48 `_SELL_MULT {1:1,2:3,3:9,4:27}` 同口径）。按此，badge=8/档=4 → 8÷4=2 ∉ {1,3,9} → 修复后行为 = roster_fallback 记 **4费1★**，不是 2★/8费；4费 2★ 的徽章真值 = **12**。§2.2 申报的新增纯函数用例（design.md:168「badge=8/档=4→2★」）照抄该错值：实现者写出的断言 `resolve_cost_star(8, 4) == (8, 2, 'badge')` 对修复后实现必红；按测试纪律停下核对时会发现是设计给的期望值错了。§1.1-4 的症状描述（badge=4÷3 不整除→记 3费1★）经核是对的，错的只是修复后示例与测试申报两处。
**证据**：design.md:180、:168；cw_observation.py:1677、:1817-1823；cw_vocab.py:145；cw_economy.py:48。
**修正方向**：两处数字改 `badge=12/档=4→2★/12费`（1★ 侧 badge=4 用例正确保留）；顺手在 §2.3 把倍数体系一句写全（倍数 = 3^(星级−1) ∈ {1,3,9}），防实现者再犯同型心算。

**G2. [minor] | design.md §2.3 | 「观察管线现役取口」依据标注失真：`game_state_from_ctx` 的现役消费面是动作 op 写端，观察侧零消费；所引「桩对齐先例」实为未选方案的代价注记。**
全 src grep `game_state_from_ctx`：53 处消费全部位于动作 op/动作链（operations/cw_op/*、prep_actions.py:466、operations/cw_loop.py:982），**obs/ 目录零命中**；函数 docstring 自我声明「动作 op 写入点的统一供给口(R2)」（cw_game_state.py:1136）。观察管线的同族现役取口是 `game_state_of(session)`（cw_observation.py:550-555、:2415、:2481、:2552）。另：所引 test_cw_game_state.py:712-716 的桩对齐注释记录的是 `read_shop_cards` **扩签名**时的测试对齐成本——那是 F2 讨论中未获选的扩参方案的注记，本设计最终选了不改签名的内部穿线，该先例与所选方案无涉。机制本身可行（obs 导 kernel 无方向问题，None 回退闭环），纯依据标注失真——hard rule 1 的攻击面本体：下游会据「现役取口」误判 obs 侧已有同款先例。
**修正方向**：§2.3 括注改为「动作报告写端统一供给口（cw_game_state.py:1136 docstring 自declared；obs 侧首例，同族现役形态 = 同文件 game_state_of(session) 系）；测试零改面 = 桩不扩签名（现役桩 test_cw_game_state.py:712-716 无需对齐）」。顺带：:179「该路径本就落 roster_fallback 留证」不精确（None-gs 兜底下 badge 命中 1/3/9 仍落 'badge'），可顺手改为「行为与迁移前逐位一致」。

**G3. [minor] | design.md §2.2 | 落地相调用的 `param` 实参来源未交代；leg 载荷挂画面 op 实例字段、op 重建即丢的形态设计零申报——「应用一次」契约存在静默零应用边角。**
正常路径来源链闭合，先说清：发射相 leg_type/norm_item 经 env 透传（cw_overlay_pick_action.py:409-415），落地相消费 `self._pending_leg`（cw_screen_yinlang.py:118-122 存、:199-206 消费）——发射与落地同在一个 `CwScreenYinLang` 实例的 round_wait 循环内，链闭合，迁移不破。但两个试读缺口：①新签名 `report_action_pick_planner_param(gs, param, sig, *, leg_type, norm_item, evidence)` 的 `param` 为必填位参，落地调用点（重入裁决出口）手里只有 `(leg_type, norm_item)` 二元组——pick 参数（idx/reason）未随 `_pending_leg` 持久化，:160「改调 report_action_pick_planner_param(..., evidence=...)」的省略号没回答 param 传什么，实现者须自行拍板（改存三元组/现构造/传 None）。②载荷的宿主是画面 op 实例字段：若确认已发但 op 在 overlay 关闭前死亡（节点重试预算耗尽/看门狗），重建实例 `_confirm_pending=False`、`_pending_leg=None`，落地证据到达时 :201 的 `_leg is not None and _leg[0]` 守卫静默跳过——证据到了、载荷没了、**零应用且零留证行**。该形态现役已存在、迁移原样继承，但设计的落地相契约写的是「应用一次」，对「零应用」边角只字未提。
**修正方向**：§2.2 补两句——落地调用 param 实参来源（建议 `_pending_leg` 扩为三元组携带 pick 参数，一句话定点）；evidence 到达而 `_pending_leg` 为空 = 留证行（新 kind，如 `planner_landing_payload_lost`）+ 申报该形态为已知边界（或挂账）。

**G4. [minor] | design.md §2.2 | 测试迁移申报残留三块：§2.5 三测断言面、zero_writes 导入面、两个新写端的随批新测试。**
F7 修订只落了 §2.2 侧。残留：①§2.5 落地后 deploy 变换窗多一条档行写（evidence=`deploy_upgrade_tier`），三测（test_cw_yinlang_phase32.py:325-385，断言 rows_sink 留证行/落场星级/级联推演）需逐条复核——本轮预演：三测现有断言在加档行后仍应通过（档行是普通 write_logic，不进留证 sink；无写序断言），但三测恰是新行为的最自然断言宿主，申报缺失会让 §2.5 阶段的测试义务无出处；②zero_writes 函数删除后测试导入面 :55-57（`from ...zero_writes import report_action_pick_planner_param`）必断，需改指 pick_planner；两相对照测试 :292-320 同文件随迁——申报面未点名；③§2.2 的 `planner_upgrade_tier` 写端与 §2.5 的 `deploy_upgrade_tier` 写端是本批仅有的两个新容器行为，随批零新增测试申报（AGENTS §10.1：新功能测试随功能写，锁设计约定）。已有 8 处 landing 直调测试迁移后断言全部不受影响（本轮逐条预演，见 A/F7 行），此点可如实补入零影响申报。
**修正方向**：§2.2 申报面拆齐四处（§2.2 迁移 + 导入改指；§2.5 三测复核 + 档行断言；§2.3 新增 resolve_cost_star 用例——已申报；§2.4 零影响——已申报），并把两个新写端的随批测试点名。

**G5. [minor] | design.md §2.4 | 「rect 包含判定」语义未定（中心点 vs 整框），且过滤域由 y∈[300,420] 静默宽化为 rect y∈[180,455]，观察捕获集变化未评估。**
现役过滤 = 全图 OCR 后按 y 带 [300,420] + x<960 二分（cw_screen_yinlang.py:160-171，判据用 `mrl.max.center` 中心点）；改为 area rect 后：①「包含判定」三解（中心点入 rect / 整框 ⊆ rect / 相交）设计未选——库内先例偏中心点（cw_observation.py `_anchor_hit_full_ocr` :1851-1852 中心点入 rect），但整框语义下跨界文本（卡间 35px 间隙 x1030-1065 上的长行）会双落空被丢，中心点语义则无此问题，选哪个影响边界文本归属；②两卡 rect 的 y 跨度 180-455 宽于现役 300-420 带，切换后卡顶/卡底区文字（标题带、脚注带）将新进文本桶——桶文本同时喂容器观察（planner_opts）与腿型判定（classify_planner_leg 关键词锚），捕获集变化对两者的影响设计未评估（风险低：关键词锚 longest-match 对噪声稳，但「评估过零影响」与「没评估」是两回事）。
**修正方向**：§2.4 补一句——包含判定 = 中心点入 rect（同 `_anchor_hit_full_ocr` 先例）；并如实申报捕获域宽化（300-420 → 180-455）及对 planner_opts 观察值的影响面（或按需在 rect 内二次用 y 带收窄，一句话定死）。

**G6. [minor] | design.md §2.1/§1.4 | 变费族第二成员（策略赋予变费：飞光·映月驱动 1 费景元变 3/5 费）未入 §1.4 排除表，访问器边界未声明「当前仅银狼LV.999 有档覆盖」——治本核（同族第二次出现面）漏申报。**
玩法正本已在册第二变费成员：「变费同型异源:投资策略「飞光·映月」也驱动费用变换——特殊 1 费景元随镜流星级变 3/5 费,属策略赋予非角色固有」（gameplay/currency_war.md:75）。本批建的费用档机制（match 级字段名 `lv999_cost_tier` + `effective_cost` 双分支）按单角色硬编码成型；读口签名 `effective_cost(gs, char_id)` 已泛化（§2.7 唯一读口的方向对），但字段与实现是单成员形。景元变费属策略效果批、现无消费压力，不入本批范围正确——但 §1.4 排除表逐项给了理由，唯独没这一项；访问器 docstring 边界声明（§2.1 语义双轨）也未写「本口现仅 LV.999 有档分支，第二变费角色出现时扩分支、字段升 dict 键控」的升架预告。缺这句，效果批做飞光·映月时最可能的形状是另起一个平行事例（同族第二次出现该升架构件的面被漏掉）。
**修正方向**：§1.4 排除表补一行「策略赋予变费族（飞光·映月 景元 3/5 费）| 效果批；依赖 = 本批访问器，二成员时扩分支/升字段键控」；§2.1 docstring 边界声明补同句。

---

## 锚点核验清单（本轮新增/复核通过项）

| 设计引用 | 现值 | 判定 |
|---|---|---|
| 09-18 design §2.0 承载「同名即同档」口径本体 | :60 逐字在册（自带口述·权威 2026-09-18） | ✓ |
| equipment_mechanics §7 待实测行（§1.2 如实申报「未清偿」） | :162-163 在册（含「升费后牌池费用档归属」） | ✓ |
| gameplay/currency_war.md:76-79（5费两选项皆装备/新费档刷商店） | :77、:78 原文相符 | ✓ |
| action_ops.md §1「直调自己的上报函数」/ §2.3「落地与否由下一轮重入的入口观察裁决」 | :21、:41 逐字一致 | ✓ |
| 承接出处 09-18 §2.1⑤ 推广批挂账 | :84 内容相符 | ✓ |
| `game_state_from_ctx` @ cw_game_state.py:1133（None 安全） | :1133-1145 | ✓（用途注记失真见 G2） |
| 桩对齐先例 test_cw_game_state.py:712-714 | :712-716 注释+桩在册 | ✓（与所选方案无涉见 G2） |
| 四族代表锚 12 处 | 全部命中（明细见 A/F4 行） | ✓ |
| match_facts 域版本机制 + bump 先例 | cw_game_state.py:158-205（:164 match_facts:2）、:2170 扩展先例 | ✓ |
| match_facts 域与可变局级字段相容（active_strategies/board/shop_refresh_cost〔注「动态」〕同域在册） | :2201-2203 | ✓（lv999_cost_tier 可变语义不违域） |
| 投影审计登记纪律 + 双向完备锁 | cw_projection_audit.py:25-28、:58-60 | ✓（设计已申报登记行） |
| `EVIDENCE_OVERLAY_CLOSED` 单一定义 @ pick_invest | :51；pick_invest 仅依赖 kernel → pick_planner 反向 import 无环 | ✓ |
| zero_writes 现签名与新签名兼容（发射相「参数不变」） | zero_writes.py:127-129（新增 evidence kw 即目标形态） | ✓ |
| 发射调用点 env 透传 leg_type/norm_item | cw_overlay_pick_action.py:409-415 | ✓ |
| 落地记账块 :263-419；`_apply_equip_leg`/`_apply_upgrade_transform`/`_PLANNER_PRODUCER`/`_LV999_ID` 原样迁入面 | :263-419（文件恰 419 行止）、:304、:331、:269、:270 | ✓ |
| `classify_planner_leg` 词表常量 | cw_events.py:904-907 | ✓ |
| §2.6「买支出随观察自动正确」 | cw_buy_card_action.py:137 `ledger.spend_executed += action.card.cost`、:188、:194 unit_cost 同源；card 即观察 ShopCard（cost = resolve_cost_star 产物） | ✓（主张成立） |
| deploy_move 上报函数具 gs 形参，§2.5 插入点可实现 | :52、:104-107（变换判定）、:120-122（落场写）、:126-130（级联） | ✓ |
| 新披露键命名族相容（kind/evidence 为自由串无注册表；同族先例 planner_upgrade_ambiguous 等 snake_case） | cw_screen_yinlang.py:288-299 等在册同族 | ✓ |
| landing 直调测试 9 处（申报「8+」） | test_cw_yinlang_phase32.py:173/190/208/215/230/248/264/279/283 | ✓ |
| `resolve_cost_star`/`CARD_TEXT_Y` 测试零消费（申报「零」） | 全测试仓 grep 零命中 | ✓ |
| src 侧 `apply_pick_planner_landing` 消费仅 cw_screen_yinlang（删符号安全）；`report_action_pick_planner_param` src 消费仅发射点 | grep 全仓 | ✓ |
| `SILVER_WOLF_COST_BY_STAR` {1:3,2:4,3:5} 旧口径在册（§1.2 引作 sim 域另批对象） | cw_sim_special.py:39 | ✓ |
| `_SHOP_COST_MULT_TO_STAR` {1:1,3:2,9:3}（G1 判据） | cw_observation.py:1677 | ✓ |

## 治本核验（核三）

- §1.3 归层成立：症状 2/4/5 = 语义层建模缺位，修法 = 容器字段 + 单一访问器 + 两个写端（修根）；症状 1 = 架构层宿主错位，迁 kernel 单点（修根）；症状 3 = 约定层，回建档单一真相源（修根）。
- §2.3 除数修法 = 参数语义升级（base_cost = 当前档），显式拒绝 badge 多除数尝试与保留旁路（双真相源）——修根非症状。
- 批间边界：sim 池/M21、卖退款、估值族、效果批逐项显式挂账并声明依赖方向（§1.4/§2.6/§2.7），不是逐例症状补丁的堆叠形态。
- 同族第二次出现的漏申报面 = G6（变费族第二成员），其余族边界（卖退款未定谳、起始费永不迁）声明到位。

---

## 总结论

**需修订后收敛。**

发现计数：**6 条 = major 1（G1 badge=8 用例违反 {1,3,9} 倍数体系、新增测试申报锁错误期望）+ minor 5（G2 依据标注失真 / G3 落地相 param 来源与载荷丢失形态未交代 / G4 测试申报残留 / G5 包含判定语义与捕获宽化未评估 / G6 变费族第二成员漏申报）**。另 A 部分附带 1 条流程同步注记（README 进度行超前记「收敛」）。

第一轮八条修订质量总体良好：7 条落地、F7 部分落地，修订未引入结构性矛盾；F1 的依据链经改指后已闭合（被引处逐字承载口径 + 正本矛盾显式承认并排期清偿）。本轮唯一 major 是修订期新增内容的算术错误（badge=8 两处），修订量小（改两处数字 + 五处各一两句定点文字），不涉方案结构。修订后按 hard rule 4 再做一轮全量同步复查（含 README 进度行回改与 G4 申报面拆齐）即可收敛。
