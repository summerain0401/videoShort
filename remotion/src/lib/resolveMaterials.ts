// 素材解析器（纯函数版）—— 从传入的素材库数据按名称检索路径
// 素材库数据由 Node 端渲染脚本从 material-library.json 读取后传入，浏览器端不做文件 IO。

export interface LibItem {
  id: string;
  type: 'character' | 'background' | 'prop';
  name: string;
  emotion?: string;
  filePath: string;
  status: string;
}

export interface Library {
  characters: LibItem[];
  backgrounds: LibItem[];
  props: LibItem[];
}

/** 按名称+类型检索 active 素材，返回可直接用于 <Img src> 的路径（相对 public/） */
export function findActiveMaterial(
  lib: Library,
  type: 'character' | 'background' | 'prop',
  name: string,
  emotion?: string,
): string | null {
  const category =
    type === 'background'
      ? lib.backgrounds
      : type === 'character'
        ? lib.characters
        : lib.props;
  const matches = category.filter((i) => i.status === 'active' && i.name === name);
  if (matches.length === 0) {
    return null;
  }
  if (emotion) {
    const byEmotion = matches.find((i) => i.emotion === emotion);
    if (byEmotion) {
      return `/${byEmotion.filePath}`;
    }
  }
  return `/${matches[0].filePath}`;
}

/** 场景背景解析：sceneId → 背景图路径（骨架版本：S01/S02 小镇街道，其余超市内部） */
export function resolveSceneBackground(
  lib: Library,
  sceneId: string,
): string | null {
  const num = parseInt(sceneId.replace(/\D/g, ''), 10) || 1;
  const bgName = num <= 2 ? '小镇街道' : '超市内部';
  return findActiveMaterial(lib, 'background', bgName);
}

/** 元素素材解析：character/prop → 图片路径 */
export function resolveElementImage(
  lib: Library,
  el: {type: 'character' | 'prop'; name: string; emotion?: string},
): string | null {
  return findActiveMaterial(lib, el.type, el.name, el.emotion);
}
