# ==========================================================
# ETAPA 1: Compilación de DBGen y QGen usando Conda
# ==========================================================
FROM continuumio/miniconda3:latest AS builder

RUN conda install -y -c conda-forge gcc make git

WORKDIR /usr/src/tpch-kit
# Copia la subcarpeta tpch-kit hacia el contenedor
COPY tpch-kit/ .

WORKDIR /usr/src/tpch-kit/dbgen
RUN make clean || true

ENV CPPFLAGS="-std=gnu89 -Wno-error=incompatible-pointer-types"
RUN make MACHINE=LINUX DATABASE=POSTGRESQL

# ==========================================================
# ETAPA 2: Imagen PostgreSQL lista para usar
# ==========================================================
FROM postgres:15

ENV POSTGRES_PASSWORD=password123
ENV POSTGRES_DB=tpch
ENV DSS_QUERY=/opt/tpch/queries
ENV DSS_CONFIG=/opt/tpch

# Crear estructura de carpetas
RUN mkdir -p /opt/tpch/queries /opt/tpch/generated_queries

# Copiar ejecutables y plantillas
COPY --from=builder /usr/src/tpch-kit/dbgen/dbgen /usr/local/bin/dbgen
COPY --from=builder /usr/src/tpch-kit/dbgen/qgen /usr/local/bin/qgen
COPY --from=builder /usr/src/tpch-kit/dbgen/dists.dss /opt/tpch/dists.dss
COPY --from=builder /usr/src/tpch-kit/dbgen/dss.ddl /opt/tpch/dss.ddl
COPY --from=builder /usr/src/tpch-kit/dbgen/queries/ /opt/tpch/queries/

# Script de inicialización automática
RUN cat << 'EOF' > /docker-entrypoint-initdb.d/01_init_tpch.sh
#!/bin/bash
set -e

echo "=== [TPC-H] Iniciando generación de datos (SF 0.1) ==="
cd /opt/tpch
dbgen -vf -s 0.1

echo "=== [TPC-H] Normalizando delimitadores de archivos .tbl ==="
for f in *.tbl; do
  sed -i 's/|$//' "$f"
done

echo "=== [TPC-H] Creando tablas en PostgreSQL ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /opt/tpch/dss.ddl

echo "=== [TPC-H] Importando datos masivamente ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "\copy region FROM '/opt/tpch/region.tbl' WITH (FORMAT csv, DELIMITER '|');"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "\copy nation FROM '/opt/tpch/nation.tbl' WITH (FORMAT csv, DELIMITER '|');"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "\copy supplier FROM '/opt/tpch/supplier.tbl' WITH (FORMAT csv, DELIMITER '|');"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "\copy part FROM '/opt/tpch/part.tbl' WITH (FORMAT csv, DELIMITER '|');"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "\copy partsupp FROM '/opt/tpch/partsupp.tbl' WITH (FORMAT csv, DELIMITER '|');"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "\copy customer FROM '/opt/tpch/customer.tbl' WITH (FORMAT csv, DELIMITER '|');"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "\copy orders FROM '/opt/tpch/orders.tbl' WITH (FORMAT csv, DELIMITER '|');"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "\copy lineitem FROM '/opt/tpch/lineitem.tbl' WITH (FORMAT csv, DELIMITER '|');"

echo "=== [TPC-H] Creando claves primarias y foráneas ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" << 'EOSQL'
ALTER TABLE REGION ADD PRIMARY KEY (R_REGIONKEY);
ALTER TABLE NATION ADD PRIMARY KEY (N_NATIONKEY);
ALTER TABLE PART ADD PRIMARY KEY (P_PARTKEY);
ALTER TABLE SUPPLIER ADD PRIMARY KEY (S_SUPPKEY);
ALTER TABLE PARTSUPP ADD PRIMARY KEY (PS_PARTKEY, PS_SUPPKEY);
ALTER TABLE CUSTOMER ADD PRIMARY KEY (C_CUSTKEY);
ALTER TABLE ORDERS ADD PRIMARY KEY (O_ORDERKEY);
ALTER TABLE LINEITEM ADD PRIMARY KEY (L_ORDERKEY, L_LINENUMBER);

ALTER TABLE NATION ADD CONSTRAINT NATION_FK1 FOREIGN KEY (N_REGIONKEY) REFERENCES REGION(R_REGIONKEY);
ALTER TABLE SUPPLIER ADD CONSTRAINT SUPPLIER_FK1 FOREIGN KEY (S_NATIONKEY) REFERENCES NATION(N_NATIONKEY);
ALTER TABLE PARTSUPP ADD CONSTRAINT PARTSUPP_FK1 FOREIGN KEY (PS_SUPPKEY) REFERENCES SUPPLIER(S_SUPPKEY);
ALTER TABLE PARTSUPP ADD CONSTRAINT PARTSUPP_FK2 FOREIGN KEY (PS_PARTKEY) REFERENCES PART(P_PARTKEY);
ALTER TABLE CUSTOMER ADD CONSTRAINT CUSTOMER_FK1 FOREIGN KEY (C_NATIONKEY) REFERENCES NATION(N_NATIONKEY);
ALTER TABLE ORDERS ADD CONSTRAINT ORDERS_FK1 FOREIGN KEY (O_CUSTKEY) REFERENCES CUSTOMER(C_CUSTKEY);
ALTER TABLE LINEITEM ADD CONSTRAINT LINEITEM_FK1 FOREIGN KEY (L_ORDERKEY) REFERENCES ORDERS(O_ORDERKEY);
ALTER TABLE LINEITEM ADD CONSTRAINT LINEITEM_FK2 FOREIGN KEY (L_PARTKEY, L_SUPPKEY) REFERENCES PARTSUPP(PS_PARTKEY, PS_SUPPKEY);
EOSQL

echo "=== [TPC-H] Generando y normalizando las 22 consultas SQL ==="
export DSS_QUERY=/opt/tpch/queries
export DSS_CONFIG=/opt/tpch
cd /opt/tpch/generated_queries

# Copiar dists.dss aquí para que qgen lo encuentre sin importar la ruta de trabajo
cp /opt/tpch/dists.dss .

for i in $(seq 1 22); do
  qgen -d -s 0.1 "$i" > "q${i}.sql"
  sed -i 's/day (3)/day/g' "q${i}.sql"
  sed -i '/limit -1;/d' "q${i}.sql"
  sed -i -z 's/;\s*\nlimit \([0-9]\+\);/ limit \1;/g' "q${i}.sql"
done

echo "=== [TPC-H] Inicialización completada exitosamente ==="
EOF

RUN chmod +x /docker-entrypoint-initdb.d/01_init_tpch.sh && \
    chown -R postgres:postgres /opt/tpch

