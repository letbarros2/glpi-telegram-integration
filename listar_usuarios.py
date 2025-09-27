import requests
import json

# Configurações
GLPI_URL = "http://192.168.1.46/apirest.php/"
APP_TOKEN = "iy8ttWAgfDxnjcbCXVdrOwzFsKi6nuu1RIbXePdk"
USER_TOKEN = "yxfcuuRsayXp52T4c2Ig4wZeKkYXCcCRVsR51COz"  # Pode ser o do super-admin para teste

def iniciar_sessao():
    url = f"{GLPI_URL}initSession"
    headers = {
        "App-Token": APP_TOKEN,
        "Authorization": f"user_token {USER_TOKEN}"
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()["session_token"]

def listar_usuarios(session_token):
    url = f"{GLPI_URL}User"
    headers = {
        "App-Token": APP_TOKEN,
        "Session-Token": session_token
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    try:
        token = iniciar_sessao()
        usuarios = listar_usuarios(token)

        print("=== Lista de usuários e campos extras ===")
        for u in usuarios:
            print(json.dumps(u, indent=4, ensure_ascii=False))
    except Exception as e:
        print("Erro:", e)
