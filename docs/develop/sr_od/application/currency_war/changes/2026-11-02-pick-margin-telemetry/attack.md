# 设计对抗报告汇总(pick-margin-telemetry)

> 各轮由独立干净上下文子 agent 执行,全文在其会话交付记录(git 外);本文件 = 轮次与处置登记。

## 轮次轨迹

| 轮 | 发现 | 性质 |
|---|---|---|
| R1 | 13(5高) | 初稿可行性主张全部未核码(遭遇面无总分/搜索纯 argmax 无次名/deploy 键族不存在/payload 纪律冲突/定型帧无判据)——退回重写 |
| R2 | 7(2高) | R1 修订的码点声称全核实为真;数据通道对部署面空头支票(emit 首动作与定型无关)+文件面缺必改三文件(cw_vocab/flow/bridge)+键表单一源既有漂移 |
| R3 | 8(1高) | 私有槽帧定界机制缺失(虚拟调用点无法分流——sell_candidates 与 entry 实参相同/持久槽陈旧读到非部署帧/diff 空写入时点)+挑战者身份缺键形+无挑战者形态缺失+挑战者排序键未钉+基类 docstring 纪律漂移+键数泛化漏网+文件面缺 mandate_state/entry+轮次叙事违例+attack.md 断链 |
| R4 | 5(1中) | 收敛确认:R3 十处置面全部落地为真、直调全过;新发现 = 读后清与 decision_payload 零写纪律的挂点归属未定(定 bridge 覆写)/dataclass margin 字段未落字/异常路径残角申报/钩子签名缺省参兼容形/README 出处双写——全部补句处置 |

## 处置状态

- R1 13 条:全部处置(遭遇面退出/通道定版/部署收集面如实申报/顶层键/评分现值源改 scores/竞争域次名/定型出口挂载/分层 margin/板签名/键表单一源/频率保守)。
- R2 7 条:全部处置(双通道定版:词表字段[投资两 pick]+私有槽[部署];文件面补 cw_vocab/flow/bridge/cw_strategy;键表漂移随批修[回填+新增+主句两类来源+键数统一];虚拟边界穷举 5 调用点;边界值表;README 同步;末阶段七件)。
- R3 8 条:全部处置(select_deployment 纯函数+可选收集出参 margin_out——虚拟 4 点不传零写入;写入点 = entry._step5_deploy 在 deploy_diff 后;帧定界 = 入口清+读后清双保险;部署键形加挑战者板签名;无挑战者 null 形态+挑战者排序键钉死段 3 全键同款;基类 docstring :270-272 随批同步;键数统一泛化面补 decision_payload:3/:184;文件面补 mandate_state/entry/test_select_deployment/invest_env 落点;正文剥轮次叙事壳;本文件落盘补链)。

## 纪律

每轮干净上下文/无预设焦点/直调禁转述/零发现合法/禁和稀泥;判据源 = iteration-design + strategy-work §6 + strategy-telemetry.md + 现行代码直调 + 测试仓镜像。
