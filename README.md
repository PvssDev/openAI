# Análise e Reprodução — Incidente da OpenAI (Dez/2024)

Repositório do trabalho prático sobre o incidente da **OpenAI de dezembro de 2024**, quando um serviço de telemetria sobrecarregou a API do Kubernetes e derrubou a descoberta de serviços por DNS.

- **Artigo oficial do incidente:** [OpenAI Status — Incident Write-up](https://status.openai.com/incidents/ctrsv3lwd797/write-up)

---

## Objetivo da Atividade

1. **Entender o incidente real:** explicar como o problema aconteceu, montar a linha do tempo com base no texto oficial e ligar o caso a um conceito da disciplina.
2. **Montar uma miniatura em Docker Compose:** simular o problema com containers simples que mostram a API travando, o cache de DNS segurando por um tempo e a falha acontecendo quando o cache vence.
3. **Rodar e medir:** salvar as saídas reais em `logs/` (tempo até falhar, tempo até recuperar e % de requisições com erro) e comparar com o caso da OpenAI.
4. **Testar uma correção:** aplicar uma melhoria na miniatura para evitar ou diminuir o problema, medir antes e depois, e avaliar se isso poderia acontecer no projeto da equipe.

---

## Estrutura do Repositório

- `docker-compose.yml` — define os 4 containers e a rede da miniatura
- `services/` — código em Python dos serviços simulados (`k8s-api`, `dns-resolver`, `telemetry-agent` e `workload-client`)
- `scripts/run_experiment.py` — script para rodar o experimento e salvar os logs
- `tests/test_miniatura.py` — teste automatizado do fluxo de falha e recuperação
- `logs/` — saídas brutas das execuções usadas no laudo *(em andamento)*
- `IA.md` — registro dos prompts usados e dos erros da IA encontrados e corrigidos *(em andamento)*
- `README.md` — passo a passo para rodar tudo

---

## Como Reproduzir o Experimento

> *Passo a passo completo com os comandos finais será atualizado assim que concluirmos a coleta dos logs e a versão com correção (Entregas 3, 4 e 5).*
