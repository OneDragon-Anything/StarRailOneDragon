# 0344 - Δ池语料管线治本(局终自动再生 + 池新鲜度检查)

- 状态: accepted
- 日期: 2026-08-26
- 关联: ADR-0242(池快照化)/0268(防饥饿)/0306(扩容与桶覆盖)/0342(恢复早停)

## 背景与问题

2026-08-25 晚查实:Δ池快照(`cw_delta_pool_data.py`)停在当天凌晨(41 局),
下午 4 个实机局的语料全部没进池——sim 的 encounter/boss 结算样本零胜例,
P1 后段被钉死全败,期间所有策略批「sim 全绿 → 实机照溃」。管线断 12 小时
**无任何报警**(没有任何新鲜度检查项)。手工再生后新池 05d1a11f 已提交,
但触发方式仍是纯手工——同样的断线随时复发。

根因层定位:**流程层**(再生触发挂在"人想起来"上)+**可观测层缺失**
(没有断线报警)。修症状(再手工跑一次生成器)已在事故当时做过;本 ADR
是治本——再生随数据写入端走,断线有常设检查。

## 决策

1. **生成核心迁入 src**:tools/cw/gen_delta_pool_snapshot.py 的核心逻辑
   (build_pool/守卫/写快照)迁至
   `src/sr_od/application/currency_war/cw_delta_pool_gen.py`,新增可调用
   入口 `regenerate_snapshot()`(返回新池指纹;空池 raise)。tools 侧保留
   CLI 薄壳(argparse 不变)。「生成器是池的唯一入口」防线(写目标白名单 +
   源目录 ≠ sim_runs 防自中毒)随核心走——两条入口(局终钩子/CLI)共用
   同一守卫,不给回灌留第二条路。
2. **局终自动再生**:`cw_telemetry.record_run_summary`(正常局终)与
   `recover_dangling_run_summaries`(崩溃兜底回填)尾部调
   `_regenerate_delta_pool_after_run()`——**runs.jsonl 每新增一行即再生**。
   best-effort:再生失败只记 `[cw][pool-pipeline]` warning,绝不向局终收尾
   传播异常(遥测基建故障不许影响对局本体)。
3. **池新鲜度检查项** `check_pool_freshness`(cw_sim_checks):
   快照 `META.runs` 最新 run_id 距本机 `runs.jsonl` 最新 run 落后
   **≥2 局 = 违规**。双端挂:sim 批量 checks(snapshot/auto 池;
   fallback 不辖)+ 生产局终钩子再生后自检。本机无 replay(CI/裸
   checkout)跳过不辖(freshness 是本机管线属性,非池内容属性)。

### Considered Options

| 方案 | 结论 |
|---|---|
| A. 哨兵脚本定时再生(查 mtime → 重跑 CLI) | 否决——与实机进程外的哨兵栈又添一件;局中再生会收**半局语料**(outcomes 局中追加,池超前但不完整);服务器重启后哨兵失效面叠加 |
| B. 局终钩子再生(选中) | 数据写入端即触发点,语义精确("这局的语料齐了");进程内调用无 CLI 往返;崩溃路径由兜底回填触发点覆盖 |
| C. A+B 双保险 | 否决——B 已覆盖崩溃路径(兜底回填同样触发);双触发只添竞态(两进程同时写快照文件) |
| 阈值=2 局的依据 | 1 局容忍(再生挂局终后、下一局未结束前,lag=1 是管线健康的瞬态)+1 局缓冲;≥3 只能是钩子/手工链断了。更紧(=1)会在健康瞬态误报,更松(≥3)让断线多烧一局的 sim 结论 |
| 就地 import(函数内 from import) | 选中——避免 telemetry→gen→sim 的导入期环;钩子在局终执行,届时全链已加载 |

## 后果

- **快照文件随局终变脏**:`cw_delta_pool_data.py` 是 tracked 生成产物,
  局终自动再生后工作树出现未提交变更——**预期行为**,提交节奏仍走阶段
  commit(sim A/B 批记录自己跑时的池指纹,口径不变,别硬编码)。
- 服务器进程内已 import 的快照模块在再生后是旧值(`resolve_pool` 进程内
  缓存)——sim 批跑在独立 `uv run` 进程,读的是新文件;live 对局不消费
  snapshot 池,无实际影响(记录在此防误查)。
- 局中手工再生会产生"池超前于 runs.jsonl"的瞬态(池含在跑局的部分
  outcomes)——lag 口径只数晚于池最新的实机行,超前态判健康,符合意图。
- 崩溃恢复局的语料在**下一局 start_run 的兜底回填时**才入池(其
  runs.jsonl 行那时才写)——最坏滞后一局,阈值 2 容忍。

## 验证

- 单元/单帧锁:`test_cw_w109_pool_pipeline.py`(再生写守卫头注+META 覆盖/
  空池 raise/新鲜度三态[新鲜·滞后·无replay跳过]/钩子失败不阻塞/
  record_run_summary 接线)。
- ruff 全过;L1 快速集;commit 前全量。
- 不跑 sim 基线(run 10 在飞;新基线等局终后统一)。

## 实现

- `src/sr_od/application/currency_war/cw_delta_pool_gen.py`(新,核心迁入)
- `tools/cw/gen_delta_pool_snapshot.py`(改,CLI 薄壳)
- `src/sr_od/application/currency_war/cw_telemetry.py`(+`_regenerate_
  delta_pool_after_run` 钩子,两写端接线)
- `src/sr_od/application/currency_war/cw_sim_checks.py`(+`check_pool_
  freshness`/`POOL_FRESHNESS_LAG_LIMIT`)
- `src/sr_od/application/currency_war/cw_sim.py`(sim 批 checks 接线)
- `docs/develop/currency_war/strategy/README.md`(基建表行更新)
- 局终动作链新形态:判读 → **自动再生(无人工步)** → 下局

## 顺手治本(测试撞出的生成器既有坑)

原实现把 `json.dumps(meta)` 直接当 Python 字面量写进产物——JSON 的
`null`/`true`/`false` 不是合法 Python,池一旦出现 killed 全 None 的桶
(win_killed=None),产物 `.py` 即不可 import(= 再生管线自己写出毒池)。
W109 形态改为:JSON 串 `repr` 存储 + 导入时 `_json.loads`(消费符号
META/SNAPSHOT 与指纹校验不变;sort_keys 的 diff 稳定性不变;旧形态
产物在下次再生时自动切换)。测试 `test_regenerate_writes_guarded_
artifact` 即以 killed 全 None 的 fixture 锁死此坑。
