from smart_env import SmartEnv

CONFIG = {
    "DEBUG": (
        bool,
        False,
        True,
        False,
        "https://docs.djangoproject.com/en/5.1/ref/settings/#debug",
    ),
    "DATABASE_URL": (
        str,
        "",
        "sqlite:///demo.db",
        True,
        "https://docs.djangoproject.com/en/5.1/ref/settings/#DATABASES",
    ),
}

env = SmartEnv(**CONFIG)
