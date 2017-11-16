# zap2epg tv schedule grabber for kodi
################################################################################
#   This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################
import xbmc,xbmcaddon,xbmcvfs,xbmcgui,xbmcplugin
import subprocess
from subprocess import Popen
from xbmcswift2 import Plugin
import StringIO
import os
import re
import sys
import logging
import zap2epg
import urllib2
import json
from collections import OrderedDict
import time
import datetime

userdata = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
if not os.path.exists(userdata):
        os.mkdir(userdata)
log = os.path.join(userdata, 'zap2epg.log')
Clist = os.path.join(userdata, 'channels.json')
cacheDir = os.path.join(userdata, 'cache')
plugin = Plugin()
dialog = xbmcgui.Dialog()
gridtime = (int(time.mktime(time.strptime(str(datetime.datetime.now().replace(microsecond=0,second=0,minute=0)), '%Y-%m-%d %H:%M:%S'))))

def get_icon_path(icon_name):
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    return os.path.join(addon_path, 'resources', 'img', icon_name+".png")

def create_cList():
    lineupcode = xbmcaddon.Addon().getSetting('lineupcode')
    url = 'http://tvlistings.gracenote.com/api/grid?lineupId=&timespan=3&headendId=' + lineupcode + '&country=USA&device=-&postalCode=' + zipcode + '&time=' + str(gridtime) + '&pref=-&userId=-'
    content = urllib2.urlopen(url).read()
    contentDict = json.loads(content)
    stationDict = {}
    if 'channels' in contentDict:
        for channel in contentDict['channels']:
            skey = channel.get('channelId')
            stationDict[skey] = {}
            stationDict[skey]['name'] = channel.get('callSign')
            stationDict[skey]['num'] = channel.get('channelNo')
            stationDict[skey]['include'] = 'False'
    stationDictSort = OrderedDict(sorted(stationDict.iteritems(), key=lambda i: (float(i[1]['num']))))
    with open(Clist,"w") as f:
        json.dump(stationDictSort,f)

@plugin.route('/channels')
def channels():
    lineupcode = xbmcaddon.Addon().getSetting('lineupcode')
    if lineup is None or zipcode is None:
        dialog.ok('Location not configured!', '', 'Please setup your location before configuring channels.')
    if not os.path.isfile(Clist):
        create_cList()
    else:
        newList = dialog.yesno('Existing Channel List Found', 'Would you like to download a new channel list or review your current list?', '', 'Select Yes to download new list.')
        if newList:
            os.remove(Clist)
            create_cList()
    with open(Clist) as data:
        stationDict = json.load(data)
    stationDict = OrderedDict(sorted(stationDict.iteritems(), key=lambda i: (float(i[1]['num']))))
    stationCode = []
    stationListName = []
    stationListNum = []
    stationListInclude = []
    for station in stationDict:
        stationCode.append(station)
        stationListName.append(stationDict[station]['name'])
        stationListNum.append(stationDict[station]['num'])
        stationListInclude.append(stationDict[station]['include'])
    stationPre = [i for i, x in enumerate(stationListInclude) if x == 'True']
    stationListFull = zip(stationListNum, stationListName)
    stationList = ["%s %s" % x for x in stationListFull]
    selCh = dialog.multiselect('Click to Select Channels to Include', stationList, preselect=stationPre)
    for station in stationDict:
        stationDict[station]['include'] = 'False'
    stationListCodes = []
    if selCh >= 0:
        for channel in selCh:
            skey = stationCode[channel]
            stationDict[skey]['include'] = 'True'
            stationListCodes.append(skey)
    with open(Clist,"w") as f:
        json.dump(stationDict,f)
    xbmcaddon.Addon().setSetting(id='slist', value=','.join(stationListCodes))

@plugin.route('/location')
def location():
    country = ['USA', 'CAN']
    countryNew = dialog.select('Select your country', list=country)
    zipcodeNew = dialog.input('Enter your zipcode', defaultt=zipcode, type=xbmcgui.INPUT_ALPHANUM)
    if not zipcodeNew:
        return
    zipcodeNew =re.sub(' ', '', zipcodeNew)
    xbmcaddon.Addon().setSetting(id='zipcode', value=zipcodeNew)
    if countryNew == 0:
        url = 'https://tvlistings.gracenote.com/gapzap_webapi/api/Providers/getPostalCodeProviders/USA/' + zipcodeNew + '/gapzap'
        lineupsN = ['AVAILABLE LINEUPS', 'TIMEZONE - Eastern', 'TIMEZONE - Central', 'TIMEZONE - Mountain', 'TIMEZONE - Pacific', 'TIMEZONE - Alaskan', 'TIMEZONE - Hawaiian']
        lineupsC = ['NONE', 'DFLTE', 'DFLTC', 'DFLTM', 'DFLTP', 'DFLTA', 'DFLTH']
    if countryNew == 1:
        url = 'https://tvlistings.gracenote.com/gapzap_webapi/api/Providers/getPostalCodeProviders/CAN/' + zipcodeNew + '/gapzap'
        lineupsN = ['AVAILABLE LINEUPS', 'TIMEZONE - Eastern', 'TIMEZONE - Central', 'TIMEZONE - Mountain', 'TIMEZONE - Pacific']
        lineupsC = ['NONE', 'DFLTEC', 'DFLTCC', 'DFLTMC', 'DFLTPC']
    content = urllib2.urlopen(url).read()
    lineupDict = json.loads(content)
    if 'Providers' in lineupDict:
        for provider in lineupDict['Providers']:
            lineupName = provider.get('name')
            lineupLocation = provider.get('location')
            if lineupLocation != '':
                lineupCombo = lineupName + '  (' + lineupLocation + ')'
                lineupsN.append(lineupCombo)
            else:
                lineupsN.append(lineupName)
            lineupsC.append(provider.get('headendId'))
    else:
        dialog.ok('Error - No Providers!', 'No providers were found - please check zipcode and try again.')
        return
    lineupSel = dialog.select('Select a lineup', list=lineupsN)
    if lineupSel:
        lineupSelCode = lineupsC[lineupSel]
        lineupSelName = lineupsN[lineupSel]
        xbmcaddon.Addon().setSetting(id='lineupcode', value=lineupSelCode)
        xbmcaddon.Addon().setSetting(id='lineup', value=lineupSelName)
        if os.path.exists(cacheDir):
            entries = os.listdir(cacheDir)
            for entry in entries:
                oldfile = entry.split('.')[0]
                if oldfile.isdigit():
                    fn = os.path.join(cacheDir, entry)
                    try:
                        os.remove(fn)
                    except:
                        pass
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmc.executebuiltin('Container.Refresh')
        return

@plugin.route('/run')
def run():
    logging.basicConfig(filename=log, filemode='w',format='%(asctime)s %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logging.DEBUG, disable_existing_loggers=False)
    days = xbmcaddon.Addon().getSetting('days')
    lineupcode = xbmcaddon.Addon().getSetting('lineupcode')
    xdetails = xbmcaddon.Addon().getSetting('xdetails')
    slist = xbmcaddon.Addon().getSetting('slist')
    status = zap2epg.mainRun(userdata)
    dialog.ok('zap2epg Finished!', 'zap2epg completed in ' + str(status[0]) + ' seconds.', '', str(status[1]) + ' Stations and ' + str(status[2]) + ' Episodes written to xmltv.xml file.')



@plugin.route('/open_settings')
def open_settings():
    plugin.open_settings()


@plugin.route('/')
def index():
    items = []
    items.append(
    {
        'label': 'Run zap2epg and Update Guide Data',
        'path': plugin.url_for(u'run'),
        'thumbnail':get_icon_path('run'),
    })
    items.append(
    {
        'label': 'Change Current Location | Zipcode: ' + zipcode + ' &  Lineup: ' + lineup,
        'path': plugin.url_for(u'location'),
        'thumbnail':get_icon_path('antenna'),
    })
    items.append(
    {
        'label': 'Configure Channel List',
        'path': plugin.url_for(u'channels'),
        'thumbnail':get_icon_path('channel'),
    })
    items.append(
    {
        'label': 'Configure Settings and Options',
        'path': plugin.url_for(u'open_settings'),
        'thumbnail':get_icon_path('settings'),
    })
    return items


if __name__ == '__main__':
    try:
        zipcode = xbmcaddon.Addon().getSetting('zipcode')
        lineup = xbmcaddon.Addon().getSetting('lineup')
        if zipcode == '' or lineup == '':
            zipConfig = dialog.yesno('No Lineup Configured!', 'You need to configure your lineup location before running zap2epg.', '', 'Would you like to setup your lineup?')
            if zipConfig:
                location()
                xbmc.executebuiltin('Container.Refresh')
    except:
        dialog.ok('No Lineup Configured!', '', 'Please configure your zipcode and lineup under Change Current Location.')
    plugin.run()