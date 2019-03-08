#!/usr/bin/python3
import datetime
import os
import sys
from subprocess import Popen, PIPE

import requests
from tinydb import *

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
        if None is table.get(Query().id == row['id']):
            row['downloaded'] = False
            table.insert(row)


def update_video_list(user_id):
    _save_video_list(user_id, _get_video_list(user_id)['data'])


def _get_video_file_name(user_id, video_id):
    tbl = db.table(user_id)
    row = tbl.get(Query().id == video_id)
    file_name = "{time} {title} {duration}.ts"
    return file_name.format(**row)


def _get_user_id(user_name):
    res = db.get(Query().user_name == user_name)
    if None is res:
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
    db.update({'dst_name': dst_name}, Query().user_id == user_id)


def download_a_video(user_id, video_id, num_thread=10):
    tbl = db.table(user_id)

    if 0 == len(tbl.search(Query().id == video_id)):
        return -10000
    elif tbl.search((Query().id == video_id) & Query().uploaded.exists()):
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
    tbl = db.table(user_id)
    vid_info = tbl.get(Query().id == video_id)

    if None is vid_info:
        return -10000
    elif vid_info['uploaded'] and not os.path.exists(vid_info['download_path']):
            return -20000

    local_path = vid_info['download_path']
    dst_name = db.get(Query().user_id == user_id)['dst_name']
    arr_cmd = ['rclone', 'copy', local_path, dst_name+':'+dst_path]
    pr = Popen(arr_cmd, stdout=PIPE)
    (output, err) = pr.communicate()
    exit_code = pr.wait()
    if 0 != exit_code:
        print("Could not upload video {id}.".format(**vid_info))
    else:
        os.unlink(local_path)
        print("Successfully uploaded video {id}".format(**vid_info))
        tbl.update({'uploaded': True}, Query().video_id == video_id)

    return exit_code


def check_done(user_id, video_id):
    tbl = db.table(user_id)
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


def _datetime_from_vid_info(vid_info):
    return datetime.datetime.strptime(vid_info['published_at'], "%Y-%m-%dT%H:%M:%SZ")


def do_by(user_name, num=1):
    user_id = _get_user_id(user_name)
    arr = sorted(db.table(user_id).search(where('downloaded') == False), key=_datetime_from_vid_info)
    for i in range(int(num)):
        video_id = arr[i]['id']
        ret = -1
        while ret not in [0, -10000, -20000]:
            ret = download_a_video(user_id, video_id)
        ret = -1
        while ret not in [0, -10000, -20000]:
            ret = upload_a_video(user_id, video_id)


def list_non_downloaded(user_name):
    user_id = _get_user_id(user_name)
    update_video_list(user_id)
    tbl = db.table(user_id)
    res = tbl.search(where('downloaded') == False)
    return res


def list_non_uploaded(user_name):
    user_id = _get_user_id(user_name)
    tbl = db.table(user_id)
    res = tbl.search((Query().downloaded == True) & (Query().uploaded == False))
    return res


def list_done(user_name, per_page, num_page):
    user_id = _get_user_id(user_name)
    tbl = db.table(user_id)
    offset = num_page * per_page
    res = tbl.search(Query().uploaded == True)
    if len(res) <= offset + num_page:
        ret = res[offset:len(res)-1]
    else:
        ret = res[offset:offset + num_page]
    return ret


def print_list(arr_dat):
    for dat in arr_dat:
        print("ID: {id} Date: {published_at} Title: {title} Duration: {duration}".format(**dat))


def show_instruction():
    print("Usage: run.py [options] [twitch user name] [argument1...]"       '\n'
          "  options:"                                                      '\n'
          "    no-down\tprints list of non-downloaded videos"               '\n'
          "    no-up\tprints list of non-uploaded videos"                   '\n'
          "    check\tcheck video id done "                                 '\n'
          "    set\tsets destination name (to call rclone)"                 '\n'
          "    down\tdownload a video"                                      '\n'
          "    up\tupload downloaded video"                                 '\n'
          "    all\tdownload and upload all available video one by one")


def main():
    if len(sys.argv) < 3:
        show_instruction()
        return
    else:
        action = sys.argv[1].lower()
        user_name = sys.argv[2]
        user_id = _get_user_id(sys.argv[2])
    if 'no-down' == action:
        list_non_downloaded(user_name)
    elif 'no-up' == action:
        list_non_uploaded(user_name)
    elif 'check' == action:
        check_done(user_id, sys.argv[3])
    elif 'set' == action:
        _set_dst_name(user_name, sys.argv[3])
    elif 'down' == action:
        download_a_video(user_id, sys.argv[3])
    elif 'up' == action:
        upload_a_video(user_id, sys.argv[3])
    elif 'all' == action:
        down_and_up_all(user_name)
    elif 'do' == action:
        if len(sys.argv) < 4:
            do_by(user_name)
        else:
            do_by(user_name, sys.argv[3])


if __name__ == '__main__':
    main()
