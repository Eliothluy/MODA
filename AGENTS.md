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

A comparação com RSLAQ deve ser mantida na análise experimental ou na discussão dos resultados, conforme a estrutura atual do paper. AQPS deve continuar sendo usado como base conceitual, metodológica ou comparativa, conforme definido na pesquisa.

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
