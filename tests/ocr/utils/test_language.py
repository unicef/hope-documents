from hope_documents.utils.language import fqn


class MyClass:
    def my_method(self):
        pass


def my_function():
    pass


def test_fqn_with_class():
    """Test that fqn returns the correct fully qualified name for a class."""
    assert fqn(MyClass) == "test_language.MyClass"


def test_fqn_with_function():
    """Test that fqn returns the correct fully qualified name for a function."""
    assert fqn(my_function) == "test_language.my_function"


def test_fqn_with_method():
    """Test that fqn returns the correct fully qualified name for a method."""
    instance = MyClass()
    assert fqn(instance.my_method) == "test_language.MyClass.my_method"
