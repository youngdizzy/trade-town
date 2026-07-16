import Phaser from "phaser";
import type { SceneId } from "@/types";
import { PlayerController } from "@/game/entities/PlayerController";
import { CameraManager } from "@/game/systems/CameraManager";
import { SceneManager, type SceneTransitionData } from "@/game/systems/SceneManager";
import { createGroundLayer, createZone } from "@/game/systems/TileWorld";
import { EventBus } from "@/game/systems/EventBus";
import { GameManager } from "@/game/systems/GameManager";

const TILE_SIZE = 16;
const WIDTH_TILES = 30;
const HEIGHT_TILES = 20;
const WIDTH_PX = WIDTH_TILES * TILE_SIZE;
const HEIGHT_PX = HEIGHT_TILES * TILE_SIZE;

interface DoorDef {
  target: SceneId;
  label: string;
  x: number;
  y: number;
  tint: number;
}

const DOORS: DoorDef[] = [
  { target: "ScoutOfficeScene", label: "Scout Office", x: WIDTH_PX * 0.25, y: 96, tint: 0x9be7b0 },
  { target: "CeoOfficeScene", label: "CEO Office", x: WIDTH_PX * 0.5, y: 96, tint: 0xffe08a },
  { target: "BrainRoomScene", label: "Brain Room", x: WIDTH_PX * 0.75, y: 96, tint: 0xc9a3ff },
];

/** The HQ courtyard. Camera-followed player, three enterable buildings, ambient decoration. */
export class LobbyScene extends Phaser.Scene {
  private player!: PlayerController;
  private doors: { zone: Phaser.GameObjects.Zone; def: DoorDef }[] = [];
  private obstacles!: Phaser.Physics.Arcade.StaticGroup;

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

    const spawnX = data?.spawnX ?? WIDTH_PX / 2;
    const spawnY = data?.spawnY ?? HEIGHT_PX * 0.75;
    this.player = new PlayerController(this, spawnX, spawnY);
    this.physics.add.collider(this.player.sprite, this.obstacles);

    CameraManager.follow(this, this.player.sprite, { x: 0, y: 0, width: WIDTH_PX, height: HEIGHT_PX });
    CameraManager.fadeIn(this);

    GameManager.getInstance()?.setPlayerTransform({ scene: "LobbyScene", x: spawnX, y: spawnY, facing: "down" });
    EventBus.emit("scene:ready", { scene: "LobbyScene" });
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
        // No spawnX/spawnY: the target room falls back to its own default spawn point (near its exit door).
        SceneManager.goTo(this, def.target, { fromScene: "LobbyScene" });
        return;
      }
    }
  }

  private buildPath(): void {
    const map = this.make.tilemap({ tileWidth: TILE_SIZE, tileHeight: TILE_SIZE, width: WIDTH_TILES, height: HEIGHT_TILES });
    const tileset = map.addTilesetImage("tiles/path-middle", "tiles/path-middle", TILE_SIZE, TILE_SIZE, 0, 0);
    if (!tileset) return;
    const layer = map.createBlankLayer("path", tileset, 0, 0);
    if (!layer) return;
    // A horizontal walkway connecting the three doors, plus a vertical spine down to the spawn point.
    const rowTile = 7;
    for (let x = 4; x < WIDTH_TILES - 4; x++) layer.putTileAt(0, x, rowTile);
    const centerCol = Math.floor(WIDTH_TILES / 2);
    for (let y = rowTile; y < HEIGHT_TILES - 2; y++) layer.putTileAt(0, centerCol, y);
  }

  private buildPond(): void {
    const map = this.make.tilemap({ tileWidth: TILE_SIZE, tileHeight: TILE_SIZE, width: 4, height: 3 });
    const tileset = map.addTilesetImage("tiles/water-middle", "tiles/water-middle", TILE_SIZE, TILE_SIZE, 0, 0);
    if (!tileset) return;
    const layer = map.createBlankLayer("pond", tileset, 0, 0);
    if (!layer) return;
    layer.fill(0);
    layer.setPosition(WIDTH_PX - TILE_SIZE * 6, HEIGHT_PX - TILE_SIZE * 5);
  }

  private buildDecor(): void {
    const trees: [number, number][] = [
      [24, 40], [WIDTH_PX - 32, 48], [32, HEIGHT_PX - 48], [WIDTH_PX - 40, HEIGHT_PX - 64], [16, HEIGHT_PX / 2],
    ];
    for (const [x, y] of trees) {
      const tree = this.add.image(x, y, "outdoor-decoration/oak-tree").setScale(1.4).setDepth(2);
      this.obstacles.add(tree);
      const body = tree.body as Phaser.Physics.Arcade.StaticBody;
      body.setSize(tree.displayWidth * 0.5, tree.displayHeight * 0.3);
      body.setOffset((tree.displayWidth * 0.5) / 2, tree.displayHeight * 0.6);
    }

    this.add.image(TILE_SIZE * 3, HEIGHT_PX - TILE_SIZE * 2, "outdoor-decoration/fences").setScale(1.2).setDepth(2);
    this.add.image(WIDTH_PX - TILE_SIZE * 3, HEIGHT_PX - TILE_SIZE * 2, "outdoor-decoration/chest").setScale(1.3).setDepth(2);
  }

  private buildBuildings(): void {
    for (const def of DOORS) {
      const building = this.add.image(def.x, def.y - TILE_SIZE * 2, "outdoor-decoration/house-1-wood-base-blue");
      building.setScale(1.5).setTint(def.tint).setDepth(3);
      this.obstacles.add(building);
      // Collision only covers the roof/walls (top half of the sprite) so the
      // doorway at the bottom — and the interact zone in front of it — stays walkable.
      const body = building.body as Phaser.Physics.Arcade.StaticBody;
      body.setSize(building.displayWidth * 0.8, building.displayHeight * 0.5);
      body.setOffset(building.displayWidth * 0.1, building.displayHeight * 0.05);
      body.updateCenter();

      this.add
        .text(def.x, def.y - TILE_SIZE * 3.6, def.label, {
          fontFamily: "monospace",
          fontSize: "9px",
          color: "#f4e6c9",
          backgroundColor: "#241c14aa",
          padding: { x: 4, y: 2 },
        })
        .setOrigin(0.5)
        .setDepth(4);

      this.add
        .text(def.x, def.y + TILE_SIZE * 0.6, "[E] Enter", {
          fontFamily: "monospace",
          fontSize: "8px",
          color: "#d9a441",
        })
        .setOrigin(0.5)
        .setDepth(4);

      const zone = createZone(this, def.x, def.y + TILE_SIZE, TILE_SIZE * 2, TILE_SIZE);
      this.doors.push({ zone, def });
    }
  }
}
