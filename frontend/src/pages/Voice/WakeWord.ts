/* 唤醒词占位实现：本轮用 Space 长按代替真正的「小曼」唤醒词。

  真接入 Porcupine 时，只要替换 startWakeWordDetector 内部即可，回调不变。
*/

export interface WakeWordHandle {
  stop: () => void
}

export interface WakeWordCallbacks {
  onWake: () => void
  onPress: () => void   // 按下 Space
  onRelease: () => void // 松开 Space
}

export function startWakeWordDetector(cb: WakeWordCallbacks): WakeWordHandle {
  let pressed = false
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.code !== 'Space' || e.repeat) return
    if (isTypingIn(e.target)) return
    e.preventDefault()
    pressed = true
    cb.onWake()
    cb.onPress()
  }
  const onKeyUp = (e: KeyboardEvent) => {
    if (e.code !== 'Space' || !pressed) return
    if (isTypingIn(e.target)) return
    e.preventDefault()
    pressed = false
    cb.onRelease()
  }
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
  return {
    stop: () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
    },
  }
}

function isTypingIn(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false
  const tag = target.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable
}
