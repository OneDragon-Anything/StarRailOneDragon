# 对抗审查：免战牌备战认领双锚失配修复（commit 19a2cb5d3）

- **审查对象**：主仓 `19a2cb5d3`（sim 红种子根治:免战牌跳过替换出战按钮,备战双锚失配整局未识别触顶）+ 测试仓回归钉 `3f205eea`。
- **审查方式**：聚焦无前提对抗。代码/建档全部实读;sim 侧实跑红种子复现验证;实机侧用归档实拍帧走生产识别链（`screen_utils.find_area`）离线对账（对账脚本 = `.debug/temp/attack_skip_anchor_check.py`,不入库）。行号未注明处 = `git show 19a2cb5d3` 时点快照（`.debug/temp/attack_cw_loop_snapshot.py`）。
- **结论分级**：**非阻断收敛**。核心修复行为经实证有效;全部发现为文档失实/欠收敛/回归钉覆盖缺口/既有披露残留,无一阻断合并。

## 1. 验证记录（对修复有效的正面实证）

1. **sim 红种子复现根治**：`test_sim_smoke_batch.py::test_smoke_match_completes[20261015]` 实跑通过（95.1s 整局完成,非 abandoned）——commit 声明的红种子已根治。
2. **实机实拍帧 OCR 对账**（生产链 `find_area`,三帧全符预期）：
   - `sr-od-test/screens/货币战争-备战-免战/跳过态.webp`：购买经验 **TRUE** + 按钮-出战 **FALSE** + 按钮-跳过 **TRUE** → 双锚命中（修复前该帧失配）。
   - `…/货币战争-备战-开商店/免战叠加态.webp`：购买经验 T + 出战 F + 跳过 T,且开商店屏「按钮-收起」T（id_mark 购买经验+收起全中）→ 叠加帧由阶段一身份分发接住,不依赖双锚。
   - `…/货币战争-备战/shop_closed.webp`：出战 T + 跳过 F → 常规帧无双形态误命中回归。
3. **误命中面核实**：screen_info 全集 `text: 跳过` 仅备战系 3 处（`currency_war_battle_prep.yml:621`、`currency_war_battle_prep_shop_open.yml:271`、`currency_war_battle_prep_skip.yml:5`）,同 rect (1700,710-1900,775);非备战画面无「跳过」文本锚,且假阳性需同帧第一锚「购买经验」(229,841-363,878) 命中——仅备战系布局成立,快照注释声明属实。
4. **无第三处漏网**：全量 grep「按钮-出战」消费点闭环——① helper `_prep_anchors_hit`（快照 :385,已改双形态）;② 阶段二内联（快照 :1579,已改双形态）;③ StartBattle op（`cw_start_battle_action.py:106-122`,出战 miss → 两屏查跳过 fallback,`skip_substate` 随自上报携带免战递减）——与认领修复衔接闭环;④ sim backend（`cw_sim_backend.py:1494-1527` 按钮对真值,辖域内免战场:跳过=持卡真值/出战=取反）;⑤ 战斗等待回备战到达判定（`cw_screen_battle_wait.py:90-96`）**有意用购买经验单锚**（注释 :102 明示宽到达判定,双锚精判归循环分支）——免战帧照常命中,设计自洽非漏网;⑥ `prep_actions.py:92-94`/`cw_game_state.py:1413` 为静态词表/文档,无判定语义。
5. **免战帧分发路径闭环**：`CW_DISPATCH_SCREENS`（快照 :510-521）不含「货币战争-备战」与「货币战争-备战-免战」→ 免战纯帧阶段一身份 miss → 阶段二双锚认领（修复生效点）;叠加帧被开商店身份接住。退出链/停机位走屏名白名单 `PREP_DIRECT_EXIT_SCREENS`（`cw_screen_state.py:46-48`,含免战屏名）+ 全集识别,不依赖双锚——修复面外自洽（`cw_entry_exit.py:121-125`、快照 :1440-1454）。
6. **回归钉与免战链测试**：`test_launch.py`（含回归钉 `test_prep_anchors_skip_substate_form`）+ `test_battle_skip_sim_chain.py` 共 18 passed。

## 2. 发现清单

### SA-1 「同位同精度」声明与建档不符（文档失实 · 非阻断）

- **位置**：commit message;快照 :1575-1581 注释「『按钮-跳过』仅出现在备战系帧,与出战同位同精度」;`outer_loop.md` 修改段（:72-74）「同位同精度」;`_prep_anchors_hit` docstring 未提参数差异。
- **事实**：`按钮-出战` rect (1745,710-1895,775) 宽 150px、lcs 0.5;`按钮-跳过` rect (1700,710-1900,775) 宽 200px、lcs 0.9（`currency_war_battle_prep.yml:601-635`）。同位带但**宽与匹配精度均不同**——「跳过(2/2)」计数文本需要更宽 rect + 更严 lcs 才能可靠命中。声明失实;所幸失实方向是「跳过锚更严」,对误命中面反而有利（本次实拍帧对账跳过锚 3/3 命中,无误命中）。
- **现状**：工作区未提交改动（HEAD=19a2cb5d3,`cw_loop.py`/`outer_loop.md` 在 M 态）已把表述改为「rect 跳过略宽,覆盖『跳过(N/N)』计数文本,lcs 收紧 0.9」——修正方向正确,但未随本 commit 入库。
- **严重度**：低。纯注释/文档表述,零行为影响。

### SA-2 exit_chain.md 沿用过时消费面清单「三处调用点」（文档-代码不符 · 非阻断）

- **位置**：commit 版 `exit_chain.md` §3（diff 上下文行未核改）「服务投资策略复探门(现役载体 = `CwScreenInvestStrategy.ENTRY_REPROBE_*`)/发出仲裁预检/C3 确认…后者三处调用点有意穿透」。
- **事实**：commit 时点 `_prep_anchors_hit` 仅有 **1 个**函数调用点（`_launch_screen_recheck` 快照 :284,C3 屏态复验,armed/resume 两 face 共用）,阶段二为内联散写非调用;投资策略复探门（`cw_screen_invest_strategy.py:167-191`）探的是**该屏自身锚**「标识-请选择投资策略」（`_entry_anchor_hit` :170-172）,不消费穿透双锚。修改者改锚描述行时未核对所沿用的消费面清单。
- **现状**：工作区未提交版已改为「调用点两处 = 出战前屏态复验…与阶段二备战认领;投资策略复探门…不消费本判定」——已自行纠正,未随本 commit 入库。
- **严重度**：低。文档与代码不符会误导后续读者沿错误清单排查;无行为影响。

### SA-3 「禁判据外散写」声明与阶段二内联散写并存（单一源欠收敛 · 非阻断）

- **位置**：`_prep_anchors_hit` docstring（快照 :375）「复用身份分发锚表同款两锚;禁判据外散写」vs 阶段二内联双锚（快照 :1575-1581,未复用 helper）。
- **事实**：同一判据两份代码文本。行为经核实**完全等价**（`round_by_find_area` 默认 `crop_first=False`,框架 `operation.py:1045`,helper 显式传参与内联缺省无差异;or 短路消费序两侧一致）——但回归钉只钉 helper（stub 三断言）,阶段二内联不在钉内:未来只改 helper 一侧时阶段二不报警,正是「一处改了另一处没改干净」的残留形态在本 commit 内的自我复刻。
- **现状**：工作区未提交改动已收敛（阶段二改 `if _prep_anchors_hit(self, screen)` + 注释「判定单一源 = _prep_anchors_hit(禁散写)」）——实现者自己撞上了此问题并已修正,未随本 commit 入库。
- **严重度**：低-中（若工作区收敛改动最终未提交则升为中;当前等价性已核实,无行为差异）。

### SA-4 回归钉未锁实拍帧 OCR 命中（覆盖缺口 · 非阻断）

- **位置**：测试仓 `3f205eea` 新增 `test_prep_anchors_skip_substate_form`（`test_launch.py:298-316`）——纯 `_Frame(hits=…)` stub 逻辑钉（或逻辑/第一锚必要性）,不触 OCR。
- **事实**：实机侧「跳过 OCR 锚同位可命中」当前依赖 M72 建档声明 + 本次审查的离线对账背书;两张归档实拍帧（`免战跳过态.webp`/`免战叠加态.webp`）在测试仓内存在但**无任何实帧锁消费**（实帧锁样式先例 = `test_read_level_up_cost_real_fixture`）。锚 rect/lcs 未来漂移（改 yml 不跑实帧锁）时回归钉不会红,实机侧将静默回到失配形态——与 sim 桩钉不同,桩钉锁不住建档层。
- **严重度**：低-中。建议后续补两条实帧锁（免战纯帧三锚真值 + 常规帧跳过锚 miss）;按纪律本次只指出不修复。

### SA-5 sim 跳过辖域假设未校准残留（既有披露,非本 commit 引入 · 非阻断）

- **位置**：`cw_sim_backend.py:269` `CW_SKIP_NODE_KINDS = frozenset({'battle'})`;`currency_war_prep.md:57` 披露键 `cw_skip_scope_battle_only_assumption`（遭遇/首领/奖励备战帧是否也替换按钮待实机校准）。
- **事实**：本修复的双锚 or 形态对辖域失配**天然鲁棒**（实机侧跳过按钮出现即认备战,不依赖辖域假设——这是修复设计的优点）;但若实机首领/遭遇备战帧也替换按钮,StartBattle 将点跳过并按 `skip_substate=True` 上报免战递减,而 sim 侧该节点建模为「不替换」——真值/推演分叉面仍在既有披露处挂着,非本 commit 职责,但其根治仍悬于实机校准。
- **严重度**：低（已登记披露;backend docstring :1506-1510 对跳过锚真值域边界的自申报与消费面前置条件核实一致——or 短路满足「出战 miss 前置」约束）。

## 3. 攻击未成立面（尝试过并证伪的角度）

- **选伙伴引导态穿透误判扩大**：修复使免战底层帧在浮层半开时也可被 C3 复验穿透命中,但发射链浮层闸（`_launch_overlay_gate` 快照 :314-346）与 op 层「找不到按钮」双防线兜住,无误发射面。
- **免战次数用尽恢复帧过渡**：按钮文本切换间隙若两锚皆 miss → 落未知兜底单帧,15 帧阈值内自愈;sim 已按恢复建模（backend :1519-1522）。
- **锁定态(中断恢复)×免战叠加**：锁定探针点商店（免战不替换商店钮）照常分辨锁定/非锁定;锁定直出战经 StartBattle fallback 跳过,闭环。
- **横幅中间态守卫**（「请选择投资策略」lcs 0.8 round_wait）与免战帧无交集——免战激活后横幅不在场。

## 4. 验证工件

- 对账脚本:`.debug/temp/attack_skip_anchor_check.py`（gitignore,含完整输出记录于本报告 §1.2）。
- 快照:`.debug/temp/attack_cw_loop_snapshot.py` = `git show 19a2cb5d3:src/.../cw_loop.py`。
- 实跑:红种子冒烟 95.1s passed;`test_launch.py` + `test_battle_skip_sim_chain.py` 18 passed（本机 venv,2026-11-01）。
