import Phaser from "phaser";

export interface GroundLayerOptions {
  tileAssetId: string;
  tileSize: number;
  widthTiles: number;
  heightTiles: number;
  fillIndex?: number;
}

/**
 * Builds a Phaser Tilemap ground layer from a manifest tile asset. Works for
 * both single-tile "Middle" images (1x1 grid, always index 0) and the
 * multi-tile autotile sheets (Nx M grid), since Phaser infers the grid from
 * the loaded texture's dimensions.
 */
export function createGroundLayer(scene: Phaser.Scene, opts: GroundLayerOptions): Phaser.Tilemaps.TilemapLayer {
  const map = scene.make.tilemap({
    tileWidth: opts.tileSize,
    tileHeight: opts.tileSize,
    width: opts.widthTiles,
    height: opts.heightTiles,
  });
  const tileset = map.addTilesetImage(opts.tileAssetId, opts.tileAssetId, opts.tileSize, opts.tileSize, 0, 0);
  if (!tileset) {
    throw new Error(`[TileWorld] Failed to build tileset for "${opts.tileAssetId}"`);
  }
  const layer = map.createBlankLayer("ground", tileset, 0, 0);
  if (!layer) {
    throw new Error("[TileWorld] Failed to create ground layer");
  }
  layer.fill(opts.fillIndex ?? 0);
  return layer;
}

/** Adds a rectangular ring of static collision bodies around a room's perimeter. */
export function createPerimeterWalls(
  scene: Phaser.Scene,
  widthPx: number,
  heightPx: number,
  thickness = 16,
): Phaser.Physics.Arcade.StaticGroup {
  const walls = scene.physics.add.staticGroup();
  const addWall = (x: number, y: number, w: number, h: number) => {
    const rect = scene.add.rectangle(x, y, w, h).setOrigin(0, 0);
    scene.physics.add.existing(rect, true);
    walls.add(rect);
  };
  addWall(0, 0, widthPx, thickness); // top
  addWall(0, heightPx - thickness, widthPx, thickness); // bottom
  addWall(0, 0, thickness, heightPx); // left
  addWall(widthPx - thickness, 0, thickness, heightPx); // right
  return walls;
}

/** Creates an invisible interaction/transition zone (e.g. a door). */
export function createZone(scene: Phaser.Scene, x: number, y: number, w: number, h: number): Phaser.GameObjects.Zone {
  const zone = scene.add.zone(x, y, w, h);
  scene.physics.add.existing(zone, true);
  return zone;
}
