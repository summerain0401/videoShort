import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {springIn} from '../lib/animations';

interface DialogueBubbleProps {
  speaker: string;
  text: string;
  side?: 'left' | 'right' | 'center';
  start?: number;
}

const SPEAKER_COLORS: Record<string, {bg: string; text: string; border: string}> = {
  '小新': {bg: '#FFD21E', text: '#D32F2F', border: '#D32F2F'},
  '美伢': {bg: '#FF80AB', text: '#4A148C', border: '#C2185B'},
  '广志': {bg: '#81D4FA', text: '#0D47A1', border: '#0288D1'},
  '小白': {bg: '#FFFFFF', text: '#37474F', border: '#455A64'},
  '风间': {bg: '#90CAF9', text: '#1565C0', border: '#1976D2'},
};

export const DialogueBubble: React.FC<DialogueBubbleProps> = ({
  speaker,
  text,
  side = 'left',
  start = 0,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const startFrame = start * fps;
  const enterSpring = springIn(frame, startFrame, {fps});
  const opacity = interpolate(frame, [startFrame, startFrame + fps * 0.15], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  if (frame < startFrame || opacity <= 0.01) {
    return null;
  }

  const theme = SPEAKER_COLORS[speaker] || {bg: '#FFE082', text: '#212121', border: '#212121'};

  const bubbleLeft = side === 'left' ? '6%' : side === 'right' ? '14%' : '10%';
  const tailLeft = side === 'left' ? '25%' : side === 'right' ? '75%' : '50%';

  return (
    <div
      style={{
        position: 'absolute',
        top: '26%',
        left: bubbleLeft,
        width: '84%',
        zIndex: 50,
        opacity,
        transform: `scale(${enterSpring})`,
        transformOrigin: side === 'left' ? 'bottom left' : 'bottom right',
        pointerEvents: 'none',
      }}
    >
      {/* 对话框主体 */}
      <div
        style={{
          position: 'relative',
          backgroundColor: '#FFFFFF',
          border: '7px solid #1E1E1E',
          borderRadius: 36,
          padding: '24px 32px',
          boxShadow: '0 16px 30px rgba(0,0,0,0.2), inset 0 2px 6px rgba(255,255,255,0.8)',
        }}
      >
        {/* 发言人徽章 */}
        <div
          style={{
            position: 'absolute',
            top: -24,
            left: side === 'left' ? 28 : undefined,
            right: side === 'right' ? 28 : undefined,
            backgroundColor: theme.bg,
            color: theme.text,
            border: `5px solid ${theme.border}`,
            borderRadius: 20,
            padding: '4px 20px',
            fontSize: 30,
            fontWeight: 900,
            letterSpacing: 1.5,
            boxShadow: '0 4px 10px rgba(0,0,0,0.15)',
          }}
        >
          {speaker}
        </div>

        {/* 对话文字 */}
        <div
          style={{
            fontSize: 42,
            fontWeight: 800,
            color: '#1E1E1E',
            lineHeight: 1.4,
            textAlign: 'center',
            letterSpacing: 1,
            marginTop: 6,
          }}
        >
          {text}
        </div>

        {/* 气泡尖角小尾巴 */}
        <div
          style={{
            position: 'absolute',
            bottom: -22,
            left: tailLeft,
            transform: 'translateX(-50%)',
            width: 0,
            height: 0,
            borderLeft: '20px solid transparent',
            borderRight: '20px solid transparent',
            borderTop: '24px solid #1E1E1E',
          }}
        />
        <div
          style={{
            position: 'absolute',
            bottom: -13,
            left: tailLeft,
            transform: 'translateX(-50%)',
            width: 0,
            height: 0,
            borderLeft: '14px solid transparent',
            borderRight: '14px solid transparent',
            borderTop: '18px solid #FFFFFF',
          }}
        />
      </div>
    </div>
  );
};
