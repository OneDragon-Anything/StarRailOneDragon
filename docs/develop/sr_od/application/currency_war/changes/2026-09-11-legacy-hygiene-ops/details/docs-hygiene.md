# 悬空引用清理与文档树迁移（详设：T-24 / T-25）

## 问题与约束
本篇辖两批，共享 `docs/develop/currency_war/` 旧文档树与部分 src 注释面；两批互斥串行（先清理后迁移），且与在飞迁移批（账本 T-29 BoardState 详设迁 changes / T-30 散落设计找回）互斥。

### T-24 悬空 ADR 引用清理（0648/0649/0650/0653 删除笔遗留）
- **根因归层**：流程层——ADR 删除流程缺「残留引用清扫」步骤（引用形态残缺，非语义缺陷）。
- **症状**：用户命令删除旧决策档(0648/0649/0650/0653 四件)后残留悬空引用——记账时点约 20 处/11 文件，定稿时点实测 25 处/12 文件（不含本迭代 attack.md 自引；以开工时 grep 重跑为准）（依据 = 旧账交接检查点 §未竟清单#3；`git grep -E 'ADR-06(48|49|50|53)|0648-p92|0649-equipment|0650-cw4|0653-m2b'` 实测命中面）。
- **命中面（定稿时点实测，开工时以 grep 重跑为准）**：docs/develop/currency_war/strategy-docs/11_shop_decisions.md、19_reinforce_channel_and_survival_discount.md；changes/2026-09-11-unified-state/details/recovered/T-320-决策行文件schema设计.md；src 侧 telemetry/recorder.py、telemetry/match_archive.py、operations/cw_loop.py、kernel/cw_board_state.py、mandate_v1/shop.py、mandate_v1/mandate_state.py、mandate_v1/criteria/contracts.py、mandate_v1/criteria/equipment.py、mandate_v1/criteria/__init__.py。
- **扩围面（账本 T-24 附注 2026-09-11T23:59:17）**：正本到 .debug 的悬空引用清单（引用目标文件已灭失——math_proofs/projection_contract/flow 多处）本批一并覆盖，清单 = reports/T-30-r1.md 第 4 节（attack.md F8 裁决回写 landing §3.2 同口径）。
- **处置口径（总纲 IC-5）**：每处引用改写为纯语义描述（被引 ADR 的裁决语义一句话，读者无需回原文）或直接删除装饰性引用；**禁重建 ADR、禁改 ADR 历史原文**；src 注释面的改写遵循注释规范（持久索引或纯语义描述，禁会话局部标识符）。
- **互斥与前置**：
  - changes/ recovered 文件在 T-30（散落设计找回整理）范围内 → 本批候 T-30 done，开工前核对该目录无在飞写入；
  - src 命中文件多个有在飞 hunks（cw_loop.py / cw_board_state.py / mandate_v1/shop.py / criteria/* 等）→ 按 GC-1 逐文件避让申报或候入库；与 T-18/T-20（shop.py）串行（landing.md 排布：T-24 先行）。

### T-25 CW 文档树迁移（docs/develop/currency_war → docs/develop/sr_od/application/currency_war）
- **根因归层**：流程层——文档树地址规范落地流程欠账（历史树未随双层文档流规范迁移，属交接缺口非内容缺陷）。
- **范围**：`docs/develop/currency_war/` 整体迁至 `docs/develop/sr_od/application/currency_war/`（双层文档流规范地址，依据 = AGENTS.md「双层文档流」+ 旧账交接检查点 §未竟清单#4「触发条件已满足（W5/T-321 均落定）」）；随迁修正 77 处 proofs 引用路径错层（同检查点#4 计数，开工时以 grep 重算为准）。
- **引用面同步（全量清单）**：
  1. 主仓全仓旧路径引用（src 注释、docs、tools）grep 清零——迁移后旧路径全仓 0 引用 grep 锁（账本 criteria）；
  2. **sr-od-currency-war-dev skill 内路径引用同步**——skill 本体在**本仓** `skills/sr-od-currency-war-dev/`（junction 挂载 `.dsh/skills/sr-od-currency-war-dev`；SR 专属 skill 单源在本仓，依据 = AGENTS.md「SR 专属 skill 进本仓 skills/」；公共仓 OneDragon-Skills 的 skills/ 只有 od-dev-* 系，无此 skill——attack.md F5 裁决校正，防 worker 误去公共仓找/改甚至 fork 单源）。路径引用修改发生在本仓，单仓单笔 commit，交付报告登记本仓 hash；
  3. 正本区内部相对链接随目录整体迁移天然保持，逐篇抽查断链。
- **边界**：`docs/game/currency_war/` 不迁（游戏知识树地址不变）；changes/ 迭代目录不迁（已在目标地址下）；ADR decisions/ 目录随树迁移（decisions 属设计文档区;后经用户令整体删除,本节为当时点边界记录）。
- **互斥**：与一切写 `docs/develop/currency_war/**` 的批互斥（T-24 先行；此后各代码批的文档回写按总纲 IC-4 用新路径）；与在飞 T-29/T-30 的 changes/ 写入互斥（它们写 changes/ 新址，本批迁旧树，物理不重叠，但开工前按 GC-1 对账一次防新落文档落错树）。

## 方案（实施序）
1. **T-24 先行**：grep 命中面重跑 → 逐文件处置（IC-5 口径）→ 全仓 0 命中 grep 锁 + ruff（src 命中文件）+ 受影响测试绿。
2. **T-25 随后**：`git mv` 整树迁移 → 77 处 proofs 错层引用修正 → 全仓引用面同步（含本仓 skill 本体，F5 裁决）→ 旧路径 0 引用 grep 锁 → 断链抽查。

## 关键取舍
- **先清理后迁移**：悬空引用清理若排迁移后，grep 口径要在新旧两套路径下各跑一遍且迁移 diff 混入清理 diff，验收对照失真；先清理使迁移 diff 纯净（纯移动 + 路径修正）。
- **迁移用 git mv 保历史**：文档考古走 git 历史（AGENTS.md），整树 rename 让 git 跟踪文件历史；禁删了重写。
- **skill 同步单仓单笔**：skill 本体在本仓（F5 裁决），与主仓文档迁移同一仓内分批 commit、禁跨批混提（junction 挂载点 `.dsh/skills/` 不入库，gitignore 已覆盖）；skill 路径同步漏改的后果 = 单一源地图指旧路径，skill 读者全部踩空——以旧路径全仓 0 引用 grep 锁覆盖（git grep 天然含本仓 tracked 的 skill 文件，无盲区）。
