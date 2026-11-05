# or_reqs 退役符号清理清单（详设）

## 问题与约束

- 边界：`or_reqs` 字段及其全部字段层机器的符号级删除；**不动** kernel 结算侧谓词族（总纲契约 D：`seele_system_formed` / `SEELE_AMP_FACTIONS` / `engines_count` / `is_seele_system_member` / `SYSTEM_LINE_FACTIONS` / cw_system_cards 数据层 / cw_engine_facts / cw_win_model / cw_battle_calib / tools/cw 全部 proofs 与 ab_judge——comp-structure-unification transition-library.md「保留边界」明列）。
- 依赖：详设一（终局条目删 or_reqs）+ 详设二（过渡条目库替换，旧「希儿引擎」条目退役）先行——本篇是最后消费者移除后的机器删除（总纲契约 C 顺序锁）。

## 方案

### 退役符号集中清单（grep 清零的唯一依据；逐符号，禁字符串盲 grep）

| # | 符号 | 宿主 | 处置 |
|---|---|---|---|
| 1 | `Comp.or_reqs` 字段 + docstring | kernel/cw_comps.py | 字段删除 |
| 2 | form_progress 的 OR 折法段（虚拟分支/组内 max/or_reqs 循环）+ `getattr(comp, 'or_reqs', ...)` 防御读 + 「承接规则」注释块 | kernel/cw_comps.py `form_progress` | 删除——函数收敛为「档 0 均值 + required 逐名折条」两段；docstring 单一源契约改为「fp=1.0 ⟺ 档 0 全档 ∧ required 全在板」 |
| 3 | 建库校验③（`_or_keys` / `_stray` / or_reqs ⊆ 档 0 检查） | kernel/cw_comps.py `Comp.__post_init__` | 删除（字段消亡）；校验①②④⑤保留 |
| 4 | `SEELE_OR_REQS` / `SEELE_CARRY_CHAR` 常量 + 注释块（「同步回改第三表面」历史警告已随配方层退役，删前核对无残留引用） | kernel/cw_comps.py | 删除 |
| 5 | `_line_form_tier_groups` 的 OR 组折叠段（or_keys 分支）/ `_or_group_target` / `_or_keys_of` 三函数 | strategies/impl/mandate_v1/deploy_search.py | 删除——`_line_form_tier_groups` 收敛为「档 0 每键一组」；调用点（L1 评分键组）零改动跟随 |
| 6 | `_SEELE_SYSTEM_KEY` / `_seele_formed` / `_SEELE_ACTIVATION_PIECES` + L1 评分的三处希儿系专属分支（k == '希儿系' 的计分支 / 无键板面成型加分支 / 第二处分支） | strategies/impl/mandate_v1/deploy_search.py | 删除——过渡部署圈人统一走条目档 0 键组（量子同频/贝洛伯格是普通羁绊族键，`_line_form_tier_groups` 现成机器；过渡条目已换组合条目，希儿量2/希儿贝2 组合的圈人 = 量子/贝羁绊成员 ∪ 点名希儿，AND 语义现成） |
| 7 | `SEELE_SYSTEM: str = '希儿系'` 常量 + `bond == SEELE_SYSTEM` 分支 | knowledge/cw_line_facts.py | **保留不动**——独立观测消费在案：telemetry/schema.py:20/37 import 进 `RHO_SYSTEM_KEYS`（ρ 实测观测面的第四体系键，rho_shop_obs 每帧消费），不在本迭代删除面；就地补一行注释声明该消费引用点（防将来误判孤儿） |
| 8 | `or_reqs` 在 TRANSITION_LIBRARY 旧条目「希儿引擎」的引用 | kernel/cw_comps.py | 随详设二条目替换自然消失，本篇核对 |
| 9 | 测试镜像：test_cw_comps / test_deploy_search / test_cw_intention / test_line_select 中 or_reqs / SEELE_OR_REQS / 希儿系伪键断言 | sr-od-test/ | 同步删改；`form_progress` 的 OR 折法测试（虚拟分支 max 语义、承接免账）随机器删除 |

### form_progress 收敛后的形态（实现者照抄）

```python
def form_progress(comp: Comp, gs: GameState) -> float:
    """成型度 0..1：档 0 各羁绊进度均值 + required 逐名 0/1 折条的均值。
    单一源契约：fp = 1.0 ⟺ 档 0 全键达标 ∧ required_deployed 全在板。档 1 不进（加分层归
    部署次层/采购面）。档 0 空（非羁绊成型阵容，如反甲白厄）→ fp 恒 0（装备流走轮数兜底）。"""
    core = comp.core_faction_reqs
    required = comp.required_deployed
    if not core and not required:
        return 0.0
    # 档 0 均值 + required 逐名折条（在板=1；无 deployed 视图按 0 计保守向）
    # ——两段逻辑与现行实现逐行一致，仅删 OR 段；板面读法 gs.board.value 鸭型读不变
```

### 行为核对（删除面零残留的判据）

- 全库 `or_reqs` 符号 grep 清零（含测试仓；前置 = 详设二已移除旧「希儿引擎」条目）；
- `SEELE_OR_REQS|SEELE_CARRY_CHAR|_SEELE_SYSTEM_KEY|_seele_formed|_or_group_target|_or_keys_of` grep 清零——注意 `_SEELE_SYSTEM_KEY`（deploy_search 私有副本）在清零域，`SEELE_SYSTEM`（cw_line_facts 公开常量，telemetry RHO_SYSTEM_KEYS 消费）**不在**清零域，`seele_system_formed`/`SEELE_AMP_FACTIONS` 同不在（契约 D 保留面）；
- 非希儿线行为逐位恒等：20 条终局线 + 过渡组合条目的 form_progress / 部署评分与详设一、二落地后基线一致（迁移恒等测试承载）。

## 关键取舍

- **放弃「保留 or_reqs 字段、仅清消费」的保守方案**：全库最后消费者随详设一/二移除，字段留存 = 死字段 + 死机器的维护病（先例：level_plan 消费面被取代后整块死数据）；字段准入判据 1（消费先行）反向适用——无消费即退役。
- **kernel 谓词族保留而非同批统一**：结算键 rung / 胜率模型 / A-B 工具消费的是「四体系引擎计数」观测语言，与 Comp 决策表示解耦（3.3 保留边界）；同批重写 = 切断结算与判据工具链，且观测判据「任一即成」在结算语境自洽——两侧口径差异就地注释声明即可。
