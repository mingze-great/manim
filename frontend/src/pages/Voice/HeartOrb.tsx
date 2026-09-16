/* 心脏 Orb：五种状态各有一套动效。
   为了不引入 three.js 依赖上的复杂度，先用纯 CSS + framer-motion + SVG 实现一个高质量的
   glow-orb。视觉上完全可以打过豆包的默认 UI。
   之后要升级为 R3F shader 版，只需替换本组件内部实现。 */
import { motion, useReducedMotion } from 'framer-motion'
import type { VoiceState } from './useVoiceSession'

interface Props {
  state: VoiceState
  amp: number // 0..1，实时音量（说话时驱动波纹强度）
}

const RING_COUNT = 3

const stateColor: Record<VoiceState, [string, string]> = {
  idle:     ['#3b82f6', '#8b5cf6'], // 蓝紫
  wake:     ['#22d3ee', '#a78bfa'], // 青紫
  listening:['#f59e0b', '#ec4899'], // 橙粉
  thinking: ['#a855f7', '#6366f1'], // 紫蓝
  speaking: ['#10b981', '#22d3ee'], // 青绿
  error:    ['#ef4444', '#f97316'], // 红橙
}

export default function HeartOrb({ state, amp }: Props) {
  const reduce = useReducedMotion()
  const [c1, c2] = stateColor[state]
  const pulse = reduce ? 1 : 1 + amp * 0.35

  return (
    <div className="voice-orb-wrap">
      {[...Array(RING_COUNT)].map((_, i) => (
        <motion.div
          key={i}
          className="voice-ring"
          style={{ borderColor: i % 2 === 0 ? c1 : c2 }}
          animate={
            reduce
              ? {}
              : {
                  scale: [1, 1.25 + i * 0.12, 1],
                  opacity: [0.55, 0.15, 0.55],
                }
          }
          transition={{
            duration: state === 'listening' ? 1.6 : state === 'speaking' ? 1.2 : 3.0,
            delay: i * 0.35,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
      <motion.div
        className="voice-core"
        style={{
          background: `radial-gradient(circle at 30% 30%, ${c1}, ${c2} 55%, #0b0f1a 100%)`,
          boxShadow: `0 0 80px 12px ${c1}55, 0 0 160px 40px ${c2}33`,
        }}
        animate={
          reduce
            ? {}
            : state === 'thinking'
              ? { rotate: [0, 360] }
              : { scale: [1, pulse, 1] }
        }
        transition={{
          duration: state === 'thinking' ? 8 : 1.8,
          repeat: Infinity,
          ease: state === 'thinking' ? 'linear' : 'easeInOut',
        }}
      >
        <div className="voice-core-inner" />
      </motion.div>
      <motion.div
        className="voice-label"
        animate={{ opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        {stateLabel(state)}
      </motion.div>
    </div>
  )
}

function stateLabel(s: VoiceState): string {
  switch (s) {
    case 'idle':      return '按住空格召唤小曼'
    case 'wake':      return '小曼在听…'
    case 'listening': return '正在聆听'
    case 'thinking':  return '正在思考'
    case 'speaking':  return '小曼说话中'
    case 'error':     return '出了点岔子'
  }
}
