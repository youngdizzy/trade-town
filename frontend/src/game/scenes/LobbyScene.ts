import Phaser from "phaser";
import type { SceneId } from "@/types";
import { PlayerController } from "@/game/entities/PlayerController";
import { CameraManager } from "@/game/systems/CameraManager";
import { SceneManager, type SceneTransitionData } from "@/game/systems/SceneManager";
import { createGroundLayer, createZone } from "@/game/systems/TileWorld";
import { EventBus } from "@/game/systems/EventBus";
import { GameManager } from "@/game/systems/GameManager";
import { AssetLoader } from "@/game/systems/AssetLoader";

const TILE_SIZE = 16;
const WIDTH_TILES = 108;
const HEIGHT_TILES = 32;
const WIDTH_PX = WIDTH_TILES * TILE_SIZE;
const HEIGHT_PX = HEIGHT_TILES * TILE_SIZE;

const BACK_ROW_Y = 96;
const FRONT_ROW_Y = 336;

interface DoorDef {
  target: SceneId;
  label: string;
  x: number;
  y: number;
  /** Manifest asset id for this building's sprite — see the Buildings/ folder. */
  asset: string;
  /**
   * Every building is scaled to this display width regardless of its native
   * art size, so a much bigger source sprite (the Inn) doesn't overlap its
   * neighbors. These are tuned per building rather than one shared constant
   * — the source sprites have very different native aspect ratios (the
   * greenhouse is narrow and tall, the limestone mansion is short and wide),
   * so scaling every building to the same width would leave the narrow ones
   * comically tall (a first pass at a flat 190px front-row width scaled the
   * greenhouse to 253px tall, floating its label far above the actual roof
   * — see buildBuildings()'s topEdge comment). Chosen so every building's
   * resulting height lands in a similar ~120-190px band instead.
   */
  targetWidth: number;
}

// Two staggered rows rather than one straight line — the back row holds the
// original six-room roster's buildings, the front row the v0.5/v0.6 rooms,
// offset horizontally so the courtyard reads as a small village rather than
// a row of shopfronts. Every building is a distinct piece from the Cute
// Fantasy premium pack's Unique_Buildings set (or a named house variant),
// not the same sprite re-tinted nine times.
const DOORS: DoorDef[] = [
  { target: "ScoutOfficeScene", label: "Scout Office", x: (WIDTH_PX * 1) / 6, y: BACK_ROW_Y, asset: "props/buildings/fisherman-house-base-blue", targetWidth: 150 },
  { target: "BrainRoomScene", label: "Brain Room", x: (WIDTH_PX * 2) / 6, y: BACK_ROW_Y, asset: "props/buildings/blacksmith-house-blue", targetWidth: 150 },
  { target: "CeoOfficeScene", label: "CEO Office", x: (WIDTH_PX * 3) / 6, y: BACK_ROW_Y, asset: "props/buildings/inn-black", targetWidth: 170 },
  { target: "MeetingRoomScene", label: "Meeting Room", x: (WIDTH_PX * 4) / 6, y: BACK_ROW_Y, asset: "props/buildings/church-red-front", targetWidth: 150 },
  { target: "BreakRoomScene", label: "Break Room", x: (WIDTH_PX * 5) / 6, y: BACK_ROW_Y, asset: "props/buildings/shed-base-red", targetWidth: 150 },
  { target: "SimulationLabScene", label: "Simulation Lab", x: (WIDTH_PX * 1) / 8, y: FRONT_ROW_Y, asset: "props/buildings/greenhouse-wood-front", targetWidth: 130 },
  { target: "HallOfFameScene", label: "Hall of Fame", x: (WIDTH_PX * 3) / 8, y: FRONT_ROW_Y, asset: "props/buildings/windmill", targetWidth: 175 },
  { target: "TradingFloorScene", label: "Trading Floor", x: (WIDTH_PX * 5) / 8, y: FRONT_ROW_Y, asset: "props/buildings/house-5-limestone-base-blue", targetWidth: 190 },
  { target: "PerformanceCenterScene", label: "Performance Center", x: (WIDTH_PX * 7) / 8, y: FRONT_ROW_Y, asset: "props/buildings/barn-base-red", targetWidth: 165 },
];

// The town square sits dead center — horizontally at the map's midpoint
// (where the spawn spine already runs), vertically in the open band
// between the back row's doorsteps (~y160) and the front row's road
// (~y352). A cobblestone plaza (see buildTownSquare()) fills this
// rectangle; the pond sits in the middle of it, like a fountain.
const PLAZA_CENTER = { x: WIDTH_PX / 2, y: 264 };
const PLAZA_COLS: [number, number] = [WIDTH_TILES / 2 - 6, WIDTH_TILES / 2 + 6]; // 12 tiles wide
const PLAZA_ROWS: [number, number] = [13, 20]; // 8 tiles tall — clear of both rows' roads

const NEWSPAPER_STAND = { x: PLAZA_COLS[1] * TILE_SIZE + TILE_SIZE * 6, y: PLAZA_CENTER.y };
const POND = { x: PLAZA_CENTER.x - TILE_SIZE * 2, y: PLAZA_CENTER.y - TILE_SIZE * 1.5 };

// Benches flanking the pond on all four corners, inside the plaza.
const BENCH_SPOTS: [number, number][] = [
  [POND.x - 50, POND.y + 8],
  [POND.x + TILE_SIZE * 4 + 50, POND.y + 8],
  [POND.x - 50, POND.y + TILE_SIZE * 3 - 8],
  [POND.x + TILE_SIZE * 4 + 50, POND.y + TILE_SIZE * 3 - 8],
];

// Two lampposts per row, at the plaza-facing midpoints between doors (never
// on a door's own x column, and never on the road's y — a lamppost sitting
// on the walkway tile would block the path it's supposed to light).
const LAMPPOST_SPOTS: [number, number][] = [
  [WIDTH_PX * 0.25, 145], // back row: between the road (ends y128) and the building base (y160)
  [WIDTH_PX * 0.75, 145],
  [WIDTH_PX * 0.25, 340], // front row: between the plaza and the road (starts y352)
  [WIDTH_PX * 0.75, 340],
];

// Extra tree variety near the plaza, on top of buildDecor()'s six corner oaks.
const EXTRA_TREE_SPOTS: [number, number, string][] = [
  [WIDTH_PX * 0.5 - 260, 250, "props/small-spruce-tree"],
  [WIDTH_PX * 0.5 + 260, 250, "props/small-fruit-tree"],
];

// Frame indices into the 7-column "props/outdoor-decor-free"
// tileset (16x16 cells) — picked by visually inspecting the sheet, not
// guessed, since most of it is farming/mining decor that doesn't read well
// out of context. These four are the only cells that render as clean,
// self-contained sprites at a glance (see LobbyScene's landscaping notes).
const DECOR_LEAF_SPRIG = 0;
const DECOR_FLOWER_WHITE = 7;
const DECOR_FLOWER_RED = 56;
const DECOR_FLOWER_YELLOW = 57;
const DECOR_STUMP = 14;

/** The HQ courtyard: two staggered rows of distinct buildings around a central plaza (pond + newspaper stand), camera-followed player, ambient decoration. */
export class LobbyScene extends Phaser.Scene {
  private player!: PlayerController;
  private doors: { zone: Phaser.GameObjects.Zone; def: DoorDef }[] = [];
  private obstacles!: Phaser.Physics.Arcade.StaticGroup;
  private newspaperZone!: Phaser.GameObjects.Zone;

  constructor() {
    super("LobbyScene");
  }

  create(data: SceneTransitionData): void {
    this.physics.world.setBounds(0, 0, WIDTH_PX, HEIGHT_PX);
    this.obstacles = this.physics.add.staticGroup();

    createGroundLayer(this, {
      tileAssetId: "tilesets/grass-middle",
      tileSize: TILE_SIZE,
      widthTiles: WIDTH_TILES,
      heightTiles: HEIGHT_TILES,
    });

    this.buildPath();
    this.buildTownSquare();
    this.buildPond();
    this.buildDecor();
    this.buildBuildings();
    this.buildLandscaping();
    this.buildPondDecor();
    this.buildAmbientAnimals();
    this.buildBenches();
    this.buildLampposts();
    this.buildNewspaperStand();

    const spawnX = data?.spawnX ?? WIDTH_PX / 2;
    const spawnY = data?.spawnY ?? HEIGHT_PX - TILE_SIZE * 4;
    this.player = new PlayerController(this, spawnX, spawnY);
    this.physics.add.collider(this.player.sprite, this.obstacles);

    CameraManager.follow(this, this.player.sprite, { x: 0, y: 0, width: WIDTH_PX, height: HEIGHT_PX });
    CameraManager.fadeIn(this);

    GameManager.getInstance()?.setPlayerTransform({ scene: "LobbyScene", x: spawnX, y: spawnY, facing: "down" });
    EventBus.emit("scene:ready", { scene: "LobbyScene" });
    EventBus.emit("room:entered", { scene: "LobbyScene" });
  }

  update(): void {
    this.player.update();
    GameManager.getInstance()?.setPlayerTransform({
      scene: "LobbyScene",
      x: this.player.x,
      y: this.player.y,
      facing: this.player.currentFacing,
    });

    if (this.player.pausePressed) {
      GameManager.getInstance()?.togglePause();
    }

    for (const { zone, def } of this.doors) {
      const near = Phaser.Geom.Intersects.RectangleToRectangle(this.player.sprite.getBounds(), zone.getBounds());
      if (near && this.player.interactPressed) {
        this.registry.set("lobbyReturnX", def.x);
        this.registry.set("lobbyReturnY", def.y + TILE_SIZE * 2);
        EventBus.emit("room:left", { scene: "LobbyScene" });
        // No spawnX/spawnY: the target room falls back to its own default spawn point (near its exit door).
        SceneManager.goTo(this, def.target, { fromScene: "LobbyScene" });
        return;
      }
    }

    if (this.player.interactPressed) {
      const nearPaper = Phaser.Geom.Intersects.RectangleToRectangle(this.player.sprite.getBounds(), this.newspaperZone.getBounds());
      if (nearPaper) {
        EventBus.emit("ui:newspaper", { open: true });
      }
    }
  }

  private buildPath(): void {
    const map = this.make.tilemap({ tileWidth: TILE_SIZE, tileHeight: TILE_SIZE, width: WIDTH_TILES, height: HEIGHT_TILES });
    const tileset = map.addTilesetImage("tilesets/path-middle", "tilesets/path-middle", TILE_SIZE, TILE_SIZE, 0, 0);
    if (!tileset) return;
    const layer = map.createBlankLayer("path", tileset, 0, 0);
    if (!layer) return;
    // One walkway per row (back row doors, front row doors), plus a vertical
    // spine connecting the spawn point up through both rows.
    const backRowTile = (BACK_ROW_Y + TILE_SIZE) / TILE_SIZE;
    const frontRowTile = (FRONT_ROW_Y + TILE_SIZE) / TILE_SIZE;
    for (let x = 4; x < WIDTH_TILES - 4; x++) {
      layer.putTileAt(0, x, backRowTile);
      layer.putTileAt(0, x, frontRowTile);
    }
    const centerCol = Math.floor(WIDTH_TILES / 2);
    for (let y = backRowTile; y < HEIGHT_TILES - 2; y++) layer.putTileAt(0, centerCol, y);

    // A short spur straight from the road to each building's doorstep — the
    // road already runs at def.y+16 (one tile below the row) and every
    // building's base sits at def.y+64 (see buildBuildings()), a 2-tile gap
    // that otherwise reads as "the road passes by" rather than "the road
    // leads to the door."
    for (const def of DOORS) {
      const doorCol = Math.round(def.x / TILE_SIZE);
      const rowTile = def.y === BACK_ROW_Y ? backRowTile : frontRowTile;
      const baseTile = Math.floor((def.y + 64) / TILE_SIZE);
      for (let y = rowTile + 1; y < baseTile; y++) layer.putTileAt(0, doorCol, y);
    }
  }

  /**
   * A cobblestone town square at the map's dead center, replacing the
   * stretch of dirt spine that used to run straight through — a real town
   * has a paved center, not just a corridor. Drawn on its own layer after
   * buildPath() so it overlaps/widens the spine's center section rather
   * than requiring the spine to route around it; the pond (built right
   * after this) then sits in the middle of the square like a fountain.
   */
  private buildTownSquare(): void {
    const [colStart, colEnd] = PLAZA_COLS;
    const [rowStart, rowEnd] = PLAZA_ROWS;
    const cols = colEnd - colStart;
    const rows = rowEnd - rowStart;
    const map = this.make.tilemap({ tileWidth: TILE_SIZE, tileHeight: TILE_SIZE, width: cols, height: rows });
    const tileset = map.addTilesetImage("tilesets/cobble-path", "tilesets/cobble-path", TILE_SIZE, TILE_SIZE, 0, 0);
    if (!tileset) return;
    const layer = map.createBlankLayer("town-square", tileset, 0, 0);
    if (!layer) return;
    layer.fill(0);
    layer.setPosition(colStart * TILE_SIZE, rowStart * TILE_SIZE);
  }

  private buildPond(): void {
    const map = this.make.tilemap({ tileWidth: TILE_SIZE, tileHeight: TILE_SIZE, width: 4, height: 3 });
    const tileset = map.addTilesetImage("tilesets/water-middle", "tilesets/water-middle", TILE_SIZE, TILE_SIZE, 0, 0);
    if (!tileset) return;
    const layer = map.createBlankLayer("pond", tileset, 0, 0);
    if (!layer) return;
    layer.fill(0);
    layer.setPosition(POND.x, POND.y);
  }

  private buildDecor(): void {
    const trees: [number, number][] = [
      [24, 40],
      [WIDTH_PX - 32, 40],
      [24, HEIGHT_PX / 2],
      [WIDTH_PX - 32, HEIGHT_PX / 2],
      [24, HEIGHT_PX - 40],
      [WIDTH_PX - 32, HEIGHT_PX - 40],
    ];
    for (const [x, y] of trees) {
      const tree = this.add.image(x, y, "props/oak-tree").setScale(1.4).setDepth(2);
      this.obstacles.add(tree);
      const body = tree.body as Phaser.Physics.Arcade.StaticBody;
      body.setSize(tree.displayWidth * 0.5, tree.displayHeight * 0.3);
      body.setOffset((tree.displayWidth * 0.5) / 2, tree.displayHeight * 0.6);
    }

    // A couple of non-oak trees near the plaza for variety, from the Cute
    // Fantasy premium pack — a spruce and a fruit tree, each the middle
    // frame cropped from a 3-frame sheet (see animation-config.json).
    for (const [x, y, asset] of EXTRA_TREE_SPOTS) {
      const tree = this.add.image(x, y, asset).setScale(1.6).setDepth(2);
      this.obstacles.add(tree);
      const body = tree.body as Phaser.Physics.Arcade.StaticBody;
      body.setSize(tree.displayWidth * 0.5, tree.displayHeight * 0.25);
      body.setOffset((tree.displayWidth * 0.5) / 2, tree.displayHeight * 0.7);
    }

    const fence = this.add.image(TILE_SIZE * 4, HEIGHT_PX - TILE_SIZE * 3, "props/fences").setScale(1.2).setDepth(2);
    this.obstacles.add(fence);
    const fenceBody = fence.body as Phaser.Physics.Arcade.StaticBody;
    fenceBody.setSize(fence.displayWidth * 0.85, fence.displayHeight * 0.5);
    fenceBody.setOffset(fence.displayWidth * 0.075, fence.displayHeight * 0.4);

    const chest = this.add.image(WIDTH_PX - TILE_SIZE * 4, HEIGHT_PX - TILE_SIZE * 3, "props/chest").setScale(1.3).setDepth(2);
    this.obstacles.add(chest);
    const chestBody = chest.body as Phaser.Physics.Arcade.StaticBody;
    chestBody.setSize(chest.displayWidth * 0.8, chest.displayHeight * 0.7);
    chestBody.setOffset(chest.displayWidth * 0.1, chest.displayHeight * 0.25);
  }

  /** Registers (once) and returns the Phaser frame name for one 16x16 cell of the decor tileset. */
  private decorFrame(index: number): string {
    const key = "props/outdoor-decor-free";
    const frameKey = `decor-${index}`;
    const texture = this.textures.get(key);
    if (!texture.has(frameKey)) {
      const cols = 7;
      const col = index % cols;
      const row = Math.floor(index / cols);
      texture.add(frameKey, 0, col * 16, row * 16, 16, 16);
    }
    return frameKey;
  }

  private addDecor(x: number, y: number, index: number, scale = 1.4): void {
    this.add.image(x, y, "props/outdoor-decor-free", this.decorFrame(index)).setScale(scale).setDepth(2);
  }

  /** Flower beds flanking each building's entrance and a scatter of leaf sprigs/stumps in the plaza — ground-level texture so the courtyard doesn't read as flat grass. Walk-over only, no collision, same as the tree canopy overhang. */
  private buildLandscaping(): void {
    // Every building is scaled and positioned so its bottom edge lands at
    // def.y + 64 regardless of its native art size (see buildBuildings()).
    // Flowers need to sit below that — not just below the door's interact
    // zone — or the house's own depth-3 artwork draws over them despite
    // being on lower depth, since Phaser depth-sorts whole sprites, not
    // per-pixel against lower-depth objects under their bounding box.
    const flowerVariants = [DECOR_FLOWER_WHITE, DECOR_FLOWER_RED, DECOR_FLOWER_YELLOW];
    DOORS.forEach((def, i) => {
      const variant = flowerVariants[i % flowerVariants.length]!;
      this.addDecor(def.x - 26, def.y + TILE_SIZE * 4.6, variant);
      this.addDecor(def.x + 26, def.y + TILE_SIZE * 4.6, variant);
    });

    const sprigSpots: [number, number][] = [
      [WIDTH_PX * 0.42, 200],
      [WIDTH_PX * 0.58, 250],
      [WIDTH_PX * 0.5, 160],
      [TILE_SIZE * 7, HEIGHT_PX - TILE_SIZE * 5],
      [WIDTH_PX - TILE_SIZE * 7, HEIGHT_PX - TILE_SIZE * 5],
      [WIDTH_PX * 0.5, HEIGHT_PX - TILE_SIZE * 5],
    ];
    for (const [x, y] of sprigSpots) this.addDecor(x, y, DECOR_LEAF_SPRIG, 1.2);

    // Clear of the town square's cobblestone (see buildTownSquare()) — this
    // is grass decor, not a plaza fixture.
    this.addDecor(POND.x + TILE_SIZE * 3, POND.y - TILE_SIZE * 4, DECOR_STUMP);
    this.addDecor(WIDTH_PX - TILE_SIZE * 5, 200, DECOR_STUMP);
  }

  /**
   * Animated pond life from the Cute Fantasy premium pack — lilypads
   * bobbing mid-water, cattails and a grass tuft swaying at the bank, a
   * small wooden dock jutting off the east edge, two ducks, and flowers
   * ringing the shore. Walk-over only, no collision, same as the flower
   * beds — the pond tilemap itself has no collision either (pre-existing;
   * out of scope here), so a dock or duck standing partly "in" the water
   * doesn't block anything that wasn't already walkable.
   */
  private buildPondDecor(): void {
    const playAnim = (x: number, y: number, assetId: string, animName: string, depth: number): void => {
      this.add.sprite(x, y, assetId).setDepth(depth).play(AssetLoader.animKey(assetId, animName));
    };

    // Pond spans POND.x..POND.x+64, POND.y..POND.y+48 (4x3 tiles) — lilypads
    // sit inside that rectangle, cattails just outside its left/right edges.
    playAnim(POND.x + TILE_SIZE * 1.4, POND.y + TILE_SIZE * 1, "animations/lillypad-green-anim", "bob", 1);
    playAnim(POND.x + TILE_SIZE * 2.6, POND.y + TILE_SIZE * 1.8, "animations/lillypad-green-anim", "bob", 1);
    playAnim(POND.x - 8, POND.y + TILE_SIZE * 1, "animations/cattail-anim", "sway", 2);
    playAnim(POND.x + TILE_SIZE * 4 + 8, POND.y + TILE_SIZE * 1.5, "animations/cattail-anim", "sway", 2);
    playAnim(POND.x + TILE_SIZE * 1.5, POND.y - TILE_SIZE * 0.8, "animations/grass-sway-anim", "sway", 2);

    // Dock — cropped from the bridge-wood sheet, rotated to jut out from
    // the east bank into the water rather than span a gap.
    this.add.image(POND.x + TILE_SIZE * 4 + 6, POND.y + TILE_SIZE * 2, "props/dock").setAngle(90).setScale(1.1).setDepth(1);

    // Two ducks — one bobbing on the water, one preening on the bank.
    this.add.image(POND.x + TILE_SIZE * 1, POND.y + TILE_SIZE * 2.3, "characters/animals/duck/duck-idle").setScale(0.85).setDepth(1);
    this.add.image(POND.x + TILE_SIZE * 3.5, POND.y + TILE_SIZE * 3.4, "characters/animals/duck/duck-idle").setScale(0.85).setFlipX(true).setDepth(2);

    // Flowers ringing the shore, using the same decor tileset as the
    // building flower beds.
    this.addDecor(POND.x + TILE_SIZE * 0.5, POND.y - TILE_SIZE * 0.5, DECOR_FLOWER_WHITE, 1.1);
    this.addDecor(POND.x + TILE_SIZE * 2, POND.y + TILE_SIZE * 3.6, DECOR_FLOWER_YELLOW, 1.1);
    this.addDecor(POND.x - TILE_SIZE * 0.5, POND.y + TILE_SIZE * 2.5, DECOR_FLOWER_RED, 1.1);
  }

  /** A previously-unused free-pack asset put to real use: one ambient chicken grazing near the Barn, not a placeholder — see chicken-idle's note in animation-config.json for why it's a cropped frame rather than the raw sheet. */
  private buildAmbientAnimals(): void {
    const barn = DOORS.find((d) => d.target === "PerformanceCenterScene")!;
    this.add.image(barn.x + 46, barn.y + 76, "characters/animals/chicken/chicken-idle").setScale(1.1).setDepth(2);
  }

  /** Plaza seating — walk-blocking, like the trees and fence, since a bench is a solid object you'd otherwise phase through. */
  private buildBenches(): void {
    for (const [x, y] of BENCH_SPOTS) {
      const bench = this.add.image(x, y, "props/bench").setScale(1.3).setDepth(2);
      this.obstacles.add(bench);
      const body = bench.body as Phaser.Physics.Arcade.StaticBody;
      body.setSize(bench.displayWidth * 0.85, bench.displayHeight * 0.5);
      body.setOffset(bench.displayWidth * 0.075, bench.displayHeight * 0.4);
    }
  }

  /** Lampposts flanking both path rows, each with a gently flickering flame. Thin obstacle — you can't walk through the post. */
  private buildLampposts(): void {
    for (const [x, y] of LAMPPOST_SPOTS) {
      const lamp = this.add
        .sprite(x, y, "animations/lamppost-glow-anim")
        .setScale(0.85)
        .setDepth(2)
        .play(AssetLoader.animKey("animations/lamppost-glow-anim", "flicker"));
      this.obstacles.add(lamp);
      const body = lamp.body as Phaser.Physics.Arcade.StaticBody;
      body.setSize(lamp.displayWidth * 0.3, lamp.displayHeight * 0.2);
      body.setOffset(lamp.displayWidth * 0.35, lamp.displayHeight * 0.75);
    }
  }

  private buildBuildings(): void {
    for (const def of DOORS) {
      const building = this.add.image(def.x, def.y, def.asset).setDepth(3);
      const scale = def.targetWidth / building.width;
      building.setScale(scale);
      // Every building's bottom edge lands on the same baseline (def.y + 64)
      // regardless of its native art size, so buildings of very different
      // heights (a windmill tower vs. a low shed) still sit on the same
      // "ground line" instead of floating at different depths.
      building.setY(def.y + 64 - building.displayHeight / 2);
      this.obstacles.add(building);

      // Collision covers the upper-middle mass of the sprite (not the full
      // footprint) so the doorway — and the interact zone in front of it —
      // stays walkable regardless of exactly how each building's art is
      // laid out within its canvas.
      const body = building.body as Phaser.Physics.Arcade.StaticBody;
      body.setSize(building.displayWidth * 0.7, building.displayHeight * 0.45);
      body.setOffset(building.displayWidth * 0.15, building.displayHeight * 0.05);
      body.updateCenter();

      const topEdge = def.y + 64 - building.displayHeight;

      // Both labels float above the roof rather than one sitting on the
      // door artwork — "[E] Enter" used to overlap the house's own painted
      // door, which read as cluttered up close; stacking it just above the
      // name label keeps both legible against the sky instead of the busy
      // building sprite underneath. Positioned relative to each building's
      // own computed roofline (topEdge) rather than a fixed offset, since
      // buildings now vary a lot in height.
      this.add
        .text(def.x, topEdge - 24, "[E] Enter", {
          fontFamily: "monospace",
          fontSize: "8px",
          color: "#d9a441",
          backgroundColor: "#241c14aa",
          padding: { x: 4, y: 1 },
        })
        .setOrigin(0.5)
        .setDepth(4);

      this.add
        .text(def.x, topEdge - 10, def.label, {
          fontFamily: "monospace",
          fontSize: "9px",
          color: "#f4e6c9",
          backgroundColor: "#241c14aa",
          padding: { x: 4, y: 2 },
        })
        .setOrigin(0.5)
        .setDepth(4);

      const zone = createZone(this, def.x, def.y + TILE_SIZE, TILE_SIZE * 2, TILE_SIZE);
      this.doors.push({ zone, def });
    }
  }

  private buildNewspaperStand(): void {
    const { x, y } = NEWSPAPER_STAND;
    this.add.rectangle(x, y, 6, 22, 0x5c3b20).setDepth(2); // post
    const board = this.add.rectangle(x, y - 16, 22, 16, 0xf4e6c9).setStrokeStyle(1, 0x241c14).setDepth(3);
    this.obstacles.add(board);
    const boardBody = board.body as Phaser.Physics.Arcade.StaticBody;
    boardBody.setSize(22, 16);
    for (let i = 0; i < 3; i++) {
      this.add.rectangle(x, y - 21 + i * 3, 16, 1, 0x241c14, 0.6).setDepth(4);
    }
    this.add
      .text(x, y + 14, "TradeTown Daily\n[E] Read", {
        fontFamily: "monospace",
        fontSize: "7px",
        color: "#d9a441",
        align: "center",
      })
      .setOrigin(0.5, 0)
      .setDepth(4);

    this.newspaperZone = createZone(this, x, y + TILE_SIZE, TILE_SIZE * 1.5, TILE_SIZE);
  }
}
