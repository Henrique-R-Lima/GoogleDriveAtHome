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

| Tecnologia      | Finalidade                                         |
|-----------------|----------------------------------------------------|
| **Python**      | Linguagem principal do sistema                     |
| **watchdog**    | Monitoramento de mudanças em diretórios            |
| **MongoDB**     | Armazenamento dos eventos de alteração             |
| **pymongo**     | Driver Python para MongoDB                         |
| **requests**    | Comunicação HTTP (se necessário)                   |
| **Flask**       | (Futuro) APIs RESTful para comunicação             |

---

## 📁 Estrutura de Código

O repositório inclui três scripts com funcionalidades semelhantes que monitoram alterações em diretórios:

### `file_watcher.py`, `directory_state.py`, `enhanced_watchdog.py`

Todos esses scripts:

- Utilizam a biblioteca `watchdog` para monitorar um diretório chamado `test_chamber`.
- Capturam e registram eventos como **criação, modificação, exclusão e movimentação** de arquivos e diretórios.
- Geram um arquivo `change_log.json` que armazena os eventos em formato JSON.

---

## 📁 Estrutura do Projeto

```
GoogleDriveAtHome/
│
├── directory_state.py         # Script principal de monitoramento e registro de eventos
├── mongo_config.py            # Configuração da conexão com o MongoDB
├── requirements.txt           # Dependências do projeto
├── change_log.json            # Log local das alterações (opcional)
├── test_chamber/              # Diretório monitorado
│   └── ...                    # Arquivos e subpastas monitorados
└── README.md
```

---

## 🚀 Como Executar o Projeto

### 1. Instale o MongoDB

- Baixe e instale o MongoDB Community Server: https://www.mongodb.com/try/download/community
- Inicie o serviço do MongoDB:
    - Se instalado como serviço:  
      `net start MongoDB`
    - Ou execute o `mongod.exe` manualmente.

### 2. Instale as dependências do Python

No terminal do VS Code, execute:
```bash
pip install -r requirements.txt
```

### 3. Configure o acesso ao MongoDB

Verifique o arquivo `mongo_config.py`:
```python
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "google_drive_at_home"
```

### 4. Execute o monitoramento

No terminal, execute:
```bash
python directory_state.py
```

### 5. Faça alterações no diretório monitorado

- Adicione, edite, mova ou exclua arquivos na pasta `test_chamber`.
- Os eventos serão registrados no arquivo `change_log.json` e na collection `events` do MongoDB.

### 6. Visualize os eventos no MongoDB

#### Usando o terminal:
```bash
mongosh
use google_drive_at_home
db.events.find().pretty()
```

#### Usando o MongoDB Compass:
- Abra o Compass e conecte em `mongodb://localhost:27017/`
- Navegue até o banco `google_drive_at_home` e veja a collection `events`.

---

## 📦 Dependências

Para executar os scripts de monitoramento, instale as dependências principais com:

```bash
pip install -r requirements.txt
```

---

## 📚 Exemplo de Documento na Collection `events`

```json
{
  "_id": "ObjectId",
  "timestamp": "2025-05-31T10:10:27.793686",
  "type": "modified",
  "src": "test_chamber/TXT.txt",
  "is_directory": false
}
```

---

## 💡 Observações Importantes

- O sistema implementa um filtro para evitar eventos duplicados em curto intervalo de tempo (0.5s) para o mesmo arquivo.
- O MongoDB cria automaticamente o banco e a collection ao inserir o primeiro evento.
- O arquivo `change_log.json` é mantido como log local, mas o MongoDB é a fonte principal dos eventos.
- Para evitar duplicidade de eventos, o sistema ignora eventos idênticos para o mesmo arquivo em menos de 0.5 segundo. Se quiser ajustar esse tempo, altere o valor em `directory_state.py` na linha:
  ```python
  if now - last_time < 0.5:
      return
  ```

---

## 👨‍💻 Alunos

- **Heitor Vieira Macedo**
- **Henrique Rodrigues Lima**

---

## 📚 Tema Relacionado

**Sistemas de Arquivos Distribuídos**

---

## ✅ Status

🟡 Em desenvolvimento  
🔍 Pesquisando ferramenta de comunicação entre servidores

---

## 📌 Observações Futuras

Este repositório corresponde à **etapa de monitoramento e sincronização local**. Em fases futuras do projeto, serão adicionados:

- APIs RESTful com Flask
- Lógica de replicação e consistência entre servidores
- Interface de cliente para interação com o sistema

---