# ==========================================================
# ETAPA 1: Compilación de dsdgen y dsqgen con Conda
# ==========================================================
FROM continuumio/miniconda3:latest AS builder

RUN conda install -y -c conda-forge gcc make git flex bison

# Enlazar flex para responder a llamadas de lex
RUN ln -sf /opt/conda/bin/flex /opt/conda/bin/lex

WORKDIR /usr/src/tpcds-kit
COPY tpcds-kit/ .

WORKDIR /usr/src/tpcds-kit/tools
RUN make clean || true

RUN make OS=LINUX \
    LINUX_CFLAGS="-g -Wall -std=gnu89 -fcommon -Wno-implicit-int -Wno-implicit-function-declaration -Wno-error=incompatible-pointer-types" \
    LDFLAGS="-fcommon" \
    LEX=flex

# ==========================================================
# ETAPA 2: Imagen PostgreSQL con esquema TPC-DS Optimizado
# ==========================================================
FROM postgres:15

ENV POSTGRES_PASSWORD=password123
ENV POSTGRES_DB=tpcds
ENV DSS_QUERY=/opt/tpcds/query_templates

RUN mkdir -p /opt/tpcds/query_templates /opt/tpcds/generated_queries /opt/tpcds/queries_individuales

# Copiar ejecutables y dependencias compiladas
COPY --from=builder /usr/src/tpcds-kit/tools/dsdgen /usr/local/bin/dsdgen
COPY --from=builder /usr/src/tpcds-kit/tools/dsqgen /usr/local/bin/dsqgen
COPY --from=builder /usr/src/tpcds-kit/tools/tpcds.idx /opt/tpcds/tpcds.idx
COPY --from=builder /usr/src/tpcds-kit/tools/tpcds.dst /opt/tpcds/tpcds.dst
COPY --from=builder /usr/src/tpcds-kit/tools/tpcds.sql /opt/tpcds/tpcds.sql
COPY --from=builder /usr/src/tpcds-kit/tools/tpcds_ri.sql /opt/tpcds/tpcds_ri.sql
COPY --from=builder /usr/src/tpcds-kit/query_templates/ /opt/tpcds/query_templates/

# Script de inicialización automática al arrancar el contenedor
RUN cat << 'EOF' > /docker-entrypoint-initdb.d/01_init_tpcds.sh
#!/bin/bash
set -e

echo "=== [TPC-DS] Generando datos de prueba (Scale Factor 1 GB) ==="
cd /opt/tpcds
dsdgen -scale 1 -force Y -verbose Y

echo "=== [TPC-DS] Normalizando delimitadores de archivos .dat ==="
for f in *.dat; do
  sed -i 's/|$//' "$f"
done

echo "=== [TPC-DS] Creando las 25 tablas en PostgreSQL ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /opt/tpcds/tpcds.sql

echo "=== [TPC-DS] Importando los datos masivamente ==="
for dat_file in *.dat; do
  table_name=$(basename "$dat_file" .dat)
  echo "Cargando tabla: $table_name..."
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
       -c "\copy $table_name FROM '/opt/tpcds/$dat_file' WITH (FORMAT csv, DELIMITER '|');"
done

echo "=== [TPC-DS] Creando claves primarias e índices relacionales del comité ==="
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /opt/tpcds/tpcds_ri.sql || true

echo "=== [TPC-DS] Generando índices analíticos adicionales de cobertura ==="
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" << 'EOSQL'
CREATE INDEX IF NOT EXISTS idx_sr_returned_date_sk ON store_returns (sr_returned_date_sk);
CREATE INDEX IF NOT EXISTS idx_sr_customer_sk ON store_returns (sr_customer_sk);
CREATE INDEX IF NOT EXISTS idx_sr_store_sk ON store_returns (sr_store_sk);
CREATE INDEX IF NOT EXISTS idx_ss_sold_date_sk ON store_sales (ss_sold_date_sk);
CREATE INDEX IF NOT EXISTS idx_ss_item_sk ON store_sales (ss_item_sk);
CREATE INDEX IF NOT EXISTS idx_ss_customer_sk ON store_sales (ss_customer_sk);
CREATE INDEX IF NOT EXISTS idx_d_date_sk ON date_dim (d_date_sk);
CREATE INDEX IF NOT EXISTS idx_d_year ON date_dim (d_year);
CREATE INDEX IF NOT EXISTS idx_d_moy ON date_dim (d_moy);
CREATE INDEX IF NOT EXISTS idx_d_month_seq ON date_dim (d_month_seq);
CREATE INDEX IF NOT EXISTS idx_c_current_addr_sk ON customer (c_current_addr_sk);
CREATE INDEX IF NOT EXISTS idx_ca_address_sk ON customer_address (ca_address_sk);
EOSQL

echo "=== [TPC-DS] Actualizando estadísticas del optimizador (ANALYZE) ==="
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "ANALYZE VERBOSE;"

echo "=== [TPC-DS] Generando el archivo unificado de consultas ==="
cd /opt/tpcds/generated_queries
cp /opt/tpcds/tpcds.idx .

dsqgen -DIRECTORY /opt/tpcds/query_templates \
       -INPUT /opt/tpcds/query_templates/templates.lst \
       -VERBOSE Y -QUALIFY Y -SCALE 1 -DIALECT netezza \
       -DISTRIBUTIONS /opt/tpcds/tpcds.idx \
       -OUTPUT_DIR /opt/tpcds/generated_queries

echo "=== [TPC-DS] Dividiendo el flujo en las 99 consultas individuales ==="
awk '/^-- start query/ { match($0, /query[0-9]+/); qname=substr($0, RSTART, RLENGTH); outfile="/opt/tpcds/queries_individuales/" qname ".sql"; } { if (outfile != "") print >> outfile; }' query_0.sql

echo "=== [TPC-DS] Normalizando sintaxis SQL e inyectando alias para PostgreSQL ==="
# 1. Corregir sintaxis de intervalos temporales
sed -i -E "s/\+([[:space:]]*)([0-9]+)[[:space:]]+days/\+ interval '\2 days'/g" /opt/tpcds/queries_individuales/*.sql

# 2. Corregir subconsultas huérfanas genéricas
sed -i -E 's/from \((select [^;]+)\)[[:space:]]*where/from (\1) as subq where/gI' /opt/tpcds/queries_individuales/*.sql
sed -i -E 's/from \((select [^;]+)\)[[:space:]]*group/from (\1) as subq group/gI' /opt/tpcds/queries_individuales/*.sql

# 3. Solución nativa con sed en modo multilínea (-z) para corregir el alias estructural en query2.sql
sed -i -z 's/from (select ws_sold_date_sk sold_date_sk\n              ,ws_ext_sales_price sales_price\n        from web_sales \n        union all\n        select cs_sold_date_sk sold_date_sk\n              ,cs_ext_sales_price sales_price\n        from catalog_sales))/from (select ws_sold_date_sk sold_date_sk\n              ,ws_ext_sales_price sales_price\n        from web_sales \n        union all\n        select cs_sold_date_sk sold_date_sk\n              ,cs_ext_sales_price sales_price\n        from catalog_sales) as sub_union)/g' /opt/tpcds/queries_individuales/query2.sql

echo "=== [TPC-DS] Inicialización analítica completada exitosamente ==="
EOF

RUN chmod +x /docker-entrypoint-initdb.d/01_init_tpcds.sh && \
    chown -R postgres:postgres /opt/tpcds

