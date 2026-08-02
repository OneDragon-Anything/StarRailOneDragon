import winreg

from one_dragon.utils.log_utils import log


class RegistryPatch:
    """注册表补丁：修改指定键值并在之后恢复原始值。

    用法:
        patch = RegistryPatch(subkey, root=winreg.HKEY_CURRENT_USER)
        patch.backup_and_set({
            'ValueName': (data, winreg.REG_DWORD),
            ...
        })
        # ... 做需要的事 ...
        patch.restore()
    """

    def __init__(self, subkey: str, root: int = winreg.HKEY_CURRENT_USER):
        self._root = root
        self._subkey = subkey
        self._backup: dict[str, tuple[bytes | int, int]] | None = None

    @property
    def has_backup(self) -> bool:
        return self._backup is not None

    def backup_and_set(self, values: dict[str, tuple[bytes | int, int]]) -> bool:
        """备份 *values* 中涉及的键值，然后写入新值。

        :param values: {name: (data, reg_type)} 要写入的注册表值
        :return: 是否写入成功
        """
        try:
            with winreg.CreateKeyEx(self._root, self._subkey, 0,
                                    winreg.KEY_READ | winreg.KEY_WRITE) as key:
                # 备份现有值
                self._backup = _read_values(key, set(values.keys()))

                # 写入新值
                for name, (data, reg_type) in values.items():
                    winreg.SetValueEx(key, name, 0, reg_type, data)
            return True
        except OSError:
            log.exception('注册表写入失败: %s', self._subkey)
            return False

    def restore(self) -> None:
        """恢复之前备份的注册表值。仅恢复一次，调用后备份清空。

        恢复失败时保留备份，以便后续重试。
        """
        if self._backup is None:
            return

        try:
            with winreg.CreateKeyEx(self._root, self._subkey, 0,
                                    winreg.KEY_WRITE) as key:
                for name, (data, reg_type) in self._backup.items():
                    winreg.SetValueEx(key, name, 0, reg_type, data)
            self._backup = None
            log.info('注册表已恢复: %s', self._subkey)
        except OSError:
            log.exception('注册表恢复失败（备份已保留，可重试）: %s', self._subkey)


def _read_values(key: winreg.HKEYType, names: set[str]) -> dict[str, tuple[bytes | int, int]]:
    """从已打开的注册表键中读取指定名称的值。"""
    _, num_values, _ = winreg.QueryInfoKey(key)
    result: dict[str, tuple[bytes | int, int]] = {}
    for i in range(num_values):
        name, data, reg_type = winreg.EnumValue(key, i)
        if name in names:
            result[name] = (data, reg_type)
    return result
