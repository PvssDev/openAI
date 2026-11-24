# Plano Detalhado de Entregas — Incidente OpenAI (Dez/2024)

Este documento divide toda a atividade de SRE em **6 entregas estruturadas**, conectando cada requisito de [contexto-atividade.md](file:///c:/Users/pedro.vsouza/Desktop/pedro/git-team/openAI/docs/contexto-atividade.md) diretamente ao tema escolhido pela equipe: o incidente da **OpenAI de 11 de dezembro de 2024**, no qual um novo serviço de telemetria sobrecarregou o plano de controle do Kubernetes (`kube-apiserver`) e derrubou a descoberta de serviços via DNS.

- **Fonte oficial de referência:** https://status.openai.com/incidents/ctrsv3lwd797/write-up
- **Objetivo final:** Entregar um **Laudo Técnico em PDF (máximo 6 páginas)** e o **repositório Git** com `docker-compose.yml`, `logs/`, `README.md` e `IA.md`, cobrindo integralmente os 4,0 pontos da rubrica.

---

## Visão Geral da Relação entre o Tema e as Entregas

No incidente real da OpenAI:
1. Um **serviço de telemetria** foi implantado para coletar métricas do plano de controle do Kubernetes.
2. Por erro de configuração e custo operacional proporcional ao tamanho do cluster, todos os nós passaram a executar operações pesadas na **API do Kubernetes**, saturando os servidores de API (`kube-apiserver`).
3. O **cache de DNS** nos nós mascarou o problema inicialmente (servindo registros antigos), permitindo que o *rollout* continuasse além da fase canário.
4. Quando os registros em cache expiraram, os serviços não conseguiram mais resolver endpoints via DNS (porque o DNS/CoreDNS depende da API do Kubernetes), gerando **falha em cascata** em produtos como ChatGPT, API e Sora.
5. A recuperação foi dificultada porque o próprio plano de controle estava saturado, bloqueando comandos administrativos de *rollback* até que a carga fosse contida e o serviço revertido.

Cada entrega abaixo isola uma camada desse problema para garantir rigor técnico, rastreabilidade em `logs/` e fidelidade ao artigo oficial.

---

## Entrega 1 — Estudo do Incidente e Especificação do Mecanismo (Parte A do Laudo)

**Peso na rubrica:** 0,6 ponto (**A. Mecanismo e conceito**)  
**Destino final:** Seção **Parte A — O mecanismo** do Laudo Técnico (PDF).

### O que deve ser entregue
1. **Mecanismo do incidente em uma frase:**
   - Síntese objetiva da cadeia causal: *um serviço de telemetria mal configurado gerou operações pesadas proporcionais ao tamanho do cluster que saturaram a API do Kubernetes, impedindo a atualização de registros DNS após a expiração do cache local e derrubando a descoberta de serviços em cascata (além de dificultar o próprio rollback pelo plano de controle congestionado).*
2. **Linha do tempo localizada no artigo oficial (4 a 6 eventos):**
   - Cada evento deve citar explicitamente a **seção** ou o **horário** conforme publicado em `https://status.openai.com/incidents/ctrsv3lwd797/write-up` (ex.: implantação do serviço de telemetria por volta de 3:12 PM PST, início da degradação dos serviços às 3:16 PM PST, expiração do cache DNS em uma janela de ~20 minutos, bloqueio/dificuldade de mitigação via API, recuperação substancial por volta de 5:36–5:45 PM PST e resolução total às 7:38 PM PST — *todos os horários e seções exatos devem ser conferidos diretamente no texto oficial antes de fechar o PDF*).
3. **Vínculo justificado com um conceito da disciplina:**
   - Escolher **um** conceito dentre os listados na atividade (*condição de corrida, exclusão mútua, ponto único de falha, efeito manada, acoplamento ou consistência*) e justificar tecnicamente:
     - **Acoplamento** (entre plano de dados/descoberta de serviços por DNS e o plano de controle/API do Kubernetes, somado ao mascaramento por cache) **e/ou Efeito manada** (milhares de nós executando simultaneamente operações pesadas contra o mesmo `kube-apiserver` compartilhado, multiplicando a carga pelo tamanho do cluster).
     - Explicar *por que* esse conceito descreve a raiz estrutural do incidente e não apenas um sintoma superficial.

### Critérios de aceite e cuidados
- **Regra eliminatória:** qualquer citação, horário ou evento que não conste no artigo oficial **zera a Parte A**.
- Validar cada linha da linha do tempo diretamente contra o texto de `status.openai.com/incidents/ctrsv3lwd797/write-up`.

---

## Entrega 2 — Arquitetura e Implementação da Miniatura (Parte B + `docker-compose.yml`)

**Peso na rubrica:** 0,8 ponto (**B. Miniatura honesta**) + base para reprodutibilidade (**E**)  
**Destino final:** Arquivo `docker-compose.yml` (+ código-fonte dos serviços da miniatura no repositório) e seção **Parte B — A miniatura** do Laudo (PDF).

### O que deve ser entregue
1. **Ambiente Docker Compose funcional (mínimo 3 containers):**
   - Arquitetura sugerida com **4 containers** (ou 3, unificando o cliente/carga se necessário, mas 4 deixa os papéis cristalinos) conectados em rede Docker dedicada:
     1. `k8s-api` (simulador do `kube-apiserver`): mantém o catálogo de serviços/endpoints e possui capacidade limitada de processamento (ex.: *worker pool* / limite de concorrência / latência crescente sob sobrecarga).
     2. `dns-resolver` (simulador do CoreDNS / descoberta por DNS): consulta `k8s-api` para resolver nomes de serviço, mantém **cache local com TTL configurável** (reproduzindo a janela em que o cache mascara a falha) e passa a retornar erro (`SERVFAIL`/timeout) quando o TTL expira e a `k8s-api` não responde.
     3. `telemetry-agent` (simulador do serviço de telemetria): dispara requisições pesadas/intensivas em rajada ou *polling* contínuo contra a `k8s-api`, simulando o custo proporcional ao tamanho do cluster.
     4. `workload-client` (simulador de serviços/aplicações no plano de dados + gerador de carga): realiza requisições contínuas resolvendo o destino via `dns-resolver` e registra métricas em tempo real (latência, códigos HTTP/DNS, momento da primeira falha, recuperação).
2. **Diagrama de containers e redes:**
   - Diagrama claro mostrando os containers, as portas/protocolos e as dependências de rede (destacando a dependência oculta: `workload-client` -> `dns-resolver` -> `k8s-api`, disputando o mesmo recurso saturado por `telemetry-agent`).
3. **Tabela de correspondência (Miniatura × Sistema Real da OpenAI):**
   - Mapear explicitamente cada container e rede da miniatura para o componente equivalente no ambiente da OpenAI (ex.: `k8s-api` ↔ `kube-apiserver`; `dns-resolver` ↔ CoreDNS / cache DNS dos nós; `telemetry-agent` ↔ daemon/serviço de telemetria implantado nos nós; `workload-client` ↔ serviços como ChatGPT/API/Sora dependendo de DNS).
4. **Tabela de limitações honestas (mínimo 3 pontos específicos):**
   - Cada limitação deve indicar **o que não é reproduzido** e **qual o efeito disso nas conclusões**:
     - *Escala do cluster:* OpenAI operava milhares de nós e múltiplos clusters massivos, onde o custo escalava com o tamanho do cluster; na miniatura há poucos containers em uma única máquina, comprimindo tempos e volumes.
     - *Bloqueio operacional do rollback:* No caso real, engenheiros tiveram dificuldade até para reverter o *deploy* porque a própria API de administração estava saturada; na miniatura, o controle pode ser feito externamente via Docker Compose, subestimando o tempo de reação operacional.
     - *Heterogeneidade de caches e planos de dados:* Na nuvem real há múltiplos níveis de cache (node-local DNS, CoreDNS, clientes) e tráfego real de usuários, enquanto na miniatura o TTL e a carga são sintéticos e uniformes.
     - *Recursos reais de CPU/memória/etcd:* A `k8s-api` real é apoiada por `etcd` e múltiplas réplicas; o simulador abstrai persistência distribuída e contenção real de disco/rede.

### Critérios de aceite
- Subir com `docker compose up` sem passos manuais ocultos.
- Demonstrar claramente o **efeito de mascaramento pelo cache** seguido da **falha em cascata no DNS** quando o TTL expira sob saturação da API.

---

## Entrega 3 — Execução do Experimento, Coleta de Logs e Análise (Parte C + `logs/`)

**Peso na rubrica:** 1,2 ponto (**C. Experimento e evidências** — maior peso da rubrica)  
**Destino final:** Pasta `logs/` no repositório + seção **Parte C — O experimento** do Laudo (PDF).

### O que deve ser entregue
1. **Execução controlada do cenário de falha e salvamento de logs brutos em `logs/`:**
   - Registrar saídas completas e datadas (ex.: `logs/experimento-sem-mitigacao.log`, `logs/k8s-api.log`, `logs/dns-resolver.log`, `logs/workload-client.log` ou equivalente bem organizado).
2. **Medição obrigatória das 3 métricas (sempre apontando o arquivo de log exato):**
   - **Tempo até a falha:** tempo desde o início da sobrecarga pelo `telemetry-agent` até o momento em que o `workload-client` começa a falhar por expiração do cache DNS (ex.: indicando linha/timestamp no arquivo `logs/...`).
   - **Tempo até a recuperação:** tempo desde a interrupção/rollback do `telemetry-agent` até a normalização da `k8s-api` e restabelecimento da resolução DNS no `workload-client`.
   - **Porcentagem de requisições com erro:** total de requisições com erro dividido pelo total de requisições na janela medida (com os números exatos extraídos de `logs/...`).
3. **Comparação com o caso real da OpenAI:**
   - Comparar ordens de grandeza e dinâmica temporal: na miniatura, a falha é comprimida em segundos/minutos; na OpenAI, o cache DNS segurou por ~20 minutos antes da degradação ampla e a recuperação total levou ~4,5 horas (entre 3:16 PM e 7:38 PM PST). Explicar por que a curva de comportamento (platô estável -> queda abrupta após TTL -> recuperação gradual) se assemelha ou diverge.
4. **Parágrafo sobre comportamento inesperado ("a surpresa"):**
   - Documentar algo real que saiu diferente do previsto ao rodar os containers (por exemplo: demora maior do que a esperada para esvaziar filas/conexões abertas após parar a telemetria, comportamento de cache negativo no DNS, ou *timeouts* do cliente mantendo conexões presas) e explicar a causa técnica observada nos logs.

### Critérios de aceite
- **Regra eliminatória:** qualquer número citado no laudo que não apareça literalmente nos arquivos em `logs/` zera o critério C.

---

## Entrega 4 — Mitigação e Parecer para a Diretora (Parte D + `logs/`)

**Peso na rubrica:** 1,0 ponto (**D. Parecer e mitigação**)  
**Destino final:** Alteração/perfil mitigado no `docker-compose.yml`, logs em `logs/` e seção **Parte D — O parecer para a diretora** do Laudo (PDF).

### O que deve ser entregue
1. **Parecer de aplicabilidade no projeto da equipe na disciplina:**
   - Responder objetivamente à diretora de tecnologia se o mesmo mecanismo pode ocorrer no projeto da equipe.
   - **Indicar um arquivo e um trecho reais** do projeto da equipe (ex.: configuração de `docker-compose`, cliente HTTP sem *timeout*/*rate limit*, *healthcheck*, serviço de monitoramento/polling ou configuração de DNS/descoberta de serviços) onde esse padrão de acoplamento/sobrecarga poderia acontecer. *(Obs.: definir previamente com a equipe qual repositório/projeto da disciplina será analisado e extrair o caminho e trecho exatos).*
2. **Implementação de uma mitigação na miniatura:**
   - Escolher e implementar uma mitigação coerente com o incidente da OpenAI, por exemplo:
     - **Rate limiting / Backoff exponencial com jitter** no `telemetry-agent` e/ou proteção por *rate limit* / *circuit breaker* na `k8s-api` para preservar endpoints críticos (como o `dns-resolver`).
     - Ou **servir cache DNS expirado (*serve-stale*)** no `dns-resolver` quando a `k8s-api` estiver indisponível, desacoplando o plano de dados da falha temporária do plano de controle.
     - Ou **rollout em ondas / canary com janela superior ao TTL do DNS** e *healthcheck* que valida a saúde da API antes de expandir.
3. **Medição Antes × Depois (rastreável em `logs/`):**
   - Rodar o mesmo cenário de carga com a mitigação ativa e salvar as saídas brutas em `logs/` (ex.: `logs/experimento-com-mitigacao.log`).
   - Apresentar tabela comparativa **Antes vs. Depois** (tempo até a falha / se houve falha, tempo até recuperação, % de requisições com erro), referenciando os respectivos arquivos em `logs/`.

---

## Entrega 5 — Documentação de Reprodutibilidade e Uso de IA (`README.md` e `IA.md`)

**Peso na rubrica:** 0,4 ponto (**E. Reprodutibilidade e IA**)  
**Destino final:** Arquivos `README.md` e `IA.md` na raiz do repositório.

### O que deve ser entregue
1. **`README.md` completo para reprodução pelo professor:**
   - Pré-requisitos (Docker, Docker Compose).
   - Comandos exatos para subir a miniatura sem mitigação, acionar/observar a falha, coletar os logs em `logs/` e derrubar o ambiente.
   - Comandos exatos para rodar o cenário **com mitigação** e verificar a diferença nos logs.
   - Onde encontrar cada métrica citada no laudo dentro de `logs/`.
2. **`IA.md` transparente e auditável:**
   - Registro dos **3 a 5 prompts mais importantes** usados pela equipe durante o trabalho, detalhando em cada um:
     - o que foi **aceito**,
     - o que foi **mudado**,
     - o que foi **descartado**.
   - Descrição de **pelo menos 2 erros reais da IA** encontrados ao rodar o código ou validar o experimento (ex.: erro de rede/porta no Compose, bug no cálculo de TTL ou métrica, comando que não funcionava no container) e **a correção feita pela equipe**.

---

## Entrega 6 — Consolidação e Revisão Final do Laudo Técnico (PDF)

**Destino final:** Arquivo PDF do Laudo Técnico (máximo **6 páginas**) + link do repositório.

### Checklist final antes da entrega
- [ ] O PDF possui **no máximo 6 páginas** e contém as Partes **A, B, C e D** claramente identificadas.
- [ ] **Parte A:** Todas as citações, seções e horários constam literalmente em `https://status.openai.com/incidents/ctrsv3lwd797/write-up`.
- [ ] **Parte B:** Diagrama de containers/redes, tabela de correspondência real e tabela com ≥ 3 limitações específicas e seus efeitos.
- [ ] **Parte C:** Todo número citado (tempo até falha, tempo até recuperação, % de erro) existe em `logs/` e indica o arquivo correspondente; parágrafo sobre o comportamento inesperado incluído.
- [ ] **Parte D:** Arquivo e trecho **reais** do projeto da equipe citados; mitigação implementada na miniatura e medida antes e depois com logs em `logs/`.
- [ ] **Repositório:** Contém `docker-compose.yml`, `logs/`, `README.md` testado do zero e `IA.md` com 3–5 prompts e ≥ 2 erros corrigidos.
- [ ] **Higiene Git:** `docs/` e `.agents/` permanecem ignorados pelo `.gitignore` e não poluem o repositório final entregue.

---

## Matriz Resumo: Entregas × Arquivos × Rubrica

| Entrega | Foco Principal | Arquivos Gerados/Atualizados | Critério da Rubrica | Pontos |
| :--- | :--- | :--- | :--- | :---: |
| **Entrega 1** | Mecanismo, linha do tempo e conceito (OpenAI dez/2024) | Parte A do Laudo (PDF) | A. Mecanismo e conceito | 0,6 |
| **Entrega 2** | Miniatura Docker Compose, diagrama e limitações | `docker-compose.yml`, serviços, Parte B do Laudo | B. Miniatura honesta | 0,8 |
| **Entrega 3** | Execução, métricas em `logs/`, comparação e surpresa | `logs/*`, Parte C do Laudo | C. Experimento e evidências | 1,2 |
| **Entrega 4** | Parecer no projeto real + mitigação medida antes/depois | `docker-compose.yml` (mitigação), `logs/*`, Parte D | D. Parecer e mitigação | 1,0 |
| **Entrega 5** | Passo a passo reproduzível + registro crítico de IA | `README.md`, `IA.md` | E. Reprodutibilidade e IA | 0,4 |
| **Entrega 6** | Revisão de integridade, rastreabilidade e limite de 6 pág. | Laudo Final (PDF) + Repositório | Todos (auditoria final) | **4,0** |

