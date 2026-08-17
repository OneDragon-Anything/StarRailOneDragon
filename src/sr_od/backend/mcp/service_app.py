"""MCP 应用运行工具：一条龙、独立应用、应用列表与自定义 operation 运行入口。"""

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from sr_od.backend import operation_registry
from sr_od.backend.backend_context import SrBackendContext
from sr_od.backend.schemas import ApplicationListResult, OperationListResult

if TYPE_CHECKING:
    from one_dragon.base.operation.operation_base import OperationResult


def make_run_one_dragon(backend: SrBackendContext) -> Callable:
    """构造 ``run_one_dragon`` tool。"""
    async def run_one_dragon(
        block: Annotated[bool, Field(description="False=立刻返回用 get_run_status 查进度(默认);True=阻塞到一条龙结束")] = False,
    ) -> dict:
        """按当前 GUI/配置的一条龙设置启动完整一条龙运行。

        跑全套已启用应用用本 tool;单个应用用 ``run_standalone_app``;单个 operation 用 ``run_operation``。

        block=False(默认)立刻返回,用 get_run_status 查进度;block=True 阻塞到结束。
        副作用:操作游戏并运行已启用的一条龙应用组;单跑道,已有运行时返回错误。

        Returns:
            三种形态:① 并发拒绝 dict ``{started: False, error, source, hint}``;
            ② 受理 dict ``{started: True, source, app, started_at, hint}``(block=False);
            ③ block=True 终态 dict ``{success: bool, result: <结果文本>}``。
            进度/结果细节看 ``get_run_status``。
        """
        try:
            ok, future = backend.run_one_dragon('mcp')
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'started': False, 'error': str(e)}
        if not ok:
            # 并发拒绝时返回当前占用者信息，方便 agent 决定轮询还是停止。
            st = backend.query_status()
            return {
                'started': False,
                'error': '已有运行在进行中',
                'source': st.source,
                'hint': '先 get_run_status 查状态,或 stop_run 停止',
            }
        if not block:
            # 长耗时自动化默认不阻塞 MCP 调用，避免 agent 等待期间失去交互能力。
            st = backend.query_status()
            return {
                'started': True,
                'source': 'mcp',
                'app': st.app,
                'started_at': st.started_at,
                'hint': '用 get_run_status 查进度与结果',
            }
        # block=True 只返回最终摘要，不把运行日志塞进 tool 输出。
        result: OperationResult | None = await asyncio.wrap_future(future)
        if result is None:
            return {'success': False, 'result': '一条龙运行结束,但未返回结果'}
        return {'success': result.success,
                'result': '一条龙运行成功' if result.success else f'一条龙运行失败: {result.status}'}
    return run_one_dragon


def make_run_standalone_app(backend: SrBackendContext) -> Callable:
    """构造 ``run_standalone_app`` tool。"""
    async def run_standalone_app(
        app_id: Annotated[str | None, Field(description="独立应用 ID;None=用 GUI「应用运行」当前选中项")] = None,
        block: Annotated[bool, Field(description="False=立刻返回用 get_run_status 查进度(默认);True=阻塞到结束")] = False,
    ) -> dict:
        """启动独立应用。

        单个应用用本 tool;全套用 ``run_one_dragon``;单个 operation 用 ``run_operation``。

        app_id 为空时使用 GUI「应用运行」当前选中的应用。block=False(默认)立刻返回,
        用 get_run_status 查进度;block=True 阻塞到结束。副作用:操作游戏并运行目标应用。

        Returns:
            三种形态:① 并发拒绝 dict ``{started: False, error, source, hint}``;
            ② 受理 dict ``{started: True, source, app, started_at, hint}``(block=False);
            ③ block=True 终态 dict ``{success: bool, result: <结果文本>}``。
            进度/结果细节看 ``get_run_status``。
        """
        try:
            ok, future = backend.run_standalone_app('mcp', app_id=app_id)
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'started': False, 'error': str(e)}
        if not ok:
            # 并发拒绝时返回当前占用者信息，方便 agent 决定轮询还是停止。
            st = backend.query_status()
            return {
                'started': False,
                'error': '已有运行在进行中',
                'source': st.source,
                'hint': '先 get_run_status 查状态,或 stop_run 停止',
            }
        if not block:
            # 独立应用也可能跑很久，默认立刻返回并交给 get_run_status 轮询。
            st = backend.query_status()
            return {
                'started': True,
                'source': 'mcp',
                'app': st.app,
                'started_at': st.started_at,
                'hint': '用 get_run_status 查进度与结果',
            }
        # block=True 只返回最终摘要，不把运行日志塞进 tool 输出。
        result: OperationResult | None = await asyncio.wrap_future(future)
        if result is None:
            return {'success': False, 'result': '独立应用运行结束,但未返回结果'}
        return {'success': result.success,
                'result': '独立应用运行成功' if result.success else f'独立应用运行失败: {result.status}'}
    return run_standalone_app


def make_list_applications(backend: SrBackendContext) -> Callable[[], ApplicationListResult | dict]:
    """构造 ``list_applications`` tool。"""
    def list_applications() -> ApplicationListResult | dict:
        """列出当前实例可运行应用、独立应用列表和当前选中项(无副作用)。

        列应用用本 tool;列可运行 operation 用 ``list_operations``。

        返回的 ``current_instance_idx`` 是激活实例的 idx(账号下标):**idx N → config/0N 目录**
        (idx 1 → config/01 账号01,idx 2 → config/02 账号02),**不是** config/0<idx+1>。
        激活实例看 ``config/one_dragon.yml`` 的 ``instance_list`` 里 ``active: true`` 项;
        改某实例配置前据此定位目录,别把 idx 当目录号做偏移。

        Returns:
            ``{current_instance_idx, active_standalone_app_id, applications[]}``;
            ``active_standalone_app_id`` = GUI「独立应用运行」当前选中项(无则 None)。
            ``applications[]`` 元素: ``{app_id, app_name, enabled_in_one_dragon(是否在
            一条龙组里启用), in_standalone_list(是否在独立应用列表), is_active_standalone
            (是否为当前选中独立应用)}``。
        """
        try:
            return backend.list_applications()
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'error': str(e)}
    return list_applications


def make_list_operations(backend: SrBackendContext) -> Callable[[], OperationListResult | dict]:
    """构造 ``list_operations`` tool(自定义 operation 运行入口)。"""
    def list_operations() -> OperationListResult | dict:
        """列出可运行的自定义 operation(扫描 operations/ 承载包,纯反射不实例化)。

        列 operation 用本 tool;列应用用 ``list_applications``。

        返回每个 operation 的 op_id(<module>.<ClassName>)与 __init__ 参数 schema(已剔除
        self/ctx)。用 describe_operation 看单个详情,用 run_operation 按 op_id 运行。无副作用。

        Returns:
            ``{operations[], failures[]}``。``operations[]`` 元素:
            ``{op_id, class_name, module, params[]}``;``params[]`` 元素见
            ``describe_operation`` 的 Returns(结构相同)。``failures[]`` 是单模块
            import 失败记录(``{module}: {error}``),不影响其余扫描结果。
        """
        try:
            return operation_registry.scan_operations(backend.ctx)
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'error': str(e)}
    return list_operations


def make_describe_operation(backend: SrBackendContext) -> Callable[[str], dict]:
    """构造 ``describe_operation`` tool(自定义 operation 运行入口)。"""
    def describe_operation(
        op_id: Annotated[str, Field(description="operation 定位标识 <module>.<ClassName>,可从 list_operations 获取")],
    ) -> dict:
        """描述单个 operation 的参数 schema(纯反射,不实例化)。

        op_id 格式 ``<dotted module path>.<ClassName>``,可从 list_operations 获取。
        每个参数标 json_serializable(标量/list/dict=True、复杂数据类如 ChargePlanItem=False,
        提示走 application);整体 debuggable 表示所有必填参数是否可经 JSON 传入。

        Returns:
            ``{op_id, debuggable, params[]}``;``params[]`` 元素:
            ``{name, annotation(类型注解字符串,如 'str'/'ChargePlanItem'), required,
            default(默认值字符串,必填为 None), json_serializable(可否直接传 JSON 值),
            coercible(@dataclass+from_dict,可传 dict 自动反序列化)}``。
        """
        try:
            return operation_registry.describe_operation(backend.ctx, op_id)
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'error': str(e)}
    return describe_operation


def make_run_operation(backend: SrBackendContext) -> Callable:
    """构造 ``run_operation`` tool(自定义 operation 运行入口)。

    按 op_id 运行任意 operation;args 以构造参数 ``cls(ctx, **args)`` 烤进闭包。
    resolve_op_class + validate_args 在调用方线程先校验,通过后才提交单跑道运行槽。
    """
    async def run_operation(
        op_id: Annotated[str, Field(description="operation 定位标识 <module>.<ClassName>,可从 list_operations 获取")],
        args: Annotated[dict | None, Field(description="构造参数 dict;JSON 标量/列表/字典,@dataclass+from_dict 参数传 dict 自动反序列化;其余复杂数据类走 application")] = None,
        block: Annotated[bool, Field(description="False=立刻返回用 get_run_status 查进度(默认);True=阻塞到结束")] = False,
    ) -> dict:
        """按 op_id(package.path.ClassName)运行任意 operation;args 传构造参数。

        单个 operation 用本 tool;全套用 ``run_one_dragon``;单个应用用 ``run_standalone_app``。

        args 传 JSON 标量/列表/字典;``@dataclass``+``from_dict`` 参数传 dict,实例化前自动反序列化;其余复杂数据类走 application。
        用 list_operations / describe_operation 查 op_id 与参数。
        block=False(默认)立刻返回,用 get_run_status 查进度;block=True 阻塞到结束。
        副作用:操作游戏;单跑道,已有运行时返回错误(含 source + 提示)。

        Returns:
            三种形态:① 参数/并发错误 dict ``{started: False, error(, source, hint)}``;
            ② 受理 dict ``{started: True, op_id, source, started_at, hint}``(block=False);
            ③ block=True 终态 dict ``{success: bool, result: <结果文本>}``。
            进度/结果细节看 ``get_run_status``。
        """
        try:
            cls = operation_registry.resolve_op_class(op_id)
            err = operation_registry.validate_args(cls, args or {})
            if err:
                return {'started': False, 'error': err}
            # 闭包把 cls + args bake 进 op_factory(槽只认统一签名 op_factory(ctx) → Operation)
            def op_factory(ctx):  # noqa: ANN202 闭包签名固定 Callable[[SrContext], Operation]
                # @dataclass+from_dict 参数的 dict 值反序列化为实例
                coerced_args = operation_registry.coerce_dataclass_params(cls, args or {})
                return cls(ctx, **coerced_args)
            ok, future = backend.run_slot._start(
                'mcp', op_factory=op_factory, display_name=op_id,
            )
        except Exception as e:  # noqa: BLE001 工具层兜底(resolve/validate/_start 异常)
            return {'started': False, 'error': str(e)}
        if not ok:
            # 并发拒绝:返回当前占用者信息,方便 agent 决定轮询还是停止。
            st = backend.query_status()
            return {
                'started': False,
                'error': '已有运行在进行中',
                'source': st.source,
                'hint': '先 get_run_status 查状态,或 stop_run 停止',
            }
        if not block:
            st = backend.query_status()
            return {
                'started': True,
                'op_id': op_id,
                'source': 'mcp',
                'started_at': st.started_at,
                'hint': '用 get_run_status 查进度与结果',
            }
        # block=True 只返回最终摘要,不把运行日志塞进 tool 输出。
        result: OperationResult | None = await asyncio.wrap_future(future)
        if result is None:
            return {'success': False, 'result': 'operation 运行结束,但未返回结果'}
        return {'success': result.success,
                'result': 'operation 运行成功' if result.success else f'operation 运行失败: {result.status}'}
    return run_operation
