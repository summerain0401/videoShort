// 道具层组件 —— 绝对定位 + spring 进入/退出 + 投影

import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {ENTER_ANIM_DURATION, EXIT_ANIM_DURATION, SAFE_AREA} from '../lib/constants';
import {springIn} from '../lib/animations';
import {staticPath} from '../lib/staticPath';

interface PropProps {
  imagePath: string;
  enterFrom?: 'left' | 'right' | 'top' | 'bottom' | 'none';
  /** [start, end] 秒 */
  duration: [number, number];
  /** 画面中的位置: left | right | center */
  position?: 'left' | 'right' | 'center';
  zIndex?: number;
  /** 尺寸比例（相对画面高度） */
  scale?: number;
}

const PROP_LEFT_PCT: Record<string, string> = {
  left: '8%',
  right: '46%',
  center: '50%',
};

/**
 * 道具层：
 * - 绝对定位，与角色形成稳定左右构图
 * - 从指定方向 spring 弹性滑入/滑出
 * - 顶部约束在安全区内（SAFE_AREA.top + 40）
 * - 透明底 PNG + 柔和投影
 */
export const Prop: React.FC<PropProps> = ({
  imagePath,
  enterFrom = 'none',
  duration,
  position = 'right',
  zIndex = 3,
  scale = 0.36,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const [start, end] = duration;
  const startFrame = start * fps;
  const endFrame = end * fps;

  const enterProgress = springIn(frame, startFrame, {fps});

  const exitProgress = interpolate(
    frame,
    [endFrame - fps * EXIT_ANIM_DURATION, endFrame],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const inScene = frame >= startFrame && frame <= endFrame;
  const translateX = enterFrom === 'left' ? -280 * (1 - enterProgress) : enterFrom === 'right' ? 280 * (1 - enterProgress) : 0;
  const translateY = enterFrom === 'bottom' ? 240 * (1 - enterProgress) : enterFrom === 'top' ? -240 * (1 - enterProgress) : 0;

  const isCenter = position === 'center';
  const centerTransform = isCenter ? 'translateX(-50%)' : '';

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
          left: PROP_LEFT_PCT[position],
          top: SAFE_AREA.top + 40,
          height: `${scale * 100}%`,
          width: 'auto',
          objectFit: 'contain',
          transform: `${centerTransform} translate(${translateX}px, ${translateY}px)`,
          opacity,
          filter: 'drop-shadow(0 10px 16px rgba(60, 30, 5, 0.32))',
        }}
      />
    </AbsoluteFill>
  );
};
