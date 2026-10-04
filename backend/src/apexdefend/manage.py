import argparse

from alembic import command
from alembic.config import Config

from .config import HANDOFF, ROOT, Settings
from .db import Database


def initialize(settings=None):
    settings = settings or Settings()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "backend/migrations"))
    cfg.attributes["settings"] = settings
    command.upgrade(cfg, "head")
    db = Database(settings)
    db.seed(HANDOFF / "fixtures/local-reference-data.json")
    return db


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init"])
    parser.parse_args()
    initialize()
    print("Database migrated; synthetic local reference data seeded. No cases or scores were preloaded.")
