from datetime import datetime
from pprint import pprint

from flask import Flask, request, jsonify

from requests import get

app = Flask(__name__)
app.notifications = {}

def TeA_asd_(a,b,c,d,e):
    u = "Very looooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooong string to trigger pep8"
    return None

@app.route('/git_hook', methods=['POST'])
def git_hook():
    hook_data = request.get_json()
    if 'pusher' in hook_data:
        #Push handler
        repo_info = hook_data['repository']
        diff_url = repo_info['compare_url'].format(base=hook_data['before'],
                                                   head=hook_data['after'])
        diff_info = get(diff_url).json()
        pprint(diff_info)
    # pprint(hook_data)
    return 'ok'


@app.route('/health', methods=['GET'])
def health():
    return 'ok'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='8080')
