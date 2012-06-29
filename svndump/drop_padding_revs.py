#!/usr/bin/env python
#===============================================================================
#
# Copyright (C) 2012 Aurelien Mino <aurelien.mino@gmail.com>
#
# This file is part of SvnDumpTool
#
# SvnDumpTool is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# SvnDumpTool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SvnDumpTool; see the file COPYING.  If not, write to
# the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#
#===============================================================================

import os
import sys
import tempfile
import random
import string

from svndump import __version
from optparse import OptionParser
from file import SvnDumpFile

class SanitizeDumpFile(object):

    def __init__(self, verbosity ):
        self.verbosity = verbosity
        self.skipped_revisions = 0
        self.rev_map = {}
        
    def transform(self, dump ):
        """The dump object passed to this method has been set to the revision
        we're to transform"""
        # Update Node-copyfrom-rev property on nodes
        if self.skipped_revisions > 0:
            for node in dump.get_nodes_iter():
                copy_from_rev = node.get_copy_from_rev()
                if copy_from_rev != 0:
                    if self.verbosity > 0:
                        print " * updated referenced revison in copy_from_rev from %s to %s" % (copy_from_rev, self.rev_map[copy_from_rev])
                    node.set_copy_from(node.get_copy_from_path(), self.rev_map[copy_from_rev])

    def filter_dump_file(self, srcfile, dstfile ):
    
        # SvnDumpFile classes for reading/writing dumps
        srcdmp = SvnDumpFile()
        dstdmp = SvnDumpFile()
    
        # read a first time source file to find all referenced revisions (they should not be later removed)
        srcdmp.open( srcfile )
        hasrev = srcdmp.read_next_rev()
        referenced_revs = set()
        while hasrev:
            for node in srcdmp.get_nodes_iter():
                copy_from_rev = node.get_copy_from_rev()
                if copy_from_rev != 0:
                    referenced_revs.add(copy_from_rev)
            hasrev = srcdmp.read_next_rev()
        srcdmp.close()

        # start reading again source file
        srcdmp.open( srcfile )
        hasrev = srcdmp.read_next_rev()
        if hasrev:
            # create the dump file
            dstdmp.create_like( dstfile, srcdmp )
            # now copy all the revisions
            while hasrev:
                if self.verbosity > 0:
                    print "Revision-number: orig=%s, new=%s" % (srcdmp.get_rev_nr(), srcdmp.get_rev_nr()-self.skipped_revisions)
                if srcdmp.get_rev_log() == "This is an empty revision for padding." and srcdmp.get_rev_nr() not in referenced_revs:
                    if self.verbosity > 0:
                        print " * skipped padding revison (number of skipped revisions = %s)" % self.skipped_revisions
                    self.skipped_revisions += 1
                else:
                    self.transform( srcdmp )
                    self.rev_map[srcdmp.get_rev_nr()] = (srcdmp.get_rev_nr() - self.skipped_revisions)
                    dstdmp.add_rev_from_dump( srcdmp )
                hasrev = srcdmp.read_next_rev()
        else:
            print "no revisions in the source dump '%s' ???" % srcfile
    
        # cleanup
        srcdmp.close()
        dstdmp.close()

def svndump_drop_padding_revs_cmdline( appname, args ):
    """
    Parses the commandline and executes the removal of padding revisions.

    Usage:

        >>> svndump_drop_padding_revs_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] source destination" % appname
    parser = OptionParser( usage=usage, version="%prog "+__version )
    parser.add_option( "-v", "--verbose",
                       action="store_const", dest="verbose", const=2,
                       help="verbose output" )
    (options, args) = parser.parse_args( args )
        
    if len( args ) != 2:
        print "specify exactly one source and one destination dump file."
        return 1

    sanitizer = SanitizeDumpFile(options.verbose)
    sanitizer.filter_dump_file( args[0], args[1] )
    return 0


