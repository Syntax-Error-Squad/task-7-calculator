import argparse
import logging

from calculator import Calculator


def setup_logging(console_level):
    """Настраивает логирование в файл и в консоль.

    Parameters
    ----------
    console_level : int
        Уровень сообщений для консоли, например logging.WARNING.
        В файл calculator.log всегда пишутся все сообщения (DEBUG).
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("calculator.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s"
    ))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def main():
    """Запускает интерактивный цикл калькулятора.

    Читает выражения построчно и печатает результат или сообщение
    об ошибке. Выход: exit, quit, q, Ctrl+C или Ctrl+D (Ctrl+Z в Windows).
    Ключ -v / --verbose включает подробные логи в консоли.
    """
    parser = argparse.ArgumentParser(description="Интерактивный калькулятор")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="выводить в консоль подробные логи (DEBUG)")
    args = parser.parse_args()

    setup_logging(logging.DEBUG if args.verbose else logging.WARNING)
    logger = logging.getLogger(__name__)
    logger.info("Калькулятор запущен")

    calc = Calculator()
    print("Калькулятор. Операции: + - * / ^ ( ), _ — предыдущий результат.")
    print("Для выхода введите exit")

    while True:
        try:
            expression = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            logger.info("Ввод завершён пользователем")
            break

        if expression.lower() in ("exit", "quit", "q"):
            break
        if not expression:
            continue

        try:
            print(calc.calculate(expression))
        except ValueError as e:
            logger.info(f"Ошибка во вводе: {e}")
            print(f"Ошибка: {e}")
        except Exception:
            logger.exception("Неожиданная ошибка")
            print("Неожиданная ошибка, подробности в calculator.log")

    logger.info("Калькулятор завершил работу")


if __name__ == "__main__":
    main()
