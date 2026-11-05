# equip-taboos-retirement 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- L1 快速集（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`）全绿——零行为退役的本批验证面（无更高级验证义务：无行为可观察，design §2.2）；
- 提交：逐文件点名 `git add`；commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。

## 阶段 3 代码落地

**范围**：design §2.1 第 1-3 条——字段删除、唯一消费点删除、数据行删除。
**完成判据**：
- `grep -r 'equip_taboos' src/ sr-od-test/` 零命中；
- cw_intention `_line_hoard` 返回值形态不变（`tuple[set, set]`），万敌囤货装备集退役前后恒等（恒等由 design §1 症状 1 交集式保证，落地后抽查 `_line_hoard(万敌)` 返回值含全部 4 件关键装备）；
- 完成前常规检查。

**验收凭据形式**：grep 记录 + `_line_hoard` 抽查输出 + 测试名。

## 阶段 4 文档收尾

**范围**：design §2.1 第 4-5 条——P42 三处注记、10 号稿两处、comp-definition skill 两处。
**完成判据**：
- P42 正文推导未改写（diff 仅注记行）；
- 正本与 skill 措辞与代码现状一致（`equip_taboos` 符号在活文档零残留；proofs 留档注记豁免）；
- README 进度收尾 + 遗留登记清零。

**验收凭据形式**：文档 diff 对照。
