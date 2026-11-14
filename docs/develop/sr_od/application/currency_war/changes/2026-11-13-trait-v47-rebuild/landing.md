# 羁绊数据域 v4.7 重建 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关子集；收尾阶段跑 L1 全量）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 前置依赖（外部，非本迭代阶段）

- **角色注册表 v4.7 重建**（另一会话，已收口）：阶段 3.2/3.6 的硬前置——members 翻译与**查表契约**（消费方从注册表 source 字段派生映射，契约见 design.md §2.3；用户裁定 2026-11-14 形态=派生，无需角色批交付符号）、成员对拍、开拓者条目消失。未就绪时仅阶段 3.1 可开工。

### 3.1 聚合器核心（gen_traits.py 生成段）

**范围**：`gen_factions.py` 重写并更名 **gen_traits.py**（对齐官方 trait 口径，第二轮复攻 B6）为聚合生成器——config 骨架过滤（type 0/1/2）+ 帖子聚合（layers/role_ids/simple_desc，去重规则 = 层数最多、新帖优先）+ count_mode 判定表（千星商会 STAR3 带引文校验；**只建模不接线**——板面计数接线不在本迭代，design.md §2.1-5）+ 富文本渲染管线（沿用 render_rich）+ wiki 交叉验证报告段；产出**中间产物**（id 形态 Trait 全量 + 三源报告 stdout）。边界：不含成员翻译（3.2）、不落 `cw_traits_data.py`（3.3）、不动消费点。
**设计依据**：design.md §2.1-2/§2.1-5；details/trait-data-layer.md §2/§4
**文件面**：新增 `skills/sr-od-dev-currency-war/scripts/gen_traits.py`；旧 `gen_factions.py` 随 3.2 完成删除（git 历史可溯）；报告样本落 `.debug/temp/currency_war/`
**依赖**：无（角色表未就绪亦可开工）
**优先级建议**：8
**完成判据**：
- 29 条 Trait 中间产物 id 形态齐全（config 骨架逐键对拍通过）；
- 聚合覆盖对拍通过（layers 全档位，无「骨架有而聚合无」报警）；
- wiki 交叉报告产出（27 词条比对 + 缺收清单）；
- <完成前常规检查（本文首节）>
**验收凭据形式**：三源报告 + 中间产物文件；覆盖对拍零 diff

### 3.2 翻译与对拍闭环（gen_traits.py 翻译/对拍段）

**范围**：role_ids → 角色规范名翻译（查表契约见 design.md §2.3；同名多档合并/隐藏条目过滤/fail-closed）+ 成员对拍（官方 vs 注册表自报，例外清单机制）+ `cw_traits_data.py` 全文渲染功能就绪。边界：不执行落库（3.3 执行），例外清单首版为空待人裁。
**设计依据**：design.md §2.1/§2.3；details/trait-data-layer.md §2 翻译/§3 对拍
**文件面**：`skills/sr-od-dev-currency-war/scripts/gen_traits.py`（3.1 已建，本阶段续写翻译/对拍段）
**依赖**：3.1；角色注册表 v4.7 重建（外部前置，已收口）；查表契约 = design §2.3 派生形态（随本阶段落地）
**优先级建议**：7
**完成判据**：
- 翻译零 fail-closed 触发（或触发的 id 已提交角色会话处置并有结论）；
- 成员对拍差异清单产出并逐条人裁（放行进例外清单 / 修角色注册表）；
- 生成器 dry-run 输出完整 `cw_traits_data.py` 预览；
- <完成前常规检查（本文首节）>
**验收凭据形式**：对拍报告 + 人裁记录；dry-run 预览通过数据层 import 烟测

### 3.3 新数据层落库

**范围**：执行生成器落库 `data/cw_traits_data.py`。边界：**不删 `cw_factions.py`**（旧模块退役移至收尾阶段 3.8，防 import 断中间态——第一轮对抗 A10 重划）；不动消费点。
**设计依据**：design.md §2.1-1；details/trait-data-layer.md §1
**文件面**：`src/sr_od/application/currency_war/data/cw_traits_data.py`（新增）
**依赖**：3.2
**优先级建议**：7
**完成判据**：
- `cw_traits_data.py` import 通过 + 结构守卫测试绿（键集一致/count_mode 枚举/members sanity——守卫测试随本阶段落仓）；
- <完成前常规检查（本文首节）>
**验收凭据形式**：import 烟测 + 结构守卫测试名

### 3.4 消费点迁移·A 类（纯字段路径）

**范围**：consumer-migration.md §2 A 类判据——当日 grep 清单中消费沿用/疑似改名羁绊 tiers/desc/members 的文件，替换 `FACTIONS[x]` → `trait_by_name[x]`；疑似改名 2 项按 desc 原文对照落确认（确认落沿用 / 改判消失+新增）。边界：B 类失效逻辑（3.5）、死代码（3.6）不在本阶段；清单以开工日 grep 输出为准（设计不预写文件名单，见 consumer-migration.md §问题与约束）。
**设计依据**：design.md §2.2 契约；details/consumer-migration.md §1/§2 A 类
**文件面**：按当日 A 类清单（grep 实测生成）
**依赖**：3.3
**优先级建议**：7
**完成判据**：
- A 类文件 `FACTIONS` 引用清零（grep 复核）；
- 疑似改名 2 项有 desc 对照结论；
- <完成前常规检查（本文首节）>
**验收凭据形式**：grep 清零 + 映射核对记录

### 3.5 消费点迁移·B 类（失效逻辑处置）与边界处置

**范围**：consumer-migration.md §2 B 类判据——消失档羁绊名的失效逻辑段逐处处置（量子同频/贝洛伯格特判、列车同行系统卡、cw_gain_chain 策略卡判据 trait_type 语义重定义 §2.1 等）+ §4 边界处置（COMP_LIBRARY 退役标记、旧 fixture 测试 skip、引擎阵营表退役标注、`currency_war_config` DEFAULT_* 豁免声明）。
**设计依据**：design.md §2.2 契约；details/consumer-migration.md §1 消失档/§2 B 类与 §2.1/§4
**文件面**：按当日 B 类清单（grep 实测生成）+ §4 所列文件
**依赖**：3.4
**优先级建议**：6
**完成判据**：
- B 类逐处有处置结论（重写/退役标注）；
- 消失名清零复核，范围按 consumer-migration.md §5 定义（B 类清单文件内消费代码清零；豁免 = 手编策略表退役标注段/currency_war_config DEFAULT_*/注册表与装备与 fixture 历史数据面/注释内引文）；
- COMP_LIBRARY import 不炸（防孤儿校验通过）；fixture 相关测试 skip 标注到位；
- <完成前常规检查（本文首节）>
**验收凭据形式**：处置记录 + import/测试输出

### 3.6 死代码删除（开拓者双形态 + 布洛妮娅选边）

**范围**：consumer-migration.md §2 C 类判据——`trailblazer_*`/`SIDE_PICK_DUAL_BONDS`/`side_pick_bond` 符号与调用分支整体删除（用户裁定 2026-11-13）。边界：注册表条目删除归角色批（本阶段前置已含）；旧赛季帖子 fixture 数据不动；`deploy_search.py` 为 A/C 双处置文件（A 类段归 3.4）。
**设计依据**：design.md §2.1-4；details/consumer-migration.md §2 C 类
**文件面**：按当日 C 类清单（grep 实测生成，含 A6 修正的 obs/cw_observation.py 与 mandate_v1/deploy_search.py）
**依赖**：3.3；角色注册表重建（外部前置）
**优先级建议**：6
**完成判据**：
- `is_trailblazer|trailblazer_|SIDE_PICK_DUAL_BONDS|side_pick_bond` 全仓 grep 清零（fixture 数据字面除外）；
- 挂账板对应条目闭环销项；
- <完成前常规检查（本文首节）>
**验收凭据形式**：grep 清零 + L1 子集测试输出

### 3.7 旧模块退役

**范围**：删除 `data/cw_factions.py`（A/B/C 类迁移全部完成后，全仓引用清零为前提）；`ISOLATED`/旧 `MEMBER_EXCEPTIONS` 概念随文件消亡；注释字面顺手订正（consumer-migration.md §3）。
**设计依据**：design.md §2.1-1；details/consumer-migration.md §3
**文件面**：`src/sr_od/application/currency_war/data/cw_factions.py`（删除）
**依赖**：3.4 / 3.5 / 3.6
**优先级建议**：6
**完成判据**：
- 全仓 grep `cw_factions|FACTIONS` 清零（豁免范围同 3.5 定义 + 注释引文）；
- <完成前常规检查（本文首节）>
**验收凭据形式**：grep 清零 + L1 子集测试输出

### 3.8 测试补齐与全量验收

**范围**：对拍闭环测试落仓（结构守卫已于 3.3 落）；测试仓 FACTIONS 引用排查迁移收尾；L1 全量对照验收（基线 = 迭代前等价，存量旧红 2 个除外——挂账板在案）。
**设计依据**：details/consumer-migration.md §5；details/trait-data-layer.md §3
**文件面**：`sr-od-test/test/sr_od/application/currency_war/**`
**依赖**：3.4 / 3.5 / 3.6 / 3.7
**优先级建议**：6
**完成判据**：
- 对拍闭环测试落仓通过；
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
- `docs/develop/sr_od/application/currency_war/strategy-docs/README.md`：§3 关系表的代码注册表示例行补入 `cw_traits_data`（第一轮对抗 A12 修正锚点）← 3.3
