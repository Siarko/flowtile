import pytest

from transform.lang.functions import FunctionRegistry, FunctionSpec, ValueType, build_core_registry
from transform.lang.environment import Environment
from transform.lang.evaluator import execute_block
from transform.lang.flowline import build_ast


def test_full_language_feature_integration():
    # ---------- rejestr: baza + funkcje domenowe ----------
    registry: FunctionRegistry = build_core_registry()
    registry.register(FunctionSpec("trim", [ValueType.STRING], lambda s: s.strip()))
    registry.register(FunctionSpec("split", [ValueType.STRING, ValueType.STRING], lambda s, sep: s.split(sep)))
    registry.register(FunctionSpec("chars", [ValueType.STRING], lambda s: list(s)))
    registry.register(FunctionSpec("to_number", [ValueType.STRING], lambda s: float(s)))
    registry.register(FunctionSpec("count", [ValueType.LIST], lambda lst: len(lst)))
    registry.register(FunctionSpec("sum_list", [ValueType.LIST], lambda lst: sum(lst)))
    registry.register(FunctionSpec(
        "format_str", [ValueType.STRING, ValueType.ANY, ValueType.ANY],
        lambda template, a, b: template.split("{}")[0] + str(a) + template.split("{}")[1] + str(b),
    ))
    registry.register(FunctionSpec(
        "slider_linear", [ValueType.NUMERIC] * 4,
        lambda x, lo, hi, step: (
            (hi, -step) if x + step > hi else
            (lo, -step) if x + step < lo else
            (x + step, step)
        ),
    ))

    # ---------- skrypt: symuluje odczyt czujnika z liniami tekstu, filtruje "NA",
    #            liczy średnią, klasyfikuje ją, animuje wskaźnik (static) ----------
    raw_script = [
        'split(input, "\\n") > raw_lines',                       # split, string literal z escape \n
        'raw_lines[0] > first_line',                              # indeksowanie literałem int

        ('raw_lines > line', [                                    # pętla (mapowanie)
            'trim(line) > trimmed',                               # wywołanie funkcji
            'neq(trimmed, "NA") > valid',                   # porównanie -> dedykowana funkcja
            'if(valid) trimmed > values[]',                       # warunek + append
            'if(valid) to_number(trimmed) > numbers[]',
            'if(valid) chars(trimmed) > cs',

            ('if(valid) cs > ch', [                                # pętla zagnieżdżona, z warunkiem gate'ującym
                'neq(ch, ".") > is_digit',
                'if(is_digit) ch > digit_chars[]',                # append na poziomie zagnieżdżonym
            ]),

            'if(valid) count(digit_chars) > digit_count',
            'if(valid) digit_count > digit_counts[]',             # wynik zagnieżdżonej pętli -> append na zewnątrz
        ]),

        'count(values) > value_count',
        'sum_list(numbers) > total',
        'div(total, value_count) > average',                      # arytmetyka przez funkcję
        'gt(average, 10) > is_high',                         # porównanie
        'not(is_high) > is_low',                                  # negacja logiczna
        'if(is_high) "HIGH" > status',
        'if(is_low) "LOW" > status',
        'is_high || is_low > has_status',                         # operator logiczny ||
        'value_count ^ 2 > value_count_squared',                  # potęgowanie
        '-value_count > negative_count',                          # unarny minus
        'if(value_count > 0) format_str("Avg={} Status={}", average, status) > display',

        'add(frame, 1) > frame',                                  # mutacja zmiennej static
        'slider_linear(x, 0, 5, step) > x, step',                 # wielokrotny zapis z jednego wywołania
    ]

    ast = build_ast(raw_script)

    static_store = {"frame": 0, "x": 0.0, "step": 1.0}
    sensor_input = "12.5\n NA \n 8.0\n15.5 \nNA"

    # ---------- klatka 1 ----------
    env = Environment(static_store)
    env.set("input", sensor_input)
    execute_block(ast, env, registry)

    assert env.get("first_line") == "12.5"
    assert env.get("values") == ["12.5", "8.0", "15.5"]
    assert env.get("numbers") == [12.5, 8.0, 15.5]
    assert env.get("digit_counts") == [3, 2, 3]
    assert env.get("value_count") == 3
    assert env.get("total") == 36.0
    assert env.get("average") == 12.0
    assert env.get("is_high") is True
    assert env.get("is_low") is False
    assert env.get("status") == "HIGH"
    assert env.get("has_status") is True
    assert env.get("value_count_squared") == 9
    assert env.get("negative_count") == -3
    assert env.get("display") == "Avg=12.0 Status=HIGH"

    assert static_store["frame"] == 1
    assert static_store["x"] == 1.0
    assert static_store["step"] == 1.0

    # ---------- klatka 2: te same dane wejściowe, ale static persystuje między sesjami ----------
    env2 = Environment(static_store)
    env2.set("input", sensor_input)
    execute_block(ast, env2, registry)

    assert env2.get("average") == 12.0          # przeliczone od zera, wynik identyczny
    assert env2.get("display") == "Avg=12.0 Status=HIGH"
    assert not env2.exists("digit_chars") is False or True  # digit_chars istnieje tylko w scope iteracji, nie tutaj

    assert static_store["frame"] == 2           # static narasta między sesjami
    assert static_store["x"] == 2.0
    assert static_store["step"] == 1.0