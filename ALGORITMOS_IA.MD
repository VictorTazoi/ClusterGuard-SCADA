# ClusterGuard-SCADA — Experimentos com K-Means e DENCLUE - Contribuição Bryan

## 1. Objetivo deste documento

O objetivo do experimento é investigar a possibilidade de identificar comportamentos anômalos em tráfego **Modbus TCP** de um ambiente SCADA utilizando técnicas de aprendizado não supervisionado.

Foram utilizados dois cenários:

1. **Cenário simples**, desenvolvido originalmente no projeto do grupo.
2. **Cenário variável**, desenvolvido posteriormente para introduzir maior variabilidade e aumentar a dificuldade do problema.

A intenção avaliar experimentalmente até que ponto os agrupamentos encontrados correspondem aos eventos anômalos simulados.

---

# 2. Cenário experimental original

O laboratório inicial apresentava um comportamento bastante controlado.

O tráfego legítimo realizava aproximadamente:

```text
1 requisição por segundo
```

Durante o evento de carga Modbus, o tráfego aumentava para aproximadamente:

```text
50 a 52 requisições por segundo
```

O ensaio continha aproximadamente:

```text
60 s → operação normal
20 s → carga Modbus
60 s → recuperação
```

Total:

```text
140 janelas temporais
```

Foram identificadas:

```text
119 janelas legítimas
21 janelas de carga
```

Esse cenário foi mantido como **cenário simples**, pois permite avaliar o comportamento dos algoritmos quando existe grande separação entre tráfego normal e anômalo.

---

# 3. Limitações identificadas no cenário simples

Durante a análise inicial foi observado que os dados eram extremamente separados.

O comportamento típico era aproximadamente:

```text
Operação normal / recuperação
≈ 1 req/s

Carga Modbus
≈ 50–52 req/s
```

Isso significa que um algoritmo de clusterização consegue distinguir os dois comportamentos com relativa facilidade.

Por esse motivo foi desenvolvido um segundo laboratório experimental com maior variabilidade.

---

# 4. Desenvolvimento do cenário variável

O laboratório foi ampliado sem alterar o objetivo original de análise de tráfego Modbus.

As principais mudanças foram:

## 4.1 Tráfego legítimo variável

O cliente deixou de gerar uma quantidade completamente fixa de consultas.

Foram introduzidas pequenas variações no comportamento normal para evitar um padrão totalmente determinístico.

---

## 4.2 Manutenção legítima

Foi introduzido um período de **manutenção autorizada**.

Durante esse período existe aumento legítimo na quantidade de requisições.

O objetivo dessa mudança foi criar um caso difícil para os algoritmos:

```text
tráfego elevado ≠ necessariamente ataque
```

Isso permite avaliar falsos positivos.

---

## 4.3 Cargas Modbus graduais

Em vez de apenas uma carga muito elevada, foram criados três níveis:

```text
Carga baixa
≈ 3 req/s

Carga média
≈ 6 req/s

Carga alta
≈ 10–12 req/s
```

Esses níveis tornam possível analisar se a capacidade de detecção varia conforme a intensidade da anomalia.

---

## 4.4 Recuperação

Após os eventos anômalos o sistema retorna ao comportamento normal.

Isso permite verificar se os algoritmos voltam a interpretar o tráfego como legítimo após o encerramento da carga.

---

## 4.5 Vários ensaios

O cenário realista foi executado diversas vezes utilizando sementes diferentes.

Foram gerados:

```text
12 ensaios
2160 janelas temporais
```

As sementes foram separadas em:

```text
Treino:
101–106

Validação:
107–109

Teste:
110–112
```

Dessa forma, os ensaios utilizados no teste não participaram do treinamento.

---

# 5. Auditoria e preparação dos dados

Antes da utilização dos algoritmos foram realizadas verificações de qualidade.

O dataset consolidado apresentou:

```text
2160 linhas
12 ensaios
0 linhas completamente duplicadas
0 duplicações de ensaio + janela
0 durações inválidas
```

As condições existentes foram:

```text
normal
manutenção
carga_baixa
carga_media
carga_alta
recuperacao
```

Também foram identificadas janelas de transição entre as fases experimentais.

Essas janelas foram mantidas, pois representam o comportamento temporal natural da mudança entre estados.

---

# 6. Características utilizadas

Após a análise exploratória foram escolhidas:

```python
COLUNAS_ML = [
    "taxa_requisicoes",
    "latencia_ms",
    "latencia_disponivel"
]
```

Algumas características foram retiradas do modelo.

## bytes_rx e bytes_tx

Apresentaram correlação praticamente perfeita com `taxa_requisicoes`.

Utilizar as três variáveis daria peso excessivo para a mesma informação.

---

## taxa_timeout e taxa_erro

Apresentaram variância zero no dataset analisado.

Portanto, não contribuíam para as distâncias entre observações.

---

## consultas_cliente

Não foi utilizada por representar informação privilegiada sobre a origem legítima do tráfego.

---

# 7. Tratamento de valores ausentes

Foram identificados valores ausentes de latência em janelas onde nenhuma consulta legítima estava disponível.

Esses valores não representavam erro de coleta.

A estratégia utilizada foi:

```text
latencia_ms ausente
→ mediana da latência calculada apenas no treino
```

A mediana encontrada foi aproximadamente:

```text
2,4758 ms
```

A coluna:

```text
latencia_disponivel
```

foi mantida para indicar se aquela latência havia sido realmente observada.

Isso evita que o valor imputado seja interpretado como uma medição real.

---

# 8. Normalização

Foram comparados:

```text
StandardScaler
RobustScaler
```

Os resultados apresentaram comportamento muito semelhante.

O **StandardScaler** foi escolhido para o experimento principal.

A principal justificativa é que valores elevados de taxa de requisições não eram erros ou outliers acidentais, mas faziam parte dos próprios eventos experimentais.

---

# 9. K-Means — cenário realista

O número de clusters foi investigado utilizando:

- método do cotovelo;
- Silhouette Score.

O método do cotovelo indicou:

```text
K = 5
```

O melhor Silhouette apareceu posteriormente em K=7, porém K=5 foi mantido como configuração principal por ter sido escolhido previamente pelo método do cotovelo.


---

# 10. Estrutura encontrada pelo K-Means

Um dos clusters apresentou centróide próximo de:

```text
11 requisições/s
```

Esse cluster foi composto exclusivamente por carga alta no conjunto de treinamento.

Outro cluster apresentou aproximadamente:

```text
5,4 requisições/s
```

e continha principalmente:

```text
carga média
+
manutenção legítima
```

Isso mostrou uma das principais dificuldades do experimento:

```text
manutenção legítima
≈
carga anômala intermediária
```

---

# 11. K-Means — resultados no cenário realista

Resultados no conjunto de teste:

| Métrica | Resultado |
|---|---:|
| Acurácia | 77,96% |
| Precisão | 72,54% |
| Recall | 56,28% |
| F1-score | 63,38% |
| Especificidade | 89,08% |
| Taxa de falso alarme | 10,92% |
| Ataques perdidos | 43,72% |

## Recall por intensidade

| Intensidade | Recall |
|---|---:|
| Carga alta | 92,06% |
| Carga média | 70,00% |
| Carga baixa | 5,00% |

O resultado mostra que o K-Means apresentou boa capacidade de identificar eventos intensos e parte das cargas intermediárias, mas praticamente não conseguiu diferenciar cargas baixas do tráfego legítimo.

---

# 12. Falsos positivos do K-Means

Um resultado importante foi observado durante manutenção legítima.

| Condição | Taxa de falso positivo |
|---|---:|
| Normal | 0% |
| Recuperação | 0% |
| Manutenção | 86,67% |

Todos os falsos positivos observados no teste ocorreram durante manutenção.

Isso mostra que o K-Means utiliza bem o aumento de tráfego para identificar comportamentos diferentes, porém possui dificuldade para distinguir:

```text
aumento legítimo
de
aumento provocado por carga anômala
```

---

# 13. DENCLUE — cenário realista

O DENCLUE foi implementado utilizando:

- kernel Gaussiano;
- subida em direção aos atratores de densidade;
- agrupamento de atratores próximos;
- parâmetro `sigma`;
- limiar de densidade `xi`.

Foi realizada uma análise de sensibilidade para `sigma`.

Os testes mostraram:

```text
sigma pequeno
→ muitos clusters

sigma intermediário
→ estruturas estáveis

sigma grande
→ fusão dos clusters
```

Foi escolhida uma região estável:

```text
sigma = 0,42
```

---

# 14. Escolha de xi no cenário realista

Antes do limiar foram encontrados três atratores:

| Cluster | Pontos | Densidade |
|---|---:|---:|
| 0 | 960 | 0,191199 |
| 1 | 116 | 0,034488 |
| 2 | 4 | 0,002507 |

O terceiro atrator representava apenas:

```text
4 pontos
0,37% do treino
```

Foi escolhido um limiar entre a densidade do menor e do segundo menor atrator:

```text
xi ≈ 0,018497
```

Assim:

```text
cluster de 4 pontos
→ ruído (-1)
```

enquanto os dois principais agrupamentos foram preservados.

---

# 15. DENCLUE — estrutura encontrada

No cenário realista o DENCLUE separou essencialmente:

```text
Cluster 0
→ operação normal
→ recuperação
→ manutenção
→ carga baixa
→ carga média

Cluster 1
→ principalmente carga alta

Ruído
→ alguns eventos extremos de carga alta
```

Isso mostra que carga baixa e carga média permaneceram dentro da principal região de densidade do tráfego.

---

# 16. DENCLUE — resultados no cenário realista

| Métrica | Resultado |
|---|---:|
| Acurácia | 77,22% |
| Precisão | 100% |
| Recall | 32,79% |
| F1-score | 49,38% |
| Especificidade | 100% |
| Taxa de falso alarme | 0% |
| Ataques perdidos | 67,21% |

## Recall por intensidade

| Intensidade | Recall |
|---|---:|
| Carga alta | 95,24% |
| Carga média | 0% |
| Carga baixa | 0% |

O DENCLUE apresentou comportamento mais conservador.

Quando indicou uma anomalia, ela realmente correspondia a um evento anômalo, resultando em:

```text
Precisão = 100%
Falso alarme = 0%
```

Entretanto, cargas de baixa e média intensidade não formaram regiões suficientemente distintas para serem detectadas.

---

# 17. Cenário simples — K-Means

No cenário simples foram utilizadas as 140 janelas do experimento original.

O método do cotovelo e o Silhouette indicaram:

```text
K = 3
Silhouette = 0,8266
```

Os clusters encontrados foram:

```text
Cluster 0
119 pontos
→ comportamento legítimo

Cluster 1
20 pontos
→ carga Modbus

Cluster 2
1 ponto
→ outlier legítimo de latência
```

O terceiro cluster apareceu devido a uma única observação normal com latência de aproximadamente:

```text
11,188 ms
```

---

# 18. K-Means — resultados no cenário simples

| Métrica | Resultado |
|---|---:|
| Acurácia | 99,29% |
| Precisão | 100% |
| Recall | 95,24% |
| F1-score | 97,56% |
| Falsos positivos | 0 |
| Falsos negativos | 1 |

Das 21 janelas rotuladas como carga:

```text
20 foram detectadas
1 foi classificada como legítima
```

A janela não detectada apresentava comportamento semelhante ao tráfego normal durante a transição entre fases.

---

# 19. Cenário simples — DENCLUE

A análise de `sigma` apresentou uma ampla região de estabilidade:

```text
sigma entre 0,25 e 0,75
→ 3 clusters
→ Silhouette = 0,8266
```

Foi escolhido:

```text
sigma = 0,50
```

por estar no interior dessa região estável.

Antes da aplicação de `xi`, os atratores eram:

| Atrator | Pontos | Densidade |
|---|---:|---:|
| 0 | 119 | 0,328391 |
| 2 | 20 | 0,055450 |
| 1 | 1 | 0,003628 |

O atrator contendo apenas uma observação foi considerado uma estrutura de baixa densidade.

Foi definido:

```text
xi ≈ 0,029539
```

Assim:

```text
1 observação
→ ruído (-1)

119 observações
→ cluster legítimo

20 observações
→ cluster de carga
```

---

# 20. DENCLUE — resultados no cenário simples

| Métrica | Resultado |
|---|---:|
| Acurácia | 99,29% |
| Precisão | 100% |
| Recall | 95,24% |
| F1-score | 97,56% |
| Falsos positivos | 0 |
| Falsos negativos | 1 |

K-Means e DENCLUE obtiveram exatamente as mesmas métricas nesse cenário.

Entretanto, a representação interna foi diferente.

### K-Means

O outlier de latência precisou formar um cluster:

```text
Cluster com 1 observação
```

### DENCLUE

O mesmo ponto pôde ser tratado explicitamente como:

```text
ruído (-1)
```

Essa diferença evidencia uma característica importante dos dois métodos.

---

# 21. Comparação final dos cenários

| Cenário | Algoritmo | Acurácia | Precisão | Recall | F1 | Falso alarme |
|---|---|---:|---:|---:|---:|---:|
| Simples | K-Means | 99,29% | 100% | 95,24% | 97,56% | 0% |
| Simples | DENCLUE | 99,29% | 100% | 95,24% | 97,56% | 0% |
| Realista | K-Means | 77,96% | 72,54% | 56,28% | 63,38% | 10,92% |
| Realista | DENCLUE | 77,22% | 100% | 32,79% | 49,38% | 0% |

---

# 22. Principais conclusões

## Cenários simples podem superestimar o desempenho

No cenário simples existe uma grande diferença entre tráfego legítimo e carga anômala:

```text
legítimo ≈ 1 req/s
ataque ≈ 50–52 req/s
```

Isso permite que ambos os algoritmos produzam resultados próximos da perfeição.

Quando o cenário recebe maior variabilidade, os resultados diminuem significativamente.

---

## K-Means apresentou maior sensibilidade

No cenário realista o K-Means conseguiu detectar:

```text
92,06% das cargas altas
70,00% das cargas médias
5,00% das cargas baixas
```

Porém apresentou dificuldade com manutenção legítima, produzindo falsos alarmes.

Portanto, apresentou comportamento mais sensível, mas menos específico.

---

## DENCLUE apresentou comportamento mais conservador

No cenário realista o DENCLUE detectou:

```text
95,24% das cargas altas
0% das cargas médias
0% das cargas baixas
```

Entretanto:

```text
Precisão = 100%
Taxa de falso alarme = 0%
```

Assim, apresentou maior confiança quando sinalizou uma anomalia, mas menor capacidade de identificar ataques discretos.

---

## Manutenção legítima foi importante para o experimento

A introdução de manutenção legítima mostrou que:

```text
tráfego elevado
não significa automaticamente
atividade maliciosa
```

O K-Means confundiu várias janelas de manutenção com carga anômala.

O DENCLUE manteve essas janelas dentro da principal região de densidade legítima.

Essa diferença não apareceria no cenário simples.

---

# 23. Limitações

Algumas limitações devem ser consideradas:

- os experimentos utilizam tráfego Modbus simulado;
- o cenário simples contém apenas um ensaio e foi avaliado no próprio conjunto utilizado para a clusterização;
- o cenário realista possui maior rigor por utilizar ensaios independentes de treino, validação e teste;
- os ataques analisados são principalmente eventos de aumento de carga;
- ataques mais sofisticados envolvendo conteúdo sem alteração significativa no volume de tráfego não foram avaliados;
- o cenário ainda não representa toda a complexidade de uma rede SCADA industrial real;

Portanto, os resultados do cenário simples e do cenário realista não devem ser interpretados como avaliações metodologicamente idênticas.

O cenário simples possui finalidade principalmente exploratória e demonstrativa.

---

# 24. Resumo

O desenvolvimento experimental mostrou que **K-Means e DENCLUE conseguem identificar padrões anômalos em tráfego Modbus**, porém seu desempenho depende fortemente da complexidade do ambiente.

No cenário simples, ambos alcançaram resultados próximos da perfeição.

No cenário realista, as limitações ficaram mais evidentes.

O K-Means apresentou maior capacidade de detectar ataques intermediários, ao custo de falsos positivos.

O DENCLUE apresentou maior precisão e ausência de falsos alarmes, porém detectou principalmente eventos de alta intensidade.

Esses resultados reforçam a importância de avaliar técnicas de detecção de anomalias em cenários com variabilidade suficiente para representar comportamentos legítimos e anômalos semelhantes.