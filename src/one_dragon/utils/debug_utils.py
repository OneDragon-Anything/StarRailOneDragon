import io
import os
import time
from functools import lru_cache
from typing import Optional

import cv2
import win32clipboard
import win32con
from cv2.typing import MatLike
from PIL import Image

from one_dragon.utils import cv2_utils, os_utils
from one_dragon.utils.log_utils import log


@lru_cache
def get_debug_dir_path() -> str:
    return os_utils.get_path_under_work_dir('.debug')


@lru_cache()
def get_debug_image_dir_path() -> str:
    return os_utils.get_path_under_work_dir('.debug', 'images')


def get_debug_image_path(filename, suffix: str = '.png') -> str:
    return os.path.join(get_debug_image_dir_path(), filename + suffix)


def get_debug_image(filename, suffix: str = '.png') -> MatLike:
    return cv2_utils.read_image(get_debug_image_path(filename, suffix))


def copy_image_to_clipboard(image) -> bool:
    """将图片复制到剪贴板"""
    try:
        pil_image = Image.fromarray(image)
        with io.BytesIO() as output:
            pil_image.save(output, "BMP")
            data = output.getvalue()[14:]  # 跳过BMP文件头，获取DIB数据

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, data)
            log.debug('图片已复制到剪贴板')
            return True
        finally:
            win32clipboard.CloseClipboard()
    except Exception as e:
        log.error('无法将图片复制到剪贴板: %s', e)
        return False


def save_debug_image(image, file_name: Optional[str] = None, prefix: str = '', copy_screenshot: bool = False) -> str:
    """保存调试图片到文件，可选择是否同时复制到剪贴板

    契约:成功返回 ``file_name``(**非完整路径**;自动生成时为
    ``<prefix>_<毫秒时间戳>``,完整路径 = .debug/images/<file_name>.png);
    失败(图像数据/目录/写入)返回**空串**——调用方以返回值非空判断落盘
    成功,勿拿返回值当路径直接读文件。

    写入失败(目录缺失/磁盘/编码)时 log.error 并返回空串——调试截图常被
    停机钩子当取证证据(外层多为 best-effort 包装),静默假成功会让证据
    缺失不可见(2026-09-02 夜间语料批局1:取证图被吞后无任何日志线索)。
    """
    if file_name is None:
        file_name = '%s_%d' % (prefix, round(time.time() * 1000))
    path = get_debug_image_path(file_name)
    log.debug('临时图片保存 %s', path)

    bgr_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    if not cv2.imwrite(path, bgr_image):
        log.error('调试图片写入失败 %s(imwrite 返回 False,检查目录/权限/图像数据)', path)
        return ''

    if copy_screenshot:
        copy_image_to_clipboard(image)

    return file_name
