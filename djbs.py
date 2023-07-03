import random
import secrets
import sys
from io import BytesIO
from pathlib import Path
from subprocess import run
from zipfile import ZipFile

from args import parse_args
from thttp import request

from textwrap import dedent


EXAMPLE_MANAGEMENT_COMMAND = """# Example management command
# https://docs.djangoproject.com/en/4.0/howto/custom-management-commands/

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "An example management command created by djbs"

    def handle(self, *args, **options):
        self.stdout.write("Configure your management commands here...")
        raise CommandError("Management command not implemented")"""


def create_project_directory(dir):
    dir.mkdir()
    return dir


def django_install(dir):
    run(["pipenv install django"], shell=True, check=True, cwd=dir)


def django_startproject(dir, project_name):
    run(
        [f"pipenv run django-admin startproject {project_name} ."],
        shell=True,
        check=True,
        cwd=dir,
    )


def django_secret_key_in_env(dir, project_name):
    settings = open(dir / project_name / "settings.py", "r").read().splitlines()

    for i, l in enumerate(settings):
        if l.startswith("from pathlib import Path"):
            settings[i] = "import os\nfrom pathlib import Path"

        if l.startswith("SECRET_KEY ="):
            settings[i] = f'SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "totally-insecure")'

        if l.startswith("DEBUG ="):
            settings[i] = (
                l
                + "\n"
                + """if not DEBUG and SECRET_KEY == "totally-insecure":
    raise Exception("Do not run with the default secret key in production")"""
            )

    with open(dir / project_name / "settings.py", "w") as f:
        f.write("\n".join(settings))

    with open(dir / ".env", "w") as f:
        f.write(f"DJANGO_SECRET_KEY={secrets.token_urlsafe(40)}")


def django_set_allowed_hosts(dir, project_name, domain):
    settings = open(dir / project_name / "settings.py", "r").read()
    settings = settings.replace("ALLOWED_HOSTS = []", f'ALLOWED_HOSTS = ["{domain}", "localhost"]')

    with open(dir / project_name / "settings.py", "w") as f:
        f.write(settings)


def django_startapp(dir, app_name):
    run(
        [f"pipenv run python manage.py startapp {app_name}"],
        shell=True,
        check=True,
        cwd=dir,
    )


def django_run_migrations(dir, app_name):
    run([f"pipenv run python manage.py migrate"], shell=True, check=True, cwd=dir)


def django_add_app_to_installed_apps(dir, project_name, app):
    settings = open(dir / project_name / "settings.py", "r").read()
    settings = settings.replace('"django.contrib.staticfiles",', f'"django.contrib.staticfiles",\n    "{app}",')

    with open(dir / project_name / "settings.py", "w") as f:
        f.write(settings)


def django_add_base_template(dir, project_name, app):
    p = dir / app / "templates"
    p.mkdir()

    basehtml = request("https://basehtml.xyz").content.decode()
    basehtml = basehtml.split("<!--")[0] + "{% block content %}{% endblock %}\n\n</body>\n</html>"

    with open(p / "base.html", "w") as f:
        f.write(basehtml)


def django_add_management_command(dir, project_name, app):
    management_command_dir = dir / app / "management" / "commands"
    management_command_dir.mkdir(parents=True)

    with open(management_command_dir / "example_command.py", "w") as f:
        f.write(EXAMPLE_MANAGEMENT_COMMAND)

    with open(dir / app / "management" / "__init__.py", "w") as f:
        f.write("")

    with open(management_command_dir / "__init__.py", "w") as f:
        f.write("")


def django_add_style_css(dir, project_name, app):
    p = dir / app / "static" / "css"
    p.mkdir(parents=True)

    with open(p / "style.css", "w") as f:
        f.write("")


def django_add_favicon(dir, project_name, app):
    favicon = request("https://raw.githubusercontent.com/sesh/favicons/main/ico/grape-circle.ico").content

    with open(dir / app / "static" / "favicon.ico", "wb") as f:
        f.write(favicon)


def django_add_up(dir, project_name):
    django_up_zip = BytesIO(request("https://github.com/sesh/django-up/archive/refs/heads/main.zip").content)

    z = ZipFile(django_up_zip)
    z.extractall(dir)
    Path(dir / "django-up-main").replace(dir / "up")

    django_add_app_to_installed_apps(dir, project_name, "up")

    run("pipenv install pyyaml dj-database-url", shell=True, check=True, cwd=dir)

    settings = open(dir / project_name / "settings.py", "r").read()
    settings_before, settings_after = (
        settings.split("DATABASES =")[0][:-12],
        settings.split("DATABASES =")[1].split("}", 2)[2],
    )

    settings = (
        settings_before
        + """\n\nimport dj_database_url
DATABASES = {
    'default': dj_database_url.config(default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}"""
        + settings_after
    )

    settings += "\n\n"
    settings += "# Django Up\n"
    settings += "# https://github.com/sesh/django-up\n\n"
    settings += f"UP_GUNICORN_PORT = {random.randint(11000, 20000)}\n"
    settings += "SECURE_PROXY_SSL_HEADER = ('HTTP_X_SCHEME', 'https')\n"

    with open(dir / project_name / "settings.py", "w") as f:
        f.write(settings)


def django_add_authuser(dir, project_name):
    django_authuser_zip = BytesIO(
        request("https://github.com/sesh/django-authuser/archive/refs/heads/main.zip").content
    )

    z = ZipFile(django_authuser_zip)
    z.extractall(dir)
    Path(dir / "django-authuser-main").replace(dir / "authuser")

    django_add_app_to_installed_apps(dir, project_name, "authuser")

    settings = open(dir / project_name / "settings.py", "r").read()
    settings += '\n\n# Custom user model\n\nAUTH_USER_MODEL = "authuser.User"\nAUTH_USER_ALLOW_SIGNUP = True\n'

    with open(dir / project_name / "settings.py", "w") as f:
        f.write(settings)

    urls = open(dir / project_name / "urls.py", "r").read()
    urls = urls.replace("]", "    path('accounts/', include('authuser.urls')),\n]")
    urls = urls.replace("from django.urls import path", "from django.urls import include, path")

    with open(dir / project_name / "urls.py", "w") as f:
        f.write(urls)


def django_add_default_logging(dir, project_name):
    settings = open(dir / project_name / "settings.py", "r").read()

    settings += "\n\n"
    settings += "# Logging Configuration\n"
    settings += "if DEBUG == False:\n"
    settings += "    LOGGING = {\n"
    settings += '        "version": 1,\n'
    settings += '        "disable_existing_loggers": False,\n'
    settings += '        "handlers": {\n'
    settings += '            "file": {\n'
    settings += '                "level": "DEBUG",\n'
    settings += '                "class": "logging.FileHandler",\n'
    settings += f'                "filename": "/srv/www/{project_name}/logs/debug.log",\n'
    settings += "            },\n"
    settings += "        },\n"
    settings += '        "loggers": {\n'
    settings += '            "django": {\n'
    settings += '                "handlers": ["file"],\n'
    settings += '                "level": "DEBUG",\n'
    settings += '                "propagate": True,\n'
    settings += "            },\n"
    settings += "        },\n"
    settings += "    }\n"

    with open(dir / project_name / "settings.py", "w") as f:
        f.write(settings)


def django_add_wellknown_urls(dir, project_name):
    urls = open(dir / project_name / "urls.py", "r").read()
    urlpatterns = """from django.http import HttpResponse

def robots(request):
    return HttpResponse(
        "User-Agent: *", headers={"Content-Type": "text/plain; charset=UTF-8"}
    )


def security(request):
    return HttpResponse(
        "Contact: <your-email>\\nExpires: 2025-01-01T00:00:00.000Z",
        headers={"Content-Type": "text/plain; charset=UTF-8"},
    )


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    # .well-known
    path("robots.txt", robots),
    path(".well-known/security.txt", security),
    path(".well-known/500", trigger_error),
"""

    urls = urls.replace("urlpatterns = [", urlpatterns)
    with open(dir / project_name / "urls.py", "w") as f:
        f.write(urls)


def django_set_staticfiles_storage(dir, project_name):
    settings = open(dir / project_name / "settings.py", "r").read().splitlines()

    for i, l in enumerate(settings):
        if l.startswith("STATIC_URL ="):
            l += '\nif not DEBUG:\n    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"'
            settings[i] = l

    with open(dir / project_name / "settings.py", "w") as f:
        f.write("\n".join(settings))


def django_add_middleware(dir, project_name):
    middleware = request("https://raw.githubusercontent.com/sesh/django-middleware/main/middleware.py").content.decode()
    with open(dir / project_name / "middleware.py", "w") as f:
        f.write(middleware)

    settings = open(dir / project_name / "settings.py", "r").read()
    settings = settings.replace(
        '"django.middleware.clickjacking.XFrameOptionsMiddleware",',
        f"""'django.middleware.clickjacking.XFrameOptionsMiddleware',
    '{project_name}.middleware.set_remote_addr',
    '{project_name}.middleware.csp',
    '{project_name}.middleware.permissions_policy',
    '{project_name}.middleware.xss_protect',
    '{project_name}.middleware.expect_ct',
    '{project_name}.middleware.cache',
    '{project_name}.middleware.corp_coop_coep',
    '{project_name}.middleware.dns_prefetch',""",
    )

    with open(dir / project_name / "settings.py", "w") as f:
        f.write(settings)


def django_add_sentry(dir, project_name):
    settings = open(dir / project_name / "settings.py", "r").read()
    settings += "\n\n"
    settings += "# Sentry\n"
    settings += "# https://sentry.io\n"
    settings += "# Enabled by setting SENTRY_DSN, install sentry_sdk if you plan on using Sentry\n\n"
    settings += 'SENTRY_DSN = os.environ.get("SENTRY_DSN", "")\n\n'
    settings += "if SENTRY_DSN and not DEBUG:\n"
    settings += "    import sentry_sdk\n"
    settings += "    from sentry_sdk.integrations.django import DjangoIntegration\n"
    settings += "    sentry_sdk.init(\n"
    settings += "        dsn=SENTRY_DSN,\n"
    settings += "        integrations=[\n"
    settings += "            DjangoIntegration(),\n"
    settings += "        ],\n"
    settings += "        # Set traces_sample_rate to 1.0 to capture 100%\n"
    settings += "        # of transactions for performance monitoring.\n"
    settings += "        # We recommend adjusting this value in production.\n"
    settings += "        traces_sample_rate=0.05,\n"
    settings += "        # If you wish to associate users to errors (assuming you are using\n"
    settings += "        # django.contrib.auth) you may enable sending PII data.\n"
    settings += "        send_default_pii=False\n"
    settings += "    )\n"

    with open(dir / project_name / "settings.py", "w") as f:
        f.write(settings)


def install_and_run_black(dir):
    run("pipenv install --dev black", shell=True, check=True, cwd=dir)
    run("pipenv run black .", shell=True, check=True, cwd=dir)


def install_and_run_isort(dir):
    run("pipenv install --dev isort", shell=True, check=True, cwd=dir)
    run("pipenv run isort .", shell=True, check=True, cwd=dir)


def add_pyproject(dir):
    with open(dir / "pyproject.toml", "w") as f:
        f.write(
            """[tool.ruff]
line-length = 120

[tool.black]
line-length = 120

[tool.isort]
profile = "black"
"""
        )


def add_readme(dir, project_name, domain):
    with open(dir / "README.md", "w") as f:
        f.write(
            f"""# {project_name}

## Usage

### Running the initial migrations

```bash
pipenv run python manage.py migrate
```

### Running the development server

```bash
pipenv run python manage.py runserver
```

### Running the tests

```bash
pipenv run python manage.py test
```

### Deploying to a VPS

Notes:

- Ansible must be installed on your local machine
- Target should be running Ubuntu 22.04

```bash
pipenv run python manage.py up {domain} --email=<your-email>
```

---

Generated with [sesh/djbs](https://github.com/sesh/djbs).
"""
        )


def add_gitignore(dir):
    gitignore = request("https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore").content.decode()
    with open(dir / ".gitignore", "w") as f:
        f.write(gitignore)


def main(project_name, app_name, domain, base_dir):
    p = Path(base_dir + project_name)
    p = create_project_directory(p)

    django_install(p)
    django_startproject(p, project_name)
    django_secret_key_in_env(p, project_name)
    django_set_allowed_hosts(p, project_name, domain)
    django_set_staticfiles_storage(p, project_name)
    django_add_default_logging(p, project_name)
    django_startapp(p, app_name)
    django_add_app_to_installed_apps(p, project_name, app_name)
    django_add_base_template(p, project_name, app_name)
    django_add_style_css(p, project_name, app_name)
    django_add_management_command(p, project_name, app_name)
    django_add_favicon(p, project_name, app_name)
    django_add_up(p, project_name)
    django_add_authuser(p, project_name)
    django_add_wellknown_urls(p, project_name)
    django_add_sentry(p, project_name)
    django_add_middleware(p, project_name)
    django_run_migrations(p, project_name)
    add_readme(p, project_name, domain)
    add_pyproject(p)
    add_gitignore(p)

    install_and_run_black(p)
    install_and_run_isort(p)


if __name__ == "__main__":
    project_name = input("Project name: ")
    domain_name = input("Domain name: ")

    app_name = input("App name [core]:")
    if not app_name:
        app_name = "core"

    base_dir = input("Base directory [../]: ")
    if not base_dir:
        base_dir = "../"

    if not base_dir.endswith("/"):
        cont = input("Base directory does not end with '/', continue (yN)? ")
        if cont != "y":
            sys.exit("Exiting..")

    main(project_name, app_name, domain_name, base_dir)
