// Configuración de marca y conexión. Para cambiar el nombre del producto: VITE_APP_NAME en frontend/.env
export const APP_NAME: string = import.meta.env.VITE_APP_NAME || "Football IQ";
export const APP_TAGLINE: string = import.meta.env.VITE_APP_TAGLINE || "Scouting & Analytics";
// Por defecto se usa el proxy de Vite (/api -> backend). En producción se puede apuntar a otra URL.
export const API_BASE: string = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

// Fotos y escudos enlazados desde la web (tienen derechos de sus dueños; no se redistribuyen).
// Con VITE_SHOW_IMAGES=false se muestran solo iniciales.
export const SHOW_IMAGES: boolean = (import.meta.env.VITE_SHOW_IMAGES ?? "true") !== "false";

export const SERIES_COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)"];
export const OUTCOME_COLORS = { home: "var(--series-1)", draw: "var(--neutral-mark)", away: "var(--series-2)" };
