export type MapPoint = {
  id: string;
  lat: number;
  lng: number;
  label: string;
  role: "origin" | "destination" | "primary" | "backup" | "pressure";
  color?: string;
};

export type MapModel = {
  points: MapPoint[];
  fitBounds?: boolean;
};

export interface MapAdapter {
  mount(container: HTMLElement, model: MapModel): Promise<void> | void;
  update(model: MapModel): Promise<void> | void;
  destroy(): void;
}
