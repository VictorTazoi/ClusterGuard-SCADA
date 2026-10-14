# ClusterGuard SCADA — etapa experimental do Yan

## Começar no Windows

Requer **Python 3.11 ou superior**. Não precisa instalar pacotes, executar como administrador, criar VMs ou configurar Ollama.

1. Extraia este ZIP.
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

## O que foi entregue

- `laboratorio.py`: servidor Modbus TCP didático, cliente com tratamento de erros, carga controlada, cronograma e agregação.
- `test_laboratorio.py`: testes de comunicação, timeout, validação, preservação de arquivos e experimento completo.
- `METODOLOGIA.md`: descrição do método e diferenças em relação ao artigo.
- `exemplos_validados/`: três execuções reais curtas neste ambiente de desenvolvimento, para verificar integração; não são resultados do homelab do Yan.
- `VALIDACAO.md`: resultados observados e limitações.
- `originais/`: arquivos recebidos, sem alterações.

## Repetir experimentos

Exemplo de três repetições de uma MESMA configuração (cerca de sete minutos):

```powershell
python laboratorio.py --normal 60 --carga 20 --recuperacao 60 --taxa 50 --seed 43 --saida resultados/repeticao_1
python laboratorio.py --normal 60 --carga 20 --recuperacao 60 --taxa 50 --seed 44 --saida resultados/repeticao_2
python laboratorio.py --normal 60 --carga 20 --recuperacao 60 --taxa 50 --seed 45 --saida resultados/repeticao_3
```

Após isso, outras taxas podem ser comparadas mantendo os demais parâmetros. O limite implementado é de 200 consultas/s e 120 segundos por fase de carga; não existe alvo remoto configurável. A taxa efetiva é medida nos logs, não presumida a partir do parâmetro. O gerador é sequencial, sem fila ilimitada e sem compensação por rajadas quando atrasa.

Interromper com Ctrl+C deixa uma pasta parcial, que não deve entrar na análise. Uma pasta completa tem `ensaio.json` com `status: completo`, `features.csv` e `avaliacao.csv`.

## Arquivos produzidos em cada ensaio

| Arquivo | Conteúdo |
|---|---|
| `servidor.csv` | Uma linha por resposta concluída: horário de recepção e bytes de aplicação Modbus recebidos/enviados, incluindo cliente e carga. |
| `cliente.csv` | Tentativas legítimas, sucesso/falha, timeout, latência, sensores e bytes. |
| `carga.csv` | Tentativas do módulo de carga e seus resultados. |
| `ataques.csv` | Início/fim efetivos da fase de carga e taxa alvo. |
| `ensaio.json` | Configuração, seed, porta efetiva, intervalo analisado e ambiente. |
| `features.csv` | Características em janelas de um segundo, SEM rótulos de ataque. |
| `avaliacao.csv` | Rótulos temporais e fases, separados para avaliação posterior. |

Os horários são Unix epoch em segundos. A última janela pode ser parcial se a duração escolhida não for inteira. Os bytes estão na perspectiva do servidor e excluem cabeçalhos Ethernet/IP/TCP, handshakes e retransmissões. Requisições de leitura usam 12 bytes Modbus ADU; respostas bem-sucedidas de dois registradores usam 13 bytes.

`taxa_requisicoes` conta as requisições atendidas no servidor por segundo, de TODAS as origens. O registro é emitido após envio da resposta; consultas incompletas não entram nessa contagem. Os logs de tentativas do cliente/carga são preservados para investigar diferenças. As medições de latência são fim a fim, incluindo abertura de conexão TCP e fechamento, pois cada consulta abre uma conexão. Os clientes originais usavam conexão persistente: os números não são diretamente comparáveis.

## Entregar ao Bryan

Envie a pasta completa de cada ensaio, este código e a metodologia. As seis colunas de entrada são, nesta ordem:

```python
colunas = [
    'taxa_requisicoes', 'bytes_rx', 'bytes_tx',
    'latencia_ms', 'taxa_timeout', 'taxa_erro'
]
```

`taxa_timeout` e `taxa_erro` são frações entre 0 e 1 de tentativas legítimas; erro inclui timeout. `latencia_ms` é a média das tentativas legítimas iniciadas na janela, incluindo as falhas. Janela sem consulta legítima recebe campos vazios nessas três medições: filtrar explicitamente ou imputar com uma regra documentada; não interpretar como zero. `consultas_cliente` e `latencia_disponivel` ajudam nessa decisão.

Não usar `janela`, `ts_inicio`, `duracao_s` ou colunas de controle como características do modelo. NÃO passar `avaliacao.csv`, fase, seed ou horários dos ataques ao treinamento/padronização. Depois de prever, unir os resultados por `janela` para avaliação.

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
