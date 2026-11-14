# Método experimental

## Implementação realizada

Foi construído um laboratório local em Python 3.11+, com três papéis lógicos: RTU virtual Modbus TCP, estação supervisória e gerador de carga. A RTU mantém temperatura nominal de 60 com variação inteira uniforme de ±3 e pressão nominal de 100 com variação de ±10, atualizadas a cada segundo. A seed é configurável e registrada; ela reproduz a sequência dos sensores, mas não os tempos de escalonamento do sistema operacional.

O laboratório utiliza mensagens binárias Modbus TCP de leitura de holding registers (FC03, endereço inicial 0, quantidade 2 e unit id 1). O servidor também aceita outras faixas válidas dentro dos seus 100 registradores e devolve respostas de exceção para funções/endereço não suportados. Trata-se de implementação didática do subconjunto de leitura, feita com a biblioteca padrão; os arquivos originais baseados em pymodbus foram preservados separadamente.

No perfil padrão, o cliente legítimo consulta os sensores em intervalos programados de um segundo. Quando a consulta atrasa, não compensa com uma rajada. As exceções de conexão, respostas inválidas e timeouts são registradas, permitindo que as consultas seguintes continuem. O bloco de comunicação tem timeout de 0,5 segundo; o fechamento ocorre fora dele. Cada consulta estabelece uma conexão TCP nova, em contraste com a conexão persistente do cliente original.

No perfil variável, o intervalo base recebe um fator uniforme entre `1-jitter` e `1+jitter`, com piso de 0,1 s. A manutenção usa outro intervalo base e também recebe jitter, inclusive com perfil fixo. Sua condição é avaliada após cada tentativa e usa início inclusivo e fim exclusivo. `atividades_legitimas.csv` registra os horários planejados, não confirma o instante de uma primeira consulta de manutenção. O gerador do cliente usa `seed + 10_000`, separado do gerador dos sensores; repetir a seed não fixa os tempos de execução.

A carga pode ser fixa ou dividida em três segmentos de mesma duração planejada, com taxas baixa, média e alta. Os limites de 200 consultas/s e 120 s se aplicam à taxa máxima e à duração total da carga. `ataques.csv` registra os horários medidos de cada segmento, após seu término.

## Organização e responsabilidades

`RTU` mantém os sensores e atende TCP local; `request` realiza uma leitura; `polling` agenda tentativas legítimas ou de carga; `run` coordena fases e encerramento; `aggregate` transforma logs em janelas. `main` interpreta e valida a CLI. A comunicação dos clientes com o servidor continua passando por sockets, apesar de todos compartilharem o mesmo processo e event loop.

Essa escolha reduz preparação do ambiente e permite encerrar os papéis em uma execução. Também compartilha CPU, disco e escalonamento: lentidão no processo pode afetar simultaneamente quem gera, atende e mede. Os resultados não isolam gargalos de uma rede industrial. `laboratorio.py` permanece único porque essas responsabilidades ainda cabem em uma leitura sequencial. `Configuracao` explicita os parâmetros e `Janela` reúne os acumuladores.

O contrato completo dos CSVs e do JSON está no README. A validação dos parâmetros ocorre em main, antes do início do ensaio.

## Protocolo de execução

1. Iniciar servidor exclusivo em loopback e registrar a configuração.
2. Coletar a fase normal com apenas o cliente legítimo.
3. Manter o cliente legítimo e executar leituras adicionais por duração limitada.
4. Registrar separadamente os horários efetivos de início/fim da carga.
5. Interromper a carga e manter a coleta durante a recuperação.
6. Finalizar os registros e agregar em janelas temporais de um segundo.

A configuração padrão prevê 60 s normais, 20 s de carga com teto de 50 consultas/s e 60 s de recuperação. Recomenda-se repetir a mesma configuração em pelo menos três execuções independentes e registrar taxas efetivamente atingidas. O lote final contém 12 ensaios de 180 s, com 60 s por fase, seeds 101–112, jitter de 30%, manutenção entre 20 e 35 s e carga em segmentos de 20 s a 2, 5 e 10 consultas/s. O intervalo legítimo passa de 1 s para 0,2 s durante a manutenção.

## Aquisição e características

O servidor captura o horário após ler o cabeçalho Modbus e grava o registro após enviar a resposta. Registra bytes Modbus de aplicação em ambas as direções. O cliente legítimo registra a latência fim a fim, sucesso, timeout e valores de processo. O gerador registra suas próprias tentativas em arquivo separado.

Em cada janela calcula-se: requisições atendidas por segundo; bytes de aplicação recebidos; bytes de aplicação enviados; média das latências do cliente legítimo; proporção de timeouts; e proporção total de falhas, incluindo timeouts. A atribuição das consultas às janelas usa o instante de início da tentativa no cliente e o instante de recepção no servidor. Os dois instantes podem pertencer a janelas diferentes nas fronteiras.

Os bytes não representam captura de pacotes nem utilização total de rede. Como todas as leituras têm tamanho fixo, taxa e volumes de bytes são correlacionados, o que motiva a seleção de entradas descrita em ALGORITMOS_IA.MD. Os valores dos sensores são contexto e não são alterados pela carga.

## Avaliação sem vazamento de rótulos

A tabela `features.csv` não contém rótulos, fase, seed ou horários da carga. `avaliacao.csv` contém o identificador da janela, fase e rótulo obtido da sobreposição com o intervalo de carga. O laboratório exporta as seis características documentadas na ordem contratada. Os notebooks selecionam posteriormente taxa, latência e indicador de disponibilidade; mediana e escalas do cenário variável são ajustadas somente no treino. Os rótulos não entram nessas entradas numéricas, mas são usados na validação para mapear clusters para classes e depois calcular métricas no teste. Essa atribuição de classes usa supervisão, embora o ajuste dos clusters não use rótulos. Os exemplos curtos de validação não substituem os ensaios finais do grupo.

Uma detecção de aumento de taxa pode ocorrer sem falhas de disponibilidade. O rótulo identifica a presença da carga experimental e não comprova DoS. Clusters minoritários não correspondem necessariamente a esse rótulo.

## Limitações do experimento

- `run` grava `status: completo` antes de agregar; uma interrupção pode deixar a pasta sem JSON e uma falha posterior pode deixar derivados incompletos. O status isolado não certifica conclusão.
- `aggregate` usa `int(ts - inicio)` para localizar eventos. Um evento ligeiramente anterior ao início pode cair na primeira janela; na última janela parcial, um evento posterior ao fim pode ser incluído. A função não valida logs arbitrários fora do intervalo.
- O fim analisado é planejado, enquanto as fases usam esperas e tentativas reais. Uma consulta iniciada perto do prazo pode terminar depois dele.
- O lote ignora pastas existentes sem conferir o status. O painel conta registros entre atualizações, que não equivalem necessariamente a um segundo exato.
- Nos notebooks 10/12, o treino não exclui pontos sem convergência. A previsão do notebook 10 os classifica como ruído.
