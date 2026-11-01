/**
 * Rolling digits (UI spec 6.1): when a count changes, each changed digit rolls like an odometer,
 * ones first, up for increases and down for decreases. Pure helpers; the RollingNumber
 * component turns them into animations.
 *
 * Digits are addressed by place, counted from the right (ones = 0), so that the same place keeps
 * its slot when the number grows or shrinks. Anything that is not an ASCII digit (thousands
 * separators) is static.
 */

/** Each digit rolls for this long, with this easing. */
export const ROLL_DURATION_MS = 450;
export const ROLL_EASING = 'cubic-bezier(.25, .8, .25, 1)';
/** Each further changed digit to the left starts this much later, up to the cap. */
export const STAGGER_STEP_MS = 50;
export const STAGGER_CAP_MS = 150;
/** Leading digits that appear or disappear fade over this long. */
export const FADE_MS = 300;

/** The strip holds 0–9 three times; at rest it shows the middle copy (indices 10–19). */
export const STRIP_DIGITS = 30;
const MIDDLE_COPY = 10;

export type RollDirection = 'up' | 'down';

export type NumberToken =
  { kind: 'digit'; digit: number; place: number } | { kind: 'static'; char: string; key: string };

/** Split formatted text into digits (with their place) and static characters. */
export function tokenize(text: string): NumberToken[] {
  const chars = characters(text);
  let place = chars.filter(isDigit).length;
  return chars.map((char, index) => {
    if (isDigit(char)) {
      place -= 1;
      return { kind: 'digit', digit: Number(char), place };
    }
    // Keyed by the number of digits to its right, so a separator keeps its key while it stays put.
    return { kind: 'static', char, key: `${place}:${index === 0 ? 'lead' : char}` };
  });
}

/** Digits by place: index 0 is the ones digit. */
export function digitsByPlace(text: string): number[] {
  return characters(text).filter(isDigit).map(Number).reverse();
}

/** Formatted counts hold only digits and single-character separators, so code points suffice. */
function characters(text: string): string[] {
  return Array.from(text);
}

function isDigit(char: string): boolean {
  return char >= '0' && char <= '9';
}

export interface ExitingDigit {
  id: string;
  place: number;
  digit: number;
}

/** Everything the component needs to animate one change of value. */
export interface RollState {
  value: number;
  text: string;
  /** Direction of the last change; null before the first change. */
  direction: RollDirection | null;
  /** Start delay per changed place (ms); unchanged places are absent. */
  delays: Record<number, number>;
  /** Places that did not exist before the last change (new leading digits). */
  entering: number[];
  /** Leading digits that no longer exist and are fading out. */
  exits: ExitingDigit[];
}

export function initialRollState(value: number, text: string): RollState {
  return { value, text, direction: null, delays: {}, entering: [], exits: [] };
}

/** The roll from the previous state to a new value and its formatted text. */
export function nextRollState(previous: RollState, value: number, text: string): RollState {
  const before = digitsByPlace(previous.text);
  const after = digitsByPlace(text);
  const changed = after.flatMap((digit, place) => (before[place] === digit ? [] : [place]));
  const delays = Object.fromEntries(changed.map((place, rank) => [place, staggerDelay(rank)]));
  const newExits = before
    .map((digit, place) => ({ id: `${previous.text}@${place}`, place, digit }))
    .filter((exit) => exit.place >= after.length);
  return {
    value,
    text,
    direction: rollDirection(previous.value, value),
    delays,
    entering: changed.filter((place) => place >= before.length),
    exits: [...previous.exits.filter((exit) => exit.place >= after.length), ...newExits],
  };
}

export function rollDirection(previous: number, next: number): RollDirection | null {
  if (next > previous) return 'up';
  return next < previous ? 'down' : null;
}

/** Ones first: the rightmost changed digit starts at once, each one to its left 50 ms later. */
export function staggerDelay(rank: number): number {
  return Math.min(rank * STAGGER_STEP_MS, STAGGER_CAP_MS);
}

/** Strip index at which a digit rests (middle copy). */
export function restIndex(digit: number): number {
  return MIDDLE_COPY + digit;
}

/**
 * Bring a (possibly fractional, mid-roll) strip position into the middle copy. The strip repeats
 * every 10 digits, so this changes nothing on screen.
 */
export function normalizeIndex(index: number): number {
  return MIDDLE_COPY + ((((index - MIDDLE_COPY) % 10) + 10) % 10);
}

/**
 * Where the strip should roll to, from its current position, to show ``digit``: the next
 * occurrence above (up) or below (down), wrapping past 9→0 or 0→9 like an odometer. Starting
 * from the middle copy keeps the target inside the strip (0–29).
 */
export function rollTarget(fromIndex: number, digit: number, direction: RollDirection): number {
  const from = normalizeIndex(fromIndex);
  const rest = restIndex(digit);
  if (direction === 'up') return rest > from ? rest : rest + 10;
  return rest < from ? rest : rest - 10;
}
