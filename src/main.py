import os
import sys
import logging # Import logging
from logging.handlers import RotatingFileHandler # For rotating file logs

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, request as flask_request # Added request for logging
from src.models.user import db
from src.routes.auth import auth_bp
from src.routes.user import user_bp
from src.routes.payment import payment_bp
from flask_cors import CORS

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
CORS(app)

# Configure Logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs') # Create logs dir at project root
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'app.log')

file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO) # Set to INFO, DEBUG, ERROR as needed
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

# Log each request
@app.before_request
def log_request_info():
    app.logger.info(f"Request: {flask_request.method} {flask_request.url} Headers: {flask_request.headers} Body: {flask_request.get_data(as_text=True)}")

@app.after_request
def log_response_info(response):
    app.logger.info(f"Response: {response.status} Headers: {response.headers} Body: {response.get_data(as_text=True)}")
    return response

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(payment_bp, url_prefix='/api')

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:{os.getenv('DB_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'mydb')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()
    app.logger.info("Database tables created or already exist.")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            app.logger.error("Static folder not configured")
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            app.logger.error("index.html not found in static folder")
            return "index.html not found", 404


if __name__ == '__main__':
    app.logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)
