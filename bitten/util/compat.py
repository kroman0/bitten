# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

"""Compatibility fixes for external libraries and Python."""

import sys

# Fix for issue http://bugs.python.org/issue8797 in Python 2.6

if sys.version_info[:2] == (2, 6):
    import urllib2
    import base64

    class HTTPBasicAuthHandler(urllib2.HTTPBasicAuthHandler):
        """Patched version of Python 2.6's HTTPBasicAuthHandler.
        
        The fix for [1]_ introduced an infinite recursion bug [2]_ into
        Python 2.6.x that is triggered by attempting to connect using
        Basic authentication with a bad username and/or password. This
        class fixes the problem using the simple solution outlined in [3]_.
        
        .. [1] http://bugs.python.org/issue3819
        .. [2] http://bugs.python.org/issue8797
        .. [3] http://bugs.python.org/issue8797#msg126657
        """

        def retry_http_basic_auth(self, host, req, realm):
            user, pw = self.passwd.find_user_password(realm, host)
            if pw is not None:
                raw = "%s:%s" % (user, pw)
                auth = 'Basic %s' % base64.b64encode(raw).strip()
                if req.get_header(self.auth_header, None) == auth:
                    return None
                req.add_unredirected_header(self.auth_header, auth)
                return self.parent.open(req, timeout=req.timeout)
            else:
                return None

else:
    from urllib2 import HTTPBasicAuthHandler
