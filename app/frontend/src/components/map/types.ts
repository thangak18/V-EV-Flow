export type MapPoint = {
  id: string;
  lat: number;
  lng: number;
  label: string;
  role: "origin" | "destination" | "primary" | "backup" | "pressure";
  color?: string;
  description?: string;
  badge?: string;
  /** Camera summary; its presence marks the station as having a camera. */
  camera?: string;
  /** Vehicles waiting at a charging station, shown as a prominent marker pill. */
  queue?: number;
};

/** Station known to the UI but missing directory coordinates — text only. */
export type UnlocatedMapPoint = {
  id: string;
  label: string;
  role: MapPoint["role"];
};

export type MapModel = {
  routes?: {
    id: string;
    label: string;
    color: string;
    dashed?: boolean;
    coordinates: { lat: number; lng: number }[];
  }[];
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
