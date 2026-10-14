# Validação da entrega

Executado em Python 3.12.14, Linux. Data: 14/10/2026.

Quatro testes automatizados passaram: conexão recusada, timeout, experimento completo com reagregação idêntica e proteção contra sobrescrita, e rejeição de parâmetros fora dos limites.

Também foram executados três ensaios locais de 20 segundos cada (8 s normais, 4 s de carga e 8 s de recuperação). As taxas abaixo correspondem às tentativas de carga concluídas divididas pela duração real da fase, não ao tráfego de uma rede física.

| Ensaio | Taxa alvo | Tentativas de carga | Taxa efetiva carga | Consultas legítimas | Falhas legítimas |
|---|---:|---:|---:|---:|---:|
| ensaio_1_20rps | 20.0 | 80 | 20.00/s | 20 | 0 |
| ensaio_2_50rps | 50.0 | 200 | 50.00/s | 20 | 0 |
| ensaio_3_100rps | 100.0 | 400 | 99.99/s | 20 | 0 |

Não houve evidência de indisponibilidade nesses ensaios curtos: todas as consultas legítimas tiveram sucesso. Portanto, os exemplos demonstram coleta sob carga e funcionamento da integração, sem comprovar DoS efetivo ou eficácia de K-Means/DENCLUE. O ensaio de timeout foi separado, com um servidor de teste que não responde, sem introduzir falhas artificiais nos dados experimentais.

Não foi executado no Windows/Hyper-V do usuário. Os exemplos não devem ser apresentados como resultados coletados no homelab ou como repetição estatística de uma mesma configuração, pois usam três taxas distintas. Para o artigo final, executar as repetições documentadas no README e analisar os dados com o Bryan.

A implementação utiliza apenas a biblioteca padrão do Python; não depende de uma versão corrente do pymodbus. A validação verifica o protocolo usado no próprio laboratório e os tamanhos de mensagens; não certifica conformidade completa Modbus industrial.
