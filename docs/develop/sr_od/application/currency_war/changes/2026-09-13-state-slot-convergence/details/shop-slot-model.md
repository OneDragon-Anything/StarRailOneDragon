# 商店域三态定长槽位模型(详设)

## 问题与约束

**问题**:商店域识别产物是紧缩 list——店未开(收起锚 miss)、OCR/SIFT 失读、买空(5 槽亮度均值 <60 全走空槽 continue)三种事实塌缩成同一个 `[]`(读链 cw_observation.py:1794-1812)。容器 ShopPayload 注释「恒 5 张」与实现背离(cw_game_state.py:530)。后果链:买空店重进 → `if state.shop:` falsy 不写 → bs.shop 保持 None → 决策前置门 ValueError(实机 T-181 崩溃循环,`.debug/temp/shop_slot_problems.md` P1)。

**总纲划给的接口契约**(design.md §2,服从):
1. `ShopSlot.kind ∈ {'content','empty','unknown'}`;`ShopPayload.cards` 定长 5;
2. `unknown` 元素必须落缺陷台账,决策消费一律跳过;
3. 投影口空位置换在单一转移函数内实现(详设 details/sim-state-switch.md 定谳函数居所,本篇只锁语义);
4. 渠道签名封闭集不变。

**依赖约束**:本详设的读链写入门落在阶段一 3.2(生产链直写)之后的漏斗上;landing.md 3.5 依赖 3.2。

**用户裁定**(2026-09-13,模型总纲):固定坑位域识别产物=定长槽位数组,元素三态=内容/空位/None(应为内容但识别失败→告警,不猜);买光店=[空位×5] 是合法真值。

## 方案

### 1. 词表(cw_game_state.py,容器侧类型区,与 BenchSlot 同区)

```python
@dataclass(frozen=True)
class ShopSlot:
    """商店一槽:三态之一(定长五槽的元素,用户三态裁定 2026-09-13)。

    kind='content' 时 card 有效;empty=识别确证无内容(占位带);
    unknown=应为内容但识别失败(必携缺陷台账,决策一律跳过)。
    物理槽位 = 数组下标 + 1(1 基,= screen_info「商店牌-N」序号);
    本类型无 slot 字段——定长数组下标即槽位,紧凑下标≠物理槽位的
    历史病灶类(ADR-0646 同族;cw_game_state.py:516-523 实证「买牌
    点击不注册」)在本模型下结构性消失。
    """
    kind: Literal['content', 'empty', 'unknown'] = 'empty'
    card: ShopCard | None = None   # kind='content' 时有效(现容器版 ShopCard 原样复用)
```

- `ShopPayload.cards: list[ShopSlot]` 定长 5,注释「恒 5 张」兑现(下标 0-4 ↔ 物理槽 1-5);
- 现容器版 ShopCard(cw_game_state.py:496)原样保留为 content 载荷;其 `slot` 字段退役(定长数组下标即槽位;构造期约定 slot=数组下标+1,兼容期由构造包装保证,消费点禁止再读 slot 字段——批2 清理);
- 与 BenchSlot(kind + unit|None,cw_game_state.py:440-449)同构,样板一致。

### 2. 读链契约(read_shop_cards 改造,cw_observation.py:1760)

前置门(现役保留):「按钮-收起」锚 miss → 返回 None,语义 = **店未开**(调用方漏斗不写 payload)。注意签名语义变更:旧 `[]` 混载「店未开/买空/失读」,新 None 只剩「店未开」,恒不为买空。

逐槽判定(i=1..5,槽 rect 由 screen_info「商店牌-N-i」):

| 条件 | 判定 | 依据 |
|---|---|---|
| rect 缺失 | unknown + 缺陷台账(建档漂移) | 现役 `continue` 静默跳过是病灶(审计 A 项);坐标单一真相源规范 |
| 亮度均值 < 50 | empty(确定性占位带) | 实测真卡 min 67.4 vs 空槽 19.5(cw_observation.py:1802-1805 注);<50 取现役 <60 判空带中确定性半区 |
| 50 ≤ 均值 < 60 | unknown + 缺陷台账(灰带:疑暗卡) | 现役 50-60 灰带日志(:1808-1811)升级为 defect 留证,不猜 |
| 均值 ≥ 60,SIFT 识别出 | content(card=现字段逻辑原样) | 现役 :1813 起识别链不变 |
| 均值 ≥ 60,SIFT miss | unknown + record_defect(读空事件 confidence 面,现役 :1820-1834 复用) | 用户提供 None=告警语义;现役遥测面直接承接 |

5 槽恒产(无 continue);`merge_preview` 只对 content 槽计算(空槽/unknown 不裁,省一次顶部带 mask+TM)。

**终判稳定门(对抗窄攻 F2 定谳,防过渡帧误判)**:全 empty 或含 unknown 的判定成立前,入口观察**强制重观察一次**(0.8s 后重读,两帧一致才接受终判;不一致 = 动画/淡入过渡帧,以第二次为准再核)——防「淡入帧亮度<50 被误判 empty → 买光店假象 → 误关店」。重观察上限一次,不构成等待环(与「失读窗收店」语义的边界:重观察后仍全 unknown = 真失读,走 §5.1 收店+留证)。

### 3. 容器写入门(漏斗 shop 域)

- 店开(收起锚命中/0n 三锚)→ `bs.observe(bs.shop, ShopPayload(cards=[5 槽], refresh_probs=现读), sig=obs 族)`;
- 店关 → `leave_screen(bs.shop)`(现役,不变);
- payload None 语义收敛 = **离屏**;旧「空牌面不写」分支(.synthesize_from_game_state shop 域 elif 族 cw_game_state.py:2936-2942)随阶段一反转退役——本详设只锁契约:店开即写、写即定长、None 仅离屏。

### 4. 投影口(单一转移函数内)

- BuyCard:payload 移除该牌 → **对应槽 kind 置 empty、card=None**(替换现「紧凑列表剔除」语义,apply_shop_action_logic BuyCard 分支 :1565-1578 改);同 (name,star) k 张按 canonical 序对槽位,k 张即 k 槽置换;
- RefreshShop:投影只扣金,刷后牌面由续段入口观察重写 payload(现役语义,不变);
- CloseShop:leave_screen(不变)。

### 5. 两个硬必改(audit D 项,不改则新模型反向引入事故)

1. 收工停机钩子 `any(not c.name)`(cw_op_buy_cards.py:1201-1234)→ 判据改 `kind == 'unknown'`(empty 不是未识别;content 恒有 name 语义不变);输入源随阶段一改容器 payload;
2. cw_observe_full.py:129 子态键 `'shop_cards': read_shop_cards(...) != []` → 改店开锚判据(收起锚命中或 payload 非 None),与读数解耦。

### 5.1 全 unknown 窗行为(对抗 F6 定谳)

店开锚命中而五槽全 unknown(整帧 OCR/SIFT 失读窗)时的决策与终结语义:

- **花钱动作禁发射**:unknown 槽在场时 BuyCard/RefreshShop/LevelUp 一律不提案(烧金在失读牌面上、刷后重观察多半仍失读,不猜);终结集降级为仅 CloseShop;
- 收工路径触发收工未识别卡停机钩子(kind=='unknown' 判据)→ 停机留证——与 flow/shop_visit.md §3 未识别卡停机裁决(用户 2026-08-24 在册)同向;
- **行为收紧显式申报**:现役「失读窗沿用陈旧牌面续决策」退役后,该窗从「带陈旧牌面试买」收紧为「快速收店+停机留证」;验收补形态锁「失读帧 → 收店 + 钩子留证」,与「买光=[空位×5] 正常收工」判据并列(两种不同形态)。

### 6. 两个硬必改之外的消费点适配(批2,清单 = 审计 D 项 13 处)

模式统一:`for s in payload.cards if s.kind == 'content'` 取候选;`s.card` 取载荷。要点逐处:

- mandate_v1/shop.py 9 处 `bs.shop.value.cards` 迭代/计数/EV;
- criteria/buy.py:28/71 `enumerate` 紧缩下标 → 槽位 = 下标+1(数组下标即物理槽,候选槽位直取);
- cw_vocab.py:540-556/744-749 Fill 契约 shop 源 idx = 紧缩下标 → 槽号(阶段一转移单源化后此面随 simulate 退役,以详设 sim-state-switch 定谳为准);
- refresh_effective(cw_op_buy_cards.py:220)刷前刷后集合比对 → content 槽过滤后比对;
- cw_observe_full.py:129(见上)。

## 关键取舍

1. **弃「沿用现值 + verified_empty 旗标」**(2026-09-13 通道层提案):不改表示,买光语义仍借用失读通道,三事实塌缩仍在;用户裁定表示层根治,本方案为根治形态。
2. **弃 `Optional[ShopCard]` 两态**(None=空):三态中 unknown(应为内容但识别失败)必须显式存在并告警,Optional 只有兩态;BenchSlot kind 模式已定型(样板一致性)。
3. **弃 ShopSlot 平摊字段**(不嵌 ShopCard):字段搬家 diff 大,且丢双 ShopCard 归一的现成载体;嵌 `card: ShopCard | None` 复用最大、与 BenchSlot(kind+unit|None) 同构。
4. **empty 判据取 <50 而非现役 <60**:50-60 灰带是「疑暗卡」歧义带,落 unknown+告警(不猜)而非确证空;代价 = 灰带槽从「被当空跳过」变「unknown+告警」,决策面等价(两态都不产生买候选),告警面增益(暗卡漏采可见)。
5. **失读窗行为语义(对抗 R3 预答)**:整帧失读(店开但 5 槽全 unknown)→ 无买候选 → CloseShop 收工。与现役「沿用陈旧牌面试买」相比:试买点击落在失读帧上本就不可靠(执行侧无验证),新行为的代价 = 本轮少买一窗,牌面持续到刷新/轮末,下一备战轮重开店即重观察重决策——效率损失非正确性损失,且 unknown 告警留痕使失读窗可统计。真买空帧([空位×5])不受影响(那是 empty 非 unknown)。


## 7. 三域三态化补记(bench / deployed / 备战面板;3.7 前置设计)

> 本节 = 派单前设计补记(编排者指令,2026-09-13):三域现状审计、
> §2.2 豁免撤销判据、迁移面清单与平移边界。**只设计不实现**。

### 7.1 三域现状与同构性判定

| 域 | 容器域 | 现行表示 | 三态化程度 | 同构性判定 |
|---|---|---|---|---|
| 备战席 | bs.bench(BenchView) | `BenchSlot(kind∈{unit,supply_box,tome,empty}, unit|None)` 定长(容量随效果改写) | **已完成四态**(比三态多 supply_box/tome 两个占位内容物态;empty=确证空) | 与 ShopSlot 同构(本源样板);**无需迁移** |
| 上场 | bs.front_row / bs.back_row(list[Unit]) | Unit 行表(定长,占位=None),行内 Unit.slot=1 基槽号(信息位) | 结构上已是「定长+缺席=None」= 两态等价;**缺 unknown 态**(识别失败=缺席,与真空不可辨) | 需补:行表 → 槽包装(kind∈{unit,empty,unknown})或行表保持 + 判定面增 unknown(两案见 7.4) |
| 备战面板 | 观察域(bs 外;prep 观察回执) | 逐字段 gate(prep_clean/prep_shop_open spec),非容器域 | 不适用(面板=画面不是席位域) | 三态化对象实为「商店牌行」(已在本篇 §2 完成);本域仅申明边界 |

判定总结:**bench 已达模型终态;deployed 缺 unknown 显态;备战面板为边界申明非迁移对象**。

### 7.2 §2.2 豁免的撤销判据与撤销后写入端语义

§2.2 现行豁免(容器域 None 语义 =「非当前画面」的结构事实;payload 域
失读帧「不写、沿用现值」)。三态化后的撤销判据(按域):

- **shop(已撤销生效)**:店开即写(买光=[empty×5]),None 仅离屏——
  本篇 §3 落地;豁免残留 = read_game_state 失读沿用支(保留:锚 miss
  语义 = 画面事实不明,沿用旧值优于误清;撤销条件 = 锚判定确定性化,
  现以二值化门+全帧位匹配达成,残留支仅防御)。
- **deployed(撤销判据)**:识别失败帧从「不写沿用」改「unknown 显态」
  的前提 = 识别层能对「每槽」给三态结论(槽级 SIFT 置信度面,现只对
  整行)。判据:槽级置信度遥测(镜像 shop 的 per-slot 缺陷台账)连续
  两版本稳定 → 撤销整行沿用,行写改槽级三态。撤销前现行语义保留。
- **bench(无豁免)**:BenchView 槽级直写已运行,无豁免可撤。

撤销后写入端语义(统一):「写 = 本槽三态结论;不写 = 画面事实不明
(沿用);None/leave_screen = 结构性离屏」——三档与 shop 域 r4 后
完全同构。

### 7.3 迁移面清单(deployed 域;bench 无迁移面)

- 词表:行表包装类型(建议 `DeploySlot(kind∈{unit,empty,unknown},
  unit|None)`,与 BenchSlot/ShopSlot 同构)或维持行表+判定面增态
  (两案定夺见 7.4);
- 写端:deployed_rows_from_obs(观察直写)/deployed_slots_to_rows
  (引擎平移契约)/synthesize 行写(三处);
- 消费端:deployed_slots_of 读口(换算处)、围栏选点(_board_factions_of/
  engines_count 等 registry 派生面不受影响——faction 丢失族申报表在案)、
  prep_expect 域(槽号语义面);
- 锁:行几何锁(定长)+unknown 显态锁+写端三态锁(照 shop 锁面三件
  形态)。

### 7.4 平移边界

- **保留引擎内**:合成/结算/装备链的引擎真值写(已容器化,不在本域);
- **进单源(转移函数/读链)**:行写的槽级三态结论、unknown 缺陷台账、
  位匹配锚判定同款;
- **不迁移**:faction 入容器(§3.2.3 申报表既定,W5 域另案);bench
  四态词表(终态);备战面板域(非席位域)。
- 实施载体:独立任务批(建议 3.7 批1 = 词表+写端,批2 = 消费面),
  依赖本篇词表冻结。
