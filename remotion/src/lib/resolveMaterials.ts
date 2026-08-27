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

/** 场景背景解析：sceneId/bgName → 背景图路径 */
export function resolveSceneBackground(
  lib: Library,
  sceneIdOrName: string,
): string | null {
  // 如果直接是背景名
  const directMatch = findActiveMaterial(lib, 'background', sceneIdOrName);
  if (directMatch) {
    return directMatch;
  }
  // 蜡笔小新默认场景映射
  if (sceneIdOrName === '春日部超市' || sceneIdOrName === '超市内部') {
    return findActiveMaterial(lib, 'background', '春日部超市') || findActiveMaterial(lib, 'background', '超市内部');
  }
  if (sceneIdOrName === '野原家客厅' || sceneIdOrName === '温馨客厅') {
    return findActiveMaterial(lib, 'background', '野原家客厅') || findActiveMaterial(lib, 'background', '温馨客厅');
  }
  const num = parseInt(sceneIdOrName.replace(/\D/g, ''), 10) || 1;
  const defaultBg = num <= 2 ? '春日部街道' : '春日部超市';
  return findActiveMaterial(lib, 'background', defaultBg) || findActiveMaterial(lib, 'background', '小镇街道');
}

/** 元素素材解析：character/prop → 图片路径 */
export function resolveElementImage(
  lib: Library,
  el: {type: 'character' | 'prop'; name: string; emotion?: string},
): string | null {
  return findActiveMaterial(lib, el.type, el.name, el.emotion);
}
