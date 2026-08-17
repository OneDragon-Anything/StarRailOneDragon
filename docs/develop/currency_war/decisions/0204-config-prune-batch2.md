# ADR-0204 配置面收敛第二批(economy_mode / event_whitelist / hp 阈值删除,seed/max_rounds 降开发字段)

- **Status**: accepted
- **日期**: 2026-08-17

## Context

ADR-0203 确立「配置 = 用户偏好单一职责」后,[config.md](../config.md) §4 留了一批待批处置项。
用户 2026-08-17 批准全部执行,并追问 `event_whitelist` 为何不删 —— 复核承认上一轮保留理由
(「指定具体分值的精调能力」)不成立:那是引擎调参不是用户偏好表达,且 priority/forbid 轴
落地后用户语义(想要/不要/恒最高三态中的前两态)已全覆盖,「恒最高」第三态无真实画像需求。

## Decision Drivers

- 用户画像(日常玩家 + 成就刷取,config.md §1):配置只表达「我想怎么玩」。
- 死配置证据:`economy_mode` 所在的消费链 `_economy_mode_for` 中,node_plan 各区间都有明确
  spend_mode,`adaptive` 档只在 fallback 区间(plane>3)出现 —— 用户改了几乎无感。
- 策略校准参数归代码:「A7 该在 52 血弃息」没有用户个人意见空间,值随实机校准走 git。

## Considered Options

1. **economy_mode** —— ①保留(现状):死配置,GUI 化后是「看似可调实则无效」的坏体验 → 弃;
   ②删除,消费端 spend_mode 单一源(`_economy_mode_for` adaptive 档恒 neutral;
   `_maybe_sell_for_interest` 删 `rush_level` 用户门)—— **采纳**。
3. **hp_safe_threshold + difficulty_hp_override** —— ①保留为用户字段:校准参数当偏好卖 → 弃;
   ②降代码常量:`cw_state.HP_SAFE_THRESHOLD`(40)+ `DIFFICULTY_HP_TABLE`(A1-A8 阶梯),
   `effective_hp_threshold(state)` 签名去 config 参,6 处调用点同步 —— **采纳**。
   (不合并进 `cw_evaluate.HP_DANGER`:两者语义不同 —— HP_DANGER 是「危险」判据默认,
   HP_SAFE_THRESHOLD 是「安全地板」回退;数值同 40 但演进路径独立。)
4. **strategy_seed / max_rounds** —— ①删除:A/B 复现与多轮采样是开发验证刚需,删了工具没了 → 弃;
   ②降级为开发/实验字段(config 内显式分段注释「不进未来 GUI」,yml-only)—— **采纳**。
5. **event_whitelist** —— ①保留:精调能力论(被用户质疑)→ 弃,见 Context;②升级为
   strategy_priority 的一部分:priority(+30 soft)语义已覆盖且更统一 → 弃(重复);
   ③删除,`decide_event` 白名单评分块/penalty 联动一并删(penalty 恒 100)—— **采纳**。
   行为影响:原先靠 whitelist 制造高分卡的测试改用高评估分卡(远见 70)表达;无生产路径
   依赖默认空 whitelist(删 DEFAULT_EVENT_WHITELIST 后生产恒空)。

## Decision

- 删配置字段:`economy_mode`(+ALLOWED_ECONOMY)、`event_whitelist`、`hp_safe_threshold`、
  `difficulty_hp_override`(+DEFAULT_DIFFICULTY_HP)。
- 新代码常量:`cw_state.HP_SAFE_THRESHOLD` / `DIFFICULTY_HP_TABLE`;
  `effective_hp_threshold(state)` 单参签名(cw_economy/cw_plan×2/cw_evaluate×2/cw_comps 调用点同步;
  `level_up_gate`/`_xp_gold_floor` 顺带去 config 参)。
- `_economy_mode_for(state)` 去 config 参;`_maybe_sell_for_interest` 删 economy_mode 用户门。
- `strategy_seed`/`max_rounds` 留在 config(开发/实验分段注释),不进未来 GUI。
- 用户最终配置面(config.md §3):角色/阵营/投资策略/投资环境 × 禁用/优先/必含 + `strategy_id`。

## 后果

- 正面:配置面与用户画像一一对齐,无死配置无引擎旋钮;阈值校准回归代码 git 流程。
- 负面/迁移:用户 yml 里手写过这四个键的实例被静默忽略(economy_mode 本就无效;
  hp 阈值极少数手动调过 A8=55 的实例由表值 55 等价接管)。
- 验证:CW 测试 700+ passed(全量;ledger-horizon 慢测单跑过 —— 全量跑中的一次失败系
  并发僵尸 pytest 抢 CPU 的假失败,清理后单跑 2/2 过);ruff 全过;删测试 2 条
  (whitelist 选卡、economy_mode fallback)断言语义已由转向轴测试族接管。
