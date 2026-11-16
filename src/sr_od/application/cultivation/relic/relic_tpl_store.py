"""遗器域识别模板 store:模板库单一入口 + 五个只读派生视图。

模板库 = ``assets/template/relic_icon/<template_id>/raw.webp``。命名约定即注册表:
- 目录名 == ``f'{RelicSetDef.id}_{RELIC_POS_EN[pos]}'`` → 该套装该部位的单件模板;
- 其余 → 资产命名错误,遍历时直接 raise(受控资产错误立即暴露,优于静默跳过)。
- 国际服词条未同步的套装(套装 id 为空串)尚无 id,不在模板库中,回填后补录
  （7 套 20 件,名单由测试白名单锁定）。

与光锥卡面库的差异:光锥一套一模板(卡面),遗器一套多件(隧洞 4 件/位面 2 件),
template_id 由套装 id + 部位英文组合定位到单件。

消费方(遗器识别)一律经 :class:`RelicTplStore` 的视图属性取模板集,
不得自行扫目录或按名称键拼路径——id 回填、目录增删的归属关系都由本模块
的约定解析统一维护。匹配与锚定归各消费场景自行实现。

store 只注入 TemplateLoader、不持 ctx;五视图(card_faces / tm_prep_tpls /
icon_tpls / icon_feats / icon_hists)全部由盘上静态资产 + mys 常量表确定性
派生,懒构建、构建后只读,无失效场景,不提供清缓存接口。
实例由 SrContext 以 ``@cached_property`` 挂载(ctx 级单例),构建与 ctx 实例
无关——「谁先建」只影响构建时机,不影响内容。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from one_dragon.base.screen.template_loader import TemplateLoader
from one_dragon.utils import cv2_utils, os_utils
from sr_od.mys.sr_relic_sets import (
    RELIC_POS_EN,
    RELIC_SETS,
    RelicSetDef,
    SrRelicPieceDef,
)

if TYPE_CHECKING:
    from one_dragon.base.screen.template_info import TemplateInfo

#: 模板库在 assets/template 下的分类目录名
RELIC_TEMPLATE_SUB_DIR = 'relic_icon'

# masked TM 身份层的模板构建参数(2026-11-11 实机六部位帧验证:真值卡彩色
# NCC 0.93-0.99,全部判对;错误匹配峰值 ~0.93 出现在缩放档错位时,档位对齐
# 后未复现):按绝对目标像素缩放,卡面渲染像素才是常量,比例随模板分辨率
# 派生,混合尺寸模板库禁用「比例」参数(512 件按 256 比例会缩小一半,
# 连结绳全帧误判实证)
_TM_TARGET_PX = 90        # 256 系正源模板的目标像素(卡面渲染实测 ~90px)
_TM_TARGET_PX_ROPE = 92   # 连结绳(pos6,512×512 正源)未选中卡渲染实测 ~92px
_TM_TARGET_PX_ROPE_SEL = 96  # 连结绳选中卡(白框)渲染放大 ~4% → 96px(尺度扫描峰值)
_TM_TARGET_PX_SELECTED = 96  # 256 系选中卡(白框)渲染实测 96px(尺度扫描峰值;与连结绳选中卡同值)

# 角标头像模板的资产布局:avatarminiicon 平铺 png 目录(裸路径读盘,不走
# TemplateLoader,透明圆外由读盘侧取 RGB 丢弃)
_MINI_DIR_REL = 'assets/template/character_avatar_mini'
# 角标 SIFT 特征上采样倍率:两尺度互补(部分角色仅在其一尺度上出足特征);
# 匹配侧 zone 特征提取与构建侧同参(单一源,识别器 import 使用)
_UPSAMPLE_SCALES: tuple[int, ...] = (2, 3)
_SIFT = cv2.SIFT_create(nfeatures=400)


def relic_template_id(relic_set: RelicSetDef, pos: int) -> str:
    """套装 + 部位号 → 模板目录名。pos 坐标系见 SrRelicPieceDef(生成期快照,恒稳)。"""
    return f'{relic_set.id}_{RELIC_POS_EN[pos]}'


@dataclass
class RelicTemplate:
    """单个遗器单件模板条目。

    Attributes:
        template_id: 模板目录名(== 套装 id + 部位英文,TemplateLoader 的 template_id)。
        relic_set: 模板对应的套装定义。
        piece: 模板对应的单件定义(pos 与 template_id 部位段一致)。
        info: 模板信息(raw 与 SIFT 特征惰性加载)。
    """

    template_id: str
    relic_set: RelicSetDef
    piece: SrRelicPieceDef
    info: TemplateInfo


def _fg_mask_from_rgb(rgb: np.ndarray) -> np.ndarray:
    """归档 webp 的前景 mask:四角中位取合成底色,色距 >30 为前景。

    归档模板无 alpha(透明区已合成深紫底),底色平坦不产生匹配信号;TM 逐
    像素比对必须剔除底色,否则底色互相关稀释前景分数。
    """
    corners = np.stack([rgb[:4, :4].reshape(-1, 3), rgb[:4, -4:].reshape(-1, 3),
                        rgb[-4:, :4].reshape(-1, 3), rgb[-4:, -4:].reshape(-1, 3)])
    bg = np.median(corners.reshape(-1, 3), axis=0)
    return np.linalg.norm(rgb.astype(np.float64) - bg[None, None, :], axis=2) > 30


class RelicTplStore:
    """遗器域识别模板的派生视图容器(五视图,懒构建,构建后只读)。

    视图与数据源:
    - card_faces: 模板库读盘 + 命名校验(单一入口);
    - tm_prep_tpls: card_faces 派生(masked TM 模板,256 系与连结绳各按
      双档缩放 + 前景 mask,pos==6 分支保留在构建逻辑内);
    - icon_tpls / icon_feats / icon_hists: 角标头像模板裸路径读盘及其
      SIFT 特征 / HSV 直方图派生。
    """

    def __init__(self, template_loader: TemplateLoader):
        """只注入 loader,不持 ctx:视图内容与 ctx 实例无关,契约测试可零 ctx 自建。"""
        self.template_loader: TemplateLoader = template_loader

    @cached_property
    def card_faces(self) -> list[RelicTemplate]:
        """模板库全量模板遍历(懒构建,构建后只读)。

        目录名必须命中「有 id 套装 × 部位」组合(空 id 套装不入库),违者 raise;
        模板缺失(raw 读不到)视为资产错误 raise,与命名校验同一口径。
        """
        # 预期入库集合:非空 id 套装全部件 → template_id
        expected: dict[str, tuple[RelicSetDef, SrRelicPieceDef]] = {
            relic_template_id(relic_set, piece.pos): (relic_set, piece)
            for relic_set in RELIC_SETS if relic_set.id
            for piece in relic_set.pieces
        }
        root = os_utils.get_path_under_work_dir('assets', 'template', RELIC_TEMPLATE_SUB_DIR)
        entries: list[RelicTemplate] = []
        for dir_name in sorted(os.listdir(root)):
            full = os.path.join(root, dir_name)
            if not os.path.isdir(full):
                continue
            hit = expected.get(dir_name)
            if hit is None:
                raise ValueError(
                    f'遗器模板库存在不合命名约定的目录: {dir_name}'
                    f'(应为 套装id_部位英文,如 spacesealingstation_planarsphere)')
            relic_set, piece = hit
            info = self.template_loader.get_template(RELIC_TEMPLATE_SUB_DIR, dir_name)
            if info is None or info.raw is None:
                raise ValueError(f'遗器模板缺失原图: {dir_name}')
            entries.append(RelicTemplate(dir_name, relic_set, piece, info))
        return entries

    @cached_property
    def tm_prep_tpls(self) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
        """遗器件名 → [(RGB 模板, 前景 mask), ...] 按档位,已缩放到目标像素。

        模板经模板库单一入口 card_faces 取。缩放按模板原始尺寸归一:
        256 系正源 → 90/96 双档、512 连结绳 → 92/96 双档——卡面渲染像素才是
        常量,比例随模板分辨率派生;双档覆盖列表常态与选中卡(白框)的放大渲染。
        """
        prep: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {}
        for entry in self.card_faces:
            img = entry.info.raw
            mask = _fg_mask_from_rgb(img)
            # 双档:主档(未选中卡渲染) + 选中档(选中卡白框放大 ~4%)。
            # 相似件分数接近时,选中卡的放大差足以让次优件反超(行1列2 死水头
            # 被透镜反超实证),双档级联为必需而非可选。
            targets = ((_TM_TARGET_PX_ROPE, _TM_TARGET_PX_ROPE_SEL) if entry.piece.pos == 6
                       else (_TM_TARGET_PX, _TM_TARGET_PX_SELECTED))
            entries = []
            for target in targets:
                tpl = cv2.resize(img, (target, target), interpolation=cv2.INTER_AREA).astype(np.float32)
                mask_s = (cv2.resize(mask.astype(np.uint8), (target, target),
                                     interpolation=cv2.INTER_NEAREST) * 255).astype(np.uint8)
                entries.append((tpl, mask_s))
            prep[entry.piece.name] = entries
        return prep

    @cached_property
    def icon_tpls(self) -> dict[str, np.ndarray]:
        """全部角标头像模板 RGB。avatarminiicon 为 RGBA(圆外透明),取 RGB 三通道。"""
        out: dict[str, np.ndarray] = {}
        base = Path(os_utils.get_path_under_work_dir(*_MINI_DIR_REL.split('/')))
        for f in sorted(base.glob('*.png')):
            img = cv2_utils.read_image(str(f))
            if img is None:
                continue
            if img.ndim == 3 and img.shape[2] == 4:
                img = img[:, :, :3]
            out[f.stem] = img
        return out

    @cached_property
    def icon_feats(self) -> dict[str, dict[int, tuple[list, np.ndarray | None]]]:
        """角标头像模板特征:名字 → 尺度 → (关键点, 描述子);描述子 None = 该尺度特征贫乏。"""
        out: dict[str, dict[int, tuple[list, np.ndarray | None]]] = {}
        for name, img in self.icon_tpls.items():
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            by_scale: dict[int, tuple[list, np.ndarray | None]] = {}
            for k in _UPSAMPLE_SCALES:
                g_up = cv2.resize(gray, (gray.shape[1] * k, gray.shape[0] * k),
                                  interpolation=cv2.INTER_CUBIC)
                by_scale[k] = _SIFT.detectAndCompute(g_up, None)
            out[name] = by_scale
        return out

    @cached_property
    def icon_hists(self) -> dict[str, np.ndarray]:
        """角标头像模板 HSV 色相/饱和直方图(模板圆内采样,归一化)。"""
        out: dict[str, np.ndarray] = {}
        for name, img in self.icon_tpls.items():
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            mask = np.zeros(img.shape[:2], np.uint8)
            cv2.circle(mask, (img.shape[1] // 2, img.shape[0] // 2),
                       int(img.shape[0] * 0.45), 255, -1)
            hist = cv2.calcHist([hsv], [0, 1], mask, [32, 32], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            out[name] = hist
        return out
