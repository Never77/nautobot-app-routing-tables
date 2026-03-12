try:
    from invoke import task
except Exception:
    task = None  # type: ignore

if task:
    @task
    def docs(c):
        c.run("mkdocs build")
        c.run("python -m nautobot_routing_tables.tools.copy_docs_to_static")

@task
def validate_app_config(context):
    """Validate the app config based on the app config schema."""
    start(context, service="nautobot")
    nbshell(
        context,
        plain=True,
        file="development/app_config_schema.py",
        env={"APP_CONFIG_SCHEMA_COMMAND": "validate"},
    )