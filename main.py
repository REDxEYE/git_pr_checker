import json

from flake8.api import legacy as flake8

from unidiff import PatchSet

from flask import Flask, request
from requests import get, post

from api import GIT_COMMIT_URL, GIT_COMPARE_URL, GIT_PULL_REVIEW_URL
from utils import (_changed_in_diff,
                   _get_file_by_name,
                   _comment_on_line,
                   auth,
                   host,
                   )

app = Flask(__name__)


def handle_push(push_data: dict):
    repo_info = push_data['repository']
    results = check_commit(push_data['after'],
                           repo_info['owner']['name'],
                           repo_info['name'],
                           )
    for file_name, comments_per_line in results.items():
        for line_n, comments in comments_per_line.items():
            comment = '\n'.join(comments)
            app.logger.info(
                'Writing comment on git commit (%s) %s:%i',
                push_data['after'],
                file_name,
                line_n)
            _comment_on_line(repo_info['owner']['name'],
                             repo_info['name'],
                             push_data['after'],
                             line_n,
                             file_name, comment)


def check_commit(commit_sha, owner, repo, parent_sha=None):
    if parent_sha is None:
        commit_info = get(GIT_COMMIT_URL.format(sha=commit_sha,
                                                owner=owner,
                                                repo=repo,
                                                host=host)).json()
        parent_sha = commit_info['parents'][0]['sha']
    diff_url = GIT_COMPARE_URL.format(base=parent_sha,
                                      head=commit_sha,
                                      owner=owner,
                                      repo=repo,
                                      host=host)
    diff_info = get(diff_url, auth=auth).json()
    diff_content = get(diff_url, auth=auth, headers={
        "Accept": "application/vnd.github.v3.diff"}).content.decode('utf8')
    patch_set = PatchSet(diff_content)
    comments_per_file = {}
    for file in diff_info['files']:
        content = get(file['contents_url'], auth=auth).json()
        raw_content = get(content['download_url']).content
        with open("flake8_tmp_file.py", 'wb') as test_file:
            test_file.write(raw_content)
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
        comments_per_file[file['filename']] = comments_per_line
    return comments_per_file


def handle_pull_request(hook_data):
    owner = hook_data['repository']['owner']['name']
    repo = hook_data['repository']['name']
    pr_info = hook_data['pull_request']
    app.logger.info("Checking %s commit against %s commit",
                    pr_info['head']['sha'],
                    pr_info['base']['sha'])
    results = check_commit(pr_info['head']['sha'],
                           owner,
                           repo,
                           parent_sha=pr_info['base']['sha'])
    message = "PEP8 code style violations! Requesting changes!"
    for filename, comments in results.items():
        line = f"{filename}:"
        for comment in comments:
            line += f'\n\t{comment}'
        message += "\n" + message
    review = {
        "commit_id": pr_info['head']['sha'],
        "body": message,
        "event": "REQUEST_CHANGES",
        "comments": [
        ]
    }
    post(GIT_PULL_REVIEW_URL.format(host=host,
                                    owner=owner,
                                    repo=repo,
                                    pull_numper=pr_info['number'],
                                    json=review), auth=auth)


@app.route('/git_hook', methods=['POST'])
def git_hook():
    hook_data = request.get_json()
    if 'pusher' in hook_data:
        # Push handler
        handle_push(hook_data)
    elif 'pull_request' in hook_data:
        # Pull request handler
        handle_pull_request(hook_data)

    return 'ok'


@app.route('/health', methods=['GET'])
def health():
    return 'ok'


if __name__ == '__main__':
    # with open('tmp.json', 'r') as f:
    #     handle_push(json.load(f))
    app.run(host='0.0.0.0', port='9090')
