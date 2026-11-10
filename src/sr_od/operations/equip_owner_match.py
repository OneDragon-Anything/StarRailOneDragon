"""装备列表卡「占用者识别」:角标区角色头像 SIFT 特征匹配 + 双证据合取。

替换列表每件装备右上角的圆形头像角标 = 当前装备者的游戏渲染;模板库 =
avatarminiicon 64×64 圆形头像原样(``assets/template/character_avatar_mini/``,
文件名 = Character.id,生成器见私有 skill ``sr-od-dev-character-data``)。

识别 = 结构证据 × 颜色证据,四道判定按序:
1. SIFT 双尺度上采样(×2/×3)特征匹配,全库竞争取最高 RANSAC 内点数 ——
   64px 小图原生特征贫乏,上采样后特征大量出现且两尺度互补;场景特征
   每尺度只提取一次,模板逐个比对;
2. Lowe 比值 0.7:放宽到 0.75/0.8 时无角标卡面(纯卡面装饰/星空背景)会
   出现 15-29 内点的假一致(RANSAC 在装饰纹样上凑满阈),0.7 下无角标
   卡面内点天花板 11、真角标最低 18,真假分离;
3. 内点数 ≥ 阈值(15)且颜色验证通过:最高内点模板的 HSV 色相/饱和直方图
   (角标内圆 vs 模板圆)Bhattacharyya 距离全库排名 <5 —— 直方图与结构
   证据独立,假一致内点的模板颜色必然不符,防止结构闸被假内点击穿;
4. 歧义降级:次高模板(不同角色)内点 ≥ 0.75×最高且也过阈 → 返回 None
   不猜(两个模板相争 = 证据不唯一,诚实交给上层)。

方法矩阵实测排除(48 用例基准逐一对比):matchTemplate 多尺度(真假分数带
重叠)、圆形掩码 NCC(掩码分数真假同带)、ORB(无角标假阳性)、AKAZE(误识)、
pHash(全错);HSV 直方图单项 argmax 全对但纯颜色无法区分同色系角色,
只作验证闸不作主判。基准固化为
``sr-od-test/test/sr_od/operations/test_equip_owner_match.py``
(3 帧整屏 fixture,21 真角标 + 27 无角标逐卡位人工标注真值)。

实测:21 真角标 0 漏 0 误,27 无角标 0 假;真角标内点 18-61、无角标卡面
最高 11。全部模板低于阈值 = 未装备或角标角色不在模板库,诚实返回 None
(不猜测,上层按「不抢」语义处理)。

角标窗 = 角标整圆外接正方形(光锥:卡内 (x1+95,y1+9)~(x1+139,y1+53) 44×44,
圆心≈(x1+117,y1+31) 外径≈44px,Canny 环拟合 7 卡一致;遗器:卡右上角
(x2-55,y1+10)~(x2+6,y1+62),圆心≈(x2-19,y1+34) 直径≈40px,网格判读标定),
由调用方按所在界面传入;匹配时内部扩边 ±16 吸收定位偏差与列表选中卡轻微
放大导致的角标溢出。

遗器侧标定(2026-11-10 实机 3 帧审计,与光锥同参数直接可用):遗器角标直径
≈40px(小于光锥 44px),真角标内点 16-30、无角标卡面内点 4-8 —— 阈 15 两侧
余量 +1/-7,真角标最低余量薄于光锥(18)但假阳性侧更厚,同一阈值成立;
12 件在穿副本跨 3 帧 15 正例全中、25 负例零假。语义实证:遗器替换列表角标
=当前穿着者(与光锥同),仓库件无角标 —— 旧「仓库件也有头像」结论系误读,
已推翻。
"""

import re
from pathlib import Path

import cv2
import numpy as np

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils import cv2_utils, os_utils
from sr_od.config.character_const import get_character_by_id

_MINI_DIR_REL = 'assets/template/character_avatar_mini'
# 角标窗边长与匹配扩边:扩边吸收调用方定位偏差与选中卡放大溢出
_TEMPLATE_SIZE: int = 44
_ZONE_PAD: int = 16
# 上采样倍率:两尺度互补(部分角色仅在其一尺度上出足特征)
_UPSAMPLE_SCALES: tuple[int, ...] = (2, 3)
# Lowe 比值阈值(见模块 docstring 第 2 条:0.75+ 会让假一致内点过阈)
_LOWES_RATIO: float = 0.7
# 内点判定阈(光锥真角标 18-61 / 无角标卡面 ≤11;遗器真 16-30 / 无角标 4-8
# —— 两界面共用,偏真侧留漏报余量)
OWNER_MATCH_MIN_INLIERS: int = 15
# 颜色验证闸:最高内点模板的直方图距离全库排名须小于此值
_HIST_RANK_MAX: int = 5
# 歧义降级:次高(不同角色)内点 ≥ 最高×此比例且 ≥ 内点阈 → None
_AMBIG_RATIO: float = 0.75
# 场景侧直方图采样圆半径(zone 76×76 内的角标内圆)
_ZONE_HIST_RADIUS: int = 19

_SIFT = cv2.SIFT_create(nfeatures=400)
_MATCHER = cv2.BFMatcher()

_tpl_cache: dict[str, np.ndarray] | None = None
_feat_cache: dict[str, dict[int, tuple[list, np.ndarray | None]]] | None = None
_hist_cache: dict[str, np.ndarray] | None = None


def _templates() -> dict[str, np.ndarray]:
    """全部模板 RGB。avatarminiicon 为 RGBA(圆外透明),取 RGB 三通道。"""
    global _tpl_cache
    if _tpl_cache is not None:
        return _tpl_cache
    out: dict[str, np.ndarray] = {}
    base = Path(os_utils.get_path_under_work_dir(*_MINI_DIR_REL.split('/')))
    for f in sorted(base.glob('*.png')):
        img = cv2_utils.read_image(str(f))
        if img is None:
            continue
        if img.ndim == 3 and img.shape[2] == 4:
            img = img[:, :, :3]
        out[f.stem] = img
    _tpl_cache = out
    return out


def _tpl_features() -> dict[str, dict[int, tuple[list, np.ndarray | None]]]:
    """模板特征缓存:名字 → 尺度 → (关键点, 描述子);描述子 None = 该尺度特征贫乏。"""
    global _feat_cache
    if _feat_cache is not None:
        return _feat_cache
    out: dict[str, dict[int, tuple[list, np.ndarray | None]]] = {}
    for name, img in _templates().items():
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        by_scale: dict[int, tuple[list, np.ndarray | None]] = {}
        for k in _UPSAMPLE_SCALES:
            g_up = cv2.resize(gray, (gray.shape[1] * k, gray.shape[0] * k),
                              interpolation=cv2.INTER_CUBIC)
            by_scale[k] = _SIFT.detectAndCompute(g_up, None)
        out[name] = by_scale
    _feat_cache = out
    return out


def _tpl_hists() -> dict[str, np.ndarray]:
    """模板 HSV 色相/饱和直方图缓存(模板圆内采样,归一化)。"""
    global _hist_cache
    if _hist_cache is not None:
        return _hist_cache
    out: dict[str, np.ndarray] = {}
    for name, img in _templates().items():
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        mask = np.zeros(img.shape[:2], np.uint8)
        cv2.circle(mask, (img.shape[1] // 2, img.shape[0] // 2),
                   int(img.shape[0] * 0.45), 255, -1)
        hist = cv2.calcHist([hsv], [0, 1], mask, [32, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        out[name] = hist
    _hist_cache = out
    return out


def _inliers_at_scale(kp_z: list, des_z: np.ndarray | None,
                      tkp: list, tdesc: np.ndarray | None) -> int:
    """单尺度匹配:knnMatch(Lowe ratio)+ RANSAC,返回内点数。"""
    if des_z is None or tdesc is None or len(kp_z) < 4 or len(tkp) < 4 or len(des_z) < 4:
        return 0
    matches = _MATCHER.knnMatch(tdesc, des_z, k=2)
    good = [m[0] for m in matches
            if len(m) == 2 and m[0].distance < _LOWES_RATIO * m[1].distance]
    if len(good) < 4:
        return 0
    src = np.float32([tkp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_z[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    _, ransac_mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    return int(ransac_mask.sum()) if ransac_mask is not None else 0


def match_owner(screen_rgb: np.ndarray, badge_rect: Rect,
                min_inliers: int = OWNER_MATCH_MIN_INLIERS) -> tuple[str | None, int]:
    """识别角标区的占用角色,返回**中文角色名**(如「黄泉」)。

    流程:角标窗扩边 → 场景 SIFT 特征(每尺度一次)→ 全库模板双尺度比对
    → 内点阈 → 直方图距离排名验证 → 歧义降级 → 中文名。

    :param screen_rgb: 整屏截图(RGB)
    :param badge_rect: 角标检测区(调用方按所在界面的角标偏移换算,见各 op 常量;
        窗须完整含角标圆,内部自动扩边吸收定位偏差)
    :param min_inliers: RANSAC 内点数判定阈
    :return: (中文角色名, 最高内点数);任一道判定不过返回 (None, 最高内点数) ——
        未装备 / 角标角色不在模板库 / 证据歧义,不猜测。中文映射缺失的角色
        兜底返回模板英文 id。
    """
    x1 = max(0, badge_rect.x1 - _ZONE_PAD)
    y1 = max(0, badge_rect.y1 - _ZONE_PAD)
    x2 = min(screen_rgb.shape[1], badge_rect.x2 + _ZONE_PAD)
    y2 = min(screen_rgb.shape[0], badge_rect.y2 + _ZONE_PAD)
    zone = screen_rgb[y1:y2, x1:x2]
    if zone.size == 0:
        return None, 0
    if zone.ndim == 3 and zone.shape[2] == 4:
        zone = zone[:, :, :3]
    gray_zone = cv2.cvtColor(zone, cv2.COLOR_RGB2GRAY)

    zone_feats: dict[int, tuple[list, np.ndarray | None]] = {}
    for k in _UPSAMPLE_SCALES:
        g_up = cv2.resize(gray_zone, (gray_zone.shape[1] * k, gray_zone.shape[0] * k),
                          interpolation=cv2.INTER_CUBIC)
        zone_feats[k] = _SIFT.detectAndCompute(g_up, None)

    per: dict[str, int] = {}
    for name, by_scale in _tpl_features().items():
        per[name] = max(_inliers_at_scale(*zone_feats[k], *by_scale[k])
                        for k in _UPSAMPLE_SCALES)
    order = sorted(per.items(), key=lambda kv: -kv[1])
    best_name, best_inliers = order[0]
    if best_inliers < min_inliers:
        return None, best_inliers

    dists = {n: cv2.compareHist(h, _zone_hist(zone), cv2.HISTCMP_BHATTACHARYYA)
             for n, h in _tpl_hists().items()}
    hist_rank = sorted(dists, key=dists.get).index(best_name)
    if hist_rank >= _HIST_RANK_MAX:
        return None, best_inliers

    if len(order) > 1:
        second_name, second_inliers = order[1]
        if (_owner_cn(second_name) != _owner_cn(best_name)
                and second_inliers >= _AMBIG_RATIO * best_inliers
                and second_inliers >= min_inliers):
            return None, best_inliers

    return _owner_cn(best_name), best_inliers


def _zone_hist(zone_rgb: np.ndarray) -> np.ndarray:
    """场景侧直方图:角标窗中心内圆采样(与模板圆同口径)。"""
    hsv = cv2.cvtColor(zone_rgb, cv2.COLOR_RGB2HSV)
    mask = np.zeros(zone_rgb.shape[:2], np.uint8)
    cv2.circle(mask, (zone_rgb.shape[1] // 2, zone_rgb.shape[0] // 2),
               _ZONE_HIST_RADIUS, 255, -1)
    hist = cv2.calcHist([hsv], [0, 1], mask, [32, 32], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    return hist


def _owner_cn(template_name: str) -> str:
    """模板名 → 中文角色名;皮肤模板(`<角色id>_skin<衣装号>`)剥后缀归一。

    模板文件名 = Character.id(生成器按 character_const 保证),
    character_const 直接可查;未收录的角色(库先于角色录入更新)兜底
    返回模板名原串,不猜测。"""
    character = get_character_by_id(template_name)
    if character is not None:
        return character.cn
    base = re.sub(r'_skin\d+$', '', template_name)
    if base != template_name:
        character = get_character_by_id(base)
        if character is not None:
            return character.cn
    return template_name
