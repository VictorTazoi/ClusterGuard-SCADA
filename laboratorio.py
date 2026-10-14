"""Laboratório Modbus TCP local. Python >=3.11; somente biblioteca padrão."""
import argparse
import asyncio
import csv
import json
import math
import random
import struct
import time
from pathlib import Path

FEATURES = ['taxa_requisicoes', 'bytes_rx', 'bytes_tx', 'latencia_ms', 'taxa_timeout', 'taxa_erro']
EVENTS = ['ts', 'origem', 'sucesso', 'timeout', 'latencia_ms', 'bytes_tx', 'bytes_rx', 'temp', 'pres', 'detalhe']

class Log:
    def __init__(self, path, fields):
        self.f = open(path, 'x', newline='', encoding='utf-8')
        self.w = csv.DictWriter(self.f, fieldnames=fields)
        self.w.writeheader()
    def row(self, **row):
        self.w.writerow(row)
        self.f.flush()
    def close(self):
        self.f.close()

async def request(port, timeout=0.5):
    """Uma leitura FC03, unit id 1, endereço 0, dois registradores."""
    ts, start = time.time(), time.perf_counter()
    writer = None
    sent = received = 0
    out = dict(ts=ts, sucesso=0, timeout=0, temp='', pres='', detalhe='')
    try:
        async with asyncio.timeout(timeout):
            reader, writer = await asyncio.open_connection('127.0.0.1', port)
            packet = struct.pack('>HHHBBHH', 1, 0, 6, 1, 3, 0, 2)
            writer.write(packet)
            sent = len(packet)
            await writer.drain()
            header = await reader.readexactly(7)
            received += len(header)
            tid, proto, length, unit = struct.unpack('>HHHB', header)
            if not 2 <= length <= 254:
                raise ValueError('comprimento Modbus invalido')
            body = await reader.readexactly(length - 1)
            received += len(body)
            if (tid, proto, unit) != (1, 0, 1) or len(body) != 6 or body[:2] != b'\x03\x04':
                raise ValueError('resposta Modbus inesperada')
            out['temp'], out['pres'] = struct.unpack('>HH', body[2:])
            out['sucesso'] = 1
    except TimeoutError:
        out.update(timeout=1, detalhe='timeout')
    except (OSError, asyncio.IncompleteReadError, ValueError) as exc:
        out['detalhe'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass
    out.update(latencia_ms=round((time.perf_counter()-start)*1000, 6), bytes_tx=sent, bytes_rx=received)
    return out

class RTU:
    """Subconjunto Modbus TCP FC03. Mantém os mesmos sensores dos originais."""
    def __init__(self, log, seed):
        self.log = log
        self.rng = random.Random(seed)
        self.values = (60, 100)
        self.connections = set()
    async def sensors(self):
        while True:
            self.values = (60+self.rng.randint(-3,3), 100+self.rng.randint(-10,10))
            await asyncio.sleep(1)
    async def handle(self, reader, writer):
        self.connections.add(writer)
        try:
            while True:
                header = await reader.readexactly(7)
                ts = time.time()
                tid, proto, length, unit = struct.unpack('>HHHB', header)
                if proto != 0 or not 2 <= length <= 254:
                    break
                body = await reader.readexactly(length-1)
                if len(body) == 5 and body[0] == 3:
                    addr, count = struct.unpack('>HH', body[1:])
                    if 1 <= count <= 100 and addr+count <= 100:
                        regs = list(self.values) + [0]*98
                        payload = bytes([3, 2*count]) + struct.pack('>'+'H'*count, *regs[addr:addr+count])
                    else:
                        payload = b'\x83\x02'
                else:
                    payload = bytes([(body[0] | 128), 1])
                response = struct.pack('>HHHB', tid, 0, len(payload)+1, unit)+payload
                writer.write(response)
                await writer.drain()
                self.log.row(ts=ts, bytes_rx=7+len(body), bytes_tx=len(response))
        except (asyncio.IncompleteReadError, ConnectionError, OSError):
            pass
        finally:
            self.connections.discard(writer)
            writer.close()

async def polling(port, duration, interval, log, origin):
    end = time.monotonic()+duration
    deadline = time.monotonic()
    while time.monotonic() < end:
        log.row(origem=origin, **(await request(port)))
        deadline += interval
        # Não dispara rajada para compensar consultas atrasadas.
        deadline = max(deadline, time.monotonic())
        await asyncio.sleep(max(0, min(deadline-time.monotonic(), end-time.monotonic())))

async def load(port, duration, rate, log):
    # Sequencial, sem concorrência ilimitada: taxa solicitada é um teto.
    await polling(port, duration, 1/rate, log, 'carga')

def aggregate(folder):
    folder = Path(folder)
    meta = json.loads((folder/'ensaio.json').read_text(encoding='utf-8'))
    attack = list(csv.DictReader(open(folder/'ataques.csv', encoding='utf-8')))
    start, end = meta['inicio'], meta['fim']
    bins = {}
    for i in range(math.ceil(end-start)):
        bins[i] = dict(n=0, rx=0, tx=0, lat=[], failures=0, timeouts=0, attempts=0)
    with open(folder/'servidor.csv', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            i = int(float(row['ts'])-start)
            if i in bins:
                b = bins[i]; b['n'] += 1; b['rx'] += int(row['bytes_rx']); b['tx'] += int(row['bytes_tx'])
    with open(folder/'cliente.csv', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            i = int(float(row['ts'])-start)
            if i in bins:
                b = bins[i]; b['attempts'] += 1
                b['lat'].append(float(row['latencia_ms']))
                b['timeouts'] += int(row['timeout'])
                b['failures'] += 1-int(row['sucesso'])
    paths = ['features.csv', 'avaliacao.csv']
    # Reagregação explícita substitui somente arquivos derivados.
    with open(folder/paths[0], 'w', newline='', encoding='utf-8') as f, open(folder/paths[1], 'w', newline='', encoding='utf-8') as g:
        fields = ['janela', 'ts_inicio', 'duracao_s']+FEATURES+['consultas_cliente', 'latencia_disponivel']
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        v = csv.DictWriter(g, fieldnames=['janela','label','fase']); v.writeheader()
        for i,b in bins.items():
            lo = start+i; hi = min(lo+1,end); dt=hi-lo
            attacked = any(float(a['inicio']) < hi and float(a['fim']) > lo for a in attack)
            row = dict(janela=i, ts_inicio=lo, duracao_s=dt, taxa_requisicoes=b['n']/dt, bytes_rx=b['rx'], bytes_tx=b['tx'], latencia_ms=sum(b['lat'])/len(b['lat']) if b['lat'] else '', taxa_timeout=b['timeouts']/b['attempts'] if b['attempts'] else '', taxa_erro=b['failures']/b['attempts'] if b['attempts'] else '', consultas_cliente=b['attempts'], latencia_disponivel=int(bool(b['lat'])))
            w.writerow(row)
            phase = 'carga' if attacked else ('normal' if lo < float(attack[0]['inicio']) else 'recuperacao')
            v.writerow(dict(janela=i,label=int(attacked),fase=phase))
    return len(bins)

async def run(args):
    folder = Path(args.saida)
    folder.mkdir(parents=True, exist_ok=False)
    logs=[]; tasks=[]; server=None
    try:
        def log(name, fields):
            obj=Log(folder/name,fields); logs.append(obj); return obj
        serverlog=log('servidor.csv',['ts','bytes_rx','bytes_tx'])
        clientlog=log('cliente.csv',EVENTS)
        loadlog=log('carga.csv',EVENTS)
        attacks=log('ataques.csv',['inicio','fim','tipo','taxa_alvo_rps'])
        rtu=RTU(serverlog,args.seed)
        # Bind exclusivo: nunca usa um servidor desconhecido na porta ocupada.
        server=await asyncio.start_server(rtu.handle,'127.0.0.1',args.port)
        port=server.sockets[0].getsockname()[1]
        tasks.append(asyncio.create_task(rtu.sensors()))
        start=time.time()
        total=args.normal+args.carga+args.recuperacao
        tasks.append(asyncio.create_task(polling(port,total,args.intervalo,clientlog,'legitimo')))
        print('Fase NORMAL', flush=True)
        await asyncio.sleep(args.normal)
        attackstart=time.time()
        print('Fase CARGA controlada', flush=True)
        await load(port,args.carga,args.taxa,loadlog)
        attackend=time.time()
        attacks.row(inicio=attackstart,fim=attackend,tipo='carga_Modbus_FC03',taxa_alvo_rps=args.taxa)
        print('Fase RECUPERACAO', flush=True)
        await asyncio.sleep(args.recuperacao)
        await tasks[1]
        end=start+total
        metadata=dict(inicio=start,fim=end,config=vars(args),porta_efetiva=port,bytes='ADU Modbus TCP; sem cabecalhos TCP/IP/Ethernet',ambiente='loopback; servidor, cliente e carga no mesmo processo asyncio',status='completo')
        (folder/'ensaio.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    finally:
        if server:
            server.close(); await server.wait_closed()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        if server:
            for writer in list(rtu.connections):
                writer.close()
        for obj in logs:
            obj.close()
    n=aggregate(folder)
    print(f'Concluido: {folder} ({n} janelas).',flush=True)

def positive(value):
    n=float(value)
    if not math.isfinite(n) or n <= 0:
        raise argparse.ArgumentTypeError('use numero positivo e finito')
    return n

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--saida',default='resultados/ensaio_'+time.strftime('%Y%m%d_%H%M%S'))
    p.add_argument('--normal',type=positive,default=60)
    p.add_argument('--carga',type=positive,default=20)
    p.add_argument('--recuperacao',type=positive,default=60)
    p.add_argument('--taxa',type=positive,default=50)
    p.add_argument('--intervalo',type=positive,default=1)
    p.add_argument('--port',type=int,default=5020)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--agregar',metavar='PASTA',help='recalcula CSVs de um ensaio completo')
    a=p.parse_args()
    if a.agregar:
        print(aggregate(a.agregar)); return
    if a.taxa>200 or a.carga>120 or a.normal>600 or a.recuperacao>600 or a.intervalo<0.1 or not 0<=a.port<=65535:
        p.error('limites: taxa <=200, carga <=120s, normal/recuperacao <=600s, intervalo >=0.1s, porta 0..65535')
    try:
        asyncio.run(run(a))
    except KeyboardInterrupt:
        print('Interrompido: pasta parcial; nao usar como ensaio completo.')
    except (OSError, ValueError) as exc:
        p.exit(1, f'Falha: {exc}\nUse outra pasta de saida/porta.\n')

if __name__=='__main__':
    main()
