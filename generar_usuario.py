"""
Generador de hashes de contraseñas para el dashboard Finnegans BI
Ejecutar: python generar_usuario.py
"""
import hashlib
import getpass
import tomllib
from pathlib import Path

SECRETS_PATH = Path(".streamlit/secrets.toml")

def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000).hex()

def main():
    # Leer salt del secrets.toml
    if not SECRETS_PATH.exists():
        print(f"ERROR: No se encontró {SECRETS_PATH}")
        return

    with open(SECRETS_PATH, "rb") as f:
        secrets = tomllib.load(f)

    salt = secrets.get("auth", {}).get("salt")
    if not salt:
        print("ERROR: No se encontró [auth] salt en secrets.toml")
        return

    print("=== Generador de credenciales ===")
    usuario = input("Nombre de usuario: ").strip()
    if not usuario:
        print("El nombre de usuario no puede estar vacío.")
        return

    password = getpass.getpass("Contraseña: ")
    if not password:
        print("La contraseña no puede estar vacía.")
        return

    h = hash_password(password, salt)
    print(f"\nAgregá esta línea en la sección [users] de .streamlit/secrets.toml:")
    print(f'\n{usuario} = "{h}"\n')

if __name__ == "__main__":
    main()
