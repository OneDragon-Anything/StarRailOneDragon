# P26 参数标定报告(候用户裁;零拟合常数进策略代码)

- 生成时间:2026-09-05T23:33:27.662061+00:00
- 数据源:D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\replay
- 状态:**insufficient: 实机 p26_prep_obs 样本不足(join 后 n=0 < 10),不硬跑;待采集批补样后重跑**
- decisions 行 15535,其中带 p26_prep_obs 0 行;outcomes 行 2064;join 后 0 行
- join 轮号对账:可比 0 行,node_type_next 与结算 node_type 错位 0 行 {}

## 结论使用边界

- 本报告为纯标定产出;任何桶/分位进入策略代码前须经用户裁与对抗审查,脚本自身不写任何策略常数。
- 样本不足的桶/节点型只代表「当前无证据」,不代表「无差异」;定向补样优先补 insufficient 高频桶。
