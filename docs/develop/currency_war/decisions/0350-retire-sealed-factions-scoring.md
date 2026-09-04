# ADR-0350:清债——评分层五家人上人改四体系 + 已封存桥删除(W124-H2)

- 状态:accepted(2026-08-26,W126;随步③ 批落地)
- 判据:2026-08-24 四体系封闭裁定(用户;狼狩/贝洛伯格体系封存);W124-H2 复读债务清单(commit 5e7cf8c0 记档:「评分/桥池仍奖励已封存线,记③批债务——②b 在飞不动 src」);`docs/game/currency_war/research/transition_combos.md` 四体系定稿(仙舟3/列车2/DOT2/希儿系,r399 希儿系=希儿在场∧量/贝任一≥2)
- 影响:default 栈**显式解冻三文件**(清债 sanctioned:W124-H2 记档本批)——`cw_evaluate.py`(TRANSITION_FACTIONS 四体系化+希儿系条件计数)、`cw_bridge_pool.py`(删 dot_belog/hunt3 两桥)、`cw_transition.py`(删狼狩/贝洛伯格框架映射);派生面 `cw_line_defs.ENGINE_FACTIONS` 随桥池收缩(狼狩/贝洛伯格退出引擎门/部署围栏)

## 背景

2026-08-24 四体系封闭裁定后,狼狩/贝洛伯格两体系已封存(P2 边界
受限,详见 p02 存档),但 default 栈评分层仍存在三条「已封存线奖励」
残留(W124 文档复读 H2 指认,记为③ 批债务):①`cw_evaluate.
TRANSITION_FACTIONS` 经 skeleton_factions 派生仍含狼狩/贝洛伯格,
transition_tempo(过渡羁绊人上人奖励)继续给已封存体系发保血分;
②`cw_bridge_pool` 的 dot_belog/hunt3 两桥(BRIDGE_POOL 成员)仍向
买侧供给「桥件」标签与保护;③`cw_transition.FRAMEWORK_FACTIONS`
仍给两体系框架豁免通道。债务在 ②a/②b 在飞期间不动 src,排本批。

## 决策

1. **五家人上人改四体系**(cw_evaluate):TRANSITION_FACTIONS 从
   `skeleton_factions()`(plaza 骨架派生,含已封存两系与一批非体系
   骨架阵营)改为 **TRANSITION_TRAITS 派生**(四体系三羁绊单一源:
   仙舟/持续伤害/列车同行)+ 治疗手工补(角色效果驱动,派生判据筛
   不到);**希儿系**(第四体系)以条件计数进 transition_tempo_score
   ——`_seele_system_activated`:希儿 deployed ∧(量子同频≥2 ∨
   贝洛伯格≥2),与 `cw_sim._engines_count` 的 seele 分支同式。
   **贝洛伯格是希儿系放大器**:只在希儿系判据内保留贝计数
   (无希儿在场的纯贝 2 人不计),不得作独立伤害源。
2. **已封存桥删除**(cw_bridge_pool):dot_belog(2DOT+2贝)/
   hunt3(3狼狩+2DOT)两 BridgeCombo 删除(git 可查);存活三桥
   (xianzhou_dot/xianzhou_train/train_dot)派生 ENGINE_FACTIONS=
   {仙舟, 持续伤害, 列车同行}——狼狩/贝洛伯格退出引擎门,连带退出
   deploy 围栏(RECIPE ∪ ENGINE)与 classify_buy 的 bridge_seed 名单。
3. **框架映射删除**(cw_transition):FRAMEWORK_FACTIONS 的
   '狼狩'/'贝洛伯格' 两键删除——已封存线不再有框架豁免通道;
   '量子' 键的贝洛伯格保留(希儿线主流构成,希儿系判据内)。

## Considered Options

| 选项 | 裁决 | 理由 |
|---|---|---|
| 只摘狼狩/贝洛伯格、保留 skeleton 其余骨架阵营(巡海游侠等) | 否 | 「四体系」是封闭裁定后的过渡主体定义;骨架派生集是旧方法论(V4.0 plaza 开局组合)的产物,与四体系口径并存的每一分都是双源温床。治疗手工补保留(角色效果驱动,不属体系域) |
| 保留两桥但置空(加 enabled 开关) | 否 | 开关=死代码+双源;git revert 即回退路径,不需要运行时开关 |
| cw_plan.py:235 的同口径镜像(`skeleton_factions() | {持续伤害,治疗}`)一并改 | **挂账不改** | 任务书范围=评分/桥池/框架三处;cw_plan 买侧凑档门是独立消费面(default 栈买入侧),改它超出本批授权面——记入报告遗留清单,归 default 栈下一批(该行影响 `_should_buy` 类骨架配对,需单独锁) |

## 后果

- default 栈行为变化(清债意图内):狼狩/贝洛伯格件失去 tempo 保血
  分/引擎门/桥标签/框架豁免;希儿系(希儿在场+量/贝≥2)获得 tempo
  计数——评分与四体系封闭裁定对齐;
- 部署围栏收缩:飞霄(狼狩)/纯贝件在配方饥饿期回到 bench(不再有
  桥派生豁免)——符合「已封存体系件是可回收垫层」的 [31] 语义;
- decision_v2 侧零变化(v2 的体系判定走 cw_deploy_logic.
  TRANSITION_TRAITS/cw_sim._engines_count,本就四体系口径);
- cw_plan.py:235 镜像行为与评分层口径分叉(挂账,见 Considered
  Options)。

## 验证

- 全量 `uv run pytest sr-od-test/` **2124 passed / 0 failed**
  (含重写锁:r271 ENGINE_FACTIONS 四体系断言/r357 围栏反向断言
  (狼狩/贝洛伯格 not in fence)/core_count_for hunt3 退缺省路由/
  decisions tempo 四体系+希儿系条件计数(含无希儿纯贝=0 反例));
- 派生集实测:ENGINE_FACTIONS={仙舟,列车同行,持续伤害},
  TRANSITION_FACTIONS={仙舟,持续伤害,列车同行,治疗}。
