// 动画原语库 —— 消除线性插值的"PPT 感"
// 全部基于 Remotion 内置 API（spring / Easing / interpolate），无第三方依赖。

import {Easing, interpolate, spring} from 'remotion';

/** 常用缓动曲线 */
export const EASE = {
  /** 入场缓出（元素进入画面） */
  out: Easing.out(Easing.cubic),
  /** 对称缓动（持续运动/循环） */
  inOut: Easing.inOut(Easing.cubic),
  /** 弹性回弹（卡片/标题强调） */
  back: Easing.out(Easing.back(1.6)),
} as const;

/**
 * 物理弹性入场（spring）：返回 0→1 的进度，带自然回弹。
 * 用于角色/道具/卡片入场，替代线性 interpolate。
 * Remotion 4 的 spring 使用 durationRestThreshold（剩余幅度阈值）控制截断。
 */
export function springIn(
  frame: number,
  startFrame: number,
  opts: {fps: number; durationRestThreshold?: number} = {fps: 30},
): number {
  const {fps, durationRestThreshold = 0.01} = opts;
  return spring({
    frame: frame - startFrame,
    fps,
    config: {damping: 14, stiffness: 120, mass: 1},
    durationRestThreshold,
  });
}

/**
 * 自然漂浮：双频正弦叠加，比单一 sin 更接近"呼吸感"。
 * progress 为 0→1 的场景进度。
 */
export function naturalFloat(
  progress: number,
  opts: {amp?: number; speed?: number; phase?: number} = {},
): number {
  const {amp = 10, speed = 2, phase = 0} = opts;
  return (
    Math.sin(progress * Math.PI * 2 * speed + phase) * amp * 0.7 +
    Math.sin(progress * Math.PI * 2 * speed * 2.7 + phase * 1.7) * amp * 0.3
  );
}

/**
 * 轻幅脉冲缩放（关键词强调/问题呼吸感）：
 * progress 为 0→1 的循环进度，返回 min~max 之间的缩放值。
 */
export function pulseScale(
  progress: number,
  opts: {min?: number; max?: number; speed?: number} = {},
): number {
  const {min = 1, max = 1.05, speed = 2} = opts;
  const wave = 0.5 - 0.5 * Math.cos(progress * Math.PI * 2 * speed);
  return min + (max - min) * wave;
}

/**
 * Ken Burns 推拉：easeInOut 缓动，避免线性运动的生硬感。
 */
export function kenBurnsScale(
  progress: number,
  opts: {from?: number; to?: number} = {},
): number {
  const {from = 1, to = 1.06} = opts;
  return interpolate(progress, [0, 1], [from, to], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE.inOut,
  });
}

/**
 * Ken Burns 平移：easeInOut 缓动。
 * range 形如 [x0, x1]，返回插值后的位移。
 */
export function kenBurnsTranslate(
  progress: number,
  range: [number, number],
): number {
  return interpolate(progress, [0, 1], range, {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE.inOut,
  });
}

/**
 * 表情/素材交叉过渡：返回 [opacityA, opacityB]（B 覆盖 A）。
 * 用于角色表情切换、图片淡入淡出替换。
 */
export function emotionCrossfade(
  frame: number,
  from: number,
  to: number,
  opts: {fps?: number; dur?: number} = {},
): [number, number] {
  const {fps = 30, dur = 0.6} = opts;
  const startFrame = Math.max(from, to - fps * dur);
  const progress = interpolate(
    frame,
    [startFrame, startFrame + fps * dur],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out},
  );
  return [1 - progress, progress];
}

/**
 * 闪烁透明度（星光/粒子）：基于 sin 波形，phase 用随机种子错开。
 * progress 为 0→1 的循环进度。
 */
export function twinkle(
  progress: number,
  opts: {phase?: number; min?: number; max?: number; speed?: number} = {},
): number {
  const {phase = 0, min = 0.15, max = 1, speed = 3} = opts;
  const wave = 0.5 - 0.5 * Math.cos((progress * Math.PI * 2 + phase) * speed);
  return min + (max - min) * wave;
}
