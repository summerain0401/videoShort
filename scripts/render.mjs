#!/usr/bin/env node
/**
 * render.js — Node 端渲染脚本
 * 读取单条视频项目的数据文件（timeline.json + material-library.json），
 * 解析所有素材路径后，用 Remotion 程序化 API 渲染成片。

 * 用法:
 *   node scripts/render.mjs <project_dir> [--out out.mp4] [--still 帧号]
 *
 * 说明:
 *   --still 渲染单帧（用于快速审稿/融合预览），否则渲染完整视频。
 */
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import fs from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

const ENTRY = path.join(ROOT, 'remotion', 'index.ts');

function parseArgs(argv) {
  const args = {projectDir: argv[2], out: null, still: null};
  for (let i = 3; i < argv.length; i++) {
    if (argv[i] === '--out') args.out = argv[i + 1];
    if (argv[i] === '--still') args.still = parseInt(argv[i + 1], 10);
  }
  return args;
}

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf-8'));
}

/** 从素材库按名称+类型+情绪找 active 素材，返回相对 public/ 的路径（带前导 /） */
function findActiveMaterial(lib, type, name, emotion) {
  const category =
    type === 'background'
      ? 'backgrounds'
      : type === 'character'
        ? 'characters'
        : 'props';
  const items = lib[category] || [];
  const matches = items.filter((i) => i.status === 'active' && i.name === name);
  if (matches.length === 0) return null;
  if (emotion) {
    const byEmotion = matches.find((i) => i.emotion === emotion);
    if (byEmotion) return `/${byEmotion.filePath}`;
  }
  return `/${matches[0].filePath}`;
}

/** 正文场景默认背景映射（scene-config 指定 background 时优先） */
function resolveBackground(lib, sceneId, sceneBackgroundName) {
  if (sceneBackgroundName) {
    const found = findActiveMaterial(lib, 'background', sceneBackgroundName);
    if (found) return found;
  }
  const num = parseInt(sceneId.replace(/\D/g, ''), 10) || 1;
  // 默认：S01 小镇街道引入，S02 起进入超市内部
  const bgName = num <= 1 ? '小镇街道' : '超市内部';
  return (
    findActiveMaterial(lib, 'background', bgName) ||
    findActiveMaterial(lib, 'background', '超市内部') ||
    findActiveMaterial(lib, 'background', '小镇街道')
  );
}

/** 把 timeline 里的场景和元素都填上素材路径 */
function resolveTimelineMaterials(timeline, lib) {
  timeline.scenes.forEach((scene) => {
    if (!scene.backgroundPath) {
      scene.backgroundPath = resolveBackground(lib, scene.sceneId, scene.backgroundName);
    }
    scene.elements.forEach((el) => {
      if (!el.imagePath) {
        el.imagePath = findActiveMaterial(lib, el.type, el.name, el.emotion);
      }
    });
  });
  return timeline;
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.projectDir) {
    console.error('用法: node scripts/render.mjs <project_dir> [--out out.mp4] [--still N]');
    process.exit(1);
  }
  const projectDir = path.resolve(ROOT, args.projectDir);
  const timelinePath = path.join(projectDir, 'data', 'timeline.json');
  if (!fs.existsSync(timelinePath)) {
    console.error(`[error] 缺少 ${timelinePath}，请先运行 build-timeline.py`);
    process.exit(1);
  }

  // 1. 读取数据
  const timeline = readJson(timelinePath);
  const libPath = path.join(ROOT, 'shared', 'material-library.json');
  const library = fs.existsSync(libPath)
    ? readJson(libPath)
    : {characters: [], backgrounds: [], props: []};

  // 2. 解析素材路径并内嵌到 timeline
  resolveTimelineMaterials(timeline, library);

  // 3. 复制音频到 public/_audio/（Remotion 只服务 public/）
  //    注意: audioFile 可能是绝对路径, 必须用 path.resolve 而非 path.join
  //    （path.join 会把绝对路径当普通段拼接, 拼出不存在路径导致静默无配音）
  //    优先使用混音轨 audio/mixed.mp3（BGM Ducking + 转场音效，由 mix-audio.py 生成）
  const mixedPath = path.join(projectDir, 'audio', 'mixed.mp3');
  const audioSrc = fs.existsSync(mixedPath)
    ? mixedPath
    : timeline.audioFile
      ? path.resolve(ROOT, timeline.audioFile)
      : null;
  let narration = undefined;
  if (audioSrc && fs.existsSync(audioSrc)) {
    const pubDir = path.join(ROOT, 'public', '_audio');
    fs.mkdirSync(pubDir, {recursive: true});
    const dest = path.join(pubDir, 'voice.mp3');
    fs.copyFileSync(audioSrc, dest);
    narration = '_audio/voice.mp3';
    console.log(`[render] 音频已复制: ${audioSrc} -> ${dest}`);
  } else {
    console.warn(`[render] 警告: 未找到音频文件 ${audioSrc ?? timeline.audioFile}，成片将无旁白音频`);
  }

  // 4. 读取片尾问答（可选，从项目目录 outro.json）
  let outro;
  const outroPath = path.join(projectDir, 'data', 'outro.json');
  if (fs.existsSync(outroPath)) {
    outro = readJson(outroPath);
  }

  // 4.1 片尾角色素材解析：outro.character 指定角色名，缺省兜底「小布丁」；
  //     提问阶段用 thinking，答案揭晓阶段用 smile；找不到素材则整体回退纯卡片
  if (outro) {
    const outroCharName = outro.character || '小新';
    outro.character = outroCharName;
    outro.characterImage =
      outro.characterImage ??
      findActiveMaterial(library, 'character', outroCharName, 'thinking') ??
      findActiveMaterial(library, 'character', '小新', 'thinking');
    outro.characterImageHappy =
      outro.characterImageHappy ??
      findActiveMaterial(library, 'character', outroCharName, 'smile') ??
      findActiveMaterial(library, 'character', '小新', 'smile');
  }

  const inputProps = {timeline, library, narration, outro};

  // 5. 打包 + 渲染
  console.log('[render] bundling...');
  const serveUrl = await bundle({
    entryPoint: ENTRY,
    publicDir: path.join(ROOT, 'public'),
  });
  const composition = await selectComposition({serveUrl, id: 'Main', inputProps});

  if (args.still != null) {
    const out = args.out || path.join(projectDir, 'qa', 'story-review', 'preview.png');
    fs.mkdirSync(path.dirname(out), {recursive: true});
    await renderStill({
      composition,
      serveUrl,
      output: out,
      frame: args.still,
      inputProps,
      imageFormat: 'png',
    });
    console.log(`[ok] 静态帧: ${out} (frame ${args.still})`);
    return;
  }

  const out = args.out || path.join(projectDir, 'deliverables', `${timeline.videoId}_成片.mp4`);
  fs.mkdirSync(path.dirname(out), {recursive: true});
  console.log(`[render] rendering ${composition.durationInFrames} frames...`);
  await renderMedia({
    composition,
    serveUrl,
    codec: 'h264',
    outputLocation: out,
    inputProps,
    overwrite: true,
  });
  console.log(`[ok] 成片: ${out}`);
}

main().catch((err) => {
  console.error('[render] 失败:', err);
  process.exit(1);
});
