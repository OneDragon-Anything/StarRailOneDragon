# -*- coding: utf-8 -*-
"""锚点对应点定标 (人工半自动): 可见锚点图标屏幕位 + 官方坐标, 遍历分配求自洽相似变换。
用法: uv run calib_by_anchors.py <map_id> <截图> <输出目录> <sw1x,sw1y> <sw2x,sw2y> [sw3x,sw3y ...]
"""
import io
import json
import os
import sys

import numpy as np
import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
PROBE = os.path.join(REPO, '.debug', 'temp', 'animestudio', 'mys_probe')
MAP_ID = int(sys.argv[1])
SHOT = sys.argv[2]
OUT = os.path.join(PROBE, sys.argv[3])
os.makedirs(OUT, exist_ok=True)
swirls = [tuple(float(v) for v in a.split(',')) for a in sys.argv[4:]]

info = json.load(io.open(os.path.join(PROBE, f'map_info_{MAP_ID}.json'), encoding='utf-8'))
detail = json.loads(info['data']['info']['detail'])
origin = detail['origin']
pts = json.load(io.open(os.path.join(PROBE, f'map_point_{MAP_ID}.json'), encoding='utf-8'))
labels = {lb['id']: lb['name'] for lb in pts['data']['label_list']}
anchors = [(p['x_pos'], p['y_pos']) for p in pts['data']['point_list'] if '锚' in labels.get(p['label_id'], '')]
print(f'官方锚点 {len(anchors)}: {anchors}')
print(f'可见锚点图标 {len(swirls)}: {swirls}')

import itertools
import requests
from PIL import Image

best = None
# 官方坐标 -> 切片像素
for perm in itertools.permutations(range(len(anchors)), len(swirls)):
    # 前 2 个对应点求相似变换 (point+origin 系)
    (p0, s0), (p1, s1) = [(np.array(anchors[perm[i]]) + np.array(origin), np.array(swirls[i], dtype=np.float64)) for i in (0, 1)]
    v1 = s1 - s0
    v0 = p1 - p0
    scale = float(np.hypot(*v1) / np.hypot(*v0))
    if not 0.2 < scale < 5:
        continue
    ang = np.arctan2(v1[1], v1[0]) - np.arctan2(v0[1], v0[0])
    if abs(np.degrees(ang)) > 2:
        continue
    c, si = np.cos(ang), np.sin(ang)
    R = np.array([[c, -si], [si, c]])
    t = s0 - scale * R @ p0
    # 验证: 其余可见锚点
    errs = []
    for i in range(2, len(swirls)):
        p = np.array(anchors[perm[i]]) + np.array(origin)
        pred = scale * R @ p + t
        errs.append(float(np.hypot(*(pred - np.array(swirls[i])))))
    score = max(errs) if errs else 0.0
    if best is None or score < best[0]:
        best = (score, scale, np.degrees(ang), t, perm, errs)

if best is None:
    print('无自洽分配')
    sys.exit(1)
score, scale, rot, t, perm, errs = best
print(f'最优分配: 官方{list(perm)} -> 屏幕{swirls[:len(swirls)]} 校验残差={errs} max={score:.1f}px')
print(f'scale={scale:.5f} rot={rot:.3f}deg t=({t[0]:.1f},{t[1]:.1f})')

# 生成 raw (同 gen_map 约定: 画布 = (切片 - t)/scale + off)
import requests
arr = np.array(Image.open(io.BytesIO(requests.get(detail['slices'][0][0]['url'], timeout=120).content)).convert('RGBA'))
base_bgr = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
base_alpha = arr[:, :, 3]
bh, bw = base_bgr.shape[:2]
corners = np.array([[0, 0], [bw, 0], [0, bh], [bw, bh]], dtype=np.float64)
gc = (corners - t) / scale
min_xy, max_xy = gc.min(axis=0), gc.max(axis=0)
off_x, off_y = 20 - min_xy[0], 20 - min_xy[1]
cw, ch = int(max_xy[0] - min_xy[0]) + 40, int(max_xy[1] - min_xy[1]) + 40
M = np.array([[1 / scale, 0, -t[0] / scale + off_x], [0, 1 / scale, -t[1] / scale + off_y]], dtype=np.float64)
rng = np.random.default_rng(20260912)
alpha_w = cv2.warpAffine((base_alpha > 10).astype(np.uint8) * 255, M, (cw, ch), borderValue=0)
content = cv2.warpAffine(base_bgr, M, (cw, ch), borderValue=0)
raw = rng.integers(201, 210, (ch, cw, 3), dtype=np.uint8)
raw[alpha_w > 10] = content[alpha_w > 10]
mask_src = (base_alpha > 10).astype(np.uint8) * 255
mask = cv2.warpAffine(mask_src, M, (cw, ch), borderValue=0)
n, lbl, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=4)
for lb in range(1, n):
    if stats[lb, cv2.CC_STAT_AREA] < 500:
        mask[lbl == lb] = 0
sp_rows = []
for i, (bx, by) in enumerate(sorted(anchors), 1):
    gx = (bx + origin[0] - t[0]) / scale + off_x
    gy = (by + origin[1] - t[1]) / scale + off_y
    sp_rows.append({'num': i, 'official': [bx, by], 'lm_pos': [round(gx, 1), round(gy, 1)]})
    print(f'锚{i}: lm_pos=({gx:.0f},{gy:.0f})')
cv2.imwrite(os.path.join(OUT, 'raw.png'), raw)
cv2.imwrite(os.path.join(OUT, 'mask.png'), mask)
with open(os.path.join(OUT, 'calib.json'), 'w', encoding='utf-8') as fp:
    json.dump({'map_id': MAP_ID, 'origin': origin, 'scale': scale, 't': [float(t[0]), float(t[1])],
               'off': [float(off_x), float(off_y)], 'canvas': [cw, ch],
               'inliers': len(swirls), 'rot_deg': rot, 'shot': os.path.basename(SHOT),
               'calib_method': 'anchor_correspondence', 'sp': sp_rows}, fp, ensure_ascii=False, indent=1)
print(f'产物: {OUT}')

