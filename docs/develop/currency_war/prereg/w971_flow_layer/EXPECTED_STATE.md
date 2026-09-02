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

## 3. 原子 op × 期望态更新全枚举(全集 41 条;每条必有定义或「不更新」理由)

> 铁律:**无例外枚举**——不需要更新期望态的 op 也必须写理由(review 与后续翻看的证据)。
> 分组:A 商店窗口(精确区)/ B 备战窗口(精确区)/ C overlay 动作(到账登记)/ D 流程与系统(理由区)。

### A. 商店窗口(精确建模区)

| # | op | 期望态更新 |
|---|---|---|
| 1 | BuyCard | `gold−费`;**xp += XP_PER_BUY(买牌买经验同源+4,ADR-0129/0286——对抗补,漏则 level 失准)**;`tracked_bench += (角色,星级=卡星级,位=落点)`;**合成引擎**(§4):连锁/落点/装备继承;满栏自动多买(k×单价全款);2星直出 → 金账对账暴露 |
| 2 | RefreshShop | `gold−2`;shop_cards 失效(下轮波顶实读覆盖) |
| 3 | CloseShopOp | shop_cards/商店族清理;**离开商店窗口** → 未覆盖 expected 携带到备战覆盖点 |
| 4 | OpenShopOp | 画面态 shop_open=true(实读锚即得,非期望态语义) |
| 5 | OpenShop(read_only) | 同 4,纯观察变体:开+观察刷新+收起——**零游戏状态变更**(无期望态更新) |

### B. 备战窗口(精确建模区)

| # | op | 期望态更新 |
|---|---|---|
| 6 | **M7 装备拖拽(穿装备)** | `last_owned_equips −1` + `tracked_deployed[角色].equips +1`(**装备分布期望态**——漏项补,复盘 181254 A 条同源路径) |
| 7 | **C6 装备转移** | 角色 A `.equips −件` + 角色 B `.equips +件`(**装备分布期望态**;转移遍 ≤3 件/次,落空即停) |
| 8 | DeployMove | bench 源−1;deployed 目标+1;board 阵营计数±1(上阵+1/下场−1,对抗补);拖到场上同名同星=合成(升星+装备继承);前后台换位;守卫=场上同名同星≤1 恒成立约束 |
| 9 | SellDeployed | deployed−1;装备全额返还 owned;gold += cw_state.sell_refund(1★=cost 全额/2★=3c/3★=9c/star≥2∧cost≥2 −1 手续费——权威单源,对抗修正 v1「星级×基数」);board 阵营计数−1 |
| 10 | SellBench | bench−1;owned += 该角色已穿装备(备战角色同样可穿,equipment_mechanics §1/§3——v1「无装备」前提错,对抗修正);gold+售价 |
| 11 | LevelUpShop | gold−cost;xp+XP_PER_BUY(xp_expect_ledger 迁入);跨门槛→level+1/cap+1 |
| 12 | ClickSpheres | 球−1;`expected[pending_reward]='球(待实读)'` |
| 13 | OpenBox | 箱−1;武装箱选卡 overlay 弹(→C-27) |
| 14 | OpenTome | 秘典−1;秘典 overlay 弹(→C-31) |
| 15 | StartBattle | 进战斗(战斗等待 op 接管;hp/gold/streak 由结算屏覆盖) |
| 16 | EnsureShopClosed | **已退役**(P3b:意图类删除;收起=CloseShopOp)——枚举留痕 |
| 16a | 穿装备(穿着即自动合成) | owned−件+角色equips+件;**穿着触发配方合成**(两件互为配方自动合成,ADR-0391 守卫根源机制)——期望态含合成链(对抗 P0 补装备家族) |
| 16b | 特殊装备类(扳手/冶金炉/令牌/特权卡) | 冶金炉3件同刷(回收线)/令牌/特权(进阶配对)——按注册表 effect 建模进期望态(对抗 P0 补家族) |
| 16c | 员工投影仪(备战席造1★复制) | **非BuyCard 的 tracked_bench+1 通道**(对抗 P0):tracked_bench += (被复制角色,1★);佩戴/拆卸=复制时机,建模待实机对账校准 |

### C. overlay 动作(到账登记区,粗粒度 expected)

| # | op | 期望态更新 |
|---|---|---|
| 17 | 补给 SelectSupplyCard | 暂态无影响(未确认) |
| 18 | 补给 ConfirmSupply | `owned += 选中装备名`(选卡时已知) |
| 19 | 补给 RefreshSupplyCard | 候选重掷;`_supply_refresh_used` 门(次数态;决策器内,无 session 状态字段变更) |
| 20 | 投资 RefreshStrategyCard | 候选重掷;次数门(决策器内) |
| 21 | 投资 SelectStrategyCard | 暂态无影响 |
| 22 | 投资 ConfirmStrategy | `active_strategies += 卡`;效果**走台账不进 session 推进**(范围裁剪 §4.3) |
| 23 | 遭遇 RefreshEncounter | 候选刷新;`_encounter_refresh_used` 门 |
| 24 | 遭遇 SelectEncounterOption | 暂态无影响 |
| 25 | 遭遇 ReadEncounterDifficulty | **纯读**(难度预览→决策器输入;无 session 状态变更) |
| 26 | 遭遇 ConfirmEncounter | 节点难度设定;进遭遇战斗(战斗段接管);难度选择结果归遥测/难度账(决策面) |
| 27 | 武装箱 SelectBoxCard+Confirm | `owned += 选中装备` |
| 28 | 秘典 SelectBookCard+ConfirmBook | `owned += 星徽/装备`(星徽含阵营语义→分配守卫联动) |
| 29 | 巨星 Select+ConfirmMegastar | `chosen_megastar`(session 字段已有);comp 语义变化(决策面) |
| 30 | 列车同行 Select+ConfirmPartner | `chosen_partner`;列车同行星徽+1(产出→owned 期望);board 语义 |
| 31 | 祈愿 Select+ConfirmWish | 效果登记台账(不做 session 推进——单轮即回) |
| 32 | 策划 Select+ConfirmPlanner | 规则变化登记(环境/台账语义;不进 session 推进) |
| 33 | 命运 Select+ConfirmFortune | 强化登记台账 |
| 34 | BOSS 简报点空白 | 画面推进(交回循环);无状态变更 |
| 35 | BriefingOp 点下一步 | 简报字段已在观察段写入 session;推进由画面流转(无额外期望态) |

### D. 流程与系统(理由区)

| # | op | 理由(不更新期望态) |
|---|---|---|
| 36 | PlaneTransitionOp(点空白) | **位面推进**:plane+1 为期望语义,但节点表/位面实采由 CollectPlaneIntel+探针覆盖——跳过中间态标记,登记即可 |
| 37 | WaitOneOneOp | 纯等待(锚=1-1 就绪);无状态变更 |
| 38 | 自动战斗自愈(开关点击) | 游戏 UI 态,非局状态字段 |
| 39 | 干扰弹窗关闭(概率表/道具详情/消耗品) | 纯 UI 关闭,无状态后果 |
| 40 | OpenShop 探针/收起重进(容忍路径) | 画面态周转,终态由 CloseShopOp/开态锚承载 |
| 41 | ExitCurrencyWarMatch(整局退出) | 局终:expected_state 随局级清空(机制边界) |

### P2 批注(对抗轮补注,随实现批逐项落)

1. **2星直出**:买价≠1星价 → 金账对账自动暴露(探测通道已有,spend 账本);
2. **满栏连锁落点**:merge §2.5 自注置信低(商店语境合成落点未亲见)——列为对账优先观察项;
3. **装备继承证据分级**:「场上吸收」有口述证据;「备战栏合成」继承证据空白——引擎实现按两案分立,对账分别校验;
4. **覆盖点替代通道**:合成预览星标(W556 休眠对账信号)/角色详情页(星级替代实读)——登记备查;
5. **恒成立不变量**:「场上同名同星 ≤1」用作 merge_simulate 断言 + DeployMove 守卫(已列入 #8);
6. **装备区槽位序**:last_owned_equips 按 fill-order(无空洞/消耗品第 1 排右起,dd-010)——期望态推进保序。

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
| **op 效果函数自身 bug** | apply_op_effect 推进逻辑实现错(与「模型错」分立:模型=游戏机制认知错;函数=实现错) | 修函数+单测补例 |
| **非 op 游戏侧自变**(随便骰子每节点自动穿2件/节点切换整店自动刷新——对抗补) | 无 op 触发的状态变化:expected 无记录而 actual 变了 | 白名单登记(覆盖时 diff 免留证)或按机制补「非 op 自变推进」挂节点钩子 |
| 未建模行为 | 游戏做了模型外的事(隐藏机制/版本变化) | 按证据补建模或登记 |
| 识别缺陷 | expected 推进正确但实读错(OCR/SIFT) | 修识别(非期望态问题) |

留证:diff 行写 `.debug/temp/currency_war/expected_reconcile.jsonl`(round/op/path/expected/actual)——复用现有对账通道形态。

## 6. 与 P3b 拆内环的接口

- 备战单轮 op 的「对账段」(生命周期②)= 本机制覆盖点的 reconcile 执行处;
- 商店 op 波顶观察 = 商店覆盖点;
- 原子 op 执行器:每 op 执行完 → `apply_op_effect`(期望态推进)——执行器调,逻辑在 kernel 纯函数;
- stall 判定(外循环)消费 expected_state 的轮次戳(「字段长期 expected 未被覆盖」= 停留在不可识别画面过久 → 线索)。
