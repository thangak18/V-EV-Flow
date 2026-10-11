import type { MapAdapter, MapModel } from "./types";

export class FakeMapAdapter implements MapAdapter {
  public mounted = false;
  public lastModel: MapModel | null = null;
  public destroyed = false;
  public calls: Array<"mount" | "update" | "destroy"> = [];

  mount(container: HTMLElement, model: MapModel): void {
    this.mounted = true;
    this.lastModel = model;
    this.calls.push("mount");
    container.dataset.mapAdapter = "fake";
    container.textContent = `Fake map · ${model.points.length} points`;
  }

  update(model: MapModel): void {
    this.lastModel = model;
    this.calls.push("update");
  }

  destroy(): void {
    this.destroyed = true;
    this.calls.push("destroy");
  }
}
