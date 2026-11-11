"""生成行迹升级材料数量表(BWIKI 角色页「技能晋阶材料」→ src/sr_od/config 常量)。

数据源:BWIKI 角色页的「技能晋阶材料」节(如 https://wiki.biligame.com/sr/藿藿)。
该表为全 5 星角色统一固定表(游戏机制:行迹升级消耗不因角色而异),拉取
任意一名 5 星角色页即可取全;4 星角色表未核对,不覆盖。

可信度凭据(三重交叉验证):BWIKI 表各段累计与游戏内
晋阶界面实读完全一致——终结技 1→8 累计信用点 192500 / 永恒之花 8 /
永寿荣枝 7 / 无穷假身的遗恨 1,四项全中。

版本更新后重跑刷新(数据块禁手改)。EdgeOne 反爬下重拉需浏览器级请求,
可先手工缓存页面 HTML 到 CACHE_HTML 再跑。
"""
import json
import re
import urllib.request
from pathlib import Path

CACHE_HTML = '.debug/temp/bwiki_char_huohuo.html'
PAGE_URL = 'https://wiki.biligame.com/sr/%E8%97%BF%E8%97%BF'
OUT_PATH = 'src/sr_od/config/trace_levelup_const.py'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0'

# 主表(战技/终结技/天赋共用,等级 1→10 共 9 段);普攻/秘技段数不同,
# BWIKI 表的第二张未含材料行,不覆盖——以游戏内界面实读为准
_MAIN_TABLE_MIN_ROWS = 3


def load_html() -> str:
    p = Path(CACHE_HTML)
    if p.exists():
        return p.read_text(encoding='utf-8')
    req = urllib.request.Request(PAGE_URL, headers={'User-Agent': UA})
    html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
    p.write_text(html, encoding='utf-8')
    return html


def parse_main_table(html: str) -> dict[str, dict[str, int]]:
    """解析「技能晋阶材料」节主表 → {段名: {材料名: 数量}}。"""
    anchors = [m.start() for m in re.finditer(r'id="技能晋阶材料"', html)]
    if not anchors:
        raise RuntimeError('角色页无「技能晋阶材料」节(页面结构变更?)')
    seg = html[anchors[-1]: anchors[-1] + 30000]
    tables = re.findall(r'<table.*?</table>', seg, re.S)
    if not tables:
        raise RuntimeError('节内无表格')

    def cell_parts(cell: str) -> list[tuple[str, int | None]]:
        parts = re.split(r'(<img[^>]*>)', cell)
        out: list[tuple[str, int | None]] = []
        pending = None
        for p in parts:
            if p.startswith('<img'):
                m = re.search(r'alt="([^"]+)"', p)
                pending = m.group(1).strip() if m else None
                continue
            text = re.sub(r'<[^>]+>', ' ', p)
            text = re.sub(r'\s+', ' ', text).strip()
            if pending:
                m = re.search(r'(\d[\d,]*)', text)
                out.append((pending, int(m.group(1).replace(',', '')) if m else None))
                pending = None
            elif text:
                out.append((text, None))
        return out

    main = tables[0]
    rows = re.findall(r'<tr.*?</tr>', main, re.S)
    if len(rows) < _MAIN_TABLE_MIN_ROWS:
        raise RuntimeError(f'主表仅 {len(rows)} 行,结构变更')
    grid = [[cell_parts(c) for c in re.findall(r'<t[dh].*?>(.*?)</t[dh]>', r, re.S)]
            for r in rows]
    seg_names = [parts[0][0] for parts in grid[0] if parts]
    costs: dict[str, dict[str, int]] = {}
    for col, seg_name in enumerate(seg_names):
        mats: dict[str, int] = {}
        for row in grid[2:]:
            if col >= len(row):
                continue
            for name, amount in row[col]:
                if name and amount is not None:
                    mats[name] = amount
        if mats:
            costs[seg_name] = mats
    return costs


def write_const(costs: dict[str, dict[str, int]]) -> None:
    head = '''"""行迹升级材料数量表(5 星角色统一固定表,分段口径)。

本文件由 skills/sr-od-dev-character-data/scripts/generate_trace_cost_const.py 从 BWIKI 角色页
「技能晋阶材料」节生成,**禁手改**(数据修正走重新生成)。
- 段名「A→B」= 技能等级 A 升到 B;解锁条件 = 角色晋阶段数(「1→2」需
  角色晋阶 1,以此类推)——行迹升级 op 的「可提升至N级」即受此约束。
- 全 5 星角色统一(游戏机制);4 星角色表未核对不覆盖。
- 普攻(上限更低)与秘技(1 级)段数不同,BWIKI 第二张表无材料行不覆盖,
  以游戏内界面实读为准。
- 可信度凭据:与游戏内晋阶界面三重交叉验证吻合(终结技 1→8 累计
  信用点 192500 / 永恒之花 8 / 永寿荣枝 7 / 无穷假身的遗恨 1)。
"""
'''
    body = json.dumps(costs, ensure_ascii=False, indent=1)
    tail = '''

def total_cost(from_level: int, to_level: int) -> dict[str, int]:
    """技能从 from_level 升到 to_level 的材料合计(半开区间,不含 from_level
    所在行,含 to_level 行;如 total_cost(1, 8) = 1→2 至 7→8 各段之和)。"""
    result: dict[str, int] = {}
    for seg_name, mats in _TRACE_LEVELUP_COSTS.items():
        a = int(seg_name.split('→')[0])
        if from_level < a + 1 <= to_level:
            for name, amount in mats.items():
                result[name] = result.get(name, 0) + amount
    return result
'''
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(head)
        f.write('\n_TRACE_LEVELUP_COSTS: dict[str, dict[str, int]] = ')
        f.write(body)
        f.write('\n')
        f.write(tail)
    print(f'已生成 {OUT_PATH} ({len(costs)} 段)')


def main() -> None:
    html = load_html()
    costs = parse_main_table(html)
    # 固化前交叉验证:1→8 累计信用点必须=192500(实机锚点)
    acc: dict[str, int] = {}
    for seg in ['1→2', '2→3', '3→4', '4→5', '5→6', '6→7', '7→8']:
        for name, amount in costs.get(seg, {}).items():
            acc[name] = acc.get(name, 0) + amount
    if acc.get('信用点') != 192500 or acc.get('永恒之花') != 8:
        raise RuntimeError(f'交叉验证失败: {acc}(与实机锚点不符,页面数据可疑)')
    write_const(costs)


if __name__ == '__main__':
    main()
