# ADR-0261: deploy 引擎件存量躺 bench 诊断——根因在 op 侧,纯函数不改(A3 修复2)

- **Status**: accepted(诊断结论;op 侧修改待主会话裁决)
- **Date**: 2026-08-24

## Context

A3 实机弹药 v2.1:局末「买了没上」5 人次(姬子·启行×2/彦卿/饮月/
开拓者·欢愉躺 bench,deployed 上着非引擎件)。任务规格疑因:
select_deployments 的 ignition_gain 排序折损存量件或围栏误 held。

## 诊断(探针复现,探针用完即删)

用局64 精确数据形态(deployed=饮月+三月七+3 非引擎,bench=姬子×2,
cap=7)对 `cw_deploy_logic.select_deployments` 复现:**纯函数让姬子
上场**(排序/围栏均无病;第二张按 r404-A2 去重正确留 bench)。真根因
在**生产路径 DeployBench op(`deploy_bench.py`)与纯函数的漂移**:

1. op `_deploy_deterministic` 的 tgt/rest 排序**没有 ignition_gain
   首键**(r404-A1 只落了纯函数侧;op 还是 r361 tier_completes +
   r251 引擎身份键旧序);
2. op 的 r288 配方底线门(列车≥2 且仙舟<3 → 列车件留 bench,
   deploy_bench.py `配方底线` 分支)正是局64 姬子躺 bench 的直接
   机制——deployed 已有饮月+三月七=列车2,仙舟 1-2<3,姬子被拦;
3. 纯函数侧**没有** r288 门 → sim 永远看不见该拦截(执行层代理
   覆盖缺口,ADR-0249 同型)。

## Considered Options

1. **报告不改**(本 ADR)——deploy_bench.py 不在本任务声明文件集;
   且 r288 门是既定配方纪律(局23/24 实锤的刻意设计),「列车第 3
   人 vs 仙舟基础线」是**策略权衡不是明确 bug**,改动应由主会话
   裁决(选项:op 补 ignition 排序 / r288 门加引擎件豁免 / 纯函数
   补 r288 门对齐 sim)。
2. 硬改 op——越声明文件集 + 单方面推翻 r288 既定纪律。
3. 纯函数加 r288 门「对齐」——方向反了:会把 sim 也变差
   (engines2 刚由 ADR-0260 改善),且治标(排序漂移仍在)。

## Decision

选 1:纯函数零改动;锁测试 2 条把局64 形态的纯函数正确行为钉死
(防排序回归 + 记录 op/sim 分歧的 sim 侧锚点);本 ADR 记录完整
诊断链供裁决。顺带在 cw_deploy_logic 模块注释标注与 op 的已知漂移点。

## Consequences

- A3「deploy 侧引擎优先级缺口」的修复**未在本批完成**——修复落点
  在 deploy_bench.py(op 排序 + r288 门豁免),等主会话裁决;
- 若裁决改 op:同步评估纯函数是否补 r288 门(消 sim/生产分歧,
  否则 sim 继续测不出该形态);
- 实机验证锚点(裁决后修复生效时):局末 bench 不再有「引擎件×n
  + deployed 非引擎件 + cap 未满」形态。
