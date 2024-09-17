"""
Configuration for threadmem
"""

import os

AGENTSEA_HOME = os.path.expanduser(os.environ.get("AGENTSEA_HOME", "~/.agentsea"))
AGENTSEA_DB_DIR = os.path.expanduser(
    os.environ.get("AGENTSEA_DB_DIR", os.path.join(AGENTSEA_HOME, "data"))
)
AGENTSEA_LOG_DIR = os.path.expanduser(
    os.environ.get("AGENTSEA_LOG_DIR", os.path.join(AGENTSEA_HOME, "logs"))
)
AGENTSEA_PROC_DIR = os.path.expanduser(
    os.environ.get("AGENTSEA_PROC_DIR", os.path.join(AGENTSEA_HOME, "proc"))
)
DB_TEST = os.environ.get("AGENTSEA_DB_TEST", "false") == "true"
DB_NAME = os.environ.get("SKILLS_DB_NAME", "skills.db")
if DB_TEST:
    DB_NAME = "skills_test.db"
