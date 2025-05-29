# Sistema de Armazenamento Distribuído com Replicação e Sincronização de Arquivos

## 📄 Descrição do Projeto

Este projeto é parte de um trabalho acadêmico da disciplina de **Sistemas Distribuídos**. O objetivo é desenvolver um **sistema de arquivos distribuído**, inspirado no funcionamento de ferramentas como o **Google Drive**. O sistema permitirá que usuários realizem **upload, download e exclusão** de arquivos, com foco em **alta disponibilidade** e **tolerância a falhas**, através da **replicação** e **sincronização** dos dados entre múltiplos servidores.

## 🖥️ Arquitetura Proposta

- Dois computadores atuando como **servidores gerentes**, responsáveis por armazenar réplicas dos arquivos.
- Um computador atuando como **cliente**, que fará requisições aos servidores.
- **Sincronização automática** entre os servidores, garantindo a consistência dos dados.
- **Escolha dinâmica** do servidor a ser utilizado, considerando:
  - Frescor dos dados
  - Tempo de resposta
  - Disponibilidade

A replicação e a comunicação entre servidores serão implementadas com um **mecanismo de troca de mensagens**, que está em fase de definição.

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Finalidade |
|------------|------------|
| **Python** | Linguagem principal do sistema |
| **Flask**  | Construção de APIs para comunicação entre cliente e servidores |
| **watchdog** | Monitoramento de mudanças em diretórios |
| **Armazenamento local** | Persistência de arquivos nos servidores |
| *(A definir)* | Sistema de troca de mensagens entre servidores |

---

## 📁 Estrutura de Código

O repositório inclui três scripts com funcionalidades semelhantes que monitoram alterações em diretórios:

### `file_watcher.py`, `directory_state.py`, `enhanced_watchdog.py`

Todos esses scripts:

- Utilizam a biblioteca `watchdog` para monitorar um diretório chamado `test_chamber`.
- Capturam e registram eventos como **criação, modificação, exclusão e movimentação** de arquivos e diretórios.
- Geram um arquivo `change_log.json` que armazena os eventos em formato JSON.

#### Funcionamento básico:

```bash
$ python file_watcher.py
```

O terminal passará a exibir em tempo real os eventos detectados, e os registros serão salvos no `change_log.json`.

---

## 👨‍💻 Alunos

- **Heitor Vieira Macedo**
- **Henrique Rodrigues Lima**

---

## 📚 Tema Relacionado

**Sistemas de Arquivos Distribuídos**

---

## 📦 Dependências

Para executar os scripts de monitoramento, instale a dependência principal com:

```bash
pip install watchdog
```

---

## ✅ Status

🟡 Em desenvolvimento  
🔍 Pesquisando ferramenta de comunicação entre servidores

---

## 📌 Observações

Este repositório corresponde à **etapa de monitoramento e sincronização local**. Em fases futuras do projeto, serão adicionados:

- APIs RESTful com Flask
- Lógica de replicação e consistência entre servidores
- Interface de cliente para interação com o sistema
