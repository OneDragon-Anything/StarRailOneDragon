"""货币战争 RunNode 基类:对局内一个节点的生命周期 owner。

(头 # 未验证 标记已清,2026-08-24 架构 review 卫生项:子类
supply/megastar 均已 live 跑过——局47 r5 补给 RunSupplyNode
正常处理实证;基类 committed-but-verifying 语义经多局验证。)

op 划分方法论(2026-08-04 实践提炼,详 ``.debug/temp/currency_war/runnode_decomposition.md``;
后续沉淀进 od-dev skills):

旧 ``Handle*`` 是**盲单发** —— 做一次动作就**无条件** ``round_success``,从不验证节点是否真完成
(overlay 是否消失)→ 动作失败(确认灰 / click 没中 / 多步缺一步)时也回 success → 外层 flat loop
``round_wait``(**不计 retry**)无限重派 → 卡死烧预算。实例:巨星 6min、投资策略 18min、投资环境卡死。

RunNode 改 **committed-but-verifying + 节点作用域预算**:
  每轮(框架经 ``round_retry`` 重跑当前节点,计 ``node_max_retry_times`` 预算):
    1. 截屏 → **验证完成**:已不在本节点画面(``_in_node`` 返 False,通常 = 节点关键词消失)=
       overlay 关闭 / 进了下一节点 → ``round_success``(节点完成,交还外层)。
    2. 仍在节点内 → ``_do_action`` 做当前阶段一个动作 → ``round_retry``(重跑,计预算)。
  超 ``node_max_retry_times`` 仍未完成 → 框架转 **FAIL**(bail 交还外层;**不无限烧全局预算**)。

子类实现:
  - ``_in_node(screen) -> bool``:还在本节点画面?False = 节点结束(子类给关键词判定)。
  - ``_do_action(screen) -> None``:本节点一个动作(选 / 点 / 确认;子类特定)。
  - ``@operation_node`` 装饰的入口方法(设 name + ``node_max_retry_times``=节点预算)调 ``self._run_node()``。

职责边界:外层 ``CurrencyWarRunLoop`` 仍负责"**分类**进哪种节点 → **委派** RunNode";RunNode 只管
"**把这节点跑到完**(验证完成才 success,超预算 bail)"。永久卡死的节点(如巨星待修机制)会反复
bail —— 需外层升级(连续 bail → 弃局)或修节点机制,非本基类职责。
"""
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.operations.sr_operation import SrOperation


class RunNode(SrOperation):
    """对局内节点生命周期 owner:committed-but-verifying + 节点作用域预算。"""

    def _run_node(self) -> OperationRoundResult:
        """committed-but-verifying 节点循环(子类 ``@operation_node`` 入口调此)。

        每轮:验证完成(已离开本节点画面)→ success;否则做一动作 → round_retry(计预算,超 → FAIL)。
        """
        screen = self.last_screenshot
        # 验证完成:已不在本节点画面 = overlay 消失 / 进了下一节点 → 节点完成,交还外层。
        if not self._in_node(screen):
            return self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)')
        # 仍在节点内 → 做一个动作;round_retry 重跑本节点(计 node_max_retry_times 预算,超 → FAIL bail)。
        self._do_action(screen)
        return self.round_retry(wait=1.5)

    def _in_node(self, screen) -> bool:
        """还在本节点画面?False = 节点结束(子类实现,通常 = 节点关键词消失)。"""
        raise NotImplementedError

    def _do_action(self, screen) -> None:
        """本节点的一个动作(选 / 点 / 确认;子类实现)。每次轮到重跑都会再调一次。"""
        raise NotImplementedError
