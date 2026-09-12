# 投资策略候选全集门 落地

> 阶段唯一源纪律：本文件 = 账本阶段唯一源；设计改 → 本文件改 → 账本跟着改，禁两处各自演化。
> 通用工程门 = od-dev-progress-tracking §12（含 `ruff check` 仅改动文件、测试纪律；各阶段完成判据统一引用，不逐条复述）。
> 在飞互斥总注：`kernel/cw_events.py`、`kernel/cw_comps.py`、`kernel/cw_investments.py` 与统一 state 迁移在飞面（账本 T-96 cw_events 容器切换 / T-109 cw_comps 中间态收尾）及兄弟迭代 `2026-09-12-invest-env` 落地批（3.2/3.6 = cw_investments，3.4 = cw_comps，3.5 = cw_events）同文件——同文件阶段互斥、编排者排序，禁并行。

## 3.1 335 条策略卡全量分类盘点

**范围**：逐卡分类（绑定锚定/定义型/经济引擎/血本位/非锚定功能），产出三件——①全量分类审计表（`details/strategy-335-audit.md`，注册表值直调）；②`STRATEGY_BINDINGS` 覆盖缺口清单（按效果原文人工复核应锚定未锚定卡）；③「绑定全集外实卡」实测清单（门锁 fixture 源）。方法论单一源 = 详设 §6（5 步决策树/两遍挖掘协议/十一列 schema/机检验收：失格行集合 = D-c 18 卡逐卡相等；挖矿字典③ = 官方 config API `trait_info_list` 全集[详设 §6.2，实测 33 名]，开工前重拉对账）。角色全集口径已定稿（core_chars only，详设 §2）。边界：不碰任何生产代码。

**设计依据**：design.md §2.2（分类判据表）/ §2.2 表（定义卡现状核对）

**文件面**：`docs/develop/sr_od/application/currency_war/changes/2026-09-12-strategy-universe-gate/details/strategy-335-audit.md`（新建）；数据源只读（`kernel/cw_investments.py`/`kernel/cw_comps.py`/`data/cw_invest_data.py`）

**依赖**：无（静态注册表审计，不依赖环境迭代落码）

**优先级建议**：5

**完成判据**：
- 335 卡逐卡有分类行（无「待定」残留；真二义卡显式挂账并说明缺什么事实）
- 缺口清单逐条带效果原文引文与复核结论
- 实测清单 ≥1 张全集外实卡（否则门咬合面为空需如实申报）
- §12 通用工程门（引用，不复述）

**验收凭据形式**：审计表对照注册表抽查 + 缺口清单 review

## 3.2 门谓词落码 + 锁

**范围**：`kernel/cw_events.py` 策略分支全集门落码（**S4 全域跳过**：eval/eval-lcs/prior 三支，锚定源 `strategy_bindings`、豁免面三条件——S1 前提守卫/S2 经济/血本位自辖、`resolve_strategy_canonical` 形变名解析、`strategy-off-universe` 归因串；门谓词总装 = 详设 §5）；`kernel/cw_comps.py` 新增 `candidate_core_char_universe`（core-only，详设 §2）+ 共享遍历 helper（行为保持重构，U/D 断言保绿）；`cw_investments.py` 补 3.1 缺口清单确认的绑定条目。锁：详设 §7 全表（D-a..D-e 漂移断言 + G1-G14 行为锁；G14 注入型占位）。边界：不碰 T-162 判据本体、不碰环境分支、不碰意向层。

**设计依据**：design.md §2.1（门谓词与豁免面，定稿 = 详设 §2-§5）/ §2.3（T-162 对账，旗标细化 = 详设 §3.4）/ §2.6（验证设计 = 详设 §7）

**文件面**：`src/sr_od/application/currency_war/kernel/cw_events.py`、`src/sr_od/application/currency_war/kernel/cw_comps.py`（`candidate_core_char_universe` + 共享遍历 helper）、`src/sr_od/application/currency_war/kernel/cw_investments.py`（若 3.1 缺口清单要求补 STRATEGY_BINDINGS 条目）、`sr-od-test/test/sr_od/app/currency_war/`（锁文件名批首 grep 对齐聚居地）

**依赖**：3.1（分类表与 fixture）；`2026-09-12-invest-env` **3.5 收口**（env 分支汇合集成 = env 侧 `cw_events.py` 最后触面，3.1/3.4 由其依赖闭包传递覆盖；共享契约 = 详设 §8）；同文件 `cw_investments.py`（本批补绑定条目 vs env 3.2/3.6）互斥见头注；落码批首步 = `flow.decide_invest` 实传 evicted 形态核对（详设 §8「evicted 语义单一源」行：`decide_event` 既有参数，零接口新增——核对传参链现态与该声明一致后才动评分循环）

**优先级建议**：5

**完成判据**：
- 门锁全绿（详设 §7 锁面逐条：D-a..D-e + G1-G14）
- `test_cw_invest_refresh.py` + invest-env 迭代全部锁回归全绿（详设 §7 回归面）
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + 回归文件 + ruff check

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1、3.2
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `strategy-docs/13_pick_family.md` §1 `decide_invest` 行（判据格补策略全集门语义：锚定源/豁免面含 S1 前提守卫/归因串）← 3.2
- `strategy-docs/08_events.md` E2 行（决策机制格补全集门一句话）← 3.2
