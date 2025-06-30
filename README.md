# Sistema de Armazenamento Distribuído com Replicação e Sincronização de Arquivos

## Descrição do Projeto

Este projeto é parte de um trabalho acadêmico da disciplina de **Sistemas Distribuídos**. O objetivo é desenvolver um **sistema de arquivos distribuído**, inspirado em ferramentas como o **Google Drive**. O sistema permite que usuários realizem **upload, download, exclusão e sincronização** de arquivos, com foco em **alta disponibilidade** e **tolerância a falhas**, através da **replicação** e **sincronização** dos dados entre múltiplos servidores.

## Arquitetura

- **Dois servidores gerentes**: armazenam réplicas dos arquivos e sincronizam entre si automaticamente.
- **Um cliente**: realiza requisições aos servidores, monitora alterações locais e oferece interface web para acompanhamento e comandos.
- **Sincronização automática** entre servidores, garantindo consistência dos dados.
- **Escolha dinâmica** do servidor pelo cliente, considerando disponibilidade e resposta.
- **Interface web** para visualização do status, arquivos e mudanças pendentes.

## Tecnologias Utilizadas

| Tecnologia        | Finalidade                                         |
|-------------------|----------------------------------------------------|
| **Python**        | Linguagem principal do sistema                     |
| **watchdog**      | Monitoramento de mudanças em diretórios            |
| **Flask**         | APIs RESTful e interface web                       |
| **Flask-SocketIO**| Comunicação em tempo real com o frontend           |
| **requests**      | Comunicação HTTP entre servidores e cliente        |
| **eventlet**      | Suporte a WebSockets                               |
| **base64**        | Transferência segura de arquivos binários          |

## Estrutura do Projeto

```
GoogleDriveAtHome/
│
├── server.py            # Servidor: monitora, sincroniza e expõe APIs REST
├── user.py              # Cliente: monitora, sincroniza, interface web e API
├── requirements.txt     # Dependências do projeto
├── change_log.json      # Log local das alterações
├── test_chamber/        # Diretório monitorado e sincronizado
│   ├── TXT.txt
│   ├── novoteste.txt
│   └── ...
├── static/              # Arquivos estáticos da interface web
│   ├── app.js
│   └── style.css
├── templates/
│   └── index.html       # Interface web principal
└── README.md
```

## Como Executar o Projeto

### 1. Instale as dependências do Python

No terminal do VS Code, execute:
```bash
pip install -r requirements.txt
```

### 2. Inicie os servidores

Em dois computadores diferentes (ou portas diferentes), execute:
```bash
python server.py
```
- Configure o IP do peer em `PEER_ADDRESS` no início do [`server.py`](server.py).

### 3. Inicie o cliente

No computador cliente, execute:
```bash
python user.py
```
- O cliente abrirá um servidor Flask na porta 7000, com interface web e API.

### 4. Acesse a interface web

Abra no navegador:
```
http://localhost:7000/
```
- Visualize arquivos, mudanças pendentes, status de conexão e realize comandos de pull/push.

## APIs e Funcionalidades

### Servidor (`server.py`)

- `/get_full_state` (GET): Retorna o estado completo dos arquivos/diretórios monitorados.
- `/get_changes` (GET): Retorna mudanças desde um timestamp.
- `/push_change` (POST): Recebe e aplica uma mudança enviada pelo cliente.

### Cliente (`user.py`)

- `/api/status` (GET): Retorna status dos arquivos, mudanças pendentes e conexão.
- `/api/pull` (POST): Força sincronização do estado do servidor para o cliente.
- `/api/push` (POST): Envia mudanças pendentes do cliente para o servidor.
- Interface web em tempo real via SocketIO.

## Dependências

- Python 3.8+
- watchdog
- flask
- flask_socketio
- requests
- eventlet

Instale com:
```bash
pip install -r requirements.txt
```

## Exemplo de Documento no Log de Mudanças

```json
{
  "timestamp": "2025-05-31T10:10:27.793686",
  "type": "modified",
  "src": "test_chamber/TXT.txt",
  "is_directory": false
}
```

## Observações Importantes

- O sistema implementa filtro para evitar eventos duplicados em curto intervalo (0.5s) para o mesmo arquivo.
- O arquivo `change_log.json` é o log local das alterações.
- O cliente detecta automaticamente a disponibilidade dos servidores e tenta reconectar.
- Toda transferência de arquivo é feita via base64 para garantir integridade.
- O diretório monitorado é sempre `test_chamber`.

## Alunos

- **Heitor Vieira Macedo**
- **Henrique Rodrigues Lima**

## Tema Relacionado

**Sistemas de Arquivos Distribuídos**

## Status

Em desenvolvimento  
Pesquisando ferramenta de comunicação entre servidores

## Observações Futuras

- Melhorias na resolução de conflitos de arquivos.
- Interface web para upload/download direto.
- Suporte a múltiplos peers e balanceamento.
- Autenticação e controle de acesso.

---