import sys
import subprocess


def run_migrations(message: str):
    if not message:
        print("Erro: informe uma mensagem para a migration.")
        sys.exit(1)

    # Gera a migration
    print(f"Gerando migration: {message}")
    result = subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", message],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("Erro ao gerar migration:")
        print(result.stderr)
        sys.exit(1)

    # Aplica a migration
    print("Aplicando migration...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"], capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("Erro ao aplicar migration:")
        print(result.stderr)
        sys.exit(1)

    print("Migration concluída com sucesso!")


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:])  # Mensagem passada como argumento
    run_migrations(msg)
