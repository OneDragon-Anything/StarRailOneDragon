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
from sr_od.backend.mcp.config_app import (
    make_add_config_item,
    make_delete_config_item,
    make_describe_config,
    make_get_config,
    make_list_app_configs,
    make_set_config,
)
from sr_od.backend.mcp.prompts import (
    register_prompt_tools,
    register_prompts,
    render_instructions,
)
from sr_od.backend.mcp.service_app import (
    make_describe_operation,
    make_list_applications,
    make_list_operations,
    make_run_one_dragon,
    make_run_operation,
    make_run_standalone_app,
)
from sr_od.backend.schemas import AnalyzeScreenResult, RunStatusResult, WindowStatus

if TYPE_CHECKING:
    from one_dragon.base.operation.operation_base import OperationResult


def make_open_game(backend: SrBackendContext) -> Callable:
    """构造 ``open_game`` tool(模块级,便于独立测试)。

    enter=True(默认)跑 ``OpenAndEnterGame``(打开+自动登录,到大世界);
    enter=False 跑 ``OpenGame``(打开+等窗口就绪,停在打开游戏 ready 态,不登录)。
    其余 block/并发语义同原 ``open_and_enter_game``。
    """
    async def open_game(
        enter: Annotated[bool, Field(description="True=打开+自动登录到大世界;False=只打开停在 ready 态不登录")] = True,
        block: Annotated[bool, Field(description="True=阻塞到完成;False=立刻返回,用 get_run_status 查进度")] = True,
    ) -> dict:
        """打开游戏(可选自动登录)。长耗时,需交互式桌面。操作类。

        enter=True(默认)→ 打开 + 自动登录(= 原 open_and_enter_game,到大世界);
        enter=False → 只打开 + 等窗口就绪,停在「打开游戏」ready 态(不登录),
        供调用方分步驱动登录流程。
        block=True(默认)阻塞到完成;block=False 立刻返回,用 get_run_status 查进度。
        副作用:操作游戏(启动 exe / 可能登录);单跑道,已有运行时返回错误(含 source + 提示)。

        Returns:
            三种形态:① 并发拒绝 dict ``{started: False, error, source, hint}``;
            ② 受理 dict ``{started: True, source, started_at, hint}``(block=False);
            ③ block=True 终态 dict ``{success: bool, result: <结果文本>}``。
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


def make_get_run_status(backend: SrBackendContext) -> Callable[[], RunStatusResult]:
    """构造 ``get_run_status`` tool(模块级,便于独立测试)。"""
    def get_run_status() -> RunStatusResult:
        """查当前/最近一次运行状态(无副作用)。观察类。

        运行中返当前节点/耗时/重试;非运行返结果/失败定位。停止运行用 ``stop_run``。

        Returns:
            ``RunStatusResult``: ``{state, source, app, started_at, duration_seconds,
            current_node, retry_count, last_status, failed_node}``。
            ``state`` 取值 ``idle``(无运行)/``running``/``success``/``failed``/``stopped``;
            ``current_node``/``retry_count`` 仅运行中有值;``last_status`` 仅终态有值
            (成功描述 / 失败原因 / ``已停止[来源]``(来源=stop_source,如
            ``mcp:stop_run`` / ``hook:*`` / ``gui:*``));``failed_node`` 仅 failed 时有值
            (失败停在哪一步,排障锚点);``started_at`` 为 ISO 时间戳,可作 tail 日志锚点。
        """
        return backend.query_status()
    return get_run_status


def make_stop_run(backend: SrBackendContext) -> Callable[[], dict]:
    """构造 ``stop_run`` tool(模块级,便于独立测试)。"""
    def stop_run() -> dict:
        """发出停止信号,operation 在当前节点完成后退出(非强杀)。操作类。

        返回仅表信号已发出(过渡期 get_run_status 仍显示 running)。
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
    def check_game_window() -> WindowStatus | dict:
        """检查星穹铁道游戏窗口状态(只读,不改状态)。观察类。

        返回窗口标题、有效性、激活态、缩放比例及客户区矩形(与 HTTP ``/game/window`` 同构)。

        Returns:
            ``WindowStatus``(win_title / is_win_valid / is_win_active / is_win_scale /
            x / y / width / height;位置字段不可用时为 None);backend 抛错时返回
            ``{'error': <原因>}``。

            判游戏是否在跑/窗口是否存在,看 ``is_win_valid``:**勿据 win_title 判断** ——
            win_title 是 controller 缓存的预期标题(从配置来),游戏未启动时仍可能为该
            预期常量、非 None;is_win_valid=False 才表示没找到匹配窗口。
        """
        try:
            return backend.check_window()
        except Exception as e:  # noqa: BLE001 工具层统一兜底，避免异常透传到 MCP 框架
            return {'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="捕获游戏截图"))
    def capture_game_screen() -> dict:
        """捕获游戏画面并保存截图,返回结构化结果。观察类。

        **仅在「只要截图文件本身、不做画面分析」时用本 tool**(如存档证据 / 喂视觉大模型)。
        要知道画面是什么(OCR / 画面匹配)直接调 ``analyze_screen`` —— 它默认自己截图自己分析,
        不需要也不应该先走本 tool。

        Returns:
            ``{success: True, path: 截图文件绝对路径}``;backend 抛错时
            ``{success: False, error: <原因>}``。
        """
        try:
            image = backend.capture()
            path = _save_screenshot(image)
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'error': str(e)}
        log.info(f"截图已保存到: {path}")
        return {'success': True, 'path': path}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="分析游戏画面"))
    def analyze_screen(
        screenshot: Annotated[str | None, Field(description="截图来源:None=实时截当前画面(需游戏在线);传路径=读该图(无需游戏在线);纯名字=读 .debug/images/<名字>.png")] = None,
        save_image: Annotated[bool, Field(description="仅实时模式:把截图落盘并回传 screenshot_path 供视觉模型复用;离线模式忽略")] = False,
        include_ocr: Annotated[bool, Field(description="是否返回全量散落 OCR 文本(未归类到任何 area 的);默认 False 只回画面匹配+area 命中,读屏幕上的零散文字时才开")] = False,
    ) -> AnalyzeScreenResult:
        """识别层的客观回读:画面身份判定 + area 命中坐标 + 结构化数据。观察类,不改游戏状态。

        **定位分工(当前模型有原生视觉,本工具不再是「眼睛」)**:
        - 「看懂画面」(布局 / 图标语义 / 状态 / 未建档元素)→ 用你自己的视觉
          (``read_image`` 截图文件;实时分析加 ``save_image=True`` 拿路径直接看)。
        - 本工具管「**对账**」:①画面身份判定(对建档 screen_info 的确定性
          ``is_precise`` 匹配,bot 运行时同源);②精确坐标与置信度(area 命中
          rect,定坐标/验坐标的 ground truth);③结构化领域数据(extras);
          ④零图像 token 的廉价轮询。视觉判读与本研究打架 = 建档漂移信号。
        - 典型连招:新画面先视觉看懂 → 建档 → 用本工具对账;已知画面轮询
          状态只调本工具(不带 save_image)。

        **默认用法:不带参数直接调用** —— 自动截当前游戏画面并分析(需游戏在线),
        **不要先调 capture_game_screen 再把路径传进来**(多一次往返,且两次截图间画面可能已变)。

        传 screenshot 仅用于**离线**场景(分析已存的历史截图,无需游戏在线):绝对路径
        按路径读 / 纯名字到 ``.debug/images/<名字>.png`` 读;**不回写**识别状态。
        用于离线校验/反哺 screen_info。

        Returns:
            ``AnalyzeScreenResult``:顶层字段 ``success`` / ``ocr_texts`` / ``screens`` /
            ``error`` / ``screenshot_path`` / ``vision_hint`` / ``extras`` / ``extras_doc``。
            决策优先看 ``screens``(精准命中 1 个 ``is_precise=True``;否则 top_n 个候选)。

            **坐标系:统一 1920×1080 游戏空间**——``ocr_texts[]``、``screens[].areas[]``
            的 x/y/width/height 与 ``unmatched_areas`` 的 ``pc_rect``、``click_game`` 点击
            坐标同源,可直接互喂(controller 截图统一缩放到 1080p 后才做 OCR/匹配)。
            **例外**:离线传入(``screenshot`` 参数)的**非 1080p 图片**未经缩放,返回坐标
            是该图自身像素空间,别当游戏坐标直接喂点击。

            嵌套结构:
            - ``ocr_texts[]``: ``{text, x, y, width, height}`` (1080p 游戏坐标);
              **默认空列表**,``include_ocr=True`` 才返回全量散落 OCR(未归类到任何
              area 的文本;读屏幕零散文字/校对文字区时开)。
            - ``screens[]``: ``{screen_name(中文), is_precise, areas[], unmatched_areas[]}``;
              ``unmatched_areas`` 仅精准命中时填充,``reason`` 取值 ``no_method``(纯定位区,
              无 OCR/模板,带 pc_rect 可点击) / ``sub_state``(有识别方法但当前不可见的
              子态区,带 text/template_id,用于判断当前子态);模糊候选恒为空。
            - ``areas[]``(命中详情): ``{area_name, area_type('text'|'template'), x, y,
              width, height(1080p 游戏坐标), text(仅文本区,实际命中文本), confidence(文本=OCR
              score / 模板=匹配度)}``。

            ``vision_hint``(success 时):本结果与视觉判读的分工提醒(本工具=识别对账;
            理解画面/未建档元素用视觉),非错误。

            ``extras``(精准命中时):若该画面注册了额外识别器(recognizer),带该画面的结构化
            领域事实(画面特定结构,如货币战争备战画面的前后台 / 备战席角色 + 金币 / 阶段);
            识别器异常不中断本结果(extras=None);无注册识别器的画面恒为 None。

            ``extras_doc``(与 extras 平级):extras 各字段的说明 dict(字段名 → 一行语义,
            含取值格式 / 读不到时的值 / 可靠性注意);有 extras 语义时直接读它,不必猜;
            无注册识别器 / 未声明时为 None。
        """
        try:
            return backend.analyze(screenshot, save_image, include_ocr)
        except Exception as e:  # noqa: BLE001 工具层统一兜底，避免异常透传到 MCP 框架
            return AnalyzeScreenResult(success=False, ocr_texts=[], screens=[], error=str(e))

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="录屏(NVENC,dev)"))
    def record_screen(
        mode: Annotated[str, Field(description="'fixed'=录 duration 秒自停(默认,阻塞返回);'start'=后台开始(返 pid);'stop'=停止收尾")] = 'fixed',
        duration: Annotated[float, Field(description="fixed 模式录制秒数")] = 10.0,
        out_name: Annotated[str, Field(description="输出文件名(存 .debug/record/)")] = 'rec',
        fps: Annotated[int, Field(description="帧率")] = 30,
        capture: Annotated[str, Field(description="'window'=游戏窗口(游戏不在退回 desktop);'desktop'=全桌面")] = 'window',
        bitrate: Annotated[str, Field(description="目标码率,如 6M")] = '6M',
    ) -> dict:
        """录屏(**dev-only**)。观察类,不占单跑道,可与 bot run 并行。需 dev 依赖 imageio-ffmpeg。

        ffmpeg gdigrab 采集 + h264_nvenc(NVIDIA GPU)硬编码,跑在本 server(Session 1),
        能录游戏画面。典型用法:① record_screen(mode='start', out_name='match01') → 跑 bot →
        record_screen(mode='stop');② record_screen(mode='fixed', duration=30) 录当前画面。
        imageio-ffmpeg 为延迟导入,缺失时本 tool 返回提示、不影响 server 启动。

        Returns:
            dict: ``{success, path?, pid?, action, error?, hint?}``。
        """
        try:
            return backend.record_screen(mode, duration, out_name, fps, capture, bitrate)
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(title="增改画面区域"))  # 操作类:改 screen_info(写 yml + reload)
    def upsert_screen_area(
        screen_name: str, area_name: str,
        pc_rect: Annotated[list[int], Field(description="area 矩形 [x1,y1,x2,y2],1080p 游戏坐标;模板 bbox 建议每边 +10px")],
        text: str = '', lcs_percent: float = 0.5,
        template_sub_dir: str = '', template_id: str = '', template_match_threshold: float = 0.7,
        color_range: list[list[int]] | None = None, goto_list: list[str] | None = None,
        id_mark: bool = False, gamepad_key: str | None = None,
    ) -> dict:
        """按 area_name 在指定 screen 插入或更新一个 area(写 yml + reload)。操作类,改 screen_info。

        area_name 存在则整体更新,不存在则追加。校验:screen 存在、area_name 非空、pc_rect 合法、
        模板引用存在(template_id 非空时)。写回 yml 并 reload,下次 analyze_screen 即生效。无需游戏在线。

        Returns:
            dict: ``{success, screen_name, area_name, action(inserted/updated), area_count, error}``。
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
        """按 area_name 删除指定 screen 的一个 area(写 yml + reload)。操作类,不可逆。

        screen_name + area_name 定位;area 不存在则 success=False。
        写回 yml 并 reload,下次 analyze_screen 即生效。

        Returns:
            dict: ``{success, screen_name, area_name, action(deleted), area_count, error}``。
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
        """创建一个新画面(空 area_list;写 yml + reload)。操作类,改 screen_info。

        screen_id 不与既有冲突、screen_name 唯一。创建后用 ``upsert_screen_area`` 加 area。
        无需游戏在线。**增减 MCP method 需客户端 /mcp 重连**获取新工具。

        Returns:
            dict: ``{success, screen_id, screen_name, action(created), error}``。
        """
        try:
            return backend.create_screen(screen_id, screen_name, app_id, pc_alt)
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'screen_id': screen_id, 'screen_name': screen_name,
                    'action': None, 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="列出画面名"))
    def list_screen_names() -> dict:
        """列出全部画面名(只读)。观察类,无需游戏在线。

        screen_name 是 screen_info 的匹配键(中文,须完全一致)—— goto_list
        填写、goto_screen 目标选择、get_screen_detail 入参都从这里查。

        Returns:
            dict: ``{success, count, screen_names(排序全量), error}``。
        """
        try:
            return backend.list_screen_names()
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'count': 0, 'screen_names': [], 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="读取画面档全集"))
    def get_screen_detail(
        screen_name: Annotated[str, Field(description="画面名,与 screen_info 的 screen_name 完全一致(如 邮件)")],
    ) -> dict:
        """读取单个画面档全集:全部 area(含 goto_list)+ 路由可达邻居(只读)。观察类。

        analyze_screen 只回当前帧命中;本方法回建档全集 —— 核对 screen_info、
        查「从这里能 goto 到哪」(goto_neighbors)、建档补漏用。无需游戏在线。

        Returns:
            dict: ``{success, screen_name, screen_id, pc_alt, area_count, areas[], goto_neighbors[], error}``。
        """
        try:
            return backend.get_screen_detail(screen_name)
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'screen_name': screen_name, 'screen_id': None,
                    'pc_alt': None, 'area_count': 0, 'areas': [], 'goto_neighbors': [],
                    'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(title="按路由导航画面"))  # 操作类:实际点击游戏
    def goto_screen(
        target_screen_name: Annotated[str, Field(description="目标画面名,与 screen_info 的 screen_name 完全一致(如 邮件)")],
        max_steps: Annotated[int, Field(description="最多点击次数,防路由成环", ge=1, le=30)] = 10,
    ) -> dict:
        """沿建档 goto_list 路由导航到目标画面。操作类(实际点击游戏)。

        复用 op 层 round_by_goto_screen 的同一套路由图:识别当前画面 → 查
        Floyd 路由 → 逐边点击对应 area。报「无路径」= 两画面间 goto 边未建档
        (补 area 的 goto_list,别硬试坐标)。goto_list 如实记录跳转(含不可逆/
        消耗类出口,不做安全过滤);本工具会自动点击沿途边,路径安全由调用方负责。

        Returns:
            dict: ``{success, current_screen, target_screen, steps[每步 画面--area-->画面], error}``。
        """
        try:
            return backend.goto_screen(target_screen_name, max_steps)
        except StopRunInterrupted:
            # 同 click_game:BaseException 按名收口,防穿透 ASGI(防御纵深;
            # backend 层另有按名收口,双保险)。
            return {'success': False, 'current_screen': None, 'target_screen': target_screen_name,
                    'steps': [], 'error': '运行已被停机中断(守卫拦截本次导航点击)'}
        except Exception as e:  # noqa: BLE001 工具层统一兜底
            return {'success': False, 'current_screen': None, 'target_screen': target_screen_name,
                    'steps': [], 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True, title="关闭游戏"))  # 操作类+破坏性:关游戏
    def close_game() -> str:
        """关闭游戏(发关闭窗口信号,秒级)。操作类。

        controller 吞异常不返成功标志,故只表「信号已发」—— 用 check_game_window
        验证是否真关。

        Returns:
            ``{success: True, result: <backend 返回文本>}``(信号已发,非已关闭);
            backend 抛错时 ``{success: False, error: <原因>}``。
        """
        try:
            msg = backend.close_game()
        except StopRunInterrupted:
            # 同 click_game:BaseException 按名收口,防穿透 ASGI(防御纵深)。
            return {'success': False, 'error': '运行已被停机中断(守卫拦截本次操作)'}
        except Exception as e:  # noqa: BLE001 工具层兜底(BackendNotReadyError 等)
            return {'success': False, 'error': str(e)}
        return {'success': True, 'result': msg}

    @mcp.tool(annotations=ToolAnnotations(title="点击游戏坐标"))  # 操作类:操作游戏点击(非破坏)
    def click_game(
        x: float, y: float,
        press_time: Annotated[float, Field(description="按住时长(秒);默认 0.1(游戏识别下限,0=极短按可能无效)")] = 0.1,
        pc_alt: Annotated[bool, Field(description="点击前是否按住 Alt 解锁光标;大世界等 pc_alt=true 画面必需,其余 False")] = False,
    ) -> dict:
        """点击游戏窗口内坐标(1080p 游戏空间,同 screen_info pc_rect 中心)。操作类。

        鼠标点击用本 tool;键盘按键用 ``key_tap``;鼠标拖拽用 ``drag``。

        坐标经控制器缩放到真实屏幕;不在窗口内则不点击(in_window=False)。需游戏窗口就绪。

        pc_alt=True 时点击前先按住 Alt 解锁光标 —— 大世界等 pc_alt=true 画面必需
        (星穹铁道锁光标,不按 Alt 点击落空)。判断依据:目标画面对应 screen_info
        的 ``pc_alt`` 字段;框架内部点击(跑 application)会自动带,经 MCP 手动点击
        pc_alt 画面时需显式传 True。其余画面保持 False。

        ⚠️ 操作后建议 sleep:底层 click 无内置等待,点 UI 常触发画面切换(菜单/弹窗/
        进画面),连续操作或 ``capture_game_screen`` 前建议 sleep ~1s 等动画(否则截过渡帧)。

        Returns:
            ``{success, x, y, in_window, pc_alt, error?}``;backend 抛错时 success=False + error。
        """
        try:
            return backend.click_game(x, y, press_time, pc_alt)
        except StopRunInterrupted:
            # 停机守卫异常是 BaseException,下方泛型 except Exception 接不住;
            # 不按名收口会穿透 FastMCP → Starlette ServerErrorMiddleware
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
        """键盘按键(press_time=0 短按,>0 长按)。操作类。

        键盘按键用本 tool;鼠标点击用 ``click_game``;拖拽用 ``drag``。

        覆盖框架 btn_controller 能发的键:移动 ``w``/``a``/``s``/``d``、交互 ``f``、
        ``esc``、``space`` 等(键名沿用框架约定)。press_time>0 长按(如移动长按 1-2s)。
        需游戏窗口就绪。

        ⚠️ 操作后建议 sleep(底层无内置等待):移动 wasd ~1s 等角色到位(不等就 interact
        可能失效,见 scratch_card issue #2405)、交互 ``f`` ~1-2s 进场景/对话、``esc``
        ~0.5s 开关菜单。连续操作前按需 sleep。

        Returns:
            ``{success, key, press_time, error?}``;backend 抛错时 success=False + error。
        """
        try:
            return backend.key_tap(key, press_time)
        except StopRunInterrupted:
            # 同 click_game:BaseException 按名收口,防穿透 ASGI(防御纵深)。
            return {'success': False, 'key': key, 'press_time': press_time,
                    'error': '运行已被停机中断(守卫拦截本次输入)'}
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'success': False, 'key': key, 'press_time': press_time, 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(title="鼠标拖拽"))  # 操作类:鼠标拖拽(非破坏)
    def drag(
        x1: float, y1: float, x2: float, y2: float,
        duration: Annotated[float, Field(description="拖拽耗时(秒),默认 1.0")] = 1.0,
    ) -> dict:
        """鼠标按住拖拽((x1,y1)→(x2,y2),1080p 游戏坐标,同 screen_info pc_rect)。操作类。

        鼠标拖拽用本 tool;点击用 ``click_game``;按键用 ``key_tap``。

        覆盖刮刮卡刮开、八卦收集来回拖、咖啡拖动等。需游戏窗口就绪。

        ⚠️ 操作后建议 sleep:底层 drag 无内置等待,拖后画面变化(刮/滚),连续操作或
        capture 前建议 sleep ~0.5s。

        Returns:
            ``{success, x1, y1, x2, y2, duration, error?}``;backend 抛错时 success=False + error。
        """
        try:
            return backend.drag(x1, y1, x2, y2, duration)
        except StopRunInterrupted:
            # 同 click_game:BaseException 按名收口,防穿透 ASGI(防御纵深)。
            return {'success': False, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'duration': duration,
                    'error': '运行已被停机中断(守卫拦截本次输入)'}
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'success': False, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'duration': duration, 'error': str(e)}

    @mcp.tool(annotations=ToolAnnotations(title="输入文本"))  # 操作类:文本输入(非破坏)
    def input_text(
        text: Annotated[str, Field(description="要输入的文本(账号/密码/兑换码等)")],
        use_clipboard: Annotated[bool | None, Field(description="None=跟随 game_config.type_input_way;True=强制剪贴板;False=强制逐键")] = None,
    ) -> dict:
        """向当前焦点输入框输入文本(账号/密码等)。操作类。

        需先用 click_game 点击输入框聚焦。需游戏窗口就绪。

        Returns:
            ``{success, method, masked_text, error?}``;backend 抛错时 success=False + error。
        """
        try:
            return backend.input_text(text, use_clipboard)
        except StopRunInterrupted:
            # 同 click_game:BaseException 按名收口,防穿透 ASGI(防御纵深)。
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
    mcp.tool(annotations=ToolAnnotations(title="运行 operation"))(make_run_operation(backend))
    # 配置修改工具(通用入口,按 app_id 路由到各 config 领域方法)
    mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="读取配置"))(make_get_config(backend))
    mcp.tool(annotations=ToolAnnotations(title="修改配置字段"))(make_set_config(backend))
    mcp.tool(annotations=ToolAnnotations(title="增改配置列表项"))(make_add_config_item(backend))
    mcp.tool(annotations=ToolAnnotations(destructiveHint=True, title="删除配置列表项"))(make_delete_config_item(backend))
    mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="描述配置结构"))(make_describe_config(backend))
    mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="列出可改配置"))(make_list_app_configs(backend))
    register_prompts(mcp)
    register_prompt_tools(mcp)

    return mcp
