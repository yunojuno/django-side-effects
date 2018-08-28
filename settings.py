# minimal settings required for tests to run
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
    }
}

INSTALLED_APPS = (
    'side_effects',
    'test_app'
)

SECRET_KEY = "side-effects"
