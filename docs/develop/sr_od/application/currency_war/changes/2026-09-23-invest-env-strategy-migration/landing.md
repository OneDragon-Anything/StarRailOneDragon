# 投资环境策略层迁移 落地

## 3.1 策略层新增（纯新增，零行为）
**范围**：新增 `strategies/impl/mandate_v1/line_value.py`、`gift_value.py`、`env_economy.py`（自 `kernel/cw_env_economy.py` 迁入改造：删域带归一与上界校验项，§2.3）、`invest_env.py`（决策入口+四价值组件+立场分表+刷新判据+交互规则+构建期校验）；配套单测。边界：不动 flow 接线、不动 kernel 现有符号——本阶段结束新旧并存但新文件零调用。
**设计依据**：design.md §2.2-§2.6、§2.7、§2.8、§2.9（接口按 §2.9 预留形态）
**文件面**：`src/sr_od/application/currency_war/strategies/impl/mandate_v1/`（新增 4 文件）、`sr-od-test/test/sr_od/application/currency_war/`（新增测试文件）。tools/ 两脚本 import 路径更新归 3.2（与 kernel 原文件删除同批）。
**依赖**：无
**优先级建议**：5
**完成判据**：
- 单测绿：①方向分序（注册表真实数据：列车同行概念股 > 减益概念股 > 仙舟概念股；锁线不含该阵营 → 0；evicted 收窄后线退场 → 0）②赠卡分（战技点契约=双 core 白得高分；全员集外 → 0；advisor 减半；随机阵营=成员档位平均）③时代族 6 条总分=0 ④现金分（增发货币>0 且 resolved；缺参环境=0 且不炸）⑤刷新三态（禁选必刷/低分帧+剩余≥1 刷/高分帧不刷）⑥自拆台排除 ⑦构建校验（立场表缺行即炸）
- 行为对照 design.md §2.2（加法总分公式）与 §2.6（表 1-3 键完备）
- 立场系数与立场分初值经用户过目（表 1/2/3 为裁决窗）
- §12 通用工程门（引用，不复述）
**验收凭据形式**：测试名清单 + 系数表裁决记录

## 3.2 原子行为切换
**范围**：flow `_decide_invest` env 分支接线到 `invest_env.decide`；kernel 删除面一次性执行（design.md §2.10 全清单，含 `cw_events` env 轴、`ENV_PICK_VALUE` 环境条目、`ENV_FACTION_MATCH_FLOOR`、`GIFT_FLOOR_*`、旧归属声明、`kernel/cw_env_economy.py`、`candidate_faction_universe`/`candidate_char_universe` 孤儿查证删除、env 侧 CommitSignals 死代码、旧测试断言清理）；env 侧工具脚本 import 切到新路径。
**设计依据**：design.md §2.9、§2.10
**文件面**：`src/sr_od/application/currency_war/strategies/impl/flow.py`、`kernel/cw_events.py`、`kernel/cw_investments.py`、`kernel/cw_comps.py`（孤儿函数删除）、`kernel/cw_env_economy.py`（删）、`kernel/cw_vocab.py`（仅当注释指针引用被删符号）、`tools/cw/` 两脚本、相关测试文件
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- 全仓 grep：`ENV_FACTION_MATCH_FLOOR`/`GIFT_FLOOR_`/`cw_env_economy`（kernel 侧 import）/`candidate_faction_universe`/`candidate_char_universe` 零残留；`cw_events` 无 env 轴分支
- L1 快速集全绿（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`）
- 行为对照 §2.10 行为变化申报表四条方向（序变化可从表 1-3 推导预期，非复刻旧序）+ flow 消费侧测试锁四条（env 帧路由与动作包装/memo 三态/decide-decide_pick 零漂移含全排除退化帧/策略轴回归）
- §12 通用工程门（引用，不复述）
**验收凭据形式**：grep 清零记录 + L1 通过 + 申报表对照
**注意**：改代码后 MCP server 必须重启才生效（runtime-ops）；本阶段 commit 内新旧不并存。

## 3.3 文档拆分与实机对照
**范围**：新建 `strategy-docs/28_invest_env_screen.md`（投资环境画面策略正本篇：标尺、四价值组件语义、系数/立场表指针=常量名、刷新判据、交互规则；值不落文档）；`25_event_overlays.md` 删投资环境相关行；`13_pick_family.md` `decide_invest_env` 行改指策略层新文件；`strategy-docs/README.md` §2 补 28 行；kernel 注释指针全面收口（3.2 审查实测 ≥6 簇：`cw_events.py` 模块头与 decide_event docstring 已删 env 轴描述段、`cw_investments.py` 模块头维护清单与 6 处 `cw_env_economy.*` docstring 指针、`cw_comps.gift_hit_tier` 消费契约指向已删 GIFT_FLOOR_*/env 分支、`invest_env.decide_pick` docstring「sim 复用同吃」改「为 sim 复用预留」、`_d_src` 失去消费方的收口裁决）；landing 本文件 3.2 节「33 分位」措辞对齐 §2.7 均值口径；实机一局对照（重启 MCP server 后跑一局，对照 §2.10 申报方向抽验 2-3 个选择帧的归因）。
**设计依据**：宪法六（一画面一文档）；design.md §2.10（注释指针收口项）
**文件面**：`docs/develop/sr_od/application/currency_war/strategy-docs/`（28 新建、25/13/README 修改）、`kernel/cw_events.py`/`kernel/cw_investments.py`/`kernel/cw_comps.py`（仅头注与契约注）、`.debug/`（实机局记录）
**依赖**：3.2
**优先级建议**：4
**完成判据**：
- 28 号稿与代码现状一致（直白表述、值只写常量名）；25/13/README 无投资环境旧口径残留（grep「decide_event」「ENV_PICK_VALUE」于三文档零命中）
- 实机一局完成，投资环境帧选择归因与设计语义一致（抽验帧记录）
- §12 通用工程门（引用，不复述）
**验收凭据形式**：文档对照 + 实机局 run_id 与抽验帧记录

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条复核收口
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1-3.3 全部
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单
- `strategy-docs/28_invest_env_screen.md`（新建即正本） ← 3.3
- `strategy-docs/25_event_overlays.md`：删投资环境行 ← 3.3
- `strategy-docs/13_pick_family.md`：decide_invest_env 行（接口与决策本体指针） ← 3.3
- `strategy-docs/README.md`：§2 分篇表补 28 行 + 25 号行描述去「投资环境」 ← 3.3/返工
- `strategy-docs/16_evaluation_tables_reassessment.md`：ENV_PICK_VALUE/ENV_FACTION_MATCH_FLOOR/GIFT_FLOOR_* 行改退役（本迭代删除，依据 = 本迭代 design §2.10 + P97） ← 末阶段（3.3 实机提请 + 终审提请）
- `strategy-docs/08_events.md`：E1 行旧机制层亲和口径换 28 指针 ← 末阶段（终审提请）
- `kernel/cw_events.py`/`kernel/cw_investments.py`/`kernel/cw_comps.py`：模块头 env 轴归属注与消费位契约注（含 1003-1006 声明的残留指针） ← 3.2/3.3
