"""Painel de terminal para o laboratório: roda laboratorio.py e mostra 1 linha por segundo.

Uso (aceita os mesmos argumentos do laboratorio.py):
    python visualizar.py
    python visualizar.py --normal 20 --carga 10 --recuperacao 20 --taxa 50
Somente leitura dos CSVs; não altera o método nem os dados.
"""
import argparse
import csv
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

os.system('')  # O console do Windows precisa aceitar as cores ANSI já usadas pelo painel.
COR = {'NORMAL': '\033[32m', 'CARGA': '\033[31;1m', 'RECUPERACAO': '\033[36m', '': '\033[0m'}
RESET = '\033[0m'
estado_execucao = {'nome': 'INICIANDO', 'fim': False}

def ler_stdout(processo: subprocess.Popen[str]) -> None:
    for linha in processo.stdout:
        linha = linha.strip()
        if linha.startswith('Fase '):
            estado_execucao['nome'] = linha.split()[1].upper().replace('Ç', 'C').replace('Ã', 'A')
        elif linha:
            estado_execucao['msg'] = linha
    estado_execucao['fim'] = True

def linhas(caminho: str | Path) -> list[dict[str, str]]:
    try:
        conteudo_csv = Path(caminho).read_text(encoding='utf-8')
    except OSError:
        return []
    linhas_csv = conteudo_csv.splitlines()
    if conteudo_csv and not conteudo_csv.endswith('\n'):
        linhas_csv = linhas_csv[:-1]  # A escrita do laboratório pode estar no meio de um registro.
    return list(csv.DictReader(linhas_csv))

def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--saida', default='resultados/ensaio_' + time.strftime('%Y%m%d_%H%M%S'))
    parser.add_argument('--taxa', type=float, default=50)
    argumentos_painel, argumentos_laboratorio = parser.parse_known_args()
    comando = [sys.executable, '-u', str(Path(__file__).with_name('laboratorio.py')),
           '--saida', argumentos_painel.saida, '--taxa', str(argumentos_painel.taxa)] + argumentos_laboratorio
    processo = subprocess.Popen(
        comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8',
    )
    threading.Thread(target=ler_stdout, args=(processo,), daemon=True).start()
    pasta_ensaio = Path(argumentos_painel.saida)
    escala = max(argumentos_painel.taxa + 1, 2)
    largura = 40
    print(f'Pasta: {pasta_ensaio}\n{"t(s)":>5}  {"fase":<12} {"req/s":>6}  {"barra (escala 0-%d)" % escala:<{largura}}  {"lat ms":>7}  falhas')
    segundo_exibido, consultas_anteriores, falhas_anteriores = 0, 0, 0
    totais = {'NORMAL': [], 'CARGA': [], 'RECUPERACAO': []}
    while not estado_execucao['fim']:
        time.sleep(1)
        segundo_exibido += 1
        registros_servidor = linhas(pasta_ensaio / 'servidor.csv')
        tentativas_cliente = linhas(pasta_ensaio / 'cliente.csv')
        taxa = len(registros_servidor) - consultas_anteriores
        consultas_anteriores = len(registros_servidor)
        falhas = sum(1 - int(tentativa['sucesso']) for tentativa in tentativas_cliente)
        ultima_latencia_ms = float(tentativas_cliente[-1]['latencia_ms']) if tentativas_cliente else float('nan')
        fase = estado_execucao['nome']
        cheio = min(largura, round(taxa / escala * largura))
        barra = '█' * cheio + '░' * (largura - cheio)
        aviso = '  <-- FALHA' if falhas > falhas_anteriores else ''
        falhas_anteriores = falhas
        print(f'{segundo_exibido:>5}  {COR.get(fase, "")}{fase:<12} {taxa:>6}  {barra}{RESET}  {ultima_latencia_ms:>7.2f}  {falhas:>6}{aviso}', flush=True)
        if fase in totais:
            totais[fase].append(taxa)
    processo.wait()
    print()
    for fase, contagens_fase in totais.items():
        if contagens_fase:
            print(f'{fase:<12} média {sum(contagens_fase)/len(contagens_fase):7.1f} req/s   máx {max(contagens_fase)}')
    print(estado_execucao.get('msg', ''))
    sys.exit(processo.returncode)

if __name__ == '__main__':
    main()
