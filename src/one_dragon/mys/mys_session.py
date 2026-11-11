"""米游社会话与设备的落盘持久化 + 会话异常体系。

会话文件布局（docs/develop/one_dragon/mys/README.md「会话文件布局与语义」节）：
``config/<实例>/mys/`` 下三文件、JSON、原子写（同目录临时文件 + ``os.replace``）
+ 权限尽力 0o600（POSIX 生效；Windows 依 ACL 继承，失败不阻塞主流程）。

- ``session.json`` 字段级 schema（定死）：
  ``{"schema_version": 1, "saved_at": "<ISO8601>", "expired": true|null,
  "cookies": {"<name>": "<value>"}}``——expired 缺省视为 false；
- ``role.json``：``{"role_id": "<字符串>", "server": "<区服>"}``（角色定位缓存）；
- ``device.json``：``{"schema_version": 1, "device_id": "<uuid>"}``（设备锚）。

store 实例由装配层构建并注入，同一实例贯穿 client/controller——同一把锁
（构造必填，禁默认自建）是 mark_expired 与滚动写不撞车的保证；全部入口持锁。
会话失效只打 expired 标记，永不清任何落盘文件；清除仅发生于用户显式登出
（``clear``）或登录成功整体覆盖。
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path

from one_dragon.utils.log_utils import log

SESSION_FILE_NAME: str = 'session.json'
ROLE_FILE_NAME: str = 'role.json'
DEVICE_FILE_NAME: str = 'device.json'

SESSION_SCHEMA_VERSION: int = 1
DEVICE_SCHEMA_VERSION: int = 1

#: 会话失效 retcode 映射（单一常量，便于实测定案后修订）：
#: 10001 = Please login（skills/sr-od-account-inspection/references/api.md
#: 错误码分诊表 2026-10-14 实测）；-100 = TokenInvalid
#: （login-verification-research.md §5）。空罐打 game_record 的实际返回码
#: 两权威源均未记载，以实机首验定案。
SESSION_EXPIRED_RETCODES: frozenset[int] = frozenset({10001, -100})


class MysApiError(Exception):
    """米游社 API 业务错误（retcode 非 0 时上抛）。

    Attributes:
        code: 服务端 retcode。
        message: 服务端 message 文案（可为空；不含 cookie/请求头等本机凭据）。
    """

    def __init__(self, code: int, message: str = '') -> None:
        self.code: int = code
        self.message: str = message
        super().__init__(f'retcode={code}' + (f' message={message}' if message else ''))


class MysSessionExpired(MysApiError):
    """会话已失效（retcode 命中 ``SESSION_EXPIRED_RETCODES``），提示重新登录。"""


def _try_chmod_600(path: Path) -> None:
    """尽力收紧文件权限到 0600；Windows 下语义受限，失败不影响主流程。"""
    try:
        os.chmod(path, 0o600)
    except OSError as e:
        log.warning(f'落盘权限收紧失败(尽力语义,不影响使用): {path.name} {e}')


class SessionStore:
    """session.json / role.json / device.json 的持久化原语（全部入口持锁）。"""

    def __init__(self, session_dir: Path, lock: threading.Lock) -> None:
        """两参必填：目录与锁都由装配层提供，禁默认自建。

        Args:
            session_dir: 三文件的存放目录（不存在时写入前自动创建）。
            lock: 同一实例贯穿 client/controller 的互斥锁。
        """
        self._session_dir: Path = session_dir
        self._lock: threading.Lock = lock

    # ---- session.json ----

    def save_cookies(self, cookies: dict[str, str]) -> None:
        """滚动续存：更新 saved_at 与 cookies，保留既有 expired 标记。

        每次业务响应的 Set-Cookie 滚动入罐后走本方法（过期只打标记不清理，
        滚动写不得抹掉过期标记）。无既有文件时 expired 落 null（schema 的
        true|null 缺省态）。
        """
        with self._lock:
            raw = self._read_json(SESSION_FILE_NAME) or {}
            raw['schema_version'] = SESSION_SCHEMA_VERSION
            raw['saved_at'] = datetime.now().isoformat()
            raw['expired'] = raw.get('expired')
            raw['cookies'] = dict(cookies)
            self._write_json(SESSION_FILE_NAME, raw)

    def save_session_full(self, cookies: dict[str, str]) -> None:
        """整体覆盖：重写 session.json 且产物不含 expired 键。

        仅「登录成功」与「验证成功重发成功」两个场景使用——过期标记随覆盖
        自然消失，无需显式清除。
        """
        with self._lock:
            self._write_json(SESSION_FILE_NAME, {
                'schema_version': SESSION_SCHEMA_VERSION,
                'saved_at': datetime.now().isoformat(),
                'cookies': dict(cookies),
            })

    def mark_expired(self) -> None:
        """合并写入 expired: true，cookies 等其余字段原样保留。

        文件不存在时幂等无操作（没有会话就没有「过期」概念）；文件损坏
        视同缺失（无可标记者，重登成功时整体覆盖即可恢复）。
        """
        with self._lock:
            raw = self._read_json(SESSION_FILE_NAME)
            if raw is None:
                return
            raw['expired'] = True
            self._write_json(SESSION_FILE_NAME, raw)

    def load_cookies(self) -> dict[str, str]:
        """读取 cookie 罐；文件缺失/损坏返回空 dict。"""
        with self._lock:
            raw = self._read_json(SESSION_FILE_NAME)
        if not raw:
            return {}
        cookies = raw.get('cookies')
        if not isinstance(cookies, dict):
            return {}
        return {
            key: value
            for key, value in cookies.items()
            if isinstance(key, str) and isinstance(value, str)
        }

    def is_expired(self) -> bool:
        """读 expired 标记（缺省视为 false；文件缺失/损坏视为未过期）。"""
        with self._lock:
            raw = self._read_json(SESSION_FILE_NAME)
        return raw is not None and raw.get('expired') is True

    # ---- role.json ----

    def save_role(self, role: dict) -> None:
        """保存角色定位缓存 ``{"role_id": "<字符串>", "server": "<区服>"}``。"""
        with self._lock:
            self._write_json(ROLE_FILE_NAME, dict(role))

    def load_role(self) -> dict | None:
        """读取角色定位缓存；文件缺失/损坏返回 None。"""
        with self._lock:
            return self._read_json(ROLE_FILE_NAME)

    # ---- device.json ----

    def save_device(self, device_id: str) -> None:
        """保存设备锚 ``{"schema_version": 1, "device_id": "<uuid>"}``。"""
        with self._lock:
            self._write_json(DEVICE_FILE_NAME, {
                'schema_version': DEVICE_SCHEMA_VERSION,
                'device_id': device_id,
            })

    def load_device(self) -> str | None:
        """读取设备锚，返回值三分支（损坏形态需要可区分，供 mys_device 决定
        「静默首建」还是「重生成 + warning 留痕」）：

        - ``None``：文件不存在（首次运行，正常路径）；
        - 字符串：存量 device_id 字段值（uuid 合法性由调用方校验）；
        - 空串：文件存在但损坏（JSON 解析失败 / device_id 字段缺失或非字符串）。
        """
        with self._lock:
            path = self._session_dir / DEVICE_FILE_NAME
            if not path.exists():
                return None
            raw = self._read_json(DEVICE_FILE_NAME)
        device_id = raw.get('device_id') if raw is not None else None
        if isinstance(device_id, str):
            return device_id
        return ''

    # ---- 清理 ----

    def clear(self) -> None:
        """删除 session.json 与 role.json，保留 device.json（设备锚不随登出
        轮换）。仅用户显式登出时调用。"""
        with self._lock:
            (self._session_dir / SESSION_FILE_NAME).unlink(missing_ok=True)
            (self._session_dir / ROLE_FILE_NAME).unlink(missing_ok=True)

    # ---- 原子读写底层 ----

    def _write_json(self, name: str, data: dict) -> None:
        """同目录临时文件 + os.replace 原子替换（os.replace 同卷内原子）。"""
        self._session_dir.mkdir(parents=True, exist_ok=True)
        target = self._session_dir / name
        tmp = target.with_name(name + '.tmp')
        tmp.write_bytes(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        _try_chmod_600(tmp)
        os.replace(tmp, target)

    def _read_json(self, name: str) -> dict | None:
        """读 JSON 对象；文件缺失/损坏/非对象统一返回 None（调用方各自定语义）。"""
        path = self._session_dir / name
        try:
            raw = json.loads(path.read_bytes().decode('utf-8'))
        except (OSError, UnicodeDecodeError, ValueError):
            return None
        return raw if isinstance(raw, dict) else None
