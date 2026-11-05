# key-items-retirement 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关子集）；
- 术语清理：本阶段文件面内代码注释与文档的存量表述按统一术语表 `docs/develop/sr_od/application/currency_war/terminology.md` 核对（替换表内词改白话，保留词首现带定义）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」「文档规范·术语使用」节。

## 3.1 key_items 字段退役批

**范围**：`Comp.key_items` 字段删除 + 全部消费点改写 + 常量删除 + 建库校验/测试断言同步。具体：
- cw_comps.py：字段与 docstring 删除；21 套条目数据行删除（66 行）；Comp 类体内「知识卡字段」注释块收窄（知识卡 = need_star）；数据行「# 骨架=…」注释块与 `carry_set` docstring「与 key_items 骨架档/插件档三分」句随批清理；
- line_select.py：`LineScore.skeleton` 分量删除、`gate_positive` 去骨架项、`line_score_breakdown` 删 `skeleton_hits` 与插件档的 `− key_items` 排除项、`SKELETON_BONUS` import 删除；模块头与 docstring 的「骨架」措辞同步；
- cw_line_scales.py：`SKELETON_BONUS` 常量删除、docstring 消费面声明同步；
- shop.py：货架资格臂 `_qual_names |= set(_vc.key_items or ())` 行删除、注释「CARRY/骨架级」措辞改「CARRY 级」；
- 测试仓：test_faction_derivation_locks（`assert comp.key_items` 非空断言删除；`(*comp.need_star, *comp.key_items)` 校验循环去 key_items 半边）；test_line_select 骨架档断言改写（skeleton 分量断言删除、证据门断言去骨架项、key_items 相关构造样例清理）；**test_shop_session_loop**（`test_skeleton_card_on_shelf_qualifies` 改写为反向断言——资格域外件不触发 `shelf_qualify_buy` 买入；`_f_qual |= set(_c.key_items or ())` 复刻断言删 key_items 半边；「CARRY ∪ key_items」注释同步）；**test_no_target_three_arms**（`carry_set(c) | set(c.key_items or ())` 复刻断言删 key_items 半边；注释同步）；
- **行为变化对照 design.md §2.2 申报表执行**：全部 8 行活数据损失与门翻转/二阶效应统一语义（§2.2 表前段）已申报，落地批不逐行复推演；sim 正项上界自算测试随分量删除自动收窄（自算口径即自证，如断言值写死则按新上界更新）。

**边界（不含）**：绯英线藿藈进 shared 评估；圣杯任务链特殊系统；过渡块→终局线衔接通道；字段族防复发机制与 flex_factions 同键清算（均见 design.md §1 不解决清单）。

**设计依据**：design.md §2.1/§2.2/§2.5

**文件面**：`src/sr_od/application/currency_war/kernel/cw_comps.py`、`src/sr_od/application/currency_war/kernel/cw_line_scales.py`、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/line_select.py`、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`；`sr-od-test/` 镜像：`test/sr_od/application/currency_war/kernel/test_faction_derivation_locks.py`、`test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_line_select.py`、`test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_shop_session_loop.py`、`test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_no_target_three_arms.py`

**依赖**：无

**优先级建议**：8

**完成判据**：
- `key_items` 全词（含注释裸词）在 src + sr-od-test 零残留；`SKELETON_BONUS` 与 `skeleton_hits` 同口径零残留；
- 证据分行为对照：`line_score_breakdown` 输出无 skeleton 分量、`gate_positive` = env ∨ carry ∨ 插件；货架资格集 = `carry_set`（design.md §2.1）；
- 行为验证 = 测试全绿（含 §2.1 第 4 条全部断言处置）；**实机首局观察记为遗留待办**（观察点 = `shelf_qualify_buy` 买入案例中骨架级单卡零出现——沿 or-reqs-retirement 先例用法，不设为完成判据，落地批在测试仓 README 或迭代 README 遗留节登记指针）；
- 完成前常规检查（本文首节）+ 全量测试。

**验收凭据形式**：全词 grep 零残留记录 + 测试名清单 + 遗留待办登记指针

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新权威版本文档。

**设计依据**：本文件「正本更新清单」节

**文件面**：清单所列权威版本文档

**依赖**：3.1

**优先级建议**：0

**完成判据**：清单清零；权威版本与实现一致；黑话终扫（本迭代全部文件面按术语表扫描，design/landing 自身新写稿同守表）

**验收凭据形式**：文档对照 review

## 正本更新清单

- `strategy-docs/12_line_and_intention.md`：篇首引言术语定义行（知识卡定义删 key_items，留 need_star）← 3.1
- `strategy-docs/12_line_and_intention.md`：§1.1 线分公式行「证据分(carry + 骨架 + 插件 + 装备件 + 热度)」删骨架项 ← 3.1
- `strategy-docs/12_line_and_intention.md`：§1.1 证据层「引用 > 其余 core > 骨架 > 插件」四档措辞 → 三档；数量级表「骨架件 `SKELETON_BONUS`(4 骨架 = 1 anchor 相平)」行删除（常量随删，正本禁引已删符号）；姬子 A/B 拆分行「need_star/key_items/站位共享」删 key_items ← 3.1
- `strategy-docs/12_line_and_intention.md`：§1.1 `gate_positive` 分量表述；§1.2 证据门「env ∨ carry ∨ 骨架 ∨ 插件」；§1.1 末条「key_items 缺行时持有证据仅消费 carry 层」fail 方向句删除；§1.1 末条货架「CARRY/骨架级牌」措辞 ← 3.1
- `strategy-docs/11_shop_decisions.md`：§1 货架资格臂「CARRY/骨架级（`carry_set` ∪ `key_items`）」→「CARRY 级（`carry_set`）」 ← 3.1
- `skills/sr-od-dev-currency-war/references/comp-definition.md`：schema 分层语义「知识卡」字段族（key_items/need_star → need_star 单字段）；「名单多胞胎警惕」先例条目补 key_items 整字段退役（过渡体系建成后旧载体清算，对齐 lock_rules/entry_signals 先例句式） ← 3.1

（核实注记：`strategy-docs/10_prep_decisions.md` §5 字段存留表经逐行核实**无 key_items 行**，无更新项——沿 or-reqs-retirement 同位核实先例登记，防第三次幽灵行。）
