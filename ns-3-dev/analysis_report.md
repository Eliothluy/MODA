# Relatório de Análise de Desempenho da Simulação RSLAQ

## 1. Introdução
Este relatório analisa os resultados da simulação RSLAQ (Radio/Network Slice‑Aware QoS) em cenários de tráfego variados, executada no simulador NS‑3 com módulo 5G‑LENA. O objetivo é avaliar o comportamento de uma rede 5G com três fatias de serviço (eMBB, URLLC, MTC) sob diferentes cargas de tráfego, utilizando scheduler Round‑Robin (RR) e sem otimização dinâmica.

## 2. Metodologia
### 2.1 Configuração da Simulação
- **Cenários**: `low_traffic`, `normal`, `congestion`, `stressed`, `insufficient_resources`
- **Fatias**: 
  - **eMBB** (5 UEs, pacote 1500 B)
  - **URLLC** (5 UEs, pacote 50 B, fluxo GBR)
  - **MTC** (10 UEs, pacote 100 B)
- **Cargas oferecidas (Mbps)**:
  | Cenário          | eMBB | URLLC | MTC  |
  |------------------|------|-------|------|
  | low_traffic      | 0.05 | 1.0   | 2.0  |
  | normal           | 70   | 1.0   | 2.0  |
  | congestion       | 100  | 1.0   | 100  |
  | stressed         | 100  | 1.0   | 100  |
  | insufficient_resources | 100 | 2.0 | 100 |

- **Parâmetros de rede**:
  - Banda: 10 MHz, numerologia 0, frequência 2.59 GHz
  - TDD: `DL|DL|DL|DL|DL|DL|UL|UL|DL|UL`
  - Scheduler: Round‑Robin (RR)
  - Tempo de simulação: 4 s, tráfego inicia em 0.5 s
  - Buffer RLC: ilimitado (`999999999`)

### 2.2 Métricas de Desempenho
- **Throughput** (Mbps): taxa de recepção de dados
- **Atraso médio** (ms): tempo médio de traslado dos pacotes
- **Jitter** (ms): variância do atraso
- **PDR** (Packet Delivery Ratio): razão entre pacotes recebidos e transmitidos
- **PLR** (Packet Loss Ratio): razão entre pacotes perdidos e transmitidos

## 3. Resultados Consolidados
### 3.1 Métricas por Fatia e Cenário
| Cenário | Fatia | Throughput (Mbps) | Atraso (ms) | Jitter (ms) | PDR | PLR |
|---------|-------|-------------------|-------------|-------------|------|------|
| low_traffic | eMBB | 0.052 | 17.50 | 10.53 | 1.0000 | 0.0000 |
| low_traffic | URLLC | 1.558 | 5.13 | 1.03 | 0.9989 | 0.0000 |
| low_traffic | MTC | 2.556 | 6.03 | 2.08 | 0.9985 | 0.0000 |
| normal | eMBB | 11.431 | 1332.68 | 5.41 | 0.1603 | 0.0000 |
| normal | URLLC | 1.558 | 6.03 | 1.60 | 0.9989 | 0.0000 |
| normal | MTC | 2.556 | 6.76 | 2.80 | 0.9985 | 0.0000 |
| congestion | eMBB | 8.288 | 1624.68 | 7.48 | 0.0814 | 0.0000 |
| congestion | URLLC | 1.558 | 4.69 | 0.51 | 0.9989 | 0.0000 |
| congestion | MTC | 16.423 | 1546.62 | 0.69 | 0.1283 | 0.0000 |
| stressed | eMBB | 8.288 | 1624.68 | 7.48 | 0.0814 | 0.0000 |
| stressed | URLLC | 1.558 | 4.69 | 0.51 | 0.9989 | 0.0000 |
| stressed | MTC | 16.423 | 1546.62 | 0.69 | 0.1283 | 0.0000 |
| insufficient_resources | eMBB | 6.437 | 1649.48 | 9.51 | 0.0632 | 0.0000 |
| insufficient_resources | URLLC | 3.115 | 6.12 | 1.01 | 0.9983 | 0.0000 |
| insufficient_resources | MTC | 13.186 | 1593.29 | 0.84 | 0.1030 | 0.0000 |

### 3.2 Throughput Total por Cenário
| Cenário | Throughput Total (Mbps) | PDR Médio |
|---------|-------------------------|-----------|
| low_traffic | 4.167 | 0.9991 |
| normal | 15.546 | 0.5472 |
| congestion | 26.269 | 0.1414 |
| stressed | 26.269 | 0.1414 |
| insufficient_resources | 22.737 | 0.1330 |

## 4. Análise Detalhada

### 4.1 Comportamento da Fatia eMBB
- **Cenário de baixa carga**: throughput proporcional à carga, PDR perfeito, atraso moderado (17.5 ms).
- **Cenário normal**: saturação severa. Apesar de oferecer 70 Mbps, a fatia atinge apenas 11.4 Mbps, com PDR de 16% e atraso de 1.3 s. Indica que a capacidade da célula para eMBB é limitada.
- **Cenários congestion/stressed/insufficient_resources**: piora adicional. Throughput cai para 6.4‑8.3 Mbps, PDR entre 6‑8%, atrasos >1.6 s. A alta carga combinada esgota recursos de rádio.

### 4.2 Comportamento da Fatia URLLC
- **Consistência notável**: mantém throughput próximo à carga oferecida (1.5‑3.1 Mbps) em todos os cenários.
- **Latência baixa e estável**: atraso entre 4.7‑6.1 ms, jitter <1.6 ms.
- **PDR sempre >0.998**: demonstra que o mecanismo de QoS (dedicated QoS flows com GBR) garante isolamento e priorização efetiva.

### 4.3 Comportamento da Fatia MTC
- **Sensível à carga**: em baixa carga (2 Mbps) funciona bem (PDR 0.9985). Ao aumentar para 100 Mbps, o throughput cresce para 13‑16 Mbps mas com PDR muito baixo (10‑13%) e atrasos altos (1.5‑1.6 s).
- **Menos degradada que eMBB**: apesar da alta carga, o throughput absoluto é maior devido ao maior número de UEs (10 vs 5).

### 4.4 Comparação entre Cenários
- **low_traffic**: linha de base ideal, todas as fatias operam dentro do esperado.
- **normal**: ponto de inflexão. A eMBB já está saturada, mas URLLC e MTC ainda performam.
- **congestion/stressed**: sobrecarga generalizada. eMBB e MTC sofrem, URLLC permanece imune.
- **insufficient_resources**: semelhante a congestion, mas URLLC com dobro de carga ainda mantém qualidade, mostrando robustez.

### 4.5 Isolamento entre Fatias
- **URLLC está isolada**: não é afetada pelo aumento de carga das outras fatias. Isso indica que o mecanismo de dedicated QoS flows com GBR funciona como pretendido.
- **eMBB e MTC competem**: ambas sofrem degradação quando a carga aumenta, sugerindo que o scheduler RR não oferece isolamento suficiente entre elas.
- **Ausência de perda de pacotes (PLR=0)**: peculiar, pode indicar que pacotes são descartados antes da transmissão ou buffering infinito (tamanho do buffer RLC configurado como ilimitado).

## 5. Conclusões e Recomendações

### 5.1 Conclusões
1. **O scheduler Round‑Robin é inadequado para cenários multi‑slice com requisitos heterogêneos**. Ele não diferencia entre fatias com diferentes necessidades de QoS, resultando em degradação severa das fatias eMBB e MTC quando a carga aumenta.
2. **O mecanismo de dedicated QoS flows com GBR protege efetivamente a fatia URLLC**, garantindo baixa latência e alta confiabilidade mesmo em condições de sobrecarga.
3. **A capacidade da célula é limitada**: com 10 MHz de banda e TDD downlink‑dominante, a taxa máxima sustentável parece ser da ordem de 15‑20 Mbps no total.
4. **O buffering ilimitado (RLC UM) pode estar mascarando perdas reais**, causando atrasos extremos em vez de descartes visíveis (PLR=0).

### 5.2 Recomendações
1. **Implementar um scheduler de fatia-aware** (ex: Weighted Round‑Robin ou deficit Round‑Robin) para garantir garantias mínimas de recursos por fatia.
2. **Configurar tamanhos de buffer RLC realistas** para evitar atrasos infinitos e permitir que perdas ocorram de forma controlada.
3. **Considerar separação de recursos em nível de MAC** (ex: PRB dedication por fatia) para eMBB e MTC, ou pelo menos pesos diferentes no scheduler.
4. **Validar os requisitos de capacidade da célula** contra as cargas oferecidas nos cenários; é possível que 100 Mbps por fatia seja irrealista para a configuração atual.
5. **Explorar schedulers PF (Proportional Fair) ou MAX‑CQI** para melhorar a eficiência espectral sem sacrificar completamente o isolamento.

### 5.3 Limitações do Estudo
- Simulação simplificada (célula única, SISO, sem mobilidade, canal estático).
- Scheduler RR não representa a complexidade de implementações reais 5G.
- Buffer ilimitado distorce a métrica de perda.

---

**Data da análise**: 01/04/2026  
**Ferramentas**: NS‑3 (5G‑LENA), CSV exportado via `rslaq-simulation-fixed.cc`