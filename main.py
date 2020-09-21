from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
app.notifications = {}


@app.route('/git_hook', methods=['POST'])
def git_hook():
    pass


@app.route('/health', methods=['GET'])
def health():
    return 'ok'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='6001')
