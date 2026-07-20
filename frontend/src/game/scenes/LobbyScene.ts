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
  /**
   * Native (unscaled) pixel offset of the door's true center from the
   * source art's canvas center — most of these buildings have the door
   * dead center, but a few don't (Blacksmith_House_Blue's canvas is a
   * house-plus-forge assembly with the door well left of the bounding
   * box's midpoint; Fisherman_House_Base_Blue/Shed_Base_Red both have a
   * door a few pixels left of center). Measured directly from each
   * source PNG. Anything meant to line up with the actual door (the path
   * spur, the interact zone, flanking flowers) should go through
   * doorWorldX() rather than def.x when this is set.
   */
  doorOffsetX?: number;
}

// Two staggered rows, clustered toward the map's center third rather than
// spread edge-to-edge — a reference screenshot of a similar HQ-town layout
// (dense building cluster, hedge-lined courtyard, park margins) called for
// a tighter village footprint than the original evenly-spaced rows. CEO
// Office anchors the back row at dead center, the same "hero building
// facing the square" role the reference's Command Center plays; every
// other position is spaced out symmetrically from there with enough gap
// for each building's targetWidth. The ~400px margins this frees up on
// both sides (unused before) now hold the hedge/fountain/market-stall
// accents — see buildHedges()/buildCourtyardAccents(). Every building is a
// distinct piece from the Cute Fantasy premium pack's Unique_Buildings set
// (or a named house variant), not the same sprite re-tinted nine times.
const DOORS: DoorDef[] = [
  { target: "ScoutOfficeScene", label: "Scout Office", x: 464, y: BACK_ROW_Y, asset: "props/buildings/fisherman-house-base-blue", targetWidth: 150, doorOffsetX: -9 },
  { target: "BrainRoomScene", label: "Brain Room", x: 664, y: BACK_ROW_Y, asset: "props/buildings/blacksmith-house-blue", targetWidth: 150, doorOffsetX: -43 },
  { target: "CeoOfficeScene", label: "CEO Office", x: WIDTH_PX / 2, y: BACK_ROW_Y, asset: "props/buildings/inn-black", targetWidth: 170 },
  { target: "MeetingRoomScene", label: "Meeting Room", x: 1064, y: BACK_ROW_Y, asset: "props/buildings/church-red-front", targetWidth: 150 },
  { target: "BreakRoomScene", label: "Break Room", x: 1264, y: BACK_ROW_Y, asset: "props/buildings/shed-base-red", targetWidth: 150, doorOffsetX: -9 },
  { target: "SimulationLabScene", label: "Simulation Lab", x: 330, y: FRONT_ROW_Y, asset: "props/buildings/greenhouse-wood-front", targetWidth: 130 },
  // windmill.png's source file turned out to be the tower and the sail
  // assembly side by side, not pre-composited — the sails rendered as a
  // disconnected chunk floating next to the tower instead of mounted on
  // it. Fixed at the asset level: recomposited (sails layered onto the
  // tower at their shared native Y-coordinate, then trimmed to content).
  // New native size is 54x111 (was 128x112), hence the much narrower
  // targetWidth here than its neighbors.
  // Hall of Fame and Trading Floor sit at y=336, inside the plaza's own
  // vertical span (160-352) by design — but that means, unlike the back
  // row, they can visually collide with the hedge/lamppost pair flanking
  // the plaza's east/west edges if placed too close. Kept clear of both
  // (lamppost sits at PLAZA_COLS[0]*16-24 / PLAZA_COLS[1]*16+24 = 696/1032)
  // with a comfortable margin, rather than hugging the square like the
  // first pass here did.
  { target: "HallOfFameScene", label: "Hall of Fame", x: 580, y: FRONT_ROW_Y, asset: "props/buildings/windmill", targetWidth: 78 },
  { target: "TradingFloorScene", label: "Trading Floor", x: 1180, y: FRONT_ROW_Y, asset: "props/buildings/house-5-limestone-base-blue", targetWidth: 190 },
  { target: "PerformanceCenterScene", label: "Performance Center", x: 1430, y: FRONT_ROW_Y, asset: "props/buildings/barn-base-red", targetWidth: 165 },
];

// The town square sits dead center, filling the entire open gap between
// the back row's building baseline (tile row 10, y160 — see
// buildBuildings()) and the front row's road (tile row 22, y352) — the
// plaza's top and bottom edges land exactly on those, no leftover grass
// strip. 18 tiles wide, comfortably clear of the nearest doors on either
// row (Brain Room/Meeting Room on the back row, Hall of Fame/Trading
// Floor on the front) with room to spare.
const PLAZA_COLS: [number, number] = [WIDTH_TILES / 2 - 9, WIDTH_TILES / 2 + 9]; // 18 tiles wide
const PLAZA_ROWS: [number, number] = [10, 22]; // 12 tiles tall, y160-352
const PLAZA_CENTER = { x: WIDTH_PX / 2, y: (((PLAZA_ROWS[0] + PLAZA_ROWS[1]) / 2) * TILE_SIZE) };

const NEWSPAPER_STAND = { x: PLAZA_COLS[1] * TILE_SIZE + TILE_SIZE * 3, y: PLAZA_CENTER.y };

// The pond is a single pre-composed graphic (props/pond-curved, an organic
// jagged-bank shape), not a rectangle of water tiles — see buildPond(). It's
// centered on the plaza and scaled up from its native 48x48. Bumped from
// 3.6 to 4.27 (roughly +2 tiles of display width) at the user's request.
const POND_CENTER = PLAZA_CENTER;
const POND_SCALE = 4.27;

// Benches flanking the pond on all four corners, inside the plaza — outside
// the pond's jagged bank (its outermost spikes reach ~81px from center at
// this scale) but clear of the hedge lining the plaza's own edges (at
// PLAZA_COLS[0]*16-8 / PLAZA_COLS[1]*16+8, only ~152px from POND_CENTER.x —
// an earlier pass scaled these offsets up along with the pond itself and
// pushed them into the hedge; reverted to the original, already-clear
// values instead, since the pond's widening left plenty of room without it).
const BENCH_SPOTS: [number, number][] = [
  [POND_CENTER.x - 115, POND_CENTER.y - 70],
  [POND_CENTER.x + 115, POND_CENTER.y - 70],
  [POND_CENTER.x - 115, POND_CENTER.y + 70],
  [POND_CENTER.x + 115, POND_CENTER.y + 70],
];

// Two lampposts flanking the square's east/west entrances, just outside
// its paved edge (see buildTownSquare()) — not mid-gap between the two
// rows like before, since the enlarged square now leaves no such gap on
// the front-row side.
const LAMPPOST_SPOTS: [number, number][] = [
  [PLAZA_COLS[0] * TILE_SIZE - 24, PLAZA_CENTER.y],
  [PLAZA_COLS[1] * TILE_SIZE + 24, PLAZA_CENTER.y],
];

// Extra tree variety near the plaza, on top of buildDecor()'s six corner
// oaks. Kept clear of Hall of Fame (x:541-619) and Trading Floor
// (x:1085-1275) — the original symmetric ±260 offsets landed inside Hall
// of Fame's footprint once the front row's buildings moved closer to the
// plaza (see DOORS' comment), half-hiding the spruce tree behind its roof.
const EXTRA_TREE_SPOTS: [number, number, string][] = [
  [500, 250, "props/small-spruce-tree"],
  [1310, 250, "props/small-fruit-tree"],
];

// A low hedge border tracing the square's east/west edges — see
// buildHedges(). props/hedge-tiles' narrow column-0 pieces: frame 0 = top
// cap, 4 = fill, 12 = bottom cap (see animation-config.json). Two rows are
// skipped at the plaza's vertical midpoint on each side, leaving a gateway
// where the existing lamppost already marks the entrance rather than
// having the hedge run straight through it.
const HEDGE_CAP_TOP = 0;
const HEDGE_FILL = 4;
const HEDGE_CAP_BOTTOM = 12;
const HEDGE_GATE_ROWS = [5, 6];

// Fountains flanking the courtyard out in the park margin the tighter
// building cluster freed up (see DOORS' comment) — a flat stone basin on
// one side, the taller spouting tier on the other (props/fountain frames
// 0/1), echoing a reference screenshot's courtyard fountain.
const FOUNTAIN_SPOTS: [number, number, number][] = [
  [200, 150, 1],
  [WIDTH_PX - 200, 150, 0],
];

// Market stalls south of Trading Floor's entrance — echoes the reference
// screenshot's stall row outside its Armory building. props/market-stalls
// frames are 4 color variants (red/green/blue/orange).
const TRADING_FLOOR_DOOR = DOORS.find((d) => d.target === "TradingFloorScene")!;
const MARKET_STALL_SPOTS: [number, number, number][] = [
  [TRADING_FLOOR_DOOR.x - 55, TRADING_FLOOR_DOOR.y + 90, 0],
  [TRADING_FLOOR_DOOR.x - 5, TRADING_FLOOR_DOOR.y + 90, 2],
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
    this.buildHedges();
    this.buildCourtyardAccents();
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

  /**
   * The road network — a cool grey square-tile pattern that reads as
   * cobblestone (tilesets/cobblestone-grey, the same tile the town square
   * uses), cropped from a user-supplied reference sheet. Replaced a
   * warm-tan dirt path the user tried and didn't like. One walkway per
   * row plus a vertical spine connecting the spawn point up through both
   * rows and into the square.
   */
  private buildPath(): void {
    const map = this.make.tilemap({ tileWidth: TILE_SIZE, tileHeight: TILE_SIZE, width: WIDTH_TILES, height: HEIGHT_TILES });
    const tileset = map.addTilesetImage("tilesets/cobblestone-grey", "tilesets/cobblestone-grey", TILE_SIZE, TILE_SIZE, 0, 0);
    if (!tileset) return;
    const layer = map.createBlankLayer("path", tileset, 0, 0);
    if (!layer) return;
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
      const doorCol = Math.round(this.doorWorldX(def) / TILE_SIZE);
      const rowTile = def.y === BACK_ROW_Y ? backRowTile : frontRowTile;
      const baseTile = Math.floor((def.y + 64) / TILE_SIZE);
      for (let y = rowTile + 1; y < baseTile; y++) layer.putTileAt(0, doorCol, y);
    }
  }

  /**
   * The world-x of a building's actual door, correcting for doorOffsetX
   * on buildings whose door isn't centered in the source art (see
   * DoorDef.doorOffsetX). Scaled by the same targetWidth/native-width
   * ratio buildBuildings() uses to place the sprite itself, so the
   * correction stays accurate regardless of each building's scale.
   */
  private doorWorldX(def: DoorDef): number {
    if (!def.doorOffsetX) return def.x;
    const nativeWidth = this.textures.get(def.asset).getSourceImage().width;
    return def.x + (def.doorOffsetX * def.targetWidth) / nativeWidth;
  }

  /**
   * Widens the road into an actual town square at the map's dead center —
   * without this, the crossroads there would just be a 1-tile-wide
   * intersection instead of a plaza big enough to hold a pond and
   * benches. Drawn on its own layer after buildPath() so it overlaps and
   * widens that section rather than requiring the road to route around
   * it; the pond (built right after this) then sits in the middle like a
   * fountain.
   */
  private buildTownSquare(): void {
    const [colStart, colEnd] = PLAZA_COLS;
    const [rowStart, rowEnd] = PLAZA_ROWS;
    const cols = colEnd - colStart;
    const rows = rowEnd - rowStart;
    const map = this.make.tilemap({ tileWidth: TILE_SIZE, tileHeight: TILE_SIZE, width: cols, height: rows });
    const tileset = map.addTilesetImage("tilesets/cobblestone-grey", "tilesets/cobblestone-grey", TILE_SIZE, TILE_SIZE, 0, 0);
    if (!tileset) return;
    const layer = map.createBlankLayer("town-square", tileset, 0, 0);
    if (!layer) return;
    layer.fill(0);
    layer.setPosition(colStart * TILE_SIZE, rowStart * TILE_SIZE);
  }

  /**
   * A single pre-composed pond graphic rather than a rectangle of water
   * tiles — props/pond-curved is a 48x48 organic jagged-bank shape (see
   * animation-config.json), scaled up, so the pond reads as a real curved
   * pond instead of a flat rectangle of water color.
   */
  private buildPond(): void {
    this.add.image(POND_CENTER.x, POND_CENTER.y, "props/pond-curved").setScale(POND_SCALE).setDepth(1);
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

    // Note: props/fences is a 4-piece tileset (post/rail/lattice/post), not
    // a single sprite — drawing it whole (as an earlier pass here did)
    // shows all four disconnected pieces crammed together, which reads as
    // a random jumble rather than a fence. Left out rather than shipped
    // looking broken; a real fence line would need each piece placed and
    // sliced individually, same as props/outdoor-decor-free's decorFrame().

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
      const doorX = this.doorWorldX(def);
      this.addDecor(doorX - 26, def.y + TILE_SIZE * 4.6, variant);
      this.addDecor(doorX + 26, def.y + TILE_SIZE * 4.6, variant);
    });

    // First two nudged clear of the now-much-larger town square (x:720-1008,
    // y:160-352) — this is grass decor, not a plaza fixture.
    const sprigSpots: [number, number][] = [
      [PLAZA_COLS[0] * TILE_SIZE - 20, 200],
      [PLAZA_COLS[1] * TILE_SIZE + 20, 250],
      [WIDTH_PX * 0.5, 148],
      [TILE_SIZE * 7, HEIGHT_PX - TILE_SIZE * 5],
      [WIDTH_PX - TILE_SIZE * 7, HEIGHT_PX - TILE_SIZE * 5],
      [WIDTH_PX * 0.5, HEIGHT_PX - TILE_SIZE * 5],
    ];
    for (const [x, y] of sprigSpots) this.addDecor(x, y, DECOR_LEAF_SPRIG, 1.2);

    // Clear of the town square's paving (see buildTownSquare()) — this is
    // grass decor, not a plaza fixture.
    this.addDecor(WIDTH_PX * 0.5 - 220, PLAZA_ROWS[0] * TILE_SIZE - 20, DECOR_STUMP);
    this.addDecor(WIDTH_PX - TILE_SIZE * 5, 200, DECOR_STUMP);
  }

  /**
   * Animated pond life from the Cute Fantasy premium pack — lilypads
   * bobbing mid-water, cattails and a grass tuft swaying at the bank, a
   * south-bank dock ramp with a rowboat resting off its end, two ducks,
   * and flowers ringing the shore. All positioned relative to POND_CENTER
   * now that the pond itself is a single scaled image rather than a tile
   * rectangle. Walk-over only, no collision — the pond graphic itself
   * has none either (pre-existing; out of scope here), so the dock, boat,
   * or a duck standing partly "in" the water doesn't block anything that
   * wasn't already walkable.
   */
  private buildPondDecor(): void {
    const playAnim = (x: number, y: number, assetId: string, animName: string, depth: number): void => {
      this.add.sprite(x, y, assetId).setDepth(depth).play(AssetLoader.animKey(assetId, animName));
    };
    const cx = POND_CENTER.x;
    const cy = POND_CENTER.y;

    // Lilypads sit inside the water; cattails and grass just outside the
    // jagged bank. The pond's water is irregular, not circular — its
    // native PNG shows the water region off-center within the 48x48
    // canvas (extends 11-15px from center depending on direction) inside
    // a bank ring reaching out to ~19px at its jagged widest — so these
    // offsets were checked against the actual source pixels (which color
    // sits under each point) rather than assumed from a single "radius."
    playAnim(cx - 28, cy - 14, "animations/lillypad-green-anim", "bob", 1);
    playAnim(cx + 24, cy + 19, "animations/lillypad-green-anim", "bob", 1);
    playAnim(cx - 95, cy - 9, "animations/cattail-anim", "sway", 2);
    playAnim(cx + 95, cy + 14, "animations/cattail-anim", "sway", 2);
    playAnim(cx, cy - 92, "animations/grass-sway-anim", "sway", 2);

    // Dock — cropped from the bridge-wood sheet, left unrotated (its
    // native portrait shape already reads as a ramp) so it runs from the
    // south bank down into the water like a boat launch. Scale and offset
    // checked against the pond's actual water pixels: the north (top) end
    // lands solidly in water, the south end past the bank on grass — an
    // earlier pass here just scaled the pre-widening offset by the same
    // ratio as POND_SCALE and ended up placing the whole dock on dry grass
    // south of the bank instead.
    this.add.image(cx, cy + 35, "props/dock").setScale(1.3).setDepth(1);

    // A small rowboat resting in the water off the dock's water-side end
    // (checked against the source pixels, same reasoning as the dock).
    this.add.image(cx + 25, cy + 5, "props/boat").setScale(1.15).setDepth(1);

    // Two ducks — one bobbing on the water (checked against the source
    // pixels — the scaled-up offset from the pond-widening pass had
    // drifted onto the bank), one preening on the bank as originally
    // designed.
    this.add.image(cx - 43, cy + 5, "characters/animals/duck/duck-idle").setScale(1.2).setDepth(1);
    this.add.image(cx + 33, cy - 52, "characters/animals/duck/duck-idle").setScale(1.2).setFlipX(true).setDepth(2);

    // Flowers ringing the shore, using the same decor tileset as the
    // building flower beds.
    this.addDecor(cx - 10, cy - 119, DECOR_FLOWER_WHITE, 1.1);
    this.addDecor(cx + 104, cy + 90, DECOR_FLOWER_YELLOW, 1.1);
    this.addDecor(cx - 109, cy + 81, DECOR_FLOWER_RED, 1.1);
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

  /**
   * A low hedge wall along the square's east/west edges, with a 2-tile
   * gateway at each lamppost so the border doesn't just run straight
   * through them. Walk-blocking, like a real garden hedge — a thin
   * collision box per tile rather than one for the whole run, so the
   * gateway gap is actually walkable and not blocked by a neighboring
   * tile's oversized body.
   */
  private buildHedges(): void {
    const [colStart, colEnd] = PLAZA_COLS;
    const [rowStart, rowEnd] = PLAZA_ROWS;
    const rows = rowEnd - rowStart;
    const xs = [colStart * TILE_SIZE - TILE_SIZE / 2, colEnd * TILE_SIZE + TILE_SIZE / 2];
    for (const x of xs) {
      for (let i = 0; i < rows; i++) {
        if (HEDGE_GATE_ROWS.includes(i)) continue;
        const beforeGate = i === HEDGE_GATE_ROWS[0]! - 1;
        const afterGate = i === HEDGE_GATE_ROWS[HEDGE_GATE_ROWS.length - 1]! + 1;
        let frame = HEDGE_FILL;
        if (i === 0 || afterGate) frame = HEDGE_CAP_TOP;
        else if (i === rows - 1 || beforeGate) frame = HEDGE_CAP_BOTTOM;

        const y = rowStart * TILE_SIZE + i * TILE_SIZE + TILE_SIZE / 2;
        const hedge = this.add.image(x, y, "props/hedge-tiles", frame).setDepth(2);
        this.obstacles.add(hedge);
        const body = hedge.body as Phaser.Physics.Arcade.StaticBody;
        body.setSize(hedge.displayWidth * 0.8, hedge.displayHeight * 0.8);
        body.setOffset(hedge.displayWidth * 0.1, hedge.displayHeight * 0.1);
      }
    }
  }

  /**
   * Fountains in the park margin the tighter building cluster freed up,
   * and a couple of market stalls outside Trading Floor — courtyard
   * accents echoing a reference screenshot's HQ-town layout. Both are
   * solid props like the benches, not walk-through decor.
   */
  private buildCourtyardAccents(): void {
    for (const [x, y, frame] of FOUNTAIN_SPOTS) {
      const fountain = this.add.image(x, y, "props/fountain", frame).setDepth(2);
      this.obstacles.add(fountain);
      const body = fountain.body as Phaser.Physics.Arcade.StaticBody;
      body.setSize(fountain.displayWidth * 0.75, fountain.displayHeight * 0.5);
      body.setOffset(fountain.displayWidth * 0.125, fountain.displayHeight * 0.4);
    }

    for (const [x, y, frame] of MARKET_STALL_SPOTS) {
      const stall = this.add.image(x, y, "props/market-stalls", frame).setDepth(2);
      this.obstacles.add(stall);
      const body = stall.body as Phaser.Physics.Arcade.StaticBody;
      body.setSize(stall.displayWidth * 0.85, stall.displayHeight * 0.4);
      body.setOffset(stall.displayWidth * 0.075, stall.displayHeight * 0.5);
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

      const zone = createZone(this, this.doorWorldX(def), def.y + TILE_SIZE, TILE_SIZE * 2, TILE_SIZE);
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
