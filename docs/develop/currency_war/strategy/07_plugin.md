# 07 策略插件(CwStrategy)

> 把「决策大脑」抽象成**可替换对象**:换一个对象 = 换整套打法,框架(观察/执行/验证/防护)不动。服务:用户自写策略 + 策略比赛。设计 → ADR-036(D-34)。

## 1. 五件套

| 组件 | 模块 | 语义 |
|---|---|---|
| `CwStrategy`(ABC) | `cw_strategy` | 大脑接口:**纯逻辑**(只吃 GameState/选项,出 Action/Pick,绝不碰屏幕);钩子 abstract,ABC 自身不含逻辑 |
| `StrategySession` | `cw_strategy` | 每局状态(target_comp / rng / performance / memory 私有 scratch);框架每局新建、局终销毁 |
| `CurrencyWarMatch` | `cw_strategy` | strategy+session 轻容器,挂 `ctx.cw_match`(显式声明,局终置 None 防跨局污染) |
| `StrategyManager` | `cw_strategy_manager` | 自动发现:BUILTIN(`strategies/`)+ THIRD_PARTY(`plugins/currency_war_strategies/` 子目录);`STRATEGY_ID` 唯一性强校验;对标 app 插件机制(无 factory/config 间接层,`cls()` 即实例化) |
| `DefaultCwStrategy` | `strategies/default_strategy` | 内置具现 v1(每个钩子委托既有模块函数);自定义两条路:继承 ABC 全自研 / 继承 Default 只覆盖关心的钩子 |
| `LineStrategy` | `strategies/line_strategy` | **现行生产策略 v2**(继承 Default,只覆盖 4 策略性钩子:锁线/桥线/四象限/应急 + `decide_prep` 决战窗;`strategy_id=line_v2`,生产 checks 按此判栈,ADR-0245) |

## 2. 钩子清单

**生命周期**:`create_session`(每局)/ `on_match_start` / `on_round_end(obs)`(默认 `performance.record`——观测驱动回路)/ `on_match_end(outcome)`。

**决策**:`update_target`(战略,写 session.target_comp;框架在环入口调)/ **`decide_prep(state, session, config)`**(备战整段计划——复合动作 RunBuyPhase 路径的决策口,返回动作列表;LineStrategy 的四象限/应急/决战窗在此,03 §3)/ **`decide_prep_action(obs, session, config)`**(备战单步——PrepDirector 环的决策口,03 §1;两个备战口并存:环走单步、复合走整段)/ `decide_invest` / `decide_supply` / `decide_encounter` / `decide_megastar` / `decide_partner` / `decide_planner`(策划事件选项,银狼命运卜者类,r104 接策略模块)(事件节点,04;overlay 态经 decide_prep_action 内部委托)。

**state 供给契约**:框架在调 `update_target` 前产出与生产一致的 state(shop 关闭帧 hp 覆盖 → 开 shop 读 gold/board/shop),策略不自己截图。

## 3. 配置与 GUI

`currency_war_config`:`strategy_id`(默认 `default` = 不配置即内置打法)/ `strategy_seed`(None=真随机;int=A/B 复现)。GUI setting card 下拉选策略 + 种子框。

## 4. 种子化语义(诚实边界)

`strategy_seed` 只种子化**策略内部随机**(默认策略的蒙特卡洛 D 牌走 session.rng);**游戏侧行局演化(发牌/boss/掉血)不可种子化**,且 rng 有状态随调用次数推进——「同 seed 复现」只对固定输入序列(replay)成立,对真实对局脆弱。

## 5. 测试与 replay

- 策略纯逻辑 → 离线 unit(喂构造 state 断言 action);框架环用 mock controller 测;换策略不改框架测试。
- replay(`decisions.jsonl` 重放)= **回归测试**(策略改版后面对历史局面决策是否退化)+ 调试,**不是胜率裁判**:obs 序列是当时策略产生的,换策略后游戏演化路径本就不同(分布偏移);真实胜率 A/B 必须实机大样本。
- `batch_score` 类评分同理,只比「同一 obs 序列下的决策差异」。

## 6. 威胁模型

进程内全信任(与第三方 app 插件同:plugins 目录自动 import 执行),不沙箱;比赛在受信任环境跑。
