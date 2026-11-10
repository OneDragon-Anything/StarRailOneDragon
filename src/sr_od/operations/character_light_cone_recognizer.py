"""「角色-光锥」TAB 页的画面额外识别器(backend analyze 精准命中后自动调用)。

读取右栏当前装备光锥的结构化信息(名/命途/等级/叠影阶/技能名/三围),
供 MCP ``analyze_screen`` 的 ``extras`` 输出——agent 查看角色当前光锥不用
再靠视觉目检截图。

读区全部来自 screen_info 建档(character_light_cone.yml),坐标单一真相源。
OCR 失败的字段返回 None(extras 稀疏,不猜测)。
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.config.character_const import CHARACTER_PATH_LIST

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext

# 「等级80/80」→ 前段数字 = 当前等级
_LEVEL_RE = re.compile(r'等级\s*(\d{1,3})')
# 「叠影1阶」→ 叠影数
_RANK_RE = re.compile(r'叠影\s*(\d)\s*阶')


class CharacterLightConeRecognizer(ScreenRecognizer):

    screen_name = '角色-光锥'

    extras_doc: dict[str, str] = {
        'cone_name': '当前装备光锥名(OCR,识别失败为 null)',
        'path_cn': '光锥命途(OCR)',
        'level': '光锥当前等级(「等级80/80」前段数字,1-80)',
        'rank': '叠影数(「叠影N阶」,1-5)',
        'skill_name': '光锥技能名(OCR)',
        'hp': '生命值白值(OCR 数字)',
        'atk': '攻击力白值(OCR 数字)',
        'def': '防御力白值(OCR 数字)',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,
    ) -> dict | None:
        """全图 OCR 一遍 → 按读区矩形过滤 → 结构化输出。

        不用 crop OCR(rect 裁剪识别不稳,实测叠影/技能名读区裁剪后 miss)。
        过滤 = 行中心落在读区 rect **外扩 15px** 内:全图 OCR 与建档 rect 存
        在 0-12px 小偏差(实测叠影行中心 y=568 vs rect 上缘 570),中心精确
        在内会 miss;外扩量经核验不致跨区误吸(相邻区块间隔 >25px)。命途
        读区含图标装饰,OCR 带杂字 → 用命途白名单清洗取命中项。"""
        all_rows = ctx.ocr_service.get_ocr_result_list(image=image, crop_first=False)
        result: dict = {}

        def read(area_name: str) -> str | None:
            area = ctx.screen_loader.get_area('角色-光锥', area_name)
            rect = area.rect
            texts = [str(r.data).strip() for r in all_rows
                     if rect.x1 - 15 <= r.x + r.w / 2 <= rect.x2 + 15
                     and rect.y1 - 15 <= r.y + r.h / 2 <= rect.y2 + 15
                     and str(r.data).strip()]
            return ''.join(texts) if texts else None

        cone_name = read('读区-光锥名')
        if cone_name is not None:
            result['cone_name'] = cone_name

        path_text = read('读区-命途')
        if path_text is not None:
            hit = [p.cn for p in CHARACTER_PATH_LIST if p.cn in path_text]
            if hit:
                result['path_cn'] = hit[0]

        level_text = read('读区-等级')
        if level_text is not None:
            m = _LEVEL_RE.search(level_text)
            if m is not None:
                result['level'] = int(m.group(1))

        rank_text = read('读区-叠影')
        if rank_text is not None:
            m = _RANK_RE.search(rank_text)
            if m is not None:
                result['rank'] = int(m.group(1))

        skill_name = read('读区-光锥技能名')
        if skill_name is not None:
            result['skill_name'] = skill_name

        for key, area_name in (('hp', '读区-生命值'), ('atk', '读区-攻击力'),
                               ('def', '读区-防御力')):
            num = read(area_name)
            if num is not None:
                digits = re.sub(r'[^\d]', '', num)
                if digits:
                    result[key] = int(digits)
        return result or None
