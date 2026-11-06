# 统一让位优先级 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`，约 2.5min）；测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 红测逐条判断：代码错 → 修代码；测试过时 → 更新期望并说明依据；禁不加判断改期望值；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面；
- **改 Python 代码后重启项目 MCP server 才生效**（AGENTS §6；重启前查运行状态，运行中先 stop）；
- 行为申报核对：每阶段交付对照 design §2.7 行为申报集（无条件刷/K 源切换/P1 锁定配方退出/万金油退出义务买入面/无池子/黑塔统一/溢出安置部署补位/不设仅一星过滤）确认实现与申报一致。

### 3.1 优先级判据件与部署接口落地
**范围**：新建 `criteria/priority.py`（PriorityContext 装配体/sort_key/sell_order，八档判定+档内键+在手旗标+随机尾键）；部署选人核心抽取为纯函数 `select_deployment(frame, prep)`（结构抽取，判据零改动，PrepContext 字段面按实际读面冻结）。
**设计依据**：details/priority-model.md 全篇 + details/acquisition-and-sell.md §1
**文件面**：`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/priority.py`（新）、`entry.py`、`mandate.py`、`session_scope.py`（如需读口暴露）、`kernel/cw_intention.py`（只读消费，不改判据）
**依赖**：无
**优先级建议**：0
**完成判据**：
- 八档判定谓词逐档与 priority-model §2 表一致（数据源单一源逐项对齐）；
- 档内键与 §3 表一致（含档 2 三键/档 6/7 总星级数第一键/档 8 概率+稳定序）；
- 在手旗标与随机尾键（StrategySession.rng）按 §4；
- `select_deployment` 纯函数抽取后现行部署测试全过（行为不变守卫）；
- 完成前常规检查（本节首）。
**验收凭据形式**：新判据件单帧测试（八档判定/档内键/在手旗标断言）+ 现行部署测试回归绿。

### 3.2 获取角色流程与场景判据件改造
**范围**：席满买入六步流程替换置换账（shop.py）；场景注册表（SCENE_SPECS）重写为统一序列消费（五场景参数表）；溢出安置 = 部署补位承载（无特殊规则）；补给选角色改虚拟全局评估形态；免费刷新分支改无条件刷（外层记忆闸照旧）。
**设计依据**：details/acquisition-and-sell.md §2/§3/§3.1/§6 + design §2.2/§2.3/§2.4
**文件面**：`shop.py`、`criteria/sell_candidates.py`、`criteria/sell.py`、`supply.py`、`entry.py`
**依赖**：3.1
**优先级建议**：1
**完成判据**：
- 六步流程与 acquisition §2 逐条一致（含升星模拟/部署重算/末位让路/拒绝语义）；
- 五场景与 §3 表一致（跨档止盈/同轮禁卖保留，身份过滤删除）；
- 免费刷无条件刷 + 记忆外层闸照旧（design §2.2）；
- 补给虚拟全局评估与 §3.1 一致；
- 完成前常规检查（本节首）。
**验收凭据形式**：席满帧断言（绯英置换成功/末位=新牌放弃）+ 各触发场景测试 + 免费刷行为测试。

### 3.3 阵容内优先级字段迁移
**范围**：阵容知识卡增成员优先级字段（迁移期 = core→高/其余→低两档映射）；消费面接入档 2/3/5 档内排序；跨线取最高/配方成员低优先级/无表项 need_star=1 规则落地。
**设计依据**：design §2.1.1 + priority-model §2/§3
**文件面**：`kernel/cw_comps.py`、`criteria/priority.py`、消费位
**依赖**：3.1
**优先级建议**：2
**完成判据**：
- 两档映射与 §2.1.1 迁移期形态一致；
- 取值规则（跨线最高/配方低档/无表项=1）与 priority-model §2/§3 一致；
- 完成前常规检查（本节首）。
**验收凭据形式**：迁移映射测试 + 档内排序断言。

### 3.4 旧判据拆除
**范围**：按 dismantle §1-§4 执行——刷新预测门、单卡核心囤积规则（含 contracts 死件/场景死行）、静态不许卖名单卖侧+买侧（囤货臂/宽集收窄/序 4 prio1 腿/枢纽消费位/hub 死链/甲臂兜底/K 源切换）、旧价值函数退役；保留项（循环防线/物理谓词/万金油常量/概率退金表）不动。**3.2 验收登记的遗留分期项并入本阶段**：①付费腿 `refresh_warranted` 内 target_buyable 合取删除（免费腿已先行切无条件刷）；②万金油义务买入面退役（shop.py:916 CROSS_LINE 项，随 K 源切换重建——design §2.7 申报②生效点）；③K 空窗回退集退役（甲臂兜底，dismantle §3 买侧段）；④bench_full 拦因写端退役残余清理；⑤卖面身份段收缩（sell_gate 保护集/义务基座照读态拆除）；⑥criteria/sell.py 两处 bench_effect 消费随场景退役（若 3.2 未尽）。
**设计依据**：details/dismantle.md §1-§4 + design §2.5
**文件面**：`criteria/refresh.py`、`criteria/sell_candidates.py`、`criteria/sell.py`、`shop.py`、`sell_gate.py`、`mandate.py`、`protection.py`、`kernel/cw_intention.py`、`criteria/contracts.py`、`entry.py`
**依赖**：3.1、3.2
**优先级建议**：3
**完成判据**：
- 拆除对象逐项零残留（dismantle §1-§4 代码面逐行对账）；
- 保留项逐项在位（§4 表）；
- 甲分支定理 A 处置核对项落地（判据死则证明随迁）；
- 拆除后跑 L1 全过 + 语义反查（「一星」「甲臂」「枢纽」触达面口径统一）；
- 完成前常规检查（本节首）。
**验收凭据形式**：grep 零残留对照表 + L1 全量绿 + 反查记录。

### 3.5 遥测键切换与观测键新增
**范围**：删除键（target_unbuyable/core_* 族/身份保护键族）、保留键核对（memory_skip/fuel_victim_protect_demoted）、新增键（置换成功拒绝/档位分布/随机尾键命中）；schema 同步。
**设计依据**：details/dismantle.md 各遥测键面 + details/acquisition-and-sell.md §6
**文件面**：`shop.py`、`telemetry/schema.py`、各写点位
**依赖**：3.2、3.4
**优先级建议**：4
**完成判据**：
- 删除/保留键与 dismantle 键面逐项一致；
- 新增键按 §6 登记键表；
- schema 字段与写点一致；
- 完成前常规检查（本节首）。
**验收凭据形式**：键表对照 + schema 测试。

### 3.6 全量验证与实机冒烟
**范围**：L3 全量（`uv run pytest sr-od-test/ -m "not slow"`）；单帧断言集（三条核心断言，手工 GameState fixture）；实机冒烟（连跑数局核三项判据：升星目标在店必置换成功/金滞留超利息线帧数显著下降/无单卡核心囤积买入）；与 sim-flow-fidelity 顺序依赖遵守（其批 A 合入前禁 sim 重放类验证）。
**设计依据**：design §2.10
**文件面**：测试仓断言集
**依赖**：3.1-3.5
**优先级建议**：5
**完成判据**：
- L3 全量绿；
- 三条单帧断言全过；
- 实机三项判据核验记录；
- 完成前常规检查（本节首）。
**验收凭据形式**：L3 输出 + 单帧断言输出 + 实机局判读记录。

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条更新正本文档，与代码实现对齐。
**设计依据**：本文件「正本更新清单」节 + details/dismantle.md 各文档面
**文件面**：清单所列正本文档
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- 11 号稿（strategy-docs/11_shop_decisions.md）：§1 单卡核心支整节删/六序收敛、§3 目标可买三腿并集整节删/免费腿无条件刷、§4.0 场景表（C1 行/置换账→六步流程/筹资仅一星过滤删）、§4.1 卖出资格仲裁（P78 身份段/P78-5）——← 3.2/3.4
- 12 号稿（12_line_and_intention.md）：§1.2 囤积纪律（囤货面退役）、§4 hub 数据面表述——← 3.4
- 30 号稿（30_supply_screen.md）：三级字典序中间级改统一序列——← 3.2
- 01 号稿（01_math_framework.md）：判据组件行与组件表（:84/:86/:147 三腿引用）——← 3.4
- 20 号稿（20_*.md）:66 刷新行、23 号稿 §1——← 3.4
- 24 号稿（24_*.md）：部署选人核心抽取的结构变化（判据零改动声明）——← 3.1
- protection 相关 design 篇：退役标记（引用寿命处理）——← 3.4
- math_proofs.md：P86 索引行乙臂退役注记、甲臂定理 A 处置——← 3.4
- proofs/p86-proof-batch.md：乙分支证明章删除、甲分支定理 A 处置——← 3.4
- proofs/p86-no-target-period-fund-allocation.md：乙分支节退役标记——← 3.4
- docs/game/currency_war/research/stage_transitions.md：策略层消费点节（若引用面变化）——← 3.4
- strategy-docs/README.md：分篇入口变化汇总——← 末阶段
