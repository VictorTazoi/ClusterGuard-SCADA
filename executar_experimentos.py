from pathlib import Path
import subprocess
import sys


SEMENTES = list(range(101, 113))
PASTA_RESULTADOS = Path("resultados/experimento_final")


for semente in SEMENTES:
    pasta_saida = PASTA_RESULTADOS / f"ensaio_seed_{semente}"
    if pasta_saida.exists():
        print(f"[IGNORADO] Seed {semente}: pasta já existe.")
        continue
    comando = [
        sys.executable,
        "laboratorio.py",
        "--port", "0",
        "--normal", "60",
        "--carga", "60",
        "--recuperacao", "60",
        "--intervalo", "1",
        "--perfil-cliente", "variavel",
        "--jitter", "0.30",
        "--manutencao-inicio", "20",
        "--manutencao-duracao", "15",
        "--intervalo-manutencao", "0.20",
        "--perfil-carga", "degraus",
        "--taxa-baixa", "2",
        "--taxa-media", "5",
        "--taxa", "10",
        "--seed", str(semente),
        "--saida", str(pasta_saida)
    ]
    print()
    print("=" * 60)
    print(f"Executando seed {semente}")
    print("=" * 60)
    subprocess.run(comando, check=True)
print()
print("Todos os experimentos foram executados.")
