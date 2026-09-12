# 武装箱选卡价值升级（armory-box-value）设计对抗审报告

- 攻击对象：本目录 `design.md` / `landing.md` / `README.md`（通读后逐面攻击）。
- 判据源（全部直调原文/原码，禁转述）：策略宪法 `strategy-docs/00_framework.md`、`01_math_framework.md`；流程硬门 `.dsh/skills/sr-od-currency-war-dev/references/strategy-work.md`（§1/§6）；写作规范 `docs/develop/harness/iteration-design.md`（硬规则三条/§7 三核）；源迭代 `2026-09-12-supply-selection/design.md` + `details/supply-value-spec.md` + `landing.md` + `README.md`；代码真值 `flow.py`（decide_box_card:654-702 / decide_invest:483-529 / _refresh_direction_views:392-434）、`kernel/cw_prep_expect.py`（MATERIAL_VALUE_TABLE:32-35）、`kernel/cw_events.py`（_EQUIP_VALUE:617-655、decide_supply:688-719）、`prep_actions.py`（:202-238 裁定注、:986-1031 _open_box、:1062-1144 _pick_box_card/_default_box_card）、`kernel/cw_strategy_session.py`（:167）、`kernel/cw_exec_state.py`（:278-344）、`mandate_v1/mandate.py`（:1640-1654）、`mandate_v1/entry.py`（:665）、注册表 `data/cw_equipment_data.py` 全量、`kernel/cw_comps.py`（COMP_LIBRARY:570 起、get_comp:1202）；玩法研究 `equipment_mechanics.md`、`board_structure.md`；证明索引 `proofs/math_proofs.md`（P42 行）；sim 面 `sr-od-test/fixtures/cw_fake_game/fake_match.py`（:590-593、:730-788）、`rules.py`（:176-186）。
- 数值直调手段：`uv run python` 实跑注册表统计（见发现 1）。
- 行号为写作时点读数，定位以符号为准。

## 一、发现清单

计数：**阻断 2 / 重要 3 / 次要 9，共 14**。判定：对抗不收敛，设计停留草案，不可派落地批。

### 阻断

**F1【阻断】材料通用性维的取值语义断裂——设计全部示例数建立在与消费契约相反的值上，用户指令锚点行为在契约语义下反转**
- 位置：design.md §2.1（机器三件套照执）、§2.2（base 定义与「材料通用性 0-7」、未锁态示例序）、§2.6（行为变化表行 1「改后 火力风暴潮（base 6>3）」）；landing.md §3.1（V2 全绿判据）。
- 契约原文（supply-value-spec.md §1.3 第 2 件）：`equip_material_generality(name)` =「全 EQUIPMENTS 配方引用计数（【注·注册表派生】）」；V2 锁（同文 §5）：「`equip_material_generality(n)` == 旧 `MATERIAL_VALUE_TABLE[n]` ∀ 8 名」。
- 直调证据（实跑注册表统计，`data/cw_equipment_data.py` 全量 recipes）：8 件简易材料**每件被恰好 10 条配方引用**（成员槽 11，自对配方双成员），而手表值为 花7/鞋6/电池6/钻头5/刀5/装甲5/枪4/星3——两套数在**任何计数口径下都对不上**（手表源=过期局部文档 `docs/game/currency_war/data/equipment.md`，注册表头部自注该 md 仅 4 条兜底）。契约语义与 V2 互斥：按契约取注册表计数则 V2 必红；按 V2 保手表值则「注册表派生」标注为伪（真值源=冻结手表）。
- 发作场景：本设计按契约语义取值时，base(幸运星)=0+10=10 > base(火力风暴潮)=6+0=6 → §2.6 行 1 的「改后选火力风暴潮」**反向**（仍选幸运星），且全部材料通用性同分 10、退化为「是材料 +10」布尔——用户指令「没有目标阵容时选更普遍用于输出的」在该语义下落空，§2.2 未锁态示例序（风暴潮>皮靴>甲>幸运星）整体不成立，「0-7」「base 极值 13」值域声明全错。按手表值取值时示例成立，但消费的是一张伪标注的冻结表，且与源迭代 V2 的对拍走向冲突（落地即红）。
- 修正方向：设计层对 generality 取值语义定谳三选一并全量重算受影响数字：①真注册表计数（须接受材料布尔主导，未锁态先验需重设计——去通用性项或改判据形态）；②手表快照（改标注为对拍冻结表、V2 语义改为快照对拍，并在本设计显式声明沿用手表值）；③改用目标线相关面的在册机器（`cw_synthesis.component_demand`/`recycle_qualified` 族）重定义「通用性」。①/③保住「注册表派生」的真实性；不推荐②。

**F2【阻断】「加法制→序数制零行为漂移/逐点同序」论证错误：现行档内排序基是 material_value（无通用值项），不是 base——已锁态档内序改变未申报，R1 辖域自相矛盾**
- 位置：design.md §2.2（等价性段落、§2.6 已锁态两行「等价」）；landing.md §3.2（R1「现行三档行为逐点保持」）。
- 代码真值（flow.py:694-699）：现行打分 = `effect_pick_bias + 100·[key] + 30·[key_mat] + material_value(name)`——**没有 equip_generic_value 项**，档内序 = material_value 序。§2.2「同档内加法分 = 常数 + base，随 base 单调，序同 base 序」对现行代码不成立；「现行加法三档的值域 = 直击 ≥100、材料 [30,43]、通用 ≤13」也不是现行值域（现行实为 [100,107]/[30,37]/[0,7]，13=6+7 是新 base 上界）。
- 反例（真实 comp：COMP_LIBRARY 「花火」系 key_equips 含 火力风暴潮+热血沸腾拳，cw_comps.py:1083；生命之花→热血沸腾拳、轮滑鞋→火力风暴潮均为 key 材料）：已锁态 offer [生命之花, 轮滑鞋]——现行 30+7=37 > 30+6=36 选**生命之花**；新制 base 0+7=7 < 4+6=10 选**轮滑鞋**。同档（材料档）内序翻转。该翻转在两种 generality 语义下都成立（注册表值 10 vs 14 同向）。同族：已锁态 tier0 通用件之间现行全并列取先、新制按 base 排序——同为未申报的档内行为变化。
- 发作场景：§2.6 行为变化表已锁态仅两行且均标「等价」（只覆盖档间），档内变化行缺失；landing 3.2 要求 §2.6 逐行锁 + R1「现行三档行为逐点保持」——worker 按任一口径落锁都与另一口径冲突（锁现行档内序 = 与 pick_equipment 新序相反；锁新序 = R1 不绿），实现者无可执行判据（违反写作硬规则 2）。
- 修正方向：等价性命题改述为「仅档间序不变」（该命题本身成立：100/30/0 三段分离在任一 base 上界下都保持）；§2.6 补档内行（材料档内、tier0 档内的序变化，标注为变化并给出意图依据）；R1 重定义为「档间回归帧 + 显式列出的接受变化档内对照」；若要求档内也零漂移则须重定义 base（受 F1 语义定谳约束，一并裁）。

### 重要

**F3【重要】近兑现判定对自对配方（×2 合成）恒为假——8 条自配进阶全部结构性失效，含速度系命脉反重力皮靴**
- 位置：design.md §2.3 判定式与「边界情形裁决」清单。
- 证据：判定式 `X ∈ {A,B} ∧ ledger.count(X)==0 ∧ ledger.count(另一侧)≥1`。注册表自对配方 8 条：反重力皮靴=轮滑鞋×2（:72）、永动机=光能电池×2（:107）、碎星斩舰刀=折叠小刀×2（:80）、虫洞掘进钻头=以太钻头×2（:105）、生命之环（:98）、很硬的甲（:102）、天基轨道炮（:87）、随便骰子（:93）。自对时「另一侧」=X 自身 → `count(X)==0 ∧ count(X)≥1` 永假。而反重力皮靴/永动机/碎星斩舰刀/虫洞掘进钻头均为在册 comp 的 key_equips（cw_comps.py :662/:687/:632/:801 等；cw_events.py:612 自注「找鞋战争：速度 comp 命脉」）。
- 发作场景：恰持一件轮滑鞋、箱出第二只（正好补成 key 皮靴）→ 近兑现档静默不触发，按 tier1 与其他材料比。该族 key 的新档收益整体为零，且按式实现无法从测试外发现（静默失效，与 r130 材料分失效同构）。
- 修正方向：§2.3 显式裁决自对情形（如 `X==A==B 时改判 ledger.count(X)==1`），并入边界情形清单与行为锁。

**F4【重要】landing 3.1 继承并重申自相矛盾的「box 值零变化」判据——按源迁移表执行 box 行后该判据两条路径都不可达**
- 位置：landing.md §3.1（「六消费位回归帧全绿（box/supply/planner/sim 值零变化…）」）及其照执的源 landing §3.1 同款判据。
- 证据：源迁移表（supply-value-spec.md §1.3 消费位迁移清单）decide_box_card 行 =「② 消费 equip_material_generality；未锁 = 仅材料通用性 + **通用值**」——box 打分加入现行没有的通用值项 + ② 换数据源（F1 已证换源必变值）。而源与本的 landing 均要求「box 值零变化 / 行为等价」。加通用值项 = 变；不加 = 迁移表未执行。另：源迭代 README 自身状态矛盾（卷首「草案（口径收集态）」vs 进度行「迭代设计:定稿」），「§3.1 全量范围照执」的锚本体处于不稳定态。
- 发作场景：worker 立阶段判据时「值零变化」与「迁移表执行」互斥，验收锁无从落。
- 修正方向：3.1 明确 box 消费位的行为等价基线（相对现行 flow 实现的 argmax 逐点一致、material_value 保留原值），把「加通用值」显式划为本迭代 3.2 的行为变化面并给变化判据；同时促源迭代收敛其 README 状态与迁移表。

**F5【重要】§2.7 sim 可见性框架失准：直调已可定谳的三事实（无策略路由/假游戏箱发角色牌/引擎零箱动作）使「二选一」申报框架两支都不描述真实结构**
- 位置：design.md §2.7；landing.md §3.2 完成判据「sim 选卡路由核实结论落报告（…二选一如实申报）」。
- 证据：①fake_match.py:757-788 `_pick_box_card` 无任何策略调用，card_idx None → 恒 1（第一张）；②fake_match.py:751-754/780-784 箱选项 = shop_pool **角色名**、落 BenchChar 入备战——与真机箱「4 选 1 装备」（board_structure.md:61 实机采证；生产侧选卡入 last_owned_equips，prep_actions.py:1019-1030）不同物；③`src/sr_od/application/currency_war/sim/` 全域 grep PickBoxCard/OpenBox/decide_box 零命中——引擎根本不发箱动作。design.md §2.7 引文坐标本身属实（fake_match.py:592-593、rules.py:178 在库），但「若经策略，还须确认 sim 会话 last_owned_equips 同步」支完全 vacuous（即便路由，选项是角色名，装备打分全零）。
- 发作场景：3.2 的「二选一」核实被引导到错误分支；未来若有人给 sim 补策略路由，A/B 仍测不到本批（选项语义错物）。
- 修正方向：§2.7 直接落直调结论（结构性不可见：无路由 + 选项为角色牌 + 引擎零箱动作），申报口径按此改写；「假游戏箱改发装备牌」如需补齐另立 sim 侧迭代，不入本批。

### 次要

**F6【次要】§1.2 写端盘点引文失真：「买牌 +」指向的 cw_op_buy_cards.py:1170 是读不是写**
- 证据：该行 = `state.equips = list(getattr(match.session, 'last_owned_equips', []) or [])`，注释自证是「cw_comps 装备动态权重读 state.equips」的投影同步（读端）。全仓 last_owned_equips 写端实况：prep_actions.py:411/:577（全量重写）、cw_exec_state.py:278-282（`_owned_add`，经 apply_op_effect 于 PickBoxCard :344、SellDeployed 装备返还 :335-337）、cw_op_equip_all.py:152-155（穿戴 −）、:623（重写）、_overlay_confirm.py:61-63（确认到账 +）。「买牌 → 库存 +1」写端不存在。
- 发作：写端清单含伪成员（值对标签错类）；但「库存账在册且可消费」总论不受影响（开箱/确认到账/穿戴/卖返四通道齐全，恰为本迭代消费面）。
- 修正：删「买牌 +」或改为实际事件「确认到账/补给确认 +」。

**F7【次要】V4 是恒真锁：key_fit_names 已定义为 key_recipe_pairs 的派生，「≡」断言无咬合力**
- 位置：design.md §2.1（「key_fit_names 改为由 key_recipe_pairs 派生…对拍锁 V4 防两路漂移」）；landing.md §3.1 V4。
- 证据：断言两侧 = 同一推导（keys ∪ pairs 全成员），恒真，「两路」不存在，「防漂移」无从发生。
- 修正：V4 改为独立第二构造（直查 EQUIPMENTS.recipes 遍历 vs 经 pairs 派生）对拍；或降级为普通单元断言并删「防两路漂移」表述。

**F8【次要】`pick_equipment` 的 `with_generality` 参数全文无语义**
- 位置：design.md §2.1 签名。该布尔缺省 True，正文/docstring 未定义 False 行为与消费方——实现者遇到即未定义语义（写作硬规则 2 卡点）。
- 修正：删参，或定义语义与消费场景。

**F9【次要】近兑现无「K 需求已满足」守卫——会把提权送给第二个 K（唯一件族 = 死库存方向）**
- 位置：design.md §2.3。判定只查材料对，不查账内 K 件数是否已达 key_equips 需求（key_equips 可含重复，cw_comps.py:107 注「可含重复，如阿雅需 2 反重力皮靴」）。唯一件族（电光履/蓄能帆/绝对热量，equipment_mechanics.md §4：第二件即死库存）受害最明确。
- 发作场景：comp 需 1 件绝对热量且已持有、账内有生命之花 → 箱出光能电池升 tier2（补第二对）→ 追第二件绝对热量 = 死库存提权，压过对其他 key 有用的 tier1 材料。
- 修正：判定增加「K 未满足」合取（`ledger.count(K) < key_equips 需求件数` 口径），入边界清单。

**F10【次要】档序推导 2 未引在册最强权威 P42**
- 证据：01_math_framework.md §3.6 组件保留行：「分层 = 最近兑现距离 × partner 到位率——**近兑现张最贵，绝不喂**｜P42 ①③」，math_proofs.md P42 行（③ 支配定理，R4 对抗收口）。design §2.3 推导 2 用 00_framework 发展优先 + 裁定 3 自推，未引 P42——本迭代档序恰是该已证序级结论的选卡面应用。
- 修正：推导 2 补引 P42 ①③ 为主要依据（依据就地标注取最强在册源），自推降为同向注记。

**F11【次要】正本更新清单缺 `08_events.md` E18 行**
- 证据：08_events.md:33 E18 行含「材料估值 = `cw_prep_expect.material_value`」与「待 derive（结构打分…）」表述，本迭代落地即过期；同清单只列 13_pick_family.md E18 行。源迭代先例同型（其正本更新清单含 08_events.md E4 节）。
- 修正：清单补「strategy-docs/08_events.md §判据表 E18 行 ← 3.2」。

**F12【次要】README 进度行缺对抗报告指针（模板偏差；本批文件面受限仅写 attack.md，移交后续批）**
- 证据：iteration-design.md §4 模板要求「设计对抗:<状态> · 报告=[attack.md](attack.md)」；本迭代 README「设计对抗:未开始」无指针行。本报告落盘后该行应更新为「进行中 · 报告=[attack.md](attack.md)」——归编排者/下一批（本攻击批文件面 = 仅 attack.md）。

**F13【次要】§2.2 示例括号序与公式序相反，按公式读则四个示例的成员标签全错**
- 证据：公式 base = `equip_generic_value + equip_material_generality`（通用值在前）；示例「火力风暴潮(0+6)…幸运星(3+0)」按(通用值,通用性)序读则成员值全反（实值：风暴潮 通用6/通用性0，幸运星 通用0/通用性3；「(0+6)(0+5)(0+4)(3+0)」实为(通用性,通用值)序）。加法下数值不变，但按公式读数的实现者/评审会取错成员值（值对标签错类）。
- 修正：统一为公式序（6+0 / 5+0 / 4+0 / 0+3）。

**F14【次要】治本核验·跨件半问未答：pick 族 target_comp 锚定错位的第三件逐件修，剩余消费位无族级清点**
- 证据：同族「target_comp 伪 comp 锚 → 两态化」已修 decide_invest（T-155/ADR-0597）、decide_supply（源迭代 P-3），本迭代修 decide_box_card = 第三件。§1.4 仅对 planner/supply 声明辖域外溢；flow.py 内仍在消费 `state_of(session).target_comp` 的 pick 族（decide_encounter:541、decide_megastar:552、decide_partner:567-568、decide_star_tome:602、decide_wish_trial:632、decide_planner:581）无族级清点与处置声明。两态锚定契约（源详设契约 3）已是族级底座，但「剩余消费位各自裁定路径」未显式收口——按 AGENTS.local 跨件半问，同族第三件应升级族级处置或显式声明为何不升。
- 修正：§1.4 补一段剩余消费位清点 + 处置计划（或声明由源迭代 OQ-3 扩容承接并点名各消费位）。

## 二、攻过未破角度清单

1. **现行打分复述**（§1.1 四项、+100/+30 常数、effect_pick_bias 恒 0 占位、并列取先、OCR 左→右输入序、fallback idx=0）——与 flow.py:654-702、pick_bias.py:30-31/:38-61（bias 循环体只 continue 不累加，恒 0）、prep_actions.py:1078（按 x 排序）逐项一致。
2. **锚定错位事实链**——target_comp 的 P1 伪 comp 物化（flow.py:401-427，ADR-0357 配方锁局 locked_comp 恒空）与设计 §1.1 gap 2/§2.4 引述一致；decide_invest 先例（:483-529）与 `_ensure_intention` 接线方式一致。
3. **契约签名不变**——cw_strategy.py:206-208 抽象签名直调一致；`get_comp(ist.locked_comp)` 读法与 flow.py:400 一致；fail-closed 保守向（解析失败落未锁+哨兵）与源迭代 §1.4 同款。
4. **§2.5 裁定注辖域解读**——prep_actions.py:211-216 确为「装备穿戴计划产出位」语境（执行帧 read_equips 现读可得），设计「该裁定辖穿戴场景、开箱场景结构不存在发射后漂移面」的辨析成立；`_open_box` 同动作选卡闭环（:986-1031）与选卡后补推进（:1019-1030）直调属实；「账失真 → 落 tier1 = 现行行为」保守退化自洽。
5. **消费先例**——mandate.py:1640-1654（m7 可穿面谓词吃 last_owned_equips）、entry.py:665（持有快照）在册，与 §2.5「同源同风险位」声明一致。
6. **零调参宪法合规**——本迭代零新增决策常数（档位为纯序数、base 全用既有表值）；拒绝计数加权/伙伴通用性仲裁等拍序面（§2.3/§3 取舍表）与 strategy-work §1「禁拟合常数充当闸门」一致；数值半部维持挂账、不因本迭代解锁，与 P42 在册状态（🔴 λ 待标定、序级结论在册）一致。
7. **近兑现档序推导 1（直击 ⊇ 近兑现）**——「弃加法制保支配」的取舍论证成立（若近兑现并入 +100，base 项确可翻转支配方向）；字典序使档间支配结构化的说法成立（错在档内，见 F2，档间部分无恙）。
8. **裁定对账**——裁定 5/6/7/8 原文（源 README 裁定汇编）与设计的引用（未锁态保留材料通用性=裁定 5 box 消费不变、通用机器禁第二套=裁定 6、装备穿戴面 S13 归源判据）逐条相符；「box 行为变化在源阶段划分无归属、自成新迭代」符合 iteration-design §1.1 外溢判定。
9. **landing 结构规范**——阶段小节七件齐、末阶段+正本更新清单在、单文档方案合法（iteration-design §2.1）、状态表述（草案/未过审不派批）合规。
10. **13_pick_family.md E18 / 08_events.md E18 引用真实性**——两处 E18 行在册且内容与设计「现行结构打分」描述一致（仅 F11 指出正本更新清单遗漏）。

## 三、判定

三核结论：**不收敛**。核一（无前提）：F1/F2 击穿 §2.2 核心论证与 §2.6 行为表完整性，F3/F5 为语义/框架缺口；核二（规范遵循）：写作硬规则 2 多处失守（F2 的 R1 辖域、F3 自对情形、F8 参数、F4 判据互斥）；核三（治本）：根因归层（语义层）成立、库存维治本路径（序数切片避开 P42 数值挂账）成立，但跨件半问未答（F14）。修复方按各发现修正方向改稿后，须以**新干净上下文**再攻一轮。
