# Análise e Reprodução SRE — Incidente OpenAI (Dez/2024)

Repositório dedicado ao estudo, reprodução em miniatura (Docker Compose), medição e mitigação do mecanismo central do incidente da **OpenAI de dezembro de 2024**, no qual um serviço de telemetria sobrecarregou a API do Kubernetes e derrubou a descoberta de serviços por DNS.

- **Fonte oficial do incidente:** [OpenAI Status — Incident Write-up](https://status.openai.com/incidents/ctrsv3lwd797/write-up)

---

## Objetivo da Atividade

Atuando como equipe de confiabilidade (SRE), o trabalho consiste em:

1. **Analisar o incidente real:** mapear o mecanismo central, a linha do tempo baseada no relato oficial e o conceito de sistemas distribuídos/confiabilidade associado.
2. **Reproduzir em miniatura (Docker Compose):** simular com pelo menos 3 containers o mecanismo central da falha (efeito cascata, sobrecarga de plano de controle e impacto na descoberta de serviços por DNS).
3. **Executar e medir:** coletar métricas brutas em `logs/` (tempo até a falha, tempo até a recuperação e porcentagem de requisições com erro), comparando os resultados com o incidente real.
4. **Propor e validar mitigação:** implementar uma mitigação na miniatura (ex.: *backoff* com *jitter*, *healthcheck*, limite validado ou *rollout* em ondas), medir o antes e o depois, e emitir parecer técnico sobre aplicabilidade no projeto da equipe.

---

## Estrutura do Repositório

- `docker-compose.yml` — definição dos containers e redes da miniatura do incidente *(em desenvolvimento)*
- `logs/` — saídas brutas das execuções citadas no laudo técnico *(em desenvolvimento)*
- `IA.md` — registro dos 3 a 5 prompts mais importantes e de pelo menos 2 erros da IA encontrados e corrigidos durante a execução *(em desenvolvimento)*
- `README.md` — documentação e passo a passo para reprodução do experimento

---

## Entregáveis Previstos

### Laudo Técnico (PDF, máx. 6 páginas)
- **Parte A — O mecanismo:** resumo do mecanismo em uma frase, linha do tempo (4 a 6 eventos com seção/horário do artigo oficial) e vínculo justificado com conceito da disciplina.
- **Parte B — A miniatura:** diagrama de containers e redes, tabela de correspondência com o sistema real e tabela com pelo menos 3 limitações específicas e seus efeitos nas conclusões.
- **Parte C — O experimento:** medições de tempo até a falha, tempo até a recuperação e porcentagem de requisições com erro, todas rastreáveis aos arquivos em `logs/`, além da análise de comportamento inesperado.
- **Parte D — O parecer para a diretora:** avaliação de risco no projeto da equipe (indicando arquivo e trecho reais) e implementação de mitigação na miniatura com comparação antes e depois.

---

## Como Reproduzir o Experimento

> *Seção em construção: o passo a passo completo com os comandos `docker compose` para subir a miniatura, reproduzir a falha, coletar os logs em `logs/` e testar a mitigação será adicionado após a implementação do `docker-compose.yml`.*

