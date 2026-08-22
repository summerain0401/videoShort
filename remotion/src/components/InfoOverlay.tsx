// 动态视觉图层组件（节点3）—— 数字/计算/对比语句触发的纯文本子模板
// 无需生图素材，由 Remotion 直接渲染：
//   price-tag  价格标签（黄橙胶囊 + ¥ 大号数字 + 小标题）
//   equation   算式块（白字描边大算式）
//   vs-card    对比卡（左右两块 + 中间 vs 徽章）

import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {EASE, naturalFloat} from '../lib/animations';
import {SAFE_AREA} from '../lib/constants';
import type {InfoOverlayData} from '../lib/types';

const POSITION_STYLE: Record<NonNullable<InfoOverlayData['position']>, React.CSSProperties> = {
  top: {top: SAFE_AREA.top + 90},
  center: {top: '36%'},
  bottom: {bottom: SAFE_AREA.bottom + 280},
};

const FONT = 'PingFang SC, Microsoft YaHei, sans-serif';

/** 通用入场/漂浮容器：位置由 style 控制 */
const FloatLayer: React.FC<{
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({style, children}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({
    frame,
    fps,
    durationInFrames: 22,
    config: {damping: 12, stiffness: 160},
  });
  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE.out,
  });
  const floatY = naturalFloat(frame / fps, {amp: 6, speed: 0.55});
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        pointerEvents: 'none',
        ...style,
        opacity,
        transform: `translateY(${floatY}px) scale(${0.7 + 0.3 * pop})`,
      }}
    >
      {children}
    </div>
  );
};

/** 价格标签：小标题 + 黄橙胶囊 + ¥ 大号数字 */
const PriceTag: React.FC<{text: string; title?: string; position?: InfoOverlayData['position']}> = ({
  text,
  title,
  position = 'top',
}) => (
  <FloatLayer style={POSITION_STYLE[position]}>
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8}}>
      {title ? (
        <div
          style={{
            fontSize: 30,
            fontWeight: 800,
            color: '#fff',
            background: 'rgba(200, 110, 20, 0.85)',
            borderRadius: 999,
            padding: '4px 22px',
            fontFamily: FONT,
            textShadow: '0 2px 4px rgba(0,0,0,0.35)',
          }}
        >
          {title}
        </div>
      ) : null}
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: 6,
          background: 'linear-gradient(180deg, #ffd93d, #ff9f1a)',
          border: '4px solid #fff',
          borderRadius: 999,
          padding: '10px 36px',
          boxShadow: '0 10px 30px rgba(180, 90, 0, 0.45)',
        }}
      >
        <span style={{fontSize: 52, fontWeight: 900, color: '#7a3c00', fontFamily: FONT}}>¥</span>
        <span
          style={{
            fontSize: 78,
            fontWeight: 900,
            color: '#fff',
            fontFamily: FONT,
            textShadow: '0 3px 0 rgba(122, 60, 0, 0.55), 0 6px 14px rgba(0,0,0,0.3)',
          }}
        >
          {text}
        </span>
      </div>
    </div>
  </FloatLayer>
);

/** 算式块：白字描边大算式 */
const Equation: React.FC<{text: string; title?: string; position?: InfoOverlayData['position']}> = ({
  text,
  title,
  position = 'top',
}) => (
  <FloatLayer style={POSITION_STYLE[position]}>
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8}}>
      {title ? (
        <div
          style={{
            fontSize: 30,
            fontWeight: 800,
            color: '#fff',
            background: 'rgba(40, 90, 120, 0.85)',
            borderRadius: 999,
            padding: '4px 22px',
            fontFamily: FONT,
          }}
        >
          {title}
        </div>
      ) : null}
      <div
        style={{
          fontSize: 96,
          fontWeight: 900,
          color: '#fff',
          fontFamily: FONT,
          background: 'rgba(255, 217, 61, 0.22)',
          border: '3px solid rgba(255, 255, 255, 0.65)',
          borderRadius: 32,
          padding: '14px 48px',
          textShadow: '0 3px 0 rgba(60, 30, 10, 0.4), 0 8px 20px rgba(0,0,0,0.35)',
        }}
      >
        {text}
      </div>
    </div>
  </FloatLayer>
);

/** 对比卡：左 A / vs 徽章 / 右 B */
const VsCard: React.FC<{text: string; title?: string; position?: InfoOverlayData['position']}> = ({
  text,
  title,
  position = 'top',
}) => {
  const sides = text
    .split(/\s*vs\.?\s*/i)
    .map((s) => s.trim())
    .filter(Boolean);
  const [a, b] = sides.length >= 2 ? sides : [text, ''];
  const sideBox = (label: string, color: string) => (
    <div
      style={{
        flex: 1,
        minWidth: 210,
        textAlign: 'center',
        background: `${color}E6`,
        borderRadius: 24,
        border: '3px solid rgba(255,255,255,0.85)',
        padding: '16px 12px',
        boxShadow: '0 8px 22px rgba(0,0,0,0.25)',
      }}
    >
      <div
        style={{
          fontSize: 46,
          fontWeight: 900,
          color: '#fff',
          fontFamily: FONT,
          textShadow: '0 2px 0 rgba(60,30,10,0.4)',
        }}
      >
        {label || '?'}
      </div>
    </div>
  );
  return (
    <FloatLayer style={{...POSITION_STYLE[position], flexDirection: 'column', alignItems: 'center'}}>
      {title ? (
        <div
          style={{
            fontSize: 30,
            fontWeight: 800,
            color: '#7a3c00',
            background: '#ffd93d',
            borderRadius: 999,
            padding: '4px 22px',
            marginBottom: 12,
            fontFamily: FONT,
            boxShadow: '0 6px 16px rgba(0,0,0,0.2)',
          }}
        >
          {title}
        </div>
      ) : null}
      <div style={{display: 'flex', alignItems: 'center', gap: 14}}>
        {sideBox(a, '#ff8a3d')}
        <div
          style={{
            width: 62,
            height: 62,
            borderRadius: 999,
            background: '#fff',
            border: '4px solid #ff8a3d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 26,
            fontWeight: 900,
            color: '#ff8a3d',
            fontFamily: FONT,
            boxShadow: '0 6px 16px rgba(0,0,0,0.2)',
          }}
        >
          VS
        </div>
        {sideBox(b, '#3f9dd0')}
      </div>
    </FloatLayer>
  );
};

export const InfoOverlay: React.FC<InfoOverlayData> = ({kind, text, title, position}) => {
  if (!text) {
    return null;
  }
  if (kind === 'price-tag') {
    return <PriceTag text={text} title={title} position={position} />;
  }
  if (kind === 'vs-card') {
    return <VsCard text={text} title={title} position={position} />;
  }
  return <Equation text={text} title={title} position={position} />;
};
