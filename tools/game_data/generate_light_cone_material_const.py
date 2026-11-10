"""生成光锥晋阶材料使用表(BWIKI 一览页快照 → src/sr_od/config 常量文件)。

数据源:BWIKI「光锥晋阶材料一览」页(https://wiki.biligame.com/sr/光锥晋阶材料一览),
表格为「材料 → 使用该材料的光锥清单」反查形态(命途材料表 + 敌方掉落材料表)。
输入 = 本地缓存的页面 HTML(.debug/temp/,EdgeOne 反爬下重拉需浏览器级请求)。

版本更新后重跑刷新(数据块禁手改)。
"""
import json
import re
from pathlib import Path

CACHE_HTML = '.debug/temp/bwiki_lc_materials.html'
OUT_PATH = 'src/sr_od/config/light_cone_material_const.py'


def parse_reverse_table(html: str) -> dict[str, list[str]]:
    """解析一览页的全部表格 → {材料名: [光锥名(去重保序)]}。"""
    usage: dict[str, list[str]] = {}
    tables = re.findall(r'<table.*?</table>', html, re.S)
    for table in tables:
        for row in re.findall(r'<tr.*?</tr>', table, re.S):
            cells = re.findall(r'<t[dh].*?>(.*?)</t[dh]>', row, re.S)
            if len(cells) < 2:
                continue
            material_names = re.findall(r'title="([^"]+)"', cells[0])
            if not material_names:
                continue  # 表头行
            material = material_names[0].strip()
            cones: list[str] = []
            for title in re.findall(r'title="([^"]+)"', cells[1]):
                name = title.strip()
                if name and name != material and name not in cones:
                    cones.append(name)
            if cones:
                usage[material] = cones
    return usage


_HEAD = '''"""光锥晋阶材料使用表:材料名 → 使用该材料的光锥清单(BWIKI 快照)。

本文件由 tools/game_data/generate_light_cone_material_const.py 从 BWIKI
「光锥晋阶材料一览」页生成,**禁手改**(数据修正走重新生成)。
查询方向:给光锥找晋阶材料用 get_materials_for_light_cone;给材料找
适用光锥用 get_light_cones_for_material。光锥晋阶材料数量为全光锥统一
的固定表(游戏机制),不在本表——数量以游戏内晋阶界面实读为准。
"""
'''

_TAIL = '''

def get_light_cones_for_material(material_name: str) -> list[str]:
    """材料名 → 使用该材料晋阶的光锥名清单;表外材料返回空列表。"""
    return _LIGHT_CONE_MATERIAL_DATA.get(material_name, [])


def get_materials_for_light_cone(cone_name: str) -> list[str]:
    """光锥名 → 该光锥晋阶需要的特殊材料清单(经验书/信用点之外的专属类);
    表外光锥返回空列表。"""
    return [material for material, cones in _LIGHT_CONE_MATERIAL_DATA.items()
            if cone_name in cones]
'''


def main() -> None:
    html = Path(CACHE_HTML).read_text(encoding='utf-8')
    usage = parse_reverse_table(html)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(_HEAD)
        f.write('\n_LIGHT_CONE_MATERIAL_DATA: dict[str, list[str]] = ')
        f.write(json.dumps(usage, ensure_ascii=False, indent=1))
        f.write('\n')
        f.write(_TAIL)
    print(f'已生成 {OUT_PATH} ({len(usage)} 种材料)')


if __name__ == '__main__':
    main()
