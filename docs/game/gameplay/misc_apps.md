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

## 二、消耗品购买 / 合成 app(CustomCombineOp 薄壳)

三个 app 都是 `CustomCombineOp` 薄壳:app 代码只 `run_op` 跑一条**用户路由 yml**
(`config/custom_combine_op/<name>.yml`),真实流程(传送 → 移动 → 交互 → 购买 / 合成)
全在路由里。`CustomCombineOp` 按路由逐条指令分发到已有 SrOperation,最后回大世界。

### 路由指令 DSL(`OpEnum`)

路由 yml 每条 `ops[]` = `{op, data[], allow_fail?}`;`op` 取值与 `data` 形状:

| op | data | 分发到的 SrOperation |
|---|---|---|
| `back_to_world_plus` | `[]` | `BackToNormalWorldPlus`(回大世界,常用作首 / 末指令拉干净起点) |
| `transport` | `[星球, 区域, 楼层, 传送点]` | `TransportByMap` |
| `wait` | `[类型, 秒]`(类型 `in_world` / `seconds`) | `WaitInWorld` / `WaitInSeconds` |
| `move` / `slow_move` | `[x, y]` 或 `[x, y, 楼层]` | `MoveDirectly`(slow_move = 不疾跑) |
| `interact` | `[类型, 词]` 或 `[类型, 词, lcs]`(类型 `world` / `world_single_line` / `talk`) | `MoveInteract` / `TalkInteract` |
| `click` | `[x, y]` | `ClickPoint` |
| `buy_store_item` | `[item_id, 数量]` | `BuyStoreItem`(item_id 见 `StoreItemEnum`) |
| `synthesize` | `[category, item_id, 数量]` | `Synthesize`(item_id 见 `SynthesizeItemEnum`;dispatch 只用 item_id / 数量,category 不参与查找) |

> `patrol` 虽在 `OpEnum`,但 `run_op` 无对应分支 → 路由用了它会 `round_fail`(shipped 路由不用)。
> `allow_fail: true` 的指令失败不中断整条路由(如商品已买光 / 无货)。

### shipped 路由(app 实际跑的)

| app(op_name) | 路由 | 流程概要 |
|---|---|---|
| **buy_xianzhou_parcel**(仙舟过期邮包) | `buy_xianzhou_parcel.yml` | 传送 仙舟「罗浮」·流云渡·1层·积玉坊 → NPC **茂贞** → 对话「我想买个过期邮包试试手气」→ 购 **逾期未取的贵重邮包**(`xianzhou_parcel`,allow_fail)→ 回大世界 |
| **memory_crystal_shard**(领取记忆残晶) | `memory_crystal_shard.yml` | 传送 翁法罗斯·「永恒圣城」奥赫玛·1层·**流憩大厅** → 走到 **追忆残像** → interact「开启追忆残像」→ click(960,980)领取 ×2 → 回大世界(**纯领取,无购买**) |
| **trick_snack**(奇巧零食) | `buy_trick_snack_route_yll6_xzq.yml` | 路线1:传送 雅利洛-VI·行政区·1层·中央广场 → NPC **罗纳德** → 购 **气态流体** + **种子**(allow_fail) |
| | `buy_trick_snack_route_xzlf_xchzs.yml` | 路线2:传送 仙舟「罗浮」·星槎海中枢·0层·宣夜大道 → NPC **货全** → 购 **气态流体** + **种子**(allow_fail) |
| | `synthesize_trick_snack.yml` | 合成 消耗品·**奇巧零食**(`trick_snack`)—— 用路线1/2 买的 气态流体 + 种子 作原料 |

**trick_snack 编排**:`buy_1`(路线1,`route_yll6_xzq` 开关)→ `buy_2`(路线2,`route_xzlf_xchzs` 开关)→ `synthesize_trick_snack`(`synthesize_trick_snack` 开关),三步在 `TrickSnackConfig` 各有开关(默认全开);开关关 → 该节点 `round_success('路线未启用')` 跳过。

**画面复用**:这些 app 不引入新画面 —— 购买走通用商店(见 [商店](../screens/store.md))、合成走 [合成台](../screens/synthesize.md)、传送 / 移动 / 交互在大世界(见 [大世界](../screens/normal_world.md) / [地图](../screens/large_map.md))。

## 备注 / 待查

- **开发工具 vs 玩法**:calibrator / large_map_recorder 是 dev 工具(校准 / 录制),非玩法 —— 建档归类到「开发 / 维护」,日常一条龙不跑。
- **路由完整性测试**:`sr-od-test/test/sr_od/operations/custom_combine_op/test_custom_combine_op_config.py` —— 校验 shipped 路由的 op / data 形状 / item 枚举解析(改坏路由即暴露)。
- **消耗品 app 现状**:三个 app 流程已对齐 shipped 路由(见上「shipped 路由」表);路由随游戏版本 / 商店变动时,以 `config/custom_combine_op/` 的 yml 为准。
- **one_dragon_app / notify**:框架级(一条龙总调度 / 通知),非独立玩法,不单独建档。
