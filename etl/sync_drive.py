"""
Sincroniza archivos .xlsx desde Google Drive a data/raw/
Usa Service Account authentication con credenciales en GOOGLE_SERVICE_ACCOUNT_JSON
"""

import os
import json
from pathlib import Path
from typing import Optional
from io import BytesIO

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
except ImportError:
    raise ImportError(
        "Google Drive API libraries not installed. "
        "Install with: pip install google-auth google-auth-httplib2 google-api-python-client"
    )

RAW_DIR = Path("data/raw")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _get_drive_service():
    """Crea y retorna servicio de Drive autenticado con Service Account"""
    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_JSON no está definida. "
            "Configura la variable de entorno con el JSON del Service Account."
        )
    
    try:
        creds_dict = json.loads(creds_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"GOOGLE_SERVICE_ACCOUNT_JSON es JSON inválido: {e}")
    
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


def descargar_archivo(file_id: str, file_name: str) -> bool:
    """
    Exporta un Google Sheet como xlsx y lo guarda en data/raw/.
    Funciona tanto con Google Sheets como con archivos .xlsx nativos de Drive.
    """
    try:
        service = _get_drive_service()
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        local_path = RAW_DIR / file_name

        # Verificar tipo de archivo
        file_metadata = service.files().get(
            fileId=file_id,
            fields="name, mimeType"
        ).execute()

        mime = file_metadata.get("mimeType", "")
        print(f"  ↓ Descargando {file_name} (tipo: {mime})...")

        if mime == "application/vnd.google-apps.spreadsheet":
            # Es un Google Sheet → exportar como xlsx
            content = service.files().export_media(
                fileId=file_id,
                mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ).execute()
        else:
            # Es un archivo binario normal (.xlsx subido)
            request = service.files().get_media(fileId=file_id)
            buf = BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            content = buf.getvalue()

        with open(local_path, "wb") as f:
            f.write(content)

        print(f"  ✓ {file_name} sincronizado ({local_path})")
        return True

    except Exception as e:
        import traceback
        print(f"  ✗ Error descargando {file_name}: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


def sincronizar():
    """Descarga ambos archivos desde Google Drive"""
    print("─" * 50)
    print("Sincronizando archivos desde Google Drive...")
    
    file_ids = {
        "datos_facturacion.xlsx": {
            "env": "GOOGLE_DRIVE_FACTURACION_FILE_ID",
            "id": os.getenv("GOOGLE_DRIVE_FACTURACION_FILE_ID", ""),
        },
        "cc_clientes.xlsx": {
            "env": "GOOGLE_DRIVE_CC_FILE_ID",
            "id": os.getenv("GOOGLE_DRIVE_CC_FILE_ID", ""),
        },
        "composicion_saldos.xlsx": {
            "env": "GOOGLE_DRIVE_COMPOSICION_FILE_ID",
            "id": os.getenv("GOOGLE_DRIVE_COMPOSICION_FILE_ID", ""),
        },
    }
    
    resultados = {}
    for file_name, conf in file_ids.items():
        file_id = conf["id"]
        env_name = conf["env"]
        if not file_id:
            print(f"  ⊘ Saltando {file_name}: ID no configurado (env={env_name})")
            resultados[file_name] = False
            continue
        print(f"  → Intenta descargar {file_name} (ID: {file_id[:20]}...)")
        resultados[file_name] = descargar_archivo(file_id, file_name)
    
    print("─" * 50)
    return resultados


if __name__ == "__main__":
    sincronizar()
