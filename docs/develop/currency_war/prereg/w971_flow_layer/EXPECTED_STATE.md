# W971 · 期望态(Expected State)机制设计

> 状态:DESIGN v1(编排者初稿 2026-09-02,待对抗);上游定稿 = 02-state §4.3(机制定稿/范围裁剪/跨轮链)
> 依赖:画面 op 生命周期五段(03-prep §1.1);合成规则 = merge_mechanics §2/§2.5/§2.7;装备 = dd-010/dd-015 定谳

## 1. 机制总述

**session 字段双源**:实读覆盖(actual,来自各画面识别面)+ 期望态推进(expected,来自操作 op 的逻辑后果)。

- **推进**:原子 op 执行后,按逻辑规则更新 session 对应字段,**标记 source=expected**(含产生者 op/轮次);
- **覆盖+对账**:回到能识别该字段的画面时,实读覆盖 actual;覆盖时若该字段存在 expected 标记 → **diff 对账**(expected ≠ actual → 留证:合成落点模型错/未建模行为/识别缺陷三类);
- **决策读路径不变**:决策接口永远读 session 字段本体(= 期望态优先的最新值),单一读路径。

**数据结构**(session 侧新增容器,非逐字段改造):

```
session.expected_state: dict[str, ExpectedEntry]
ExpectedEntry = {path: 字段路径, value: 推进值, produced_by: op 名, at_round: 'p1-r4', kind: 字段族}
```

字段本体照常更新(expected 推进值直接写入);`expected_state` 只记「哪些路径尚未被实读确认」——覆盖点 reconcile 后移除条目。

**统一现有雏形**:`pending_buy_expect`(买牌对账)/`xp_expect_ledger`(经验对账)/`tracked_*` 动作登记——全部迁入本机制(向后兼容:迁移批一次性收编,旧字段退役)。

## 2. 覆盖点(实读 merge 点,全枚举)

| 覆盖点 | 时机 | 覆盖字段族 |
|---|---|---|
| **备战观察**(最大覆盖点) | 备战单轮 op 观察段 | tracked_bench_chars / tracked_deployed(身份+星级+装备)/ last_owned_equips / gold / level+xp / board / bench 占位 |
| 商店波顶(shop_state_frame) | 商店 op 观察段 | gold / shop_cards / 备战席占位(**星级身份不可见**——期望态存活的主场景) |
| 结算屏(战斗等待 op) | 每场战斗结算 | hp(真值链)/ gold / streak / level+xp |
| 节点探针 | CloseShopOp 后 | node_type/节点表 |

## 3. 原子 op × 期望态更新全枚举(核心表)

> 精确建模范围(02-state §4.3 裁剪):**商店多轮窗口**必须全准;单轮即回的 overlay 按「到账」语义登记(粗粒度 expected,实读覆盖即可,不深建模)。
> 星徽阵营语义(dd-015 定谳):星徽 add-if-absent,给已自报同阵营角色 = 装备不上(分配守卫已拦)。

### 3.1 商店窗口 op(精确建模区)

| op | 期望态推进(字段:变化) |
|---|---|
| **BuyCard** | `gold -= 费`;`tracked_bench += (角色, 星级=卡星级, 位=落点)`;**合成引擎触发**(§4):同名同星凑 3 → 升星(连锁/落点/装备继承)——bench/deployed/星级按引擎输出推进;满栏自动多买:一次点击买 min(店内张数, 3−已有 mod 3) 张,金账按 k×单价记全款 |
| **RefreshShop** | `gold -= 2`;shop_cards 失效(下一轮波顶实读覆盖) |
| **LevelUpShop** | `gold -= cost`;`xp += XP_PER_BUY`(xp_expect_ledger 迁入);xp 跨门槛 → `level += 1` + `cap 可能+1`(期望态);实读对账:期望升级未发生 = xp 口径错 |
| **OpenShopOp** | shop_open=true(画面态,非期望态语义——实读锚即得) |
| **CloseShopOp** | shop_cards/商店族字段清理(§3 生命周期);**离开商店窗口** → 待覆盖的 expected 携带到备战观察覆盖点 |

### 3.2 备战窗口 op(精确建模区)

| op | 期望态推进 |
|---|---|
| **DeployMove** | `tracked_bench 源位 -=1`;`tracked_deployed 目标位 += (角色,星级)`;**拖到场上同名同星 = 合成**(升星:星级 +1,装备继承——已穿装备随人,位置=场上原位);前后台换位:位置字段推进 |
| **SellDeployed** | `tracked_deployed -=1`;`last_owned_equips += 该角色已穿装备(全额返还)`;`gold += 售价(星级×基数)`;board 该角色阵营计数 −1 |
| **SellBench** | `tracked_bench -=1`;`gold += 售价`(bench 件无装备) |
| **ClickSpheres** | 球消失;奖励内容未知 → `expected[pending_reward] = '球(类型待实读)'` 覆盖点实读对账 |
| **OpenBox / OpenTome** | 候选物 −1;对应 overlay 弹出(交 handler;产出见 §3.3) |
| **StartBattle** | 进入战斗(战斗等待 op 接管;hp/gold/streak 由结算屏覆盖) |

### 3.3 overlay 动作(到账登记区,粗粒度)

| 动作 | 到账登记(expected,实读覆盖即可) |
|---|---|
| 补给/武装箱选卡 | `last_owned_equips += 选中装备名`(**选卡时已知**——非未知) |
| 秘典选卡 | owned += 星徽/装备(选时已知) |
| 列车同行选人 | chosen_partner;列车同行星徽 +1(产出);board 语义变化 |
| 投资策略选卡 | `active_strategies += 卡`;**效果到账走台账**(金/XP 按节点流 → 延时到账由实读覆盖;不逐卡硬编码 session 推进——范围裁剪) |
| 投资环境选卡 | active_env(全局,不进字段推进) |
| 祈愿/策划/命运 | 各自效果登记(台账面;不做 session 推进) |
| 遭遇确认 | 进入遭遇战斗(战斗段接管) |

## 4. 合成引擎(merge_simulate,纯函数离线可测)

```
merge_simulate(state: {bench, deployed}, buy: (角色, 星级, 张数))
  → {bench', deployed', 合成链: [(星, 落点, 装备继承)], 多买张数}
```

规则(merge_mechanics 权威):
1. 同名同星计数:bench+deployed 全场合计;满 3 → 合成升星(**连锁可多级**:2★ 合成产物再与 2★ 凑 3 → 3★);
2. 落点:**三张全在备战栏 → 取最左**;**含场上 → 落场上那个同星的位置**;
3. 满栏例外:能触发合成的牌,满栏也买得进;**自动多买**一次买满缺数(min(店内张数, 3 − 已有 mod 3));金账全款;
4. 装备继承:合成后装备随高星产物(继承规则按实机对账校验);
5. 星徽(阵营装备)不参与星数合成(类别分流,add-if-absent);
6. 已知建模缺口:合成后 bench 重排(最左落点的后续位移)是否影响其他 tracked 位置——**实机对账项**。

单测要求:merge_mechanics §2 两个例(备战合成/连锁合成落场)逐条断言 + 满栏自动多买 3 例 + 装备继承 1 例。

## 5. 对账(diff 三分类 + 留证)

覆盖点 reconcile 时,expected vs actual 的 diff:

| diff 类 | 含义 | 处置 |
|---|---|---|
| 合成落点/星级不符 | merge_simulate 模型错(落点/连锁/继承规则) | 修引擎 + merge_mechanics 补档 |
| 未建模行为 | 游戏做了模型外的事(隐藏机制/版本变化) | 按证据补建模或登记 |
| 识别缺陷 | expected 推进正确但实读错(OCR/SIFT) | 修识别(非期望态问题) |

留证:diff 行写 `.debug/temp/currency_war/expected_reconcile.jsonl`(round/op/path/expected/actual)——复用现有对账通道形态。

## 6. 与 P3b 拆内环的接口

- 备战单轮 op 的「对账段」(生命周期②)= 本机制覆盖点的 reconcile 执行处;
- 商店 op 波顶观察 = 商店覆盖点;
- 原子 op 执行器:每 op 执行完 → `apply_op_effect`(期望态推进)——执行器调,逻辑在 kernel 纯函数;
- stall 判定(外循环)消费 expected_state 的轮次戳(「字段长期 expected 未被覆盖」= 停留在不可识别画面过久 → 线索)。
