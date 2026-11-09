import getpass

from app import db, seguridad


def main():
    nombre = input("Nombre: ").strip()
    email = input("Correo: ").strip().lower()
    rol = input("Rol (admin/usuario) [usuario]: ").strip() or "usuario"
    limite = int(input("Límite de tokens [20000]: ").strip() or "20000")
    password = getpass.getpass("Contraseña (mínimo 8 caracteres, no se ve al escribir): ")

    if rol not in ("admin", "usuario") or len(password) < 8:
        raise SystemExit("Rol inválido o contraseña demasiado corta")

    # Si el correo ya existe, actualiza sus datos en lugar de fallar
    fila = db.uno(
        """INSERT INTO usuarios (nombre, email, password_hash, rol, limite_tokens)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (email) DO UPDATE
           SET nombre = EXCLUDED.nombre, password_hash = EXCLUDED.password_hash,
               rol = EXCLUDED.rol, limite_tokens = EXCLUDED.limite_tokens, activo = TRUE
           RETURNING id""",
        (nombre, email, seguridad.hashear(password), rol, limite),
    )
    print(f"Listo: usuario {email} con rol {rol} (id {fila['id']})")


if __name__ == "__main__":
    main()