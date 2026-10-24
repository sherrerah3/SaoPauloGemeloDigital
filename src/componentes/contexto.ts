import { createContext, useContext } from "react";
import type { Fuente } from "../datos";

export const FuentesContexto = createContext<Record<string, Fuente>>({});

export const useFuentes = () => useContext(FuentesContexto);
