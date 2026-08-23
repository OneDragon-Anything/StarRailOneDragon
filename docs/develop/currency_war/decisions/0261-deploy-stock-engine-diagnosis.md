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

## 裁决落地(2026-08-24,指挥官裁定「1+3 组合」;原诊断不动)

主会话裁决采纳选项 1 + 选项 3 组合(选项 2「r288 门加引擎件豁免」
未采纳——r288 保持既定配方纪律不变):

1. **选项1(op 补 ignition 排序)**:`deploy_bench.py` 排序统一走
   新增模块级 `_deployment_order`(import `cw_deploy_logic.ignition_gain`
   单一源,不复制)——tgt 序 `(-ignition_gain, -tier_completes)`、
   rest 序 `(-ignition_gain, r251 引擎身份键)`、桶序修正(点火 rest
   件先于 ignition=0 的 tgt 件),与 r404-A1/ADR-0258 纯函数语义一致;
2. **选项3(纯函数补 r288 门)**:`cw_deploy_logic.select_deployments`
   上场循环补 r288 配方底线门(主阵营=列车同行 且 running 列车≥2
   且仙舟<3 → 让位留 bench;running 阵营档随每件上场累加,等价 op
   drag 循环的动态仲裁)——**消 sim 盲区**:sim 从此能测出「引擎件
   被配方底线拦」形态(局64 姬子躺 bench 不再 sim 不可见);
3. **对齐后差异面**:op 与纯函数的行为差异只剩「读屏 vs 内存态」
   (op 的 SIFT 读身份/槽位坐标/drag 验证);诊断提到的两处漂移
   (排序首键/r288 门)均已双向对齐,无其它漂移点残留。

配套锁测试:bfd1c21 两条诊断锁按新语义更新(局64 形态纯函数**同样**
拦姬子=对齐锚;点火形态门不触发);新增 `test_cw_a3_deploy_align.py`
3 条(op 排序点火首键探针形态/tgt 内点火首键/op 与纯函数同输入序一致)。

效果预期:局64 形态(列车2 已达+仙舟<3)两侧一致拦截列车第 3 人
(r288 纪律保持);「deployed 非引擎 + bench 点火引擎件」形态由
ignition 首键修正——点火引擎件不再被非引擎 tgt 件压在序后。sim 侧
影响(engines2 分布变化)由指挥官下段跑 sim 批量对照验证,本段只落
代码+锁。
