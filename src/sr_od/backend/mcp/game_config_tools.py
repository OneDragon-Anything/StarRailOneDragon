"""游戏配置 MCP 工具:update_game_config(语言 / 游戏路径,白名单键)。

与通用配置工具(make_set_config,按 app_id 路由到 ApplicationConfig 体系)的
分界:本工具面向 **框架级游戏配置** —— ``game_config.lang``(文本语言,
窗口标题/i18 默认语言/OCR 阈值表的状态源)与 ``game_account_config.game_path``
(游戏安装路径,启动器定位用)。这两个键不在 ApplicationConfig 体系内,
通用配置工具路由不到,故单独开白名单入口。

lang 语义边界:本工具只改 **配置状态源**,不动游戏内设置(游戏内切换走
``SwitchLanguageOp``;用户手动在游戏内改语言后,也用本工具校正配置)。
"""
import os
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from sr_od.backend.backend_context import SrBackendContext

#: lang 合法值(与 ``GameLanguageEnum`` 一致)
_LANG_VALUES: dict[str, str] = {'cn': '简体中文', 'en': 'English'}


def register_game_config_tools(mcp: FastMCP, backend: SrBackendContext) -> None:
    """注册游戏配置工具(update_game_config;由 ``create_mcp_server`` 调用)。"""

    @mcp.tool(annotations=ToolAnnotations(title="更新游戏配置"))  # 操作类:写框架级配置
    def update_game_config(
        key: Annotated[str, Field(description="配置键,暂只支持 'lang'(游戏文本语言) 与 'game_path'(游戏安装路径)")],
        value: Annotated[str, Field(description="配置值;lang 取 'cn'/'en',game_path 取游戏安装目录绝对路径")],
    ) -> dict:
        """更新框架级游戏配置(白名单键,暂只支持语言与游戏路径)。

        lang 只改配置状态源(i18 默认语言/窗口标题/OCR 阈值表随它取值),
        不操作游戏内设置 —— 游戏内切换语言走 SwitchLanguageOp(operation);
        用户手动在游戏内改了语言后,也用本工具校正配置(键:lang)。

        Returns:
            ``{success, key, value}`` 或 ``{success: False, error}``(非法键/值)。
        """
        if key == 'lang':
            if value not in _LANG_VALUES:
                return {'success': False,
                        'error': f"lang 只支持 {'/'.join(_LANG_VALUES)},实际: {value}"}
            backend.ctx.game_config.lang = value
            # 运行进程的控制器按缓存标题查找窗口,必须与配置同步刷新——
            # 只改配置不刷缓存 = 下次窗口查找用新标题找旧窗口,找不到会触发
            # 「检测游戏窗口」的重新启动游戏兜底(误拉起第二个游戏实例)。
            backend.ctx.controller.set_window_title(backend.ctx.game_config.win_title)
            return {'success': True, 'key': key, 'value': value,
                    'hint': '配置与控制器窗口标题已同步;游戏内实际切换语言'
                            '请运行 SwitchLanguageOp'}
        if key == 'game_path':
            if not os.path.isdir(value):
                return {'success': False, 'error': f'路径不存在或不是目录: {value}'}
            backend.ctx.game_account_config.game_path = value
            return {'success': True, 'key': key, 'value': value}
        return {'success': False, 'error': f"不支持的配置键: {key}(暂只支持 'lang'/'game_path')"}
