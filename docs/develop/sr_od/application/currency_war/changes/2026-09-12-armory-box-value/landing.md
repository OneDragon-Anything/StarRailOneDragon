# 武装箱选卡价值升级 落地

> 阶段唯一源纪律：本文件 = 账本阶段唯一源；设计改 → 本文件改 → 账本跟着改，禁两处各自演化。
> 通用工程门 = od-dev-progress-tracking §12（含 `ruff check` 仅改动文件、测试纪律；各阶段完成判据统一引用，不逐条复述）。
> 状态：草案（设计对抗未过，不可立账本任务派落地批）。

## 3.1 装备价值共享机器（吸收源迭代 P-1 + 本迭代接口扩展）

**范围**：执行 `2026-09-12-supply-selection/landing.md` §3.1（P-1）全量范围——`kernel/cw_equip_value.py` 三件套（`EQUIP_GENERIC_VALUE` 逐值平移 / `equip_material_generality` 注册表化 / `key_fit_names`）+ 六消费位重接（supply/box/planner/sim 采样/sim 审计行为等价，wear 一处行为变化 S13 归源迭代判据）；本迭代**追加**机器第四件：`key_recipe_pairs(key_equips)`（design.md §2.1，`key_fit_names` 改为由它派生，V4 派生一致性锁）+ 通用选装入口 `equip_tier` / `pick_equipment`（design.md §2.1/§2.2，本阶段落完整实现，行为语义锁归 3.2 的 B 组）。边界：不含 box 打分切换（3.2）；若源迭代 P-1 已交付，本阶段缩减为接口扩展 + V4/V 组增量。

**设计依据**：本迭代 design.md §2.1；`2026-09-12-supply-selection/landing.md` §3.1（共享部分范围单一源）

**文件面**：`kernel/cw_equip_value.py`（新建）、`kernel/cw_events.py`、`kernel/cw_prep_expect.py`、`strategies/impl/flow.py`（box 段符号重接）、`operations/cw_screen/cw_screen_equip_pick.py`、`sim/engine_p1.py`、`sim/checks/ledger.py`、`sr-od-test/test/sr_od/app/currency_war/test_cw_supply_pick.py`（V 组，源迭代 P-1 已建则复用）

**依赖**：无

**优先级建议**：5

**完成判据**：
- V1/V2/V3 漂移锁 + V4（`key_fit_names` ≡ keys ∪ `key_recipe_pairs` 全成员，抽样对拍）全绿
- `pick_equipment` 未锁退化路径帧全绿（空 key_equips = 纯 base 排序；空 names → 0）
- 六消费位回归帧全绿（box/supply/planner/sim 值零变化；wear S13 归源迭代判据不在此重复断言）
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + ruff check

## 3.2 武装箱选卡序数化 + 两态锚定 + 近兑现档

**范围**：design.md §2.2-§2.6——`decide_box_card` 薄壳化：解析 locked_comp 两态锚（`_ensure_intention`，`get_comp` 失败落未锁 + 日志哨兵）+ owned 账传递（`session.last_owned_equips`）→ 调机器 `pick_equipment`（3.1 件），自身零打分实现；tier 2 近兑现判定语义 = design.md §2.3，锁打在 `pick_equipment` 纯函数上（供后续消费位复用）+ 一条 box 集成帧锁 wrapper 接线（锚解析/账传递/OCR 序输入）。旧锁处置：`test_cw_material_score.py` 的 target_comp 锚改 locked_comp（锚定语义已被本设计取代，锁重推非机械跟绿；docstring 记改锚原因），其两条断言语义在重锚后保持。新增行为帧锁对照 design.md §2.6 行为变化表逐行（变化行锁新行为、等价行锁现行行为保持，含 R1 加法→序数等价回归帧）。边界：不碰 decide_supply / decide_planner / equip_pick 判据（§2.8 通用化边界，挂后续裁定）、不碰 obs 层与执行器（`_pick_box_card` 机械链不动）。

**设计依据**：design.md §2.2/§2.3/§2.4/§2.5/§2.6/§2.7

**文件面**：`strategies/impl/flow.py`（decide_box_card 及其 docstring）、`sr-od-test/test/sr_od/app/currency_war/test_cw_material_score.py`（重锚）、`sr-od-test/test/sr_od/app/currency_war/test_cw_armory_box_pick.py`（新建，B 组 + R1）

**依赖**：3.1

**优先级建议**：5

**完成判据**：
- design.md §2.6 行为变化表逐行锁全绿（新文件 B 组，锁名清单进交付报告）
- R1 等价回归帧全绿（现行三档行为逐点保持）
- `test_cw_material_score.py` 重锚后全绿 + box 相关既有锁（test_cw_box_pick_arm / test_cw_box_open_pick_merged / test_cw_obs_arch_prep_writeflow 扫描锚）全绿
- sim 选卡路由核实结论落报告（design.md §2.7：经策略可见 / 内嵌默认结构性不可见，二选一如实申报，附核实证据）
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + sim 路由核实记录 + ruff check

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1、3.2
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `strategy-docs/13_pick_family.md` §判据表 E18 行（decide_box_card）：判据列重写为序数分档制 + 两态锚定 + 近兑现档指针；数值只写常量名/函数名（单一源在代码）← 3.2
- `strategies/impl/flow.py` `decide_box_card` docstring 语义核对（语义面归本阶段核对，改写随 3.2 代码批内完成）← 3.2
