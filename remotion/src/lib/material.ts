// 素材检索工具 —— 在共享素材库中查找素材文件

import {staticFile} from 'remotion';
import type {SceneElement} from './types';

// Remotion 中通过 staticFile() 引用公共目录下的文件。
// 约定：项目根目录的 shared/ 软链到 public/，或者用 import.meta.url 引用相对文件。

/**
 * 解析素材路径：
 * 优先使用项目相对路径，其次尝试共享素材库。
 * 在 Remotion 中，放在 public/ 目录下的文件可通过 staticFile() 访问。
 */
export function resolveAssetPath(filePath: string): string | null {
  // 支持两种形式：
  // 1. 已经是 staticFile 形式: /shared/characters/xxx.png
  // 2. 项目相对路径: shared/characters/xxx.png
  try {
    const normalized = filePath.startsWith('/') ? filePath : `/${filePath}`;
    return staticFile(normalized);
  } catch {
    return null;
  }
}

/**
 * 根据场景元素查找对应素材。
 * 约定命名：shared/{characters|props}/{name}_{emotion|action}_{id}.png
 * 由于素材命名由 register-material.py 控制，这里提供宽松匹配：
 * 查找文件名包含角色名+情绪的文件。
 */
export async function findMaterialFile(
  element: SceneElement,
): Promise<string | null> {
  const {name, emotion} = element;
  const type = element.type === 'character' ? 'characters' : 'props';

  // 简化实现：直接尝试常见命名
  const candidates = [
    `${name}_${emotion ?? 'default'}`,
    name,
  ];

  for (const c of candidates) {
    // 尝试通过 public/shared 目录匹配
    const viaStatic = resolveAssetPath(`shared/${type}/${c}.png`);
    if (viaStatic) {
      // staticFile 不校验存在性，这里用 fetch HEAD 太贵，直接返回供组件用 onError 兜底
      return viaStatic;
    }
  }
  return null;
}
