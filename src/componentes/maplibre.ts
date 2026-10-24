// MapLibre v6 busca su worker junto a su propio módulo, y Vite no lo copia al empaquetar.
// Se importa como URL para que Vite lo publique y se registra una sola vez aquí.
import { setWorkerUrl } from "maplibre-gl";
import urlWorker from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import "maplibre-gl/dist/maplibre-gl.css";

setWorkerUrl(urlWorker);

export * from "maplibre-gl";
