"""MCP 应用运行工具：一条龙、独立应用、应用列表与自定义 operation 运行入口。"""

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from sr_od.backend import operation_flow, operation_registry
from sr_od.backend.backend_context import SrBackendContext
from sr_od.backend.schemas import ApplicationListResult, ApplicationListResultOut

if TYPE_CHECKING:
    from one_dragon.base.operation.operation_base import OperationResult


def make_run_one_dragon(backend: SrBackendContext) -> Callable:
    """构造 ``run_one_dragon`` tool。"""
    async def run_one_dragon(
        block: Annotated[bool, Field(description="False=立刻返回用 get_run_status 查进度(默认);True=阻塞到一条龙结束")] = False,
    ) -> dict:
        """按当前 GUI/配置的一条龙设置启动完整一条龙运行。长耗时(全套应用,可达小时级)。操作类(会控制游戏)。

        跑全套已启用应用用本 tool;单个应用用 run_standalone_app;单个 operation
        用 run_operation。单跑道:同一时间只允许一个运行,已有运行时返回拒绝
        (含 source 与提示)。
        """
        try:
            ok, future = backend.run_one_dragon('mcp')
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'started': False, 'error': str(e)}
        if not ok:
            # 拒绝响应区分「本进程已有 run」与「游戏窗口被他进程占用」,方便归因。
            return backend.run_refusal_response('先 get_run_status 查状态,或 stop_run 停止')
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
        """启动单个独立应用。操作类(会控制游戏)。

        单个应用用本 tool;全套用 run_one_dragon;单个 operation 用 run_operation。
        可运行应用清单用 list_applications 查。单跑道,已有运行时返回拒绝
        (含 source 与提示)。
        """
        try:
            ok, future = backend.run_standalone_app('mcp', app_id=app_id)
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'started': False, 'error': str(e)}
        if not ok:
            # 拒绝响应区分「本进程已有 run」与「游戏窗口被他进程占用」,方便归因。
            return backend.run_refusal_response('先 get_run_status 查状态,或 stop_run 停止')
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


def make_list_applications(backend: SrBackendContext) -> Callable[[], ApplicationListResultOut | dict]:
    """构造 ``list_applications`` tool。"""
    def list_applications() -> ApplicationListResultOut | dict:
        """列出当前实例可运行应用、独立应用列表和当前选中项。观察类(只读,不刷新配置)。

        列应用用本 tool;列可运行 operation 用 list_operations。
        """
        try:
            result = backend.list_applications()
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'error': str(e)}
        return ApplicationListResultOut.from_backend(result) if isinstance(result, ApplicationListResult) else result
    return list_applications


def make_list_operations(backend: SrBackendContext) -> Callable[..., dict]:
    """构造 ``list_operations`` tool(自定义 operation 运行入口)。"""
    def list_operations(
        query: Annotated[str, Field(description="子串过滤 op_id(大小写不敏感),如 'move'/'battle';空=全量")] = "",
    ) -> dict:
        """列出可运行的自定义 operation 的定位符清单。观察类(纯反射,不实例化,不改任何状态)。

        只返回定位符不含参数 schema——参数详情用 describe_operation 查;列应用
        用 list_applications。定位符可直接传给 describe_operation / run_operation:
        类名无同名冲突时为类名短名(如 MoveDirectly),有同名冲突时为完整 op_id
        (含点),无需区分。failures[] 为单模块 import 失败记录,不影响其余结果。
        """
        try:
            result = operation_registry.scan_operations(backend.ctx)
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'error': str(e)}
        return operation_registry.compact_operation_list(result, query)
    return list_operations


def make_describe_operation(backend: SrBackendContext) -> Callable[[str], dict]:
    """构造 ``describe_operation`` tool(自定义 operation 运行入口)。"""
    def describe_operation(
        op_id: Annotated[str, Field(description="operation 定位标识 <module>.<ClassName>,可从 list_operations 获取;也可只传类名短名(如 MoveDirectly),命中多个同名类时全部返回")],
    ) -> dict:
        """描述单个 operation 的参数 schema。观察类(纯反射,不实例化,不改任何状态)。

        op_id 短名命中多个同名类时返回全部候选(ambiguous=True),未找到时附
        相似类名建议。返回的 docstring 是该 op 的语义唯一来源(做什么/起终点
        画面/副作用/参数语义);params[] 元素的 json_serializable 标记能否直接
        传 JSON 值,coercible 标记可传 dict 由 run_operation 自动反序列化。
        """
        try:
            return operation_registry.describe_operation(backend.ctx, op_id)
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'error': str(e)}
    return describe_operation


def make_describe_operation_flow(backend: SrBackendContext) -> Callable[[str, bool], dict]:
    """构造 ``describe_operation_flow`` tool(自定义 operation 运行入口)。

    核心函数纯反射不依赖 backend.ctx,签名保留 backend 与既有工厂对齐
    (挂接层统一注入模式);MCP / HTTP 同契约走同一核心函数。
    """
    def describe_operation_flow(
        op_id: Annotated[str, Field(description="operation 定位标识 <module>.<ClassName>,可从 list_operations 获取;也可只传类名短名(如 MoveDirectly);完整形态实时解析,接受任意 Operation 子类含 Application")],
        mermaid: Annotated[bool, Field(description="True 时额外返回 mermaid 字段(flowchart 源码,渲染交给客户端);默认 False 不占返回体")] = False,
    ) -> dict:
        """查看单个 operation 的节点流转图(节点/边/诊断)。观察类(纯反射,不实例化,不改任何状态)。

        describe_operation 看参数 schema,本 tool 看节点怎么流转(怎么走/失败走哪/
        收尾在哪),两者互补;改 op 前先看图了解现状,改完再看图核对。纯静态提取
        零副作用,可在运行前发现断名边/多起点等编排错误。短名查不到属预期
        (App 类不进扫描缓存),改用完整 op_id。返回字段语义随结果自解释:
        diagnostics 的 error=运行时必炸或图不成立,warn=结构可疑不致命。
        """
        try:
            return operation_flow.describe_operation_flow(op_id, mermaid=mermaid)
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'error': str(e)}
    return describe_operation_flow


def make_run_operation(backend: SrBackendContext) -> Callable:
    """构造 ``run_operation`` tool(自定义 operation 运行入口)。

    按 op_id 运行任意 operation;args 以构造参数 ``cls(ctx, **args)`` 烤进闭包。
    resolve_op_class + validate_args 在调用方线程先校验,通过后才提交单跑道运行槽。
    """
    async def run_operation(
        op_id: Annotated[str, Field(description="operation 定位标识 <module>.<ClassName>,可从 list_operations 获取;也可只传类名短名(如 MoveDirectly),命中多个同名类时报错并列出候选")],
        args: Annotated[dict | None, Field(description="构造参数 dict;JSON 标量/列表/字典;@dataclass+from_dict 参数及其 Optional/list/dict 容器形态传对应 JSON 结构(dict/list[dict]),实例化前自动规整;tuple/set 参数传 list 自动转换;其余复杂数据类走 application")] = None,
        block: Annotated[bool, Field(description="False=立刻返回用 get_run_status 查进度(默认);True=阻塞到结束")] = False,
    ) -> dict:
        """按 op_id(package.path.ClassName)或类名短名运行任意 operation;args 传构造参数。操作类(会控制游戏)。

        单个 operation 用本 tool;全套用 run_one_dragon;单个应用用
        run_standalone_app。短名命中多个同名类时拒绝并列出候选(防误运行);
        复杂参数先用 describe_operation 看参数与传法。单跑道,已有运行时返回
        拒绝(含 source 与提示)。block=True 终态的 data 字段是 op 的数据通道
        (读数类 op 携带结果,无数据为 null)。
        """
        try:
            cls = operation_registry.resolve_unique_op(op_id)
            err = operation_registry.validate_args(cls, args or {})
            if err:
                return {'started': False, 'error': err}
            # 闭包把 cls + args bake 进 op_factory(槽只认统一签名 op_factory(ctx) → Operation)
            def op_factory(ctx):  # noqa: ANN202 闭包签名固定 Callable[[SrContext], Operation]
                # 参数值规整为注解形态(dataclass from_dict 及其 Optional/容器级,tuple/set 的 list 转换)
                coerced_args = operation_registry.coerce_params(cls, args or {})
                return cls(ctx, **coerced_args)
            # display_name 用解析后的完整 op_id:短名传入时也能在运行状态/日志定位到具体 op
            ok, future = backend.run_slot._start(
                'mcp', op_factory=op_factory,
                display_name=f'{cls.__module__}.{cls.__name__}',
            )
        except Exception as e:  # noqa: BLE001 工具层兜底(resolve/validate/_start 异常)
            return {'started': False, 'error': str(e)}
        if not ok:
            # 拒绝响应区分「本进程已有 run」与「游戏窗口被他进程占用」,方便归因。
            return backend.run_refusal_response('先 get_run_status 查状态,或 stop_run 停止')
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
        # data 是 op 的数据通道(读数类 op 如 ReadWarpStatusOp 把结果放这里);
        # 无数据的 op 为 None,不占输出
        return {'success': result.success,
                'result': 'operation 运行成功' if result.success else f'operation 运行失败: {result.status}',
                'data': result.data}
    return run_operation
