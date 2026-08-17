# 08 节点决策:遭遇 / 补给 / 巨星(分,完整性-2/3/5 补)

> 总见 [README](README.md)。review r1(方案)发现:遭遇难度选择、巨星强化、补给出钻 三块节点决策 naive 或缺失。这些是 A8 高胜率的关键节点决策(非买/deploy/升/刷新的核心循环,但每局必遇)。

## 决策接线状态(2026-08-17 刷新)

> 模式:handler 应 **read 选项 → 调 `strategy.decide_*` → 点选中项**,非硬编码默认。

| 决策点 | 策略函数 | reader | handler 接入 | 状态 |
|---|---|---|---|---|
| 买牌 | `plan` ✅ | `read_shop_cards` ✅ | BuyShopCards ✅ | ✅ 接入(D-90 修 refresh) |
| 投资环境/策略 | `decide_invest`→`decide_event` ✅ | OCR 卡名 ✅ | HandleInvest* ✅ | ✅ 接入 |
| **遭遇** | `decide_encounter` ✅(难度三态+奖励,P9/2026-08-17) | `read_encounter_options` ✅(D-91) | HandleEncounter ✅(D-91) | ✅ 接入 |
| **补给** | `decide_supply` ✅(钻优先+无钻重掷,2026-08-17) | `read_supply_options` ✅(含钻识别双通道) | RunSupplyNode ✅(含刷新按钮流) | ✅ **接入** |
| 巨星 | `select_megastar` ✅(comp 级偏好绑定,19 号 P2/2026-08-17) | `read_megastar_options` ✅(D-95) | RunMegastarNode ✅(D-95/D-96) | ✅ 接入 |
| 伙伴 | (PartnerOption,fn 待写) | 候选名 OCR ❌缺 | HandleSelectPartner ❌(取最左) | ❌ 待接 |
| 部署 | plan 的 `DeployMove` | 备战席身份(SIFT)✅ D-12 | DeployBench ✅ | ✅ 接入 |

**接入 6 / 未接 1**(伙伴:候选只立绘无角色名,真接需 SIFT 立绘)。

## 遭遇节点(decide_encounter,2026-08-17 P9 增强)

**评分 = 词缀契合 + 难度档定价(36 号账本三态)+ 奖励价值(与敢难联动)**:

- **难度三态**(用户口径「阵容足够强才敢难」):压 −2 档价值作风险计——
  碾压(form≥0.9,gap≤−36)→ **敢难白拿奖励**;边际/未成型(压档值一条命)→ 保守保血。
  `encounter_tier_score` 包装 36 号 `marginal_value`(三态+P1 尖峰 ×1.5)。
- **奖励价值**(OCR 奖励带本就在读):文本启发分档 棱彩 1.0>进阶 0.8>简易 0.65>
  经验 0.6>无 0.5(OCR 漏不惩罚)——**与敢难联动**:敢难时高难+棱彩额外 +0.2;
  不敢难时奖励不兑现;P3 永避高难维持(ADR-0130),奖励仅轻 tiebreak。
- **词缀**:全分支克 comp → 刷新换批;有利分支 → 选最利(debuff=buff)。
- 血量参照:1.052^d(米游社拟合)落 `_difficulty_hp_ratio`(备用)。
- **扑满识别**(P11,等扑满图):含扑满分支奖励更高,SIFT 模板路(与钻识别同款)。

> **状态(2026-08-04,D-19)**:`decide_encounter` 纯逻辑骨架**已实现 + 4 测试绿**(`cw_decisions.py`):未成型→低难度 / 全分支克 comp→刷新 / 成型+利 comp(debuff=buff)→高难度。`EncounterOption`(idx/难度/词缀/奖励)+ `EncounterPick`(idx/refresh/reason)。**handler 接线待阶段 5**(`read_encounter_options` OCR + `handle_encounter` 改调,替代 naive 选左)。

## 巨星强化(select_megastar,完整性-2,high)

**详 [03 阵容规划](03_comp_planning.md#巨星选择)**:`select_megastar(state, target_comp) → char`。
**2026-08-17 重写**(19 号 P2):选择序 = core 在阵绑定 → `COMP_MEGASTAR_PREFERENCE`
comp 级偏好表(前台单核族→星期日 +132% 首位直乘/暴击引擎族→知更鸟 +55% 幸运率/
战技点→花火/击破→大丽花|加拉赫/DoT 5费堆叠→黑天鹅 满档最大乘区)→ 机械属性兜底
→ naive。巨星效果是**乘区**,绑定逻辑 = comp 引擎 × 乘法关系(非单属性键)。

## 补给节点(decide_supply,✅ 全链接入 2026-08-17)

**决策链(钻优先 + 无钻重掷)**:
1. **带钻**(红/蓝/财富宝钻)→ 直选(基本赢级价值);
2. **无钻 + 刷新未用** → 点刷新按钮重掷(钻概率再抽一次);
3. 刷过 → `target_comp.key_equips` 契合(+10 碾压)+ 通用装备价值(鞋>电池>花)选。

**钻识别双通道**(2026-08-17):主 = SIFT(装备 icon 区扫三钻模板,31 张存档实测
4 命中/27 零误报/红钻样本三方对拍一致);兜底 = OCR 装备名精确匹配。
**刷新按钮**(同日实锤):VLM 判建档图 + 采集数据锚 (974,854)——图标式按钮
(OCR 找不到是因为无文字),「剩余次数:1」;旧断言「无刷新按钮」作废。

## 数据需求(游戏边界)
- ~~遭遇选项/巨星候选/补给选项 OCR~~ ✅ 均已建(reader 落 cw_node_obs);
- 词缀表 + 对策映射 ✅(MECHANIC_COUNTERS/SYNERGIES);
- **扑满图**(P11,等用户提供):遭遇小怪含扑满分支奖励更高,SIFT 模板路。

## 测试(纯逻辑)
- decide_encounter:未成型→低难度;碾压敢难;**奖励 tie-break 敢难/不敢难两态**;词缀克→刷新。✅ 97 过
- select_megastar:comp 级偏好表(前台单核→星期日/暴击引擎→知更鸟/…)。✅ 6 过
- decide_supply:带钻优先;无钻→刷;刷过按契合。✅
