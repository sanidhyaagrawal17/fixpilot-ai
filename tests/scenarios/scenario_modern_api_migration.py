"""Scenario 6: Tavily Live-Docs Spotlight (Pydantic v2 Migration: BaseSettings)
Demonstrates real-time web grounding when legacy code imports BaseSettings from `pydantic`
instead of `pydantic_settings`. Legacy-trained LLMs often hallucinate outdated Pydantic v1 syntax,
allowing Tavily Search + Nemotron 3 Ultra to retrieve ground-truth documentation and apply the correct patch.
"""

DESCRIPTION = "PydanticImportError: BaseSettings moved to pydantic-settings in modern Pydantic v2 migration"

SOURCE_CODE = """from pydantic import BaseModel, BaseSettings

class ServiceConfig(BaseSettings):
    service_name: str = "FixPilot Autonomous Engine"
    api_version: str = "v1"
    max_concurrency: int = 16

def load_service_config():
    # Bug: In Pydantic v2, BaseSettings was moved to the separate pydantic_settings package
    return ServiceConfig()
"""

ERROR_TRACEBACK = """Traceback (most recent call last):
  File "solution.py", line 1, in <module>
    from pydantic import BaseModel, BaseSettings
pydantic.errors.PydanticImportError: `BaseSettings` has been moved to the `pydantic-settings` package. See https://docs.pydantic.dev/2.13/migration/#basesettings-has-moved-to-pydantic-settings for more details.
"""

TEST_CODE = """from solution import load_service_config

def test_service_config():
    cfg = load_service_config()
    assert cfg.service_name == "FixPilot Autonomous Engine"
    assert cfg.api_version == "v1"
    assert cfg.max_concurrency == 16
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_service_config()
"""
