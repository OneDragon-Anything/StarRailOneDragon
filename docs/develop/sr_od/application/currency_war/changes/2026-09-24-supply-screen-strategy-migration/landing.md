# 补给屏策略层迁移与选卡改形 落地

> 通用工程门（各阶段判据引用项，此处单一定义）：`uv run ruff check` 改动文件全过；直接受影响测试 + L1（`$env:PYTHONPATH='src'; uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow" -q`）一次通过；`git add` 逐文件点名；提交后 `git show --stat` 复核入库面 = 申报面。（源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节）

## 3.1 策略层决策本体 + flow 接线
**范围**：新建 `strategies/impl/mandate_v1/supply.py`（三级字典序决策 + 刷新判据 + 纯值出口，design §2.2-§2.5）；`flow.py::decide_supply` 改调 `supply.decide`（意向解析照 `invest_env` 同源：`locked_comp` 套名经 `get_comp` 解析后传入、`demoted_endgame` 直通；闸前移内嵌 decide）。边界：不动 kernel（删除归 3.2）；不动动作词表 / op handler / 观察写槽。**入库豁免**：§2.6 原子切换约束下本阶段不单独 commit——完成 = 工作区自验（ruff + L1 + 新锁绿），git 提交随 3.2 一并执行，通用工程门的提交/复核两项由 3.2 承接。
**设计依据**：design.md §2.2 / §2.3 / §2.4 / §2.5
**文件面**：`strategies/impl/mandate_v1/supply.py`（新）、`strategies/impl/flow.py`、`sr-od-test/test/sr_od/application/currency_war/`（新增决策锁）
**依赖**：无
**优先级建议**：5
**完成判据**：
- 行为对照 design §2.2（三级序与两账输入）、§2.3（凑星判据数据源 = `same_star_count`）、§2.4（三级全空 + 闸内嵌 fail-closed）
- 通用工程门（本文首节定义）
**验收凭据形式**：单帧锁 `sr-od-test/test/sr_od/application/currency_war/test_cw_supply_decision.py`——锁语义不锁牌面：①带钻必选（多钻按角色/装备细分）；②锁线帧终局成员卡压高价值装备卡；③未锁线/降格帧/get_comp 解析失败帧角色级空转、装备级无 key 参照；④已持够数成品不再高分、组件/近兑现升档（持有账按 design §2.2 第 3 级两账口径构造）；⑤三级全空才刷 + left 缺/尽不刷不阻塞落选卡（闸内嵌语义）；⑥席满无特殊分支（溢出席语义 = 正常选卡）；⑦凑星 tiebreak：同名 1★ 恰 2 张时该角色候选先于不凑星的终局成员候选，**含 2 张同名 1★ 分跨备战席/上阵行域的构造**（钉死 deployed 展平，防只数备战席的漏域实现）；⑧P1 配方锁帧：无钻帧建议刷（三级全空恒真）+ left 缺/尽构造下直接按「钻或通用值定序」落选卡（design §2.6 申报 ⑤ 刷新腿与闸语义）；⑨空候选帧返 idx=0 no-options（design §2.2 空帧定义）。

## 3.2 kernel 剪除与死代码删除
**范围**：删 `cw_events.decide_supply` 函数体 + `SupplyPick` + `EVENT_PICK_TYPES` 元组该位与 `EventPick` 联合别名该位（`SupplyOption`/`_equip_value` 按 design §2.6 保留）；删 `cw_survey19_hooks.supply_reroll_decision`；design §2.6 注释指针收口清单逐点处理；step3 幸存闸锁 docstring 过期注记（`test_cw_obs_arch_event_screens_step3.py:130-136`）。与 3.1 同一 commit 原子切换（新旧不并存）：**commit 面 = 3.1 ∪ 3.2 文件并集**（3.1 交付随本阶段一并入库，工程门提交/复核两项在此兑现）。测试面按 design §2.6 如实申报：在册无 kernel 侧 supply 决策专用锁；strategy 级 stub 两处（test_cw_obs_arch_event_screens_step3 / test_cw_supply_pick_immediate_report）不随删；`test_cw_unified_action_4.py` 类型 import 与实例构造点两处随删。
**设计依据**：design.md §2.6
**文件面**：`kernel/cw_events.py`、`kernel/cw_survey19_hooks.py`、`kernel/cw_vocab.py`、`operations/cw_op/cw_pick_supply_action.py`、`operations/cw_screen/cw_screen_supply_node.py`（仅注释）、`obs/cw_node_obs.py`（仅注释）、`sr-od-test/` 内引用被删符号的旧锁（含 `test_cw_unified_action_4.py` 的 SupplyPick 类型 import `:27-33` 与实例构造点 `:303`）
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- 全仓 grep `decide_supply` / `SupplyPick` / `supply_reroll_decision` 三段式验收：①kernel 决策面零残留（`SupplyOption` 按设计留在 kernel）；②合法存留面白名单 = flow 入口方法名（3.1 新链）及其在 `cw_screen_supply_node.py` 决策分支的合法调用点（`match.strategy.decide_supply()`）、`cw_strategy.py` ABC 抽象声明、strategy 级 stub 两处、其他迭代 `changes/` 历史工件（历史指称随其寿命存续，不溯改）、迁移后仍真实的存活指称（`flow/README.md:81`、`screens/supply.md:3/:39`——3.3 收口后为 30 号稿指针）、3.3 前的 docs 旧指针（3.3 收口）；③白名单外零命中
- kernel → strategies 零 import 方向成立
- 通用工程门（本文首节定义）
**验收凭据形式**：grep 输出 + `uv run ruff check <改动文件>` + 受影响测试全量（L1 快速集）

## 3.3 文档拆分（30 号稿 + 指针更新）
**范围**：新建 `strategy-docs/30_supply_screen.md`；`25_event_overlays.md` 头注/§1 prose/§2 动作清单表行移除补给；`13_pick_family.md` §1 `decide_supply` 行与 §2 E4 目录行改指单一源；`strategy-docs/README.md` §2 分篇表增 30 行 + `:54` 阅读导航句「18-29」→「18-30」改述（落批前 = 18-29，29 批 `9cce56962` 已改）；`08_events.md` E4 行「现有语义」格整体替换（design §2.7 口径）；`16_evaluation_tables_reassessment.md` 改形挂账行销账 + 死引用替锚；三份画面文档去陈旧（`screens/supply.md` 委托指针与重调语义、`docs/game/screens/currency_war_supply.md` 与 `docs/game/screens/货币战争-补给.md` 算法描述）。跨批协调纪律（design §2.7 末条）：落批时重读共享文档当前态，行号锚以实址为准。
**设计依据**：design.md §2.7
**文件面**：`strategy-docs/30_supply_screen.md`（新）、`strategy-docs/25_event_overlays.md`、`strategy-docs/13_pick_family.md`、`strategy-docs/README.md`、`strategy-docs/08_events.md`、`strategy-docs/16_evaluation_tables_reassessment.md`、`docs/develop/sr_od/application/currency_war/screens/supply.md`、`docs/game/screens/currency_war_supply.md`、`docs/game/screens/货币战争-补给.md`
**依赖**：3.1、3.2（文档须与落码后的实态一致）
**优先级建议**：5
**完成判据**：
- 30 号稿自足：判据语义（§2.2-§2.5）+ 裁定登记（**四项**：三级优先/终局名单/溢出席/刷新三空结构**含裁定原文与读法 A 确认记录**，用户 2026-09-24）+ 数学挂账（E4 derive / 带钻支配论证 / 重刷期权数学化）+ sim 盲区申报；as-built 无状态
- 指针内容逐条对照 design §2.7（含 strategy-docs/README `:54` 导航句改述）；无过程叙事（iteration-design 写作硬规则 3）
- 通用工程门（本文首节定义）
**验收凭据形式**：文档对照 review + 可执行 grep 词表——25 号稿内 `补给` 仅剩拆分头注 1 行；13/08/16 号稿补给表述仅存 30 号稿指针行/销账后形态；strategy-docs/README 内「18-27」零残留；screens/supply.md 与 docs/game 两份画面文档内 `decide_supply` 指针全部改指策略层；全仓 grep 旧指针零残留

## 3.4 实机判读对照
**范围**：跑实机局，按 design §2.6 实机判读锚点①-⑤逐项对账（①锁线局终局成员卡优先于高价值装备卡；②手握成品/组件的无钻帧不再刷新；③三级全空帧仍刷新——含 tier 0 高通用值件帧；④P1 配方锁帧按「钻或通用值」选卡；⑤席满帧凑星漏计已知、不判异常）。
**设计依据**：design.md §2.6（行为变化申报 + 实机判读锚点）
**文件面**：只读运行（MCP 跑实机局 + 判读），无代码/文档编辑面
**依赖**：3.1、3.2、3.3
**优先级建议**：5
**完成判据**：
- 逐锚点对账完成：命中/不命中逐条记录，不命中 = 回设计层定位（strategy-work §4：锚点没中 = 改动没生效或假设错，两者都要查）
- 单局异常条目当场定位，定位不了不进下一局
- 通用工程门（本文首节定义）
**验收凭据形式**：run_id + 逐锚点对账记录（进度账本/判读记录）

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条核验收口；全仓复扫旧指针零残留（含 flow/supply.py 注释、13 号稿族文档、25 号稿头注、16 号稿挂账行、screens/game 画面文档）。
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档 + 本迭代 README.md（进度收尾）
**依赖**：3.1、3.2、3.3、3.4
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单
- `strategy-docs/README.md` §2 分篇表 + `:54` 导航句 ← 3.3
- `strategy-docs/25_event_overlays.md` 画面族清单与头注 ← 3.3
- `strategy-docs/13_pick_family.md` §1 `decide_supply` 行 + §2 E4 目录行 ← 3.3
- `strategy-docs/08_events.md` E4 行 ← 3.3
- `strategy-docs/16_evaluation_tables_reassessment.md` 改形挂账行（销账 + 死引用清理 + 支配性定性对齐 30 号稿）← 3.3
- `docs/develop/sr_od/application/currency_war/screens/supply.md`（委托指针 + 重调语义）← 3.3
- `docs/game/screens/currency_war_supply.md`（算法描述/符号指称）← 3.3
- `docs/game/screens/货币战争-补给.md`（算法描述/符号指称）← 3.3
- （`30_supply_screen.md` 为新建正本，3.3 交付即正本）
