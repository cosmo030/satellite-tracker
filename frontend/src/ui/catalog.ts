/**
 * Readable names for catalog codes. The API passes CelesTrak SATCAT values through unchanged:
 * the "country" is the SATCAT owner (source) code, which covers countries and organisations.
 * Codes not listed here are shown as they are.
 */

const OWNER_NAMES: Readonly<Record<string, string>> = {
  AB: 'Arabsat',
  AC: 'AsiaSat',
  ARGN: 'Argentina',
  ASRA: 'Austria',
  AUS: 'Australia',
  BEL: 'Belgium',
  BRAZ: 'Brazil',
  CA: 'Canada',
  CIS: 'Commonwealth of Independent States',
  CZCH: 'Czechia',
  DEN: 'Denmark',
  EGYP: 'Egypt',
  ESA: 'European Space Agency',
  EST: 'Estonia',
  EUME: 'EUMETSAT',
  EUTE: 'Eutelsat',
  FIN: 'Finland',
  FR: 'France',
  GER: 'Germany',
  GLOB: 'Globalstar',
  GREC: 'Greece',
  HUN: 'Hungary',
  IM: 'Inmarsat',
  IND: 'India',
  INDO: 'Indonesia',
  IRAN: 'Iran',
  IRID: 'Iridium',
  ISRA: 'Israel',
  ISS: 'International Space Station',
  IT: 'Italy',
  ITSO: 'Intelsat',
  JPN: 'Japan',
  KAZ: 'Kazakhstan',
  LTU: 'Lithuania',
  LUXE: 'Luxembourg',
  MALA: 'Malaysia',
  MEX: 'Mexico',
  NATO: 'NATO',
  NETH: 'Netherlands',
  NIG: 'Nigeria',
  NKOR: 'North Korea',
  NOR: 'Norway',
  O3B: 'O3b Networks',
  ORB: 'ORBCOMM',
  PAKI: 'Pakistan',
  POL: 'Poland',
  POR: 'Portugal',
  PRC: 'China',
  ROC: 'Taiwan',
  RP: 'Philippines',
  SAFR: 'South Africa',
  SAUD: 'Saudi Arabia',
  SES: 'SES',
  SING: 'Singapore',
  SKOR: 'South Korea',
  SPN: 'Spain',
  SWED: 'Sweden',
  SWTZ: 'Switzerland',
  THAI: 'Thailand',
  TURK: 'Turkey',
  UAE: 'United Arab Emirates',
  UK: 'United Kingdom',
  UKR: 'Ukraine',
  US: 'United States',
  VTNM: 'Vietnam',
};

const OBJECT_TYPES: Readonly<Record<string, string>> = {
  PAY: 'payload',
  'R/B': 'rocket body',
  DEB: 'debris',
  UNK: 'unknown object',
};

/** Display name for a SATCAT owner code; unknown codes are returned unchanged. */
export function ownerName(code: string): string {
  return OWNER_NAMES[code.toUpperCase()] ?? code;
}

export interface OwnerOption {
  code: string;
  name: string;
}

/** Every named owner, sorted by name, for the country filter. */
export const OWNER_OPTIONS: readonly OwnerOption[] = Object.entries(OWNER_NAMES)
  .map(([code, name]) => ({ code, name }))
  .sort((a, b) => a.name.localeCompare(b.name, 'en'));

/** The owner code for a typed name or code ("Germany", "germany", "GER"); null if unknown. */
export function ownerCodeFor(input: string): string | null {
  const wanted = input.trim().toLowerCase();
  if (wanted === '') return null;
  const match = OWNER_OPTIONS.find(
    (option) => option.name.toLowerCase() === wanted || option.code.toLowerCase() === wanted,
  );
  return match?.code ?? null;
}

/** Sentence-case label for a SATCAT object type ("PAY" -> "payload"). */
export function objectTypeLabel(code: string): string {
  return OBJECT_TYPES[code.toUpperCase()] ?? code;
}
