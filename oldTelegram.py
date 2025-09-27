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
GLPI_URL = "http://192.168.1.46/"
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

    # def _autenticar(self):
    #     """Autentica no GLPI"""
    #     try:
    #         response = requests.post(
    #             f"{GLPI_URL}/initSession",
    #             json={"login": USER, "password": PASSWORD},
    #             headers={"App-Token": APP_TOKEN},
    #             timeout=10
    #         )
    #         response.raise_for_status()
    #         return response.json()["session_token"]
    #     except Exception as e:
    #         logging.error(f"Falha na autenticação: {e}")
    #         raise
        def _autenticar(self):
            """Autentica no GLPI"""
            try:
                url = f"{GLPI_URL}apirest.php/initSession"
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
            requests.get(
                f"{GLPI_URL}/killSession",
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

    def _buscar_tickets_recentes(self, session_token, horas=4):
        """Busca tickets recentes com intervalo personalizado"""
        try:
            intervalo = (datetime.now() - relativedelta.relativedelta(hours=horas)).strftime("%Y-%m-%d %H:%M:%S")
            payload = {
                "criteria": [{"field": 19, "searchtype": "morethan", "value": intervalo}],
                "forcedisplay": ["2", "1", "4", "5", "12", "15", "19", "50", "83"],
                "sort": "19",
                "order": "DESC",
                "range": f"0-{MAX_TICKETS}"
            }
            response = requests.post(
                f"{GLPI_URL}/search/Ticket/",
                headers={
                    "App-Token": APP_TOKEN,
                    "Session-Token": session_token,
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            logging.error(f"Erro ao buscar tickets: {e}")
            raise

    def _buscar_detalhes_ticket(self, ticket_id, session_token):
        """Busca detalhes completos de um ticket"""
        try:
            response = requests.get(
                f"{GLPI_URL}/Ticket/{ticket_id}",
                headers={
                    "App-Token": APP_TOKEN,
                    "Session-Token": session_token,
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Erro ao buscar detalhes do ticket {ticket_id}: {e}")
            return None

    def _buscar_localizacao(self, location_id, session_token):
        """Busca nome da localização com cache"""
        if not location_id:
            return "Não especificada"
            
        if location_id in self.cache_localizacoes:
            return self.cache_localizacoes[location_id]
            
        try:
            response = requests.get(
                f"{GLPI_URL}/Location/{location_id}",
                headers={
                    "App-Token": APP_TOKEN,
                    "Session-Token": session_token,
                    "Content-Type": "application/json"
                },
                timeout=5
            )
            response.raise_for_status()
            nome = response.json().get("completename", f"Local ID {location_id}")
            self.cache_localizacoes[location_id] = nome
            return nome
        except Exception:
            nome = f"Local ID {location_id}"
            self.cache_localizacoes[location_id] = nome
            return nome

    def _buscar_acompanhamentos(self, ticket_id, session_token):
        """Busca todos os acompanhamentos de um ticket"""
        try:
            response = requests.get(
                f"{GLPI_URL}/Ticket/{ticket_id}/TicketFollowup",
                headers={
                    "App-Token": APP_TOKEN,
                    "Session-Token": session_token,
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Erro ao buscar acompanhamentos do ticket {ticket_id}: {e}")
            return []

    def _buscar_usuarios_relacionados(self, ticket_id, session_token):
        """Busca usuários relacionados ao ticket"""
        try:
            response = requests.get(
                f"{GLPI_URL}/Ticket/{ticket_id}/Ticket_User",
                headers={
                    "App-Token": APP_TOKEN,
                    "Session-Token": session_token,
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            response.raise_for_status()
            usuarios = response.json()

            dados = defaultdict(list)
            tipo_map = {"1": "requerente", "2": "atribuido", "3": "observadores"}

            for user in usuarios:
                tipo = str(user.get("type"))
                user_id = user.get("users_id")
                alt_email = user.get("alternative_email")

                if tipo in tipo_map:
                    if user_id and user_id != 0:
                        nome = self._buscar_nome_usuario(user_id, session_token)
                        if nome:
                            dados[tipo_map[tipo]].append(nome)
                    elif alt_email:
                        dados[tipo_map[tipo]].append(alt_email)

            if not dados["requerente"]:
                dados["requerente"].append("Não informado")
            if not dados["atribuido"]:
                dados["atribuido"].append("Não atribuído")
            if not dados["observadores"]:
                dados["observadores"].append("Sem observadores")

            return dados
        except Exception as e:
            logging.error(f"Erro ao buscar usuários do ticket {ticket_id}: {e}")
            return {
                "requerente": ["Não informado"],
                "atribuido": ["Não atribuído"],
                "observadores": ["Sem observadores"]
            }

    def _buscar_nome_usuario(self, user_id, session_token):
        """Busca nome do usuário com cache"""
        if not user_id:
            return "Sistema"
            
        if user_id in self.cache_usuarios:
            return self.cache_usuarios[user_id]
            
        try:
            response = requests.get(
                f"{GLPI_URL}/User/{user_id}",
                headers={
                    "App-Token": APP_TOKEN,
                    "Session-Token": session_token,
                    "Content-Type": "application/json"
                },
                timeout=5
            )
            response.raise_for_status()
            nome = response.json().get("name", f"ID {user_id}")
            self.cache_usuarios[user_id] = nome
            return nome
        except Exception:
            nome = f"ID {user_id}"
            self.cache_usuarios[user_id] = nome
            return nome

    def _formatar_mensagem_acompanhamento(self, acompanhamento, session_token):
        """Formata mensagem de acompanhamento limpa"""
        try:
            data_criacao = datetime.strptime(acompanhamento.get("date"), "%Y-%m-%d %H:%M:%S")
            conteudo = self._remover_tags_html(acompanhamento.get("content", ""))
            
            if len(conteudo) > 1000:
                conteudo = conteudo[:1000] + " [...]"

            user_id = acompanhamento.get("users_id")
            nome_usuario = self._buscar_nome_usuario(user_id, session_token)

            return (
                "💬 <b>NOVO ACOMPANHAMENTO</b>\n\n"
                f"🆔 <b>Ticket:</b> {acompanhamento.get('tickets_id', 'N/A')}\n"
                f"👤 <b>Autor:</b> {nome_usuario}\n"
                f"📅 <b>Data:</b> {data_criacao.strftime('%d/%m/%Y %H:%M')}\n\n"
                f"📝 <b>Conteúdo:</b>\n{conteudo}"
            )
        except Exception as e:
            logging.error(f"Erro ao formatar acompanhamento: {str(e)}")
            return None

    def _formatar_mensagem_status(self, ticket_id, status_antigo, status_novo, session_token):
        """Formata mensagem de mudança de status"""
        try:
            detalhes = self._buscar_detalhes_ticket(ticket_id, session_token)
            if not detalhes:
                return None

            usuarios = self._buscar_usuarios_relacionados(ticket_id, session_token)
            data_mod = datetime.strptime(detalhes.get("date_mod"), "%Y-%m-%d %H:%M:%S")
            localizacao = self._buscar_localizacao(detalhes.get("locations_id"), session_token)
            conteudo = self._remover_tags_html(detalhes.get("content", "Sem descrição"))
        
            if len(conteudo) > 1000:
                conteudo = conteudo[:1000] + " [...]"

            return (
                "🔄 <b>STATUS ALTERADO</b>\n\n"
                f"📌 <b>Ticket:</b> {ticket_id}\n"
                f"🏢 <b>Local:</b> {localizacao}\n\n"
                f"👤 <b>Requerente:</b> {', '.join(usuarios['requerente'])}\n"
                f"🔄 <b>Status anterior:</b> {status_antigo}\n"
                f"✅ <b>Novo status:</b> {status_novo}\n\n"
                f"📝 <b>Descrição:</b>\n{conteudo}\n\n"
                f"🕒 <b>Atualizado em:</b> {data_mod.strftime('%d/%m/%Y %H:%M')}"
            )
        except Exception as e:
            logging.error(f"Erro ao formatar status: {str(e)}")
            return None

    def _formatar_mensagem_novo_ticket(self, detalhes, session_token):
        """Formata mensagem para NOVO TICKET com todas as informações solicitadas"""
        try:
            ticket_id = detalhes.get("id")
            titulo = self._remover_tags_html(detalhes.get("name", "Sem título"))
            data_criacao = datetime.strptime(detalhes.get("date"), "%Y-%m-%d %H:%M:%S")
            status = self.STATUS_MAP.get(detalhes.get("status"), "Desconhecido")
            conteudo = self._remover_tags_html(detalhes.get("content", "Sem descrição"))
            usuarios = self._buscar_usuarios_relacionados(ticket_id, session_token)
            

            # Limita o tamanho da descrição se for muito longa
            if len(conteudo) > 1000:
                conteudo = conteudo[:1000] + " [...]"

            return (
                "🆕 <b>NOVO TICKET CRIADO</b>\n\n"
                f"📌 <b>Ticket:</b> {ticket_id}\n"
                f"📋 <b>Título:</b> {titulo}\n"
                f"📅 <b>Criado em:</b> {data_criacao.strftime('%d/%m/%Y %H:%M')}\n"
                f"🔄 <b>Status:</b> {status}\n\n"
                f"👤 <b>Requerente:</b> {', '.join(usuarios['requerente'])}\n"
                f"👀 <b>Observadores:</b> {', '.join(usuarios['observadores'])}\n"
                f"🔧 <b>Atribuído a:</b> {', '.join(usuarios['atribuido'])}\n\n"
                f"📝 <b>Descrição:</b>\n{conteudo}"
            )
        except Exception as e:
            logging.error(f"Erro ao formatar novo ticket: {str(e)}")
            return None

    def _enviar_mensagem_telegram(self, texto, chat_id):
        """Envia mensagem para o Telegram"""
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": texto,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True
                },
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem para o Telegram (chat_id {chat_id}): {e}")
            return False

    def _processar_ticket(self, ticket, session_token):
        """Processa um ticket individual"""
        ticket_id = str(ticket.get('2'))
        if not ticket_id:
            return

        # Verifica se é um NOVO TICKET (não existia no estado anterior)
        is_novo_ticket = ticket_id not in self.ultimo_estado

        # Inicializa estrutura do ticket se não existir
        if is_novo_ticket:
            self.ultimo_estado[ticket_id] = {
                'status': None,
                'acompanhamentos_notificados': []
            }

        # Notifica NOVO TICKET
        if is_novo_ticket:
            detalhes = self._buscar_detalhes_ticket(ticket_id, session_token)
            if detalhes:
                msg = self._formatar_mensagem_novo_ticket(detalhes, session_token)
                if msg:
                    entidade_id = str(detalhes.get("entities_id", "0"))
                    chat_id = ENTIDADE_CHAT_MAP.get(entidade_id)
                    if chat_id and self._enviar_mensagem_telegram(msg, chat_id):
                        logging.info(f"Notificado NOVO TICKET {ticket_id}")

        # Processa mudança de status
        detalhes = self._buscar_detalhes_ticket(ticket_id, session_token)
        if detalhes:
            novo_status = detalhes.get("status")
            status_atual = self.ultimo_estado[ticket_id]['status']
            
            if status_atual is None or novo_status != status_atual:
                status_antigo = self.STATUS_MAP.get(status_atual, "Desconhecido")
                status_novo = self.STATUS_MAP.get(novo_status, "Desconhecido")
                
                msg = self._formatar_mensagem_status(ticket_id, status_antigo, status_novo, session_token)
                if msg:
                    entidade_id = str(detalhes.get("entities_id", "0"))
                    chat_id = ENTIDADE_CHAT_MAP.get(entidade_id)
                    if chat_id and self._enviar_mensagem_telegram(msg, chat_id):
                        self.ultimo_estado[ticket_id]['status'] = novo_status
                        logging.info(f"Notificado mudança de status do ticket {ticket_id}")

        # Processa acompanhamentos
        acompanhamentos = self._buscar_acompanhamentos(ticket_id, session_token)
        for acomp in acompanhamentos:
            acomp_id = str(acomp.get('id'))
            if acomp_id not in self.ultimo_estado[ticket_id]['acompanhamentos_notificados']:
                msg = self._formatar_mensagem_acompanhamento(acomp, session_token)
                if msg:
                    detalhes = self._buscar_detalhes_ticket(ticket_id, session_token)
                    if detalhes:
                        entidade_id = str(detalhes.get("entities_id", "0"))
                        chat_id = ENTIDADE_CHAT_MAP.get(entidade_id)
                        if chat_id and self._enviar_mensagem_telegram(msg, chat_id):
                            self.ultimo_estado[ticket_id]['acompanhamentos_notificados'].append(acomp_id)
                            logging.info(f"Notificado acompanhamento {acomp_id} do ticket {ticket_id}")

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

if __name__ == "__main__":
    monitor = GLPIMonitor()
    monitor.monitorar()
