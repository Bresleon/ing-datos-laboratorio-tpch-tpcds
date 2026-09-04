import os
import time
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt

# 1. Configuración de conexión a PostgreSQL en Docker
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "tpch",
    "user": "postgres",
    "password": "password123"
}

QUERIES_DIR = "consultas_tpch"
OUTPUT_CSV = "tiempos_tpch.csv"
OUTPUT_IMG = "grafico_tpch.png"

def run_benchmark():
    print("Conectando a PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    results = []

    # Iterar por las 22 consultas en orden numérico
    for i in range(1, 23):
        file_path = os.path.join(QUERIES_DIR, f"q{i}.sql")
        
        if not os.path.exists(file_path):
            print(f"[!] Archivo {file_path} no encontrado. Saltando...")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            query_sql = f.read()

        print(f"Ejecutando Consulta Q{i}...", end="", flush=True)

        start = time.perf_counter()
        try:
            cursor.execute(query_sql)
            cursor.fetchall()
            elapsed = time.perf_counter() - start
            print(f" Completada en {elapsed:.3f} s")
            results.append({"Consulta": f"Q{i}", "Segundos": elapsed})
        except Exception as e:
            print(f" Error: {e}")
            conn.rollback()

    cursor.close()
    conn.close()

    # Guardar resultados en DataFrame
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n[+] Tiempos guardados en {OUTPUT_CSV}.")

    # 2. Generar el gráfico comparativo
    plt.figure(figsize=(12, 6))
    bars = plt.bar(df["Consulta"], df["Segundos"], color="royalblue", edgecolor="black", alpha=0.85)

    plt.title("Tiempo de Ejecución por Consulta TPC-H (PostgreSQL en Docker)", fontsize=14, pad=15)
    plt.xlabel("Consulta", fontsize=12)
    plt.ylabel("Tiempo de ejecución (segundos)", fontsize=12)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    # Añadir el valor de tiempo encima de cada barra
    for bar in bars:
        height = bar.get_height()
        plt.annotate(f"{height:.2f}s",
                     xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3),
                     textcoords="offset points",
                     ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.savefig(OUTPUT_IMG, dpi=300)
    print(f"[+] Gráfico guardado como {OUTPUT_IMG}.")

if __name__ == "__main__":
    run_benchmark()

