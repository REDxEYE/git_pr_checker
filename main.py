from datetime import datetime
from pprint import pprint

from flask import Flask, request, jsonify

app = Flask(__name__)
app.notifications = {}


@app.route('/git_hook', methods=['POST'])
def git_hook():
    hook_data = request.get_json()
    pprint(hook_data)
    return 'ok'


@app.route('/health', methods=['GET'])
def health():
    return 'ok'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='8080')
