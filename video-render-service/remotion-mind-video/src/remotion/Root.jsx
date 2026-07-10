import React from 'react';
import {Composition} from 'remotion';
import {MindVideo} from './MindVideo.jsx';
import {KnowledgeIpPackage} from './KnowledgeIpPackage.jsx';
import {defaultScript, scriptToStory} from '../story.js';

const sampleStory = scriptToStory({script: defaultScript, style: 'aurora', density: 1});

export const RemotionRoot = () => (
  <>
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
    <Composition
      id="KnowledgeIpPackage"
      component={KnowledgeIpPackage}
      durationInFrames={5172}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        sourceVideo: 'workflow-inputs/knowledge-ip-test-cfr.mp4',
        materialTrackSrc: 'workflow-assets/knowledge-ip-test/material_track.mp4',
        baseVideoSrc: 'workflow-assets/knowledge-ip-test/base_track.mp4',
        durationMs: 172400
      }}
      calculateMetadata={({props}) => {
        const fps = 30;
        const durationMs = Number(props.durationMs || 172400);
        return {
          durationInFrames: Math.max(1, Math.ceil(durationMs / 1000 * fps)),
          fps,
          width: 1080,
          height: 1920
        };
      }}
    />
  </>
);
