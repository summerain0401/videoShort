// 主合成组件 —— 第 0 秒直入正文 Hook，标题悬浮贴纸，场景交叉溶解转场

import React from 'react';
import {AbsoluteFill, Audio, Sequence, useVideoConfig} from 'remotion';
import {HookTitle} from './components/HookTitle';
import {NarrationScene} from './scenes/NarrationScene';
import {OutroScene} from './scenes/OutroScene';
import {CROSS_DISSOLVE, OUTRO_DURATION, ROOT_BACKGROUND} from './lib/constants';
import {staticPath} from './lib/staticPath';
import type {OutroData, Timeline} from './lib/types';

export interface MainCompositionProps {
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
  outro?: OutroData;
  /** 背景音乐/音效路径（可选） */
  bgmPath?: string;
  /** 旁白音频路径（可选，有则自动对齐时间轴） */
  narrationPath?: string;
}

/**
 * 完整视频合成（节点：转场白闪修复 + 片头直入）：
 * - 第 0 秒直接是正文首个场景（人物动态画面），标题以 HookTitle 悬浮贴纸浮在上方
 * - 相邻正文场景 Sequence 重叠 CROSS_DISSOLVE 秒，opacity 交叉溶解（不再露根背景闪白）
 * - 片尾提前 CROSS_DISSOLVE 秒开始，与最后一个正文场景交叉过渡
 * - 旁白音频从起点播放
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
  const crossFrames = Math.round(CROSS_DISSOLVE * fps);

  return (
    <AbsoluteFill style={{backgroundColor: ROOT_BACKGROUND}}>
      {/* 正文场景：第 0 秒直接开播；场景间交叉溶解 */}
      <Sequence from={0}>
        <AbsoluteFill>
          {timeline.scenes.map((scene, i) => {
            const sceneStart = i === 0 ? 0 : scene.start;
            // 场景 i 渲染区间 [start_i - cross, end_i]：开始提前 cross 秒做淡入，与上一场景尾部重叠
            const fromFrame = i === 0 ? 0 : Math.max(0, Math.round(sceneStart * fps) - crossFrames);
            const durationFrames = Math.max(
              1,
              Math.round((scene.end - sceneStart) * fps + crossFrames),
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
                  fadeIn={i > 0}
                  fadeOut={i < timeline.scenes.length - 1}
                />
              </Sequence>
            );
          })}

          {/* 悬浮标题贴纸（替代静态片头卡）：0~2.6s 浮在画面上方，弹入+呼吸浮动+淡出 */}
          <Sequence from={0} durationInFrames={Math.round(2.6 * fps)} name="HookTitle">
            <HookTitle title={timeline.title} />
          </Sequence>

          {/* 旁白音频：从起点播放 */}
          {narrationPath ? (
            <Audio src={staticPath(narrationPath)} />
          ) : null}

          {/* 背景音乐：音量压低 */}
          {bgmPath ? (
            <Audio src={staticPath(bgmPath)} volume={0.15} />
          ) : null}
        </AbsoluteFill>
      </Sequence>

      {/* 片尾：提前 cross 秒开始，与正文最后场景交叉溶解 */}
      <Sequence
        from={Math.max(0, Math.round(timeline.totalDuration * fps) - crossFrames)}
        durationInFrames={Math.round(OUTRO_DURATION * fps) + crossFrames}
      >
        <OutroScene
          question={outro.question}
          answer={outro.answer}
          characterImage={outro.characterImage}
          characterImageHappy={outro.characterImageHappy}
        />
      </Sequence>
    </AbsoluteFill>
  );
};
