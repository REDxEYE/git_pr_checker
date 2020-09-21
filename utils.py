import os
from typing import List

from requests.api import post
from unidiff import PatchedFile, Hunk
from unidiff.patch import Line

GIT_COMMENT_URL = 'https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}/comments'
header = {"Authorization": f'Bearer {os.environ.get("GITAPIKEY", "ERROR")}'}


def _changed_in_diff(diff: PatchedFile, line_n: int):
    """Returns True if line were changed in passed diff parameter"""
    for hunk in diff:
        hunk: Hunk
        for line_change in hunk:
            line_change: Line
            if line_change.is_added and line_change.target_line_no == line_n:
                return True
    return False


def _get_file_by_name(mod_files: List[PatchedFile], filename: str):
    """Finds PatchedFile object in list of PathedFile`s by name"""
    for mod in mod_files:
        if mod.path == filename:
            return mod
    return None


def _comment_on_line(user, repo, commit_sha, line_n, filename, message):
    """Posts commit comment on specified commit and line"""
    res = post(
        GIT_COMMENT_URL.format(owner=user, repo=repo, commit_sha=commit_sha),
        headers=header, json={
            "body": message,
            "path": filename,
            "position": line_n,
        })

    # app.logger.info(str(res.json()))
    assert res.status_code == 201
