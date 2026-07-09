# AGENTS.md

Contexto vigente para este workspace: considerar este arquivo como a referência principal para qualquer agente de IA que trabalhe no paper, na revisão textual, na análise metodológica, na implementação experimental ou na organização dos resultados.

Este documento deve preservar o escopo atual da pesquisa. Agentes não devem reformular o problema, trocar as variáveis de decisão, substituir o objetivo experimental ou alterar o conjunto principal de comparações sem instrução explícita do autor.

---

## 1. Contexto do Paper

O paper investiga como diferentes meta-heurísticas se comportam na otimização da distribuição de recursos entre slices em redes 5G/O-RAN.

O problema é formulado como um problema de otimização contínua, no qual os pesos de alocação dos slices são as variáveis de decisão. A formulação atual deve ser mantida durante a escrita, revisão e implementação.

O objetivo experimental central é avaliar a capacidade de diferentes métodos de busca em encontrar bons vetores de pesos de alocação para os slices. A conclusão principal do trabalho deve indicar, de forma explícita, qual meta-heurística encontrou as melhores soluções para essa formulação.

---

## 2. Escopo Inalterável da Pesquisa

Os seguintes pontos são decisões de projeto e devem ser preservados:

- O problema continua sendo tratado como otimização contínua.
- As variáveis de decisão continuam sendo os pesos de alocação dos slices.
- A formulação atual do problema deve ser mantida.
- As meta-heurísticas principais avaliadas são PSO, GA, SA e a meta-heurística híbrida reformulada pelo trabalho.
- A comparação deve permanecer centrada na qualidade das soluções encontradas para a formulação com pesos de alocação como variáveis de decisão.
- AQPS e RSLAQ devem ser mantidos como bases conceituais e comparativas do paper.
- Os schedulers puros RR, BCQI e PF devem ser usados como baselines de comparação.

Agentes não devem deslocar o foco do artigo para aprendizado por reforço, deep learning, projeto de novos schedulers, otimização discreta, programação inteira ou outra formulação alternativa, salvo se o autor solicitar explicitamente.

---

## 3. Formulação do Problema

A formulação deve ser apresentada como um problema de otimização contínua aplicado à distribuição de recursos entre slices em redes 5G/O-RAN.

### 3.1 Variáveis de decisão

A solução candidata deve ser representada por um vetor de pesos de alocação:

\[
\mathbf{w} = [w_1, w_2, \ldots, w_S]
\]

em que:

- \(S\) é o número de slices considerados no cenário experimental;
- \(w_i\) representa o peso de alocação associado ao slice \(i\);
- \(\mathbf{w}\) é a entrada otimizada pelas meta-heurísticas.

A interpretação dos pesos deve permanecer alinhada à formulação original do paper. Caso a implementação utilize normalização, projeção ou penalização para garantir viabilidade, isso deve ser descrito explicitamente na metodologia.

### 3.2 Domínio das variáveis

Salvo definição diferente já estabelecida no paper ou no código experimental, os pesos devem respeitar as seguintes condições gerais:

\[
w_i \geq 0, \quad \forall i \in \{1, \ldots, S\}
\]

\[
\sum_{i=1}^{S} w_i = 1
\]

Se a formulação oficial usar limites inferiores, limites superiores, normalização alternativa ou pesos não necessariamente normalizados, a versão oficial da formulação deve prevalecer. O agente deve apenas documentar essa escolha, não substituí-la.

### 3.3 Função objetivo

A função objetivo deve avaliar a qualidade de um vetor de pesos \(\mathbf{w}\) com base nas métricas de desempenho definidas no paper.

A estrutura geral deve ser descrita como:

\[
\max_{\mathbf{w}} F(\mathbf{w})
\]

ou, de forma equivalente, como minimização:

\[
\min_{\mathbf{w}} J(\mathbf{w}) = -F(\mathbf{w})
\]

A escolha entre maximização e minimização deve seguir a implementação experimental. Agentes não devem inverter o sentido da função objetivo sem verificar a convenção usada nos experimentos.

A definição de “melhor solução” deve estar diretamente associada ao valor da função objetivo, respeitando restrições de viabilidade e critérios experimentais definidos.

### 3.4 Restrições e penalidades

Caso uma solução candidata viole restrições da formulação, a metodologia deve explicar como a violação é tratada. Estratégias aceitáveis incluem:

- normalização do vetor de pesos;
- projeção para o domínio viável;
- penalização na função objetivo;
- descarte ou reparo da solução inviável.

A estratégia escolhida deve ser aplicada de forma consistente a PSO, GA, SA e à meta-heurística híbrida para evitar viés experimental.

---

## 4. Métodos Avaliados

### 4.1 Meta-heurísticas principais

O estudo deve comparar as seguintes meta-heurísticas:

- PSO — Particle Swarm Optimization;
- GA — Genetic Algorithm;
- SA — Simulated Annealing;
- Meta-heurística híbrida reformulada pelo trabalho.

A descrição de cada método deve enfatizar seu papel na busca por vetores de pesos de alocação. A explicação não deve transformar os algoritmos em schedulers independentes; eles atuam como mecanismos de otimização dos pesos.

### 4.2 Meta-heurística híbrida

A meta-heurística híbrida deve ser apresentada como a contribuição reformulada do trabalho. Sua descrição deve deixar claro:

- quais componentes algorítmicos são combinados;
- qual etapa favorece exploração global;
- qual etapa favorece exploração local ou refinamento;
- como uma solução candidata é representada;
- como soluções são atualizadas;
- como a função objetivo é avaliada;
- qual critério de parada é usado;
- por que a hibridização é adequada para a formulação contínua com pesos de alocação.

Agentes não devem inventar uma arquitetura híbrida diferente da usada no paper. Se a definição ainda estiver incompleta, o texto deve sinalizar a necessidade de explicitar a estrutura da híbrida, em vez de substituir a proposta.

---

## 5. Baselines e Comparações Obrigatórias

### 5.1 Comparação entre meta-heurísticas

A comparação principal deve ser feita entre:

- PSO;
- GA;
- SA;
- meta-heurística híbrida.

O objetivo dessa comparação é identificar qual método encontra as melhores soluções para a formulação proposta.

### 5.2 Comparação com schedulers puros

Os resultados das heurísticas e meta-heurísticas devem ser comparados com schedulers puros:

- RR — Round Robin;
- BCQI — Best Channel Quality Indicator;
- PF — Proportional Fair.

Essa comparação deve mostrar se a otimização dos pesos de alocação gera melhoria em relação ao uso direto de schedulers tradicionais.

### 5.3 Comparação com RSLAQ e AQPS

O paper deve manter AQPS e RSLAQ como bases relevantes.

A comparação com RSLAQ deve ser mantida na análise experimental ou na discussão dos resultados, conforme a estrutura atual do paper. RSLAQ representa a base orientada por aprendizado/reinforcement learning usada para posicionar a proposta em relação a métodos adaptativos existentes; quando os resultados da Phase 4 estiverem disponíveis, eles devem entrar como baseline DRL principal do paper.

AQPS deve continuar sendo usado como base conceitual, metodológica ou comparativa, conforme definido na pesquisa. No estado atual do código experimental, AQPS aparece como o modo `slice_aqps`: um baseline slice-aware que calcula orçamentos inteiros de RBGs por slice com garantia mínima para demandas ativas e ajuste por urgência/prioridade. Ele deve ser tratado como baseline adaptativo de alocação por slice, não como substituto da formulação principal baseada na otimização contínua dos pesos.

RSLAQ e AQPS servem para responder se a otimização offline por meta-heurísticas é competitiva frente a abordagens adaptativas já consideradas no trabalho. A redação deve preservar essa função comparativa sem deslocar o foco do artigo para DRL, aprendizado por reforço ou projeto de novos schedulers.

Agentes devem evitar remover RSLAQ ou AQPS da narrativa do paper.

---

## 6. Protocolo Experimental Recomendado

A metodologia experimental deve ser suficientemente detalhada para permitir reprodutibilidade.

Sempre que os dados estiverem disponíveis, o paper deve reportar:

- número de execuções independentes por algoritmo;
- número máximo de iterações ou avaliações da função objetivo;
- tamanho da população ou enxame, quando aplicável;
- parâmetros específicos de PSO, GA, SA e da híbrida;
- critérios de parada;
- sementes aleatórias ou procedimento de controle de aleatoriedade;
- ambiente de simulação;
- configuração dos slices;
- métricas de rede usadas na função objetivo;
- tempo de execução ou custo computacional, quando relevante.

Como recomendação estatística, quando não houver restrição contrária, usar múltiplas execuções independentes para cada método. Um valor típico é pelo menos 30 execuções por algoritmo, desde que o custo computacional permita.

---

## 7. Métricas de Avaliação

A comparação deve priorizar a qualidade das soluções encontradas para a formulação proposta.

Sempre que possível, reportar:

- melhor valor da função objetivo;
- média dos valores obtidos;
- mediana;
- desvio padrão;
- intervalo interquartil;
- pior valor obtido;
- curva de convergência;
- número de avaliações da função objetivo;
- tempo de execução;
- taxa de soluções viáveis, se aplicável.

Métricas de rede, como vazão, latência, justiça, perda, eficiência espectral ou satisfação de requisitos por slice, devem ser incluídas apenas se fizerem parte da formulação ou da avaliação experimental do paper.

---

## 8. Análise Estatística

A conclusão sobre a melhor meta-heurística deve ser sustentada por evidências quantitativas.

Quando houver múltiplas execuções independentes, recomenda-se aplicar análise estatística apropriada, como:

- teste de Friedman para comparação global entre múltiplos algoritmos;
- pós-teste de Nemenyi, Holm ou Bonferroni quando necessário;
- teste de Wilcoxon pareado para comparações dois a dois;
- teste de Kruskal-Wallis quando a estrutura dos dados justificar comparação não paramétrica independente.

O paper deve evitar afirmar superioridade absoluta de um método com base em apenas uma execução ou em diferenças pequenas sem análise de variabilidade.

Caso testes estatísticos não sejam usados, a limitação deve ser reconhecida e a conclusão deve ser formulada com cautela.

---

## 9. Regras de Escrita e Interpretação

Ao escrever ou revisar o paper, agentes devem seguir estas regras:

- Usar linguagem técnica compatível com redes 5G/O-RAN, network slicing e otimização por meta-heurísticas.
- Manter o foco na otimização dos pesos de alocação dos slices.
- Explicar que PSO, GA, SA e a híbrida procuram soluções candidatas no espaço contínuo dos pesos.
- Diferenciar claramente meta-heurísticas de otimização e schedulers puros.
- Não afirmar que a híbrida é melhor sem sustentação nos resultados experimentais.
- Não remover comparações com RR, BCQI, PF, RSLAQ ou AQPS.
- Não alterar a formulação matemática sem autorização explícita.
- Não introduzir métodos adicionais como se fossem parte do objetivo central do paper.
- Evitar conclusões vagas; a conclusão deve dizer objetivamente qual método apresentou o melhor desempenho segundo os critérios experimentais.

---

## 10. Estrutura Recomendada para a Discussão dos Resultados

A discussão dos resultados deve seguir uma linha argumentativa clara:

1. Apresentar o desempenho dos schedulers puros RR, BCQI e PF.
2. Apresentar o desempenho das meta-heurísticas PSO, GA, SA e híbrida.
3. Comparar as meta-heurísticas entre si com base na função objetivo e nas métricas de rede relevantes.
4. Comparar os resultados obtidos com RSLAQ e, quando aplicável, com AQPS.
5. Discutir convergência, estabilidade e custo computacional.
6. Indicar qual método encontrou as melhores soluções para a formulação adotada.
7. Reconhecer limitações experimentais, se houver.

---

## 11. Conclusão Esperada do Paper

A conclusão do paper deve ser objetiva e diretamente conectada ao objetivo experimental.

Ela deve responder explicitamente:

- qual meta-heurística encontrou as melhores soluções;
- em quais métricas essa superioridade foi observada;
- se o ganho em relação a PSO, GA e SA foi consistente;
- se houve vantagem em relação aos schedulers puros RR, BCQI e PF;
- como os resultados se posicionam em relação ao RSLAQ e às bases do AQPS;
- quais limitações permanecem para trabalhos futuros.

A conclusão não deve ser genérica. Expressões vagas como “os métodos apresentaram bons resultados” devem ser acompanhadas de evidência quantitativa e indicação clara do método com melhor desempenho.

---

## 12. Checklist para Agentes

Antes de finalizar qualquer contribuição para o paper, o agente deve verificar:

- A formulação continua sendo de otimização contínua?
- Os pesos de alocação dos slices continuam sendo as variáveis de decisão?
- PSO, GA, SA e a híbrida foram mantidos como métodos principais?
- RR, BCQI e PF foram mantidos como schedulers puros de comparação?
- RSLAQ e AQPS continuam presentes na narrativa do paper?
- A comparação está centrada na qualidade das soluções encontradas?
- A metodologia informa parâmetros, critérios de parada e número de execuções?
- A análise apresenta média, dispersão e melhor solução quando possível?
- A conclusão aponta objetivamente o método vencedor?
- O texto evita afirmações de superioridade sem suporte experimental?

---

## 13. Restrições para Agentes

Agentes não devem:

- trocar a formulação contínua por formulação discreta;
- trocar os pesos dos slices por outra variável de decisão;
- remover PSO, GA, SA ou a híbrida do conjunto principal;
- substituir RR, BCQI e PF por outros schedulers sem autorização;
- remover RSLAQ ou AQPS da comparação;
- criar resultados numéricos inexistentes;
- inventar parâmetros experimentais se eles não estiverem definidos;
- afirmar significância estatística sem teste apropriado;
- declarar que a híbrida é superior antes de verificar os resultados;
- transformar o artigo em uma proposta de novo scheduler em vez de uma análise de meta-heurísticas para otimização dos pesos.

Quando alguma informação estiver ausente, o agente deve sinalizar a lacuna e propor uma forma de preenchê-la sem alterar o escopo do paper.

---

## 14. Contexto Operacional e Estado Experimental (Sessão 2026-07-07)

Esta seção registra o estado experimental vigente, as mudanças aplicadas e os bugs conhecidos, de forma que agentes futuros herdem o contexto sem precisar rederivá-lo. Ela complementa (não substitui) as seções anteriores; em caso de conflito sobre escopo ou formulação, prevalecem as seções 1-13.

### 14.1 Campanha vigente

- **Run tag**: `20260626_122326`, em `ns-o-ran-gym/results_controlled/heuristics_metaheuristics/20260626_122326/`.
- **Decisão de projeto**: ambiente controlado com **3 seeds (1, 2, 3)** e `RUNS=1`. Não há intenção de expandir para 30 execuções por restrição de tempo de simulação. Agents não devem introduzir 30 seeds por iniciativa própria.
- **Hiperparâmetros vigentes**: `META_ITERATIONS=12`, `META_POPULATION=6`, `META_RANDOM_SEED=2026`, `META_MUTATION_STRENGTH=0.12`, `META_INTRA_ALGO=PF`. Cada par (cenário, seed) executa GA (72 evals), PSO (72), SA (72, orçamento equalizado a `iterations×population`) e híbrida (84 = `iterations×(population+1)`, o +1 é o refinamento local SA por iteração), totalizando **300 avaliações da função objetivo por par**. O orçamento de avaliações do SA foi equalizado ao do GA/PSO (72) para uma comparação justa sob igual custo computacional; anteriormente o SA fazia apenas 12 evals (busca por trajetória única), o que era uma comparação injusta.
- **Fases**: Phase 1 (baselines) está 210/211 OK; Phase 2 (meta-heurísticas) em execução; Phase 3 (meta-eval) e Phase 4 (RSLAQ DDQN paper-faithful) agendadas na sequência via `resume_campaign.sh`.
- **AQPS na campanha**: o baseline AQPS está habilitado como `slice_aqps` nos scripts de baselines e aparece no manifesto `heuristics_ns3/results_rslaq_network_only/batch_manifest.csv`. No estado verificado desta sessão, há 15 execuções planejadas de `slice_aqps`: 14 `ok` com `summary.csv` e 1 `run_failed` em `congestion`, `seed=1`, `run=1` (`ns3_run_failed`).

### 14.2 Mudanças de código aplicadas nesta sessão (não descrever como bugs novos)

Estas alterações já estão aplicadas e devem ser tratadas como o estado corrente:

1. **Checkpoint de evals em `run_rslaq_metaheuristics.py`**: cada avaliação grava um sidecar `candidate.json` no diretório do eval. Ao reiniciar, o closure `evaluate` desserializa e pula o ns-3 quando os pesos pedidos batem com o cache (tolerância 1e-9). A persistência do `metaheuristic_results_*.csv` e do `best_candidate_*.json` é incremental (após cada método). O `import csv` foi adicionado (bug bloqueante que impedia a Phase 2 de salvar resultados).
2. **Calibração da penalidade URLLC em `scoring.py`**: o divisor `(delay - 10)/200` foi trocado por `/20`. Com o divisor antigo, a penalidade era irrisória na faixa operacional (14,864 ms → −0,6 pts), permitindo que o "ótimo" violasse o SLA de 10 ms. Agora: 14,864 ms → −6,08 pts; saturação em 30 ms (−25 pts). O scoring usa `delay_ms_mean` (ponderado por pacote); os percentis `delay_ms_p95/p99` **não são usados** na função objetivo.
3. **Re-score do cache**: o script `examples/rescore_cache.py` recalcula scores dos `summary.csv` em cache quando o `scoring.py` muda, sem re-rodar o ns-3. Os 150 evals em cache foram re-scored após a mudança acima (66 mudaram, delta médio −19,4 pts).
4. **Hiperparâmetros**: `META_ITERATIONS` 4→12 em `run_all_scenarios.sh` e `resume_campaign.sh`. O cache é reaproveitado porque o RNG é seeded e os pesos dos primeiros evals são deterministicamente reproduzíveis.

### 14.3 Bugs e limitações conhecidas (documentar no paper, não corrigir por iniciativa própria)

- **Percentis de delay amostrados por janela, não por pacote**: no `rslaq-sim.cc`, `delay_ms_p95/p99` são calculados sobre médias por janela de 10 ms, o que produz inconsistências do tipo `delay_ms_mean > delay_ms_p95` em ~20% das linhas. A correção exigiria modificar o `StatsCallback` no C++ e re-rodar toda a campanha (Phase 1+2). **Decisão: adiar e documentar como limitação** (o scoring usa `delay_ms_mean`, então a otimização não é afetada).
- **SA com escala de aceitação ad-hoc**: o orçamento do SA foi equalizado a 72 evals (= GA/PSO), resolvendo a inequidade anterior (12 evals). A escala da aceitação de Metropolis (`temperature * 20.0`) permanece uma compensação ad-hoc para a escala da função objetivo.
- **PSO/Híbrida com renormalização pós-passo**: a projeção para o simplexo após cada atualização de velocidade destrói a semântica canônica do vetor velocidade. Funciona empiricamente mas não é PSO estritamente canônico.
- **Hiperparâmetros ainda modestos**: `population=6, iterations=12` está acima do regime "piloto" anterior mas abaixo do ideal para meta-heurísticas. Aumentar a população invalidaria o cache existente.

### 14.4 Achados da revisão crítica (devem orientar a redação, não serem revertidos)

Uma revisão crítica de pesquisa identificou pontos que devem ser refletidos na redação do paper:

- **Em cenários não-saturados (low_traffic, normal, stressed)**, os dados mostram que o scheduler é praticamente irrelevante: os 14 modos colapsam para throughput idênticos determinados pelo seed. Só `congestion` apresenta separação real entre modos. O paper deve declarar isso como **resultado negativo honesto**, não esconder.
- **A híbrida perde para o PSO puro em 2 dos 3 cenários** relatados no draft atual. A contribuição não deve ser posicionada como "híbrida vencedora" sem evidência robusta. Posicionamento recomendado: híbrida como avaliação comparativa, com foco metodológico em **META_RISK_ELASTIC** (blending prior×online) e **AQPS** (budgets inteiros com garantia mínima) como baselines mais sólidas.
- **N=3 seeds é insuficiente para testes estatísticos formais** (Wilcoxon/Friedman exigem n≥5). O paper deve reportar média±desvio e melhor/mediana, **não declarar significância**, e reconhecer a limitação explicitamente, remetendo significância formal a trabalho futuro.
- **RSLAQ DDQN (Phase 4) é o baseline DRL do paper** e deve entrar na comparação principal quando disponível. Ele responde à pergunta "por que meta-heurísticas e não DRL?" que um revisor fará.

### 14.5 Diretrizes operacionais para agents

- **Não commitar** `results_controlled/`, `*.pid`, logs de campanha (`resume_campaign.log`, `.meta_*.log`, `run_*_parallel*.log`). O `.gitignore` da raiz e o `ns-o-ran-gym/.gitignore` já os protegem.
- **Ao mudar `scoring.py`**, executar `examples/rescore_cache.py` para atualizar os sidecars em cache antes de relançar a Phase 2.
- **Ao mudar hiperparâmetros que afetem o RNG** (population, random_seed), o cache é invalidado e tudo precisa re-rodar do zero. Mudar apenas `iterations` preserva o cache.
- **Para parar a campanha**: SIGTERM ao PID em `resume_campaign.pid` pode não propagar aos filhos; usar `pkill -KILL -f "ns3.46-rslaq-sim-default|run_rslaq_metaheuristics.py|run_all_scenarios.sh"` se necessário. O cache (sidecars já escritos) sobrevive a SIGKILL.
- **Relevância**: o SOTA em RAN slicing (2024-2025) é dominado por DRL (DDPG, PPO, federated/hierarchical RL). O paper deve articular explicitamente por que meta-heurísticas offline (auditáveis, estáveis, sem treinamento) são a escolha certa — caso contrário, um revisor questionará por que não DRL.

### 14.6 Dashboard de monitoramento

Existe um dashboard Streamlit read-only para acompanhar a campanha em tempo real:

- **Arquivo**: `ns-o-ran-gym/examples/dashboard.py`.
- **Como rodar**: usar o venv dedicado em `ns-o-ran-gym/.venv-dashboard/` (PEP 668 bloqueia o python3 do sistema):
  ```
  cd ns-o-ran-gym
  .venv-dashboard/bin/streamlit run examples/dashboard.py
  ```
  Abre em `http://localhost:8501`, com auto-refresh a cada 15s.
- **O que mostra**: % global de conclusão e ETA (Seção A); heatmap cenário×seed e tabela de progresso por método (B); curvas de convergência, boxplots e ranking comparativo de GA/PSO/SA/híbrida por par selecionado (C); melhor candidato por cenário com pesos ótimos (D); ticker de atividade recente e detecção de erros nos logs (E).
- **Fonte de dados**: lê apenas sidecars `candidate.json`, `best_candidate_*.json`, `metaheuristic_results_*.csv` e o `batch_manifest.csv` da Phase 1. **Nunca modifica a campanha** (read-only).
- **Contagens embutidas** (iter=12, pop=6): GA=72, PSO=72, SA=12, híbrida=84 → 240 evals/par, 3600 global. Se hiperparâmetros mudarem, atualizar `EVALS_PER_METHOD` no `dashboard.py`.
- **Limitação conhecida**: o `streamlit-autorefresh` opcional não está instalado; o app usa fallback via `<meta http-equiv="refresh">` (recarrega a página no browser a cada 15s). Para auto-refresh nativo (sem reload visível), instale `streamlit-autorefresh` no venv-dashboard.
