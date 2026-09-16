# -*- coding: utf-8 -*-
"""512 锚点对应穷举: 3 官方锚 vs 候选漩涡位, 60 种分配, rot≈0 且 s 合理者保留, 输出候选供目检。"""
import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PROBE = r'D:\code\workspace\StarRailOneDragon\.debug\temp\animestudio\mys_probe'
MAP_ID = 512
ORIGIN = (1195, 2106)
CANDS = [(885, 295), (655, 358), (828, 473), (893, 482), (890, 862)]

pts = json.load(io.open(os.path.join(PROBE, f'map_point_{MAP_ID}.json'), encoding='utf-8'))
labels = {lb['id']: lb['name'] for lb in pts['data']['label_list']}
anchors = [(p['x_pos'] + ORIGIN[0], p['y_pos'] + ORIGIN[1]) for p in pts['data']['point_list'] if '锚' in labels.get(p['label_id'], '')]
print(f'官方锚点 {len(anchors)}: {[(round(a[0]), round(a[1])) for a in anchors]}')

import itertools
cands = []
for combo in itertools.combinations(range(len(CANDS)), 3):
    for perm in itertools.permutations(range(len(anchors)), 3):
        pts3 = [np.array(anchors[perm[i]], dtype=np.float64) for i in range(3)]
        sw3 = [np.array(CANDS[combo[i]], dtype=np.float64) for i in range(3)]
        # 2 点拟合
        v0 = pts3[1] - pts3[0]
        v1 = sw3[1] - sw3[0]
        scale = float(np.hypot(*v1) / np.hypot(*v0))
        if not 0.3 < scale < 4:
            continue
        ang = np.arctan2(v1[1], v1[0]) - np.arctan2(v0[1], v0[0])
        if abs(np.degrees(ang)) > 0.5:
            continue
        c, si = np.cos(ang), np.sin(ang)
        R = np.array([[c, -si], [si, c]])
        t = sw3[0] - scale * R @ pts3[0]
        err = float(np.hypot(*(scale * R @ pts3[2] + t - sw3[2])))
        cands.append((err, scale, float(np.degrees(ang)), combo, perm, R, t))

cands.sort(key=lambda x: x[0])
print(f'自洽候选 {len(cands)} 个 (rot≈0 且 s 合理):')
for err, scale, ang, combo, perm, R, t in cands[:5]:
    print(f'  漩涡组={[CANDS[i] for i in combo]} 官方={list(perm)} scale={scale:.4f} rot={ang:.2f} 校验残差={err:.1f}px t=({t[0]:.0f},{t[1]:.0f})')
