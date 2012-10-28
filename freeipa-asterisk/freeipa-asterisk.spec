%global httpd_conf /etc/httpd/conf.d
%global plugin_dir %{_libdir}/dirsrv/plugins
%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from
distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from
distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif
%global POLICYCOREUTILSVER 1.33.12-1
%global gettext_domain ipa

Name:           freeipa-asterisk
Version:        0.1.0
Release:        1%{?dist}
Summary:        freeIPA plugin for administering Asterisk LDAP realtime database

Group:          System Environment/Base
License:        GPLv3+
URL:            http://www.freeipa.org/
Source0:        http://www.freeipa.org/downloads/src/freeipa-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  nspr-devel
BuildRequires:  nss-devel
BuildRequires:  openssl-devel
BuildRequires:  openldap-devel
BuildRequires:  krb5-devel
BuildRequires:  krb5-workstation
BuildRequires:  libuuid-devel
BuildRequires:  libcurl-devel >= 7.21.7-2
BuildRequires:  xmlrpc-c-devel >= 1.27.4
BuildRequires:  popt-devel
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  m4
BuildRequires:  libtool
BuildRequires:  gettext
BuildRequires:  python-devel
BuildRequires:  authconfig
BuildRequires:  python-ldap
BuildRequires:  python-setuptools
BuildRequires:  python-krbV
BuildRequires:  python-nss
BuildRequires:  python-netaddr >= 0.7.5-3
BuildRequires:  python-kerberos
BuildRequires:  python-rhsm
BuildRequires:  pyOpenSSL
BuildRequires:  pylint
BuildRequires:  libipa_hbac-python
BuildRequires:  python-memcached
BuildRequires:  sssd >= 1.8.0
Requires: freeipa-python >= 2.2.0
Requires: freeipa-client >= 2.2.0
Requires: python-krbV
Requires: python-ldap

%description
This package provides all the required freeIPA objects, schema and templates
required for creating and managing most Asterisk LDAP realtime objects for
Asterisk 1.8+

%prep
%setup -n freeipa-%{version} -q

%build
export CFLAGS="$CFLAGS %{optflags}"
export CPPFLAGS="$CPPFLAGS %{optflags}"
export SUPPORTED_PLATFORM=fedora16
# Force re-generate of platform support
rm -f ipapython/services.py
make version-update
cd ipa-client; ../autogen.sh --prefix=%{_usr} --sysconfdir=%{_sysconfdir} --localstatedir=%{_localstatedir} --libdir=%{_libdir} --mandir=%{_mandir}; cd ..
%if ! %{ONLY_CLIENT}
cd daemons; ../autogen.sh --prefix=%{_usr} --sysconfdir=%{_sysconfdir} --localstatedir=%{_localstatedir} --libdir=%{_libdir} --mandir=%{_mandir} --with-openldap; cd ..
cd install; ../autogen.sh --prefix=%{_usr} --sysconfdir=%{_sysconfdir} --localstatedir=%{_localstatedir} --libdir=%{_libdir} --mandir=%{_mandir}; cd ..
%endif

%if ! %{ONLY_CLIENT}
make IPA_VERSION_IS_GIT_SNAPSHOT=no %{?_smp_mflags} all
cd selinux
# This isn't multi-process make capable yet
make all
%else
make IPA_VERSION_IS_GIT_SNAPSHOT=no %{?_smp_mflags} client
%endif

%install
rm -rf %{buildroot}
%if ! %{ONLY_CLIENT}
export SUPPORTED_PLATFORM=fedora16
# Force re-generate of platform support
rm -f ipapython/services.py
make install DESTDIR=%{buildroot}
cd selinux
make install DESTDIR=%{buildroot}
cd ..
%else
make client-install DESTDIR=%{buildroot}
%endif
%find_lang %{gettext_domain}


%if ! %{ONLY_CLIENT}
# Remove .la files from libtool - we don't want to package
# these files
rm %{buildroot}/%{plugin_dir}/libipa_pwd_extop.la
rm %{buildroot}/%{plugin_dir}/libipa_enrollment_extop.la
rm %{buildroot}/%{plugin_dir}/libipa_winsync.la
rm %{buildroot}/%{plugin_dir}/libipa_repl_version.la
rm %{buildroot}/%{plugin_dir}/libipa_uuid.la
rm %{buildroot}/%{plugin_dir}/libipa_modrdn.la
rm %{buildroot}/%{plugin_dir}/libipa_lockout.la
rm %{buildroot}/%{_libdir}/krb5/plugins/kdb/ipadb.la

# Some user-modifiable HTML files are provided. Move these to /etc
# and link back.
mkdir -p %{buildroot}/%{_sysconfdir}/ipa/html
mkdir -p %{buildroot}/%{_localstatedir}/cache/ipa/sysrestore
mkdir %{buildroot}%{_usr}/share/ipa/html/
ln -s ../../../..%{_sysconfdir}/ipa/html/ssbrowser.html \
    %{buildroot}%{_usr}/share/ipa/html/ssbrowser.html
ln -s ../../../..%{_sysconfdir}/ipa/html/unauthorized.html \
    %{buildroot}%{_usr}/share/ipa/html/unauthorized.html
ln -s ../../../..%{_sysconfdir}/ipa/html/browserconfig.html \
    %{buildroot}%{_usr}/share/ipa/html/browserconfig.html
ln -s ../../../..%{_sysconfdir}/ipa/html/ipa_error.css \
    %{buildroot}%{_usr}/share/ipa/html/ipa_error.css

# So we can own our Apache configuration
mkdir -p %{buildroot}%{_sysconfdir}/httpd/conf.d/
/bin/touch %{buildroot}%{_sysconfdir}/httpd/conf.d/ipa.conf
/bin/touch %{buildroot}%{_sysconfdir}/httpd/conf.d/ipa-pki-proxy.conf
/bin/touch %{buildroot}%{_sysconfdir}/httpd/conf.d/ipa-rewrite.conf
mkdir -p %{buildroot}%{_usr}/share/ipa/html/
/bin/touch %{buildroot}%{_usr}/share/ipa/html/ca.crt
/bin/touch %{buildroot}%{_usr}/share/ipa/html/configure.jar
/bin/touch %{buildroot}%{_usr}/share/ipa/html/krb.con
/bin/touch %{buildroot}%{_usr}/share/ipa/html/krb5.ini
/bin/touch %{buildroot}%{_usr}/share/ipa/html/krbrealm.con
/bin/touch %{buildroot}%{_usr}/share/ipa/html/preferences.html
mkdir -p %{buildroot}%{_initrddir}
# Default to systemd initscripts for F16 and above
mkdir -p %{buildroot}%{_unitdir}
install -m 644 init/systemd/ipa.service %{buildroot}%{_unitdir}/ipa.service
mkdir -p %{buildroot}%{_libexecdir}
install -m 644 init/systemd/ipa_memcached.service %{buildroot}%{_unitdir}/ipa_memcached.service
install -m 755 init/systemd/freeipa-systemd-upgrade %{buildroot}%{_libexecdir}/freeipa-systemd-upgrade

mkdir -p %{buildroot}%{_initrddir}
mkdir %{buildroot}%{_sysconfdir}/sysconfig/
install -m 644 init/ipa_memcached.conf %{buildroot}%{_sysconfdir}/sysconfig/ipa_memcached
mkdir -p %{buildroot}%{_localstatedir}/run/
install -d -m 0700 %{buildroot}%{_localstatedir}/run/ipa_memcached/

mkdir -p %{buildroot}%{_sysconfdir}/tmpfiles.d/
install -m 0644 init/systemd/ipa.conf.tmpfiles %{buildroot}%{_sysconfdir}/tmpfiles.d/ipa.conf
%endif

mkdir -p %{buildroot}%{_sysconfdir}/ipa/
/bin/touch %{buildroot}%{_sysconfdir}/ipa/default.conf
/bin/touch %{buildroot}%{_sysconfdir}/ipa/ca.crt
mkdir -p %{buildroot}/%{_localstatedir}/lib/ipa-client/sysrestore

%if ! %{ONLY_CLIENT}
mkdir -p %{buildroot}%{_sysconfdir}/bash_completion.d
install -pm 644 contrib/completion/ipa.bash_completion %{buildroot}%{_sysconfdir}/bash_completion.d/ipa
mkdir -p %{buildroot}%{_sysconfdir}/cron.d
install -pm 644 ipa-compliance.cron %{buildroot}%{_sysconfdir}/cron.d/ipa-compliance
%endif

%clean
rm -rf %{buildroot}

%if ! %{ONLY_CLIENT}
%post server
# Use systemd scheme, update systemd as service units have changed
    /bin/systemctl --system daemon-reload 2>&1 || :
if [ $1 -gt 1 ] ; then
    # When upgrade is performed from SysV to systemd, ipa.service will be inactive
    # due to https://bugzilla.redhat.com/show_bug.cgi?id=752846
    # FreeIPA existing setup cannot be used without upgrade script
    # Note also it is now safe to run this script against working FreeIPA install
    # after it has been migrated to systemd setup
    /usr/libexec/freeipa-systemd-upgrade || :
    /usr/sbin/ipa-upgradeconfig || :
fi

%posttrans server
# This must be run in posttrans so that updates from previous
# execution that may no longer be shipped are not applied.
/usr/sbin/ipa-ldap-updater --upgrade >/dev/null 2>&1 || :

%preun server
if [ $1 = 0 ]; then
# Use systemd scheme
    /bin/systemctl --quiet stop ipa.service || :
    /bin/systemctl --quiet disable ipa.service || :
fi

%postun server
if [ "$1" -ge "1" ]; then
# Use systemd scheme
    /bin/systemctl --quiet is-active ipa.service >/dev/null && \
    /bin/systemctl try-restart ipa.service >/dev/null 2>&1 || :
fi

%pre server-selinux
if [ -s /etc/selinux/config ]; then
       . %{_sysconfdir}/selinux/config
       FILE_CONTEXT=%{_sysconfdir}/selinux/targeted/contexts/files/file_contexts
       if [ "${SELINUXTYPE}" == targeted -a -f ${FILE_CONTEXT} ]; then \
               cp -f ${FILE_CONTEXT} ${FILE_CONTEXT}.%{name}
       fi
fi

%post server-selinux
semodule -s targeted -i /usr/share/selinux/targeted/ipa_httpd.pp /usr/share/selinux/targeted/ipa_dogtag.pp
. %{_sysconfdir}/selinux/config
FILE_CONTEXT=%{_sysconfdir}/selinux/targeted/contexts/files/file_contexts
selinuxenabled
if [ $? == 0  -a "${SELINUXTYPE}" == targeted -a -f ${FILE_CONTEXT}.%{name} ]; then
       fixfiles -C ${FILE_CONTEXT}.%{name} restore
       rm -f ${FILE_CONTEXT}.%name
fi

%preun server-selinux
if [ $1 = 0 ]; then
if [ -s /etc/selinux/config ]; then
       . %{_sysconfdir}/selinux/config
       FILE_CONTEXT=%{_sysconfdir}/selinux/targeted/contexts/files/file_contexts
       if [ "${SELINUXTYPE}" == targeted -a -f ${FILE_CONTEXT} ]; then \
               cp -f ${FILE_CONTEXT} ${FILE_CONTEXT}.%{name}
       fi
fi
fi

%postun server-selinux
if [ $1 = 0 ]; then
semodule -s targeted -r ipa_httpd ipa_dogtag
. %{_sysconfdir}/selinux/config
FILE_CONTEXT=%{_sysconfdir}/selinux/targeted/contexts/files/file_contexts
selinuxenabled
if [ $? == 0  -a "${SELINUXTYPE}" == targeted -a -f ${FILE_CONTEXT}.%{name} ]; then
       fixfiles -C ${FILE_CONTEXT}.%{name} restore
       rm -f ${FILE_CONTEXT}.%name
fi
fi
%endif


%if ! %{ONLY_CLIENT}
%files server
%defattr(-,root,root,-)
%doc COPYING README Contributors.txt
%{_sbindir}/ipa-ca-install
%{_sbindir}/ipa-dns-install
%{_sbindir}/ipa-server-install
%{_sbindir}/ipa-replica-conncheck
%{_sbindir}/ipa-replica-install
%{_sbindir}/ipa-replica-prepare
%{_sbindir}/ipa-replica-manage
%{_sbindir}/ipa-csreplica-manage
%{_sbindir}/ipa-server-certinstall
%{_sbindir}/ipa-ldap-updater
%{_sbindir}/ipa-compat-manage
%{_sbindir}/ipa-nis-manage
%{_sbindir}/ipa-managed-entries
%{_sbindir}/ipactl
%{_sbindir}/ipa-upgradeconfig
%{_sbindir}/ipa-compliance
%{_sysconfdir}/cron.d/ipa-compliance
%config(noreplace) %{_sysconfdir}/sysconfig/ipa_memcached
%dir %attr(0700,apache,apache) %{_localstatedir}/run/ipa_memcached/
%config %{_sysconfdir}/tmpfiles.d/ipa.conf
# Use systemd scheme
%attr(644,root,root) %{_unitdir}/ipa.service
%attr(644,root,root) %{_unitdir}/ipa_memcached.service
%{_libexecdir}/freeipa-systemd-upgrade
%dir %{python_sitelib}/ipaserver
%{python_sitelib}/ipaserver/*
%dir %{_libdir}/ipa/certmonger
%attr(755,root,root) %{_libdir}/ipa/certmonger/*
%dir %{_usr}/share/ipa
%{_usr}/share/ipa/wsgi.py*
%{_usr}/share/ipa/*.ldif
%{_usr}/share/ipa/*.uldif
%{_usr}/share/ipa/*.template
%dir %{_usr}/share/ipa/html
%{_usr}/share/ipa/html/ssbrowser.html
%{_usr}/share/ipa/html/browserconfig.html
%{_usr}/share/ipa/html/unauthorized.html
%{_usr}/share/ipa/html/ipa_error.css
%dir %{_usr}/share/ipa/migration
%{_usr}/share/ipa/migration/error.html
%{_usr}/share/ipa/migration/index.html
%{_usr}/share/ipa/migration/invalid.html
%{_usr}/share/ipa/migration/migration.py*
%dir %{_usr}/share/ipa/ui
%{_usr}/share/ipa/ui/index.html
%{_usr}/share/ipa/ui/login.html
%{_usr}/share/ipa/ui/logout.html
%{_usr}/share/ipa/ui/*.ico
%{_usr}/share/ipa/ui/*.css
%{_usr}/share/ipa/ui/*.js
%{_usr}/share/ipa/ui/*.eot
%{_usr}/share/ipa/ui/*.svg
%{_usr}/share/ipa/ui/*.ttf
%{_usr}/share/ipa/ui/*.woff
%dir %{_usr}/share/ipa/ui/ext
%config(noreplace) %{_usr}/share/ipa/ui/ext/extension.js
%dir %{_usr}/share/ipa/ui/images
%{_usr}/share/ipa/ui/images/*.png
%{_usr}/share/ipa/ui/images/*.gif
%dir %{_sysconfdir}/ipa
%dir %{_sysconfdir}/ipa/html
%config(noreplace) %{_sysconfdir}/ipa/html/ssbrowser.html
%config(noreplace) %{_sysconfdir}/ipa/html/ipa_error.css
%config(noreplace) %{_sysconfdir}/ipa/html/unauthorized.html
%config(noreplace) %{_sysconfdir}/ipa/html/browserconfig.html
%ghost %attr(0644,root,apache) %config(noreplace) %{_sysconfdir}/httpd/conf.d/ipa-rewrite.conf
%ghost %attr(0644,root,apache) %config(noreplace) %{_sysconfdir}/httpd/conf.d/ipa.conf
%ghost %attr(0644,root,apache) %config(noreplace) %{_sysconfdir}/httpd/conf.d/ipa-pki-proxy.conf
%{_usr}/share/ipa/ipa.conf
%{_usr}/share/ipa/ipa-rewrite.conf
%{_usr}/share/ipa/ipa-pki-proxy.conf
%ghost %attr(0644,root,apache) %config(noreplace) %{_usr}/share/ipa/html/ca.crt
%ghost %attr(0644,root,apache) %{_usr}/share/ipa/html/configure.jar
%ghost %attr(0644,root,apache) %{_usr}/share/ipa/html/krb.con
%ghost %attr(0644,root,apache) %{_usr}/share/ipa/html/krb5.ini
%ghost %attr(0644,root,apache) %{_usr}/share/ipa/html/krbrealm.con
%ghost %attr(0644,root,apache) %{_usr}/share/ipa/html/preferences.html
%dir %{_usr}/share/ipa/updates/
%{_usr}/share/ipa/updates/*
%attr(755,root,root) %{plugin_dir}/libipa_pwd_extop.so
%attr(755,root,root) %{plugin_dir}/libipa_enrollment_extop.so
%attr(755,root,root) %{plugin_dir}/libipa_winsync.so
%attr(755,root,root) %{plugin_dir}/libipa_repl_version.so
%attr(755,root,root) %{plugin_dir}/libipa_uuid.so
%attr(755,root,root) %{plugin_dir}/libipa_modrdn.so
%attr(755,root,root) %{plugin_dir}/libipa_lockout.so
%dir %{_localstatedir}/lib/ipa
%attr(700,root,root) %dir %{_localstatedir}/lib/ipa/sysrestore
%dir %{_localstatedir}/cache/ipa
%attr(700,apache,apache) %dir %{_localstatedir}/cache/ipa/sessions
%attr(755,root,root) %{_libdir}/krb5/plugins/kdb/ipadb.so
%{_mandir}/man1/ipa-replica-conncheck.1.gz
%{_mandir}/man1/ipa-replica-install.1.gz
%{_mandir}/man1/ipa-replica-manage.1.gz
%{_mandir}/man1/ipa-csreplica-manage.1.gz
%{_mandir}/man1/ipa-replica-prepare.1.gz
%{_mandir}/man1/ipa-server-certinstall.1.gz
%{_mandir}/man1/ipa-server-install.1.gz
%{_mandir}/man1/ipa-dns-install.1.gz
%{_mandir}/man1/ipa-ca-install.1.gz
%{_mandir}/man1/ipa-compat-manage.1.gz
%{_mandir}/man1/ipa-nis-manage.1.gz
%{_mandir}/man1/ipa-managed-entries.1.gz
%{_mandir}/man1/ipa-ldap-updater.1.gz
%{_mandir}/man8/ipactl.8.gz
%{_mandir}/man8/ipa-upgradeconfig.8.gz
%{_mandir}/man1/ipa-compliance.1.gz

%files server-selinux
%defattr(-,root,root,-)
%doc COPYING README Contributors.txt
%{_usr}/share/selinux/targeted/ipa_httpd.pp
%{_usr}/share/selinux/targeted/ipa_dogtag.pp
%endif

%files client
%defattr(-,root,root,-)
%doc COPYING README Contributors.txt
%{_sbindir}/ipa-client-install
%{_sbindir}/ipa-getkeytab
%{_sbindir}/ipa-rmkeytab
%{_sbindir}/ipa-join
%dir %{_usr}/share/ipa
%dir %{_usr}/share/ipa/ipaclient
%dir %{_localstatedir}/lib/ipa-client
%dir %{_localstatedir}/lib/ipa-client/sysrestore
%{_usr}/share/ipa/ipaclient/ipa.cfg
%{_usr}/share/ipa/ipaclient/ipa.js
%dir %{python_sitelib}/ipaclient
%{python_sitelib}/ipaclient/*.py*
%{_mandir}/man1/ipa-getkeytab.1.gz
%{_mandir}/man1/ipa-rmkeytab.1.gz
%{_mandir}/man1/ipa-client-install.1.gz
%{_mandir}/man1/ipa-join.1.gz
%{_mandir}/man5/default.conf.5.gz

%if ! %{ONLY_CLIENT}
%files admintools
%defattr(-,root,root,-)
%doc COPYING README Contributors.txt
%{_bindir}/ipa
%config %{_sysconfdir}/bash_completion.d
%{_mandir}/man1/ipa.1.gz
%endif

%files python -f %{gettext_domain}.lang
%defattr(-,root,root,-)
%doc COPYING README Contributors.txt
%dir %{python_sitelib}/ipapython
%dir %{python_sitelib}/ipapython/platform
%{python_sitelib}/ipapython/*.py*
%{python_sitelib}/ipapython/platform/*.py*
%dir %{python_sitelib}/ipalib
%{python_sitelib}/ipalib/*
%{python_sitearch}/default_encoding_utf8.so
%{python_sitelib}/ipapython-*.egg-info
%{python_sitelib}/freeipa-*.egg-info
%{python_sitearch}/python_default_encoding-*.egg-info
%ghost %attr(0644,root,apache) %config(noreplace) %{_sysconfdir}/ipa/default.conf
%ghost %attr(0644,root,apache) %config(noreplace) %{_sysconfdir}/ipa/ca.crt

%changelog
* Sat Oct 27 2012 Loris Santamaria <loris@lgs.com.ve> - 0.1.0-1
- Initial version
