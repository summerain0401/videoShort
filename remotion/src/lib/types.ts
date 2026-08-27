// 视频数据类型定义 —— 与 scripts/ 生成的 JSON 对齐

export type ElementType = "character" | "prop";

export type CharacterEffectType = "steam" | "sweat" | "shake" | "idea" | "question" | "none";

export interface SceneElement {
  type: ElementType;
  name: string;
  emotion?: string;
  enterFrom?: "left" | "right" | "top" | "bottom" | "none";
  /** 画面位置: left | right | center */
  position?: "left" | "right" | "center";
  zIndex: number;
  /** [start, end] 秒 */
  duration: [number, number];
  /** 渲染脚本解析后的素材路径（相对 public/） */
  imagePath?: string;
  /** 是否为当前正在说话的角色 */
  isSpeaker?: boolean;
  /** 角色头顶/身体表情特效 */
  effect?: CharacterEffectType;
}

/** 动态视觉图层（纯文本子模板） */
export interface InfoOverlayData {
  kind: 'price-tag' | 'equation' | 'vs-card';
  text: string;
  title?: string;
  position?: 'top' | 'center' | 'bottom';
}

/** 2.0 涂鸦风动态图表数据 */
export interface InfographicData {
  kind: 'balance' | 'bar' | 'counter';
  title?: string;
  /** 天平左右文本及倾斜方向 */
  leftLabel?: string;
  rightLabel?: string;
  tilt?: 'left' | 'right' | 'balanced';
  /** 柱状对比图 */
  bars?: Array<{ label: string; value: number; color?: string; unit?: string }>;
  /** 跳字计数器 */
  counter?: { prefix?: string; suffix?: string; from: number; to: number };
}

/** 2.0 漫画对话气泡数据 */
export interface DialogueBubbleData {
  speaker: string;
  side?: 'left' | 'right' | 'center';
  text: string;
}

export interface TimelineScene {
  sceneId: string;
  /** 秒 */
  start: number;
  /** 秒 */
  end: number;
  /** 当前发言角色（如：小新 / 美伢 / 广志） */
  speaker?: string;
  /** 角色特效（如：冒蒸汽/大汗/震惊抖动/灯泡） */
  characterEffect?: CharacterEffectType;
  /** 2.0 动态图表组件 */
  infographic?: InfographicData;
  /** 2.0 漫画对话气泡 */
  dialogueBubble?: DialogueBubbleData;
  subtitle: {
    text: string;
    start: number;
    end: number;
    /** 关键词高亮 */
    highlights?: string[];
    /** 断句段，每段按字数比例分配展示时间 */
    segments?: Array<{text: string; start: number; end: number}>;
  };
  elements: SceneElement[];
  /** 动态视觉图层（价格标签/算式/对比卡，纯文本渲染） */
  overlays?: InfoOverlayData[];
  /** 镜头序号 */
  shotIndex?: number;
  /** 场景配置指定的背景名 */
  backgroundName?: string;
  /** 渲染脚本解析后的背景路径（相对 public/） */
  backgroundPath?: string;
}

export interface Timeline {
  videoId: string;
  title: string;
  totalDuration: number;
  audioFile?: string;
  scenes: TimelineScene[];
}

/** 片尾问答数据（data/outro.json） */
export interface OutroData {
  question: string;
  answer: string;
  character?: string;
  characterImage?: string;
  characterImageHappy?: string;
  companionImage?: string;
}

