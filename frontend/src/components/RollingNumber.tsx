import { createContext, useCallback, useContext, useLayoutEffect, useRef, useState } from 'react';

import { formatCount } from '../orbit/format';
import {
  FADE_MS,
  initialRollState,
  nextRollState,
  restIndex,
  ROLL_DURATION_MS,
  ROLL_EASING,
  rollTarget,
  STRIP_DIGITS,
  tokenize,
  type ExitingDigit,
  type RollDirection,
} from '../ui/rolling';

/**
 * Whether counts inside this part of the workspace may animate. The workspace turns it off for
 * collapsed tiles, where a count changes out of sight and should simply be set.
 */
export const CountMotion = createContext(true);

const STRIP = Array.from({ length: STRIP_DIGITS }, (_, index) => index % 10);

interface RollingNumberProps {
  value: number;
  /** Formats the value; defaults to the user's locale with thousands separators. */
  format?: (value: number) => string;
  className?: string;
}

/**
 * A count whose changed digits roll like an odometer when the value changes (UI spec 6.1).
 * The first render shows the value at once; remount it (with a ``key``) to skip a roll.
 * Screen readers get the formatted value as text; the moving digits are hidden from them.
 */
export function RollingNumber({ value, format = formatCount, className }: RollingNumberProps) {
  const text = format(value);
  const [state, setState] = useState(() => initialRollState(value, text));
  const motion = useContext(CountMotion);

  // Work out the roll when the value changes, during render (React's pattern for state that
  // follows a prop), so the slots get their direction and delays in the same commit.
  let roll = state;
  if (state.value !== value || state.text !== text) {
    roll = nextRollState(state, value, text);
    setState(roll);
  }

  const removeExit = useCallback((id: string) => {
    setState((current) => ({ ...current, exits: current.exits.filter((exit) => exit.id !== id) }));
  }, []);

  return (
    <span className={className ? `rolling-number ${className}` : 'rolling-number'}>
      <span className="visually-hidden">{text}</span>
      <span className="rolling-digits" aria-hidden="true">
        {roll.exits
          .toSorted((a, b) => b.place - a.place)
          .map((exit) => (
            <ExitingSlot key={exit.id} exit={exit} motion={motion} onDone={removeExit} />
          ))}
        {tokenize(text).map((token) =>
          token.kind === 'static' ? (
            <span key={`s${token.key}`}>{token.char}</span>
          ) : (
            <DigitSlot
              key={`d${token.place}`}
              digit={token.digit}
              direction={roll.direction}
              delayMs={roll.delays[token.place] ?? 0}
              entering={roll.entering.includes(token.place)}
              motion={motion}
            />
          ),
        )}
      </span>
    </span>
  );
}

/** Animations are skipped when the user asks for less motion or nobody can see them. */
function canAnimate(motion: boolean): boolean {
  return (
    motion &&
    document.visibilityState === 'visible' &&
    !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

function stripTransform(index: number): string {
  return `translateY(${(-index * 100) / STRIP_DIGITS}%)`;
}

/** Current strip position in digits, read from the (possibly animating) computed transform. */
function currentIndex(strip: HTMLElement, fallback: number): number {
  const digitHeight = strip.offsetHeight / STRIP_DIGITS;
  if (digitHeight <= 0) return fallback;
  const { m42: offsetY } = new DOMMatrixReadOnly(getComputedStyle(strip).transform);
  return -offsetY / digitHeight;
}

interface DigitSlotProps {
  digit: number;
  direction: RollDirection | null;
  delayMs: number;
  /** A new leading digit: it slides in from the edge and fades in. */
  entering: boolean;
  motion: boolean;
}

/** One digit: a clipped slot holding a vertical strip of 0–9, three times. */
function DigitSlot({ digit, direction, delayMs, entering, motion }: DigitSlotProps) {
  const innerRef = useRef<HTMLSpanElement>(null);
  const stripRef = useRef<HTMLSpanElement>(null);
  const shownRef = useRef(digit);
  // How this slot first appeared; only used once, on mount.
  const arrivalRef = useRef({ entering, direction, delayMs, motion });

  // Roll when the digit changes. The strip's resting transform (set in render) already shows
  // the new digit in the middle copy; the animation runs from where the strip is on screen to
  // the same digit in the copy above or below, then ends on that equivalent resting position.
  useLayoutEffect(() => {
    const strip = stripRef.current;
    const previous = shownRef.current;
    shownRef.current = digit;
    if (!strip || previous === digit) return;
    const running = strip.getAnimations();
    const from =
      running.length > 0 ? currentIndex(strip, restIndex(previous)) : restIndex(previous);
    running.forEach((animation) => {
      animation.cancel();
    });
    if (!direction || !canAnimate(motion)) return;
    const to = rollTarget(from, digit, direction);
    if (Math.abs(to - from) < 0.01) return;
    strip.animate([{ transform: stripTransform(from) }, { transform: stripTransform(to) }], {
      duration: ROLL_DURATION_MS,
      delay: delayMs,
      easing: ROLL_EASING,
      fill: 'backwards',
    });
  }, [digit, direction, delayMs, motion]);

  // A new leading digit enters from below (increase) or above (decrease) while fading in.
  useLayoutEffect(() => {
    const inner = innerRef.current;
    const arrival = arrivalRef.current;
    if (!inner || !arrival.entering || !arrival.direction || !canAnimate(arrival.motion)) return;
    const edge = arrival.direction === 'up' ? '100%' : '-100%';
    const timing = { delay: arrival.delayMs, easing: ROLL_EASING, fill: 'backwards' as const };
    const slide = inner.animate([{ transform: `translateY(${edge})` }, { transform: 'none' }], {
      ...timing,
      duration: ROLL_DURATION_MS,
    });
    const fadeIn = inner.animate([{ opacity: 0 }, { opacity: 1 }], {
      ...timing,
      duration: FADE_MS,
    });
    return () => {
      slide.cancel();
      fadeIn.cancel();
    };
  }, []);

  return (
    <span className="digit-slot">
      <span className="digit-sizer">0</span>
      <span ref={innerRef} className="digit-roll">
        <span
          ref={stripRef}
          className="digit-strip"
          style={{ transform: stripTransform(restIndex(digit)) }}
        >
          {STRIP.map((stripDigit, index) => (
            <span key={index}>{stripDigit}</span>
          ))}
        </span>
      </span>
    </span>
  );
}

interface ExitingSlotProps {
  exit: ExitingDigit;
  motion: boolean;
  onDone: (id: string) => void;
}

/** A leading digit that no longer exists: it fades out, then is removed. */
function ExitingSlot({ exit, motion, onDone }: ExitingSlotProps) {
  const slotRef = useRef<HTMLSpanElement>(null);

  useLayoutEffect(() => {
    const slot = slotRef.current;
    if (!slot || !canAnimate(motion)) {
      onDone(exit.id);
      return;
    }
    const fade = slot.animate([{ opacity: 1 }, { opacity: 0 }], {
      duration: FADE_MS,
      fill: 'forwards',
    });
    fade.onfinish = () => {
      onDone(exit.id);
    };
    return () => {
      fade.onfinish = null;
      fade.cancel();
    };
  }, [exit.id, motion, onDone]);

  return (
    <span ref={slotRef} className="digit-slot">
      <span className="digit-sizer exiting">{exit.digit}</span>
    </span>
  );
}
