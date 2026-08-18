// 正文场景 —— 背景 + 角色 + 道具 + 字幕的融合画面

import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Character} from '../components/Character';
import {Prop} from '../components/Prop';
import {Subtitle} from '../components/Subtitle';
import {EDGE_MARGIN} from '../lib/constants';
import {staticPath} from '../lib/staticPath';
import type {TimelineScene} from '../lib/types';

interface NarrationSceneProps {
  scene: TimelineScene;
  /** 素材路径解析器（兜底/兼容，优先使用 scene.backgroundPath 和 element.imagePath） */
  resolveSceneBackground?: (sceneId: string) => string | null;
  resolveElementImage?: (el: {
    type: 'character' | 'prop';
    name: string;
    emotion?: string;
  }) => string | null;
}

/**
 * 正文场景（左右构图为主）：
 * - 背景层：图片或纯色
 * - 角色层：人物占一边
 * - 道具层：道具放另一边
 * - 字幕层：底部安全区
 */
export const NarrationScene: React.FC<NarrationSceneProps> = ({
  scene,
  resolveSceneBackground,
  resolveElementImage,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const backgroundPath = scene.backgroundPath ?? resolveSceneBackground?.(scene.sceneId) ?? undefined;

  // 场景淡入淡出（frame 是场景 Sequence 内的相对帧）
  const sceneDurationSeconds = scene.end - scene.start;
  const sceneDurationFrames = Math.max(1, Math.round(sceneDurationSeconds * fps));

  // 场景淡入淡出
  const sceneOpacity = interpolate(
    frame,
    [0, fps * 0.2, sceneDurationFrames - fps * 0.2, sceneDurationFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // 场景整体轻微缩放入场：1.02 -> 1.0，配合透明度更有层次
  const sceneScale = interpolate(
    frame,
    [0, fps * 0.35],
    [1.02, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // 竖屏布局决策：角色居中偏下，道具居中偏上；多个元素时按索引左右分布
  const characters = scene.elements.filter((e) => e.type === 'character');
  const props = scene.elements.filter((e) => e.type === 'prop');

  // 元素动画使用相对当前场景的秒数
  const sceneRelativeDuration: [number, number] = [0, sceneDurationSeconds];

  // 每句字幕的关键词高亮（数据源：scene-config.json 的 subtitle.highlights）
  const highlights = scene.subtitle.highlights ?? [];

  // Ken Burns 镜头运动：按 sceneId 决定方向，避免所有场景同向单调
  const sceneNum = parseInt(scene.sceneId.replace(/\D/g, ''), 10) || 1;
  const kenBurnsProgress = frame / sceneDurationFrames;
  const bgScale = interpolate(kenBurnsProgress, [0, 1], [1, 1.06], {extrapolateRight: 'clamp'});
  // 竖屏较窄，位移幅度减小，避免背景晃动过强
  const panDirections = [
    {x: [0, 12], y: [0, -8]},
    {x: [0, -10], y: [0, 10]},
    {x: [0, 8], y: [0, 12]},
    {x: [0, -10], y: [0, -8]},
    {x: [0, 12], y: [0, 6]},
  ];
  const dir = panDirections[(sceneNum - 1) % panDirections.length];
  const bgTranslateX = interpolate(kenBurnsProgress, [0, 1], dir.x, {extrapolateRight: 'clamp'});
  const bgTranslateY = interpolate(kenBurnsProgress, [0, 1], dir.y, {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill
      style={{
        opacity: sceneOpacity,
        transform: `scale(${sceneScale})`,
      }}
    >
      {/* 背景层（Ken Burns 缓慢推拉） */}
      {backgroundPath ? (
        <Img
          src={staticPath(backgroundPath)}
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
        <AbsoluteFill style={{backgroundColor: '#0e7490'}} />
      )}

      {/* 暖色渐变遮罩：底部压暗保证字幕可读，顶部柔光提亮 */}
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(40, 20, 5, 0.22) 0%, rgba(40, 20, 5, 0) 20%, rgba(40, 20, 5, 0) 58%, rgba(40, 20, 5, 0.46) 100%)',
        }}
      />

      {/* 角色层：第一个角色在左，第二个在右；只有一个角色且无道具时居中 */}
      {characters.map((el, i) => {
        const img = el.imagePath ?? resolveElementImage?.(el);
        if (!img) {
          return null;
        }
        const charPosition = characters.length === 1 && props.length === 0
          ? 'center'
          : characters.length === 1
            ? 'left'
            : (i % 2 === 0 ? 'left' : 'right');
        return (
          <Character
            key={`${el.name}-${i}`}
            imagePath={img}
            enterFrom={el.enterFrom ?? 'none'}
            duration={sceneRelativeDuration}
            position={charPosition}
            zIndex={el.zIndex ?? 2}
            floating
          />
        );
      })}

      {/* 道具层：与角色互补；只有一个道具且无角色时居中，有角色时放右侧 */}
      {props.map((el, i) => {
        const img = el.imagePath ?? resolveElementImage?.(el);
        if (!img) {
          return null;
        }
        const propPosition = props.length === 1 && characters.length === 0
          ? 'center'
          : props.length === 1
            ? 'right'
            : (i % 2 === 0 ? 'right' : 'left');
        // 竖屏道具比例：高度相对 VIDEO_HEIGHT，单个居中在上，多个左右分布
        const scale =
          el.name === '超市货架' ? 0.25 :
          el.name === '工资条' ? 0.18 :
          el.name === '零食袋' ? 0.23 :
          el.name === '饮料瓶' ? 0.16 :
          0.22;
        return (
          <Prop
            key={`${el.name}-${i}`}
            imagePath={img}
            enterFrom={el.enterFrom ?? 'right'}
            duration={[sceneRelativeDuration[0] + 0.3, sceneRelativeDuration[1]]}
            position={propPosition}
            scale={scale}
            zIndex={el.zIndex ?? 3}
          />
        );
      })}

      {/* 字幕层：subtitle 时间轴是全局秒数，但 useCurrentFrame 返回场景内相对帧，需要减去 scene.start */}
      <Subtitle
        text={scene.subtitle.text}
        start={scene.subtitle.start - scene.start}
        end={scene.subtitle.end - scene.start}
        highlights={highlights}
      />

      {/* 边缘安全线（极淡，几乎不可见） */}
      <div
        style={{
          position: 'absolute',
          left: EDGE_MARGIN,
          right: EDGE_MARGIN,
          top: 0,
          bottom: 0,
          borderLeft: '1px dashed rgba(255,255,255,0.04)',
          borderRight: '1px dashed rgba(255,255,255,0.04)',
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  );
};
