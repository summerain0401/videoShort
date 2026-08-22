// 背景光斑 —— 多个模糊圆斑缓慢缩放浮动，模拟景深里的虚化光点

import React from 'react';
import {AbsoluteFill, random, useCurrentFrame, useVideoConfig} from 'remotion';

interface AmbientBokehProps {
  /** 光斑数量 */
  count?: number;
  /** 光斑颜色池（循环取用） */
  colors?: string[];
  /** 整体不透明度（建议 ≤ 0.2） */
  opacity?: number;
  /** 光斑直径范围 px */
  sizeRange?: [number, number];
}

interface Bokeh {
  x: number;
  y: number;
  size: number;
  color: string;
  phase: number;
  rate: number;
}

/**
 * 背景光斑：
 * - 位置/大小/颜色随机预生成
 * - 每帧轻微缩放 + 上下浮动，模拟呼吸感
 * - 纯装饰层，pointerEvents 关闭
 */
export const AmbientBokeh: React.FC<AmbientBokehProps> = ({
  count = 10,
  colors = ['#ffffff', '#ffd93d', '#ffb36b'],
  opacity = 0.16,
  sizeRange = [40, 160],
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  const bokehs: Bokeh[] = React.useMemo(
    () =>
      Array.from({length: count}, (_, i) => {
        const [min, max] = sizeRange;
        return {
          x: random(`bx-${i}`) * 100,
          y: random(`by-${i}`) * 100,
          size: min + random(`bs-${i}`) * (max - min),
          color: colors[i % colors.length],
          phase: random(`bp-${i}`) * Math.PI * 2,
          rate: 0.4 + random(`br-${i}`) * 0.6,
        };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [count, sizeRange[0], sizeRange[1]],
  );

  return (
    <AbsoluteFill style={{opacity, pointerEvents: 'none', zIndex: 1}}>
      {bokehs.map((b, i) => {
        const breathe = 0.5 - 0.5 * Math.cos(t * b.rate * 1.6 + b.phase);
        const scale = 0.85 + breathe * 0.35;
        const dy = Math.sin(t * b.rate * 2 + b.phase) * 10;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${b.x}%`,
              top: `${b.y}%`,
              width: b.size,
              height: b.size,
              borderRadius: '50%',
              background: b.color,
              filter: 'blur(14px)',
              opacity: 0.4 + breathe * 0.5,
              transform: `translate(-50%, calc(-50% + ${dy}px)) scale(${scale})`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
