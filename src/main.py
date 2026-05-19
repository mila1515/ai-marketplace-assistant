from src.core.database import init_db


def main() -> None:
    init_db()
    print("AI Marketplace Assistant initialized.")


if __name__ == "__main__":
    main()
