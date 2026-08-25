# ADR-0348:扑满守卫(离线可做部分)——「经济过热」类环境 reward 节点按战斗节点处理

- 状态:accepted(2026-08-26,W119;节点模板建档等三项挂账)
- 判据:W113 §8-5(E1,W115 对抗审计最高优先);口述 [16] 2026-08-25 例外注记:「经济过热」类投资环境下奖励节点变次元/超级次元扑满——**有战力要求要打**,「奖励节点无战斗」前提失效
- 影响:decision_v2 新增 ev.REWARD_BATTLE_ENVS/reward_node_is_battle;discipline._hard_node(连胜 EV 地板/保血通道 hard 判定)消费;单帧锁(test_cw_w119 ⑥)

## 背景

`cw_invest_data.PLAZA_PORTALS` id 105「经济过热」/119「经济严重过热」:
「本局的全部奖励节点替换为(超级)次元扑满主题」——扑满要打且跑得快
(掉更多战利品)。决策层此前零消费:reward 节点被无条件当作零战斗
(「必胜、无血可扣」),持过热局时该攒的战力没攒、该 D 的轮没 D。

## 决策

- 环境名单 `REWARD_BATTLE_ENVS` 从 `cw_invest_data.PLAZA_PORTALS`
  按**效果文本派生**(含「奖励节点替换」;单一源,版本重跑自动跟上;
  锁测试断言 == {'经济过热','经济严重过热'})。
- `reward_node_is_battle(state)`:`node_type=='reward' ∧ active_env ∈
  名单` → 按战斗节点处理。消费点=discipline `_hard_node` 单一源
  (连续 EV 地板 `_streak_floor` 的深花授权 + 掉血报警保血通道的
  `allow_refresh_in_war` hard 判定)。
- **掉血三臂(BloodAlarmTracker._BATTLE_NODES)不辖**——三臂是用户
  定调的不可回归旁路,语义逐位不动;扑满节点的掉血是否入臂留
  实机语料后再裁(挂账)。

### 挂账项(本批不做,W115 E1 四处跟进的其余三项)

1. 投资效果表(cw_investments/cw_effect_ledger)加「reward 节点变
   战斗」机制突变项;
2. DP 台账指纹纳入该突变重解;
3. 节点识别扑满模板档(cw_node_reader 自陈未建,采集 hook 已有)——
   留实机(模板建档走画面建档流程,非离线可做)。

default 栈的 `_is_reward` 类守卫(cw_evaluate.py:215 族)**冻结不动**
(回退保险+基线臂),两栈同病的 default 侧修复随 default 解冻批次。

## Considered Options

- **手写环境名常量**:否决——cw_invest_data 是生成文件(勿手编),
  名单派生自效果文本随版本重跑传导;
- **reward 节点直接进 BloodAlarmTracker._BATTLE_NODES**:否决——
  改旁路语义,违反本批铁律;硬节点分类已覆盖决策面的深花授权;
- **效果表突变项同批落**:否决——台账突变影响 DP 世界模型,与 DP
  姿态标定(②b)耦合,归后续批一起裁。

## Consequences

- 行为面:持过热局的 reward 节点上,连胜 ≥2 的破息地板(降 5)与
  报警升级态的保血 refresh 辖域生效——「必胜节点不花钱」假设在这些
  局修正。
- 实机验证锚点:持「经济过热」局进 reward 节点时,连胜在手应见
  深花/刷新动作;节点模板建档后(node_type 读出非 reward)本守卫
  自然退化为兜底。
