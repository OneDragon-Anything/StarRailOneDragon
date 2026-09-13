# 补给选卡升级 落地

> 阶段唯一源纪律：本文件 = 账本阶段唯一源；设计改 → 本文件改 → 账本跟着改，禁两处各自演化。
> 通用工程门 = od-dev-progress-tracking §12（含 `ruff check` 仅改动文件、测试纪律；各阶段完成判据统一引用，不逐条复述）。
> 阶段骨架单一源 = details/supply-value-spec.md §6（依赖切分：P-1/P-2 无依赖可先行并行；P-4 等 env 机器落地）。

## 3.1 P-1 装备价值共享机器

**范围**：新建 `kernel/cw_equip_value.py` 三件套（`EQUIP_GENERIC_VALUE` 逐值平移 + `equip_material_generality` 注册表化 + `key_fit_names`）+ §1.3 迁移表六消费位重接（supply/box/wear/planner/sim 采样/sim 审计）。迁移性质：box/supply/planner/sim = 行为等价（仅符号与数据源换）；**wear 一处行为变化** = 未锁态 stash_comp +100 移除（用户裁定 2026-09-12 OQ-2 严格版裁定 5，锁 S13）；sim/checks 跨模块私有 import 坏味消除。边界：不含 decide_supply 两态化（P-3）、不含角色维。

**设计依据**：details/supply-value-spec.md §1.3（三件套与迁移表）

**文件面**：`kernel/cw_equip_value.py`（新建）、`kernel/cw_events.py`、`kernel/cw_prep_expect.py`、`strategies/impl/flow.py`（box 段）、`operations/cw_screen/cw_screen_equip_pick.py`、`sim/engine_p1.py`、`sim/checks/ledger.py`、`sr-od-test/test/sr_od/app/currency_war/test_cw_supply_pick.py`（新建，V 组先行）

**依赖**：无

**优先级建议**：5

**完成判据**：
- V1/V2/V3 漂移锁全绿（表平移快照对拍/通用性 8 名对拍/key_fit_names ⊆ ROSTER）
- S13 行为变化锚点全绿（wear 未锁态 stash 契合不再胜出）
- 其余消费位回归帧全绿（值零变化：box/supply/planner/sim 现行为锁）
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单（V 组 + 回归帧）+ ruff check

> **代位指针（armory-box-value 定稿）**：本阶段 P-1 已由 `2026-09-12-armory-box-value/landing.md` §3.1 代位执行并交付——V2 判据修订（原「通用性 8 名对拍」与注册表真相互斥：手表梯度无据，改独立构造对拍 + 形态快照）、件 2 薄委托暂缓（material_value 保持手表本体至该迭代 3.2 随打分器整体退役消灭）、S13 认领归属该迭代 3.1。编排者不再按本 §3.1 另立 P-1 任务。

## 3.2 P-2 执行面卫生

**范围**：`_supply_refresh_used` 布尔升格节点戳 `_supply_refresh_node (plane, round)`（op + sim 两写点、ExecState 字段、旧布尔删除）；`flow.py:537` 与 `cw_strategy.py:173`「OCR 未就绪」滞后 docstring 修正。边界：不碰 decide_supply 判据（P-3）。

**设计依据**：details/supply-value-spec.md §2 执行模型 + §1.4 现状盘点「刷新旗标缺陷」

**文件面**：`operations/cw_screen/cw_screen_supply_node.py`、`sim/engine_p1.py`、`kernel/cw_exec_state.py`、`strategies/impl/flow.py`、`strategies/impl/cw_strategy.py`、`sr-od-test/test/sr_od/app/currency_war/`（多补给节点刷新可用锁）

**依赖**：无（与 3.1 文件域交叠点 = engine_p1，批序编排者裁）

**优先级建议**：4

**完成判据**：
- 多补给节点帧刷新可用锁全绿（第二补给节点刷新不再被吞）
- 现有供给 op 锁全绿
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + ruff check

## 3.3 P-3 补给决策两态化

**范围**：kernel `decide_supply` 重写（§1.4 决策序：带钻分支含宝钻/单钻细分、无条件先刷+带钻跳刷、已锁态 key_fit 成品+10/材料+3、未锁态纯通用值；签名改 `locked_comp/evicted` 关键字，`config` 参数移除）+ flow wrapper 接线（locked_comp/evicted，decide_invest 先例同款）+ sim 调用点改参。锁 S1-S6、S8、S11、S12。边界：角色维占位 0（P-4）、不碰 obs 层。

**设计依据**：details/supply-value-spec.md §1.1/§1.3/§1.4/§2（锁表 S 组先行条）

**文件面**：`kernel/cw_events.py`、`strategies/impl/flow.py`、`sim/engine_p1.py`、`sr-od-test/test/sr_od/app/currency_war/test_cw_supply_pick.py`（增锁）

**依赖**：3.1

**优先级建议**：5

**完成判据**：
- S1-S6/S8/S11/S12 全绿（含 S8 行为变化锚点：伪 comp key 契合不再胜出）
- `test_cw_supply_options_dualrow.py` + sim 供给路径冒烟 + supply 相关既有锁回归全绿
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + 回归文件 + ruff check

## 3.4 P-4 角色层接入

**范围**：`char_candidate_tier`（env §2.1 机器单角色底座，复用禁复制）+ `line_identity_tier` 过渡维 max 合成 + w_P1 线性衰减 + evicted 传递；锁 S7、S9、S10。边界：env 侧底座若缺单角色 helper 由 env 侧扩（详设契约 1），本迭代禁第二遍历。

**设计依据**：details/supply-value-spec.md §1.2（两态角色层与衰减）/ §5（S7/S9/S10）

**文件面**：`kernel/cw_comps.py`（或 env 侧指定落点）、`kernel/cw_events.py`（角色分接入）、`sr-od-test/test/sr_od/app/currency_war/test_cw_supply_pick.py`（增锁）

**依赖**：3.3；`2026-09-12-invest-env` §2.1 机器落地

**优先级建议**：4

**完成判据**：
- S7（衰减两侧）/S9/S10 全绿
- supply 相关全部锁回归全绿
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + 回归文件 + ruff check

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1、3.2、3.3、3.4
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `strategy-docs/13_pick_family.md` §判据表 supply 行（两态价值模型/刷新判据/角色层指针）+ 「OCR 未就绪」滞后标注清除 ← 3.3/3.4
- `strategy-docs/08_events.md` E4 节（组件缺口：结构版落地/数值化挂账指针）← 3.3
- `strategies/impl/flow.py` docstring（:497 括注过期、:537）——代码批内修，语义面本阶段核对 ← 3.3
