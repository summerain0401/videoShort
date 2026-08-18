// 字幕条组件 —— 治愈卡通风格：描边大字 + 渐变胶囊底

import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {SUBTITLE_SAFE_ZONE} from '../lib/constants';

interface SubtitleProps {
  text: string;
  start: number; // 秒
  end: number; // 秒
  /** 需要高亮显示的关键词列表 */
  highlights?: string[];
}

/**
 * 底部字幕条（治愈卡通风）：
 * - 淡入淡出（各 0.15s）
 * - 白色粗体大字 + 深色描边投影，保证任何背景可读
 * - 半透明奶油色胶囊底 + 白色描边 + 柔和阴影
 * - 始终处于画面底部安全区
 */
export const Subtitle: React.FC<SubtitleProps> = ({text, start, end, highlights = []}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const startFrame = start * fps;
  const endFrame = end * fps;

  const opacity = interpolate(
    frame,
    [startFrame, startFrame + fps * 0.15, endFrame - fps * 0.15, endFrame],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // 轻微上浮入场
  const rise = interpolate(
    frame,
    [startFrame, startFrame + fps * 0.25],
    [12, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  if (opacity <= 0.01) {
    return null;
  }

  // 关键词高亮：把 text 拆成普通段和高亮段
  const renderHighlighted = () => {
    if (!highlights.length) return text;
    const pattern = new RegExp(
      `(${highlights.map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`,
      'g',
    );
    const parts = text.split(pattern);
    return parts.map((part, i) => {
      if (highlights.includes(part)) {
        return (
          <span
            key={i}
            style={{
              color: '#ffd93d',
              textShadow:
                '0 2px 0 rgba(120, 70, 0, 0.45), 0 4px 10px rgba(0, 0, 0, 0.5)',
            }}
          >
            {part}
          </span>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 140,
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        opacity,
        zIndex: 100,
        transform: `translateY(${rise}px)`,
      }}
    >
      <div
        style={{
          background:
            'linear-gradient(180deg, rgba(255, 252, 246, 0.22), rgba(255, 252, 246, 0.08))',
          border: '2px solid rgba(255, 255, 255, 0.4)',
          color: '#ffffff',
          fontSize: 50,
          fontWeight: 800,
          fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif',
          padding: '16px 40px',
          borderRadius: 999,
          maxWidth: '92%',
          textAlign: 'center',
          lineHeight: 1.35,
          textShadow:
            '0 2px 0 rgba(60, 30, 10, 0.35), 0 4px 10px rgba(0, 0, 0, 0.45), 0 0 3px rgba(0, 0, 0, 0.5)',
          boxShadow: '0 10px 28px rgba(0, 0, 0, 0.25)',
        }}
      >
        {renderHighlighted()}
      </div>
    </div>
  );
};
