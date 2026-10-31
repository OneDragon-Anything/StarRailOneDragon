# 统一优先级三面收敛（名单 · 卖出/获取 · 部署）落地

> 状态：定稿（双块终验收口：卖出 0 阻断 / 部署 1 阻断文档卫生类已修收档——处置表见 attack-*-final.md 末尾）。

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集）;
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交;
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。
- L1 基线：`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`（基线 2225 passed, 2 skipped——阶段内不得引入非申报面红）。
- 改动 src 后涉及 MCP server 的验证按需重启（本迭代全部为策略层/kernel 改动，sim 与测试为主，无 screen_info 变更）。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 阶段 1：名单单一准入修复（含金币 tie-break 与 k_members 换源）

**范围**：`plane2_started_of` 单一准入 + 配方槽位直读贯穿（priority 装配/成员判定/卖出防线）；sort_key 档内补退金损失 tie-break（裁定三）；`k_members` 装配读口换源（§2.6 换源不消亡）。边界——不含场景注册删除、不含获取让位评估、不含部署搜索本体。
**设计依据**：design.md §2.1 / §2.2 第 1-2 项（membership 部分）/ §2.2 金币核查表 / §2.6。
**文件面**：`strategies/impl/mandate_v1/criteria/priority.py`、`criteria/sell_candidates.py`（仅 `sell_line_membership` 与 docstring）、`mandate.py`（k_members 两处装配读口换源 :467-489/:1882；保留面消费零改）。
**依赖**：无。
**优先级建议**：9（全迭代其余批的判定地基）。
**完成判据**：
- 三景测试（design §3 三景行）：P1 锁定局配方成员入名单落档 3/5；P2 恒空集；未锁定并集含配方——`recipe_members` 读口 = 槽位直读 + 读前判窗；
- 档内 tie-break：同档并列退金损失最小者优先（合成序 = 档 → 退金损失 → 稳定键 → 随机尾）；
- k_members：P1 锁定局 `frame.k_members` 含配方成员（换源生效），溢出告警门与 `cheapest_member_cost` 消费回归通过；
- §2.5 行为申报（P1 锁定局可卖池收窄/预算投影收紧）对应用例更新；
- 完成前常规检查（本文首节）。
**验收凭据形式**：test_priority.py / test_sell_candidates.py / test_mandate（k_members 面）用例名对照 §3 三景行。

## 阶段 2：升级凑金整链删除

**范围**：第 4 步凑金卖出臂、`_bench_liquid_gold`、levelup `gold_short` 臂（含 entry.py:898 悬空引用）、`_step3_liquidation_pending` 整删（裁定 A：等钱帧凑息照常）、`levelup_liquidate_prep` 场景行、遥测停产登记。边界——不含 `session_funding` 行（阶段 3）、不含凑息豁免（阶段 4）。
**设计依据**：design.md §2.2 第 3 项 / §2.3 凑金行 / §2.5 升级等钱申报。
**文件面**：`entry.py`、`criteria/levelup.py`、`shop.py`（:696-702/:698）、`criteria/sell_candidates.py`（levelup_liquidate_prep 注册行）、`telemetry/schema.py`。
**依赖**：阶段 1（membership 口径先行）。
**优先级建议**：8。
**完成判据**：
- 金不足帧零卖出动作（恒 defer，拒因键 `levelup_fund_line_defer`）；等钱/等级帽/奖励帧节末凑息恢复运行（裁定 A 用例）；
- `GATE_GOLD_SHORT` 全仓零残留（grep 断言）；`_bench_liquid_gold`/`_step3_liquidation_pending` 函数级删除；
- SCENE_SPECS 5→4（levelup_liquidate_prep 出表；session_funding 留待阶段 3）；凑金键族 + `levelup_stockpile_wait` 停产登记；
- 完成前常规检查。
**验收凭据形式**：test_levelup / test_entry 用例（levelup_liquidate_prep 面改 defer 断言）+ grep 断言。

## 阶段 3：获取让位统一 + 跨画面计划变量

**范围**：买入臂统一评估（虚拟阵容/虚拟金币/金币要求集三项——含鸭子面板 readiness 重放与缺列 fail-closed）；拦因分键与 ShopOpportunity 字段扩展 + 解拦分轴；`session_funding` 场景行与 funding 通道退役（闭集 5→3 收口）；计划变量槽/路径失败标记（StrategyState + 重置表）+ 备战前置步计划游标执行 + bridge `_launch_front_check` 让位谓词。边界——不含部署搜索本体（T 定型经接口契约③接现行 `select_deployment`，阶段 5 换统一搜索后接口面不变）。
**设计依据**：design.md §2.2 第 4 项（含裁定一计划变量/裁定二金币域收全）/ §2.3 获取驱动让位表 / 用户裁定补录。
**文件面**：`shop.py`（买入臂评估 + :1305-1309 筹资挂载面）、`shop_session.py`（解拦分轴）、`mandate_state.py`（blocked_by 闭集 +1、ShopOpportunity 三字段、计划槽/标记字段 + 重置表）、`entry.py`（前置步计划游标）、`bridge.py`（让位谓词）、`criteria/sell_candidates.py`（session_funding 行）、`telemetry/schema.py`（新键/观测键）。
**依赖**：阶段 1、2。
**优先级建议**：8。
**完成判据**：
- design §3「获取让位评估测试」全行（分键语境断言/victim 落位分流/池穷尽 gold_short/无 session_funding 残留）；
- 「计划变量测试」全行（步骤序列写入/逐帧消化/序列空清槽/**零重验断言——备战执行零搜索调用**/执行失败按计划语境记键/节点边界清零/挡 1-9 步用例）；
- 饱和线项：鸭子面板构造用例（bench 无 X/缺列 fail-closed/时点 = 买 X 帧）；
- 完成前常规检查。
**验收凭据形式**：test_shop（让位评估面）/ test_entry（计划游标面）/ test_mandate_state（键与字段面）用例名。

## 阶段 4：凑息卖出豁免

**范围**：凑息候选池剔除线内未达标成员（豁免集承载 = §2.2 第 5 项定义）；豁免剔光帧观测键。边界——仅利息动机类；被迫类零改。
**设计依据**：design.md §2.2 第 5 项 / §2.3 凑息行 / §2.5 凑息豁免申报。
**文件面**：`criteria/priority.py`（豁免谓词单一源 `interest_exempt_member`——design §2.2 第 5 项明文落点）、`criteria/sell_candidates.py`（场景参数 + 池过滤 + 剔光观测键）、`entry.py`（第 8 步面）、`telemetry/schema.py`。
**依赖**：阶段 1（线内口径）。
**优先级建议**：6。
**完成判据**：design §3「凑息豁免测试」四用例（剔光零动作/非线内垫件照卖/达标件照常/被迫类不受豁免）；观测键在案；完成前常规检查。
**验收凭据形式**：test_sell_candidates 凑息面用例名（TestInterestMemberExemption 前三用例 + 剔光键边界）；第四用例（被迫类照卖，获取让位帧）= test_acquire_yield 凑息豁免不适用用例名。

## 阶段 5：统一部署搜索（评分制）

**范围**：详设全量——评分函数（层归属全域组得分/增量口径/相位枚举/过渡条件两态）、三段搜索（圈人/分组背包补人/终评全量）、差分执行器（统一拖动交替重观察/计划游标 target = 固定 T）、统一拖动 Op（schema 单坐标系/SellDeployed 坐标域扩展/截断器分类表登记/faction 字段）、收编清单（swap 机器/转型域双门/让渡序/态 1 特例/k_members 消费面）、SellDeployed 三发出点收口。边界——卖出场景逻辑零改（部署/卖出两套独立算法）。
**设计依据**：details/unified-deploy-order.md 全文（§1-§5/场景走查/关键取舍）+ design.md §2.7。
**文件面**：`strategies/impl/mandate_v1/deploy_plan.py`（或新判据件）、`kernel/cw_deploy_logic.py`、`kernel/cw_vocab.py`（动作 schema）、`operations/cw_op/cw_deploy_move_action.py`、`operations/cw_op/cw_sell_deployed_action.py`、`kernel/cw_game_state.py`（:653 sell 消费位直读）、`kernel/cw_action_report/deploy_move.py`、`entry.py`（第 6 步切执行器/truncate_frame_stable 分类表）、`kernel/cw_bond_equips.py`（若 unit_bond_tags 扩展）、`telemetry/schema.py`、`docs/develop/sr_od/application/currency_war/flow/action_exec.md`（§1 契约改版——随代码同批）。
**依赖**：阶段 3（计划游标与差分执行器接口先行）。
**优先级建议**：7。
**完成判据**：
- design §3「部署搜索测试」全行 + 详设场景走查表全行（保板相位/换防跳变/同名异星两步/唯一性键/银狼一致性/空羁绊线/L2 键集）；
- sim 计时申报复核（can_deploy_single ≈ 0.1s 级/帧、评估帧 2 次搜索——D8-4/D9-6 口径）；
- 收编清单逐行对照（swap 机器零残留/三发出点在役/k_members 保留面消费通过）；
- 完成前常规检查。
**验收凭据形式**：test_deploy_plan / test_cw_deploy / test_cw_vocab（动作面）/ sim 计时输出对照。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节（= design.md §正本更新清单 镜像）。
**文件面**：清单所列正本文档。
**依赖**：全部落地阶段。
**优先级建议**：0。
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- strategy-docs/11_shop_decisions.md §4.0/§4.1：核对「身份段退役」「线内身份集」表述与修复后实现一致 ← 阶段 1
- strategy-docs/11_shop_decisions.md §2：凑金域口径收敛（gold_short/defer 分派与凑至守线表述 → 破线恒 defer 等钱）← 阶段 2
- strategy-docs/11_shop_decisions.md §2 :47 凑息抑制句 / :48 凑金可达性行退役 ← 阶段 2
- strategy-docs/11_shop_decisions.md §4.0：场景参数全集表删升级凑金行；「三触发五场景」计数同步；六步流程节改写为统一获取让位评估 ← 阶段 2/3
- strategy-docs/22_prep_screen.md §1 第 4 步凑金卖出表述删除；场景枚举行同步 ← 阶段 2
- strategy-docs/22_prep_screen.md §1 第 8 步节末凑息抑制句删除 ← 阶段 2
- strategy-docs/11_shop_decisions.md §4.0：会话内筹资正文段与 `funding` 通道行退役 ← 阶段 3
- strategy-docs/11_shop_decisions.md §4.1：卖出资格仲裁随拦因分键（`priority_insufficient_gold`）与解拦分轴同步 ← 阶段 3
- strategy-docs/23_shop_screen.md：会话循环/机会清单解拦复核随分键分轴同步 ← 阶段 3
- strategy-docs/12_line_and_intention.md §1.2 :29「筹资」措辞核对修订（删「正文预期零改」声明）← 阶段 3
- strategy-docs/22_prep_screen.md §1「无需状态机记步」与 §4「独立备战卖出上场件义务出口不存在」：被计划变量（逐帧游标）/路径失败标记/前置步 SellDeployed 突破——架构级声明改写 ← 阶段 3
- strategy-docs/24_deploy_segment.md：全文重写为统一部署搜索·评分制（三套机器/转型域双门/让渡序表述退役）← 阶段 5
- strategy-docs/12_line_and_intention.md §3：配方对链板面执行段收编（易手语义归稳定键/评分搜索）← 阶段 5
- strategy-docs/02_mandate_layer.md §7 sell 行：姊妹出口表述随 swap 机器删除退役 ← 阶段 5
- docs/develop/sr_od/application/currency_war/proofs/math_proofs.md：P79 行消解登记（被统一部署搜索取代）← 阶段 5
- docs/develop/sr_od/application/currency_war/flow/action_exec.md §1：统一拖动与 SellDeployed 坐标域契约改版登记（truncate_frame_stable 分类表同步）← 阶段 5（随代码批内完成，末阶段复核）
