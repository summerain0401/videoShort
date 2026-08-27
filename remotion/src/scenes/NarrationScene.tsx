// 正文场景 —— 背景 + 角色 + 道具 + 对话气泡 + 涂鸦图表 + 字幕的融合画面

import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Character} from '../components/Character';
import {Prop} from '../components/Prop';
import {Subtitle} from '../components/Subtitle';
import {InfoOverlay} from '../components/InfoOverlay';
import {DialogueBubble} from '../components/DialogueBubble';
import {Infographics} from '../components/Infographics';
import {AmbientBokeh} from '../components/effects/AmbientBokeh';
import {GlowOrb} from '../components/effects/GlowOrb';
import {EASE, kenBurnsScale, kenBurnsTranslate} from '../lib/animations';
import {CROSS_DISSOLVE, SAFE_AREA} from '../lib/constants';
import {staticPath} from '../lib/staticPath';
import type {TimelineScene} from '../lib/types';

interface NarrationSceneProps {
  scene: TimelineScene;
  backgroundPath?: string;
  resolveSceneBackground?: (sceneId: string) => string | null;
  resolveElementImage?: (el: {
    type: 'character' | 'prop';
    name: string;
    emotion?: string;
  }) => string | null;
  fadeIn?: boolean;
  fadeOut?: boolean;
}

export const NarrationScene: React.FC<NarrationSceneProps> = ({
  scene,
  backgroundPath,
  resolveSceneBackground,
  resolveElementImage,
  fadeIn = false,
  fadeOut = false,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const bgPath =
    scene.backgroundPath ?? backgroundPath ?? resolveSceneBackground?.(scene.sceneId) ?? undefined;

  const sceneDurationSeconds = scene.end - scene.start;
  const sceneDurationFrames = Math.max(1, Math.round(sceneDurationSeconds * fps));

  const fadeInFrames = (fadeIn ? CROSS_DISSOLVE : 0) * fps;
  const fadeOutFrames = (fadeOut ? CROSS_DISSOLVE : 0) * fps;

  let sceneOpacity = 1;
  if (sceneDurationFrames > 2) {
    const fadeInOpacity =
      fadeIn && fadeInFrames > 0
        ? interpolate(frame, [0, Math.min(sceneDurationFrames, fadeInFrames)], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: EASE.out,
          })
        : 1;
    const fadeOutOpacity =
      fadeOut && fadeOutFrames > 0
        ? interpolate(
            frame,
            [Math.max(0, sceneDurationFrames - fadeOutFrames), sceneDurationFrames],
            [1, 0],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out},
          )
        : 1;
    sceneOpacity = Math.min(fadeInOpacity, fadeOutOpacity);
  }

  // 场景整体轻微缩放入场
  const sceneScale = interpolate(
    frame,
    [0, fps * 0.35],
    [1.02, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out},
  );

  const characters = scene.elements.filter((e) => e.type === 'character');
  const props = scene.elements.filter((e) => e.type === 'prop');

  const sceneRelativeDuration: [number, number] = [0, sceneDurationSeconds];
  const highlights = scene.subtitle.highlights ?? [];

  const sceneNum = parseInt(scene.sceneId.replace(/\D/g, ''), 10) || 1;
  const shotIdx = scene.shotIndex ?? sceneNum - 1;
  const kenBurnsProgress = frame / sceneDurationFrames;
  const zoomIn = shotIdx % 2 === 0;
  const bgScale = kenBurnsScale(kenBurnsProgress, {
    from: zoomIn ? 1 : 1.08,
    to: zoomIn ? 1.08 : 1,
  });

  const panDirections: Array<{x: [number, number]; y: [number, number]}> = [
    {x: [0, 10], y: [0, -6]},
    {x: [0, -8], y: [0, 8]},
    {x: [0, 6], y: [0, 10]},
    {x: [0, -8], y: [0, -6]},
  ];
  const dir = panDirections[shotIdx % panDirections.length];
  const bgTranslateX = kenBurnsTranslate(kenBurnsProgress, dir.x);
  const bgTranslateY = kenBurnsTranslate(kenBurnsProgress, dir.y);

  const orbColors = ['#ffd93d', '#ffb36b', '#fff3c4', '#ff8a3d'];
  const orbColor = orbColors[(sceneNum - 1) % orbColors.length];

  return (
    <AbsoluteFill
      style={{
        opacity: sceneOpacity,
        transform: `scale(${sceneScale})`,
      }}
    >
      {/* 背景层（Ken Burns 缓慢推拉） */}
      {bgPath ? (
        <Img
          src={staticPath(bgPath)}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${bgScale}) translate(${bgTranslateX}px, ${bgTranslateY}px)`,
            transformOrigin: 'center center',
          }}
        />
      ) : (
        <AbsoluteFill style={{backgroundColor: '#FFFDF0'}} />
      )}

      {/* 背景装饰特效：柔光球 + 光斑 */}
      <GlowOrb color={orbColor} size={560} top="30%" left="50%" opacity={0.16} amp={14} />
      <AmbientBokeh count={8} opacity={0.12} sizeRange={[40, 140]} />

      {/* 暖色渐变遮罩 */}
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(40, 20, 5, 0.18) 0%, rgba(40, 20, 5, 0) 20%, rgba(40, 20, 5, 0) 58%, rgba(40, 20, 5, 0.42) 100%)',
        }}
      />

      {/* 角色层：双人站位 + 发言人判定 + 经典表情特效 */}
      {characters.map((el, i) => {
        const img = el.imagePath ?? resolveElementImage?.(el);
        if (!img) {
          return null;
        }
        const charPosition =
          el.position ??
          (characters.length === 1 && props.length === 0
            ? 'center'
            : characters.length === 1
              ? 'left'
              : (i % 2 === 0 ? 'left' : 'right'));

        const isSpeaker =
          el.isSpeaker ??
          (scene.speaker ? el.name === scene.speaker : true);

        const effect =
          el.effect ??
          (el.name === scene.speaker ? scene.characterEffect : 'none');

        return (
          <Character
            key={`${el.name}-${i}`}
            imagePath={img}
            enterFrom={el.enterFrom ?? 'none'}
            duration={sceneRelativeDuration}
            position={charPosition}
            zIndex={el.zIndex ?? 2}
            isSpeaker={isSpeaker}
            effect={effect}
            floating
          />
        );
      })}

      {/* 道具层 */}
      {props.map((el, i) => {
        const img = el.imagePath ?? resolveElementImage?.(el);
        if (!img) {
          return null;
        }
        const propPosition =
          el.position ??
          (props.length === 1 && characters.length === 0
            ? 'center'
            : props.length === 1
              ? 'right'
              : (i % 2 === 0 ? 'right' : 'left'));

        const scale =
          el.name === '巧克比' ? 0.24 :
          el.name === '第二件半价牌' ? 0.22 :
          el.name === '工资条' ? 0.20 :
          0.22;

        return (
          <Prop
            key={`${el.name}-${i}`}
            imagePath={img}
            enterFrom={el.enterFrom ?? 'right'}
            duration={[sceneRelativeDuration[0] + 0.2, sceneRelativeDuration[1]]}
            position={propPosition}
            scale={scale}
            zIndex={el.zIndex ?? 3}
          />
        );
      })}

      {/* 2.0 涂鸦风动态图表层（天平/柱状图/跳字计数器） */}
      {scene.infographic ? (
        <Infographics data={scene.infographic} start={0.2} />
      ) : null}

      {/* 2.0 漫画对话气泡（有 speaker 且非图表时优先展示气泡） */}
      {scene.dialogueBubble ? (
        <DialogueBubble
          speaker={scene.dialogueBubble.speaker}
          text={scene.dialogueBubble.text}
          side={scene.dialogueBubble.side}
          start={0.1}
        />
      ) : scene.speaker && !scene.infographic && (scene.overlays?.length ?? 0) === 0 ? (
        <DialogueBubble
          speaker={scene.speaker}
          text={scene.subtitle.text}
          side={characters.findIndex((c) => c.name === scene.speaker) === 1 ? 'right' : 'left'}
          start={0.1}
        />
      ) : null}

      {/* 动态视觉图层（纯文本子模板：价格标签/算式/对比卡） */}
      {(scene.overlays ?? []).map((ov, i) => (
        <InfoOverlay key={i} kind={ov.kind} text={ov.text} title={ov.title} position={ov.position} />
      ))}

      {/* 底部字幕层 */}
      <Subtitle
        text={scene.subtitle.text}
        start={scene.subtitle.start - scene.start}
        end={scene.subtitle.end - scene.start}
        highlights={highlights}
        segments={scene.subtitle.segments?.map((s) => ({
          text: s.text,
          start: s.start - scene.start,
          end: s.end - scene.start,
        }))}
      />
    </AbsoluteFill>
  );
};

