"""sim 接缝端口模块(驱动反转;接口契约唯一载体,权威版本 = sim-design.md §6.2)。

sim 重构为「游戏后端」(SimBackend)后,流程侧与后端的全部替换面收敛在
本模块:模块级装配槽 + 端口函数。**缺省 ``None` = 纯实机**,零行为变化;
装配纪律 = 进程内单装配(重复安装 raise)、``uninstall_sim_backend`` 幂等、
测试 teardown 必卸(模块槽是进程全局,残留跨测试泄漏)。模式先例 =
``decision_assembly.install_obs_ports`` 家族「模块级槽 + 缺省关 + 装配点
显式接通」;装配点 = sim 运行器(测试仓 harness 与未来实跑入口)。

端口六口(薄协议,签名不随屏数增长):
- ``screen_identity()`` —— 后端画面状态机答当前 screen_info 档名;
- ``observe(screen_name)`` —— 生成器直出该屏 ``CwScreenXxxObs`` 形状产物
  (消费方 = 画面 op 读屏点,产物必须经 ``cw_screen_report`` 同名上报函数
  落状态容器,写通道铁律见 flow-seam 详设 §3);
- ``sim_or_live_observation(screen_name, live_read)`` —— 读屏点改道 helper:
  装了后端 → ``observe``,否则原读链(逐屏显式读屏点一行机械接入);
- ``click_answer(op, screen_name, area_name, until_find_all, until_not_find_all)``
  —— sim 点击应答:后端先按点击处理画面状态机转移,再出实机同形 round
  结果(机械镜 = :func:`mirror_click_answer`);
- ``visible(screen_name, area_name)`` —— until / 门可见性问询;
- ``declare_world(decl)`` —— 动作后果声明喂入(声明化主通道):未装配
  = no-op(实机零开销零行为变化),装配后 = 后端 ``advance(decl)``;
  ``decl is None``(非转移动作,无声明可喂)本层直返。

依赖方向:本模块不 import kernel/operations/后端本体(后端对象经装配槽
注入,鸭子类型);``SimBackendProtocol`` 只做类型面文档,不做运行时检查。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from one_dragon.base.operation.operation import Operation
    from one_dragon.base.operation.operation_round_result import (
        OperationRoundResult,
    )
    from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl


class SimBackendProtocol(Protocol):
    """sim 后端端口协议(结构类型;3.2 SimBackend 按此实现)。

    形状取最小稳定面(薄协议):新增屏 = 后端注册生成器,协议签名不变
    (旧协议 4 方法随流程形态漂移作废的教训:协议形状取最小面)。
    """

    def screen_identity(self) -> str:
        """当前画面 screen_info 档名(画面状态机唯一答口)。"""
        ...

    def observe(self, screen_name: str) -> Any:
        """生成器直出该屏观察产物(CwScreenXxxObs 形状;零截图零识别)。"""
        ...

    def visible(self, screen_name: str, area_name: str) -> bool:
        """until / 门可见性问询(画面状态机裁该 area 当前是否可见)。"""
        ...

    def click_answer(
        self,
        op: Operation,
        screen_name: str,
        area_name: str,
        until_find_all: list[tuple[str, str]] | None,
        until_not_find_all: list[tuple[str, str]] | None,
    ) -> OperationRoundResult:
        """sim 点击应答(契约见 :func:`mirror_click_answer`)。"""
        ...

    def advance(self, decl: WorldDecl) -> None:
        """声明驱动推进(按 ``decl.trigger`` 分派状态过程/画面呈现,完成后
        按 ``decl.next_screen`` 等值对账;动作后果声明化迭代总纲
        design.md §2.2 契约 5)。"""
        ...


#: 装配槽(进程全局,缺省 None = 纯实机)。禁在模块外直接读写,
#: 一律走 install/uninstall/get(单装配纪律的单点)。
_BACKEND: SimBackendProtocol | None = None


def install_sim_backend(backend: SimBackendProtocol) -> None:
    """装配 sim 后端(进程内单装配;重复安装 raise)。

    调用方(sim 运行器)负责 teardown 必卸:模块槽是进程全局,
    残留会把后续测试/实跑静默切进 sim 模式。
    """
    global _BACKEND
    if _BACKEND is not None:
        raise RuntimeError(
            'sim 后端重复安装(进程内单装配;装前先 '
            'uninstall_sim_backend 复位,或检查装配点是否重复进入)')
    _BACKEND = backend


def uninstall_sim_backend() -> None:
    """卸载 sim 后端(幂等;未装配时调用 = 无操作)。"""
    global _BACKEND
    _BACKEND = None


def get_sim_backend() -> SimBackendProtocol | None:
    """当前装配的后端(None = 未装配 = 纯实机)。"""
    return _BACKEND


def sim_backend_installed() -> bool:
    """sim 后端是否在装配(直连旁路 port 检查与 CwOperation 覆写面共用)。"""
    return _BACKEND is not None


def _require_backend() -> SimBackendProtocol:
    """取装配槽;未装配 = AssertionError 响亮(端口六口只在 sim 分支可达,
    未装配即触达 = 调用点接错,禁静默回落实机)。"""
    if _BACKEND is None:
        raise AssertionError(
            'sim 后端未装配(端口调用只在 install_sim_backend 之后合法;'
            '检查装配点与调用序)')
    return _BACKEND


def screen_identity() -> str:
    """当前画面 screen_info 档名(后端画面状态机答)。"""
    return _require_backend().screen_identity()


def observe(screen_name: str) -> Any:
    """生成器直出该屏观察产物(消费方必须经同名上报函数落状态容器)。"""
    return _require_backend().observe(screen_name)


def visible(screen_name: str, area_name: str) -> bool:
    """until / 门可见性问询。"""
    return _require_backend().visible(screen_name, area_name)


def sim_or_live_observation(screen_name: str,
                            live_read: Callable[[], Any]) -> Any:
    """读屏点改道 helper(观察分支唯一 op 触点的接入原语)。

    装了后端 → ``observe(screen_name)``(生成器直出);否则执行
    ``live_read()`` 原读链。逐屏显式读屏点一行机械改:
    ``obs = cw_sim_ports.sim_or_live_observation('货币战争-备战', lambda: 原读链())``。
    """
    if _BACKEND is not None:
        return _BACKEND.observe(screen_name)
    return live_read()


def sim_or_live_identity(screen_names: tuple[str, ...] | list[str],
                         live_read: Callable[[], str | None]) -> str | None:
    """画面身份读点改道 helper(外循环阶段一身份分发的接入原语)。

    语义与 :func:`sim_or_live_observation` 同族:装了后端 →
    ``screen_identity()``(画面状态机唯一答口,flow-seam 附录 A.2
    「sim 画面身份归 screen_identity」),且仅当档名 ∈ 调用方清单时返回
    (清单外 = None,结束本次访问调用方默认分支——与实机 ``get_match_screen_name``
    的清单过滤语义同形,备战两识别标志同帧命中的默认分支因此不受影响);未装配 → 执行
    ``live_read()`` 原识别链,实机路径零行为变化。
    """
    if _BACKEND is not None:
        name = _BACKEND.screen_identity()
        return name if name in screen_names else None
    return live_read()


def mechanical_io_allowed() -> bool:
    """机械 IO 分支(直连 controller 点击/拖拽)当前是否可达。

    实机(未装配)True;sim 装配后 False——机械执行分支静默跳过,动作的
    状态副本反应由紧随的自上报(上报函数族)承接(flow-seam 详设 §2
    直连旁路 port 检查口,与各旁路文件逐点守卫同用;漏改路径仍由
    运行器 controller 桩兜底触碰即炸)。
    """
    return _BACKEND is None


def click_answer(
    op: Operation,
    screen_name: str,
    area_name: str,
    until_find_all: list[tuple[str, str]] | None,
    until_not_find_all: list[tuple[str, str]] | None,
) -> OperationRoundResult:
    """sim 点击应答(委托装配后端;契约 = :func:`mirror_click_answer`)。"""
    return _require_backend().click_answer(
        op, screen_name, area_name, until_find_all, until_not_find_all)


def declare_world(decl: WorldDecl | None) -> None:
    """动作后果声明喂入(声明化主通道;动作后果声明化迭代总纲
    design.md §2.2 契约 3)。

    未装配 = no-op(实机零开销零行为变化——与 ``sim_or_live_*`` 族
    同型的缺省关纪律);装配后 = ``_BACKEND.advance(decl)``;
    ``decl is None``(非转移动作,上报出口恒 None)本层直返,不触后端。
    """
    if _BACKEND is None or decl is None:
        return
    _BACKEND.advance(decl)


def mirror_click_answer(
    op: Operation,
    screen_name: str,
    area_name: str,
    until_find_all: list[tuple[str, str]] | None,
    until_not_find_all: list[tuple[str, str]] | None,
) -> OperationRoundResult:
    """点击应答机械镜(实机 ``round_by_find_and_click_area`` 语义的 sim
    镜像;后端 click_answer 的共享实现——先处理状态机转移,再委托本
    helper 出实机同形 round 结果)。

    - 点击分支 = screen_loader 档案点位直成功(area 未建档 = round_fail
      响亮,与实机 AREA_NO_CONFIG 同形;``node_clicked`` 置位语义保留,
      ``update_screen_after_operation`` 画面簿记照走——两者均零 controller
      触达);
    - **屏门**(实机「按钮在本帧上找到才点得着」的 sim 对偶):问询屏
      非后端当前呈现屏(经 :func:`visible` 判定)→ round_retry(实机
      OCR_CLICK_NOT_FOUND 同形,调用方按 is_success 分流)。无此门 =
      任意屏上点击恒成功,驻留型动作 op 在状态副本已切走后仍每轮「点击 +
      上报」越屏偷跑推进——冒烟批阻断二实证(结算确认把后续 16 节点
      的推进全部冒领,流程层节点处理零执行,5000 步风暴假通过);
    - until 问询 = :func:`visible`(``until_not_find_all`` = 取反,目标区域
      不可见才算过);问询为假 = 继续轮询返回 ``round_wait``,**不重发点击**
      (sim 点击分支已成功,重发会重复触发状态机转移);
    - 有 until 按实机同形 ``round_wait``(「点了≠成了」,下一轮 until 问
      状态机取转移后真值),无 until = ``round_success``。
    """
    if until_find_all is not None and op.node_clicked:
        if all(visible(_s, _a) for _s, _a in until_find_all):
            return op.round_success(status=area_name)
    if until_not_find_all is not None and op.node_clicked:
        if not any(visible(_s, _a) for _s, _a in until_not_find_all):
            return op.round_success(status=area_name)
    area = op.ctx.screen_loader.get_area(screen_name, area_name)
    if area is None:
        return op.round_fail(status=f'区域未配置 {area_name}')
    if not visible(screen_name, area_name):
        return op.round_retry(status=f'未找到 {area_name}')
    op.node_clicked = True
    op.update_screen_after_operation(screen_name, area_name)
    if until_find_all is None and until_not_find_all is None:
        return op.round_success(status=area_name)
    return op.round_wait(status=area_name)
