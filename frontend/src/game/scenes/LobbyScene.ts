import Phaser from "phaser";
import type { SceneId } from "@/types";
import { PlayerController } from "@/game/entities/PlayerController";
import { CameraManager } from "@/game/systems/CameraManager";
import { SceneManager, type SceneTransitionData } from "@/game/systems/SceneManager";
import { createGroundLayer, createZone } from "@/game/systems/TileWorld";
import { EventBus } from "@/game/systems/EventBus";
import { GameManager } from "@/game/systems/GameManager";

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
  { target: "ScoutOfficeScene", label: "Scout Office", x: (WIDTH_PX * 1) / 6, y: BACK_ROW_Y, asset: "outdoor-decoration/buildings/fisherman-house-base-blue", targetWidth: 150 },
  { target: "BrainRoomScene", label: "Brain Room", x: (WIDTH_PX * 2) / 6, y: BACK_ROW_Y, asset: "outdoor-decoration/buildings/blacksmith-house-blue", targetWidth: 150 },
  { target: "CeoOfficeScene", label: "CEO Office", x: (WIDTH_PX * 3) / 6, y: BACK_ROW_Y, asset: "outdoor-decoration/buildings/inn-black", targetWidth: 170 },
  { target: "MeetingRoomScene", label: "Meeting Room", x: (WIDTH_PX * 4) / 6, y: BACK_ROW_Y, asset: "outdoor-decoration/buildings/church-red-front", targetWidth: 150 },
  { target: "BreakRoomScene", label: "Break Room", x: (WIDTH_PX * 5) / 6, y: BACK_ROW_Y, asset: "outdoor-decoration/buildings/shed-base-red", targetWidth: 150 },
  { target: "SimulationLabScene", label: "Simulation Lab", x: (WIDTH_PX * 1) / 8, y: FRONT_ROW_Y, asset: "outdoor-decoration/buildings/greenhouse-wood-front", targetWidth: 130 },
  { target: "HallOfFameScene", label: "Hall of Fame", x: (WIDTH_PX * 3) / 8, y: FRONT_ROW_Y, asset: "outdoor-decoration/buildings/windmill", targetWidth: 175 },
  { target: "TradingFloorScene", label: "Trading Floor", x: (WIDTH_PX * 5) / 8, y: FRONT_ROW_Y, asset: "outdoor-decoration/buildings/house-5-limestone-base-blue", targetWidth: 190 },
  { target: "PerformanceCenterScene", label: "Performance Center", x: (WIDTH_PX * 7) / 8, y: FRONT_ROW_Y, asset: "outdoor-decoration/buildings/barn-base-red", targetWidth: 165 },
];

const NEWSPAPER_STAND = { x: WIDTH_PX / 2 + TILE_SIZE * 6, y: 224 };
const POND = { x: TILE_SIZE * 3, y: 224 };

// Frame indices into the 7-column "outdoor-decoration/outdoor-decor-free"
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
      tileAssetId: "tiles/grass-middle",
      tileSize: TILE_SIZE,
      widthTiles: WIDTH_TILES,
      heightTiles: HEIGHT_TILES,
    });

    this.buildPath();
    this.buildPond();
    this.buildDecor();
    this.buildBuildings();
    this.buildLandscaping();
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
    const tileset = map.addTilesetImage("tiles/path-middle", "tiles/path-middle", TILE_SIZE, TILE_SIZE, 0, 0);
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
  }

  private buildPond(): void {
    const map = this.make.tilemap({ tileWidth: TILE_SIZE, tileHeight: TILE_SIZE, width: 4, height: 3 });
    const tileset = map.addTilesetImage("tiles/water-middle", "tiles/water-middle", TILE_SIZE, TILE_SIZE, 0, 0);
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
      const tree = this.add.image(x, y, "outdoor-decoration/oak-tree").setScale(1.4).setDepth(2);
      this.obstacles.add(tree);
      const body = tree.body as Phaser.Physics.Arcade.StaticBody;
      body.setSize(tree.displayWidth * 0.5, tree.displayHeight * 0.3);
      body.setOffset((tree.displayWidth * 0.5) / 2, tree.displayHeight * 0.6);
    }

    const fence = this.add.image(TILE_SIZE * 4, HEIGHT_PX - TILE_SIZE * 3, "outdoor-decoration/fences").setScale(1.2).setDepth(2);
    this.obstacles.add(fence);
    const fenceBody = fence.body as Phaser.Physics.Arcade.StaticBody;
    fenceBody.setSize(fence.displayWidth * 0.85, fence.displayHeight * 0.5);
    fenceBody.setOffset(fence.displayWidth * 0.075, fence.displayHeight * 0.4);

    const chest = this.add.image(WIDTH_PX - TILE_SIZE * 4, HEIGHT_PX - TILE_SIZE * 3, "outdoor-decoration/chest").setScale(1.3).setDepth(2);
    this.obstacles.add(chest);
    const chestBody = chest.body as Phaser.Physics.Arcade.StaticBody;
    chestBody.setSize(chest.displayWidth * 0.8, chest.displayHeight * 0.7);
    chestBody.setOffset(chest.displayWidth * 0.1, chest.displayHeight * 0.25);
  }

  /** Registers (once) and returns the Phaser frame name for one 16x16 cell of the decor tileset. */
  private decorFrame(index: number): string {
    const key = "outdoor-decoration/outdoor-decor-free";
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
    this.add.image(x, y, "outdoor-decoration/outdoor-decor-free", this.decorFrame(index)).setScale(scale).setDepth(2);
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

    this.addDecor(POND.x + TILE_SIZE * 3, POND.y - TILE_SIZE * 2, DECOR_STUMP);
    this.addDecor(WIDTH_PX - TILE_SIZE * 5, 200, DECOR_STUMP);
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
