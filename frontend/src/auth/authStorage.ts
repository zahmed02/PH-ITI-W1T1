// Single source of truth for where the auth token lives (localStorage) and
// how other parts of the app find out it changed.
//
// Cross-tab sync relies on a browser guarantee: when localStorage is
// modified, every OTHER tab of the same origin gets a native 'storage'
// event immediately - but the tab that made the change does NOT get that
// event itself. So we also fire a custom window event for same-tab
// listeners. Together, both same-tab and other-tab listeners react
// instantly to login/logout.

const AUTH_KEY = 'stellaris_auth';
const AUTH_CHANGED_EVENT = 'stellaris-auth-changed';

export interface StoredAuth {
  token: string;
  username: string;
}

export function getStoredAuth(): StoredAuth | null {
  const raw = localStorage.getItem(AUTH_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.token === 'string') return parsed;
    return null;
  } catch {
    return null;
  }
}

export function setStoredAuth(data: StoredAuth) {
  localStorage.setItem(AUTH_KEY, JSON.stringify(data));
  window.dispatchEvent(new CustomEvent(AUTH_CHANGED_EVENT));
}

export function clearStoredAuth() {
  localStorage.removeItem(AUTH_KEY);
  window.dispatchEvent(new CustomEvent(AUTH_CHANGED_EVENT));
}

/**
 * Subscribes to both the auth key changing in another tab (native
 * 'storage' event) and in this tab (our custom event). Returns an
 * unsubscribe function.
 */
export function subscribeToAuthChanges(callback: () => void): () => void {
  const storageHandler = (e: StorageEvent) => {
    if (e.key === AUTH_KEY || e.key === null) callback();
  };
  const localHandler = () => callback();

  window.addEventListener('storage', storageHandler);
  window.addEventListener(AUTH_CHANGED_EVENT, localHandler);

  return () => {
    window.removeEventListener('storage', storageHandler);
    window.removeEventListener(AUTH_CHANGED_EVENT, localHandler);
  };
}
