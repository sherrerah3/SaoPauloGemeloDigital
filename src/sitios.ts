import type { FeatureCollection } from "geojson";

// Sitios emblemáticos del mapa 3D. Al pasar el mouse por uno se abre un globo con su foto.
// Las fotos vienen de Wikimedia Commons (licencias libres) y se convirtieron con
// herramientas/fotos_webp.py a public/fotos/sitios/<id>-480.webp. Para agregar un sitio:
// convertir la foto con ese script y sumar una entrada aquí con su autor y licencia.

export interface Sitio {
  id: string;
  nombre: string;
  /** Barrio o referencia corta. */
  zona: string;
  /** [longitud, latitud] */
  coordenadas: [number, number];
  autor: string;
  licencia: string;
  /** Página del archivo en Wikimedia Commons, donde está el detalle de la licencia. */
  fuente: string;
}

const COMMONS = "https://commons.wikimedia.org/wiki/File:";

export const SITIOS: Sitio[] = [
  {
    id: "masp",
    nombre: "MASP",
    zona: "Avenida Paulista",
    coordenadas: [-46.6556, -23.5614],
    autor: "Wilfredor",
    licencia: "CC0",
    fuente: `${COMMONS}MASP_Brazil.jpg`,
  },
  {
    id: "ibirapuera",
    nombre: "Parque Ibirapuera",
    zona: "Vila Mariana",
    coordenadas: [-46.6576, -23.5874],
    autor: "Wilfredor",
    licencia: "CC0",
    fuente: `${COMMONS}Ibirapuera_Park_in_S%C3%A3o_Paulo.jpg`,
  },
  {
    id: "se",
    nombre: "Catedral da Sé",
    zona: "Sé, centro histórico",
    coordenadas: [-46.6336, -23.5505],
    autor: "Wilfredor",
    licencia: "CC0",
    fuente: `${COMMONS}Catedral_da_S%C3%A9,_S%C3%A3o_Paulo,_Brasil.jpg`,
  },
  {
    id: "mercado",
    nombre: "Mercado Municipal",
    zona: "Sé, centro",
    coordenadas: [-46.6292, -23.5413],
    autor: "Wilfredor",
    licencia: "CC BY-SA 4.0",
    fuente: `${COMMONS}Municipal_Market_of_S%C3%A3o_Paulo_city.jpg`,
  },
  {
    id: "copan",
    nombre: "Edifício Copan",
    zona: "República, centro",
    coordenadas: [-46.6423, -23.545],
    autor: "Pablo Trincado",
    licencia: "CC BY 2.0",
    fuente: `${COMMONS}Edif%C3%ADcio_Copan_-_frente.jpg`,
  },
  {
    id: "theatro",
    nombre: "Theatro Municipal",
    zona: "República, centro",
    coordenadas: [-46.6387, -23.5452],
    autor: "Wilfredor",
    licencia: "CC0",
    fuente: `${COMMONS}Teatro_Municipal_de_S%C3%A3o_Paulo_8.jpg`,
  },
  {
    id: "luz",
    nombre: "Estação da Luz",
    zona: "Bom Retiro",
    coordenadas: [-46.6361, -23.5343],
    autor: "Wilfredor",
    licencia: "CC0",
    fuente: `${COMMONS}Luz_Train_Station,_Sao_Paulo.jpg`,
  },
  {
    id: "morumbi",
    nombre: "Estádio do Morumbi",
    zona: "Morumbi",
    coordenadas: [-46.7222, -23.6],
    autor: "Horcoff",
    licencia: "CC BY 4.0",
    fuente: `${COMMONS}Est%C3%A1dio_do_Morumbi,_2018.jpg`,
  },
  {
    id: "estaiada",
    nombre: "Ponte Octávio Frias de Oliveira",
    zona: "Brooklin, Marginal Pinheiros",
    coordenadas: [-46.6985, -23.6087],
    autor: "ikedaleo",
    licencia: "CC0",
    fuente: `${COMMONS}Ponte_Oct%C3%A1vio_Frias_de_Oliveira,_S%C3%A3o_Paulo,_Brasil.jpg`,
  },
];

export function rutaFotoSitio(id: string): string {
  return `${import.meta.env.BASE_URL}fotos/sitios/${id}-480.webp`;
}

export const SITIOS_GEOJSON: FeatureCollection = {
  type: "FeatureCollection",
  features: SITIOS.map((s) => ({
    type: "Feature",
    properties: { id: s.id },
    geometry: { type: "Point", coordinates: s.coordenadas },
  })),
};
