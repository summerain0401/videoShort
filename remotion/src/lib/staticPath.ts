// 静态资源路径工具
// Remotion 4 中渲染/Studio 的静态文件统一通过 staticFile() 访问，
// 它会自动加上 /public 基路径（remotion_staticBase）。
// 数据层路径可能带前导 "/"（如 /shared/backgrounds/bg_town.png），
// staticFile() 内部会去掉前导斜杠，所以这里统一转发即可。

import {staticFile} from 'remotion';

export const staticPath = (p?: string | null): string | undefined => {
  if (!p) {
    return undefined;
  }
  return staticFile(p);
};
