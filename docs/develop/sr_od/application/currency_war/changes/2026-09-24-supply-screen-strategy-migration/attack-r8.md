# 设计对抗报告 · 第 8 轮（attack-r8）

> 审查日期 2026-09-24。无前提独立审查：攻击对象 = 本目录 design.md / landing.md / README.md（当前工作区状态，r7 修订后的文本）。判据源自取并全部直调复核，未采信任何前轮报告结论。规范源：docs/develop/harness/iteration-design.md（四硬规则/§7 三核/阶段七件/正本清单）、.dsh/skills/sr-od-currency-war-dev/references/strategy-work.md（§1 零调参/§4 验证阶梯与可观测性声明/§5 单帧测试/§6 对抗纪律）、strategy-docs/00_framework.md（宪法五/六）、项目 AGENTS.md。行号锚按任务纪律以符号锚优先，±3 漂移且语义锚成立者不登记。

## 发现清单

### R8-1 [中] sim-redesign 批日期错标，交接指针解析到不存在的批次（核一·引用锚存在性 + 核二·硬规则 4）
- **位置**：design.md:105（§2.7「**sim-redesign 批（2026-09-23）**在册复用面交接：其 design 声明 kernel `decide_supply` 为复用面（该批 design.md 三处）」）。
- **发现**：直调 changes/ 目录全集，声明 `decide_supply` 为复用面的批次是 `changes/2026-09-15-sim-redesign/`（design.md :70 复用面清单「decide_event/decide_encounter/decide_supply 等」、:104 M18 表行复用面列、:267 M18 节「复用面：kernel/cw_events.decide_supply」——「三处」复用面声明本身核对成立），29 批 landing:33 引用同批亦写作 2026-09-15。现稿日期标签「2026-09-23」指向的实为 `changes/2026-09-23-sim-backend-unification/`——直调该批 design/landing/details 全文 grep `decide_supply` **零命中**，该批并无此复用面声明。交接申报的收件方按现文会解析到错误批次（任务面已被误导过一次），「三处」核对不过则交接义务落空。
- **修正方向**：:105 日期改为 `changes/2026-09-15-sim-redesign`（可附 :70/:104/:267 三处锚）；「三处」计数核对无误可保留。

### R8-2 [中] 「三级全空」对裁定「存在任一非末级项」的解读被包装成「直接推论」，实际存在相反读法且分歧帧行为实质（核一·依据错标 + 核二·strategy-work §1）
- **位置**：design.md:65（三级全空定义「装备级全体落 tier 0（用户裁定 2026-09-24：字典序下『存在任一非末级项』= 值得拿）」）、:68（「这是裁定结构（『值得拿』= 非末级项）的直接推论」）；对照 :53/:57（装备轴 = (tier, base) 字典序，同 tier 按通用值定序）、:92 锚③。
- **发现**：装备轴按设计自己的定义是 (tier, 通用值) 双键字典序，则该轴的「末级项」自然读法 = **tier 0 ∧ 通用值 0**（全序最底），「存在任一非末级项 = 值得拿」在该读法下蕴含「tier 0 但通用值 >0 的帧**不**属于三级全空 → 不刷」；设计取的却是「只看 equip_tier、通用值不参与」（:68），两读法恰在 tier 0 高通用值帧上给出相反行为——火力风暴潮（通用值 6，EQUIP_GENERIC_VALUE 表自注「伤害征服核心乘区，最高优先」）所在的无钻无角色帧，按现稿口径**被刷掉**。设计引文自身（裁定原句）不足以唯一确定「末级」定义，「直接推论」的定性把一个解释选择表达成了必然，超出引文可支撑的强度。锚③（含 tier 0 高通用值件帧仍刷）+ 与旧制同域申报是有效缓解，但锚是「验证已选解读」不是「解读合法性依据」。
- **修正方向**：①:68 把「直接推论」降格为显式申报：「『末级 = tier 0（通用值不入阈值）』为本设计对裁定结构的一种解读，与『全序末项』读法在 tier 0 高通用值帧上分叉，解读分歧由实机锚③对账」；②30 号稿裁定登记（§2.7）收录裁定原文（或向用户确认「末级」定义），使该解读可审计；③锚③ 对账目的改写为「验证该解读」而非「刷不视为异常」。

### R8-3 [低] §2.1 与 §2.2 对「消费的 kernel 符号」表述不一致（核一·篇内一致性）
- **位置**：design.md:32（§2.1「`supply.py` 消费 kernel `equip_tier`/`same_star_count`/`GameState` 读口」）对照 :53（§2.2「装备轴打分单一源 = **直调共享机器 `cw_equip_value.pick_equipment`**……不另写打分」）与 :103（16 号稿替锚「`EQUIP_GENERIC_VALUE` 表本体现址……本批保留为定序常数源」）。
- **发现**：§2.2/§2.7 定单一打分入口 = `pick_equipment`（`equip_tier` 是其内部件，直调方无需也不能分开调）；§2.1 的消费清单却写 `equip_tier`。实现者若按 §2.1 直调 `equip_tier` 自建排序，恰好落进 §2.2 明令禁止的「另写第二套打分」。同一语义两节给的符号名不一致。
- **修正方向**：:32 改「消费 kernel `pick_equipment`（内部 `equip_tier`）/`same_star_count`/`GameState` 读口」。

### R8-4 [低] 13 号稿 §0 fallback 纪律两处引用与该纪律字面辖域错位（核一·依据就地标注）
- **位置**：design.md:46（空候选帧「与旧码及 13 号稿 §0 fallback 纪律一致」）、:52（char 读缺「不进角色候选——不猜，沿 13 号稿 §0 OCR 未就绪纪律」）；对照 13_pick_family.md:11（§0 原文「OCR 未就绪位（选项 char_id 空）的接口按 fallback（idx=0）执行并标注」）。
- **发现**：§0 纪律的字面辖域 = 「选项 char_id 空的接口按 fallback idx=0」。两处引用均不逐字合位：(a) 空候选帧（options 为空）不是 §0 所指的「char_id 空位」，idx=0 兜底实为旧码自身行为（cw_events.py:627-628）；(b) char 读缺的处理（不进角色候选、仍参与装备轴）与 §0 字面的接口级 idx=0 退化形态**不同**——设计取了该纪律的「不猜/保守降级」精神但偏离其字面形态，引用却写成「沿纪律」。依据与结论的对应关系两处都偏松（行为本身安全合理，问题在标注失真）。
- **修正方向**：两处引用改述为「取 13 号稿 §0『OCR 未就绪不猜』的保守降级精神（字面 idx=0 形态不适用本接口）」；(a) 处依据改挂旧码行为（cw_events 现址）。

### R8-5 [低] `SupplyOption` 字段 docstring 的旧决策语义漏出注释收口清单，与「已知点全列」申报相抵（核一·边界完整性 + 核二·硬规则 4）
- **位置**：design.md:80（§2.6「注释指针收口（**已知点全列**；末阶段另有全仓复扫兜底）」）对照 cw_events.py:588-592（`SupplyOption` docstring：「has_diamond:带红/蓝钻(视觉判定;**钻 = 拿到基本赢,碾压一切**)」「equip:装备名(OCR;**`key_equips` 契合 + 通用价值排序用**)」）。
- **发现**：`SupplyOption` 按设计留 kernel（§2.1），其字段 docstring 的两句决策语义描述（钻支配旧口径、equip 字段的旧打分用途）随迁移全部过期；该块属设计已两引的已知面（§2.1 :33 与 §2.6 :77 都锚过 ：585-596），却不在收口清单的 7 个已知点内。全仓复扫兜底大概率能捞到，但「已知点全列」的申报被此块证伪。
- **修正方向**：:80 收口清单补 `cw_events.py:588-592`（改写为观察载荷语义，决策语义归 30 号稿指针）。

### R8-6 [低] 16 号稿 ：74 挂账行的重写规格不完整，中段改形序措辞无映射答案（核一·实现者无需再设计）
- **位置**：design.md:103（§2.7「16 号稿 :74 行：本批即其在册改形的执行批——挂账销账；行内死引用替锚……；『带钻支配（零参数已就位）』定性与 30 号稿对齐」）对照 16_evaluation_tables_reassessment.md:74（在册改形序「带钻支配（零参数已就位）> **key_equip 命中** > 功能定序」）。
- **发现**：在册改形序与落地形结构不同——落地形插入了角色轴（第 2 级），`key_equip` 命中降为装备轴内的 tier 3。重写指令只覆盖三件事（销账/死引用替锚/带钻支配定性对齐），未说明行内中段「key_equip 命中 > 功能定序」措辞如何映射到新结构：部分改写（只动带钻支配定性）会留下「key_equip 命中为第二优先轴」的表述，与 30 号稿三级序相抵。
- **修正方向**：:103 补一句「该行优先序表述整体按 30 号稿三级序改写：带钻支配 = 第 1 级定性；`key_equip` 命中 = 装备轴内 tier 3（第 3 级内部）；角色轴为其上位档（第 2 级）；功能定序 = 通用值定序常数」。

## 实际攻击过的面清单（全部直调复核，值/锚逐一对源）

1. **cw_events.py 补给段全锚**：`decide_supply` :616-647、`SupplyPick` :599-605、`SupplyOption` :585-596、`_equip_value` :609-612、段头 :583、`EVENT_PICK_TYPES` :1003、`EventPick` :1007、模块 docstring :1、`char` 不参与评分（:616-647 只消费 equip/has_diamond）、+10（:642）、刷新判据 :633-635、key_fit 消费 :637/:641-642、`_equip_value` 仍被 planner 消费 :786——设计删除面/保留面逐锚成立。
2. **cw_equip_value.py**：表自注 ：36、表本体 ：42-80、`equip_tier` :163-189（3/2/1/0 语义与模块头一致）、`pick_equipment` :192-210（(tier, base) 字典序、并列取输入序先、key_equips 可含重复按计数）、模块头「禁第二套打分」裁定引用——全部成立。
3. **消费方面**：`SupplyOption` 五方（cw_node_obs.py:21/:215 三钻集/:206 陈旧注；cw_game_state.py:114 TYPE_CHECKING/:209 域版本 2/:2283 supply 字段/:2210-2229 溢出位；supply_node.py:16/:41；cw_sim_backend.py:78/:573-585 恒置一带钻槽；测试仓 test_cw_route_clear/test_cw_screen_report_ports）；`SupplyPick` src 零外部类型 import + cw_vocab :728/:915 + cw_pick_supply_action.py:37 + 测试仓 test_cw_unified_action_4.py:27-33/:303（全仓 grep 复核无遗漏）。
4. **flow/invest_env/intention**：flow.decide_supply :537-552（闸前移 :544-545、内务 ：546）、`_consume_prep_direction_frame` 兄弟入口同款、`_refresh_direction_views` :326/:327/:335-352/:353（P1 物化臂、伪 comp `pair_target_comp` key_equips 恒空 = cw_intention.py:1185-1194 构造未传该字段）、decide_box_card 先例 ：712-718/:719-740/:728-731（展平 `*_wf, *_wb`）、`invest_env.decide` 闸内嵌 ：388-401（None fail-closed）、降格清锁 cw_intention.py:2075-2077、`line_value` 降格未锁口径（line_value.py:16/:62）——全部成立。
5. **凑星判据机器**：`same_star_count` :424-433、合成规则 :337、`_entry_identity` fail-closed（:93-107，二元组直传静默跳过实证）、`bench_units_of`/`deployed_rows_of` 形状（cw_game_state.py:3645/:3654，前者返回 list[Unit] 可直喂计数族）、补给入席恒 1★（pick_supply.py:48-50）——设计的入参形状与失真分析成立。
6. **op 层语义**：cw_screen_supply_node.py :8-14/:39-40/:242-245/:272-280 各陈旧注、重调路径唯一触发面推演（闸内嵌后 ：276-288 行为逐分支核）、sim 补给屏在产分发（cw_sim_backend.py:832/:880/:1250-1253 + flow-seam 金路径清单含补给）——「op 零行为改动、仅注释收口」申报成立。
7. **死代码与退役面**：`supply_reroll_decision` :46-56 src+测试仓 grep 零消费、唯一 import 点 cw_events.py:552 只取 `encounter_tier_score`、cw_survey19_hooks 模块头 ：1-8；`sim/checks/ledger.py` 与 `check_equip_value` src+测试仓零命中；`cw_replay.py:10-12` `--diff` 退役、回放面只辖商店——三项删除/豁免申报成立。
8. **文档面锚**：25 号稿 :3-4/:11/:18（辖 11 屏清点核对）、13 号稿 :20/:40（「组件/成品需求」与实码不符核实）、08 号稿 :19（E4 行结构与替锚文本核对）、16 号稿 :74、strategy-docs/README §2 分篇表、screens/supply.md :12/:33/:40/:63/:80/:88、docs/game/screens 两份 :19/:37/:39/:57/:32——全部存在且过期描述属实。
9. **跨批协调**：env 批/29 批「明确不解决」登记补给迁移（两批 design 实文核实）；29 批 landing:32-33（decide_event 约 270 行删除、flow.py/cw_vocab.py 双批编辑面、13 号稿增补共用判据节、行号锚漂移重核义务、sim-redesign 批改指先例）与本批 §2.7 表述逐条对上；29 号稿编号占用（29 批 landing 3.3 规划件）；宪法五/六先例（env 批 design:5、00_framework §1 第 5/6 条）。
10. **宪法/纪律符合性**：零调参（新判据零自由参数、+10 死、通用值表保留 = 16 号稿 §1.8 在册处置 + 本批仅消费申报）、未证即退役（带钻支配论证留 E4 批的边界申报）、验证阶梯（sim 可观测性声明 + 占位分布盲区申报 + 实机锚事前写定 + cw_replay 豁免依据）、验收线保全盘点（三入口申报 + 全 progress 抽查未见以补给选择为判据面的在册验收线）、单帧测试 9 项与 design §2.2-§2.5 逐条映射、landing 七件套/末阶段/正本清单、README 模板与链接存在性（attack.md…r7 在册）、硬规则 3（design/landing 无「第 N 轮/已改」叙事）、行为变化申报 ①-⑤ 与锚 ①-⑤ 篇内一致性互核、核三治本（根因归层成立；修复 = 迁移 + 模型重建非症状补丁；逐画面推进 = 宪法六裁定节奏非逐件修）。

## 结论

6 项发现（中 2 / 低 4）。两项中级均为申报/引用面的定性错误（批次指针错标、裁定解读的依据强度超claim），不动摇方案结构；四项低级为清单完备性与引用精度。设计主体（迁移结构、三级字典序、闸内嵌、删除面、测试面、验证申报）经全量直调复核无实质缺陷。
