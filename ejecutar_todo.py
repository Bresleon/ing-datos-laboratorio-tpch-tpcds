import os
import subprocess
import sys
import pandas as pd
import matplotlib.pyplot as plt

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TPCH_DIR = os.path.join(ROOT_DIR, "tpch")
TPCDS_DIR = os.path.join(ROOT_DIR, "tpcds")

TPCH_CSV = os.path.join(TPCH_DIR, "tiempos_tpch.csv")
TPCDS_CSV = os.path.join(TPCDS_DIR, "tiempos_tpcds.csv")
COMPARATIVA_IMG = os.path.join(ROOT_DIR, "comparativa_tpch_vs_tpcds.png")
COMPARATIVA_CSV = os.path.join(ROOT_DIR, "tiempos_consolidados.csv")

def ejecutar_benchmark(modulo_dir, script_nombre, nombre_benchmark):
    print(f"\n========================================================")
    print(f"   INICIANDO BENCHMARK: {nombre_benchmark}")
    print(f"========================================================")
    
    script_path = os.path.join(modulo_dir, script_nombre)
    if not os.path.exists(script_path):
        print(f"[!] Error: No se encontró {script_path}")
        return False
        
    resultado = subprocess.run([sys.executable, script_nombre], cwd=modulo_dir)
    return resultado.returncode == 0

def consolidar_y_graficar():
    if not os.path.exists(TPCH_CSV) or not os.path.exists(TPCDS_CSV):
        print("[!] No se encontraron los archivos CSV generados para consolidar.")
        return

    df_tpch = pd.read_csv(TPCH_CSV)
    df_tpch["Benchmark"] = "TPC-H"

    df_tpcds = pd.read_csv(TPCDS_CSV)
    df_tpcds["Benchmark"] = "TPC-DS"

    # Consolidar en un solo CSV maestro
    df_total = pd.concat([df_tpch, df_tpcds], ignore_index=True)
    df_total.to_csv(COMPARATIVA_CSV, index=False)
    print(f"\n[+] Datos consolidados guardados en: {COMPARATIVA_CSV}")

    # Generar gráfico comparativo con dos subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Gráfico TPC-H
    ax1.bar(df_tpch["Consulta"], df_tpch["Segundos"], color="royalblue", edgecolor="black", alpha=0.85)
    ax1.set_title("TPC-H (Modelo Relacional / Consultas Ad-hoc)", fontsize=12, pad=10)
    ax1.set_xlabel("Consulta", fontsize=10)
    ax1.set_ylabel("Tiempo de ejecución (s)", fontsize=10)
    ax1.tick_params(axis="x", rotation=45)
    ax1.grid(axis="y", linestyle="--", alpha=0.7)

    # Gráfico TPC-DS
    ax2.bar(df_tpcds["Consulta"], df_tpcds["Segundos"], color="darkorange", edgecolor="black", alpha=0.85)
    ax2.set_title("TPC-DS (Modelo Copo de Nieve / Data Warehouse)", fontsize=12, pad=10)
    ax2.set_xlabel("Consulta", fontsize=10)
    ax2.set_ylabel("Tiempo de ejecución (s)", fontsize=10)
    ax2.tick_params(axis="x", rotation=45)
    ax2.grid(axis="y", linestyle="--", alpha=0.7)

    plt.suptitle("Comparativa de Rendimiento PostgreSQL (TPC-H vs TPC-DS)", fontsize=14, y=0.98)
    plt.tight_layout()
    plt.savefig(COMPARATIVA_IMG, dpi=300)
    print(f"[+] Gráfico comparativo guardado como: {COMPARATIVA_IMG}\n")

if __name__ == "__main__":
    ok_tpch = ejecutar_benchmark(TPCH_DIR, "medir_tpch.py", "TPC-H (Puerto 5432)")
    ok_tpcds = ejecutar_benchmark(TPCDS_DIR, "medir_tpcds.py", "TPC-DS (Puerto 5433)")

    if ok_tpch and ok_tpcds:
        consolidar_y_graficar()
        print("=== PROCESO MAESTRO FINALIZADO CON ÉXITO ===")
    else:
        print("[!] Uno de los benchmarks falló en la ejecución.")

