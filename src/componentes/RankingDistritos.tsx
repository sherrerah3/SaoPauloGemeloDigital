import { useState } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatear, formatearCorto, type Indicador } from "../datos";
import { EJE, ESTILO_TOOLTIP, SERIE_1 } from "./graficos";

interface Props {
  titulo: string;
  /** Ya ordenado: el gráfico muestra los 10 primeros y la tabla, todos. */
  ranking: (Indicador & { valor: number })[];
  unidad: string;
  seleccionado: string | null;
  onSeleccionar: (codigo: string) => void;
  /** Nombre de la unidad en la tabla: «Distrito» o «Subprefeitura». */
  columna?: string;
  children?: React.ReactNode;
}

/** Los 10 primeros en barras, o la tabla completa. Clic en una barra o fila selecciona el territorio. */
export default function RankingDistritos({
  titulo,
  ranking,
  unidad,
  seleccionado,
  onSeleccionar,
  columna = "Distrito",
  children,
}: Props) {
  const [verTabla, setVerTabla] = useState(false);
  return (
    <div className="panel">
      <div className="panel-cabecera">
        <h2>{titulo}</h2>
        <button type="button" className="enlace" onClick={() => setVerTabla((v) => !v)}>
          {verTabla ? "Ver gráfico" : `Ver tabla de los ${ranking.length}`}
        </button>
      </div>
      {verTabla ? (
        <div className="tabla-scroll">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>{columna}</th>
                <th className="num">{unidad}</th>
              </tr>
            </thead>
            <tbody>
              {ranking.map((i, n) => (
                <tr key={i.id} className={i.codigo_territorio === seleccionado ? "fila-activa" : ""}>
                  <td>{n + 1}</td>
                  <td>
                    <button type="button" className="enlace" onClick={() => onSeleccionar(i.codigo_territorio)}>
                      {i.nombre_territorio}
                    </button>
                  </td>
                  <td className="num">{formatear(i.valor, i.unidad)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={360}>
          <BarChart
            data={ranking
              .slice(0, 10)
              .map((i) => ({ nombre: i.nombre_territorio, valor: i.valor, codigo: i.codigo_territorio }))}
            layout="vertical"
            margin={{ left: 8, right: 16 }}
            barCategoryGap={4}
          >
            <CartesianGrid horizontal={false} stroke="var(--grilla)" />
            <XAxis type="number" tickFormatter={formatearCorto} {...EJE} />
            <YAxis type="category" dataKey="nombre" width={130} {...EJE} />
            <Tooltip
              cursor={{ fill: "var(--superficie-2)" }}
              formatter={(v) => [formatear(Number(v), unidad), unidad]}
              {...ESTILO_TOOLTIP}
            />
            <Bar
              dataKey="valor"
              fill={SERIE_1}
              radius={[0, 4, 4, 0]}
              onClick={(d) => onSeleccionar((d as unknown as { codigo: string }).codigo)}
              style={{ cursor: "pointer" }}
            >
              {/* Con valores cercanos entre sí las barras se parecen: el valor va escrito. */}
              <LabelList
                dataKey="valor"
                position="insideRight"
                formatter={(v: unknown) => formatear(Number(v), unidad)}
                style={{ fill: "#ffffff", fontSize: 11, fontWeight: 600 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
      {children}
    </div>
  );
}
