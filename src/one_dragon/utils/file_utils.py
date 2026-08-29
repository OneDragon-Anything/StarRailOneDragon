import zipfile
from functools import cache
from pathlib import Path


@cache
def get_project_root() -> Path:
    """定位仓库根目录（src/ 的上级）。

    为什么集中在这里：包内各模块原先各自用 ``Path(__file__).parents[N]``
    硬编码目录深度，文件挪层（如分包重构移动目录）时会静默指错路径；
    统一走本函数后，深度计算只在本文件维护一处。
    锚定方式 = 本文件自身向上找最近的 ``src`` 目录再取上级，
    对 ``src/one_dragon`` 与 ``src/sr_od`` 等任意顶层包的调用方一致成立；
    结果与调用方文件位置无关，故进程内缓存安全。
    """
    src_dir = find_src_dir(Path(__file__).resolve())
    if src_dir is None:
        raise RuntimeError(f'无法从 {__file__} 定位 src 目录,仓库布局异常')
    return src_dir.parent


def find_src_dir(file_path: Path | str) -> Path | None:
    """从文件路径中查找最后一个 'src' 目录

    反向查找路径中最后一个名为 'src' 的目录，返回该目录的完整路径。

    Args:
        file_path: 文件或目录的路径

    Returns:
        Path | None: src 目录路径（含 src 本身），找不到返回 None
    """
    parts = Path(file_path).parts
    try:
        src_index = len(parts) - parts[::-1].index('src') - 1
        return Path(*parts[:src_index + 1])
    except ValueError:
        return None


def unzip_file(zip_file_path: str, unzip_dir_path: str) -> bool:
    """
    解压一个压缩包
    :param zip_file_path: 压缩包文件的路径。
    :param unzip_dir_path: 解压位置的文件夹
    :return: 是否解压成功
    """
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(unzip_dir_path)
        return True
    except Exception:
        return False
