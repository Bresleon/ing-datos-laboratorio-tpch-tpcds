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
├── servers.json                    # Configuración de precarga de servidores para pgAdmin
├── ejecutar_todo.py                # Script maestro de ejecución global y consolidación
├── README.md                       # Documentación técnica del laboratorio
├── tiempos_consolidados.csv        # Dataset combinado de tiempos de ejecución
├── comparativa_tpch_vs_tpcds.png   # Gráfica comparativa consolidada
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
* Python 3.10+

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

En la máquina local, crea y activa el entorno de análisis para ejecutar los scripts de métricas:

```bash
conda create -n tpch_benchmark python=3.11 psycopg2 pandas matplotlib -y
conda activate tpch_benchmark
```

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

