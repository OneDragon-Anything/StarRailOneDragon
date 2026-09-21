# 池升格批(pool-kernel-promotion)实现独立审查 R1

- 审查对象:主仓 `6db7b1c3f`(feat/mcp-backend-sync2 线)、测试仓 `31099cfa`
- 基准:`design.md`(定稿)§2.1–§2.6
- 审查员:实现独立(GLM-5.3 档,与实现 worker 交叉视角);只读审查,除本报告外零文件改动
- 方法:旧实现 `git show 6db7b1c3f^:sim/cw_sim_pool.py` 与新建 `kernel/cw_pool.py` 逐函数 diff;双侧仓 grep 残留;测试仓前后版 diff;独立复跑 L1

## 逐项核验

### 1. 逐字迁移核验(重)— 通过

`git diff --no-index` 全量比对(旧 `sim/cw_sim_pool.py` 109 行 vs 新 `kernel/cw_pool.py` 163 行),逐函数结论:

| 函数/成员 | 函数体差异 | 是否申报内 |
|---|---|---|
| `fixed_pool` | 仅 raise 文案去 `U10:` 前缀 + docstring 重写 | ✅(见发现 1,系清单项 2 强制) |
| `held_copies` | 仅 docstring(补同名同档定谳句);循环体零改动 | ✅ 头注/docstring 重写 |
| `_remaining_and_held` | 仅守恒炸错文案(「sim 内部 bug」→「池派生与持有约束不一致」) | ✅ §2.1 显式申报 |
| `remaining_pool` | 零改动(docstring 指针更新) | ✅ |
| `drawable_names` | 唯一过滤行 `CHARACTERS[name].cost == cost` → `effective_cost(gs, name) == cost` + docstring | ✅ §2.1 唯一语义改造 |
| `EXPERT_COPIES_ASSUMED` | 值 9 不变;注释去 U10 标记 | ✅ |
| `grant_bucket_names` | 新增(§2.2 契约出口) | ✅ |

超出申报的函数体差异:**零**。

### 2. 头注重写铁律 — 通过

`kernel/cw_pool.py` 全文 grep:`changes/` 零命中、`M06`/`U10`/`U11`/任何 M/U 节号零命中。持久索引双双在册:模块头注载「常量单一源 = `data/cw_shop_odds.py` 的 `POOL_COPIES_PER_CARD`;口径出处 = `docs/game/currency_war/research/economy.md` §1」。守恒炸错 kernel 语义申报段(r4-F22)按 §2.1 落入模块头注。✅

### 3. 双出口语义 — 通过

- `grant_bucket_names` 过滤 = `left > 0 and effective_cost(gs, name) == cost`——**无 held<9 条件**,与 §2.2 契约逐字一致;
- `drawable_names` 三条件(档 ∧ 剩余>0 ∧ held<9)原样;
- 披露键两枚在册:`GRANT_BUCKET_NO_NINE_FILTER_V0` = `'grant_bucket_no_nine_filter_v0'`、`GRANT_BUCKET_UNIFORM_BY_NAME_V0` = `'grant_bucket_uniform_by_name_v0'`,各带语义注释;
- `grant_bucket_names` docstring 载:调用时序契约(先回归写落容器再采样、merge_step_once 范式不适用)+ extra_experts「kernel 调用恒缺省 None,调用方禁自填」申报。✅
- 两出口共用 `_remaining_and_held` 单源,无第二实现。✅

### 4. M21 退役完整性 — 通过

- 双侧仓 grep `silver_wolf_effective_cost`/`SILVER_WOLF_COST_BY_STAR`:src 侧命中仅 `docs/develop/.../changes/` 历史设计文档(设计文档引设计文档,合法;**代码零残留**);sr-od-test 侧零命中。
- `sim/cw_sim_special.py`:两符号已删;留守三符号 `SILVER_WOLF_ID`/`planner_overlay_due`/`trailblazer_form_of` 齐全。头注 M21 段整段重写:新口径 = 费用档 = 容器推演状态(`gs.lv999_cost_tier`/`effective_cost`,2026-09-18 定谳)、池桶归属经 `kernel.cw_pool` 承接、旧「星级×上场态」「池过滤器语义」句已清除;试用句指针 = `docs/game/gameplay/currency_war.md`「试用角色」行 :81(实测该行内容 = 试用角色机制行,指针有效)。
- `cw_sim_engine.py` :159-162 import 面(仅 `SILVER_WOLF_ID`+`planner_overlay_due`)与 :473 附近 `planner_overlay_due` 消费点核验不受影响。✅

### 5. 测试等价锁真实性 — 通过

- `git diff --no-index` 前后版 `test_cw_sim_pool.py`:原 7 测**断言零改**,唯一既有面变化 = import 块(`sim.cw_sim_pool` → `kernel.cw_pool` + 新增 `grant_bucket_names` import);三新锁纯追加。等价锁成立。
- 三新锁构造真实性:
  - **档感知锁**:`write_logic(gs.lv999_cost_tier, 4)` 后 `drawable_names(4)` 含银狼 / `(3)` 不含;未写档 gs 归约 3 费桶——与 §2.4 逐条对应;
  - **双出口分野锁**:1 费卡 3★ 构造 held=9(断言 `held_copies == 9`)、断言 `remaining_pool == POOL_COPIES_PER_CARD[1] - 9`(27−9=18>0,共享条件在场)→ 商店出口清空、授予出口在册——正是设计点名的 held=9/剩余=18 形态,分野纯由 ≥9 过滤产生;
  - **守恒跨档锁**:2★(held=3)→ 写档 4 → 1★(held=1),断言剩余 = 9−1 不炸、旧档账面无负、双出口档=4 在册——与 §2.4 对应。

### 6. 爆炸半径 — 通过

- 主仓 commit 文件面 = `kernel/cw_pool.py`(新)+ `sim/cw_sim_pool.py`(删)+ `sim/cw_sim_shop.py`(import 直改一行)+ `sim/cw_sim_special.py`(退役+头注)= §2.6 文件面**精确重合**,无文件面外触碰;测试仓 = 两测试文件,亦与 §2.6 重合。
- src 全库 grep `cw_sim_pool` 零代码残留;`cw_sim_shop.py` import 已指 `kernel.cw_pool`,无 re-export shim。✅

### 7. worker 两点边界申报复核 — 通过

- 披露键常量形态:两键以 `GRANT_BUCKET_*_V0` 模块常量承载、字符串值与设计点名一致,带注释——最小且正当;
- `test_cw_sim_equips.py` 头注同步:锁面行从「U26 银狼升费口径」改为「银狼策划触发判据……当前档 = 容器推演状态,读口 = `kernel.cw_economy.effective_cost`」,与符号退役事实一致、最小改面。✅

## 发现清单

1. `[minor] | design §2.1/§2.4 | fixed_pool 的 raise 文案与 EXPERT_COPIES_ASSUMED 注释也去了 U10 标记,严格说超出「头注/docstring 重写」字面 | 但与审查清单第 2 项「全文零 U10/U11 节号标记」强制一致,且测试零断言该文案 | 无需修正;建议后续迭代把「申报面」措辞放宽为「全文 M/U 标记清除」以免逐字条款与全文铁律互斥的表述歧义 |
2. `[minor] | 观察项(非 design 违约) | sim/cw_sim_special.py 文件级「设计正本 = changes/2026-09-15-sim-redesign/...」行随 M21 段重写仍保留 | 本批契约仅要求 M21 段重写;changes/ 引用属该文件既有欠账(sim 域普遍形态),非本批引入 | 归 sim 正本收敛时统一处置,不阻本批 |

无 major 发现。

## 独立复跑

`$env:PYTHONPATH='src'; uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow and not legacy_baseline" -q` → **916 passed, 1 warning(deprecation,与本批无关), 26.58s**。

## 总结论

**通过**。七项审查清单全部核验通过;唯二发现均为 minor 观察项(其一系契约措辞自我互斥所致的正确取舍,其二为本批范围外的既有欠账),无打回项。逐字迁移等价、双出口语义与披露、M21 退役、测试等价锁、爆炸半径、边界申报全部与定稿设计一致。
