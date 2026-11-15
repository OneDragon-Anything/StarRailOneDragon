"""MCP 适配器：把 ``SrBackendContext`` 以 MCP tool 的形式对外暴露。

本模块在后端 game 切片（``SrBackendContext``）之上架设一层传输适配：
- ``create_mcp_server`` 创建一个 ``FastMCP`` 实例，并通过闭包将 backend 注入到
  工具函数中，使工具调用最终落到 backend 的 game 切片方法上。
- 工具返回值尽量保持「可直接读」的字符串或传输无关结构，便于上层（CLI/Agent）消费。

注意：
    - 同步工具（check/capture/analyze）直接调用 backend 的同步方法；
    - ``open_game`` 为异步长耗时操作，基于 ``backend.start_run`` 适配，
      ``block=True`` 阻塞到完成、``block=False`` 立刻返回。
    - 运行类 tool 工厂（``make_open_game`` 等）为模块级函数，
      只调 backend 公开方法，不戳 run_slot 私有，便于独立测试。
    - 增减 MCP method（新增/删除 tool）后需客户端 /mcp 重连才能拿到新工具清单。

tool 写法（annotations / Field / 返回 / docstring）遵循
``docs/develop/sr_od/backend/mcp-implementation.md``。
"""

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from one_dragon.base.controller.stop_guard import StopRunInterrupted
from one_dragon.utils.log_utils import log
from sr_od.backend.backend_context import SrBackendContext, _save_screenshot
from sr_od.backend.mcp.character_tools import register_character_tools
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
    RunStatusOut,
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
    ) -> dict:
        """打开游戏(可选自动登录)。长耗时,需交互式桌面。操作类(会启动游戏进程,可能登录)。

        单跑道:同一时间只允许一个运行,已有运行时返回拒绝。
        """
        from sr_od.operations.enter_game.open_and_enter_game import OpenAndEnterGame
        from sr_od.operations.enter_game.open_game import OpenGame
        op_factory = (lambda ctx: OpenGame(ctx)) if not enter else (lambda ctx: OpenAndEnterGame(ctx))
        ok, future = backend.start_run('mcp', op_factory)
        if not ok:
            # 拒绝响应区分「本进程已有 run」与「游戏窗口被他进程占用」,方便归因。
            return backend.run_refusal_response('先 get_run_status 查状态,或 stop_run 停止')
        if not block:
            st = backend.query_status()
            return {
                'started': True,
                'source': 'mcp',
                'started_at': st.started_at,
                'hint': '用 get_run_status 查进度与结果',
            }
        result: OperationResult = await asyncio.wrap_future(future)  # 中断 cancel 的是 await,底层 _run 继续
        if enter:
            msg = '成功打开并进入星穹铁道游戏' if result.success else f'打开游戏失败: {result.status}'
        else:
            msg = '成功打开游戏(未登录)' if result.success else f'打开游戏失败: {result.status}'
        return {'success': result.success, 'result': msg}
    return open_game


def make_get_run_status(backend: SrBackendContext) -> Callable[[], RunStatusOut]:
    """构造 ``get_run_status`` tool(模块级,便于独立测试)。"""
    def get_run_status() -> RunStatusOut:
        """查询当前/最近一次运行状态(运行中返当前节点/耗时/重试,终态返结果/失败定位)。
        观察类(只读,无副作用)。停止运行用 stop_run。
        """
        return RunStatusOut.from_backend(backend.query_status())
    return get_run_status


def make_stop_run(backend: SrBackendContext) -> Callable[[], dict]:
    """构造 ``stop_run`` tool(模块级,便于独立测试)。"""
    def stop_run() -> dict:
        """向正在运行的 operation 发出停止信号(当前节点完成后退出,非强杀)。操作类。

        返回仅表信号已发——过渡期 get_run_status 仍显示 running,以其离开
        running 为准。
        """
        return backend.stop()
    return stop_run


def create_mcp_server(backend: SrBackendContext, name: str = "sr_od") -> FastMCP:
    """创建 MCP 服务器并注册 game 工具与 prompt。

    通过闭包将 ``backend`` 注入到各工具函数中，使工具调用最终落到 backend 的
    game 切片方法（``check_window``/``capture``/``analyze``）；运行类操作
    （``open_game``/``get_run_status``/``stop_run``）经模块级工厂
    构造后用 ``mcp.tool()(...)`` 注册。

    Args:
        backend: 已就绪的 ``SrBackendContext``，提供 game 切片能力。
        name: MCP 服务器名称，默认 ``sr_od``。

    Returns:
        注册好工具的 ``FastMCP`` 实例。
    """
    mcp = FastMCP(name, instructions=render_instructions())

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="检查游戏窗口"))
    def check_game_window() -> WindowStatusOut:
        """检查星穹铁道游戏窗口状态。观察类(只读,不改任何状态)。

        判断游戏是否在跑/窗口是否存在,看 is_win_valid——勿据 win_title 判断。
        """
        return WindowStatusOut.from_backend(backend.check_window())

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="捕获游戏截图"))
    def capture_game_screen() -> str:
        """捕获游戏画面并保存截图,返回截图文件绝对路径。观察类(只读,不改任何状态)。

        仅在「只要截图文件本身」时用(存档证据 / 喂视觉大模型);要识别画面内容
        直接调 analyze_screen——它自己截图自己分析,先走本 tool 再传路径是多一次
        往返,且两次截图间画面可能已变。
        """
        path = _save_screenshot(backend.capture())
        log.info(f"截图已保存到: {path}")
        return path

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
    ) -> dict:
        """录屏(**dev-only**)。观察类(只读,不占单跑道,可与 bot run 并行)。需 dev 依赖 imageio-ffmpeg。

        ffmpeg gdigrab 采集,能录游戏画面;编码器自动探测(h264_nvenc 优先,回退
        libx264),结果带 encoder 字段;imageio-ffmpeg 缺失时返回提示,不影响 server。
        典型流程:mode='start' 开录 → 跑 bot → mode='stop' 收尾(start 为
        fragmented mp4,中途被 kill 也安全可播)。

        Returns:
            dict: ``{success, path?(文件路径), pid?(start 模式进程号), action,
            error?, hint?, encoder?(编码器), returncode?}``。
        """
        try:
            return backend.record_screen(mode, duration, out_name, fps, capture, bitrate)
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(title="增改画面区域"))  # 操作类:改 screen_info(写 yml + reload)
    def upsert_screen_area(
        screen_name: str, area_name: str,
        pc_rect: Annotated[list[int], Field(description="area 矩形 [x1,y1,x2,y2];模板 bbox 建议每边 +10px")],
        text: str = '', lcs_percent: float = 0.5,
        template_sub_dir: str = '', template_id: str = '', template_match_threshold: float = 0.7,
        color_range: list[list[int]] | None = None, goto_list: list[str] | None = None,
        id_mark: bool = False, gamepad_key: str | None = None,
    ) -> dict:
        """按 area_name 在指定 screen 插入或更新一个 area(写 yml + reload,下次 analyze_screen 即生效)。
        操作类(改画面建档,不碰游戏运行时),无需游戏在线。

        area_name 存在则整体更新,不存在则追加;写前校验 screen 存在、area_name
        非空、pc_rect 合法、模板引用存在(template_id 非空时)。pc_alt 是 screen
        级属性(create_screen 设置),area 不单设。
        """
        try:
            return backend.upsert_screen_area(
                screen_name, area_name, pc_rect, text, lcs_percent,
                template_sub_dir, template_id, template_match_threshold,
                color_range, goto_list, id_mark, gamepad_key,
            )
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'screen_name': screen_name, 'area_name': area_name,
                    'action': None, 'area_count': None, 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True, title="删除画面区域"))  # 操作类+不可逆:删 screen_info area
    def delete_screen_area(screen_name: str, area_name: str) -> dict:
        """按 area_name 删除指定 screen 的一个 area(写 yml + reload,不可逆)。操作类。

        下次 analyze_screen 即生效。
        """
        try:
            return backend.delete_screen_area(screen_name, area_name)
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'screen_name': screen_name, 'area_name': area_name,
                    'action': None, 'area_count': None, 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(title="新建画面"))  # 操作类:建新 screen_info(写 yml + reload)
    def create_screen(
        screen_id: Annotated[str, Field(description="画面 ID,英文 snake_case,作 yml 文件名(如 currency_war_lobby)")],
        screen_name: Annotated[str, Field(description="画面名,中文,作 get_screen / analyze 的 key(如 货币战争-大厅)")],
        app_id: str = '',
        pc_alt: bool = False,
    ) -> dict:
        """创建一个新画面(空 area_list;写 yml + reload)。操作类(改画面建档),无需游戏在线。

        screen_id 不与既有冲突,screen_name 唯一;创建后用 upsert_screen_area 加 area。
        """
        try:
            return backend.create_screen(screen_id, screen_name, app_id, pc_alt)
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'screen_id': screen_id, 'screen_name': screen_name,
                    'action': None, 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="列出画面名"))
    def list_screen_names() -> dict:
        """列出全部画面名(排序全量)。观察类(只读),无需游戏在线。

        screen_name 是画面建档的匹配键(中文,须完全一致),goto_screen /
        get_screen_detail / upsert_screen_area 的定位入参都从这里查。
        """
        try:
            return backend.list_screen_names()
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'count': 0, 'screen_names': [], 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="读取画面档全集"))
    def get_screen_detail(
        screen_name: Annotated[str, Field(description="画面名,与 screen_info 的 screen_name 完全一致(如 邮件)")],
    ) -> str:
        """读取单个画面档全集:全部 area(含 goto_list)+ 路由可达邻居,自解释 markdown。
        观察类(只读),无需游戏在线。

        analyze_screen 只回当前帧命中;本方法回建档全集——核对画面建档、
        查「从这里能 goto 到哪」、建档补漏用。
        """
        try:
            result = backend.get_screen_detail(screen_name)
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            result = {'success': False, 'screen_name': screen_name, 'screen_id': None,
                      'pc_alt': None, 'area_count': 0, 'areas': [], 'goto_neighbors': [],
                      'error': str(e)}
        return render_screen_detail(result)

    @mcp.tool(annotations=ToolAnnotations(title="按路由导航画面"))  # 操作类:实际点击游戏
    def goto_screen(
        target_screen_name: Annotated[str, Field(description="目标画面名,与 screen_info 的 screen_name 完全一致(如 邮件)")],
        max_steps: Annotated[int, Field(description="最多点击次数,防路由成环", ge=1, le=30)] = 10,
    ) -> dict:
        """沿画面建档的路由边自动导航到目标画面(实际点击游戏)。操作类(会控制游戏)。

        识别当前画面 → 查路由 → 逐边点击;报「无路径」= 跳转边未建档(补 area
        的 goto_list,别硬试坐标)。跳转边如实记录(含不可逆/消耗类出口),
        本工具不做安全过滤,路径安全由调用方负责。
        """
        try:
            return backend.goto_screen(target_screen_name, max_steps)
        except StopRunInterrupted:
            # 同 click_game:BaseException 按名收尾,防穿透 ASGI(防御纵深;
            # backend 层另有按名收尾,双保险)。
            return {'success': False, 'current_screen': None, 'target_screen': target_screen_name,
                    'steps': [], 'error': '运行已被停机中断(守卫拦截本次导航点击)'}
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'current_screen': None, 'target_screen': target_screen_name,
                    'steps': [], 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True, title="关闭游戏"))  # 操作类+破坏性:关游戏
    def close_game() -> str:
        """关闭游戏窗口(发关闭信号,秒级)。操作类,破坏性(游戏会被关闭)。

        返回只表「信号已发」非已关闭——用 check_game_window 验证是否真关。
        """
        try:
            return backend.close_game()
        except StopRunInterrupted as e:
            # BaseException 不能裸透传(FastMCP/Starlette 只接 Exception,穿透即连接断):
            # 按名转普通异常走错误通道(防御纵深;手动端点已在 backend 层豁免,正常不达)
            raise RuntimeError('运行已被停机中断(守卫拦截本次操作)') from e

    @mcp.tool(annotations=ToolAnnotations(title="点击游戏坐标"))  # 操作类:操作游戏点击(非破坏)
    def click_game(
        x: float, y: float,
        press_time: Annotated[float, Field(description="按住时长(秒);默认 0.1(游戏识别下限,0=极短按可能无效)")] = 0.1,
        pc_alt: Annotated[bool, Field(description="点击前是否按住 Alt 解锁光标;大世界等 pc_alt=true 画面必需,其余 False")] = False,
    ) -> dict:
        """点击游戏窗口内坐标(取画面建档 pc_rect 中心)。操作类(会控制游戏),需游戏窗口就绪。

        鼠标点击用本 tool;键盘按键用 key_tap;拖拽用 drag。坐标经控制器缩放到
        真实屏幕;不在窗口内则不点击(in_window=False)。大世界等锁光标画面
        点击会落空,需传 pc_alt=True 解锁光标(画面是否锁光标看建档的 pc_alt)。

        ⚠️ 底层无内置等待:点 UI 常触发画面切换(菜单/弹窗/进画面),连续操作或
        截图前建议 sleep ~1s 等动画(否则截过渡帧)。
        """
        try:
            return backend.click_game(x, y, press_time, pc_alt)
        except StopRunInterrupted:
            # 停机守卫异常是 BaseException,下方泛型 except Exception 接不住;
            # 不按名收尾会穿透 FastMCP → Starlette ServerErrorMiddleware
            # (同样只接 Exception)→ ASGI 层错误 + 连接断,客户端拿不到
            # 结构化错误。正常路径不应到达此处(手动端点在 backend 层已
            # stop_guard_exemption 豁免)——本兜底是防御纵深:未来新增端点
            # 忘记豁免时,客户端仍拿到可读错误而非连接断。
            return {'success': False, 'x': x, 'y': y, 'in_window': False, 'pc_alt': pc_alt,
                    'error': '运行已被停机中断(守卫拦截本次输入)'}
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'success': False, 'x': x, 'y': y, 'in_window': False, 'pc_alt': pc_alt, 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(title="键盘按键"))  # 操作类:键盘输入(非破坏)
    def key_tap(
        key: Annotated[str, Field(description="框架键名:w/a/s/d 移动、f 交互、esc、space 等(沿用框架 btn_controller 约定)")],
        press_time: Annotated[float, Field(description="按住时长(秒);0=短按 tap,>0=长按(如移动长按 1-2s)")] = 0.0,
    ) -> dict:
        """向游戏发送键盘按键(短按/长按)。操作类(会控制游戏),需游戏窗口就绪。

        键盘按键用本 tool;鼠标点击用 click_game;拖拽用 drag。

        ⚠️ 底层无内置等待:移动 wasd ~1s 等角色到位、交互 f ~1-2s 进场景/对话、
        esc ~0.5s 开关菜单,连续操作前按需 sleep。
        """
        try:
            return backend.key_tap(key, press_time)
        except StopRunInterrupted:
            # 同 click_game:BaseException 按名收尾,防穿透 ASGI(防御纵深)。
            return {'success': False, 'key': key, 'press_time': press_time,
                    'error': '运行已被停机中断(守卫拦截本次输入)'}
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'success': False, 'key': key, 'press_time': press_time, 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(title="鼠标拖拽"))  # 操作类:鼠标拖拽(非破坏)
    def drag(
        x1: float, y1: float, x2: float, y2: float,
        duration: Annotated[float, Field(description="拖拽耗时(秒),默认 1.0")] = 1.0,
    ) -> dict:
        """鼠标按住拖拽 (x1,y1)→(x2,y2)。操作类(会控制游戏),需游戏窗口就绪。

        鼠标拖拽用本 tool;点击用 click_game;按键用 key_tap。列表滚动/翻页用
        拖拽实现,手指移动方向决定滚动方向(触摸语义:手指上滑=列表向深处翻页)。

        ⚠️ 底层无内置等待:拖后画面变化(刮/滚),连续操作或截图前建议 sleep ~0.5s。
        """
        try:
            return backend.drag(x1, y1, x2, y2, duration)
        except StopRunInterrupted:
            # 同 click_game:BaseException 按名收尾,防穿透 ASGI(防御纵深)。
            return {'success': False, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'duration': duration,
                    'error': '运行已被停机中断(守卫拦截本次输入)'}
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'success': False, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'duration': duration, 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(title="输入文本"))  # 操作类:文本输入(非破坏)
    def input_text(
        text: Annotated[str, Field(description="要输入的文本(账号/密码/兑换码等)")],
        use_clipboard: Annotated[bool | None, Field(description="None=跟随 game_config.type_input_way;True=强制剪贴板;False=强制逐键")] = None,
    ) -> dict:
        """向当前焦点输入框输入文本。操作类(会控制游戏),需游戏窗口就绪。

        需先用 click_game 点击输入框聚焦。返回的 masked_text 对密码类输入已打码。
        """
        try:
            return backend.input_text(text, use_clipboard)
        except StopRunInterrupted:
            # 同 click_game:BaseException 按名收尾,防穿透 ASGI(防御纵深)。
            return {'success': False, 'method': None, 'masked_text': None,
                    'error': '运行已被停机中断(守卫拦截本次输入)'}
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'success': False, 'method': None, 'masked_text': None, 'error': str(e)}

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
    register_light_cone_tools(mcp, backend)
    register_relic_tools(mcp, backend)
    register_game_config_tools(mcp, backend)
    register_prompts(mcp)
    register_prompt_tools(mcp)

    return mcp
