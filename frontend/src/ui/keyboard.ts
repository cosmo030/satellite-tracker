/** Keyboard shortcut helpers. */

/** Apple keyboards say ⌘ where others say Ctrl. */
export function shortcutModifierLabel(userAgent: string): string {
  return /Mac|iPhone|iPad/.test(userAgent) ? '⌘K' : 'Ctrl K';
}

/** ⌘K or Ctrl K, without other modifiers. */
export function isSearchShortcut(
  event: Pick<KeyboardEvent, 'key' | 'metaKey' | 'ctrlKey' | 'altKey' | 'shiftKey'>,
): boolean {
  const modifier = event.metaKey || event.ctrlKey;
  return modifier && !event.altKey && !event.shiftKey && event.key.toLowerCase() === 'k';
}
