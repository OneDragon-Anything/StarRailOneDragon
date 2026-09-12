# 武装箱选卡价值升级（armory-box-value）设计对抗审报告

- 攻击对象：本目录 `design.md` / `landing.md` / `README.md`（通读后逐面攻击；`attack.md` 本体按无前提纪律未读）。
- 判据源（全部直调原文/原码，禁转述）：策略宪法 `strategy-docs/00_framework.md`、`01_math_framework.md`（§3.6 装备行、§6 三形态章程）；流程硬门 `.dsh/skills/sr-od-currency-war-dev/references/strategy-work.md`（§1 零调参/§3 开关/§6 对抗循环）；写作规范 `docs/develop/harness/iteration-design.md`（§1.1 外溢判定/§5 硬规则三条/§7 三核）；源迭代 `2026-09-12-supply-selection/design.md` + `details/supply-value-spec.md` + `landing.md` + `README.md`（裁定汇编 1-8）；代码真值 `strategies/impl/flow.py`（decide_box_card:654-702、decide_invest:483-529、_refresh_direction_views:392-434）、`kernel/cw_prep_expect.py`（MATERIAL_VALUE_TABLE:32-40、模块 docstring:1-9）、`kernel/cw_events.py`（_EQUIP_VALUE:712-750、decide_supply:783-814）、`prep_actions.py`（:202-238 在册裁定注、:545-589 观察写端、:986-1031 _open_box、:1062-1144 _pick_box_card/_default_box_card）、`kernel/cw_strategy_session.py:167`、`kernel/cw_exec_state.py:278-349`、`operations/cw_screen/_overlay_confirm.py:35-70`、`operations/cw_op/cw_op_equip_all.py:135-169`、`strategies/impl/pick_bias.py` 全文、`strategies/impl/cw_strategy.py:205-208`、`mandate_v1/mandate.py:1640-1654`、`mandate_v1/entry.py:460-467/:665`；注册表 `data/cw_equipment_data.py` 全量实跑、`kernel/cw_comps.py:90-123`；玩法研究 `equipment_mechanics.md`（§1/§1.1/§4）、`board_structure.md:59-62`；证明索引 `proofs/math_proofs.md`（P42 行 :56）；测试仓 `test_cw_material_score.py`、`test_cw_screens_ops.py:41-108`、`test_cw_box_pick_arm.py`、`test_cw_box_open_pick_merged.py`、`test_cw_obs_arch_prep_writeflow.py:360-382`；sim 面 `sr-od-test/fixtures/cw_fake_game/fake_match.py:740-788`、`rules.py:176-186`、`src/.../sim/` 全域 grep。
- 数值直调手段：`uv run python`（PYTHONPATH=src）实跑 `EQUIPMENTS` 全量 recipes 统计（配方引用数与成员槽分列计数、自对配方全量、进阶类引用数）。

## 结论

**9 项发现：1 阻断 + 3 重要 + 5 次要。** 核心方向（序数分档、两态锚定、近兑现档、通用选装入口、通用性退役）成立且零调参合规；但落地面存在一处不可执行的计划（F1），核心新机制（近兑现判定）的规范文本自相矛盾（F3），库存账语义与两个新判据的需求不匹配（F2），以及一处核心取舍的依据论断不成立（F4）。修复后需新一轮无前提对抗再收口。

## 发现清单

### F1【阻断】material_value「全仓退役」漏掉第二消费位，landing 3.2 文件面/边界/完成判据三者互相矛盾

- 位置：`landing.md` §3.2（范围「`cw_prep_expect.material_value` / `MATERIAL_VALUE_TABLE` 随箱打分切换退为零消费 → 本阶段删除」「material_value 退役后全仓零引用（grep 证明）」；文件面仅 flow.py/cw_prep_expect.py/test_cw_material_score.py/test_cw_armory_box_pick.py；边界「不碰 obs 层与执行器」）；`design.md` §2.1/§3 取舍 1。
- 证据（直调）：`material_value` 的生产消费位有**两处**——①`flow.py:666/:699`（decide_box_card，3.2 已覆盖）；②`prep_actions.py:1140-1143`：`_default_box_card` 的**局外回落分支**（match=None 时 `from ...cw_prep_expect import material_value` 并按其排序选卡），同函数 docstring `:1114` 自引回落行为锁。`cw_prep_expect.py:1-9` 模块 docstring 亦自证「同时喂给武装箱选卡策略与备战执行器的内联回落」。测试侧：`test_cw_screens_ops.py:41-43` **模块级** import material_value，`:77-81` `test_material_value_table` 锁手表值（7/6/0），`:99-108` `test_pick_card_fallback_by_material_value` 锁局外回落行为（生命之花胜出）。
- 发作场景：worker 照 3.2 执行——在声明文件面内删 material_value → `test_cw_screens_ops.py` 整模块收集期 ImportError、`_default_box_card` 局外路径运行时 ImportError、「全仓零引用」判据永不可达；不删 → 判据同样不可达。完成判据与文件面/边界无解，触发 iteration-design 写作硬规则 2 的停手令。
- 修正方向：①局外回落的迁移语义入 3.2 范围显式裁决（改消费机器 `equip_material_generality`——注意值从手表 7/6/5… 变注册表计数 10，属行为变化需申报并重推 `test_pick_card_fallback_by_material_value` 锁；或按「虚构序退役」同改 base 排序）；②文件面补 `prep_actions.py` 与 `test_cw_screens_ops.py`；③「全仓零引用」判据改挂「迁移完成后零引用」。

### F2【重要】需求满足判定漏「已穿戴」形态：唯一件守卫（行 8）在最常见的满足态失效

- 位置：`design.md` §2.2（tier 3 条件 `ledger.count(X) < 需求件数(X)`、「需求已满足的 K 不再吃 key 提权」）、§2.3（near_redeem 的 ∃K 需求门同式）、§2.6 行 8。
- 证据（直调）：`last_owned_equips` = **装备区库存账**——全量重写源 = `read_equips`（prep_actions.py:411/:571-577，读装备区网格）；穿戴即移出（cw_op_equip_all.py:152-155，设计 §1.2 自列「穿戴 −」）；已穿件记在 `tracked_deployed[*].equips`（cw_op_equip_all.py:158-161）。锁定态（P2+）下 key 件经装备链穿到角色身上是常态，此时 `ledger.count(K)=0 < 1` → 判定「需求未满足」：箱再出同件 K 仍吃 tier 3、K 的材料对仍可吃 tier 2——恰是行 8 要消除的「零战力增益冗余件提权」，与 §2.2「冗余件必不优于任何有用件」直接冲突。行 8 的示例帧「需 1 已持 1」只覆盖首件仍在库存未穿的少数态。
- 发作场景：锁定局、key 件已穿、箱 offer 复出同件（或其材料）→ 新打分把它排到最有用件之上，守卫承诺落空。
- 修正方向：需求满足判定改用「库存账 + 穿戴账」合计（穿戴账现成 = `tracked_deployed[*].equips`，`exec_state_of(session)` 可读）；近兑现的配对数学保持库存口径（栏内合成的输入面在库存区，现口径正确），仅其 ∃K 需求门换合计。行为表行 8 补「已穿」形态帧。

### F3【重要】近兑现判定三种表述互相矛盾（定义 / 操作条件 / 语义意图对不上），实现者无所适从

- 位置：`design.md` §2.3 判定块。
- 证据（数学直推 + 直调配方结构）：定义「选 X 使可用对数增加」⟺ 交叉对 `cnt(X) < cnt(另一侧)`（min(cntX+1,cntO) > min(cntX,cntO) ⟺ cntX < cntO）；操作条件却写「A≠B → cnt(X)==0 ∧ cnt(另一侧)≥1」——漏掉 1 ≤ cntX < cntO 的真实增对帧（例：持 1 折叠小刀 + 2 轮滑鞋、key=火力风暴潮，再得 1 轮滑鞋，对数 1→2，操作条件判否）。自对条件「cnt 为奇数」与定义一致，但与 §1.1 gap 3 的意图「选这张卡 = 立即合成**拿到** key 装备」（= 选卡解锁**首对**）不一致：持 3 只时第一对早已可合、再得 1 只按操作条件仍升 tier 2。三套语义（真·对数增加 / 写出的操作条件 / 首对解锁意图）在角帧上两两分叉。
- 发作场景：实现者按字面条件落码 → 与定义文本不符、锁 pin 住哪个语义无依据可引（写作硬规则 2「无需再设计」失守，后续锁重推无出处）。
- 修正方向：三取一并全文对齐。建议按意图锚定「选卡解锁首对」：交叉 = `cnt(X)==0 ∧ cnt(另一侧)≥1`、自对 = `cnt(X)==1`（持 3 只以上的第 2/3 对不属「立即拿到」）；或坚持「对数增加」并改交叉条件为 `cnt(X) < cnt(另一侧)`、自对维持奇数——两者都是合法设计，但必须选一个，并把行为变化表补对应申报行。

### F4【重要】「材料通用性在箱候选域为常数/不产生序」论断与设计自身的行为表矛盾

- 位置：`design.md` §1.1 gap 4、§1.4（「保留与否不影响序」）、§2.1、§3 取舍 1；`landing.md` §3.1（V2 快照锚表述）。
- 证据（直调）：「每件 10 条配方引用/11 槽」实跑属实（8 简易全体同值、蓝/红钻 12 槽、进阶 0 引用）——**简易域内**常数成立。但「箱候选域内为常数」只在 offer 同质（全简易或同引用数）时成立，而 offer 组成同质性无任何出处；设计自己的行 1 锚点帧 `[幸运星, 火力风暴潮]` 恰是**简易+进阶混合 offer**，该维在现行打分中产生 3 vs 0 的序（行 1 现行列「幸运星（通用性 3>0）」正是靠它才成立）。故「保留即死重/不影响序」在混合 offer 下为假，§1.4 借它对「box 消费不变」裁定做的「事实前提已被推翻」收窄论证不完整。
- 发作场景：读者按「无序故移除」理解 → 把一次**有意的序反转**（简易优先 → 输出件优先）误读为无行为影响的清理；对抗审后续轮次会反复纠缠此点。
- 修正方向：依据重写（结论不变）——「同域内常数；跨简易/进阶域的旧序（简易优先于无表值进阶件）被本设计**有意废弃**，依据 = 用户指令（输出向先验）+ 裁定 5 同构」；V2 快照锁的「等值」断言显式限定简易域。

### F5【次要】「账失真 → 保守退化（漏提权非错提权）」与实际失效方向不符；计数敏感度高于所引先例

- 位置：`design.md` §2.3 边界清单、§2.5。
- 证据（直调）：空账时 key 件落 **tier 3** 而非「tier 1/0」（「等于现行行为」这半句成立，括注表述不准）；欠计数（获得未记账的通道，如令牌/炉产物）→ 冗余 K 吃 tier 3 = 复现行 8 形态，是**错提权**不是漏提权；过计数 → tier 2 误升。本判据消费 `==0 / ≥1 / 奇偶` 的精确计数，而所引先例 m7 是存在性谓词（mandate.py:1653-1654，容忍计数漂移）——「同源同风险位」低估了敏感度差。缓和事实：穿着即合成主流路径已被「穿戴 −1」正确建模（两件简易各 −1、产物在身上本就不入库存账）；栏内合成（cell_synth）现无生产发射位（全仓仅 cw_prep_expect 期望层建模）。
- 修正方向：表述如实降格（「失真窗内行为 = 现行行为或轻度过提权」），或把新鲜度门/失真观测键从「非目标」升为挂账；不必阻塞定稿。

### F6【次要】行为变化表两处失真（该表是 B 组锁的规范源）

- 位置：`design.md` §2.6 行 4、行 9。
- 证据：行 4 现行列「并列取先」应为「material_value 大者（并列才取先）」——现行对两件表外件按 mv 比较（flow.py:693-701），仅在 mv 相等时才取先；照抄建锁会钉错基线。行 9 帧名「已锁态锚定 = 过渡伪 comp 的帧」自相矛盾——伪 comp 恰是**未锁**帧的物化（flow.py:401-427：locked_comp 空 ∧ P1 才物化），该帧应名「未锁（P1 伪 comp）帧」。
- 修正方向：两处措辞改正；行 4 拆「mv 不等 → 变化（档内序）」与「mv 相等 → 等价（取先不变）」两行更利对锁。

### F7【次要】§2.3 推导 2 的引证辖域：P42 ①③ 是保留面结论，转用于获取面排序

- 位置：`design.md` §2.3 档序推导 2（【推，在册权威 = P42 ①③】）。
- 证据（直调）：math_proofs.md P42 行（:56）与 01_math_framework §3.6 的「近兑现张最贵，绝不喂」辖的是**组件保留**（持有件不喂不卖），非获取面选卡排序；引文文字与出处本身无误。设计已有独立零参数推导兜底（近兑现 = 立即交付 ≥ 延后交付）。
- 修正方向：主推导自立（立即交付论证），P42 降为方向注记——防「在册权威」标签抬高证据强度（结论强度取最弱一环）。

### F8【次要】依据标注缺口两处

- 位置：`design.md` §2.5/§3 取舍 7、§2.2/§2.3/§3 取舍 5。
- 证据：①「overlay 物理遮挡装备区/现读通道不存在」无出处——board_structure.md:61 只证「面板无金币现值、无出售选项」，未证遮挡；该论断支撑着「选择集 = {state 账, 盲选}」与对 prep_actions:211-216 裁定的不冲突论证，应补画面建档/截图级依据。②「唯一件族第二件即死库存」引 equipment_mechanics §4，该节语义本身为【口述·印象级】未实测 +【推断】（仅电光履/蓄能帆/绝对热量 3 组在册唯一标记），设计未带证据分级；守卫逻辑本身不依赖唯一件语义（`key_equips.count` 的需求向量覆盖一般情形），引用强度被抬高。
- 修正方向：①补依据或如实降格为「面板全屏覆盖型 overlay，装备区读取无在册通道（候实证）」；②引用处带证据分级，或改引「需求向量超配 = 零边际」的模型假设。

### F9【次要】零星三件

- 证据（直调）：①§2.3「自对配方（注册表在册 8 条…）」——注册表实际 **10** 条自对（8 简易 + 红钻×2、蓝钻×2 → 财富宝钻），「8 条」未限定简易域（实跑全量清单核对）；②§2.1 机器「追加三件」清单缺 base 取值函数（§2.2 的 `equip_generic_value(X)`）——源三件套只有 dict + 两个函数，cw_events `_equip_value`（:777-779）可作同形先例，建议补一行声明；③`decide_box_card` 薄壳化后 `effect_pick_bias` 通道（pick_bias.py:38-61，R5 预留、恒 0 实证）去留未声明——按 §2.2「自身不再有任何打分实现」将被静默拔除，今日零行为差，但 R5「选项名级偏置随标定批启用」的预留接线点应显式处置（保留 = 薄壳内保留偏置加项；移除 = 声明）。
- 修正方向：①改「注册表在册 10 条，其中简易 8 条」；②补一行；③加一句显式声明。

## 攻过未破角度清单（实际攻击过且未发现问题的面）

1. **注册表统计主张全量实跑复核**：8 简易每件恰 10 条配方引用/11 成员槽完全同值；蓝钻/红钻 12 槽；进阶类 0 引用；8 条简易自对产物清单逐条对上；recipes = 配方元组的元组、每条 (材料a,材料b) 结构属实。
2. **base 值与例证**：`_EQUIP_VALUE`（cw_events.py:712-750）火力风暴潮 6/反重力皮靴 5/以牙还牙甲 4/轮滑鞋 4；幸运星、生命之花不在表（=0）；值域 0-6 属实；行 1/行 3 的现行/改后胜负值逐步复算一致。
3. **现行打分还原**：+100/+30（PICK_BIAS:30-31）、material_value 0-7（cw_prep_expect:32-35 与设计引文逐字一致）、effect_pick_bias 恒 0（pick_bias.py:49-61 bias 恒 0.0 实证）、target_comp 锚（flow.py:669-670）、argmax 严格大于取先（输入序 = OCR 按 x 排序，prep_actions.py:1078）、无信息 fallback idx=0——§1.1 打分摘要与代码逐点吻合。
4. **档间序零漂移命题**：三段 [100,107]/[30,37]/[0,7] 分离复算成立（直击∩材料双中的 130+ 帧不破结论）；R1 辖域自我收窄为「标准帧」、不做全域主张——诚实。
5. **库存账写端清单**：观察全量重写（:411/:571-577）、开箱选卡 +（apply_op_effect cw_exec_state.py:338-345 经 _open_box :1014-1030 补推进）、确认到账 +（_overlay_confirm.py:61-63）、穿戴 −（cw_op_equip_all.py:152-155，且 tracked_deployed.equips +1）、卖角色返还 +（cw_exec_state.py:335-337）——§1.2 清单逐点对上，账确实在、确实被维护。
6. **在册裁定（prep_actions:211-216）辖域区分**：该注确在穿戴计划产出位（_build_equip_wear_plan）语境，辖「发射位吃陈旧快照」；箱场景决策与点卡同函数闭环（_pick_box_card 一体内完成），entry.py:460-465 的发射位也只是发 PickBoxCard 空动作、选卡决策仍在执行期——§2.5 的不冲突论证成立。
7. **锚定两态化**：契约 3（锁线 ⇔ locked_comp 非空）、P1 配方锁帧 locked_comp 恒空自然落未锁（flow.py:401-427 注实读）、decide_invest 先例同款接线（flow.py:503-509）、契约签名不变（cw_strategy.py:206-208）——全部对上；gap 2 对伪 comp 锚的错位描述与源迭代 §1.3 自证一致。
8. **sim 可见性定谳**：fake_match.py `_pick_box_card`（:757-788）无策略调用、card_idx None 恒 idx 0；箱选项 = 商店角色池名落 BenchChar（:751-754/:780-784、rules.py:176-186）；src `sim/` 全域 grep 无 OpenBox/PickBoxCard/decide_box_card——三项直调全对；「A/B 不可作本批判据 + 另立 sim 侧迭代」符合 strategy-work §4 可观测性申报纪律。
9. **零调参合规**：档位 3/2/1/0 = 序数载体零参数；base 全量平移已审计表（ADR-0298/0130/0555，源迭代已裁「值不再重推」）；近兑现推导零参数；需求件数 = 注册表 count；计数加权被正确拒绝（P42 λ 🔴 挂账中，math_proofs :56 实读）；无新开关（§3 默认无开关合规）。
10. **治本核验**：根因归层（语义层：价值模型缺维 + 未分态）成立；§1.4 族级清点正面应答跨件半问——第三件出现即升格族级归口（OQ-3/后续族级迭代）、明示不做第四件盲修；§2.8 通用化边界（bundle 加性形态不可走字典序、equip_pick 换轨需单独裁定）防住「一个入口包打一切」反模式；库存维取序数切片而非拍值 = 治本姿态。
11. **规范遵循（iteration-design）**：总纲四节齐；landing 三阶段七件齐、依赖线性（3.2←3.1）、固定末阶段+正本清单齐；README 模板逐字合规；承接出处卷首注明（源迭代名+裁定节）符合 §1.1 外溢判定要求；正本更新清单目标实存（13_pick_family.md:26/:49 E18 行、08_events.md:33 E18 行均实读核对）。
12. **旧锁处置方案**：test_cw_material_score.py 实读——恰两条断言，在 locked_comp 重锚 + 需求守卫（反甲白厄 3 件需求的多重性由 count 正确承载）+ 空 ledger 帧下语义均保持，「重锚后保持」可行。
13. **引用的测试锚实存性**：test_cw_box_pick_arm / test_cw_box_open_pick_merged / test_cw_obs_arch_prep_writeflow（:360-382 扫描锚辖 `_default_box_card` 含 decide_box_card 调用，3.2 不动执行器则不受影响）均实存。

## 证据强度声明

- 阻断项（F1）的证据 = 生产代码直读 + 测试仓直读 + 设计文本自身三处（范围/边界/判据）互斥，强度高。
- 重要项 F2/F3 的证据 = 代码语义直读与数学直推，其中 F2 的发作频率依赖「锁定态 key 件已穿为常态」这一流程事实（装备链行为，代码注释级佐证），未做实机帧统计；F3 为纯规范文本矛盾，不依赖任何频率假设。
- 重要项 F4 的证据 = 设计文本自涉（行 1 帧与常数论断互斥）+ box offer 组成无出处（缺失证据本身），结论不受影响但依据必须重写。
- 结论整体强度受 F1 约束：landing 3.2 现文本不可执行，定稿前必须修复后重攻。
