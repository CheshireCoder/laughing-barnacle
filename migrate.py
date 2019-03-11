from tinydb import *

db_src = TinyDB('./db.json')
db_dst = TinyDB("./Aatrox.db.json")

tbl_user = 'users'
tbl_video = 'videos'
tbl_remote = 'remotes'
tbl_accounts = 'accounts'

d_user = dict(
    user_name=None,         # string, twitch user name.
    user_id=None,           # string, twitch user id.
    remote=None             # remote destination name.
)
d_video = dict(
    lfbar_downloaded=None,  # boolean, if download is done.
    lfbar_uploaded=None,    # boolean, if upload is done.
    lfbar_filesize=None,    # number, size of downloaded file.
    lfbar_lcopy_path=None   # string, absolute path of downloaded file.
)
d_remote = dict(
    name=None,              # string, name of remote, can be different from rclone's.
    account=None,           # string, in case of uploading is limited via account.
    rclone_config=None      # string, name of remote, defined in rclone config.
)
d_account = dict(
    name=None,              # string, name of account
    quota=None,             # number, upload quota
    reset_cycle=None,       # string - timedelta, upload quota time window size.
    next_available_at=None  # string - datetime, next available time with Zulu ending.
)


def alt_if_none(src, s, d, alt=False):
    t = src.get(s, None)
    if None is t:
        src[d] = alt
    else:
        src.pop(s)
        src[d] = t
    return src


t = dict()

for tbl_name in [tbl_user, tbl_video, tbl_remote, tbl_accounts]:
    t[tbl_name] = db_dst.table(tbl_name)

rows = db_src.all()
for row in rows:
    row = alt_if_none(row, 'dst_name', 'remote', None)
    t[tbl_user].insert(row)
    t[tbl_remote].insert(dict(
        name=row['remote'],
        account=None,
        rclone_config=row['remote']
    ))
tbls = db_src.tables()
for tbl in tbls:
    if '_default' != tbl:
        rows = db_src.table(tbl).all()
        for row in rows:
            row = alt_if_none(row, 'downloaded', 'lfbar_downloaded')
            row = alt_if_none(row, 'uploaded', 'lfbar_uploaded')
            row = alt_if_none(row, 'download_path', 'lfbar_lcopy_path')
            row['lfbar_filesize'] = 1
            t[tbl_video].insert(row)
