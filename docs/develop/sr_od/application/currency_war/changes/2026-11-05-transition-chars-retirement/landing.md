# transition-chars-retirement 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关子集；行为批另加全量）；
- 术语清理：本阶段文件面内代码注释与文档的存量黑话按统一术语表 `docs/develop/sr_od/application/currency_war/terminology.md` 清理；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」「文档规范·术语使用」节。

## 3.1 退役批：字段 + 档位机器 + 拒因标签 + 数据 + 测试

**范围**：`Comp.transition_chars` 整字段删除（字段声明 + 21 套 48 行数据 + 关联 docstring 措辞）；送卡档位机器降三档（`_GIFT_TIER_RANK`/`_GIFT_TIER_DOWN`/`_char_gift_tier`/`gift_hit_tier`/`GIFT_TIER_SCORE` + invest_env `_gift_tiers` 期望域常量双侧同步）；概念股期望分受影响清单核对（design §2.2 概念股行）；商店拒因 `transition_char` 键停写（落 `non_line`，退役标签申报区追加）；测试同步（design §2.5 点名清单）。**不含**：正本文档（末阶段）；任何补偿通道/派生标签（design §1 不解决清单）。
**设计依据**：design.md §2.1–§2.5（单文档方案全文）。
**文件面**：`src/sr_od/application/currency_war/kernel/cw_comps.py`（字段/机器/数据/注释）；`src/sr_od/application/currency_war/strategies/impl/mandate_v1/gift_value.py`（键域/docstring）；`src/sr_od/application/currency_war/strategies/impl/mandate_v1/invest_env.py`（`_gift_tiers` 期望域常量）；`src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`（拒因标签段）；`sr-od-test/` 镜像（test_invest_strategy/test_cw_comps/test_shop_session_loop 及 grep 点名处）。
**依赖**：无。
**优先级建议**：10。
**完成判据**：
- 行为对照 design §2.2 申报表：A/B 类门翻转 = 赠卡分 transition 路径断言改 0 值方向；概念股期望分受影响清单逐条核（分母收缩、方向升或归零）；C 类与「锻冶专家:刃 = 10.0」断言不变（压过口径活证）；
- `transition_chars` 符号级 grep 清零（src 生产代码 + sr-od-test；设计文档自身豁免）；
- 档位词 `transition` 一词级 grep 复核四文件面（cw_comps/shop/gift_value/invest_env）——注释与 docstring 措辞残留（如「是 core 非 transition」类对比句）改写或随行删除；
- `GIFT_TIER_SCORE` 键域 = {'core','shared','off'} 且 invest_env `_gift_tiers` 常量同步（import 即验，双侧单侧漏改即炸）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名清单 + grep 零残留记录 + 键域断言输出。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新权威版本文档。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列权威版本文档。
**依赖**：3.1。
**优先级建议**：0。
**完成判据**：清单清零；权威版本与实现一致；黑话终扫（本迭代文件面含 changes/ 自身，按术语表；历史证明文档豁免沿 key-items-retirement 先例）。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `strategy-docs/12_line_and_intention.md`（线与意向：成员三名单口径 → core/shared 两名单；知识卡字段面收窄）← 3.1
- `strategy-docs/28_invest_env_screen.md`（投资环境屏：赠卡分行四档定序 → 三档）← 3.1
- `strategy-docs/29` 号稿（投资策略屏：赠卡分口径同步）← 3.1
- `strategy-docs/10_prep_decisions.md`（字段存留表：transition_chars 行删除）← 3.1
- `strategy-docs/32_unified_sell_priority.md`（让位序：如涉三名单措辞，落地批 grep 定位）← 3.1
- `skills/sr-od-dev-currency-war/references/comp-definition.md`（schema 分层语义「成员」族三档 → 两档；「名单多胞胎」判例补录本字段）← 3.1
- `docs/game/currency_war/research/` 全域 grep 复核（final_comps 各篇 + transition_combos.md + combo_methodology.md：字段名与三名单措辞残留，命中即改——游戏知识叙事本身无同步义务）← 3.1
