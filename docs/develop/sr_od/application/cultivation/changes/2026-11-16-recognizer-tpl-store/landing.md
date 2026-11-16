# recognizer-tpl-store 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过（只查改动文件，不跑全仓）；
- 本阶段直接受影响测试全量一次通过（`uv run pytest` 指定测试子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段在测试仓提交；
- 删除测试文件前先做 src 指针对账（sr-od-test/README「删除测试的工序」：grep 该测试文件名于 src，零悬空后才删；删后复扫一遍）；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含迭代名与阶段号；提交后 `git show --stat` 复核入库面 = 申报面；
- 改了任何 Python 代码后若要经 MCP 验证运行行为，先重启项目 MCP server（server 缓存已加载模块）；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」「MCP」节。

## 3.1 光锥域迁移

**范围**：新建 `light_cone_tpl_store.py`（卡面库读盘校验 + `card_faces`/`tm_prep_tpls`/`superimpose_tpls`/`icon_tpls`/`icon_feats`/`icon_hists` 六视图，按 design §2.2 映射表与构建纪律；`superimpose_tpls` = 原函数体迁入，无运行时缩放；`_SUPERIMPOSE_NORM_SIZE` 死常量随迁删除）；`light_cone_list_recognizer.py` 改委托（仅 `_superimpose_templates`/`_tm_templates_all`，组合 helper 不动，design §2.4）、icons 三件套删除、`match_owner` 增加 ctx 参数、构建期常量与 `_fg_mask_from_rgb`/`_SIFT`/`_UPSAMPLE_SCALES` 迁出；SrContext 挂 `light_cone_tpl_store`（design §2.3）；`config/light_cone_templates.py` 退役（design §2.5）；测试三件：重写 `test_superimpose_templates_exist`、`_fake_ctx` 加 store 字段、config 测试迁移（design §2.6）。**不含**：遗器域任何文件。
**设计依据**：design.md §2.1–§2.6（光锥侧）、§2.8 裁定①③
**文件面**：`src/sr_od/application/cultivation/light_cone/light_cone_tpl_store.py`（新建）、`src/sr_od/application/cultivation/light_cone/light_cone_list_recognizer.py`、`src/sr_od/context/sr_context.py`、`src/sr_od/config/light_cone_templates.py`（删除）；测试仓 `test/sr_od/application/cultivation/light_cone/test_light_cone_tpl_store.py`（新建）、`test/sr_od/application/cultivation/light_cone/operations/test_light_cone_list_recognizer.py`、`test/sr_od/application/cultivation/light_cone/operations/test_light_cone_owner_match.py`、`test/sr_od/config/test_light_cone_templates.py`（删除）
**依赖**：无
**优先级建议**：5
**完成判据**：
- 重写后的 `test_superimpose_templates_exist` **单跑必过**（单用例选择器直跑，冷路径，design §2.7 直接判据）；
- `test_light_cone_list_recognizer.py` 全文件（含 slow 项，不加 `-m` 过滤）一次通过；
- `test_light_cone_tpl_store.py` 通过（库 == 常量表契约 + 条目自洽）；
- `test_light_cone_owner_match.py` 通过（`match_owner` 加 ctx 后 4 处中本域 2 处更新）；
- src 全仓 grep 归零：`_superimpose_tpl_cache`、`_SUPERIMPOSE_NORM_SIZE`、light_cone 侧 `_tm_prep_cache`/`_tpl_cache`/`_feat_cache`/`_hist_cache`、`iter_light_cone_templates`、`getattr(ctx, 'light_cone_templates'`；
- 生产行为零变化：识别器 diff 仅限缓存访问路径与 design §2.4/§2.5 申报项（review 对照）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试通过输出（含单跑）+ grep 归零输出 + 识别器 diff review

## 3.2 遗器域迁移

**范围**：同构迁移遗器域——新建 `relic_tpl_store.py`（`card_faces`/`tm_prep_tpls`/`icon_tpls`/`icon_feats`/`icon_hists` 五视图 + `RelicTemplate`/`RELIC_TEMPLATE_SUB_DIR`/`relic_template_id` 迁入 + 连结绳 pos==6 双档分支保留在构建逻辑内）；`relic_list_recognizer.py` 改委托（仅 `_tm_templates_all`）、icons 三件套删除、`match_owner` 加 ctx；SrContext 挂 `relic_tpl_store`；`config/relic_templates.py` 退役；`sr_relic_sets.py` 模块 docstring 指向 config 的持久指针改指 store（仅该注释行，design §2.5）；测试：`_fake_ctx` 加 store 字段、config 测试迁移、owner 基准 2 处调用补 ctx。**不含**：光锥域文件。
**设计依据**：design.md §2.1–§2.6（遗器侧）、§2.8 裁定①③
**文件面**：`src/sr_od/application/cultivation/relic/relic_tpl_store.py`（新建）、`src/sr_od/application/cultivation/relic/relic_list_recognizer.py`、`src/sr_od/mys/sr_relic_sets.py`（仅 docstring 指针行）、`src/sr_od/context/sr_context.py`、`src/sr_od/config/relic_templates.py`（删除）；测试仓 `test/sr_od/application/cultivation/relic/test_relic_tpl_store.py`（新建）、`test/sr_od/application/cultivation/relic/operations/test_relic_list_recognizer.py`、`test/sr_od/application/cultivation/relic/operations/test_relic_owner_match.py`、`test/sr_od/config/test_relic_templates.py`（删除）
**依赖**：3.1（SrContext 同文件，防同文件在飞冲突）
**优先级建议**：5
**完成判据**：
- `test_relic_list_recognizer.py` 全文件一次通过（`_fake_ctx` 补 store 后 `test_relic_recognizer`/`test_detect_pos_from_tabs` 恢复；`test_pos_template_subset` 零改动项经薄委托生效）；
- `test_relic_tpl_store.py` 通过（库 == 常量表 + `relic_template_id` 公式锚）；
- `test_relic_owner_match.py` 通过；
- src 全仓 grep 归零：relic 侧 `_tm_prep_cache`/`_tpl_cache`/`_feat_cache`/`_hist_cache`、`iter_relic_templates`、`getattr(ctx, 'relic_templates'`、`config/relic_templates`（含 sr_relic_sets.py 指针改指后）；
- 两域 grep 联合复核：`global` 语句在两识别器文件归零；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试通过输出 + grep 归零输出 + 识别器 diff review

## 3.3 全量口径一致性终验

**范围**：双口径全量各跑一次并 diff 失败集合，验证 design §2.7 验收口径。不修任何非本迭代范围的既有失败。
**设计依据**：design.md §2.7
**文件面**：无代码改动（纯验证批；若暴露本迭代引入的新失败，回 3.1/3.2 打回修复后重跑）
**依赖**：3.1、3.2
**优先级建议**：6
**完成判据**：
- 基线留档：3.1 开工前当次工作区 HEAD 上双口径各跑一次的新鲜失败清单（design §2.7 基线口径；3.1 开工时已产生，本阶段对照消费）；
- `-m "not slow"` 与全量两口径失败集合逐条一致；
- `test_superimpose_templates_exist` 不在任何失败集合中；
- 相对新鲜基线无新增失败文件（design §2.7 既有失败清单仅作漂移参考；基线漂移 = 并行批在飞所致时在验收记录申报，不回打本迭代）；
- 完成前常规检查（本文首节；本阶段无代码改动则提交/删除项不适用，失败集合 diff 输出随验收记录）。
**验收凭据形式**：两份失败清单 diff 输出

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致（store 挂载/单一入口指向逐条对照代码）
**验收凭据形式**：文档对照 review

## 正本更新清单

- `docs/develop/sr_od/application/cultivation/README.md` §1（域结构树补两 store 文件）← 3.1/3.2
- `docs/develop/sr_od/application/cultivation/README.md` §3（识别器自含口径：模板库与缓存归属改为域 store；卡面库单一入口从 config 改指 store）← 3.1/3.2
- `docs/develop/sr_od/application/account_profile/mys-data.md`「识别模板规范库」段（遗器遍历入口改指 `relic_tpl_store.py`）← 3.2
- `skills/sr-od-dev-cone-data/SKILL.md`「识别模板库」段与「对齐链」段（遍历单一入口改指 store）← 3.1
- `skills/sr-od-dev-cone-data/design/overview.md`「项目侧配套」条（改指 store）← 3.1
- `skills/sr-od-dev-relic-data/SKILL.md`「模板库」段与「双库关系」段（遍历入口改指 store）← 3.2
- `skills/sr-od-dev-relic-data/design/overview.md`「loader」条（改指 store，ctx 级缓存语义不变）← 3.2
