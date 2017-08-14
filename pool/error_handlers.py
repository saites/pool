from flask import render_template
import werkzeug.exceptions
from pool import app


@app.errorhandler(werkzeug.exceptions.NotFound)
def page_not_found(e):
    return render_template('error404.html')


@app.errorhandler(werkzeug.exceptions.InternalServerError)
def server_error(e):
    print(e)
    return render_template('error500.html')
