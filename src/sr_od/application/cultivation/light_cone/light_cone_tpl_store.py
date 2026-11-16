"""光锥域识别模板 store:卡面库单一入口 + 六个只读派生视图。

卡面库 = ``assets/template/light_cone_icon/<template_id>/raw.webp``。命名约定即注册表:
- 目录名 == ``LightConeDef.id`` → 该光锥的卡面模板;
- 其余 → 资产命名错误,遍历时直接 raise(受控资产错误立即暴露,优于静默跳过)。
- 国际服词条未同步的光锥(id 为空串)尚无 id,不在卡面库中,回填后补录。

消费方(光锥识别)一律经 :class:`LightConeTplStore` 的视图属性取模板集,
不得自行扫目录或按名称键拼路径——id 回填、目录增删的归属关系都由本模块
的约定解析统一维护。匹配与锚定归各消费场景自行实现。

store 只注入 TemplateLoader、不持 ctx;六视图(card_faces / tm_prep_tpls /
superimpose_tpls / icon_tpls / icon_feats / icon_hists)全部由盘上静态资产
+ mys 常量表确定性派生,懒构建、构建后只读,无失效场景,不提供清缓存接口。
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
from sr_od.mys.sr_light_cones import LIGHT_CONES, LightConeDef

if TYPE_CHECKING:
    from one_dragon.base.screen.template_info import TemplateInfo

#: 卡面库在 assets/template 下的分类目录名
LIGHT_CONE_TEMPLATE_SUB_DIR = 'light_cone_icon'

# masked TM 身份层的模板构建参数(实机替换列表 27 卡标定:真值卡彩色
# NCC 0.981-0.995、次高模板天花板 0.961):按绝对目标像素缩放,卡面渲染
# 像素才是常量,比例随模板分辨率派生,混合尺寸模板库禁用「比例」参数
_TM_TARGET_PX = 100           # 256 正源模板的目标像素(卡面渲染实测 ~100px,2px 步进扫描峰值)
_TM_TARGET_PX_SELECTED = 106  # 选中卡(白框)渲染放大 ~6% → 106px(尺度扫描峰值)

# 叠影模板目录(TemplateLoader 规范二级结构):<叠影数>/raw.webp = 归一 26×26
# 紧圆窗灰度裁片(圆心 ±13)。rank = 目录名数字,每档一个模板。底色与明暗差异(半透明圆透出的卡底
# 色差、1 星白底卡的亮底暗字反相)均被归一化相关系数 + 滑动匹配吸收,
# 实测白底 III 卡对暗底模板 0.669、暗紫底 I 卡对金褐底模板 0.999——
# 曾按底色/明暗分过多套模板,逐套实测均为冗余,已并。五档齐(1-5)。底色差异(半透明圆透出卡底)由 TM_CCOEFF_NORMED 的
# 去均值除方差 + 探针滑动匹配吸收,无需按底色分模板(暗紫底卡对金褐底
# 模板实测 0.99)。
_SUPERIMPOSE_SUB_DIR = 'light_cone_superimpose'

# 角标头像模板的资产布局:avatarminiicon 平铺 png 目录(裸路径读盘,不走
# TemplateLoader,透明圆外由读盘侧取 RGB 丢弃)
_MINI_DIR_REL = 'assets/template/character_avatar_mini'
# 角标 SIFT 特征上采样倍率:两尺度互补(部分角色仅在其一尺度上出足特征);
# 匹配侧 zone 特征提取与构建侧同参(单一源,识别器 import 使用)
_UPSAMPLE_SCALES: tuple[int, ...] = (2, 3)
_SIFT = cv2.SIFT_create(nfeatures=400)


@dataclass
class LightConeTemplate:
    """单个光锥卡面模板条目。

    Attributes:
        template_id: 模板目录名(== LightConeDef.id,TemplateLoader 的 template_id)。
        light_cone: 模板对应的光锥定义。
        info: 模板信息(raw 与 SIFT 特征惰性加载)。
    """

    template_id: str
    light_cone: LightConeDef
    info: TemplateInfo


def _fg_mask_from_rgb(rgb: np.ndarray) -> np.ndarray:
    """归档 webp 的前景 mask:四角中位取合成底色,色距 >30 为前景。

    归档模板无 alpha(透明区已按稀有度合成卡框底色),底色平坦不产生匹配
    信号;TM 逐像素比对必须剔除底色,否则底色互相关稀释前景分数。
    """
    corners = np.stack([rgb[:4, :4].reshape(-1, 3), rgb[:4, -4:].reshape(-1, 3),
                        rgb[-4:, :4].reshape(-1, 3), rgb[-4:, -4:].reshape(-1, 3)])
    bg = np.median(corners.reshape(-1, 3), axis=0)
    return np.linalg.norm(rgb.astype(np.float64) - bg[None, None, :], axis=2) > 30


class LightConeTplStore:
    """光锥域识别模板的派生视图容器(六视图,懒构建,构建后只读)。

    视图与数据源:
    - card_faces: 卡面库读盘 + 命名校验(单一入口);
    - tm_prep_tpls: card_faces 派生(masked TM 模板,raw 缩放双档 + 前景 mask);
    - superimpose_tpls: 叠影圆标模板(TemplateLoader 盘上归一裁片,仅转灰度);
    - icon_tpls / icon_feats / icon_hists: 角标头像模板裸路径读盘及其
      SIFT 特征 / HSV 直方图派生。
    """

    def __init__(self, template_loader: TemplateLoader):
        """只注入 loader,不持 ctx:视图内容与 ctx 实例无关,契约测试可零 ctx 自建。"""
        self.template_loader: TemplateLoader = template_loader

    @cached_property
    def card_faces(self) -> list[LightConeTemplate]:
        """卡面库全量模板遍历(懒构建,构建后只读)。

        目录名必须命中某把光锥的 id(空 id 光锥不入库),违者 raise;
        模板缺失(raw 读不到)视为资产错误 raise,与命名校验同一口径。
        """
        by_id = {c.id: c for c in LIGHT_CONES if c.id}
        root = os_utils.get_path_under_work_dir('assets', 'template', LIGHT_CONE_TEMPLATE_SUB_DIR)
        entries: list[LightConeTemplate] = []
        for dir_name in sorted(os.listdir(root)):
            full = os.path.join(root, dir_name)
            if not os.path.isdir(full):
                continue
            cone = by_id.get(dir_name)
            if cone is None:
                raise ValueError(
                    f'光锥卡面库存在不合命名约定的目录: {dir_name}(应为 LightConeDef.id)')
            info = self.template_loader.get_template(LIGHT_CONE_TEMPLATE_SUB_DIR, dir_name)
            if info is None or info.raw is None:
                raise ValueError(f'光锥卡面模板缺失原图: {dir_name}')
            entries.append(LightConeTemplate(dir_name, cone, info))
        return entries

    @cached_property
    def tm_prep_tpls(self) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
        """光锥名 → [(RGB 模板, 前景 mask), ...] 按档位,已缩放到目标像素。

        模板经卡面库单一入口 card_faces 取。缩放按模板原始尺寸归一:256
        正源 → 主档 100px / 选中档 106px——卡面渲染像素才是常量,比例随
        模板分辨率派生;双档覆盖列表常态与选中卡(白框)的放大渲染。
        """
        prep: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {}
        for entry in self.card_faces:
            img = entry.info.raw
            mask = _fg_mask_from_rgb(img)
            # 双档:主档(未选中卡渲染) + 选中档(选中卡白框放大 ~6%)。
            # 相似件分数接近时,选中卡的放大差足以让次优件反超(遗器侧行内
            # 死水头被透镜反超实证),双档级联为必需而非可选。
            entries = []
            for target in (_TM_TARGET_PX, _TM_TARGET_PX_SELECTED):
                tpl = cv2.resize(img, (target, target), interpolation=cv2.INTER_AREA).astype(np.float32)
                mask_s = (cv2.resize(mask.astype(np.uint8), (target, target),
                                     interpolation=cv2.INTER_NEAREST) * 255).astype(np.uint8)
                entries.append((tpl, mask_s))
            prep[entry.light_cone.name] = entries
        return prep

    @cached_property
    def superimpose_tpls(self) -> dict[str, np.ndarray]:
        """模板 id → 归一灰度圆盘(盘上已是 26×26 紧圆裁片,仅 RGB→灰度,无缩放)。"""
        lib: dict[str, np.ndarray] = {}
        for info in self.template_loader.get_all_template_info_from_disk():
            if info.sub_dir != _SUPERIMPOSE_SUB_DIR:
                continue
            raw = info.raw
            if raw is None:
                continue
            gray = cv2.cvtColor(raw, cv2.COLOR_RGB2GRAY) if raw.ndim == 3 else raw
            lib[info.template_id] = gray
        return lib

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
