export async function copyRichHtml(html: string) {
  if (!html) {
    throw new Error('没有可复制的内容')
  }

  if (window.isSecureContext && 'ClipboardItem' in window && navigator.clipboard?.write) {
    const blobMap = {
      'text/html': new Blob([html], { type: 'text/html' }),
      'text/plain': new Blob([html], { type: 'text/plain' }),
    }
    await navigator.clipboard.write([new ClipboardItem(blobMap)])
    return
  }

  const container = document.createElement('div')
  container.innerHTML = html
  container.style.position = 'fixed'
  container.style.left = '-99999px'
  container.style.top = '0'
  container.style.opacity = '0'
  container.setAttribute('contenteditable', 'true')
  document.body.appendChild(container)

  const selection = window.getSelection()
  const range = document.createRange()
  range.selectNodeContents(container)
  selection?.removeAllRanges()
  selection?.addRange(range)

  const success = document.execCommand('copy')
  selection?.removeAllRanges()
  document.body.removeChild(container)

  if (!success) {
    throw new Error('浏览器不支持富文本复制')
  }
}
