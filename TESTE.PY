import requests
import logging

# Configurações (mesmas do bot)
GLPI_URL = "http://192.168.1.46/apirest.php/"
APP_TOKEN = "iy8ttWAgfDxnjcbCXVdrOwzFsKi6nuu1RIbXePdk"
LOG_FILE = "glpi_test_vinculo.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)


def test_user_chatid(chat_id):
    try:
        # Inicializa sessão do bot
        r = requests.get(
            f"{GLPI_URL}initSession",
            auth=("glpibot1", "r3d3.ti33"),
            headers={"App-Token": APP_TOKEN},
            timeout=10,
        )
        r.raise_for_status()
        bot_session = r.json().get("session_token")
        logging.info(f"Sessão do bot criada com sucesso para teste")

        # Buscar usuários
        r = requests.get(
            f"{GLPI_URL}User",
            headers={"App-Token": APP_TOKEN, "Session-Token": bot_session},
            params={"limit": 100},
            timeout=10,
        )
        r.raise_for_status()
        users = r.json()

        user_found = None
        for u in users:
            fields = u.get("fields", {})
            for key, value in fields.items():
                if str(value) == str(chat_id):
                    user_found = u
                    break
            if user_found:
                break

        if user_found:
            logging.info(f"✅ Usuário encontrado para chat_id {chat_id}: {user_found.get('name')}")
            if user_found.get("api_token"):
                logging.info(f"Usuário tem API token configurado: {user_found.get('api_token')[:6]}...")
            else:
                logging.warning("⚠ Usuário não possui API token configurado")
        else:
            logging.warning(f"❌ Nenhum usuário vinculado ao chat_id {chat_id}")

    except Exception as e:
        logging.error(f"Erro ao testar chat_id {chat_id}: {e}")


if __name__ == "__main__":
    # Teste com chat_ids que você quer verificar
    test_user_chatid(5478754716)
    test_user_chatid(1634722412)
