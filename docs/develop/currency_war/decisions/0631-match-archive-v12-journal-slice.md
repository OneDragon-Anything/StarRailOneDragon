# ADR-0631: match_archive 装配器 v12——统一 state 新账切片+相对路径物化+旧档案自动重装配补键

- 日期:2026-09-11
- 状态:已实施(R3-1 消费方迁移批入库 commit `f55631c84`;本条 = R3-1 落地审 F6「v12 bump 无 ADR」补档,记账 T-228)
- 关联:ADR-0630(统一 state 状态流水,两文件模型)、ADR-0615(v11 先例:装配端纯读列+auto-rebuild 兼容路径)、ADR-0605(v10 先例)、`src/sr_od/application/currency_war/telemetry/match_archive.py`(装配器本体,SCHEMA_VERSION/_SLICE_FILES/materialize_slice/load_archive)、`src/sr_od/application/currency_war/telemetry/journal_query.py`(新账读面)、`src/sr_od/application/currency_war/telemetry/cli.py`(--source 路由)

## 背景

统一 state 消费方迁移批 R3-1(离线判读工具族接统一 state 新账)把档案装配器 `SCHEMA_VERSION` 11→12,当时未随批立 ADR——版本先例链 v10(ADR-0605)/v11(ADR-0615)在 v12 断档,R3-1 落地审 F6 记账归 T-228 补档。v12 的装配面变化有三,本文记录其 why。

## 决策

1. **切片 ``state/journal.jsonl``**(加法切片):统一 state 新账进 `_SLICE_FILES`,按 run_id 过滤(新账行行自带 run_id,与既有流同一过滤口径)。写端(kernel/cw_state_journal)影子开关缺省关 → 产物目录无该文件是常态:**文件缺席 = 空切片,判读区分「未开」与「无行」**,不判「丢数据」。
2. **物化相对路径还原**:`materialize_slice` 按切片键同名相对路径落盘(v12 起 ``state/journal.jsonl`` 带子目录,父目录自动建)——`--match` 档案切片物化到临时 replay 目录后,新账读面(telemetry/journal_query)读同一相对位置;`--match` 与 `--run` 因此走同一套 query 实现(单一源),输出一致。
3. **旧档案重装配补键**:`load_archive` 版本检查(stale = schema_version < 12)默认就地重装配一次;水位线推进对欠版本档案同样自愈一次——直读 JSON 的离线消费端(判读脚本)不会吃到缺 v12 切片的档案。加法面,旧 12 流切片零触碰。

## Considered Options

- 设计清单第二文件(策略侧决策行)同批加切片——否决:该文件落地批未到,先加切片 = 空引用;候其落地批再加。
- 文件缺席按异常/告警——否决:影子期开关缺省关是合法常态,缺席 = 「未开」必须可判读,告警会污染影子期判读。
- 不 bump 版本、按文件存在性探测——否决:版本号是 load_archive 重装配的触发器;不 bump 则存量档案永不补键,判读端面分裂。

## 后果

- 档案消费端单入口:新账读面只有「live 全账(--run)/档案切片(--match 物化)」两条喂入,同一实现;CLI `--source {old,journal}` 显式配对校验(配错 = 拒绝),缺省 old 现状不变。
- 验证:`test_cw_state_journal_reader.py` 19 锁(自足行 roundtrip/宽容缺字段坏行/档案 v12 切片按 run 过滤+物化还原+v11 旧档案自动重装配补键/CLI 视图族+配对拒绝+缺省旧路径零变化);L1 3199 passed、L3 3725 passed 亲跑在案(reviews/统一state-R3.1-落地审.md accept 条件记档)。
