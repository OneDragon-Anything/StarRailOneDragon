# 遭遇画面策略层迁移与判据激活

## 文档
- 设计总纲:[design.md](design.md)
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:定稿（2026-09-24；三项用户裁定已回写 design §2.2/§2.10）
- 设计对抗:收敛（九轮，累计 83 项发现全部处置） · 报告=[attack.md](attack.md) · [attack-r2.md](attack-r2.md) · [attack-r3.md](attack-r3.md) · [attack-r4.md](attack-r4.md) · [attack-r5.md](attack-r5.md) · [attack-r6.md](attack-r6.md) · [attack-r7.md](attack-r7.md) · [attack-r8.md](attack-r8.md) · [attack-r9.md](attack-r9.md)
- 落地:3/3 done（3.1 = 56ed73db/测试仓 c763b1c6；3.2 = 8922f97d2/测试仓 0e340efa；3.3 = 405731119；review-31/32/33 全过）
- 正本更新:清零（31 号稿新建 + 25/13/08/04/README + 两画面文档；01 号稿 §6 闸门位立场值修订随裁定补落）

## 遗留挂账（后续批，登记备查）
- architecture.md:144 模块地图行过期（cw_events/cw_encounter_selection 判据均已迁策略层）→ CW 正本维护小批（与 25 号稿银狼升星行缺项、screens/encounter.md 两处 game 侧链接显示文本 cosmetic 一并）。
- 补给孪生面防线（cw_screen_supply_node 重调分支同款循环面）→ 归补给域/op-layer §1.4 全域条款批（31 号稿挂账在册）。
- 实机验证前置：MCP server 重启（改码生效；避开对局运行期）。

## 已裁定（2026-09-24 用户）
1. EV 核退役删除（design.md §2.10 裁定点 1）。
2. 章程 §6 修订（新增闸门位立场值形态）+ 边缘态 cap = 2 批准生效。
3. 奖励偏好序（钻 > 装备 > 金币 > 末档）批准生效。
   - 2/3 用户备注：暂定值，实机遥测数据累积后重拍（重拍触发器 = 遭遇帧判读积累）；过目记录 = 本节 + design §2.2/§2.10 回写。

## 待用户过目（设计 §2.2 形态申报，捆绑同一裁决门）
- 边缘态难度上限 cap 与奖励偏好序——逐项详述见与用户的裁定对话记录；过目记录 = 落地验收凭据。
