# 07 装备系统(分,完整性-1 补)

> 总见 [README](README.md)。review r1(方案)发现装备系统整块缺失(high)。装备是 auto-chess 核心机制,影响极大:反重力皮靴(跨版本最稳 T0)/物质分解液(真伤强装)/永动机/绝对热量(正当防卫对策);且**狼狩羁绊按场上装备数成长**(factions.md 原文),不建模装备 → 狼狩强度评估偏低。

## 装备数据(单一源 `cw_equipment.EQUIPMENTS` 158 件;旧 data/equipment.md 已删 2026-08-18)
- 简易装备(~7 类基础)/ 进阶装备(~33,2 简易合成)/ 特权装备(~27)/ 星徽钻石(~22)/ 白昼装备(~6,Fate ~24)/ 工具(~11)。
- 关键 T0:反重力皮靴(速度+20%,每回合+15% 可无限叠加,"找鞋战争")、物质分解液(生命+10%/速度+15%,每回合首次技能触发真伤,强装)、永动机(刷终结技)、绝对热量(正当防卫反伤对策)、生命之环(生存)。
- 来源:米游社百科(注册表字段带出处;2026-08-18 数据单一源收敛)。

## GameState 装备字段
```
equip: dict[str, list[str]]     # char_id → 装备名列表(每角色最多 3 件)
key_equips_owned: list[str]     # 已拥有的关键装备(反重力皮靴/物质分解液/...)
# 简化版(OCR 装备细节难时):equip_count_per_char: dict[str,int] + key_equips_owned
```

## 装备评分 = comp 相关(2026-08-03 用户:装备不单独评分,和阵容/目标挂钩)

**装备价值是 comp 相关的,不是绝对持有加分**。反重力皮靴对昼神阿雅(需 2 靴)是命脉,对别的 comp 不一定。故**不设独立 `equip_score` 加项**,装备并入 comp 评估(`comp_viability` / `comp_score`,详 10/03),用 **`equip_fit(comp, state)`** 驱动:

```
equip_fit(comp, state) =
    WK * holds(comp.key_equips, state)                # 持有【该 comp 的关键装备】(comp.key_equips 驱动,非通用 T0 裸分)
  + WS * stacking_bonus(comp.stacking_equips, state)  # 该 comp 受益的可叠加装备(如昼神用反重力靴)count**1.5(早拿复利)
  + WW * 狼狩_bonus(if comp 用狼狩)                   # 狼狩 comp 专属:按场上装备数 × tier 成长
# Comp 加字段 stacking_equips: list[str](该 comp 受益的可叠加装备);key_equips 已有。
```

**关键**:`equip_fit` 全程 comp 驱动 —— 同一件装备对不同 comp 评分不同(在 comp.key_equips/stacking_equips 里才算分)。不进 evaluate 的独立项,只在评 comp 时算(给 comp_viability 的装备维度 + select_comp 的 candidate 打分)。

`key_equips_owned`(bot 跟踪已有关键装备)仍保留,作为 `holds(comp.key_equips, state)` 的数据来源。**补给决策 `decide_supply`** 也 comp 相关:优先出 comp.key_equips / stacking_equips 里的(详 08)。

## Equip 动作(cw_state 加)
```
@dataclass
class ComposeEquip: simple_a: str; simple_b: str → adv Equip      # 2 简易 → 1 进阶
@dataclass
class AssignEquip: char_id: str; equip: str                        # 分配装备给角色
@dataclass
class UnequipEquip: char_id: str; equip: str                       # 拆装(拆装扳手)
```
plan 候选修增 ComposeEquip(有 2 同类简易 → 合成进阶,key_equipsOwned 更新)、AssignEquip(key_equip → 主 C)。

## 装备穿戴机制(UI op,2026-08-09 D-17 research 补)

**现状:bot 完全裸装** —— `EquipAll` op(drag-based,`operations/prep/equip_all.py`)因回归被**解绑**(git `e9747690`:drag 致「前台区域无角色」→ loop stall retry 46)。装备是 A8 成型关键(D-17:「1雅1鞋成型」、反重力皮靴必备、裸装输)→ **重启用 EquipAll = 当前最高杠杆**。

**机制(待 live 验)**:
- 攻略(D-17)说**拖拽**穿戴(装备区 owned equip icon → 角色装备槽)+ 「拆装扳手」道具拆装 + 2 简易合 1 进阶。与 `equip_all.py` 的 drag 方案一致(但有回归)。
- VLM 实测(D-17,跨 2 样本 万敌+镜流)+ **live 实测(r1-1 藿藿,2026-08-09)**:角色详情面板底部「装备推荐」按钮(~x1509,y816)。**click 后弹出「推荐装备」+「次选装备」列表(OCR 实锤),不是一键自动穿** —— "一键穿最佳"假设证伪。装备仍需从列表选(点推荐装备→穿?)或拖拽。
- **→ EquipAll 无 clean one-click 路径**:两条路 —— ① 修 drag 回归(`equip_all.py` drop zone / hold_time,git `e9747690`);② 实现 list-select 流程(开面板→装备推荐→点推荐装备→穿,每角色多 click)。每局保底 ≥3 装(开局+1/p1boss+1/p2boss+1 + 奖励/补给节点)。
- **下一步(live)**:进备战 + 点已部署角色开详情面板 → click「装备推荐」→ 截图/日志看是否自动穿戴。是 → 重写 EquipAll 为 click「装备推荐」;否 → 修 `equip_all.py` 的 drag 回归(drop zone / hold_time)。每局保底 ≥3 装(开局+1/p1boss+1/p2boss+1 + 奖励/补给节点)。

## 补给节点决策(decide_supply,完整性-5)
research §10.5:"补给角色有概率带红/蓝钻装备,未出钻就重刷(拿钻基本宣告胜利);位面1 补给优先级 姬子·启行 > 折叠小刀 > 轮回鞋;无钻时 鞋(反重力靴)> 电池(永动机)> 生命花(分解液/能量饮料)"。
```
decide_supply(options, state, config) → (idx, refresh?)
- 若某 option 带钻(OCR/规则识别)→ 选它(拿到基本赢)。
- 无钻 → 按优先级:反重力皮靴 > 永动机 > 物质分解液/能量饮料 > 其它;且可刷新 1 次(未出钻就刷)。
- 与 target_comp.key_equips 契合的装备优先(详 03)。
```

## 装备-阵容契合(select_comp 加项)
comp.key_equips(03 的 Comp 字段)进 comp_score:已拥有 comp.key_equips → comp 契合度 ↑。例如「昼神阿雅」comp.key_equips=["反重力皮靴"],开局拿到鞋 → 该 comp comp_score ↑。

## 数据需求(游戏边界)
- 装备图鉴:`cw_equipment.EQUIPMENTS`(注册表单一源)。**非游戏**(meta 数据)。
- 装备 OCR(补给选项 + 角色穿戴):**需游戏**(read_supply + read_equip)。
- 装备合成 OCR:补给/装备节点画面。**需游戏**。

## 测试(纯逻辑)
- equip_fit(comp):昼神阿雅持有反重力靴(其 key_equips)→ 高分;别的 comp 持有同靴不算分(comp 相关);狼狩 comp 的装备数 bonus;可叠加装备超线性(count**1.5)。
- decide_supply:带钻优先;无钻按 鞋>电池>花;刷新未出钻。
- ComposeEquip:2 简易 → 进阶;key_equips_owned 更新。

## round 3 补充(P1)
- **P1-4 装备合成树(recipe graph,high)**:07 加了 ComposeEquip 但**无合成树数据**(哪 2 简易→哪个进阶)。从 `cw_equipment.EQUIPMENTS`(注册表,合成公式字段)提 `EQUIP_RECIPES: dict[adv_name, (simple_a, simple_b)]`;ComposeEquip 查表(当前"有 2 同类简易→合成"太模糊,无具体配方无法决策合成什么)。建模**机会成本**(合成消耗 2 槽 vs 等更好 T0 drop)。
- **P1-5 可叠加装备超线性(high)**:research+07 明确"反重力皮靴每回合+15% 可无限叠加" → 早 commit 复利。`equip_fit(comp)`(comp 相关)对把反重力靴列入 `stacking_equips` 的 comp(昼神阿雅)用超线性 `count**1.5` 或复利 `(1.15)**count`(2 双远超 2×);别的 comp 持有同靴不算分。
- **R2-20 装备组件中间态(low)**:`equip_fit(comp)` 只奖成品 comp.key_equips,无"持有 2 简易即将合成 key_equip"中间态。加 component_progress 分(该 comp 的 key_equip 配方简易组件 × 合成接近度)。
