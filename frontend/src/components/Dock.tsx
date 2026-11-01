import type { ReactNode, Ref } from 'react';

import { ClockIcon, LayersIcon, SearchIcon, SettingsIcon, TrackerIcon } from './icons';

interface DockProps {
  onHome: () => void;
  onSearch: () => void;
  onGroups: () => void;
  onTimeline: () => void;
  onSettings: () => void;
  settingsOpen: boolean;
  /** On small screens, the tile whose bottom sheet is open (its button shows as pressed). */
  openSheet: 'search' | 'groups' | 'timeline' | 'selected' | null;
  settingsButtonRef?: Ref<HTMLButtonElement>;
}

/** Icon column (a bottom bar on small screens) that brings tiles into view and opens Settings. */
export function Dock({
  onHome,
  onSearch,
  onGroups,
  onTimeline,
  onSettings,
  settingsOpen,
  openSheet,
  settingsButtonRef,
}: DockProps) {
  return (
    <nav className="tile dock" aria-label="Workspace">
      <DockButton label="Tracker home view" className="home" onClick={onHome}>
        <TrackerIcon />
      </DockButton>
      <DockButton label="Search" onClick={onSearch} pressed={openSheet === 'search'}>
        <SearchIcon />
      </DockButton>
      <DockButton label="Groups" onClick={onGroups} pressed={openSheet === 'groups'}>
        <LayersIcon />
      </DockButton>
      <DockButton label="Timeline" onClick={onTimeline} pressed={openSheet === 'timeline'}>
        <ClockIcon />
      </DockButton>
      <span className="dock-spacer" />
      <DockButton
        label="Settings"
        onClick={onSettings}
        expanded={settingsOpen}
        buttonRef={settingsButtonRef}
      >
        <SettingsIcon />
      </DockButton>
    </nav>
  );
}

interface DockButtonProps {
  label: string;
  onClick: () => void;
  className?: string;
  expanded?: boolean;
  /** Only set where the button toggles something (a bottom sheet); omitted otherwise. */
  pressed?: boolean;
  buttonRef?: Ref<HTMLButtonElement> | undefined;
  children: ReactNode;
}

function DockButton({
  label,
  onClick,
  className,
  expanded,
  pressed,
  buttonRef,
  children,
}: DockButtonProps) {
  return (
    <button
      ref={buttonRef}
      type="button"
      className={className ? `dock-button ${className}` : 'dock-button'}
      aria-label={label}
      aria-expanded={expanded}
      aria-pressed={pressed || undefined}
      onClick={onClick}
    >
      {children}
      <span className="tooltip" aria-hidden="true">
        {label}
      </span>
    </button>
  );
}
