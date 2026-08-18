// 视频数据类型定义 —— 与 scripts/ 生成的 JSON 对齐

export type ElementType = "character" | "prop";

export interface SceneElement {
  type: ElementType;
  name: string;
  emotion?: string;
  enterFrom?: "left" | "right" | "top" | "bottom" | "none";
  /** 画面位置: left | right | center（可选，默认按 index 交替） */
  position?: "left" | "right" | "center";
  zIndex: number;
  /** [start, end] 秒 */
  duration: [number, number];
  /** 渲染脚本解析后的素材路径（相对 public/） */
  imagePath?: string;
}

export interface TimelineScene {
  sceneId: string;
  /** 秒 */
  start: number;
  /** 秒 */
  end: number;
  subtitle: {
    text: string;
    start: number;
    end: number;
    /** 关键词高亮（由场景配置指定，WorkBuddy 产稿时填入） */
    highlights?: string[];
  };
  elements: SceneElement[];
  /** 场景配置指定的背景名（可选，未指定时按序号默认） */
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
