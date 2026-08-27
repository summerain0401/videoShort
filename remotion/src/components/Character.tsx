// 角色层组件 —— 绝对定位 + spring 入场/退出 + 说话高亮 + 经典表情特效（冒蒸汽/大汗/抖动/灯泡）

import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {CHARACTER_BOTTOM, EXIT_ANIM_DURATION} from '../lib/constants';
import {EASE, naturalFloat, springIn} from '../lib/animations';
import {staticPath} from '../lib/staticPath';
import type {CharacterEffectType} from '../lib/types';

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
  /** 是否为发言角色 */
  isSpeaker?: boolean;
  /** 表情特效（冒蒸汽/大汗/抖动/灯泡/问号） */
  effect?: CharacterEffectType;
}

const LEFT_PCT: Record<string, string> = {
  left: '4%',
  right: '48%',
  center: '50%',
};

export const Character: React.FC<CharacterProps> = ({
  imagePath,
  enterFrom = 'none',
  duration,
  position = 'center',
  zIndex = 2,
  floating = false,
  isSpeaker = true,
  effect = 'none',
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
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  const inScene = frame >= startFrame && frame <= endFrame;

  // 入场位移
  const enterShiftX =
    enterFrom === 'left' ? -300 * (1 - enterProgress) : enterFrom === 'right' ? 300 * (1 - enterProgress) : 0;
  const enterShiftY =
    enterFrom === 'bottom' ? 300 * (1 - enterProgress) : enterFrom === 'top' ? -300 * (1 - enterProgress) : 0;

  // 说话时的微弹跳 / 漂浮
  const speakerBounce = isSpeaker ? Math.sin(frame * 0.35) * 6 : 0;
  const floatOffset = floating ? naturalFloat(progress, {amp: 8, speed: 2}) : 0;

  // 震颤/惊吓抖动特效
  const shakeX = effect === 'shake' ? (Math.sin(frame * 1.5) > 0 ? 8 : -8) : 0;

  const isCenter = position === 'center';
  const centerTransform = isCenter ? 'translateX(-50%)' : '';
  const scale = isSpeaker ? 1.05 : 0.92;

  // 入场淡入 + 退出淡出
  const opacity = inScene ? enterProgress * exitProgress * (isSpeaker ? 1.0 : 0.85) : 0;

  if (!inScene || opacity <= 0.01) {
    return null;
  }

  return (
    <AbsoluteFill style={{zIndex, pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          left: LEFT_PCT[position],
          bottom: CHARACTER_BOTTOM,
          height: '46%',
          width: position === 'center' ? 'auto' : '48%',
          transform: `${centerTransform} translate(${enterShiftX + shakeX}px, ${enterShiftY + floatOffset + speakerBounce}px) scale(${scale})`,
          transformOrigin: 'bottom center',
          opacity,
          transition: 'transform 0.15s, opacity 0.15s',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'flex-end',
        }}
      >
        {/* 表情特效挂件 */}
        {effect !== 'none' && (
          <CharacterEffectBadge effect={effect} frame={frame} fps={fps} startFrame={startFrame} />
        )}

        <Img
          src={staticPath(imagePath)}
          style={{
            maxHeight: '100%',
            maxWidth: '100%',
            objectFit: 'contain',
            filter: isSpeaker
              ? 'drop-shadow(0 16px 24px rgba(60, 30, 5, 0.4))'
              : 'drop-shadow(0 8px 12px rgba(0, 0, 0, 0.2))',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

/** 角色头顶漫画特效组件 */
const CharacterEffectBadge: React.FC<{
  effect: CharacterEffectType;
  frame: number;
  fps: number;
  startFrame: number;
}> = ({effect, frame, fps, startFrame}) => {
  const enter = springIn(frame, startFrame, {fps});
  const pulse = Math.sin(frame * 0.4) * 0.1 + 1;

  let emoji = '';
  let bgColor = '#FFF';

  if (effect === 'steam') {
    emoji = '💥';
    bgColor = '#FFCDD2';
  } else if (effect === 'sweat') {
    emoji = '💧';
    bgColor = '#E1F5FE';
  } else if (effect === 'idea') {
    emoji = '💡';
    bgColor = '#FFF9C4';
  } else if (effect === 'question') {
    emoji = '❓';
    bgColor = '#FFECB3';
  } else {
    return null;
  }

  return (
    <div
      style={{
        fontSize: 52,
        backgroundColor: bgColor,
        border: '4px solid #1E1E1E',
        borderRadius: '50%',
        width: 76,
        height: 76,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: -16,
        zIndex: 10,
        boxShadow: '0 6px 14px rgba(0,0,0,0.2)',
        transform: `scale(${enter * pulse})`,
      }}
    >
      {emoji}
    </div>
  );
};

