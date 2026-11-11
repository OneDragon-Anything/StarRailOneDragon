"""sim 战斗结算战力模型子包(设计权威版本 =
docs/develop/sr_od/application/currency_war/sim/sim-power-model.md;
首期落地形态与迭代收束史归 git 历史)。

本包子面(渐次落位):语料抽取器(本包现有)/ 训练与校准 /
查询面与权重常量 / 幅度层。纪律:
- 铁律 1(唯一消费者 = sim 战斗结算层):策略模块禁 import 本包,
  依赖方向锁断言集随查询面落地;
- 铁律 2:抽取器输入守卫 = 解析后路径精确相等断言 + sim 批根目录
  守卫 + run 级隔离(corpus_extract 模块);
- 铁律 3:HP 量只进幅度样本表,不入胜负特征(features 模块)。

产物落 .debug(gitignored),data/ 桶禁落任何模型产物(权威版本 §6.2-2)。
"""
