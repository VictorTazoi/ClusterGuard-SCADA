# Análise com K-Means e DENCLUE

## Dados e cenários

Os notebooks analisam tráfego do laboratório Modbus TCP local, usando NumPy, pandas, matplotlib, scikit-learn e Jupyter. As métricas correspondem às saídas salvas, sem novo treinamento durante a conferência documental.

| Cenário | Dados | Avaliação |
|---|---|---|
| Simples | Um ensaio, 140 janelas: 119 legítimas e 21 de carga | Ajuste, atribuição de classe e avaliação no mesmo ensaio |
| Variável | 12 ensaios, 2.160 janelas, manutenção e carga em degraus | Separação por ensaio em treino, validação e teste |

O cenário simples usa aproximadamente 1 consulta legítima/s e carga alvo de 50 consultas/s durante 20 s. O variável usa jitter de 30%, manutenção com intervalo base de 0,2 s e carga alvo de 2, 5 e 10 consultas/s. Cada ensaio variável dura 180 s: 60 s normais, 60 s de carga e 60 s de recuperação. A carga se soma às consultas legítimas.

O nome “realista” em algumas saídas antigas designa o cenário variável. Ambos os cenários são locais e didáticos.

## Preparação

Os notebooks 06 e 07 consolidam e auditam os dados. A chave é o par `ensaio, janela`. Cada ensaio pertence a um único conjunto.

| Conjunto | Seeds | Janelas | Legítimas | Carga |
|---|---|---:|---:|---:|
| Treino | 101–106 | 1.080 | 714 | 366 |
| Validação | 107–109 | 540 | 357 | 183 |
| Teste | 110–112 | 540 | 357 | 183 |

O laboratório exporta seis características na ordem documentada no README. A seleção posterior dos modelos é:

```python
COLUNAS_ML = [
    "taxa_requisicoes",
    "latencia_ms",
    "latencia_disponivel",
]
```

Os bytes são redundantes com a taxa neste protocolo de mensagens fixas. As frações de erro e timeout não variam no lote. `consultas_cliente` fica fora do modelo por identificar a origem legítima. O indicador `latencia_disponivel` também depende da instrumentação do cliente e limita a transferência direta do modelo para captura passiva de tráfego.

Há 155 janelas sem latência no lote variável. A mediana do treino, 2,4758 ms, preenche esses valores. `StandardScaler` é ajustado no treino para taxa e latência; o indicador de disponibilidade continua binário. Validação e teste recebem as mesmas transformações. O notebook 08 compara `StandardScaler` e `RobustScaler`.

Rótulos e metadados permanecem no consolidado para avaliação, mas não entram em `COLUNAS_ML`. Nos notebooks 09 e 10, a maioria dos rótulos da validação define a classe associada a cada cluster. O ajuste é não supervisionado; essa atribuição de classes usa supervisão.

## K-Means

O notebook 09 adota `k=5`, `random_state=42` e `n_init=20`. A escolha é exploratória, apoiada no cotovelo e na interpretação dos grupos. A maior Silhouette entre os valores comparados com `StandardScaler` ocorre em `k=7` (0,4836), enquanto `k=5` obtém 0,4101. Portanto, cinco grupos não maximizam essa métrica.

Os centróides são ajustados no treino. A previsão associa as demais observações ao centróide mais próximo. O mapa cluster→classe da validação é aplicado ao teste.

## DENCLUE didático

O notebook 10 estima densidade Gaussiana, desloca cada observação para um atrator e une atratores próximos. O deslocamento usa tolerância de `1e-4`, até 100 iterações; a fusão usa distância de 0,05 no espaço preparado.

A configuração principal usa `sigma=0.42` e `xi=0.018497080747067`. O limiar é o ponto médio entre as duas menores densidades dos atratores representativos do treino. Mantém dois clusters e classifica quatro observações do treino como ruído. A Silhouette dos pontos mantidos é 0,505234.

A busca por sigma incluiu 0,15 a 1,00 e refinamento entre 0,38 e 0,55. A seleção considera estrutura dos grupos e convergência, além da Silhouette. A previsão usa o treino como referência de densidade e associa o atrator ao representante sobrevivente mais próximo. Não convergência ou densidade inferior a xi resultam em ruído.

A classe do ruído também é atribuída pela validação. A implementação é inspirada em DENCLUE, com regras próprias de fusão e previsão, sem equivalência integral à implementação de referência.

## Resultados no teste variável

Fonte: notebook 09, células 35–38, e notebook 10, células 46–49 (índices a partir de zero). O teste tem 540 janelas, das quais 183 são de carga.

| Métrica | K-Means | DENCLUE didático |
|---|---:|---:|
| Acurácia | 0,7796 | 0,7722 |
| Precisão | 0,7254 | 1,0000 |
| Recall | 0,5628 | 0,3279 |
| F1 | 0,6338 | 0,4938 |
| Taxa de falsos positivos | 0,1092 | 0,0000 |

| Contagem | K-Means | DENCLUE didático |
|---|---:|---:|
| Verdadeiros negativos | 318 | 357 |
| Falsos positivos | 39 | 0 |
| Falsos negativos | 80 | 123 |
| Verdadeiros positivos | 103 | 60 |

| Nível de carga | Janelas no teste | Detecções K-Means | Detecções DENCLUE |
|---|---:|---:|---:|
| Baixa | 60 | 3 (5,00%) | 0 (0,00%) |
| Média | 60 | 42 (70,00%) | 0 (0,00%) |
| Alta | 63 | 58 (92,06%) | 60 (95,24%) |

K-Means detectou mais janelas de carga, com falsos alarmes. DENCLUE não apresentou falsos positivos nesse teste, mas deixou de detectar 123 das 183 janelas de carga. Precisão de 100% nesse conjunto não garante ausência de falsos alarmes em novos ensaios.

## Cenário simples

Nos notebooks 11 e 12, ambos obtêm 119 verdadeiros negativos, nenhum falso positivo, um falso negativo e 20 verdadeiros positivos: acurácia 0,9929, precisão 1,0000, recall 0,9524 e F1 0,9756. K-Means usa `k=3`; DENCLUE usa `sigma=0.50` e `xi=0.029538869390677`.

Esses números são exploratórios: o mesmo ensaio participa do ajuste e da avaliação. Não são diretamente comparáveis à avaliação em ensaios separados do cenário variável.

## Limitações

- O lote usa loopback, sensores sintéticos e um único processo. Não representa uma planta industrial.
- Os rótulos indicam sobreposição com a carga, incluindo janelas de fronteira. Não certificam indisponibilidade ou intenção maliciosa.
- São três ensaios de teste; as janelas de um ensaio não são observações independentes. Não foram calculados intervalos de confiança por ensaio.
- O treino do DENCLUE não exclui pontos sem convergência, enquanto a previsão os trata como ruído.
- `janela_transicao` indica mudanças entre condições vizinhas, incluindo as extremidades; não mede a sobreposição temporal exata.
- A tabela comparativa final do notebook 12 contém valores digitados. As matrizes e métricas dos notebooks 09–12 são as fontes dos resultados apresentados aqui.
- Não foram avaliados ataques que alteram conteúdo sem aumento de taxa, generalização para redes físicas ou custo de detecção em operação contínua.
