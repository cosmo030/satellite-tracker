/**
 * Imperative wrapper around the CesiumJS viewer: satellite points, selection, orbit lines and
 * lighting. React components talk to this class only; Cesium types do not leak into the UI code.
 */
import {
  buildModuleUrl,
  Cartesian3,
  Color,
  ImageryLayer,
  JulianDate,
  Material,
  PerspectiveFrustum,
  PointPrimitiveCollection,
  type PointPrimitive,
  type Polyline,
  PolylineCollection,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  TileMapServiceImageryProvider,
  CesiumWidget,
  defined,
} from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';

import { POSITION_STRIDE, type GeoPosition } from '../orbit/propagation';

/** Which extras are drawn for the selected satellite. */
export interface GlobeLayers {
  orbitPath: boolean;
  groundTrack: boolean;
}

const KM_TO_M = 1000;
// Only the selected satellite uses the accent colour; every other satellite is a neutral grey.
const POINT_COLOR = Color.fromCssColorString('#b4bcc8').withAlpha(0.85);
const MARKER_OUTLINE = Color.fromCssColorString('#07080a');
const FALLBACK_ACCENT = '#ff7847';
const GROUND_TRACK_ALPHA = 0.4;
const ORBIT_DASH_LENGTH_PX = 14;
// When a satellite is selected the camera moves above it, this far beyond its altitude.
const CAMERA_STANDOFF_KM = 8000;
const FLIGHT_SECONDS = 1.5;
// Straight segments between track points would dip below the surface; lift the line a bit.
const GROUND_TRACK_HEIGHT_KM = 10;

function toCartesian(p: GeoPosition, heightKm = p.heightKm): Cartesian3 {
  return Cartesian3.fromDegrees(p.longitudeDeg, p.latitudeDeg, heightKm * KM_TO_M);
}

function flightSeconds(): number {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : FLIGHT_SECONDS;
}

export class GlobeScene {
  private readonly viewer: CesiumWidget;
  private readonly points: PointPrimitiveCollection;
  private readonly clickHandler: ScreenSpaceEventHandler;
  private pointList: PointPrimitive[] = [];
  private readonly selectedMarker: PointPrimitive;
  private readonly orbitLine: Polyline;
  private readonly groundTrackLine: Polyline;
  private focusedNoradId: number | null = null;
  private accent = Color.fromCssColorString(FALLBACK_ACCENT);
  private layers: GlobeLayers = { orbitPath: true, groundTrack: true };
  private hasTrack = false;
  private homeViewPending = true;

  constructor(
    container: HTMLElement,
    creditContainer: HTMLElement,
    onPick: (noradId: number | null) => void,
  ) {
    // CesiumWidget rather than Viewer: Viewer's toolbar widgets use Knockout, which needs
    // 'unsafe-eval' in the Content-Security-Policy.
    this.viewer = new CesiumWidget(container, {
      // Offline imagery bundled with Cesium: no Cesium ion account or token needed.
      baseLayer: ImageryLayer.fromProviderAsync(
        TileMapServiceImageryProvider.fromUrl(buildModuleUrl('Assets/Textures/NaturalEarthII')),
      ),
      // Credits are shown in a corner of the viewport tile, wherever the canvas extends to.
      creditContainer,
    });
    this.viewer.scene.globe.enableLighting = true;
    // The app drives the clock (see setTime) so the sun matches the time the UI shows.
    this.viewer.clock.shouldAnimate = false;

    const primitives = this.viewer.scene.primitives;
    this.points = primitives.add(new PointPrimitiveCollection());
    const lines: PolylineCollection = primitives.add(new PolylineCollection());
    this.orbitLine = lines.add({ width: 1.5, show: false });
    this.groundTrackLine = lines.add({ width: 1.5, show: false });
    const highlight: PointPrimitiveCollection = primitives.add(new PointPrimitiveCollection());
    this.selectedMarker = highlight.add({
      pixelSize: 10,
      outlineColor: MARKER_OUTLINE,
      outlineWidth: 1.5,
      show: false,
    });
    this.applyAccent();

    this.clickHandler = new ScreenSpaceEventHandler(this.viewer.scene.canvas);
    this.clickHandler.setInputAction((click: ScreenSpaceEventHandler.PositionedEvent) => {
      const picked: unknown = this.viewer.scene.pick(click.position);
      onPick(pickedNoradId(picked));
    }, ScreenSpaceEventType.LEFT_CLICK);
  }

  /** Replace the displayed satellites; positions arrive later via ``updatePositions``. */
  setSatellites(noradIds: readonly number[]): void {
    this.points.removeAll();
    this.pointList = noradIds.map((id) =>
      this.points.add({ id, pixelSize: 4, color: POINT_COLOR, show: false }),
    );
  }

  /** Move the points; ``positions`` is packed [lon, lat, heightKm] in ``setSatellites`` order. */
  updatePositions(positions: Float64Array): void {
    this.pointList.forEach((point, index) => {
      const offset = index * POSITION_STRIDE;
      const longitudeDeg = positions[offset] ?? Number.NaN;
      const latitudeDeg = positions[offset + 1] ?? Number.NaN;
      const heightKm = positions[offset + 2] ?? Number.NaN;
      if (Number.isNaN(longitudeDeg)) {
        point.show = false;
        return;
      }
      point.position = toCartesian({ longitudeDeg, latitudeDeg, heightKm });
      point.show = true;
    });
  }

  /** Highlight the selected satellite; the camera flies to it when the selection changes. */
  setSelectedPosition(noradId: number | null, position: GeoPosition | null): void {
    if (noradId === null || !position) {
      this.selectedMarker.show = false;
      if (noradId === null) this.focusedNoradId = null;
      return;
    }
    this.selectedMarker.position = toCartesian(position);
    this.selectedMarker.show = true;
    if (noradId !== this.focusedNoradId) {
      this.focusedNoradId = noradId;
      this.viewer.camera.flyTo({
        destination: toCartesian(position, position.heightKm + CAMERA_STANDOFF_KM),
        duration: flightSeconds(),
      });
    }
  }

  /** Draw the orbit path and its ground track; an empty track hides both. */
  setSelectedTrack(track: readonly GeoPosition[]): void {
    this.hasTrack = track.length > 1;
    if (this.hasTrack) {
      this.orbitLine.positions = track.map((p) => toCartesian(p));
      this.groundTrackLine.positions = track.map((p) => toCartesian(p, GROUND_TRACK_HEIGHT_KM));
    }
    this.applyLineVisibility();
  }

  setLayers(layers: GlobeLayers): void {
    this.layers = layers;
    this.applyLineVisibility();
  }

  /** The selected satellite, its marker and its lines use the skin's accent (a CSS colour). */
  setAccent(cssColor: string): void {
    this.accent = Color.fromCssColorString(cssColor.trim() || FALLBACK_ACCENT);
    this.applyAccent();
  }

  setLighting(enabled: boolean): void {
    this.viewer.scene.globe.enableLighting = enabled;
  }

  /** The time the scene shows (sun position for day/night lighting). */
  setTime(date: Date): void {
    this.viewer.clock.currentTime = JulianDate.fromDate(date);
  }

  /** Field of view along the canvas's longer side (see ui/placement fieldOfViewFor). */
  setFieldOfView(radians: number): void {
    const frustum = this.viewer.camera.frustum;
    if (frustum instanceof PerspectiveFrustum) frustum.fov = radians;
    // The start view was fitted before the canvas had its real size and lens; fit it again once.
    if (this.homeViewPending) {
      this.homeViewPending = false;
      this.viewer.camera.flyHome(0);
    }
  }

  flyHome(): void {
    this.viewer.camera.flyHome(flightSeconds());
  }

  destroy(): void {
    this.clickHandler.destroy();
    this.viewer.destroy();
  }

  private applyAccent(): void {
    this.selectedMarker.color = this.accent;
    this.orbitLine.material = Material.fromType('PolylineDash', {
      color: this.accent,
      dashLength: ORBIT_DASH_LENGTH_PX,
    });
    this.groundTrackLine.material = Material.fromType('Color', {
      color: this.accent.withAlpha(GROUND_TRACK_ALPHA),
    });
  }

  private applyLineVisibility(): void {
    this.orbitLine.show = this.hasTrack && this.layers.orbitPath;
    this.groundTrackLine.show = this.hasTrack && this.layers.groundTrack;
  }
}

function pickedNoradId(picked: unknown): number | null {
  if (!defined(picked) || typeof picked !== 'object' || !('id' in picked)) return null;
  return typeof picked.id === 'number' ? picked.id : null;
}
