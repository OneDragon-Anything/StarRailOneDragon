# 羁绊数据域 v4.7 重建 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关子集；收尾阶段跑 L1 全量）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 前置依赖（外部，非本迭代阶段）

- **角色注册表 v4.7 重建**（另一会话）：阶段 2/6 的硬前置——members 翻译、成员对拍、开拓者条目消失。未就绪时仅阶段 1 可开工。

### 3.1 聚合器核心（gen_factions 改造·生成段）

**范围**：`gen_factions.py` 重写为聚合生成器——config 骨架过滤（type 0/1/2）+ 帖子聚合（layers/role_ids/simple_desc，去重规则 = 层数最多、新帖优先）+ count_mode 判定表（千星商会 STAR3 带引文校验）+ wiki 交叉验证报告段；产出**中间产物**（id 形态 Trait 全量 + 三源报告 stdout）。边界：不含成员翻译（阶段 2）、不落 `cw_traits_data.py`（阶段 3）、不动消费点。
**设计依据**：design.md §2.1-2；details/trait-data-layer.md §2/§4
**文件面**：`skills/sr-od-dev-currency-war/scripts/gen_factions.py`；报告样本落 `.debug/temp/currency_war/`
**依赖**：无（角色表未就绪亦可开工）
**优先级建议**：8
**完成判据**：
- 29 条 Trait 中间产物 id 形态齐全（config 骨架逐键对拍通过）；
- 聚合覆盖对拍通过（layers 全档位，无「骨架有而聚合无」报警）；
- wiki 交叉报告产出（27 词条比对 + 缺收清单）；
- <完成前常规检查（本文首节）>
**验收凭据形式**：三源报告 + 中间产物文件；覆盖对拍零 diff

### 3.2 翻译与对拍闭环（gen_factions·生成段续）

**范围**：role_ids → 角色规范名翻译（同名多档合并/隐藏条目过滤/fail-closed）+ 成员对拍（官方 vs 注册表自报，例外清单机制）+ `cw_traits_data.py` 全文渲染功能就绪。边界：不执行落库（阶段 3 执行），例外清单首版为空待人裁。
**设计依据**：design.md §2.1；details/trait-data-layer.md §2 翻译/§3 对拍
**文件面**：`skills/sr-od-dev-currency-war/scripts/gen_factions.py`
**依赖**：3.1；角色注册表 v4.7 重建（外部前置）
**优先级建议**：7
**完成判据**：
- 翻译零 fail-closed 触发（或触发的 id 已提交角色会话处置并有结论）；
- 成员对拍差异清单产出并逐条人裁（放行进例外清单 / 修角色注册表）；
- 生成器 dry-run 输出完整 `cw_traits_data.py` 预览；
- <完成前常规检查（本文首节）>
**验收凭据形式**：对拍报告 + 人裁记录；dry-run 预览通过数据层 import 烟测

### 3.3 数据层落库与旧模块退役

**范围**：执行生成器落库 `cw_traits_data.py`；`data/cw_factions.py` 整文件退役；`ISOLATED`/旧 `MEMBER_EXCEPTIONS` 概念消亡。边界：不动消费点（阶段 4-6）——本阶段结束存在「消费方 import 断」中间态，故本阶段与阶段 4 同一提交序列连续落地（落地批可同 worker 连续执行）。
**设计依据**：design.md §2.1-1；details/trait-data-layer.md §1
**文件面**：`src/sr_od/application/currency_war/data/cw_traits_data.py`（新增）、`data/cw_factions.py`（删除）
**依赖**：3.2
**优先级建议**：7
**完成判据**：
- `cw_traits_data.py` import 通过 + 结构守卫测试绿（键集一致/count_mode 枚举/members sanity）；
- 旧 `cw_factions.py` 无残留引用（阶段 4-6 完成后复核）；
- <完成前常规检查（本文首节）>
**验收凭据形式**：import 烟测 + 结构守卫测试名

### 3.4 消费点迁移·A 类（纯字段路径）

**范围**：consumer-migration.md §2 A 类 13 文件——`FACTIONS[x].tiers/get` → `trait_by_name[x]` 投影；沿用/疑似改名羁绊按映射表 §1 核对（疑似项对照 desc 原文落确认）。边界：B 类失效逻辑（3.5）、死代码（3.6）不在本阶段。
**设计依据**：design.md §2.2 契约；details/consumer-migration.md §1/§2 A 类
**文件面**：A 类清单 13 文件
**依赖**：3.3
**优先级建议**：7
**完成判据**：
- A 类文件 `FACTIONS` 引用清零（grep 复核）；
- 疑似改名 2 项有 desc 对照结论（沿用确认或改判消失+新增）；
- <完成前常规检查（本文首节）>
**验收凭据形式**：grep 清零 + 映射核对记录

### 3.5 消费点迁移·B 类（失效逻辑处置）与边界处置

**范围**：consumer-migration.md §2 B 类（消失羁绊的失效逻辑段：量子同频/贝洛伯格特判、列车同行系统卡、燃血名单、引擎阵营表键更新）+ §4 边界处置（COMP_LIBRARY 退役标记防孤儿、旧 fixture 测试 skip 策略）。
**设计依据**：design.md §2.2 契约；details/consumer-migration.md §1 消失档/§2 B 类/§4
**文件面**：B 类清单文件 + `cw_comps.py`（仅退役标记与字段路径）+ `cw_plaza_posts.py` 消费测试
**依赖**：3.4
**优先级建议**：6
**完成判据**：
- B 类逐处有处置结论（重写/退役标注）且 grep 复核消失名清零；
- COMP_LIBRARY import 不炸（防孤儿校验通过）；fixture 相关测试 skip 标注到位；
- <完成前常规检查（本文首节）>
**验收凭据形式**：处置记录 + import/测试输出

### 3.6 死代码删除（开拓者双形态 + 布洛妮娅选边）

**范围**：consumer-migration.md §2 C 类 14 文件——机制函数与调用分支整体删除（用户裁定 2026-11-13）。边界：注册表条目删除归角色批（本阶段前置已含）；旧赛季帖子 fixture 数据不动。
**设计依据**：design.md §2.1-4；details/consumer-migration.md §2 C 类
**文件面**：C 类清单 14 文件
**依赖**：3.3；角色注册表重建（外部前置）
**优先级建议**：6
**完成判据**：
- `is_trailblazer|trailblazer_|SIDE_PICK_DUAL_BONDS|side_pick_bond` 全仓 grep 清零（fixture 数据字面除外）；
- 挂账板对应条目闭环销项；
- <完成前常规检查（本文首节）>
**验收凭据形式**：grep 清零 + L1 子集测试输出

### 3.7 测试补齐与全量验收

**范围**：数据层结构守卫测试 + 对拍闭环测试落仓；测试仓 FACTIONS 引用排查迁移；L1 全量对照验收（基线 = 迭代前等价，存量旧红 2 个除外——挂账板在案）。
**设计依据**：details/consumer-migration.md §5；details/trait-data-layer.md §3
**文件面**：`sr-od-test/test/sr_od/application/currency_war/**`
**依赖**：3.4 / 3.5 / 3.6
**优先级建议**：6
**完成判据**：
- 新守卫测试 + 对拍闭环测试落仓通过；
- L1 全量输出与基线对照记录；
- <完成前常规检查（本文首节）>
**验收凭据形式**：测试名清单 + L1 全量输出对照

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `docs/game/currency_war/data/README.md`：注册表清单行（羁绊 `cw_factions.FACTIONS,32` → `cw_traits_data.TRAITS,29` 与生成器指针）← 3.3
- `docs/game/currency_war/README.md`：更新流程节（羁绊重建入口换新聚合命令）← 3.2
- `skills/sr-od-dev-currency-war/references/data-collection.md`：§一羁绊行（两跳采集通道 → 新聚合通道；生成器职责描述）← 3.2
- `skills/sr-od-dev-currency-war/references/version-update.md`：§3.2 羁绊域行（对拍器描述 → 生成器+对拍；依赖序声明核对）← 3.2
- `skills/sr-od-dev-currency-war/SKILL.md`：单一源地图（若羁绊数据行提及旧模块名）← 3.3
- `docs/develop/sr_od/application/currency_war/strategy-docs/README.md`：模块地图 data/ 行（cw_factions → cw_traits_data）← 3.3
