// 角色层组件 —— 绝对定位 + spring 入场/退出 + 双频漂浮 + 投影

import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {CHARACTER_BOTTOM, ENTER_ANIM_DURATION, EXIT_ANIM_DURATION, SAFE_AREA} from '../lib/constants';
import {naturalFloat, springIn} from '../lib/animations';
import {staticPath} from '../lib/staticPath';

interface CharacterProps {
  imagePath: string;
  enterFrom?: 'left' | 'right' | 'top' | 'bottom' | 'none';
  /** [start, end] 秒 */
  duration: [number, number];
  /** 画面中的位置: left | right | center */
  position?: 'left' | 'right' | 'center';
  zIndex?: number;
  /** 轻微漂浮动画 */
  floating?: boolean;
}

const LEFT_PCT: Record<string, string> = {
  left: '8%',
  right: '42%',
  center: '50%',
};

/**
 * 角色层：
 * - 绝对定位，避免 flex margin 偏移不可控
 * - 从指定方向 spring 弹性滑入/滑出
 * - 双频正弦自然漂浮（替代机械单频）
 * - 入场带淡入（opacity = enterProgress * exitProgress），避免"啪"地出现
 * - 透明底 PNG + 柔和投影
 */
export const Character: React.FC<CharacterProps> = ({
  imagePath,
  enterFrom = 'none',
  duration,
  position = 'center',
  zIndex = 2,
  floating = false,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const [start, end] = duration;
  const startFrame = start * fps;
  const endFrame = end * fps;

  const progress = (frame - startFrame) / (fps * (end - start || 1));

  // 进入动画：spring 弹性
  const enterProgress = springIn(frame, startFrame, {fps});

  // 退出动画：线性淡出
  const exitProgress = interpolate(
    frame,
    [endFrame - fps * EXIT_ANIM_DURATION, endFrame],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const inScene = frame >= startFrame && frame <= endFrame;

  // 入场位移（基于绝对定位位置，spring 缓动）
  const enterShiftX =
    enterFrom === 'left' ? -300 * (1 - enterProgress) : enterFrom === 'right' ? 300 * (1 - enterProgress) : 0;
  const enterShiftY =
    enterFrom === 'bottom' ? 300 * (1 - enterProgress) : enterFrom === 'top' ? -300 * (1 - enterProgress) : 0;

  // 双频自然漂浮
  const floatOffset = floating ? naturalFloat(progress, {amp: 10, speed: 2}) : 0;

  const isCenter = position === 'center';
  const centerTransform = isCenter ? 'translateX(-50%)' : '';

  // 入场淡入 + 退出淡出
  const opacity = inScene ? enterProgress * exitProgress : 0;

  if (!inScene || opacity <= 0.01) {
    return null;
  }

  return (
    <AbsoluteFill style={{zIndex, pointerEvents: 'none'}}>
      <Img
        src={staticPath(imagePath)}
        style={{
          position: 'absolute',
          left: LEFT_PCT[position],
          bottom: CHARACTER_BOTTOM,
          height: '44%',
          width: 'auto',
          objectFit: 'contain',
          transform: `${centerTransform} translate(${enterShiftX}px, ${enterShiftY + floatOffset}px)`,
          opacity,
          filter: 'drop-shadow(0 14px 20px rgba(60, 30, 5, 0.35))',
        }}
      />
    </AbsoluteFill>
  );
};
