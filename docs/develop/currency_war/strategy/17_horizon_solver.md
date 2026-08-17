# 17. HORIZON 跨期求解器(DP 姿态引擎)

> 总见 [README](README.md)。本文:**`cw_horizon.py` 求解器的使用与维护导览** —— 它是什么 /
> 怎么被消费 / 改常量时要做什么 / 缓存机制。决策 why 见
> [ADR-0155](../decisions/0155-horizon-dp-seam.md)(落地)、
> [ADR-0181](../decisions/0181-horizon-shadow-ab.md)(离线 A/B 与切流门槛)、
> [ADR-0202](../decisions/0202-effect-ledger-v0.md)(效果感知注入 v2/性能 v3-v5);
> 本文只讲 what 与 how。

## 1. 它是什么(一句话)

**离线一次性解出的「花钱节奏攻略手册」**:对全部 `(节点 t × 金 × 等级 × 血 × 板强)`
状态组合逆向递推,求每个状态下「最优姿态」(升级/刷牌/攒息),运行时 O(1) 查表
(`posture()` ~2µs)。它是全系统唯一做**跨 27 节点全局权衡**的器官——战术层只看单步,
它看「现在省的 50 金到 P3 值多少存活率」。

```
游戏内每回合: 读画面 → sol.posture(t, gold, level, hp, rb) → 姿态 → 战术层执行
离线一次性:   solve(ledger) → HorizonSolution(act[], val[]) → 缓存落盘
```

## 2. 状态空间与递推

| 维 | 域 | 常量 |
|---|---|---|
| 节点 t | 0-26(3 位面 ×9) | `NODES_PER_PLANE` |
| 金 g | 0-110 步长 1 | `GOLD_MAX`/`GOLD_STEP`(步长 1 是 D1:日程 +1/+2 金不得被量化蒸发,ADR-0202) |
| 等级 L | 1-10 | `LEVEL_MIN/MAX` |
| 血 h | 5-100 桶 5 | `HP_BUCKET`(概率是掉血**期望**,桶粗够) |
| 板强 rb | 5 档 0-1 | `RB_STEPS`(刷牌加成) |

- 递推:`V(t,s) = max over 8 姿态 { V(t+1, s') }`,终值 = 存活奖励 + 金/级/血残值
  (血残值若无,DP 拿安全余量换利息 → 系统性欠升级,V1.1 实测教训);
- 姿态空间:`{升?, D0/D2/D4/D6}` 8 个,动作码 int8(0=存息…7=升+D6);
- 掉血模型:`_hp_loss` = `HP_LOSS_PRIOR` 板强线性插值 × `difficulty_scale(t)`
  ——**期望近似**(V2 切片二「桶分布化」是已知升级方向,见 §6)。

## 3. 消费端(谁在读它)

| 消费端 | 接口 | 模式 |
|---|---|---|
| `get_node_goal` 影子换源 | `_horizon_node_goal → _solved().posture()` | **影子**(与手写表 diff,切流待 47 号灰度) |
| 0181 离线 A/B / 0190 损失预算 | `cw_shadow_ab`/`cw_loss_budget` 的 dp_policy | 离线工具 |
| 38 号搜牌会话(批次) | 终值接 `value_at` | 未接 |
| 33 号合同台层 3(批次) | 义务重解 ΔV | 未接 |

生产路径只有第一行,且**当前查的是「无效果」基线解**(效果感知解未切流,决策权在
47 号发布层,勿静默上)。

## 4. 改常量 checklist(高频操作)

1. 改 `cw_horizon.py` 头部常量(掉血先验/收入/单击价/残值权重);
2. **不用清缓存**——缓存键含依赖文件内容哈希(`_version_key`),改动自动失效;
3. 跑验证(两道锚):
   ```powershell
   $env:PYTHONPATH="src"; uv run python src/sr_od/application/currency_war/cw_horizon.py   # 涌现轨迹
   uv run pytest sr-od-test/test/sr_od/app/currency_war/ -q                                # 全量
   ```
   涌现验证的 plaza meta 带(`_expected_band`,P1 末 lv6-8 等)是行为对拍锚——
   改常量后 band_pass_rate 大幅变化 = 行为实质变了,要能解释;
4. 敏感历史:XP_CLICK_COST_FLAT 曾因取值过贵 → 全路径值 0 坍塌(ADR 注释在常量处)。

## 5. 效果感知(ADR-0202 v2)与缓存(v3)

- `solve(ledger)`:持有效果改变世界规则时(息 cap/单击价/连胜乘子/节点日程)按
  台账重解;`None` = 基线(零漂移锚,709 测试锁行为);
- `EffectLedger` 的字段语义见 `cw_effect_ledger.py`(四象限路由);**纯时点金
  (instant_gold 类,overlay 73 条中 52 条)不进台账 → 指纹不变 → 不重解**;
- 三层缓存(`solve_cached`):进程内 memo(0s)→ 盘 pickle(`~27MB`,键 =
  台账指纹 + 依赖内容哈希;损坏自动重解)→ 冷解(~14s)。

## 6. 已知边界与升级方向(改动概率排序)

| 方向 | 触发 | 影响 |
|---|---|---|
| 掉血换实测桶分布(18 号 V2 切片二) | 19 号 L1 建档后 | `_hp_loss` → 分布转移;35 号价格审计已证 hp 价格缝(ADR-0188) |
| `difficulty_scale` 接管 | 36 号账本(ADR-0199) | 手写曲线 → 记账恒等式 |
| 常数 verified 化 | 23 号注册表升级 | 消灭先验值 |
| 效果解切流 | 47 号发布层灰度 | 生产从基线解 → 定制解 |
| 内环 numpy 向量化 | 若冷解需 <5s | 当前 13.7s + 缓存已够用,性价比低,搁置 |

## 7. 维护红线

- **零漂移锚不可破**:无 ledger 解必须与历史基线逐 posture 一致(集成测试锁定),
  它是 0181/0190 两份 A/B 报告的可比性根基;
- 值/动作表是**紧凑数组不是 dict**:`policy`/`value` property 是惰性物化(旧测试
  兼容),生产代码**只用 `posture()`/`value_at()`**;
- 缓存目录 `.debug/temp/currency_war/dp_cache/` 不入 git,删了自动重建,永远安全。
