import os

from apis_acdhch_default_settings.settings import *  # noqa: F403

INSTALLED_APPS += ["apis_core.documentation"]  # noqa: F405
INSTALLED_APPS += ["apis_acdhch_django_invite"]
INSTALLED_APPS += ["django_json_editor_field"]
INSTALLED_APPS += ["django_interval"]
INSTALLED_APPS += ["simple_history"]
INSTALLED_APPS += ["sass_processor"]
INSTALLED_APPS += ["mine_frontend"]
INSTALLED_APPS += ["mine_edit"]

INSTALLED_APPS += ["django.contrib.postgres"]

ROOT_URLCONF = "apis_ontology.urls"

LANGUAGE_CODE = "de"


MIDDLEWARE += [  # noqa: F405
    "auditlog.middleware.AuditlogMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ADDITIONAL_MODULE_LOOKUP_PATHS = ["apis_ontology", "apis_acdhch_default_settings"]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "sass_processor.finders.CssFinder",
]
# SASS_ROOT = os.path.join(BASE_DIR, "mine_frontend", "static", "theme", "css")
# STORAGES = {
#    "sass_processor": {
#        "ROOT": SASS_ROOT,
#    }
# }
#
CSP_DEFAULT_SRC = CSP_DEFAULT_SRC + (  # noqa: F405
    "*.jquery.com",
    "*.googleapis.com",
    "*.gstatic.com",
    "*.rawgit.com",
)

CSP_IMG_SRC += [  # noqa: F405
    "*.wikimedia.org",
    "*.acdh.oeaw.ac.at",
]

STATICFILES_DIRS = [
    "/data/static_files/",
]

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": "for-imgproxy",  # Required; use env var
            "access_key": os.environ.get("AWS_S3_ACCESS_KEY_ID"),
            "secret_key": os.environ.get("AWS_S3_SECRET_ACCESS_KEY"),
            "endpoint_url": os.environ.get("AWS_S3_ENDPOINT_URL"),
            # Optional: "region_name": "eu-central-1",
        },
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
