from agente.tools.terminal import run_command
from agente.tools.files import read_file, write_file, list_directory
from agente.tools.notes import add_note_or_task, list_notes_and_tasks, delete_note_or_task
from agente.tools.web import search_web, fetch_web_content
from agente.tools.whatsapp import send_whatsapp_message
from agente.tools.mockup import generate_business_mockup
from agente.tools.agenda import add_appointment, list_appointments, update_appointment_status
from agente.tools.prospecting import (
    search_business_leads,
    save_lead,
    list_leads,
    generate_pitch,
    run_autonomous_campaign,
    update_lead_status
)

# Lista de funciones pasadas directamente al SDK de Google Gemini para Function Calling
AGENT_TOOLS = [
    run_command,
    read_file,
    write_file,
    list_directory,
    add_note_or_task,
    list_notes_and_tasks,
    delete_note_or_task,
    search_web,
    fetch_web_content,
    send_whatsapp_message,
    generate_business_mockup,
    add_appointment,
    list_appointments,
    update_appointment_status,
    search_business_leads,
    save_lead,
    list_leads,
    generate_pitch,
    run_autonomous_campaign,
    update_lead_status
]
