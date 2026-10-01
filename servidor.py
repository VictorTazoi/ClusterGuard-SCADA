import argparse
import asyncio
import math
import random
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartAsyncTcpServer

# atualizar_sensores realiza o input randomico de dados como temperatura e pressão, simulamos também uma variação
async def atualizar_sensores(context: ModbusServerContext, slave_id: int = 0):
    t = 0
    while True:
        temperatura_normal = 250 # temperatura padrão
        temperatura = temperatura_normal + random.randint(-3, 3) # pega a temperatura padrão e simula uma variação

        pressao_normal = 1000 # pressao padrão
        pressao = pressao_normal + random.randint(-10, 10) # pega a pressao padrão e simula uma variação

        context[slave_id].setValues(3, 0, [temperatura, pressao])  # holding registers
        t += 1
        await asyncio.sleep(1)

async def main():
    parser = argparse.ArgumentParser(description="Servidor Modbus TCP - ClusterGuard SCADA")
    parser.add_argument("--host", default="0.0.0.0", help="Endereço RX (padrão: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5020, help="Porta Modbus TCP (padrão: 5020)")
    parser.add_argument("--num-regs", type=int, default=100, help="Quantidade de holding registers")
    args = parser.parse_args()

    store = ModbusSlaveContext(
        hr=ModbusSequentialDataBlock(0, [0] * args.num_regs),  # Holding Registers
        ir=ModbusSequentialDataBlock(0, [0] * args.num_regs),  # Input Registers
        co=ModbusSequentialDataBlock(0, [0] * args.num_regs),  # Coils
        di=ModbusSequentialDataBlock(0, [0] * args.num_regs),  # Discrete Inputs
    )
    context = ModbusServerContext(slaves=store, single=True)

    print(f"[servidor] iniciando servidor Modbus TCP em {args.host}:{args.port}")
    asyncio.create_task(atualizar_sensores(context))
    await StartAsyncTcpServer(context=context, address=(args.host, args.port))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[servidor] encerrado")