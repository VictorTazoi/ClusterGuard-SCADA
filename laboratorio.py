"""Laboratório Modbus TCP local. Python >=3.11; somente biblioteca padrão."""
import argparse
import asyncio
import csv
import json
import math
import random
import struct
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

ENDERECO_LOCAL = '127.0.0.1'
TIMEOUT_CONSULTA_S = 0.5
INTERVALO_SENSORES_S = 1
TAMANHO_CABECALHO_MODBUS_BYTES = 7
COMPRIMENTO_MINIMO_MODBUS_BYTES = 2
COMPRIMENTO_MAXIMO_MODBUS_BYTES = 254
QUANTIDADE_REGISTRADORES = 100
TEMPERATURA_NOMINAL = 60
VARIACAO_TEMPERATURA = 3
PRESSAO_NOMINAL = 100
VARIACAO_PRESSAO = 10

FEATURES = ['taxa_requisicoes', 'bytes_rx', 'bytes_tx', 'latencia_ms', 'taxa_timeout', 'taxa_erro']
EVENTS = [
    'ts', 'origem', 'sucesso', 'timeout', 'latencia_ms',
    'bytes_tx', 'bytes_rx', 'temp', 'pres', 'detalhe',
]

TAXA_MAXIMA_CARGA_RPS = 200
DURACAO_MAXIMA_CARGA_S = 120
DURACAO_MAXIMA_FASE_SEM_CARGA_S = 600
INTERVALO_MINIMO_CLIENTE_S = 0.1
JITTER_MAXIMO = 0.5
PORTA_MAXIMA = 65535
DESLOCAMENTO_SEED_CLIENTE = 10_000


@dataclass
class Configuracao:
    saida: str
    normal: float
    carga: float
    recuperacao: float
    taxa: float
    perfil_carga: str
    taxa_baixa: float
    taxa_media: float
    intervalo: float
    perfil_cliente: str
    jitter: float
    manutencao_inicio: float
    manutencao_duracao: float
    intervalo_manutencao: float
    port: int
    seed: int
    agregar: str | None


class Log:
    def __init__(self, path: str | Path, fields: Sequence[str]) -> None:
        self.arquivo = open(path, 'x', newline='', encoding='utf-8')
        self.escritor = csv.DictWriter(self.arquivo, fieldnames=fields)
        self.escritor.writeheader()

    def row(self, **registro: str | int | float) -> None:
        self.escritor.writerow(registro)
        self.arquivo.flush()

    def close(self) -> None:
        self.arquivo.close()


async def request(port: int, timeout: float = TIMEOUT_CONSULTA_S) -> dict[str, str | int | float]:
    """Consulta FC03 local; timeout em segundos e latência retornada em ms.

    Falhas previstas viram registros com sucesso=0. O campo timeout só vale 1
    quando a conexão já foi estabelecida; a latência inclui o fechamento.
    """
    ts, inicio_medicao = time.time(), time.perf_counter()
    writer = None
    conexao_estabelecida = False
    bytes_enviados = bytes_recebidos = 0
    tentativa = dict(ts=ts, sucesso=0, timeout=0, temp='', pres='', detalhe='')
    try:
        async with asyncio.timeout(timeout):
            reader, writer = await asyncio.open_connection(ENDERECO_LOCAL, port)
            conexao_estabelecida = True
            consulta = struct.pack('>HHHBBHH', 1, 0, 6, 1, 3, 0, 2)
            writer.write(consulta)
            bytes_enviados = len(consulta)
            await writer.drain()
            cabecalho = await reader.readexactly(TAMANHO_CABECALHO_MODBUS_BYTES)
            bytes_recebidos += len(cabecalho)
            transacao, protocolo, comprimento, unidade = struct.unpack('>HHHB', cabecalho)
            if not COMPRIMENTO_MINIMO_MODBUS_BYTES <= comprimento <= COMPRIMENTO_MAXIMO_MODBUS_BYTES:
                raise ValueError('comprimento Modbus invalido')
            corpo = await reader.readexactly(comprimento - 1)
            bytes_recebidos += len(corpo)
            if (transacao, protocolo, unidade) != (1, 0, 1) or len(corpo) != 6 or corpo[:2] != b'\x03\x04':
                raise ValueError('resposta Modbus inesperada')
            tentativa['temp'], tentativa['pres'] = struct.unpack('>HH', corpo[2:])
            tentativa['sucesso'] = 1
    except TimeoutError as exc:
        if conexao_estabelecida:
            tentativa.update(timeout=1, detalhe='timeout')
        else:
            tentativa['detalhe'] = type(exc).__name__ + ': conexão TCP não estabelecida'
    except (OSError, asyncio.IncompleteReadError, ValueError) as exc:
        tentativa['detalhe'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                # Uma falha no fechamento não substitui o resultado da tentativa.
                pass
    tentativa.update(
        latencia_ms=round((time.perf_counter() - inicio_medicao) * 1000, 6),
        bytes_tx=bytes_enviados,
        bytes_rx=bytes_recebidos,
    )
    return tentativa


class RTU:
    """Subconjunto Modbus TCP FC03. Mantém os mesmos sensores dos originais."""
    def __init__(self, log: Log, seed: int) -> None:
        self.log = log
        self.rng = random.Random(seed)
        self.values = (TEMPERATURA_NOMINAL, PRESSAO_NOMINAL)
        self.connections: set[asyncio.StreamWriter] = set()

    async def sensors(self) -> None:
        while True:
            self.values = (
                TEMPERATURA_NOMINAL + self.rng.randint(-VARIACAO_TEMPERATURA, VARIACAO_TEMPERATURA),
                PRESSAO_NOMINAL + self.rng.randint(-VARIACAO_PRESSAO, VARIACAO_PRESSAO),
            )
            await asyncio.sleep(INTERVALO_SENSORES_S)

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.connections.add(writer)
        try:
            while True:
                cabecalho = await reader.readexactly(TAMANHO_CABECALHO_MODBUS_BYTES)
                ts = time.time()
                transacao, protocolo, comprimento, unidade = struct.unpack('>HHHB', cabecalho)
                if protocolo != 0 or not (
                    COMPRIMENTO_MINIMO_MODBUS_BYTES <= comprimento <= COMPRIMENTO_MAXIMO_MODBUS_BYTES
                ):
                    break
                corpo = await reader.readexactly(comprimento - 1)
                if len(corpo) == 5 and corpo[0] == 3:
                    endereco, quantidade = struct.unpack('>HH', corpo[1:])
                    if (
                        1 <= quantidade <= QUANTIDADE_REGISTRADORES
                        and endereco + quantidade <= QUANTIDADE_REGISTRADORES
                    ):
                        registradores = list(self.values) + [0] * (QUANTIDADE_REGISTRADORES - 2)
                        conteudo_resposta = bytes([3, 2 * quantidade]) + struct.pack(
                            '>' + 'H' * quantidade,
                            *registradores[endereco:endereco + quantidade],
                        )
                    else:
                        conteudo_resposta = b'\x83\x02'
                else:
                    conteudo_resposta = bytes([(corpo[0] | 128), 1])
                resposta = struct.pack(
                    '>HHHB', transacao, 0, len(conteudo_resposta) + 1, unidade,
                ) + conteudo_resposta
                writer.write(resposta)
                await writer.drain()
                self.log.row(
                    ts=ts, bytes_rx=TAMANHO_CABECALHO_MODBUS_BYTES + len(corpo),
                    bytes_tx=len(resposta),
                )
        except (asyncio.IncompleteReadError, ConnectionError, OSError):
            # O cliente pode encerrar a conexão sem completar outra solicitação.
            pass
        finally:
            self.connections.discard(writer)
            writer.close()


async def polling(
    port: int, duration: float, interval: float, log: Log, origin: str,
    interval_fn: Callable[[float], float] | None = None,
) -> None:
    """Consulta sequencialmente por duration segundos; interval também está em segundos.

    interval_fn recebe o tempo decorrido após a tentativa. Atrasos não acumulam
    consultas pendentes: o próximo prazo nunca fica anterior ao instante atual.
    """
    inicio = time.monotonic()
    fim = time.monotonic() + duration
    proxima_consulta = time.monotonic()
    while time.monotonic() < fim:
        log.row(origem=origin, **(await request(port)))

        if interval_fn is not None:
            decorrido = time.monotonic() - inicio
            passo = interval_fn(decorrido)
        else:
            passo = interval

        proxima_consulta += passo
        proxima_consulta = max(proxima_consulta, time.monotonic())
        espera = max(0, min(proxima_consulta - time.monotonic(), fim - time.monotonic()))
        await asyncio.sleep(espera)


async def load(port: int, duration: float, rate: float, log: Log) -> None:
    # Sequencial, sem concorrência ilimitada: taxa solicitada é um teto.
    await polling(port, duration, 1 / rate, log, 'carga')

def intervalo_do_cliente(
    decorrido: float, args: Configuracao | argparse.Namespace, rng: random.Random,
) -> float:
    """Retorna segundos; manutenção inclui o início e exclui o fim.

    Fora da manutenção, o perfil fixo não consome sorteios. Na manutenção,
    o jitter também se aplica ao perfil fixo, conforme o comportamento original.
    """
    inicio_manutencao = args.manutencao_inicio
    fim_manutencao = args.manutencao_inicio + args.manutencao_duracao
    em_manutencao = (
        args.manutencao_duracao > 0
        and inicio_manutencao <= decorrido < fim_manutencao
    )
    if em_manutencao:
        intervalo_base = args.intervalo_manutencao
    elif args.perfil_cliente == 'fixo':
        return args.intervalo
    else:
        intervalo_base = args.intervalo
    fator = rng.uniform(1 - args.jitter, 1 + args.jitter)
    intervalo_s = intervalo_base * fator
    return max(INTERVALO_MINIMO_CLIENTE_S, intervalo_s)


@dataclass
class Janela:
    requisicoes: int = 0
    bytes_rx: int = 0
    bytes_tx: int = 0
    latencias_ms: list[float] = field(default_factory=list)
    falhas: int = 0
    timeouts: int = 0
    tentativas: int = 0


def aggregate(folder: str | Path) -> int:
    """Regrava somente os dois CSVs derivados e retorna a quantidade de janelas.

    Requer os logs de um ensaio e inicio/fim no JSON, em segundos Unix epoch.
    Falhas de leitura, conversão ou escrita são propagadas ao chamador.
    """
    pasta_ensaio = Path(folder)
    metadados = json.loads((pasta_ensaio / 'ensaio.json').read_text(encoding='utf-8'))
    with open(pasta_ensaio / 'ataques.csv', encoding='utf-8') as arquivo_ataques:
        periodos_carga = list(csv.DictReader(arquivo_ataques))
    inicio_ensaio, fim_ensaio = metadados['inicio'], metadados['fim']
    janelas = {
        indice: Janela() for indice in range(math.ceil(fim_ensaio - inicio_ensaio))
    }
    with open(pasta_ensaio / 'servidor.csv', encoding='utf-8') as arquivo_servidor:
        for registro in csv.DictReader(arquivo_servidor):
            indice = int(float(registro['ts']) - inicio_ensaio)
            if indice in janelas:
                janela = janelas[indice]
                janela.requisicoes += 1
                janela.bytes_rx += int(registro['bytes_rx'])
                janela.bytes_tx += int(registro['bytes_tx'])
    with open(pasta_ensaio / 'cliente.csv', encoding='utf-8') as arquivo_cliente:
        for registro in csv.DictReader(arquivo_cliente):
            indice = int(float(registro['ts']) - inicio_ensaio)
            if indice in janelas:
                janela = janelas[indice]
                janela.tentativas += 1
                janela.latencias_ms.append(float(registro['latencia_ms']))
                janela.timeouts += int(registro['timeout'])
                janela.falhas += 1 - int(registro['sucesso'])
    # Reagregação explícita substitui somente arquivos derivados.
    with (
        open(pasta_ensaio / 'features.csv', 'w', newline='', encoding='utf-8') as arquivo_features,
        open(pasta_ensaio / 'avaliacao.csv', 'w', newline='', encoding='utf-8') as arquivo_avaliacao,
    ):
        campos = ['janela', 'ts_inicio', 'duracao_s'] + FEATURES + [
            'consultas_cliente', 'latencia_disponivel',
        ]
        escritor_features = csv.DictWriter(arquivo_features, fieldnames=campos)
        escritor_features.writeheader()
        escritor_avaliacao = csv.DictWriter(
            arquivo_avaliacao, fieldnames=['janela', 'label', 'fase'],
        )
        escritor_avaliacao.writeheader()
        for indice, janela in janelas.items():
            inicio_janela = inicio_ensaio + indice
            fim_janela = min(inicio_janela + 1, fim_ensaio)
            duracao_janela_s = fim_janela - inicio_janela
            sobrepoe_carga = any(
                float(periodo['inicio']) < fim_janela
                and float(periodo['fim']) > inicio_janela
                for periodo in periodos_carga
            )
            registro = dict(
                janela=indice,
                ts_inicio=inicio_janela,
                duracao_s=duracao_janela_s,
                taxa_requisicoes=janela.requisicoes / duracao_janela_s,
                bytes_rx=janela.bytes_rx,
                bytes_tx=janela.bytes_tx,
                latencia_ms=(
                    sum(janela.latencias_ms) / len(janela.latencias_ms)
                    if janela.latencias_ms else ''
                ),
                taxa_timeout=janela.timeouts / janela.tentativas if janela.tentativas else '',
                taxa_erro=janela.falhas / janela.tentativas if janela.tentativas else '',
                consultas_cliente=janela.tentativas,
                latencia_disponivel=int(bool(janela.latencias_ms)),
            )
            escritor_features.writerow(registro)
            fase = 'carga' if sobrepoe_carga else (
                'normal' if inicio_janela < float(periodos_carga[0]['inicio']) else 'recuperacao'
            )
            escritor_avaliacao.writerow(dict(janela=indice, label=int(sobrepoe_carga), fase=fase))
    return len(janelas)


async def run(args: Configuracao | argparse.Namespace) -> None:
    pasta_ensaio = Path(args.saida)
    pasta_ensaio.mkdir(parents=True, exist_ok=False)
    registros_abertos = []
    tarefas = []
    servidor = None
    try:
        def abrir_log(nome: str, campos: Sequence[str]) -> Log:
            registro = Log(pasta_ensaio / nome, campos)
            registros_abertos.append(registro)
            return registro

        log_servidor = abrir_log('servidor.csv', ['ts', 'bytes_rx', 'bytes_tx'])
        log_cliente = abrir_log('cliente.csv', EVENTS)
        log_carga = abrir_log('carga.csv', EVENTS)
        log_ataques = abrir_log('ataques.csv', ['inicio', 'fim', 'tipo', 'taxa_alvo_rps'])
        atividades_log = abrir_log('atividades_legitimas.csv', ['inicio', 'fim', 'tipo'])
        rtu = RTU(log_servidor, args.seed)
        # Bind exclusivo: nunca usa um servidor desconhecido na porta ocupada.
        servidor = await asyncio.start_server(rtu.handle, ENDERECO_LOCAL, args.port)
        port = servidor.sockets[0].getsockname()[1]
        tarefas.append(asyncio.create_task(rtu.sensors()))
        inicio_ensaio = time.time()
        duracao_total_s = args.normal + args.carga + args.recuperacao
        if args.manutencao_duracao > 0:
            atividades_log.row(
                inicio=inicio_ensaio + args.manutencao_inicio,
                fim=inicio_ensaio + args.manutencao_inicio + args.manutencao_duracao,
                tipo='manutencao_legitima',
            )
        rng_cliente = random.Random(args.seed + DESLOCAMENTO_SEED_CLIENTE)

        def proximo_intervalo(decorrido: float) -> float:
            return intervalo_do_cliente(decorrido, args, rng_cliente)

        tarefa_cliente = asyncio.create_task(polling(
            port, duracao_total_s, args.intervalo, log_cliente, 'legitimo', proximo_intervalo,
        ))
        tarefas.append(tarefa_cliente)
        print('Fase NORMAL', flush=True)
        await asyncio.sleep(args.normal)
        print("Fase CARGA controlada", flush=True)
        if args.perfil_carga == "degraus":
            segmentos = [
                ('baixa', args.taxa_baixa), ('media', args.taxa_media), ('alta', args.taxa),
            ]
        else:
            segmentos = [("fixa", args.taxa)]

        duracao_segmento = args.carga / len(segmentos)
        for nivel, taxa in segmentos:
            inicio_segmento = time.time()

            print(f" Carga {nivel}: {taxa} req/s", flush=True)

            await load(port, duracao_segmento, taxa, log_carga)
            fim_segmento = time.time()
            log_ataques.row(
                inicio=inicio_segmento, fim=fim_segmento,
                tipo=f'carga_{nivel}', taxa_alvo_rps=taxa,
            )

        print('Fase RECUPERACAO', flush=True)
        await asyncio.sleep(args.recuperacao)
        await tarefa_cliente
        fim_ensaio = inicio_ensaio + duracao_total_s
        metadados = dict(
            inicio=inicio_ensaio, fim=fim_ensaio, config=vars(args), porta_efetiva=port,
            bytes='ADU Modbus TCP; sem cabecalhos TCP/IP/Ethernet',
            ambiente='loopback; servidor, cliente e carga no mesmo processo asyncio',
            status='completo',
        )
        (pasta_ensaio / 'ensaio.json').write_text(
            json.dumps(metadados, indent=2, ensure_ascii=False), encoding='utf-8',
        )
    finally:
        if servidor:
            servidor.close()
            await servidor.wait_closed()
        for tarefa in tarefas:
            tarefa.cancel()
        await asyncio.gather(*tarefas, return_exceptions=True)
        if servidor:
            for writer in list(rtu.connections):
                writer.close()
        for registro in registros_abertos:
            registro.close()
    quantidade_janelas = aggregate(pasta_ensaio)
    print(f'Concluido: {pasta_ensaio} ({quantidade_janelas} janelas).', flush=True)

def positive(value: str) -> float:
    numero = float(value)
    if not math.isfinite(numero) or numero <= 0:
        raise argparse.ArgumentTypeError('use numero positivo e finito')
    return numero

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida',default='resultados/ensaio_'+time.strftime('%Y%m%d_%H%M%S'))
    parser.add_argument('--normal',type=positive,default=60)
    parser.add_argument('--carga',type=positive,default=20)
    parser.add_argument('--recuperacao',type=positive,default=60)
    parser.add_argument('--taxa',type=positive,default=50)
    parser.add_argument("--perfil-carga",choices=["fixa","degraus"],default="fixa")
    parser.add_argument("--taxa-baixa",type=positive,default=2)
    parser.add_argument("--taxa-media",type=positive,default=5)
    parser.add_argument('--intervalo',type=positive,default=1)
    parser.add_argument("--perfil-cliente",choices=["fixo","variavel"],default="fixo")
    parser.add_argument("--jitter",type=float,default=0.30)
    parser.add_argument("--manutencao-inicio",type=float,default=0)
    parser.add_argument("--manutencao-duracao",type=float,default=0)
    parser.add_argument("--intervalo-manutencao",type=positive,default=0.20)
    parser.add_argument('--port',type=int,default=5020)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--agregar',metavar='PASTA',help='recalcula CSVs de um ensaio completo')
    configuracao = Configuracao(**vars(parser.parse_args()))
    if configuracao.agregar:
        print(aggregate(configuracao.agregar))
        return
    if (
        configuracao.taxa > TAXA_MAXIMA_CARGA_RPS
        or configuracao.carga > DURACAO_MAXIMA_CARGA_S
        or configuracao.normal > DURACAO_MAXIMA_FASE_SEM_CARGA_S
        or configuracao.recuperacao > DURACAO_MAXIMA_FASE_SEM_CARGA_S
        or configuracao.intervalo < INTERVALO_MINIMO_CLIENTE_S
        or not 0 <= configuracao.port <= PORTA_MAXIMA
        or not math.isfinite(configuracao.jitter)
        or not 0 <= configuracao.jitter <= JITTER_MAXIMO
        or not math.isfinite(configuracao.manutencao_inicio)
        or not math.isfinite(configuracao.manutencao_duracao)
        or configuracao.manutencao_inicio < 0
        or configuracao.manutencao_duracao < 0
        or configuracao.manutencao_inicio + configuracao.manutencao_duracao > configuracao.normal
        or configuracao.intervalo_manutencao < INTERVALO_MINIMO_CLIENTE_S
        or (
            configuracao.perfil_carga == 'degraus'
            and not configuracao.taxa_baixa <= configuracao.taxa_media <= configuracao.taxa
        )
    ):
        parser.error("limites: taxa <=200, carga <=120s, normal/recuperacao <=600s, intervalo >=0.1s, jitter 0..0.5, porta 0..65535")
    try:
        asyncio.run(run(configuracao))
    except KeyboardInterrupt:
        print('Interrompido: pasta parcial; nao usar como ensaio completo.')
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Falha: {exc}\nUse outra pasta de saida/porta.\n')

if __name__=='__main__':
    main()
