/** Small line icons (16 px, current colour). Decorative: buttons carry their own labels. */
import type { ReactNode } from 'react';

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export function TrackerIcon() {
  return (
    <Icon>
      <circle cx="8" cy="8" r="2.2" />
      <ellipse cx="8" cy="8" rx="6.5" ry="3" transform="rotate(-30 8 8)" />
      <circle cx="13.2" cy="4.6" r="0.9" fill="currentColor" stroke="none" />
    </Icon>
  );
}

export function SearchIcon() {
  return (
    <Icon>
      <circle cx="7" cy="7" r="4.5" />
      <path d="M10.4 10.4 14 14" />
    </Icon>
  );
}

export function LayersIcon() {
  return (
    <Icon>
      <path d="M8 2.5 14 5.5 8 8.5 2 5.5Z" />
      <path d="M2 8.5 8 11.5 14 8.5" />
      <path d="M2 11 8 14 14 11" opacity="0.6" />
    </Icon>
  );
}

export function ClockIcon() {
  return (
    <Icon>
      <circle cx="8" cy="8" r="6" />
      <path d="M8 4.8V8l2.2 1.6" />
    </Icon>
  );
}

export function SettingsIcon() {
  return (
    <Icon>
      <circle cx="8" cy="8" r="2" />
      <path d="M8 1.8v1.6M8 12.6v1.6M14.2 8h-1.6M3.4 8H1.8M12.4 3.6l-1.1 1.1M4.7 11.3l-1.1 1.1M12.4 12.4l-1.1-1.1M4.7 4.7 3.6 3.6" />
      <circle cx="8" cy="8" r="4.4" />
    </Icon>
  );
}

export function CloseIcon() {
  return (
    <Icon>
      <path d="M4 4l8 8M12 4l-8 8" />
    </Icon>
  );
}

export function PlayIcon() {
  return (
    <Icon>
      <path d="M5 3.5v9l7-4.5Z" fill="currentColor" stroke="none" />
    </Icon>
  );
}

export function SunIcon() {
  return (
    <Icon>
      <circle cx="8" cy="8" r="2.8" />
      <path d="M8 1.5v1.3M8 13.2v1.3M14.5 8h-1.3M2.8 8H1.5M12.6 3.4l-.9.9M4.3 11.7l-.9.9M12.6 12.6l-.9-.9M4.3 4.3l-.9-.9" />
    </Icon>
  );
}
