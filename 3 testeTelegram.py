import requests
import json
import time
import logging
import mysql.connector

# Configurações
GLPI_URL = "http://192.168.1.46/apirest.php/"
APP_TOKEN = "iy8ttWAgfDxnjcbCXVdrOwzFsKi6nuu1RIbXePdk"
TELEGRAM_BOT_TOKEN = "8233082568:AAH-3bcfmpRn_ORqHhJF54lsduEfz9w1CjU"
INTERVALO_VERIFICACAO = 20  # segundos
LOG_FILE = "glpi_monitor_v2.log"

DB_CONFIG = {
    "host": "192.168.1.46",
    "user": "glpiwork",
    "password": "Cunh,9233",
    "database": "glpi"
}

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ],
)


class GLPITelegramBot:
    def __init__(self):
        self.offset = 0
        self.bot_session = self._create_bot_session()
        logging.info("Monitor inicializado. Tickets conhecidos: 0")

    def _create_bot_session(self):
        """Cria sessão de serviço do bot"""
        try:
            r = requests.get(
                f"{GLPI_URL}initSession",
                auth=("glpibot1", "r3d3.ti33"),
                headers={"App-Token": APP_TOKEN},
                timeout=10,
            )
            r.raise_for_status()
            logging.info("Sessão do bot criada com sucesso")
            return r.json().get("session_token")
        except Exception as e:
            logging.error(f"Erro ao criar sessão do bot: {e}")
            return None

    def _get_user_session(self, chat_id):
        """Faz login no GLPI usando token pessoal do usuário, buscando chat_id no banco"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT u.id, u.name, u.api_token
                FROM glpi_users u
                JOIN glpi_plugin_fields_userintegraotelegrams p
                ON p.items_id = u.id
                WHERE p.telegramchatidfield = %s
            """, (chat_id,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if not user:
                logging.warning(f"[ERRO] Nenhum usuário vinculado ao chat_id {chat_id}")
                return None

            if not user['api_token']:
                logging.warning(f"[ERRO] Usuário {user['name']} não tem API token configurado")
                return None

            # Criar sessão com token pessoal
            r = requests.get(
                f"{GLPI_URL}initSession",
                headers={"App-Token": APP_TOKEN, "Authorization": f"user_token {user['api_token']}"},
                timeout=10
            )
            r.raise_for_status()
            return r.json().get("session_token")

        except Exception as e:
            logging.error(f"Erro login automático chat_id {chat_id}: {e}")
            return None

    def _send_message(self, chat_id, text):
        """Envia mensagem para o Telegram"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            r = requests.post(url, json={"chat_id": chat_id, "text": text})
            r.raise_for_status()
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem Telegram: {e}")

    def _get_updates(self):
        """Busca novas mensagens do Telegram"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            r = requests.get(url, params={"timeout": 30, "offset": self.offset + 1}, timeout=40)
            r.raise_for_status()
            updates = r.json().get("result", [])
            if updates:
                self.offset = updates[-1]["update_id"]
            return updates
        except Exception as e:
            logging.error(f"Erro no getUpdates: {e}")
            return []

    def _abrir_chamado(self, chat_id, descricao):
        """Abre chamado no GLPI em nome do usuário autenticado"""
        session_token = self._get_user_session(chat_id)
        if not session_token:
            self._send_message(chat_id, "❌ Você não está autorizado ou não possui token configurado no GLPI.")
            return

        try:
            url = f"{GLPI_URL}Ticket"
            payload = {
                "input": {
                    "name": "Chamado via Telegram",
                    "content": descricao,
                }
            }
            r = requests.post(
                url,
                headers={"App-Token": APP_TOKEN, "Session-Token": session_token},
                json=payload,
                timeout=15,
            )
            r.raise_for_status()
            ticket = r.json()
            ticket_id = ticket.get("id")
            self._send_message(chat_id, f"✅ Chamado aberto com sucesso! Número: {ticket_id}")
        except Exception as e:
            logging.error(f"Erro ao abrir chamado: {e}")
            self._send_message(chat_id, "❌ Erro ao abrir chamado no GLPI.")

    def run(self):
        """Loop principal"""
        while True:
            updates = self._get_updates()
            for update in updates:
                message = update.get("message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]
                text = message.get("text", "")

                if text.startswith("/abrir"):
                    descricao = text.replace("/abrir", "").strip()
                    if not descricao:
                        self._send_message(chat_id, "Use assim: /abrir Descrição do chamado")
                        continue
                    self._abrir_chamado(chat_id, descricao)

                elif text == "/start":
                    self._send_message(chat_id, "👋 Bem-vindo! Use /abrir para abrir chamados no GLPI.")

            time.sleep(2)


if __name__ == "__main__":
    bot = GLPITelegramBot()
    bot.run()
