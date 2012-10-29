# Authors:
#   Loris Santamaria <loris@lgs.com.ve>
#
# Copyright (C) 2012  Links Global Services, C.A.
# see file 'COPYING' for use and warranty information
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import netaddr
import time
import re

from ipalib.request import context
from ipalib import api, errors, output
from ipalib import Command
from ipalib.parameters import Flag, Bool, Int, Decimal, Str, StrEnum, Any
from ipalib.plugins.baseldap import *
from ipalib import _, ngettext
from ipalib.util import (validate_zonemgr, normalize_zonemgr,
        validate_hostname, validate_dns_label, validate_domain_name)
from ipapython.ipautil import valid_ip, CheckedIPAddress
from ldap import explode_dn

__doc__ = _("""
Asterisk Configuration

Manage Asterisk PBX Sites, Extensions, Users, Voicemail and configs. An organization
may have multiple asterisk sites, and in a site there may be multiple asterisk servers,
equally configured to offer failover and/or load balancing. Thus in a asterisk site we
define "users", which represent phones, "extensions" that define the dialing logic in 
the site, "voicemail" mailboxes, and Asterisk configuration values.

EXAMPLES:

 Add new Asterisk site:
   ipa astsite-add headquarter --description="Headquarter SIP servers"

 Modify the zone description:
   ipa astsite-mod headquarter --description="Headquarter Telephony servers" 

 Add an Asterisk user
   ipa astuser-add headquarter --tech=SIP --name=1001 --description="John Doe" \\
	--context=local --callerid="John Doe <1001>" --secret=abc123456 \\
	--brand=ACME --model="Acme P001" --mac-address=00:11:22:33:44:55

 Add an Asterisk extension
   ipa astextension-add headquarter --name=1001-1 \\
	--context=ext-local --extension=1001 --priority=1 \\
	--application="Dial" --data="SIP/1001,20"

PER-SITE DEFAULTS

Most SIP or IAX users in a site share the same values for most attributes 
like registration server, encryption and so forth. Setting default values
allows the administrator to have most of these details filled at user creation
time. NOTE: When changing per-site defaults, already created objects won't get
updated with the new default values. It is the duty of the administrator to update
these values.

 Show per-site defaults
   ipa astsite-show headquarter

 Modify per-site defaults
   ipa astsite-mod headquarter --default_registrationserver="sip.acme.com" \\
	--default_encryption=yes --default_canreinvite=yes --default_nat=no

Automatic extension creation

In most setup every user created needs at least one extension created in the 
dialplan. Setting the appropiate per-site defaults the administrator may have
the extensions created automatically. 

In the --auto-extension-params option the fields are separated by commas. The first field
is the context in which the extension will be created, the second is the extension priority,
the third is the application to executed and the rest of the field are the application parameters. 
There MUST be at least four fields even tough the last one may be blank 

The $NAME variable will be substituted by the corresponding "user" name, and the
$TECH variable will be substituted by the user's tech.

NOTE: deleting a user won't remove the automatically created extensions.

 Enable per-site automatic extension creation
   ipa astdefaults-mod headquarter --auto-extension-creation=TRUE

 Define default extension values
   ipa astsite-mod headquarter \\
	--auto-extension-params="ext-local,1,Dial,$TECH/$NAME,20" \\
	--auto-extension-params="ext-local,2,Hangup," \\
	--auto-extension-params="ext-local,hint,$TECH/$NAME,"
""")

def _validate_ipmask(ugettext, ipmask):
    if not ipmask:
        return

    try:
        ip = CheckedIPAddress(ipmask, parse_netmask=True,
                              allow_network=True)
    except (netaddr.AddrFormatError, ValueError), e:
        return unicode(e)
    except UnboundLocalError:
        return _(u"invalid address format")

class astsite(LDAPObject):
    """
    Asterisk site, container for users, extensions, mailboxes and configs.
    """
    container_dn = 'cn=asterisk'
    object_name = _('Asterisk Site')
    object_name_plural = _('Asterisk Sites')
    object_class = ['top', 'nsContainer', 'AsteriskSiteDefaults']
    default_attributes = [
        'cn', 'description' 
    ] 
    label = _('Asterisk Sites')
    label_singular = _('Asterisk Site')

    takes_params = (
        Str('cn',
            cli_name='name',
            label=_('Site name'),
            doc=_('Site Name'),
            normalizer=lambda value: value.lower(),
            primary_key=True,
        ),
        Str('description',
            cli_name='description',
            label=_('Site Description'),
            doc=_('Site Description'),
        ),
        Str('astaccountregistrationserver?',
            cli_name='default_registrationserver',
            label=_('Default registration server'),
            doc=_('Default registration server for this site. You may specify an IP or domain name'),
        ),
        Str('astaccountfromdomain?',
            cli_name='default_fromdomain',
            label=_('Default FromDomain'),
            doc=_('Sets default From: domain in SIP messages when acting as a SIP ua (client)'),
        ),
        StrEnum('astaccountallowoverlap?',
            cli_name='default_allowoverlap',
            label=_('AllowOverlap Default'),
            doc=_('Overlap dial provides for a longer time-out period between digits, also called the inter-digit timer. With overlap dial set to off, the gateway expects to receive the digits one right after the other coming in to this line with very little delay between digits'),
            values=(u'yes', u'no',),
        ),
        Str('astaccountallowedcodec?',
            cli_name='default_allowedcodec',
            label=_('Default Allowed Codecs'),
            doc=_('Default Allowed Codecs'),
        ),
        Str('astaccountdisallowedcodec?',
            cli_name='default_disallowedcodec',
            label=_('Default Disallowed Codecs'),
            doc=_('Default Disallowed Codecs'),
        ),
        StrEnum('astaccountamaflags?',
            cli_name='default_amaflags',
            label=_('AMAflags Default'),
            doc=_('Default Automated Message Accounting flags'),
            values=(u'default', u'omit', u'billing', u'documentation',),
        ),
        Int('astaccountcalllimit?',
            cli_name='default_calllimit',
            label=_('CallLimit Default'),
            doc=_('Number of simultaneous calls through this user/peer by default'),
            minvalue=0,
        ),
        StrEnum('astaccountcanreinvite?',
            cli_name='default_canreinvite',
            label=_('CanReinvite Default'),
            doc=_('Permit direct media traffic between endpoints by default'),
            values=(u'yes', u'no',),
        ),
        StrEnum('astaccountnat?',
            cli_name='default_nat',
            label=_('Nat Default'),
            doc=_('Setting it to yes forces RFC 3581 behavior and enables symmetric RTP support. Setting it to no only enables RFC 3581 behavior if the remote side requests it and disables symmetric RTP support. Setting it to force_rport forces RFC 3581 behavior and disables symmetric RTP support. Setting it to comedia enables RFC 3581 behavior if the remote side requests it and enables symmetric RTP support.'),
            values=(u'yes', u'no', u'force_rport', u'comedia',),
        ),
        StrEnum('astaccountqualify?',
            cli_name='default_qualify',
            label=_('Qualify Default'),
            doc=_('Check if peer is online'),
            values=(u'yes', u'no',),
        ),
        StrEnum('astaccountdtmfmode?',
            cli_name='default_dtmfmode',
            label=_('Default Dtmfmode'),
            doc=_('Configure DTMF transmission'),
            values=(u'inband', u'rfc2833', u'info', u'auto',),
        ),
        Str('astaccountpermit?',
            _validate_ipmask,
            cli_name='default_permit',
            label=_('Default permitted subnet') ,
            doc=_('Default permitted subnet in ip/mask format'),
        ),
        Str('astaccountdeny?',
            _validate_ipmask,
            cli_name='default_deny',
            label=_('Default denied subnet'),
            doc=_('Default permitted subnet in ip/mask format'),
        ),
        Str('astaccountlanguage?',
            cli_name='default_language',
            label=_('Default Language'),
            doc=_('Default language for voice prompts'),
        ),
        Str('astaccountmusiconhold?',
            cli_name='default_musiconhold',
            label=_('Default MOH'),
            doc=_('Default music on hold category'),
        ),
        Int('astaccountrtpholdtimeout?',
            cli_name='default_rtpholdtimeout',
            label=_('Default RTPHoldTimeout'),
            doc=_('Default value for RTP HOLD timeout parameter'),
            minvalue=0,
        ),
        Int('astaccountrtptimeout?',
            cli_name='default_rtptimeout',
            label=_('Default RTPtimeout'),
            doc=_('Default value for RTP timeout parameter'),
            minvalue=0,
        ),
        Str('astaccountregistrationcontext?',
            cli_name='default_registrationcontext',
            label=_('Default registration context'),
            doc=_('If specified, Asterisk will dynamically create and destroy a NoOp priority 1 extension in this context for a given peer who registers '),
        ),
        Str('astaccountsubscribecontext?',
            cli_name='default_subscribecontext',
            label=_('Default subscribe context'),
            doc=_('Set a specific context for SIP SUBSCRIBE requests'),
        ),
        Str('astaccounttransport?',
            cli_name='default_transport',
            label=_('Default transport'),
            doc=_('Default transports in preferred order, comma separated. E.g. tls,tcp,udp'),
        ),
        StrEnum('astaccounttype?',
            cli_name='default_type',
            label=_('type Default'),
            doc=_(' '),
            values=(u'user', u'peer', u'friend'),
        ),
        StrEnum('astaccountvideosupport?',
            cli_name='default_videosupport',
            label=_('videosupport Default'),
            doc=_(' '),
            values=(u'yes', u'no',),
        ),
	#astvoicemailoptions
	#astvoicemailtimestamp
	#astvoicemailcontext
        StrEnum('astaccountencryption?',
            cli_name='default_encryption',
            label=_('encryption Default'),
            doc=_(' '),
            values=(u'yes', u'no',),
        ),
	#ipaautoastextension
	#ipaautoasttemplate
    )

api.register(astsite)

class astsite_add(LDAPCreate):
    __doc__ = _('Create new Asterisk Site')

api.register(astsite_add)


class astsite_del(LDAPDelete):
    __doc__ = _('Delete Asterisk Site')

api.register(astsite_del)


class astsite_mod(LDAPUpdate):
    __doc__ = _('Modify Asterisk Site')

api.register(astsite_mod)


class astsite_find(LDAPSearch):
    __doc__ = _('Search for Asterisk Site')

api.register(astsite_find)

class astsite_show(LDAPRetrieve):
    __doc__ = _('Display information about an Asterisk site')

api.register(astsite_show)

