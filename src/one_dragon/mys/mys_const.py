"""米游社账号 API 协议常量。

常量全部内联自 miyoushe-api-flow.md §2/§3/§4（该文档常量经参考实现源码逐行
核对 + 2026-11-03 实测流量校对）；本文件零逻辑，只放常量。
"""

# ---- 端点（出处：miyoushe-api-flow.md §2.1/§3.2/§4.3/§1）----

#: 密码登录（web 形态，loginByPassword）
LOGIN_URL: str = 'https://passport-api.miyoushe.com/account/ma-cn-passport/web/loginByPassword'

#: 设备指纹注册 getFp
GET_FP_URL: str = 'https://public-data-api.mihoyo.com/device-fp/api/getFp'

#: 按 cookie 查绑定角色（角色自动发现入口）
ROLE_LIST_URL: str = 'https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie'

#: game_record 请求基座（崩铁子路径如 hkrpg/api/index 由调用方拼接）
GAME_RECORD_BASE_URL: str = 'https://api-takumi-record.mihoyo.com/game_record/app/'

# ---- DS salt（出处：miyoushe-api-flow.md §2.3/§4.1）----

#: 登录专用 DS salt（三段式 salt&t&r，与 game_record 的 DS2 salt 不同）
LOGIN_SALT: str = 'LyD1rXqMv2GJhnwdvCBjFOKGiKuLY3aO'

#: game_record DS2 salt（社区通称 4X salt；q 按 key 排序 + URL 编码）
RECORD_SALT: str = 'xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs'

# ---- RSA 公钥（1024 位，原文逐字复制自 miyoushe-api-flow.md §2.2；
# 与参考实现及 UIGF password_passport.md 逐字一致）----

RSA_PUBLIC_KEY_PEM: str = '''-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDDvekdPMHN3AYhm/vktJT+YJr7
cI5DcsNKqdsx5DZX0gDuWFuIjzdwButrIYPNmRJ1G8ybDIF7oDW2eEpm5sMbL9zs
9ExXCdvqrn51qELbqj0XxtMTIpaCHFSI50PfPpTFV9Xt/hmyVwokoOXFlAEgCn+Q
CgGs52bFoYMtyi+xEQIDAQAB
-----END PUBLIC KEY-----'''

# ---- 头值常量（出处：miyoushe-api-flow.md §2.4 登录十件套 / §4.2 game_record 头 / §3.2 getFp 头）----

CONTENT_TYPE_JSON: str = 'application/json'

#: 桌面 Chrome UA——直连 API 场景实测通过（UIGF 的安卓 webview 形态是 H5 页面路线前提，不适用）
USER_AGENT_DESKTOP_CHROME: str = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36'
)

# 登录请求「十件套」中的 5 个显式业务头（另含设备头三件 + Content-Type + ds，由 mys_client 组装）
LOGIN_X_RPC_APP_ID: str = 'bll8iq97cem8'
LOGIN_X_RPC_CLIENT_TYPE: str = '4'
LOGIN_X_RPC_SOURCE: str = 'v2.webLogin'
LOGIN_X_RPC_GAME_BIZ: str = 'bbs_cn'
LOGIN_X_RPC_SDK_VERSION: str = '2.31.0'

# game_record 请求头（binding 域角色发现同管线同头集，实测同款通过）
RECORD_X_RPC_APP_VERSION: str = '2.11.1'
RECORD_X_RPC_CLIENT_TYPE: str = '5'
RECORD_REFERER: str = 'https://webstatic.mihoyo.com/'

# getFp 请求的 Referer（登录与 game_record 请求不带 Referer，仅 getFp 带）
GET_FP_REFERER: str = 'https://act.mihoyo.com/'

# 设备头三件中的 platform 值：请求头使用口径恒 '4'（getFp body 内 platform='1' 是注册口径，两者不矛盾，
# 见 miyoushe-api-flow.md §3.4）
DEVICE_PLATFORM_VALUE: str = '4'

# ---- 主机白名单（仅允许 https；契约见 docs/develop/one_dragon/mys/README.md 模块表 mys_const 行）----
# 与参考实现 ALLOWED 的差异：换入 public-data-api.mihoyo.com 供 getFp；
# 弃 bbs-api.miyoushe.com（本迭代无该域请求，角色发现走 api-takumi 本就在名单内）。
HOST_WHITELIST: frozenset[str] = frozenset({
    'passport-api.miyoushe.com',
    'api-takumi.mihoyo.com',
    'api-takumi-record.mihoyo.com',
    'public-data-api.mihoyo.com',
})
