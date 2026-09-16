# 链观察落地 落地

> 通用工程门（各阶段判据引用项，此处单一定义）：`uv run ruff check` 改动文件全过；直接受影响测试 + L1（`$env:PYTHONPATH='src'; uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow" -q`）一次通过；`git add` 逐文件点名；提交后 `git show --stat` 复核入库面 = 申报面。（源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节）

## 3.1 载体升级批（TokenCell/NodeChain + 字段 + schema + 读口适配）
**范围**：kernel/cw_game_state.py 新增 `TokenCell`/`NodeChain` 数据类（链正本 §2 形状：`NodeChain{plane:int, seq:list[TokenCell]}`、`TokenCell{token:str|None, channel:str, hu_dist:float|None}`，channel 封闭集 {hu,label,sift,none,dim}）；`node_path` 字段值形 `Field[list[str]]` → `Field[NodeChain | None]`；新增 `node_path_baseline: Field[NodeChain | None]`；node schema 域升版（值形变化，按 fields.md §3.7 机制，升版注记列两字段）；`chain_node_type` 读口适配（解 `NodeChain.seq`/逐格 token、plane 不匹配 → None，签名与零内建回落语义不变）。**不含**任何写端与派生消费接线；journal 旧档 list[str] 行只读保留（跨版本判读边界申报：现无判读面消费 node_path 域）。
**设计依据**：design.md §2.1-1；链正本 §2/§6
**文件面**：`kernel/cw_game_state.py`（载体+字段+schema 域版本+读口适配）、`sr-od-test` 对应测试
**依赖**：无
**优先级建议**：8
**完成判据**：
- 两字段读写/缺省 None/整帧替换语义单测；`chain_node_type` 对 NodeChain 载体的命中/越界/位面不匹配/未辨四态单测
- schema 域版本断言更新随批
- 全仓 `node_path` 旧值形构造/消费点 grep：仅剩读口适配一处（现役仅 chain_node_type 消费，已核）
- 通用工程门（本文首节定义）
**验收凭据形式**：测试名清单 + ruff 干净

## 3.2 备战帧现行链写端（prep_row，挂点 = 入口 heavy 行读升格）
**范围**：备战入口 heavy 观察的节点行读点（`cw_observe_full` heavy 链，现读后弃槽处）升格：slots 构造 `NodeChain` 经 `bs.observe(node_path, ...)` 写入（evidence='prep_row'）。逐格映射：past→dim/None；current→**左移推断**（复用现役 anchor 机制语义：上一帧该位 upcoming 的 Hu 读数即本轮，channel='hu'；anchor 不可用→OCR 标签兜底 channel='label'，fields.md §3.2.1 帧标签仅 battle/boss 稳定的采信约束随迁）；upcoming→hu/Hu；hu 超阈→none/None；boss 末槽→sift。写门 = 轮位对齐门（现役语义随迁）；**变异窗不对链写设门**（design §2.1-2）。基线回填：位面内首个 clean 链写（基线为空时）同写 `node_path_baseline`（evidence='prep_row_first'，P2/P3 基线承接）。变异窗关闭点迁移：轮位对齐 clean 链读成功即关 `env_grace_until`（与链写执行脱钩）。**不含**关店探针改动（`_probe_node_type` 各职责现状不动）、session 写点③改动（冻结条款）。
**设计依据**：design.md §2.1-2/6；链正本 §3/§5
**文件面**：`operations/cw_screen/cw_screen_prep.py`（入口 heavy 链读点邻域）、`obs/cw_node_reader.py`（如需升格辅助）、`obs/cw_observe_full.py`（行读点改造）、`operations/cw_screen/cw_screen_invest_env.py`（仅关窗点迁出如涉）、`kernel/cw_game_state.py`（如门/锚接口需 kernel 化）、`sr-od-test` 对应测试
**依赖**：3.1
**优先级建议**：8
**完成判据**：
- 单测：clean 备战帧 → node_path 整帧覆盖（dim/label/hu/none/sift 五通道各一例 + current 左移推断值一例、anchor 缺失 OCR 兜底一例）；轮位错位帧拒写；窗内照写（新语义）且窗被本读关闭；链读失败字段保持未写不阻塞
- journal 写入行断言（obs 渠道、行含 NodeChain 快照）；基线回填（空则写/非空不覆）单测
- **生产时序四②命中（harness 剧本）**：按真实帧序演「round N-1 入口链写 → round N 开店（弹窗腿）→ 查询 chain[N] 命中 Hu token」——防「单测手工构造可绿、生产恒 None」（对抗 F1-3）
- 两路径触达断言：旧 run() 与五段 lifecycle 的入口观察均触发链写（F6）
- 通用工程门（本文首节定义）
**验收凭据形式**：测试名清单 + 现役 fixture 帧离线判读样例

## 3.3 过渡屏观察段（基线链 + 离场快照）
**范围**：`CwScreenPlaneTransition._click_blank`（两路径共享点击执行体，cw_screen_plane_transition.py:107-121）点击前读节点行（`read_node_sequence` 同源）写两笔：容器节点镜像三源全缺（kernel 过渡腿先例语义，cw_game_state.py:3383-3391）判开局 → `node_path_baseline`（evidence='transition_row'，行位面=1）；每次过渡屏 → `node_path` 离场快照（evidence='transition_snapshot'，行位面 = 非开局取节点镜像 plane、镜像缺失跳写诚实缺位）。接管局残余风险按 design §2.1-3 申报（镜像全缺 ⟺ 游戏最开端，污染形态 = 极端崩溃恢复，接受）。**不含**位面详情采集通道改动（冻结）。
**设计依据**：design.md §2.1-3；链正本 §3
**文件面**：`operations/cw_screen/cw_screen_plane_transition.py`、`sr-od-test` 对应测试
**依赖**：3.1
**优先级建议**：7
**完成判据**：
- 单测：开局屏（镜像全缺）→ 基线落 + 现行链快照落；1→2 屏（镜像有值）→ 基线不动 + 前位面离场快照落；镜像缺失跳写；行读失败不阻塞点击继续
- fixture 离线判读：`sr-od-test/screens/货币战争-位面过渡/plane_1to2.webp` 行九槽类型与 plane_schedule_observed.md P1 地面真值一致
- 两路径触达断言：旧路径与 lifecycle 均经 `_click_blank` 触发观察段（F6）
- 实拍补档义务（实机窗口依赖，候 3.3 实机验证期一并）：开局过渡屏与 2→3 过渡屏各采一帧 fixture 归档（现仅 plane_1to2 一张，F11）
- 通用工程门（本文首节定义）
**验收凭据形式**：测试名清单 + fixture 判读对照

## 3.4 diff 证据接线
**范围**：kernel 纯函数 `chain_diff(baseline, current)`（链正本 §4 全规则：rewrite 位集/通道受限差单列/长度差/首差位/基线覆盖位集）+ `OBS_EVENT_EVENTS` 扩词 `chain_diff`（现值 (arbitrate, miss, popup)，cw_game_state.py:262）+ 触发纪律（基线在场 ∧ 连续两 clean 备战帧一致才记；离场快照单帧即记；变异窗豁免）。触发状态载体零真实副作用（可注入回调，缺省不落账）。
**设计依据**：design.md §2.1-4；链正本 §4/§5
**文件面**：`kernel/cw_game_state.py`（纯函数+触发状态载体）、`sr-od-test` 对应测试
**依赖**：3.2、3.3
**优先级建议**：6
**完成判据**：
- 单测：rewrite 位集（含通道受限差不入改写）/长度差（插节点）/两帧确认门/离场豁免/变异窗豁免各一例
- 通用工程门（本文首节定义）
**验收凭据形式**：测试名清单

## 3.5 消费接线 + 删违例写点
**范围**：派生管线类型派生步的**商店面板块触发面**（屏名 ∈ 商店面板块「货币战争-备战-开商店」；plane/round 取值 = 刚推进的 hist 反解，仿 cw_game_state.py:3383-3391 三源序）调 `chain_node_type`——token 非 None → `_write_derived_node_type`（actor=派生规则四②）；None 维持零写。非商店画面零查链零写。**随后删**：商店回填写端（cw_screen_buy_cards.py:951-973 整段）、投资环境写点②（cw_screen_invest_env.py:444-484 `_refresh_node_ledger` 调用与方法体；开窗点 :432 保留）。session 台账在役消费点（`read_game_state` 查表优先主值 cw_observation.py:2245-2246、装备 O1 门 cw_equip_wear_plan.py:258-275、三票校验）与写点①③**全部保留在册**（冻结条款，对抗 F2/F12）。
**设计依据**：design.md §2.1-5/7；链正本 §6
**文件面**：`kernel/cw_game_state.py`（类型派生步）、`operations/cw_screen/cw_screen_buy_cards.py`、`operations/cw_screen/cw_screen_invest_env.py`、`sr-od-test` 对应测试
**依赖**：3.2、3.3、3.4
**优先级建议**：8
**完成判据**：
- 单测：商店弹窗腿进店（链在位）→ node.kind=查链直定值 → 店决策 `node_kind_of` 读到正确类型；链缺位 → 维持零写；非商店画面零查链（F9）
- 删除面 grep：`node_ledger_backfill`/`_refresh_node_ledger` 零残留
- 台账在役消费点在册断言（三处 + 写点①③，防误删，对抗 F2）
- 既有 ADR-0587 回归锁仍绿（店决策不再读滞后节点）
- 通用工程门（本文首节定义）
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
- `game_state/fields.md`：§3.1.5（开局初值写端：过渡屏 transition_row 为先、位面详情降回退）与 §3.2.2（写端在役形态、载体 NodeChain、baseline 字段）← 3.1/3.2/3.3
- `game_state/chain-observation.md`：§3 写门条款修订（现行链写门由「轮位对齐门∧非变异窗」改为「轮位对齐门」,变异窗豁免语义由 design.md §2.3-7 承接）+ §3 quality 值域两义注并轨定谳（prep_row/row_read 择一固化,B-3 接线批职责归本迭代 3.4）+ §5 遥测挂接表述核对 + §7 sim 条款修订（合成口写链裁剪为不写,取舍 = design.md §2.3-5）← 3.1/3.2/3.4
- `game_state/node-domain.md`：§5/§7 类型派生四②「商店查现行链」接线在册 ← 3.5
- `game_state/node-derivation.md`：派生规则四②接线注记（若该文承载派生规则在册面，落地时核实）← 3.5
- `game_state/retirement.md`：§5 遥测排期面与 chain_diff 词登记状态核对（对抗 F8 路径修正：实际路径在 game_state/ 下）← 3.4
- `kernel/cw_game_state.py` 模块头节点域段（node_path/baseline 两字段与管线段序表述）← 3.1
