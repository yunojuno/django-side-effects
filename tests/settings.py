# minimal settings required for tests to run
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

INSTALLED_APPS = ("side_effects", "tests")

SECRET_KEY = "side-effects"  # noqa: S105
