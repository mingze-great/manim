export const AUTH_STORAGE_KEY = 'auth-storage'
export const LOGOUT_MARKER_KEY = 'auth-logout-at'

export function clearAuthArtifacts() {
  if (typeof window === 'undefined') return
  try {
    localStorage.removeItem(AUTH_STORAGE_KEY)
    localStorage.setItem(LOGOUT_MARKER_KEY, String(Date.now()))
    sessionStorage.removeItem('admin_mode')
  } catch {
  }
}

export function syncCrossSiteLogout(targetOrigin: string) {
  if (typeof window === 'undefined') return
  const iframe = document.createElement('iframe')
  iframe.style.display = 'none'
  iframe.src = `${targetOrigin.replace(/\/$/, '')}/logout-bridge`
  document.body.appendChild(iframe)
  window.setTimeout(() => iframe.remove(), 2000)
}

export function buildLegacyEntryUrl(targetOrigin: string) {
  const normalized = targetOrigin.replace(/\/$/, '') || window.location.origin
  return `${normalized}/?legacy_entry=1`
}
