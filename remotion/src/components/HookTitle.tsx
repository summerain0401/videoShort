// 悬浮标题贴纸 —— 替代静态片头卡：第 0 秒正文已开播，标题以动效贴纸浮在画面上方
// 治愈卡通风：奶油色圆角卡片 + 橙色描边 + 轻微呼吸浮动，2.4s 后淡出

import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {EASE, naturalFloat, springIn} from '../lib/animations';
import {SAFE_AREA} from '../lib/constants';

interface HookTitleProps {
  title: string;
}

const HOOK_DURATION = 2.6; // 秒：弹入(0.5s) → 停留浮动 → 淡出(0.4s)

export const HookTitle: React.FC<HookTitleProps> = ({title}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // 弹入：scale 0.82 → 1，带回弹（spring）
  const pop = springIn(frame, 0, {fps});
  const scale = 0.82 + 0.18 * pop;

  // 呼吸浮动（叠加在弹入之后）
  const progress = frame / (HOOK_DURATION * fps);
  const floatY = naturalFloat(progress, {amp: 7, speed: 1.6});

  // 整体淡出（2.2s 开始，0.4s 淡出）
  const opacity = interpolate(
    frame,
    [HOOK_DURATION * fps - fps * 0.4, HOOK_DURATION * fps],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out},
  );

  if (opacity <= 0.01) {
    return null;
  }

  return (
    <div
      style={{
        position: 'absolute',
        top: SAFE_AREA.top + 12,
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        opacity,
        transform: `translateY(${floatY}px)`,
        pointerEvents: 'none',
        zIndex: 20,
      }}
    >
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 22px',
          borderRadius: 999,
          background: 'rgba(255, 248, 238, 0.94)',
          border: '3px solid #ffb36b',
          boxShadow: '0 6px 18px rgba(180, 100, 30, 0.22)',
          transform: `scale(${scale})`,
          transformOrigin: 'center top',
        }}
      >
        <span
          style={{
            fontSize: 24,
            lineHeight: 1,
            filter: 'drop-shadow(0 2px 3px rgba(180, 100, 30, 0.35))',
          }}
        >
          ❓
        </span>
        <span
          style={{
            fontSize: 30,
            fontWeight: 800,
            color: '#7a4a12',
            letterSpacing: 1,
            textShadow: '0 1px 0 rgba(255,255,255,0.6)',
          }}
        >
          {title}
        </span>
      </div>
    </div>
  );
};
