# Una sola imagen con Python (pipeline de datos) y Node (sitio), para que todo el
# equipo corra lo mismo sin instalar GDAL, geopandas ni Node en su máquina.
# Vercel no la usa: despliega el front y los datos ya construidos en public/data/.
FROM node:22-bookworm-slim AS node

FROM python:3.12-slim-bookworm

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

WORKDIR /app

# Dependencias primero, para que Docker las cachee mientras no cambien.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

# El contenedor corre con el usuario de tu máquina (ver docker-compose.yml), así que
# /app debe poder escribirse sin ser root (caché de Vite, tsbuildinfo).
RUN mkdir -p node_modules/.vite dist && chmod -R a+rwX /app

ENV PYTHONUNBUFFERED=1 HOME=/tmp
CMD ["python", "ingesta/todo.py"]
