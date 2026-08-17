# ADR-0203 配置 = 用户偏好单一职责(dot_punish_envs 删除,机制注册表单一源)

- **Status**: accepted
- **日期**: 2026-08-17

## Context

用户在策略对话中指出:`dot_punish_envs`(克制 DoT 的环境名单)是**整个游戏版本一致的客观数据**,
不是用户偏好,不该是配置;并要求全面按使用者视角重审配置面(记录见 [../config.md](../config.md))。

考古发现的错位证据:

1. `DEFAULT_DOT_PUNISH_ENVS = ["净化身心"]` 住在 `CurrencyWarConfig`,注释标它「投资环境」——
   实际「净化身心」是敌人词缀/机制(83 条 ENV_CATEGORY 里没有它),注释已错 = 双源失同步的现成样本。
2. 同一份知识早已在 `cw_comps.MECHANIC_COUNTERS["净化"] = ["DoT", "减益"]` 正式建模
   (competitors.md 米游社 ~50 词缀全集派生,带 `AFFIX_MECHANIC_MAP` 词缀名归一),消费侧
   两条路各写一份(config 裸子串匹配 vs 注册表归一化匹配),OCR 容错能力也不一致。
3. 用户不会去改这个字段(没有「我喜欢被净化身心克」的偏好),配置项形同虚设却占默认值维护成本。

## Decision Drivers

- 配置面的职责 = 表达用户个人目的(画像:日常玩家 + 成就刷取),不是寄存游戏数据。
- 记忆单一源原则:同一信息两处记必漂移(注释已漂)。
- 版本维护路径:游戏客观数据应走注册表/数据 doc 的既有更新流程(gen_plaza_invest 重跑 +
  competitors.md 实机 OCR),不走用户 yml。

## Considered Options

1. **保留 config 字段,默认值同步注册表** —— 否决:双源仍在,同步靠人肉,漂移只是被推迟。
2. **保留字段但语义改为「用户额外补充名单」**(默认空,注册表为主,两者并集)—— 否决:为不存在的
   用户需求留接口;用户没有「补充克制关系」的能力(那是数据维护,该走 doc+注册表);并集逻辑让
   归因更难(惩罚触发时不知来自哪份)。
3. **删除 config 字段,消费走机制注册表**(名 → `AFFIX_MECHANIC_MAP` → `MECHANIC_COUNTERS`,
   与当前板面 DoT/减益 主派判定求交)—— **采纳**。顺带的泛化收益:与「净化身心」同类的任意
   anti-DoT 词缀/环境自动覆盖,不再单点名;子串包含语义保留(OCR 容错不降级)。
4. 顺带识别的同病字段(`difficulty_hp_override` 阶梯表、`economy_mode` 死配置等)—— 本 ADR 只
   判原则与执行 dot_punish_envs 一项;其余按 [../config.md §4-5](../config.md) 记录为提议,
   逐项待用户批准后另行执行(不搭车)。

## Decision

- 配置 = 用户偏好单一职责:**游戏客观数据归注册表,策略校准参数归代码常量,只有「用户因个人
  目的想改」的才进配置**(判据与归属表见 config.md §2)。
- 删除 `CurrencyWarConfig.dot_punish_envs`(字段/默认值/save 键);`cw_events.decide_event` 的
  机制克制惩罚改读 `MECHANIC_COUNTERS`(经 `AFFIX_MECHANIC_MAP` 归一),行为对「净化身心」
  等价,对其余 anti-DoT 词缀为受控泛化。
- 用户画像定调(日常玩家为主 + 成就刷取)与目标配置面(角色/投资策略/投资环境 × 禁用/优先 +
  strategy_id)记录于 [../config.md](../config.md),作为后续配置演进的单一源。

## 后果

- 正面:双源消除;「净化身心」注释错位(词缀≠环境)随字段一起消失;同类词缀零成本覆盖。
- 负面/风险:用户 yml 里手写过 `dot_punish_envs` 的实例该键被静默忽略(无迁移需求:语义已由
  注册表全覆盖,且该字段本无合理用户值)。
- 验证:sr-od-test 148 例过(含 test_decide_event_dot_needs_major_faction —— 断言不依赖
  config 字段,天然锁住迁移后行为);ruff 过。
