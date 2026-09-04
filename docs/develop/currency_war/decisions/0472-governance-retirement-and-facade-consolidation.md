# ADR-0472: 包治理退役批——零消费数据层删除与门面收敛

## 1. 背景与问题

货币战争包代码治理审计(逐符号消费面 grep:src + sr-od-test 全部 .py,模块 import 三形态 + 符号级正则)查出四类「数据/路径在、决策链不在」的退役面:

- **零消费数据层三件**:`cw_chars_data.py`(PLAZA_ROLES 75 条 plaza 官方条目)、`cw_factions_data.py`(TRAIT_TIERS 33 键 + TRAIT_ROLES 32 键)、`cw_power_table.py` + `cw_power_table_data.py`(战力表判断层+数据层,1432 行)。三者生产消费均为 **0**(唯一消费者是被删的测试文件/生成器本身)。且 chars/factions 两份数据是与手维护注册表(CHARACTERS/FACTIONS)同源同语义的重复维护点——「对拍基线」是口头的:全仓没有任何测试/守卫读两表比对,双份 tiers 漂移无人知晓。战力表的最后一条设计消费路径(桥线桶 check 调用)已随 ADR-0336 断,数据在、判断层在、决策链不在。
- **选桥函数簇无主**:`cw_bridge_pool.py` 的 `score_bridge`/`pick_bridge`/`_char_bond_hits`(约 70 行)生产消费 0——选桥决策路径已被 cw_intention/cw_line_defs 的 form_tiers 机制取代(ADR-0336 后);文件只剩池数据被消费(BRIDGE_POOL 三处活跃消费:intention/line_defs/sim_checks)。
- **obs 门面双路径**:`cw_observation.py` 门面 re-export 段(12 处旧路径消费,含 `area_center` 9 处)与直连 owner(cw_obs_core/cw_briefing_obs/cw_settlement_obs)双路径并存——同符号两条 import 路径是漂移温床。
- **investments 派生冗余**:ENV_FACTION/ENV_CATEGORY 中 42 条值可由名字后缀规则派生(「仙舟概念股」→「仙舟」),星徽套组/单件 21 对绑定元组逐对全等——第三份拷贝(「追击星徽套组(二)」)。

## 2. 决策

1. **删三个零消费数据层**:`cw_chars_data.py`、`cw_factions_data.py`、`cw_power_table.py` + `cw_power_table_data.py` 及对应死测试。**守卫替代决策**:chars/factions 的「口头对拍」升级为**对拍器接线守卫**——`tools/cw/gen_plaza_chars.py`、`tools/cw/gen_factions.py` 从生成器(写 src 数据文件)改为对拍器(stdout 逐条报 diff,不一致非零退出,不再写任何 src 文件),配轻守卫测试(plaza 冻结条目抽样断言 cost/position/traits 与 CHARACTERS 全等;factions 侧断言 traits.tiers ≡ FACTIONS 逐键、官方成员 ≡ chars_by_faction 派生集合)。数据从「两份静默零守卫」收敛为「一份注册表 + 一个版本更新守卫」——比删除前更强,不是防线损失。
2. **bridge_pool 裁函数簇、留数据**:删选桥函数簇;保留 `BridgeCombo`/`BRIDGE_POOL`/`BRIDGE_POOL_P2`(三处活跃消费)。平局偏好语义(r253 P1 tie-break 偏 xianzhou_dot)在消费点(cw_intention form_tiers docstring)补退役注释,防语义静默消失后未来被无感知重造。
3. **obs 门面收敛**:12 处门面路径 import 改直连 owner 模块,删 cw_observation.py 的 noqa re-export 段——消费方一律直连 owner,本模块不再 re-export。
4. **investments 派生化**:ENV_CATEGORY/ENV_FACTION 改「例外表 + 名字派生」(例外条手写带用户确认注,其余后缀规则生成);星徽套组条由单件条派生(绑定元组逐位共享同一对象)。**构建期逐位断言**:派生结果 ≡ 改前原表全量快照(ENV_CATEGORY 83 键 / ENV_FACTION 43 键 / 套组 21 键逐位相等,对拍脚本 3/3 GREEN)+ 永久测试锁(套组≡单件同一对象,禁套组条目回潮手写)——表内容逐位不变,行为零变化是硬约束。

同批文档裁决:退役前人读快照 `docs/develop/currency_war/power_table_meta.md`(103 行)一并删除——出处留 git 历史,本 ADR 记退役决策。

## 3. 被否决的替代方案

- **保留 chars_data/factions_data 作「机读对拍快照」**:零消费 = 运行时与测试中均无功能;守卫需要的是「对拍」这个动作,不是第二份数据。生成器可随时从上游(plaza API/traits.json)重放,无不可逆损失。
- **保留选桥函数簇「以备复接」**:零生产消费 + 消费点注释已记录退役语义;需要同等偏好时按注释另行设计,留无主函数只会误导读者以为决策路径还在。
- **investments 保留平铺表、只加一致性测试**:平铺表 + 测试 = 每次加条目要改两处(表 + 期望),派生 + 构建期断言 = 只改例外表,断言当场炸;派生方案把「一致性」从事后检查变为构造保证。

## 4. Consequences

- 退役件(cw_chars_data/cw_factions_data/cw_power_table 全家、选桥函数簇、power_table_meta.md 快照)如需考古走 **git 历史**;战力表调研若要复活,动作 = revert 对应 commit + 重跑生成器。
- **对拍器成为数据一致性的单一守卫面**:版本更新重采时,「官方数据 vs 注册表」的一致性由 gen_plaza_chars/gen_factions 的 stdout 对拍 + 抽样守卫测试承载,不再依赖人目视 diff。
- obs 层单一路径:符号 → owner 模块一一对应,re-export 温床消除;observation 命名混淆的根治归分包归桶(另行安排)。
- 全部删除/改写以「生产消费 0」与「逐位相等」为前提,实机与 sim 行为零变化。
- 遗留:`tools/cw/gen_power_table.py` 因产物删除成孤儿,处置(改对拍器或整删)挂账分包期;个别文档中「数据层」旧提法按对拍器口径另行同步。

## 5. 验证

- 删除零消费复核:开工/执行两轮 grep(`cw_chars_data|cw_factions_data|PLAZA_ROLES|TRAIT_TIERS|TRAIT_ROLES|cw_power_table`,src+sr-od-test+tools+docs 全树)命中仅生成器与注册表注释(均已改写)。
- 两对拍器实跑均「一致」exit 0(含首跑真咬出 1 条 diff——8007 开拓者·记忆共享壳例外,补 CHECK_EXCEPTIONS 后归零)。
- investments 逐位对拍断言 3/3 GREEN;`test_megastar_set_binding_derived_from_single` 永久锁 + 既有 test_cw_investments 22 条原值锁全绿。
- L1(cw_quick)绿;L3 全量 3548 passed / 0 failed 复核绿;ruff 改动文件全过。
