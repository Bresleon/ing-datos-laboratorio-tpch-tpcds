import os
import time
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "tpcds",
    "user": "postgres",
    "password": "password123"
}

QUERIES_DIR = "consultas_tpcds"
OUTPUT_CSV = "tiempos_tpcds.csv"
OUTPUT_IMG = "grafico_tpcds.png"

# Timeout en milisegundos por consulta (ej: 3 minutos)
STATEMENT_TIMEOUT_MS = 360000

def run_tpcds_benchmark():
    print("Conectando a PostgreSQL (TPC-DS en Docker:5433)...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cursor = conn.cursor()

    # Optimizaciones de sesión para Data Warehouse
    cursor.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS};")
    cursor.execute("SET work_mem = '128MB';")

    results = []
    # Probaremos las primeras 10 consultas
    sample_queries = list(range(1, 11))

    for q_num in sample_queries:
        file_path = os.path.join(QUERIES_DIR, f"query{q_num}.sql")
        
        if not os.path.exists(file_path):
            print(f"[!] {file_path} no encontrado. Saltando...")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            query_sql = f.read()

        print(f"Ejecutando Consulta {q_num}...", end="", flush=True)
        start = time.perf_counter()
        try:
            cursor.execute(query_sql)
            cursor.fetchall()
            elapsed = time.perf_counter() - start
            print(f" Completada en {elapsed:.3f} s")
            results.append({"Consulta": f"Q{q_num}", "Segundos": elapsed})
        except psycopg2.errors.QueryCanceled:
            print(" [TIMEOUT] Cancelada por exceder el tiempo límite.")
        except Exception as e:
            print(f" [ERROR]: {e}")

    cursor.close()
    conn.close()

    if not results:
        print("No se registraron ejecuciones exitosas.")
        return

    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n[+] Tiempos guardados en '{OUTPUT_CSV}'.")

    plt.figure(figsize=(10, 5))
    bars = plt.bar(df["Consulta"], df["Segundos"], color="darkorange", edgecolor="black", alpha=0.85)
    plt.title("Tiempos de Consulta TPC-DS (PostgreSQL 15 - SF 1)", fontsize=13, pad=15)
    plt.xlabel("Consulta", fontsize=11)
    plt.ylabel("Tiempo (segundos)", fontsize=11)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    for bar in bars:
        h = bar.get_height()
        plt.annotate(f"{h:.2f}s",
                     xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 3),
                     textcoords="offset points",
                     ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.savefig(OUTPUT_IMG, dpi=300)
    print(f"[+] Gráfico exportado como '{OUTPUT_IMG}'.")

if __name__ == "__main__":
    run_tpcds_benchmark()

