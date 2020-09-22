import os
from typing import List

from requests.api import post
from requests.auth import HTTPBasicAuth
from unidiff import PatchedFile, Hunk
from unidiff.patch import Line

from api import GIT_COMMENT_URL

host = os.environ.get("GITHOST_API", "api.github.com")

auth = HTTPBasicAuth(os.environ.get("GITUSERNAME", "ERROR"),
                     os.environ.get("GITAPIKEY", "ERROR"))


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
        GIT_COMMENT_URL.format(host=host, owner=user, repo=repo,
                               commit_sha=commit_sha),
        auth=auth, json={
            "body": message,
            "path": filename,
            "position": line_n,
        })

    assert res.status_code == 201, f'Got non 201 status, ' \
                                   f'error message: {res.content}'
