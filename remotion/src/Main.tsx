// 主合成组件 —— 按时间轴渲染 片头 + 正文场景 + 片尾

import React from 'react';
import {AbsoluteFill, Audio, Sequence, useVideoConfig} from 'remotion';
import {IntroScene} from './scenes/IntroScene';
import {NarrationScene} from './scenes/NarrationScene';
import {OutroScene} from './scenes/OutroScene';
import {INTRO_DURATION} from './lib/constants';
import {staticPath} from './lib/staticPath';
import type {Timeline} from './lib/types';

interface MainCompositionProps {
  timeline: Timeline;
  /** 背景素材解析: (sceneId) => string | null */
  resolveSceneBackground?: (sceneId: string) => string | null;
  /** 元素素材解析: (el) => string | null */
  resolveElementImage?: (el: {
    type: 'character' | 'prop';
    name: string;
    emotion?: string;
  }) => string | null;
  /** 片尾问答 */
  outro?: {question: string; answer: string};
  /** 背景音乐/音效路径（可选） */
  bgmPath?: string;
  /** 旁白音频路径（可选，有则自动对齐时间轴） */
  narrationPath?: string;
}

/**
 * 完整视频合成：
 * - Sequence 0 → 片头
 * - 之后 → 正文场景（按 timeline.scenes）
 * - 最后 → 片尾
 * - 旁白音频从正文 Sequence 起点开始播放
 *
 * 注意：嵌套 Sequence 的 from 是相对父 Sequence 的起始帧。
 */
export const MainComposition: React.FC<MainCompositionProps> = ({
  timeline,
  resolveSceneBackground,
  resolveElementImage,
  outro = {question: '你学会了吗？', answer: '下次见！'},
  bgmPath,
  narrationPath,
}) => {
  const {fps} = useVideoConfig();
  const introFrames = INTRO_DURATION * fps;

  // 正文从片头结束后开始
  const bodyStartFrame = introFrames;

  return (
    <AbsoluteFill style={{backgroundColor: '#000000'}}>
      {/* 片头 */}
      <Sequence from={0} durationInFrames={introFrames}>
        <IntroScene title={timeline.title} />
      </Sequence>

      {/* 正文场景：from=bodyStartFrame 相对于合成；子 Sequence from 相对于正文 */}
      <Sequence from={bodyStartFrame}>
        <AbsoluteFill>
          {timeline.scenes.map((scene) => {
            const fromFrame = scene.start * fps;
            const durationFrames = Math.max(
              1,
              Math.round((scene.end - scene.start) * fps),
            );
            return (
              <Sequence
                key={scene.sceneId}
                from={fromFrame}
                durationInFrames={durationFrames}
                name={scene.sceneId}
              >
                <NarrationScene
                  scene={scene}
                  backgroundPath={resolveSceneBackground?.(scene.sceneId) ?? undefined}
                  resolveElementImage={resolveElementImage}
                />
              </Sequence>
            );
          })}

          {/* 旁白音频：从正文 Sequence 起点播放 */}
          {narrationPath ? (
            <Audio src={staticPath(narrationPath)} />
          ) : null}

          {/* 背景音乐：音量压低 */}
          {bgmPath ? (
            <Audio src={staticPath(bgmPath)} volume={0.15} />
          ) : null}
        </AbsoluteFill>
      </Sequence>

      {/* 片尾 */}
      <Sequence from={bodyStartFrame + Math.round(timeline.totalDuration * fps)}>
        <OutroScene question={outro.question} answer={outro.answer} />
      </Sequence>
    </AbsoluteFill>
  );
};
