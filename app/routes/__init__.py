from app.routes.auth import auth_bp
from app.routes.customers import customers_bp
from app.routes.products import products_bp
from app.routes.invoices import invoices_bp
from app.routes.dashboard import dashboard_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(dashboard_bp)
