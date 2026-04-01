def test_celery_app_configured():
    from pipeline.celery_app import celery_app
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert "json" in celery_app.conf.accept_content
    assert celery_app.conf.timezone == "UTC"


def test_celery_broker_uses_redis():
    from pipeline.celery_app import celery_app
    import config
    assert celery_app.conf.broker_url == config.REDIS_URL


def test_celery_app_name():
    from pipeline.celery_app import celery_app
    assert celery_app.main == "lavenderhealth"
