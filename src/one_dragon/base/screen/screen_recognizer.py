"""画面额外识别器(per-screen recognizer)的公共契约:基类 + 注册表 + 扫描结果。

本模块是游戏无关的公共包契约,与 ``screen_match.py`` / ``screen_info.py`` 同域。
SR(及未来 ZZZ)的 backend 在画面**精准命中**后,按 ``screen_name`` 查注册表调用对应
recognizer,做该画面特有的额外识别(如货币战争备战画面的前后台 / 备战席角色),
把结构化领域事实回传给 ``analyze`` 调用方。

设计要点:
- **基类 ``ScreenRecognizer``**:子类设类属性 ``screen_name`` + 实现 ``recognize()``,
  框架扫描游戏应用包自动发现(扫描根由各游戏 backend 配置,无需中心注册)。
- **注册表 ``ScreenRecognizerRegistry``**:``screen_name → recognizer`` 内存映射,
  只管存取,不管扫描(扫描由各游戏 backend 侧做 —— 公共包不能反向依赖游戏代码)。
- **``RecognizerScanResult``**:扫描器返回(注册表 + failures)。

详见 ``docs/superpowers/specs/2026-08-09-screen-recognizer-design.md``。
"""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.operation.one_dragon_context import OneDragonContext
    from one_dragon.base.screen.screen_info import ScreenInfo


class ScreenRecognizer:
    """画面额外识别器:画面精准命中后,框架按 ``screen_name`` 查表调用。

    子类只需:① 设类属性 ``screen_name``(中文画面名,与 ``ScreenMatch.screen_name`` 一致);
    ② 实现 ``recognize()``;③ 声明类属性 ``extras_doc``(extras 字段说明,随响应自描述)。
    框架扫描游戏应用包自动发现(扫描根由各游戏 backend 配置,SR 为
    ``sr_od.operations`` + ``sr_od.application``),无需中心注册。

    recognize 内部鼓励用领域模型类组装,再转 JSON 可序列化 dict 返回(工程化质量:
    单一真相源 / 类型注解)。框架层不规定 dict 结构(各画面不同),
    但**必须经 ``extras_doc`` 声明返回字段语义**(字段名 → 一行说明),analyze 会把它与 ``extras``
    一起平级返回(``AnalyzeScreenResult.extras_doc``)—— 调用方(智能体 / HTTP)拿到 extras 的同时
    就拿到字段语义,不必知道画面是什么、也不必另查文档。
    ``extras`` 直接计入 MCP tool 响应 token 预算(P6,Claude Code tool response 限 25000 tokens),
    故保持精简、只返决策需要的语义字段,别倒整张原始 OCR/坐标表;``extras_doc`` 每字段一行,
    同样从简。recognize 不得写 ``self.``;
    不得复用带**业务语义**进程级可变状态的 reader(如 ``_last_phase_round`` 这类会影响 operation 决策的
    last-known-good 缓存)—— 但**透明缓存类**共享状态(如 ``ocr_service._cache``,其并发异常已被内部兜住)
    可放心复用。详见实现文档 / spec §6「并发安全」。
    """

    screen_name: str   # 关联画面名;与 analyze 命中的 ScreenMatch.screen_name 一致

    # extras 字段说明(单一源,随代码走):字段名 → 一行语义(取值格式 / 读不到时的值 / 可靠性注意)。
    # analyze 把它与 extras 一起平级返回(AnalyzeScreenResult.extras_doc),调用方零跳查。
    # 键集应与 recognize 实际返回的 dict 键一致(加 / 改字段时同步)。
    extras_doc: dict[str, str] = {}

    def recognize(
        self,
        ctx: 'OneDragonContext',
        image: 'MatLike',
        screen_info: 'ScreenInfo',
    ) -> dict | None:
        """对该画面做额外识别,返回 JSON 可序列化的领域事实 dict;无内容/不适用返 None。

        抛异常由框架兜住(analyze 不中断,extras 置 None + 记日志)。

        Args:
            ctx: 运行上下文(提供 screen_loader / ocr_service / tm)。
            image: 已截取的 RGB 画面(analyze 已截,复用,不重截)。
            screen_info: 命中画面的 ScreenInfo(可读 area_list 取 pc_rect)。

        Returns:
            JSON 可序列化 dict(画面特定结构);或 None。
        """
        raise NotImplementedError


class ScreenRecognizerRegistry:
    """``screen_name → recognizer`` 内存映射。公共包只管存取,不管扫描(扫描由游戏 backend 侧做)。"""

    def __init__(self) -> None:
        self._map: dict[str, ScreenRecognizer] = {}

    def register(self, recognizer: ScreenRecognizer) -> str | None:
        """注册一个 recognizer。

        Args:
            recognizer: 已实例化的识别器(``.screen_name`` 必须非空)。

        Returns:
            错误描述(注册失败:screen_name 为空 / 已被占用);None 表示成功。
            不抛异常 —— 扫描器收集错误进 failures,不中断扫描。
        """
        name = getattr(recognizer, 'screen_name', '')
        if not name:
            return f'{type(recognizer).__name__}.screen_name 为空'
        if name in self._map:
            return f'screen_name 重复: {name}({type(recognizer).__name__} 与 {type(self._map[name]).__name__})'
        self._map[name] = recognizer
        return None

    def get(self, screen_name: str) -> ScreenRecognizer | None:
        """按画面名取识别器;无则 None。"""
        return self._map.get(screen_name)

    def screen_names(self) -> list[str]:
        """已注册的画面名(排序,便于排障/展示)。"""
        return sorted(self._map)


@dataclass
class RecognizerScanResult:
    """扫描结果(镜像 OperationListResult 的 failures 语义)。

    Attributes:
        registry: 扫描构建的注册表(screen_name → recognizer)。
        failures: 单模块 import 失败 / 重复 screen_name 记录(扫描不中断)。
    """

    registry: ScreenRecognizerRegistry = field(default_factory=ScreenRecognizerRegistry)
    failures: list[str] = field(default_factory=list)
