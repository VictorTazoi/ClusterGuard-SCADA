import asyncio
import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from laboratorio import request

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
            subprocess.run([sys.executable,'laboratorio.py','--agregar',str(folder)],check=True,capture_output=True)
            self.assertEqual(before,(folder/'features.csv').read_bytes())
            r=subprocess.run([sys.executable,'laboratorio.py','--saida',str(folder)],capture_output=True)
            self.assertNotEqual(r.returncode,0)

    def test_limits(self):
        for args in [['--taxa','201'],['--carga','121'],['--taxa','nan'],['--intervalo','0']]:
            r=subprocess.run([sys.executable,'laboratorio.py']+args,capture_output=True)
            self.assertNotEqual(r.returncode,0)

if __name__=='__main__': unittest.main(verbosity=2)
