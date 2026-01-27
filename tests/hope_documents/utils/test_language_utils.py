from hope_documents.utils.language import (
    Dummy,
    classproperty,
    flatten,
    get_attr,
    is_simple,
    repr_list,
)


def test_is_simple():
    assert is_simple(1) is True
    assert is_simple("hello") is True
    assert is_simple([1, 2]) is True
    assert is_simple({"a": 1}) is True

    class MyClass:
        pass

    assert is_simple(MyClass()) is False
    assert is_simple(Dummy()) is False


def test_flatten():
    assert flatten([]) == []
    assert flatten([1, 2, 3]) == [1, 2, 3]
    assert flatten([1, [2, 3], 4]) == [1, 2, 3, 4]
    assert flatten([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]
    assert flatten(["a", ["b", "c"], "d"]) == ["a", "b", "c", "d"]
    assert flatten(["a", [("b", "c")], "d"]) == ["a", "b", "c", "d"]


def test_get_attr():
    class MyObject:
        def __init__(self):
            self.a = 1
            self.b = MyObject2()

    class MyObject2:
        def __init__(self):
            self.c = "hello"

    obj = MyObject()

    assert get_attr(obj, "a") == 1
    assert get_attr(obj, "b.c") == "hello"
    assert get_attr(obj, "x") is None
    assert get_attr(obj, "x", "default_value") == "default_value"
    assert get_attr(obj, "b.x", "default_value") == "default_value"


def test_classproperty():
    class MyClass:
        _value = "class_value"

        @classproperty
        def value(cls):
            return cls._value

    assert MyClass.value == "class_value"
    assert MyClass().value == "class_value"


def test_repr_list():
    assert repr_list([]) == ""
    assert repr_list(["a", "b", "c"]) == "'a', 'b', 'c'"
    assert repr_list([1, 2, 3]) == "'1', '2', '3'"
