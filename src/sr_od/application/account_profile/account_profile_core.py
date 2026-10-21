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
from typing import TYPE_CHECKING

import cv2
from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.screen.template_loader import TemplateLoader
from one_dragon.utils.cv2_utils import feature_match_for_one

if TYPE_CHECKING:
    from one_dragon.base.matcher.template_matcher import TemplateMatcher

ASSET_DIR: Path = Path('config') / 'idx' / 'avatar_scan'
MINI_DIR_NAME: str = 'avatarminiicon'
MAP_FILE_NAME: str = 'characters-full.json'

MIN_CONF: float = 0.55

# 列表区右界(1080p):角色列表侧栏 x < 600,右侧详情页的「等级80/80」据此排除
LIST_X_MAX: int = 600
# 「等级」标签锚定的头像识别区:标签左上 (lx,ly) → 裁剪 (lx-PAD, ly-UP, lx+w+PAD, ly+h+DOWN)
LABEL_PAD_X: int = 40
LABEL_UP: int = 80  # 等级文本上方到头像顶 ≈75px;旧值 115 会把上一行角色顶部圈进来干扰匹配
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
        self._tpl_loader = TemplateLoader()  # 统一模板服务:加载 + 特征懒缓存(features.xml 落盘)
        # 模板源 = 项目已有角色头像库(330 个,含全部角色);id 混合中英文,读名兜底定中文名
        self._tpl_names = [i.template_id for i in self._tpl_loader.get_all_template_info_from_disk(
            need_raw=True, need_config=False)
            if i.template_id and i.sub_dir == 'character_avatar']
    @property
    def template_count(self) -> int:
        """已载入的模板数,0 = 资产缺失(调用方应报错而非空转)。"""
        return len(self._tpl_names)

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
        gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)  # 框架截图为 RGB(imread 读文件才是 BGR),灰度权重不能反
        ocr_results = ocr_func(screen)
        for r in ocr_results:
            text = str(r.data or '')
            if '等级' not in text:
                continue
            lx, ly = int(r.x), int(r.y)
            w = int(r.w)
            if lx > LIST_X_MAX:
                continue
            # 头像 93px 见方以等级文本中心对齐;横向 ±40 pad 会把相邻格子的边缘圈进来干扰 SIFT
            cx = lx + w // 2
            avatar_top = max(0, ly - 75)
            avatar = gray[avatar_top:ly + 20, cx - 46:cx + 46]
            best_id, best_conf = self._match_avatar(avatar)
            cn = best_id if best_id else None
            miss = cn is None
            cells.append({
                'lx': cx - 46, 'ly': avatar_top, 'w': 92,
                'cx': cx,
                'cy': ly - CLICK_UP,
                'abs_key': (round((ly - CLICK_UP) / 40), round(cx / 60)),
                'cn': cn,
                'conf': round(best_conf, 3),
                'miss': miss,
            })
        return cells

    def _match_avatar(self, avatar_crop: MatLike) -> tuple[str | None, float]:
        """单格头像经框架模板服务逐个特征匹配,返回 (角色中文名, 置信度);全失败返回 (None, 0)。"""
        kp, desc = self._sift.detectAndCompute(avatar_crop, None)
        best_id: str | None = None
        best_conf: float = 0.0
        for cn in self._tpl_names:
            tpl = self._tpl_loader.get_template('character_avatar', cn)
            if tpl is None:
                continue
            tpl_kps, tpl_desc = tpl.features
            m = feature_match_for_one(kp, desc, tpl_kps, tpl_desc,
                                      tpl.raw.shape[1], tpl.raw.shape[0])
            if m is not None and m.confidence > best_conf:
                best_conf, best_id = m.confidence, cn
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


# 星魂挂锁识别:模板与阈值单一源(app 与测试共用)
EIDOLON_LOCK_TEMPLATE_SUB_DIR: str = 'account_profile'
EIDOLON_LOCK_TEMPLATE_ID: str = 'eidolon_lock'
# 挂锁章为全角色统一 UI 元素,2026-10-21 五角色实机实测:锁位分数 ≥0.945,非锁位 ≤0.578,
# 阈值取中点偏锁侧,两侧余量近 0.2(RGB 口径,TemplateMatcher.crop_and_match_template)
EIDOLON_LOCK_THRESHOLD: float = 0.75


def count_eidolon_locks(tm: TemplateMatcher, screen: MatLike,
                        rects: list[tuple[int, int, int, int]]) -> int:
    """数星魂页 6 个图标位上的挂锁章数量(= 未获得星魂数,eidolon_count = 6 - 锁数)。

    星魂只有两态:已获得(白亮图标无锁)/ 未获得(暗图标 + 挂锁章);
    名字与序号两态恒显示,OCR 数名字恒得 6(曾据此记 eidolon_count,已作废)。
    挂锁章位置固定,锁位 area = 角色-星魂 的 锁位-星魂1图标~6图标(坐标单一真相源在 screen_info)。
    :param tm: 框架模板匹配器(ctx.tm)
    :param screen: 星魂页整页截图(RGB,框架截图口径)
    :param rects: 6 个锁位矩形 (x1,y1,x2,y2),顺序与 星魂N名 读区一致
    :return: 挂锁数量(0-6)
    """
    locked = 0
    for x1, y1, x2, y2 in rects:
        res = tm.crop_and_match_template(
            screen, Rect(x1, y1, x2, y2),
            EIDOLON_LOCK_TEMPLATE_SUB_DIR, EIDOLON_LOCK_TEMPLATE_ID,
            threshold=EIDOLON_LOCK_THRESHOLD)
        if res is not None and len(res) > 0:
            locked += 1
    return locked
