# ADR-0317: 场上同名唯一守卫 + 提案代际校验(游戏规则级约束下沉 cw_state;C1 契约漏洞补口)

- 状态:accepted(补写;行为已随 W48 批 commit,本篇事后落档)
- 日期:原 commit 2026-08-24(cb7a5d50);补写 2026-08-25
- 背靠:W43 sim A/B(重构验收第一轮)暴露的删除门槛阻塞项 1-4,leader
  裁决清单(W43 收账节);W48 执行落码。落点:`cw_state.py`(守卫+代际)
  /`cw_sim.py`(账本 target_comp+事务后重决策)/`cw_sim_checks.py`
  (reason 归一化)。

## 背景与动机

W43 sim A/B(decision_v2 新臂 vs v1 基线)发现四类缺陷,前两类直接
阻塞旧策略删除门槛:

1. **【严重】同名重复上场**:CompTransaction 链把同名角色重复放上
   deployed,A/B 实测旧臂 **54% 轮**出现场上同名重复——board/rung
   读数被污染(同名虚高羁绊计数),且生产上会撞游戏规则(场上同角色
   仅 1)。根因:动作契约 C1 只写了「槽位不越界/索引合法」,**没写
   名字唯一性**——资源约束类条款缺位,契约层无守卫,生成侧也不自查。
2. **phantom_rebuys 177 次**:提案生成→应用之间状态已被同批先行动作
   改变,陈旧提案(指向已变化的槽位/店槽)被照常套用。
3. 账本 `target_comp` 恒空:decision_v2 栈不写 `locked_line`/`bridge_id`,
   decisions.jsonl 对新栈失去判读价值。
4. 三检查器对 d2_ 前缀 reason 误报+失明:豁免边/计数用裸 reason 精确
   匹配,`d2_copy`/`d2_engine_seed` 匹配不上。

**契约漏洞怎么被发现**:不是 review 发现的——C1 契约评审时「槽位
合法」检查项全过;是 sim A/B 批量跑出来 54% 轮同名重复才暴露。这
是本批最重要的方法论结论:**动作契约的「资源约束类条款」(唯一性/
互斥/守恒)静态评审容易漏,因为评审者检查的是「写过的条款是否被
满足」,而缺位的条款不产生检查项;只有模拟涌现(批量 seed 下违规
行为高频显影)能暴露**。后续契约包评审应把资源约束类条款单列一栏,
且即使评审核过也要过模拟涌现验证。

## 决策

1. **同名唯一性下沉 cw_state,判据键 `board_unique_key`**:char_id 空
   (未知身份)→ None 不参与查重(两个未知不是可证明的重复);开拓者
   各排形态(char_id 随排切换)归一为同一键 `__trailblazer__`(场上
   同样仅 1 个开拓者);其余 = char_id 本身。
2. **三处守卫,整事务/单动作拒绝语义统一**:①`_resolve_comp_transaction`
   终态 deployed 名单查重(留下的旧档 + deploy 新上 + fill 填位 + shop
   填位),任一重复 → 整事务拒绝(reason=`duplicate_on_board`,进
   action_log)——原子性口径与金/上限校验同层;②单动作 `DeployMove`/
   `SwapDeploy` 同理拒绝(进 action_log);③`mutate_bench_deployed`
   (runtime 跟踪侧)镜像同守卫 no-op——sim/生产两套状态迁移同源,
   防口径分叉。围栏(deploy fence)语义不动。
3. **代际校验(expect 字段族)**:`FillSpec`/`SellDeployed`/`SwapDeploy`/
   `CompTransaction` 增 `expect*` 字段(默认空=不校验,草案级扩字段):
   提案生成时记录该 idx 指向内容的期望名,应用时不符 → 整事务/单动作
   拒绝(stale_proposal),不套用陈旧引用。sim 侧配套:事务 fill 已
   消费店槽时,同批后续 BuyCard 作废并立即重决策(break-redecide,
   同 RefreshShop 语义)。
4. **账本 target_comp 优先级链**:v2 字段(`locked_line`/`bridge_id`)
   非空优先(旧臂语义不变),空则回退 v3 意向名(`v3_intention.
   locked_comp`,COMP_LIBRARY 套名)。
5. **`_normalize_buy_reason` 单一源 helper**:剥 `d2_` 前缀与 `_merge`
   尾,三检查器(coldstart/同轮买卖/种子回卖/振荡)统一走它。

## Considered Options

- **守卫放生成侧(cw_evolution 提案时自查)而非执行侧**——被否
  (事后重构补记;当时备选未记录):生成侧自查挡不住「同批多动作
  互相制造重复」(A 事务合法+B 事务合法,先后应用后同名)与陈旧
  提案;游戏规则级约束必须在**状态迁移的单一收口**(simulate/
  mutate)强制,生成侧只能是建议。判据:违规行为是否能构造出
  「每个生成决策局部合法但终态违规」的序列——能,则守卫必须在
  应用层。
- **未知身份(char_id 空)也查重(按 faction 键)**——被否:两个
  未知不是可证明的重复,误拒会阻塞合法填位;守卫语义是「拒绝可
  证明的规则违规」,不是「只放行可证明的合法」(后者在观测不全时
  死锁)。
- **开拓者按各排形态分别查重**——被否(来自 r404-A2 同源判据,
  历史裁决记录):开拓者 char_id 随排切换是**观测表示**问题,场上
  的游戏实体仍只有一个开拓者;不归一则换排形态切换可绕过守卫。
- **phantom_rebuys 靠「重读状态」防御式编程**——被否(事后重构
  补记):每个应用点重读等于把一致性检查摊到所有调用方,漏一处
  回归一处;expect 显式字段把「提案的假设」变成数据,应用层一处
  校验。
- **账本 target_comp 只写 v3 意向**——被否(裁决 3 原文):v2 旧臂
  仍在跑且是 A/B 对照臂,直接换口径会让历史 decisions.jsonl 断代;
  优先级链保持旧臂逐位不变。
- **检查器逐个内联归一化**——被否(裁决 4):coldstart 检查已有
  内联归一化先例,再复制三份=下一个双源;helper 单一源。
- **修后立即重跑 A/B**——被否(收账节明示):W49 口径审计已发现
  星徽/Δ池键等同族口径问题,单修本批重跑浪费;裁决为 W50 口径批
  合并后联调重跑(「遗留归联调批」)。

## 影响

- 代码:`cw_state.py`(board_unique_key/_resolve 增校验/三动作守卫+
  mutate 镜像/expect 字段族)、`cw_sim.py`(_target_comp_label/break
  重决策)、`cw_sim_checks.py`(_normalize_buy_reason)。
- 测试:守卫 18 条;全量 2138 passed。
- 遗留(显式声明归联调批):evolution 侧 expect 填充(生成侧登记
  期望名)、ledger 复验、A/B 重跑。
- 方法论:动作契约评审单列「资源约束类条款」栏 + 该类条款必过模拟
  涌现验证(54% 是涌现证据,非 review 证据)。
