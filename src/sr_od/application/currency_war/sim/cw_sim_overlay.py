"""sim overlay 占位披露键(常量宿主)。

现役 overlay 架构(呈现/判据/词表单一源均在本模块外):

- **判据与登记**:kernel 值回调(cw_faction_callbacks,deployed 逻辑写
  尾派生维护)→ 容器登记簿记(gs.screen_changes,kernel/
  cw_overlay_register 三口 + 九 kind 封闭词表);
- **呈现**:sim 后端问询时点懒呈现 + advance 纯转移尾 + 节点窗起点
  (sim/cw_sim_backend._present_pending_overlay);
- **无 sim 呈现面族**(画面 op 无 sim 观察分支)消费 + 披露,
  披露键 = 本模块 ``OVERLAY_PARAM_PENDING`` 逐 kind 后缀。

(旧统一队列与占位框架已整体停用;呈现/判据/词表单一源见上。)
"""
from __future__ import annotations

#: 占位参数统一披露键(随局结果消费;逐 kind 后缀 ``{键}:{kind}``)。
OVERLAY_PARAM_PENDING: str = 'overlay_param_pending'
