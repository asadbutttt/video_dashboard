from app import create_app, make_celery
from config import Config
import os

# Create Flask app
app = create_app()

# Create Celery instance
celery = make_celery(app)

if __name__ == '__main__':
    # Create INPUT and OUTPUT directories if they don't exist
    Config.init_app(app)
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
