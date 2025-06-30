# 🤖 Integração GLPI + Telegram

Este projeto permite a integração entre o **GLPI** (sistema de chamados) e o **Telegram**, com funcionalidades como:

- Notificação automática de **novos tickets**
- Alerta em tempo real de **mudança de status**
- Envio de **acompanhamentos** (follow-ups) diretamente para o grupo do Telegram

---

## 📦 Requisitos

- Python 3.8+
- GLPI com API REST habilitada
- Bot no Telegram (via [@BotFather](https://t.me/BotFather))

---

## ⚙️ Instalação

1. Clone este repositório:
   ```bash
   git clone https://github.com/seu-usuario/glpi-telegram-integration.git
   cd glpi-telegram-integration
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Crie um arquivo `.env` baseado no `.env.example`:
   ```bash
   cp .env.example .env
   ```

4. Edite o `.env` com suas credenciais do GLPI e Telegram.

---

## 🚀 Executando

```bash
python glpi_monitor_v2.py
```

---

## 📁 Arquivos principais

- `glpi_monitor_v2.py` → Script principal
- `estado_tickets_v2.json` → Histórico local dos tickets
- `.env.example` → Modelo de variáveis de ambiente
- `requirements.txt` → Dependências do projeto

---

## 🛡️ Segurança

- Nunca compartilhe seu `.env` com dados reais.
- Arquivos sensíveis já estão no `.gitignore`.

---

## 📄 Licença

MIT — Use, modifique e contribua como quiser. 😉

---

## ✉️ Autor

**Pedro Ribeiro**  
[LinkedIn](https://www.linkedin.com/in/pedro-ribeiro-4b5710207)
