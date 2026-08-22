// 片尾场景 —— 治愈卡通风：暖色卡片问答复习 + 小布丁出镜
// 三段式节奏：P1 提问(0-45帧) → P2 停顿强调(45-90帧) → P3 答案揭晓(90-150帧)

import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {EASE, emotionCrossfade, naturalFloat, pulseScale, springIn} from '../lib/animations';
import {OUTRO_DURATION, SAFE_AREA} from '../lib/constants';
import {FloatingParticles} from '../components/effects/FloatingParticles';
import {AmbientBokeh} from '../components/effects/AmbientBokeh';
import {staticPath} from '../lib/staticPath';

interface OutroSceneProps {
  /** 概括全文的问题 */
  question: string;
  /** 答案 + 少量结论 */
  answer: string;
  /** 提问阶段角色图片路径（可选，缺省不渲染角色） */
  characterImage?: string;
  /** 答案揭晓阶段角色图片路径（可选） */
  characterImageHappy?: string;
}

/**
 * 片尾（治愈卡通风）：
 * - 暖橙→奶油渐变背景 + 光斑/粒子装饰
 * - 小布丁角色出镜：思考表情 → 答案揭晓时交叉过渡到微笑
 * - 「提问 → 停顿 → 答案揭晓」三段式节奏，答案 spring 弹入
 * - 白色圆角卡片 + 柔和阴影
 */
export const OutroScene: React.FC<OutroSceneProps> = ({
  question,
  answer,
  characterImage,
  characterImageHappy,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const totalFrames = OUTRO_DURATION * fps;

  const fadeIn = interpolate(frame, [0, fps * 0.3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE.out,
  });

  // ---- P1 提问（0 - 45 帧）----
  const labelSpring = springIn(frame, 0, {fps});
  const labelOpacity = interpolate(frame, [0, fps * 0.2], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE.out,
  });

  const questionRise = interpolate(frame, [fps * 0.15, fps * 0.6], [44, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE.out,
  });
  const questionOpacity = interpolate(frame, [fps * 0.15, fps * 0.45], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE.out,
  });

  // ---- P2 停顿（45 - 90 帧）：问题呼吸强调 ----
  const pauseProgress = interpolate(frame, [fps * 1.5, fps * 3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const questionPulse = pulseScale(Math.min(pauseProgress, 1), {
    min: 1,
    max: 1.03,
    speed: 1.4,
  });

  // ---- P3 答案揭晓（90 - 150 帧）----
  const revealProgress = interpolate(frame, [fps * 3, fps * 3.8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const answerSpring = springIn(frame, fps * 3, {fps});
  const answerOpacity = interpolate(frame, [fps * 3, fps * 3.5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE.out,
  });

  // ---- 角色：思考 → 微笑 交叉过渡（0.6s）----
  // 在 P3 答案揭晓起点（fps*3）开始过渡，0.6s 后完成，而非拖到片尾最后一刻
  const [thinkOpacity, smileOpacity] = emotionCrossfade(frame, fps * 3, fps * 3.6, {
    fps,
  });
  const characterVisible = Boolean(characterImage);
  // 角色整体淡入
  const charEnter = springIn(frame, fps * 0.1, {fps});
  const charFloat = naturalFloat(frame / fps / 8, {amp: 12, speed: 1.4});

  // 底部「完」淡入
  const endOpacity = interpolate(
    frame,
    [fps * 0.8, fps * 1.4, totalFrames - fps * 0.2, totalFrames],
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
      {/* 背景装饰特效（统一治愈风，低透明度） */}
      <AmbientBokeh count={8} colors={['#fff3c4', '#ffffff', '#ffd93d']} opacity={0.18} sizeRange={[50, 170]} />
      <FloatingParticles count={12} color="#fff3c4" opacity={0.2} sizeRange={[6, 16]} amp={12} />

      {/* 角色层：顶部居中出镜，思考 → 微笑 */}
      {characterVisible ? (
        <div
          style={{
            position: 'absolute',
            top: SAFE_AREA.top + 30,
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'center',
            zIndex: 3,
            opacity: charEnter,
            transform: `translateY(${charFloat}px)`,
            pointerEvents: 'none',
          }}
        >
          {/* 思考表情（提问阶段） */}
          <Img
            src={staticPath(characterImage)}
            style={{
              height: 320,
              width: 'auto',
              objectFit: 'contain',
              opacity: thinkOpacity,
              filter: 'drop-shadow(0 12px 18px rgba(120, 50, 0, 0.3))',
            }}
          />
          {/* 微笑表情（答案揭晓，覆盖在上面交叉过渡） */}
          {characterImageHappy ? (
            <Img
              src={staticPath(characterImageHappy)}
              style={{
                position: 'absolute',
                left: 0,
                right: 0,
                margin: '0 auto',
                height: 320,
                width: 'auto',
                objectFit: 'contain',
                opacity: smileOpacity,
                filter: 'drop-shadow(0 12px 18px rgba(120, 50, 0, 0.3))',
              }}
            />
          ) : null}
        </div>
      ) : null}

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
          transform: `translateY(${(1 - revealProgress) * 10}px) scale(${1 + (1 - answerSpring) * -0.02})`,
          boxShadow: '0 24px 60px rgba(120, 50, 0, 0.35)',
          border: '3px solid rgba(255, 255, 255, 0.8)',
          marginTop: characterVisible ? 330 : 0,
        }}
      >
        {/* 「回顾一下」胶囊标签（spring 弹入） */}
        <div
          style={{
            color: '#ffffff',
            fontSize: 32,
            fontWeight: 700,
            background: '#ff5a5f',
            padding: '10px 30px',
            borderRadius: 999,
            marginBottom: 36,
            opacity: labelOpacity,
            letterSpacing: 2,
            transform: `scale(${0.7 + labelSpring * 0.3})`,
            boxShadow: '0 6px 16px rgba(255, 90, 95, 0.4)',
          }}
        >
          回顾一下
        </div>

        {/* 问题（P2 阶段轻幅呼吸 pulse） */}
        <div
          style={{
            color: '#3d2b1f',
            fontSize: 58,
            fontWeight: 800,
            textAlign: 'center',
            lineHeight: 1.35,
            marginBottom: 24,
            opacity: questionOpacity,
            transform: `translateY(${questionRise}px) scale(${questionPulse})`,
          }}
        >
          {question}
        </div>

        {/* 答案（P3 spring 弹入 + 关键词底色渐显） */}
        <div
          style={{
            color: '#6b4f3a',
            fontSize: 38,
            fontWeight: 500,
            textAlign: 'center',
            lineHeight: 1.55,
            background: `rgba(255, 197, 61, ${0.25 * revealProgress})`,
            borderRadius: 20,
            padding: '14px 24px',
            opacity: answerOpacity,
            transform: `scale(${0.9 + answerSpring * 0.1})`,
          }}
        >
          {answer}
        </div>
      </div>

      {/* 底部小字 */}
      <div
        style={{
          position: 'absolute',
          bottom: SAFE_AREA.bottom,
          color: 'rgba(255, 255, 255, 0.8)',
          fontSize: 24,
          letterSpacing: 4,
          opacity: endOpacity,
        }}
      >
        · 完 ·
      </div>
    </AbsoluteFill>
  );
};
