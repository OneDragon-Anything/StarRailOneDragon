# P59:阵容成型门适用帧的买入集与「阵容外+围栏」件不相交(换阵卖出义务分支无振荡风险)

> 状态:**证伪(注册表反例 + 代码语义 + 帧级复现;2026-09-06)**
> 对象:换阵卖出义务分支——`cw_op_deploy.offtarget_sell_allowed`
> (`fenced_offline_sellable`/`protect_names` 参,L194-228)、触发门
> `fenced_swap_arm_of`(L247-254)、喂入单一源(唯一事实来源,下同)
> `swap_arm_deployed_count`
> (L231-244;该执行侧真读读口已随部署机执行侧停用与死代码清偿移除——
> 现役板满前提按决策帧状态容器(GameState)计数);买面单一源 `cw_intention.locked_buy_membership`
> (`cw_intention.py:1572-1608`)与 `_line_hoard`(L1375-1399)。
> 依据:(含 2026-09-05 原裁定文档修订「P18 型结构命题」立项登记待办)、
> 原裁定文档修订节(已停用)、`flow.py:224-264`(target_comp = get_comp(locked_comp)
> 单源物化)、`shop.py:434-487`(buy_members 消费)。
> 复现:`未入库临时档案(git 外)cw_math_batch/prop_repro.py::prop1`(注册表直调,只读)。

## 命题(形式化)

设帧 F 满足**门的适用前提**(即落入该门的管辖范围):换阵卖出义务分支激活,即

- `form_progress(target_comp, state) ≥ 1.00`(阵容成型,单一源 cw_comps);
- `swap_arm_deployed_count ≥ front_n + back_n`(上阵区已满,部署数原由画面模板匹配实读——该读口已随部署机执行侧停用与死代码清偿移除,现役前提按决策帧状态容器板面计数);
- 备战席有目标阵容单位(D-3 守卫,`cw_op_deploy.py:441`)。

记:

- **买入集** B(F) = `locked_buy_membership(ist)`(阵容锁定帧〔终局阵容已锁定,`locked_comp` 已设〕 = `_line_hoard(locked_comp)`
  角色全集;未锁定阵容的帧 = k_members,不在本命题范围内);
- **阵容外+围栏的可卖集** S(F)〔围栏=fence:上场/卖出资格的排除规则;阵容外=目标阵容之外,下同〕 = { deployed 单位 d :
  bonds(d) ∩ all_factions(target_comp) = ∅ ∧ bonds(d) ∩ (RECIPE ∪ ENGINE) ≠ ∅
  ∧ d ∉ target_cores ∪ protect_names },其中 protect_names = target_comp
  core∪shared(全条件代入 `offtarget_sell_allowed`)。

**命题:门的适用前提下 B(F) ∩ S(F) = ∅。**(成立则义务分支无买↔卖振荡风险;
证伪则触发门须修。)

## 证明(证伪:注册表反例 + 代码语义推导 + 复现)

### ① 两面判定域不同构(根因)

买面成员判定(`_line_hoard`,cw_intention.py:1382-1396)的成员全集 =:

```
core_chars ∪ shared_chars ∪ 替班者(substitute_plan)
            ∪ {(factions|flows) ∩ (form_tiers ∪ sub_tiers 键) ≠ ∅ 的注册表成员}
```

(符号改名指针:上式的 `form_tiers ∪ sub_tiers 键` 已随 comp-structure-unification 3.1 并入 `faction_reqs`——现读法 = `core_faction_reqs ∪ bonus_faction_reqs` 键,键集恒等,判定域不变。)

卖面保护域(`offtarget_sell_allowed` L221-224 + `_protect` L463-465)的
不可卖全集 = `target_cores ∪ protect_names` = core∪shared,外加
`bonds ∩ all_factions ≠ ∅` 的 target 单位豁免
(all_factions = `factions ∪ flex_factions`,cw_comps.py:164-167)。

**唯一无羁绊保证的分支 = 替班者**:它凭 `substitute_plan` 直接入买入集,
不经任何「bonds ∩ 阵容羁绊 ≠ ∅」检查;卖面也不在 core∪shared 内。
两边一交即穿。

### ② 注册表反例:黄泉减益 × 卡芙卡(替班者)

注册表直调(对全部 20 个阵容扫描,`prop_repro.py::prop1`):

| 检查 | 值 |
|---|---|
| 卡芙卡 ∈ locked_buy_membership(黄泉减益) | True(经 substitute_plan 替班者分支,L1383-1385) |
| bonds(卡芙卡) | {持续伤害, 星核猎手} |
| all_factions(黄泉减益) | {减益, 击破, 巡海游侠, 治疗, 追击, 量子同频} → 交集 ∅ = 阵容外 |
| bonds ∩ (RECIPE∪ENGINE) | {持续伤害}(ENGINE_FACTIONS/RECIPE_FACTIONS 均含)→ 围栏件(可卖) |
| ∈ core / ∈ shared | False / False → 不受 target_cores/protect_names 护 |
| **offtarget_sell_allowed(fenced_offline_sellable=True)** | **True(分支可卖)** |

即 |B ∩ S| ≥ 1,命题不成立。∎(证伪)

同扫描的其余 4 个「囤积集角色对本阵容为阵容外」实例(不死途/布洛妮娅/
刃/白厄)全部落在 core∪shared 保护域内,不入 S(白厄 bonds 为空但属
core,受 target_cores 护)——反例唯一,但结构性(替班者分支无约束,
后续注册表新增替班者即可复发)。

### ③ 前提帧可实现性

门的适用前提帧可现实发生:卡芙卡作为持续伤害引擎件在过渡期买入并上场
(此前登记过的一起振荡事故,形态即「引擎件闲置占位」),后续终局阵容锁定为黄泉减益、
fp 达 1.00、上阵区已满——与 第七局死锁帧同构(旧阵容的件在场上 + 新阵容的
备战席成员待进场),只是此处旧阵容的件同时是**新阵容的替班者**。

### ④ 反方向排除记录(证明已尽力攻击)

- 「fp 与 locked_comp 不一致帧」不是本案根因:`flow.py:245/264` 中
  `session.target_comp = get_comp(ist.locked_comp)` 单源物化,阵容锁定帧
  两面同一阵容——**预设的修法「触发门改 locked_comp 单一源」
  对本案无效**(单一源本已成立,裂口在成员全集不同构)。
- sub_tiers/form_tiers 档位键 ⊆ all_factions:20 个阵容全量 0 违例
  (档案位键契约成立,非裂口)。
- 未锁定阵容的帧(k_members = core∪shared)与 S 天然不相交(core∪shared 受
  protect)——命题只在阵容锁定帧破。

## 结论

**证伪**:fp≥1.00 门适用帧内,买入集与阵容外+围栏的可卖集可相交
(现行注册表已有实例:黄泉减益 × 卡芙卡)。义务分支对替班者件存在
买↔卖振荡风险:M2 按义务买入(reason='m2_line_member',不走利息门)、
换阵分支按阵容外+围栏卖出,同一身份两面矛盾。

## 工程后果(修法路由)

1. **治本候选(推荐,语义单一源)**:`protect_names` 并入
   `substitute_plan` 替班者全集。依据 = `Comp.substitute_plan` 字段
   契约原文「替班=『不卖、转副C沉淀』」(cw_comps.py:132-135)——
   卖替班者本就违替班语义;死锁担忧不回归(死锁件是旧阵容的
   普通件,替班者属新阵容的沉淀位,且数量 1-2/阵容,占位代价可控)。
   需 ADR 批 + 真值表测试更新 + 「替班者占位 vs 备战席目标成员进场」
   优先级语义补裁。
2. **备选(买面收窄)**:M2 义务集剔除「阵容外 ∧ 围栏可卖 ∧ 非保护」
   成员(替班者降机会性 EV 买)——保留义务纯度,但替班者再无到岗
   通道,违 substitute_plan 设计意图,需先修设计再实现。
3. **预设修法作废登记**:「触发门改 locked_comp 单一源」
   不成立(目标阵容本就单源于 locked_comp,flow.py:245)——本篇
   即该登记待办的回写:裂口在成员全集,不在 fp 一致性。
4. 防回归引用:注册表级静态断言「囤积集角色中对本阵容为阵容外 ∧
   围栏可卖的成员必须 ⊆ core∪shared∪替班者保护域」可机检
   (prop_repro.py::prop1 即该断言的实现)。

## 关联

- P18(同型集合过滤命题,release 门——本篇为其换阵分支姊妹篇,结论相反);
- (登记待办出处与预设修法)、原裁定文档修订节(买面/卖免面三面
  拆分——本篇是该拆分的第二处域间裂缝);
- P60(同批:终局阵容锁定后囤积集换手循环收敛性,买面义务集与 M4 的另一裂缝)。
