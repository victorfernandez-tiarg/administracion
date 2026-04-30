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
    Descarga un archivo desde Google Drive
    
    Args:
        file_id: ID del archivo en Google Drive
        file_name: Nombre local para guardar (ej: "datos_facturacion.xlsx")
    
    Returns:
        True si descargó exitosamente, False si hay error
    """
    try:
        service = _get_drive_service()
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        
        local_path = RAW_DIR / file_name
        
        # Obtener metadatos del archivo (name y tamaño)
        file_metadata = service.files().get(
            fileId=file_id,
            fields="name, size, modifiedTime"
        ).execute()
        
        file_size_mb = float(file_metadata.get("size", 0)) / (1024 * 1024)
        print(f"  ↓ Descargando {file_name} ({file_size_mb:.2f} MB)...")
        
        # Descargar contenido
        request = service.files().get_media(fileId=file_id)
        file_handle = MediaIoBaseDownload(BytesIO(), request)
        
        done = False
        while not done:
            status, done = file_handle.next_chunk()
        
        # Guardar a disco
        with open(local_path, "wb") as f:
            f.write(file_handle.getbuffer().getvalue())
        
        print(f"  ✓ {file_name} sincronizado ({local_path})")
        return True
        
    except Exception as e:
        print(f"  ✗ Error descargando {file_name}: {e}")
        return False


def sincronizar():
    """Descarga ambos archivos desde Google Drive"""
    print("─" * 50)
    print("Sincronizando archivos desde Google Drive...")
    
    file_ids = {
        "datos_facturacion.xlsx": os.getenv("GOOGLE_DRIVE_FACTURACION_FILE_ID", ""),
        "cc_clientes.xlsx": os.getenv("GOOGLE_DRIVE_CC_FILE_ID", ""),
    }
    
    resultados = {}
    for file_name, file_id in file_ids.items():
        if not file_id:
            print(f"  ⊘ Saltando {file_name}: ID no configurado")
            resultados[file_name] = False
            continue
        resultados[file_name] = descargar_archivo(file_id, file_name)
    
    print("─" * 50)
    return resultados


if __name__ == "__main__":
    sincronizar()
