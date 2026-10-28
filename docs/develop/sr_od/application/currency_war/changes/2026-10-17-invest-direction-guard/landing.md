# 投资选卡阵容冲突护栏 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关子集;跨阶段收口跑 CW 全量);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面;
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 kernel 指向集推导函数

**范围**:新增 `env_faction_scope` / `strategy_faction_scope` 两个纯函数(策略指向 = STRATEGY_BINDINGS 阵营分支 + 角色分支经 CHARACTERS factions 全集派生;环境指向 = faction 分支 + ENV_COMP_AFFINITY 亲和分支;锁定线指向 = Comp.factions 现读,design §2.1);不含选卡判据接线。
**设计依据**:design.md §2.1
**文件面**:`src/sr_od/application/currency_war/kernel/cw_investments.py`;`sr-od-test/test/sr_od/application/currency_war/kernel/test_cw_investments.py`(指向集函数落 cw_investments.py,测试镜像并入其既有测试文件)
**依赖**:无
**优先级建议**:5
**完成判据**:
- 行为对照 design.md §2.1 三条分支语义(faction/亲和/成员)+ §4 kernel 单元清单(黑塔纪元→{银河学者, 群攻};琼玉专家:青雀→{仙舟};命运圣杯契约(env,亲和分支)→{命运圣杯, 能量};命运圣杯邀请(env)→{命运圣杯, 能量};无绑定→空;未注册角色跳过;多阵营角色展开;成员分支装备党→含{追击};特邀专家:桑博亲和分支;特邀专家:加拉赫 faction 例外;持有名归一查询)
- 完成前常规检查(本文首节)
**验收凭据形式**:指向集单元测试名清单

## 3.2 策略选卡护栏接线

**范围**:`invest_strategy.decide` / `decide_pick` 接阵容冲突护栏(冲突基准判定 = 锁定线/持有指向并集切换 + 出域过滤 + 回退 + off-direction 归因前缀)。
**设计依据**:design.md §2.2/§2.3/§2.5
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/invest_strategy.py`;`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_invest_strategy.py`
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- 行为对照 design.md §2.3 规则表 + §4 invest_strategy 行为测试清单(持有指向帧冲突定义型/冲突组件型排除、通用与兼容卡正常、无指向持有帧不回归、全出域回退、刷新交互、锁定换基帧)
- 完成前常规检查(本文首节)
**验收凭据形式**:行为测试名清单;`uv run pytest .../test_invest_strategy.py` 全绿

## 3.3 环境选卡护栏接线

**范围**:`invest_env.decide` / `decide_pick` 接同款护栏(环境指向入口)。
**设计依据**:design.md §2.3/§2.4
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/invest_env.py`;`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_invest_strategy.py`(env 段)
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- 行为对照 design.md §2.4 环境侧 + §4 invest_env 行为测试清单(持有指向帧冲突环境排除、无指向持有帧零变化、通用环境正常、全出域+闸尽回退)
- 完成前常规检查(本文首节)
**验收凭据形式**:行为测试名清单

## 3.4 同 seed 复测对照

**范围**:seed-20261016 重跑 sim 局,r3 三选一不再选黑塔纪元;复跑 CW 全量 L1 收口。落盘走一次性临时脚本(用后即删,design §4 落盘纪律——禁常驻测试落盘复盘档案)。
**设计依据**:design.md §3
**文件面**:.debug 下跑局产物(不入 git);无源码面(回归即改回)
**依赖**:3.2、3.3
**优先级建议**:5
**完成判据**:
- r3 `active_strategies` 写行 ≠ 黑塔纪元(语义锚对照 design.md §3 重演)
- `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 全量一次通过
- 完成前常规检查(本文首节)
**验收凭据形式**:复测局 journal 语义锚 + 全量测试输出

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本(29/28 号稿的护栏节 + 12 号稿 §1.3 引用句,三篇正本统一在末阶段一次更新,各落地阶段不夹带)。
**设计依据**:本文件「正本更新清单」节
**文件面**:`docs/develop/sr_od/application/currency_war/strategy-docs/29_invest_strategy_screen.md`;`docs/develop/sr_od/application/currency_war/strategy-docs/28_invest_env_screen.md`;`docs/develop/sr_od/application/currency_war/strategy-docs/12_line_and_intention.md`
**依赖**:3.1-3.4 全部
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致
**验收凭据形式**:文档对照 review

## 正本更新清单

- `strategy-docs/29_invest_strategy_screen.md`:§3 结构分区(落地序前置「阵容冲突护栏」步 + §2.5 关键取舍进动机) ← 3.2
- `strategy-docs/28_invest_env_screen.md`:结构分区/护栏节 ← 3.3
- `strategy-docs/12_line_and_intention.md`:补一句「投资选卡端消费『已持有投资的阵容指向集』做冲突排除(锁定后基准 = 锁定线 factions);该护栏不读方向层状态、不进 committed 语义,与方向层读口无耦合」(落 §1.3 或 §4 按行文就近) ← 3.2
