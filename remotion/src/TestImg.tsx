import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
export default function TestImg() {
  return (
    <AbsoluteFill>
      <Img src={staticFile('test.png')} style={{width:'100%',height:'100%',objectFit:'cover'}} />
    </AbsoluteFill>
  );
}
