from agente.tools.terminal import run_command
from agente.tools.files import read_file, write_file, list_directory
from agente.tools.notes import add_note_or_task, list_notes_and_tasks, delete_note_or_task
from agente.tools.web import search_web, fetch_web_content
from agente.tools.whatsapp import send_whatsapp_message
from agente.tools.agenda import add_appointment, list_appointments, update_appointment_status
from agente.tools.prospecting import (
    search_business_leads,
    save_lead,
    list_leads,
    generate_pitch,
    run_autonomous_campaign,
    update_lead_status
)
from agente.tools.demo_generator import generate_business_demo

# 1. HERRAMIENTAS COMERCIALES (Seguras para exposición pública y clientes)
# Se excluyen terminantemente run_command, read_file, write_file y list_directory
# para prevenir vulnerabilidades de RCE o filtración de archivos por Prompt Injection.
COMMERCIAL_TOOLS = [
    generate_business_demo,
    search_business_leads,
    save_lead,
    list_leads,
    generate_pitch,
    run_autonomous_campaign,
    update_lead_status,
    add_appointment,
    list_appointments,
    update_appointment_status,
    add_note_or_task,
    list_notes_and_tasks,
    delete_note_or_task,
    search_web,
    fetch_web_content,
    send_whatsapp_message,
]

# 2. HERRAMIENTAS ADMINISTRATIVAS COMPLETAS (Uso exclusivo de desarrollo local)
ADMIN_TOOLS = [
    run_command,
    read_file,
    write_file,
    list_directory,
    *COMMERCIAL_TOOLS,
]

# Por defecto, la lista general de herramientas expuesta es la lista comercial segura
AGENT_TOOLS = COMMERCIAL_TOOLS
