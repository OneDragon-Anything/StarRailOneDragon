# 0265 - 装备合成组件保留(P1 不入穿戴池)

- 日期:2026-08-24
- 状态:accepted
- 关联:r405;压测经济批 [29](`sim_压力测试_经济批_2026-08-23.md`);口述 [29]/[9]/[24];ADR-0154(M7 装备分配)、ADR-0254(装备层 sim 代理)、ADR-0252/0257(开局 hold)

## 背景 / 决策驱动

sim 压力测试经济批(n=60,snapshot 池,指纹 942d3f79)实锤:**16/60 局(27%)在 r5 附近的 supply 位把合成组件穿上场**——光能电池 ×11、轮滑鞋 ×5,穿着者多为准核心/过渡角色(绯英/爻光/三月七/藿藿…)。局70 实机同构形态(口述 [29] 的原始病例)。

根因(结构实锤):`cw_comps.equip_allocation` 三条路径(carry key_equips / core 吃满 / 兜底)均从 owned 池直接发放,无「组件不入穿戴池」判据;合成图谱 `cw_synthesis` 存在但装备层零消费。sim 装备代理与实机 EquipAll 消费**同一纯函数** → 实机同病,非 sim 伪影。

口述权威 [29](2026-08-23,看局70):「定阵容前不浪费装备合成/穿着」——过渡期把组件(量产型装甲/光能电池类)穿给过渡角色 = 锁死后续合成路线 + 浪费转移成本;组件在最终阵容确定前留在物品栏。与 [24] 的「过渡期关键装备穿上场」不冲突:[24] 说的是**输出装/关键装备**(进阶成品),不是**合成组件**。

## 决策

P1(plane==1)阶段,合成保留组件集 **不入穿戴池**,留在 owned 待合成:

- **组件集单一源**:`cw_synthesis.RESERVED_COMPONENTS = SYNTHESIS_BASES ∪ {光能电池}`(新增常量,从既有图谱派生;装备层消费它,不复制清单)。
- **落点**:`equip_allocation` 增加 `plane` 参数(默认 1),P1 时过滤池;`EquipAll` op 与 sim 代理(cw_sim)同函数同生效。
- **P2+ 过滤关闭**:合成窗口随 P1 过渡期关闭,组件穿着不再锁路线(保留 owned 不再有意义)。

### 豁免边界(key_equips)

组件恰是 comp 的 `key_equips` 成员时放行——key_equips 是 comp 显式声明的关键装备意图(角色特定价值 > 合成保留)。**实查 COMP_LIBRARY 全部 key_equips 与 RESERVED_COMPONENTS 零重叠**(脚本核验),豁免当前零命中,是防御性判据:未来 comp 若显式要求组件(如「合成前过渡穿着」打法)不需改本函数。

## Considered Options

| 选项 | 结论 |
|---|---|
| **A(选定):equip_allocation 加 plane 过滤** | 纯函数层单点修复,sim/实机/测试同源生效;组件集消费图谱单一源 |
| B:EquipAll op 侧过滤 | 只修实机,sim 代理不经过 op → sim 检查项永远看不到修复效果,双源 |
| C:组件也禁止拾取(decide_supply 不选) | 拿组件本身没问题(`_EQUIP_VALUE` 估值合理,压测确认「拿没问题,穿才是问题」);禁拾 = 放弃合成路线素材 |
| D:过滤所有位面 | 过度——P2/P3 合成窗口已关,组件穿着的「锁路线」代价不存在 |

## 后果

- **正向**:合成路线不再被过渡穿着锁死;检查项 `no_component_equipped_p1`(0 容忍)入 sim 批量检查集。
- **权衡**:P1 期间组件槽位的微弱过渡战力被放弃(组件本身数值低,期望损失可忽略;sim A/B 验证 hp 指标不恶化)。
- `check_equip_worn_in_battle` 联动:owned 全是保留组件时 equipped 空是合法形态,不计入「白板挨打」判定(防误报)。
- 锁更新:`test_cw_floor_and_equip` / `test_equip_alloc_identity` 的 owned 清单原含组件名(轮转/兜底语义与组件无关)——换非组件名保持原语义,语义修正注记进测试 docstring(r354 先例)。

## 验证

- 单帧锁:`test_cw_r405_component_reserve.py`(P1 组件不上身 / P2 放行 / key_equips 豁免 / 容量语义不变 / 检查项双向)。
- sim A/B(n=60 snapshot,同种子域):见 ADR 报告与进度树;`no_component_equipped_p1` 违规 16/60 → 0。
