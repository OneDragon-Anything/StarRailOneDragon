"""账号档案扫描的识别核心。

两部分:
- AvatarMatcher:角色列表头像识别(动态格定位 + SIFT 匹配,模板库 config/idx/avatar_scan/ 本地快照)
- normalize_cn_name:角色名统一清洗(SIFT 映射名 / OCR 读名 / 历史档案加载 三路共用)

格定位思路(2026-10-19 实测定稿):列表滚动后格位随内容变化,固定 4x6 网格会错位;
每个完整可见格的底部都有「等级 N」底标文本,OCR 找齐全部底标即得全部完整格,
截断的半行无底标,天然排除。
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from cv2.typing import MatLike

from one_dragon.utils.cv2_utils import feature_match_for_one

ASSET_DIR: Path = Path('config') / 'idx' / 'avatar_scan'
MINI_DIR_NAME: str = 'avatarminiicon'
MAP_FILE_NAME: str = 'characters-full.json'

MIN_CONF: float = 0.55

# 列表区右界(1080p):角色列表侧栏 x < 600,右侧详情页的「等级80/80」据此排除
LIST_X_MAX: int = 600
# 「等级」标签锚定的头像识别区:标签左上 (lx,ly) → 裁剪 (lx-PAD, ly-UP, lx+w+PAD, ly+h+DOWN)
LABEL_PAD_X: int = 40
LABEL_UP: int = 115
LABEL_DOWN: int = 10
# 点击点:标签中心上方 50px(格子中部,避开关底标)
CLICK_UP: int = 50

# 玩家昵称黑名单前缀(全大写比较):OCR 会把详情页昵称误读为角色名
_NAME_BLOCKLIST_PREFIX: tuple[str, ...] = ('MOMOJ',)
# 名字长度上限(「银狼LV.999」类噪声超长;真名最长如「开拓者·欢愉」7 字)
_NAME_MAX_LEN: int = 12
# 读名别名:OCR 变体/易混字/映射表噪声 → 档案主名(实机噪声归并,2026-10-19)
_NAME_ALIAS: dict[str, str] = {
    '傑帕德': '杰帕德',
    '千冶·刀': '千冶·刃',
    '欢愉': '开拓者·欢愉',
    '知更鸟·晴歌': '知更鸟',
    '砂金·戏浪': '砂金',
    '银狼LV.999': '银狼',
}


def normalize_cn_name(raw: str | None) -> str | None:
    """角色名统一清洗:噪声名返回 None(调用方跳过该来源);合法名归一化。

    三路共用:SIFT 映射名(cn_name——映射表本身有采集噪声「银狼LV.999」)、
    OCR 读名、历史档案加载。实测噪声形态:
    - 名字串等级:「银狼LV.999」
    - OCR 读名噪声:emoji/纯符号(🌟)、玩家昵称变体(Momojile)、截断片段(·梅)
    - 间隔号双形:映射表用 •,读名用 ·,统一为 ·
    - 易混字/变体:傑帕德/千冶·刀/欢愉 等,按 _NAME_ALIAS 归并
    """
    if raw is None:
        return None
    name = raw.replace('★', '').replace('☆', '').replace('🌟', '').strip()
    if not name:
        return None
    if name.upper().startswith(_NAME_BLOCKLIST_PREFIX):
        return None
    if len(name) > _NAME_MAX_LEN:
        return None
    if name.startswith('·') or name.startswith('•'):
        return None
    if name[0].isdigit():
        # 纯数字/数字开头 = 模板键泄漏的 avatarId,不是角色名
        return None
    if 'LV' in name.upper() and any(ch.isdigit() for ch in name):
        return None
    valid = sum(
        1 for ch in name
        if (ch.isascii() and ch.isalnum()) or '\u4e00' <= ch <= '\u9fff' or ch in '·•-'
    )
    # 全中文单字真名(如「刃」)放行;两个以上有效字符才要求混合可读
    if valid < 1:
        return None
    if valid == 1 and not all('\u4e00' <= ch <= '\u9fff' for ch in name):
        return None
    result = name.replace('•', '·')
    return _NAME_ALIAS.get(result, result)


def imread_gray(path: Path) -> MatLike:
    """读灰度图;np.fromfile + imdecode 支持 non-ASCII 路径(cv2.imread 不支持)。"""
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)


class AvatarMatcher:
    """角色列表头像识别器:OCR 定位格子 + SIFT 匹配头像。"""

    def __init__(self, asset_dir: Path = ASSET_DIR):
        self._id_map: dict[str, dict] = {}
        map_path = asset_dir / MAP_FILE_NAME
        if map_path.exists():
            with open(map_path, encoding='utf-8') as f:
                self._id_map = json.load(f)

        self._sift = cv2.SIFT_create()
        self._tpl_feats: dict[str, tuple[MatLike, any, any]] = {}
        mini_dir = asset_dir / MINI_DIR_NAME
        if mini_dir.is_dir():
            for fn in mini_dir.iterdir():
                if fn.suffix != '.png':
                    continue
                # 文件名是 avatarId 数字,先经映射表转中文名再清洗(数字 ID 不是名字)
                cn = normalize_cn_name(self.cn_name(fn.stem))
                if cn is None:
                    continue
                tpl_img = imread_gray(fn)
                kp, desc = self._sift.detectAndCompute(tpl_img, None)
                self._tpl_feats[cn] = (tpl_img, kp, desc)
        # manual 目录:游戏内截图裁片模板,文件名 = 中文名(真珠等映射表缺失角色);
        # 截图裁片与运行时渲染同源,作为解包 mini 图的补充
        manual_dir = asset_dir / 'manual'
        if manual_dir.is_dir():
            for fn in manual_dir.iterdir():
                if fn.suffix != '.png':
                    continue
                tpl_img = imread_gray(fn)
                kp, desc = self._sift.detectAndCompute(tpl_img, None)
                self._tpl_feats[fn.stem] = (tpl_img, kp, desc)

    @property
    def template_count(self) -> int:
        """已载入的模板数,0 = 资产缺失(调用方应报错而非空转)。"""
        return len(self._tpl_feats)

    def cn_name(self, avatar_id: str) -> str | None:
        """avatarId → 清洗后中文名;映射外/清洗不过(映射表采集噪声)返回 None,调用方走读名兜底。"""
        info = self._id_map.get(avatar_id)
        return normalize_cn_name(info.get('cn') if info else None)

    def detect_cells(self, screen: MatLike, ocr_func) -> list[dict]:
        """动态识别列表格:以每个「等级」底标为锚,标出全部完整可见格并识别头像。

        :param ocr_func: ctx.ocr.ocr(全文 OCR 函数)
        :return: 元素 {lx, ly, cx, cy, abs_key, cn, conf, miss}
            lx/ly = 标签左上;cx/cy = 点击点;
            abs_key = (标签锚定绝对纵坐标, 标签横坐标) —— 滚动后同一格 abs_key 不变,去重用;
            cn/conf = SIFT 结果(cn 可能为 None = 映射噪声);miss = SIFT 未命中,调用方点击读名兜底
        """
        cells: list[dict] = []
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        ocr_results = ocr_func(screen)
        for r in ocr_results:
            text = str(r.data or '')
            if '等级' not in text:
                continue
            lx, ly = int(r.x), int(r.y)
            w, h = int(r.w), int(r.h)
            if lx > LIST_X_MAX:
                continue
            x0 = max(0, lx - LABEL_PAD_X)
            y0 = max(0, ly - LABEL_UP)
            x1 = min(screen.shape[1], lx + w + LABEL_PAD_X)
            y1 = min(screen.shape[0], ly + h + LABEL_DOWN)
            avatar = gray[y0:y1, x0:x1]
            best_id, best_conf = self._match_avatar(avatar)
            cn = best_id if best_id else None
            miss = cn is None
            cells.append({
                'lx': lx, 'ly': ly, 'w': w,
                'cx': lx + w // 2,
                'cy': ly - CLICK_UP,
                'abs_key': (round((ly + CLICK_UP) / 40), round((lx + w // 2) / 60)),
                'cn': cn,
                'conf': round(best_conf, 3),
                'miss': miss,
            })
        return cells

    def _match_avatar(self, avatar_crop: MatLike) -> tuple[str | None, float]:
        """单格头像 SIFT 匹配,返回 (最佳模板名=角色中文名, 置信度);无有效特征返回 (None, 0)。"""
        kp, desc = self._sift.detectAndCompute(avatar_crop, None)
        best_id: str | None = None
        best_conf: float = 0.0
        for avatar_id, (tpl_img, tpl_kp, tpl_desc) in self._tpl_feats.items():
            m = feature_match_for_one(kp, desc, tpl_kp, tpl_desc, tpl_img.shape[1], tpl_img.shape[0])
            if m is not None and m.confidence > best_conf:
                best_conf, best_id = m.confidence, avatar_id
        return best_id, best_conf


def ocr_rect_texts(ocr_func, screen: MatLike, rect: tuple[int, int, int, int]) -> list[str]:
    """按 (x0, y0, x1, y1) 裁剪截图并 OCR,返回文本列表。

    ocr_func = ctx.ocr.ocr(全文 OCR 函数,本函数先裁剪再识别)。
    坐标单一真相源在 screen_info 读区;调用方经 screen_loader.get_area 取 rect 传入。
    """
    x0, y0, x1, y1 = rect
    crop = screen[y0:y1, x0:x1]
    results = ocr_func(crop)
    return [str(r.data or '').strip() for r in results if str(r.data or '').strip()]
