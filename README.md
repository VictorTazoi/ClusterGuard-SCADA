# ClusterGuard SCADA

Laboratório local de tráfego Modbus TCP e análise de anomalias com K-Means e DENCLUE.

## Começar no Windows

O laboratório requer **Python 3.11 ou superior** e usa somente a biblioteca padrão. Os notebooks de análise utilizam NumPy, pandas, matplotlib, scikit-learn e Jupyter. Os arquivos históricos em `originais/` utilizam pymodbus. Essas dependências não são necessárias para coletar ou reagregar ensaios com `laboratorio.py`.

1. Abra a pasta do repositório.
2. Abra o PowerShell na pasta que contém `laboratorio.py`.
3. Confira a versão e execute:

```powershell
python --version
python laboratorio.py
```

O programa inicia seu próprio servidor em `127.0.0.1:5020`, cliente legítimo e módulo de carga. Não execute os servidores originais ao mesmo tempo nessa porta. Para usar uma porta local disponível automaticamente:

```powershell
python laboratorio.py --port 0
```

A execução padrão dura aproximadamente 140 segundos: 60 segundos normais, 20 segundos de carga a no máximo 50 consultas/s e 60 segundos de recuperação. O cliente legítimo mantém uma consulta/s quando as respostas permitem. O diretório de resultados aparece no terminal. Não reutilize uma pasta de saída existente; o programa recusa sobrescrever ensaios.

## Estrutura do repositório

- `laboratorio.py`: servidor Modbus TCP didático, cliente com tratamento de erros, carga controlada, cronograma e agregação.
- `test_laboratorio.py`: testes de comunicação, timeout, validação, preservação de arquivos e experimento completo.
- `METODOLOGIA.md`: protocolo experimental, características e limites do método.
- `exemplos_validados/`: três ensaios curtos de integração, executados em Linux; distintos do lote experimental final.
- `VALIDACAO.md`: resultados observados e limitações.
- `originais/`: versão inicial do cliente e do servidor, baseada em pymodbus.
- `executar_experimentos.py`: lote com as seeds 101–112, manutenção e carga em degraus.
- `visualizar.py`: acompanhamento no terminal; suas contagens entre atualizações não substituem as janelas de `features.csv`.
- `notebooks/`, `datasets/` e `ALGORITMOS_IA.MD`: preparação dos dados e análise com K-Means e DENCLUE.

## Escopo e requisitos

O experimento permite repetir configurações e comparar taxas de carga a partir dos registros brutos. A seed controla as sequências pseudoaleatórias dos sensores e dos intervalos variáveis, mas não reproduz exatamente o escalonamento, as latências ou os CSVs de uma nova execução.

O laboratório gera logs, características sem rótulos e avaliação temporal separada. A coleta mantém comunicação local, limites de carga e recusa de sobrescrita de ensaios. O treinamento dos detectores ocorre nos notebooks. O escopo se limita a sensores sintéticos e tráfego local; não inclui operação de uma planta SCADA ou validação com equipamento físico.

## Repetir experimentos

Exemplo de três repetições de uma MESMA configuração (cerca de sete minutos):

```powershell
python laboratorio.py --normal 60 --carga 20 --recuperacao 60 --taxa 50 --seed 43 --saida resultados/repeticao_1
python laboratorio.py --normal 60 --carga 20 --recuperacao 60 --taxa 50 --seed 44 --saida resultados/repeticao_2
python laboratorio.py --normal 60 --carga 20 --recuperacao 60 --taxa 50 --seed 45 --saida resultados/repeticao_3
```

Após isso, outras taxas podem ser comparadas mantendo os demais parâmetros. O limite implementado é de 200 consultas/s e 120 segundos por fase de carga; não existe alvo remoto configurável. A taxa efetiva é medida nos logs, não presumida a partir do parâmetro. O gerador é sequencial, sem fila ilimitada e sem compensação por rajadas quando atrasa.

Interromper com Ctrl+C deixa uma pasta parcial, que não deve entrar na análise. Uma pasta completa tem `ensaio.json` com `status: completo`, `features.csv` e `avaliacao.csv`.

**Limitação atual:** `run` grava o JSON somente ao final da coleta, antes da agregação. Uma interrupção anterior pode deixar a pasta sem JSON; uma falha na agregação pode deixar `status: completo` sem os derivados completos. Portanto, esse status isolado não certifica a conclusão. Confira também o encerramento sem erro e os dois CSVs derivados. Não existe hoje um status explícito para ensaio incompleto.

### Perfis disponíveis

`--perfil-cliente variavel` aplica variação uniforme de ±`--jitter` ao intervalo base. O perfil padrão é `fixo`. Durante manutenção, o intervalo base passa a `--intervalo-manutencao`, e o jitter se aplica mesmo se o perfil for fixo. O período inclui o início e exclui o fim, avaliados após cada tentativa.

`--perfil-carga degraus` divide a duração total de carga igualmente entre taxas baixa, média e alta. Exemplo curto, em uma pasta nova:

```powershell
python laboratorio.py --port 0 --normal 1 --carga 1 --recuperacao 1 --perfil-cliente variavel --manutencao-inicio 0.2 --manutencao-duracao 0.4 --perfil-carga degraus --taxa-baixa 2 --taxa-media 5 --taxa 10 --seed 43 --saida resultados/verificacao_perfis
```

| Parâmetros | Restrição da CLI |
|---|---|
| `normal`, `recuperacao` | Positivos, finitos, até 600 s cada |
| `carga` | Positiva, finita, até 120 s no total, inclusive em degraus |
| `taxa` | Positiva, finita, até 200 consultas/s |
| `taxa-baixa`, `taxa-media` | Positivas e finitas; em degraus: baixa ≤ média ≤ taxa |
| `intervalo`, `intervalo-manutencao` | Finitos, no mínimo 0,1 s |
| `jitter` | Finito, entre 0 e 0,5 |
| `manutencao-inicio`, `manutencao-duracao` | Finitos, não negativos; início + duração ≤ fase normal |
| `port` | Inteiro entre 0 e 65535; 0 escolhe uma porta local disponível |
| `seed` | Inteiro |

Os limites de duração se referem à configuração; uma tentativa iniciada antes do prazo pode terminar depois dele. O timeout de comunicação é 0,5 s; o fechamento da conexão ocorre fora desse bloco de timeout.

O lote `python executar_experimentos.py` usa 60 s por fase e seeds 101–112. Ele ignora qualquer pasta já existente, mesmo incompleta, e executa também se for importado. Execute-o diretamente apenas quando quiser esse lote; uma pasta ignorada não comprova conclusão.

## Arquivos produzidos em cada ensaio

| Arquivo | Conteúdo |
|---|---|
| `servidor.csv` | Uma linha por resposta concluída: horário de recepção e bytes de aplicação Modbus recebidos/enviados, incluindo cliente e carga. |
| `cliente.csv` | Tentativas legítimas, sucesso/falha, timeout, latência, sensores e bytes. |
| `carga.csv` | Tentativas do módulo de carga e seus resultados. |
| `ataques.csv` | Início/fim efetivos da fase de carga e taxa alvo. |
| `atividades_legitimas.csv` | Início/fim planejados da manutenção; fica só com o cabeçalho se ela estiver desativada. |
| `ensaio.json` | Configuração, seed, porta efetiva, intervalo analisado e ambiente. |
| `features.csv` | Características em janelas de um segundo, SEM rótulos de ataque. |
| `avaliacao.csv` | Rótulos temporais e fases, separados para avaliação posterior. |

Os horários são Unix epoch em segundos. A última janela pode ser parcial se a duração escolhida não for inteira. Os bytes estão na perspectiva do servidor e excluem cabeçalhos Ethernet/IP/TCP, handshakes e retransmissões. Requisições de leitura usam 12 bytes Modbus ADU; respostas bem-sucedidas de dois registradores usam 13 bytes.

### Contrato de dados

Os CSVs são UTF-8, separados por vírgula, com cabeçalho e ponto decimal. As colunas são:

| Arquivo | Colunas, na ordem gravada |
|---|---|
| `servidor.csv` | `ts,bytes_rx,bytes_tx` |
| `cliente.csv`, `carga.csv` | `ts,origem,sucesso,timeout,latencia_ms,bytes_tx,bytes_rx,temp,pres,detalhe` |
| `ataques.csv` | `inicio,fim,tipo,taxa_alvo_rps` |
| `atividades_legitimas.csv` | `inicio,fim,tipo` |
| `features.csv` | `janela,ts_inicio,duracao_s,taxa_requisicoes,bytes_rx,bytes_tx,latencia_ms,taxa_timeout,taxa_erro,consultas_cliente,latencia_disponivel` |
| `avaliacao.csv` | `janela,label,fase` |

`sucesso`, `timeout`, `label` e `latencia_disponivel` usam 0/1. Nos logs de tentativas, bytes recebidos/enviados são vistos pelo cliente; em `servidor.csv` e `features.csv`, pelo servidor. `temp` e `pres` são valores sintéticos dos registradores, vazios quando não obtidos. `detalhe` registra a falha; conexão não estabelecida conta como erro, mas o campo `timeout` só recebe 1 após estabelecer a conexão.

`ensaio.json` contém `inicio`, `fim`, `config`, `porta_efetiva`, `bytes`, `ambiente` e `status`. `config` guarda os argumentos, com nomes de opções convertidos para sublinhado; a seed permanece ali. `fim` é o início mais a duração planejada das três fases, não uma medição do instante de encerramento. O JSON não registra a versão do Python nem a versão do sistema operacional.

`taxa_requisicoes` conta as requisições atendidas no servidor por segundo, de TODAS as origens. O registro é emitido após envio da resposta; consultas incompletas não entram nessa contagem. Os logs de tentativas do cliente/carga são preservados para investigar diferenças. As medições de latência são fim a fim, incluindo abertura de conexão TCP e fechamento, pois cada consulta abre uma conexão. Os clientes originais usavam conexão persistente: os números não são diretamente comparáveis.

## Entradas para a análise

A análise utiliza a pasta completa de cada ensaio. As seis colunas exportadas como características são, nesta ordem:

```python
colunas = [
    'taxa_requisicoes', 'bytes_rx', 'bytes_tx',
    'latencia_ms', 'taxa_timeout', 'taxa_erro'
]
```

`taxa_timeout` e `taxa_erro` são frações entre 0 e 1 de tentativas legítimas; erro inclui timeout. `latencia_ms` é a média das tentativas legítimas iniciadas na janela, incluindo as falhas. Janela sem consulta legítima recebe campos vazios nessas três medições: filtrar explicitamente ou imputar com uma regra documentada; não interpretar como zero. `consultas_cliente` e `latencia_disponivel` ajudam nessa decisão.

Não usar `janela`, `ts_inicio`, `duracao_s` ou colunas de controle como características do modelo. NÃO passar `avaliacao.csv`, fase, seed ou horários dos ataques ao treinamento/padronização. Depois de prever, unir os resultados por `janela` para avaliação.

Essa é a interface de seis entradas do laboratório. Os notebooks existentes adotam uma seleção posterior de três colunas: `taxa_requisicoes`, `latencia_ms` e `latencia_disponivel`. O indicador de disponibilidade é uma decisão específica dessa análise, descrita em `ALGORITMOS_IA.MD`; não altera o contrato de exportação. O consolidado `datasets/dataset_experimental.csv` contém rótulos e metadados, portanto não deve ser passado inteiro ao modelo. Nos notebooks 09/10, os rótulos da validação são usados para atribuir a classe ataque/legítimo aos clusters depois do ajuste.

O rótulo é 1 quando há qualquer sobreposição da janela com o período de carga; janelas de fronteira podem conter mistura. Fazer uma análise adicional sem essas janelas é útil. A fase recuperação não garante que eventuais efeitos residuais cessaram; seu rótulo indica ausência de carga planejada, não certeza de normalidade.

## Testar e reagregar

```powershell
python -m unittest -v test_laboratorio.py
python laboratorio.py --agregar resultados/repeticao_1
```

A reagregação substitui somente `features.csv` e `avaliacao.csv`. Não modifica os registros brutos.

## Limite da conclusão

Este experimento mede anomalias de tráfego sob carga de aplicação controlada. Não provoca deliberadamente falhas nem adiciona latência artificial. O aumento de taxa NÃO prova indisponibilidade: só descrever como DoS efetivo se os registros demonstrarem degradação. Se todos os clientes continuarem respondendo, relatar aumento de carga, sem alegar negação de serviço.

O servidor suporta apenas o subconjunto necessário de Modbus TCP (leitura FC03, 100 registradores), não uma RTU industrial completa. Todos os papéis rodam no mesmo processo/event loop e no mesmo computador, o que limita a independência das medições e a generalização para redes industriais. Os testes validam este caminho autocontido; não comprovam compatibilidade com todas as versões do pymodbus ou com equipamentos físicos.
