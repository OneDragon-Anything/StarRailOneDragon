# 武装箱选卡价值升级（armory-box-value）设计对抗报告

> 对象：本目录 `design.md` / `landing.md` / `README.md`（`attack.md` 历史产物按任务书禁读，未打开）。
> 判据源（全部直调）：strategy-docs/00_framework.md、01_math_framework.md（§3.6/§6）、strategy-work.md（§1/§3/§4/§6）、iteration-design.md（写作硬规则/§7）、源迭代 supply-selection 的 design.md + details/supply-value-spec.md + landing.md + README.md、math_proofs.md P42 行；代码真值按任务书清单逐符号直读；注册表/阵容统计类主张全部实跑复核（`uv run python`，PYTHONPATH=src）。
> 攻击纪律：数值/口径/引文/码点直调复核；篇内自洽与对得上宪法/注册表/裁定分开验；行号漂移按符号定位判。

## 1. 结论概览

**发现 5 项：阻断 0 / 重要 1 / 次要 4。** 无宪法违例、无核心数学错误、注册表与代码类主张绝大多数实跑吻合；1 项重要为「总持有账构成」在 design 内部与 landing 之间自相矛盾（两本 vs 三本），须统一后方可定稿。

## 2. 发现清单

### F1【重要】总持有账构成自相矛盾：三本账 vs 两本账

- **位置**：design.md §2.2（守卫注）与 §2.3（边界②）为**三本**；design.md §2.5 与 §2.1（`equip_tier` 的 `owned_total` 注）、landing.md §3.2（范围）为**两本**。
  - 三本：§2.2「持有数_total = 三本现成账合计（备用 `last_owned_equips` + 部署位 `tracked_deployed[*].equips` + 备战席 `tracked_bench_chars[*].equips`）」；§2.3②「总持有账零成本并入第三本账 `tracked_bench_chars[*].equips`（§2.2 已并入）」。
  - 两本：§2.5「两本账：①备用…②穿戴账 = 部署位 `tracked_deployed[*].equips`（…需求守卫与备用账合计）」；§2.1「`owned_total` = 总持有账（备用 + 已穿戴）」；landing 3.2「两本库存账传递（备用 = …；总持有 = 备用 + 部署位穿戴账 `tracked_deployed[*].equips`，经 `exec_state_of` 读）」。
- **凭什么**：五处原文直引；三个账号字段均实存（cw_strategy_session.py:167、cw_exec_state.py:154-155），矛盾不在数据可得性，在口径文本本身。
- **发作场景**：landing = 账本阶段唯一源，落地批照 landing 3.2 落**两本**合计 → 备战席角色身上骑装的 key 件不入守卫口径 → 恰好是 §2.3② 声称「已收窄」的入队瞬间缺口原样保留，且与 §2.2 定义节、行为表行 8b「合计口径」不一致；实现者按 §2.2 落三本则与唯一源 landing 相悖（写作硬规则 2 的停手点）。
- **修正方向**：全链统一**三本**（改 §2.5、§2.1 注、landing 3.2 各补第三本，与 §2.2/§2.3② 对齐）；若有意降为两本，则删 §2.3② 的「已并入/收窄」表述并同步行为表行 8b 的口径注。

### F2【次要】V2 修订版快照锚的计数单位未钉死（蓝钻/红钻：11 条配方引用 vs 12 槽）

- **位置**：design.md §2.1（`equip_material_generality` =「注册表配方引用计数」；锚「简易 10 条配方引用/11 槽」「蓝钻/红钻 12 槽」「垃圾袋 2 槽」）；landing.md §3.1 同句。
- **凭什么**：实跑 EQUIPMENTS 全量 recipes 枚举：简易 8 件每件 = 9 交叉 + 1 自对 = **10 条引用 / 11 槽**；蓝钻/红钻 = 9 交叉 + 1 红蓝交叉 + 1 自对 = **11 条引用 / 12 槽**；垃圾袋 = 2/2。锚面给简易两个单位、给钻只给槽位单位——若机器返「配方引用条数」（语义名所示），蓝钻 = 11 ≠ 锚面 12；若返槽位数，简易 = 11 ≠ 锚面「10 条配方引用」。锁断言「机器计数 vs 直查注册表计数逐名相等 + 快照锚」因此二义，实现者需自行裁决单位 = 写作硬规则 2 缺口（锁可能写红或写空转）。
- **发作场景**：3.1 落 V2 修订锁时单位选错 → 锁红（误报漂移）或锚值改写（锁失锚定力）。
- **修正方向**：钉死函数返回语义（建议 = 配方引用条数：简易 10 / 蓝钻红钻 11 / 垃圾袋 2 / 进阶 0），快照锚全按该单位书写，槽位数降为附注。该函数箱打分已不消费（audit-only），波及面小。

### F3【次要】§2.2 共享材料示例帧注册表错误（以牙还牙甲·特权 无 recipes）

- **位置**：design.md §2.2 守卫注「反甲白厄的 以牙还牙甲/以牙还牙甲·特权 共享材料帧钉此语义」。
- **凭什么**：实跑：全部 46 个变体条目（`·特权`/`白昼·`/`极·`）recipes 恒 `()`——以牙还牙甲·特权 无材料集，与以牙还牙甲无共享材料，该帧在注册表上不存在（值对标签错类）。∃未满足 K 的共享材料语义本身成立且有真实帧：反甲白厄的**幸运星** ∈ 以牙还牙甲(量产型装甲+幸运星)/高周波电锯(幸运星+折叠小刀)/热血沸腾拳(生命之花+幸运星) 三 key 共享。
- **发作场景**：语义锁照该帧构造 → 注册表上凑不出 → 锁写不出或锁了空语义。
- **修正方向**：换真实帧（幸运星三 key 共享帧）钉 ∃K 语义，或加注「变体无配方、不入材料档」。

### F4【次要】§2.3② 缺口「纠正通道」高估：合并/对账纠正不了入队瞬间缺口

- **位置**：design.md §2.3②「残余缺口收窄为入队瞬间的写端缺位……直至首次合并/对账/部署纠正」。
- **凭什么**：①bench 装备机制不可读：cw_bench_equips.py:3-5「未上阵角色不显示装备 icon(机制盲区)」、battle_prep_recognizer.py:141/:195「备战席无 below icon → equips 恒 []」→ 对账续接（cw_reconcile `_merge_equips`：按 char_id 把**旧 tracking** equips 续接到新读对象）没有新信息可吸收；②合并继承（cw_merge_simulate.py:268）只把各副本**已记账** equips 拷给载体（入队未记账 → 空∪空 = 空）。对入队缺口唯一有纠错力的写端 = 部署快照（cw_op_deploy `_snapshot_equips_into_tracking`）及随部署/换防的对象位移。第三本账的真实增量 = 「部署过又换防的角色的装备随账移动」，对商店自带装备形态在首次部署前恒为空。
- **发作场景**：审阅者/实现者按「合并/对账会纠正」理解 → 低估欠计数窗口（错提权暴露时长），观测键阈值与回炉判读失真。
- **修正方向**：纠正通道改述为「部署快照/换防位移」；「零成本并入第三本账」保留，但「残余缺口收窄」幅度按本条改写。失效方向申报（欠计数 → 错提权）与观测键挂账本身成立，不动。

### F5【次要】正本更新清单缺两处，末阶段「正本与实现一致」会静默失守

- **位置**：landing.md「正本更新清单」现仅 13_pick_family E18 / 08_events E18 / flow.py docstring 三行。
- **凭什么**：grep 实证另有两处正本行随本批过期——①`docs/develop/sr_od/application/currency_war/flow/screen_op.md:140`：「…`_pick_box_card`:OCR 卡名→`decide_box_card`/材料通用性回落」——回落改 `pick_equipment` 后「材料通用性回落」过期；②`strategy-docs/16_evaluation_tables_reassessment.md:77`：PICK_BIAS 平表行「E17 星徽秘典/E5 圣杯试炼/E18 武装箱」——box 两常数退役后枚举过期。
- **发作场景**：末阶段按清单清零即收尾 → 两处正本与实现不一致残留。
- **修正方向**：清单补两行，均 ← 3.2。

## 3. 攻过未破角度清单（实际攻击过且未击穿的面）

1. **注册表主张全量实跑**：简易 8 件每件 10 条配方引用/11 槽完全同值；蓝钻/红钻 12 槽；垃圾袋 2 槽（欢愉星徽双配方：红+袋、蓝+袋）；进阶类 0 引用（全部配方成员仅 8 简易 + 红蓝钻 + 垃圾袋 11 名）；自对配方恰 10 条（简易 8 + 红钻×2/蓝钻×2）；财富宝钻 recipes 三路（蓝蓝/红红/红蓝交叉——§2.3 只列自对、未误称全集）；COMP_LIBRARY 恰 20 套；重复 key_equips 恰 5 套且实名逐套吻合（昼神阿雅 2×反重力皮靴、狼尊欢愉 2×反重力皮靴、命运圣杯红A 2×动能激发剑、追击飞霄 2×火力风暴潮、专家桑博DOT 2×火力风暴潮）；key_equips 全体 ∉ mv 表；key 材料全体 = 8 简易名且 mv 最小 3；key∩材料双中叠加现行库零实例；反重力皮靴 effect「可叠加」在册；cw_comps「可含重复，如阿雅需 2 反重力皮靴」注在册——**§1.1 gap 4、§2.1、§2.2、§2.3 的注册表面全部成立**。
2. **现行打分行为与值域分离**：flow.py `decide_box_card`（:656-704）三项独立 if（+100/+30/mv）+ `effect_pick_bias` 恒 0.0（pick_bias.py:49-61 bias 从未被累加）实测；直击 {100}/材料 [33,37]（30+mv，key 材料全体 mv 最小 3）/通用 [0,7]（通用含表外 mv=0 与表内非本 comp 材料 mv 至 7）三段分离成立 → §2.2「档间序零漂移」命题前提成立；「argmax 严格大于、并列取先」与现行代码一致。
3. **base 平移表值逐点核对**：`_EQUIP_VALUE`（cw_events.py:712-750）max 6；风暴潮 6/皮靴 5/甲 4/鞋 4/电池 3、花/幸运星表外 0——行为表行 1/3/4c/7a/10 的 base 数值全部与表吻合。
4. **锚定两态化**：`pair_target_comp`（cw_intention.py:1076-1147）构造 Comp 确不传 key_equips（缺省空，cw_comps Comp 字段）→ 伪 comp 帧 key 提权结构性恒死；`target_comp` 写点全仓 grep 仅 flow.py:427 / engine_p2.py:143，带非空 key_equips 的写入均为锁定/引擎帧 → 行为等价（行 9）与「消除隐式依赖」的定性成立。
5. **库存账写端全景**：备用账两观察写端全量重写（prep_actions.py:416/:584，read_equips SIFT）+ 效果增量（cw_exec_state.apply_op_effect：PickBoxCard :338-345、ConfirmBox 等 :352-354、SellDeployed 装备返还 :335-337；**SellBench 确无装备返还面** :317-324）+ 穿戴 −1/穿戴账 +1（cw_op_equip_all.register_equip_worn :134-163，穿戴账记拖入件名 → §2.3① 欠计数通道成立）+ 部署快照（cw_op_deploy:959-1013，含布局未知态冻结守卫）+ 合并继承/对账续接（存在性确认，见 F4 的幅度修正）+ 确认到账（_overlay_confirm.py:61-63）——§1.2/§2.5 的账面清单如实。
6. **§2.5 防御注记**：prep_actions.py:211-216 在册裁定引文逐字相符、辖域（穿戴计划产出位、执行帧可现读）定性准确；开箱决策在执行链内闭环（`_open_box` 内联调 `_pick_box_card`；entry.py:461-467 发射位只发空 `PickBoxCard()`）→ 「发射后执行前漂移」失效面确实不存在，消费不与裁定冲突。
7. **行为表 12 行逐行推演**：行 7a（反甲白厄持量产型装甲：幸运星经 甲(装甲+星) 成 tier 2、生命之花经 拳(花+星) 落 tier 1；现行 33<37 选花 → 新制选星）；行 7b/7c 自对 cnt==1/cnt≥3 排除；行 8a/8b/8c 守卫（count 语义 need=2 帧）；行 2/2b/4a/4b/4c/10——全部与两制语义自洽，可锁。
8. **档序三段推导**：直击⊇近兑现的严格支配在字典序下结构成立（加法制反例论证成立，取舍表第 2 行有效）；近兑现>原料按「发展优先默认」+ P42 ①③ 仅作方向佐证、证据强度申报如实（math_proofs.md P42 行「近兑现张最贵，绝不喂」确为保留面结论，01_math_framework §3.6 同）——证据分级诚实。
9. **§2.7 sim 结构性不可见**：fake_match.py:763-794 `_pick_box_card` 无策略调用、card_idx None 恒取第 1 张；rules.py:176-186 箱选项 = 商店角色池名、落 BenchChar 入备战；`sim/` 全域 grep OpenBox/PickBoxCard/decide_box_card 零命中——「A/B 不可作本批判据、验证 = B 组单元锁 + 实机判读」成立，且符合 strategy-work §4 sim 可观测性申报门。
10. **旧锁处置面**：test_cw_material_score.py target_comp 锚（:17）+ 两条断言在 locked_comp 重锚后语义保持（幸运星 tier 1、直击 tier 3 均成立）；test_cw_screens_ops.py 恰两把 material_value 锁（:77 手表值锁/:99 回落行为锁）与「退役/重锚」处置一一对应；test_cw_obs_arch_prep_writeflow.py 扫描锚（:360-388 断 `_default_box_card` 源码含 `decide_box_card`/`board_state_of(`）在 3.2 后 match 分支仍委托策略层 → 「锚不受影响」判断成立；test_cw_box_pick_arm / test_cw_box_open_pick_merged 为发射臂/机械链锁，不涉打分。
11. **material_value 全仓退役前提**：src/ 生产消费 grep 恰两处（flow.py:701 主路径、prep_actions.py:1161 局外回落）+ pick_bias.py:32 注释与各 docstring 引用均在 landing 3.2 文件面内 → 「两处消费退出后删除」可成立，grep-zero 判据可达。
12. **共享机器与消费位接线**：六消费位清单与源 spec §1.3 迁移表逐位对表（supply/box/wear/planner/engine_p1:2840/ledger:1540/:1606 私有 import 坏味实存）；3.1 期 ② 不换源保 argmax 基线、V2 修订的互斥前提（注册表等值 vs 手表梯度）实跑证实；mandate_v1/bridge.py 无 decide_box_card 覆写；key_fit_names 改由 key_recipe_pairs 派生 + V4 独立第二构造对拍自洽。
13. **治本核验（核三）**：§1.3 归层（语义层缺维 + 锚定错位 + 表示层过期值）成立；§2 修在价值模型与锚定契约本体，非症状补丁；跨件半问第三件以族级清点处置——剩余六位（decide_encounter/megastar/partner/star_tome/wish_trial/planner，flow.py:537-672 逐位 grep 吻合）价值语义各异，归口 OQ-3 扩容/族级迭代并声明不第四件盲修，符合根源两问与跨件半问纪律。
14. **规范遵循（核二）**：iteration-design 四件齐、landing 三阶段小节七件齐、README 与模板吻合、状态位一致（草案/对抗进行中/0-3）；写作硬规则 1 依据就地标注抽验全命中（含 flow.py:405-410 ADR-0357 注、cw_strategy.py:206-208 契约签名、board_structure.md:61「4 选 1 装备」、equipment_mechanics.md §1.1/§3/§4 唯一标记恰 3 组、`docs/game/currency_war/data/equipment.md` 经 git 确认已删除）；无过程叙事；零调参宪法——全案无新拍值（tier 为纯序数载体、base 全量平移、需求件数/持有数均为注册表/state 定义量）、无开关；prereg 完整性硬门不适用（非修复批，sim 结构性不可见已申报）；strategy-work 锁存在性纪律——新锁均引 design §2.6 行号出处、旧锁处置均给语义重推理由。
15. **遗留小注**（不构成发现）：tier 序数值 3/2/1/0 未显式引 ADR-0524 定序族/禁读基数声明——字典序消费结构上读不到基数，建议落码时在机器模块头补一句定序声明即可；§2.5「（候实证）」措辞含混，建议改「待实证」。

## 4. 纪律执行附记

- `attack.md` 未打开；执行内容 grep 时其 4 行片段（验证类确认）被意外带入上下文，均与本轮独立完成并已记录的核对项重合，未引入任何发现方向（F1-F5 均在泄露前已成形并有独立证据）。
- 数值类主张（注册表计数/阵容统计/表值）全部脚本实跑；文本引文逐处直读原文；行号漂移处均以符号定位判定，未单独立发现。
