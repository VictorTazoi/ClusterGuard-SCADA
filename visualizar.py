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

os.system('')  # habilita sequências ANSI no console do Windows
COR = {'NORMAL': '\033[32m', 'CARGA': '\033[31;1m', 'RECUPERACAO': '\033[36m', '': '\033[0m'}
RESET = '\033[0m'
phase = {'nome': 'INICIANDO', 'fim': False}

def ler_stdout(proc):
    for line in proc.stdout:
        line = line.strip()
        if line.startswith('Fase '):
            phase['nome'] = line.split()[1].upper().replace('Ç', 'C').replace('Ã', 'A')
        elif line:
            phase['msg'] = line
    phase['fim'] = True

def linhas(path):
    try:
        text = Path(path).read_text(encoding='utf-8')
    except OSError:
        return []
    rows = text.splitlines()
    if text and not text.endswith('\n'):
        rows = rows[:-1]  # linha ainda incompleta
    return list(csv.DictReader(rows))

def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--saida', default='resultados/ensaio_' + time.strftime('%Y%m%d_%H%M%S'))
    p.add_argument('--taxa', type=float, default=50)
    known, extra = p.parse_known_args()
    cmd = [sys.executable, '-u', str(Path(__file__).with_name('laboratorio.py')),
           '--saida', known.saida, '--taxa', str(known.taxa)] + extra
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
    threading.Thread(target=ler_stdout, args=(proc,), daemon=True).start()
    folder = Path(known.saida)
    escala = max(known.taxa + 1, 2)
    largura = 40
    print(f'Pasta: {folder}\n{"t(s)":>5}  {"fase":<12} {"req/s":>6}  {"barra (escala 0-%d)" % escala:<{largura}}  {"lat ms":>7}  falhas')
    t, prev, falhas_prev = 0, 0, 0
    totais = {'NORMAL': [], 'CARGA': [], 'RECUPERACAO': []}
    while not phase['fim']:
        time.sleep(1)
        t += 1
        srv = linhas(folder / 'servidor.csv')
        cli = linhas(folder / 'cliente.csv')
        taxa = len(srv) - prev
        prev = len(srv)
        falhas = sum(1 - int(r['sucesso']) for r in cli)
        lat = float(cli[-1]['latencia_ms']) if cli else float('nan')
        n = phase['nome']
        cheio = min(largura, round(taxa / escala * largura))
        barra = '█' * cheio + '░' * (largura - cheio)
        aviso = '  <-- FALHA' if falhas > falhas_prev else ''
        falhas_prev = falhas
        print(f'{t:>5}  {COR.get(n, "")}{n:<12} {taxa:>6}  {barra}{RESET}  {lat:>7.2f}  {falhas:>6}{aviso}', flush=True)
        if n in totais:
            totais[n].append(taxa)
    proc.wait()
    print()
    for n, v in totais.items():
        if v:
            print(f'{n:<12} média {sum(v)/len(v):7.1f} req/s   máx {max(v)}')
    print(phase.get('msg', ''))
    sys.exit(proc.returncode)

if __name__ == '__main__':
    main()
