# Laboratorio de Benchmarking Analítico: TPC-H vs TPC-DS

Este proyecto implementa, automatiza y compara los benchmarks estándar de la industria **TPC-H** (procesamiento analítico relacional / ad-hoc) y **TPC-DS** (toma de decisiones en esquemas complejos de Data Warehouse) utilizando **Conda**, **Docker**, **Docker Compose**, **PostgreSQL 15** y **pgAdmin 4**.

## 1. Arquitectura y Estructura del Proyecto

La solución utiliza una arquitectura basada en contenedores orquestados con compilación multietapa (*multistage build*):
* **Etapa Builder:** Emplea imágenes de Miniconda (`continuumio/miniconda3`) con compiladores C (`gcc`, `make`, `flex`, `bison`) y compatibilidad C89 (`-std=gnu89`, `-fcommon`) para compilar las suites oficiales `tpch-kit` y `tpcds-kit`.
* **Etapa Runtime:** PostgreSQL 15 oficial sobre Debian para garantizar compatibilidad con `glibc`. Scripts de inicio automatizados (`/docker-entrypoint-initdb.d/`) generan los datos, crean las tablas, aplican índices de cobertura analítica, calculan estadísticas (`ANALYZE`) y normalizan las consultas SQL.
* **Monitoreo:** pgAdmin 4 con precarga automática de servidores (`servers.json`) para visualización y métricas en tiempo real.

```text
ingenieria_datos/
├── docker-compose.yml              # Orquestador de servicios (TPC-H, TPC-DS, pgAdmin)
├── environment.yml                 # Definición del entorno Conda para reproducibilidad
├── LICENSE                         # Licencia de código abierto
├── servers.json                    # Configuración de precarga de servidores para pgAdmin
├── ejecutar_todo.py                # Script maestro de ejecución global y consolidación
├── README.md                       # Documentación técnica del laboratorio
├── tiempos_consolidados.csv        # Dataset combinado de tiempos de ejecución
├── comparativa_tpch_vs_tpcds.png   # Gráfica comparativa consolidada
├── ingestion/
│   └── sling/
│       └── replication.yaml        # Configuración declarativa del pipeline EL (Postgres -> DuckDB)
├── tpch/
│   ├── Dockerfile                  # Build multistage DBGen + PostgreSQL
│   ├── medir_tpch.py               # Automatización y métricas de TPC-H
│   ├── tiempos_tpch.csv            # Tiempos individuales de TPC-H
│   ├── grafico_tpch.png            # Gráfico de barras de TPC-H
│   ├── consultas_tpch/             # 22 consultas SQL estándar normalizadas
│   └── tpch-kit/                   # Código fuente oficial de TPC-H
└── tpcds/
    ├── Dockerfile                  # Build multistage DSDGen/DSQGen + PostgreSQL
    ├── medir_tpcds.py              # Automatización y métricas de TPC-DS
    ├── tiempos_tpcds.csv           # Tiempos individuales de TPC-DS
    ├── grafico_tpcds.png           # Gráfico de barras de TPC-DS
    ├── consultas_tpcds/            # 99 consultas SQL divididas y normalizadas
    └── tpcds-kit/                  # Código fuente oficial de TPC-DS
```

## 2. Requisitos Previos

* Docker Engine y Docker Compose V2
* Gestor de entornos Conda (Miniconda o Anaconda)
* Git
* Sling CLI (`pip install sling` o binario nativo)

## 3. Despliegue de la Infraestructura

Para construir las imágenes, inicializar los esquemas relacionales y levantar todos los servicios en segundo plano:

```bash
docker compose up -d --build
```

### Puertos y Servicios Disponibles:
* **TPC-H (PostgreSQL):** `localhost:5432` | Base de datos: `tpch` | Usuario: `postgres` | Clave: `password123`
* **TPC-DS (PostgreSQL):** `localhost:5433` | Base de datos: `tpcds` | Usuario: `postgres` | Clave: `password123` *(Memoria compartida asignada: 1 GB)*
* **pgAdmin 4 (Web UI):** `http://localhost:8080`

## 4. Configuración del Entorno en Conda

Para garantizar la reproducibilidad de las librerías analíticas (`psycopg2`, `pandas`, `matplotlib`), crea y activa el entorno directamente desde el archivo `environment.yml` ubicado en la raíz del proyecto:

```bash
# Crear el entorno a partir de la especificación
conda env create -f environment.yml

# Activar el entorno
conda activate tpc_env
```

*(Si en el futuro modificas dependencias en `environment.yml`, puedes sincronizarlo ejecutando `conda env update -f environment.yml --prune`).*

## 5. Ejecución de los Benchmarks

### Opción A: Ejecución Integral (Recomendada)
Para ejecutar ambos benchmarks en secuencia, consolidar los datos y generar la comparativa gráfica en un solo paso, corre desde la raíz del proyecto:

```bash
python ejecutar_todo.py
```

**Salidas generadas en la raíz:**
* `tiempos_consolidados.csv`: Archivo tabular unificado con todas las mediciones.
* `comparativa_tpch_vs_tpcds.png`: Figura comparativa con subgráficos lado a lado.

### Opción B: Ejecución Individual por Benchmark
Si deseas evaluar cada motor por separado:

* **TPC-H (22 consultas):**
  ```bash
  cd tpch
  python medir_tpch.py
  cd ..
  ```
  *Genera `tpch/tiempos_tpch.csv` y `tpch/grafico_tpch.png`.*

* **TPC-DS (Consultas representativas de Data Warehouse):**
  ```bash
  cd tpcds
  python medir_tpcds.py
  cd ..
  ```
  *Genera `tpcds/tiempos_tpcds.csv` y `tpcds/grafico_tpcds.png`.*

## 6. Monitoreo en Tiempo Real con pgAdmin

1. Ingresa en tu navegador a `http://localhost:8080`.
2. Inicia sesión con las credenciales:
   * **Usuario:** `admin@admin.com`
   * **Contraseña:** `password123`
3. En el árbol de navegación izquierdo (**Servers > Benchmarks**), selecciona el servidor deseado (`TPC-H` o `TPC-DS`) e introduce la contraseña de base de datos (`password123`).
4. Abre la pestaña **Dashboard** para monitorear en tiempo real transacciones por segundo (TPS), tuplas leídas/escritas y actividad de I/O mientras corren los scripts de Python.

## 7. Mantenimiento y Control de Contenedores

* **Detener los servicios (conservando los datos cargados):**
  ```bash
  docker compose stop
  ```
* **Reanudar la infraestructura instantáneamente:**
  ```bash
  docker compose start
  ```
* **Destruir los contenedores y los volúmenes de datos asociados:**
  ```bash
  docker compose down -v
  ```

## 8. Ingestión y Replicación EL: PostgreSQL a DuckDB con Sling

Además de la generación y benchmarking de datos en PostgreSQL, el proyecto incorpora una capa de Extract & Load (EL) hacia un motor analítico columnar embebido (DuckDB) utilizando Sling CLI.

### 8.1. Configuración de Conexiones

En `~/.sling/env.yaml` se definen las conexiones de origen y destino:

```yaml
connections:
  TPCH:
    type: postgres
    host: localhost
    port: 5432
    database: tpch
    user: postgres
    password: password123
  DUCK_DW:
    type: duckdb
    instance: /home/{nombre_usuario}/tpch_dw.duckdb
```

Nota sobre SSL en Docker: Dado que PostgreSQL corre en un contenedor local sin soporte SSL habilitado, se desactiva la negociación forzada del driver configurando la variable de entorno:

```bash
export PGSSLMODE=disable
```

### 8.2. Definición del Pipeline Declarativo (`ingestion/sling/replication.yaml`)

El pipeline replica tanto tablas dimensionales como de hechos, combinando estrategias de Full Refresh e Incremental:

```yaml
source: TPCH
target: DUCK_DW

defaults:
  mode: full-refresh

streams:
  public.region:
    object: main.region
  public.nation:
    object: main.nation
  public.supplier:
    object: main.supplier
  public.part:
    object: main.part
  public.customer:
    object: main.customer
  public.orders:
    object: main.orders
    mode: incremental
    primary_key: [o_orderkey]
    update_key: o_orderdate
  public.lineitem:
    object: main.lineitem
```

### 8.3. Ejecución del Pipeline

Para ejecutar la sincronización completa:

```bash
sling run -r ingestion/sling/replication.yaml
```

## 9. Métricas de Replicación y Validación Analítica

### 9.1. Rendimiento de Ingestión

Durante la replicación inicial de 7 streams, se migraron 786.602 registros en 30 segundos sin fallas:

| Stream | Registros | Tamaño | Tiempo | Rendimiento |
| --- | --- | --- | --- | --- |
| public.region | 5 | 475 B | 1 s | 4 r/s |
| public.nation | 25 | 2.6 kB | 1 s | 20 r/s |
| public.supplier | 1.000 | 146 kB | 1 s | 723 r/s |
| public.part | 20.000 | 2.7 MB | 1 s | 11.658 r/s |
| public.customer | 15.000 | 2.4 MB | 1 s | 9.340 r/s |
| public.orders | 150.000 | 18.0 MB | 4 s | 35.808 r/s |
| public.lineitem | 600.572 | 87.0 MB | 16 s | 36.674 r/s |
| Total Pipeline | 786.602 | ~110.2 MB | 30 s | ~26.220 r/s (global) |

### 9.2. Validación Analítica en DuckDB

Para verificar la consistencia e integridad referencial post-replicación, se ejecuta una consulta agregada multidimensional sobre DuckDB:

```python
import duckdb

con = duckdb.connect("/home/{nombre_usuario}/tpch_dw.duckdb")

query = """
    SELECT 
        n.n_name AS pais,
        COUNT(o.o_orderkey) AS total_pedidos,
        ROUND(SUM(o.o_totalprice), 2) AS facturacion_total
    FROM main.customer c
    JOIN main.orders o ON c.c_custkey = o.o_custkey
    JOIN main.nation n ON c.c_nationkey = n.n_nationkey
    GROUP BY n.n_name
    ORDER BY facturacion_total DESC
    LIMIT 5;
"""

print(con.execute(query).df())
```

Resultado obtenido:

```
        pais  total_pedidos  facturacion_total
0       IRAN           6568       9.462088e+08
1  INDONESIA           6445       9.161848e+08
2   ETHIOPIA           6333       9.028494e+08
3    MOROCCO           6300       8.931228e+08
4      CHINA           6141       8.819649e+08
```

La coherencia de los totales y la resolución sin nulos de los JOIN confirman la preservación de las relaciones dimensionales entre PostgreSQL y DuckDB.