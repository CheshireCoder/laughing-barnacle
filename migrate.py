from tinydb import *

db_src = TinyDB('./db.json')
db_dst = TinyDB("./Aatrox.db.json")

tbl_user = 'users'
tbl_video = 'videos'
tbl_remote = 'remotes'

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
    reset_cycle=None,       # 
    next_available_at=None
)

