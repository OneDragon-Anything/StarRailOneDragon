# P59:线成型门辖帧买入集与 off-line 围栏件不相交(换阵卖出义务臂无振荡风险)

> 状态:**证伪(注册表反例 + 代码语义 + 帧级复现;2026-09-06)**
> 对象:ADR-0522 换阵卖出义务臂——`cw_op_deploy.offtarget_sell_allowed`
> (`fenced_offline_sellable`/`protect_names` 参,L194-228)、触发门
> `fenced_swap_arm_of`(L247-254)、喂入单一源 `swap_arm_deployed_count`
> (L231-244);买面单一源 `cw_intention.locked_buy_membership`
> (`cw_intention.py:1572-1608`)与 `_line_hoard`(L1375-1399)。
> 依据:ADR-0522(含 2026-09-05 修订节「P18 型结构命题」立项挂账)、
> ADR-0521 修订节、`flow.py:224-264`(target_comp = get_comp(locked_comp)
> 单源物化)、`shop.py:434-487`(buy_members 消费)。
> 复现:`.debug/temp/cw_math_batch/prop_repro.py::prop1`(注册表直调,只读)。

## 命题(形式化)

设帧 F 满足**门辖前提**:换阵卖出义务臂激活,即

- `form_progress(target_comp, state) ≥ 1.00`(线成型,单一源 cw_comps);
- `swap_arm_deployed_count ≥ front_n + back_n`(板满,SIFT 真读部署数);
- bench 有 target 单位(D-3 守卫,`cw_op_deploy.py:441`)。

记:

- **买入集** B(F) = `locked_buy_membership(ist)`(锁线帧 = `_line_hoard(locked_comp)`
  角色全集;未锁帧 = k_members,不辖);
- **off-line fenced 臂可卖集** S(F) = { deployed 单位 d :
  bonds(d) ∩ all_factions(target_comp) = ∅ ∧ bonds(d) ∩ (RECIPE ∪ ENGINE) ≠ ∅
  ∧ d ∉ target_cores ∪ protect_names },其中 protect_names = target_comp
  core∪shared(ADR-0522 决策 1/2 全条件代入 `offtarget_sell_allowed`)。

**命题:门辖前提下 B(F) ∩ S(F) = ∅。**(成立则义务臂无买↔卖振荡风险;
证伪则触发门须修。)

## 证明(证伪:注册表反例 + 代码语义推导 + 复现)

### ① 两面判定域不同构(根因)

买面成员判定(`_line_hoard`,cw_intention.py:1382-1396)的成员全集 =:

```
core_chars ∪ shared_chars ∪ 替班者(substitute_plan)
            ∪ {(factions|flows) ∩ (form_tiers ∪ sub_tiers 键) ≠ ∅ 的注册表成员}
```

卖面保护域(`offtarget_sell_allowed` L221-224 + `_protect` L463-465)的
不可卖全集 = `target_cores ∪ protect_names` = core∪shared,外加
`bonds ∩ all_factions ≠ ∅` 的 target 单位豁免
(all_factions = `factions ∪ flex_factions`,cw_comps.py:164-167)。

**唯一无羁绊保证的腿 = 替班者**:它凭 `substitute_plan` 直接入买入集,
不经任何「bonds ∩ comp 羁绊 ≠ ∅」检查;卖面也不在 core∪shared 内。
两边一交即穿。

### ② 注册表反例:黄泉减益 × 卡芙卡(替班者)

注册表直调(20 comp 全量扫描,`prop_repro.py::prop1`):

| 检查 | 值 |
|---|---|
| 卡芙卡 ∈ locked_buy_membership(黄泉减益) | True(经 substitute_plan 替班者腿,L1383-1385) |
| bonds(卡芙卡) | {持续伤害, 星核猎手} |
| all_factions(黄泉减益) | {减益, 击破, 巡海游侠, 治疗, 追击, 量子同频} → 交集 ∅ = off-line |
| bonds ∩ (RECIPE∪ENGINE) | {持续伤害}(ENGINE_FACTIONS/RECIPE_FACTIONS 均含)→ fenced |
| ∈ core / ∈ shared | False / False → 不受 target_cores/protect_names 护 |
| **offtarget_sell_allowed(fenced_offline_sellable=True)** | **True(臂可卖)** |

即 |B ∩ S| ≥ 1,命题不成立。∎(证伪)

同扫描的其余 4 个「hoard 角色对本 comp off-line」实例(不死途/布洛妮娅/
刃/白厄)全部落在 core∪shared 保护域内,不入 S(白厄 bonds 为空但属
core,受 target_cores 护)——反例唯一,但结构性(替班者腿无约束,
后续注册表新增替班者即可复发)。

### ③ 前提帧可实现性

门辖前提帧可现实发生:卡芙卡作为持续伤害引擎件在过渡期买入并上场
(ADR-0386 W209 振荡事故即「引擎件躺板」形态),线后续锁向黄泉减益、
fp 达 1.00、板满——与 ADR-0522 第七局死锁帧同构(旧线件在板 + 新线
bench 待进场),只是此处旧线件同时是**新线替班者**。

### ④ 反方向排除记录(证明已尽力攻击)

- 「fp 与 locked_comp 不一致帧」不是本案根因:`flow.py:245/264` 中
  `session.target_comp = get_comp(ist.locked_comp)` 单源物化,锁线帧
  两面同一 comp——**ADR-0522 预设的修法「触发门改 locked_comp 单一源」
  对本案无效**(单一源本已成立,裂口在成员全集不同构)。
- sub_tiers/form_tiers 档位键 ⊆ all_factions:20 comp 全量 0 违例
  (档案位键契约成立,非裂口)。
- 未锁帧(k_members = core∪shared)与 S 天然不相交(core∪shared 受
  protect)——命题只在锁线帧破。

## 结论

**证伪**:fp≥1.00 门辖帧内,买入集与 off-line fenced 臂可卖集可相交
(现行注册表已有实例:黄泉减益 × 卡芙卡)。义务臂对替班者件存在
买↔卖振荡风险:M2 按义务买入(reason='m2_line_member',不走息律门)、
换阵臂按 off-line fenced 卖出,同一身份两面矛盾。

## 工程后果(修法路由)

1. **治本候选(推荐,语义单一源)**:`protect_names` 并入
   `substitute_plan` 替班者全集。依据 = `Comp.substitute_plan` 字段
   契约原文「替班=『不卖、转副C沉淀』」(cw_comps.py:132-135)——
   卖替班者本就违替班语义;ADR-0522 死锁担忧不回归(死锁件是旧线
   普通件,替班者属新线沉淀位,且数量 1-2/comp,占位代价可控)。
   需 ADR 批 + 真值表锁更新 + 「替班者占位 vs bench target 进场」
   优先级语义补裁。
2. **备选(买面收窄)**:M2 义务集剔除「off-line ∧ fenced ∧ 非保护」
   成员(替班者降机会性 EV 买)——保留义务纯度,但替班者再无到岗
   通道,违 substitute_plan 设计意图,需先修设计再落码。
3. **ADR-0522 预设修法作废登记**:「触发门改 locked_comp 单一源」
   不成立(目标 comp 本就单源于 locked_comp,flow.py:245)——本篇
   即该挂账的回写:裂口在成员全集,不在 fp 一致性。
4. 防回归锚:注册表级静态断言「hoard 角色中对本 comp off-line ∧
   fenced 的成员必须 ⊆ core∪shared∪替班者保护域」可机检
   (prop_repro.py::prop1 即该断言的实现)。

## 关联

- P18(同型集合过滤命题,release 门——本篇为其换阵臂姊妹篇,结论相反);
- ADR-0522(挂账出处与预设修法)、ADR-0521 修订节(买面/卖免面三面
  拆分——本篇是该拆分的第二处域间裂缝);
- P60(同批:锁线 hoard 换手循环收敛性,买面义务集与 M4 的另一裂缝)。
