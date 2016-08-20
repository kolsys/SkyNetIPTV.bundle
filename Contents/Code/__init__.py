# -*- coding: utf-8 -*-

# Copyright (c) 2016, KOL
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from urlparse import urlparse
from updater import Updater

PREFIX = '/video/skynetiptv'

ART = 'art-default.jpg'
ICON = 'icon-default.png'
TITLE = 'SkyNet IPTV'

SKYNET_PLAYLIST = 'http://m3u.sknt.ru/cat/'
UDPXY_RE = Regex('^.+:[0-9]{1,5}$')
GROUP_RE = Regex('group-title="([^"]+)"')


def Start():
    HTTP.CacheTime = CACHE_1HOUR

def ValidatePrefs():
    if (ValidateProxy()):
        return MessageContainer(
            header=u'%s' % L('Success'),
            message=u'%s' % L('Preferences was changed')
        )
    else:
        return MessageContainer(
            header=u'%s' % L('Error'),
            message=u'%s' % L('Bad proxy address')
        )


def ValidateProxy():
    return not Prefs['proxy'] or UDPXY_RE.match(Prefs['proxy'])


@handler(PREFIX, TITLE, thumb=ICON)
def MainMenu():

    oc = ObjectContainer(title2=TITLE, no_cache=True)

    Updater(PREFIX+'/update', oc)

    groups = GetGroups()

    if not groups:
        return NoContents()

    oc.add(InputDirectoryObject(
        key=Callback(
            Search
        ),
        title=u'Поиск', prompt=u'Поиск канала'
    ))

    oc.add(DirectoryObject(
        key=Callback(
            Search,
            query=' HD'
        ),
        title=u'Каналы HD'
    ))
    oc.add(DirectoryObject(
        key=Callback(
            Search,
            query=' 3D'
        ),
        title=u'Каналы 3D'
    ))

    for group in groups:
        oc.add(DirectoryObject(
            key=Callback(
                Group,
                group=group
            ),
            title=u'%s' % group
        ))

    return oc


@route(PREFIX + '/group')
def Group(group):
    channels = GetChannels()

    if not channels:
        return NoContents()

    oc = ObjectContainer(
        title2=u'%s' % group,
        replace_parent=False,
    )

    group = group.decode('utf-8')

    for uri, meta in channels.items():
        if meta['group'].decode('utf-8') == group:
            Log.Debug(meta)
            try:
                vco = GetVideoObject(uri, meta['title'])
                oc.add(vco)
            except Exception as e:
                try:
                    Log.Warn('Can\'t add video to list: %s', e.status)
                except:
                    continue
    if not len(oc):
        return NoContents()

    return oc


@route(PREFIX + '/play')
def VideoPlay(uri, title):
    return ObjectContainer(
        objects=[GetVideoObject(uri, title)],
        content=ContainerContent.GenericVideos
    )


def GetVideoObject(uri, title):
    return VideoClipObject(
        key=Callback(
            VideoPlay,
            uri=uri,
            title=title
        ),
        rating_key=uri,
        title=u'%s' % title,
        source_title=TITLE,
        items=[
            MediaObject(
                parts=[PartObject(key=GetPlayUri(uri))],
                container=Container.MP4,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                optimized_for_streaming=True
            )
        ]
    )


def GetPlayUri(uri):

    if not Prefs['proxy']:
        return uri

    parsed = urlparse(uri)

    return 'http://%s/%s/%s' % (
        Prefs['proxy'],
        parsed.scheme,
        parsed.netloc[1:] if parsed.netloc.startswith('@') else parsed.netloc
    )


def GetGroups():
    channels = GetChannels()
    if not channels:
        return None

    groups = set()
    for meta in channels.values():
        groups.add(meta['group'])

    return groups


def GetChannels():
    try:
        res = HTTP.Request(SKYNET_PLAYLIST).content.splitlines()
    except:
        return None


    if not len(res) > 2 or not res[0].startswith('#EXTM3U'):
        return None

    ret = {}
    current = None

    for i in range(1, len(res)):
        line = res[i].strip()

        if not line:
            continue
        if line.startswith('#EXTINF:'):
            try:
                meta = line[8:].split(',', 1)
                current = {
                    'title': meta[1],
                    'group': GROUP_RE.search(meta[0]).group(1)
                }
            except:
                current = None
        elif current:
            ret[line] = current
            current = None

    return ret


def Search(query, **kwargs):

    channels = GetChannels()

    found = {}
    query = query.decode('utf-8').lower()

    for uri, meta in channels.items():
        if query in meta['title'].decode('utf-8').lower():
            found[uri] = meta['title']

    if not found:
        return NoContents()

    oc = ObjectContainer(
        title2=u'Поиск канала',
        replace_parent=False,
    )

    for uri, title in found.items():
        oc.add(GetVideoObject(uri, title))
    return oc


def NoContents():
    return ObjectContainer(
        header=u'%s' % L('Error'),
        message=u'%s' % L('No entries found')
    )
