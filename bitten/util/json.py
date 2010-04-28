# -*- coding: utf-8 -*-
#
# Copyright (C)2006-2009 Edgewall Software
# Copyright (C) 2006 Christopher Lenz <cmlenz@gmx.de>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.

"""Utility functions for converting to web formats"""

# to_json is really a wrapper for trac.util.presentation.to_json, but we have lots of fallbacks for compatibility
# trac.util.presentation.to_json is present from Trac 0.12
# If that's not present, we fall back to the default Python json module, present from Python 2.6 onwards
# If that's not present, we have a copy of the to_json method, which we will remove once Trac 0.11 support is removed
# And finally, the to_json method requires trac.util.text.javascript_quote, which is only present from Trac 0.11.3, so we have a copy of that too

try:
    # to_json is present from Trac 0.12 onwards - should remove once Trac 0.11 support is removed
    from trac.util.presentation import to_json
except ImportError:
    try:
        # If we have Python 2.6 onwards, use the json method directly
        from json import dumps
        
        def to_json(value):
            """Encode `value` to JSON."""
            return dumps(value, sort_keys=True, separators=(',', ':'))
    except ImportError:
        # javascript_quote is present from Trac 0.11.3 onwards - should remove once Trac 0.11.2 support is removed
        try:
            from trac.util.text import javascript_quote
        except ImportError:
            _js_quote = {'\\': '\\\\', '"': '\\"', '\b': '\\b', '\f': '\\f',
                 '\n': '\\n', '\r': '\\r', '\t': '\\t', "'": "\\'"}
            for i in range(0x20):
                _js_quote.setdefault(chr(i), '\\u%04x' % i)
            _js_quote_re = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t\']')
            def javascript_quote(text):
                """Quote strings for inclusion in javascript"""
                if not text:
                    return ''
                def replace(match):
                    return _js_quote[match.group(0)]
                return _js_quote_re.sub(replace, text)

        def to_json(value):
            """Encode `value` to JSON."""
            if isinstance(value, basestring):
                return '"%s"' % javascript_quote(value)
            elif value is None:
                return 'null'
            elif value is False:
                return 'false'
            elif value is True:
                return 'true'
            elif isinstance(value, (int, long)):
                return str(value)
            elif isinstance(value, float):
                return repr(value)
            elif isinstance(value, (list, tuple)):
                return '[%s]' % ','.join(to_json(each) for each in value)
            elif isinstance(value, dict):
                return '{%s}' % ','.join('%s:%s' % (to_json(k), to_json(v))
                                         for k, v in sorted(value.iteritems()))
            else:
                raise TypeError('Cannot encode type %s' % value.__class__.__name__)
