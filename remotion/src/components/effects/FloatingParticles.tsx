// 漂浮粒子 —— 治愈卡通风格的背景点缀，向上缓漂 + 横向轻摆

import React from 'react';
import {AbsoluteFill, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {naturalFloat} from '../../lib/animations';

interface FloatingParticlesProps {
  /** 粒子数量 */
  count?: number;
  /** 粒子颜色 */
  color?: string;
  /** 整体不透明度（建议 ≤ 0.25，避免喧宾夺主） */
  opacity?: number;
  /** 粒子直径范围 [min, max] px */
  sizeRange?: [number, number];
  /** 覆盖区域：'full' | 'top' | 'bottom'（默认 full） */
  zone?: 'full' | 'top' | 'bottom';
  /** 漂浮幅度 px */
  amp?: number;
}

interface Particle {
  seed: number;
  size: number;
  x: number; // 水平位置 %
  delay: number; // 秒
  speed: number;
  opacity: number;
}

/**
 * 漂浮粒子：
 * - 位置/大小/速度由 random(seed) 预生成，渲染帧稳定
 * - 每帧基于相对秒数计算漂浮，向上缓漂 + sin 横向摆动
 * - 纯装饰层，pointerEvents 关闭
 */
export const FloatingParticles: React.FC<FloatingParticlesProps> = ({
  count = 14,
  color = '#ffd93d',
  opacity = 0.22,
  sizeRange = [6, 18],
  zone = 'full',
  amp = 14,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  // 粒子静态属性预生成（依赖 count 固定不变）
  const particles: Particle[] = React.useMemo(() => {
    const [minSize, maxSize] = sizeRange;
    return Array.from({length: count}, (_, i) => {
      const seed = i * 0.618;
      return {
        seed,
        size: minSize + random(`size-${i}`) * (maxSize - minSize),
        x: random(`x-${i}`) * 100,
        delay: random(`delay-${i}`) * 6,
        speed: 0.6 + random(`speed-${i}`) * 0.9,
        opacity: 0.35 + random(`op-${i}`) * 0.65,
      };
    });
  }, [count, sizeRange[0], sizeRange[1]]);

  const topBase = zone === 'top' ? 0 : zone === 'bottom' ? 55 : 0;
  const bottomBase = zone === 'top' ? 45 : zone === 'bottom' ? 100 : 100;

  return (
    <AbsoluteFill style={{opacity, pointerEvents: 'none', zIndex: 1}}>
      {particles.map((p, i) => {
        // 每个粒子独立循环：漂浮周期 = 8s / speed，delay 错开
        const cycle = (t + p.delay) / (8 / p.speed);
        const cycleProgress = cycle % 1;
        // 垂直位置：从底部 100% 缓漂到顶部 0%（循环）
        const yPct = bottomBase - cycleProgress * (bottomBase - topBase);
        const xSway = Math.sin(cycleProgress * Math.PI * 2 * 1.3 + p.seed * 10) * amp;
        const scale = 0.7 + 0.6 * Math.sin(cycleProgress * Math.PI + p.seed * 8);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${p.x}%`,
              top: `${yPct}%`,
              width: p.size,
              height: p.size,
              borderRadius: '50%',
              background: color,
              transform: `translateX(${xSway}px) scale(${scale})`,
              opacity: p.opacity * Math.sin(cycleProgress * Math.PI),
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
