import hashlib
import json
import logging
from logging import Logger
import hmac

from flask import Flask, request, abort
from requests import get, post

from api import GIT_FILE_REF

from utils import (post_comment_on_line, auth, host_api, host,
                   format_comment, flake8_scan_file, post_pr_review, secret)

app = Flask(__name__)
app.logger.setLevel(logging.INFO)


def handle_push(push_data: dict):
    repo_info = push_data['repository']
    results = flake8_scan_file(push_data['after'],
                               repo_info['owner']['login'],
                               repo_info['name'],
                               )
    for file_name, comments_per_line in results.items():
        for line_n, comments_data in comments_per_line.items():
            comment = ""
            for comment_data in comments_data:
                comment += f'\nLine:{comment_data[1]} -> ' \
                           f'{format_comment(*comment_data)}'
            app.logger.info('Writing comment on git commit (%s) %s:%i',
                            push_data['after'],
                            file_name,
                            line_n)
            post_comment_on_line(repo_info['owner']['login'],
                                 repo_info['name'],
                                 push_data['after'],
                                 line_n,
                                 file_name, comment)


def handle_pull_request(hook_data):
    owner = hook_data['repository']['owner']['login']
    repo = hook_data['repository']['name']
    pr_info = hook_data['pull_request']
    commit_sha = pr_info['head']['sha']

    app.logger.info("Checking %s commit against %s commit",
                    commit_sha,
                    pr_info['base']['sha'])

    results = flake8_scan_file(commit_sha,
                               owner,
                               repo,
                               parent_sha=pr_info['base']['sha'])

    message = "Dear developer, " \
              "please fix all referenced " \
              "PEP8 code style violations before merging PR."

    for filename, comments in results.items():
        file_ref = GIT_FILE_REF.format(host=host,
                                       owner=owner,
                                       repo=repo,
                                       sha=pr_info['head']['sha'],
                                       filepath=filename)
        line = f"## [{filename}]({file_ref}):"

        for comments_per_line in comments.values():
            for comment in comments_per_line:
                line += f'\n[Line {comment[1]}]' \
                        f'({file_ref}#L{comment[1]}):' \
                        f'{format_comment(*comment)}'
        message += "\n" + line

    post_pr_review(owner, repo, commit_sha, pr_info['number'],
                   message)


@app.route('/git_hook', methods=['POST'])
def git_hook():
    msg_hash = "sha1=" + hmac.new(secret,
                                  request.get_data(),
                                  hashlib.sha1).hexdigest().lower()
    if msg_hash != request.headers['X-Hub-Signature']:
        return abort(403)
    hook_data = request.get_json()
    hook_type = request.headers['X-GitHub-Event']
    app.logger.critical(f"Request from GIT: {hook_type}")
    if hook_type == 'push':
        # Push handler
        handle_push(hook_data)
    elif hook_type == 'pull_request':
        pr_action = hook_data['action']
        # Pull request handler
        if pr_action in ['opened', 'synchronize']:
            # React only to open or new commits
            handle_pull_request(hook_data)

    return 'ok'


@app.route('/health', methods=['GET'])
def health():
    return 'ok'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='9090')
