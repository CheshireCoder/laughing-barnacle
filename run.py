#!/usr/bin/python3
import os, sys
import requests
from tinydb import *
from subprocess import Popen, PIPE

db = TinyDB('./db.json')
tbl_user = 'user_name_to_id'
twitch_CID = {'Client-ID': '8dp5au7iqhcs3qhmfrjjo9i22515zp'}


def _get_video_list(user_id, size=100):
    ep = "https://api.twitch.tv/helix/videos"
    dic_param = {'user_id': user_id,
                 'first': size}
    dic_header = twitch_CID
    res = requests.get(ep, params=dic_param, headers=dic_header)
    return res.json()


def _save_video_list(user_id, arr_list):
    table = db.table(str(user_id))
    for row in arr_list:
        if 0 == len(table.get(Query().id == row['id'])):
            row['downloaded'] = False
            table.insert(row)


def update_video_list(user_id):
    _save_video_list(user_id, _get_video_list(user_id)['data'])


def _get_video_file_name(user_id, video_id):
    tbl = db.table(str(user_id))
    row = tbl.get(Query().id == video_id)
    file_name = "{time} {title}.ts"
    return file_name.format(time=row['published_at'], title=row['title'])


def _get_user_id(user_name):
    res = db.get(Query().user_name == user_name)
    if 0 == len(res):
        ep = 'https://api.twitch.tv/helix/users'
        dic_param = {'login': user_name}
        dic_header = twitch_CID
        res = requests.get(ep, params=dic_param, headers=dic_header)
        user_id = res.json()['data'][0]['id']
        db.insert(dict(user_name=user_name, user_id=user_id))
    else:
        user_id = res['user_id']
    return user_id


def _set_dst_name(user_name, dst_name):
    user_id = _get_user_id(user_name)
    db.insert({'user_name': user_name, 'user_id': user_id, 'dst_name': dst_name})


def download_a_video(user_id, video_id, num_thread=10):
    tbl = db.table(str(user_id))

    if 0 == len(tbl.search(Query().id == video_id)):
        return -10000
    else:
        if tbl.search((Query().id == video_id) & Query().uploaded.exists()):
            return -20000

    cmd = 'streamlink --hls-segment-threads {num_th} {url} best -o {dst}'
    local_path = user_id + '_' + video_id
    pr = Popen(cmd.format(num_th=num_thread, url='www.twitch.tv/videos/'+video_id, dst=local_path).split(" "),
               stdout=PIPE)
    (output, err) = pr.communicate()
    exit_code = pr.wait()
    if 0 != exit_code:
        print("Download Failed. exit code: {exit_code}".format(exit_code=exit_code))
        os.unlink(local_path)
    else:
        local_path_finished = _get_video_file_name(user_id, video_id)
        os.rename(local_path, local_path_finished)
        local_path = os.path.abspath(local_path_finished)
        tbl.update(dict(download_path=local_path, downloaded=True, uploaded=False), Query().id == video_id)

    return exit_code


def upload_a_video(user_id, video_id, dst_path=''):
    exit_code = -1
    tbl = db.table(str(user_id))

    if 0 == len(tbl.search(Query().id == video_id)):
        return -10000
    else:
        if tbl.get(Query().video_id == video_id)['uploaded']:
            return -20000

    local_path = tbl.get(Query().id == video_id)['local_path_finished']
    dst_name = db.get(Query().user_id == user_id)['dst_name']
    arr_cmd = 'rclone copy {src} {dst_name}:{dst_path}'\
        .format(src=local_path, dst_name=dst_name, dst_path=dst_path)\
        .split(' ')
    while 0 != exit_code:
        pr = Popen(arr_cmd, stdout=PIPE)
        (output, err) = pr.communicate()
        exit_code = pr.wait()
        if 0 != exit_code:
            print(err)
        else:
            os.unlink(local_path)
            tbl.update({'uploaded': True}, Query().video_id == video_id)

    return exit_code


def list_non_downloaded(user_name):
    user_id = _get_user_id(user_name)
    update_video_list(user_id)

    tbl = db.table(user_id)
    res = tbl.search(where('downloaded') == False)
    for row in res:
        print("ID: {id} Date: {published_at} Title: {title}".format(**row))
    return res


def list_non_uploaded(user_name):
    user_id = _get_user_id(user_name)
    tbl = db.table(user_id)
    res = tbl.search((where('downloaded') == True) & (where('uploaded') == False))
    for row in res:
        print("ID: {id} Date: {published_at} Title: {title}".format(**row))
    return res


def check_done(user_id, video_id):
    tbl = db.table(str(user_id))
    res = tbl.update(dict(downloaded=True, uploaded=True), Query().id == video_id)
    if 0 == len(res):
        print("Couldn't find id {vid}".format(vid=video_id))
    else:
        print("Checked id {vid}".format(vid=video_id))


def down_and_up_all(user_name):
    arr = list_non_uploaded(user_name)
    for item in arr:
        upload_a_video(_get_user_id(user_name), item['id'])
    arr = list_non_downloaded(user_name)
    for item in arr:
        if 0 == download_a_video(_get_user_id(user_name), item['id']):
            upload_a_video(_get_user_id(user_name), item['id'])


def show_instruction():
    print("Usage: run.py [options] [twitch user name] [argument1...]"
          "  options:"
          "    no-down\tprints list of non-downloaded videos"
          "    no-up\tprints list of non-uploaded videos"
          "    check\tcheck video id done "
          "    set\tsets destination name (to call rclone)"
          "    down\tdownload a video"
          "    up\tupload downloaded video"
          "    all\tdownload and upload all available video one by one")


def main():
    if len(sys.argv) < 3:
        show_instruction()
        return
    action = sys.argv[1].lower()
    if 'no-down' == action:
        list_non_downloaded(sys.argv[2])
    if 'no-up' == action:
        list_non_uploaded(sys.argv[2])
    if 'check' == action:
        check_done(_get_user_id(sys.argv[2]), sys.argv[3])
    if 'set' == action:
        _set_dst_name(sys.argv[2], sys.argv[3])
    if 'down' == action:
        download_a_video(_get_user_id(sys.argv[2]), sys.argv[3])
    if 'up' == action:
        upload_a_video(_get_user_id(sys.argv[2]), sys.argv[3])
    if 'all' == action:
        down_and_up_all(sys.argv[2])


if __name__ == '__main__':
    main()
