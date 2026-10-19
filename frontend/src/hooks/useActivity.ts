import { useCallback, useEffect, useState } from "react";

// Actividad de la sesión (búsquedas, comparaciones, análisis). Vive en sessionStorage:
// es por pestaña y se borra al cerrarla. No se envía al backend.
export interface ActivityItem {
  kind: "player" | "team" | "compare" | "scouting" | "similar" | "market" | "value" | "match" | "search";
  label: string;
  detail?: string;
  path: string;
  at: number;
}

const KEY = "fiq.activity";
const EVENT = "fiq-activity";
const MAX = 30;

function read(): ActivityItem[] {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function logActivity(item: Omit<ActivityItem, "at">) {
  try {
    const items = read().filter((i) => !(i.path === item.path && i.kind === item.kind));
    items.unshift({ ...item, at: Date.now() });
    sessionStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX)));
    window.dispatchEvent(new Event(EVENT));
  } catch {
    /* almacenamiento no disponible: la app sigue funcionando sin historial */
  }
}

export function useActivity() {
  const [items, setItems] = useState<ActivityItem[]>(read);
  useEffect(() => {
    const update = () => setItems(read());
    window.addEventListener(EVENT, update);
    return () => window.removeEventListener(EVENT, update);
  }, []);
  const clear = useCallback(() => {
    try {
      sessionStorage.removeItem(KEY);
    } catch {
      /* nada que limpiar */
    }
    setItems([]);
  }, []);
  return { items, clear };
}
