import requests
import json
import time
import os
import logging
import re
from html import unescape
from datetime import datetime
from dateutil import relativedelta
from collections import defaultdict

# Configurações
GLPI_URL = "http://192.168.1.46/apirest.php/"
APP_TOKEN = "iy8ttWAgfDxnjcbCXVdrOwzFsKi6nuu1RIbXePdk"
USER = "glpibot1"
PASSWORD = "r3d3.ti33"
TELEGRAM_BOT_TOKEN = "8233082568:AAH-3bcfmpRn_ORqHhJF54lsduEfz9w1CjU"
INTERVALO_VERIFICACAO = 20  # SEGUNDOS PARA VERIFICACAO
ARQUIVO_ESTADO = "estado_tickets_v2.json"
LOG_FILE = "glpi_monitor_v2.log"
MAX_TICKETS = 50

# Mapeamento de entidade para grupo do Telegram
ENTIDADE_CHAT_MAP = {
    "0": "-4890701328",  # Entidade
}

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

class GLPIMonitor:
    STATUS_MAP = {
        1: "Novo",
        2: "Em atendimento",
        3: "Planejado",
        4: "Pendente",
        5: "Solucionado",
        6: "Fechado"
    }

    def __init__(self):
        self.ultimo_estado = self._carregar_estado()
        self.cache_usuarios = {}
        self.cache_localizacoes = {}
        logging.info(f"Monitor inicializado. Tickets conhecidos: {len(self.ultimo_estado)}")

    def _carregar_estado(self):
        """Carrega o estado com estrutura completa"""
        try:
            if os.path.exists(ARQUIVO_ESTADO):
                with open(ARQUIVO_ESTADO, 'r', encoding='utf-8') as f:
                    estado = json.load(f)
                    for ticket_id, dados in estado.items():
                        if 'acompanhamentos_notificados' not in dados:
                            dados['acompanhamentos_notificados'] = []
                        if 'status' not in dados:
                            dados['status'] = None
                    return estado
            return {}
        except Exception as e:
            logging.error(f"Erro ao carregar estado: {e}")
            return {}

    def _salvar_estado(self):
        """Salva o estado atualizado"""
        try:
            with open(ARQUIVO_ESTADO, 'w', encoding='utf-8') as f:
                json.dump(self.ultimo_estado, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Erro ao salvar estado: {e}")

    def _autenticar(self):
        """Autentica no GLPI"""
        try:
            url = f"{GLPI_URL}initSession"
            response = requests.get(
                url,
                auth=(USER, PASSWORD),  # autenticação básica
                headers={"App-Token": APP_TOKEN},
                timeout=10
            )
            response.raise_for_status()
            return response.json()["session_token"]
        except Exception as e:
            logging.error(f"Falha na autenticação: {e}")
            raise

    def _encerrar_sessao(self, session_token):
        """Encerra a sessão no GLPI"""
        try:
            url = f"{GLPI_URL}killSession"
            requests.get(
                url,
                headers={"App-Token": APP_TOKEN, "Session-Token": session_token},
                timeout=5
            )
        except Exception as e:
            logging.warning(f"Erro ao encerrar sessão: {e}")

    def _remover_tags_html(self, texto):
        """Remove TODAS as tags HTML"""
        if not texto:
            return ""
        texto = unescape(texto)
        texto = re.sub(r'<[^>]*>', '', texto)
        return ' '.join(texto.split()).strip()

    # --- resto do código (sem mudanças) ---
    # aqui permanecem seus métodos: _buscar_tickets_recentes, _buscar_detalhes_ticket,
    # _buscar_localizacao, _buscar_acompanhamentos, _buscar_usuarios_relacionados,
    # _buscar_nome_usuario, _formatar_mensagem_acompanhamento, _formatar_mensagem_status,
    # _formatar_mensagem_novo_ticket, _enviar_mensagem_telegram, _processar_ticket

    # ... (todo o código que você já tinha) ...

    def monitorar(self):
        """Loop principal de monitoramento"""
        while True:
            try:
                logging.info("="*50)
                logging.info(f"Iniciando verificação em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

                session_token = self._autenticar()
                logging.info("Autenticação bem-sucedida")

                tickets = self._buscar_tickets_recentes(session_token)
                logging.info(f"Tickets encontrados: {len(tickets)}")

                for ticket in tickets:
                    self._processar_ticket(ticket, session_token)
                    time.sleep(0.5)  # Intervalo entre requisições

                self._salvar_estado()
                self._encerrar_sessao(session_token)
                logging.info(f"Próxima verificação em {INTERVALO_VERIFICACAO} segundos")
                time.sleep(INTERVALO_VERIFICACAO)

            except KeyboardInterrupt:
                logging.info("Monitoramento interrompido pelo usuário")
                break
            except Exception as e:
                logging.error(f"Erro no ciclo de monitoramento: {str(e)}")
                time.sleep(20)
    def _buscar_tickets_recentes(self, session_token):
        """Busca os tickets recentes no GLPI"""
        try:
            url = f"{GLPI_URL}Ticket"
            params = {
                "range": "0-50",
                "order": "DESC",
                "sort": "date_mod"
            }
            response = requests.get(
                url,
                headers={
                    "App-Token": APP_TOKEN,
                    "Session-Token": session_token
                },
                params=params,
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Erro ao buscar tickets: {e}")
            return []

    def _buscar_detalhes_ticket(self, ticket_id, session_token):
        """Busca os detalhes de um ticket específico"""
        try:
            url = f"{GLPI_URL}Ticket/{ticket_id}"
            response = requests.get(
                url,
                headers={
                    "App-Token": APP_TOKEN,
                    "Session-Token": session_token
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Erro ao buscar detalhes do ticket {ticket_id}: {e}")
            return None

    def _processar_ticket(self, ticket, session_token):
        """Processa um ticket (novo ou atualizado)"""
        ticket_id = str(ticket["id"])
        logging.info(f"Processando ticket {ticket_id}")

        detalhes = self._buscar_detalhes_ticket(ticket_id, session_token)
        if not detalhes:
            return

        titulo = detalhes.get("name", "")
        logging.info(f"Ticket {ticket_id} - {titulo}")


if __name__ == "__main__":
    monitor = GLPIMonitor()
    monitor.monitorar()
