# tests/test_environment.py
import pytest
from transform.lang.environment import (
    Environment, UndefinedVariableError, VariableTypeConflictError,
)


class TestBasicGetSet:
    def test_get_undefined_raises(self):
        env = Environment(static_store={})
        with pytest.raises(UndefinedVariableError):
            env.get("x")

    def test_set_creates_dynamic_variable(self):
        env = Environment(static_store={})
        env.set("x", 5)
        assert env.get("x") == 5

    def test_set_updates_static_variable(self):
        static = {"x": 0}
        env = Environment(static_store=static)
        env.set("x", 42)
        assert static["x"] == 42
        assert env.get("x") == 42

    def test_dynamic_does_not_leak_into_static_store(self):
        static = {}
        env = Environment(static_store=static)
        env.set("temp", 1)
        assert "temp" not in static

    def test_exists(self):
        env = Environment(static_store={"a": 1})
        env.set("b", 2)
        assert env.exists("a") is True
        assert env.exists("b") is True
        assert env.exists("c") is False


class TestDeclare:
    def test_declare_creates_with_default(self):
        env = Environment(static_store={})
        env.declare("x", None)
        assert env.get("x") is None

    def test_declare_does_not_overwrite_existing_dynamic(self):
        env = Environment(static_store={})
        env.set("x", 5)
        env.declare("x", None)
        assert env.get("x") == 5

    def test_declare_does_not_overwrite_existing_static(self):
        env = Environment(static_store={"x": 10})
        env.declare("x", None)
        assert env.get("x") == 10

    def test_declare_list_default(self):
        env = Environment(static_store={})
        env.declare("items", [])
        assert env.get("items") == []


class TestAppendToList:
    def test_append_creates_list_if_missing(self):
        env = Environment(static_store={})
        env.append_to_list("items", "a")
        assert env.get("items") == ["a"]

    def test_append_multiple_values(self):
        env = Environment(static_store={})
        env.append_to_list("items", "a")
        env.append_to_list("items", "b")
        assert env.get("items") == ["a", "b"]

    def test_append_to_non_list_raises(self):
        env = Environment(static_store={})
        env.set("x", 5)
        with pytest.raises(VariableTypeConflictError):
            env.append_to_list("x", "a")

    def test_append_persists_in_static_across_environments(self):
        static = {"items": []}
        env1 = Environment(static_store=static)
        env1.append_to_list("items", "a")
        env2 = Environment(static_store=static)
        assert env2.get("items") == ["a"]


class TestChildScope:
    def test_child_sees_parent_dynamic_values(self):
        env = Environment(static_store={})
        env.set("x", 1)
        child = env.child_scope()
        assert child.get("x") == 1

    def test_child_sees_parent_static_values(self):
        env = Environment(static_store={"x": 1})
        child = env.child_scope()
        assert child.get("x") == 1

    def test_child_writes_do_not_leak_to_parent_dynamic(self):
        env = Environment(static_store={})
        child = env.child_scope()
        child.set("item", "value")
        assert not env.exists("item")

    def test_child_writes_to_static_leak_to_parent(self):
        static = {"x": 0}
        env = Environment(static_store=static)
        child = env.child_scope()
        child.set("x", 99)
        assert env.get("x") == 99

    def test_multiple_children_are_isolated_from_each_other(self):
        env = Environment(static_store={})
        env.set("shared_dynamic", "base")
        child_a = env.child_scope()
        child_b = env.child_scope()
        child_a.set("item", "A")
        child_b.set("item", "B")
        assert child_a.get("item") == "A"
        assert child_b.get("item") == "B"
        assert not env.exists("item")


class TestFlush:
    def test_flush_clears_dynamic_variables(self):
        env = Environment(static_store={})
        env.set("x", 1)
        env.declare("items", [])
        env.flush()
        assert not env.exists("x")
        assert not env.exists("items")

    def test_flush_keeps_static_variables_and_their_values(self):
        static = {"counter": 5}
        env = Environment(static_store=static)
        env.set("counter", 6)
        env.flush()
        assert env.exists("counter")
        assert env.get("counter") == 6
        assert static["counter"] == 6

    def test_flush_on_empty_dynamic_is_a_no_op(self):
        env = Environment(static_store={"a": 1})
        env.flush()
        assert env.get("a") == 1

    def test_declare_after_flush_uses_default_again(self):
        env = Environment(static_store={})
        env.set("x", "line one value")
        env.flush()
        env.declare("x", None)
        assert env.get("x") is None

    def test_flush_does_not_touch_a_different_environment_sharing_static(self):
        static = {"a": 1}
        env1 = Environment(static_store=static)
        env2 = Environment(static_store=static)
        env1.set("temp", "only in env1")
        env1.flush()
        env2.set("b", 2)
        assert not env2.exists("temp")
        assert env2.get("b") == 2