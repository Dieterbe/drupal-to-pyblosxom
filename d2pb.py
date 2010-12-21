#!/usr/bin/env python2
import optparse
import sys, os
import MySQLdb
import subprocess
import time

def main():
	p = optparse.OptionParser()
	p.add_option('--host', '-H', default="localhost")
	p.add_option('--user', '-u')
	p.add_option('--passw', '-p', default="")
	p.add_option('--db', '-d')
	p.add_option('--blog', '-b')
	options, arguments = p.parse_args()
	if not options.user or not options.blog or not options.db:
		p.print_help()
		sys.exit(2)
	print 'Connecting %s:%s@%s db %s and writing to %s\n' % (options.user, options.passw, options.host, options.db, options.blog)
	try:
		conn = MySQLdb.connect (host = options.host,
		     	                user = options.user,
		                        passwd = options.passw,
		                        db = options.db)
		cursor = conn.cursor()
	except Exception, e:
		sys.stderr.write ("Could not connect to database\n")
		os._exit(2)
	try:
		# I don't have multiple revisions per node in drupal
		# I don't think pyblosxom can have different teaser per item, so we only use the full body
		# I use tagadelic with fixed tags.  we ignore tag weights and assocations between tags
		# Embedding php code ('<?php ... ?>' or '<% ... %>') like what drupal allows obviously won't work very well. Luckily I never used that feature
		query = "SELECT node.nid, url_alias.dst, node.title, node.created, node.changed, node_revisions.body, GROUP_CONCAT(term_data.name) \
			 FROM node \
			 LEFT JOIN url_alias ON url_alias.src = CONCAT ('node/', node.nid) \
			 JOIN node_revisions on node_revisions.nid = node.nid \
			 LEFT JOIN term_node ON term_node.nid = node.nid \
			 LEFT JOIN term_data ON term_data.tid = term_node.tid \
			 WHERE type = 'blog' AND status = 1 \
			 GROUP BY node.nid \
			 ORDER BY CREATED ASC"
		cursor.execute(query)
        except Exception, e:
		sys.stderr.write("Could not execute query: %s:\n%s\n" % (query, str(e)))
	for row in cursor:
		print "Processing entry: %s" % row[2]
		if row[1]:
			# The url alias is usually a pretty clean starting point (at least i do my Url_aliases_like_this_and_dont_use_special_chars)
			filename = row[1].lower()
		else:
			# first make the string lowercase and replace all useful special chars to something more appropriate:
			filename = row[2].lower().replace(' ','_').replace ('&','and')
			# TODO: there could still be special characters we don't want ($, ^, ...), just remove them. (accented characters should probably become non-accented) (I don't need this in my case)
		try:
			file_path = os.path.join(options.blog,'entries',filename+'.txt')
			print ("\tWriting to %s" % file_path)
			file = open(file_path, 'w')
			file.write('%s\n' % row[2])
			file.write('# pubdate %s\n' % time.strftime("%Y-%m-%d", time.localtime(row[3])))
			file.write('# pubtime %s\n' % time.strftime("%H:%M:%S", time.localtime(row[3])))
			if row[6]:
				file.write('# tags %s\n' % row[6])
			# I've never used input format 2 (which allows almost no html) and format 1 is like format 3, but with stricter html tag allowance.
			# I just assume we use format 3, this should be good enough.
			# Perform drupalesque text processing
			p = subprocess.Popen(['./text_filter.php'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
			output = p.communicate(row[5])[0]
			file.write(output)
			file.close()
		except Exception, e:
			sys.stderr.write ("Cannot write to %s:\n%s\n" % (file_path,str(e)))
			os._exit(2)
# comments : comments.cid, comments.nid, comments.uid, comments.subject, comments.comment, comments.timestamp 	status 	format 	thread 	users 	name 	mail 	homepage

if __name__ == '__main__':
	try:
		main()
	except Exception, e:
		import traceback
		sys.stderr.write ("%s\n" % str(e))
		traceback.print_exc()
		os._exit(1)
