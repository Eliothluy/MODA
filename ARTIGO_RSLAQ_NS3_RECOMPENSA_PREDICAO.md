# RSLAQ-NS3: Otimizacao SLA-Aware de Recursos em Redes 5G/O-RAN com Recompensa Eficiente e Predicao Temporal de KPIs

## Resumo

A evolucao das redes 5G e 6G torna a operacao de fatias de rede um problema simultaneamente tecnico e contratual: alem de maximizar vazao ou reduzir atraso, o controlador deve manter indicadores de desempenho dentro dos limites definidos por acordos de nivel de servico (SLAs). O trabalho RSLAQ propos um xApp baseado em aprendizado por reforco profundo para operar slices eMBB, URLLC e MTC em uma arquitetura O-RAN, integrando SLAs diretamente na funcao de recompensa. Este artigo apresenta uma reproducao e extensao do RSLAQ em um ambiente ns-3/5G-LENA integrado ao ns-o-ran-gym. A primeira contribuicao e metodologica: migramos a formulacao do RSLAQ para uma simulacao de sistema baseada em ns-3, com topologia 5G, FlowMonitor, escalonamento MAC slice-aware e comunicacao online com agentes DRL via IPC. A segunda contribuicao e uma funcao de recompensa orientada a eficiencia de recursos, que preserva a penalizacao SLA-aware do RSLAQ e adiciona shaping somente quando nao ha violacao de SLA. A terceira contribuicao e uma extensao preditiva, na qual um previsor temporal baseado em GRU estima risco futuro de outage, violacao soft e KPIs normalizados a partir de janelas historicas de estados, acoes e recompensas. A proposta e avaliada contra o RSLAQ fiel ao artigo e contra baselines nativos do ns-3, permitindo separar aderencia a SLA, eficiencia de alocacao de PRBs e beneficio da antecipacao temporal de risco.

Palavras-chave: O-RAN, RAN slicing, SLA, 5G, ns-3, 5G-LENA, aprendizado por reforco profundo, SAC, DDQN, predicao temporal.

## 1. Introducao

Redes moveis modernas precisam atender servicos heterogeneos em uma mesma infraestrutura fisica. Aplicacoes eMBB demandam alta vazao, URLLC exige baixa latencia e filas reduzidas, enquanto MTC envolve grande numero de dispositivos e padroes de trafego intermitentes. A tecnica de network slicing permite isolar logicamente esses servicos, mas a simples divisao estatica de recursos pode gerar desperdicio quando uma fatia esta ociosa ou outage quando a demanda se desloca rapidamente entre fatias.

O paradigma O-RAN introduz controladores inteligentes capazes de transformar politicas de alto nivel em acoes de controle na RAN. Nesse contexto, xApps no Near-RT RIC podem observar KPIs, decidir alocacao de PRBs e selecionar politicas de escalonamento em intervalos compativeis com a operacao da rede. O RSLAQ avanca essa linha ao incorporar SLAs explicitamente no processo de aprendizado, fazendo com que o agente nao apenas otimize metricas medias, mas receba penalizacoes diretas quando os requisitos contratuais deixam de ser atendidos.

Este artigo parte do RSLAQ como referencia cientifica e pergunta: como reproduzir e estender essa ideia em um ambiente ns-3/5G-LENA online, com trafego de rede, escalonamento MAC, buffers, perdas e dinamica temporal observaveis? A resposta envolve tres escolhas centrais. Primeiro, manter uma implementacao fiel da recompensa RSLAQ como baseline experimental. Segundo, propor uma recompensa adicional para eficiencia de recursos por slice, sem diluir a semantica de SLA da Eq. 12 do RSLAQ. Terceiro, adicionar predicao temporal de KPIs para que o agente possa antecipar risco de violacao antes que o estado corrente ja esteja degradado.

## 2. Fundamentacao: RSLAQ e SLA-Aware DRL

O RSLAQ modela a operacao de QoS em O-RAN como um problema de aprendizado por reforco no qual o agente observa estatisticas da RAN e retorna acoes de controle para as fatias. Para tres slices, o estado segue a estrutura matricial:

$$
s_t =
\begin{bmatrix}
btx_{0} & btx_{1} & btx_{2} & btx_{cell} \\
bfs_{0} & bfs_{1} & bfs_{2} & bfs_{cell} \\
rsh_{0} & rsh_{1} & rsh_{2} & rsh_{cell} \\
tdp_{0} & tdp_{1} & tdp_{2} & tdp_{cell}
\end{bmatrix},
$$

em que $btx$ representa bytes transmitidos ou ofertados, $bfs$ representa ocupacao de buffer, $rsh$ representa participacao de recursos e $tdp$ representa perdas ou pacotes descartados. No nosso ambiente, essa observacao e implementada como uma matriz $4 \times 4$ no modo `observation_mode="paper"`.

A acao no RSLAQ combina alocacao de recursos por slice e, quando aplicavel, selecao de escalonador intra-slice. A formulacao original discretiza proporcoes de PRBs e combina essas proporcoes com escalonadores como RR, PF e BCQI. Na reproducao com DDQN, essa estrutura discreta e preservada. Na extensao com SAC, a acao e continua e representa diretamente a proporcao de PRBs por slice; nesse caso, a selecao explicita de escalonador pode ser desabilitada, mantendo o foco na otimizacao inter-slice.

O ponto central do RSLAQ e a funcao de recompensa. Ela separa metricas de otimizacao de condicoes de violacao de SLA. Assim, estados sem violacao recebem uma recompensa positiva ponderada, enquanto estados com outage ou violacao soft recebem recompensas especiais que interrompem ou penalizam a trajetoria, dependendo da configuracao experimental.

## 3. Metodologia de Simulacao com ns-3/5G-LENA

### 3.1 Ambiente de rede

A implementacao foi desenvolvida em dois componentes acoplados. O primeiro e o simulador C++ em `ns-3-dev/scratch/rslaq/`, responsavel pela rede 5G. O segundo e o pacote Python `ns-o-ran-gym`, responsavel pelo ambiente Gymnasium, agentes DRL, recompensa, logs e extensao preditiva.

A topologia simulada no ns-3 segue o fluxo:

$$
remoteHost \rightarrow PGW/EPC \rightarrow gNB\ NR \rightarrow UEs\ NR.
$$

O enlace entre `remoteHost` e PGW/EPC usa ponto-a-ponto de alta capacidade. A celula possui um gNB fixo e UEs estaticos distribuidos uniformemente em um disco ao redor do gNB. Os UEs sao associados a tres slices logicos por faixas de identificador: slice 0 para eMBB, slice 1 para URLLC e slice 2 para MTC. Cada UE recebe um fluxo UDP downlink, e a porta UDP de destino e usada para mapear estatisticas do FlowMonitor de volta para UE e slice.

O perfil fisico padrao utiliza portadora em 3.55 GHz, largura de banda de 100 MHz, numerologia $\mu=1$ com SCS de 30 kHz, canal 3GPP UMi, sombreamento configuravel, antena de gNB do tipo painel e antenas isotropicas nos UEs. A simulacao registra series temporais por UE e agregados por slice, incluindo vazao, bytes transmitidos/recebidos, ocupacao de buffer, perdas e participacao real de recursos.

### 3.2 Modos de execucao

O simulador opera em dois modos.

No modo standalone, o ns-3 executa campanhas de baseline sem agente Python. Ao final, gera `timeseries.csv`, `slice_alloc.csv`, `summary.csv` e `metadata.json`. Esse modo permite avaliar escalonadores nativos e variantes slice-aware sem DRL, como `pure_rr`, `pure_pf`, `pure_bcqi`, `slice_rr`, `slice_pf`, `slice_bcqi`, `slice_weighted_*`, `psta_equal` e `slice_custom`.

No modo online, o simulador usa IPC com semaforos POSIX e arquivos CSV. A cada periodo de controle (`periodMs`, tipicamente 10 ms), o ns-3 escreve KPIs agregados em `rslaq-kpms.txt`, sinaliza o ambiente Python, aguarda a acao do agente em `rslaq_actions_for_ns3.csv` e aplica os percentuais de PRBs no `RslaqMacScheduler`. Esse acoplamento permite treinar DDQN, SAC e SAC preditivo com o simulador em execucao, em vez de apenas usar traces offline.

### 3.3 Diferencas em relacao ao RSLAQ original

O RSLAQ original foi formulado e avaliado em simulacao sistemica propria do artigo. Nossa implementacao preserva a formulacao de estado, a logica de acoes e a recompensa SLA-aware, mas muda a infraestrutura experimental para ns-3/5G-LENA. Essa diferenca e metodologicamente relevante por quatro motivos.

Primeiro, o ns-3 explicita efeitos de rede como buffers, perdas, atraso de aplicacao, attach de UEs, HARQ, escalonamento MAC e variacao de canal. Segundo, a coleta de KPIs depende de FlowMonitor e do mapeamento entre fluxos UDP, UEs e slices, aproximando o pipeline de uma telemetria de rede. Terceiro, o agente atua online por IPC, de modo que cada acao altera a execucao subsequente da simulacao. Quarto, a implementacao separa claramente o baseline fiel ao artigo (`reward_mode="paper"`) da contribuicao proposta (`reward_mode="resource_efficient"`), evitando comparar recompensas heterogeneas como se fossem a mesma metrica.

Essa separacao e essencial para a defesa cientifica do trabalho. O modo `paper` responde se a formulacao RSLAQ foi reproduzida corretamente no ns-3. O modo `resource_efficient` responde se a nova proposta melhora o uso de recursos mantendo a disciplina de SLA.

## 4. Recompensa RSLAQ Fiel ao Artigo

No modo `paper`, a recompensa segue a estrutura do RSLAQ. Para cada passo de controle, calculam-se tres termos de otimizacao, um por slice.

Para eMBB, a recompensa usa a vazao media por UE normalizada pela vazao maxima de referencia:

$$
h_1 = \min\left(\frac{\bar{T}_{eMBB}}{T_{max}}, 1\right),
\qquad
\bar{T}_{eMBB}=\frac{T_{eMBB}}{|\Lambda_{eMBB}|}.
$$

Para URLLC, a recompensa privilegia baixa ocupacao maxima de buffer:

$$
h_2 = \exp\left(-\frac{B^{max}_{URLLC}}{B_{norm}}\right).
$$

Para MTC, usa-se novamente vazao media por UE normalizada:

$$
h_3 = \min\left(\frac{\bar{T}_{MTC}}{T_{max}}, 1\right),
\qquad
\bar{T}_{MTC}=\frac{T_{MTC}}{|\Lambda_{MTC}|}.
$$

A recompensa de otimizacao e:

$$
r_{opt}=\alpha h_1+\beta h_2+\gamma h_3+\mathbb{1}_{sched}\frac{1}{c(s)}.
$$

Os pesos padrao adotados sao:

$$
\alpha=0.3333,\qquad \beta=0.4000,\qquad \gamma=0.2667,
$$

correspondendo a eMBB, URLLC e MTC. Quando a acao inclui selecao de escalonador, o custo segue a logica do RSLAQ: RR tem custo 1, enquanto PF e BCQI tem custo 2. Em treinamentos SAC continuos sem selecao explicita de escalonador, o termo $1/c(s)$ e omitido.

A logica de SLA e:

$$
r_{RSLAQ}=\begin{cases}
-\sum_{j\in\mathcal{O}}\omega_j, & \text{se houver outage de SLA},\\
0, & \text{se houver violacao soft de SLA},\\
r_{opt}, & \text{caso contrario}.
\end{cases}
$$

O conjunto $\mathcal{O}$ contem os slices em outage confirmado, e $\omega_j$ e o peso do slice. A implementacao usa checagem instantanea de outage consistente com confiabilidade de 100% por passo, mas adiciona duas salvaguardas praticas para ns-3: uma janela de warm-up e uma confirmacao por passos consecutivos. Essas salvaguardas filtram transientes de inicializacao, attach, ramp-up de aplicacao, preenchimento de buffers e jitter do simulador. A penalidade de outage nao e suavizada; apenas evita-se que uma flutuacao inicial encerre o treinamento antes que o agente colete trajetorias informativas.

Durante treinamento, tambem se permite desacoplar penalizacao de SLA e terminacao de episodio. Com `terminate_on_sla_violation=False`, o agente recebe exatamente a penalidade da Eq. 12, mas o episodio pode continuar ate o horizonte periodico. Essa escolha e defensavel porque xApps em operacao real nao deixam de existir apos uma violacao; eles continuam atuando para restaurar a QoS. Portanto, o agente observa estados antes, durante e apos a violacao, aprendendo dinamicas de recuperacao em vez de preencher o replay buffer apenas com trajetorias curtas de falha inicial.

## 5. Recompensa Proposta para Eficiencia de Recursos

A extensao proposta parte de uma restricao de desenho: nenhuma melhoria de eficiencia pode mascarar violacoes de SLA. Assim, a recompensa eficiente e um shaping aplicado somente quando nao ha outage nem violacao soft. Formalmente:

$$
r_{eff}=\begin{cases}
r_{RSLAQ}, & \text{se houver outage ou violacao soft},\\
r_{RSLAQ}+\Delta r_{eff}, & \text{caso contrario}.
\end{cases}
$$

O termo adicional combina eficiencia de entrega, alinhamento entre demanda e alocacao, penalidade por superalocacao, penalidade por subalocacao e suavidade da acao:

$$
\Delta r_{eff}=\lambda_E E+\lambda_M M-\lambda_O O-\lambda_U U-\lambda_S S.
$$

Os pesos padrao da implementacao sao:

$$
\lambda_E=0.20,\quad
\lambda_M=0.15,\quad
\lambda_O=0.25,\quad
\lambda_U=0.10,\quad
\lambda_S=0.05.
$$

Na versao preditiva, os scripts podem usar uma parametrizacao simetrica para alguns termos, por exemplo $\lambda_M=\lambda_O=\lambda_U=0.20$, mantendo o mesmo principio de projeto.

A alocacao efetiva e normalizada como:

$$
a_j=\frac{p_j}{\sum_k p_k},
$$

em que $p_j$ e o percentual de PRBs alocado ao slice $j$. Quando a acao nao esta disponivel, a implementacao usa a participacao de recursos observada no ns-3 como fallback.

A necessidade dinamica de cada slice e estimada por:

$$
n_j=TX_j+B_j+C_L L_j,
$$

onde $TX_j$ sao bytes transmitidos/ofertados, $B_j$ e o buffer maximo, $L_j$ e o numero de pacotes perdidos e $C_L$ e o equivalente em bytes por pacote perdido. Em seguida, aplicam-se ajustes especificos por slice: eMBB aumenta necessidade quando a vazao fica abaixo da meta minima; URLLC aumenta necessidade conforme pressao de buffer; MTC aumenta necessidade moderadamente quando sua vazao fica abaixo da meta.

A participacao dinamica da demanda e:

$$
d_j=\frac{n_j}{\sum_k n_k}.
$$

O alvo eficiente mistura pesos estaticos do RSLAQ e demanda observada:

$$
q_j=(1-\rho)\omega_j+\rho d_j,
$$

com $\rho=0.75$ por padrao. Portanto, a proposta nao abandona a prioridade do operador; ela a combina com a demanda corrente.

O casamento entre demanda e alocacao e:

$$
M=\max\left(0,1-\frac{1}{2}\sum_j |a_j-q_j|\right).
$$

A superalocacao e subalocacao sao:

$$
O=\sum_j\max(a_j-q_j-\epsilon,0),
\qquad
U=\sum_j\max(q_j-a_j-\epsilon,0),
$$

com tolerancia $\epsilon=0.03$. A fracao servida e:

$$
s_j=\min\left(\frac{RX_j}{TX_j},1\right),
$$

e a eficiencia de entrega e:

$$
E=M\sum_j q_j s_j.
$$

Finalmente, a suavidade de acao penaliza oscilacoes bruscas de PRBs:

$$
S=\frac{1}{2}\sum_j |a_j(t)-a_j(t-1)|.
$$

A defesa da recompensa proposta e que ela desloca a otimizacao do agente de "cumprir SLA a qualquer custo" para "cumprir SLA com menor desperdicio e melhor alinhamento com demanda". Como o shaping e nulo em estados de violacao, a Eq. 12 permanece dominante. Isso evita a falha metodologica de recompensar economia de PRBs quando a rede ja esta descumprindo o contrato de servico.

## 6. Predicao Temporal de KPIs e Risco de SLA

O modulo preditivo adiciona memoria temporal ao processo de decisao. Em vez de observar apenas o estado corrente $s_t$, o agente SAC preditivo recebe tambem uma estimativa de risco futuro produzida por um previsor GRU treinado offline.

Cada frame temporal contem:

- a observacao RSLAQ $4\times4$ achatada;
- a acao de alocacao por slice;
- a recompensa normalizada;
- flags de outage por slice;
- flags de violacao soft por slice;
- codificacao one-hot do cenario.

Logo, o vetor de entrada por passo possui dimensao:

$$
16 + 3 + 1 + 6 + 5 = 31,
$$

onde 16 vem da observacao, 3 da acao, 1 da recompensa, 6 dos riscos binarios e 5 dos cenarios. A rede recebe uma janela historica de comprimento $L$ e produz um alvo composto por riscos futuros e KPIs medios normalizados no horizonte $H$:

$$
\hat{y}_{t:t+H}=f_{GRU}(x_{t-L+1},\ldots,x_t).
$$

O alvo preditivo possui 22 dimensoes: seis indicadores de risco futuro, correspondentes a outage e violacao soft para tres slices, e 16 valores medios da observacao futura. O treinamento usa BCE para os riscos binarios e MSE para os KPIs continuos, com peso adicional para risco, pois antecipar violacao de SLA e mais critico do que prever pequenas variacoes de KPI.

O conjunto de treinamento do previsor pode vir de duas fontes. A primeira sao logs `step_metrics.csv` gerados por agentes DRL. A segunda sao traces `timeseries.csv` de campanhas ns-3 standalone, agregados por UE e slice. Quando se usam baselines ns-3, a implementacao reconstrui frames por timestamp, estima alocacao por `slice_alloc.csv` quando disponivel e recalcula recompensa e flags de SLA com a recompensa `resource_efficient`. Isso alinha os rotulos do previsor com a contribuicao do artigo.

Durante o treinamento online, o `TemporalKpiForecaster` permanece congelado. O SAC preditivo concatena a observacao corrente com a saida do GRU. Alem disso, a funcao de treinamento inclui penalidades explicitas de risco, como `risk_penalty` para outage futuro e `soft_penalty` para violacao soft futura. Assim, o agente nao espera apenas a recompensa negativa acontecer; ele recebe informacao antecipada sobre estados que provavelmente levarao a violacao.

## 7. Desenho Experimental

A avaliacao deve ser organizada em linhas experimentais separadas.

1. Baselines ns-3 sem DRL: `pure_rr`, `pure_pf`, `pure_bcqi` e variantes slice-aware.
2. RSLAQ fiel ao artigo: DDQN ou SAC com `reward_mode="paper"`.
3. Proposta eficiente: DDQN ou SAC com `reward_mode="resource_efficient"`.
4. Proposta preditiva: SAC com observacao aumentada por GRU e `reward_mode="resource_efficient"`.

Essa organizacao evita uma comparacao inadequada entre rewards absolutos. O ranking principal deve usar metricas de rede e SLA, nao apenas reward acumulado, porque `paper` e `resource_efficient` otimizam objetivos relacionados, mas nao identicos.

As metricas recomendadas sao:

- taxa de outage por slice;
- taxa de violacao soft;
- throughput medio por slice;
- buffer maximo ou medio do URLLC;
- perdas por slice;
- PRB medio por slice;
- eficiencia de recursos;
- casamento demanda-alocacao;
- superalocacao;
- subalocacao;
- suavidade da acao;
- numero medio de passos por episodio;
- desempenho por cenario e por semente.

Os cenarios `low_traffic`, `normal`, `congestion`, `stressed` e `insufficient_resources` permitem testar desde baixa carga ate escassez. Essa variedade e importante porque uma recompensa eficiente deve reduzir desperdicio em baixa carga sem degradar SLA em congestionamento, enquanto a predicao deve ter maior impacto em cenarios nos quais o risco de violacao cresce antes de se tornar outage confirmado.

## 8. Defesa Metodologica

A principal defesa deste trabalho e que a contribuicao nao substitui o RSLAQ; ela o usa como baseline controlado. O modo `paper` preserva a recompensa original e permite verificar se a migracao para ns-3/5G-LENA mantem a semantica SLA-aware. O modo `resource_efficient` adiciona termos de eficiencia apenas quando o SLA esta satisfeito. Desse modo, a proposta nao relaxa requisitos de QoS nem transforma economia de recursos em objetivo superior ao contrato.

Tambem e defensavel tratar violacoes de SLA como estados penalizados nao absorventes durante alguns treinamentos. A recompensa negativa continua identica a formulacao RSLAQ; o que muda e a mecanica de reset do episodio. Em um simulador ns-3 online, encerramentos muito precoces podem fazer o replay buffer ser dominado por transientes de inicializacao, impedindo o agente de observar recuperacao apos uma acao corretiva. A continuidade do episodio representa melhor um xApp em operacao, que deve reagir a falhas em vez de simplesmente reiniciar.

A migracao para ns-3 reforca a validade externa da avaliacao, pois introduz efeitos de rede ausentes em modelos mais abstratos: filas, perdas, HARQ, escalonamento MAC, mapeamento de fluxos por UE, variacao de demanda e atraso entre acao e efeito. Por outro lado, essa mesma fidelidade exige cuidado na interpretacao. Nem toda violacao inicial representa falha da politica; algumas decorrem de warm-up, attach ou ramp-up de aplicacao. Por isso, a implementacao registra flags de SLA, termos de recompensa e diagnosticos de eficiencia separadamente.

A extensao preditiva tambem e coerente com a arquitetura O-RAN. O proprio RSLAQ descreve o papel do Non-RT RIC e de rApps na predicao de eventos e geracao de politicas, enquanto o Near-RT RIC executa controle em janela curta. Nosso previsor GRU funciona como um componente temporal auxiliar: ele aprende de traces anteriores e fornece ao agente near-RT uma estimativa compacta de risco futuro. Isso aproxima o controle de uma operacao proativa, na qual o xApp pode realocar recursos antes que o KPI ja tenha cruzado o limiar de outage.

## 9. Ameacas a Validade

A primeira ameaca e a diferenca entre o simulador original do RSLAQ e o ns-3/5G-LENA. Embora a formulacao matematica seja preservada, os valores absolutos de KPI podem diferir por causa de canal, antenas, RLC, HARQ e trafego. Por isso, a avaliacao deve enfatizar comparacoes internas no mesmo ambiente ns-3.

A segunda ameaca e a calibracao dos pesos da recompensa eficiente. Pesos excessivos para economia podem induzir subalocacao em cenarios criticos; por isso, a implementacao bloqueia shaping em estados com violacao de SLA e registra diagnosticos separados.

A terceira ameaca e o treinamento offline do previsor. Se os traces usados para treinar o GRU nao cobrirem adequadamente os cenarios de avaliacao, a predicao pode introduzir vies. A mitigacao e treinar com multiplos cenarios, sementes e baselines, e reportar desempenho do previsor separadamente do desempenho do agente.

A quarta ameaca e comparar rewards entre modos diferentes. Como o modo eficiente adiciona shaping, reward acumulado nao deve ser a metrica principal para concluir superioridade. A comparacao deve priorizar SLA, throughput, perdas, buffers e eficiencia de recursos.

## 10. Conclusao

Este artigo apresentou uma reproducao e extensao do RSLAQ em ns-3/5G-LENA. A metodologia preserva o RSLAQ original como baseline (`reward_mode="paper"`) e introduz uma recompensa proposta (`reward_mode="resource_efficient"`) que incentiva alocacao eficiente de PRBs somente quando nao ha violacao de SLA. A extensao preditiva baseada em GRU adiciona informacao temporal ao agente SAC, permitindo antecipar risco de outage e violacao soft. A contribuicao central e, portanto, dupla: uma plataforma experimental mais proxima da dinamica de rede 5G/O-RAN e uma politica de aprendizado que busca cumprir SLA com menor desperdicio de recursos e maior capacidade proativa.

Em termos cientificos, a proposta deve ser defendida nao como uma alteracao arbitraria do RSLAQ, mas como uma decomposicao controlada: primeiro reproduz-se a recompensa do artigo; depois adiciona-se eficiencia como shaping condicionado ao cumprimento de SLA; por fim, adiciona-se predicao temporal para antecipar falhas. Essa ordem torna a avaliacao auditavel, separa baseline de contribuicao e permite demonstrar claramente onde esta o ganho da nova implementacao.
