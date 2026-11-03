"""米游社 DS 签名与 RSA 加密（纯函数）。

口径出处：docs/develop/sr_od/application/account_profile/miyoushe-api-flow.md：
- 登录 DS（§2.3）：``{t},{r},{md5(salt={LOGIN_SALT}&t={t}&r={r})}``，
  t 默认秒级时间戳、r 默认 6 位小写 hex；
- game_record DS2（§4.1）：``{t},{r},{md5(salt={RECORD_SALT}&t={t}&r={r}&b={b}&q={q})}``，
  本模块只服务 GET 形态（b 恒空串）；q = 参数按 key 排序后做
  application/x-www-form-urlencoded 序列化再以 ``&`` 拼接，序列化规则与参考实现
  ``URLSearchParams.toString()`` 逐字节一致（Node 24 实测：空格 → ``+``；
  仅 ``[A-Za-z0-9*-._]`` 原样保留，其余字节一律大写十六进制百分号编码，
  含 ``~``/``!``/``+`` 等其它编码器会放行的字符）；
- RSA（§2.2）：1024 位公钥 PKCS#1 v1.5 padding + base64，账号与密码都加密。
"""

import base64
import hashlib
import secrets
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding

from one_dragon.mys.mys_const import (
    LOGIN_SALT,
    RECORD_SALT,
    RSA_PUBLIC_KEY_PEM,
)

#: application/x-www-form-urlencoded 序列化中原样保留的字节集
# （ASCII 字母数字 + * - . _；依据上文模块 docstring 的 URLSearchParams 实测口径）
_FORM_URLENCODE_SAFE: frozenset[int] = frozenset(
    b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789*-._'
)

# DS2 的 r 取值域 [100001, 200000] 闭区间整数（miyoushe-api-flow.md §4.1，三源一致）
_RECORD_R_MIN: int = 100001
_RECORD_R_RANGE: int = 100000


def _form_urlencode(value: str) -> str:
    """按 URLSearchParams.toString() 的字节级口径编码单个参数值（见模块 docstring）。"""
    parts: list[str] = []
    for byte in value.encode('utf-8'):
        if byte == 0x20:
            parts.append('+')
        elif byte in _FORM_URLENCODE_SAFE:
            parts.append(chr(byte))
        else:
            parts.append(f'%{byte:02X}')
    return ''.join(parts)


def _build_query_string(query: dict) -> str:
    """query 按 key 码点序排序后序列化（无参数时为空串）。

    排序与参考实现 ``Object.entries(query).sort(([a],[b])=>a.localeCompare(b))``
    等价：本项目 query 键均为 ASCII 小写蛇形命名，码点序与 localeCompare 序
    在该键域内一致。值统一 str()（与 JS URLSearchParams 对值自动字符串化同口径）。
    """
    pairs = sorted(query.items(), key=lambda item: str(item[0]))
    return '&'.join(
        f'{_form_urlencode(str(key))}={_form_urlencode(str(value))}'
        for key, value in pairs
    )


def ds_login(t: int | None = None, r: str | None = None) -> str:
    """登录专用 DS（三段式，无 b/q；签名串口径 miyoushe-api-flow.md §2.3）。

    Args:
        t: 秒级时间戳；None 取当前时间。可注入以复现测试向量。
        r: 6 位小写 hex；None 随机生成。可注入以复现测试向量。

    Returns:
        形如 ``{t},{r},{md5hex}`` 的 DS 头值。
    """
    t_value = int(time.time()) if t is None else t
    r_value = secrets.token_hex(3) if r is None else r
    raw = f'salt={LOGIN_SALT}&t={t_value}&r={r_value}'
    digest = hashlib.md5(raw.encode('utf-8')).hexdigest()
    return f'{t_value},{r_value},{digest}'


def ds_record(query: dict, t: int | None = None, r: int | None = None) -> str:
    """game_record DS2（GET 形态，b 恒空；签名串口径 miyoushe-api-flow.md §4.1）。

    Args:
        query: URL 参数字典；q 按 key 排序 + URL 编码后参与签名。
        t: 秒级时间戳；None 取当前时间。可注入以复现测试向量。
        r: [100001, 200000] 整数；None 随机生成。可注入以复现测试向量。

    Returns:
        形如 ``{t},{r},{md5hex}`` 的 DS 头值。
    """
    t_value = int(time.time()) if t is None else t
    r_value = secrets.randbelow(_RECORD_R_RANGE) + _RECORD_R_MIN if r is None else r
    # b 恒空串（GET）：本模块只签 GET 形态；POST 的 b=实际发送串由调用层组装后再签
    raw = f'salt={RECORD_SALT}&t={t_value}&r={r_value}&b=&q={_build_query_string(query)}'
    digest = hashlib.md5(raw.encode('utf-8')).hexdigest()
    return f'{t_value},{r_value},{digest}'


#: 公钥对象（模块级解析一次；PEM 原文见 mys_const，加载失败属部署事故，直接失败）
_PUBLIC_KEY = serialization.load_pem_public_key(RSA_PUBLIC_KEY_PEM.encode('utf-8'))


def rsa_encrypt(plain: str) -> str:
    """RSA-PKCS1 v1.5 加密并 base64（口径 miyoushe-api-flow.md §2.2）。

    账号与密码都经本函数加密进登录 body；PKCS#1 v1.5 填充含随机字节，
    同一明文两次加密密文不同（服务端按私钥侧解密，随机性是规范要求）。

    Args:
        plain: 明文（明文长度上限 117 字节，超出由底层抛 ValueError——
            1024 位模长减去 11 字节填充头的规范上限）。

    Returns:
        base64 编码的密文（128 字节密文 → 172 字符）。
    """
    ciphertext = _PUBLIC_KEY.encrypt(plain.encode('utf-8'), rsa_padding.PKCS1v15())
    return base64.b64encode(ciphertext).decode('ascii')
