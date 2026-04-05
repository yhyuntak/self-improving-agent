import os

from minimal_agent_harness.config import load_dotenv_if_present


def test_load_dotenv_if_present_reads_missing_env_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# comment",
                "OPENROUTER_API_KEY=test-key",
                'OPENROUTER_MODEL="openai/gpt-oss-20b"',
            ]
        )
    )

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    load_dotenv_if_present(env_file)

    assert os.environ["OPENROUTER_API_KEY"] == "test-key"
    assert os.environ["OPENROUTER_MODEL"] == "openai/gpt-oss-20b"


def test_load_dotenv_if_present_does_not_override_existing_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENROUTER_MODEL=openai/gpt-oss-20b\n")

    monkeypatch.setenv("OPENROUTER_MODEL", "custom/model")

    load_dotenv_if_present(env_file)

    assert os.environ["OPENROUTER_MODEL"] == "custom/model"
