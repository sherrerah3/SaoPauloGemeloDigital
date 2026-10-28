import type { FeatureCollection } from "geojson";

// Sitios emblemáticos del mapa 3D. Al pasar el mouse por una estrella se abre un globo con su foto.
// Las fotos vienen de Wikimedia Commons (licencias libres) y se convirtieron con
// herramientas/fotos_webp.py a public/fotos/sitios/<id>-480.webp. Para agregar un sitio:
// convertir la foto con ese script y sumar una entrada aquí con su autor y licencia.
//
// Las coordenadas son las de Wikipedia. Para que las estrellas no tapen otras ubicaciones se midió la
// distancia de cada sitio a las estaciones de metro, a los estadios y a los demás sitios:
//   - ningún sitio queda a menos de 170 m de una estación (lo más cerca es la Sé, a 173 m),
//   - ninguno queda a menos de 300 m de otro sitio (lo más cerca son la Sé y el Pátio do Colégio, 399 m).
// A zoom 14 los radios de una estrella y de una estación suman unos 16 px, que son unos 140 m, así que no se tocan.
// La Catedral da Sé y la Estação da Luz se corrieron unas decenas de metros para cumplir lo primero;
// el resto está en su posición de Wikipedia.
// Excepción: el Morumbi queda a 152 m del punto de su estadio en la capa «Estadios» (apagada por
// defecto). Es el mismo lugar, así que no tiene sentido separarlos.

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

type DefinicionSitio = Omit<Sitio, "fuente"> & {
  /** Nombre del archivo en Wikimedia Commons, sin el prefijo «File:». */
  archivo: string;
};

const COMMONS = "https://commons.wikimedia.org/wiki/File:";

const DEFINICIONES: DefinicionSitio[] = [
  {
    id: "masp",
    nombre: "MASP",
    zona: "Avenida Paulista",
    coordenadas: [-46.6559, -23.5616],
    autor: "Wilfredor",
    licencia: "CC0",
    archivo: "MASP Brazil.jpg",
  },
  {
    id: "ibirapuera",
    nombre: "Parque Ibirapuera",
    zona: "Vila Mariana",
    coordenadas: [-46.6589, -23.5883],
    autor: "Wilfredor",
    licencia: "CC0",
    archivo: "Ibirapuera Park in São Paulo.jpg",
  },
  {
    id: "se",
    nombre: "Catedral da Sé",
    zona: "Sé, centro histórico",
    coordenadas: [-46.6348, -23.5512],
    autor: "Wilfredor",
    licencia: "CC0",
    archivo: "Catedral da Sé, São Paulo, Brasil.jpg",
  },
  {
    id: "patio",
    nombre: "Pátio do Colégio",
    zona: "Sé, donde se fundó la ciudad",
    coordenadas: [-46.6328, -23.5481],
    autor: "Renato Santiago Rodrigues",
    licencia: "CC BY-SA 4.0",
    archivo: "Pateo do collegio 01.jpg",
  },
  {
    id: "mercado",
    nombre: "Mercado Municipal",
    zona: "Sé, centro",
    coordenadas: [-46.6292, -23.5417],
    autor: "Wilfredor",
    licencia: "CC BY-SA 4.0",
    archivo: "Municipal Market of São Paulo city.jpg",
  },
  {
    id: "copan",
    nombre: "Edifício Copan",
    zona: "República, centro",
    coordenadas: [-46.6444, -23.5466],
    autor: "Pablo Trincado",
    licencia: "CC BY 2.0",
    archivo: "Edifício Copan - frente.jpg",
  },
  {
    id: "theatro",
    nombre: "Theatro Municipal",
    zona: "República, centro",
    coordenadas: [-46.6386, -23.5453],
    autor: "Wilfredor",
    licencia: "CC0",
    archivo: "Teatro Municipal de São Paulo 8.jpg",
  },
  {
    id: "luz",
    nombre: "Estação da Luz",
    zona: "Bom Retiro",
    coordenadas: [-46.6355, -23.5347],
    autor: "Wilfredor",
    licencia: "CC0",
    archivo: "Luz Train Station, Sao Paulo.jpg",
  },
  {
    id: "memorial",
    nombre: "Memorial da América Latina",
    zona: "Barra Funda",
    coordenadas: [-46.6653, -23.5272],
    autor: "Picturesartbr",
    licencia: "CC BY-SA 4.0",
    archivo: "Memorial da América Latina - Alvaro Menezes (1).jpg",
  },
  {
    id: "beco",
    nombre: "Beco do Batman",
    zona: "Vila Madalena",
    coordenadas: [-46.6866, -23.5565],
    autor: "Diego Bravo",
    licencia: "CC BY-SA 4.0",
    archivo: "Beco do Batman - Vila-Madalena, São Paulo - SP 02.jpg",
  },
  {
    id: "villalobos",
    nombre: "Parque Villa-Lobos",
    zona: "Alto de Pinheiros",
    coordenadas: [-46.7239, -23.5467],
    autor: "Mike Peel",
    licencia: "CC BY-SA 4.0",
    archivo: "Parque Villa-Lobos 2018 014.jpg",
  },
  {
    id: "ipiranga",
    nombre: "Museu do Ipiranga",
    zona: "Ipiranga, donde se proclamó la independencia",
    coordenadas: [-46.6097, -23.5856],
    autor: "LuanCampSouza93",
    licencia: "CC0",
    archivo: "Fachada do Museu do Ipiranga.jpg",
  },
  {
    id: "morumbi",
    nombre: "Estádio do Morumbi",
    zona: "Morumbi",
    coordenadas: [-46.7202, -23.6001],
    autor: "Horcoff",
    licencia: "CC BY 4.0",
    archivo: "Estádio do Morumbi, 2018.jpg",
  },
  {
    id: "estaiada",
    nombre: "Ponte Octávio Frias de Oliveira",
    zona: "Brooklin, Marginal Pinheiros",
    coordenadas: [-46.6992, -23.6127],
    autor: "ikedaleo",
    licencia: "CC0",
    archivo: "Ponte Octávio Frias de Oliveira, São Paulo, Brasil.jpg",
  },
  {
    id: "zoo",
    nombre: "Zoológico de São Paulo",
    zona: "Parque Estadual das Fontes do Ipiranga",
    coordenadas: [-46.6222, -23.6493],
    autor: "Wilfredor",
    licencia: "CC0",
    archivo: "Phoenicopterus ruber in São Paulo Zoo.jpg",
  },
  {
    id: "interlagos",
    nombre: "Autódromo de Interlagos",
    zona: "Interlagos, zona sur",
    coordenadas: [-46.6972, -23.7011],
    autor: "Boaventuravinicius",
    licencia: "CC BY-SA 4.0",
    archivo: "Autódromo de Interlagos em Dezembro de 2023.jpg",
  },
  {
    id: "jaragua",
    nombre: "Pico do Jaraguá",
    zona: "Jaraguá, el punto más alto de la ciudad",
    coordenadas: [-46.7653, -23.4583],
    autor: "Joalpe",
    licencia: "CC BY-SA 4.0",
    archivo: "Pico do Jaraguá, São Paulo 03.jpg",
  },
  {
    id: "carmo",
    nombre: "Parque do Carmo",
    zona: "Itaquera, zona este",
    coordenadas: [-46.4692, -23.575],
    autor: "Adriano Makoto Suzuki",
    licencia: "CC BY 2.0",
    archivo: "Bosque das Cerejeiras, Parque do Carmo, São Paulo - SP.jpg",
  },
];

export const SITIOS: Sitio[] = DEFINICIONES.map(({ archivo, ...sitio }) => ({
  ...sitio,
  fuente: COMMONS + encodeURIComponent(archivo.replaceAll(" ", "_")),
}));

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
