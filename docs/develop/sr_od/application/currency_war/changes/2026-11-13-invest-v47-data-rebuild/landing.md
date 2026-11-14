# 投资域 v4.7 数据层重建 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`，约 2.5 分钟；L3 全量仅在收尾 commit 前跑一次）;
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交（测试仓独立 commit）;
- 提交：逐文件点名 `git add`（禁 `-A`/目录级 add）；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 生成器落点修正

**范围**：`gen_plaza_invest.py` 删除人读版文档产出（DOC_MD 常量、render_doc()、写盘与输出行），头注释同步为单产物说明；本会话早前的 CACHE_GLOB 在飞改动随本阶段入库。边界：不改 canon/strip_rich/diff_report 逻辑。
**设计依据**：design.md §2.1
**文件面**：`skills/sr-od-dev-currency-war/scripts/gen_plaza_invest.py`
**依赖**：无
**优先级建议**：8
**完成判据**：
- 文件中不再出现 `invest_cards.md` 引用与 DOC_MD 产出路径；
- 完成前常规检查（本文首节）。
**验收凭据形式**：代码走读（干跑落盘验证在 3.2 一并完成）

## 3.2 base 数据层重建

**范围**：重跑生成器（--cache 用 V4.7 config 缓存）产出 `cw_invest_data.py` V4.7（策略 298 + 环境 73）。边界：不动 cw_investments.py（3.3/3.4 辖域）。
**设计依据**：design.md §2.2
**文件面**：`src/sr_od/application/currency_war/data/cw_invest_data.py`
**依赖**：3.1
**优先级建议**：9
**完成判据**：
- 生成器 diff 输出与本迭代 diff 分析一致：策略 +77/−113/24 效果变、环境 +37/−47（对照 `.debug/temp/cw_invest_v47/diff_v44_v47.md` 汇总行）；
- 文件头版本 = V4.7，条数 = 298/73；
- `from sr_od.application.currency_war.data.cw_invest_data import PLAZA_AUGMENTS, PLAZA_PORTALS` 通过（此时 cw_investments 尚未对齐，预期其 import 失败属正常中间态，3.3 修复）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：生成器 diff 输出留档 + import 冒烟

## 3.3 overlay 孤儿清理与派生适配

**范围**：按 design.md §2.3 五组执行——A 组 22 张 dict 源表删 211 个净退场键（退场名集 = id 级退场 且 名字 ∉ V4.7；同名复活 36 键剔除不删、逐名列 = details/design_scan_v3.txt §A）；B 组 `_ENV_SUFFIX_DERIVED_NAMES` 元组按 V4.7 名单重写（删 31/留 11/加 21，终态 32 名，逐名列 = details/design_scan_v2.txt §A；同名覆盖披露随批）；C 组补 20 条星徽单件 explicit 绑定（机械事实登记，8 张存活条目按 V4.7 卡文重审）；D 组删补遗「追击星徽套组(二)」及其 GRANTS 级联条目（L4330）；E 组反扫闭集守卫直读发放补登记 27 条（裁定 = design §2.3-E）。边界：派生表与 EQUIPMENTS 不碰；机制桥函数代码不删。
**设计依据**：design.md §2.3（表分类/退场名集判据/删除手法/机械验证链/依据标注均在节内）
**文件面**：`src/sr_od/application/currency_war/kernel/cw_investments.py`
**依赖**：3.2
**优先级建议**：9
**完成判据**：
- 机械验证链三条全过（design §2.3：五道守卫 + 反扫守卫 import 通过 / v3+v2 扫描对账归零 / 逐表键数对账，实测数字记录进验收记录）；
- 冒烟 = 策略 298 + 环境 **72**（注册表按名键空间口径，同名双 id 取一名）；GRANTS 终态 62；
- 完成前常规检查（本文首节）。
**验收凭据形式**：design_scan_v3 复跑输出 + import 冒烟 + 逐表对账数字

## 3.4 存活卡数值与具名内容重审

**范围**：按 design.md §2.4 两部分执行——A 部分 24 条对照表逐条（字段改数 / effect_text 镜像同步 / cw_mismatch_policy.py 六处 45s→50s / 触点紧邻注释引文同步）；B 部分同名存活具名登记重审（66 触点 = design_scan_v2.txt §C 55 + design_scan_v3.txt §A 的 ENV_GIFTS 11——其中 36 键同名复活强制重审、30 键同 id 存活轻量核对；逐条对照 V4.7 卡文，不一致按卡文直读同步、一致登记核对一致、不可直读的声明挂账）。边界：未建模面不新增登记。
**设计依据**：design.md §2.4（A 对照表含触点行号；B 处置规则）
**文件面**：`src/sr_od/application/currency_war/kernel/cw_investments.py`、`src/sr_od/application/currency_war/kernel/cw_mismatch_policy.py`
**依赖**：3.2（与 3.3 无相互依赖，可并行）
**优先级建议**：8
**完成判据**：
- 对照表 24 条逐条清零（每条动作完成或标注「无动作/挂账」）；
- B 部分 66 触点逐条有「同步/一致/挂账」结论记录；
- effect_text 与 `.debug/game_data/currency_war/invest_v4.7.json` 官方原文逐字一致（抽查 3 条）；
- import 过；完成前常规检查（本文首节）。
**验收凭据形式**：对照表与触点结论记录 + 抽查 diff

## 3.5 测试修复

**范围**：CW 域测试逐个判断修复（判据 = design.md §2.5 四分类）。边界：不修主分支存量旧红 2 个；不做新增卡的建模登记测试。
**设计依据**：design.md §2.5
**文件面**：`sr-od-test/test/sr_od/application/currency_war/**`（独立 git 仓）
**依赖**：3.3、3.4
**优先级建议**：8
**完成判据**：
- `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 一次通过（存量旧红 2 个除外，须与分支既有红名单一致）；
- 每个修复点有 a/b/c/d 分类判断记录（commit message 或验收记录）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：L1 测试输出 + 分类判断记录

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列文件
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `src/sr_od/application/currency_war/kernel/cw_investments.py` 模块 docstring：V4.4 计数（「投资策略 334 + 投资环境 83」）与版本引用 ← 3.2/3.3 导致
- `src/sr_od/application/currency_war/kernel/cw_investments.py` `_build_strategies` docstring「base 334 条 + 补遗」（L2942）← 3.2/3.3 导致
- `src/sr_od/application/currency_war/kernel/cw_investments.py` `_build_envs` docstring「base 83 条」（L2959）← 3.2 导致
- `src/sr_od/application/currency_war/kernel/cw_investments.py` `get_strategy` docstring「注册表已全量 335」（L3316）← 3.3 导致
- `skills/sr-od-dev-currency-war/references/data-collection.md` 投资行「cw_invest_data(334+83)」（L20）← 3.2 导致
- `src/sr_od/application/currency_war/data/cw_invest_data.py` 头注释（生成器产出自动更新，核对指向 invest_effects.md 的指针行仍在）← 3.2 导致
- 正本区其余「全量 N 条」计数型引用（3.5 期间发现一处改一处，先例叙述型引用不动——design.md §1 不解决 5）← 3.5 导致
