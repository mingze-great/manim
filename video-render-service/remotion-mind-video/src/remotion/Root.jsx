import React from 'react';
import {Composition} from 'remotion';
import {MindVideo} from './MindVideo.jsx';
import {defaultScript, scriptToStory} from '../story.js';

const sampleStory = scriptToStory({script: defaultScript, style: 'aurora', density: 1});

export const RemotionRoot = () => (
  <Composition
    id="MindVideo"
    component={MindVideo}
    durationInFrames={sampleStory.durationInFrames}
    fps={sampleStory.fps}
    width={sampleStory.width}
    height={sampleStory.height}
    defaultProps={{
      script: defaultScript,
      style: 'aurora',
      density: 1,
      audioScenes: [],
      bgmSrc: null
    }}
    calculateMetadata={({props}) => {
      const story = scriptToStory(props);
      return {
        durationInFrames: story.durationInFrames,
        fps: story.fps,
        width: story.width,
        height: story.height
      };
    }}
  />
);
