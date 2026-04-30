#!/usr/bin/env python3
"""
Script de validación pre-deploy
Verifica que todo esté listo antes de pushear a GitHub y Railway
"""

import sys
from pathlib import Path
import json

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def check(condition, message):
    """Imprime resultado de verificación"""
    if condition:
        print(f"{GREEN}✓{RESET} {message}")
        return True
    else:
        print(f"{RED}✗{RESET} {message}")
        return False

def main():
    print(f"\n{BOLD}Validación Pre-Deploy - Finnegans BI{RESET}")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    all_ok = True
    
    # 1. Archivos existen
    print(f"\n{BOLD}1. Archivos Requeridos:{RESET}")
    files_required = [
        "etl/sync_drive.py",
        "etl/procesar.py", 
        "etl/procesar_cc.py",
        "dashboard/app.py",
        "deploy/Dockerfile",
        "requirements.txt",
        ".gitignore",
        "ENVIRONMENT_VARIABLES.md",
        "DEPLOYMENT_STEPS.md",
        "RAILWAY_QUICK_START.md",
    ]
    
    for file in files_required:
        all_ok &= check(
            (project_root / file).exists(),
            f"{file}"
        )
    
    # 2. Imports en Python
    print(f"\n{BOLD}2. Importaciones Python:{RESET}")
    
    try:
        sys.path.insert(0, str(project_root))
        from etl.sync_drive import sincronizar
        all_ok &= check(True, "etl.sync_drive.sincronizar importable")
    except ImportError as e:
        all_ok &= check(False, f"etl.sync_drive: {e}")
    
    try:
        from etl.procesar import correr_etl
        all_ok &= check(True, "etl.procesar.correr_etl importable")
    except ImportError as e:
        all_ok &= check(False, f"etl.procesar: {e}")
    
    try:
        from etl.procesar_cc import correr_etl_cc
        all_ok &= check(True, "etl.procesar_cc.correr_etl_cc importable")
    except ImportError as e:
        all_ok &= check(False, f"etl.procesar_cc: {e}")
    
    # 3. Requirements
    print(f"\n{BOLD}3. Dependencias en requirements.txt:{RESET}")
    req_file = project_root / "requirements.txt"
    if req_file.exists():
        content = req_file.read_text()
        all_ok &= check("google-auth" in content, "google-auth presente")
        all_ok &= check("google-api-python-client" in content, "google-api-python-client presente")
    else:
        all_ok &= check(False, "requirements.txt no encontrado")
    
    # 4. .gitignore
    print(f"\n{BOLD}4. .gitignore (Seguridad):{RESET}")
    gitignore_file = project_root / ".gitignore"
    if gitignore_file.exists():
        content = gitignore_file.read_text()
        all_ok &= check(".secrets/" in content, ".secrets/ está en .gitignore")
        all_ok &= check("data/raw/" in content, "data/raw/ está en .gitignore")
        all_ok &= check(".env" in content, ".env está en .gitignore")
    else:
        all_ok &= check(False, ".gitignore no encontrado")
    
    # 5. Dockerfile
    print(f"\n{BOLD}5. Dockerfile (Healthcheck):{RESET}")
    dockerfile = project_root / "deploy" / "Dockerfile"
    if dockerfile.exists():
        content = dockerfile.read_text()
        all_ok &= check("HEALTHCHECK" in content, "HEALTHCHECK configurado")
        all_ok &= check("requests" in content or "python -c" in content, "Healthcheck no usa curl")
    else:
        all_ok &= check(False, "Dockerfile no encontrado")
    
    # 6. Documentación
    print(f"\n{BOLD}6. Documentación:{RESET}")
    docs = ["ENVIRONMENT_VARIABLES.md", "DEPLOYMENT_STEPS.md", "RAILWAY_QUICK_START.md"]
    for doc in docs:
        all_ok &= check((project_root / doc).exists(), f"{doc} presente")
    
    # 7. Estructura de directorios
    print(f"\n{BOLD}7. Estructura de Directorios:{RESET}")
    all_ok &= check((project_root / "data" / "raw").exists(), "data/raw/ existe")
    all_ok &= check((project_root / "data" / "processed").exists(), "data/processed/ existe")
    all_ok &= check((project_root / "etl").exists(), "etl/ existe")
    all_ok &= check((project_root / "dashboard").exists(), "dashboard/ existe")
    
    # Resultado final
    print(f"\n{'=' * 60}")
    if all_ok:
        print(f"{GREEN}{BOLD}✓ LISTO PARA DEPLOY{RESET}")
        print("\nPróximos pasos:")
        print("1. python validar_deploy.py  (este script)")
        print("2. git add -A")
        print("3. git commit -m 'Paso 5-6: Sync con Google Drive'")
        print("4. git push origin main")
        print("5. Configurar variables en Railway")
        print("6. Ver RAILWAY_QUICK_START.md para detalles")
        return 0
    else:
        print(f"{RED}{BOLD}✗ FALTAN AJUSTES{RESET}")
        print("\nRevisa los errores arriba y corrige antes de deployar")
        return 1

if __name__ == "__main__":
    sys.exit(main())
