"""MCP 适配器：把 ``SrBackendContext`` 以 MCP tool 的形式对外暴露。

本模块在后端 game 切片（``SrBackendContext``）之上架设一层传输适配：
- ``create_mcp_server`` 创建一个 ``FastMCP`` 实例，并通过闭包将 backend 注入到
  工具函数中，使工具调用最终落到 backend 的 game 切片方法上。
- 工具返回值尽量保持「可直接读」的字符串或传输无关结构，便于上层（CLI/Agent）消费。

注意：
    - 同步工具（check/analyze）直接调用 backend 的同步方法；
    - ``open_game`` 为异步长耗时操作，基于 ``backend.start_run`` 适配，
      ``block=True`` 阻塞到完成、``block=False`` 立刻返回。
    - 运行类 tool 工厂（``make_open_game`` 等）为模块级函数，
      只调 backend 公开方法，不戳 run_slot 私有，便于独立测试。
    - 增减 MCP method（新增/删除 tool）后需客户端 /mcp 重连才能拿到新工具清单。
    - 运行模式（player/dev）由启动参数决定:玩家模式按 ``DEV_ONLY_TOOLS``
      名单隐藏维护类工具(全量注册后移除,注册代码与名单解耦)。
      设计见 docs/develop/sr_od/backend/changes/mcp-mode-split/design.md。

tool 写法（annotations / Field / 返回 / docstring）遵循
od-dev-write-backend skill（公共仓 OneDragon-Skills）。
"""

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from one_dragon.base.controller.stop_guard import StopRunInterrupted
from sr_od.backend.backend_context import RunState, SrBackendContext
from sr_od.backend.mcp.character_tools import register_character_tools
from sr_od.backend.mcp.cw_lookup_tools import register_cw_lookup_tools
from sr_od.backend.mcp.config_app import (
    make_add_config_item,
    make_delete_config_item,
    make_describe_config,
    make_get_config,
    make_list_app_configs,
    make_set_config,
    make_update_config_item,
)
from sr_od.backend.mcp.game_config_tools import register_game_config_tools
from sr_od.backend.mcp.light_cone_tools import register_light_cone_tools
from sr_od.backend.mcp.markdown_render import render_screen_detail
from sr_od.backend.mcp.modes import DEV_ONLY_TOOLS, MCP_MODE_DEV, MCP_MODE_PLAYER
from sr_od.backend.mcp.mys_tools import register_mys_tools
from sr_od.backend.mcp.prompts import (
    register_prompt_tools,
    register_prompts,
    render_instructions,
)
from sr_od.backend.mcp.relic_tools import register_relic_tools
from sr_od.backend.mcp.service_app import (
    make_describe_operation,
    make_describe_operation_flow,
    make_list_applications,
    make_list_operations,
    make_run_one_dragon,
    make_run_operation,
    make_run_standalone_app,
)
from sr_od.backend.schemas import (
    AnalyzeScreenOut,
    AreaMutationOut,
    GotoScreenOut,
    InputTextOut,
    RecordScreenOut,
    RunFinishOut,
    RunFinishResult,
    RunStartOut,
    RunStartResult,
    RunStatusOut,
    RunStopOut,
    ScreenCreateOut,
    ScreenNamesOut,
    WindowStatusOut,
)

if TYPE_CHECKING:
    from one_dragon.base.operation.operation_base import OperationResult


def make_open_game(backend: SrBackendContext) -> Callable:
    """构造 ``open_game`` tool(模块级,便于独立测试)。

    enter=True(默认)跑 ``OpenAndEnterGame``(打开+自动登录,到大世界);
    enter=False 跑 ``OpenGame``(打开+等窗口就绪,不登录)。
    """
    async def open_game(
        enter: Annotated[bool, Field(description="True=打开+自动登录到大世界;False=只打开停在 ready 态不登录")] = True,
        block: Annotated[bool, Field(description="True=阻塞到完成;False=立刻返回,用 get_run_status 查进度")] = True,
    ) -> RunStartOut | RunFinishOut:
        """打开游戏(可选自动登录)。长耗时,需交互式桌面。操作类(会启动游戏进程,可能登录)。

        单跑道:已有运行时受理被拒(RunStartRefusedError,可先 stop_run 再重试)。
        """
        from sr_od.operations.enter_game.open_and_enter_game import OpenAndEnterGame
        from sr_od.operations.enter_game.open_game import OpenGame
        op_factory = (lambda ctx: OpenGame(ctx)) if not enter else (lambda ctx: OpenAndEnterGame(ctx))
        ok, future = backend.start_run('mcp', op_factory)
        if not ok:
            raise backend.run_refusal_error('先 get_run_status 查状态,或 stop_run 停止')
        if not block:
            st = backend.query_status()
            return RunStartOut.from_backend(RunStartResult(app=st.app, started_at=st.started_at))
        result: OperationResult = await asyncio.wrap_future(future)  # 中断 cancel 的是 await,底层 _run 继续
        if enter:
            status = '成功打开并进入星穹铁道游戏' if result.success else f'打开游戏失败: {result.status}'
        else:
            status = '成功打开游戏(未登录)' if result.success else f'打开游戏失败: {result.status}'
        return RunFinishOut.from_backend(RunFinishResult(success=result.success, status=status))
    return open_game


def make_get_run_status(backend: SrBackendContext) -> Callable[..., RunStatusOut]:
    """构造 ``get_run_status`` tool(模块级,便于独立测试)。"""
    def get_run_status(
        include_screen: Annotated[bool, Field(
            description='True=运行中时截图识别当前画面(遍历建档画面,秒级耗时);'
                        '识别不到(过渡帧/未建档)为 null;终态不识别')] = True,
    ) -> RunStatusOut:
        """查询当前/最近一次运行状态(运行中返当前 op/节点/画面/耗时/重试,终态返结果/失败定位)。
        观察类(只读,无副作用)。停止运行用 stop_run。
        """
        st = RunStatusOut.from_backend(backend.query_status())
        if include_screen and st.state == RunState.RUNNING.value:
            st.current_screen = backend.recognize_current_screen()
        return st
    return get_run_status


def make_stop_run(backend: SrBackendContext) -> Callable[[], RunStopOut]:
    """构造 ``stop_run`` tool(模块级,便于独立测试)。"""
    def stop_run() -> RunStopOut:
        """向正在运行的 operation 发出停止信号(当前节点完成后退出,非强杀)。操作类。

        返回只表「信号已发」非已结束——过渡期 get_run_status 仍显示 running,
        以其离开 running 为准。stopped=False = 当前无运行(幂等结果,非错误)。
        """
        return RunStopOut.from_backend(backend.stop())
    return stop_run


def create_mcp_server(backend: SrBackendContext, name: str = "sr_od",
                      mode: str = MCP_MODE_PLAYER) -> FastMCP:
    """创建 MCP 服务器并注册 game 工具与 prompt。

    通过闭包将 ``backend`` 注入到各工具函数中，使工具调用最终落到 backend 的
    game 切片方法（``check_window``/``analyze``）；运行类操作
    （``open_game``/``get_run_status``/``stop_run``）经模块级工厂
    构造后用 ``mcp.tool()(...)`` 注册。

    Args:
        backend: 已就绪的 ``SrBackendContext``，提供 game 切片能力。
        name: MCP 服务器名称，默认 ``sr_od``。
        mode: 运行模式。``player``(默认)=按 ``DEV_ONLY_TOOLS`` 名单隐藏维护类
            工具;``dev``=全量暴露。由启动参数决定,进程级状态(切换需重启+客户端重连)。

    Returns:
        注册好工具的 ``FastMCP`` 实例。

    Raises:
        ValueError: ``mode`` 不在合法值内(fail-fast,不静默回退玩家)。
    """
    if mode not in (MCP_MODE_PLAYER, MCP_MODE_DEV):
        raise ValueError(f"未知 MCP 运行模式: {mode}(合法值: {MCP_MODE_PLAYER} / {MCP_MODE_DEV})")
    # 无状态模式:server 不发 session id,每请求独立 transport。规范(MAY assign)
    # 允许;本项目工具全一问一答、无 server 主动推送需求,而开发期改代码重启 server
    # 是常态,有状态会话的凭证存进程内存,重启即作废且客户端(ZCode)不按规范对
    # 404 重新握手,每次重启都要手动恢复连接——无状态从根上免疫。
    mcp = FastMCP(name, instructions=render_instructions(), stateless_http=True)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="检查游戏窗口"))
    def check_game_window() -> WindowStatusOut:
        """检查星穹铁道游戏窗口状态。观察类(只读,不改任何状态)。

        判断游戏是否在跑/窗口是否存在,看 is_win_valid——勿据 win_title 判断。
        """
        return WindowStatusOut.from_backend(backend.check_window())

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="分析游戏画面"))
    def analyze_screen(
        screenshot: Annotated[str | None, Field(description="截图来源:None=实时截当前画面(需游戏在线);传路径=读该图(无需游戏在线);纯名字=读 .debug/images/<名字>.png")] = None,
        save_image: Annotated[bool, Field(description="仅实时模式:把截图落盘并回传 screenshot_path 供视觉模型复用;离线模式忽略")] = False,
        include_ocr: Annotated[bool, Field(description="是否返回全量散落 OCR 文本(未归类到任何 area 的);默认 False 只回画面匹配+area 命中,读屏幕上的零散文字时才开")] = False,
    ) -> AnalyzeScreenOut:
        """基于已探索的画面信息(screen_info)，通过 OCR 和图像算法，识别游戏画面的内容。观察类(只读,不改游戏状态)。

        - 识别内容为确认过的游戏语义，相信返回内容的语义说明；
        - 依然存在未建档，或传统算法不方便识别的内容未在本方法返回；
        - 因此，识别内容不代表画面的全部，依然要使用大模型读取图片进行完整理解；
        - 返回坐标是精准坐标，相信本方法坐标而不是大模型读图的目测坐标。
        """
        return AnalyzeScreenOut.from_backend(backend.analyze(screenshot, save_image, include_ocr))

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="录屏(dev)"))
    def record_screen(
        mode: Annotated[str, Field(description="'fixed'=录 duration 秒自停(默认,阻塞返回);'start'=后台开始(返 pid);'stop'=停止收尾")] = 'fixed',
        duration: Annotated[float, Field(description="fixed 模式录制秒数")] = 10.0,
        out_name: Annotated[str, Field(description="输出文件名(存 .debug/record/)")] = 'rec',
        fps: Annotated[int, Field(description="帧率")] = 30,
        capture: Annotated[str, Field(description="'window'=游戏窗口(按句柄定位,窗口不在退回 desktop);'desktop'=全桌面")] = 'window',
        bitrate: Annotated[str, Field(description="目标码率,如 6M")] = '6M',
    ) -> RecordScreenOut:
        """录屏(**dev-only**)。观察类(只读,不占单跑道,可与 bot run 并行)。需 dev 依赖 imageio-ffmpeg。

        ffmpeg gdigrab 采集,能录游戏画面;编码器自动探测(h264_nvenc 优先,回退
        libx264),结果带 encoder 字段。
        典型流程:mode='start' 开录 → 跑 bot → mode='stop' 收尾(start 为
        fragmented mp4,中途被 kill 也安全可播)。
        """
        return RecordScreenOut.from_backend(
            backend.record_screen(mode, duration, out_name, fps, capture, bitrate))

    @mcp.tool(annotations=ToolAnnotations(title="增改画面区域"))  # 操作类:改 screen_info(写 yml + reload)
    def upsert_screen_area(
        screen_name: str, area_name: str,
        pc_rect: Annotated[list[int], Field(description="area 矩形 [x1,y1,x2,y2];模板 bbox 建议每边 +10px")],
        text: str = '', lcs_percent: float = 0.5,
        template_sub_dir: str = '', template_id: str = '', template_match_threshold: float = 0.7,
        color_range: list[list[int]] | None = None, goto_list: list[str] | None = None,
        id_mark: bool = False, gamepad_key: str | None = None,
    ) -> AreaMutationOut:
        """按 area_name 在指定 screen 插入或更新一个 area(写 yml + reload,下次 analyze_screen 即生效)。
        操作类(改画面建档,不碰游戏运行时),无需游戏在线。

        area_name 存在则整体更新,不存在则追加。pc_alt 是 screen 级属性
        (create_screen 设置),area 不单设。
        """
        return AreaMutationOut.from_backend(backend.upsert_screen_area(
            screen_name, area_name, pc_rect, text, lcs_percent,
            template_sub_dir, template_id, template_match_threshold,
            color_range, goto_list, id_mark, gamepad_key,
        ))

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True, title="删除画面区域"))  # 操作类+不可逆:删 screen_info area
    def delete_screen_area(screen_name: str, area_name: str) -> AreaMutationOut:
        """按 area_name 删除指定 screen 的一个 area(写 yml + reload,不可逆)。操作类。

        下次 analyze_screen 即生效。
        """
        return AreaMutationOut.from_backend(backend.delete_screen_area(screen_name, area_name))

    @mcp.tool(annotations=ToolAnnotations(title="新建画面"))  # 操作类:建新 screen_info(写 yml + reload)
    def create_screen(
        screen_id: Annotated[str, Field(description="画面 ID,英文 snake_case,作 yml 文件名(如 currency_war_lobby)")],
        screen_name: Annotated[str, Field(description="画面名,中文,作 get_screen / analyze 的 key(如 货币战争-大厅)")],
        app_id: str = '',
        pc_alt: bool = False,
    ) -> ScreenCreateOut:
        """创建一个新画面(空 area_list;写 yml + reload)。操作类(改画面建档),无需游戏在线。

        screen_id 不与既有冲突,screen_name 唯一;创建后用 upsert_screen_area 加 area。
        """
        return ScreenCreateOut.from_backend(backend.create_screen(screen_id, screen_name, app_id, pc_alt))

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="列出画面名"))
    def list_screen_names() -> ScreenNamesOut:
        """列出全部画面名(排序全量)。观察类(只读),无需游戏在线。"""
        return ScreenNamesOut(screen_names=backend.list_screen_names())

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="读取画面档全集"))
    def get_screen_detail(
        screen_name: Annotated[str, Field(description="画面名,与 screen_info 的 screen_name 完全一致(如 邮件)")],
    ) -> str:
        """读取单个画面档全集:全部 area(含 goto_list)+ 路由可达邻居,自解释 markdown。
        观察类(只读),无需游戏在线。

        analyze_screen 只回当前帧命中;本方法回建档全集——核对画面建档、
        查「从这里能 goto 到哪」、建档补漏用。
        """
        return render_screen_detail(backend.get_screen_detail(screen_name))

    @mcp.tool(annotations=ToolAnnotations(title="按路由导航画面"))  # 操作类:实际点击游戏
    def goto_screen(
        target_screen_name: Annotated[str, Field(description="目标画面名,与 screen_info 的 screen_name 完全一致(如 邮件)")],
        max_steps: Annotated[int, Field(description="最多点击次数,防路由成环", ge=1, le=30)] = 10,
    ) -> GotoScreenOut:
        """沿画面建档的路由边自动导航到目标画面(实际点击游戏)。操作类(会控制游戏)。

        报「无路径」= 跳转边未建档(补 area 的 goto_list,别硬试坐标)。
        跳转边如实记录(含不可逆/消耗类出口),本工具不做安全过滤,路径安全由
        调用方负责。arrived=False 是正常中断结果(带 current_screen/steps 现场
        与 reason 原因),非错误。
        """
        return GotoScreenOut.from_backend(backend.goto_screen(target_screen_name, max_steps))

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True, title="关闭游戏"))  # 操作类+破坏性:关游戏
    def close_game() -> str:
        """关闭游戏窗口(发关闭信号,秒级)。操作类,破坏性(游戏会被关闭)。

        返回只表「信号已发」非已关闭——用 check_game_window 验证是否真关。
        """
        try:
            return backend.close_game()
        except StopRunInterrupted as e:
            # BaseException 不能裸透传(FastMCP/Starlette 只接 Exception,穿透即连接断):
            # 按名转普通异常走错误通道。防御纵深:当前调用链是窗口关闭信号(非输入
            # 动作),不经过停机守卫检查点,本分支不可达;防未来改走守卫拦截路径。
            raise RuntimeError('运行已被停机中断(守卫拦截本次操作)') from e

    @mcp.tool(annotations=ToolAnnotations(title="点击游戏坐标"))  # 操作类:操作游戏点击(非破坏)
    def click_game(
        x: float, y: float,
        press_time: Annotated[float, Field(description="按住时长(秒);默认 0.1(游戏识别下限,0=极短按可能无效)")] = 0.1,
        pc_alt: Annotated[bool, Field(description="点击前是否按住 Alt 解锁光标;锁光标画面必需(看 analyze_screen 返回的 pc_alt),其余 False")] = False,
    ) -> bool:
        """点击游戏窗口内坐标(取画面建档 pc_rect 中心)。操作类(会控制游戏),需游戏窗口就绪。

        鼠标点击用本 tool;键盘按键用 key_tap;拖拽用 drag。坐标经控制器缩放到
        真实屏幕。返回 False = 坐标不在窗口内、未点击(正常结果,非错误)。
        大世界等锁光标画面点击会落空,需传 pc_alt=True 解锁光标(画面是否锁
        光标看 analyze_screen 返回的 pc_alt)。

        ⚠️ 底层无内置等待:点 UI 常触发画面切换(菜单/弹窗/进画面),连续操作或
        截图前建议 sleep ~1s 等动画(否则截过渡帧)。
        """
        try:
            return backend.click_game(x, y, press_time, pc_alt)
        except StopRunInterrupted as e:
            # 停机守卫异常是 BaseException,不能裸透传(FastMCP/Starlette 只接
            # Exception,穿透即 ASGI 错误 + 连接断)。手动端点在 backend 层已
            # stop_guard_exemption 豁免,本兜底是防御纵深:转普通异常走错误通道。
            raise RuntimeError('运行已被停机中断(守卫拦截本次输入)') from e

    @mcp.tool(annotations=ToolAnnotations(title="键盘按键"))  # 操作类:键盘输入(非破坏)
    def key_tap(
        key: Annotated[str, Field(description="框架键名:w/a/s/d 移动、f 交互、esc、space 等(沿用框架 btn_controller 约定)")],
        press_time: Annotated[float, Field(description="按住时长(秒);0=短按 tap,>0=长按(如移动长按 1-2s)")] = 0.0,
    ) -> str:
        """向游戏发送键盘按键(短按/长按),返回确认文案。操作类(会控制游戏),需游戏窗口就绪。

        键盘按键用本 tool;鼠标点击用 click_game;拖拽用 drag。

        ⚠️ 底层无内置等待:移动 wasd ~1s 等角色到位、交互 f ~1-2s 进场景/对话、
        esc ~0.5s 开关菜单,连续操作前按需 sleep。
        """
        try:
            return backend.key_tap(key, press_time)
        except StopRunInterrupted as e:
            # 同 click_game:BaseException 按名转普通异常,防穿透 ASGI(防御纵深)。
            raise RuntimeError('运行已被停机中断(守卫拦截本次输入)') from e

    @mcp.tool(annotations=ToolAnnotations(title="鼠标拖拽"))  # 操作类:鼠标拖拽(非破坏)
    def drag(
        x1: float, y1: float, x2: float, y2: float,
        duration: Annotated[float, Field(description="拖拽耗时(秒),默认 1.0")] = 1.0,
    ) -> str:
        """鼠标按住拖拽 (x1,y1)→(x2,y2),返回确认文案。操作类(会控制游戏),需游戏窗口就绪。

        鼠标拖拽用本 tool;点击用 click_game;按键用 key_tap。列表滚动/翻页用
        拖拽实现,手指移动方向决定滚动方向(触摸语义:手指上滑=列表向深处翻页)。

        ⚠️ 底层无内置等待:拖后画面变化(刮/滚),连续操作或截图前建议 sleep ~0.5s。
        """
        try:
            return backend.drag(x1, y1, x2, y2, duration)
        except StopRunInterrupted as e:
            # 同 click_game:BaseException 按名转普通异常,防穿透 ASGI(防御纵深)。
            raise RuntimeError('运行已被停机中断(守卫拦截本次输入)') from e

    @mcp.tool(annotations=ToolAnnotations(title="输入文本"))  # 操作类:文本输入(非破坏)
    def input_text(
        text: Annotated[str, Field(description="要输入的文本(账号/密码/兑换码等)")],
        use_clipboard: Annotated[bool | None, Field(description="None=跟随 game_config.type_input_way;True=强制剪贴板;False=强制逐键")] = None,
    ) -> InputTextOut:
        """向当前焦点输入框输入文本。操作类(会控制游戏),需游戏窗口就绪。

        需先用 click_game 点击输入框聚焦。
        """
        try:
            return InputTextOut.from_backend(backend.input_text(text, use_clipboard))
        except StopRunInterrupted as e:
            # BaseException 不能裸透传(FastMCP/Starlette 只接 Exception,穿透即连接断):
            # 按名转普通异常走错误通道(防御纵深;手动端点已在 backend 层豁免,正常不达)
            raise RuntimeError('运行已被停机中断(守卫拦截本次输入)') from e

    # 运行类 / 查询类工厂 tool:annotations(含 title)在注册时传(函数定义在 service_app.py)
    mcp.tool(annotations=ToolAnnotations(title="打开游戏"))(make_open_game(backend))
    mcp.tool(annotations=ToolAnnotations(title="运行一条龙"))(make_run_one_dragon(backend))
    mcp.tool(annotations=ToolAnnotations(title="运行独立应用"))(make_run_standalone_app(backend))
    mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="列出可运行应用"))(make_list_applications(backend))
    mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="查询运行状态"))(make_get_run_status(backend))
    mcp.tool(annotations=ToolAnnotations(title="停止运行"))(make_stop_run(backend))
    mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="列出可运行 operation"))(make_list_operations(backend))
    mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="查看 operation 参数"))(make_describe_operation(backend))
    mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="查看 operation 节点流转"))(make_describe_operation_flow(backend))
    mcp.tool(annotations=ToolAnnotations(title="运行 operation"))(make_run_operation(backend))
    # 配置修改工具(通用入口,按 app_id 路由到各 config 领域方法)
    mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="读取配置"))(make_get_config(backend))
    mcp.tool(annotations=ToolAnnotations(title="修改配置字段"))(make_set_config(backend))
    mcp.tool(annotations=ToolAnnotations(title="增改配置列表项"))(make_add_config_item(backend))
    mcp.tool(annotations=ToolAnnotations(destructiveHint=True, title="删除配置列表项"))(make_delete_config_item(backend))
    mcp.tool(annotations=ToolAnnotations(title="原位更新配置列表项"))(make_update_config_item(backend))
    mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="描述配置结构"))(make_describe_config(backend))
    mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="列出可改配置"))(make_list_app_configs(backend))
    # 米游社账号五工具（登录/登出/角色列表/名册明细/遗器词条评估；控制器单例在
    # 首次调用时装配，注册期不构建——backend 为测试替身时零副作用）
    register_mys_tools(mcp, backend)
    register_character_tools(mcp, backend)
    register_cw_lookup_tools(mcp, backend)  # 货币战争静态查询(角色/羁绊/装备;玩家面,backend 参数不消费)
    register_light_cone_tools(mcp, backend)
    register_relic_tools(mcp, backend)
    register_game_config_tools(mcp, backend)
    register_prompts(mcp)
    register_prompt_tools(mcp, mode)

    if mode == MCP_MODE_PLAYER:
        # 先全量注册再按名单移除(而非条件注册):注册代码零改动,名单是唯一分流依据。
        # 取交集再删:remove_tool 对未注册名抛 ToolError,名单含尚未存在的工具名
        # (如登记笔误)不炸启动,偏差由契约测试暴露。
        registered = set(mcp._tool_manager._tools.keys())
        for tool_name in DEV_ONLY_TOOLS & registered:
            mcp.remove_tool(tool_name)

    return mcp
