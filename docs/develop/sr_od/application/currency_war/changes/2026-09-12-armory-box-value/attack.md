# 武装箱选卡价值升级 设计对抗审报告（armory-box-value）

> 审对象：本目录 `design.md` / `landing.md` / `README.md`（未读同目录历史对抗产物，无前提纪律）。
> 判据源：strategy-docs/00_framework.md、01_math_framework.md（§3.6）、`sr-od-currency-war-dev` skill references/strategy-work.md（§1 零调参/§6 对抗循环）、docs/develop/harness/iteration-design.md（写作硬规则/§7 三核）、源迭代 `2026-09-12-supply-selection/design.md` + `details/supply-value-spec.md` + `landing.md` + `README.md`、玩法研究（equipment_mechanics.md §1.1/§3/§4、board_structure.md）、math_proofs.md P42 行、现行代码、注册表、测试仓、sim 面。
> 方法：数值/口径/引文/码点全部直调原文与代码；注册表与阵容统计类主张由本审自行实跑复核（`uv run python`，2026-09-12 注册表态）；「篇内/代码自洽」与「对得上游戏/宪法/裁定」分开验；设计内行号按任务书口径允许漂移，一律以符号定位复核。
> 结论概要：**发现 6 项 = 阻断 1 / 重要 2 / 次要 3**；另附攻过未破角度清单。

## 一、发现清单

### A1【阻断】「伪 comp key 提权」现行行为断言失实——伪 comp 的 key_equips 恒为空，gap 2 的现行危害不存在，行为表行 9 的「现行」格为假

- **位置**：design.md §1.1 gap 2（「过渡线的关键装备被当终局关键装备 +100 提权」）、§1.3（「锚定错位继承自 target_comp 伪 comp」）、§2.6 行 9（现行 = 「伪 comp 提权胜出」，性质 = **变化**）、landing.md §3.2 完成判据（行 9 列入「变化行各自变化锚点锁」）。
- **证据（直调 + 实跑）**：
  - `state_of(session).target_comp` 全仓写点仅两处：flow.py:427（`_refresh_direction_views`）与 sim/engine_p2.py:143（仅 locked 帧写真 comp）。flow.py:400-426 的取值只有两形态——locked 帧 `get_comp(ist.locked_comp)` 真 comp；未锁 P1 帧 `pair_target_comp(pair)` 伪 comp。
  - `pair_target_comp`（cw_intention.py:1076-1147）构造 `Comp(...)` 时**不传 key_equips**；`Comp.key_equips` 字段缺省 = `field(default_factory=list)`（cw_comps.py:107），构造期无派生（C5 恒等是数据维护测试锁，非 `__post_init__` 推导）。实跑构造伪 comp 确认 `key_equips == []`。
  - 因此现行 `decide_box_card`（flow.py:656-704）的 ①(+100)/③(+30) 两项在 P1 伪 comp 帧结构性恒死（空 key → `_key`/`_key_mats` 皆空）；两项在生产行为里**只在 locked 帧**经真 comp 触发——而那正是锚定正确的帧。「过渡 key 被当终局 key +100」没有任何可达帧。
  - 旁证：test_cw_material_score.py 是把真 comp（反甲白厄）手工放进 `target_comp` 才复现 +100/+30，对应的是 locked 帧路径，不构成 P1 帧反例。
- **发作场景**：landing 3.2 要求为行 9 写「变化锚点锁」——现行侧「伪 comp 提权胜出」不可复现，worker 只能写出对现行为的不实断言或空锁；验收对照 design §1.1 的危害陈述时整段失效。设计定稿后此错误陈述还会随动机段进正本。
- **修正方向**：gap 2 改判为「锚定一致性重构（行为等价）」——两态切锚保留（族级契约对齐、消灭死路径），行 9 从变化行移入等价行/重构申报（以 wrapper 接线锁表达），§1.3 归层句同步收窄，并把「伪 comp 无 key_equips → 箱 ①③ 在 P1 恒死」写为现状事实。源详设 §1.3 box 行的「现行 ①③ 伪 comp 项移除」表述同源同错（非本审对象，但本迭代正本更新清单的指针回写行应一并修正措辞）。本迭代立项正当性不受影响（gap 1/3/4 + 用户指令独立成立）。

### A2【重要】design.md §1.4「明确不解决」与 landing.md §3.1「S13 认领归属 = 本阶段」直接矛盾（同一迭代两文档范围打架）

- **位置**：design.md §1.4 第 3 条（「装备穿戴面（cw_screen_equip_pick）stash 移除：源迭代 P-1 S13 辖域」列入明确不解决）；landing.md §3.1 代位执行声明（「S13 认领归属 = 本阶段……源迭代 P-1 已由本阶段代位，不再单跑」）+ 完成判据（「S13 行为变化锚点全绿」）+ 文件面（含 `cw_screen_equip_pick.py`）。
- **证据（直调）**：源迭代 landing.md §3.1 明文：六消费位重接中「**wear 一处行为变化** = 未锁态 stash_comp +100 移除（……锁 S13）」。本迭代 3.1 执行「源 P-1 全量范围」即把该行为变化带进本迭代；design.md §1.4 未随代位更新，仍把它记作「不解决/归源迭代」。design.md §2.8 也只区分了「equip_pick 接 pick_equipment（非本迭代辖域）」，未区分同一文件上源 P-1 的锚定重接（3.1 辖内）。
- **发作场景**：编排者照 landing 派 3.1、reviewer 照 design §1.4 验收 → 实施了设计声明「不解决」的行为变化，验收冲突打回；或 worker 按交付契约停手令停工提请修订（iteration-design 写作硬规则 2 卡点）。
- **修正方向**：design.md §1.4 该行改写为「由本迭代 3.1 代位承接（源 P-1 范围，锁 S13）」移出明确不解决清单；§2.8 补一句辖域切分（接 pick_equipment = 非本迭代 vs 源 P-1 锚定重接 = 3.1 代位）。

### A3【重要】§2.3 边界②与 §2.5 的写端清单失实：「tracked_bench_chars 无 equips 写端」「全仓 `.equips =` 写点仅两处、均辖 deployed」被代码证伪

- **位置**：design.md §2.3 边界②括注（「`tracked_bench_chars` 无 equips 写端（全仓 `.equips =` 写点仅 cw_op_equip_all.py:160 与 cw_op_deploy.py:1010，均辖 deployed）」）。
- **证据（grep 全仓 + 直调）**：`\.equips\s*=` 命中 9 处。tracked_bench_chars 有**两条生产写路径**：
  1. 买牌 3 合 1 合成装备继承：`_merge_bench` 就地写 `carrier.equips += 继承件`（cw_merge_simulate.py:268；docstring 明示「live tracking 与 simulate 同源」），经 `mutate_bench_deployed`（cw_vocab.py:1124/1150，docstring「本函数**就地改** bench/deployed 两个列表」）作用在 session tracked 槽位表上——2★ 载体落 bench 时合成继承件就写进 tracked_bench_chars.equips；cw_merge_simulate.py:182 为 merge_simulate 副本域同型写点；
  2. 对账续接：`_merge_equips(exec_state_of(session).tracked_bench_chars, bench)`（cw_reconcile.py:257 → :74 `bc.equips = pools.pop(0)`；deployed 侧同款 :274）。
  其余写点：battle_prep_recognizer.py:192（部署排观察注入，备战席不读：:167-168/:195）、engine_p2.py:112（sim）、cw_op_buy_cards.py:1175（GameState.equips 镜像）。
  **headline 缺口仍成立**：商店角色自带装备通道确不入账（`_card_to_bench` cw_vocab.py:625-628 不带 equips；备战席无装备 icon 不可读）。
- **发作场景**：(a) 需求守卫的总持有账少读一本**现成存在**的账——合成继承到 bench 载体上的 key 件在部署前被守卫漏计；设计把该通道描述成「结构性盲区」，会使后续持有/穿戴账补全批低估可修面、把可零识别面成本修掉的通道排进挂账；(b) 后续批按「仅两处写点」做全仓梳理会漏改。
- **修正方向**：修正写端清单；重估总持有账构成 = 备用（last_owned_equips）+ 部署穿戴（tracked_deployed[*].equips）+ **bench 穿戴（tracked_bench_chars[*].equips，合并继承通道现成可读）**；商店自带装备通道维持挂账；缺陷申报表（欠计数方向）随第三本账并入而收窄。

### A4【次要】「跨简易/进阶域旧序建立在虚构值上」表述过强——该序方向与注册表计数同向，废止依据应只挂用户指令 + 裁定 5 同构

- **位置**：design.md §1.1 gap 4 末句（「含『简易件优先于无表值进阶件』的跨域序」归入虚构值之序）、§2.1（「跨简易/进阶域的旧序（手表梯度）为虚构序」）。
- **证据（实跑）**：手表值（cw_prep_expect.py:32-35，花7/鞋6/电池6/钻头5/刀5/装甲5/枪4/星3）自注出处 `docs/game/currency_war/data/equipment.md` **在仓内已不存在**（glob 仅剩 research/equipment_mechanics.md），且注册表下简易域内 8 件全部 10 配方/11 槽完全同值——**域内梯度确为虚构**，本审实跑证实。但跨域方向（简易材料 10 > 进阶成品 0 引用）与注册表派生计数**同向**，并非注册表反驳的序。
- **发作场景**：后续读者引用本设计论证「注册表化通用性维无序」时，沿「跨域序也虚构」的印象误伤 `equip_material_generality` 在非箱消费位（审计、后续裁定）的合法性评估。
- **修正方向**：措辞收窄为「域内梯度虚构（注册表等值反驳）；跨域序方向与注册表同向，本设计废止它的依据 = 用户指令（未锁线选输出）+ 裁定 5 同构，非虚构性」。

### A5【次要】landing 末阶段「正本更新清单」混入两行源迭代 changes/ 文档，与「正本更新」命名/文件面口径不符，跨迭代改写亦无规范明文授权

- **位置**：landing.md「正本更新清单」后两行（`changes/2026-09-12-supply-selection/details/supply-value-spec.md` §1.3/§5、`changes/2026-09-12-supply-selection/landing.md` §3.1 ← 3.1）与末阶段范围/文件面（「按清单逐条更新**正本**」「文件面 = 清单所列**正本文档**」）。
- **证据**：iteration-design.md §1.1 对外溢迭代的关联手法 = 新迭代卷首注明承接出处 + 账本 dep 挂最小前置；未授权改写源迭代文档。源迭代是活跃迭代（落地 0/5，其 landing 是其账本唯一源）；对另一迭代的 changes/ 过程件做写操作，且该件「寿命 = 迭代」——源迭代先行收尾/清理时指针悬挂。
- **发作场景**：源迭代若先于本迭代末阶段收尾，其文档已被自己的正本更新批改写或进入清理窗 → 本迭代再写入代位指针 = 冲突或悬空；reviewer 按「正本更新」名义验收会漏掉这两行的特殊生命周期。
- **修正方向**：两行从「正本更新清单」拆出为独立的「对源迭代的修订指针」小节（末阶段文件面显式列这两处 changes/ 路径），或改为经编排者在账本层作废源 P-1 任务 + 源 README 进度行登记；避免以「正本更新」名义夹带跨迭代过程件改写。

### A6【次要】tier 1 的需求守卫机制存在二义：满足 K 的材料「退出提权」未写明按 K 过滤，共享材料帧会出现两种实现分歧

- **位置**：design.md §2.2 tier 表 tier 1 行（`X ∈ key_fit_names(key_equips) 材料`，公式不带需求门）+ §2.2/§2.3 守卫 prose（「需求已满足的 K（含其材料对）不再吃 key 提权」）。
- **证据（直调）**：简易材料高度共享——每件材料进 10 条配方（实跑），一套 comp 的多个 key 成品普遍共用材料。具体分歧帧：反甲白厄（key = 以牙还牙甲/高周波电锯/以牙还牙甲·特权/热血沸腾拳），幸运星同时是三者材料；若以牙还牙甲需求已满足而高周波电锯未满足，offer 出幸运星：「先建全集再剔除满足 K 的材料」实现 → tier 0；「∃ 未满足 K 含 X」实现 → tier 1。near_redeem 定义已是显式按 K 需求门（「∃ key_equip K（需求未满足……）」），tier 1 未同构声明。
- **发作场景**：实现者按字面「剔除满足 K 的材料」落码 → 与设计自己的需求门语义（超配只灭该 K 的边际，不灭材料对其他未满足 K 的服务）相悖，共享材料帧系统性漏提权，且行为锁若按错误读法写会钉死错语义。
- **修正方向**：tier 1 公式补齐需求门，写为「∃ 未满足 K：X ∈ key_recipe_pairs(K) 材料」（与 near_redeem 同门同口径），一行改动即可消除二义。

## 二、攻过未破角度清单（实际攻击过的面与关键证据）

1. **注册表配方统计全套主张**（§1.1 gap 4 / §2.1 / §2.3）：简易 8 件每件恰 10 条去重配方引用/11 槽、完全合成图 K8；蓝钻/红钻 12 槽（11 配方）；垃圾袋 2（欢愉星徽双配方）；进阶类 0 引用；自对配方恰 10 条且逐条名单与 §2.3 所列完全一致——实跑逐项证实。
2. **阵容库统计主张**（§2.1/§2.6 行 8c）：COMP_LIBRARY 恰 20 套；重复 key_equips 恰 5 套且名单/重复件逐套吻合（昼神阿雅 2×反重力皮靴、狼尊欢愉 2×反重力皮靴、命运圣杯红A 2×动能激发剑、追击飞霄 2×火力风暴潮、专家桑博DOT 2×火力风暴潮）；cw_comps.py:107 注原文在位——实跑证实。
3. **现行加法制值域三段分离**（§2.2 漂移面）：直击 {100}（key_equips ∩ mv 表 = ∅ 实跑）、材料 [33,37]（key 材料全体 = 8 简易名实跑、mv 最小 3）、通用 [0,7]——「每一直击 > 每一材料 > 每一通用」成立，R1 档间零漂移命题的现行侧成立；①+③ 双中叠加「结构存在、现行库零实例」证实（独立 if 无 elif，flow.py:695-703）。
4. **base 平移表主张**：`_EQUIP_VALUE` 值域 0-6（min 2/max 6，表外 0）、键 ⊆ EQUIPMENT_ROSTER、火力风暴潮 6/反重力皮靴 5/以牙还牙甲 4/光能电池 3/轮滑鞋 4——行 1/2/3/4c/未锁态示例各值直调证实。
5. **库存账与写端清单**（§1.2/§2.5）：last_owned_equips（cw_strategy_session.py:167）、观察全量重写（prep_actions.py:404-416/:571-584）、开箱选卡 +（cw_exec_state.py:338-345）、确认到账 +（_overlay_confirm.py:61-63）、穿戴 − 与部署位 +1（cw_op_equip_all.py:134-163，:152-155/:156-161 分工与设计引用一致）、卖返 +（cw_exec_state.py:325-337）、期望态对账网（compare_equip_expect 在册）——逐一证实。
6. **§2.5 防御注记**：prep_actions.py:211-216 在册裁定原文辖「发射位吃快照」且理由是「执行帧现读严格不劣」，与开箱场景（决策与点卡同执行链闭环：_open_box :1004-1049 于 :1032 内联 _pick_box_card :1080-1117；entry.py:465 发射位只发空 `PickBoxCard()`）结构可分——不与裁定冲突的论证成立；OCR 卡名行输入契约（:1090-1096，按 x 排序 = 从左到右）与「并列取输入序先者」衔接证实。
7. **§2.7 sim 三项定谳**：FakeMatch._pick_box_card（fake_match.py:763-794）无策略调用、card_idx None 恒取第 1 张；假箱选项 = 商店角色池名（rules.py:176-186）落 BenchChar 入备战；`sim/` 全域 grep OpenBox/PickBoxCard/decide_box_card 零命中——「结构性不可见、A/B 不可作本批判据」成立。
8. **行为表其余各行现行侧复核**（1/2/2b/3/4a/4b/4c/5/6/7a/7b/7c/8a/8b/8c/10）：含 7a 帧可行性（反甲白厄 key 集直调：以牙还牙甲配方 = (量产型装甲, 幸运星)、热血沸腾拳配方含生命之花，现行 37>33 选花、新制 tier2>tier1 选星）、7b/7c 自对边界（cnt==1 / cnt≥3 排除）、8c 原序列 count 语义（frozenset 去重会误判已满足的论证成立）——除行 9（A1）外全部成立。
9. **近兑现档定义/操作条件自洽与档序推导**（§2.3）：交叉/自对条件与「选前 0 对 → 选后 ≥1」定义逐条对齐；自对排除 cnt≥3、弃「对数净增加」宽定义的理由自洽；直击⊇近兑现的支配性论证 + 弃加法制防 base 顶翻的结构理由成立；证据分级申报（P42 保留面定位、唯一件【口述·印象级】仅辅助、皮靴可叠加反面信号 + plaza 3×皮靴形态申报、观测键挂账）如实。
10. **零调参宪法对账**：全案零新数值（档位 0-3 序数、base = 既有平移表、100/30 随退役消亡）；MATERIAL_VALUE_TABLE「虚构序」定性（表值直调吻合、出处文档已删、注册表无梯度）成立（A4 仅收窄跨域表述）；序数切片绕开 λ 挂账的违宪风险论证成立。
11. **旧锁处置与测试面**（landing 3.2）：test_cw_material_score（target_comp 锚、两条断言）、test_cw_screens_ops 两把 material_value 锁（:77 手表值锁 / :99 回落行为锁，后者与 _default_box_card docstring :1132 互证）、test_cw_obs_arch_prep_writeflow 扫描锚（:360-382 扫 `_default_box_card` 源码含 'decide_box_card'，3.2 后 match 分支仍委托策略层 → 锚不受影响的判断成立）、box 机械链测试（test_cw_box_pick_arm/test_cw_box_open_pick_merged）不涉打分——处置清单成立。
12. **material_value 退役面**：src/ 消费位全量 = flow.py（box 主路径）+ prep_actions.py:1159-1161（局外回落）+ pick_bias.py:32 注释——「两处消费退出后全仓退役删除」的前提成立（测试仓消费已在处置清单内）。
13. **共享机器与消费位接线**（§2.1/landing 3.1）：key_fit_names 改由 key_recipe_pairs 派生、V4 独立第二构造对拍、V2 修订（机器计数 vs 直查计数 + 注册表形态快照锚，数值经实跑吻合）、3.1 期 ② 不换源保 argmax 基线、六消费位与源 P-1 范围对表、mandate_v1/bridge.py 覆写面（decide_prep_screen/decide_encounter/decide_shop_screen，未覆写 decide_box_card）——成立。
14. **规范遵循**：README 模板合规；landing 三阶段七件齐、固定末阶段 + 清单在；design 无过程叙事；mandate_v1 未覆写面下「CwFlowStrategy 默认实现」的表述与 bridge.py 直调一致；族级清点六消费位名单（decide_encounter/megastar/partner/star_tome/wish_trial/planner）与 flow.py 直读一致、跨件半问已应答（归口 OQ-3/族级迭代）——治本核通过（根源两问：语义层价值模型缺维，修法为语义层重建 + 序数切片，非症状补丁）。
15. **行号漂移对账**：design/landing 所引码点行号普遍有 2-45 行漂移（如 _open_box 实为 :1004-1049、内联选卡实为 :1032、_pick_box_card 实为 :1080-1117、decide_supply 实为 :783-814），均在任务书声明容差内，符号定位全部成立，不作发现。

## 三、证据强度声明

- 阻断项 A1 证据链 = 构造点直读（pair_target_comp 不传 key_equips）+ 字段缺省直读（cw_comps.py:107）+ 写点全量 grep（target_comp 仅 2 处）+ 实跑构造验证，四环独立同向，无弱环。
- A3 证据 = 全仓 grep + 写端函数体直读；「商店自带装备不入账」的反向确认（_card_to_bench 不带 equips + 备战席无 icon）同样直调。
- 其余发现证据均为直调代码/文档原文；注册表与阵容数字为本审实跑复算，非转述。
- 结论强度取最弱一环：A1 使现行行为陈述与验收判据失真，**修复前不满足定稿门槛（攻击收敛 + 试读过）**；A2/A3 为定稿前必改；A4-A6 为措辞/口径收口项。
