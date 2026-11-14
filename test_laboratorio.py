import asyncio
import argparse
from contextlib import redirect_stderr
import csv
import io
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from laboratorio import aggregate, intervalo_do_cliente, main, request

class Communication(unittest.IsolatedAsyncioTestCase):
    async def test_connection_refused_is_logged(self):
        server=await asyncio.start_server(lambda r,w: None,'127.0.0.1',0)
        port=server.sockets[0].getsockname()[1]
        server.close(); await server.wait_closed()
        result=await request(port)
        self.assertEqual(result['sucesso'],0)
        self.assertEqual(result['timeout'],0)
        self.assertIn('Error',result['detalhe'])

    async def test_timeout_is_distinct(self):
        writers=[]
        async def silent(reader,writer):
            writers.append(writer)
            await reader.read()
            writer.close()
        server=await asyncio.start_server(silent,'127.0.0.1',0)
        try:
            result=await request(server.sockets[0].getsockname()[1],0.05)
            self.assertEqual(result['timeout'],1)
            self.assertEqual(result['sucesso'],0)
        finally:
            server.close(); await server.wait_closed()
            for writer in writers: writer.close()

class Experiment(unittest.TestCase):
    def test_full_experiment_and_reaggregation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'ensaio'
            subprocess.run([sys.executable,'laboratorio.py','--saida',str(folder),'--port','0','--normal','1','--carga','1','--recuperacao','1','--taxa','20','--intervalo','0.2'],check=True,capture_output=True)
            def rows(name):
                with open(folder/name,encoding='utf-8') as f: return list(csv.DictReader(f))
            features=rows('features.csv'); evaluation=rows('avaliacao.csv')
            self.assertEqual(len(features),3)
            self.assertEqual(len(evaluation),3)
            self.assertNotIn('label',features[0])
            self.assertTrue(any(int(r['label']) for r in evaluation))
            load=rows('carga.csv')
            self.assertGreater(len(load),10)
            clients=rows('cliente.csv')
            self.assertTrue(all(r['sucesso']=='1' for r in clients+load))
            self.assertTrue(all(57<=int(r['temp'])<=63 and 90<=int(r['pres'])<=110 for r in clients+load))
            server=rows('servidor.csv')
            self.assertTrue(all(int(r['bytes_rx'])==12 and int(r['bytes_tx'])==13 for r in server))
            before=(folder/'features.csv').read_bytes()
            arquivos_antes = {
                caminho.name: caminho.read_bytes() for caminho in folder.iterdir()
            }
            subprocess.run([sys.executable,'laboratorio.py','--agregar',str(folder)],check=True,capture_output=True)
            self.assertEqual(before,(folder/'features.csv').read_bytes())
            self.assertEqual(
                arquivos_antes,
                {caminho.name: caminho.read_bytes() for caminho in folder.iterdir()},
            )
            r=subprocess.run([sys.executable,'laboratorio.py','--saida',str(folder)],capture_output=True)
            self.assertNotEqual(r.returncode,0)

    def test_limits(self):
        for args in [['--taxa','201'],['--carga','121'],['--taxa','nan'],['--intervalo','0']]:
            r=subprocess.run([sys.executable,'laboratorio.py']+args,capture_output=True)
            self.assertNotEqual(r.returncode,0)

    def test_degraus_e_manutencao_sao_registrados_separadamente(self):
        with tempfile.TemporaryDirectory() as pasta_temporaria:
            pasta_ensaio = Path(pasta_temporaria) / 'ensaio'
            subprocess.run([
                sys.executable, 'laboratorio.py', '--saida', str(pasta_ensaio),
                '--port', '0', '--normal', '1', '--carga', '1', '--recuperacao', '1',
                '--perfil-carga', 'degraus', '--taxa-baixa', '2',
                '--taxa-media', '5', '--taxa', '10',
                '--perfil-cliente', 'variavel', '--seed', '43',
                '--manutencao-inicio', '0.2', '--manutencao-duracao', '0.4',
            ], check=True, capture_output=True, timeout=30)
            with (pasta_ensaio / 'ataques.csv').open(encoding='utf-8', newline='') as arquivo:
                segmentos = list(csv.DictReader(arquivo))
            with (pasta_ensaio / 'atividades_legitimas.csv').open(encoding='utf-8', newline='') as arquivo:
                atividades = list(csv.DictReader(arquivo))
            metadados = json.loads((pasta_ensaio / 'ensaio.json').read_text(encoding='utf-8'))
            self.assertEqual([segmento['tipo'] for segmento in segmentos], [
                'carga_baixa', 'carga_media', 'carga_alta',
            ])
            self.assertEqual([float(segmento['taxa_alvo_rps']) for segmento in segmentos], [2, 5, 10])
            for segmento in segmentos:
                self.assertLess(float(segmento['inicio']), float(segmento['fim']))
            for anterior, seguinte in zip(segmentos, segmentos[1:]):
                self.assertLessEqual(float(anterior['fim']), float(seguinte['inicio']))
            self.assertEqual(len(atividades), 1)
            self.assertEqual(atividades[0]['tipo'], 'manutencao_legitima')
            self.assertEqual(float(atividades[0]['inicio']), metadados['inicio'] + 0.2)
            self.assertEqual(float(atividades[0]['fim']), metadados['inicio'] + 0.2 + 0.4)
            self.assertEqual(metadados['config']['seed'], 43)
            self.assertEqual(metadados['status'], 'completo')

class Agregacao(unittest.TestCase):
    def setUp(self):
        pasta_temporaria = tempfile.TemporaryDirectory()
        self.addCleanup(pasta_temporaria.cleanup)
        self.pasta_ensaio = Path(pasta_temporaria.name)
        (self.pasta_ensaio / 'ensaio.json').write_text(
            json.dumps({'inicio': 1000, 'fim': 1002.5, 'status': 'completo'}),
            encoding='utf-8',
        )
        (self.pasta_ensaio / 'ataques.csv').write_text(
            'inicio,fim,tipo,taxa_alvo_rps\n1001,1002,carga_fixa,20\n',
            encoding='utf-8',
        )
        (self.pasta_ensaio / 'servidor.csv').write_text(
            'ts,bytes_rx,bytes_tx\n'
            '1000.1,12,13\n1001,12,13\n1002.1,12,13\n1002.3,12,13\n',
            encoding='utf-8',
        )
        (self.pasta_ensaio / 'cliente.csv').write_text(
            'ts,sucesso,timeout,latencia_ms\n'
            '1000.1,1,0,5\n1002.1,1,0,10\n1002.2,0,0,20\n1002.3,0,1,30\n',
            encoding='utf-8',
        )
        aggregate(self.pasta_ensaio)
        with (self.pasta_ensaio / 'features.csv').open(encoding='utf-8', newline='') as arquivo:
            self.janelas = list(csv.DictReader(arquivo))
        with (self.pasta_ensaio / 'avaliacao.csv').open(encoding='utf-8', newline='') as arquivo:
            self.avaliacao = list(csv.DictReader(arquivo))

    def test_cabecalho_preserva_ordem_das_seis_entradas_sem_rotulos(self):
        self.assertEqual(list(self.janelas[0]), [
            'janela', 'ts_inicio', 'duracao_s',
            'taxa_requisicoes', 'bytes_rx', 'bytes_tx',
            'latencia_ms', 'taxa_timeout', 'taxa_erro',
            'consultas_cliente', 'latencia_disponivel',
        ])
        self.assertEqual(list(self.avaliacao[0]), ['janela', 'label', 'fase'])

    def test_janela_sem_consulta_legitima_nao_vira_zero(self):
        janela = self.janelas[1]
        self.assertEqual(janela['consultas_cliente'], '0')
        self.assertEqual(janela['latencia_disponivel'], '0')
        for coluna in ('latencia_ms', 'taxa_timeout', 'taxa_erro'):
            with self.subTest(coluna=coluna):
                self.assertEqual(janela[coluna], '')
        self.assertEqual(float(janela['taxa_requisicoes']), 1)

    def test_janela_parcial_normaliza_taxa_mas_preserva_volume_de_bytes(self):
        self.assertEqual(len(self.janelas), 3)
        janela = self.janelas[2]
        self.assertEqual(float(janela['duracao_s']), 0.5)
        self.assertEqual(float(janela['taxa_requisicoes']), 4)
        self.assertEqual(int(janela['bytes_rx']), 24)
        self.assertEqual(int(janela['bytes_tx']), 26)

    def test_falhas_entram_na_latencia_e_timeout_tambem_conta_como_erro(self):
        janela = self.janelas[2]
        self.assertEqual(int(janela['consultas_cliente']), 3)
        self.assertEqual(janela['latencia_disponivel'], '1')
        self.assertEqual(float(janela['latencia_ms']), 20)
        self.assertAlmostEqual(float(janela['taxa_timeout']), 1 / 3)
        self.assertAlmostEqual(float(janela['taxa_erro']), 2 / 3)

    def test_carga_na_fronteira_nao_rotula_janelas_apenas_adjacentes(self):
        self.assertEqual(self.avaliacao, [
            {'janela': '0', 'label': '0', 'fase': 'normal'},
            {'janela': '1', 'label': '1', 'fase': 'carga'},
            {'janela': '2', 'label': '0', 'fase': 'recuperacao'},
        ])


class IntervalosDoCliente(unittest.TestCase):
    def setUp(self):
        self.configuracao = argparse.Namespace(
            intervalo=1, perfil_cliente='fixo', jitter=0.3,
            manutencao_inicio=20, manutencao_duracao=15,
            intervalo_manutencao=0.2,
        )

    def test_perfil_fixo_fora_da_manutencao_nao_consome_sorteios(self):
        gerador = random.Random(42)
        estado_inicial = gerador.getstate()
        self.assertEqual(intervalo_do_cliente(0, self.configuracao, gerador), 1)
        self.assertEqual(gerador.getstate(), estado_inicial)

    def test_perfil_variavel_repete_intervalos_com_a_mesma_seed(self):
        self.configuracao.perfil_cliente = 'variavel'
        primeiro_gerador = random.Random(42)
        segundo_gerador = random.Random(42)
        primeira_sequencia = [
            intervalo_do_cliente(segundo, self.configuracao, primeiro_gerador)
            for segundo in range(20)
        ]
        segunda_sequencia = [
            intervalo_do_cliente(segundo, self.configuracao, segundo_gerador)
            for segundo in range(20)
        ]
        self.assertEqual(primeira_sequencia, segunda_sequencia)
        self.assertGreater(len(set(primeira_sequencia)), 1)
        self.assertTrue(all(0.7 <= intervalo <= 1.3 for intervalo in primeira_sequencia))

    def test_manutencao_inclui_inicio_e_exclui_fim(self):
        self.configuracao.jitter = 0
        gerador = random.Random(42)
        for segundo, intervalo_esperado in ((19.9, 1), (20, 0.2), (34.9, 0.2), (35, 1)):
            with self.subTest(segundo=segundo):
                self.assertEqual(
                    intervalo_do_cliente(segundo, self.configuracao, gerador),
                    intervalo_esperado,
                )

    def test_jitter_respeita_intervalo_minimo_de_um_decimo_de_segundo(self):
        self.configuracao.perfil_cliente = 'variavel'
        self.configuracao.intervalo = 0.1
        self.configuracao.jitter = 0.5
        gerador = random.Random(42)
        intervalos = [
            intervalo_do_cliente(segundo, self.configuracao, gerador)
            for segundo in range(20)
        ]
        self.assertTrue(all(intervalo >= 0.1 for intervalo in intervalos))
        self.assertIn(0.1, intervalos)


class LimitesDaCLI(unittest.TestCase):
    def test_parametros_invalidos_sao_rejeitados_antes_de_iniciar_ensaio(self):
        casos = [
            ['--normal', '601'], ['--recuperacao', '601'],
            ['--intervalo', '0.09'], ['--port', '-1'], ['--port', '65536'],
            ['--jitter', '-0.01'], ['--jitter', '0.51'], ['--jitter', 'nan'],
            ['--manutencao-inicio', '-1'], ['--manutencao-inicio', 'inf'],
            ['--manutencao-duracao', '-1'], ['--manutencao-duracao', 'nan'],
            ['--manutencao-inicio', '50', '--manutencao-duracao', '11'],
            ['--intervalo-manutencao', '0.09'],
            ['--perfil-carga', 'degraus', '--taxa-baixa', '6', '--taxa-media', '5'],
            ['--perfil-carga', 'degraus', '--taxa-media', '51'],
            ['--perfil-carga', 'degraus', '--taxa-baixa', '201', '--taxa-media', '201', '--taxa', '201'],
            ['--taxa-baixa', '0'], ['--taxa-media', 'inf'],
            ['--normal', 'nan'], ['--carga', 'inf'], ['--recuperacao', '-1'],
            ['--host', '192.0.2.1'],
        ]
        for argumentos in casos:
            with self.subTest(argumentos=argumentos):
                with (
                    patch.object(sys, 'argv', ['laboratorio.py', *argumentos]),
                    patch('laboratorio.run', new_callable=Mock) as executar_ensaio,
                    patch('laboratorio.asyncio.run'),
                    redirect_stderr(io.StringIO()),
                ):
                    with self.assertRaises(SystemExit) as encerramento:
                        main()
                    self.assertEqual(encerramento.exception.code, 2)
                    executar_ensaio.assert_not_called()

    def test_valores_exatos_dos_limites_permanecem_aceitos(self):
        argumentos = [
            '--taxa', '200', '--carga', '120', '--normal', '600',
            '--recuperacao', '600', '--intervalo', '0.1',
            '--perfil-carga', 'degraus', '--taxa-baixa', '200', '--taxa-media', '200',
            '--manutencao-inicio', '0', '--manutencao-duracao', '600',
            '--intervalo-manutencao', '0.1',
        ]
        for porta, jitter in (('0', '0'), ('65535', '0.5')):
            with self.subTest(porta=porta, jitter=jitter):
                with (
                    patch.object(sys, 'argv', [
                        'laboratorio.py', *argumentos, '--port', porta, '--jitter', jitter,
                    ]),
                    patch('laboratorio.run', new_callable=Mock) as executar_ensaio,
                    patch('laboratorio.asyncio.run'),
                ):
                    main()
                    executar_ensaio.assert_called_once()


if __name__=='__main__': unittest.main(verbosity=2)
