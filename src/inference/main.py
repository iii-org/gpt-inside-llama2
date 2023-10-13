from environment import app
from api import text_api


app.add_url_rule('/__api/qa', view_func=text_api, methods=['POST'])

if __name__ == '__main__':
    app.run()
