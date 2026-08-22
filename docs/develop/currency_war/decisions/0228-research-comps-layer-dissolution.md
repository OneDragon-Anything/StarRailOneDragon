# ADR-0228 撤销 research/comps 打法卡层(final_comps 十类为单一源)

## Status

accepted(2026-08-22;用户裁定)

## Context

`research/comps/`(20 张打法卡,ADR-0212 建,组织轴 = COMP_LIBRARY 20 条目)与 `research/final_comps/`(十类深读,2026-08-21 用户提案 r171,组织轴 = CARRY 分类,784 篇 Final 段全量校准)内容双源:同一批事实(7 级 D 三星姬子/领航员绑三月七/装备铁三角/降级路径/counter)两边都有,互不引用、无边界声明。版本更新时同一结论要改两处。

## Decision Drivers

- 用户裁定:「删掉 comps,final 那套已经是我们校准过的了」
- final_comps 数据更新更深(784 篇全量 vs 攻略先验+零星 ADR)
- research 自身纪律:「整段搬运 = 双源,禁止」

## Considered Options

1. 保留两轴立硬边界(comps 瘦身成指针卡):20 张薄卡维护成本不值
2. **撤销 comps,final_comps 为单一源**(选):三套长尾 comp(昼神阿雅/景元仙舟/龙丹战技点——final_comps 未建类或只散见)增量并入新建 final_longtail_others.md;17 张卡经关键词覆盖度审计为十类文档子集,直接删
3. 反向拆 final_comps 进 comps 卡:丢失类级规律(A-E 全局总结)与分类学价值

## Decision

选 2。覆盖度审计脚本留档于本 ADR 提交的 git 历史;COMP_LIBRARY 与 final_comps 的映射由 final_comps/README 类索引表承载(每类 CARRY 列);ADR-0212 的「打法卡」概念自此由 final_comps 类文档承担,cw_comps.py 两处注释指路已更新。
