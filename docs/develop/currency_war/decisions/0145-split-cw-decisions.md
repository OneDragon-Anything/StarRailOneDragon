# ADR-0145: cw_decisions.py 一次性拆分(四领域模块 + 全调用点迁移)

## Status

Accepted(2026-08-15)

## Context

- cw_decisions.py 1423 行 / 76 顶层定义,十个功能块挤一文件(评估/规划/经济/事件/节奏骨架);ADR-0142/0143/0144 连续往里加东西,可维护性下降。
- 用户定调:**一次性重构完**(不留 facade 渐进迁移)。

## Decision Drivers

1. 纯移动零行为变化(函数名/签名/常量值全不变,测试只改 import)。
2. 分层无环:investments/state/comps → economy → evaluate → plan;events 只依赖 investments/state/comps。
3. 调用点一次改全(12 个 src 文件 + 5 个测试文件),不留旧名别名。

## Considered Options

- A. 四领域模块 + facade 过渡(早前提案):零调用点改动但 facade 是永久中间态温床,用户否决。
- B. 一次性四模块 + 全调用点迁移 ✅。
- C. 只拆最大块(plan/events)留两块:中间态,半吊子。

## Decision

| 模块 | 职责 | 关键符号 |
|---|---|---|
| `cw_economy` | 经济/等级/节奏骨架(底层,三层共享) | economy_score / xp_click_cost / _refresh_cost / NodeGoal+get_node_goal / _char_synergies(纯数据) |
| `cw_evaluate` | 评估(消费 economy) | evaluate / synergy_score / _phase_weights / optionality/α(t) / _card_hits_target / MAX_REFRESH_PER_ROUND |
| `cw_plan` | 备战动作规划(消费 economy+evaluate) | plan / 蒙特卡洛 D 牌 / _should_deploy / _pick_deploy_row / level_up_gate |
| `cw_events` | 事件节点决策 | decide_event(ADR-0143/0144)/ decide_encounter / decide_supply / 巨星伙伴 dataclass |

- 拆分方式:**脚本机械切分**(顶层语句按归属表切片 + import 按词边界自动推导),非手抄,零转录误差;切片含前导注释(语义跟随)。
- 分层修正实录(环检测驱动):① NodeGoal 三件套最初归 plan,economy._want_level_up 也消费 → 下沉 economy;② _target_progress_remaining/_card_hits_target/MAX_REFRESH_PER_ROUND 等 5 符号是 evaluate 消费 → 从 plan 移入 evaluate;③ _char_synergies 被 evaluate+plan 双方用 → 下沉 economy(纯数据函数,只依赖 CHARACTERS)。三步后无环(ruff F821+全测试证)。
- 传递 re-export 修复:测试曾 `from cw_decisions import PickEvent`(经 cw_decisions 的 cw_state import 传递可用)→ 拆分后断 → 改直接 `from cw_state import PickEvent`。
- 注释指针同步:12 处旧 `cw_decisions.X` 注释更新为新模块路径(shop/battle_prep/cw_state/cw_shop_odds 等)。

## 验证

- CW 全套 401 passed + 1 skipped(拆分前 401 同数;唯一行为性改动=零)。
- ruff 全绿(自动推导 import 精确,无 F401/F821)。
- `grep cw_decisions`(src+tests)运行时引用为零,仅剩 ADR/历史记录提及。

## 后续

- server 下次重启自然加载新模块(insights「重启重置 session」协议:局间重启,M19 在跑不动它)。
- test_cw_decisions.py 文件名保留(测试名不动;docstring 已提及新模块);后续可随自然改动更名。
