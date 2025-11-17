def get_journal_file_path(journal_name: str = "default") -> str:
    journal, journal_file = get_journal(journal_name)
    return journal_file


def get_journal(journal_name: str = "default") -> tuple["Journal", str]:
    # Delay these imports to avoid circular-import during module import.
    from jrnl import install
    from jrnl.config import scope_config
    from jrnl.journals import Journal
    config = install.load_or_install_jrnl("")
    config = scope_config(config, journal_name)
    journal_file = config["journal"]
    journal = Journal()
    journal.open(journal_file)
    return journal, journal_file
