/**
 * localStorage access that never throws: storage can be disabled, full, or blocked
 * (private windows, strict privacy settings). UI preferences are a convenience, so failures
 * are ignored and the defaults apply.
 */

export function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeStorage(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Not saved: the preference applies for this visit only.
  }
}

export function removeStorage(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Nothing stored, or storage is blocked; either way there is nothing to remove.
  }
}
