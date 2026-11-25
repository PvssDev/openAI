# Registro de Uso de IA (`IA.md`)

Este arquivo registra os principais prompts usados pela equipe com a IA durante o trabalho sobre o incidente da OpenAI (dez/2024), o que foi aceito, mudado ou descartado em cada etapa, e os erros reais da IA encontrados ao rodar o código.

---

## Principais Prompts Utilizados

### 1. Organização do projeto em entregas com base no incidente da OpenAI (dez/2024)
- **Prompt resumido:** Pedimos para dividir toda a atividade em entregas separadas, conectando cada entrega ao incidente escolhido (OpenAI, dez/2024) e aos critérios da rubrica.
- **O que foi aceito:** A divisão em 6 entregas (Parte A teórica, Miniatura em Docker Compose, Experimento com logs, Mitigação e Parecer, README/IA e Revisão do PDF) e o uso da fonte oficial `status.openai.com/incidents/ctrsv3lwd797/write-up`.
- **O que foi mudado:** Ajustamos o `.gitignore` para ignorar apenas `docs/local/` (em vez de ignorar toda a pasta `docs/`), permitindo versionar o plano geral e o contexto da atividade.
- **O que foi descartado:** Nenhuma parte foi descartada nessa etapa.

### 2. Criação da miniatura em Docker Compose e rascunho das Partes A e B do laudo
- **Prompt resumido:** Pedimos para implementar a Entrega 2 com Docker Compose simulando o mecanismo do incidente e gerar o rascunho inicial do laudo em Markdown.
- **O que foi aceito:** A arquitetura com 4 containers leves em Python (`k8s-api`, `dns-resolver` com cache TTL de 12s, `telemetry-agent` e `workload-client`) conectados em uma rede Docker própria (`openai-sim-net`), sem depender de bibliotecas externas.
- **O que foi mudado:** Os textos iniciais das Partes A e B foram revisados depois no Prompt 4 para ficarem mais simples e fáceis de ler.
- **O que foi descartado:** A ideia de inventar/simular registros fictícios no `IA.md` foi descartada para manter transparência total com as regras da atividade e usar apenas erros reais encontrados nos testes.

### 3. Execução da Entrega 3 com testes automatizados e script de coleta de logs
- **Prompt resumido:** Pedimos para avançar na Entrega 3 sempre criando testes para validar o comportamento real da miniatura.
- **O que foi aceito:** A criação do teste de integração em `tests/test_miniatura.py` e do script `scripts/run_experiment.py` para automatizar a coleta dos arquivos em `logs/` e calcular as métricas diretamente dos logs brutos.
- **O que foi mudado:** Ao rodar o teste automatizado, encontramos 2 bugs reais no código gerado pela IA (descritos abaixo), que foram corrigidos antes de prosseguir.
- **O que foi descartado:** Nenhuma parte foi descartada.

### 4. Simplificação da linguagem do laudo e implementação da mitigação (Entrega 4)
- **Prompt resumido:** Pedimos para reescrever os textos com linguagem simples e direta de estudante (sem jargões desnecessários) e implementar a mitigação da Entrega 4 testando localmente.
- **O que foi aceito:** A correção do texto que estava com linguagem robusta demais (deixando o laudo e o `README.md` mais diretos e fáceis de ler), além da criação de `docker-compose.mitigado.yml` com `SERVE_STALE=true` no `dns-resolver` e `BACKOFF_JITTER=true` no `telemetry-agent`.
- **O que foi mudado:** Os campos de métricas reais (Parte C e tabela Antes × Depois da Parte D) e o trecho do projeto da equipe foram mantidos como marcadores `[PREENCHER]` até a execução final no Docker Compose, garantindo que nenhum número seja inventado.
- **O que foi descartado:** Expressões excessivamente técnicas como "não linearidade de clusters massivos", "contenção em disco" e "tempestades de retry".

---

## Erros Reais da IA Encontrados ao Rodar o Código e Correções

### Erro 1 — Deadlock no `k8s-api` por fazer escrita de log e resposta HTTP dentro de `queue_lock`
- **Onde aconteceu:** `services/k8s_api/server.py` (na primeira versão gerada pela IA).
- **Como foi descoberto:** Ao rodar `python -m unittest discover -s tests -v`, o teste `test_cache_masks_overload_then_fails_and_recovers` travou na etapa de recuperação e falhou após `28.334s` com `AssertionError: dns-resolver did not recover after stopping telemetry-agent`.
- **Causa do erro:** A IA colocou `print(..., flush=True)` e `self._send_json(503, ...)` dentro do bloco `with queue_lock:`. Sob alta carga, quando a saída de log bloqueava ou uma conexão fechava no meio, a thread segurava o `queue_lock` e impedia todas as outras requisições (inclusive a recuperação do `dns-resolver`) de avançarem.
- **Correção feita:** Liberamos o `queue_lock` antes de chamar `print()` e `self._send_json()`, guardando apenas o estado booleano `overloaded`, e adicionamos tratamento para `BrokenPipeError` e `ConnectionResetError` no envio da resposta HTTP.

### Erro 2 — Travamento por buffer cheio no `subprocess.PIPE` ao rodar os testes no Windows
- **Onde aconteceu:** `tests/test_miniatura.py` (na primeira versão gerada pela IA).
- **Como foi descoberto:** Na mesma execução do teste automatizado no Windows, o processo `k8s-api` produziu centenas de linhas de `503 OVERLOADED` em poucos segundos e travou sem responder mesmo depois de encerrar o `telemetry-agent`.
- **Causa do erro:** A IA abriu os subprocessos no teste com `stdout=subprocess.PIPE`, mas não consumia a saída do pipe em nenhuma thread. No Windows, o buffer do pipe é pequeno (4 KB); quando encheu, o `k8s-api` bloqueou na escrita de `stdout`.
- **Correção feita:** Trocamos o redirecionamento nos subprocessos do teste para `stdout=subprocess.DEVNULL` e `stderr=subprocess.DEVNULL`. Após as duas correções, o teste passou em `6.215s` (e a suíte completa com o teste da mitigação passou em `9.414s`, `OK`).

### Erro 3 — Cálculo errado do tempo de recuperação por diferença de relógio entre Windows e Docker
- **Onde aconteceu:** `scripts/run_experiment.py` (ao rodar o experimento real no Docker Desktop no Windows).
- **Como foi descoberto:** Na primeira execução de `python scripts/run_experiment.py sem-mitigacao`, o resumo mostrou `time_to_recovery_s=68.33` mesmo com o container voltando a responder em poucos segundos, e o horário `rollback_ts` (`11:49:42`) apareceu anterior ao `flood_start_ts` (`11:50:22`).
- **Causa do erro:** A IA pegou o horário do rollback usando `datetime.now()` do Windows, enquanto os logs dos serviços usavam o relógio interno da máquina virtual Linux do Docker (WSL2), que estava ~66 segundos adiantado.
- **Correção feita:** Adicionamos a função `container_ts()` em `scripts/run_experiment.py`, que lê o horário direto de dentro do container `k8s-api` (`docker compose exec -T k8s-api ...`) no momento do rollback. Depois da correção, o tempo de recuperação ficou coerente com os logs (`2,52s`).

