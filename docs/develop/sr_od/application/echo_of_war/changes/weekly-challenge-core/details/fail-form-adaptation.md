# 战斗失败新形态适配（详设）

## 问题与约束
- 边界（用户裁定 2026-11-14：周本 app 与开拓力 app 的接入不在源迭代范围）：本篇只定义**共享失败继续件** `ResumeFromBattleFail`——周本核心 op 的 ⑩ 失败分支消费它；`use_trailblaze_power`（开拓力侧）与 `ChallengeEchoOfWar`（周本 app 侧）的失败分支接入为外溢迭代，各自占位目录：
  - `docs/develop/sr_od/application/trailblaze_power/changes/use-trailblaze-power-rehome/`（迁移 + 三处失败消费点接入，含设计草案）
  - `docs/develop/sr_od/application/echo_of_war/changes/echo-of-war-fail-adaptation/`（失败分支接入 + 战斗超时防线，含设计草案）
  - 光锥/角色手动路径：`docs/develop/sr_od/application/cultivation/changes/manual-fail-form-cultivation/`（更早占位）
- 失败画面新形态事实（2026-11-14 花萼+周本真打失败实测，正常途径周本失败由负责人核对一致）：
  - 失败画面 = 「大世界-战斗失败」精准命中，无「退出关卡/再来一次」按钮，新增 推荐队伍等级/弱点/提示行/前往角色攻略，底部「点击空白区域继续」；
  - 点空白 → 回挑战画面（花萼=挑战副本·拟造花萼、周本=挑战副本-历战余响）；
  - 失败检测层已通：battle.yml「战斗失败」文本区(734,138-1190,400)几何覆盖新标题位，`get_tp_battle_screen_state` 可判 BATTLE_FAIL；
  - 点空白后真打父链断裂：关闭副本落大世界-普通（花萼/周本一致）。
- 区域依据：「点击区-空白继续」已建档于「大世界-战斗失败」（commit 2c2dc9bd4）；「按钮-关闭副本」已在「挑战副本」（1838,38-1888,95）与「挑战副本-历战余响」镜像。
- 现状风险声明（外溢迭代落地前持续存在）：`use_trailblaze_power` 与 `ChallengeEchoOfWar` 的失败分支在新形态上无限重试卡死；`ChallengeEchoOfWar` 战斗等待无超时防线（round_wait 无限继续）。

## 方案：共享失败继续件 `ResumeFromBattleFail`（新增，challenge_mission 包）

职责：把画面从「战斗失败画面」交还到「挑战画面」。**只做画面恢复，不做重试/退出决策**（决策归调用方——各 op 的重试预算与退出落点是真差异）。

- 签名：`def __init__(self, ctx: SrContext)`（纯 ctx，MCP 契约合规；作为流转碎片 op 供 op 内委托）。
- 节点链（is_start_node 单节点，node_max_retry_times=5，`timeout_seconds = 3 分钟` 兜底——点空白与旧锚均失效时的最终出口）：
  - **入口两态分流**（新形态与旧形态并存防误伤）：
    - 态 A：「大世界-战斗失败」在场（新形态，id_mark = 标题-战斗失败 + 点击空白区域继续）→ 点 `点击区-空白继续` → until 挑战态锚回归（`挑战副本·挑战按钮`，通用几何对花萼/周本帧均命中——2026-11-14 两形态实测）
    - 态 B：「战斗画面」旧结算锚在场（退出关卡按钮/再来一次按钮——失败形态未变的副本类型回退面，UseTrailblazePower 还服务凝滞虚影/侵蚀隧洞等类目，use_trailblaze_power.py:106-135）→ 点 战斗画面·退出关卡按钮 → until 挑战态锚回归
    - 两态皆不中 → 并入连等封顶路径（失败画面渲染过渡帧的保守覆盖：锚缺席的轮次计入连等计数、不点击），封顶后按下方连等出口失败；转试另一态前先验其锚在场，不在场直接 `round_fail('失败画面未能离开')`（防转态后按「未找到按钮」路径耗尽预算、status 落框架默认文案）
  - **连等封顶**：点空白/点退出后 until 挑战态锚未回归时 `round_wait` 重入，连等 5 轮（wait=2）未回归 → 转试另一态 → 再 5 轮仍未回归 → `round_fail('失败画面未能离开')`（防纯定位区点击恒成功导致的无界等待）
- 出口：`round_success('已回挑战画面')` / `round_fail('失败画面未能离开')`。
- 调用方拿到 success 后自行决策：重发（回各自发起链）或退出（关副本走各自收尾）。
- 本迭代消费方：周本核心 ⑪（weekly-core.md）；外溢迭代消费方：use_trailblaze_power 三处失败消费点、ChallengeEchoOfWar 失败分支（设计草案已迁至各自占位目录）。

## 关键取舍
- **抽共享失败继续件而非各处自写**——「点空白→回挑战画面」逻辑在挑战机制家族至少出现五处潜在消费（核心/use_trailblaze_power×2 消费点/ChallengeEchoOfWar/光锥角色挂账），challenge_mission 包已有共享小 op 先例（ClickChallenge 等）；同族第三次出现即应升公共件（跨件半问），共享件也是后续 battle-loop 统一外溢迭代的收敛面之一。
- **只做画面恢复不做决策**——重试预算与退出落点是各 op 真差异，塞进共享件会让它反向耦合每个调用方的策略；决策留调用方，共享件保持无状态单跳。
