# 行迹升级 op 重构：面板态起点 + agent 选节点（外溢迭代·占位）

## 承接出处
- 源迭代：`docs/develop/sr_od/application/echo_of_war/changes/weekly-challenge-core/`（行迹刷取接入的外围）；探索记录 `.debug/temp/operation-explore/2026-11-14-行迹升级流程/`（全量实测事实）
- 用户裁定（2026-11-14）：程序层不做技能树节点选择（树形随命途/角色变，固定坐标不可维护）；op 起点改「角色-行迹·面板态」（`target` 校验面板技能分类，不符显式失败）、终点 = 收尾关面板回树态；节点三态判据（黯淡=未激活/鲜明无数字=无需升级/带数字读 X/Y）归 agent 读画面

## 范围（一句话）
重构 `UpgradeTraceOp`：起点/终点改面板态↔树态契约；删除固定节点点击区路线，改 agent 选节点 + op 校验；auto_farm 券刷链补齐（连刷次数参数接入 + `_FARM_TICKET_PER` 常量按实测回填为花萼赤 10+券 1/次）；参数面与光锥/角色线对齐（`auto_farm`→`farm_dungeon`、补 `use_fast_ticket` 或显式声明差异、`node_max_retry_times` 对齐）；收尾日志改实际值记账（修配置值 -1 打负数问题）。

## 状态

已并入迭代 `cultivation/changes/upgrade-ops-adaptation/`（块 D，details/trace-rework.md）。本占位不再单独立项。
