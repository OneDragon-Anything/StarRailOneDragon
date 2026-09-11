# 旧账卫生与运维收编 落地

> 阶段 = 账本任务的追认式映射：每阶段对应一个已立账本任务（T-\<N\>），完成判据 = 账本 criteria 预注册原文（阶段小节不改写判据；设计改 → 本文件改 → 账本 note/criteria 跟改）。阶段间依赖 = 账本共同前置 T-33 之外的真实排布：语义单源依赖（标注「单源依赖」）或文件互斥排序（标注「互斥排序」），**全部边收录于 design.md §3「账本依赖边清单」并一一对应**（账本落账 = 账本动作申报，由编排者执行）。wait 态阶段的外部条件与复查时机显式写入，不虚设开工态。
> 通用工程门 = design.md §2 GC-1..GC-4（各阶段完成判据统一引用，不再逐条复述）。

## 3.1 工具死引用微修（账本 T-19）
**范围**：tools/cw/review_skeleton.py 对 merge_round_rows 的死引用修复；亲跑复现通过。明确不含：任何复盘语义改动（零行为工具面修复）。
**设计依据**：design.md §2「T-19 内联设计」。
**文件面**：tools/cw/review_skeleton.py。
**依赖**：无（T-33 之外）。
**优先级建议**：2
**完成判据**（=账本 T-19 criteria）：
- merge_round_rows 死引用修复
- 工具亲跑复现通过
- GC-1..GC-4
**验收凭据形式**：亲跑命令输出（脚本成功执行到骨架产出）+ ruff。

## 3.2 悬空 ADR 引用清理（账本 T-24）
**范围**：ADR-0648/0649/0650/0653 删除笔残留引用全仓清零（记账时点 20 处/11 文件，定稿时点实测 25 处/12 文件——不含本迭代 attack.md 自引；以开工时 grep 重跑为准，docs + src 注释面），处置口径 IC-5。**扩围面（账本 T-24 附注 2026-09-11T23:59:17）：正本到 .debug 的悬空引用清单（引用目标文件已灭失——math_proofs/projection_contract/flow 多处）一并覆盖，清单 = reports/T-30-r1.md 第 4 节**。明确不含：ADR 重建、ADR 历史原文改动、语义勘误（引用处只改引用形态，不顺手改内容）。
**设计依据**：details/docs-hygiene.md §T-24；design.md §2 IC-5。
**文件面**：docs/develop/currency_war/strategy-docs/{11,19}*.md、changes/2026-09-11-unified-state/details/recovered/T-320-决策行文件schema设计.md、src 命中文件（telemetry/recorder.py、telemetry/match_archive.py、operations/cw_loop.py、kernel/cw_board_state.py、mandate_v1/shop.py、mandate_state.py、criteria/{contracts,equipment,__init__}.py——以开工时 grep 重跑为准）。
**依赖**：账本 T-30 done（recovered 文件互斥；边见 design.md §3，T-30 已 done 记边固化排布）；GC-1 留树面对账（src 命中文件多处在飞，开工前逐文件核对，不预写快照）；互斥排序：先于 3.8/3.9（共 shop.py）与 3.3（共 doc 树），边见 design.md §3。
**优先级建议**：2
**完成判据**（=账本 T-24 criteria）：
- git grep -E 'ADR-0648|ADR-0649|ADR-0650|ADR-0653|0648-p92|0649-equipment|0650-cw4|0653-m2b' 全仓 0 命中
- ruff + 受影响测试绿
- GC-1..GC-4
**验收凭据形式**：grep 0 命中输出 + ruff/测试输出。

## 3.3 CW 文档树迁移（账本 T-25）
**范围**：docs/develop/currency_war/ 整树 git mv 至 docs/develop/sr_od/application/currency_war/；77 处 proofs 引用路径错层随迁修正；全仓引用面同步含本仓 skill 本体（skills/sr-od-currency-war-dev，junction 挂载 `.dsh/skills/sr-od-currency-war-dev`；SR 专属 skill 单源在本仓，公共仓 OneDragon-Skills 无此 skill）。明确不含：docs/game/currency_war/（不迁）、changes/ 目录（已在址）、文档内容语义改动。
**设计依据**：details/docs-hygiene.md §T-25；design.md §2 IC-4。
**文件面**：docs/develop/currency_war/**（迁出）、docs/develop/sr_od/application/currency_war/**（迁入）、主仓引用面文件、本仓 skills/sr-od-currency-war-dev/**（单仓单笔 commit）。
**依赖**：3.2（doc 树互斥排序，边见 design.md §3）；账本 T-29/T-30 终态（changes/ 找回面落定，防新文档落错树；边见 design.md §3）；互斥声明：执行期间与一切写 docs/develop/currency_war/** 的批排他。
**优先级建议**：2
**完成判据**（=账本 T-25 criteria）：
- docs/develop/currency_war/ 整体迁 docs/develop/sr_od/application/currency_war/
- 77 处 proofs 引用路径错层随迁修正
- sr-od-currency-war-dev skill 内路径引用同步
- 迁移后旧路径全仓 0 引用 grep 锁
- GC-1..GC-4
**验收凭据形式**：git mv 后 git status 对照（rename 检出）+ 旧路径 grep 0 命中输出 + 单仓 commit hash（skill 本体在本仓，无第二仓）。

## 3.4 simulate 落洞 churn 重排治本（账本 T-17）【三层已由 T-308 入库，本阶段 = 残余收尾】
**范围**：三层方案（S2 写回槽位表+健康门 / S1 四点下标直拷 / S3 epoch 通道）与顺路面三件**已由旧账 T-308 落码批入库**（主仓 bd27989d4，2026-09-11 12:42，7 文件 +203/−33；测试仓 377b61889ae0，3 文件新锁 15；落地审 reviews/T-308-落地审.md accept；方案正本 = T-280-交付报告.md §③ v2 修订版，落盘见 details/sources/）。本阶段辖残余四件：① **T-308 落地审 P3 残余小修**——cw_reconcile.py 健康门拒绝分支 sorted 混型防御面 + 返回值 docstring；② **「连续批跑 0 例降级 WARNING（前值 2 例）」正式取证**——sim 批，**挂 sim 门后执行（design.md §2 编排者裁决原文），不构成 W6 前置**；③ 同型 visit 实机回归 0 例（候实机窗）；④ T-308 已交付凭据（两例重放锁逐字节 EQ / 新锁 15 / 107 passed）与账本 criteria 对账记档。明确不含：三层方案重做（已入库，禁零 diff 白批）、观察结构改动、策略语义（零策略语义）、math_proofs 增行。
**设计依据**：details/execution-seam-projection.md §T-17（按 T-308 后世界态重写）；design.md §2 跨迭代互斥（T-17 残余修复先于 W6 + sim 门辖域裁决）。
**文件面**：kernel/cw_reconcile.py（P3 小修）+ 测试仓锁面（若取证需补锁）。已入库面（bd27989d4：cw_reconcile.py S2/S3 段、cw_exec_state.py、cw_op_buy_cards.py、cw_shop_action_ops.py、ADR-0646、decisions/INDEX.md、flow/projection_contract.md）禁重触；cw_state.py 零触碰（T-308 交付收窄）。
**依赖**：GC-1 在飞面开工前核对（不预写快照结论）；互斥排序：先于账本 T-16（单源依赖 IC-2，边见 design.md §3）；时序主张：**T-17 残余修复先于 unified-state W6 开工**（r5 §2 窗内；「先于 W6/W7/W8」旧主张已废止，见 design.md §2）；批跑取证段候 sim 门（state 链全 done）。
**优先级建议**：4
**完成判据**（=账本 T-17 criteria；括注 T-308 兑现状态）：
- 对账 churn 事件接投影链（跨 reconcile/投影两域独立批）——已由 T-308 兑现（S3 epoch 通道 + 播种期快照 + 单动作循环检差三步入库）
- 修复后连续批跑 0 例降级 WARNING（前值 2 例实证）——残余①②，候 sim 门正式取证
- 行为锁——已由 T-308 兑现（新锁 15，107 passed）
- GC-1..GC-4（验证设计①-⑤：两例重放转锁全 EQ 已交付、写回 pad 态形状锁含健康门拒绝路径已入库、S3 epoch 事件锁已入库、同型 visit 实机回归候实机窗、SIFT 读链 slot 写点亲读结论已落 ADR-0646；P3 小修随残余批补齐）
**验收凭据形式**：残余批交付报告（P3 小修 diff + 批跑 WARNING 计数对照（前值 2 → 0，候 sim 门）+ criteria 对账记档 + ruff）。

## 3.5 开局金/首收入校准（账本 T-21）
**范围**：sim 注入侧开局金/首收入逐字段对权威源校准 + 差异清单落档 + 对拍锁。明确不含：生产注册表改动（注册表错报编排者另立）。
**设计依据**：details/sim-baseline.md §T-21。
**文件面**：sim/engine_p1.py + 测试仓对拍锁。
**依赖**：无（T-33 之外）；互斥排序：先于 3.7（共 engine_p1.py，边见 design.md §3）；GC-1 在飞面开工前核对（不预写快照）。
**优先级建议**：3
**完成判据**（=账本 T-21 criteria）：
- 假环境开局金/首收入语义真值校准（归 env 权威批族）
- 对拍锁
- GC-1..GC-4 + IC-3（基线锚申报，若校准改变 sim 批跑读数）
**验收凭据形式**：字段差异清单（sim 现值/权威值/出处逐条）+ 对拍锁绿。

## 3.6 P-2 假环境账本立卡（账本 T-22）
**范围**：plan 成本 vs 实扣容忍缺口语义定谳（合法差 vs 真漏账逐形态归因）+ sim 账本位常设检查卡。明确不含：真漏账形态的修复落码（定谳后报编排者另立）。
**设计依据**：details/sim-baseline.md §T-22。
**文件面**：sim/ledger_hooks.py、sim/runner.py（账本行 schema/校验位）+ 结论落档交付报告。
**依赖**：无（T-33 之外）；互斥排序：先于 3.7（共 runner.py）；GC-1。
**优先级建议**：2
**完成判据**（=账本 T-22 criteria）：
- plan 成本 vs 实扣容忍缺口语义定谳 + sim 账本位立卡处置
- 结论落档指针
- GC-1..GC-4（容忍值 = 合法差形态枚举推导，禁拍定）
**验收凭据形式**：定谳结论文档 + 检查卡锁（构造超容忍样本翻红）。

## 3.7 sim 宝钻注入联动 + back_size 死字段处置（账本 T-23）
**范围**：sim 合成口补宝钻计数项（值源 = cw_equipment_data.py:53 官方锚）；back_size 死字段六文件处置（收敛容器真值单源，禁第二值源）；锁面更新。明确不含：观察读面结构改动、W6 决策面切换（撞面即停手回路由）、A/B 历史段补采。
**设计依据**：details/sim-baseline.md §T-23；design.md §2 域边界（obs/ 只动值计算）。
**文件面**：sim/engine_p1.py、sim/runner.py、obs/cw_back_layout.py（仅值计算段，若需）、mandate_v1/contracts.py、mandate_v1/adapter.py、decision_assembly.py、kernel/cw_prep_actions.py、operations/cw_screen/cw_screen_prep.py + 锁面。
**依赖**：3.5（engine_p1.py 互斥排序，边见 design.md §3）、3.6（runner.py 互斥排序，边见 design.md §3）；单源依赖：T-322 闸门二/三语义（合成口第八域契约、back_size 保留钉死语义，见 T-322-实施-交付报告.md——落盘正本 details/sources/，原始出处 .debug/temp/ 易失）；GC-1 在飞面开工前核对（不预写快照）。
**优先级建议**：3
**完成判据**（=账本 T-23 criteria）：
- 宝钻注入 sim 联动落码
- back_size 死字段随联动处置
- 锁面更新
- CW 测试子集绿
- GC-1..GC-4 + IC-3（A/B 基线锚申报 + 可比性中断面声明）
**验收凭据形式**：CW 子集绿 + 段表登记/池指纹申报 + back_size 处置面 grep 对照。

## 3.8 腾席卖出上游滤占位件（账本 T-18）【wait：实机窗】
**范围**：三段——实机核证「箱可卖真值」→ 结论落档 board_structure.md → 定修法落码（生产资格面 fuel_sell_candidates 滤占位件）+ 行为锁。明确不含：假环境侧重做（既有对账面保留）、卖出通道其他语义。
**设计依据**：details/strategy-qualification.md §T-18。
**文件面**：mandate_v1/mandate.py、mandate_v1/shop.py、mandate_v1/entry.py、docs/game/currency_war/research/board_structure.md + 锁面。
**依赖**：3.2（shop.py 互斥排序，边见 design.md §3）；与 3.10 共 mandate.py 互斥（fuel_sell_candidates 段 × m3_levelup_batch 段，两段同文件、编排者控制在飞互斥，见 design.md §1 症状 3）；**外部等待（账本 cond）：实机核证箱可卖真值——复查时机 = 随实机窗（与 3.11 建档、3.12 验证族同窗并盘），先核证后定修法**；核证段前只允许资格面代码链梳理（只读准备面，不虚设开工）。
**优先级建议**：3
**完成判据**（=账本 T-18 criteria）：
- fuel_sell_candidates 上游滤占位件（生产资格面，修复只做了假环境侧对账）
- 箱可卖真值核证结论先行落档
- 行为锁
- CW 测试子集绿
- GC-1..GC-4
**验收凭据形式**：核证结论（实机交互证据 + 落档指针）+ 行为锁 + CW 子集绿。

## 3.9 seat_recoverable 代理收窄（账本 T-20）
**范围**：三段独立——诊断段（偏宽帧形态枚举）→ 方案段（收窄基准 = IC-1 资格单源）→ 落码段（P92 装配点 + 判定尺签名/docstring + 行为锁）。明确不含：P92 门其他通道语义。
**设计依据**：details/strategy-qualification.md §T-20；design.md §2 IC-1。
**文件面**：mandate_v1/shop.py（P92 装配段）、mandate_v1/criteria/refresh.py + 锁面。
**依赖**：3.8（单源依赖 IC-1：收窄基准 = T-18 定谳资格面；诊断段可在 3.8 核证期间先行，方案/落码段候 3.8；边见 design.md §3）；GC-1 在飞面开工前核对（不预写快照）。
**优先级建议**：3
**完成判据**（=账本 T-20 criteria）：
- T-313 方案对抗审残余面：seat_recoverable 代理收窄独立诊断 + 方案 + 落码
- 行为锁
- GC-1..GC-4（策略门行为面 → 方案审 + 落地审双审）
**验收凭据形式**：诊断清单（偏宽帧形态逐条）+ 方案审/落地审结论 + 行为锁（拦刷行为对照样本）。

## 3.10 备战帧金动作漏账修复（账本 T-16）【wait：mandate 面入库】
**范围**：备战帧金动作（m3 经验批 LevelUp(-20金) 等）接入 journal 回执/outcome 计数/spend_executed 三套账 + 修点定谳义务三条（HEAD 对照组落档 / 钉死展开位 / 守卫锁出处回填持久指针）+ 执行缝账务包络测试锁。明确不含：商店单元账务语义改动、策略行为。
**设计依据**：details/execution-seam-projection.md §T-16。
**文件面**：strategies/impl/mandate_v1/mandate.py（m3_levelup_batch 段）、执行缝入账模块（以修点定谳为准：cw_screen_prep.py / cw_shop_action_ops.py / cw_op_buy_cards.py / cw_exec_state.py 子集）+ 锁面。
**依赖**：3.4（单源依赖 IC-2：pad 态契约与 guard 形状**本体已由 T-308 入库（bd27989d4）**，开工前复核已入库契约（ADR-0646 + flow/projection_contract.md），以 T-17 残余修复落库后形状为修点定谳基准；边见 design.md §3）；与 3.8 共 mandate.py 互斥（m3_levelup_batch 段 × fuel_sell_candidates 段，见 design.md §1 症状 3）；**外部等待（账本 cond）：mandate 面在飞改动入库——复查时机 = 每次盘点 git status 与主线索引，在飞面落库即开工**；修复双审（方案段 + 落地审）。
**优先级建议**：4
**完成判据**（=账本 T-16 criteria）：
- m3 经验批 LevelUp(-20金) 等备战帧金动作经 journal 回执/outcome 计数/spend_executed 入账（执行缝三套账只辖商店单元的缺口闭合）
- 执行缝账务包络测试锁
- CW 测试子集绿
- 落地审 accept
- GC-1..GC-4（修点定谳义务三条随批执行）
**验收凭据形式**：HEAD 对照组落档 + 展开位定谳结论 + 备战帧金账锁 + CW 子集绿 + 落地审结论。

## 3.11 免费刷新机制建档接入（账本 T-13）【wait：实机窗】
**范围**：四段——对账段（T-162 入库面覆盖核对，可先行）→ 建档段（免费刷新按钮/余额区 screen_info 建档，走 MCP 工具）→ 读链接入 → 消费接线（固定理财/大裁员/加油站授予余额的真值通道 + 执行面免费通道消费；**计数载体归 unified-state 效果线，见总纲 IC-7**）。明确不含：观察基类迁移（IC-6）、投资屏付费刷新通道改动、执行面自造第二计数源（IC-7）。
**设计依据**：details/free-refresh-onboarding.md。
**文件面**：assets/game_data/screen_info/（MCP 工具维护）、商店屏读链模块、执行面刷新消费模块、data/cw_invest_data.py（若需）、测试仓锁面。
**依赖**：无内部阶段依赖（T-33 之外）；**跨迭代接口（IC-7）：效果线计数载体（账本 T-11 wire）未落期间，消费段只做屏读通道 + 候裁**；**外部等待（账本 cond）：实机窗口（需游戏画面含免费刷新按钮态）——复查时机 = 下次实机窗随布防清单一并建档**；对账段（防双源）为建档段前置，可先行；口径挂账（免费刷次数口径两说）随同窗定谳。
**优先级建议**：6
**完成判据**（=账本 T-13 criteria）：
- screen_info 建档（免费刷新独立按钮区，走 upsert_screen_area）+ 读链接入
- 免费刷新余额执行面消费接真值通道（固定理财/大裁员/加油站等授予余额的消费依赖）
- analyze_screen 对账命中
- CW 测试子集绿
- GC-1..GC-4（screen_info 修改一律走 MCP 工具，_od_merged.yml 在飞面对账）
**验收凭据形式**：analyze_screen 对账命中输出 + 消费接线单测/锁 + CW 子集绿。

## 3.12 实机验证族集中批（账本 T-14）【wait：实机解禁】
**范围**：检查点#5 清单六类项的盘点制验证（T-297 五锚/T-307 锚走查、back_max 4 条、游戏知识 5 条、T-309 竞态观察、T-322 实机窗、W4 显影抽查）+ 逐项结论回写。明确不含：任何策略行为修改（发现缺陷 → 报编排者另立）；落码面（纯观察/判读/回写）。
**设计依据**：details/live-verification-and-rulings.md §T-14。
**文件面**：docs/game/currency_war/research/**（知识回写）、迁移后正本区（系统项回写，按 IC-4 路径基线）。
**依赖**：无内部依赖；**外部等待（账本 cond）：实机解禁（state 链全 done 后门开）——复查时机 = 每次实机窗盘点余项，清单 = 旧账交接检查点#5**；实机窗按 runtime-ops 武装哨兵；与 3.8 核证段、3.11 建档段同窗并盘。
**优先级建议**：5
**完成判据**（=账本 T-14 criteria）：
- T-297 五锚 + T-307 锚走查
- back_max 实机确认 4 条（召唤物加格算术/diff 大于 2 公式形状/宝石剑缩格/投资环境通道合成）
- 游戏知识待实机 5 条
- T-309 竞态分布观察（桥后持卡局 frame 对照 + 第三局金账复核）
- T-322 实机窗
- W4 显影抽查（判读面计数可见性）
- 逐项结论回写文档或勘误，指针登记本 criteria
- GC-1..GC-4
**验收凭据形式**：逐项判读结论（清单对账表：项/结论/回写指针）。

## 3.13 结算面板三分量口径用户亲核（账本 T-26）【wait：用户亲核时机】
**范围**：三段——样本攒齐（胜局结算屏读数）→ 呈报段（三分量读数 vs 注册表对照表随对话呈报）→ 收尾段（结论落档 economy.md §11；勘误回写 economy.md §11 + cw_settlement_obs 申报面）。明确不含：败轮补发金口径（同窗顺呈报项，候编排者裁决，不并本判据）。
**设计依据**：details/live-verification-and-rulings.md §T-26。
**文件面**：docs/game/currency_war/research/economy.md（§11）、obs/cw_settlement_obs.py（申报面勘误，若有；在飞面按 GC-1）。
**依赖**：无内部依赖；**外部等待（账本 cond）：用户亲核时机——复查时机 = 结算样本局攒齐后随对话呈报**。
**优先级建议**：1
**完成判据**（=账本 T-26 criteria）：
- 三分量口径亲核结论落档
- 口径勘误（如有）回写文档与 cw_settlement_obs 申报面
- GC-1..GC-4
**验收凭据形式**：亲核结论落档指针 + 呈报对照表 + 勘误 diff（如有）。

## 3.14 显式动作轮部署目标视图统一候裁（账本 T-27）【wait：ADR 裁决】
**范围**：三段——呈报包组装（R1-b 扩面证据 + 显式轮滞留扫描数据 + 第三分歧现状清单，可先行）→ 候裁段（随对话呈报，用户二选一裁 deploy 围栏视图归属）→ 收尾段（定谳回写设计文档 + 滞留扫描结论 + 框架阵营并集第三分歧同收结论）。明确不含：ADR 落纸以外任何代码改动（本批零落码面）。
**设计依据**：details/live-verification-and-rulings.md §T-27。
**文件面**：呈报材料（reports/ 或 .debug/temp/currency_war/）、迁移后正本区设计文档（回写面）、ADR decisions/（候用户命令）。
**依赖**：无内部依赖；**外部等待（账本 cond）：ADR 定谳 deploy 围栏视图归属二选一——复查时机 = 随用户对话呈报 T-279 方案审 R1-b 扩面证据**；单源事实：T-279 已 done（R2 已落地，扫描义务可执行）。
**优先级建议**：2
**完成判据**（=账本 T-27 criteria）：
- ADR 定谳围栏视图归属
- T-279 R2 落地后扫显式轮滞留
- sim/生产第三分歧（框架阵营并集）同收结论
- GC-1..GC-4
**验收凭据形式**：呈报材料 + 用户裁决记录 + 三项收结论的回写指针。

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条核对正本与实现一致；查漏（各阶段内回写是否落对正本区、是否漏更）；本迭代 README 进度收尾。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档（迁移后地址为准）。
**依赖**：全部落地阶段。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。
**账本承载（F12 定稿必修申报）**：本阶段账本现无卡可派——末阶段卡由编排者落账（dag.py 命令草案见 design.md §3 账本动作申报第 2 条，deps = 全部落地阶段，建议 T-33 验收时即立），使收尾成为流程终点而非「记得就做」。

## 正本更新清单
- 本迭代目录 details/sources/：T-280-交付报告.md、T-322-实施-交付报告.md 正本落盘核对（定稿批已自 .debug/temp/currency_war/ 复制并附溯源 README）；末阶段核对 design/landing/details 引用指针全部指向落盘正本、temp 路径仅存「原始出处」注记 ← 3.4 / 3.7（attack.md F7 处置）
- docs/develop/sr_od/application/currency_war/（迁移后）flow/guards.md：执行缝账务包络语义（备战帧金动作三套账） ← 3.10
- docs/develop/sr_od/application/currency_war/（迁移后）flow/ 或 strategy/ 分篇：投影播种与 guard 布局契约（pad 态单一源、epoch 通道） ← 3.4
- docs/develop/sr_od/application/currency_war/（迁移后）strategy/ 分篇：腾席资格面语义（占位件滤、可卖子类） ← 3.8
- docs/develop/sr_od/application/currency_war/（迁移后）strategy/ 分篇：P92 席可落判定语义（代理收窄后口径） ← 3.9
- docs/develop/sr_od/application/currency_war/（迁移后）sim/sim-design.md + sim-wiring.md：开局金/首收入注入语义、账本行容忍口径与检查卡、宝钻联动、back_size 处置 ← 3.5 / 3.6 / 3.7
- docs/game/currency_war/research/board_structure.md：§备战栏 箱可卖真值；§上限 9 格 back_max 4 条结论 ← 3.8 / 3.12
- docs/game/currency_war/research/economy.md：§10/§11 开局金/首收入口径（若有勘误）、§11 三分量亲核凭据 ← 3.5 / 3.13
- docs/game/currency_war/research/（免费刷新机制落点篇：shop/refresh 相关或 invest_effects.md）：免费刷新按钮/余额机制 ← 3.11
- docs/game/currency_war/research/ 各篇：待实机 5 条逐项结论 ← 3.12
- docs/develop/sr_od/application/currency_war/（迁移后）策略分篇：deploy 围栏视图归属定谳、显式轮滞留与第三分歧结论 ← 3.14
- 本仓 skill（sr-od-currency-war-dev）单一源地图：迁移后路径（3.3 阶段内已同步，末阶段核对；skill 本体在本仓 skills/，F5 裁决）← 3.3
