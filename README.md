# Análise e Reprodução — Incidente da OpenAI (Dez/2024)

Repositório do trabalho prático sobre o incidente da **OpenAI de dezembro de 2024**, quando um serviço de telemetria sobrecarregou a API do Kubernetes e derrubou a descoberta de serviços por DNS.

- **Artigo oficial do incidente:** [OpenAI Status — Incident Write-up](https://status.openai.com/incidents/ctrsv3lwd797/write-up)

---

## Pré-requisitos

- **Docker** e **Docker Compose** (v2+) instalados e com o daemon ativo.
- **Python 3.10+** (apenas para rodar o script de coleta de logs e os testes automatizados; não precisa instalar bibliotecas externas).

---

## Estrutura do Repositório

- `docker-compose.yml` — miniatura no cenário **sem mitigação** (reproduz a falha).
- `docker-compose.mitigado.yml` — arquivo extra que ativa a **mitigação** (`SERVE_STALE=true` no DNS e `BACKOFF_JITTER=true` na telemetria).
- `services/` — código Python dos 4 containers:
  - `services/k8s_api/server.py` — simula a API do Kubernetes com limite de atendimento.
  - `services/dns_resolver/server.py` — simula o DNS com cache de 12 segundos.
  - `services/telemetry_agent/agent.py` — simula o serviço de telemetria gerando carga pesada.
  - `services/workload_client/client.py` — simula os aplicativos consultando o DNS a cada 0,5s.
- `scripts/run_experiment.py` — automatiza a execução, simula o rollback (`stop telemetry-agent`), salva os logs em `logs/` e calcula as métricas.
- `tests/test_miniatura.py` — testes automatizados dos cenários sem e com mitigação.
- `logs/` — saídas brutas das execuções citadas no laudo.
- `IA.md` — registro dos prompts mais importantes e dos erros reais da IA encontrados e corrigidos.

---

## Como Reproduzir o Experimento

### 1. Rodar o cenário SEM mitigação (reproduzir a falha)

Usando o script automatizado (recomendado — sobe os containers, aguarda 36s, para o `telemetry-agent`, aguarda 15s de recuperação, salva tudo em `logs/` e derruba o ambiente):

```bash
python scripts/run_experiment.py sem-mitigacao
```

Ou manualmente com Docker Compose:

```bash
docker compose up -d
# Aguarde ~35s para ver o cache vencer e os erros 503 no workload-client
docker compose logs -f workload-client
# Em outro terminal, simule o rollback parando a telemetria:
docker compose stop telemetry-agent
# Salve os logs brutos e encerre:
docker compose logs --no-color > logs/sem-mitigacao-all.log
docker compose down
```

Os arquivos gerados pelo script ficam em:
- `logs/sem-mitigacao-workload-client.log` (cada requisição com timestamp, status e latência)
- `logs/sem-mitigacao-dns-resolver.log`
- `logs/sem-mitigacao-k8s-api.log`
- `logs/sem-mitigacao-telemetry-agent.log`
- `logs/sem-mitigacao-all.log`
- `logs/sem-mitigacao-resumo.txt` (métricas calculadas diretamente dos logs)

### 2. Rodar o cenário COM mitigação (antes × depois)

Usando o script automatizado:

```bash
python scripts/run_experiment.py com-mitigacao
```

Ou manualmente com Docker Compose:

```bash
docker compose -f docker-compose.yml -f docker-compose.mitigado.yml up -d
docker compose -f docker-compose.yml -f docker-compose.mitigado.yml logs -f workload-client
docker compose -f docker-compose.yml -f docker-compose.mitigado.yml down
```

Os arquivos gerados ficam em `logs/com-mitigacao-*.log` e `logs/com-mitigacao-resumo.txt`.

### 3. Rodar os testes automatizados (sem precisar do Docker)

```bash
python -m unittest discover -s tests -v
```
