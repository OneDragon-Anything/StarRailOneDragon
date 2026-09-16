# -*- coding: utf-8 -*-
"""仿射定标生成器 v2 (兜底级): uv run calib_affine_gen.py <map_id> <截图> <输出目录>
SIFT 对 -> estimateAffine2D (shot->base) -> 取逆 (base->游戏帧) -> raw/mask/lm_pos -> 贴回(纯平移) -> 门测。
适用: 底图艺术与实机渲染存在旋转/剪切/非等比的区域 (哀丽秘榭 448: rot≈-2°)。
"""
import io
import json
import os
import sys

import numpy as np
import cv2
import requests
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
WORK = os.path.join(REPO, '.debug', 'temp', 'animestudio')
PROBE = os.path.join(WORK, 'mys_probe')
CUT = (285, 190, 1300, 930)
VIEW = (0, 100, 1430, 1015)
UI_RECTS = [(0, 20, 230, 100), (10, 550, 130, 1020), (500, 940, 970, 1020)]

MAP_ID = int(sys.argv[1])
SHOT = sys.argv[2]
OUT = os.path.join(PROBE, sys.argv[3])
os.makedirs(OUT, exist_ok=True)

info = json.load(io.open(os.path.join(PROBE, f'map_info_{MAP_ID}.json'), encoding='utf-8'))
detail = json.loads(info['data']['info']['detail'])
origin = np.array(detail['origin'])
arr = np.array(Image.open(io.BytesIO(requests.get(detail['slices'][0][0]['url'], timeout=120).content)).convert('RGBA'))
base_bgr = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
base_alpha = arr[:, :, 3]
base_gray = cv2.cvtColor(base_bgr, cv2.COLOR_BGR2GRAY)
shot = cv2.imread(SHOT)
assert shot is not None

sift = cv2.SIFT_create(nfeatures=20000)
kp1, d1 = sift.detectAndCompute(cv2.cvtColor(shot, cv2.COLOR_BGR2GRAY), None)
kp2, d2 = sift.detectAndCompute(base_gray, None)
bf = cv2.BFMatcher()
pairs = []
for mp in bf.knnMatch(d1, d2, k=2):
    if len(mp) == 2 and mp[0].distance < 0.75 * mp[1].distance:
        pairs.append((mp[0].queryIdx, mp[0].trainIdx))
src = np.array([kp1[i].pt for i, _ in pairs], dtype=np.float64).reshape(-1, 1, 2)
dst = np.array([kp2[j].pt for _, j in pairs], dtype=np.float64).reshape(-1, 1, 2)
A, inl = cv2.estimateAffine2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=6.0, maxIters=20000, confidence=0.9999)
assert A is not None and inl is not None and int(inl.sum()) >= 10, '仿射内点不足'
n_inl = int(inl.sum())
Minv = cv2.invertAffineTransform(A)  # base -> 游戏帧(=截图系)
sx = float(np.hypot(A[0, 0], A[1, 0]))
sy = float(np.hypot(A[0, 1], A[1, 1]))
rot = float(np.degrees(np.arctan2(-Minv[0, 1], Minv[1, 1])))
si = inl.ravel().astype(bool)
src_i = src[si].reshape(-1, 2)
dst_i = dst[si].reshape(-1, 2)
pred = src_i @ A[:, :2].T + A[:, 2]
resid = float(np.hypot(*(pred - dst_i).T).mean())
print(f'仿射定标: 内点={n_inl} 活动尺s={sx:.5f}/{sy:.5f} 视图rot={rot:.3f} 残差={resid:.2f}')
assert 0.2 < sx < 5 and 0.8 < sy / sx < 1.25 and abs(rot) < 5 and resid < 3.0, '仿射护栏失败'

bh, bw = base_bgr.shape[:2]
corners = np.array([[0, 0], [bw, 0], [0, bh], [bw, bh]], dtype=np.float64)
gc = corners @ Minv[:, :2].T + Minv[:, 2]
min_xy, max_xy = gc.min(axis=0), gc.max(axis=0)
off_x, off_y = 20 - min_xy[0], 20 - min_xy[1]
cw, ch = int(max_xy[0] - min_xy[0]) + 40, int(max_xy[1] - min_xy[1]) + 40
M = Minv.copy()
M[:, 2] = Minv[:, 2] + np.array([off_x, off_y])
rng = np.random.default_rng(20260912)
alpha_w = cv2.warpAffine((base_alpha > 10).astype(np.uint8) * 255, M, (cw, ch), borderValue=0)
content = cv2.warpAffine(base_bgr, M, (cw, ch), borderValue=0)
raw = rng.integers(201, 210, (ch, cw, 3), dtype=np.uint8)
raw[alpha_w > 10] = content[alpha_w > 10]
mask = cv2.warpAffine((base_alpha > 10).astype(np.uint8) * 255, M, (cw, ch), borderValue=0)
n, lbl, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=4)
for lb in range(1, n):
    if stats[lb, cv2.CC_STAT_AREA] < 500:
        mask[lbl == lb] = 0

pts = json.load(io.open(os.path.join(PROBE, f'map_point_{MAP_ID}.json'), encoding='utf-8'))
labels = {lb['id']: lb['name'] for lb in pts['data']['label_list']}
anchors = [(p['x_pos'], p['y_pos']) for p in pts['data']['point_list'] if '锚' in labels.get(p['label_id'], '')]
sp_rows = []
for i, (bx, by) in enumerate(sorted(anchors), 1):
    sl = np.array([bx + origin[0], by + origin[1]])  # point -> 切片像素
    g = sl @ Minv[:, :2].T + Minv[:, 2] + np.array([off_x, off_y])
    sp_rows.append({'num': i, 'official': [bx, by], 'lm_pos': [round(float(g[0]), 1), round(float(g[1]), 1)]})
    print(f'锚{i}: lm_pos=({g[0]:.0f},{g[1]:.0f})')

# 贴回: 游戏帧=截图系 1:1, 画布 = 游戏 - min_xy + off (纯平移)
vx1, vy1, vx2, vy2 = VIEW
sub = shot[vy1:vy2, vx1:vx2]
ox, oy = int(vx1 + off_x), int(vy1 + off_y)
hh, ww = sub.shape[:2]
sx1, sy1 = max(0, -ox), max(0, -oy)
ox, oy = max(0, ox), max(0, oy)
ww = min(ww - sx1, cw - ox)
hh = min(hh - sy1, ch - oy)
sub = sub[sy1:sy1 + hh, sx1:sx1 + ww]
pmask = (alpha_w[oy:oy + hh, ox:ox + ww] > 10).astype(np.uint8) * 255
for (ux1, uy1, ux2, uy2) in UI_RECTS:
    if uy2 > vy1 and uy1 < vy2 and ux2 > vx1 and ux1 < vx2:
        r1, r2 = max(0, uy1 - vy1 - sy1), min(hh, uy2 - vy1 - sy1)
        c1, c2 = max(0, ux1 - vx1 - sx1), min(ww, ux2 - vx1 - sx1)
        if r2 > r1 and c2 > c1:
            pmask[r1:r2, c1:c2] = 0
pmask = cv2.GaussianBlur(pmask, (0, 0), 2)
a = (pmask.astype(np.float32) / 255.0)[..., None]
region = raw[oy:oy + hh, ox:ox + ww].astype(np.float32)
raw[oy:oy + hh, ox:ox + ww] = (sub.astype(np.float32) * a + region * (1 - a)).clip(0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(OUT, 'raw_overlaid.png'), raw)
cv2.imwrite(os.path.join(OUT, 'mask.png'), mask)
with open(os.path.join(OUT, 'calib.json'), 'w', encoding='utf-8') as fp:
    json.dump({'map_id': MAP_ID, 'origin': [int(origin[0]), int(origin[1])],
               'inv_affine': Minv.tolist(), 'min_xy': [float(min_xy[0]), float(min_xy[1])],
               'off': [float(off_x), float(off_y)], 'canvas': [cw, ch],
               'inliers': n_inl, 'rot_deg_view': rot, 'resid': resid,
               'shot': os.path.basename(SHOT), 'calib_method': 'affine', 'sp': sp_rows},
              fp, ensure_ascii=False, indent=1)

# 门测 (贴回版): CUT 裁剪 画布位 = CUT - min_xy + off (1:1)
spc = shot[CUT[1]:CUT[3], CUT[0]:CUT[2]]
ex, ey = int(CUT[0] + off_x), int(CUT[1] + off_y)
roi = raw[ey:ey + spc.shape[0], ex:ex + spc.shape[1]]
if roi.shape[0] == spc.shape[0] and roi.shape[1] == spc.shape[1]:
    res = cv2.matchTemplate(roi, spc, cv2.TM_CCOEFF_NORMED)
    res = np.nan_to_num(res, nan=0.0, posinf=0.0, neginf=0.0)
    _, mx, _, _ = cv2.minMaxLoc(res)
    print(f'贴回后 CUT门: {mx:.4f}')
else:
    print(f'门测 roi 越界 {roi.shape}')
print(f'产物: {OUT}')





