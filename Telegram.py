# Configurações GLPI
GLPI_URL = "http://192.168.1.46/apirest.php"
APP_TOKEN = "iy8ttWAgfDxnjcbCXVdrOwzFsKi6nuu1RIbXePdk"
USER = "glpibot1"
PASSWORD = "r3d3.ti33"

# Configurações Telegram
TELEGRAM_BOT_TOKEN = "8233082568:AAH-3bcfmpRn_ORqHhJF54lsduEfz9w1CjU"
INTERVALO_VERIFICACAO = 20
ARQUIVO_ESTADO = "estado_tickets_v2.json"
LOG_FILE = "glpi_monitor_v2.log"
MAX_TICKETS = 50

# Exemplo de mapeamento entidade → grupo
ENTIDADE_CHAT_MAP = {
    "0": "-4890701328"
}

# Função para autenticar no GLPI
def autenticar_glpi():
    try:
        response = requests.post(
            f"{GLPI_URL}/initSession",
            json={"login": USER, "password": PASSWORD},
            headers={"App-Token": APP_TOKEN},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data["session_token"]
    except Exception as e:
        logging.error(f"Erro ao autenticar no GLPI: {e}")
        return None

# Função para encerrar sessão
def encerrar_sessao(session_token):
    try:
        requests.get(
            f"{GLPI_URL}/killSession",
            headers={"App-Token": APP_TOKEN, "Session-Token": session_token},
            timeout=5
        )
    except Exception as e:
        logging.warning(f"Erro ao encerrar sessão: {e}")
