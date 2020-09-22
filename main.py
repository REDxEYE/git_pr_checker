import json
import os

# import pycodestyle
from flake8.api import legacy as flake8
from flake8.api.legacy import Report

from unidiff import PatchSet

from flask import Flask, request
from requests import get

from utils import _changed_in_diff, _get_file_by_name, _comment_on_line, auth

app = Flask(__name__)


def handle_push(push_data: dict):
    repo_info = push_data['repository']
    diff_url = repo_info['compare_url'].format(base=push_data['before'],
                                               head=push_data['after'])
    diff_info = get(diff_url, auth=auth).json()
    diff_content = get(diff_url, auth=auth, headers={
        "Accept": "application/vnd.github.v3.diff"}).content.decode('utf8')
    patch_set = PatchSet(diff_content)
    for file in diff_info['files']:
        content = get(file['contents_url'], auth=auth).json()
        raw_content = get(content['download_url']).content
        with open("flake8_tmp_file.py", 'wb') as f:
            f.write(raw_content)
        style_guide = flake8.get_style_guide(ignore=['E24', 'W503'])
        style_guide.input_file('./flake8_tmp_file.py', )
        results = style_guide._application.file_checker_manager.checkers[
            0].results
        comments_per_line = {}
        for code, line_n, offset, text, src in results:
            if _changed_in_diff(_get_file_by_name(patch_set,
                                                  file['filename']),
                                line_n):
                comments = comments_per_line.get(line_n, [])
                comments.append(f'Line:{line_n}:{offset} -> {code} {text}')
                comments_per_line[line_n] = comments
        for line_n, comments in comments_per_line.items():
            comment = '\n'.join(comments)
            app.logger.info(
                'Writing comment on git commit (%s) %s:%i',
                push_data['after'],
                file['filename'],
                line_n)
            _comment_on_line(repo_info['owner']['name'],
                             repo_info['name'],
                             push_data['after'],
                             line_n,
                             file['filename'], comment)


@app.route('/git_hook', methods=['POST'])
def git_hook():
    hook_data = request.get_json()
    if 'pusher' in hook_data:
        # Push handler
        handle_push(hook_data)

    return 'ok'


@app.route('/health', methods=['GET'])
def health():
    return 'ok'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='9090')
