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

/** 动态视觉图层（节点3：数字/对比语句触发的纯文本子模板） */
export interface InfoOverlayData {
  kind: 'price-tag' | 'equation' | 'vs-card';
  text: string;
  title?: string;
  position?: 'top' | 'center' | 'bottom';
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
    /** 节点5：6~10 字断句段（可选，由 build-timeline 生成），每段按字数比例分配展示时间 */
    segments?: Array<{text: string; start: number; end: number}>;
  };
  elements: SceneElement[];
  /** 动态视觉图层（价格标签/算式/对比卡，纯文本渲染） */
  overlays?: InfoOverlayData[];
  /** 镜头序号（分镜细分后递增，渲染端据此差异化 Ken Burns 方向） */
  shotIndex?: number;
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

/** 片尾问答数据（data/outro.json，渲染脚本会补充角色素材路径） */
export interface OutroData {
  question: string;
  answer: string;
  /** 角色名（可选，渲染脚本兜底为「小布丁」） */
  character?: string;
  /** 提问阶段角色图片路径（渲染脚本解析，相对 public/） */
  characterImage?: string;
  /** 答案揭晓阶段角色图片路径（渲染脚本解析，相对 public/） */
  characterImageHappy?: string;
}
