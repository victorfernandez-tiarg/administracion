import hashlib

SALT = "7e400d31a279f4f8be86125444f95e1de86d29437f949a95132616c02ada1c44"

hashes_viejos = {
    "admin":             "5fde54906f0a7d48207ba816822ced9e5c95c107ccec3b7e8b75713a283d119c",
    "usuario_1":         "9ea908cea785c677154c4c1b36aaaba845143c9e11300a3aaa14730f88eb51c5",
    "sebastian_hoffman": "a7ae09edc41285758811a54abebed791f7bfd561afd20105b78db196e31708e9",
    "growers":           "139d54082754a9a5094a6c414078619293c7e70e12981b89149ccb02c6bbee0e",
}

def h(pwd):
    return hashlib.pbkdf2_hmac("sha256", pwd.encode(), SALT.encode(), 260_000).hex()

# Verificar si los hashes viejos fueron generados con este salt
print("=== Verificando compatibilidad de salt ===")
for pwd in ["admin123", "admin", "finnegans", "tiarg", "1234", "123456", "password"]:
    result = h(pwd)
    if result == hashes_viejos["admin"]:
        print(f"MATCH admin! password = {pwd}")
        break
else:
    print("Los hashes VIEJOS no coinciden con este salt.")
    print("El salt del Railway viejo era DISTINTO al que copiaste.")

print()
print("=== Generando AUTH_USERS con password 'admin123' para test ===")
nuevo = h("admin123")
print(f"admin:{nuevo}")
print()
print("Pegá esto en Railway -> Variables -> AUTH_USERS para hacer la prueba:")
print(f"admin:{nuevo}")
