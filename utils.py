import os
from typing import List

from requests.api import post, get
from requests.auth import HTTPBasicAuth

from unidiff import PatchedFile, Hunk, PatchSet
from unidiff.patch import Line

from flake8.api import legacy as flake8

from api import GIT_COMMENT_URL, GIT_COMMIT_URL, GIT_COMPARE_URL, \
    GIT_PULL_REVIEW_URL

host_api = os.environ.get("GITHOST_API", "api.github.com")
host = os.environ.get("GITHOST", "github.com")

auth = HTTPBasicAuth(os.environ.get("GITUSERNAME", "ERROR"),
                     os.environ.get("GITAPIKEY", "ERROR"))


def format_comment(filename, line_n, offset, code, text):
    """Returns formatted comment.
     Just a dummy function to pass tuple of arguments by *args"""
    return f'{code}: {text}'


def get_commit_parent(commit_sha: str, owner: str, repo: str):
    """Returns parent commit sha"""
    link = GIT_COMMIT_URL.format(sha=commit_sha,
                                 owner=owner,
                                 repo=repo,
                                 host=host_api)
    commit_info_req = get(link, auth=auth)
    commit_info = commit_info_req.json()
    return commit_info['parents'][0]['sha']


def flake8_scan_file(commit_sha, owner, repo, parent_sha=None):
    """Runs flake8 scan on all changed files and returns array of warnings"""
    if parent_sha is None:
        parent_sha = get_commit_parent(commit_sha, owner, repo)
    diff_url = GIT_COMPARE_URL.format(base=parent_sha,
                                      head=commit_sha,
                                      owner=owner,
                                      repo=repo,
                                      host=host_api)
    diff_info = get(diff_url, auth=auth).json()
    diff_content = get(diff_url,
                       auth=auth,
                       headers={"Accept": "application/vnd.github.v3.diff"}
                       ).content.decode('utf8')
    patch_set = PatchSet(diff_content)
    comments_per_file = {}
    for file in diff_info['files']:
        content = get(file['contents_url'], auth=auth).json()
        file_content = get(content['download_url']).content
        with open("flake8_tmp_file.py", 'wb') as test_file:
            test_file.write(file_content)
        style_guide = flake8.get_style_guide(ignore=['E24', 'W503'])
        style_guide.input_file('./flake8_tmp_file.py', )
        results = style_guide._application.file_checker_manager.checkers[
            0].results
        comments_per_line = {}
        for code, line_n, offset, text, src in results:
            if changed_in_diff(get_file_by_name(patch_set,
                                                file['filename']), line_n):
                comments = comments_per_line.get(line_n, [])
                comments.append((file['filename'], line_n, offset, code, text))
                comments_per_line[line_n] = comments
        comments_per_file[file['filename']] = comments_per_line
    return comments_per_file


def changed_in_diff(diff: PatchedFile, line_n: int):
    """Returns True if line were changed in passed diff parameter"""
    for hunk in diff:
        hunk: Hunk
        for line_change in hunk:
            line_change: Line
            if line_change.is_added and line_change.target_line_no == line_n:
                return True
    return False


def get_file_by_name(mod_files: List[PatchedFile], filename: str):
    """Finds PatchedFile object in list of PathedFile`s by name"""
    for mod in mod_files:
        if mod.path == filename:
            return mod
    return None


def post_comment_on_line(owner, repo, commit_sha, line_n, filename, message):
    """Posts commit comment on specified commit and line"""
    res = post(
        GIT_COMMENT_URL.format(host=host_api, owner=owner, repo=repo,
                               commit_sha=commit_sha),
        auth=auth, json={
            'body': message,
            'path': filename,
            'position': line_n,
        })

    assert res.status_code == 201, f'Got non 201 status, ' \
                                   f'error message: {res.content}'


def post_pr_review(owner, repo,
                   commit_sha, pull_number,
                   message, event='COMMENT'):
    """Posts review comment on specified pull request and change it status"""
    review = {
        'commit_id': commit_sha,
        'body': message,
        'event': event,
    }

    res = post(GIT_PULL_REVIEW_URL.format(host=host_api,
                                          owner=owner,
                                          repo=repo,
                                          pull_number=pull_number),
               json=review, auth=auth)
    assert res.status_code == 200, f'Got non 201 status, ' \
                                   f'error message: {res.content}'
