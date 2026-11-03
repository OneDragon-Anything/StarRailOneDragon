"""米游社设备身份：device_id 持久化 + getFp 设备指纹（含缓存与降级）。

口径出处：miyoushe-api-flow.md §3（device.json 结构 / getFp 端点与 20 字段
固定指纹模板 / 四判据 / 24h 缓存与 30 分钟冷却 / 设备头三件）、design.md
§2.2 mys_device 小节。

- device_id 是设备信誉锚：device.json 存在即用，正常路径严禁轮换（已登录
  设备重复登录不触发验证，依据 login-verification-research.md §3.4 调研）。
  唯一例外 = 文件损坏（解析失败 / 字段非法）——损坏件已无法提供信誉，
  重生成是止损而非轮换，须 warning 留痕。
- getFp 成功判据四条同时满足（HTTP 2xx + retcode==0 + data.code==200 +
  fp 匹配 ``/^[a-z0-9]{6,100}$/i``）：仅 retcode=0 不够——FP 服务仍可能
  返回 data.code=403（account-device.mjs:33-34 同款结论）。
- fp 内存缓存 24h；失败后 30 分钟冷却，冷却期内降级不带头（其余请求照发，
  实测有/无 fp 两种形态登录与 game_record 均可用）。
"""

import json
import re
import secrets
import threading
import time
import uuid

from one_dragon.mys.mys_const import (
    CONTENT_TYPE_JSON,
    DEVICE_PLATFORM_VALUE,
    GET_FP_REFERER,
    GET_FP_URL,
    USER_AGENT_DESKTOP_CHROME,
)
from one_dragon.mys.mys_http import HttpSend
from one_dragon.mys.mys_session import SessionStore
from one_dragon.utils.log_utils import log

DEVICE_ID_HEADER: str = 'x-rpc-device_id'
DEVICE_FP_HEADER: str = 'x-rpc-device_fp'
DEVICE_PLATFORM_HEADER: str = 'x-rpc-platform'

# device_id 合法形态：UUID（大小写不敏感；与参考实现 /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i 一致）
_DEVICE_ID_RE: re.Pattern[str] = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

# fp 合法形态（四判据之一；大小写不敏感）
_FP_RE: re.Pattern[str] = re.compile(r'^[a-z0-9]{6,100}$', re.IGNORECASE)

_FP_CACHE_SECONDS: float = 24 * 3600
_FP_RETRY_COOLDOWN_SECONDS: float = 30 * 60

#: getFp 请求头（miyoushe-api-flow.md §3.2；UA 与 game_record 头同款桌面 Chrome）
_GET_FP_HEADERS: dict[str, str] = {
    'Content-Type': CONTENT_TYPE_JSON,
    'Referer': GET_FP_REFERER,
    'User-Agent': USER_AGENT_DESKTOP_CHROME,
}

#: getFp body 的 app_name 与 device_fp 固定字段（miyoushe-api-flow.md §3.2）
_GET_FP_APP_NAME: str = 'bbs_cn'
_GET_FP_DEVICE_FP_FIELD: str = '38d7ee834d1e9'


def _build_ext_fields(device_id: str) -> dict[str, str]:
    """getFp ext_fields 20 字段固定指纹模板（逐字照抄 miyoushe-api-flow.md §3）。

    这些是固定兼容参数（出处 SeelieEx，上游固定参考提交），**不是**本机真实
    硬件读数；IDFV 是唯一动态字段 = device_id 大写。
    """
    return {
        'proxyStatus': '0',
        'accelerometer': '-0.159515x-0.830887x-0.682495',
        'ramCapacity': '3746',
        'IDFV': device_id.upper(),
        'gyroscope': '-0.191951x-0.112927x0.632637',
        'isJailBreak': '0',
        'model': 'iPhone12,5',
        'ramRemain': '115',
        'chargeStatus': '1',
        'networkType': 'WIFI',
        'vendor': '--',
        'osVersion': '17.0.2',
        'batteryStatus': '50',
        'screenSize': '414×896',
        'cpuCores': '6',
        'appMemory': '55',
        'romCapacity': '488153',
        'romRemain': '157348',
        'cpuType': 'CPU_TYPE_ARM64',
        'magnetometer': '-84.426331x-89.708435x-37.117889',
    }


def _json_compact(data: dict) -> bytes:
    """紧凑 JSON 字节串（与参考实现 JSON.stringify 形态一致，非 ASCII 原样 UTF-8）。"""
    return json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


class DeviceIdentity:
    """设备身份：device_id 读写 + getFp 注册，产出请求设备头三件。

    构造两参必填无默认（design.md §2.2 / §2.5 契约 3）：store 与 http_send
    都由装配层注入，测试注入临时目录 + 假发送函数即零副作用。
    """

    def __init__(self, store: SessionStore, http_send: HttpSend) -> None:
        self._store: SessionStore = store
        self._http_send: HttpSend = http_send
        # fp 状态的进程内互斥（独立于 store 的落盘锁：两者保护对象不同）
        self._fp_lock: threading.Lock = threading.Lock()
        self._device_fp: str | None = None
        self._fp_expires_at: float = 0.0  # monotonic 时点：缓存失效时刻
        self._fp_retry_at: float = 0.0  # monotonic 时点：失败冷却结束时刻

    def get_headers(self) -> dict[str, str]:
        """组装设备头三件（每次请求实时产出，口径 miyoushe-api-flow.md §3.4）。

        fp 降级期不带 ``x-rpc-device_fp``，其余头照常（实测有/无 fp 均可用）。
        """
        device_id = self._load_or_create_device_id()
        headers: dict[str, str] = {
            DEVICE_ID_HEADER: device_id,
            DEVICE_PLATFORM_HEADER: DEVICE_PLATFORM_VALUE,
        }
        device_fp = self._get_device_fp(device_id)
        if device_fp is not None:
            headers[DEVICE_FP_HEADER] = device_fp
        return headers

    def _load_or_create_device_id(self) -> str:
        """读存量 device_id；缺失静默首建，损坏重生成 + warning 留痕。

        SessionStore.load_device 三分支语义：None=文件缺失（首建，非轮换、
        无警告）；''/非法 uuid=存量损坏（重生成留痕）；其余=合法存量即用。
        """
        saved = self._store.load_device()
        if saved is not None and _DEVICE_ID_RE.fullmatch(saved) is not None:
            return saved
        if saved is not None:
            # 损坏件已无法提供设备信誉，重生成是止损非轮换（warning 留痕让轮换可观测）
            log.warning('米游社设备身份文件损坏(解析失败或字段非法)，已重新生成 device_id')
        device_id = str(uuid.uuid4())
        self._store.save_device(device_id)
        return device_id

    def _get_device_fp(self, device_id: str) -> str | None:
        """取缓存 fp；缓存过期且不在冷却期才发起 getFp（详见模块 docstring）。"""
        with self._fp_lock:
            now = time.monotonic()
            if now < self._fp_retry_at:
                # 冷却期：上次获取失败未满 30 分钟，降级不带头且不再请求
                return None
            if self._device_fp is not None and now < self._fp_expires_at:
                return self._device_fp  # 24h 内存缓存命中
            device_fp = self._fetch_device_fp(device_id)
            if device_fp is not None:
                self._device_fp = device_fp
                self._fp_expires_at = time.monotonic() + _FP_CACHE_SECONDS
            else:
                self._device_fp = None
                self._fp_retry_at = time.monotonic() + _FP_RETRY_COOLDOWN_SECONDS
            return device_fp

    def _fetch_device_fp(self, device_id: str) -> str | None:
        """发起一次 getFp；四判据全过返回 fp，任一不过返回 None（进入冷却）。"""
        body: dict[str, str | bytes] = {
            'seed_id': secrets.token_hex(8),  # 每次随机 16 位 hex（参考实现 randomBytes(8).hex）
            'device_id': device_id.upper(),  # body 内 device_id 用大写（注册口径）
            'platform': '1',  # 注册口径 platform=1，与请求头 platform=4 使用口径分离
            'seed_time': str(int(time.time() * 1000)),
            'ext_fields': json.dumps(
                _build_ext_fields(device_id), ensure_ascii=False, separators=(',', ':')
            ),
            'app_name': _GET_FP_APP_NAME,
            'device_fp': _GET_FP_DEVICE_FP_FIELD,
        }
        try:
            result = self._http_send(
                GET_FP_URL, 'POST', dict(_GET_FP_HEADERS), _json_compact(body)
            )
        except Exception as e:  # 网络异常按获取失败降级（与参考实现 catch 分支一致）
            log.warning(f'getFp 请求异常，进入降级冷却({int(_FP_RETRY_COOLDOWN_SECONDS)}s): {type(e).__name__}')
            return None
        # 四判据（任一不过 = 失败；不细分打印响应内容，避免把服务端报文刷进日志）
        if not 200 <= result.status < 300:
            return None
        try:
            data = json.loads(result.body.decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            return None
        if not isinstance(data, dict) or data.get('retcode') != 0:
            return None
        inner = data.get('data')
        if not isinstance(inner, dict) or inner.get('code') != 200:
            return None  # 仅 retcode=0 不够：FP 服务仍可能返回 data.code=403
        device_fp = inner.get('device_fp')
        if not isinstance(device_fp, str) or _FP_RE.fullmatch(device_fp) is None:
            return None
        return device_fp
