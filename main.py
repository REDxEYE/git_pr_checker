import os

import pycodestyle

from io import StringIO
from typing import List

from unidiff import PatchSet, PatchedFile, Hunk
from unidiff.patch import Line

from flask import Flask, request
from requests import get, post

app = Flask(__name__)
app.notifications = {}

GIT_COMMENT_URL = 'https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}/comments'
header = {"Authorization": f'Bearer {os.environ.get("GITAPIKEY", "ERROR")}'}


def _changed_in_diff(diff: PatchedFile, line_n: int):
    for hunk in diff:
        hunk: Hunk
        for line_change in hunk:
            line_change: Line
            if (line_change.is_added and
                line_change.target_line_no == line_n) \
                    or line_change.is_context:
                return True
    return False


def _get_file_by_name(mod_files: List[PatchedFile], filename: str):
    for mod in mod_files:
        if mod.path == filename:
            return mod
    return None


def _comment_on_line(user, repo, commit_sha, line_n, filename, message):
    res = post(
        GIT_COMMENT_URL.format(owner=user, repo=repo, commit_sha=commit_sha),
        headers=header, data={
            "body": message,
            "path": filename,
            "position": line_n
        })
    assert res.status_code == 201


@app.route('/git_hook', methods=['POST'])
def git_hook():
    hook_data = request.get_json()
    if 'pusher' in hook_data:
        # Push handler
        repo_info = hook_data['repository']
        diff_url = repo_info['compare_url'].format(base=hook_data['before'],
                                                   head=hook_data['after'])
        diff_info = get(diff_url).json()
        diff_content = get(diff_info['diff_url']).content.decode('utf8')
        patch_set = PatchSet(diff_content)
        for file in diff_info['files']:
            raw_content = get(file['raw_url']).content.decode('utf8')
            checker = pycodestyle.Checker(
                filename=file['filename'],
                lines=StringIO(raw_content).readlines()
            )
            warning_count = checker.check_all()
            comments_per_line = {}
            for line_n, offset, code, text, doc in checker.report._deferred_print:
                if _changed_in_diff(_get_file_by_name(patch_set.modified_files,
                                                      file['filename']),
                                    line_n):
                    print(f'{checker.filename}:{line_n}'
                          f' {code} : {text}')
                    comments = comments_per_line.get(line_n, [])
                    comments.append(f'{code} : {text}')
                    comments_per_line[line_n] = comments
            for line_n, comments in comments_per_line.items():
                comment = '\n'.join(comments)
                _comment_on_line(repo_info['owner']['name'],
                                 repo_info['name'],
                                 hook_data['after'],
                                 line_n,
                                 file['filename'], comment)

    return 'ok'


@app.route('/health', methods=['GET'])
def health():
    return 'ok'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='8080')
