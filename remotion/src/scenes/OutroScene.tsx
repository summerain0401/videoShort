// 片尾场景 —— 治愈卡通风：暖色卡片问答复习

import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {OUTRO_DURATION} from '../lib/constants';

interface OutroSceneProps {
  /** 概括全文的问题 */
  question: string;
  /** 答案 + 少量结论 */
  answer: string;
}

/**
 * 片尾（治愈卡通风）：
 * - 暖橙→奶油渐变背景
 * - 白色圆角卡片 + 柔和阴影
 * - 「回顾一下」胶囊标签 + 问题 + 答案
 */
export const OutroScene: React.FC<OutroSceneProps> = ({question, answer}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const totalFrames = OUTRO_DURATION * fps;

  const fadeIn = interpolate(frame, [0, fps * 0.3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const cardRise = interpolate(frame, [fps * 0.15, fps * 0.55], [50, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const titleOpacity = interpolate(
    frame,
    [fps * 0.2, fps * 0.6, totalFrames - fps * 0.2, totalFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill
      style={{
        opacity: fadeIn,
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif',
        background:
          'linear-gradient(160deg, #ffb36b 0%, #ff8a3d 45%, #ffb36b 100%)',
      }}
    >
      {/* 装饰圆点 */}
      <div
        style={{
          position: 'absolute',
          top: 140,
          left: 60,
          width: 40,
          height: 40,
          borderRadius: 23,
          background: 'rgba(255, 255, 255, 0.3)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: 200,
          left: 130,
          width: 18,
          height: 18,
          borderRadius: 10,
          background: 'rgba(255, 197, 61, 0.6)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: 160,
          right: 70,
          width: 30,
          height: 30,
          borderRadius: 17,
          background: 'rgba(255, 255, 255, 0.25)',
        }}
      />

      {/* 白色问答卡片 */}
      <div
        style={{
          width: '88%',
          background: 'rgba(255, 252, 246, 0.96)',
          borderRadius: 40,
          padding: '56px 44px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          boxSizing: 'border-box',
          transform: `translateY(${cardRise}px)`,
          boxShadow: '0 24px 60px rgba(120, 50, 0, 0.35)',
          border: '3px solid rgba(255, 255, 255, 0.8)',
        }}
      >
        {/* 「回顾一下」胶囊标签 */}
        <div
          style={{
          color: '#ffffff',
          fontSize: 32,
          fontWeight: 700,
          background: '#ff5a5f',
          padding: '10px 30px',
          borderRadius: 999,
          marginBottom: 36,
            opacity: titleOpacity,
            letterSpacing: 2,
            boxShadow: '0 6px 16px rgba(255, 90, 95, 0.4)',
          }}
        >
          回顾一下
        </div>

        {/* 问题 */}
        <div
          style={{
          color: '#3d2b1f',
          fontSize: 58,
          fontWeight: 800,
          textAlign: 'center',
          lineHeight: 1.35,
          marginBottom: 24,
          }}
        >
          {question}
        </div>

        {/* 答案 */}
        <div
          style={{
          color: '#6b4f3a',
          fontSize: 38,
          fontWeight: 500,
          textAlign: 'center',
          lineHeight: 1.55,
            opacity: 0.92,
          }}
        >
          {answer}
        </div>
      </div>

      {/* 底部小字 */}
      <div
        style={{
          position: 'absolute',
          bottom: 44,
          color: 'rgba(255, 255, 255, 0.8)',
          fontSize: 24,
          letterSpacing: 4,
        }}
      >
        · 完 ·
      </div>
    </AbsoluteFill>
  );
};
