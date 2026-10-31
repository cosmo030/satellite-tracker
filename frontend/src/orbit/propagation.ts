/**
 * Orbit maths on top of satellite.js (SGP4): element sets in, geodetic positions out.
 * Pure functions, shared by the main thread and the propagation worker.
 */
import {
  degreesLat,
  degreesLong,
  eciToGeodetic,
  gstime,
  json2satrec,
  propagate,
  type OMMJsonObject,
  type SatRec,
} from 'satellite.js';

import type { ElementSet } from '../api/client';

/** Geodetic position: degrees and kilometres above the WGS-84 ellipsoid. */
export interface GeoPosition {
  longitudeDeg: number;
  latitudeDeg: number;
  heightKm: number;
}

export interface SatelliteState extends GeoPosition {
  speedKmPerS: number;
}

/** Values per satellite in a packed positions buffer: longitude, latitude, height. */
export const POSITION_STRIDE = 3;

const MS_PER_MINUTE = 60_000;

/**
 * Convert an API element set to the OMM JSON object satellite.js expects.
 * The epoch is sent without a zone designator, the way CelesTrak publishes it (UTC).
 */
export function toOmm(elements: ElementSet): OMMJsonObject {
  return {
    OBJECT_NAME: elements.object_name,
    OBJECT_ID: elements.object_id ?? '',
    EPOCH: new Date(elements.epoch).toISOString().replace('Z', ''),
    MEAN_MOTION: elements.mean_motion,
    ECCENTRICITY: elements.eccentricity,
    INCLINATION: elements.inclination_deg,
    RA_OF_ASC_NODE: elements.raan_deg,
    ARG_OF_PERICENTER: elements.arg_of_pericenter_deg,
    MEAN_ANOMALY: elements.mean_anomaly_deg,
    EPHEMERIS_TYPE: 0,
    CLASSIFICATION_TYPE: elements.classification_type === 'C' ? 'C' : 'U',
    NORAD_CAT_ID: elements.norad_id,
    ELEMENT_SET_NO: elements.element_set_no ?? 999,
    REV_AT_EPOCH: elements.rev_at_epoch ?? 0,
    BSTAR: elements.bstar,
    MEAN_MOTION_DOT: elements.mean_motion_dot,
    MEAN_MOTION_DDOT: elements.mean_motion_ddot,
  };
}

export function createSatrec(elements: ElementSet): SatRec {
  return json2satrec(toOmm(elements));
}

/** Position and speed at ``date``, or null when SGP4 cannot propagate (for example, decayed). */
export function stateAt(satrec: SatRec, date: Date): SatelliteState | null {
  const result = propagate(satrec, date);
  if (!result) return null;
  const { position, velocity } = result;
  const geodetic = eciToGeodetic(position, gstime(date));
  return {
    longitudeDeg: degreesLong(geodetic.longitude),
    latitudeDeg: degreesLat(geodetic.latitude),
    heightKm: geodetic.height,
    speedKmPerS: Math.hypot(velocity.x, velocity.y, velocity.z),
  };
}

/**
 * Positions of many satellites at one instant, packed as [lon, lat, height, ...].
 * Satellites that cannot be propagated get NaN entries so indexes stay aligned.
 */
export function propagateAll(satrecs: readonly SatRec[], date: Date): Float64Array {
  const buffer = new Float64Array(satrecs.length * POSITION_STRIDE);
  const gmst = gstime(date);
  satrecs.forEach((satrec, index) => {
    const offset = index * POSITION_STRIDE;
    const result = propagate(satrec, date);
    if (!result) {
      buffer.fill(Number.NaN, offset, offset + POSITION_STRIDE);
      return;
    }
    const geodetic = eciToGeodetic(result.position, gmst);
    buffer[offset] = degreesLong(geodetic.longitude);
    buffer[offset + 1] = degreesLat(geodetic.latitude);
    buffer[offset + 2] = geodetic.height;
  });
  return buffer;
}

/**
 * Positions over one orbital period starting at ``start``, sampled ``steps`` times plus the
 * end point. Used to draw the orbit path and the ground track.
 */
export function orbitTrack(
  satrec: SatRec,
  start: Date,
  periodMinutes: number,
  steps = 180,
): GeoPosition[] {
  const track: GeoPosition[] = [];
  const stepMs = (periodMinutes * MS_PER_MINUTE) / steps;
  for (let i = 0; i <= steps; i += 1) {
    const state = stateAt(satrec, new Date(start.getTime() + i * stepMs));
    if (state) track.push(state);
  }
  return track;
}
