# 链观察落地 落地

## 3.1 载体升级批（TokenCell/NodeChain + 字段 + schema）
**范围**：kernel/cw_game_state.py 新增 `TokenCell`/`NodeChain` 数据类（链正本 §2 形状：`NodeChain{plane:int, seq:list[TokenCell]}`、`TokenCell{token:str|None, channel:str, hu_dist:float|None}`，channel 封闭集 {hu,label,sift,none,dim}）；`node_path` 字段值形 `Field[list[str]]` → `Field[NodeChain | None]`；新增 `node_path_baseline: Field[NodeChain | None]`；node schema 域升版（值形变化，升版注记列两字段）。**不含**任何写端与消费接线。
**设计依据**：design.md §2.1-1；链正本 §2
**文件面**：`kernel/cw_game_state.py`（字段区+载体定义+schema 域版本）、`sr-od-test` 对应测试
**依赖**：无
**优先级建议**：8
**完成判据**：
- 两字段读写/缺省 None/整帧替换语义单测；schema 域版本断言更新随批
- 全仓 node_path 旧值形消费点 grep 零残留（现役仅 chain_node_type 读口，已核）
- L1 全绿；§12 通用工程门（引用，不复述）
**验收凭据形式**：测试名清单 + ruff 干净

## 3.2 备战帧现行链写端（prep_row）
**范围**：备战入口 heavy 观察的节点行读数升格 TokenCell（state 映射：past→dim/None、current→label/OCR、upcoming→hu/Hu、hu 超阈→none/None、boss 末槽→sift）+ `bs.observe(node_path, NodeChain(...))` 写入（evidence='prep_row'）；两门随迁（轮位对齐门 cw_screen_prep.py:3195-3204、变异窗门 :3208）；变异窗关闭点迁移（链写成功即关 `env_grace_until`）。session 写点③按冻结条款保留不动。
**设计依据**：design.md §2.1-2/6；链正本 §3/§5
**文件面**：`operations/cw_screen/cw_screen_prep.py`（heavy 观察链读点邻域）、`obs/cw_node_reader.py`（如需升格辅助）、`kernel/cw_game_state.py`（如门随迁需接口）、`sr-od-test` 对应测试
**依赖**：3.1
**优先级建议**：8
**完成判据**：
- 单测：clean 备战帧 → node_path 整帧覆盖（dim/label/hu/none/sift 五通道各一例）；轮位错位帧拒写；变异窗内拒写且不关窗；链读失败字段保持未写不阻塞
- journal 写入行断言（obs 渠道、行含 NodeChain 快照）
- L1 全绿；§12 通用工程门
**验收凭据形式**：测试名清单 + 现役 fixture 帧离线判读样例

## 3.3 过渡屏观察段（基线链 + 离场快照）
**范围**：`CwScreenPlaneTransition` 观察段在「点击空白处继续」前读节点行（`read_node_sequence` 同源）写两笔：P1 开局屏（0q 首现）→ `node_path_baseline`（evidence='transition_row'）；每次过渡屏 → `node_path` 离场快照（evidence='transition_snapshot'，行位面=刚离开位面，判定 = 到达位面-1 下限 1）。行归属判定按设计 §2.1-3（球高亮不作判据）；整行全亮无轮位门。**不含**位面详情采集通道改动（冻结）。
**设计依据**：design.md §2.1-3；链正本 §3（transition_row/transition_snapshot）
**文件面**：`operations/cw_screen/cw_screen_plane_transition.py`、`sr-od-test` 对应测试（fixture = `sr-od-test/screens/货币战争-位面过渡/plane_1to2.webp` 等）
**依赖**：3.1
**优先级建议**：7
**完成判据**：
- 单测：P1 开局屏 → 基线落 + 现行链快照落；1→2 屏 → 基线不动 + P1 离场快照落；行读失败不阻塞点击继续
- fixture 离线判读：plane_1to2 行九槽类型与 `plane_schedule_observed.md` P1 地面真值一致
- L1 全绿；§12 通用工程门
**验收凭据形式**：测试名清单 + fixture 判读对照

## 3.4 diff 证据接线
**范围**：kernel 纯函数 `chain_diff(baseline, current)`（链正本 §4 全规则：rewrite 位集/通道受限差/长度差/首差位/基线覆盖位集）+ `OBS_EVENT_EVENTS` 扩词 `chain_diff` + 触发纪律（基线在场 ∧ 连续两 clean 备战帧一致才记；离场快照单帧即记；变异窗豁免）。
**设计依据**：design.md §2.1-4；链正本 §4/§5
**文件面**：`kernel/cw_game_state.py`（纯函数+触发状态载体）、`sr-od-test` 对应测试
**依赖**：3.2、3.3
**优先级建议**：6
**完成判据**：
- 单测：rewrite 位集（含通道受限差不入改写）/长度差（插节点）/两帧确认门/离场豁免/变异窗豁免各一例
- 触发状态载体零真实副作用（可注入回调纪律，缺省不落任何账）
- L1 全绿；§12 通用工程门
**验收凭据形式**：测试名清单

## 3.5 消费接线 + 删违例写点
**范围**：派生管线类型派生步未定型分支接 `chain_node_type`（token 非 None → `_write_derived_node_type`，actor=派生规则四②；None 维持零写）；删商店回填写端（cw_screen_buy_cards.py 买后段查 session 表写容器 node 的整段）；删投资环境写点②（cw_screen_invest_env.py:444-484 `_refresh_node_ledger` 调用与方法体）。session 写点①③与三票校验保留（冻结条款）。
**设计依据**：design.md §2.1-5/7；链正本 §6
**文件面**：`kernel/cw_game_state.py`（类型派生步）、`operations/cw_screen/cw_screen_buy_cards.py`、`operations/cw_screen/cw_screen_invest_env.py`、`sr-od-test` 对应测试
**依赖**：3.2、3.3、3.4
**优先级建议**：8
**完成判据**：
- 单测：商店弹窗腿进店（链在位）→ node.kind=查链直定值 → 店决策 `node_kind_of` 读到正确类型；链缺位 → 维持零写（不猜语义）
- 删除面 grep：`node_ledger_backfill`/`_refresh_node_ledger` 零残留；`ledger_node_type` 生产零调用（函数保留申报）
- 既有 ADR-0587 回归锁仍绿（店决策不再读滞后节点）
- L1 全绿；§12 通用工程门
**验收凭据形式**：测试名清单 + grep 输出

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1-3.5 全部
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单
- `game_state/fields.md`：§3.1.5（开局初值写端：位面详情 → 过渡屏 transition_row 为先、位面详情降回退）与 §3.2.2（写端在役形态、载体 NodeChain、baseline 字段）← 3.1/3.2/3.3
- `game_state/chain-observation.md`：§3 quality 值域两义注并轨定谳（prep_row/row_read 择一固化）+ 消费接线在册表述核对 ← 3.2/3.5
- `game_state/node-domain.md`：§5/§7 类型派生四②「商店查现行链」接线在册 ← 3.5
- `docs/develop/sr_od/application/currency_war/game_state/node-derivation.md`：派生规则四②接线注记（若该文承载派生规则在册面）← 3.5
- `telemetry/retirement.md` §5（若词登记状态需同步 chain_diff 词接线）← 3.4
- `kernel/cw_game_state.py` 模块头节点域段（node_path/baseline 两字段与管线段序表述）← 3.1
