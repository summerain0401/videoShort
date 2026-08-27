import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {EASE, springIn} from '../lib/animations';
import type {InfographicData} from '../lib/types';

interface InfographicsProps {
  data: InfographicData;
  start?: number;
}

export const Infographics: React.FC<InfographicsProps> = ({data, start = 0}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const startFrame = start * fps;
  const enterSpring = springIn(frame, startFrame, {fps});
  const opacity = interpolate(frame, [startFrame, startFrame + fps * 0.2], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  if (frame < startFrame || opacity <= 0.01) {
    return null;
  }

  return (
    <div
      style={{
        position: 'absolute',
        top: '20%',
        left: '8%',
        width: '84%',
        zIndex: 45,
        opacity,
        transform: `scale(${enterSpring})`,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          backgroundColor: 'rgba(255, 253, 240, 0.95)',
          border: '6px solid #1E1E1E',
          borderRadius: 32,
          padding: '24px 28px',
          boxShadow: '0 16px 36px rgba(0,0,0,0.18)',
        }}
      >
        {data.title ? (
          <div
            style={{
              fontSize: 32,
              fontWeight: 900,
              color: '#D32F2F',
              textAlign: 'center',
              marginBottom: 16,
              letterSpacing: 1,
            }}
          >
            📊 {data.title}
          </div>
        ) : null}

        {data.kind === 'balance' && (
          <BalanceView
            leftLabel={data.leftLabel || '选项A'}
            rightLabel={data.rightLabel || '选项B'}
            tilt={data.tilt || 'right'}
            startFrame={startFrame}
          />
        )}

        {data.kind === 'bar' && (
          <BarChartView bars={data.bars || []} startFrame={startFrame} />
        )}

        {data.kind === 'counter' && data.counter && (
          <CounterView
            from={data.counter.from}
            to={data.counter.to}
            prefix={data.counter.prefix || ''}
            suffix={data.counter.suffix || ''}
            startFrame={startFrame}
          />
        )}
      </div>
    </div>
  );
};

// 1. 天平倾斜动画组件
const BalanceView: React.FC<{
  leftLabel: string;
  rightLabel: string;
  tilt: 'left' | 'right' | 'balanced';
  startFrame: number;
}> = ({leftLabel, rightLabel, tilt, startFrame}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const targetAngle = tilt === 'left' ? -14 : tilt === 'right' ? 14 : 0;
  const rotation = interpolate(
    frame,
    [startFrame + fps * 0.2, startFrame + fps * 0.8],
    [0, targetAngle],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out}
  );

  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '10px 0'}}>
      {/* 天平横梁与托盘 */}
      <div
        style={{
          width: '90%',
          height: 12,
          backgroundColor: '#37474F',
          borderRadius: 6,
          position: 'relative',
          transform: `rotate(${rotation}deg)`,
          transformOrigin: 'center center',
          transition: 'transform 0.1s',
          margin: '30px 0 40px 0',
        }}
      >
        {/* 左托盘 */}
        <div
          style={{
            position: 'absolute',
            left: -10,
            top: 12,
            width: 140,
            backgroundColor: '#FFD54F',
            border: '4px solid #1E1E1E',
            borderRadius: 16,
            padding: '8px 10px',
            textAlign: 'center',
            fontSize: 26,
            fontWeight: 800,
            color: '#212121',
            transform: `rotate(${-rotation}deg)`,
          }}
        >
          {leftLabel}
        </div>

        {/* 右托盘 */}
        <div
          style={{
            position: 'absolute',
            right: -10,
            top: 12,
            width: 140,
            backgroundColor: '#FF8A80',
            border: '4px solid #1E1E1E',
            borderRadius: 16,
            padding: '8px 10px',
            textAlign: 'center',
            fontSize: 26,
            fontWeight: 800,
            color: '#212121',
            transform: `rotate(${-rotation}deg)`,
          }}
        >
          {rightLabel}
        </div>
      </div>

      {/* 天平支柱与底座 */}
      <div style={{width: 14, height: 40, backgroundColor: '#37474F', borderRadius: 4}} />
      <div style={{width: 90, height: 12, backgroundColor: '#37474F', borderRadius: 6}} />
    </div>
  );
};

// 2. 动态对比柱状图
const BarChartView: React.FC<{
  bars: Array<{label: string; value: number; color?: string; unit?: string}>;
  startFrame: number;
}> = ({bars, startFrame}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const progress = interpolate(
    frame,
    [startFrame + fps * 0.15, startFrame + fps * 0.7],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out}
  );

  const maxValue = Math.max(...bars.map((b) => b.value), 1);

  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: 16, margin: '10px 0'}}>
      {bars.map((bar, i) => {
        const pct = (bar.value / maxValue) * 100 * progress;
        const barColor = bar.color || (i === 0 ? '#42A5F5' : '#EF5350');

        return (
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: 14}}>
            <div style={{width: 110, fontSize: 26, fontWeight: 800, color: '#37474F', textAlign: 'right'}}>
              {bar.label}
            </div>
            <div
              style={{
                flex: 1,
                height: 38,
                backgroundColor: '#ECEFF1',
                borderRadius: 19,
                overflow: 'hidden',
                border: '3px solid #1E1E1E',
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: '100%',
                  backgroundColor: barColor,
                  borderRadius: 16,
                }}
              />
            </div>
            <div style={{width: 100, fontSize: 28, fontWeight: 900, color: '#1E1E1E'}}>
              {Math.round(bar.value * progress)}
              {bar.unit || ''}
            </div>
          </div>
        );
      })}
    </div>
  );
};

// 3. 动态跳字计数器
const CounterView: React.FC<{
  from: number;
  to: number;
  prefix: string;
  suffix: string;
  startFrame: number;
}> = ({from, to, prefix, suffix, startFrame}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const val = interpolate(
    frame,
    [startFrame + fps * 0.15, startFrame + fps * 0.9],
    [from, to],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out}
  );

  return (
    <div style={{textAlign: 'center', padding: '10px 0'}}>
      <div style={{fontSize: 64, fontWeight: 900, color: '#E53935', letterSpacing: 2}}>
        {prefix}
        {Math.round(val).toLocaleString()}
        {suffix}
      </div>
    </div>
  );
};
