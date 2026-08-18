#!/usr/bin/env python3
"""
generate-preview.py — 批量场景预览图（阶段 2：脚本化处理链）
为项目每个场景导出静态预览帧到 qa/story-review/，供「先审画面再做配音」使用。

时间来源：
  优先 timeline.json（配音后的真实时间）；没有则退回 scene-config.json 的 preferredStart。

用法:
    python scripts/generate-preview.py <project_dir> [--frame-per-scene 1|2] [--outdir qa/story-review]

  --frame-per-scene 1   每个场景只导起始帧（默认）
  --frame-per-scene 2   另导场景中段帧（+0.5s，看元素入场后的构图）

输出:
    <project_dir>/qa/story-review/S01_000.png  (场景起始帧)
    <project_dir>/qa/story-review/S01_mid.png  (场景中段帧，可选)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
INTRO_DURATION = 3.0  # 与 remotion/src/lib/constants.ts 保持一致


def load_times(project_dir: Path) -> list:
    """返回 [(sceneId, start_seconds)] 列表"""
    timeline_path = project_dir / "data" / "timeline.json"
    scene_path = project_dir / "data" / "scene-config.json"
    if timeline_path.exists():
        t = json.loads(timeline_path.read_text(encoding="utf-8"))
        return [(s["sceneId"], s["start"]) for s in t.get("scenes", [])]
    if scene_path.exists():
        sc = json.loads(scene_path.read_text(encoding="utf-8"))
        return [(s["sceneId"], s.get("preferredStart", 0.0)) for s in sc.get("scenes", [])]
    print("[error] 项目缺少 timeline.json 或 scene-config.json", file=sys.stderr)
    sys.exit(1)


def render_still(project_dir: Path, frame: int, out_path: Path) -> bool:
    r = subprocess.run(
        ["node", str(ROOT / "scripts" / "render.mjs"), str(project_dir),
         "--still", str(frame), "--out", str(out_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"[warn] 渲染失败 frame={frame}: {r.stderr.strip()[-200:]}")
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description="批量导出场景静态预览图")
    ap.add_argument("project_dir", help="项目目录")
    ap.add_argument("--frame-per-scene", type=int, default=1, choices=[1, 2],
                    help="每个场景导几帧（2 = 起始帧+中段帧）")
    ap.add_argument("--outdir", default="qa/story-review", help="输出子目录（相对项目目录）")
    args = ap.parse_args()

    project_dir = Path(args.project_dir)
    out_dir = project_dir / args.outdir
    out_dir.mkdir(parents=True, exist_ok=True)

    scenes = load_times(project_dir)
    if not scenes:
        print("[error] 没有可预览的场景", file=sys.stderr)
        sys.exit(1)

    ok, fail = 0, 0
    for scene_id, start in scenes:
        start_frame = int(round((INTRO_DURATION + start) * FPS))
        out1 = out_dir / f"{scene_id}_start.png"
        if render_still(project_dir, start_frame, out1):
            ok += 1
            print(f"[ok] {out1.name}  (frame {start_frame})")
        else:
            fail += 1
        if args.frame_per_scene == 2:
            mid_frame = int(round((INTRO_DURATION + start + 0.5) * FPS))
            out2 = out_dir / f"{scene_id}_mid.png"
            if render_still(project_dir, mid_frame, out2):
                ok += 1
                print(f"[ok] {out2.name}  (frame {mid_frame})")
            else:
                fail += 1

    print(f"\n[done] 预览图目录: {out_dir}")
    print(f"[info] 成功 {ok} 张, 失败 {fail} 张")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
