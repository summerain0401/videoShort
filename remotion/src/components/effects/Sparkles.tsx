// 闪烁星光 —— 4 芒星光，随机位置 + 闪烁，营造治愈氛围

import React from 'react';
import {AbsoluteFill, random, useCurrentFrame, useVideoConfig} from 'remotion';

interface SparklesProps {
  /** 星光数量 */
  count?: number;
  /** 星光颜色 */
  color?: string;
  /** 星光尺寸（对角线长度 px） */
  size?: number;
  /** 整体不透明度（建议 ≤ 0.3） */
  opacity?: number;
  /** 闪烁速度倍率 */
  speed?: number;
}

interface Sparkle {
  x: number; // %
  y: number; // %
  size: number;
  phase: number;
  rate: number;
}

/**
 * 闪烁星光：
 * - 位置随机预生成，闪烁相位错开
 * - 用两个交叉菱形组成 4 芒星，旋转制造光芒感
 * - 纯装饰层，pointerEvents 关闭
 */
export const Sparkles: React.FC<SparklesProps> = ({
  count = 8,
  color = '#fff3c4',
  size = 26,
  opacity = 0.28,
  speed = 1,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  const sparkles: Sparkle[] = React.useMemo(
    () =>
      Array.from({length: count}, (_, i) => ({
        x: random(`sx-${i}`) * 96 + 2,
        y: random(`sy-${i}`) * 96 + 2,
        size: size * (0.55 + random(`sz-${i}`) * 0.9),
        phase: random(`sp-${i}`) * Math.PI * 2,
        rate: 0.5 + random(`sr-${i}`) * 0.7,
      })),
    [count, size],
  );

  return (
    <AbsoluteFill style={{opacity, pointerEvents: 'none', zIndex: 1}}>
      {sparkles.map((s, i) => {
        const wave = 0.5 - 0.5 * Math.cos(t * speed * s.rate * 2.4 + s.phase);
        const alpha = 0.25 + wave * 0.75;
        const scale = 0.8 + wave * 0.5;
        const rotate = s.phase * 30;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${s.x}%`,
              top: `${s.y}%`,
              width: s.size,
              height: s.size,
              opacity: alpha,
              transform: `rotate(${rotate}deg) scale(${scale})`,
            }}
          >
            {/* 水平芒 + 垂直芒 */}
            <div
              style={{
                position: 'absolute',
                left: '50%',
                top: '50%',
                width: s.size,
                height: 3,
                borderRadius: 2,
                background: color,
                transform: 'translate(-50%, -50%)',
              }}
            />
            <div
              style={{
                position: 'absolute',
                left: '50%',
                top: '50%',
                width: 3,
                height: s.size,
                borderRadius: 2,
                background: color,
                transform: 'translate(-50%, -50%)',
              }}
            />
            {/* 中心光点 */}
            <div
              style={{
                position: 'absolute',
                left: '50%',
                top: '50%',
                width: s.size * 0.4,
                height: s.size * 0.4,
                borderRadius: '50%',
                background: color,
                transform: 'translate(-50%, -50%)',
                boxShadow: `0 0 ${s.size * 0.6}px ${color}`,
              }}
            />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
