// 角色层组件 —— 绝对定位 + 进入/退出动画 + 投影

import React, {useState} from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {ENTER_ANIM_DURATION, EXIT_ANIM_DURATION} from '../lib/constants';
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
  left: '6%',
  right: '46%',
  center: '50%',
};

/**
 * 角色层：
 * - 绝对定位，避免 flex margin 偏移不可控
 * - 从指定方向滑入/滑出
 * - 轻微上下漂浮（可选）
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

  // 进入动画
  const enterProgress = interpolate(
    frame,
    [startFrame, startFrame + fps * ENTER_ANIM_DURATION],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // 退出动画
  const exitProgress = interpolate(
    frame,
    [endFrame - fps * EXIT_ANIM_DURATION, endFrame],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const inScene = frame >= startFrame && frame <= endFrame;

  // 入场位移（基于绝对定位位置）
  const enterShiftX = enterFrom === 'left' ? -300 * (1 - enterProgress) : enterFrom === 'right' ? 300 * (1 - enterProgress) : 0;
  const enterShiftY = enterFrom === 'bottom' ? 300 * (1 - enterProgress) : enterFrom === 'top' ? -300 * (1 - enterProgress) : 0;

  const floatOffset = floating ? Math.sin(progress * Math.PI * 2) * 10 : 0;

  const isCenter = position === 'center';
  const centerTransform = isCenter ? 'translateX(-50%)' : '';

  const opacity = inScene ? exitProgress : 0;

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
          bottom: 420,
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
