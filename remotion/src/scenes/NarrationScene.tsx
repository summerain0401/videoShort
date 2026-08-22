// 正文场景 —— 背景 + 角色 + 道具 + 字幕的融合画面

import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Character} from '../components/Character';
import {Prop} from '../components/Prop';
import {Subtitle} from '../components/Subtitle';
import {InfoOverlay} from '../components/InfoOverlay';
import {AmbientBokeh} from '../components/effects/AmbientBokeh';
import {GlowOrb} from '../components/effects/GlowOrb';
import {EASE, kenBurnsScale, kenBurnsTranslate} from '../lib/animations';
import {CROSS_DISSOLVE, SAFE_AREA} from '../lib/constants';
import {staticPath} from '../lib/staticPath';
import type {TimelineScene} from '../lib/types';

interface NarrationSceneProps {
  scene: TimelineScene;
  /** 已解析的背景路径（由上层传入，优先于 scene.backgroundPath） */
  backgroundPath?: string;
  /** 素材路径解析器（兜底/兼容，优先使用 scene.backgroundPath 和 element.imagePath） */
  resolveSceneBackground?: (sceneId: string) => string | null;
  resolveElementImage?: (el: {
    type: 'character' | 'prop';
    name: string;
    emotion?: string;
  }) => string | null;
  /**
   * 场景切换交叉溶解（节点：转场白闪修复）：
   * 相邻场景 Sequence 重叠 CROSS_DISSOLVE 秒，opacity 交叉渐变，
   * 不再整场景淡出到根背景（旧实现导致全屏白闪/曝光）。
   */
  fadeIn?: boolean;
  fadeOut?: boolean;
}

/**
 * 正文场景（左右构图为主）：
 * - 背景层：图片或纯色 + 光斑/柔光球装饰
 * - 角色层：人物占一边
 * - 道具层：道具放另一边
 * - 字幕层：底部安全区
 */
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

  // 场景淡入淡出（交叉溶解，不整场景淡出到根背景避免白闪）：
  // fadeIn 场景在前 CROSS_DISSOLVE 秒 0→1（与上一场景尾部淡出重叠），
  // fadeOut 场景在后 CROSS_DISSOLVE 秒 1→0（与下一场景头部淡入重叠）。
  const sceneDurationSeconds = scene.end - scene.start;
  const sceneDurationFrames = Math.max(1, Math.round(sceneDurationSeconds * fps));

  const fadeInFrames = (fadeIn ? CROSS_DISSOLVE : 0) * fps;
  const fadeOutFrames = (fadeOut ? CROSS_DISSOLVE : 0) * fps;

  // 场景淡入淡出（缓动曲线）：中间主体恒为 1，仅重叠区渐变
  const sceneOpacity = interpolate(
    frame,
    [
      0,
      Math.max(0, fadeInFrames),
      Math.min(sceneDurationFrames, sceneDurationFrames - Math.max(0, fadeOutFrames)),
      sceneDurationFrames,
    ],
    [fadeIn ? 0 : 1, 1, 1, fadeOut ? 0 : 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out},
  );

  // 场景整体轻微缩放入场：1.02 -> 1.0（缓动）
  const sceneScale = interpolate(
    frame,
    [0, fps * 0.35],
    [1.02, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE.out},
  );

  // 竖屏布局决策：角色居中偏下，道具居中偏上；多个元素时按索引左右分布
  const characters = scene.elements.filter((e) => e.type === 'character');
  const props = scene.elements.filter((e) => e.type === 'prop');

  // 元素动画使用相对当前场景的秒数
  const sceneRelativeDuration: [number, number] = [0, sceneDurationSeconds];

  // 每句字幕的关键词高亮（数据源：scene-config.json 的 subtitle.highlights）
  const highlights = scene.subtitle.highlights ?? [];

  // Ken Burns 镜头运动（easeInOut）：按 shotIndex 决定方向与推拉模式，避免同向单调
  // shotIndex 由 build-timeline 分镜细分后递增（节点3），不同镜头方向/缩放交替
  const sceneNum = parseInt(scene.sceneId.replace(/\D/g, ''), 10) || 1;
  const shotIdx = scene.shotIndex ?? sceneNum - 1;
  const kenBurnsProgress = frame / sceneDurationFrames;
  // 推拉交替：偶数镜头 zoom-in（1→1.10），奇数镜头 zoom-out（1.10→1）
  const zoomIn = shotIdx % 2 === 0;
  const bgScale = kenBurnsScale(kenBurnsProgress, {
    from: zoomIn ? 1 : 1.1,
    to: zoomIn ? 1.1 : 1,
  });
  // 竖屏较窄，位移幅度减小，避免背景晃动过强；方向按 shotIndex 循环（细分数变多后不重复）
  const panDirections: Array<{x: [number, number]; y: [number, number]}> = [
    {x: [0, 12], y: [0, -8]},
    {x: [0, -10], y: [0, 10]},
    {x: [0, 8], y: [0, 12]},
    {x: [0, -10], y: [0, -8]},
    {x: [0, 12], y: [0, 6]},
    {x: [0, -12], y: [0, -6]},
  ];
  const dir = panDirections[shotIdx % panDirections.length];
  const bgTranslateX = kenBurnsTranslate(kenBurnsProgress, dir.x);
  const bgTranslateY = kenBurnsTranslate(kenBurnsProgress, dir.y);

  // 背景装饰色：按场景号轮换，保持治愈暖色调
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
        <AbsoluteFill style={{backgroundColor: '#0e7490'}} />
      )}

      {/* 背景装饰特效：柔光球 + 光斑（低透明度，不喧宾夺主） */}
      <GlowOrb color={orbColor} size={560} top="30%" left="50%" opacity={0.2} amp={14} />
      <AmbientBokeh count={8} opacity={0.14} sizeRange={[40, 140]} />

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

      {/* 动态视觉图层（节点3）：价格标签/算式/对比卡，纯文本渲染 */}
      {(scene.overlays ?? []).map((ov, i) => (
        <InfoOverlay key={i} kind={ov.kind} text={ov.text} title={ov.title} position={ov.position} />
      ))}

      {/* 字幕层：subtitle 时间轴是全局秒数，但 useCurrentFrame 返回场景内相对帧，需要减去 scene.start */}
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

      {/* 边缘安全线（极淡，几乎不可见） */}
      <div
        style={{
          position: 'absolute',
          left: SAFE_AREA.side,
          right: SAFE_AREA.side,
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
