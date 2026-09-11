# sim 基线校准、账本立卡与宝钻联动（详设：T-21 / T-22 / T-23）

## 问题与约束
本篇辖三批，均在 sim 域（engine_p1.py / runner.py / ledger_hooks.py），三批间文件面互斥按 landing.md 排布（T-21 ↔ T-23 共 engine_p1.py，T-22 ↔ T-23 共 runner.py）；任一批改 sim 行为 → 总纲 IC-3 段表登记/池指纹申报。权威源声明（防偏离门解锁一）：开局金/首收入/back 容量的权威源 = 生产注册表与玩法研究档，见各批小节。

### T-21 开局金/首收入校准（旧账 T-220）
- **根因归层**：语义层——sim 适配面开局金/首收入注入语义与生产注册表真值缺口（适配语义漂移，非机制缺陷）。
- **症状**：假环境开局金/首收入语义存在真值缺口——T-209 G1 定性 + 落地审立项建议，归 env 权威批族（依据 = 旧账 T-220 卡）。
- **权威源**：开局经济真值 = 生产注册表 `kernel/cw_economy.py`（BASE_INCOME / REWARD_BASE_GOLD_BY_ROUND / streak_gold / 利息封顶）+ docs/game/currency_war/research/economy.md §10/§11（机制与凭据，值只读注册表）。
- **修法**：sim 注入侧（engine_p1.py 开局帧构造与首轮收入段）逐字段对权威源校准；语义差异逐条列表（字段 / sim 现值 / 权威源值 / 出处）落交付报告，属注册表错的报编排者另立（禁在本批顺手改注册表——本批辖域 = sim 适配面）。
- **对拍锁**：sim 开局金/首收入 vs 注册表直算值的对拍测试锁（同输入同输出，覆盖平局/连胜/利息三通道）。
- **改动面**：sim/engine_p1.py（开局金注入、首收入结算段）；与 T-23 共文件，排 T-23 之前。

### T-22 P-2 假环境账本立卡（旧账 T-273）
- **根因归层**：语义层——「plan 成本 vs 实扣」容忍缺口的合法差/真漏账语义边界未定谳（语义边界缺失，非记账实现错）。
- **症状**：「plan 成本 vs 实扣」既有容忍缺口——删除波 1 落地审 P-2 登记的 sim 账面缺口（依据 = 旧账 T-273 卡）。
- **修法（定谳先行）**：
  1. **定谳段**：亲读 sim 账本行的 plan 成本与实扣记录链（sim/ledger_hooks.py 埋点 + runner.py 账本行 schema），把容忍缺口逐形态归因（免费刷新/折扣/退款等合法差 vs 真漏账），结论落交付报告；合法差形态在账本行 schema 注释声明口径，真漏账形态立修复项回编排者。
  2. **立卡段**：按定谳结论在 sim 账本位立常设检查卡（ledger 行校验：plan 成本与实扣差超容忍即账面红），容忍值 = 定谳结论给出，禁拍定（差值容忍须由合法差形态枚举推导）。
- **改动面**：sim/ledger_hooks.py、sim/runner.py（账本行 schema/校验位）；结论落档交付报告。与 T-23 共 runner.py，排 T-23 之前。

### T-23 sim 宝钻注入联动 + back_size 死字段处置（T-322 申报①）
- **根因归层**：语义层为主——sim 合成口缺宝钻容量计数语义；叠加表示层残留——back_size 死字段 = T-322 值源切换半途的表示残留（闸门三保留未清除）。
- **症状**：back_max 四类消费切当前局面容量（T-322 四闸门，已入库 04b8078ca）后，sim 侧宝钻格数联动未做（涉 A/B 基线，T-322 申报①候立项）；`snapshot.back_size` 成死字段（T-322 闸门三保留钉死，候联动批处置）。
- **值源**：宝钻 = 财富宝钻，官方效果原文「拥有宝钻可以使团队规模上限+1，无论是否被角色穿戴」+ 装备者每 3 备战阶段 1 金（cw_equipment_data.py:53，每颗+1 可叠加、局内只增不减）；容量裁决通道 = T-322 闸门二 `resolve_back_slots` 收尾写容器（obs/cw_back_layout.py）。
- **修法**：
  1. **宝钻联动**：sim 合成口补宝钻计数项——back_layout 合成（T-322 闸门二B 增补的 sim 合成口第八域）纳入宝钻持有数 ×1；生产合成口值计算（obs/cw_back_layout.py resolve 段）若缺宝钻计数同批补齐（值计算语义，非观察结构，域边界见总纲 §2）；
  2. **back_size 死字段处置**：mandate_v1/contracts.py、adapter.py、decision_assembly.py、kernel/cw_prep_actions.py、operations/cw_screen/cw_screen_prep.py、sim/runner.py 的 back_size 透传/消费位随联动一并处置（删除或收敛到容器真值单源）；**禁制造第二值源**（T-322 闸门三钉死语义）；若处置面撞 W6 决策面切换在飞 → 停手回路由。
  3. **A/B 基线锚申报**：本批改变 sim 行为，按 IC-3 交付段表登记/池指纹申报；既有 A/B 段的可比性中断面在申报中显式声明。
- **改动面**：sim/engine_p1.py（合成口）、sim/runner.py（back_size 位）、obs/cw_back_layout.py（仅值计算段，若需）、mandate_v1/contracts.py / adapter.py、decision_assembly.py、kernel/cw_prep_actions.py、operations/cw_screen/cw_screen_prep.py；锁面更新 + CW 子集绿。单源事实（闸门二/三语义）见 T-322-实施-交付报告.md——落盘正本 = 同迭代 details/sources/（原始出处 .debug/temp/ 易失）。

## 方案（实施序）
1. T-21 → 2. T-22 → 3. T-23（T-21/T-22 与 T-23 的文件面互斥串行；T-21/T-22 互不依赖可任意序，但同为 sim 基线语义批，编排者宜单跑道顺序派）。

## 关键取舍
- **校准先于联动**：T-23 在 engine_p1 合成口叠加新计数，若开局/收入基线未校准，联动后的 A/B 读数把两类改动混在一起无法归因——先固定基线再加联动。
- **死字段随联动处置、不独立立项**：back_size 的死因就是值源切换未完成（T-322 闸门三只保留未清除），与宝钻联动同属「sim 侧追平容器真值」一个语义面，拆两批会两次触碰同一批文件。
- **定谳结论不进 ADR**：T-22 容忍缺口语义定谳 = 交付报告 + 账本行注释（GC-4）；「立卡」是 sim 账本检查位，不是任务账本操作。
