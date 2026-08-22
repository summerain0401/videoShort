// 根组件 —— 注册 composition，接收渲染脚本传入的 inputProps
//
// 重要：registerRoot 注册的组件本身不会直接收到外部 inputProps。
// 程序化渲染时，inputProps 通过 getInputProps() 读取；
// Studio 预览时若无 inputProps 则使用默认值。

import React from 'react';
import {Composition, getInputProps} from 'remotion';
import {MainComposition} from './Main';
import {CROSS_DISSOLVE, FPS, VIDEO_HEIGHT, VIDEO_WIDTH} from './lib/constants';
import {resolveElementImage, resolveSceneBackground} from './lib/resolveMaterials';
import type {OutroData, Timeline} from './lib/types';
import type {Library} from './lib/resolveMaterials';
import TestImg from './TestImg';

interface RootInputProps {
  timeline?: Timeline;
  /** 素材库（可选；若 scene/element 未自带路径则兜底解析） */
  library?: Library;
  /** 相对 public/ 的音频路径，如 _audio/voice.mp3 */
  narration?: string;
  /** 片尾问答 */
  outro?: OutroData;
}

const EMPTY_TIMELINE: Timeline = {
  videoId: 'C001',
  title: '示例视频',
  totalDuration: 30,
  scenes: [],
};

export const RemotionRoot: React.FC = () => {
  const inputProps = getInputProps() as RootInputProps;
  const timeline = inputProps.timeline ?? EMPTY_TIMELINE;
  const lib = inputProps.library ?? {characters: [], backgrounds: [], props: []};
  const outro = inputProps.outro ?? {question: '你学会了吗？', answer: '下次见！'};

  const duration = Math.max(
    30,
    // 无静态片头：正文 totalDuration + 片尾 OUTRO_DURATION（片尾提前 CROSS_DISSOLVE 开始，故 +cross 帧余量）
    Math.ceil(((timeline.totalDuration ?? 30) + 5) * FPS) + Math.round(CROSS_DISSOLVE * FPS),
  );

  return (
    <>
      <Composition
        id="TestImg"
        component={TestImg}
        durationInFrames={30}
        fps={FPS}
        width={VIDEO_WIDTH}
        height={VIDEO_HEIGHT}
      />
      <Composition
        id="Main"
        component={MainComposition as unknown as React.FC<Record<string, unknown>>}
        durationInFrames={duration}
        fps={FPS}
        width={VIDEO_WIDTH}
        height={VIDEO_HEIGHT}
        defaultProps={{
          timeline,
          resolveSceneBackground: (sceneId: string) =>
            resolveSceneBackground(lib, sceneId),
          resolveElementImage: (el: {
            type: 'character' | 'prop';
            name: string;
            emotion?: string;
          }) => resolveElementImage(lib, el),
          narrationPath: inputProps.narration,
          outro,
        }}
      />
    </>
  );
};
