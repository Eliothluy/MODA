# Defesa da Adaptacao da Recompensa RSLAQ para Treinamento DDQN

## Contexto

Este trabalho implementa o RSLAQ, proposto no artigo _RSLAQ: A Robust SLA-driven 6G O-RAN QoS xApp Using Deep Reinforcement Learning_, em um ambiente online baseado em ns-3/5G-LENA e O-RAN Gym. A funcao de recompensa segue a formulacao do artigo, especialmente:

- Eq. 8: recompensa de otimizacao ponderada por slice;
- Eq. 12: penalizacao por violacao de SLA;
- Eq. 13-15: condicoes de outage e soft SLA;
- Eq. 16-18: termos de otimizacao para eMBB, URLLC e MTC.

Durante a validacao experimental, observou-se que os episodios de DDQN eram interrompidos sistematicamente no quinto passo de controle. A causa nao era o fim da simulacao ns-3 nem o horizonte periodico do RSLAQ, mas a ativacao imediata da condicao terminal da Eq. 12 apos a janela de confirmacao de outage.

## Problema Observado

O ambiente usava:

```text
warmup_steps = 5
consecutive_outage_steps = 5
periodMs = 10 ms
ntsr = 100
```

Assim, quando o slice eMBB permanecia abaixo do SLA minimo durante os primeiros passos, o estado de outage era confirmado exatamente no passo 5. A funcao de recompensa retornava `terminated=True`, encerrando o episodio antes que o agente atingisse o horizonte `ntsr=100` descrito no algoritmo do RSLAQ.

Esse comportamento gera tres problemas metodologicos:

1. O replay buffer do DDQN recebe trajetorias muito curtas e pouco diversas.
2. O agente aprende majoritariamente a partir de estados transitorios de inicializacao do ns-3.
3. O treinamento deixa de seguir o reset periodico de `ntsr` passos usado no roteiro do artigo.

Em termos praticos, o agente nao observa dinamicas de recuperacao apos uma violacao de SLA. Isso e particularmente problematico para redes 5G/O-RAN, onde um xApp real nao deixa de atuar apos uma violacao instantanea; ele continua ajustando recursos para restaurar a QoS.

## Adaptacao Proposta

A adaptacao separa dois conceitos que estavam acoplados na implementacao:

- penalizar uma violacao de SLA;
- encerrar imediatamente o episodio.

A recompensa permanece fiel a Eq. 12:

```text
r_t = -sum(phi_j * omega_j), se houver outage
r_t = 0, se houver soft SLA violation
r_t = r_opt, caso contrario
```

A diferenca esta apenas na dinamica de treinamento do DDQN:

```text
done_t = True somente no reset periodico ntsr
```

em vez de:

```text
done_t = True em qualquer violacao de SLA
```

Na implementacao, isso foi introduzido pela opcao:

```text
terminate_on_sla_violation = False
```

para o treinamento DDQN. A opcao antiga continua disponivel com:

```text
--terminate-on-sla-violation
```

## Justificativa Para um Paper IEEE

A defesa central e que a adaptacao preserva a semantica da recompensa RSLAQ, mas evita que transientes iniciais do simulador dominem o processo de aprendizado.

Uma forma adequada de descrever no artigo e:

> To avoid premature episode truncation caused by simulator warm-up transients, we decouple SLA-violation penalization from episode termination during DDQN training. The reward assigned to SLA outage states remains identical to the RSLAQ formulation, i.e., the weighted negative penalty of Eq. 12. However, the environment does not force an immediate reset after such violation; instead, the episode follows the periodic reset horizon `ntsr`, as described in Algorithm 1. This preserves the SLA-driven learning signal while allowing the agent to collect longer state-action trajectories and populate the replay buffer with recovery dynamics.

Essa decisao e defensavel porque:

- a penalidade por outage nao foi suavizada nem removida;
- a funcao objetivo continua SLA-driven;
- o agente continua recebendo sinal negativo quando viola SLA;
- o episodio passa a representar uma janela operacional continua, mais proxima de um xApp em execucao;
- o reset periodico `ntsr` fica alinhado com o algoritmo de treinamento do RSLAQ;
- o DDQN passa a observar tanto falha quanto recuperacao, melhorando a qualidade das transicoes no replay buffer.

## Relacao Com o Artigo Original

No artigo, a Eq. 12 define a recompensa para estados de violacao. Em uma formulacao MDP abstrata, esses estados podem ser modelados como terminais. Entretanto, em uma implementacao online com ns-3, os primeiros passos de cada episodio incluem efeitos de inicializacao, attach/RRC, ramp-up de aplicacao, preenchimento de buffers e estabilizacao do escalonador MAC.

Portanto, tratar toda violacao inicial como estado absorvente pode introduzir um vies experimental que nao reflete a operacao continua de um xApp O-RAN.

A adaptacao proposta nao altera as equacoes de recompensa. Ela altera apenas a politica de reset durante o treinamento:

- a recompensa continua seguindo a Eq. 12;
- os indicadores de outage e soft violation continuam registrados;
- a avaliacao pode reportar explicitamente a taxa de violacao de SLA;
- o episodio de treinamento passa a seguir `ntsr`, como no algoritmo do artigo.

## Impacto Esperado no Treinamento

Com episodios limitados a 5 passos, o DDQN recebe poucas amostras por episodio e tende a aprender a partir de transicoes quase identicas, dominadas por estados iniciais ruins. Ao manter o episodio ate `ntsr`, o replay buffer passa a conter:

- estados antes da violacao;
- estados durante a violacao;
- estados apos a acao corretiva;
- transicoes de recuperacao;
- efeitos retardados da realocacao de PRBs.

Isso e importante porque a alocacao de recursos em 5G possui atraso entre acao e efeito observado, especialmente quando ha filas, HARQ, mudancas de CQI e competicao entre slices.

## Como Reportar na Secao Experimental

Recomenda-se reportar:

- reward medio por episodio;
- taxa de outage por slice;
- taxa de soft SLA violation;
- numero medio de passos por episodio;
- throughput medio por slice;
- PLR/PDR por slice;
- comparacao com a variante terminal original.

Uma frase recomendada para a secao experimental:

> During training, SLA violations are treated as non-absorbing penalized states. This prevents the DDQN replay buffer from being dominated by short warm-up trajectories. During evaluation, SLA violations are still explicitly measured and reported per slice, ensuring that the non-terminal training treatment does not hide QoS failures.

## Ameacas a Validade

A principal ameaca e que a variante nao terminal pode parecer menos estrita do que a formulacao terminal original. Para mitigar isso, a avaliacao deve sempre reportar metricas independentes de SLA, e nao apenas reward acumulado.

Tambem e recomendavel comparar:

- DDQN com terminacao por SLA;
- DDQN com penalidade nao terminal;
- baselines ns-3 puros, como RR, PF e BCQI.

Desse modo, a adaptacao e apresentada como uma escolha de estabilidade de treinamento, nao como relaxamento dos requisitos de QoS.

## Resumo da Defesa

A mudanca e metodologicamente defensavel porque preserva a recompensa do RSLAQ, mas ajusta a mecanica de episodios para uma implementacao online realista com ns-3. A penalidade de SLA continua presente e forte; o que muda e que o agente nao e impedido de aprender trajetorias de recuperacao. Isso aproxima o treinamento de um xApp O-RAN em operacao continua e restaura o horizonte `ntsr` usado no algoritmo do artigo.
