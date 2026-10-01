import argparse
import csv
import time
from pymodbus.client import ModbusTcpClient

def ler_registradores(client: ModbusTcpClient, address: int, count: int, slave: int):
    try:
        return client.read_holding_registers(address, count=count, slave=slave)
    except TypeError:
        return client.read_holding_registers(address, count=count, device_id=slave)

def main():
    parser = argparse.ArgumentParser(description="Mestre Modbus TCP - ClusterGuard SCADA")
    parser.add_argument("--host", default="127.0.0.1", help="IP do escravo")
    parser.add_argument("--port", type=int, default=5020, help="Porta do escravo")
    parser.add_argument("--slave-id", type=int, default=1, help="ID do escravo Modbus")
    parser.add_argument("--csv", default="dados.csv", help="Arquivo CSV de saida")
    parser.add_argument("--intervalo", type=float, default=1.0, help="Intervalo entre RX (s)")
    parser.add_argument("--duracao", type=float, default=0, help="Duracao total em segundos (0 = infinito)")
    args = parser.parse_args()
    client = ModbusTcpClient(args.host, port=args.port)

    if not client.connect():
        print(f"[mestre] falha ao conectar em {args.host}:{args.port}")
        return

    print(f"[mestre] conectado em {args.host}:{args.port} - gravando em {args.csv}")
    inicio = time.time()

    with open(args.csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ts", "temp", "pres", "latencia_ms", "erro", "label"])

        try:
            while True:
                if args.duracao and (time.time() - inicio) >= args.duracao:
                    break

                t0 = time.time()
                resposta = ler_registradores(client, 0, 2, args.slave_id)
                latencia_ms = (time.time() - t0) * 1000

                if resposta.isError():
                    writer.writerow([t0, "", "", round(latencia_ms, 2), 1, 0])
                else:
                    temp, pres = resposta.registers[0], resposta.registers[1]
                    writer.writerow([t0, temp, pres, round(latencia_ms, 2), 0, 0])

                f.flush()
                time.sleep(args.intervalo)

        except KeyboardInterrupt:
            print("\n[mestre] encerrado pelo usuario")

    client.close()

if __name__ == "__main__":
    main()