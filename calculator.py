import re
import logging

class Calculator:
    """Калькулятор вещественных выражений на основе рекурсивного спуска.

    Поддерживает операции + - * / ^ (или **), скобки, унарные + и -,
    числа inf и nan и предыдущий результат _. Приоритет операций
    (от низшего к высшему): + и -, затем * и /, затем унарный знак,
    затем степень. Степень правоассоциативна: 2^3^2 = 2^(3^2).

    Деление на ноль, ноль в отрицательной степени, переполнение и
    отрицательное число в дробной степени не вызывают исключений:
    результатом становится nan или inf, а в лог пишется предупреждение.
    """

    TOKEN_RE = re.compile(
        r"(?P<NUMBER>\d+\.?\d*|\.\d+)"   # числа: 2, 2., 2.5, .5
        r"|(?P<NAME>inf|nan)"            # inf, nan (любой регистр)
        r"|(?P<PREV>_)"                  # предыдущий результат
        r"|(?P<OP>\*\*|[-+*/^()])"       # операторы и скобки; ** раньше *
        r"|(?P<SKIP>\s+)"                # пробелы — пропускаем
        r"|(?P<MISMATCH>.)",             # любой другой символ — ошибка
        re.IGNORECASE,
    )

    def __init__(self):
        """Создаёт калькулятор; предыдущий результат _ равен 0.0."""
        self.last_result = 0.0
        self.logger = logging.getLogger(__name__)
        self.tokens = []
        self.pos = 0

    def tokenize(self, expression):
        """Разбивает строку выражения на токены.

        Parameters
        ----------
        expression : str
            Выражение, например "2 * (3 + _) ** -1".

        Returns
        -------
        list of float or str
            Числа (включая inf и nan) в виде float, операторы, скобки
            и _ в виде строк. Оператор ** заменяется на ^.

        Raises
        ------
        ValueError
            Если в выражении есть недопустимый символ.
        """
        tokens = []
        for m in self.TOKEN_RE.finditer(expression):
            kind = m.lastgroup
            text = m.group()

            if kind == "NUMBER" or kind == "NAME":
                tokens.append(float(text))
            elif kind == "PREV" or kind == "OP":
                if text == "**":
                    text = "^"
                tokens.append(text)
            elif kind == "SKIP":
                continue
            elif kind == "MISMATCH":
                raise ValueError(f"неизвестный символ {text}")
        self.logger.debug(f"Токены для {expression}: {tokens}")
        return tokens

    def peek(self):
        """Возвращает текущий токен, не сдвигая позицию (None в конце)."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self):
        """Возвращает текущий токен и переходит к следующему."""
        token = self.peek()
        self.pos += 1
        return token

    def parse_expr(self):
        """Вычисляет сумму или разность слагаемых: term (('+' | '-') term)*."""
        result = self.parse_term()
        while self.peek() in ("+", "-"):
            op = self.advance()
            right = self.parse_term()
            if op == "+":
                result += right
            else:
                result -= right
        return result

    def parse_term(self):
        """Вычисляет произведение или частное: unary (('*' | '/') unary)*.

        Деление на ноль даёт nan и пишет предупреждение в лог.
        """
        result = self.parse_unary()
        while self.peek() in ("*", "/"):
            op = self.advance()
            right = self.parse_unary()
            if op == "*":
                result *= right
            elif right == 0:
                result = float("nan")
                self.logger.warning("Деление на ноль, результат nan")
            else:
                result /= right
        return result

    def parse_unary(self):
        """Вычисляет выражение с унарными знаками: ('+' | '-')* power.

        Унарный минус слабее степени: -2^2 = -(2^2) = -4.
        """
        negative = False
        while self.peek() in ("+", "-"):
            if self.advance() == "-":
                negative = not negative
        result = self.parse_power()
        if negative:
            return -result
        return result

    def parse_power(self):
        """Вычисляет степень: atom ('^' unary)?.

        Показатель разбирается через parse_unary, поэтому допустимы
        2^-1 и правоассоциативная цепочка 2^3^2 = 2^(3^2).
        """
        base = self.parse_atom()
        if self.peek() == "^":
            self.advance()
            exponent = self.parse_unary()
            return self.power(base, exponent)
        return base

    def power(self, base, exponent):
        """Возводит base в степень exponent без исключений.

        Parameters
        ----------
        base : float
            Основание.
        exponent : float
            Показатель степени.

        Returns
        -------
        float
            base ** exponent. Особые случаи:
            ноль в отрицательной степени — inf;
            переполнение — inf или -inf (для отрицательного основания
            в нечётной степени);
            отрицательное основание в дробной степени — nan.
        """
        try:
            result = base ** exponent
        except ZeroDivisionError:
            self.logger.warning("Ноль в отрицательной степени")
            return float("inf")
        except OverflowError:
            if base < 0 and not exponent.is_integer():
                self.logger.warning("Отрицательное число в дробной степени, результат nan")
                return float("nan")
            self.logger.warning("Переполнение при возведении в степень")
            if base < 0 and exponent % 2 == 1:
                return float("-inf")
            return float("inf")
        if isinstance(result, complex):
            self.logger.warning("Отрицательное число в дробной степени, результат nan")
            return float("nan")
        return result

    def parse_atom(self):
        """Вычисляет атом: число, _ или выражение в скобках.

        Raises
        ------
        ValueError
            Если нет закрывающей скобки, выражение оборвалось
            или встретился неожиданный токен.
        """
        token = self.advance()
        if isinstance(token, float):
            return token
        if token == "_":
            return self.last_result
        if token == "(":
            value = self.parse_expr()
            if self.advance() != ")":
                raise ValueError("Не хватает закрывающей скобки")
            return value
        if token is None:
            raise ValueError("Неожиданный конец выражения")
        raise ValueError(f"Неожиданный токен: {token}")

    def calculate(self, expression):
        """Вычисляет выражение и запоминает результат как _.

        Parameters
        ----------
        expression : str
            Выражение, например "-(2 + 3) ^ 2 / _".

        Returns
        -------
        float
            Значение выражения (может быть inf, -inf или nan).

        Raises
        ------
        ValueError
            Если выражение пустое, содержит недопустимый символ,
            синтаксическую ошибку или слишком глубокую вложенность.
            Предыдущий результат при этом не меняется.
        """
        self.logger.info(f"Вычисление: {expression}")
        self.tokens = self.tokenize(expression)
        self.pos = 0
        if not self.tokens:
            raise ValueError("Пустое выражение")
        try:
            result = self.parse_expr()
        except RecursionError:
            raise ValueError("Слишком глубокая вложенность выражения") from None
        if self.peek() is not None:
            raise ValueError(f"Лишний токен: {self.peek()}")
        self.last_result = result
        self.logger.info(f"Результат: {result}")
        return result
