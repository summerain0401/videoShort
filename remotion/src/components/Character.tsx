// 角色层组件 2.1 —— 呼吸微动 (Breathing Idle) + Spring 弹性入场 + 电影感光影描边 + 动态表情特效
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
    enterFrom === 'left' ? -350 * (1 - enterProgress) : enterFrom === 'right' ? 350 * (1 - enterProgress) : 0;
  const enterShiftY =
    enterFrom === 'bottom' ? 350 * (1 - enterProgress) : enterFrom === 'top' ? -350 * (1 - enterProgress) : 0;

  // 2.1 升级：角色呼吸微动 (Breathing Animation)
  const breathY = Math.sin(frame * 0.16) * 4;
  const squashX = 1 + Math.cos(frame * 0.16) * 0.012;
  const squashY = 1 - Math.cos(frame * 0.16) * 0.012;

  // 说话时的微弹跳
  const speakerBounce = isSpeaker ? Math.sin(frame * 0.38) * 5 : 0;
  const floatOffset = floating ? naturalFloat(progress, {amp: 8, speed: 2}) : 0;

  // 震颤/惊吓抖动特效
  const shakeX = effect === 'shake' ? (Math.sin(frame * 1.6) > 0 ? 8 : -8) : 0;
  const shakeY = effect === 'shake' ? (Math.cos(frame * 1.6) > 0 ? 4 : -4) : 0;

  const isCenter = position === 'center';
  const centerTransform = isCenter ? 'translateX(-50%)' : '';
  const baseScale = isSpeaker ? 1.05 : 0.92;

  // 入场淡入 + 退出淡出
  const opacity = inScene ? enterProgress * exitProgress * (isSpeaker ? 1.0 : 0.88) : 0;

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
          height: '48%',
          width: position === 'center' ? 'auto' : '48%',
          transform: `${centerTransform} translate(${enterShiftX + shakeX}px, ${enterShiftY + floatOffset + speakerBounce + breathY + shakeY}px) scale(${baseScale * squashX}, ${baseScale * squashY})`,
          transformOrigin: 'bottom center',
          opacity,
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
              ? 'drop-shadow(0 0 16px rgba(255, 255, 255, 0.4)) drop-shadow(0 18px 26px rgba(40, 20, 5, 0.38))'
              : 'drop-shadow(0 8px 14px rgba(0, 0, 0, 0.25))',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

/** 角色头顶漫画特效组件 2.1 */
const CharacterEffectBadge: React.FC<{
  effect: CharacterEffectType;
  frame: number;
  fps: number;
  startFrame: number;
}> = ({effect, frame, fps, startFrame}) => {
  const enter = springIn(frame, startFrame, {fps});
  const pulse = Math.sin(frame * 0.4) * 0.12 + 1;
  const float = Math.sin(frame * 0.25) * 6;

  let emoji = '';
  let bgColor = '#FFF';
  let borderColor = '#1E1E1E';

  if (effect === 'steam') {
    emoji = '💥';
    bgColor = '#FF8A80';
    borderColor = '#D50000';
  } else if (effect === 'sweat') {
    emoji = '💧';
    bgColor = '#80D8FF';
    borderColor = '#0091EA';
  } else if (effect === 'idea') {
    emoji = '💡';
    bgColor = '#FFFF8D';
    borderColor = '#FFD600';
  } else if (effect === 'question') {
    emoji = '❓';
    bgColor = '#FFE082';
    borderColor = '#FF6F00';
  } else {
    return null;
  }

  return (
    <div
      style={{
        fontSize: 54,
        backgroundColor: bgColor,
        border: `4px solid ${borderColor}`,
        borderRadius: '50%',
        width: 80,
        height: 80,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: -20,
        zIndex: 10,
        boxShadow: '0 8px 20px rgba(0,0,0,0.25)',
        transform: `translateY(${float}px) scale(${enter * pulse})`,
      }}
    >
      {emoji}
    </div>
  );
};
