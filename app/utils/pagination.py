from flask import request, current_app


def paginate_query(query):
    """Paginate a SQLAlchemy query using ?page= and ?per_page= query params."""
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get("per_page", current_app.config["PAGINATION_DEFAULT_PAGE_SIZE"]))
    except (TypeError, ValueError):
        per_page = current_app.config["PAGINATION_DEFAULT_PAGE_SIZE"]

    page = max(page, 1)
    per_page = max(1, min(per_page, current_app.config["PAGINATION_MAX_PAGE_SIZE"]))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return pagination, {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    }
