# Método experimental — contribuição do Yan

## Implementação realizada

Foi construído um laboratório local em Python 3.11+, com três papéis lógicos: RTU virtual Modbus TCP, estação supervisória e gerador de carga. A RTU mantém temperatura nominal de 60 com variação inteira uniforme de ±3 e pressão nominal de 100 com variação de ±10, atualizadas a cada segundo. A seed é configurável e registrada; ela reproduz a sequência dos sensores, mas não os tempos de escalonamento do sistema operacional.

O laboratório utiliza mensagens binárias Modbus TCP de leitura de holding registers (FC03, endereço inicial 0, quantidade 2 e unit id 1). O servidor também aceita outras faixas válidas dentro dos seus 100 registradores e devolve respostas de exceção para funções/endereço não suportados. Trata-se de implementação didática do subconjunto de leitura, feita com a biblioteca padrão; os arquivos originais baseados em pymodbus foram preservados separadamente.

O cliente legítimo consulta os sensores em intervalos programados de um segundo. Quando a consulta atrasa, não compensa com uma rajada. As exceções de conexão, respostas inválidas e timeouts são registradas, permitindo que as consultas seguintes continuem. O timeout de cada tentativa é de 0,5 segundo. Cada consulta estabelece uma conexão TCP nova, em contraste com a conexão persistente do cliente original.

## Protocolo de execução

1. Iniciar servidor exclusivo em loopback e registrar a configuração.
2. Coletar a fase normal com apenas o cliente legítimo.
3. Manter o cliente legítimo e executar leituras adicionais por duração limitada.
4. Registrar separadamente os horários efetivos de início/fim da carga.
5. Interromper a carga e manter a coleta durante a recuperação.
6. Finalizar os registros e agregar em janelas temporais de um segundo.

A configuração padrão prevê 60 s normais, 20 s de carga com teto de 50 consultas/s e 60 s de recuperação. Recomenda-se repetir a mesma configuração em pelo menos três execuções independentes e registrar taxas efetivamente atingidas. A quantidade de repetições e a duração final devem constar do artigo conforme os ensaios realmente realizados.

## Aquisição e características

O servidor registra o horário de recepção de cada solicitação completa para a qual conseguiu emitir resposta e os bytes Modbus de aplicação em ambas as direções. O cliente legítimo registra a latência fim a fim, sucesso, timeout e valores de processo. O gerador registra suas próprias tentativas em arquivo separado.

Em cada janela calcula-se: requisições atendidas por segundo; bytes de aplicação recebidos; bytes de aplicação enviados; média das latências do cliente legítimo; proporção de timeouts; e proporção total de falhas, incluindo timeouts. A atribuição das consultas às janelas usa o instante de início da tentativa no cliente e o instante de recepção no servidor. Os dois instantes podem pertencer a janelas diferentes nas fronteiras.

Os bytes não representam captura de pacotes nem utilização total de rede. Como todas as leituras têm tamanho fixo, taxa e volumes de bytes são correlacionados; discutir essa redundância na análise. Os valores dos sensores são contexto e não são alterados pela carga.

## Avaliação sem vazamento de rótulos

A tabela `features.csv` não contém o campo de ataque. `avaliacao.csv` contém o identificador da janela, fase e rótulo obtido da sobreposição com o intervalo de carga. A padronização e a clusterização recebem apenas as seis características documentadas. Os rótulos são associados posteriormente para cálculo das métricas. Os dados sintéticos e os exemplos curtos de validação não substituem os ensaios finais do grupo.

Uma detecção de aumento de taxa pode ocorrer sem falhas de disponibilidade. O trabalho deve distinguir detecção da fase de carga de detecção de um DoS que efetivamente degradou o serviço. Não presumir que clusters minoritários representam ataques em qualquer duração de ensaio.

## Ajustes necessários no artigo recebido

- Substituir a afirmação de que todo o caminho experimental utiliza pymodbus pela descrição desta implementação didática, OU manter essa versão como experimento alternativo e documentá-la explicitamente.
- Informar que os três papéis executam localmente no mesmo processo asyncio, sem VMs nesta entrega.
- Definir bytes como bytes ADU Modbus, sem cabeçalhos de rede.
- Esclarecer o uso de uma conexão nova por consulta e não comparar diretamente a latência com os 0,893 ms da linha de base original.
- Relatar somente as durações, contagens e efeitos realmente medidos; não declarar sucesso de DoS sem degradação observada.
- Painel, K-Means e DENCLUE continuam sendo a etapa do Bryan; não estão implementados neste pacote.

## O que explicar na apresentação

O servidor simula sensores; o cliente faz leituras normais; a carga adiciona leituras controladas. A coleta no servidor permite observar o tráfego adicional. Os logs são agrupados por segundo para transformar eventos em uma tabela numérica. Os horários da carga ficam separados para conferir as detecções depois, sem entregar a resposta ao algoritmo.
