import pytest
from transform.lang.tokenizer import tokenize, TokenType, TokenizeError


# ---------- Helpers ----------

def types(tokens):
    """Wyciąga same TokenType z listy tokenów, pomijając END dla czytelności."""
    return [t.type for t in tokens if t.type != TokenType.END]


def types_and_values(tokens):
    return [(t.type, t.value) for t in tokens if t.type != TokenType.END]


# ---------- Liczby ----------

class TestNumbers:
    def test_single_digit_int(self):
        result = tokenize("5")
        assert types_and_values(result) == [(TokenType.NUMBER_INT, 5)]

    def test_multi_digit_int(self):
        result = tokenize("123")
        assert types_and_values(result) == [(TokenType.NUMBER_INT, 123)]

    def test_float(self):
        result = tokenize("1.5")
        assert types_and_values(result) == [(TokenType.NUMBER_FLOAT, 1.5)]

    def test_float_missing_fraction_digit_raises(self):
        with pytest.raises(TokenizeError):
            tokenize("1.")

    def test_number_followed_by_letter_raises(self):
        with pytest.raises(TokenizeError):
            tokenize("123abc")

    def test_number_followed_by_space_and_letter_is_two_tokens(self):
        # to NIE jest błąd tokenizera - patrz dyskusja o granicy odpowiedzialności
        result = tokenize("123 abc")
        assert types(result) == [TokenType.NUMBER_INT, TokenType.IDENTIFIER]

    def test_int_directly_followed_by_concat_no_spaces(self):
        # "1..2" - pojedyncza kropka po cyfrach to część liczby, ale DWIE kropki
        # pod rząd to operator konkatenacji, nie zaczątek ułamka
        result = tokenize("1..2")
        assert types_and_values(result) == [
            (TokenType.NUMBER_INT, 1),
            (TokenType.OPERATOR_CONCAT, None),
            (TokenType.NUMBER_INT, 2),
        ]

    def test_float_directly_followed_by_concat_no_spaces(self):
        result = tokenize("1.5..2.5")
        assert types_and_values(result) == [
            (TokenType.NUMBER_FLOAT, 1.5),
            (TokenType.OPERATOR_CONCAT, None),
            (TokenType.NUMBER_FLOAT, 2.5),
        ]

    def test_int_directly_followed_by_last_condition_operator(self):
        # "1..." - dwie kropki nie są zjadane jako float, trzecia domyka "..."
        result = tokenize("1...")
        assert types(result) == [TokenType.NUMBER_INT, TokenType.OPERATOR_LAST_CONDITION]

    def test_trailing_single_dot_still_raises(self):
        with pytest.raises(TokenizeError):
            tokenize("1.")

    def test_digit_dot_letter_still_raises(self):
        with pytest.raises(TokenizeError):
            tokenize("1.x")


# ---------- Stringi ----------

class TestStrings:
    def test_simple_string(self):
        result = tokenize('"hello"')
        assert types_and_values(result) == [(TokenType.STRING, "hello")]

    def test_string_with_newline_escape(self):
        result = tokenize('"a\\nb"')
        assert result[0].value == "a\nb"

    def test_unknown_escape_raises(self):
        with pytest.raises(TokenizeError):
            tokenize('"a\\qb"')

    def test_unclosed_string_raises(self):
        with pytest.raises(TokenizeError):
            tokenize('"unclosed')

    def test_empty_string(self):
        result = tokenize('""')
        assert types_and_values(result) == [(TokenType.STRING, "")]


# ---------- Identyfikatory, słowa kluczowe, bool ----------

class TestIdentifiersAndKeywords:
    def test_identifier(self):
        result = tokenize("my_var")
        assert types_and_values(result) == [(TokenType.IDENTIFIER, "my_var")]

    def test_if_keyword(self):
        result = tokenize("if")
        assert types_and_values(result) == [(TokenType.KEYWORD_IF, None)]

    def test_true_literal(self):
        result = tokenize("true")
        assert types_and_values(result) == [(TokenType.BOOL, True)]

    def test_false_literal(self):
        result = tokenize("false")
        assert types_and_values(result) == [(TokenType.BOOL, False)]

    def test_identifier_with_underscore_prefix(self):
        result = tokenize("_private")
        assert types_and_values(result) == [(TokenType.IDENTIFIER, "_private")]

    def test_identifier_with_number(self):
        result = tokenize("_private123")
        assert types_and_values(result) == [(TokenType.IDENTIFIER, "_private123")]


# ---------- Operatory jedno- i dwuznakowe ----------

class TestOperators:
    @pytest.mark.parametrize("symbol,expected_type", [
        ("+", TokenType.OPERATOR_ADD),
        ("*", TokenType.OPERATOR_MULTIPLY),
        ("/", TokenType.OPERATOR_DIVIDE),
        ("%", TokenType.OPERATOR_MODULO),
        ("^", TokenType.OPERATOR_POWER),
        ("<", TokenType.OPERATOR_LESS_THAN),
        (">", TokenType.OPERATOR_GREATER_THAN),
        ("~", TokenType.OPERATOR_NOT),
    ])
    def test_single_char_operator_between_operands(self, symbol, expected_type):
        result = tokenize(f"a {symbol} b")
        assert types(result) == [TokenType.IDENTIFIER, expected_type, TokenType.IDENTIFIER]

    @pytest.mark.parametrize("symbol,expected_type", [
        ("==", TokenType.OPERATOR_EQUAL),
        ("~=", TokenType.OPERATOR_NOT_EQUAL),
        (">=", TokenType.OPERATOR_GREATER_EQUAL_THAN),
        ("<=", TokenType.OPERATOR_LESS_EQUAL_THAN),
    ])
    def test_two_char_operator(self, symbol, expected_type):
        result = tokenize(f"a {symbol} b")
        assert types(result) == [TokenType.IDENTIFIER, expected_type, TokenType.IDENTIFIER]

    def test_double_star_is_two_multiply_tokens(self):
        result = tokenize("2**3")
        assert types(result) == [
            TokenType.NUMBER_INT, TokenType.OPERATOR_MULTIPLY,
            TokenType.OPERATOR_MULTIPLY, TokenType.NUMBER_INT,
        ]

    def test_unknown_character_raises(self):
        with pytest.raises(TokenizeError):
            tokenize("a @ b")


# ---------- Unarny minus - to jest krytyczny obszar, testujemy dokładnie ----------

class TestUnaryMinus:
    def test_minus_at_start_of_line_is_unary(self):
        result = tokenize("-5")
        assert types(result) == [TokenType.OPERATOR_NEGATIVE, TokenType.NUMBER_INT]

    def test_minus_between_identifiers_is_binary(self):
        result = tokenize("a - b")
        assert types(result) == [TokenType.IDENTIFIER, TokenType.OPERATOR_SUBTRACT, TokenType.IDENTIFIER]

    def test_minus_after_operator_is_unary(self):
        result = tokenize("a + -b")
        assert types(result) == [
            TokenType.IDENTIFIER, TokenType.OPERATOR_ADD,
            TokenType.OPERATOR_NEGATIVE, TokenType.IDENTIFIER,
        ]

    def test_minus_after_open_paren_is_unary(self):
        result = tokenize("(-5)")
        assert types(result) == [
            TokenType.LEFT_PAREN, TokenType.OPERATOR_NEGATIVE,
            TokenType.NUMBER_INT, TokenType.RIGHT_PAREN,
        ]

    def test_minus_after_comma_is_unary(self):
        result = tokenize("f(a, -b)")
        assert types(result) == [
            TokenType.IDENTIFIER, TokenType.LEFT_PAREN, TokenType.IDENTIFIER,
            TokenType.COMMA, TokenType.OPERATOR_NEGATIVE, TokenType.IDENTIFIER,
            TokenType.RIGHT_PAREN,
        ]

    def test_minus_after_closing_paren_is_binary(self):
        result = tokenize("(a) - 5")
        assert types(result) == [
            TokenType.LEFT_PAREN, TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.OPERATOR_SUBTRACT, TokenType.NUMBER_INT,
        ]

    def test_minus_after_number_is_binary(self):
        result = tokenize("5 - 3")
        assert types(result) == [TokenType.NUMBER_INT, TokenType.OPERATOR_SUBTRACT, TokenType.NUMBER_INT]


# ---------- END token ----------

class TestEndToken:
    def test_end_token_always_appended(self):
        result = tokenize("a")
        assert result[-1].type == TokenType.END

    def test_end_token_on_empty_line(self):
        result = tokenize("")
        assert types(result) == []
        assert result[-1].type == TokenType.END


# ---------- Całe linie - integracja kilku typów tokenów naraz ----------

class TestFullLines:
    def test_simple_instruction(self):
        result = tokenize("add(a, b) > c")
        assert types(result) == [
            TokenType.IDENTIFIER, TokenType.LEFT_PAREN, TokenType.IDENTIFIER,
            TokenType.COMMA, TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER,
        ]

    def test_condition_with_comparison(self):
        result = tokenize("if(a >= b) x > y")
        assert types(result) == [
            TokenType.KEYWORD_IF, TokenType.LEFT_PAREN, TokenType.IDENTIFIER,
            TokenType.OPERATOR_GREATER_EQUAL_THAN, TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.IDENTIFIER, TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER,
        ]

    def test_list_indexing(self):
        result = tokenize("lista[0][1]")
        assert types(result) == [
            TokenType.IDENTIFIER, TokenType.LEFT_BRACKET, TokenType.NUMBER_INT, TokenType.RIGHT_BRACKET,
            TokenType.LEFT_BRACKET, TokenType.NUMBER_INT, TokenType.RIGHT_BRACKET,
        ]

    def test_nested_function_calls(self):
        result = tokenize("format_str(trim(x), y) > out")
        assert types(result) == [
            TokenType.IDENTIFIER, TokenType.LEFT_PAREN,
            TokenType.IDENTIFIER, TokenType.LEFT_PAREN, TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.COMMA, TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER,
        ]

# ---------- Złożone linie z warunkami ----------

class TestConditionalLines:
    def test_condition_with_variable_only(self):
        # if(variable) format_str("rgb({},{},{})", x) > color
        result = tokenize('if(variable) format_str("rgb({},{},{})", x) > color')
        assert types(result) == [
            TokenType.KEYWORD_IF, TokenType.LEFT_PAREN, TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.IDENTIFIER, TokenType.LEFT_PAREN, TokenType.STRING, TokenType.COMMA,
            TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER,
        ]

    def test_condition_with_nested_function_call(self):
        # if(greater(x, 0)) x > y   - warunek to samo wywołanie funkcji, nie porównanie infiksowe
        result = tokenize("if(greater(x, 0)) x > y")
        assert types(result) == [
            TokenType.KEYWORD_IF, TokenType.LEFT_PAREN,
            TokenType.IDENTIFIER, TokenType.LEFT_PAREN, TokenType.IDENTIFIER,
            TokenType.COMMA, TokenType.NUMBER_INT, TokenType.RIGHT_PAREN,
            TokenType.RIGHT_PAREN,
            TokenType.IDENTIFIER, TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER,
        ]

    def test_condition_with_negative_number_comparison(self):
        # if(x >= -1) x > y  - minus zaraz po operatorze porównania musi być unarny
        result = tokenize("if(x >= -1) x > y")
        assert types(result) == [
            TokenType.KEYWORD_IF, TokenType.LEFT_PAREN,
            TokenType.IDENTIFIER, TokenType.OPERATOR_GREATER_EQUAL_THAN,
            TokenType.OPERATOR_NEGATIVE, TokenType.NUMBER_INT,
            TokenType.RIGHT_PAREN,
            TokenType.IDENTIFIER, TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER,
        ]

    def test_condition_with_multiple_outputs(self):
        # if(a) slider_linear(x, 0, 200, step) > x, step
        result = tokenize("if(a) slider_linear(x, 0, -200, step) > x, step")
        assert types(result) == [
            TokenType.KEYWORD_IF, TokenType.LEFT_PAREN, TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.IDENTIFIER, TokenType.LEFT_PAREN,
            TokenType.IDENTIFIER, TokenType.COMMA, TokenType.NUMBER_INT, TokenType.COMMA,
            TokenType.OPERATOR_NEGATIVE, TokenType.NUMBER_INT, TokenType.COMMA, TokenType.IDENTIFIER,
            TokenType.RIGHT_PAREN,
            TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER, TokenType.COMMA, TokenType.IDENTIFIER,
        ]

    def test_arithmetic_expression_with_output(self):
        # a + b - v * 2 > a
        result = tokenize("a + b - v * 2 > a")
        assert types(result) == [
            TokenType.IDENTIFIER, TokenType.OPERATOR_ADD, TokenType.IDENTIFIER,
            TokenType.OPERATOR_SUBTRACT, TokenType.IDENTIFIER, TokenType.OPERATOR_MULTIPLY,
            TokenType.NUMBER_INT,
            TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER,
        ]

    def test_condition_with_equality_and_string(self):
        # if(color == "red") true > matched
        result = tokenize('if(color == "red") true > matched')
        assert types(result) == [
            TokenType.KEYWORD_IF, TokenType.LEFT_PAREN, TokenType.IDENTIFIER,
            TokenType.OPERATOR_EQUAL, TokenType.STRING, TokenType.RIGHT_PAREN,
            TokenType.BOOL, TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER,
        ]

    def test_condition_with_not_equal(self):
        # if(a ~= b) a > result
        result = tokenize("if(a ~= b) a > result")
        assert types(result) == [
            TokenType.KEYWORD_IF, TokenType.LEFT_PAREN, TokenType.IDENTIFIER,
            TokenType.OPERATOR_NOT_EQUAL, TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.IDENTIFIER, TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER,
        ]

    def test_loop_header_line(self):
        # if(a) lista > item, index    (dwukropek zjada YAML/structure builder, tu go nie ma)
        result = tokenize("if(a) lista > item, index")
        assert types(result) == [
            TokenType.KEYWORD_IF, TokenType.LEFT_PAREN, TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.IDENTIFIER,
            TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER, TokenType.COMMA, TokenType.IDENTIFIER,
        ]

    def test_list_append_output(self):
        # trim(item) > items[]   - append syntax to na razie 3 tokeny: IDENTIFIER LBRACKET RBRACKET
        result = tokenize("trim(item) > items[]")
        assert types(result) == [
            TokenType.IDENTIFIER, TokenType.LEFT_PAREN, TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.OPERATOR_GREATER_THAN,
            TokenType.IDENTIFIER, TokenType.LEFT_BRACKET, TokenType.RIGHT_BRACKET,
        ]

    def test_multiple_comparisons_in_condition_not_combined(self):
        # if(a > b) samo GT_OR_SEP - ten sam znak co separator, ale wewnątrz nawiasu
        # sprawdzamy że tokenizer NIE odróżnia znaczenia - oba to OPERATOR_GREATER_THAN,
        # rozróżnienie to zadanie parsera, nie tokenizera
        result = tokenize("if(a > b) c > d")
        gt_positions = [i for i, t in enumerate(types(result)) if t == TokenType.OPERATOR_GREATER_THAN]
        assert len(gt_positions) == 2
        assert types(result) == [
            TokenType.KEYWORD_IF, TokenType.LEFT_PAREN, TokenType.IDENTIFIER,
            TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER, TokenType.RIGHT_PAREN,
            TokenType.IDENTIFIER, TokenType.OPERATOR_GREATER_THAN, TokenType.IDENTIFIER,
        ]

    def test_string_with_special_yaml_looking_chars(self):
        # upewniamy się, że tokenizer nie robi nic dziwnego z tekstem,
        # który wygląda jak YAML (nawiasy klamrowe traktowane jako zwykłe znaki stringa)
        result = tokenize('format_str("rgb({},{},{})", x) > color')
        string_token = next(t for t in result if t.type == TokenType.STRING)
        assert string_token.value == "rgb({},{},{})"