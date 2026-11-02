# videoShort · Pudding Economics

[中文](README.md) | [English](README.en.md)

A vertical-video workflow for everyday economics using the original 小布丁 (Little Pudding) character and shared assets. Python handles scripts, speech, timelines, assets, and checks; React / Remotion handles visuals and composition. See the [brand guide](ACCOUNT_BRAND.md).

## Current capabilities

The repository contains scripts, scene configurations, timelines, covers, and shared characters / backgrounds / props. The target is 1080×1920 at 30 fps; narration and timeline determine duration. SpongeBob examples in design-source documents are not the current protagonist or a verified delivered feature.

Human script and material approval in each project's `qa/review.json` is required before production. The checker does not approve anything automatically. Historical projects in a clean clone may lack review records and audio, so full reconstruction is not guaranteed.

## Setup

Requires Node.js / npm, a Remotion-compatible browser, Python 3.10+, and FFmpeg / ffprobe. Basic Python dependencies can be installed in an isolated environment:

```bash
npm ci
python3 -m venv .venv
source .venv/bin/activate
pip install edge-tts Pillow
bash scripts/pipeline.sh help
bash scripts/pipeline.sh list
```

There is no complete locked Python manifest. Azure speech additionally needs `azure-cognitiveservices-speech` and [environment configuration](.env.example). Semantic asset search additionally needs PyTorch, Transformers, FAISS, and NumPy and downloads a model on first use. These optional capabilities are not included in the basic setup above.

## Production entry

Run from the repository root with your own new project ID:

```bash
bash scripts/pipeline.sh new "Everyday economics topic" C100_新选题
# Edit the script, prepare assets, and complete qa/review.json manually:
bash scripts/pipeline.sh voice 02_项目/C100_新选题 edge
bash scripts/pipeline.sh timeline 02_项目/C100_新选题
bash scripts/pipeline.sh render 02_项目/C100_新选题
bash scripts/pipeline.sh check 02_项目/C100_新选题
```

Speech requires network access and may incur service costs. `new` uses template mode and creates a draft, not researched or approved factual content. Without the explicit `edge` argument, speech selection may use configured Azure credentials.

## Inputs and outputs

- `02_项目/`: per-episode `script/`, `data/`, `audio/`, `qa/`, and `deliverables/`.
- `shared/`: assets, index, and avatars; see the [shared-asset guide](shared/README.md). Preserve the relative `public/shared` symlink when moving the project.
- `scripts/`: production/checking entry points; `remotion/`: video components.
- `batch-plans/`: batch topics; `tests/` currently contains no actual test cases.

Technical and semantic checks do not replace human review. This documentation update checked safe entry points only; no speech, paid call, or complete render was performed.

## License
The default branch does not include a project-level license file. Public visibility does not itself grant reuse rights. Third-party dependencies and assets retain their own terms.
