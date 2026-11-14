# Validação

## Testes automatizados

```powershell
python -m unittest -v test_laboratorio.py
```

Execução registrada em 14/11/2026: Windows, Python 3.14.6, 16 testes em 14,218 s, resultado `OK`.

| Cobertura | Verificação |
|---|---|
| Comunicação | Conexão recusada e timeout registrados separadamente |
| Ensaio completo | Comunicação local, sensores, bytes e proteção contra sobrescrita |
| Reagregação | Preservação dos brutos e reprodução dos CSVs derivados |
| Contrato de dados | Cabeçalhos, ordem das seis características e separação dos rótulos |
| Ausência de consultas | Campos vazios nas medições indisponíveis |
| Janelas | Duração parcial, média com falhas e fronteiras dos eventos |
| Perfis | Intervalo fixo, seed, jitter e manutenção |
| CLI | Rejeição de valores inválidos e aceitação dos limites exatos |
| Carga em degraus | Ordem, taxas e registro separado da manutenção |

A execução padrão também foi verificada em pasta temporária: término sem erro e 140 janelas. A sintaxe dos três scripts é compatível com a gramática do Python 3.11; a execução acima foi feita com 3.14.6.

## Integridade dos dados

A reagregação em cópias dos 20 ensaios existentes reproduziu `features.csv` e `avaliacao.csv` byte a byte, totalizando 2.960 janelas. Os brutos das cópias permaneceram inalterados. Nesse conjunto, 180 janelas não contêm consulta legítima e mantêm as medições correspondentes vazias.

O lote final reúne 12 ensaios e 2.160 janelas, divididas em 1.080 de treino, 540 de validação e 540 de teste. As linhas do consolidado conferem com as tabelas de origem. Nesse lote, 155 janelas não possuem medição de latência do cliente legítimo. Os logs contêm 2.856 consultas legítimas e 4.080 de carga, todas com sucesso registrado.

Os totais de 180 e 155 janelas sem consulta se referem a conjuntos diferentes: todos os 20 ensaios e os 12 ensaios do lote final, respectivamente.

## Análise em notebooks

As métricas de K-Means e DENCLUE provêm das saídas salvas nos notebooks 09–12. O ajuste dos modelos não foi reexecutado na conferência documental. As matrizes de confusão sustentam os valores apresentados em `ALGORITMOS_IA.MD`.

O painel de terminal foi verificado com fases de 1 s em pasta temporária. O lote teve comandos e mensagens conferidos com substitutos para subprocessos e existência de pastas; essa verificação não iniciou outro lote experimental.

## Ensaios de integração — 14/10/2026

O registro histórico informa Python 3.12.14 em Linux e quatro testes aprovados. Foram executados três ensaios de 20 s: 8 s normais, 4 s de carga e 8 s de recuperação.

| Ensaio | Taxa alvo | Consultas de carga | Taxa efetiva | Consultas legítimas | Falhas legítimas |
|---|---:|---:|---:|---:|---:|
| ensaio_1_20rps | 20/s | 80 | 20,00/s | 20 | 0 |
| ensaio_2_50rps | 50/s | 200 | 50,00/s | 20 | 0 |
| ensaio_3_100rps | 100/s | 400 | 99,99/s | 20 | 0 |

A taxa efetiva divide as tentativas concluídas pela duração medida da fase. Esses ensaios usam taxas diferentes e verificam integração; não constituem repetições de uma configuração única. O teste de timeout utiliza um servidor de teste que não responde, separado dos dados experimentais.

## Limites

Os testes verificam o caminho local implementado. Não certificam conformidade Modbus completa, equipamentos físicos, todas as versões do Python ou uma instalação limpa do sistema. A ausência de falhas não demonstra comportamento sob saturação nem eficácia em rede industrial.

Permanecem as limitações de status do JSON, indexação temporal, contagem do painel, pastas ignoradas pelo lote e convergência do DENCLUE descritas em `METODOLOGIA.md`.
