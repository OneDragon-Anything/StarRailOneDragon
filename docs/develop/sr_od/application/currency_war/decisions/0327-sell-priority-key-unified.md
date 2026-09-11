# ADR-0327:S5 统一卖件弱序(sell_priority_key + AD9-2-3 守卫)

- 状态:accepted(W52 批)
- 日期:2026-08-25
- 决策:见下「决策」节;正文落点 = `decision_v2/discipline.py` 的
  `sell_priority_key`/`_sell_expected_loss`/`sell_score_weight`/
  `register_round_sold` + `decision_v2/registry.py` 的
  remeet_window_rounds/through_rate/sell_key_weight_scale +
  四消费点(carry_gate ④ / _compensate_gold / _compensate_bench /
  层3 off_target 评分)。W52 执行序第 8 步。

## 背景(现象与根因)

卖件选择弱序散落四通道:carry_gate ④ 手搓
`(in_protect, 0 if (cp>3 or absent_mergeable) else 1, cp)`、
liquidity(已收编)手搓 `(net0, cost, star)`、补偿器各自局部键、
层3 评分用均一 `off_target_sell_bias`——**同通道内卖件相对序
不一致**(双源漂移温床),且均无「再遇代价 × 终局贯穿率」维度
(设计点5:卖件应优先卖再遇成本低、终局贯穿率低的件)。

**AD9-2-3(指挥官裁决,升格必改)**:净0 序卖 3合1 进行中素材——
加权副本 ≥2 的件(合成进行中/完整份)不可卖,防补偿/腾位通道拆
合成进度(与「3合1 完整份不卖」同族收紧)。

**根在哪一层**:约定层——卖件序是跨通道共享的决策约定,应单一源
注册表化,禁各通道手搓。

## 决策

1. `sell_priority_key(bc, state, session, protect=None, registry=None)`
   → tuple | None(升序=最先卖;None=不可卖):
   `(in_protect, redundancy, expected_loss, net0_rank, cost, star)`。
   守卫 → None:未识别(空名/注册表外)/round_sell_blocked/
   seed_age_blocked/**加权副本 ≥2**(AD9-2-3)/。种子单列兜底逻辑
   (唯一可卖=种子豁免)由 carry_gate ④/补偿器保留在外(专属时序,
   键不管)。槽位模型:入参 BenchChar,返回键不含槽位号。
2. `expected_loss = remeet_window_rounds[cost] × through_rate[cost]`
   (registry 表;首版三档近似 + W4 费级代理派生,**sim 校准域**——
   设计 §9-4 自评「有键但粗」)。
3. 四消费点统一收编:carry_gate ④ / `_compensate_gold` /
   `_compensate_bench` 改消费 `sell_priority_key`(禁手搓);
   层3 off_target/for_gold/free_bench 评分改按键缩放
   `val += off_target_sell_bias × sell_score_weight(cost)`
   (w=1/(1+expected_loss) 归一化,封顶 1;净0 件 w=1、沉淀件 w→小;
   **只改同通道内相对序,不改「卖不卖」正分门槛**——未知费级件
   w=1 保底;回退开关 sell_key_weight_scale=1 即均一 bias)。
4. `register_round_sold(names, state, session)`:卖出件入同轮已卖集
   (r408 对称臂)统一 helper(带轮键自校验,防跨轮误写);四消费点
   (carry_gate/两补偿器/strategy 主循环)统一走。

## Considered Options

- 各通道保留手搓弱序(否决):双源漂移(设计 §4 明示温床)。
- 统一键含槽位号(否决):槽位模型下发射时由调用方带槽位号
  (置 None 语义),键只管排序。
- absent_mergeable 最弱级(设计 r2 原文)→ 被 AD9-2-3 覆盖:
  加权副本 ≥2 一律不可卖(指挥官裁决优先,原最弱级分支随之不可达,
  保留为结构注释)。

## 影响面

- 行为变化清单:
  - 2★/2 份素材件:由「可卖(最弱级优先)」改「不可卖」(AD9-2-3,
    补偿/腾位通道)——**意图内**(指挥官裁决)。
  - 卖件相对序:同轮多卖候选改按 expected_loss 排序(低费先卖)——
    **意图内**(S5)。
  - 层3 卖分:均一 bias → bias×w(w<1)——卖件顺序变化,卖不卖
    门槛不变(纯占位件仍正分可卖)——**意图内**。
- 测试:carry_gate 两旧锁语义化重写(AD9-2-3 反转 absent_mergeable
  旧行为);新锁 test_s5_key_orders_low_cost_net0_first /
  test_s5_ad9_2_3_compensation_not_sell_merge_material;
  `test_off_target_sell_bias_flips_zero_score` 用注册表外件
  (w=1 保底)断言不变。

