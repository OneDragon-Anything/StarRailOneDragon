# CW 装备域 v4.7 换赛季适配 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- **装备域测试**（`sr-od-test/test/sr_od/application/currency_war/kernel/test_equip.py` 及本阶段文件面内测试）适配后全量一次通过——期望更新 = 设计裁定行为的申报（重灌/分类迁移是 design.md §2 的裁定行为，测试按新注册表现值更新，逐处注明裁定依据）；**消费方域测试红**（投资/穿戴/策略非装备域文件的红）不在本迭代验收内，逐条登记随跨域迁移批清偿（design.md §2.6）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。

## 3.1 data 层注册表紧耦合批（生成器 + 注册表 + 图谱判据 + 穿戴规则 + 测试适配）

**范围**：①重写 `gen_equip_registry.py`（config 单源直灌：删图鉴 OCR 与 md 兜底两源、官方分类直落、简易装备派生、先对拍旧基准后覆盖写、diff 报告）；②重灌 `cw_equipment_data.py`（模块模板随批：字段定稿/official_category 删除/两常量失效申报）；③`cw_synthesis.py` 进阶配方过滤判据 `'进阶'` → `'进阶装备'`；④`cw_equipment_wear_rules_data.py` v4.7 形态（件级门/类别门/白名单清空、前置表保留——随便骰子两条 v4.7 在库实证、互检骨架保留、文件头申报，design.md §2.3.1）；⑤装备域测试 `test_equip.py` 同步适配（期望更新逐处注明裁定依据）。边界：不动上述文件面外的任何消费方。
**设计依据**：design.md §2.1/§2.2/§2.3/§2.3.1/§2.4
**文件面**：`skills/sr-od-dev-currency-war/scripts/gen_equip_registry.py`、`src/sr_od/application/currency_war/data/cw_equipment_data.py`、`src/sr_od/application/currency_war/data/cw_synthesis.py`、`src/sr_od/application/currency_war/data/cw_equipment_wear_rules_data.py`、`sr-od-test/test/sr_od/application/currency_war/kernel/test_equip.py`
**依赖**：无
**优先级建议**：8
**完成判据**：
- 生成器对旧文件无旧源调用残留（grep 图鉴/md 解析函数与 `parse_skeleton` 外旧函数名零命中）；
- 重灌后注册表 = 官方 105 条 + 派生简易装备 11 件 = 116 件，category 值域 = 官方 7 类 + 简易装备；
- stdout 掉出清单完整输出（旧 158 vs 新 116 对照，交集 84 = 官方侧保留 73 + 派生简易回归 11，双口径随生成器 stdout 输出）；
- 穿戴规则互检 `check_equipment_wear_rule_coverage()` 返回空（门侧清空 + 前置表保留 + 互检骨架保留的 §2.3.1 形态：正向有条目不警、措辞核对骰子 effect 仍含关键词不警、孤儿向门空不警）；
- 合成图谱派生条数与 config 进阶装备 recipes 非空条数一致（36）；
- `test_equip.py` 适配完成且**消费方类别字面量最小迁移预演下全量通过**（已实证）；树状态下的残余红根因在消费方文件（wear_equip.py 两处 `'进阶'` 字面量、cw_investments 好运来转换行源类别），登记进 §2.6 红窗清单随跨域批清偿，禁绿洗不改；
- <完成前常规检查（本文首节）>
**验收凭据形式**：生成 stdout 数字对照（116 件/掉出清单/互检空）+ test_equip.py 全过

## 3.2 模板库对齐分析

**范围**：按配方链子件反查集合 ∪ plaza 69 art 计算保留集，输出 `equip_plaza` 混合库的掉出清单（stdout/落盘报告）。**不删文件**（清理随人工裁定，conservative 口径见 design.md §2.5）。plaza 图 69 个已更新不重复执行。派生简易装备 11 件的模板 png 已验证全部在库。
**设计依据**：design.md §2.5
**文件面**：只读分析 + 报告落盘 `.debug/temp/currency_war/`（如需脚本，临时脚本用完即删）
**依赖**：3.1
**优先级建议**：6
**完成判据**：
- 保留集/掉出清单双列表完整输出，数字对得上（185 = 保留 ∪ 掉出，无遗漏）；
- <完成前常规检查（本文首节，纯分析无代码改动则 ruff/测试项不适用，申报即可）>
**验收凭据形式**：对齐报告（数字对照 185）

## 3.3 跨域影响挂账登记

**范围**：按 design.md §2.6 表逐项登记 CW 跨迭代挂账板（`.debug/progress/CW跨迭代挂账.md`），十项（消费方迁移/两常量重裁/图鉴链退役/改件穿戴语义/固有装备/五类存废/stacking 抽检/wiki 探针/穿戴规则门重建/家族议题）。**与既有条目合并登记不另起重复行**：消费方迁移项与挂账板既有「v4.7 换赛季适配欠账族」的装备贡献表等交叠条目合并；家族议题登记进「等用户裁定（家族级议题）」节；消费方迁移红窗承接指向既有「羁绊消费点迁移批」承接面。
**设计依据**：design.md §2.6
**文件面**：`.debug/progress/CW跨迭代挂账.md`
**依赖**：3.1（登记内容引用本迭代实际产出的掉出数字）
**优先级建议**：5
**完成判据**：
- 十项全部在板（交叠项为合并更新非新建），每项含背景/影响面/去向三要素；
- <完成前常规检查（本文首节，纯文档无代码不适用，申报即可）>
**验收凭据形式**：挂账板对照 review

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `docs/game/currency_war/data/README.md`：装备注册表行（158→116 件口径、数据源单源声明）← 3.1
- `docs/game/currency_war/research/equipment_mechanics.md`：数据单一源声明（图鉴 OCR 校正链退役、config 单源）← 3.1
- `skills/sr-od-dev-currency-war/references/data-collection.md`：装备行（图鉴实采标记 v4.7 免除、生成器单源）← 3.1
- `skills/sr-od-dev-official-api/references/currency-war.md`：装备采集通道声明（config desc 即全文、wiki 不可作数值源）← 3.1
