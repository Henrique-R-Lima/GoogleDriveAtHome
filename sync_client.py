import os
import requests
import base64
from pathlib import Path

# ==================== CONFIG ====================

# Endereço do servidor (pode ser A ou B)
SERVER_URL = "http://localhost:5000"  # Altere para o IP real de A ou B

# Pasta local onde os downloads serão salvos
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ==================== FUNÇÕES ====================

def listar_arquivos():
    try:
        resp = requests.get(f"{SERVER_URL}/get_full_state", timeout=5)
        resp.raise_for_status()
        state = resp.json()
        arquivos = [f for f in state if not f["is_directory"]]

        print("\nArquivos disponíveis:")
        for idx, item in enumerate(arquivos):
            print(f"[{idx}] {item['path']}")

        return arquivos
    except Exception as e:
        print(f"Erro ao listar arquivos: {e}")
        return []

def baixar_arquivo(arquivos, idx):
    try:
        item = arquivos[idx]
        nome = os.path.basename(item["path"])
        conteudo = base64.b64decode(item["content"])
        destino = DOWNLOAD_DIR / nome

        with open(destino, "wb") as f:
            f.write(conteudo)

        print(f"Arquivo '{nome}' salvo em '{destino}'")
    except Exception as e:
        print(f"Erro ao baixar arquivo: {e}")

def enviar_arquivo():
    caminho = input("Digite o caminho do arquivo a enviar: ").strip()
    if not os.path.isfile(caminho):
        print("Arquivo não encontrado.")
        return

    rel_path = os.path.basename(caminho)
    try:
        with open(caminho, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "path": rel_path,
            "content": content,
            "is_directory": False
        }
        resp = requests.post(f"{SERVER_URL}/upload", json=payload, timeout=5)
        if resp.status_code == 200:
            print("Arquivo enviado com sucesso!")
        else:
            print(f"Erro ao enviar arquivo: {resp.text}")
    except Exception as e:
        print(f"Erro ao ler/enviar arquivo: {e}")

# ==================== INTERFACE ====================

def menu():
    while True:
        print("\nMenu:")
        print("1. Listar arquivos")
        print("2. Baixar arquivo")
        print("3. Enviar arquivo")
        print("0. Sair")

        op = input("Escolha uma opção: ").strip()
        if op == "1":
            global lista_cache
            lista_cache = listar_arquivos()
        elif op == "2":
            if not lista_cache:
                print("Nenhum arquivo listado ainda.")
                continue
            idx = input("Digite o número do arquivo: ").strip()
            if idx.isdigit() and 0 <= int(idx) < len(lista_cache):
                baixar_arquivo(lista_cache, int(idx))
            else:
                print("Índice inválido.")
        elif op == "3":
            enviar_arquivo()
        elif op == "0":
            print("Encerrando...")
            break
        else:
            print("Opção inválida.")

# ==================== INÍCIO ====================

if __name__ == "__main__":
    lista_cache = []
    menu()
