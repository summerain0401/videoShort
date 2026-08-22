// 常用常量

export const VIDEO_WIDTH = 1080;
export const VIDEO_HEIGHT = 1920;
export const FPS = 30;

/**
 * 统一安全区：竖屏视频在不同机型（19.5:9 / 20:9 / 21:9）全屏播放时，
 * 上下会被裁切 10.9%~15.6%，另有刘海/圆角/手势条遮挡。
 * 所有关键内容（字幕/角色/道具/徽章）必须约束在安全区内。
 * 内容可视区 = [SAFE_AREA.top, VIDEO_HEIGHT - SAFE_AREA.bottom]
 *
 * 节点5「安全区上抬」：底部安全区从 220px(11.5%) 上抬到 350px(18.2%)，
 * 覆盖全机型最坏裁切 15.6% + 手势条余量（落在 15-20% 区间）；
 * 顶部同步从 180px 上抬到 240px(12.5%)，避免片头标题在 19.5:9 机型被裁。
 */
export const SAFE_AREA = {
  /** 顶部安全区（刘海/状态栏遮挡） */
  top: 240,
  /** 底部安全区（手势条遮挡；节点5 上抬至 18.2%） */
  bottom: 350,
  /** 左右安全区（圆角/裁切） */
  side: 64,
} as const;

/** 角色站立高度：底部安全区上沿 + 150px，保证角色脚底不被上抬后的字幕条遮挡 */
export const CHARACTER_BOTTOM = SAFE_AREA.bottom + 150;

/** 字幕安全区（兼容旧引用）：字幕条底部不得低于此高度 */
export const SUBTITLE_SAFE_ZONE = SAFE_AREA.bottom;

/** 画面侧边留白（兼容旧引用），防止道具贴边 */
export const EDGE_MARGIN = SAFE_AREA.side;

/** 动画时长（秒） */
export const ENTER_ANIM_DURATION = 0.5;
export const EXIT_ANIM_DURATION = 0.4;

/** 中文解说参考语速（字/秒），用于没有精确对齐时的估算 */
export const ZH_SPEECH_RATE = 4.5;

/** 片头标题显示时长（秒）—— 已废弃（片头直入正文，标题改悬浮贴纸），保留兼容 */
export const INTRO_DURATION = 3.0;
/** 片尾黑板停留时长（秒） */
export const OUTRO_DURATION = 5.0;
/**
 * 场景切换交叉溶解时长（秒）：
 * 相邻场景重叠渲染、opacity 交叉渐变，替代全屏白闪/曝光转场，
 * 避免移动端夜间观看刺眼。首尾淡出淡入区间 = CROSS_DISSOLVE。
 */
export const CROSS_DISSOLVE = 0.22;

/**
 * 根背景兜底色（治愈暖奶白）：
 * 场景淡入淡出/序列衔接的间隙会透出该色，避免透出纯黑造成黑帧。
 * 全片任何一帧的亮度都高于 blackdetect 阈值，黑帧检测永不误报。
 */
export const ROOT_BACKGROUND = '#FFF8EE';
