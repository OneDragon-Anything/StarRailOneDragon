---
name: sr-od-dev-map-data
description: 维护崩坏:星穹铁道「大世界地图信息」时用——新版本新星球/新区域录入、区域/传送点/特殊点数据增改、副本(指南注册表)更新、大地图资产绘制或重录、地图重绘后坐标修正。凡是「新区域录一下」「新副本录一下」「大地图没资产要录」「重绘后坐标怎么改」都用,即使没明说。英文:map data maintenance, region data entry, dungeon data entry, large map record。不触发:锄大地路线编写、巡访 op 开发、小地图识别调参、画面建档(归 od-dev-screen-onboarding)。
---

# 地图信息(区域 / 副本 / 大地图)

三个主题按需路由;同一次版本更新可能涉及多个。**涉及角色数据录入时,副本信息更新必须先做**——角色晋阶材料的「材料→刷取副本」join 以副本注册表为锚,sr-od-version-update-adaptation 的总流程按此排序。

| 主题 | 场景 | 方法 |
|---|---|---|
| 区域信息 | 新星球/新区域录入;区域/楼层/传送点/特殊点数据增改 | `references/region-data-entry.md` |
| 副本信息 | 生存索引副本(花萼/虚影/隧洞/余响/饰品提取等)新增或文本修正 | `references/dungeon-data-entry.md` |
| 大地图绘制 | 区域缺大地图资产、重录、录制失败排查、重绘后路线修正 | `references/large-map-record.md` |

主题间衔接:

- 区域录入通常伴随地图缺失 → 录制流程在 `references/large-map-record.md`;录制产物(底图/定标坐标)的正式落位与 uid 命名回 `references/region-data-entry.md` 执行。
- 三个主题的验证都以「框架加载 + GUI 可见 + 名字关联不断链」为底线判据,各自方法文档内带具体 checklist。

公共纪律:

- 官方接口(srmap / wiki)数据先快照再消费,快照即单一事实源;编辑者手标类内容(点位)只作线索,存在性以实机裁决;接口打法见 sr-od-dev-official-api。
- 未覆盖的地图类需求先查两份方法文档的落位规则;仍无方案按「调研影响面 → 与用户确认 → 补档对应方法文档 → 再实施」扩展,禁凭猜直改。
