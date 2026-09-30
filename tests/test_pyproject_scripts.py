from pathlib import Path


PYPROJECT = Path("pyproject.toml").read_text()

EXPECTED_SCRIPTS = {
    "ai-toolkit",
    "install-skills",
    "install-mcp-servers",
    "install-pi-config",
    "install-agent-rules",
    "install-omp-commands",
    "install-provider-blocks",
    "install-hooks",
    "fetch-pr-review",
    "forge-issue",
    "forge-detect",
    "repo-maintenance",
}


def test_all_public_console_scripts_are_registered():
    scripts_section = PYPROJECT.split("[project.scripts]", 1)[1].split("[", 1)[0]
    registered = {
        line.split("=", 1)[0].strip()
        for line in scripts_section.splitlines()
        if "=" in line
    }

    assert registered == EXPECTED_SCRIPTS
