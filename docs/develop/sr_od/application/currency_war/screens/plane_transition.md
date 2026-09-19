# 位面过渡(plane_transition · 货币战争-位面过渡)

> 代码 = `operations/cw_screen/cw_screen_plane_transition.py::CwScreenPlaneTransition`(两 node 直继承 `SrOperation`)。职责:「点击空白处继续」提示出现即点空白(简报「下一步」后 / 每个 boss 位面开始时各一次);完成 = 提示消失(真转移)交回循环;提示未现 = 该步不适用(fail 交编排壳/循环重新分流)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 分发 = **阶段一身份行(节点锚)**:双「位面」id_mark 全命中即派发本屏 op;身份臂含 boss 判别排他——帧含「强敌」片段(判别单一源 = `cw_screen_boss_briefing.py`)时接管派发 BOSS 简报,不派本屏 op(防 boss 帧位面锚可读时误派空 fail)。连续 fail 预算归外环通用网(`OP_FAIL_REDISPATCH_LIMIT`,[../flow/guards.md](../flow/guards.md) §1)。
- 原 0q 误读兜底(提示 rect 派发)已退役(2026-09-16 裁定:未建档实证的故障形态不作兜底理由,见 [../flow/outer_loop.md](../flow/outer_loop.md) §2.3 退役记录)——节点锚 miss 的帧走未知兜底停机留证,证据入库后再议锚加固(节点盘模板化)。

## 2. 画面形态声明

**空决策形态**(纯推进 + 链观察)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 提示门(「提示-点击空白继续」,miss = round_fail 交回外循环重判)→ 底部全亮行读数构造链值 → `report_screen_plane_transition_obs` 落容器(node_path 离场快照双写,见 §6)→ obs 挂实例属性。决策动作 node = 顶部重入裁决(点空白已发 → 提示不在 = 过渡完成 → success;提示在 = 点击未落地 → 重点)→ 点空白推进 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=8` 现役值仅框架异常路径消费)。裁决位序 = pending 先行、miss fail 后置(与未达上限弹窗的 miss 分支内序不同,各屏分支序语义各异,禁跨屏统一)。

## 3. 观察面

提示门 = 「货币战争-位面过渡.提示-点击空白继续」(**本档 area 名无「处」字**;与 BOSS 简报档「提示-点击空白处继续」为两张画面档各自的 area,不相通用)。门 hit → 链观察一次读(`obs/cw_node_reader.py::read_node_sequence` 行读数 → TokenCell 构造,行空/读缺 = chain None 诚实缺位),读+写整体 best-effort(异常抑制,不阻塞点击推进)。观察 payload = `CwScreenPlaneTransitionObs`(`on_screen`/`chain`/`screen`,住 `kernel/cw_screen_report/plane_transition.py`);report = `report_screen_plane_transition_obs` 链写容器(见 §6)。提示未现 = 未到位(上位面未结束)或已过去 → fail 交重新分流。

## 4. 动作面

单动作 = 点空白:`kernel/cw_obs_core.py::area_center('区域-空白点击', '货币战争-位面过渡')` → mouse_move 先行 + click(overlay 族同款点击时序)→ 固定短等(点击异步落地 + 过渡翻页动画)→ 置位。建档缺失 → `round_fail` 留证。

## 5. 终结与交回

重入观察裁决:提示已消失 → `round_success(wait=1.0)` 交回外循环重判(下一位面/流转由全分支判定);点击未落地 → 重点(`round_wait` 循环推进,无防御上限);首发 miss → fail。

## 6. 状态上报面

链观察写(`report_screen_plane_transition_obs`,纯观测写点,调用方的 best-effort 抑制由观察侧保留):`gs.observe(node_path, chain, evidence='transition_snapshot')` 双写——`node_path_baseline` 开局幂等回填(已有值不覆写);防御逐位:chain 缺 = 行空/读缺不写(诚实缺位),非开局且节点镜像缺 = 行归属位面不可知禁猜跳写;离场快照链 diff 触发(`maybe_emit_chain_diff`,snapshot=True 豁免两帧门)随写点同迁。字段节 = [../game_state/fields.md](../game_state/fields.md);链正本 = [../game_state/chain-observation.md](../game_state/chain-observation.md)。

## 7. 子态与 overlay

过渡全屏动画帧,无子态;与 boss 简报的排他见 §1。

## 8. 守卫与防线

`node_max_retry_times=8` 现役值仅框架异常路径消费;连续 fail 预算归外环通用网([../flow/guards.md](../flow/guards.md) §1);误派防线 = 阶段一身份臂 boss 判别排他(§1);节点锚 miss 的帧走未知兜底停机留证(0q 兜底已退役,证据入库后再议锚加固)。

## 9. 遥测与锁面

- journal op 名 = 「位面过渡」;日志前缀 `[cw-flow-plane]`。
- 测试锁:两 node 行为锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py`(位面过渡观察门 miss 早退与链 report/重入裁决组合)(代码注另引 `test_cw_flow_ops.py`(现状:sr-od-test 无此文件,锁面重建归测试仓批;申报见下),现状不在测试仓 = 开放设计注)。
- game 侧知识:[../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #2/#29;画面档 = `assets/game_data/screen_info/currency_war_plane_transition.yml`。

## 开放设计注

代码注引用的 `test_cw_flow_ops.py` 在 sr-od-test 现状无对应文件(锁面重建归属待测试仓清理批,与 [boss_briefing.md](boss_briefing.md)/[wait_one_one.md](wait_one_one.md) 同批申报)。
