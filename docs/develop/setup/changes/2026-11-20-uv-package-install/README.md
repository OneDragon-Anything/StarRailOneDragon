# 2026-11-20 uv 包安装化（消灭 PYTHONPATH 依赖）

## 文档

- 设计总纲:[design.md](design.md)
- 落地:[landing.md](landing.md)

## 进度

- 迭代设计:定稿（四轮对抗收敛，用户端丙案经用户裁定；全程记录见 [attack.md](attack.md)）
- 设计对抗:收敛 · 报告=[attack.md](attack.md)（分核:[attack-core1.md](attack-core1.md)/[attack-core2.md](attack-core2.md)/[attack-core3.md](attack-core3.md)/[attack-round2-closure.md](attack-round2-closure.md)/[attack-round2-nopremise.md](attack-round2-nopremise.md)/[attack-round3.md](attack-round3.md)/[attack-round4.md](attack-round4.md)）
- 落地:阶段 3/3 done（3.1 核心构建与冒烟 / 3.2 打包冒烟与脚本清理 / 3.3 CI 环境包与探针，阶段划分见 landing.md）
- 正本更新:清零（③ 层清单 grep 收口达判据：残留仅剩警示类内容与 daemon/GUI 保留注入点引用；ZZZ 同步件与 skill 反馈件已产出 `.debug/temp/`）
