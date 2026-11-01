/**
 * Imperative wrapper around the CesiumJS viewer: satellite points, selection and orbit lines.
 * React components talk to this class only; Cesium types do not leak into the UI code.
 */
import {
  buildModuleUrl,
  Cartesian3,
  Color,
  ImageryLayer,
  Material,
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

const KM_TO_M = 1000;
const POINT_COLOR = Color.fromCssColorString('#e8f1ff');
const SELECTED_COLOR = Color.fromCssColorString('#ffd166');
const ORBIT_COLOR = Color.fromCssColorString('#4cc9f0');
const GROUND_TRACK_COLOR = Color.fromCssColorString('#ffd166').withAlpha(0.6);
// When a satellite is selected the camera moves above it, this far beyond its altitude.
const CAMERA_STANDOFF_KM = 8000;
// Straight segments between track points would dip below the surface; lift the line a bit.
const GROUND_TRACK_HEIGHT_KM = 10;

function toCartesian(p: GeoPosition, heightKm = p.heightKm): Cartesian3 {
  return Cartesian3.fromDegrees(p.longitudeDeg, p.latitudeDeg, heightKm * KM_TO_M);
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

  constructor(container: HTMLElement, onPick: (noradId: number | null) => void) {
    // CesiumWidget rather than Viewer: Viewer's toolbar widgets use Knockout, which needs
    // 'unsafe-eval' in the Content-Security-Policy.
    this.viewer = new CesiumWidget(container, {
      // Offline imagery bundled with Cesium: no Cesium ion account or token needed.
      baseLayer: ImageryLayer.fromProviderAsync(
        TileMapServiceImageryProvider.fromUrl(buildModuleUrl('Assets/Textures/NaturalEarthII')),
      ),
    });
    const primitives = this.viewer.scene.primitives;
    this.points = primitives.add(new PointPrimitiveCollection());
    const lines: PolylineCollection = primitives.add(new PolylineCollection());
    this.orbitLine = lines.add({ width: 2, show: false, material: colorMaterial(ORBIT_COLOR) });
    this.groundTrackLine = lines.add({
      width: 2,
      show: false,
      material: colorMaterial(GROUND_TRACK_COLOR),
    });
    const highlight: PointPrimitiveCollection = primitives.add(new PointPrimitiveCollection());
    this.selectedMarker = highlight.add({
      pixelSize: 12,
      color: SELECTED_COLOR,
      outlineColor: Color.BLACK,
      outlineWidth: 1,
      show: false,
    });
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
      this.points.add({ id, pixelSize: 5, color: POINT_COLOR, show: false }),
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
        duration: 1.5,
      });
    }
  }

  /** Draw the orbit path and its ground track; an empty track hides both. */
  setSelectedTrack(track: readonly GeoPosition[]): void {
    const visible = track.length > 1;
    this.orbitLine.show = visible;
    this.groundTrackLine.show = visible;
    if (!visible) return;
    this.orbitLine.positions = track.map((p) => toCartesian(p));
    this.groundTrackLine.positions = track.map((p) => toCartesian(p, GROUND_TRACK_HEIGHT_KM));
  }

  destroy(): void {
    this.clickHandler.destroy();
    this.viewer.destroy();
  }
}

function colorMaterial(color: Color): Material {
  return Material.fromType('Color', { color });
}

function pickedNoradId(picked: unknown): number | null {
  if (!defined(picked) || typeof picked !== 'object' || !('id' in picked)) return null;
  return typeof picked.id === 'number' ? picked.id : null;
}
