"""米游社 HTTP 发送抽象与 requests 实装。

HttpSend 契约（docs/develop/one_dragon/mys/README.md 模块表 mys_http 行）：http_send 全链路必填
无默认——真实实装 ``RequestsHttpSend`` 只由运行入口（MCP 装配层）传入，
测试注入剧本式假实现。headers 为 ``list[tuple[str, str]]`` 保序保重复，
多条 Set-Cookie 不合并；取单值头用本模块的 ``header_get`` 大小写不敏感助手。
"""

from collections.abc import Callable
from dataclasses import dataclass

import requests

#: 请求超时秒数（口径 miyoushe-api-flow.md §4.2：25 秒；登录响应同为超时管控）。
#: 模块级常量供测试按需收紧（真实运行恒为 25）。
REQUEST_TIMEOUT_SECONDS: float = 25.0


@dataclass
class HttpSendResult:
    """一次 HTTP 发送的结果。

    Attributes:
        status: HTTP 状态码。非 2xx 不在传输层抛错——由调用方按业务分诊
            （与参考实现「传输层只管发，response.ok 判定归调用方」一致）。
        headers: 响应头列表，保序保重复（多条 Set-Cookie 各占一项，不合并；
            经 ``response.raw.headers`` 的 urllib3 HTTPHeaderDict 产出，
            原始大小写与到达顺序保留）。取值用 ``header_get``。
        body: 响应体原始字节。
    """

    status: int
    headers: list[tuple[str, str]]
    body: bytes


def header_get(headers: list[tuple[str, str]], name: str) -> str | None:
    """按头名大小写不敏感取第一个匹配的值；不存在返回 None。

    Args:
        headers: ``HttpSendResult.headers`` 形态的头列表。
        name: 头名（任意大小写）。
    """
    lowered = name.lower()
    for key, value in headers:
        if key.lower() == lowered:
            return value
    return None


#: HTTP 发送契约：(url, method, headers, body) -> HttpSendResult。
#: body 传 None 表示无请求体（GET）；调用方不解析传输层异常之外的结果——
#: 网络/超时异常由实装类原样上抛，调用方自行决定降级语义。
HttpSend = Callable[[str, str, dict[str, str], bytes | None], HttpSendResult]


class RequestsHttpSend:
    """HttpSend 的 requests 同步实装。

    口径（miyoushe-api-flow.md §2.1/§4.2，与参考实现 ``redirect: 'error'`` 一致）：
    - redirect 禁用：3xx 原样返回给调用方，不跟随；
    - 超时 25 秒（连接 + 读取共用，见 ``REQUEST_TIMEOUT_SECONDS``）；
    - Set-Cookie 全量收取：经 ``response.raw.headers``（urllib3 HTTPHeaderDict）
      取头列表——requests 的 ``response.headers`` 是 dict 合并视图，同名多条
      Set-Cookie 会被合并丢失，违反「保序保重复」契约。
    """

    def __call__(
        self,
        url: str,
        method: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> HttpSendResult:
        with requests.Session() as session:
            response = session.request(
                url=url,
                method=method,
                headers=headers,
                data=body,
                allow_redirects=False,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            # 响应体已随请求同步读入内存；raw 头列表在 session 关闭后仍可读
            # （数据在 response 对象上，不依赖连接存活）。
            header_pairs: list[tuple[str, str]] = list(response.raw.headers.items())
        return HttpSendResult(
            status=response.status_code,
            headers=header_pairs,
            body=response.content,
        )
