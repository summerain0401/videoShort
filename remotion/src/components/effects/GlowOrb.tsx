// 背景柔光球 —— 大尺寸径向渐变 + 模糊，缓慢漂浮，增加画面层次与温度

import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {naturalFloat} from '../../lib/animations';

interface GlowOrbProps {
  /** 光球颜色（径向渐变中心色） */
  color: string;
  /** 直径 px */
  size?: number;
  /** 位置（百分比或像素） */
  top?: string;
  left?: string;
  /** 整体不透明度（建议 ≤ 0.3） */
  opacity?: number;
  /** 漂浮幅度 px */
  amp?: number;
}

/**
 * 背景柔光球：
 * - 径向渐变 + blur 制造柔和光晕
 * - 基于场景进度缓慢漂浮（双频正弦）
 * - 通常置于背景层之上、内容层之下
 */
export const GlowOrb: React.FC<GlowOrbProps> = ({
  color,
  size = 520,
  top = '20%',
  left = '50%',
  opacity = 0.22,
  amp = 16,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  const dx = naturalFloat(t / 8, {amp: amp * 0.6, speed: 1, phase: 1.3});
  const dy = naturalFloat(t / 10, {amp, speed: 0.8, phase: 0.4});
  const pulse = 1 + 0.05 * Math.sin(t * 0.6);

  return (
    <div
      style={{
        position: 'absolute',
        top,
        left,
        width: size,
        height: size,
        borderRadius: '50%',
        background: `radial-gradient(circle at 50% 50%, ${color} 0%, ${color} 25%, rgba(255, 255, 255, 0) 70%)`,
        filter: 'blur(30px)',
        opacity,
        transform: `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) scale(${pulse})`,
        pointerEvents: 'none',
        zIndex: 1,
      }}
    />
  );
};
