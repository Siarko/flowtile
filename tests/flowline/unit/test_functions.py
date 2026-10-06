import pytest
from transform.lang.functions import build_core_registry, FunctionCallError
from transform.lang.functions import FunctionRegistry, FunctionSpec, ValueType


@pytest.fixture
def registry():
    return build_core_registry()


class TestArithmetic:
    def test_add(self, registry):
        assert registry.call("add", [2, 3]) == 5

    def test_add_float(self, registry):
        assert registry.call("add", [2.5, 1.5]) == 4.0

    def test_sub(self, registry):
        assert registry.call("sub", [5, 3]) == 2

    def test_mul(self, registry):
        assert registry.call("mul", [4, 3]) == 12

    def test_div(self, registry):
        assert registry.call("div", [10, 4]) == 2.5

    def test_div_by_zero_raises(self, registry):
        with pytest.raises(FunctionCallError):
            registry.call("div", [1, 0])

    def test_pow(self, registry):
        assert registry.call("pow", [2, 3]) == 8

    def test_neg(self, registry):
        assert registry.call("neg", [5]) == -5

    def test_mod(self, registry):
        assert registry.call("mod", [7, 3]) == 1


class TestTypeValidation:
    def test_add_rejects_string(self, registry):
        with pytest.raises(FunctionCallError):
            registry.call("add", [1, "2"])

    def test_add_rejects_bool_disguised_as_int(self, registry):
        with pytest.raises(FunctionCallError):
            registry.call("add", [True, 5])

    def test_wrong_arity_raises(self, registry):
        with pytest.raises(FunctionCallError):
            registry.call("add", [1, 2, 3])

    def test_unknown_function_raises(self, registry):
        with pytest.raises(FunctionCallError):
            registry.call("nonexistent", [1, 2])


class TestComparisons:
    def test_equals_numbers(self, registry):
        assert registry.call("eq", [5, 5]) is True

    def test_equals_strings(self, registry):
        assert registry.call("eq", ["a", "b"]) is False

    def test_greater(self, registry):
        assert registry.call("gt", [5, 3]) is True

    def test_less_or_equal(self, registry):
        assert registry.call("lteq", [3, 3]) is True


class TestLogic:
    def test_and(self, registry):
        assert registry.call("and", [True, False]) is False

    def test_or(self, registry):
        assert registry.call("or", [True, False]) is True

    def test_not(self, registry):
        assert registry.call("not", [True]) is False

    def test_and_rejects_non_bool(self, registry):
        with pytest.raises(FunctionCallError):
            registry.call("and", [1, True])


class TestRegistryIsolation:
    def test_two_registries_are_independent(self):

        r1 = build_core_registry()
        r2 = build_core_registry()
        r2.register(FunctionSpec("double", [ValueType.NUMERIC], lambda a: a * 2))

        assert "double" not in r1
        assert r2.call("double", [5]) == 10

    def test_registering_duplicate_raises(self, registry):

        with pytest.raises(ValueError):
            registry.register(FunctionSpec("add", [ValueType.NUMERIC, ValueType.NUMERIC], lambda a, b: a + b))