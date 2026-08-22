// 字幕条组件 —— 治愈卡通风格：描边大字 + 渐变胶囊底

import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {EASE, pulseScale} from '../lib/animations';
import {SAFE_AREA} from '../lib/constants';

interface SubtitleSegment {
  text: string;
  start: number;
  end: number;
}

interface SubtitleProps {
  text: string;
  start: number; // 秒
  end: number; // 秒
  /** 需要高亮显示的关键词列表 */
  highlights?: string[];
  /** 节点5：6~10 字断句段（场景相对秒）。有则按当前时间只显示对应段 */
  segments?: SubtitleSegment[];
}

/**
 * 底部字幕条（治愈卡通风）：
 * - 淡入淡出（各 0.15s，缓动曲线）
 * - 白色粗体大字 + 深色描边投影，保证任何背景可读
 * - 半透明奶油色胶囊底 + 白色描边 + 柔和阴影
 * - 始终处于画面底部安全区（bottom = SAFE_AREA.bottom + 20）
 * - 关键词高亮带轻幅 pulse 动效
 * - 节点5：传入 segments 时逐段显示（6~10 字/段），每段独立淡入淡出
 */
export const Subtitle: React.FC<SubtitleProps> = ({text, start, end, highlights = [], segments}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // 断句模式：按当前时间选出应显示的段（衔接处 0.05s 容差，间隙时保持上一段）
  let displayText = text;
  let segStart = start;
  let segEnd = end;
  let segHighlights = highlights;
  if (segments && segments.length > 0) {
    const t = frame / fps;
    let idx = segments.findIndex((s) => t >= s.start - 0.05 && t <= s.end + 0.05);
    if (idx < 0) {
      for (let i = segments.length - 1; i >= 0; i--) {
        if (t >= segments[i].start) {
          idx = i;
          break;
        }
      }
      if (idx < 0) {
        idx = 0;
      }
    }
    const seg = segments[Math.min(idx, segments.length - 1)];
    displayText = seg.text;
    segStart = seg.start;
    segEnd = seg.end;
    segHighlights = highlights.filter((h) => seg.text.includes(h));
  }

  const startFrame = segStart * fps;
  const endFrame = segEnd * fps;

  const opacity = interpolate(
    frame,
    [startFrame, startFrame + fps * 0.12, endFrame - fps * 0.12, endFrame],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out},
  );

  // 轻微上浮入场（缓动）
  const rise = interpolate(
    frame,
    [startFrame, startFrame + fps * 0.25],
    [12, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out},
  );

  if (opacity <= 0.01) {
    return null;
  }

  // 关键词高亮：把 text 拆成普通段和高亮段
  const renderHighlighted = () => {
    if (!segHighlights.length) return displayText;
    const pattern = new RegExp(
      `(${segHighlights.map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`,
      'g',
    );
    const parts = displayText.split(pattern);
    return parts.map((part, i) => {
      if (segHighlights.includes(part)) {
        // 高亮词 pulse：基于当前段展示周期循环
        const pulse = pulseScale(
          (frame - startFrame) / Math.max(1, endFrame - startFrame),
          {min: 1, max: 1.06, speed: 2.2},
        );
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              color: '#ffd93d',
              transform: `scale(${pulse})`,
              transformOrigin: 'center',
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
        bottom: SAFE_AREA.bottom + 20,
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
