"""sim overlay 占位披露键(常量宿主)。

现役 overlay 架构(呈现/判据/词表单一源均在本模块外):

- **判据与登记**:kernel 值回调(cw_faction_callbacks,deployed 逻辑写
  尾派生维护)→ 容器登记簿记(gs.screen_changes,kernel/
  cw_overlay_register 三口 + 九 kind 封闭词表);
- **呈现**:sim 后端问询时点懒呈现 + advance 纯转移尾 + 节点窗起点
  (sim/cw_sim_backend._present_pending_overlay);
- **无 sim 呈现面族**(画面 op 无 sim 观察腿)消费 + 披露,
  披露键 = 本模块 ``OVERLAY_PARAM_PENDING`` 逐 kind 后缀。

(旧「统一 overlay 队列 + 三元组占位框架」[队列/选项生成占位/占位
效果应用/占位面清单]已整体退役:呈现数据源 = 容器登记,选项效果
建模候实机补档按需重建,占位清单以退役词表为键且零生产调用。)
"""
from __future__ import annotations

#: 占位参数统一披露键(随局结果消费;逐 kind 后缀 ``{键}:{kind}``)。
OVERLAY_PARAM_PENDING: str = 'overlay_param_pending'
