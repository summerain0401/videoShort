// 片头场景 —— 治愈卡通风：小镇背景 + 大标题卡片

import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {INTRO_DURATION} from '../lib/constants';
import {staticPath} from '../lib/staticPath';

interface IntroSceneProps {
  title: string;
  /** 估算时长文案，如 "约 1 分钟" */
  durationLabel?: string;
}

/**
 * 片头（治愈卡通风）：
 * - 治愈系小镇街道背景 + 暖色渐变遮罩
 * - 大标题卡片淡入 + 轻微缩放
 * - 左上角频道标签、右下角时长胶囊
 */
export const IntroScene: React.FC<IntroSceneProps> = ({
  title,
  durationLabel = '约 1 分钟',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const totalFrames = INTRO_DURATION * fps;

  const opacity = interpolate(
    frame,
    [0, fps * 0.3, totalFrames - fps * 0.3, totalFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const scale = interpolate(frame, [0, fps * 0.5], [0.94, 1], {
    extrapolateRight: 'clamp',
  });

  // 片头背景 Ken Burns：缓慢放大 + 轻微左移
  const bgProgress = frame / totalFrames;
  // 竖屏片头背景 Ken Burns：轻微推进即可，避免画面移动过大
  const bgScale = interpolate(bgProgress, [0, 1], [1, 1.06], {extrapolateRight: 'clamp'});
  const bgTranslateY = interpolate(bgProgress, [0, 1], [0, -18], {extrapolateRight: 'clamp'});

  const titleRise = interpolate(frame, [fps * 0.15, fps * 0.6], [36, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const badgeOpacity = interpolate(
    frame,
    [fps * 0.05, fps * 0.35, totalFrames - fps * 0.2, totalFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill style={{opacity}}>
      {/* 小镇街道背景（Ken Burns 缓慢推进） */}
      <Img
        src={staticPath('shared/backgrounds/bg_town.png')}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${bgScale}) translate(0px, ${bgTranslateY}px)`,
          transformOrigin: 'center center',
        }}
      />

      {/* 暖色渐变遮罩：上下压暗，保证文字可读 */}
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(50, 25, 5, 0.35) 0%, rgba(50, 25, 5, 0) 35%, rgba(50, 25, 5, 0.15) 70%, rgba(50, 25, 5, 0.55) 100%)',
        }}
      />

      {/* 左上角频道标签 */}
      <div
        style={{
          position: 'absolute',
          top: 100,
          left: 60,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          background: 'rgba(255, 252, 246, 0.85)',
          padding: '10px 22px',
          borderRadius: 999,
          boxShadow: '0 4px 14px rgba(0, 0, 0, 0.2)',
          opacity: badgeOpacity,
        }}
      >
        <span
          style={{
            display: 'inline-block',
            width: 14,
            height: 14,
            borderRadius: 7,
            background: '#ff5a5f',
          }}
        />
        <span
          style={{
            color: '#3d2b1f',
            fontSize: 26,
            fontWeight: 700,
            fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif',
          }}
        >
          知识小课堂
        </span>
      </div>

      {/* 主题标题卡片 */}
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          transform: `scale(${scale})`,
        }}
      >
        <div
          style={{
          color: '#ffffff',
          fontSize: 92,
          fontWeight: 800,
          fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif',
          textAlign: 'center',
          padding: '44px 56px',
          lineHeight: 1.35,
          maxWidth: '86%',
            transform: `translateY(${titleRise}px)`,
            textShadow:
              '0 4px 0 rgba(60, 30, 10, 0.4), 0 10px 30px rgba(0, 0, 0, 0.45)',
            background: 'rgba(0, 0, 0, 0.22)',
            borderRadius: 32,
            border: '3px solid rgba(255, 255, 255, 0.35)',
            backdropFilter: 'blur(4px)',
            boxShadow: '0 16px 40px rgba(0, 0, 0, 0.25)',
          }}
        >
          {title}
        </div>
      </AbsoluteFill>

      {/* 右下角时长胶囊 */}
      <div
        style={{
          position: 'absolute',
          bottom: 120,
          right: 60,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          background: 'rgba(40, 20, 5, 0.55)',
          padding: '10px 24px',
          borderRadius: 999,
          border: '2px solid rgba(255, 255, 255, 0.35)',
          opacity: badgeOpacity,
        }}
      >
        <span
          style={{
            display: 'inline-block',
            width: 22,
            height: 22,
            borderRadius: 6,
            background: '#ffc53d',
          }}
        />
        <span
          style={{
            color: '#ffffff',
            fontSize: 26,
            fontWeight: 600,
            fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif',
          }}
        >
          {durationLabel}
        </span>
      </div>
    </AbsoluteFill>
  );
};
