from app import create_app, make_celery

# Create Flask app and Celery instance
app = create_app()
celery = make_celery(app)

if __name__ == '__main__':
    # Start Celery worker
    celery.start()
