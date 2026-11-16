import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured


@pytest.fixture
def reload_llm(monkeypatch):
    """Reload the llm settings fragment with controlled HOPE_* env vars.

    Pass backend=<json string> to set HOPE_LLM_BACKEND, or omit to unset it.
    Pass chain=<string> to set HOPE_EXTRACTOR_CHAIN, or omit to use the default.
    """
    import hope_documents.config.fragments.llm as _mod

    def _go(*, backend=None, chain=None):
        if backend is None:
            monkeypatch.delenv("HOPE_LLM_BACKEND", raising=False)
        else:
            monkeypatch.setenv("HOPE_LLM_BACKEND", backend)
        if chain is None:
            monkeypatch.delenv("HOPE_EXTRACTOR_CHAIN", raising=False)
        else:
            monkeypatch.setenv("HOPE_EXTRACTOR_CHAIN", chain)
        return importlib.reload(_mod)

    yield _go
    # Clear any HOPE_* vars set during the test before the restore-reload so that
    # a "raises" test cannot leave a bad value in os.environ and cause teardown to
    # raise ImproperlyConfigured.
    monkeypatch.delenv("HOPE_LLM_BACKEND", raising=False)
    monkeypatch.delenv("HOPE_EXTRACTOR_CHAIN", raising=False)
    importlib.reload(_mod)


def test_llm_backend_none_when_env_absent(reload_llm):
    mod = reload_llm()
    assert mod.LLM_BACKEND is None


def test_llm_backend_set_from_valid_json(reload_llm):
    cfg = (
        '{"provider": "hope_documents.llm.backends.OllamaBackend",'
        ' "host": "http://localhost:11434", "model": "llama3.2-vision"}'
    )
    mod = reload_llm(backend=cfg)
    assert mod.LLM_BACKEND == {
        "provider": "hope_documents.llm.backends.OllamaBackend",
        "host": "http://localhost:11434",
        "model": "llama3.2-vision",
    }


def test_llm_backend_accepts_json_null(reload_llm):
    mod = reload_llm(backend="null")
    assert mod.LLM_BACKEND is None


def test_llm_backend_invalid_json_raises(reload_llm):
    with pytest.raises(ImproperlyConfigured, match="not valid JSON"):
        reload_llm(backend="{invalid json}")


def test_llm_backend_non_dict_raises(reload_llm):
    with pytest.raises(ImproperlyConfigured, match="JSON object or null"):
        reload_llm(backend='"just a string"')


def test_extractor_chain_defaults_to_ocr(reload_llm):
    mod = reload_llm()
    assert mod.EXTRACTOR_CHAIN == ["ocr"]


def test_extractor_chain_strips_whitespace(reload_llm):
    mod = reload_llm(chain="ocr, llm")
    assert mod.EXTRACTOR_CHAIN == ["ocr", "llm"]
