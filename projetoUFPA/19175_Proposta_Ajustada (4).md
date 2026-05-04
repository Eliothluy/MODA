

Prezada Comissão Avaliadora do Programa OpenRAN@Brasil,

Agradecemos pelo valioso retorno e pelas construtivas sugestões recebidas durante a
avaliação da nossa proposta intitulada “GreenRAN: Open RAN Sustentável para o Agro e
Campi Inteligentes”. Consideramos os comentários extremamente pertinentes e
fundamentais para aprimorar a clareza, o escopo e o impacto técnico da proposta.

Temos o prazer de submeter a versão revisada do nosso projeto, na qual atendemos
cuidadosamente a todas as sugestões dos revisores. Para facilitar a análise, todo o texto que
foi alterado ou adicionado em resposta aos seus comentários específicos está destacado em
azul no documento a posteriori.

Acreditamos que estas alterações reforçam significativamente a originalidade, a viabilidade
técnica e o alinhamento estratégico da proposta GreenRAN com os objetivos do programa
OpenRAN@Brasil, particularmente no que tange ao desenvolvimento de soluções
inovadoras, eficientes e aplicáveis aos desafios de conectividade e sustentabilidade do país.

Reiteramos nosso entusiasmo com a oportunidade de contribuir para o ecossistema de
Open RAN nacional e estamos à disposição para quaisquer esclarecimentos adicionais.

## Atenciosamente,

## Prof. Eduardo Coelho Cerqueira
Coordenador Geral da Proposta - UFPA
## 04/01/2026







Carta de Resposta aos Revisores

Respostas aos comentários gerais sobre a proposta
Q1 - O projeto lista casos de uso como entregáveis, mas o edital exige aplicações: quais
aplicações concretas serão geradas a partir dos casos de uso propostos? Descreva cada
aplicação, suas funcionalidades principais, requisitos de integração com a infraestrutura
Open RAN e os critérios de validação que serão usados para comprovar seu funcionamento.
R1: Obrigado pelos comentários. Enfatizamos no texto da proposta reformulada as duas aplicações
a serem entregues, denominadas: App1-Vigilância e App2-Monitoramento. A primeira aplicação
será responsável por transformar o campus da UFPA-Belém em um “Living Lab” para
monitoramento da segurança pública utilizando métodos de IA para detecção de casos de
violência no campus, e problemas relacionados, através da imagem de câmeras. Na aplicação
App2-Monitoramento, coletaremos informações de sensores IoT espalhados pelo campus,
incluindo sensores localizados no solo em regiões de vegetação, através da  Rede-5G-Green  para
monitorarmos em tempo real as métricas obtidas e identificarmos dados de interesse que possam
indicar situações de risco ambiental e mudanças bruscas nas características do solo. Adicionamos
na proposta as descrições das funcionalidades principais dessas aplicações, requisitos de
integração com a infraestrutura e os critérios de validação na seção de casos de uso, conforme
requisitado. As alterações realizadas no texto estão detalhadas abaixo.

Seção 6.2: Na vertical de “Cidades e Campi Inteligentes”, será desenvolvida uma aplicação
final principal denominada App1-Vigilância: um sistema de segurança pública baseado em
monitoramento por vídeo de alta definição com análise de inteligência artificial em tempo
real para o campus universitário. Para a vertical “Agro 4.0 e Conectividade Rural”, a aplicação
final central é denominada App2-Monitoramento, e consiste no monitoramento  ambiental
e do solo mediante dados de sensores para análise em tempo real, contando com rede
massiva de sensores para análise.

Seção 6.3: Esta estratégia habilita o desenvolvimento na vigência deste projeto de 2
aplicações inovadoras voltadas para  dois casos de uso distintos:  a aplicação App1-Vigilância
voltada para a vigilância do campus por vídeo e IA (eMBB), e a aplicação
App2-Monitoramento voltada para o monitoramento ambiental e do solo utilizando uma
rede de sensores no campus (mMTC).  Em todos casos, será exercida atenção especial à
segurança cibernética, desde o projeto das aplicações até suas validações.
## ...
Na aplicação App1-Vigilância, o campus da UFPA-Belém será transformado em um “Living
Lab” para monitoramento da segurança pública, utilizando a Rede-5G-Green otimizada pela
Solução-ORAN-Green para redução do consumo de energia. O tráfego das câmeras de alta

definição, instaladas em áreas críticas do campus, representará uma alta carga para a
Rede-5G-Green. As informações de todas as câmeras serão transmitidas via 5G. As faces de
pessoas serão anonimizadas usando IA para garantir a privacidade e preservação da
identidade de quem circula no campus. A aplicação App1-Vigilância utilizará IA para
detecção de casos de violência no campus, como agressões e assaltos. Utilizaremos modelos
de IA e banco de dados disponíveis na literatura para aperfeiçoamento do modelo que será
utilizado no campus, detectando as poses e movimentações de interesse que possuem alta
probabilidade de estarem associadas a atos violentos. No caso de suspeita de ato violento, a
aplicação retirará a anonimização da face da suspeita de envolvidos em atos violentos e
emitirá um alerta para o responsável da segurança para avaliação da situação, tornando o
sistema de monitoramento mais efetivo. Como requisito de integração da aplicação com a
infraestrutura Open RAN temos a necessidade de garantia de alta taxas de dados, dado que
cada câmera 4K com H.256 requer em média 25 Mbps, e uma garantia de latência abaixo de
100 ms da rede para garantir que atos violentos sejam identificados rapidamente e a equipe
de segurança do campus obtenha a informação no menor tempo possível. A aplicação será
validada com a encenação de atos violentos pelo campus que deverão ser detectados assim
como o monitoramento de métricas de rede para garantia dos requisitos de taxa de dados e
latência.
Na aplicação App2-Monitoramento voltada para os  casos de uso “Agro” e “Campus
inteligente”, as informações coletadas através de sensores IoT espalhados pelo campus,
incluindo sensores localizados no solo em regiões de vegetação, serão transmitidas pela
Rede-5G-Green para avaliarmos, em condições reais, tanto a conectividade 5G da
Solução-ORAN-Green quanto o monitoramento das métricas obtidas pelos sensores em
tempo real.
## ...
Como requisitos para eficaz  integração com a infraestrutura Open RAN, temos a
necessidade de reduzido consumo de potência dos nós sensores e alcance adequado, além
da otimização da taxa de transmissão às necessidades de cada sensor. Todos esses requisitos
devem ser alcançados com baixo custo, para viabilizar aumento de escala em experimentos
com mMTC. Algumas das pesquisas possíveis são pautadas em experimentos para controle
de parâmetros da rede que diminuam as probabilidades de erro de transmissão de pacotes,
como por exemplo a fixação de valores de MCS baixos, e o ajuste dinâmico de recursos
utilizados pelo slice de mMTC dadas características de coleta intermitente da maioria dos
sensores. A aplicação será validada através do grau de sucesso no estabelecimento de
conectividade com diversos sensores distintos e do monitoramento de parâmetros como a
taxa de perda de pacotes nas transmissões efetuadas por sensores, assim como o consumo
de energia e a utilização da rede pelos sensores nos tempos programados.



Q2 - De que maneira a combinação entre a Solução-ORAN-Green e o uso de ISAC pode
tornar o “Living Lab” da UFPA-Belém um ambiente pioneiro para experimentos em
segurança pública e monitoramento ambiental, conciliando eficiência energética e análise
avançada de dados?
R2: Para alinhar com sugestões dos revisores, retiramos a funcionalidade de ISAC com intuito de
aumentar a garantia dos entregáveis dentro do tempo de execução do projeto. As aplicações de
terceiros poderão usar a Solução-ORAN-Green em distintos níveis, tais como: 1) o acesso aos
dados para experimentos convenientemente realizados em suas premissas, ou 2) execução de
Apps que usem  apenas a infraestrutura de hardware, ou 3) Apps que usem também software
desenvolvido no projeto (por exemplo: Agentic-AI-Green, xApp1-RANSlicer, xApp2-EnergySaver,
rApp-ResourceOptimizer).

Q3 - Como a combinação de drones, sensores IoT e soluções híbridas de conectividade (5G,
FWA e satélite) pode contribuir para validar a robustez da Rede-5G-Green e apoiar a
expansão de aplicações agrícolas inteligentes em larga escala? Como será essa cobertura
tendo em vista que no plano de trabalho o projeto planeja trabalhar com áreas cujo testbed
não prevê cobertura (e.g. UFRA e UFPA Castanhal)?
R3: Com as mudanças das aplicações e casos de usos da proposta recomendadas pelos revisores,
não utilizaremos mais drones nas nossas aplicações. Mas com relação à utilização de sensores IoT
e soluções híbridas de conectividade, as soluções puramente baseadas em em dispositivos 5G
enfrentam desafios relacionados ao custo e até mesmo a inexistência de dispositivos e sensores
com a conectividade 5G embutida. Dentro desse contexto a Rede-5G-Green é também uma rede
de integração com outras tecnologias de conectividade, seja através da conexão via RAN ou núcleo
da rede.  Dessa forma, aplicações que necessitam de alto desempenho com relação à taxa de
dados utilizarão a rede 5G de forma direta através de módulos 5G móveis ou FWA, enquanto que
dispositivos que precisam de maior alcance e possuem opções de baixo custo utilizando
tecnologias como LoRA, serão conectados à rede Open RAN 5G através de gateways. Dessa forma,
garantimos uma solução de baixo custo e que atende os requisitos das aplicações, enquanto
concentramos o controle da rede na Rede-5G-Green, facilitando a otimização de recursos de
acordo com as necessidades de cada aplicação. As alterações no texto estão detalhadas abaixo em
azul.

A estrutura de rede e cobertura da mesma estarão limitadas à UFPA campus Belém, e por isso
esclarecemos no texto que a colaboração com a UFRA e UFPA Castanhal ocorrerão por meio de
desenvolvimento locais em cada instituição, com atividades de integração à rede 5G envolvendo as
diferentes instituições em períodos selecionados para verificação de efetividade das soluções
propostas. Os especialistas de domínio nas instituições parceiras do projeto irão contribuir mesmo
sem haver rede 5G instalada em suas premissas. A UFPA Belém também estará à disposição das
instituições parceiras para realização de testes de hipóteses usando a rede 5G. É importante
enfatizar que o campus UFPA Belém possui extensa zona de vegetação e floresta ao longo do
campus, permitindo a implementação de sensores ambientais e do solo como exigidos pela nossa
proposta.


Seção 6.3: Para habilitar esta aplicação,  ampliaremos o ecossistema de dispositivos 5G
comumente utilizados com o uso de equipamentos RedCap, a possibilidade de transmissão
via satélite, por meio de soluções como da Skylo, e a utilização de gateways IoT
BR5G-Gateways integrados com pontos de acesso 5G, explorando soluções que aumentem o
número de dispositivos conectados e que sejam adequados para ambientes rurais. Dessa
forma, quando sensores ou dispositivos IoT não dispuserem de conectividade 5G nativa,
utilizaremos dispositivos 5G FWA com WiFi, ou desenvolveremos um “gateway” dedicado
(BR5G-Gateways).

Plano de trabalho 3 (PT3): Na aplicação App2-Monitoramento, sensores voltados ao
controle e análise do solo para agricultura serão utilizados para fornecer informações-chave
para inferência de qualidade do solo. Serão exploradas as comunicações com sensores de
medição de nutrientes do solo, sensor de umidade, sensor de temperatura e sensor de
condutividade elétrica. Sensores voltados ao monitoramento ambiental no campus
inteligente serão adotados para fornecerem informações em tempo real sobre a qualidade
do ar, ocorrência e intensidade de chuva, níveis de radiação solar e temperatura. A partir da
consolidação de tais indicadores, a aplicação poderá gerar relatórios, alertas e identificar
anomalias.

Q4 - A proposta abrange quatro casos de uso distintos mais a complexidade do 5G/Open
RAN em apenas 24 meses. Como vocês analisam os riscos do projeto e qual o plano de
mitigação para tal? qual é a interdependência entre esses quatro casos? Se o Caso 1 atrasar,
ele bloqueia os outros? E, mais importante: Qual destes quatro é o 'carro-chefe' que será
priorizado se o cronograma apertar, e qual será o primeiro a ser descartado para salvar o
projeto?
R4: Conforme orientações recebidas pelos revisores, nós optamos por reduzir pela metade o
número de aplicações a serem entregues, com o intuito de diminuir os riscos de execução do
projeto ao longo do tempo fornecido. Com isso, agora temos a entrega de duas aplicações e sem
interdependência, como forma a minimizar os riscos do projeto e assegurar a conclusão do mesmo
dentro do prazo de 24 meses.  As atividades de otimização da rede previstas no Plano de Trabalho
1  (PT1) apesar de essenciais para a garantia do bom funcionamento das aplicações, não
bloqueiam completamente as demais atividades.  Realizando-se uma gerência do projeto de forma
atenciosa e eficaz, as 3 frentes conseguirão executar seus trabalhos no prazo e as entregas
prometidas serão realizadas no prazo.


Q5 - De que forma o caso de uso na UFRA (que está desacoplado da arquitetura
homologada) será integrado ou adaptado ao ambiente do hospedeiro?

R5: Com a redesignação das aplicações do projeto não teremos mais o caso de uso que consistiria
na obtenção de imagens de gado bovino e bubalino na UFRA. Mas para fins de registro, as
atividades previstas para a UFRA e algumas outras parceiras não exigia a rede Open RAN 5G.


Q6 - Qual é o papel das tecnologias quânticas no projeto e como elas serão incorporadas de
maneira prática (principalmente pq não há previsão de compra de equipamentos)
R6: Seguindo a orientação dos revisores, a nova proposta do projeto retirou os estudos e entregas
relacionadas a tecnologias quânticas, alinhada com a sugestão para diminuir as chances de
eventuais problemas com os entregáveis dentro do tempo de execução do projeto.


Q7 - Como o projeto estruturará a gestão e a coordenação entre equipes responsáveis por
entregas distintas e interdependentes, assegurando integração contínua, alinhamento de
cronograma e mitigação de riscos técnicos durante o desenvolvimento?
R7: A gestão e a coordenação do projeto foram estruturadas para lidar com entregas distintas,
porém fortemente interdependentes, como é o caso de xApps, rApps, Agentic AI, infraestrutura
Open RAN e aplicações App1-Vigilância e App2-Monitoramento, conforme detalhado no PT4
(Governança) e na organização transversal dos PT1, PT2 e PT3.
O projeto assegura gestão e coordenação eficazes baseado em: (1) Adota governança em
camadas, com papéis claros; (2) Estrutura o desenvolvimento em pacotes de trabalho
interdependentes, porém desacoplados; (3) Usa interfaces Open RAN padronizadas como eixo de
integração contínua; (4) Planeja o cronograma com base em dependências técnicas reais; (5)
Implementa gestão ativa de riscos, com prototipação e validação incremental. Os grupos
responsáveis pelos diferentes entregáveis do projeto estão listados a seguir:
Domínio Responsáveis principais
Open RAN (CU/DU, E2, KPM) UFPA
xApps (Near-RT RIC) UFPA / UFRGS
rApps (Non-RT RIC) UFPA / UFRGS
Agentic-AI e interface UNICAMP
Aplicações eMBB
(App1-Vigilância)
## UFPA / UEPA
Aplicações mMTC
(App2-Monitoramento)
## UFPA / UNIFESSPA




Respostas ao Revisor 1
A proposta GreenRAN visa implantar a Solução‑ORAN‑Green — uma rede 5G Open RAN no campus
da UFPA com xApps (slicing, economia de energia, ISAC), rApps (otimização, monitoramento
ambiental) e um Agentic‑AI para orquestração — e validar quatro casos de uso: estimativa de peso
de bovinos/bubalinos por visão; rede massiva de sensores para solo; vigilância por vídeo com IA;
monitoramento ambiental de baixo consumo, em um horizonte de dois anos.
R0: Agradecemos ao revisor pelas observações. Alterações na proposta foram realizadas para
atender aos comentários e sugestões dos revisores.


Q1: Pontos de atenção incluem segurança e integridade das interfaces Open RAN (incluindo a
necessidade de detalhar QKD ou alternativas), clareza sobre o uso e a disponibilidade de SDRs no
testbed, garantias de interoperabilidade entre RU/CU/DU/RICs, medição confiável da economia de
energia, e definição clara dos mecanismos de conectividade entre UFRA/UNIFESSPA e o POP‑PA (RNP,
links dedicados, NTN ou data‑mules) para assegurar a coleta de dados em campo. O consórcio é
sólido e multidisciplinar — liderado pela UFPA e com UNICAMP, UFRA, UNIFESSPA, UEPA, UFRGS,
Embrapa Amazônia Oriental e IT Aveiro — oferecendo expertise em RAN, IA, agronegócio, segurança
cibernética e infraestrutura de experimentação, o que fortalece a viabilidade técnica e a capacidade
de entregar, ao final de 24 meses, os xApps/rApps integrados, o Agentic‑AI funcional e relatórios de
validação e desempenho dos quatro casos de uso.
R1: Agradecemos ao revisor pelas observações, que contribuíram significativamente para o
aprimoramento da clareza técnica da proposta.

Quanto ao uso de tecnologias quânticas (QKD), esclarecemos que para melhor alinhar a proposta
com as sugestões dos revisores, a abordagem com QKD foi retirada do escopo da proposta
ajustada. Desta forma, o projeto passa a concentrar seus esforços de pesquisa avançada para
aumentar os níveis de segurança em pontos chaves da arquitetura Open RAN, com foco no
desenvolvimento de mecanismos de defesa contra ataques de evasão e comportamentos
adversariais de modelos de ML nas xApps que operam no Near-RT RIC, incluindo detecção de
padrões anômalos. Essa abordagem mantém o caráter inovador da proposta, ao mesmo tempo
em que permanece plenamente aderente ao ecossistema Open RAN.

A interoperabilidade entre RU, DU, CU e RICs será garantida pelo uso de stacks Open Source
consolidadas, bem como pela implementação de extensões nas CU/DU para habilitar a coleta de
métricas e o controle via interface E2, conforme descrito nas atividades E1.1 e E1.2 do plano de
trabalho. Os trechos alterados na proposta estão detalhados abaixo em azul. Com relação à
disponibilidade de SDRs, no núcleo de antenas indoor localizado no PCT Guamá na UFPA Belém,
temos a disponibilidade de diferentes dispositivos SDR que permitem testes utilizando softwares
open-source para a RAN tanto funcionando como a estação de rádio base e também como UEs. A
utilização desses SDRs para ambas as funções já é uma expertise do grupo que já faz o uso deles
em pesquisas relacionadas a redes 5G e incluímos como contraproposta da instituição UFPA
campus Belém.


Seção 6.2: Do ponto de vista prático, softwares de código aberto, como o OpenAirInterface,
normalmente implementam as funções de alocação de PRB e controle de potência de forma estática.
Portanto, parte do desenvolvimento deste projeto consistirá em habilitar a definição dinâmica da
quantidade de recursos para cada slice de RAN e a seleção do algoritmo de controle de potência,
permitindo que esses valores sejam configurados via interface E2 da arquitetura Open RAN. Dessa
forma, as nossas alterações nas funções da RAN denominadas RAN-CodeUpdates serão
disponibilizadas publicamente.
## ...
O mesmo princípio aplica-se às funções de ligar/desligar células e “layers” de forma inteligente, e
também a coleta de métricas de KPM, que, embora estejam naturalmente disponíveis nas diferentes
camadas da stack 5G (como PHY e MAC), não dispõem de uma interface para sua coleta via E2
completamente implementadas, o que impediria sua utilização por xApps e rApps. Dessa forma, um
pilar fundamental da solução proposta será avançar o estado da arte dos softwares de código aberto
(SANTOS, 2025), o que chamamos de RAN-CodeUpdates,  que implementam a CU/DU, habilitando a
coleta de informações e o controle dinâmico das funções determinadas (ELYASI, 2025).

Q2: Pontos negativos incluem a falta de transparência em relação ao uso de QKD e a possibilidade de
disseminação dos resultados em jornais e conferências, considerando que foram alocados recursos
para viagens em congressos.
R2: Conforme explicado anteriormente, a abordagem usando QKD foi retirada do escopo da
proposta ajustada. E quanto à disseminação dos resultados, esclarecemos que os recursos
destinados a viagens têm como objetivo exclusivamente a divulgação científica e técnica dos
resultados efetivamente obtidos no projeto, em conferências e eventos alinhados ao escopo do
projeto e às áreas de Open RAN, redes móveis, IA aplicada e sustentabilidade. A produção de
artigos científicos, “white papers” e apresentações técnicas constitui, inclusive, um entregável
formal do projeto (E4.1), conforme estabelecido no plano de trabalho e em consonância com as
diretrizes do edital.


Respostas ao Revisor 2
A proposta apresenta méritos técnicos, mas enfrenta desafios significativos de viabilidade e
planejamento orçamentário. Do ponto de vista do escopo, o projeto mostra-se excessivamente
ambicioso para o prazo de 24 meses; a tentativa de cobrir simultaneamente 5G Open RAN, Visão
Computacional e quatro casos de uso distintos gera risco de dispersão e não entrega.
R0: Agradecemos ao revisor pelas observações. Conforme orientações recebidas pelos revisores,
nós optamos por diminuir o número de aplicações e casos de uso da proposta com o intuito de
diminuir os riscos de execução do projeto ao longo do tempo fornecido. Com isso, agora temos a
entrega de duas aplicações e sem interdependências críticas, como forma a minimizar os riscos do
projeto e assegurar a conclusão do mesmo dentro do prazo de 24 meses.  As aplicações podem ser
executadas de forma independentes. As atividades de otimização da rede previstas no PT1 apesar

de essenciais para garantia do bom funcionamento das aplicações, não impedem a implementação
e testes isolados de cada uma das aplicações, dado que basta que a Rede-5G-Green forneça a
conectividade para que testes iniciais sejam realizados com cada aplicação.  Dessa forma, as 3
frentes conseguirão executar seus trabalhos de forma independente.

Q1: Especificamente no Caso de Uso C3 (Vigilância), há preocupações latentes quanto à ética do
monitoramento contínuo e à segurança da informação dos dados coletados que demandam maior
atenção.
R1:  Agradecemos ao revisor pela observação. Dentro da reorganização da proposta, a aplicação
de vigilância agora é chamada App1-Vigilância e na seção onde explicamos a aplicação
adicionamos detalhes sobre a anonimização das faces das pessoas presentes nas filmagens obtidas
pelas câmeras, de forma que todos os datasets gerados no âmbito da aplicação App1-Vigilância
serão previamente censurados, ofuscados e anonimizados, de modo a impedir a identificação de
pessoas, placas de veículos ou quaisquer outros elementos sensíveis. Desta forma, serão
consideradas apenas informações agregadas ou derivadas, em conformidade com os princípios de
minimização de dados e com a legislação vigente, em especial a Lei Geral de Proteção de Dados
(LGPD). As alterações da proposta referentes à aplicação de vigilância estão detalhadas abaixo em
azul.

Seção 6.3: Esta estratégia habilita o desenvolvimento na vigência deste projeto de 2 aplicações
inovadoras voltadas para  dois casos de uso distintos:  a aplicação App1-Vigilância voltada para a
vigilância do campus por vídeo e IA (eMBB), e a aplicação App2-Monitoramento voltada para o
monitoramento ambiental e do solo utilizando uma rede de sensores no campus (mMTC).  Em todos
casos, será exercida atenção especial à segurança cibernética, desde o projeto das aplicações até
suas validações.
## ...
Na aplicação App1-Vigilância, o campus da UFPA-Belém será transformado em um “Living Lab” para
monitoramento da segurança pública, utilizando a Rede-5G-Green otimizada pela
Solução-ORAN-Green para redução do consumo de energia. O tráfego das câmeras de alta definição,
instaladas em áreas críticas do campus, representará uma alta carga para a Rede-5G-Green. As
informações de todas as câmeras serão transmitidas via 5G. As faces de pessoas serão anonimizadas
usando IA para garantir a privacidade e preservação da identidade de quem circula no campus. A
aplicação App1-Vigilância utilizará IA para detecção de casos de violência no campus, como
agressões e assaltos. Utilizaremos modelos de IA e banco de dados disponíveis na literatura para
aperfeiçoamento do modelo que será utilizado no campus, detectando as poses e movimentações de
interesse que possuem alta probabilidade de estarem associadas a atos violentos. No caso de
suspeita de ato violento, a aplicação retirará a anonimização da face da suspeita de envolvidos em
atos violentos e emitirá um alerta para o responsável da segurança para avaliação da situação,
tornando o sistema de monitoramento mais efetivo. Como requisito de integração da aplicação com
a infraestrutura Open RAN temos a necessidade de garantia de alta taxas de dados, dado que cada
câmera 4K com H.256 requer em média 25 Mbps, e uma garantia de latência abaixo de 100 ms da
rede para garantir que atos violentos sejam identificados rapidamente e a equipe de segurança do

campus obtenha a informação no menor tempo possível. A aplicação será validada com a encenação
de atos violentos pelo campus que deverão ser detectados assim como o monitoramento de
métricas de rede para garantia dos requisitos de taxa de dados e latência.


Q2: Na análise orçamentária, identificam-se fragilidades que ameaçam a operação: o valor alocado
para serviços em nuvem (R$ 8.000,00) está muito abaixo do necessário para suportar um data lake
de vídeo e IoT, e a ausência total de verba para Material de Consumo (R$ 0,00) é incompatível com a
natureza de um projeto de hardware. Adicionalmente, a tabela de pessoal apresenta inconsistências
de formatação que dificultam a auditoria dos valores. Conclui-se que a proposta seria mais sólida se
o escopo fosse reduzido, permitindo à equipe focar na entrega efetiva e segura dos resultados
prioritários.
R2: Agradecemos pela observação. Ajustamos o orçamento e esclarecemos no texto que
utilizaremos um servidor local adquirido para o projeto para executar a função de Data Lake dos
dados de vídeo e IoT. Optamos por uma solução local dado o menor custo do que a contratação de
serviços de nuvem para fornecer o serviço durante o tempo de execução do projeto. Corrigimos o
orçamento que classificou erroneamente os sensores, cabos e outros itens como materiais
permanentes ao invés de consumo, na rubrica custeio.



Respostas ao Revisor 5
A proposta apresenta um escopo abrangente, tecnicamente robusto e com clara relevância social,
articulando aplicações em agropecuária, segurança em campus universitário, monitoramento
ambiental e uso de IA avançada. O texto demonstra maturidade na identificação de problemas reais
e na proposição de soluções alinhadas às capacidades do 5G e da arquitetura Open RAN. Além disso,
a equipe reúne pesquisadores experientes em áreas como redes sem fio, IA, sensoriamento e
segurança, demonstrando forte capacidade de execução nas frentes centrais da proposta. O
envolvimento de múltiplas instituições e a colaboração internacional reforçam ainda mais a solidez
da iniciativa.
R0: Agradecemos ao revisor pelas observações e identificação de potenciais da nossa proposta.

Q1: Entretanto, a amplitude dos casos de uso — abrangendo agro inteligente, segurança de campus,
monitoramento ambiental, otimização energética, visão computacional, governança digital e redes
de sensores — representa um ponto de atenção central. Cada um desses domínios possui requisitos
técnicos próprios, fluxos de dados distintos e complexidade de integração elevada. Assumir
simultaneamente tantas linhas de investigação tende a aumentar riscos de atraso, dispersão de
esforços e potencial redução da profundidade técnica de cada frente. Uma priorização mais clara dos
casos de uso essenciais fortaleceria a viabilidade global da proposta.

R1: Agradecemos ao revisor pelas observações. Conforme orientações recebidas pelos revisores,
nós optamos por diminuir o número de aplicações e casos de uso da proposta com o intuito de
diminuir os riscos de execução do projeto ao longo do tempo fornecido. Com isso, agora temos a
entrega de duas aplicações e sem interdependência como forma a minimizar os riscos do projeto e
assegurar a conclusão do mesmo dentro do prazo de 24 meses.  As aplicações podem ser
executadas separadamente. As ações de otimização da rede planejadas no PT1, embora
fundamentais para assegurar o funcionamento adequado das aplicações, não bloqueiam a
implementação e os testes individuais de cada aplicação, pois é suficiente que a Rede-5G-Green
forneça conectividade para a realização dos testes iniciais de cada uma. Dessa maneira, garante-se
que as três frentes poderão desenvolver seus trabalhos de modo independente, assegurando as
entregas previstas sem que seja preciso priorizar aplicações em razão de interdependências entre
atividades ou da relação entre atividades e o cronograma do projeto. Os trechos alterados na
proposta estão detalhados abaixo em azul.


Seção 6.3: Esta estratégia habilita o desenvolvimento na vigência deste projeto de 2 aplicações
inovadoras voltadas para  dois casos de uso distintos:  a aplicação App1-Vigilância voltada para a
vigilância do campus por vídeo e IA (eMBB), e a aplicação App2-Monitoramento voltada para o
monitoramento ambiental e do solo utilizando uma rede de sensores no campus (mMTC).  Em todos
casos, será exercida atenção especial à segurança cibernética, desde o projeto das aplicações até
suas validações.
## ...
Na aplicação App1-Vigilância, o campus da UFPA-Belém será transformado em um “Living Lab” para
monitoramento da segurança pública, utilizando a Rede-5G-Green otimizada pela
Solução-ORAN-Green para redução do consumo de energia. O tráfego das câmeras de alta definição,
instaladas em áreas críticas do campus, representará uma alta carga para a Rede-5G-Green. As
informações de todas as câmeras serão transmitidas via 5G. As faces de pessoas serão anonimizadas
usando IA para garantir a privacidade e preservação da identidade de quem circula no campus. A
aplicação App1-Vigilância utilizará IA para detecção de casos de violência no campus, como
agressões e assaltos. Utilizaremos modelos de IA e banco de dados disponíveis na literatura para
aperfeiçoamento do modelo que será utilizado no campus, detectando as poses e movimentações de
interesse que possuem alta probabilidade de estarem associadas a atos violentos. No caso de
suspeita de ato violento, a aplicação retirará a anonimização da face da suspeita de envolvidos em
atos violentos e emitirá um alerta para o responsável da segurança para avaliação da situação,
tornando o sistema de monitoramento mais efetivo. Como requisito de integração da aplicação com
a infraestrutura Open RAN temos a necessidade de garantia de alta taxas de dados, dado que cada
câmera 4K com H.256 requer em média 25 Mbps, e uma garantia de latência abaixo de 100 ms da
rede para garantir que atos violentos sejam identificados rapidamente e a equipe de segurança do
campus obtenha a informação no menor tempo possível. A aplicação será validada com a encenação
de atos violentos pelo campus que deverão ser detectados assim como o monitoramento de
métricas de rede para garantia dos requisitos de taxa de dados e latência.
Na aplicação App2-Monitoramento voltada para os  casos de uso “Agro” e “Campus
inteligente”, as informações coletadas através de sensores IoT espalhados pelo campus,
incluindo sensores localizados no solo em regiões de vegetação, serão transmitidas pela

Rede-5G-Green para avaliarmos, em condições reais, tanto a conectividade 5G da
Solução-ORAN-Green quanto o monitoramento das métricas obtidas pelos sensores em
tempo real. Para habilitar esta aplicação,  ampliaremos o ecossistema de dispositivos 5G
comumente utilizados com o uso de equipamentos RedCap, a possibilidade de transmissão
via satélite, por meio de soluções como da Skylo, e a utilização de gateways IoT
BR5G-Gateways integrados com pontos de acesso 5G, explorando soluções que aumentem
o número de dispositivos conectados e que sejam adequados para ambientes rurais. Dessa
forma, quando sensores ou dispositivos IoT não dispuserem de conectividade 5G nativa,
utilizaremos dispositivos 5G FWA com WiFi, ou desenvolveremos um “gateway” dedicado
(BR5G-Gateways). Dessa forma, a App2-Monitoramento permitirá que o projeto explore
tecnologias que ampliem o uso de Open RAN e 5G em ambientes rurais, tanto no
monitoramento ambiental quanto no agronegócio, onde alguns dos principais desafios para
mMTC nesse contexto são a baixa diversidade de equipamentos com rádio 5G e relativo
alto custo.  Como requisitos para eficaz  integração com a infraestrutura Open RAN, temos
a necessidade de reduzido consumo de potência dos nós sensores e alcance adequado,
além da otimização da taxa de transmissão às necessidades de cada sensor. Todos esses
requisitos devem ser alcançados com baixo custo, para viabilizar aumento de escala em
experimentos com mMTC. Algumas das pesquisas possíveis são pautadas em
experimentos para controle de parâmetros da rede que diminuam as probabilidades de erro
de transmissão de pacotes, como por exemplo a fixação de valores de MCS baixos, e o
ajuste dinâmico de recursos utilizados pelo slice de mMTC dadas características de coleta
intermitente da maioria dos sensores. A aplicação será validada através do grau de sucesso
no estabelecimento de conectividade com diversos sensores distintos e do monitoramento
de parâmetros como a taxa de perda de pacotes nas transmissões efetuadas por sensores,
assim como o consumo de energia e a utilização da rede pelos sensores nos tempos
programados.

Q2: Outro aspecto relevante refere-se à execução das frentes especificamente ambientais e
agrobiológicas. Embora a participação da Embrapa agregue valor, os casos de uso propostos
abrangem elementos de monitoramento eco-hidrológico, variáveis agronômicas e sensores
ambientais que exigem validação contínua e acompanhamento especializado. Recomenda-se ampliar
ou tornar mais explícita a atuação de pesquisadores com formação direta em áreas ambientais,
biológicas ou afins, garantindo rigor metodológico e fidelidade científica nas etapas de coleta,
calibração e interpretação dos dados.
R2: Obrigado pela sugestão. Com a redefinição de casos de uso, agora temos a aplicação
App2-Monitoramento como a principal interface com os colaboradores da EMBRAPA. Essa
aplicação coletará informações de sensores IoT espalhados pelo campus, incluindo sensores
localizados no solo em regiões de vegetação, através da  Rede-5G-Green  para monitorarmos em
tempo real as métricas obtidas e habilitar avaliações por especialistas. Enfatizamos no texto dos
planos de trabalhos o alinhamento da UFPA campus Castanhal, Embrapa e UFRA nas atividades
relacionadas ao monitoramento eco-hidrológico, variáveis agronômicas e sensores ambientais
para o monitoramento contínuo e correta interpretação dessas informações obtidas com rigor
metodológico. No entanto, o principal objetivo da aplicação é explorar a conectividade via rede 5G
e o monitoramento de sensores, não focando em aspectos como a geração de inteligência de
processos usando como base os dados coletados. Os detalhes das alterações nos planos de

trabalhos estão detalhados abaixo em azul.

Plano de trabalho 3 (PT3):
## UNIFESSPA
A UNIFESSPA será a líder do PT3 e também colaborará com a montagem e instalação de sensores
com conectividade 5G no campus universitário, o envio de informações dos sensores para o “data
lake”, no desenvolvimento de aplicação para o monitoramento de métricas ambientais e de
qualidade do solo e a integração das aplicações de caso de uso com a Rede-5G-Green.
## Embrapa
A Embrapa atuará como consultora quanto aos requisitos e qualidade das aplicações desenvolvidas.
Assim, a Embrapa colaborará com o desenvolvimento da plataforma de monitoramento ambiental e
do solo através do levantamento de métricas-chave e informações sobre transformação de dados dos
sensores em informação útil e sua interpretação.
## UFRA
A UFRA atuará como consultora quanto aos requisitos e qualidade das aplicações desenvolvidas
principalmente no âmbito de monitoramento ambiental, como na identificação de comportamentos
anômalos e métricas chave para monitoramento.


Q3: No que diz respeito ao Open RAN, apesar da boa descrição conceitual, a proposta poderia
aprofundar como se dará a integração prática com plataformas reais, SDKs, orquestradores, pipelines
de CI/CD e, sobretudo, com o RIC em seus níveis near-RT e non-RT. A depender da complexidade das
frentes simultâneas, a equipe pode enfrentar dificuldades em consolidar xApps/rApps plenamente
funcionais no tempo disponível, especialmente considerando as lacunas de especialização explícita
nas tecnologias centrais da O-RAN Alliance. Esse ponto afeta a avaliação da viabilidade técnica e da
maturidade da implementação.
R3: Agradecemos o comentário. Como a proposta de aplicação está de acordo com as
funcionalidades da ilha Open RAN do hospedeiro, alguns detalhes relacionados à implementação
da infra-estrutura Open RAN como estações de rádio base (RU, DU, CU) e RICs não foram
apresentadas na proposta de aplicação devido ao limite de páginas imposto. Ainda sim,
adicionamos detalhes sobre a implementação de xApps/rApps e a integração dos mesmos com
diferentes pilhas de softwares para o Near e Non-RT RIC, garantindo assim a integração dos
xApps/rApps que serão desenvolvidos com a infraestrutura Open RAN. Não ficou claro a quais
lacunas específicas o revisor se refere, mas também  adicionamos informações sobre a expertise
dos integrantes da proposta que possuem implementações de xApps e rApps integrados com Near
e Non-RT RICs em outros cenários e seriam os responsáveis por realizar a adaptação para a
presente proposta.


Q4: Em síntese, trata-se de uma proposta ambiciosa, inovadora e com forte potencial de impacto,
com alinhamento sólido aos objetivos da chamada. Contudo, recomenda-se ajustar o escopo para
mitigar a dispersão causada pelo grande número de casos de uso e reforçar a participação de
especialistas ambientais nas frentes correspondentes.
R4: Agradecemos os comentários. Seguindo as orientações, agora a proposta foi ajustada para
entregar duas aplicações e software associado.






























## PROGRAMA OPENRAN@BRASIL:
## SELEÇÃO INTEGRADA DE APLICAÇÕES 5G OPEN RAN E HOSPEDEIROS – ETAPA 2
## ANEXO II - FORMULÁRIO DE SUBMISSÃO





Proposta de Aplicação 5G Open RAN
GreenRAN: Open RAN Sustentável para o Agro e Campi Inteligentes

Nome em língua inglesa:
GreenRAN: Sustainable Open RAN for Agriculture and Smart Campuses








## Eduardo Coelho Cerqueira
24/Out/2025


- Dados do Proponente / Coordenador Geral
A pessoa identificada como proponente e Coordenadora Geral precisa pertencer ao quadro
de funcionários da Instituição Executora/Principal.
## I. Nome Completo:
## Eduardo Coelho Cerqueira
II. Instituição de Vínculo:
Universidade Federal do Pará (UFPA)
III. E-mail de Contato:
cerqueira@ufpa.br
IV. Telefone de Contato:
## (91) 992032121
## V. Currículo Lattes Atualizado:
http://lattes.cnpq.br/1028151705135221





- Dados da Instituição do Coordenador Geral
Apresentar as informações da instituição à qual o Coordenador Geral está vinculado e que
se candidata no âmbito da Seleção de Aplicações 5G Open RAN e Hospedeiros.
I. Nome da Instituição:
Universidade Federal do Pará
II. Sigla:
## UFPA
## III. CNPJ:
## 34.621.748/0001-23
IV. Informar a natureza da Instituição:
Instituição pública de ensino superior
## V. Estado:
## Pará
VI. Cidade:
## Belém
VII. Bairro:
## Guamá
## VIII. CEP:
## 66075-110
IX. Endereço:
## Rua Augusto Corrêa, 01



- Dados das Instituições Parceiras
● Nome da Instituição #1 - Universidade de Campinas (UNICAMP)
● Pesquisador da Instituição #1 - Carlos Alberto Astudillo Trujillo / Professor
## ● CNPJ: 46.068.425/0001-33
## ● Estado: São Paulo
## ● Cidade: Campinas
● Contribuição: A UNICAMP irá contribuir com sua expertise em RAN (Radio Access
Network) slicing, especificamente no uso de Machine Learning (ML) para otimizar
a utilização de slices para as aplicações eMBB (Enhanced Mobile Broadband)
com vídeos de alta definição e dados de LiDAR (Light Detection and Ranging).
● Contrapartida: O Instituto de Computação da UNICAMP possui uma infraestrutura
computacional composta por servidores contendo mais de 300 núcleos agregados
de processamento com 1TB de memória RAM, além de 4 GPUs, totalizando
18432 cuda cores. Para processamento de altas cargas de trabalho, conta com
uma máquina servidora com 2 CPUS Intel(R) Xeon(R) Platinum 8358 CPU
2.60GHz cada uma com 32 cores e 64 threads, 8 GPUs NVIDIA A100 80GB, 1.5
TB de RAM e 5.25 TB de armazenamento. São também disponibilizados para o
projeto: dispositivos IoT, Arduino, Raspberry Pi, Zigbee e WiFi, dispositivos de
rádio definido por software (SDR) USRP B210/B200, antenas, minicomputadores
para borda e USRPs, e NVIDIA Jetson Nano.


● Nome da Instituição #2 - Universidade Federal do Sul e Sudeste do Pará
## (UNIFESSPA)
● Pesquisador da Instituição #2 - Diego Gomes / Professor
## ● CNPJ: 18.657.063/0001-80
## ● Estado: Pará
## ● Cidade: Marabá
● Contribuição: A UNIFESSPA contribuirá com a sua expertise nas áreas de IoT e
simulações de sistemas de comunicação NTN (Non-Terrestrial Network), as quais
serão importantes para os testes disruptivos da tecnologia “direct to cell” previstos
para serem realizados com o apoio da empresa Skylo (www.skylo.tech). O uso de
satélites permite ampliar o escopo de aplicações mMTC (Massive Machine-Type
Communications), complementando tecnologias como RedCap (Reduced
Capability) NR e é de importância para habilitar a conectividade rural em países
como o Brasil. Além disso, a experiência da UNIFESSPA na área de
processamento de sinais e camada física de comunicações 5G e NTN, será
importante para a configuração, otimização e aprimoramento da rede nos casos
de uso colimados.
● Contrapartida: Diversos sensores para aplicações em regiões de fazendas e áreas
remotas, acesso a dados de estação meteorológica disponibilizada através de
banco de dados em nuvem, pesquisadores e com experiência em análise de
dados, inteligência artificial e desenvolvimento de aplicações Web.



● Nome da Instituição #3 - Universidade do Estado do Pará (UEPA)
● Pesquisador da Instituição #3 - Hugo Santos / Professor
## ● CNPJ: 34.860.833/0001-44
## ● Estado: Pará
## ● Cidade: Belém
● Contribuição: A UEPA contribuirá com a sua expertise na área de
desenvolvimento de sistemas baseados em ML/AI e aplicações Web, gestão de
“data lake” e computação em nuvem, os quais são essenciais para os casos de
uso a serem desenvolvidos. Além disso, a UEPA contribuirá com sua expertise
nas aplicações que envolvem distribuição de vídeos de alta resolução com
otimização da qualidade e experiência do usuário.
● Contrapartida: Computadores e recursos humanos nas áreas citadas, incluindo o
desenvolvimento de sistemas inteligentes, gestão de “data lake” e computação em
nuvem.

● Nome da Instituição #4 - Universidade Federal Rural da Amazônia (UFRA)
● Pesquisador da Instituição #4 - Allan Costa / Professor
## ● CNPJ: 05.200.001/0001-01.
## ● Estado: Pará
## ● Cidade: Belém
● Contribuição: Sendo a UFRA uma referência no agronegócio, com foco nas
cadeias produtivas e na realidade ambiental da região amazônica, a mesma
contribuirá com sua expertise para alavancar o desenvolvimento e validação dos
casos de uso do projeto. O campus da UFRA fica ao lado da UFPA. Apesar dos
rádios (RUs) estarem localizados de forma agregada no campus da UFPA, como
será detalhado no texto desse projeto, as aplicações usando dados provenientes
de lavouras serão estrategicamente emuladas na rede 5G Open RAN. Para isso, é
essencial a contribuição da UFRA no provimento de dados realistas do campo, e
no desenvolvimento das aplicações referentes aos casos de uso desenvolvidos no
projeto. Além disso, a UFRA, que é parceria da RNP e da UFPA, durante a 30ª
Conferência das Partes das Nações Unidas sobre Mudança do Clima (COP30 -
Belém/PA de 05 até 21/Nov/2025), contribuirá com sua expertise na área de
segurança cibernética.
● Contrapartida: Locais para coleta de dados e execução de testes, incluindo áreas
de plantações. Computadores e recursos humanos para o desenvolvimento e
validação dos casos de uso do projeto, bem como na área de segurança
cibernética para a proteção dos dados (ambientais, etc.) e resiliência cibernética.

● Nome da Instituição #5 - Universidade Federal do Rio Grande do Sul (UFRGS)
● Pesquisador da Instituição #5 - Weverton Luis da Costa Cordeiro / Professor
## ● CNPJ: 18.657.063/0001-80
● Estado: Rio Grande do Sul
## ● Cidade: Porto Alegre
● Contribuição: A UFRGS usará sua expertise em desenvolvimento de aplicativos
para redes Open RAN, para contribuir neste projeto com o desenvolvimento de
xApps e rApps relacionados a slicing e à economia de energia em redes Open

RAN, explorando métodos de inteligência artificial para otimização dos slices e
também identificação de momentos oportunos para economia da energia.
● Contrapartida: A equipe da UFRGS conta com switches programáveis Edgecore
Tofino, smartNICs NVIDIA BlueField-2 e Xilinx Alveo, além de placas NetFPGA e
servidores de alto desempenho com processadores AMD EPYC e Intel Xeon.
Inclui ainda desktops compatíveis para testes e desenvolvimento, equipamentos
SDR (USRP B210/B200mini) para experimentação em rádio definido por software,
e minicomputadores e dispositivos IoT como Raspberry Pi e Arduino. Essa
infraestrutura permite experimentação remota completa do plano de dados e
controle, com suporte à programabilidade, virtualização e integração de redes 5G,
auxiliando no desenvolvimento do projeto ao prover um ambiente extra de
experimentação além do hospedado na UFPA.


● Nome da Instituição #6 - Empresa Brasileira de Pesquisa Agropecuária (Embrapa)
## Amazônia Oriental
● Pesquisador da Instituição #6 - Walkymário Lemos / Chefe Geral
## ● CNPJ: 00.348.003/0128-01
## ● Estado: Pará
## ● Cidade: Belém
● Contribuição: A Embrapa contribuirá com a sua expertise com os casos de uso
relacionados a Agro 4.0 e conectividade rural em geral, com foco no mMTC e as
aplicações referentes aos casos de uso. A mesma não estará atuando no
desenvolvimento em si ou produzindo entregáveis formais, mas tem parte
essencial no “Advisory Board” do projeto, sendo responsável por validar os
requisitos e as aplicações dos casos de uso do projeto.
● Contrapartida: A Embrapa irá prover acesso a lavouras e plantações, além de
alocar recursos humanos para contribuir com a avaliação das aplicações para os
casos de uso “Agro”, com expertise em pilotos IoT e 5G, por exemplo através do
programa Semear Digital (https://www.semear-digital.cnptia.embrapa.br).


● Nome da Instituição #7 - Instituto de Telecomunicações / Universidade de Aveiro
● Pesquisador da Instituição #7 - Susana Sargento
● CNPJ: Não se Aplica
● Estado: Não se Aplica (País: Portugal)
## ● Cidade: Aveiro
● Contribuição: Apesar de assumir uma categoria diferenciada das demais
parceiras, por não ser listada como uma instituição conectada à RNP, o IT Aveiro é
destacado aqui nesta seção pela relevância ao projeto no seu papel de
colaboradora internacional. O IT Aveiro já avançou em alguns dos desafios que
serão encarados no presente projeto, e com isso é essencial como referência a
“deployments” de Open RAN a pesquisadores (docentes e discentes) que já se
beneficiam da colaboração existente. Mais especificamente, o IT Aveiro contribui
com sua expertise em experimentação Open RAN em “living labs” e no
desenvolvimento em colaboração com a equipe deste projeto nas soluções
disruptivas na área do Agro 4.0, Conectividade Rural e Campus e Cidades

Inteligentes. A experiência bem sucedida no desenvolvimento de xApps e casos
de uso Open RAN na cidade de Aveiro em Portugal irá contribuir para acelerar o
desenvolvimento das aplicações do projeto, e a colaboração internacional
impulsiona o impacto do projeto em aspectos como visibilidade das publicações.
● Contrapartida: Acesso a xApps e infraestrutura Open RAN na cidade de Aveiro
(Portugal) composto de 44 unidades de rádio reconfiguráveis, com comunicações
de curto e longo alcance (p.e., 5G, LoRa, WiFi, V2X, backhaul por mWave e
Satélite), sensores para recolha de dados (como sensores ambientais e sensores
de mobilidade, Lidars, radares e câmaras de vídeo em carros, caminhões,
bicicletas e scooters), sensores de estacionamento, e unidades de computação
avançada para processamento de dados e tomada de decisões com Inteligência
## Artificial.


- Instituição Hospedeira e Coordenador do Hospedeiro

I. Nome da Instituição Hospedeira:
POP-PA / UFPA – Universidade Federal do Pará
II. Nome do Coordenador do Hospedeiro:
## Aldebaro Klautau



- Verticais de Interesse

## I. Vertical Principal:
C. Agro 4.0 e Conectividade Rural
II. Verticais Secundárias:
F. Cidades e Campi Inteligentes


- Descrição da proposta de Aplicação 5G Open RAN
## 6.1. Sumário Executivo
A proposta “GreenRAN: Open RAN Sustentável para o Agro e Campi Inteligentes”
entregará a Solução-ORAN-Green, a qual inclui
dois xApps e um rApp. Esta solução será
sistemática e extensivamente avaliada a partir de
duas aplicações desenvolvidas em
distintos casos de uso, nas verticais “Agro 4.0 e Conectividade Rural” (principal) e “Cidades
e Campi Inteligentes” (secundária). Essas aplicações utilizarão a conectividade 5G
proporcionada pela Rede-5G-Green, hospedada no campus da UFPA em Belém. O uso de
ML / AI através do Open RAN permitirá aplicações “green”, com otimização do consumo de
energia.
Os xApps que serão desenvolvidos para a Solução-ORAN-Green são: xApp1-RANSlicer
para “RAN slicing” e o xApp2-EnergySaver para “economia de energia”, os quais habilitam a
Rede-5G-Green a se ajustar aos SLAs (Service Level Agreements) de cada slice e otimizar
o consumo de energia. Desta forma, a Solução-ORAN-Green suporta aplicações de 5G que
se beneficiam de melhorias em desempenho proporcionadas pelo Open RAN para
aumentar a eficiência no cumprimento de requisitos de aplicações e eficiência energética. .
O  rApp a ser desenvolvido é o rApp-ResourceOptimizer de “otimização de recursos” que
visa garantir a coordenação entre as funções de RAN slicing e economia de energia de
forma a priorizar o cumprimento de requisitos de slices enquanto se minimiza o consumo de
energia em momentos oportunos da rede, como por exemplo em momentos de baixa
demanda. Assumindo sucesso do projeto nesses casos de uso, a Solução-ORAN-Green
também incorpora “Agentic AI” e técnicas que visam aumentar a segurança na utilização de
xApps e rApps na arquitetura Open RAN(por exemplo, no uso de IA em xApps) de forma a
fomentar sua adoção.
O projeto valida a Solução-ORAN-Green por meio de duas aplicações, em distintos casos
de uso
, focados nas verticais “Agro” e “Campus”, explorando tanto aplicações de alta taxa
(eMBB) quanto de comunicação massiva de dispositivos (mMTC). Na vertical “Agro”,
desenvolve-se uma aplicação
mMTC consistindo em uma rede de sensores para gestão e
análise do solo em campo e monitoramento ambiental. Já na vertical “Campus”, um caso
(eMBB) emprega vídeo e IA para vigilância com baixo consumo de energia.
Além do foco
comum aos dois casos de uso na redução de consumo de energia, o projeto considera as
limitações atuais de diversidade e custo de dispositivos 5G, os quais limitam principalmente
os serviços mMTC em cenários como o do Agro 4.0. Por isso, a equipe desenvolverá
gateways customizados e configurará modems FWA com suporte a ambos 5G e Wi-Fi,
entregando dispositivos com custo reduzido e auxiliando a expansão do 5G mMTC no
## Brasil.
Dentre os principais benefícios e impactos esperados, encontra-se o desenvolvimento de
inovadora tecnologia nacional, associada não apenas
à Solução-ORAN-Green mas também
às aplicações para os casos de uso. O projeto também promoverá a
difusão do Open RAN
5G e o posicionamento da RNP e seus usuários na vanguarda das tecnologias associadas.



Tabela 1 - Sumário dos principais entregáveis do projeto GreenRAN.
Nome / sigla Descrição
Solução-ORAN-Green Solução completa de softwares funcionando na estrutura 5G
fornecida pelo hospedeiro, os dois agentes de IA, e todos softwares
desenvolvidos (como xApps e rApps).
Rede-5G-Green Rede Open RAN 5G hospedada no campus da UFPA em Belém.
Agentic-AI-Green Softwares que dão suporte ao uso de agentes de IA no contexto da
Solução-ORAN-Green. Durante o projeto serão desenvolvidos dois
agentes.
Agent-AI-OpenRAN Agente de IA responsável pela orquestração dos rApps, operando
com base em intenções de rede fornecidas pelo Agent-AI-Usuário.
Agent-AI-Usuário Agente de IA responsável por interpretar intenções de alto nível
fornecidas pelo operador da rede e gerar intenções separadas para
cumprimento de requisitos nos slices e economias de energia.
RAN-CodeUpdates Coleção de rotinas modificadas para dar suporte à solução,
relacionadas aos padrões 3GPP e OpenAirInterface
xApp1-RANSlicer xApp responsável pelo controle de alocação de recursos entre RAN
slices para garantia de cumprimento de requisitos.
xApp2-EnergySaver xApp responsável pelo controle de alocação de potência para UEs e
identificação de momentos oportunos para economizar energia
sem deixar de atender os requisitos.
rApp-ResourceOptimizer rApp responsável pela otimização de recursos e energia de forma
conjunta, orquestrando as operações dos xApps  xApp1-RANSlicer e
xApp2-EnergySaver.
App1-Vigilância Aplicação responsável por transformar o campus da UFPA-Belém
em um “Living Lab” para monitoramento da segurança pública
utilizando métodos de IA para detecção de casos de violência no
campus através da imagem de câmeras.
App2-Monitoramento Aplicação responsável pela coleta de informações de sensores IoT
espalhados pelo campus, incluindo sensores localizados no solo em
regiões de vegetação, através da  Rede-5G-Green  para
monitorarmos em tempo real as métricas obtidas e identificarmos
dados de interesse que possam indicar situações de risco ambiental
e mudanças bruscas na características do solo.
BR5G-Gateways Gateways IoT customizados para conexão com rede Open RAN 5G.



## 6.2. Desenvolvimento Tecnológico
Este projeto propõe a implantação da Rede-5G-Green, uma infraestrutura Open RAN que
emprega a funcionalidade de RICs e seus aplicativos (xApps e rApps) para otimizar e
adaptar dinamicamente às operações da rede, atendendo às demandas específicas das
verticais de “Agro 4.0 e Conectividade Rural” e “Cidades e Campi Inteligentes”. A
Rede-5G-Green aproveitará os recursos da arquitetura Open RAN, complementados pelo
desenvolvimento de xApps e rApps personalizados, para viabilizar aplicações finais de alto
desempenho (KOUCHAKI, 2025), com foco nas verticais do projeto, assegurando altas
taxas de transmissão, confidencialidade e confiabilidade e, baixa latência. O suporte da
rede a essas aplicações será realizado por meio da implementação de métodos inovadores
que avançam o estado da arte em controle e otimização de processos em redes Open RAN,
fornecendo garantias sólidas para o atendimento dos requisitos das aplicações finais.
Na vertical de “Cidades e Campi Inteligentes”, será desenvolvida uma aplicação final
principal denominada App1-Vigilância: um sistema de segurança pública baseado em
monitoramento por vídeo de alta definição com análise de inteligência artificial em tempo
real para o campus universitário. Para a vertical “Agro 4.0 e Conectividade Rural”, a
aplicação final central é denominada App2-Monitoramento, e consiste no monitoramento
ambiental e do solo mediante  dados de sensores para análise em tempo real, contando
com rede  massiva de sensores para análise.
Diante desses casos de uso, é fundamental
prover altas taxas de transmissão e baixa latência aos dispositivos que disseminam
imagens para análise de IA em tempo real, assim como garantir transmissões de alta
confiabilidade para os sensores de monitoramento ambiental. Para além dos requisitos
individuais de cada aplicação, o projeto visa otimizá-las globalmente através da gestão
inteligente de recursos de rede, permitindo a diferenciação de serviços, o fornecimento e
orquestração de slices adaptativos e personalizados para distintos contextos. Esta
abordagem também permitirá uma otimização geral da rede, com foco na economia de
energia e na exploração de dados ambientais obtidos por meio de dados de transmissão em
radiofrequência (RF).
A orquestração e execução das funcionalidades da rede 5G será executada por meio da
utilização de xApps no Near-RT (Near-Real-Time) RIC e rApps no Non-RT (Non-Real Time)
RIC, sendo essenciais para atender aos objetivos das aplicações finais exigidas por cada
caso de uso. Com este propósito, o projeto apresenta a Solução-ORAN-Green, cuja visão
geral é ilustrada na Figura 1. Esta arquitetura destaca os diferentes domínios de coleta de
informação e controle distribuídos pela estrutura Open RAN, como a Distributed Unit (DU), a
Centralized Unit (CU), os RICs Near-RT e Non-RT, o Data Lake, bem como as aplicações
de caso de uso e de gerenciamento de usuários. Por fim, a arquitetura incorporará os
Equipamentos dos Usuários (UEs) representados por câmeras, sensores e dispositivos
como smartphones, que se conectarão à rede 5G por meio de uma das duas RUs externas
ou de uma das duas RUs internas disponíveis na ilha Open RAN hospedada na UFPA.
Com base em uma análise preliminar e nos requisitos dos casos de uso das verticais
selecionadas, foram identificadas como essenciais às funções da CU/DU de alocação de
blocos de recursos físicos (PRB), controle de potência de transmissão, ligar/desligar células
e camadas (“layers”), e coleta de informações de métricas-chave de desempenho (KPM).
As funções de alocação de PRB e de potência estão diretamente relacionadas ao
atendimento dos requisitos de diferentes fatias de rede (RAN slicing), impactando

diretamente a capacidade de transmissão e a eficiência energética de cada slice (Oliveira,
2025). A função para ligar/desligar células e “layers” permite o controle sobre o uso das
diferentes células e “layers” de RF disponíveis na rede para um controle granular da energia
utilizada pelo sistema. Por sua vez, as funções de coleta de KPM, realizadas em diversos
momentos de operação da rede, permitem o monitoramento em tempo real do desempenho
da rede, auxiliando assim na tomada de decisão para alocação de recursos. Do ponto de
vista prático, softwares de código aberto, como o OpenAirInterface, normalmente
implementam as funções de alocação de PRB e controle de potência de forma estática.
Portanto, parte do desenvolvimento deste projeto consistirá em habilitar a definição
dinâmica da quantidade de recursos para cada slice de RAN e a seleção do algoritmo de
controle de potência, permitindo que esses valores sejam configurados via interface E2 da
arquitetura Open RAN. Dessa forma,
as nossas alterações nas funções da RAN
denominadas RAN-CodeUpdates serão disponibilizadas publicamente.
Além disso, este
projeto propõe o uso de orquestração baseada na arquitetura Service Management and
Orchestration (SMO), viabilizando ajustes automatizados e coordenados das funções da
CU/DU. O SMO atuará na coordenação, integrando dados provenientes do Near-RT RIC e
do Non-RT RIC para otimizar a operação da RAN de forma contínua e adaptativa. E assim,
promover uma operação mais eficiente e alinhada aos requisitos das verticais selecionadas,
de forma autônoma e orientada por intenções.
O mesmo princípio aplica-se às funções de ligar/desligar células e “layers” de forma
inteligente, e também a coleta de métricas de KPM, que, embora estejam naturalmente
disponíveis nas diferentes camadas da stack 5G (como PHY e MAC), não dispõem de uma
interface para sua coleta via E2 completamente implementadas, o que impediria sua
utilização por xApps e rApps. Dessa forma, um pilar fundamental da solução proposta será
avançar o estado da arte dos softwares de código aberto (SANTOS, 2025),
o que
chamamos de RAN-CodeUpdates,
que implementam a CU/DU, habilitando a coleta de
informações e o controle dinâmico das funções determinadas (ELYASI, 2025).
A inteligência para controle da Rede-5G-Green será distribuída em dois domínios distintos.
O primeiro estará localizado nos RICs da arquitetura Open RAN, sendo implementado por
meio de xApps para slicing de rede e economia de energia no Near-RT RIC, e pelo rApp de
otimização de recursos no Non-RT RIC. Complementarmente a essas funções, o
Agent-AI-OpenRAN atuará como um agente de IA para orquestração dos rApps, operando
com base em intenções de rede. O segundo domínio é representado pelas aplicações de
caso de uso e gerenciamento de usuário, onde serão implementadas as aplicações finais
responsáveis por atender a cada um dos casos de uso das verticais. Enquanto o primeiro
domínio adapta e otimiza a Rede-5G-Green para atender aos requisitos de comunicação
necessários para cada aplicação final, o domínio das aplicações de caso de uso implementa
os serviços efetivos que serão disponibilizados aos usuários da rede.



Figura 1 - Arquitetura da Solução-ORAN-Green baseada na integração entre a
Rede-5G-Green e o uso de Agentic-AI-Green para adaptação de recursos em tempo real
para atender aos requisitos das diferentes aplicações dos usuários presentes na rede.

Todos os componentes de ambos os domínios serão desenvolvidos para avançar o estado
da arte em suas respectivas funcionalidades de controle de rede, com avaliação fim a fim
baseada nas métricas de rede e no desempenho das aplicações finais de cada caso de uso
das verticais. O xApp
xApp1-RANSlicer de RAN slicing será responsável pelo controle da
alocação de PRBs para cada slice disponível na rede. Nossa equipe possui expertise
consolidada no desenvolvimento de alocadores de recursos de rádio que utilizam métodos
de aprendizado de máquina, especificamente aprendizado por reforço profundo (DRL), para
cenários de redes 5G com requisitos de slices baseados em intenção (Nahum, 2023;
## Nahum, 2025),
além de termos desenvolvido um xApp alocador de PRB para diferentes
RAN slices utilizando o simulador NS-3 - NORI (Network Simulator 3 - New Open RAN
Interface) integrado à implementação real do Near-RT RIC da O-RAN SC (Oliveira, 2025).
## A
implementação do xApp de RAN slicing se baseará no conceito de alocador de PRB por
intenções já estabelecido em nossos trabalhos anteriores, mas promoverá a investigação de
métodos de aprendizado por reforço seguro (Nagib, 2025) para reduzir o número de
violações dos requisitos de cada slice, bem como métodos de treinamento online (Nagib,
2023) para manter a alta performance da política de alocação, assegurando continuamente
o atendimento aos requisitos. Dessa forma, o fluxo operacional do xApp1-RANSlicer
consiste em receber os requisitos de cada slice presentes na rede, informados pelo rApp de
otimização de recursos, definir as variáveis de alocação de PRB na função da CU/DU, e
monitorar continuamente as métricas de cada slice para garantir a conformidade com os
requisitos estabelecidos.

O xApp2-EnergySaver de economia de energia terá como função principal gerenciar o
desligamento seletivo de células de transmissão e “layers”, visando reduzir o consumo
energético nas estações rádio base, que compreendem o conjunto RU, DU e CU. Em
cenários onde os Equipamentos de Usuário (UEs) se concentram na área de borda entre
duas RUs, gerando um aumento significativo de interferência, o xApp avaliará a viabilidade
de desativar uma das células ou “layers”. Esta ação será sempre balanceada com a
necessidade de manter o cumprimento dos requisitos estabelecidos para cada slice de rede
e aplicação final. Adicionalmente, o xApp terá a funcionalidade de identificar períodos de
baixa utilização da rede, frequentemente causados por comportamentos sazonais, como a
redução do fluxo de pessoas em campi universitários durante o período noturno. Neste
contexto, o xApp aprenderá a reconhecer tais padrões comportamentais para identificar
janelas de oportunidade para o desligamento de células e “layers”, maximizando assim a
eficiência energética da Rede-5G-Green. Para o desenvolvimento da metodologia de
detecção desses momentos oportunos e do controle sobre quais recursos desligar, serão
empregados métodos de aprendizado de máquina para reconhecimento de padrões em
métricas de rede que indiquem subutilização ou cenários de alta interferência intercelular
(Haider, 2023), complementados por técnicas de aprendizado por reforço para definir a
estratégia ótima de desligamento (Islam, 2023). É importante ressaltar que, paralelamente
aos avanços proporcionados pela construção do xApp, o projeto também contribuirá para o
estado da arte do software de código aberto que implementa a RAN, habilitando nele a
funcionalidade de desligamento de células e “layers”, o que é um pré-requisito para que
esse controle possa ser exercido pelo xApp.

No domínio do Non-RT RIC, será implementado o rApp rApp-ResourceOptimizer de
otimização de recursos que terá a função central de coordenar as ações do xApp de RAN
slicing e do xApp de economia de energia, promovendo uma otimização conjunta que atinja
os objetivos definidos pelo Agent-AI-OpenRAN. Considerando que os xApps operam com
uma visão isolada de seus respectivos recursos e ações, cabe a este rApp harmonizar as
políticas de cada um para garantir o cumprimento dos objetivos finais dos casos de uso. Por
exemplo, ao receber a exigência de um slice dedicado ao monitoramento por câmeras que
necessita de garantia de qualidade de serviço para transmissão de vídeo em 4K, o rApp de
otimização selecionará e configurará as políticas executadas pelos xApps de RAN slicing e
economia de energia, assegurando o atendimento dos requisitos de desempenho enquanto
maximiza a eficiência energética. Por não ser um agente baseado em modelo de
linguagem, o rApp disporá de uma interface bem definida para a entrada de requisitos dos
casos de uso. Sua operação se baseará em métodos de aprendizado de máquina aplicados
a dados históricos de operação da Rede-5G-Green, que relacionam o desempenho final das
aplicações com as diferentes políticas de alocação de potência e RAN slicing
implementadas pelos xApps. O desenvolvimento deste rApp representará um avanço em
relação ao estado da arte atual, que tipicamente aborda a otimização energética e o slicing
de rede de forma isolada em ambientes reais (Elkael, 2025), ao propor uma otimização
integrada dos recursos de RAN slicing e economia de energia com base em requisitos
dinâmicos fornecidos por Agentic IA e IA generativa - Language Model (LM)s.
Ainda no Non-RT RIC, temos a função de Agentic-AI-Green, que é a responsável por
interpretar as intenções de rede de alto nível expressas pelo usuário da rede através do

Agent-AI-Usuário e transformá-las em objetivos claros e bem definidos para o rApp de
otimização de recursos. Por exemplo, o gerenciador Agent-AI-OpenRAN pode receber
intenções do Agent-AI-Usuário indicando que o slice de monitoramento via câmeras deveria
ser priorizado em casos de congestionamento na rede, de forma que os slices responsáveis
pelo monitoramento de sensores menos prioritários como  sensores de umidade do solo
poderiam ter uma diminuição geral dos seus recursos ou mesmo um aumento significativo
nos dados requisitados pelos dispositivos na rede. Dessa forma, o Agent-AI-OpenRAN
operará no domínio da linguagem natural para perceber as necessidades expressas pelo
usuário através do Agent-AI-Usuário e instruir os rApps para adaptar os seus
comportamentos e, por consequência, o funcionamento dos xApps e funções da CU/DU. O
Agent-AI-OpenRAN também terá capacidade de tomar decisões de forma autônoma após
identificar alterações não desejadas nas condições da rede.
No domínio das aplicações de caso de uso e do gerenciamento de usuários, temos o
Agent-AI-Usuário, que estará localizado fora da Rede-5G-Green e será o responsável por
interagir com os usuários da rede para obter informações detalhadas sobre os casos de uso
e os requisitos de cada aplicação. Além de fornecer informações sobre a rede e seus casos
de uso, o Agent-AI-Usuário também pode oferecer ao usuário informações, sugestões e
alertas sobre a condição da rede. Apesar da possibilidade de controle humano através da
interface de usuário, uma vez definido os casos de usos e requisitos a serem alcançados,
os Agent-AI-OpenRAN e Agent-AI-Usuário dialogam de forma autônoma sobre a melhor
forma de alcançar os objetivos dado a condição atual da rede, e promovendo adaptações
sempre que necessário, seja por limitações na disponibilidade de recursos ou por não
concordar com as políticas sugeridas para o rApp.
Um exemplo da interação entre o Agent-AI-OpenRAN e Usuário é demonstrado na Figura 2.
A interface de usuário representa um sistema que permite a entrada de dados por parte do
usuário, como por exemplo uma caixa de texto detalhando qual o tipo de mudança ele
gostaria de realizar na rede. O Agent-AI-Usuário é o responsável por interpretar a entrada
do usuário em linguagem natural e compreender os objetivos gerais  da rede que precisam
ser alcançados sem entrar em detalhes sobre como esses objetivos serão alcançados. O
Agent-AI-OpenRAN será o responsável por processar os objetivos gerados pelo
Agent-AI-Usuário e transformar a intenção recebida em entradas bem definidas e em
formato de código pré-definido para o rApp com o qual está interagindo. Apesar de não
representado na figura, o Agent-AI-OpenRAN pode interagir com mais de um rApp ao
mesmo tempo se julgar necessário que sejam realizadas ações conjuntas em diferentes
domínios da rede. No fluxo inverso, o rApp fornece informações sobre o estado atual da
rede para o Agent-AI-OpenRAN que fornecerá para o Agent-AI-Usuário uma descrição
técnica do estado da rede após as ações que foram implementadas. Por fim, o
Agent-AI-Usuário fornecerá ao usuário uma descrição de alto nível e de fácil entendimento
sobre o estado da rede e sobre o impacto nas aplicações de caso de uso.


Figura 2 - Exemplo de interação entre Agentic-AI-Green, rApp e interface de usuário para
gerenciamento de consumo de energia na Rede-5G-Green.
É importante notar que os planos de dados e controle, os modelos inteligentes
automatizados, e a própria infraestrutura do Open RAN possuem requisitos de segurança
cruciais. Essa necessidade se destaca ao se verificar que agentes maliciosos podem causar
grandes danos ao vazar ou utilizar indevidamente dados confidenciais ou ao atacar os
modelos de aprendizado de máquina, levando-os a gerar falsas detecções e alarmes.
Outras ameaças relevantes são capazes de tornar parte ou toda a rede inoperante. Dessa
forma, não basta apenas garantir a comunicação no plano de dados ou a coleta de
informações no plano de controle; é imprescindível assegurar aspectos de segurança como
o desenvolvimento de métodos que tornem os modelos inteligentes mais robustos contra
agentes maliciosos. Por uma perspectiva de segurança transversal, será proposto um
arcabouço de soluções para elevar o nível de defesa contra ameaças externas, com foco na
robustez dos modelos de aprendizado de máquina.
Nesta abordagem de segurança, destaca-se a importância de métodos de defesa contra
ataques de evasão (Dias, 2025). Esses tipos de ataques são explorados por atores
maliciosos com a intenção de produzir falsos alarmes, ou evadir detecção e monitoramento
automatizado. Métodos de robustez e resiliência aplicados aos modelos de aprendizado de
máquina implantados, vai permitir aumentar o nível de proteção executados nas xAPPs e
também em outros modelos que tenham execução na rede Open RAN. Vale ressaltar que a
equipe do projeto possui expertise consolidada em propor soluções nos aspectos de
segurança mencionados.








6.3. Caso(s) de Uso 5G e Open RAN
O projeto busca inovação tecnológica tanto no desenvolvimento da Solução-ORAN-Green,
quanto na sua validação por meio de casos de uso estruturados em duas características da
rede, eMBB e mMTC, aplicados a duas verticais: “Agro” e “Campus”. Essa estratégia
aproveita as similaridades entre aplicações dentro de cada característica, otimizando o
esforço de desenvolvimento. A instalação concentrada das RUs no campus da UFPA em
Belém permitirá experimentos contínuos e de longa duração na vertical “Campus”, enquanto
os casos de uso da vertical “Agro” possibilitarão a validação e o refinamento da
Rede-5G-Green e da Solução-ORAN-Green em condições reais de operação rural.
Esta estratégia habilita o desenvolvimento na vigência deste projeto de 2 aplicações
inovadoras voltadas para  dois casos de uso distintos:  a aplicação App1-Vigilância voltada
para a vigilância do campus por vídeo e IA (eMBB), e a aplicação App2-Monitoramento
voltada para o monitoramento ambiental e do solo utilizando uma rede de sensores no
campus (mMTC).  Em todos casos, será exercida atenção especial à segurança cibernética,
desde o projeto das aplicações até suas validações.
As inovações tecnológicas associadas
aos casos de uso se organizam em torno de dois eixos principais: economia de energia em
eMBB e redução de custo em mMTC. A primeira problemática é bem conhecida e a maioria
das publicações científicas usam simulações ou fazem testes em cenários onde o consumo
de energia é minimizado apenas através da ação de desligar oportunisticamente algumas
gNBs (Mobile base stations). Além dessas técnicas tradicionais, este projeto irá inovar por
reduzir o consumo através da economia de PRBs ativos, e no uso de técnicas de IA como
aprendizado por reforço (ou RL), combinadas com slicing (Nahum, 2023) e orquestração
inteligente dos slices (Silva, 2025)
Neste contexto, um diferencial do projeto é a variedade dos dispositivos a serem usados, os
quais dão suporte a distintos entregáveis, assim como permitem estressar a rede com
padrões de tráfego realistas. Isso permitirá explorar as vantagens do uso de Open RAN e
IA, gerando aplicações do interesse da sociedade brasileira. A Figura 3 contém alguns dos
dispositivos, cujo uso é detalhado nos pacotes de trabalho (PTs). O projeto leva em conta
que atualmente há limitações na diversidade e custo de dispositivos 5G, e desenvolve
“gateways” customizados
denominados BR5G-Gateways, além de configurar modems FWA
(Fixed Wireless Access), tal como o da Intelbras que suporta ambos 5G e WiFi para uso nas
aplicações.


Figura 3 - Aplicações propostas enfatizando os dispositivos a serem usados nos casos de uso,
incluindo comerciais e os que serão desenvolvidos pela equipe do projeto, como o baseado em SDR
para coleta de dados de sensores.
Na aplicação App1-Vigilância, o campus da UFPA-Belém será transformado em um “Living
Lab” para monitoramento da segurança pública, utilizando a Rede-5G-Green otimizada pela
Solução-ORAN-Green para redução do consumo de energia. O tráfego das câmeras de alta
definição, instaladas em áreas críticas do campus, representará uma alta carga para a
Rede-5G-Green. As informações de todas as câmeras serão transmitidas via 5G. As faces
de pessoas serão anonimizadas usando IA para garantir a privacidade e preservação da
identidade de estudantes no campus. A aplicação App1-Vigilância utilizará AI para detecção
de casos de violência no campus, como agressões e assaltos. Utilizaremos modelos de IA e
banco de dados disponíveis na literatura para aperfeiçoamento do modelo que será utilizado
no campus, detectando as poses e movimentações de interesse que possuem alta
probabilidade de estarem associadas a atos violentos. No caso de suspeita de ato violento,
a aplicação retirará a anonimização da face da suspeita de envolvidos em atos violentos e
emitirá um alerta para o responsável da segurança para avaliação da situação, tornando o
sistema de monitoramento mais efetivo. Como requisito de integração da aplicação com a
infraestrutura Open RAN temos a necessidade de garantia de alta taxas de dados, dado
que cada câmera 4K com H.256 requer em média 25 Mbps, e uma garantia de latência
abaixo de 100 ms da rede para garantir que atos violentos sejam identificados rapidamente
e a equipe de segurança do campus obtenha a informação no menor tempo possível. A
aplicação será validada com a encenação de atos violentos pelo campus que deverão ser
detectados assim como o monitoramento de métricas de rede para garantia dos requisitos
de taxa de dados e latência.
Na aplicação App2-Monitoramento voltada para os  casos de uso “Agro” e “Campus
inteligente”, as informações coletadas através de sensores IoT espalhados pelo campus,
incluindo sensores localizados no solo em regiões de vegetação, serão transmitidas pela
Rede-5G-Green para avaliarmos, em condições reais, tanto a conectividade 5G da
Solução-ORAN-Green quanto o monitoramento das métricas obtidas pelos sensores em

tempo real. Para habilitar esta aplicação,  ampliaremos o ecossistema de dispositivos 5G
comumente utilizados com o uso de equipamentos RedCap, a possibilidade de transmissão
via satélite, por meio de soluções como da Skylo, e a utilização de gateways IoT
BR5G-Gateways integrados com pontos de acesso 5G, explorando soluções que aumentem
o número de dispositivos conectados e que sejam adequados para ambientes rurais. Dessa
forma, quando sensores ou dispositivos IoT não dispuserem de conectividade 5G nativa,
utilizaremos dispositivos 5G FWA com WiFi, ou desenvolveremos um “gateway” dedicado
(BR5G-Gateways). Dessa forma, a App2-Monitoramento permitirá que o projeto explore
tecnologias que ampliem o uso de Open RAN e 5G em ambientes rurais, tanto no
monitoramento ambiental quanto no agronegócio, onde alguns dos principais desafios para
mMTC nesse contexto são a baixa diversidade de equipamentos com rádio 5G e relativo
alto custo.  Como requisitos para eficaz  integração com a infraestrutura Open RAN, temos
a necessidade de reduzido consumo de potência dos nós sensores e alcance adequado,
além da otimização da taxa de transmissão às necessidades de cada sensor. Todos esses
requisitos devem ser alcançados com baixo custo, para viabilizar aumento de escala em
experimentos com mMTC. Algumas das pesquisas possíveis são pautadas em
experimentos para controle de parâmetros da rede que diminuam as probabilidades de erro
de transmissão de pacotes, como por exemplo a fixação de valores de MCS baixos, e o
ajuste dinâmico de recursos utilizados pelo slice de mMTC dadas características de coleta
intermitente da maioria dos sensores. A aplicação será validada através do grau de sucesso
no estabelecimento de conectividade com diversos sensores distintos e do monitoramento
de parâmetros como a taxa de perda de pacotes nas transmissões efetuadas por sensores,
assim como o consumo de energia e a utilização da rede pelos sensores nos tempos
programados.


- Descrição da proposta de Aplicação 5G Open RAN

7.1. Cronograma do Plano de Trabalho

PT/Atividade
## 2026 2027
## 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24
PT1: Aplicação 5G Open RAN: xAPPs, rApps, Agentic-AI-Green e interface de usuário
Entregáveis do PT1
## E1.1        E1.2
## E1.3
## /
## E1.4
## /
## E1.5

## Atividade 1.1 -
Habilitar o controle
de PRBs por slice

## Atividade 1.2 -
Habilitar o controle
de potência de
transmissão

## Atividade 1.3 -
Habilitar o
desligamento de
células e “layers”
de SDM

## Atividade 1.4 -
## Expandir /
implementar as
coletas de métricas
de KPM

## Atividade 1.5 -
Desenvolver o xApp
de RAN slicing

## Atividade 1.6 -
Desenvolver o xApp


de economia de
energia
## Atividade 1.7 -
Desenvolver o rApp
de otimização de
recursos

## Atividade 1.8 -
Desenvolver os
Agentic-AI-Green e
interface

## Atividade 1.9 -
Integração das
aplicações Open
RAN e
Agentic-AI-Green
com as aplicações
dos casos de uso

## Atividade 1.10 -
Desenvolvimento de
Mecanismos de
Defesa contra
Ataques de Evasão
em xApps

PT2: Casos de Uso eMBB: visão computacional e análise por inteligência artificial em tempo real
Entregáveis do PT2
## E2.1    E2.2    E2.5    E2.3
## Atividade 2.1 -
Instalação e
conexão das
câmeras 5G e das
Wi-Fi a RUs e a
modems FWA no
Campus UFPA
## Belém


## Atividade 2.2 -
Criação de “data
lake” para
armazenamento dos
vídeos obtidos com
as câmeras e LiDAR

## Atividade 2.3 -
Desenvolvimento de
métodos de IA e
visão
computacional para
detecção de casos
de violência

## Atividade 2.4 -
Integração de
aplicações de caso
de uso com a rede
Open RAN

PT3: Casos de Uso mMTC: Redes de sensores e dispositivos IoT
Entregáveis do PT3
## E3.1    E3.3    E3.2
## Atividade 3.1 -
Montagem de
sensores e
integração com
módulos de
conectividade 5G

## Atividade 3.2 -
Instalação dos
sensores no
campus
universitário e


conexão com a rede
5G Open RAN
## Atividade 3.3 -
Habilitar o envio de
métricas de
sensores para o
“data lake”

## Atividade 3.4 -
## Desenvolver
aplicação para
monitoramento e
geração de alertas
de monitoramento
ambiental no
campus
universitário

## Atividade 3.5 -
Integração de
aplicações de caso
de uso com a rede
Open RAN

PT4: Governança: coordenação, impacto, gestão estratégica e disseminação
Entregáveis do PT4
## E4.2    E4.2    E4.2    E4.2    E4.2  E4.1
## E4.2 /
## E4.3
## Atividade 4.1 –
Estratégias de
Projeto e
## Coordenação

## Atividade 4.2 –
Definição e
implantação de
ferramentas e
processos de
gestão


## Atividade 4.3 –
Redação dos
relatórios
físico-financeiros

## Atividade 4.4 -
Divulgação de
resultados



7.2. Descrição dos Pacotes de Trabalho
Número do Pacote de Trabalho PT1
Nome do Pacote de Trabalho Aplicação 5G Open RAN: xAPPs, rApps,
Agentic-AI-Green e interface de usuário
Duração do Pacote de Trabalho M1-M24
Instituição Responsáveis: UFPA, UNICAMP, UFRGS e Aveiro

O objetivo deste pacote de trabalho é investigar e desenvolver xApps, rApps,
Agentic-AI-Green e interfaces de usuários para a Rede-5G-Green que darão suporte às
aplicações voltadas aos casos de uso. Estas aplicações serão desenvolvidas no escopo
da execução dos pacotes de trabalho PT2 e PT3.

As ações deste PT1 estão distribuídas em diferentes domínios da rede: CU/DU, Near-RT
RIC através de xApps, Non-RT RIC através de rApps e Agent-AI-OpenRAN,  e também
no domínio do operador de rede através do Agent-AI-Usuário e interface. Como objetivos
específicos do PT1, temos o desenvolvimento das seguintes funcionalidades:

O1.1 - Habilitar o controle de funções e leitura de dados na aplicação de código aberto do
CU/DU. Mais especificamente, objetiva-se: a) habilitar o controle da alocação de PRBs
para diferentes slices da rede, b) o controle de potência de alocação para diferentes UEs,
c) o controle do desligamento de RUs e d) “layers” (camadas) ao se usar “spatial division
multiplexing” (SDM), assim como e) a coleta de informações via KPM.
O1.2 - Desenvolvimento das xApps de controle de recursos de RAN slicing e economia
de energia.
O1.3 - Desenvolvimento da rApp de otimização de recursos.
O1.4 - Desenvolvimento do Agentic-AI-Green e interface de usuário para definição de
intenções de rede e tradução de objetivos em políticas para o rApp.
O1.5 - Propor e implementar métodos de hardening (proteção) para aumentar a robustez
e resiliência dos modelos de Aprendizado de Máquina (ML) utilizados nas xApps e rApps,
mitigando ameaças externas como ataques de evasão e exemplos adversariais.

Descrição das Atividades:

Atividade 1.1 - Habilitar o controle de PRBs por slice - M1-M4 (Instituição
Responsável: UFPA)
A atividade têm o objetivo de expandir/implementar a função de controle de alocação de
PRBs por slices na plataforma responsável por implementar a função de CU/DU (usando,
por exemplo, a pilha do OpenAirInterface ou do srsRAN).
Atende ao objetivo O1.1.

Atividade 1.2 - Habilitar o controle de potência de transmissão - M1-M4 (Instituição
Responsável: UFPA)
A atividade têm o objetivo de habilitar o controle de potência alocada para cada PRB no
downlink e para cada usuário no uplink no código da plataforma de CU/DU.
Atende ao objetivo O1.1.


Atividade 1.3 - Habilitar o desligamento de células e “layers” de SDM - M1-M4
(Instituição Responsável: UFPA)
A atividade têm o objetivo de avaliar e habilitar os mecanismos de controle de
desligamento de RUs e “layers” em SDM na plataforma de CU/DU.
Atende ao objetivo O1.1.


Atividade 1.4 - Expandir / implementar as coletas de métricas de KPM  - M1-M4
(Instituição Responsável: UFPA)
A atividade têm o objetivo de avaliar o atual estado de implementação da coleta de
métricas de KPM nos softwares disponíveis na ilha, e eventualmente modificá-los para
garantir que as métricas necessárias para os xApps estarão disponíveis.
Atende ao objetivo O1.1.


Atividade 1.5 - Desenvolver o xApp de RAN slicing - M4-M8 (Instituição
Responsável: UFRGS)
A atividade consiste no desenvolvimento de xApp xApp1-RANSlicer que interaja com a
função de controle de alocação de PRBs para diferentes slices (desenvolvida na
Atividade 1.1) através da interface E2. Este xApp implementará política de alocação
baseada em método de aprendizado de máquina / inteligência artificial (ML/AI) para
balanceamento dos recursos alocados de acordo com os requisitos de cada slice.
Atende ao objetivo O1.2.

Atividade 1.6 - Desenvolver o xApp de economia de energia - M4-M12 (Instituição
Responsável: UFPA)
A atividade consiste no desenvolvimento de xApp xApp2-EnergySaver que interaja com
as funções de controle de alocação de potência e desligamento de células e “layers” em
SDM. O xApp implementará política baseada em ML/AI para diminuir a potência alocada
para slices menos prioritários em momentos oportunos ou diminuir a energia geral
utilizada em momentos de baixa demanda da rede.
Atende ao objetivo O1.2.

Atividade 1.7 - Desenvolver o rApp de otimização de recursos - M12-M20
(Instituição Responsável: UFRGS)
A atividade consiste no desenvolvimento de rApp rApp-ResourceOptimizer que será o
responsável por coordenar a alocação de PRBs e de energia através da interação com os
xApps de RAN slicing e economia de energia (GOMES, 2025). O rApp coordena as ações
dos xApps de forma a cumprir com os requisitos definidos para cada slice enquanto
minimiza o consumo de energia em momentos oportunos, tal como instantes de baixa
carga na rede.
Atende ao objetivo O1.3.

Atividade 1.9 - Desenvolver os Agentic-AI-Green e interface - M8-M20 (Instituição
## Responsável: Unicamp)
A atividade consiste no desenvolvimento de Agentic-AI-Green capazes de interagir com o
usuário operador da rede através de uma interface, interpretando as intenções de rede
expressas em linguagem natural e as traduzindo para requisitos de rede e comandos
previamente definidos para comunicação com o rApp.
Atende ao objetivo O1.4.

Atividade 1.10 - Integração das aplicações Open RAN e Agentic-AI-Green com as
aplicações dos casos de uso - M20-M24 (Instituição Responsável: UFPA)
A atividade consiste na integração de todas as aplicações desenvolvidas à
Rede-5G-Green, de forma a testar na prática as funcionalidades de otimização de
recursos da rede, priorização de slices e interação com os Agentic-AI-Green.
Atende aos objetivos O1.2, O1.3 e O1.4.

Atividade 1.11 - Desenvolvimento de Mecanismos de Defesa contra Ataques de
Evasão em xApps - M4-M20  (Instituição Responsável: UFPA)

Esta atividade foca em projetar e implementar técnicas de proteção de modelos de
aprendizado de máquina contra ataques de evasão. Um dos objetivos é também
introduzir defesas ativas para detectar e isolar inputs maliciosos que possam desviar o
comportamento dos modelos, garantindo a robustez contra ataques adversariais.
Atende aos objetivos O1.6

Papel das Envolvidas:
## UFPA
A equipe da UFPA irá participar ativamente do desenvolvimento dos 2 xApps e 1 rApp
que compõem a Solução-ORAN-Green e do arcabouço com soluções de segurança.
Estas atividades também incluem o desenvolvimento do Agentic-AI-Green e a
incorporação das técnicas de segurança cibernética para as aplicações Open RAN. A
UFPA também irá articular o desenvolvimento desta solução com as instituições parceiras
que já vêm atuando em Open RAN: UNICAMP, UFRGS e Univ. de Aveiro. Apesar de não
possuírem atuação direta nos entregáveis do PT1, através das atividades do PT4
(descrito a seguir), as outras instituições da região norte do país (UNIFESSPA, UEPA e
UFRA) receberão treinamento em Open RAN e seus participantes serão convidados a
treinarem equipes em suas instituições e acompanharem o desenvolvimento da
Solução-ORAN-Green no PT1.

## UNICAMP
Colaborará com as atividades relacionadas à implementação do Agentic-AI-Green e
interface de usuário para interpretação de intenções de rede expressas através de
linguagem natural pelo usuário operador da rede.

## UFRGS
Colaborará com as atividades relacionadas ao controle e implementação de RAN slicing e
otimização de recursos, desenvolvimento de xApp e rApp, assim como a integração das
aplicações desenvolvidas com a Rede-5G-Green.

Universidade de Aveiro
Colaborará com a expansão das métricas de KPM coletadas através das interfaces E2,
incluindo métricas sobre o canal, e métricas de interesse para os xApps e rApps de
economia de energia,  e RAN slicing.
## Entregáveis:

E1.1 - Código da CU/DU para habilitar controle de funções e coleta de informações
via E2 (M1-M4)
Código da plataforma open-source CU/DU com as funcionalidades que habilitam o
controle de alocação de PRBs, potência de transmissão, desligamento de células e
“layers”, e a coleta de métricas de KPM e CSI-RS.

E1.2 - Código das xApps de RAN slicing e economia de energia (M4-M12)
Código da implementação das xApps responsáveis por fazer o controle de RAN slicing
através da alocação de PRBs e economia de energia com o desligamento de células e
## “layers”.

E1.3 - Código da rApp de otimização de recursos  (M12-M20)
Código da implementação da rApp responsável pela otimização de recursos nos domínios
de alocação de PRBs e economia de energia,.

E1.4 - Código dos Agentic-AI-Green e interface de usuário (M8-M20)

Código dos Agentic-AI-Green utilizados tanto no Non-RT RIC quanto no domínio do
usuário operador da rede e a interface usada para comunicação utilizando linguagem
natural com esses agentes.


E1.5 - Relatório com detalhes da integração e validação do arcabouço de segurança
## (M4-M20)
Este entregável consolidará os resultados técnicos da atividade A1.11. O relatório
detalhará a eficácia dos mecanismos de defesa contra ataques de evasão de modelos de
aprendizado de máquina (com taxas de falsos positivos/negativos).


Número do Pacote de Trabalho PT2
Nome do Pacote de Trabalho Caso de Uso eMBB: visão computacional e
análise por inteligência artificial em tempo
real para vigilância do campus
Duração do Pacote de Trabalho M1-M24
Instituição Responsáveis: UFPA e UEPA

O objetivo deste pacote de trabalho é investigar e desenvolver a aplicação
App1-Vigilância voltada para a vigilância do campus por vídeo e IA (eMBB) . Como
câmeras de vídeo de alta resolução, usadas para o monitoramento, demandam taxas de
bits elevadas, o caso de uso apresenta características de aplicações eMBB, necessitando
de suporte da Solução-ORAN-Green pois os tráfegos gerados no experimento superarão
a capacidade instalada da rede. A operação se dá em tempo real com suporte da
Solução-ORAN-Green. O aplicativo App1-Vigilância utilizará câmeras de alta definição
espalhadas pelo campus e conectadas à Rede-5G-Green para capturar  vídeos e então
aplicar métodos de IA em tempo real para detectar possíveis situações de violência no
campus, como assaltos e agressões. As imagens onde não são detectadas atitudes
suspeitas passarão por uma etapa de anonimização das faces das pessoas para evitar
problemas de privacidade.  Como objetivos específicos deste plano de trabalho temos:

O2.1 - Instalação de infraestrutura de câmeras no campus UFPA Belém em locais
estratégicos para vigilância e monitoramento de situações de violência no campus.
O2.2 - Desenvolvimento de aplicação com métodos de IA para detecção de casos de
violência através da análise de vídeos oriundos das câmeras.


Descrição das Atividades:

Atividade 2.1 - Instalação e conexão das câmeras 5G e das Wi-Fi a RUs e a modems
FWA no Campus UFPA Belém - M9-M10 (Instituição Responsável: UFPA)
A atividade têm o objetivo de implementar as câmeras no campus UFPA e conectá-las à
Rede-5G-Green de forma direta no caso das câmeras 5G ou através dos modems FWA
no caso das câmeras Wi-Fi.
Atende ao objetivo O2.1.

Atividade 2.2 - Criação de “data lake” para armazenamento dos vídeos obtidos com
as câmeras - M4-M8 (Instituição Responsável: UEPA)
A atividade têm o objetivo de implementar um banco de dados para armazenamento e
gerenciamento dos vídeos obtidos para as câmeras que serão utilizados para treinamento
dos modelos de IA.

Atende ao objetivo O2.1.

Atividade 2.3 - Desenvolvimento de métodos de IA e visão computacional para
detecção de casos de violência - M1-M20 (Instituição Responsável: UFPA)
A atividade têm o objetivo de investigar e desenvolver métodos de IA e visão
computacional para a detecção de casos de violência no campus. Exploraremos o
treinamento utilizando tanto datasets disponíveis na literatura quanto datasets compostos
a partir dos vídeos das câmeras instaladas pelo projeto.
Atende ao objetivo O2.2.

Atividade 2.4 - Integração de aplicações de caso de uso com a Rede-5G-Green -
M20-M24 (Instituição Responsável: UFPA)
A atividade consiste na integração das aplicações de caso de uso desenvolvidas no PT2
com a Rede-5G-Green. As aplicações de caso de uso devem se comunicar através da
Rede-5G-Green em tempo real com desempenho satisfatório para que as análises e
inferências sejam realizadas de forma otimizada. Os experimentos permitirão aperfeiçoar
a Solução-ORAN-Green, ao mesmo tempo que se busca melhorar o desempenho das
aplicações em si.
Atende ao objetivo O2.2.

Papel das Envolvidas:
## UFPA
A equipe da UFPA irá se responsabilizar primariamente pelas ações relacionadas ao
desenvolvimento de métodos de IA para detecção de casos de violência no campus
universitário, na administração dos recursos da Rede-5G-Green.

## UEPA
A UEPA colaborará na criação de “data lake” para armazenamento dos vídeos obtidos
com as câmeras, na coleta de dados utilizando os câmeras de alta definição e no
processamento das imagens obtidas pelas câmeras para detecção de casos de violência
no campus.

## Entregáveis:
E2.1 - Código de implementação de data lake (M4-M8)
O código de instalação e configuração do data lake para armazenamento das
informações obtidas da Rede-5G-Green através das câmeras e demais dados produzidos
pela rede.

E2.2 - Relatório de infraestrutura de monitoramento e vigilância via rede 5G
## (M9-M12)
A instalação da infraestrutura contendo as câmeras e modems FWA 5G conectadas a
Rede-5G-Green para transmissão em tempo real das imagens obtidas.

E2.3 - Código de método de IA e visão computacional para detecção de casos de
violência  (M1-M20)
Código da implementação do método desenvolvido para detecção de casos de violência
utilizando imagens de câmeras em tempo real.

Número do Pacote de Trabalho PT3
Nome do Pacote de Trabalho Casos de Uso mMTC: Redes de sensores e
dispositivos IoT para monitoramento
ambiental e do solo

Duração do Pacote de Trabalho M1-M24
Instituição Responsáveis: UFPA, UNIFESSPA, Embrapa, UFRA

O objetivo deste pacote de trabalho é investigar e desenvolver a aplicação
App2-Monitoramento voltada para o monitoramento ambiental e do solo utilizando uma
rede de sensores no campus (mMTC)”. A aplicação apresenta  características de
aplicações mMTC, necessitando da conexão com múltiplos dispositivos e sensores com
tráfego de pacotes relativamente baixo.

A abordagem adotada para a pesquisa com mMTC, em especial com foco na redução de
custo, requer contextualização adequada. Os sensores e dispositivos IoT com suporte a
5G são atualmente de custo elevado. Esta é uma das razões pelas quais não há testbeds
ou plataformas experimentais que habilitem experimentos com número elevado de
dispositivos 5G. Atualmente, só há relato de “deployment” de mMTC com centenas ou
milhares de dispositivos por parte de operadoras, as quais distribuem, por exemplo,
medidores de energia em área relativamente vasta. Atualmente há vários esforços para
baratear o custo de IoT para 5G (GLOBAL TD-LTE INITIATIVE, 2025), (GSMA, 2025).

Em dezembro de 2024 o 3GPP estabeleceu um “working item” em A-IoT (“ambient IoT”),
o qual avançará o suporte existente na Release 19 para dispositivos capazes de “energy
harvesting” e que consomem
## 1
aproximadamente 1 μW. Os A-IoT (Butt, 2024) funcionam
como “tags” (similares ao RFID) e podem identificar uma planta, por exemplo.

Outro problema premente do uso do 5G no Agro 4.0 e na conectividade rural, em especial
em um país com as dimensões do Brasil, é o custo do backhaul em função das distâncias
envolvidas. Muitas das vezes, apenas a sede de um município é servida com fibra óptica,
mas não sua zona rural. Em muitos destes cenários, a comunicação NTN (“non-terrestrial
networks”) é uma alternativa promissora.

Na aplicação App2-Monitoramento, sensores voltados ao controle e análise do solo para
agricultura serão utilizados para fornecer informações-chave para inferência de qualidade
do solo. Serão exploradas as comunicações com sensores de medição de nutrientes do
solo, sensor de umidade, sensor de temperatura e sensor de condutividade elétrica. ,
Sensores voltados ao monitoramento ambiental no campus inteligente serão adotados
para fornecerem informações em tempo real sobre a qualidade do ar, ocorrência e
intensidade de chuva, níveis de radiação solar e temperatura. A partir da consolidação de
tais indicadores, a aplicação poderá, e.g., gerar relatórios, alertas e identificar anomalias.

O3.1 - Instalação de sensores e conectividade com Rede-5G-Green para monitoramento
de métricas em tempo real.
O3.2 - Investigação de diferentes tipos de conexão de sensores utilizando módulos 5G,
5G RedCap, e agregação com gateways 5G FWA.

O3.3 - Desenvolvimento de plataforma para visualização das métricas de monitoramento
ambiental e do solo.

Descrição das Atividades:

Atividade 3.1 - Montagem de sensores e integração com módulos de conectividade
5G - M4-M8 (Instituição Responsável: UNIFESSPA)
A atividade têm o objetivo de integrar os sensores utilizados para monitoramento do solo
no campo e monitoramento ambiental no campus universitário aos módulos de
## 1
Para comparação, apenas o rádio de um “smartphone”, quando transmite, consome em torno de 1 a 2 W, enquanto um
módulo NB-IoT (“low power”) tipicamente consome 100 a 200 mW.

conectividade de rede. Parte dos sensores se conectarão diretamente à rede 5G usando
o módulo padrão 5G, outra parte utilizará o módulo 5G RedCap (“reduced capacity”)
voltado para comunicações IoT, e o restante utilizará módulos LoRA conectados a um
gateway com conexão ao modem FWA 5G. Outros dispositivos a serem desenvolvidos e
integrados usarão NTN, com módulos como o da empresa Skylo. Enquanto alguns destes
sensores permanecerão conectados à Rede-5G-Green na UFPA em Belém, outros serão
testados nas instalações de parceiros como UFRA, Embrapa e campus da UFPA em
Castanhal. Após testes iniciais, os dispositivos serão conectados na Rede-5G-Green na
UFPA em Belém
Atende ao objetivo O3.1.

Atividade 3.2 - Instalação dos sensores no campus universitário e conexão com a
Rede-5G-Green - M9-M12 (Instituição Responsável: UFPA)
A atividade têm o objetivo de instalar os sensores e seus respectivos módulos de
conectividade em diferentes locais do campus, distribuindo os sensores de
monitoramento do solo em locais apropriados e similares às condições encontrados no
campo. Os sensores de monitoramento ambiental serão instalados em locais estratégicos
para coleta de seus respectivos indicadores.
Atende ao objetivo O3.1 e O3.2.

Atividade 3.3 - Habilitar o envio de métricas de sensores para o “data lake”  -
M12-M16 (Instituição Responsável: UNIFESSPA)
A atividade têm o objetivo de desenvolver mecanismo de coleta em tempo real das
métricas dos sensores para armazenamento no “data lake”, usando-se tanto sensores no
campus da UFPA de Belém quanto em locais disponibilizados pelos parceiros do projeto.
Atende ao objetivo O3.2 e O3.3.

Atividade 3.4 - Desenvolver aplicação para monitoramento e identificação de
anomalias - M1-M20 (Instituição Responsável: UFPA)
A atividade consiste no desenvolvimento de aplicação para processamento das
informações brutas obtidas pelos sensores e transformação dos dados em informações
úteis e de fácil entendimento a serem exibidas em uma plataforma de visualização.
Desenvolvimento de sistema de monitoramento ambiental e do solo.
Atende ao objetivo O3.3.

Atividade 3.5 - Integração de aplicações de caso de uso com a Rede-5G-Green -
M20-M24 (Instituição Responsável: UFPA)
A atividade consiste na integração das aplicações de caso de uso desenvolvidas no PT3
com a Rede-5G-Green. As aplicações de caso de uso devem se comunicar através da
Rede-5G-Green em tempo real com desempenho otimizado para que as análises e
inferências sejam realizadas de forma correta.
Atende ao objetivo O3.2 e O3.3.

Papel das Envolvidas:

## UFPA
De forma similar ao PT2, a equipe da UFPA irá se responsabilizar primariamente pelas
ações relacionadas ao desenvolvimento de administração da rede Rede-5G-Green e do
aplicativo App2-Monitoramento.

## UNIFESSPA
A UNIFESSPA será a líder do PT3 e também colaborará com a montagem e instalação
de sensores com conectividade 5G no campus universitário, o envio de informações dos
sensores para o “data lake”, no desenvolvimento de aplicação para o monitoramento de

métricas ambientais e de qualidade do solo e a integração das aplicações de caso de uso
com a Rede-5G-Green.

## Embrapa
A Embrapa atuará como consultora quanto aos requisitos e qualidade das aplicações
desenvolvidas. Assim, a Embrapa colaborará com o desenvolvimento da plataforma de
monitoramento ambiental e do solo através do levantamento de métricas-chave e
informações sobre transformação de dados dos sensores em informação útil e sua
interpretação.

## UFRA
A UFRA atuará como consultora quanto aos requisitos e qualidade das aplicações
desenvolvidas principalmente no âmbito de monitoramento ambiental, como na
identificação de comportamentos anômalos e métricas chave para monitoramento.

## Entregáveis:

E3.1 - Relatório sobre infraestrutura de monitoramento de sensores via rede 5G
## (M4-M12)
A instalação da infraestrutura contendo os sensores de monitoramento do solo e
monitoramento ambiental conectados a Rede-5G-Green para transmissão em tempo real
dos dados obtidos.


E3.2 - Código de aplicação para monitoramento ambiental e do solo  (M1-M20)
Código da implementação da aplicação App2-Monitoramento para monitoramento
ambiental e do solo no campus universitário em tempo real utilizando as informações
obtidas dos sensores.

E3.3 - Datasets com informações de monitoramento ambiental e do solo(M12-M16)
Dataset com os dados utilizados para treinamentos dos métodos de IA serão
disponibilizados publicamente para reprodução do treinamento dos métodos e
investigação de novas técnicas.



Número do Pacote de Trabalho PT4
Nome do Pacote de Trabalho Governança: coordenação, impacto, gestão
estratégica e disseminação
Duração do Pacote de Trabalho M1-M24
Instituição Responsáveis: UFPA
Objetivos do Pacote de Trabalho:

O objetivo deste pacote é realizar a gestão do projeto, cumprir as entregas de
documentação obrigatória e disseminar os resultados do projeto para a comunidade RNP,
especialistas e não especialistas.

O4.1 – Definir e aplicar as ferramentas de gestão do projeto, gestão de código/software e
máquina virtual.

O4.2 – Cumprir as entregas de documentação obrigatória (relatórios e Código-Fonte
## Final).


Número do Pacote de Trabalho PT4
O4.3 – Disseminar os resultados do projeto para a comunidade da RNP, bem como para
especialistas (conferências, workshops e periódicos) e não especialista (defesa civil,
mobilidade urbana, alunos de escolas públicas, empresas e governo), com atenção
especial à expansão do know-how em Open RAN dentre instituições parceiras do projeto,
com foco particular nas parceiras UNIFESSPA, UEPA e UFRA. Iniciando-se pelas
parceiras, almeja-se que o projeto difunda a tecnologia Open RAN em toda região norte
do país, assim como nas demais regiões e cause impacto também na comunidade
internacional.

Descrição das Atividades:

Atividade 4.1 – Estratégias de Projeto e Coordenação – M1-M24 (UFPA)
Compreende a avaliação contínua do andamento do projeto, bem como as reuniões de
orientação e ações gerenciais. Esta fase também contempla as ações para execução dos
fundos e bolsas do projeto.
Atende ao objetivo O4.1.

Atividade 4.2 – Definição e implantação de ferramentas e processos de gestão –
## M1-M2 (UFPA)
Definir e implantar canais de comunicação internos, bem como ferramentas de gestão de
projetos e gestão de código/software.
Atende ao objetivo O4.1.

Atividade 4.3 – Redação dos relatórios físico-financeiros – M1-M24 (UFPA)
Escrita e entrega dos relatórios de atividades quadrimestrais à RNP, informando os
avanços do projeto e a execução financeira.
Atende ao objetivo O4.2.

Atividade 4.4 - Divulgação de resultados - M4-M24 (UFPA)
Elaboração do Whitepaper com os resultados consolidados da aplicação, análise de
desafios e vantagens do 5G Open RAN. Elaboração de artigos científicos para publicação
em revistas e congressos científicos.
Atende ao objetivo O4.3.

Atividade 4.5 – Disponibilização do Código-Fonte Final – M23 -M24 (UFPA)
Finalização e disponibilização do código-fonte dos entregáveis (xApps/rApps, Agentes de
IA, adaptações de software OAI/srsRAN) no ambiente de desenvolvimento colaborativo
da RNP.
Atende ao objetivo O4.3.

Papel das Envolvidas:
## UFPA
Garantir a entrega dos produtos obrigatórios com a qualidade requerida, conforme os
prazos finais do edital, e atuar para que o projeto não só alcance impacto em sua duração
mas que tenha continuidade e permita absorção de know-how pela sociedade.

## Entregáveis:

E4.1 – Publicação de Whitepaper (M22)
Documento técnico com os resultados dos casos de uso, conforme o Item 9.i.viii do Edital.
Lista de publicações com resultados associados ao projeto.

E4.2 - Relatórios físico-financeiros quadrimestrais (M4, M8, M12, M16, M20, M24)

Número do Pacote de Trabalho PT4
Documentos de acompanhamento do projeto comparando o progresso físico (quantitativo
e de etapas) com o cronograma e o orçamento previstos.

E4.3 – Divulgação de Código Fonte da Solução (M24)
Repositório final do código-fonte completo da solução e dos xApps, rApps,
Agentic-AI-Green e demais softwares desenvolvidos.

7.3. Lista de Entregáveis

## Entregável
(Chave)
Nome do Entregável Pacote
de
## Trabalho
## Líder
(Sigla)
Tipo Mês de
## Entrega
E1.1 Código da CU/DU para habilitar
controle de funções e coleta de
informações via E2
## PT1 UFPA S M4
E2.1 Código de implementação de
data lake
## PT2 UEPA D M8
E1.2 Código das xApps de RAN slicing
e economia de energia
## PT1 UFPA S M12
E2.2 Relatório de infraestrutura de
monitoramento e vigilância via
rede 5G
## PT2 UFPA D M12
E3.1 Relatório sobre infraestrutura de
monitoramento de sensores via
rede 5G
## PT3 UNIFES
## SPA
## D M12
E3.3 Datasets com informações de
monitoramento ambiental e do
solo
## PT3 UNIFES
## SPA
## O M16
E1.3 Código das rApps de otimização
de recursos
## PT1 UFRGS S M20
E1.4 Código dos Agentic-AI-Green e
interface de usuário
## PT1 UNICA
## MP
## S M20
E1.5 Relatório com detalhes da
integração e validação do
arcabouço de segurança
## PT1 UFPA D M20
E2.3 Código de método de IA e visão
computacional para detecção de
casos de violência
## PT2 UFPA S M20
E3.2 Código de aplicação para
monitoramento ambiental e do
solo
## PT3 UFPA S M20
E4.1 Publicação de Whitepaper PT4 UFPA D M22
E4.2 Relatórios físico-financeiros
quadrimestrais
## PT4 UFPA D M4, M8,
## M12,
## M16,
## M20,
## M24
E4.3 Divulgação de Código Fonte da
## Solução
## PT4 UFPA S M24

## 8. Referências

## BUTT, M. M.; MANGALVEDHE, N. R.; PRATAS, N. K.; HARREBEK, J.; KIMIONIS, J.;
TAYYAB, M.; BARBU, O.–E.; RATASUK, R.; VEJLGAARD, B. Ambient IoT: A Missing Link in
3GPP IoT Devices Landscape. In: IEEE INTERNET OF THINGS MAGAZINE, v. 7, n. 2, p.
85-92, 2024. DOI: https://doi.org/10.1109/IOTM.001.2300198.
DIAS, Victor; SILVA, Murilo; GOMES, Matheus; BORGES, Lucas; RIKER, André; ABELÉM,
Antônio. Ataque Adversarial de Evasão a Sistema de Detecção de Intrusão e Métodos de
Defesa em Redes Open RAN. In: SIMPÓSIO BRASILEIRO DE CIBERSEGURANÇA
(SBSEG), 2025. DOI: https://doi.org/10.5753/sbseg.2025.11492.
ELKAEL, Maxime; D’ORO, Salvatore; BONATI, Leonardo; POLESE, Michele; LEE,
Yunseong; FURUEDA, Koichiro; MELODIA, Tommaso. AgentRAN: An Agentic AI
Architecture for Autonomous Control of Open 6G Networks. 2025. Disponível em:
https://arxiv.org/abs/2508.17778. Acesso em: 18 out. 2025.
ELYASI, Arman; ASHDOWN, Andrew; RUMMAN, K. M.; RESTUCCIA, Francesco. O-Ran
Xapps: Survey and Research Challenges. 2025. Disponível em:
https://ssrn.com/abstract=5236117. Acesso em: 18 out. 2025.
GLOBAL TD-LTE INITIATIVE (GTI). Passive IoT Typical Scenarios White Paper. In: GTI
WHITE PAPER, 2024. Disponível em:
https://www.gtigroup.org/Uploads/File/2024/02/23/u65d8351b5140d.pdf. Acesso em: 1 nov.
## 2025.
GOMES, Elen C. R. ; RODRIGUES, Lucas ; BEZERRA, Diego de Freitas ; SADOK, Djamel ;
GONÇALVES, Glauco. Machine Learning Models for Virtual Base Station Power
Consumption Estimation. In: XLIII Simpósio Brasileiro de Telecomunicações e
Processamento de Sinais, 2025. DOI: http://doi.org/10.14209/sbrt.2025.1571144356.
GSMA. 5G Case Study: 5G-Advanced to Support Self-Powered Sensors (Powerless
Sensors). In: 5G HUB WHITE PAPER, 2023. Disponível em:
https://www.gsma.com/5GHub/images/5G-Case-Study-Self-Powered-Sensors-full.pdf .
Acesso em: 1 nov. 2025.
HAIDER, U. et al. Network load prediction and anomaly detection using ensemble learning in
5G cellular networks. Computer Communications, v. 197, p. 141–150, jan. 2023.
ISLAM, T.; LEE, D.; LIM, S. S. Enabling Network Power Savings in 5G-Advanced and
Beyond. IEEE Journal on Selected Areas in Communications, v. 41, n. 6, p. 1888–1899, 8
maio 2023.
## KOUCHAKI, M.; NATANZI, S. B. H.; ZHANG, M.; TANG, B.; MAROJEVIC, V. O-RAN
Performance Analyzer: Platform Design, Development, and Deployment. IEEE
Communications Magazine, v. 63, n. 2, p. 152-159, fev. 2025.
NAGIB, A. M.; ABOU-ZEID, H.; HASSANEIN, H. S. SafeSlice: Enabling SLA-Compliant
O-RAN Slicing via Safe Deep Reinforcement Learning. Disponível em:
<https://arxiv.org/abs/2503.12753>. Acesso em: 23 out. 2025.

NAGIB, A. M.; HATEM ABOU-ZEID; HASSANEIN, H. S. Safe and Accelerated Deep
Reinforcement Learning-Based O-RAN Slicing: A Hybrid Transfer Learning Approach. IEEE
Journal on Selected Areas in Communications, v. 42, n. 2, p. 310–325, 28 nov. 2023.
NAHUM, Cleverson V.; D'ORO, Salvatore; BATISTA, Pedro; BOTH, Cristiano B.;
CARDOSO, Kleber V.; KLAUTAU, Aldebaro; MELODIA, Tommaso. Intent-based radio
scheduler for RAN slicing: Learning to deal with different network scenarios. IEEE
Transactions on Mobile Computing, [S. l.], 2025.
NAHUM, Cleverson Veloso; LOPES, Victor Hugo L.; DREIFUERST, Ryan M.; BATISTA,
Pedro; CORREA, Ilan; CARDOSO, Kleber Vieira; KLAUTAU, Aldebaro; HEATH, Robert W.
Intent-aware radio resource scheduling in a RAN slicing scenario using reinforcement
learning. IEEE Transactions on Wireless Communications, [S. l.], v. 23, n. 3, p. 2253-2267,
## 2023.
OLIVEIRA, Andrey A. Miranda de; ALBUQUERQUE, João Pedro; NAHUM, Cleverson
Veloso; CAMPOS, Daniel; CARDOSO, Kleber V.; KLAUTAU, Aldebaro; REZENDE, José F.
de. Enabling NS-3 Simulations Integrated with Latest Versions of Open RAN Near-RT RICs.
Anais do XLIII Simpósio Brasileiro de Telecomunicações e Processamento de Sinais, 2025.
DOI: https://doi.org/10.14209/sbrt.2025.1571157244.
## OLIVEIRA, LUCAS B; SILVA, MURILO ; MARQUES, D. A. L. ; ARAUJO, G. H. ; SCHWARZ,
Marcos F. ; FARIAS, Fernando N. N. ; BONDAN, L. ; GRANVILLE, L. Z. ; ABELEM, Antônio
J. G. . Advancing Open RAN Deployment and Management on the OpenRAN@Brasil
Testbed. In: IEEE Network Operations and Management Symposium, 2025. DOI:
https://doi.org/10.1109/NOMS57970.2025.11073589.
SANTOS, J. F.; HUFF, A.; CAMPOS, D.; CARDOSO, K. V.; BOTH, C. B.; DASILVA, L. A.
Managing O-RAN Networks: xApp Development From Zero to Hero. IEEE Communications
## Surveys & Tutorials, 2025.
SILVA, Murilo; OLIVEIRA, Lucas B.; DIAS, Victor; GOMES, Matheus; FARIAS, Fernando;
RIKER, André; ABELÉM, Antônio. Automatizando a Alocação de Usuários em Slices 5G em
Arquiteturas Open RAN. In: WORKSHOP DE GERÊNCIA E OPERAÇÃO DE REDES E
SERVIÇOS (WGRS), 2025. DOI: https://doi.org/10.5753/wgrs.2025.8865.

