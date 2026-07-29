---
gameplay_name: 辅助 app 总览(开发工具 + 消耗品购买)
last_updated: 2026-07-29
source: `application/` 各 app 代码(calibrator / large_map_recorder / buy_xianzhou_parcel / memory_crystal_shard / trick_snack)
---

# 辅助 app 总览

非核心玩法的辅助 app,分两类:**开发工具**(校准 / 录制,dev 用)和**消耗品购买 / 合成**。

## 一、开发工具 app(非玩法,dev / 维护用)

### calibrator(校准)
- op_name「校准」。**校准小地图定位 + 角色朝向**(大世界导航准确性前提)。
- 流程:`tp1`/`tp2`(传送去校准点)→ `check_mini_map_pos`(小地图定位校准)→ 转向校准。
- 用途:大世界自动导航(move/小地图找敌)依赖准确的小地图坐标 + 朝向,校准器修正偏移。

### large_map_recorder(大地图录制)
- op_name「大地图录制 <区域>」。**录制大地图区域数据**(自动行驶的路线 / 坐标)。
- `LargeMapRecorder` + `RegionRecorderCheckPoint`(检查点 max_row/max_column)。
- 用途:为 world_patrol(锄大地)/ 各玩法大世界导航录制区域路线数据(传送点 / 移动节点),是自动跑图的数据来源。
- 关联 [world_patrol](world_patrol.md) 路线数据。

> calibrator + large_map_recorder 是**维护自动导航的 dev 工具**,非日常玩法,普通用户不直接用(开发 / 录制路线时用)。

## 二、消耗品购买 / 合成 app

### buy_xianzhou_parcel(买仙舟包裹)
- `run_op`(执行自定义指令)。购买仙舟包裹(消耗品 / 礼包)。

### memory_crystal_shard(记忆水晶碎片)
- `run_op`(执行自定义指令)。记忆水晶碎片相关(领 / 买道具)。

### trick_snack(奇巧零食)
- op_name「奇巧零食」。`buy_1`/`buy_2`(购买路线 1/2)+ `synthesize_trick_snack`(合成零食)。
- 奇巧零食:战斗用消耗品(临时增益),购买 + 合成。

> buy_xianzhou_parcel / memory_crystal_shard 用 `run_op`(跑用户配的自定义指令,非固定流程);trick_snack 有固定购买 / 合成路线。

## 备注 / 待查

- **开发工具 vs 玩法**:calibrator / large_map_recorder 是 dev 工具(校准 / 录制),非玩法 —— 建档归类到「开发 / 维护」,日常一条龙不跑。
- **自定义指令 app**:buy_xianzhou_parcel / memory_crystal_shard 的 `run_op` 跑用户自定义 op(灵活,非固定流程),待 `describe_operation` 细化。
- **trick_snack 流程**:购买路线 1/2 + 合成,具体路线待实拍。
- **one_dragon_app / notify**:框架级(一条龙总调度 / 通知),非独立玩法,不单独建档。
