# 0005. 截图手动分解 op 节点,不靠跑 app/op 中途 capture

- **Status**: accepted
- **Date**: 2026-08-04(形式化;原始踩坑 2026-07-12 起)

## Context
跑 app(`run_standalone_app`)/ 跑单个 op(`run_operation`)中途 `capture` **抓不到中间态** —— op 执行快、且会**自动消费中间画面**(如确认弹窗被 op 自己点掉),sleep 完再 capture 只能看到 op 跑完的结果(如落地入口),抓不到中间弹窗。实战多个玩法(scratch_card / drive_disc_dismantle / engagement_reward / city_fund)跑完回大世界时 capture,目标子态(嗷呜对话 / 刮层 / 快速选择 / 领取弹窗)早已错过;scratch_card 更受每日一次时机限制。核实:`run_operation` 跑单个 op 和 `run_standalone_app` 一样自动消费中间画面。

配套踩坑(随实战补强):
- **transport 后角色朝向**:传送后角色朝向**继承传送前**(若传送前已在同一地图)。app 常假设 transport 后固定朝向 `move_w`+`interact`;手动复现需先传送别的地图、再传送回目标,朝向重置到默认。
- **手动 move 距离要与 app 一致**:`suibian_temple` 入口实拍时 `key_tap w` 走 2.5s 错过交互点 —— `SuibianTempleApp.goto_suibian_temple` **无 move**(Transport 后直接 OCR「前往随便观」,传送点就在交互范围内),盲走 2.5s 过了交互点;同期 `coffee` / `random_play` POINT_1 是 `turn_to_angle` + `move_w 1s`。
- **操作后等动画再 capture**:底层 `click_game` / `key_tap` / `drag` **无内置等待**(等待在框架 operation round 层 `success_wait`,MCP 不经 round)。F 交互后立即 capture 截到旧画面;move 后不 sleep 紧接 interact 会失效(issue #2405,scratch_card 代码 sleep 1)。
- **可交互对象 `>` 名字 `<` 三角形**:星穹铁道 NPC / 交互对象进入可交互范围时,名字左右出现三角形标记(如 `> 狮耶 <`)。OCR 常只识出名字漏了 `>` `<` 符号,vision 也不懂这约定 → 双双误判「没到,还要走」(我盲走 0.5~2.5s 反而过头)。同期误以为入口是「OCR 点文字」,实际是 Transport 后传送点旁 interact 狮耶(NPC)→ 出「前往随便观」。
- **边缘状态态**:游历收获需到期 / 饮茶缺料需材料不足 / 邦巢持有上限需满 / S 级需刷新出 —— 会话内创造不了,智能体盲刷空跑(随机态)/ 创造不了(条件态)。随便观 B 类全靠用户帮切 4 画面才补全。
- **Transport 失败 = 地图未探索**:`hou_hou_bakery`(3.0 玩法,布亚斯特城区)`run_operation Transport` 两次失败 —— Transport 打开地图后选不中目标传送点(88s OCR 重试超时),根因是用户未探索该城区、传送点未解锁。但 OCR 识别 / 地图加载 / 目标名不匹配 / 超时也会同状,结合地图截图 + server 日志 + 超时节点确认后再下结论。

## Decision Drivers
- **抓得到中间态**:op 自动消费中间画面,中途 capture 必错过。
- **复现可重复**:手动分解读 op 代码,按 app 的距离 / 对象复现。
- **人机协作**:边缘状态态靠用户造条件,比智能体盲操作高效。

## Considered Options
1. **跑 app/op 中途 capture**:op 快 + 自动消费中间画面 + 运行慢三重叠加 → 抓不到中间态。
2. **手动分解 op 节点 + 单步 capture**(选中):读 op 代码,每步一个 click/key_tap/drag + capture。
3. **改 op 加 capture 钩子**:改框架代码成本高,不通用。

## Decision
选 2:
- app/op 内部连续动作(transport→move→interact→drag→…→各弹窗)产生的画面,按 op 的 `@operation_node` 节点逻辑**手动分解成单步** —— 读 op 代码,每步一个 `click_game` / `key_tap` / `drag` + `capture`,逐步截图(在 op 会自动点的弹窗处**停下、手动不点、先 capture**)。跑 app / run_operation 只用于「验证流程通」或「到位」,不用于抓中间态画面。
- **手动复现 move 前,先读 app/operation 的 `@operation_node` 链**(move_w press_time?turn_to_angle?interact 哪个 NPC?),按 app 的距离 / 对象复现;走多了反而错过交互点(角色过头,提示消失)。
- **操作时序**:操作后等动画再 capture。关键 sleep 点:move 后等角色到位(不等紧接 interact 会失效);interact(F)长按(`press_time>0`)非短按 tap。**sleep 建议值**:click ~1s / move ~1s / interact 1-2s / esc ~0.5s / drag ~0.5s。
- **可交互对象判据(`>` 名字 `<` 三角形)**:出现即在交互范围,`interact F` 即可(不需再走)。OCR 漏三角符号时看 NPC 名是否在画面稳定 + 对照 app 假设的位置;vision 提示词要明确「可交互对象名字左右有 `>` `<` 三角形,出现即已可交互,不要再走」。F 提示文本未必是 F 实际交互对象(如 F 提示小贩但实际 interact 了狮耶)→ F 实际选中的对象看结果画面。
- **transport 朝向重置**:手动复现 app 的 `move_w`+`interact` 前,先传送别的地图再回目标,重置朝向到默认。
- **Transport 失败排查**:Transport 打开了地图但选不中目标点 → 先确认目标地图已探索、传送点已解锁(新版本玩法 / 新城区尤甚),否则换已解锁的 app 建档。
- **边缘状态态**:依赖「资源消耗 / 时间 / 随机」而非「导航可达」的状态态 → 标「待条件」,别硬刷。处理:① doc 标「待条件」+ 已拍的核心态先归档;② 请用户帮切(用户调游戏状态造条件);③ 后续会话条件出现时补。

## Consequences
- **正向**:抓得到中间态;复现按 app 代码有据;边缘态走人机协作不空跑。
- **负向**:手动分解读 op 代码成本高(必要时);依赖用户帮切(非纯自动)。
- **边界**:本游戏追尾视角下「看到角色背部 = 正对前方」(仅适用追尾摄像机 + 当前场景,勿泛化所有第三人称画面);朝向以 OCR 交互提示 + interact 结果为最终判据(见 [ADR-0004](0004-vision-required.md))。

## Links
- SKILL.md「截图获取:手动分解动作,不靠跑 app 中途」+ 子节(transport 复现 / 操作时序 / 边缘状态态)。
- 相关:[ADR-0004](0004-vision-required.md)(vision 不可信边界)、[ADR-0001](0001-five-step-flow.md)(五步流)。
