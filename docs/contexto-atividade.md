# Contexto e Missão da Atividade

Vocês são a equipe de confiabilidade (SRE) de uma empresa que roda tudo em containers na nuvem. A diretora de tecnologia leu sobre um incidente famoso e quer saber se isso pode acontecer com a empresa.

A equipe vai escrever um laudo técnico sobre um incidente real, apoiado em um experimento rodado por vocês:
1. Escolher um artigo da lista ou propor outro oficial. Cada artigo pode ser escolhido por no máximo duas equipes.
2. Reproduzir em miniatura, com Docker Compose, o mecanismo central do incidente.
3. Medir, comparar com o caso real e escrever o laudo.

O que precisa aparecer na miniatura é o mecanismo do incidente: a condição de corrida, o efeito cascata, a falta de limite ou o ponto único de falha. Três containers bastam, desde que rodem e mostrem esse mecanismo.

## Incidente Escolhido (Fonte Oficial)

- **OpenAI, dez/2024:** um serviço de telemetria sobrecarregou a API do Kubernetes e derrubou a descoberta de serviços por DNS.
- **Link oficial:** https://status.openai.com/incidents/ctrsv3lwd797/write-up

---

## Entregáveis

Laudo em PDF, com no máximo 6 páginas, e o link do repositório.

### Parte A — O mecanismo
- O mecanismo do incidente em uma frase.
- Uma linha do tempo com 4 a 6 eventos, cada um com a seção ou o horário do artigo onde aparece.
- Ligar o caso a um conceito da disciplina (condição de corrida, exclusão mútua, ponto único de falha, efeito manada, acoplamento ou consistência) e explicar por que é esse conceito.

### Parte B — A miniatura
- Um diagrama dos containers e das redes.
- Uma tabela com o que cada container representa no sistema real.
- Uma tabela com pelo menos 3 pontos específicos que a miniatura não reproduz e o efeito de cada um nas conclusões.

### Parte C — O experimento
- Rodar a miniatura e medir:
  - tempo até a falha;
  - tempo até a recuperação;
  - porcentagem de requisições com erro.
- Comparar o que observaram com o que o artigo relata.
- Cada número indica o arquivo de log de onde saiu.
- Escrever também um parágrafo sobre algo que saiu diferente do esperado e a explicação que encontraram.

### Parte D — O parecer para a diretora
- Responder se isso pode acontecer com o projeto da equipe na disciplina, indicando o arquivo e o trecho onde o mesmo mecanismo poderia aparecer.
- Implementar na miniatura uma mitigação (backoff com jitter, healthcheck, limite validado, rollout em ondas ou outra) e medir o resultado antes e depois.

---

## Estrutura do Repositório

- `docker-compose.yml`
- pasta `logs/` com as saídas brutas das execuções citadas no laudo
- `README.md` com o passo a passo para o professor rodar
- `IA.md` com o registro de uso de IA

---

## Uso de IA

Vocês podem usar IA para ler o artigo, escrever código e revisar o texto. O que a equipe observou no experimento precisa vir das execuções de vocês.
- O `IA.md` registra os 3 a 5 prompts mais importantes e o que a equipe aceitou, mudou ou descartou em cada um.
- O `IA.md` descreve pelo menos 2 erros da IA que vocês encontraram ao rodar o código e a correção feita.
- Um número do laudo que não aparece em `logs/` será considerado inventado e zera o critério em que aparece.
- Uma citação que não existe no artigo zera a Parte A.

---

## Rubrica (4,0 pontos)

- **A. Mecanismo e conceito (0,6):** mecanismo correto, linha do tempo localizada no artigo e conceito justificado.
- **B. Miniatura honesta (0,8):** correspondência coerente entre peças reais e containers; 3 ou mais limitações específicas com o efeito discutido.
- **C. Experimento e evidências (1,2):** métricas medidas e comparadas com o caso real; todo número rastreável em `logs/`; a surpresa explicada.
- **D. Parecer e mitigação (1,0):** indica um arquivo e um trecho reais do projeto da equipe; mitigação medida antes e depois.
- **E. Reprodutibilidade e IA (0,4):** seguindo o `README.md`, o professor consegue subir a miniatura e reproduzir a falha; `IA.md` com 2 ou mais erros corrigidos.
- **Nota parcial:** 50% do critério quando o requisito aparece incompleto ou com alguma inconsistência.

