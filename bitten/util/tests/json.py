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

import doctest
import unittest

from bitten.util import json


class ToJsonTestCase(unittest.TestCase):

    def test_simple_types(self):
        self.assertEqual('42', json.to_json(42))
        self.assertEqual('123.456', json.to_json(123.456))
        self.assertEqual('true', json.to_json(True))
        self.assertEqual('false', json.to_json(False))
        self.assertEqual('null', json.to_json(None))
        self.assertEqual('"String"', json.to_json('String'))
        self.assertEqual(r'"a \" quote"', json.to_json('a " quote'))

    def test_compound_types(self):
        self.assertEqual('[1,2,[true,false]]',
                         json.to_json([1, 2, [True, False]]))
        self.assertEqual('{"one":1,"other":[null,0],"two":2}',
                         json.to_json({"one": 1, "two": 2,
                                               "other": [None, 0]}))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ToJsonTestCase))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
