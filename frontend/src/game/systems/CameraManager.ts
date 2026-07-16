import Phaser from "phaser";

const BASE_ZOOM = 2.5;

/** Configures smooth camera-follow behavior consistently across scenes. */
export class CameraManager {
  static follow(
    scene: Phaser.Scene,
    target: Phaser.GameObjects.GameObject,
    bounds?: Phaser.Types.Math.Vector2Like & { width: number; height: number },
  ): void {
    const cam = scene.cameras.main;
    if (bounds) {
      cam.setBounds(bounds.x ?? 0, bounds.y ?? 0, bounds.width, bounds.height);
    }
    cam.startFollow(target, true, 0.12, 0.12);
    cam.setDeadzone(32, 24);
    cam.roundPixels = true;

    // BASE_ZOOM looks right for most rooms, but a room/viewport combination
    // where the world is smaller than the zoomed viewport would leave a
    // black void the camera can't scroll into (bounds clamp it). Zoom in
    // further whenever needed so the world always fully covers the
    // viewport, like CSS `background-size: cover`, re-checked on resize.
    const applyZoom = () => {
      let zoom = BASE_ZOOM;
      if (bounds) {
        const viewportW = scene.scale.width;
        const viewportH = scene.scale.height;
        zoom = Math.max(BASE_ZOOM, viewportW / bounds.width, viewportH / bounds.height);
      }
      cam.setZoom(zoom);
    };
    applyZoom();
    scene.scale.on(Phaser.Scale.Events.RESIZE, applyZoom);
    scene.events.once(Phaser.Scenes.Events.SHUTDOWN, () => scene.scale.off(Phaser.Scale.Events.RESIZE, applyZoom));
  }

  static fadeIn(scene: Phaser.Scene, durationMs = 300): void {
    scene.cameras.main.fadeIn(durationMs, 0, 0, 0);
  }

  static fadeOutThen(scene: Phaser.Scene, durationMs: number, onComplete: () => void): void {
    scene.cameras.main.fadeOut(durationMs, 0, 0, 0);
    scene.cameras.main.once(Phaser.Cameras.Scene2D.Events.FADE_OUT_COMPLETE, onComplete);
  }
}
