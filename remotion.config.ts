// Remotion 配置
import {Config} from '@remotion/cli/config';
import path from 'node:path';

Config.setEntryPoint(path.join(process.cwd(), 'remotion', 'index.ts'));
Config.setPublicDir(path.join(process.cwd(), 'public'));
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
