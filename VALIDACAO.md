<div align="center">

# ✅ Validação

**O que foi testado no ClusterGuard SCADA, com quais resultados e até onde isso vale**

[← Voltar ao README](README.md) •
[Metodologia](METODOLOGIA.md) •
[Algoritmos](ALGORITMOS_IA.MD)

</div>

---

## 📋 Índice

1. [Resumo](#-resumo)
2. [Testes automatizados](#-testes-automatizados)
3. [Integridade dos dados](#-integridade-dos-dados)
4. [Análise em notebooks](#-análise-em-notebooks)
5. [Ensaios de integração](#-ensaios-de-integração--14102026)
6. [Limites](#-limites)

---

## 🧾 Resumo

| Verificação | Resultado |
|---|---|
| Testes automatizados | **16 testes, `OK`**, em 14,218 s (Windows, Python 3.14.6, 14/11/2026) |
| Execução padrão | Término sem erro e **140 janelas** |
| Reagregação | `features.csv` e `avaliacao.csv` reproduzidos **byte a byte** em 20 ensaios (2.960 janelas) |
| Lote final | 12 ensaios, 2.160 janelas, conferidas com as tabelas de origem |
| Ensaios de integração | 3 ensaios de 20 s, sem falhas legítimas |

---

## 🧪 Testes automatizados

```powershell
python -m unittest -v test_laboratorio.py
```

Execução registrada em **14/11/2026**: Windows, Python 3.14.6, 16 testes em 14,218 s, resultado `OK`.

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

**Outras verificações de execução:**

- A execução padrão foi verificada em pasta temporária: término sem erro e 140 janelas.
- A sintaxe dos três scripts é compatível com a gramática do Python 3.11. A execução acima foi feita com o 3.14.6.

---

## 🔐 Integridade dos dados

### Reagregação dos 20 ensaios

A reagregação em cópias dos 20 ensaios existentes reproduziu `features.csv` e `avaliacao.csv` **byte a byte**, num total de **2.960 janelas**. Os brutos das cópias permaneceram inalterados. Nesse conjunto, **180 janelas** não têm consulta legítima e mantêm vazias as medições correspondentes.

### Lote final

O lote final reúne **12 ensaios** e **2.160 janelas**:

| Conjunto | Janelas |
|---|---:|
| Treino | 1.080 |
| Validação | 540 |
| Teste | 540 |

- As linhas do consolidado conferem com as tabelas de origem.
- **155 janelas** não têm medição de latência do cliente legítimo.
- Os logs contêm **2.856 consultas legítimas** e **4.080 de carga**, todas com sucesso registrado.

> [!NOTE]
> Os totais de 180 e 155 janelas sem consulta se referem a conjuntos diferentes: os **20 ensaios** existentes e os **12 ensaios** do lote final, respectivamente.

---

## 📓 Análise em notebooks

- As métricas de K-Means e DENCLUE vêm das saídas salvas nos notebooks 09 a 12.
- O ajuste dos modelos **não foi reexecutado** na conferência documental.
- As matrizes de confusão sustentam os valores apresentados em [`ALGORITMOS_IA.MD`](ALGORITMOS_IA.MD).

**Ferramentas de apoio:**

- O painel de terminal foi verificado com fases de 1 s em pasta temporária.
- O lote teve comandos e mensagens conferidos com substitutos para subprocessos e existência de pastas. Essa verificação **não** iniciou outro lote experimental.

---

## 🔬 Ensaios de integração — 14/10/2026

O registro histórico informa Python 3.12.14 em Linux e quatro testes aprovados. Foram executados três ensaios de 20 s: 8 s normais, 4 s de carga e 8 s de recuperação.

| Ensaio | Taxa alvo | Consultas de carga | Taxa efetiva | Consultas legítimas | Falhas legítimas |
|---|---:|---:|---:|---:|---:|
| `ensaio_1_20rps` | 20/s | 80 | 20,00/s | 20 | 0 |
| `ensaio_2_50rps` | 50/s | 200 | 50,00/s | 20 | 0 |
| `ensaio_3_100rps` | 100/s | 400 | 99,99/s | 20 | 0 |

- A taxa efetiva divide as tentativas concluídas pela duração medida da fase.
- Os ensaios usam taxas diferentes e verificam **integração**. Não são repetições de uma configuração única.
- O teste de timeout usa um servidor de teste que não responde, separado dos dados experimentais.

---

## 🚧 Limites

> [!WARNING]
> Os testes verificam o caminho local implementado. A ausência de falhas **não** demonstra comportamento sob saturação nem eficácia em rede industrial.

**Não certificam:**

- conformidade Modbus completa;
- equipamentos físicos;
- todas as versões do Python;
- uma instalação limpa do sistema.

**Limitações que permanecem** (descritas em [`METODOLOGIA.md`](METODOLOGIA.md)):

- status do JSON;
- indexação temporal;
- contagem do painel;
- pastas ignoradas pelo lote;
- convergência do DENCLUE.
