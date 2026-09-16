import { motion, AnimatePresence } from 'framer-motion'
import type { TurnRecord } from './useVoiceSession'

interface Props {
  turns: TurnRecord[]
  liveUser: string
  liveAssistant: string
}

export default function Timeline({ turns, liveUser, liveAssistant }: Props) {
  return (
    <div className="voice-timeline">
      <AnimatePresence initial={false}>
        {turns.map((t) => (
          <motion.div
            key={t.id}
            layout
            className="voice-turn"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.35 }}
          >
            <div className="voice-user">🎙 {t.user || '（未识别到内容）'}</div>
            <div className="voice-assistant">🌙 {t.assistant || '…'}</div>
          </motion.div>
        ))}
      </AnimatePresence>

      {(liveUser || liveAssistant) && (
        <motion.div
          className="voice-turn voice-turn-live"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {liveUser && <div className="voice-user">🎙 {liveUser}</div>}
          {liveAssistant && <div className="voice-assistant">🌙 {liveAssistant}</div>}
        </motion.div>
      )}
    </div>
  )
}
