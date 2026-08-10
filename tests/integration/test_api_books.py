import importlib
import os


def test_books_dir_honors_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv('LIBRO_BOOKS_DIR', str(tmp_path))
    import app as app_module
    importlib.reload(app_module)
    try:
        assert app_module.BOOKS_DIR == tmp_path
    finally:
        monkeypatch.delenv('LIBRO_BOOKS_DIR', raising=False)
        importlib.reload(app_module)
