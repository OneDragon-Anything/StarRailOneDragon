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

# 读名别名:OCR 变体/易混字 → 档案主名(实机噪声归并,2026-10-19)
_NAME_ALIAS: dict[str, str] = {
    '傑帕德': '杰帕德',
    '千冶·刀': '千冶·刃',
    '欢愉': '开拓者·欢愉',
    '知更鸟·晴歌': '知更鸟',
    '砂金·戏浪': '砂金',
}
# 权威角色名单(白名单制):由 AvatarMatcher.__init__ 从映射表构建填充。
# 注意官方名含非常规形态(如「银狼LV.999」是欢愉命途银狼的官方名),禁用规则式猜测拒绝。
_KNOWN_NAMES: set[str] = set()


def normalize_cn_name(raw: str | None) -> str | None:
    """角色名统一清洗(白名单制):不在权威名单的名字一律拒绝。

    三路共用:SIFT 映射名(cn_name)/OCR 读名/历史档案加载。
    - 先做形态归一(星标剥离/间隔号统一/别名归并)
    - 再查 _KNOWN_NAMES 权威名单(映射表 cn 全集 + 别名目标);
      官方非常规名(如「银狼LV.999」= 欢愉命途银狼)在名单内,正确保留
    - 名单外(OCR 噪声 🌟/Momojile、模板键泄漏的数字 ID、截断片段)一律拒绝
    _KNOWN_NAMES 由 AvatarMatcher.__init__ 构建填充。
    """
    if raw is None:
        return None
    if not _KNOWN_NAMES:
        # 名单未构建(测试/异常路径):仅做间隔号归一,不拒绝
        return raw.replace('★', '').replace('☆', '').strip().replace('•', '·') or None
    name = raw.replace('★', '').replace('☆', '').replace('🌟', '').strip()
    if not name:
        return None
    result = name.replace('•', '·')
    result = _NAME_ALIAS.get(result, result)
    return result if result in _KNOWN_NAMES else None


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

        # extra 映射先行读取:目标名(映射表缺失角色如真珠)并入权威名单
        extra_map_path = asset_dir / 'extra_templates.json'
        extra_dir = asset_dir / 'extra'
        extra_map: dict[str, str] = {}
        if extra_map_path.exists():
            with open(extra_map_path, encoding='utf-8') as f:
                extra_map = json.load(f)

        # 构建权威名单:映射表 cn 清洗后全集 + 别名归并目标 + extra 目标
        # (银狼LV.999 等官方非常规名依赖「名单内保留」;真珠等映射表缺失角色靠 extra 补)
        for info in self._id_map.values():
            cn = (info.get('cn') or '').replace('•', '·')
            if cn:
                _KNOWN_NAMES.add(cn)
        for target in _NAME_ALIAS.values():
            _KNOWN_NAMES.add(target)
        for target in extra_map.values():
            _KNOWN_NAMES.add(target)

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
        # extra 目录:映射表缺失角色的解包 mini 图(文件名 = avatarpre 英文代号如 Pearl),
        # extra_templates.json 给出 英文代号 → 中文名;图与 mini 主库同源解包资产
        extra_dir = asset_dir / 'extra'
        if extra_dir.is_dir():
            for fn in extra_dir.iterdir():
                if fn.suffix != '.png':
                    continue
                cn = normalize_cn_name(extra_map.get(fn.stem))
                if cn is None:
                    continue
                tpl_img = imread_gray(fn)
                kp, desc = self._sift.detectAndCompute(tpl_img, None)
                self._tpl_feats[cn] = (tpl_img, kp, desc)

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
