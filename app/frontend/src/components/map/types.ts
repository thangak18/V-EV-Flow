export type MapPoint = {
  id: string;
  lat: number;
  lng: number;
  label: string;
  role: "origin" | "destination" | "primary" | "backup" | "pressure";
  color?: string;
  description?: string;
};

/** Station known to the UI but missing directory coordinates — text only. */
export type UnlocatedMapPoint = {
  id: string;
  label: string;
  role: MapPoint["role"];
};

export type MapModel = {
  points: MapPoint[];
  unlocated?: UnlocatedMapPoint[];
  fitBounds?: boolean;
  focus?: { id: string; role: MapPoint["role"]; sequence: number };
};

export interface MapAdapter {
  mount(container: HTMLElement, model: MapModel): Promise<void> | void;
  update(model: MapModel): Promise<void> | void;
  destroy(): void;
}
